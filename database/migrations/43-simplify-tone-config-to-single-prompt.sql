-- Migration 43: 簡化語氣配置為單一 Prompt 欄位
-- 用途：將複雜的 JSONB 結構簡化為單一 TEXT 欄位
-- 建立時間：2025-10-25
--
-- 背景：
--   Migration 42 建立了複雜的 JSONB 結構：
--   - tone_description (TEXT)
--   - tone_guidelines (JSONB)
--   - tone_examples (JSONB)
--   - tone_summary (JSONB)
--
-- 簡化：
--   實際上語氣配置就是一段 prompt 文字，不需要複雜結構
--   改為單一 tone_prompt (TEXT) 欄位，更簡單直覺

-- ========================================
-- 1. 備份現有資料（合併成完整 prompt）
-- ========================================

-- 為三種業態建立完整的 prompt 文字
UPDATE business_types_config
SET description = CASE type_value
    WHEN 'full_service' THEN '包租型業者語氣配置（已保存於 tone_prompt）'
    WHEN 'property_management' THEN '代管型業者語氣配置（已保存於 tone_prompt）'
    WHEN 'system_provider' THEN '系統商語氣配置（已保存於 tone_prompt）'
    ELSE description
END
WHERE type_value IN ('full_service', 'property_management', 'system_provider');

-- ========================================
-- 2. 新增 tone_prompt 欄位
-- ========================================

ALTER TABLE business_types_config
ADD COLUMN IF NOT EXISTS tone_prompt TEXT;

COMMENT ON COLUMN business_types_config.tone_prompt IS '語氣調整 Prompt（用於 LLM 優化器）';

-- ========================================
-- 3. 將現有資料轉換為 prompt 文字
-- ========================================

-- full_service (包租型)
UPDATE business_types_config
SET tone_prompt = '業種特性：包租型業者 - 提供全方位服務，直接負責租賃管理

語氣要求：
• 使用主動承諾語氣：「我們會」、「公司將」、「我們負責」
• 表達直接負責：「我們處理」、「我們安排」
• 避免被動引導：不要用「請您聯繫」、「建議」等
• 展現服務能力：強調公司會主動處理問題

範例轉換：
❌ 「請您與房東聯繫處理」
✅ 「我們會立即為您處理」

❌ 「建議您先拍照記錄」
✅ 「我們會協助您處理，請先拍照記錄現場狀況」'
WHERE type_value = 'full_service';

-- property_management (代管型)
UPDATE business_types_config
SET tone_prompt = '業種特性：代管型業者 - 協助租客與房東溝通，居中協調

語氣要求：
• 使用協助引導語氣：「請您」、「建議」、「可協助」
• 表達居中協調：「我們可以協助您聯繫」、「我們居中協調」
• 避免直接承諾：不要用「我們會處理」、「公司負責」等
• 引導租客行動：提供建議和協助選項

範例轉換：
❌ 「我們會為您處理維修」
✅ 「建議您先聯繫房東，我們可協助居中協調維修事宜」

❌ 「公司將立即安排」
✅ 「請您先與房東溝通，如需要我們可以協助聯繫」'
WHERE type_value = 'property_management';

-- system_provider (系統商)
UPDATE business_types_config
SET tone_prompt = '業種特性：系統商 - 提供系統平台給其他業者使用

語氣要求：
• 使用專業技術語氣：「平台功能」、「系統設定」、「功能支援」
• 表達系統特性：「系統提供」、「平台支援」、「功能包含」
• 避免服務承諾：不要用「我們會處理」等服務型語句
• 強調自助操作：引導使用者操作系統功能

範例轉換：
❌ 「我們會為您設定」
✅ 「您可在系統設定中調整此功能」

❌ 「請聯繫我們處理」
✅ 「請參考系統操作手冊，或聯繫您的服務業者」'
WHERE type_value = 'system_provider';

-- ========================================
-- 4. 刪除舊的複雜欄位
-- ========================================

ALTER TABLE business_types_config
DROP COLUMN IF EXISTS tone_description,
DROP COLUMN IF EXISTS tone_guidelines,
DROP COLUMN IF EXISTS tone_examples,
DROP COLUMN IF EXISTS tone_summary;

-- ========================================
-- 5. 驗證結果
-- ========================================

\echo ''
\echo '📊 簡化後的業態類型語氣配置：'
SELECT
    type_value,
    display_name,
    CASE
        WHEN tone_prompt IS NOT NULL THEN '✓ 已配置 (' || LENGTH(tone_prompt) || ' 字元)'
        ELSE '✗ 未配置'
    END as tone_status
FROM business_types_config
ORDER BY display_order;

\echo ''
\echo '📝 完整 Prompt 預覽（full_service）：'
SELECT tone_prompt
FROM business_types_config
WHERE type_value = 'full_service';

-- ========================================
-- 6. 記錄 Migration
-- ========================================

INSERT INTO schema_migrations (id, migration_file, description, executed_at)
VALUES (43, '43-simplify-tone-config-to-single-prompt.sql', 'Simplify tone config to single prompt field', NOW())
ON CONFLICT (id) DO NOTHING;

-- ========================================
-- 完成
-- ========================================

\echo ''
\echo '✅ Migration 43: 語氣配置已簡化為單一 Prompt 欄位'
\echo '   - 已刪除複雜的 JSONB 欄位'
\echo '   - 新增單一 tone_prompt TEXT 欄位'
\echo '   - 已轉換三種業態的語氣配置'
\echo ''
\echo '📝 下一步：'
\echo '   1. 修改 llm_answer_optimizer.py 直接使用 tone_prompt'
\echo '   2. 簡化前端編輯介面（在主表單新增 prompt 欄位）'
\echo '   3. 移除語氣配置 Modal 和相關程式碼'
