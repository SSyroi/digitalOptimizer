"""Synthesizable Gate-Level Structural Verilog Generator with Shared Intermediate Nodes.

Generates a clean, standard cell structural Verilog netlist (.v) where:
- Inverters and shared product terms (cubes) are instantiated once as explicit
  standard cell instances driving named intermediate wires (w_c0, w_c1, ...).
- Shared nodes across outputs are wired directly to output NAND trees without duplication.
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple, Any
from pyeda.boolalg.expr import OrOp, AndOp, Variable, Complement, Expression

from ams_optimizer.core.models import INVERTER_EQUIVALENTS, TRANSISTOR_COST


class UnifiedVerilogNetlistEmitter:
    """Generates standard cell structural Verilog code with shared intermediate nodes."""

    def __init__(
        self,
        module_name: str,
        input_names: List[str],
        targets: List[str],
        min_exprs: Dict[str, Expression],
        gate_counts: Dict[str, int],
        total_ge: float,
        total_transistors: int,
        total_cells: int,
    ):
        self.module_name = module_name
        self.input_names = input_names
        self.targets = targets
        self.min_exprs = min_exprs
        self.gate_counts = gate_counts
        self.total_ge = total_ge
        self.total_transistors = total_transistors
        self.total_cells = total_cells

    def emit(self) -> str:
        lines: List[str] = []

        lines.append("// ============================================================================")
        lines.append(f"// Module: {self.module_name}_netlist")
        lines.append(f"// Synthesized by Unified Espresso-MV Silicon Optimizer")
        lines.append(f"// Gate-Level Synthesizable Structural Netlist with Shared Intermediate Nodes")
        lines.append(f"// Total Standard Cells : {self.total_cells} cells")
        lines.append(f"// Inverter Equivalents  : {self.total_ge:.1f} GE")
        lines.append(f"// Transistor Count     : {self.total_transistors} transistors")
        lines.append("// ============================================================================")
        lines.append("")

        ports = [
            "VDD", "VSS", "sub", "res_n", "c_DfT_en_LP", "c_DfT_en_PWM",
            "c_DfT_oc_dig_VDD", "en_LP", "oc_select", "oc_ctrl_cp", "oc_ctrl_bgr",
            "clk_i", "en_lowFreq", "oc_select_ext", "oc_ctrl_cp_ext", "en_LP_ext",
            "c_metalFix_invert_oc_defaults"
        ]
        lines.append(f"module {self.module_name}_netlist ({', '.join(ports)});")
        lines.append("  input wire VDD, VSS, sub, res_n, clk_i;")
        lines.append("  input wire c_DfT_en_LP, c_DfT_en_PWM, c_metalFix_invert_oc_defaults;")
        lines.append("  input wire [1:0] c_DfT_oc_dig_VDD;")
        lines.append("  output wire en_LP, oc_select, oc_ctrl_cp, oc_ctrl_bgr, en_lowFreq;")
        lines.append("  output wire oc_select_ext, oc_ctrl_cp_ext, en_LP_ext;")
        lines.append("")

        var_names = []
        var_ident_map = {}
        for inp in self.input_names:
            if "c_DfT_oc_dig_VDD[" in inp:
                bit = inp.split("[")[1].split("]")[0]
                ident = f"c_DfT_oc_dig_VDD_{bit}"
                var_names.append(inp)
                var_ident_map[inp] = ident
            elif inp in ("c_DfT_en_LP", "c_DfT_en_PWM", "c_metalFix_invert_oc_defaults"):
                var_names.append(inp)
                var_ident_map[inp] = inp
            elif "cnt[" in inp:
                bit = inp.split("[")[1].split("]")[0]
                ident = f"cnt_{bit}_q"
                var_names.append(ident)
                var_ident_map[ident] = ident
            else:
                ident = f"{inp}_q"
                var_names.append(ident)
                var_ident_map[ident] = ident

        # Extract Unique Cubes & Build Map
        unique_cubes: List[Tuple[str, Any]] = []
        cube_map: Dict[str, int] = {}
        cube_usage: Dict[str, List[str]] = {}

        for tgt in self.targets:
            expr = self.min_exprs.get(tgt)
            if expr is None:
                continue
            if isinstance(expr, OrOp):
                cubes = list(expr.xs)
            elif str(expr) not in ("0", "1"):
                cubes = [expr]
            else:
                cubes = []

            for c in cubes:
                c_str = str(c)
                cube_usage.setdefault(c_str, []).append(tgt)
                if c_str not in cube_map:
                    cube_map[c_str] = len(unique_cubes)
                    unique_cubes.append((c_str, c))

        # Wires
        lines.append("  // Internal State Registers & Next-State Nets")
        lines.append("  wire oc_ctrl_bgr_q, oc_ctrl_bgr_d;")
        lines.append("  wire cnt_0_q, cnt_0_d;")
        lines.append("  wire cnt_1_q, cnt_1_d;")
        lines.append("  wire cnt_2_q, cnt_2_d;")
        lines.append("  wire cnt_3_q, cnt_3_d;")
        lines.append("  wire startup_q, startup_d;")
        lines.append("")
        lines.append("  // Inverted Polarity Pool Wires")
        lines.append("  wire " + ", ".join(f"w_inv_{var_ident_map[v]}" for v in var_names) + ";")
        lines.append("")
        lines.append(f"  // Shared Intermediate Product Term Wires ({len(unique_cubes)} unique shared cubes)")
        lines.append("  wire " + ", ".join(f"w_c{i}" for i in range(len(unique_cubes))) + ";")
        lines.append("")

        # Inverter Gate Instantiations
        lines.append("  // 1. Global Input & Register Inverters")
        for v in var_names:
            v_ident = var_ident_map[v]
            lines.append(f"  INV_X1  U_inv_{v_ident:<28} (.A({v}), .Y(w_inv_{v_ident}));")
        lines.append("")

        def emit_cube_nand_tree(lits: List[str], target_wire: str, prefix: str) -> List[str]:
            k = len(lits)
            if k == 1:
                return [f"  INV_X1 U_{prefix} (.A({lits[0]}), .Y({target_wire}));"]
            elif k == 2:
                return [f"  NAND2_X1 U_{prefix} (.A({lits[0]}), .B({lits[1]}), .Y({target_wire}));"]
            elif k == 3:
                return [f"  NAND3_X1 U_{prefix} (.A({lits[0]}), .B({lits[1]}), .C({lits[2]}), .Y({target_wire}));"]
            elif k == 4:
                return [f"  NAND4_X1 U_{prefix} (.A({lits[0]}), .B({lits[1]}), .C({lits[2]}), .D({lits[3]}), .Y({target_wire}));"]
            else:
                out = []
                inv_chunks = []
                for i in range(0, k, 4):
                    chunk = lits[i:i+4]
                    w_nand = f"w_{prefix}_n{i//4}"
                    w_inv = f"w_{prefix}_i{i//4}"
                    out.append(f"  wire {w_nand}, {w_inv};")
                    out.extend(emit_cube_nand_tree(chunk, w_nand, f"{prefix}_n{i//4}"))
                    out.append(f"  INV_X1 U_{prefix}_inv{i//4} (.A({w_nand}), .Y({w_inv}));")
                    inv_chunks.append(w_inv)
                out.extend(emit_cube_nand_tree(inv_chunks, target_wire, f"{prefix}_root"))
                return out

        # Shared Cube Gate Instantiations
        lines.append(f"  // 2. Shared Intermediate Product Term Gates ({len(unique_cubes)} unique NAND cells)")
        for idx, (c_str, c_expr) in enumerate(unique_cubes):
            users = cube_usage.get(c_str, [])
            u_cmt = f"// Shared: {', '.join(users)}" if len(users) > 1 else f"// Output: {users[0]}"

            if isinstance(c_expr, AndOp):
                lits = []
                for l in c_expr.xs:
                    if isinstance(l, Complement):
                        var_idx = int(str(l.top).split("_")[1])
                        v = var_names[var_idx]
                        lits.append(f"w_inv_{var_ident_map[v]}")
                    else:
                        var_idx = int(str(l).split("_")[1])
                        lits.append(var_names[var_idx])

                lines.append(f"  {u_cmt}")
                lines.extend(emit_cube_nand_tree(lits, f"w_c{idx}", f"c{idx}"))
            elif isinstance(c_expr, Complement):
                var_idx = int(str(c_expr.top).split("_")[1])
                v = var_names[var_idx]
                lines.append(f"  assign w_c{idx} = {v}; {u_cmt}")
            elif isinstance(c_expr, Variable):
                var_idx = int(str(c_expr).split("_")[1])
                v = var_names[var_idx]
                lines.append(f"  assign w_c{idx} = w_inv_{var_ident_map[v]}; {u_cmt}")
        lines.append("")

        # Output Stage Gate Instantiations
        lines.append("  // 3. Output Stage Combinational Gates (NAND Combinations of Shared Wires)")
        target_wire_map = {
            "en_LP": "en_LP",
            "oc_select": "oc_select",
            "oc_ctrl_cp": "oc_ctrl_cp",
            "en_lowFreq": "en_lowFreq",
            "oc_ctrl_bgr_d": "oc_ctrl_bgr_d",
            "cnt[3]_d": "cnt_3_d",
            "cnt[2]_d": "cnt_2_d",
            "cnt[1]_d": "cnt_1_d",
            "cnt[0]_d": "cnt_0_d",
            "startup_d": "startup_d",
        }

        def emit_nand_or_tree(inputs: List[str], target_net: str, prefix: str) -> List[str]:
            k = len(inputs)
            if k == 1:
                return [f"  assign {target_net} = {inputs[0]};"]
            elif k == 2:
                return [f"  NAND2_X1 U_{prefix} (.A({inputs[0]}), .B({inputs[1]}), .Y({target_net}));"]
            elif k == 3:
                return [f"  NAND3_X1 U_{prefix} (.A({inputs[0]}), .B({inputs[1]}), .C({inputs[2]}), .Y({target_net}));"]
            elif k == 4:
                return [f"  NAND4_X1 U_{prefix} (.A({inputs[0]}), .B({inputs[1]}), .C({inputs[2]}), .D({inputs[3]}), .Y({target_net}));"]
            else:
                out_lines = []
                chunk_outputs = []
                for i in range(0, k, 4):
                    chunk = inputs[i:i+4]
                    c_out = f"w_{prefix}_ch{i//4}"
                    out_lines.append(f"  wire {c_out};")
                    out_lines.extend(emit_nand_or_tree(chunk, c_out, f"{prefix}_ch{i//4}"))
                    inv_out = f"w_{prefix}_inv_ch{i//4}"
                    out_lines.append(f"  wire {inv_out};")
                    out_lines.append(f"  INV_X1 U_{prefix}_inv{i//4} (.A({c_out}), .Y({inv_out}));")
                    chunk_outputs.append(inv_out)
                out_lines.extend(emit_nand_or_tree(chunk_outputs, target_net, f"{prefix}_root"))
                return out_lines

        for tgt in self.targets:
            out_wire = target_wire_map.get(tgt, tgt)
            expr = self.min_exprs.get(tgt)
            if expr is None:
                continue

            clean_tgt = tgt.replace('[','_').replace(']','')
            if str(expr) == "0":
                lines.append(f"  assign {out_wire} = 1'b0;")
            elif str(expr) == "1":
                lines.append(f"  assign {out_wire} = 1'b1;")
            elif isinstance(expr, OrOp):
                inputs_to_nand = [f"w_c{cube_map[str(c)]}" for c in expr.xs]
                lines.extend(emit_nand_or_tree(inputs_to_nand, out_wire, f"out_{clean_tgt}"))
            else:
                c_idx = cube_map[str(expr)]
                lines.append(f"  INV_X1   U_out_{clean_tgt} (.A(w_c{c_idx}), .Y({out_wire}));")

        lines.append("")
        # Flip-Flops
        lines.append("  // 4. Sequential Register Bank")
        lines.append("  DFFS_X1 U_dff_bgr   (.D(oc_ctrl_bgr_d), .CK(clk_i), .SN(res_n), .Q(oc_ctrl_bgr_q), .QN());")
        lines.append("  DFFR_X1 U_dff_cnt0  (.D(cnt_0_d),       .CK(clk_i), .RN(res_n), .Q(cnt_0_q),       .QN());")
        lines.append("  DFFR_X1 U_dff_cnt1  (.D(cnt_1_d),       .CK(clk_i), .RN(res_n), .Q(cnt_1_q),       .QN());")
        lines.append("  DFFR_X1 U_dff_cnt2  (.D(cnt_2_d),       .CK(clk_i), .RN(res_n), .Q(cnt_2_q),       .QN());")
        lines.append("  DFFR_X1 U_dff_cnt3  (.D(cnt_3_d),       .CK(clk_i), .RN(res_n), .Q(cnt_3_q),       .QN());")
        lines.append("  DFFS_X1 U_dff_start (.D(startup_d),     .CK(clk_i), .SN(res_n), .Q(startup_q),     .QN());")
        lines.append("")
        lines.append("  // Extended Output Aliases")
        lines.append("  assign oc_ctrl_bgr   = oc_ctrl_bgr_q;")
        lines.append("  assign oc_select_ext = oc_select;")
        lines.append("  assign oc_ctrl_cp_ext= oc_ctrl_cp;")
        lines.append("  assign en_LP_ext     = en_LP;")
        lines.append("")
        lines.append("endmodule")
        lines.append("")

        return "\n".join(lines)
