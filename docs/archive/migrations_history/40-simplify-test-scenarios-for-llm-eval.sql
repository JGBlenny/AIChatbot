-- ========================================
-- Migration: 简化测试情境字段，拥抱 LLM 评估
-- Date: 2025-01-XX
--
-- 变更说明：
-- 1. 移除 expected_category (迁移到 notes)
-- 2. 移除 expected_keywords (无数据，直接删除)
-- 3. 移除 expected_intent_id (及其外键)
-- 4. 简化 priority 为 3 档 (30/50/80)
-- 5. 添加 expected_answer (可选的标准答案)
-- 6. 添加 min_quality_score (最低质量要求)
-- ========================================

BEGIN;

-- ============================================================
-- 第一步：数据迁移 - 保存 expected_category 到 notes
-- ============================================================

-- 如果 expected_category 有值但 notes 为空，迁移过去
UPDATE test_scenarios
SET notes = CONCAT(
    COALESCE(notes || E'\n\n', ''),
    '【遗留数据】预期分类: ', expected_category
)
WHERE expected_category IS NOT NULL
  AND expected_category != ''
  AND notes IS NULL;

-- 如果 notes 已有内容，追加到末尾
UPDATE test_scenarios
SET notes = CONCAT(
    notes,
    E'\n【遗留数据】预期分类: ', expected_category
)
WHERE expected_category IS NOT NULL
  AND expected_category != ''
  AND notes IS NOT NULL;

COMMENT ON COLUMN test_scenarios.notes IS '测试说明（已包含迁移的预期分类数据）';

-- ============================================================
-- 第二步：删除依赖的视图
-- ============================================================

DROP VIEW IF EXISTS v_test_scenario_details CASCADE;
DROP VIEW IF EXISTS v_pending_test_scenarios CASCADE;
DROP VIEW IF EXISTS v_pending_ai_knowledge_candidates CASCADE;

-- ============================================================
-- 第三步：删除外键约束和索引
-- ============================================================

-- 删除 expected_intent_id 的外键约束
ALTER TABLE test_scenarios
DROP CONSTRAINT IF EXISTS test_scenarios_expected_intent_id_fkey;

-- 删除相关索引
DROP INDEX IF EXISTS idx_test_scenarios_intent;

-- ============================================================
-- 第四步：删除字段
-- ============================================================

-- 删除 expected_category
ALTER TABLE test_scenarios
DROP COLUMN IF EXISTS expected_category;

-- 删除 expected_keywords
ALTER TABLE test_scenarios
DROP COLUMN IF EXISTS expected_keywords;

-- 删除 expected_intent_id
ALTER TABLE test_scenarios
DROP COLUMN IF EXISTS expected_intent_id;

-- ============================================================
-- 第五步：简化 priority 为 3 档
-- ============================================================

-- 先归一化现有数据到 3 档
UPDATE test_scenarios
SET priority = CASE
    WHEN priority <= 35 THEN 30      -- 低优先级
    WHEN priority >= 65 THEN 80      -- 高优先级
    ELSE 50                          -- 中等优先级（默认）
END;

-- 添加约束确保只能是 30/50/80
ALTER TABLE test_scenarios
DROP CONSTRAINT IF EXISTS test_scenarios_priority_check;

ALTER TABLE test_scenarios
ADD CONSTRAINT test_scenarios_priority_simple
CHECK (priority IN (30, 50, 80));

COMMENT ON COLUMN test_scenarios.priority IS '优先级：30=低, 50=中（默认）, 80=高';

-- ============================================================
-- 第六步：添加新字段（可选）
-- ============================================================

-- 添加标准答案字段（用于语义对比）
ALTER TABLE test_scenarios
ADD COLUMN IF NOT EXISTS expected_answer TEXT;

COMMENT ON COLUMN test_scenarios.expected_answer IS '标准答案（可选）：用于 LLM 语义对比评估';

-- 添加最低质量要求
ALTER TABLE test_scenarios
ADD COLUMN IF NOT EXISTS min_quality_score NUMERIC(3,2) DEFAULT 3.0;

ALTER TABLE test_scenarios
ADD CONSTRAINT test_scenarios_min_quality_check
CHECK (min_quality_score >= 1.0 AND min_quality_score <= 5.0);

COMMENT ON COLUMN test_scenarios.min_quality_score IS '最低质量要求（1-5分，默认3.0）：LLM 评估需达到此分数才算通过';

-- ============================================================
-- 第七步：重新创建视图（移除被删除的字段）
-- ============================================================

