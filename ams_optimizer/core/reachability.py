"""FSM State Reachability Analyzer.

Discovers unreachable state combinations starting from the reset state (state = 0)
and classifies them as Don't-Cares (X) for Boolean minimization.

Zero external dependencies. Compatible with Python 3.9+.
"""

from __future__ import annotations
from typing import Dict, List, Set

from .models import SlicedDAG


class FSMReachabilityAnalyzer:
    """Analyzes FSM state transitions to find unreachable state combinations."""

    def __init__(self, dag: SlicedDAG):
        self.dag = dag
        self.unreachable_states: Set[int] = set()
        self._analyze()

    def _analyze(self):
        """Discovers unreachable states using breadth-first search from reset."""
        fsm_regs = [r for r in self.dag.registers.values() if "state" in r.name or "trim" in r.name]
        for reg in fsm_regs:
            total_possible = 1 << reg.width
            visited = {reg.reset_val}
            queue = [reg.reset_val]

            while queue:
                curr_st = queue.pop(0)
                for start_val in (0, 1):
                    for comp_val in (0, 1):
                        test_inputs = {
                            "start": start_val,
                            "start_trim": start_val,
                            "comp_out": comp_val,
                            "comp_high": comp_val,
                        }
                        for b in range(reg.width):
                            test_inputs[f"{reg.name}[{b}]"] = (curr_st >> b) & 1

                        # Compute next state
                        next_st = 0
                        for b in range(reg.width):
                            d_node = self.dag.nodes.get(f"{reg.name}[{b}]_d")
                            if d_node:
                                bit_val = d_node.eval_fn(test_inputs)
                                next_st |= (bit_val << b)
                            else:
                                next_st |= (((curr_st >> b) & 1) << b)

                        if next_st < total_possible and next_st not in visited:
                            visited.add(next_st)
                            queue.append(next_st)

            unreachable = set(range(total_possible)) - visited
            if unreachable:
                self.unreachable_states = unreachable

    def get_unreachable_states(self) -> Set[int]:
        """Returns the set of discovered unreachable FSM states."""
        return self.unreachable_states

    def get_dont_cares_for_inputs(self, pruned_inputs: List[str], true_minterms: List[int]) -> List[int]:
        """Maps unreachable FSM states to don't-cares if inputs match state registers."""
        dont_cares: List[int] = []
        if not self.unreachable_states:
            return dont_cares

        import re
        fsm_regs = [r for r in self.dag.registers.values() if "state" in r.name]
        for reg in fsm_regs:
            reg_bits = [f"{reg.name}[{b}]" for b in range(reg.width)]
            if len(pruned_inputs) == reg.width and set(pruned_inputs) == set(reg_bits):
                for unreach_st in self.unreachable_states:
                    row_idx = 0
                    for p_idx, p_name in enumerate(pruned_inputs):
                        m = re.search(r"\[(\d+)\]", p_name)
                        b = int(m.group(1)) if m else 0
                        bit_val = (unreach_st >> b) & 1
                        row_idx |= (bit_val << p_idx)
                    if row_idx not in true_minterms and row_idx not in dont_cares:
                        dont_cares.append(row_idx)
        return sorted(dont_cares)
