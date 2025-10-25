-- Migration 38: 將業態類型改為陣列以支援多重業態
-- 用途：業者可以同時擁有多種業態類型（例如：既做包租又做代管）
-- 建立時間：2025-10-24
-- 業態類型定義：
--   - system_provider: 系統商（提供系統平台給其他業者使用）
--   - full_service: 包租型（包租代管，負責招租和管理）
--   - property_management: 代管型（僅提供物業管理服務）
-- 範例：
--   - 只做包租：['full_service']
--   - 只做代管：['property_management']
--   - 包租&代管：['full_service', 'property_management']

-- ========================================
-- 1. 備份現有的 business_type 資料
-- ========================================

-- 添加臨時欄位儲存舊資料
ALTER TABLE vendors
ADD COLUMN IF NOT EXISTS business_type_old VARCHAR(50);

UPDATE vendors
SET business_type_old = business_type
WHERE business_type IS NOT NULL;

-- ========================================
-- 2. 將 business_type 改為 business_types 陣列
-- ========================================

-- 刪除舊欄位
ALTER TABLE vendors
DROP COLUMN IF EXISTS business_type;

-- 新增陣列欄位
ALTER TABLE vendors
ADD COLUMN business_types TEXT[] DEFAULT ARRAY['property_management'];

-- 從舊資料遷移（將單一值轉為陣列）
UPDATE vendors
SET business_types = ARRAY[business_type_old]
WHERE business_type_old IS NOT NULL;

-- 移除臨時欄位
ALTER TABLE vendors
DROP COLUMN IF EXISTS business_type_old;

-- 添加註釋
COMMENT ON COLUMN vendors.business_types IS '業態類型陣列：system_provider=系統商, full_service=包租型, property_management=代管型（可多選，例如：同時做包租和代管）';

-- 建立索引（使用 GIN 索引支援陣列查詢）
CREATE INDEX IF NOT EXISTS idx_vendors_business_types ON vendors USING GIN(business_types);

-- ========================================
-- 3. 更新 platform_sop_templates 表
-- ========================================

-- platform_sop_templates.business_type 保持單一值（範本只屬於一種類型）
-- 但更新註釋說明業者可能有多種類型
COMMENT ON COLUMN platform_sop_templates.business_type IS '業種類型（system_provider=系統商, full_service=包租型, property_management=代管型），NULL=通用範本。業者擁有此類型時即可使用該範本。';

-- ========================================
-- 4. 更新檢視：業者可用範本（支援陣列匹配）
-- ========================================

-- 重建檢視以支援陣列匹配
DROP VIEW IF EXISTS v_vendor_available_sop_templates CASCADE;

CREATE OR REPLACE VIEW v_vendor_available_sop_templates AS
SELECT
    v.id AS vendor_id,
    v.name AS vendor_name,
    v.business_types AS vendor_business_types,
    pc.id AS category_id,
    pc.category_name,
    pc.description AS category_description,
    psg.id AS group_id,
    psg.group_name,
    pt.id AS template_id,
    pt.item_number,
    pt.item_name,
    pt.content,
    pt.template_notes,
    pt.customization_hint,
    COALESCE(
        (SELECT ARRAY_AGG(psti.intent_id ORDER BY psti.intent_id)
         FROM platform_sop_template_intents psti
         WHERE psti.template_id = pt.id),
        ARRAY[]::INTEGER[]
    ) AS intent_ids,
    pt.priority,
    -- 檢查業者是否已複製此範本
    CASE
        WHEN vsi.id IS NOT NULL THEN true
        ELSE false
    END AS already_copied,
    vsi.id AS vendor_sop_item_id
FROM vendors v
CROSS JOIN platform_sop_templates pt
INNER JOIN platform_sop_categories pc ON pt.category_id = pc.id
LEFT JOIN platform_sop_groups psg ON pt.group_id = psg.id
LEFT JOIN vendor_sop_items vsi
    ON vsi.vendor_id = v.id
    AND vsi.template_id = pt.id
    AND vsi.is_active = TRUE
WHERE
    pt.is_active = TRUE
    AND pc.is_active = TRUE
    AND v.is_active = TRUE
    -- 重要：只顯示符合業者任一業種的範本，或通用範本
    -- 使用陣列操作符：業者的 business_types 陣列包含範本的 business_type
    AND (pt.business_type = ANY(v.business_types) OR pt.business_type IS NULL)
ORDER BY
    v.id,
    pc.display_order,
    pt.item_number;

COMMENT ON VIEW v_vendor_available_sop_templates IS '業者可用範本檢視（根據業種類型陣列過濾，業者擁有的任一業種符合範本即可使用）';

-- ========================================
-- 5. 記錄 Migration
-- ========================================

INSERT INTO schema_migrations (id, description, executed_at)
VALUES (38, 'Expand business types to array: support multiple business types per vendor', NOW())
ON CONFLICT (id) DO NOTHING;

-- ========================================
-- 完成
-- ========================================

\echo '✅ Migration 38: 業態類型改為陣列完成'
\echo '   - business_type (VARCHAR) → business_types (TEXT[])'
\echo '   - 支援 4 種業態類型：'
\echo '     1. system_provider (系統商)'
\echo '     2. full_service (包租型)'
\echo '     3. property_management (代管型)'
\echo '     4. 可組合：例如 [''full_service'', ''property_management'']'
\echo ''
\echo '   - 已建立 GIN 索引支援陣列查詢'
\echo '   - 已更新 v_vendor_available_sop_templates 檢視'
\echo '   - 現有資料已自動遷移為陣列格式'
\echo ''
\echo '📝 查詢範例：'
\echo '   - 查詢所有包租業者：WHERE ''full_service'' = ANY(business_types)'
\echo '   - 查詢包租或代管業者：WHERE business_types && ARRAY[''full_service'', ''property_management'']'
