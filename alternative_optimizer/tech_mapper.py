"""Silicon Technology Mapper for CMOS Standard Cell Libraries.

Maps Boolean expressions into standard CMOS cells:
- INV (1.0 GE, 2T)
- NAND2 (2.0 GE, 4T), NAND3 (3.0 GE, 6T), NAND4 (4.0 GE, 8T)
- NOR2 (2.0 GE, 4T), NOR3 (3.0 GE, 6T), NOR4 (4.0 GE, 8T)
- AND2 (3.0 GE, 6T), OR2 (3.0 GE, 6T)
- AOI21 (3.0 GE, 6T), OAI21 (3.0 GE, 6T)
- AOI22 (4.0 GE, 8T), OAI22 (4.0 GE, 8T)
- MUX2 (6.0 GE, 12T), XOR2 (6.0 GE, 12T)

Supports dual-polarity phase assignment and compound gate pattern recognition.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple
from pyeda.boolalg.expr import OrOp, AndOp, NotOp, Variable, Complement, Expression

from ams_optimizer.core.models import (
    LocalTruthTable,
    MappedLogicNode,
    INVERTER_EQUIVALENTS,
    TRANSISTOR_COST,
)


def calculate_ge(gate_counts: Dict[str, int]) -> float:
    """Computes total Inverter Equivalents (GE) from a gate dictionary."""
    return sum(count * INVERTER_EQUIVALENTS.get(gate, 3.0) for gate, count in gate_counts.items())


def calculate_transistors(gate_counts: Dict[str, int]) -> int:
    """Computes total transistor count from a gate dictionary."""
    return sum(count * TRANSISTOR_COST.get(gate, 6) for gate, count in gate_counts.items())


class SiliconTechMapper:
    """Maps pyeda SOP expressions and truth tables to CMOS standard cells."""

    def __init__(self, allow_compound_gates: bool = True, dual_polarity: bool = True):
        self.allow_compound = allow_compound_gates
        self.dual_polarity = dual_polarity

    def match_truth_table_fast(self, tt: LocalTruthTable) -> Optional[MappedLogicNode]:
        """Checks direct NPN bitmask match for small k (1, 2, 3 inputs)."""
        if not self.allow_compound:
            return None
        from ams_optimizer.core.npn_matcher import NPNBitmaskMatcher
        if tt.num_vars == 1:
            return NPNBitmaskMatcher.match_1input(tt)
        elif tt.num_vars == 2:
            return NPNBitmaskMatcher.match_2input(tt, allow_and_or=False)
        elif tt.num_vars == 3:
            return NPNBitmaskMatcher.match_3input(tt, allow_and_or=False, allow_mux=True)
    def map_sop_via_demorgan(self, expr: Expression, node_name: str) -> MappedLogicNode:
        """Transforms an SOP expression into a pure CMOS NAND-NAND tree via DeMorgan's laws."""
        expr_str = str(expr)
        if expr_str in ["0", "0.0"]:
            return MappedLogicNode(node_name=node_name, expression="0.0", gate_counts={})
        if expr_str in ["1", "1.0"]:
            return MappedLogicNode(node_name=node_name, expression="1.0", gate_counts={})
        if isinstance(expr, Variable):
            return MappedLogicNode(node_name=node_name, expression=expr.name, gate_counts={})
        if isinstance(expr, Complement):
            return MappedLogicNode(node_name=node_name, expression=f"INV({expr.top.name})", gate_counts={"INV": 1})

        gates: Dict[str, int] = {}

        def inv_lit(lit: str) -> str:
            if lit.startswith("INV(") and lit.endswith(")"):
                if gates.get("INV", 0) > 0:
                    gates["INV"] -= 1
                    if gates["INV"] == 0:
                        del gates["INV"]
                return lit[4:-1]
            else:
                gates["INV"] = gates.get("INV", 0) + 1
                return f"INV({lit})"

        p_terms = list(expr.xs) if isinstance(expr, OrOp) else [expr]

        if len(p_terms) == 1:
            term = p_terms[0]
            lits = list(term.xs) if isinstance(term, AndOp) else [term]
            lit_strs = [inv_lit(l.top.name) if isinstance(l, Complement) else (l.name if hasattr(l, "name") else str(l)) for l in lits]
            k = len(lit_strs)
            if k == 1:
                return MappedLogicNode(node_name=node_name, expression=lit_strs[0], gate_counts=gates)
            elif k <= 4:
                gates[f"NAND{k}"] = gates.get(f"NAND{k}", 0) + 1
                out = inv_lit(f"NAND{k}(" + ", ".join(lit_strs) + ")")
                return MappedLogicNode(node_name=node_name, expression=out, gate_counts=gates)
            else:
                curr = lit_strs[0]
                for nxt in lit_strs[1:]:
                    gates["NAND2"] = gates.get("NAND2", 0) + 1
                    curr = inv_lit(f"NAND2({curr}, {nxt})")
                return MappedLogicNode(node_name=node_name, expression=curr, gate_counts=gates)

        inv_p_terms = []
        for term in p_terms:
            lits = list(term.xs) if isinstance(term, AndOp) else [term]
            lit_strs = [inv_lit(l.top.name) if isinstance(l, Complement) else (l.name if hasattr(l, "name") else str(l)) for l in lits]
            k = len(lit_strs)
            if k == 1:
                inv_p_terms.append(inv_lit(lit_strs[0]))
            elif k <= 4:
                gates[f"NAND{k}"] = gates.get(f"NAND{k}", 0) + 1
                inv_p_terms.append(f"NAND{k}(" + ", ".join(lit_strs) + ")")
            else:
                curr = lit_strs[0]
                for nxt in lit_strs[1:-1]:
                    gates["NAND2"] = gates.get("NAND2", 0) + 1
                    curr = inv_lit(f"NAND2({curr}, {nxt})")
                gates["NAND2"] = gates.get("NAND2", 0) + 1
                inv_p_terms.append(f"NAND2({curr}, {lit_strs[-1]})")

        num_prods = len(inv_p_terms)
        if num_prods <= 4:
            gates[f"NAND{num_prods}"] = gates.get(f"NAND{num_prods}", 0) + 1
            expr_out = f"NAND{num_prods}(" + ", ".join(inv_p_terms) + ")"
        else:
            curr = inv_p_terms[0]
            for pt in inv_p_terms[1:-1]:
                gates["NAND2"] = gates.get("NAND2", 0) + 1
                curr = inv_lit(f"NAND2({curr}, {pt})")
            gates["NAND2"] = gates.get("NAND2", 0) + 1
            expr_out = f"NAND2({curr}, {inv_p_terms[-1]})"

        return MappedLogicNode(node_name=node_name, expression=expr_out, gate_counts=gates)

    def map_sop_to_basic_gates(self, expr: Expression, node_name: str) -> MappedLogicNode:
        """Maps a pyeda expression using only basic gates (INV, AND2/3/4, OR2/3/4).
        
        This is Mode 1 (Simple Espresso baseline).
        """
        gate_counts: Dict[str, int] = {}
        expr_str = str(expr)

        if expr_str in ["0", "0.0"]:
            return MappedLogicNode(node_name=node_name, expression="0.0", gate_counts={})
        if expr_str in ["1", "1.0"]:
            return MappedLogicNode(node_name=node_name, expression="1.0", gate_counts={})

        if isinstance(expr, Variable):
            return MappedLogicNode(node_name=node_name, expression=expr.name, gate_counts={})

        if isinstance(expr, Complement):
            gate_counts["INV"] = 1
            return MappedLogicNode(node_name=node_name, expression=f"INV({expr.top.name})", gate_counts=gate_counts)

        if isinstance(expr, AndOp):
            # Single product term
            self._count_and_term(expr.xs, gate_counts)
            return MappedLogicNode(node_name=node_name, expression=str(expr), gate_counts=gate_counts)

        if isinstance(expr, OrOp):
            # Sum of products
            prod_terms = expr.xs
            # Count each product term
            for term in prod_terms:
                if isinstance(term, AndOp):
                    self._count_and_term(term.xs, gate_counts)
                elif isinstance(term, Complement):
                    gate_counts["INV"] = gate_counts.get("INV", 0) + 1
            
            # OR reduction across product terms
            num_prods = len(prod_terms)
            self._count_or_tree(num_prods, gate_counts)
            return MappedLogicNode(node_name=node_name, expression=str(expr), gate_counts=gate_counts)

        return MappedLogicNode(node_name=node_name, expression=str(expr), gate_counts=gate_counts)

    def map_sop_to_cmos_cells(self, expr: Expression, node_name: str) -> MappedLogicNode:
        """Maps an SOP expression into standard CMOS compound cells (AOI21, OAI21, NAND, NOR, INV).
        
        Evaluates both direct and inverting CMOS forms for lowest GE.
        """
        expr_str = str(expr)
        if expr_str in ["0", "0.0"]:
            return MappedLogicNode(node_name=node_name, expression="0.0", gate_counts={})
        if expr_str in ["1", "1.0"]:
            return MappedLogicNode(node_name=node_name, expression="1.0", gate_counts={})
        if isinstance(expr, Variable):
            return MappedLogicNode(node_name=node_name, expression=expr.name, gate_counts={})
        if isinstance(expr, Complement):
            return MappedLogicNode(node_name=node_name, expression=f"INV({expr.top.name})", gate_counts={"INV": 1})

        # 1. Direct Compound Gate Matching
        if self.allow_compound and isinstance(expr, OrOp):
            # Check AOI21 pattern: (A & B) | C -> inverted AOI21 + INV, or AOI if polarity permits
            terms = expr.xs
            # Pattern: 2 terms, one of size 2 and one of size 1
            if len(terms) == 2:
                sizes = [len(t.xs) if isinstance(t, AndOp) else 1 for t in terms]
                if sorted(sizes) == [1, 2]:
                    # Matches AOI21 structure: (A & B) | C
                    # In CMOS: AOI21 = ~( (A & B) | C ) (3.0 GE) + INV (1.0 GE) = 4.0 GE
                    # Compare against: AND2 (3.0 GE) + OR2 (3.0 GE) = 6.0 GE
                    gate_counts = {"AOI21": 1, "INV": 1}
                    # Count literal inversions
                    for t in terms:
                        if isinstance(t, Complement):
                            gate_counts["INV"] = gate_counts.get("INV", 0) + 1
                        elif isinstance(t, AndOp):
                            for lit in t.xs:
                                if isinstance(lit, Complement):
                                    gate_counts["INV"] = gate_counts.get("INV", 0) + 1
                    return MappedLogicNode(node_name=node_name, expression=str(expr), gate_counts=gate_counts)

                elif sizes == [2, 2]:
                    # Matches AOI22: (A & B) | (C & D)
                    # CMOS: AOI22 (4.0 GE) + INV (1.0 GE) = 5.0 GE vs 2*AND2 + OR2 = 9.0 GE
                    gate_counts = {"AOI22": 1, "INV": 1}
                    for t in terms:
                        for lit in t.xs:
                            if isinstance(lit, Complement):
                                gate_counts["INV"] = gate_counts.get("INV", 0) + 1
                    return MappedLogicNode(node_name=node_name, expression=str(expr), gate_counts=gate_counts)

        # 2. NAND-NAND Mapping for general SOP:
        # F = P1 | P2 | ... = ~( ~P1 & ~P2 & ... )
        # Each Pk is an AND; in CMOS: Pk can be computed by NANDk, fed into NAND-input
        # This replaces AND (3.0 GE) + OR (3.0 GE) with NAND (2.0 GE) + NAND (2.0 GE)
        if isinstance(expr, OrOp):
            gate_counts = {}
            # Product terms
            for term in expr.xs:
                if isinstance(term, AndOp):
                    k = len(term.xs)
                    if k == 2:
                        gate_counts["NAND2"] = gate_counts.get("NAND2", 0) + 1
                    elif k == 3:
                        gate_counts["NAND3"] = gate_counts.get("NAND3", 0) + 1
                    elif k == 4:
                        gate_counts["NAND4"] = gate_counts.get("NAND4", 0) + 1
                    else:
                        self._count_and_term(term.xs, gate_counts)
                    for lit in term.xs:
                        if isinstance(lit, Complement):
                            gate_counts["INV"] = gate_counts.get("INV", 0) + 1
                elif isinstance(term, Complement):
                    gate_counts["INV"] = gate_counts.get("INV", 0) + 1

            # Output stage: NAND gate across terms
            num_prods = len(expr.xs)
            if num_prods == 2:
                gate_counts["NAND2"] = gate_counts.get("NAND2", 0) + 1
            elif num_prods == 3:
                gate_counts["NAND3"] = gate_counts.get("NAND3", 0) + 1
            elif num_prods == 4:
                gate_counts["NAND4"] = gate_counts.get("NAND4", 0) + 1
            else:
                self._count_or_tree(num_prods, gate_counts)

            nand_node = MappedLogicNode(node_name=node_name, expression=str(expr), gate_counts=gate_counts)
            basic_node = self.map_sop_to_basic_gates(expr, node_name)
            
            if calculate_ge(nand_node.gate_counts) < calculate_ge(basic_node.gate_counts):
                return nand_node
            return basic_node

        return self.map_sop_to_basic_gates(expr, node_name)

    def _count_and_term(self, lits: Tuple[Expression, ...], gate_counts: Dict[str, int]) -> None:
        """Counts gates for an AND product term."""
        for lit in lits:
            if isinstance(lit, Complement):
                gate_counts["INV"] = gate_counts.get("INV", 0) + 1

        k = len(lits)
        if k <= 1:
            return
        elif k == 2:
            gate_counts["AND2"] = gate_counts.get("AND2", 0) + 1
        elif k == 3:
            gate_counts["AND3"] = gate_counts.get("AND3", 0) + 1
        elif k == 4:
            gate_counts["AND4"] = gate_counts.get("AND4", 0) + 1
        else:
            # Tree of AND2/3/4
            rem = k
            while rem > 1:
                chunk = min(rem, 4)
                gate_counts[f"AND{chunk}"] = gate_counts.get(f"AND{chunk}", 0) + 1
                rem -= (chunk - 1)

    def _count_or_tree(self, num_inputs: int, gate_counts: Dict[str, int]) -> None:
        """Counts gates for an OR reduction tree."""
        if num_inputs <= 1:
            return
        elif num_inputs == 2:
            gate_counts["OR2"] = gate_counts.get("OR2", 0) + 1
        elif num_inputs == 3:
            gate_counts["OR3"] = gate_counts.get("OR3", 0) + 1
        elif num_inputs == 4:
            gate_counts["OR4"] = gate_counts.get("OR4", 0) + 1
        else:
            rem = num_inputs
            while rem > 1:
                chunk = min(rem, 4)
                gate_counts[f"OR{chunk}"] = gate_counts.get(f"OR{chunk}", 0) + 1
                rem -= (chunk - 1)
