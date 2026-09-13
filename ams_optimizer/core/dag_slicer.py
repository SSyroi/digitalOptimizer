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
from .rtl_simulator import (
    RTLCombinationalSimulator,
    VerilogExprEvaluator,
    VerilogProceduralParser,
    Stmt,
    AssignStmt,
    IfStmt,
    CaseStmt,
    parse_verilog_int,
)



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
        # Parameters
        for match in re.finditer(r"\bparameter\s+(?:\[(\d+)\s*:\s*(\d+)\]\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;]+);", self.clean_code):
            p_name = match.group(3)
            dag.parameters[p_name] = parse_verilog_int(match.group(4).strip())

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

        # Wire declarations for internal nets
        for match in re.finditer(r"\bwire\s+(?:\[(\d+)\s*:\s*(\d+)\]\s+)?([^;]+);", self.clean_code):
            msb = int(match.group(1)) if match.group(1) is not None else 0
            lsb = int(match.group(2)) if match.group(2) is not None else 0
            width = abs(msb - lsb) + 1 if match.group(1) is not None else 1
            names = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", match.group(3))
            names = [n for n in names if n not in ("wire", "logic", "signed", "unsigned")]
            for w_name in names:
                if w_name and w_name not in dag.ports:
                    dag.wires[w_name] = SlicedPort(name=w_name, direction="wire", width=width, msb=msb, lsb=lsb)

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

            # Parse reset values from the reset branch (e.g. if (!res_n) ... else ...)
            if rst_sig:
                rst_branch_m = re.search(
                    rf"if\s*\(\s*(?:!\s*{re.escape(rst_sig)}|~{re.escape(rst_sig)}|{re.escape(rst_sig)}\s*==\s*1'b0|{re.escape(rst_sig)})\s*\)\s*begin(.*?)end",
                    body,
                    re.DOTALL
                )
                if rst_branch_m:
                    rst_body = rst_branch_m.group(1)
                    for assign_m in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*<=\s*([^;]+);", rst_body):
                        tgt = assign_m.group(1).strip()
                        val_str = assign_m.group(2).strip()
                        parsed_val = _parse_int_val(val_str)
                        if tgt in dag.registers:
                            dag.registers[tgt].reset_val = parsed_val

            # Extract non-blocking assignments <=
            self._extract_register_next_states(dag, body)

    def _extract_register_next_states(self, dag: SlicedDAG, body: str):
        """Extracts D-inputs for all registers using the unified RTL procedural simulator."""
        for r_name, reg in dag.registers.items():
            for bit_idx in range(reg.width):
                b_name = f"{r_name}[{bit_idx}]" if reg.width > 1 else r_name
                node_name = f"{b_name}_d"
                self._synthesize_generic_reg_d(dag, r_name, reg, bit_idx, body)

    def _get_reg_dependencies(self, dag: SlicedDAG, r_name: str, body: str) -> List[str]:
        reg = dag.registers.get(r_name)
        needed_vars: Set[str] = set()
        if reg:
            needed_vars.update(reg.bit_names)

        # Parse procedural statements of active body
        else_match = re.search(r"\belse\b", body)
        active_body = body[else_match.end():].strip() if else_match else body

        parser = VerilogProceduralParser(active_body)
        stmts = parser.parse_statements(active_body)

        def find_assigned_deps(stmt_list: List[Stmt], target: str) -> Tuple[bool, Set[str]]:
            assigns = False
            deps: Set[str] = set()
            for stmt in stmt_list:
                if isinstance(stmt, AssignStmt):
                    if stmt.target_name == target:
                        assigns = True
                        for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", stmt.expr_str):
                            deps.add(tok)
                elif isinstance(stmt, IfStmt):
                    then_assigns, then_deps = find_assigned_deps(stmt.then_stmts, target)
                    else_assigns, else_deps = find_assigned_deps(stmt.else_stmts, target)
                    if then_assigns or else_assigns:
                        assigns = True
                        deps.update(then_deps)
                        deps.update(else_deps)
                        for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", stmt.cond_str):
                            deps.add(tok)
                elif isinstance(stmt, CaseStmt):
                    case_assigns = False
                    for val_eval, branch_stmts in stmt.branches:
                        b_assigns, b_deps = find_assigned_deps(branch_stmts, target)
                        if b_assigns:
                            case_assigns = True
                            deps.update(b_deps)
                    d_assigns, d_deps = find_assigned_deps(stmt.default_stmts, target)
                    if d_assigns:
                        case_assigns = True
                        deps.update(d_deps)
                    if case_assigns or d_assigns:
                        assigns = True
                        for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", stmt.expr_str):
                            deps.add(tok)
            return assigns, deps

        # Wire continuous assign dependencies
        wire_deps: Dict[str, Set[str]] = {}
        for match in re.finditer(r"\bassign\s+([A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?)\s*=\s*([^;]+);", self.clean_code):
            w_lhs = match.group(1).strip().split("[")[0]
            w_rhs = match.group(2).strip()
            wire_deps.setdefault(w_lhs, set()).update(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", w_rhs))

        def expand_tok(tok_name: str, visited: Set[str]) -> Set[str]:
            if tok_name in visited:
                return set()
            visited.add(tok_name)
            if tok_name in wire_deps:
                sub_res = set()
                for sub_t in wire_deps[tok_name]:
                    sub_res.update(expand_tok(sub_t, visited))
                return sub_res
            return {tok_name}

        assigns, raw_deps = find_assigned_deps(stmts, r_name)
        expanded_deps: Set[str] = set()
        for tok in raw_deps:
            base_tok = tok.split("[")[0]
            expanded_deps.update(expand_tok(base_tok, set()))

        for tok in expanded_deps:
            base_tok = tok.split("[")[0]
            if base_tok in dag.parameters:
                continue
            if base_tok in dag.registers:
                needed_vars.update(dag.registers[base_tok].bit_names)
            elif base_tok in dag.ports and dag.ports[base_tok].direction == "input":
                needed_vars.update(dag.ports[base_tok].bit_names)

        clock_sig = reg.clock_signal if reg else "clk"
        reset_sig = reg.reset_signal if reg else "rst_n"
        deps = [v for v in needed_vars if v not in ("clk", "rst_n", "rst", "reset", clock_sig, reset_sig)]
        return sorted(deps) if deps else [p for p in dag.primary_inputs if p not in ("clk", "rst_n", "rst", "reset")] + dag.register_q_bits

    def _synthesize_generic_reg_d(self, dag: SlicedDAG, r_name: str, reg: SlicedRegister, bit_idx: int, body: str):
        """Builds next-state evaluator for FSM state registers and general registers using RTL simulator."""
        b_name = f"{r_name}[{bit_idx}]" if reg.width > 1 else r_name
        node_name = f"{b_name}_d"

        candidate_inputs = self._get_reg_dependencies(dag, r_name, body)

        if not hasattr(self, "_rtl_sim") or self._rtl_sim is None:
            self._rtl_sim = RTLCombinationalSimulator(self.raw_code)

        target_sig = node_name
        sim = self._rtl_sim

        def make_eval(sig: str, simulator: RTLCombinationalSimulator):
            return lambda inputs: simulator.simulate_vector(inputs).get(sig, 0)

        dag.nodes[node_name] = DAGNode(
            name=node_name,
            node_type="register_d",
            inputs=candidate_inputs,
            eval_fn=make_eval(target_sig, sim),
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
                else:
                    dag.nodes[out_bit] = DAGNode(
                        name=out_bit,
                        node_type="primary_output",
                        inputs=[],
                        eval_fn=lambda inp: 0,
                        level=0,
                        raw_expr="0.0"
                    )

    def _create_assign_node(self, dag: SlicedDAG, lhs: str, rhs: str):
        # Case A: Pure Vector alias (e.g. assign count = cnt_reg; or assign count_bin = q;)
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", lhs) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", rhs):
            lhs_port = dag.ports.get(lhs) or dag.wires.get(lhs)
            rhs_reg = dag.registers.get(rhs) or dag.ports.get(rhs) or dag.wires.get(rhs)
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

        evaluator = VerilogExprEvaluator(rhs)

        # Extract variable dependencies from rhs tokens
        in_names: Set[str] = set()
        tokens = evaluator.tokens
        for i, (tok_type, tok_txt) in enumerate(tokens):
            if tok_type == "ID":
                if tok_txt in dag.parameters:
                    continue
                if i + 3 < len(tokens) and tokens[i+1][1] == "[" and tokens[i+3][1] == "]":
                    bit_str = tokens[i+2][1]
                    in_names.add(f"{tok_txt}[{bit_str}]")
                else:
                    port_or_wire = dag.ports.get(tok_txt) or dag.wires.get(tok_txt)
                    reg = dag.registers.get(tok_txt)
                    if port_or_wire and port_or_wire.width > 1:
                        in_names.update(port_or_wire.bit_names)
                    elif reg and reg.width > 1:
                        in_names.update(reg.bit_names)
                    else:
                        in_names.add(tok_txt)

        valid_inputs = [
            n for n in in_names
            if n in dag.nodes or n in dag.primary_inputs or n in dag.register_q_bits
            or any(n.startswith(f"{p}[") for p in dag.primary_inputs)
            or any(n.startswith(f"{r}[") for r in dag.registers)
            or n in dag.ports or n in dag.wires
        ]
        if not valid_inputs:
            valid_inputs = list(in_names)

        def make_assign_eval(ev: VerilogExprEvaluator, params: Dict[str, int], bit_index: Optional[int] = None):
            if bit_index is not None:
                return lambda inp: (ev.evaluate({**params, **inp}) >> bit_index) & 1
            return lambda inp: 1 if ev.evaluate({**params, **inp}) else 0

        port_or_wire = dag.ports.get(lhs) or dag.wires.get(lhs)
        if port_or_wire and port_or_wire.width > 1:
            for bit_i in range(port_or_wire.width):
                b_lhs = f"{lhs}[{bit_i}]"
                dag.nodes[b_lhs] = DAGNode(
                    name=b_lhs,
                    node_type="primary_output" if b_lhs in dag.primary_outputs else "intermediate",
                    inputs=sorted(valid_inputs),
                    eval_fn=make_assign_eval(evaluator, dag.parameters, bit_i),
                    level=1,
                    raw_expr=f"({rhs})[{bit_i}]"
                )
            return

        node_type = "primary_output" if lhs in dag.primary_outputs else "intermediate"
        dag.nodes[lhs] = DAGNode(
            name=lhs,
            node_type=node_type,
            inputs=sorted(valid_inputs),
            eval_fn=make_assign_eval(evaluator, dag.parameters),
            level=1,
            raw_expr=rhs
        )

    def _parse_comb_always_body(self, dag: SlicedDAG, body: str):
        """Parses combinational always @(*) blocks with arbitrary nested procedural logic."""
        parser = VerilogProceduralParser(body)
        stmts = parser.parse_statements(body)

        def _find_targets(s_list: List[Stmt]) -> Set[str]:
            res = set()
            for s in s_list:
                if isinstance(s, AssignStmt):
                    res.add(s.target_name)
                elif isinstance(s, IfStmt):
                    res.update(_find_targets(s.then_stmts))
                    res.update(_find_targets(s.else_stmts))
                elif isinstance(s, CaseStmt):
                    for _, b_stmts in s.branches:
                        res.update(_find_targets(b_stmts))
                    res.update(_find_targets(s.default_stmts))
            return res

        all_targets = _find_targets(stmts)
        all_targets = {t for t in all_targets if t not in dag.registers}

        def _extract_signals_for_target(s_list: List[Stmt], tgt: str) -> Set[str]:
            used = set()
            for s in s_list:
                if isinstance(s, AssignStmt):
                    if s.target_name == tgt:
                        for m in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?", s.expr_str):
                            used.add(m.group(0))
                elif isinstance(s, IfStmt):
                    then_used = _extract_signals_for_target(s.then_stmts, tgt)
                    else_used = _extract_signals_for_target(s.else_stmts, tgt)
                    if then_used or else_used:
                        used.update(then_used)
                        used.update(else_used)
                        for m in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?", s.cond_str):
                            used.add(m.group(0))
                elif isinstance(s, CaseStmt):
                    case_used = set()
                    for _, b_stmts in s.branches:
                        case_used.update(_extract_signals_for_target(b_stmts, tgt))
                    case_used.update(_extract_signals_for_target(s.default_stmts, tgt))
                    if case_used:
                        used.update(case_used)
                        for m in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?", s.expr_str):
                            used.add(m.group(0))
            return used

        # Available signals in DAG
        available = set(dag.primary_inputs) | set(dag.register_q_bits) | set(dag.nodes.keys())
        for port in dag.ports.values():
            if port.width > 1:
                available.update(port.bit_names)
        for w in dag.wires.values():
            if w.width > 1:
                available.update(w.bit_names)

        for out in all_targets:
            raw_deps = _extract_signals_for_target(stmts, out)
            expanded_deps: Set[str] = set()
            for d in raw_deps:
                base_d = d.split("[")[0]
                if base_d in dag.parameters:
                    continue
                port_or_wire = dag.ports.get(base_d) or dag.wires.get(base_d)
                reg = dag.registers.get(base_d)
                if "[" in d:
                    if d in available or d in dag.nodes:
                        expanded_deps.add(d)
                elif port_or_wire and port_or_wire.width > 1:
                    expanded_deps.update([b for b in port_or_wire.bit_names if b in available or b in dag.nodes])
                elif reg and reg.width > 1:
                    expanded_deps.update([b for b in reg.bit_names if b in available or b in dag.register_q_bits])
                elif d in available or d in dag.nodes:
                    expanded_deps.add(d)

            # Safety fallback: if expanded_deps is empty, search tokens in body
            if not expanded_deps:
                for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?", body):
                    if tok in dag.parameters:
                        continue
                    if (tok in available or tok in dag.nodes) and tok != out:
                        expanded_deps.add(tok)

            def make_comb_eval(tgt: str, statements: List[Stmt], params: Dict[str, int]):
                def _eval(inp: Dict[str, int]) -> int:
                    env = dict(params)
                    env.update(inp)
                    for s in statements:
                        s.execute(env, env)
                    return env.get(tgt, 0)
                return _eval

            dag.nodes[out] = DAGNode(
                name=out,
                node_type="primary_output" if out in dag.primary_outputs else "intermediate",
                inputs=sorted(expanded_deps),
                eval_fn=make_comb_eval(out, stmts, dag.parameters),
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
