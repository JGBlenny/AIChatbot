-- =====================================================
-- agentic-mcp-orchestration 任務 3.3：knowledge_base 審核旗標（R11.6，DSP-012 選項 A）
--
-- 背景（design.md 元件 5 DSP-012 段）：DSP-012 裁決同時補上 design 原假設缺的
--   資料面——原文寫「售前大綱由**已審核**知識列組裝」，但 `knowledge_base`
--   實查**查無任何審核旗標**（`grep -rniE "approved_by|is_approved|review_status"
--   rag-orchestrator/models/ rag-orchestrator/database/` 零命中；正對照組同法
--   搜 `target_user` 有命中）⇒ 現況等於「有 KB 寫入權＝有 system prompt 寫入權」。
--   依 R11.6 增設審核旗標，`build_prospect_outline` SHALL 過濾未審核列。
--
-- 比照 `20260904_create_help_center_pages.sql` 的 `approved_by text` 欄位型別，
-- 與 `20260904_api_keys_agent_scope.sql` 的驗證區塊寫法。
--
-- 語義：`outline_approved_by IS NOT NULL` 的列才得進 prospect 大綱組裝
--   （`OutlineAssembler.build_prospect_outline`）；⚠️ **不影響** `kb.get` 整數 id
--   取回當引用來源——那條路徑走既有的可見性謂詞與保留分類排除，與本旗標無關。
--
-- 冪等：ADD COLUMN IF NOT EXISTS（PostgreSQL 9.6+）。重跑無副作用。
-- 執行：由業主以 database/migrate.sh --apply 執行；⛔ 本任務只寫檔不跑、
--   不對 aichatbot_admin 執行任何 SQL。
-- =====================================================

ALTER TABLE knowledge_base
    ADD COLUMN IF NOT EXISTS outline_approved_by text NULL,
    ADD COLUMN IF NOT EXISTS outline_approved_at timestamptz NULL;

COMMENT ON COLUMN knowledge_base.outline_approved_by IS
    'agentic-mcp-orchestration 3.3（R11.6）：核可此列進售前大綱組裝者；NULL＝未審核、排除於 build_prospect_outline。';
COMMENT ON COLUMN knowledge_base.outline_approved_at IS
    'agentic-mcp-orchestration 3.3（R11.6）：核可時間戳；與 outline_approved_by 成對寫入。';

DO $$
DECLARE n INTEGER;
BEGIN
    SELECT COUNT(*) INTO n
      FROM information_schema.columns
     WHERE table_name = 'knowledge_base'
       AND column_name IN ('outline_approved_by', 'outline_approved_at');
    IF n <> 2 THEN
        RAISE EXCEPTION 'knowledge_base 的審核旗標兩欄未就緒（實際 % 欄）——大聲失敗', n;
    END IF;
    RAISE NOTICE '✅ knowledge_base.outline_approved_by／outline_approved_at 就緒';
END $$;
