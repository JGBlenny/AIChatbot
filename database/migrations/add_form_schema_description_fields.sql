-- ==========================================
-- 表單 Schema 描述欄位遷移腳本
-- 版本: 1.2.0
-- 日期: 2026-01-11
-- 說明: 為 form_schemas 表新增 description 和 default_intro 欄位
-- ==========================================

BEGIN;

-- 檢查欄位是否已存在,如果不存在才新增
DO $$
BEGIN
    -- 新增 description 欄位(表單描述)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'form_schemas' AND column_name = 'description'
    ) THEN
        ALTER TABLE form_schemas
        ADD COLUMN description TEXT;

        COMMENT ON COLUMN form_schemas.description IS '表單描述說明';
        RAISE NOTICE '✅ 新增 description 欄位';
    ELSE
        RAISE NOTICE 'ℹ️  description 欄位已存在,跳過';
    END IF;

    -- 新增 default_intro 欄位(預設引導語)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'form_schemas' AND column_name = 'default_intro'
    ) THEN
        ALTER TABLE form_schemas
        ADD COLUMN default_intro TEXT;

        COMMENT ON COLUMN form_schemas.default_intro IS '表單開始時的預設引導語';
        RAISE NOTICE '✅ 新增 default_intro 欄位';
    ELSE
        RAISE NOTICE 'ℹ️  default_intro 欄位已存在,跳過';
    END IF;
END $$;

COMMIT;

-- ==========================================
-- 驗證遷移
-- ==========================================

-- 顯示新增的欄位
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'form_schemas'
    AND column_name IN ('description', 'default_intro')
ORDER BY ordinal_position;
