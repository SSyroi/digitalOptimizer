# AMS Digital Logic Optimizer & Synthesizer

<p align="center">
  <img src="https://img.shields.io/badge/status-active-brightgreen.svg" alt="Status">
  <img src="https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/EDA-Cadence%20Virtuoso%20%7C%20Spectre-orange.svg" alt="EDA Compatible">
  <img src="https://img.shields.io/badge/dependencies-zero%20(pure%20python)-green.svg" alt="Zero Dependencies">
  <img src="https://img.shields.io/badge/tests-5%20passing-success.svg" alt="Tests">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
</p>

> **A specialized Multi-Level DAG logic minimization, tech-mapping, and code generation engine for Analog & Mixed-Signal (AMS) IC blocks.**  
> Transforms behavioral Verilog RTL into isolated Flip-Flops, optimized CMOS gates (`NAND`, `NOR`, `MUX2`, `AOI21`, `OAI21`, `XOR2`), simulation-ready Cadence Spectre **Verilog-A** models, and **Cadence Virtuoso SKILL** schematic scripts.

---

### 💡 Key Highlights

- **Zero External Dependencies**: 100% pure Python 3.9+ standard library. Runs out of the box on locked-down corporate UNIX servers without `pip install` or C++ compilers.
- **Multi-Level DAG Sharing**: Preserves intermediate conditions (`is_az_mode`, `is_chop_mode`, `eff_oc_mode`) as shared graph nodes, avoiding the 5.7× gate explosion of flat 2-level truth tables.
- **Exact Mathematical Technology Mapping**:
  - **NPN Bitmask Matching**: Direct integer signature lookup for `AOI21`, `OAI21`, `XOR2`, `XNOR2`, `NAND2/3/4`, `NOR2/3/4`.
  - **Shannon Decomposition**: Automatically extracts 6-transistor transmission-gate `MUX2` cells.
  - **Quine-McCluskey with Don't-Cares ($X$)**: Minimal prime implicants for custom FSM transition cones.
- **Automated FSM State Reachability**: Analyzes reachable state space from reset; marks unreachable states as Don't-Cares to maximize gate reduction.
- **Full Cadence Deliverables & Intermediate Netlist**:
  - **Cadence Spectre Verilog-A (`.va`)**: **Supply-Aware architecture** with dynamic `V(VDD)` / `V(VSS)` output swing (operates at any supply without code edits), input boundary differential thresholding `((V(pin) > V(VDD,VSS)*0.5) ? 1.0 : 0.0)`, pure 0/1 Boolean helper functions, `@(initial_step)` reset, `@(cross(V(clk)-vth, +1))` clock sampling, and detailed Inverter Equivalents (GE) header notes.
  - **Structural Gate Netlist (`.json`)**: Intermediate gate-level netlist capturing all standard cell instances, topological levels, and pin-to-pin connections for future schematic mapping.
  - **Cadence Virtuoso SKILL (`.il`)**: Automated schematic generator placing standard cells in dependency rank columns.
  - **Schematic Bill of Materials (BOM) Report (`.md` / `.txt`)**.

---

## 📊 Benchmark Results

| Circuit | Description | Regs | Total Gates | Inverter Eq. (GE) | Est. Transistors | Key Gates Mapped |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **`PWM_CTRL_registered_bgr.v`** | Multi-mode PWM & AZ (Registered Glitch-Free BGR) | 6 | **112 cells** | **308.0 GE** | **~616 T** | `AOI22`, `AOI21`, `NAND2/3/4`, `NOR2/3`, `DFFR`, `DFFS` |
| **`PWM_CTRL_relaxed.v` (Min Cells)** | Multi-mode PWM & Auto-Zero (Optimal Cell Count) | 7 | **88 cells** | **325.0 GE** | **~650 T** | `AOI22`, `AOI21`, `MUX2`, `NAND2/3/4`, `NOR2/3`, `DFFR`, `DFFS` |
| **`PWM_CTRL_relaxed.v` (Min Area)** | Multi-mode PWM & Auto-Zero (Pure Inverting CMOS) | 7 | **113 cells** | **322.0 GE** | **~644 T** | `AOI22`, `AOI21`, `NAND2/3/4`, `NOR2/3`, `DFFR`, `DFFS` |
| **`gray_counter.v`** | 3-bit binary to Gray-code generator | 3 | **5 cells** | **32.0 GE** | **~64 T** | `XOR2`, `DFFR` |
| **`sar_adc_ctrl.v`** | 4-bit synchronous SAR ADC controller | 8 | **59 cells** | **197.0 GE** | **~394 T** | `MUX2`, `XOR2`, `NOR2`, `AND3`, `DFFR` |
| **`bandgap_trim_fsm.v`**| Comparator-guided bandgap trimmer | 4 | **31 cells** | **104.0 GE** | **~208 T** | `MUX2`, `NOR2`, `DFFR` |
| **`clock_divider_rst.v`**| Configurable 4-bit loadable clock divider | 5 | **85 cells** | **231.0 GE** | **~462 T** | `MUX2`, `NOR3`, `AND4`, `DFFR` |

