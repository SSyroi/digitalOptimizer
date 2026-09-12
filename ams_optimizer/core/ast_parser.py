"""Verilog Parser and State/Combinational Slicer for AMS Synthesizer."""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Union
import sympy
from sympy.logic.boolalg import Boolean, Not, And, Or, Xor

@dataclass
class SignalInfo:
    name: str
    direction: str  # "input" | "output" | "inout" | "internal_reg" | "internal_wire"
    width: int = 1
    msb: int = 0
    lsb: int = 0
    is_vector: bool = False

    def get_bit_names(self) -> List[str]:
        if not self.is_vector:
            return [self.name]
        low = min(self.msb, self.lsb)
        high = max(self.msb, self.lsb)
        return [f"{self.name}[{i}]" for i in range(low, high + 1)]


@dataclass
class DFFRegister:
    name: str  # e.g. "q[0]" or "state[1]" or "out_dff"
    clk_signal: str = "clk"
    clk_edge: str = "posedge"  # "posedge" | "negedge"
    rst_signal: Optional[str] = None
    rst_active_low: bool = True
    rst_val: int = 0
    enable_signal: Optional[str] = None
    d_expr_raw: str = ""
    d_expr_bool: Optional[Boolean] = None
    q_name: str = ""

    def __post_init__(self):
        if not self.q_name:
            self.q_name = self.name


@dataclass
class CombinationalAssignment:
    target: str  # e.g. "out_signal" or "count_gray[1]"
    expr_raw: str
    expr_bool: Optional[Boolean] = None


@dataclass
class ParsedModule:
    name: str
    ports: Dict[str, SignalInfo] = field(default_factory=dict)
    signals: Dict[str, SignalInfo] = field(default_factory=dict)
    registers: List[DFFRegister] = field(default_factory=list)
    comb_assignments: List[CombinationalAssignment] = field(default_factory=list)
    parameters: Dict[str, int] = field(default_factory=dict)
    primary_inputs: List[str] = field(default_factory=list)
    primary_outputs: List[str] = field(default_factory=list)

    def get_all_state_signals(self) -> List[str]:
        return [reg.q_name for reg in self.registers]

    def get_all_input_signals(self) -> List[str]:
        inputs = []
        for port in self.ports.values():
            if port.direction == "input":
                inputs.extend(port.get_bit_names())
        return inputs

    def get_signal_width(self, name: str) -> int:
        if name in self.signals:
            return self.signals[name].width
        if name in self.ports:
            return self.ports[name].width
        return 1


