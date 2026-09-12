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
        inv_cache: Dict[str, str] = {}  # net_name -> inverted_net_name

        # 1. Instantiate Sequential Register Flops
        for r_name, reg in self.dag.registers.items():
            cell_type = "DFFR" if reg.reset_signal else "DFF"
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
                    pin_conns["RN" if reg.is_active_low_reset else "R"] = reg.reset_signal

                instances.append(GateInstance(
                    instance_name=f"U_REG_{r_name}_{bit_i}",
                    cell_type=cell_type,
                    pin_connections=pin_conns,
                    level=0,
                    inverter_equivalent=INVERTER_EQUIVALENTS.get(cell_type, 8.0),
                    transistors=TRANSISTOR_COST.get(cell_type, 16)
                ))

        # Helper to recursively instantiate gate trees
        def instantiate_expr(expr: str, target_net: str, level: int) -> str:
            nonlocal inst_idx
            expr = expr.strip()
            gate_match = re.match(r"^([A-Z0-9]+)\((.*)\)$", expr)
            if not gate_match:
                return expr

            cell = gate_match.group(1)
            raw_args = self._split_args(gate_match.group(2))

            # Shared inverter optimization
            if cell == "INV" and len(raw_args) == 1 and not re.match(r"^[A-Z0-9]+\(.*\)$", raw_args[0]):
                in_sig = raw_args[0]
                if in_sig in inv_cache and target_net != inv_cache[in_sig]:
                    return inv_cache[in_sig]

            resolved_in_nets: List[str] = []
            for arg_i, arg in enumerate(raw_args):
                if re.match(r"^[A-Z0-9]+\(.*\)$", arg):
                    sub_net = f"n_{inst_idx}_{arg[:arg.find('(')].lower()}"
                    instantiate_expr(arg, sub_net, level + 1)
                    resolved_in_nets.append(sub_net)
                else:
                    resolved_in_nets.append(arg)

            pin_conns: Dict[str, str] = {}
            if cell == "INV":
                pin_conns = {"A": resolved_in_nets[0], "Y": target_net}
                if len(raw_args) == 1 and not re.match(r"^[A-Z0-9]+\(.*\)$", raw_args[0]):
                    inv_cache[raw_args[0]] = target_net
            elif cell in ("NAND2", "NOR2", "AND2", "OR2", "XOR2", "XNOR2"):
                pin_conns = {
                    "A": resolved_in_nets[0] if len(resolved_in_nets) > 0 else "1.0",
                    "B": resolved_in_nets[1] if len(resolved_in_nets) > 1 else "1.0",
                    "Y": target_net
                }
            elif cell in ("NAND3", "NOR3", "AND3", "OR3"):
                pin_conns = {
                    "A": resolved_in_nets[0] if len(resolved_in_nets) > 0 else "1.0",
                    "B": resolved_in_nets[1] if len(resolved_in_nets) > 1 else "1.0",
                    "C": resolved_in_nets[2] if len(resolved_in_nets) > 2 else "1.0",
                    "Y": target_net
                }
            elif cell in ("NAND4", "AND4", "NOR4", "OR4"):
                pin_conns = {
                    "A": resolved_in_nets[0] if len(resolved_in_nets) > 0 else "1.0",
                    "B": resolved_in_nets[1] if len(resolved_in_nets) > 1 else "1.0",
                    "C": resolved_in_nets[2] if len(resolved_in_nets) > 2 else "1.0",
                    "D": resolved_in_nets[3] if len(resolved_in_nets) > 3 else "1.0",
                    "Y": target_net
                }
            elif cell == "MUX2":
                pin_conns = {
                    "S": resolved_in_nets[0] if len(resolved_in_nets) > 0 else "0.0",
                    "D0": resolved_in_nets[1] if len(resolved_in_nets) > 1 else "0.0",
                    "D1": resolved_in_nets[2] if len(resolved_in_nets) > 2 else "0.0",
                    "Y": target_net
                }
            elif cell in ("AOI21", "OAI21"):
                pin_conns = {
                    "A": resolved_in_nets[0] if len(resolved_in_nets) > 0 else "1.0",
                    "B": resolved_in_nets[1] if len(resolved_in_nets) > 1 else "1.0",
                    "C": resolved_in_nets[2] if len(resolved_in_nets) > 2 else "1.0",
                    "Y": target_net
                }
            else:
                pin_conns = {"Y": target_net}
                for i, net in enumerate(resolved_in_nets):
                    pin_conns[f"IN{i}"] = net

            safe_name = target_net.replace("[", "_").replace("]", "").replace(".", "_")
            instances.append(GateInstance(
                instance_name=f"U_COMB_{inst_idx}_{safe_name}_{cell}",
                cell_type=cell,
                pin_connections=pin_conns,
                level=level,
                inverter_equivalent=INVERTER_EQUIVALENTS.get(cell, 2.0),
                transistors=TRANSISTOR_COST.get(cell, 4)
            ))
            inst_idx += 1
            return target_net

        # 2. Instantiate Combinational Logic Gates from Mapped Nodes
        for node_name in self.dag.topo_order:
            mn = self.mapped_nodes.get(node_name)
            if not mn or mn.expression in ("0.0", "1.0"):
                continue

            node_obj = self.dag.nodes.get(node_name)
            level = node_obj.level if node_obj else 1
            instantiate_expr(mn.expression, node_name, level)

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
