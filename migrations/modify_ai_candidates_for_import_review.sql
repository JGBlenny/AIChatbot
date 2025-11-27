-- 修改 ai_generated_knowledge_candidates 表以支援規格書/外部檔案審核
-- 實施方案 A：擴充現有審核表，不新建表
-- 創建日期：2025-11-23

-- =====================================================
-- Step 1: 移除 test_scenario_id NOT NULL 約束
-- =====================================================
-- 原因：規格書產生的知識不需要綁定測試情境

ALTER TABLE ai_generated_knowledge_candidates
ALTER COLUMN test_scenario_id DROP NOT NULL;

COMMENT ON COLUMN ai_generated_knowledge_candidates.test_scenario_id IS
'測試情境 ID（對話記錄審核時必填，規格書審核時為 NULL）';

-- =====================================================
-- Step 2: 新增來源類型欄位
-- =====================================================

-- 來源類型（區分不同的審核流程）
ALTER TABLE ai_generated_knowledge_candidates
ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) DEFAULT 'ai_generated';

COMMENT ON COLUMN ai_generated_knowledge_candidates.source_type IS
'來源類型：ai_generated（AI 生成，有 test_scenario_id）, spec_import（規格書匯入）, external_file（外部檔案）, line_chat（LINE 對話記錄）';

-- 匯入來源（更細緻的分類）
ALTER TABLE ai_generated_knowledge_candidates
ADD COLUMN IF NOT EXISTS import_source VARCHAR(50);

COMMENT ON COLUMN ai_generated_knowledge_candidates.import_source IS
'匯入來源：system_export（系統匯出）, external_excel（外部 Excel）, external_json（外部 JSON）, spec_docx（規格書 Word）, spec_pdf（規格書 PDF）';

-- =====================================================
-- Step 3: 新增規格書/外部檔案相關欄位
-- =====================================================

-- 規格書檔名
ALTER TABLE ai_generated_knowledge_candidates
ADD COLUMN IF NOT EXISTS source_file_name VARCHAR(255);

COMMENT ON COLUMN ai_generated_knowledge_candidates.source_file_name IS
'來源檔案名稱（規格書或外部檔案）';

-- 關鍵字（從匯入檔案解析）
ALTER TABLE ai_generated_knowledge_candidates
ADD COLUMN IF NOT EXISTS keywords TEXT[];

-- 優先級（0-10）
ALTER TABLE ai_generated_knowledge_candidates
ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 0;

-- 適用範圍
ALTER TABLE ai_generated_knowledge_candidates
ADD COLUMN IF NOT EXISTS scope VARCHAR(20) DEFAULT 'global';

-- 廠商 ID
ALTER TABLE ai_generated_knowledge_candidates
ADD COLUMN IF NOT EXISTS vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE;

-- 業務類型
ALTER TABLE ai_generated_knowledge_candidates
ADD COLUMN IF NOT EXISTS business_types TEXT[];

-- 目標用戶
ALTER TABLE ai_generated_knowledge_candidates
ADD COLUMN IF NOT EXISTS target_user TEXT;

-- =====================================================
-- Step 4: 新增約束檢查
-- =====================================================

-- 確保 source_type 的值合法
ALTER TABLE ai_generated_knowledge_candidates
DROP CONSTRAINT IF EXISTS check_ai_candidates_source_type;

ALTER TABLE ai_generated_knowledge_candidates
ADD CONSTRAINT check_ai_candidates_source_type
CHECK (source_type IN ('ai_generated', 'spec_import', 'external_file', 'line_chat'));

-- 確保 priority 範圍
ALTER TABLE ai_generated_knowledge_candidates
DROP CONSTRAINT IF EXISTS check_ai_candidates_priority;

ALTER TABLE ai_generated_knowledge_candidates
ADD CONSTRAINT check_ai_candidates_priority
CHECK (priority >= 0 AND priority <= 10);

-- 確保 scope 的值合法
ALTER TABLE ai_generated_knowledge_candidates
DROP CONSTRAINT IF EXISTS check_ai_candidates_scope;

