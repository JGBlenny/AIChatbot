-- =====================================================
-- agentic-mcp-orchestration 任務 1.6：help.read 資料表
--
-- 背景：MCP 工具 help.read 需要一張最小可讀來源表；匯入工具與
--   citable=true 的人工核可流程屬子 spec help-center-source（D3 裁後），
--   本 migration 只建表，不寫入任何列。
--
-- 約束：citable=true 必須有 approved_by（可引用內容必須有人核可）；
--   citable 預設 false，符合 tasks.md 1.6「citable 全 false 直到裁定」。
--
-- 冪等：CREATE TABLE IF NOT EXISTS；約束用 DO 區塊配合
--   IF NOT EXISTS 判斷避免重複 ADD CONSTRAINT 報錯。
-- =====================================================

CREATE TABLE IF NOT EXISTS help_center_pages (
    slug            text PRIMARY KEY,
    title           text NOT NULL,
    text            text NOT NULL,
    version         text NOT NULL,
    source_url      text,
    content_sha256  text NOT NULL,
    citable         boolean NOT NULL DEFAULT false,
    approved_by     text,
    imported_at     timestamptz NOT NULL DEFAULT now()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'help_center_pages_citable_requires_approval'
    ) THEN
        ALTER TABLE help_center_pages
            ADD CONSTRAINT help_center_pages_citable_requires_approval
            CHECK (citable = false OR approved_by IS NOT NULL);
    END IF;
END $$;

DO $$
DECLARE n INTEGER;
BEGIN
    SELECT COUNT(*) INTO n FROM help_center_pages;
    RAISE NOTICE '✅ help_center_pages 就緒：% 筆', n;
END $$;
