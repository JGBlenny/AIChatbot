-- =====================================================
-- agentic-mcp-orchestration 任務 2.4：確認 token 表
--
-- 背景：design.md 資料模型
--   agent_confirmation_tokens(token PK, session_id, payload_sha256,
--                             summary_sha256, expires_at, redeemed, created_at)
--   `confirm.request` 寫入；寫入工具（`jgb2.action.*`，子 spec agent-write-tools）
--   以單述句 `UPDATE … WHERE token=$1 AND session_id=$2 AND redeemed=false
--   AND expires_at>now() RETURNING …` 兌現。⛔ M0–M3 不註冊任何 `jgb2.action.*`，
--   本表在 M1 先建好，供 `confirm.request` 與 `redeem_token()` 的整合測試使用。
--
-- 為什麼 token 是 PRIMARY KEY（而不是另加一個代理鍵）：
--   兌現路徑唯一的查詢條件就是 token，PK 的唯一索引即是兌現要的索引；
--   多一個代理鍵只會讓「同一個 token 出現兩列」變成可能。
--
-- ⚠️ 本表存的是**雜湊**，不存 payload／summary 原文——
--   確認的內容可能含合約編號、金額等資料，落地即是新的外洩面。
--   兌現只需要「送來的 payload 是不是當初那一份」，雜湊就夠了。
--
-- 冪等：CREATE TABLE / CREATE INDEX 皆 IF NOT EXISTS；
--   CHECK 約束以 pg_constraint 查名後才 ADD（比照
--   20260904_create_help_center_pages.sql 的寫法）。
--
-- ⛔ 本檔只建結構、不寫入任何列；線上執行由業主依 runbook 操作。
-- =====================================================

CREATE TABLE IF NOT EXISTS agent_confirmation_tokens (
    token           text PRIMARY KEY,
    session_id      text NOT NULL,
    payload_sha256  text NOT NULL,
    summary_sha256  text NOT NULL,
    expires_at      timestamptz NOT NULL,
    redeemed        boolean NOT NULL DEFAULT false,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- 雜湊欄位形狀約束：sha256 十六進位一律 64 字。
-- 這條擋的是「有人改用別的摘要演算法卻沒改兌現端」——長度不合當場失敗，
-- 好過兌現時靜默比不中、每一次確認都變成 CONFIRMATION_REQUIRED。
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'agent_confirmation_tokens_sha256_shape'
    ) THEN
        ALTER TABLE agent_confirmation_tokens
            ADD CONSTRAINT agent_confirmation_tokens_sha256_shape
            CHECK (
                payload_sha256 ~ '^[0-9a-f]{64}$'
                AND summary_sha256 ~ '^[0-9a-f]{64}$'
            );
    END IF;
END $$;

-- session_id 非空：跨 session 兌現的防線之一是 `WHERE session_id = $2`，
-- 空字串會讓那條謂詞失去意義。
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'agent_confirmation_tokens_session_not_blank'
    ) THEN
        ALTER TABLE agent_confirmation_tokens
            ADD CONSTRAINT agent_confirmation_tokens_session_not_blank
            CHECK (length(btrim(session_id)) > 0);
    END IF;
END $$;

-- 依 session 查（trace／清理用）。兌現本身走 PK，不靠這條。
CREATE INDEX IF NOT EXISTS idx_agent_confirmation_tokens_session
    ON agent_confirmation_tokens (session_id);

-- 過期列清理用（保留期政策另議；⛔ 本檔不建 cron、不刪任何列）。
CREATE INDEX IF NOT EXISTS idx_agent_confirmation_tokens_expires
    ON agent_confirmation_tokens (expires_at);

DO $$
DECLARE n INTEGER;
BEGIN
    SELECT COUNT(*) INTO n FROM agent_confirmation_tokens;
    RAISE NOTICE '✅ agent_confirmation_tokens 就緒：% 筆', n;
END $$;
