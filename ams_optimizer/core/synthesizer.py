"""Boolean Logic Synthesizer and Custom Cell Technology Mapper for AMS Blocks."""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Union
import sympy
from sympy.logic.boolalg import Boolean, Not, And, Or, Xor, simplify_logic
from .library import Library, Cell
from .ast_parser import VerilogExprParser

@dataclass
class LogicNode:
    """Represents a gate in the synthesized logic tree/DAG."""
    gate_type: str  # e.g. "NAND2", "NOR3", "MUX2", "INV", "XOR2", "WIRE"
    inputs: List[Union[str, LogicNode]] = field(default_factory=list)
    output_name: str = ""
    cost: int = 1

    def is_leaf(self) -> bool:
        return self.gate_type == "WIRE" or len(self.inputs) == 0

    def get_leaves(self) -> Set[str]:
        """Get all primary input/register signal names driving this node."""
        leaves = set()
        for inp in self.inputs:
            if isinstance(inp, str):
                leaves.add(inp)
            elif isinstance(inp, LogicNode):
                leaves.update(inp.get_leaves())
        return leaves

    def to_nested_str(self) -> str:
        """Render the node as a nested gate call string like NAND2(A, NOR2(B, C))."""
        if self.gate_type == "WIRE":
            return str(self.inputs[0]) if self.inputs else self.output_name
        inp_strs = []
        for inp in self.inputs:
            if isinstance(inp, str):
                inp_strs.append(inp)
            elif isinstance(inp, LogicNode):
                inp_strs.append(inp.to_nested_str())
        return f"{self.gate_type}({', '.join(inp_strs)})"


@dataclass
class SynthesizedCone:
    target: str
    root: LogicNode
    total_cost: int
    gate_counts: Dict[str, int] = field(default_factory=dict)


