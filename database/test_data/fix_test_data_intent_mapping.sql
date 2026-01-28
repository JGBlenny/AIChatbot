-- 修正測試數據的意圖映射 - 2026-01-24
-- 問題：SOP 和知識沒有意圖 ID，無法被檢索到

-- ============================================
-- 1. 更新 SOP 測試數據的 related_intent_id
-- ============================================

-- 【測試】租賃須知 → 合約條款／內容 (7)
UPDATE vendor_sop_items
SET related_intent_id = 7
WHERE item_name = '【測試】租賃須知';

-- 【測試】看房預約 → 物件資訊 (5)
UPDATE vendor_sop_items
SET related_intent_id = 5
WHERE item_name = '【測試】看房預約';

-- 【測試】報修申請 → 報修問題 (3)
UPDATE vendor_sop_items
SET related_intent_id = 3
WHERE item_name = '【測試】報修申請';

-- 【測試】查詢租金帳單 → 帳務查詢 (1)
UPDATE vendor_sop_items
SET related_intent_id = 1
WHERE item_name = '【測試】查詢租金帳單';

-- 【測試】租屋申請 → 租約查詢 (4)
UPDATE vendor_sop_items
SET related_intent_id = 4
WHERE item_name = '【測試】租屋申請';

-- ============================================
-- 2. 為測試知識建立意圖映射
-- ============================================

-- 先獲取測試知識的 ID
DO $$
DECLARE
    kb_api_call_id INT;
    kb_form_then_api_id INT;
    kb_downgrade_form_id INT;
    kb_downgrade_api_id INT;
BEGIN
    -- 獲取知識 ID
    SELECT id INTO kb_api_call_id FROM knowledge_base WHERE question_summary = '【測試】我的租金繳費記錄';
    SELECT id INTO kb_form_then_api_id FROM knowledge_base WHERE question_summary = '【測試】我要退租';
    SELECT id INTO kb_downgrade_form_id FROM knowledge_base WHERE question_summary = '【測試】降級邏輯：缺少 form_id';
    SELECT id INTO kb_downgrade_api_id FROM knowledge_base WHERE question_summary = '【測試】降級邏輯：缺少 api_config';

    -- 刪除舊的映射（如果存在）
    DELETE FROM knowledge_intent_mapping WHERE knowledge_id IN (kb_api_call_id, kb_form_then_api_id, kb_downgrade_form_id, kb_downgrade_api_id);

    -- 建立新映射
    -- 【測試】我的租金繳費記錄 → 帳務查詢 (1)
    IF kb_api_call_id IS NOT NULL THEN
        INSERT INTO knowledge_intent_mapping (knowledge_id, intent_id)
        VALUES (kb_api_call_id, 1);
    END IF;

    -- 【測試】我要退租 → 退租 (12)
    IF kb_form_then_api_id IS NOT NULL THEN
        INSERT INTO knowledge_intent_mapping (knowledge_id, intent_id)
        VALUES (kb_form_then_api_id, 12);
    END IF;

    -- 【測試】降級邏輯：缺少 form_id → 一般知識 (105)
    IF kb_downgrade_form_id IS NOT NULL THEN
        INSERT INTO knowledge_intent_mapping (knowledge_id, intent_id)
        VALUES (kb_downgrade_form_id, 105);
    END IF;

    -- 【測試】降級邏輯：缺少 api_config → 一般知識 (105)
    IF kb_downgrade_api_id IS NOT NULL THEN
        INSERT INTO knowledge_intent_mapping (knowledge_id, intent_id)
        VALUES (kb_downgrade_api_id, 105);
    END IF;

    RAISE NOTICE '✅ 意圖映射已更新';
END $$;

-- ============================================
-- 驗證結果
-- ============================================

SELECT
    '=== SOP 意圖映射 ===' as info,
    id, item_name, related_intent_id
FROM vendor_sop_items
WHERE item_name LIKE '【測試】%'
ORDER BY id;

SELECT
    '=== Knowledge 意圖映射 ===' as info,
    kb.id, LEFT(kb.question_summary, 40) as question, m.intent_id
FROM knowledge_base kb
LEFT JOIN knowledge_intent_mapping m ON kb.id = m.knowledge_id
WHERE kb.question_summary LIKE '【測試】%'
ORDER BY kb.id;
