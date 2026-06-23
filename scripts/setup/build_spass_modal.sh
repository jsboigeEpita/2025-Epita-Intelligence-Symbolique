#!/bin/bash
# ---------------------------------------------------------------------------
# Build & install SPASS 3.9 (SOTA modal theorem prover) for the modal axis (#1234)
# ---------------------------------------------------------------------------
# Reproducible Linux/WSL build of the real SPASS CLI, plus the Tweety<->SPASS
# DFG delivery-contract adapter (scripts/solvers/spass_eml_adapter.sh).
#
# WHY this exists (the "énorme régression" reported 2026-06-23):
#   * The modal axis defaulted to TWEETY/SimpleMlReasoner (pure-Java, naive
#     Kripke enumeration) which OOMs at ~12 atoms (FP-16 #1231) — so real KBs
#     never decided (valid=None).
#   * The vendored SPASS.exe was a GUI/elevation InstallShield build (err740,
#     requireAdministrator) — never a runnable CLI — and was deleted in the
#     cleanup-gate commit f1234b58 together with the Tweety notebooks.
#   * SPASS was therefore never genuinely activated for modal logic.
#
# This script rebuilds SPASS from source and wires the EML->eml adapter so the
# real SOTA prover decides modal consistency (incl. the multi-atom KBs that OOM
# SimpleMlReasoner) — verified firsthand via the production ModalHandler.
#
# Firsthand build environment (po-2025 / WSL2, sudo-free):
#   gcc + make from the distro; flex 2.6.4 + bison 3.8.2 from conda-forge
#   (`conda install -n base -c conda-forge flex bison make`). Source tarball
#   spass39.tgz (554633 bytes) from the official SPASS distribution.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BUILD_DIR="${SPASS_BUILD_DIR:-$HOME/spass_build}"
SRC_TGZ="${SPASS_SRC_TGZ:-$BUILD_DIR/spass39.tgz}"
# Detection looks under PROJ_ROOT/ext_tools (settings.jvm.ext_tools_dir); this
# dir is gitignored except the vendored EProver, so the binary is NOT committed.
DEST_DIR="${SPASS_DEST_DIR:-$REPO_ROOT/ext_tools/spass}"
ADAPTER_SRC="$REPO_ROOT/scripts/solvers/spass_eml_adapter.sh"

echo "== SPASS 3.9 build for modal logic (#1234) =="
echo "  build dir : $BUILD_DIR"
echo "  source    : $SRC_TGZ"
echo "  install to: $DEST_DIR"

# 1. Toolchain check (do NOT auto-install; report what is missing).
missing=""
for tool in gcc make flex bison; do
  command -v "$tool" >/dev/null 2>&1 || missing="$missing $tool"
done
if [ -n "$missing" ]; then
  echo "ERROR: missing build tools:$missing" >&2
  echo "  apt:   sudo apt-get install build-essential flex bison" >&2
  echo "  conda: conda install -n base -c conda-forge flex bison make  (sudo-free)" >&2
  exit 1
fi

# 2. Obtain the source (spass39.tgz from the official SPASS distribution).
mkdir -p "$BUILD_DIR"
if [ ! -f "$SRC_TGZ" ]; then
  echo "ERROR: SPASS source tarball not found at $SRC_TGZ" >&2
  echo "  Download spass39.tgz from the official SPASS distribution" >&2
  echo "  (https://www.spass-prover.org/) and place it there, or set SPASS_SRC_TGZ." >&2
  exit 1
fi

# 3. Extract (the tarball expands flat — analyze.c, approx.c, ... at top level).
cd "$BUILD_DIR"
tar xzf "$SRC_TGZ"

# 4. Build the CLI binary.
make SPASS
test -x "$BUILD_DIR/SPASS" || { echo "ERROR: SPASS build produced no binary" >&2; exit 1; }
echo "Built: $("$BUILD_DIR/SPASS" 2>&1 | grep -i version | head -1 || echo "$BUILD_DIR/SPASS")"

# 5. Install binary + adapter side by side (detection registers the adapter).
mkdir -p "$DEST_DIR"
cp -f "$BUILD_DIR/SPASS" "$DEST_DIR/SPASS"
cp -f "$ADAPTER_SRC" "$DEST_DIR/spass_eml_adapter.sh"
chmod +x "$DEST_DIR/SPASS" "$DEST_DIR/spass_eml_adapter.sh"

echo "== Installed =="
echo "  real binary : $DEST_DIR/SPASS"
echo "  adapter     : $DEST_DIR/spass_eml_adapter.sh  (registered as EXTERNAL_TOOL_PATHS['spass'])"
echo
echo "Set modal_solver=spass (config.py / MODAL_SOLVER=spass) to route the modal"
echo "axis through SPASS. Verify: tests/integration/.../test_spass_real.py"
