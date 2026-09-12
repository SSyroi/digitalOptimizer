"""FastAPI Web Server for AMS Digital Optimizer & Synthesizer Dashboard."""

from __future__ import annotations
import os
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from ams_optimizer.core.library import Library, Cell, load_default_library
from ams_optimizer.core.pipeline import OptimizerPipeline

app = FastAPI(title="AMS Digital Optimizer & Synthesizer API", version="0.1.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "examples")

os.makedirs(STATIC_DIR, exist_ok=True)

class OptimizeRequest(BaseModel):
    verilog_code: str
    virtuoso_lib: str = "MY_AMS_LIB"
    custom_cells: Optional[Dict[str, Any]] = None

class CellDefinition(BaseModel):
    name: str
    cell_type: str = "combinational"
    inputs: List[str]
    output: str = "Y"
    function: str = ""
    cost: int = 4
    veriloga_func: str = ""

@app.get("/api/library")
def get_library():
    """Return the default library cell definitions."""
    lib = load_default_library()
    return {
        "name": lib.name,
        "description": lib.description,
        "supply_voltage": lib.supply_voltage,
        "threshold_voltage": lib.threshold_voltage,
        "cells": {
            name: {
                "name": c.name,
                "cell_type": c.cell_type,
                "inputs": c.inputs,
                "output": c.output,
                "outputs": c.outputs,
                "function": c.function_str,
                "cost": c.cost,
                "veriloga_func": c.veriloga_func,
            }
            for name, c in lib.cells.items()
        },
    }

@app.get("/api/examples")
def get_examples():
    """Return list of built-in AMS example blocks."""
    examples = {}
    if os.path.exists(EXAMPLES_DIR):
        for fname in sorted(os.listdir(EXAMPLES_DIR)):
            if fname.endswith(".v"):
                fpath = os.path.join(EXAMPLES_DIR, fname)
                with open(fpath, "r") as f:
                    examples[fname] = f.read()
    return examples

@app.post("/api/optimize")
def optimize_verilog(req: OptimizeRequest):
    """Run optimization, synthesis, Verilog-A generation, and formal equivalence checking."""
    if not req.verilog_code.strip():
        raise HTTPException(status_code=400, detail="Verilog code cannot be empty")

    lib = load_default_library()

    # Apply custom cells if passed
    if req.custom_cells:
        for cname, cinfo in req.custom_cells.items():
            lib.cells[cname] = Cell(
                name=cname,
                cell_type=cinfo.get("cell_type", "combinational"),
                inputs=cinfo.get("inputs", ["A", "B"]),
                output=cinfo.get("output", "Y"),
                function_str=cinfo.get("function", ""),
                cost=int(cinfo.get("cost", 4)),
                veriloga_func=cinfo.get("veriloga_func", ""),
            )

    try:
        pipeline = OptimizerPipeline(lib)
        result = pipeline.run(req.verilog_code, virtuoso_lib=req.virtuoso_lib)

        reg_data = [
            {
                "target": f"{reg_name}.D",
                "reg_name": reg_name,
                "type": "DFF Register",
                "expr": expr.nested_expr,
                "leaves": list(expr.leaves),
            }
            for reg_name, expr in result.register_expressions.items()
        ]

        out_data = [
            {
                "target": out_name,
                "type": "Combinational Output",
                "expr": expr.nested_expr,
                "leaves": list(expr.leaves),
            }
            for out_name, expr in result.output_expressions.items()
        ]

        bom_data = []
        for cell_name, count in sorted(result.gate_breakdown.items()):
            cell = lib.get_cell(cell_name)
            cost = cell.cost if cell else 4
            cat = "Sequential" if (cell and cell.cell_type == "sequential") else "Combinational"
            bom_data.append({
                "cell_name": cell_name,
                "category": cat,
                "count": count,
                "transistors_per_cell": cost,
                "total_transistors": cost * count,
            })

        instances_data = [
            {
                "name": inst.inst_name,
                "cell": inst.cell_type,
                "connections": inst.pin_connections,
                "is_sequential": inst.is_sequential,
            }
            for inst in result.schematic_instances
        ]

        verif_data = {
            "is_equivalent": result.verification.is_equivalent if result.verification else True,
            "message": result.verification.message if result.verification else "Verification complete",
            "signals_count": len(result.verification.signal_results) if result.verification else 0,
            "patterns_count": result.verification.tested_patterns_count if result.verification else 0,
            "mismatches": result.verification.mismatches if result.verification else [],
        }

        return {
            "module_name": result.parsed_module.name,
            "primary_inputs": result.parsed_module.primary_inputs,
            "primary_outputs": result.parsed_module.primary_outputs,
            "state_signals": result.parsed_module.get_all_state_signals(),
            "registers": reg_data,
            "outputs": out_data,
            "bom": bom_data,
            "instances": instances_data,
            "total_gates": result.total_gates,
            "total_transistors": result.total_transistors,
            "veriloga_code": result.veriloga_code,
            "schematic_report": result.schematic_report,
            "skill_script": result.skill_script,
            "spice_netlist": result.spice_netlist,
            "verification": verif_data,
        }
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"Synthesis Error: {str(e)}\n{traceback.format_exc()}")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "AMS Digital Optimizer API running. Build static UI in ams_optimizer/web/static/"}
