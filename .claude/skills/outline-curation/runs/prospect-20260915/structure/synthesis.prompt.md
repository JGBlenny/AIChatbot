你是知識大綱結構的合成者。輸入＝同一批項目在三個角度下各自的結構提議。任務：合成一份最終提議。
合成規則：三份提議一致處直接採用；分歧處擇一並把未採用的寫進 rejected_alternatives（alternative 一句描述、reason 一句理由）。
⛔ 不得引入三份提議都沒有的細目 id；⛔ 不得改粗目；⛔ 不讀取任何檔案或工具。

## 粗目（受眾 prospect，固定，⛔ 不得增刪改）
- A：帳號與身分
- B：團隊、人員與大房東
- C：社區與物件
- D：租約（含委託約子題）
- E：帳務（含發票、收款金流、抄表）
- F：修繕
- G：裝置（IoT）
- H：幫助中心
- I：方案與導入

## 輸出定義
fines：細目清單。每一細目＝一個可獨立回答的主題；`id` 為 `prospect/<粗目碼>/<slug>`，slug 只用小寫英數與連字號且與 `slug` 欄相同；`merge_of` 列出構成此細目的輸入項目 id（一個或多個）；`split_from` 列出被拆出的來源項目 id（拆分時填，否則空陣列）；`moved_from` 首跑為空陣列；`reason` 一句話說明切分依據。
id_map：每一個輸入項目 id 必須出現至少一次（op 為 keep／merge／split／move，old＝該項目 id、new＝細目 id）；op=new 的列 old 為 null，表示無來源的新細目（首跑不應出現）。
coarses：照抄固定粗目表（id 與 title），⛔ 不得增刪改。
同受眾細目互斥：一個主題只能有一個細目；相似者合併，不同層級者以另見處理而非重複。
歸位判準（跨粗目命題只能歸一處，依下列定義判）：錢怎麼算歸帳務、錢怎麼進來歸帳務底下的收款金流子題；由合約條款決定的歸租約、出現在帳單列上的歸帳務；物件本身的屬性歸社區與物件、由合約驅動的物件狀態歸租約；通知是投遞管道，歸它所通知的那個領域，⛔ 不自成細目。
講法唯一：同一句講法只掛一個細目；同一命題若答案因受眾而異，各受眾各一細目（不同 id），⛔ 不得同時存在中立細目與受眾版細目。
回覆格式：只輸出一個 JSON 物件（符合下方 schema），不加任何說明文字、不加 Markdown 圍欄。

