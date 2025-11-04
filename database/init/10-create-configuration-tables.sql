-- ========================================
-- 配置管理表
-- 用途：業態類型、目標用戶、系統參數等配置
-- ========================================

-- ========================================
-- 1. 業態類型配置表
-- ========================================

CREATE TABLE IF NOT EXISTS business_types_config (
    id SERIAL PRIMARY KEY,
    type_value VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    display_order INT DEFAULT 0,
    icon VARCHAR(50),
    color VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_business_types_config_active ON business_types_config(is_active);
CREATE INDEX idx_business_types_config_order ON business_types_config(display_order);

CREATE TRIGGER update_business_types_config_updated_at
    BEFORE UPDATE ON business_types_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE business_types_config IS '業態類型配置表：定義系統支援的業態類型';

-- 插入預設數據
INSERT INTO business_types_config (type_value, display_name, description, display_order, icon, color) VALUES
('system_provider', '系統商', '提供系統平台給其他業者使用的服務商', 10, '💻', 'blue'),
('full_service', '包租型', '包租代管業者，負責招租和物業管理', 20, '🏢', 'green'),
('property_management', '代管型', '僅提供物業管理服務的業者', 30, '🏠', 'orange')
ON CONFLICT (type_value) DO NOTHING;

-- ========================================
-- 2. 目標用戶配置表
-- ========================================

CREATE TABLE IF NOT EXISTS target_user_config (
    id SERIAL PRIMARY KEY,
    user_value VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_target_user_config_active ON target_user_config(is_active);
CREATE INDEX idx_target_user_config_order ON target_user_config(display_order);

CREATE TRIGGER update_target_user_config_updated_at
    BEFORE UPDATE ON target_user_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE target_user_config IS '目標用戶配置表：定義系統支援的用戶類型';

-- 插入預設數據
INSERT INTO target_user_config (user_value, display_name, description, icon, display_order) VALUES
('tenant', '租客', '承租人 - 租屋的一方', '👤', 1),
('landlord', '房東', '出租人 - 提供租屋的一方', '🏠', 2),
('property_manager', '物業管理師', '協助管理租賃事務的專業人員', '👔', 3),
('system_admin', '系統管理員', '系統後台管理人員', '⚙️', 4)
ON CONFLICT (user_value) DO NOTHING;

-- ========================================
-- 3. 分類配置表
-- ========================================

CREATE TABLE IF NOT EXISTS category_config (
    id SERIAL PRIMARY KEY,
    category_value VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    display_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_category_config_active ON category_config(is_active);
CREATE INDEX idx_category_config_order ON category_config(display_order);
CREATE INDEX idx_category_config_value ON category_config(category_value);

CREATE TRIGGER update_category_config_updated_at
    BEFORE UPDATE ON category_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE category_config IS '分類配置表：管理知識庫分類選項（目前未使用，保留供未來擴展）';
COMMENT ON COLUMN category_config.category_value IS '實際儲存值';
COMMENT ON COLUMN category_config.display_name IS '前端顯示名稱';
COMMENT ON COLUMN category_config.display_order IS '顯示順序，數字越小越靠前';
COMMENT ON COLUMN category_config.is_active IS '是否啟用';
COMMENT ON COLUMN category_config.usage_count IS '使用次數';

-- 插入預設數據
INSERT INTO category_config (category_value, display_name, display_order, description, usage_count) VALUES
('合約問題', '合約問題', 1, '租約合約相關規定、簽約流程、合約內容等', 0),
('帳務問題', '帳務問題', 2, '帳單、費用、繳費記錄等財務相關問題', 0),
('服務問題', '服務問題', 3, 'JGB 服務內容、申請流程、入住手續等', 0),
('設備報修', '設備報修', 4, '設備故障報修、維修進度查詢', 0),
('設施使用', '設施使用', 5, '社區公共設施使用相關問題', 0),
('設施問題', '設施問題', 6, '設施故障、問題回報', 0),
('物件問題', '物件問題', 7, '租賃物件地址、資訊相關問題', 0),
('帳號問題', '帳號問題', 8, '帳號註冊、登入、密碼重設等問題', 0),
('其他', '其他', 999, '其他未分類問題', 0)
ON CONFLICT (category_value) DO NOTHING;

-- ========================================
-- 4. 系統參數定義表
-- ========================================

CREATE TABLE IF NOT EXISTS system_param_definitions (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,          -- payment, contract, service, contact
    param_key VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    data_type VARCHAR(20) NOT NULL,         -- string, number, boolean, text
    unit VARCHAR(20),
    description TEXT,
    default_value TEXT,
    placeholder TEXT,
    is_required BOOLEAN DEFAULT false,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_param_def_category ON system_param_definitions(category);
CREATE INDEX idx_param_def_active ON system_param_definitions(is_active);
CREATE INDEX idx_param_def_key ON system_param_definitions(param_key);

CREATE TRIGGER update_system_param_definitions_updated_at
    BEFORE UPDATE ON system_param_definitions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE system_param_definitions IS '系統參數定義表：定義可配置的系統參數';

-- 插入預設參數定義
INSERT INTO system_param_definitions (category, param_key, display_name, data_type, unit, description, default_value, display_order) VALUES
-- 繳費相關參數
('payment', 'payment_day', '每月繳費日', 'number', '號', '租金繳費日期', '5', 10),
('payment', 'grace_period', '寬限期', 'number', '天', '繳費寬限天數', '3', 20),
('payment', 'late_fee', '逾期手續費', 'number', '元', '逾期繳費手續費金額', '300', 30),
('payment', 'payment_method', '繳費方式', 'text', NULL, '可用的繳費方式', '轉帳、ATM、超商繳費', 40),

-- 合約相關參數
('contract', 'min_lease_period', '最短租期', 'number', '月', '最短租賃期限', '12', 10),
('contract', 'deposit_months', '押金月數', 'number', '個月', '押金為幾個月租金', '2', 20),
('contract', 'termination_notice_days', '解約通知天數', 'number', '天', '提前解約需提前通知的天數', '30', 30),

-- 服務相關參數
('service', 'service_hotline', '客服專線', 'string', NULL, '客服聯絡電話', '0800-000-000', 10),
('service', 'service_hours', '服務時間', 'string', NULL, '客服服務時間', '週一至週五 9:00-18:00', 20),
('service', 'repair_response_time', '報修回應時間', 'number', '小時', '緊急報修回應時限', '24', 30),
('service', 'line_id', 'LINE 官方帳號', 'string', NULL, 'LINE 官方帳號 ID', '@example', 40),

-- 聯絡資訊
('contact', 'office_address', '公司地址', 'text', NULL, '公司辦公室地址', '台北市信義區信義路五段7號', 10),
('contact', 'company_email', '公司信箱', 'string', NULL, '公司聯絡信箱', 'service@example.com', 20)
ON CONFLICT (param_key) DO NOTHING;

-- ========================================
-- 顯示統計資訊
-- ========================================

SELECT
    '✅ 配置管理表已建立' AS status,
    (SELECT COUNT(*) FROM business_types_config) AS business_types_count,
    (SELECT COUNT(*) FROM target_user_config) AS target_users_count,
    (SELECT COUNT(*) FROM category_config) AS category_count,
    (SELECT COUNT(*) FROM system_param_definitions) AS param_definitions_count;
