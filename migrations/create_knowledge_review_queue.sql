-- 創建知識審核佇列表（不綁定測試情境）
-- 用途：一般知識的審核流程，區別於測試情境審核
-- 創建日期：2025-11-22

CREATE TABLE IF NOT EXISTS knowledge_review_queue (
    id SERIAL PRIMARY KEY,

    -- 基本資訊
    question_summary TEXT NOT NULL,
    answer TEXT NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'import',  -- 'import', 'ai_generation', 'manual'
    import_source VARCHAR(50),                     -- 'system_export', 'external_file', 'line_chat'

    -- 分類資訊
    scope VARCHAR(20) DEFAULT 'global',
    vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE,
    business_types TEXT[],
    target_user TEXT,
    keywords TEXT[],
    priority INTEGER DEFAULT 0,

    -- 意圖推薦
    recommended_intent_ids INTEGER[],
    intent_confidence NUMERIC(3,2),

    -- 質量評估
    quality_score INTEGER,                         -- 1-10
    quality_reasoning TEXT,
    warnings TEXT[],

    -- 向量嵌入
    question_embedding vector(1536),

    -- 審核狀態
    status VARCHAR(20) DEFAULT 'pending_review',
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    review_notes TEXT,

    -- 編輯記錄
    edited_question_summary TEXT,
    edited_answer TEXT,
    edit_summary TEXT,

    -- 時間戳記
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 約束
    CONSTRAINT check_krq_status CHECK (status IN ('pending_review', 'approved', 'rejected', 'edited')),
    CONSTRAINT check_krq_priority CHECK (priority >= 0 AND priority <= 10)
);

-- 索引
CREATE INDEX idx_krq_status ON knowledge_review_queue(status);
CREATE INDEX idx_krq_vendor ON knowledge_review_queue(vendor_id);
CREATE INDEX idx_krq_source ON knowledge_review_queue(import_source);
CREATE INDEX idx_krq_created ON knowledge_review_queue(created_at DESC);
CREATE INDEX idx_krq_reviewed ON knowledge_review_queue(reviewed_at DESC);

-- 向量相似度搜尋索引
CREATE INDEX idx_krq_embedding ON knowledge_review_queue
USING ivfflat (question_embedding vector_cosine_ops)
WITH (lists = 100);

-- 觸發器：自動更新 updated_at
CREATE OR REPLACE FUNCTION update_krq_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_krq_update_timestamp
    BEFORE UPDATE ON knowledge_review_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_krq_timestamp();

-- 註釋
COMMENT ON TABLE knowledge_review_queue IS '知識審核佇列（不綁定測試情境）';
COMMENT ON COLUMN knowledge_review_queue.import_source IS '匯入來源：system_export, external_file, line_chat';
COMMENT ON COLUMN knowledge_review_queue.status IS '審核狀態：pending_review, approved, rejected, edited';
COMMENT ON COLUMN knowledge_review_queue.quality_score IS '質量評估分數（1-10）';
