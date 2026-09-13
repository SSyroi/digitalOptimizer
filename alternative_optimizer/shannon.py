"""Shannon Decomposition Engine.

Decomposes a Boolean function f(x1, ..., xk) about a select variable S:
    f = S * f_S + (~S) * f_not_S
Implemented as MUX2(S, A=f_S, B=f_not_S).
Evaluates whether MUX2 decomposition achieves lower Gate Equivalents (GE)
than flat two-level SOP logic.
"""

from __future__ import annotations
from typing import Callable, Dict, List, Optional, Set, Tuple
from ams_optimizer.core.models import LocalTruthTable, MappedLogicNode


class ShannonDecomposer:
    """Performs Shannon expansion to extract MUX2 control multiplexing."""

    def __init__(
        self,
        minimizer_fn: Callable[[LocalTruthTable], MappedLogicNode],
        cost_eval_fn: Callable[[MappedLogicNode], float],
        min_inputs: int = 3,
        mux2_ge_cost: float = 6.0,
    ):
        self.minimizer_fn = minimizer_fn
        self.cost_eval_fn = cost_eval_fn
        self.min_inputs = min_inputs
        self.mux2_ge_cost = mux2_ge_cost

    def try_decompose(self, tt: LocalTruthTable) -> Optional[MappedLogicNode]:
        """Tries Shannon decomposition on all input variables.
        
        Returns the best MUX2 MappedLogicNode if cheaper than flat SOP, else None.
        """
        k = tt.num_vars
        if k < self.min_inputs:
            return None

        best_node: Optional[MappedLogicNode] = None
        best_cost = float("inf")

        true_set = set(tt.true_minterms)
        dc_set = set(tt.dont_cares)

        for sel_idx, sel_var in enumerate(tt.inputs):
            # Form cofactors F0 (sel=0) and F1 (sel=1)
            cofactor_inputs = [inp for idx, inp in enumerate(tt.inputs) if idx != sel_idx]
            rem_k = k - 1
            rem_rows = 1 << rem_k

            f0_minterms: List[int] = []
            f0_dcs: List[int] = []
            f1_minterms: List[int] = []
            f1_dcs: List[int] = []

            for rem_row in range(rem_rows):
                # Construct original row indices with sel=0 and sel=1
                # bit insertion: bits before sel_idx are unchanged, bits at and after are shifted by 1
                row_0 = 0
                row_1 = 0
                for bit in range(rem_k):
                    val = (rem_row >> bit) & 1
                    target_bit = bit if bit < sel_idx else bit + 1
                    row_0 |= (val << target_bit)
                    row_1 |= (val << target_bit)
                row_1 |= (1 << sel_idx)

                # Classify for F0
                if row_0 in true_set:
                    f0_minterms.append(rem_row)
                elif row_0 in dc_set:
                    f0_dcs.append(rem_row)

                # Classify for F1
                if row_1 in true_set:
                    f1_minterms.append(rem_row)
                elif row_1 in dc_set:
                    f1_dcs.append(rem_row)

            # Synthesize cofactors
            tt_f0 = LocalTruthTable(
                node_name=f"{tt.node_name}_f0",
                inputs=cofactor_inputs,
                num_vars=rem_k,
                true_minterms=f0_minterms,
                dont_cares=f0_dcs,
            )
            tt_f1 = LocalTruthTable(
                node_name=f"{tt.node_name}_f1",
                inputs=cofactor_inputs,
                num_vars=rem_k,
                true_minterms=f1_minterms,
                dont_cares=f1_dcs,
            )

            node_f0 = self.minimizer_fn(tt_f0)
            node_f1 = self.minimizer_fn(tt_f1)

            # Check trivial / degenerate cases
            expr_f0 = node_f0.expression
            expr_f1 = node_f1.expression

            # If both are equal, no MUX needed
            if expr_f0 == expr_f1:
                continue

            gate_counts: Dict[str, int] = {}
            for g, c in node_f0.gate_counts.items():
                gate_counts[g] = gate_counts.get(g, 0) + c
            for g, c in node_f1.gate_counts.items():
                gate_counts[g] = gate_counts.get(g, 0) + c

            if expr_f0 == "0.0":
                # f = sel_var & expr_f1 (AND gate)
                gate_counts["AND2"] = gate_counts.get("AND2", 0) + 1
                expr = f"({sel_var} & {expr_f1})"
            elif expr_f1 == "1.0":
                # f = sel_var | expr_f0 (OR gate)
                gate_counts["OR2"] = gate_counts.get("OR2", 0) + 1
                expr = f"({sel_var} | {expr_f0})"
            elif expr_f0 == "1.0":
                # f = ~sel_var | expr_f1
                gate_counts["OR2"] = gate_counts.get("OR2", 0) + 1
                gate_counts["INV"] = gate_counts.get("INV", 0) + 1
                expr = f"(~{sel_var} | {expr_f1})"
            elif expr_f1 == "0.0":
                # f = ~sel_var & expr_f0
                gate_counts["AND2"] = gate_counts.get("AND2", 0) + 1
                gate_counts["INV"] = gate_counts.get("INV", 0) + 1
                expr = f"(~{sel_var} & {expr_f0})"
            else:
                # Full MUX2
                gate_counts["MUX2"] = gate_counts.get("MUX2", 0) + 1
                expr = f"MUX2(S={sel_var}, A={expr_f1}, B={expr_f0})"

            cand_node = MappedLogicNode(
                node_name=tt.node_name,
                expression=expr,
                gate_counts=gate_counts,
            )
            cand_cost = self.cost_eval_fn(cand_node)

            if cand_cost < best_cost:
                best_cost = cand_cost
                best_node = cand_node

        return best_node
