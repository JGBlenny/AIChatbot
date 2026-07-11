-- ============================================================
-- trigger-vocabulary-debt：usage_events 檢索仲裁分數欄（spec trigger-vocabulary-debt 任務 3.1 M1）
-- 灰帶分析用遙測欄位：記錄每次查詢中 knowledge / SOP 兩軌的最高分數，
-- 以及最終仲裁走哪條決策路徑（knowledge / sop / fallback 等）。
-- 加性變更：NOT NULL 不加（歷史列保持 NULL）。冪等：ADD COLUMN IF NOT EXISTS。
-- ============================================================

ALTER TABLE usage_events
  ADD COLUMN IF NOT EXISTS knowledge_score NUMERIC(4,3),   -- RAG 知識庫最高命中分數（0–1），NULL 表示未走知識檢索
  ADD COLUMN IF NOT EXISTS sop_score       NUMERIC(4,3),   -- SOP 流程最高命中分數（0–1），NULL 表示未走 SOP 檢索
  ADD COLUMN IF NOT EXISTS decision_case   VARCHAR(60);    -- 仲裁決策路徑標籤，如 knowledge_win / sop_win / both_low / fallback

DO $$
DECLARE n INT;
BEGIN
    SELECT count(*) INTO n
    FROM information_schema.columns
    WHERE table_name = 'usage_events'
      AND column_name IN ('knowledge_score', 'sop_score', 'decision_case');
    RAISE NOTICE '✅ usage_events 分數欄：% / 3 欄就緒（knowledge_score, sop_score, decision_case）', n;
END $$;
