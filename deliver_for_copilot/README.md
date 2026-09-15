# Deliverables for Copilot / Linux x86_64 Offline Cluster

This folder contains the pre-compiled binary wheel(s) requested for **`pyeda 0.29.0`** on **Linux x86_64 (CPython 3.9)**.

---

## 1. PyPI Note Regarding PyEDA Linux Wheels
PyPI (**https://pypi.org/project/pyeda/0.29.0/#files**) **does not publish binary wheels for Linux/manylinux** for version 0.29.0 (nor any other PyEDA release). PyPI only hosts Windows binary wheels (`.win_amd64.whl`) and the source distribution tarball (`pyeda-0.29.0.tar.gz`).

To fulfill Copilot's exact request without requiring network access, compilers, or headers on the target UNIX machine:
- The binary wheels here were built using the official Conda-Forge Linux x86_64 CPython 3.9 toolchain.
- Shared libraries (`exprnode.so`, `espresso.so`, `picosat.so`) are linked strictly against `libc.so.6` with max symbol version `GLIBC_2.14`.
- Fully compatible with `manylinux2014_x86_64` (glibc 2.17+), `manylinux_2_17_x86_64`, and modern glibc (RHEL 7/8/9, CentOS, Ubuntu, Debian, SLES).

---

## 2. Included Files & SHA-256 Checksums

| File | Size | SHA-256 Checksum |
| :--- | :--- | :--- |
| **`pyeda-0.29.0-cp39-cp39-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl`** | 250 KB | `a33a31f7388614ecb3c0742a58197aa76193e92e499951c1c13bcb9b8878bc13` |
| **`pyeda-0.29.0-cp39-cp39-manylinux2014_x86_64.whl`** | 250 KB | `9b9d00b856687a241e911cd10497aae0d661e05db329f2cabebe0e0b5de82775` |
| **`pyeda-0.29.0-cp39-cp39-manylinux_2_17_x86_64.whl`** | 250 KB | `76a8ce348956e7864e109061ae69684e1b6abd75b26046c4d1f0f5c41b9147f9` |

Verification:
```bash
cd deliver_for_copilot
sha256sum -c SHA256SUMS.txt
```

---

## 3. How to Install Offline

### Option A: Install pyeda from this folder
```bash
python3 -m pip install --no-index --find-links=deliver_for_copilot pyeda
```

### Option B: One-command full offline installation
All dependencies (including this Linux wheel, markupsafe Linux wheel, jinja2, ply, pyverilog) can be installed together:
```bash
python3 -m pip install --no-index --find-links=deliver_for_copilot --find-links=vendor/wheels --user pyeda pyverilog ply jinja2 markupsafe
```
Or simply run:
```bash
bash vendor/install_offline.sh
```
*(The wheel is also placed in `vendor/wheels/` so `install_offline.sh` works out of the box without any network access or C compiler!)*
