"""Shannon Decomposition Engine for MUX2 Extraction.

Applies Shannon's Expansion Theorem to discover control variables S and extract
compact 6-transistor transmission-gate MUX2 standard cells:
    F = S · F_{S=1} + ~S · F_{S=0}  -->  MUX2(S, D0_expr, D1_expr)

Zero external dependencies. Compatible with Python 3.9+.
"""

from __future__ import annotations
from typing import Callable, Dict, List, Optional, Tuple

from .models import LocalTruthTable, MappedLogicNode


class ShannonMUXDecomposer:
    """Extracts transmission-gate MUX2 cells via Shannon cofactor expansion."""

    def __init__(self, map_fn: Callable[[LocalTruthTable], MappedLogicNode]):
        self.map_fn = map_fn

    def try_decompose(self, tt: LocalTruthTable) -> Optional[MappedLogicNode]:
        """Tests candidate select lines S to extract MUX2 gates."""
        inputs = tt.inputs
        k = tt.num_vars

        if k < 3:
            return None

        for s_idx, s in enumerate(inputs):
            rem_inputs = [x for x in inputs if x != s]
            rem_k = len(rem_inputs)

            minterms_0: List[int] = []
            minterms_1: List[int] = []

            for row in range(1 << rem_k):
                # Row with S=0
                orig_row_0 = 0
                for idx, rem_name in enumerate(rem_inputs):
                    bit = (row >> idx) & 1
                    orig_row_0 |= (bit << inputs.index(rem_name))
                if orig_row_0 in tt.true_minterms:
                    minterms_0.append(row)

                # Row with S=1
                orig_row_1 = orig_row_0 | (1 << s_idx)
                if orig_row_1 in tt.true_minterms:
                    minterms_1.append(row)

            # Check if cofactors simplify compactly
            tt_d0 = LocalTruthTable(f"{tt.node_name}_d0", rem_inputs, rem_k, minterms_0, bitmask=sum(1 << m for m in minterms_0))
            tt_d1 = LocalTruthTable(f"{tt.node_name}_d1", rem_inputs, rem_k, minterms_1, bitmask=sum(1 << m for m in minterms_1))

            if rem_k <= 2 or len(minterms_0) in (0, 1, (1 << rem_k) - 1, 1 << rem_k):
                res_d0 = self.map_fn(tt_d0)
                res_d1 = self.map_fn(tt_d1)

                gates = {"MUX2": 1}
                for g, cnt in res_d0.gate_counts.items():
                    gates[g] = gates.get(g, 0) + cnt
                for g, cnt in res_d1.gate_counts.items():
                    gates[g] = gates.get(g, 0) + cnt

                expr = f"MUX2({s}, {res_d0.expression}, {res_d1.expression})"
                return MappedLogicNode(node_name=tt.node_name, expression=expr, gate_counts=gates)

        return None
