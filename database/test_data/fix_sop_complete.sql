-- 完整修復 SOP 測試數據 - 2026-01-24
-- 問題：
-- 1. SOP 沒有 category_id（INNER JOIN 會過濾掉）
-- 2. 沒有在 vendor_sop_item_intents 表中建立映射

-- ============================================
-- 1. 創建測試 SOP 分類
-- ============================================

-- 獲取測試分類 ID
DO $$
DECLARE
    test_category_id INT;
    sop_id INT;
BEGIN
    -- 獲取或創建測試分類
    SELECT id INTO test_category_id
    FROM vendor_sop_categories
    WHERE vendor_id = 1 AND category_name = '【測試分類】';

    IF test_category_id IS NULL THEN
        INSERT INTO vendor_sop_categories (vendor_id, category_name, is_active)
        VALUES (1, '【測試分類】', true)
        RETURNING id INTO test_category_id;
    END IF;

    RAISE NOTICE '✅ 測試分類 ID: %', test_category_id;

    -- ============================================
    -- 2. 更新所有測試 SOP 的 category_id
    -- ============================================

    UPDATE vendor_sop_items
    SET category_id = test_category_id
    WHERE vendor_id = 1 AND item_name LIKE '【測試】%';

    RAISE NOTICE '✅ 已更新測試 SOP 的 category_id';

    -- ============================================
    -- 3. 在 vendor_sop_item_intents 建立意圖映射
    -- ============================================

    -- 刪除舊的映射
    DELETE FROM vendor_sop_item_intents
    WHERE sop_item_id IN (
        SELECT id FROM vendor_sop_items
        WHERE vendor_id = 1 AND item_name LIKE '【測試】%'
    );

    -- 【測試】租賃須知 (1657) → 合約條款／內容 (7)
    SELECT id INTO sop_id FROM vendor_sop_items WHERE item_name = '【測試】租賃須知';
    IF sop_id IS NOT NULL THEN
        INSERT INTO vendor_sop_item_intents (sop_item_id, intent_id) VALUES (sop_id, 7);
        RAISE NOTICE '✅ SOP % → Intent 7', sop_id;
    END IF;

    -- 【測試】看房預約 (1658) → 物件資訊 (5)
    SELECT id INTO sop_id FROM vendor_sop_items WHERE item_name = '【測試】看房預約';
    IF sop_id IS NOT NULL THEN
        INSERT INTO vendor_sop_item_intents (sop_item_id, intent_id) VALUES (sop_id, 5);
        RAISE NOTICE '✅ SOP % → Intent 5', sop_id;
    END IF;

    -- 【測試】報修申請 (1659) → 報修問題 (3)
    SELECT id INTO sop_id FROM vendor_sop_items WHERE item_name = '【測試】報修申請';
    IF sop_id IS NOT NULL THEN
        INSERT INTO vendor_sop_item_intents (sop_item_id, intent_id) VALUES (sop_id, 3);
        RAISE NOTICE '✅ SOP % → Intent 3', sop_id;
    END IF;

    -- 【測試】查詢租金帳單 (1660) → 帳務查詢 (1)
    SELECT id INTO sop_id FROM vendor_sop_items WHERE item_name = '【測試】查詢租金帳單';
    IF sop_id IS NOT NULL THEN
        INSERT INTO vendor_sop_item_intents (sop_item_id, intent_id) VALUES (sop_id, 1);
        RAISE NOTICE '✅ SOP % → Intent 1', sop_id;
    END IF;

    -- 【測試】租屋申請 (1661) → 租約查詢 (4)
    SELECT id INTO sop_id FROM vendor_sop_items WHERE item_name = '【測試】租屋申請';
    IF sop_id IS NOT NULL THEN
        INSERT INTO vendor_sop_item_intents (sop_item_id, intent_id) VALUES (sop_id, 4);
        RAISE NOTICE '✅ SOP % → Intent 4', sop_id;
    END IF;

END $$;

-- ============================================
-- 驗證結果
-- ============================================

SELECT
    '=== SOP 完整配置 ===' as info,
    si.id,
    si.item_name,
    si.category_id,
    sc.category_name,
    si.related_intent_id,
    vsii.intent_id as item_intent_id
FROM vendor_sop_items si
LEFT JOIN vendor_sop_categories sc ON si.category_id = sc.id
LEFT JOIN vendor_sop_item_intents vsii ON si.id = vsii.sop_item_id
WHERE si.item_name LIKE '【測試】%'
ORDER BY si.id;
