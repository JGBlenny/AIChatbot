-- ============================================================
-- T4-A/B2：form_sessions **additive** responsibility carrier（業主裁定 2026-08-30）
--
-- 目的：讓 C2 committed responsibility authority 能跨一次 form round-trip 存活。
--
-- ⚠️ scope 是 **persistence transport**，⛔ 不是順手重新設計 session schema。
--    型別／長度沿用本表最接近欄位的既有慣例：
--      session_authority_mode / fulfillment_strategy → varchar(50)  （比照 `state`）
--      responsibility_id / fulfillment_binding_id / input_contract_id
--                                                    → varchar(100)（比照 session_id／form_id）
--
-- ⛔ **不新增 enum／CHECK／NOT NULL**（業主明示）：
--    先讓 **application invariant**（services/responsibility_session.py）與 persistence
--    round-trip 證成；等 legacy NULL sessions 自然退出，再決定是否收緊 DB constraint。
--    ⚠️ 現在加 constraint 會**改變 legacy acceptance boundary** —— 那是另一件事。
--
-- ⛔ **NO HISTORICAL BACKFILL**（LEGACY_SESSION_COMPATIBILITY）：
--    既有列一律維持 session_authority_mode IS NULL。
--    runtime 解讀：NULL ＋ 既有 legacy 形狀 → 視為 legacy_row；
--    **新建立**的 session 才強制寫明示 mode。
--    ⚠️ backfill 是 production data mutation、對 C2 無必要，且會把 migration 與
--       runtime feature 混在一起。
--
-- ⚠️ responsibility mode 的 knowledge_id 必須為 NULL——該不變量由 **application**
--    強制（SessionAuthorityConflict），⛔ 本 migration 不以 DB constraint 代勞。
--
-- 冪等：IF NOT EXISTS；重跑安全。⛔ 無破壞性語句（無 DROP／TRUNCATE）。
-- ============================================================

ALTER TABLE form_sessions
  ADD COLUMN IF NOT EXISTS session_authority_mode  varchar(50),
  ADD COLUMN IF NOT EXISTS responsibility_id       varchar(100),
  ADD COLUMN IF NOT EXISTS fulfillment_binding_id  varchar(100),
  ADD COLUMN IF NOT EXISTS fulfillment_strategy    varchar(50),
  ADD COLUMN IF NOT EXISTS input_contract_id       varchar(100);

-- 比照 idx_form_sessions_knowledge_id 的既有慣例：authority 主鍵給一個 btree。
-- ⚠️ partial index：只索引 responsibility sessions（legacy 列一律 NULL，不必進索引）。
CREATE INDEX IF NOT EXISTS idx_form_sessions_responsibility_id
  ON form_sessions (responsibility_id)
  WHERE responsibility_id IS NOT NULL;

COMMENT ON COLUMN form_sessions.session_authority_mode IS
  'legacy_row | responsibility；NULL＝歷史列（視為 legacy）。⛔ 不得由其他欄位存在與否猜測 mode。';
COMMENT ON COLUMN form_sessions.responsibility_id IS
  'responsibility mode 的 authority；⛔ knowledge_id 不得作為 authority recovery source（F-C5）。';
COMMENT ON COLUMN form_sessions.fulfillment_binding_id IS
  '穩定 binding ID（例 receipt.actual_amount.v1）；⛔ 不存 callable／function path。';
COMMENT ON COLUMN form_sessions.input_contract_id IS
  'reviewed input contract 的穩定 ID；resolver_id 是另一個 identity，⛔ 不混用。';
