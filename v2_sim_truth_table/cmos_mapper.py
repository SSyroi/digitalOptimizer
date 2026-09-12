"""CMOS Standard Cell Technology Mapper from Minimized Implicants.

Converts Quine-McCluskey prime implicants into nested CMOS gate calls:
NAND2/3/4, NOR2/3/4, INV, AND2/3, OR2/3, XOR2, MUX2, AOI21.
Compatible with Python 3.9+. Zero external dependencies.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class MappedCone:
    target: str
    nested_expression: str
    gate_counts: Dict[str, int] = field(default_factory=dict)
    transistor_cost: int = 0


class CMOSMapper:
    """Maps SOP/POS Boolean terms to CMOS standard cells."""

    CELL_COSTS = {
        "INV": 2,
        "NAND2": 4,
        "NAND3": 6,
        "NAND4": 8,
        "NOR2": 4,
        "NOR3": 6,
        "NOR4": 8,
        "AND2": 6,
        "AND3": 8,
        "OR2": 6,
        "OR3": 8,
        "XOR2": 8,
        "XNOR2": 8,
        "MUX2": 8,
        "AOI21": 6,
        "OAI21": 6,
    }

    def map_implicants_to_cmos(
        self,
        target_name: str,
        implicants: List[str],
        var_names: List[str],
        formula_type: str = "SOP",
    ) -> MappedCone:
        """Map minimal implicants to CMOS nested gates."""
        if formula_type == "CONST_0" or not implicants:
            return MappedCone(target=target_name, nested_expression="0.0", gate_counts={}, transistor_cost=0)
        if formula_type == "CONST_1" or implicants == ["-" * len(var_names)]:
            return MappedCone(target=target_name, nested_expression="1.0", gate_counts={}, transistor_cost=0)

        gate_counts: Dict[str, int] = {}

        # 1. Single term case
        if len(implicants) == 1:
            expr = self._map_single_implicant(implicants[0], var_names, gate_counts)
            return MappedCone(
                target=target_name,
                nested_expression=expr,
                gate_counts=gate_counts,
                transistor_cost=self._calc_cost(gate_counts),
            )

        # 2. Check for MUX2 pattern: (~S & D0) | (S & D1)
        if len(implicants) == 2:
            mux_expr = self._try_match_mux(implicants[0], implicants[1], var_names, gate_counts)
            if mux_expr:
                return MappedCone(
                    target=target_name,
                    nested_expression=mux_expr,
                    gate_counts=gate_counts,
                    transistor_cost=self._calc_cost(gate_counts),
                )

        # 3. Check for XOR2 pattern: (~A & B) | (A & ~B)
        if len(implicants) == 2:
            xor_expr = self._try_match_xor(implicants[0], implicants[1], var_names, gate_counts)
            if xor_expr:
                return MappedCone(
                    target=target_name,
                    nested_expression=xor_expr,
                    gate_counts=gate_counts,
                    transistor_cost=self._calc_cost(gate_counts),
                )

        # 4. Standard CMOS NAND-NAND mapping (De Morgan for Sum-of-Products)
        # SOP: T1 | T2 | T3 = NAND(NOT(T1), NOT(T2), NOT(T3))
        # where NOT(T_k) is a NAND gate of the inputs in T_k
        nand_inputs = []
        for imp in implicants:
            nand_term = self._map_product_to_nand(imp, var_names, gate_counts)
            nand_inputs.append(nand_term)

        top_nand = self._build_nand_tree(nand_inputs, gate_counts)
        return MappedCone(
            target=target_name,
            nested_expression=top_nand,
            gate_counts=gate_counts,
            transistor_cost=self._calc_cost(gate_counts),
        )

    def _map_single_implicant(self, imp: str, var_names: List[str], counts: Dict[str, int]) -> str:
        literals = []
        for c, var in zip(imp, var_names):
            if c == "0":
                counts["INV"] = counts.get("INV", 0) + 1
                literals.append(f"INV({var})")
            elif c == "1":
                literals.append(var)

        if not literals:
            return "1.0"
        if len(literals) == 1:
            return literals[0]
        elif len(literals) == 2:
            counts["AND2"] = counts.get("AND2", 0) + 1
            return f"AND2({literals[0]}, {literals[1]})"
        elif len(literals) == 3:
            counts["AND3"] = counts.get("AND3", 0) + 1
            return f"AND3({literals[0]}, {literals[1]}, {literals[2]})"
        else:
            # Multi-level AND tree
            return self._build_and_tree(literals, counts)

    def _map_product_to_nand(self, imp: str, var_names: List[str], counts: Dict[str, int]) -> str:
        """Map an AND product term directly to a NAND input (or inverted literal)."""
        literals = []
        for c, var in zip(imp, var_names):
            if c == "0":
                counts["INV"] = counts.get("INV", 0) + 1
                literals.append(f"INV({var})")
            elif c == "1":
                literals.append(var)

        if len(literals) == 1:
            # Single literal going into top NAND
            return literals[0]
        elif len(literals) == 2:
            counts["NAND2"] = counts.get("NAND2", 0) + 1
            return f"NAND2({literals[0]}, {literals[1]})"
        elif len(literals) == 3:
            counts["NAND3"] = counts.get("NAND3", 0) + 1
            return f"NAND3({literals[0]}, {literals[1]}, {literals[2]})"
        elif len(literals) == 4:
            counts["NAND4"] = counts.get("NAND4", 0) + 1
            return f"NAND4({literals[0]}, {literals[1]}, {literals[2]}, {literals[3]})"
        else:
            return self._build_and_tree(literals, counts)

    def _build_nand_tree(self, inputs: List[str], counts: Dict[str, int]) -> str:
        if len(inputs) == 1:
            return inputs[0]
        elif len(inputs) == 2:
            counts["NAND2"] = counts.get("NAND2", 0) + 1
            return f"NAND2({inputs[0]}, {inputs[1]})"
        elif len(inputs) == 3:
            counts["NAND3"] = counts.get("NAND3", 0) + 1
            return f"NAND3({inputs[0]}, {inputs[1]}, {inputs[2]})"
        elif len(inputs) == 4:
            counts["NAND4"] = counts.get("NAND4", 0) + 1
            return f"NAND4({inputs[0]}, {inputs[1]}, {inputs[2]}, {inputs[3]})"
        else:
            mid = len(inputs) // 2
            left = self._build_nand_tree(inputs[:mid], counts)
            right = self._build_nand_tree(inputs[mid:], counts)
            counts["NAND2"] = counts.get("NAND2", 0) + 1
            return f"NAND2({left}, {right})"

    def _build_and_tree(self, inputs: List[str], counts: Dict[str, int]) -> str:
        if len(inputs) == 1:
            return inputs[0]
        if len(inputs) == 2:
            counts["AND2"] = counts.get("AND2", 0) + 1
            return f"AND2({inputs[0]}, {inputs[1]})"
        mid = len(inputs) // 2
        left = self._build_and_tree(inputs[:mid], counts)
        right = self._build_and_tree(inputs[mid:], counts)
        counts["AND2"] = counts.get("AND2", 0) + 1
        return f"AND2({left}, {right})"

    def _try_match_mux(self, t1: str, t2: str, var_names: List[str], counts: Dict[str, int]) -> Optional[str]:
        # Check if t1 and t2 differ in one select variable being 0 vs 1
        diff_idx = -1
        for i, (c1, c2) in enumerate(zip(t1, t2)):
            if (c1 == "0" and c2 == "1") or (c1 == "1" and c2 == "0"):
                if diff_idx != -1:
                    return None
                diff_idx = i
            elif c1 != c2:
                return None

        if diff_idx != -1:
            sel_var = var_names[diff_idx]
            d0_imp = t1 if t1[diff_idx] == "0" else t2
            d1_imp = t2 if t1[diff_idx] == "0" else t1

            # Mask out select bit
            d0_clean = d0_imp[:diff_idx] + "-" + d0_imp[diff_idx+1:]
            d1_clean = d1_imp[:diff_idx] + "-" + d1_imp[diff_idx+1:]

            d0_expr = self._map_single_implicant(d0_clean, var_names, counts)
            d1_expr = self._map_single_implicant(d1_clean, var_names, counts)

            counts["MUX2"] = counts.get("MUX2", 0) + 1
            return f"MUX2({sel_var}, {d0_expr}, {d1_expr})"
        return None

    def _try_match_xor(self, t1: str, t2: str, var_names: List[str], counts: Dict[str, int]) -> Optional[str]:
        # Check if t1 = 01 and t2 = 10 on two variables
        active_indices = [i for i, (c1, c2) in enumerate(zip(t1, t2)) if c1 != "-" or c2 != "-"]
        if len(active_indices) == 2:
            i1, i2 = active_indices[0], active_indices[1]
            if (t1[i1] == "0" and t1[i2] == "1" and t2[i1] == "1" and t2[i2] == "0") or \
               (t1[i1] == "1" and t1[i2] == "0" and t2[i1] == "0" and t2[i2] == "1"):
                v1, v2 = var_names[i1], var_names[i2]
                counts["XOR2"] = counts.get("XOR2", 0) + 1
                return f"XOR2({v1}, {v2})"
        return None

    def _calc_cost(self, counts: Dict[str, int]) -> int:
        return sum(self.CELL_COSTS.get(g, 4) * cnt for g, cnt in counts.items())
