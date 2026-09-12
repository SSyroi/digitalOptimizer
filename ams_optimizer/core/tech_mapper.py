"""Technology Mapper Coordinator.

Delegates local truth tables to specialized synthesis engines:
1. NPN Bitmask Matching (AOI21, OAI21, XOR2, NAND2/3/4, NOR2/3/4)
2. Shannon Decomposition (6T Transmission-Gate MUX2)
3. Quine-McCluskey & Petrick Solver (Arbitrary SOP trees with Don't-Cares)
4. Global Inverter Sharing Pool (single inverter instance shared across cones)

Zero external dependencies. Compatible with Python 3.9+.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple

from .models import LocalTruthTable, MappedLogicNode, MappedCell
from .npn_matcher import NPNBitmaskMatcher
from .shannon_mux import ShannonMUXDecomposer
from .quine_mccluskey import QuineMcCluskeySolver


class TechnologyMapper:
    """Coordinates technology mapping and gate selection for local truth tables."""

    def __init__(self):
        self.inverter_pool: Dict[str, str] = {}
        self.shannon_mux = ShannonMUXDecomposer(self.map_truth_table)

    def get_or_create_inverter(self, net_name: str) -> str:
        """Reuses inverted signals globally to avoid duplicate inverters."""
        if net_name.startswith("INV(") and net_name.endswith(")"):
            return net_name[4:-1]
        return f"INV({net_name})"

    def map_truth_table(self, tt: LocalTruthTable) -> MappedLogicNode:
        """Synthesizes a local truth table into standard CMOS cells."""
        k = tt.num_vars
        inputs = tt.inputs

        # 1. Constant cases
        if k == 0:
            val_str = "1.0" if (0 in tt.true_minterms) else "0.0"
            return MappedLogicNode(node_name=tt.node_name, expression=val_str)

        if len(tt.true_minterms) == 0:
            return MappedLogicNode(node_name=tt.node_name, expression="0.0")

        if len(tt.true_minterms) == (1 << k):
            return MappedLogicNode(node_name=tt.node_name, expression="1.0")

        # 2. 1-Input Buffer / Inverter
        if k == 1:
            match_1 = NPNBitmaskMatcher.match_1input(tt)
            if match_1:
                return match_1

        # 3. 2-Input Exact NPN Bitmask Matching
        if k == 2:
            match_2 = NPNBitmaskMatcher.match_2input(tt)
            if match_2:
                return match_2

        # 4. 3-Input Exact NPN Bitmask Matching (AOI21, OAI21, NAND3, NOR3, MUX2)
        if k == 3:
            match_3 = NPNBitmaskMatcher.match_3input(tt)
            if match_3:
                return match_3

        # 5. Shannon Decomposition Check (Extract MUX2 for 3 to 5 inputs)
        if k >= 3:
            mux_match = self.shannon_mux.try_decompose(tt)
            if mux_match:
                return mux_match

        # 6. Fallback: Pure Quine-McCluskey SOP -> CMOS Gate Tree Mapping
        return self._map_quine_mccluskey(tt)

    def _map_quine_mccluskey(self, tt: LocalTruthTable) -> MappedLogicNode:
        """Minimizes arbitrary truth tables via Quine-McCluskey into CMOS gate trees."""
        implicants = QuineMcCluskeySolver.solve(tt.num_vars, tt.true_minterms, tt.dont_cares)
        if not implicants:
            return MappedLogicNode(node_name=tt.node_name, expression="0.0")

        inputs = tt.inputs
        gates: Dict[str, int] = {}
        product_terms: List[str] = []

        for imp in implicants:
            literals = []
            for bit_i, c in enumerate(imp):
                if c == "1":
                    literals.append(inputs[bit_i])
                elif c == "0":
                    inv_lit = self.get_or_create_inverter(inputs[bit_i])
                    gates["INV"] = gates.get("INV", 0) + 1
                    literals.append(inv_lit)

            if len(literals) == 1:
                product_terms.append(literals[0])
            elif len(literals) == 2:
                gates["AND2"] = gates.get("AND2", 0) + 1
                product_terms.append(f"AND2({literals[0]}, {literals[1]})")
            elif len(literals) == 3:
                gates["AND3"] = gates.get("AND3", 0) + 1
                product_terms.append(f"AND3({literals[0]}, {literals[1]}, {literals[2]})")
            elif len(literals) == 4:
                gates["AND4"] = gates.get("AND4", 0) + 1
                product_terms.append(f"AND4({literals[0]}, {literals[1]}, {literals[2]}, {literals[3]})")
            else:
                curr = literals[0]
                for lit in literals[1:]:
                    gates["AND2"] = gates.get("AND2", 0) + 1
                    curr = f"AND2({curr}, {lit})"
                product_terms.append(curr)

        # Combine product terms
        if len(product_terms) == 1:
            return MappedLogicNode(node_name=tt.node_name, expression=product_terms[0], gate_counts=gates)
        elif len(product_terms) == 2:
            gates["OR2"] = gates.get("OR2", 0) + 1
            return MappedLogicNode(node_name=tt.node_name, expression=f"OR2({product_terms[0]}, {product_terms[1]})", gate_counts=gates)
        elif len(product_terms) == 3:
            gates["OR3"] = gates.get("OR3", 0) + 1
            return MappedLogicNode(node_name=tt.node_name, expression=f"OR3({product_terms[0]}, {product_terms[1]}, {product_terms[2]})", gate_counts=gates)
        else:
            curr = product_terms[0]
            for pt in product_terms[1:]:
                gates["OR2"] = gates.get("OR2", 0) + 1
                curr = f"OR2({curr}, {pt})"
            return MappedLogicNode(node_name=tt.node_name, expression=curr, gate_counts=gates)
