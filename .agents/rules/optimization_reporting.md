# Optimization Reporting Rule

## Presentation of Auto-Sweep Optimization Results
- Whenever executing `--auto-sweep` or reporting synthesis results to the user, **ALWAYS** output the full Pareto table of all top candidates (at least top 10 ranks) with all swept parameters (`Rank`, `GE`, `Transistors`, `Cells`, `MUX`, `AND/OR`, `QM`, `SH`, `BUF`, `LEC`).
- Do not collapse or omit this table in favor of just a single result.
- Present the detailed BOM breakdown for the winning configuration directly beneath the Pareto table.
