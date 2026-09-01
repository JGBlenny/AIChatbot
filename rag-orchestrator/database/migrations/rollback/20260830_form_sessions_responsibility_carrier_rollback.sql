-- rollback：T4-A/B2 form_sessions responsibility carrier
-- ⚠️ **破壞性**（DROP COLUMN）——runner 會自動跳過破壞性語句，故本檔僅供人工執行。
-- ⚠️ 僅在確認**無** responsibility-mode session 在飛時執行；否則進行中的 session 會失去 authority。
--   先查：SELECT count(*) FROM form_sessions
--          WHERE session_authority_mode = 'responsibility' AND completed_at IS NULL;
DROP INDEX IF EXISTS idx_form_sessions_responsibility_id;
ALTER TABLE form_sessions
  DROP COLUMN IF EXISTS input_contract_id,
  DROP COLUMN IF EXISTS fulfillment_strategy,
  DROP COLUMN IF EXISTS fulfillment_binding_id,
  DROP COLUMN IF EXISTS responsibility_id,
  DROP COLUMN IF EXISTS session_authority_mode;
