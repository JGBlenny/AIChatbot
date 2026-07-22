-- 修正 knowledge_base.intent_id 外鍵行為
-- 日期: 2026-04-14
-- 問題: FK 預設 NO ACTION，TRUNCATE intents CASCADE 會連帶清空 knowledge_base
-- 修正: 改為 ON DELETE SET NULL

ALTER TABLE knowledge_base
DROP CONSTRAINT IF EXISTS fk_knowledge_intent;

ALTER TABLE knowledge_base
DROP CONSTRAINT IF EXISTS knowledge_base_intent_id_fkey;

ALTER TABLE knowledge_base
ADD CONSTRAINT fk_knowledge_intent
FOREIGN KEY (intent_id)
REFERENCES intents(id)
ON DELETE SET NULL;

-- 同時修正 knowledge_import_jobs.target_intent_id
ALTER TABLE knowledge_import_jobs
DROP CONSTRAINT IF EXISTS knowledge_import_jobs_target_intent_id_fkey;

ALTER TABLE knowledge_import_jobs
ADD CONSTRAINT knowledge_import_jobs_target_intent_id_fkey
FOREIGN KEY (target_intent_id)
REFERENCES intents(id)
ON DELETE SET NULL;

-- 同時修正 suggested_intents.approved_intent_id
ALTER TABLE suggested_intents
DROP CONSTRAINT IF EXISTS suggested_intents_approved_intent_id_fkey;

ALTER TABLE suggested_intents
ADD CONSTRAINT suggested_intents_approved_intent_id_fkey
FOREIGN KEY (approved_intent_id)
REFERENCES intents(id)
ON DELETE SET NULL;
