# Quick Prototyping Schematic Guide: PWM_CTRL_netlist

Auto-generated from `/Users/ssyr/Git/digitalOptimizer/examples/PWM_CTRL_netlist.v`.

## 1. Instance Arrays Summary

| Cell Type | Instance Array Name | Count | Terminals |
| :--- | :--- | :---: | :--- |
| **INV** | `INV<87:1>` | 87 | `A, Y` |
| **NAND2** | `NAND2<51:1>` | 51 | `A, B, Y` |
| **NAND4** | `NAND4<47:1>` | 47 | `A, B, C, D, Y` |
| **NAND3** | `NAND3<19:1>` | 19 | `A, B, C, Y` |
| **DFFR** | `DFFR<5:1>` | 5 | `D, CK, RN, Q, QN` |
| **Term** | `Term<2:1>` | 2 | `A, Y` |
| **DFFS** | `DFFS<2:1>` | 2 | `D, CK, SN, Q, QN` |
| **Combinational** | `Combinational<1:1>` | 1 | `A, B, C, D, Y` |

## 2. 1-Line Comma-Separated Wire Labels (Virtuoso Ready)

### `INV<87:1>` (87 instances)
```text
Terminal A:
w_out_oc_ctrl_bgr_d_root_ch1, w_out_oc_ctrl_bgr_d_root_ch0, w_out_oc_ctrl_bgr_d_ch5, w_out_oc_ctrl_bgr_d_ch4, w_out_oc_ctrl_bgr_d_ch3, w_out_oc_ctrl_bgr_d_ch2, w_out_oc_ctrl_bgr_d_ch1, w_out_oc_ctrl_bgr_d_ch0, w_out_en_LP_d_ch1, w_c38, w_out_en_LP_d_ch0, w_c29, w_out_en_lowFreq_ch2, w_c19, w_out_en_lowFreq_ch1, w_out_en_lowFreq_ch0, w_out_oc_ctrl_cp_ch1, w_out_oc_ctrl_cp_ch0, w_out_oc_select_ch1, w_c4, w_out_oc_select_ch0, w_c52_n1, w_c52_n0, w_c51_n1, w_c51_n0, w_c50_n1, w_c50_n0, w_c49_n1, w_c49_n0, w_c48_n1, w_inv_oc_ctrl_bgr_q, w_c48_n0, w_c47_n1, w_c47_n0, w_c46_n1, w_c46_n0, w_c45_n1, w_c45_n0, w_c44_n1, w_c44_n0, w_c43_n1, w_c43_n0, w_c42_n1, w_c42_n0, w_c41_n1, w_inv_oc_ctrl_bgr_q, w_c41_n0, w_c40_n1, w_c40_n0, w_c39_n1, w_c39_n0, w_c19_n1, w_c19_n0, w_c18_n1, w_c18_n0, w_c17_n1, w_c17_n0, w_c16_n1, w_c16_n0, w_c15_n1, w_c15_n0, w_c14_n1, w_c14_n0, w_c13_n1, w_c13_n0, w_c12_n1, w_c12_n0, w_c10_n1, w_c10_n0, w_c8_n1, oc_ctrl_bgr_q, w_c8_n0, w_c7_n1, oc_ctrl_bgr_q, w_c7_n0, oc_ctrl_bgr_q, en_LP_q, startup_q, cnt_0_q, cnt_1_q, cnt_2_q, cnt_3_q, c_metalFix_invert_oc_defaults, c_DfT_oc_dig_VDD[0], c_DfT_oc_dig_VDD[1], c_DfT_en_PWM, c_DfT_en_LP

Terminal Y:
w_out_oc_ctrl_bgr_d_root_inv_ch1, w_out_oc_ctrl_bgr_d_root_inv_ch0, w_out_oc_ctrl_bgr_d_inv_ch5, w_out_oc_ctrl_bgr_d_inv_ch4, w_out_oc_ctrl_bgr_d_inv_ch3, w_out_oc_ctrl_bgr_d_inv_ch2, w_out_oc_ctrl_bgr_d_inv_ch1, w_out_oc_ctrl_bgr_d_inv_ch0, w_out_en_LP_d_inv_ch1, w_out_en_LP_d_ch1, w_out_en_LP_d_inv_ch0, cnt_0_d, w_out_en_lowFreq_inv_ch2, w_out_en_lowFreq_ch2, w_out_en_lowFreq_inv_ch1, w_out_en_lowFreq_inv_ch0, w_out_oc_ctrl_cp_inv_ch1, w_out_oc_ctrl_cp_inv_ch0, w_out_oc_select_inv_ch1, w_out_oc_select_ch1, w_out_oc_select_inv_ch0, w_c52_i1, w_c52_i0, w_c51_i1, w_c51_i0, w_c50_i1, w_c50_i0, w_c49_i1, w_c49_i0, w_c48_i1, w_c48_n1, w_c48_i0, w_c47_i1, w_c47_i0, w_c46_i1, w_c46_i0, w_c45_i1, w_c45_i0, w_c44_i1, w_c44_i0, w_c43_i1, w_c43_i0, w_c42_i1, w_c42_i0, w_c41_i1, w_c41_n1, w_c41_i0, w_c40_i1, w_c40_i0, w_c39_i1, w_c39_i0, w_c19_i1, w_c19_i0, w_c18_i1, w_c18_i0, w_c17_i1, w_c17_i0, w_c16_i1, w_c16_i0, w_c15_i1, w_c15_i0, w_c14_i1, w_c14_i0, w_c13_i1, w_c13_i0, w_c12_i1, w_c12_i0, w_c10_i1, w_c10_i0, w_c8_i1, w_c8_n1, w_c8_i0, w_c7_i1, w_c7_n1, w_c7_i0, w_inv_oc_ctrl_bgr_q, w_inv_en_LP_q, w_inv_startup_q, w_inv_cnt_0_q, w_inv_cnt_1_q, w_inv_cnt_2_q, w_inv_cnt_3_q, w_inv_c_metalFix_invert_oc_defaults, w_inv_c_DfT_oc_dig_VDD_0, w_inv_c_DfT_oc_dig_VDD_1, w_inv_c_DfT_en_PWM, w_inv_c_DfT_en_LP

```

