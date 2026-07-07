-- =====================================================
-- conversational-diagnosis 任務 8.2：合約查詢知識補標診斷分類（資料，非 schema）
-- 將「缺分類的合約 form_fill / 查詢知識」的 categories 補上 '狀態判斷'，
-- 使分類路由（handle_retrieval 元件 5）能命中、改走診斷對話而非直接觸發表單。
--
-- 識別合約查詢知識（不硬編 id，跨環境通用）：
--   (a) 知識自身 api_config 端點 = jgb_contracts（api_call / form_then_api 型）；或
--   (b) 知識 form_id 對應之 form_schema api_config 端點 = jgb_contracts（form_fill 型，端點在表單）。
-- 一般合約知識（違約責任/條款解釋等 direct_answer，無此端點）不受影響 → 維持靜態知識（三出口）。
--
-- 安全：冪等（已含則不重複加）；僅 is_active；明確排除保留分類（對話規則/系統脈絡，避免違反
--   chk_categories_no_reserved）；補多值 categories（_knowledge_category 先讀此欄位）。
--
-- 套用（部署作業，非單元測試執行）：
--   psql "$DATABASE_URL" -f database/migrations/backfill_contract_knowledge_diagnosis_category.sql
-- 套用後清快取（重啟或後台任一儲存）即生效。
-- ⚠️ 套用前建議先以下方「預覽」SELECT 確認受影響列，必要時依實際資料調整 WHERE。
-- =====================================================

-- 預覽：將被補標的合約查詢知識（執行 UPDATE 前可先單獨跑此段確認）
-- SELECT kb.id, kb.question_summary, kb.action_type, kb.form_id, kb.category, kb.categories
-- FROM knowledge_base kb
-- WHERE kb.is_active = TRUE
--   AND kb.category IS DISTINCT FROM '對話規則'
--   AND kb.category IS DISTINCT FROM '系統脈絡'
--   AND NOT (COALESCE(kb.categories, ARRAY[]::text[]) @> ARRAY['狀態判斷']::text[])
--   AND (
--         kb.api_config->>'endpoint' = 'jgb_contracts'
--         OR kb.form_id IN (SELECT form_id FROM form_schemas WHERE api_config->>'endpoint' = 'jgb_contracts')
--       );

UPDATE knowledge_base kb
SET categories = array_append(COALESCE(kb.categories, ARRAY[]::text[]), '狀態判斷'),
    updated_at = now()
WHERE kb.is_active = TRUE
  AND kb.category IS DISTINCT FROM '對話規則'
  AND kb.category IS DISTINCT FROM '系統脈絡'
  AND NOT (COALESCE(kb.categories, ARRAY[]::text[]) @> ARRAY['狀態判斷']::text[])
  AND (
        kb.api_config->>'endpoint' = 'jgb_contracts'
        OR kb.form_id IN (
            SELECT form_id FROM form_schemas WHERE api_config->>'endpoint' = 'jgb_contracts'
        )
      );

-- 驗證：補標後計數
DO $$
DECLARE
    n INTEGER;
BEGIN
    SELECT COUNT(*) INTO n FROM knowledge_base
    WHERE is_active = TRUE
      AND categories @> ARRAY['狀態判斷']::text[];
    RAISE NOTICE '✅ 已掛 狀態判斷 的知識：% 筆（套用後請清快取使分類路由生效）', n;
END $$;
