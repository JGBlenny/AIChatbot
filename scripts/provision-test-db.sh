#!/usr/bin/env bash
# provision-test-db.sh — 供裝測試資料庫 aichatbot_test
#   （spec conversational-routing-execution 任務 2.4｜R1.2）
#
# 為什麼需要這支：任務 2.1 的 fail-closed 守門只允許連白名單內的測試庫
# （aichatbot_test / aichatbot_ci）。在該庫供裝完成前，integration 與 e2e
# 會全數被守門拒絕——那是**預期行為，不是回歸**。本腳本把它建起來。
#
# ⚠️ repo 內**沒有**從零建 schema 的路徑（init seed 已於 2026-07-11 除役，
#    見 database/README.md；runbook 附錄 A 明訂「新環境建置＝空庫從 dump 還原」）。
#    故本腳本以 **schema-only dump** 自來源庫複製結構，不複製資料。
#
# 供裝範圍（2026-08-23 業主定案的「最小供裝」）：
#   ✅ database 本身、schema／migrations（經 schema-only dump）
#   ✅ Face configs＋system context＋dialogue rules
#      ＝ knowledge_base 中 category IN ('對話規則','系統脈絡') 共 48 列（全表 1041 列的 4.6%）
#   ❌ 完整 KB、embedding、semantic-model index —— **刻意不供裝**
#      （任務 2.5 已證直達進場與分類路由在 C4b 標的上等價，故 C4b 不需真檢索）
#
# 用法：
#   bash scripts/provision-test-db.sh            # dry-run：只報告會做什麼
#   bash scripts/provision-test-db.sh --apply    # 真跑（可重入）
#
# 冪等：DB 已存在則不重建；資料以「先清該兩類、再灌入」達成可重入。
set -euo pipefail

PG_CONTAINER="${PG_CONTAINER:-aichatbot-postgres}"
DB_USER="${DB_USER:-aichatbot}"
SRC_DB="${SRC_DB:-aichatbot_admin}"
DST_DB="${DST_DB:-aichatbot_test}"

# ── 安全閘門：本腳本只准寫測試庫 ──────────────────────────────
ALLOWED_TARGETS=("aichatbot_test" "aichatbot_ci")
if ! printf '%s\n' "${ALLOWED_TARGETS[@]}" | grep -qxF "$DST_DB"; then
  echo "❌ 拒絕：目標庫 '$DST_DB' 不在允許清單 ${ALLOWED_TARGETS[*]} 內。" >&2
  echo "   本腳本會清除目標庫的資料列，不得指向 production。" >&2
  exit 1
fi
if [[ "$DST_DB" == "$SRC_DB" ]]; then
  echo "❌ 拒絕：來源與目標相同（${SRC_DB}）——會清掉來源資料。" >&2
  exit 1
fi

APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1
say() { echo "$@"; }

dex()      { docker exec "$PG_CONTAINER" "$@"; }
psql_src() { dex psql -U "$DB_USER" -d "$SRC_DB" -tA -c "$1"; }
psql_dst() { dex psql -U "$DB_USER" -d "$DST_DB" -tA -v ON_ERROR_STOP=1 -c "$1"; }

MODE="$( [[ $APPLY == 1 ]] && echo 真跑 || echo dry-run )"
say "═══ 供裝 ${DST_DB}（來源 schema：${SRC_DB}）｜模式：$MODE ═══"

# ── 1. 建庫（不存在才建）──────────────────────────────────────
EXISTS="$(dex psql -U "$DB_USER" -d postgres -tA -c "SELECT 1 FROM pg_database WHERE datname='$DST_DB'" || true)"
if [[ "$EXISTS" == "1" ]]; then
  say "1. database 已存在 → 跳過建立"
elif [[ $APPLY == 1 ]]; then
  say "1. 建立 database $DST_DB"
  dex psql -U "$DB_USER" -d postgres -q -c "CREATE DATABASE $DST_DB"
