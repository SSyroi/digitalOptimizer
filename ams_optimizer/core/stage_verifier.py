"""Stage-by-Stage Logic Equivalence & Transformation Verifier.

Tests and compares the arrays of generated values across every transformation stage
directly against the unbiased golden reference (Verilog RTL with flip-flops removed).

Transformation Stages:
- Stage 0: Golden RTL Reference (RTLCombinationalSimulator)
- Stage 1: Multi-Level DAG Slicing (DAGNode.eval_fn)
- Stage 2: Local Truth Tables & Variable Pruning (LocalTruthTable)
- Stage 3: Technology Mapping & Simplification (MappedLogicNode standard cells)
- Stage 4: Cadence Verilog-A Behavioral Model

100% standard library. Zero external dependencies. Compatible with Python 3.9+.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import SlicedDAG, MappedLogicNode, LocalTruthTable
from .rtl_simulator import RTLCombinationalSimulator
from .truth_table import LocalTruthTableEvaluator
from .tech_mapper import TechnologyMapper
from .equivalence_checker import StandardCellEvaluator
from .reachability import FSMReachabilityAnalyzer
from .veriloga_emitter import VerilogAEmitter


@dataclass
class StageMismatch:
    stage_index: int
    stage_name: str
    signal_name: str
    vector_index: int
    stimulus: Dict[str, int]
    golden_val: int
    stage_val: int


@dataclass
class StageVerificationReport:
    passed: bool
    total_vectors: int
    stages_tested: List[str]
    signals_checked: List[str]
    mismatches: List[StageMismatch] = field(default_factory=list)
    stage_match_counts: Dict[str, int] = field(default_factory=dict)
    execution_time_seconds: float = 0.0


class StageByStageVerifier:
    """Verifies and compares output arrays across every logic transformation stage."""

    def __init__(self, verilog_code: str, dag: SlicedDAG, mapped_nodes: Dict[str, MappedLogicNode]):
        self.verilog_code = verilog_code
        self.dag = dag
        self.mapped_nodes = mapped_nodes
        self.rtl_sim = RTLCombinationalSimulator(verilog_code)
        self.tt_evaluator = LocalTruthTableEvaluator(dag)
        self.reachability = FSMReachabilityAnalyzer(dag)

    def run_verification(self, max_vectors: int = 16384) -> StageVerificationReport:
        start_time = time.time()
        stage_names = [
            "Stage 0: Golden RTL Reference",
            "Stage 1: Multi-Level DAG Slicer",
            "Stage 2: Local Truth Tables",
            "Stage 3: Technology-Mapped Gates",
            "Stage 4: Cadence Verilog-A Model",
        ]
        va_emitter = VerilogAEmitter(dag=self.dag, mapped_nodes=self.mapped_nodes)

        # 1. Discover all stimulus variables (Primary Inputs + Register Q bits)
        stimulus_vars, vectors, golden_arrays = self.rtl_sim.simulate_all_vectors(max_vectors=max_vectors)
        total_vectors = len(vectors)
        check_signals = [sig for sig in self.rtl_sim.check_signals if sig in self.dag.nodes or sig in self.mapped_nodes]

        # Discover unreachable states for FSM Don't-Care filtering
        unreachable_states = self.reachability.get_unreachable_states()

        stage_match_counts = {name: 0 for name in stage_names[1:]}
        mismatches: List[StageMismatch] = []

        # Precompute local truth tables once for all DAG nodes
        node_tts = {name: self.tt_evaluator.evaluate_node(node) for name, node in self.dag.nodes.items()}

        # Precompile mapped and Verilog-A expressions for Stage 3 & Stage 4
        compiled_mapped = {name: StandardCellEvaluator.compile_expr(m.expression) for name, m in self.mapped_nodes.items()}
        compiled_va = {}
        for name, m in self.mapped_nodes.items():
            expr_va = va_emitter._format_veriloga_expr(m.expression)
            compiled_va[name] = StandardCellEvaluator.compile_expr(expr_va)

        # 2. Sweep all stimulus vectors across stages
        for vec_idx, stimulus in enumerate(vectors):
            # Check if this vector represents an unreachable FSM state
            is_unreachable = self.reachability.is_unreachable_stimulus(stimulus)
            if not is_unreachable and unreachable_states:
                for reg in self.dag.registers.values():
                    if "state" in reg.name:
                        st_val = 0
                        for b in range(reg.width):
                            st_val |= (stimulus.get(f"{reg.name}[{b}]", 0) << b)
                        if st_val in unreachable_states:
                            is_unreachable = True
                            break

            # -------------------------------------------------------------
            # Stage 1: Evaluate Multi-Level DAG
            # -------------------------------------------------------------
            env_dag = dict(stimulus)
            for node_name in self.dag.topo_order:
                node = self.dag.nodes.get(node_name)
                if node:
                    try:
                        env_dag[node_name] = node.eval_fn(env_dag)
                    except Exception as e:
                        raise RuntimeError(f"DAG node '{node_name}' stage 1 eval_fn failed: {e}") from e

            s1_pass = True
            for sig in check_signals:
                gold_val = golden_arrays[sig][vec_idx]
                dag_val = env_dag.get(sig, 0)
                if gold_val != dag_val:
                    if not is_unreachable:
                        s1_pass = False
                        if len(mismatches) < 20:
                            mismatches.append(StageMismatch(
                                stage_index=1,
                                stage_name="Stage 1: Multi-Level DAG Slicer",
                                signal_name=sig,
                                vector_index=vec_idx,
                                stimulus=stimulus,
                                golden_val=gold_val,
                                stage_val=dag_val
                            ))
            if s1_pass:
                stage_match_counts["Stage 1: Multi-Level DAG Slicer"] += 1

            # -------------------------------------------------------------
            # Stage 2: Evaluate Local Truth Tables
            # -------------------------------------------------------------
            env_tt = dict(stimulus)
            for node_name in self.dag.topo_order:
                tt = node_tts.get(node_name)
                if tt:
                    # Evaluate minterm row index for active inputs
                    row_idx = 0
                    for p_i, p_name in enumerate(tt.inputs):
                        bit_val = env_tt.get(p_name, 0)
                        row_idx |= (bit_val << p_i)
                    env_tt[node_name] = 1 if (row_idx in tt.true_minterms) else 0

            s2_pass = True
            for sig in check_signals:
                gold_val = golden_arrays[sig][vec_idx]
                tt_val = env_tt.get(sig, 0)
                if gold_val != tt_val:
                    if not is_unreachable:
                        s2_pass = False
                        if len(mismatches) < 20:
                            mismatches.append(StageMismatch(
                                stage_index=2,
                                stage_name="Stage 2: Local Truth Tables",
                                signal_name=sig,
                                vector_index=vec_idx,
                                stimulus=stimulus,
                                golden_val=gold_val,
                                stage_val=tt_val
                            ))
            if s2_pass:
                stage_match_counts["Stage 2: Local Truth Tables"] += 1

            # -------------------------------------------------------------
            # Stage 3: Evaluate Technology-Mapped CMOS Gates
            # -------------------------------------------------------------
            env_mapped = dict(stimulus)
            for node_name in self.dag.topo_order:
                eval_fn = compiled_mapped.get(node_name)
                if eval_fn:
                    env_mapped[node_name] = eval_fn(env_mapped)
                elif node_name in env_dag:
                    env_mapped[node_name] = env_dag[node_name]

            s3_pass = True
            for sig in check_signals:
                gold_val = golden_arrays[sig][vec_idx]
                mapped_val = env_mapped.get(sig, 0)
                if gold_val != mapped_val:
                    if not is_unreachable:
                        s3_pass = False
                        if len(mismatches) < 20:
                            mismatches.append(StageMismatch(
                                stage_index=3,
                                stage_name="Stage 3: Technology-Mapped Gates",
                                signal_name=sig,
                                vector_index=vec_idx,
                                stimulus=stimulus,
                                golden_val=gold_val,
                                stage_val=mapped_val
                            ))
            if s3_pass:
                stage_match_counts["Stage 3: Technology-Mapped Gates"] += 1
            # -------------------------------------------------------------
            # Stage 4: Evaluate Cadence Verilog-A Behavioral Model
            # -------------------------------------------------------------
            env_va = {"vhigh": 1, "vlow": 0}
            for p in self.dag.primary_inputs:
                env_va[f"V({p})"] = stimulus.get(p, 0)
                env_va[p] = stimulus.get(p, 0)
            for r_name, r in self.dag.registers.items():
                for bit_i in range(r.width):
                    b_key = f"{r_name}[{bit_i}]" if r.width > 1 else r_name
                    b_var = f"{r_name}_{bit_i}_q" if r.width > 1 else f"{r_name}_q"
                    env_va[b_var] = stimulus.get(b_key, 0)

            for node_name in self.dag.topo_order:
                node = self.dag.nodes.get(node_name)
                eval_fn = compiled_va.get(node_name)
                if node and eval_fn:
                    val = eval_fn(env_va)
                    if node.node_type == "register_d":
                        d_var = node_name.replace("[", "_").replace("]", "")
                        env_va[d_var] = val
                    else:
                        val_var = node_name.replace("[", "_").replace("]", "") + "_val"
                        env_va[val_var] = val

            s4_pass = True
            for sig in check_signals:
                gold_val = golden_arrays[sig][vec_idx]
                if sig.endswith("_d"):
                    d_var = sig.replace("[", "_").replace("]", "")
                    va_val = env_va.get(d_var, 0)
                else:
                    base_name = sig.split("[")[0]
                    b_var = sig.replace("[", "_").replace("]", "")
                    if base_name in self.dag.registers:
                        va_val = env_va.get(f"{b_var}_q", 0)
                    else:
                        va_val = env_va.get(f"{b_var}_val", 0)

                if gold_val != va_val:
                    if not is_unreachable:
                        s4_pass = False
                        if len(mismatches) < 20:
                            mismatches.append(StageMismatch(
                                stage_index=4,
                                stage_name="Stage 4: Cadence Verilog-A Model",
                                signal_name=sig,
                                vector_index=vec_idx,
                                stimulus=stimulus,
                                golden_val=gold_val,
                                stage_val=va_val
                            ))
            if s4_pass:
                stage_match_counts["Stage 4: Cadence Verilog-A Model"] += 1

        elapsed = time.time() - start_time
        passed = (len(mismatches) == 0)

        return StageVerificationReport(
            passed=passed,
            total_vectors=total_vectors,
            stages_tested=stage_names,
            signals_checked=check_signals,
            mismatches=mismatches,
            stage_match_counts=stage_match_counts,
            execution_time_seconds=elapsed
        )
