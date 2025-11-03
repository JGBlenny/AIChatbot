-- Migration 35: 建立平台 SOP 範本系統（Template + Override 架構）
-- 用途：平台管理員定義 SOP 範本，業者僅需覆寫差異部分
-- 建立時間：2025-10-18
-- 架構設計：docs/SOP_REFACTOR_ARCHITECTURE.md

-- ========================================
-- 1. 建立平台 SOP 分類表（Platform-Level Categories）
-- ========================================

CREATE TABLE IF NOT EXISTS platform_sop_categories (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    display_order INTEGER DEFAULT 0,

    -- 範本提示（幫助業者理解此分類）
    template_notes TEXT,

    -- 狀態與時間
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_platform_sop_categories_active ON platform_sop_categories(is_active);
CREATE INDEX IF NOT EXISTS idx_platform_sop_categories_order ON platform_sop_categories(display_order);

COMMENT ON TABLE platform_sop_categories IS '平台級 SOP 分類表（由平台管理員統一定義）';
COMMENT ON COLUMN platform_sop_categories.category_name IS '分類名稱（全局唯一，如：租金繳納、寵物飼養規定）';
COMMENT ON COLUMN platform_sop_categories.template_notes IS '範本說明（幫助業者理解此分類的用途和常見問題）';

-- ========================================
-- 2. 建立平台 SOP 範本表（Platform-Level Templates）
-- ========================================

CREATE TABLE IF NOT EXISTS platform_sop_templates (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES platform_sop_categories(id) ON DELETE CASCADE,

    -- 項目基本資訊
    item_number INTEGER NOT NULL,                     -- 項次（如：1, 2, 3...）
    item_name VARCHAR(200) NOT NULL,                  -- 項目名稱（如：「租金如何繳納」）
    content TEXT NOT NULL,                            -- 基礎內容（通用版本）

    -- 金流模式相關（範本提供預設值）
    requires_cashflow_check BOOLEAN DEFAULT FALSE,    -- 是否需要檢查金流模式
    cashflow_through_company TEXT,                    -- 金流過我家時的內容範本
    cashflow_direct_to_landlord TEXT,                 -- 金流不過我家時的內容範本
    cashflow_mixed TEXT,                              -- 混合型時的內容範本

    -- 業種類型相關
    requires_business_type_check BOOLEAN DEFAULT FALSE, -- 是否需要檢查業種類型
    business_type_full_service TEXT,                  -- 包租型時的語氣調整範本
    business_type_management TEXT,                    -- 代管型時的語氣調整範本

    -- 關聯與優先級
    related_intent_id INTEGER REFERENCES intents(id) ON DELETE SET NULL, -- 預設關聯意圖
    priority INTEGER DEFAULT 50,                      -- 預設優先級（0-100）

    -- 範本引導（幫助業者自訂）
    template_notes TEXT,                              -- 範本說明（解釋此 SOP 的目的）
    customization_hint TEXT,                          -- 自訂提示（建議業者如何調整）
    common_override_fields TEXT,                      -- 常見覆寫欄位（JSON array，如：["content", "priority"]）

    -- 狀態與時間
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 確保每個分類內的項次編號唯一
    CONSTRAINT unique_template_item_number UNIQUE(category_id, item_number)
);

CREATE INDEX IF NOT EXISTS idx_platform_sop_templates_category ON platform_sop_templates(category_id);
CREATE INDEX IF NOT EXISTS idx_platform_sop_templates_intent ON platform_sop_templates(related_intent_id);
CREATE INDEX IF NOT EXISTS idx_platform_sop_templates_cashflow ON platform_sop_templates(requires_cashflow_check);
CREATE INDEX IF NOT EXISTS idx_platform_sop_templates_active ON platform_sop_templates(is_active);
CREATE INDEX IF NOT EXISTS idx_platform_sop_templates_priority ON platform_sop_templates(priority DESC);

COMMENT ON TABLE platform_sop_templates IS '平台級 SOP 範本表（由平台管理員統一定義，業者可選擇性覆寫）';
COMMENT ON COLUMN platform_sop_templates.template_notes IS '範本說明（解釋此 SOP 的目的和適用場景）';
COMMENT ON COLUMN platform_sop_templates.customization_hint IS '自訂提示（建議業者如何根據自身情況調整內容）';
COMMENT ON COLUMN platform_sop_templates.common_override_fields IS '常見覆寫欄位（JSON array，統計業者最常覆寫的欄位）';

-- ========================================
-- 3. 建立業者 SOP 覆寫表（Vendor-Level Overrides）
-- ========================================

CREATE TABLE IF NOT EXISTS vendor_sop_overrides (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE,
    template_id INTEGER REFERENCES platform_sop_templates(id) ON DELETE CASCADE,

    -- 覆寫類型（決定如何使用範本）
    override_type VARCHAR(20) NOT NULL DEFAULT 'use_template',
    -- 可選值：
    --   'use_template'     : 完全使用範本（預設，不需要建立記錄）
    --   'partial_override' : 部分覆寫（只覆寫特定欄位，其他用範本）
    --   'full_override'    : 完全覆寫（完全自訂內容）
    --   'disabled'         : 停用此 SOP（此業者不適用）

    -- 覆寫欄位（NULL = 使用範本值）
    item_name VARCHAR(200),                           -- 覆寫項目名稱
    content TEXT,                                     -- 覆寫基礎內容

    -- 金流模式覆寫
    cashflow_through_company TEXT,                    -- 覆寫金流過我家版本
    cashflow_direct_to_landlord TEXT,                 -- 覆寫金流不過我家版本
    cashflow_mixed TEXT,                              -- 覆寫混合型版本

    -- 業種類型覆寫
    business_type_full_service TEXT,                  -- 覆寫包租型版本
    business_type_management TEXT,                    -- 覆寫代管型版本

    -- 關聯與優先級覆寫
    related_intent_id INTEGER REFERENCES intents(id) ON DELETE SET NULL,
    priority INTEGER,                                 -- 覆寫優先級

    -- 覆寫原因（業務記錄）
    override_reason TEXT,                             -- 為何需要覆寫（如：「本業者押金政策特殊」）

    -- 狀態與時間
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 確保每個業者對每個範本只能有一條覆寫記錄
    CONSTRAINT unique_vendor_template_override UNIQUE(vendor_id, template_id)
);

CREATE INDEX IF NOT EXISTS idx_vendor_sop_overrides_vendor ON vendor_sop_overrides(vendor_id);
CREATE INDEX IF NOT EXISTS idx_vendor_sop_overrides_template ON vendor_sop_overrides(template_id);
CREATE INDEX IF NOT EXISTS idx_vendor_sop_overrides_type ON vendor_sop_overrides(override_type);
CREATE INDEX IF NOT EXISTS idx_vendor_sop_overrides_active ON vendor_sop_overrides(is_active);

COMMENT ON TABLE vendor_sop_overrides IS '業者 SOP 覆寫表（僅儲存與範本的差異，減少資料重複）';
COMMENT ON COLUMN vendor_sop_overrides.override_type IS '覆寫類型：use_template（使用範本）, partial_override（部分覆寫）, full_override（完全覆寫）, disabled（停用）';
COMMENT ON COLUMN vendor_sop_overrides.override_reason IS '覆寫原因（業務記錄，幫助理解為何此業者需要特殊處理）';

-- ========================================
-- 4. 建立動態合併檢視（Runtime Merged View）
-- ========================================

CREATE OR REPLACE VIEW v_vendor_sop_merged AS
SELECT
    -- 業者資訊
    v.id AS vendor_id,
    v.name AS vendor_name,
    v.business_type,
    v.cashflow_model,

    -- 分類資訊
    pc.id AS category_id,
    pc.category_name,
    pc.description AS category_description,
    pc.display_order AS category_display_order,

    -- 範本資訊
    pt.id AS template_id,
    pt.item_number,

    -- 動態合併欄位（使用 COALESCE 優先使用覆寫值，否則使用範本值）
    COALESCE(vo.item_name, pt.item_name) AS item_name,
    COALESCE(vo.content, pt.content) AS content,

    -- 金流模式動態合併
    pt.requires_cashflow_check,
    COALESCE(vo.cashflow_through_company, pt.cashflow_through_company) AS cashflow_through_company,
    COALESCE(vo.cashflow_direct_to_landlord, pt.cashflow_direct_to_landlord) AS cashflow_direct_to_landlord,
    COALESCE(vo.cashflow_mixed, pt.cashflow_mixed) AS cashflow_mixed,

    -- 業種類型動態合併
    pt.requires_business_type_check,
    COALESCE(vo.business_type_full_service, pt.business_type_full_service) AS business_type_full_service,
    COALESCE(vo.business_type_management, pt.business_type_management) AS business_type_management,

    -- 關聯與優先級動態合併
    COALESCE(vo.related_intent_id, pt.related_intent_id) AS related_intent_id,
    i.name AS related_intent_name,
    COALESCE(vo.priority, pt.priority) AS priority,

    -- 覆寫狀態
    COALESCE(vo.override_type, 'use_template') AS override_type,
    vo.override_reason,

    -- 範本引導
    pt.template_notes,
    pt.customization_hint,

    -- 時間（範本為主）
    pt.created_at AS template_created_at,
    vo.created_at AS override_created_at

FROM vendors v
CROSS JOIN platform_sop_templates pt
INNER JOIN platform_sop_categories pc ON pt.category_id = pc.id
LEFT JOIN vendor_sop_overrides vo
    ON v.id = vo.vendor_id
    AND pt.id = vo.template_id
    AND vo.is_active = TRUE
LEFT JOIN intents i
    ON COALESCE(vo.related_intent_id, pt.related_intent_id) = i.id

WHERE
    pt.is_active = TRUE
    AND pc.is_active = TRUE
    AND (vo.override_type IS NULL OR vo.override_type != 'disabled')  -- 排除已停用的 SOP

ORDER BY
    v.id,
    pc.display_order,
    pt.item_number;

COMMENT ON VIEW v_vendor_sop_merged IS 'SOP 動態合併檢視（自動合併平台範本與業者覆寫，實現繼承邏輯）';

-- ========================================
-- 5. 建立業者未覆寫檢視（Available Templates for Vendor）
-- ========================================

CREATE OR REPLACE VIEW v_vendor_available_templates AS
SELECT
    v.id AS vendor_id,
    v.name AS vendor_name,
    pt.id AS template_id,
    pc.category_name,
    pt.item_number,
    pt.item_name,
    pt.template_notes,
    pt.customization_hint,
    CASE
        WHEN vo.id IS NULL THEN 'use_template'
        ELSE vo.override_type
    END AS current_status

FROM vendors v
CROSS JOIN platform_sop_templates pt
INNER JOIN platform_sop_categories pc ON pt.category_id = pc.id
LEFT JOIN vendor_sop_overrides vo
    ON v.id = vo.vendor_id
    AND pt.id = vo.template_id

WHERE pt.is_active = TRUE AND pc.is_active = TRUE

ORDER BY v.id, pc.display_order, pt.item_number;

COMMENT ON VIEW v_vendor_available_templates IS '業者可用範本檢視（顯示所有範本及業者當前覆寫狀態）';

-- ========================================
-- 6. 建立覆寫統計檢視（Override Statistics）
-- ========================================

CREATE OR REPLACE VIEW v_sop_override_statistics AS
SELECT
    pt.id AS template_id,
    pc.category_name,
    pt.item_name,
    COUNT(DISTINCT vo.vendor_id) AS total_overrides,
    COUNT(DISTINCT CASE WHEN vo.override_type = 'partial_override' THEN vo.vendor_id END) AS partial_overrides,
    COUNT(DISTINCT CASE WHEN vo.override_type = 'full_override' THEN vo.vendor_id END) AS full_overrides,
    COUNT(DISTINCT CASE WHEN vo.override_type = 'disabled' THEN vo.vendor_id END) AS disabled_count,
    ROUND(
        COUNT(DISTINCT vo.vendor_id)::NUMERIC / NULLIF(COUNT(DISTINCT v.id), 0) * 100,
        2
    ) AS override_percentage

FROM platform_sop_templates pt
INNER JOIN platform_sop_categories pc ON pt.category_id = pc.id
CROSS JOIN vendors v
LEFT JOIN vendor_sop_overrides vo
    ON pt.id = vo.template_id
    AND vo.is_active = TRUE

WHERE pt.is_active = TRUE AND pc.is_active = TRUE

GROUP BY pt.id, pc.category_name, pt.item_name

ORDER BY override_percentage DESC, total_overrides DESC;

COMMENT ON VIEW v_sop_override_statistics IS '覆寫統計檢視（分析哪些範本最常被覆寫，幫助優化範本設計）';

-- ========================================
-- 7. 建立實用函數：取得業者的最終 SOP 內容
-- ========================================

CREATE OR REPLACE FUNCTION get_vendor_sop_content(
    p_vendor_id INTEGER,
    p_template_id INTEGER
) RETURNS TABLE (
    item_name VARCHAR(200),
    final_content TEXT,
    override_type VARCHAR(20),
    source VARCHAR(20)  -- 'template' or 'override'
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(vo.item_name, pt.item_name) AS item_name,
        COALESCE(vo.content, pt.content) AS final_content,
        COALESCE(vo.override_type, 'use_template') AS override_type,
        CASE
            WHEN vo.content IS NOT NULL THEN 'override'::VARCHAR(20)
            ELSE 'template'::VARCHAR(20)
        END AS source
    FROM platform_sop_templates pt
    LEFT JOIN vendor_sop_overrides vo
        ON pt.id = vo.template_id
        AND vo.vendor_id = p_vendor_id
        AND vo.is_active = TRUE
    WHERE pt.id = p_template_id
      AND pt.is_active = TRUE
      AND (vo.override_type IS NULL OR vo.override_type != 'disabled');
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_vendor_sop_content IS '取得業者的最終 SOP 內容（自動合併範本與覆寫）';

-- ========================================
-- 8. 記錄 Migration
-- ========================================

INSERT INTO schema_migrations (id, description, executed_at)
VALUES (35, 'Create platform SOP template system with vendor override mechanism', NOW())
ON CONFLICT (id) DO NOTHING;

-- ========================================
-- 完成
-- ========================================

\echo '✅ Migration 35: 平台 SOP 範本系統建立完成'
\echo '   - 建立 platform_sop_categories 表（平台分類）'
\echo '   - 建立 platform_sop_templates 表（平台範本）'
\echo '   - 建立 vendor_sop_overrides 表（業者覆寫）'
\echo '   - 建立 v_vendor_sop_merged 檢視（動態合併）'
\echo '   - 建立 v_vendor_available_templates 檢視（可用範本）'
\echo '   - 建立 v_sop_override_statistics 檢視（覆寫統計）'
\echo '   - 建立 get_vendor_sop_content 函數（內容查詢）'
\echo ''
\echo '📝 注意：'
\echo '   - 舊表（vendor_sop_categories, vendor_sop_items）保留以確保向後兼容'
\echo '   - 需執行資料遷移工具將舊資料轉換為新架構'
\echo '   - 參考文檔：docs/SOP_REFACTOR_ARCHITECTURE.md'
