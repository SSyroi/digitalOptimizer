"""Unified Optimization Pipeline for AMS Digital Blocks."""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
import sympy
from sympy.logic.boolalg import Boolean
from .ast_parser import VerilogParser, ParsedModule
from .library import Library, load_default_library
from .synthesizer import LogicSynthesizer, SynthesizedCone
from .tree_collapser import TreeCollapser, CollapsedExpression
from .veriloga_emitter import VerilogAEmitter
from .schematic_emitter import SchematicEmitter, SchematicInstance
from .verifier import LogicVerifier, EquivalenceResult

@dataclass
class OptimizationResult:
    parsed_module: ParsedModule
    library: Library
    register_expressions: Dict[str, CollapsedExpression] = field(default_factory=dict)
    output_expressions: Dict[str, CollapsedExpression] = field(default_factory=dict)
    veriloga_code: str = ""
    schematic_report: str = ""
    skill_script: str = ""
    spice_netlist: str = ""
    verification: Optional[EquivalenceResult] = None
    schematic_instances: List[SchematicInstance] = field(default_factory=list)
    total_gates: int = 0
    total_transistors: int = 0
    gate_breakdown: Dict[str, int] = field(default_factory=dict)


class OptimizerPipeline:
    """End-to-end synthesizer and optimizer pipeline for AMS digital blocks."""

    def __init__(self, library: Optional[Library] = None):
        self.library = library or load_default_library()
        self.synthesizer = LogicSynthesizer(self.library)
        self.collapser = TreeCollapser()
        self.va_emitter = VerilogAEmitter(self.library)
        self.schem_emitter = SchematicEmitter(self.library)
        self.verifier = LogicVerifier(self.library)

    def run(self, verilog_code: str, virtuoso_lib: str = "MY_AMS_LIB") -> OptimizationResult:
        """Run the full optimization, code generation, schematic mapping, and verification flow."""
        # 1. Parse Verilog RTL & Extract State
        parser = VerilogParser(verilog_code)
        parsed = parser.parse()

        # 2. Inline intermediate combinational wires to eliminate unresolved symbols
        self._inline_intermediate_wires(parsed)

        # 3. Synthesize Combinational Logic Cones
        cones: Dict[str, SynthesizedCone] = {}
        used_gates: Set[str] = set()
        gate_breakdown: Dict[str, int] = {}
        total_trans = 0

        # Synthesize Register D-inputs
        reg_exprs: Dict[str, CollapsedExpression] = {}
        for reg in parsed.registers:
            cone = self.synthesizer.synthesize_expression(reg.name, reg.d_expr_bool)
            cones[reg.name] = cone
            collapsed = self.collapser.collapse_cone(cone)
            reg_exprs[reg.name] = collapsed

            # Record gate statistics
            for g, cnt in cone.gate_counts.items():
                gate_breakdown[g] = gate_breakdown.get(g, 0) + cnt
                used_gates.add(g)

            # Record sequential register cost
            dff_type = "DFFR" if reg.rst_signal else "DFF"
            gate_breakdown[dff_type] = gate_breakdown.get(dff_type, 0) + 1

        # Synthesize Combinational Outputs
        out_exprs: Dict[str, CollapsedExpression] = {}
        for comb in parsed.comb_assignments:
            cone = self.synthesizer.synthesize_expression(comb.target, comb.expr_bool)
            cones[comb.target] = cone
            collapsed = self.collapser.collapse_cone(cone)
            out_exprs[comb.target] = collapsed

            for g, cnt in cone.gate_counts.items():
                gate_breakdown[g] = gate_breakdown.get(g, 0) + cnt
                used_gates.add(g)

        # 4. Formal Equivalence Verification
        verification = self.verifier.verify_module(parsed, cones)

        # 5. Generate Verilog-A Module
        va_code = self.va_emitter.emit(parsed, reg_exprs, out_exprs, used_gates)

        # 6. Generate Schematic Guides & Netlists
        instances = self.schem_emitter.extract_schematic_instances(parsed, cones)
        schem_report = self.schem_emitter.generate_markdown_report(parsed, instances)
        skill_script = self.schem_emitter.generate_cadence_skill(parsed, instances, virtuoso_lib)
        spice_netlist = self.schem_emitter.generate_spice_netlist(parsed, instances)

        # Calculate totals
        total_gates = sum(gate_breakdown.values())
        for gname, count in gate_breakdown.items():
            cell = self.library.get_cell(gname)
            cost = cell.cost if cell else 4
            total_trans += cost * count

        return OptimizationResult(
            parsed_module=parsed,
            library=self.library,
            register_expressions=reg_exprs,
            output_expressions=out_exprs,
            veriloga_code=va_code,
            schematic_report=schem_report,
            skill_script=skill_script,
            spice_netlist=spice_netlist,
            verification=verification,
            schematic_instances=instances,
            total_gates=total_gates,
            total_transistors=total_trans,
            gate_breakdown=gate_breakdown,
        )

    def _inline_intermediate_wires(self, parsed: ParsedModule):
        """Recursively inline intermediate combinational wires so logic trees only reference inputs and registers."""
        primary_in_symbols = {
            sympy.Symbol(re.sub(r"\[(\d+)\]", r"_\1_", sig))
            for sig in parsed.get_all_input_signals()
        }
        state_symbols = {
            sympy.Symbol(re.sub(r"\[(\d+)\]", r"_\1_", reg.name))
            for reg in parsed.registers
        }
        output_symbols = {
            sympy.Symbol(re.sub(r"\[(\d+)\]", r"_\1_", out_sig))
            for port in parsed.ports.values() if port.direction == "output"
            for out_sig in port.get_bit_names()
        }

        # Collect internal wire definitions
        comb_map: Dict[sympy.Symbol, Boolean] = {}
        for comb in parsed.comb_assignments:
            clean_sym = sympy.Symbol(re.sub(r"\[(\d+)\]", r"_\1_", comb.target))
            if clean_sym not in primary_in_symbols and clean_sym not in state_symbols:
                if comb.expr_bool is not None:
                    comb_map[clean_sym] = comb.expr_bool

        # Iterate to inline dependencies
        for _ in range(5):
            changed = False
            for k, v in list(comb_map.items()):
                if v is not None:
                    new_v = v.subs(comb_map)
                    if new_v != v:
                        comb_map[k] = new_v
                        changed = True
            if not changed:
                break

        # Apply inlining to registers
        for reg in parsed.registers:
            if reg.d_expr_bool is not None:
                reg.d_expr_bool = reg.d_expr_bool.subs(comb_map)

        # Apply inlining to outputs
        for comb in parsed.comb_assignments:
            if comb.expr_bool is not None:
                comb.expr_bool = comb.expr_bool.subs(comb_map)
