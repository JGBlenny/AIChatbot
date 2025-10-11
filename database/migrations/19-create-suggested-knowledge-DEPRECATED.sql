-- ================================================
-- Migration: Create suggested_knowledge table
-- Purpose: Store AI-generated knowledge suggestions from unclear questions
-- Date: 2025-10-11
-- ================================================

-- Drop existing objects if they exist
DROP VIEW IF EXISTS v_knowledge_suggestions CASCADE;
DROP TABLE IF EXISTS suggested_knowledge CASCADE;

-- ================================================
-- Create suggested_knowledge table
-- ================================================
CREATE TABLE suggested_knowledge (
    id SERIAL PRIMARY KEY,

    -- Source unclear question
    source_unclear_question_id INTEGER REFERENCES unclear_questions(id) ON DELETE SET NULL,

    -- AI-generated suggestion
    suggested_question TEXT NOT NULL,
    suggested_answer TEXT NOT NULL,
    suggested_category VARCHAR(100),
    suggested_keywords TEXT[],

    -- Business scope validation
    is_in_business_scope BOOLEAN DEFAULT FALSE,
    scope_reasoning TEXT,

    -- AI confidence score (0.00 - 1.00)
    ai_confidence DECIMAL(3,2) CHECK (ai_confidence >= 0 AND ai_confidence <= 1),

    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'edited')),

    -- Review information
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    review_notes TEXT,

    -- Link to created knowledge base entry (when approved)
    knowledge_id INTEGER REFERENCES knowledge_base(id) ON DELETE SET NULL,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ================================================
-- Create indexes for performance
-- ================================================
CREATE INDEX idx_suggested_knowledge_status ON suggested_knowledge(status);
CREATE INDEX idx_suggested_knowledge_source ON suggested_knowledge(source_unclear_question_id);
CREATE INDEX idx_suggested_knowledge_scope ON suggested_knowledge(is_in_business_scope);
CREATE INDEX idx_suggested_knowledge_created_at ON suggested_knowledge(created_at DESC);
CREATE INDEX idx_suggested_knowledge_knowledge_id ON suggested_knowledge(knowledge_id);

-- ================================================
-- Create view for easy querying with related data
-- ================================================
CREATE VIEW v_knowledge_suggestions AS
SELECT
    sk.id,
    sk.suggested_question,
    sk.suggested_answer,
    sk.suggested_category,
    sk.suggested_keywords,
    sk.is_in_business_scope,
    sk.scope_reasoning,
    sk.ai_confidence,
    sk.status,
    sk.reviewed_by,
    sk.reviewed_at,
    sk.review_notes,
    sk.knowledge_id,
    sk.created_at,
    sk.updated_at,

    -- Source unclear question data
    uq.question AS source_question,
    uq.user_question AS source_user_question,
    uq.created_at AS source_created_at,

    -- Created knowledge base data (if approved)
    kb.question AS kb_question,
    kb.answer AS kb_answer,
    kb.category AS kb_category,
    kb.vendor_id AS kb_vendor_id
FROM
    suggested_knowledge sk
LEFT JOIN
    unclear_questions uq ON sk.source_unclear_question_id = uq.id
LEFT JOIN
    knowledge_base kb ON sk.knowledge_id = kb.id;

-- ================================================
-- Create function to automatically update updated_at
-- ================================================
CREATE OR REPLACE FUNCTION update_suggested_knowledge_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ================================================
-- Create trigger for auto-updating updated_at
-- ================================================
CREATE TRIGGER trigger_update_suggested_knowledge_updated_at
    BEFORE UPDATE ON suggested_knowledge
    FOR EACH ROW
    EXECUTE FUNCTION update_suggested_knowledge_updated_at();

-- ================================================
-- Add comments for documentation
-- ================================================
COMMENT ON TABLE suggested_knowledge IS 'Stores AI-generated knowledge suggestions from unclear questions for manager review';
COMMENT ON COLUMN suggested_knowledge.source_unclear_question_id IS 'Reference to the unclear question that triggered this suggestion';
COMMENT ON COLUMN suggested_knowledge.is_in_business_scope IS 'Whether the question is within the business scope (包租代管業務)';
COMMENT ON COLUMN suggested_knowledge.scope_reasoning IS 'AI reasoning for the business scope judgment';
COMMENT ON COLUMN suggested_knowledge.ai_confidence IS 'AI confidence score for the generated answer (0.00-1.00)';
COMMENT ON COLUMN suggested_knowledge.status IS 'Suggestion status: pending, approved, rejected, edited';
COMMENT ON COLUMN suggested_knowledge.knowledge_id IS 'Reference to the created knowledge base entry when approved';

-- ================================================
-- Insert sample data for testing (optional)
-- ================================================
-- Note: This requires unclear_questions table to have data
-- Uncomment below if you want to insert test data

/*
-- Example: Insert a test suggestion
INSERT INTO suggested_knowledge (
    source_unclear_question_id,
    suggested_question,
    suggested_answer,
    suggested_category,
    suggested_keywords,
    is_in_business_scope,
    scope_reasoning,
    ai_confidence,
    status
) VALUES (
    NULL, -- Set to actual unclear_question id if available
    '租客可以提前解約嗎？',
    '根據租約規定，租客可以提前解約，但需要提前一個月通知，並且可能需要支付違約金。具體金額依照合約條款而定。',
    '租約管理',
    ARRAY['提前解約', '違約金', '租約', '通知期'],
    TRUE,
    '此問題涉及租賃管理中的解約流程，屬於包租代管業務範圍',
    0.85,
    'pending'
);
*/

COMMIT;
