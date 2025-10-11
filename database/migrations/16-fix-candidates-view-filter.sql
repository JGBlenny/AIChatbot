-- ================================================
-- Migration: Fix v_unclear_question_candidates view filtering
-- Purpose: Only show questions that actually need action
-- Date: 2025-10-12
-- ================================================

-- 問題：
-- 當前視圖顯示所有頻率 >= 2 的問題，包括已經有 pending_review/approved 情境的問題
-- 這導致前端顯示大量 can_create_scenario = false 的無用數據

-- 解決方案：
-- 只顯示真正需要處理的問題：
-- 1. 沒有任何測試情境的問題（可以創建）
-- 2. 有 rejected 情境且達到高頻閾值的問題（可以重試）

DROP VIEW IF EXISTS v_unclear_question_candidates;

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

    -- 判斷是否可以創建/重新創建
    CASE
        WHEN ts.id IS NULL THEN true
        WHEN ts.status = 'rejected' AND uq.frequency >= 5 THEN true
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
  AND uq.frequency >= 2
  AND (
      -- 條件1：沒有任何測試情境
      ts.id IS NULL
      OR
      -- 條件2：有 rejected 情境且達到高頻閾值
      (ts.status = 'rejected' AND uq.frequency >= 5)
  )
ORDER BY
    CASE WHEN ts.status = 'rejected' AND uq.frequency >= 5 THEN 0 ELSE 1 END,
    uq.frequency DESC,
    uq.last_asked_at DESC;

COMMENT ON VIEW v_unclear_question_candidates IS
'用戶問題轉測試情境候選列表（已過濾）。
只顯示需要處理的問題：
1. 頻率 >= 2 且沒有任何測試情境的問題
2. 頻率 >= 5 且最新情境為 rejected 的問題（高頻重試）

不顯示：
- 已有 pending_review 情境的問題（正在審核中）
- 已有 approved 情境的問題（已處理完成）
- 有 rejected 情境但頻率 < 5 的問題（未達重試閾值）';

COMMIT;
