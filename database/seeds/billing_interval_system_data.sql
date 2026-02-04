-- =====================================================
-- 電費寄送區間查詢系統 - 完整資料建立腳本
-- =====================================================
--
-- 此腳本包含：
-- 1. 知識庫項目 (ID: 1296)
-- 2. 表單配置 (billing_address_form)
-- 3. API 端點配置 (lookup_billing_interval)
--
-- 建立日期: 2026-02-04
-- 用途: 快速部署電費寄送區間查詢功能
-- =====================================================

-- =====================================================
-- 1. API 端點配置
-- =====================================================
-- 說明: 定義 Lookup API 端點，用於查詢電費寄送區間

INSERT INTO api_endpoints (
    endpoint_id,
    endpoint_name,
    endpoint_icon,
    description,
    available_in_knowledge,
    available_in_form,
    default_params,
    is_active,
    display_order,
    vendor_id,
    implementation_type,
    api_url,
    http_method,
    request_headers,
    request_body_template,
    request_timeout,
    param_mappings,
    response_format_type,
    response_template,
    custom_handler_name,
    retry_times,
    cache_ttl
) VALUES (
    'lookup_billing_interval',
    '電費寄送區間查詢',
    '🔌',
    '查詢物件地址的電費寄送區間（單月/雙月）',
    TRUE,
    TRUE,
    '[]'::JSONB,
    TRUE,
    0,
    NULL,  -- 所有業者通用
    'dynamic',
    'http://localhost:8100/api/lookup',
    'GET',
    '{"Accept": "application/json", "Content-Type": "application/json"}'::JSONB,
    NULL,
    30,
    -- 參數映射配置
    '[
        {
            "source": "static",
            "required": true,
            "param_name": "category",
            "description": "查詢類別固定為 billing_interval",
            "static_value": "billing_interval"
        },
        {
            "source": "form",
            "required": true,
            "param_name": "key",
            "source_key": "address",
            "description": "從表單獲取用戶輸入的地址"
        },
        {
            "source": "session",
            "required": true,
            "param_name": "vendor_id",
            "source_key": "vendor_id",
            "description": "從 session 獲取業者 ID"
        },
        {
            "source": "static",
            "required": false,
            "param_name": "fuzzy",
            "description": "啟用模糊匹配",
            "static_value": "true"
        },
        {
            "source": "static",
            "required": false,
            "param_name": "threshold",
            "description": "模糊匹配閾值",
            "static_value": "0.75"
        }
    ]'::JSONB,
    'template',
    E'✅ 查詢成功\n\n{fuzzy_warning}\n\n📬 **寄送區間**: {value}\n💡 {note}',
    NULL,
    0,
    0
)
ON CONFLICT (endpoint_id) DO UPDATE SET
    endpoint_name = EXCLUDED.endpoint_name,
    endpoint_icon = EXCLUDED.endpoint_icon,
    description = EXCLUDED.description,
    available_in_knowledge = EXCLUDED.available_in_knowledge,
    available_in_form = EXCLUDED.available_in_form,
    is_active = EXCLUDED.is_active,
    api_url = EXCLUDED.api_url,
    http_method = EXCLUDED.http_method,
    request_headers = EXCLUDED.request_headers,
    param_mappings = EXCLUDED.param_mappings,
    response_format_type = EXCLUDED.response_format_type,
    response_template = EXCLUDED.response_template,
    updated_at = NOW();

-- =====================================================
-- 2. 表單配置
-- =====================================================
-- 說明: 定義電費地址查詢表單，用於收集用戶地址

INSERT INTO form_schemas (
    form_id,
    form_name,
    trigger_intents,
    fields,
    vendor_id,
    is_active,
    description,
    default_intro,
    on_complete_action,
    api_config,
    skip_review
) VALUES (
    'billing_address_form',
    '電費寄送區間查詢',
    NULL,  -- 由知識庫觸發，不需要設定觸發意圖
    -- 表單欄位配置
    '[
        {
            "prompt": "請提供完整的物件地址（例如：新北市板橋區忠孝路48巷4弄8號二樓）",
            "required": true,
            "field_name": "address",
            "field_type": "text",
            "field_label": "物件地址",
            "validation_type": "free_text"
        }
    ]'::JSONB,
    1,  -- vendor_id = 1 (建鉅不動產)
    TRUE,
    '收集用戶地址以查詢電費寄送區間（單月/雙月）',
    '好的！我來協助您查詢電費寄送區間。請提供以下資訊：',
    'call_api',  -- 表單完成後調用 API
    -- API 調用配置
    '{
        "endpoint": "lookup_billing_interval",
        "params_from_form": {
            "address": "address"
        }
    }'::JSONB,
    TRUE  -- 跳過審核，自動提交
)
ON CONFLICT (form_id, vendor_id) DO UPDATE SET
    form_name = EXCLUDED.form_name,
    fields = EXCLUDED.fields,
    is_active = EXCLUDED.is_active,
    description = EXCLUDED.description,
    default_intro = EXCLUDED.default_intro,
    on_complete_action = EXCLUDED.on_complete_action,
    api_config = EXCLUDED.api_config,
    skip_review = EXCLUDED.skip_review,
    updated_at = NOW();

