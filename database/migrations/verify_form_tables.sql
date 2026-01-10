-- ==========================================
-- 表單功能資料表驗證腳本
-- 說明: 用於驗證表單功能資料表是否正確建立
-- ==========================================

-- 1. 檢查所有表單相關資料表
SELECT
    '✅ 資料表檢查' as check_type,
    tablename,
    CASE
        WHEN tablename IS NOT NULL THEN '已建立'
        ELSE '未建立'
    END as status
FROM pg_tables
WHERE tablename IN ('form_schemas', 'form_sessions', 'form_submissions')
ORDER BY tablename;

-- 2. 檢查索引數量
SELECT
    '✅ 索引檢查' as check_type,
    tablename,
    COUNT(*) as index_count
FROM pg_indexes
WHERE tablename LIKE 'form_%'
GROUP BY tablename
ORDER BY tablename;

-- 3. 檢查表單定義
SELECT
    '✅ 表單定義檢查' as check_type,
    form_id,
    form_name,
    is_active,
    jsonb_array_length(fields) as field_count,
    jsonb_array_length(trigger_intents) as trigger_count,
    vendor_id,
    created_at
FROM form_schemas
ORDER BY form_id;

-- 4. 檢查欄位定義詳細內容（租屋申請表）
SELECT
    '✅ 租屋申請表欄位詳細' as check_type,
    jsonb_pretty(fields) as field_definitions
FROM form_schemas
WHERE form_id = 'rental_application';

-- 5. 檢查觸發意圖
SELECT
    '✅ 觸發意圖檢查' as check_type,
    form_id,
    jsonb_pretty(trigger_intents) as trigger_intents
FROM form_schemas
WHERE form_id = 'rental_application';

-- 6. 檢查表單會話狀態（應該為空）
SELECT
    '✅ 表單會話檢查' as check_type,
    COUNT(*) as session_count,
    COUNT(CASE WHEN state = 'COLLECTING' THEN 1 END) as collecting_count,
    COUNT(CASE WHEN state = 'COMPLETED' THEN 1 END) as completed_count,
    COUNT(CASE WHEN state = 'CANCELLED' THEN 1 END) as cancelled_count
FROM form_sessions;

-- 7. 檢查表單提交記錄（應該為空）
SELECT
    '✅ 表單提交檢查' as check_type,
    COUNT(*) as submission_count
FROM form_submissions;

-- 8. 檢查外鍵約束
SELECT
    '✅ 外鍵約束檢查' as check_type,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name LIKE 'form_%'
ORDER BY tc.table_name, kcu.column_name;

-- 9. 總結報告
DO $$
DECLARE
    schema_count INTEGER;
    session_count INTEGER;
    submission_count INTEGER;
    index_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO schema_count FROM form_schemas;
    SELECT COUNT(*) INTO session_count FROM form_sessions;
    SELECT COUNT(*) INTO submission_count FROM form_submissions;
    SELECT COUNT(*) INTO index_count FROM pg_indexes WHERE tablename LIKE 'form_%';

    RAISE NOTICE '';
    RAISE NOTICE '==========================================';
    RAISE NOTICE '表單功能資料表驗證總結';
    RAISE NOTICE '==========================================';
    RAISE NOTICE '✅ 表單定義數量: %', schema_count;
    RAISE NOTICE '✅ 表單會話數量: %', session_count;
    RAISE NOTICE '✅ 表單提交數量: %', submission_count;
    RAISE NOTICE '✅ 索引總數: %', index_count;
    RAISE NOTICE '==========================================';

    IF schema_count > 0 THEN
        RAISE NOTICE '✅ 驗證通過：表單功能資料表已正確建立';
    ELSE
        RAISE WARNING '⚠️  驗證失敗：未找到表單定義';
    END IF;
END $$;
