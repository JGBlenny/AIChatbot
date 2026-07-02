-- =====================================================
-- contract-conversational-facets 任務 3.2：合約 5 子面向系統脈絡（資料，非 schema）
--
-- 面向化疊加（get_system_context 沿父鏈組三層）：base ＋ 母『系統合約』＋ 命中的子面向一列。
-- 本檔新增 5 列子面向脈絡（categories=[<面向>] 各一列，300–600 字）：
--   合約異動（含申請書三段骨架＋團隊擁有者提示）／退租收尾／續約／建約引導／簽署排障。
-- 原則：脈絡只放「制度解讀框架」；這份合約的分流/步驟/進度結論由 formatter 決定性算出
--   （FACE_BUILDERS），LLM 照系統判定作答——脈絡通則不得覆寫 API 現值。
-- 內容依 research.md §二–§六 jgb2 ground truth 撰寫（藍字凍結、取消保留租客資料路徑差異、
--   續約配額真因、免註冊不重簽、72h/30天效期、每日轉歷史排程、申請書契約）。
--
-- 前置：add_contract_facet_categories_v2.sql（5 子分類）。
-- 套用：psql "$DATABASE_URL" -f database/migrations/seed_contract_facet_system_context.sql
-- 套用後清快取（重啟或後台 /conversational-config 任一儲存）。
-- 冪等：以 (category='系統脈絡', question_summary) 識別，已存在不重插。
-- =====================================================

-- 子面向『合約異動』：三出口解讀＋藍字概念＋申請書三段骨架（R2.4/R2.5/R2.6）
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：合約領域-合約異動(子面向)',
    $CTX$## 合約異動（改合約內容）怎麼解讀
系統會判定這份合約的異動出口，照系統判定作答：未發送可直接編輯（也可刪除）；已送簽約邀請要先取消退回「待發送」再改——管理者主動取消會保留租客資料，租客按不同意或邀請逾期退回則會清空；雙方簽署完成後不可直接修改，出口只有複製合約重建新約重簽，或填資料異動申請書由客服後台調整。
- 藍字：簽署後印上 PDF 的參數（租金、電價、租期等）＝藍字，簽後不可改；申請書調的是系統資料庫資料，不重簽則 PDF 與實際收款會不一致，風險由申請人承擔。
- 轉歷史/刪除訴求：到期後系統每日排程自動轉歷史；未簽合約可直接刪除；已簽走申請書。

## 資料異動申請書（收斂產出，照三段骨架填值）
【申請書填寫內容】異動項目類別（會員資料/物件資料/合約資料/帳務資料/其他）；合約 ID（已鎖定那份）；異動前（現況）；異動後（希望改成的內容）。
【範本與提交】向客服索取「資料異動申請書」官方範本，填寫並公司用印後，由申請人會員帳戶之電子信箱寄 service@jgbsmart.com（或紙本郵寄客服部）。
【注意事項】團隊管理者申請時，會員帳號欄應填「團隊擁有者」帳號；金箍棒保留是否受理異動與費用收取之權利；辦理完成後以 email 回覆。$CTX$,
    '系統脈絡', ARRAY['合約異動']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：合約領域-合約異動(子面向)');

-- 子面向『退租收尾』：步驟鏈解讀（R3.1–3.5）
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：合約領域-退租收尾(子面向)',
    $CTX$## 退租收尾怎麼解讀
系統會判定這份合約收尾卡在哪一步與下一步，照系統判定作答。步驟鏈：發起（到期點退或提前解約）→ 租客同意 → 帳單封存 → 轉歷史。
- 點交與點退互不相依：不需先點交才能點退（可略過點交直接點退），可否一律以系統判定清單為準。
- 提前解約：於合約操作中發起、填希望終止日，租客回簽效期預設 30 天；確認後系統把到期日改為終止日，之後同樣走封存與轉歷史。
- 帳單封存：至帳單總表以合約編號搜尋，把剩餘未結帳單批次封存；提前解約多產出的帳單也要封存，否則會持續掛帳。
- 轉歷史：過到期/終止日後，系統每日排程自動轉為歷史合約，無需手動；若逾期多日仍未轉，引導聯繫客服盤查，不要自行猜測原因。$CTX$,
    '系統脈絡', ARRAY['退租收尾']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：合約領域-退租收尾(子面向)');

-- 子面向『續約』：系統續約 vs 重建新約＋重簽規則＋配額真因（R4.1–4.5）
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：合約領域-續約(子面向)',
    $CTX$## 續約怎麼解讀
