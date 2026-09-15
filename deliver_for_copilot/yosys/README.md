# Ultra-Lightweight Offline Yosys & ABC via YoWASP (`yowasp-yosys`)

This directory contains pre-packaged, offline-installable Python wheels for **Yosys 0.69** and **Berkeley ABC** compiled to WebAssembly (WASI) via **[YoWASP](https://yowasp.org/)**.

---

## 1. Executive Summary & Why This Approach

Semiconductor compute farms (e.g., RHEL 8/9, CentOS, or custom enterprise Linux) impose strict security constraints:
* **Zero external network access** (air-gapped or proxy-restricted nodes).
* **Zero root / sudo permissions** (users cannot run `yum`, `apt`, `dpkg`, or `rpm`).
* **FUSE (`/dev/fuse`) disabled** (AppImages fail to mount on cluster compute nodes).
* **Strict disk quotas** (multi-gigabyte toolchains like the 1.5+ GB OSS CAD Suite are impractical to transfer and commit).

**YoWASP Yosys** completely bypasses these bottlenecks:
1. **Ultra-Compact Footprint**: The entire synthesis suite (Yosys + full Berkeley ABC) is **~25.7 MB** total for Linux x86_64, well under GitHub's 100 MB per-file limit.
2. **Zero Admin Rights**: Installs purely into user space via standard `pip --user`.
3. **Zero Host Library Dependencies**: No `libffi`, `tcl`, `boost`, or `readline` system library hell. The entire C++ logic synthesis engine runs inside the WebAssembly sandbox via `wasmtime`.
4. **Offline Installation**: Fully vendored with `--no-index --find-links`.

---

## 2. How It Works Under the Hood

```
+-------------------------------------------------------------------------------+
| Python User Environment (CLI or Script)                                       |
|   `yowasp-yosys -p "read_verilog in.v; synth; abc; write_verilog out.v"`      |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
| yowasp-runtime & wasmtime Engine (JIT Execution)                              |
|   - Maps host directories to WASI sandbox                                     |
|   - Translates POSIX file I/O, stdin, stdout, stderr                          |
|   - Requires ONLY standard host libc.so.6 (glibc >= 2.28, RHEL 8/9 compatible) |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
| yosys.wasm (WebAssembly Bytecode Module, ~66 MB uncompressed, ~15.6 MB in .whl)|
|   - Full Yosys Core (AST parser, elaboration, coarse-grain optimization)      |
|   - Embedded Berkeley ABC Engine (AIG rewriting, technology mapping, LUTs)    |
|   - Built-in Standard Cell / FPGA architecture libraries                      |
+-------------------------------------------------------------------------------+
```

* **WASI (WebAssembly System Interface)**: When you pass `-p "read_verilog input.v; write_verilog output.v"`, the YoWASP runtime automatically grants pre-opened filesystem access to the working directory. File reads and writes happen seamlessly against real host files.
* **Berkeley ABC Integration**: ABC is compiled directly into the `yosys.wasm` binary. Commands like `abc -g AND,OR,NOT`, `abc -lut 4`, or `abc -liberty my_cells.lib` execute in-process without requiring a secondary `berkeley-abc` executable on `$PATH`.
* **Execution Performance**: Because `wasmtime` compiles WASM to native machine code using Cranelift JIT, execution performance reaches ~50–80% of native C++ speed. For controller modules and typical logic blocks (<10,000 gates), synthesis finishes in fractions of a second.

---

## 3. How Yosys Complements the Unified Logic Optimizer

In this repository (`digitalOptimizer`), we currently rely on **Berkeley Espresso-MV** (`pyeda` / C extension) for exact two-level logic minimization and Shannon MUX decomposition.

Adding **Yosys + ABC** opens up powerful capabilities for Copilot and future optimization workflows:

| Feature | Espresso-MV Engine | Yosys + ABC Engine |
| :--- | :--- | :--- |
| **Logic Domain** | Two-level SOP / ESOP minimization | Multi-level DAG / AIG logic restructuring |
| **Multi-Valued Inputs** | Native multi-valued variable encoding | Synthesizes to binary one-hot / binary state nets |
| **Technology Mapping** | Direct Shannon MUX2 / AND-OR mapping | Standard Cell Library mapping (`.lib` / Liberty format) |
| **FPGA / ASIC Target** | Cadence AMS / Behavioral Verilog-A | Any ASIC standard cell library, SkyWater 130nm, or LUTs |
| **Cross-Verification** | LEC equivalence checking | Formal verification (`sat`, `miter`, `equiv_make`) |

### Proposed Synergy:
1. **Frontend**: Espresso-MV produces minimized two-level SOP logic for complex multi-condition analog control words.
2. **Backend**: Yosys + ABC takes the generated structural Verilog netlist, performs multi-level technology mapping against standard cell libraries (e.g. Inverter, NAND2, NOR2, MUX2), and calculates exact Silicon Gate Equivalents (GE) and cell count trade-offs.

---

## 4. Quickstart / Offline Installation Guide

### Step 1: Install Offline
Run this single command on the offline UNIX machine:
```bash
python3 -m pip install --no-index --find-links=deliver_for_copilot/yosys --user yowasp-yosys
```
*(No internet access, no root, and no external compiler needed).*

### Step 2: Verify Installation
```bash
yowasp-yosys -V
# Expected output:
# Yosys 0.69 (git sha1 ..., clang/wasm32 ...)
```

### Step 3: Run Synthesis (CLI Example)
```bash
yowasp-yosys -p "read_verilog input.v; synth -top my_module; abc -g AND,OR,NOT; write_verilog output_syn.v"
```

### Step 4: Run Synthesis from Python
```python
import subprocess

def run_yosys_synthesis(input_verilog, top_module, output_verilog):
    script = (
        f"read_verilog {input_verilog}; "
        f"synth -top {top_module}; "
        f"abc -g AND,OR,NOT; "
        f"write_verilog -noattr {output_verilog};"
    )
    subprocess.run(["yowasp-yosys", "-p", script], check=True)

# Example call:
run_yosys_synthesis("examples/controller.v", "controller", "examples/controller_yosys.v")
```

---

## 5. Included Wheels & Checksums

| Package | Filename | Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| **YoWASP Yosys** | `yowasp_yosys-0.69.0.0.post1233-py3-none-any.whl` | 15.6 MB | `59284760d6455b764fce5dcf296d2c183b05dc980f59092461deddc9caa09bdd` |
| **Wasmtime (Linux)** | `wasmtime-47.0.1-py3-none-manylinux1_x86_64.whl` | 10.0 MB | `9724600b036c6e95c4fe952e29fad83b4f02bdc11d23f25c4ee3ffff2c1d7257` |
| **Wasmtime (macOS)** | `wasmtime-47.0.1-py3-none-macosx_11_0_arm64.whl` | 8.5 MB | `58da69f71750e844e32614c1805246ffca4c8b032d46a8145faa26c228c6c5ac` |
| **YoWASP Runtime** | `yowasp_runtime-1.96-py3-none-any.whl` | 5.2 KB | `4ff456a4a6dff9d689c7feac9f68fb1492bed4cf873450d7b41259fa31645783` |
| **Click** | `click-8.1.8-py3-none-any.whl` | 98 KB | `63c132bbbed01578a06712a2d1f497bb62d9c1c0d329b7903a866228027263b2` |
| **PlatformDirs** | `platformdirs-4.4.0-py3-none-any.whl` | 18 KB | `abd01743f24e5287cd7a5db3752faf1a2d65353f38ec26d98e25a6db65958c85` |

Integrity check command:
```bash
cd deliver_for_copilot/yosys
sha256sum -c SHA256SUMS.txt
```
