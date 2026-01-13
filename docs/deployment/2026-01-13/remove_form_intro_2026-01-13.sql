-- Migration: 刪除 knowledge_base.form_intro 欄位
-- 日期: 2026-01-13
-- 原因: form_intro 欄位冗餘，統一使用 form_schemas.default_intro

-- ========================================
-- 1. 檢查現有數據
-- ========================================

-- 檢查是否有知識使用 form_intro
SELECT
    COUNT(*) as total_knowledge_with_form,
    COUNT(form_intro) as knowledge_using_form_intro
FROM knowledge_base
WHERE form_id IS NOT NULL;

-- 如果有使用 form_intro 的知識，列出來檢查
SELECT id, question_summary, form_id, form_intro
FROM knowledge_base
WHERE form_intro IS NOT NULL AND form_intro != '';

-- ========================================
-- 2. 刪除欄位（不可逆操作）
-- ========================================

-- 刪除 form_intro 欄位
ALTER TABLE knowledge_base DROP COLUMN IF EXISTS form_intro;

-- ========================================
-- 3. 驗證
-- ========================================

-- 確認欄位已刪除
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'knowledge_base'
  AND column_name = 'form_intro';
-- 預期結果：0 rows（欄位已刪除）

-- ========================================
-- 回滾方案（如果需要）
-- ========================================

-- 如果需要回滾，執行以下語句：
-- ALTER TABLE knowledge_base ADD COLUMN form_intro TEXT;
