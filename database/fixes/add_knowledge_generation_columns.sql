-- 添加 AI 知識生成所需的欄位
-- 用途：支援從測試情境自動生成知識庫候選內容

-- 1. 擴展 test_scenarios 表：追蹤是否有對應知識
ALTER TABLE test_scenarios
ADD COLUMN IF NOT EXISTS has_knowledge BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS linked_knowledge_ids INTEGER[],
ADD COLUMN IF NOT EXISTS knowledge_generation_requested BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS knowledge_generation_requested_at TIMESTAMP;

COMMENT ON COLUMN test_scenarios.has_knowledge IS '是否已有對應的知識庫內容';
COMMENT ON COLUMN test_scenarios.linked_knowledge_ids IS '關聯的知識 ID 陣列';
COMMENT ON COLUMN test_scenarios.knowledge_generation_requested IS '是否已請求 AI 生成知識';
COMMENT ON COLUMN test_scenarios.knowledge_generation_requested_at IS 'AI 生成請求時間';

-- 2. 擴展 knowledge_base 表：標註知識來源
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) DEFAULT 'manual',
ADD COLUMN IF NOT EXISTS source_test_scenario_id INTEGER REFERENCES test_scenarios(id),
ADD COLUMN IF NOT EXISTS generation_metadata JSONB,
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

COMMENT ON COLUMN knowledge_base.source_type IS '知識來源類型: manual (人工), ai_generated (AI生成), imported (匯入), ai_assisted (AI輔助)';
COMMENT ON COLUMN knowledge_base.source_test_scenario_id IS '來源測試情境 ID（如果由測試情境生成）';
COMMENT ON COLUMN knowledge_base.generation_metadata IS 'AI 生成的詳細資訊: {model, prompt, confidence, reviewed_by, edited}';
COMMENT ON COLUMN knowledge_base.is_active IS '知識是否啟用';

-- 3. 建立 AI 生成知識候選表（審核前的暫存區）
CREATE TABLE IF NOT EXISTS ai_generated_knowledge_candidates (
    id SERIAL PRIMARY KEY,
    test_scenario_id INTEGER NOT NULL REFERENCES test_scenarios(id) ON DELETE CASCADE,

    -- 生成內容
    question TEXT NOT NULL,
    generated_answer TEXT NOT NULL,
    confidence_score DECIMAL(3,2),  -- AI 生成的信心度 (0.00-1.00)

    -- 生成詳情
    generation_prompt TEXT,         -- 使用的 prompt
    ai_model VARCHAR(50),            -- 使用的模型 (gpt-4, gpt-3.5-turbo)
    generation_reasoning TEXT,       -- AI 的推理過程
    suggested_sources TEXT[],        -- AI 建議的參考來源
    warnings TEXT[],                 -- AI 標註的風險警告

    -- 審核狀態
    status VARCHAR(20) DEFAULT 'pending_review',
    -- pending_review: 待審核
    -- needs_revision: 需要修訂
    -- approved: 已批准（轉為正式知識）
    -- rejected: 已拒絕

    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    review_notes TEXT,

    -- 編輯記錄
    edited_question TEXT,            -- 審核者編輯後的問題
    edited_answer TEXT,              -- 審核者編輯後的答案
    edit_summary TEXT,               -- 編輯摘要（記錄主要修改）

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_candidates_test_scenario ON ai_generated_knowledge_candidates(test_scenario_id);
CREATE INDEX IF NOT EXISTS idx_ai_candidates_status ON ai_generated_knowledge_candidates(status);
CREATE INDEX IF NOT EXISTS idx_ai_candidates_created ON ai_generated_knowledge_candidates(created_at DESC);

COMMENT ON TABLE ai_generated_knowledge_candidates IS 'AI 生成的知識候選（審核前暫存）';
