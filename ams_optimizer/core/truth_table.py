"""Local Node Truth Table Evaluator & Variable Sensitivity Pruner.

Sweeps local inputs for each DAG node to produce minimal local truth tables
and integer bitmasks. Prunes inactive input variables that do not affect output.

Zero external dependencies. Compatible with Python 3.9+.
"""

from __future__ import annotations
from typing import Dict, List, Set

from .models import SlicedDAG, DAGNode, LocalTruthTable
from .reachability import FSMReachabilityAnalyzer


class LocalTruthTableEvaluator:
    """Evaluates local truth tables per DAG node with active sensitivity pruning."""

    def __init__(self, dag: SlicedDAG):
        self.dag = dag
        self.reachability = FSMReachabilityAnalyzer(dag)

    def evaluate_node(self, node: DAGNode) -> LocalTruthTable:
        """Evaluates a single node across its local inputs and prunes inactive variables."""
        raw_inputs = list(node.inputs)
        if not raw_inputs:
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
            inp_dict = {}
            for idx, orig_i in enumerate(active_indices):
                inp_dict[raw_inputs[orig_i]] = (p_row >> idx) & 1
            for idx, inp_name in enumerate(raw_inputs):
                if idx not in active_indices:
                    inp_dict[inp_name] = 0

            val = node.eval_fn(inp_dict)
            if val:
                true_minterms.append(p_row)
                bitmask |= (1 << p_row)

        # 4. Extract Don't-Cares from FSM reachability
        dont_cares = self.reachability.get_dont_cares_for_inputs(pruned_inputs, true_minterms)

        return LocalTruthTable(
            node_name=node.name,
            inputs=pruned_inputs,
            num_vars=p_k,
            true_minterms=true_minterms,
            dont_cares=dont_cares,
            bitmask=bitmask
        )
