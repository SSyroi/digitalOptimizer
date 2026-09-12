"""Schematic Wiring Guide, Cadence Virtuoso SKILL, and SPICE/CDL Emitters."""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple
from .ast_parser import ParsedModule
from .library import Library
from .synthesizer import LogicNode, SynthesizedCone

@dataclass
class SchematicInstance:
    inst_name: str
    cell_type: str
    pin_connections: Dict[str, str]  # PinName -> NetName
    is_sequential: bool = False


class SchematicEmitter:
    """Generates schematic wiring documentation, Cadence Virtuoso SKILL scripts, and SPICE netlists."""

    def __init__(self, library: Library):
        self.library = library

    def extract_schematic_instances(
        self,
        parsed: ParsedModule,
        cones: Dict[str, SynthesizedCone],
    ) -> List[SchematicInstance]:
        """Flatten logic cones and registers into discrete standard cell instances and nets."""
        instances: List[SchematicInstance] = []
        inst_counter: Dict[str, int] = {}
        net_counter = 0

        # 1. Instantiate Sequential DFFs
        for reg in parsed.registers:
            dff_type = "DFFR" if reg.rst_signal else "DFF"
            count = inst_counter.get(dff_type, 0) + 1
            inst_counter[dff_type] = count
            inst_name = f"I_DFF_{self._sanitize(reg.name)}"

            pins = {
                "CLK": reg.clk_signal,
                "D": f"net_d_{self._sanitize(reg.name)}",
                "Q": reg.name,
            }
            if reg.rst_signal:
                pins["RST_N" if reg.rst_active_low else "RST"] = reg.rst_signal

            instances.append(SchematicInstance(inst_name=inst_name, cell_type=dff_type, pin_connections=pins, is_sequential=True))

        # 2. Instantiate Combinational Logic Trees
        for target, cone in cones.items():
            out_net = f"net_d_{self._sanitize(target)}" if any(r.name == target for r in parsed.registers) else target
            self._instantiate_node(cone.root, out_net, instances, inst_counter)

        return instances

    def _instantiate_node(
        self,
        node: LogicNode,
        out_net: str,
        instances: List[SchematicInstance],
        inst_counter: Dict[str, int],
    ):
        if node.gate_type == "WIRE":
            return

        gtype = node.gate_type
        count = inst_counter.get(gtype, 0) + 1
        inst_counter[gtype] = count
        inst_name = f"I_{gtype}_{count}"

        cell = self.library.get_cell(gtype)
        pin_names = cell.inputs if cell else [f"IN{i}" for i in range(len(node.inputs))]
        out_pin = cell.output if cell else "Y"

        pins: Dict[str, str] = {out_pin: out_net}

        for idx, inp in enumerate(node.inputs):
            pin_name = pin_names[idx] if idx < len(pin_names) else f"IN{idx}"
            if isinstance(inp, str):
                pins[pin_name] = inp
            elif isinstance(inp, LogicNode):
                # Generate intermediate net name
                sub_net = f"net_{gtype.lower()}_{count}_in{idx}"
                pins[pin_name] = sub_net
                self._instantiate_node(inp, sub_net, instances, inst_counter)

        instances.append(SchematicInstance(inst_name=inst_name, cell_type=gtype, pin_connections=pins))

    def generate_markdown_report(
        self,
        parsed: ParsedModule,
        instances: List[SchematicInstance],
    ) -> str:
        """Generate human-readable schematic bill of materials & wiring guide."""
        lines: List[str] = []
        lines.append(f"# Schematic Bill of Materials & Wiring Guide: `{parsed.name}`\n")

        # BOM Summary
        lines.append("## 1. Bill of Materials (BOM)")
        bom: Dict[str, int] = {}
        for inst in instances:
            bom[inst.cell_type] = bom.get(inst.cell_type, 0) + 1

        lines.append("| Cell Name | Category | Count | Total Transistors |")
        lines.append("| :--- | :--- | :--- | :--- |")
        total_transistors = 0
        for cell_name, count in sorted(bom.items()):
            cell = self.library.get_cell(cell_name)
            cost = cell.cost if cell else 4
            tot_t = cost * count
            total_transistors += tot_t
            cat = "Sequential" if (cell and cell.cell_type == "sequential") else "Combinational"
            lines.append(f"| `{cell_name}` | {cat} | {count} | ~{tot_t} |")
        lines.append(f"| **TOTAL** | | **{len(instances)} instances** | **~{total_transistors} transistors** |\n")

        # Instance Wiring Table
        lines.append("## 2. Gate-by-Gate Schematic Wiring Table")
        lines.append("| Instance | Cell | Pin Connections |")
        lines.append("| :--- | :--- | :--- |")
        for inst in instances:
            conns = ", ".join([f"**{p}** $\\rightarrow$ `{n}`" for p, n in inst.pin_connections.items()])
            lines.append(f"| `{inst.inst_name}` | `{inst.cell_type}` | {conns} |")

        return "\n".join(lines)

    def generate_cadence_skill(
        self,
        parsed: ParsedModule,
        instances: List[SchematicInstance],
        target_lib: str = "MY_AMS_LIB",
    ) -> str:
        """Generate Cadence Virtuoso SKILL script for automated schematic construction."""
        lines: List[str] = []
        lines.append(f";; =============================================================================")
        lines.append(f";; Cadence Virtuoso SKILL Script for Module: {parsed.name}")
        lines.append(f";; Auto-generated by AMS Digital Optimizer")
        lines.append(f";; =============================================================================")
        lines.append(f"cv = dbOpenCellViewByType(\"{target_lib}\" \"{parsed.name}\" \"schematic\" \"schematic\" \"w\")")
        lines.append("if( cv then")
        lines.append("  printf(\"Creating schematic for %s\\n\" cv~>cellName)")
        lines.append("")

        for idx, inst in enumerate(instances):
            x = (idx % 6) * 2.5
            y = (idx // 6) * 2.0
            lines.append(f"  ;; Instance {inst.inst_name} ({inst.cell_type})")
            lines.append(f"  inst = dbCreateParamInstByMasterName(cv \"{target_lib}\" \"{inst.cell_type}\" \"symbol\" \"{inst.inst_name}\" list({x:.2f} {y:.2f}) \"R0\" 1)")
            for pin, net in inst.pin_connections.items():
                lines.append(f"  ;; Connect pin {pin} -> net {net}")

        lines.append("")
        lines.append("  schCheck(cv)")
        lines.append("  dbSave(cv)")
        lines.append("  dbClose(cv)")
        lines.append("  printf(\"Schematic generated successfully!\\n\")")
        lines.append(")")
        return "\n".join(lines)

    def generate_spice_netlist(
        self,
        parsed: ParsedModule,
        instances: List[SchematicInstance],
    ) -> str:
        """Generate CDL/SPICE subcircuit netlist."""
        lines: List[str] = []
        ports_str = " ".join(parsed.ports.keys())
        lines.append(f"* CDL / SPICE Gate-Level Netlist for: {parsed.name}")
        lines.append(f".SUBCKT {parsed.name} {ports_str} VDD VSS")
        lines.append("")

        for inst in instances:
            # Format: X<inst_name> <pin1_net> <pin2_net> ... <cell_type>
            pin_nets = " ".join(inst.pin_connections.values())
            lines.append(f"X{inst.inst_name} {pin_nets} VDD VSS {inst.cell_type}")

        lines.append("")
        lines.append(f".ENDS {parsed.name}")
        return "\n".join(lines)

    def _sanitize(self, name: str) -> str:
        return re.sub(r"[\[\]]", "_", name).strip("_")
