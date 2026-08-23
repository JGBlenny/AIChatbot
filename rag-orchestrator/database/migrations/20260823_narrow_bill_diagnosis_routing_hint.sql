-- =====================================================
-- 20260823 收窄帳單診斷面向的 Routing Hint
--   spec conversational-routing-execution｜任務 3.4（Requirement 2 修復）
--
-- 病灶（3.3 evidence packet 判定為 REGRESSION，非 expectation drift）：
--   20260731_assistant_report_fixes.sql §3（T-1）為了讓「查我的實值」問法能進面向，
--   把 `條件診斷：帳單` 掛到三筆**內容型 KB**（3402／3406／3519）上。
--   但 Routing Hint 掛在整筆 KB，於是**規則／流程／操作**問句也一起被帶進 Face：
--     「點退帳單的金額是怎麼算的」→ 進面向反問 bill_ref（答非所問）
--     「點退做完後，帳單會自動出來嗎？」→ 同上
--     「收據 PDF 在哪裡下載」→ 同上
--   ＝ 修一個 routing 缺口時製造了新的 routing overreach。
--
-- ⚠️ **T-1 的需求本身是真的**：instance-specific 問法確實需要進 Face。
--    故本批**不是**「拿掉分類」了事——那只會把舊 T-1 bug 裝回去。
--    修的是「同一筆 KB 同時承載 knowledge evidence 與過寬 Routing Hint」，
--    改回本專案既有的分工：**空答案錨點帶 Routing Hint，內容 KB 只帶 evidence**
--    （既有先例：4640 帳單收據金額／4656 查帳單編號／4657 合約的點退帳單金額）。
--
-- 冪等：UPDATE 以 question_summary 定位並檢查現況；INSERT 以 question_summary 判重。
-- ⚠️ 新增列 embedding 為 NULL，套用後須跑 tools/embed_missing.py 補嵌，否則錨點不會被檢索到。
-- =====================================================

-- ── 1. 內容型 KB 卸下 Routing Hint（保留其 knowledge evidence 與原主題分類）──
UPDATE knowledge_base
SET categories = array_remove(categories, '條件診斷：帳單'), updated_at = CURRENT_TIMESTAMP
WHERE question_summary IN ('點退帳單金額計算 押金結算',
                           '點退帳單 自動產生 費用結算',
                           '帳單收據 繳費證明 PDF 下載')
  AND '條件診斷：帳單' = ANY(coalesce(categories, '{}'));

-- ── 2. 補窄錨點：接住原本靠 3519 進場的 instance 問法 ──
--   實測：拔掉 3519 的 Hint 後「我這張點退帳單金額怎麼算出來的」→ 落回 single（T-1 復活）。
--   既有錨點 4657「合約的點退帳單金額 查點退金額」在此句型下輸給 3519，
--   故補一筆以「查/我的/這張/多少錢」為特徵的錨點（刻意不含「怎麼算」——實測含之會連規則問句一起吃掉）（沿 20260803 batch24 的錨點範式）。
INSERT INTO knowledge_base (question_summary, answer, categories, target_user, business_types,
                            keywords, is_active, source)
SELECT '查我的點退帳單金額 這張點退多少錢', '', ARRAY['條件診斷：帳單']::text[],
       ARRAY['property_manager','tenant']::text[], ARRAY['system_provider']::text[],
       ARRAY['點退','金額','查詢']::text[], TRUE, 'manual'
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
                  WHERE question_summary = '查我的點退帳單金額 這張點退多少錢');

-- ── 驗證 ──
DO $$
DECLARE leftover INT; anchors INT;
BEGIN
    SELECT COUNT(*) INTO leftover FROM knowledge_base
     WHERE question_summary IN ('點退帳單金額計算 押金結算', '點退帳單 自動產生 費用結算',
                                '帳單收據 繳費證明 PDF 下載')
       AND '條件診斷：帳單' = ANY(coalesce(categories, '{}'));
    SELECT COUNT(*) INTO anchors FROM knowledge_base
     WHERE is_active AND answer = '' AND '條件診斷：帳單' = ANY(coalesce(categories, '{}'));
    RAISE NOTICE '✅ 內容型 KB 仍掛 Hint：% 筆（應為 0）｜帳單診斷錨點：% 筆（套用後請跑 embed_missing.py 並清快取）',
                 leftover, anchors;
END $$;
