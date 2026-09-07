-- =====================================================
-- 子 spec agent-write-tools・W2（DSP-038-3，2026-09-08）：
--   agent_confirmation_tokens 加一欄 pending_id
--
-- 背景：DSP-038 把「兌現」從寫入工具搬到 Runtime——使用者按下的按鈕送回來的是
--   `confirm_submit:<pending_id>`，Runtime 必須只憑 `(session_id, pending_id)`
--   就能兌現，**token 因此完全不必離開 DB 與 run_turn 那一格行程**。
--   `pending_id` 本來就算得出來（`sha256(token)[:16]`，見
--   `services/agent/tools/confirm.py:pending_id_for`），這裡只是把它存下來當
--   查詢鍵——⛔ 不是新的秘密，它是 token 的單向摘要，拿到它兌現不了。
--
-- ⛔ **本檔只加這一欄**：表的「只存雜湊、不存 payload／summary／receipt 原文」
--   這個決定不變（DSP-038-3）。待確認的 action／payload／receipt 存 session 狀態
--   （`agent_state["pending_confirm"]` → `form_sessions.collected_data`，
--   與既有 bill_ref／contract_ref 槽位同一敏感等級與保留期，DSP-038-4）。
--
-- 冪等：ADD COLUMN / CREATE INDEX 皆 IF NOT EXISTS；回填只碰 pending_id IS NULL
--   的列；CHECK 以 pg_constraint 查名後才 ADD（比照 20260905 那支的寫法）。
--
-- 可逆（回退步驟，⛔ 不會掉任何既有資料）：
--   ALTER TABLE agent_confirmation_tokens DROP CONSTRAINT IF EXISTS
--       agent_confirmation_tokens_pending_id_shape;
--   DROP INDEX IF EXISTS idx_agent_confirmation_tokens_pending;
--   ALTER TABLE agent_confirmation_tokens DROP COLUMN IF EXISTS pending_id;
--   回退後 `redeem_token(token, session_id)`（2.4 的既有函式，仍保留）照常運作，
--   只有 DSP-038 的 `redeem_pending` 那條路會失效 ⇒ 確認段回 CONFIRMATION_REQUIRED
--   （fail-closed，不會誤放行）。
--
-- ⛔ 本檔不刪任何列；線上執行由業主依 runbook 操作。
-- =====================================================

-- 1. 新欄（nullable：既有列先留空，下一步回填；⛔ 不設 NOT NULL，
--    那會讓這支 migration 在有存量列的庫上直接失敗）
ALTER TABLE agent_confirmation_tokens
    ADD COLUMN IF NOT EXISTS pending_id text;

-- 2. 回填既有列：pending_id = sha256(token) 的十六進位前 16 字
--    （與 `confirm.pending_id_for` 逐位元同式；PostgreSQL 11+ 內建 sha256(bytea)，
--     本專案實跑於 PG 16）。
--    ⚠️ token 欄型別是 text ⇒ 先轉 bytea 再雜湊；`convert_to(..., 'UTF8')` 與
--    Python 端 `token.encode("utf-8")` 對齊（token 是 urlsafe base64，純 ASCII，
--    兩種轉法結果相同；寫明編碼是為了不依賴 server 的 client_encoding）。
UPDATE agent_confirmation_tokens
   SET pending_id = left(encode(sha256(convert_to(token, 'UTF8')), 'hex'), 16)
 WHERE pending_id IS NULL;

-- 3. 形狀約束：16 個十六進位字元（NULL 放行——新欄可為空，見上）。
--    這條擋的是「有人改了 pending_id 的算式卻沒改兌現端」——長度不合當場失敗，
--    好過兌現時靜默查不到、每一次確認都變成 CONFIRMATION_REQUIRED。
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'agent_confirmation_tokens_pending_id_shape'
    ) THEN
        ALTER TABLE agent_confirmation_tokens
            ADD CONSTRAINT agent_confirmation_tokens_pending_id_shape
            CHECK (pending_id IS NULL OR pending_id ~ '^[0-9a-f]{16}$');
    END IF;
END $$;

-- 4. 兌現用索引：`WHERE pending_id=$1 AND session_id=$2`。
--    ⚠️ 欄位順序 (pending_id, session_id) 是刻意的——pending_id 選擇性遠高於
--    session_id（前者每張 token 唯一，後者一個 session 可能有多列）。
--    ⛔ 不建 UNIQUE：pending_id 是 token 的摘要、理論上唯一，但 UNIQUE 會讓
--    一次天文數字級的碰撞從「兩列並存」升級成「confirm.request 直接寫不進去」。
CREATE INDEX IF NOT EXISTS idx_agent_confirmation_tokens_pending
    ON agent_confirmation_tokens (pending_id, session_id);

DO $$
DECLARE total INTEGER; filled INTEGER;
BEGIN
    SELECT COUNT(*), COUNT(pending_id) INTO total, filled
      FROM agent_confirmation_tokens;
    RAISE NOTICE '✅ agent_confirmation_tokens.pending_id 就緒：% / % 列已有值', filled, total;
    IF filled <> total THEN
        RAISE EXCEPTION '回填未完成：% 列仍為 NULL（⛔ 大聲失敗，不留半套狀態）', total - filled;
    END IF;
END $$;
