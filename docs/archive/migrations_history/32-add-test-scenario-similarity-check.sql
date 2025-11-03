-- Migration 32: 為測試情境增加語意相似度檢查，支援完整去重
-- 目的：讓知識匯入的語意去重功能也能檢查測試情境表

-- 建立測試情境的語意相似度搜尋函數
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
        (1 - (ts.question_embedding <=> p_question_embedding))::DECIMAL AS similarity_score,
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

-- 更新綜合相似度檢查函數，加入測試情境檢查
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
