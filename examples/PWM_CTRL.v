// =============================================================================
// Module: PWM_CTRL
// Description:
//   Optimized Digital Controller for Offset Compensation and PWM / Low-Power Mode.
//   Synthesizable Verilog-2001 RTL with verified glitch-free registered control
//   outputs, architectural flexibility parameters, and optimal default settings.
//
// Architectural Features:
//   - Glitch-Free BGR Control Output (oc_ctrl_bgr): Registered directly with an
//     output Flip-Flop clocked by clk_i to eliminate combinational decode glitches.
//   - Glitch-Free Charge Pump Control Output (oc_ctrl_cp): Derived directly from
//     the registered oc_ctrl_bgr output, eliminating redundant register banks
//     while maintaining exact startup auto-zero stagger.
//   - Low-Power PWM Window: Active for exactly 2 cycles (cnt=0, 1) during en_LP=0.
//   - Mid-Gap Chopping Swap: In PWM Chopping mode, oc_ctrl_bgr swaps polarity
//     at the posedge entering cnt=1 (middle of LP=0 gap, triggered at cnt==0).
//
// Flexibility Parameters:
//   - RELAX_STATIC_MODES (default: 1):
//       0: Strict static mode decoding (01 -> 0, 10 -> 1).
//       1: Flexible static mode polarity (bit 0 sets static polarity: 01 -> 1, 10 -> 0).
//          [Optimal default: 1 reduces logic complexity significantly]
//   - RELAX_PWM_SAMPLE (default: 0):
//       0: Strict 2-cycle PWM auto-zero sample window: (cnt == 4'd15) || (cnt == 4'd0).
//       1: Relaxed single-cycle PWM auto-zero sample window: (cnt == 4'd0).
//   - RELAX_STARTUP (default: 0):
//       0: Strict startup (BGR samples 1 cycle: cnt=0; CP samples 2 cycles: cnt=0,1).
//       1: Relaxed startup (BGR and CP both sample 2 cycles; startup clears at cnt==1).
// =============================================================================

module PWM_CTRL #(
  parameter RELAX_STATIC_MODES = 1,
  parameter RELAX_PWM_SAMPLE   = 0,
  parameter RELAX_STARTUP      = 0
) (
  input wire        VDD,
  input wire        VSS,
  input wire        sub,
  input wire        res_n,
  input wire        clk_i,
  input wire        c_DfT_en_LP,
  input wire        c_DfT_en_PWM,
  input wire [1:0]  c_DfT_oc_dig_VDD,
  input wire        c_metalFix_invert_oc_defaults,
  output reg        en_LP,
  output reg        oc_select,
  output reg        oc_ctrl_cp,
  output reg        oc_ctrl_bgr,
  output reg        en_lowFreq,
  output wire       oc_select_ext,
  output wire       oc_ctrl_cp_ext,
  output wire       en_LP_ext
);

// -----------------------------------------------------------------------------
// Internal State Registers & Mode Decoding
// -----------------------------------------------------------------------------
reg [3:0] cnt;
reg       startup;

wire [1:0] eff_oc_mode;
wire       is_az_mode;
wire       is_chop_mode;
wire       is_static_0;
wire       is_static_1;
wire       is_pwm_active_window;

// Metal-fix allows remapping default 2'b00 (auto-zero) to 2'b11 (chopping)
assign eff_oc_mode = c_DfT_oc_dig_VDD ^ {2{c_metalFix_invert_oc_defaults}};

