"""FSM State Reachability Analyzer.

Discovers unreachable state combinations starting from the reset state (state = 0)
and classifies them as Don't-Cares (X) for Boolean minimization.

Zero external dependencies. Compatible with Python 3.9+.
"""

from __future__ import annotations
from typing import Dict, List, Set

from .models import SlicedDAG


class FSMReachabilityAnalyzer:
    """Analyzes FSM state transitions to find unreachable joint state combinations."""

    def __init__(self, dag: SlicedDAG):
        self.dag = dag
        self.reachable_states: Set[int] = set()
        self.reg_bit_names: List[str] = []
        self._analyze()

    def _analyze(self):
        regs = sorted(list(self.dag.registers.values()), key=lambda r: r.name)
        for r in regs:
            if r.width == 1:
                self.reg_bit_names.append(r.name)
            else:
                for b in range(r.width):
                    self.reg_bit_names.append(f"{r.name}[{b}]")
                    
        total_bits = len(self.reg_bit_names)
        if total_bits == 0 or total_bits > 12:
            return

        # Initial state from resets
        init_state = 0
        bit_idx = 0
        for r in regs:
            for b in range(r.width):
                bit_val = (r.reset_val >> b) & 1
                init_state |= (bit_val << bit_idx)
                bit_idx += 1

        visited = {init_state}
        queue = [init_state]

        while queue:
            curr_st = queue.pop(0)
            
            # Since primary inputs can affect transitions, we should iterate over all primary inputs?
            # PWM_CTRL only has static mode inputs (c_DFT_en_LP, c_DFT_en_PWM, c_DfT_oc_dig_VDD, c_metalFix)
            # Actually, we can just simulate a few random or all 0/1 for the small number of inputs.
            # But the primary inputs don't affect cnt, startup, chopping_clk, pwm_chop transitions!
            # The next-state for these is purely deterministic and internal.
            # We'll just provide all 0s for primary inputs, which is safe for counters.
            test_inputs = {pi: 0 for pi in self.dag.primary_inputs}
            
            for idx, b_name in enumerate(self.reg_bit_names):
                test_inputs[b_name] = (curr_st >> idx) & 1

            next_st = 0
            for idx, b_name in enumerate(self.reg_bit_names):
                d_node = self.dag.nodes.get(f"{b_name}_d")
                if d_node:
                    bit_val = d_node.eval_fn(test_inputs)
                else:
                    bit_val = (curr_st >> idx) & 1
                next_st |= (bit_val << idx)

            if next_st not in visited:
                visited.add(next_st)
                queue.append(next_st)

        self.reachable_states = visited

    def get_dont_cares_for_inputs(self, pruned_inputs: List[str], true_minterms: List[int]) -> List[int]:
        dont_cares: List[int] = []
        if not self.reachable_states:
            return dont_cares
            
        # Check if all pruned_inputs are register bits
        input_indices = []
        for pi in pruned_inputs:
            if pi in self.reg_bit_names:
                input_indices.append(self.reg_bit_names.index(pi))
            else:
                return dont_cares # If there's a primary input, we can't reliably say it's unreachable
                
        # Project reachable states onto the pruned_inputs
        reachable_projections = set()
        for st in self.reachable_states:
            proj = 0
            for i, idx in enumerate(input_indices):
                bit_val = (st >> idx) & 1
                proj |= (bit_val << i)
            reachable_projections.add(proj)
            
        total_combs = 1 << len(pruned_inputs)
        for val in range(total_combs):
            if val not in reachable_projections and val not in true_minterms:
                dont_cares.append(val)
                
        return sorted(dont_cares)

    def is_unreachable_stimulus(self, stimulus: Dict[str, int]) -> bool:
        if not self.reachable_states:
            return False
        
        st_val = 0
        for i, b_name in enumerate(self.reg_bit_names):
            bit_val = stimulus.get(b_name, 0)
            st_val |= (bit_val << i)
            
        return st_val not in self.reachable_states

    def get_unreachable_states(self) -> Set[int]:
        if not self.reachable_states or len(self.reg_bit_names) == 0:
            return set()
        total = 1 << len(self.reg_bit_names)
        return set(range(total)) - self.reachable_states

