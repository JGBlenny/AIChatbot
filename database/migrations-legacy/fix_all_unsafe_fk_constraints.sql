-- 修正所有不合理的 FK 約束
-- 日期: 2026-04-14
-- 原則: 主資料表（knowledge_base 等）不應因清除參考資料而被影響
-- 所有 NO ACTION 改為 SET NULL

-- ============================================
-- 1. knowledge_base 的 FK
-- ============================================

-- intent_id → intents
ALTER TABLE knowledge_base DROP CONSTRAINT IF EXISTS fk_knowledge_intent;
ALTER TABLE knowledge_base DROP CONSTRAINT IF EXISTS knowledge_base_intent_id_fkey;
ALTER TABLE knowledge_base ADD CONSTRAINT fk_knowledge_intent
  FOREIGN KEY (intent_id) REFERENCES intents(id) ON DELETE SET NULL;

-- source_loop_id → knowledge_completion_loops
ALTER TABLE knowledge_base DROP CONSTRAINT IF EXISTS knowledge_base_source_loop_id_fkey;
ALTER TABLE knowledge_base ADD CONSTRAINT knowledge_base_source_loop_id_fkey
  FOREIGN KEY (source_loop_id) REFERENCES knowledge_completion_loops(id) ON DELETE SET NULL;

-- source_loop_knowledge_id → loop_generated_knowledge
ALTER TABLE knowledge_base DROP CONSTRAINT IF EXISTS knowledge_base_source_loop_knowledge_id_fkey;
ALTER TABLE knowledge_base ADD CONSTRAINT knowledge_base_source_loop_knowledge_id_fkey
  FOREIGN KEY (source_loop_knowledge_id) REFERENCES loop_generated_knowledge(id) ON DELETE SET NULL;

-- ============================================
-- 2. knowledge_import_jobs.target_intent_id
-- ============================================

ALTER TABLE knowledge_import_jobs DROP CONSTRAINT IF EXISTS knowledge_import_jobs_target_intent_id_fkey;
ALTER TABLE knowledge_import_jobs ADD CONSTRAINT knowledge_import_jobs_target_intent_id_fkey
  FOREIGN KEY (target_intent_id) REFERENCES intents(id) ON DELETE SET NULL;

-- ============================================
-- 3. suggested_intents.approved_intent_id
-- ============================================

ALTER TABLE suggested_intents DROP CONSTRAINT IF EXISTS suggested_intents_approved_intent_id_fkey;
ALTER TABLE suggested_intents ADD CONSTRAINT suggested_intents_approved_intent_id_fkey
  FOREIGN KEY (approved_intent_id) REFERENCES intents(id) ON DELETE SET NULL;

-- ============================================
-- 4. form_sessions.form_id
-- ============================================

ALTER TABLE form_sessions DROP CONSTRAINT IF EXISTS form_sessions_form_id_fkey;
ALTER TABLE form_sessions ADD CONSTRAINT form_sessions_form_id_fkey
  FOREIGN KEY (form_id) REFERENCES form_schemas(form_id) ON DELETE SET NULL;

-- ============================================
-- 5. form_submissions.form_session_id
-- ============================================

ALTER TABLE form_submissions DROP CONSTRAINT IF EXISTS form_submissions_form_session_id_fkey;
ALTER TABLE form_submissions ADD CONSTRAINT form_submissions_form_session_id_fkey
  FOREIGN KEY (form_session_id) REFERENCES form_sessions(id) ON DELETE SET NULL;

-- ============================================
-- 6. backtest_manual_reviews.backtest_result_id
-- ============================================

ALTER TABLE backtest_manual_reviews DROP CONSTRAINT IF EXISTS backtest_manual_reviews_backtest_result_id_fkey;
ALTER TABLE backtest_manual_reviews ADD CONSTRAINT backtest_manual_reviews_backtest_result_id_fkey
  FOREIGN KEY (backtest_result_id) REFERENCES backtest_results(id) ON DELETE SET NULL;

-- ============================================
-- 7. loop_generated_knowledge.gap_analysis_id
-- ============================================

ALTER TABLE loop_generated_knowledge DROP CONSTRAINT IF EXISTS loop_generated_knowledge_gap_analysis_id_fkey;
ALTER TABLE loop_generated_knowledge ADD CONSTRAINT loop_generated_knowledge_gap_analysis_id_fkey
  FOREIGN KEY (gap_analysis_id) REFERENCES knowledge_gap_analysis(id) ON DELETE SET NULL;

-- ============================================
-- 8. knowledge_completion_loops.parent_loop_id
-- ============================================

ALTER TABLE knowledge_completion_loops DROP CONSTRAINT IF EXISTS knowledge_completion_loops_parent_loop_id_fkey;
ALTER TABLE knowledge_completion_loops ADD CONSTRAINT knowledge_completion_loops_parent_loop_id_fkey
  FOREIGN KEY (parent_loop_id) REFERENCES knowledge_completion_loops(id) ON DELETE SET NULL;
