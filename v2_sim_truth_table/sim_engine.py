"""Exhaustive Combinational Simulation Engine for Truth Table Generation.

Linear tokenizer-based Verilog-to-Python compiler for exhaustive simulation.
Compatible with Python 3.9+.
"""

from __future__ import annotations
import itertools
import os
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple

from .slicer import SlicedModule, SlicedPort, SlicedRegister


@dataclass
class TruthTable:
    input_names: List[str]
    output_names: List[str]
    num_inputs: int
    num_patterns: int
    true_minterms: Dict[str, List[int]] = field(default_factory=dict)
    dont_cares: Dict[str, List[int]] = field(default_factory=dict)


class SimulationEngine:
    """Executes exhaustive simulation to build exact truth tables."""

    def __init__(self, sliced_module: SlicedModule, verilog_code: str):
        self.mod = sliced_module
        self.raw_code = self._strip_comments(verilog_code)

    def _strip_comments(self, code: str) -> str:
        code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
        code = re.sub(r"//.*", "", code)
        return code

    def generate_truth_table(self) -> TruthTable:
        ppi_names = self.mod.get_all_ppi_names()
        ppo_names = self.mod.get_all_ppo_names()
        eval_fn = self._build_python_evaluator(ppi_names, ppo_names)

        true_minterms: Dict[str, List[int]] = {out: [] for out in ppo_names}
        num_inputs = len(ppi_names)

        # Loop through all 2^N combinations
        for m in range(1 << num_inputs):
            env = {}
            for i, iname in enumerate(ppi_names):
                bit_val = (m >> i) & 1
                env[iname] = bit_val

            out_vals = eval_fn(env)
            for out_name in ppo_names:
                if out_vals.get(out_name, 0) == 1:
                    true_minterms[out_name].append(m)

        return TruthTable(
            input_names=ppi_names,
            output_names=ppo_names,
            num_inputs=num_inputs,
            num_patterns=1 << num_inputs,
            true_minterms=true_minterms,
            dont_cares={out: [] for out in ppo_names},
        )

    def _build_python_evaluator(self, ppi_names: List[str], ppo_names: List[str]) -> Callable[[Dict[str, int]], Dict[str, int]]:
        code_lines: List[str] = []
        code_lines.append("def evaluate(env):")
        code_lines.append("    # Primary inputs & Register Present States")
        for iname in ppi_names:
            var_name = self._py_var_name(iname)
            code_lines.append(f"    {var_name} = env.get('{iname}', 0)")

        # Reconstruct vector words from bits
        vectors_seen = set()
        for iname in ppi_names:
            if "[" in iname:
                base = iname.split("[")[0]
                vectors_seen.add(base)

        for vec in sorted(vectors_seen):
            bit_vars = [iname for iname in ppi_names if iname.startswith(f"{vec}[")]
            bit_vars.sort(key=lambda x: int(x.split("[")[1].split("]")[0]))
            expr_parts = [f"({self._py_var_name(b)} << {idx})" for idx, b in enumerate(bit_vars)]
            code_lines.append(f"    {vec} = ({' | '.join(expr_parts)}) if ({' | '.join(expr_parts)}) else 0")

        # Initialize all register D-inputs to their present state (Q) - default retention
        for r in self.mod.registers:
            py_r = self._py_var_name(r.name)
            py_d = self._py_var_name(f"{r.name}_d")
            code_lines.append(f"    {py_d} = {py_r}")

        # Initialize all primary outputs to 0
        for p in self.mod.primary_outputs:
            for bit in p.get_bits():
                code_lines.append(f"    {self._py_var_name(bit)} = 0")

        # Extract continuous assignments
        for match in re.finditer(r"\bassign\s+([a-zA-Z0-9_\[\]]+)\s*=\s*([^;]+);", self.raw_code):
            target, expr = match.groups()
            target_clean = target.strip()
            expr_clean = expr.strip()
            py_target = self._py_var_name(target_clean)
            py_expr = self._convert_expr_to_py(expr_clean)
            code_lines.append(f"    {py_target} = {py_expr}")

            # If target was a vector e.g. assign count_bin = q;
            matching_port = next((p for p in self.mod.primary_outputs if p.name == target_clean and p.is_vector), None)
            if matching_port:
                for bidx in range(matching_port.width):
                    bit_name = f"{target_clean}[{bidx}]"
                    py_bname = self._py_var_name(bit_name)
                    code_lines.append(f"    {py_bname} = ({py_target} >> {bidx}) & 1")

        # Extract sequential blocks (non-reset branch)
        seq_pattern = re.compile(r"always\s*@\s*\(\s*(?:posedge|negedge).*?\)\s*(?:begin)?(.*?)(?=\balways\b|\bendmodule\b|\Z)", re.DOTALL)
        for match in seq_pattern.finditer(self.raw_code):
            body = match.group(1).strip()
            rst_m = re.search(r"if\s*\(\s*!?\s*[a-zA-Z_0-9]+\s*\)\s*(?:begin)?(.*?)\bend\s*else\s*(?:begin)?(.*)", body, re.DOTALL)
            active_body = rst_m.group(2) if rst_m else body
            self._parse_verilog_statements(active_body, code_lines, is_sequential=True, indent=4)

        # Extract combinational procedural blocks
        comb_pattern = re.compile(r"always\s*@\s*(?:\*\s*|\(\s*\*\s*\)|\((?!(?:posedge|negedge)\b).*?\))\s*(?:begin)?(.*?)(?=\balways\b|\bendmodule\b|\Z)", re.DOTALL)
        for match in comb_pattern.finditer(self.raw_code):
            body = match.group(1).strip()
            self._parse_verilog_statements(body, code_lines, is_sequential=False, indent=4)

        code_lines.append("    res = {}")
        for oname in ppo_names:
            py_out = self._py_var_name(oname)
            code_lines.append(f"    res['{oname}'] = 1 if {py_out} else 0")
        code_lines.append("    return res")

        full_code = "\n".join(code_lines)
        local_scope = {}
        exec(full_code, {}, local_scope)
        return local_scope["evaluate"]

    def _parse_verilog_statements(self, code: str, out_lines: List[str], is_sequential: bool, indent: int):
        pad = " " * indent
        i = 0
        code = code.strip()
        while i < len(code):
            while i < len(code) and code[i].isspace():
                i += 1
            if i >= len(code):
                break

            cur = code[i:]

            # Case statement
            if cur.startswith("case"):
                m_case = re.match(r"case\s*\(\s*([a-zA-Z0-9_\[\]]+)\s*\)", cur)
                if m_case:
                    sel_expr = self._convert_expr_to_py(m_case.group(1).strip())
                    i += m_case.end()
                    endcase_pos = code.find("endcase", i)
                    case_body = code[i:endcase_pos] if endcase_pos != -1 else code[i:]
                    i = endcase_pos + 7 if endcase_pos != -1 else len(code)
                    self._parse_case_body(sel_expr, case_body, out_lines, is_sequential, indent)
                    continue

            # If statement
            if cur.startswith("if"):
                m_if = re.match(r"if\s*\((.*?)\)", cur)
                if m_if:
                    cond_str = m_if.group(1).strip()
                    py_cond = self._convert_expr_to_py(cond_str)
                    i += m_if.end()
                    then_body, adv_then = self._extract_block(code[i:])
                    i += adv_then
                    out_lines.append(f"{pad}if ({py_cond}):")
                    self._parse_verilog_statements(then_body, out_lines, is_sequential, indent + 4)

                    rest_after = code[i:].lstrip()
                    if rest_after.startswith("else"):
                        else_offset = len(code[i:]) - len(rest_after) + 4
                        else_body, adv_else = self._extract_block(rest_after[4:])
                        i += else_offset + adv_else
                        out_lines.append(f"{pad}else:")
                        self._parse_verilog_statements(else_body, out_lines, is_sequential, indent + 4)
                    continue

            # Assignment statement
            m_assign = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*(?:\[\d+\])?)\s*(?:<=|=)\s*([^;]+);", cur)
            if m_assign:
                target, rhs = m_assign.groups()
                i += m_assign.end()
                target_clean = target.strip()
                rhs_clean = rhs.strip()
                py_rhs = self._convert_expr_to_py(rhs_clean)

                if is_sequential:
                    if "[" in target_clean:
                        py_target = self._py_var_name(f"{target_clean}_d")
                        out_lines.append(f"{pad}{py_target} = {py_rhs}")
                    else:
                        # Target is a vector register e.g. q <= q + 1;
                        py_temp = f"_tmp_{self._py_var_name(target_clean)}"
                        out_lines.append(f"{pad}{py_temp} = {py_rhs}")
                        # Find all bits for this register
                        reg_bits = [r for r in self.mod.registers if r.base_name == target_clean]
                        for r in reg_bits:
                            bidx = r.bit_idx if r.bit_idx is not None else 0
                            py_d = self._py_var_name(f"{r.name}_d")
                            out_lines.append(f"{pad}{py_d} = ({py_temp} >> {bidx}) & 1")
                else:
                    py_target = self._py_var_name(target_clean)
                    out_lines.append(f"{pad}{py_target} = {py_rhs}")
                continue

            i += 1

    def _extract_block(self, code_slice: str) -> Tuple[str, int]:
        s = code_slice.lstrip()
        offset = len(code_slice) - len(s)
        if s.startswith("begin"):
            depth = 1
            i = 5
            start = 5
            while i < len(s):
                m = re.search(r"\b(begin|end)\b", s[i:])
                if not m:
                    return s[start:], len(code_slice)
                w = m.group(1)
                i += m.end()
                if w == "begin":
                    depth += 1
                elif w == "end":
                    depth -= 1
                    if depth <= 0:
                        return s[start:i-3], offset + i
        else:
            m = re.search(r";", s)
            if m:
                return s[:m.end()], offset + m.end()
            return s, len(code_slice)

    def _parse_case_body(self, sel_expr: str, case_body: str, out_lines: List[str], is_sequential: bool, indent: int):
        pad = " " * indent
        first = True
        branch_pattern = re.compile(r"(\d+\x27[bBdDhH][0-9a-fA-F]+|\d+|default|[a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(?:begin)?(.*?)(?=\s*(?:\d+\x27[bBdDhH][0-9a-fA-F]+|\d+|default|[a-zA-Z_][a-zA-Z0-9_]*)\s*:|\Z)", re.DOTALL)
        for bm in branch_pattern.finditer(case_body):
            vstr, bbody = bm.groups()
            vstr = vstr.strip()
            if vstr == "default":
                out_lines.append(f"{pad}else:")
                self._parse_verilog_statements(bbody, out_lines, is_sequential, indent + 4)
            else:
                val_num = self._parse_num(vstr)
                cond_hdr = f"if ({sel_expr} == {val_num}):" if first else f"elif ({sel_expr} == {val_num}):"
                first = False
                out_lines.append(f"{pad}{cond_hdr}")
                self._parse_verilog_statements(bbody, out_lines, is_sequential, indent + 4)

    def _convert_expr_to_py(self, expr: str) -> str:
        s = expr.strip()
        # Parse numeric constants: 4'b1000 -> 8, 3'd4 -> 4
        s = re.sub(r"(\d+)\x27[bB]([01]+)", lambda m: str(int(m.group(2), 2)), s)
        s = re.sub(r"(\d+)\x27[dD](\d+)", lambda m: str(int(m.group(2), 10)), s)
        s = re.sub(r"(\d+)\x27[hH]([0-9a-fA-F]+)", lambda m: str(int(m.group(2), 16)), s)
        # Operators
        s = re.sub(r"===", "==", s)
        s = re.sub(r"!==|!=", "!=", s)
        s = re.sub(r"&&", " and ", s)
        s = re.sub(r"\|\|", " or ", s)
        s = re.sub(r"!", " not ", s)
        s = re.sub(r"~", " not ", s)
        # Bracketed indices like state[0] -> state_0
        s = re.sub(r"([a-zA-Z_][a-zA-Z0-9_]*)\[(\d+)\]", r"\1_\2", s)
        return s

    def _py_var_name(self, name: str) -> str:
        return re.sub(r"[\[\]]", "_", name).strip("_")

    def _parse_num(self, lit: str) -> int:
        lit = lit.strip()
        if "'b" in lit or "'B" in lit:
            return int(lit.split("'b")[-1].split("'B")[-1], 2)
        elif "'h" in lit or "'H" in lit:
            return int(lit.split("'h")[-1].split("'H")[-1], 16)
        elif "'d" in lit or "'D" in lit:
            return int(lit.split("'d")[-1].split("'D")[-1], 10)
        elif lit.isdigit():
            return int(lit)
        return 0
