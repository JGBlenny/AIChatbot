-- =====================================================
-- JGB 修繕報修表單
-- =====================================================
-- 創建日期: 2026-04-22
-- 用途: 透過 JGB 系統 API 建立修繕單
-- 流程: SOP 觸發 → 物件搜尋(api_search) → 分類/項目/原因(api_select 級聯)
--       → 補充說明(text) → 急迫性(select) → POST 建單
-- =====================================================

INSERT INTO form_schemas (
    form_id,
    form_name,
    description,
    default_intro,
    fields,
    vendor_id,
    is_active,
    skip_review,
    on_complete_action,
    api_config,
    created_at,
    updated_at
) VALUES (
    'jgb_repair_create',
    '修繕報修',
    '透過 JGB 系統建立修繕單',
    '好的，我來幫您建立修繕單。',
    '[
        {
            "field_name": "estate_id",
            "field_label": "物件",
            "field_type": "api_search",
            "prompt": "請輸入物件名稱或地址關鍵字",
            "required": true,
            "api_config": {
                "endpoint": "jgb_estates",
                "search_param": "keyword",
                "display_template": "{title}（{estate_room_number}）",
                "value_field": "id",
                "extra_params": {
                    "role_id": "{session.role_id}"
                }
            }
        },
        {
            "field_name": "category_id",
            "field_label": "修繕分類",
            "field_type": "api_select",
            "prompt": "請選擇修繕分類",
            "required": true,
            "api_config": {
                "endpoint": "jgb_repair_categories",
                "data_path": "data",
                "display_field": "name",
                "value_field": "id"
            }
        },
        {
            "field_name": "item_id",
            "field_label": "修繕項目",
            "field_type": "api_select",
            "prompt": "請選擇修繕項目",
            "required": true,
            "depends_on": "category_id",
            "options_path": "items",
            "display_field": "name",
            "value_field": "id"
        },
        {
            "field_name": "broken_reason",
            "field_label": "損壞原因",
            "field_type": "api_select",
            "prompt": "請選擇損壞原因",
            "required": true,
            "depends_on": "item_id",
            "options_path": "broken_reasons"
        },
        {
            "field_name": "broken_note",
            "field_label": "補充說明",
            "field_type": "text",
            "prompt": "請描述損壞狀況（可輸入「跳過」略過）",
            "required": false,
            "validation_type": "free_text"
        },
        {
            "field_name": "emergency_status",
            "field_label": "急迫性",
            "field_type": "select",
            "prompt": "是否為緊急修繕？\n1. 緊急\n2. 非緊急",
            "required": true,
            "options": [
                {"label": "緊急", "value": 1},
                {"label": "非緊急", "value": 2}
            ]
        }
    ]'::jsonb,
    2,
    true,
    true,
    'call_api',
    '{
        "endpoint": "jgb_create_repair",
        "params_from_form": {
            "role_id": "{session.role_id}",
            "estate_id": "estate_id",
            "category_id": "category_id",
            "item_id": "item_id",
            "broken_reason": "broken_reason",
            "broken_note": "broken_note",
            "emergency_status": "emergency_status"
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
    skip_review = EXCLUDED.skip_review,
    on_complete_action = EXCLUDED.on_complete_action,
    api_config = EXCLUDED.api_config,
    updated_at = CURRENT_TIMESTAMP;

-- 驗證配置
DO $$
DECLARE
    form_config RECORD;
BEGIN
    SELECT * INTO form_config
    FROM form_schemas
    WHERE form_id = 'jgb_repair_create';

    RAISE NOTICE '=================================================';
    RAISE NOTICE '✅ JGB 修繕報修表單創建完成';
    RAISE NOTICE '=================================================';

    IF form_config.form_id IS NOT NULL THEN
        RAISE NOTICE '📋 表單 ID: %', form_config.form_id;
        RAISE NOTICE '📋 表單名稱: %', form_config.form_name;
        RAISE NOTICE '📋 業者 ID: %', form_config.vendor_id;
        RAISE NOTICE '📋 欄位數: %', jsonb_array_length(form_config.fields);
        RAISE NOTICE '📋 完成動作: %', form_config.on_complete_action;
        RAISE NOTICE '📋 跳過審核: %', CASE WHEN form_config.skip_review THEN '是' ELSE '否' END;
        RAISE NOTICE '📋 API Endpoint: %', form_config.api_config->>'endpoint';
    ELSE
        RAISE WARNING '❌ jgb_repair_create 配置失敗';
    END IF;

    RAISE NOTICE '=================================================';
END $$;
