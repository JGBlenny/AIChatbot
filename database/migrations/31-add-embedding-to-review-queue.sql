-- Migration 31: 為審核佇列增加 embedding 欄位，支援語意去重
-- 目的：讓知識匯入的語意去重功能也能檢查審核佇列中的知識

-- 為 ai_generated_knowledge_candidates 增加 embedding 欄位
ALTER TABLE ai_generated_knowledge_candidates
ADD COLUMN IF NOT EXISTS question_embedding vector(1536);

-- 為 test_scenarios 增加 embedding 欄位
ALTER TABLE test_scenarios
ADD COLUMN IF NOT EXISTS question_embedding vector(1536);

-- 重新實作審核佇列的語意相似度搜尋函數
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
    RETURN QUERY
    SELECT
        c.id AS similar_candidate_id,
        c.question AS similar_question,
        c.generated_answer AS similar_answer,
        (1 - (c.question_embedding <=> p_question_embedding))::DECIMAL AS similarity_score,
        c.status AS candidate_status
    FROM ai_generated_knowledge_candidates c
    WHERE c.question_embedding IS NOT NULL
      AND (1 - (c.question_embedding <=> p_question_embedding)) >= p_similarity_threshold
    ORDER BY c.question_embedding <=> p_question_embedding
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_similar_knowledge_candidate IS
'查詢審核佇列中語意相似的待審核知識（使用向量相似度，閾值預設 0.85）';

-- 為新增的欄位建立索引，提升查詢效能
CREATE INDEX IF NOT EXISTS idx_candidates_question_embedding
ON ai_generated_knowledge_candidates USING ivfflat (question_embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_test_scenarios_question_embedding
ON test_scenarios USING ivfflat (question_embedding vector_cosine_ops)
WITH (lists = 100);
