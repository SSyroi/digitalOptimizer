"""Unified Optimization Pipeline for AMS Digital Blocks."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
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

        # 2. Synthesize Combinational Logic Cones
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

        # 3. Formal Equivalence Verification
        verification = self.verifier.verify_module(parsed, cones)

        # 4. Generate Verilog-A Module
        va_code = self.va_emitter.emit(parsed, reg_exprs, out_exprs, used_gates)

        # 5. Generate Schematic Guides & Netlists
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
