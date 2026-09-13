"""Standard IEEE RTL Combinational & Sequential Extractor using pyverilog & iverilog.

Replaces handwritten regex parsers and custom AST interpreters with the industry-standard
pyverilog AST parser and Icarus Verilog simulation engine. Dynamically handles both:
1. Pure combinational circuits (0 Flip-Flops: decoders, ALUs, multiplexer trees, etc.)
2. Sequential synchronous circuits (N Flip-Flops: FSMs, controllers, counters, etc.)
"""

from __future__ import annotations
import os
import subprocess
import tempfile
from typing import Dict, List, Set, Tuple

from pyverilog.vparser.parser import parse
from pyverilog.vparser.ast import Input, Output, Decl, Reg, Width, NonblockingSubstitution


class UnifiedRTLExtractor:
    """Extracts all combinational outputs and register next-states using pyverilog + iverilog."""

    def __init__(self, verilog_code_or_path: str):
        # Support either raw verilog code string or file path
        if os.path.exists(verilog_code_or_path):
            self.verilog_path = os.path.abspath(verilog_code_or_path)
            self._temp_v = None
        else:
            self._temp_v = tempfile.NamedTemporaryFile(suffix=".v", mode="w", delete=False)
            self._temp_v.write(verilog_code_or_path)
            self._temp_v.flush()
            self.verilog_path = self._temp_v.name

        # 1. Parse AST using standard pyverilog parser
        ast, _ = parse([self.verilog_path])
        module = ast.description.definitions[0]
        self.module_name = module.name

        # 2. Extract Ports & Signals
        self.ports: List[Tuple[str, str, int, int, int]] = []
        self.primary_inputs: List[str] = []
        self.comb_outputs: List[str] = []
        self.clk_name: str | None = None
        self.rst_name: str | None = None

        for port in module.portlist.ports:
            p = port.first
            name = p.name
            direction = "input" if isinstance(p, Input) else "output"
            width = 1
            msb, lsb = 0, 0
            if p.width:
                msb = int(p.width.msb.value)
                lsb = int(p.width.lsb.value)
                width = abs(msb - lsb) + 1
            self.ports.append((name, direction, width, msb, lsb))

            if direction == "input":
                if name in ("clk", "clk_i", "clock"):
                    self.clk_name = name
                    continue
                if name in ("rst", "res_n", "reset", "rst_n"):
                    self.rst_name = name
                    continue
                if name in ("VDD", "VSS", "sub"):
                    continue
                if width > 1:
                    step = 1 if msb >= lsb else -1
                    for b_idx in range(msb, lsb - step, -step):
                        self.primary_inputs.append(f"{name}[{b_idx}]")
                else:
                    self.primary_inputs.append(name)
            else:
                if not name.endswith("_ext"):
                    if width > 1:
                        step = 1 if msb >= lsb else -1
                        for b_idx in range(msb, lsb - step, -step):
                            self.comb_outputs.append(f"{name}[{b_idx}]")
                    else:
                        self.comb_outputs.append(name)

        # 3. Detect Sequential Registers (signals assigned with <=)
        seq_targets = set()

        def find_seq(node):
            if isinstance(node, NonblockingSubstitution):
                seq_targets.add(str(node.left.var))
            for c in node.children():
                find_seq(c)

        find_seq(ast)

        # Determine widths of registers
        reg_widths: Dict[str, int] = {name: width for name, _, width, _, _ in self.ports}
        for item in module.items:
            if isinstance(item, Decl):
                for d in item.list:
                    if isinstance(d, Reg) and d.name in seq_targets:
                        if d.width:
                            msb = int(d.width.msb.value)
                            lsb = int(d.width.lsb.value)
                            reg_widths[d.name] = abs(msb - lsb) + 1
                        else:
                            reg_widths[d.name] = 1

        ordered_seq_targets = []
        for item in module.items:
            if isinstance(item, Decl):
                for d in item.list:
                    if isinstance(d, Reg) and d.name in seq_targets and d.name not in ordered_seq_targets:
                        ordered_seq_targets.append(d.name)
        for r in sorted(seq_targets):
            if r not in ordered_seq_targets:
                ordered_seq_targets.append(r)

        self.register_bits: List[str] = []
        self.reg_definitions: List[Tuple[str, int]] = []
        for r in ordered_seq_targets:
            w = reg_widths.get(r, 1)
            self.reg_definitions.append((r, w))
            if w > 1:
                for b_idx in range(w - 1, -1, -1):
                    self.register_bits.append(f"{r}[{b_idx}]")
            else:
                self.register_bits.append(r)

        # Remove registered outputs from comb_outputs (driven directly by their DFFs)
        self.comb_outputs = [o for o in self.comb_outputs if o.split("[")[0] not in seq_targets]

        self.inputs = self.primary_inputs + self.register_bits
        self.num_inputs = len(self.inputs)
        self.total_ffs = len(self.register_bits)

        # Register D-inputs
        self.d_targets = [f"{b}_d" for b in self.register_bits]
        self.comb_targets = self.comb_outputs + self.d_targets

    def extract_truth_tables(self, dc_relaxation: str = "exact") -> Dict[str, str]:
        """Simulates all 2^K vectors with iverilog in <0.1s to extract exact truth tables."""
        num_rows = 1 << self.num_inputs
        with tempfile.TemporaryDirectory() as tmpdir:
            tb_path = os.path.join(tmpdir, "extract_tb.v")
            vvp_path = os.path.join(tmpdir, "extract_tb.vvp")
            out_path = os.path.join(tmpdir, "tb_out.txt")

            # Dynamically construct testbench matching exact module interface
            tb_lines = ["`timescale 1ns/1ps", "module tb;"]

            # Declare signals
            for name, direction, width, msb, lsb in self.ports:
                w_str = f"[{msb}:{lsb}] " if width > 1 else ""
                if direction == "input":
                    tb_lines.append(f"  reg {w_str}{name};")
                else:
                    tb_lines.append(f"  wire {w_str}{name};")

            # Combinational sample registers
            for tgt in self.comb_outputs:
                clean_tgt = tgt.replace("[", "_").replace("]", "")
                tb_lines.append(f"  reg s_{clean_tgt};")

            # Instantiate DUT
            tb_lines.append(f"\n  {self.module_name} dut (")
            conn_lines = [f"    .{name}({name})" for name, _, _, _, _ in self.ports]
            tb_lines.append(",\n".join(conn_lines))
            tb_lines.append("  );\n")

            # Test loop
            tb_lines.append(f"  integer i;")
            tb_lines.append(f"  reg [{self.num_inputs-1}:0] vec;")
            tb_lines.append(f"  integer fd;\n")
            tb_lines.append("  initial begin")
            tb_lines.append(f'    fd = $fopen("{out_path}", "w");')

            # Initialize power, clock, reset
            for name, direction, _, _, _ in self.ports:
                if direction == "input":
                    if name in ("clk", "clk_i", "clock"):
                        tb_lines.append(f"    {name} = 0;")
                    elif name in ("res_n", "rst_n"):
                        tb_lines.append(f"    {name} = 1;")
                    elif name in ("rst", "reset"):
                        tb_lines.append(f"    {name} = 0;")
                    elif name == "VDD":
                        tb_lines.append(f"    VDD = 1'b1;")
                    elif name in ("VSS", "sub"):
                        tb_lines.append(f"    {name} = 1'b0;")

            tb_lines.append(f"    for (i = 0; i < {num_rows}; i = i + 1) begin")
            tb_lines.append(f"      vec = i[{self.num_inputs-1}:0];")

            # Apply vector to inputs
            for bit_i, inp_name in enumerate(self.inputs):
                if inp_name in self.primary_inputs:
                    tb_lines.append(f"      {inp_name} = vec[{bit_i}];")
                else:
                    tb_lines.append(f"      dut.{inp_name} = vec[{bit_i}];")

            tb_lines.append("      #1;")
            # Sample combinational outputs
            for tgt in self.comb_outputs:
                clean_tgt = tgt.replace("[", "_").replace("]", "")
                tb_lines.append(f"      s_{clean_tgt} = {tgt};")

            # If sequential, pulse clock and sample next state
            if self.total_ffs > 0 and self.clk_name:
                tb_lines.append(f"      {self.clk_name} = 1; #1; {self.clk_name} = 0; #1;")

            # Format string to display
            fmt_spec = "%b" * len(self.comb_targets)
            sample_args = []
            for tgt in self.comb_outputs:
                clean_tgt = tgt.replace("[", "_").replace("]", "")
                sample_args.append(f"s_{clean_tgt}")
            for reg_bit in self.register_bits:
                sample_args.append(f"dut.{reg_bit}")

            tb_lines.append(f'      $fdisplay(fd, "{fmt_spec}", {", ".join(sample_args)});')
            tb_lines.append("    end")
            tb_lines.append("    $fclose(fd);")
            tb_lines.append("    $finish;")
            tb_lines.append("  end")
            tb_lines.append("endmodule")

            with open(tb_path, "w") as f:
                f.write("\n".join(tb_lines))

            # Invoke iverilog compiler and runtime
            subprocess.run(
                ["/opt/homebrew/bin/iverilog", "-o", vvp_path, tb_path, self.verilog_path],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["/opt/homebrew/bin/vvp", vvp_path],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            with open(out_path) as f:
                lines = [line.strip() for line in f if line.strip()]

        table_strings: Dict[str, str] = {}
        for col, tgt in enumerate(self.comb_targets):
            raw_bits = list("".join(line[col] for line in lines))

            # Optional Don't-Care relaxation for startup states in stateful designs
            # CRITICAL: Never relax next-state D-targets (self.d_targets), so state transitions
            # (such as startup clearing at cnt==15 and steady-state counter/BGR next-states)
            # are preserved with 100% formal accuracy. Also protect en_lowFreq and oc_ctrl_cp
            # so that the 2-cycle fast clock window and 1-cycle CP-longer-than-BGR timing are preserved.
            if dc_relaxation == "startup_relaxed" and tgt not in self.d_targets and tgt not in ("en_lowFreq", "oc_ctrl_cp") and "startup" in self.inputs and any("cnt" in inp for inp in self.inputs):
                startup_idx = self.inputs.index("startup")
                cnt_indices = [idx for idx, inp in enumerate(self.inputs) if "cnt[" in inp]
                for row_i in range(num_rows):
                    startup_val = (row_i >> startup_idx) & 1
                    cnt_val = 0
                    for c_bit, c_idx in enumerate(reversed(cnt_indices)):
                        cnt_val |= (((row_i >> c_idx) & 1) << c_bit)
                    if startup_val == 1 and cnt_val > 1:
                        raw_bits[row_i] = "-"

            table_strings[tgt] = "".join(raw_bits)

        return table_strings

    def __del__(self):
        if hasattr(self, "_temp_v") and self._temp_v:
            try:
                os.remove(self._temp_v.name)
            except Exception:
                pass
