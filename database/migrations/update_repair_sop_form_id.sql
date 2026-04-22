-- =====================================================
-- 修繕 SOP 表單指向更新
-- =====================================================
-- 創建日期: 2026-04-22
-- 用途: 將修繕類 SOP 的 next_form_id 從 maintenance_request
--       更新為新的 jgb_repair_create 表單
-- 影響: vendor_id=2 且 next_action='form_fill' 且
--       next_form_id='maintenance_request' 的 SOP 記錄
-- =====================================================

-- 先檢查受影響的筆數
DO $$
DECLARE
    affected_count INT;
BEGIN
    SELECT COUNT(*) INTO affected_count
    FROM vendor_sop_items
    WHERE vendor_id = 2
      AND next_action = 'form_fill'
      AND next_form_id = 'maintenance_request';

    RAISE NOTICE '將更新 % 筆修繕 SOP 的 next_form_id', affected_count;
END $$;

-- 執行更新
UPDATE vendor_sop_items
SET next_form_id = 'jgb_repair_create',
    updated_at = CURRENT_TIMESTAMP
WHERE vendor_id = 2
  AND next_action = 'form_fill'
  AND next_form_id = 'maintenance_request';

-- 驗證結果
DO $$
DECLARE
    updated_count INT;
    remaining_count INT;
BEGIN
    -- 檢查更新後的結果
    SELECT COUNT(*) INTO updated_count
    FROM vendor_sop_items
    WHERE vendor_id = 2
      AND next_action = 'form_fill'
      AND next_form_id = 'jgb_repair_create';

    -- 檢查是否還有殘留的 maintenance_request
    SELECT COUNT(*) INTO remaining_count
    FROM vendor_sop_items
    WHERE vendor_id = 2
      AND next_action = 'form_fill'
      AND next_form_id = 'maintenance_request';

    RAISE NOTICE '=================================================';
    RAISE NOTICE '✅ 修繕 SOP 表單指向更新完成';
    RAISE NOTICE '=================================================';
    RAISE NOTICE '📋 已更新為 jgb_repair_create: % 筆', updated_count;
    RAISE NOTICE '📋 殘留 maintenance_request: % 筆', remaining_count;
    RAISE NOTICE '=================================================';
END $$;
