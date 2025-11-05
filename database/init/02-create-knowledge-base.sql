-- ========================================
-- knowledge_base 表（最終完整版本）
-- 整合所有 migrations 的結果
-- ========================================

CREATE TABLE IF NOT EXISTS knowledge_base (
    -- 主鍵
    id SERIAL PRIMARY KEY,

    -- 核心內容（必填）
    question_summary TEXT NOT NULL,
    answer TEXT NOT NULL,

    -- 意圖分類（舊欄位，保留向後兼容）
    -- 注意：intent_id 將在 04 腳本執行後添加外鍵約束
    intent_id INTEGER,
    intent_confidence FLOAT,
    intent_assigned_by VARCHAR(20) DEFAULT 'auto',

    -- 多維度過濾
    business_types TEXT[] DEFAULT NULL,
    target_user TEXT[] DEFAULT NULL,
    keywords TEXT[],

    -- 業者與範圍（vendor_id 外鍵將在 07 腳本執行後添加）
    vendor_id INTEGER,
    scope VARCHAR(20) DEFAULT 'global',
    priority INTEGER DEFAULT 0,

    -- 模板支援
    is_template BOOLEAN DEFAULT false,
    template_vars JSONB DEFAULT '[]',

    -- 向量搜尋
    embedding vector(1536),

    -- 影片支援
    video_s3_key VARCHAR(500),
    video_url VARCHAR(500),
    video_thumbnail_s3_key VARCHAR(500),
    video_thumbnail_url VARCHAR(500),
    video_duration INTEGER,
    video_file_size BIGINT,
    video_format VARCHAR(20),
    video_uploaded_at TIMESTAMP,

    -- 來源追蹤（source_test_scenario_id 外鍵將在 09 腳本執行後添加）
    source_type VARCHAR(20) DEFAULT 'manual',
    source_file VARCHAR(255),
    source_date DATE,
    source_test_scenario_id INTEGER,
    generation_metadata JSONB,

    -- 業務分類（category 外鍵將在 10 腳本執行後可用）
    category VARCHAR(50),

    -- 狀態與審計
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);

-- ========================================
-- 索引
-- ========================================

-- 基本索引
CREATE INDEX IF NOT EXISTS idx_kb_scope ON knowledge_base(scope);
CREATE INDEX IF NOT EXISTS idx_kb_template ON knowledge_base(is_template);
CREATE INDEX IF NOT EXISTS idx_kb_created_at ON knowledge_base(created_at);
CREATE INDEX IF NOT EXISTS idx_kb_is_active ON knowledge_base(is_active);
CREATE INDEX IF NOT EXISTS idx_kb_source_type ON knowledge_base(source_type);
CREATE INDEX IF NOT EXISTS idx_kb_category ON knowledge_base(category);

-- 向量索引（IVFFlat 演算法加速向量搜尋）
-- lists 參數：建議設為 sqrt(總資料筆數)，這裡預估 1000 筆，設為 100
CREATE INDEX IF NOT EXISTS idx_kb_embedding ON knowledge_base
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- GIN 索引（陣列欄位）
CREATE INDEX IF NOT EXISTS idx_kb_keywords ON knowledge_base USING GIN(keywords);
CREATE INDEX IF NOT EXISTS idx_kb_business_types ON knowledge_base USING GIN(business_types);
CREATE INDEX IF NOT EXISTS idx_kb_target_user ON knowledge_base USING GIN(target_user);

-- 部分索引（有影片的知識）
CREATE INDEX IF NOT EXISTS idx_kb_video_s3_key ON knowledge_base(video_s3_key)
WHERE video_s3_key IS NOT NULL;

-- ========================================
-- 觸發器：自動更新 updated_at
-- ========================================

CREATE TRIGGER update_kb_updated_at
    BEFORE UPDATE ON knowledge_base
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- 欄位註釋
-- ========================================

COMMENT ON TABLE knowledge_base IS '知識庫表 - 使用 intents(意圖分類) + business_types(業態語氣) + target_user(用戶視角) 三維度過濾';

COMMENT ON COLUMN knowledge_base.question_summary IS '問題摘要（必填）';
COMMENT ON COLUMN knowledge_base.answer IS '答案內容（必填）';
COMMENT ON COLUMN knowledge_base.business_types IS '適用的業態類型陣列：system_provider(系統商), full_service(包租型), property_management(代管型)。NULL=適用所有業態（通用知識）';
COMMENT ON COLUMN knowledge_base.target_user IS '目標用戶類型（可多選）：tenant=租客, landlord=房東, property_manager=物業管理師, system_admin=系統管理員, NULL=通用（所有人可見）';
COMMENT ON COLUMN knowledge_base.vendor_id IS '業者 ID（NULL 表示全域知識）';
COMMENT ON COLUMN knowledge_base.is_template IS '是否為模板（包含變數）';
COMMENT ON COLUMN knowledge_base.template_vars IS '模板變數列表（JSON 陣列）';
COMMENT ON COLUMN knowledge_base.scope IS '知識範圍：global（全域）, vendor（業者專屬）, customized（覆蓋全域）';
COMMENT ON COLUMN knowledge_base.priority IS '優先級（數字越大優先級越高，用於排序）';
COMMENT ON COLUMN knowledge_base.source_type IS '知識來源類型: manual (人工), ai_generated (AI生成), imported (匯入), ai_assisted (AI輔助)';
COMMENT ON COLUMN knowledge_base.source_test_scenario_id IS '來源測試情境 ID（如果由測試情境生成）';
COMMENT ON COLUMN knowledge_base.generation_metadata IS 'AI 生成的詳細資訊: {model, prompt, confidence, reviewed_by, edited}';
COMMENT ON COLUMN knowledge_base.category IS '業務分類（參考 category_config 表的 category_value）';
COMMENT ON COLUMN knowledge_base.is_active IS '知識是否啟用';

-- ========================================
-- 測試資料（pgvector 驗證）
-- ========================================

INSERT INTO knowledge_base (question_summary, answer, keywords, source_file)
VALUES
    (
        'pgvector 是否正確安裝',
        '如果你看到這筆資料，代表 pgvector 已經成功安裝並可以使用！',
        ARRAY['測試', 'pgvector', '安裝'],
        'init_script'
    );

-- ========================================
-- 相關表：chat_history
-- ========================================

CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,

    -- 使用者資訊
    user_id VARCHAR(100),
    user_role VARCHAR(50),  -- 房東、租客、管理師等

    -- 對話內容
    question TEXT NOT NULL,
    answer TEXT NOT NULL,

    -- 相關知識庫 ID
    related_kb_ids INTEGER[],

    -- 評價
    feedback_score INTEGER CHECK (feedback_score BETWEEN 1 AND 5),
    feedback_comment TEXT,

    -- 時間戳記
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_user_id ON chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_created_at ON chat_history(created_at);

-- ========================================
-- 顯示統計資訊
-- ========================================

SELECT
    '✅ knowledge_base 表已建立（最終版本）' AS status,
    COUNT(*) AS test_records_count
FROM knowledge_base;