### `NAND2<51:1>` (51 instances)
```text
Terminal A:
w_out_oc_ctrl_bgr_d_root_inv_ch0, w_out_oc_ctrl_bgr_d_inv_ch4, w_out_en_LP_d_inv_ch0, w_c27, w_out_oc_ctrl_cp_inv_ch0, w_c9, w_out_oc_select_inv_ch0, w_c52_i0, w_c51_i0, cnt_3_q, w_c50_i0, cnt_3_q, w_c49_i0, cnt_1_q, w_c48_i0, w_c47_i0, w_c46_i0, cnt_2_q, w_c45_i0, cnt_2_q, w_c44_i0, cnt_1_q, w_c43_i0, w_c42_i0, cnt_0_q, w_c41_i0, w_c40_i0, w_c39_i0, cnt_0_q, w_inv_cnt_2_q, w_inv_cnt_3_q, w_inv_cnt_1_q, w_inv_cnt_0_q, cnt_1_q, w_inv_cnt_1_q, cnt_2_q, cnt_2_q, cnt_3_q, cnt_3_q, cnt_3_q, w_c19_i0, w_c18_i0, w_c17_i0, w_c16_i0, w_c15_i0, w_c14_i0, w_c13_i0, w_c12_i0, w_c10_i0, w_c8_i0, w_c7_i0

Terminal B:
w_out_oc_ctrl_bgr_d_root_inv_ch1, w_out_oc_ctrl_bgr_d_inv_ch5, w_out_en_LP_d_inv_ch1, w_c28, w_out_oc_ctrl_cp_inv_ch1, w_c10, w_out_oc_select_inv_ch1, w_c52_i1, w_c51_i1, oc_ctrl_bgr_q, w_c50_i1, oc_ctrl_bgr_q, w_c49_i1, oc_ctrl_bgr_q, w_c48_i1, w_c47_i1, w_c46_i1, oc_ctrl_bgr_q, w_c45_i1, oc_ctrl_bgr_q, w_c44_i1, oc_ctrl_bgr_q, w_c43_i1, w_c42_i1, oc_ctrl_bgr_q, w_c41_i1, w_c40_i1, w_c39_i1, oc_ctrl_bgr_q, startup_q, startup_q, startup_q, startup_q, w_inv_cnt_0_q, cnt_0_q, w_inv_cnt_0_q, w_inv_cnt_1_q, w_inv_cnt_1_q, w_inv_cnt_2_q, w_inv_cnt_0_q, w_c19_i1, w_c18_i1, w_c17_i1, w_c16_i1, w_c15_i1, w_c14_i1, w_c13_i1, w_c12_i1, w_c10_i1, w_c8_i1, w_c7_i1

Terminal Y:
oc_ctrl_bgr_d, w_out_oc_ctrl_bgr_d_root_ch1, en_LP_d, cnt_1_d, oc_ctrl_cp, w_out_oc_ctrl_cp_ch1, oc_select, w_c52, w_c51, w_c51_n1, w_c50, w_c50_n1, w_c49, w_c49_n1, w_c48, w_c47, w_c46, w_c46_n1, w_c45, w_c45_n1, w_c44, w_c44_n1, w_c43, w_c42, w_c42_n1, w_c41, w_c40, w_c39, w_c39_n1, w_c33, w_c32, w_c31, w_c30, w_c28, w_c27, w_c25, w_c24, w_c23, w_c22, w_c20, w_c19, w_c18, w_c17, w_c16, w_c15, w_c14, w_c13, w_c12, w_c10, w_c8, w_c7

```

