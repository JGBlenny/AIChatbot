-- ==========================================
-- 表單填寫功能資料庫遷移腳本
-- 版本: 1.0.0
-- 日期: 2026-01-09
-- 說明: 建立表單填寫對話功能所需的資料表
-- ==========================================

BEGIN;

-- ==========================================
-- 1. 建立 form_schemas 表 (表單定義)
-- ==========================================

CREATE TABLE IF NOT EXISTS form_schemas (
    id SERIAL PRIMARY KEY,
    form_id VARCHAR(100) UNIQUE NOT NULL,
    form_name VARCHAR(200) NOT NULL,
    trigger_intents JSONB,  -- 觸發意圖列表，例如：["租屋申請", "報修申請"]
    fields JSONB NOT NULL,  -- 欄位定義（JSON格式）
    vendor_id INTEGER,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE form_schemas IS '表單定義表 - 儲存表單結構和欄位定義';
COMMENT ON COLUMN form_schemas.form_id IS '表單唯一識別碼，例如: rental_application';
COMMENT ON COLUMN form_schemas.form_name IS '表單顯示名稱，例如: 租屋申請表';
COMMENT ON COLUMN form_schemas.trigger_intents IS '觸發表單的意圖列表（JSONB），當用戶意圖匹配時自動觸發表單';
COMMENT ON COLUMN form_schemas.fields IS '表單欄位定義（JSONB），包含欄位名稱、類型、提示語、驗證規則等';
COMMENT ON COLUMN form_schemas.vendor_id IS '業者 ID，NULL 表示平台通用表單';
COMMENT ON COLUMN form_schemas.is_active IS '表單是否啟用';

-- 索引
CREATE INDEX IF NOT EXISTS idx_form_schemas_form_id ON form_schemas(form_id);
CREATE INDEX IF NOT EXISTS idx_form_schemas_vendor_id ON form_schemas(vendor_id);
CREATE INDEX IF NOT EXISTS idx_form_schemas_is_active ON form_schemas(is_active);

-- ==========================================
-- 2. 建立 form_sessions 表 (表單會話)
-- ==========================================

CREATE TABLE IF NOT EXISTS form_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,  -- 沿用現有 session_id 機制
    user_id VARCHAR(100),
    vendor_id INTEGER,
    form_id VARCHAR(100) NOT NULL REFERENCES form_schemas(form_id),
    state VARCHAR(50) NOT NULL,  -- COLLECTING / DIGRESSION / COMPLETED / CANCELLED
    current_field_index INTEGER DEFAULT 0,
    collected_data JSONB,  -- 已收集的資料
    started_at TIMESTAMP DEFAULT NOW(),
    last_activity_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP
);

COMMENT ON TABLE form_sessions IS '表單會話表 - 追蹤表單填寫進度和狀態';
COMMENT ON COLUMN form_sessions.session_id IS '會話 ID，與對話系統的 session_id 關聯';
COMMENT ON COLUMN form_sessions.user_id IS '用戶 ID';
COMMENT ON COLUMN form_sessions.vendor_id IS '業者 ID';
COMMENT ON COLUMN form_sessions.form_id IS '表單 ID（外鍵到 form_schemas）';
COMMENT ON COLUMN form_sessions.state IS '會話狀態：COLLECTING（收集中）、DIGRESSION（離題中）、COMPLETED（已完成）、CANCELLED（已取消）';
COMMENT ON COLUMN form_sessions.current_field_index IS '當前收集的欄位索引（從 0 開始）';
COMMENT ON COLUMN form_sessions.collected_data IS '已收集的資料（JSONB），格式：{"field_name": "value", ...}';
COMMENT ON COLUMN form_sessions.last_activity_at IS '最後活動時間，用於過期會話清理';
COMMENT ON COLUMN form_sessions.completed_at IS '完成時間';
COMMENT ON COLUMN form_sessions.cancelled_at IS '取消時間';