*Note: 1 Gate Equivalent (GE) = 1 Inverter = 2 Transistors (e.g. INV = 1.0 GE, NAND2/NOR2 = 2.0 GE, AND2/OR2 = 3.0 GE, AOI21/OAI21 = 3.0 GE, AOI22/OAI22 = 4.0 GE, MUX2 = 6.0 GE, DFFR/DFFS = 17.0 GE).*

---

## 🏆 Competitive Optimization Benchmark: Beating the Automation Deck (`PWM_CTRL_relaxed`)

A major real-world benchmark for AMS digital logic synthesis is `PWM_CTRL_relaxed.v` (a multi-mode PWM & Auto-Zero mixed-signal controller). When benchmarked against the reference **Automation Deck**, the AMS Optimizer beats the baseline across both **silicon area (Gate Equivalents)** and **total cell count** while maintaining **100% Formal Logic Equivalence (4,096 / 4,096 vectors)**:

### 1. Benchmark Comparison vs. Automation Deck

| Synthesis Solution | Total Cells | Area (GE) | Transistors | MUX2 | INV | AOI22 | AOI21 | Area Delta vs. Deck | Cell Delta vs. Deck | Formal LEC (4096 Vecs) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Automation Deck Baseline** | 104 | 392.0 GE | 784 T | 0 | 16 | — | — | Baseline | Baseline | 100% PASS |
| **AMS Optimizer: Relaxed (Default Flow)** | **96** | **344.0 GE** | **688 T** | **15** | 34 | 6 | 1 | **-48.0 GE (-12.2%)** | **-8 cells (-7.7%)** | **100% PASS** |
| **AMS Optimizer: Relaxed (Min Cells Winner)** | **88** | **325.0 GE** | **650 T** | **15** | 34 | 6 | 1 | **-67.0 GE (-17.1%)** | **-16 cells (-15.4%)** | **100% PASS** |
| **AMS Optimizer: Relaxed (Min Area Winner / Pure CMOS)** | **113** | **322.0 GE** | **644 T** | **0** | 32 | 6 | 1 | **-70.0 GE (-17.9%)** | +9 cells | **100% PASS** |

---

### 2. Standard Optimization Execution: Automated Sweep Flow (`--auto-sweep`)

The optimizer includes a built-in **Two-Phase Parameter Sweep** that exhaustively explores **48 technology mapping configurations** in ~80 seconds, selects the Pareto-winning netlist, formally verifies it, and directly generates the Cadence Verilog-A model, SKILL schematic script, and BOM report:

- **Phase 1: Rapid Multi-Configuration Synthesis (synthesis-only):** Pre-extracts the circuit DAG and truth tables **once** (2.5s for 23 nodes), then sweeps 48 configurations with node-level memoization. Suboptimal candidates are synthesized in ~70s without redundant verification.
- **Phase 2: Targeted Formal Verification (Winner LEC):** Candidates are Pareto-ranked by Silicon Area (GE) and gate count. Exhaustive **Formal Logic Equivalence Checking (LEC)** is executed across all $2^N$ input combinations **only on the winning candidate(s)** (taking ~6s), mathematically guaranteeing 100% equivalence against golden RTL.

#### Recommended Command to Run Optimization:
```bash
# Automatically sweep 48 configurations, formally verify winner, and save all outputs:
python3 -m ams_optimizer.cli examples/PWM_CTRL_relaxed.v \
  --auto-sweep \
  -o examples/PWM_CTRL_relaxed.va \
  --save-netlist examples/PWM_CTRL_relaxed_netlist.json \
  --save-skill examples/PWM_CTRL_relaxed_schematic.il \
  --save-report examples/PWM_CTRL_relaxed_report.txt \
  --stage-verify
```

