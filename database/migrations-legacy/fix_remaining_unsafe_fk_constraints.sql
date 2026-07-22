-- 修正剩餘不合理的 FK 約束
-- 日期: 2026-04-14

-- ============================================
-- 1. intents 相關
-- ============================================

-- knowledge_intent_mapping.intent_id：刪意圖不該刪知識 mapping
ALTER TABLE knowledge_intent_mapping DROP CONSTRAINT IF EXISTS fk_intent;
ALTER TABLE knowledge_intent_mapping DROP CONSTRAINT IF EXISTS knowledge_intent_mapping_intent_id_fkey;
ALTER TABLE knowledge_intent_mapping ADD CONSTRAINT knowledge_intent_mapping_intent_id_fkey
  FOREIGN KEY (intent_id) REFERENCES intents(id) ON DELETE SET NULL;

-- ============================================
-- 2. platform_sop_templates 相關
-- ============================================

-- vendor_sop_overrides.template_id：刪模板不該刪業者覆寫紀錄
ALTER TABLE vendor_sop_overrides DROP CONSTRAINT IF EXISTS vendor_sop_overrides_template_id_fkey;
ALTER TABLE vendor_sop_overrides ADD CONSTRAINT vendor_sop_overrides_template_id_fkey
  FOREIGN KEY (template_id) REFERENCES platform_sop_templates(id) ON DELETE SET NULL;

-- ============================================
-- 3. vendors 相關（紀錄性質改 SET NULL）
-- ============================================

-- ai_generated_knowledge_candidates.vendor_id
ALTER TABLE ai_generated_knowledge_candidates DROP CONSTRAINT IF EXISTS ai_generated_knowledge_candidates_vendor_id_fkey;
ALTER TABLE ai_generated_knowledge_candidates ADD CONSTRAINT ai_generated_knowledge_candidates_vendor_id_fkey
  FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE SET NULL;

-- knowledge_import_jobs.vendor_id
ALTER TABLE knowledge_import_jobs DROP CONSTRAINT IF EXISTS knowledge_import_jobs_vendor_id_fkey;
ALTER TABLE knowledge_import_jobs ADD CONSTRAINT knowledge_import_jobs_vendor_id_fkey
  FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE SET NULL;

-- knowledge_review_queue.vendor_id
ALTER TABLE knowledge_review_queue DROP CONSTRAINT IF EXISTS knowledge_review_queue_vendor_id_fkey;
ALTER TABLE knowledge_review_queue ADD CONSTRAINT knowledge_review_queue_vendor_id_fkey
  FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE SET NULL;

-- unified_jobs.vendor_id
ALTER TABLE unified_jobs DROP CONSTRAINT IF EXISTS unified_jobs_vendor_id_fkey;
ALTER TABLE unified_jobs ADD CONSTRAINT unified_jobs_vendor_id_fkey
  FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE SET NULL;
