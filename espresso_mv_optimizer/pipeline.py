"""Top-Level Unified Multi-Output Espresso-MV Pipeline.

Runs full-circuit multi-output logic minimization using standard pyverilog,
iverilog simulation, and pyeda C Espresso-MV minimization.
"""

from __future__ import annotations
import time
from typing import Dict, Any, List

from .extractor import UnifiedRTLExtractor
from .multi_output_engine import MultiOutputEspressoEngine
from .gate_mapper import SharedGateMapper


class UnifiedEspressoMVOptimizer:
    """Unified Multi-Output Espresso-MV Optimizer without combinational slicing."""

    def __init__(self):
        pass

    def optimize(
        self,
        verilog_code_or_path: str,
        dc_relaxation: str = "exact",
        enable_demorgan: bool = True,
        enable_tech_mapping: bool = False,
        enable_shannon: bool = True,
        shannon_threshold: int = 8,
        var_selection: str = "frequency",
        max_fan_in: int = 4,
        extractor: UnifiedRTLExtractor = None,
    ) -> Dict[str, Any]:
        """Runs unified multi-output synthesis on full Verilog RTL."""
        t0 = time.time()

        # 1. Extract full truth tables via pyverilog + iverilog
        if extractor is None:
            extractor = UnifiedRTLExtractor(verilog_code_or_path)
        table_strings = extractor.extract_truth_tables(dc_relaxation=dc_relaxation)
        t_extract = time.time() - t0

        # 2. Joint Multi-Output Espresso-MV via pyeda
        t1 = time.time()
        engine = MultiOutputEspressoEngine(extractor.inputs)
        min_exprs, shared_cubes = engine.solve(table_strings)
        t_esp = time.time() - t1

        # 3. Silicon Gate Mapping with Global Sharing
        mapper = SharedGateMapper(extractor.inputs)
        metrics = mapper.map_shared_network(
            min_exprs,
            shared_cubes,
            total_ffs=extractor.total_ffs,
            enable_demorgan=enable_demorgan,
            enable_tech_mapping=enable_tech_mapping,
            enable_shannon=enable_shannon,
            shannon_threshold=shannon_threshold,
            var_selection=var_selection,
            max_fan_in=max_fan_in,
        )

        # 4. Formal Verification against Golden Truth Table
        lec_passed = self._verify_equivalence(extractor, min_exprs, engine.py_vars, table_strings)

        metrics.update({
            "name": f"Espresso-MV (dc={dc_relaxation}, sh={shannon_threshold}, fan={max_fan_in})",
            "dc_relaxation": dc_relaxation,
            "shannon_threshold": shannon_threshold,
            "var_selection": var_selection,
            "max_fan_in": max_fan_in,
            "enable_demorgan": enable_demorgan,
            "enable_tech_mapping": enable_tech_mapping,
            "enable_shannon": enable_shannon,
            "min_exprs": min_exprs,
            "shared_cubes": shared_cubes,
            "lec_passed": lec_passed,
            "time_extract_s": t_extract,
            "time_espresso_s": t_esp,
            "input_names": extractor.inputs,
            "targets": extractor.comb_targets,
        })

        return metrics

    def _verify_equivalence(
        self,
        extractor: UnifiedRTLExtractor,
        min_exprs: Dict[str, Any],
        py_vars: List[Any],
        table_strings: Dict[str, str],
    ) -> bool:
        """Verifies that minimized multi-output expressions match the truth table."""
        num_rows = 1 << extractor.num_inputs

        # Check sample vectors across the input space
        step = 1 if num_rows <= 256 else max(1, num_rows // 256)
        for row in range(0, num_rows, step):
            point = {py_vars[bit_i]: (row >> bit_i) & 1 for bit_i in range(extractor.num_inputs)}
            for tgt, expr in min_exprs.items():
                gold_char = table_strings[tgt][row]
                if gold_char == "-":
                    continue  # Don't care point
                gold_val = int(gold_char)

                if str(expr) in ["0", "1"]:
                    pyeda_val = int(str(expr))
                else:
                    pyeda_val = int(expr.restrict(point))

                if pyeda_val != gold_val:
                    return False

        return True
