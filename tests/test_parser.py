"""Tests for Verilog AST parser and state slicer."""

import unittest
import sympy
from ams_optimizer.core.ast_parser import VerilogParser, VerilogExprParser


class TestParser(unittest.TestCase):
    def test_expr_parser_basic(self):
        parser = VerilogExprParser("a & b | ~c")
        expr = parser.parse()
        self.assertIsNotNone(expr)
        expected = sympy.Or(sympy.And(sympy.Symbol("a"), sympy.Symbol("b")), sympy.Not(sympy.Symbol("c")))
        self.assertEqual(sympy.simplify_logic(sympy.Equivalent(expr, expected)), sympy.true)


    def test_expr_parser_xor_ternary(self):
        parser = VerilogExprParser("ena ? (q[1] ^ q[0]) : q[1]")
        expr = parser.parse()
        self.assertIsNotNone(expr)
        syms = {sympy.Symbol("ena"): True, sympy.Symbol("q_1_"): False, sympy.Symbol("q_0_"): True}
        self.assertTrue(bool(expr.subs(syms)))

    def test_parse_gray_counter(self):
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
        self.assertEqual(p.name, "gray_counter")
        self.assertEqual(len(p.registers), 3)
        reg_names = [r.name for r in p.registers]
        self.assertIn("q[0]", reg_names)
        self.assertIn("q[1]", reg_names)
        self.assertIn("q[2]", reg_names)
        self.assertEqual(len(p.comb_assignments), 6)


if __name__ == "__main__":
    unittest.main()

