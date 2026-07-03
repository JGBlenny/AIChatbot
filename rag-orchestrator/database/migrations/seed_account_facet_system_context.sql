-- =====================================================
-- account-conversational-facets 任務 2.2：帳號系統脈絡——母薄層＋4 子面向（資料，非 schema）
-- 內容依 research.md 主題 1–4 jgb2 ground truth 撰寫（驗證碼 TTL/重發規則、LINE 登入、
-- 自助 vs 後台判定表、藍字兩但書、團隊可見範圍三層）。機制數字寫死、LLM 不得自創。
-- 母層自律（R1.3）：僅名詞對照＋代問模式一句，外部/內部類機制細節一律下沉子層。
-- 前置：add_account_facet_categories.sql。套用後清快取。
-- 冪等：以 (category='系統脈絡', question_summary) 識別，已存在不重插。
-- =====================================================

-- 母『帳號中心』：名詞對照（薄層，所有帳號面向共用）
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：帳號領域-帳號中心(母共用)',
    $CTX$## 帳號名詞對照
一人一個主帳號；手機與信箱和帳號是唯一對應（已被使用就不能再註冊）。同一帳號可同時有租客、房東、團隊成員多重身分，畫面左上角的身分選單決定當下看到的資料範圍。團隊＝法人房東，成員的資料範圍由團隊內指派決定。帳號問題常由管理者代租客詢問——回答時給管理者可執行的動作，並附可直接轉給租客的說法。$CTX$,
    '系統脈絡', ARRAY['帳號中心']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：帳號領域-帳號中心(母共用)');

-- 子『註冊驗證排障』（外部類）
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：帳號領域-註冊驗證排障(子面向)',
    $CTX$## 註冊與驗證怎麼排障
註冊主路徑是 Email（輸入信箱→收驗證碼→設密碼→選身分），手機簡訊驗證是最後的綁定步驟、可先跳過之後再補綁。
- 驗證碼規則：效期 300 秒（5 分鐘）、輸錯三次即失效需重新取得；每次重新取得都會產生新碼、舊碼立刻失效；120 秒冷卻內重按不會產生新碼也不會發送。簡訊與信件開頭有三個英文字母的識別碼——請對照畫面顯示的識別碼，只輸入「識別碼對得上的那一封」裡的碼。
- 收不到簡訊：先核對手機號碼與垃圾匣；仍收不到就改走 Email 註冊（給租客註冊頁連結）。
- 顯示「已註冊」：代表該信箱或手機已有帳號，改走登入或換綁處理，不要另註冊新帳號。
- 管理者也可重發合約邀請：租客用邀請信連結完成免註冊驗證，連結效期 72 小時。
- 註冊頁全面錯誤、多位業者同時回報、或出現「金鑰無效」字樣：屬系統面事故，直接聯繫客服，不做個案排查。$CTX$,
    '系統脈絡', ARRAY['註冊驗證排障']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：帳號領域-註冊驗證排障(子面向)');

-- 子『登入排障』（外部類）
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：帳號領域-登入排障(子面向)',
    $CTX$## 登入問題怎麼判
提供合約編號或物件名稱時，系統會查該合約租客的帳號現值（是否已註冊、登入信箱是否與邀請一致），照系統判定作答。
- LINE 快速登入跳到註冊畫面：用帳號密碼註冊的帳號沒有 LINE 綁定、也無法事後補綁——請改用帳號密碼登入，這是目前的設計不是故障。
- 信箱要用「當初註冊時的確切寫法」輸入：寫法不同可能登進另一個同名帳號，登入成功卻看不到自己的合約、帳單或電表，多半就是登錯帳號。
- 忘記密碼：登入頁可自助重設，Email 或手機簡訊驗證擇一。忘記當初用哪個信箱：登入頁「忘記帳號」以手機驗證後會顯示打星號的信箱提示；沒綁手機才需要找客服。
- 登入成功但畫面空白或少資料：先確認左上角身分選單已切到正確身分（租客資料要在租客身分下看）；仍異常再懷疑登錯帳號。$CTX$,
    '系統脈絡', ARRAY['登入排障']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：帳號領域-登入排障(子面向)');

-- 子『帳號綁定異動』（內部類）
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：帳號領域-帳號綁定異動(子面向)',
    $CTX$## 帳號資料異動怎麼分流
先分「可自助」與「需申請」，不代辦、不承諾處理時效。
- 可自助：姓名、稱謂、聯絡電話（非主手機）、地址、頭像——帳號設定的基本資訊頁自行修改。注意：合約雙方完成簽署後姓名會被鎖定，之後要改需走申請。
- 需申請（JGB 後台作業）：主手機與 Email 的換綁、解綁、兩個帳號合併。出口是「資料異動申請書」：載明帳號識別（信箱或手機）、修改前後值、合約 ID，經公司用印後寄 service@jgbsmart.com，由客服人工處理。
- 「此手機/信箱已註冊」：綁定是唯一對應，被占用就只能對原帳號做解綁申請，不要建議另開新帳號繞過。
- 合約上的藍字欄位（由帳號資料帶入）有兩個但書：尚未完成簽署的合約，簽署時會帶入當下帳號資料（改名即生效）；已完成簽署的合約是定案快照、不會跟著帳號連動，要改須一併申請。$CTX$,
    '系統脈絡', ARRAY['帳號綁定異動']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：帳號領域-帳號綁定異動(子面向)');

-- 子『團隊成員權限』（內部類）
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：帳號領域-團隊成員權限(子面向)',
    $CTX$## 成員權限怎麼判
- 加入成員的前提：對方要先自行註冊好帳號，才能以信箱或手機被搜尋加入團隊。
- 成員「看不到社區/物件、不能新增」最常見原因：加入後尚未被指派角色——請管理者到成員列表對該成員「變更角色」，指派後權限即生效。
- 可見範圍分三層：多數角色可看全團隊物件；部分角色僅能看「自己被指派為經理人」的物件；再細可逐筆指派。成員看得到但不能改，代表其角色只有查看沒有編輯權限。
- 新增社區、新增合約各需對應的編輯權限，角色沒開就會做不了；系統內建十種範本角色（擁有者、最高管理者、店長、會計、一般業務等），也可自訂。
- 一個帳號可加入多個團隊：左上角身分選單切換，系統會記住上次使用的身分作為下次登入落點。$CTX$,
    '系統脈絡', ARRAY['團隊成員權限']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：帳號領域-團隊成員權限(子面向)');

DO $$
DECLARE n INT;
BEGIN
    SELECT COUNT(*) INTO n FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary LIKE '系統脈絡：帳號領域-%' AND is_active;
    RAISE NOTICE '✅ 帳號領域系統脈絡：% / 5（母1＋子4）', n;
END $$;
