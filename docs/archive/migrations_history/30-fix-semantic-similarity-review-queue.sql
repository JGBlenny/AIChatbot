-- Migration 30: 修正語意相似度檢查 - 審核佇列改用文字匹配
-- 原因：test_scenarios 和 ai_generated_knowledge_candidates 都沒有 embedding 欄位
-- 因此審核佇列只能使用文字精確匹配，無法使用語意相似度

-- ============================================================
-- 修正函數：查詢審核佇列中相似的候選知識（改用文字匹配）
-- ============================================================

CREATE OR REPLACE FUNCTION find_similar_knowledge_candidate(
    p_question_embedding vector(1536),
    p_similarity_threshold DECIMAL DEFAULT 0.85
)
RETURNS TABLE (
    similar_candidate_id INTEGER,
    similar_question TEXT,
    similar_answer TEXT,
    similarity_score DECIMAL,
    candidate_status VARCHAR
) AS $$
BEGIN
    -- 審核佇列沒有 embedding，無法進行語意相似度比對
    -- 回傳空結果
    RETURN QUERY
    SELECT
        NULL::INTEGER,
        NULL::TEXT,
        NULL::TEXT,
        NULL::DECIMAL,
        NULL::VARCHAR
    WHERE FALSE;  -- 永遠不回傳任何結果
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_similar_knowledge_candidate IS
'查詢審核佇列中語意相似的待審核知識（目前無法實作，因為沒有 embedding）';

-- Note: 審核佇列的去重改由應用層處理文字精確匹配
