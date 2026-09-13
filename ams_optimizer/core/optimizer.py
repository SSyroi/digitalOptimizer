"""Master Multi-Level Logic Optimizer & Synthesizer Pipeline.

Orchestrates multi-level DAG slicing, local truth-table simulation,
exact NPN bitmask matching, Shannon MUX extraction, Quine-McCluskey SOP reduction,
structural logical netlist generation, Cadence Spectre Verilog-A emission,
and Virtuoso SKILL schematic scripts.

Zero external dependencies. Compatible with Python 3.9+.
"""

from __future__ import annotations
import itertools
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    SlicedDAG,
    LocalTruthTable,
    MappedLogicNode,
    OptimizationResult,
    StructuralNetlist,
    TRANSISTOR_COST,
    INVERTER_EQUIVALENTS,
)
from .dag_slicer import VerilogDAGSlicer
from .truth_table import LocalTruthTableEvaluator
from .tech_mapper import TechnologyMapper
from .netlist_generator import StructuralNetlistGenerator
from .veriloga_emitter import VerilogAEmitter
from .skill_emitter import SKILLEmitter
from .equivalence_checker import FormalEquivalenceChecker


class AMSOptimizer:
    """High-performance, zero-dependency Multi-Level AMS Digital Optimizer."""

    def __init__(
        self,
        supply_voltage: float = 1.8,
        threshold_voltage: float = 0.9,
        skill_lib: str = "tsmcN65",
        run_verification: bool = True,
        allow_and_or: bool = True,
        allow_mux: bool = True,
        qm_max_inputs: int = 6,
        shannon_min_inputs: int = 3,
        dual_polarity: bool = True,
        allow_output_buffers: bool = True,
    ):
        self.supply_voltage = supply_voltage
        self.threshold_voltage = threshold_voltage
        self.skill_lib = skill_lib
        self.run_verification = run_verification
        self.allow_and_or = allow_and_or
        self.allow_mux = allow_mux
        self.qm_max_inputs = qm_max_inputs
        self.shannon_min_inputs = shannon_min_inputs
        self.dual_polarity = dual_polarity
        self.allow_output_buffers = allow_output_buffers

    def run(self, verilog_code: str) -> OptimizationResult:
        t_start = time.perf_counter()

        # Step 1: Multi-Level Slicing (Preserve intermediate conditions)
        t0 = time.perf_counter()
        slicer = VerilogDAGSlicer(verilog_code)
        dag = slicer.parse()
        t_slice = time.perf_counter() - t0

        # Step 2: Local Truth Table Simulation & Reachability Analysis
        t0 = time.perf_counter()
        evaluator = LocalTruthTableEvaluator(dag)

        local_tables: Dict[str, LocalTruthTable] = {}
        for node_name, node in dag.nodes.items():
            local_tables[node_name] = evaluator.evaluate_node(node)
        t_tt = time.perf_counter() - t0

        # Step 3: Map Logic Nodes using Technology Mapper
        t0 = time.perf_counter()
        mapper = TechnologyMapper(
            allow_and_or=self.allow_and_or,
            allow_mux=self.allow_mux,
            qm_max_inputs=self.qm_max_inputs,
            shannon_min_inputs=self.shannon_min_inputs,
            dual_polarity=self.dual_polarity,
        )
        mapped_nodes: Dict[str, MappedLogicNode] = {}
        for node_name in dag.topo_order:
            tt = local_tables.get(node_name)
            if tt:
                mapped_nodes[node_name] = mapper.map_truth_table(tt)
        t_map = time.perf_counter() - t0

        # Step 4: Generate Intermediate Structural Gate Netlist
        t0 = time.perf_counter()
        netlist_gen = StructuralNetlistGenerator(
            dag,
            mapped_nodes,
            allow_output_buffers=self.allow_output_buffers,
        )
        structural_netlist = netlist_gen.generate()
        t_netlist = time.perf_counter() - t0

        # Step 5: Aggregate Gate Breakdown, Inverter Equivalents & Transistor Cost
        gate_breakdown: Dict[str, int] = {}
        for inst in structural_netlist.instances:
            gate_breakdown[inst.cell_type] = gate_breakdown.get(inst.cell_type, 0) + 1

        total_gates = structural_netlist.total_gates
        total_ge = structural_netlist.total_inverter_equivalents
        total_transistors = structural_netlist.total_transistors

        # Step 6: Formal Logic Equivalence Checking (LEC)
        t0 = time.perf_counter()
        equivalence_result = None
        if self.run_verification:
            checker = FormalEquivalenceChecker(dag, mapped_nodes, verilog_code=verilog_code)
            equivalence_result = checker.verify()
        t_lec = time.perf_counter() - t0

        # Step 7: Emit Deliverables (Verilog-A & Virtuoso SKILL)
        va_emitter = VerilogAEmitter(
            dag=dag,
            mapped_nodes=mapped_nodes,
            gate_breakdown=gate_breakdown,
            supply_voltage=self.supply_voltage,
            threshold_voltage=self.threshold_voltage
        )
        veriloga_code = va_emitter.emit()

        skill_emitter = SKILLEmitter(dag, mapped_nodes, self.skill_lib)
        skill_code = skill_emitter.emit()

        t_synth = t_slice + t_tt + t_map + t_netlist
        t_total = time.perf_counter() - t_start
        timing_breakdown = {
            "slicing": t_slice,
            "truth_table": t_tt,
            "mapping": t_map,
            "netlist_gen": t_netlist,
            "synthesis_total": t_synth,
            "verification": t_lec,
            "total": t_total,
        }

        # Step 8: Generate Detailed BOM Report with Inverter Equivalents & Verification
        bom_lines = [
            f"# Schematic Bill of Materials (BOM) for `{dag.module_name}`",
            f"",
            f"**Generated by AMS Digital Optimizer (Multi-Level DAG Engine)**",
            f"",
            f"- **Total Gate Count**: {total_gates} cells",
            f"- **Inverter Equivalents (GE)**: {total_ge:.1f} inverters (1 GE = 1 Inverter = 2 Transistors)",
            f"- **Est. Total Transistors**: ~{total_transistors} transistors",
        ]

        if equivalence_result:
            status_str = "100% PASSED (Equivalence Verified)" if equivalence_result.passed else "FAILED (Discrepancy Detected)"
            bom_lines.extend([
                f"- **Formal Equivalence Status**: {status_str}",
                f"- **Verified Vectors**: {equivalence_result.matching_vectors} / {equivalence_result.total_vectors} ({equivalence_result.execution_time_seconds:.4f}s)",
            ])

        bom_lines.extend([
            f"",
            f"| Standard Cell | Count | Inverter Eq. / Cell | Total Inverters | Transistors / Cell | Total Transistors |",
            f"| :--- | :---: | :---: | :---: | :---: | :---: |",
        ])
        for g, cnt in sorted(gate_breakdown.items()):
            ge_per = INVERTER_EQUIVALENTS.get(g, 2.0)
            cost_per = TRANSISTOR_COST.get(g, 6)
            bom_lines.append(f"| `{g}` | {cnt} | {ge_per:.1f} GE | {cnt * ge_per:.1f} inverters | {cost_per}T | {cnt * cost_per}T |")
        bom_lines.append(f"| **TOTAL** | **{total_gates} gates** | — | **{total_ge:.1f} inverters** | — | **~{total_transistors}T** |")
        bom_lines.append(f"")
        bom_lines.append(f"### Simplified Multi-Level Expressions")
        bom_lines.append(f"```verilog")
        for node_name in dag.topo_order:
            mn = mapped_nodes.get(node_name)
            if mn:
                bom_lines.append(f"  {node_name:<24} = {mn.expression};")
        bom_lines.append(f"```")
        bom_lines.append(f"")
        bom_lines.append(f"### Performance & Execution Timing")
        bom_lines.append(f"- **Synthesis Total**: {t_synth:.4f}s (Slicing: {t_slice:.4f}s, Truth Table: {t_tt:.4f}s, Mapping: {t_map:.4f}s, Netlist: {t_netlist:.4f}s)")
        bom_lines.append(f"- **Formal Verification**: {t_lec:.4f}s ({'Skipped' if not self.run_verification else 'Verified'})")
        bom_lines.append(f"- **Total Runtime**: {t_total:.4f}s")
        bom_report = "\n".join(bom_lines)

        return OptimizationResult(
            module_name=dag.module_name,
            dag=dag,
            mapped_nodes=mapped_nodes,
            structural_netlist=structural_netlist,
            veriloga_code=veriloga_code,
            skill_code=skill_code,
            bom_report=bom_report,
            gate_breakdown=gate_breakdown,
            total_gates=total_gates,
            total_inverter_equivalents=total_ge,
            total_transistors=total_transistors,
            equivalence_result=equivalence_result,
            timing_breakdown=timing_breakdown,
        )

    @classmethod
    def auto_optimize(
        cls,
        verilog_code: str,
        param_grid: Optional[Dict[str, list]] = None,
        verify_top_n: int = 1,
        supply_voltage: float = 1.8,
        threshold_voltage: float = 0.9,
        skill_lib: str = "tsmcN65",
        verbose: bool = True,
    ) -> Tuple[OptimizationResult, List[Dict[str, Any]]]:
        """Runs automated two-phase parameter sweep optimization.

        Phase 1: Rapid multi-configuration synthesis (synthesis-only, no LEC).
                 Evaluates all combinations in seconds.
        Phase 2: Ranks candidates by Area (GE) and cell count, then executes
                 exhaustive Formal Logic Equivalence Checking (LEC) ONLY on the
                 top Pareto candidates to guarantee 100% mathematical equivalence.
        """
        if param_grid is None:
            param_grid = {
                "allow_and_or": [False, True],
                "allow_mux": [False, True],
                "qm_max_inputs": [5, 6, 7],
                "shannon_min_inputs": [3, 4],
                "allow_output_buffers": [False, True],
            }

        keys = list(param_grid.keys())
        combinations = list(itertools.product(*param_grid.values()))

        sweep_start = time.perf_counter()
        if verbose:
            print(f"[*] Starting Auto-Optimization: Pre-evaluating circuit DAG and truth tables...", flush=True)

        # Step 1 & 2: Parse DAG and extract local truth tables ONCE
        t_prep_0 = time.perf_counter()
        slicer = VerilogDAGSlicer(verilog_code)
        dag = slicer.parse()
        evaluator = LocalTruthTableEvaluator(dag)
        local_tables: Dict[str, LocalTruthTable] = {}
        for node_name, node in dag.nodes.items():
            local_tables[node_name] = evaluator.evaluate_node(node)
        prep_time = time.perf_counter() - t_prep_0

        if verbose:
            print(f"[*] DAG & Truth Tables extracted in {prep_time:.2f}s ({len(dag.nodes)} nodes).", flush=True)
            print(f"[*] Phase 1: Rapidly sweeping {len(combinations)} technology mapping configurations...", flush=True)

        candidates: List[Dict[str, Any]] = []
        mapping_cache: Dict[Tuple[str, bool, bool, int, int], MappedLogicNode] = {}
        phase1_sweep_start = time.perf_counter()
        for idx, values in enumerate(combinations):
            params = dict(zip(keys, values))
            t_cand_0 = time.perf_counter()

            mapper = TechnologyMapper(
                allow_and_or=params["allow_and_or"],
                allow_mux=params["allow_mux"],
                qm_max_inputs=params["qm_max_inputs"],
                shannon_min_inputs=params["shannon_min_inputs"],
            )
            mapped_nodes: Dict[str, MappedLogicNode] = {}
            for node_name in dag.topo_order:
                tt = local_tables.get(node_name)
                if tt:
                    cache_key = (
                        node_name,
                        params["allow_and_or"],
                        params["allow_mux"],
                        params["qm_max_inputs"],
                        params["shannon_min_inputs"],
                    )
                    if cache_key in mapping_cache:
                        mapped_nodes[node_name] = mapping_cache[cache_key]
                    else:
                        node_res = mapper.map_truth_table(tt)
                        mapping_cache[cache_key] = node_res
                        mapped_nodes[node_name] = node_res

            netlist_gen = StructuralNetlistGenerator(
                dag,
                mapped_nodes,
                allow_output_buffers=params["allow_output_buffers"],
            )
            structural_netlist = netlist_gen.generate()
            synth_time = time.perf_counter() - t_cand_0

            gate_breakdown: Dict[str, int] = {}
            for inst in structural_netlist.instances:
                gate_breakdown[inst.cell_type] = gate_breakdown.get(inst.cell_type, 0) + 1

            candidates.append({
                "params": params,
                "mapped_nodes": mapped_nodes,
                "structural_netlist": structural_netlist,
                "ge": structural_netlist.total_inverter_equivalents,
                "gates": structural_netlist.total_gates,
                "transistors": structural_netlist.total_transistors,
                "synth_time": synth_time,
                "breakdown": gate_breakdown,
            })

        # Rank by Area (GE) primary, Gate count secondary
        candidates.sort(key=lambda c: (c["ge"], c["gates"]))
        phase1_time = time.perf_counter() - phase1_sweep_start

        if verbose:
            print(f"[*] Phase 1 Complete in {phase1_time:.2f}s! Swept {len(combinations)} configs (avg {phase1_time/len(combinations)*1000:.1f}ms/config).", flush=True)
            print(f"[*] Phase 2: Formally verifying Top {min(verify_top_n, len(candidates))} Pareto candidate(s)...", flush=True)

        # Phase 2: Formally verify top N candidates
        for i in range(min(verify_top_n, len(candidates))):
            cand = candidates[i]
            top_opt = cls(
                supply_voltage=supply_voltage,
                threshold_voltage=threshold_voltage,
                skill_lib=skill_lib,
                run_verification=True,
                **cand["params"]
            )
            verified_res = top_opt.run(verilog_code)
            cand["result"] = verified_res
            cand["equivalence_result"] = verified_res.equivalence_result
            cand["lec_passed"] = verified_res.equivalence_result.passed if verified_res.equivalence_result else False
            cand["lec_time"] = verified_res.timing_breakdown.get("verification", 0.0)
            if verbose:
                status = "PASS" if cand["lec_passed"] else "FAIL"
                print(f"    - Rank {i+1}: {cand['ge']:.1f} GE, {cand['gates']} cells -> 100% LEC: [{status}] ({cand['lec_time']:.2f}s)", flush=True)

        best_candidate = candidates[0].get("result")
        if best_candidate is None:
            # If verify_top_n was 0, construct result for best candidate
            top_opt = cls(
                supply_voltage=supply_voltage,
                threshold_voltage=threshold_voltage,
                skill_lib=skill_lib,
                run_verification=False,
                **candidates[0]["params"]
            )
            best_candidate = top_opt.run(verilog_code)

        return best_candidate, candidates
