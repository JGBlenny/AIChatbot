-- ============================================================
-- usage-metering：使用事件表（spec usage-metering 任務 1.1）
-- 每次 /api/v1/message 一筆；計費三軌原料（訊息/對話/token 成本）；
-- 不存問題原文與回答全文（R7，message_len 為唯一內容痕跡）。
-- request_id 冪等鍵：雙落點（middleware/串流 finally）防重。
-- 冪等：IF NOT EXISTS。
-- ============================================================

CREATE TABLE IF NOT EXISTS usage_events (
    id                BIGSERIAL PRIMARY KEY,
    request_id        UUID UNIQUE NOT NULL,
    ts                TIMESTAMPTZ NOT NULL,
    date_tpe          DATE NOT NULL,               -- Asia/Taipei 日界（寫入時計算，計費口徑）
    vendor_id         INTEGER,
    mode              VARCHAR(10),
    target_user       VARCHAR(30),
    user_type         VARCHAR(20) NOT NULL,        -- tenant|landlord|property_manager|system_admin|prospect|internal|unknown
    role_id           VARCHAR(50),
    user_id           VARCHAR(100),
    session_id        VARCHAR(120),
    channel           VARCHAR(20) NOT NULL DEFAULT 'web',
    is_internal       BOOLEAN NOT NULL DEFAULT FALSE,
    internal_kind     VARCHAR(20),                 -- backtest|loop|smoke|dev
    message_len       INTEGER NOT NULL DEFAULT 0,
    processing_path   VARCHAR(60),
    answer_source     VARCHAR(40),
    status            VARCHAR(10) NOT NULL,        -- success|error
    http_status       SMALLINT,
    duration_ms       INTEGER,
    llm_calls         SMALLINT NOT NULL DEFAULT 0,
    prompt_tokens     INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    est_cost_usd      NUMERIC(10,6),               -- 單價表缺模型→NULL（不臆造）
    model_breakdown   JSONB
);

CREATE INDEX IF NOT EXISTS idx_usage_date_vendor ON usage_events (date_tpe, vendor_id, is_internal);
CREATE INDEX IF NOT EXISTS idx_usage_session ON usage_events (session_id);

DO $$
DECLARE n INT;
BEGIN
    SELECT count(*) INTO n FROM information_schema.columns WHERE table_name='usage_events';
    RAISE NOTICE '✅ usage_events：% 欄（預期 25 含 id）＋2 索引', n;
END $$;
