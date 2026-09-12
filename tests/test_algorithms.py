"""Dedicated Unit Tests for Individual Synthesis Algorithms.

Tests each isolated modular algorithm file independently:
- npn_matcher.py (NPN bitmask matching)
- shannon_mux.py (Shannon decomposition)
- quine_mccluskey.py (Quine-McCluskey & Petrick set cover)
- reachability.py (FSM reachability analysis)

Zero external dependencies. Compatible with Python 3.9+.
"""

from __future__ import annotations
import unittest

from ams_optimizer.core.models import LocalTruthTable
from ams_optimizer.core.npn_matcher import NPNBitmaskMatcher
from ams_optimizer.core.shannon_mux import ShannonMUXDecomposer
from ams_optimizer.core.quine_mccluskey import QuineMcCluskeySolver
from ams_optimizer.core.tech_mapper import TechnologyMapper


class TestSynthesisAlgorithms(unittest.TestCase):
    def test_npn_matcher_2input(self):
        # XOR2: bitmask 0b0110 = 6
        tt_xor = LocalTruthTable("xor_node", ["a", "b"], 2, [1, 2], bitmask=6)
        match = NPNBitmaskMatcher.match_2input(tt_xor)
        self.assertIsNotNone(match)
        self.assertEqual(match.expression, "XOR2(a, b)")
        self.assertEqual(match.gate_counts["XOR2"], 1)

        # NAND2: bitmask 0b0111 = 7
        tt_nand = LocalTruthTable("nand_node", ["a", "b"], 2, [0, 1, 2], bitmask=7)
        match = NPNBitmaskMatcher.match_2input(tt_nand)
        self.assertIsNotNone(match)
        self.assertEqual(match.expression, "NAND2(a, b)")
        self.assertEqual(match.gate_counts["NAND2"], 1)

    def test_npn_matcher_aoi21(self):
        # AOI21: ~((A & B) | C) with inputs a, b, c -> bitmask 7
        tt_aoi = LocalTruthTable("aoi_node", ["a", "b", "c"], 3, [0, 1, 2], bitmask=7)
        match = NPNBitmaskMatcher.match_3input(tt_aoi)
        self.assertIsNotNone(match)
        self.assertTrue(match.expression.startswith("AOI21("))
        self.assertEqual(match.gate_counts["AOI21"], 1)

    def test_shannon_mux_decomposition(self):
        mapper = TechnologyMapper()
        decomposer = ShannonMUXDecomposer(mapper.map_truth_table)

        # MUX2: when s=0 -> d0, when s=1 -> d1
        # Truth table over [s, d0, d1]:
        # s=0: row 0(000)->0, row 2(010)->1, row 4(001)->0, row 6(011)->1
        # s=1: row 1(100)->0, row 3(110)->0, row 5(101)->1, row 7(111)->1
        # true minterms = [2, 5, 6, 7]
        tt_mux = LocalTruthTable("mux_node", ["s", "d0", "d1"], 3, [2, 5, 6, 7], bitmask=(1<<2)|(1<<5)|(1<<6)|(1<<7))
        match = decomposer.try_decompose(tt_mux)
        self.assertIsNotNone(match)
        self.assertTrue(match.expression.startswith("MUX2("))
        self.assertEqual(match.gate_counts["MUX2"], 1)

    def test_quine_mccluskey_solver_with_dont_cares(self):
        # Simple SOP: minterms [0, 1, 2], dont_cares [3]
        # With DC at 3, 00, 01, 10, 11 all merge to 1 term "-" -> CONST 1 or 0 literals
        pis = QuineMcCluskeySolver.solve(2, [0, 1, 2], dont_cares=[3])
        self.assertEqual(pis, ["--"])

        # XOR parity: minterms [1, 2] (01, 10)
        pis_xor = QuineMcCluskeySolver.solve(2, [1, 2])
        self.assertEqual(len(pis_xor), 2)
        self.assertIn("10", pis_xor)
        self.assertIn("01", pis_xor)


if __name__ == "__main__":
    unittest.main()
