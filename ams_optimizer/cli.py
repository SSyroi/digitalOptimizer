"""Command-line interface for AMS Digital Optimizer & Synthesizer."""

from __future__ import annotations
import argparse
import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

from ams_optimizer.core.library import Library, load_default_library
from ams_optimizer.core.pipeline import OptimizerPipeline

console = Console()

def main():
    parser = argparse.ArgumentParser(
        description="AMS Digital Logic Optimizer & Synthesizer for Custom IC Blocks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("verilog_file", help="Path to input behavioral Verilog RTL file")
    parser.add_argument("-l", "--lib", help="Path to custom cell library YAML file (optional)")
    parser.add_argument("-o", "--output-va", help="Path to output Verilog-A file (.va)")
    parser.add_argument("--virtuoso-lib", default="MY_AMS_LIB", help="Target Cadence Virtuoso cell library name")
    parser.add_argument("--save-skill", help="Path to save Cadence Virtuoso SKILL .il script")
    parser.add_argument("--save-spice", help="Path to save CDL/SPICE netlist (.sp)")
    parser.add_argument("--save-report", help="Path to save Schematic Markdown wiring report (.md)")

    args = parser.parse_args()

    if not os.path.exists(args.verilog_file):
        console.print(f"[bold red]Error:[/] Verilog file not found: {args.verilog_file}")
        sys.exit(1)

    with open(args.verilog_file, "r") as f:
        verilog_code = f.read()

    # Load Library
    if args.lib:
        if not os.path.exists(args.lib):
            console.print(f"[bold red]Error:[/] Library file not found: {args.lib}")
            sys.exit(1)
        library = Library.load_from_yaml(args.lib)
    else:
        library = load_default_library()

    console.print(Panel(
        f"[bold cyan]AMS Digital Optimizer & Synthesizer[/]\n"
        f"Input RTL: [bold green]{args.verilog_file}[/]\n"
        f"Library: [bold yellow]{library.name}[/] ({len(library.cells)} cells)",
        border_style="cyan"
    ))

    # Run Pipeline
    pipeline = OptimizerPipeline(library)
    result = pipeline.run(verilog_code, virtuoso_lib=args.virtuoso_lib)

    # Display Extracted Flip-Flops & Nested Expressions
    reg_table = Table(title=f"Extracted Sequential Elements & Simplified Next-State Logic: {result.parsed_module.name}")
    reg_table.add_column("Register / Output", style="bold cyan")
    reg_table.add_column("Type", style="magenta")
    reg_table.add_column("Simplified Nested Gate Expression", style="green")

    for reg_name, expr in result.register_expressions.items():
        reg_table.add_row(f"{reg_name}.D", "DFF D-Input", expr.nested_expr)

    for out_name, expr in result.output_expressions.items():
        reg_table.add_row(out_name, "Combinational Out", expr.nested_expr)

    console.print(reg_table)

    # Display BOM
    bom_table = Table(title="Schematic Bill of Materials (BOM)")
    bom_table.add_column("Cell Name", style="bold yellow")
    bom_table.add_column("Count", justify="right", style="cyan")
    bom_table.add_column("Transistors / Cell", justify="right")
    bom_table.add_column("Total Transistors", justify="right", style="green")

    for cname, cnt in sorted(result.gate_breakdown.items()):
        cell = library.get_cell(cname)
        cost = cell.cost if cell else 4
        bom_table.add_row(cname, str(cnt), f"~{cost}", f"~{cost * cnt}")

    bom_table.add_row(
        "[bold]TOTAL[/]",
        f"[bold cyan]{result.total_gates}[/]",
        "-",
        f"[bold green]~{result.total_transistors}[/]"
    )
    console.print(bom_table)

    # Display Verification Status
    if result.verification:
        if result.verification.is_equivalent:
            console.print(Panel(
                f"[bold green]✔ {result.verification.message}[/]",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"[bold red]✘ {result.verification.message}[/]\n" + "\n".join(result.verification.mismatches),
                border_style="red"
            ))

    # Save Output Files if specified
    if args.output_va:
        with open(args.output_va, "w") as f:
            f.write(result.veriloga_code)
        console.print(f"[bold green]Saved Verilog-A model to:[/] {args.output_va}")

    if args.save_skill:
        with open(args.save_skill, "w") as f:
            f.write(result.skill_script)
        console.print(f"[bold green]Saved Cadence SKILL script to:[/] {args.save_skill}")

    if args.save_spice:
        with open(args.save_spice, "w") as f:
            f.write(result.spice_netlist)
        console.print(f"[bold green]Saved SPICE netlist to:[/] {args.save_spice}")

    if args.save_report:
        with open(args.save_report, "w") as f:
            f.write(result.schematic_report)
        console.print(f"[bold green]Saved Schematic Wiring Report to:[/] {args.save_report}")

    # If no output file specified, print a preview of Verilog-A
    if not args.output_va:
        console.print("\n[bold cyan]Generated Verilog-A Preview (use -o <file.va> to save):[/]")
        syntax = Syntax(result.veriloga_code[:1200] + ("\n... [truncated, use -o to save full file]" if len(result.veriloga_code) > 1200 else ""), "verilog", theme="monokai", line_numbers=True)
        console.print(syntax)

if __name__ == "__main__":
    main()