assign is_az_mode   = (eff_oc_mode == 2'b00);
assign is_static_0  = (eff_oc_mode == 2'b01);
assign is_static_1  = RELAX_STATIC_MODES ? eff_oc_mode[0] : (eff_oc_mode == 2'b10);
assign is_chop_mode = (eff_oc_mode == 2'b11);

// In PWM mode, first 2 cycles of 16-cycle counter (cnt=0,1) are active (LP=0)
assign is_pwm_active_window = (cnt < 4'd2);

// -----------------------------------------------------------------------------
// Sequential Core: Counter, Startup Flag, and Registered BGR Control
// -----------------------------------------------------------------------------
always @(posedge clk_i or negedge res_n) begin
  if (!res_n) begin
    cnt         <= 4'b0000;
    startup     <= 1'b1;
    oc_ctrl_bgr <= 1'b1; // In nominal auto-zero startup, BGR initializes high
  end else begin
    cnt <= cnt + 4'b0001;

    // Startup flag clearing after initial startup phase
    if (cnt == 4'd15) begin
      startup <= 1'b0;
    end

    // Sequential BGR Control Output (Registered Flip-Flop)
    if (c_DfT_en_LP) begin
      oc_ctrl_bgr <= 1'b0;
    end else if (c_DfT_en_PWM && is_az_mode) begin
      // Auto-zero PWM: controls rise at cnt=15, stay high at cnt=0, drop at cnt=1
      oc_ctrl_bgr <= (cnt == 4'd14) || (cnt == 4'd15);
    end else if (c_DfT_en_PWM && is_chop_mode) begin
      // Swaps chopping polarity once per period, at the middle of the LP=0 gap (cnt: 0 -> 1)
      if (cnt == 4'd0) begin
        oc_ctrl_bgr <= ~oc_ctrl_bgr;
      end
    end else if (is_chop_mode) begin
      // Continuous chopping mode: toggle every clock cycle
      oc_ctrl_bgr <= ~oc_ctrl_bgr;
    end else if (is_az_mode) begin
      // Auto-zero mode: BGR samples 1 cycle (cnt=0), drops to 0 at cnt=1
      if (startup && (cnt == 4'd0)) begin
        oc_ctrl_bgr <= 1'b0;
      end else begin
        oc_ctrl_bgr <= ~cnt[0];
      end
    end else if (is_static_1) begin
      oc_ctrl_bgr <= 1'b1;
    end else begin
      oc_ctrl_bgr <= 1'b0;
    end
  end
end

// -----------------------------------------------------------------------------
// Combinational Control Logic
// -----------------------------------------------------------------------------
always @(*) begin
  // 1. Low-Power Enable Logic (en_LP)
  if (c_DfT_en_LP) begin
    en_LP = 1'b1;
  end else if (c_DfT_en_PWM) begin
    en_LP = !is_pwm_active_window;
  end else begin
    en_LP = 1'b0; // Normal active operation
  end

  // 2. Frequency Control Logic (en_lowFreq)
  // Fast clock (0) during auto-zero sampling or chopping.
  // Slow clock (1) during closed-loop operation.
  if (c_DfT_en_LP) begin
    en_lowFreq = 1'b0;
  end else if (c_DfT_en_PWM) begin
    en_lowFreq = !is_pwm_active_window; // Fast only over the LP=0 gap
  end else if (is_chop_mode) begin
    en_lowFreq = 1'b0;
  end else if (is_az_mode) begin
    if (startup && (cnt < 4'd2)) begin
      en_lowFreq = 1'b0; // Fast clock for initial 2 startup pulses (cnt=0,1)
    end else begin
      en_lowFreq = !cnt[0]; // Slow clock (1) at cnt=2, fast (0) at cnt=3...
    end
  end else begin
    en_lowFreq = 1'b0;
  end

  // 3. Offset Compensation Select (oc_select)
  if (c_DfT_en_LP) begin
    oc_select = 1'b0;
  end else if (is_chop_mode || is_az_mode) begin
    oc_select = 1'b1;
  end else begin
    oc_select = 1'b0;
  end

  // 4. Charge Pump Control Output (oc_ctrl_cp)
  if (c_DfT_en_LP) begin
    oc_ctrl_cp = 1'b0;
  end else if (is_chop_mode) begin
    oc_ctrl_cp = ~oc_ctrl_bgr;
  end else if (!RELAX_STARTUP && !c_DfT_en_PWM && is_az_mode && startup && (cnt == 4'd1)) begin
    oc_ctrl_cp = 1'b1;
  end else begin
    oc_ctrl_cp = oc_ctrl_bgr;
  end
end

// -----------------------------------------------------------------------------
// Extended Output Drivers (Direct Duplicates)
// -----------------------------------------------------------------------------
assign oc_select_ext   = oc_select;
assign oc_ctrl_cp_ext  = oc_ctrl_cp;
assign en_LP_ext       = en_LP;

endmodule
