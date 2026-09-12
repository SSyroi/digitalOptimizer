"""Master Synthesis Pipeline for Simulation-Driven Truth Table Synthesis.

Includes automatic Support-Set Variable Pruning & Exact Quine-McCluskey Minimization.
Compatible with Python 3.9+. Zero external dependencies.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .slicer import VerilogSlicer, SlicedModule
from .sim_engine import SimulationEngine, TruthTable
from .quine_mccluskey import minimize_truth_table
from .cmos_mapper import CMOSMapper, MappedCone
from .veriloga_emitter import VerilogAEmitter


@dataclass
class SimOptimizationResult:
    module: SlicedModule
    truth_table: TruthTable
    mapped_cones: Dict[str, MappedCone]
    veriloga_code: str
    total_gates: int
    total_transistors: int
    gate_breakdown: Dict[str, int]
    bom_report: str


class SimTruthTableOptimizer:
    """End-to-end Simulation-Driven Truth Table Optimizer."""

    def __init__(self, supply_voltage: float = 1.8, threshold_voltage: float = 0.9):
        self.vdd = supply_voltage
        self.vth = threshold_voltage
        self.mapper = CMOSMapper()
        self.va_emitter = VerilogAEmitter(supply_voltage=supply_voltage, threshold_voltage=threshold_voltage)

    def run(self, verilog_code: str) -> SimOptimizationResult:
        # 1. Slice RTL into Inputs (X, Q) and Outputs (D, Y)
        slicer = VerilogSlicer(verilog_code)
        mod = slicer.slice()

        # 2. Exhaustive Simulation -> Truth Table
        sim = SimulationEngine(mod, verilog_code)
        tt = sim.generate_truth_table()

        # 3. Exact Quine-McCluskey Minimization & CMOS Mapping for each cone
        mapped_cones: Dict[str, MappedCone] = {}
        used_gates: Set[str] = set()
        gate_breakdown: Dict[str, int] = {}
        total_transistors = 0

        for out_name in tt.output_names:
            minterms = tt.true_minterms.get(out_name, [])
            
            # Prune independent variables (Support Set Reduction)
            active_vars, projected_minterms = self._prune_support_set(
                tt.num_inputs, tt.input_names, minterms
            )

            if len(projected_minterms) == 0:
                cone = MappedCone(target=out_name, nested_expression="0.0", gate_counts={}, transistor_cost=0)
            elif len(projected_minterms) == (1 << len(active_vars)):
                cone = MappedCone(target=out_name, nested_expression="1.0", gate_counts={}, transistor_cost=0)
            else:
                pis, ftype = minimize_truth_table(len(active_vars), projected_minterms, [])
                cone = self.mapper.map_implicants_to_cmos(out_name, pis, active_vars, ftype)

            mapped_cones[out_name] = cone

            for g, cnt in cone.gate_counts.items():
                gate_breakdown[g] = gate_breakdown.get(g, 0) + cnt
                used_gates.add(g)

        # Add sequential register costs
        for reg in mod.registers:
            dff_name = "DFFR" if reg.rst_signal else "DFF"
            gate_breakdown[dff_name] = gate_breakdown.get(dff_name, 0) + 1
            used_gates.add(dff_name)

        # 4. Emit Cadence Spectre Verilog-A Code
        va_code = self.va_emitter.emit(mod, mapped_cones, used_gates)

        # 5. Generate BOM Report
        total_gates = sum(gate_breakdown.values())
        for g, cnt in gate_breakdown.items():
            cost = 18 if g.startswith("DFF") else self.mapper.CELL_COSTS.get(g, 4)
            total_transistors += cost * cnt

        bom_lines = [
            f"# Schematic Bill of Materials: {mod.module_name}",
            f"- Total Standard Cell Gates: **{total_gates}**",
            f"- Estimated Transistor Footprint: **~{total_transistors} Transistors**",
            "",
            "| Cell Type | Count | Transistors / Cell | Total Transistors |",
            "| :--- | :---: | :---: | :---: |",
        ]
        for g, cnt in sorted(gate_breakdown.items()):
            cost = 18 if g.startswith("DFF") else self.mapper.CELL_COSTS.get(g, 4)
            bom_lines.append(f"| {g} | {cnt} | ~{cost} | ~{cost * cnt} |")
        bom_report = "\n".join(bom_lines)

        return SimOptimizationResult(
            module=mod,
            truth_table=tt,
            mapped_cones=mapped_cones,
            veriloga_code=va_code,
            total_gates=total_gates,
            total_transistors=total_transistors,
            gate_breakdown=gate_breakdown,
            bom_report=bom_report,
        )

    def _prune_support_set(
        self,
        num_vars: int,
        var_names: List[str],
        minterms: List[int],
    ) -> Tuple[List[str], List[int]]:
        """Identify which variables actually affect the output and project truth table onto active variables."""
        if not minterms:
            return [], []
        if len(minterms) == (1 << num_vars):
            return [], [0]

        minterm_set = set(minterms)
        active_var_indices = []

        for i in range(num_vars):
            # Check if toggling variable i ever changes the output
            depends = False
            for m in minterm_set:
                flipped = m ^ (1 << i)
                if flipped not in minterm_set:
                    depends = True
                    break
            if depends:
                active_var_indices.append(i)

        if not active_var_indices:
            return [], [0]

        active_var_names = [var_names[i] for i in active_var_indices]

        # Project minterm integers onto active variables
        projected_set = set()
        for m in minterm_set:
            proj_m = 0
            for new_idx, old_idx in enumerate(active_var_indices):
                bit = (m >> old_idx) & 1
                proj_m |= (bit << new_idx)
            projected_set.add(proj_m)

        return active_var_names, sorted(list(projected_set))
