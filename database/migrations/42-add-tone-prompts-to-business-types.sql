-- Migration 42: 將業態類型語氣 Prompt 移到資料庫配置
-- 用途：將硬編碼在程式中的語氣 prompt 移至資料庫，實現動態管理
-- 建立時間：2025-10-25
--
-- 背景：
--   目前業態類型的語氣調整 prompt 硬編碼在 llm_answer_optimizer.py 中：
--   - full_service（包租型）：主動承諾語氣
--   - property_management（代管型）：協助引導語氣
--   - system_provider（系統商）：❌ 未定義
--
-- 改進：
--   將語氣 prompt 移至 business_types_config 表，允許管理員動態管理：
--   - tone_description: 業種特性描述
--   - tone_guidelines: 語氣要求（JSONB 格式）
--   - tone_examples: 範例轉換（JSONB 格式）
--   - tone_summary: 簡化版語氣說明（用於 synthesize 和 optimize）

-- ========================================
-- 1. 擴展 business_types_config 表結構
-- ========================================

-- 新增語氣相關欄位
ALTER TABLE business_types_config
ADD COLUMN IF NOT EXISTS tone_description TEXT,
ADD COLUMN IF NOT EXISTS tone_guidelines JSONB,
ADD COLUMN IF NOT EXISTS tone_examples JSONB,
ADD COLUMN IF NOT EXISTS tone_summary JSONB;

-- 新增欄位註釋
COMMENT ON COLUMN business_types_config.tone_description IS '業種特性描述（用於 AI prompt）';
COMMENT ON COLUMN business_types_config.tone_guidelines IS '語氣要求和關鍵詞（JSONB 格式）';
COMMENT ON COLUMN business_types_config.tone_examples IS '語氣轉換範例（JSONB 格式）';
COMMENT ON COLUMN business_types_config.tone_summary IS '簡化版語氣說明（用於答案合成和優化）';

-- ========================================
-- 2. 更新現有資料：full_service（包租型）
-- ========================================

UPDATE business_types_config
SET
    tone_description = '包租型業者 - 提供全方位服務，直接負責租賃管理',
    tone_guidelines = '{
        "requirements": [
            "使用主動承諾語氣：「我們會」、「公司將」、「我們負責」",
            "表達直接負責：「我們處理」、「我們安排」",
            "避免被動引導：不要用「請您聯繫」、「建議」等",
            "展現服務能力：強調公司會主動處理問題"
        ],
        "key_phrases": ["我們會", "公司將", "我們負責", "我們處理", "我們安排"],
        "avoid_phrases": ["請您聯繫", "建議您", "可協助您"]
    }'::jsonb,
    tone_examples = '[
        {
            "wrong": "請您與房東聯繫處理",
            "correct": "我們會立即為您處理"
        },
        {
            "wrong": "建議您先拍照記錄",
            "correct": "我們會協助您處理，請先拍照記錄現場狀況"
        }
    ]'::jsonb,
    tone_summary = '{
        "description": "包租型業者，提供全方位服務",
        "tone": "主動告知、確認、承諾",
        "key_phrases": ["我們會", "公司將"]
    }'::jsonb,
    updated_at = CURRENT_TIMESTAMP
WHERE type_value = 'full_service';

-- ========================================
-- 3. 更新現有資料：property_management（代管型）
-- ========================================

UPDATE business_types_config
SET
    tone_description = '代管型業者 - 協助租客與房東溝通，居中協調',
    tone_guidelines = '{
        "requirements": [
            "使用協助引導語氣：「請您」、「建議」、「可協助」",
            "表達居中協調：「我們可以協助您聯繫」、「我們居中協調」",
            "避免直接承諾：不要用「我們會處理」、「公司負責」等",
            "引導租客行動：提供建議和協助選項"
        ],
        "key_phrases": ["請您", "建議", "可協助", "居中協調", "可以協助您聯繫"],
        "avoid_phrases": ["我們會處理", "公司負責", "公司將立即安排"]
    }'::jsonb,
    tone_examples = '[
        {
            "wrong": "我們會為您處理維修",
            "correct": "建議您先聯繫房東，我們可協助居中協調維修事宜"
        },
        {
            "wrong": "公司將立即安排",
            "correct": "請您先與房東溝通，如需要我們可以協助聯繫"
        }
    ]'::jsonb,
    tone_summary = '{
        "description": "代管型業者，協助租客與房東溝通",
        "tone": "協助引導、建議聯繫",
        "key_phrases": ["請您", "建議", "可協助"]
    }'::jsonb,
    updated_at = CURRENT_TIMESTAMP
WHERE type_value = 'property_management';

-- ========================================
-- 4. 更新現有資料：system_provider（系統商）
-- ========================================

UPDATE business_types_config
SET
    tone_description = '系統商 - 提供系統平台給其他業者使用',
    tone_guidelines = '{
        "requirements": [
            "使用專業技術語氣：「平台功能」、「系統設定」、「功能支援」",
            "表達系統特性：「系統提供」、「平台支援」、「功能包含」",
            "避免服務承諾：不要用「我們會處理」等服務型語句",
            "強調自助操作：引導使用者操作系統功能"
        ],
        "key_phrases": ["平台功能", "系統設定", "系統提供", "平台支援", "功能包含"],
        "avoid_phrases": ["我們會處理", "公司將安排", "請聯繫我們"]
    }'::jsonb,
    tone_examples = '[
        {
            "wrong": "我們會為您設定",
            "correct": "您可在系統設定中調整此功能"
        },
        {
            "wrong": "請聯繫我們處理",
            "correct": "請參考系統操作手冊，或聯繫您的服務業者"
        }
    ]'::jsonb,
    tone_summary = '{
        "description": "系統商，提供平台給其他業者使用",
        "tone": "專業技術、自助操作",
        "key_phrases": ["系統功能", "平台支援"]
    }'::jsonb,
    updated_at = CURRENT_TIMESTAMP
WHERE type_value = 'system_provider';

-- ========================================
-- 5. 驗證查詢
-- ========================================

-- 查詢所有業態的語氣配置
\echo ''
\echo '📊 業態類型語氣配置：'
SELECT
    type_value,
    display_name,
    tone_description,
    jsonb_pretty(tone_summary) as tone_summary_preview
FROM business_types_config
ORDER BY display_order;

-- ========================================
-- 6. 記錄 Migration
-- ========================================

INSERT INTO schema_migrations (id, description, executed_at)
VALUES (42, 'Add tone prompts to business_types_config table', NOW())
ON CONFLICT (id) DO NOTHING;

-- ========================================
-- 完成
-- ========================================

\echo ''
\echo '✅ Migration 42: 業態類型語氣 Prompt 配置完成'
\echo '   - 已擴展 business_types_config 表結構'
\echo '   - 已更新三種業態類型的語氣配置'
\echo '   - full_service: 主動承諾語氣'
\echo '   - property_management: 協助引導語氣'
\echo '   - system_provider: 專業技術語氣（新增）'
\echo ''
\echo '📝 下一步：'
\echo '   1. 修改 llm_answer_optimizer.py 從資料庫讀取語氣配置'
\echo '   2. 測試三種業態類型的語氣轉換'
\echo '   3. 更新前端管理介面（可選）'
