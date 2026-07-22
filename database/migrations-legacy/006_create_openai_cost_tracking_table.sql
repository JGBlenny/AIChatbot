-- Migration: 建立 OpenAI 成本追蹤資料表
-- 日期: 2026-03-21
-- 任務: 1.6 建立成本追蹤資料表
-- 用途: 記錄所有 OpenAI API 呼叫的 token 使用量與成本

CREATE TABLE IF NOT EXISTS openai_cost_tracking (
    id SERIAL PRIMARY KEY,
    loop_id INT NOT NULL REFERENCES knowledge_completion_loops(id) ON DELETE CASCADE,

    -- API 呼叫資訊
    operation VARCHAR(50) NOT NULL,  -- knowledge_generation, action_type_classification
    model VARCHAR(50) NOT NULL,  -- gpt-3.5-turbo, gpt-4o-mini, gpt-4o

    -- Token 使用量
    prompt_tokens INT NOT NULL,
    completion_tokens INT NOT NULL,

    -- 成本（USD）
    cost_usd NUMERIC(10, 6) NOT NULL,

    -- 時間戳記
    created_at TIMESTAMP DEFAULT NOW()
);

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_cost_loop_id ON openai_cost_tracking(loop_id);
CREATE INDEX IF NOT EXISTS idx_cost_created_at ON openai_cost_tracking(created_at);

-- 建立註釋
COMMENT ON TABLE openai_cost_tracking IS 'OpenAI API 呼叫成本追蹤記錄';
COMMENT ON COLUMN openai_cost_tracking.operation IS 'API 呼叫類型：knowledge_generation（知識生成）、action_type_classification（動作類型分類）';
COMMENT ON COLUMN openai_cost_tracking.model IS 'OpenAI 模型名稱：gpt-3.5-turbo, gpt-4o-mini, gpt-4o';
COMMENT ON COLUMN openai_cost_tracking.cost_usd IS 'API 呼叫成本（美元，精度 6 位小數）';
