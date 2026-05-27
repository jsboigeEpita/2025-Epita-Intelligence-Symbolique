#!/usr/bin/env bash
# FF Showcase Re-run — Track FF #693
# Reproducible runner for Epic #717 capstone.
# Runs both paths (DAG + conversational) + deep synthesis on corpora A/B/C.
#
# Usage:
#   conda run -n projet-is-roo-new --no-capture-output bash scripts/run_ff_showcase.sh
#
# Output (gitignored):
#   outputs/deep_analysis/both_paths_vs_zeroshot_{A,B,C}.json
#   outputs/deep_analysis/both_paths_vs_zeroshot_{A,B,C}_{path}.synthesis.md

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

for corpus in A B C; do
    echo "=== Corpus $corpus ==="
    conda run -n projet-is-roo-new --no-capture-output python \
        scripts/measure_both_paths_vs_zeroshot.py \
        --corpus "$corpus" \
        --paths dag,conversational
    echo ""
done

echo "=== Done. Outputs in outputs/deep_analysis/ ==="
ls -la outputs/deep_analysis/both_paths_vs_zeroshot_*.json
ls -la outputs/deep_analysis/both_paths_vs_zeroshot_*.synthesis.md
