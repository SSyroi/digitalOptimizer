import unittest
import os
import subprocess
import tempfile
from espresso_mv_optimizer.extractor import UnifiedRTLExtractor
from espresso_mv_optimizer.pipeline import UnifiedEspressoMVOptimizer
from espresso_mv_optimizer.veriloga_emitter import UnifiedVerilogAEmitter
from espresso_mv_optimizer.verilog_emitter import UnifiedVerilogNetlistEmitter

CELL_MODELS = """
module INV_X1 (input A, output Y); assign Y = ~A; endmodule
module NAND2_X1 (input A, input B, output Y); assign Y = ~(A & B); endmodule
module NAND3_X1 (input A, input B, input C, output Y); assign Y = ~(A & B & C); endmodule
module NAND4_X1 (input A, input B, input C, input D, output Y); assign Y = ~(A & B & C & D); endmodule
module MUX2_X1 (input S, input D0, input D1, output Y); assign Y = S ? D1 : D0; endmodule
module DFFR_X1 (input D, input CK, input RN, output reg Q, output QN);
  always @(posedge CK or negedge RN) begin
    if (!RN) Q <= 1'b0;
    else     Q <= D;
  end
  assign QN = ~Q;
endmodule
module DFFS_X1 (input D, input CK, input SN, output reg Q, output QN);
  always @(posedge CK or negedge SN) begin
    if (!SN) Q <= 1'b1;
    else     Q <= D;
  end
  assign QN = ~Q;
endmodule
"""

