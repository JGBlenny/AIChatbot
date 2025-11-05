-- 修復：暫時禁用測試情境的向量相似度檢查
-- 原因：test_scenarios 表缺少 question_embedding 欄位
-- 策略：讓函數返回空結果，不影響知識匯入流程

-- 修改 find_similar_test_scenario 函數，暫時返回空結果
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
    -- 暫時返回空結果，因為 test_scenarios 表缺少 question_embedding 欄位
    -- 文字去重已在 _deduplicate_exact_match 函數中完成
    -- 未來可在添加 question_embedding 欄位後恢復向量相似度檢查
    RETURN;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_similar_test_scenario IS
'查詢測試情境中語意相似的問題（暫時禁用，因為缺少 question_embedding 欄位）';

SELECT '✅ 已修復 find_similar_test_scenario 函數（暫時禁用向量檢查）' AS status;
