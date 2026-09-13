"""Unified Multi-Output Espresso-MV Optimizer without Combinational Slicing.

Extracts all combinational logic into a single multi-output matrix, minimizes all
outputs jointly using Berkeley Espresso-MV via pyeda, and extracts globally
shared product terms across logic cones.
"""

__version__ = "1.0.0"
