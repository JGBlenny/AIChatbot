-- Migration 36: 簡化 SOP 架構（移除覆寫機制，改為複製-編輯模式）
-- 用途：簡化業者 SOP 管理，從「範本+覆寫」改為「範本複製」模式
-- 建立時間：2025-10-18
-- 設計理念：平台範本按業種分類，業者複製後自行編輯

-- ========================================
-- 1. 刪除所有相關的 Views 和 Functions
-- ========================================

DROP VIEW IF EXISTS v_vendor_sop_merged CASCADE;
DROP VIEW IF EXISTS v_vendor_available_templates CASCADE;
DROP VIEW IF EXISTS v_sop_override_statistics CASCADE;
DROP VIEW IF EXISTS v_vendor_sop_full CASCADE;
DROP FUNCTION IF EXISTS get_vendor_sop_content(INTEGER, INTEGER) CASCADE;

-- ========================================
-- 2. 刪除覆寫表
-- ========================================

DROP TABLE IF EXISTS vendor_sop_overrides CASCADE;

-- ========================================
-- 3. 修改 platform_sop_templates（添加業種類型）
-- ========================================

-- 添加 business_type 欄位
ALTER TABLE platform_sop_templates
ADD COLUMN IF NOT EXISTS business_type VARCHAR(50);

-- 移除金流相關欄位
ALTER TABLE platform_sop_templates
DROP COLUMN IF EXISTS requires_cashflow_check,
DROP COLUMN IF EXISTS cashflow_through_company,
DROP COLUMN IF EXISTS cashflow_direct_to_landlord,
DROP COLUMN IF EXISTS cashflow_mixed,
DROP COLUMN IF EXISTS requires_business_type_check,
DROP COLUMN IF EXISTS business_type_full_service,
DROP COLUMN IF EXISTS business_type_management;

-- 更新註釋
COMMENT ON TABLE platform_sop_templates IS '平台級 SOP 範本表（按業種類型分類的參考範本，業者可複製後編輯）';
COMMENT ON COLUMN platform_sop_templates.business_type IS '業種類型（full_service=包租, property_management=代管），NULL=通用範本';
COMMENT ON COLUMN platform_sop_templates.content IS '範本內容（業者複製此內容後可自行調整）';

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_platform_sop_templates_business_type ON platform_sop_templates(business_type);

-- ========================================
-- 4. 修改 vendor_sop_items（移除金流欄位）
-- ========================================

-- 移除金流相關欄位
ALTER TABLE vendor_sop_items
DROP COLUMN IF EXISTS requires_cashflow_check,
DROP COLUMN IF EXISTS cashflow_through_company,
DROP COLUMN IF EXISTS cashflow_direct_to_landlord,
DROP COLUMN IF EXISTS cashflow_mixed,
DROP COLUMN IF EXISTS requires_business_type_check,
DROP COLUMN IF EXISTS business_type_full_service,
DROP COLUMN IF EXISTS business_type_management;

-- 添加範本來源記錄（可選，用於追蹤）
ALTER TABLE vendor_sop_items
ADD COLUMN IF NOT EXISTS template_id INTEGER REFERENCES platform_sop_templates(id) ON DELETE SET NULL;

COMMENT ON TABLE vendor_sop_items IS '業者 SOP 項目表（從平台範本複製後，業者可自行編輯調整）';
COMMENT ON COLUMN vendor_sop_items.template_id IS '來源範本ID（記錄此 SOP 是從哪個範本複製而來，可為 NULL）';

-- ========================================
-- 5. 修改 vendor_sop_categories（移除不必要欄位）
-- ========================================

-- vendor_sop_categories 保持不變，但確保有基本索引
CREATE INDEX IF NOT EXISTS idx_vendor_sop_categories_vendor ON vendor_sop_categories(vendor_id);
CREATE INDEX IF NOT EXISTS idx_vendor_sop_categories_active ON vendor_sop_categories(is_active);

-- ========================================
-- 6. 建立新的檢視：業者可用範本
-- ========================================

