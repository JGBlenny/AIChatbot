-- 修復：添加知識相似度檢查函數
-- 來源：migration 29 和 32
-- 目的：修復知識匯入時的語意相似度檢查功能

-- ============================================================
-- 1. 建立函數：查詢相似的知識庫內容
-- ============================================================

CREATE OR REPLACE FUNCTION find_similar_knowledge(
    p_question_embedding vector(1536),
    p_similarity_threshold DECIMAL DEFAULT 0.85
)
RETURNS TABLE (
    similar_knowledge_id INTEGER,
    similar_question TEXT,
    similar_answer TEXT,
    similarity_score DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        id,
        question_summary,
        LEFT(answer, 200) AS answer_preview,
        (1 - (embedding <=> p_question_embedding))::DECIMAL(5,4) AS similarity
    FROM knowledge_base
    WHERE embedding IS NOT NULL
        AND (1 - (embedding <=> p_question_embedding)) >= p_similarity_threshold
    ORDER BY embedding <=> p_question_embedding ASC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_similar_knowledge IS
'查詢知識庫中語意相似的知識（預設閾值 0.85，與 unclear_questions 一致）';

-- ============================================================
-- 2. 建立函數：查詢審核佇列中相似的候選知識
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
    -- 從 ai_generated_knowledge_candidates 的 question_embedding 欄位比對
    RETURN QUERY
    SELECT
        kc.id,
        kc.question,
        LEFT(kc.generated_answer, 200) AS answer_preview,
        (1 - (kc.question_embedding <=> p_question_embedding))::DECIMAL(5,4) AS similarity,
        kc.status
    FROM ai_generated_knowledge_candidates kc
    WHERE kc.question_embedding IS NOT NULL
        AND (1 - (kc.question_embedding <=> p_question_embedding)) >= p_similarity_threshold
        AND kc.status = 'pending_review'  -- 只檢查待審核的
    ORDER BY kc.question_embedding <=> p_question_embedding ASC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_similar_knowledge_candidate IS
'查詢審核佇列中語意相似的待審核知識（避免重複匯入）';

-- ============================================================
-- 3. 建立函數：查詢測試情境中的相似問題
-- ============================================================

CREATE OR REPLACE FUNCTION find_similar_test_scenario(
    p_question_embedding vector(1536),
    p_similarity_threshold DECIMAL DEFAULT 0.85
)
RETURNS TABLE (
    similar_scenario_id INTEGER,
    similar_question TEXT,
    similarity_score DECIMAL,
    scenario_status VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ts.id AS similar_scenario_id,
        ts.test_question AS similar_question,
        (1 - (ts.question_embedding <=> p_question_embedding))::DECIMAL(5,4) AS similarity_score,
        ts.status AS scenario_status
    FROM test_scenarios ts
    WHERE ts.question_embedding IS NOT NULL
      AND (1 - (ts.question_embedding <=> p_question_embedding)) >= p_similarity_threshold
    ORDER BY ts.question_embedding <=> p_question_embedding
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_similar_test_scenario IS
'查詢測試情境中語意相似的問題（使用向量相似度，閾值預設 0.85）';

-- ============================================================
-- 4. 建立函數：綜合查詢（檢查知識庫 + 審核佇列 + 測試情境）
-- ============================================================

CREATE OR REPLACE FUNCTION check_knowledge_exists_by_similarity(
    p_question_embedding vector(1536),
    p_similarity_threshold DECIMAL DEFAULT 0.85
)
RETURNS TABLE (
    exists_in_knowledge_base BOOLEAN,
    exists_in_review_queue BOOLEAN,
    exists_in_test_scenarios BOOLEAN,
    knowledge_id INTEGER,
    candidate_id INTEGER,
    scenario_id INTEGER,
    matched_question TEXT,
    similarity_score DECIMAL,
    source_table VARCHAR
) AS $$
DECLARE
    v_kb_result RECORD;
    v_candidate_result RECORD;
    v_scenario_result RECORD;
BEGIN
    -- 1. 檢查正式知識庫
    SELECT * INTO v_kb_result
    FROM find_similar_knowledge(p_question_embedding, p_similarity_threshold);

    -- 2. 檢查審核佇列
    SELECT * INTO v_candidate_result
    FROM find_similar_knowledge_candidate(p_question_embedding, p_similarity_threshold);

    -- 3. 檢查測試情境
    SELECT * INTO v_scenario_result
    FROM find_similar_test_scenario(p_question_embedding, p_similarity_threshold);

    -- 4. 返回綜合結果（優先級：knowledge_base > review_queue > test_scenarios）
    IF v_kb_result IS NOT NULL THEN
        -- 知識庫中已有相似知識
        RETURN QUERY SELECT
            TRUE,
            FALSE,
            FALSE,
            v_kb_result.similar_knowledge_id,
            NULL::INTEGER,
            NULL::INTEGER,
            v_kb_result.similar_question,
            v_kb_result.similarity_score,
            'knowledge_base'::VARCHAR;
    ELSIF v_candidate_result IS NOT NULL THEN
        -- 審核佇列中已有相似知識
        RETURN QUERY SELECT
            FALSE,
            TRUE,
            FALSE,
            NULL::INTEGER,
            v_candidate_result.similar_candidate_id,
            NULL::INTEGER,
            v_candidate_result.similar_question,
            v_candidate_result.similarity_score,
            'review_queue'::VARCHAR;
    ELSIF v_scenario_result IS NOT NULL THEN
        -- 測試情境中已有相似問題
        RETURN QUERY SELECT
            FALSE,
            FALSE,
            TRUE,
            NULL::INTEGER,
            NULL::INTEGER,
            v_scenario_result.similar_scenario_id,
            v_scenario_result.similar_question,
            v_scenario_result.similarity_score,
            'test_scenarios'::VARCHAR;
    ELSE
        -- 沒有找到相似知識
        RETURN QUERY SELECT
            FALSE,
            FALSE,
            FALSE,
            NULL::INTEGER,
            NULL::INTEGER,
            NULL::INTEGER,
            NULL::TEXT,
            NULL::DECIMAL,
            NULL::VARCHAR;
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION check_knowledge_exists_by_similarity IS
'綜合檢查知識庫、審核佇列和測試情境中是否存在語意相似的知識（閾值預設 0.85）';

-- ============================================================
-- 5. 為 ai_generated_knowledge_candidates 添加 question_embedding 欄位（如果不存在）
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'ai_generated_knowledge_candidates'
        AND column_name = 'question_embedding'
    ) THEN
        ALTER TABLE ai_generated_knowledge_candidates
        ADD COLUMN question_embedding vector(1536);

        -- 添加索引以加速向量搜尋
        CREATE INDEX idx_ai_candidates_question_embedding
        ON ai_generated_knowledge_candidates
        USING ivfflat (question_embedding vector_cosine_ops);

        RAISE NOTICE 'Added question_embedding column to ai_generated_knowledge_candidates';
    ELSE
        RAISE NOTICE 'question_embedding column already exists';
    END IF;
END $$;

-- ============================================================
-- 完成訊息
-- ============================================================

SELECT '✅ 知識相似度檢查函數已添加' AS status;
