-- ========================================
-- 意圖管理系統 - 資料庫遷移腳本
-- ========================================

-- 1. intents 表（意圖配置）
CREATE TABLE IF NOT EXISTS intents (
    id SERIAL PRIMARY KEY,

    -- 基本資訊
    name VARCHAR(100) NOT NULL UNIQUE,          -- 意圖名稱（唯一）
    type VARCHAR(50) NOT NULL,                  -- knowledge/data_query/action/hybrid
    description TEXT,                           -- 描述
    keywords TEXT[],                            -- 關鍵字陣列

    -- 配置
    confidence_threshold FLOAT DEFAULT 0.80,    -- 信心度閾值
    is_enabled BOOLEAN DEFAULT true,            -- 是否啟用
    priority INTEGER DEFAULT 0,                 -- 優先級（數字越大優先級越高）

    -- API 配置
    api_required BOOLEAN DEFAULT false,         -- 是否需要外部 API
    api_endpoint VARCHAR(100),                  -- API 端點名稱
    api_action VARCHAR(100),                    -- API 動作名稱

    -- 統計資訊
    knowledge_count INTEGER DEFAULT 0,          -- 關聯的知識庫數量
    usage_count INTEGER DEFAULT 0,              -- 使用次數
    last_used_at TIMESTAMP,                     -- 最後使用時間

    -- 元數據
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_intents_enabled ON intents(is_enabled);
CREATE INDEX IF NOT EXISTS idx_intents_type ON intents(type);
CREATE INDEX IF NOT EXISTS idx_intents_priority ON intents(priority DESC);
CREATE INDEX IF NOT EXISTS idx_intents_keywords ON intents USING GIN(keywords);

-- 觸發器：自動更新 updated_at
CREATE TRIGGER update_intents_updated_at
    BEFORE UPDATE ON intents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ========================================

-- 2. suggested_intents 表（建議新增的意圖）
CREATE TABLE IF NOT EXISTS suggested_intents (
    id SERIAL PRIMARY KEY,

    -- 建議資訊
    suggested_name VARCHAR(100) NOT NULL,       -- 建議的意圖名稱
    suggested_type VARCHAR(50),                 -- 建議的意圖類型
    suggested_description TEXT,                 -- 建議的描述
    suggested_keywords TEXT[],                  -- 建議的關鍵字

    -- 發現來源
    trigger_question TEXT NOT NULL,             -- 觸發的問題
    user_id VARCHAR(100),                       -- 提問用戶

    -- OpenAI 分析結果
    relevance_score FLOAT,                      -- 相關性分數（0-1）
    reasoning TEXT,                             -- OpenAI 的推理說明
    openai_response JSONB,                      -- 完整 OpenAI 回應

    -- 統計
    frequency INTEGER DEFAULT 1,                -- 出現頻率
    first_suggested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_suggested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 審核狀態
    status VARCHAR(20) DEFAULT 'pending',       -- pending/approved/rejected/merged
    reviewed_by VARCHAR(100),                   -- 審核人員
    reviewed_at TIMESTAMP,                      -- 審核時間
    review_note TEXT,                           -- 審核備註

    -- 如果採納，關聯到實際建立的意圖
    approved_intent_id INTEGER REFERENCES intents(id),

    -- 元數據
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_suggested_intents_status ON suggested_intents(status);
CREATE INDEX IF NOT EXISTS idx_suggested_intents_frequency ON suggested_intents(frequency DESC);
CREATE INDEX IF NOT EXISTS idx_suggested_intents_relevance ON suggested_intents(relevance_score DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_suggested_intents_name_pending
    ON suggested_intents(suggested_name)
    WHERE status = 'pending';  -- 同名建議只能有一個 pending

-- 觸發器
CREATE TRIGGER update_suggested_intents_updated_at
    BEFORE UPDATE ON suggested_intents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ========================================

-- 3. business_scope_config 表（業務範圍配置）
CREATE TABLE IF NOT EXISTS business_scope_config (
    id SERIAL PRIMARY KEY,

    -- 配置資訊
    scope_name VARCHAR(100) NOT NULL UNIQUE,    -- 配置名稱（internal/external）
    scope_type VARCHAR(50) NOT NULL,            -- 類型（system_vendor/property_management）
    display_name VARCHAR(100) NOT NULL,         -- 顯示名稱

    -- 業務描述
    business_description TEXT NOT NULL,         -- 業務範圍描述
    example_questions TEXT[],                   -- 範例問題
    example_intents TEXT[],                     -- 範例意圖

    -- OpenAI Prompt 配置
    relevance_prompt TEXT,                      -- 判斷相關性的 Prompt

    -- 配置
    is_active BOOLEAN DEFAULT false,            -- 是否啟用

    -- 元數據
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_business_scope_active ON business_scope_config(is_active);

-- 觸發器
CREATE TRIGGER update_business_scope_updated_at
    BEFORE UPDATE ON business_scope_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 預設配置資料
INSERT INTO business_scope_config (scope_name, scope_type, display_name, business_description, example_questions, example_intents, relevance_prompt, is_active) VALUES
(
    'internal',
    'system_vendor',
    '系統商（內部使用）',
    '系統商內部管理系統，包含：系統設定、用戶管理、權限管理、系統監控、資料分析、帳務管理等',
    ARRAY['如何新增用戶？', '怎麼設定權限？', '系統監控在哪裡？', '如何匯出報表？'],
    ARRAY['用戶管理', '權限設定', '系統監控', '資料匯出'],
    '判斷以下問題是否與「系統商內部管理」相關。系統商業務包含：系統設定、用戶管理、權限管理、系統監控、資料分析、帳務管理等。',
    false
),
(
    'external',
    'property_management',
    '包租代管業者（外部使用）',
    '包租代管客服系統，包含：租約管理、繳費問題、維修報修、退租流程、合約規定、設備使用、物件資訊等',
    ARRAY['如何退租？', '押金什麼時候退還？', '如何報修？', '租約到期日是什麼時候？'],
    ARRAY['退租流程', '押金處理', '設備報修', '租約查詢'],
    '判斷以下問題是否與「包租代管服務」相關。包租代管業務包含：租約管理、繳費問題、維修報修、退租流程、合約規定、設備使用、物件資訊等。',
    true  -- 預設啟用外部模式
)
ON CONFLICT (scope_name) DO NOTHING;

-- ========================================

-- 4. 修改 knowledge_base 表
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS intent_id INTEGER REFERENCES intents(id),
ADD COLUMN IF NOT EXISTS intent_confidence FLOAT,           -- 自動分類的信心度
ADD COLUMN IF NOT EXISTS intent_assigned_by VARCHAR(20) DEFAULT 'auto';  -- auto/manual

-- 新增索引
CREATE INDEX IF NOT EXISTS idx_kb_intent_id ON knowledge_base(intent_id);

-- ========================================

-- 5. 修改 conversation_logs 表
ALTER TABLE conversation_logs
ADD COLUMN IF NOT EXISTS suggested_intent_id INTEGER REFERENCES suggested_intents(id),
ADD COLUMN IF NOT EXISTS is_new_intent_suggested BOOLEAN DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_conv_suggested_intent ON conversation_logs(suggested_intent_id);

-- ========================================

-- 顯示統計資訊
SELECT
    '✅ 意圖管理系統表已建立' AS status,
    (SELECT COUNT(*) FROM intents) AS intents_count,
    (SELECT COUNT(*) FROM business_scope_config) AS scope_configs_count;
