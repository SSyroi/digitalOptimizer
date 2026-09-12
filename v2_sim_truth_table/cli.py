"""Command-Line Interface for Simulation-Driven Truth Table Optimizer.

Pure standard library (argparse, sys, os). Compatible with Python 3.9+.
Zero external dependencies.
"""

from __future__ import annotations
import argparse
import os
import sys

# Ensure parent directory is in sys.path when executed directly as a script
if __package__ is None or __package__ == "":
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from v2_sim_truth_table.optimizer import SimTruthTableOptimizer
else:
    from .optimizer import SimTruthTableOptimizer



def main():
    parser = argparse.ArgumentParser(
        description="Simulation-Driven Truth Table Optimizer & Synthesizer (Python 3.9+ Compatible)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("verilog_file", help="Path to input Verilog RTL file (.v)")
    parser.add_argument("-o", "--output-va", help="Path to output Cadence Verilog-A file (.va)")
    parser.add_argument("--vdd", type=float, default=1.8, help="Supply voltage in Volts (default: 1.8)")
    parser.add_argument("--vth", type=float, default=0.9, help="Logic threshold voltage in Volts (default: 0.9)")
    parser.add_argument("--save-report", help="Path to save BOM Markdown report (.md)")

    args = parser.parse_args()

    if not os.path.exists(args.verilog_file):
        print(f"Error: File not found: {args.verilog_file}", file=sys.stderr)
        sys.exit(1)

    with open(args.verilog_file, "r") as f:
        verilog_code = f.read()

    print("=" * 78)
    print("AMS Digital Optimizer (v2 Simulation-Driven Truth Table Engine)")
    print(f"Input RTL: {args.verilog_file}")
    print(f"Voltage: VDD={args.vdd}V, VTH={args.vth}V")
    print("=" * 78)

    optimizer = SimTruthTableOptimizer(supply_voltage=args.vdd, threshold_voltage=args.vth)
    result = optimizer.run(verilog_code)

    print("\n--- Simplified Next-State & Output Gate Expressions ---")
    for target, cone in sorted(result.mapped_cones.items()):
        print(f"  {target:<20} = {cone.nested_expression}")

    print("\n--- Schematic Bill of Materials (BOM) ---")
    for g, cnt in sorted(result.gate_breakdown.items()):
        print(f"  {g:<10}: {cnt:>3} cells")
    print("-" * 35)
    print(f"  TOTAL GATES: {result.total_gates}")
    print(f"  EST. TRANSISTORS: ~{result.total_transistors}")
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

    if args.save_report:
        with open(args.save_report, "w") as f:
            f.write(result.bom_report)
        print(f"[OK] Saved BOM report to: {args.save_report}")


if __name__ == "__main__":
    main()
