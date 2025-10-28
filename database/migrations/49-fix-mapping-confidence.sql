-- ============================================================
-- 修復 knowledge_intent_mapping 的 confidence 值
-- 創建日期: 2025-10-28
-- 目的: 修復 mapping 表中默認為 1.0 的 confidence 值，使其與 knowledge_base.intent_confidence 一致
-- ============================================================

-- 背景說明：
-- 1. knowledge_base.intent_confidence 儲存主意圖的 LLM 信心度評分
-- 2. knowledge_intent_mapping.confidence 原本全部使用默認值 1.0
-- 3. 這導致數據不一致，無法通過 mapping 表查詢低信心度知識
--
-- 修復策略：
-- - 主意圖 mapping：使用 knowledge_base.intent_confidence 的值
-- - 副意圖 mapping：使用主意圖信心度 * 0.85（衰減值）

BEGIN;

-- 記錄修復前的狀態
DO $$
DECLARE
    total_mappings INTEGER;
    primary_with_default INTEGER;
    secondary_with_default INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_mappings FROM knowledge_intent_mapping;
    SELECT COUNT(*) INTO primary_with_default
    FROM knowledge_intent_mapping
    WHERE intent_type = 'primary' AND confidence = 1.0;
    SELECT COUNT(*) INTO secondary_with_default
    FROM knowledge_intent_mapping
    WHERE intent_type = 'secondary' AND confidence = 1.0;

    RAISE NOTICE '=== 修復前統計 ===';
    RAISE NOTICE '總 mapping 數: %', total_mappings;
    RAISE NOTICE '主意圖使用默認值 (1.0): %', primary_with_default;
    RAISE NOTICE '副意圖使用默認值 (1.0): %', secondary_with_default;
END $$;

-- 修復 knowledge_intent_mapping 的 confidence 值
UPDATE knowledge_intent_mapping kim
SET confidence = CASE
    -- 主意圖：使用 knowledge_base 的 intent_confidence
    WHEN kim.intent_type = 'primary' THEN
        COALESCE(kb.intent_confidence, 1.0)
    -- 副意圖：使用主意圖信心度的 85%
    WHEN kim.intent_type = 'secondary' THEN
        COALESCE(kb.intent_confidence, 1.0) * 0.85
    -- 其他情況保持原值（理論上不應該出現）
    ELSE kim.confidence
END,
updated_at = CURRENT_TIMESTAMP
FROM knowledge_base kb
WHERE kim.knowledge_id = kb.id
  AND kim.confidence = 1.0;  -- 只更新默認值的記錄

-- 記錄修復後的狀態
DO $$
DECLARE
    total_updated INTEGER;
    primary_avg NUMERIC;
    secondary_avg NUMERIC;
    primary_min NUMERIC;
    primary_max NUMERIC;
    secondary_min NUMERIC;
    secondary_max NUMERIC;
BEGIN
    -- 獲取更新數量（通過比較 updated_at）
    SELECT COUNT(*) INTO total_updated
    FROM knowledge_intent_mapping
    WHERE updated_at > NOW() - INTERVAL '1 minute';

    -- 獲取主意圖統計
    SELECT
        AVG(confidence),
        MIN(confidence),
        MAX(confidence)
    INTO primary_avg, primary_min, primary_max
    FROM knowledge_intent_mapping
    WHERE intent_type = 'primary';

    -- 獲取副意圖統計
    SELECT
        AVG(confidence),
        MIN(confidence),
        MAX(confidence)
    INTO secondary_avg, secondary_min, secondary_max
    FROM knowledge_intent_mapping
    WHERE intent_type = 'secondary';

    RAISE NOTICE '';
    RAISE NOTICE '=== 修復後統計 ===';
    RAISE NOTICE '已更新記錄數: %', total_updated;
    RAISE NOTICE '';
    RAISE NOTICE '主意圖信心度統計:';
    RAISE NOTICE '  平均值: %', ROUND(primary_avg, 3);
    RAISE NOTICE '  最小值: %', ROUND(primary_min, 3);
    RAISE NOTICE '  最大值: %', ROUND(primary_max, 3);
    RAISE NOTICE '';
    RAISE NOTICE '副意圖信心度統計:';
    RAISE NOTICE '  平均值: %', ROUND(secondary_avg, 3);
    RAISE NOTICE '  最小值: %', ROUND(secondary_min, 3);
    RAISE NOTICE '  最大值: %', ROUND(secondary_max, 3);
END $$;

-- 驗證修復結果：檢查是否還有異常值
DO $$
DECLARE
    remaining_defaults INTEGER;
    mismatch_count INTEGER;
