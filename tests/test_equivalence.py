"""Formal Logic Equivalence Checking (LEC) Regression Tests.

100% standard library. Compatible with Python 3.9+.
Zero external dependencies.
"""

from __future__ import annotations
import os
import unittest

from ams_optimizer import AMSOptimizer
from ams_optimizer.core.equivalence_checker import FormalEquivalenceChecker
from ams_optimizer.core.models import MappedLogicNode

EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")


class TestEquivalenceChecker(unittest.TestCase):
    def setUp(self):
        self.optimizer = AMSOptimizer(supply_voltage=1.8, threshold_voltage=0.9, run_verification=True)

    def test_pwm_ctrl_equivalence(self):
        with open(os.path.join(EXAMPLES_DIR, "PWM_CTRL.v"), "r") as f:
            code = f.read()

        result = self.optimizer.run(code)
        self.assertIsNotNone(result.equivalence_result)
        eq = result.equivalence_result
        self.assertTrue(eq.passed, f"PWM_CTRL verification failed: {eq.mismatches}")
        self.assertEqual(len(eq.mismatches), 0)
        self.assertEqual(eq.total_vectors, 512)
        self.assertEqual(eq.matching_vectors, 512)
        self.assertIn("en_LP", eq.verified_signals)
        self.assertIn("oc_select", eq.verified_signals)

    def test_gray_counter_equivalence(self):
        with open(os.path.join(EXAMPLES_DIR, "gray_counter.v"), "r") as f:
            code = f.read()

        result = self.optimizer.run(code)
        self.assertIsNotNone(result.equivalence_result)
        eq = result.equivalence_result
        self.assertTrue(eq.passed, f"gray_counter verification failed: {eq.mismatches}")
        self.assertEqual(len(eq.mismatches), 0)
        self.assertEqual(eq.total_vectors, 16)
        self.assertEqual(eq.matching_vectors, 16)
        self.assertIn("count_gray[0]", eq.verified_signals)
        self.assertIn("q[0]_d", eq.verified_signals)

    def test_sar_adc_ctrl_equivalence(self):
        with open(os.path.join(EXAMPLES_DIR, "sar_adc_ctrl.v"), "r") as f:
            code = f.read()

        result = self.optimizer.run(code)
        self.assertIsNotNone(result.equivalence_result)
        eq = result.equivalence_result
        self.assertTrue(eq.passed, f"sar_adc_ctrl verification failed: {eq.mismatches}")
        self.assertEqual(len(eq.mismatches), 0)
        self.assertEqual(eq.total_vectors, 1024)
        self.assertEqual(eq.matching_vectors, 1024)
        self.assertIn("state[0]_d", eq.verified_signals)
        self.assertIn("dac_reg[0]_d", eq.verified_signals)

    def test_bandgap_trim_fsm_equivalence(self):
        with open(os.path.join(EXAMPLES_DIR, "bandgap_trim_fsm.v"), "r") as f:
            code = f.read()

        result = self.optimizer.run(code)
        self.assertIsNotNone(result.equivalence_result)
        eq = result.equivalence_result
        self.assertTrue(eq.passed, f"bandgap_trim_fsm verification failed: {eq.mismatches}")
        self.assertEqual(len(eq.mismatches), 0)
        self.assertEqual(eq.total_vectors, 64)
        self.assertEqual(eq.matching_vectors, 64)
        self.assertIn("trim_reg[0]_d", eq.verified_signals)
        self.assertIn("trim_done", eq.verified_signals)

    def test_clock_divider_rst_equivalence(self):
        with open(os.path.join(EXAMPLES_DIR, "clock_divider_rst.v"), "r") as f:
            code = f.read()

        result = self.optimizer.run(code)
        self.assertIsNotNone(result.equivalence_result)
        eq = result.equivalence_result
        self.assertTrue(eq.passed, f"clock_divider_rst verification failed: {eq.mismatches}")
        self.assertEqual(len(eq.mismatches), 0)
        self.assertEqual(eq.total_vectors, 1024)
        self.assertEqual(eq.matching_vectors, 1024)
        self.assertIn("cnt_reg[0]_d", eq.verified_signals)
        self.assertIn("clk_out", eq.verified_signals)

    def test_mutation_detection(self):
        """Inject an intentional logic corruption into mapped gates to verify the checker catches errors."""
        with open(os.path.join(EXAMPLES_DIR, "gray_counter.v"), "r") as f:
            code = f.read()

        # Run optimizer without verification first
        opt = AMSOptimizer(supply_voltage=1.8, threshold_voltage=0.9, run_verification=False)
        result = opt.run(code)
        self.assertIsNone(result.equivalence_result)

        # Mutate one of the mapped gates for count_gray[0]
        corrupted_nodes = dict(result.mapped_nodes)
        orig_node = corrupted_nodes["count_gray[0]"]
        corrupted_nodes["count_gray[0]"] = MappedLogicNode(
            node_name="count_gray[0]",
            expression=f"INV({orig_node.expression})",
            cells_used=orig_node.cells_used,
            gate_counts=orig_node.gate_counts,
        )

        checker = FormalEquivalenceChecker(result.dag, corrupted_nodes)
        eq = checker.verify()

        self.assertFalse(eq.passed)
        self.assertGreater(len(eq.mismatches), 0)
        mismatch_signals = {m["signal"] for m in eq.mismatches}
        self.assertIn("count_gray[0]", mismatch_signals)


if __name__ == "__main__":
    unittest.main()
