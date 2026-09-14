# Offline Vendored Dependencies (`vendor/`)

This directory contains pre-packaged, offline-installable dependencies for the **Unified Espresso-MV Logic Optimizer**. It allows running the optimizer on air-gapped or restricted semiconductor compute clusters (e.g. RHEL 9 without internet or external pip access).

## Total Footprint: **~4.1 MB**
* `vendor/wheels/` (~830 KB): Offline Python wheelhouse containing `.whl` and `.tar.gz` archives.
* `vendor/packages/` (~3.3 MB): Direct unpackaged pure-Python modules (`pyverilog`, `ply`, `jinja2`, `markupsafe`, `pyeda`).

---

## Contents of `vendor/wheels/`

| Package | Version | Type | Notes |
| :--- | :--- | :--- | :--- |
| **`pyeda`** | `0.29.0` | Source tarball | Contains complete Berkeley Espresso C source code |
| **`pyverilog`** | `1.3.0` | Universal tarball | Pure Python IEEE-1364 Verilog AST parser |
| **`ply`** | `3.11` | Pure Python wheel | Python Lex-Yacc |
| **`jinja2`** | `3.1.6` | Pure Python wheel | Template engine |
| **`markupsafe`** | `3.0.3` | Wheels (Linux x86_64 & macOS) | Required dependency of `jinja2` |

---

## How to Use on Locked / Offline Clusters

### Option 1: Zero-Install (Direct `PYTHONPATH`)
`espresso_mv_optimizer` automatically looks for `vendor/packages` on startup. If you run:
```bash
python3 -m espresso_mv_optimizer.cli examples/PWM_CTRL.v
```
It will automatically load the dependencies from `./vendor/packages` without modifying your environment.

### Option 2: Offline User Installation (Recommended for Clusters)
Run the included offline installation script:
```bash
bash vendor/install_offline.sh
```
Or manually run `pip` with `--no-index`:
```bash
export CFLAGS="-Wno-incompatible-function-pointer-types -Wno-error"
python3 -m pip install --no-index --find-links=vendor/wheels --user pyeda pyverilog ply jinja2 markupsafe
```
This builds and installs all packages into your user directory (`~/.local/lib/python3.x/site-packages`) with **zero internet connection** and **zero IT permissions needed**.
