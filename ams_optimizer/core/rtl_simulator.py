"""RTL Combinational Simulator & Golden Reference Generator.

Parses Verilog RTL directly, removes/cuts flip-flop storage elements to treat
the sequential blocks as pure combinational next-state networks, and simulates
the original Verilog semantics to produce unbiased golden truth table arrays.

100% standard library. Zero external dependencies. Compatible with Python 3.9+.
"""

from __future__ import annotations
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .models import SlicedPort, SlicedRegister


def parse_verilog_int(val_str: str) -> int:
    """Parses standard Verilog integer literals like 3'b001, 4'hA, 8'd10, 15."""
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


class VerilogExprEvaluator:
    """Recursive descent expression evaluator for Verilog expressions."""

    TOKEN_SPEC = [
        ("HEX", r"\d+'[hH][0-9a-fA-F_]+"),
        ("BIN", r"\d+'[bB][01_]+"),
        ("DEC", r"\d+'[dD][0-9_]+"),
        ("NUM", r"\b\d+\b"),
        ("EQ", r"=="),
        ("NE", r"!="),
        ("LE", r"<="),
        ("GE", r">="),
        ("AND", r"&&"),
        ("OR", r"\|\|"),
        ("LT", r"<"),
        ("GT", r">"),
        ("NOT", r"!"),
        ("INV", r"~"),
        ("XOR", r"\^"),
        ("AMP", r"&"),
        ("PIPE", r"\|"),
        ("PLUS", r"\+"),
        ("MINUS", r"-"),
        ("LPAREN", r"\("),
        ("RPAREN", r"\)"),
        ("LBRACK", r"\["),
        ("RBRACK", r"\]"),
        ("LBRACE", r"\{"),
        ("RBRACE", r"\}"),
        ("COLON", r":"),
        ("COMMA", r","),
        ("QUESTION", r"\?"),
        ("ID", r"[a-zA-Z_][a-zA-Z0-9_]*"),
        ("WS", r"\s+"),
    ]
    TOKEN_REGEX = re.compile("|".join(f"(?P<{n}>{p})" for n, p in TOKEN_SPEC))

    def __init__(self, expr_str: str):
        self.expr_str = expr_str.strip()
        self.tokens = self._tokenize(self.expr_str)
        self.pos = 0

    def _tokenize(self, text: str) -> List[Tuple[str, str]]:
        toks = []
        for m in self.TOKEN_REGEX.finditer(text):
            k = m.lastgroup
            if k != "WS":
                toks.append((k, m.group()))
        return toks

    def peek(self) -> Tuple[str, str]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else ("EOF", "")

    def get(self) -> Tuple[str, str]:
        tok = self.peek()
        self.pos += 1
        return tok

    def evaluate(self, env: Dict[str, int]) -> int:
        self.pos = 0
        if not self.tokens:
            return 0
        try:
            return self._expr(env)
        except Exception:
            return 0

    def _expr(self, env: Dict[str, int]) -> int:
        return self._ternary(env)

    def _ternary(self, env: Dict[str, int]) -> int:
        val = self._lor(env)
        if self.peek()[0] == "QUESTION":
            self.get()
            true_val = self._expr(env)
            if self.peek()[0] == "COLON":
                self.get()
            false_val = self._expr(env)
            return true_val if val else false_val
        return val

    def _lor(self, env: Dict[str, int]) -> int:
        val = self._land(env)
        while self.peek()[0] == "OR":
            self.get()
            r = self._land(env)
            val = 1 if (val or r) else 0
        return val

    def _land(self, env: Dict[str, int]) -> int:
        val = self._bor(env)
        while self.peek()[0] == "AND":
            self.get()
            r = self._bor(env)
            val = 1 if (val and r) else 0
        return val

    def _bor(self, env: Dict[str, int]) -> int:
        val = self._bxor(env)
        while self.peek()[0] == "PIPE":
            self.get()
            val = val | self._bxor(env)
        return val

    def _bxor(self, env: Dict[str, int]) -> int:
        val = self._band(env)
        while self.peek()[0] == "XOR":
            self.get()
            val = val ^ self._band(env)
        return val

    def _band(self, env: Dict[str, int]) -> int:
        val = self._eq(env)
        while self.peek()[0] == "AMP":
            self.get()
            val = val & self._eq(env)
        return val

    def _eq(self, env: Dict[str, int]) -> int:
        val = self._rel(env)
        while self.peek()[0] in ("EQ", "NE"):
            op = self.get()[0]
            r = self._rel(env)
            val = 1 if ((val == r) if op == "EQ" else (val != r)) else 0
        return val

    def _rel(self, env: Dict[str, int]) -> int:
        val = self._add(env)
        while self.peek()[0] in ("LT", "LE", "GT", "GE"):
            op = self.get()[0]
            r = self._add(env)
            if op == "LT": val = 1 if val < r else 0
            elif op == "LE": val = 1 if val <= r else 0
            elif op == "GT": val = 1 if val > r else 0
            elif op == "GE": val = 1 if val >= r else 0
        return val

    def _add(self, env: Dict[str, int]) -> int:
        val = self._unary(env)
        while self.peek()[0] in ("PLUS", "MINUS"):
            op = self.get()[0]
            r = self._unary(env)
            val = (val + r) if op == "PLUS" else (val - r)
        return val

    def _unary(self, env: Dict[str, int]) -> int:
        k, txt = self.peek()
        if k == "NOT":
            self.get()
            return 1 if not self._unary(env) else 0
        elif k == "INV":
            self.get()
            u = self._unary(env)
            return (~u) & 1 if u in (0, 1) else ~u
        elif k == "MINUS":
            self.get()
            return -self._unary(env)
        return self._primary(env)

    def _primary(self, env: Dict[str, int]) -> int:
        k, txt = self.get()
        if k in ("HEX", "BIN", "DEC", "NUM"):
            return parse_verilog_int(txt)
        elif k == "ID":
            # Check bit select: id[bit] or id[msb:lsb]
            if self.peek()[0] == "LBRACK":
                self.get()
                b_val = self._expr(env)
                if self.peek()[0] == "COLON":
                    self.get()
                    l_val = self._expr(env)
                    if self.peek()[0] == "RBRACK":
                        self.get()
                    full = env.get(txt, 0)
                    mask = (1 << (b_val - l_val + 1)) - 1
                    return (full >> l_val) & mask
                if self.peek()[0] == "RBRACK":
                    self.get()
                key = f"{txt}[{b_val}]"
                if key in env:
                    return env[key]
                full = env.get(txt, 0)
                return (full >> b_val) & 1
            return env.get(txt, 0)
        elif k == "LPAREN":
            val = self._expr(env)
            if self.peek()[0] == "RPAREN":
                self.get()
            return val
        elif k == "LBRACE":
            # Concatenation {a, b, c}
            parts = []
            while self.peek()[0] not in ("RBRACE", "EOF"):
                parts.append(self._expr(env))
                if self.peek()[0] == "COMMA":
                    self.get()
            if self.peek()[0] == "RBRACE":
                self.get()
            res = 0
            for p in parts:
                res = (res << 1) | (p & 1)
            return res
        return 0


