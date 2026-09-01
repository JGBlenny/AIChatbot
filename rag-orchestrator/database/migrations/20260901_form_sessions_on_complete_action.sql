-- 20260901_form_sessions_on_complete_action
-- 把 responsibility session authority contract 的最後一欄補進 persistence layer。
--
-- 為何需要（2026-09-01 由 S2 真 DB round-trip 逼出，⛔ unit 測試看不到）：
--   build_responsibility_session() 在記憶體裡設 on_complete_action=resume_fulfillment；
--   validate_session() 把該值當 **契約的一部分**驗（且明確禁 show_knowledge，F-C4）；
--   但 form_sessions **沒有這個欄位**，session_state 來自 `SELECT * FROM form_sessions`
--   ⇒ restore 後必為 None ⇒ turn 2 resume 直接 SessionAuthorityError。
--   ⇒ SESSION_CONTRACT_NOT_PERSISTABLE = CONFIRMED（業主定性）
--
-- 業主裁定（2026-09-01）：persist what you validate。
--   ⛔ 不採 restore 階段推導——那會讓 validate_session 對還原路徑變成恆真（normalization
--      而非 validation），F-C4 那條防線等於消失。
--   ⛔ 不改 form_schemas 的 CHECK 去容納 resume_fulfillment——
--      legacy form definition 的 completion semantics ≠ responsibility session authority action，
--      為了新欄位去擴 legacy enum 會把兩個概念重新混回去。
--
-- ⚠️ **NULL-able，⛔ 不加 NOT NULL**：既有 2042 筆 legacy session 沒有這個 persisted
--    contract，⛔ 不得順便改它們的語義（沿用 T4-B2 的 LEGACY_SESSION_COMPATIBILITY）。
-- ⚠️ ⛔ NO BACKFILL：既有列一律維持 NULL。
-- 型別長度沿用本表既有慣例（比照 state / session_authority_mode 的 varchar(50)）。
-- 冪等：IF NOT EXISTS。⛔ 無破壞性語句。

ALTER TABLE form_sessions
  ADD COLUMN IF NOT EXISTS on_complete_action varchar(50);

COMMENT ON COLUMN form_sessions.on_complete_action IS
  'responsibility mode 必須為 resume_fulfillment（F-C4／F-C28）；NULL＝legacy session。⛔ restore 時只讀原值，不得推導或補值。';
