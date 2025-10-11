-- ================================================
-- Migration: Add source tracking to knowledge_candidates
-- Purpose: Track the source of knowledge candidates (test_scenario or unclear_question)
-- Date: 2025-10-12
-- ================================================

-- Add source tracking columns to ai_generated_knowledge_candidates
ALTER TABLE ai_generated_knowledge_candidates
ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) DEFAULT 'test_scenario'
    CHECK (source_type IN ('test_scenario', 'unclear_question', 'manual')),
ADD COLUMN IF NOT EXISTS source_unclear_question_id INTEGER REFERENCES unclear_questions(id) ON DELETE SET NULL;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_ai_knowledge_candidates_source_type
    ON ai_generated_knowledge_candidates(source_type);

CREATE INDEX IF NOT EXISTS idx_ai_knowledge_candidates_source_unclear
    ON ai_generated_knowledge_candidates(source_unclear_question_id);

-- Add comments
COMMENT ON COLUMN ai_generated_knowledge_candidates.source_type IS 'Source of the candidate: test_scenario, unclear_question, or manual';
COMMENT ON COLUMN ai_generated_knowledge_candidates.source_unclear_question_id IS 'Reference to unclear_question if source_type is unclear_question';

-- Update existing records to have source_type = 'test_scenario'
UPDATE ai_generated_knowledge_candidates
SET source_type = 'test_scenario'
WHERE source_type IS NULL;

COMMIT;
