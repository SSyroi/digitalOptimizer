"""Tests for AMS cell library manager."""

import pytest
from ams_optimizer.core.library import load_default_library, Library, Cell

def test_load_default_library():
    lib = load_default_library()
    assert lib.name == "default_ams"
    assert "NAND2" in lib.cells
    assert "NOR3" in lib.cells
    assert "MUX2" in lib.cells
    assert "DFFR" in lib.cells

def test_cell_evaluation():
    lib = load_default_library()
    nand2 = lib.get_cell("NAND2")
    assert nand2.evaluate({"A": True, "B": True}) is False
    assert nand2.evaluate({"A": True, "B": False}) is True

    mux2 = lib.get_cell("MUX2")
    assert mux2.evaluate({"S": False, "D0": True, "D1": False}) is True
    assert mux2.evaluate({"S": True, "D0": True, "D1": False}) is False
