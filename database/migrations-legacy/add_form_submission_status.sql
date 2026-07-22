-- ==========================================
-- 表單提交狀態管理功能資料庫遷移腳本
-- 版本: 1.1.0
-- 日期: 2026-01-10
-- 說明: 為 form_submissions 表新增狀態管理欄位
-- ==========================================

BEGIN;

-- 檢查欄位是否已存在，如果不存在才新增
DO $$
BEGIN
    -- 新增 status 欄位（狀態：pending, processing, completed, rejected）
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'form_submissions' AND column_name = 'status'
    ) THEN
        ALTER TABLE form_submissions
        ADD COLUMN status VARCHAR(50) DEFAULT 'pending';

        COMMENT ON COLUMN form_submissions.status IS '處理狀態：pending(待處理), processing(處理中), completed(已完成), rejected(已拒絕)';
    END IF;

    -- 新增 notes 欄位（備註說明）
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'form_submissions' AND column_name = 'notes'
    ) THEN
        ALTER TABLE form_submissions
        ADD COLUMN notes TEXT;

        COMMENT ON COLUMN form_submissions.notes IS '處理備註說明';
    END IF;

    -- 新增 updated_at 欄位（最後更新時間）
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'form_submissions' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE form_submissions
        ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();

        COMMENT ON COLUMN form_submissions.updated_at IS '最後更新時間';
    END IF;

    -- 新增 updated_by 欄位（更新者）
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'form_submissions' AND column_name = 'updated_by'
    ) THEN
        ALTER TABLE form_submissions
        ADD COLUMN updated_by VARCHAR(100);

        COMMENT ON COLUMN form_submissions.updated_by IS '更新者（業者代碼或管理員）';
    END IF;
END $$;

-- 新增狀態索引（如果不存在）
CREATE INDEX IF NOT EXISTS idx_form_submissions_status ON form_submissions(status);

COMMIT;

-- ==========================================
-- 驗證遷移
-- ==========================================

-- 顯示 form_submissions 表結構
\d form_submissions;

-- 顯示新增的欄位
SELECT
    column_name,
    data_type,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'form_submissions'
    AND column_name IN ('status', 'notes', 'updated_at', 'updated_by')
ORDER BY ordinal_position;
