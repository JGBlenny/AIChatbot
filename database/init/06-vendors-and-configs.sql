-- ============================================
-- Phase 1: Multi-Vendor Support
-- 包租代管業者（Vendors）及其配置參數
-- ============================================

-- 包租代管業者表（系統商的客戶）
CREATE TABLE IF NOT EXISTS vendors (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,                    -- 業者代碼（唯一識別）
    name VARCHAR(200) NOT NULL,                          -- 業者名稱
    short_name VARCHAR(100),                             -- 簡稱
    contact_phone VARCHAR(50),                           -- 聯絡電話
    contact_email VARCHAR(100),                          -- 聯絡郵箱
    address TEXT,                                        -- 公司地址

    -- 訂閱設定
    subscription_plan VARCHAR(50) DEFAULT 'basic',       -- 訂閱方案
    subscription_status VARCHAR(20) DEFAULT 'active',    -- active, suspended, expired
    subscription_start_date DATE,                        -- 訂閱開始日期
    subscription_end_date DATE,                          -- 訂閱結束日期

    -- 系統設定（JSONB 儲存彈性配置）
    settings JSONB DEFAULT '{}',                         -- 額外設定（如 LINE Bot token 等）

    -- 狀態管理
    is_active BOOLEAN DEFAULT true,                      -- 是否啟用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);

-- 業者配置參數表（各業者的差異化參數）
CREATE TABLE IF NOT EXISTS vendor_configs (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,

    -- 參數分類和鍵值
    category VARCHAR(50) NOT NULL,                       -- 分類：payment, contract, service, contact
    param_key VARCHAR(100) NOT NULL,                     -- 參數鍵（如 payment_day）
    param_value TEXT NOT NULL,                           -- 參數值

    -- 參數元數據
    data_type VARCHAR(20) DEFAULT 'string',              -- string, number, date, boolean, json
    display_name VARCHAR(200),                           -- 顯示名稱（用於前端）
    description TEXT,                                    -- 參數說明
    unit VARCHAR(20),                                    -- 單位（如：元、天、%）

    -- 狀態
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 確保同一業者的同一分類下參數鍵唯一
    UNIQUE(vendor_id, category, param_key)
);

-- 建立索引加速查詢
CREATE INDEX idx_vendor_configs_vendor_id ON vendor_configs(vendor_id);
CREATE INDEX idx_vendor_configs_category ON vendor_configs(category);
CREATE INDEX idx_vendors_code ON vendors(code);
CREATE INDEX idx_vendors_active ON vendors(is_active);

-- ============================================
-- 插入測試資料
-- ============================================

-- 業者 A: 甲山林包租代管
INSERT INTO vendors (code, name, short_name, contact_phone, contact_email, subscription_plan, subscription_start_date, created_by)
VALUES ('VENDOR_A', '甲山林包租代管股份有限公司', '甲山林', '02-2345-6789', 'service@vendorA.com', 'premium', '2024-01-01', 'system');

-- 業者 B: 信義包租代管
INSERT INTO vendors (code, name, short_name, contact_phone, contact_email, subscription_plan, subscription_start_date, created_by)
VALUES ('VENDOR_B', '信義包租代管股份有限公司', '信義', '02-8765-4321', 'support@vendorB.com', 'standard', '2024-02-01', 'system');

-- 業者 A 配置參數
-- 帳務類別
INSERT INTO vendor_configs (vendor_id, category, param_key, param_value, data_type, display_name, description, unit)
VALUES
    (1, 'payment', 'payment_day', '1', 'number', '繳費日期', '每月繳費日期', '號'),
    (1, 'payment', 'payment_method', '銀行轉帳、超商繳費', 'string', '繳費方式', '可用的繳費方式', NULL),
    (1, 'payment', 'late_fee', '200', 'number', '逾期手續費', '逾期繳費手續費', '元'),
    (1, 'payment', 'grace_period', '5', 'number', '繳費寬限期', '繳費日後的寬限天數', '天');

-- 合約類別
INSERT INTO vendor_configs (vendor_id, category, param_key, param_value, data_type, display_name, description, unit)
VALUES
    (1, 'contract', 'min_lease_period', '12', 'number', '最短租期', '最短租賃期限', '月'),
    (1, 'contract', 'deposit_months', '2', 'number', '押金月數', '押金為月租的倍數', '月'),
    (1, 'contract', 'termination_notice_days', '30', 'number', '提前解約通知期', '提前解約需通知天數', '天');

