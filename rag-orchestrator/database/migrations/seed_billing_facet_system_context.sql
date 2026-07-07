-- =====================================================
-- billing-conversational-facets 任務 4.2：帳務系統脈絡——母共用＋5 子面向（資料，非 schema）
-- 內容依 research.md §一–§四 jgb2 ground truth 撰寫（狀態機/超商撥付時程/可見三條件/
-- 發票三軌/滯納金兩機制/期限與發送規則）。脈絡只放制度解讀框架；該筆帳單的結論由
-- BILL_FACE_BUILDERS 決定性算出——脈絡通則不得覆寫 API 現值；金額只引用存值。
-- 前置：add_billing_facet_categories.sql。套用後清快取。
-- 冪等：以 (category='系統脈絡', question_summary) 識別，已存在不重插。
-- =====================================================

-- 母『系統帳務』：帳單狀態機＋名詞（所有帳務面向共用）
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：帳務領域-系統帳務(母共用)',
    $CTX$## 帳單狀態（金流階段參考）
| 值 | 狀態 | 白話 |
|--|--|--|
| 1 | 待發送 | 帳單已產生，還沒發給租客（租客看不到） |
| 32 | 排定發送 | 已排入自動發送，尚未送出（租客看不到） |
| 2 | 待繳費 | 已發送，等租客繳費（租客看得到） |
| 8 | 待對帳 | 租客已繳費、款項尚未入帳 |
| 16 | 已到帳 | 款項已入帳，完成 |
| 64 | 已失效 | 帳單失效（限儲值型） |
用詞：待對帳＝「錢繳了但還沒進來」；已到帳＝完成。
帳單由每日排程自動產生（最早提前一個月）；合約起始日在過去時，簽約完成當下會一次補產到當期。
金額（total/final_total）為系統存值——回答金額一律引用存值，不自行計算。$CTX$,
    '系統脈絡', ARRAY['系統帳務']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：帳務領域-系統帳務(母共用)');

-- 子『繳費金流排障』
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：帳務領域-繳費金流排障(子面向)',
    $CTX$## 繳費金流怎麼解讀
系統會判定這筆帳單的金流階段與該做什麼，照系統判定作答。
- 通道差異是關鍵：ATM/銀行轉帳類通常金流通知一到就入帳；**超商代收是唯一天然停在「待對帳」的通道**——超商撥付入帳為每月 5、15、25 日（遇假日順延），停在待對帳屬正常時程，等撥付日即入帳。
- 查無繳費紀錄（已發送但系統沒收到繳費）：請租客核對繳款帳號、確認轉帳金額未超過單筆上限、保留交易明細；必要時把帳單收回重發——重發會產生新的繳費資訊。
- 金額與通知不符時系統會標記異常並停在待對帳等人工處理——這種情況直接聯繫客服，附上帳單編號與繳費時間。
- 非超商通道多日未入帳也屬異常，導客服核查，不要猜測原因。$CTX$,
    '系統脈絡', ARRAY['繳費金流排障']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：帳務領域-繳費金流排障(子面向)');

-- 子『帳單異常』
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：帳務領域-帳單異常(子面向)',
    $CTX$## 帳單異常怎麼解讀
系統會列出這筆帳單的存值組成，照存值作答、不重算。
- 金額「不對」常見真因：不足月比例計費（帳單期間非整月時按實際天數/名目天數比例）、首期含押金、生活費用品項、合約折扣——逐項看系統明細即可對帳。
- 帳單「沒產生」：產生時點最早提前一個月，未到時點屬正常；合約起始日在過去的，簽約完成當下就會補產到當期；再查不到才是異常。
- 租客「看不到帳單」三條件缺一不可：租客是該帳單付款方、帳單已發送（待發送/排定發送都看不到）、帳單未封存。都符合仍看不到 → 請租客確認以租客身分登入（左上角角色切換）並到帳務管理頁查看。
- 封存/點退帳單屬合約退租收尾範疇——涉及封存處理時轉由合約領域接手，不在此重複解答。$CTX$,
    '系統脈絡', ARRAY['帳單異常']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：帳務領域-帳單異常(子面向)');

-- 子『發票』
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：帳務領域-發票(子面向)',
    $CTX$## 發票怎麼解讀
