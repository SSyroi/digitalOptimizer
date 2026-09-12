"""Local Truth Table Evaluator & FSM Reachability Analyzer.

Computes exact truth tables (and integer bitmasks) locally for each node in the DAG.
Performs state reachability analysis from reset to discover Don't-Care (X) states.

Zero external dependencies. Compatible with Python 3.9+.
"""

from __future__ import annotations
import itertools
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .dag_slicer import SlicedDAG, DAGNode


@dataclass
class LocalTruthTable:
    node_name: str
    inputs: List[str]
    num_vars: int
    true_minterms: List[int]
    dont_cares: List[int] = field(default_factory=list)
    bitmask: int = 0  # e.g., 0b1110 = 14 for NAND2


class TruthTableEvaluator:
    """Simulates each node locally and performs state-reachability analysis."""

    def __init__(self, dag: SlicedDAG):
        self.dag = dag
        self.unreachable_states: Set[int] = set()
        self._analyze_fsm_reachability()

    def _analyze_fsm_reachability(self):
        """Discovers unreachable FSM states starting from reset state (state = 0)."""
        # Check if we have an FSM state register (e.g. state[2:0])
        fsm_regs = [r for r in self.dag.registers.values() if "state" in r.name or "trim" in r.name]
        for reg in fsm_regs:
            total_possible = 1 << reg.width
            visited = {reg.reset_val}
            queue = [reg.reset_val]

            # Breadth-first reachability search
            while queue:
                curr_st = queue.pop(0)
                # Test with primary inputs (e.g. start=0, start=1, comp=0, comp=1)
                for start_val in (0, 1):
                    for comp_val in (0, 1):
                        test_inputs = {
                            "start": start_val,
                            "start_trim": start_val,
                            "comp_out": comp_val,
                            "comp_high": comp_val,
                        }
                        for b in range(reg.width):
                            test_inputs[f"{reg.name}[{b}]"] = (curr_st >> b) & 1

                        # Calculate next state from DAG nodes
                        next_st = 0
                        for b in range(reg.width):
                            d_node = self.dag.nodes.get(f"{reg.name}[{b}]_d")
                            if d_node:
                                bit_val = d_node.eval_fn(test_inputs)
                                next_st |= (bit_val << b)
                            else:
                                next_st |= (((curr_st >> b) & 1) << b)

                        if next_st < total_possible and next_st not in visited:
                            visited.add(next_st)
                            queue.append(next_st)

            # Unvisited states are Don't Cares
            unreachable = set(range(total_possible)) - visited
            if unreachable:
                self.unreachable_states = unreachable

    def evaluate_node(self, node: DAGNode) -> LocalTruthTable:
        """Evaluates a single node across its local inputs and prunes inactive variables."""
        raw_inputs = list(node.inputs)
        if not raw_inputs:
            # Constant node
            val = node.eval_fn({})
            return LocalTruthTable(
                node_name=node.name,
                inputs=[],
                num_vars=0,
                true_minterms=[0] if val else [],
                bitmask=1 if val else 0
            )

        # 1. Sweep all 2^k local input combinations
        k = len(raw_inputs)
        total_rows = 1 << k
        out_vector: List[int] = []

        for row_idx in range(total_rows):
            inp_dict = {}
            for bit_i in range(k):
                inp_dict[raw_inputs[bit_i]] = (row_idx >> bit_i) & 1
            val = node.eval_fn(inp_dict)
            out_vector.append(1 if val else 0)

        # 2. Check sensitivity per variable (prune inactive inputs)
        active_indices: List[int] = []
        for bit_i in range(k):
            is_sensitive = False
            for row_idx in range(total_rows):
                flipped_row = row_idx ^ (1 << bit_i)
                if out_vector[row_idx] != out_vector[flipped_row]:
                    is_sensitive = True
                    break
            if is_sensitive:
                active_indices.append(bit_i)

        pruned_inputs = [raw_inputs[i] for i in active_indices]
        p_k = len(pruned_inputs)

        # 3. Build truth table over active inputs
        true_minterms: List[int] = []
        bitmask = 0

        for p_row in range(1 << p_k):
            # Map pruned row back to original inputs
            inp_dict = {}
            for idx, orig_i in enumerate(active_indices):
                inp_dict[raw_inputs[orig_i]] = (p_row >> idx) & 1
            # Fill un-active inputs with 0
            for idx, inp_name in enumerate(raw_inputs):
                if idx not in active_indices:
                    inp_dict[inp_name] = 0

            val = node.eval_fn(inp_dict)
            if val:
                true_minterms.append(p_row)
                bitmask |= (1 << p_row)

        # 4. Map FSM unreachable states to don't-cares if inputs include state bits
        dont_cares: List[int] = []
        # If active inputs match a 3-bit state vector
        if p_k == 3 and all("state" in inp for inp in pruned_inputs):
            for unreach_st in self.unreachable_states:
                if unreach_st not in true_minterms:
                    dont_cares.append(unreach_st)

        return LocalTruthTable(
            node_name=node.name,
            inputs=pruned_inputs,
            num_vars=p_k,
            true_minterms=true_minterms,
            dont_cares=dont_cares,
            bitmask=bitmask
        )
