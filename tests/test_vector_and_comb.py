"""Tests for vector condition expansion, always @* parsing, and complete Verilog-A output coverage."""

import unittest
from ams_optimizer.core.pipeline import OptimizerPipeline
from ams_optimizer.core.library import load_default_library


class TestVectorAndComb(unittest.TestCase):
    def test_counter_with_vector_comparison(self):
        verilog = """
        module counter_fsm (clk, rst_n, ena, cnt, match_out, status_flag);
          input clk, rst_n, ena;
          output [2:0] cnt;
          output match_out;
          output status_flag;

          reg [2:0] cnt;
          reg match_out;

          always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
              cnt <= 3'd0;
              match_out <= 1'b0;
            end else if (ena) begin
              cnt <= cnt + 1;
              if (cnt == 3'd4) begin
                match_out <= 1'b1;
              end else begin
                match_out <= 1'b0;
              end
            end
          end

          assign status_flag = match_out;

        endmodule
        """
        library = load_default_library()
        pipeline = OptimizerPipeline(library)
        result = pipeline.run(verilog)

        self.assertTrue(result.verification.is_equivalent)
        va = result.veriloga_code

        # Check that raw undeclared identifier 'cnt' alone is NOT in the Verilog-A body
        # Only cnt[0], cnt[1], cnt[2], cnt_0_q, cnt_1_q, cnt_2_q should exist
        self.assertIn("real cnt_0_q;", va)
        self.assertIn("real cnt_1_q;", va)
        self.assertIn("real cnt_2_q;", va)

        # Check all outputs are generated
        self.assertIn("V(cnt[0]) <+ transition", va)
        self.assertIn("V(cnt[1]) <+ transition", va)
        self.assertIn("V(cnt[2]) <+ transition", va)
        self.assertIn("V(match_out) <+ transition", va)
        self.assertIn("V(status_flag) <+ transition", va)

    def test_always_comb_procedural_block(self):
        verilog = """
        module alu_comb (a, b, sel, out, overflow);
          input [1:0] a, b;
          input sel;
          output [1:0] out;
          output overflow;

          reg [1:0] out;
          reg overflow;

          always @* begin
            if (sel) begin
              out = a & b;
              overflow = 1'b0;
            end else begin
              out = a | b;
              overflow = 1'b1;
            end
          end

        endmodule
        """
        library = load_default_library()
        pipeline = OptimizerPipeline(library)
        result = pipeline.run(verilog)

        self.assertTrue(result.verification.is_equivalent)
        va = result.veriloga_code

        # Check all outputs are present
        self.assertIn("V(out[0]) <+ transition", va)
        self.assertIn("V(out[1]) <+ transition", va)
        self.assertIn("V(overflow) <+ transition", va)


if __name__ == "__main__":
    unittest.main()

