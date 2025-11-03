-- 更新視圖：移除 expected_category 字段
-- 原因：測試情境簡化，不再使用 expected_category 字段

CREATE OR REPLACE VIEW v_pending_ai_knowledge_candidates AS
SELECT
    kc.id as candidate_id,
    kc.test_scenario_id,
    ts.test_question as original_test_question,
    ts.difficulty,
    kc.question,
    kc.generated_answer,
    kc.confidence_score,
    kc.ai_model,
    kc.warnings,
    kc.status,
    kc.created_at,
    kc.edited_answer IS NOT NULL as has_edits,
    -- 來源問題的頻率
    CASE
        WHEN ts.source_question_id IS NOT NULL
        THEN (SELECT frequency FROM unclear_questions WHERE id = ts.source_question_id)
        ELSE NULL
    END as source_question_frequency
FROM ai_generated_knowledge_candidates kc
INNER JOIN test_scenarios ts ON kc.test_scenario_id = ts.id
WHERE kc.status IN ('pending_review', 'needs_revision')
ORDER BY kc.created_at DESC;

COMMENT ON VIEW v_pending_ai_knowledge_candidates IS '
待審核的 AI 知識候選視圖（已移除 expected_category 字段）
包含：
- 基本候選信息
- 測試情境信息
- 編輯狀態
- 來源問題頻率
';
