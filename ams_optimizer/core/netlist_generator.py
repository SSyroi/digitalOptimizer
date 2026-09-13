"""Structural Logical Netlist Generator.

Generates a clean intermediate structural gate-level netlist (devices, pin connections,
transistor costs, inverter equivalents) that can be saved to JSON/Verilog and reused
by downstream schematic placers and routers before Verilog-A code generation.

Zero external dependencies. Compatible with Python 3.9+.
"""

from __future__ import annotations
import json
import re
from typing import Dict, List, Set

from .models import (
    SlicedDAG,
    MappedLogicNode,
    GateInstance,
    StructuralNetlist,
    TRANSISTOR_COST,
    INVERTER_EQUIVALENTS,
)


class StructuralNetlistGenerator:
    """Constructs the intermediate structural gate netlist from mapped DAG nodes."""

    def __init__(self, dag: SlicedDAG, mapped_nodes: Dict[str, MappedLogicNode]):
        self.dag = dag
        self.mapped_nodes = mapped_nodes

    def _split_args(self, arg_str: str) -> List[str]:
        args = []
        current = []
        depth = 0
        for char in arg_str:
            if char == "(":
                depth += 1
                current.append(char)
            elif char == ")":
                depth -= 1
                current.append(char)
            elif char == "," and depth == 0:
                args.append("".join(current).strip())
                current = []
            else:
                current.append(char)
        if current:
            args.append("".join(current).strip())
        return [a for a in args if a]

    def generate(self) -> StructuralNetlist:
        instances: List[GateInstance] = []
        inst_idx = 1
        subexpr_cache: Dict[str, str] = {}  # canonical_key -> net_name
        net_aliases: Dict[str, str] = {}    # alias -> real_net

        # 1. Instantiate Sequential Register Flops (DFFS for preset, DFFR for reset)
        for r_name, reg in self.dag.registers.items():
            if reg.reset_signal:
                cell_type = "DFFS" if reg.reset_val != 0 else "DFFR"
            else:
                cell_type = "DFF"

            for bit_i in range(reg.width):
                b_name = f"{r_name}[{bit_i}]" if reg.width > 1 else r_name
                d_net = f"{b_name}_d"
                q_net = b_name

                pin_conns = {
                    "CLK": reg.clock_signal,
                    "D": d_net,
                    "Q": q_net,
                }
                if reg.reset_signal:
                    if cell_type == "DFFS":
                        pin_conns["SN" if reg.is_active_low_reset else "S"] = reg.reset_signal
                    else:
                        pin_conns["RN" if reg.is_active_low_reset else "R"] = reg.reset_signal

                instances.append(GateInstance(
                    instance_name=f"U_REG_{r_name}_{bit_i}",
                    cell_type=cell_type,
                    pin_connections=pin_conns,
                    level=0,
                    inverter_equivalent=INVERTER_EQUIVALENTS.get(cell_type, 17.0),
                    transistors=TRANSISTOR_COST.get(cell_type, 34)
                ))

        commutative_cells = {
            "NAND2", "NAND3", "NAND4", "NOR2", "NOR3", "NOR4",
            "AND2", "AND3", "AND4", "OR2", "OR3", "OR4",
            "XOR2", "XNOR2"
        }

        def get_resolved_net(n: str) -> str:
            visited = set()
            while n in net_aliases and n not in visited:
                visited.add(n)
                n = net_aliases[n]
            return n

        # Helper to recursively instantiate gate trees with Global Cross-Cone CSE
        def instantiate_expr(expr: str, target_net: Optional[str] = None, level: int = 1) -> str:
            nonlocal inst_idx
            expr = expr.strip()
            gate_match = re.match(r"^([A-Z0-9]+)\((.*)\)$", expr)
            if not gate_match:
                resolved = get_resolved_net(expr)
                if target_net and target_net != resolved:
                    net_aliases[target_net] = resolved
                return resolved

            cell = gate_match.group(1)
            raw_args = self._split_args(gate_match.group(2))

            # Recursively instantiate each input argument
            resolved_in_nets: List[str] = []
            for arg in raw_args:
                in_net = instantiate_expr(arg, None, level + 1)
                resolved_in_nets.append(get_resolved_net(in_net))

            # Build canonical key for CSE deduplication
            if cell in commutative_cells:
                canonical_key = f"{cell}({', '.join(sorted(resolved_in_nets))})"
            elif cell == "AOI21":
                sorted_ab = sorted([resolved_in_nets[0], resolved_in_nets[1]])
                canonical_key = f"AOI21({sorted_ab[0]}, {sorted_ab[1]}, {resolved_in_nets[2]})"
            elif cell == "AOI22":
                p1 = tuple(sorted([resolved_in_nets[0], resolved_in_nets[1]]))
                p2 = tuple(sorted([resolved_in_nets[2], resolved_in_nets[3]]))
                sp = sorted([p1, p2])
                canonical_key = f"AOI22({sp[0][0]}, {sp[0][1]}, {sp[1][0]}, {sp[1][1]})"
            elif cell == "OAI21":
                sorted_ab = sorted([resolved_in_nets[0], resolved_in_nets[1]])
                canonical_key = f"OAI21({sorted_ab[0]}, {sorted_ab[1]}, {resolved_in_nets[2]})"
            elif cell == "OAI22":
                p1 = tuple(sorted([resolved_in_nets[0], resolved_in_nets[1]]))
                p2 = tuple(sorted([resolved_in_nets[2], resolved_in_nets[3]]))
                sp = sorted([p1, p2])
                canonical_key = f"OAI22({sp[0][0]}, {sp[0][1]}, {sp[1][0]}, {sp[1][1]})"
            elif cell == "INV":
                canonical_key = f"INV({resolved_in_nets[0]})"
            elif cell == "MUX2":
                canonical_key = f"MUX2({resolved_in_nets[0]}, {resolved_in_nets[1]}, {resolved_in_nets[2]})"
            else:
                canonical_key = f"{cell}({', '.join(resolved_in_nets)})"

            # Check if this exact gate was already synthesized in another cone
            if canonical_key in subexpr_cache:
                existing_net = subexpr_cache[canonical_key]
                if target_net and target_net != existing_net:
                    net_aliases[target_net] = existing_net
                return existing_net

            # Not cached: allocate output net and instantiate gate
            out_net = target_net if target_net else f"n_{inst_idx}_{cell.lower()}"

            pin_conns: Dict[str, str] = {}
            if cell == "INV":
                pin_conns = {"A": resolved_in_nets[0], "Y": out_net}
            elif cell in ("NAND2", "NOR2", "AND2", "OR2", "XOR2", "XNOR2"):
                pin_conns = {
                    "A": resolved_in_nets[0] if len(resolved_in_nets) > 0 else "1.0",
                    "B": resolved_in_nets[1] if len(resolved_in_nets) > 1 else "1.0",
                    "Y": out_net
                }
            elif cell in ("NAND3", "NOR3", "AND3", "OR3"):
                pin_conns = {
                    "A": resolved_in_nets[0] if len(resolved_in_nets) > 0 else "1.0",
                    "B": resolved_in_nets[1] if len(resolved_in_nets) > 1 else "1.0",
                    "C": resolved_in_nets[2] if len(resolved_in_nets) > 2 else "1.0",
                    "Y": out_net
                }
            elif cell in ("NAND4", "AND4", "NOR4", "OR4"):
                pin_conns = {
                    "A": resolved_in_nets[0] if len(resolved_in_nets) > 0 else "1.0",
                    "B": resolved_in_nets[1] if len(resolved_in_nets) > 1 else "1.0",
                    "C": resolved_in_nets[2] if len(resolved_in_nets) > 2 else "1.0",
                    "D": resolved_in_nets[3] if len(resolved_in_nets) > 3 else "1.0",
                    "Y": out_net
                }
            elif cell == "MUX2":
                pin_conns = {
                    "S": resolved_in_nets[0] if len(resolved_in_nets) > 0 else "0.0",
                    "D0": resolved_in_nets[1] if len(resolved_in_nets) > 1 else "0.0",
                    "D1": resolved_in_nets[2] if len(resolved_in_nets) > 2 else "0.0",
                    "Y": out_net
                }
            elif cell in ("AOI21", "OAI21"):
                pin_conns = {
                    "A": resolved_in_nets[0] if len(resolved_in_nets) > 0 else "1.0",
                    "B": resolved_in_nets[1] if len(resolved_in_nets) > 1 else "1.0",
                    "C": resolved_in_nets[2] if len(resolved_in_nets) > 2 else "1.0",
                    "Y": out_net
                }
            elif cell in ("AOI22", "OAI22"):
                pin_conns = {
                    "A": resolved_in_nets[0] if len(resolved_in_nets) > 0 else "1.0",
                    "B": resolved_in_nets[1] if len(resolved_in_nets) > 1 else "1.0",
                    "C": resolved_in_nets[2] if len(resolved_in_nets) > 2 else "1.0",
                    "D": resolved_in_nets[3] if len(resolved_in_nets) > 3 else "1.0",
                    "Y": out_net
                }
            else:
                pin_conns = {"Y": out_net}
                for i, net in enumerate(resolved_in_nets):
                    pin_conns[f"IN{i}"] = net

            safe_name = out_net.replace("[", "_").replace("]", "").replace(".", "_")
            instances.append(GateInstance(
                instance_name=f"U_COMB_{inst_idx}_{safe_name}_{cell}",
                cell_type=cell,
                pin_connections=pin_conns,
                level=level,
                inverter_equivalent=INVERTER_EQUIVALENTS.get(cell, 2.0),
                transistors=TRANSISTOR_COST.get(cell, 4)
            ))
            subexpr_cache[canonical_key] = out_net
            inst_idx += 1
            return out_net

        # 2. Instantiate Combinational Logic Gates from Mapped Nodes
        for node_name in self.dag.topo_order:
            mn = self.mapped_nodes.get(node_name)
            if not mn or mn.expression in ("0.0", "1.0"):
                continue

            node_obj = self.dag.nodes.get(node_name)
            level = node_obj.level if node_obj else 1
            instantiate_expr(mn.expression, node_name, level)

        # 3. Handle primary outputs that were aliased to existing internal nets
        for po in self.dag.primary_outputs:
            if po in net_aliases:
                real_src = get_resolved_net(po)
                po_driven = any(inst.pin_connections.get("Y") == po for inst in instances)
                if not po_driven:
                    instances.append(GateInstance(
                        instance_name=f"U_BUF_{po.replace('[', '_').replace(']', '')}",
                        cell_type="BUFFER",
                        pin_connections={"A": real_src, "Y": po},
                        level=1,
                        inverter_equivalent=INVERTER_EQUIVALENTS.get("BUFFER", 2.0),
                        transistors=TRANSISTOR_COST.get("BUFFER", 4)
                    ))

        # Calculate totals
        total_gates = len(instances)
        total_ge = sum(inst.inverter_equivalent for inst in instances)
        total_tr = sum(inst.transistors for inst in instances)

        ports_dict = {
            p.name: {"direction": p.direction, "width": str(p.width), "bits": p.bit_names}
            for p in self.dag.ports.values()
        }

        return StructuralNetlist(
            module_name=self.dag.module_name,
            ports=ports_dict,
            instances=instances,
            total_gates=total_gates,
            total_inverter_equivalents=total_ge,
            total_transistors=total_tr
        )

    @staticmethod
    def to_json_str(netlist: StructuralNetlist) -> str:
        """Serializes the structural netlist to a formatted JSON string."""
        data = {
            "module_name": netlist.module_name,
            "summary": {
                "total_gates": netlist.total_gates,
                "total_inverter_equivalents_ge": netlist.total_inverter_equivalents,
                "total_transistors": netlist.total_transistors,
                "inverter_definition": "1 GE = 1 Inverter = 2 Transistors",
            },
            "ports": netlist.ports,
            "instances": [
                {
                    "name": inst.instance_name,
                    "cell_type": inst.cell_type,
                    "connections": inst.pin_connections,
                    "level": inst.level,
                    "inverter_equivalent_ge": inst.inverter_equivalent,
                    "transistors": inst.transistors,
                }
                for inst in netlist.instances
            ]
        }
        return json.dumps(data, indent=2)