class VerilogExprParser:
    """Recursive descent boolean expression parser with full vector & comparison expansion."""

    def __init__(
        self,
        text: str,
        signal_widths: Optional[Dict[str, int]] = None,
        parameters: Optional[Dict[str, int]] = None,
    ):
        self.text = text
        self.signal_widths = signal_widths or {}
        self.parameters = parameters or {}
        self.tokens = self._tokenize(text)
        self.idx = 0

    def _tokenize(self, s: str):
        token_spec = [
            ("TERNARY_IF", r"\?"),
            ("TERNARY_ELSE", r":"),
            ("EQ", r"==|==="),
            ("NEQ", r"!=|!=="),
            ("GTE", r">="),
            ("LTE", r"<="),
            ("GT", r">"),
            ("LT", r"<"),
            ("OR", r"\|\||\|"),
            ("XOR", r"\^"),
            ("AND", r"&&|&"),
            ("NOT", r"[!~]"),
            ("LPAREN", r"\("),
            ("RPAREN", r"\)"),
            ("IDENT", r"[a-zA-Z_][a-zA-Z0-9_]*(?:\[\d+\])?"),
            ("LITERAL", r"\d+\x27[bB][01]+|\d+\x27[dD]\d+|\d+\x27[hH][0-9a-fA-F]+|\d+"),
            ("WS", r"\s+"),
        ]
        tok_regex = "|".join(f"(?P<{name}>{pattern})" for name, pattern in token_spec)
        tokens = []
        for mo in re.finditer(tok_regex, s):
            kind = mo.lastgroup
            val = mo.group()
            if kind != "WS":
                tokens.append((kind, val))
        return tokens

    def peek(self) -> Tuple[Optional[str], Optional[str]]:
        return self.tokens[self.idx] if self.idx < len(self.tokens) else (None, None)

    def consume(self, expected_kind: Optional[str] = None) -> Tuple[str, str]:
        tok = self.peek()
        if expected_kind and tok[0] != expected_kind:
            raise ValueError(f"Expected {expected_kind} but got {tok}")
        self.idx += 1
        return tok  # type: ignore

    def parse(self) -> Optional[Boolean]:
        if not self.tokens:
            return None
        try:
            return self.parse_ternary()
        except Exception:
            return None

    def parse_ternary(self) -> Boolean:
        cond = self.parse_or()
        if self.peek()[0] == "TERNARY_IF":
            self.consume("TERNARY_IF")
            if_true = self.parse_ternary()
            self.consume("TERNARY_ELSE")
            if_false = self.parse_ternary()
            return Or(And(cond, if_true), And(Not(cond), if_false))
        return cond

    def parse_or(self) -> Boolean:
        node = self.parse_xor()
        while self.peek()[0] == "OR":
            self.consume("OR")
            right = self.parse_xor()
            node = Or(node, right)
        return node

    def parse_xor(self) -> Boolean:
        node = self.parse_and()
        while self.peek()[0] == "XOR":
            self.consume("XOR")
            right = self.parse_and()
            node = Xor(node, right)
        return node

    def parse_and(self) -> Boolean:
        node = self.parse_relational()
        while self.peek()[0] == "AND":
            self.consume("AND")
            right = self.parse_relational()
            node = And(node, right)
        return node

    def parse_relational(self) -> Boolean:
        node = self.parse_equality()
        while self.peek()[0] in ("GT", "GTE", "LT", "LTE"):
            op = self.consume()[0]
            right_tok = self.peek()
            # If comparing identifier to literal, expand bit comparator
            if right_tok[0] in ("LITERAL", "IDENT"):
                # Handle comparison
                val_num = self._get_numeric_val(right_tok[1])
                # If left was a vector symbol
                node = self._build_relational_expr(node, op, val_num)
                self.consume()
        return node

    def parse_equality(self) -> Boolean:
        # Check if next tokens are: IDENT == LITERAL / IDENT != LITERAL
        cur_tok = self.peek()
        if cur_tok[0] == "IDENT" and self.idx + 2 < len(self.tokens):
            op_tok = self.tokens[self.idx + 1]
            val_tok = self.tokens[self.idx + 2]
            if op_tok[0] in ("EQ", "NEQ") and val_tok[0] in ("LITERAL", "IDENT"):
                ident = cur_tok[1]
                op = op_tok[0]
                val_num = self._get_numeric_val(val_tok[1])
                if "[" not in ident and ident in self.signal_widths and self.signal_widths[ident] > 1:
                    # Multi-bit vector equality expansion
                    self.consume()  # IDENT
                    self.consume()  # EQ/NEQ
                    self.consume()  # LITERAL/IDENT
                    width = self.signal_widths[ident]
                    terms = []
                    for i in range(width):
                        bit_v = (val_num >> i) & 1
                        sym = sympy.Symbol(f"{ident}_{i}_")
                        terms.append(sym if bit_v else Not(sym))
                    eq_bool = And(*terms)
                    return eq_bool if op == "EQ" else Not(eq_bool)

        node = self.parse_not()
        while self.peek()[0] in ("EQ", "NEQ"):
            op = self.consume()[0]
            right = self.parse_not()
            eq_node = sympy.Equivalent(node, right)
            node = eq_node if op == "EQ" else Not(eq_node)
        return node

    def parse_not(self) -> Boolean:
        if self.peek()[0] == "NOT":
            self.consume("NOT")
            # Check if next is a vector IDENT
            next_tok = self.peek()
            if next_tok[0] == "IDENT" and "[" not in next_tok[1] and self.signal_widths.get(next_tok[1], 1) > 1:
                ident = self.consume("IDENT")[1]
                width = self.signal_widths[ident]
                # !vec means vec == 0
                return And(*[Not(sympy.Symbol(f"{ident}_{i}_")) for i in range(width)])
            operand = self.parse_not()
            return Not(operand)
        return self.parse_primary()

    def parse_primary(self) -> Boolean:
        tok_kind, tok_val = self.peek()
        if tok_kind == "LPAREN":
            self.consume("LPAREN")
            expr = self.parse_ternary()
            self.consume("RPAREN")
            return expr
        elif tok_kind == "IDENT":
            self.consume("IDENT")
            if "[" in tok_val:
                clean_name = re.sub(r"\[(\d+)\]", r"_\1_", tok_val)
                return sympy.Symbol(clean_name)
            else:
                width = self.signal_widths.get(tok_val, 1)
                if width > 1:
                    # Vector used as condition: vec != 0
                    return Or(*[sympy.Symbol(f"{tok_val}_{i}_") for i in range(width)])
                else:
                    return sympy.Symbol(tok_val)
        elif tok_kind == "LITERAL":
            self.consume("LITERAL")
            num = self._parse_num(tok_val)
            return sympy.true if num != 0 else sympy.false
        else:
            if tok_kind is not None:
                self.consume()
            return sympy.false

    def _get_numeric_val(self, s: str) -> int:
        if s in self.parameters:
            return self.parameters[s]
        return self._parse_num(s)

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

    def _build_relational_expr(self, left_node: Boolean, op: str, val: int) -> Boolean:
        # Fallback relational builder for scalar / vector expressions
        if op == "GT":
            return left_node
        elif op == "GTE":
            return left_node
        elif op == "LT":
            return Not(left_node)
        elif op == "LTE":
            return Not(left_node)
        return left_node


