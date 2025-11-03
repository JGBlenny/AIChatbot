-- Migration: 39-create-target-user-config.sql
-- 目的: 創建 target_user_config 配置表，用於管理目標用戶類型
-- 類似 business_types_config 的設計模式

BEGIN;

-- 1. 創建 target_user_config 表
CREATE TABLE IF NOT EXISTS target_user_config (
    id SERIAL PRIMARY KEY,
    user_value VARCHAR(50) NOT NULL UNIQUE,  -- 用戶類型值 (如: tenant, landlord)
    display_name VARCHAR(100) NOT NULL,       -- 顯示名稱 (如: 租客, 房東)
    description TEXT,                         -- 說明
    icon VARCHAR(50),                         -- 圖標 (emoji 或圖示代碼)
    display_order INTEGER DEFAULT 0,          -- 顯示順序
    is_active BOOLEAN DEFAULT TRUE,           -- 是否啟用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 建立索引
CREATE INDEX idx_target_user_config_active ON target_user_config(is_active);
CREATE INDEX idx_target_user_config_order ON target_user_config(display_order);

-- 3. 插入預設的目標用戶類型
INSERT INTO target_user_config (user_value, display_name, description, icon, display_order) VALUES
('tenant', '租客', '承租人 - 租屋的一方', '👤', 1),
('landlord', '房東', '出租人 - 提供租屋的一方', '🏠', 2),
('property_manager', '物業管理師', '協助管理租賃事務的專業人員', '👔', 3),
('system_admin', '系統管理員', '系統後台管理人員', '⚙️', 4);

-- 4. 新增註釋
COMMENT ON TABLE target_user_config IS '目標用戶類型配置表 - 定義知識庫可針對的用戶類型';
COMMENT ON COLUMN target_user_config.user_value IS '用戶類型值（唯一識別碼）';
COMMENT ON COLUMN target_user_config.display_name IS '顯示名稱（前端顯示用）';
COMMENT ON COLUMN target_user_config.description IS '說明文字';
COMMENT ON COLUMN target_user_config.icon IS '圖標（emoji 或圖示）';
COMMENT ON COLUMN target_user_config.display_order IS '顯示順序';
COMMENT ON COLUMN target_user_config.is_active IS '是否啟用';

-- 5. 創建更新觸發器
CREATE TRIGGER update_target_user_config_updated_at
    BEFORE UPDATE ON target_user_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMIT;

-- 完成通知
\echo '══════════════════════════════════════════'
\echo '  Migration 39 完成'
\echo '  已創建 target_user_config 配置表'
\echo '  已插入 4 種預設用戶類型'
\echo '══════════════════════════════════════════'
