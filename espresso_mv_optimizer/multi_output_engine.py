"""Unified Multi-Output Espresso-MV Minimization Engine.

Runs Berkeley Espresso-MV across all circuit outputs jointly to discover
globally shared product terms.
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple
from pyeda.inter import exprvar, truthtable, espresso_tts
from pyeda.boolalg.expr import OrOp, AndOp, Variable, Complement, Expression


class MultiOutputEspressoEngine:
    """Minimizes all combinational outputs simultaneously via Espresso-MV."""

    def __init__(self, input_names: List[str]):
        self.input_names = input_names
        self.k = len(input_names)
        self.py_vars = [exprvar(f"x_{i}") for i in range(self.k)]

    def solve(self, table_strings: Dict[str, str]) -> Tuple[Dict[str, Expression], Dict[str, Set[str]]]:
        """Runs joint Espresso-MV on all truth tables.
        
        Returns:
            min_exprs: Dict[output_name, pyeda_expression]
            shared_cubes: Dict[cube_str, Set[output_names_using_cube]]
        """
        target_names = list(table_strings.keys())
        tts = [truthtable(self.py_vars, table_strings[name]) for name in target_names]

        # Single joint Espresso-MV call
        raw_results = espresso_tts(*tts)

        min_exprs: Dict[str, Expression] = {}
        shared_cubes: Dict[str, Set[str]] = {}

        for name, expr in zip(target_names, raw_results):
            min_exprs[name] = expr

            # Extract individual cubes
            if isinstance(expr, OrOp):
                cubes = list(expr.xs)
            elif str(expr) in ["0", "1"]:
                cubes = []
            else:
                cubes = [expr]

            for c in cubes:
                c_str = str(c)
                if c_str not in shared_cubes:
                    shared_cubes[c_str] = set()
                shared_cubes[c_str].add(name)

        return min_exprs, shared_cubes
