-- ================================================
-- Migration: Update v_unclear_question_candidates view
-- Purpose: Show rejected scenarios that can be retried
-- Date: 2025-10-12
-- ================================================

-- 先刪除舊視圖
DROP VIEW IF EXISTS v_unclear_question_candidates;

-- 重新創建視圖（添加 is_high_freq_retry 欄位）
CREATE VIEW v_unclear_question_candidates AS
SELECT
    uq.id as unclear_question_id,
    uq.question,
    uq.intent_type,
    uq.frequency,
    uq.first_asked_at,
    uq.last_asked_at,
    uq.status as unclear_status,
    ts.id as existing_scenario_id,
    ts.status as scenario_status,

    -- 判斷是否可以創建/重新創建測試情境
    CASE
        -- 情況1：沒有任何情境 → 可以創建
        WHEN ts.id IS NULL THEN true

        -- 情況2：有 rejected 情境 + 高頻（≥5次）→ 可以重新創建
        WHEN ts.status = 'rejected' AND uq.frequency >= 5 THEN true

        -- 情況3：其他情況（pending_review, approved，或 rejected 但未達高頻）→ 不可創建
        ELSE false
    END as can_create_scenario,

    -- 標識是否為高頻重試場景
    CASE
        WHEN ts.status = 'rejected' AND uq.frequency >= 5 THEN true
        ELSE false
    END as is_high_freq_retry,

    uq.similarity_score,
    uq.retrieved_docs
FROM unclear_questions uq
LEFT JOIN (
    -- 子查詢：取每個 source_question_id 最新的測試情境
    SELECT DISTINCT ON (source_question_id)
        id,
        source_question_id,
        status,
        created_at
    FROM test_scenarios
    WHERE source_question_id IS NOT NULL
    ORDER BY source_question_id, created_at DESC
) ts ON ts.source_question_id = uq.id
WHERE uq.status IN ('pending', 'in_progress')
  AND uq.frequency >= 2  -- 至少被問過2次
ORDER BY
    CASE WHEN ts.status = 'rejected' AND uq.frequency >= 5 THEN 0 ELSE 1 END,  -- 高頻重試優先
    uq.frequency DESC,
    uq.last_asked_at DESC;

COMMENT ON VIEW v_unclear_question_candidates IS
'用戶問題轉測試情境候選列表。包含：
1. 頻率 >= 2 且未創建情境的問題
2. 頻率 >= 5 且最新情境為 rejected 的高頻問題（允許重試）';

COMMIT;
