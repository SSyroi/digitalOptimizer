"""Unified Multi-Output Espresso-MV Optimizer without Combinational Slicing.

Extracts all combinational logic into a single multi-output matrix, minimizes all
outputs jointly using Berkeley Espresso-MV via pyeda, and extracts globally
shared product terms across logic cones.
"""

import os
import sys

# Automatically include vendored offline packages if available
_vendor_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vendor", "packages"))
if os.path.isdir(_vendor_dir) and _vendor_dir not in sys.path:
    sys.path.insert(0, _vendor_dir)

__version__ = "1.0.0"
