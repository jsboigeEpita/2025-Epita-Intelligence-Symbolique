#!/bin/bash
# ---------------------------------------------------------------------------
# Tweety <-> SPASS DFG delivery-contract adapter (#1234)
# ---------------------------------------------------------------------------
# Modal analogue of the eprover #1204 delivery-contract sentinel.
#
# PROBLEM (firsthand-diagnosed, 2026-06-23):
#   Tweety 1.29's SPASSMlReasoner translates a modal KB to DFG and writes the
#   special-formulae logic token in UPPERCASE:
#       list_of_special_formulae(axioms,EML).
#   SPASS 3.9's DFG parser requires the token in LOWERCASE and aborts with:
#       "got 'EML', expected special type (eml)"  (exit 1)
#   so SPASSMlReasoner.query throws "SPASS returned no result which can be
#   interpreted" and the modal axis cannot decide. This is a Tweety<->SPASS
#   version mismatch, NOT a reasoning failure.
#
# FIX (no contournement — the real SOTA prover does ALL the work):
#   Rewrite ONLY the keyword case in the DFG temp file Tweety passes as a file
#   argument, then exec the real SPASS unchanged. SPASS still performs the full
#   EML->FOL translation + saturation; this only repairs the interface token.
#
# WIRING:
#   Detection (argumentation_analysis/core/jvm_setup.py) registers THIS script
#   as EXTERNAL_TOOL_PATHS['spass'] when it is present next to the real binary,
#   so Tweety invokes the adapter transparently. The real SPASS binary must sit
#   beside this script as ./SPASS (override with $SPASS_REAL_BIN).
#
# Build the real SPASS: scripts/setup/build_spass_modal.sh
# ---------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REAL="${SPASS_REAL_BIN:-$HERE/SPASS}"

if [ ! -x "$REAL" ]; then
  echo "spass_eml_adapter: real SPASS binary not found/executable at '$REAL'" >&2
  echo "  set SPASS_REAL_BIN or place the binary beside this adapter as ./SPASS" >&2
  exit 127
fi

# Repair the DFG keyword case in every file argument (Tweety passes exactly one
# DFG temp file). Match only the special-formulae logic token to stay surgical.
for a in "$@"; do
  if [ -f "$a" ]; then
    sed -i 's/list_of_special_formulae(\([a-zA-Z_]*\),EML)/list_of_special_formulae(\1,eml)/g' "$a"
  fi
done

exec "$REAL" "$@"
