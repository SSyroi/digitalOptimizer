#!/usr/bin/env python3
"""Convenience CLI script to generate Cadence Virtuoso Quick Prototyping Guides.

Usage:
  # Generate guide for default PWM_CTRL (saves to examples/PWM_CTRL_quick_proto.md):
  python3 scripts/generate_prototyping_schematic.py

  # Generate guide with custom output file:
  python3 scripts/generate_prototyping_schematic.py -o examples/PWM_CTRL_quick_proto.md

  # Generate guide from an arbitrary structural Verilog netlist:
  python3 scripts/generate_prototyping_schematic.py examples/PWM_CTRL_netlist.v -o examples/PWM_CTRL_netlist_quick_proto.md

"""

import sys
import os

# Ensure repo root is on sys.path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from espresso_mv_optimizer.schematic_emitter import main

if __name__ == "__main__":
    main()
