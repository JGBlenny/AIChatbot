-- Migration: 建立資料一致性約束與觸發器
-- 日期: 2026-03-21
-- 任務: 1.8 建立資料一致性約束與觸發器
-- 用途: 語義去重、同步完整性檢查、審核超時提醒重置

-- ============================================
-- 1. 語義去重函數與觸發器
-- ============================================

CREATE OR REPLACE FUNCTION check_semantic_duplication()
RETURNS TRIGGER AS $$
DECLARE
    existing_count INT;
    max_similarity FLOAT;
BEGIN
    -- 只在有 embedding 時才檢查
    IF NEW.embedding IS NULL THEN
        RETURN NEW;
    END IF;

    -- 檢查是否有相似度 > 0.95 的知識存在於 knowledge_base
    SELECT COUNT(*), MAX(1 - (embedding <=> NEW.embedding))
    INTO existing_count, max_similarity
    FROM knowledge_base
    WHERE NEW.embedding IS NOT NULL
      AND 1 - (embedding <=> NEW.embedding) > 0.95;

    IF existing_count > 0 THEN
        RAISE WARNING '語義去重：發現相似度 %.2f 的知識已存在於 knowledge_base，建議合併', max_similarity;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_semantic_duplication_check
BEFORE INSERT ON loop_generated_knowledge
FOR EACH ROW
EXECUTE FUNCTION check_semantic_duplication();

COMMENT ON FUNCTION check_semantic_duplication() IS '語義去重：檢查 loop_generated_knowledge 插入時是否與 knowledge_base 中的知識相似度 > 0.95';

-- ============================================
-- 2. 同步完整性檢查函數與觸發器
-- ============================================

CREATE OR REPLACE FUNCTION validate_sync_completeness()
RETURNS TRIGGER AS $$
BEGIN
    -- 當 status 變更為 'synced' 時，驗證必要欄位
    IF NEW.status = 'synced' THEN
        IF NEW.question IS NULL OR NEW.answer IS NULL OR NEW.embedding IS NULL THEN
            RAISE EXCEPTION '同步失敗：question, answer, embedding 欄位不可為空';
        END IF;

        IF NEW.synced_to_kb = false THEN
            RAISE EXCEPTION '同步失敗：synced_to_kb 必須為 true';
        END IF;

        IF NEW.kb_id IS NULL THEN
            RAISE EXCEPTION '同步失敗：kb_id 必須填入';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_sync_completeness_check
BEFORE UPDATE ON loop_generated_knowledge
FOR EACH ROW
EXECUTE FUNCTION validate_sync_completeness();

COMMENT ON FUNCTION validate_sync_completeness() IS '同步完整性檢查：確保 loop_generated_knowledge 標記為 synced 時所有必要欄位都已填入';

-- ============================================
-- 3. 審核超時提醒重置函數與觸發器
-- ============================================

CREATE OR REPLACE FUNCTION reset_review_timeout_reminder()
RETURNS TRIGGER AS $$
BEGIN
    -- 當狀態從 'reviewing' 變更為其他狀態時，重置提醒標記
    IF OLD.status = 'reviewing' AND NEW.status != 'reviewing' THEN
        NEW.review_timeout_reminder_sent := false;
        NEW.review_timeout_reminder_sent_at := NULL;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_reset_review_timeout_reminder
BEFORE UPDATE ON knowledge_completion_loops
FOR EACH ROW
EXECUTE FUNCTION reset_review_timeout_reminder();

COMMENT ON FUNCTION reset_review_timeout_reminder() IS '審核超時提醒重置：當狀態從 reviewing 變更時，重置提醒標記以便下次進入 reviewing 時可重新發送';
