-- =====================================================
-- 業者 2 (信義包租代管) - 完整資料匯入
-- =====================================================
--
-- 此腳本包含業者 2 所需的所有配置：
-- 1. 表單配置 (billing_address_form_v2)
-- 2. 知識庫項目 (ID: 1297)
-- 3. Lookup Tables 資料（從業者 1 複製）
-- 4. Embedding（從業者 1 複製）
--
-- 前提條件: 業者 1 的資料已存在
-- 執行時間: ~5 秒
-- =====================================================

BEGIN;

-- =====================================================
-- 1. 表單配置 (業者 2)
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
    vendor_id = EXCLUDED.vendor_id,
    is_active = EXCLUDED.is_active,
    description = EXCLUDED.description,
    default_intro = EXCLUDED.default_intro,
    on_complete_action = EXCLUDED.on_complete_action,
    api_config = EXCLUDED.api_config,
    skip_review = EXCLUDED.skip_review,
    updated_at = NOW();

-- =====================================================
-- 2. 知識庫項目 (業者 2)
-- =====================================================

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
    2,  -- vendor_id = 2 (信義包租代管)
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
    vendor_id = EXCLUDED.vendor_id,
    keywords = EXCLUDED.keywords,
    priority = EXCLUDED.priority,
    is_active = EXCLUDED.is_active,
    scope = EXCLUDED.scope,
    business_types = EXCLUDED.business_types,
    updated_at = NOW();

-- =====================================================
-- 3. 複製 Lookup Tables 資料（從業者 1）
-- =====================================================

-- 先檢查業者 2 是否已有資料
DO $$
DECLARE
    v2_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v2_count
    FROM lookup_tables
    WHERE vendor_id = 2 AND category = 'billing_interval';

    IF v2_count > 0 THEN
        RAISE NOTICE '業者 2 已有 % 筆資料，跳過複製', v2_count;
    ELSE
        -- 從業者 1 複製資料
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

        GET DIAGNOSTICS v2_count = ROW_COUNT;
        RAISE NOTICE '已從業者 1 複製 % 筆資料給業者 2', v2_count;
    END IF;
END $$;

-- =====================================================
-- 4. 複製 Embedding（從業者 1）
-- =====================================================

UPDATE knowledge_base
SET embedding = (
    SELECT embedding
    FROM knowledge_base
    WHERE id = 1296
)
WHERE id = 1297 AND embedding IS NULL;

COMMIT;

-- =====================================================
-- 驗證結果
-- =====================================================

\echo ''
\echo '===== 驗證結果 ====='
\echo ''

-- 檢查表單配置
\echo '1. 表單配置:'
SELECT
    form_id,
    form_name,
    vendor_id,
    skip_review,
    is_active
FROM form_schemas
WHERE form_id = 'billing_address_form_v2';

\echo ''
\echo '2. 知識庫項目:'
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
WHERE id = 1297;

\echo ''
\echo '3. Lookup Tables 資料統計:'
SELECT
    vendor_id,
    COUNT(*) as 總筆數,
    COUNT(CASE WHEN lookup_value = '單月' THEN 1 END) as 單月,
    COUNT(CASE WHEN lookup_value = '雙月' THEN 1 END) as 雙月,
    COUNT(CASE WHEN lookup_value = '自繳' THEN 1 END) as 自繳
FROM lookup_tables
WHERE category = 'billing_interval' AND vendor_id = 2
GROUP BY vendor_id;

\echo ''
\echo '===== 完成！ ====='
\echo ''
\echo '業者 2 (信義包租代管) 的配置已完成'
\echo '請執行以下命令重啟服務:'
\echo '  docker-compose restart rag-orchestrator'
\echo ''

-- =====================================================
-- 使用說明
-- =====================================================
--
-- 執行此腳本:
--   docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
--     database/seeds/import_vendor2_only.sql
--
-- 預期結果:
--   - 表單: billing_address_form_v2 (1 筆)
--   - 知識庫: ID 1297 (1 筆)
--   - Lookup Tables: 247 筆（單月 29、雙月 191、自繳 27）
--   - Embedding: 已從業者 1 複製
--
-- 測試:
--   curl -X POST http://localhost:8100/api/v1/message \
--     -H "Content-Type: application/json" \
--     -d '{
--       "message": "我想查詢電費寄送區間",
--       "vendor_id": 2,
--       "user_role": "customer",
--       "user_id": "test_user",
--       "session_id": "test_session"
--     }'
--
-- =====================================================
