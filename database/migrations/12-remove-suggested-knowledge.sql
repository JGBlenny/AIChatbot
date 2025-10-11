-- ================================================
-- Migration: Remove suggested_knowledge feature
-- Purpose: Drop all database objects related to suggested_knowledge (now merged into ai_generated_knowledge_candidates)
-- Date: 2025-10-12
-- ================================================

-- Drop view first (depends on table)
DROP VIEW IF EXISTS v_knowledge_suggestions CASCADE;

-- Drop trigger (depends on function and table)
DROP TRIGGER IF EXISTS trigger_update_suggested_knowledge_updated_at ON suggested_knowledge;

-- Drop table (will also drop its indexes and constraints)
DROP TABLE IF EXISTS suggested_knowledge CASCADE;

-- Drop function (no longer needed)
DROP FUNCTION IF EXISTS update_suggested_knowledge_updated_at();

COMMIT;
