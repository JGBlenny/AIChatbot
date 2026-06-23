#!/usr/bin/env bash
# run-tests.sh — 本地與 CI 共用的測試入口（spec testing-traceability 元件 2・R1.2/1.4/4.2）
#
# 在 Python 3.11 容器（對齊執行期）內跑 pytest：掛載源碼、改碼即跑、免 rebuild。
# 統一用 `docker compose run --rm`（不用 docker exec，避免假設常駐容器），本地與 CI 同一支。
#
# 用法：
#   scripts/run-tests.sh [unit|integration|e2e|all] [--cov] [pytest 額外參數...]
# 範例：
#   scripts/run-tests.sh                 # 預設 unit（CI 主力、可離線）
#   scripts/run-tests.sh unit --cov      # unit + 覆蓋率
#   scripts/run-tests.sh all -k chain    # 全部、篩選含 chain 的測試
#
# 退出碼：pytest 失敗→非 0（供 CI 把關）。
set -euo pipefail

cd "$(dirname "$0")/.."   # 專案根目錄

LAYER="${1:-unit}"
shift || true

COMPOSE_FILE="docker-compose.dev.yml"
SERVICE="rag-orchestrator"

# 組 pytest -m 表達式
case "$LAYER" in
  unit)        MARK_EXPR="unit" ;;
  integration) MARK_EXPR="integration" ;;
  e2e)         MARK_EXPR="e2e" ;;
  all)         MARK_EXPR="" ;;
  --cov|-*)    # 未指定 layer，第一參數其實是旗標 → 視為 unit 並把參數放回
               set -- "$LAYER" "$@"; MARK_EXPR="unit" ;;
  *)           MARK_EXPR="$LAYER" ;;   # 直接當作自訂 marker 表達式
esac

# 解析 --cov
COV_ARGS=()
PYTEST_EXTRA=()
for arg in "$@"; do
  if [[ "$arg" == "--cov" ]]; then
    COV_ARGS=(--cov=services --cov=routers --cov-report=term-missing --cov-report=json:tests/.coverage.json)
  else
    PYTEST_EXTRA+=("$arg")
  fi
done

PYTEST_CMD=(python3 -m pytest)
if [[ -n "$MARK_EXPR" ]]; then
  PYTEST_CMD+=(-m "$MARK_EXPR")
fi
# 安全展開可能為空的陣列（相容 bash 3.2 + set -u）
PYTEST_CMD+=(${COV_ARGS[@]+"${COV_ARGS[@]}"} ${PYTEST_EXTRA[@]+"${PYTEST_EXTRA[@]}"})

echo "▶ layer=${LAYER}  →  ${PYTEST_CMD[*]}"

# 在容器內先裝測試相依（正式 image 不含），再跑 pytest。
docker compose -f "$COMPOSE_FILE" run --rm "$SERVICE" sh -c \
  "pip install -q -r requirements-test.txt && ${PYTEST_CMD[*]}"
