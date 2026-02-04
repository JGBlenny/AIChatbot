-- =====================================================
-- Migration: 添加 skip_review 欄位到 form_schemas 表
-- =====================================================
-- 日期: 2026-02-04
-- 目的: 支持表單跳過審核功能
-- =====================================================

BEGIN;

-- 添加 skip_review 欄位
ALTER TABLE form_schemas
ADD COLUMN IF NOT EXISTS skip_review BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN form_schemas.skip_review IS '是否跳過表單審核流程';

COMMIT;

-- 驗證
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'form_schemas'
          AND column_name = 'skip_review'
    ) THEN
        RAISE NOTICE '=================================================';
        RAISE NOTICE '✅ skip_review 欄位添加成功';
        RAISE NOTICE '=================================================';
    ELSE
        RAISE EXCEPTION '❌ skip_review 欄位添加失敗';
    END IF;
END $$;

-- =====================================================
-- 使用說明
-- =====================================================
--
-- 執行此 migration:
--   docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
--     database/migrations/add_skip_review_to_form_schemas.sql
--
-- 此欄位允許表單跳過人工審核流程，直接執行 API 調用。
--
-- =====================================================
