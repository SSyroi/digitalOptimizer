"""Silicon Area & Transistor Cost Models for Technology Mapping.

Physical transistor counts and inverter equivalent (GE) weights for
standard CMOS logic gates and storage elements.
"""

from __future__ import annotations
from typing import Dict

# Physical transistor cost per CMOS standard cell
TRANSISTOR_COST: Dict[str, int] = {
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
INVERTER_EQUIVALENTS: Dict[str, float] = {
    "INV": 1.0,    # 2T / 2T = 1.0 Inverter
    "BUFFER": 2.0, # 4T / 2T = 2.0 Inverters
    "NAND2": 2.0,  # 4T / 2T = 2.0 Inverters
    "NOR2": 2.0,   # 4T / 2T = 2.0 Inverters
    "AND2": 3.0,   # 6T / 2T = 3.0 Inverters
    "OR2": 3.0,    # 6T / 2T = 3.0 Inverters
    "NAND3": 3.0,  # 6T / 2T = 3.0 Inverters
    "NOR3": 3.0,   # 6T / 2T = 3.0 Inverters
    "AND3": 4.0,   # 8T / 2T = 4.0 Inverters
    "OR3": 4.0,    # 8T / 2T = 4.0 Inverters
    "NAND4": 4.0,  # 8T / 2T = 4.0 Inverters
    "NOR4": 4.0,   # 8T / 2T = 4.0 Inverters
    "AND4": 5.0,   # 10T / 2T = 5.0 Inverters
    "XOR2": 6.0,   # 12T / 2T = 6.0 Inverters
    "XNOR2": 6.0,  # 12T / 2T = 6.0 Inverters
    "MUX2": 6.0,   # 12T / 2T = 6.0 Inverters
    "AOI21": 3.0,  # 6T / 2T = 3.0 Inverters
    "OAI21": 3.0,  # 6T / 2T = 3.0 Inverters
    "AOI22": 4.0,  # 8T / 2T = 4.0 Inverters
    "OAI22": 4.0,  # 8T / 2T = 4.0 Inverters
    "DFFR": 17.0,  # 34T / 2T = 17.0 Inverters
    "DFFS": 17.0,  # 34T / 2T = 17.0 Inverters
    "DFF": 17.0,   # 34T / 2T = 17.0 Inverters
}
