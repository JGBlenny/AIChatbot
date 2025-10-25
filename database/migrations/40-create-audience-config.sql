-- Migration 40: 建立 audience_config 配置表
-- 用途：動態管理受眾（audience）選項及其與業務範圍的映射
-- 建立時間：2025-10-24
--
-- 背景：
--   目前 audience 選項和 business_scope 映射都是硬編碼在代碼中：
--   - 前端：KnowledgeView.vue 的下拉選項
--   - 後端：business_scope_utils.py 的映射關係
--
-- 改進：
--   建立配置表，允許管理員從後台動態管理 audience：
--   - 新增/編輯/停用 audience 選項
--   - 定義 audience 屬於哪個 business_scope (external/internal/both)
--   - 控制顯示順序
--
-- 設計：
--   audience_config 表：
--   - audience_value: 實際存儲的值（如：'租客', '管理師'）
--   - display_name: 顯示名稱
--   - business_scope: 'external' (B2C) / 'internal' (B2B) / 'both' (通用)
--   - display_order: 顯示順序
--   - is_active: 是否啟用

-- ========================================
-- 1. 建立 audience_config 表
-- ========================================

CREATE TABLE IF NOT EXISTS audience_config (
    id SERIAL PRIMARY KEY,

    -- 核心欄位
    audience_value VARCHAR(50) UNIQUE NOT NULL,  -- 實際值（如：'租客', '管理師'）
    display_name VARCHAR(100) NOT NULL,          -- 顯示名稱
    business_scope VARCHAR(20) NOT NULL          -- 'external', 'internal', 'both'
        CHECK (business_scope IN ('external', 'internal', 'both')),

    -- 輔助欄位
    description TEXT,                             -- 說明
    display_order INT DEFAULT 0,                  -- 顯示順序（數字越小越前面）
    is_active BOOLEAN DEFAULT TRUE,               -- 是否啟用

    -- 時間戳記
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_audience_config_scope ON audience_config(business_scope);
CREATE INDEX IF NOT EXISTS idx_audience_config_active ON audience_config(is_active);
CREATE INDEX IF NOT EXISTS idx_audience_config_order ON audience_config(display_order);

-- 註釋
COMMENT ON TABLE audience_config IS 'Audience（受眾）配置表：動態管理知識庫的受眾選項及其業務範圍映射';
COMMENT ON COLUMN audience_config.audience_value IS '實際存儲的受眾值（與 knowledge_base.audience 對應）';
COMMENT ON COLUMN audience_config.business_scope IS '業務範圍：external(B2C), internal(B2B), both(通用)';
COMMENT ON COLUMN audience_config.display_order IS '顯示順序（越小越前面）';

-- ========================================
-- 2. 插入預設數據
-- ========================================

-- B2C（External）受眾
INSERT INTO audience_config (audience_value, display_name, business_scope, description, display_order) VALUES
('租客', '租客', 'external', 'B2C - 租客專用知識', 10),
('房東', '房東', 'external', 'B2C - 房東專用知識', 20),
('租客|管理師', '租客|管理師', 'both', '租客和管理師都可見', 30),
('房東|租客', '房東|租客', 'external', 'B2C - 房東和租客都可見', 40),
('房東|租客|管理師', '房東|租客|管理師', 'both', '房東、租客、管理師都可見', 50);

-- B2B（Internal）受眾
INSERT INTO audience_config (audience_value, display_name, business_scope, description, display_order) VALUES
('管理師', '管理師', 'internal', 'B2B - 管理師專用知識', 100),
('系統管理員', '系統管理員', 'internal', 'B2B - 系統管理員專用知識', 110),
('房東/管理師', '房東/管理師', 'internal', 'B2B - 房東相關的內部管理', 120);

-- 通用受眾
INSERT INTO audience_config (audience_value, display_name, business_scope, description, display_order) VALUES
('general', '所有人（通用）', 'both', '所有業務範圍都可見（B2C 和 B2B）', 200);

-- 兼容舊數據：添加 'tenant' 選項（如果現有數據中有使用）
INSERT INTO audience_config (audience_value, display_name, business_scope, description, display_order) VALUES
('tenant', 'Tenant (租客英文)', 'external', 'B2C - 租客（英文版）', 15)
ON CONFLICT (audience_value) DO NOTHING;

-- ========================================
-- 3. 建立檢視：依業務範圍分組
-- ========================================

CREATE OR REPLACE VIEW v_audience_by_scope AS
SELECT
    business_scope,
    CASE
        WHEN business_scope = 'external' THEN 'B2C - 終端用戶（External）'
        WHEN business_scope = 'internal' THEN 'B2B - 內部管理（Internal）'
        WHEN business_scope = 'both' THEN '通用（Both）'
    END as scope_display_name,
    audience_value,
    display_name,
    description,
    display_order,
    is_active
FROM audience_config
WHERE is_active = TRUE
ORDER BY
    CASE business_scope
        WHEN 'external' THEN 1
        WHEN 'both' THEN 2
        WHEN 'internal' THEN 3
    END,
    display_order;

COMMENT ON VIEW v_audience_by_scope IS '依業務範圍分組的受眾檢視（僅顯示啟用的選項）';

-- ========================================
-- 4. 建立更新 updated_at 的觸發器
-- ========================================

CREATE TRIGGER update_audience_config_updated_at
    BEFORE UPDATE ON audience_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- 5. 驗證查詢範例
-- ========================================

-- 查詢所有啟用的受眾（依顯示順序）
-- SELECT * FROM audience_config WHERE is_active = TRUE ORDER BY display_order;

-- 查詢 external (B2C) 受眾
-- SELECT * FROM audience_config WHERE business_scope IN ('external', 'both') AND is_active = TRUE ORDER BY display_order;

-- 查詢 internal (B2B) 受眾
-- SELECT * FROM audience_config WHERE business_scope IN ('internal', 'both') AND is_active = TRUE ORDER BY display_order;

-- 使用檢視查詢（推薦）
-- SELECT * FROM v_audience_by_scope;

-- ========================================
-- 6. 記錄 Migration
-- ========================================

INSERT INTO schema_migrations (id, description, executed_at)
VALUES (40, 'Create audience_config table for dynamic audience management', NOW())
ON CONFLICT (id) DO NOTHING;

-- ========================================
-- 完成
-- ========================================

\echo '✅ Migration 40: audience_config 配置表建立完成'
\echo '   - 已建立 audience_config 表'
\echo '   - 已插入預設受眾數據（B2C + B2B + 通用）'
\echo '   - 已建立 v_audience_by_scope 檢視'
\echo ''
\echo '📊 預設受眾統計：'
SELECT
    business_scope,
    COUNT(*) as count
FROM audience_config
GROUP BY business_scope
ORDER BY business_scope;

\echo ''
\echo '📝 使用範例：'
\echo '   - 查詢所有啟用的受眾：SELECT * FROM audience_config WHERE is_active = TRUE ORDER BY display_order;'
\echo '   - 查詢 B2C 受眾：SELECT * FROM v_audience_by_scope WHERE business_scope IN (''external'', ''both'');'
\echo '   - 新增受眾：INSERT INTO audience_config (audience_value, display_name, business_scope, display_order) VALUES (''新受眾'', ''新受眾名稱'', ''external'', 25);'
\echo '   - 停用受眾：UPDATE audience_config SET is_active = FALSE WHERE audience_value = ''舊受眾'';'
