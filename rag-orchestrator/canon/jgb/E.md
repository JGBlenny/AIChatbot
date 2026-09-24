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
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
草稿帳單可以「編輯帳單」修改內容。
草稿帳單可以「發送帳單」，送出後轉為應到帳狀態通知對象繳費。
草稿帳單也可以直接「移至已到帳」，略過發送、直接視為已收款。
草稿帳單可以「封存帳單」。
「合併帳單」動作目前只提供給特定合作團隊使用。
在「草稿帳單」分頁勾選一筆以上帳單後，批次操作列會多出「批次預覽編輯」，可以把勾選的帳單（或用全選連同篩選條件一起送出）一次性帶入批次編輯的預覽視窗調整費用內容。
### 「排定發送」狀態的帳單可以做哪些動作？（只有「取消排定發送」） {#jgb/E/bill-actions-scheduled}
- phrasings:
  - {text: "排定發送可以取消嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "取消排定發送", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「排定發送」狀態的帳單，齒輪選單只有一個「取消排定發送」的動作。
### 「封存」狀態的帳單可以做哪些動作？（沒有任何動作，齒輪選單是空的） {#jgb/E/bill-actions-archived}
- phrasings:
  - {text: "封存的帳單能做什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "封存後還能操作嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
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
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
應到帳的收款帳單，如果不是走自動收款，齒輪選單會顯示「匯款資訊」讓房東查看匯款帳戶。
應到帳的收款帳單一律可以「移至已到帳」或「取消帳單」；「開立發票」則要這張帳單所屬合約有設定自動開立發票、帳單本身也設定自動開立發票、且發票狀態還沒到「已完成」時才會出現，不是每一張應到帳帳單都看得到。
### 「待對帳」狀態的收款帳單可以做哪些動作？（退至應到帳／移至已到帳／開立發票，沒有取消帳單） {#jgb/E/bill-actions-progress}
- phrasings:
  - {text: "待對帳可以做什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "退至應到帳", source: "draft:outline-20260920", status: proposed}
  - {text: "待對帳能取消嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
待對帳狀態的收款帳單一律可以「退至應到帳」或「移至已到帳」，選單裡不會有「取消帳單」；「開立發票」的顯示條件跟應到帳狀態相同（合約設定自動開立發票、帳單本身設定自動開立發票、且發票尚未完成），不是每一張待對帳帳單都看得到。
### 「已到帳」狀態的收款帳單可以做哪些動作？（收款備註／發票／收據／退款對帳單） {#jgb/E/bill-actions-received}
- phrasings:
  - {text: "已到帳能做什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "重開發票", source: "draft:outline-20260920", status: proposed}
  - {text: "作廢發票", source: "draft:outline-20260920", status: proposed}
  - {text: "收款備註怎麼改", source: "draft:outline-20260920", status: proposed}
  - {text: "退款對帳單", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
已到帳的收款帳單可以「編輯收款備註」。
已到帳的收款帳單，如果帳單本身有設定自動開立發票、且已經產生發票，齒輪選單裡會列出對應的「發票」按鈕（一張以上會依張數編號），點下去可以打開對應的發票連結；已經作廢的那張後面會加註「（已作廢）」。
已到帳的收款帳單一律可以看到「收據」。
只有這張帳單本身是反轉帳單（房東退款給租客）時，齒輪選單才會多出「退款對帳單」。
已到帳的收款帳單只要本身有設定自動開立發票，就會常駐顯示「重開發票」，不論目前發票狀態為何。
只有在這張帳單有已開立且未作廢的發票時，齒輪選單才會出現「作廢發票」。
已到帳的收款帳單一律可以「封存帳單」。
### 「應支出」狀態的支出帳單，房東跟租客各能做什麼？（房東：前往付款／通知已匯款／取消帳單；租客：付款） {#jgb/E/bill-actions-expense-unpaid}
- phrasings:
  - {text: "應支出可以做什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "租客怎麼付款", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
應支出的支出帳單，房東端可以「前往付款」「通知已匯款」或「取消帳單」；租客端則只看到「付款」。
### 「待對帳」狀態的支出帳單，房東跟租客各能做什麼？（房東：前往付款／通知已匯款／取消帳單；租客：沒有齒輪動作） {#jgb/E/bill-actions-expense-unconfirmed}
- phrasings:
  - {text: "待對帳支出帳單", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
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
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
帳單列表的關鍵字搜尋可以指定用「案名」「地址」「租客」「ID」「手機」「信箱」「帳單名稱」「虛擬帳號」或「合約帳單」共 9 種其中一種去比對。
關鍵字搜尋框旁邊有下拉選單，可以先選要用哪一種條件（例如案名、租客、虛擬帳號）去比對，再輸入關鍵字查詢。
預設是用「案名」去比對輸入的關鍵字。
### 帳單總表怎麼匯出？（要先勾選帳單才會出現匯出選項；全選走篩選條件、勾選部分筆數走ID清單；其他分頁另有一套匯出流程） {#jgb/E/bill-list-export}
- phrasings:
  - {text: "帳單怎麼匯出", source: "draft:outline-20260920", status: proposed}
  - {text: "匯出帳單上限", source: "draft:outline-20260920", status: proposed}
  - {text: "匯出帳單要先勾選嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "全選匯出跟勾選匯出差在哪", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
帳單總表沒有一個隨時可以按的「匯出帳單」按鈕，只有在左側核取方塊勾選帳單（或用表頭「全選」）之後，上方才會跳出批次動作列，裡面才有「匯出帳單」這個選項。
如果是用表頭「全選」核取方塊整批勾選（連同尚未載入的其他頁一起選），按「匯出帳單」會依照目前畫面上的篩選條件匯出整批帳單；如果只是勾選畫面上看到的幾筆（沒有按全選），匯出改成只匯出這幾筆勾選的帳單。
匯出筆數超過系統上限時會直接擋下，並提示匯出筆數超過上限、請縮小搜尋範圍後再試，不會只匯出部分結果。
帳單總表的批次操作列要有匯出帳單的權限才會出現「匯出帳單」選項；「草稿帳單」「收款帳單」分頁勾選帳單後，批次操作列也會出現同樣勾選/全選邏輯的「匯出」選項，跟帳單總表共用同一套規則。
### 帳單總表勾選多筆不同狀態的帳單時，批次操作列會出現哪些動作？（只列出每一筆帳單都能做的共同動作） {#jgb/E/bill-list-bulk-action-intersection}
- phrasings:
  - {text: "勾選不同狀態的帳單能做什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單總表批次操作交集", source: "draft:outline-20260920", status: proposed}
  - {text: "混合狀態帳單批次動作", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
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
- sources: [code:src/use/config/useBillTypes.js]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「草稿帳單」跟「支出帳單」「總收支」分頁右上角一律有一個固定的「匯出」／「匯出帳單」按鈕，不需要先勾選任何一筆，按下去會另外開一個（較舊的）匯出視窗，跟帳單總表用勾選觸發的匯出是不同的流程。
### 「收款帳單」分頁固定的匯出按鈕，什麼時候會多出「匯出租客繳費證明」子選項？（只有身分類別為社會住宅的帳號才有） {#jgb/E/bill-list-income-export-social-housing}
- phrasings:
  - {text: "收款帳單怎麼匯出", source: "draft:outline-20260920", status: proposed}
  - {text: "匯出租客繳費證明", source: "draft:outline-20260920", status: proposed}
  - {text: "社會住宅匯出證明", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js, code:app/Role.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「收款帳單」分頁右上角固定有一個「匯出帳單」按鈕，只要帳號的身分類別（收費規則類型）有設定值就會顯示——一般房東帳號（個人／法人／社會住宅）身分類別必定有值，等同於一律會顯示，不是只有特定帳號才有。
只有身分類別是「社會住宅」的帳號，這顆固定匯出按鈕才會多一個子選項「匯出租客繳費證明」；其他身分類別的帳號沒有這個子選項。
### 「應到帳」「已到帳」狀態，特定合作團隊的帳號會多出哪些按鈕？（應到帳：匯入發票；已到帳：匯出收據／匯入收據／批次匯出收據） {#jgb/E/bill-list-special-team-cvs-buttons}
- phrasings:
  - {text: "匯入發票在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "匯出收據", source: "draft:outline-20260920", status: proposed}
  - {text: "批次匯出收據", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
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
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
一般帳號在「草稿帳單」分頁右上角「新增帳單」按鈕旁邊，預設會有「新增週期帳單」「新增批次帳單」「排定發送帳單」「批次編輯帳單」四個快捷選項可以選；「帳單總表」分頁沒有「新增帳單」按鈕，也沒有這些快捷選項。
「新增批次帳單」會先讓房東挑選多位租客（合約），再一次建立多張帳單。
「新增週期帳單」會先讓房東挑選多個物件，用來建立會依週期重複產生的帳單。
「批次編輯帳單」預設會開啟匯入試算表的視窗，讓房東批次調整帳單內容；但對某些特定合作團隊的帳號會改開另一個專用視窗（可篩選範圍、整批品項金額一起編輯）。
另一組特定合作團隊的帳號，右上角的快捷選項只會顯示「新增批次帳單」一項；還有一組特定合作團隊的帳號，快捷選項會多一個「Excel新增帳單」，可以用 Excel 檔案批次新增帳單。
### 「排定發送帳單」有什麼限制？（只有度數填完的帳單才能排，每天中午 12 點統一發送） {#jgb/E/bill-scheduled-send-rule}
- phrasings:
  - {text: "排定發送帳單怎麼用", source: "draft:outline-20260920", status: proposed}
  - {text: "排定發送限制", source: "draft:outline-20260920", status: proposed}
  - {text: "水電度數沒填能排定發送嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單幾點統一發送", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/pick/Index.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
排定發送帳單要先在挑選頁面選好要排定的帳單。
只有已經填寫完，或本來就沒有水電、瓦斯度數細節要填的帳單，才能執行批次排定發送。
系統會在每天中午 12:00 把選取的帳單統一發送給租客。
「租客免註冊合約」下的帳單不適用排定發送這個功能。
### 帳單通知信裡的連結點進去會看到什麼？（單張帳單以彈窗顯示，不會跳到完整列表） {#jgb/E/bill-single-notification-deeplink}
- phrasings:
  - {text: "帳單連結點進去", source: "draft:outline-20260920", status: proposed}
  - {text: "通知信帳單連結", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單不存在會怎樣", source: "draft:outline-20260920", status: proposed}
  - {text: "單張帳單彈窗", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/BillController.php, code:resources/views/bills/one.blade.php, code:src/pages/bills/list/Index.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
帳單通知信或系統通知裡帶的單張帳單連結，點進去是用彈出視窗顯示這一張帳單的明細，不是完整的帳單列表頁。
如果連結指到的帳單已經不存在，透過網址直接進入時會被導回帳單列表，並提示「該帳單不存在」。
如果之後在同一個分頁自己重新送出進階搜尋條件，這個通知帶進來的單筆帳單鎖定就會被清除，回到一般的列表篩選。
### 「總收支」分頁的用途是什麼？（同時看全部已到帳、已支出、應到帳、應支出的帳單） {#jgb/E/bill-balance-tab}
- phrasings:
  - {text: "總收支分頁", source: "draft:outline-20260920", status: proposed}
  - {text: "收支總覽在哪看", source: "draft:outline-20260920", status: proposed}
  - {text: "總收支跟帳單總表差在哪", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useBillTypes.js]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「總收支」分頁底下分「全部」「已到帳」「已支出」「應到帳」「應支出」，可以在同一個分頁把收款帳單跟支出帳單放在一起看。
「總收支」分頁跟「帳單總表」不同：總收支只列收款/支出這幾個狀態的帳單，帳單總表是列出全部帳單不分狀態。
「總收支」分頁裡「已到帳」「已支出」「應到帳」「應支出」這四個狀態頁籤都有本頁小計功能，因為金額欄顯示的是「這張帳單在本分頁那一邊的金額」，所以才需要本頁小計，跟上方彙總卡片的數字對得起來；「全部」頁籤本身沒有這個小計。
## 建立與編輯帳單（單筆、批次、週期批次） {#E-bill-create-edit}
### 新增帳單有哪幾種頁面？（新增帳單／新增批次帳單／新增週期帳單／編輯帳單） {#jgb/E/bill-create-modes}
- phrasings:
  - {text: "新增帳單有幾種", source: "draft:outline-20260920", status: proposed}
  - {text: "批次帳單跟週期帳單差在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼新增帳單", source: "draft:outline-20260920", status: proposed}
  - {text: "編輯帳單在哪", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/_parts/BillBasicInfoSection.vue]
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
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
新增帳單時「對象」下拉可以選「租客」「大房東」「物件」「其他」四種身分。
切換對象後，付款方式與收款帳戶會先清空，再依新選的對象重新帶入預設值。
對象選「租客」時，會依所選的合約帶出該合約的簽約資訊（法人約顯示公司名）；對象選「大房東」則是從『目前所選物件』的大房東名單裡挑一位——這份名單是依所選物件即時查詢帶出的，不是整個團隊共用同一份大房東名單，換一個物件、可選的大房東也會跟著換。
### 「新增批次帳單」跟「新增週期帳單」有什麼不同？（挑租客合約 vs 挑物件） {#jgb/E/bill-batch-vs-cycle}
- phrasings:
  - {text: "批次帳單跟週期帳單差別", source: "draft:outline-20260920", status: proposed}
  - {text: "新增批次帳單怎麼選對象", source: "draft:outline-20260920", status: proposed}
  - {text: "新增週期帳單怎麼選物件", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/_parts/BillTargetBatchBlock.jsx, code:src/use/config/useBillTypes.js]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
「新增批次帳單」的對象是「租客」，所以是先挑多個合約（租客），對每個合約各自建立一張帳單。
「新增週期帳單」的對象是「物件」，所以是先挑多個物件，用來建立會依週期重複產生的帳單。
批次帳單建立後，每位租客各自產生一張獨立的帳單，之後可以分別調整；週期帳單則是依照週期設定，之後依週期反覆自動產生新的帳單。
### 新增週期帳單的「繳費週期」設定要填哪些欄位？（繳費週期／繳費截止日／截止日設定／帳單週期制度） {#jgb/E/bill-cycle-schedule-fields}
- phrasings:
  - {text: "週期帳單怎麼設定", source: "draft:outline-20260920", status: proposed}
  - {text: "繳費週期選項", source: "draft:outline-20260920", status: proposed}
  - {text: "當月分算跟跨月計算差在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "提前截止同月截止", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/_parts/CycleBillingCycleFields.vue, code:src/utils/constants/contract.js]
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
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「總額（自動分攤）」欄位只出現在新增週期帳單頁面，而且團隊要開通社區投報率功能才會顯示。
「總額（自動分攤）」開啟後可以直接填一筆總金額，讓系統自動拆分到各期金額，不需要像預設模式一樣逐期分別填寫金額。
「總額（自動分攤）」的分攤方式是把填入的總金額平均分成各期，除不盡的零頭全部加在最後一期，不是依比例或依天數分攤。
### 帳單費用細目填寫有什麼規則？（度數欄位最多小數點後 2 位、電水瓦斯金額欄位限制小數點後 2 位、當期度數要大於上期度數） {#jgb/E/bill-fee-item-rules}
- phrasings:
  - {text: "費用細目怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "水電費當期度數錯誤", source: "draft:outline-20260920", status: proposed}
  - {text: "金額小數點限制", source: "draft:outline-20260920", status: proposed}
  - {text: "度數輸入錯誤提示", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/_parts/FeesBlock.jsx, code:src/components/PrefixInput.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
費用細目裡的「當期度數」「上期度數」欄位最多只能輸入到小數點後 2 位，超過會被自動截斷；金額欄位只有「電費」「水費」「瓦斯費」這三種項目會限制到小數點後 2 位，其他項目的金額欄位沒有這個限制。
水電這類用度數計費的項目，只有「當期度數嚴格小於上期度數」才會在小計欄下方顯示錯誤提示；當期度數等於上期度數（用電量 0 度）不會出現這個錯誤，即使錯誤文字寫的是『必須大於上期度數』。
這兩個驗證都是即時檢查：一邊輸入就會即時提示，不需要送出後才發現錯誤。
### 「帳單標題」最多可以輸入幾個字？（45 個字） {#jgb/E/bill-title-field}
- phrasings:
  - {text: "帳單標題字數上限", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單標題最多幾個字", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/_parts/BillBasicInfoSection.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「帳單標題」最多可以輸入 45 個字。
### 「帳單備註」最多可以輸入幾個字？（150 個字） {#jgb/E/bill-remark-field}
- phrasings:
  - {text: "帳單備註字數上限", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單備註最多幾個字", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/_parts/BillBasicInfoSection.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「帳單備註」最多可以輸入 150 個字。
### 「內部備註」最多可以輸入幾個字？誰看得到？（100 個字，僅供業者團隊成員查看／編輯，租客看不到） {#jgb/E/bill-internal-note-field}
- phrasings:
  - {text: "內部備註字數上限", source: "draft:outline-20260920", status: proposed}
  - {text: "內部備註誰看得到", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/_parts/BillBasicInfoSection.vue, code:src/pages/bills/edit/_parts/InternalNoteBlock.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「內部備註」最多可以輸入 100 個字，欄位上標示「僅供內部查看」，這個備註是僅供業者團隊成員查看／編輯的欄位，租客端看不到。
### 「內部備註」欄位在哪些頁面會出現？（只有「新增帳單」單筆跟「編輯帳單」有，批次／週期帳單頁面不顯示） {#jgb/E/bill-internal-note-visibility}
- phrasings:
  - {text: "內部備註在批次帳單有嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "內部備註在週期帳單有嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/_parts/BillBasicInfoSection.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「內部備註」欄位只會出現在「新增帳單」（單筆）跟「編輯帳單」頁面，「新增批次帳單」「新增週期帳單」不會顯示這個欄位。
即使是在「新增帳單」或「編輯帳單」頁面，「內部備註」欄位還要同時符合三個條件才會顯示：操作者不是租客身分、操作者不是大房東、而且這張帳單本身有「內部備註」這個能力（某些情況下帳單資料裡不會有內部備註這個能力，例如 B2B 對方付款的帳單）——三個條件都成立才會出現這個欄位。
### 新增帳單時付款方式跟收款帳戶一定要一起填嗎？（兩者要嘛都空、要嘛都填；固定虛擬帳號例外） {#jgb/E/bill-payment-method-account-pair}
- phrasings:
  - {text: "付款方式沒填會怎樣", source: "draft:outline-20260920", status: proposed}
  - {text: "收款帳戶沒選會怎樣", source: "draft:outline-20260920", status: proposed}
  - {text: "固定虛擬帳號付款方式", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/Index.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在「新增帳單」跟「新增批次帳單」，付款方式跟收款帳戶兩者都空著可以送出（沿用合約的收款設定）；但只填其中一項會被擋下，提示要完成付款方式與收款帳戶選擇。
選擇固定虛擬帳號當付款方式是例外：這個方式本來就沒有對應的收款帳戶欄位，所以不受兩者要成對填寫的規則限制。
這個成對檢查只發生在按下送出確認彈窗（送出點退不受影響）的當下，並不是每次改欄位就即時檢查。
### 租客還沒完成驗證時，發給他的帳單會怎樣？（帳單卡在草稿分頁，發不出去；但可以手動移至應到帳/已到帳） {#jgb/E/bill-tenant-unverified-draft-lock}
- phrasings:
  - {text: "租客沒驗證帳單發不出去", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單卡在草稿", source: "draft:outline-20260920", status: proposed}
  - {text: "租客驗證連結過期帳單", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單一直是草稿狀態", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/_parts/BillTargetBlock.jsx]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
如果租客的 Email 或手機都還沒完成驗證，系統會把帳單停留在草稿帳單分頁，等租客完成驗證或驗證連結過期後，才能真正發送帳單，避免租客收不到帳單通知。
在這個情況下，房東仍然可以手動把帳單直接由草稿移至應到帳或已到帳，不受驗證狀態限制。
這個限制只影響帳單能不能真正「發送」出去，帳單本身仍然可以照常建立、編輯內容。
### 新增帳單頁面下方送出按鈕的文字跟行為會依情境改變（送出／發送簽核／簽核中／預覽帳單） {#jgb/E/bill-submit-button-behavior}
- phrasings:
  - {text: "送出按鈕文字不一樣", source: "draft:outline-20260920", status: proposed}
  - {text: "發送簽核是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "簽核中按鈕", source: "draft:outline-20260920", status: proposed}
  - {text: "週期帳單預覽按鈕", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/Index.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
一般情況下按鈕文字是「送出」；如果這筆帳單設定要走簽核流程，按鈕文字會改成「發送簽核」，代表按下去是送進簽核而不是直接發帳單。
如果簽核正在處理中，按鈕會顯示「簽核中」。
新增週期帳單頁面，底部按鈕固定顯示「預覽帳單」，用來先產生本次週期會建立的帳單清單再確認。
一般情況下，底部主按鈕右邊還會有一個下拉選項「儲存草稿」，可以先把目前填寫的內容存成草稿，不用直接送出或走簽核；特定合作團隊的帳號、簽核處理中、或週期帳單預覽這幾種情境下，不會出現這個下拉選項。
### 新增帳單選租客當對象時，付款方式會自動帶入合約的收款設定嗎？（會，但帳戶已停用/不可取號等情況不會亂猜） {#jgb/E/bill-contract-payment-prefill}
- phrasings:
  - {text: "帳單付款方式自動帶入", source: "draft:outline-20260920", status: proposed}
  - {text: "新增帳單付款方式跟合約一樣", source: "draft:outline-20260920", status: proposed}
  - {text: "合約收款方式帶入帳單", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/edit/Index.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
只有「新增帳單」（單筆）在對象選租客時，才會依該租客合約的收款設定自動帶入付款方式與收款帳戶。
如果合約帶出來的帳戶已經停用、不可取號、是自訂現金或屬於舊制/儲值等不符合判準的情況，系統不會亂猜一個值，付款方式會維持未選。
這個自動帶入的機制只在對象是「租客」時才會啟動，選其他對象（大房東、物件、其他）不會嘗試帶入合約付款設定。
## 帳單統計與報表 {#E-bill-stats}
### 「統計報表」的「當前表現」分頁顯示什麼？（收款情況／支出情況卡片） {#jgb/E/bill-stat-overview}
- phrasings:
  - {text: "統計報表看什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "收款情況怎麼算", source: "draft:outline-20260920", status: proposed}
  - {text: "支出情況怎麼算", source: "draft:outline-20260920", status: proposed}
  - {text: "預計總收款是什麼", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/stat/Index.jsx, code:src/pages/bills/stat/_parts/Stat.jsx]
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
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「每月報表」分頁底下是「物件報表」，可以依社區、物件篩選後按「新增報表」上傳檔案。
「每月對帳單」分頁底下是「物件對帳單」，一樣可以篩選後按「新增對帳單」上傳。
選定的物件如果還沒有人上傳過報表，畫面會顯示「尚未上傳任何報表」。
「物件報表」要先選「社區」再選「物件」兩層下拉篩選，選定物件後才會抓這個物件的報表清單；如果選了社區但還沒選物件，畫面會用「尚未上傳任何報表」搭配「請選擇物件」提示，不是真的代表這個社區沒有任何報表。
### 「財務報表」（年度／每月）跟「統計報表」是不同頁面？（年度／每月收支總表；頁面上的「下載」目前沒有動作） {#jgb/E/bill-sheet-report-title}
- phrasings:
  - {text: "年度財務報表", source: "draft:outline-20260920", status: proposed}
  - {text: "每月財務報表", source: "draft:outline-20260920", status: proposed}
  - {text: "財務報表怎麼下載", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單報表在哪", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/sheet/Index.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「財務報表」跟前面「統計報表」的「當前表現」是不同頁面：網址沒有指定月份時標題顯示「年度財務報表」，網址有指定年月時標題顯示「每月財務報表」。
財務報表頁面右上角有「下載」字樣，但目前點了沒有任何動作。
報表下方依照開啟時的檢視方式（按物件或按項目）呈現不同的表格內容，頁面上沒有切換器。
### 財務報表可以用哪兩種方式檢視？（按物件檢視、按項目檢視） {#jgb/E/bill-sheet-two-views}
- phrasings:
  - {text: "財務報表按物件看", source: "draft:outline-20260920", status: proposed}
  - {text: "財務報表按項目看", source: "draft:outline-20260920", status: proposed}
  - {text: "收支小計怎麼看", source: "draft:outline-20260920", status: proposed}
  - {text: "已收入已支出分項", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/sheet/Index.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
財務報表依打開頁面時網址帶的參數決定顯示哪一種檢視：預設情況顯示「按物件」檢視，每個物件一列，最右邊有一欄「收支小計」加總這個物件全年（或該月）的收支。
如果網址帶特定參數指定要看「依項目統計」，則改顯示「按項目」檢視，這時會分別列出「已收入」跟「已支出」兩張表，各自依項目名稱、逐月呈現金額。
「按項目」檢視會用「已收入」跟「已支出」兩個色塊標籤區分兩張表格，方便分辨目前看的是收入項目還是支出項目。
### 財務報表上方的三張總計卡片是怎麼算的？（收入總計／支出總計／收支總計） {#jgb/E/bill-sheet-total-cards}
- phrasings:
  - {text: "財務報表收入總計", source: "draft:outline-20260920", status: proposed}
  - {text: "財務報表支出總計", source: "draft:outline-20260920", status: proposed}
  - {text: "收支總計怎麼算", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/sheet/Index.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
財務報表最上方會顯示「收入總計」「支出總計」「收支總計」三張卡片，「收支總計」＝收入總計－支出總計，反映該年度（或該月）的淨收支。
「按物件」檢視時，表格最後會多出一列「項目總計」，把所有物件的各項金額加總起來。
「按項目」檢視時，收入表跟支出表各自也會多一列「收入總計」或「支出總計」。
### 財務報表右上角的「下載」按鈕可以下載什麼？ {#jgb/E/bill-sheet-download-button}
- phrasings:
  - {text: "財務報表下載按鈕", source: "draft:outline-20260920", status: proposed}
  - {text: "財務報表怎麼匯出", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/bills/sheet/Index.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
財務報表頁面右上角有一個帶下載圖示的「下載」按鈕。
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
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在匯出歷史清單裡，只有排在最上面、還沒歸檔的那一筆紀錄旁邊會有「確定歸檔」的操作按鈕，按下去會跳出確認視窗「確定要歸檔嗎」。
確認視窗說明執行歸檔後，資料會同步至資料庫且無法修改，要繼續才按「確認」。
綠色帶勾勾圖示的「歸檔」標籤，只會在這筆紀錄已經完成歸檔之後才顯示；已經歸檔的紀錄，「確定歸檔」按鈕會保留在畫面上但變成無法點擊的停用狀態，不是完全消失，也沒有另外一個單獨叫「歸檔」的按鈕。
在「其餘筆」（非最新一筆）的歷史紀錄裡，如果這筆還沒歸檔，該列的表單欄位只會用文字＋頓號列出表單名稱，不會出現可以下載的按鈕；只有已經歸檔的紀錄，表單名稱才會變成可以點擊下載的按鈕。
## 差額發票（群組、底租、社區層開關） {#E-balance-invoice}
### 社區怎麼開啟差額發票功能？（社區編輯頁的開關，設定底租總額幣別與每月租金） {#jgb/E/balance-invoice-community-switch}
- phrasings:
  - {text: "怎麼開差額發票", source: "draft:outline-20260920", status: proposed}
  - {text: "社區差額發票開關", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票怎麼計算", source: "draft:outline-20260920", status: proposed}
  - {text: "底租總額怎麼設定", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/edit/BalanceInvoice.jsx]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
差額發票功能是在社區編輯頁用「是否開設差額發票」這個開關來開啟。
開啟後的說明文字是：當此社區下所有物件的每月總租金金額大於每月底租金額時，系統將自動開立差額發票。
開啟開關要填「底租總額」的幣別與每月租金金額；關閉開關時，幣別與金額欄位會被清空。
### 差額發票群組總表有哪些狀態？（尚未生效／進行中／歷史／封存） {#jgb/E/balance-invoice-group-statuses}
- phrasings:
  - {text: "差額發票群組狀態", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票群組總表", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票尚未生效", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票封存", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/utils/constants/balanceInvoices.ts, code:src/pages/balanceInvoices/list/_parts/ListTable.vue]
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
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
建立差額發票群組要填「群組名稱」，這是必填欄位。
要填「底租」金額，這是必填欄位。
要填「租期」起訖日期，這是必填欄位。
可以另外填「前期餘額」金額與結算日期。
還可以填「個人住宅所有權人」「房屋座落地址」「房屋稅籍編號」。
### 差額發票群組怎麼加入物件？每個物件的底租可以自訂嗎？（可開「自訂個別底租」分配群組底租） {#jgb/E/balance-invoice-pick-and-individual-rent}
- phrasings:
  - {text: "差額發票怎麼加物件", source: "draft:outline-20260920", status: proposed}
  - {text: "自訂個別底租", source: "draft:outline-20260920", status: proposed}
  - {text: "可分配租金是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "群組底租怎麼分配到每個物件", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/balanceInvoices/edit/pickEstates/Index.vue, code:src/pages/balanceInvoices/_parts/IndividualBaseRentSetting.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
差額發票群組要透過「請選擇物件」頁面挑選要加入群組的物件。
所屬物件可以開啟「自訂個別底租」，開啟後會顯示「可分配租金」，把整個群組的底租總額分配給各個物件，而不是全部物件共用同一個底租金額。
維持關閉「自訂個別底租」的物件，是用整個群組共用同一筆底租金額去計算差額。
「可分配租金」顯示的是這個群組的底租總額扣掉已經分配給其他物件之後，還剩下多少可以分給這個物件。
### 差額發票群組詳細頁面看得到什麼？（招租數量／本月應收金額／本月已收金額，以及三個分頁） {#jgb/E/balance-invoice-group-detail-tabs}
- phrasings:
  - {text: "差額發票群組詳細頁", source: "draft:outline-20260920", status: proposed}
  - {text: "招租數量是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "本月應收金額", source: "draft:outline-20260920", status: proposed}
  - {text: "差額總表在哪看", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/balanceInvoices/groups/Index.vue, code:src/pages/balanceInvoices/groups/_parts/ReportTable.vue]
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
- sources: [code:src/pages/balanceInvoices/groups/_parts/InvoiceTable.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
差額總表按月份列出這個群組每個月的累積成本、累積收入、差額，以及是否開發票、開立日期、發票金額、發票字軌。
還沒開發票的月份，「差額」欄位＝前期結轉（前期餘額）加上（當月收入 − 當月成本）；已經開立發票的月份，「差額」跟「發票金額」這兩欄改成顯示同一個發票開立時的實際金額，不再是重新計算出來的差額公式結果。
已經開立發票的月份會另外顯示發票的「開立日期」跟「發票字軌」。
### 差額發票什麼時候自動產生？（一般業者每月 1 日 03:00 開立上月發票；特定團隊另有自己的時程） {#jgb/E/balance-invoice-timing}
- phrasings:
  - {text: "差額發票何時開立", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票排程", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票狀態多久更新一次", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票每2小時", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Models/BalanceInvoiceGroup.php, code:app/Console/Kernel.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
除了一個特定合作團隊以外，其餘業者的差額發票由系統於每月 1 日凌晨 03:00 排程自動開立「上一個月」的差額發票。
那個特定合作團隊的時程不同：改成每月最後一天 23:30 直接開立「當月」發票，並在次月 1 日 03:05 依當下最新資料重新計算明細表（不是重印快照，讓月底才入帳的款項也能反映在報表上）。
差額發票群組的狀態（尚未生效／進行中／歷史）由每日凌晨 01:05 的排程更新一次；累積成本／累積收入則是每 2 小時更新一次。
### 差額發票群組列表的動作選單有哪些選項？各自什麼時候會被停用？（編輯群組／開立發票／封存群組／刪除群組；另有查看歷程圖示） {#jgb/E/balance-invoice-group-action-menu}
- phrasings:
  - {text: "差額發票群組怎麼刪除", source: "draft:outline-20260920", status: proposed}
  - {text: "差額發票群組動作選單", source: "draft:outline-20260920", status: proposed}
  - {text: "開立發票按鈕為什麼灰色", source: "draft:outline-20260920", status: proposed}
  - {text: "封存群組按鈕為什麼不能按", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/balanceInvoices/useBalanceInvoicesActions.ts, code:src/components/SurelyVue/BalanceInvoices/ActionsCell.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
差額發票群組列表跟群組詳細頁的動作選單裡固定有四個選項：「編輯群組」「開立發票」「封存群組」「刪除群組」。
「編輯群組」永遠可以點，會跳轉去編輯這個群組的基本資料。
「開立發票」只有在這個群組目前狀態是「進行中」、而且這個月還沒開過發票時才能點；已經開過發票，或群組不是進行中狀態，這個選項會顯示但無法點擊。
「封存群組」只要這個群組目前的狀態還不是「封存」就能點；已經是封存狀態時，這個選項會顯示但無法點擊。
「刪除群組」只有在這個群組本身允許刪除時才能點，否則顯示但無法點擊；能不能刪除是系統依群組狀態判定的。
動作選單旁邊另外有一個獨立的「查看歷程」圖示按鈕，不在下拉選單裡，點下去可以看這個群組的操作紀錄。
## 固定虛擬帳號管理（租客虛擬帳號、餘額、歷程） {#E-virtual-account}
### 「固定虛擬帳號管理」列表看得到哪些資訊？（帳號設定開啟時才有租客與物件相關欄位；虛擬帳號、餘額、歷程一律都有） {#jgb/E/recharge-account-list-columns}
- phrasings:
  - {text: "固定虛擬帳號管理在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號列表欄位", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號餘額能改嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號歷程", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/rechargeAccountList/Index.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「固定虛擬帳號管理」列表一定會有的欄位是虛擬帳號、餘額、歷程；租客姓名、Email、手機號碼這組欄位，以及物件 ID、案名、地址這組欄位，都要看帳號設定是否開啟對應的欄位開關才會出現。
每一列最後有一個「歷程」欄位，可以點開查看這組帳號的金額變動紀錄。
帳號設定開啟物件欄位時，列表才會顯示這個物件的物件 ID、案名跟地址。
「餘額」欄位在新增／編輯的視窗裡是可以手動輸入修改的數字欄位（不能小於 0），不是系統自動累加、不能修改的唯讀顯示。
### 固定虛擬帳號要怎麼刪除？（列表操作選單選「刪除」，跳出確認視窗後才會真的刪掉） {#jgb/E/recharge-account-delete}
- phrasings:
  - {text: "虛擬帳號刪除流程", source: "draft:outline-20260920", status: proposed}
  - {text: "刪除虛擬帳號要確認嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "刪除虛擬帳號失敗", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/rechargeAccountList/Index.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在「固定虛擬帳號管理」列表，每一列右邊的操作選單裡有「編輯」跟「刪除」兩個選項。
點「刪除」會先跳出確認視窗，顯示這組虛擬帳號的租客姓名跟帳號，需要再按一次「刪除」才會真的刪除；按「取消」可以中止。
刪除成功後畫面會提示「已刪除」，並重新整理列表；如果刪除失敗，會顯示對應的錯誤訊息。
### 點開「歷程」看得到哪些內容？（每筆金額變動的時間／類型／金額／前後餘額／操作人員，有連結帳單可以點開查看） {#jgb/E/recharge-account-history-content}
- phrasings:
  - {text: "歷程看得到什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "金額變動歷程內容", source: "draft:outline-20260920", status: proposed}
  - {text: "歷程能看帳單嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/rechargeAccountList/Index.vue]
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
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
新增中國信託虛擬帳號時，需要輸入「企業識別碼」（5 碼）與「繳款人識別碼」（8 碼），系統會用這兩組數字直接算出對應的虛擬帳號。
這個計算過程只是在畫面上算好帳號給你看，實際送出新增的時候，系統送出的還是計算出來的固定式虛擬帳號欄位。
這個中信虛擬帳號計算機模式目前只有特定客戶在使用，介面文字暫時維持原文，還沒套上多語系翻譯。
### 虛擬帳號建立後，銀行跟帳號可以改嗎？（不行，只能改租客資料跟餘額，銀行帳號建立後鎖死） {#jgb/E/recharge-account-immutable}
- phrasings:
  - {text: "虛擬帳號可以改銀行嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號可以改帳號嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "編輯虛擬帳號能改什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號要換銀行怎麼辦", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/rechargeAccountList/Index.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
編輯虛擬帳號時，「銀行」跟帳號欄位都是唯讀的，這兩個是建立後不能修改的欄位，因為它們是同一個實體銀行帳戶的識別碼，改掉會讓餘額同步錯亂（舊群組少一筆記錄、新群組被覆寫錯誤餘額）。
編輯時可以改的是租客姓名、Email、手機號碼跟餘額（以及有開放物件欄位時的物件）。
如果租客的手機號碼、Email 或姓名有異動，直接在編輯視窗更新這些欄位即可，不需要重新建立整組虛擬帳號。
如果需要更換銀行或帳號，唯一的方式是先把這組虛擬帳號刪除，再重新建立一組新的；畫面上也直接提示「銀行與帳號建立後不可修改，如需變更請刪除後重新建立」
### 虛擬帳號綁定物件時，輸入物件 ID 有什麼驗證？ {#jgb/E/recharge-account-estate-binding-validation}
- phrasings:
  - {text: "虛擬帳號綁定物件ID", source: "draft:outline-20260920", status: proposed}
  - {text: "物件ID驗證失敗", source: "draft:outline-20260920", status: proposed}
  - {text: "物件不屬於這個團隊", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號選擇物件按鈕", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/rechargeAccountList/Index.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在虛擬帳號綁定物件時輸入物件 ID，如果 ID 不是有效格式，會提示「請輸入有效的物件 ID」。
如果物件 ID 存在但不屬於目前登入的團隊，會提示「物件不存在或不屬於此團隊」，驗證通過後才會帶出案名跟地址讓你確認。
驗證通過後畫面會顯示這個物件的案名跟地址，讓操作者在送出前可以再次確認是不是要綁的那個物件。
除了直接輸入物件 ID，欄位旁邊還有一個「選擇物件」按鈕，點下去會先把目前編輯中的表單內容暫存起來，再跳轉到物件挑選頁面讓使用者用搜尋/瀏覽的方式選物件，選好後會自動帶回物件 ID。
### 「固定虛擬帳號管理」列表怎麼匯出？（指定日期區間匯出 Excel 明細） {#jgb/E/recharge-account-export}
- phrasings:
  - {text: "虛擬帳號怎麼匯出", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號匯出明細", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號匯出日期區間", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/rechargeAccountList/Index.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
匯出虛擬帳號要先選「起始日期」跟「結束日期」，兩個日期都沒填或起始日期晚於結束日期都會被擋下不能匯出。
匯出的檔案是 Excel（.xlsx），檔名會帶入「固定虛擬帳號匯入明細」跟指定的起訖日期。
匯出時預設會帶入本月第一天到今天當作日期區間，可以再自行調整成需要的區間。
### 固定虛擬帳號的入帳是怎麼自動比對到帳單的？（每日凌晨 03:00 排程沖銷；限特定合作團隊才會自動比對；餘額不夠不會變成已到帳） {#jgb/E/recharge-account-daily-settlement}
- phrasings:
  - {text: "固定虛擬帳號自動到帳", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號入帳幾點處理", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬帳號沖銷排程", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Console/Kernel.php, code:app/Console/Commands/BillRechargeAccount.php, code:app/RechargeAccount.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
系統每天凌晨 03:00 會跑一個排程，把固定虛擬帳號收到的款項自動沖銷、比對到對應的帳單。
這個自動比對只會處理特定合作團隊的帳單，其他團隊的固定虛擬帳號帳單不會被這個排程自動處理，仍要靠人工對帳。
如果虛擬帳號的餘額不夠支付某張帳單，這張帳單會維持原本的「應到帳」狀態，不會被標記成「已到帳」；排程之後每天還會再重新比對一次。
## 線上金流收款帳號開通（藍新、中信；入口在「線上智能整合收款」頁的「開通帳號」） {#E-payment-onboarding}
### JGB 支援哪些收款金流？身分限制是什麼？（國泰世華／永豐銀行僅法人；中國信託／藍新法人與個人皆可） {#jgb/E/payment-gateway-options}
- phrasings:
  - {text: "支援哪些收款金流", source: "draft:outline-20260920", status: proposed}
  - {text: "個人房東可以用哪個金流", source: "draft:outline-20260920", status: proposed}
  - {text: "國泰世華可以申請嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "永豐銀行金流申請", source: "draft:outline-20260920", status: proposed}
- sources: [help:paymentapply_zh-Hant.html]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
JGB 目前支援國泰世華、永豐銀行、中國信託、藍新 NewebPay 四種收款金流。
國泰世華跟永豐銀行僅開放法人申請，個人房東目前可以選擇的是中國信託跟藍新。
中國信託的租客必須有中信帳戶，並透過中信 APP 繳費，申請前建議先確認租客是否方便使用。
### 各家收款金流的費率跟入帳帳戶限制是什麼？（國泰世華／永豐銀行首次設定費 5,000 元且限本行帳戶；中國信託／藍新免費且不限本行帳戶） {#jgb/E/payment-gateway-fees}
- phrasings:
  - {text: "金流申請要收費嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "首次設定費多少", source: "draft:outline-20260920", status: proposed}
  - {text: "入帳帳戶有限制嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "國泰世華入帳帳戶", source: "draft:outline-20260920", status: proposed}
- sources: [help:paymentapply_zh-Hant.html]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
國泰世華、永豐銀行是自行向銀行申請，兩者都有「首次設定費 5,000 元」；中國信託、藍新 NewebPay 是在 JGB 系統線上申請，都是免費的。
入帳帳戶也有限制：國泰世華只能匯入國泰世華的實體帳戶，永豐銀行只能匯入永豐銀行的實體帳戶；中國信託跟藍新則可以指定任一實體帳戶收款。
### 開通藍新智付通前要準備什麼？（手機號碼欄位不能是空的、限台灣手機、只能開通一次；權限不足或租客會被導回） {#jgb/E/newebpay-precondition}
- phrasings:
  - {text: "藍新開通前提條件", source: "draft:outline-20260920", status: proposed}
  - {text: "藍新智付通手機驗證", source: "draft:outline-20260920", status: proposed}
  - {text: "藍新已經開通過會怎樣", source: "draft:outline-20260920", status: proposed}
  - {text: "沒有權限開藍新會怎樣", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/UserController.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
開通藍新智付通限定台灣手機號碼的帳號才能申請。
如果帳號的手機號碼欄位是空的，會被導回並提示要先完成手機號碼驗證後才能進行藍新金流的開通設定；但這個判斷實際上只檢查『有沒有填寫手機號碼』，並不是檢查『手機號碼有沒有通過驗證』。
同一個帳號只能開通一次，已經開通過商店的帳號再進入會被導回並提示已開通過商店。
沒有「收款設定」編輯權限的帳號會被導回，並提示「您目前登入的帳號無法使用智付通開通功能」；租客帳號則是在更早的地方就被直接導回帳號資訊頁面，不會看到這則提示訊息。
### 開通藍新智付通前，個人房東跟團隊各自要先填完哪些資料？ {#jgb/E/newebpay-required-fields}
- phrasings:
  - {text: "藍新開通要先填什麼資料", source: "draft:outline-20260920", status: proposed}
  - {text: "身分證字號沒填能開藍新嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "公司統編沒填能開藍新嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/UserController.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
個人房東要先填好名稱、姓氏、身分證字號、Email 並完成 Email 驗證，以及通訊地址（縣市、區、地址），沒填完會被導回帳號資訊頁面並列出缺少的欄位。
團隊帳號則要先填好公司統編、公司名稱、公司地址（縣市、區、地址），以及管理者的手機號碼、Email 並完成 Email 驗證，沒填完會被導回團隊頁面。
個人房東欄位缺漏時會被導回帳號資訊頁面，並用逗號列出所有還沒填寫或還沒驗證的欄位名稱。
團隊帳號則是導回團隊頁面，一樣會列出缺少的公司資料或管理者資料。
### 藍新開通時可以勾選哪些付款方式？（信用卡／Google Pay／Samsung Pay／ATM／超商代碼／國外卡） {#jgb/E/newebpay-payment-methods}
- phrasings:
  - {text: "藍新支援哪些付款方式", source: "draft:outline-20260920", status: proposed}
  - {text: "超商代碼繳費金額限制", source: "draft:outline-20260920", status: proposed}
  - {text: "國外卡要另外申請嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "藍新付款方式預設開哪些", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/UserController.php]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
藍新開通畫面可以勾選「信用卡」「Google Pay」「Samsung Pay」「ATM」「超商代碼」「國外卡」六種付款方式，除了國外卡以外都是預設開啟。
超商代碼有付款金額限制，畫面上會提示付款金額有 TWD 30 到 TWD 20,000 的限制。
「國外卡」預設是關閉的，如果一開始沒有勾選開通，之後要開通須另外透過 JGB 向藍新金流申請，耗時約 5 到 7 個工作天；同一組付款方式清單裡，只有「超商代碼」跟「國外卡」帶有提示文字，其餘信用卡／Google Pay／Samsung Pay／ATM 四個選項沒有提示文字。
### 中國信託轉帳 Pay 怎麼申請？（線上填資料送出後走人工審核，審核 5 個工作天） {#jgb/E/ctbc-apply-flow}
- phrasings:
  - {text: "中信轉帳Pay怎麼申請", source: "draft:outline-20260920", status: proposed}
  - {text: "中信金流審核多久", source: "draft:outline-20260920", status: proposed}
  - {text: "中信收款帳號開通流程", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/UserController.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
中國信託轉帳 Pay 是在系統上填寫身分證字號/統一編號、聯絡電話、收款銀行代碼與名稱、戶名、銀行帳號後送出申請。
送出後不是馬上生效，會轉為人工審核，審核時間需 5 個工作天（不含例假日）。
如果表單資料驗證失敗，會直接返回原本填寫的頁面並保留已輸入的內容，不用重新整份填寫。
申請通過驗證送出後，系統會把這次填寫的收款資訊記錄下來，並更新這個帳號目前使用的收款方式為中國信託。
中信申請頁面雖然會把「分行代碼」這個欄位值一起放進畫面初始化的資料裡，但畫面上完全沒有可以填寫「分行代碼」的欄位；申請時只要選「銀行代碼與名稱」，不需要另外填分行代碼。
### 中國信託申請表單各欄位有什麼格式限制？（聯絡電話 10 碼、銀行代碼 3 碼、銀行帳號 10～16 碼） {#jgb/E/ctbc-form-validation}
- phrasings:
  - {text: "中信申請表單欄位限制", source: "draft:outline-20260920", status: proposed}
  - {text: "聯絡電話要幾碼", source: "draft:outline-20260920", status: proposed}
  - {text: "銀行帳號要幾碼", source: "draft:outline-20260920", status: proposed}
  - {text: "銀行代碼幾碼", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/UserController.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
聯絡電話必須剛好 10 碼數字。
銀行代碼必須剛好 3 碼數字。
銀行帳號要輸入 10 到 16 碼數字，不足 16 碼系統會自動在前面補 0。
### 各家金流的款項要怎麼提領？（藍新要自己登入後台辦理，前 5 次免費之後每次 10 元） {#jgb/E/payment-gateway-withdrawal}
- phrasings:
  - {text: "藍新款項怎麼提領", source: "draft:outline-20260920", status: proposed}
  - {text: "藍新提款手續費", source: "draft:outline-20260920", status: proposed}
  - {text: "收到的錢在哪裡領", source: "draft:outline-20260920", status: proposed}
- sources: [help:paymentapply_zh-Hant.html]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
藍新的款項會先留在藍新帳戶中，需要自行登入藍新後台辦理提款，前 5 次免費，之後每次收取 10 元手續費。
藍新提款是在藍新自己的後台辦理，不是在 JGB 系統內操作。
