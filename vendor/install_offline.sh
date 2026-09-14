#!/usr/bin/env bash
# ==============================================================================
# Offline Vendor Package Installer for Semiconductor / Air-Gapped Clusters
# Installs pyeda, pyverilog, ply, jinja2, markupsafe with ZERO internet access
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WHEELS_DIR="${SCRIPT_DIR}/wheels"

echo "================================================================================"
echo "Installing AMS / Espresso-MV dependencies offline from: ${WHEELS_DIR}"
echo "================================================================================"

# Allow C compiler to accept classic ANSI C function pointer types in Berkeley Espresso
export CFLAGS="-Wno-incompatible-function-pointer-types -Wno-error ${CFLAGS}"

python3 -m pip install \
  --no-index \
  --find-links="${WHEELS_DIR}" \
  --user \
  pyeda==0.29.0 \
  pyverilog==1.3.0 \
  ply==3.11 \
  jinja2==3.1.6 \
  markupsafe==3.0.3

echo ""
echo "All packages successfully installed into user environment!"
echo "Verifying installation:"
python3 -c "import pyeda.inter, pyverilog, ply, jinja2, markupsafe; print('✓ All Espresso-MV dependencies verified and ready!')"
