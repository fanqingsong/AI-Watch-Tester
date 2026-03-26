#!/usr/bin/env bash
# test-teardown-loop.sh — 10회 연속 회원가입 테스트 (teardown 포함)
# Usage: ./tests/test-teardown-loop.sh [N] [--skip-teardown]
#   N: 반복 횟수 (기본 10)
#   --skip-teardown: teardown 건너뜀 (Firebase 정리 없이 이메일 중복 방지만 검증)

set -euo pipefail

RUNS="${1:-10}"
SKIP_TD="${2:-}"
SCENARIO="scenarios/clasring/SC-CR001_register.yaml"

# 프로젝트 루트로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# venv 활성화
if [ -f ".venv/bin/activate" ]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
fi

echo "========================================"
echo " ClasRing 회원가입 연속 실행 테스트"
echo " 반복 횟수: $RUNS"
echo " teardown: $([ -n "$SKIP_TD" ] && echo '건너뜀' || echo '활성화')"
echo "========================================"

SUCCESS=0
FAIL=0
START_TOTAL=$(date +%s)

for i in $(seq 1 "$RUNS"); do
  echo ""
  echo "--- 실행 $i/$RUNS ($(date '+%H:%M:%S')) ---"
  START=$(date +%s)

  AAT_CMD="aat run --skill-mode $SCENARIO"
  [ -n "$SKIP_TD" ] && AAT_CMD="$AAT_CMD --skip-teardown"

  if $AAT_CMD 2>&1; then
    END=$(date +%s)
    echo "✓ 실행 $i 성공 ($((END - START))초)"
    SUCCESS=$((SUCCESS + 1))
  else
    END=$(date +%s)
    echo "✗ 실행 $i 실패 ($((END - START))초)"
    FAIL=$((FAIL + 1))
  fi

  # 마지막 실행이 아니면 1초 대기 (timestamp 충돌 방지)
  [ "$i" -lt "$RUNS" ] && sleep 1
done

END_TOTAL=$(date +%s)
TOTAL=$((END_TOTAL - START_TOTAL))

echo ""
echo "========================================"
echo " 결과: $SUCCESS/$RUNS 성공, $FAIL 실패"
echo " 총 소요시간: ${TOTAL}초 ($((TOTAL / 60))분 $((TOTAL % 60))초)"
echo " 평균: $((TOTAL / RUNS))초/회"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
echo "✅ $RUNS회 연속 실행 모두 성공!"