### `NAND4<47:1>` (47 instances)
```text
Terminal A:
w_out_oc_ctrl_bgr_d_inv_ch0, w_c49, w_c4, w_c3, w_c14, w_c12, w_c39, w_c34, w_c30, w_c20, w_c15, w_c11, w_c5, w_inv_cnt_2_q, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_cnt_2_q, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_cnt_3_q, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_cnt_1_q, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP

Terminal B:
w_out_oc_ctrl_bgr_d_inv_ch1, w_c50, w_c18, w_c16, w_c44, w_c13, w_c40, w_c35, w_c31, w_c21, w_c16, w_c12, w_c6, w_inv_cnt_1_q, w_inv_c_DfT_oc_dig_VDD_0, c_DfT_en_PWM, c_DfT_en_PWM, c_DfT_en_PWM, w_inv_c_DfT_en_PWM, w_inv_cnt_1_q, c_DfT_oc_dig_VDD[0], c_DfT_en_PWM, c_DfT_en_PWM, c_DfT_en_PWM, c_DfT_en_PWM, c_DfT_en_PWM, w_inv_c_DfT_en_PWM, c_DfT_en_PWM, c_DfT_en_PWM, cnt_2_q, w_inv_c_DfT_en_PWM, w_inv_c_DfT_en_PWM, w_inv_c_DfT_en_PWM, w_inv_c_DfT_en_PWM, w_inv_c_DfT_en_PWM, w_inv_c_DfT_en_PWM, w_inv_c_DfT_en_PWM, w_inv_c_DfT_en_PWM, cnt_0_q, w_inv_c_DfT_en_PWM, c_DfT_oc_dig_VDD[1], w_inv_c_DfT_oc_dig_VDD_1, c_DfT_oc_dig_VDD[1], w_inv_c_DfT_oc_dig_VDD_0, w_inv_c_DfT_oc_dig_VDD_1, w_inv_c_DfT_oc_dig_VDD_1, c_DfT_oc_dig_VDD[1]

Terminal C:
w_out_oc_ctrl_bgr_d_inv_ch2, w_c51, w_c47, w_c46, w_c45, w_c42, w_c41, w_c36, w_c32, w_c22, w_c17, w_c13, w_c7, w_inv_cnt_0_q, c_metalFix_invert_oc_defaults, w_inv_c_DfT_oc_dig_VDD_0, c_DfT_oc_dig_VDD[0], c_DfT_oc_dig_VDD[0], c_DfT_oc_dig_VDD[0], w_inv_cnt_0_q, w_inv_c_metalFix_invert_oc_defaults, w_inv_c_DfT_oc_dig_VDD_0, c_DfT_oc_dig_VDD[0], w_inv_c_DfT_oc_dig_VDD_0, c_DfT_oc_dig_VDD[1], c_DfT_oc_dig_VDD[0], w_inv_c_DfT_oc_dig_VDD_0, w_inv_c_DfT_oc_dig_VDD_1, w_inv_c_DfT_oc_dig_VDD_0, cnt_1_q, w_inv_c_DfT_oc_dig_VDD_1, c_DfT_oc_dig_VDD[1], c_DfT_oc_dig_VDD[1], w_inv_c_DfT_oc_dig_VDD_1, c_DfT_oc_dig_VDD[1], c_DfT_oc_dig_VDD[1], w_inv_c_DfT_oc_dig_VDD_1, w_inv_c_DfT_oc_dig_VDD_1, startup_q, w_inv_cnt_3_q, w_inv_c_metalFix_invert_oc_defaults, w_inv_c_DfT_oc_dig_VDD_0, c_DfT_oc_dig_VDD[0], c_metalFix_invert_oc_defaults, c_DfT_oc_dig_VDD[0], c_DfT_oc_dig_VDD[0], w_inv_c_DfT_oc_dig_VDD_0

Terminal D:
w_out_oc_ctrl_bgr_d_inv_ch3, w_c52, w_c48, w_c17, w_c15, w_c43, w_c19, w_c37, w_c33, w_c23, w_c18, w_c14, w_c8, w_inv_oc_ctrl_bgr_q, w_inv_cnt_3_q, c_metalFix_invert_oc_defaults, w_inv_c_metalFix_invert_oc_defaults, w_inv_c_metalFix_invert_oc_defaults, w_inv_c_metalFix_invert_oc_defaults, w_inv_oc_ctrl_bgr_q, w_inv_cnt_3_q, c_metalFix_invert_oc_defaults, w_inv_c_metalFix_invert_oc_defaults, c_metalFix_invert_oc_defaults, c_metalFix_invert_oc_defaults, w_inv_c_metalFix_invert_oc_defaults, c_metalFix_invert_oc_defaults, w_inv_c_metalFix_invert_oc_defaults, c_metalFix_invert_oc_defaults, cnt_0_q, w_inv_c_DfT_oc_dig_VDD_0, c_DfT_oc_dig_VDD[0], c_DfT_oc_dig_VDD[0], w_inv_c_DfT_oc_dig_VDD_0, c_DfT_oc_dig_VDD[0], c_DfT_oc_dig_VDD[0], w_inv_c_DfT_oc_dig_VDD_0, w_inv_c_DfT_oc_dig_VDD_0, w_inv_oc_ctrl_bgr_q, w_inv_cnt_2_q, w_inv_oc_ctrl_bgr_q, w_inv_c_metalFix_invert_oc_defaults, c_metalFix_invert_oc_defaults, w_inv_oc_ctrl_bgr_q, w_inv_oc_ctrl_bgr_q, w_inv_c_metalFix_invert_oc_defaults, c_metalFix_invert_oc_defaults

Terminal Y:
w_out_oc_ctrl_bgr_d_root_ch0, w_out_oc_ctrl_bgr_d_ch5, w_out_oc_ctrl_bgr_d_ch4, w_out_oc_ctrl_bgr_d_ch3, w_out_oc_ctrl_bgr_d_ch2, w_out_oc_ctrl_bgr_d_ch1, w_out_oc_ctrl_bgr_d_ch0, w_out_en_LP_d_ch0, startup_d, cnt_3_d, w_out_en_lowFreq_ch1, w_out_en_lowFreq_ch0, w_out_oc_ctrl_cp_ch0, w_c52_n1, w_c52_n0, w_c51_n0, w_c50_n0, w_c49_n0, w_c48_n0, w_c47_n1, w_c47_n0, w_c46_n0, w_c45_n0, w_c44_n0, w_c43_n0, w_c42_n0, w_c41_n0, w_c40_n0, w_c39_n0, w_c21, w_c19_n0, w_c18_n0, w_c17_n0, w_c16_n0, w_c15_n0, w_c14_n0, w_c13_n0, w_c12_n0, w_c10_n1, w_c10_n0, w_c9, w_c8_n0, w_c7_n0, w_c6, w_c5, w_c4, w_c3

```

