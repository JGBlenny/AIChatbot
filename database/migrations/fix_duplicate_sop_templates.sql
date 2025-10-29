-- ============================================================================
-- 修復 SOP 模板重複問題
-- ============================================================================
--
-- 問題說明：
-- 1. Excel 文件有 28 個應備欄位，對應 9 個群組（說明）
-- 2. 資料庫中 ID 1-28 的模板已正確分配群組
-- 3. 資料庫中 ID 346-401 的模板是重複資料，且未分配群組
-- 4. 共 56 個重複模板需要停用
--
-- 修復策略：
-- 將重複的模板標記為 is_active=false（保留歷史記錄，不刪除）
-- ============================================================================

BEGIN;

-- 記錄修復前的狀態
DO $$
DECLARE
    total_templates INTEGER;
    active_templates INTEGER;
    templates_with_group INTEGER;
    templates_without_group INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_templates FROM platform_sop_templates;
    SELECT COUNT(*) INTO active_templates FROM platform_sop_templates WHERE is_active = true;
    SELECT COUNT(*) INTO templates_with_group FROM platform_sop_templates WHERE is_active = true AND group_id IS NOT NULL;
    SELECT COUNT(*) INTO templates_without_group FROM platform_sop_templates WHERE is_active = true AND group_id IS NULL;

    RAISE NOTICE '====================================';
    RAISE NOTICE '修復前狀態：';
    RAISE NOTICE '  總模板數：%', total_templates;
    RAISE NOTICE '  啟用模板數：%', active_templates;
    RAISE NOTICE '  已分配群組：%', templates_with_group;
    RAISE NOTICE '  未分配群組：%', templates_without_group;
    RAISE NOTICE '====================================';
END $$;

-- 停用重複的模板（ID 346-401）
UPDATE platform_sop_templates
SET
    is_active = false,
    updated_at = CURRENT_TIMESTAMP
WHERE id BETWEEN 346 AND 401
  AND is_active = true;

-- 記錄修復後的狀態
DO $$
DECLARE
    total_templates INTEGER;
    active_templates INTEGER;
    templates_with_group INTEGER;
    templates_without_group INTEGER;
    deactivated_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_templates FROM platform_sop_templates;
    SELECT COUNT(*) INTO active_templates FROM platform_sop_templates WHERE is_active = true;
    SELECT COUNT(*) INTO templates_with_group FROM platform_sop_templates WHERE is_active = true AND group_id IS NOT NULL;
    SELECT COUNT(*) INTO templates_without_group FROM platform_sop_templates WHERE is_active = true AND group_id IS NULL;
    SELECT COUNT(*) INTO deactivated_count FROM platform_sop_templates WHERE id BETWEEN 346 AND 401 AND is_active = false;

    RAISE NOTICE '====================================';
    RAISE NOTICE '修復後狀態：';
    RAISE NOTICE '  總模板數：%', total_templates;
    RAISE NOTICE '  啟用模板數：%', active_templates;
    RAISE NOTICE '  已分配群組：%', templates_with_group;
    RAISE NOTICE '  未分配群組：%', templates_without_group;
    RAISE NOTICE '  已停用重複模板：%', deactivated_count;
    RAISE NOTICE '====================================';

    -- 驗證修復結果
    IF templates_without_group > 0 THEN
        RAISE WARNING '警告：仍有 % 個模板未分配群組！', templates_without_group;
    ELSE
        RAISE NOTICE '✅ 所有啟用的模板都已正確分配群組！';
    END IF;
END $$;

-- 顯示被停用的模板列表（供確認）
SELECT
    id,
    category_id,
    item_name as 模板名稱,
    '已停用（重複）' as 狀態
FROM platform_sop_templates
WHERE id BETWEEN 346 AND 401
ORDER BY id;

COMMIT;

-- ============================================================================
-- 驗證查詢：修復後的結構應該是
-- - 3 個分類
-- - 9 個群組（說明）
-- - 28 個啟用模板（應備欄位）
-- - 所有啟用模板都有 group_id
-- ============================================================================
