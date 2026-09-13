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

    @staticmethod
    def _create_pruned_tt(name: str, rem_inputs: List[str], rem_k: int, minterms: List[int]) -> LocalTruthTable:
        if rem_k == 0 or len(minterms) == 0:
            return LocalTruthTable(
                node_name=name,
                inputs=[],
                num_vars=0,
                true_minterms=[0] if len(minterms) > 0 else [],
                dont_cares=[],
                bitmask=1 if len(minterms) > 0 else 0
            )
        if len(minterms) == (1 << rem_k):
            return LocalTruthTable(
                node_name=name,
                inputs=[],
                num_vars=0,
                true_minterms=[0],
                dont_cares=[],
                bitmask=1
            )

        # Check sensitivity for each bit in rem_inputs
        minterms_set = set(minterms)
        active_bits = []
        for bit_i in range(rem_k):
            is_active = False
            for m in minterms:
                flipped = m ^ (1 << bit_i)
                if flipped not in minterms_set:
                    is_active = True
                    break
            if is_active:
                active_bits.append(bit_i)

        if len(active_bits) == rem_k:
            return LocalTruthTable(
                node_name=name,
                inputs=rem_inputs,
                num_vars=rem_k,
                true_minterms=minterms,
                dont_cares=[],
                bitmask=sum(1 << m for m in minterms)
            )

        pruned_inputs = [rem_inputs[i] for i in active_bits]
        pruned_k = len(pruned_inputs)
        pruned_minterms = set()
        for m in minterms:
            pruned_m = 0
            for new_idx, orig_bit in enumerate(active_bits):
                bit_val = (m >> orig_bit) & 1
                pruned_m |= (bit_val << new_idx)
            pruned_minterms.add(pruned_m)

        sorted_pm = sorted(pruned_minterms)
        bitmask = sum(1 << m for m in sorted_pm)
        return LocalTruthTable(
            node_name=name,
            inputs=pruned_inputs,
            num_vars=pruned_k,
            true_minterms=sorted_pm,
            dont_cares=[],
            bitmask=bitmask
        )

    def try_decompose(self, tt: LocalTruthTable) -> Optional[MappedLogicNode]:
        """Tests candidate select lines S to extract MUX2 gates."""
        inputs = tt.inputs
        k = tt.num_vars

        if k < 3:
            return None

        # Score candidate select lines S to pick the best partition
        candidates = []
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

            c0_len = len(minterms_0)
            c1_len = len(minterms_1)
            full_k = 1 << rem_k
            is_trivial_0 = (c0_len == 0 or c0_len == full_k)
            is_trivial_1 = (c1_len == 0 or c1_len == full_k)

            score = 0
            if is_trivial_0 or is_trivial_1:
                score += 100
            if c0_len == 1 or c0_len == full_k - 1:
                score += 40
            if c1_len == 1 or c1_len == full_k - 1:
                score += 40

            candidates.append((score, s, rem_inputs, rem_k, minterms_0, minterms_1))

        candidates.sort(key=lambda x: x[0], reverse=True)

        for score, s, rem_inputs, rem_k, minterms_0, minterms_1 in candidates:
            c0_len = len(minterms_0)
            c1_len = len(minterms_1)
            full_k = 1 << rem_k

            if rem_k <= 2 or score > 0 or k >= 4:
                tt_d0 = self._create_pruned_tt(f"{tt.node_name}_d0", rem_inputs, rem_k, minterms_0)
                tt_d1 = self._create_pruned_tt(f"{tt.node_name}_d1", rem_inputs, rem_k, minterms_1)

                res_d0 = self.map_fn(tt_d0)
                res_d1 = self.map_fn(tt_d1)

                # Avoid redundant MUX2 where both branches are identical
                if res_d0.expression == res_d1.expression:
                    return res_d0

                gates = {"MUX2": 1}
                for g, cnt in res_d0.gate_counts.items():
                    gates[g] = gates.get(g, 0) + cnt
                for g, cnt in res_d1.gate_counts.items():
                    gates[g] = gates.get(g, 0) + cnt

                expr = f"MUX2({s}, {res_d0.expression}, {res_d1.expression})"
                return MappedLogicNode(node_name=tt.node_name, expression=expr, gate_counts=gates)

        return None
