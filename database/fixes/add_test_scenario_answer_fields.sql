-- 添加測試場景的答案和質量評分欄位
-- 用於 LLM 語義對比和質量控制

ALTER TABLE test_scenarios
ADD COLUMN IF NOT EXISTS expected_answer TEXT,
ADD COLUMN IF NOT EXISTS min_quality_score DECIMAL(2,1) DEFAULT 3.0 CHECK (min_quality_score >= 1.0 AND min_quality_score <= 5.0);

COMMENT ON COLUMN test_scenarios.expected_answer IS '標準答案（可選）用於 LLM 語義對比';
COMMENT ON COLUMN test_scenarios.min_quality_score IS '最低質量要求（1-5分）';
