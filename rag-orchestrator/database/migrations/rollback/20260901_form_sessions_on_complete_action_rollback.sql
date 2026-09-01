-- rollback of 20260901_form_sessions_on_complete_action
-- ⚠️ **破壞性**（DROP COLUMN）——migrate.sh 會自動跳過破壞性語句，本檔僅供人工執行。
-- ⚠️ 執行前先確認無進行中的 responsibility session：
--   SELECT count(*) FROM form_sessions
--    WHERE session_authority_mode='responsibility' AND completed_at IS NULL;
-- ⛔ 只撤銷本 migration 自己新增的那一欄，⛔ 不碰其他欄位與任何資料列。
ALTER TABLE form_sessions DROP COLUMN IF EXISTS on_complete_action;
DELETE FROM schema_migrations WHERE migration_name = '20260901_form_sessions_on_complete_action';
