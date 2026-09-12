"""Integration tests for the complete AMS Digital Optimizer Pipeline."""

import os
import pytest
from ams_optimizer.core.pipeline import OptimizerPipeline

EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")

def test_pipeline_gray_counter():
    with open(os.path.join(EXAMPLES_DIR, "gray_counter.v")) as f:
        code = f.read()

    pipeline = OptimizerPipeline()
    result = pipeline.run(code)

    assert result.parsed_module.name == "gray_counter"
    assert len(result.register_expressions) == 3
    assert len(result.output_expressions) == 6
    assert result.verification is not None
    assert result.verification.is_equivalent is True
    assert "module gray_counter_va" in result.veriloga_code
    assert "NAND" in result.veriloga_code or "MUX2" in result.veriloga_code

def test_pipeline_sar_adc_ctrl():
    with open(os.path.join(EXAMPLES_DIR, "sar_adc_ctrl.v")) as f:
        code = f.read()

    pipeline = OptimizerPipeline()
    result = pipeline.run(code)

    assert result.parsed_module.name == "sar_adc_ctrl"
    assert len(result.register_expressions) == 8  # 3 state + 4 dac + 1 eoc
    assert result.verification is not None
    assert result.verification.is_equivalent is True

def test_pipeline_bandgap_trim_fsm():
    with open(os.path.join(EXAMPLES_DIR, "bandgap_trim_fsm.v")) as f:
        code = f.read()

    pipeline = OptimizerPipeline()
    result = pipeline.run(code)

    assert result.parsed_module.name == "bandgap_trim_fsm"
    assert len(result.register_expressions) == 4
    assert result.verification is not None
    assert result.verification.is_equivalent is True

def test_pipeline_clock_divider():
    with open(os.path.join(EXAMPLES_DIR, "clock_divider_rst.v")) as f:
        code = f.read()

    pipeline = OptimizerPipeline()
    result = pipeline.run(code)

    assert result.parsed_module.name == "clock_divider_rst"
    assert result.verification is not None
    assert result.verification.is_equivalent is True
