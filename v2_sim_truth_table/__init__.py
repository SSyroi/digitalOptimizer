"""v2_sim_truth_table: Simulation-Driven Truth Table Synthesizer for AMS Digital Blocks.

Python 3.9+ compatible with zero external dependencies.
"""

from .optimizer import SimTruthTableOptimizer, SimOptimizationResult
from .slicer import VerilogSlicer, SlicedModule
from .quine_mccluskey import minimize_truth_table
from .cmos_mapper import CMOSMapper

__all__ = [
    "SimTruthTableOptimizer",
    "SimOptimizationResult",
    "VerilogSlicer",
    "SlicedModule",
    "minimize_truth_table",
    "CMOSMapper",
]
