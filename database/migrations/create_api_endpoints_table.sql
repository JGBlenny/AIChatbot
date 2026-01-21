-- 創建 API Endpoints 管理表
-- 日期: 2026-01-18
-- 用途: 動態管理系統可用的 API endpoints，替代硬編碼方式

CREATE TABLE IF NOT EXISTS api_endpoints (
    id SERIAL PRIMARY KEY,
    endpoint_id VARCHAR(100) UNIQUE NOT NULL,  -- API 識別碼 (例如: billing_inquiry)
    endpoint_name VARCHAR(200) NOT NULL,        -- 顯示名稱 (例如: 帳單查詢)
    endpoint_icon VARCHAR(10) DEFAULT '🔌',     -- Emoji 圖示
    description TEXT,                           -- API 描述
    handler_function VARCHAR(200),              -- 後端處理函數名稱 (例如: handle_billing_inquiry)

    -- 可用範圍
    available_in_knowledge BOOLEAN DEFAULT TRUE,  -- 是否在知識庫管理中可用
    available_in_form BOOLEAN DEFAULT TRUE,       -- 是否在表單管理中可用

    -- 參數定義 (JSONB 格式)
    -- 例如: [{"name": "user_id", "type": "string", "required": true, "source": "session"}]
    default_params JSONB DEFAULT '[]',

    -- 狀態
    is_active BOOLEAN DEFAULT TRUE,
    display_order INTEGER DEFAULT 0,  -- 顯示順序

    -- 業者限制
    vendor_id INTEGER REFERENCES vendors(id) ON DELETE SET NULL,  -- NULL 表示全局可用

    -- 時間戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 創建索引
CREATE INDEX idx_api_endpoints_endpoint_id ON api_endpoints(endpoint_id);
CREATE INDEX idx_api_endpoints_is_active ON api_endpoints(is_active);
CREATE INDEX idx_api_endpoints_vendor_id ON api_endpoints(vendor_id);
CREATE INDEX idx_api_endpoints_display_order ON api_endpoints(display_order);

-- 插入現有的 API endpoints 作為初始數據
INSERT INTO api_endpoints (endpoint_id, endpoint_name, endpoint_icon, description, handler_function, available_in_knowledge, available_in_form, display_order) VALUES
('billing_inquiry', '帳單查詢', '📋', '查詢租客的帳單資訊', 'handle_billing_inquiry', TRUE, TRUE, 1),
('verify_tenant_identity', '租客身份驗證', '🔐', '驗證租客身份', 'handle_verify_tenant_identity', TRUE, FALSE, 2),
('resend_invoice', '重新發送帳單', '📧', '重新發送帳單給租客', 'handle_resend_invoice', TRUE, FALSE, 3),
('maintenance_request', '報修申請', '🔧', '提交報修申請', 'handle_maintenance_request', TRUE, TRUE, 4),
('rent_history', '查詢租金紀錄', '💰', '查詢歷史租金繳納紀錄', 'handle_rent_history', TRUE, TRUE, 5)
ON CONFLICT (endpoint_id) DO NOTHING;

-- 創建更新時間觸發器
CREATE OR REPLACE FUNCTION update_api_endpoints_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_api_endpoints_updated_at
    BEFORE UPDATE ON api_endpoints
    FOR EACH ROW
    EXECUTE FUNCTION update_api_endpoints_updated_at();

-- 添加註釋
COMMENT ON TABLE api_endpoints IS 'API endpoints 管理表，用於動態配置系統可用的 API';
COMMENT ON COLUMN api_endpoints.endpoint_id IS 'API 唯一識別碼，用於程式中引用';
COMMENT ON COLUMN api_endpoints.endpoint_name IS '顯示給用戶看的名稱';
COMMENT ON COLUMN api_endpoints.endpoint_icon IS 'Emoji 圖示，用於前端顯示';
COMMENT ON COLUMN api_endpoints.handler_function IS '後端處理函數名稱，必須在 api_call_handler.py 中實作';
COMMENT ON COLUMN api_endpoints.available_in_knowledge IS '是否在知識庫管理的 action_type 中可選';
COMMENT ON COLUMN api_endpoints.available_in_form IS '是否在表單管理的 on_complete_action 中可選';
COMMENT ON COLUMN api_endpoints.default_params IS '預設參數定義，JSON 格式';
COMMENT ON COLUMN api_endpoints.display_order IS '顯示順序，數字越小越靠前';
