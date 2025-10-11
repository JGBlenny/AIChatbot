-- ============================================================
-- Migration: Deprecate Collection Tables
-- Purpose: Mark test collection tables as deprecated
-- Date: 2025-10-11
-- Reason: Collections over-engineered for small test set
--         Replaced with score-based prioritization
-- ============================================================

-- Add comments to mark tables as deprecated
COMMENT ON TABLE test_collections IS
'DEPRECATED: Collection functionality removed in favor of score-based test prioritization.
Table kept for historical data only. Created: 2025-10-11';

COMMENT ON TABLE test_scenario_collections IS
'DEPRECATED: Collection functionality removed in favor of score-based test prioritization.
Table kept for historical data only. Created: 2025-10-11';

COMMENT ON VIEW v_test_collection_summary IS
'DEPRECATED: Collection functionality removed. View kept for backward compatibility only.';

-- Note: We keep the tables and data for historical reference
-- but they are no longer used in the application

-- Update test_scenarios table comment to reflect new prioritization
COMMENT ON TABLE test_scenarios IS
'Test scenarios for RAG system backtesting.
Prioritization now based on fail_rate and avg_score instead of collections.
Updated: 2025-10-11';

-- Document the new prioritization strategy in column comments
COMMENT ON COLUMN test_scenarios.total_runs IS 'Total number of test executions (used for fail rate calculation)';
COMMENT ON COLUMN test_scenarios.pass_count IS 'Number of passing test executions (used for fail rate calculation)';
COMMENT ON COLUMN test_scenarios.fail_count IS 'Number of failing test executions (used for fail rate calculation)';
COMMENT ON COLUMN test_scenarios.avg_score IS 'Average score across all test runs (lower scores prioritized in testing)';
COMMENT ON COLUMN test_scenarios.priority IS 'Manual priority override (1-100, higher = more important)';
