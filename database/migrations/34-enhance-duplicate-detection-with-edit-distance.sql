-- Migration 34: 增強重複問題檢測 - 組合策略（語義 + 編輯距離）
-- 日期: 2025-10-13
-- 目的: 提升打字錯誤的容錯能力
--
-- 改進:
-- 1. 降低語義相似度閾值從 0.85 → 0.80
-- 2. 增加編輯距離檢測（Levenshtein Distance ≤ 2）
-- 3. 組合策略: 語義 ≥ 0.80 OR 編輯距離 ≤ 2
--
-- 覆蓋案例:
-- - "每月租金幾號要繳" vs "每月租金幾號較腳" (語義 0.8363, 編輯 2) ✅
-- - "每月租金幾號要繳" vs "每月住金幾號要繳" (語義 0.7633, 編輯 1) ✅
-- - "每月租金幾號要繳" vs "每月租金幾好要繳" (語義 0.9107, 編輯 1) ✅

-- ====================
-- 1. 創建 Levenshtein 編輯距離函數（如果不存在）
-- ====================

CREATE OR REPLACE FUNCTION levenshtein_distance(s1 TEXT, s2 TEXT)
RETURNS INTEGER
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    len1 INTEGER;
    len2 INTEGER;
    cost INTEGER;
    d INTEGER[][];
    i INTEGER;
    j INTEGER;
BEGIN
    len1 := LENGTH(s1);
    len2 := LENGTH(s2);

    -- 初始化矩陣
    FOR i IN 0..len1 LOOP
        d[i][0] := i;
    END LOOP;

    FOR j IN 0..len2 LOOP
        d[0][j] := j;
    END LOOP;

    -- 計算編輯距離
    FOR i IN 1..len1 LOOP
        FOR j IN 1..len2 LOOP
            IF SUBSTRING(s1 FROM i FOR 1) = SUBSTRING(s2 FROM j FOR 1) THEN
                cost := 0;
            ELSE
                cost := 1;
            END IF;

            d[i][j] := LEAST(
                d[i-1][j] + 1,      -- 刪除
                d[i][j-1] + 1,      -- 插入
                d[i-1][j-1] + cost  -- 替換
            );
        END LOOP;
    END LOOP;

    RETURN d[len1][len2];
END;
$$;

COMMENT ON FUNCTION levenshtein_distance IS '計算兩個字符串之間的 Levenshtein 編輯距離';

-- ====================
-- 2. 更新 record_unclear_question_with_semantics 函數
-- ====================

DROP FUNCTION IF EXISTS public.record_unclear_question_with_semantics(TEXT, vector(1536), VARCHAR(100), DECIMAL);

CREATE OR REPLACE FUNCTION public.record_unclear_question_with_semantics(
    p_question TEXT,
    p_question_embedding vector(1536),
    p_intent_guess VARCHAR(100) DEFAULT NULL,
    p_similarity_threshold DECIMAL DEFAULT 0.80  -- 降低閾值從 0.85 → 0.80
)
RETURNS TABLE (
    unclear_question_id INTEGER,
    is_new_question BOOLEAN,
    matched_similar_question TEXT,
    sim_score DECIMAL,
    current_frequency INTEGER,
    match_method VARCHAR(50)  -- 新增：匹配方法（'exact', 'semantic', 'edit_distance', 'none'）
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
        levenshtein_distance(question, p_question) AS edit_dist
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
            levenshtein_distance(question, p_question) <= 2
        )
    ORDER BY
        -- 優先選擇語義相似度高的，其次是編輯距離小的
        (1 - (question_embedding <=> p_question_embedding)) DESC,
        levenshtein_distance(question, p_question) ASC
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

-- ====================
-- 3. 創建統計視圖（可選）
-- ====================

CREATE OR REPLACE VIEW v_unclear_questions_match_stats AS
SELECT
    COUNT(*) FILTER (WHERE frequency = 1) as unique_questions,
    COUNT(*) FILTER (WHERE frequency > 1) as merged_questions,
    AVG(frequency) as avg_frequency,
    MAX(frequency) as max_frequency,
    COUNT(DISTINCT CASE WHEN question_embedding IS NOT NULL THEN id END) as with_embedding
FROM unclear_questions
WHERE status != 'resolved';

COMMENT ON VIEW v_unclear_questions_match_stats IS '未釐清問題匹配統計（用於監控去重效果）';

-- ====================
-- 4. 記錄 Migration
-- ====================

INSERT INTO schema_migrations (migration_file, description, executed_at)
VALUES ('34-enhance-duplicate-detection-with-edit-distance.sql', 'Enhance duplicate question detection with combined strategy (semantic + edit distance)', NOW())
ON CONFLICT (migration_file) DO NOTHING;

-- ====================
-- 測試與驗證建議
-- ====================

-- 測試編輯距離函數：
-- SELECT levenshtein_distance('每月租金幾號要繳', '每月租金幾號較腳');  -- 應返回 2
-- SELECT levenshtein_distance('每月租金幾號要繳', '每月住金幾號要繳');  -- 應返回 1

-- 測試去重函數：
-- SELECT * FROM record_unclear_question_with_semantics(
--     '每月租金幾號較腳'::TEXT,
--     (SELECT question_embedding FROM unclear_questions WHERE question = '每月租金幾號要繳' LIMIT 1),
--     'unclear'::VARCHAR(100),
--     0.80::DECIMAL
-- );

-- 查看統計：
-- SELECT * FROM v_unclear_questions_match_stats;
