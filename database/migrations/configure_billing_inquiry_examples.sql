-- ==========================================
-- 帳單查詢系統配置範例
-- 版本: 1.0.0
-- 日期: 2026-01-16
-- 說明: 插入帳單查詢相關的知識庫、表單和 API 配置範例
-- 相關文檔: docs/design/KNOWLEDGE_ACTION_SYSTEM_DESIGN.md
-- ==========================================

BEGIN;

-- ==========================================
-- 場景 A: 純知識問答 (direct_answer)
-- 用戶問：「租金怎麼繳」
-- ==========================================

INSERT INTO knowledge_base (
    question_summary,
    answer,
    action_type,
    keywords,
    scope,
    is_active
) VALUES (
    '租金繳納方式說明',
    E'💳 **租金繳納方式**\n\n我們提供以下繳納方式：\n\n1. **線上信用卡繳費**\n   - 登入系統後選擇「繳費」功能\n   - 支援 Visa、Mastercard、JCB\n\n2. **ATM 轉帳**\n   - 銀行代碼：012\n   - 帳號：請見您的帳單\n\n3. **超商代收**\n   - 持帳單條碼至四大超商繳費\n   - 每筆手續費 15 元\n\n📅 **繳費期限**：每月 5 號前\n⏰ **逾期費用**：每日 0.05% 滯納金\n\n如有任何問題，歡迎隨時聯繫客服！',
    'direct_answer',
    ARRAY['租金', '繳費', '繳納', '付款'],
    'global',
    true
)
ON CONFLICT DO NOTHING;

-- ==========================================
-- 場景 B: 表單填寫 (form_fill)
-- 用戶問：「我想租房子」
-- ==========================================

-- 先創建租屋申請表單（如果不存在）
INSERT INTO form_schemas (
    form_id,
    form_name,
    trigger_intents,
    fields,
    on_complete_action,
    vendor_id,
    is_active
) VALUES (
    'rental_inquiry',
    '租屋詢問表',
    '["租屋詢問", "我想租房", "租房申請"]'::jsonb,
    '[
        {
            "field_name": "contact_name",
            "field_label": "聯絡人姓名",
            "field_type": "text",
            "prompt": "請問您的姓名是？",
            "validation_type": "taiwan_name",
            "required": true
        },
        {
            "field_name": "contact_phone",
            "field_label": "聯絡電話",
            "field_type": "text",
            "prompt": "請提供您的聯絡電話",
            "validation_type": "phone",
            "required": true
        },
        {
            "field_name": "preferred_area",
            "field_label": "希望區域",
            "field_type": "text",
            "prompt": "您希望租房的區域是？（例如：台北市大安區）",
            "validation_type": "address",
            "required": true
        },
        {
            "field_name": "budget_range",
            "field_label": "預算範圍",
            "field_type": "text",
            "prompt": "您的租金預算範圍是？（例如：10000-15000）",
            "validation_type": "free_text",
            "required": true
        }
    ]'::jsonb,
    'show_knowledge',
    NULL,
    true
)
ON CONFLICT (form_id) DO UPDATE SET
    fields = EXCLUDED.fields,
    on_complete_action = EXCLUDED.on_complete_action,
    updated_at = NOW();

-- 插入知識庫配置
INSERT INTO knowledge_base (
    question_summary,
    answer,
    action_type,
    form_id,
    keywords,
    scope,
    is_active
) VALUES (
    '租屋詢問與申請',
    E'✅ **感謝您的租屋詢問！**\n\n我們已經收到您的資料，專員會在 **1-2 個工作天內** 與您聯繫。\n\n📋 **後續流程**：\n1. 專員會根據您的需求推薦適合的物件\n2. 安排看房時間\n3. 協助辦理租賃合約\n\n如有急事，歡迎直接撥打客服電話：(02)1234-5678',
    'form_fill',
    'rental_inquiry',
    ARRAY['租房', '租屋', '申請', '詢問'],
    'global',
    true
)
ON CONFLICT DO NOTHING;

-- ==========================================
-- 場景 C: API 查詢（已登入）(api_call)
-- 用戶問：「我的帳單」（user_id 已存在）
-- ==========================================

