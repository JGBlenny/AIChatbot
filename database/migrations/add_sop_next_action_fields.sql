-- Migration: 擴展 vendor_sop_items 支援後續動作
-- Date: 2026-01-22
-- Purpose: 讓 SOP 項目支援 4 種觸發模式（資訊型、排查型、行動型、緊急型）
--
-- 四種 SOP 類型：
--   1. 資訊型 (trigger_mode='none'): 純資訊，無後續動作（例如：垃圾規範）
--   2. 排查型 (trigger_mode='manual'): 排查無效後，用戶說關鍵詞才觸發（例如：冷氣不冷）
--   3. 行動型 (trigger_mode='immediate'): 返回 SOP 後立即詢問是否執行（例如：繳租登記）
--   4. 緊急型 (trigger_mode='auto'): 返回 SOP 的同時自動觸發（例如：天花板漏水）
--
-- 設計思路：
--   1. trigger_mode: 觸發模式 (none/manual/immediate/auto)
--   2. next_action: 定義後續動作 (none/form_fill/api_call/form_then_api)
--   3. next_form_id: 指定要觸發的表單
--   4. next_api_config: 指定要調用的 API
--   5. trigger_keywords: 觸發關鍵詞（manual/immediate 模式使用）
--   6. immediate_prompt: 立即詢問提示語（immediate 模式使用）
--   7. followup_prompt: 後續動作的引導語

BEGIN;

-- ==========================================
-- 1. 新增欄位
-- ==========================================
ALTER TABLE vendor_sop_items
ADD COLUMN IF NOT EXISTS trigger_mode VARCHAR(20) DEFAULT 'none',
ADD COLUMN IF NOT EXISTS next_action VARCHAR(50) DEFAULT 'none',
ADD COLUMN IF NOT EXISTS next_form_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS next_api_config JSONB,
ADD COLUMN IF NOT EXISTS trigger_keywords TEXT[],
ADD COLUMN IF NOT EXISTS immediate_prompt TEXT,
ADD COLUMN IF NOT EXISTS followup_prompt TEXT;

-- ==========================================
-- 2. 新增約束
-- ==========================================
ALTER TABLE vendor_sop_items
ADD CONSTRAINT check_trigger_mode
CHECK (trigger_mode IN ('none', 'manual', 'immediate', 'auto')),

ADD CONSTRAINT check_next_action
CHECK (next_action IN ('none', 'form_fill', 'api_call', 'form_then_api'));

-- ==========================================
-- 3. 新增索引
-- ==========================================
CREATE INDEX IF NOT EXISTS idx_vendor_sop_items_trigger_mode
ON vendor_sop_items(trigger_mode)
WHERE trigger_mode != 'none';

CREATE INDEX IF NOT EXISTS idx_vendor_sop_items_next_action
ON vendor_sop_items(next_action)
WHERE next_action != 'none';

-- ==========================================
-- 4. 新增外鍵約束
-- ==========================================
ALTER TABLE vendor_sop_items
ADD CONSTRAINT fk_sop_next_form
FOREIGN KEY (next_form_id)
REFERENCES form_schemas(form_id)
ON DELETE SET NULL;

-- ==========================================
-- 5. 新增註解
-- ==========================================
COMMENT ON COLUMN vendor_sop_items.trigger_mode IS '觸發模式：none(資訊型), manual(排查型), immediate(行動型), auto(緊急型)';
COMMENT ON COLUMN vendor_sop_items.next_action IS '後續動作類型：none(無), form_fill(填表單), api_call(調用API), form_then_api(先填表單再調用API)';
COMMENT ON COLUMN vendor_sop_items.next_form_id IS '後續動作要觸發的表單 ID (對應 form_schemas.form_id)';
COMMENT ON COLUMN vendor_sop_items.next_api_config IS '後續動作要調用的 API 配置 (JSON格式)';
COMMENT ON COLUMN vendor_sop_items.trigger_keywords IS '觸發關鍵詞陣列。manual模式：自定義（例如：["還是不行", "試過了"]）；immediate模式：通用肯定詞（["是", "要", "好"]）';
COMMENT ON COLUMN vendor_sop_items.immediate_prompt IS '立即詢問提示語（immediate 模式使用，例如：「📋 是否要登記本月租金繳納記錄？」）';
COMMENT ON COLUMN vendor_sop_items.followup_prompt IS '觸發後續動作時的引導語（例如：「好的，我來協助您提交維修請求」）';

COMMIT;

-- ==========================================
-- 驗證
-- ==========================================
DO $$
BEGIN
    -- 檢查欄位是否成功新增
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vendor_sop_items'
        AND column_name = 'trigger_mode'
    ) THEN
        RAISE EXCEPTION 'trigger_mode 欄位新增失敗';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vendor_sop_items'
        AND column_name = 'next_action'
    ) THEN
        RAISE EXCEPTION 'next_action 欄位新增失敗';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vendor_sop_items'
        AND column_name = 'next_form_id'
    ) THEN
        RAISE EXCEPTION 'next_form_id 欄位新增失敗';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vendor_sop_items'
        AND column_name = 'next_api_config'
    ) THEN
        RAISE EXCEPTION 'next_api_config 欄位新增失敗';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vendor_sop_items'
        AND column_name = 'trigger_keywords'
    ) THEN
        RAISE EXCEPTION 'trigger_keywords 欄位新增失敗';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vendor_sop_items'
        AND column_name = 'immediate_prompt'
    ) THEN
        RAISE EXCEPTION 'immediate_prompt 欄位新增失敗';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vendor_sop_items'
        AND column_name = 'followup_prompt'
    ) THEN
        RAISE EXCEPTION 'followup_prompt 欄位新增失敗';
    END IF;

    RAISE NOTICE '✓ vendor_sop_items 表擴展成功（新增 7 個欄位）';
END $$;
