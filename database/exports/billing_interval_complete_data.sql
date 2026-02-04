-- =====================================================
-- 電費寄送區間查詢系統 - 完整資料匯出
-- =====================================================
--
-- 此檔案包含完整的系統配置資料：
-- 1. API 端點配置 (api_endpoints)
-- 2. 表單配置 (form_schemas) - 業者 1 & 2
-- 3. 知識庫項目 (knowledge_base) - 業者 1 & 2
-- 4. Lookup Tables 資料 (lookup_tables) - 業者 1 & 2
--
-- 匯出日期: 2026-02-04
-- 用途: 生產環境部署或災難恢復
-- =====================================================

-- =====================================================
-- 1. API 端點配置
-- =====================================================

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
    '查詢物件地址的電費寄送區間（單月/雙月/自繳）',
    TRUE,                                    -- available_in_knowledge
    TRUE,                                    -- available_in_form
    '[]'::JSONB,                            -- default_params
    TRUE,                                    -- is_active
    0,                                       -- display_order
    NULL,                                    -- vendor_id (所有業者共用)
    'dynamic',                               -- implementation_type
    'http://localhost:8100/api/lookup',     -- api_url
    'GET',                                   -- http_method
    '{"Accept": "application/json", "Content-Type": "application/json"}'::JSONB,  -- request_headers
    NULL,                                    -- request_body_template
    30,                                      -- request_timeout
    -- param_mappings: 定義如何從不同來源取得參數
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
    'template',                              -- response_format_type
    -- response_template: 定義回應訊息格式
    E'✅ 查詢成功\n\n{fuzzy_warning}\n\n📬 **寄送區間**: {value}\n💡 {note}',
    NULL,                                    -- custom_handler_name
    0,                                       -- retry_times
    0                                        -- cache_ttl
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

-- 2.1 業者 1 (甲山林包租代管)
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
    NULL,
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
    1,  -- vendor_id
    TRUE,
    '收集用戶地址以查詢電費寄送區間（單月/雙月）',
    '好的！我來協助您查詢電費寄送區間。請提供以下資訊：',
    'call_api',
    '{
        "endpoint": "lookup_billing_interval",
        "params_from_form": {
            "address": "address"
        }
    }'::JSONB,
    TRUE  -- skip_review: 跳過審核，自動提交
)
ON CONFLICT (form_id) DO UPDATE SET
    form_name = EXCLUDED.form_name,
    fields = EXCLUDED.fields,
    is_active = EXCLUDED.is_active,
    description = EXCLUDED.description,
    default_intro = EXCLUDED.default_intro,
    on_complete_action = EXCLUDED.on_complete_action,
    api_config = EXCLUDED.api_config,
    skip_review = EXCLUDED.skip_review,
    updated_at = NOW();

-- 2.2 業者 2 (信義包租代管)
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
    'billing_address_form_v2',
    '電費寄送區間查詢',
    NULL,
    '[
        {
            "prompt": "請提供完整的物件地址（例如：台北市大安區信義路四段1號3樓）",
            "required": true,
            "field_name": "address",
            "field_type": "text",
            "field_label": "物件地址",
            "validation_type": "free_text"
        }
    ]'::JSONB,
    2,  -- vendor_id
    TRUE,
    '收集用戶地址以查詢電費寄送區間（單月/雙月）',
    '好的！我來協助您查詢電費寄送區間。請提供以下資訊：',
    'call_api',
    '{
        "endpoint": "lookup_billing_interval",
        "params_from_form": {
            "address": "address"
        }
    }'::JSONB,
    TRUE
)
ON CONFLICT (form_id) DO UPDATE SET
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

-- 3.1 業者 1 (ID: 1296)
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
    'auto',
    'billing_address_form',
    NULL,
    ARRAY['電費', '寄送', '區間', '單月', '雙月', '帳單'],
    ARRAY['tenant', 'customer', 'landlord', 'property_manager'],
    'form_fill',
    1,  -- vendor_id
    ARRAY['電費', '寄送區間', '單月', '雙月', '繳費時間', '帳單'],
    100,
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