-- =====================================================
-- 3. 知識庫項目
-- =====================================================
-- 說明: 定義電費寄送區間查詢的知識庫項目，自動觸發表單

INSERT INTO knowledge_base (
    id,
    question_summary,
    answer,
    trigger_mode,
    form_id,
    immediate_prompt,
    trigger_keywords,
    target_user,
    action_type,
    vendor_id,
    keywords,
    priority,
    is_active
) VALUES (
    1296,
    '查詢電費帳單寄送區間（單月/雙月）',
    E'📬 **電費寄送區間查詢服務**\n\n我可以協助您查詢物件的電費寄送區間（單月或雙月）。\n\n查詢方式：\n1. 提供完整的物件地址\n2. 系統會自動查詢該地址的電費寄送區間\n3. 立即告知您帳單寄送時間\n\n',
    'auto',  -- 自動觸發模式：匹配到關鍵詞時自動觸發表單
    'billing_address_form',
    NULL,  -- auto 模式不需要確認提示
    ARRAY['電費', '寄送', '區間', '單月', '雙月', '帳單'],  -- 觸發關鍵詞
    ARRAY['tenant', 'customer', 'landlord', 'property_manager'],  -- 適用角色
    'form_fill',  -- 行動類型：觸發表單填寫
    1,  -- vendor_id = 1 (建鉅不動產)
    ARRAY['電費', '寄送區間', '單月', '雙月', '繳費時間', '帳單'],  -- 檢索關鍵詞
    100,  -- 高優先級
    TRUE
)
ON CONFLICT (id) DO UPDATE SET
    question_summary = EXCLUDED.question_summary,
    answer = EXCLUDED.answer,
    trigger_mode = EXCLUDED.trigger_mode,
    form_id = EXCLUDED.form_id,
    immediate_prompt = EXCLUDED.immediate_prompt,
    trigger_keywords = EXCLUDED.trigger_keywords,
    target_user = EXCLUDED.target_user,
    action_type = EXCLUDED.action_type,
    keywords = EXCLUDED.keywords,
    priority = EXCLUDED.priority,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- =====================================================
-- 驗證資料
-- =====================================================

-- 檢查 API 端點
SELECT
    endpoint_id,
    endpoint_name,
    is_active,
    implementation_type
FROM api_endpoints
WHERE endpoint_id = 'lookup_billing_interval';

-- 檢查表單配置
SELECT
    form_id,
    form_name,
    skip_review,
    is_active,
    on_complete_action
FROM form_schemas
WHERE form_id = 'billing_address_form';

-- 檢查知識庫項目
SELECT
    id,
    question_summary,
    trigger_mode,
    form_id,
    action_type,
    priority
FROM knowledge_base
WHERE id = 1296;

-- =====================================================
-- 使用說明
-- =====================================================
--
-- 1. 執行此腳本：
--    psql -U aichatbot -d aichatbot_admin -f billing_interval_system_data.sql
--
-- 2. 或在 Docker 環境中：
--    docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < billing_interval_system_data.sql
--
-- 3. 測試流程：
--    用戶輸入: "我想查詢電費寄送區間"
--    系統行為:
--    - 知識庫匹配 (ID: 1296)
--    - 自動觸發表單 (billing_address_form)
--    - 詢問地址
--    - 用戶提供地址後自動調用 API (lookup_billing_interval)
--    - 返回查詢結果
--
-- 4. 相關文檔：
--    - docs/LOOKUP_SYSTEM_REFERENCE.md
--    - docs/deployment/DEPLOYMENT_2026-02-04.md
--
-- =====================================================
