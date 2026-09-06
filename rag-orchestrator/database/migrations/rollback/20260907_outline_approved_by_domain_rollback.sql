-- =====================================================
-- 回滾：20260907_outline_approved_by_domain.sql
--   （knowledge-outline-and-intent-architecture 任務 3.1）
--
-- 只拆約束，⛔ 不動任何列的值——`outline_approved_by` 的既有值（含 D1 改寫過的
-- `pool-marked-<date>`／匯入寫進的 `reviewed:<who>`）一律保留。約束是「以後不准
-- 寫進值域外的值」，拆掉它不需要、也不應該把已寫入的值改回去。
--
-- ⚠️ 拆掉之後值域恢復成任意 text ⇒ 不變量 32 的 DB 子檢查失去 DB 層保護，
--    只剩程式層謂詞（`content_reviewed_predicate`）擋——謂詞仍是正向白名單，
--    值域外的值依然不可見，故拆約束**不會**讓未審列變可見。
-- =====================================================

ALTER TABLE knowledge_base
    DROP CONSTRAINT IF EXISTS chk_outline_approved_by_domain;

DO $$
DECLARE n INTEGER;
BEGIN
    SELECT COUNT(*) INTO n
      FROM pg_constraint
     WHERE conname = 'chk_outline_approved_by_domain'
       AND conrelid = 'knowledge_base'::regclass;
    IF n <> 0 THEN
        RAISE EXCEPTION 'chk_outline_approved_by_domain 仍存在（% 筆）——回滾未生效，大聲失敗', n;
    END IF;
    RAISE NOTICE '✅ chk_outline_approved_by_domain 已移除';
END $$;
