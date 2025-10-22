-- Migration: 移除 platform_sop_templates 表的 related_intent_id 欄位
-- Date: 2025-10-22
-- Description: 移除已廢棄的 related_intent_id 欄位，全面使用 platform_sop_template_intents 多對多關聯表

-- 1. 先刪除依賴 related_intent_id 的 view
DROP VIEW IF EXISTS v_vendor_available_sop_templates;

-- 2. 移除 related_intent_id 欄位
ALTER TABLE platform_sop_templates
DROP COLUMN IF EXISTS related_intent_id;

-- 3. 重建 view，使用 intent_ids 陣列取代 related_intent_id
CREATE OR REPLACE VIEW v_vendor_available_sop_templates AS
SELECT
    v.id AS vendor_id,
    v.name AS vendor_name,
    v.business_type AS vendor_business_type,
    pc.id AS category_id,
    pc.category_name,
    pc.description AS category_description,
    pg.id AS group_id,
    pg.group_name,
    pt.id AS template_id,
    pt.item_number,
    pt.item_name,
    pt.content,
    pt.template_notes,
    pt.customization_hint,
    -- 使用 intent_ids 陣列取代單一 related_intent_id
    COALESCE(
        (SELECT ARRAY_AGG(psti.intent_id ORDER BY psti.intent_id)
         FROM platform_sop_template_intents psti
         WHERE psti.template_id = pt.id),
        ARRAY[]::INTEGER[]
    ) AS intent_ids,
    pt.priority,
    CASE
        WHEN vsi.id IS NOT NULL THEN TRUE
        ELSE FALSE
    END AS already_copied,
    vsi.id AS vendor_sop_item_id
FROM vendors v
CROSS JOIN platform_sop_templates pt
JOIN platform_sop_categories pc ON pt.category_id = pc.id
LEFT JOIN platform_sop_groups pg ON pt.group_id = pg.id
LEFT JOIN vendor_sop_items vsi ON vsi.vendor_id = v.id AND vsi.template_id = pt.id AND vsi.is_active = TRUE
WHERE
    pt.is_active = TRUE
    AND pc.is_active = TRUE
    AND v.is_active = TRUE
    AND (pt.business_type = v.business_type OR pt.business_type IS NULL)
ORDER BY v.id, pc.display_order, pg.display_order, pt.item_number;

-- 4. 添加註釋
COMMENT ON TABLE platform_sop_templates IS '平台 SOP 範本表（使用 platform_sop_template_intents 進行意圖關聯）';
COMMENT ON VIEW v_vendor_available_sop_templates IS '業者可用的平台 SOP 範本（含多意圖陣列）';

-- 驗證：確認 platform_sop_template_intents 表有資料
-- SELECT COUNT(*) FROM platform_sop_template_intents;