系統會判定這份合約可否走系統續約（原約需雙簽完成且未過期）與租客重簽方式，照系統判定作答。
- 系統續約 vs 重建新約：系統續約延長租期、產「續約增補」文件；租金、電費等日期以外參數要變更，需重建新約重新簽訂；租客要申請租屋補助時也建議重建新約。
- 重簽方式：租客已註冊 → 需雙方重新簽署（邀請效期 72 小時）；免註冊租客 → 管理者單方確認即生效，不需租客重簽。
- 續約後的呈現：列表僅顯示最新一筆合約；開舊約會自動跳轉最新續約，續約增補文件以分頁掛在合約上（不是合約不見了）。
- 「已達數量上限」：真因是訂閱方案的合約配額——歷史合約與每筆續約都計數，不是物件下架；引導檢視方案配額或聯繫客服，不要沿用「原約到期物件下架」的說法。$CTX$,
    '系統脈絡', ARRAY['續約']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：合約領域-續約(子面向)');

-- 子面向『建約引導』：兩輪分流框架（R5.1–5.6）
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：合約領域-建約引導(子面向)',
    $CTX$## 建約引導怎麼分流
先用至多兩輪確認情境再給路徑，不要一次丟整套教學。
- 建約方式四選一：電子簽新約／紙本合約上傳留存／舊約內容要改（屬合約異動，非建新約）／續約（屬續約面向）。
- 對象型態：個人、法人（公司戶，需統編與代表人）、多人共同承租、商用店面——欄位與註冊方式各有差異，確認後以對應知識作答。
- 條款與附件：預設補充條款位置、字數限制、附件夾帶、滯納金設定等，屬知識收尾範疇，直接以知識作答。
- 簽出去前提醒：藍字參數（租金、電價、租期等）簽署後印上 PDF 不可改，發送簽約邀請前務必設定正確。
- 特殊建檔個案（如包租多戶租補建檔）與系統事故：不做對話化解答，識別後建議聯繫客服處理。$CTX$,
    '系統脈絡', ARRAY['建約引導']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：合約領域-建約引導(子面向)');

-- 子面向『簽署排障』：排查框架＋效期/錯配制度（R6.1–6.5）
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：合約領域-簽署排障(子面向)',
    $CTX$## 簽署問題怎麼排查
系統會判定這份合約的簽署進度（還差誰簽）、邀請發送通道與租客綁定狀態，照系統判定作答。流程：發送邀請 → 租客簽名 → 管理者回簽 → 完成。
- 邀請效期預設 72 小時；逾期系統自動把合約退回「待發送」並清空租客資料——這是「租客資料不見了」的標準原因，需重填租客資料重新發送。
- 信箱錯配：邀請寄到 A 信箱、租客用 B 帳號登入（如以其他信箱註冊或 SSO）會看不到合約；請確認租客實際登入信箱與發送信箱一致，不一致就改用登入信箱重新發送邀請。
- 系統資料判不了的（第幾格沒簽、簡訊未達、驗證碼收不到）：給標準自助排查（確認簡訊未被攔截、重新收驗證碼、換瀏覽器再試），解不了收斂建議聯繫客服，不要自行猜測原因。$CTX$,
    '系統脈絡', ARRAY['簽署排障']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：合約領域-簽署排障(子面向)');

-- 驗證＋長度預算自檢（base＋母＋最長子 ≤ 4500；每輪只疊「命中的那一個」子面向）
DO $$
DECLARE base_len INT; p_len INT; c_max INT; n INT; total INT;
BEGIN
    SELECT COUNT(*) INTO n FROM knowledge_base
    WHERE category='系統脈絡' AND is_active
      AND categories && ARRAY['合約異動','退租收尾','續約','建約引導','簽署排障']::text[];
    SELECT COALESCE(length(answer),0) INTO base_len FROM knowledge_base
    WHERE category='系統脈絡' AND is_active AND target_user IS NULL
      AND (categories IS NULL OR cardinality(categories)=0) ORDER BY id DESC LIMIT 1;
    SELECT COALESCE(length(answer),0) INTO p_len FROM knowledge_base
    WHERE category='系統脈絡' AND is_active AND '系統合約'=ANY(categories) ORDER BY id DESC LIMIT 1;
    SELECT COALESCE(MAX(length(answer)),0) INTO c_max FROM knowledge_base
    WHERE category='系統脈絡' AND is_active
      AND categories && ARRAY['狀態判斷','合約異動','退租收尾','續約','建約引導','簽署排障']::text[];
    total := COALESCE(base_len,0) + COALESCE(p_len,0) + COALESCE(c_max,0);
    RAISE NOTICE '✅ 合約子面向脈絡：% / 5 列；長度預算 base=% ＋ 母=% ＋ 最長子=% ＝ %（上限 4500）',
        n, base_len, p_len, c_max, total;
    IF total > 4500 THEN
        RAISE WARNING '⚠️ 三層疊加 % 超過 4500 上限，請精簡子面向脈絡', total;
    END IF;
END $$;
