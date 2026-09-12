"""AMS Digital Logic Optimizer & Synthesizer for Custom IC Blocks.

Zero external dependencies. Compatible with Python 3.9+.
"""

from .optimizer import AMSOptimizer, OptimizationResult
from .dag_slicer import VerilogDAGSlicer, SlicedDAG
from .npn_mapper import TechnologyMapper, MappedLogicNode

__all__ = ["AMSOptimizer", "OptimizationResult", "VerilogDAGSlicer", "SlicedDAG", "TechnologyMapper", "MappedLogicNode"]
