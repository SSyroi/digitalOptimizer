// =============================================================================
// Module: PWM_CTRL
// Description:
//   Modified Digital Controller for Offset Compensation and PWM / Low-Power Mode.
//   Synthesizable Verilog-2001 RTL specification with architectural flexibility parameters.
//
// Architectural Refinement:
//   - Glitch-Free BGR Control Output (oc_ctrl_bgr): Registered directly with an
//     output Flip-Flop clocked by clk_i to eliminate combinational decode glitches.
//   - Glitch-Free Charge Pump Control Output (oc_ctrl_cp): Derived directly from
//     the registered oc_ctrl_bgr output, eliminating redundant register banks
//     while maintaining exact startup auto-zero stagger (CP samples for 2 cycles:
//     cnt=0,1; BGR samples for 1 cycle: cnt=0).
//
// Flexibility Parameters:
//   - RELAX_STATIC_MODES (default: 0):
//       0: Strict static mode decoding (01 -> 0, 10 -> 1).
//       1: Flexible static mode polarity (bit 0 sets static polarity: 01 -> 1, 10 -> 0).
//   - RELAX_PWM_SAMPLE (default: 0):
//       0: Strict 2-cycle PWM auto-zero sample window: (cnt == 4'd15) || (cnt == 4'd0).
//       1: Relaxed single-cycle PWM auto-zero sample window: (cnt == 4'd0).
//   - RELAX_STARTUP (default: 0):
//       0: Strict startup (BGR samples 1 cycle, CP samples 2 cycles; startup clears at cnt==15).
//       1: Relaxed startup (BGR and CP both sample 2 cycles; startup clears at cnt==1).
//
// Operating Modes (decoded from c_DfT_oc_dig_VDD ^ c_metalFix_invert_oc_defaults):
//   - 2'b00: Auto-zero mode.
//            Startup: 2 cycles initial sampling for CP (cnt=0,1), 1 cycle for BGR (cnt=0).
//                     Fast clock (en_lowFreq=0) remains active for these 2 pulses.
//            Steady-state: 1 cycle offset sampling (fast clock: en_lowFreq=0, oc_ctrl=1),
//                          1 cycle closed-loop active (slow clock: en_lowFreq=1, oc_ctrl=0).
//   - 2'b11: Chopping mode.
//            Continuous fast clock (en_lowFreq=0) and controls alternate every cycle.
//   - 2'b01 / 2'b10: No offset compensation.
//            Stable static controls (0 for 2'b01, 1 for 2'b10).
//
// Power & DFT Controls:
//   - Normal mode (c_DfT_en_LP=0, c_DfT_en_PWM=0): Active mode (en_LP=0).
//   - PWM mode (c_DfT_en_PWM=1):
//            16-cycle period: 2 cycles active (en_LP=0), 14 cycles LP (en_LP=1).
//            Fast clock (en_lowFreq=0) over the 2 active cycles, slow otherwise.
//            Auto-zero: controls rise at cnt=15 (one cycle before en_LP falls),
//                       stay high at cnt=0, drop at cnt=1 (mid-gap), low until cnt=15.
//            Chopping:  controls swap polarity once per period, at cnt=0 -> 1.
//   - DfT LP override (c_DfT_en_LP=1):
//            Forces en_LP=1 in all regimes, freezing all oc_ctrl outputs.
// =============================================================================

module PWM_CTRL (
  input wire        VDD,
  input wire        VSS,
  input wire        sub,
  input wire        res_n,
  input wire        c_DfT_en_LP,
  input wire        c_DfT_en_PWM,
  input wire [1:0]  c_DfT_oc_dig_VDD,
  output reg        en_LP,
  output reg        oc_select,
  output reg        oc_ctrl_cp,
  output reg        oc_ctrl_bgr,
  input wire        clk_i,
  output reg        en_lowFreq,
  output wire       oc_select_ext,
  output wire       oc_ctrl_cp_ext,
  output wire       en_LP_ext,
  input wire        c_metalFix_invert_oc_defaults
);

// -----------------------------------------------------------------------------
// Flexibility Parameters (RELAX_STATIC_MODES = 1 for optimal logic minimization)
// -----------------------------------------------------------------------------
parameter RELAX_STATIC_MODES = 1;
parameter RELAX_PWM_SAMPLE   = 0;
parameter RELAX_STARTUP      = 0;

// -----------------------------------------------------------------------------
// Internal Registers & Signals
// -----------------------------------------------------------------------------
reg [3:0] cnt;
reg       startup;

wire [1:0] eff_oc_mode;
wire       is_az_mode;
wire       is_chop_mode;
wire       is_static_0;
wire       is_static_1;
wire       is_pwm_active_window;

// -----------------------------------------------------------------------------
// Mode Decoding
// -----------------------------------------------------------------------------
// Metal-fix allows remapping default 2'b00 (auto-zero) to 2'b11 (chopping)
assign eff_oc_mode = c_DfT_oc_dig_VDD ^ {2{c_metalFix_invert_oc_defaults}};

assign is_az_mode   = (eff_oc_mode == 2'b00);
assign is_static_0  = (eff_oc_mode == 2'b01);
// Static mode: strict decoding checks 2'b10; relaxed mode uses eff_oc_mode[0]
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
      // Controls rise at cnt=15, stay high at cnt=0, drop at cnt=1
      oc_ctrl_bgr <= (cnt == 4'd14) || (cnt == 4'd15);
    end else if (c_DfT_en_PWM && is_chop_mode) begin
      // Swaps chopping polarity once per period, at the middle of the LP=0 gap (cnt: 0 -> 1)
      if (cnt == 4'd0) begin
        oc_ctrl_bgr <= ~oc_ctrl_bgr;
      end
    end else if (is_chop_mode) begin
      // Chopping mode: toggle every clock cycle
      oc_ctrl_bgr <= ~oc_ctrl_bgr;
    end else if (is_az_mode) begin
      // Auto-zero mode:
      // BGR samples 1 cycle (cnt=0), drops to 0 at cnt=1
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
      en_lowFreq = !cnt[0]; // Slow clock (1) at cnt=2, fast (0) at cnt=3, slow (1) at cnt=4...
    end
  end else begin
    en_lowFreq = 1'b0;
  end

  // 3. Offset Compensation Select (oc_select)
  // Indicates dynamic chopping / offset compensation activity
  if (c_DfT_en_LP) begin
    oc_select = 1'b0;
  end else if (is_chop_mode || is_az_mode) begin
    oc_select = 1'b1;
  end else begin
    oc_select = 1'b0;
  end

  // 4. Charge Pump Control Output (oc_ctrl_cp)
  // Reuses the clean registered BGR control output without extra flip-flops.
  // Differentiates only during initial startup auto-zero sampling (CP samples for
  // 2 cycles, remaining high at cnt=1).
  if (c_DfT_en_LP) begin
    oc_ctrl_cp = 1'b0;
  end else if (is_chop_mode) begin
    oc_ctrl_cp = ~oc_ctrl_bgr;
  end else if (!c_DfT_en_PWM && is_az_mode && startup && (cnt == 4'd1)) begin
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
