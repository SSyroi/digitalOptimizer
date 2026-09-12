"""Formal Logic Equivalence Checker for AMS Synthesizer."""

from __future__ import annotations
import itertools
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import sympy
from sympy.logic.boolalg import Boolean, simplify_logic
from .ast_parser import ParsedModule
from .library import Library
from .synthesizer import LogicNode, SynthesizedCone

@dataclass
class EquivalenceResult:
    is_equivalent: bool
    signal_results: Dict[str, bool] = field(default_factory=dict)
    mismatches: List[str] = field(default_factory=list)
    tested_patterns_count: int = 0
    message: str = ""


class LogicVerifier:
    """Formally verifies that synthesized gate expressions match the original RTL equations."""

    def __init__(self, library: Library):
        self.library = library

    def verify_module(
        self,
        parsed: ParsedModule,
        cones: Dict[str, SynthesizedCone],
    ) -> EquivalenceResult:
        """Verify all register D-inputs and combinational outputs against original RTL expressions."""
        signal_results = {}
        mismatches = []
        total_patterns = 0

        # Verify each register D-input
        for reg in parsed.registers:
            target = reg.name
            if target in cones and reg.d_expr_bool is not None:
                equiv, patterns, err = self._verify_cone(reg.d_expr_bool, cones[target].root)
                total_patterns += patterns
                signal_results[target] = equiv
                if not equiv:
                    mismatches.append(f"Register D-input '{target}': {err}")

        # Verify each combinational output
        for comb in parsed.comb_assignments:
            target = comb.target
            if target in cones and comb.expr_bool is not None:
                equiv, patterns, err = self._verify_cone(comb.expr_bool, cones[target].root)
                total_patterns += patterns
                signal_results[target] = equiv
                if not equiv:
                    mismatches.append(f"Combinational output '{target}': {err}")

        all_ok = len(mismatches) == 0 and len(signal_results) > 0
        msg = (
            f"Formal Verification PASSED: {len(signal_results)} signals verified across {total_patterns} state evaluations (100% equivalent)."
            if all_ok
            else f"Formal Verification FAILED: {len(mismatches)} mismatches detected."
        )

        return EquivalenceResult(
            is_equivalent=all_ok,
            signal_results=signal_results,
            mismatches=mismatches,
            tested_patterns_count=total_patterns,
            message=msg,
        )

    def _verify_cone(self, orig_bool: Boolean, synth_root: LogicNode) -> Tuple[bool, int, str]:
        """Exhaustively compare truth table of original Boolean expression vs synthesized gate tree."""
        # Extract all input variables
        orig_symbols = orig_bool.free_symbols
        synth_symbols_str = synth_root.get_leaves()
        synth_symbols = {sympy.Symbol(re.sub(r"([a-zA-Z_][a-zA-Z0-9_]*)\[(\d+)\]", r"\1_\2_", s)) for s in synth_symbols_str if s not in ("1'b1", "1'b0", "True", "False")}

        all_syms = list(orig_symbols.union(synth_symbols))

        # Test all 2^N combinations (for AMS blocks N is typically <= 12)
        if len(all_syms) > 16:
            # For very large cones, use SymPy SAT / logic equivalence simplification
            synth_bool = self._node_to_sympy(synth_root)
            is_eq = simplify_logic(sympy.Equivalent(orig_bool, synth_bool)) is sympy.true
            return is_eq, 1, "" if is_eq else "Symbolic equivalence check failed"

        patterns = 2 ** len(all_syms)
        for bit_comb in itertools.product([False, True], repeat=len(all_syms)):
            env = dict(zip(all_syms, bit_comb))
            # 1. Evaluate original
            val_orig = bool(orig_bool.subs(env))

            # 2. Evaluate synthesized gate tree
            # Convert environment back to signal names
            env_signals = {re.sub(r"([a-zA-Z_][a-zA-Z0-9_]*)_(\d+)_", r"\1[\2]", str(k)): v for k, v in env.items()}
            env_signals["1'b1"] = True
            env_signals["1'b0"] = False
            val_synth = self._eval_node(synth_root, env_signals)

            if val_orig != val_synth:
                return False, patterns, f"Mismatch at input pattern {env_signals} (Orig={val_orig}, Synth={val_synth})"

        return True, patterns, ""

    def _eval_node(self, node: LogicNode, env: Dict[str, bool]) -> bool:
        """Evaluate logic node recursively."""
        if node.gate_type == "WIRE":
            sig = str(node.inputs[0]) if node.inputs else node.output_name
            return env.get(sig, False)

        evaluated_inputs = []
        for inp in node.inputs:
            if isinstance(inp, str):
                evaluated_inputs.append(env.get(inp, False))
            elif isinstance(inp, LogicNode):
                evaluated_inputs.append(self._eval_node(inp, env))

        cell = self.library.get_cell(node.gate_type)
        if not cell:
            # Fallback evaluation for standard gates
            return self._fallback_eval(node.gate_type, evaluated_inputs)

        pin_map = {pin: evaluated_inputs[idx] for idx, pin in enumerate(cell.inputs)}
        return cell.evaluate(pin_map)

    def _fallback_eval(self, gtype: str, inps: List[bool]) -> bool:
        if gtype == "INV":
            return not inps[0]
        elif gtype.startswith("NAND"):
            return not all(inps)
        elif gtype.startswith("NOR"):
            return not any(inps)
        elif gtype.startswith("AND"):
            return all(inps)
        elif gtype.startswith("OR"):
            return any(inps)
        elif gtype == "XOR2":
            return inps[0] ^ inps[1]
        elif gtype == "XNOR2":
            return not (inps[0] ^ inps[1])
        elif gtype == "MUX2":
            s, d0, d1 = inps[0], inps[1], inps[2]
            return d1 if s else d0
        return False

    def _node_to_sympy(self, node: LogicNode) -> Boolean:
        """Convert synthesized logic node back to SymPy boolean expression."""
        if node.gate_type == "WIRE":
            s = str(node.inputs[0]) if node.inputs else node.output_name
            if s in ("1'b1", "True"):
                return sympy.true
            if s in ("1'b0", "False"):
                return sympy.false
            return sympy.Symbol(re.sub(r"([a-zA-Z_][a-zA-Z0-9_]*)\[(\d+)\]", r"\1_\2_", s))

        in_exprs = [self._node_to_sympy(inp) if isinstance(inp, LogicNode) else (sympy.true if inp == "1'b1" else (sympy.false if inp == "1'b0" else sympy.Symbol(re.sub(r"([a-zA-Z_][a-zA-Z0-9_]*)\[(\d+)\]", r"\1_\2_", inp)))) for inp in node.inputs]

        if node.gate_type == "INV":
            return sympy.Not(in_exprs[0])
        elif node.gate_type.startswith("NAND"):
            return sympy.Not(sympy.And(*in_exprs))
        elif node.gate_type.startswith("NOR"):
            return sympy.Not(sympy.Or(*in_exprs))
        elif node.gate_type.startswith("AND"):
            return sympy.And(*in_exprs)
        elif node.gate_type.startswith("OR"):
            return sympy.Or(*in_exprs)
        elif node.gate_type == "XOR2":
            return sympy.Xor(in_exprs[0], in_exprs[1])
        elif node.gate_type == "MUX2":
            s, d0, d1 = in_exprs[0], in_exprs[1], in_exprs[2]
            return sympy.Or(sympy.And(s, d1), sympy.And(sympy.Not(s), d0))

        return sympy.true
