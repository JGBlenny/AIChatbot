#!/usr/bin/env bash
# 帳本感知部署 runner（2026-07-25；v2 加 seed 批）
#   A. SQL 批：讀 schema_migrations → 只跑未套的 .sql → 逐支記帳；破壞性(DROP/TRUNCATE)自動跳過。
#   B. Seed 批：讀 seeds.manifest（需 embedding 的知識 seed／補嵌）→ once 支未記帳才跑並記帳；always 支每次跑。
#   冪等；出錯即停；預設 dry-run，加 --apply 才真跑。
#
# 用法（repo 根目錄；prod 上 cd /home/ec2-user/AIChatbot）：
#   bash rag-orchestrator/database/migrate.sh            # dry-run：列 SQL＋seed 待辦
#   bash rag-orchestrator/database/migrate.sh --apply    # 真跑（seed 批需 DB_PASSWORD＋EMBEDDING_API_URL）
#
# 前提：schema_migrations 帳本表已存在（§17）。prod 帳本若未回填 facet 大批，先手動跑
#       20260722_schema_migrations_ledger.sql 再用本 runner，避免重跑已上線的 facet 批。
set -euo pipefail

PG_CONTAINER="${PG_CONTAINER:-aichatbot-postgres}"
DB_USER="${DB_USER:-aichatbot}"
DB_NAME="${DB_NAME:-aichatbot_admin}"
HERE="$(cd "$(dirname "$0")" && pwd)"
MIG_DIR="${MIG_DIR:-$HERE/migrations}"
SEED_MANIFEST="${SEED_MANIFEST:-$HERE/seeds.manifest}"
REPO_ROOT="${REPO_ROOT:-$(cd "$HERE/../.." && pwd)}"

APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

psql_q() { docker exec "$PG_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tA -c "$1"; }  # 無 -i：-c 不需 stdin，避免吃掉迴圈 manifest
psql_file() { docker exec -i "$PG_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 < "$1"; }

applied="$(psql_q "SELECT migration_name FROM schema_migrations" 2>/dev/null || true)"
is_applied() { grep -qxF "$1" <<<"$applied"; }
is_destructive() { grep -qiE "DROP[[:space:]]+COLUMN|DROP[[:space:]]+TABLE|TRUNCATE[[:space:]]" "$1"; }
record() { psql_q "INSERT INTO schema_migrations (migration_name, created_by) VALUES ('$1','migrate.sh') ON CONFLICT (migration_name) DO NOTHING;" >/dev/null; }

echo "帳本已套：$(grep -c . <<<"$applied" || echo 0) 支｜模式：$([[ $APPLY == 1 ]] && echo 真跑 || echo dry-run)"

# ── A. SQL 批 ───────────────────────────────────────────────
echo "═══ A. SQL migrations ═══"
sql_ran=0; sql_skip=0; sql_destr=0
for f in $(ls "$MIG_DIR"/*.sql 2>/dev/null | sort); do
  name="$(basename "$f" .sql)"
  # ⚠️ **rollback 檔永遠不得被當成 migration 套用**（2026-08-26 P2.2 dry-run 抓到）：
  #    慣例是放 migrations/rollback/（glob 掃不到），但曾有檔案落在主目錄，
  #    於是 runner 會「先套 seed、再立刻把它 rollback」——淨效果是什麼都沒發生，
  #    而且帳本會記成兩支都已套。放錯位置不該造成錯誤結果，故在此再擋一層。
  case "$name" in *rollback*|*.rollback) echo "↩️  rollback 檔·跳過（不得自動套用）：$name"; continue;; esac
  if is_applied "$name"; then sql_skip=$((sql_skip+1)); continue; fi
  if is_destructive "$f"; then echo "⚠️  破壞性·跳過（手動跑並記帳）：$name"; sql_destr=$((sql_destr+1)); continue; fi
  if [[ $APPLY == 1 ]]; then
    echo "▶️  套用：$name"; psql_file "$f"; record "$name"; echo "   ✅ 已套並記帳：$name"
  else echo "🔸 待跑：$name"; fi
  sql_ran=$((sql_ran+1))
done
echo "SQL：待跑/已跑 ${sql_ran}｜已套跳過 ${sql_skip}｜破壞性跳過 ${sql_destr}"

# ── B. Seed 批（需 embedding 的知識 seed／補嵌）────────────────
echo "═══ B. Seeds（seeds.manifest）═══"
seed_pending=0; seed_done=0; seed_skip=0
if [[ -f "$SEED_MANIFEST" ]]; then
  # 先掃一遍算 pending（決定要不要檢查 env）
  while IFS=$'\t' read -r -u 3 mode ledger cmd; do
    [[ -z "${mode:-}" || "$mode" == \#* ]] && continue
    if [[ "$mode" == "once" ]] && is_applied "$ledger"; then continue; fi
    seed_pending=$((seed_pending+1))
  done 3< "$SEED_MANIFEST"

  if [[ $APPLY == 1 && $seed_pending -gt 0 ]]; then
    : "${DB_PASSWORD:?seed 批需設 DB_PASSWORD（prod DB 密碼）}"
    : "${EMBEDDING_API_URL:?seed 批需設 EMBEDDING_API_URL}"
  fi

  while IFS=$'\t' read -r -u 3 mode ledger cmd; do
    [[ -z "${mode:-}" || "$mode" == \#* ]] && continue
    if [[ "$mode" == "once" ]] && is_applied "$ledger"; then
      echo "⏭️  已記帳跳過：$ledger"; seed_skip=$((seed_skip+1)); continue
    fi
    if [[ $APPLY == 1 ]]; then
      echo "▶️  seed（${mode}）：${ledger} → ${cmd}"
      ( cd "$REPO_ROOT" && eval "$cmd" ) </dev/null
      [[ "$mode" == "once" ]] && { record "$ledger"; echo "   ✅ 已跑並記帳：$ledger"; } || echo "   ✅ 已跑（always，不記帳）：$ledger"
      seed_done=$((seed_done+1))
    else
      echo "🔸 待跑 seed（${mode}）：${ledger} → ${cmd}"
    fi
  done 3< "$SEED_MANIFEST"
else
  echo "（無 seeds.manifest，略過）"
fi
echo "Seed：待跑 ${seed_pending}｜已跑 ${seed_done}｜已記帳跳過 ${seed_skip}"

echo "───────────────────────────────────────────────"
[[ $APPLY == 0 ]] && echo "（dry-run；確認後加 --apply 真跑。seed 批 --apply 需 DB_PASSWORD＋EMBEDDING_API_URL）"
exit 0
