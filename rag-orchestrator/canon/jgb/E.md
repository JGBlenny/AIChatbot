---
coarse: E
title: 帳務（含發票、收款金流、抄表）
scope: 帳單產生與週期、催繳、滯納金、收款方式與金流商、發票、抄表與水電費；⛔ 修繕流程歸 F
version: 2026-09-21.0
reviewers: [owner]
language: zh-TW
---
## 帳單列表與帳單狀態 {#E-bill-list}
### 帳單列表分成哪些分頁？（帳單總表／草稿帳單／收款帳單／支出帳單／總收支） {#jgb/E/bill-list-tabs}
- phrasings:
  - {text: "帳單分頁", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單列表怎麼分類", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單總表跟草稿帳單差在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單有哪些分頁", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js, code:src/pages/bills/list/Index.jsx]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
房東登入後的帳單列表分成「帳單總表」「草稿帳單」「收款帳單」「支出帳單」「總收支」共 5 個分頁，可以切換查看。
「帳單總表」不分狀態，會列出全部帳單；其餘四個分頁底下再各自分幾個狀態頁籤。
「草稿帳單」「收款帳單」「支出帳單」這三個分頁上方另外有月份切換列，可以切換月份查看不同月份的帳單。
### 「草稿帳單」「收款帳單」「支出帳單」分頁底下各分哪些狀態？ {#jgb/E/bill-status-tabs-landlord}
- phrasings:
  - {text: "帳單狀態有哪些", source: "draft:outline-20260920", status: proposed}
  - {text: "草稿排定發送封存差在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "應到帳待對帳已到帳", source: "draft:outline-20260920", status: proposed}
  - {text: "應支出已支出已失效", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「草稿帳單」分頁底下分「草稿」「排定發送」「封存」三個狀態。
「收款帳單」分頁底下分「應到帳」「待對帳」「已到帳」三個狀態。
「支出帳單」分頁底下分「應支出」「已支出」「已失效」三個狀態。
### 租客的帳單列表跟房東的有什麼不同？（只有收款帳單／支出帳單兩個分頁） {#jgb/E/bill-status-tabs-tenant}
- phrasings:
  - {text: "租客帳單列表", source: "draft:outline-20260920", status: proposed}
  - {text: "租客看得到草稿帳單嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "租客帳單分頁", source: "draft:outline-20260920", status: proposed}
  - {text: "租客帳單狀態", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
租客登入後的帳單列表只有「收款帳單」與「支出帳單」兩個分頁，房東才有的「帳單總表」「草稿帳單」「總收支」租客端沒有。
租客「收款帳單」分頁底下分「應到帳」「已到帳」兩個狀態。
租客「支出帳單」分頁底下分「應支出」「待對帳」「已支出」「已失效」四個狀態。
### 「草稿」狀態的帳單可以做哪些動作？（編輯／發送／移至已到帳／封存） {#jgb/E/bill-actions-draft}
- phrasings:
  - {text: "草稿帳單能做什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "草稿帳單怎麼發送", source: "draft:outline-20260920", status: proposed}
  - {text: "草稿帳單齒輪選單", source: "draft:outline-20260920", status: proposed}
  - {text: "合併帳單", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
草稿帳單可以「編輯帳單」修改內容。
草稿帳單可以「發送帳單」，送出後轉為應到帳狀態通知對象繳費。
草稿帳單也可以直接「移至已到帳」，略過發送、直接視為已收款；但部分特定合作團隊的帳單選單沒有「移至已到帳」。
草稿帳單可以「封存帳單」。
「合併帳單」動作目前只提供給特定合作團隊使用。
在「草稿帳單」分頁勾選一筆以上帳單後，批次操作列會多出「批次預覽編輯」，可以把勾選的帳單（或用全選連同篩選條件一起送出）一次性帶入批次編輯的預覽視窗調整費用內容。
### 「排定發送」狀態的帳單可以做哪些動作？（只有「取消排定發送」） {#jgb/E/bill-actions-scheduled}
- phrasings:
  - {text: "排定發送可以取消嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "取消排定發送", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「排定發送」狀態的帳單，齒輪選單只有一個「取消排定發送」的動作。
### 「封存」狀態的帳單可以做哪些動作？（沒有任何動作，齒輪選單是空的） {#jgb/E/bill-actions-archived}
- phrasings:
  - {text: "封存的帳單能做什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "封存後還能操作嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「封存」狀態的帳單，齒輪選單目前沒有任何可以選的動作，選單會是空的。
### 「應到帳」狀態的收款帳單可以做哪些動作？（匯款資訊／移至已到帳／開立發票／取消帳單） {#jgb/E/bill-actions-unreceived}
- phrasings:
  - {text: "應到帳可以做什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "匯款資訊在哪看", source: "draft:outline-20260920", status: proposed}
  - {text: "應到帳可以取消嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
應到帳的收款帳單，如果不是走自動收款，齒輪選單會顯示「匯款資訊」讓房東查看匯款帳戶。
應到帳的收款帳單可以「移至已到帳」或「取消帳單」（部分特定合作團隊的選單沒有「移至已到帳」）；「開立發票」則要這張帳單所屬合約有設定自動開立發票、帳單本身也設定自動開立發票、且發票狀態還沒到「已完成」時才會出現，不是每一張應到帳帳單都看得到。
### 「待對帳」狀態的收款帳單可以做哪些動作？（單張可退至應到帳、移至已到帳、開立發票，沒有取消帳單；批次沒有退至應到帳） {#jgb/E/bill-actions-progress}
- phrasings:
  - {text: "待對帳可以做什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "退至應到帳", source: "draft:outline-20260920", status: proposed}
  - {text: "待對帳能取消嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js, code:app/Http/Controllers/UserController.php, code:src/use/config/useFeatures.js]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
房東方在「待對帳」收款帳單的齒輪選單裡，可以選「退至應到帳」「移至已到帳」，條件符合時還有「開立發票」；選單裡沒有「取消帳單」。
「退至應到帳」「移至已到帳」需要有帳單的新增或編輯權限（「新增&編輯&刪除所屬帳單」或「新增&編輯&刪除所有帳單」）才會出現，沒有這個權限的成員看不到；另外特定合作團隊的選單沒有「移至已到帳」。
「開立發票」只有在這張帳單所屬合約設定自動開立發票、帳單本身也設定自動開立發票、而且發票還沒開立完成時才會出現，不是每一張待對帳帳單都有。
在帳單總表或收款帳單分頁勾選多筆「待對帳」帳單時，批次操作列可能出現的動作是「移至已到帳」「開立發票」，以及有匯出權限時的匯出（收款帳單分頁叫「匯出」，帳單總表叫「匯出帳單」）；批次操作列沒有「退至應到帳」。
批次的「移至已到帳」同樣要有帳單的新增或編輯權限，特定合作團隊也沒有這個選項；批次的「開立發票」必須同時符合：團隊開通手動開立發票功能、勾選的每一張帳單都設定自動開立發票（合約與帳單）、而且都還沒開立過發票。
### 「已到帳」狀態的收款帳單可以做哪些動作？（收款備註／發票／收據／退款對帳單） {#jgb/E/bill-actions-received}
- phrasings:
  - {text: "已到帳能做什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "重開發票", source: "draft:outline-20260920", status: proposed}
  - {text: "作廢發票", source: "draft:outline-20260920", status: proposed}
  - {text: "收款備註怎麼改", source: "draft:outline-20260920", status: proposed}
  - {text: "退款對帳單", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js, code:app/Notification.php, code:app/Http/Controllers/UserController.php, code:config/role.php]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
這是房東方帳號在「已到帳」收款帳單齒輪選單看到的內容；其中「編輯收款備註」「重開發票」「作廢發票」「封存帳單」要有「新增&編輯&刪除所屬帳單」或「新增&編輯&刪除所有帳單」權限才會顯示。
已到帳的收款帳單可以「編輯收款備註」。
已到帳的收款帳單，如果所屬合約有設定自動開立發票、且已經產生發票，齒輪選單裡會列出對應的「發票」按鈕（一張以上會依張數編號），已經作廢的那張後面會加註「（已作廢）」；ezPay 開立的發票點下去會打開該張發票的連結，eCloud 開立的則是打開 eCloud 的登入頁面。
已到帳的收款帳單一律可以看到「收據」；部分特定合作團隊點「收據」下載的是押金收據。
只有這張帳單本身是反轉帳單（房東退款給租客）時，齒輪選單才會多出「退款對帳單」。
已到帳的收款帳單只要本身有設定自動開立發票，就會常駐顯示「重開發票」，不論目前發票狀態為何。
只有在這張帳單有已開立且未作廢的發票時，齒輪選單才會出現「作廢發票」。
已到帳的收款帳單可以「封存帳單」。
帳單轉為已付款（不論是線上付款、或業者手動移至已到帳）時，如果收款方是個人房東或法人房東，系統會自動寄一封通知信給租客，一般會附收據 PDF（部分特定合作團隊的通知信不附收據）；收款方是社會住宅時，系統不會寄這封通知信；畫面上目前沒有「重寄收據」的按鈕可以手動再發一次。
押金設算息帳單轉為已到帳時，不會另外通知租客。
### 「應支出」狀態的支出帳單，房東跟租客各能做什麼？（房東：前往付款／通知已匯款／取消帳單；租客：付款） {#jgb/E/bill-actions-expense-unpaid}
- phrasings:
  - {text: "應支出可以做什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "租客怎麼付款", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
應支出的支出帳單，房東端可以「前往付款」「通知已匯款」或「取消帳單」；租客端則只看到「付款」。
### 「待對帳」狀態的支出帳單，房東跟租客各能做什麼？（房東：前往付款／通知已匯款／取消帳單；租客：沒有齒輪動作） {#jgb/E/bill-actions-expense-unconfirmed}
- phrasings:
  - {text: "待對帳支出帳單", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
待對帳的支出帳單，房東端一樣有「前往付款」「通知已匯款」「取消帳單」；這個狀態租客端沒有齒輪動作。
### 「已支出」狀態的支出帳單，房東跟租客各能做什麼？（房東一律有編輯收款備註／封存；反轉帳單才多出收據／退款對帳單） {#jgb/E/bill-actions-expense-paid}
- phrasings:
  - {text: "已支出的收據", source: "draft:outline-20260920", status: proposed}
  - {text: "退款對帳單怎麼看", source: "draft:outline-20260920", status: proposed}
  - {text: "已支出可以封存嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
已支出的支出帳單，房東端一律可以「編輯收款備註」跟「封存帳單」；只有這張帳單本身是反轉帳單（房東退款給租客）時，才會多出「收據」或「退款對帳單」。
已支出的支出帳單，租客端一律看得到「收據」；只有對租客端來說是反轉帳單時，才會多出「退款對帳單」；如果這張帳單所屬合約有設定自動開立發票且已經產生發票，齒輪選單裡還會列出對應的「發票」按鈕（一張以上依張數編號），已經作廢的那張後面會加註「（已作廢）」。
### 帳單狀態顯示「已失效」是什麼意思？（限電錶儲值帳單，4 天繳費期限） {#jgb/E/bill-expired-status}
- phrasings:
  - {text: "已失效是什麼意思", source: "draft:outline-20260920", status: proposed}
  - {text: "儲值帳單過期", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單已失效要補繳嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "電錶儲值帳單失效", source: "draft:outline-20260920", status: proposed}
- sources: [help:billexpired_zh-Hant.html]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
帳單列表看到「已失效」，一定是一張電錶費儲值帳單，一般的租金、押金、點退帳單不會出現這個狀態。
儲值帳單是按下【儲值】的當下由系統即時產生，帳單上的發送者會顯示「JGB系統」，跟需要房東主動編輯發送的租金帳單不同。
儲值帳單從建立當天起算共有 4 天的繳費期限，若逾期未繳，系統會在隔天凌晨自動將它標記為已失效。
已失效的帳單不需要補繳，因為代表這筆款項從頭到尾都沒有支付，該筆帳單即作廢，也不會累積成欠款。
### 帳單列表怎麼用關鍵字搜尋？（可指定用案名／地址／租客／ID／手機／信箱／帳單名稱／虛擬帳號／合約帳單共 9 種比對） {#jgb/E/bill-list-keyword-search}
- phrasings:
  - {text: "帳單怎麼搜尋", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單關鍵字搜尋", source: "draft:outline-20260920", status: proposed}
  - {text: "用虛擬帳號查帳單", source: "draft:outline-20260920", status: proposed}
  - {text: "用租客名字找帳單", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/list/Index.jsx]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
帳單列表的關鍵字搜尋可以指定用「案名」「地址」「租客」「ID」「手機」「信箱」「帳單名稱」「虛擬帳號」或「合約帳單」共 9 種其中一種去比對。
關鍵字搜尋框旁邊有下拉選單，可以先選要用哪一種條件（例如案名、租客、虛擬帳號）去比對，再輸入關鍵字查詢。
預設是用「案名」去比對輸入的關鍵字。
### 帳單總表怎麼匯出？（要先勾選帳單才會出現匯出選項） {#jgb/E/bill-list-export}
- phrasings:
  - {text: "帳單怎麼匯出", source: "draft:outline-20260920", status: proposed}
  - {text: "匯出帳單上限", source: "draft:outline-20260920", status: proposed}
  - {text: "匯出帳單要先勾選嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "全選匯出跟勾選匯出差在哪", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js, code:src/pages/bills/list/Index.jsx, code:src/pages/bills/_parts/ListTable.jsx, code:src/components/SurelyVue/Common/PickAllFooter.vue]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
帳單總表沒有一個隨時可以按的「匯出帳單」按鈕，只有在左側核取方塊勾選帳單之後，上方才會跳出批次動作列，裡面才有「匯出帳單」這個選項。
匯出筆數超過系統上限時會直接擋下，並提示匯出筆數超過上限、請縮小搜尋範圍後再試，不會只匯出部分結果。
帳單總表的批次操作列要有匯出帳單的權限才會出現「匯出帳單」選項；「草稿帳單」「收款帳單」分頁勾選帳單後，批次操作列也會出現同樣勾選/全選邏輯的「匯出」選項，跟帳單總表共用同一套規則。
### 帳單總表勾選多筆不同狀態的帳單時，批次操作列會出現哪些動作？（只列出每一筆帳單都能做的共同動作） {#jgb/E/bill-list-bulk-action-intersection}
- phrasings:
  - {text: "勾選不同狀態的帳單能做什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單總表批次操作交集", source: "draft:outline-20260920", status: proposed}
  - {text: "混合狀態帳單批次動作", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在帳單總表勾選多筆帳單時，系統會先分別算出每一張帳單各自可以做的動作，再取這些動作的交集，批次操作列只會列出「每一筆都可以做」的共同動作。
如果勾選的帳單裡有一筆已經沒有任何跟其他筆重疊的動作，交集就會變成空集合，批次操作列除了固定附加的「匯出帳單」以外不會有其他動作。
### 「草稿帳單」「支出帳單」「總收支」分頁的匯出按鈕，跟帳單總表不是同一套（不需要先勾選，走另一個較舊的匯出流程） {#jgb/E/bill-list-export-other-tabs}
- phrasings:
  - {text: "支出帳單怎麼匯出", source: "draft:outline-20260920", status: proposed}
  - {text: "總收支怎麼匯出", source: "draft:outline-20260920", status: proposed}
  - {text: "草稿帳單怎麼匯出", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js, code:app/Http/Controllers/UserController.php]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「草稿帳單」跟「支出帳單」「總收支」分頁右上角，有「匯出帳務資料」權限的帳號會看到一個固定的「匯出」／「匯出帳單」按鈕，不需要先勾選任何一筆，按下去會另外開一個（較舊的）匯出視窗，跟帳單總表用勾選觸發的匯出是不同的流程。
「排定發送」「封存」「已失效」分頁則沒有這個匯出按鈕。
### 「收款帳單」分頁固定的匯出按鈕，什麼時候會多出「匯出租客繳費證明」子選項？（只有身分類別為社會住宅的帳號才有） {#jgb/E/bill-list-income-export-social-housing}
- phrasings:
  - {text: "收款帳單怎麼匯出", source: "draft:outline-20260920", status: proposed}
  - {text: "匯出租客繳費證明", source: "draft:outline-20260920", status: proposed}
  - {text: "社會住宅匯出證明", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js, code:app/Role.php, code:app/Http/Controllers/UserController.php]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
只有身分類別是「社會住宅」的帳號，這顆固定匯出按鈕才會多一個子選項「匯出租客繳費證明」；其他身分類別的帳號沒有這個子選項。
### 「應到帳」「已到帳」狀態，特定合作團隊的帳號會多出哪些按鈕？（應到帳：匯入發票；已到帳：匯出收據／匯入收據／批次匯出收據） {#jgb/E/bill-list-special-team-cvs-buttons}
- phrasings:
  - {text: "匯入發票在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "匯出收據", source: "draft:outline-20260920", status: proposed}
  - {text: "批次匯出收據", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「收款帳單」分頁的「應到帳」狀態，特定合作團隊的帳號會多出一個「匯入發票」按鈕。
「收款帳單」分頁的「已到帳」狀態，另外兩個特定合作團隊的帳號會多出「匯出收據」「匯入收據」「批次匯出收據」三個按鈕。
### 「總收支」分頁的匯出按鈕，特定合作團隊的帳號會多出什麼子選項？（匯出收支明細表） {#jgb/E/bill-balance-tab-export-submenu}
- phrasings:
  - {text: "匯出收支明細表", source: "draft:outline-20260920", status: proposed}
  - {text: "總收支匯出子選項", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「總收支」分頁的匯出按鈕，屬於「差額發票」特定合作團隊的帳號會多一個子選項「匯出收支明細表」。
### 「草稿帳單」分頁右上角有哪些批次建立帳單的快捷按鈕？（新增週期帳單／新增批次帳單／排定發送帳單／批次編輯帳單，Excel新增帳單僅限特定合作團隊；帳單總表沒有這些按鈕） {#jgb/E/bill-list-batch-shortcuts}
- phrasings:
  - {text: "批次建立帳單", source: "draft:outline-20260920", status: proposed}
  - {text: "一次建立多張帳單", source: "draft:outline-20260920", status: proposed}
  - {text: "Excel新增帳單", source: "draft:outline-20260920", status: proposed}
  - {text: "批次編輯帳單", source: "draft:outline-20260920", status: proposed}
  - {text: "批次編輯帳單特定團隊視窗不一樣", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
一般帳號在「草稿帳單」分頁右上角「新增帳單」按鈕旁邊，預設會有「新增週期帳單」「新增批次帳單」「排定發送帳單」「批次編輯帳單」四個快捷選項可以選；「帳單總表」分頁沒有「新增帳單」按鈕，也沒有這些快捷選項。
「新增批次帳單」會先讓房東挑選多位租客（合約），再一次建立多張帳單。
「新增週期帳單」會先讓房東挑選多個物件，用來建立會依週期重複產生的帳單。
「批次編輯帳單」預設會開啟匯入試算表的視窗，讓房東批次調整帳單內容；但對某些特定合作團隊的帳號會改開另一個專用視窗（可篩選範圍、整批品項金額一起編輯）。
另一組特定合作團隊的帳號，右上角的快捷選項只會顯示「新增批次帳單」一項；還有一組特定合作團隊的帳號，快捷選項會多一個「Excel新增帳單」，可以用 Excel 檔案批次新增帳單。
### 「排定發送帳單」有什麼限制？（一般要度數填完才能排，點退帳單與綁定智慧電錶的電費例外；每天中午 12 點統一發送） {#jgb/E/bill-scheduled-send-rule}
- phrasings:
  - {text: "排定發送帳單怎麼用", source: "draft:outline-20260920", status: proposed}
  - {text: "排定發送限制", source: "draft:outline-20260920", status: proposed}
  - {text: "水電度數沒填能排定發送嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單幾點統一發送", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/pick/Index.jsx, code:app/Bill.php, code:app/Http/Controllers/BillController.php, code:app/Console/Commands/BillBatchSend.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
排定發送帳單要先在挑選頁面選好要排定的帳單。
只有已經填寫完，或本來就沒有水電、瓦斯度數細節要填的帳單，才能排入排定發送。
例外有兩種：點退帳單不需要先填完度數也能排入；另外，如果帳單唯一還沒填的是電費，而且物件有綁定智慧電錶、讀得到讀數，這張帳單也能排入，電費度數會在排入時和中午發送時自動補上，發送時如果還是補不到度數或讀數是 0 度，這張帳單會被跳過、不會送出。
系統會在每天中午 12:00 把選取的帳單統一發送給租客。
「租客免註冊合約」下的帳單不適用排定發送這個功能。
### 帳單通知信裡的連結點進去會看到什麼？（帳單列表只先列出通知裡的那幾張帳單，自己改篩選後回到一般列表） {#jgb/E/bill-single-notification-deeplink}
- phrasings:
  - {text: "帳單連結點進去", source: "draft:outline-20260920", status: proposed}
  - {text: "通知信帳單連結", source: "draft:outline-20260920", status: proposed}
  - {text: "通知連結只列出那張帳單", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/BillController.php, code:src/pages/bills/list/Index.jsx, code:src/use/config/billListSearch.js]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
帳單通知信或系統通知裡帶的帳單連結，點進去是帳單列表頁，但清單只會先列出通知裡的那幾張帳單。
之後只要自己改了篩選條件（例如切換分頁、換月份或重新送出搜尋），這個只看通知帳單的限制就會被拿掉，回到一般的列表篩選。
### 「總收支」分頁的用途是什麼？（「全部」混列已到帳與已支出的帳單，另有已到帳、已支出、應到帳、應支出各自的頁籤） {#jgb/E/bill-balance-tab}
- phrasings:
  - {text: "總收支分頁", source: "draft:outline-20260920", status: proposed}
  - {text: "收支總覽在哪看", source: "draft:outline-20260920", status: proposed}
  - {text: "總收支跟帳單總表差在哪", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「總收支」分頁底下分「全部」「已到帳」「已支出」「應到帳」「應支出」，可以在同一個分頁看收款帳單跟支出帳單；其中「全部」只混列已到帳與已支出的帳單，應到帳、應支出的帳單要到各自的頁籤看。
「總收支」分頁跟「帳單總表」不同：總收支只列收款/支出這幾個狀態的帳單，帳單總表是列出全部帳單不分狀態。
「總收支」分頁裡「已到帳」「已支出」「應到帳」「應支出」這四個狀態頁籤都有本頁小計功能，因為金額欄顯示的是「這張帳單在本分頁那一邊的金額」，所以才需要本頁小計，跟上方彙總卡片的數字對得起來；「全部」頁籤本身沒有這個小計。
### 帳單通知走哪些管道？通知對象是誰？（免註冊租客可分別開關 Email／簡訊，已註冊租客固定收 Email 與站內通知、已綁定 LINE／FB 另收推播；只發給帳單本身的那位承租人） {#jgb/E/bill-notify-channels}
- phrasings:
  - {text: "帳單通知怎麼關", source: "draft:outline-20260920", status: proposed}
  - {text: "簡訊通知在哪關掉", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單通知會發給誰", source: "draft:outline-20260920", status: proposed}
  - {text: "關閉租客所有通知", source: "draft:outline-20260920", status: proposed}
- sources: [docs:knowledge/jgb-product-facts.md#p914-bill-notify]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
帳單通知的管道依租客是否註冊而不同：免註冊的租客可以分別開關 Email 跟簡訊，業者也可以在租客列表關閉；已註冊的租客固定會收到 Email 與站內通知，已綁定 LINE／FB 的另外會收到推播，租客列表上的開關對他們不能操作。
帳單通知的收件對象只認這張帳單記錄上的那一位承租人，只會發到這個人的手機跟 Email，不會同時發給合約上另一位掛名的承租人。
### 發票可以線上作廢嗎？（可在帳單詳細頁作廢，但只支援 ezPay；其他金流商的發票作廢不了，已開折讓的發票也不能再作廢） {#jgb/E/bill-invoice-void-limitation}
- phrasings:
  - {text: "發票怎麼作廢", source: "draft:outline-20260920", status: proposed}
  - {text: "作廢發票支援哪些金流商", source: "draft:outline-20260920", status: proposed}
  - {text: "折讓後還能作廢嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "ezPay作廢發票", source: "draft:outline-20260920", status: proposed}
- sources: [docs:knowledge/jgb-product-facts.md#p914-invoice-void-ezpay]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
業者可以在帳單詳細頁把該帳單已開立的發票作廢，但這個功能只支援 ezPay 開出來的發票，其他發票廠商的發票會被擋下、作廢不了。
如果這張發票已經開立過折讓單，依 ezPay 的規則就不能再作廢，要退費得改走折讓那條路徑。
### 「通知已匯款」按鈕什麼時候才會出現？（租客付款資訊視窗只在非線上金流收款的帳單才有；應支出帳單的齒輪選單則沒有這個限制） {#jgb/E/bill-notify-remittance-visibility}
- phrasings:
  - {text: "通知已匯款在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "通知已匯款不見了", source: "draft:outline-20260920", status: proposed}
  - {text: "線上收款還要通知已匯款嗎", source: "draft:outline-20260920", status: proposed}
- sources: [docs:knowledge/jgb-product-facts.md#p914-notify-remittance, code:src/components/Lightbox/BillPayInfo.vue, code:src/use/config/useBillTypes.js, code:app/Role.php]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
租客在「帳務管理」→「繳費帳單」打開帳單的付款資訊時，可以按「通知已匯款」，輸入匯款帳號後五碼送出，也可以另外上傳繳款證明。
付款資訊視窗裡的「通知已匯款」，只有不是走線上金流收款的帳單才會出現；應支出帳單齒輪選單裡的「通知已匯款」則沒有這個線上金流的條件。
### 帳單要什麼狀態才可以直接封存？（「待發送」跟「已到帳」都可以直接封存，不用先轉成已到帳；可勾選多筆一次封存） {#jgb/E/bill-archive-precondition}
- phrasings:
  - {text: "草稿可以直接封存嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "封存要先變已到帳嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "批次封存帳單", source: "draft:outline-20260920", status: proposed}
  - {text: "封存順序怎麼安排", source: "draft:outline-20260920", status: proposed}
- sources: [docs:knowledge/jgb-product-facts.md#p914-bill-archive-states, code:src/use/config/useBillTypes.js]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
封存這個動作允許在「待發送」（草稿）跟「已到帳」兩種狀態下直接執行，不需要先把待發送的帳單轉成已到帳才能封存。
帳單總表、收款帳單這類分頁都可以勾選多筆同狀態的帳單一次封存。
### 押金收據號碼是系統自動產生的嗎？（特定合作團隊的客製功能，號碼透過 Excel 匯出／匯入手動填寫，系統不會自動編流水號） {#jgb/E/bill-deposit-receipt-no}
- phrasings:
  - {text: "押金收據號碼怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "押金收據號碼會自動產生嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "押金收據匯入匯出", source: "draft:outline-20260920", status: proposed}
- sources: [docs:knowledge/jgb-product-facts.md#p914-deposit-receipt-no]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
押金收據號碼是特定合作團隊的客製功能：不是系統自動產生的流水號，而是業者用 Excel 匯出、自己填好號碼後再匯入系統寫回去，同一個團隊內號碼不能重複；一般團隊沒有這個欄位。
### 合約已結束、但底下還留著未來計費期間的租金帳單，系統排定發送時會怎麼處理？（系統自動排定發送／自動寄出都會跳過不寄，但不會刪除帳單；業者手動排定發送則不受這條規則限制；批次寄出依帳單 id 由小到大處理，沒有可指定的發送順序） {#jgb/E/bill-scheduled-contract-ended-guard}
- phrasings:
  - {text: "合約結束後帳單還會自動寄嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "解約後草稿帳單會怎樣", source: "draft:outline-20260920", status: proposed}
  - {text: "排定發送帳單順序", source: "draft:outline-20260920", status: proposed}
  - {text: "合約到期未來帳單擋不擋", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Services/Bills/ContractEndedRentBillGuard.php, code:app/Console/Commands/BillBatchSend.php]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
如果一般租金帳單的計費期間起日晚於它所屬合約的結束日，系統每天自動排定發送、自動寄出這兩段流程都會直接跳過這張帳單、不自動寄出，但帳單不會被刪除。
這個攔截只作用在系統自動執行的那兩段流程；業者自己手動把這張帳單按下排定發送，不受這個規則限制。
系統批次寄出排定發送帳單時，是依帳單 id 由小到大遞增處理，沒有可以另外指定發送順序的設定。
### 業者可以請 JGB 客服代發催繳通知嗎？（此操作需由 JGB 客服協助；業者端沒有自助重發催繳的介面） {#jgb/E/bill-remind-resend-by-support}
- phrasings:
  - {text: "催繳通知可以重發嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "客服可以幫忙催繳嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "重新寄催繳通知", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/UserController.php, docs:.kiro/specs/knowledge-outline-and-intent-architecture/inputs/review-sheet-9.15-S2-DE-20260927.md#111, code:app/Console/Commands/BillNotifyOverdue.php]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
逾期未繳的帳單，系統會從逾期隔天起每隔一天自動寄送催繳通知，逾期超過 65 天後停止寄送；業者端沒有自己重新發送催繳通知的按鈕或介面。
此操作需由 JGB 客服協助。
### 超商代碼繳費逾期後才繳，帳單還會入帳嗎？（系統不檢查代碼期限，代碼逾期後是否還能繳費屬外部規定，系統不判斷） {#jgb/E/bill-cvs-barcode-overdue-payment}
- phrasings:
  - {text: "超商代碼過期還能繳嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "超商代碼逾期入帳", source: "draft:outline-20260920", status: proposed}
  - {text: "超商繳費逾期", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/PaymentController.php, docs:.kiro/specs/knowledge-outline-and-intent-architecture/inputs/review-sheet-9.15-S2-DE-20260927.md#114]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
系統收到超商代碼繳費的付款結果通知時，沒有另外檢查這組代碼是不是已經過了繳費期限；是否入帳取決於通知內容是否完整、找不找得到對應的訂單與帳單、這筆訂單是不是已經付過、金流商回傳的交易狀態是不是成功，以及付款金額跟訂單金額是否相符。
代碼過期後還能不能拿去超商繳費、繳了算不算數，屬於金流商自己的規定，系統不判斷這件事。
### 收據功能還會不會有新的開發？（現行已到帳帳單的齒輪選單一律看得到收據，目前沒有公開的後續開發時程） {#jgb/E/bill-receipt-feature-roadmap}
- phrasings:
  - {text: "收據功能會不會更新", source: "draft:outline-20260920", status: proposed}
  - {text: "收據還有新功能嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "收據開發時程", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js, docs:knowledge/jgb-product-facts.md#p914-receipt-email, docs:.kiro/specs/knowledge-outline-and-intent-architecture/inputs/review-sheet-9.15-S2-DE-20260927.md#117, code:app/Notification.php, code:config/role.php]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
現在已到帳的收款帳單，齒輪選單一律看得到「收據」（部分特定合作團隊點「收據」下載的是押金收據）；帳單轉為已付款時，如果收款方是個人房東或法人房東，系統也會自動寄送通知信給租客，一般會附收據 PDF（部分特定合作團隊的通知信不附收據）；收款方是社會住宅的帳單，以及押金設算息帳單，不會寄這封通知信。
目前沒有公開的收據功能開發時程。
## 建立與編輯帳單（單筆、批次、週期批次） {#E-bill-create-edit}
### 新增帳單有哪幾種頁面？（新增帳單／新增批次帳單／新增週期帳單／編輯帳單） {#jgb/E/bill-create-modes}
- phrasings:
  - {text: "新增帳單有幾種", source: "draft:outline-20260920", status: proposed}
  - {text: "批次帳單跟週期帳單差在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼新增帳單", source: "draft:outline-20260920", status: proposed}
  - {text: "編輯帳單在哪", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/_parts/BillBasicInfoSection.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
新增帳單有「新增帳單」（單筆）、「新增批次帳單」、「新增週期帳單」三種頁面，另外已存在的帳單可以進「編輯帳單」修改。
這三個新增帳單頁面跟編輯帳單畫面共用同一套版面，只是依所在頁面決定要不要走批次模式、要顯示哪些欄位跟標題。
「編輯帳單」是針對已經存在的單一張帳單修改內容，不能一次修改多張。
### 新增帳單時「對象」可以選哪些？（租客／大房東／物件／其他） {#jgb/E/bill-create-target}
- phrasings:
  - {text: "帳單對象怎麼選", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單可以開給大房東嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單對象是誰", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單開給物件", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/utils/constants/bill.js, code:src/pages/bills/edit/Index.jsx, code:src/pages/bills/edit/_parts/BillBasicInfoSection.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
新增帳單時「對象」下拉可以選「租客」「大房東」「物件」「其他」四種身分。
在單筆「新增帳單」頁切換對象後，付款方式與收款帳戶會先清空；只有對象選「租客」時，才會依所選合約重新帶入收款設定，選「大房東」「物件」「其他」則維持清空、要自己選。
對象選「租客」時，會依所選的合約帶出該合約的簽約資訊（法人約顯示公司名）；對象選「大房東」則是從『目前所選物件』的大房東名單裡挑一位——這份名單是依所選物件即時查詢帶出的，不是整個團隊共用同一份大房東名單，換一個物件、可選的大房東也會跟著換。
### 「新增批次帳單」跟「新增週期帳單」有什麼不同？（批次是每個對象各一張，週期是一次產出各期帳單；兩者都可在租客與物件之間切換） {#jgb/E/bill-batch-vs-cycle}
- phrasings:
  - {text: "批次帳單跟週期帳單差別", source: "draft:outline-20260920", status: proposed}
  - {text: "新增批次帳單怎麼選對象", source: "draft:outline-20260920", status: proposed}
  - {text: "新增週期帳單怎麼選物件", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/_parts/BillTargetBatchBlock.jsx, code:src/use/config/useBillTypes.js, code:src/utils/constants/contract.js, code:src/pages/contracts/pick/_parts/PageTop.vue, code:src/pages/bills/edit/Index.jsx]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
「新增批次帳單」預設從合約（租客）挑選、「新增週期帳單」預設從物件挑選，但兩個頁面的挑選頁都可以在「租客」與「物件」之間切換。
「新增週期帳單」是依設定的期間與繳費週期，一次產出各期的帳單（送出前會先「預覽帳單」），不是之後由系統自動反覆產生。
批次帳單建立後，每個對象各自產生一張獨立的帳單，之後可以分別調整；週期帳單產出的各期帳單，之後也可以到各期帳單再編輯。
### 新增週期帳單的「繳費週期」設定要填哪些欄位？（繳費週期／繳費截止日／截止日設定／帳單週期制度） {#jgb/E/bill-cycle-schedule-fields}
- phrasings:
  - {text: "週期帳單怎麼設定", source: "draft:outline-20260920", status: proposed}
  - {text: "繳費週期選項", source: "draft:outline-20260920", status: proposed}
  - {text: "當月分算跟跨月計算差在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "提前截止同月截止", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/_parts/CycleBillingCycleFields.vue, code:src/utils/constants/contract.js]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「繳費週期」下拉提供每月到每年（1～12 個月制）共 12 種選項。
「繳費截止日」跟帳單週期分算日都是選每月第幾號（1～31 號）。
「截止日設定」分「提前截止」與「同月截止」兩種。
「帳單週期制度」是單選，分「當月分算」與「跨月計算」，預設選第一項「當月分算」；選「跨月計算」才會多顯示「帳單週期分算日」欄位。
### 「總額（自動分攤）」欄位什麼時候才會出現？（只有新增週期帳單、且團隊開通社區投報率時） {#jgb/E/bill-cycle-amortization}
- phrasings:
  - {text: "總額自動分攤在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "週期帳單金額怎麼分攤", source: "draft:outline-20260920", status: proposed}
  - {text: "自動分攤欄位不見了", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/_parts/BillBasicInfoSection.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「總額（自動分攤）」欄位只出現在新增週期帳單頁面，而且團隊要開通社區投報率功能才會顯示。
「金額輸入方式」預設是「每期金額」，費用欄位填的金額會套用到每一期；改選「總額（自動分攤）」時，費用欄位改填整筆總金額，由系統拆分到各期。
「總額（自動分攤）」的分攤方式是把填入的總金額平均分成各期，除不盡的零頭全部加在最後一期，不是依比例或依天數分攤。
### 帳單費用細目填寫有什麼規則？（度數欄位最多小數點後 2 位、電水瓦斯金額欄位限制小數點後 2 位、當期度數不可小於上期度數） {#jgb/E/bill-fee-item-rules}
- phrasings:
  - {text: "費用細目怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "水電費當期度數錯誤", source: "draft:outline-20260920", status: proposed}
  - {text: "金額小數點限制", source: "draft:outline-20260920", status: proposed}
  - {text: "度數輸入錯誤提示", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/_parts/FeesBlock.jsx, code:src/components/PrefixInput.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
費用細目裡的「當期度數」「上期度數」欄位最多只能輸入到小數點後 2 位，超過會被自動截斷；金額欄位只有「電費」「水費」「瓦斯費」這三種項目會限制到小數點後 2 位，其他項目的金額欄位沒有這個限制。
水電這類用度數計費的項目，只有「當期度數嚴格小於上期度數」才會在小計欄下方顯示錯誤提示；當期度數等於上期度數（用電量 0 度）不會出現這個錯誤，即使錯誤文字寫的是『必須大於上期度數』。
度數的檢查不是一邊打字一邊提示，而是在輸入完、離開欄位時觸發；不需要等到送出才發現錯誤。
### 「帳單標題」最多可以輸入幾個字？（45 個字） {#jgb/E/bill-title-field}
- phrasings:
  - {text: "帳單標題字數上限", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單標題最多幾個字", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/_parts/BillBasicInfoSection.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「帳單標題」最多可以輸入 45 個字。
### 「帳單備註」最多可以輸入幾個字？（150 個字） {#jgb/E/bill-remark-field}
- phrasings:
  - {text: "帳單備註字數上限", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單備註最多幾個字", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/_parts/BillBasicInfoSection.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「帳單備註」最多可以輸入 150 個字。
### 「內部備註」最多可以輸入幾個字？誰看得到？（100 個字，僅供業者團隊成員查看／編輯，租客看不到） {#jgb/E/bill-internal-note-field}
- phrasings:
  - {text: "內部備註字數上限", source: "draft:outline-20260920", status: proposed}
  - {text: "內部備註誰看得到", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/_parts/BillBasicInfoSection.vue, code:src/pages/bills/edit/_parts/InternalNoteBlock.jsx]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「內部備註」最多可以輸入 100 個字，欄位上標示「僅供內部查看」，這個備註是僅供業者團隊成員查看／編輯的欄位，租客端看不到。
### 「內部備註」在哪些地方會出現？（只給業者團隊成員看：新增帳單單筆、編輯帳單與帳單列表欄位可填，帳單明細可看；批次／週期帳單頁面不顯示） {#jgb/E/bill-internal-note-visibility}
- phrasings:
  - {text: "內部備註在批次帳單有嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "內部備註在週期帳單有嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/_parts/BillBasicInfoSection.vue, code:src/pages/bills/_parts/ListTable.jsx, code:src/components/Lightbox/BillItemDetail.vue, code:app/Http/Controllers/BillController.php, code:app/BillAdditions.php]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「內部備註」可以在「新增帳單」（單筆）跟「編輯帳單」頁面填寫，也可以在帳單列表的「內部備註」欄直接修改後存檔；「新增批次帳單」「新增週期帳單」不會顯示這個欄位；填好的內部備註也會出現在帳單明細視窗裡。
內部備註只給這張帳單所屬業者團隊的成員看：租客身分、大房東看不到，不是這張帳單所屬團隊的成員也看不到。
### 新增帳單時付款方式跟收款帳戶一定要一起填嗎？（兩者要嘛都空、要嘛都填；固定虛擬帳號例外） {#jgb/E/bill-payment-method-account-pair}
- phrasings:
  - {text: "付款方式沒填會怎樣", source: "draft:outline-20260920", status: proposed}
  - {text: "收款帳戶沒選會怎樣", source: "draft:outline-20260920", status: proposed}
  - {text: "固定虛擬帳號付款方式", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/Index.jsx, code:src/pages/bills/edit/_parts/BillCreatePaymentSelector.vue, code:app/Http/Controllers/BillController.php]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在「新增帳單」跟「新增批次帳單」，付款方式跟收款帳戶兩者都空著可以送出（沿用合約的收款設定）；但只填其中一項會被擋下，提示要完成付款方式與收款帳戶選擇。
選擇固定虛擬帳號當付款方式是例外：這個方式的收款帳戶欄位只是顯示合約綁定的帳號、不能挑選，所以不受兩者要成對填寫的規則限制。
這個成對檢查不是每次改欄位就即時檢查，而是在按下送出確認彈窗（送出點退不受影響）或儲存草稿的當下才檢查；只填其中一項時，儲存草稿也會被擋下，提示同樣要完成付款方式與收款帳戶選擇。
### 租客還沒完成驗證時，帳單會被擋在草稿嗎？（合約頁的提示這樣寫，但目前送出帳單時系統不會因為驗證狀態擋下） {#jgb/E/bill-tenant-unverified-draft-lock}
- phrasings:
  - {text: "租客沒驗證帳單發不出去", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單卡在草稿", source: "draft:outline-20260920", status: proposed}
  - {text: "租客驗證連結過期帳單", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單一直是草稿狀態", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/_parts/BillTargetBlock.jsx, code:src/pages/contracts/_parts/SignerInfoCard.jsx, code:app/Http/Controllers/BillController.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
合約頁的簽約對象資訊裡有一段提示：如果有發送驗證通知給租客，系統會把帳單停留在草稿帳單分頁，待租客完成驗證或驗證連結過期後才能發送；但目前實際送出帳單時，系統並不會因為租客還沒完成驗證而擋下。
在這個情況下，房東仍然可以手動把帳單直接由草稿移至應到帳或已到帳，不受驗證狀態限制。
### 新增帳單頁面下方送出按鈕的文字跟行為會依情境改變（送出／發送簽核／簽核中／預覽帳單） {#jgb/E/bill-submit-button-behavior}
- phrasings:
  - {text: "送出按鈕文字不一樣", source: "draft:outline-20260920", status: proposed}
  - {text: "發送簽核是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "簽核中按鈕", source: "draft:outline-20260920", status: proposed}
  - {text: "週期帳單預覽按鈕", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/Index.jsx]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
一般情況下按鈕文字是「送出」；只有部分特定合作團隊的帳單會走簽核流程，這時按鈕文字會改成「發送簽核」，代表按下去是送進簽核而不是直接發帳單。
如果簽核正在處理中，按鈕會顯示「簽核中」。
新增週期帳單頁面，底部按鈕固定顯示「預覽帳單」，用來先產生本次週期會建立的帳單清單再確認。
一般情況下，底部主按鈕右邊還會有一個下拉選項「儲存草稿」，可以先把目前填寫的內容存成草稿，不用直接送出或走簽核；特定合作團隊的帳號、簽核處理中、或週期帳單預覽這幾種情境下，不會出現這個下拉選項。
### 新增帳單選租客當對象時，付款方式會自動帶入合約的收款設定嗎？（會，但帳戶已停用/不可取號等情況不會亂猜） {#jgb/E/bill-contract-payment-prefill}
- phrasings:
  - {text: "帳單付款方式自動帶入", source: "draft:outline-20260920", status: proposed}
  - {text: "新增帳單付款方式跟合約一樣", source: "draft:outline-20260920", status: proposed}
  - {text: "合約收款方式帶入帳單", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/Index.jsx, code:src/helpers/billCreatePaymentPrefill.ts]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
只有「新增帳單」（單筆）在對象選租客時，才會依該租客合約的收款設定自動帶入付款方式與收款帳戶。
如果合約帶出來的收款帳戶已經停用、線上金流帳戶目前不可取號、是自訂的現金帳戶，或合約的收款方式是支票、線下現金這類舊制方式，系統不會亂猜一個值，付款方式會維持未選；合約是固定虛擬帳號時，綁定仍有效才會帶入「固定虛擬帳號」，綁定已失效就維持未選。
這個自動帶入的機制只在對象是「租客」時才會啟動，選其他對象（大房東、物件、其他）不會嘗試帶入合約付款設定。
### 不足一個月的租金怎麼算？（依天數比例；一般團隊以剩餘天數 ÷ 該月曆天數，逐月產帳以實際天數 ÷ 該期帳單天數，不是固定除以 30） {#jgb/E/bill-partial-month-proration}
- phrasings:
  - {text: "不足月租金怎麼算", source: "draft:outline-20260920", status: proposed}
  - {text: "入住天數比例分攤", source: "draft:outline-20260920", status: proposed}
  - {text: "不足一個月租金按天數怎麼折算", source: "draft:outline-20260920", status: proposed}
- sources: [docs:knowledge/jgb-product-facts.md#p914-proration, code:app/Role.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
不足一個月的租金是依天數比例計算，不是固定除以 30 天：一般團隊（合約成立時就產生整個租期的帳單）用「剩餘天數 ÷ 該月的曆天數」折算；部分特定合作團隊與排程逐月產帳，則用「這一期實際天數 ÷ 這一期帳單的天數」折算。
### 草稿帳單的電費度數要自己填嗎？（物件有綁定智慧電錶時，可在編輯頁按「取得即時電錶度數」先帶入） {#jgb/E/bill-power-reading-draft-defaults}
- phrasings:
  - {text: "電費度數怎麼帶入", source: "draft:outline-20260920", status: proposed}
  - {text: "電表度數會重抓嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "草稿帳單度數空白", source: "draft:outline-20260920", status: proposed}
- sources: [docs:knowledge/jgb-product-facts.md#p914-power-reading-draft, code:app/Bill.php, code:src/pages/bills/edit/_parts/FeesBlock.jsx, code:app/Http/Controllers/BillController.php, code:app/Detail.php, code:app/Services/ApprovalService.php, code:src/use/search/modules/billType.js]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
草稿的合約帳單，如果物件有綁定智慧電錶、系統預設的「電費」品項當期度數還沒有填過，打開編輯頁時當期度數就會自動帶入電錶當下讀數，已經填過的度數不會被覆蓋（特定合作團隊已送簽核的帳單除外）；這種電費列另有「取得即時電錶度數」按鈕，按下去會再抓一次電錶當下讀數填進當期度數，部分特定合作團隊沒有這個按鈕；沒有綁定智慧電錶的物件不會自動帶入電錶讀數。
## 帳單統計與報表 {#E-bill-stats}
### 「統計報表」的「當前表現」分頁顯示什麼？（收款情況／支出情況卡片） {#jgb/E/bill-stat-overview}
- phrasings:
  - {text: "統計報表看什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "收款情況怎麼算", source: "draft:outline-20260920", status: proposed}
  - {text: "支出情況怎麼算", source: "draft:outline-20260920", status: proposed}
  - {text: "預計總收款是什麼", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/stat/Index.jsx, code:src/pages/bills/stat/_parts/Stat.jsx]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
統計報表預設進到「當前表現」分頁，顯示「收款情況」跟「支出情況」兩張卡片。
「收款情況」卡片的「預計總收款」＝應到帳＋待對帳＋已到帳；「未收款」＝應到帳＋待對帳。
「支出情況」卡片的「預計總支出」＝應支出＋已支出。
### 統計報表除了「當前表現」，還有「每月報表」「每月對帳單」分頁，但只有特定合作團隊看得到 {#jgb/E/bill-stat-monthly-tabs}
- phrasings:
  - {text: "每月報表在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "每月對帳單在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "統計報表分頁不見了", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/stat/Index.jsx]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
統計報表頁面除了「當前表現」，還有「每月報表」跟「每月對帳單」兩個分頁，但這兩個分頁只提供給特定合作團隊的帳號使用，一般帳號只看得到「當前表現」一個分頁。
一般帳號直接進統計報表頁面時，分頁切換列只會顯示「當前表現」一個選項。
就算試著用網址直接切換到「每月報表」或「每月對帳單」，只要這個帳號不屬於特定合作團隊，畫面依然會顯示「當前表現」的內容而不是報表內容。
### 「每月報表」跟「每月對帳單」分頁在做什麼？（依社區/物件上傳與下載每月的物件報表、對帳單檔案） {#jgb/E/bill-monthly-report-upload}
- phrasings:
  - {text: "物件報表怎麼新增", source: "draft:outline-20260920", status: proposed}
  - {text: "物件對帳單怎麼新增", source: "draft:outline-20260920", status: proposed}
  - {text: "報表還沒上傳", source: "draft:outline-20260920", status: proposed}
  - {text: "每月報表社區物件篩選", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/stat/_parts/MonthlyReport.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「每月報表」分頁底下是「物件報表」，可以依社區、物件篩選後按「新增報表」上傳檔案。
「每月對帳單」分頁底下是「物件對帳單」，一樣可以篩選後按「新增對帳單」上傳。
選定的物件如果還沒有人上傳過報表，畫面會顯示「尚未上傳任何報表」。
「物件報表」要先選「社區」再選「物件」兩層下拉篩選，選定物件後才會抓這個物件的報表清單；如果選了社區但還沒選物件，畫面會用「尚未上傳任何報表」搭配「請選擇物件」提示，不是真的代表這個社區沒有任何報表。
## 社宅報表 {#E-social-housing-report}
### 社宅報表的「清冊列表」在列什麼？（每個媒合編號底下的表單勾選與修繕費、申請期數） {#jgb/E/social-housing-sheet-list}
- phrasings:
  - {text: "社宅報表清冊列表", source: "draft:outline-20260920", status: proposed}
  - {text: "媒合編號在哪看", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅表單修繕費", source: "draft:outline-20260920", status: proposed}
  - {text: "申請期數上限是12嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅表單哪個沒有額外欄位", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅表單全選", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/socialHousingSheets/Index.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社宅報表頁面上方是「清冊列表」，以「媒合編號」為單位，每一列可以勾選要製作的表單，目前總共有「表單 4」「表單 7」「表單 9」「表單 11」四種表單類型。
「表單 4」需要另外填「修繕費」金額。
「表單 7」「表單 9」需要另外填「申請期數」，可選期數是 1 到「12 減去這份合約已經申報過的期數」之間，不是固定的 1～12 期。
「表單 11」沒有「修繕費」或「申請期數」這類額外欄位，畫面排版也跟其他表單不一樣，是單獨一個核取方塊，不是跟其他欄位並排。
清冊列表最上方那一列，「表單 4」「表單 7」「表單 9」「表單 11」各自都有獨立的「全選」核取方塊，可以針對單一表單類型一次勾選或取消勾選底下所有列，不是整張清冊只有一個共用的全選。
### 社宅報表上方的合約版本切換列是做什麼用的？（切換不同版本的社宅合約，每次查詢都會帶著這個版本一起送出） {#jgb/E/social-housing-sheet-contract-version}
- phrasings:
  - {text: "社宅報表合約版本", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅報表版本切換", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅合約版本網址", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/routes/bills.js, code:src/pages/bills/socialHousingSheets/Index.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社宅報表的網址上會帶有目前選擇的「合約版本」，頁面上方有一條切換列，可以切換不同版本的社宅合約類型。
不管切換到哪個版本、或送出任何查詢，系統查詢時都會一併帶著這個版本一起送出，不只是畫面上的分頁效果。
### 社宅報表怎麼製作表單？（填撥款日、勾選表單後按「製作表單」，會記錄成清冊紀錄） {#jgb/E/social-housing-sheet-make-form}
- phrasings:
  - {text: "社宅報表怎麼做表單", source: "draft:outline-20260920", status: proposed}
  - {text: "撥款日在哪填", source: "draft:outline-20260920", status: proposed}
  - {text: "製作表單按鈕", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅表單團隊紀錄", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/socialHousingSheets/Index.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
製作表單前要先在「撥款日」欄位選一個日期，並勾選清冊列表裡要製作的表單。
按下「製作表單」後，系統會把上述勾選跟填寫的資料存下來，之後再進清冊列表時，會自動帶入團隊成員最後一次操作的紀錄。
製作出來的表單會出現在下方的「匯出歷史」清單裡，可以點選清單裡的表單按鈕逐一下載。
### 社宅報表的「匯出歷史」會記錄幾筆匯出動作？（系統至多記錄近 30 筆） {#jgb/E/social-housing-sheet-export-history}
- phrasings:
  - {text: "社宅報表匯出歷史", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅表單匯出紀錄上限", source: "draft:outline-20260920", status: proposed}
  - {text: "匯出歷史看多少筆", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/socialHousingSheets/Index.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
製作表單後會進入「匯出歷史」清單，記錄匯出時間、操作人員與表單類型。
系統至多記錄近 30 筆匯出動作。
### 社宅報表的「歸檔」是什麼意思？（操作按鈕是「確定歸檔」；綠色「歸檔」標籤只在已歸檔後才出現） {#jgb/E/social-housing-sheet-archive}
- phrasings:
  - {text: "社宅報表歸檔", source: "draft:outline-20260920", status: proposed}
  - {text: "歸檔後能修改嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "確定歸檔按鈕", source: "draft:outline-20260920", status: proposed}
  - {text: "舊紀錄表單能下載嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/socialHousingSheets/Index.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在匯出歷史清單裡，只有排在最上面、還沒歸檔的那一筆紀錄旁邊會有「確定歸檔」的操作按鈕，按下去會跳出確認視窗「確定要歸檔嗎」。
確認視窗說明執行歸檔後，資料會同步至資料庫且無法修改，要繼續才按「確認」。
綠色帶勾勾圖示的「歸檔」標籤，只會在這筆紀錄已經完成歸檔之後才顯示；已經歸檔的紀錄，「確定歸檔」按鈕會保留在畫面上但變成無法點擊的停用狀態，不是完全消失，也沒有另外一個單獨叫「歸檔」的按鈕。
在「其餘筆」（非最新一筆）的歷史紀錄裡，如果這筆還沒歸檔，該列的表單欄位只會用文字＋頓號列出表單名稱，不會出現可以下載的按鈕；只有已經歸檔的紀錄，表單名稱才會變成可以點擊下載的按鈕。
### 社宅報表的「社會住宅」身份可以對應到哪個地方政府的社宅方案？（系統只定義身份類別，不判斷方案適配） {#jgb/E/social-housing-sheet-program-scope}
- phrasings:
  - {text: "社宅報表適用哪個社宅方案", source: "draft:outline-20260920", status: proposed}
  - {text: "社會住宅身份限制", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅報表限台灣嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:config/role.php, docs:.kiro/specs/knowledge-outline-and-intent-architecture/inputs/review-sheet-9.15-S2-DE-20260927.md#104]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
JGB 把「社會住宅」設計成一種團隊身份，跟「個人房東/代理人」「法人房東(公司)」並列，可以建立多筆，但只開放台灣（幣別新台幣、地區台灣）使用。
至於這個身份能不能對應到某個地方政府推出的特定社宅方案，屬地方政府社宅政策認定，系統不判斷。
## 差額發票（群組、底租、社區層開關） {#E-balance-invoice}
### 差額發票要在哪裡設定？（團隊開通後在「差額發票管理」建立差額群組；社區編輯頁的差額發票開關只對部分特定合作團隊顯示） {#jgb/E/balance-invoice-community-switch}
- phrasings:
  - {text: "怎麼開差額發票", source: "draft:outline-20260920", status: proposed}
  - {text: "社區差額發票開關", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票怎麼計算", source: "draft:outline-20260920", status: proposed}
  - {text: "底租總額怎麼設定", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/edit/BalanceInvoice.jsx, code:src/pages/communities/edit/Index.vue, code:app/Role.php]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
差額發票是團隊開通功能後，從選單的「差額發票管理」建立差額群組來設定；社區編輯頁的「差額發票」分頁（「是否開設差額發票」開關）只對部分特定合作團隊顯示。
社區編輯頁這個開關開啟後的說明文字是：當此社區下所有物件的每月總租金金額大於每月底租金額時，系統將自動開立差額發票。
在社區編輯頁開啟開關要填「底租總額」的幣別與每月租金金額；關閉開關時，幣別與金額欄位會被清空。
### 差額發票群組總表有哪些狀態？（尚未生效／進行中／歷史／封存） {#jgb/E/balance-invoice-group-statuses}
- phrasings:
  - {text: "差額發票群組狀態", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票群組總表", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票尚未生效", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票封存", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/utils/constants/balanceInvoices.ts, code:src/pages/balanceInvoices/list/_parts/ListTable.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
差額發票群組總表的狀態分「尚未生效」「進行中」「歷史」「封存」四種。
「尚未生效」代表包租約還沒開始，「進行中」代表包租約正在進行，「歷史」代表包租約已經停止，「封存」則是使用者自己把這個群組收起來。
群組總表可以依這四個狀態切換分頁查看，不同狀態的群組會分開列表。
### 差額發票群組總表列表裡看得到哪些欄位？（ID／出租物件數／本月發票狀態／累積成本／累積收入／累積發票金額） {#jgb/E/balance-invoice-list-columns}
- phrasings:
  - {text: "差額發票列表欄位", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票累積成本", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票累積收入", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票本月發票狀態", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/balanceInvoices/list/_parts/ListTable.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
差額發票群組總表列表欄位有：ID、狀態、群組、出租物件數、本月發票狀態、累積成本、累積收入、累積發票金額。
「群組」欄位顯示的是差額發票群組的名稱。
「出租物件數」顯示這個群組目前底下有幾個物件正在出租。
### 建立差額發票群組要填哪些基本資料？（群組名稱／底租／租期／前期餘額／房屋座落地址／房屋稅籍編號） {#jgb/E/balance-invoice-group-basic-info}
- phrasings:
  - {text: "差額發票群組怎麼建立", source: "draft:outline-20260920", status: proposed}
  - {text: "群組名稱必填嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "前期餘額怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "房屋稅籍編號填在哪", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/balanceInvoices/edit/basicInfo/Index.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
建立差額發票群組要填「群組名稱」，這是必填欄位。
要填「底租」金額，這是必填欄位。
要填「租期」起訖日期，這是必填欄位。
可以另外填「前期餘額」金額與結算日期。
還可以填「個人住宅所有權人」「房屋座落地址」「房屋稅籍編號」。
### 差額發票群組怎麼加入物件？每個物件的底租可以自訂嗎？（群組可開「自訂個別底租」，把群組底租總額分配給各物件） {#jgb/E/balance-invoice-pick-and-individual-rent}
- phrasings:
  - {text: "差額發票怎麼加物件", source: "draft:outline-20260920", status: proposed}
  - {text: "自訂個別底租", source: "draft:outline-20260920", status: proposed}
  - {text: "可分配租金是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "群組底租怎麼分配到每個物件", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/balanceInvoices/edit/pickEstates/Index.vue, code:src/pages/balanceInvoices/_parts/IndividualBaseRentSetting.vue, code:src/pages/balanceInvoices/groups/Index.vue, code:app/Services/BalanceInvoiceService.php]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
差額發票群組要透過「請選擇物件」頁面挑選要加入群組的物件。
差額發票群組有一個「自訂個別底租」開關，是整個群組共用一個開關；開啟後會顯示「可分配租金」，可以把群組的底租總額分配給群組內各個物件，而不是全部物件共用同一個底租金額。
群組的「自訂個別底租」維持關閉時，是把群組底租總額依群組內物件數平均，再乘上計入底租的物件數，當作每月成本去計算差額。
### 差額發票群組詳細頁面看得到什麼？（招租數量／本月應收金額／本月已收金額，以及三個分頁） {#jgb/E/balance-invoice-group-detail-tabs}
- phrasings:
  - {text: "差額發票群組詳細頁", source: "draft:outline-20260920", status: proposed}
  - {text: "招租數量是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "本月應收金額", source: "draft:outline-20260920", status: proposed}
  - {text: "差額總表在哪看", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/balanceInvoices/groups/Index.vue, code:src/pages/balanceInvoices/groups/_parts/ReportTable.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
群組詳細頁面上方會顯示「招租數量」「底租金額」「前期餘額金額」「本月應收金額」「本月已收金額」。
群組詳細頁面下方分三個分頁：「群組物件」「差額總表」「報表發票下載」。
「群組物件」分頁列出目前這個群組底下有哪些物件，以及各自的底租設定。
「報表發票下載」分頁則是依年份列出可以下載的月度報表或發票檔案。
### 「差額總表」裡每個月的差額怎麼看、怎麼開發票？（累積成本、累積收入、差額、是否開發票、發票金額、發票字軌） {#jgb/E/balance-invoice-monthly-invoice-table}
- phrasings:
  - {text: "差額總表欄位", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票開立日期", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票字軌", source: "draft:outline-20260920", status: proposed}
  - {text: "差額怎麼算", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/balanceInvoices/groups/_parts/InvoiceTable.vue, code:app/Services/BalanceInvoiceService.php, code:src/use/config/balanceInvoices/useBalanceInvoicesActions.ts, code:app/Console/Kernel.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
差額總表按月份列出這個群組每個月的累積成本、累積收入、差額，以及是否開發票、開立日期、發票金額、發票字軌。
還沒開發票的月份，「差額」欄顯示的是差額金額的絕對值（不帶正負號）；已經開立發票的月份，「差額」跟「發票金額」這兩欄改成顯示同一個發票開立時的實際金額。
已經開立發票的月份會另外顯示發票的「開立日期」跟「發票字軌」。
差額發票除了由系統每月排程自動開立，也可以在差額發票群組列表的動作選單點「開立發票」手動開立；手動開立時群組要是「進行中」狀態、而且這個月還沒開過發票。
### 差額發票什麼時候自動產生？（一般業者每月 1 日 03:00 開立上月發票；特定團隊另有自己的時程） {#jgb/E/balance-invoice-timing}
- phrasings:
  - {text: "差額發票何時開立", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票排程", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票狀態多久更新一次", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票每2小時", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Models/BalanceInvoiceGroup.php, code:app/Console/Kernel.php, code:app/Services/BalanceInvoiceService.php, code:routes/api.php, code:src/pages/balanceInvoices/edit/Index.vue, code:src/pages/balanceInvoices/list/_parts/ListTable.vue]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
除了一個特定合作團隊以外，其餘業者的差額發票由系統於每月 1 日凌晨 03:00 排程自動開立「上一個月」的差額發票。
那個特定合作團隊的時程不同：改成每月最後一天 23:30 直接開立「當月」發票，並在次月 1 日 03:05 依當下最新資料重新計算明細表（不是重印快照，讓月底才入帳的款項也能反映在報表上）。
差額發票群組的狀態（尚未生效／進行中／歷史）除了每日凌晨 01:05 的排程更新一次，編輯群組存檔時也會依租期立即重新計算；群組列表上的「累積成本」「累積收入」則是每次開啟列表時，依已開立發票的月份當場算出。
### 差額發票群組的動作選單有哪些選項？什麼時候不能用？（編輯群組／開立發票／封存群組／刪除群組；列表頁不能用時反灰，詳細頁直接不顯示；另有查看歷程圖示） {#jgb/E/balance-invoice-group-action-menu}
- phrasings:
  - {text: "差額發票群組怎麼刪除", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票群組動作選單", source: "draft:outline-20260920", status: proposed}
  - {text: "開立發票按鈕為什麼灰色", source: "draft:outline-20260920", status: proposed}
  - {text: "封存群組按鈕為什麼不能按", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/balanceInvoices/useBalanceInvoicesActions.ts, code:src/components/SurelyVue/BalanceInvoices/ActionsCell.vue, code:src/pages/balanceInvoices/groups/Index.vue, code:app/Services/BalanceInvoiceService.php, code:src/pages/balanceInvoices/list/_parts/ListTable.vue, code:src/components/Lightbox/BalanceInvoicesActivityLog.vue]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
差額發票群組的動作選單選項有「編輯群組」「開立發票」「封存群組」「刪除群組」四個。
「編輯群組」永遠可以點，會跳轉去編輯這個群組的基本資料。
「開立發票」只有在群組目前狀態是「進行中」、而且這個月還沒開過發票時才能用。
「封存群組」在群組還不是「封存」狀態時才能用。
「刪除群組」要這個群組還能刪除才能用；在動作選單手動「開立發票」過的群組就不能再刪除。
在群組列表頁，不能用的選項會反灰、無法點擊；在群組詳細頁則直接不顯示不能用的選項，而且詳細頁不會出現「開立發票」。
在群組列表頁，動作選單旁邊另外有一個獨立的「查看歷程」圖示按鈕，不在下拉選單裡，點下去可以看這個群組的操作紀錄；群組詳細頁沒有這個按鈕。
### 差額發票收支表的租金退款／減免怎麼呈現？（列在「租金增(減)(B)」欄，以負數表示） {#jgb/E/balance-invoice-refund-report-column}
- phrasings:
  - {text: "差額發票收支表退款", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票租金增減欄", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票減免怎麼記", source: "draft:outline-20260920", status: proposed}
- sources: [docs:knowledge/jgb-product-facts.md#p914-balance-invoice-refund]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「報表發票下載」分頁裡的收支表，租金退款或減免會列在「租金增(減)(B)」這一欄，並以負數（括號）表示。
### 差額發票收支表怎麼判斷一個帳單品項算不算「租金」收入？（系統預設品項看名稱是不是「租金」「退租金」；自訂品項看品項性質） {#jgb/E/balance-invoice-rent-item-rule}
- phrasings:
  - {text: "差額發票租金品項判定", source: "draft:outline-20260920", status: proposed}
  - {text: "退租帳單科目重複計入", source: "draft:outline-20260920", status: proposed}
  - {text: "差額收支表怎麼認租金", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Services/BalanceInvoiceService.php, code:src/use/search/modules/billType.js, code:app/Bill.php]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
差額發票收支表判斷一筆帳單品項算不算「租金」收入：系統預設品項看品項名稱是不是「租金」或「退租金」；業者自訂的品項則看品項性質是不是「租金」，自訂品項即使取名「租金」、性質不是租金也不算；另外還要先看這筆帳單的「帳單來源」：只有「合約帳單」「點退帳單」「手動建立帳單」上的品項才會逐筆判斷，「罰金帳單」「儲值電費帳單」「設算息帳單」上的品項不論名稱或性質一律不計入。
如果個案帳單的品項命名方式跟預繳租金重複，會不會造成收支表重複計入，屬記帳命名上的判斷，需要依個案帳單資料確認。
### 身分從法人改成自然人後，差額發票群組要怎麼重新設定？（系統沒有專用的身分切換規則） {#jgb/E/balance-invoice-entity-type-change}
- phrasings:
  - {text: "差額發票法人改自然人", source: "draft:outline-20260920", status: proposed}
  - {text: "差額群組身分切換", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票身分變更", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Services/BalanceInvoiceService.php]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
差額發票的計算與開票邏輯裡，沒有針對「法人改成自然人」這種身分變更設計專屬的處理規則，結果要看個案在系統上實際填寫、切換的資料，需要依個案情況確認。
### 合約還沒簽回時能不能開發票或收據？（發票看合約的開票設定、押金收據看帳單是否到帳，簽署狀態是否連動要看個案） {#jgb/E/balance-invoice-unsigned-contract}
- phrasings:
  - {text: "合約未簽回能開發票嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "合約未簽回押金收據", source: "draft:outline-20260920", status: proposed}
  - {text: "簽約中可以開發票嗎", source: "draft:outline-20260920", status: proposed}
- sources: [docs:knowledge/jgb-product-facts.md#p914-invoice-per-bill, docs:knowledge/jgb-product-facts.md#p914-receipt-email]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
發票什麼時候開立，是依合約與團隊的開票設定決定（例如是否開啟「預先開立發票」、有沒有立即開立權限），不是直接看合約有沒有簽回。
押金收據則是看這筆帳單本身有沒有被標記為已到帳；帳單到帳後系統寄給租客的通知信會附上收據（部分特定合作團隊另有處理方式）。
至於合約還沒簽署完成時，這些規則會不會被連動擋下，屬個案情況，需要查詢個案的合約與帳單資料確認。
### 帳單不在任何差額發票群組內時，JGB 怎麼處理？ {#jgb/E/balance-invoice-anomaly-list}
- phrasings:
  - {text: "帳單沒有差額群組怎麼辦", source: "draft:outline-20260920", status: proposed}
  - {text: "發票異常盤查名單", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單不在差額群組", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/Admin/InvoiceFailureController.php, code:app/Services/InvoiceFailureAuditService.php, code:routes/web.php, code:app/Bill.php, code:src/use/search/modules/billInvoiceStatus.js]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
帳單不屬於任何差額發票群組、又出現開票異常的情況時，系統會把它列進內部「發票異常盤查」名單；業者端在帳單列表可以用「發票異常」狀態篩選，撈出原該開立但開立失敗的帳單。
## 固定虛擬帳號管理（租客虛擬帳號、餘額、歷程） {#E-virtual-account}
### 「固定虛擬帳號管理」列表看得到哪些資訊？（虛擬帳號、餘額、歷程一律都有；租客或物件欄位看團隊的固定虛擬帳號模式；有編輯權限時另有操作欄） {#jgb/E/recharge-account-list-columns}
- phrasings:
  - {text: "固定虛擬帳號管理在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號列表欄位", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號餘額能改嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號歷程", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/rechargeAccountList/Index.vue, code:app/Http/Controllers/RechargeAccountListController.php, code:app/RechargeAccount.php, code:app/Http/Controllers/Admin/FeatureConfigController.php]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「固定虛擬帳號管理」列表一定會有的欄位是虛擬帳號、餘額、歷程；團隊的固定虛擬帳號功能如果是「以人為主」模式，會多出租客姓名、Email、手機號碼欄位，如果是「以物件為主」模式，則會多出物件 ID、案名、地址欄位（兩種模式由 JGB 後台設定、只能擇一）。
每一列有一個「歷程」欄位，可以點開查看這組帳號的金額變動紀錄；有編輯權限的成員，最右邊還會多一欄操作選單。
團隊是「以物件為主」模式時，列表才會顯示這個物件的物件 ID、案名跟地址。
租客匯款到固定虛擬帳號時，系統會自動把金額加進「餘額」；另外在新增／編輯視窗也可以手動輸入修改餘額（不能小於 0）。
### 固定虛擬帳號要怎麼刪除？（列表操作選單選「刪除」，跳出確認視窗後才會真的刪掉） {#jgb/E/recharge-account-delete}
- phrasings:
  - {text: "虛擬帳號刪除流程", source: "draft:outline-20260920", status: proposed}
  - {text: "刪除虛擬帳號要確認嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "刪除虛擬帳號失敗", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/rechargeAccountList/Index.vue, code:app/Http/Controllers/RechargeAccountListController.php]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
有編輯固定虛擬帳號權限的成員，在「固定虛擬帳號管理」列表每一列右邊的操作選單裡有「編輯」跟「刪除」兩個選項；沒有這個權限就看不到操作選單。
點「刪除」會先跳出確認視窗，顯示這組虛擬帳號的租客姓名跟帳號，需要再按一次「刪除」才會真的刪除；按「取消」可以中止。
刪除成功後畫面會提示「已刪除」，並重新整理列表；如果刪除失敗，會顯示對應的錯誤訊息。
### 點開「歷程」看得到哪些內容？（每筆金額變動的時間／類型／金額／前後餘額／操作人員，有連結帳單可以點開查看） {#jgb/E/recharge-account-history-content}
- phrasings:
  - {text: "歷程看得到什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "金額變動歷程內容", source: "draft:outline-20260920", status: proposed}
  - {text: "歷程能看帳單嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/rechargeAccountList/Index.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
點開「歷程」會列出這組虛擬帳號每一筆金額變動紀錄，包含時間、類型、變動金額、變動前餘額、變動後餘額、操作人員。
如果這筆金額變動有連結到某張帳單，該列會多一個「帳單」圖示，點下去可以疊加開啟這張帳單的詳細資料，不用關掉歷程視窗。
如果目前還沒有任何歷程記錄，會顯示「目前尚無歷程記錄」。
### 固定虛擬帳號可以選哪些銀行？（聯邦、中國信託有專屬的建號流程，其餘從系統銀行清單選） {#jgb/E/recharge-account-bank-support}
- phrasings:
  - {text: "虛擬帳號支援哪家銀行", source: "draft:outline-20260920", status: proposed}
  - {text: "聯邦虛擬帳號", source: "draft:outline-20260920", status: proposed}
  - {text: "中信虛擬帳號", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號銀行清單", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/rechargeAccountList/Index.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
新增虛擬帳號時「銀行」欄位是從系統銀行清單挑選。
選到銀行代碼 803（聯邦）時，會切換成「填金額、由系統取號」的建號模式。
選到銀行代碼 822（中國信託）時，畫面會改成用識別碼直接算出帳號的方式。
### 聯邦（803）虛擬帳號怎麼建立？有什麼限制？（金額鎖在帳號裡，租客月租變動要重新建一組） {#jgb/E/recharge-account-ubot-flow}
- phrasings:
  - {text: "聯邦虛擬帳號怎麼建", source: "draft:outline-20260920", status: proposed}
  - {text: "聯邦虛擬帳號綁定金額", source: "draft:outline-20260920", status: proposed}
  - {text: "聯邦虛擬帳號金額改了怎麼辦", source: "draft:outline-20260920", status: proposed}
  - {text: "聯邦虛擬帳號匯錯金額", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/rechargeAccountList/Index.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
建立聯邦虛擬帳號要先填「綁定金額」，再按「產生帳號」才能取得系統配發的固定式虛擬帳號；沒有先產生帳號無法送出新增。
聯邦的虛擬帳號會把金額鎖在帳號裡，一組帳號只能收這個金額，租客匯錯金額時，銀行在 ATM 當下就會直接擋下來。
之後如果這位租客的月租有變動，原本這組帳號就會失效，必須重新建立一組新的給他。
### 中國信託（822）虛擬帳號怎麼算出帳號？（填企業識別碼 5 碼與繳款人識別碼 8 碼由系統計算） {#jgb/E/recharge-account-ctbc-flow}
- phrasings:
  - {text: "中信虛擬帳號怎麼算", source: "draft:outline-20260920", status: proposed}
  - {text: "企業識別碼幾碼", source: "draft:outline-20260920", status: proposed}
  - {text: "繳款人識別碼幾碼", source: "draft:outline-20260920", status: proposed}
  - {text: "中信虛擬帳號計算機", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/rechargeAccountList/Index.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
新增虛擬帳號時選到中國信託（822），會出現「企業識別碼」（5 碼）與「繳款人識別碼」（8 碼）兩個欄位，系統會用這兩組數字直接算出對應的虛擬帳號；編輯既有的虛擬帳號時不會出現這兩個欄位。
### 虛擬帳號建立後，銀行跟帳號可以改嗎？（不行，銀行跟帳號建立後不能改；可以改餘額，以及依團隊模式改租客資料或綁定物件） {#jgb/E/recharge-account-immutable}
- phrasings:
  - {text: "虛擬帳號可以改銀行嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號可以改帳號嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "編輯虛擬帳號能改什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號要換銀行怎麼辦", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/rechargeAccountList/Index.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
編輯虛擬帳號時，「銀行」跟帳號欄位都是唯讀的，建立後就不能修改。
編輯時可以改的是餘額；團隊的固定虛擬帳號是「以人為主」模式時，還可以改租客姓名、Email、手機號碼，是「以物件為主」模式時，則可以改綁定的物件。
「以人為主」模式下，如果租客的手機號碼、Email 或姓名有異動，直接在編輯視窗更新這些欄位即可，不需要重新建立整組虛擬帳號。
如果需要更換銀行或帳號，唯一的方式是先把這組虛擬帳號刪除，再重新建立一組新的；畫面上也直接提示「銀行與帳號建立後不可修改，如需變更請刪除後重新建立」
### 虛擬帳號綁定物件時，輸入物件 ID 有什麼驗證？ {#jgb/E/recharge-account-estate-binding-validation}
- phrasings:
  - {text: "虛擬帳號綁定物件ID", source: "draft:outline-20260920", status: proposed}
  - {text: "物件ID驗證失敗", source: "draft:outline-20260920", status: proposed}
  - {text: "物件不屬於這個團隊", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號選擇物件按鈕", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/rechargeAccountList/Index.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在虛擬帳號綁定物件時輸入物件 ID，如果 ID 不是有效格式，會提示「請輸入有效的物件 ID」。
如果物件 ID 存在但不屬於目前登入的團隊，會提示「物件不存在或不屬於此團隊」，驗證通過後才會帶出案名跟地址讓你確認。
驗證通過後畫面會顯示這個物件的案名跟地址，讓操作者在送出前可以再次確認是不是要綁的那個物件。
除了直接輸入物件 ID，欄位旁邊還有一個「選擇物件」按鈕，點下去會先把目前編輯中的表單內容暫存起來，再跳轉到物件挑選頁面讓使用者用搜尋/瀏覽的方式選物件，選好後會自動帶回物件 ID。
### 「固定虛擬帳號管理」的「報表匯出」匯出什麼？（指定日期區間內租客匯入的入帳明細 Excel） {#jgb/E/recharge-account-export}
- phrasings:
  - {text: "虛擬帳號怎麼匯出", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號匯出明細", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號匯出日期區間", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/rechargeAccountList/Index.vue, code:app/Http/Controllers/RechargeAccountListController.php]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「固定虛擬帳號管理」的「報表匯出」要先選「起始日期」跟「結束日期」，任一個日期沒填或起始日期晚於結束日期都會被擋下不能匯出。
匯出的是指定日期區間內租客匯款入帳（「租客匯入」）的明細，不是虛擬帳號列表；檔案是 Excel（.xlsx），檔名會帶入「固定虛擬帳號匯入明細」跟指定的起訖日期。
匯出時預設會帶入本月第一天到今天當作日期區間，可以再自行調整成需要的區間。
### 固定虛擬帳號的入帳是怎麼自動比對到帳單的？（入金當下即時銷帳，另有每日凌晨 03:00 排程再比對；限特定合作團隊；餘額不夠不會變成已到帳） {#jgb/E/recharge-account-daily-settlement}
- phrasings:
  - {text: "固定虛擬帳號自動到帳", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號入帳幾點處理", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號沖銷排程", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Console/Kernel.php, code:app/Console/Commands/BillRechargeAccount.php, code:app/RechargeAccount.php]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客匯款進固定虛擬帳號、餘額增加的當下，系統就會立刻把這組帳號可以沖銷的待付帳單標記為「已到帳」；另外每天凌晨 03:00 還有一個排程，用同樣的規則再比對一次。
這個自動比對（入金當下與每日排程都一樣）只會處理特定合作團隊的帳單，其他團隊的固定虛擬帳號帳單不會被自動比對，仍要靠人工對帳。
如果虛擬帳號的餘額不夠支付某張帳單，這張帳單會維持原本的「應到帳」狀態，不會被標記成「已到帳」；排程之後每天還會再重新比對一次。
### 退押金這類要付給租客的帳單，也走固定虛擬帳號嗎？（不會，顯示的是租客本人的收款帳戶） {#jgb/E/recharge-account-refund-excluded}
- phrasings:
  - {text: "退押金走虛擬帳號嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "支出帳單收款帳戶", source: "draft:outline-20260920", status: proposed}
  - {text: "退款方向虛擬帳號", source: "draft:outline-20260920", status: proposed}
- sources: [docs:knowledge/jgb-product-facts.md#p914-refund-bill-account]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
收款方是租客本人的支出帳單（例如退押金），畫面顯示的是租客本人的收款銀行帳戶，不會使用「固定虛擬帳號管理」裡設定的帳號；固定虛擬帳號只用在租客要繳款給業者的方向。
### 「固定虛擬帳號管理」跟租客線上繳費取得的 ATM 虛擬帳號是同一種嗎？（不是，線上繳費的 ATM 帳號是依單張帳單單筆取號，藍新取號的效期為 180 天） {#jgb/E/recharge-account-vs-single-use-atm}
- phrasings:
  - {text: "ATM虛擬帳號跟固定虛擬帳號差在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "線上繳費ATM虛擬帳號效期", source: "draft:outline-20260920", status: proposed}
  - {text: "固定虛擬帳號跟單筆ATM帳號一樣嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/RechargeAccountListController.php, code:app/Http/Controllers/BillController.php, code:app/Payment.php, docs:knowledge/jgb-product-facts.md#p914-newebpay-atm-expiry]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
不是同一種。
「固定虛擬帳號管理」列表裡管理的，是團隊名下、綁在租客或物件上、帶有餘額的固定虛擬帳號。
租客在帳單上線上繳費、選 ATM 轉帳時取得的虛擬帳號，是針對這一張帳單單筆取號產生的，帳號資訊記在這張帳單的付款紀錄上；它不是固定虛擬帳號，也不會出現在「固定虛擬帳號管理」列表裡。
藍新取號的 ATM 虛擬帳號效期是 180 天；效期內再選 ATM 轉帳會顯示同一組帳號，已過效期或還沒取過號就會重新取一組新的。
### 租客重複匯款時系統怎麼處理？（國泰世華單筆帳單 ATM 帳號已付款後重複匯入會略過；固定虛擬帳號多匯的部分留在儲值餘額） {#jgb/E/recharge-account-mismatch-and-duplicate}
- phrasings:
  - {text: "虛擬帳號重複匯款", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號多匯的錢去哪", source: "draft:outline-20260920", status: proposed}
  - {text: "重複匯款會重複入帳嗎", source: "draft:outline-20260920", status: proposed}
- sources: [docs:knowledge/jgb-product-facts.md#p914-duplicate-remittance, code:app/Payment.php, code:app/RechargeAccount.php, code:app/Services/Payment/SinopacVaNotifyService.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
如果匯到國泰世華單筆帳單 ATM 帳號的這筆帳單已經付款完成，租客又重複匯款進來，系統只會在內部記錄這筆訂單已被處理並略過，不會再沖到任何帳單。
匯到固定虛擬帳號的錢會先進這組帳號的儲值餘額；只有後台開通自動對帳的部分特定合作團隊，系統才會用餘額自動銷帳、多匯的部分留作餘額抵扣後續帳單，其他團隊的餘額不會自動抵帳單。
同一筆銀行入帳通知重複收到時，系統會用指紋比對去重，不會重複儲值。
### 逾期的虛擬帳號能不能重新產生？（此操作需由 JGB 客服協助，業者端沒有自助入口） {#jgb/E/recharge-account-regenerate-expired}
- phrasings:
  - {text: "逾期虛擬帳號重新產生", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號過期怎麼辦", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號重發", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/rechargeAccountList/Index.vue, docs:.kiro/specs/knowledge-outline-and-intent-architecture/inputs/review-sheet-9.15-S2-DE-20260927.md#93]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
虛擬帳號逾期需要重新產生時，業者端目前沒有自助重新產生的入口，此操作需由 JGB 客服協助。
## 線上金流收款帳號開通（藍新、中信；入口在「線上智能整合收款」頁的「開通帳號」） {#E-payment-onboarding}
### JGB 支援哪些收款金流？身分限制是什麼？（國泰世華／永豐銀行／中國信託／藍新／愛金卡；個人房東不能開通藍新、國泰世華、永豐銀行） {#jgb/E/payment-gateway-options}
- phrasings:
  - {text: "支援哪些收款金流", source: "draft:outline-20260920", status: proposed}
  - {text: "個人房東可以用哪個金流", source: "draft:outline-20260920", status: proposed}
  - {text: "國泰世華可以申請嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "永豐銀行金流申請", source: "draft:outline-20260920", status: proposed}
- sources: [help:paymentapply_zh-Hant.html, code:app/Http/Controllers/UserController.php, code:app/Payment.php]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
JGB 的線上收款金流有國泰世華、永豐銀行、中國信託、藍新 NewebPay 與愛金卡。
個人房東不能開通藍新、國泰世華、永豐銀行，選項會顯示「您無法開通此收款方式，若有問題請洽詢JGB客服」；團隊如果是免費方案或體驗方案，則不能開通國泰世華與永豐銀行。
中國信託的租客必須有中信帳戶，並透過中信 APP 繳費，申請前建議先確認租客是否方便使用。
### 各家收款金流的申請費用跟入帳帳戶限制是什麼？（國泰世華／永豐銀行首次設定費 5,000 元且限本行帳戶；中國信託／藍新線上申請不收申請費、可指定任一實體帳戶） {#jgb/E/payment-gateway-fees}
- phrasings:
  - {text: "金流申請要收費嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "首次設定費多少", source: "draft:outline-20260920", status: proposed}
  - {text: "入帳帳戶有限制嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "國泰世華入帳帳戶", source: "draft:outline-20260920", status: proposed}
- sources: [help:paymentapply_zh-Hant.html, code:src/pages/users/payment/_parts/Newebpay.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
國泰世華、永豐銀行是自行向銀行申請，兩者都有「首次設定費 5,000 元」；中國信託、藍新 NewebPay 是在 JGB 系統線上申請，申請本身不收費。
入帳帳戶也有限制：國泰世華只能匯入國泰世華的實體帳戶，永豐銀行只能匯入永豐銀行的實體帳戶；中國信託跟藍新則可以指定任一實體帳戶收款。
藍新的款項會先留在藍新帳戶中，要自行登入藍新後台辦理提款，前 5 次免費，之後每次收取 10 元。
藍新的交易手續費，開通畫面的條款寫明「費率以藍新科技股份有限公司本服務會員系統公告為依據」。
### 開通藍新智付通前要準備什麼？（申請表要自填 09 開頭的台灣手機號碼） {#jgb/E/newebpay-precondition}
- phrasings:
  - {text: "藍新開通前提條件", source: "draft:outline-20260920", status: proposed}
  - {text: "藍新智付通手機號碼", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/UserController.php]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
開通藍新智付通時，管理者手機號碼是在申請表上自行填寫，必須是 09 開頭、共 10 碼的台灣手機號碼；系統不再檢查帳號原本綁定的手機號碼。
### 開通藍新智付通前，團隊要先填完哪些資料？（個人房東不能開通藍新） {#jgb/E/newebpay-required-fields}
- phrasings:
  - {text: "藍新開通要先填什麼資料", source: "draft:outline-20260920", status: proposed}
  - {text: "個人房東可以開藍新嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "公司統編沒填能開藍新嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/UserController.php, code:src/pages/users/payment/routerView/Add.vue, code:src/mixin/methods.js, code:config/role.php]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
個人房東在現行收款設定頁不能開通藍新，選了只會看到「您無法開通此收款方式」的提示，若有問題要洽詢 JGB 客服。
團隊帳號則要先填好公司統編、公司名稱、公司地址（縣市、區、地址），法人房東團隊沒填完會被導回團隊頁面；管理者的手機號碼與 Email 改在申請表上填寫，不需要先在帳號上設定或驗證。
法人房東團隊被導回團隊頁面時，一樣會列出缺少的公司資料；社會住宅團隊沒填完時則不會被導回團隊頁面，而是在送出申請時顯示欄位錯誤訊息。
### 藍新開通時有哪些付款方式？（信用卡／Google Pay／Samsung Pay／ATM／超商代碼送出時都會開啟；國外卡要另外申請） {#jgb/E/newebpay-payment-methods}
- phrasings:
  - {text: "藍新支援哪些付款方式", source: "draft:outline-20260920", status: proposed}
  - {text: "超商代碼繳費金額限制", source: "draft:outline-20260920", status: proposed}
  - {text: "國外卡要另外申請嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "藍新付款方式預設開哪些", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/UserController.php, docs:knowledge/jgb-product-facts.md#p914-credit-installment, code:config/rolepayment.php, code:src/pages/users/payment/_parts/Newebpay.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
藍新開通畫面列出「信用卡」「Google Pay」「Samsung Pay」「ATM」「超商代碼」五種付款方式；開通送出時這五種一律以開啟送出，畫面上的勾選目前不會改變送出的設定。
開通畫面上沒有「國外卡」選項。
超商代碼有付款金額限制，畫面上會提示付款金額有 TWD 30 到 TWD 20,000 的限制。
「國外卡」如果需要開通，要另外透過 JGB 向藍新金流申請，耗時約 5 到 7 個工作天。
### 中國信託收款怎麼申請？（中信轉帳 Pay 填資料送審，ACH 驗證約 5 個工作天；中信虛擬帳號填 5 碼企業代碼即可，個人房東不能開通） {#jgb/E/ctbc-apply-flow}
- phrasings:
  - {text: "中信轉帳Pay怎麼申請", source: "draft:outline-20260920", status: proposed}
  - {text: "中信金流審核多久", source: "draft:outline-20260920", status: proposed}
  - {text: "中信收款帳號開通流程", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/UserController.php, code:src/pages/users/payment/_parts/Ctbc.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
中國信託轉帳 Pay 是在系統上填寫身分證字號/統一編號、聯絡電話、收款銀行代碼與名稱、戶名、銀行帳號後送出申請。
中信轉帳 Pay 送出後不是馬上生效，會由 JGB Smart 進行 ACH 驗證並撥款 1 元到收款帳號，審核時間需 5 個工作天（不含例假日）。
如果欄位驗證失敗，畫面會列出驗證錯誤訊息，修正後再送出即可。
另外也可以申請「中信虛擬帳號」，只要填 5 碼的虛擬帳號企業代碼，不需要經過上面的 ACH 審核等待；但個人房東不能開通中信虛擬帳號，畫面會顯示「您無法開通此收款方式，若有問題請洽詢JGB客服」
### 中國信託申請表單各欄位有什麼格式限制？（聯絡電話 10 碼、銀行代碼 3 碼） {#jgb/E/ctbc-form-validation}
- phrasings:
  - {text: "中信申請表單欄位限制", source: "draft:outline-20260920", status: proposed}
  - {text: "聯絡電話要幾碼", source: "draft:outline-20260920", status: proposed}
  - {text: "銀行帳號要幾碼", source: "draft:outline-20260920", status: proposed}
  - {text: "銀行代碼幾碼", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/UserController.php, code:src/pages/users/payment/_parts/Ctbc.vue, code:src/pages/users/payment/routerView/Add.vue, code:routes/web.php]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
聯絡電話必須剛好 10 碼數字。
銀行代碼必須剛好 3 碼數字。
銀行帳號欄位最多只能填 14 碼數字，至少要 10 碼；不足 16 碼系統會自動在前面補 0。
### 各家金流的款項要怎麼提領？（藍新要自己登入後台辦理，前 5 次免費之後每次 10 元） {#jgb/E/payment-gateway-withdrawal}
- phrasings:
  - {text: "藍新款項怎麼提領", source: "draft:outline-20260920", status: proposed}
  - {text: "藍新提款手續費", source: "draft:outline-20260920", status: proposed}
  - {text: "收到的錢在哪裡領", source: "draft:outline-20260920", status: proposed}
- sources: [help:paymentapply_zh-Hant.html, docs:.kiro/specs/knowledge-outline-and-intent-architecture/inputs/review-sheet-9.15-S2-DE-20260927.md#47]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
藍新的款項會先留在藍新帳戶中，需要自行登入藍新後台辦理提款，前 5 次免費，之後每次收取 10 元手續費。
藍新提款是在藍新自己的後台辦理，不是在 JGB 系統內操作。
國泰世華、永豐銀行、中國信託的提領方式與審核工作天，請洽客服。
### 線上金流收款會不會有稅務申報風險？（屬稅捐機關與業者自身規劃，系統不判斷） {#jgb/E/payment-onboarding-tax-risk}
- phrasings:
  - {text: "金流收款稅務風險", source: "draft:outline-20260920", status: proposed}
  - {text: "線上收款要報稅嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "資金流向申報", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/UserController.php, docs:.kiro/specs/knowledge-outline-and-intent-architecture/inputs/review-sheet-9.15-S2-DE-20260927.md#102]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
線上金流收款的資金運用是否涉及稅務申報風險，屬稅捐機關與業者自身的稅務規劃，系統不判斷。
### 「現金收款帳戶」怎麼管理？（可以新增、編輯、移除；需要收款設置編輯權限） {#jgb/E/cash-payment-account-management}
- phrasings:
  - {text: "現金收款帳戶怎麼設定", source: "draft:outline-20260920", status: proposed}
  - {text: "現金收款帳戶可以刪除嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "常用收款帳戶管理", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/payment/_parts/CashBanks.vue, code:src/components/Lightbox/PaymentCashBanksDelete.vue, code:src/pages/users/payment/routerView/Index.vue]
- reviewed: {by: owner, at: 2026-09-27}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
收款設定頁上有一個「現金收款帳戶」區塊，可以用「新增現金帳戶」建立金融帳戶資料，之後編輯每份合約時會自動帶入合約的收款訊息；沒有收款設置編輯權限的帳號不能新增或修改。
已經建立的現金收款帳戶可以「編輯帳戶」或「移除帳戶」；移除時會先跳出確認視窗，提示刪除後未來簽約時就不能再選這個帳戶當收款帳戶，但不影響過去已成立的合約，按下「刪除」後才會移除。
