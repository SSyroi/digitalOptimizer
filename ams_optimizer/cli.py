"""Command-Line Interface for AMS Digital Optimizer.

Pure standard library (argparse, sys, os). Compatible with Python 3.9+.
Zero external dependencies.
"""

from __future__ import annotations
import argparse
import os
import sys

# Ensure repository root is in sys.path when executed directly
if __package__ is None or __package__ == "":
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from ams_optimizer.core.optimizer import AMSOptimizer
    from ams_optimizer.core.netlist_generator import StructuralNetlistGenerator
else:
    from .core.optimizer import AMSOptimizer
    from .core.netlist_generator import StructuralNetlistGenerator


def main():
    parser = argparse.ArgumentParser(
        description="AMS Digital Optimizer (Multi-Level DAG Truth Table & CMOS Technology Mapper)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("verilog_file", help="Path to input Verilog RTL file (.v)")
    parser.add_argument("-o", "--output-va", help="Path to output Cadence Verilog-A file (.va)")
    parser.add_argument("--save-netlist", help="Path to output structural gate netlist in JSON format (.json)")
    parser.add_argument("--save-skill", help="Path to output Cadence Virtuoso SKILL schematic script (.il)")
    parser.add_argument("--save-report", help="Path to save BOM Markdown report (.md)")
    parser.add_argument("--vdd", type=float, default=1.8, help="Supply voltage in Volts (default: 1.8)")
    parser.add_argument("--vth", type=float, default=0.9, help="Logic threshold voltage in Volts (default: 0.9)")
    parser.add_argument("--lib", default="tsmcN65", help="Target Cadence standard cell library name (default: tsmcN65)")

    args = parser.parse_args()

    if not os.path.exists(args.verilog_file):
        print(f"Error: File not found: {args.verilog_file}", file=sys.stderr)
        sys.exit(1)

    with open(args.verilog_file, "r") as f:
        verilog_code = f.read()

    print("=" * 78)
    print("AMS Digital Optimizer (Multi-Level DAG Synthesis Engine)")
    print(f"Input RTL: {args.verilog_file}")
    print(f"Voltage: VDD={args.vdd}V, VTH={args.vth}V, Library: {args.lib}")
    print("=" * 78)

    optimizer = AMSOptimizer(supply_voltage=args.vdd, threshold_voltage=args.vth, skill_lib=args.lib)
    result = optimizer.run(verilog_code)

    print("\n--- Multi-Level Intermediate Conditions & Next-State Gates ---")
    for node_name in result.dag.topo_order:
        mn = result.mapped_nodes.get(node_name)
        if mn:
            print(f"  {node_name:<24} = {mn.expression}")

    print("\n--- Schematic Bill of Materials (BOM) ---")
    for g, cnt in sorted(result.gate_breakdown.items()):
        print(f"  {g:<10}: {cnt:>3} cells")
    print("-" * 35)
    print(f"  TOTAL GATES           : {result.total_gates} cells")
    print(f"  INVERTER EQUIVALENTS  : {result.total_inverter_equivalents:.1f} inverters (1 GE = 1 Inverter = 2T)")
    print(f"  EST. TRANSISTORS      : ~{result.total_transistors} transistors")
    print("=" * 78)

    if args.output_va:
        with open(args.output_va, "w") as f:
            f.write(result.veriloga_code)
        print(f"\n[OK] Saved Cadence Verilog-A model to: {args.output_va}")
    else:
        print("\n--- Generated Verilog-A Preview (use -o <file.va> to save) ---")
        lines = result.veriloga_code.splitlines()
        preview = "\n".join(lines[:45])
        print(preview)
        if len(lines) > 45:
            print(f"... [{len(lines)-45} more lines omitted, use -o to save full file]")

    if args.save_netlist:
        json_netlist = StructuralNetlistGenerator.to_json_str(result.structural_netlist)
        with open(args.save_netlist, "w") as f:
            f.write(json_netlist)
        print(f"[OK] Saved Structural Gate Netlist JSON to: {args.save_netlist}")

    if args.save_skill:
        with open(args.save_skill, "w") as f:
            f.write(result.skill_code)
        print(f"[OK] Saved Virtuoso SKILL schematic script to: {args.save_skill}")

    if args.save_report:
        with open(args.save_report, "w") as f:
            f.write(result.bom_report)
        print(f"[OK] Saved BOM report to: {args.save_report}")


if __name__ == "__main__":
    main()
