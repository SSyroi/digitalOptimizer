"""Shared Data Models and Constants for AMS Digital Optimizer.

Defines all core dataclasses for ports, registers, DAG nodes, truth tables,
mapped cells, and optimization deliverables.

Zero external dependencies. Compatible with Python 3.9+.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple


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
    bitmask: int = 0  # e.g., 0b1110 = 14 for NAND2


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
class OptimizationResult:
    module_name: str
    dag: SlicedDAG
    mapped_nodes: Dict[str, MappedLogicNode]
    veriloga_code: str
    skill_code: str
    bom_report: str
    gate_breakdown: Dict[str, int] = field(default_factory=dict)
    total_gates: int = 0
    total_transistors: int = 0


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
    "XOR2": 8,
    "XNOR2": 8,
    "MUX2": 6,    # 6T Transmission-Gate MUX
    "AOI21": 6,   # 6T Single-stage compound gate
    "OAI21": 6,   # 6T Single-stage compound gate
    "DFFR": 16,
    "DFFS": 16,
    "DFF": 16,
}
