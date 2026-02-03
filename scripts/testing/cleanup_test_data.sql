-- 清理測試資料

\echo '=== 清理前統計 ==='
SELECT COUNT(*) AS 測試資料筆數
FROM knowledge_base
WHERE question_summary LIKE '測試-%' AND vendor_id = 1;

-- 執行刪除
DELETE FROM knowledge_base
WHERE question_summary LIKE '測試-%' AND vendor_id = 1;

\echo ''
\echo '=== 清理後統計 ==='
SELECT COUNT(*) AS 剩餘測試資料筆數
FROM knowledge_base
WHERE question_summary LIKE '測試-%' AND vendor_id = 1;

\echo ''
\echo '✅ 測試資料清理完成'
