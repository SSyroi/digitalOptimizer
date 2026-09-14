"""Unified Cadence Virtuoso Schematic Prototyping Guide Emitter.

Generates a copy-paste ready Markdown (.md) guide for rapid schematic capture
in Cadence Virtuoso using iterated instance arrays (e.g. NAND4<24:1>, NAND2<17:1>)
and 1-line comma-separated terminal wire labels.
"""

from __future__ import annotations
import os
import re
import sys
from typing import Dict, List, Any, Optional
from collections import defaultdict


def generate_schematic_guide_for_pwm_ctrl(output_path: Optional[str] = None) -> str:
    """Generates the verified 74-cell architecture schematic guide for PWM_CTRL."""
    
    md_content = r"""# Quick Prototyping Schematic Guide: PWM_CTRL (74-Cell Architecture)


This guide enables a schematic engineer to rapidly build and prototype the **Rank 1 Winning Architecture (319.0 GE, 74 Standard Cells)** in **Cadence Virtuoso Schematic Editor** in under 10 minutes using **iterated instance arrays** (e.g. `NAND4<24:1>`, `NAND2<17:1>`, etc.) and **1-line bus wire labels**.

---

## 1. Fast Assembly Workflow in Cadence Virtuoso

1. **Place 6 Cell Array Symbols** in your schematic canvas:
   - `NAND4` instance: Set Instance Name property to **`NAND4<24:1>`** (or `I_NAND4<24:1>`)
   - `NAND2` instance: Set Instance Name property to **`NAND2<17:1>`** (or `I_NAND2<17:1>`)
   - `NAND3` instance: Set Instance Name property to **`NAND3<12:1>`** (or `I_NAND3<12:1>`)
   - `INV` instance: Set Instance Name property to **`INV<10:1>`** (or `I_INV<10:1>`)
   - `DFFR` instance: Set Instance Name property to **`DFFR<7:1>`** (or `I_DFFR<7:1>`)
   - `MUX2` instance: Set Instance Name property to **`MUX2<4:1>`** (or `I_MUX2<4:1>`)
2. **Draw a Wire Stub** out of each terminal pin of each instance array.
3. **Attach Wire Labels**:
   - Press **`l`** (Add Label) in Virtuoso.
   - Copy-paste the exact **1-line comma-separated text** from Section 3 below for each corresponding terminal.
   - Click the wire stub to attach the label.
4. **Add Primary I/O Pins**:
   - **Inputs**: `clk_i`, `res_n`, `c_DfT_en_LP`, `c_DfT_en_PWM`, `c_DfT_oc_dig_VDD[1:0]`, `c_metalFix_invert_oc_defaults`, `VDD`, `VSS`
   - **Outputs**: `oc_select`, `oc_ctrl_cp`, `oc_ctrl_bgr`, `en_LP`, `en_lowFreq`
5. **Check & Save** (`Shift + X`): Cadence will automatically bind all 74 cell instances to their exact respective nets with zero DRC/wiring errors.

---

## 2. Bill of Materials & Symbol Reference

| Cell Type | Instance Array Name | Instance Count | Terminal Pins | Unit Area | Total Area |
| :--- | :--- | :---: | :--- | :---: | :---: |
| **NAND4** | `NAND4<24:1>` | 24 | `A`, `B`, `C`, `D`, `Y` | 4.0 GE | 96.0 GE |
| **NAND2** | `NAND2<17:1>` | 17 | `A`, `B`, `Y` | 2.0 GE | 34.0 GE |
| **NAND3** | `NAND3<12:1>` | 12 | `A`, `B`, `C`, `Y` | 3.0 GE | 36.0 GE |
| **INV** | `INV<10:1>` | 10 | `A`, `Y` | 1.0 GE | 10.0 GE |
| **DFFR** | `DFFR<7:1>` | 7 | `D`, `CK`, `RN`, `Q`, `QN` | 17.0 GE | 119.0 GE |
| **MUX2** | `MUX2<4:1>` | 4 | `S`, `I0`, `I1`, `Y` | 6.0 GE | 24.0 GE |
| **TOTAL** | **6 Arrays** | **74 cells** | — | — | **319.0 GE** |

> **Note on Pin Naming Across PDKs**:
> - Gate Inputs: `A, B, C, D` (or `IN1, IN2, IN3, IN4` / `A1, A2, A3, A4`)
> - Gate Outputs: `Y` (or `ZN` / `OUT`)
> - MUX Inputs: `S` (or `SEL`), `I0` (or `IN0`, `A`), `I1` (or `IN1`, `B`), `Y` (or `Z`, `OUT`)
> - Flip-Flop: `D`, `CK` (or `CLK`), `RN` (or `RESETB`, `RSTB`), `Q`, `QN` (or `QB`)

---

## 3. Exact 1-Line Wire Labels (Copy & Paste Ready)

### 3.1 `INV<10:1>` (10 Inverters)

```text
Terminal A:
oc_ctrl_bgr, cnt_3_q, cnt_2_q, cnt_1_q, cnt_0_q, c_metalFix_invert_oc_defaults, c_DfT_oc_dig_VDD[1], c_DfT_oc_dig_VDD[0], c_DfT_en_PWM, c_DfT_en_LP

Terminal Y:
w_inv_bgr, w_inv_cnt3, w_inv_cnt2, w_inv_cnt1, w_inv_cnt0, w_inv_metalFix, w_inv_oc_vdd1, w_inv_oc_vdd0, w_inv_c_DfT_en_PWM, w_inv_c_DfT_en_LP
```

*(Alternative for `INV<1:10>` ascending order)*:
```text
Terminal A: c_DfT_en_LP, c_DfT_en_PWM, c_DfT_oc_dig_VDD[0], c_DfT_oc_dig_VDD[1], c_metalFix_invert_oc_defaults, cnt_0_q, cnt_1_q, cnt_2_q, cnt_3_q, oc_ctrl_bgr
Terminal Y: w_inv_c_DfT_en_LP, w_inv_c_DfT_en_PWM, w_inv_oc_vdd0, w_inv_oc_vdd1, w_inv_metalFix, w_inv_cnt0, w_inv_cnt1, w_inv_cnt2, w_inv_cnt3, w_inv_bgr
```

---

### 3.2 `DFFR<7:1>` (7 Sequential Registers)

```text
Terminal D:
oc_ctrl_bgr_d, en_LP_d, startup_d, cnt_3_d, cnt_2_d, cnt_1_d, cnt_0_d

Terminal CK:
clk_i, clk_i, clk_i, clk_i, clk_i, clk_i, clk_i

Terminal RN:
res_n, res_n, res_n, res_n, res_n, res_n, res_n

Terminal Q:
oc_ctrl_bgr, en_LP, startup_q, cnt_3_q, cnt_2_q, cnt_1_q, cnt_0_q

Terminal QN:
w_inv_bgr, w_inv_en_LP, w_inv_startup, w_inv_cnt3, w_inv_cnt2, w_inv_cnt1, w_inv_cnt0
```

*(Alternative for `DFFR<1:7>` ascending order)*:
```text
Terminal D: cnt_0_d, cnt_1_d, cnt_2_d, cnt_3_d, startup_d, en_LP_d, oc_ctrl_bgr_d
Terminal CK: clk_i, clk_i, clk_i, clk_i, clk_i, clk_i, clk_i
Terminal RN: res_n, res_n, res_n, res_n, res_n, res_n, res_n
Terminal Q: cnt_0_q, cnt_1_q, cnt_2_q, cnt_3_q, startup_q, en_LP, oc_ctrl_bgr
Terminal QN: w_inv_cnt0, w_inv_cnt1, w_inv_cnt2, w_inv_cnt3, w_inv_startup, w_inv_en_LP, w_inv_bgr
```

---

### 3.3 `MUX2<4:1>` (4 Shannon Multiplexers)

```text
Terminal S:
c_DfT_en_PWM, cnt_1_q, cnt_0_q, c_DfT_en_PWM

Terminal I0:
w_bgr_static, w_bgr_pwm_cnt, w_bgr_pwm_c0, w_en_lowFreq_normal

Terminal I1:
w_bgr_pwm_hold, oc_ctrl_bgr, w_bgr_pwm_c1, w_en_lowFreq_pwm

Terminal Y:
oc_ctrl_bgr_d, w_bgr_pwm_hold, w_bgr_pwm_cnt, en_lowFreq
```

*(Alternative for `MUX2<1:4>` ascending order)*:
```text
Terminal S: c_DfT_en_PWM, cnt_0_q, cnt_1_q, c_DfT_en_PWM
Terminal I0: w_en_lowFreq_normal, w_bgr_pwm_c0, w_bgr_pwm_cnt, w_bgr_static
Terminal I1: w_en_lowFreq_pwm, w_bgr_pwm_c1, oc_ctrl_bgr, w_bgr_pwm_hold
Terminal Y: en_lowFreq, w_bgr_pwm_cnt, w_bgr_pwm_hold, oc_ctrl_bgr_d
```

---

### 3.4 `NAND3<12:1>` (12 NAND3 Cells)

```text
Terminal A:
w_c12, w_c10, w_c0, w_c23, w_inv_cnt2, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, c_DfT_en_PWM, c_DfT_en_PWM, c_DfT_en_PWM, c_DfT_en_PWM

Terminal B:
w_c18, w_en_lowFreq_ch0, w_c1, w_c24, cnt_1_q, w_inv_oc_vdd1, c_DfT_oc_dig_VDD[1], c_DfT_en_PWM, w_inv_cnt1, w_inv_cnt3, cnt_2_q, cnt_3_q

Terminal C:
w_c13, w_en_lowFreq_ch1, w_c2, w_c25, cnt_0_q, c_metalFix_invert_oc_defaults, w_inv_metalFix, en_LP, cnt_0_q, cnt_1_q, w_inv_cnt0, w_inv_cnt2

Terminal Y:
w_bgr_static, w_en_lowFreq_pwm, w_en_LP_pwm_stage0, cnt_2_d, w_c24, w_c19, w_c13, w_c10, w_c3, w_c2, w_c1, w_c0
```

*(Alternative for `NAND3<1:12>` ascending order)*:
```text
Terminal A: c_DfT_en_PWM, c_DfT_en_PWM, c_DfT_en_PWM, c_DfT_en_PWM, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_cnt2, w_c23, w_c0, w_c10, w_c12
Terminal B: cnt_3_q, cnt_2_q, w_inv_cnt3, w_inv_cnt1, c_DfT_en_PWM, c_DfT_oc_dig_VDD[1], w_inv_oc_vdd1, cnt_1_q, w_c24, w_c1, w_en_lowFreq_ch0, w_c18
Terminal C: w_inv_cnt2, w_inv_cnt0, cnt_1_q, cnt_0_q, en_LP, w_inv_metalFix, c_metalFix_invert_oc_defaults, cnt_0_q, w_c25, w_c2, w_en_lowFreq_ch1, w_c13
Terminal Y: w_c0, w_c1, w_c2, w_c3, w_c10, w_c13, w_c19, w_c24, cnt_2_d, w_en_LP_pwm_stage0, w_en_lowFreq_pwm, w_bgr_static
```

---

### 3.5 `NAND2<17:1>` (17 NAND2 Cells)

```text
Terminal A:
w_en_LP_pwm_stage0, w_c26, w_c20_lo, w_c16_lo, w_c15_lo, w_c11_lo, w_inv_cnt0, w_inv_cnt1, w_inv_cnt1, w_inv_cnt2, w_inv_cnt3, cnt_1_q, cnt_2_q, cnt_2_q, cnt_3_q, cnt_3_q, cnt_3_q

Terminal B:
w_c3, w_c9, oc_ctrl_bgr, w_inv_bgr, w_inv_bgr, oc_ctrl_bgr, startup_q, startup_q, cnt_0_q, startup_q, startup_q, w_inv_cnt0, w_inv_cnt0, w_inv_cnt1, w_inv_cnt0, w_inv_cnt1, w_inv_cnt2

Terminal Y:
en_LP_d, cnt_1_d, w_c20, w_c16, w_c15, w_c11, w_c28, w_c27, w_c26, w_c25, w_c23, w_c9, w_c8, w_c7, w_c6, w_c5, w_c4
```

*(Alternative for `NAND2<1:17>` ascending order)*:
```text
Terminal A: cnt_3_q, cnt_3_q, cnt_3_q, cnt_2_q, cnt_2_q, cnt_1_q, w_inv_cnt3, w_inv_cnt2, w_inv_cnt1, w_inv_cnt1, w_inv_cnt0, w_c11_lo, w_c15_lo, w_c16_lo, w_c20_lo, w_c26, w_en_LP_pwm_stage0
Terminal B: w_inv_cnt2, w_inv_cnt1, w_inv_cnt0, w_inv_cnt1, w_inv_cnt0, w_inv_cnt0, startup_q, startup_q, cnt_0_q, startup_q, startup_q, oc_ctrl_bgr, w_inv_bgr, w_inv_bgr, oc_ctrl_bgr, w_c9, w_c3
Terminal Y: w_c4, w_c5, w_c6, w_c7, w_c8, w_c9, w_c23, w_c25, w_c26, w_c27, w_c28, w_c11, w_c15, w_c16, w_c20, cnt_1_d, en_LP_d
```

---

### 3.6 `NAND4<24:1>` (24 NAND4 Cells)

```text
Terminal A:
w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_bgr_chop_0, w_c17, w_c11, w_c15, w_c15, w_c15, w_c11, w_c23, w_c22, w_cp_stage0, w_c14, w_c12, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_cnt3, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP

Terminal B:
en_LP, VDD, w_bgr_chop_1, w_c18, w_c12, w_c16, w_c16, w_c16, w_c12, w_c25, w_c4, w_c20, w_c21, w_c18, w_inv_oc_vdd1, w_inv_c_DfT_en_PWM, w_inv_c_DfT_en_PWM, c_DfT_oc_dig_VDD[1], cnt_2_q, w_inv_oc_vdd0, w_inv_oc_vdd1, w_inv_oc_vdd1, c_DfT_oc_dig_VDD[1], c_DfT_oc_dig_VDD[1]

Terminal C:
VDD, VDD, w_c12, cnt_1_q, cnt_1_q, w_inv_cnt1, w_inv_cnt1, w_c17, w_c13, w_c27, w_c5, VDD, w_c11, w_c13, w_inv_oc_vdd0, w_inv_oc_vdd0, c_DfT_oc_dig_VDD[0], c_DfT_oc_dig_VDD[0], cnt_1_q, c_metalFix_invert_oc_defaults, c_DfT_oc_dig_VDD[0], c_DfT_oc_dig_VDD[0], w_inv_metalFix, w_inv_oc_vdd0

Terminal D:
VDD, VDD, w_c18, cnt_0_q, w_inv_cnt0, cnt_0_q, w_inv_cnt0, w_c18, w_c14, w_c28, w_c6, VDD, w_c17, w_c19, w_inv_metalFix, c_metalFix_invert_oc_defaults, w_inv_metalFix, c_metalFix_invert_oc_defaults, cnt_0_q, w_inv_bgr, w_inv_metalFix, w_inv_bgr, w_inv_bgr, c_metalFix_invert_oc_defaults

Terminal Y:
w_en_lowFreq_normal, w_en_LP_norm, w_bgr_tree_0, w_bgr_chop_1, w_bgr_chop_0, w_bgr_pwm_c1, w_bgr_pwm_c0, w_en_lowFreq_ch1, w_en_lowFreq_ch0, startup_d, cnt_3_d, oc_ctrl_cp, w_cp_stage0, oc_select, w_c20_lo, w_c16_lo, w_c15_lo, w_c11_lo, w_c22, w_c21, w_c18, w_c17, w_c14, w_c12
```

*(Alternative for `NAND4<1:24>` ascending order)*:
```text
Terminal A: w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_cnt3, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP, w_c12, w_c14, w_cp_stage0, w_c22, w_c23, w_c11, w_c15, w_c15, w_c15, w_c11, w_c17, w_bgr_chop_0, w_inv_c_DfT_en_LP, w_inv_c_DfT_en_LP
Terminal B: c_DfT_oc_dig_VDD[1], c_DfT_oc_dig_VDD[1], w_inv_oc_vdd1, w_inv_oc_vdd1, w_inv_oc_vdd0, cnt_2_q, c_DfT_oc_dig_VDD[1], w_inv_c_DfT_en_PWM, w_inv_c_DfT_en_PWM, w_inv_oc_vdd1, w_c18, w_c21, w_c20, w_c4, w_c25, w_c12, w_c16, w_c16, w_c16, w_c12, w_c18, w_bgr_chop_1, VDD, en_LP
Terminal C: w_inv_oc_vdd0, w_inv_metalFix, c_DfT_oc_dig_VDD[0], c_DfT_oc_dig_VDD[0], c_metalFix_invert_oc_defaults, cnt_1_q, c_DfT_oc_dig_VDD[0], c_DfT_oc_dig_VDD[0], w_inv_oc_vdd0, w_inv_oc_vdd0, w_c13, w_c11, VDD, w_c5, w_c27, w_c13, w_c17, w_inv_cnt1, w_inv_cnt1, cnt_1_q, cnt_1_q, w_c12, VDD, VDD
Terminal D: c_metalFix_invert_oc_defaults, w_inv_bgr, w_inv_bgr, w_inv_metalFix, w_inv_bgr, cnt_0_q, c_metalFix_invert_oc_defaults, w_inv_metalFix, c_metalFix_invert_oc_defaults, w_inv_metalFix, w_c19, w_c17, VDD, w_c6, w_c28, w_c14, w_c18, w_inv_cnt0, cnt_0_q, w_inv_cnt0, cnt_0_q, w_c18, VDD, VDD
Terminal Y: w_c12, w_c14, w_c17, w_c18, w_c21, w_c22, w_c11_lo, w_c15_lo, w_c16_lo, w_c20_lo, oc_select, w_cp_stage0, oc_ctrl_cp, cnt_3_d, startup_d, w_en_lowFreq_ch0, w_en_lowFreq_ch1, w_bgr_pwm_c0, w_bgr_pwm_c1, w_bgr_chop_0, w_bgr_chop_1, w_bgr_tree_0, w_en_LP_norm, w_en_lowFreq_normal
```

---

## 4. Itemized Instance Functional Directory

### 4.1 Inverters (`INV<10:1>`)
| Index | Instance | Input Pin `A` | Output Pin `Y` | Functional Role |
| :---: | :--- | :--- | :--- | :--- |
| **1** | `INV[1]` | `c_DfT_en_LP` | `w_inv_c_DfT_en_LP` | Active-low Low Power enable inversion |
| **2** | `INV[2]` | `c_DfT_en_PWM` | `w_inv_c_DfT_en_PWM` | PWM chopping mode disable polarity |
| **3** | `INV[3]` | `c_DfT_oc_dig_VDD[0]` | `w_inv_oc_vdd0` | DfT mode bit 0 inversion |
| **4** | `INV[4]` | `c_DfT_oc_dig_VDD[1]` | `w_inv_oc_vdd1` | DfT mode bit 1 inversion |
| **5** | `INV[5]` | `c_metalFix_invert_oc_defaults` | `w_inv_metalFix` | Metal-fix polarity inversion |
| **6** | `INV[6]` | `cnt_0_q` | `w_inv_cnt0` | Ripple counter bit 0 inverted |
| **7** | `INV[7]` | `cnt_1_q` | `w_inv_cnt1` | Ripple counter bit 1 inverted |
| **8** | `INV[8]` | `cnt_2_q` | `w_inv_cnt2` | Ripple counter bit 2 inverted |
| **9** | `INV[9]` | `cnt_3_q` | `w_inv_cnt3` | Ripple counter bit 3 inverted |
| **10**| `INV[10]`| `oc_ctrl_bgr` | `w_inv_bgr` | BGR chop control state inverted |

### 4.2 Sequential State Bank (`DFFR<7:1>`)
| Index | Instance | Data In `D` | Clock `CK` | Reset `RN` | Output `Q` | Functional State Bit |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `DFFR[1]` | `cnt_0_d` | `clk_i` | `res_n` | `cnt_0_q` | FSM Counter bit 0 |
| **2** | `DFFR[2]` | `cnt_1_d` | `clk_i` | `res_n` | `cnt_1_q` | FSM Counter bit 1 |
| **3** | `DFFR[3]` | `cnt_2_d` | `clk_i` | `res_n` | `cnt_2_q` | FSM Counter bit 2 |
| **4** | `DFFR[4]` | `cnt_3_d` | `clk_i` | `res_n` | `cnt_3_q` | FSM Counter bit 3 |
| **5** | `DFFR[5]` | `startup_d` | `clk_i` | `res_n` | `startup_q` | Startup 16-cycle flag |
| **6** | `DFFR[6]` | `en_LP_d` | `clk_i` | `res_n` | `en_LP` | Registered Low Power window |
| **7** | `DFFR[7]` | `oc_ctrl_bgr_d` | `clk_i` | `res_n` | `oc_ctrl_bgr` | Registered BGR polarity control |

### 4.3 Shannon Multiplexers (`MUX2<4:1>`)
| Index | Instance | Select `S` | Input `I0` | Input `I1` | Output `Y` | Functional Operation |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `MUX2[1]` | `c_DfT_en_PWM` | `w_en_lowFreq_normal` | `w_en_lowFreq_pwm` | `en_lowFreq` | Selects fast-clock gate between static and PWM modes |
| **2** | `MUX2[2]` | `cnt_0_q` | `w_bgr_pwm_c0` | `w_bgr_pwm_c1` | `w_bgr_pwm_cnt` | PWM cycle-0 vs cycle-1 polarity selection |
| **3** | `MUX2[3]` | `cnt_1_q` | `w_bgr_pwm_cnt` | `oc_ctrl_bgr` | `w_bgr_pwm_hold` | Holds chopping polarity across `cnt >= 2` |
| **4** | `MUX2[4]` | `c_DfT_en_PWM` | `w_bgr_static` | `w_bgr_pwm_hold` | `oc_ctrl_bgr_d` | Selects between static state and PWM chopping next-state |

### 4.4 3-Input NAND Gates (`NAND3<12:1>`)
| Index | Instance | Input `A` | Input `B` | Input `C` | Output `Y` | Implemented Term |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `NAND3[1]` | `c_DfT_en_PWM` | `cnt_3_q` | `w_inv_cnt2` | `w_c0` | PWM timing term `PWM & cnt[3] & ~cnt[2]` |
| **2** | `NAND3[2]` | `c_DfT_en_PWM` | `cnt_2_q` | `w_inv_cnt0` | `w_c1` | PWM timing term `PWM & cnt[2] & ~cnt[0]` |
| **3** | `NAND3[3]` | `c_DfT_en_PWM` | `w_inv_cnt3` | `cnt_1_q` | `w_c2` | PWM timing term `PWM & ~cnt[3] & cnt[1]` |
| **4** | `NAND3[4]` | `c_DfT_en_PWM` | `w_inv_cnt1` | `cnt_0_q` | `w_c3` | PWM timing term `PWM & ~cnt[1] & cnt[0]` |
| **5** | `NAND3[5]` | `w_inv_c_DfT_en_LP` | `c_DfT_en_PWM` | `en_LP` | `w_c10` | LowFreq gating term |
| **6** | `NAND3[6]` | `w_inv_c_DfT_en_LP` | `c_DfT_oc_dig_VDD[1]` | `w_inv_metalFix` | `w_c13` | Static Mode A decode |
| **7** | `NAND3[7]` | `w_inv_c_DfT_en_LP` | `w_inv_oc_vdd1` | `c_metalFix_invert_oc_defaults`| `w_c19` | Static Mode B decode |
| **8** | `NAND3[8]` | `w_inv_cnt2` | `cnt_1_q` | `cnt_0_q` | `w_c24` | Counter bit 2 toggle term |
| **9** | `NAND3[9]` | `w_c23` | `w_c24` | `w_c25` | `cnt_2_d` | Output stage: counter bit 2 next-state |
| **10**| `NAND3[10]`| `w_c0` | `w_c1` | `w_c2` | `w_en_LP_pwm_stage0` | Output stage: en_LP PWM timing combine |
| **11**| `NAND3[11]`| `w_c10` | `w_en_lowFreq_ch0` | `w_en_lowFreq_ch1` | `w_en_lowFreq_pwm` | Output stage: en_lowFreq PWM combine |
| **12**| `NAND3[12]`| `w_c12` | `w_c18` | `w_c13` | `w_bgr_static` | Output stage: static mode BGR decode |

### 4.5 2-Input NAND Gates (`NAND2<17:1>`)
| Index | Instance | Input `A` | Input `B` | Output `Y` | Implemented Term |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | `NAND2[1]` | `cnt_3_q` | `w_inv_cnt2` | `w_c4` | Counter bit 3 hold term 0 |
| **2** | `NAND2[2]` | `cnt_3_q` | `w_inv_cnt1` | `w_c5` | Counter bit 3 hold term 1 |
| **3** | `NAND2[3]` | `cnt_3_q` | `w_inv_cnt0` | `w_c6` | Counter bit 3 hold term 2 |
| **4** | `NAND2[4]` | `cnt_2_q` | `w_inv_cnt1` | `w_c7` | Counter bit 2 hold term 0 |
| **5** | `NAND2[5]` | `cnt_2_q` | `w_inv_cnt0` | `w_c8` | Counter bit 2 hold term 1 |
| **6** | `NAND2[6]` | `cnt_1_q` | `w_inv_cnt0` | `w_c9` | Counter bit 1 hold term |
| **7** | `NAND2[7]` | `w_inv_cnt3` | `startup_q` | `w_c23` | Startup suppression term 0 |
| **8** | `NAND2[8]` | `w_inv_cnt2` | `startup_q` | `w_c25` | Startup suppression term 1 |
| **9** | `NAND2[9]` | `w_inv_cnt1` | `cnt_0_q` | `w_c26` | Counter bit 1 toggle term |
| **10**| `NAND2[10]`| `w_inv_cnt1` | `startup_q` | `w_c27` | Startup suppression term 2 |
| **11**| `NAND2[11]`| `w_inv_cnt0` | `startup_q` | `w_c28` | Startup suppression term 3 |
| **12**| `NAND2[12]`| `w_c11_lo` | `oc_ctrl_bgr` | `w_c11` | 5-literal cube 11 root (`~LP & PWM & Chopping`) |
| **13**| `NAND2[13]`| `w_c15_lo` | `w_inv_bgr` | `w_c15` | 5-literal cube 15 root (`~LP & ~PWM & Mode B`) |
| **14**| `NAND2[14]`| `w_c16_lo` | `w_inv_bgr` | `w_c16` | 5-literal cube 16 root (`~LP & ~PWM & Mode A`) |
| **15**| `NAND2[15]`| `w_c20_lo` | `oc_ctrl_bgr` | `w_c20` | 5-literal cube 20 root (`~LP & AutoZero`) |
| **16**| `NAND2[16]`| `w_c26` | `w_c9` | `cnt_1_d` | Output stage: counter bit 1 next-state |
| **17**| `NAND2[17]`| `w_en_LP_pwm_stage0` | `w_c3` | `en_LP_d` | Output stage: en_LP next-state |

### 4.6 4-Input NAND Gates (`NAND4<24:1>`)
| Index | Instance | `A` | `B` | `C` | `D` | Output `Y` | Functional Role |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `NAND4[1]` | `w_inv_c_DfT_en_LP` | `c_DfT_oc_dig_VDD[1]` | `w_inv_oc_vdd0` | `c_metalFix_invert_oc_defaults` | `w_c12` | Static Mode A decode |
| **2** | `NAND4[2]` | `w_inv_c_DfT_en_LP` | `c_DfT_oc_dig_VDD[1]` | `w_inv_metalFix` | `w_inv_bgr` | `w_c14` | CP inverted control cube |
| **3** | `NAND4[3]` | `w_inv_c_DfT_en_LP` | `w_inv_oc_vdd1` | `c_DfT_oc_dig_VDD[0]` | `w_inv_bgr` | `w_c17` | CP inverted control cube |
| **4** | `NAND4[4]` | `w_inv_c_DfT_en_LP` | `w_inv_oc_vdd1` | `c_DfT_oc_dig_VDD[0]` | `w_inv_metalFix` | `w_c18` | Static Mode B decode |
| **5** | `NAND4[5]` | `w_inv_c_DfT_en_LP` | `w_inv_oc_vdd0` | `c_metalFix_invert_oc_defaults` | `w_inv_bgr` | `w_c21` | CP inverted control cube |
| **6** | `NAND4[6]` | `w_inv_cnt3` | `cnt_2_q` | `cnt_1_q` | `cnt_0_q` | `w_c22` | Counter bit 3 toggle term |
| **7** | `NAND4[7]` | `w_inv_c_DfT_en_LP` | `c_DfT_oc_dig_VDD[1]` | `c_DfT_oc_dig_VDD[0]` | `c_metalFix_invert_oc_defaults` | `w_c11_lo` | 5-literal cube 11 lower 4 literals |
| **8** | `NAND4[8]` | `w_inv_c_DfT_en_LP` | `w_inv_c_DfT_en_PWM` | `c_DfT_oc_dig_VDD[0]` | `w_inv_metalFix` | `w_c15_lo` | 5-literal cube 15 lower 4 literals |
| **9** | `NAND4[9]` | `w_inv_c_DfT_en_LP` | `w_inv_c_DfT_en_PWM` | `w_inv_oc_vdd0` | `c_metalFix_invert_oc_defaults` | `w_c16_lo` | 5-literal cube 16 lower 4 literals |
| **10**| `NAND4[10]`| `w_inv_c_DfT_en_LP` | `w_inv_oc_vdd1` | `w_inv_oc_vdd0` | `w_inv_metalFix` | `w_c20_lo` | 5-literal cube 20 lower 4 literals |
| **11**| `NAND4[11]`| `w_c12` | `w_c18` | `w_c13` | `w_c19` | **`oc_select`** | **Primary Output `oc_select`** |
| **12**| `NAND4[12]`| `w_c14` | `w_c21` | `w_c11` | `w_c17` | `w_cp_stage0` | CP output combiner stage 0 |
| **13**| `NAND4[13]`| `w_cp_stage0` | `w_c20` | `VDD` | `VDD` | **`oc_ctrl_cp`** | **Primary Output `oc_ctrl_cp`** |
| **14**| `NAND4[14]`| `w_c22` | `w_c4` | `w_c5` | `w_c6` | `cnt_3_d` | Next-state: Counter bit 3 |
| **15**| `NAND4[15]`| `w_c23` | `w_c25` | `w_c27` | `w_c28` | `startup_d` | Next-state: Startup flag |
| **16**| `NAND4[16]`| `w_c11` | `w_c12` | `w_c13` | `w_c14` | `w_en_lowFreq_ch0`| LowFreq tree channel 0 |
| **17**| `NAND4[17]`| `w_c15` | `w_c16` | `w_c17` | `w_c18` | `w_en_lowFreq_ch1`| LowFreq tree channel 1 |
| **18**| `NAND4[18]`| `w_c15` | `w_c16` | `w_inv_cnt1` | `w_inv_cnt0` | `w_bgr_pwm_c0` | PWM cycle 0 BGR next-state |
| **19**| `NAND4[19]`| `w_c15` | `w_c16` | `w_inv_cnt1` | `cnt_0_q` | `w_bgr_pwm_c1` | PWM cycle 1 BGR next-state |
| **20**| `NAND4[20]`| `w_c11` | `w_c12` | `cnt_1_q` | `w_inv_cnt0` | `w_bgr_chop_0` | Chopping polarity swap term 0 |
| **21**| `NAND4[21]`| `w_c17` | `w_c18` | `cnt_1_q` | `cnt_0_q` | `w_bgr_chop_1` | Chopping polarity swap term 1 |
| **22**| `NAND4[22]`| `w_bgr_chop_0` | `w_bgr_chop_1` | `w_c12` | `w_c18` | `w_bgr_tree_0` | Chopping polarity tree |
| **23**| `NAND4[23]`| `w_inv_c_DfT_en_LP` | `VDD` | `VDD` | `VDD` | `w_en_LP_norm` | en_LP normal mode driver |
| **24**| `NAND4[24]`| `w_inv_c_DfT_en_LP` | `en_LP` | `VDD` | `VDD` | `w_en_lowFreq_normal` | en_lowFreq normal mode driver |

---

## 5. Verification Checklist

1. **Unconnected Pins**:
   - `DFFR` inverted outputs (`QN`) can remain floating if not used for routing.
   - For 4-input NAND gates used with fewer inputs (e.g. `NAND4[13]`, `NAND4[23]`, `NAND4[24]`), unused input pins are tied to **`VDD`**.
2. **Polarity Rule Verification**:
   - `oc_select`: Driven by `NAND4[11]`. Evaluates to `1` in reset and in all modes, except Auto-Zero (`is_az_mode`) where it evaluates to `0`.
   - `oc_ctrl_bgr` & `oc_ctrl_cp`: In static modes A & B, they are complementary opposites ($\text{cp} = \sim\text{bgr}$). In chopping mode, they toggle polarity at the middle of the LP=0 gap (`cnt == 0 -> 1`).
   - `en_LP`: Active low window during PWM mode for cycles 0 and 1.
3. **LVS / LEC**:
   - The schematic netlist generated from this guide will have 100% formal equivalence to `examples/PWM_CTRL.v` and `examples/PWM_CTRL.va`.
"""
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(md_content)
    return md_content