# ==============================================================================
# Procedural Statements AST
# ==============================================================================

class Stmt:
    def execute(self, env: Dict[str, int], next_env: Dict[str, int]):
        raise NotImplementedError


class AssignStmt(Stmt):
    def __init__(self, target_name: str, bit_idx: Optional[int], expr_str: str, is_blocking: bool = False):
        self.target_name = target_name
        self.bit_idx = bit_idx
        self.expr_str = expr_str
        self.is_blocking = is_blocking
        self.evaluator = VerilogExprEvaluator(expr_str)

    def execute(self, env: Dict[str, int], next_env: Dict[str, int]):
        val = self.evaluator.evaluate(env)
        target_dict = env if self.is_blocking else next_env

        if self.bit_idx is not None:
            # Single bit update: target[bit]
            orig = target_dict.get(self.target_name, 0)
            new_val = (orig & ~(1 << self.bit_idx)) | ((val & 1) << self.bit_idx)
            target_dict[self.target_name] = new_val
            target_dict[f"{self.target_name}[{self.bit_idx}]"] = val & 1
            if not self.is_blocking:
                next_env[self.target_name] = new_val
                next_env[f"{self.target_name}[{self.bit_idx}]"] = val & 1
        else:
            # Full vector update: target <= expr
            target_dict[self.target_name] = val
            for b in range(16):
                key = f"{self.target_name}[{b}]"
                if key in target_dict or key in env:
                    target_dict[key] = (val >> b) & 1
            if not self.is_blocking:
                next_env[self.target_name] = val
                for b in range(16):
                    key = f"{self.target_name}[{b}]"
                    if key in next_env or key in env:
                        next_env[key] = (val >> b) & 1


