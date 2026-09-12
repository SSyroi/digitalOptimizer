"""Tree Collapser: Converts synthesized logic DAGs into clean, human-readable nested gate calls."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple
from .synthesizer import LogicNode, SynthesizedCone

@dataclass
class CollapsedExpression:
    target: str  # Signal name being driven (e.g. "q[0]", "dff_d[1]", "out_val")
    nested_expr: str  # e.g. "NAND2(in_a, NOR3(MUX2(sel, d0, d1), in_b, q[1]))"
    leaves: Set[str] = field(default_factory=set)  # All primary input / state signals consumed
    shared_wires: Dict[str, str] = field(default_factory=dict)  # Optional extracted high-fanout sub-expressions


class TreeCollapser:
    """Collapses logic trees into human-readable nested functional gate expressions."""

    def __init__(self, max_inline_depth: int = 10, extract_high_fanout: bool = True):
        self.max_inline_depth = max_inline_depth
        self.extract_high_fanout = extract_high_fanout

    def collapse_cone(self, cone: SynthesizedCone) -> CollapsedExpression:
        """Collapse a synthesized cone into a nested expression."""
        leaves = cone.root.get_leaves()
        shared_wires: Dict[str, str] = {}

        nested_str = self._render_node(cone.root, depth=0, shared_wires=shared_wires)

        return CollapsedExpression(
            target=cone.target,
            nested_expr=nested_str,
            leaves=leaves,
            shared_wires=shared_wires,
        )

    def _render_node(self, node: LogicNode, depth: int, shared_wires: Dict[str, str]) -> str:
        if node.gate_type == "WIRE":
            return str(node.inputs[0]) if node.inputs else node.output_name

        rendered_args = []
        for inp in node.inputs:
            if isinstance(inp, str):
                rendered_args.append(inp)
            elif isinstance(inp, LogicNode):
                rendered_args.append(self._render_node(inp, depth + 1, shared_wires))

        return f"{node.gate_type}({', '.join(rendered_args)})"
