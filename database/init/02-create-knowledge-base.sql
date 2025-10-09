-- 建立知識庫表
CREATE TABLE IF NOT EXISTS knowledge_base (
    id SERIAL PRIMARY KEY,

    -- 基本資訊
    title VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    question_summary TEXT,
    answer TEXT NOT NULL,

    -- 分類與標籤
    audience VARCHAR(50),  -- 對象：房東、租客、管理師等
    keywords TEXT[],       -- 關鍵字陣列

    -- 來源資訊
    source_file VARCHAR(255),
    source_date DATE,

    -- 向量欄位 (OpenAI text-embedding-3-small 使用 1536 維)
    embedding vector(1536),

    -- 時間戳記
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 建立索引以加速查詢
CREATE INDEX IF NOT EXISTS idx_kb_category ON knowledge_base(category);
CREATE INDEX IF NOT EXISTS idx_kb_audience ON knowledge_base(audience);
CREATE INDEX IF NOT EXISTS idx_kb_created_at ON knowledge_base(created_at);

-- 建立向量索引 (使用 IVFFlat 演算法加速向量搜尋)
-- lists 參數：建議設為 sqrt(總資料筆數)，這裡預估 1000 筆，設為 100
CREATE INDEX IF NOT EXISTS idx_kb_embedding ON knowledge_base
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 建立 GIN 索引以加速關鍵字搜尋
CREATE INDEX IF NOT EXISTS idx_kb_keywords ON knowledge_base USING GIN(keywords);

-- 建立觸發器：自動更新 updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_kb_updated_at
    BEFORE UPDATE ON knowledge_base
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 建立對話歷史表 (用於記錄 ChatBot 對話)
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

-- 插入測試資料（範例）
INSERT INTO knowledge_base (title, category, question_summary, answer, audience, keywords, source_file)
VALUES
    (
        '測試：pgvector 安裝成功',
        '系統測試',
        'pgvector 是否正確安裝',
        '如果你看到這筆資料，代表 pgvector 已經成功安裝並可以使用！',
        '系統管理員',
        ARRAY['測試', 'pgvector', '安裝'],
        'init_script'
    );

-- 顯示統計資訊
SELECT
    '✅ pgvector 擴充已啟用' AS status,
    COUNT(*) AS test_records_count
FROM knowledge_base;
