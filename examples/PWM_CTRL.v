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
  reg is_chop_mode;
  reg is_pwm_active_window;
  reg is_pwm_sample_window;
  reg en_LP;
  reg en_LowFreq;
  reg oc_select;
  reg oc_ctrl_bgr;
  reg oc_ctrl_cp;

  // Sequential counter block
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      cnt <= 4'b0000;
    end else begin
      cnt <= cnt + 4'b0001;
    end
  end

  // Multi-level intermediate conditions and combinational decode
  always @(*) begin
    eff_oc_mode = c_DfT_oc_dig_VDD;
    is_az_mode = (eff_oc_mode == 2'b00);
    is_chop_mode = (eff_oc_mode == 2'b01);
    is_pwm_active_window = (cnt >= 4'd2 && cnt <= 4'd12);
    is_pwm_sample_window = (cnt >= 4'd13 && cnt <= 4'd15);

    if (is_az_mode) begin
      en_LP = 1'b1;
      en_LowFreq = 1'b0;
      oc_select = 1'b1;
      oc_ctrl_bgr = 1'b0;
      oc_ctrl_cp = 1'b1;
    end else if (is_chop_mode) begin
      en_LP = is_pwm_active_window;
      en_LowFreq = is_pwm_sample_window;
      oc_select = is_pwm_active_window;
      oc_ctrl_bgr = is_pwm_sample_window;
      oc_ctrl_cp = is_pwm_active_window;
    end else begin
      en_LP = en_LP_ext;
      en_LowFreq = 1'b1;
      oc_select = oc_select_ext;
      oc_ctrl_bgr = 1'b1;
      oc_ctrl_cp = oc_ctrl_cp_ext;
    end
  end

endmodule
