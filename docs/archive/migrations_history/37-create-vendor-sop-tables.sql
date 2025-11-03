-- Migration 33: 建立業者 SOP 資料表
-- 用途：儲存業者的標準作業流程（SOP），支援金流模式與業種類型的動態調整
-- 建立時間：2025-10-18

-- ========================================
-- 1. 擴充 vendors 表（新增業種類型與金流模式）
-- ========================================

ALTER TABLE vendors
ADD COLUMN IF NOT EXISTS business_type VARCHAR(50) DEFAULT 'property_management',
ADD COLUMN IF NOT EXISTS cashflow_model VARCHAR(50) DEFAULT 'direct_to_landlord';

COMMENT ON COLUMN vendors.business_type IS '業種類型：full_service(包租型), property_management(代管型)';
COMMENT ON COLUMN vendors.cashflow_model IS '金流模式：through_company(金流過我家), direct_to_landlord(金流不過我家), mixed(混合型)';

-- ========================================
-- 2. 建立 SOP 分類表
-- ========================================

CREATE TABLE IF NOT EXISTS vendor_sop_categories (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE,
    category_name VARCHAR(200) NOT NULL,
    description TEXT,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sop_categories_vendor ON vendor_sop_categories(vendor_id);
CREATE INDEX IF NOT EXISTS idx_sop_categories_active ON vendor_sop_categories(is_active);

COMMENT ON TABLE vendor_sop_categories IS '業者 SOP 分類表（如：租賃流程、維護修繕等）';

-- ========================================
-- 3. 建立 SOP 項目表
-- ========================================

CREATE TABLE IF NOT EXISTS vendor_sop_items (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES vendor_sop_categories(id) ON DELETE CASCADE,
    vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE,

    -- 項目基本資訊
    item_number INTEGER,                          -- 項次（如：1, 2, 3...）
    item_name VARCHAR(200),                       -- 項目名稱（如：「申請步驟」）
    content TEXT NOT NULL,                        -- 基礎內容（通用版本）

    -- 金流模式相關
    requires_cashflow_check BOOLEAN DEFAULT FALSE, -- 是否需要檢查金流模式
    cashflow_through_company TEXT,                -- 金流過我家時的內容
    cashflow_direct_to_landlord TEXT,             -- 金流不過我家時的內容
    cashflow_mixed TEXT,                          -- 混合型時的內容

    -- 業種類型相關
    requires_business_type_check BOOLEAN DEFAULT FALSE, -- 是否需要檢查業種類型
    business_type_full_service TEXT,              -- 包租型時的語氣調整
    business_type_management TEXT,                -- 代管型時的語氣調整

    -- 關聯與優先級
    related_intent_id INTEGER REFERENCES intents(id) ON DELETE SET NULL, -- 關聯意圖
    priority INTEGER DEFAULT 0,

    -- 狀態與時間
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sop_items_vendor ON vendor_sop_items(vendor_id);
CREATE INDEX IF NOT EXISTS idx_sop_items_category ON vendor_sop_items(category_id);
CREATE INDEX IF NOT EXISTS idx_sop_items_intent ON vendor_sop_items(related_intent_id);
CREATE INDEX IF NOT EXISTS idx_sop_items_cashflow_check ON vendor_sop_items(requires_cashflow_check);
CREATE INDEX IF NOT EXISTS idx_sop_items_active ON vendor_sop_items(is_active);

COMMENT ON TABLE vendor_sop_items IS '業者 SOP 項目表（支援金流模式與業種類型動態調整）';
COMMENT ON COLUMN vendor_sop_items.requires_cashflow_check IS '是否需要根據金流模式調整內容';
COMMENT ON COLUMN vendor_sop_items.requires_business_type_check IS '是否需要根據業種類型調整語氣';

-- ========================================
-- 4. 建立 SOP 檢視（方便查詢）
-- ========================================

CREATE OR REPLACE VIEW v_vendor_sop_full AS
SELECT
    si.id,
    si.vendor_id,
    v.name AS vendor_name,
    v.business_type,
    v.cashflow_model,
    sc.id AS category_id,
    sc.category_name,
    sc.description AS category_description,
    si.item_number,
    si.item_name,
    si.content,
    si.requires_cashflow_check,
    si.cashflow_through_company,
    si.cashflow_direct_to_landlord,
    si.cashflow_mixed,
    si.requires_business_type_check,
    si.business_type_full_service,
    si.business_type_management,
    si.related_intent_id,
    i.name AS related_intent_name,
    si.priority,
    si.is_active,
    si.created_at
FROM vendor_sop_items si
INNER JOIN vendor_sop_categories sc ON si.category_id = sc.id
INNER JOIN vendors v ON si.vendor_id = v.id
LEFT JOIN intents i ON si.related_intent_id = i.id
WHERE si.is_active = TRUE AND sc.is_active = TRUE
ORDER BY sc.display_order, si.item_number;

COMMENT ON VIEW v_vendor_sop_full IS 'SOP 完整檢視（包含業者資訊、分類、意圖等）';

-- ========================================
-- 5. 記錄 Migration
-- ========================================

INSERT INTO schema_migrations (id, description, executed_at)
VALUES (33, 'Create vendor SOP tables (categories, items) with cashflow and business type support', NOW())
ON CONFLICT (id) DO NOTHING;

-- ========================================
-- 完成
-- ========================================

\echo '✅ Migration 33: 業者 SOP 資料表建立完成'
\echo '   - 擴充 vendors 表（business_type, cashflow_model）'
\echo '   - 建立 vendor_sop_categories 表'
\echo '   - 建立 vendor_sop_items 表'
\echo '   - 建立 v_vendor_sop_full 檢視'