else
  say "1. 🔸 [dry-run] 會建立 database $DST_DB"
fi

# ── 2. schema-only 還原（不含任何資料列）─────────────────────
SCHEMA_SQL="${TMPDIR:-/tmp}/aichatbot_test_schema.sql"
if [[ $APPLY == 1 ]]; then
  say "2. 還原 schema（--schema-only，零資料列）"
  dex pg_dump -U "$DB_USER" -d "$SRC_DB" --schema-only --no-owner --no-privileges > "$SCHEMA_SQL"
  docker exec -i "$PG_CONTAINER" psql -U "$DB_USER" -d "$DST_DB" -q < "$SCHEMA_SQL" >/dev/null 2>&1 || true
  rm -f "$SCHEMA_SQL"
else
  say "2. 🔸 [dry-run] 會以 pg_dump --schema-only 自 $SRC_DB 還原結構"
fi

# ── 3. 最小 seed（表驅動；順序即 FK 依賴順序）────────────────
#   knowledge_base 只灌「對話規則＋系統脈絡」＝ Face configs／system context／dialogue rules。
#   ⚠️ form_schemas 是**必備而非可選**：form_sessions.form_id 有 FK 指向它，
#      面向會話一律以 form_id='conversational' 落地——缺它則任何面向執行測試都會
#      ForeignKeyViolationError（2026-08-23 實跑逼出，原最小清單漏列）。
#   ❌ 仍**不供裝**：完整 KB（category 不在上述兩類者）、embedding、semantic-model index。
SEED_TABLES=(
  "vendors|TRUE"
  "vendor_configs|TRUE"
  "form_schemas|TRUE"
  "knowledge_base|category IN ('對話規則','系統脈絡')"
)

seed_table() {
  local tbl="$1" where="$2" cols n tsv
  cols="$(psql_src "SELECT string_agg(quote_ident(column_name), ',' ORDER BY ordinal_position) FROM information_schema.columns WHERE table_name='${tbl}'")"
  n="$(psql_src "SELECT count(*) FROM ${tbl} WHERE ${where}")"
  say "   ・${tbl}（WHERE ${where}）→ ${n} 列"
  [[ ${APPLY} == 1 ]] || return 0
  tsv="${TMPDIR:-/tmp}/aichatbot_test_seed_${tbl}.tsv"
  psql_dst "DELETE FROM ${tbl} WHERE ${where}" >/dev/null
  psql_src "COPY (SELECT ${cols} FROM ${tbl} WHERE ${where}) TO STDOUT" > "${tsv}"
  docker exec -i "${PG_CONTAINER}" psql -U "${DB_USER}" -d "${DST_DB}" -q -v ON_ERROR_STOP=1 \
      -c "COPY ${tbl} (${cols}) FROM STDIN" < "${tsv}"
  rm -f "${tsv}"
}

say "3. 最小 seed（可重入：先清同範圍再灌）"
for spec in "${SEED_TABLES[@]}"; do
  seed_table "${spec%%|*}" "${spec#*|}"
done

# ── 4. 驗收 ──────────────────────────────────────────────────
if [[ ${APPLY} == 1 ]]; then
  say "4. 驗收"
  psql_dst "SELECT '   表數='||count(*) FROM information_schema.tables WHERE table_schema='public'"
  for spec in "${SEED_TABLES[@]}"; do
    t="${spec%%|*}"
    psql_dst "SELECT '   ${t}='||count(*) FROM ${t}"
  done
  psql_dst "SELECT '   ⚠️ 未供裝的 KB 列（應為 0）='||count(*) FROM knowledge_base WHERE category NOT IN ('對話規則','系統脈絡')"
  say "✅ 供裝完成。測試連線用：DB_ENV=test DB_NAME=${DST_DB}"
else
  say "4. （dry-run 不驗收）加 --apply 才真跑"
fi
