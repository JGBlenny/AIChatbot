-- ========================================
-- 遷移：重命名 chat_history.user_role → target_user
-- 日期：2026-01-13
-- 目的：統一系統使用 target_user 欄位命名
-- ========================================

-- 1. 重命名欄位
ALTER TABLE chat_history
RENAME COLUMN user_role TO target_user;

-- 2. 確認結果
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'chat_history'
  AND column_name = 'target_user';
