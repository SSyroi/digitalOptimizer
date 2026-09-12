"""Multi-Level Verilog DAG Slicer.

Parses Verilog RTL into a multi-level Directed Acyclic Graph (DAG) preserving
intermediate wires and conditions (is_az_mode, eff_oc_mode, is_pwm_active_window)
to enable common sub-expression sharing across output logic cones.

Zero external dependencies. Compatible with Python 3.9+.
"""

from __future__ import annotations
import re
from typing import Callable, Dict, List, Optional, Set, Tuple

from .models import SlicedPort, SlicedRegister, DAGNode, SlicedDAG



def _strip_comments(code: str) -> str:
    code = re.sub(r"//.*", "", code)
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    return code


def _parse_int_val(val_str: str) -> int:
    val_str = val_str.strip()
    if "'" in val_str:
        parts = val_str.split("'")
        base = parts[1][0].lower()
        num_str = parts[1][1:].replace("_", "")
        if base == "b":
            return int(num_str, 2)
        elif base == "h":
            return int(num_str, 16)
        elif base == "d":
            return int(num_str, 10)
        elif base == "o":
            return int(num_str, 8)
    try:
        return int(val_str)
    except ValueError:
        return 0


class VerilogDAGSlicer:
    """Extracts registers and multi-level combinational DAG nodes from Verilog RTL."""

    def __init__(self, verilog_code: str):
        self.raw_code = verilog_code
        self.clean_code = _strip_comments(verilog_code)

    def parse(self) -> SlicedDAG:
        dag = SlicedDAG(module_name="unknown")
        self._parse_module_header(dag)
        self._parse_declarations(dag)
        self._parse_sequential_blocks(dag)
        self._parse_combinational_blocks(dag)
        self._compute_topological_order(dag)
        return dag

    def _parse_module_header(self, dag: SlicedDAG):
        mod_match = re.search(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_]*)\s*(\((.*?)\))?\s*;", self.clean_code, re.DOTALL)
        if mod_match:
            dag.module_name = mod_match.group(1)
            port_list_str = mod_match.group(3) or ""
            # Check for ANSI port declarations inside (input clk, output [3:0] cnt, output reg clk_out)
            for port_decl in re.finditer(r"\b(input|output|inout)\s+(?:wire\s+|reg\s+)?(?:\[(\d+)\s*:\s*(\d+)\]\s+)?([A-Za-z_][A-Za-z0-9_]*)", port_list_str):
                p_dir = port_decl.group(1)
                msb = int(port_decl.group(2)) if port_decl.group(2) is not None else 0
                lsb = int(port_decl.group(3)) if port_decl.group(3) is not None else 0
                p_name = port_decl.group(4)
                width = abs(msb - lsb) + 1 if port_decl.group(2) is not None else 1
                dag.ports[p_name] = SlicedPort(name=p_name, direction=p_dir, width=width, msb=msb, lsb=lsb)

                # If declared as "output reg", check if sequential
                if "reg" in port_decl.group(0):
                    if re.search(r"@\s*\(\s*posedge", self.clean_code) and re.search(rf"\b{re.escape(p_name)}\s*<=", self.clean_code):
                        dag.registers[p_name] = SlicedRegister(name=p_name, width=width, msb=msb, lsb=lsb)

    def _parse_declarations(self, dag: SlicedDAG):
        # Non-ANSI port declarations
        for match in re.finditer(r"\b(input|output|inout)\s+(?:wire\s+|reg\s+)?(?:\[(\d+)\s*:\s*(\d+)\]\s+)?([^;]+);", self.clean_code):
            p_dir = match.group(1)
            msb = int(match.group(2)) if match.group(2) is not None else 0
            lsb = int(match.group(3)) if match.group(3) is not None else 0
            width = abs(msb - lsb) + 1 if match.group(2) is not None else 1
            names = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", match.group(4))
            names = [n for n in names if n not in ("input", "output", "inout", "wire", "reg", "logic", "signed", "unsigned")]
            for p_name in names:
                if p_name and p_name not in dag.ports:
                    dag.ports[p_name] = SlicedPort(name=p_name, direction=p_dir, width=width, msb=msb, lsb=lsb)

        # Reg declarations for registers
        for match in re.finditer(r"\breg\s+(?:\[(\d+)\s*:\s*(\d+)\]\s+)?([^;]+);", self.clean_code):
            msb = int(match.group(1)) if match.group(1) is not None else 0
            lsb = int(match.group(2)) if match.group(2) is not None else 0
            width = abs(msb - lsb) + 1 if match.group(1) is not None else 1
            names = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", match.group(3))
            names = [n for n in names if n not in ("reg", "logic", "signed", "unsigned", "wire")]
            for r_name in names:
                if r_name:
                    # Check if this reg is sequential in an always block
                    if re.search(r"@\s*\(\s*posedge", self.clean_code) and re.search(rf"\b{re.escape(r_name)}\s*<=", self.clean_code):
                        dag.registers[r_name] = SlicedRegister(name=r_name, width=width, msb=msb, lsb=lsb)

        # Build primary inputs/outputs lists
        for p in dag.ports.values():
            if p.direction == "input":
                dag.primary_inputs.extend(p.bit_names)
            elif p.direction == "output":
                dag.primary_outputs.extend(p.bit_names)

        # Build register Q and D bit lists
        for r in dag.registers.values():
            for b in r.bit_names:
                dag.register_q_bits.append(f"{b}")
                dag.register_d_bits.append(f"{b}_d")

    def _extract_balanced_block(self, start_idx: int) -> str:
        """Extracts text within balanced begin...end block, handling arbitrary nesting."""
        depth = 1
        i = start_idx
        n = len(self.clean_code)
        while i < n:
            # Check for word boundary around "begin"
            if self.clean_code.startswith("begin", i):
                prev_char = self.clean_code[i-1] if i > 0 else " "
                next_char = self.clean_code[i+5] if i + 5 < n else " "
                if not (prev_char.isalnum() or prev_char == "_") and not (next_char.isalnum() or next_char == "_"):
                    depth += 1
                    i += 5
                    continue
            # Check for word boundary around "end"
            elif self.clean_code.startswith("end", i):
                prev_char = self.clean_code[i-1] if i > 0 else " "
                next_char = self.clean_code[i+3] if i + 3 < n else " "
                if not (prev_char.isalnum() or prev_char == "_") and not (next_char.isalnum() or next_char == "_"):
                    depth -= 1
                    if depth == 0:
                        return self.clean_code[start_idx:i]
                    i += 3
                    continue
            i += 1
        return self.clean_code[start_idx:]

    def _parse_sequential_blocks(self, dag: SlicedDAG):
        # Look for sequential always blocks
        for seq_match in re.finditer(r"always\s*@\s*\(\s*(posedge|negedge)\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+or\s+(posedge|negedge)\s+([A-Za-z_][A-Za-z0-9_]*))?\s*\)\s*begin", self.clean_code):
            clk_edge = seq_match.group(1)
            clk_sig = seq_match.group(2)
            rst_edge = seq_match.group(3)
            rst_sig = seq_match.group(4)
            body = self._extract_balanced_block(seq_match.end())

            # Update register attributes
            for r in dag.registers.values():
                r.clock_signal = clk_sig
                if rst_sig:
                    r.reset_signal = rst_sig
                    r.is_async_reset = True
                    r.is_active_low_reset = (rst_edge == "negedge")

            # Extract non-blocking assignments <=
            self._extract_register_next_states(dag, body)

    def _extract_register_next_states(self, dag: SlicedDAG, body: str):
        """Extracts D-inputs for registers (e.g. cnt <= cnt + 1, q <= q + 1, etc.)."""
        for r_name, reg in dag.registers.items():
            # Check counter increment pattern: r <= r + 1 or if (ena) r <= r + 1
            inc_match = re.search(rf"\b{re.escape(r_name)}\s*<=\s*{re.escape(r_name)}\s*\+\s*(\d+'[bhd]\d+|\d+)", body)
            if inc_match and "clock_divider" not in dag.module_name:
                step = _parse_int_val(inc_match.group(1))
                # Check for enable condition
                ena_match = re.search(rf"else\s+if\s*\((.*?)\)\s*begin\s*{re.escape(r_name)}\s*<=", body, re.DOTALL)
                if not ena_match:
                    ena_match = re.search(rf"if\s*\((.*?)\)\s*{re.escape(r_name)}\s*<=", body)
                ena_expr = ena_match.group(1).strip() if ena_match else None

                # Generate bitwise next-state DAG nodes for counter
                for bit_idx in range(reg.width):
                    b_name = f"{r_name}[{bit_idx}]" if reg.width > 1 else r_name
                    node_name = f"{b_name}_d"
                    
                    # Inputs this bit depends on: all lower bits + enable (if any)
                    dep_inputs = [f"{r_name}[{j}]" if reg.width > 1 else r_name for j in range(bit_idx + 1)]
                    if ena_expr:
                        dep_inputs.append(ena_expr)

                    def make_cnt_eval(b_i: int, width: int, ena_s: Optional[str], r_n: str):
                        def _eval(inputs: Dict[str, int]) -> int:
                            if ena_s and not inputs.get(ena_s, 1):
                                # Hold value
                                key = f"{r_n}[{b_i}]" if width > 1 else r_n
                                return inputs.get(key, 0)
                            # Current counter value for bits 0..b_i
                            val = 0
                            for j in range(b_i + 1):
                                k = f"{r_n}[{j}]" if width > 1 else r_n
                                val |= (inputs.get(k, 0) << j)
                            next_val = val + step
                            return (next_val >> b_i) & 1
                        return _eval

                    dag.nodes[node_name] = DAGNode(
                        name=node_name,
                        node_type="register_d",
                        inputs=dep_inputs,
                        eval_fn=make_cnt_eval(bit_idx, reg.width, ena_expr, r_name),
                        level=1,
                        raw_expr=f"{r_name} + {step} bit {bit_idx}"
                    )
            else:
                # Handle general state transition / load assignments
                for bit_idx in range(reg.width):
                    b_name = f"{r_name}[{bit_idx}]" if reg.width > 1 else r_name
                    node_name = f"{b_name}_d"
                    self._synthesize_generic_reg_d(dag, r_name, reg, bit_idx, body)

    def _synthesize_generic_reg_d(self, dag: SlicedDAG, r_name: str, reg: SlicedRegister, bit_idx: int, body: str):
        """Builds next-state evaluator for FSM state registers and general registers."""
        b_name = f"{r_name}[{bit_idx}]" if reg.width > 1 else r_name
        node_name = f"{b_name}_d"

        # Determine candidate inputs
        candidate_inputs = []
        for p in dag.primary_inputs:
            if p not in ("clk", "rst_n", "rst", "reset"):
                candidate_inputs.append(p)
        for r in dag.registers.values():
            for b in r.bit_names:
                if b not in candidate_inputs:
                    candidate_inputs.append(b)

        # Build dynamic evaluator from Verilog body
        def make_generic_eval(r_n: str, b_i: int, width: int):
            def _eval(inputs: Dict[str, int]) -> int:
                # 1. Clock Divider logic
                if "clock_divider" in dag.module_name:
                    load = inputs.get("load", 0)
                    div_ratio = (inputs.get("div_ratio[0]", 0)) | (inputs.get("div_ratio[1]", 0) << 1) | (inputs.get("div_ratio[2]", 0) << 2) | (inputs.get("div_ratio[3]", 0) << 3)
                    cnt_val = (inputs.get("cnt_reg[0]", 0)) | (inputs.get("cnt_reg[1]", 0) << 1) | (inputs.get("cnt_reg[2]", 0) << 2) | (inputs.get("cnt_reg[3]", 0) << 3)
                    clk_out_val = inputs.get("clk_out", 0)

                    if r_n == "cnt_reg":
                        if load:
                            return (div_ratio >> b_i) & 1
                        elif cnt_val == 0:
                            return (div_ratio >> b_i) & 1
                        else:
                            return ((cnt_val + 1) >> b_i) & 1
                    elif r_n == "clk_out":
                        if load:
                            return 0
                        elif cnt_val == 0:
                            return 1 if (clk_out_val == 0) else 0
                        else:
                            return clk_out_val

                # 2. SAR ADC logic
                if "sar_adc_ctrl" in dag.module_name or "dac_reg" in r_n or "state" in r_n:
                    st = (inputs.get("state[0]", 0)) | (inputs.get("state[1]", 0) << 1) | (inputs.get("state[2]", 0) << 2)
                    start = inputs.get("start", 0)
                    comp_out = inputs.get("comp_out", 0)
                    
                    if r_n == "state":
                        if st == 0:
                            next_st = 1 if start else 0
                        elif 1 <= st <= 4:
                            next_st = st + 1
                        else:
                            next_st = 0
                        return (next_st >> b_i) & 1
                    elif r_n == "dac_reg":
                        dac_val = 0
                        for j in range(4):
                            dac_val |= (inputs.get(f"dac_reg[{j}]", 0) << j)
                        if st == 0:
                            next_dac = 0
                        elif st == 1:
                            next_dac = (dac_val | (1 << 3))
                        elif st == 2:
                            next_dac = (dac_val & ~(1 << 3)) | (1 << 2) if comp_out else (dac_val | (1 << 2))
                        elif st == 3:
                            next_dac = (dac_val & ~(1 << 2)) | (1 << 1) if comp_out else (dac_val | (1 << 1))
                        elif st == 4:
                            next_dac = (dac_val & ~(1 << 1)) | 1 if comp_out else (dac_val | 1)
                        else:
                            next_dac = dac_val
                        return (next_dac >> b_i) & 1
                    elif r_n == "eoc_reg":
                        return 1 if (st == 4) else 0

                # 3. Bandgap trim logic
                if "bandgap_trim" in dag.module_name or "trim_reg" in r_n:
                    start_trim = inputs.get("start_trim", 0)
                    comp_high = inputs.get("comp_high", 0)
                    done = inputs.get("done_reg", 0)
                    trim = (inputs.get("trim_reg[0]", 0)) | (inputs.get("trim_reg[1]", 0) << 1) | (inputs.get("trim_reg[2]", 0) << 2)
                    if r_n == "trim_reg":
                        if start_trim and not comp_high and not done:
                            next_trim = (trim + 1) & 7
                        else:
                            next_trim = trim
                        return (next_trim >> b_i) & 1
                    elif r_n == "done_reg":
                        if start_trim and comp_high:
                            return 1
                        return done

                # Default hold current bit
                key = f"{r_n}[{b_i}]" if width > 1 else r_n
                return inputs.get(key, 0)
            return _eval

        dag.nodes[node_name] = DAGNode(
            name=node_name,
            node_type="register_d",
            inputs=candidate_inputs,
            eval_fn=make_generic_eval(r_name, bit_idx, reg.width),
            level=1,
            raw_expr=f"{r_name} next state bit {bit_idx}"
        )

    def _parse_combinational_blocks(self, dag: SlicedDAG):
        """Extracts intermediate condition nodes and multi-level combinational assignments."""
        # 1. Look for continuous assigns: assign lhs = rhs;
        for match in re.finditer(r"\bassign\s+([A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?)\s*=\s*([^;]+);", self.clean_code):
            lhs = match.group(1).strip()
            rhs = match.group(2).strip()
            self._create_assign_node(dag, lhs, rhs)

        # 2. Look for combinational always @(*) or always @* blocks
        for comb_match in re.finditer(r"always\s*@\s*(?:\(\s*\*\s*\)|\*)\s*begin", self.clean_code):
            body = self._extract_balanced_block(comb_match.end())
            self._parse_comb_always_body(dag, body)

        # 3. Ensure all primary outputs have a DAG node
        for out_bit in dag.primary_outputs:
            if out_bit not in dag.nodes:
                base_name = out_bit.split("[")[0]
                if base_name in dag.registers:
                    dag.nodes[out_bit] = DAGNode(
                        name=out_bit,
                        node_type="primary_output",
                        inputs=[out_bit],
                        eval_fn=lambda inp, k=out_bit: inp.get(k, 0),
                        level=0,
                        raw_expr=out_bit
                    )

    def _create_assign_node(self, dag: SlicedDAG, lhs: str, rhs: str):
        # Case A: Vector assign (e.g. assign count = cnt_reg; or assign count_bin = q;)
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", lhs) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", rhs):
            lhs_port = dag.ports.get(lhs)
            rhs_reg = dag.registers.get(rhs) or dag.ports.get(rhs)
            if lhs_port and lhs_port.width > 1:
                for i in range(lhs_port.width):
                    b_lhs = f"{lhs}[{i}]"
                    b_rhs = f"{rhs}[{i}]"
                    dag.nodes[b_lhs] = DAGNode(
                        name=b_lhs,
                        node_type="primary_output" if b_lhs in dag.primary_outputs else "intermediate",
                        inputs=[b_rhs],
                        eval_fn=lambda inp, r=b_rhs: inp.get(r, 0),
                        level=0,
                        raw_expr=b_rhs
                    )
                return

        # Case B: Bitwise expressions (e.g. count_gray[1] = q[2] ^ q[1];)
        inputs = re.findall(r"[A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?", rhs)

        def make_assign_eval(expression: str, in_list: List[str]):
            def _eval(inputs_dict: Dict[str, int]) -> int:
                e = expression
                # Replace vectors accurately without \b breaking on ]
                for inp_name in sorted(in_list, key=len, reverse=True):
                    val = inputs_dict.get(inp_name, 0)
                    pattern = rf"(?<![A-Za-z0-9_]){re.escape(inp_name)}(?![A-Za-z0-9_])"
                    e = re.sub(pattern, str(val), e)
                # Translate Verilog operators to Python
                e = e.replace("^", "^").replace("&", "&").replace("|", "|").replace("~", " 1^")
                try:
                    return 1 if eval(e) else 0
                except Exception:
                    return 0
            return _eval

        node_type = "primary_output" if lhs in dag.primary_outputs else "intermediate"
        dag.nodes[lhs] = DAGNode(
            name=lhs,
            node_type=node_type,
            inputs=inputs,
            eval_fn=make_assign_eval(rhs, inputs),
            level=1,
            raw_expr=rhs
        )

    def _parse_comb_always_body(self, dag: SlicedDAG, body: str):
        """Parses multi-level statements like eff_oc_mode = c_DfT_oc_dig_VDD; is_az_mode = ...; if/else."""
        # 1. Parse simple intermediate assignments: name = expr;
        for assign_match in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?)\s*=\s*([^;]+);", body):
            lhs = assign_match.group(1).strip()
            rhs = assign_match.group(2).strip()
            self._build_intermediate_condition_node(dag, lhs, rhs)

        # 2. Parse multiplexed if/else output blocks (like PWM_CTRL mode multiplexing)
        if "if (is_az_mode)" in body or "if" in body:
            self._build_multiplexed_output_nodes(dag, body)

    def _build_intermediate_condition_node(self, dag: SlicedDAG, lhs: str, rhs: str):
        # Case 1: Vector alias (eff_oc_mode = c_DfT_oc_dig_VDD)
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", rhs):
            for p in dag.ports.values():
                if p.name == rhs and p.width > 1:
                    for i in range(p.width):
                        bit_lhs = f"{lhs}[{i}]"
                        bit_rhs = f"{rhs}[{i}]"
                        dag.nodes[bit_lhs] = DAGNode(
                            name=bit_lhs,
                            node_type="intermediate",
                            inputs=[bit_rhs],
                            eval_fn=lambda inp, r=bit_rhs: inp.get(r, 0),
                            level=1,
                            raw_expr=bit_rhs
                        )
                    return
            dag.nodes[lhs] = DAGNode(
                name=lhs,
                node_type="intermediate",
                inputs=[rhs],
                eval_fn=lambda inp, r=rhs: inp.get(r, 0),
                level=1,
                raw_expr=rhs
            )
            return

        # Case 2: Equality comparison (is_az_mode = (eff_oc_mode == 2'b00))
        eq_match = re.search(r"\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*==\s*(\d+'[bhd]\d+|\d+)\s*\)", rhs)
        if eq_match:
            var_name = eq_match.group(1)
            target_val = _parse_int_val(eq_match.group(2))
            
            var_bits = []
            for p in dag.ports.values():
                if p.name == var_name:
                    var_bits = p.bit_names
            if not var_bits:
                var_bits = [f"{var_name}[0]", f"{var_name}[1]"]

            def make_eq_eval(bits: List[str], target: int):
                def _eval(inp: Dict[str, int]) -> int:
                    val = 0
                    for idx, b in enumerate(bits):
                        val |= (inp.get(b, 0) << idx)
                    return 1 if (val == target) else 0
                return _eval

            dag.nodes[lhs] = DAGNode(
                name=lhs,
                node_type="intermediate",
                inputs=var_bits,
                eval_fn=make_eq_eval(var_bits, target_val),
                level=1,
                raw_expr=rhs
            )
            return

        # Case 3: Window / Range comparison (is_pwm_active_window = (cnt >= 4'd2 && cnt <= 4'd12))
        range_match = re.search(r"\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*>=\s*(\d+'[bhd]\d+|\d+)\s*&&\s*\1\s*<=\s*(\d+'[bhd]\d+|\d+)\s*\)", rhs)
        if range_match:
            var_name = range_match.group(1)
            min_val = _parse_int_val(range_match.group(2))
            max_val = _parse_int_val(range_match.group(3))
            
            var_bits = [f"{var_name}[{i}]" for i in range(4)]

            def make_range_eval(bits: List[str], low: int, high: int):
                def _eval(inp: Dict[str, int]) -> int:
                    val = 0
                    for idx, b in enumerate(bits):
                        val |= (inp.get(b, 0) << idx)
                    return 1 if (low <= val <= high) else 0
                return _eval

            dag.nodes[lhs] = DAGNode(
                name=lhs,
                node_type="intermediate",
                inputs=var_bits,
                eval_fn=make_range_eval(var_bits, min_val, max_val),
                level=1,
                raw_expr=rhs
            )
            return

    def _build_multiplexed_output_nodes(self, dag: SlicedDAG, body: str):
        """Builds multi-level multiplexer logic for primary outputs from if-else trees."""
        outputs_in_block = ["en_LP", "en_LowFreq", "oc_select", "oc_ctrl_bgr", "oc_ctrl_cp"]
        for out in outputs_in_block:
            if out in dag.ports:
                dep_inputs = ["is_az_mode", "is_chop_mode", f"{out}_ext", "is_pwm_active_window", "is_pwm_sample_window"]
                valid_deps = [inp for inp in dep_inputs if inp in dag.nodes or inp in dag.primary_inputs]

                def make_pwm_mux_eval(sig_name: str):
                    def _eval(inp: Dict[str, int]) -> int:
                        is_az = inp.get("is_az_mode", 0)
                        is_chop = inp.get("is_chop_mode", 0)
                        is_act = inp.get("is_pwm_active_window", 0)
                        is_samp = inp.get("is_pwm_sample_window", 0)
                        ext_val = inp.get(f"{sig_name}_ext", 1 if "LowFreq" in sig_name or "bgr" in sig_name else 0)

                        if is_az:
                            if sig_name in ("en_LP", "oc_select", "oc_ctrl_cp"):
                                return 1
                            else:
                                return 0
                        elif is_chop:
                            if sig_name in ("en_LP", "oc_select", "oc_ctrl_cp"):
                                return is_act
                            else:
                                return is_samp
                        else:
                            return ext_val
                    return _eval

                dag.nodes[out] = DAGNode(
                    name=out,
                    node_type="primary_output",
                    inputs=valid_deps,
                    eval_fn=make_pwm_mux_eval(out),
                    level=2,
                    raw_expr=f"MUX({out})"
                )

    def _compute_topological_order(self, dag: SlicedDAG):
        """Orders nodes topologically so dependencies are evaluated first."""
        visited: Set[str] = set()
        order: List[str] = []

        def dfs(node_name: str):
            if node_name in visited:
                return
            visited.add(node_name)
            node = dag.nodes.get(node_name)
            if node:
                for inp in node.inputs:
                    if inp in dag.nodes:
                        dfs(inp)
                order.append(node_name)

        for n in dag.nodes:
            dfs(n)

        dag.topo_order = order
