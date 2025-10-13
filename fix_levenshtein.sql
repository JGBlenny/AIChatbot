-- Fix levenshtein function to use PostgreSQL built-in

-- Drop old functions
DROP FUNCTION IF EXISTS levenshtein_distance(TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS public.record_unclear_question_with_semantics(TEXT, vector(1536), VARCHAR(100), DECIMAL) CASCADE;

-- Recreate function using built-in levenshtein
CREATE OR REPLACE FUNCTION public.record_unclear_question_with_semantics(
    p_question TEXT,
    p_question_embedding vector(1536),
    p_intent_guess VARCHAR(100) DEFAULT NULL,
    p_similarity_threshold DECIMAL DEFAULT 0.80
)
RETURNS TABLE (
    unclear_question_id INTEGER,
    is_new_question BOOLEAN,
    matched_similar_question TEXT,
    sim_score DECIMAL,
    current_frequency INTEGER,
    match_method VARCHAR(50)
) LANGUAGE plpgsql AS $$
DECLARE
    v_existing_id INTEGER;
    v_similar_question TEXT;
    v_similarity DECIMAL;
    v_new_frequency INTEGER;
    v_edit_distance INTEGER;
    v_matched_by VARCHAR(50);
BEGIN
    -- 策略 1: 精確匹配（最優先）
    SELECT id INTO v_existing_id
    FROM unclear_questions
    WHERE question = p_question
        AND status != 'resolved';

    IF v_existing_id IS NOT NULL THEN
        -- 精確匹配：更新頻率
        UPDATE unclear_questions
        SET frequency = frequency + 1,
            last_asked_at = NOW(),
            question_embedding = COALESCE(question_embedding, p_question_embedding)
        WHERE id = v_existing_id
        RETURNING frequency INTO v_new_frequency;

        RETURN QUERY SELECT
            v_existing_id,
            FALSE,
            p_question,
            1.0::DECIMAL,
            v_new_frequency,
            'exact'::VARCHAR(50);
        RETURN;
    END IF;

    -- 策略 2: 組合檢測（語義相似度 OR 編輯距離）
    SELECT
        id,
        question,
        1 - (question_embedding <=> p_question_embedding) AS semantic_similarity,
        levenshtein(question, p_question) AS edit_dist
    INTO
        v_existing_id,
        v_similar_question,
        v_similarity,
        v_edit_distance
    FROM unclear_questions
    WHERE question_embedding IS NOT NULL
        AND status != 'resolved'
        AND (
            -- 條件 A: 語義相似度 >= 閾值
            (1 - (question_embedding <=> p_question_embedding)) >= p_similarity_threshold
            OR
            -- 條件 B: 編輯距離 <= 2（輕微打字錯誤）
            levenshtein(question, p_question) <= 2
        )
    ORDER BY
        -- 優先選擇語義相似度高的，其次是編輯距離小的
        (1 - (question_embedding <=> p_question_embedding)) DESC,
        levenshtein(question, p_question) ASC
    LIMIT 1;

    IF v_existing_id IS NOT NULL THEN
        -- 找到相似問題：更新頻率
        UPDATE unclear_questions
        SET frequency = frequency + 1,
            last_asked_at = NOW()
        WHERE id = v_existing_id
        RETURNING frequency INTO v_new_frequency;

        -- 判斷匹配方法
        IF v_similarity >= p_similarity_threshold THEN
            v_matched_by := 'semantic';
        ELSE
            v_matched_by := 'edit_distance';
        END IF;

        RETURN QUERY SELECT
            v_existing_id,
            FALSE,
            v_similar_question,
            v_similarity,
            v_new_frequency,
            v_matched_by;
        RETURN;
    END IF;

    -- 策略 3: 無匹配，建立新問題
    INSERT INTO unclear_questions (
        question,
        question_embedding,
        intent_type,
        frequency,
        status,
        first_asked_at,
        last_asked_at
    ) VALUES (
        p_question,
        p_question_embedding,
        p_intent_guess,
        1,
        'pending',
        NOW(),
        NOW()
    )
    RETURNING id INTO v_existing_id;

    RETURN QUERY SELECT
        v_existing_id,
        TRUE,
        NULL::TEXT,
        0.0::DECIMAL,
        1,
        'none'::VARCHAR(50);
END;
$$;

COMMENT ON FUNCTION record_unclear_question_with_semantics IS
'記錄未釐清問題（增強版）：支援組合策略（語義相似度 ≥ 0.80 OR 編輯距離 ≤ 2）以提升打字錯誤容錯能力';
