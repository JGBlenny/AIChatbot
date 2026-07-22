-- ==========================================
-- 知識庫動作系統資料庫遷移腳本
-- 版本: 1.0.0
-- 日期: 2026-01-16
-- 說明: 添加 action_type 和 api_config 欄位以支援表單、API、知識庫的靈活組合
-- 相關文檔: docs/design/KNOWLEDGE_ACTION_SYSTEM_DESIGN.md
-- ==========================================

BEGIN;

-- ==========================================
-- 1. 擴充 knowledge_base 表
-- ==========================================

-- 添加 action_type 欄位
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS action_type VARCHAR(50) DEFAULT 'direct_answer';

-- 添加 api_config 欄位
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS api_config JSONB;

-- 欄位註釋
COMMENT ON COLUMN knowledge_base.action_type IS '動作類型：direct_answer（純知識問答）, form_fill（表單+知識）, api_call（API+知識）, form_then_api（表單+API+知識）';
COMMENT ON COLUMN knowledge_base.api_config IS 'API 調用配置（JSONB），包含 endpoint, params, combine_with_knowledge 等設定';

-- 索引
CREATE INDEX IF NOT EXISTS idx_kb_action_type ON knowledge_base(action_type);

-- ==========================================
-- 2. 擴充 form_schemas 表
-- ==========================================

-- 添加 on_complete_action 欄位
ALTER TABLE form_schemas
ADD COLUMN IF NOT EXISTS on_complete_action VARCHAR(50) DEFAULT 'show_knowledge';

-- 添加 api_config 欄位
ALTER TABLE form_schemas
ADD COLUMN IF NOT EXISTS api_config JSONB;

-- 欄位註釋
COMMENT ON COLUMN form_schemas.on_complete_action IS '表單完成後動作：show_knowledge（顯示知識答案）, call_api（調用API）, both（兩者都執行）';
COMMENT ON COLUMN form_schemas.api_config IS '表單完成後的 API 調用配置（JSONB），包含 endpoint, param_mapping 等設定';

-- 索引
CREATE INDEX IF NOT EXISTS idx_form_schemas_on_complete_action ON form_schemas(on_complete_action);

-- ==========================================
-- 3. 添加約束檢查（可選）
-- ==========================================

-- 檢查 action_type 的有效值
ALTER TABLE knowledge_base
ADD CONSTRAINT check_action_type
CHECK (action_type IN ('direct_answer', 'form_fill', 'api_call', 'form_then_api'));

-- 檢查 on_complete_action 的有效值
ALTER TABLE form_schemas
ADD CONSTRAINT check_on_complete_action
CHECK (on_complete_action IN ('show_knowledge', 'call_api', 'both'));

-- ==========================================
-- 4. 數據遷移（更新現有數據）
-- ==========================================

-- 將現有的表單觸發知識設置為 form_fill
UPDATE knowledge_base
SET action_type = 'form_fill'
WHERE form_id IS NOT NULL
  AND action_type = 'direct_answer';

-- 檢查是否有 form_intro 欄位（已棄用）
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'knowledge_base'
        AND column_name = 'form_intro'
    ) THEN
        RAISE NOTICE '⚠️  檢測到 form_intro 欄位，建議檢查數據並考慮遷移到 form_schemas';
    END IF;
END $$;

COMMIT;

-- ==========================================
-- 驗證腳本執行結果
-- ==========================================

DO $$
DECLARE
    kb_action_type_exists BOOLEAN;
    kb_api_config_exists BOOLEAN;
    fs_on_complete_action_exists BOOLEAN;
    fs_api_config_exists BOOLEAN;
BEGIN
    -- 檢查 knowledge_base 新欄位
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'knowledge_base'
        AND column_name = 'action_type'
    ) INTO kb_action_type_exists;

    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'knowledge_base'
        AND column_name = 'api_config'
    ) INTO kb_api_config_exists;

    -- 檢查 form_schemas 新欄位
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'form_schemas'
        AND column_name = 'on_complete_action'
    ) INTO fs_on_complete_action_exists;

    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'form_schemas'
        AND column_name = 'api_config'
    ) INTO fs_api_config_exists;

    -- 輸出結果
    IF kb_action_type_exists THEN
        RAISE NOTICE '✅ knowledge_base.action_type 欄位添加成功';
    ELSE
        RAISE WARNING '❌ knowledge_base.action_type 欄位添加失敗';
    END IF;

    IF kb_api_config_exists THEN
        RAISE NOTICE '✅ knowledge_base.api_config 欄位添加成功';
    ELSE
        RAISE WARNING '❌ knowledge_base.api_config 欄位添加失敗';
    END IF;

    IF fs_on_complete_action_exists THEN
        RAISE NOTICE '✅ form_schemas.on_complete_action 欄位添加成功';
    ELSE
        RAISE WARNING '❌ form_schemas.on_complete_action 欄位添加失敗';
    END IF;

    IF fs_api_config_exists THEN
        RAISE NOTICE '✅ form_schemas.api_config 欄位添加成功';
    ELSE
        RAISE WARNING '❌ form_schemas.api_config 欄位添加失敗';
    END IF;
END $$;

-- 顯示遷移統計
SELECT
    '📊 知識庫統計' AS category,
    action_type,
    COUNT(*) AS count
FROM knowledge_base
WHERE is_active = true
GROUP BY action_type
ORDER BY count DESC;