-- 服務類別
INSERT INTO vendor_configs (vendor_id, category, param_key, param_value, data_type, display_name, description, unit)
VALUES
    (1, 'service', 'service_hotline', '02-2345-6789', 'string', '客服專線', '24小時客服專線', NULL),
    (1, 'service', 'service_hours', '週一至週日 09:00-21:00', 'string', '服務時間', '客服服務時間', NULL),
    (1, 'service', 'emergency_repair_hours', '24小時', 'string', '緊急報修時效', '緊急報修處理時效', NULL);

-- 聯絡資訊類別
INSERT INTO vendor_configs (vendor_id, category, param_key, param_value, data_type, display_name, description, unit)
VALUES
    (1, 'contact', 'office_address', '台北市信義區信義路五段100號', 'string', '公司地址', '總公司地址', NULL),
    (1, 'contact', 'line_id', '@vendorA', 'string', 'LINE 官方帳號', 'LINE 官方客服帳號', NULL);

-- 業者 B 配置參數
-- 帳務類別
INSERT INTO vendor_configs (vendor_id, category, param_key, param_value, data_type, display_name, description, unit)
VALUES
    (2, 'payment', 'payment_day', '5', 'number', '繳費日期', '每月繳費日期', '號'),
    (2, 'payment', 'payment_method', '銀行轉帳、信用卡', 'string', '繳費方式', '可用的繳費方式', NULL),
    (2, 'payment', 'late_fee', '300', 'number', '逾期手續費', '逾期繳費手續費', '元'),
    (2, 'payment', 'grace_period', '3', 'number', '繳費寬限期', '繳費日後的寬限天數', '天');

-- 合約類別
INSERT INTO vendor_configs (vendor_id, category, param_key, param_value, data_type, display_name, description, unit)
VALUES
    (2, 'contract', 'min_lease_period', '6', 'number', '最短租期', '最短租賃期限', '月'),
    (2, 'contract', 'deposit_months', '2', 'number', '押金月數', '押金為月租的倍數', '月'),
    (2, 'contract', 'termination_notice_days', '60', 'number', '提前解約通知期', '提前解約需通知天數', '天');

-- 服務類別
INSERT INTO vendor_configs (vendor_id, category, param_key, param_value, data_type, display_name, description, unit)
VALUES
    (2, 'service', 'service_hotline', '02-8765-4321', 'string', '客服專線', '客服專線', NULL),
    (2, 'service', 'service_hours', '週一至週五 09:00-18:00', 'string', '服務時間', '客服服務時間', NULL),
    (2, 'service', 'emergency_repair_hours', '2小時內回應', 'string', '緊急報修時效', '緊急報修處理時效', NULL);

-- 聯絡資訊類別
INSERT INTO vendor_configs (vendor_id, category, param_key, param_value, data_type, display_name, description, unit)
VALUES
    (2, 'contact', 'office_address', '台北市大安區仁愛路三段200號', 'string', '公司地址', '總公司地址', NULL),
    (2, 'contact', 'line_id', '@vendorB', 'string', 'LINE 官方帳號', 'LINE 官方客服帳號', NULL);

-- ============================================
-- 註解說明
-- ============================================
COMMENT ON TABLE vendors IS '包租代管業者表（系統商的客戶）';
COMMENT ON TABLE vendor_configs IS '業者配置參數表（各業者的差異化參數）';

COMMENT ON COLUMN vendors.code IS '業者代碼（唯一識別，用於 API）';
COMMENT ON COLUMN vendors.subscription_plan IS '訂閱方案：basic, standard, premium';
COMMENT ON COLUMN vendors.settings IS '額外設定（JSONB），如 LINE Bot token 等';

COMMENT ON COLUMN vendor_configs.category IS '參數分類：payment, contract, service, contact';
COMMENT ON COLUMN vendor_configs.data_type IS '資料型別：string, number, date, boolean, json';
COMMENT ON COLUMN vendor_configs.unit IS '參數單位：元、天、%、月等';
