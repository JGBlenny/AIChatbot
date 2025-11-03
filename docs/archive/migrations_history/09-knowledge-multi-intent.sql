-- ============================================================
-- 知識庫多意圖支援
-- 創建日期: 2025-10-11
-- 目的: 支援一筆知識關聯多個意圖
-- ============================================================

-- 1. 創建知識-意圖關聯表
CREATE TABLE IF NOT EXISTS knowledge_intent_mapping (
    id SERIAL PRIMARY KEY,
    knowledge_id INT NOT NULL,
    intent_id INT NOT NULL,
    intent_type VARCHAR(20) NOT NULL DEFAULT 'secondary', -- 'primary' 或 'secondary'
    confidence FLOAT DEFAULT 1.0,
    assigned_by VARCHAR(50) DEFAULT 'migration', -- 'manual', 'auto', 'migration'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 外鍵約束
    CONSTRAINT fk_knowledge FOREIGN KEY (knowledge_id)
        REFERENCES knowledge_base(id) ON DELETE CASCADE,
    CONSTRAINT fk_intent FOREIGN KEY (intent_id)
        REFERENCES intents(id) ON DELETE CASCADE,

    -- 唯一約束：同一知識不能重複關聯同一意圖
    CONSTRAINT unique_knowledge_intent UNIQUE(knowledge_id, intent_id),

    -- 檢查約束
    CONSTRAINT check_intent_type CHECK (intent_type IN ('primary', 'secondary')),
    CONSTRAINT check_confidence CHECK (confidence >= 0 AND confidence <= 1)
);

-- 2. 創建索引
CREATE INDEX idx_kim_knowledge_id ON knowledge_intent_mapping(knowledge_id);
CREATE INDEX idx_kim_intent_id ON knowledge_intent_mapping(intent_id);
CREATE INDEX idx_kim_intent_type ON knowledge_intent_mapping(intent_type);
CREATE INDEX idx_kim_composite ON knowledge_intent_mapping(knowledge_id, intent_type);

-- 3. 遷移現有資料（將 knowledge_base.intent_id 遷移到 mapping 表）
INSERT INTO knowledge_intent_mapping (knowledge_id, intent_id, intent_type, confidence, assigned_by)
SELECT
    id as knowledge_id,
    intent_id,
    'primary' as intent_type,
    COALESCE(intent_confidence, 1.0) as confidence,
    COALESCE(intent_assigned_by, 'migration') as assigned_by
FROM knowledge_base
WHERE intent_id IS NOT NULL
ON CONFLICT (knowledge_id, intent_id) DO NOTHING;

-- 4. 添加註解
COMMENT ON TABLE knowledge_intent_mapping IS '知識-意圖多對多關聯表，支援一筆知識關聯多個意圖';
COMMENT ON COLUMN knowledge_intent_mapping.intent_type IS '意圖類型：primary（主要）或 secondary（次要）';
COMMENT ON COLUMN knowledge_intent_mapping.confidence IS '意圖關聯的信心度（0-1）';
COMMENT ON COLUMN knowledge_intent_mapping.assigned_by IS '分類來源：manual（手動）、auto（自動）、migration（遷移）';

-- 5. 創建輔助函數：取得知識的所有意圖
CREATE OR REPLACE FUNCTION get_knowledge_intents(p_knowledge_id INT)
RETURNS TABLE (
    intent_id INT,
    intent_name VARCHAR,
    intent_type VARCHAR,
    confidence FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        kim.intent_id,
        i.name::VARCHAR as intent_name,
        kim.intent_type::VARCHAR,
        kim.confidence
    FROM knowledge_intent_mapping kim
    JOIN intents i ON kim.intent_id = i.id
    WHERE kim.knowledge_id = p_knowledge_id
    ORDER BY
        CASE kim.intent_type
            WHEN 'primary' THEN 1
            WHEN 'secondary' THEN 2
        END,
        kim.confidence DESC;
END;
$$ LANGUAGE plpgsql;

-- 6. 創建輔助函數：取得意圖下的所有知識
CREATE OR REPLACE FUNCTION get_intent_knowledge(p_intent_id INT, p_include_secondary BOOLEAN DEFAULT TRUE)
RETURNS TABLE (
    knowledge_id INT,
    title VARCHAR,
    intent_type VARCHAR,
    confidence FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        kb.id as knowledge_id,
        kb.title::VARCHAR,
        kim.intent_type::VARCHAR,
        kim.confidence
    FROM knowledge_intent_mapping kim
    JOIN knowledge_base kb ON kim.knowledge_id = kb.id
    WHERE kim.intent_id = p_intent_id
        AND (p_include_secondary OR kim.intent_type = 'primary')
    ORDER BY
        CASE kim.intent_type
            WHEN 'primary' THEN 1
            WHEN 'secondary' THEN 2
        END,
        kim.confidence DESC;
END;
$$ LANGUAGE plpgsql;

-- 7. 統計資訊
DO $$
DECLARE
    migrated_count INT;
    total_with_intent INT;
BEGIN
    SELECT COUNT(*) INTO migrated_count FROM knowledge_intent_mapping;
    SELECT COUNT(*) INTO total_with_intent FROM knowledge_base WHERE intent_id IS NOT NULL;

    RAISE NOTICE '=== 知識庫多意圖遷移完成 ===';
    RAISE NOTICE '總知識數（有意圖）: %', total_with_intent;
    RAISE NOTICE '已遷移到 mapping 表: %', migrated_count;
    RAISE NOTICE '遷移完成率: %', ROUND(migrated_count::NUMERIC / NULLIF(total_with_intent, 0) * 100, 2);
END $$;

-- 8. 驗證遷移
SELECT
    'knowledge_intent_mapping' as table_name,
    COUNT(*) as total_mappings,
    COUNT(DISTINCT knowledge_id) as unique_knowledge,
    COUNT(DISTINCT intent_id) as unique_intents,
    SUM(CASE WHEN intent_type = 'primary' THEN 1 ELSE 0 END) as primary_count,
    SUM(CASE WHEN intent_type = 'secondary' THEN 1 ELSE 0 END) as secondary_count
FROM knowledge_intent_mapping;
