// ============================================================================
// Module: PWM_CTRL_netlist
// Synthesized by Unified Espresso-MV Silicon Optimizer
// Gate-Level Synthesizable Structural Netlist with Shared Intermediate Nodes
// Total Standard Cells : 74 cells
// Inverter Equivalents  : 318.0 GE
// Transistor Count     : 636 transistors
// ============================================================================

module PWM_CTRL_netlist (VDD, VSS, sub, res_n, c_DfT_en_LP, c_DfT_en_PWM, c_DfT_oc_dig_VDD, en_LP, oc_select, oc_ctrl_cp, oc_ctrl_bgr, clk_i, en_lowFreq, oc_select_ext, oc_ctrl_cp_ext, en_LP_ext, c_metalFix_invert_oc_defaults);
  input wire VDD, VSS, sub, res_n, clk_i;
  input wire c_DfT_en_LP, c_DfT_en_PWM, c_metalFix_invert_oc_defaults;
  input wire [1:0] c_DfT_oc_dig_VDD;
  output wire en_LP, oc_select, oc_ctrl_cp, oc_ctrl_bgr, en_lowFreq;
  output wire oc_select_ext, oc_ctrl_cp_ext, en_LP_ext;

  // Internal State Registers & Next-State Nets
  wire cnt_3_q, cnt_3_d;
  wire cnt_2_q, cnt_2_d;
  wire cnt_1_q, cnt_1_d;
  wire cnt_0_q, cnt_0_d;
  wire startup_q, startup_d;
  wire en_LP_q, en_LP_d;
  wire oc_ctrl_bgr_q, oc_ctrl_bgr_d;

  // Inverted Polarity Pool Wires
  wire w_inv_c_DfT_en_LP, w_inv_c_DfT_en_PWM, w_inv_c_DfT_oc_dig_VDD_1, w_inv_c_DfT_oc_dig_VDD_0, w_inv_c_metalFix_invert_oc_defaults, w_inv_cnt_3_q, w_inv_cnt_2_q, w_inv_cnt_1_q, w_inv_cnt_0_q, w_inv_startup_q, w_inv_en_LP_q, w_inv_oc_ctrl_bgr_q;

  // Shared Intermediate Product Term Wires (53 unique shared cubes)
  wire w_c0, w_c1, w_c2, w_c3, w_c4, w_c5, w_c6, w_c7, w_c8, w_c9, w_c10, w_c11, w_c12, w_c13, w_c14, w_c15, w_c16, w_c17, w_c18, w_c19, w_c20, w_c21, w_c22, w_c23, w_c24, w_c25, w_c26, w_c27, w_c28, w_c29, w_c30, w_c31, w_c32, w_c33, w_c34, w_c35, w_c36, w_c37, w_c38, w_c39, w_c40, w_c41, w_c42, w_c43, w_c44, w_c45, w_c46, w_c47, w_c48, w_c49, w_c50, w_c51, w_c52;

  // 1. Global Input & Register Inverters
  INV_X1  U_inv_c_DfT_en_LP                  (.A(c_DfT_en_LP), .Y(w_inv_c_DfT_en_LP));
  INV_X1  U_inv_c_DfT_en_PWM                 (.A(c_DfT_en_PWM), .Y(w_inv_c_DfT_en_PWM));
  INV_X1  U_inv_c_DfT_oc_dig_VDD_1           (.A(c_DfT_oc_dig_VDD[1]), .Y(w_inv_c_DfT_oc_dig_VDD_1));
  INV_X1  U_inv_c_DfT_oc_dig_VDD_0           (.A(c_DfT_oc_dig_VDD[0]), .Y(w_inv_c_DfT_oc_dig_VDD_0));
  INV_X1  U_inv_c_metalFix_invert_oc_defaults (.A(c_metalFix_invert_oc_defaults), .Y(w_inv_c_metalFix_invert_oc_defaults));
  INV_X1  U_inv_cnt_3_q                      (.A(cnt_3_q), .Y(w_inv_cnt_3_q));
  INV_X1  U_inv_cnt_2_q                      (.A(cnt_2_q), .Y(w_inv_cnt_2_q));
  INV_X1  U_inv_cnt_1_q                      (.A(cnt_1_q), .Y(w_inv_cnt_1_q));
  INV_X1  U_inv_cnt_0_q                      (.A(cnt_0_q), .Y(w_inv_cnt_0_q));
  INV_X1  U_inv_startup_q                    (.A(startup_q), .Y(w_inv_startup_q));
  INV_X1  U_inv_en_LP_q                      (.A(en_LP_q), .Y(w_inv_en_LP_q));
  INV_X1  U_inv_oc_ctrl_bgr_q                (.A(oc_ctrl_bgr_q), .Y(w_inv_oc_ctrl_bgr_q));

  // 2. Shared Intermediate Product Term Gates (53 unique NAND cells)
  // Output: oc_select
  NAND3_X1 U_c0 (.A(w_inv_c_DfT_en_LP), .B(w_inv_c_DfT_oc_dig_VDD_1), .C(w_inv_c_DfT_oc_dig_VDD_0), .Y(w_c0));
  // Output: oc_select
  NAND3_X1 U_c1 (.A(w_inv_c_DfT_en_LP), .B(c_DfT_oc_dig_VDD[1]), .C(c_DfT_oc_dig_VDD[0]), .Y(w_c1));
  // Output: oc_ctrl_cp
  wire w_c2_n0, w_c2_i0;
  NAND4_X1 U_c2_n0 (.A(w_inv_c_DfT_en_LP), .B(w_inv_c_DfT_en_PWM), .C(w_inv_c_DfT_oc_dig_VDD_1), .D(w_inv_c_DfT_oc_dig_VDD_0), .Y(w_c2_n0));
  INV_X1 U_c2_inv0 (.A(w_c2_n0), .Y(w_c2_i0));
  wire w_c2_n1, w_c2_i1;
  NAND4_X1 U_c2_n1 (.A(w_inv_c_metalFix_invert_oc_defaults), .B(w_inv_cnt_3_q), .C(w_inv_cnt_2_q), .D(w_inv_cnt_1_q), .Y(w_c2_n1));
  INV_X1 U_c2_inv1 (.A(w_c2_n1), .Y(w_c2_i1));
  wire w_c2_n2, w_c2_i2;
  NAND2_X1 U_c2_n2 (.A(cnt_0_q), .B(startup_q), .Y(w_c2_n2));
  INV_X1 U_c2_inv2 (.A(w_c2_n2), .Y(w_c2_i2));
  NAND3_X1 U_c2_root (.A(w_c2_i0), .B(w_c2_i1), .C(w_c2_i2), .Y(w_c2));
  // Output: oc_ctrl_cp
  wire w_c3_n0, w_c3_i0;
  NAND4_X1 U_c3_n0 (.A(w_inv_c_DfT_en_LP), .B(w_inv_c_DfT_oc_dig_VDD_1), .C(w_inv_c_DfT_oc_dig_VDD_0), .D(c_metalFix_invert_oc_defaults), .Y(w_c3_n0));
  INV_X1 U_c3_inv0 (.A(w_c3_n0), .Y(w_c3_i0));
  wire w_c3_n1, w_c3_i1;
  INV_X1 U_c3_n1 (.A(w_inv_oc_ctrl_bgr_q), .Y(w_c3_n1));
  INV_X1 U_c3_inv1 (.A(w_c3_n1), .Y(w_c3_i1));
  NAND2_X1 U_c3_root (.A(w_c3_i0), .B(w_c3_i1), .Y(w_c3));
  // Output: oc_ctrl_cp
  NAND4_X1 U_c4 (.A(w_inv_c_DfT_en_LP), .B(c_DfT_oc_dig_VDD[1]), .C(c_metalFix_invert_oc_defaults), .D(oc_ctrl_bgr_q), .Y(w_c4));
  // Output: oc_ctrl_cp
  wire w_c5_n0, w_c5_i0;
  NAND4_X1 U_c5_n0 (.A(w_inv_c_DfT_en_LP), .B(c_DfT_oc_dig_VDD[1]), .C(c_DfT_oc_dig_VDD[0]), .D(w_inv_c_metalFix_invert_oc_defaults), .Y(w_c5_n0));
  INV_X1 U_c5_inv0 (.A(w_c5_n0), .Y(w_c5_i0));
  wire w_c5_n1, w_c5_i1;
  INV_X1 U_c5_n1 (.A(w_inv_oc_ctrl_bgr_q), .Y(w_c5_n1));
  INV_X1 U_c5_inv1 (.A(w_c5_n1), .Y(w_c5_i1));
  NAND2_X1 U_c5_root (.A(w_c5_i0), .B(w_c5_i1), .Y(w_c5));
  // Output: oc_ctrl_cp
  NAND4_X1 U_c6 (.A(w_inv_c_DfT_en_LP), .B(w_inv_c_DfT_oc_dig_VDD_0), .C(w_inv_c_metalFix_invert_oc_defaults), .D(oc_ctrl_bgr_q), .Y(w_c6));
  // Output: oc_ctrl_cp
  NAND4_X1 U_c7 (.A(w_inv_c_DfT_en_LP), .B(w_inv_c_DfT_oc_dig_VDD_1), .C(c_DfT_oc_dig_VDD[0]), .D(oc_ctrl_bgr_q), .Y(w_c7));
  // Output: oc_ctrl_cp
  wire w_c8_n0, w_c8_i0;
  NAND4_X1 U_c8_n0 (.A(w_inv_c_DfT_en_LP), .B(w_inv_c_DfT_en_PWM), .C(c_DfT_oc_dig_VDD[1]), .D(c_DfT_oc_dig_VDD[0]), .Y(w_c8_n0));
  INV_X1 U_c8_inv0 (.A(w_c8_n0), .Y(w_c8_i0));
  wire w_c8_n1, w_c8_i1;
  NAND4_X1 U_c8_n1 (.A(c_metalFix_invert_oc_defaults), .B(w_inv_cnt_3_q), .C(w_inv_cnt_2_q), .D(w_inv_cnt_1_q), .Y(w_c8_n1));
  INV_X1 U_c8_inv1 (.A(w_c8_n1), .Y(w_c8_i1));
  wire w_c8_n2, w_c8_i2;
  NAND2_X1 U_c8_n2 (.A(cnt_0_q), .B(startup_q), .Y(w_c8_n2));
  INV_X1 U_c8_inv2 (.A(w_c8_n2), .Y(w_c8_i2));
  NAND3_X1 U_c8_root (.A(w_c8_i0), .B(w_c8_i1), .C(w_c8_i2), .Y(w_c8));
  // Shared: en_lowFreq, oc_ctrl_bgr_d
  wire w_c9_n0, w_c9_i0;
  NAND4_X1 U_c9_n0 (.A(w_inv_c_DfT_en_LP), .B(w_inv_c_DfT_en_PWM), .C(c_DfT_oc_dig_VDD[1]), .D(c_DfT_oc_dig_VDD[0]), .Y(w_c9_n0));
  INV_X1 U_c9_inv0 (.A(w_c9_n0), .Y(w_c9_i0));
  wire w_c9_n1, w_c9_i1;
  NAND3_X1 U_c9_n1 (.A(c_metalFix_invert_oc_defaults), .B(cnt_1_q), .C(w_inv_cnt_0_q), .Y(w_c9_n1));
  INV_X1 U_c9_inv1 (.A(w_c9_n1), .Y(w_c9_i1));
  NAND2_X1 U_c9_root (.A(w_c9_i0), .B(w_c9_i1), .Y(w_c9));
  // Shared: en_lowFreq, oc_ctrl_bgr_d
  wire w_c10_n0, w_c10_i0;
  NAND4_X1 U_c10_n0 (.A(w_inv_c_DfT_en_LP), .B(w_inv_c_DfT_en_PWM), .C(c_DfT_oc_dig_VDD[1]), .D(c_DfT_oc_dig_VDD[0]), .Y(w_c10_n0));
  INV_X1 U_c10_inv0 (.A(w_c10_n0), .Y(w_c10_i0));
  wire w_c10_n1, w_c10_i1;
  NAND3_X1 U_c10_n1 (.A(c_metalFix_invert_oc_defaults), .B(w_inv_cnt_0_q), .C(w_inv_startup_q), .Y(w_c10_n1));
  INV_X1 U_c10_inv1 (.A(w_c10_n1), .Y(w_c10_i1));
  NAND2_X1 U_c10_root (.A(w_c10_i0), .B(w_c10_i1), .Y(w_c10));
  // Shared: en_lowFreq, oc_ctrl_bgr_d
  wire w_c11_n0, w_c11_i0;
  NAND4_X1 U_c11_n0 (.A(w_inv_c_DfT_en_LP), .B(w_inv_c_DfT_en_PWM), .C(c_DfT_oc_dig_VDD[1]), .D(c_DfT_oc_dig_VDD[0]), .Y(w_c11_n0));
  INV_X1 U_c11_inv0 (.A(w_c11_n0), .Y(w_c11_i0));
  wire w_c11_n1, w_c11_i1;
  NAND3_X1 U_c11_n1 (.A(c_metalFix_invert_oc_defaults), .B(cnt_2_q), .C(w_inv_cnt_0_q), .Y(w_c11_n1));
  INV_X1 U_c11_inv1 (.A(w_c11_n1), .Y(w_c11_i1));
  NAND2_X1 U_c11_root (.A(w_c11_i0), .B(w_c11_i1), .Y(w_c11));
  // Shared: en_lowFreq, oc_ctrl_bgr_d
  wire w_c12_n0, w_c12_i0;
  NAND4_X1 U_c12_n0 (.A(w_inv_c_DfT_en_LP), .B(w_inv_c_DfT_en_PWM), .C(w_inv_c_DfT_oc_dig_VDD_1), .D(w_inv_c_DfT_oc_dig_VDD_0), .Y(w_c12_n0));
  INV_X1 U_c12_inv0 (.A(w_c12_n0), .Y(w_c12_i0));
  wire w_c12_n1, w_c12_i1;
  NAND3_X1 U_c12_n1 (.A(w_inv_c_metalFix_invert_oc_defaults), .B(cnt_3_q), .C(w_inv_cnt_0_q), .Y(w_c12_n1));
  INV_X1 U_c12_inv1 (.A(w_c12_n1), .Y(w_c12_i1));
  NAND2_X1 U_c12_root (.A(w_c12_i0), .B(w_c12_i1), .Y(w_c12));
  // Shared: en_lowFreq, oc_ctrl_bgr_d
  wire w_c13_n0, w_c13_i0;
  NAND4_X1 U_c13_n0 (.A(w_inv_c_DfT_en_LP), .B(w_inv_c_DfT_en_PWM), .C(c_DfT_oc_dig_VDD[1]), .D(c_DfT_oc_dig_VDD[0]), .Y(w_c13_n0));
  INV_X1 U_c13_inv0 (.A(w_c13_n0), .Y(w_c13_i0));
  wire w_c13_n1, w_c13_i1;
  NAND3_X1 U_c13_n1 (.A(c_metalFix_invert_oc_defaults), .B(cnt_3_q), .C(w_inv_cnt_0_q), .Y(w_c13_n1));
  INV_X1 U_c13_inv1 (.A(w_c13_n1), .Y(w_c13_i1));
  NAND2_X1 U_c13_root (.A(w_c13_i0), .B(w_c13_i1), .Y(w_c13));
  // Shared: en_lowFreq, oc_ctrl_bgr_d
  wire w_c14_n0, w_c14_i0;
  NAND4_X1 U_c14_n0 (.A(w_inv_c_DfT_en_LP), .B(w_inv_c_DfT_en_PWM), .C(w_inv_c_DfT_oc_dig_VDD_1), .D(w_inv_c_DfT_oc_dig_VDD_0), .Y(w_c14_n0));
  INV_X1 U_c14_inv0 (.A(w_c14_n0), .Y(w_c14_i0));
  wire w_c14_n1, w_c14_i1;
  NAND3_X1 U_c14_n1 (.A(w_inv_c_metalFix_invert_oc_defaults), .B(w_inv_cnt_0_q), .C(w_inv_startup_q), .Y(w_c14_n1));
  INV_X1 U_c14_inv1 (.A(w_c14_n1), .Y(w_c14_i1));
  NAND2_X1 U_c14_root (.A(w_c14_i0), .B(w_c14_i1), .Y(w_c14));
  // Output: en_lowFreq
  NAND3_X1 U_c15 (.A(w_inv_c_DfT_en_LP), .B(c_DfT_en_PWM), .C(en_LP_q), .Y(w_c15));
  // Shared: en_lowFreq, oc_ctrl_bgr_d
  wire w_c16_n0, w_c16_i0;
  NAND4_X1 U_c16_n0 (.A(w_inv_c_DfT_en_LP), .B(w_inv_c_DfT_en_PWM), .C(w_inv_c_DfT_oc_dig_VDD_1), .D(w_inv_c_DfT_oc_dig_VDD_0), .Y(w_c16_n0));
  INV_X1 U_c16_inv0 (.A(w_c16_n0), .Y(w_c16_i0));
  wire w_c16_n1, w_c16_i1;
  NAND3_X1 U_c16_n1 (.A(w_inv_c_metalFix_invert_oc_defaults), .B(cnt_2_q), .C(w_inv_cnt_0_q), .Y(w_c16_n1));
  INV_X1 U_c16_inv1 (.A(w_c16_n1), .Y(w_c16_i1));
  NAND2_X1 U_c16_root (.A(w_c16_i0), .B(w_c16_i1), .Y(w_c16));
  // Shared: en_lowFreq, oc_ctrl_bgr_d
  wire w_c17_n0, w_c17_i0;
  NAND4_X1 U_c17_n0 (.A(w_inv_c_DfT_en_LP), .B(w_inv_c_DfT_en_PWM), .C(w_inv_c_DfT_oc_dig_VDD_1), .D(w_inv_c_DfT_oc_dig_VDD_0), .Y(w_c17_n0));
  INV_X1 U_c17_inv0 (.A(w_c17_n0), .Y(w_c17_i0));
  wire w_c17_n1, w_c17_i1;
  NAND3_X1 U_c17_n1 (.A(w_inv_c_metalFix_invert_oc_defaults), .B(cnt_1_q), .C(w_inv_cnt_0_q), .Y(w_c17_n1));
  INV_X1 U_c17_inv1 (.A(w_c17_n1), .Y(w_c17_i1));
  NAND2_X1 U_c17_root (.A(w_c17_i0), .B(w_c17_i1), .Y(w_c17));
  // Output: cnt[3]_d
  NAND4_X1 U_c18 (.A(w_inv_cnt_3_q), .B(cnt_2_q), .C(cnt_1_q), .D(cnt_0_q), .Y(w_c18));
  // Output: cnt[3]_d
  NAND2_X1 U_c19 (.A(cnt_3_q), .B(w_inv_cnt_0_q), .Y(w_c19));
  // Output: cnt[3]_d
  NAND2_X1 U_c20 (.A(cnt_3_q), .B(w_inv_cnt_2_q), .Y(w_c20));
  // Output: cnt[3]_d
  NAND2_X1 U_c21 (.A(cnt_3_q), .B(w_inv_cnt_1_q), .Y(w_c21));
  // Output: cnt[2]_d
  NAND2_X1 U_c22 (.A(cnt_2_q), .B(w_inv_cnt_0_q), .Y(w_c22));
  // Output: cnt[2]_d
  NAND3_X1 U_c23 (.A(w_inv_cnt_2_q), .B(cnt_1_q), .C(cnt_0_q), .Y(w_c23));
  // Output: cnt[2]_d
  NAND2_X1 U_c24 (.A(cnt_2_q), .B(w_inv_cnt_1_q), .Y(w_c24));
  // Output: cnt[1]_d
  NAND2_X1 U_c25 (.A(w_inv_cnt_1_q), .B(cnt_0_q), .Y(w_c25));
  // Output: cnt[1]_d
  NAND2_X1 U_c26 (.A(cnt_1_q), .B(w_inv_cnt_0_q), .Y(w_c26));
  assign w_c27 = cnt_0_q; // Output: cnt[0]_d
  // Output: startup_d
  NAND2_X1 U_c28 (.A(w_inv_cnt_3_q), .B(startup_q), .Y(w_c28));
  // Output: startup_d
  NAND2_X1 U_c29 (.A(w_inv_cnt_1_q), .B(startup_q), .Y(w_c29));
  // Output: startup_d
  NAND2_X1 U_c30 (.A(w_inv_cnt_2_q), .B(startup_q), .Y(w_c30));
  // Output: startup_d
  NAND2_X1 U_c31 (.A(w_inv_cnt_0_q), .B(startup_q), .Y(w_c31));
  assign w_c32 = w_inv_c_DfT_en_LP; // Output: en_LP_d
  // Output: en_LP_d
  NAND3_X1 U_c33 (.A(c_DfT_en_PWM), .B(w_inv_cnt_3_q), .C(cnt_1_q), .Y(w_c33));
  // Output: en_LP_d
  NAND3_X1 U_c34 (.A(c_DfT_en_PWM), .B(w_inv_cnt_1_q), .C(cnt_0_q), .Y(w_c34));
  // Output: en_LP_d
  NAND3_X1 U_c35 (.A(c_DfT_en_PWM), .B(cnt_2_q), .C(w_inv_cnt_0_q), .Y(w_c35));
  // Output: en_LP_d
  NAND3_X1 U_c36 (.A(c_DfT_en_PWM), .B(cnt_3_q), .C(w_inv_cnt_2_q), .Y(w_c36));
  // Output: oc_ctrl_bgr_d
  wire w_c37_n0, w_c37_i0;
  NAND4_X1 U_c37_n0 (.A(w_inv_c_DfT_en_LP), .B(c_DfT_en_PWM), .C(w_inv_c_DfT_oc_dig_VDD_0), .D(c_metalFix_invert_oc_defaults), .Y(w_c37_n0));
  INV_X1 U_c37_inv0 (.A(w_c37_n0), .Y(w_c37_i0));
  wire w_c37_n1, w_c37_i1;
  NAND2_X1 U_c37_n1 (.A(cnt_1_q), .B(oc_ctrl_bgr_q), .Y(w_c37_n1));
  INV_X1 U_c37_inv1 (.A(w_c37_n1), .Y(w_c37_i1));
  NAND2_X1 U_c37_root (.A(w_c37_i0), .B(w_c37_i1), .Y(w_c37));
  // Output: oc_ctrl_bgr_d
  wire w_c38_n0, w_c38_i0;
  NAND4_X1 U_c38_n0 (.A(w_inv_c_DfT_en_LP), .B(c_DfT_oc_dig_VDD[0]), .C(w_inv_c_metalFix_invert_oc_defaults), .D(w_inv_cnt_3_q), .Y(w_c38_n0));
  INV_X1 U_c38_inv0 (.A(w_c38_n0), .Y(w_c38_i0));
  wire w_c38_n1, w_c38_i1;
  NAND4_X1 U_c38_n1 (.A(w_inv_cnt_2_q), .B(w_inv_cnt_1_q), .C(w_inv_cnt_0_q), .D(w_inv_oc_ctrl_bgr_q), .Y(w_c38_n1));
  INV_X1 U_c38_inv1 (.A(w_c38_n1), .Y(w_c38_i1));
  NAND2_X1 U_c38_root (.A(w_c38_i0), .B(w_c38_i1), .Y(w_c38));
  // Output: oc_ctrl_bgr_d
  wire w_c39_n0, w_c39_i0;
  NAND4_X1 U_c39_n0 (.A(w_inv_c_DfT_en_LP), .B(c_DfT_en_PWM), .C(c_DfT_oc_dig_VDD[0]), .D(w_inv_c_metalFix_invert_oc_defaults), .Y(w_c39_n0));
  INV_X1 U_c39_inv0 (.A(w_c39_n0), .Y(w_c39_i0));
  wire w_c39_n1, w_c39_i1;
  NAND2_X1 U_c39_n1 (.A(cnt_3_q), .B(oc_ctrl_bgr_q), .Y(w_c39_n1));
  INV_X1 U_c39_inv1 (.A(w_c39_n1), .Y(w_c39_i1));
  NAND2_X1 U_c39_root (.A(w_c39_i0), .B(w_c39_i1), .Y(w_c39));
  // Output: oc_ctrl_bgr_d
  wire w_c40_n0, w_c40_i0;
  NAND4_X1 U_c40_n0 (.A(w_inv_c_DfT_en_LP), .B(c_DfT_en_PWM), .C(c_DfT_oc_dig_VDD[1]), .D(c_metalFix_invert_oc_defaults), .Y(w_c40_n0));
  INV_X1 U_c40_inv0 (.A(w_c40_n0), .Y(w_c40_i0));
  wire w_c40_n1, w_c40_i1;
  NAND3_X1 U_c40_n1 (.A(cnt_3_q), .B(cnt_2_q), .C(cnt_1_q), .Y(w_c40_n1));
  INV_X1 U_c40_inv1 (.A(w_c40_n1), .Y(w_c40_i1));
  NAND2_X1 U_c40_root (.A(w_c40_i0), .B(w_c40_i1), .Y(w_c40));
  // Output: oc_ctrl_bgr_d
  wire w_c41_n0, w_c41_i0;
  NAND4_X1 U_c41_n0 (.A(w_inv_c_DfT_en_LP), .B(c_DfT_en_PWM), .C(w_inv_c_DfT_oc_dig_VDD_0), .D(c_metalFix_invert_oc_defaults), .Y(w_c41_n0));
  INV_X1 U_c41_inv0 (.A(w_c41_n0), .Y(w_c41_i0));
  wire w_c41_n1, w_c41_i1;
  NAND2_X1 U_c41_n1 (.A(cnt_0_q), .B(oc_ctrl_bgr_q), .Y(w_c41_n1));
  INV_X1 U_c41_inv1 (.A(w_c41_n1), .Y(w_c41_i1));
  NAND2_X1 U_c41_root (.A(w_c41_i0), .B(w_c41_i1), .Y(w_c41));
  // Output: oc_ctrl_bgr_d
  wire w_c42_n0, w_c42_i0;
  NAND4_X1 U_c42_n0 (.A(w_inv_c_DfT_en_LP), .B(c_DfT_en_PWM), .C(w_inv_c_DfT_oc_dig_VDD_0), .D(c_metalFix_invert_oc_defaults), .Y(w_c42_n0));
  INV_X1 U_c42_inv0 (.A(w_c42_n0), .Y(w_c42_i0));
  wire w_c42_n1, w_c42_i1;
  NAND2_X1 U_c42_n1 (.A(cnt_3_q), .B(oc_ctrl_bgr_q), .Y(w_c42_n1));
  INV_X1 U_c42_inv1 (.A(w_c42_n1), .Y(w_c42_i1));
  NAND2_X1 U_c42_root (.A(w_c42_i0), .B(w_c42_i1), .Y(w_c42));
  // Output: oc_ctrl_bgr_d
  wire w_c43_n0, w_c43_i0;
  NAND4_X1 U_c43_n0 (.A(w_inv_c_DfT_en_LP), .B(c_DfT_en_PWM), .C(w_inv_c_DfT_oc_dig_VDD_1), .D(w_inv_c_metalFix_invert_oc_defaults), .Y(w_c43_n0));
  INV_X1 U_c43_inv0 (.A(w_c43_n0), .Y(w_c43_i0));
  wire w_c43_n1, w_c43_i1;
  NAND3_X1 U_c43_n1 (.A(cnt_3_q), .B(cnt_2_q), .C(cnt_1_q), .Y(w_c43_n1));
  INV_X1 U_c43_inv1 (.A(w_c43_n1), .Y(w_c43_i1));
  NAND2_X1 U_c43_root (.A(w_c43_i0), .B(w_c43_i1), .Y(w_c43));
  // Output: oc_ctrl_bgr_d
  wire w_c44_n0, w_c44_i0;
  NAND4_X1 U_c44_n0 (.A(w_inv_c_DfT_en_LP), .B(w_inv_c_DfT_oc_dig_VDD_0), .C(c_metalFix_invert_oc_defaults), .D(w_inv_cnt_3_q), .Y(w_c44_n0));
  INV_X1 U_c44_inv0 (.A(w_c44_n0), .Y(w_c44_i0));
  wire w_c44_n1, w_c44_i1;
  NAND4_X1 U_c44_n1 (.A(w_inv_cnt_2_q), .B(w_inv_cnt_1_q), .C(w_inv_cnt_0_q), .D(w_inv_oc_ctrl_bgr_q), .Y(w_c44_n1));
  INV_X1 U_c44_inv1 (.A(w_c44_n1), .Y(w_c44_i1));
  NAND2_X1 U_c44_root (.A(w_c44_i0), .B(w_c44_i1), .Y(w_c44));
  // Output: oc_ctrl_bgr_d
  NAND4_X1 U_c45 (.A(w_inv_c_DfT_en_LP), .B(c_DfT_oc_dig_VDD[1]), .C(w_inv_c_DfT_oc_dig_VDD_0), .D(c_metalFix_invert_oc_defaults), .Y(w_c45));
  // Output: oc_ctrl_bgr_d
  wire w_c46_n0, w_c46_i0;
  NAND4_X1 U_c46_n0 (.A(w_inv_c_DfT_en_LP), .B(c_DfT_en_PWM), .C(c_DfT_oc_dig_VDD[0]), .D(w_inv_c_metalFix_invert_oc_defaults), .Y(w_c46_n0));
  INV_X1 U_c46_inv0 (.A(w_c46_n0), .Y(w_c46_i0));
  wire w_c46_n1, w_c46_i1;
  NAND2_X1 U_c46_n1 (.A(cnt_2_q), .B(oc_ctrl_bgr_q), .Y(w_c46_n1));
  INV_X1 U_c46_inv1 (.A(w_c46_n1), .Y(w_c46_i1));
  NAND2_X1 U_c46_root (.A(w_c46_i0), .B(w_c46_i1), .Y(w_c46));
  // Output: oc_ctrl_bgr_d
  NAND4_X1 U_c47 (.A(w_inv_c_DfT_en_LP), .B(w_inv_c_DfT_oc_dig_VDD_1), .C(c_DfT_oc_dig_VDD[0]), .D(w_inv_c_metalFix_invert_oc_defaults), .Y(w_c47));
  // Output: oc_ctrl_bgr_d
  wire w_c48_n0, w_c48_i0;
  NAND4_X1 U_c48_n0 (.A(w_inv_c_DfT_en_LP), .B(c_DfT_en_PWM), .C(c_DfT_oc_dig_VDD[0]), .D(w_inv_c_metalFix_invert_oc_defaults), .Y(w_c48_n0));
  INV_X1 U_c48_inv0 (.A(w_c48_n0), .Y(w_c48_i0));
  wire w_c48_n1, w_c48_i1;
  NAND2_X1 U_c48_n1 (.A(cnt_1_q), .B(oc_ctrl_bgr_q), .Y(w_c48_n1));
  INV_X1 U_c48_inv1 (.A(w_c48_n1), .Y(w_c48_i1));
  NAND2_X1 U_c48_root (.A(w_c48_i0), .B(w_c48_i1), .Y(w_c48));
  // Output: oc_ctrl_bgr_d
  wire w_c49_n0, w_c49_i0;
  NAND4_X1 U_c49_n0 (.A(w_inv_c_DfT_en_LP), .B(w_inv_c_DfT_en_PWM), .C(c_DfT_oc_dig_VDD[0]), .D(w_inv_c_metalFix_invert_oc_defaults), .Y(w_c49_n0));
  INV_X1 U_c49_inv0 (.A(w_c49_n0), .Y(w_c49_i0));
  wire w_c49_n1, w_c49_i1;
  INV_X1 U_c49_n1 (.A(w_inv_oc_ctrl_bgr_q), .Y(w_c49_n1));
  INV_X1 U_c49_inv1 (.A(w_c49_n1), .Y(w_c49_i1));
  NAND2_X1 U_c49_root (.A(w_c49_i0), .B(w_c49_i1), .Y(w_c49));
  // Output: oc_ctrl_bgr_d
  wire w_c50_n0, w_c50_i0;
  NAND4_X1 U_c50_n0 (.A(w_inv_c_DfT_en_LP), .B(w_inv_c_DfT_en_PWM), .C(w_inv_c_DfT_oc_dig_VDD_0), .D(c_metalFix_invert_oc_defaults), .Y(w_c50_n0));
  INV_X1 U_c50_inv0 (.A(w_c50_n0), .Y(w_c50_i0));
  wire w_c50_n1, w_c50_i1;
  INV_X1 U_c50_n1 (.A(w_inv_oc_ctrl_bgr_q), .Y(w_c50_n1));
  INV_X1 U_c50_inv1 (.A(w_c50_n1), .Y(w_c50_i1));
  NAND2_X1 U_c50_root (.A(w_c50_i0), .B(w_c50_i1), .Y(w_c50));
  // Output: oc_ctrl_bgr_d
  wire w_c51_n0, w_c51_i0;
  NAND4_X1 U_c51_n0 (.A(w_inv_c_DfT_en_LP), .B(c_DfT_en_PWM), .C(c_DfT_oc_dig_VDD[0]), .D(w_inv_c_metalFix_invert_oc_defaults), .Y(w_c51_n0));
  INV_X1 U_c51_inv0 (.A(w_c51_n0), .Y(w_c51_i0));
  wire w_c51_n1, w_c51_i1;
  NAND2_X1 U_c51_n1 (.A(cnt_0_q), .B(oc_ctrl_bgr_q), .Y(w_c51_n1));
  INV_X1 U_c51_inv1 (.A(w_c51_n1), .Y(w_c51_i1));
  NAND2_X1 U_c51_root (.A(w_c51_i0), .B(w_c51_i1), .Y(w_c51));
  // Output: oc_ctrl_bgr_d
  wire w_c52_n0, w_c52_i0;
  NAND4_X1 U_c52_n0 (.A(w_inv_c_DfT_en_LP), .B(c_DfT_en_PWM), .C(w_inv_c_DfT_oc_dig_VDD_0), .D(c_metalFix_invert_oc_defaults), .Y(w_c52_n0));
  INV_X1 U_c52_inv0 (.A(w_c52_n0), .Y(w_c52_i0));
  wire w_c52_n1, w_c52_i1;
  NAND2_X1 U_c52_n1 (.A(cnt_2_q), .B(oc_ctrl_bgr_q), .Y(w_c52_n1));
  INV_X1 U_c52_inv1 (.A(w_c52_n1), .Y(w_c52_i1));
  NAND2_X1 U_c52_root (.A(w_c52_i0), .B(w_c52_i1), .Y(w_c52));

  // 3. Output Stage Combinational Gates (NAND Combinations of Shared Wires)
  NAND2_X1 U_out_oc_select (.A(w_c0), .B(w_c1), .Y(oc_select));
  wire w_out_oc_ctrl_cp_ch0;
  NAND4_X1 U_out_oc_ctrl_cp_ch0 (.A(w_c2), .B(w_c3), .C(w_c4), .D(w_c5), .Y(w_out_oc_ctrl_cp_ch0));
  wire w_out_oc_ctrl_cp_inv_ch0;
  INV_X1 U_out_oc_ctrl_cp_inv0 (.A(w_out_oc_ctrl_cp_ch0), .Y(w_out_oc_ctrl_cp_inv_ch0));
  wire w_out_oc_ctrl_cp_ch1;
  NAND3_X1 U_out_oc_ctrl_cp_ch1 (.A(w_c6), .B(w_c7), .C(w_c8), .Y(w_out_oc_ctrl_cp_ch1));
  wire w_out_oc_ctrl_cp_inv_ch1;
  INV_X1 U_out_oc_ctrl_cp_inv1 (.A(w_out_oc_ctrl_cp_ch1), .Y(w_out_oc_ctrl_cp_inv_ch1));
  NAND2_X1 U_out_oc_ctrl_cp_root (.A(w_out_oc_ctrl_cp_inv_ch0), .B(w_out_oc_ctrl_cp_inv_ch1), .Y(oc_ctrl_cp));
  wire w_out_en_lowFreq_ch0;
  NAND4_X1 U_out_en_lowFreq_ch0 (.A(w_c9), .B(w_c10), .C(w_c11), .D(w_c12), .Y(w_out_en_lowFreq_ch0));
  wire w_out_en_lowFreq_inv_ch0;
  INV_X1 U_out_en_lowFreq_inv0 (.A(w_out_en_lowFreq_ch0), .Y(w_out_en_lowFreq_inv_ch0));
  wire w_out_en_lowFreq_ch1;
  NAND4_X1 U_out_en_lowFreq_ch1 (.A(w_c13), .B(w_c14), .C(w_c15), .D(w_c16), .Y(w_out_en_lowFreq_ch1));
  wire w_out_en_lowFreq_inv_ch1;
  INV_X1 U_out_en_lowFreq_inv1 (.A(w_out_en_lowFreq_ch1), .Y(w_out_en_lowFreq_inv_ch1));
  wire w_out_en_lowFreq_ch2;
  INV_X1 U_out_en_lowFreq_ch2 (.A(w_c17), .Y(w_out_en_lowFreq_ch2));
  wire w_out_en_lowFreq_inv_ch2;
  INV_X1 U_out_en_lowFreq_inv2 (.A(w_out_en_lowFreq_ch2), .Y(w_out_en_lowFreq_inv_ch2));
  NAND3_X1 U_out_en_lowFreq_root (.A(w_out_en_lowFreq_inv_ch0), .B(w_out_en_lowFreq_inv_ch1), .C(w_out_en_lowFreq_inv_ch2), .Y(en_lowFreq));
  NAND4_X1 U_out_cnt_3_d (.A(w_c18), .B(w_c19), .C(w_c20), .D(w_c21), .Y(cnt_3_d));
  NAND3_X1 U_out_cnt_2_d (.A(w_c22), .B(w_c23), .C(w_c24), .Y(cnt_2_d));
  NAND2_X1 U_out_cnt_1_d (.A(w_c25), .B(w_c26), .Y(cnt_1_d));
  INV_X1   U_out_cnt_0_d (.A(w_c27), .Y(cnt_0_d));
  NAND4_X1 U_out_startup_d (.A(w_c28), .B(w_c29), .C(w_c30), .D(w_c31), .Y(startup_d));
  wire w_out_en_LP_d_ch0;
  NAND4_X1 U_out_en_LP_d_ch0 (.A(w_c32), .B(w_c33), .C(w_c34), .D(w_c35), .Y(w_out_en_LP_d_ch0));
  wire w_out_en_LP_d_inv_ch0;
  INV_X1 U_out_en_LP_d_inv0 (.A(w_out_en_LP_d_ch0), .Y(w_out_en_LP_d_inv_ch0));
  wire w_out_en_LP_d_ch1;
  INV_X1 U_out_en_LP_d_ch1 (.A(w_c36), .Y(w_out_en_LP_d_ch1));
  wire w_out_en_LP_d_inv_ch1;
  INV_X1 U_out_en_LP_d_inv1 (.A(w_out_en_LP_d_ch1), .Y(w_out_en_LP_d_inv_ch1));
  NAND2_X1 U_out_en_LP_d_root (.A(w_out_en_LP_d_inv_ch0), .B(w_out_en_LP_d_inv_ch1), .Y(en_LP_d));
  wire w_out_oc_ctrl_bgr_d_ch0;
  NAND4_X1 U_out_oc_ctrl_bgr_d_ch0 (.A(w_c37), .B(w_c17), .C(w_c38), .D(w_c39), .Y(w_out_oc_ctrl_bgr_d_ch0));
  wire w_out_oc_ctrl_bgr_d_inv_ch0;
  INV_X1 U_out_oc_ctrl_bgr_d_inv0 (.A(w_out_oc_ctrl_bgr_d_ch0), .Y(w_out_oc_ctrl_bgr_d_inv_ch0));
  wire w_out_oc_ctrl_bgr_d_ch1;
  NAND4_X1 U_out_oc_ctrl_bgr_d_ch1 (.A(w_c10), .B(w_c40), .C(w_c11), .D(w_c41), .Y(w_out_oc_ctrl_bgr_d_ch1));
  wire w_out_oc_ctrl_bgr_d_inv_ch1;
  INV_X1 U_out_oc_ctrl_bgr_d_inv1 (.A(w_out_oc_ctrl_bgr_d_ch1), .Y(w_out_oc_ctrl_bgr_d_inv_ch1));
  wire w_out_oc_ctrl_bgr_d_ch2;
  NAND4_X1 U_out_oc_ctrl_bgr_d_ch2 (.A(w_c12), .B(w_c13), .C(w_c14), .D(w_c42), .Y(w_out_oc_ctrl_bgr_d_ch2));
  wire w_out_oc_ctrl_bgr_d_inv_ch2;
  INV_X1 U_out_oc_ctrl_bgr_d_inv2 (.A(w_out_oc_ctrl_bgr_d_ch2), .Y(w_out_oc_ctrl_bgr_d_inv_ch2));
  wire w_out_oc_ctrl_bgr_d_ch3;
  NAND4_X1 U_out_oc_ctrl_bgr_d_ch3 (.A(w_c43), .B(w_c44), .C(w_c45), .D(w_c46), .Y(w_out_oc_ctrl_bgr_d_ch3));
  wire w_out_oc_ctrl_bgr_d_inv_ch3;
  INV_X1 U_out_oc_ctrl_bgr_d_inv3 (.A(w_out_oc_ctrl_bgr_d_ch3), .Y(w_out_oc_ctrl_bgr_d_inv_ch3));
  wire w_out_oc_ctrl_bgr_d_ch4;
  NAND4_X1 U_out_oc_ctrl_bgr_d_ch4 (.A(w_c47), .B(w_c48), .C(w_c49), .D(w_c50), .Y(w_out_oc_ctrl_bgr_d_ch4));
  wire w_out_oc_ctrl_bgr_d_inv_ch4;
  INV_X1 U_out_oc_ctrl_bgr_d_inv4 (.A(w_out_oc_ctrl_bgr_d_ch4), .Y(w_out_oc_ctrl_bgr_d_inv_ch4));
  wire w_out_oc_ctrl_bgr_d_ch5;
  NAND4_X1 U_out_oc_ctrl_bgr_d_ch5 (.A(w_c16), .B(w_c51), .C(w_c9), .D(w_c52), .Y(w_out_oc_ctrl_bgr_d_ch5));
  wire w_out_oc_ctrl_bgr_d_inv_ch5;
  INV_X1 U_out_oc_ctrl_bgr_d_inv5 (.A(w_out_oc_ctrl_bgr_d_ch5), .Y(w_out_oc_ctrl_bgr_d_inv_ch5));
  wire w_out_oc_ctrl_bgr_d_root_ch0;
  NAND4_X1 U_out_oc_ctrl_bgr_d_root_ch0 (.A(w_out_oc_ctrl_bgr_d_inv_ch0), .B(w_out_oc_ctrl_bgr_d_inv_ch1), .C(w_out_oc_ctrl_bgr_d_inv_ch2), .D(w_out_oc_ctrl_bgr_d_inv_ch3), .Y(w_out_oc_ctrl_bgr_d_root_ch0));
  wire w_out_oc_ctrl_bgr_d_root_inv_ch0;
  INV_X1 U_out_oc_ctrl_bgr_d_root_inv0 (.A(w_out_oc_ctrl_bgr_d_root_ch0), .Y(w_out_oc_ctrl_bgr_d_root_inv_ch0));
  wire w_out_oc_ctrl_bgr_d_root_ch1;
  NAND2_X1 U_out_oc_ctrl_bgr_d_root_ch1 (.A(w_out_oc_ctrl_bgr_d_inv_ch4), .B(w_out_oc_ctrl_bgr_d_inv_ch5), .Y(w_out_oc_ctrl_bgr_d_root_ch1));
  wire w_out_oc_ctrl_bgr_d_root_inv_ch1;
  INV_X1 U_out_oc_ctrl_bgr_d_root_inv1 (.A(w_out_oc_ctrl_bgr_d_root_ch1), .Y(w_out_oc_ctrl_bgr_d_root_inv_ch1));
  NAND2_X1 U_out_oc_ctrl_bgr_d_root_root (.A(w_out_oc_ctrl_bgr_d_root_inv_ch0), .B(w_out_oc_ctrl_bgr_d_root_inv_ch1), .Y(oc_ctrl_bgr_d));

  // 4. Sequential Register Bank
  DFFR_X1 U_dff_cnt_3      (.D(cnt_3_d), .CK(clk_i), .RN(res_n), .Q(cnt_3_q), .QN());
  DFFR_X1 U_dff_cnt_2      (.D(cnt_2_d), .CK(clk_i), .RN(res_n), .Q(cnt_2_q), .QN());
  DFFR_X1 U_dff_cnt_1      (.D(cnt_1_d), .CK(clk_i), .RN(res_n), .Q(cnt_1_q), .QN());
  DFFR_X1 U_dff_cnt_0      (.D(cnt_0_d), .CK(clk_i), .RN(res_n), .Q(cnt_0_q), .QN());
  DFFS_X1 U_dff_startup    (.D(startup_d), .CK(clk_i), .SN(res_n), .Q(startup_q), .QN());
  DFFR_X1 U_dff_en_LP      (.D(en_LP_d), .CK(clk_i), .RN(res_n), .Q(en_LP_q), .QN());
  DFFS_X1 U_dff_oc_ctrl_bgr (.D(oc_ctrl_bgr_d), .CK(clk_i), .SN(res_n), .Q(oc_ctrl_bgr_q), .QN());

  // Extended Output Aliases
  assign oc_ctrl_bgr   = oc_ctrl_bgr_q;
  assign en_LP         = en_LP_q;
  assign oc_select_ext = oc_select;
  assign oc_ctrl_cp_ext= oc_ctrl_cp;
  assign en_LP_ext     = en_LP;

endmodule
