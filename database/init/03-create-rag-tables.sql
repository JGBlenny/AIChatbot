-- RAG Orchestrator 相關表
-- 對話記錄和未釐清問題

-- 對話記錄表
CREATE TABLE IF NOT EXISTS conversation_logs (
    id SERIAL PRIMARY KEY,
    conversation_id UUID DEFAULT gen_random_uuid(),
    user_id VARCHAR(100),

    -- 問題
    question TEXT NOT NULL,
    intent_type VARCHAR(50),
    sub_category VARCHAR(100),
    keywords TEXT[],

    -- 檢索結果
    retrieved_docs JSONB,
    similarity_scores FLOAT[],
    confidence_score FLOAT,

    -- API 呼叫記錄
    api_called BOOLEAN DEFAULT false,
    api_endpoints TEXT[],
    api_responses JSONB,

    -- 答案
    final_answer TEXT,
    answer_source VARCHAR(50), -- 'knowledge', 'api', 'llm_enhanced', 'unclear'
    processing_time_ms INTEGER,

    -- 反饋
    user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 5),
    user_feedback TEXT,
    is_resolved BOOLEAN DEFAULT true,
    escalated_to_human BOOLEAN DEFAULT false,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 未釐清問題表
CREATE TABLE IF NOT EXISTS unclear_questions (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    user_id VARCHAR(100),
    intent_type VARCHAR(50),

    -- 檢索結果
    similarity_score FLOAT,
    retrieved_docs JSONB,

    -- 統計
    frequency INTEGER DEFAULT 1,
    first_asked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_asked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 處理狀態
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'resolved', 'ignored')),
    assigned_to VARCHAR(100),
    resolved_at TIMESTAMP,
    resolution_note TEXT,

    -- 建議答案
    suggested_answers TEXT[],

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_conv_user ON conversation_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_conv_intent ON conversation_logs(intent_type);
CREATE INDEX IF NOT EXISTS idx_conv_created ON conversation_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conv_confidence ON conversation_logs(confidence_score);

CREATE INDEX IF NOT EXISTS idx_unclear_status ON unclear_questions(status);
CREATE INDEX IF NOT EXISTS idx_unclear_frequency ON unclear_questions(frequency DESC);
CREATE INDEX IF NOT EXISTS idx_unclear_last_asked ON unclear_questions(last_asked_at DESC);

-- 註解
COMMENT ON TABLE conversation_logs IS 'RAG 系統對話記錄';
COMMENT ON TABLE unclear_questions IS '低信心度未釐清問題記錄';

COMMENT ON COLUMN conversation_logs.confidence_score IS '答案信心度分數 (0-1)';
COMMENT ON COLUMN conversation_logs.answer_source IS '答案來源: knowledge/api/llm_enhanced/unclear';
COMMENT ON COLUMN unclear_questions.frequency IS '問題被問次數';
COMMENT ON COLUMN unclear_questions.status IS '處理狀態: pending/in_progress/resolved/ignored';

-- 觸發器：更新 updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_unclear_questions_updated_at
    BEFORE UPDATE ON unclear_questions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 初始化成功訊息
DO $$
BEGIN
    RAISE NOTICE '✅ RAG Orchestrator 資料表建立完成';
    RAISE NOTICE '   - conversation_logs: 對話記錄';
    RAISE NOTICE '   - unclear_questions: 未釐清問題';
END $$;
