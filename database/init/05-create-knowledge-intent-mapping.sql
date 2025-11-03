-- ========================================
-- 知識-意圖多對多映射表
-- 用途：支援一個知識關聯多個意圖
-- ========================================

CREATE TABLE IF NOT EXISTS knowledge_intent_mapping (
    id SERIAL PRIMARY KEY,
    knowledge_id INT NOT NULL,
    intent_id INT NOT NULL,
    intent_type VARCHAR(20) NOT NULL DEFAULT 'secondary', -- 'primary' 或 'secondary'
    confidence FLOAT DEFAULT 1.0,
    assigned_by VARCHAR(50) DEFAULT 'manual', -- 'manual', 'auto', 'migration'
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

-- 索引
CREATE INDEX idx_kim_knowledge_id ON knowledge_intent_mapping(knowledge_id);
CREATE INDEX idx_kim_intent_id ON knowledge_intent_mapping(intent_id);
CREATE INDEX idx_kim_intent_type ON knowledge_intent_mapping(intent_type);

-- 觸發器：自動更新 updated_at
CREATE TRIGGER update_knowledge_intent_mapping_updated_at
    BEFORE UPDATE ON knowledge_intent_mapping
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 欄位註釋
COMMENT ON TABLE knowledge_intent_mapping IS '知識-意圖多對多映射表：支援一個知識關聯多個意圖';
COMMENT ON COLUMN knowledge_intent_mapping.intent_type IS 'primary（主要意圖）或 secondary（次要意圖）';
COMMENT ON COLUMN knowledge_intent_mapping.confidence IS '關聯信心度（0.0-1.0）';
COMMENT ON COLUMN knowledge_intent_mapping.assigned_by IS '指派方式：manual（人工）, auto（自動）, migration（遷移）';

-- 顯示統計資訊
SELECT
    '✅ knowledge_intent_mapping 表已建立' AS status;
