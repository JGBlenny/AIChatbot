-- ========================================
-- Platform SOP 管理系統
-- 用途：統一管理平台級 SOP 範本和業者覆寫
-- ========================================

-- ========================================
-- 1. Platform SOP 分類表
-- ========================================

CREATE TABLE IF NOT EXISTS platform_sop_categories (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    display_order INTEGER DEFAULT 0,
    template_notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_platform_sop_categories_active ON platform_sop_categories(is_active);
CREATE INDEX idx_platform_sop_categories_order ON platform_sop_categories(display_order);

CREATE TRIGGER update_platform_sop_categories_updated_at
    BEFORE UPDATE ON platform_sop_categories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE platform_sop_categories IS 'Platform SOP 分類表';

-- ========================================
-- 2. Platform SOP 範本表
-- ========================================

CREATE TABLE IF NOT EXISTS platform_sop_templates (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES platform_sop_categories(id) ON DELETE CASCADE,

    -- SOP 群組（用於邏輯分組，但不創建資料庫外鍵）
    group_id INTEGER,
    group_name VARCHAR(200),

    item_number INTEGER NOT NULL,
    item_name VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,

    -- 業種類型相關（三維度支援）
    business_type VARCHAR(50),  -- NULL=通用, full_service=包租業, property_management=代管業
    requires_business_type_check BOOLEAN DEFAULT FALSE,
    business_type_full_service TEXT,
    business_type_management TEXT,

    related_intent_id INTEGER REFERENCES intents(id) ON DELETE SET NULL,
    priority INTEGER DEFAULT 50,
    template_notes TEXT,
    customization_hint TEXT,
    common_override_fields TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_template_item UNIQUE(category_id, group_id, item_number, business_type)
);

CREATE INDEX idx_platform_sop_templates_category ON platform_sop_templates(category_id);
CREATE INDEX idx_platform_sop_templates_group ON platform_sop_templates(group_id);
CREATE INDEX idx_platform_sop_templates_intent ON platform_sop_templates(related_intent_id);
CREATE INDEX idx_platform_sop_templates_active ON platform_sop_templates(is_active);
CREATE INDEX idx_platform_sop_templates_business_type ON platform_sop_templates(business_type);

CREATE TRIGGER update_platform_sop_templates_updated_at
    BEFORE UPDATE ON platform_sop_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE platform_sop_templates IS 'Platform SOP 範本表';
COMMENT ON COLUMN platform_sop_templates.business_type IS '業種類型：NULL=通用範本, full_service=包租業, property_management=代管業';
COMMENT ON COLUMN platform_sop_templates.group_id IS 'SOP 群組 ID（邏輯分組，不是外鍵）';
COMMENT ON COLUMN platform_sop_templates.group_name IS 'SOP 群組名稱';

-- ========================================
-- 3. SOP 群組表（用於管理群組資訊）
-- ========================================

CREATE TABLE IF NOT EXISTS platform_sop_groups (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES platform_sop_categories(id) ON DELETE CASCADE,
    group_name VARCHAR(200) NOT NULL,
    description TEXT,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_category_group UNIQUE(category_id, group_name)
);

CREATE INDEX idx_platform_sop_groups_category ON platform_sop_groups(category_id);
CREATE INDEX idx_platform_sop_groups_active ON platform_sop_groups(is_active);

CREATE TRIGGER update_platform_sop_groups_updated_at
    BEFORE UPDATE ON platform_sop_groups
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE platform_sop_groups IS 'Platform SOP 群組表';

-- ========================================
-- 4. 業者 SOP 覆寫表
-- ========================================

CREATE TABLE IF NOT EXISTS vendor_sop_overrides (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE,
    template_id INTEGER REFERENCES platform_sop_templates(id) ON DELETE CASCADE,
    override_type VARCHAR(20) NOT NULL DEFAULT 'use_template',  -- use_template, customize, hide

    item_name VARCHAR(200),
    content TEXT,
    business_type_full_service TEXT,
    business_type_management TEXT,
    related_intent_id INTEGER REFERENCES intents(id) ON DELETE SET NULL,
    priority INTEGER,
    override_reason TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_vendor_template_override UNIQUE(vendor_id, template_id)
);

CREATE INDEX idx_vendor_sop_overrides_vendor ON vendor_sop_overrides(vendor_id);
CREATE INDEX idx_vendor_sop_overrides_template ON vendor_sop_overrides(template_id);
CREATE INDEX idx_vendor_sop_overrides_active ON vendor_sop_overrides(is_active);

CREATE TRIGGER update_vendor_sop_overrides_updated_at
    BEFORE UPDATE ON vendor_sop_overrides
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE vendor_sop_overrides IS '業者 SOP 覆寫表：業者可以自訂 SOP 內容';
COMMENT ON COLUMN vendor_sop_overrides.override_type IS 'use_template（使用範本）, customize（自訂）, hide（隱藏）';

-- ========================================
-- 5. Platform SOP Template Intents 多對多映射表
-- ========================================

CREATE TABLE IF NOT EXISTS platform_sop_template_intents (
    id SERIAL PRIMARY KEY,
    template_id INTEGER NOT NULL REFERENCES platform_sop_templates(id) ON DELETE CASCADE,
    intent_id INTEGER NOT NULL REFERENCES intents(id) ON DELETE CASCADE,
    intent_type VARCHAR(20) NOT NULL DEFAULT 'secondary',
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_template_intent UNIQUE(template_id, intent_id),
    CONSTRAINT check_template_intent_type CHECK (intent_type IN ('primary', 'secondary')),
    CONSTRAINT check_template_confidence CHECK (confidence >= 0 AND confidence <= 1)
);

CREATE INDEX idx_platform_sop_template_intents_template ON platform_sop_template_intents(template_id);
CREATE INDEX idx_platform_sop_template_intents_intent ON platform_sop_template_intents(intent_id);

COMMENT ON TABLE platform_sop_template_intents IS 'Platform SOP 範本-意圖多對多映射表';

-- ========================================
-- 顯示統計資訊
-- ========================================

SELECT
    '✅ Platform SOP 管理系統已建立' AS status;
