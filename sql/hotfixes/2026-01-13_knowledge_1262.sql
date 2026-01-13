-- ========================================
-- 緊急修正：知識 ID 1262 意圖分類錯誤
-- 日期：2026-01-13
-- 問題：「你好，我要續約，新的合約甚麼時候會提供?」被分類到錯誤的意圖
-- ========================================

-- 檢查當前分類
SELECT
    kb.id,
    kb.question_summary,
    kim.intent_id,
    i.name as intent_name,
    kim.intent_type
FROM knowledge_base kb
LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
LEFT JOIN intents i ON kim.intent_id = i.id
WHERE kb.id = 1262;

-- 預期看到：intent_id = 105 (一般知識) ❌

-- 修正分類：改為 intent 10 (租期／到期 - 續約相關)
BEGIN;

DELETE FROM knowledge_intent_mapping WHERE knowledge_id = 1262;

INSERT INTO knowledge_intent_mapping (knowledge_id, intent_id, intent_type, confidence)
VALUES (1262, 10, 'primary', 1.0);

COMMIT;

-- 驗證修正結果
SELECT
    kb.id,
    kb.question_summary,
    kim.intent_id,
    i.name as intent_name,
    i.description,
    kim.intent_type
FROM knowledge_base kb
LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
LEFT JOIN intents i ON kim.intent_id = i.id
WHERE kb.id = 1262;

-- 預期看到：intent_id = 10 (租期／到期) ✅