class IfStmt(Stmt):
    def __init__(self, cond_str: str, then_stmts: List[Stmt], else_stmts: List[Stmt]):
        self.cond_str = cond_str
        self.then_stmts = then_stmts
        self.else_stmts = else_stmts
        self.evaluator = VerilogExprEvaluator(cond_str)

    def execute(self, env: Dict[str, int], next_env: Dict[str, int]):
        cond_val = self.evaluator.evaluate(env)
        if cond_val:
            for s in self.then_stmts:
                s.execute(env, next_env)
        else:
            for s in self.else_stmts:
                s.execute(env, next_env)


class CaseStmt(Stmt):
    def __init__(self, expr_str: str, branches: List[Tuple[str, List[Stmt]]], default_stmts: List[Stmt]):
        self.expr_str = expr_str
        self.branches = [(VerilogExprEvaluator(vexp), stmts) for vexp, stmts in branches]
        self.default_stmts = default_stmts
        self.evaluator = VerilogExprEvaluator(expr_str)

    def execute(self, env: Dict[str, int], next_env: Dict[str, int]):
        sel_val = self.evaluator.evaluate(env)
        matched = False
        for val_eval, stmts in self.branches:
            target_val = val_eval.evaluate(env)
            if sel_val == target_val:
                matched = True
                for s in stmts:
                    s.execute(env, next_env)
                break
        if not matched and self.default_stmts:
            for s in self.default_stmts:
                s.execute(env, next_env)


# ==============================================================================
# Verilog Procedural Parser
# ==============================================================================

