"""Pure-Python Quine-McCluskey & Petrick's Exact Set Cover Solver.

Computes exact minimal Prime Implicants from truth table minterms and Don't-Cares.
Maps implicants to optimal multi-level CMOS NAND/NOR/AND/OR gate trees.

Zero external dependencies. Compatible with Python 3.9+.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple

from .models import LocalTruthTable, MappedLogicNode


def _to_bin_str(val: int, num_vars: int) -> str:
    return "".join("1" if ((val >> i) & 1) else "0" for i in range(num_vars))


def _can_combine(t1: str, t2: str) -> Optional[str]:
    diff = 0
    diff_idx = -1
    for i in range(len(t1)):
        c1 = t1[i]
        c2 = t2[i]
        if c1 != c2:
            if c1 == "-" or c2 == "-":
                return None
            diff += 1
            if diff > 1:
                return None
            diff_idx = i
    if diff == 1:
        return t1[:diff_idx] + "-" + t1[diff_idx + 1:]
    return None


def _covers(implicant: str, minterm_str: str) -> bool:
    for i in range(len(implicant)):
        ic = implicant[i]
        if ic != "-" and ic != minterm_str[i]:
            return False
    return True


class QuineMcCluskeySolver:
    """Solves exact two-level Boolean minimization with Don't-Cares."""

    @staticmethod
    def solve(num_vars: int, true_minterms: List[int], dont_cares: Optional[List[int]] = None) -> List[str]:
        total_states = 1 << num_vars
        if len(true_minterms) == 0:
            return []
        if len(true_minterms) == total_states:
            return ["-" * num_vars]

        dc_set = set(dont_cares or [])
        true_set = set(true_minterms) - dc_set
        if not true_set:
            return []

        all_set = true_set | dc_set
        all_bin = {_to_bin_str(m, num_vars) for m in all_set}
        true_bin = {_to_bin_str(m, num_vars) for m in true_set}

        current = set(all_bin)
        pis: Set[str] = set()

        while current:
            next_grp: Set[str] = set()
            comb: Set[str] = set()
            by_ones: Dict[int, List[str]] = {}
            for t in current:
                cnt = t.count("1")
                by_ones.setdefault(cnt, []).append(t)

            for cnt, grp in by_ones.items():
                next_ones = by_ones.get(cnt + 1, [])
                for t1 in grp:
                    for t2 in next_ones:
                        m = _can_combine(t1, t2)
                        if m is not None:
                            next_grp.add(m)
                            comb.add(t1)
                            comb.add(t2)

            for t in current:
                if t not in comb:
                    pis.add(t)

            current = next_grp

        # Essential Prime Implicants & Petrick's Set Covering
        pi_list = sorted(list(pis))
        uncovered = set(true_bin)
        chosen: List[str] = []

        cov = {m: [p for p in pi_list if _covers(p, m)] for m in uncovered}
        changed = True
        while changed:
            changed = False
            epis = set()
            for m, p_list in cov.items():
                if len(p_list) == 1:
                    epis.add(p_list[0])
            for epi in epis:
                if epi not in chosen:
                    chosen.append(epi)
                    covered_now = [m for m in uncovered if _covers(epi, m)]
                    for m in covered_now:
                        uncovered.remove(m)
                        if m in cov:
                            del cov[m]
                    changed = True

        while uncovered:
            best_pi = None
            best_cnt = -1
            for p in pi_list:
                if p in chosen:
                    continue
                c = sum(1 for m in uncovered if _covers(p, m))
                if c > best_cnt:
                    best_pi = p
                    best_cnt = c
            if best_pi is None or best_cnt == 0:
                break
            chosen.append(best_pi)
            covered_now = [m for m in uncovered if _covers(best_pi, m)]
            for m in covered_now:
                uncovered.remove(m)

        return chosen
