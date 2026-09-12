"""Tests for Verilog AST parser and state slicer."""

import pytest
from ams_optimizer.core.ast_parser import VerilogParser, VerilogExprParser
import sympy

def test_expr_parser_basic():
    parser = VerilogExprParser("a & b | ~c")
    expr = parser.parse()
    assert expr is not None
    expected = sympy.Or(sympy.And(sympy.Symbol("a"), sympy.Symbol("b")), sympy.Not(sympy.Symbol("c")))
    assert sympy.simplify_logic(sympy.Equivalent(expr, expected)) is sympy.true

def test_expr_parser_xor_ternary():
    parser = VerilogExprParser("ena ? (q[1] ^ q[0]) : q[1]")
    expr = parser.parse()
    assert expr is not None
    syms = {sympy.Symbol("ena"): True, sympy.Symbol("q_1_"): False, sympy.Symbol("q_0_"): True}
    assert bool(expr.subs(syms)) is True

def test_parse_gray_counter():
    code = """
    module gray_counter (
        input clk,
        input rst_n,
        input ena,
        output [2:0] count_bin,
        output [2:0] count_gray
    );
        reg [2:0] q;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                q <= 3'b000;
            end else if (ena) begin
                q <= q + 3'd1;
            end
        end
        assign count_bin = q;
        assign count_gray[2] = q[2];
        assign count_gray[1] = q[2] ^ q[1];
        assign count_gray[0] = q[1] ^ q[0];
    endmodule
    """
    p = VerilogParser(code).parse()
    assert p.name == "gray_counter"
    assert len(p.registers) == 3
    reg_names = [r.name for r in p.registers]
    assert "q[0]" in reg_names
    assert "q[1]" in reg_names
    assert "q[2]" in reg_names
    assert len(p.comb_assignments) == 6
