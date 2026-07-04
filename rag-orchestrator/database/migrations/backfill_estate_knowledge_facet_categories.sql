-- =====================================================
-- estate-conversational-facets 任務 3.1：既有物件知識補標＋停用（資料，非 schema）
-- 依 facet-backfill-review.md 人工閘門後執行。answer 改寫走批次檔 updates
-- （import_facet_knowledge.py estate-knowledge-batch.json），本檔只動 categories 與 is_active。
-- ⚠️ embedding 基於 question_summary（feedback_embedding_integrity）——本檔不動
--    question_summary，categories 補標不影響向量。
-- 冪等：categories 追加前檢查未含；停用重複執行無害。
-- =====================================================

-- ── 掛『物件操作引導』（內容不動：3429/3430/3432/3434；改寫另走批次：3505/3506）──
-- 批次上傳範圍外（使用者裁定 2026-07-04）：3431 不補標不改寫、3357 不停用（過時口徑掛帳）
UPDATE knowledge_base SET categories = array_append(categories, '物件操作引導'), updated_at = now()
WHERE id IN (3429, 3430, 3432, 3434, 3505, 3506)
  AND NOT (categories @> ARRAY['物件操作引導']);

-- ── 掛『物件現況診斷』（3428 狀態定義/3507 不能建約/3861 建約前提雙掛/3862 多合約）──
UPDATE knowledge_base SET categories = array_append(COALESCE(categories, ARRAY[]::text[]), '物件現況診斷'), updated_at = now()
WHERE id IN (3428, 3507, 3861, 3862)
  AND (categories IS NULL OR NOT (categories @> ARRAY['物件現況診斷']));

-- ── 未標旗設『物件操作引導』（3894 快照原則/3895 刊登租金調整）──
UPDATE knowledge_base SET categories = ARRAY['物件操作引導'], updated_at = now()
WHERE id IN (3894, 3895) AND (categories IS NULL OR categories = ARRAY[]::text[]);


DO $$
DECLARE g INT; d INT; x INT;
BEGIN
    SELECT COUNT(*) INTO g FROM knowledge_base WHERE categories @> ARRAY['物件操作引導'] AND is_active;
    SELECT COUNT(*) INTO d FROM knowledge_base WHERE categories @> ARRAY['物件現況診斷'] AND is_active;
    x := 0;
    RAISE NOTICE '✅ 物件補標：操作引導 % 筆、現況診斷 % 筆（批次項已撤 x=%）', g, d, x;
END $$;
