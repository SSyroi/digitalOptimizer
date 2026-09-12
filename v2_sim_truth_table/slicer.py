"""Verilog RTL Slicer for Simulation-Driven Truth Table Synthesis.

Separates sequential registers (Flip-Flops) from combinational logic.
Creates:
- Pseudo-Primary Inputs (PPI): Primary Inputs (X) + Present State Register Outputs (Q)
- Pseudo-Primary Outputs (PPO): Primary Outputs (Y) + Next State Register Inputs (D)
Compatible with Python 3.9+.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class SlicedPort:
    name: str
    direction: str  # "input" | "output"
    width: int = 1
    msb: int = 0
    lsb: int = 0
    is_vector: bool = False

    def get_bits(self) -> List[str]:
        if not self.is_vector:
            return [self.name]
        low = min(self.msb, self.lsb)
        high = max(self.msb, self.lsb)
        return [f"{self.name}[{i}]" for i in range(low, high + 1)]


@dataclass
class SlicedRegister:
    name: str  # e.g. "state[0]" or "cnt[3]"
    base_name: str  # e.g. "state" or "cnt"
    bit_idx: Optional[int] = None
    clk_signal: str = "clk"
    rst_signal: Optional[str] = None
    rst_active_low: bool = True
    rst_val: int = 0


@dataclass
class SlicedModule:
    module_name: str
    clk_port: str = "clk"
    rst_port: Optional[str] = "rst_n"
    rst_active_low: bool = True
    primary_inputs: List[SlicedPort] = field(default_factory=list)
    primary_outputs: List[SlicedPort] = field(default_factory=list)
    registers: List[SlicedRegister] = field(default_factory=list)
    combinational_code: str = ""
    parameters: Dict[str, int] = field(default_factory=dict)

    def get_all_ppi_names(self) -> List[str]:
        """Get all inputs to the combinational cloud: [X_0, X_1, ..., Q_0, Q_1, ...]"""
        ppi = []
        for port in self.primary_inputs:
            if port.name not in (self.clk_port, self.rst_port):
                ppi.extend(port.get_bits())
        for reg in self.registers:
            ppi.append(reg.name)
        return ppi

    def get_all_ppo_names(self) -> List[str]:
        """Get all outputs from the combinational cloud: [D_0, D_1, ..., Y_0, Y_1, ...]"""
        ppo = []
        for reg in self.registers:
            ppo.append(f"{reg.name}_d")
        for port in self.primary_outputs:
            ppo.extend(port.get_bits())
        return ppo


class VerilogSlicer:
    """Extracts sequential elements and creates pure combinational evaluation models."""

    def __init__(self, verilog_code: str):
        self.raw_code = verilog_code
        self.clean_code = self._strip_comments(verilog_code)

    def _strip_comments(self, code: str) -> str:
        code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
        code = re.sub(r"//.*", "", code)
        return code

    def slice(self) -> SlicedModule:
        mod_match = re.search(r"module\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:#\s*\((.*?)\))?\s*\((.*?)\);", self.clean_code, re.DOTALL)
        if not mod_match:
            mod_match = re.search(r"module\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*;", self.clean_code)
            if not mod_match:
                raise ValueError("Could not parse Verilog module header")
            mod_name = mod_match.group(1)
            port_str = ""
        else:
            mod_name = mod_match.group(1)
            port_str = mod_match.group(3)

        sliced = SlicedModule(module_name=mod_name)
        self._parse_ports(sliced, port_str)
        self._parse_parameters(sliced)
        self._parse_registers(sliced)
        return sliced

    def _parse_ports(self, sliced: SlicedModule, port_str: str):
        # ANSI-style ports
        port_pattern = re.compile(r"(input|output|inout)\s+(?:reg\s+|wire\s+)?(?:\[(\d+):(\d+)\]\s+)?([a-zA-Z_][a-zA-Z0-9_]*)")
        for match in port_pattern.finditer(port_str):
            direction, msb, lsb, name = match.groups()
            is_vec = msb is not None and lsb is not None
            msb_val = int(msb) if is_vec else 0
            lsb_val = int(lsb) if is_vec else 0
            width = abs(msb_val - lsb_val) + 1 if is_vec else 1
            sport = SlicedPort(name=name, direction=direction, width=width, msb=msb_val, lsb=lsb_val, is_vector=is_vec)
            if direction == "input":
                sliced.primary_inputs.append(sport)
            elif direction == "output":
                sliced.primary_outputs.append(sport)

        # Body-declared ports
        body_pattern = re.compile(r"\b(input|output|inout)\s+(?:reg\s+|wire\s+)?(?:\[(\d+):(\d+)\]\s+)?([a-zA-Z0-9_,\s]+);")
        for match in body_pattern.finditer(self.clean_code):
            direction, msb, lsb, names_str = match.groups()
            is_vec = msb is not None and lsb is not None
            msb_val = int(msb) if is_vec else 0
            lsb_val = int(lsb) if is_vec else 0
            width = abs(msb_val - lsb_val) + 1 if is_vec else 1
            for name in [n.strip() for n in names_str.split(",") if n.strip()]:
                if not any(p.name == name for p in (sliced.primary_inputs + sliced.primary_outputs)):
                    sport = SlicedPort(name=name, direction=direction, width=width, msb=msb_val, lsb=lsb_val, is_vector=is_vec)
                    if direction == "input":
                        sliced.primary_inputs.append(sport)
                    elif direction == "output":
                        sliced.primary_outputs.append(sport)

    def _parse_parameters(self, sliced: SlicedModule):
        param_pattern = re.compile(r"\bparameter\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(\d+|'b[01]+|'h[0-9a-fA-F]+);")
        for match in param_pattern.finditer(self.clean_code):
            pname, pval = match.groups()
            sliced.parameters[pname] = self._parse_num(pval)

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

    def _parse_registers(self, sliced: SlicedModule):
        # Look for sequential always @(posedge ...) blocks
        seq_pattern = re.compile(r"always\s*@\s*\(\s*(posedge|negedge)\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+or\s+(posedge|negedge)\s+([a-zA-Z_][a-zA-Z0-9_]*))?\s*\)", re.DOTALL)
        
        # Also find all reg declarations to know their widths
        reg_decl_pattern = re.compile(r"\b(?:input\s+|output\s+)?reg\s+(?:\[(\d+):(\d+)\]\s+)?([a-zA-Z0-9_,\s]+);")
        reg_widths: Dict[str, Tuple[int, int, int, bool]] = {} # name -> (width, msb, lsb, is_vector)
        for match in reg_decl_pattern.finditer(self.clean_code):
            msb, lsb, names_str = match.groups()
            is_vec = msb is not None and lsb is not None
            msb_val = int(msb) if is_vec else 0
            lsb_val = int(lsb) if is_vec else 0
            width = abs(msb_val - lsb_val) + 1 if is_vec else 1
            for name in [n.strip() for n in names_str.split(",") if n.strip()]:
                reg_widths[name] = (width, msb_val, lsb_val, is_vec)

        seen_regs: Set[str] = set()
        for match in seq_pattern.finditer(self.clean_code):
            edge1, sig1, edge2, sig2 = match.groups()
            clk_sig = sig1
            rst_sig = sig2 if sig2 else None
            rst_active_low = (edge2 == "negedge") if edge2 else True
            sliced.clk_port = clk_sig
            sliced.rst_port = rst_sig
            sliced.rst_active_low = rst_active_low

            start_pos = match.end()
            assign_pattern = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*(?:\[\d+\])?)\s*<=")
            body_window = self.clean_code[start_pos:start_pos+3000]
            assigned_vars = set(assign_pattern.findall(body_window))

            for avar in sorted(assigned_vars):
                if "[" in avar:
                    base = avar.split("[")[0]
                    bidx = int(avar.split("[")[1].split("]")[0])
                    if avar not in seen_regs:
                        seen_regs.add(avar)
                        sliced.registers.append(
                            SlicedRegister(
                                name=avar,
                                base_name=base,
                                bit_idx=bidx,
                                clk_signal=clk_sig,
                                rst_signal=rst_sig,
                                rst_active_low=rst_active_low,
                            )
                        )
                else:
                    if avar in reg_widths and reg_widths[avar][3]: # is vector
                        width, msb, lsb, _ = reg_widths[avar]
                        for i in range(min(msb, lsb), max(msb, lsb) + 1):
                            rname = f"{avar}[{i}]"
                            if rname not in seen_regs:
                                seen_regs.add(rname)
                                sliced.registers.append(
                                    SlicedRegister(
                                        name=rname,
                                        base_name=avar,
                                        bit_idx=i,
                                        clk_signal=clk_sig,
                                        rst_signal=rst_sig,
                                        rst_active_low=rst_active_low,
                                    )
                                )
                    else:
                        if avar not in seen_regs:
                            seen_regs.add(avar)
                            sliced.registers.append(
                                SlicedRegister(
                                    name=avar,
                                    base_name=avar,
                                    bit_idx=None,
                                    clk_signal=clk_sig,
                                    rst_signal=rst_sig,
                                    rst_active_low=rst_active_low,
                                )
                            )
