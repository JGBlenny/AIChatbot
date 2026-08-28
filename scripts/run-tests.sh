#!/usr/bin/env bash
# run-tests.sh — 本地與 CI 共用的測試入口（spec testing-traceability 元件 2・R1.2/1.4/4.2）
#
# 在 Python 3.11 容器（對齊執行期）內跑 pytest：掛載源碼、改碼即跑、免 rebuild。
# 統一用 `docker compose run --rm`（不用 docker exec，避免假設常駐容器）。
#
# ⚠️ 本地與 CI **不是同一支入口**（spec conversational-routing-execution 任務 1.5｜元件 1-C）。
#    CI 直接跑 `python3 -m pytest`，不經本腳本。分工如下：
#      ・不變量（旗標語義、skip 型別前綴、空跑守門、測試 DB 守門）
#        → 掛在 **pytest 層**（tests/conftest.py），本地與 CI 共用同一份，不得各有一套；
#      ・供裝（容器啟動、network attach、pip install）
#        → **各自的 runner 負責**（本腳本 ／ GH Actions service containers），
#          兩者供裝方式本質不同，強行統一只會多一層間接。
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

# 測試旗標注入（spec conversational-routing-execution 任務 1.1／1.8｜R1.1/1.4/1.5）
#
# 兩組變數，責任不同：
#   RUN_INTEGRATION / RUN_E2E  ── 讓該層「可以跑」（conftest 的 skip gate 讀它）
#   REQUESTED_TEST_LAYERS      ── 宣告本次「要求跑哪一層」（空跑守門讀它）
# 後者是 requested-layer 的唯一權威來源；conftest **不解析 `-m` 運算式**推導意圖
# （`-m "not integration"` 會被字面比對誤判成請求了 integration → 無辜硬擋）。
ENV_ARGS=()
case "$LAYER" in
  integration) ENV_ARGS=(-e RUN_INTEGRATION=1 -e REQUESTED_TEST_LAYERS=integration) ;;
  e2e)         ENV_ARGS=(-e RUN_E2E=1 -e REQUESTED_TEST_LAYERS=e2e) ;;
  all)         ENV_ARGS=(-e RUN_INTEGRATION=1 -e RUN_E2E=1
                         -e REQUESTED_TEST_LAYERS=integration,e2e) ;;
  *)           ;;   # unit 與自訂 marker 運算式：兩者皆不注入（維持離線、不受守門管轄）
esac

# ── 真 API 防護（fail-closed；2026-08-26 加）────────────────────────────────
#
# 起因：業主把本機 stack 接到 production JGB（JGB_API_BASE_URL=https://www.jgbsmart.com、
# USE_MOCK_JGB_API=false）。而 runner 與 docker-compose.dev.yml **都沒有**覆寫該值，
# 於是 `.env` 的設定會直接被測試容器吃到——跑一次 integration/e2e 就會對線上發真請求。
#
# ⚠️ 危險不只是讀：`create_repair` 是 **POST /api/external/v1/repairs**
#    （jgb_system_api 唯一的寫入端點），走到送出會在**線上開出真的報修單**。
#
# 故一律強制注入替身；要打真 API 必須**顯式**開 ALLOW_REAL_JGB_API=1，且會印警告。
# 同 assert_non_production_db 的 fail-closed 思路：預設安全，例外要說出口。
if [[ "${ALLOW_REAL_JGB_API:-0}" == "1" ]]; then
  echo "⚠️  ALLOW_REAL_JGB_API=1 —— 測試將對 **真 JGB API** 發請求（含可能的寫入端點）"
  # ⚠️ 旗標必須**傳進容器**：測試自己也要看得見它才能決定跑不跑
  #    （任務 12.1 的契約 smoke 以此當顯式閘門）。
  #    2026-08-28 實跑逼出：原本只在 host 端判斷，容器內恆為 unset，
  #    於是「開了旗標卻永遠 gate_skipped」，而略過訊息看起來完全正常。
  ENV_ARGS+=(-e ALLOW_REAL_JGB_API=1)
else
  ENV_ARGS+=(-e USE_MOCK_JGB_API=true)
fi

echo "▶ layer=${LAYER}  →  ${PYTEST_CMD[*]}"

# 在容器內先裝測試相依（正式 image 不含），再跑 pytest。
docker compose -f "$COMPOSE_FILE" run --rm ${ENV_ARGS[@]+"${ENV_ARGS[@]}"} "$SERVICE" sh -c \
  "pip install -q -r requirements-test.txt && ${PYTEST_CMD[*]}"
