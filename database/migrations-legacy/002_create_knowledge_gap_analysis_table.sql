-- Migration: 建立知識庫完善迴圈系統 - 知識缺口分析表
-- 日期: 2026-03-21
-- 任務: 1.2 建立知識缺口分析資料表
-- 用途: 記錄每次迭代的缺口分析結果

CREATE TABLE IF NOT EXISTS knowledge_gap_analysis (
    id SERIAL PRIMARY KEY,
    loop_id INT NOT NULL REFERENCES knowledge_completion_loops(id) ON DELETE CASCADE,
    iteration INT NOT NULL,
    scenario_id INT NOT NULL,  -- 參照 test_scenarios.id

    -- 缺口資訊
    question TEXT NOT NULL,
    failure_reason VARCHAR(50) NOT NULL,  -- no_match, low_confidence, semantic_mismatch, system_error
    priority VARCHAR(10) NOT NULL,  -- p0, p1, p2
    suggested_action_type VARCHAR(50),  -- knowledge, form, api

    -- 回測評分資訊
    confidence_score FLOAT,
    max_similarity FLOAT,

    -- 意圖聚類
    intent_id INT,
    intent_name VARCHAR(200),
    frequency INT DEFAULT 1,  -- 相似問題數

    -- 關聯至生成的知識
    loop_knowledge_id INT,  -- 將在後續 migration 中建立外鍵（loop_generated_knowledge 表尚未建立）

    -- 處理狀態
    status VARCHAR(50) DEFAULT 'pending',  -- pending, knowledge_generated, approved, rejected

    created_at TIMESTAMP DEFAULT NOW(),

    -- CHECK 約束
    CONSTRAINT check_failure_reason CHECK (failure_reason IN ('no_match', 'low_confidence', 'semantic_mismatch', 'system_error')),
    CONSTRAINT check_priority CHECK (priority IN ('p0', 'p1', 'p2')),
    CONSTRAINT check_status CHECK (status IN ('pending', 'knowledge_generated', 'approved', 'rejected'))
);

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_gap_analysis_loop_iteration ON knowledge_gap_analysis(loop_id, iteration);
CREATE INDEX IF NOT EXISTS idx_gap_analysis_priority ON knowledge_gap_analysis(priority);
CREATE INDEX IF NOT EXISTS idx_gap_analysis_status ON knowledge_gap_analysis(status);

-- 建立註釋
COMMENT ON TABLE knowledge_gap_analysis IS '知識缺口分析結果';
COMMENT ON COLUMN knowledge_gap_analysis.failure_reason IS '失敗原因分類：no_match（無匹配）, low_confidence（低信心度）, semantic_mismatch（語義不匹配）, system_error（系統錯誤）';
COMMENT ON COLUMN knowledge_gap_analysis.priority IS '優先級：p0（高）、p1（中）、p2（低）';
COMMENT ON COLUMN knowledge_gap_analysis.loop_knowledge_id IS '關聯至 loop_generated_knowledge.id（生成知識後填入）';
COMMENT ON COLUMN knowledge_gap_analysis.suggested_action_type IS '建議的動作類型：knowledge（純知識）, form（表單）, api（API）';
COMMENT ON COLUMN knowledge_gap_analysis.frequency IS '相似問題的頻率（聚類後的問題數量）';
