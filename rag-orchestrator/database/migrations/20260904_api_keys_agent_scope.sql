-- =====================================================
-- agentic-mcp-orchestration 任務 1.7：api_keys 加 agent 作用域兩欄
--
-- 背景（design.md 元件 4「額度落點」／決策 13）：DSP-011 把「額度」定為
--   本系統對呼叫者的唯一控制。既有的內部流量判定（services/usage_metering.py
--   的 INTERNAL_RULES）看的是**請求字串**（session_id 前綴 backtest_／loop_…），
--   呼叫方可自行決定 ⇒ 等於可以自己把額度關掉。
--   `/mcp` 路徑因此改由 **API key 紀錄**決定：
--     is_internal  — 這把 key 的流量是否算內部（不計額度）
--     vendor_ids   — 這把 key 可代表哪些業者；**NULL ＝ 不限**（⛔ 不是「空陣列」）
--   `/api/v1/message` 的既有前綴規則不動（另案）。
--
-- 冪等：ADD COLUMN IF NOT EXISTS（PostgreSQL 9.6+）。重跑無副作用。
-- 執行：由業主以 database/migrate.sh --apply 執行；⛔ 本任務只寫檔不跑。
--
-- ⚠️ 語義提醒（勿改回）：`vendor_ids IS NULL` 表示「不限業者」，
--    `vendor_ids = '{}'`（空陣列）表示「哪個業者都不准」。兩者不可混用；
--    程式端 services/agent/mcp_facade.py:parse_identity 依此判 403。
-- =====================================================

ALTER TABLE api_keys
    ADD COLUMN IF NOT EXISTS is_internal boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS vendor_ids  integer[] NULL;

COMMENT ON COLUMN api_keys.is_internal IS
    'agentic-mcp-orchestration 1.7：這把 key 的 /mcp 流量是否算內部（不計額度）。';
COMMENT ON COLUMN api_keys.vendor_ids IS
    'agentic-mcp-orchestration 1.7：這把 key 可代表的業者白名單；NULL ＝ 不限，空陣列 ＝ 全拒。';

DO $$
DECLARE n INTEGER;
BEGIN
    SELECT COUNT(*) INTO n
      FROM information_schema.columns
     WHERE table_name = 'api_keys'
       AND column_name IN ('is_internal', 'vendor_ids');
    IF n <> 2 THEN
        RAISE EXCEPTION 'api_keys 的 agent 作用域兩欄未就緒（實際 % 欄）——大聲失敗', n;
    END IF;
    RAISE NOTICE '✅ api_keys.is_internal／vendor_ids 就緒';
END $$;