class VerilogProceduralParser:
    """Parses procedural code blocks (if/else, case, assignments) into executable AST."""

    def __init__(self, code_text: str):
        self.code = self._strip_comments(code_text)

    @staticmethod
    def _strip_comments(code: str) -> str:
        code = re.sub(r"//.*", "", code)
        code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
        return code

    def parse_statements(self, text: str) -> List[Stmt]:
        """Parses a sequence of statements inside an active procedural block."""
        tokens = self._tokenize(text)
        stmts, _ = self._parse_stmt_list(tokens, 0, stop_tokens={"end", "endcase", "EOF"})
        return stmts

    def _tokenize(self, text: str) -> List[Tuple[str, str]]:
        token_spec = [
            ("HEX", r"\d+'[hH][0-9a-fA-F_]+"),
            ("BIN", r"\d+'[bB][01_]+"),
            ("DEC", r"\d+'[dD][0-9_]+"),
            ("NUM", r"\b\d+\b"),
            ("EQ", r"=="),
            ("NE", r"!="),
            ("LE", r"<="),
            ("GE", r">="),
            ("AND", r"&&"),
            ("OR", r"\|\|"),
            ("ASSIGN", r"="),
            ("COLON", r":"),
            ("SEMI", r";"),
            ("LPAREN", r"\("),
            ("RPAREN", r"\)"),
            ("LBRACK", r"\["),
            ("RBRACK", r"\]"),
            ("LBRACE", r"\{"),
            ("RBRACE", r"\}"),
            ("COMMA", r","),
            ("ID", r"[a-zA-Z_][a-zA-Z0-9_]*"),
            ("OP", r"[+\-!~^&|?><]+"),
            ("WS", r"\s+"),
        ]
        reg = re.compile("|".join(f"(?P<{n}>{p})" for n, p in token_spec))
        toks = []
        for m in reg.finditer(text):
            k = m.lastgroup
            if k != "WS":
                toks.append((k, m.group()))
        toks.append(("EOF", ""))
        return toks

    def _parse_stmt_list(self, toks: List[Tuple[str, str]], pos: int, stop_tokens: Set[str]) -> Tuple[List[Stmt], int]:
        stmts = []
        n = len(toks)
        while pos < n:
            k, txt = toks[pos]
            if txt in stop_tokens or k == "EOF":
                break
            stmt, next_pos = self._parse_single_stmt(toks, pos)
            if stmt:
                stmts.append(stmt)
            if next_pos <= pos:
                pos += 1
            else:
                pos = next_pos
        return stmts, pos

    def _parse_single_stmt(self, toks: List[Tuple[str, str]], pos: int) -> Tuple[Optional[Stmt], int]:
        k, txt = toks[pos]

        # 1. begin ... end block
        if txt == "begin":
            pos += 1
            stmts, next_pos = self._parse_stmt_list(toks, pos, stop_tokens={"end"})
            if next_pos < len(toks) and toks[next_pos][1] == "end":
                next_pos += 1
            if len(stmts) == 1:
                return stmts[0], next_pos
            return IfStmt("1", stmts, []), next_pos

        # 2. if (cond) then [else]
        if txt == "if":
            pos += 1
            if toks[pos][0] == "LPAREN":
                pos += 1
            # Gather condition tokens until matching RPAREN
            depth = 1
            cond_parts = []
            while pos < len(toks) and depth > 0:
                ck, ctxt = toks[pos]
                if ctxt == "(":
                    depth += 1
                elif ctxt == ")":
                    depth -= 1
                    if depth == 0:
                        pos += 1
                        break
                cond_parts.append(ctxt)
                pos += 1
            cond_str = " ".join(cond_parts)

            then_stmt, pos = self._parse_single_stmt(toks, pos)
            then_stmts = [then_stmt] if then_stmt else []

            else_stmts = []
            if pos < len(toks) and toks[pos][1] == "else":
                pos += 1
                else_stmt, pos = self._parse_single_stmt(toks, pos)
                if else_stmt:
                    else_stmts = [else_stmt]

            return IfStmt(cond_str, then_stmts, else_stmts), pos

        # 3. case (expr) ... endcase
        if txt == "case":
            pos += 1
            if toks[pos][0] == "LPAREN":
                pos += 1
            case_expr_parts = []
            while pos < len(toks) and toks[pos][1] != ")":
                case_expr_parts.append(toks[pos][1])
                pos += 1
            if pos < len(toks) and toks[pos][1] == ")":
                pos += 1
            case_expr_str = " ".join(case_expr_parts)

            branches: List[Tuple[str, List[Stmt]]] = []
            default_stmts: List[Stmt] = []

            while pos < len(toks) and toks[pos][1] != "endcase" and toks[pos][0] != "EOF":
                if toks[pos][1] == "default":
                    pos += 1
                    if pos < len(toks) and toks[pos][1] == ":":
                        pos += 1
                    d_stmt, pos = self._parse_single_stmt(toks, pos)
                    if d_stmt:
                        default_stmts.append(d_stmt)
                else:
                    val_parts = []
                    while pos < len(toks) and toks[pos][1] != ":":
                        val_parts.append(toks[pos][1])
                        pos += 1
                    if pos < len(toks) and toks[pos][1] == ":":
                        pos += 1
                    b_val_str = " ".join(val_parts)
                    b_stmt, pos = self._parse_single_stmt(toks, pos)
                    b_stmts = [b_stmt] if b_stmt else []
                    branches.append((b_val_str, b_stmts))

            if pos < len(toks) and toks[pos][1] == "endcase":
                pos += 1

            return CaseStmt(case_expr_str, branches, default_stmts), pos

        # 4. Assignment: target [bit] <= expr; OR target = expr;
        if k == "ID":
            target_name = txt
            bit_idx = None
            pos += 1

            if pos < len(toks) and toks[pos][0] == "LBRACK":
                pos += 1
                bit_idx = int(toks[pos][1])
                pos += 1
                if pos < len(toks) and toks[pos][0] == "RBRACK":
                    pos += 1

            if pos < len(toks) and toks[pos][0] in ("LE", "ASSIGN"):
                is_blocking = (toks[pos][0] == "ASSIGN")
                pos += 1
                expr_parts = []
                while pos < len(toks) and toks[pos][1] != ";" and toks[pos][0] != "EOF":
                    expr_parts.append(toks[pos][1])
                    pos += 1
                if pos < len(toks) and toks[pos][1] == ";":
                    pos += 1
                expr_str = " ".join(expr_parts)
                return AssignStmt(target_name, bit_idx, expr_str, is_blocking=is_blocking), pos

        return None, pos + 1


# ==============================================================================
# Top-Level RTL Combinational Simulator
# ==============================================================================

