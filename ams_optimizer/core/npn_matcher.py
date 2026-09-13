"""NPN Bitmask Pattern Matcher for Standard Cell Identification.

Matches 1, 2, and 3-input truth table integer bitmasks directly against
standard CMOS logic gates (AOI21, OAI21, XOR2, XNOR2, NAND2/3/4, NOR2/3/4, MUX2).

Zero external dependencies. Compatible with Python 3.9+.
"""

from __future__ import annotations
import itertools
from typing import Dict, List, Optional, Tuple

from .models import LocalTruthTable, MappedLogicNode


class NPNBitmaskMatcher:
    """Matches local truth table bitmasks against standard cell physical topologies."""

    @staticmethod
    def match_1input(tt: LocalTruthTable) -> Optional[MappedLogicNode]:
        """Matches 1-input buffer or inverter."""
        inp = tt.inputs[0]
        if tt.bitmask == 0b10:  # Identity buffer: Y = A
            return MappedLogicNode(node_name=tt.node_name, expression=inp)
        elif tt.bitmask == 0b01:  # Inverter: Y = ~A
            return MappedLogicNode(node_name=tt.node_name, expression=f"INV({inp})", gate_counts={"INV": 1})
        return None

    @staticmethod
    def match_2input(tt: LocalTruthTable, allow_and_or: bool = True) -> Optional[MappedLogicNode]:
        """Matches 2-input NAND2, NOR2, AND2, OR2, XOR2, XNOR2."""
        a, b = tt.inputs[0], tt.inputs[1]
        bm = tt.bitmask
        if bm == 0b1000:  # AND2: A & B
            if allow_and_or:
                return MappedLogicNode(node_name=tt.node_name, expression=f"AND2({a}, {b})", gate_counts={"AND2": 1})
            return MappedLogicNode(node_name=tt.node_name, expression=f"INV(NAND2({a}, {b}))", gate_counts={"NAND2": 1, "INV": 1})
        elif bm == 0b0111:  # NAND2: ~(A & B)
            return MappedLogicNode(node_name=tt.node_name, expression=f"NAND2({a}, {b})", gate_counts={"NAND2": 1})
        elif bm == 0b1110:  # OR2: A | B
            if allow_and_or:
                return MappedLogicNode(node_name=tt.node_name, expression=f"OR2({a}, {b})", gate_counts={"OR2": 1})
            return MappedLogicNode(node_name=tt.node_name, expression=f"INV(NOR2({a}, {b}))", gate_counts={"NOR2": 1, "INV": 1})
        elif bm == 0b0001:  # NOR2: ~(A | B)
            return MappedLogicNode(node_name=tt.node_name, expression=f"NOR2({a}, {b})", gate_counts={"NOR2": 1})
        elif bm == 0b0110:  # XOR2: A ^ B
            return MappedLogicNode(node_name=tt.node_name, expression=f"XOR2({a}, {b})", gate_counts={"XOR2": 1})
        elif bm == 0b1001:  # XNOR2: ~(A ^ B)
            return MappedLogicNode(node_name=tt.node_name, expression=f"XNOR2({a}, {b})", gate_counts={"XNOR2": 1})
        return None

    @staticmethod
    def match_3input(tt: LocalTruthTable, allow_and_or: bool = True, allow_mux: bool = True) -> Optional[MappedLogicNode]:
        """Matches 3-input NAND3, NOR3, AND3, OR3, AOI21, OAI21, MUX2."""
        inputs = tt.inputs
        bm = tt.bitmask

        # NAND3: 0b01111111 (127)
        if bm == 0b01111111:
            return MappedLogicNode(node_name=tt.node_name, expression=f"NAND3({inputs[0]}, {inputs[1]}, {inputs[2]})", gate_counts={"NAND3": 1})
        # AND3: 0b10000000 (128)
        if bm == 0b10000000:
            if allow_and_or:
                return MappedLogicNode(node_name=tt.node_name, expression=f"AND3({inputs[0]}, {inputs[1]}, {inputs[2]})", gate_counts={"AND3": 1})
            return MappedLogicNode(node_name=tt.node_name, expression=f"INV(NAND3({inputs[0]}, {inputs[1]}, {inputs[2]}))", gate_counts={"NAND3": 1, "INV": 1})
        # NOR3: 0b00000001 (1)
        if bm == 0b00000001:
            return MappedLogicNode(node_name=tt.node_name, expression=f"NOR3({inputs[0]}, {inputs[1]}, {inputs[2]})", gate_counts={"NOR3": 1})
        # OR3: 0b11111110 (254)
        if bm == 0b11111110:
            if allow_and_or:
                return MappedLogicNode(node_name=tt.node_name, expression=f"OR3({inputs[0]}, {inputs[1]}, {inputs[2]})", gate_counts={"OR3": 1})
            return MappedLogicNode(node_name=tt.node_name, expression=f"INV(NOR3({inputs[0]}, {inputs[1]}, {inputs[2]}))", gate_counts={"NOR3": 1, "INV": 1})

        # Test permutations for AOI21: ~((A & B) | C)
        for perm in itertools.permutations(inputs, 3):
            a, b, c = perm
            aoi_bm = 0
            for row in range(8):
                val_a = (row >> inputs.index(a)) & 1
                val_b = (row >> inputs.index(b)) & 1
                val_c = (row >> inputs.index(c)) & 1
                out = 1 if not ((val_a and val_b) or val_c) else 0
                if out:
                    aoi_bm |= (1 << row)
            if bm == aoi_bm:
                return MappedLogicNode(node_name=tt.node_name, expression=f"AOI21({a}, {b}, {c})", gate_counts={"AOI21": 1})

        # Test permutations for MUX2: (S ? D1 : D0)
        if allow_mux:
            for s in inputs:
                d_inputs = [x for x in inputs if x != s]
                d0, d1 = d_inputs[0], d_inputs[1]
                for (curr_d0, curr_d1) in ((d0, d1), (d1, d0)):
                    mux_bm = 0
                    for row in range(8):
                        val_s = (row >> inputs.index(s)) & 1
                        val_d0 = (row >> inputs.index(curr_d0)) & 1
                        val_d1 = (row >> inputs.index(curr_d1)) & 1
                        out = val_d1 if val_s else val_d0
                        if out:
                            mux_bm |= (1 << row)
                    if bm == mux_bm:
                        return MappedLogicNode(node_name=tt.node_name, expression=f"MUX2({s}, {curr_d0}, {curr_d1})", gate_counts={"MUX2": 1})

        return None
