-- =====================================================
-- 電費寄送區間查詢系統 - 業者 2 (信義包租代管) 配置
-- =====================================================
--
-- 此腳本為業者 2 建立：
-- 1. 表單配置 (billing_address_form)
-- 2. 知識庫項目
--
-- 注意: API 端點 (lookup_billing_interval) 是所有業者共用的
-- =====================================================

-- =====================================================
-- 1. 表單配置 (業者 2 專用)
-- =====================================================

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
    2,  -- vendor_id = 2 (信義包租代管)
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
-- 2. 知識庫項目 (業者 2 專用)
-- =====================================================

INSERT INTO knowledge_base (
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
    '查詢電費帳單寄送區間（單月/雙月）',
    E'📬 **電費寄送區間查詢服務**\n\n我可以協助您查詢物件的電費寄送區間（單月或雙月）。\n\n查詢方式：\n1. 提供完整的物件地址\n2. 系統會自動查詢該地址的電費寄送區間\n3. 立即告知您帳單寄送時間\n\n',
    'auto',
    'billing_address_form_v2',
    NULL,
    ARRAY['電費', '寄送', '區間', '單月', '雙月', '帳單'],
    ARRAY['tenant', 'customer', 'landlord', 'property_manager'],
    'form_fill',
    2,  -- vendor_id = 2 (信義包租代管)
    ARRAY['電費', '寄送區間', '單月', '雙月', '繳費時間', '帳單'],
    100,
    TRUE
);

-- =====================================================
-- 驗證資料
-- =====================================================

-- 檢查表單配置
SELECT
    form_id,
    form_name,
    vendor_id,
    skip_review,
    is_active
FROM form_schemas
WHERE form_id = 'billing_address_form_v2' AND vendor_id = 2;

-- 檢查知識庫項目
SELECT
    id,
    question_summary,
    trigger_mode,
    form_id,
    vendor_id,
    action_type
FROM knowledge_base
WHERE question_summary = '查詢電費帳單寄送區間（單月/雙月）' AND vendor_id = 2;

-- =====================================================
-- 使用說明
-- =====================================================
--
-- 1. 執行此腳本建立業者 2 的配置：
--    docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < database/seeds/billing_interval_system_vendor2.sql
--
-- 2. 匯入業者 2 的電費寄送區間資料：
--    python3 scripts/data_import/import_billing_intervals.py \
--      --file data/全案場電錶.xlsx \
--      --vendor-id 2
--
-- 3. 驗證資料匯入：
--    docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
--      SELECT lookup_value, COUNT(*)
--      FROM lookup_tables
--      WHERE category = 'billing_interval' AND vendor_id = 2
--      GROUP BY lookup_value;
--    "
--
-- =====================================================
