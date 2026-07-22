-- =====================================================
-- Lookup API Endpoint 配置
-- =====================================================
-- 創建日期: 2026-02-04
-- 用途: 配置 Lookup API 的 endpoint 記錄
-- 說明: 使用 dynamic 實現類型，通過 UniversalAPICallHandler 調用
-- =====================================================

-- 插入 Lookup API endpoint 配置
INSERT INTO api_endpoints (
    endpoint_id,
    endpoint_name,
    implementation_type,
    api_url,
    http_method,
    request_headers,
    param_mappings,
    response_format_type,
    response_template,
    request_timeout,
    is_active,
    created_at,
    updated_at
) VALUES (
    'lookup_billing_interval',
    '電費寄送區間查詢',
    'dynamic',
    'http://localhost:8100/api/lookup',
    'GET',
    '{
        "Content-Type": "application/json",
        "Accept": "application/json"
    }'::jsonb,
    '[
        {
            "param_name": "category",
            "source": "static",
            "static_value": "billing_interval",
            "required": true,
            "description": "查詢類別固定為 billing_interval"
        },
        {
            "param_name": "key",
            "source": "form",
            "source_key": "address",
            "required": true,
            "description": "從表單獲取用戶輸入的地址"
        },
        {
            "param_name": "vendor_id",
            "source": "session",
            "source_key": "vendor_id",
            "required": true,
            "description": "從 session 獲取業者 ID"
        },
        {
            "param_name": "fuzzy",
            "source": "static",
            "static_value": "true",
            "required": false,
            "description": "啟用模糊匹配"
        },
        {
            "param_name": "threshold",
            "source": "static",
            "static_value": "0.6",
            "required": false,
            "description": "模糊匹配閾值"
        }
    ]'::jsonb,
    'template',
    '✅ 查詢成功

📬 **寄送區間**: {value}
💡 您的電費帳單將於每【{value}】寄送。

{metadata.note}',
    30,
    true,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (endpoint_id) DO UPDATE SET
    endpoint_name = EXCLUDED.endpoint_name,
    implementation_type = EXCLUDED.implementation_type,
    api_url = EXCLUDED.api_url,
    http_method = EXCLUDED.http_method,
    request_headers = EXCLUDED.request_headers,
    param_mappings = EXCLUDED.param_mappings,
    response_format_type = EXCLUDED.response_format_type,
    response_template = EXCLUDED.response_template,
    request_timeout = EXCLUDED.request_timeout,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

-- 插入通用 Lookup API endpoint（用於其他類別）
INSERT INTO api_endpoints (
    endpoint_id,
    endpoint_name,
    implementation_type,
    api_url,
    http_method,
    request_headers,
    param_mappings,
    response_format_type,
    response_template,
    request_timeout,
    is_active
) VALUES (
    'lookup_generic',
    '通用 Lookup 查詢',
    'dynamic',
    'http://localhost:8100/api/lookup',
    'GET',
    '{
        "Content-Type": "application/json"
    }'::jsonb,
    '[
        {
            "param_name": "category",
            "source": "form",
            "source_key": "category",
            "required": true
        },
        {
            "param_name": "key",
            "source": "form",
            "source_key": "query_key",
            "required": true
        },
        {
            "param_name": "vendor_id",
            "source": "session",
            "source_key": "vendor_id",
            "required": true
        }
    ]'::jsonb,
    'template',
    '✅ 查詢結果: {value}',
    30,
    true
)
ON CONFLICT (endpoint_id) DO UPDATE SET
    endpoint_name = EXCLUDED.endpoint_name,
    api_url = EXCLUDED.api_url,
    param_mappings = EXCLUDED.param_mappings,
    updated_at = CURRENT_TIMESTAMP;

-- 驗證配置
DO $$
DECLARE
    billing_config RECORD;
    generic_config RECORD;
BEGIN
    -- 檢查電費查詢配置
    SELECT * INTO billing_config
    FROM api_endpoints
    WHERE endpoint_id = 'lookup_billing_interval';

    -- 檢查通用查詢配置
    SELECT * INTO generic_config
    FROM api_endpoints
    WHERE endpoint_id = 'lookup_generic';

    RAISE NOTICE '=================================================';
    RAISE NOTICE '✅ API Endpoints 配置完成';
    RAISE NOTICE '=================================================';

    IF billing_config.endpoint_id IS NOT NULL THEN
        RAISE NOTICE '📌 [%] - %', billing_config.endpoint_id, billing_config.endpoint_name;
        RAISE NOTICE '   類型: %', billing_config.implementation_type;
        RAISE NOTICE '   URL: %', billing_config.api_url;
        RAISE NOTICE '   方法: %', billing_config.http_method;
        RAISE NOTICE '   狀態: %', CASE WHEN billing_config.is_active THEN '✅ 啟用' ELSE '❌ 停用' END;
    ELSE
        RAISE WARNING '❌ lookup_billing_interval 配置失敗';
    END IF;

    RAISE NOTICE '';

    IF generic_config.endpoint_id IS NOT NULL THEN
        RAISE NOTICE '📌 [%] - %', generic_config.endpoint_id, generic_config.endpoint_name;
        RAISE NOTICE '   類型: %', generic_config.implementation_type;
        RAISE NOTICE '   狀態: %', CASE WHEN generic_config.is_active THEN '✅ 啟用' ELSE '❌ 停用' END;
    ELSE
        RAISE WARNING '❌ lookup_generic 配置失敗';
    END IF;

    RAISE NOTICE '=================================================';
END $$;
