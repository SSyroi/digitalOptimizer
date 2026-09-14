# Project Rules: Digital Optimizer & Synthesis

## 0. Single-Command Execution Rule for AI Agents
- **Execute Exactly ONE Command**: To optimize any Verilog file, run:
  ```bash
  ./optimize <path_to_verilog>
  # or: python3 -m espresso_mv_optimizer.cli <path_to_verilog>
  ```
- **Zero Exploratory Overhead**:
  - Do NOT run intermediate AST checks, unit tests, `git diff`, `git status`, or file explorations unless specifically asked by the user to debug or edit code.
  - All Cadence deliverables (`.va`, `_netlist.v`, `_quick_proto.md`) are automatically generated alongside the input file by default.
- **Output Immediately**: Directly present the mandatory Top 10 Pareto Table and Rank 1 Bill of Materials (BOM) in the response.

## 1. Always Present the Full Optimization Pareto Table
Whenever running the logic optimizer, benchmarking, or executing `--auto-sweep`:
- **MANDATORY**: Always print the **Full Pareto Results Table** containing the top candidate configurations (Rank 1 through 10) directly in the response to the user.
- **Include All Swept Parameters & Metrics**:
  - `Rank`
  - `GE` (Inverter Equivalents)
  - `Transistors` (Estimated total transistor count)
  - `Cells` (Total standard cell count)
  - `MUX` (Shannon MUX2 mapping enabled: True/False)
  - `AND/OR` (Direct AND/OR gate mapping: True/False)
  - `QM` (Quine-McCluskey threshold)
  - `SH` (Shannon decomposition threshold)
  - `BUF` (Buffer insertion enabled: True/False)
  - `LEC` (Formal Logic Equivalence Check status)
- **NEVER** present only a single winning result. The user must always see the complete exploration landscape to evaluate silicon area vs. gate count vs. technology mapping trade-offs.
- Only *after* displaying the full Pareto table should you display the detailed Bill of Materials (BOM) breakdown for the chosen winner.

## 2. PWM & Chopping Timing Rules
- In PWM mode (`c_DfT_en_PWM = 1`), the active window is `en_LP = 0` for 2 cycles (`cnt = 0` and `cnt = 1`).
- In PWM Chopping mode, control signals (`oc_ctrl_bgr`, `oc_ctrl_cp`) must swap polarity **at the middle of the LP=0 gap** (`cnt == 0 -> 1`), NOT at the falling edge of `en_LP` (`cnt == 15 -> 0`).
- Ensure registered control signals trigger their PWM chopping toggle at `if (cnt == 4'd0)` so that the registered output changes at the posedge entering `cnt = 1`.
