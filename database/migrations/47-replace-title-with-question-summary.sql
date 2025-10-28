-- ==========================================
-- Migration 47: 移除 title，只保留 question_summary
-- ==========================================
--
-- 目的：簡化知識庫結構，用 question_summary 取代 title
--
-- 步驟：
-- 1. 將現有 title 資料合併到 question_summary
-- 2. 修改 question_summary 為 NOT NULL
-- 3. 刪除 title 欄位
--
-- ==========================================

BEGIN;

-- Step 1: 將 title 資料合併到 question_summary
-- 規則：如果 question_summary 為空或 NULL，則使用 title；否則保留 question_summary
UPDATE knowledge_base
SET question_summary = COALESCE(
    NULLIF(TRIM(question_summary), ''),  -- 如果 question_summary 非空，使用它
    title                                 -- 否則使用 title
);

-- Step 2: 修改 question_summary 為 NOT NULL（現在所有記錄都有值了）
ALTER TABLE knowledge_base
    ALTER COLUMN question_summary SET NOT NULL;

-- Step 3: 刪除 title 欄位
ALTER TABLE knowledge_base
    DROP COLUMN title;

-- 驗證遷移
DO $$
DECLARE
    record_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO record_count FROM knowledge_base WHERE question_summary IS NULL;
    IF record_count > 0 THEN
        RAISE EXCEPTION '❌ 遷移失敗: 仍有 % 筆記錄的 question_summary 為 NULL', record_count;
    END IF;

    RAISE NOTICE '✅ 遷移成功: title 已移除，所有知識已使用 question_summary';
END $$;

COMMIT;

-- 顯示遷移後的結構
SELECT
    '✅ 遷移完成' AS status,
    COUNT(*) AS total_knowledge,
    COUNT(DISTINCT question_summary) AS unique_questions
FROM knowledge_base;
