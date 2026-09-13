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

    def __init__(
        self,
        allow_and_or: bool = True,
        allow_mux: bool = True,
        qm_max_inputs: int = 6,
        shannon_min_inputs: int = 3,
        dual_polarity: bool = True,
    ):
        self.allow_and_or = allow_and_or
        self.allow_mux = allow_mux
        self.qm_max_inputs = qm_max_inputs
        self.shannon_min_inputs = shannon_min_inputs
        self.dual_polarity = dual_polarity
        self.inverter_pool: Dict[str, str] = {}
        self.shannon_mux = ShannonMUXDecomposer(
            self.map_truth_table,
            allow_and_or=self.allow_and_or,
            allow_mux=self.allow_mux,
        )

    def _calculate_ge_cost(self, node: MappedLogicNode) -> float:
        from .models import INVERTER_EQUIVALENTS
        return sum(count * INVERTER_EQUIVALENTS.get(gate, 3.0) for gate, count in node.gate_counts.items())

    def get_or_create_inverter(self, net_name: str) -> str:
        """Reuses inverted signals globally to avoid duplicate inverters."""
        if net_name.startswith("INV(") and net_name.endswith(")"):
            return net_name[4:-1]
        return f"INV({net_name})"

    def map_truth_table(self, tt: LocalTruthTable) -> MappedLogicNode:
        """Synthesizes a local truth table into standard CMOS cells, evaluating f and !f."""
        pos_match = self._map_single_polarity(tt)
        
        if not self.dual_polarity or pos_match.expression in ["0.0", "1.0"] or tt.num_vars <= 1:
            return pos_match
            
        k = tt.num_vars
        all_minterms = set(range(1 << k))
        inv_true_minterms = list(all_minterms - set(tt.true_minterms) - set(tt.dont_cares))
        
        tt_inv = LocalTruthTable(
            node_name=tt.node_name,
            inputs=tt.inputs,
            num_vars=k,
            true_minterms=inv_true_minterms,
            dont_cares=tt.dont_cares
        )
        neg_match = self._map_single_polarity(tt_inv)
        
        new_gates = dict(neg_match.gate_counts)
        inv_expr = self.get_or_create_inverter(neg_match.expression)
        if neg_match.expression.startswith("INV(") and neg_match.expression.endswith(")"):
            if new_gates.get("INV", 0) > 0:
                new_gates["INV"] -= 1
                if new_gates["INV"] == 0:
                    del new_gates["INV"]
        else:
            new_gates["INV"] = new_gates.get("INV", 0) + 1
            
        neg_node = MappedLogicNode(node_name=tt.node_name, expression=inv_expr, gate_counts=new_gates)
        
        if self._calculate_ge_cost(neg_node) < self._calculate_ge_cost(pos_match):
            return neg_node
        return pos_match

    def _map_single_polarity(self, tt: LocalTruthTable) -> MappedLogicNode:
        """Synthesizes a single polarity local truth table into standard CMOS cells."""
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
            match_2 = NPNBitmaskMatcher.match_2input(tt, allow_and_or=self.allow_and_or)
            if match_2:
                return match_2

        # 4. 3-Input Exact NPN Bitmask Matching (AOI21, OAI21, NAND3, NOR3, MUX2)
        if k == 3:
            match_3 = NPNBitmaskMatcher.match_3input(tt, allow_and_or=self.allow_and_or, allow_mux=self.allow_mux)
            if match_3:
                return match_3

        # 5. Shannon Decomposition Check (Extract MUX2 / factored gates)
        mux_match = None
        if k >= self.shannon_min_inputs:
            mux_match = self.shannon_mux.try_decompose(tt)

        # 6. Fallback or Competitor: Quine-McCluskey SOP
        if k <= self.qm_max_inputs:
            qm_match = self._map_quine_mccluskey(tt)
            if mux_match is not None:
                mux_cost = self._calculate_ge_cost(mux_match)
                qm_cost = self._calculate_ge_cost(qm_match)
                if mux_cost <= qm_cost:
                    return mux_match
                return qm_match
            return qm_match

        if mux_match is not None:
            return mux_match

        return self._map_quine_mccluskey(tt)

    def _invert_literal(self, lit: str, gates: Dict[str, int]) -> str:
        if lit.startswith("INV(") and lit.endswith(")"):
            if gates.get("INV", 0) > 0:
                gates["INV"] -= 1
                if gates["INV"] == 0:
                    del gates["INV"]
            return lit[4:-1]
        else:
            gates["INV"] = gates.get("INV", 0) + 1
            return f"INV({lit})"

    def _map_quine_mccluskey(self, tt: LocalTruthTable) -> MappedLogicNode:
        """Minimizes arbitrary truth tables via Quine-McCluskey into CMOS NAND-NAND trees."""
        from .quine_mccluskey import QuineMcCluskeySolver
        implicants = QuineMcCluskeySolver.solve(tt.num_vars, tt.true_minterms, tt.dont_cares)
        if not implicants:
            return MappedLogicNode(node_name=tt.node_name, expression="0.0")

        inputs = tt.inputs
        gates: Dict[str, int] = {}
        
        if len(implicants) == 1:
            literals = []
            for bit_i, c in enumerate(implicants[0]):
                if c == "1":
                    literals.append(inputs[bit_i])
                elif c == "0":
                    literals.append(self._invert_literal(inputs[bit_i], gates))
            
            if len(literals) == 1:
                return MappedLogicNode(node_name=tt.node_name, expression=literals[0], gate_counts=gates)
            elif len(literals) == 2:
                if self.allow_and_or:
                    gates["AND2"] = gates.get("AND2", 0) + 1
                    return MappedLogicNode(node_name=tt.node_name, expression=f"AND2({literals[0]}, {literals[1]})", gate_counts=gates)
                else:
                    gates["NAND2"] = gates.get("NAND2", 0) + 1
                    expr = self._invert_literal(f"NAND2({literals[0]}, {literals[1]})", gates)
                    return MappedLogicNode(node_name=tt.node_name, expression=expr, gate_counts=gates)
            elif len(literals) == 3:
                if self.allow_and_or:
                    gates["AND3"] = gates.get("AND3", 0) + 1
                    return MappedLogicNode(node_name=tt.node_name, expression=f"AND3({literals[0]}, {literals[1]}, {literals[2]})", gate_counts=gates)
                else:
                    gates["NAND3"] = gates.get("NAND3", 0) + 1
                    expr = self._invert_literal(f"NAND3({literals[0]}, {literals[1]}, {literals[2]})", gates)
                    return MappedLogicNode(node_name=tt.node_name, expression=expr, gate_counts=gates)
            elif len(literals) == 4:
                if self.allow_and_or:
                    gates["AND4"] = gates.get("AND4", 0) + 1
                    return MappedLogicNode(node_name=tt.node_name, expression=f"AND4({literals[0]}, {literals[1]}, {literals[2]}, {literals[3]})", gate_counts=gates)
                else:
                    gates["NAND4"] = gates.get("NAND4", 0) + 1
                    expr = self._invert_literal(f"NAND4({literals[0]}, {literals[1]}, {literals[2]}, {literals[3]})", gates)
                    return MappedLogicNode(node_name=tt.node_name, expression=expr, gate_counts=gates)
            else:
                curr = literals[0]
                for lit in literals[1:]:
                    if self.allow_and_or:
                        gates["AND2"] = gates.get("AND2", 0) + 1
                        curr = f"AND2({curr}, {lit})"
                    else:
                        gates["NAND2"] = gates.get("NAND2", 0) + 1
                        curr = self._invert_literal(f"NAND2({curr}, {lit})", gates)
                return MappedLogicNode(node_name=tt.node_name, expression=curr, gate_counts=gates)

        inv_p_terms = []
        for imp in implicants:
            literals = []
            for bit_i, c in enumerate(imp):
                if c == "1":
                    literals.append(inputs[bit_i])
                elif c == "0":
                    literals.append(self._invert_literal(inputs[bit_i], gates))
            
            if len(literals) == 1:
                inv_p_terms.append(self._invert_literal(literals[0], gates))
            elif len(literals) == 2:
                gates["NAND2"] = gates.get("NAND2", 0) + 1
                inv_p_terms.append(f"NAND2({literals[0]}, {literals[1]})")
            elif len(literals) == 3:
                gates["NAND3"] = gates.get("NAND3", 0) + 1
                inv_p_terms.append(f"NAND3({literals[0]}, {literals[1]}, {literals[2]})")
            elif len(literals) == 4:
                gates["NAND4"] = gates.get("NAND4", 0) + 1
                inv_p_terms.append(f"NAND4({literals[0]}, {literals[1]}, {literals[2]}, {literals[3]})")
            else:
                curr = literals[0]
                for lit in literals[1:-1]:
                    if self.allow_and_or:
                        gates["AND2"] = gates.get("AND2", 0) + 1
                        curr = f"AND2({curr}, {lit})"
                    else:
                        gates["NAND2"] = gates.get("NAND2", 0) + 1
                        curr = self._invert_literal(f"NAND2({curr}, {lit})", gates)
                gates["NAND2"] = gates.get("NAND2", 0) + 1
                inv_p_terms.append(f"NAND2({curr}, {literals[-1]})")

        if len(inv_p_terms) == 2:
            gates["NAND2"] = gates.get("NAND2", 0) + 1
            expr = f"NAND2({inv_p_terms[0]}, {inv_p_terms[1]})"
        elif len(inv_p_terms) == 3:
            gates["NAND3"] = gates.get("NAND3", 0) + 1
            expr = f"NAND3({inv_p_terms[0]}, {inv_p_terms[1]}, {inv_p_terms[2]})"
        elif len(inv_p_terms) == 4:
            gates["NAND4"] = gates.get("NAND4", 0) + 1
            expr = f"NAND4({inv_p_terms[0]}, {inv_p_terms[1]}, {inv_p_terms[2]}, {inv_p_terms[3]})"
        else:
            curr = inv_p_terms[0]
            for pt in inv_p_terms[1:-1]:
                if self.allow_and_or:
                    gates["AND2"] = gates.get("AND2", 0) + 1
                    curr = f"AND2({curr}, {pt})"
                else:
                    gates["NAND2"] = gates.get("NAND2", 0) + 1
                    curr = self._invert_literal(f"NAND2({curr}, {pt})", gates)
            gates["NAND2"] = gates.get("NAND2", 0) + 1
            expr = f"NAND2({curr}, {inv_p_terms[-1]})"
            
        return MappedLogicNode(node_name=tt.node_name, expression=expr, gate_counts=gates)