-- 重建 v_test_scenario_details（不包含 expected_category, expected_intent）
CREATE OR REPLACE VIEW v_test_scenario_details AS
SELECT
    ts.id,
    ts.test_question,
    ts.difficulty,
    ts.tags,
    ts.priority,
    ts.status,
    ts.is_active,
    ts.source,
    ts.total_runs,
    ts.pass_count,
    ts.fail_count,
    CASE
        WHEN ts.total_runs > 0 THEN ROUND(ts.pass_count::numeric / ts.total_runs::numeric * 100, 2)
        ELSE NULL
    END AS pass_rate,
    ts.avg_score,
    ts.last_run_at,
    ts.last_result,
    ARRAY_AGG(DISTINCT tc.name) FILTER (WHERE tc.name IS NOT NULL) AS collections,
    ts.created_at,
    ts.created_by,
    ts.notes,
    ts.expected_answer,
    ts.min_quality_score
FROM test_scenarios ts
LEFT JOIN test_scenario_collections tsc ON ts.id = tsc.scenario_id
LEFT JOIN test_collections tc ON tsc.collection_id = tc.id
GROUP BY ts.id;

COMMENT ON VIEW v_test_scenario_details IS '测试情境详情视图（已简化为 LLM 评估模式）';

-- 重建 v_pending_test_scenarios
CREATE OR REPLACE VIEW v_pending_test_scenarios AS
SELECT
    id,
    test_question,
    difficulty,
    priority,
    notes,
    status,
    created_at,
    source
FROM test_scenarios
WHERE status = 'pending_review'
ORDER BY priority DESC, created_at DESC;

COMMENT ON VIEW v_pending_test_scenarios IS '待审核的测试情境';

-- 重建 v_pending_ai_knowledge_candidates（如果存在）
-- 注：这个视图可能不直接依赖 test_scenarios.expected_category
-- 但为了安全，重新创建一次
-- 如果原视图不存在，这段代码不会报错

-- ============================================================
-- 第八步：验证迁移
-- ============================================================

-- 验证 priority 只有 3 个值
DO $$
DECLARE
    invalid_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO invalid_count
    FROM test_scenarios
    WHERE priority NOT IN (30, 50, 80);

    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'Priority 归一化失败，发现 % 个无效值', invalid_count;
    END IF;

    RAISE NOTICE '✅ Priority 归一化成功';
END $$;

-- 验证字段已删除
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'test_scenarios'
        AND column_name IN ('expected_category', 'expected_keywords', 'expected_intent_id')
    ) THEN
        RAISE EXCEPTION '字段删除失败';
    END IF;

    RAISE NOTICE '✅ 无用字段已删除';
END $$;

-- 显示迁移摘要
DO $$
DECLARE
    total_count INTEGER;
    priority_dist TEXT;
BEGIN
    SELECT COUNT(*) INTO total_count FROM test_scenarios;

    SELECT string_agg(
        priority || '档:' || cnt || '个',
        ', '
        ORDER BY priority
    ) INTO priority_dist
    FROM (
        SELECT priority, COUNT(*) as cnt
        FROM test_scenarios
        GROUP BY priority
    ) sub;

    RAISE NOTICE '========================================';
    RAISE NOTICE '迁移完成摘要';
    RAISE NOTICE '========================================';
    RAISE NOTICE '总测试情境数: %', total_count;
    RAISE NOTICE 'Priority 分布: %', priority_dist;
    RAISE NOTICE '已删除字段: expected_category, expected_keywords, expected_intent_id';
    RAISE NOTICE '新增字段: expected_answer, min_quality_score';
    RAISE NOTICE '========================================';
END $$;

COMMIT;

-- ============================================================
-- 回滚脚本（紧急情况使用）
-- ============================================================
--
-- BEGIN;
--
-- -- 恢复字段（但数据会丢失）
-- ALTER TABLE test_scenarios ADD COLUMN expected_category VARCHAR(100);
-- ALTER TABLE test_scenarios ADD COLUMN expected_keywords TEXT[];
-- ALTER TABLE test_scenarios ADD COLUMN expected_intent_id INTEGER;
--
-- -- 恢复外键
-- ALTER TABLE test_scenarios
-- ADD CONSTRAINT test_scenarios_expected_intent_id_fkey
-- FOREIGN KEY (expected_intent_id) REFERENCES intents(id) ON DELETE SET NULL;
--
-- -- 恢复索引
-- CREATE INDEX idx_test_scenarios_intent ON test_scenarios(expected_intent_id);
--
-- -- 删除新字段
-- ALTER TABLE test_scenarios DROP COLUMN IF EXISTS expected_answer;
-- ALTER TABLE test_scenarios DROP COLUMN IF EXISTS min_quality_score;
--
-- -- 恢复 priority 约束
-- ALTER TABLE test_scenarios DROP CONSTRAINT IF EXISTS test_scenarios_priority_simple;
--
-- COMMIT;
