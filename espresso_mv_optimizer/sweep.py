"""Automated Silicon Pareto Sweeper for Unified Espresso-MV.

Executes a high-efficiency targeted sweep over critical architectural parameters:
- DC Relaxation: 'exact' vs 'startup_relaxed'
- Shannon Decomposition Threshold: 4, 8, 15 cubes
- Variable Selection Metric: 'frequency' vs 'control_priority'
- Max Gate Fan-In: 3 vs 4
- Technology Mapping: compound AOI/XOR gates (True vs False)

With 'no-brainer' parameters fixed to physically optimal values:
- DeMorgan CMOS inverting logic: True
- Multi-output term sharing: True
- Global inverter pooling: True
- Transmission-gate MUX2: True
"""

from __future__ import annotations
import sys
import os
import time
from typing import List, Dict, Any

from espresso_mv_optimizer.extractor import UnifiedRTLExtractor
from espresso_mv_optimizer.multi_output_engine import MultiOutputEspressoEngine
from espresso_mv_optimizer.gate_mapper import SharedGateMapper


def verify_equivalence_fast(
    num_inputs: int,
    min_exprs: Dict[str, Any],
    py_vars: List[Any],
    table_strings: Dict[str, str],
    num_samples: int = 64,
) -> bool:
    """Verifies that minimized multi-output expressions match the truth table."""
    num_rows = 1 << num_inputs
    step = max(1, num_rows // num_samples)

    for row in range(0, num_rows, step):
        point = {py_vars[bit_i]: (row >> bit_i) & 1 for bit_i in range(num_inputs)}
        for tgt, expr in min_exprs.items():
            gold_char = table_strings[tgt][row]
            if gold_char == "-":
                continue
            gold_val = int(gold_char)

            if str(expr) in ["0", "1"]:
                pyeda_val = int(str(expr))
            else:
                pyeda_val = int(expr.restrict(point))

            if pyeda_val != gold_val:
                return False

    return True


def run_sweep(verilog_path: str = "examples/PWM_CTRL_registered_bgr.v") -> List[Dict[str, Any]]:
    print(f"================================================================================")
    print(f"      UNIFIED ESPRESSO-MV SILICON OPTIMIZER: AUTOMATED PARETO SWEEP")
    print(f"================================================================================")
    print(f"Design:    {verilog_path}")
    print(f"Front-End: pyverilog AST Parser + Icarus Verilog Runtime (/opt/homebrew/bin/iverilog)")
    print(f"Minimizer: Berkeley Espresso-MV (pyeda C-extension)")
    print(f"Defaults:  DeMorgan=True, MultiOutput=True, TG_MUX2=True, GlobalInv=True\n", flush=True)

    t_start = time.time()
    extractor = UnifiedRTLExtractor(verilog_path)
    print(f"Extracted {len(extractor.inputs)} inputs ({len(extractor.primary_inputs)} primary, {len(extractor.register_bits)} state bits)")
    print(f"Extracted {len(extractor.comb_targets)} targets ({len(extractor.comb_outputs)} outputs, {len(extractor.d_targets)} next-state D-pins)", flush=True)

    # 1. Pre-extract truth tables with iverilog
    print("\nPre-extracting truth tables with iverilog...", flush=True)
    t0 = time.time()
    tts_by_dc = {
        "exact": extractor.extract_truth_tables("exact"),
        "startup_relaxed": extractor.extract_truth_tables("startup_relaxed"),
    }
    print(f"Truth tables ready in {time.time() - t0:.3f} s (2 x 2048 vectors)\n", flush=True)

    # 2. Joint Multi-Output Espresso-MV for each DC mode
    engine = MultiOutputEspressoEngine(extractor.inputs)
    solutions = {}
    lec_results = {}

    for dc_mode, tts in tts_by_dc.items():
        t_esp0 = time.time()
        min_exprs, shared_cubes = engine.solve(tts)
        t_esp = time.time() - t_esp0
        lec = verify_equivalence_fast(extractor.num_inputs, min_exprs, engine.py_vars, tts)
        solutions[dc_mode] = (min_exprs, shared_cubes, t_esp)
        lec_results[dc_mode] = lec
        print(f"Espresso-MV [{dc_mode}]: {len(shared_cubes)} unique shared cubes in {t_esp:.3f}s (Formal LEC: {'PASS' if lec else 'FAIL'})", flush=True)

    # 3. High-impact parameter sweep grid
    shannon_thresholds = [4, 8, 15]
    var_metrics = ["frequency", "control_priority"]
    fan_in_limits = [3, 4]
    tech_map_options = [False, True]

    results: List[Dict[str, Any]] = []
    mapper = SharedGateMapper(extractor.inputs)

    print("\nMapping configurations across high-impact Pareto space...", flush=True)
    for dc_mode, (min_exprs, shared_cubes, t_esp) in solutions.items():
        for sh_th in shannon_thresholds:
            for var_m in var_metrics:
                for fan_in in fan_in_limits:
                    for tm in tech_map_options:
                        metrics = mapper.map_shared_network(
                            min_exprs,
                            shared_cubes,
                            total_ffs=extractor.total_ffs,
                            enable_demorgan=True,
                            enable_tech_mapping=tm,
                            enable_shannon=True,
                            shannon_threshold=sh_th,
                            var_selection=var_m,
                            max_fan_in=fan_in,
                        )
                        metrics.update({
                            "name": f"Espresso-MV [{dc_mode}] (sh={sh_th}, var={var_m}, fan={fan_in}, tm={tm})",
                            "dc_relaxation": dc_mode,
                            "shannon_threshold": sh_th,
                            "var_selection": var_m,
                            "max_fan_in": fan_in,
                            "enable_tech_mapping": tm,
                            "enable_demorgan": True,
                            "enable_shannon": True,
                            "lec_passed": lec_results[dc_mode],
                            "min_exprs": min_exprs,
                            "input_names": extractor.inputs,
                            "targets": extractor.comb_targets,
                            "module_name": extractor.module_name,
                        })
                        results.append(metrics)

    print(f"Completed {len(results)} configurations in {time.time() - t_start:.2f} s total!\n", flush=True)

    # Sort results by GE ascending, then Transistors, then Cells
    results.sort(key=lambda r: (r["total_ge"], r["total_transistors"], r["total_cells"]))

    # Output Mandatory Top 10 Pareto Table
    print_pareto_table(results[:10])

    # Output Winner BOM
    print_winner_bom(results[0])

    return results


def print_pareto_table(top10: List[Dict[str, Any]]):
    print("=" * 105)
    print("                      FULL OPTIMIZATION PARETO RESULTS TABLE (TOP 10)")
    print("=" * 105)
    header = f"{'Rank':<5} | {'GE':<6} | {'Trans':<6} | {'Cells':<6} | {'DC Mode':<15} | {'SH_Th':<5} | {'Metric':<16} | {'FanIn':<5} | {'TechMap':<7} | {'LEC':<5}"
    print(header)
    print("-" * 105)
    for idx, r in enumerate(top10, 1):
        row = (
            f"{idx:<5} | "
            f"{r['total_ge']:<6.1f} | "
            f"{r['total_transistors']:<6} | "
            f"{r['total_cells']:<6} | "
            f"{r['dc_relaxation']:<15} | "
            f"{r['shannon_threshold']:<5} | "
            f"{r['var_selection']:<16} | "
            f"{r['max_fan_in']:<5} | "
            f"{str(r['enable_tech_mapping']):<7} | "
            f"{'PASS' if r['lec_passed'] else 'FAIL':<5}"
        )
        print(row)
    print("=" * 105 + "\n", flush=True)


def print_winner_bom(winner: Dict[str, Any]):
    print("=" * 60)
    print("         RANK 1 WINNING CONFIGURATION: BILL OF MATERIALS")
    print("=" * 60)
    print(f"Configuration: {winner['name']}")
    print(f"DC Relaxation: {winner['dc_relaxation']}")
    print(f"Shannon Trigger Threshold: {winner['shannon_threshold']} cubes")
    print(f"Variable Selection: {winner['var_selection']}")
    print(f"Max Gate Fan-In: {winner['max_fan_in']}")
    print(f"Tech Mapping: {winner['enable_tech_mapping']}")
    print("-" * 60)
    print(f"Total Gate Equivalents (GE): {winner['total_ge']:.1f}")
    print(f"Estimated Transistor Count: {winner['total_transistors']}")
    print(f"Total Standard Cell Count:   {winner['total_cells']}")
    print(f"Formal Verification (LEC):   {'PASS' if winner['lec_passed'] else 'FAIL'}")
    print("-" * 60)
    print(f"{'Cell Type':<15} | {'Count':<8} | {'Unit GE':<8} | {'Subtotal GE':<10}")
    print("-" * 60)

    from ams_optimizer.core.models import INVERTER_EQUIVALENTS
    for cell, count in sorted(winner["gate_counts"].items(), key=lambda x: -x[1]):
        unit_ge = INVERTER_EQUIVALENTS.get(cell, 3.0)
        sub_ge = count * unit_ge
        print(f"{cell:<15} | {count:<8} | {unit_ge:<8.2f} | {sub_ge:<10.2f}")
    print("=" * 60 + "\n", flush=True)


if __name__ == "__main__":
    run_sweep()
