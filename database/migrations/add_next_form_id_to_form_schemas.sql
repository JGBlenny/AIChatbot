-- =====================================================
-- Migration: 添加 next_form_id 欄位到 form_schemas 表（表單串接機制）
-- =====================================================
-- 日期: 2026-06-20
-- 功能: form-chaining（表單串接機制）
-- 目的: 讓一張表單完成後能依設定自動接續下一張表單（後續表單），
--       毋須依賴知識庫檢索重新觸發。
-- 需求: 1.1, 1.4, 7.3
-- 設計: .kiro/specs/form-chaining/design.md（元件 1）
--
-- 說明:
--   next_form_id 標示「來源表單完成後要接續的後續表單 form_id」。
--   命名與 vendor_sop_items.next_form_id 一致；自我參照 form_schemas(form_id)。
--   ON DELETE SET NULL：後續表單被刪除時，來源表單的串接設定自動清空，不破壞既有資料。
--   全程冪等（IF NOT EXISTS / pg_constraint 守衛），可安全重跑。
-- =====================================================

BEGIN;

-- ==========================================
-- 1. 新增 next_form_id 欄位（可空）
-- ==========================================
ALTER TABLE form_schemas
ADD COLUMN IF NOT EXISTS next_form_id VARCHAR(100);

COMMENT ON COLUMN form_schemas.next_form_id IS '後續表單串接：完成本表單後要自動接續的後續表單 ID（對應 form_schemas.form_id），NULL 表示不串接';

-- ==========================================
-- 2. 新增外鍵約束（自我參照，ON DELETE SET NULL）
--    Postgres 的 ADD CONSTRAINT 不支援 IF NOT EXISTS，故以 pg_constraint 守衛達成冪等。
-- ==========================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_form_schemas_next_form'
    ) THEN
        ALTER TABLE form_schemas
        ADD CONSTRAINT fk_form_schemas_next_form
        FOREIGN KEY (next_form_id)
        REFERENCES form_schemas(form_id)
        ON DELETE SET NULL;
    END IF;
END $$;

-- ==========================================
-- 3. 新增索引
-- ==========================================
CREATE INDEX IF NOT EXISTS idx_form_schemas_next_form_id
ON form_schemas(next_form_id);

COMMIT;

-- ==========================================
-- 驗證
-- ==========================================
DO $$
DECLARE
    has_column BOOLEAN;
    has_fk     BOOLEAN;
    has_index  BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'form_schemas' AND column_name = 'next_form_id'
    ) INTO has_column;

    SELECT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_form_schemas_next_form'
    ) INTO has_fk;

    SELECT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'form_schemas' AND indexname = 'idx_form_schemas_next_form_id'
    ) INTO has_index;

    IF has_column AND has_fk AND has_index THEN
        RAISE NOTICE '=================================================';
        RAISE NOTICE '✅ next_form_id 欄位 / FK / 索引 建立成功';
        RAISE NOTICE '=================================================';
    ELSE
        RAISE EXCEPTION '❌ 建立失敗：column=%, fk=%, index=%', has_column, has_fk, has_index;
    END IF;
END $$;

-- =====================================================
-- 使用說明
-- =====================================================
--
-- 套用此 migration（任務 1.2）:
--   docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
--     database/migrations/add_next_form_id_to_form_schemas.sql
--
-- 回滾（如需）:
--   ALTER TABLE form_schemas DROP CONSTRAINT IF EXISTS fk_form_schemas_next_form;
--   DROP INDEX IF EXISTS idx_form_schemas_next_form_id;
--   ALTER TABLE form_schemas DROP COLUMN IF EXISTS next_form_id;
--
-- =====================================================
