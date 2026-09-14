#!/usr/bin/env python3
"""Offline Capability Catalog for Vendored Libraries.

Lists all available EDA and mathematical capabilities bundled in vendor/
without requiring an internet connection or external package repository.
"""

from __future__ import annotations
import sys
import os
import json
import argparse

# Auto-add vendor/packages to sys.path
vendor_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "packages"))
if vendor_dir not in sys.path:
    sys.path.insert(0, vendor_dir)

CAPABILITIES = [
    {
        "package": "PyEDA",
        "import_name": "pyeda",
        "module": "pyeda.boolalg.espresso",
        "functionality": "Berkeley Espresso-MV Multi-Output Two-Level Logic Minimizer",
        "use_cases": "Exact prime implicant reduction, truth-table matrix compression, PLA logic minimization",
        "snippet": "from pyeda.inter import *; f_min = espresso_tts(truthtable([a, b], '0001'))",
    },
    {
        "package": "PyEDA",
        "import_name": "pyeda",
        "module": "pyeda.boolalg.bdd",
        "functionality": "Binary Decision Diagrams (BDD / ROBDD)",
        "use_cases": "Canonical formal logic equivalence, SAT model counting, boolean function isomorphism",
        "snippet": "from pyeda.boolalg.bdd import expr2bdd; bdd = expr2bdd(expr)",
    },
    {
        "package": "PyEDA",
        "import_name": "pyeda",
        "module": "pyeda.boolalg.picosat",
        "functionality": "PicoSAT Boolean Satisfiability (SAT) Solver (C-extension)",
        "use_cases": "Bounded model checking, miter equivalence checking, constraint satisfaction, fault analysis",
        "snippet": "from pyeda.boolalg.picosat import satisfy_one; sol = satisfy_one(cnf_formula)",
    },
    {
        "package": "PyEDA",
        "import_name": "pyeda",
        "module": "pyeda.boolalg.bfarray",
        "functionality": "Boolean Function Arrays & Bitvectors",
        "use_cases": "Multi-bit bus transformations, arithmetic ALU synthesis, vector logic manipulation",
        "snippet": "from pyeda.inter import exprvars; bus = exprvars('data', 8)",
    },
    {
        "package": "PyEDA",
        "import_name": "pyeda",
        "module": "pyeda.parsing.pla / dimacs",
        "functionality": "Industry-Standard Logic File Format Parsers",
        "use_cases": "Reading Berkeley .pla files and SAT competition .cnf files directly",
        "snippet": "from pyeda.parsing.pla import parse_pla; pla_data = parse_pla(pla_text)",
    },
    {
        "package": "Pyverilog",
        "import_name": "pyverilog",
        "module": "pyverilog.vparser.parser",
        "functionality": "IEEE-1364 Verilog-2001 AST Parser",
        "use_cases": "Extracting ports, nets, registers, always blocks, and module hierarchy from Verilog code",
        "snippet": "from pyverilog.vparser.parser import parse; ast, _ = parse(['design.v'])",
    },
    {
        "package": "Pyverilog",
        "import_name": "pyverilog",
        "module": "pyverilog.ast_code_generator",
        "functionality": "Verilog Code Generator (AST to RTL)",
        "use_cases": "Programmatic RTL modification, automated wrapper generation, testbench instrumentation",
        "snippet": "from pyverilog.ast_code_generator.codegen import ASTCodeGenerator; rtl = ASTCodeGenerator().visit(ast)",
    },
    {
        "package": "Pyverilog",
        "import_name": "pyverilog",
        "module": "pyverilog.dataflow",
        "functionality": "RTL Dataflow & Signal Dependency Analyzer",
        "use_cases": "Extracting combinational loops, signal fan-out trees, multi-driver detection",
        "snippet": "from pyverilog.dataflow.dataflow_analyzer import VerilogDataflowAnalyzer",
    },
    {
        "package": "Pyverilog",
        "import_name": "pyverilog",
        "module": "pyverilog.controlflow",
        "functionality": "FSM State Transition Graph (STG) Extractor",
        "use_cases": "Extracting state transition tables and control flow graphs directly from procedural Verilog",
        "snippet": "from pyverilog.controlflow.controlflow_analyzer import VerilogControlflowAnalyzer",
    },
    {
        "package": "PLY",
        "import_name": "ply",
        "module": "ply.lex & ply.yacc",
        "functionality": "Python Lex-Yacc LALR(1) Compiler-Compiler",
        "use_cases": "Building custom domain-specific parsers (SPICE netlists, Cadence DEF/LEF, Liberty .lib, SKILL)",
        "snippet": "import ply.lex as lex; import ply.yacc as yacc",
    },
    {
        "package": "Jinja2",
        "import_name": "jinja2",
        "module": "jinja2",
        "functionality": "High-Performance Code & Template Generation Engine",
        "use_cases": "Automated generation of Verilog testbenches, Cadence SKILL scripts, and Markdown documentation",
        "snippet": "from jinja2 import Template; output = Template('wire [{{w-1}}:0] {{n}};').render(n='bus', w=8)",
    },
]


def print_table(items: list[dict]):
    print("=" * 110)
    print("          OFFLINE VENDOR CAPABILITIES CATALOG (AVAILABLE WITHOUT INTERNET)")
    print("=" * 110)
    print(f"{'Package':<12} | {'Module':<28} | {'Primary Functionality':<55}")
    print("-" * 110)
    for c in items:
        print(f"{c['package']:<12} | {c['module']:<28} | {c['functionality']:<55}")
    print("=" * 110)
    print("\n[TIP] Offline documentation inspection:")
    print("  python3 -c \"import pyeda.boolalg.bdd; help(pyeda.boolalg.bdd)\"")
    print("  python3 -c \"import pyverilog.dataflow; help(pyverilog.dataflow)\"")
    print("  python3 -m pydoc pyeda.boolalg.picosat\n")


def print_markdown(items: list[dict]):
    print("| Package | Module | Primary Functionality | Example Use Cases | Quick Snippet |")
    print("| :--- | :--- | :--- | :--- | :--- |")
    for c in items:
        print(f"| **{c['package']}** | `{c['module']}` | {c['functionality']} | {c['use_cases']} | `{c['snippet']}` |")


def main():
    parser = argparse.ArgumentParser(description="Query capabilities bundled in vendor/")
    parser.add_argument("--json", action="store_true", help="Output catalog as JSON (for AI / scripts)")
    parser.add_argument("--markdown", action="store_true", help="Output catalog as Markdown table")
    parser.add_argument("--package", type=str, default="", help="Filter by package name (e.g. pyeda, pyverilog)")
    args = parser.parse_args()

    items = CAPABILITIES
    if args.package:
        q = args.package.lower()
        items = [c for c in items if q in c["package"].lower() or q in c["module"].lower()]

    if args.json:
        print(json.dumps(items, indent=2))
    elif args.markdown:
        print_markdown(items)
    else:
        print_table(items)


if __name__ == "__main__":
    main()
