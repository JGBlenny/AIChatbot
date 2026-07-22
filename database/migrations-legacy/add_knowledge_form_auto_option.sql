-- =====================================================
-- 知識庫表單自動選擇功能
-- 日期：2025-02-05
-- 功能：新增 auto 選項，讓系統智能判斷是否需要觸發表單
-- =====================================================

BEGIN;

-- 1. 更新 trigger_form_condition 欄位類型和預設值
ALTER TABLE knowledge_base
ALTER COLUMN trigger_form_condition TYPE VARCHAR(20),
ALTER COLUMN trigger_form_condition SET DEFAULT 'always';

-- 2. 新增 CHECK 約束，支援多種觸發條件
DO $$
BEGIN
    -- 先檢查約束是否存在，避免重複添加
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'check_trigger_form_condition'
        AND conrelid = 'knowledge_base'::regclass
    ) THEN
        ALTER TABLE knowledge_base
        ADD CONSTRAINT check_trigger_form_condition
        CHECK (trigger_form_condition IN ('always', 'auto', 'never', 'conditional'));

        RAISE NOTICE '✅ 新增 check_trigger_form_condition 約束';
    ELSE
        RAISE NOTICE 'ℹ️ check_trigger_form_condition 約束已存在';
    END IF;
END $$;

-- 3. 新增條件欄位（用於 conditional 模式）
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS trigger_conditions JSONB;

-- 4. 新增自動判斷的關鍵字設定（系統級）
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS auto_keywords JSONB DEFAULT '{
    "action_words": ["申請", "辦理", "報名", "預約", "登記", "提交", "要求"],
    "query_words": ["多少", "什麼", "哪裡", "何時", "是否", "有沒有", "怎麼"]
}'::jsonb;

-- 5. 更新欄位註釋
COMMENT ON COLUMN knowledge_base.trigger_form_condition IS
'表單觸發條件：
- always: 總是觸發表單（預設）
- auto: 根據用戶意圖自動判斷
- never: 永不觸發表單
- conditional: 根據自定義條件觸發';

COMMENT ON COLUMN knowledge_base.trigger_conditions IS
'自定義觸發條件（僅 conditional 模式使用）
範例：{"keywords": ["退租", "解約"], "exclude": ["詢問", "了解"]}';

COMMENT ON COLUMN knowledge_base.auto_keywords IS
'auto 模式的關鍵字配置
- action_words: 觸發表單的動作詞
- query_words: 不觸發表單的查詢詞';

-- 6. 更新現有資料（保持向後相容）
UPDATE knowledge_base
SET trigger_form_condition = 'always'
WHERE trigger_form_condition IS NULL
   OR trigger_form_condition = '';

-- 7. 創建索引以優化查詢
CREATE INDEX IF NOT EXISTS idx_kb_trigger_form_condition
ON knowledge_base(trigger_form_condition)
WHERE form_id IS NOT NULL;

COMMIT;

-- =====================================================
-- 驗證 Migration
-- =====================================================

-- 顯示更新結果
SELECT
    '📊 觸發條件統計' as "報告",
    trigger_form_condition as "觸發條件",
    COUNT(*) as "數量",
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as "百分比"
FROM knowledge_base
WHERE form_id IS NOT NULL
GROUP BY trigger_form_condition
ORDER BY COUNT(*) DESC;

-- 檢查約束
SELECT
    conname as "約束名稱",
    pg_get_constraintdef(oid) as "約束定義"
FROM pg_constraint
WHERE conrelid = 'knowledge_base'::regclass
  AND conname LIKE '%trigger%';

-- 顯示新欄位
SELECT
    column_name as "欄位名稱",
    data_type as "資料類型",
    column_default as "預設值"
FROM information_schema.columns
WHERE table_name = 'knowledge_base'
  AND column_name IN ('trigger_form_condition', 'trigger_conditions', 'auto_keywords')
ORDER BY ordinal_position;