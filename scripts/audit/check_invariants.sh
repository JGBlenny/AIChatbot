#!/usr/bin/env bash
# check_invariants.sh — 系統不變量稽核（「靠人記得」→「靠腳本抓」）
#
# 源起：條件診斷：帳單漏掛對話規則（表單→面向半遷移靠人工盤點，漏一格 = 死路，
# 系統回測 run307 才現形）。同族前科：容器舊引擎、evaluation 雙重編碼。
# 本腳本把已知不變量寫死，部署前/定期執行；違反 → exit 1（可掛 CI）。
#
# 用法：make audit（或直接 scripts/audit/check_invariants.sh）
# 觸發時機：①統一部署 runbook 的最後一步（必跑）②修任何回測/面向/知識工程後
#          ③建知識補齊迴圈前（確保測的是一致的系統）
#
# ── 維護準則（改這支腳本時遵守）──
# 1. 修掉一類 bug ＝ 加一條不變量：凡是「本該永遠成立、壞了會靜默」的事實，
#    修復收案時把檢查加進來（十行 SQL/shell 換一類 bug 永久絕版）。
# 2. 豁免必須帶理由註解：說得出「為什麼這格不需要」才能進豁免清單；說不出＝掛帳 WARN。
# 3. 掛帳收編後從 WARN 清單移除——WARN 清單只准變短，變長要有新掛帳的立案紀錄。
# 4. 不變量 3 的 SYNC_FILES：新增「會被服務容器 in-process 載入的關鍵檔」時同步補列。
# 5. FAIL 才擋部署；WARN 是待辦雷達，不擋——避免稽核疲勞讓人習慣性跳過。
set -uo pipefail

PSQL="docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -t -A"
FAIL=0

echo "═══ 不變量 1：動作知識必有面向接管（或明確豁免）═══"
# 豁免（有意為之，非漏網；2026-07-06 六筆掛帳處置定案）：
#   b2c 租客域舊表單體系（未面向化，target_user 含 tenant）
#   售前顧問（mode=all 角色級面向，進場靠 persona 非 category）
#   3508 IoT 綁定診斷：表單為廠商選擇分流 by design，被綁定查核屬 DB/客服範疇
#   3522 提前解約發起方：表單為發起方分流（違約金規則依發起方而異），合理歧義收斂
# 掛帳（WARN 不 FAIL；J 清單待 jgb2 上游端點，立案見 audit 報告 20260706）：
#   3514 租客管理／3365+1558 修繕——現行 API 為租客身分制（需該租客 user_id），
#   業者用「租客名/物件名」識別需 jgb2 新增名稱檢索端點才能面向化
VIOLATIONS=$($PSQL -c "
WITH rule_cats AS (
  SELECT DISTINCT generation_metadata->'conversational_config'->'topic_scope'->>'category' AS cat
  FROM knowledge_base WHERE category='對話規則' AND is_active
)
SELECT k.id || '|' || k.question_summary
FROM knowledge_base k
WHERE k.is_active
  AND (k.form_id IS NOT NULL OR k.action_type IN ('form_fill','api_call','form_then_api'))
  AND NOT EXISTS (SELECT 1 FROM rule_cats r WHERE r.cat = ANY(k.categories))
  AND NOT ('tenant' = ANY(COALESCE(k.target_user, ARRAY[]::text[])))         -- 豁免：b2c 舊表單體系
  AND NOT ('售前顧問' = ANY(COALESCE(k.categories, ARRAY[]::text[])))          -- 豁免：角色級面向
  AND k.id NOT IN (3508, 3522)                                                -- 豁免：分流表單 by design
  AND k.id NOT IN (3514, 3365, 1558)                                          -- 掛帳：J 清單（見 WARN）
  AND NOT (k.categories IS NULL AND k.target_user IS NULL)                    -- 豁免：遠古 b2c 列（雙空標注；
                                                                              --   1396/1397 社區資訊類，範疇外裁定 2026-07-06；資料清理候選）
")
if [ -n "$VIOLATIONS" ]; then
  echo "❌ FAIL：以下動作知識無面向接管且不在豁免/掛帳清單："
  echo "$VIOLATIONS"
  FAIL=1
else
  echo "✅ PASS"
fi
WARN=$($PSQL -c "
SELECT count(*) FROM knowledge_base k
WHERE k.is_active AND (k.form_id IS NOT NULL OR k.action_type IN ('form_fill','api_call','form_then_api'))
  AND k.id IN (3514, 3365, 1558)")
echo "⚠️  掛帳（J 清單待 jgb2 名稱檢索端點）：$WARN 筆（3514 租客管理／3365+1558 修繕）"

echo ""
echo "═══ 不變量 2：backtest_results.evaluation 必須是 JSON 物件（非字串）═══"
BAD_EVAL=$($PSQL -c "SELECT count(*) FROM backtest_results WHERE jsonb_typeof(evaluation)='string'")
if [ "$BAD_EVAL" != "0" ]; then
  echo "❌ FAIL：$BAD_EVAL 筆雙重編碼（修復 SQL 見 seed_bill_diagnosis 收案紀錄）"
  FAIL=1
else
  echo "✅ PASS"
fi

echo ""
echo "═══ 不變量 3：服務容器內關鍵檔案與本地一致 ═══"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
SYNC_FILES=(
  scripts/backtest/backtest_framework_async.py
  scripts/backtest/run_backtest_with_db_progress.py
  services/knowledge_completion_loop/backtest_client.py
  services/conversational_engine.py
  services/jgb_system_api.py
  services/jgb/bills.py
  routers/chat.py
  routers/loops.py
)
for f in "${SYNC_FILES[@]}"; do
  C=$(docker exec aichatbot-rag-orchestrator md5sum "/app/$f" 2>/dev/null | awk '{print $1}')
  L=$(md5 -q "$REPO/rag-orchestrator/$f" 2>/dev/null || md5sum "$REPO/rag-orchestrator/$f" 2>/dev/null | awk '{print $1}')
  if [ "$C" != "$L" ]; then
    echo "❌ FAIL：$f 容器與本地不一致（docker cp + restart，或重建 image）"
    FAIL=1
  fi
done
[ $FAIL -eq 0 ] && echo "✅ PASS"

echo ""
echo "═══ 不變量 4：每個面向 category 必有系統脈絡知識 ═══"
NO_CTX=$($PSQL -c "
SELECT r.generation_metadata->'conversational_config'->'topic_scope'->>'category'
FROM knowledge_base r
WHERE r.category='對話規則' AND r.is_active
  AND r.generation_metadata->'conversational_config'->'topic_scope'->>'mode' = 'category'
  AND NOT EXISTS (
    SELECT 1 FROM knowledge_base c
    WHERE c.is_active AND c.question_summary LIKE '系統脈絡：%'
      AND (c.category = r.generation_metadata->'conversational_config'->'topic_scope'->>'category'
           OR (r.generation_metadata->'conversational_config'->'topic_scope'->>'category') = ANY(COALESCE(c.categories, ARRAY[]::text[]))))")
if [ -n "$NO_CTX" ]; then
  echo "⚠️  WARN：以下面向 category 查無系統脈絡知識（確認是否輕引導型免脈絡）："
  echo "$NO_CTX"
else
  echo "✅ PASS"
fi

echo ""
if [ $FAIL -eq 0 ]; then
  echo "🎉 稽核通過（$(date +%Y-%m-%d))"
else
  echo "💥 稽核未過——修復後重跑"
fi
exit $FAIL
