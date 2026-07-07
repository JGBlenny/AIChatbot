-- =====================================================
-- billing-conversational-facets 任務 5.2：既有帳務知識補標主面向（資料，非 schema）
-- ⚠️ 套用前置條件：facet-backfill-review.md（billing spec 目錄）人工確認完成；id 與清單一致。
-- 混合制：現象描述型 form_fill 升級掛面向（分類路由先攔、form 留後備，沿 3490 系列前例）；
-- 精確操作診斷句（3495/3496/3499/3500/3504）保留不掛。
-- 掛「帳單設定引導」者兼作該面向 select='category' grounding 素材。
-- 安全：冪等；不動 category 主欄位與 embedding；部署後 reranker 重建＋清快取。
-- =====================================================

-- 繳費金流排障
UPDATE knowledge_base SET categories = array_append(COALESCE(categories, ARRAY[]::text[]), '繳費金流排障'), updated_at = now()
WHERE id IN (3361, 3366, 3497, 3502) AND is_active
  AND NOT (COALESCE(categories, ARRAY[]::text[]) @> ARRAY['繳費金流排障']::text[]);

-- 發票
UPDATE knowledge_base SET categories = array_append(COALESCE(categories, ARRAY[]::text[]), '發票'), updated_at = now()
WHERE id IN (3362, 3420, 3503) AND is_active
  AND NOT (COALESCE(categories, ARRAY[]::text[]) @> ARRAY['發票']::text[]);

-- 滯納金
UPDATE knowledge_base SET categories = array_append(COALESCE(categories, ARRAY[]::text[]), '滯納金'), updated_at = now()
WHERE id IN (3531, 3532) AND is_active
  AND NOT (COALESCE(categories, ARRAY[]::text[]) @> ARRAY['滯納金']::text[]);

-- 帳單設定引導（兼 grounding batch）
UPDATE knowledge_base SET categories = array_append(COALESCE(categories, ARRAY[]::text[]), '帳單設定引導'), updated_at = now()
WHERE id IN (3399, 3403, 3548, 3549, 3550, 3551, 3552, 3553, 3554, 3555) AND is_active
  AND NOT (COALESCE(categories, ARRAY[]::text[]) @> ARRAY['帳單設定引導']::text[]);

-- 驗證：計數＋新面向互斥
DO $$
DECLARE n INT; dup INT;
BEGIN
    SELECT COUNT(*) INTO n FROM knowledge_base
    WHERE is_active AND categories && ARRAY['繳費金流排障','帳單異常','發票','滯納金','帳單設定引導']::text[]
      AND COALESCE(category,'') NOT IN ('對話規則','系統脈絡');
    SELECT COUNT(*) INTO dup FROM knowledge_base
    WHERE is_active AND (
        SELECT COUNT(*) FROM unnest(categories) c
        WHERE c IN ('繳費金流排障','帳單異常','發票','滯納金','帳單設定引導')) > 1;
    RAISE NOTICE '✅ 帳務面向補標：% 筆（預期 19）；跨面向重複 % 筆（預期 0）', n, dup;
END $$;
