-- 修改 knowledge_base 的 loop 相關 FK 為 ON DELETE SET NULL
-- 並放寬 check_loop_source，允許迴圈刪除後知識保留
--
-- 背景：清除迴圈資料時，知識應保留，FK 和 CHECK 不應阻擋刪除

BEGIN;

-- 1. FK: source_loop_id → ON DELETE SET NULL
ALTER TABLE knowledge_base DROP CONSTRAINT knowledge_base_source_loop_id_fkey;
ALTER TABLE knowledge_base ADD CONSTRAINT knowledge_base_source_loop_id_fkey
  FOREIGN KEY (source_loop_id) REFERENCES knowledge_completion_loops(id) ON DELETE SET NULL;

-- 2. FK: source_loop_knowledge_id → ON DELETE SET NULL
ALTER TABLE knowledge_base DROP CONSTRAINT knowledge_base_source_loop_knowledge_id_fkey;
ALTER TABLE knowledge_base ADD CONSTRAINT knowledge_base_source_loop_knowledge_id_fkey
  FOREIGN KEY (source_loop_knowledge_id) REFERENCES loop_generated_knowledge(id) ON DELETE SET NULL;

-- 3. CHECK: 允許 source='loop' 時引用為 NULL（迴圈已刪除但知識保留）
ALTER TABLE knowledge_base DROP CONSTRAINT check_loop_source;
ALTER TABLE knowledge_base ADD CONSTRAINT check_loop_source
  CHECK (
    ((source)::text <> 'loop'::text AND source_loop_id IS NULL AND source_loop_knowledge_id IS NULL)
    OR ((source)::text = 'loop'::text)
  );

COMMIT;
