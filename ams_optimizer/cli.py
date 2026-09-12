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
    from ams_optimizer.core.stage_verifier import StageByStageVerifier
else:
    from .core.optimizer import AMSOptimizer
    from .core.netlist_generator import StructuralNetlistGenerator
    from .core.stage_verifier import StageByStageVerifier


def main():
    parser = argparse.ArgumentParser(
        description="AMS Digital Optimizer (Multi-Level DAG Truth Table & CMOS Technology Mapper)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("verilog_file", help="Path to input Verilog RTL file (.v)")
    parser.add_argument("-o", "--output-va", help="Path to output Cadence Verilog-A file (.va)")
    parser.add_argument("--save-netlist", help="Path to output structural gate netlist in JSON format (.json)")
    parser.add_argument("--save-skill", help="Path to output Cadence Virtuoso SKILL schematic script (.il)")
    parser.add_argument("--save-report", help="Path to save BOM report (.txt / .md)")
    parser.add_argument("--verify", dest="verify", action="store_true", default=True, help="Run Formal Logic Equivalence Checking (LEC) (default: enabled)")
    parser.add_argument("--no-verify", dest="verify", action="store_false", help="Disable Formal Logic Equivalence Checking")
    parser.add_argument("--stage-verify", action="store_true", help="Run Stage-by-Stage verification matrix across all transformation stages")
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

    optimizer = AMSOptimizer(
        supply_voltage=args.vdd,
        threshold_voltage=args.vth,
        skill_lib=args.lib,
        run_verification=args.verify
    )
    result = optimizer.run(verilog_code)

    print("\n--- Multi-Level Intermediate Conditions & Next-State Gates ---")
    for node_name in result.dag.topo_order:
        mn = result.mapped_nodes.get(node_name)
        if mn:
            print(f"  {node_name:<24} = {mn.expression}")

    if result.equivalence_result:
        eq = result.equivalence_result
        status_sym = "[PASS]" if eq.passed else "[FAIL]"
        print(f"\n--- Formal Logic Equivalence Checking (LEC) ---")
        print(f"  Status                : {status_sym} {'100% MATCH (Equivalence Verified)' if eq.passed else 'MISMATCH DETECTED'}")
        print(f"  Stimulus Vectors      : {eq.matching_vectors} / {eq.total_vectors} matched ({eq.execution_time_seconds:.4f}s)")
        print(f"  Signals Verified      : {len(eq.verified_signals)} signals (Primary Outputs + Register Next-States)")
        if eq.mismatches:
            print(f"  WARNING: {len(eq.mismatches)} discrepancies detected! First mismatch:")
            print(f"    Signal: {eq.mismatches[0]['signal']}, Golden={eq.mismatches[0]['golden_val']}, Mapped={eq.mismatches[0]['optimized_val']}")
            print(f"    Inputs: {eq.mismatches[0]['inputs']}")

    if args.stage_verify:
        verifier = StageByStageVerifier(verilog_code, result.dag, result.mapped_nodes)
        stage_rep = verifier.run_verification()
        status_sym = "[PASS]" if stage_rep.passed else "[FAIL]"
        print(f"\n--- Stage-by-Stage Logic Transformation Verification ---")
        print(f"  Overall Status        : {status_sym} {'100% MATCH Across All Transformation Stages' if stage_rep.passed else 'MISMATCH DETECTED'}")
        print(f"  Stimulus Vectors      : {stage_rep.total_vectors} combinations simulated (Flip-Flops Cut, Stage 0 Reference)")
        print(f"  Execution Time        : {stage_rep.execution_time_seconds:.4f}s")
        print(f"  Signals Verified      : {len(stage_rep.signals_checked)} signals: {', '.join(stage_rep.signals_checked[:6])}{'...' if len(stage_rep.signals_checked) > 6 else ''}")
        print(f"  Transformation Stages Matrix:")
        print(f"    - Stage 0: Golden RTL Reference       : {stage_rep.total_vectors} / {stage_rep.total_vectors} vectors (Baseline)")
        for st_name in stage_rep.stages_tested[1:]:
            cnt = stage_rep.stage_match_counts.get(st_name, 0)
            pct = (cnt / stage_rep.total_vectors * 100) if stage_rep.total_vectors > 0 else 100.0
            st_sym = "[OK]" if cnt == stage_rep.total_vectors else "[FAIL]"
            print(f"    - {st_name:<36}: {cnt:>5} / {stage_rep.total_vectors} ({pct:5.1f}%) {st_sym}")

        if stage_rep.mismatches:
            print(f"\n  WARNING: {len(stage_rep.mismatches)} discrepancies detected across stages! First mismatch:")
            m = stage_rep.mismatches[0]
            print(f"    Stage: {m.stage_name} (Index {m.stage_index})")
            print(f"    Signal: {m.signal_name}, Vector #{m.vector_index}")
            print(f"    Golden Value = {m.golden_val}, Stage Value = {m.stage_val}")
            print(f"    Stimulus: {m.stimulus}")

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
