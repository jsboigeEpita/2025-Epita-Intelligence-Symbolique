#!/usr/bin/env bash
# run_demo.sh — Single-command reproducibility verification
# Runs the politics scenario through the light workflow and asserts key outputs.
#
# Usage:  docker compose run verify
#         OR:  bash scripts/repro/run_demo.sh (local, requires conda env)
#
# Exit codes: 0 = all assertions pass, 1 = assertion failure, 2 = setup error

set -euo pipefail

SCENARIO="${1:-examples/scenarios/politics.txt}"
WORKFLOW="${2:-light}"
OUTPUT_DIR="${DEMO_OUTPUT:-/app/output}"

echo "=== Reproducibility Demo ==="
echo "Scenario: $SCENARIO"
echo "Workflow: $WORKFLOW"
echo ""

# Step 1: Run the pipeline
echo "[1/3] Running analysis pipeline..."
python argumentation_analysis/run_orchestration.py \
    --file "$SCENARIO" \
    --workflow "$WORKFLOW" \
    --output "$OUTPUT_DIR/results.json" \
    2>&1 | tee "$OUTPUT_DIR/pipeline.log" || {
    echo "ERROR: Pipeline execution failed. Check $OUTPUT_DIR/pipeline.log"
    exit 2
}

# Step 2: Check output file exists and is valid JSON
echo "[2/3] Validating output..."
if [ ! -f "$OUTPUT_DIR/results.json" ]; then
    echo "FAIL: results.json not found"
    exit 1
fi

python -c "
import json, sys
with open('$OUTPUT_DIR/results.json') as f:
    data = json.load(f)

# Assertion 1: Pipeline completed
assert data.get('status') in ('completed', 'success', None), \
    f'Pipeline status unexpected: {data.get(\"status\")}'

# Assertion 2: Has state snapshot
state = data.get('state_snapshot', {})
assert isinstance(state, dict), 'No state_snapshot in results'
assert len(state) > 0, 'state_snapshot is empty'

# Assertion 3: Arguments extracted (at least 3 for politics scenario)
args_extracted = state.get('arguments', [])
n_args = len(args_extracted) if isinstance(args_extracted, list) else state.get('argument_count', 0)
assert n_args >= 3, f'Expected >= 3 arguments, got {n_args}'

# Assertion 4: At least 1 fallacy detected
fallacies = state.get('identified_fallacies', [])
n_fallacies = len(fallacies) if isinstance(fallacies, list) else state.get('fallacy_count', 0)
assert n_fallacies >= 1, f'Expected >= 1 fallacy, got {n_fallacies}'

print(f'  Arguments: {n_args} (>= 3 OK)')
print(f'  Fallacies: {n_fallacies} (>= 1 OK)')
print(f'  State keys: {len(state)}')
print('  All assertions PASSED')
"

# Step 3: Summary
echo ""
echo "[3/3] Demo complete."
echo "Output: $OUTPUT_DIR/results.json"
echo ""
echo "=== VERIFICATION PASSED ==="
