"""AMS Digital Logic Optimizer & Synthesizer.

Multi-Level DAG Truth Table & CMOS Technology Mapping Engine.
Zero external dependencies. Compatible with Python 3.9+.
"""

from .core.optimizer import AMSOptimizer, OptimizationResult
from .core.dag_slicer import VerilogDAGSlicer, SlicedDAG
from .core.npn_mapper import TechnologyMapper, MappedLogicNode

__version__ = "0.2.0"
__all__ = ["AMSOptimizer", "OptimizationResult", "VerilogDAGSlicer", "SlicedDAG", "TechnologyMapper", "MappedLogicNode"]
