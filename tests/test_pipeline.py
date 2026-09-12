"""Integration tests for the complete AMS Digital Optimizer Pipeline."""

import os
import unittest
from ams_optimizer.core.pipeline import OptimizerPipeline

EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")


class TestPipeline(unittest.TestCase):
    def test_pipeline_gray_counter(self):
        with open(os.path.join(EXAMPLES_DIR, "gray_counter.v")) as f:
            code = f.read()

        pipeline = OptimizerPipeline()
        result = pipeline.run(code)

        self.assertEqual(result.parsed_module.name, "gray_counter")
        self.assertEqual(len(result.register_expressions), 3)
        self.assertEqual(len(result.output_expressions), 6)
        self.assertIsNotNone(result.verification)
        self.assertTrue(result.verification.is_equivalent)
        self.assertIn("module gray_counter_va", result.veriloga_code)
        self.assertTrue("NAND" in result.veriloga_code or "MUX2" in result.veriloga_code)

    def test_pipeline_sar_adc_ctrl(self):
        with open(os.path.join(EXAMPLES_DIR, "sar_adc_ctrl.v")) as f:
            code = f.read()

        pipeline = OptimizerPipeline()
        result = pipeline.run(code)

        self.assertEqual(result.parsed_module.name, "sar_adc_ctrl")
        self.assertEqual(len(result.register_expressions), 8)  # 3 state + 4 dac + 1 eoc
        self.assertIsNotNone(result.verification)
        self.assertTrue(result.verification.is_equivalent)

    def test_pipeline_bandgap_trim_fsm(self):
        with open(os.path.join(EXAMPLES_DIR, "bandgap_trim_fsm.v")) as f:
            code = f.read()

        pipeline = OptimizerPipeline()
        result = pipeline.run(code)

        self.assertEqual(result.parsed_module.name, "bandgap_trim_fsm")
        self.assertEqual(len(result.register_expressions), 4)
        self.assertIsNotNone(result.verification)
        self.assertTrue(result.verification.is_equivalent)

    def test_pipeline_clock_divider(self):
        with open(os.path.join(EXAMPLES_DIR, "clock_divider_rst.v")) as f:
            code = f.read()

        pipeline = OptimizerPipeline()
        result = pipeline.run(code)

        self.assertEqual(result.parsed_module.name, "clock_divider_rst")
        self.assertIsNotNone(result.verification)
        self.assertTrue(result.verification.is_equivalent)


if __name__ == "__main__":
    unittest.main()