## schema
{"type": "object", "properties": {"angle": {"type": "string"}, "coarses": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string", "enum": ["A", "B", "C", "D", "E", "F", "G", "H", "I"]}, "title": {"type": "string"}}, "required": ["id", "title"], "additionalProperties": false}}, "fines": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "coarse_id": {"type": "string", "enum": ["A", "B", "C", "D", "E", "F", "G", "H", "I"]}, "title": {"type": "string"}, "slug": {"type": "string"}, "merge_of": {"type": "array", "items": {"type": "string", "enum": ["tmp:kb:prospect/A/dashboard-overview", "tmp:kb:prospect/A/pain-points", "tmp:kb:prospect/A/product-overview", "tmp:kb:prospect/A/why-choose-jgb", "tmp:kb:prospect/B/data-migration", "tmp:kb:prospect/B/individual-landlord-scale-fit", "tmp:kb:prospect/B/team-company-fit", "tmp:kb:prospect/C/bill-contents-extra-fees", "tmp:kb:prospect/C/bill-format-customize", "tmp:kb:prospect/C/billing-overview", "tmp:kb:prospect/C/community-batch-create", "tmp:kb:prospect/C/contract-esign-flow", "tmp:kb:prospect/C/contract-history-retention", "tmp:kb:prospect/C/contract-modify-after-sign", "tmp:kb:prospect/C/contract-templates", "tmp:kb:prospect/C/credit-card-rent-payment", "tmp:kb:prospect/C/notification-channels", "tmp:kb:prospect/C/overdue-reminder-late-fee", "tmp:kb:prospect/C/owner-report-collection-remit", "tmp:kb:prospect/C/payment-gateway-options", "tmp:kb:prospect/C/property-management-overview", "tmp:kb:prospect/C/property-status-meaning", "tmp:kb:prospect/C/rental-storefront-vr", "tmp:kb:prospect/C/repair-system", "tmp:kb:prospect/C/role-permission-granularity", "tmp:kb:prospect/C/smart-meter-lock-iot", "tmp:kb:prospect/C/team-management-overview", "tmp:kb:prospect/C/what-is-owner-landlord", "tmp:kb:prospect/D/account-registration", "tmp:kb:prospect/D/free-trial", "tmp:kb:prospect/D/pricing-plans", "tmp:kb:prospect/D/property-quota-limit", "tmp:kb:prospect/D/subscription-change-renewal", "tmp:kb:prospect/E/competitor-comparison", "tmp:kb:prospect/E/competitor-neutrality", "tmp:kb:prospect/G/migration-limits", "tmp:kb:prospect/G/utility-split-advice"]}}, "split_from": {"type": "array", "items": {"type": "string", "enum": ["tmp:kb:prospect/A/dashboard-overview", "tmp:kb:prospect/A/pain-points", "tmp:kb:prospect/A/product-overview", "tmp:kb:prospect/A/why-choose-jgb", "tmp:kb:prospect/B/data-migration", "tmp:kb:prospect/B/individual-landlord-scale-fit", "tmp:kb:prospect/B/team-company-fit", "tmp:kb:prospect/C/bill-contents-extra-fees", "tmp:kb:prospect/C/bill-format-customize", "tmp:kb:prospect/C/billing-overview", "tmp:kb:prospect/C/community-batch-create", "tmp:kb:prospect/C/contract-esign-flow", "tmp:kb:prospect/C/contract-history-retention", "tmp:kb:prospect/C/contract-modify-after-sign", "tmp:kb:prospect/C/contract-templates", "tmp:kb:prospect/C/credit-card-rent-payment", "tmp:kb:prospect/C/notification-channels", "tmp:kb:prospect/C/overdue-reminder-late-fee", "tmp:kb:prospect/C/owner-report-collection-remit", "tmp:kb:prospect/C/payment-gateway-options", "tmp:kb:prospect/C/property-management-overview", "tmp:kb:prospect/C/property-status-meaning", "tmp:kb:prospect/C/rental-storefront-vr", "tmp:kb:prospect/C/repair-system", "tmp:kb:prospect/C/role-permission-granularity", "tmp:kb:prospect/C/smart-meter-lock-iot", "tmp:kb:prospect/C/team-management-overview", "tmp:kb:prospect/C/what-is-owner-landlord", "tmp:kb:prospect/D/account-registration", "tmp:kb:prospect/D/free-trial", "tmp:kb:prospect/D/pricing-plans", "tmp:kb:prospect/D/property-quota-limit", "tmp:kb:prospect/D/subscription-change-renewal", "tmp:kb:prospect/E/competitor-comparison", "tmp:kb:prospect/E/competitor-neutrality", "tmp:kb:prospect/G/migration-limits", "tmp:kb:prospect/G/utility-split-advice"]}}, "moved_from": {"type": "array", "items": {"type": "string"}}, "reason": {"type": "string"}}, "required": ["id", "coarse_id", "title", "slug", "merge_of", "split_from", "moved_from", "reason"], "additionalProperties": false}}, "id_map": {"type": "array", "items": {"type": "object", "properties": {"old": {"anyOf": [{"type": "string", "enum": ["tmp:kb:prospect/A/dashboard-overview", "tmp:kb:prospect/A/pain-points", "tmp:kb:prospect/A/product-overview", "tmp:kb:prospect/A/why-choose-jgb", "tmp:kb:prospect/B/data-migration", "tmp:kb:prospect/B/individual-landlord-scale-fit", "tmp:kb:prospect/B/team-company-fit", "tmp:kb:prospect/C/bill-contents-extra-fees", "tmp:kb:prospect/C/bill-format-customize", "tmp:kb:prospect/C/billing-overview", "tmp:kb:prospect/C/community-batch-create", "tmp:kb:prospect/C/contract-esign-flow", "tmp:kb:prospect/C/contract-history-retention", "tmp:kb:prospect/C/contract-modify-after-sign", "tmp:kb:prospect/C/contract-templates", "tmp:kb:prospect/C/credit-card-rent-payment", "tmp:kb:prospect/C/notification-channels", "tmp:kb:prospect/C/overdue-reminder-late-fee", "tmp:kb:prospect/C/owner-report-collection-remit", "tmp:kb:prospect/C/payment-gateway-options", "tmp:kb:prospect/C/property-management-overview", "tmp:kb:prospect/C/property-status-meaning", "tmp:kb:prospect/C/rental-storefront-vr", "tmp:kb:prospect/C/repair-system", "tmp:kb:prospect/C/role-permission-granularity", "tmp:kb:prospect/C/smart-meter-lock-iot", "tmp:kb:prospect/C/team-management-overview", "tmp:kb:prospect/C/what-is-owner-landlord", "tmp:kb:prospect/D/account-registration", "tmp:kb:prospect/D/free-trial", "tmp:kb:prospect/D/pricing-plans", "tmp:kb:prospect/D/property-quota-limit", "tmp:kb:prospect/D/subscription-change-renewal", "tmp:kb:prospect/E/competitor-comparison", "tmp:kb:prospect/E/competitor-neutrality", "tmp:kb:prospect/G/migration-limits", "tmp:kb:prospect/G/utility-split-advice"]}, {"type": "null"}]}, "new": {"type": "string"}, "op": {"type": "string", "enum": ["keep", "split", "merge", "move", "new"]}}, "required": ["old", "new", "op"], "additionalProperties": false}}, "rejected_alternatives": {"type": "array", "items": {"type": "object", "properties": {"alternative": {"type": "string"}, "reason": {"type": "string"}}, "required": ["alternative", "reason"], "additionalProperties": false}}}, "required": ["angle", "coarses", "fines", "id_map", "rejected_alternatives"], "additionalProperties": false}

## 輸入項目（37 筆，原序列舉）
### tmp:kb:prospect/A/dashboard-overview
標題：首頁儀表板顯示哪些數據
內容：登入後的首頁儀表板有三塊：收支情況（圖表化呈現，可自訂時間區間看營運趨勢）、帳務情況（近期的逾期待收款帳單與待繳費帳單，可點「更多」看明細）、修繕情況（租客目前申請中的修繕單）。 想看實際畫面可預約 demo。

### tmp:kb:prospect/A/pain-points
標題：你們能解決什麼問題（痛點對應模組）
內容：管理租賃常見的收租對帳、合約、人多協作、報修等問題，金箍棒都有對應的模組。 想知道我們怎麼解決您的狀況，先選一個您最想改善的：

### tmp:kb:prospect/A/product-overview
標題：系統總覽與適不適合我
內容：金箍棒智慧物管能把物件、合約、收租對帳到智慧設備集中在一個系統管理。 想知道適不適合您，先讓我了解一下您的狀況。

### tmp:kb:prospect/A/why-choose-jgb
標題：為什麼選金箍棒
內容：選金箍棒的主要理由在「合約類型廣 + 多元金流 + IoT 整合 + 規模化團隊管理」：合約涵蓋一般／社會住宅／委託（社宅與委託代管尤其完整）、金流支援藍新／永豐／中信／國泰／愛金卡、可串接智慧門鎖／電錶（細節由專人說明）、多人權限搭配大房東報表方便對業主交代，另有押金設算息、VR 看屋、6 國語系等加值，且新帳號享免費試用一個月。 想實際體驗可直接開試用或預約 demo。

### tmp:kb:prospect/B/data-migration
標題：舊系統資料能否匯入（可匯入範圍）
內容：換系統最怕重建資料。 金箍棒可以用 Excel 範本批次匯入：物件（一般與社會住宅）、租客、社區、大房東聯絡簿；團隊（法人房東）帳號還能用「匯出草稿帳單→填寫→匯回」的方式批次更新帳單；合約與舊系統已繳完的歷史帳單不支援匯入。 搬遷細節可預約 demo，由專人依您的資料量評估。

### tmp:kb:prospect/B/individual-landlord-scale-fit
標題：個人房東（約 10～30 戶）適配與建議做法
內容：管 10 間左右的個人房東，最花時間的通常是收租對帳和合約來回。 金箍棒把物件、合約、帳務集中在一個系統：線上電子簽章簽約、自動產帳單與金流代收、收租對帳一條龍，取代 Excel 與 LINE 的零散作業，也能發租客通知、處理報修。 建議先用免費試用一個月實際跑跑看；正式方案級距與費用調整中，可於定價頁(https://www.jgbsmart.com/pricing)查看或由專人為您說明，這裡不報數字。 管到 20 間左右，帳單與對帳的量明顯變大、人工容易出錯。 金箍棒的帳務模組（自動帳單、多元金流代收、電子發票、儲值金）能把收租對帳自動化，搭配物件管理、電子簽章合約、租客通知與修繕，讓一個人也管得動這個規模。 可先免費試用一個月感受效率差異；方案級距與費用請見定價頁(https://www.jgbsmart.com/pricing)或由專人提供，這裡不報過時數字。 管到 30 間左右，已接近個人經營的規模上限，物件與帳務都相當可觀；未來若開始多人協作或要對業主交報表，會很快需要團隊管理與大房東報表。 金箍棒在這階段能用物件、合約、帳務的完整自動化撐住現有規模，並可平順銜接到團隊方案。 建議先免費試用一個月；正式級距與費用調整中，請見定價頁(https://www.jgbsmart.com/pricing)或由專人為您盤點，這裡不直接報價。

### tmp:kb:prospect/B/team-company-fit
標題：公司或包租代管團隊適合嗎
內容：公司或團隊（包租代管、物管）通常要多人分工，還得對業主交報表，需求比個人房東複雜。 金箍棒的全模組方案正好對應這種規模——除了物件、合約、帳務，還有團隊權限管理讓成員分工，以及大房東報表，把代收代付與營運狀況整理好、對業主交代清楚；若有現場抄電表或換門鎖的需求，智慧電錶／門鎖也能依需求整合（細節由專人說明）。 實際適合的模組組合與費用會依團隊規模而不同，建議直接預約 demo，由專人陪您盤點需求並提供報價。

### tmp:kb:prospect/C/bill-contents-extra-fees
標題：帳單內容與臨時加收費用
內容：系統帳單會顯示租金繳交進度（發送帳單→租客繳交→房東對帳→確認到帳，線上自動對帳時省略對帳步驟）與租金細節（費用週期、銀行名稱、帳戶名稱、帳號）。 帳單內容依合約條件自動產生，包含固定費用（租金）、變動費用（水、電、瓦斯）與另計項目；當月臨時要加收的費用，可在「待發送」帳單編輯，於「其他費用」欄位新增。

### tmp:kb:prospect/C/bill-format-customize
標題：帳單版面能不能自訂
內容：帳單能調的是內容，版面是選不是畫。 內容方面：帳單標題與備註、計費起訖日、繳費期限、費用品項（租金、水電度數、生活費用等，可增刪、改單價數量）、收款帳戶、收款章、排定發送日都可以在系統設定。 版面方面：收據版式可在「一般收據」與「財政部包租業租金收據」（可雙版或不檢附）之間選擇，但 logo、欄位排列等不開放任意自訂；電子發票的格式則由發票廠商（ezPay／eCloud）決定，系統只設定廠商與稅率。 有特殊版面需求可預約 demo 由專人評估。

### tmp:kb:prospect/C/billing-overview
標題：帳務管理模組做什麼
內容：收租、對帳很亂、催繳費時？ 金箍棒的帳務管理自動產帳單、線上金流代收（藍新/永豐/中信/國泰/愛金卡）、開電子發票，還有儲值金與押金設算息，收租對帳一條龍，不再用 Excel 人工對。 想看實際操作可預約 demo。 電子發票可以設定自動開立：帳單到帳後開立，或依寄送、到期前後的時機預先開立，不必逐張手動開。 開給個人的 B2C 發票可存入手機條碼、自然人憑證等載具；載具只用來存發票，不是付款方式。

### tmp:kb:prospect/C/community-batch-create
標題：社區建立與批次新增物件
內容：金箍棒用「社區」把同一棟或同一社區的物件歸戶管理。 流程是先建立社區，再在「社區總表」選該社區，按右側的「批次新增」下載 Excel 模板、填入物件資料後上傳，就能一次把整批物件建進系統；單筆新增則在物件總表「新增物件」。 想看實際畫面可預約 demo。

### tmp:kb:prospect/C/contract-esign-flow
標題：建約方式與線上電子簽約流程（含時效、身分、社宅、批次續約）
內容：合約多、怕簽錯、紙本來回慢？ 金箍棒的租約管理把一般租賃合約從建約到簽署搬到線上，一頁看完重點： 【建約方式】三種：電子合約（公版範本）、電子合約（客製化契約書）、紙本簽約（把既有的紙本合約上傳留存）。 上傳的既存合約與系統制式合約效力相同，後續合約、帳務、修繕一樣可追蹤。 【流程】只有「刊登中」的物件能建約。 系統以表單引導逐項填寫（租金、收款方式、傢俱與修繕責任、公證、附件、補充條款等），全部填完可先「預覽合約」確認合約文本，再寄送給租客；送出簽約邀請後，租客會收到簡訊／Email 等邀請通知，點連結線上電子簽名（不用手寫紙本），管理者回簽即完成。 租客可選擇免註冊（由管理方代填資料），或直接在邀請流程中完成註冊。 【時效】簽約邀請有效 72 小時（同時也是租客的契約審閱期），逾期連結失效、合約退回待發送，需重填租客資料再發。 【身分】建約時可用個人或法人（團隊）身分；團隊建約會把大小章、租賃管理人員、公司聯繫資訊一併帶進合約。 【社會住宅】社會住宅另有專屬流程：因公證為必要程序，須列印紙本完成公證後上傳歸檔，並非線上完成簽署。 【其他】建立新約需逐份進行（不支援批次匯入既有合約）；續約則可在執行中合約一次勾選多筆批次處理（正在提前解約申請中、點交中、點退中的合約無法納入）。 【費用】電子簽章在系統內不另外收費；方案包含哪些內容以定價頁為準。 方案與費用請見 [查看方案與費用](https://www.jgbsmart.com/pricing) 或由專人說明。 想看實際建約畫面可預約 demo。

### tmp:kb:prospect/C/contract-history-retention
標題：歷史合約保留多久
內容：「歷史合約」是已到期的合約，會依點退進度顯示「點退完成」「未退押金」「待退押金」「點退中」等狀態；點退可從合約結束前 30 天起隨時執行。 歷史合約與已完成的帳單系統都會保留、不自動刪除、沒有期限，但仍建議把重要合約下載 PDF 自行留存。

### tmp:kb:prospect/C/contract-modify-after-sign
標題：合約送出或簽完後能不能修改
內容：【修改】未發送的合約可直接編輯；已送出邀請要先取消再改（管理者主動取消會保留已填的租客資料；逾期或租客不同意退回則會清空）；租客已簽回但管理方尚未回簽時，可取消簽名後修改重發；雙方都簽完後不可直接修改，只能複製該合約重建新約重簽，或走資料異動申請。 合約 PDF 上的簽署參數（租金、電價、租期等）簽後不可更動；資料異動申請調整的是系統資料，不重簽則 PDF 與實際收款會不一致。

### tmp:kb:prospect/C/contract-templates
標題：合約範本有哪些可以選
內容：金箍棒的電子合約範本共 12 種：內政部中文版、內政部英文版、公會中文版各有原房東、包租業、代租代管三種身分版本，另有英泰文版（原房東、代租代管）與英越文版（單一版本）。 法人團隊 12 種都能選；個人房東可選內政部中文版、內政部英文版、英泰文版與公會中文版（皆原房東版）。 另有半伴客製化住宅租賃契約書、新北住都中心租賃契約書與汽車停車位契約書三種特殊用途範本，非一般房東可選。 也可以上傳自己既有的紙本合約留存。 包租與代管在系統上的差別主要在委託合約的設定：包租填包租租金與其計算制度，代管填服務費的制度、週期與約定日期；範本也依原房東、包租業、代租代管分版。

### tmp:kb:prospect/C/credit-card-rent-payment
標題：租客能不能用信用卡繳房租
內容：可以，前提是合約約定用「線上金流」收付款。 目前搭配信用卡支付的金流是藍新，房東在收款方式選「藍新金流」的「信用卡」，租客就能刷卡繳租；雙方在合約上也看得到約定的付款方式。

### tmp:kb:prospect/C/notification-channels
標題：系統通知管道與時機
內容：金箍棒的通知以 Email 為主，租客有綁定 LINE（或 Facebook）時會同步發 LINE 通知。 目前會自動發送的包括：帳單到期前五日、三日、一日的繳費提醒，逾期後每天提醒；發送簽約邀請時租客會收到邀請郵件；註冊時的驗證碼也走 Email。 想看通知內容可預約 demo。

### tmp:kb:prospect/C/overdue-reminder-late-fee
標題：租客逾期未繳怎麼辦
內容：怕租客忘記繳、拖著不繳？ 金箍棒的帳務管理會在帳單到期前五日、三日、一日自動發 Email 與 LINE 提醒給租客，逾期後改為每日通知；逾期帳單在系統上會以紅字與「逾期」標籤標示，房東首頁也會即時更新逾期帳款。 另外系統有滯納金機制（延遲金或逾期金，依團隊設定啟用）。 想看實際催繳畫面可預約 demo。

### tmp:kb:prospect/C/owner-report-collection-remit
標題：大房東報表與代收代付
內容：要定期跟業主交報表很花時間？ 金箍棒的大房東報表能把代收代付、月結與營運狀況整理成報表，並可排程自動寄送給業主，省去人工彙整。 想看報表內容可預約 demo。 代管業者對房東的月結差額，系統每月自動整理成差額發票群組並開立，次月重新計算。

### tmp:kb:prospect/C/payment-gateway-options
標題：金流廠商差別與申請條件
內容：四家金流差在「誰能申請」與「怎麼申請」：國泰世華與永豐銀行只開放法人，要自行向銀行申請，首次設定費 5,000 元；中國信託與藍新 NewebPay 法人與個人都能用，在金箍棒系統線上申請、免費。 個人房東目前可選的是中國信託與藍新。 要讓租客用信用卡繳租，目前只有藍新支援。 款項會匯入您指定的實體帳戶。 細節與提領時程可預約 demo 由專人說明。 除線上金流外也支援固定虛擬帳號與儲值金：租客把款項儲值到物件專屬的帳戶後，系統每日自動用儲值抵扣帳單。

### tmp:kb:prospect/C/property-management-overview
標題：房源管理模組做什麼
內容：物件多、資料分散難管？ 金箍棒的房源管理把所有物件集中：物件建檔、社區歸戶、批次上傳，還有招租公開頁與 VR 看屋連結，取代散落的 Excel。 物件可以貼團隊自訂的狀態標籤（預設有可帶看、待清潔、待簽約、維修中、不出租、待完善六種），方便篩選與分工。 想看實際畫面可預約 demo。

### tmp:kb:prospect/C/property-status-meaning
標題：物件狀態是什麼意思
內容：物件總表把物件分成四種狀態：「未刊登」是建好還沒對外刊登，可編輯、刊登或刪除；「刊登中」是已對外招租，可編輯、取消刊登、建立合約；「洽談中」代表已經建立合約但雙方還沒都簽署完成；雙方簽完就變成「合約中」（租約中）。 另外要注意刊登與合約是兩條獨立的軸，租約中的物件也可以同時在刊登中。

### tmp:kb:prospect/C/rental-storefront-vr
標題：招租店舖與 VR 看屋
內容：金箍棒每個帳號或團隊都有自己的「房東對外首頁」（招租店舖），刊登中的物件會出現在上面供房客瀏覽；團隊可以在團隊管理設定招租頁面的專屬網址與時區，強化品牌辨識。 新增物件時可上傳 VR 物件連結，房客能在線上看屋。 想看招租頁長什麼樣可預約 demo。

### tmp:kb:prospect/C/repair-system
標題：線上報修與進度追蹤
內容：報修處理慢、追蹤不易？ 金箍棒的修繕系統讓租客線上報修、房東與管理方追蹤處理進度，把報修流程數位化。 想看實際流程可預約 demo。

### tmp:kb:prospect/C/role-permission-granularity
標題：成員權限能不能細分（只看不改、看不到財務）
內容：可以。 金箍棒的權限依八大功能分類（物件、合約、帳務、修繕、通知、團隊、人員、大房東管理），每類再細分查看、編輯、新增等項目；不給某位成員「查看帳務」，他就看不到帳務圖表、收付款與屋主帳單。 系統內建擁有者、最高管理者、店長、會計、一般業務等十種範本角色，也可以自訂角色；還能把物件指派給經理人，只給他該物件與對應合約的查看／編輯權限。

### tmp:kb:prospect/C/smart-meter-lock-iot
標題：智慧電錶與門鎖整合
內容：現場抄電表、換門鎖很煩？ 金箍棒有整合智慧電錶（抄表可自動帶入帳單）與智慧門鎖，屬硬體設備，實際支援範圍、安裝與費用由專人為您說明。 門鎖分兩型：「私人門鎖」是單一房間的門鎖，只綁一個物件，房東與租客各自設一組密碼；「共用門鎖」是大樓或住家大門，可綁多個物件，由房東設一組共用密碼給租客使用。 可留資由專人與您聯絡。

### tmp:kb:prospect/C/team-management-overview
標題：團隊管理模組做什麼
內容：人多、管不動？ 金箍棒的團隊管理支援多人帳號與角色權限，讓代管團隊分工協作，並提供大房東報表對業主交代。 系統沒有叫「系統管理」的模組；成員、角色權限、訂閱方案這類設定都在團隊管理裡。 想了解團隊方案可預約 demo 由專人說明。

### tmp:kb:prospect/C/what-is-owner-landlord
標題：大房東是什麼
內容：在金箍棒裡，「大房東」指的是把物件交給您代管的業主。 物管團隊可以在大房東列表用 email 邀請業主，並把特定物件授權給他，業主登入後就能瀏覽自己物件的合約、帳務與修繕狀態，不必逐一問您。 搭配大房東報表，代收代付與月結會自動整理並可排程寄給業主。 想看業主端的畫面可預約 demo。

### tmp:kb:prospect/D/account-registration
標題：怎麼註冊帳號
內容：註冊很快：到 JGB 網站點「註冊」，輸入 Email 收驗證碼，填基本資料就完成；也可以用 Facebook、Gmail、LINE 第三方帳號註冊，系統會一併建立 Email 登入。 一個帳號同時可有房東與租客身分，手機號碼作輔助登入。 租客不一定要自己註冊，房東建立合約時輸入租客 Email 或手機發出簽約邀請，租客也能從電子合約完成註冊。

### tmp:kb:prospect/D/free-trial
標題：可以免費試用嗎
內容：可以，新帳號享有免費試用一個月，註冊即可開始，先實際用過再決定。 需要協助開通可以留個聯絡方式，或直接預約 demo 由專人帶您看。

### tmp:kb:prospect/D/pricing-plans
標題：怎麼收費
內容：金箍棒採訂閱制，方案依管理規模（物件數）以及是否需要團隊、大房東報表、IoT 等功能分級。 目前方案與價格正在調整，為避免提供過時數字，實際級距與費用請參考線上定價頁(https://www.jgbsmart.com/pricing)，或留下聯絡方式由專人為您報價。 也歡迎先用免費試用一個月實際體驗。

### tmp:kb:prospect/D/property-quota-limit
標題：方案物件額度上限
內容：金箍棒的方案是依可管理的物件數分級，物件額度用滿就無法再新增，可以升級方案、加購額度，或把不再使用的物件下架釋放額度；目前用量在「訂閱方案」頁看得到。 各方案的物件數級距請以線上定價頁為準 [查看方案與費用](https://www.jgbsmart.com/pricing)。 免費方案預設可建 5 個物件（免費試用一個月就是免費方案），實際額度以帳號內「訂閱方案」頁顯示為準。 新帳號享有免費試用一個月，可先實際體驗再選方案。

### tmp:kb:prospect/D/subscription-change-renewal
標題：升級、續約與取消訂閱
內容：方案的變更在「團隊管理」的「訂閱方案」頁：點「變更」、選物件數量對應的年／月方案、完成付款即生效，支出可在「付款紀錄」查看。 訂閱到期會自動續約扣款；若扣款失敗，方案會失效、物件會被系統自動下架，補完付款後再重新上架即可。 要取消訂閱，在方案頁下方的服務條款連結點「取消訂閱」。

### tmp:kb:prospect/E/competitor-comparison
標題：跟 Bananas、屋我也差在哪
內容：同類的租賃管理系統還有 Bananas、屋我也，三者都做物件、合約、帳務，差異主要在合約類型廣度、金流、IoT 整合與適用場景。 以公開官網可查的事實來說：金箍棒的合約類型較完整（涵蓋一般租賃、社會住宅、委託），金流支援多元（藍新／永豐／中信／國泰／愛金卡），並有智慧門鎖／電錶整合（硬體細節由專人說明）與大房東報表，適合社宅委託、需多元收款、要對業主交報表的代管團隊。 對方官網未明確提及的功能，我們無法替他們確認，建議您直接向對方詢問。 若想實際比較，歡迎預約 demo。

### tmp:kb:prospect/E/competitor-neutrality
標題：會評論競爭對手嗎
內容：我們不會評論同業的好壞或內部狀況，只就公開可查的事實、以及金箍棒實際適合的情境提供中立資訊；對方未明確提供的功能，建議您直接向對方確認，我們不會替他們斷言有或沒有。 若想實際比較，最準的方式是預約 demo 或直接開免費試用體驗。

### tmp:kb:prospect/G/migration-limits
標題：資料搬遷目前不支援的項目（合約與歷史帳單）
內容：要特別說明的是：合約目前不支援批次匯入，需要逐筆建立（線上電子簽新約，或上傳既有紙本合約 PDF 存檔）；舊系統已繳完的歷史帳單也沒有搬移功能。 搬遷細節可預約 demo，由專人依您的資料量評估。

### tmp:kb:prospect/G/utility-split-advice
標題：水電費怎麼分算與大概多少錢
內容：系統支援按合約分算，金額看合約。


## 三份角度提議
[
 {
  "angle": "user_question_path",
  "coarses": [
   {
    "id": "A",
    "title": "帳號與身分"
   },
   {
    "id": "B",
    "title": "團隊、人員與大房東"
   },
   {
    "id": "C",
    "title": "社區與物件"
   },
   {
    "id": "D",
    "title": "租約（含委託約子題）"
   },
   {
    "id": "E",
    "title": "帳務（含發票、收款金流、抄表）"
   },
   {
    "id": "F",
    "title": "修繕"
   },
   {
    "id": "G",
    "title": "裝置（IoT）"
   },
   {
    "id": "H",
    "title": "幫助中心"
   },
   {
    "id": "I",
    "title": "方案與導入"
   }
  ],
  "fines": [
   {
    "id": "prospect/I/product-overview",
    "coarse_id": "I",
    "title": "系統總覽、能解決什麼問題、適不適合我",
    "slug": "product-overview",
    "merge_of": [
     "tmp:kb:prospect/A/product-overview",
     "tmp:kb:prospect/A/pain-points"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「你們是什麼系統／能解決什麼／適合我嗎」是同一個開場問題，答案都是模組總覽加追問狀況，故合併為導入前總覽。"
   },
   {
    "id": "prospect/I/why-choose-jgb",
    "coarse_id": "I",
    "title": "為什麼選金箍棒",
    "slug": "why-choose-jgb",
    "merge_of": [
     "tmp:kb:prospect/A/why-choose-jgb"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「為什麼選你們」是獨立的選型問題，與總覽和競品比較的問法不同。"
   },
   {
    "id": "prospect/I/dashboard-overview",
    "coarse_id": "I",
    "title": "登入後首頁儀表板顯示哪些數據",
    "slug": "dashboard-overview",
    "merge_of": [
     "tmp:kb:prospect/A/dashboard-overview"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「登入後看得到什麼」是導入前的產品畫面問題，內容橫跨收支、帳務、修繕，不屬單一領域，歸方案與導入。"
   },
   {
    "id": "prospect/I/individual-landlord-fit",
    "coarse_id": "I",
    "title": "個人房東（約 10～30 戶）適不適合",
    "slug": "individual-landlord-fit",
    "merge_of": [
     "tmp:kb:prospect/B/individual-landlord-scale-fit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「我管十幾間適合嗎」是個人房東的適配問題，與團隊適配問法不同。"
   },
   {
    "id": "prospect/I/team-company-fit",
    "coarse_id": "I",
    "title": "公司或包租代管團隊適不適合",
    "slug": "team-company-fit",
    "merge_of": [
     "tmp:kb:prospect/B/team-company-fit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「我們是公司／代管團隊適合嗎」是團隊規模的適配問題，獨立於個人房東適配。"
   },
   {
    "id": "prospect/I/data-migration",
    "coarse_id": "I",
    "title": "舊系統資料能否匯入（可匯入與不支援項目）",
    "slug": "data-migration",
    "merge_of": [
     "tmp:kb:prospect/B/data-migration",
     "tmp:kb:prospect/G/migration-limits"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「舊資料能不能搬過來」一個問題就要同時答可匯入與不支援項目，故合併為單一導入問題。"
   },
   {
    "id": "prospect/I/free-trial",
    "coarse_id": "I",
    "title": "可以免費試用嗎",
    "slug": "free-trial",
    "merge_of": [
     "tmp:kb:prospect/D/free-trial"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「能不能先試用」是獨立的方案問題。"
   },
   {
    "id": "prospect/I/pricing-plans",
    "coarse_id": "I",
    "title": "怎麼收費",
    "slug": "pricing-plans",
    "merge_of": [
     "tmp:kb:prospect/D/pricing-plans"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「多少錢／怎麼收費」是獨立的方案問題。"
   },
   {
    "id": "prospect/I/property-quota-limit",
    "coarse_id": "I",
    "title": "方案物件額度上限與用滿怎麼辦",
    "slug": "property-quota-limit",
    "merge_of": [
     "tmp:kb:prospect/D/property-quota-limit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「可以管幾個物件／額度滿了怎麼辦」由方案級距決定，歸方案而非物件。"
   },
   {
    "id": "prospect/I/subscription-change-renewal",
    "coarse_id": "I",
    "title": "升級、續約與取消訂閱",
    "slug": "subscription-change-renewal",
    "merge_of": [
     "tmp:kb:prospect/D/subscription-change-renewal"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「怎麼升級／取消／續約」是訂閱操作問題，與收費級距問法不同。"
   },
   {
    "id": "prospect/I/competitor-comparison",
    "coarse_id": "I",
    "title": "跟 Bananas、屋我也差在哪（含中立原則）",
    "slug": "competitor-comparison",
    "merge_of": [
     "tmp:kb:prospect/E/competitor-comparison",
     "tmp:kb:prospect/E/competitor-neutrality"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「你們跟某某比怎樣」與「你覺得某某好不好」都落在同一個競品問題，中立原則是該回答的一部分，故合併。"
   },
   {
    "id": "prospect/A/account-registration",
    "coarse_id": "A",
    "title": "怎麼註冊帳號（含驗證碼通知）",
    "slug": "account-registration",
    "merge_of": [
     "tmp:kb:prospect/D/account-registration"
    ],
    "split_from": [
     "tmp:kb:prospect/C/notification-channels"
    ],
    "moved_from": [],
    "reason": "「怎麼註冊」是帳號問題，註冊驗證碼走 Email 是通知投遞細節，歸它所通知的註冊領域。"
   },
   {
    "id": "prospect/B/team-management-overview",
    "coarse_id": "B",
    "title": "團隊管理模組做什麼",
    "slug": "team-management-overview",
    "merge_of": [
     "tmp:kb:prospect/C/team-management-overview"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「多人怎麼一起用」是團隊管理的總覽問題。"
   },
   {
    "id": "prospect/B/role-permission-granularity",
    "coarse_id": "B",
    "title": "成員權限能不能細分",
    "slug": "role-permission-granularity",
    "merge_of": [
     "tmp:kb:prospect/C/role-permission-granularity"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「能不能讓某人只看不改／看不到財務」是獨立的權限問題，與團隊總覽問法不同。"
   },
   {
    "id": "prospect/B/what-is-owner-landlord",
    "coarse_id": "B",
    "title": "大房東是什麼",
    "slug": "what-is-owner-landlord",
    "merge_of": [
     "tmp:kb:prospect/C/what-is-owner-landlord"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「大房東是什麼意思」是名詞定義問題，獨立於報表功能。"
   },
   {
    "id": "prospect/B/owner-report-collection-remit",
    "coarse_id": "B",
    "title": "大房東報表與代收代付怎麼交代",
    "slug": "owner-report-collection-remit",
    "merge_of": [
     "tmp:kb:prospect/C/owner-report-collection-remit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「怎麼跟業主交報表」是對大房東的問題，歸大房東領域。"
   },
   {
    "id": "prospect/C/property-management-overview",
    "coarse_id": "C",
    "title": "房源管理模組做什麼（含自訂狀態標籤）",
    "slug": "property-management-overview",
    "merge_of": [
     "tmp:kb:prospect/C/property-management-overview"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「物件怎麼管」是物件的總覽問題，自訂標籤是物件本身屬性。"
   },
   {
    "id": "prospect/C/community-batch-create",
    "coarse_id": "C",
    "title": "社區建立與批次新增物件",
    "slug": "community-batch-create",
    "merge_of": [
     "tmp:kb:prospect/C/community-batch-create"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「怎麼一次建一整批物件」是獨立的操作問題。"
   },
   {
    "id": "prospect/C/property-status-meaning",
    "coarse_id": "C",
    "title": "物件狀態（未刊登／刊登中／洽談中／合約中）是什麼意思",
    "slug": "property-status-meaning",
    "merge_of": [
     "tmp:kb:prospect/C/property-status-meaning"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "使用者是從物件總表的狀態欄發問，該欄以刊登軸為主並說明與合約軸獨立，歸物件並另見租約。"
   },
   {
    "id": "prospect/C/rental-storefront-vr",
    "coarse_id": "C",
    "title": "招租店舖與 VR 看屋",
    "slug": "rental-storefront-vr",
    "merge_of": [
     "tmp:kb:prospect/C/rental-storefront-vr"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「有沒有對外招租頁／VR」是物件對外呈現的獨立問題。"
   },
   {
    "id": "prospect/D/contract-esign-flow",
    "coarse_id": "D",
    "title": "建約方式與線上電子簽約流程（含身分、費用、邀請通知）",
    "slug": "contract-esign-flow",
    "merge_of": [
     "tmp:kb:prospect/C/contract-esign-flow"
    ],
    "split_from": [
     "tmp:kb:prospect/C/notification-channels"
    ],
    "moved_from": [],
    "reason": "「怎麼建約／怎麼線上簽」是一個問題，簽約邀請通知是它的投遞管道，時效、社宅、批次續約則是另外的問法，故拆出。"
   },
   {
    "id": "prospect/D/esign-invitation-validity",
    "coarse_id": "D",
    "title": "簽約邀請多久有效、逾期怎麼辦",
    "slug": "esign-invitation-validity",
    "merge_of": [
     "tmp:kb:prospect/C/contract-esign-flow"
    ],
    "split_from": [
     "tmp:kb:prospect/C/contract-esign-flow"
    ],
    "moved_from": [],
    "reason": "「邀請連結多久失效」是獨立可答的問題，從簽約流程拆出。"
   },
   {
    "id": "prospect/D/social-housing-contract",
    "coarse_id": "D",
    "title": "社會住宅合約怎麼簽（公證與紙本上傳）",
    "slug": "social-housing-contract",
    "merge_of": [
     "tmp:kb:prospect/C/contract-esign-flow"
    ],
    "split_from": [
     "tmp:kb:prospect/C/contract-esign-flow"
    ],
    "moved_from": [],
    "reason": "「社宅可以線上簽嗎」答案與一般流程相反，是獨立問題。"
   },
   {
    "id": "prospect/D/contract-renewal-batch",
    "coarse_id": "D",
    "title": "續約能不能批次處理",
    "slug": "contract-renewal-batch",
    "merge_of": [
     "tmp:kb:prospect/C/contract-esign-flow"
    ],
    "split_from": [
     "tmp:kb:prospect/C/contract-esign-flow"
    ],
    "moved_from": [],
    "reason": "「續約可以一次多筆嗎」是獨立於建約流程的問題。"
   },
   {
    "id": "prospect/D/contract-templates",
    "coarse_id": "D",
    "title": "合約範本有哪些可以選",
    "slug": "contract-templates",
    "merge_of": [
     "tmp:kb:prospect/C/contract-templates"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「有哪些範本」是獨立問題，包租與代管差別另拆為委託約子題。"
   },
   {
    "id": "prospect/D/sublease-vs-management-contract",
    "coarse_id": "D",
    "title": "包租與代管在委託合約上的差別",
    "slug": "sublease-vs-management-contract",
    "merge_of": [
     "tmp:kb:prospect/C/contract-templates"
    ],
    "split_from": [
     "tmp:kb:prospect/C/contract-templates"
    ],
    "moved_from": [],
    "reason": "「包租跟代管差在哪」是委託約子題的獨立問法，從範本清單拆出。"
   },
   {
    "id": "prospect/D/contract-modify-after-sign",
    "coarse_id": "D",
    "title": "合約送出或簽完後能不能修改",
    "slug": "contract-modify-after-sign",
    "merge_of": [
     "tmp:kb:prospect/C/contract-modify-after-sign"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「簽完能不能改」是獨立問題。"
   },
   {
    "id": "prospect/D/contract-history-retention",
    "coarse_id": "D",
    "title": "歷史合約保留多久",
    "slug": "contract-history-retention",
    "merge_of": [
     "tmp:kb:prospect/C/contract-history-retention"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「舊合約會不會被刪」是獨立問題。"
   },
   {
    "id": "prospect/E/billing-overview",
    "coarse_id": "E",
    "title": "帳務管理模組做什麼",
    "slug": "billing-overview",
    "merge_of": [
     "tmp:kb:prospect/C/billing-overview"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「收租對帳怎麼做」是帳務總覽問題，電子發票自動開立是另一個問法故拆出。"
   },
   {
    "id": "prospect/E/einvoice-issuing",
    "coarse_id": "E",
    "title": "電子發票能不能自動開、載具怎麼用",
    "slug": "einvoice-issuing",
    "merge_of": [
     "tmp:kb:prospect/C/billing-overview"
    ],
    "split_from": [
     "tmp:kb:prospect/C/billing-overview"
    ],
    "moved_from": [],
    "reason": "「發票可以自動開嗎」是獨立可答的問題，從帳務總覽拆出。"
   },
   {
    "id": "prospect/E/bill-contents-extra-fees",
    "coarse_id": "E",
    "title": "帳單內容與臨時加收費用",
    "slug": "bill-contents-extra-fees",
    "merge_of": [
     "tmp:kb:prospect/C/bill-contents-extra-fees"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「帳單有什麼／臨時費用怎麼加」是出現在帳單列上的問題，歸帳務。"
   },
   {
    "id": "prospect/E/bill-format-customize",
    "coarse_id": "E",
    "title": "帳單版面能不能自訂",
    "slug": "bill-format-customize",
    "merge_of": [
     "tmp:kb:prospect/C/bill-format-customize"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「帳單能不能改版面」是獨立問題，與帳單內容問法不同。"
   },
   {
    "id": "prospect/E/overdue-reminder-late-fee",
    "coarse_id": "E",
    "title": "租客逾期未繳怎麼辦（含繳費提醒通知）",
    "slug": "overdue-reminder-late-fee",
    "merge_of": [
     "tmp:kb:prospect/C/overdue-reminder-late-fee"
    ],
    "split_from": [
     "tmp:kb:prospect/C/notification-channels"
    ],
    "moved_from": [],
    "reason": "「逾期怎麼催」是帳務問題，繳費提醒的通知管道與時機歸它所通知的帳單領域。"
   },
   {
    "id": "prospect/E/payment-gateway-options",
    "coarse_id": "E",
    "title": "金流廠商差別與申請條件",
    "slug": "payment-gateway-options",
    "merge_of": [
     "tmp:kb:prospect/C/payment-gateway-options"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「哪家金流、怎麼申請」是收款金流問題，虛擬帳號與儲值金另拆。"
   },
   {
    "id": "prospect/E/virtual-account-prepaid",
    "coarse_id": "E",
    "title": "固定虛擬帳號與儲值金抵扣",
    "slug": "virtual-account-prepaid",
    "merge_of": [
     "tmp:kb:prospect/C/payment-gateway-options"
    ],
    "split_from": [
     "tmp:kb:prospect/C/payment-gateway-options"
    ],
    "moved_from": [],
    "reason": "「有沒有虛擬帳號／能不能儲值」是獨立的收款方式問題，從金流廠商拆出。"
   },
   {
    "id": "prospect/E/credit-card-rent-payment",
    "coarse_id": "E",
    "title": "租客能不能用信用卡繳房租",
    "slug": "credit-card-rent-payment",
    "merge_of": [
     "tmp:kb:prospect/C/credit-card-rent-payment"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「能不能刷卡」是租客端最常見的獨立問法，歸收款金流。"
   },
   {
    "id": "prospect/E/utility-split-calculation",
    "coarse_id": "E",
    "title": "水電費怎麼分算",
    "slug": "utility-split-calculation",
    "merge_of": [
     "tmp:kb:prospect/G/utility-split-advice"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「水電怎麼算」是錢怎麼算的問題，歸帳務。"
   },
   {
    "id": "prospect/F/repair-system",
    "coarse_id": "F",
    "title": "線上報修與進度追蹤",
    "slug": "repair-system",
    "merge_of": [
     "tmp:kb:prospect/C/repair-system"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「租客怎麼報修」是修繕領域的獨立問題。"
   },
   {
    "id": "prospect/G/smart-meter-lock-iot",
    "coarse_id": "G",
    "title": "智慧電錶與門鎖整合",
    "slug": "smart-meter-lock-iot",
    "merge_of": [
     "tmp:kb:prospect/C/smart-meter-lock-iot"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「有沒有支援門鎖／電錶」是裝置領域的獨立問題。"
   }
  ],
  "id_map": [
   {
    "old": "tmp:kb:prospect/A/dashboard-overview",
    "new": "prospect/I/dashboard-overview",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/A/pain-points",
    "new": "prospect/I/product-overview",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/A/product-overview",
    "new": "prospect/I/product-overview",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/A/why-choose-jgb",
    "new": "prospect/I/why-choose-jgb",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/B/data-migration",
    "new": "prospect/I/data-migration",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/B/individual-landlord-scale-fit",
    "new": "prospect/I/individual-landlord-fit",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/B/team-company-fit",
    "new": "prospect/I/team-company-fit",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/bill-contents-extra-fees",
    "new": "prospect/E/bill-contents-extra-fees",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/bill-format-customize",
    "new": "prospect/E/bill-format-customize",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/billing-overview",
    "new": "prospect/E/billing-overview",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/billing-overview",
    "new": "prospect/E/einvoice-issuing",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/community-batch-create",
    "new": "prospect/C/community-batch-create",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/contract-esign-flow",
    "new": "prospect/D/contract-esign-flow",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/contract-esign-flow",
    "new": "prospect/D/esign-invitation-validity",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/contract-esign-flow",
    "new": "prospect/D/social-housing-contract",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/contract-esign-flow",
    "new": "prospect/D/contract-renewal-batch",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/contract-history-retention",
    "new": "prospect/D/contract-history-retention",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/contract-modify-after-sign",
    "new": "prospect/D/contract-modify-after-sign",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/contract-templates",
    "new": "prospect/D/contract-templates",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/contract-templates",
    "new": "prospect/D/sublease-vs-management-contract",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/credit-card-rent-payment",
    "new": "prospect/E/credit-card-rent-payment",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/notification-channels",
    "new": "prospect/E/overdue-reminder-late-fee",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/notification-channels",
    "new": "prospect/D/contract-esign-flow",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/notification-channels",
    "new": "prospect/A/account-registration",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/overdue-reminder-late-fee",
    "new": "prospect/E/overdue-reminder-late-fee",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/owner-report-collection-remit",
    "new": "prospect/B/owner-report-collection-remit",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/payment-gateway-options",
    "new": "prospect/E/payment-gateway-options",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/payment-gateway-options",
    "new": "prospect/E/virtual-account-prepaid",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/property-management-overview",
    "new": "prospect/C/property-management-overview",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/property-status-meaning",
    "new": "prospect/C/property-status-meaning",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/rental-storefront-vr",
    "new": "prospect/C/rental-storefront-vr",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/repair-system",
    "new": "prospect/F/repair-system",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/role-permission-granularity",
    "new": "prospect/B/role-permission-granularity",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/smart-meter-lock-iot",
    "new": "prospect/G/smart-meter-lock-iot",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/team-management-overview",
    "new": "prospect/B/team-management-overview",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/what-is-owner-landlord",
    "new": "prospect/B/what-is-owner-landlord",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/D/account-registration",
    "new": "prospect/A/account-registration",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/D/free-trial",
    "new": "prospect/I/free-trial",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/D/pricing-plans",
    "new": "prospect/I/pricing-plans",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/D/property-quota-limit",
    "new": "prospect/I/property-quota-limit",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/D/subscription-change-renewal",
    "new": "prospect/I/subscription-change-renewal",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/E/competitor-comparison",
    "new": "prospect/I/competitor-comparison",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/E/competitor-neutrality",
    "new": "prospect/I/competitor-comparison",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/G/migration-limits",
    "new": "prospect/I/data-migration",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/G/utility-split-advice",
    "new": "prospect/E/utility-split-calculation",
    "op": "keep"
   }
  ]
 },
 {
  "angle": "content_boundary",
  "coarses": [
   {
    "id": "A",
    "title": "帳號與身分"
   },
   {
    "id": "B",
    "title": "團隊、人員與大房東"
   },
   {
    "id": "C",
    "title": "社區與物件"
   },
   {
    "id": "D",
    "title": "租約（含委託約子題）"
   },
   {
    "id": "E",
    "title": "帳務（含發票、收款金流、抄表）"
   },
   {
    "id": "F",
    "title": "修繕"
   },
   {
    "id": "G",
    "title": "裝置（IoT）"
   },
   {
    "id": "H",
    "title": "幫助中心"
   },
   {
    "id": "I",
    "title": "方案與導入"
   }
  ],
  "fines": [
   {
    "id": "prospect/A/account-registration",
    "coarse_id": "A",
    "title": "怎麼註冊帳號（含驗證碼通知）",
    "slug": "account-registration",
    "merge_of": [
     "tmp:kb:prospect/D/account-registration",
     "tmp:kb:prospect/C/notification-channels"
    ],
    "split_from": [
     "tmp:kb:prospect/C/notification-channels"
    ],
    "moved_from": [],
    "reason": "註冊流程獨立成立；註冊驗證碼走 Email 是註冊流程的一部分，通知不自成細目，併入帳號領域。"
   },
   {
    "id": "prospect/B/team-management-overview",
    "coarse_id": "B",
    "title": "團隊管理模組做什麼",
    "slug": "team-management-overview",
    "merge_of": [
     "tmp:kb:prospect/C/team-management-overview"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "團隊模組總覽自身完整，主題為多人協作，歸團隊粗目。"
   },
   {
    "id": "prospect/B/role-permission-granularity",
    "coarse_id": "B",
    "title": "成員權限能不能細分",
    "slug": "role-permission-granularity",
    "merge_of": [
     "tmp:kb:prospect/C/role-permission-granularity"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "權限顆粒度與範本角色自身完整，與團隊總覽主題不同，獨立一細目。"
   },
   {
    "id": "prospect/B/what-is-owner-landlord",
    "coarse_id": "B",
    "title": "大房東是什麼",
    "slug": "what-is-owner-landlord",
    "merge_of": [
     "tmp:kb:prospect/C/what-is-owner-landlord"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "大房東定義、邀請與業主端可見範圍自身完整，與報表細目主題不同。"
   },
   {
    "id": "prospect/B/owner-report",
    "coarse_id": "B",
    "title": "大房東報表與排程寄送",
    "slug": "owner-report",
    "merge_of": [
     "tmp:kb:prospect/C/owner-report-collection-remit"
    ],
    "split_from": [
     "tmp:kb:prospect/C/owner-report-collection-remit"
    ],
    "moved_from": [],
    "reason": "報表內容與排程寄送可獨立成立；月結差額發票屬發票開立主題，各自完整故拆出。"
   },
   {
    "id": "prospect/C/property-management-overview",
    "coarse_id": "C",
    "title": "房源管理模組做什麼（含自訂狀態標籤）",
    "slug": "property-management-overview",
    "merge_of": [
     "tmp:kb:prospect/C/property-management-overview"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "模組總覽與自訂標籤互相依賴才完整，屬同一細目；與系統四種物件狀態是不同主題。"
   },
   {
    "id": "prospect/C/property-status-meaning",
    "coarse_id": "C",
    "title": "物件狀態是什麼意思",
    "slug": "property-status-meaning",
    "merge_of": [
     "tmp:kb:prospect/C/property-status-meaning"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "四種系統狀態與刊登／合約雙軸自身完整，物件本身屬性歸社區與物件。"
   },
   {
    "id": "prospect/C/community-batch-create",
    "coarse_id": "C",
    "title": "社區建立與批次新增物件",
    "slug": "community-batch-create",
    "merge_of": [
     "tmp:kb:prospect/C/community-batch-create"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "社區歸戶與批次新增流程互相依賴，自身完整。"
   },
   {
    "id": "prospect/C/rental-storefront-vr",
    "coarse_id": "C",
    "title": "招租店舖與 VR 看屋",
    "slug": "rental-storefront-vr",
    "merge_of": [
     "tmp:kb:prospect/C/rental-storefront-vr"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "對外招租頁與 VR 連結自身完整，與物件建檔主題不同。"
   },
   {
    "id": "prospect/D/contract-creation-esign-flow",
    "coarse_id": "D",
    "title": "建約方式與線上電子簽約流程（含時效、身分、社宅、簽約邀請通知、費用）",
    "slug": "contract-creation-esign-flow",
    "merge_of": [
     "tmp:kb:prospect/C/contract-esign-flow",
     "tmp:kb:prospect/C/notification-channels"
    ],
    "split_from": [
     "tmp:kb:prospect/C/contract-esign-flow",
     "tmp:kb:prospect/C/notification-channels"
    ],
    "moved_from": [],
    "reason": "建約方式、流程、72 小時時效、身分、社宅公證與費用互相依賴才完整；簽約邀請通知歸它所通知的租約領域。"
   },
   {
    "id": "prospect/D/contract-batch-renewal",
    "coarse_id": "D",
    "title": "續約能不能批次處理",
    "slug": "contract-batch-renewal",
    "merge_of": [
     "tmp:kb:prospect/C/contract-esign-flow"
    ],
    "split_from": [
     "tmp:kb:prospect/C/contract-esign-flow"
    ],
    "moved_from": [],
    "reason": "批次續約與其排除條件可獨立回答，與建新約流程主題不同，故拆出。"
   },
   {
    "id": "prospect/D/contract-modify-after-sign",
    "coarse_id": "D",
    "title": "合約送出或簽完後能不能修改",
    "slug": "contract-modify-after-sign",
    "merge_of": [
     "tmp:kb:prospect/C/contract-modify-after-sign"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "各階段可否修改與資料異動申請自身完整，由合約條款決定歸租約。"
   },
   {
    "id": "prospect/D/contract-history-retention",
    "coarse_id": "D",
    "title": "歷史合約保留多久（含點退狀態）",
    "slug": "contract-history-retention",
    "merge_of": [
     "tmp:kb:prospect/C/contract-history-retention"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "歷史合約狀態與保留期限互相依賴才完整，屬同一細目。"
   },
   {
    "id": "prospect/D/contract-templates",
    "coarse_id": "D",
    "title": "合約範本有哪些可以選",
    "slug": "contract-templates",
    "merge_of": [
     "tmp:kb:prospect/C/contract-templates"
    ],
    "split_from": [
     "tmp:kb:prospect/C/contract-templates"
    ],
    "moved_from": [],
    "reason": "12 種範本、特殊範本與身分可選範圍自身完整；包租／代管委託約差異是另一主題，故拆出。"
   },
   {
    "id": "prospect/D/entrust-contract-sublease-vs-management",
    "coarse_id": "D",
    "title": "包租與代管在委託合約設定上的差別",
    "slug": "entrust-contract-sublease-vs-management",
    "merge_of": [
     "tmp:kb:prospect/C/contract-templates"
    ],
    "split_from": [
     "tmp:kb:prospect/C/contract-templates"
    ],
    "moved_from": [],
    "reason": "委託約的包租租金制度與代管服務費設定可獨立回答，屬租約粗目的委託約子題。"
   },
   {
    "id": "prospect/E/billing-overview",
    "coarse_id": "E",
    "title": "帳務管理模組做什麼",
    "slug": "billing-overview",
    "merge_of": [
     "tmp:kb:prospect/C/billing-overview"
    ],
    "split_from": [
     "tmp:kb:prospect/C/billing-overview"
    ],
    "moved_from": [],
    "reason": "帳務模組總覽自身完整；電子發票自動開立與載具是獨立主題，故拆出。"
   },
   {
    "id": "prospect/E/einvoice-auto-issue-carrier",
    "coarse_id": "E",
    "title": "電子發票自動開立時機與載具",
    "slug": "einvoice-auto-issue-carrier",
    "merge_of": [
     "tmp:kb:prospect/C/billing-overview"
    ],
    "split_from": [
     "tmp:kb:prospect/C/billing-overview"
    ],
    "moved_from": [],
    "reason": "發票開立時機與載具用途可獨立回答，與模組總覽主題不同。"
   },
   {
    "id": "prospect/E/bill-contents-extra-fees",
    "coarse_id": "E",
    "title": "帳單內容、臨時加收費用與水電分算",
    "slug": "bill-contents-extra-fees",
    "merge_of": [
     "tmp:kb:prospect/C/bill-contents-extra-fees",
     "tmp:kb:prospect/G/utility-split-advice"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "水電分算依合約帶入變動費用，單獨不成立，需依附帳單內容才完整；錢怎麼算歸帳務。"
   },
   {
    "id": "prospect/E/bill-format-customize",
    "coarse_id": "E",
    "title": "帳單版面能不能自訂",
    "slug": "bill-format-customize",
    "merge_of": [
     "tmp:kb:prospect/C/bill-format-customize"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "可調內容與版式選項自身完整，與帳單內容主題不同。"
   },
   {
    "id": "prospect/E/payment-gateway-options",
    "coarse_id": "E",
    "title": "金流廠商差別與申請條件",
    "slug": "payment-gateway-options",
    "merge_of": [
     "tmp:kb:prospect/C/payment-gateway-options"
    ],
    "split_from": [
     "tmp:kb:prospect/C/payment-gateway-options"
    ],
    "moved_from": [],
    "reason": "四家金流的申請資格、費用與撥款自身完整；固定虛擬帳號與儲值金是另一收款機制，故拆出。錢怎麼進來歸收款金流。"
   },
   {
    "id": "prospect/E/virtual-account-prepaid-balance",
    "coarse_id": "E",
    "title": "固定虛擬帳號與儲值金抵扣",
    "slug": "virtual-account-prepaid-balance",
    "merge_of": [
     "tmp:kb:prospect/C/payment-gateway-options"
    ],
    "split_from": [
     "tmp:kb:prospect/C/payment-gateway-options"
    ],
    "moved_from": [],
    "reason": "儲值抵扣機制可獨立回答，與金流廠商比較主題不同。"
   },
   {
    "id": "prospect/E/credit-card-rent-payment",
    "coarse_id": "E",
    "title": "租客能不能用信用卡繳房租",
    "slug": "credit-card-rent-payment",
    "merge_of": [
     "tmp:kb:prospect/C/credit-card-rent-payment"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "信用卡繳租的前提與設定自身完整，主題與廠商比較不同，另見金流廠商細目。"
   },
   {
    "id": "prospect/E/overdue-reminder-late-fee",
    "coarse_id": "E",
    "title": "租客逾期未繳怎麼辦（含繳費提醒通知）",
    "slug": "overdue-reminder-late-fee",
    "merge_of": [
     "tmp:kb:prospect/C/overdue-reminder-late-fee",
     "tmp:kb:prospect/C/notification-channels"
    ],
    "split_from": [
     "tmp:kb:prospect/C/notification-channels"
    ],
    "moved_from": [],
    "reason": "繳費提醒時點與管道是逾期處理的一部分，通知歸它所通知的帳務領域，不自成細目。"
   },
   {
    "id": "prospect/E/owner-settlement-difference-invoice",
    "coarse_id": "E",
    "title": "代管月結差額發票",
    "slug": "owner-settlement-difference-invoice",
    "merge_of": [
     "tmp:kb:prospect/C/owner-report-collection-remit"
    ],
    "split_from": [
     "tmp:kb:prospect/C/owner-report-collection-remit"
    ],
    "moved_from": [],
    "reason": "月結差額發票群組的開立與重算可獨立回答，出現在帳務發票層面，歸帳務。"
   },
   {
    "id": "prospect/F/repair-system",
    "coarse_id": "F",
    "title": "線上報修與進度追蹤",
    "slug": "repair-system",
    "merge_of": [
     "tmp:kb:prospect/C/repair-system"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "修繕流程自身完整，歸修繕粗目。"
   },
   {
    "id": "prospect/G/smart-meter-lock-iot",
    "coarse_id": "G",
    "title": "智慧電錶與門鎖整合",
    "slug": "smart-meter-lock-iot",
    "merge_of": [
     "tmp:kb:prospect/C/smart-meter-lock-iot"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "電錶與兩型門鎖的整合說明互相依賴才完整，歸裝置粗目。"
   },
   {
    "id": "prospect/H/dashboard-overview",
    "coarse_id": "H",
    "title": "首頁儀表板顯示哪些數據",
    "slug": "dashboard-overview",
    "merge_of": [
     "tmp:kb:prospect/A/dashboard-overview"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "首頁畫面說明橫跨帳務與修繕，是系統使用導覽而非帳號主題，自身完整歸幫助中心。"
   },
   {
    "id": "prospect/I/product-overview",
    "coarse_id": "I",
    "title": "系統總覽、能解決什麼問題與適不適合我",
    "slug": "product-overview",
    "merge_of": [
     "tmp:kb:prospect/A/product-overview",
     "tmp:kb:prospect/A/pain-points"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "兩段都是引導了解需求的產品介紹開場，各自不完整且主題重疊，合併為一細目。"
   },
   {
    "id": "prospect/I/why-choose-jgb",
    "coarse_id": "I",
    "title": "為什麼選金箍棒",
    "slug": "why-choose-jgb",
    "merge_of": [
     "tmp:kb:prospect/A/why-choose-jgb"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "選擇理由自身完整，與總覽開場主題不同。"
   },
   {
    "id": "prospect/I/individual-landlord-scale-fit",
    "coarse_id": "I",
    "title": "個人房東（約 10～30 戶）適配與建議做法",
    "slug": "individual-landlord-scale-fit",
    "merge_of": [
     "tmp:kb:prospect/B/individual-landlord-scale-fit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "三個規模段的建議互相銜接才完整，屬導入適配主題。"
   },
   {
    "id": "prospect/I/team-company-fit",
    "coarse_id": "I",
    "title": "公司或包租代管團隊適合嗎",
    "slug": "team-company-fit",
    "merge_of": [
     "tmp:kb:prospect/B/team-company-fit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "團隊適配自身完整，與個人房東適配受眾規模不同。"
   },
   {
    "id": "prospect/I/data-migration",
    "coarse_id": "I",
    "title": "舊系統資料能否匯入（可匯入與不支援範圍）",
    "slug": "data-migration",
    "merge_of": [
     "tmp:kb:prospect/B/data-migration",
     "tmp:kb:prospect/G/migration-limits"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "不支援項目已包含於可匯入範圍說明中，兩段互相依賴才完整，合併為導入主題。"
   },
   {
    "id": "prospect/I/free-trial",
    "coarse_id": "I",
    "title": "可以免費試用嗎",
    "slug": "free-trial",
    "merge_of": [
     "tmp:kb:prospect/D/free-trial"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "免費試用自身完整，與收費與額度主題不同。"
   },
   {
    "id": "prospect/I/pricing-plans",
    "coarse_id": "I",
    "title": "怎麼收費",
    "slug": "pricing-plans",
    "merge_of": [
     "tmp:kb:prospect/D/pricing-plans"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "訂閱制與分級原則自身完整，歸方案粗目。"
   },
   {
    "id": "prospect/I/property-quota-limit",
    "coarse_id": "I",
    "title": "方案物件額度上限",
    "slug": "property-quota-limit",
    "merge_of": [
     "tmp:kb:prospect/D/property-quota-limit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "額度用滿的處理與免費方案額度自身完整，與收費主題不同。"
   },
   {
    "id": "prospect/I/subscription-change-renewal",
    "coarse_id": "I",
    "title": "升級、續約與取消訂閱",
    "slug": "subscription-change-renewal",
    "merge_of": [
     "tmp:kb:prospect/D/subscription-change-renewal"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "方案變更、自動續約與取消操作互相依賴才完整，屬方案主題。"
   },
   {
    "id": "prospect/I/competitor-comparison",
    "coarse_id": "I",
    "title": "跟 Bananas、屋我也差在哪",
    "slug": "competitor-comparison",
    "merge_of": [
     "tmp:kb:prospect/E/competitor-comparison"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "差異事實比較自身完整，與評論立場主題不同。"
   },
   {
    "id": "prospect/I/competitor-neutrality",
    "coarse_id": "I",
    "title": "會評論競爭對手嗎",
    "slug": "competitor-neutrality",
    "merge_of": [
     "tmp:kb:prospect/E/competitor-neutrality"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "中立立場說明自身完整，與具體比較內容各自成立。"
   }
  ],
  "id_map": [
   {
    "old": "tmp:kb:prospect/A/dashboard-overview",
    "new": "prospect/H/dashboard-overview",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/A/pain-points",
    "new": "prospect/I/product-overview",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/A/product-overview",
    "new": "prospect/I/product-overview",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/A/why-choose-jgb",
    "new": "prospect/I/why-choose-jgb",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/B/data-migration",
    "new": "prospect/I/data-migration",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/B/individual-landlord-scale-fit",
    "new": "prospect/I/individual-landlord-scale-fit",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/B/team-company-fit",
    "new": "prospect/I/team-company-fit",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/C/bill-contents-extra-fees",
    "new": "prospect/E/bill-contents-extra-fees",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/C/bill-format-customize",
    "new": "prospect/E/bill-format-customize",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/C/billing-overview",
    "new": "prospect/E/billing-overview",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/billing-overview",
    "new": "prospect/E/einvoice-auto-issue-carrier",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/community-batch-create",
    "new": "prospect/C/community-batch-create",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/contract-esign-flow",
    "new": "prospect/D/contract-creation-esign-flow",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/contract-esign-flow",
    "new": "prospect/D/contract-batch-renewal",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/contract-history-retention",
    "new": "prospect/D/contract-history-retention",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/C/contract-modify-after-sign",
    "new": "prospect/D/contract-modify-after-sign",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/C/contract-templates",
    "new": "prospect/D/contract-templates",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/contract-templates",
    "new": "prospect/D/entrust-contract-sublease-vs-management",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/credit-card-rent-payment",
    "new": "prospect/E/credit-card-rent-payment",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/C/notification-channels",
    "new": "prospect/E/overdue-reminder-late-fee",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/notification-channels",
    "new": "prospect/D/contract-creation-esign-flow",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/notification-channels",
    "new": "prospect/A/account-registration",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/overdue-reminder-late-fee",
    "new": "prospect/E/overdue-reminder-late-fee",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/C/owner-report-collection-remit",
    "new": "prospect/B/owner-report",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/owner-report-collection-remit",
    "new": "prospect/E/owner-settlement-difference-invoice",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/payment-gateway-options",
    "new": "prospect/E/payment-gateway-options",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/payment-gateway-options",
    "new": "prospect/E/virtual-account-prepaid-balance",
    "op": "split"
   },
   {
    "old": "tmp:kb:prospect/C/property-management-overview",
    "new": "prospect/C/property-management-overview",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/property-status-meaning",
    "new": "prospect/C/property-status-meaning",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/rental-storefront-vr",
    "new": "prospect/C/rental-storefront-vr",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/repair-system",
    "new": "prospect/F/repair-system",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/C/role-permission-granularity",
    "new": "prospect/B/role-permission-granularity",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/C/smart-meter-lock-iot",
    "new": "prospect/G/smart-meter-lock-iot",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/C/team-management-overview",
    "new": "prospect/B/team-management-overview",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/C/what-is-owner-landlord",
    "new": "prospect/B/what-is-owner-landlord",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/D/account-registration",
    "new": "prospect/A/account-registration",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/D/free-trial",
    "new": "prospect/I/free-trial",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/D/pricing-plans",
    "new": "prospect/I/pricing-plans",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/D/property-quota-limit",
    "new": "prospect/I/property-quota-limit",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/D/subscription-change-renewal",
    "new": "prospect/I/subscription-change-renewal",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/E/competitor-comparison",
    "new": "prospect/I/competitor-comparison",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/E/competitor-neutrality",
    "new": "prospect/I/competitor-neutrality",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/G/migration-limits",
    "new": "prospect/I/data-migration",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/G/utility-split-advice",
    "new": "prospect/E/bill-contents-extra-fees",
    "op": "merge"
   }
  ]
 },
 {
  "angle": "audience_level",
  "coarses": [
   {
    "id": "A",
    "title": "帳號與身分"
   },
   {
    "id": "B",
    "title": "團隊、人員與大房東"
   },
   {
    "id": "C",
    "title": "社區與物件"
   },
   {
    "id": "D",
    "title": "租約（含委託約子題）"
   },
   {
    "id": "E",
    "title": "帳務（含發票、收款金流、抄表）"
   },
   {
    "id": "F",
    "title": "修繕"
   },
   {
    "id": "G",
    "title": "裝置（IoT）"
   },
   {
    "id": "H",
    "title": "幫助中心"
   },
   {
    "id": "I",
    "title": "方案與導入"
   }
  ],
  "fines": [
   {
    "id": "prospect/A/account-registration",
    "coarse_id": "A",
    "title": "怎麼註冊帳號",
    "slug": "account-registration",
    "merge_of": [
     "tmp:kb:prospect/D/account-registration"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "潛在客戶對帳號主題只需操作層級（怎麼註冊、第三方登入、租客免註冊），歸帳號與身分。"
   },
   {
    "id": "prospect/B/team-management-and-permissions",
    "coarse_id": "B",
    "title": "團隊協作與成員權限能做到什麼",
    "slug": "team-management-and-permissions",
    "merge_of": [
     "tmp:kb:prospect/C/team-management-overview",
     "tmp:kb:prospect/C/role-permission-granularity"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "同一受眾對團隊管理主題只保留能力層級，模組總覽與權限細分同屬「多人分工能做到什麼」故合併為一細目。"
   },
   {
    "id": "prospect/B/owner-landlord-and-report",
    "coarse_id": "B",
    "title": "大房東是什麼與大房東報表",
    "slug": "owner-landlord-and-report",
    "merge_of": [
     "tmp:kb:prospect/C/what-is-owner-landlord",
     "tmp:kb:prospect/C/owner-report-collection-remit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "大房東定義與大房東報表對潛在客戶同屬能力層級的同一主題（如何對業主交代），合併歸人員與大房東；月結差額發票屬報表產出的一環，不另立帳務細目。"
   },
   {
    "id": "prospect/C/property-management-overview",
    "coarse_id": "C",
    "title": "房源管理模組做什麼",
    "slug": "property-management-overview",
    "merge_of": [
     "tmp:kb:prospect/C/property-management-overview"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "物件集中管理與狀態標籤屬物件本身的能力層級說明，歸社區與物件。"
   },
   {
    "id": "prospect/C/community-batch-create",
    "coarse_id": "C",
    "title": "社區建立與批次新增物件",
    "slug": "community-batch-create",
    "merge_of": [
     "tmp:kb:prospect/C/community-batch-create"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "社區歸戶與批次建檔是獨立主題，潛在客戶只需操作層級（先建社區、下載模板上傳），另見房源管理總覽。"
   },
   {
    "id": "prospect/C/property-status-meaning",
    "coarse_id": "C",
    "title": "物件狀態是什麼意思",
    "slug": "property-status-meaning",
    "merge_of": [
     "tmp:kb:prospect/C/property-status-meaning"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "物件總表的四種狀態與刊登軸是物件本身屬性的能力層級解讀，歸社區與物件；合約驅動的狀態演變另見租約細目而不重複。"
   },
   {
    "id": "prospect/C/rental-storefront-vr",
    "coarse_id": "C",
    "title": "招租店舖與 VR 看屋",
    "slug": "rental-storefront-vr",
    "merge_of": [
     "tmp:kb:prospect/C/rental-storefront-vr"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "對外招租頁與 VR 連結是物件曝光的能力層級主題，歸社區與物件。"
   },
   {
    "id": "prospect/D/contract-esign-flow",
    "coarse_id": "D",
    "title": "建約方式與線上電子簽約流程",
    "slug": "contract-esign-flow",
    "merge_of": [
     "tmp:kb:prospect/C/contract-esign-flow"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "建約到簽署的流程、時效、身分與社宅例外對潛在客戶保留操作層級一個細目，歸租約。"
   },
   {
    "id": "prospect/D/contract-templates",
    "coarse_id": "D",
    "title": "合約範本有哪些可以選",
    "slug": "contract-templates",
    "merge_of": [
     "tmp:kb:prospect/C/contract-templates"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "可選範本種類與個人／法人差異是租約主題的權益層級（可用範圍），與流程細目分層並另見。"
   },
   {
    "id": "prospect/D/contract-modify-after-sign",
    "coarse_id": "D",
    "title": "合約送出或簽完後能不能修改",
    "slug": "contract-modify-after-sign",
    "merge_of": [
     "tmp:kb:prospect/C/contract-modify-after-sign"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "簽後修改規則由合約狀態決定，屬租約主題的操作層級獨立問題。"
   },
   {
    "id": "prospect/D/contract-history-retention",
    "coarse_id": "D",
    "title": "歷史合約保留多久",
    "slug": "contract-history-retention",
    "merge_of": [
     "tmp:kb:prospect/C/contract-history-retention"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "歷史合約保存期限與點退狀態是租約主題的權益層級（保留權益），歸租約。"
   },
   {
    "id": "prospect/E/billing-overview",
    "coarse_id": "E",
    "title": "帳務管理模組做什麼（含電子發票）",
    "slug": "billing-overview",
    "merge_of": [
     "tmp:kb:prospect/C/billing-overview"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "自動帳單、代收、電子發票自動開立與載具屬帳務主題的能力層級總覽，歸帳務。"
   },
   {
    "id": "prospect/E/bill-contents-extra-fees",
    "coarse_id": "E",
    "title": "帳單內容與臨時加收費用",
    "slug": "bill-contents-extra-fees",
    "merge_of": [
     "tmp:kb:prospect/C/bill-contents-extra-fees"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "出現在帳單列上的內容與臨時加收屬帳務，潛在客戶保留操作層級。"
   },
   {
    "id": "prospect/E/bill-format-customize",
    "coarse_id": "E",
    "title": "帳單版面能不能自訂",
    "slug": "bill-format-customize",
    "merge_of": [
     "tmp:kb:prospect/C/bill-format-customize"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "帳單版面可調範圍與收據版式是帳務主題中「能力邊界」的獨立問題，與帳單內容細目分開並另見。"
   },
   {
    "id": "prospect/E/payment-gateway-options",
    "coarse_id": "E",
    "title": "金流廠商差別、申請條件與信用卡繳租",
    "slug": "payment-gateway-options",
    "merge_of": [
     "tmp:kb:prospect/C/payment-gateway-options",
     "tmp:kb:prospect/C/credit-card-rent-payment"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "錢怎麼進來歸收款金流子題；信用卡繳租是金流廠商選擇的一個結果（僅藍新支援），同層級同主題故合併，不重複。"
   },
   {
    "id": "prospect/E/overdue-reminder-late-fee",
    "coarse_id": "E",
    "title": "租客逾期未繳怎麼辦（含繳費提醒通知）",
    "slug": "overdue-reminder-late-fee",
    "merge_of": [
     "tmp:kb:prospect/C/overdue-reminder-late-fee",
     "tmp:kb:prospect/C/notification-channels"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "通知是投遞管道不自成細目，繳費提醒的管道與時機併入其所通知的逾期催繳主題（帳務能力層級）；簽約邀請與驗證碼通知另見租約與帳號細目。"
   },
   {
    "id": "prospect/E/utility-split-advice",
    "coarse_id": "E",
    "title": "水電費怎麼分算",
    "slug": "utility-split-advice",
    "merge_of": [
     "tmp:kb:prospect/G/utility-split-advice"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "錢怎麼算歸帳務；水電分算依合約條件計入帳單，屬帳務能力層級而非裝置。"
   },
   {
    "id": "prospect/F/repair-system",
    "coarse_id": "F",
    "title": "線上報修與進度追蹤",
    "slug": "repair-system",
    "merge_of": [
     "tmp:kb:prospect/C/repair-system"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "報修流程數位化屬修繕主題的能力層級，歸修繕。"
   },
   {
    "id": "prospect/G/smart-meter-lock-iot",
    "coarse_id": "G",
    "title": "智慧電錶與門鎖整合",
    "slug": "smart-meter-lock-iot",
    "merge_of": [
     "tmp:kb:prospect/C/smart-meter-lock-iot"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "電錶與門鎖是硬體裝置的能力層級說明，歸裝置（IoT）；抄表帶入帳單另見帳務。"
   },
   {
    "id": "prospect/I/product-overview",
    "coarse_id": "I",
    "title": "系統總覽、能解決什麼問題與適不適合我",
    "slug": "product-overview",
    "merge_of": [
     "tmp:kb:prospect/A/product-overview",
     "tmp:kb:prospect/A/pain-points"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "總覽與痛點對應同為潛在客戶導入評估的能力層級入口問題，同主題合併為一細目，歸方案與導入。"
   },
   {
    "id": "prospect/I/dashboard-overview",
    "coarse_id": "I",
    "title": "首頁儀表板顯示哪些數據",
    "slug": "dashboard-overview",
    "merge_of": [
     "tmp:kb:prospect/A/dashboard-overview"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "儀表板橫跨收支、帳務、修繕三模組，屬產品導入時的整體能力層級展示，不歸單一業務領域。"
   },
   {
    "id": "prospect/I/why-choose-jgb",
    "coarse_id": "I",
    "title": "為什麼選金箍棒與同類系統的差異",
    "slug": "why-choose-jgb",
    "merge_of": [
     "tmp:kb:prospect/A/why-choose-jgb",
     "tmp:kb:prospect/E/competitor-comparison"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "選擇理由與競品差異講的是同一組差異化能力（合約廣度、金流、IoT、大房東報表），講法唯一故合併為導入評估的能力層級細目。"
   },
   {
    "id": "prospect/I/competitor-neutrality",
    "coarse_id": "I",
    "title": "會評論競爭對手嗎",
    "slug": "competitor-neutrality",
    "merge_of": [
     "tmp:kb:prospect/E/competitor-neutrality"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "對同業的中立回答原則是導入諮詢時的獨立主題，與差異比較細目分開並另見。"
   },
   {
    "id": "prospect/I/individual-landlord-scale-fit",
    "coarse_id": "I",
    "title": "個人房東（約 10～30 戶）適配與建議做法",
    "slug": "individual-landlord-scale-fit",
    "merge_of": [
     "tmp:kb:prospect/B/individual-landlord-scale-fit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "依規模判斷適不適合是導入評估的能力層級，屬方案與導入而非團隊管理。"
   },
   {
    "id": "prospect/I/team-company-fit",
    "coarse_id": "I",
    "title": "公司或包租代管團隊適合嗎",
    "slug": "team-company-fit",
    "merge_of": [
     "tmp:kb:prospect/B/team-company-fit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "團隊型客戶的適配評估屬導入層級問題，歸方案與導入；團隊權限與大房東報表細節另見 B。"
   },
   {
    "id": "prospect/I/free-trial",
    "coarse_id": "I",
    "title": "可以免費試用嗎",
    "slug": "free-trial",
    "merge_of": [
     "tmp:kb:prospect/D/free-trial"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "免費試用是方案主題的權益層級，免費試用一個月的講法只掛此細目，其他細目以另見引用。"
   },
   {
    "id": "prospect/I/pricing-plans",
    "coarse_id": "I",
    "title": "怎麼收費",
    "slug": "pricing-plans",
    "merge_of": [
     "tmp:kb:prospect/D/pricing-plans"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "訂閱制與分級方式是方案主題的權益層級（費用），歸方案與導入。"
   },
   {
    "id": "prospect/I/property-quota-limit",
    "coarse_id": "I",
    "title": "方案物件額度上限",
    "slug": "property-quota-limit",
    "merge_of": [
     "tmp:kb:prospect/D/property-quota-limit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "物件額度是方案權益層級的獨立問題（額度滿了怎麼辦），與收費細目分開並另見。"
   },
   {
    "id": "prospect/I/subscription-change-renewal",
    "coarse_id": "I",
    "title": "升級、續約與取消訂閱",
    "slug": "subscription-change-renewal",
    "merge_of": [
     "tmp:kb:prospect/D/subscription-change-renewal"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "方案變更與續約扣款屬方案主題的操作層級，與權益層級的收費、額度細目分層。"
   },
   {
    "id": "prospect/I/data-migration",
    "coarse_id": "I",
    "title": "舊系統資料能否匯入（可匯入範圍與不支援項目）",
    "slug": "data-migration",
    "merge_of": [
     "tmp:kb:prospect/B/data-migration",
     "tmp:kb:prospect/G/migration-limits"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "可匯入範圍與不支援項目是同一導入主題的能力層級正反兩面，講法重複故合併，歸方案與導入。"
   }
  ],
  "id_map": [
   {
    "old": "tmp:kb:prospect/A/dashboard-overview",
    "new": "prospect/I/dashboard-overview",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/A/pain-points",
    "new": "prospect/I/product-overview",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/A/product-overview",
    "new": "prospect/I/product-overview",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/A/why-choose-jgb",
    "new": "prospect/I/why-choose-jgb",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/B/data-migration",
    "new": "prospect/I/data-migration",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/B/individual-landlord-scale-fit",
    "new": "prospect/I/individual-landlord-scale-fit",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/B/team-company-fit",
    "new": "prospect/I/team-company-fit",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/C/bill-contents-extra-fees",
    "new": "prospect/E/bill-contents-extra-fees",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/C/bill-format-customize",
    "new": "prospect/E/bill-format-customize",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/C/billing-overview",
    "new": "prospect/E/billing-overview",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/C/community-batch-create",
    "new": "prospect/C/community-batch-create",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/contract-esign-flow",
    "new": "prospect/D/contract-esign-flow",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/C/contract-history-retention",
    "new": "prospect/D/contract-history-retention",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/C/contract-modify-after-sign",
    "new": "prospect/D/contract-modify-after-sign",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/C/contract-templates",
    "new": "prospect/D/contract-templates",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/C/credit-card-rent-payment",
    "new": "prospect/E/payment-gateway-options",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/C/notification-channels",
    "new": "prospect/E/overdue-reminder-late-fee",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/C/overdue-reminder-late-fee",
    "new": "prospect/E/overdue-reminder-late-fee",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/C/owner-report-collection-remit",
    "new": "prospect/B/owner-landlord-and-report",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/C/payment-gateway-options",
    "new": "prospect/E/payment-gateway-options",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/C/property-management-overview",
    "new": "prospect/C/property-management-overview",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/property-status-meaning",
    "new": "prospect/C/property-status-meaning",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/rental-storefront-vr",
    "new": "prospect/C/rental-storefront-vr",
    "op": "keep"
   },
   {
    "old": "tmp:kb:prospect/C/repair-system",
    "new": "prospect/F/repair-system",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/C/role-permission-granularity",
    "new": "prospect/B/team-management-and-permissions",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/C/smart-meter-lock-iot",
    "new": "prospect/G/smart-meter-lock-iot",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/C/team-management-overview",
    "new": "prospect/B/team-management-and-permissions",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/C/what-is-owner-landlord",
    "new": "prospect/B/owner-landlord-and-report",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/D/account-registration",
    "new": "prospect/A/account-registration",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/D/free-trial",
    "new": "prospect/I/free-trial",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/D/pricing-plans",
    "new": "prospect/I/pricing-plans",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/D/property-quota-limit",
    "new": "prospect/I/property-quota-limit",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/D/subscription-change-renewal",
    "new": "prospect/I/subscription-change-renewal",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/E/competitor-comparison",
    "new": "prospect/I/why-choose-jgb",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/E/competitor-neutrality",
    "new": "prospect/I/competitor-neutrality",
    "op": "move"
   },
   {
    "old": "tmp:kb:prospect/G/migration-limits",
    "new": "prospect/I/data-migration",
    "op": "merge"
   },
   {
    "old": "tmp:kb:prospect/G/utility-split-advice",
    "new": "prospect/E/utility-split-advice",
    "op": "move"
   }
  ]
 }
]

請輸出合成提議（angle 欄填 synthesis）。