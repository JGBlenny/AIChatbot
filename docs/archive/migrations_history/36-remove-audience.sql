-- Migration: 36-remove-audience.sql
-- 目的: 移除 audience 欄位和相關配置表，簡化權限控制
-- 決策: 使用 user_role 就足夠，不需要細分對象（租客/房東/管理師）

BEGIN;

-- 1. 記錄遷移前的統計數據
DO $$
DECLARE
    v_total_count INT;
    v_audience_count INT;
    v_record RECORD;
BEGIN
    SELECT COUNT(*) INTO v_total_count FROM knowledge_base;
    SELECT COUNT(*) INTO v_audience_count FROM knowledge_base WHERE audience IS NOT NULL;

    RAISE NOTICE '遷移前統計:';
    RAISE NOTICE '  - 總知識數: %', v_total_count;
    RAISE NOTICE '  - 有 audience 值的知識: %', v_audience_count;

    -- 顯示 audience 分佈
    FOR v_record IN
        SELECT audience, COUNT(*) as cnt
        FROM knowledge_base
        WHERE audience IS NOT NULL
        GROUP BY audience
        ORDER BY cnt DESC
    LOOP
        RAISE NOTICE '    - %: % 筆', v_record.audience, v_record.cnt;
    END LOOP;
END $$;

-- 2. 備份 audience 數據（以防需要回滾）
CREATE TABLE IF NOT EXISTS audience_backup_20250127 AS
SELECT id, question_summary, audience, created_at
FROM knowledge_base
WHERE audience IS NOT NULL;

COMMENT ON TABLE audience_backup_20250127 IS '備份: 移除 audience 欄位前的數據（2025-01-27）';

RAISE NOTICE '✅ 已備份 audience 數據到 audience_backup_20250127';

-- 3. 移除 knowledge_base 的 audience 欄位
ALTER TABLE knowledge_base DROP COLUMN IF EXISTS audience;

RAISE NOTICE '✅ 已移除 knowledge_base.audience 欄位';

-- 4. 刪除 audience_config 表
DROP TABLE IF EXISTS audience_config;

RAISE NOTICE '✅ 已刪除 audience_config 表';

-- 5. 清理任何相關的索引
-- （如果存在 audience 相關索引）
DROP INDEX IF EXISTS idx_knowledge_base_audience;

-- 6. 驗證
DO $$
DECLARE
    v_column_exists BOOLEAN;
    v_table_exists BOOLEAN;
BEGIN
    -- 檢查 audience 欄位是否已刪除
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'knowledge_base' AND column_name = 'audience'
    ) INTO v_column_exists;

    -- 檢查 audience_config 表是否已刪除
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'audience_config'
    ) INTO v_table_exists;

    IF v_column_exists THEN
        RAISE EXCEPTION '❌ 錯誤: audience 欄位仍然存在';
    END IF;

    IF v_table_exists THEN
        RAISE EXCEPTION '❌ 錯誤: audience_config 表仍然存在';
    END IF;

    RAISE NOTICE '✅ 驗證通過: audience 欄位和配置表已成功移除';
END $$;

-- 7. 記錄遷移
COMMENT ON TABLE knowledge_base IS '知識庫表 - 已移除 audience 欄位（2025-01-27），使用 user_role 即可';

COMMIT;

-- 遷移完成通知
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '╔════════════════════════════════════════╗';
    RAISE NOTICE '║  Migration 36 完成                     ║';
    RAISE NOTICE '║  已移除 audience 權限控制              ║';
    RAISE NOTICE '║  所有用戶現在看到相同的知識           ║';
    RAISE NOTICE '╚════════════════════════════════════════╝';
    RAISE NOTICE '';
END $$;
