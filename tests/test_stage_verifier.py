"""Unit & Regression Tests for Stage-by-Stage Logic Equivalence Verification.

Verifies that arrays of values generated after every transformation stage:
- Stage 0: Golden RTL Reference (FFs removed)
- Stage 1: Multi-Level DAG Slicer
- Stage 2: Local Truth Tables & Variable Pruning
- Stage 3: Technology-Mapped CMOS Gates
- Stage 4: Cadence Verilog-A Behavioral Model
match the original Verilog RTL semantics across all input stimulus vectors.

100% standard library. Zero external dependencies. Compatible with Python 3.9+.
"""

from __future__ import annotations
import os
import unittest

from ams_optimizer import AMSOptimizer
from ams_optimizer.core.stage_verifier import StageByStageVerifier

EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")


class TestStageVerifier(unittest.TestCase):
    def test_stage_verify_sar_adc_ctrl(self):
        with open(os.path.join(EXAMPLES_DIR, "sar_adc_ctrl.v"), "r") as f:
            code = f.read()

        opt = AMSOptimizer(run_verification=False)
        res = opt.run(code)
        verifier = StageByStageVerifier(code, res.dag, res.mapped_nodes)
        rep = verifier.run_verification()

        self.assertTrue(rep.passed, f"SAR ADC Ctrl stage verification failed: {rep.mismatches}")
        self.assertEqual(len(rep.mismatches), 0)
        self.assertEqual(rep.total_vectors, 1024)

    def test_stage_verify_pwm_ctrl(self):
        with open(os.path.join(EXAMPLES_DIR, "PWM_CTRL.v"), "r") as f:
            code = f.read()

        opt = AMSOptimizer(run_verification=False)
        res = opt.run(code)
        verifier = StageByStageVerifier(code, res.dag, res.mapped_nodes)
        rep = verifier.run_verification(max_vectors=512)

        self.assertTrue(rep.passed, f"PWM CTRL stage verification failed: {rep.mismatches}")
        self.assertEqual(len(rep.mismatches), 0)
        self.assertEqual(rep.total_vectors, 512)

    def test_stage_verify_gray_counter(self):
        with open(os.path.join(EXAMPLES_DIR, "gray_counter.v"), "r") as f:
            code = f.read()

        opt = AMSOptimizer(run_verification=False)
        res = opt.run(code)
        verifier = StageByStageVerifier(code, res.dag, res.mapped_nodes)
        rep = verifier.run_verification()

        self.assertTrue(rep.passed, f"Gray Counter stage verification failed: {rep.mismatches}")
        self.assertEqual(len(rep.mismatches), 0)
        self.assertEqual(rep.total_vectors, 16)

    def test_stage_verify_bandgap_trim_fsm(self):
        with open(os.path.join(EXAMPLES_DIR, "bandgap_trim_fsm.v"), "r") as f:
            code = f.read()

        opt = AMSOptimizer(run_verification=False)
        res = opt.run(code)
        verifier = StageByStageVerifier(code, res.dag, res.mapped_nodes)
        rep = verifier.run_verification()

        self.assertTrue(rep.passed, f"Bandgap Trim FSM stage verification failed: {rep.mismatches}")
        self.assertEqual(len(rep.mismatches), 0)
        self.assertEqual(rep.total_vectors, 64)

    def test_stage_verify_clock_divider_rst(self):
        with open(os.path.join(EXAMPLES_DIR, "clock_divider_rst.v"), "r") as f:
            code = f.read()

        opt = AMSOptimizer(run_verification=False)
        res = opt.run(code)
        verifier = StageByStageVerifier(code, res.dag, res.mapped_nodes)
        rep = verifier.run_verification()

        self.assertTrue(rep.passed, f"Clock Divider stage verification failed: {rep.mismatches}")
        self.assertEqual(len(rep.mismatches), 0)
        self.assertEqual(rep.total_vectors, 1024)


if __name__ == "__main__":
    unittest.main()
