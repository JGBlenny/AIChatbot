-- =====================================================
-- 電費寄送區間查詢表單
-- =====================================================
-- 創建日期: 2026-02-04
-- 用途: 創建地址收集表單，用於查詢電費寄送區間
-- 流程: 表單 → Lookup API → 返回結果
-- =====================================================

-- 插入表單配置
INSERT INTO form_schemas (
    form_id,
    form_name,
    description,
    default_intro,
    fields,
    vendor_id,
    is_active,
    on_complete_action,
    api_config,
    created_at,
    updated_at
) VALUES (
    'billing_address_form',
    '電費寄送區間查詢',
    '收集用戶地址以查詢電費寄送區間（單月/雙月）',
    '好的！我來協助您查詢電費寄送區間。請提供以下資訊：',
    '[
        {
            "field_name": "address",
            "field_type": "text",
            "field_label": "物件地址",
            "prompt": "請提供完整的物件地址（例如：新北市板橋區忠孝路48巷4弄8號二樓）",
            "required": true,
            "validation_type": "free_text"
        }
    ]'::jsonb,
    1,
    true,
    'call_api',
    '{
        "endpoint": "lookup_billing_interval",
        "params_from_form": {
            "address": "address"
        }
    }'::jsonb,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (form_id) DO UPDATE SET
    form_name = EXCLUDED.form_name,
    description = EXCLUDED.description,
    default_intro = EXCLUDED.default_intro,
    fields = EXCLUDED.fields,
    on_complete_action = EXCLUDED.on_complete_action,
    api_config = EXCLUDED.api_config,
    updated_at = CURRENT_TIMESTAMP;

-- 驗證配置
DO $$
DECLARE
    form_config RECORD;
BEGIN
    -- 檢查表單配置
    SELECT * INTO form_config
    FROM form_schemas
    WHERE form_id = 'billing_address_form';

    RAISE NOTICE '=================================================';
    RAISE NOTICE '✅ 電費寄送區間查詢表單創建完成';
    RAISE NOTICE '=================================================';

    IF form_config.form_id IS NOT NULL THEN
        RAISE NOTICE '📋 表單 ID: %', form_config.form_id;
        RAISE NOTICE '📋 表單名稱: %', form_config.form_name;
        RAISE NOTICE '📋 業者 ID: %', form_config.vendor_id;
        RAISE NOTICE '📋 完成動作: %', form_config.on_complete_action;
        RAISE NOTICE '📋 API Endpoint: %', form_config.api_config->>'endpoint';
        RAISE NOTICE '📋 狀態: %', CASE WHEN form_config.is_active THEN '✅ 啟用' ELSE '❌ 停用' END;
    ELSE
        RAISE WARNING '❌ billing_address_form 配置失敗';
    END IF;

    RAISE NOTICE '=================================================';
END $$;
