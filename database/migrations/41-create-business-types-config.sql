-- Migration 41: 建立 business_types_config 配置表
-- 用途：統一管理業態類型選項
-- 建立時間：2025-10-24
--
-- 背景：
--   目前業態類型（business_types）是硬編碼的值：
--   - system_provider（系統商）
--   - full_service（包租型）
--   - property_management（代管型）
--
--   這些值目前只能在業者管理頁面中選擇，沒有統一管理的地方。
--
-- 改進：
--   建立配置表，允許管理員從後台動態管理業態類型：
--   - 新增/編輯/停用業態類型
--   - 定義顯示名稱、說明、圖標、顏色
--   - 控制顯示順序

-- ========================================
-- 1. 建立 business_types_config 表
-- ========================================

CREATE TABLE IF NOT EXISTS business_types_config (
    id SERIAL PRIMARY KEY,

    -- 核心欄位
    type_value VARCHAR(50) UNIQUE NOT NULL,      -- 實際值（如：'system_provider'）
    display_name VARCHAR(100) NOT NULL,          -- 顯示名稱（如：'系統商'）
    description TEXT,                             -- 說明

    -- 顯示相關
    display_order INT DEFAULT 0,                  -- 顯示順序（數字越小越前面）
    icon VARCHAR(50),                             -- 圖標（如：'🏢', '🏠'）
    color VARCHAR(20),                            -- 顏色標籤（如：'blue', 'green'）

    -- 狀態
    is_active BOOLEAN DEFAULT TRUE,               -- 是否啟用

    -- 時間戳記
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_business_types_config_active ON business_types_config(is_active);
CREATE INDEX IF NOT EXISTS idx_business_types_config_order ON business_types_config(display_order);

-- 註釋
COMMENT ON TABLE business_types_config IS '業態類型配置表：統一管理業者的業態類型選項';
COMMENT ON COLUMN business_types_config.type_value IS '業態類型值（與 vendors.business_types 陣列中的值對應）';
COMMENT ON COLUMN business_types_config.display_name IS '顯示名稱（在前端選單顯示）';
COMMENT ON COLUMN business_types_config.display_order IS '顯示順序（越小越前面）';
COMMENT ON COLUMN business_types_config.icon IS '圖標 emoji（可選）';
COMMENT ON COLUMN business_types_config.color IS '顏色標籤（用於前端顯示，如：blue, green, orange）';

-- ========================================
-- 2. 插入預設數據
-- ========================================

-- 插入現有的三種業態類型
INSERT INTO business_types_config (type_value, display_name, description, display_order, icon, color) VALUES
('system_provider', '系統商', '提供系統平台給其他業者使用的服務商', 10, '💻', 'blue'),
('full_service', '包租型', '包租代管業者，負責招租和物業管理', 20, '🏢', 'green'),
('property_management', '代管型', '僅提供物業管理服務的業者', 30, '🏠', 'orange');

-- ========================================
-- 3. 建立更新 updated_at 的觸發器
-- ========================================

CREATE TRIGGER update_business_types_config_updated_at
    BEFORE UPDATE ON business_types_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- 4. 建立檢視：僅顯示啟用的業態類型
-- ========================================

CREATE OR REPLACE VIEW v_active_business_types AS
SELECT
    id,
    type_value,
    display_name,
    description,
    display_order,
    icon,
    color,
    is_active
FROM business_types_config
WHERE is_active = TRUE
ORDER BY display_order, id;

COMMENT ON VIEW v_active_business_types IS '啟用的業態類型檢視（依顯示順序排序）';

-- ========================================
-- 5. 驗證查詢範例
-- ========================================

-- 查詢所有啟用的業態類型（依顯示順序）
-- SELECT * FROM business_types_config WHERE is_active = TRUE ORDER BY display_order;

-- 查詢特定業態類型
-- SELECT * FROM business_types_config WHERE type_value = 'full_service';

-- 使用檢視查詢
-- SELECT * FROM v_active_business_types;

-- ========================================
-- 6. 記錄 Migration
-- ========================================

INSERT INTO schema_migrations (id, description, executed_at)
VALUES (41, 'Create business_types_config table for dynamic business types management', NOW())
ON CONFLICT (id) DO NOTHING;

-- ========================================
-- 完成
-- ========================================

\echo '✅ Migration 41: business_types_config 配置表建立完成'
\echo '   - 已建立 business_types_config 表'
\echo '   - 已插入 3 種預設業態類型（系統商、包租型、代管型）'
\echo '   - 已建立 v_active_business_types 檢視'
\echo ''
\echo '📊 預設業態類型：'
SELECT type_value, display_name, icon, color FROM business_types_config ORDER BY display_order;

\echo ''
\echo '📝 使用範例：'
\echo '   - 查詢所有業態：SELECT * FROM business_types_config ORDER BY display_order;'
\echo '   - 新增業態：INSERT INTO business_types_config (type_value, display_name, description, display_order, icon, color) VALUES (''new_type'', ''新業態'', ''說明'', 40, ''🎯'', ''purple'');'
\echo '   - 停用業態：UPDATE business_types_config SET is_active = FALSE WHERE type_value = ''old_type'';'
