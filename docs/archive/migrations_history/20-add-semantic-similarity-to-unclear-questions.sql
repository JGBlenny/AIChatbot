-- Migration: Add semantic similarity support to unclear_questions
-- Purpose: Enable clustering of semantically similar questions to share frequency counts

-- 1. Add embedding column to store question vectors
ALTER TABLE unclear_questions
ADD COLUMN IF NOT EXISTS question_embedding vector(1536);

-- 2. Create index for efficient similarity search
CREATE INDEX IF NOT EXISTS idx_unclear_questions_embedding
ON unclear_questions USING ivfflat (question_embedding vector_cosine_ops)
WITH (lists = 100);

-- 3. Create function to find semantically similar questions
CREATE OR REPLACE FUNCTION find_similar_unclear_question(
    p_question_text TEXT,
    p_question_embedding vector(1536),
    p_similarity_threshold DECIMAL DEFAULT 0.85
)
RETURNS TABLE (
    similar_question_id INTEGER,
    similar_question_text TEXT,
    similarity_score DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        id,
        question,
        (1 - (question_embedding <=> p_question_embedding))::DECIMAL(5,4) AS similarity
    FROM unclear_questions
    WHERE question_embedding IS NOT NULL
        AND question != p_question_text  -- Don't match exact same text
        AND (1 - (question_embedding <=> p_question_embedding)) >= p_similarity_threshold
    ORDER BY question_embedding <=> p_question_embedding ASC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- 4. Create function to record unclear question with semantic deduplication
CREATE OR REPLACE FUNCTION record_unclear_question_with_semantics(
    p_question TEXT,
    p_question_embedding vector(1536),
    p_intent_guess VARCHAR(100) DEFAULT NULL,
    p_similarity_threshold DECIMAL DEFAULT 0.85
)
RETURNS TABLE (
    unclear_question_id INTEGER,
    is_new_question BOOLEAN,
    matched_similar_question TEXT,
    similarity_score DECIMAL,
    current_frequency INTEGER
) AS $$
DECLARE
    v_existing_id INTEGER;
    v_similar_question TEXT;
    v_similarity DECIMAL;
    v_new_frequency INTEGER;
BEGIN
    -- First, check for exact match
    SELECT id INTO v_existing_id
    FROM unclear_questions
    WHERE question = p_question;

    IF v_existing_id IS NOT NULL THEN
        -- Exact match found, increment frequency
        UPDATE unclear_questions
        SET frequency = frequency + 1,
            last_asked_at = NOW(),
            question_embedding = COALESCE(question_embedding, p_question_embedding)
        WHERE id = v_existing_id
        RETURNING frequency INTO v_new_frequency;

        RETURN QUERY SELECT v_existing_id, FALSE, p_question, 1.0000::DECIMAL, v_new_frequency;
        RETURN;
    END IF;

    -- No exact match, check for semantic similarity
    SELECT similar_question_id, similar_question_text, similarity_score
    INTO v_existing_id, v_similar_question, v_similarity
    FROM find_similar_unclear_question(p_question, p_question_embedding, p_similarity_threshold);

    IF v_existing_id IS NOT NULL THEN
        -- Similar question found, increment frequency of existing question
        UPDATE unclear_questions
        SET frequency = frequency + 1,
            last_asked_at = NOW()
        WHERE id = v_existing_id
        RETURNING frequency INTO v_new_frequency;

        RETURN QUERY SELECT v_existing_id, FALSE, v_similar_question, v_similarity, v_new_frequency;
        RETURN;
    END IF;

    -- No similar question found, create new entry
    INSERT INTO unclear_questions (question, question_embedding, intent_guess, frequency, first_asked_at, last_asked_at)
    VALUES (p_question, p_question_embedding, p_intent_guess, 1, NOW(), NOW())
    RETURNING id INTO v_existing_id;

    RETURN QUERY SELECT v_existing_id, TRUE, NULL::TEXT, NULL::DECIMAL, 1;
END;
$$ LANGUAGE plpgsql;

-- 5. Create view to show questions with their similar matches
CREATE OR REPLACE VIEW v_unclear_questions_with_clusters AS
WITH question_pairs AS (
    SELECT
        q1.id AS q1_id,
        q1.question AS q1_text,
        q1.frequency AS q1_frequency,
        q2.id AS q2_id,
        q2.question AS q2_text,
        q2.frequency AS q2_frequency,
        (1 - (q1.question_embedding <=> q2.question_embedding))::DECIMAL(5,4) AS similarity
    FROM unclear_questions q1
    CROSS JOIN unclear_questions q2
    WHERE q1.id < q2.id
        AND q1.question_embedding IS NOT NULL
        AND q2.question_embedding IS NOT NULL
        AND (1 - (q1.question_embedding <=> q2.question_embedding)) >= 0.85
)
SELECT
    q1_id,
    q1_text,
    q1_frequency,
    q2_id AS similar_question_id,
    q2_text AS similar_question_text,
    q2_frequency AS similar_frequency,
    similarity,
    (q1_frequency + q2_frequency) AS combined_frequency
FROM question_pairs
ORDER BY combined_frequency DESC, similarity DESC;

COMMENT ON FUNCTION find_similar_unclear_question IS
'Finds the most semantically similar unclear question above a threshold';

COMMENT ON FUNCTION record_unclear_question_with_semantics IS
'Records an unclear question with semantic deduplication - increments frequency of similar questions instead of creating duplicates';

COMMENT ON VIEW v_unclear_questions_with_clusters IS
'Shows unclear questions grouped by semantic similarity with combined frequency counts';
