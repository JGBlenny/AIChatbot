-- ==========================================
-- Migration 48: 建立系統參數定義表
-- ==========================================
--
-- 目的：規範化業者配置參數，避免參數名稱和類型不一致
--
-- 步驟：
-- 1. 創建 system_param_definitions 表（系統級參數模板）
-- 2. 修改 vendor_configs 表結構
-- 3. 插入預設參數定義
--
-- ==========================================

BEGIN;

-- Step 1: 創建系統參數定義表
CREATE TABLE IF NOT EXISTS system_param_definitions (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,          -- payment, contract, service, contact
    param_key VARCHAR(100) NOT NULL UNIQUE, -- payment_day, late_fee, grace_period
    display_name VARCHAR(200) NOT NULL,     -- 繳費日, 逾期費用, 寬限期
    data_type VARCHAR(20) NOT NULL,         -- string, number, boolean, text
    unit VARCHAR(20),                       -- 元, 天, %, 小時
    description TEXT,                       -- 參數說明
    default_value TEXT,                     -- 預設值
    placeholder TEXT,                       -- 輸入提示
    is_required BOOLEAN DEFAULT false,      -- 是否必填
    display_order INTEGER DEFAULT 0,        -- 顯示順序
    is_active BOOLEAN DEFAULT true,         -- 是否啟用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_param_def_category ON system_param_definitions(category);
CREATE INDEX IF NOT EXISTS idx_param_def_active ON system_param_definitions(is_active);

-- Step 2: 檢查 vendor_configs 表是否需要調整
-- 確保 vendor_configs 只儲存業者特定的值，參數定義來自 system_param_definitions
DO $$
BEGIN
    -- 如果 vendor_configs 表有 custom 欄位，移除它（因為不再支援自訂參數）
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vendor_configs' AND column_name = 'custom'
    ) THEN
        ALTER TABLE vendor_configs DROP COLUMN custom;
    END IF;
END $$;

-- Step 3: 插入預設參數定義

-- 帳務設定 (payment)
INSERT INTO system_param_definitions (category, param_key, display_name, data_type, unit, description, default_value, placeholder, is_required, display_order) VALUES
('payment', 'payment_day', '繳費日', 'number', '日', '每月租金繳費日期（1-31）', '5', '例如：5', true, 1),
('payment', 'grace_period', '寬限期', 'number', '天', '繳費日後的寬限期天數', '3', '例如：3', false, 2),
('payment', 'late_fee', '逾期費用', 'number', '元', '超過寬限期後的逾期手續費', '300', '例如：300', false, 3),
('payment', 'late_fee_type', '逾期費用類型', 'string', '', '固定金額或百分比', 'fixed', 'fixed 或 percentage', false, 4),
('payment', 'payment_methods', '繳費方式', 'text', '', '可用的繳費方式（多行）', '轉帳\n超商繳費\n信用卡', '每行一種方式', false, 5),
('payment', 'bank_account', '銀行帳號', 'string', '', '租金匯款帳號', '', '例如：012-3456-7890', false, 6),
('payment', 'bank_name', '銀行名稱', 'string', '', '匯款銀行名稱', '', '例如：台灣銀行', false, 7);

-- 合約設定 (contract)
INSERT INTO system_param_definitions (category, param_key, display_name, data_type, unit, description, default_value, placeholder, is_required, display_order) VALUES
('contract', 'contract_duration', '合約期限', 'number', '月', '標準合約期限（月數）', '12', '例如：12', false, 1),
('contract', 'renewal_notice_days', '續約通知期', 'number', '天', '合約到期前通知天數', '30', '例如：30', false, 2),
('contract', 'deposit_months', '押金月數', 'number', '個月', '押金為租金的幾個月', '2', '例如：2', false, 3),
('contract', 'early_termination_fee', '提前解約費', 'number', '元', '提前解約的違約金', '5000', '例如：5000', false, 4),
('contract', 'contract_template_id', '合約範本 ID', 'string', '', '使用的合約範本編號', '2B3', '例如：2B3', false, 5);

-- 服務設定 (service)
INSERT INTO system_param_definitions (category, param_key, display_name, data_type, unit, description, default_value, placeholder, is_required, display_order) VALUES
('service', 'service_hotline', '客服專線', 'string', '', '客服電話號碼', '', '例如：0800-123-456', true, 1),
('service', 'service_hours', '服務時間', 'string', '', '客服服務時間', '週一至週五 09:00-18:00', '例如：週一至週五 09:00-18:00', false, 2),
('service', 'emergency_hotline', '緊急專線', 'string', '', '24小時緊急聯絡電話', '', '例如：0912-345-678', false, 3),
('service', 'service_email', '服務信箱', 'string', '', '客服電子郵件', '', '例如：service@example.com', false, 4),
('service', 'repair_response_time', '報修回應時間', 'number', '小時', '報修後的預期回應時間', '24', '例如：24', false, 5),
('service', 'inspection_frequency', '巡檢頻率', 'number', '月', '定期巡檢的頻率（月）', '3', '例如：3', false, 6);

-- 聯絡資訊 (contact)
INSERT INTO system_param_definitions (category, param_key, display_name, data_type, unit, description, default_value, placeholder, is_required, display_order) VALUES
('contact', 'company_name', '公司名稱', 'string', '', '業者公司全名', '', '例如：XX租賃管理有限公司', true, 1),
('contact', 'company_address', '公司地址', 'text', '', '公司營業地址', '', '例如：台北市信義區信義路五段7號', false, 2),
('contact', 'company_phone', '公司電話', 'string', '', '公司總機電話', '', '例如：02-1234-5678', false, 3),
('contact', 'business_hours', '營業時間', 'string', '', '公司營業時間', '週一至週五 09:00-18:00', '例如：週一至週五 09:00-18:00', false, 4),
('contact', 'website_url', '官方網站', 'string', '', '公司官方網站網址', '', '例如：https://example.com', false, 5),
('contact', 'line_id', 'LINE ID', 'string', '', 'LINE 官方帳號', '', '例如：@example', false, 6);

-- 驗證遷移
DO $$
DECLARE
    param_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO param_count FROM system_param_definitions;
    IF param_count < 20 THEN
        RAISE EXCEPTION '❌ 遷移失敗: 系統參數定義數量不足（需要至少 20 個）';
    END IF;

    RAISE NOTICE '✅ 遷移成功: 已建立 % 個系統參數定義', param_count;
END $$;

COMMIT;

-- 顯示遷移後的統計
SELECT
    '✅ 遷移完成' AS status,
    category,
    COUNT(*) as param_count
FROM system_param_definitions
WHERE is_active = true
GROUP BY category
ORDER BY category;
