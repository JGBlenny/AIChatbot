-- 完整測試數據插入腳本 - 2026-01-24
-- 目的：建立所有測試場景需要的數據

-- ============================================
-- 1. SOP 測試數據（4 種觸發模式）
-- ============================================

-- 1.1 SOP: none 模式（資訊展示）
INSERT INTO vendor_sop_items (
    vendor_id, category_id, group_id, item_number, item_name, content,
    trigger_mode, next_action, is_active, priority
) VALUES (
    1, NULL, NULL, 1, '【測試】租賃須知',
    '租屋須知：\n1. 押金為兩個月租金\n2. 租期最少一年\n3. 禁止養寵物',
    'none', 'none', true, 100
) ON CONFLICT DO NOTHING;

-- 1.2 SOP: manual 模式 + form_fill（等待關鍵字觸發表單）
INSERT INTO vendor_sop_items (
    vendor_id, category_id, group_id, item_number, item_name, content,
    trigger_mode, next_action, next_form_id, trigger_keywords, immediate_prompt, is_active, priority
) VALUES (
    1, NULL, NULL, 2, '【測試】看房預約',
    '看房預約說明：\n1. 平日時間：週一至週五 10:00-18:00\n2. 假日時間：週六 10:00-17:00\n3. 需提前一天預約',
    'manual', 'form_fill', 'repair_request',
    ARRAY['我要看房', '預約看房', '安排看房'],
    '需要協助您預約看房嗎？（輸入「是的」或「確認」開始填寫預約表單）',
    true, 100
) ON CONFLICT DO NOTHING;

-- 1.3 SOP: immediate 模式 + form_fill（立即詢問確認）
INSERT INTO vendor_sop_items (
    vendor_id, category_id, group_id, item_number, item_name, content,
    trigger_mode, next_action, next_form_id, immediate_prompt, is_active, priority
) VALUES (
    1, NULL, NULL, 3, '【測試】報修申請',
    '報修流程說明：\n1. 填寫報修表單\n2. 等待管理員確認\n3. 維修人員將於 24 小時內聯繫',
    'immediate', 'form_fill', 'maintenance_request',
    '需要立即為您申請報修嗎？（輸入「確認」開始填寫報修表單）',
    true, 100
) ON CONFLICT DO NOTHING;

-- 1.4 SOP: auto 模式 + api_call（自動調用 API）
INSERT INTO vendor_sop_items (
    vendor_id, category_id, group_id, item_number, item_name, content,
    trigger_mode, next_action, next_api_config, is_active, priority
) VALUES (
    1, NULL, NULL, 4, '【測試】查詢租金帳單',
    '租金帳單查詢服務',
    'auto', 'api_call',
    '{"endpoint": "http://api.example.com/billing", "method": "GET", "params": {"user_id": "${user_id}"}}'::jsonb,
    true, 100
) ON CONFLICT DO NOTHING;

-- 1.5 SOP: immediate 模式 + form_then_api（表單後調用 API）
INSERT INTO vendor_sop_items (
    vendor_id, category_id, group_id, item_number, item_name, content,
    trigger_mode, next_action, next_form_id, next_api_config, immediate_prompt, is_active, priority
) VALUES (
    1, NULL, NULL, 5, '【測試】租屋申請',
    '租屋申請流程：\n1. 填寫申請表\n2. 系統自動提交審核\n3. 等待審核結果',
    'immediate', 'form_then_api', 'rental_application',
    '{"endpoint": "http://api.example.com/rental/submit", "method": "POST"}'::jsonb,
    '要開始租屋申請流程嗎？（輸入「確認」開始）',
    true, 100
) ON CONFLICT DO NOTHING;

-- ============================================
-- 2. Knowledge 測試數據（不同 action_type）
-- ============================================

-- 2.1 knowledge: action_type = 'api_call'
INSERT INTO knowledge_base (
    vendor_id, question_summary, answer,
    action_type, api_config,
    target_user, is_active, priority, intent_assigned_by
) VALUES (
    1,
    '【測試】我的租金繳費記錄',
    '您的租金繳費記錄查詢中...',
    'api_call',
    '{"endpoint": "http://api.example.com/payment/history", "method": "GET", "params": {"user_id": "${user_id}"}}'::jsonb,
    ARRAY['tenant'], true, 100, 'manual'
) ON CONFLICT DO NOTHING;

-- 2.2 knowledge: action_type = 'form_then_api'
INSERT INTO knowledge_base (
    vendor_id, question_summary, answer,
    action_type, form_id, api_config,
    target_user, is_active, priority, intent_assigned_by
) VALUES (
    1,
    '【測試】我要退租',
    '退租申請流程',
    'form_then_api', 'rental_inquiry',
    '{"endpoint": "http://api.example.com/rental/cancel", "method": "POST"}'::jsonb,
    ARRAY['tenant'], true, 100, 'manual'
) ON CONFLICT DO NOTHING;

-- 2.3 knowledge: action_type = 'form_fill'（但故意缺少 form_id，測試降級）
INSERT INTO knowledge_base (
    vendor_id, question_summary, answer,
    action_type, form_id,
    target_user, is_active, priority, intent_assigned_by
) VALUES (
    1,
    '【測試】降級邏輯：缺少 form_id',
    '這是一個測試降級邏輯的知識，action_type=form_fill 但 form_id=NULL',
    'form_fill', NULL,
    ARRAY['tenant'], true, 100, 'manual'
) ON CONFLICT DO NOTHING;

-- 2.4 knowledge: action_type = 'api_call'（但故意缺少 api_config，測試降級）
INSERT INTO knowledge_base (
    vendor_id, question_summary, answer,
    action_type, api_config,
    target_user, is_active, priority, intent_assigned_by
) VALUES (
    1,
    '【測試】降級邏輯：缺少 api_config',
    '這是一個測試降級邏輯的知識，action_type=api_call 但 api_config=NULL',
    'api_call', NULL,
    ARRAY['tenant'], true, 100, 'manual'
) ON CONFLICT DO NOTHING;

-- ============================================
-- 驗證插入結果
-- ============================================

SELECT
    '=== SOP 測試數據 ===' as info,
    COUNT(*) as count
FROM vendor_sop_items
WHERE vendor_id = 1 AND item_name LIKE '【測試】%';

SELECT
    trigger_mode, next_action, COUNT(*) as count
FROM vendor_sop_items
WHERE vendor_id = 1 AND item_name LIKE '【測試】%'
GROUP BY trigger_mode, next_action
ORDER BY trigger_mode, next_action;

SELECT
    '=== Knowledge 測試數據 ===' as info,
    COUNT(*) as count
FROM knowledge_base
WHERE vendor_id = 1 AND question_summary LIKE '【測試】%';

SELECT
    action_type, form_id IS NOT NULL as has_form, api_config IS NOT NULL as has_api, COUNT(*) as count
FROM knowledge_base
WHERE vendor_id = 1 AND question_summary LIKE '【測試】%'
GROUP BY action_type, form_id IS NOT NULL, api_config IS NOT NULL
ORDER BY action_type;
