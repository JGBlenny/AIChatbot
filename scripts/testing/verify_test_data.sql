-- 驗證測試資料狀態

\echo '=== 測試資料總覽 ==='
SELECT
    id,
    question_summary AS 標題,
    action_type AS 後續動作,
    COALESCE(trigger_mode, 'NULL') AS 觸發模式,
    form_id AS 表單ID,
    COALESCE(array_length(trigger_keywords, 1), 0) AS 關鍵詞數量,
    LENGTH(COALESCE(immediate_prompt, '')) AS 提示詞長度,
    updated_at::timestamp(0) AS 最後更新
FROM knowledge_base
WHERE question_summary LIKE '測試-%' AND vendor_id = 1
ORDER BY id;

\echo ''
\echo '=== 按觸發模式分組 ==='
SELECT
    COALESCE(trigger_mode, 'NULL') AS 觸發模式,
    COUNT(*) AS 數量
FROM knowledge_base
WHERE question_summary LIKE '測試-%' AND vendor_id = 1
GROUP BY trigger_mode
ORDER BY trigger_mode NULLS FIRST;

\echo ''
\echo '=== 排查型資料詳情 ==='
SELECT
    id,
    question_summary AS 標題,
    form_id AS 表單,
    trigger_keywords AS 觸發關鍵詞
FROM knowledge_base
WHERE question_summary LIKE '測試-%'
  AND vendor_id = 1
  AND trigger_mode = 'manual'
ORDER BY id;

\echo ''
\echo '=== 行動型資料詳情 ==='
SELECT
    id,
    question_summary AS 標題,
    form_id AS 表單,
    immediate_prompt AS 確認提示詞
FROM knowledge_base
WHERE question_summary LIKE '測試-%'
  AND vendor_id = 1
  AND trigger_mode = 'immediate'
ORDER BY id;

\echo ''
\echo '=== NULL trigger_mode 資料 ==='
SELECT
    id,
    question_summary AS 標題,
    action_type AS 後續動作,
    form_id AS 表單
FROM knowledge_base
WHERE question_summary LIKE '測試-%'
  AND vendor_id = 1
  AND trigger_mode IS NULL
ORDER BY id;
