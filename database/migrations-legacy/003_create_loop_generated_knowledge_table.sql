-- Migration: 建立知識庫完善迴圈系統 - 迴圈生成知識表
-- 日期: 2026-03-21
-- 任務: 1.3 建立迴圈生成知識資料表
-- 用途: 儲存迴圈生成的臨時知識（與正式知識庫隔離）

CREATE TABLE IF NOT EXISTS loop_generated_knowledge (
    id SERIAL PRIMARY KEY,
    loop_id INT NOT NULL REFERENCES knowledge_completion_loops(id) ON DELETE CASCADE,
    iteration INT NOT NULL,
    gap_analysis_id INT REFERENCES knowledge_gap_analysis(id),

    -- 知識內容（與 knowledge_base 欄位完全一致，確保同步無資料遺失）
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    action_type VARCHAR(50) DEFAULT 'direct_answer',
    form_id VARCHAR(100),
    api_config JSONB,
    intent_id INT,
    keywords TEXT[],
    embedding VECTOR(1536),  -- OpenAI text-embedding-ada-002
    business_types TEXT[],
    target_user VARCHAR(50),
    scope VARCHAR(50),
    priority INT,

    -- 生命週期狀態
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, approved, rejected, synced, rolled_back
    synced_to_kb BOOLEAN DEFAULT false,
    kb_id INT,  -- 同步後的 knowledge_base.id

    -- 回滾資訊
    rolled_back BOOLEAN DEFAULT false,
    rollback_reason TEXT,
    rollback_at TIMESTAMP,
    rollback_by VARCHAR(100),

    -- 審核資訊
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    synced_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),

    -- CHECK 約束
    CONSTRAINT check_status CHECK (status IN ('pending', 'approved', 'rejected', 'synced', 'rolled_back')),
    CONSTRAINT check_action_type CHECK (action_type IN ('direct_answer', 'form_fill', 'api_call', 'form_then_api'))
);

-- 建立一般索引
CREATE INDEX IF NOT EXISTS idx_loop_knowledge_loop_iteration ON loop_generated_knowledge(loop_id, iteration);
CREATE INDEX IF NOT EXISTS idx_loop_knowledge_status ON loop_generated_knowledge(status);
CREATE INDEX IF NOT EXISTS idx_loop_knowledge_kb_id ON loop_generated_knowledge(kb_id);

-- 建立向量索引（HNSW）
CREATE INDEX IF NOT EXISTS idx_loop_knowledge_embedding ON loop_generated_knowledge
USING hnsw (embedding vector_cosine_ops);

-- 建立 GIN 索引（keywords, business_types）
CREATE INDEX IF NOT EXISTS idx_loop_knowledge_keywords ON loop_generated_knowledge USING GIN(keywords);
CREATE INDEX IF NOT EXISTS idx_loop_knowledge_business_types ON loop_generated_knowledge USING GIN(business_types);

-- 建立註釋
COMMENT ON TABLE loop_generated_knowledge IS '迴圈生成的臨時知識（與正式知識庫隔離）';
COMMENT ON COLUMN loop_generated_knowledge.status IS '知識生命週期狀態：pending → approved/rejected → synced/rolled_back';
COMMENT ON COLUMN loop_generated_knowledge.synced_to_kb IS '是否已同步到 knowledge_base 表';
COMMENT ON COLUMN loop_generated_knowledge.kb_id IS '同步後的 knowledge_base.id（追溯用）';
COMMENT ON COLUMN loop_generated_knowledge.embedding IS 'OpenAI text-embedding-ada-002 向量（1536 維）';
COMMENT ON COLUMN loop_generated_knowledge.action_type IS '回應類型：direct_answer, form_fill, api_call, form_then_api';
COMMENT ON COLUMN loop_generated_knowledge.rolled_back IS '是否已回滾';
COMMENT ON COLUMN loop_generated_knowledge.rollback_reason IS '回滾原因（如回測品質問題）';
