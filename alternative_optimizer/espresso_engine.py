"""Berkeley Espresso minimization engine via pyeda.

Supports single-output and multi-output heuristic two-level logic minimization
with full support for don't-care (DC) conditions.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple, Union
from pyeda.inter import exprvar, truthtable, espresso_tts
from pyeda.boolalg.expr import OrOp, AndOp, NotOp, Variable, Complement, Expression

from ams_optimizer.core.models import LocalTruthTable


def pyeda_expr_to_string(expr: Expression) -> str:
    """Converts a pyeda expression into a clean Verilog-style expression."""
    if isinstance(expr, Variable):
        return str(expr.name)
    elif isinstance(expr, Complement):
        return f"~{expr.top.name}"
    elif isinstance(expr, AndOp):
        return "(" + " & ".join(pyeda_expr_to_string(x) for x in expr.xs) + ")"
    elif isinstance(expr, OrOp):
        return "(" + " | ".join(pyeda_expr_to_string(x) for x in expr.xs) + ")"
    elif str(expr) in ["0", "1"]:
        return str(expr)
    return str(expr)


class EspressoMinimizer:
    """Wrapper around Berkeley Espresso via pyeda."""

    @staticmethod
    def minimize_truth_table(tt: LocalTruthTable) -> Tuple[str, Expression]:
        """Minimizes a LocalTruthTable using Berkeley Espresso.
        
        Returns (expression_string, pyeda_expression).
        """
        k = tt.num_vars
        if k == 0:
            val = "1.0" if (0 in tt.true_minterms) else "0.0"
            return val, exprvar("__const__")

        if len(tt.true_minterms) == 0:
            return "0.0", exprvar("__const0__")

        if len(tt.true_minterms) == (1 << k):
            return "1.0", exprvar("__const1__")

        # Build pyeda truth table entries
        # pyeda variable order: inputs[0] is LSB (bit 0), inputs[-1] is MSB
        pyeda_vars = [exprvar(name.replace("[", "_").replace("]", "")) for name in tt.inputs]
        
        # Build truth table row string
        # Row i corresponds to (i >> bit) & 1 for pyeda_vars[bit]
        total_rows = 1 << k
        entries: List[str] = []
        true_set = set(tt.true_minterms)
        dc_set = set(tt.dont_cares)

        for row in range(total_rows):
            if row in true_set:
                entries.append("1")
            elif row in dc_set:
                entries.append("-")
            else:
                entries.append("0")

        tt_str = "".join(entries)
        py_tt = truthtable(pyeda_vars, tt_str)
        
        # Run Espresso
        min_tuple = espresso_tts(py_tt)
        min_expr = min_tuple[0]

        expr_str = pyeda_expr_to_string(min_expr)
        
        # Restore original input names if escaped
        for name in tt.inputs:
            esc = name.replace("[", "_").replace("]", "")
            if esc != name:
                expr_str = expr_str.replace(esc, name)

        return expr_str, min_expr

    @staticmethod
    def minimize_multi_output(tts: List[LocalTruthTable], shared_inputs: List[str]) -> List[Tuple[str, Expression]]:
        """Minimizes multiple LocalTruthTables simultaneously using Espresso-MV.
        
        Exploits shared product terms across multiple outputs.
        """
        k = len(shared_inputs)
        if k == 0 or not tts:
            return [EspressoMinimizer.minimize_truth_table(tt) for tt in tts]

        pyeda_vars = [exprvar(name.replace("[", "_").replace("]", "")) for name in shared_inputs]
        total_rows = 1 << k

        py_tts = []
        for tt in tts:
            # Map node minterms to shared_inputs space if needed
            true_set = set(tt.true_minterms)
            dc_set = set(tt.dont_cares)
            entries = []
            for row in range(total_rows):
                if row in true_set:
                    entries.append("1")
                elif row in dc_set:
                    entries.append("-")
                else:
                    entries.append("0")
            py_tts.append(truthtable(pyeda_vars, "".join(entries)))

        min_exprs = espresso_tts(*py_tts)
        results = []
        for min_expr, tt in zip(min_exprs, tts):
            expr_str = pyeda_expr_to_string(min_expr)
            for name in shared_inputs:
                esc = name.replace("[", "_").replace("]", "")
                if esc != name:
                    expr_str = expr_str.replace(esc, name)
            results.append((expr_str, min_expr))

        return results
