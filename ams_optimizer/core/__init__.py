"""Core modules for AMS Digital Optimizer.

Zero external dependencies. Compatible with Python 3.9+.
"""

from .models import (
    SlicedPort,
    SlicedRegister,
    DAGNode,
    SlicedDAG,
    LocalTruthTable,
    MappedCell,
    MappedLogicNode,
    OptimizationResult,
    TRANSISTOR_COST,
)
from .dag_slicer import VerilogDAGSlicer
from .reachability import FSMReachabilityAnalyzer
from .truth_table import LocalTruthTableEvaluator
from .npn_matcher import NPNBitmaskMatcher
from .shannon_mux import ShannonMUXDecomposer
from .quine_mccluskey import QuineMcCluskeySolver
from .tech_mapper import TechnologyMapper
from .veriloga_emitter import VerilogAEmitter
from .skill_emitter import SKILLEmitter
from .optimizer import AMSOptimizer

__all__ = [
    "SlicedPort",
    "SlicedRegister",
    "DAGNode",
    "SlicedDAG",
    "LocalTruthTable",
    "MappedCell",
    "MappedLogicNode",
    "OptimizationResult",
    "TRANSISTOR_COST",
    "VerilogDAGSlicer",
    "FSMReachabilityAnalyzer",
    "LocalTruthTableEvaluator",
    "NPNBitmaskMatcher",
    "ShannonMUXDecomposer",
    "QuineMcCluskeySolver",
    "TechnologyMapper",
    "VerilogAEmitter",
    "SKILLEmitter",
    "AMSOptimizer",
]