INSERT INTO knowledge_base (
    question_summary,
    answer,
    action_type,
    api_config,
    keywords,
    scope,
    is_active
) VALUES (
    '帳單查詢（已登入用戶）',
    E'📌 **溫馨提醒**\n\n如果您未收到帳單郵件，請檢查：\n1. 垃圾郵件夾\n2. 郵箱地址是否正確\n3. 郵件過濾規則\n\n如仍有問題，請聯繫客服協助。',
    'api_call',
    '{
        "endpoint": "billing_inquiry",
        "params": {
            "user_id": "{session.user_id}"
        },
        "combine_with_knowledge": true,
        "fallback_message": "⚠️ 目前無法查詢帳單，請稍後再試。\n\n{knowledge_answer}"
    }'::jsonb,
    ARRAY['帳單', '查詢', '繳費通知', '未收到'],
    'global',
    true
)
ON CONFLICT DO NOTHING;

-- ==========================================
-- 場景 D: 表單 + API（未登入）(form_then_api)
-- 用戶問：「我的帳單」（user_id 不存在，需要收集資訊）
-- ==========================================

-- 創建帳單查詢表單（訪客）
INSERT INTO form_schemas (
    form_id,
    form_name,
    trigger_intents,
    fields,
    on_complete_action,
    api_config,
    vendor_id,
    is_active
) VALUES (
    'billing_inquiry_guest',
    '帳單查詢表（訪客）',
    '["帳單查詢", "查詢帳單"]'::jsonb,
    '[
        {
            "field_name": "tenant_id",
            "field_label": "租客編號",
            "field_type": "text",
            "prompt": "請提供您的租客編號（格式：T12345）",
            "validation_type": "free_text",
            "required": true
        },
        {
            "field_name": "id_last_4",
            "field_label": "身分證後4碼",
            "field_type": "text",
            "prompt": "請提供您身分證後 4 碼（用於身份驗證）",
            "validation_type": "free_text",
            "required": true,
            "max_length": 4
        },
        {
            "field_name": "inquiry_month",
            "field_label": "查詢月份",
            "field_type": "text",
            "prompt": "請問要查詢哪個月的帳單？（格式：YYYY-MM，例如：2026-01）",
            "validation_type": "free_text",
            "required": false
        }
    ]'::jsonb,
    'call_api',
    '{
        "endpoint": "billing_inquiry",
        "verify_identity_first": true,
        "verification_params": {
            "tenant_id": "tenant_id",
            "id_last_4": "id_last_4"
        },
        "params_from_form": {
            "user_id": "tenant_id",
            "month": "inquiry_month"
        },
        "combine_with_knowledge": true,
        "fallback_message": "⚠️ 目前無法查詢帳單，請稍後再試或聯繫客服。"
    }'::jsonb,
    NULL,
    true
)
ON CONFLICT (form_id) DO UPDATE SET
    fields = EXCLUDED.fields,
    on_complete_action = EXCLUDED.on_complete_action,
    api_config = EXCLUDED.api_config,
    updated_at = NOW();

-- 插入知識庫配置（訪客帳單查詢）
INSERT INTO knowledge_base (
    question_summary,
    answer,
    action_type,
    form_id,
    api_config,
    keywords,
    scope,
    is_active
) VALUES (
    '帳單查詢（訪客）',
    E'📌 **溫馨提醒**\n\n如果您未收到帳單郵件，請檢查：\n1. 垃圾郵件夾\n2. 郵箱地址是否正確\n3. 郵件過濾規則\n\n如仍有問題，請聯繫客服協助。',
    'form_then_api',
    'billing_inquiry_guest',
    '{
        "endpoint": "billing_inquiry",
        "verify_identity_first": true,
        "verification_params": {
            "tenant_id": "tenant_id",
            "id_last_4": "id_last_4"
        },
        "params_from_form": {
            "user_id": "tenant_id",
            "month": "inquiry_month"
        },
        "combine_with_knowledge": true
    }'::jsonb,
    ARRAY['帳單', '查詢', '訪客', '未登入'],
    'global',
    true
)
ON CONFLICT DO NOTHING;