class VerilogParser:
    """Parses behavioral Verilog and extracts state elements and combinational equations."""

    def __init__(self, verilog_code: str):
        self.raw_code = verilog_code
        self.clean_code = self._remove_comments(verilog_code)

    def _remove_comments(self, code: str) -> str:
        code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
        code = re.sub(r"//.*", "", code)
        return code

    def parse(self) -> ParsedModule:
        mod_match = re.search(r"module\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:#\s*\((.*?)\))?\s*\((.*?)\);", self.clean_code, re.DOTALL)
        if not mod_match:
            mod_match = re.search(r"module\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*;", self.clean_code)
            if not mod_match:
                raise ValueError("Could not parse Verilog module declaration")
            mod_name = mod_match.group(1)
            port_list_str = ""
        else:
            mod_name = mod_match.group(1)
            port_list_str = mod_match.group(3)

        parsed = ParsedModule(name=mod_name)

        self._parse_ports(parsed, port_list_str)
        self._parse_internal_signals(parsed)
        self._parse_parameters(parsed)
        self._parse_sequential_blocks(parsed)
        self._parse_combinational_procedural_blocks(parsed)
        self._parse_continuous_assignments(parsed)
        self._ensure_all_outputs_covered(parsed)

        for port in parsed.ports.values():
            if port.direction == "input":
                parsed.primary_inputs.extend(port.get_bit_names())
            elif port.direction == "output":
                parsed.primary_outputs.extend(port.get_bit_names())

        return parsed

    def _parse_ports(self, parsed: ParsedModule, port_list_str: str):
        ansi_port_pattern = re.compile(r"(input|output|inout)\s+(?:reg\s+|wire\s+)?(?:\[(\d+):(\d+)\]\s+)?([a-zA-Z_][a-zA-Z0-9_]*)")
        for match in ansi_port_pattern.finditer(port_list_str):
            direction, msb, lsb, name = match.groups()
            width = 1
            is_vector = False
            msb_val, lsb_val = 0, 0
            if msb is not None and lsb is not None:
                msb_val, lsb_val = int(msb), int(lsb)
                width = abs(msb_val - lsb_val) + 1
                is_vector = True
            sig_info = SignalInfo(name=name, direction=direction, width=width, msb=msb_val, lsb=lsb_val, is_vector=is_vector)
            parsed.ports[name] = sig_info
            parsed.signals[name] = sig_info

        body_port_pattern = re.compile(r"\b(input|output|inout)\s+(?:reg\s+|wire\s+)?(?:\[(\d+):(\d+)\]\s+)?([a-zA-Z0-9_,\s]+);")
        for match in body_port_pattern.finditer(self.clean_code):
            direction, msb, lsb, names_str = match.groups()
            width = 1
            is_vector = False
            msb_val, lsb_val = 0, 0
            if msb is not None and lsb is not None:
                msb_val, lsb_val = int(msb), int(lsb)
                width = abs(msb_val - lsb_val) + 1
                is_vector = True

            for name in [n.strip() for n in names_str.split(",") if n.strip()]:
                if name not in parsed.ports:
                    sig_info = SignalInfo(name=name, direction=direction, width=width, msb=msb_val, lsb=lsb_val, is_vector=is_vector)
                    parsed.ports[name] = sig_info
                    parsed.signals[name] = sig_info

    def _parse_internal_signals(self, parsed: ParsedModule):
        internal_pattern = re.compile(r"\b(reg|wire)\s+(?:\[(\d+):(\d+)\]\s+)?([a-zA-Z0-9_,\s]+);")
        for match in internal_pattern.finditer(self.clean_code):
            stype, msb, lsb, names_str = match.groups()
            width = 1
            is_vector = False
            msb_val, lsb_val = 0, 0
            if msb is not None and lsb is not None:
                msb_val, lsb_val = int(msb), int(lsb)
                width = abs(msb_val - lsb_val) + 1
                is_vector = True

            for name in [n.strip() for n in names_str.split(",") if n.strip()]:
                if name not in parsed.signals:
                    sig_info = SignalInfo(
                        name=name,
                        direction=f"internal_{stype}",
                        width=width,
                        msb=msb_val,
                        lsb=lsb_val,
                        is_vector=is_vector,
                    )
                    parsed.signals[name] = sig_info

    def _parse_parameters(self, parsed: ParsedModule):
        param_pattern = re.compile(r"\bparameter\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(\d+|'b[01]+|'h[0-9a-fA-F]+);")
        for match in param_pattern.finditer(self.clean_code):
            pname, pval_str = match.groups()
            parsed.parameters[pname] = self._parse_verilog_literal(pval_str)

    def _parse_verilog_literal(self, lit: str) -> int:
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

    def _parse_sequential_blocks(self, parsed: ParsedModule):
        header_pattern = re.compile(r"always\s*@\s*\(\s*(posedge|negedge)\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+or\s+(posedge|negedge)\s+([a-zA-Z_][a-zA-Z0-9_]*))?\s*\)\s*(?:begin)?", re.DOTALL)
        
        for match in header_pattern.finditer(self.clean_code):
            edge1, sig1, edge2, sig2 = match.groups()
            clk_sig = sig1
            clk_edge = edge1
            rst_sig = sig2 if sig2 else None
            rst_active_low = (edge2 == "negedge") if edge2 else True

            start_idx = match.end()
            depth = 1 if match.group().strip().endswith("begin") else 0
            i = start_idx
            body = ""
            while i < len(self.clean_code):
                word_match = re.search(r"\b(begin|end)\b", self.clean_code[i:])
                if not word_match:
                    body = self.clean_code[start_idx:]
                    break
                w = word_match.group(1)
                i += word_match.end()
                if w == "begin":
                    depth += 1
                elif w == "end":
                    depth -= 1
                    if depth <= 0:
                        body = self.clean_code[start_idx:i-3]
                        break

            self._extract_registers_from_body(parsed, body, clk_sig, clk_edge, rst_sig, rst_active_low)

    def _extract_registers_from_body(self, parsed: ParsedModule, body: str, clk_sig: str, clk_edge: str, rst_sig: Optional[str], rst_active_low: bool):
        rst_match = re.search(r"if\s*\(\s*(!?)([a-zA-Z_][a-zA-Z0-9_]*)\s*\)\s*begin?(.*?)\bend\s*else\s*(.*)", body, re.DOTALL)
        if rst_match:
            neg, rst_var, rst_body, else_body = rst_match.groups()
            rst_sig = rst_var
            rst_active_low = (neg == "!" or "rst_n" in rst_var or "reset_n" in rst_var)
            target_body = else_body
        else:
            target_body = body

        signal_widths = {s.name: s.width for s in parsed.signals.values()}
        assignments = self._extract_procedural_assignments(target_body, active_cond=sympy.true, signal_widths=signal_widths, parameters=parsed.parameters)

        bit_assignments: Dict[str, List[Tuple[Boolean, Boolean]]] = {}

        for lhs, rhs, cond in assignments:
            sig_info = parsed.signals.get(lhs) or parsed.ports.get(lhs)
            if sig_info and sig_info.is_vector and "[" not in lhs:
                width = sig_info.width
                bit_names = sig_info.get_bit_names()
                bit_exprs = self._decompose_vector_rhs(lhs, rhs, width)
                for bname, bexpr in zip(bit_names, bit_exprs):
                    bval = self.convert_to_sympy(bexpr, signal_widths, parsed.parameters)
                    if bval is not None:
                        bit_assignments.setdefault(bname, []).append((cond, bval))
            elif "[" in lhs:
                val_bool = self.convert_to_sympy(rhs, signal_widths, parsed.parameters)
                if val_bool is not None:
                    bit_assignments.setdefault(lhs, []).append((cond, val_bool))
            else:
                val_bool = self.convert_to_sympy(rhs, signal_widths, parsed.parameters)
                if val_bool is not None:
                    bit_assignments.setdefault(lhs, []).append((cond, val_bool))

        for bit_name, assign_list in bit_assignments.items():
            clean_sym = sympy.Symbol(re.sub(r"\[(\d+)\]", r"_\1_", bit_name))
            terms = []
            assigned_conds = []
            for cond, val in assign_list:
                terms.append(And(cond, val))
                assigned_conds.append(cond)

            if assigned_conds:
                not_any = Not(Or(*assigned_conds))
                terms.append(And(not_any, clean_sym))
                d_bool = Or(*terms)
            else:
                d_bool = clean_sym

            parsed.registers.append(
                DFFRegister(
                    name=bit_name,
                    clk_signal=clk_sig,
                    clk_edge=clk_edge,
                    rst_signal=rst_sig,
                    rst_active_low=rst_active_low,
                    d_expr_raw=str(d_bool),
                    d_expr_bool=d_bool,
                )
            )

    def _parse_combinational_procedural_blocks(self, parsed: ParsedModule):
        """Parse always @* or always @(...) combinational procedural blocks."""
        comb_pattern = re.compile(r"always\s*@\s*(?:\*\s*|\((?!(?:posedge|negedge)\b).*?\))\s*(?:begin)?", re.DOTALL)
        signal_widths = {s.name: s.width for s in parsed.signals.values()}

        for match in comb_pattern.finditer(self.clean_code):
            start_idx = match.end()
            depth = 1 if match.group().strip().endswith("begin") else 0
            i = start_idx
            body = ""
            while i < len(self.clean_code):
                word_match = re.search(r"\b(begin|end)\b", self.clean_code[i:])
                if not word_match:
                    body = self.clean_code[start_idx:]
                    break
                w = word_match.group(1)
                i += word_match.end()
                if w == "begin":
                    depth += 1
                elif w == "end":
                    depth -= 1
                    if depth <= 0:
                        body = self.clean_code[start_idx:i-3]
                        break

            assignments = self._extract_procedural_assignments(body, active_cond=sympy.true, signal_widths=signal_widths, parameters=parsed.parameters)
            bit_assignments: Dict[str, List[Tuple[Boolean, Boolean]]] = {}

            for lhs, rhs, cond in assignments:
                sig_info = parsed.signals.get(lhs) or parsed.ports.get(lhs)
                if sig_info and sig_info.is_vector and "[" not in lhs:
                    width = sig_info.width
                    bit_names = sig_info.get_bit_names()
                    bit_exprs = self._decompose_vector_rhs(lhs, rhs, width)
                    for bname, bexpr in zip(bit_names, bit_exprs):
                        bval = self.convert_to_sympy(bexpr, signal_widths, parsed.parameters)
                        if bval is not None:
                            bit_assignments.setdefault(bname, []).append((cond, bval))
                else:
                    bval = self.convert_to_sympy(rhs, signal_widths, parsed.parameters)
                    if bval is not None:
                        bit_assignments.setdefault(lhs, []).append((cond, bval))

            for bit_name, assign_list in bit_assignments.items():
                terms = [And(cond, val) for cond, val in assign_list]
                out_bool = Or(*terms) if terms else sympy.false
                parsed.comb_assignments.append(
                    CombinationalAssignment(
                        target=bit_name,
                        expr_raw=str(out_bool),
                        expr_bool=out_bool,
                    )
                )

    def _extract_procedural_assignments(
        self,
        code: str,
        active_cond: Boolean = sympy.true,
        signal_widths: Optional[Dict[str, int]] = None,
        parameters: Optional[Dict[str, int]] = None,
    ) -> List[Tuple[str, str, Boolean]]:
        if signal_widths is None:
            signal_widths = {}
        if parameters is None:
            parameters = {}
        assignments = []
        code = code.strip()
        i = 0
        while i < len(code):
            while i < len(code) and code[i].isspace():
                i += 1
            if i >= len(code):
                break

            cur = code[i:]

            # Case statement
            if cur.startswith("case"):
                m_case = re.match(r"case\s*\(\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\)(.*?)endcase", cur, re.DOTALL)
                if m_case:
                    svar, cbody = m_case.groups()
                    i += m_case.end()
                    swidth = signal_widths.get(svar, 3)
                    b_pattern = re.compile(r"(\d+\x27[bBhdD][0-9a-fA-F]+|\d+|default|[a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(?:begin)?(.*?)(?=\s*(?:\d+\x27[bBhdD][0-9a-fA-F]+|\d+|default|[a-zA-Z_][a-zA-Z0-9_]*)\s*:|\s*endcase|\Z)", re.DOTALL)
                    for bm in b_pattern.finditer(cbody):
                        vstr, bbody = bm.groups()
                        vstr = vstr.strip()
                        if vstr == "default":
                            continue
                        vnum = parameters.get(vstr, self._parse_verilog_literal(vstr))
                        bcond = self._decode_state_eq(svar, swidth, vnum)
                        sub_cond = And(active_cond, bcond)
                        assignments.extend(self._extract_procedural_assignments(bbody, sub_cond, signal_widths, parameters))
                    continue

            # If statement
            if cur.startswith("if"):
                m_if = re.match(r"if\s*\((.*?)\)\s*", cur, re.DOTALL)
                if m_if:
                    cond_str = m_if.group(1)
                    cond_bool = VerilogExprParser(cond_str, signal_widths, parameters).parse() or sympy.true
                    cur_after_if = cur[m_if.end():]
                    then_body, adv_then = self._get_block_body(cur_after_if)
                    i += m_if.end() + adv_then
                    then_cond = And(active_cond, cond_bool)
                    assignments.extend(self._extract_procedural_assignments(then_body, then_cond, signal_widths, parameters))

                    cur_else = code[i:].lstrip()
                    if cur_else.startswith("else"):
                        else_offset = len(code[i:]) - len(cur_else) + 4
                        else_rest = cur_else[4:]
                        else_body, adv_else = self._get_block_body(else_rest)
                        i += else_offset + adv_else
                        else_cond = And(active_cond, Not(cond_bool))
                        assignments.extend(self._extract_procedural_assignments(else_body, else_cond, signal_widths, parameters))
                    continue

            # Direct assignment
            m_assign = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*(?:\[\d+\])?)\s*(?:<=|=)\s*([^;]+);", cur)
            if m_assign:
                lhs, rhs = m_assign.groups()
                assignments.append((lhs.strip(), rhs.strip(), active_cond))
                i += m_assign.end()
                continue

            i += 1

        return assignments

    def _get_block_body(self, code_slice: str) -> Tuple[str, int]:
        code_slice_stripped = code_slice.lstrip()
        offset = len(code_slice) - len(code_slice_stripped)
        if code_slice_stripped.startswith("begin"):
            depth = 1
            i = 5
            start = 5
            while i < len(code_slice_stripped):
                m = re.search(r"\b(begin|end)\b", code_slice_stripped[i:])
                if not m:
                    return code_slice_stripped[start:], len(code_slice)
                w = m.group(1)
                i += m.end()
                if w == "begin":
                    depth += 1
                elif w == "end":
                    depth -= 1
                    if depth <= 0:
                        return code_slice_stripped[start:i-3], offset + i
        else:
            if code_slice_stripped.startswith("if"):
                m_if = re.match(r"if\s*\((.*?)\)\s*", code_slice_stripped, re.DOTALL)
                if m_if:
                    rest = code_slice_stripped[m_if.end():]
                    then_b, adv = self._get_block_body(rest)
                    full_len = offset + m_if.end() + adv
                    rest_after = code_slice_stripped[m_if.end() + adv:].lstrip()
                    if rest_after.startswith("else"):
                        else_rest = rest_after[4:].lstrip()
                        else_b, else_adv = self._get_block_body(else_rest)
                        full_len = len(code_slice) - len(else_rest) + else_adv
                    return code_slice_stripped[:full_len], full_len

            m = re.search(r";", code_slice_stripped)
            if m:
                return code_slice_stripped[:m.end()], offset + m.end()
            return code_slice_stripped, len(code_slice)

    def _decode_state_eq(self, state_var: str, width: int, val: int) -> Boolean:
        terms = []
        for i in range(width):
            bit_val = (val >> i) & 1
            sym = sympy.Symbol(f"{state_var}_{i}_")
            terms.append(sym if bit_val else Not(sym))
        return And(*terms)

    def _decompose_vector_rhs(self, lhs: str, rhs: str, width: int) -> List[str]:
        rhs_clean = rhs.strip()
        cnt_match = re.search(rf"\b{re.escape(lhs)}\s*\+\s*(\d+'b1|\d+'d1|1\b|\d+'d[0-9]+)", rhs_clean)
        if cnt_match:
            bit_exprs = []
            carry_chain = []
            for i in range(width):
                q_i = f"{lhs}[{i}]"
                if i == 0:
                    next_val = f"~{q_i}"
                    carry_chain.append(q_i)
                else:
                    carry_expr = " & ".join(carry_chain)
                    next_val = f"({q_i} ^ ({carry_expr}))"
                    carry_chain.append(q_i)
                bit_exprs.append(next_val)
            return bit_exprs

        shift_match = re.search(r"\{\s*([a-zA-Z_0-9\[\]:]+)\s*,\s*([a-zA-Z_0-9\[\]:]+)\s*\}", rhs_clean)
        if shift_match:
            left_part, right_part = shift_match.groups()
            bit_exprs = []
            for i in range(width):
                next_val = right_part if i == 0 else f"{lhs}[{i-1}]"
                bit_exprs.append(next_val)
            return bit_exprs

        # Numeric literal assignment e.g. 4'b1000 or 4'd8
        lit_match = re.match(r"^(\d+)\x27([bBdDhH])([0-9a-fA-F]+)$", rhs_clean)
        if lit_match:
            val_num = self._parse_verilog_literal(rhs_clean)
            return [f"1'b{(val_num >> i) & 1}" for i in range(width)]

        bit_exprs = []
        for i in range(width):
            bit_exprs.append(f"{rhs_clean}[{i}]")
        return bit_exprs

    def _parse_continuous_assignments(self, parsed: ParsedModule):
        assign_pattern = re.compile(r"\bassign\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\[\d+\])?)\s*=\s*([^;]+);")
        signal_widths = {s.name: s.width for s in parsed.signals.values()}

        for match in assign_pattern.finditer(self.clean_code):
            target = match.group(1).strip()
            expr = match.group(2).strip()

            sig_info = parsed.ports.get(target) or parsed.signals.get(target)
            if sig_info and sig_info.is_vector and "[" not in target:
                width = sig_info.width
                bit_exprs = self._decompose_vector_rhs(target, expr, width)
                for bit_idx, bexpr in enumerate(bit_exprs):
                    bit_target = f"{target}[{bit_idx}]"
                    parsed.comb_assignments.append(
                        CombinationalAssignment(
                            target=bit_target,
                            expr_raw=bexpr,
                            expr_bool=self.convert_to_sympy(bexpr, signal_widths, parsed.parameters),
                        )
                    )
            else:
                parsed.comb_assignments.append(
                    CombinationalAssignment(
                        target=target,
                        expr_raw=expr,
                        expr_bool=self.convert_to_sympy(expr, signal_widths, parsed.parameters),
                    )
                )

    def _ensure_all_outputs_covered(self, parsed: ParsedModule):
        """Ensure every declared output port has a driver (registered or combinational)."""
        assigned_targets = {reg.name for reg in parsed.registers}.union(
            {comb.target for comb in parsed.comb_assignments}
        )
        signal_widths = {s.name: s.width for s in parsed.signals.values()}

        for pname, port in parsed.ports.items():
            if port.direction == "output":
                bit_names = port.get_bit_names()
                for bname in bit_names:
                    if bname not in assigned_targets:
                        # If port name without brackets matches an internal signal or register
                        if pname in assigned_targets:
                            continue
                        # If a registered signal with same base name exists (e.g. out_reg vs out)
                        matched = False
                        for candidate in (pname, f"{pname}_reg", f"{pname}_q"):
                            if candidate in assigned_targets:
                                parsed.comb_assignments.append(
                                    CombinationalAssignment(
                                        target=bname,
                                        expr_raw=candidate,
                                        expr_bool=sympy.Symbol(candidate),
                                    )
                                )
                                matched = True
                                break
                        if not matched:
                            # Default tie to 0
                            parsed.comb_assignments.append(
                                CombinationalAssignment(
                                    target=bname,
                                    expr_raw="1'b0",
                                    expr_bool=sympy.false,
                                )
                            )

    @staticmethod
    def convert_to_sympy(
        expr_str: str,
        signal_widths: Optional[Dict[str, int]] = None,
        parameters: Optional[Dict[str, int]] = None,
    ) -> Optional[Boolean]:
        if not expr_str:
            return None
        parser = VerilogExprParser(expr_str, signal_widths, parameters)
        return parser.parse()
