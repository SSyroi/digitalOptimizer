"""Tests for Boolean Synthesizer and Technology Mapper."""

import pytest
import sympy
from ams_optimizer.core.library import load_default_library
from ams_optimizer.core.synthesizer import LogicSynthesizer
from ams_optimizer.core.tree_collapser import TreeCollapser

def test_synthesizer_nand_mapping():
    lib = load_default_library()
    synth = LogicSynthesizer(lib)
    collapser = TreeCollapser()

    # NAND2 test
    cone = synth.synthesize_expression("out_nand", "~(a & b)")
    expr = collapser.collapse_cone(cone)
    assert "NAND2" in expr.nested_expr

def test_synthesizer_mux_mapping():
    lib = load_default_library()
    synth = LogicSynthesizer(lib)
    collapser = TreeCollapser()

    # MUX2 test: (s & d1) | (~s & d0)
    cone = synth.synthesize_expression("out_mux", "(s & d1) | (~s & d0)")
    expr = collapser.collapse_cone(cone)
    assert "MUX2" in expr.nested_expr