class RTLCombinationalSimulator:
    """Simulates the raw Verilog RTL with flip-flops removed (pure combinational cloud)."""

    def __init__(self, verilog_code: str):
        self.raw_code = verilog_code
        self.parser = VerilogProceduralParser(verilog_code)
        self.ports: Dict[str, SlicedPort] = {}
        self.registers: Dict[str, SlicedRegister] = {}
        self.assigns: List[Tuple[str, str]] = []
        self.sequential_stmts: List[Stmt] = []
        self.comb_always_stmts: List[Stmt] = []
        self._parse_module()

    def _parse_module(self):
        clean = self.parser.code

        # 1. Parse Ports
        for m in re.finditer(r"\b(input|output|inout)\s+(?:wire\s+|reg\s+)?(?:\[(\d+):(\d+)\]\s+)?([A-Za-z_][A-Za-z0-9_]*)", clean):
            dir_str = m.group(1)
            msb = int(m.group(2)) if m.group(2) else 0
            lsb = int(m.group(3)) if m.group(3) else 0
            p_name = m.group(4)
            width = abs(msb - lsb) + 1 if m.group(2) else 1
            self.ports[p_name] = SlicedPort(name=p_name, direction=dir_str, width=width, msb=msb, lsb=lsb)

        # 2. Parse Registers
        for m in re.finditer(r"\breg\s+(?:\[(\d+):(\d+)\]\s+)?([A-Za-z_][A-Za-z0-9_]*)", clean):
            msb = int(m.group(1)) if m.group(1) else 0
            lsb = int(m.group(2)) if m.group(2) else 0
            r_name = m.group(3)
            width = abs(msb - lsb) + 1 if m.group(1) else 1
            self.registers[r_name] = SlicedRegister(name=r_name, width=width, msb=msb, lsb=lsb)

        # 3. Parse continuous assigns
        for m in re.finditer(r"\bassign\s+([A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?)\s*=\s*([^;]+);", clean):
            self.assigns.append((m.group(1).strip(), m.group(2).strip()))

        # 4. Parse sequential always block (isolate active-clock body)
        seq_match = re.search(r"always\s*@\s*\(\s*(?:posedge|negedge)\s+([A-Za-z_][A-Za-z0-9_]*).*?\)\s*begin", clean, re.DOTALL)
        if seq_match:
            start_idx = seq_match.end()
            depth = 1
            i = start_idx
            n = len(clean)
            while i < n:
                if clean.startswith("begin", i) and not (clean[i-1].isalnum() or clean[i-1] == "_") and not (clean[i+5].isalnum() or clean[i+5] == "_"):
                    depth += 1
                    i += 5
                    continue
                elif clean.startswith("end", i) and not (clean[i-1].isalnum() or clean[i-1] == "_") and not (clean[i+3].isalnum() or clean[i+3] == "_"):
                    depth -= 1
                    if depth == 0:
                        break
                    i += 3
                    continue
                i += 1
            body = clean[start_idx:i]

            # Look for reset check: if (!rst_n) ... else <ACTIVE_BODY>
            else_match = re.search(r"\belse\b", body)
            if else_match:
                active_body = body[else_match.end():].strip()
                self.sequential_stmts = self.parser.parse_statements(active_body)
            else:
                self.sequential_stmts = self.parser.parse_statements(body)

            # Filter self.registers: True flip-flops are ONLY those assigned in the clocked sequential block
            seq_assigned_regs = {}
            for r_name, reg in self.registers.items():
                if re.search(rf"\b{re.escape(r_name)}\b\s*(?:\[\d+\])?\s*<=", body):
                    seq_assigned_regs[r_name] = reg
            self.registers = seq_assigned_regs

        # 5. Parse combinational always @(*) block
        comb_match = re.search(r"always\s*@\s*(?:\(\s*\*\s*\)|\*)\s*begin", clean)
        if comb_match:
            start_idx = comb_match.end()
            depth = 1
            i = start_idx
            n = len(clean)
            while i < n:
                if clean.startswith("begin", i) and not (clean[i-1].isalnum() or clean[i-1] == "_"):
                    depth += 1
                    i += 5
                    continue
                elif clean.startswith("end", i) and not (clean[i-1].isalnum() or clean[i-1] == "_"):
                    depth -= 1
                    if depth == 0:
                        break
                    i += 3
                    continue
                i += 1
            comb_body = clean[start_idx:i]
            self.comb_always_stmts = self.parser.parse_statements(comb_body)

    @property
    def primary_inputs(self) -> List[str]:
        inputs = []
        for p in self.ports.values():
            if p.direction in ("input", "inout") and p.name not in ("clk", "rst_n", "rst", "reset"):
                inputs.extend(p.bit_names)
        return inputs

    @property
    def register_q_bits(self) -> List[str]:
        bits = []
        for r in self.registers.values():
            bits.extend(r.bit_names)
        return bits

    @property
    def check_signals(self) -> List[str]:
        """All signals that must be compared: Primary Outputs and Register next-states (D)."""
        sigs = []
        for p in self.ports.values():
            if p.direction in ("output", "inout"):
                sigs.extend(p.bit_names)
        for r in self.registers.values():
            for b in r.bit_names:
                sigs.append(f"{b}_d")
        return sigs

    def simulate_vector(self, stimulus: Dict[str, int]) -> Dict[str, int]:
        """Simulates one input stimulus vector with FFs cut, returning all D next-states and Y outputs."""
        env = dict(stimulus)

        # Populate vector-level integers for registers
        for r_name, reg in self.registers.items():
            if reg.width == 1:
                val = stimulus.get(r_name, 0)
                env[r_name] = val
                env[f"{r_name}[0]"] = val
            else:
                val = 0
                for b in range(reg.width):
                    val |= (stimulus.get(f"{r_name}[{b}]", 0) << b)
                env[r_name] = val

        # Populate vector-level integers for input ports
        for p_name, port in self.ports.items():
            if port.direction == "input" and port.width > 1:
                val = 0
                for b in range(port.width):
                    val |= (stimulus.get(f"{p_name}[{b}]", 0) << b)
                env[p_name] = val

        # 1. Combinational always block execution (updates wires / intermediate nets)
        comb_env = dict(env)
        for s in self.comb_always_stmts:
            s.execute(comb_env, comb_env)

        # 2. Continuous assigns execution (driven by X and Q, updates primary outputs / wires)
        for lhs, rhs in self.assigns:
            val = VerilogExprEvaluator(rhs).evaluate(comb_env)
            comb_env[lhs] = val
            for p_name, port in self.ports.items():
                if port.name == lhs and port.width > 1:
                    for b in range(port.width):
                        comb_env[f"{lhs}[{b}]"] = (val >> b) & 1

        # 3. Sequential block execution:
        # Default rule of flip-flops: next-state D holds current state Q unless assigned!
        next_env = dict(env)
        for s in self.sequential_stmts:
            s.execute(comb_env, next_env)

        # 4. Collect outputs
        results: Dict[str, int] = {}

        # Primary outputs (come from comb_env)
        for p_name, port in self.ports.items():
            if port.direction in ("output", "inout"):
                if port.width == 1:
                    results[p_name] = comb_env.get(p_name, 0)
                else:
                    for b in range(port.width):
                        bit_name = f"{p_name}[{b}]"
                        if bit_name in comb_env:
                            results[bit_name] = comb_env[bit_name]
                        else:
                            vec_val = comb_env.get(p_name, 0)
                            results[bit_name] = (vec_val >> b) & 1

        # Register next states (D, come from next_env)
        for r_name, reg in self.registers.items():
            if reg.width == 1:
                d_name = f"{r_name}_d"
                results[d_name] = next_env.get(r_name, 0)
            else:
                for b in range(reg.width):
                    d_name = f"{r_name}[{b}]_d"
                    bit_name = f"{r_name}[{b}]"
                    if bit_name in next_env:
                        results[d_name] = next_env[bit_name]
                    else:
                        vec_val = next_env.get(r_name, 0)
                        results[d_name] = (vec_val >> b) & 1

        return results

    def simulate_all_vectors(self, max_vectors: int = 16384) -> Tuple[List[str], List[Dict[str, int]], Dict[str, List[int]]]:
        """Sweeps all 2^k input combinations to generate golden reference arrays."""
        stimulus_vars = self.primary_inputs + self.register_q_bits
        k = len(stimulus_vars)
        total_vectors = 1 << k
        if total_vectors > max_vectors:
            total_vectors = max_vectors

        vectors: List[Dict[str, int]] = []
        golden_arrays: Dict[str, List[int]] = {sig: [] for sig in self.check_signals}

        for vec_idx in range(total_vectors):
            inp = {}
            for bit_i in range(k):
                inp[stimulus_vars[bit_i]] = (vec_idx >> bit_i) & 1
            vectors.append(inp)
            out = self.simulate_vector(inp)
            for sig in self.check_signals:
                golden_arrays[sig].append(out.get(sig, 0))

        return stimulus_vars, vectors, golden_arrays
