-- DSP-026：取消大綱重複列標記（業主 2026-09-05 同意；主 session 由 7 列收窄為 2 列）
-- 只取消答案逐字重複對中的講法列；主題頁 3584／3610 保留；5378／5379／5380 有獨有內容，⛔ 不得取消。
-- 執行前核對：SELECT (SELECT answer FROM knowledge_base WHERE id=3584)=(SELECT answer FROM knowledge_base WHERE id=5377),
--                     (SELECT answer FROM knowledge_base WHERE id=3610)=(SELECT answer FROM knowledge_base WHERE id=5376);
UPDATE knowledge_base SET outline_approved_by=NULL, outline_approved_at=NULL
 WHERE id IN (5376, 5377) AND outline_approved_by='owner-20260905';
-- 預期：UPDATE 2；SELECT count(*) FROM knowledge_base WHERE outline_approved_by IS NOT NULL ⇒ 29
