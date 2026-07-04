-- =====================================================
-- iot-conversational-facets 任務 3.2：既有 IoT 知識補標主面向（資料，非 schema）
-- ⚠️ 套用前置條件：facet-backfill-review.md（iot spec 目錄）人工確認完成；id 與清單一致。
-- 補標 3 筆：電表排障 2（3460/3461）＋IoT設定引導 1（3459）。
-- 3458/3462 門鎖維持單發不掛；answer 補強（3459/3461）在知識批次 updates（任務 3.3）。
-- 安全：冪等；不動 category 主欄位與 embedding；部署後 reranker 重建＋清快取。
-- =====================================================

-- 電表排障
UPDATE knowledge_base SET categories = array_append(COALESCE(categories, ARRAY[]::text[]), '電表排障'), updated_at = now()
WHERE id IN (3460, 3461) AND is_active
  AND NOT (COALESCE(categories, ARRAY[]::text[]) @> ARRAY['電表排障']::text[]);

-- IoT設定引導
UPDATE knowledge_base SET categories = array_append(COALESCE(categories, ARRAY[]::text[]), 'IoT設定引導'), updated_at = now()
WHERE id = 3459 AND is_active
  AND NOT (COALESCE(categories, ARRAY[]::text[]) @> ARRAY['IoT設定引導']::text[]);

-- 驗證：計數＋新面向互斥
DO $$
DECLARE n INT; dup INT;
BEGIN
    SELECT COUNT(*) INTO n FROM knowledge_base
    WHERE is_active AND categories && ARRAY['電表排障','IoT設定引導']::text[]
      AND COALESCE(category,'') NOT IN ('對話規則','系統脈絡');
    SELECT COUNT(*) INTO dup FROM knowledge_base
    WHERE is_active AND (
        SELECT COUNT(*) FROM unnest(categories) c
        WHERE c IN ('電表排障','IoT設定引導')) > 1;
    RAISE NOTICE '✅ IoT 面向補標：% 筆（預期 3；含整合測試臨時列時 +1）；跨面向重複 % 筆（預期 0）', n, dup;
END $$;
