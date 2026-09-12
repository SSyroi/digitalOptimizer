"""Tests for v2 Simulation-Driven Truth Table Synthesizer."""

import unittest
from v2_sim_truth_table.optimizer import SimTruthTableOptimizer


class TestV2SimOptimizer(unittest.TestCase):
    def test_v2_gray_counter(self):
        with open("examples/gray_counter.v") as f:
            code = f.read()

        opt = SimTruthTableOptimizer()
        res = opt.run(code)

        self.assertIn("count_gray[0]", res.mapped_cones)
        self.assertIn("count_bin[0]", res.mapped_cones)
        self.assertIn("q[0]_d", res.mapped_cones)
        self.assertIn("analog begin", res.veriloga_code)
        self.assertIn("@(initial_step", res.veriloga_code)
        self.assertIn("@(cross", res.veriloga_code)

    def test_v2_sar_adc_ctrl(self):
        with open("examples/sar_adc_ctrl.v") as f:
            code = f.read()

        opt = SimTruthTableOptimizer()
        res = opt.run(code)

        self.assertIn("state[0]_d", res.mapped_cones)
        self.assertIn("eoc", res.mapped_cones)
        self.assertIn("dac_code[0]", res.mapped_cones)
        self.assertIn("V(dac_code[0]) <+ transition", res.veriloga_code)
        self.assertIn("V(eoc) <+ transition", res.veriloga_code)

    def test_v2_bandgap_trim(self):
        with open("examples/bandgap_trim_fsm.v") as f:
            code = f.read()

        opt = SimTruthTableOptimizer()
        res = opt.run(code)

        self.assertIn("trim_code[0]", res.mapped_cones)
        self.assertIn("trim_done", res.mapped_cones)
        self.assertIn("trim_reg[0]_d", res.mapped_cones)

    def test_v2_clock_divider(self):
        with open("examples/clock_divider_rst.v") as f:
            code = f.read()

        opt = SimTruthTableOptimizer()
        res = opt.run(code)

        self.assertIn("cnt_reg[0]_d", res.mapped_cones)
        self.assertIn("count[0]", res.mapped_cones)


if __name__ == "__main__":
    unittest.main()