#### Running the Automated Sweep via Python API:
```python
from ams_optimizer.core.optimizer import AMSOptimizer

with open("examples/PWM_CTRL_relaxed.v", "r") as f:
    verilog_code = f.read()

# Automatically sweep 48 configurations and formally verify the winner in ~85s
best_result, all_candidates = AMSOptimizer.auto_optimize(
    verilog_code,
    verify_top_n=1,
    verbose=True,
)

print(f"Winner: {best_result.total_inverter_equivalents:.1f} GE, {best_result.total_gates} cells")
print(f"Formal LEC: {'100% PASSED' if best_result.equivalence_result.passed else 'FAILED'}")
print(best_result.bom_report)
```

---

### 3. Single-Pass Targeted Reproduction

To reproduce specific winning architectural trade-offs directly without running the full 48-configuration sweep:

#### Via Command-Line Interface (CLI):
```bash
# 1. Minimum Silicon Area (322.0 GE, 644T, cs019sw-compatible pure CMOS):
python3 ams_optimizer/cli.py examples/PWM_CTRL_relaxed.v \
  --no-and-or --no-mux --qm-max 7 --shannon-min 3 --no-buffers \
  -o examples/PWM_CTRL_relaxed.va

# 2. Minimum Cell Count (88 cells, 325.0 GE, 650T):
python3 ams_optimizer/cli.py examples/PWM_CTRL_relaxed.v \
  --no-and-or --allow-mux --qm-max 7 --shannon-min 3 --no-buffers \
  -o examples/PWM_CTRL_relaxed.va
```

#### Via Python API:
```python
from ams_optimizer.core.optimizer import AMSOptimizer

with open("examples/PWM_CTRL_relaxed.v", "r") as f:
    verilog_code = f.read()

# Synthesize for Minimum Silicon Area (322.0 GE / 644 Transistors, 0 MUX2)
optimizer = AMSOptimizer(
    allow_and_or=False,          # Map purely to inverting CMOS (NAND/NOR/INV)
    allow_mux=False,             # Disallow MUX2 (cs019sw standard cell library)
    qm_max_inputs=7,             # Exact Quine-McCluskey minimization up to 7 inputs
    shannon_min_inputs=3,        # Shannon decomposition threshold
    allow_output_buffers=False,  # Direct wire aliasing for duplicate output ports
    run_verification=True        # 100% formal LEC verification across 4096 vectors
)

result = optimizer.run(verilog_code)
print(f"Total Gates: {result.total_gates} cells")
print(f"Silicon Area: {result.total_inverter_equivalents:.1f} GE ({result.total_transistors} Transistors)")
print(f"Formal LEC Passed: {result.equivalence_result.passed}")
```
optimizer = AMSOptimizer(
    allow_and_or=False,          # Map purely to inverting CMOS (NAND/NOR/INV)
    allow_mux=False,             # Disallow MUX2 (cs019sw standard cell library)
    qm_max_inputs=7,             # Exact Quine-McCluskey minimization up to 7 inputs
    shannon_min_inputs=3,        # Shannon decomposition threshold
    allow_output_buffers=False,  # Direct wire aliasing for duplicate output ports
    run_verification=True        # 100% formal LEC verification across 4096 vectors
)