CREATE OR REPLACE VIEW v_vendor_available_sop_templates AS
SELECT
    v.id AS vendor_id,
    v.name AS vendor_name,
    v.business_type AS vendor_business_type,
    pc.id AS category_id,
    pc.category_name,
    pc.description AS category_description,
    pt.id AS template_id,
    pt.item_number,
    pt.item_name,
    pt.content,
    pt.template_notes,
    pt.customization_hint,
    pt.related_intent_id,
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
LEFT JOIN vendor_sop_items vsi
    ON vsi.vendor_id = v.id
    AND vsi.template_id = pt.id
    AND vsi.is_active = TRUE
WHERE
    pt.is_active = TRUE
    AND pc.is_active = TRUE
    AND v.is_active = TRUE
    -- 只顯示符合業者業種的範本，或通用範本
    AND (pt.business_type = v.business_type OR pt.business_type IS NULL)
ORDER BY
    v.id,
    pc.display_order,
    pt.item_number;

COMMENT ON VIEW v_vendor_available_sop_templates IS '業者可用範本檢視（根據業種類型過濾，顯示業者可複製的範本）';

-- ========================================
-- 7. 建立範本使用統計檢視
-- ========================================

CREATE OR REPLACE VIEW v_platform_sop_template_usage AS
SELECT
    pt.id AS template_id,
    pc.category_name,
    pt.business_type,
    pt.item_name,
    COUNT(DISTINCT vsi.vendor_id) AS copied_by_vendor_count,
    COUNT(DISTINCT v.id) FILTER (WHERE v.business_type = pt.business_type OR pt.business_type IS NULL) AS applicable_vendor_count,
    ROUND(
        COUNT(DISTINCT vsi.vendor_id)::NUMERIC /
        NULLIF(COUNT(DISTINCT v.id) FILTER (WHERE v.business_type = pt.business_type OR pt.business_type IS NULL), 0) * 100,
        2
    ) AS usage_percentage
FROM platform_sop_templates pt
INNER JOIN platform_sop_categories pc ON pt.category_id = pc.id
CROSS JOIN vendors v
LEFT JOIN vendor_sop_items vsi
    ON vsi.template_id = pt.id
    AND vsi.is_active = TRUE
WHERE
    pt.is_active = TRUE
    AND pc.is_active = TRUE
    AND v.is_active = TRUE
GROUP BY pt.id, pc.category_name, pt.business_type, pt.item_name
ORDER BY usage_percentage DESC, copied_by_vendor_count DESC;

COMMENT ON VIEW v_platform_sop_template_usage IS '平台 SOP 範本使用統計（分析哪些範本最常被複製使用）';

-- ========================================
-- 8. 更新現有資料
-- ========================================

-- 將現有的 platform_sop_templates 設為通用範本（NULL = 通用）
UPDATE platform_sop_templates
SET business_type = NULL
WHERE business_type IS NULL;

-- ========================================
-- 9. 記錄 Migration
-- ========================================

INSERT INTO schema_migrations (id, description, executed_at)
VALUES (36, 'Simplify SOP architecture: remove override mechanism, use copy-edit pattern', NOW())
ON CONFLICT (id) DO NOTHING;

-- ========================================
-- 完成
-- ========================================

\echo '✅ Migration 36: SOP 架構簡化完成'
\echo '   - 已刪除 vendor_sop_overrides 表（覆寫機制）'
\echo '   - 已刪除相關 views 和 functions'
\echo '   - platform_sop_templates 添加 business_type 欄位'
\echo '   - 移除所有金流相關欄位'
\echo '   - 建立 v_vendor_available_sop_templates 檢視（按業種過濾）'
\echo '   - 建立 v_platform_sop_template_usage 檢視（範本使用統計）'
\echo ''
\echo '📝 新架構說明：'
\echo '   - 平台管理員建立範本時，選擇業種類型（包租/代管/通用）'
\echo '   - 業者瀏覽範本時，只看到符合自己業種的範本'
\echo '   - 業者點擊「使用範本」，系統複製範本內容到 vendor_sop_items'
\echo '   - 業者可自由編輯複製後的內容，不影響範本'
\echo '   - 金流參數在 vendor_configs 中管理，SOP 內容可使用變數'
