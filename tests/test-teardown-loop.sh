#!/usr/bin/env bash
# test-teardown-loop.sh — 10x consecutive registration test (with teardown)
# Usage: ./tests/test-teardown-loop.sh [N] [--skip-teardown]
#   N: iteration count (default 10)
#   --skip-teardown: skip teardown (test email duplicate prevention only, no Firebase cleanup)

set -euo pipefail

RUNS="${1:-10}"
SKIP_TD="${2:-}"
SCENARIO="scenarios/clasring/SC-CR001_register.yaml"

# Move to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Activate venv
if [ -f ".venv/bin/activate" ]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
fi

echo "========================================"
echo " ClasRing Registration Consecutive Test"
echo " Iterations: $RUNS"
echo " teardown: $([ -n "$SKIP_TD" ] && echo 'skipped' || echo 'enabled')"
echo "========================================"

SUCCESS=0
FAIL=0
START_TOTAL=$(date +%s)

for i in $(seq 1 "$RUNS"); do
  echo ""
  echo "--- Run $i/$RUNS ($(date '+%H:%M:%S')) ---"
  START=$(date +%s)

  AAT_CMD="aat run --skill-mode $SCENARIO"
  [ -n "$SKIP_TD" ] && AAT_CMD="$AAT_CMD --skip-teardown"

  if $AAT_CMD 2>&1; then
    END=$(date +%s)
    echo "✓ Run $i succeeded ($((END - START))s)"
    SUCCESS=$((SUCCESS + 1))
  else
    END=$(date +%s)
    echo "✗ Run $i failed ($((END - START))s)"
    FAIL=$((FAIL + 1))
  fi

  # Wait 1s between runs (except last) to prevent timestamp collision
  [ "$i" -lt "$RUNS" ] && sleep 1
done

END_TOTAL=$(date +%s)
TOTAL=$((END_TOTAL - START_TOTAL))

echo ""
echo "========================================"
echo " Results: $SUCCESS/$RUNS succeeded, $FAIL failed"
echo " Total time: ${TOTAL}s ($((TOTAL / 60))min $((TOTAL % 60))s)"
echo " Average: $((TOTAL / RUNS))s/run"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
echo "✅ All $RUNS consecutive runs succeeded!"
