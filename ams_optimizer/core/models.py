"""Shared Data Models and Constants for AMS Digital Optimizer.

Defines all core dataclasses for ports, registers, DAG nodes, truth tables,
mapped cells, structural netlists, and optimization deliverables.

Zero external dependencies. Compatible with Python 3.9+.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclass
class SlicedPort:
    name: str
    direction: str  # "input", "output", "inout"
    width: int = 1
    msb: int = 0
    lsb: int = 0

    @property
    def bit_names(self) -> List[str]:
        if self.width <= 1:
            return [self.name]
        step = -1 if self.msb >= self.lsb else 1
        return [f"{self.name}[{i}]" for i in range(self.msb, self.lsb + step, step)]


@dataclass
class SlicedRegister:
    name: str
    width: int = 1
    msb: int = 0
    lsb: int = 0
    clock_signal: str = "clk"
    reset_signal: str = "rst_n"
    reset_val: int = 0
    is_async_reset: bool = True
    is_active_low_reset: bool = True

    @property
    def bit_names(self) -> List[str]:
        if self.width <= 1:
            return [self.name]
        step = -1 if self.msb >= self.lsb else 1
        return [f"{self.name}[{i}]" for i in range(self.msb, self.lsb + step, step)]


@dataclass
class DAGNode:
    name: str  # e.g. "is_az_mode", "cnt_0_d", "en_LP"
    node_type: str  # "intermediate", "register_d", "primary_output"
    inputs: List[str]  # names of nets this node depends on
    eval_fn: Callable[[Dict[str, int]], int]
    level: int = 0
    raw_expr: str = ""


@dataclass
class SlicedDAG:
    module_name: str
    ports: Dict[str, SlicedPort] = field(default_factory=dict)
    wires: Dict[str, SlicedPort] = field(default_factory=dict)
    registers: Dict[str, SlicedRegister] = field(default_factory=dict)
    nodes: Dict[str, DAGNode] = field(default_factory=dict)
    topo_order: List[str] = field(default_factory=list)
    primary_inputs: List[str] = field(default_factory=list)
    primary_outputs: List[str] = field(default_factory=list)
    register_q_bits: List[str] = field(default_factory=list)
    register_d_bits: List[str] = field(default_factory=list)


@dataclass
class LocalTruthTable:
    node_name: str
    inputs: List[str]
    num_vars: int
    true_minterms: List[int]
    dont_cares: List[int] = field(default_factory=list)
    bitmask: int = 0


@dataclass
class MappedCell:
    cell_type: str  # "NAND2", "NOR2", "MUX2", "AOI21", "INV", etc.
    inputs: List[str]
    output_net: str
    expression_str: str


@dataclass
class MappedLogicNode:
    node_name: str
    expression: str
    cells_used: List[MappedCell] = field(default_factory=list)
    gate_counts: Dict[str, int] = field(default_factory=dict)


@dataclass
class GateInstance:
    instance_name: str
    cell_type: str
    pin_connections: Dict[str, str]  # e.g. {"A": "net1", "B": "net2", "Y": "out"}
    level: int = 0
    inverter_equivalent: float = 1.0
    transistors: int = 2


@dataclass
class StructuralNetlist:
    module_name: str
    ports: Dict[str, Dict[str, str]]
    instances: List[GateInstance] = field(default_factory=list)
    total_gates: int = 0
    total_inverter_equivalents: float = 0.0
    total_transistors: int = 0


@dataclass
class EquivalenceResult:
    passed: bool
    total_vectors: int
    matching_vectors: int
    verified_signals: List[str]
    mismatches: List[Dict[str, Any]] = field(default_factory=list)
    execution_time_seconds: float = 0.0
    notes: str = ""


@dataclass
class OptimizationResult:
    module_name: str
    dag: SlicedDAG
    mapped_nodes: Dict[str, MappedLogicNode]
    structural_netlist: StructuralNetlist
    veriloga_code: str
    skill_code: str
    bom_report: str
    gate_breakdown: Dict[str, int] = field(default_factory=dict)
    total_gates: int = 0
    total_inverter_equivalents: float = 0.0
    total_transistors: int = 0
    equivalence_result: Optional[EquivalenceResult] = None
    timing_breakdown: Dict[str, float] = field(default_factory=dict)


# Physical transistor cost per CMOS standard cell
TRANSISTOR_COST = {
    "INV": 2,
    "NAND2": 4,
    "NOR2": 4,
    "AND2": 6,
    "OR2": 6,
    "NAND3": 6,
    "NOR3": 6,
    "AND3": 8,
    "OR3": 8,
    "NAND4": 8,
    "NOR4": 8,
    "AND4": 10,
    "XOR2": 12,   # 12T Static CMOS XOR2 (6 inverters)
    "XNOR2": 12,  # 12T Static CMOS XNOR2 (6 inverters)
    "MUX2": 12,   # 12T Static CMOS MUX2 (6 inverters)
    "AOI21": 6,   # 6T Single-stage compound gate
    "OAI21": 6,   # 6T Single-stage compound gate
    "AOI22": 8,   # 8T Compound gate (4 GE)
    "OAI22": 8,   # 8T Compound gate (4 GE)
    "BUFFER": 4,  # 4T Non-inverting buffer (2 inverters)
    "DFFR": 34,   # 34T Flip-Flop with Reset (17 inverters)
    "DFFS": 34,   # 34T Flip-Flop with Set (17 inverters)
    "DFF": 34,    # 34T Flip-Flop (17 inverters)
}

# Equivalent Inverter Count (Gate Equivalent - GE: 1 Inverter = 2 Transistors = 1.0 GE)
INVERTER_EQUIVALENTS = {
    "INV": 1.0,   # 2T / 2T = 1.0 Inverter
    "BUFFER": 2.0,# 4T / 2T = 2.0 Inverters
    "NAND2": 2.0, # 4T / 2T = 2.0 Inverters
    "NOR2": 2.0,  # 4T / 2T = 2.0 Inverters
    "AND2": 3.0,  # 6T / 2T = 3.0 Inverters
    "OR2": 3.0,   # 6T / 2T = 3.0 Inverters
    "NAND3": 3.0, # 6T / 2T = 3.0 Inverters
    "NOR3": 3.0,  # 6T / 2T = 3.0 Inverters
    "AND3": 4.0,  # 8T / 2T = 4.0 Inverters
    "OR3": 4.0,   # 8T / 2T = 4.0 Inverters
    "NAND4": 4.0, # 8T / 2T = 4.0 Inverters
    "NOR4": 4.0,  # 8T / 2T = 4.0 Inverters
    "AND4": 5.0,  # 10T / 2T = 5.0 Inverters
    "XOR2": 6.0,  # 12T / 2T = 6.0 Inverters
    "XNOR2": 6.0, # 12T / 2T = 6.0 Inverters
    "MUX2": 6.0,  # 12T / 2T = 6.0 Inverters
    "AOI21": 3.0, # 6T / 2T = 3.0 Inverters
    "OAI21": 3.0, # 6T / 2T = 3.0 Inverters
    "AOI22": 4.0, # 8T / 2T = 4.0 Inverters
    "OAI22": 4.0, # 8T / 2T = 4.0 Inverters
    "DFFR": 17.0, # 34T / 2T = 17.0 Inverters
    "DFFS": 17.0, # 34T / 2T = 17.0 Inverters
    "DFF": 17.0,  # 34T / 2T = 17.0 Inverters
}