result = optimizer.run(verilog_code)
print(f"Total Gates: {result.total_gates} cells")
print(f"Silicon Area: {result.total_inverter_equivalents:.1f} GE ({result.total_transistors} Transistors)")
print(f"Formal LEC Passed: {result.equivalence_result.passed}")
```

---

### 5. Key Architectural Innovations Behind the 17.1% Gain

1. **Global Cross-Cone Common Subexpression Elimination (CSE)**:
   A centralized `subexpr_cache` maps commutative gate structures across distinct cones (`oc_ctrl_cp`, `oc_ctrl_bgr`, `pwm_chop_d`), pruning duplicate inverters and redundant cofactors.
2. **Asymmetric Sequential Flop Mapping (`DFFS`)**:
   Flops with non-zero resets (such as `startup` with `reset_val = 1`) directly instantiate preset flip-flops (`DFFS`) instead of clearing flops (`DFFR`) with inverted D/Q wrapper gates, eliminating 2 inverters per instance.
3. **Compound CMOS Cell Technology Mapping (`AOI22`, `OAI22`, `AOI21`, `OAI21`)**:
   4-literal SOP terms $\overline{(A \cdot B) + (C \cdot D)}$ are mapped directly to single-stage 8-transistor `AOI22` cells (4.0 GE) rather than 3 `NAND2` gates (6.0 GE), saving 2.0 GE per cluster.
4. **Cross-Cone Double Inverter Cancellation**:
   Tracks gate ancestry across multi-level DAG cones to eliminate back-to-back inverted nodes (`INV(INV(X)) -> X`).
5. **Direct Output Port Aliasing**:
   Module alias outputs (`oc_select_ext = oc_select`, `oc_ctrl_cp_ext = oc_ctrl_cp`, `en_LP_ext = en_LP`) connect directly to driving nets without requiring 3 extra `BUFFER` gates (saving 6.0 GE).

---

### 6. Architectural Flexibility & Don't-Care Optimization (`PWM_CTRL_flexible.v`)

In mixed-signal controllers, certain internal timing alignments and static mode polarities have non-critical specifications that permit **don't-care logic optimization**. In [`examples/PWM_CTRL_flexible.v`](examples/PWM_CTRL_flexible.v), these relaxations are expressed as synthesizable Verilog `parameter` declarations:

```verilog
parameter RELAX_STATIC_MODES = 0; // 0: Strict 2'b10 static mode, 1: Bit-0 static polarity
parameter RELAX_PWM_SAMPLE   = 0; // 0: Strict 2-cycle window (15 || 0), 1: Single-cycle (0)
parameter RELAX_STARTUP      = 0; // 0: Strict 1-cyc BGR / 2-cyc CP, 1: Unified 2-cyc BGR/CP
```

#### Exhaustive Truth-Table Equivalence Proof (Default Parameters = 0):
To ensure zero functional regressions, the simulator executed an exhaustive **4,096-vector formal simulation** (all 12 state/input variables: 5 primary inputs + 7 register Q bits) across all 15 check signals:

$$\mathbf{4,096 \text{ vectors}} \times \mathbf{15 \text{ signals}} = \mathbf{61,440 \text{ truth-table evaluation points}} \rightarrow \mathbf{0 \text{ mismatches (100.0% PASS)}}$$

| Signal Name | Description | Evaluated Points | Mismatches | Equivalence |
| :--- | :--- | :---: | :---: | :---: |
| `en_LP`, `oc_select`, `oc_ctrl_cp`, `oc_ctrl_bgr`, `en_lowFreq` | Primary Outputs (5) | 20,480 | 0 | **100% MATCH** |
| `oc_select_ext`, `oc_ctrl_cp_ext`, `en_LP_ext` | Output Drivers (3) | 12,288 | 0 | **100% MATCH** |
| `cnt[3:0]_d`, `startup_d`, `chopping_clk_d`, `pwm_chop_d` | Register Next-States (7) | 28,672 | 0 | **100% MATCH** |
| **Total** | **All 15 Monitored Signals** | **61,440** | **0** | **100.0% IDENTICAL** |

#### Physical Timing Verification & Architectural Nuances:
In Cadence Virtuoso simulations, two critical physical constraints were verified:
1. **Startup Auto-Zero Delay (BGR vs. CP)**: `oc_ctrl_bgr` drops to `0` at `cnt=1`, while `oc_ctrl_cp` must remain high through `cnt=1` and drop to `0` at `cnt=2` (exactly 1 cycle later than BGR).
2. **PWM Early Control Wakeup**: Controls must rise at `cnt=15` (at least 1 cycle earlier than `en_LP` drops low at `cnt=0`) to ensure settling before active operation.
3. **Virtuoso Pin Case Matching**: Pins use exact `c_DfT_*` casing (`c_DfT_en_LP`, `c_DfT_en_PWM`, `c_DfT_oc_dig_VDD`) to match Cadence schematic symbol terminals.

#### Corrected Synthesis Results ([`examples/PWM_CTRL_relaxed.v`](examples/PWM_CTRL_relaxed.v)):
With these verified physical constraints implemented:
- **Minimum Silicon Area (Pure CMOS / cs019sw)**: **322.0 GE / 644 Transistors**, 113 cells (**-70.0 GE / -17.9% vs. Automation Deck**).
- **Minimum Standard Cell Count (with MUX2)**: **325.0 GE / 650 Transistors**, **88 cells** (**-16 cells / -15.4% vs. Automation Deck**).
- **Default Flow (with MUX2 & isolated buffers)**: **344.0 GE / 688 Transistors**, 96 cells.
- Fully passes exhaustive Formal Logic Equivalence Checking (LEC) across all 4,096 state vectors and Stage 0–4 matrix verification.

---

## 📐 Verilog Coding Guidelines & Synthesis Nuances for AMS Digital Optimizer

To ensure your Verilog RTL synthesizes smoothly without issues or unintended logic overhead, follow these criteria:

### 1. Clocked vs. Combinational Separation
- **Sequential Storage Elements (Flip-Flops)**:
  Use standard `always @(posedge clk or negedge res_n)` blocks with non-blocking assignments (`<=`).
  ```verilog
  always @(posedge clk_i or negedge res_n) begin
    if (!res_n) begin
      cnt     <= 4'b0000;
      startup <= 1'b1;
    end else begin
      cnt     <= cnt + 4'b0001;
      if (cnt == 4'd15) startup <= 1'b0;
    end
  end
  ```
- **Combinational Logic Cloud**:
  Use `always @(*)` or `assign` statements with blocking assignments (`=`). Ensure all outputs are assigned across every conditional branch to avoid unintended latches.

### 2. Reset Styles & Flop Mapping (`DFFR` vs. `DFFS`)
- The optimizer automatically detects asynchronous active-low reset `if (!res_n)`.
- **Zero Reset (`<= 0`)**: Mapped directly to standard clear flop `DFFR` (17.0 GE).
- **One Reset (`<= 1`)**: Mapped directly to preset flop `DFFS` (17.0 GE). This avoids wrapping a `DFFR` in external inversion gates, saving 2 inverters per instance.

### 3. Exploiting Multi-Level DAG Sharing with Intermediate Wires
- Rather than inlining deep nested logic expressions across multiple `always` blocks, declare intermediate conditions as `wire` and compute them via continuous `assign`:
  ```verilog
  wire is_az_mode   = (eff_oc_mode == 2'b00);
  wire is_chop_mode = (eff_oc_mode == 2'b11);
  ```
- The DAG Slicer extracts these intermediate nets as shared graph nodes. Downstream output cones (`oc_ctrl_cp`, `oc_ctrl_bgr`, `en_lowFreq`) reuse these nodes directly rather than redundantly re-synthesizing them, preventing gate explosion.

### 4. Parameterizing Don't-Cares & Architectural Flexibility
- Standard Verilog `parameter` declarations are fully supported:
  ```verilog
  parameter RELAX_STATIC_MODES = 0;
  parameter RELAX_PWM_SAMPLE   = 0;
  parameter RELAX_STARTUP      = 0;
  ```
- Use ternary operators `? :` to link parameters to optional architectural relaxations. Setting parameters to `0` maintains strict nominal equivalence; setting to `1` activates gate-saving relaxations.

### 5. Power-of-2 Alignment for Timing Windows
- If an analog specification allows flexibility in transition timing:
  - **Avoid Multi-Bit Comparators**: A condition like `(cnt == 4'd15) || (cnt == 4'd0)` requires two 4-input comparators plus an OR gate.
  - **Prefer Power-of-2 / Single-Bit Decodes**: A condition like `(cnt == 4'd0)` simplifies the decoder, and checking `cnt[3]` or `cnt < 4'd2` collapses multiple gates down to a single NOR gate.

### 6. Glitch-Free Analog Outputs (Output Flip-Flops)
- For signals directly controlling sensitive analog switches (capacitive DACs, charge pumps, auto-zero sampling), combinational decoders can produce transient switching glitches when multiple counter bits toggle simultaneously.
- Adding output registers (`output reg sig` or `assign sig = sig_q;`) completely isolates timing and provides glitch-free analog control at the cost of **1 Flip-Flop per bit** (`17.0 GE` / `34 Transistors`).
- The optimizer handles output registers natively: it instantiates the sequential flop in Column 0, connects its `Q` pin directly to the output port, and synthesizes the minimal combinational cone feeding its `D` input.

### 7. Power and Ground Pins for Supply-Aware Verilog-A
- Declare supply and ground pins in the module port list: `inout VDD, VSS;` (or `GND`, `SUB`, `AVDD`, `AVSS`, `DVDD`, `DVSS`).
- The optimizer automatically detects these pins, excludes them from Boolean gate logic, and maps them as dynamic physical supply rails in the generated Verilog-A output drivers:
  ```verilog
  V(out) <+ transition((val > 0.5) ? V(VDD) : V(VSS), tdel, trise, tfall);
  ```
- Primary inputs are differentially referenced against `V(VDD,VSS)*0.5`, enabling multi-supply corner simulation (e.g. 890 mV, 1.2 V, 1.8 V, 3.3 V) without manual model edits.

---

## 🚀 Quick Start CLI

No installation needed. Run directly with Python 3.9+:

```bash
# 1. Standard Execution: Run automated 48-configuration sweep, formally verify, and save all outputs:
python3 -m ams_optimizer.cli examples/PWM_CTRL_relaxed.v \
  --auto-sweep \
  -o examples/PWM_CTRL_relaxed.va \
  --save-netlist examples/PWM_CTRL_relaxed_netlist.json \
  --save-skill examples/PWM_CTRL_relaxed_schematic.il \
  --save-report examples/PWM_CTRL_relaxed_report.txt \
  --stage-verify

# 2. Synthesize SAR ADC Controller
python3 -m ams_optimizer.cli examples/sar_adc_ctrl.v --auto-sweep

# 3. Or install as a local command (optional)
pip install -e .
ams-opt examples/PWM_CTRL_relaxed.v --auto-sweep
```

---

## 🧪 Running Tests

Run the test suite with standard Python (zero pip dependencies):

```bash
python3 -m unittest discover -s tests -v
```

Or using pytest:
```bash
pytest tests/
```

---

## 📂 Repository Structure

```
digitalOptimizer/
├── ams_optimizer/             # Unified Multi-Level DAG Optimizer Package
│   ├── __init__.py
│   ├── cli.py                 # Pure standard library CLI (--auto-sweep, flags)
│   └── core/
│       ├── models.py          # Dataclasses, transistor & inverter equivalent costs
│       ├── dag_slicer.py      # Multi-level RTL slicer & intermediate node extractor
│       ├── reachability.py    # FSM state reachability analyzer (Don't-Cares)
│       ├── truth_table.py     # Local node truth-table evaluator & variable pruner
│       ├── shannon_mux.py     # Shannon decomposition for 6T MUX2 extraction
│       ├── npn_matcher.py     # NPN bitmask matching (AOI21, XOR2, NAND, NOR)
│       ├── quine_mccluskey.py # Pure-Python Quine-McCluskey / Petrick solver
│       ├── tech_mapper.py     # Technology mapping & global inverter sharing
│       ├── netlist_generator.py # Intermediate structural gate netlist & JSON serializer
│       ├── equivalence_checker.py # Formal Logic Equivalence Checking (LEC)
│       ├── stage_verifier.py  # Mid-synthesis stage-by-stage equivalence verifier
│       ├── rtl_simulator.py   # Golden Verilog RTL combinational AST simulator
│       ├── veriloga_emitter.py# Cadence Spectre Verilog-A emitter with GE notes
│       ├── skill_emitter.py   # Cadence Virtuoso SKILL (.il) schematic generator
│       └── optimizer.py       # Master synthesis & two-phase auto-sweep coordinator
├── examples/                  # Benchmark RTL, Verilog-A models & JSON netlists
│   ├── PWM_CTRL_flexible.v    # Synthesizable RTL with configurable don't-care parameters
│   ├── PWM_CTRL_relaxed.v     # Relaxed RTL with verified physical timing constraints
│   ├── PWM_CTRL_relaxed.va    # Winning Cadence Spectre Verilog-A model (322.0 GE)
│   ├── PWM_CTRL_relaxed_netlist.json # Winning structural gate netlist
│   ├── PWM_CTRL_relaxed_schematic.il # Winning Virtuoso SKILL schematic script
│   ├── PWM_CTRL_relaxed_report.txt   # Winning synthesis BOM report
│   ├── gray_counter.v
│   ├── gray_counter_netlist.json
│   ├── gray_counter_schematic.il
│   ├── sar_adc_ctrl.v
│   ├── sar_adc_ctrl_netlist.json
│   ├── sar_adc_ctrl_schematic.il
│   ├── bandgap_trim_fsm.v
│   ├── bandgap_trim_fsm_netlist.json
│   ├── bandgap_trim_fsm_schematic.il
│   ├── clock_divider_rst.v
│   ├── clock_divider_rst_netlist.json
│   └── clock_divider_rst_schematic.il
├── tests/                     # Zero-dependency unit & algorithm tests
│   ├── test_optimizer.py
│   ├── test_algorithms.py
│   ├── test_equivalence.py
│   └── test_stage_verifier.py
├── pyproject.toml
└── README.md
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