-- 3.2 業者 2 (ID: 1297)
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
    is_active,
    scope,
    business_types
) VALUES (
    1297,
    '查詢電費帳單寄送區間（單月/雙月）',
    E'📬 **電費寄送區間查詢服務**\n\n我可以協助您查詢物件的電費寄送區間（單月或雙月）。\n\n查詢方式：\n1. 提供完整的物件地址\n2. 系統會自動查詢該地址的電費寄送區間\n3. 立即告知您帳單寄送時間\n\n',
    'auto',
    'billing_address_form_v2',
    NULL,
    ARRAY['電費', '寄送', '區間', '單月', '雙月', '帳單'],
    ARRAY['tenant', 'customer', 'landlord', 'property_manager'],
    'form_fill',
    2,  -- vendor_id
    ARRAY['電費', '寄送區間', '單月', '雙月', '繳費時間', '帳單'],
    100,
    TRUE,
    'customized',  -- scope: customized (業者專屬知識)
    ARRAY['property_management', 'full_service']::text[]  -- business_types: 與業者 1 相同
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
    scope = EXCLUDED.scope,
    business_types = EXCLUDED.business_types,
    updated_at = NOW();

-- =====================================================
-- 4. Lookup Tables 資料
-- =====================================================

-- 注意：此處僅包含業者 1 的資料
-- 業者 2 的資料應該從業者 1 複製（見下方說明）

-- 4.1 業者 1 - 從實際資料匯出
-- （247 筆資料，包含單月 29 筆、雙月 191 筆、自繳 27 筆）

-- 由於資料量較大，這裡提供複製指令：
-- 從業者 1 複製資料給業者 2:
/*
INSERT INTO lookup_tables (
    vendor_id,
    category,
    category_name,
    lookup_key,
    lookup_value,
    metadata,
    is_active,
    created_at
)
SELECT
    2 as vendor_id,  -- 改為業者 2
    category,
    category_name,
    lookup_key,
    lookup_value,
    metadata,
    is_active,
    NOW() as created_at
FROM lookup_tables
WHERE category = 'billing_interval'
  AND vendor_id = 1
  AND is_active = TRUE;
*/

-- =====================================================
-- 5. Embedding 複製 (業者 2)
-- =====================================================

-- 業者 2 的知識庫需要複製 embedding
UPDATE knowledge_base
SET embedding = (
    SELECT embedding
    FROM knowledge_base
    WHERE id = 1296
)
WHERE id = 1297 AND embedding IS NULL;

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
    vendor_id,
    skip_review,
    is_active
FROM form_schemas
WHERE form_id IN ('billing_address_form', 'billing_address_form_v2');

-- 檢查知識庫項目
SELECT
    id,
    question_summary,
    trigger_mode,
    form_id,
    vendor_id,
    action_type,
    priority,
    embedding IS NULL as no_embedding
FROM knowledge_base
WHERE id IN (1296, 1297);

-- 檢查 Lookup Tables 資料
SELECT
    vendor_id,
    COUNT(*) as total,
    COUNT(CASE WHEN lookup_value = '單月' THEN 1 END) as 單月,
    COUNT(CASE WHEN lookup_value = '雙月' THEN 1 END) as 雙月,
    COUNT(CASE WHEN lookup_value = '自繳' THEN 1 END) as 自繳
FROM lookup_tables
WHERE category = 'billing_interval'
GROUP BY vendor_id
ORDER BY vendor_id;

-- =====================================================
-- 使用說明
-- =====================================================
--
-- 完整部署步驟:
--
-- 1. 匯入配置資料:
--    docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
--      database/exports/billing_interval_complete_data.sql
--
-- 2. 匯入業者 1 的 Lookup Tables 資料:
--    python3 scripts/data_import/import_billing_intervals.py \
--      --file data/billing_intervals.xlsx \
--      --vendor-id 1
--
-- 3. 複製資料給業者 2:
--    docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
--      INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
--      SELECT 2, category, category_name, lookup_key, lookup_value, metadata, is_active, NOW()
--      FROM lookup_tables
--      WHERE category = 'billing_interval' AND vendor_id = 1 AND is_active = TRUE;
--    "
--
-- 4. 驗證資料:
--    docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin < \
--      database/exports/billing_interval_complete_data.sql | grep "SELECT"
--
-- 5. 重啟服務:
--    docker-compose restart rag-orchestrator
--
-- =====================================================
