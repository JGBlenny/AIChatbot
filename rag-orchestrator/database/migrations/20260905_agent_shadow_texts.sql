-- =====================================================
-- agentic-mcp-orchestration 任務 4.1：ShadowRunner 全文比對表
--
-- 背景（design.md 元件 7／資料模型）：`ShadowRunner` 每輪影子回合把結構化
--   `ShadowRecord`（雜湊／長度／diff_flags／成本，⛔ 無原文）落
--   `usage_events.decision_snapshot.agent_shadow`；人工比對「新舊鏈答案
--   到底差在哪」需要看得到全文，這份全文只存這一張獨立表，且僅限
--   `prospect`（`services/agent/shadow.py:ShadowRunner._write_texts` 只在
--   `identity.resolved_audience() == "prospect"` 時才寫）。
--
-- ⚠️ 全文原文落地是額外的外洩面——這是刻意的取捨（design 明列），代價用
--   兩條線收斂：①只收 prospect（無租客個資問題）；②30 天清（見下方清理
--   指令，⛔ 本檔不建 cron，清理由業主排程執行）。
--
-- 讀取端點（`GET /api/v1/agent/shadow-texts` 或同等）需 X-API-Key，
--   屬子任務 5.x，⛔ 本檔只建表。
--
-- 30 天清理（業主排程執行，例如每日 cron 呼叫 psql -c）：
--   DELETE FROM agent_shadow_texts WHERE created_at < now() - interval '30 days';
--
-- 冪等：CREATE TABLE / CREATE INDEX 皆 IF NOT EXISTS。
-- ⛔ 本檔只建結構、不寫入任何列；線上執行由業主依 runbook 操作。
-- =====================================================

CREATE TABLE IF NOT EXISTS agent_shadow_texts (
    id             serial PRIMARY KEY,
    session_id     text NOT NULL,
    trace_id       text NOT NULL,
    agent_answer   text NOT NULL,
    old_answer     text NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE agent_shadow_texts IS
    'agentic-mcp-orchestration 4.1：ShadowRunner 全文比對（僅 prospect、保存 30 天）。'
    '⛔ 不是主計量表，decision_snapshot.agent_shadow 才是每輪落地的結構化紀錄。';

-- 依 session／trace 查（人工比對、清理排查用）。
CREATE INDEX IF NOT EXISTS idx_agent_shadow_texts_session
    ON agent_shadow_texts (session_id);

-- 30 天清理指令依 created_at 篩選，先建索引避免將來資料量大時全表掃描。
CREATE INDEX IF NOT EXISTS idx_agent_shadow_texts_created_at
    ON agent_shadow_texts (created_at);

DO $$
DECLARE n INTEGER;
BEGIN
    SELECT COUNT(*) INTO n FROM agent_shadow_texts;
    RAISE NOTICE '✅ agent_shadow_texts 就緒：% 筆', n;
END $$;
