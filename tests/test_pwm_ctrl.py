"""Comprehensive test modeled after PWM_CTRL.v with multi-bit vector comparisons, always @(*) multiplexing, and all primary outputs."""

import unittest
from ams_optimizer.core.pipeline import OptimizerPipeline
from ams_optimizer.core.library import load_default_library


class TestPwmCtrl(unittest.TestCase):
    def test_pwm_ctrl_full_structure(self):
        verilog = """
        module PWM_CTRL (
          input clk,
          input rst_n,
          input en_LP_ext,
          input oc_select_ext,
          input oc_ctrl_cp_ext,
          input [1:0] c_DfT_oc_dig_VDD,
          output [3:0] cnt,
          output en_LP,
          output en_LowFreq,
          output oc_select,
          output oc_ctrl_bgr,
          output oc_ctrl_cp,
          output is_az_mode,
          output [1:0] eff_oc_mode
        );

          reg [3:0] cnt;
          reg [1:0] eff_oc_mode;
          reg is_az_mode;
          reg en_LP;
          reg en_LowFreq;
          reg oc_select;
          reg oc_ctrl_bgr;
          reg oc_ctrl_cp;

          // Sequential block with counter increment
          always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
              cnt <= 4'b0000;
            end else begin
              cnt <= cnt + 4'b0001;
            end
          end

          // Combinational always @(*) block
          always @(*) begin
            eff_oc_mode = c_DfT_oc_dig_VDD;
            is_az_mode = (eff_oc_mode == 2'b00);

            if (is_az_mode) begin
              en_LP = 1'b1;
              en_LowFreq = 1'b0;
              oc_select = 1'b1;
              oc_ctrl_bgr = 1'b0;
              oc_ctrl_cp = 1'b1;
            end else begin
              en_LP = en_LP_ext;
              en_LowFreq = 1'b1;
              oc_select = oc_select_ext;
              oc_ctrl_bgr = 1'b1;
              oc_ctrl_cp = oc_ctrl_cp_ext;
            end
          end

        endmodule
        """
        library = load_default_library()
        pipeline = OptimizerPipeline(library)
        result = pipeline.run(verilog)

        self.assertTrue(result.verification.is_equivalent)
        va = result.veriloga_code

        # 1. Check counter bit expansion (no raw 'cnt' as leaf in expressions)
        self.assertTrue("cnt_0_q" in va or "cnt_0_d" in va)
        self.assertIn("cnt_1_d", va)
        self.assertIn("cnt_2_d", va)
        self.assertIn("cnt_3_d", va)

        # 2. Check that all primary outputs have contribution drivers
        self.assertIn("V(cnt[0]) <+ transition", va)
        self.assertIn("V(cnt[1]) <+ transition", va)
        self.assertIn("V(cnt[2]) <+ transition", va)
        self.assertIn("V(cnt[3]) <+ transition", va)
        self.assertIn("V(en_LP) <+ transition", va)
        self.assertIn("V(en_LowFreq) <+ transition", va)
        self.assertIn("V(oc_select) <+ transition", va)
        self.assertIn("V(oc_ctrl_bgr) <+ transition", va)
        self.assertIn("V(oc_ctrl_cp) <+ transition", va)
        self.assertIn("V(is_az_mode) <+ transition", va)
        self.assertIn("V(eff_oc_mode[0]) <+ transition", va)
        self.assertIn("V(eff_oc_mode[1]) <+ transition", va)


if __name__ == "__main__":
    unittest.main()

