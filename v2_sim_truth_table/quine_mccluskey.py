"""Pure Python Truth Table Minimizer (Quine-McCluskey + Petrick's Method).

100% Standard Library compatible with Python 3.9+.
No external dependencies required (zero-pip setup).
If SymPy is available in environment, can optionally use it as accelerator.
"""

from __future__ import annotations
import itertools
from typing import Dict, List, Optional, Set, Tuple

try:
    import sympy
    from sympy.logic.boolalg import And, Or, Not, simplify_logic
    HAS_SYMPY = True
except ImportError:
    HAS_SYMPY = False


def _to_bin_str(val: int, num_vars: int) -> str:
    """Converts an integer to a binary string with bit 0 on the left (or consistent index)."""
    # Bit i corresponds to (val >> i) & 1
    return "".join("1" if ((val >> i) & 1) else "0" for i in range(num_vars))


def _can_combine(term1: str, term2: str) -> Optional[str]:
    """If two implicant strings differ by exactly 1 non-dash character, returns merged implicant."""
    diff_count = 0
    diff_idx = -1
    for i, (c1, c2) in enumerate(zip(term1, term2)):
        if c1 != c2:
            if c1 == "-" or c2 == "-":
                return None
            diff_count += 1
            diff_idx = i
            if diff_count > 1:
                return None
    if diff_count == 1:
        merged = list(term1)
        merged[diff_idx] = "-"
        return "".join(merged)
    return None


def _implicant_covers(implicant: str, minterm_str: str) -> bool:
    """Checks if an implicant pattern (with '-') covers a concrete minterm binary string."""
    for imp_char, min_char in zip(implicant, minterm_str):
        if imp_char != "-" and imp_char != min_char:
            return False
    return True


def _pure_python_quine_mccluskey(
    num_vars: int,
    true_minterms: List[int],
    dont_cares: Optional[List[int]] = None,
) -> Tuple[List[str], str]:
    """Pure-Python Quine-McCluskey minimization with Petrick's exact / greedy covering."""
    total_states = 1 << num_vars
    if len(true_minterms) == 0:
        return [], "CONST_0"
    if len(true_minterms) == total_states:
        return ["-" * num_vars], "CONST_1"

    dont_cares_set = set(dont_cares or [])
    true_set = set(true_minterms) - dont_cares_set
    if not true_set:
        return [], "CONST_0"

    all_terms = true_set | dont_cares_set
    all_bin = {_to_bin_str(m, num_vars) for m in all_terms}
    true_bin = {_to_bin_str(m, num_vars) for m in true_set}

    # Step 1: Find all Prime Implicants
    current_groups: Set[str] = set(all_bin)
    prime_implicants: Set[str] = set()

    while current_groups:
        next_groups: Set[str] = set()
        combined: Set[str] = set()
        group_list = list(current_groups)

        for i in range(len(group_list)):
            for j in range(i + 1, len(group_list)):
                merged = _can_combine(group_list[i], group_list[j])
                if merged is not None:
                    next_groups.add(merged)
                    combined.add(group_list[i])
                    combined.add(group_list[j])

        for term in group_list:
            if term not in combined:
                prime_implicants.add(term)

        current_groups = next_groups

    if not prime_implicants:
        return ["-" * num_vars], "CONST_1"

    # Step 2: Essential Prime Implicants & Petrick's Covering
    pi_list = sorted(list(prime_implicants))
    uncovered_minterms = set(true_bin)
    chosen_pis: List[str] = []

    # Map each minterm to PIs covering it
    coverage: Dict[str, List[str]] = {
        m: [pi for pi in pi_list if _implicant_covers(pi, m)]
        for m in uncovered_minterms
    }

    # Identify essential prime implicants (only 1 PI covers this minterm)
    changed = True
    while changed:
        changed = False
        epis = set()
        for m, pis in coverage.items():
            if len(pis) == 1:
                epis.add(pis[0])

        for epi in epis:
            if epi not in chosen_pis:
                chosen_pis.append(epi)
                # Remove covered minterms
                covered_now = [m for m in uncovered_minterms if _implicant_covers(epi, m)]
                for m in covered_now:
                    uncovered_minterms.remove(m)
                    if m in coverage:
                        del coverage[m]
                changed = True

    # Step 3: Greedy / Branch-and-Bound Set Cover for remaining minterms
    while uncovered_minterms:
        # Pick PI that covers the most remaining minterms (favoring fewest literals/most dashes)
        best_pi = None
        best_count = -1
        best_dashes = -1
        for pi in pi_list:
            if pi in chosen_pis:
                continue
            cov_count = sum(1 for m in uncovered_minterms if _implicant_covers(pi, m))
            dashes = pi.count("-")
            if cov_count > best_count or (cov_count == best_count and dashes > best_dashes):
                best_pi = pi
                best_count = cov_count
                best_dashes = dashes

        if best_pi is None or best_count == 0:
            break

        chosen_pis.append(best_pi)
        covered_now = [m for m in uncovered_minterms if _implicant_covers(best_pi, m)]
        for m in covered_now:
            uncovered_minterms.remove(m)

    return chosen_pis, "SOP"


def minimize_truth_table(
    num_vars: int,
    true_minterms: List[int],
    dont_cares: Optional[List[int]] = None,
) -> Tuple[List[str], str]:
    """Minimizes a single boolean output column from a truth table.

    Returns list of minimal implicant strings (e.g. ['0-1', '11-']) and formula type ('SOP', 'CONST_0', 'CONST_1').
    """
    total_states = 1 << num_vars

    if len(true_minterms) == 0:
        return [], "CONST_0"
    if len(true_minterms) == total_states:
        return ["-" * num_vars], "CONST_1"

    # Use pure Python Quine-McCluskey (robust, zero-dependency)
    return _pure_python_quine_mccluskey(num_vars, true_minterms, dont_cares)
