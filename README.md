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
  - **Cadence Spectre Verilog-A (`.va`)**: Continuous analog voltage contributions (`V(out) <+ transition(...)`), `@(initial_step)` reset, `@(cross(V(clk)-vth, +1))` clock sampling, and **detailed Inverter Equivalents (GE)** header notes.
  - **Structural Gate Netlist (`.json`)**: Intermediate gate-level netlist capturing all standard cell instances, topological levels, and pin-to-pin connections for future schematic mapping.
  - **Cadence Virtuoso SKILL (`.il`)**: Automated schematic generator placing standard cells in dependency rank columns.
  - **Schematic Bill of Materials (BOM) Report (`.md` / `.txt`)**.

---

## 📊 Benchmark Results

| Circuit | Description | Regs | Total Gates | Inverter Eq. (GE) | Est. Transistors | Key Gates Mapped |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **`PWM_CTRL.v`** | Multi-mode PWM & Auto-Zero controller | 4 | **42 cells** | **128.0 GE** | **~256 T** | `MUX2`, `NOR2`, `AND2`, `OR3`, `DFFR` |
| **`gray_counter.v`** | 3-bit binary to Gray-code generator | 3 | **5 cells** | **32.0 GE** | **~64 T** | `XOR2`, `DFFR` |
| **`sar_adc_ctrl.v`** | 4-bit synchronous SAR ADC controller | 8 | **59 cells** | **197.0 GE** | **~394 T** | `MUX2`, `XOR2`, `NOR2`, `AND3`, `DFFR` |
| **`bandgap_trim_fsm.v`**| Comparator-guided bandgap trimmer | 4 | **31 cells** | **104.0 GE** | **~208 T** | `MUX2`, `NOR2`, `DFFR` |
| **`clock_divider_rst.v`**| Configurable 4-bit loadable clock divider | 5 | **85 cells** | **231.0 GE** | **~462 T** | `MUX2`, `NOR3`, `AND4`, `DFFR` |

*Note: 1 Gate Equivalent (GE) = 1 Inverter = 2 Transistors (e.g. NAND2 = 2.0 GE, AND2 = 3.0 GE, MUX2 = 3.0 GE, DFFR = 8.0 GE).*

---

## 🚀 Quick Start CLI

No installation needed. Run directly with Python 3.9+:

```bash
# 1. Synthesize PWM_CTRL to Verilog-A, Structural Netlist JSON, and Virtuoso SKILL
python3 ams_optimizer/cli.py examples/PWM_CTRL.v \
  -o examples/PWM_CTRL_va.va \
  --save-netlist examples/PWM_CTRL_netlist.json \
  --save-skill examples/PWM_CTRL_schematic.il \
  --save-report examples/PWM_CTRL_report.txt \
  --vdd 1.8 \
  --vth 0.9

# 2. Synthesize SAR ADC Controller
python3 ams_optimizer/cli.py examples/sar_adc_ctrl.v \
  -o examples/sar_adc_ctrl_va.va \
  --save-netlist examples/sar_adc_ctrl_netlist.json

# 3. Or install as a local command (optional)
pip install -e .
ams-opt examples/gray_counter.v -o examples/gray_counter_va.va
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
│   ├── cli.py                 # Pure standard library CLI
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
│       ├── veriloga_emitter.py# Cadence Spectre Verilog-A emitter with GE notes
│       ├── skill_emitter.py   # Cadence Virtuoso SKILL (.il) schematic generator
│       └── optimizer.py       # Master synthesis coordinator
├── examples/                  # Benchmark RTL, Verilog-A models & JSON netlists
│   ├── PWM_CTRL.v
│   ├── PWM_CTRL_va.va
│   ├── PWM_CTRL_netlist.json
│   ├── gray_counter.v
│   ├── gray_counter_va.va
│   ├── gray_counter_netlist.json
│   ├── sar_adc_ctrl.v
│   ├── sar_adc_ctrl_va.va
│   ├── sar_adc_ctrl_netlist.json
│   ├── bandgap_trim_fsm.v
│   ├── bandgap_trim_fsm_va.va
│   ├── bandgap_trim_fsm_netlist.json
│   ├── clock_divider_rst.v
│   ├── clock_divider_rst_va.va
│   └── clock_divider_rst_netlist.json
├── tests/                     # Zero-dependency unit & algorithm tests
│   ├── test_optimizer.py
│   └── test_algorithms.py
├── pyproject.toml
└── README.md
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
