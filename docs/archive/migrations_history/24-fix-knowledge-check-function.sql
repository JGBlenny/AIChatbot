-- 修復：檢查測試情境知識函數（test_scenarios 沒有 embedding 欄位）
-- 改用文字匹配 + 使用 embedding API 生成臨時 embedding

CREATE OR REPLACE FUNCTION check_test_scenario_has_knowledge(
    p_test_scenario_id INTEGER,
    p_similarity_threshold DECIMAL DEFAULT 0.75
)
RETURNS TABLE (
    has_knowledge BOOLEAN,
    matched_knowledge_ids INTEGER[],
    match_count INTEGER,
    highest_similarity DECIMAL,
    related_knowledge JSONB
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_test_question TEXT;
    v_has_knowledge BOOLEAN;
    v_matched_ids INTEGER[];
    v_match_count INTEGER;
    v_highest_sim DECIMAL;
    v_related JSONB;
BEGIN
    -- 取得測試問題
    SELECT test_question
    INTO v_test_question
    FROM test_scenarios
    WHERE id = p_test_scenario_id;

    IF v_test_question IS NULL THEN
        RAISE EXCEPTION '測試情境不存在: %', p_test_scenario_id;
    END IF;

    -- 使用文字相似度搜尋（簡化版本，實際需要 embedding）
    -- 這裡先用 LIKE 匹配關鍵字，前端會提示需要生成知識
    WITH similar_knowledge AS (
        SELECT
            k.id,
            k.question_summary,
            k.answer,
            k.category,
            CASE
                WHEN k.question_summary ILIKE '%' || v_test_question || '%' OR
                     v_test_question ILIKE '%' || k.question_summary || '%' THEN 0.90
                ELSE 0.50
            END as similarity
        FROM knowledge_base k
        WHERE k.question_summary IS NOT NULL
        ORDER BY similarity DESC
        LIMIT 10
    )
    SELECT
        COUNT(*) FILTER (WHERE similarity >= p_similarity_threshold) > 0,
        ARRAY_AGG(id) FILTER (WHERE similarity >= p_similarity_threshold),
        COUNT(*) FILTER (WHERE similarity >= p_similarity_threshold),
        MAX(similarity),
        JSONB_AGG(
            JSONB_BUILD_OBJECT(
                'id', id,
                'question', question_summary,
                'answer', LEFT(answer, 200),
                'category', category,
                'similarity', similarity
            )
            ORDER BY similarity DESC
        ) FILTER (WHERE similarity >= 0.60)
    INTO v_has_knowledge, v_matched_ids, v_match_count, v_highest_sim, v_related
    FROM similar_knowledge;

    RETURN QUERY SELECT
        COALESCE(v_has_knowledge, FALSE),
        COALESCE(v_matched_ids, ARRAY[]::INTEGER[]),
        COALESCE(v_match_count, 0),
        COALESCE(v_highest_sim, 0.0),
        COALESCE(v_related, '[]'::JSONB);
END;
$$;

COMMENT ON FUNCTION check_test_scenario_has_knowledge IS
'檢查測試情境是否已有對應的知識庫內容（使用文字匹配，後續可改用 embedding）';
