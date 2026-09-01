-- ========================================
-- 添加 vendor_sop_groups.group_embedding 字段
-- 用途：为 SOP Group 隔离检索提供独立的 Group 向量
-- 创建日期：2025-12-04
-- ========================================

-- 步骤 1: 添加 group_embedding 字段（允许 NULL，因为需要后续生成）
ALTER TABLE vendor_sop_groups
ADD COLUMN IF NOT EXISTS group_embedding vector(1536);

-- 步骤 2: 为 group_embedding 创建向量索引（提升检索性能）
-- ⚠️ 2026-09-01：原為 IVFFlat `lists=100`。實測該參數在小資料量下**靜默漏召回**
--    （knowledge_base 992 筆向量 ⇒ 每 list 約 10 筆、probes 預設 1 且全 repo 從未設定
--     ⇒ top-20 候選池召回率 31%、top-1 與精確掃描不同 46%，且**不會報錯**）。
--    改用 HNSW：⛔ 沒有 lists／probes 可以配錯，召回率不隨資料量崩塌。
--    證據 .kiro/specs/conversational-routing-execution/ivfflat-index-defect.md
CREATE INDEX IF NOT EXISTS idx_vendor_sop_groups_group_embedding
ON vendor_sop_groups
USING hnsw (group_embedding vector_cosine_ops);

-- 步骤 3: 添加注释
COMMENT ON COLUMN vendor_sop_groups.group_embedding IS 'Group 名称的向量表示，用于 Group 隔离检索的第一阶段（Group 识别）';

-- 步骤 4: 验证迁移结果
DO $$
DECLARE
    total_groups INTEGER;
    with_embedding INTEGER;
BEGIN
    -- 统计 Group 总数
    SELECT COUNT(*) INTO total_groups
    FROM vendor_sop_groups
    WHERE is_active = TRUE;

    -- 统计已有 embedding 的 Group 数量
    SELECT COUNT(*) INTO with_embedding
    FROM vendor_sop_groups
    WHERE is_active = TRUE AND group_embedding IS NOT NULL;

    -- 输出统计信息
    RAISE NOTICE '========================================';
    RAISE NOTICE '✅ group_embedding 字段添加成功';
    RAISE NOTICE '========================================';
    RAISE NOTICE '📊 当前统计：';
    RAISE NOTICE '   - 活跃 Group 总数: %', total_groups;
    RAISE NOTICE '   - 已有 embedding: %', with_embedding;
    RAISE NOTICE '   - 需要生成 embedding: %', total_groups - with_embedding;
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  下一步操作：';
    RAISE NOTICE '   运行脚本生成 Group Embeddings：';
    RAISE NOTICE '   python3 scripts/generate_group_embeddings.py';
    RAISE NOTICE '========================================';
END $$;
