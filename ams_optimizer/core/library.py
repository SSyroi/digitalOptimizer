"""Cell Library Manager for AMS Digital Synthesizer."""

from __future__ import annotations
import os
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import sympy
from sympy.logic.boolalg import Boolean
from .ast_parser import VerilogExprParser

@dataclass
class Cell:
    name: str
    cell_type: str  # "combinational" | "sequential"
    inputs: List[str]
    output: str = "Y"
    outputs: List[str] = field(default_factory=lambda: ["Q", "QN"])
    function_str: str = ""
    cost: int = 1  # Equivalent transistor count / relative area
    veriloga_func: str = ""
    bool_expr: Optional[Boolean] = None

    def __post_init__(self):
        if self.cell_type == "combinational" and self.function_str:
            try:
                parser = VerilogExprParser(self.function_str)
                self.bool_expr = parser.parse()
            except Exception:
                self.bool_expr = None

    def evaluate(self, input_values: Dict[str, bool]) -> bool:
        """Evaluate the cell output given a mapping of input pin names to boolean values."""
        if self.bool_expr is None:
            # Fallback evaluation for standard gates
            return self._fallback_eval(input_values)
        syms = {sympy.Symbol(pin): val for pin, val in input_values.items()}
        return bool(self.bool_expr.subs(syms))

    def _fallback_eval(self, env: Dict[str, bool]) -> bool:
        inps = [env.get(p, False) for p in self.inputs]
        if self.name == "INV":
            return not inps[0]
        elif self.name.startswith("NAND"):
            return not all(inps)
        elif self.name.startswith("NOR"):
            return not any(inps)
        elif self.name.startswith("AND"):
            return all(inps)
        elif self.name.startswith("OR"):
            return any(inps)
        elif self.name == "XOR2":
            return inps[0] ^ inps[1]
        elif self.name == "XNOR2":
            return not (inps[0] ^ inps[1])
        elif self.name == "MUX2":
            s = env.get("S", False)
            d0 = env.get("D0", False)
            d1 = env.get("D1", False)
            return d1 if s else d0
        elif self.name == "AOI21":
            a1 = env.get("A1", False)
            a2 = env.get("A2", False)
            b1 = env.get("B1", False)
            return not ((a1 and a2) or b1)
        elif self.name == "OAI21":
            a1 = env.get("A1", False)
            a2 = env.get("A2", False)
            b1 = env.get("B1", False)
            return not ((a1 or a2) and b1)
        return False


@dataclass
class Library:
    name: str
    description: str = ""
    supply_voltage: float = 1.8
    threshold_voltage: float = 0.9
    cells: Dict[str, Cell] = field(default_factory=dict)

    @classmethod
    def load_from_yaml(cls, filepath: str) -> "Library":
        """Load library definition from a YAML file."""
        with open(filepath, "r") as f:
            data = yaml.safe_load(f)

        name = data.get("name", "custom_lib")
        description = data.get("description", "")
        supply_voltage = float(data.get("supply_voltage", 1.8))
        threshold_voltage = float(data.get("threshold_voltage", 0.9))

        cells = {}
        for cell_name, cell_info in data.get("cells", {}).items():
            cell_type = cell_info.get("type", "combinational")
            inputs = cell_info.get("inputs", [])
            output = cell_info.get("output", "Y")
            outputs = cell_info.get("outputs", ["Q", "QN"])
            function_str = cell_info.get("function", "")
            cost = int(cell_info.get("cost", 1))
            veriloga_func = cell_info.get("veriloga_func", "")

            cells[cell_name] = Cell(
                name=cell_name,
                cell_type=cell_type,
                inputs=inputs,
                output=output,
                outputs=outputs,
                function_str=function_str,
                cost=cost,
                veriloga_func=veriloga_func,
            )

        return cls(
            name=name,
            description=description,
            supply_voltage=supply_voltage,
            threshold_voltage=threshold_voltage,
            cells=cells,
        )

    def get_combinational_cells(self) -> List[Cell]:
        """Return all combinational cells sorted by cost."""
        return sorted(
            [c for c in self.cells.values() if c.cell_type == "combinational"],
            key=lambda c: (c.cost, len(c.inputs)),
        )

    def get_sequential_cells(self) -> List[Cell]:
        """Return all sequential cells."""
        return [c for c in self.cells.values() if c.cell_type == "sequential"]

    def get_cell(self, name: str) -> Optional[Cell]:
        return self.cells.get(name)


def load_default_library() -> Library:
    """Load the built-in default AMS library."""
    default_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "libraries",
        "default_ams.yaml",
    )
    if os.path.exists(default_path):
        return Library.load_from_yaml(default_path)
    raise FileNotFoundError(f"Default library file not found at {default_path}")