系統會判定這筆帳單的發票狀態，照系統判定作答，不虛構號碼與日期。
- 開立時點三軌：預設「到帳後自動開立」；團隊可設定「提前開立」模式（發送日/到期日前後）；也可由後台手動開立或補開。所以「發票什麼時候開」依團隊模式而異，以該帳單實際狀態為準。
- 異常常見原因：加值中心字軌不足、發票設定缺失（金鑰、買受人資料）、資料錯誤、API 錯誤——後台發票稽核可看到失敗原因並補開。
- 補開規則：帳單已有有效發票不可重複補開；款項尚未付款不可開立；重開需原發票先作廢。
- 差額發票（包租業月結差額）是獨立子系統：差額群組的帳單開一般發票時租金品項會被排除、租金由每月群組差額發票開立——群組相關操作請聯繫客服，不自行處理。$CTX$,
    '系統脈絡', ARRAY['發票']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：帳務領域-發票(子面向)');

-- 子『滯納金』
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：帳務領域-滯納金(子面向)',
    $CTX$## 滯納金怎麼解讀
系統有兩種滯納金機制，依團隊採用的機制而定，照該筆合約設定與實際產生的滯納金帳單作答。
- 機制一「延遲金」（付款後結算）：租客付款當下若逾期，按「租金 ×（實際付款日 − 繳費期限 − 緩衝天數）× 費率」結算，開立獨立延遲金帳單（到期日＝產生日），帳單上附完整計算備註。
- 機制二「排程開單」（對逾期未付款帳單）：依團隊設定為階梯費率（逾期越久費率越高、每帳單最多兩筆）或固定金額（逾期滿一定天數收一次）。
- 共同規則：每張逾期帳單各自結算不累加；滯納金帳單本身逾期不會再產生滯納金。
- 前提是合約的滯納金設定已啟用（未啟用不會自動產生）；金額一律引用系統結算存值，不重算。
- 個案減免或調整不在自助範圍，請聯繫客服處理。$CTX$,
    '系統脈絡', ARRAY['滯納金']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：帳務領域-滯納金(子面向)');

-- 子『帳單設定引導』
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：帳務領域-帳單設定引導(子面向)',
    $CTX$## 帳單設定怎麼分流
先用至多兩輪確認要設定什麼再給路徑，不要一次丟整套教學。
- 設定對象四類：收款帳戶（銀行/虛擬帳號）、繳費週期（月/季等，合約層設定）、繳費期限與發送日、繳費方式（線上金流/線下）。
- 期限規則：合約設定「每期第 N 日前支付」；距產生日不足 5 天時系統自動延後為 5 天，避免租客來不及繳。
- 發送規則：團隊可設定「到期前 N 天」自動排定發送；也可手動逐筆發送——發送後租客才看得到帳單。
- 新收款帳戶開通驗證：官方流程是建一份租金 1 元的測試合約、發送一元帳單、實際完成繳納確認入帳，再啟用正式收款。
- 涉及特定帳單或合約的現況問題（「這筆為什麼…」）不在本面向，交由對應診斷面向接手。$CTX$,
    '系統脈絡', ARRAY['帳單設定引導']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：帳務領域-帳單設定引導(子面向)');

-- 驗證＋長度預算自檢（base＋母＋最長子 ≤ 4500）
DO $$
DECLARE base_len INT; p_len INT; c_max INT; n INT; total INT;
BEGIN
    SELECT COUNT(*) INTO n FROM knowledge_base
    WHERE category='系統脈絡' AND is_active
      AND categories && ARRAY['繳費金流排障','帳單異常','發票','滯納金','帳單設定引導']::text[];
    SELECT COALESCE(length(answer),0) INTO base_len FROM knowledge_base
    WHERE category='系統脈絡' AND is_active AND target_user IS NULL
      AND (categories IS NULL OR cardinality(categories)=0) ORDER BY id DESC LIMIT 1;
    SELECT COALESCE(length(answer),0) INTO p_len FROM knowledge_base
    WHERE category='系統脈絡' AND is_active AND '系統帳務'=ANY(categories) ORDER BY id DESC LIMIT 1;
    SELECT COALESCE(MAX(length(answer)),0) INTO c_max FROM knowledge_base
    WHERE category='系統脈絡' AND is_active
      AND categories && ARRAY['繳費金流排障','帳單異常','發票','滯納金','帳單設定引導']::text[];
    total := COALESCE(base_len,0) + COALESCE(p_len,0) + COALESCE(c_max,0);
    RAISE NOTICE '✅ 帳務子面向脈絡：% / 5 列；長度預算 base=% ＋ 母=% ＋ 最長子=% ＝ %（上限 4500）',
        n, base_len, p_len, c_max, total;
    IF total > 4500 THEN
        RAISE WARNING '⚠️ 三層疊加 % 超過 4500 上限，請精簡', total;
    END IF;
END $$;
