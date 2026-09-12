"""AMS Digital Logic Optimizer & Synthesizer.

Multi-Level DAG Truth Table & CMOS Technology Mapping Engine.
Zero external dependencies. Compatible with Python 3.9+.
"""

from .core.models import (
    SlicedPort,
    SlicedRegister,
    DAGNode,
    SlicedDAG,
    LocalTruthTable,
    MappedCell,
    MappedLogicNode,
    GateInstance,
    StructuralNetlist,
    OptimizationResult,
    TRANSISTOR_COST,
    INVERTER_EQUIVALENTS,
)
from .core.dag_slicer import VerilogDAGSlicer
from .core.reachability import FSMReachabilityAnalyzer
from .core.truth_table import LocalTruthTableEvaluator
from .core.npn_matcher import NPNBitmaskMatcher
from .core.shannon_mux import ShannonMUXDecomposer
from .core.quine_mccluskey import QuineMcCluskeySolver
from .core.tech_mapper import TechnologyMapper
from .core.netlist_generator import StructuralNetlistGenerator
from .core.veriloga_emitter import VerilogAEmitter
from .core.skill_emitter import SKILLEmitter
from .core.optimizer import AMSOptimizer

__version__ = "0.2.0"
__all__ = [
    "SlicedPort",
    "SlicedRegister",
    "DAGNode",
    "SlicedDAG",
    "LocalTruthTable",
    "MappedCell",
    "MappedLogicNode",
    "GateInstance",
    "StructuralNetlist",
    "OptimizationResult",
    "TRANSISTOR_COST",
    "INVERTER_EQUIVALENTS",
    "VerilogDAGSlicer",
    "FSMReachabilityAnalyzer",
    "LocalTruthTableEvaluator",
    "NPNBitmaskMatcher",
    "ShannonMUXDecomposer",
    "QuineMcCluskeySolver",
    "TechnologyMapper",
    "StructuralNetlistGenerator",
    "VerilogAEmitter",
    "SKILLEmitter",
    "AMSOptimizer",
]
