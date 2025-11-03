-- Migration 39: 為 knowledge_base 新增 business_types 欄位
-- 用途：支援同一問題在不同業態類型下有不同答案
-- 建立時間：2025-10-24
--
-- 背景：
--   業者可能同時提供多種業態（如：包租+代管）
--   不同業態對同一問題的答案可能不同
--   例如：「房租怎麼繳？」
--     - 包租型：「請於每月X日匯入公司帳戶...」
--     - 代管型：「請聯繫房東或使用平台代收...」
--
-- 設計：
--   knowledge_base.business_types TEXT[]
--   - NULL 或 [] = 適用所有業態（通用知識）
--   - ['full_service'] = 只適用包租型
--   - ['property_management'] = 只適用代管型
--   - ['full_service', 'property_management'] = 兩者都適用

-- ========================================
-- 1. 新增 business_types 欄位
-- ========================================

ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS business_types TEXT[] DEFAULT NULL;

COMMENT ON COLUMN knowledge_base.business_types IS '適用的業態類型陣列：system_provider(系統商), full_service(包租型), property_management(代管型)。NULL=適用所有業態（通用知識）';

-- ========================================
-- 2. 建立索引支援陣列查詢
-- ========================================

-- 使用 GIN 索引支援陣列操作（&& 重疊查詢）
CREATE INDEX IF NOT EXISTS idx_knowledge_business_types
ON knowledge_base USING GIN(business_types);

-- ========================================
-- 3. 更新現有知識為通用知識
-- ========================================

-- 將現有所有知識設為通用（NULL = 適用所有業態）
-- 管理員可以後續手動調整特定知識的業態範圍
UPDATE knowledge_base
SET business_types = NULL
WHERE business_types IS NULL;

-- ========================================
-- 4. 範例：插入不同業態的知識
-- ========================================

-- 以下為範例，實際資料由管理員或匯入流程建立

-- 範例 1：包租型專屬知識
/*
INSERT INTO knowledge_base (
    vendor_id,
    question_summary,
    answer,
    business_types,
    audience,
    scope,
    priority,
    title
) VALUES (
    1,
    '房租如何繳納',
    '請於每月1號前將房租匯入公司指定帳戶，帳號：XXX-XXX-XXX。如有問題請聯繫客服。',
    ARRAY['full_service'],
    'customer',
    'vendor',
    5,
    'system'
);
*/

-- 範例 2：代管型專屬知識
/*
INSERT INTO knowledge_base (
    vendor_id,
    question_summary,
    answer,
    business_types,
    audience,
    scope,
    priority,
    title
) VALUES (
    1,
    '房租如何繳納',
    '請直接聯繫房東繳納租金，或使用我們的平台代收服務。詳情請洽客服。',
    ARRAY['property_management'],
    'customer',
    'vendor',
    5,
    'system'
);
*/

-- 範例 3：通用知識（所有業態適用）
/*
INSERT INTO knowledge_base (
    question_summary,
    answer,
    business_types,
    audience,
    scope,
    priority,
    title
) VALUES (
    '客服電話是多少',
    '我們的客服電話是 {{service_hotline}}，服務時間為週一至週五 9:00-18:00。',
    NULL,  -- 適用所有業態
    'customer',
    'global',
    1,
    'system'
);
*/

-- ========================================
-- 5. 更新相關檢視（如果存在）
-- ========================================

-- 檢查是否有使用 knowledge_base 的檢視需要更新
-- （目前系統中沒有相關檢視，此處保留供未來使用）

-- ========================================
-- 6. 記錄 Migration
-- ========================================

INSERT INTO schema_migrations (id, description, executed_at)
VALUES (39, 'Add business_types array to knowledge_base for multi-business-type support', NOW())
ON CONFLICT (id) DO NOTHING;

-- ========================================
-- 完成
-- ========================================

\echo '✅ Migration 39: knowledge_base 新增 business_types 欄位完成'
\echo '   - 已新增 business_types TEXT[] 欄位'
\echo '   - 已建立 GIN 索引支援陣列查詢'
\echo '   - 現有知識預設為通用（NULL = 所有業態）'
\echo ''
\echo '📝 使用範例：'
\echo '   - 查詢包租型知識：WHERE business_types && ARRAY[''full_service'']'
\echo '   - 查詢通用知識：WHERE business_types IS NULL'
\echo '   - 查詢包租或代管：WHERE business_types && ARRAY[''full_service'', ''property_management'']'
\echo ''
\echo '🔍 檢索邏輯：'
\echo '   1. 優先匹配 business_types 的知識'
\echo '   2. 備選匹配 business_types IS NULL 的通用知識'