class LogicSynthesizer:
    """Performs exact Boolean optimization and CMOS technology mapping to AMS standard cells."""

    def __init__(self, library: Library, prefer_nand_sop: bool = True):
        self.library = library
        self.prefer_nand_sop = prefer_nand_sop
        self.available_gates = set(library.cells.keys())

    def synthesize_expression(self, target_name: str, expr: Union[str, Boolean, None]) -> SynthesizedCone:
        """Synthesize a single boolean expression into a mapped logic tree."""
        if expr is None:
            node = LogicNode(gate_type="WIRE", inputs=[target_name], output_name=target_name, cost=0)
            return SynthesizedCone(target=target_name, root=node, total_cost=0, gate_counts={})

        if isinstance(expr, str):
            sym_expr = self._str_to_sympy(expr)
        else:
            sym_expr = expr

        if sym_expr is None:
            node = LogicNode(gate_type="WIRE", inputs=[target_name], output_name=target_name, cost=0)
            return SynthesizedCone(target=target_name, root=node, total_cost=0, gate_counts={})

        # 1. Simplify boolean logic
        try:
            simplified = simplify_logic(sym_expr, form="dnf")
        except Exception:
            simplified = sym_expr

        # 2. Map boolean AST to library gates
        root_node = self._map_ast_to_gates(simplified)
        root_node.output_name = target_name

        # 3. Calculate gate statistics
        gate_counts: Dict[str, int] = {}
        total_cost = self._calc_stats(root_node, gate_counts)

        return SynthesizedCone(
            target=target_name,
            root=root_node,
            total_cost=total_cost,
            gate_counts=gate_counts,
        )

    def _str_to_sympy(self, s: str) -> Optional[Boolean]:
        parser = VerilogExprParser(s)
        return parser.parse()

    def _sym_to_signal_name(self, sym: sympy.Symbol) -> str:
        name = str(sym)
        return re.sub(r"([a-zA-Z_][a-zA-Z0-9_]*)_(\d+)_", r"\1[\2]", name)

    def _map_ast_to_gates(self, expr: Boolean) -> LogicNode:
        """Recursively pattern-match and decompose SymPy boolean expressions to library gates."""
        # Base case 1: Symbol / Wire
        if isinstance(expr, sympy.Symbol):
            sig_name = self._sym_to_signal_name(expr)
            return LogicNode(gate_type="WIRE", inputs=[sig_name], cost=0)

        # Base case 2: Constant True / False
        if expr is sympy.true:
            return LogicNode(gate_type="WIRE", inputs=["1'b1"], cost=0)
        if expr is sympy.false:
            return LogicNode(gate_type="WIRE", inputs=["1'b0"], cost=0)

        # Check for MUX2 pattern: (S & D1) | (~S & D0) or (~S & D0) | (S & D1)
        mux_node = self._try_match_mux2(expr)
        if mux_node:
            return mux_node

        # Check for XOR2 / XNOR2 pattern
        xor_node = self._try_match_xor(expr)
        if xor_node:
            return xor_node

        # Check for AOI21 / OAI21 patterns
        aoi_node = self._try_match_aoi_oai(expr)
        if aoi_node:
            return aoi_node

        # Pattern: NOT
        if isinstance(expr, Not):
            arg = expr.args[0]
            # NOT(AND(...)) -> NAND
            if isinstance(arg, And):
                args = list(arg.args)
                if len(args) == 2 and "NAND2" in self.available_gates:
                    return LogicNode(
                        gate_type="NAND2",
                        inputs=[self._map_ast_to_gates(args[0]), self._map_ast_to_gates(args[1])],
                        cost=self.library.cells.get("NAND2", Cell("NAND2", "combinational", [], cost=4)).cost,
                    )
                elif len(args) == 3 and "NAND3" in self.available_gates:
                    return LogicNode(
                        gate_type="NAND3",
                        inputs=[self._map_ast_to_gates(a) for a in args],
                        cost=self.library.cells.get("NAND3", Cell("NAND3", "combinational", [], cost=6)).cost,
                    )
                elif len(args) == 4 and "NAND4" in self.available_gates:
                    return LogicNode(
                        gate_type="NAND4",
                        inputs=[self._map_ast_to_gates(a) for a in args],
                        cost=self.library.cells.get("NAND4", Cell("NAND4", "combinational", [], cost=8)).cost,
                    )
                else:
                    return self._decompose_nand(args)

            # NOT(OR(...)) -> NOR
            if isinstance(arg, Or):
                args = list(arg.args)
                if len(args) == 2 and "NOR2" in self.available_gates:
                    return LogicNode(
                        gate_type="NOR2",
                        inputs=[self._map_ast_to_gates(args[0]), self._map_ast_to_gates(args[1])],
                        cost=self.library.cells.get("NOR2", Cell("NOR2", "combinational", [], cost=4)).cost,
                    )
                elif len(args) == 3 and "NOR3" in self.available_gates:
                    return LogicNode(
                        gate_type="NOR3",
                        inputs=[self._map_ast_to_gates(a) for a in args],
                        cost=self.library.cells.get("NOR3", Cell("NOR3", "combinational", [], cost=6)).cost,
                    )
                elif len(args) == 4 and "NOR4" in self.available_gates:
                    return LogicNode(
                        gate_type="NOR4",
                        inputs=[self._map_ast_to_gates(a) for a in args],
                        cost=self.library.cells.get("NOR4", Cell("NOR4", "combinational", [], cost=8)).cost,
                    )
                else:
                    return self._decompose_nor(args)

            # Default NOT -> INV
            return LogicNode(
                gate_type="INV",
                inputs=[self._map_ast_to_gates(arg)],
                cost=self.library.cells.get("INV", Cell("INV", "combinational", [], cost=2)).cost,
            )

        # Pattern: AND
        if isinstance(expr, And):
            args = list(expr.args)
            if len(args) == 2 and "AND2" in self.available_gates:
                return LogicNode(
                    gate_type="AND2",
                    inputs=[self._map_ast_to_gates(args[0]), self._map_ast_to_gates(args[1])],
                    cost=self.library.cells.get("AND2", Cell("AND2", "combinational", [], cost=6)).cost,
                )
            elif len(args) == 3 and "AND3" in self.available_gates:
                return LogicNode(
                    gate_type="AND3",
                    inputs=[self._map_ast_to_gates(a) for a in args],
                    cost=self.library.cells.get("AND3", Cell("AND3", "combinational", [], cost=8)).cost,
                )
            else:
                return self._decompose_and(args)

        # Pattern: OR
        if isinstance(expr, Or):
            args = list(expr.args)

            # Check if all terms are AND or NOT literals and we want NAND-NAND mapping (De Morgan)
            if self.prefer_nand_sop and "NAND2" in self.available_gates:
                if len(args) == 2:
                    not_t1 = self._map_ast_to_gates(Not(args[0]))
                    not_t2 = self._map_ast_to_gates(Not(args[1]))
                    return LogicNode(
                        gate_type="NAND2",
                        inputs=[not_t1, not_t2],
                        cost=4 + not_t1.cost + not_t2.cost,
                    )
                elif len(args) == 3 and "NAND3" in self.available_gates:
                    not_terms = [self._map_ast_to_gates(Not(a)) for a in args]
                    return LogicNode(
                        gate_type="NAND3",
                        inputs=not_terms,
                        cost=6 + sum(t.cost for t in not_terms),
                    )

            if len(args) == 2 and "OR2" in self.available_gates:
                return LogicNode(
                    gate_type="OR2",
                    inputs=[self._map_ast_to_gates(args[0]), self._map_ast_to_gates(args[1])],
                    cost=self.library.cells.get("OR2", Cell("OR2", "combinational", [], cost=6)).cost,
                )
            elif len(args) == 3 and "OR3" in self.available_gates:
                return LogicNode(
                    gate_type="OR3",
                    inputs=[self._map_ast_to_gates(a) for a in args],
                    cost=self.library.cells.get("OR3", Cell("OR3", "combinational", [], cost=8)).cost,
                )
            else:
                return self._decompose_or(args)

        # Pattern: XOR
        if isinstance(expr, Xor):
            args = list(expr.args)
            if len(args) == 2 and "XOR2" in self.available_gates:
                return LogicNode(
                    gate_type="XOR2",
                    inputs=[self._map_ast_to_gates(args[0]), self._map_ast_to_gates(args[1])],
                    cost=self.library.cells.get("XOR2", Cell("XOR2", "combinational", [], cost=8)).cost,
                )
            return self._decompose_xor(args)

        # Fallback
        return LogicNode(gate_type="WIRE", inputs=[str(expr)], cost=0)

    def _try_match_mux2(self, expr: Boolean) -> Optional[LogicNode]:
        """Detect MUX2 pattern: (S & D1) | (~S & D0) or (~S & D0) | (S & D1)."""
        if "MUX2" not in self.available_gates:
            return None
        if not isinstance(expr, Or) or len(expr.args) != 2:
            return None

        t1, t2 = expr.args[0], expr.args[1]
        if not (isinstance(t1, And) and isinstance(t2, And)):
            return None

        for s1 in t1.args:
            not_s1 = Not(s1) if not isinstance(s1, Not) else s1.args[0]
            if not_s1 in t2.args:
                d1_args = [a for a in t1.args if a != s1]
                d0_args = [a for a in t2.args if a != not_s1]
                d1_expr = And(*d1_args) if len(d1_args) > 1 else (d1_args[0] if d1_args else sympy.true)
                d0_expr = And(*d0_args) if len(d0_args) > 1 else (d0_args[0] if d0_args else sympy.true)

                s_node = self._map_ast_to_gates(s1 if not isinstance(s1, Not) else not_s1)
                d1_node = self._map_ast_to_gates(d1_expr if not isinstance(s1, Not) else d0_expr)
                d0_node = self._map_ast_to_gates(d0_expr if not isinstance(s1, Not) else d1_expr)

                return LogicNode(
                    gate_type="MUX2",
                    inputs=[s_node, d0_node, d1_node],
                    cost=self.library.cells.get("MUX2", Cell("MUX2", "combinational", [], cost=8)).cost,
                )
        return None

    def _try_match_xor(self, expr: Boolean) -> Optional[LogicNode]:
        """Detect XOR2/XNOR2 from DNF expansion (~A & B) | (A & ~B)."""
        if "XOR2" not in self.available_gates and "XNOR2" not in self.available_gates:
            return None
        if isinstance(expr, Or) and len(expr.args) == 2:
            t1, t2 = expr.args[0], expr.args[1]
            if isinstance(t1, And) and isinstance(t2, And) and len(t1.args) == 2 and len(t2.args) == 2:
                a1, b1 = t1.args[0], t1.args[1]
                a2, b2 = t2.args[0], t2.args[1]
                if (a1 == Not(a2) and b1 == Not(b2)) or (a1 == Not(b2) and b1 == Not(a2)):
                    var_a = a1 if not isinstance(a1, Not) else a2
                    var_b = b1 if not isinstance(b1, Not) else b2
                    if "XOR2" in self.available_gates:
                        return LogicNode(
                            gate_type="XOR2",
                            inputs=[self._map_ast_to_gates(var_a), self._map_ast_to_gates(var_b)],
                            cost=self.library.cells.get("XOR2", Cell("XOR2", "combinational", [], cost=8)).cost,
                        )
        return None

    def _try_match_aoi_oai(self, expr: Boolean) -> Optional[LogicNode]:
        """Detect AOI21: ~((A & B) | C) and OAI21: ~((A | B) & C)."""
        if isinstance(expr, Not):
            inner = expr.args[0]
            if "AOI21" in self.available_gates and isinstance(inner, Or) and len(inner.args) == 2:
                t1, t2 = inner.args[0], inner.args[1]
                if isinstance(t1, And) and len(t1.args) == 2:
                    return LogicNode(
                        gate_type="AOI21",
                        inputs=[
                            self._map_ast_to_gates(t1.args[0]),
                            self._map_ast_to_gates(t1.args[1]),
                            self._map_ast_to_gates(t2),
                        ],
                        cost=self.library.cells.get("AOI21", Cell("AOI21", "combinational", [], cost=6)).cost,
                    )
                elif isinstance(t2, And) and len(t2.args) == 2:
                    return LogicNode(
                        gate_type="AOI21",
                        inputs=[
                            self._map_ast_to_gates(t2.args[0]),
                            self._map_ast_to_gates(t2.args[1]),
                            self._map_ast_to_gates(t1),
                        ],
                        cost=self.library.cells.get("AOI21", Cell("AOI21", "combinational", [], cost=6)).cost,
                    )
            if "OAI21" in self.available_gates and isinstance(inner, And) and len(inner.args) == 2:
                t1, t2 = inner.args[0], inner.args[1]
                if isinstance(t1, Or) and len(t1.args) == 2:
                    return LogicNode(
                        gate_type="OAI21",
                        inputs=[
                            self._map_ast_to_gates(t1.args[0]),
                            self._map_ast_to_gates(t1.args[1]),
                            self._map_ast_to_gates(t2),
                        ],
                        cost=self.library.cells.get("OAI21", Cell("OAI21", "combinational", [], cost=6)).cost,
                    )
                elif isinstance(t2, Or) and len(t2.args) == 2:
                    return LogicNode(
                        gate_type="OAI21",
                        inputs=[
                            self._map_ast_to_gates(t2.args[0]),
                            self._map_ast_to_gates(t2.args[1]),
                            self._map_ast_to_gates(t1),
                        ],
                        cost=self.library.cells.get("OAI21", Cell("OAI21", "combinational", [], cost=6)).cost,
                    )
        return None

    def _decompose_and(self, args: List[Boolean]) -> LogicNode:
        if len(args) == 1:
            return self._map_ast_to_gates(args[0])
        if len(args) == 2:
            if "AND2" in self.available_gates:
                return LogicNode(
                    gate_type="AND2",
                    inputs=[self._map_ast_to_gates(args[0]), self._map_ast_to_gates(args[1])],
                    cost=6,
                )
            elif "NAND2" in self.available_gates and "INV" in self.available_gates:
                nand_node = LogicNode(
                    gate_type="NAND2",
                    inputs=[self._map_ast_to_gates(args[0]), self._map_ast_to_gates(args[1])],
                    cost=4,
                )
                return LogicNode(gate_type="INV", inputs=[nand_node], cost=6)

        mid = len(args) // 2
        left = self._decompose_and(args[:mid])
        right = self._decompose_and(args[mid:])
        if "AND2" in self.available_gates:
            return LogicNode(gate_type="AND2", inputs=[left, right], cost=6)
        nand_node = LogicNode(gate_type="NAND2", inputs=[left, right], cost=4)
        return LogicNode(gate_type="INV", inputs=[nand_node], cost=6)

    def _decompose_or(self, args: List[Boolean]) -> LogicNode:
        if len(args) == 1:
            return self._map_ast_to_gates(args[0])
        if len(args) == 2:
            if "OR2" in self.available_gates:
                return LogicNode(
                    gate_type="OR2",
                    inputs=[self._map_ast_to_gates(args[0]), self._map_ast_to_gates(args[1])],
                    cost=6,
                )
            elif "NOR2" in self.available_gates and "INV" in self.available_gates:
                nor_node = LogicNode(
                    gate_type="NOR2",
                    inputs=[self._map_ast_to_gates(args[0]), self._map_ast_to_gates(args[1])],
                    cost=4,
                )
                return LogicNode(gate_type="INV", inputs=[nor_node], cost=6)

        mid = len(args) // 2
        left = self._decompose_or(args[:mid])
        right = self._decompose_or(args[mid:])
        if "OR2" in self.available_gates:
            return LogicNode(gate_type="OR2", inputs=[left, right], cost=6)
        nor_node = LogicNode(gate_type="NOR2", inputs=[left, right], cost=4)
        return LogicNode(gate_type="INV", inputs=[nor_node], cost=6)

    def _decompose_nand(self, args: List[Boolean]) -> LogicNode:
        and_tree = self._decompose_and(args)
        return LogicNode(gate_type="INV", inputs=[and_tree], cost=and_tree.cost + 2)

    def _decompose_nor(self, args: List[Boolean]) -> LogicNode:
        or_tree = self._decompose_or(args)
        return LogicNode(gate_type="INV", inputs=[or_tree], cost=or_tree.cost + 2)

    def _decompose_xor(self, args: List[Boolean]) -> LogicNode:
        if len(args) == 1:
            return self._map_ast_to_gates(args[0])
        mid = len(args) // 2
        left = self._decompose_xor(args[:mid])
        right = self._decompose_xor(args[mid:])
        return LogicNode(
            gate_type="XOR2",
            inputs=[left, right],
            cost=8,
        )

    def _calc_stats(self, node: LogicNode, counts: Dict[str, int]) -> int:
        if node.gate_type == "WIRE":
            return 0
        counts[node.gate_type] = counts.get(node.gate_type, 0) + 1
        total = node.cost
        for inp in node.inputs:
            if isinstance(inp, LogicNode):
                total += self._calc_stats(inp, counts)
        return total
