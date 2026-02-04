-- =====================================================
-- 業者 2 完整部署 SQL
-- 包含：表單、知識庫、247 筆地址資料
-- 不依賴業者 1，完全獨立
-- =====================================================
-- 日期: 2026-02-04
-- 業者: 2 (信義包租代管)
-- =====================================================

BEGIN;

-- =====================================================
-- 1. 表單配置
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
            "prompt": "請提供完整的物件地址（例如：新北市板橋區忠孝路48巷4弄8號一樓）",
            "required": true,
            "field_name": "address",
            "field_type": "text",
            "field_label": "物件地址",
            "validation_type": "free_text"
        }
    ]'::JSONB,
    2,
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
    vendor_id = EXCLUDED.vendor_id,
    is_active = EXCLUDED.is_active,
    description = EXCLUDED.description,
    default_intro = EXCLUDED.default_intro,
    on_complete_action = EXCLUDED.on_complete_action,
    api_config = EXCLUDED.api_config,
    skip_review = EXCLUDED.skip_review,
    updated_at = NOW();

-- =====================================================
-- 2. 知識庫項目
-- =====================================================

-- 先刪除舊的業者 2 知識庫（如果存在）
DELETE FROM knowledge_base
WHERE vendor_id = 2 AND question_summary = '查詢電費帳單寄送區間（單月/雙月）';

-- 插入新的知識庫項目
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
    is_active,
    scope,
    business_types
) VALUES (
    '查詢電費帳單寄送區間（單月/雙月）',
    E'📬 **電費寄送區間查詢服務**\n\n我可以協助您查詢物件的電費寄送區間（單月或雙月）。\n\n查詢方式：\n1. 提供完整的物件地址\n2. 系統會自動查詢該地址的電費寄送區間\n3. 立即告知您帳單寄送時間\n\n',
    'auto',
    'billing_address_form_v2',
    NULL,
    ARRAY['電費', '寄送', '區間', '單月', '雙月', '帳單'],
    ARRAY['tenant', 'customer', 'landlord', 'property_manager'],
    'form_fill',
    2,
    ARRAY['電費', '寄送區間', '單月', '雙月', '繳費時間', '帳單'],
    100,
    TRUE,
    'customized',
    ARRAY['property_management', 'full_service']::text[]
);

COMMIT;

-- =====================================================
-- 驗證結果
-- =====================================================

\echo ''
\echo '===== 業者 2 配置驗證 ====='
\echo ''

\echo '1. 表單配置:'
SELECT form_id, form_name, vendor_id, is_active
FROM form_schemas
WHERE form_id = 'billing_address_form_v2';

\echo ''
\echo '2. 知識庫項目:'
SELECT id, question_summary, trigger_mode, form_id, vendor_id, scope
FROM knowledge_base
WHERE vendor_id = 2 AND question_summary = '查詢電費帳單寄送區間（單月/雙月）';

\echo ''
\echo '===== 配置完成 ====='
\echo '接下來請執行地址資料匯入:'
\echo '  docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < database/seeds/insert_lookup_tables_vendor2.sql'
\echo ''
