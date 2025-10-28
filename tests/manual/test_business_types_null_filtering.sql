-- 業態過濾 NULL 值問題測試腳本
-- 問題：business_types: null 的通用知識被過濾掉了
--
-- 測試環境：
-- - Knowledge 497: business_types = NULL (通用知識)
-- - Vendor 1: business_types = ['full_service']
--
-- 預期：Knowledge 497 應該對 Vendor 1 可見
-- 實際：檢索結果為 0

-- ========================================
-- 測試 1: 驗證知識 497 的 business_types 值
-- ========================================
SELECT
    id,
    question_summary,
    business_types,
    vendor_id,
    scope,
    embedding IS NOT NULL as has_embedding
FROM knowledge_base
WHERE id = 497;

-- ========================================
-- 測試 2: 驗證 Vendor 1 的 business_types 值
-- ========================================
SELECT
    id,
    name,
    business_types,
    is_active
FROM vendors
WHERE id = 1;

-- ========================================
-- 測試 3: 測試 NULL 過濾邏輯（簡化版）
-- ========================================
-- 這個查詢應該找到 Knowledge 497
SELECT
    id,
    question_summary,
    business_types
FROM knowledge_base
WHERE id = 497
  AND (
    business_types IS NULL
    OR business_types && ARRAY['full_service']::text[]
  );

-- ========================================
-- 測試 4: 測試向量查詢中的業態過濾
-- ========================================
-- 檢查所有通用知識（business_types IS NULL）是否有向量
SELECT
    id,
    question_summary,
    business_types,
    embedding IS NOT NULL as has_embedding,
    scope,
    vendor_id
FROM knowledge_base
WHERE business_types IS NULL
  AND embedding IS NOT NULL
ORDER BY id
LIMIT 20;

-- ========================================
-- 測試 5: 檢查知識 497 是否有意圖映射
-- ========================================
SELECT
    kb.id,
    kb.question_summary,
    kb.business_types,
    kim.intent_id,
    i.name as intent_name
FROM knowledge_base kb
LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
LEFT JOIN intents i ON kim.intent_id = i.id
WHERE kb.id = 497;

-- ========================================
-- 測試 6: 模擬完整的檢索查詢（vendor_knowledge_retriever.py line 76-120）
-- ========================================
-- 這是 retrieve_knowledge() 方法使用的實際查詢
WITH vendor_info AS (
    SELECT business_types FROM vendors WHERE id = 1
)
SELECT
    kb.id,
    kb.question_summary,
    kb.answer,
    kb.scope,
    kb.priority,
    kb.business_types,
    kb.vendor_id,
    -- 計算優先級權重
    CASE
        WHEN kb.scope = 'customized' AND kb.vendor_id = 1 THEN 1000
        WHEN kb.scope = 'vendor' AND kb.vendor_id = 1 THEN 500
        WHEN kb.scope = 'global' AND kb.vendor_id IS NULL THEN 100
        ELSE 0
    END as scope_weight
FROM knowledge_base kb
INNER JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
WHERE
    kim.intent_id = 2  -- 假設意圖 ID 為 2，根據實際情況調整
    AND (
        -- 業者客製化知識
        (kb.vendor_id = 1 AND kb.scope IN ('customized', 'vendor'))
        OR
        -- 全域知識
        (kb.vendor_id IS NULL AND kb.scope = 'global')
    )
    -- ✅ 業態類型過濾
    AND (
        kb.business_types IS NULL  -- 通用知識（適用所有業態）
        OR kb.business_types && (SELECT business_types FROM vendor_info)::text[]
    )
ORDER BY
    scope_weight DESC,
    kb.priority DESC,
    kb.created_at DESC;

-- ========================================
-- 測試 7: 測試數組操作符 && 的行為
-- ========================================
-- 驗證 NULL && array 的結果
SELECT
    NULL::text[] && ARRAY['full_service']::text[] as null_overlaps_array,
    ARRAY['full_service']::text[] && NULL::text[] as array_overlaps_null,
    NULL::text[] IS NULL as is_null_check;

-- ========================================
-- 測試 8: 檢查是否是參數傳遞問題
-- ========================================
-- 模擬 vendor_business_types 參數為空列表的情況
SELECT
    id,
    question_summary,
    business_types
FROM knowledge_base
WHERE id = 497
  AND (
    business_types IS NULL
    OR business_types && ARRAY[]::text[]  -- 空數組
  );

-- 檢查空數組與 NULL 的交集行為
SELECT
    NULL::text[] && ARRAY[]::text[] as null_overlaps_empty,
    ARRAY['full_service']::text[] && ARRAY[]::text[] as array_overlaps_empty;

-- ========================================
-- 測試 9: 檢查向量檢索中的業態過濾（rag_engine.py）
-- ========================================
-- 這是 RAG Engine 使用的查詢模式
SELECT
    id,
    question_summary,
    answer as content,
    target_user,
    keywords,
    business_types,
    embedding IS NOT NULL as has_embedding
FROM knowledge_base
WHERE embedding IS NOT NULL
  AND (business_types IS NULL OR business_types && ARRAY['full_service']::text[])
ORDER BY id
LIMIT 10;

-- ========================================
-- 測試 10: 檢查 target_user 過濾是否也有類似問題
-- ========================================
SELECT
    id,
    question_summary,
    target_user,
    business_types
FROM knowledge_base
WHERE target_user IS NULL  -- 通用目標用戶
  AND business_types IS NULL  -- 通用業態
  AND embedding IS NOT NULL
LIMIT 10;

-- ========================================
-- 測試總結查詢
-- ========================================
SELECT
    '通用知識總數（business_types IS NULL）' as metric,
    COUNT(*) as value
FROM knowledge_base
WHERE business_types IS NULL

UNION ALL

SELECT
    '通用知識有向量數' as metric,
    COUNT(*) as value
FROM knowledge_base
WHERE business_types IS NULL AND embedding IS NOT NULL

UNION ALL

SELECT
    '通用知識有意圖映射數' as metric,
    COUNT(DISTINCT kb.id) as value
FROM knowledge_base kb
INNER JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
WHERE kb.business_types IS NULL

UNION ALL

SELECT
    '全域範圍通用知識數（scope=global + business_types IS NULL）' as metric,
    COUNT(*) as value
FROM knowledge_base
WHERE scope = 'global' AND vendor_id IS NULL AND business_types IS NULL;
