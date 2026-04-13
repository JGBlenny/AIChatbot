-- 修正 knowledge_base.source_test_scenario_id 外鍵行為
-- 日期: 2026-04-13
-- 問題: FK 預設 NO ACTION，TRUNCATE test_scenarios CASCADE 會連帶清空 knowledge_base
-- 修正: 改為 ON DELETE SET NULL，刪除 test_scenarios 時只清引用欄位

-- 移除舊的 FK（可能有不同名稱）
ALTER TABLE knowledge_base
DROP CONSTRAINT IF EXISTS fk_knowledge_source_test_scenario;

ALTER TABLE knowledge_base
DROP CONSTRAINT IF EXISTS knowledge_base_source_test_scenario_id_fkey;

-- 重建 FK with ON DELETE SET NULL
ALTER TABLE knowledge_base
ADD CONSTRAINT fk_knowledge_source_test_scenario
FOREIGN KEY (source_test_scenario_id)
REFERENCES test_scenarios(id)
ON DELETE SET NULL;
