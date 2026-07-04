-- =====================================================
-- estate-conversational-facets 任務 2.2：物件系統脈絡——母薄層＋2 子面向（資料，非 schema）
-- 內容依 research.md 定案 9 項 jgb2 ground truth 撰寫（兩軸狀態機、刪除三擋、
-- 建約前提、批次 queue 與通知中心、地址雙層、店舖 /p/）。官方矛盾文章已作廢，
-- 本檔口徑以真碼為準；機制數字寫死、LLM 不得自創。
-- 母層自律：兩軸一句話版＋邊界，操作細節一律下沉子層。
-- 前置：add_estate_facet_categories.sql。套用後清快取。
-- 冪等：以 (category='系統脈絡', question_summary) 識別，已存在不重插。
-- =====================================================

-- 母『物件管理』：兩軸模型＋邊界（薄層）
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：物件領域-物件管理(母共用)',
    $CTX$## 物件領域怎麼看
物件狀態有兩條獨立軸：合約軸（未刊登建立／刊登中／洽談中＝已綁合約未簽署／租約中）與刊登軸（是否對外刊登）——租約中的物件也可以同時在刊登中，兩軸不要混為一談。物件的合約、點交、押金操作屬合約領域；物件綁電表屬智慧設備領域；成員與經理人權限屬帳號領域。$CTX$,
    '系統脈絡', ARRAY['物件管理']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：物件領域-物件管理(母共用)');

-- 子『物件操作引導』
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：物件領域-物件操作引導(子面向)',
    $CTX$## 物件操作怎麼引導
- 編輯與刊登是兩件事：「編輯物件」改內容不上架、「刊登物件」才上架。任何狀態的物件都可以編輯——物件修改**不影響既有合約**（合約簽訂時已快照）；編輯後務必按「儲存」再離開頁面，切換頁面不會自動儲存。
- 刪除物件有三擋：刊登中不可刪（先取消刊登）、**有有效合約不可刪**（需先解除合約——所以「刪除後歷史合約會不會消失」不會發生，有約根本刪不了）、有 IoT 設備綁定不可刪。
- 批次上傳：用範本 Excel（必填欄未填會逐列報「為必填欄位」）、檔案上限 **10MB**、確認後系統排隊處理——結果（成功/失敗筆數）會發到**通知中心**，不是當場顯示；若停在「處理中」超過一小時屬系統端異常，請聯繫客服，**不要重傳**以免重複建立。物件數量受訂閱方案額度限制，超額會被擋。
- 對外顯示地址：業者後台**永遠顯示完整地址**，「對外顯示地址」只作用在對外廣告頁——要確認效果請開對外頁看，不是看後台。
- 招租店舖（房東對外首頁）：公開展示團隊所有刊登中物件，網址為 /p/ 開頭（可設自訂帳號），入口在後台側邊選單。$CTX$,
    '系統脈絡', ARRAY['物件操作引導']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：物件領域-物件操作引導(子面向)');

-- 子『物件現況診斷』
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：物件領域-物件現況診斷(子面向)',
    $CTX$## 物件現況怎麼判
系統會查這個物件在對外刊登清單中的現值，照系統判定作答，不臆測。
- 狀態轉譯：刊登中／洽談中（已綁合約、尚未完成簽署——此時物件仍可編輯、但不可刪除）／租約中——查得到就代表物件目前對外刊登中（租約中也可能同時刊登中，兩軸獨立）。
- 能不能建約：前提是物件為「刊登中」且必填欄位齊備——系統會列出還缺哪些欄位，補齊即可；非刊登中要先刊登。
- 查不到的口徑：對外刊登清單找不到時，先請對方確認物件名稱是否正確；名稱無誤代表該物件目前非刊登中（尚未刊登或已下架），**不得斷言已刪除**——實際狀態請到後台物件總表確認。
- 物件修改不影響既有合約（快照原則）；地址一律只講對外顯示版本。$CTX$,
    '系統脈絡', ARRAY['物件現況診斷']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：物件領域-物件現況診斷(子面向)');

DO $$
DECLARE n INT;
BEGIN
    SELECT COUNT(*) INTO n FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary LIKE '系統脈絡：物件領域-%' AND is_active;
    RAISE NOTICE '✅ 物件領域系統脈絡：% / 3（母1＋子2）', n;
END $$;
