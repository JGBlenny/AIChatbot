-- ================================================
-- Migration: Fix v_unclear_question_candidates view - check all scenarios
-- Purpose: Don't show questions that have ANY pending_review or approved scenario
-- Date: 2025-10-12
-- ================================================

-- 問題：
-- 當前視圖只檢查最新的測試情境
-- 如果一個問題有多個測試情境（例如：#34 pending_review, #35 rejected）
-- 視圖會選擇最新的 #35，認為可以重新創建
-- 但實際上 #34 還在審核中，不應該允許再次創建

-- 解決方案：
-- 檢查該問題的所有測試情境
-- 如果有任何 pending_review 或 approved 的情境，就不顯示

DROP VIEW IF EXISTS v_unclear_question_candidates;

CREATE VIEW v_unclear_question_candidates AS
WITH question_scenario_status AS (
    -- 為每個 unclear_question 計算其關聯的所有測試情境狀態
    SELECT
        uq.id as unclear_question_id,
        uq.question,
        uq.intent_type,
        uq.frequency,
        uq.first_asked_at,
        uq.last_asked_at,
        uq.status as unclear_status,
        uq.similarity_score,
        uq.retrieved_docs,

        -- 最新的測試情境
        (SELECT ts.id
         FROM test_scenarios ts
         WHERE ts.source_question_id = uq.id
         ORDER BY ts.created_at DESC
         LIMIT 1) as latest_scenario_id,

        (SELECT ts.status
         FROM test_scenarios ts
         WHERE ts.source_question_id = uq.id
         ORDER BY ts.created_at DESC
         LIMIT 1) as latest_scenario_status,

        -- 是否有任何 pending_review 的情境
        EXISTS (
            SELECT 1
            FROM test_scenarios ts
            WHERE ts.source_question_id = uq.id
              AND ts.status = 'pending_review'
        ) as has_pending_scenario,

        -- 是否有任何 approved 的情境
        EXISTS (
            SELECT 1
            FROM test_scenarios ts
            WHERE ts.source_question_id = uq.id
              AND ts.status = 'approved'
        ) as has_approved_scenario

    FROM unclear_questions uq
    WHERE uq.status IN ('pending', 'in_progress')
      AND uq.frequency >= 2
)
SELECT
    unclear_question_id,
    question,
    intent_type,
    frequency,
    first_asked_at,
    last_asked_at,
    unclear_status,
    latest_scenario_id as existing_scenario_id,
    latest_scenario_status as scenario_status,

    -- 判斷是否可以創建/重新創建
    CASE
        -- 有 pending_review 或 approved 的情境 → 不能創建
        WHEN has_pending_scenario OR has_approved_scenario THEN false

        -- 沒有任何情境 → 可以創建
        WHEN latest_scenario_id IS NULL THEN true

        -- 所有情境都是 rejected + 達到高頻閾值 → 可以重試
        WHEN latest_scenario_status = 'rejected' AND frequency >= 5 THEN true

        ELSE false
    END as can_create_scenario,

    -- 標識是否為高頻重試場景
    CASE
        WHEN NOT has_pending_scenario
         AND NOT has_approved_scenario
         AND latest_scenario_status = 'rejected'
         AND frequency >= 5
        THEN true
        ELSE false
    END as is_high_freq_retry,

    similarity_score,
    retrieved_docs
FROM question_scenario_status
WHERE
    -- 只顯示真正需要處理的問題
    (
        -- 條件1：沒有任何測試情境
        latest_scenario_id IS NULL
        OR
        -- 條件2：所有情境都是 rejected + 高頻（沒有 pending 或 approved）
        (
            NOT has_pending_scenario
            AND NOT has_approved_scenario
            AND latest_scenario_status = 'rejected'
            AND frequency >= 5
        )
    )
ORDER BY
    CASE WHEN latest_scenario_status = 'rejected' AND frequency >= 5 THEN 0 ELSE 1 END,
    frequency DESC,
    last_asked_at DESC;

COMMENT ON VIEW v_unclear_question_candidates IS
'用戶問題轉測試情境候選列表（完整檢查）。

只顯示真正需要處理的問題：
1. 頻率 >= 2 且沒有任何測試情境
2. 頻率 >= 5 且所有情境都是 rejected（高頻重試）

排除條件：
- 有任何 pending_review 情境的問題（正在審核中）
- 有任何 approved 情境的問題（已處理完成）
- 有 rejected 情境但頻率 < 5（未達重試閾值）
- 有 rejected + pending_review 並存的問題（有情境在審核中）';

COMMIT;
