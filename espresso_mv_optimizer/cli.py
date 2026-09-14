"""Command Line Interface for the Unified Espresso-MV Silicon Optimizer.

Usage:
  python3 -m espresso_mv_optimizer.cli examples/PWM_CTRL.v
  python3 -m espresso_mv_optimizer.cli examples/PWM_CTRL.v --emit-va examples/PWM_CTRL.va --emit-verilog examples/PWM_CTRL_netlist.v
"""

from __future__ import annotations
import argparse
import os
import sys

from espresso_mv_optimizer.sweep import run_sweep
from espresso_mv_optimizer.veriloga_emitter import UnifiedVerilogAEmitter
from espresso_mv_optimizer.verilog_emitter import UnifiedVerilogNetlistEmitter
from espresso_mv_optimizer.schematic_emitter import generate_schematic_guide_for_pwm_ctrl


def main():
    parser = argparse.ArgumentParser(
        description="Unified Espresso-MV Silicon Logic Optimizer & Standard Cell Synthesizer"
    )
    parser.add_argument(
        "verilog",
        nargs="?",
        default="examples/PWM_CTRL.v",
        help="Path to input Verilog RTL source file (default: examples/PWM_CTRL.v)",
    )
    parser.add_argument(
        "--emit-va",
        metavar="PATH",
        nargs="?",
        const="examples/PWM_CTRL.va",
        help="Emit Cadence Spectre-compliant Verilog-A model for Rank 1 design",
    )
    parser.add_argument(
        "--emit-verilog",
        metavar="PATH",
        nargs="?",
        const="examples/PWM_CTRL_netlist.v",
        help="Emit synthesizable gate-level structural Verilog netlist for Rank 1 design",
    )
    parser.add_argument(
        "--emit-schematic-md",
        metavar="PATH",
        nargs="?",
        const="QUICK_PROTOTYPING_SCHEMATIC.md",
        help="Emit Cadence Virtuoso quick prototyping schematic guide with 1-line terminal labels",
    )


    args = parser.parse_args()

    if not os.path.exists(args.verilog):
        print(f"Error: Input Verilog file not found: {args.verilog}", file=sys.stderr)
        sys.exit(1)

    # Run the high-impact Pareto sweep
    results = run_sweep(args.verilog)
    winner = results[0]

    # Emit Verilog-A if requested
    if args.emit_va:
        va_emitter = UnifiedVerilogAEmitter(
            module_name=winner["module_name"],
            input_names=winner["input_names"],
            targets=winner["targets"],
            min_exprs=winner["min_exprs"],
            gate_counts=winner["gate_counts"],
            total_ge=winner["total_ge"],
            total_transistors=winner["total_transistors"],
            total_cells=winner["total_cells"],
        )
        va_content = va_emitter.emit()
        os.makedirs(os.path.dirname(os.path.abspath(args.emit_va)), exist_ok=True)
        with open(args.emit_va, "w") as f:
            f.write(va_content)
        print(f"[+] Emitted Cadence Spectre Verilog-A: {args.emit_va} ({len(va_content)} bytes)")

    # Emit Gate-Level Verilog if requested
    if args.emit_verilog:
        v_emitter = UnifiedVerilogNetlistEmitter(
            module_name=winner["module_name"],
            input_names=winner["input_names"],
            targets=winner["targets"],
            min_exprs=winner["min_exprs"],
            gate_counts=winner["gate_counts"],
            total_ge=winner["total_ge"],
            total_transistors=winner["total_transistors"],
            total_cells=winner["total_cells"],
        )
        v_content = v_emitter.emit()
        os.makedirs(os.path.dirname(os.path.abspath(args.emit_verilog)), exist_ok=True)
        with open(args.emit_verilog, "w") as f:
            f.write(v_content)
        print(f"[+] Emitted Gate-Level Structural Verilog: {args.emit_verilog} ({len(v_content)} bytes)")

    # Emit Schematic Prototyping Guide if requested
    if args.emit_schematic_md:
        sch_content = generate_schematic_guide_for_pwm_ctrl(args.emit_schematic_md)
        print(f"[+] Emitted Cadence Virtuoso Prototyping Guide: {args.emit_schematic_md} ({len(sch_content)} bytes)")


if __name__ == "__main__":

    main()