### `NAND3<19:1>` (19 instances)
```text
Terminal A:
w_c24, w_out_en_lowFreq_inv_ch0, cnt_3_q, cnt_3_q, c_DfT_en_PWM, c_DfT_en_PWM, c_DfT_en_PWM, c_DfT_en_PWM, w_inv_cnt_2_q, w_inv_c_metalFix_invert_oc_defaults, c_metalFix_invert_oc_defaults, c_metalFix_invert_oc_defaults, w_inv_c_metalFix_invert_oc_defaults, c_metalFix_invert_oc_defaults, c_metalFix_invert_oc_defaults, w_inv_c_metalFix_invert_oc_defaults, w_inv_c_metalFix_invert_oc_defaults, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP

Terminal B:
w_c25, w_out_en_lowFreq_inv_ch1, cnt_2_q, cnt_2_q, cnt_2_q, w_inv_cnt_1_q, cnt_3_q, w_inv_cnt_3_q, cnt_1_q, cnt_2_q, cnt_2_q, cnt_1_q, cnt_3_q, cnt_3_q, w_inv_cnt_0_q, cnt_1_q, w_inv_cnt_0_q, c_DfT_en_PWM, w_inv_c_DfT_oc_dig_VDD_1

Terminal C:
w_c26, w_out_en_lowFreq_inv_ch2, cnt_1_q, cnt_1_q, w_inv_cnt_0_q, cnt_0_q, w_inv_cnt_2_q, cnt_1_q, cnt_0_q, w_inv_cnt_0_q, w_inv_cnt_0_q, w_inv_cnt_0_q, w_inv_cnt_0_q, w_inv_cnt_0_q, w_inv_startup_q, w_inv_cnt_0_q, w_inv_startup_q, en_LP_q, c_metalFix_invert_oc_defaults

Terminal Y:
cnt_2_d, en_lowFreq, w_c43_n1, w_c40_n1, w_c38, w_c37, w_c36, w_c35, w_c26, w_c19_n1, w_c18_n1, w_c17_n1, w_c16_n1, w_c15_n1, w_c14_n1, w_c13_n1, w_c12_n1, w_c11, w_c2

```

### `DFFR<5:1>` (5 instances)
```text
Terminal D:
en_LP_d, cnt_0_d, cnt_1_d, cnt_2_d, cnt_3_d

Terminal CK:
clk_i, clk_i, clk_i, clk_i, clk_i

Terminal RN:
res_n, res_n, res_n, res_n, res_n

Terminal Q:
en_LP_q, cnt_0_q, cnt_1_q, cnt_2_q, cnt_3_q

Terminal QN:
, , , , 

```

### `Term<2:1>` (2 instances)
```text
Terminal A:
w_inv_c_DfT_en_LP, res_n

Terminal Y:
w_c1, w_inv_res_n

```

### `DFFS<2:1>` (2 instances)
```text
Terminal D:
oc_ctrl_bgr_d, startup_d

Terminal CK:
clk_i, clk_i

Terminal SN:
res_n, res_n

Terminal Q:
oc_ctrl_bgr_q, startup_q

Terminal QN:
, 

```

### `Combinational<1:1>` (1 instances)
```text
Terminal A:
w_c0

Terminal B:
w_c1

Terminal C:
w_c2

Terminal D:
w_c3

Terminal Y:
w_out_oc_select_ch0

```