-- 索引
CREATE INDEX IF NOT EXISTS idx_form_sessions_session_id ON form_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_form_sessions_user_id ON form_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_form_sessions_vendor_id ON form_sessions(vendor_id);
CREATE INDEX IF NOT EXISTS idx_form_sessions_state ON form_sessions(state);
CREATE INDEX IF NOT EXISTS idx_form_sessions_last_activity ON form_sessions(last_activity_at);

-- ==========================================
-- 3. 建立 form_submissions 表 (表單提交記錄)
-- ==========================================

CREATE TABLE IF NOT EXISTS form_submissions (
    id SERIAL PRIMARY KEY,
    form_session_id INTEGER NOT NULL REFERENCES form_sessions(id),
    form_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100),
    vendor_id INTEGER,
    submitted_data JSONB NOT NULL,  -- 完整的提交資料
    submitted_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE form_submissions IS '表單提交記錄表 - 儲存已完成的表單提交';
COMMENT ON COLUMN form_submissions.form_session_id IS '表單會話 ID（外鍵到 form_sessions）';
COMMENT ON COLUMN form_submissions.form_id IS '表單 ID';
COMMENT ON COLUMN form_submissions.user_id IS '用戶 ID';
COMMENT ON COLUMN form_submissions.vendor_id IS '業者 ID';
COMMENT ON COLUMN form_submissions.submitted_data IS '完整的提交資料（JSONB）';
COMMENT ON COLUMN form_submissions.submitted_at IS '提交時間';

-- 索引
CREATE INDEX IF NOT EXISTS idx_form_submissions_form_session_id ON form_submissions(form_session_id);
CREATE INDEX IF NOT EXISTS idx_form_submissions_form_id ON form_submissions(form_id);
CREATE INDEX IF NOT EXISTS idx_form_submissions_user_id ON form_submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_form_submissions_vendor_id ON form_submissions(vendor_id);
CREATE INDEX IF NOT EXISTS idx_form_submissions_submitted_at ON form_submissions(submitted_at);

-- ==========================================
-- 4. 插入測試表單定義（租屋申請表）
-- ==========================================

INSERT INTO form_schemas (form_id, form_name, trigger_intents, fields, vendor_id, is_active)
VALUES (
    'rental_application',
    '租屋申請表',
    '["租屋申請", "我要租房", "申請租屋"]'::jsonb,
    '[
        {
            "field_name": "full_name",
            "field_label": "全名",
            "field_type": "text",
            "prompt": "請問您的全名是？",
            "validation_type": "taiwan_name",
            "required": true,
            "max_length": 50
        },
        {
            "field_name": "id_number",
            "field_label": "身分證字號",
            "field_type": "text",
            "prompt": "請提供您的身分證字號（格式：A123456789）",
            "validation_type": "taiwan_id",
            "required": true
        },
        {
            "field_name": "phone",
            "field_label": "聯絡電話",
            "field_type": "text",
            "prompt": "請提供您的聯絡電話（手機或市話）",
            "validation_type": "phone",
            "required": true
        },
        {
            "field_name": "address",
            "field_label": "通訊地址",
            "field_type": "text",
            "prompt": "請提供您的通訊地址",
            "validation_type": "address",
            "required": true,
            "max_length": 200
        }
    ]'::jsonb,
    NULL,  -- NULL 表示平台通用表單
    true
)
ON CONFLICT (form_id) DO UPDATE SET
    form_name = EXCLUDED.form_name,
    trigger_intents = EXCLUDED.trigger_intents,
    fields = EXCLUDED.fields,
    updated_at = NOW();

COMMIT;

-- ==========================================
-- 驗證腳本執行結果
-- ==========================================

-- 檢查表格是否成功建立
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'form_schemas') THEN
        RAISE NOTICE '✅ 表格 form_schemas 建立成功';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'form_sessions') THEN
        RAISE NOTICE '✅ 表格 form_sessions 建立成功';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'form_submissions') THEN
        RAISE NOTICE '✅ 表格 form_submissions 建立成功';
    END IF;

    -- 檢查測試資料是否插入
    IF EXISTS (SELECT 1 FROM form_schemas WHERE form_id = 'rental_application') THEN
        RAISE NOTICE '✅ 測試表單定義（租屋申請表）插入成功';
    END IF;
END $$;