ALTER TABLE ai_generated_knowledge_candidates
ADD CONSTRAINT check_ai_candidates_scope
CHECK (scope IN ('global', 'vendor_specific'));

-- =====================================================
-- Step 5: 新增索引
-- =====================================================

-- source_type 索引（用於篩選不同來源）
CREATE INDEX IF NOT EXISTS idx_ai_candidates_source_type
ON ai_generated_knowledge_candidates(source_type);

-- vendor_id 索引
CREATE INDEX IF NOT EXISTS idx_ai_candidates_vendor
ON ai_generated_knowledge_candidates(vendor_id);

-- keywords GIN 索引（用於關鍵字搜尋）
CREATE INDEX IF NOT EXISTS idx_ai_candidates_keywords
ON ai_generated_knowledge_candidates USING GIN(keywords);

-- business_types GIN 索引
CREATE INDEX IF NOT EXISTS idx_ai_candidates_business_types
ON ai_generated_knowledge_candidates USING GIN(business_types);

-- priority 索引（用於排序）
CREATE INDEX IF NOT EXISTS idx_ai_candidates_priority
ON ai_generated_knowledge_candidates(priority DESC);

-- =====================================================
-- Step 6: 更新現有資料
-- =====================================================

-- 將現有的 AI 生成知識標記為 'ai_generated'
UPDATE ai_generated_knowledge_candidates
SET source_type = 'ai_generated'
WHERE source_type IS NULL
  AND test_scenario_id IS NOT NULL;

-- =====================================================
-- Step 7: 驗證
-- =====================================================

-- 檢查表結構
DO $$
BEGIN
    -- 檢查 test_scenario_id 是否變為 nullable
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ai_generated_knowledge_candidates'
          AND column_name = 'test_scenario_id'
          AND is_nullable = 'NO'
    ) THEN
        RAISE EXCEPTION 'test_scenario_id 仍然是 NOT NULL';
    END IF;

    -- 檢查 source_type 欄位是否存在
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ai_generated_knowledge_candidates'
          AND column_name = 'source_type'
    ) THEN
        RAISE EXCEPTION 'source_type 欄位不存在';
    END IF;

    RAISE NOTICE 'Migration 執行成功！';
END $$;

-- =====================================================
-- 使用範例
-- =====================================================

-- 範例 1：對話記錄審核（有 test_scenario_id）
/*
INSERT INTO ai_generated_knowledge_candidates (
    test_scenario_id,
    source_type,
    import_source,
    question,
    generated_answer,
    status
) VALUES (
    123,              -- 綁定測試情境
    'line_chat',      -- 來源類型
    NULL,             -- 不需要 import_source
    '問題內容',
    '答案內容',
    'pending_review'
);
*/

-- 範例 2：規格書審核（無 test_scenario_id）
/*
INSERT INTO ai_generated_knowledge_candidates (
    test_scenario_id,
    source_type,
    import_source,
    source_file_name,
    question,
    generated_answer,
    keywords,
    priority,
    scope,
    vendor_id,
    status
) VALUES (
    NULL,                  -- 不綁定測試情境
    'spec_import',         -- 來源類型
    'spec_docx',           -- 匯入來源
    '產品規格書_v2.docx',
    '問題摘要',
    '答案內容',
    ARRAY['產品', '規格'],
    5,                     -- 優先級
    'global',
    NULL,
    'pending_review'
);
*/

-- 範例 3：外部 Excel 審核
/*
INSERT INTO ai_generated_knowledge_candidates (
    test_scenario_id,
    source_type,
    import_source,
    source_file_name,
    question,
    generated_answer,
    business_types,
    target_user,
    status
) VALUES (
    NULL,
    'external_file',
    'external_excel',
    'FAQ_20251123.xlsx',
    '問題摘要',
    '答案內容',
    ARRAY['售後服務'],
    '客戶',
    'pending_review'
);
*/
