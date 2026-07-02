-- =====================================================
-- contract-conversational-facets 任務 4.2：既有合約知識補標主面向（資料，非 schema）
--
-- ⚠️ 套用前置條件：facet-backfill-review.md（spec 目錄）人工確認完成。
--    id 明列與該清單一一對應——清單有異動，本檔需同步修改後再套用。
--
-- 語意：把 11 筆既有 JGB 合約知識的 categories 補上「主面向」（一筆一主面向互斥），
--   使檢索命中後 config_for_category 能路由進對應面向對話；具體操作教學維持單發不掛。
--   已掛『狀態判斷』者不在本檔範圍（不動）。
--
-- 安全：冪等（已含該面向則跳過）；僅 is_active；不動 category 主欄位（RAG 檢索用）、
--   不動 embedding 相關欄位（question_summary/answer 不變 → 不需重算 embedding）；
--   部署後需 reranker semantic model 重建＋清快取（tasks 6.3）。
--
-- 套用：psql "$DATABASE_URL" -f database/migrations/backfill_contract_knowledge_facet_categories.sql
-- =====================================================

-- 合約異動
UPDATE knowledge_base SET categories = array_append(COALESCE(categories, ARRAY[]::text[]), '合約異動'), updated_at = now()
WHERE id IN (3329) AND is_active AND NOT (COALESCE(categories, ARRAY[]::text[]) @> ARRAY['合約異動']::text[]);

-- 退租收尾
UPDATE knowledge_base SET categories = array_append(COALESCE(categories, ARRAY[]::text[]), '退租收尾'), updated_at = now()
WHERE id IN (3327, 3380, 3526) AND is_active AND NOT (COALESCE(categories, ARRAY[]::text[]) @> ARRAY['退租收尾']::text[]);

-- 續約
UPDATE knowledge_base SET categories = array_append(COALESCE(categories, ARRAY[]::text[]), '續約'), updated_at = now()
WHERE id IN (3333, 3388) AND is_active AND NOT (COALESCE(categories, ARRAY[]::text[]) @> ARRAY['續約']::text[]);

-- 簽署排障
UPDATE knowledge_base SET categories = array_append(COALESCE(categories, ARRAY[]::text[]), '簽署排障'), updated_at = now()
WHERE id IN (3331, 3392) AND is_active AND NOT (COALESCE(categories, ARRAY[]::text[]) @> ARRAY['簽署排障']::text[]);

-- 建約引導（條款法律 QA＋對象型態素材，R5.5）
UPDATE knowledge_base SET categories = array_append(COALESCE(categories, ARRAY[]::text[]), '建約引導'), updated_at = now()
WHERE id IN (3328, 3330, 3440) AND is_active AND NOT (COALESCE(categories, ARRAY[]::text[]) @> ARRAY['建約引導']::text[]);

-- 驗證：每面向補標計數（互斥檢查：同列不應含兩個新面向）
DO $$
DECLARE n INT; dup INT;
BEGIN
    SELECT COUNT(*) INTO n FROM knowledge_base
    WHERE is_active AND categories && ARRAY['合約異動','退租收尾','續約','建約引導','簽署排障']::text[]
      AND COALESCE(category,'') NOT IN ('對話規則','系統脈絡');
    SELECT COUNT(*) INTO dup FROM knowledge_base
    WHERE is_active AND (
        SELECT COUNT(*) FROM unnest(categories) c
        WHERE c IN ('合約異動','退租收尾','續約','建約引導','簽署排障')) > 1;
    RAISE NOTICE '✅ 面向補標：% 筆知識掛新面向（預期 11）；跨面向重複 % 筆（預期 0）', n, dup;
    IF dup > 0 THEN
        RAISE WARNING '⚠️ 有知識掛多個新面向，違反一筆一主面向互斥，請檢查';
    END IF;
END $$;
