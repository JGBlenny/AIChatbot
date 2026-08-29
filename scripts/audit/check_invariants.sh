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

# ── 兩類紅燈必須分開記帳（業主定案 2026-08-29）──
# 一條**長期預期**的紅燈（產品決策未定）會壓低整份稽核的信噪比：其他不變量真的壞了
# 也只看到一個 ❌ AUDIT FAILED。但把它抽離主入口又更糟——`make audit → green` 會讓
# 「程式碼健康」被偷偷等同於「candidate architecture healthy」，重新製造 false green。
# ⇒ 紅**仍有阻擋力**（OVERALL 仍 FAIL），但**不同的紅不互相掩蓋**。
CODE_REGRESSIONS=()   # 程式契約回歸：修好就該綠
PRODUCT_BLOCKERS=()   # 產品／population blocker：等的是決策，不是修 bug

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
  services/jgb/repair_prefill.py
  services/instance_reference_gate.py
  services/instance_applicability.py
  routers/chat.py
  routers/loops.py
  services/usage_metering.py
  services/decision_layer.py
  services/base_retriever.py
  services/llm_provider.py
  services/llm_answer_optimizer.py
  services/api_call_handler.py
  services/vendor_parameter_resolver.py
  routers/lookup.py
  app.py
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
echo "═══ 不變量 5：usage-metering 計量健全（spec usage-metering R8.4）═══"
# 漏標鐵證：內部前綴 session 卻未標 internal → FAIL（統計/計費直接失真）
LEAK=$($PSQL -c "
SELECT count(*) FROM usage_events
WHERE is_internal = FALSE
  AND (session_id LIKE 'backtest\_%' OR session_id LIKE 'loop\_%' OR session_id LIKE 'smoke\_%')")
if [ "${LEAK:-0}" != "0" ]; then
  echo "❌ FAIL：$LEAK 筆內部前綴事件未標 is_internal（INTERNAL_RULES 漏網）"
  FAIL=1
else
  echo "✅ PASS"
fi
# 維度缺失雷達：近 24h 非內部事件 vendor_id 缺失 >5% → WARN（呼叫端沒帶 vendor）
MISS=$($PSQL -c "
SELECT COALESCE(round(100.0 * count(*) FILTER (WHERE vendor_id IS NULL) / NULLIF(count(*),0)), 0)
FROM usage_events WHERE is_internal = FALSE AND ts > now() - interval '24 hours'")
if [ "${MISS:-0}" -gt 5 ] 2>/dev/null; then
  echo "⚠️  WARN：近 24h 非內部事件 vendor_id 缺失 ${MISS}%（>5%，查呼叫端）"
fi

echo ""
echo "═══ 不變量 6：quota-management 額度一致（spec quota-management R5.5）═══"
# 幽靈攔截：有 blocked 事件的 vendor 卻「從未設定過」額度 → FAIL（不可能的狀態）
#   （設定後停用屬合法營運動作——24h 窗內殘留攔截事件只 WARN 不 FAIL）
GHOST=$($PSQL -c "
SELECT count(DISTINCT e.vendor_id) FROM usage_events e
WHERE e.status = 'blocked'
  AND e.ts > now() - interval '24 hours'
  AND NOT EXISTS (SELECT 1 FROM vendor_quotas q WHERE q.vendor_id = e.vendor_id)")
if [ "${GHOST:-0}" != "0" ]; then
  echo "❌ FAIL：$GHOST 個 vendor 近 24h 有攔截事件但額度表無此列（幽靈攔截）"
  FAIL=1
else
  echo "✅ PASS"
fi
DEACT=$($PSQL -c "
SELECT count(DISTINCT e.vendor_id) FROM usage_events e
WHERE e.status = 'blocked' AND e.ts > now() - interval '24 hours'
  AND EXISTS (SELECT 1 FROM vendor_quotas q
              WHERE q.vendor_id = e.vendor_id AND NOT q.is_active)")
if [ "${DEACT:-0}" != "0" ] 2>/dev/null; then
  echo "⚠️  WARN：$DEACT 個 vendor 額度已停用但 24h 內曾攔截（確認停用是否符合預期）"
fi
# 寬限模式燒錢雷達：用量超過額度 120% 且未攔截 → WARN
BURN=$($PSQL -c "
SELECT count(*) FROM vendor_quotas q
JOIN (SELECT vendor_id, count(*) AS used FROM usage_events
      WHERE date_tpe >= date_trunc('month', now() AT TIME ZONE 'Asia/Taipei')::date
        AND is_internal = FALSE AND status <> 'blocked' GROUP BY vendor_id) u
  ON u.vendor_id = q.vendor_id
WHERE q.is_active AND q.block_on_exceed = FALSE
  AND u.used > q.monthly_message_quota * 1.2")
if [ "${BURN:-0}" != "0" ] 2>/dev/null; then
  echo "⚠️  WARN：$BURN 個寬限模式團隊用量已超額 120%（持續燒 LLM 成本，考慮改攔截或加值）"
fi

echo ""
echo "═══ 不變量 7：JGB 金額欄位一律走語義層（20260810 真對話重播 P1-a）═══"
# 源起：`_diagnose_receipt` 直接寫 `bill.get("final_total", bill.get("total"))`，
# 而 jgb2 external API 把 null 壓成 (float) 0（BillApiController）→ key 存在不 fallback
# → 已繳費帳單 716317 被答成「收據金額 NT$ 0」。錯誤實值比查無更傷。
# 不變量：services/jgb/ 內除 bills.py 的語義層（_bill_amount_due/_bill_amount_received）
# 外，任何檔案都不得直接讀 final_total——狀態走 _bill_status 的同一範式。
# 允許清單只有一行：語義層本體的取值。註解行（含說明 jgb2 語義的段落）不算違反。
#
# 2026-08-27 修正誤報：`fixtures.py`（2026-08-24 加入）是 External API 投影的**合成產生端**，
# 欄位名逐鍵對齊 jgb2 `formatBill`，其檔頭明文「不得新增真 API 不存在的欄位」——
# 它**不可能**不寫出 `final_total` 這個鍵，否則 fixture 就不再是 API 的實際投影。
# ⚠️ 但**不是**整檔豁免：本不變量管的是「讀值繞過語義層」，
#    所以 fixtures.py 內只放行型別／資料宣告，**讀值形式照樣違反**
#    （`.get(`／`["final_total"]`／`.final_total`）——否則消費端只要搬進 fixtures.py 就隱形了。
AMOUNT_VIOL=$(grep -rn 'final_total' rag-orchestrator/services/jgb/ 2>/dev/null \
  | awk -F: '{ body = $0; sub(/^[^:]*:[0-9]+:/, "", body);
               if (body ~ /^[[:space:]]*#/) next;
               if ($1 ~ /bills\.py$/ && body ~ /^[[:space:]]*v = bill\.get\("final_total"\)$/) next;
               if ($1 ~ /fixtures\.py$/) {
                 if (body ~ /get\(|\.final_total|\[[[:space:]]*"final_total"/) print;
                 next; }
               print }' || true)
if [ -n "$AMOUNT_VIOL" ]; then
  echo "❌ FAIL：以下位置直接讀 final_total，未經金額語義層："
  echo "$AMOUNT_VIOL"
  FAIL=1
else
  echo "✅ PASS"
fi

echo ""
echo "═══ 不變量 8：決策層門檻唯一讀值點（retrieval-decision-layer R7.4）═══"
# 源起：KB_SIMILARITY_THRESHOLD ×4＋FORM_TRIGGER_THRESHOLD ×2 散落讀值＋六 case 硬編碼
# 常數，檢索側任何改動直接翻轉路由（前身 spec 撤案教訓 4）。
# 2026-08-19 改 AST（D-20）：原 grep 版實測 8 種規避寫法只擋 1 種——os.environ[]／
# os.environ.get／別名 import／字串拼接／變數間接／**甚至多一個空格**皆繞過；常數檢查
# 對 _SOP_MIN=0.6／型別註記／dict 形式亦無感。字面比對防不住無意的重構或排版。
# 檢查器自帶規避測試（--self-test），先驗「擋得住」再驗 repo（D-20 要求）。
DL_CHECK="$REPO/scripts/audit/checks/decision_threshold_ast.py"
if ! python3 "$DL_CHECK" --self-test >/dev/null 2>&1; then
  echo "❌ FAIL：不變量 8 檢查器的規避測試未過（檢查器本身失效，其 PASS 不可信）"
  python3 "$DL_CHECK" --self-test
  FAIL=1
elif ! DL_OUT=$(python3 "$DL_CHECK" 2>&1); then
  echo "$DL_OUT"
  FAIL=1
else
  echo "✅ PASS（含 10 種規避寫法自我測試）"
fi

echo "═══ 不變量 9：Face preemption 的能力保全（2026-08-29 21 筆 census 逼出）═══"
# 源起：面向分支在表單分支**之前**（chat.py，同一個 form_trigger_threshold），
# 且 resolver allowlist 未涵蓋的面向一律回 FACE_UNEVALUATED → face_precedence 判 "face"
# → **無條件 commit** ⇒ 知識掛的 active 表單永遠不會開，且靜默無訊號。
# 2026-07 面向化遷移期沒有做過「這筆知識原本由誰服務」的反向盤查，本不變量補上。
# ⚠️ 檢查器用 grounding_scope.select=api／execute_endpoint 當「能力等價」的**可證代理**，
#    ⛔ 那不是產品公理——出現別種等價能力時要改述詞，不是把違規列進豁免。
FP_CHECK="$REPO/scripts/audit/checks/face_preemption_capability.py"
if ! python3 "$FP_CHECK" --self-test >/dev/null 2>&1; then
  echo "❌ FAIL：不變量 9 檢查器的自我測試未過（檢查器本身失效，其 PASS 不可信）"
  python3 "$FP_CHECK" --self-test
  FAIL=1
elif ! FP_OUT=$(python3 "$FP_CHECK" 2>&1); then
  echo "$FP_OUT"
  FAIL=1
else
  echo "$FP_OUT"
  echo "✅ PASS（含 A／A'／B／C／C' 五形狀 ＋ 兩組突變控制）"
fi

echo "═══ 不變量 10：instance applicability 的三態資料契約（U1／P1a）═══"
# 源起：決定「該不該由 Face 擁有」的屬性——「回答這題需不需要使用者自己的資料」——
# **沒有被任何欄位記錄**。架構早就留了位置（grounding_scope.requires_instance_reference），
# 但實查宣告數＝0 ⇒ instance gate 條件 C 恆為 False
# ⇒ 授權機制是在一個**授權輸入結構性缺席**的系統上被評估的。
# 守兩件事：①值域封閉（只准 instance／general，⛔ 不猜變體）
#          ②讀取唯一化（宣告鍵只能經 services/instance_applicability.py 讀，
#            否則遲早出現「缺宣告當 general」或「用 form_id 推導」的 fallback）
# ⚠️ P1a/P1b 階段不要求 coverage；**P1d 起改為分期要求**：
#    2026-08-30 之後建立／修改的情境知識未宣告 → FAIL（UNKNOWN 只允許 legacy）。
#    ⚠️ **Level-A gate scope（bill_diagnosis）另有更嚴的一條、無 legacy 豁免**：
#       提名到它的知識必須 100% 明示——UNKNOWN 在該處等於「授權輸入缺席」，
#       正是整條 U1／P1 線要根除的狀態（2026-08-29 已閉合 10/10）。
#    ⇒ 存量可慢慢回填，但**不再長出新的洞**。治理規則見 .kiro/steering/knowledge.md。
IA_CHECK="$REPO/scripts/audit/checks/instance_applicability_contract.py"
if ! python3 "$IA_CHECK" --self-test >/dev/null 2>&1; then
  echo "❌ FAIL：不變量 10 檢查器的自我測試未過（檢查器本身失效，其 PASS 不可信）"
  python3 "$IA_CHECK" --self-test
  FAIL=1
elif ! IA_OUT=$(python3 "$IA_CHECK" 2>&1); then
  echo "$IA_OUT"
  FAIL=1
else
  echo "$IA_OUT"
  echo "✅ PASS（含值域變體與越權讀取的正控制）"
fi

echo "═══ 不變量 11：routing authority 的 producer-consumer transport contract ═══"
# 源起（2026-08-29，A03 抓到的 integration false-green）：P1f 的 gate 讀 knowledge 的
# applicability 宣告，consumer 已接線、契約已存在——但 retriever 回傳的知識列**沒有那個欄位**
# ⇒ production 上 109/109 一律讀到 UNKNOWN、一律 suppress。
# ⚠️ 而 P1f 的 23 條單元測試全過，因為它們餵的是手寫 {"generation_metadata": {...}}
#    ——**production 從不產生的形狀**。
# 不變量：任何 routing authority consumer 所需的 semantic contract，
#        必須由其 **production producer shape** 明示提供；
#        ⛔ fixture 不得擁有 production producer 不可能提供的 authority 欄位。
# 判定：consumer 從知識列讀取的鍵（含常數間接）⊆ producer 回傳 dict 的鍵。
AT_CHECK="$REPO/scripts/audit/checks/authority_transport_contract.py"
if ! python3 "$AT_CHECK" --self-test >/dev/null 2>&1; then
  echo "❌ FAIL：不變量 11 檢查器的自我測試未過（檢查器本身失效，其 PASS 不可信）"
  python3 "$AT_CHECK" --self-test
  FAIL=1
elif ! AT_OUT=$(python3 "$AT_CHECK" 2>&1); then
  echo "$AT_OUT"
  FAIL=1
else
  echo "$AT_OUT"
  echo "✅ PASS（含常數間接解析 ＋ 植入缺漏的正對照）"
fi

echo "═══ 不變量 12：retrieval semantic contract 與 scoring surface 的單一實作（D1/D2/D3）═══"
# 源起（2026-08-29，R8）：系統宣告某 row 承接的責任**比** scoring 看到的文字更寬
# ⇒ 4656 的 capability 是「該筆帳單完整現況」，surface 卻連「已繳／未繳」都沒有。
# 更深一層：scoring surface 過去**沒有單一實作點**——embedding 端與 reranker 端
# 各自寫一份 `question_summary or answer` 優先序 ⇒ 兩份實作＝兩個 semantic universe。
# 不變量：① scoring 文字由唯一契約函式決定；② 宣告讀取器⛔不得 fallback 猜測；
#        ③ 任何 stage-specific divergence 必須在登記簿上明示（D2）。
RR_CHECK="$REPO/scripts/audit/checks/retrieval_representation_contract.py"
if ! python3 "$RR_CHECK" --self-test >/dev/null 2>&1; then
  echo "❌ FAIL：不變量 12 檢查器的自我測試未過（檢查器本身失效，其 PASS 不可信）"
  python3 "$RR_CHECK" --self-test
  FAIL=1
elif ! RR_OUT=$(python3 "$RR_CHECK" 2>&1); then
  echo "$RR_OUT"
  FAIL=1
else
  echo "$RR_OUT"
  echo "✅ PASS（含 alias 傳遞掃描 ＋ 四項各自的正對照）"
fi

echo "═══ 不變量 14：late-fee instance ownership 單一化（T1／Step 2）═══"
# 源起：`bill_diagnosis._diagnose_late_fee`（A）與 `滯納金.build_late_fee_facts`（B）
# 曾同時承接「這一筆的滯納金診斷」；T1 決定性比對判 A 為 partial implementation，
# 且在合約列／滯納金帳單列輸出**錯誤語義** ⇒ 收斂單一 owner B，precedence REJECTED。
# 不變量：① late-fee intent ⛔ 不得由 bill_diagnosis 收斂作答（含 generic path——
#        只刪 dispatch 而落 generic 是「錯誤綠燈」）；② `_DIAG_KEYWORDS` 必須不變
#        （generic discriminator，動它會誤傷發送／取消／手動到帳）。
LF_CHECK="$REPO/scripts/audit/checks/late_fee_ownership.py"
if ! python3 "$LF_CHECK" --self-test >/dev/null 2>&1; then
  echo "❌ FAIL：不變量 14 檢查器的自我測試未過（檢查器本身失效，其 PASS 不可信）"
  python3 "$LF_CHECK" --self-test
  FAIL=1
elif ! LF_OUT=$(python3 "$LF_CHECK" 2>&1); then
  echo "$LF_OUT"
  FAIL=1
else
  echo "$LF_OUT"
  echo "✅ PASS（含關閉判定／誤傷／動 _DIAG_KEYWORDS 三組正對照）"
fi

echo "═══ 不變量 15：退役 row 不得回到 active 路徑（T2／3498 停用）═══"
# 源起：3498 判 K1 FULLY_SUBSUMED + UNDER_QUALIFIED_DUPLICATE 後停用。
# mutation 實測：改回 active 時，三個 late-fee 查詢中**兩個**它回到 **rank 1**，
# 與真正 owner（3939/3940）直接競爭排序 ⇒「保留重複 knowledge 會重製 ranking
# competition」的實證。
# 不變量：① 標記 retirement 的 row 必須 is_active=false；
#        ② 知識檢索每個 SELECT 都要以 is_active 過濾。
# ⚠️ 「失效不失憶」：⛔ 不要求刪宣告／provenance（刪了 A04 等舊證據無法解讀）。
RR_ISO="$REPO/scripts/audit/checks/retired_row_isolation.py"
if ! python3 "$RR_ISO" --self-test >/dev/null 2>&1; then
  echo "❌ FAIL：不變量 15 檢查器的自我測試未過（檢查器本身失效，其 PASS 不可信）"
  python3 "$RR_ISO" --self-test
  FAIL=1
elif ! RI_OUT=$(python3 "$RR_ISO" 2>&1); then
  echo "$RI_OUT"
  FAIL=1
else
  echo "$RI_OUT"
  echo "✅ PASS（含退役仍 active／SELECT 漏過濾 兩組正對照）"
fi

echo "═══ 不變量 16：entry alias 不得各自擁有 semantic contract（T3 裁定）═══"
# 源起：billing-knowledge-review.md 明文「錨點（12 筆，answer 空、**一種講法一筆**）」，
# 且批次 schema 每筆只有 facet/question/keywords ⇒ 錨點單位是**講法**、責任單位是 facet。
# 不變量：同一 facet 底下的 entry alias ⛔ 不得擁有**彼此不同**的 authoritative
#        retrieval_representation——那是發明不存在的 responsibility distinction。
# ⚠️ 允許：全部未宣告（現況）／同 facet 共用逐字相同的 canonical contract。
# ⚠️ ⛔ 本不變量不要求退役任何 alias（KEEP_BOTH_AS_ENTRY_VARIANTS 是業主定案）。
EA_CHECK="$REPO/scripts/audit/checks/entry_alias_contract.py"
if ! python3 "$EA_CHECK" --self-test >/dev/null 2>&1; then
  echo "❌ FAIL：不變量 16 檢查器的自我測試未過（檢查器本身失效，其 PASS 不可信）"
  python3 "$EA_CHECK" --self-test
  FAIL=1
elif ! EA_OUT=$(python3 "$EA_CHECK" 2>&1); then
  echo "$EA_OUT"
  FAIL=1
else
  echo "$EA_OUT"
  echo "✅ PASS（含同 facet 分歧／共用／單列宣告 三組對照）"
fi

echo "═══ 不變量 17：R10-P governance population 的集合身分（P0）═══"
# 源起：產 P0 母體時 SQL 的 NULL 傳遞讓 census **少列而不報錯**（兩次：NULL summary、
# NULL generation_metadata）——12 個 alias 中 10 個被靜默吞掉，母體只剩 44 卻「看起來正常」。
# 不變量：expected IDs == emitted IDs == distinct IDs == 54，且 **ID-set digest 相符**。
# ⚠️ 只比 COUNT(*)=54 不夠——「少一列、意外多另一列」會假綠。
# ⚠️ 母體漂移一律 FAIL：review 中途 governance population ⛔ 不得靜默長大，
#    需明示版本決策（比照 LEVEL_A_V1→V2）。
RP_CHECK="$REPO/scripts/audit/checks/r10p_population_integrity.py"
if ! python3 "$RP_CHECK" --self-test >/dev/null 2>&1; then
  echo "❌ FAIL：不變量 17 檢查器的自我測試未過（檢查器本身失效，其 PASS 不可信）"
  python3 "$RP_CHECK" --self-test
  FAIL=1
elif ! RP_OUT=$(python3 "$RP_CHECK" 2>&1); then
  echo "$RP_OUT"
  FAIL=1
else
  echo "$RP_OUT"
  echo "✅ PASS（含少一列／少一多一／母體漂移 三組正對照）"
fi

echo "═══ 不變量 18：R10-P2 proposal 的分割身分與 authority 邊界（P2）═══"
# 源起：17 擋的是「母體少列而不報錯」；proposal 有**第二種**同形失效——
# 54 列分群後某列被漏掉、或同時出現在兩群，而 `sum(len(members))` 仍是 54 ⇒ 假綠。
# 另擋 authority 偷渡：proposal ⛔ 不得帶 responsibility_id／applicability／review_status，
# 且**多列合併**只允許來自 entry-alias registry（本母體上唯一能產生合併的允許規則）。
RPP_CHECK="$REPO/scripts/audit/checks/r10p_proposal_integrity.py"
if ! python3 "$RPP_CHECK" --self-test >/dev/null 2>&1; then
  echo "❌ FAIL：不變量 18 檢查器的自我測試未過（檢查器本身失效，其 PASS 不可信）"
  python3 "$RPP_CHECK" --self-test
  FAIL=1
elif ! RPP_OUT=$(python3 "$RPP_CHECK" 2>&1); then
  echo "$RPP_OUT"
  FAIL=1
else
  echo "$RPP_OUT"
  echo "✅ PASS（含漏列／漏一多一／authority 偷渡／禁用規則合併 四組正對照）"
fi

echo "═══ 不變量 19：R10-P3 裁定紀錄的合法性（P3）═══"
# 源起：SCHEMA-2 把 applicability 拆兩軸，就是為了擋「還沒 review」被序列化成 unknown。
# ⚠️ Batch A 業主再點名第二種偷換：INSUFFICIENT_EVIDENCE ⛔ 不得順手填 value=unknown，
#    也 ⛔ 不得抹掉已 CONFIRMED 的 IDENTITY／MEMBERSHIP。
# 另擋：CONFIRMED_RESPONSIBILITY 必須四項命題**各自**有證據（IDENTITY 不推出 ownership）、
#      evidence 的 supports[] 不得為空、review_basis_digest 必須可重算（⛔ 不得謊報看過什麼）。
P3_CHECK="$REPO/scripts/audit/checks/p3_verdict_legality.py"
if ! python3 "$P3_CHECK" --self-test >/dev/null 2>&1; then
  echo "❌ FAIL：不變量 19 檢查器的自我測試未過（檢查器本身失效，其 PASS 不可信）"
  python3 "$P3_CHECK" --self-test
  FAIL=1
elif ! P3_OUT=$(python3 "$P3_CHECK" 2>&1); then
  echo "$P3_OUT"
  FAIL=1
else
  echo "$P3_OUT"
  echo "✅ PASS（含兩種非法 state／INSUFFICIENT＋unknown／CONFIRMED 缺 ownership／偷加證據 等九組正對照）"
fi

echo "═══ 不變量 20：R10-P4 registry 投影完整性（P4）═══"
# 源起：P4 最容易犯的錯是為了讓「每列剛好一個 responsibility」而**製造 authority**——
# 把 SPLIT 來源列硬塞成第五個責任、或替 INSUFFICIENT_EVIDENCE 的列捏一個 responsibility_id。
# ⚠️ 業主凍結的規則：**P4 要做到 row disposition 完整，⛔ 不是強迫 responsibility assignment 完整。**
# 另擋：canonical_responsibility 被機器代填（schema 明文 ⛔ 不得自動產生後直接生效）。
P4_CHECK="$REPO/scripts/audit/checks/p4_projection_integrity.py"
if ! python3 "$P4_CHECK" --self-test >/dev/null 2>&1; then
  echo "❌ FAIL：不變量 20 檢查器的自我測試未過（檢查器本身失效，其 PASS 不可信）"
  python3 "$P4_CHECK" --self-test
  FAIL=1
elif ! P4_OUT=$(python3 "$P4_CHECK" 2>&1); then
  echo "$P4_OUT"
  FAIL=1
else
  echo "$P4_OUT"
  echo "✅ PASS（含漏掛 split／偽造第五責任／掛錯 target／未解列被塞入／機器代填 canonical 等九組正對照）"
fi

# ⚠️ 13 是最後一條 ⇒ 此刻的 FAIL 值**恰好**等於「其他不變量有沒有紅」。
#    用快照取代事後從輸出回推行數：⛔ 不靠 grep 猜，靠狀態算。
CODE_FAIL_BEFORE_13=$FAIL

echo "═══ 不變量 13：Level-A representation population 完整性（D1；業主定案 2026-08-29）═══"
# ⚠️ 這條紅是**刻意保留**的產品閘：Level-A authority scope 未閉合就不得綠。
# 沿革：4657 曾卡 FACET_TYPE_SELECTION_MISSING（全流程從未讀 type），
# POINT_REFUND_BILL_SELECTION 實作後已解。
# ⛔ 不得為了讓 invariant 變綠而寫一個不忠於 row intent 的 representation；
# ⛔ 不得把 4657 改寫成 4656 的 duplicate 來湊 10/10；⛔ 不得給 legacy exemption。
# 紅燈語義＝**一個 Level-A authority row 的 execution responsibility 尚未成立**。
LA_CHECK="$REPO/scripts/audit/checks/level_a_representation_completeness.py"
if ! python3 "$LA_CHECK" --self-test >/dev/null 2>&1; then
  echo "❌ FAIL：不變量 13 檢查器的自我測試未過（檢查器本身失效，其 PASS 不可信）"
  python3 "$LA_CHECK" --self-test
  FAIL=1
elif ! LA_OUT=$(python3 "$LA_CHECK" 2>&1); then
  echo "$LA_OUT"
  FAIL=1
  # ⚠️ 歸入 **product blocker**：它等的是 4657 的能力決策，⛔ 不是程式碼壞掉。
  PRODUCT_BLOCKERS+=("INV13 / Level-A representation population 未閉合（見 r9-review-status.md）")
else
  echo "$LA_OUT"
  echo "✅ PASS（active version 全數閉合）"
fi

echo "═══ 不變量 21：active responsibility 的 canonical contract 閉合（R10-CANONICAL-REVIEW）═══"
# ⚠️ 與 13 同性質的**產品閘**（⛔ 非程式回歸）：C2 用 responsibility-level canonical contract
# 做 semantic scoring；只要還有 reviewed_active 的責任 canonical=null，跑出來的就不是
# 已裁定的 target architecture（會被迫臨時決定 fallback，改變 A05 的競爭環境）。
# ⛔ reviewed_historical 不受此閘拘束。
CN_CHECK="$REPO/scripts/audit/checks/canonical_population_completeness.py"
if ! python3 "$CN_CHECK" --self-test >/dev/null 2>&1; then
  echo "❌ FAIL：不變量 21 檢查器的自我測試未過（檢查器本身失效，其 PASS 不可信）"
  python3 "$CN_CHECK" --self-test
  FAIL=1
elif ! CN_OUT=$(python3 "$CN_CHECK" 2>&1); then
  echo "$CN_OUT"
  FAIL=1
  PRODUCT_BLOCKERS+=("INV21 / active responsibility canonical 未閉合（見 r10p/canonical-review-dossier.md）")
else
  echo "$CN_OUT"
  echo "✅ PASS（含 historical 豁免／缺 canonical／未 review／全補齊 四組對照）"
fi

echo "═══ 不變量 22：registry V1→V2 只准改 canonical 面（scope lock）═══"
# ⚠️ 本輪 scope ＝ canonical population，⛔ **不是**第二次 responsibility review。
# 若填 canonical 時順手改了 members／owner／applicability／status，registry topology 會
# **無聲漂移**，而 P4/P5 的普查數字（30 active／54 disposition）會在沒有裁定紀錄下失真。
# ⛔ 真要改 topology，必須另立 responsibility review epoch。
V2_CHECK="$REPO/scripts/audit/checks/registry_v2_scope_lock.py"
if ! python3 "$V2_CHECK" --self-test >/dev/null 2>&1; then
  echo "❌ FAIL：不變量 22 檢查器的自我測試未過（檢查器本身失效，其 PASS 不可信）"
  python3 "$V2_CHECK" --self-test
  FAIL=1
elif ! V2_OUT=$(python3 "$V2_CHECK" 2>&1); then
  echo "$V2_OUT"
  FAIL=1
  CODE_REGRESSIONS+=("INV22 / registry V1→V2 topology 漂移")
else
  echo "$V2_OUT"
  echo "✅ PASS（含偷改 members／applicability／owner／status／增刪責任／只改 canonical 必綠 等九組對照）"
fi

# ── 分類記帳：不變量 1–12 的失敗一律算 code contract regression ──
# （13 已在上面自行歸類；此處用總 FAIL 與 blocker 數回推，避免逐條改寫既有分支）
if [ "$CODE_FAIL_BEFORE_13" -ne 0 ]; then
  CODE_REGRESSIONS+=("不變量 1–12／14–20 有失敗（見上方 ❌ FAIL 行）")
fi

echo ""
echo "──────────────── 稽核記帳（兩類紅燈分開）────────────────"
echo "CODE_CONTRACT_REGRESSIONS: ${#CODE_REGRESSIONS[@]}"
for r in ${CODE_REGRESSIONS[@]+"${CODE_REGRESSIONS[@]}"}; do echo "  - $r"; done
echo "PRODUCT / POPULATION BLOCKERS: ${#PRODUCT_BLOCKERS[@]}"
for b in ${PRODUCT_BLOCKERS[@]+"${PRODUCT_BLOCKERS[@]}"}; do echo "  - $b"; done
echo ""
if [ $FAIL -eq 0 ]; then
  echo "OVERALL: PASS（$(date +%Y-%m-%d)）"
else
  echo "OVERALL: FAIL"
  if [ ${#CODE_REGRESSIONS[@]} -eq 0 ]; then
    echo "⚠️ 本次紅燈**全部**來自產品／population blocker——程式契約無回歸，"
    echo "   但 ⛔ 這不是綠燈：Level-A authority scope 尚未閉合。"
  fi
fi
exit $FAIL
