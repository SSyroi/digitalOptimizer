"""Comprehensive test modeled after PWM_CTRL.v with multi-bit vector comparisons, always @(*) multiplexing, and all primary outputs."""

import pytest
from ams_optimizer.core.pipeline import OptimizerPipeline
from ams_optimizer.core.library import load_default_library

def test_pwm_ctrl_full_structure():
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

    assert result.verification.is_equivalent
    va = result.veriloga_code

    # 1. Check counter bit expansion (no raw 'cnt' as leaf in expressions)
    assert "cnt_0_q" in va or "cnt_0_d" in va
    assert "cnt_1_d" in va
    assert "cnt_2_d" in va
    assert "cnt_3_d" in va

    # 2. Check that all primary outputs have contribution drivers
    assert "V(cnt[0]) <+ transition" in va
    assert "V(cnt[1]) <+ transition" in va
    assert "V(cnt[2]) <+ transition" in va
    assert "V(cnt[3]) <+ transition" in va
    assert "V(en_LP) <+ transition" in va
    assert "V(en_LowFreq) <+ transition" in va
    assert "V(oc_select) <+ transition" in va
    assert "V(oc_ctrl_bgr) <+ transition" in va
    assert "V(oc_ctrl_cp) <+ transition" in va
    assert "V(is_az_mode) <+ transition" in va
    assert "V(eff_oc_mode[0]) <+ transition" in va
    assert "V(eff_oc_mode[1]) <+ transition" in va
