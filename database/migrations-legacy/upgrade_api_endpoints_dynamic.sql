-- 升級 api_endpoints 表以支持動態配置
-- 日期: 2026-01-18
-- 目的: 從「每個 API 寫函數」改為「通用調用器 + 配置」

-- 新增欄位
ALTER TABLE api_endpoints
ADD COLUMN IF NOT EXISTS implementation_type VARCHAR(20) DEFAULT 'dynamic',
ADD COLUMN IF NOT EXISTS api_url TEXT,
ADD COLUMN IF NOT EXISTS http_method VARCHAR(10) DEFAULT 'GET',
ADD COLUMN IF NOT EXISTS request_headers JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS request_body_template JSONB,
ADD COLUMN IF NOT EXISTS request_timeout INTEGER DEFAULT 30,
ADD COLUMN IF NOT EXISTS param_mappings JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS response_format_type VARCHAR(50) DEFAULT 'template',
ADD COLUMN IF NOT EXISTS response_template TEXT,
ADD COLUMN IF NOT EXISTS custom_handler_name VARCHAR(100),
ADD COLUMN IF NOT EXISTS retry_times INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS cache_ttl INTEGER DEFAULT 0;

-- 添加註釋
COMMENT ON COLUMN api_endpoints.implementation_type IS '實作類型: dynamic(動態調用) 或 custom(自定義處理)';
COMMENT ON COLUMN api_endpoints.api_url IS '實際的 API URL，支持變量替換 {session.xxx}, {form.xxx}';
COMMENT ON COLUMN api_endpoints.http_method IS 'HTTP 方法: GET, POST, PUT, DELETE';
COMMENT ON COLUMN api_endpoints.request_headers IS '請求頭，JSON 格式，支持變量替換';
COMMENT ON COLUMN api_endpoints.request_body_template IS '請求體模板，用於 POST/PUT';
COMMENT ON COLUMN api_endpoints.request_timeout IS 'API 調用超時時間（秒）';
COMMENT ON COLUMN api_endpoints.param_mappings IS '參數映射配置，定義如何從 session/form/input 獲取參數';
COMMENT ON COLUMN api_endpoints.response_format_type IS '響應格式化類型: template, custom, raw';
COMMENT ON COLUMN api_endpoints.response_template IS '響應格式化模板';
COMMENT ON COLUMN api_endpoints.custom_handler_name IS '自定義處理器函數名（僅當 implementation_type=custom 時）';
COMMENT ON COLUMN api_endpoints.retry_times IS '失敗重試次數';
COMMENT ON COLUMN api_endpoints.cache_ttl IS '緩存時間（秒），0 表示不緩存';

-- 更新現有數據：將現有的 API 標記為 custom（需要手動遷移）
UPDATE api_endpoints SET
    implementation_type = 'custom',
    custom_handler_name = CASE endpoint_id
        WHEN 'billing_inquiry' THEN 'handle_billing_inquiry'
        WHEN 'verify_tenant_identity' THEN 'handle_verify_tenant_identity'
        WHEN 'resend_invoice' THEN 'handle_resend_invoice'
        WHEN 'maintenance_request' THEN 'handle_maintenance_request'
        ELSE NULL
    END
WHERE endpoint_id IN ('billing_inquiry', 'verify_tenant_identity', 'resend_invoice', 'maintenance_request');

-- 刪除 rent_history（還沒實作，避免誤用）
DELETE FROM api_endpoints WHERE endpoint_id = 'rent_history';

-- 插入一個示例動態 API（用於測試）
INSERT INTO api_endpoints (
    endpoint_id,
    endpoint_name,
    endpoint_icon,
    description,
    implementation_type,
    api_url,
    http_method,
    request_headers,
    param_mappings,
    response_format_type,
    response_template,
    available_in_knowledge,
    available_in_form,
    is_active,
    display_order
) VALUES (
    'example_user_info',
    '用戶資訊查詢（示例）',
    '👤',
    '示例：動態調用外部 API 獲取用戶資訊',
    'dynamic',
    'https://jsonplaceholder.typicode.com/users/{user_id}',
    'GET',
    '{"Content-Type": "application/json"}',
    '[
        {
            "param_name": "user_id",
            "source": "session",
            "source_key": "user_id",
            "required": true,
            "default": "1"
        }
    ]',
    'template',
    '📋 用戶資訊\n姓名: {name}\nEmail: {email}\n電話: {phone}\n公司: {company.name}',
    true,
    false,
    false,
    999
) ON CONFLICT (endpoint_id) DO NOTHING;

-- 創建索引
CREATE INDEX IF NOT EXISTS idx_api_endpoints_implementation_type ON api_endpoints(implementation_type);

COMMENT ON TABLE api_endpoints IS 'API endpoints 配置表（升級版）：支持動態配置 + 自定義處理';