-- ==========================================
-- 場景 E: 表單 + API（只返回 API 結果）(form_then_api)
-- 用戶問：「我要報修」
-- ==========================================

-- 創建報修申請表單
INSERT INTO form_schemas (
    form_id,
    form_name,
    trigger_intents,
    fields,
    on_complete_action,
    api_config,
    vendor_id,
    is_active
) VALUES (
    'maintenance_request',
    '報修申請表',
    '["報修", "維修申請", "設備故障"]'::jsonb,
    '[
        {
            "field_name": "location",
            "field_label": "報修地點",
            "field_type": "text",
            "prompt": "請提供報修地點（例如：客廳、廚房、浴室）",
            "validation_type": "free_text",
            "required": true
        },
        {
            "field_name": "issue_description",
            "field_label": "問題描述",
            "field_type": "text",
            "prompt": "請描述需要維修的問題",
            "validation_type": "free_text",
            "required": true
        },
        {
            "field_name": "urgency",
            "field_label": "緊急程度",
            "field_type": "text",
            "prompt": "請選擇緊急程度：1-一般、2-緊急、3-非常緊急",
            "validation_type": "free_text",
            "required": true
        },
        {
            "field_name": "contact_time",
            "field_label": "方便聯繫時間",
            "field_type": "text",
            "prompt": "請提供方便聯繫的時間",
            "validation_type": "free_text",
            "required": false
        }
    ]'::jsonb,
    'call_api',
    '{
        "endpoint": "maintenance_request",
        "params_from_form": {
            "user_id": "{session.user_id}",
            "location": "location",
            "description": "issue_description",
            "urgency": "urgency",
            "contact_time": "contact_time"
        },
        "combine_with_knowledge": false,
        "response_template": "✅ **報修申請已送出**\n\n報修單號：{api_response}\n\n我們會盡快安排維修人員處理，請保持電話暢通。"
    }'::jsonb,
    NULL,
    true
)
ON CONFLICT (form_id) DO UPDATE SET
    fields = EXCLUDED.fields,
    on_complete_action = EXCLUDED.on_complete_action,
    api_config = EXCLUDED.api_config,
    updated_at = NOW();

-- 插入知識庫配置（報修申請）
INSERT INTO knowledge_base (
    question_summary,
    answer,
    action_type,
    form_id,
    keywords,
    scope,
    is_active
) VALUES (
    '報修申請',
    '',  -- 不需要知識答案，只返回 API 結果
    'form_then_api',
    'maintenance_request',
    ARRAY['報修', '維修', '故障', '損壞'],
    'global',
    true
)
ON CONFLICT DO NOTHING;

COMMIT;

-- ==========================================
-- 驗證配置結果
-- ==========================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE '帳單查詢系統配置完成';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
    RAISE NOTICE '已配置的場景：';
    RAISE NOTICE '  場景 A: 租金繳納方式說明 (direct_answer)';
    RAISE NOTICE '  場景 B: 租屋詢問與申請 (form_fill)';
    RAISE NOTICE '  場景 C: 帳單查詢-已登入 (api_call)';
    RAISE NOTICE '  場景 D: 帳單查詢-訪客 (form_then_api)';
    RAISE NOTICE '  場景 E: 報修申請 (form_then_api)';
    RAISE NOTICE '';
    RAISE NOTICE '測試建議：';
    RAISE NOTICE '  1. 使用模擬 API (USE_MOCK_BILLING_API=true)';
    RAISE NOTICE '  2. 測試用戶：test_user (身分證後4碼: 1234)';
    RAISE NOTICE '  3. 特殊測試用戶：';
    RAISE NOTICE '     - test_no_data: 無帳單資料';
    RAISE NOTICE '     - test_not_sent: 尚未發送';
    RAISE NOTICE '';
END $$;

-- 顯示統計
SELECT
    '📊 知識庫統計' AS category,
    action_type,
    COUNT(*) AS count
FROM knowledge_base
WHERE is_active = true
GROUP BY action_type
ORDER BY count DESC;