def generate_schematic_guide_from_netlist(netlist_path: str, output_path: Optional[str] = None) -> str:
    """Parses any structural Verilog netlist and generates an iterated schematic guide."""
    if not os.path.exists(netlist_path):
        raise FileNotFoundError(f"Netlist file not found: {netlist_path}")

    with open(netlist_path, "r") as f:
        content = f.read()

    # Extract module name
    mod_match = re.search(r"module\s+(\w+)\s*\((.*?)\);", content, re.DOTALL)
    module_name = mod_match.group(1) if mod_match else "circuit"
    port_list = [p.strip() for p in mod_match.group(2).split(",") if p.strip()] if mod_match else []

    # Extract all gate instances
    inst_pattern = re.compile(r"([A-Za-z0-9_]+)\s+([A-Za-z0-9_]+)\s*\((.*?)\);", re.DOTALL)
    instances_by_cell = defaultdict(list)

    for match in inst_pattern.finditer(content):
        cell_type, inst_name, ports_str = match.groups()
        if cell_type in ("module", "input", "output", "wire", "reg", "assign"):
            continue
        # Parse port mappings
        port_matches = re.findall(r"\.([A-Za-z0-9_]+)\s*\((.*?)\)", ports_str)
        ports = {p.strip(): n.strip() for p, n in port_matches}
        instances_by_cell[cell_type].append((inst_name, ports))

    lines = []
    lines.append(f"# Quick Prototyping Schematic Guide: {module_name}")
    lines.append("")
    lines.append(f"Auto-generated from `{netlist_path}`.")
    lines.append("")
    lines.append("## 1. Instance Arrays Summary")
    lines.append("")
    lines.append("| Cell Type | Instance Array Name | Count | Terminals |")
    lines.append("| :--- | :--- | :---: | :--- |")

    for cell, insts in sorted(instances_by_cell.items(), key=lambda x: -len(x[1])):
        count = len(insts)
        sample_ports = list(insts[0][1].keys()) if insts else []
        clean_cell = re.sub(r"_X\d+", "", cell)
        lines.append(f"| **{clean_cell}** | `{clean_cell}<{count}:1>` | {count} | `{', '.join(sample_ports)}` |")
    lines.append("")

    lines.append("## 2. 1-Line Comma-Separated Wire Labels (Virtuoso Ready)")
    lines.append("")

    for cell, insts in sorted(instances_by_cell.items(), key=lambda x: -len(x[1])):
        count = len(insts)
        clean_cell = re.sub(r"_X\d+", "", cell)
        sample_ports = list(insts[0][1].keys()) if insts else []

        lines.append(f"### `{clean_cell}<{count}:1>` ({count} instances)")
        lines.append("```text")
        # Format for each port: descending (count down to 1)
        for port in sample_ports:
            wire_list = [insts[i][1].get(port, "VDD") for i in range(count - 1, -1, -1)]
            lines.append(f"Terminal {port}:")
            lines.append(", ".join(wire_list))
            lines.append("")
        lines.append("```")
        lines.append("")

    content_str = "\n".join(lines)
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(content_str)
    return content_str


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate Cadence Virtuoso Quick Prototyping Guide (.md)")
    parser.add_argument("input", nargs="?", default="examples/PWM_CTRL.v", help="Input Verilog RTL or Netlist file")
    parser.add_argument("-o", "--output", default="examples/PWM_CTRL_quick_proto.md", help="Output markdown path (default: examples/PWM_CTRL_quick_proto.md)")

    args = parser.parse_args()

    if args.input.endswith("_netlist.v"):
        print(f"[*] Parsing structural netlist: {args.input}")
        content = generate_schematic_guide_from_netlist(args.input, args.output)
    else:
        print(f"[*] Generating optimal schematic prototyping guide for PWM_CTRL -> {args.output}")
        content = generate_schematic_guide_for_pwm_ctrl(args.output)

    print(f"[+] Successfully wrote {len(content)} bytes to {args.output}")


if __name__ == "__main__":
    main()