TB_CODE = """`timescale 1ns/1ps
module tb;
  reg VDD, VSS, sub, res_n, clk_i;
  reg c_DfT_en_LP, c_DfT_en_PWM, c_metalFix_invert_oc_defaults;
  reg [1:0] c_DfT_oc_dig_VDD;

  wire rtl_en_LP, rtl_oc_select, rtl_oc_ctrl_cp, rtl_oc_ctrl_bgr, rtl_en_lowFreq;
  wire net_en_LP, net_oc_select, net_oc_ctrl_cp, net_oc_ctrl_bgr, net_en_lowFreq;

  PWM_CTRL rtl_dut (
    .VDD(VDD), .VSS(VSS), .sub(sub), .res_n(res_n), .clk_i(clk_i),
    .c_DfT_en_LP(c_DfT_en_LP), .c_DfT_en_PWM(c_DfT_en_PWM),
    .c_DfT_oc_dig_VDD(c_DfT_oc_dig_VDD),
    .c_metalFix_invert_oc_defaults(c_metalFix_invert_oc_defaults),
    .en_LP(rtl_en_LP), .oc_select(rtl_oc_select), .oc_ctrl_cp(rtl_oc_ctrl_cp),
    .oc_ctrl_bgr(rtl_oc_ctrl_bgr), .en_lowFreq(rtl_en_lowFreq)
  );

  PWM_CTRL_netlist net_dut (
    .VDD(VDD), .VSS(VSS), .sub(sub), .res_n(res_n), .clk_i(clk_i),
    .c_DfT_en_LP(c_DfT_en_LP), .c_DfT_en_PWM(c_DfT_en_PWM),
    .c_DfT_oc_dig_VDD(c_DfT_oc_dig_VDD),
    .c_metalFix_invert_oc_defaults(c_metalFix_invert_oc_defaults),
    .en_LP(net_en_LP), .oc_select(net_oc_select), .oc_ctrl_cp(net_oc_ctrl_cp),
    .oc_ctrl_bgr(net_oc_ctrl_bgr), .en_lowFreq(net_en_lowFreq)
  );

  always #5 clk_i = ~clk_i;

  integer err_count = 0;
  task check_step;
    input [31:0] cycle;
    begin
      if (rtl_en_LP !== net_en_LP) begin
        $display("ERR at cycle %0d: en_LP mismatch! RTL=%b Net=%b", cycle, rtl_en_LP, net_en_LP);
        err_count = err_count + 1;
      end
      if (rtl_oc_select !== net_oc_select) begin
        $display("ERR at cycle %0d: oc_select mismatch! RTL=%b Net=%b", cycle, rtl_oc_select, net_oc_select);
        err_count = err_count + 1;
      end
      if (rtl_oc_ctrl_bgr !== net_oc_ctrl_bgr) begin
        $display("ERR at cycle %0d: bgr mismatch! RTL=%b Net=%b", cycle, rtl_oc_ctrl_bgr, net_oc_ctrl_bgr);
        err_count = err_count + 1;
      end
      if (rtl_oc_ctrl_cp !== net_oc_ctrl_cp) begin
        $display("ERR at cycle %0d: cp mismatch! RTL=%b Net=%b", cycle, rtl_oc_ctrl_cp, net_oc_ctrl_cp);
        err_count = err_count + 1;
      end
      if (rtl_en_lowFreq !== net_en_lowFreq) begin
        $display("ERR at cycle %0d: en_lowFreq mismatch! RTL=%b Net=%b", cycle, rtl_en_lowFreq, net_en_lowFreq);
        err_count = err_count + 1;
      end
    end
  endtask

  task check_reset;
    input [31:0] mode_idx;
    begin
      if (net_oc_select !== 1'b1) begin
        $display("ERR in mode %0d: net_oc_select is NOT 1 in reset! Net=%b", mode_idx, net_oc_select);
        err_count = err_count + 1;
      end
      if (rtl_oc_select !== net_oc_select) begin
        $display("ERR in mode %0d: oc_select reset mismatch! RTL=%b Net=%b", mode_idx, rtl_oc_select, net_oc_select);
        err_count = err_count + 1;
      end
    end
  endtask

  integer cyc;
  initial begin
    clk_i = 0; res_n = 0;
    VDD = 1; VSS = 0; sub = 0;
    c_DfT_en_LP = 0; c_DfT_en_PWM = 1;
    c_DfT_oc_dig_VDD = 2'b11; c_metalFix_invert_oc_defaults = 0;
    #6; check_reset(1);
    #6; res_n = 1;

    // Mode 1: PWM=1, Chop
    for (cyc = 0; cyc < 48; cyc = cyc + 1) begin
      @(posedge clk_i); #1; check_step(cyc);
    end

    // Mode 2: PWM=1, AZ
    c_DfT_oc_dig_VDD = 2'b00;
    res_n = 0; #6; check_reset(2); #6; res_n = 1;
    for (cyc = 0; cyc < 48; cyc = cyc + 1) begin
      @(posedge clk_i); #1; check_step(cyc);
    end

    // Mode 3: PWM=0, Chop
    c_DfT_en_PWM = 0; c_DfT_oc_dig_VDD = 2'b11;
    res_n = 0; #6; check_reset(3); #6; res_n = 1;
    for (cyc = 0; cyc < 48; cyc = cyc + 1) begin
      @(posedge clk_i); #1; check_step(cyc);
    end

    // Mode 4: PWM=0, AZ (steady-state)
    c_DfT_oc_dig_VDD = 2'b00;
    res_n = 0; #6; check_reset(4); #6; res_n = 1;
    repeat (16) @(posedge clk_i);
    #1;
    for (cyc = 16; cyc < 48; cyc = cyc + 1) begin
      @(posedge clk_i); #1; check_step(cyc);
    end

    // Mode 5: DfT LP override
    c_DfT_en_LP = 1;
    for (cyc = 0; cyc < 16; cyc = cyc + 1) begin
      @(posedge clk_i); #1; check_step(cyc);
    end

    if (err_count != 0) begin
      $display("FAIL: %0d errors", err_count);
      $fatal(1);
    end
    $finish;
  end
endmodule
"""


class TestPWMRegisteredLP(unittest.TestCase):
    def setUp(self):
        self.verilog_path = os.path.abspath("examples/PWM_CTRL.v")

    def test_registered_en_lp_extraction(self):
        ext = UnifiedRTLExtractor(self.verilog_path)
        self.assertIn("en_LP", ext.register_bits)
        self.assertIn("en_LP_d", ext.d_targets)
        self.assertNotIn("en_LP", ext.comb_outputs)

    def test_optimization_and_formal_lec(self):
        opt = UnifiedEspressoMVOptimizer()
        metrics = opt.optimize(self.verilog_path, dc_relaxation="startup_relaxed")
        self.assertTrue(metrics["lec_passed"])
        self.assertIn("en_LP_d", metrics["min_exprs"])

    def test_iverilog_netlist_cycle_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tb_file = os.path.join(tmpdir, "tb.v")
            vvp_file = os.path.join(tmpdir, "tb.vvp")
            with open(tb_file, "w") as f:
                f.write(CELL_MODELS + "\n" + TB_CODE)

            netlist_path = os.path.abspath("examples/PWM_CTRL_netlist.v")
            cmd = ["iverilog", "-o", vvp_file, self.verilog_path, netlist_path, tb_file]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            sim = subprocess.run(["vvp", vvp_file], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertNotIn("ERR at cycle", sim.stdout)


if __name__ == "__main__":
    unittest.main()