BEGIN
    -- 檢查是否還有默認值 1.0（且應該被修復的）
    SELECT COUNT(*) INTO remaining_defaults
    FROM knowledge_intent_mapping kim
    JOIN knowledge_base kb ON kim.knowledge_id = kb.id
    WHERE kim.confidence = 1.0
      AND kb.intent_confidence IS NOT NULL
      AND kb.intent_confidence != 1.0;

    -- 檢查主意圖的 confidence 是否與 knowledge_base 一致
    SELECT COUNT(*) INTO mismatch_count
    FROM knowledge_intent_mapping kim
    JOIN knowledge_base kb ON kim.knowledge_id = kb.id
    WHERE kim.intent_type = 'primary'
      AND ABS(kim.confidence - COALESCE(kb.intent_confidence, 1.0)) > 0.001;

    RAISE NOTICE '';
    RAISE NOTICE '=== 驗證結果 ===';
    IF remaining_defaults > 0 THEN
        RAISE WARNING '仍有 % 條記錄使用默認值但應該被修復！', remaining_defaults;
    ELSE
        RAISE NOTICE '✓ 所有應該修復的默認值都已更新';
    END IF;

    IF mismatch_count > 0 THEN
        RAISE WARNING '有 % 條主意圖記錄與 knowledge_base 不一致！', mismatch_count;
    ELSE
        RAISE NOTICE '✓ 所有主意圖信心度與 knowledge_base 一致';
    END IF;
END $$;

-- 創建視圖：方便查詢低信心度知識及其意圖
CREATE OR REPLACE VIEW v_knowledge_with_intent_confidence AS
SELECT
    kb.id as knowledge_id,
    kb.question_summary,
    kb.intent_id as primary_intent_id,
    kb.intent_confidence as primary_confidence,
    i.name as primary_intent_name,
    ARRAY_AGG(
        CASE WHEN kim.intent_type = 'secondary'
        THEN json_build_object(
            'intent_id', kim.intent_id,
            'intent_name', si.name,
            'confidence', kim.confidence
        )::text
        ELSE NULL END
    ) FILTER (WHERE kim.intent_type = 'secondary') as secondary_intents
FROM knowledge_base kb
LEFT JOIN intents i ON kb.intent_id = i.id
LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
LEFT JOIN intents si ON kim.intent_id = si.id
GROUP BY kb.id, kb.question_summary, kb.intent_id, kb.intent_confidence, i.name;

COMMENT ON VIEW v_knowledge_with_intent_confidence IS
'知識庫信心度視圖：方便查詢主意圖和副意圖的信心度';

-- 最終摘要
DO $$
DECLARE
    low_confidence_primary INTEGER;
    low_confidence_secondary INTEGER;
BEGIN
    -- 統計低信心度（< 0.7）的主意圖數量
    SELECT COUNT(*) INTO low_confidence_primary
    FROM knowledge_base
    WHERE intent_confidence < 0.7;

    -- 統計低信心度（< 0.7）的副意圖數量
    SELECT COUNT(*) INTO low_confidence_secondary
    FROM knowledge_intent_mapping
    WHERE intent_type = 'secondary' AND confidence < 0.7;

    RAISE NOTICE '';
    RAISE NOTICE '=== 低信心度統計 (< 0.7) ===';
    RAISE NOTICE '主意圖低信心度: % 條知識', low_confidence_primary;
    RAISE NOTICE '副意圖低信心度: % 條 mapping', low_confidence_secondary;
    RAISE NOTICE '';
    RAISE NOTICE '✓ 修復完成！可使用視圖 v_knowledge_with_intent_confidence 查詢信心度資訊';
END $$;

COMMIT;

-- 使用範例查詢
-- 1. 查詢所有低信心度（< 0.7）的主意圖：
-- SELECT * FROM v_knowledge_with_intent_confidence WHERE primary_confidence < 0.7;

-- 2. 查詢特定知識的所有意圖及信心度：
-- SELECT
--     knowledge_id,
--     question_summary,
--     primary_intent_name,
--     primary_confidence,
--     secondary_intents
-- FROM v_knowledge_with_intent_confidence
-- WHERE knowledge_id = 123;

-- 3. 統計各信心度區間的知識數量：
-- SELECT
--     CASE
--         WHEN primary_confidence >= 0.9 THEN '0.9-1.0 (很高)'
--         WHEN primary_confidence >= 0.7 THEN '0.7-0.9 (高)'
--         WHEN primary_confidence >= 0.5 THEN '0.5-0.7 (中)'
--         ELSE '< 0.5 (低)'
--     END as confidence_range,
--     COUNT(*) as count
-- FROM v_knowledge_with_intent_confidence
-- GROUP BY confidence_range
-- ORDER BY confidence_range DESC;
