-- Migration 29: 為知識匯入新增語意相似度檢查
-- 目的：在匯入時檢查語意相似的知識，避免重複，節省 OpenAI token 成本
-- 重用 unclear_questions 的相似度機制（閾值：0.85）

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
    -- 從測試情境取得 embedding，然後比對候選知識
    RETURN QUERY
    SELECT
        kc.id,
        kc.question,
        LEFT(kc.generated_answer, 200) AS answer_preview,
        (1 - (ts.question_embedding <=> p_question_embedding))::DECIMAL(5,4) AS similarity,
        kc.status
    FROM ai_generated_knowledge_candidates kc
    INNER JOIN test_scenarios ts ON kc.test_scenario_id = ts.id
    WHERE ts.question_embedding IS NOT NULL
        AND (1 - (ts.question_embedding <=> p_question_embedding)) >= p_similarity_threshold
        AND kc.status = 'pending_review'  -- 只檢查待審核的
    ORDER BY ts.question_embedding <=> p_question_embedding ASC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_similar_knowledge_candidate IS
'查詢審核佇列中語意相似的待審核知識（避免重複匯入）';

-- ============================================================
-- 3. 建立函數：綜合查詢（檢查知識庫 + 審核佇列）
-- ============================================================

CREATE OR REPLACE FUNCTION check_knowledge_exists_by_similarity(
    p_question_embedding vector(1536),
    p_similarity_threshold DECIMAL DEFAULT 0.85
)
RETURNS TABLE (
    exists_in_knowledge_base BOOLEAN,
    exists_in_review_queue BOOLEAN,
    knowledge_id INTEGER,
    candidate_id INTEGER,
    matched_question TEXT,
    similarity_score DECIMAL,
    source_table VARCHAR
) AS $$
DECLARE
    v_kb_result RECORD;
    v_candidate_result RECORD;
BEGIN
    -- 1. 檢查正式知識庫
    SELECT * INTO v_kb_result
    FROM find_similar_knowledge(p_question_embedding, p_similarity_threshold);

    -- 2. 檢查審核佇列
    SELECT * INTO v_candidate_result
    FROM find_similar_knowledge_candidate(p_question_embedding, p_similarity_threshold);

    -- 3. 返回綜合結果
    IF v_kb_result IS NOT NULL THEN
        -- 知識庫中已有相似知識
        RETURN QUERY SELECT
            TRUE,
            FALSE,
            v_kb_result.similar_knowledge_id,
            NULL::INTEGER,
            v_kb_result.similar_question,
            v_kb_result.similarity_score,
            'knowledge_base'::VARCHAR;
    ELSIF v_candidate_result IS NOT NULL THEN
        -- 審核佇列中已有相似知識
        RETURN QUERY SELECT
            FALSE,
            TRUE,
            NULL::INTEGER,
            v_candidate_result.similar_candidate_id,
            v_candidate_result.similar_question,
            v_candidate_result.similarity_score,
            'review_queue'::VARCHAR;
    ELSE
        -- 沒有找到相似知識
        RETURN QUERY SELECT
            FALSE,
            FALSE,
            NULL::INTEGER,
            NULL::INTEGER,
            NULL::TEXT,
            NULL::DECIMAL,
            NULL::VARCHAR;
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION check_knowledge_exists_by_similarity IS
'綜合檢查知識是否已存在（檢查正式知識庫 + 審核佇列），用於匯入前的語意去重';

-- ============================================================
-- 4. 建立視圖：顯示知識庫中的相似知識群組
-- ============================================================

CREATE OR REPLACE VIEW v_similar_knowledge_clusters AS
WITH knowledge_pairs AS (
    SELECT
        k1.id AS k1_id,
        k1.question_summary AS k1_question,
        k1.category AS k1_category,
        k2.id AS k2_id,
        k2.question_summary AS k2_question,
        k2.category AS k2_category,
        (1 - (k1.embedding <=> k2.embedding))::DECIMAL(5,4) AS similarity
    FROM knowledge_base k1
    CROSS JOIN knowledge_base k2
    WHERE k1.id < k2.id
        AND k1.embedding IS NOT NULL
        AND k2.embedding IS NOT NULL
        AND (1 - (k1.embedding <=> k2.embedding)) >= 0.85
)
SELECT
    k1_id,
    k1_question,
    k1_category,
    k2_id AS similar_knowledge_id,
    k2_question AS similar_question,
    k2_category AS similar_category,
    similarity
FROM knowledge_pairs
ORDER BY similarity DESC;

COMMENT ON VIEW v_similar_knowledge_clusters IS
'顯示知識庫中語意相似的知識（相似度 ≥0.85），用於識別潛在的重複知識';

-- ============================================================
-- 5. 建立統計函數：語意重複統計
-- ============================================================

CREATE OR REPLACE FUNCTION get_semantic_duplication_stats()
RETURNS TABLE (
    total_knowledge_count BIGINT,
    knowledge_with_embedding BIGINT,
    similar_pairs_count BIGINT,
    avg_similarity NUMERIC,
    max_similarity NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH stats AS (
        SELECT
            COUNT(*)::BIGINT as total_kb,
            COUNT(*) FILTER (WHERE embedding IS NOT NULL)::BIGINT as with_emb
        FROM knowledge_base
    ),
    similarity_stats AS (
        SELECT
            COUNT(*)::BIGINT as pairs,
            ROUND(AVG(similarity)::NUMERIC, 4) as avg_sim,
            MAX(similarity) as max_sim
        FROM v_similar_knowledge_clusters
    )
    SELECT
        s.total_kb,
        s.with_emb,
        COALESCE(ss.pairs, 0),
        COALESCE(ss.avg_sim, 0),
        COALESCE(ss.max_sim, 0)
    FROM stats s
    CROSS JOIN similarity_stats ss;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_semantic_duplication_stats IS
'取得知識庫的語意重複統計資訊';

-- ============================================================
-- Migration 完成
-- ============================================================

-- 測試查詢範例：
/*
-- 1. 查詢與特定 embedding 相似的知識
SELECT * FROM find_similar_knowledge('[0.1,0.2,...]'::vector(1536), 0.85);

-- 2. 檢查知識是否已存在（綜合查詢）
SELECT * FROM check_knowledge_exists_by_similarity('[0.1,0.2,...]'::vector(1536), 0.85);

-- 3. 查看相似知識群組
SELECT * FROM v_similar_knowledge_clusters LIMIT 20;

-- 4. 取得語意重複統計
SELECT * FROM get_semantic_duplication_stats();
*/
