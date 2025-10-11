-- Fix: 重新建立語義相似度函數，避免 column ambiguity

-- 刪除舊版本
DROP FUNCTION IF EXISTS public.record_unclear_question_with_semantics(TEXT, vector, VARCHAR, DECIMAL);
DROP FUNCTION IF EXISTS public.record_unclear_question_with_semantics(TEXT, vector(1536), VARCHAR(100), DECIMAL);

-- 建立新版本，使用 sim_score 作為回傳欄位名稱（避免與 unclear_questions.similarity_score 衝突）
CREATE OR REPLACE FUNCTION public.record_unclear_question_with_semantics(
    p_question TEXT,
    p_question_embedding vector(1536),
    p_intent_guess VARCHAR(100) DEFAULT NULL,
    p_similarity_threshold DECIMAL DEFAULT 0.85
)
RETURNS TABLE (
    unclear_question_id INTEGER,
    is_new_question BOOLEAN,
    matched_similar_question TEXT,
    sim_score DECIMAL,
    current_frequency INTEGER
) LANGUAGE plpgsql AS $$
DECLARE
    v_existing_id INTEGER;
    v_similar_question TEXT;
    v_similarity DECIMAL;
    v_new_frequency INTEGER;
BEGIN
    -- 1. 檢查精確匹配
    SELECT uq.id INTO v_existing_id
    FROM unclear_questions uq
    WHERE uq.question = p_question;

    IF v_existing_id IS NOT NULL THEN
        UPDATE unclear_questions
        SET frequency = frequency + 1,
            last_asked_at = NOW(),
            question_embedding = COALESCE(question_embedding, p_question_embedding)
        WHERE id = v_existing_id
        RETURNING frequency INTO v_new_frequency;

        RETURN QUERY SELECT v_existing_id, FALSE, p_question, 1.0000::DECIMAL, v_new_frequency;
        RETURN;
    END IF;

    -- 2. 檢查語義相似度
    SELECT fsq.similar_question_id, fsq.similar_question_text, fsq.similarity_score
    INTO v_existing_id, v_similar_question, v_similarity
    FROM find_similar_unclear_question(p_question, p_question_embedding, p_similarity_threshold) fsq;

    IF v_existing_id IS NOT NULL THEN
        UPDATE unclear_questions
        SET frequency = frequency + 1,
            last_asked_at = NOW()
        WHERE id = v_existing_id
        RETURNING frequency INTO v_new_frequency;

        RETURN QUERY SELECT v_existing_id, FALSE, v_similar_question, v_similarity, v_new_frequency;
        RETURN;
    END IF;

    -- 3. 建立新記錄
    INSERT INTO unclear_questions (question, question_embedding, intent_guess, frequency, first_asked_at, last_asked_at)
    VALUES (p_question, p_question_embedding, p_intent_guess, 1, NOW(), NOW())
    RETURNING id INTO v_existing_id;

    RETURN QUERY SELECT v_existing_id, TRUE, NULL::TEXT, NULL::DECIMAL, 1;
END;
$$;

COMMENT ON FUNCTION public.record_unclear_question_with_semantics IS '記錄未釐清問題（使用語義去重）- 如果存在語義相似的問題則累加頻率而非建立新記錄';
