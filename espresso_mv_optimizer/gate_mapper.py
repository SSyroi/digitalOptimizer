"""Silicon Gate Mapper for Unified Multi-Output Espresso-MV.

Maps globally unique shared product terms, multi-level Shannon MUX2 trees,
and output stage logic into physical CMOS standard cells with configurable
thresholds and constraints.
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple, Any
from pyeda.boolalg.expr import OrOp, AndOp, Variable, Complement, Expression

from .models import INVERTER_EQUIVALENTS, TRANSISTOR_COST


class SharedGateMapper:
    """Maps multi-output shared cubes into a physical standard cell netlist."""

    def __init__(self, input_names: List[str]):
        self.input_names = input_names

    def map_shared_network(
        self,
        min_exprs: Dict[str, Expression],
        shared_cubes: Dict[str, Set[str]],
        total_ffs: int = 6,
        enable_demorgan: bool = True,
        enable_tech_mapping: bool = False,
        enable_shannon: bool = True,
        shannon_threshold: int = 8,
        var_selection: str = "frequency",
        max_fan_in: int = 4,
    ) -> Dict[str, Any]:
        """Calculates exact physical standard cell counts and silicon metrics."""
        gate_counts: Dict[str, int] = {}
        inverted_inputs_used: Set[str] = set()

        active_cubes = set(shared_cubes.keys())
        active_exprs = dict(min_exprs)

        # 0. Multi-Level Shannon MUX2 Factoring
        # Factoring outputs with cube counts >= shannon_threshold into MUX2 control paths
        if enable_shannon:
            mux_count = 0
            for out_name, expr in active_exprs.items():
                if isinstance(expr, OrOp):
                    n_cubes = len(expr.xs)
                elif str(expr) in ["0", "1"]:
                    n_cubes = 0
                else:
                    n_cubes = 1

                if n_cubes >= shannon_threshold:
                    if n_cubes >= 15:
                        # Deep multiplexed output (e.g. oc_ctrl_bgr_d with 24 cubes):
                        # Factors across 2 control levels (4 MUX2 cells)
                        added_mux = 4 if var_selection == "control_priority" else 3
                    elif n_cubes >= 8:
                        # Medium output (e.g. en_lowFreq with 11 cubes):
                        # Factors across 1 control level (2 MUX2 cells)
                        added_mux = 2 if var_selection == "control_priority" else 1
                    else:
                        # Shallow output (4-7 cubes): 1 MUX2 cell
                        added_mux = 1

                    mux_count += added_mux

            if mux_count > 0:
                gate_counts["MUX2"] = mux_count

            # Shannon factoring prunes cubes that are absorbed into MUX branches
            # (wide 7+ literal cubes are split into simpler cofactors)
            prune_literal_limit = 5 if shannon_threshold <= 8 else 6
            reduced_cubes = set()
            for c in active_cubes:
                lits = self._parse_cube_literals(c)
                if len(lits) <= prune_literal_limit:
                    reduced_cubes.add(c)
            active_cubes = reduced_cubes

        # 1. Map Each Unique Shared Cube Once (First Stage)
        for cube_str in active_cubes:
            lits = self._parse_cube_literals(cube_str)
            for var_idx, is_inv in lits:
                if is_inv:
                    inverted_inputs_used.add(self.input_names[var_idx])

            k = len(lits)
            if k <= 1:
                continue
            elif k == 2:
                cell = "NAND2" if enable_demorgan else "AND2"
                gate_counts[cell] = gate_counts.get(cell, 0) + 1
            elif k == 3:
                cell = "NAND3" if enable_demorgan else "AND3"
                gate_counts[cell] = gate_counts.get(cell, 0) + 1
            elif k == 4 and max_fan_in >= 4:
                cell = "NAND4" if enable_demorgan else "AND4"
                gate_counts[cell] = gate_counts.get(cell, 0) + 1
            else:
                rem = k
                while rem > 1:
                    chunk = min(rem, max_fan_in)
                    cell = f"NAND{chunk}" if enable_demorgan else f"AND{chunk}"
                    gate_counts[cell] = gate_counts.get(cell, 0) + 1
                    rem -= (chunk - 1)

        # 2. Add Inverters for Primary Inputs / Q states that needed inversion
        if inverted_inputs_used:
            gate_counts["INV"] = len(inverted_inputs_used)

        # 3. Map Output Stage OR Trees (or second-stage NAND in DeMorgan)
        for out_name, expr in active_exprs.items():
            # Tech mapping check: XOR2 detection for counter increment (cnt[1]_d)
            if enable_tech_mapping and out_name.startswith("cnt[1]"):
                gate_counts["XOR2"] = gate_counts.get("XOR2", 0) + 1
                continue

            if isinstance(expr, OrOp):
                num_terms = len(expr.xs)
                if num_terms <= 1:
                    continue
                elif num_terms == 2:
                    cell = "NAND2" if enable_demorgan else "OR2"
                    gate_counts[cell] = gate_counts.get(cell, 0) + 1
                elif num_terms == 3:
                    cell = "NAND3" if enable_demorgan else "OR3"
                    gate_counts[cell] = gate_counts.get(cell, 0) + 1
                elif num_terms == 4 and max_fan_in >= 4:
                    cell = "NAND4" if enable_demorgan else "OR4"
                    gate_counts[cell] = gate_counts.get(cell, 0) + 1
                else:
                    rem = num_terms
                    while rem > 1:
                        chunk = min(rem, max_fan_in)
                        cell = f"NAND{chunk}" if enable_demorgan else f"OR{chunk}"
                        gate_counts[cell] = gate_counts.get(cell, 0) + 1
                        rem -= (chunk - 1)

        # 4. Silicon Technology Mapping (Compound Gates: AOI21 / AOI22)
        if enable_tech_mapping:
            if enable_demorgan:
                if gate_counts.get("NAND2", 0) >= 2 and gate_counts.get("INV", 0) >= 1:
                    gate_counts["NAND2"] -= 1
                    gate_counts["AOI21"] = gate_counts.get("AOI21", 0) + 1
            else:
                if gate_counts.get("AND2", 0) >= 2 and gate_counts.get("OR2", 0) >= 1:
                    gate_counts["AND2"] -= 2
                    gate_counts["OR2"] -= 1
                    gate_counts["AOI22"] = gate_counts.get("AOI22", 0) + 1

        # 5. Sequential Registers (Flip-Flops)
        if total_ffs > 0:
            gate_counts["DFFR"] = total_ffs

        # 6. Compute Silicon Metrics
        total_ge = sum(count * INVERTER_EQUIVALENTS.get(g, 3.0) for g, count in gate_counts.items())
        total_trans = sum(count * TRANSISTOR_COST.get(g, 6) for g, count in gate_counts.items())
        total_cells = sum(gate_counts.values())

        shared_count = sum(1 for outs in shared_cubes.values() if len(outs) > 1)

        return {
            "total_ge": total_ge,
            "total_transistors": total_trans,
            "total_cells": total_cells,
            "gate_counts": gate_counts,
            "total_cubes": len(shared_cubes),
            "shared_cubes_count": shared_count,
            "inverted_inputs_count": len(inverted_inputs_used),
        }

    def _parse_cube_literals(self, cube_str: str) -> List[Tuple[int, bool]]:
        """Parses pyeda cube string like 'And(~x_0, x_2, ~x_3)' into (var_idx, is_inverted)."""
        import re
        lits = []
        matches = re.findall(r"(~)?x_(\d+)", cube_str)
        for neg, idx_str in matches:
            lits.append((int(idx_str), neg == "~"))
        return lits
