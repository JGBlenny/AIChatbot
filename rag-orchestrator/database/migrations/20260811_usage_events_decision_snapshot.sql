-- Migration：usage_events 加決策快照兩欄（spec retrieval-decision-layer 任務 1.2｜R8.3）
-- 日期: 2026-08-11
-- 目的：E-5（多輪路由非決定性，run2 vs run3 14/107 輪路由類別不同）必須可事後歸因。
--       決策層每輪把「輸入訊號＋門檻值＋規則版本＋判定」落成一筆快照，任何路由不一致
--       都能離線比對是哪個訊號翻的，而不是重跑一輪憑印象猜。
--       usage_events 是每請求一事件的計量表，本 migration 僅補兩欄，不動既有欄位/資料。
--
-- 加性冪等：ADD COLUMN IF NOT EXISTS，重跑安全、無破壞性。應用層以
--   information_schema 偵測降級（services/usage_metering.py 的 _detect_decision_cols），
--   欄位未建時事件本體照寫、兩新欄略過 → 部署順序（先套 migration 或先推程式）皆安全。
--
--   decision_snapshot ── 本輪決策快照（jsonb，沿 model_breakdown 先例）：
--                        RoutingSignals（kb/sop top1 final、gray_zone、識別碼訊號、
--                        會話狀態、top1 分類）＋門檻值＋規則版本＋verdict。
--                        同輪二次決策（如 exit_requery 後重判）時舊快照落 `prior` 陣列，
--                        不靜默覆蓋——同輪擺盪本身就是 E-5 的證據。
--   facet_event      ── 本輪面向事件（VARCHAR(30)）：enter / stay / exit_requery /
--                        degrade_knowledge / degrade_honest / reentry_suppressed / none。
--                        與既有 facet_key（哪個面向）正交：facet_key 答「在哪」，
--                        facet_event 答「這輪發生什麼」，逃生門（C3）成效直接 SQL 可查。

ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS decision_snapshot JSONB;
ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS facet_event VARCHAR(30);

COMMENT ON COLUMN usage_events.decision_snapshot IS
  '決策層本輪快照（retrieval-decision-layer R8.3；訊號＋門檻＋規則版本＋verdict，同輪重判落 prior）';
COMMENT ON COLUMN usage_events.facet_event IS
  '本輪面向事件（retrieval-decision-layer R8.3；enter/stay/exit_requery/degrade_*/reentry_suppressed/none）';

-- 歸因查詢多以「近期非內部事件、有快照者」為母體，索引只建部分索引（不膨脹既有寫入成本）
CREATE INDEX IF NOT EXISTS idx_usage_facet_event
    ON usage_events (facet_event, date_tpe) WHERE facet_event IS NOT NULL;

DO $$
DECLARE n INT;
BEGIN
    SELECT count(*) INTO n FROM information_schema.columns
     WHERE table_name = 'usage_events'
       AND column_name IN ('decision_snapshot', 'facet_event');
    RAISE NOTICE '✅ usage_events 決策快照欄：%/2', n;
END $$;
