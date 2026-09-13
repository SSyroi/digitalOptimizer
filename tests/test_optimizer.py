"""Comprehensive Unit & Integration Test Suite for AMS Digital Optimizer.

100% standard library. Compatible with Python 3.9+.
Zero external dependencies.
"""

from __future__ import annotations
import os
import unittest

from ams_optimizer import AMSOptimizer

EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")


class TestAMSOptimizer(unittest.TestCase):
    def setUp(self):
        self.optimizer = AMSOptimizer(supply_voltage=1.8, threshold_voltage=0.9)

    def test_pwm_ctrl_multi_level_sharing(self):
        with open(os.path.join(EXAMPLES_DIR, "PWM_CTRL.v"), "r") as f:
            code = f.read()

        result = self.optimizer.run(code)
        self.assertEqual(result.module_name, "PWM_CTRL")
        
        # 1. Multi-level intermediate conditions must be identified
        self.assertIn("is_az_mode", result.mapped_nodes)
        self.assertIn("is_chop_mode", result.mapped_nodes)
        self.assertIn("is_pwm_active_window", result.mapped_nodes)
        self.assertIn("is_pwm_sample_window", result.mapped_nodes)

        # 2. Gate count must be < 150 cells (eliminating the 594-cell flat explosion)
        self.assertLess(result.total_gates, 150)
        self.assertIn("MUX2", result.gate_breakdown)
        self.assertIn("NOR2", result.gate_breakdown)

        # 3. Verilog-A compliance
        self.assertIn("analog begin", result.veriloga_code)
        self.assertIn("@(initial_step", result.veriloga_code)
        self.assertIn("@(cross", result.veriloga_code)
        self.assertIn("V(en_LP) <+ transition", result.veriloga_code)
        self.assertIn("V(oc_select) <+ transition", result.veriloga_code)

    def test_gray_counter_xor_matching(self):
        with open(os.path.join(EXAMPLES_DIR, "gray_counter.v"), "r") as f:
            code = f.read()

        result = self.optimizer.run(code)
        self.assertEqual(result.module_name, "gray_counter")
        self.assertIn("XOR2", result.gate_breakdown)
        self.assertEqual(result.gate_breakdown["DFFR"], 3)
        self.assertIn("V(count_gray[0]) <+ transition", result.veriloga_code)
        self.assertIn("V(count_bin[0]) <+ transition", result.veriloga_code)

    def test_sar_adc_ctrl(self):
        with open(os.path.join(EXAMPLES_DIR, "sar_adc_ctrl.v"), "r") as f:
            code = f.read()

        result = self.optimizer.run(code)
        self.assertEqual(result.module_name, "sar_adc_ctrl")
        self.assertEqual(result.gate_breakdown["DFFR"], 8)
        self.assertIn("dac_reg[0]_d", result.mapped_nodes)
        self.assertIn("V(dac_code[0]) <+ transition", result.veriloga_code)
        self.assertIn("V(eoc) <+ transition", result.veriloga_code)

    def test_bandgap_trim_fsm(self):
        with open(os.path.join(EXAMPLES_DIR, "bandgap_trim_fsm.v"), "r") as f:
            code = f.read()

        result = self.optimizer.run(code)
        self.assertEqual(result.module_name, "bandgap_trim_fsm")
        self.assertEqual(result.gate_breakdown["DFFR"], 4)
        self.assertIn("trim_reg[0]_d", result.mapped_nodes)
        self.assertIn("V(trim_done) <+ transition", result.veriloga_code)

    def test_clock_divider_rst(self):
        with open(os.path.join(EXAMPLES_DIR, "clock_divider_rst.v"), "r") as f:
            code = f.read()

        result = self.optimizer.run(code)
        self.assertEqual(result.module_name, "clock_divider_rst")
        self.assertIn("cnt_reg[0]_d", result.mapped_nodes)
        self.assertIn("V(count[0]) <+ transition", result.veriloga_code)
        self.assertIn("V(clk_out) <+ transition", result.veriloga_code)


if __name__ == "__main__":
    unittest.main()
