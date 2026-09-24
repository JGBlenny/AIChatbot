# JGB 產品事實帳本（受眾中立、逐條對碼）

> **這是什麼**：AI 客服知識的「第 0 層」——只記**程式證明的產品事實**，不寫任何受眾的說法。每條附 jgb2 程式引用（`path:symbol`）、查證日期與分支。`rag-orchestrator/canon/jgb/` 九架正本裡，售前身分（`target_user=prospect`）與業者身分（`target_user=property_manager`）的細目各自從這裡**改寫成自己的層級**（售前＝能力／邊界，業者＝操作／狀態），⛔ 不得把一個受眾的細目直接開放給另一個受眾（R3.6）。
> **怎麼引用**：正本細目 `sources: [docs:knowledge/jgb-product-facts.md#<anchor>]`。
> **怎麼維護**：事實變了改這裡、附新引用；⛔ 不在正本裡各自改數字。引用只寫可 grep 的符號，行號只當輔助。
> **查證來源**：jgb2 釘住 commit `b2ee2ac382ce`（`git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce:<path>`；⛔ 不讀 `dev2` 磁碟工作樹，它在 master 上已領先該 commit）；幫助中心 HTML `/Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/`；細目對應指 `runs/outline-20260920/drafts-<架>.json` 的 `proposed_id`。全檔條目一律以此重驗。

## 身分與角色 {#identities}

### JGB 沒有「管理者」角色：管物件那一側就叫「房東」，分三種 {#landlord-is-the-manager}
- 事實：`app/Role.php` 規則鍵只有四個——`RULE_KEY_TENANT=1`、`RULE_KEY_LANDLORD_INDIVIDUAL=2`（個人房東）、`RULE_KEY_LANDLORD_CORPORATE=3`（法人房東）、`RULE_KEY_LANDLORD_SOCIAL_HOUSING=4`（社宅房東）；團隊成員與大房東是掛在房東底下的關聯型別（`USER_RELATED_TYPE_TEAM=1`、`USER_RELATED_TYPE_BIG_LANDLORD=2`）。登入頁分「房東」「租客」兩個入口。
- 事實：JGB 呼叫 AI 客服時，房東側一律送 `target_user='property_manager'`——`app/Http/Controllers/HelpAssistantController.php`（`$request->input('target_user', 'property_manager')`，註解「租客視角一律不開放智能助手（業者/property_manager 視角專用）」）與 `src/components/HelpSystem/ChatView.vue`（`targetUser: 'property_manager'`）。jgb2 全庫 `property_manager` 僅此 3 處；`landlord` 作為身分值 0 處。
- 邊界：所以我方 `property_manager` ＝ JGB 的房東（個人／法人／社宅），⛔ 不是「房東之外另一種管理者」；我方 `KNOWN_TARGET_USERS` 四值＝`tenant`／`property_manager`／`system_admin`／`prospect`（DSP-061），房東側對應 `property_manager`。JGB 目前只對房東側開智能助手，租客側未開。
- 查證：`git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -n "RULE_KEY_\|USER_RELATED_TYPE_" master -- app/Role.php`；`git -C … grep -n property_manager master`（2026-09-17，master）。

## 合約 {#contracts}

### 電子簽章不另外收費 {#esign-no-fee}
- 事實：電子簽章走 Thinkcloud，`contract_esign` 表只存 `thinkcloud_jobid／thinkcloud_docid／thinkcloud_pdf`，**無任何費用、點數欄位**；租客簽約頁 8 步流程無付費／加購 UI；合約付款方式列舉只有 `vendor／cash／recharge_account`。
- 引用：`database/migrations/2026_06_17_000002_create_contract_esign_table.php`；`app/Contract.php` 付款方式常數；`resources/views/contract/sign.blade.php`。
- 邊界：這證明「系統內無簽章計費機制」，**不證明**方案價目表上沒有把電子簽章列為方案內容——方案內容以 `/pricing` 為準（售前不報價原則）。
- 對應格：C22。

### 包租 vs 代管 {#charter-vs-management}
- 事實：委託合約 `EntrustedContract` 以 `lease_type` 區分——`LEASE_TYPE_CHARTER=1`（包租）、`LEASE_TYPE_MANAGEMENT=2`（代管）。代管必填 `service_fee_type／service_fee_currency／service_fee`（服務費制度／週期／約定日期）；包租用「包租租金」與其計算制度／週期／約定日期。合約範本按身分分版（原房東／包租業／代租代管）。
- 引用：`app/EntrustedContract.php:LEASE_TYPE_CHARTER`、`LEASE_TYPE_MANAGEMENT`、`service_fee_type` 驗證規則。
- 未證：兩者在**結算／代收代付**流程上的差異未對碼（scout 只找到費用欄位差異）。
- 對應格：C03（partial 正確：範本細目只答了範本分版）。

### 「單合約／雙合約」不是系統用語 {#single-vs-dual-contract}
- 事實：`單合約`／`雙合約` 在 jgb2 程式、163 份 docs、幫助中心 92 頁**皆無此詞**（正對照：同一掃描「合約」命中 108 份 docs）。程式裡可對應的概念：(a) 委託合約 `EntrustedContract`（房東↔業者）與租賃合約 `Contract`（業者↔租客）**兩份**並存於包租／代管情境；(b) 簽約邀請的 `STATUS_INVITING_FIRST／STATUS_INVITING_NEXT` 位元（一方或兩方簽）。
- 業主裁（2026-09-07）：**先不管**——維持 not_available，不寫說法；⛔ 沒有新事實不再重提。
- 對應格：C53。

## 帳務與發票 {#billing}

### 電子發票可自動開立，兩種模式 {#einvoice-auto}
- 事實：排程 `invoice:issue-pre-billing` 每日 05:00；`Role.invoice_mode = 'preBillingIssue'` 為預先開立（可設寄送時／到期前／到期後＋天數），另一模式為帳單到帳後開立。幫助中心 einvoice 頁：「啟用後，JGB 會依照您設定的時機，自動幫符合條件的帳單開立電子發票」。
- 引用：`app/Console/Kernel.php` schedule `invoice:issue-pre-billing`；`app/Console/Commands/IssuePreBillingInvoices.php`；`app/Role.php` `invoice_mode`。
- 對應格：C24（判者 no_source 正確：正本目前沒有這句；kb:3601 有但含越權措辭）。

### 差額發票＝業者月結對帳用 {#balance-invoice}
- 事實：`BalanceInvoiceGroup` 記 `base_rent_amount／monthly_cost／monthly_income／invoiced_amount／is_invoiced`；每月 1 日 03:00 排程「差額發票群組開立」，次月重算；狀態每日更新（尚未生效→進行中→歷史）。使用時機＝業者（代管）對房東的月結差額，不是租客端功能。
- 引用：`app/Models/BalanceInvoiceGroup.php`；`app/Console/Kernel.php` 差額發票排程；`docs/balance-invoice-group/`。
- 對應格：C25（跨受眾：這是業者知識，售前層級只需一句「支援代管月結差額發票」）。

### 手機條碼載具＝存發票，不是付款 {#carrier-types}
- 事實：`Invoice::CARRIER_TYPE_PHONE=0`（手機條碼載具）、`CARRIER_TYPE_CDC=1`（自然人憑證）、`CARRIER_TYPE_EZPAY=2`；用於 B2C 發票存入載具。付款方式另有其事（`Contract` 付款方式常數）。
- 引用：`app/Invoice.php:CARRIER_TYPE_PHONE`。
- 對應格：C54（問句「可以用來付費嗎」答案是**不能**，載具只存發票；這是可答的邊界題）。

### 儲值金／回充帳戶＝物件層級預付帳戶 {#stored-value}
- 事實：`Bill::BILL_TYPE_TOPUP=5`（儲值型帳單）；`EstateStoredValue` 以物件為單位記 `recharge_amount_base_number／recharge_accounts_code／recharge_accounts_account`，有 `recharge()／deduct()` 與交易紀錄；排程 `bill:recharge-account` 每日 03:00 以儲值抵扣固定虛擬帳號帳單、`topup-bill-expire:check` 每日 00:02 查逾期。與電錶儲值（DAE 電表）是**不同機制**。
- 引用：`app/Bill.php:BILL_TYPE_TOPUP`；`app/EstateStoredValue.php`；`app/Console/Kernel.php`；`docs/api/recharge-accounts.md`。
- 對應格：C29（跨受眾：業者操作知識；售前層級一句「支援固定虛擬帳號＋儲值抵扣」）。

## 智慧設備 {#iot}

### 私人門鎖 vs 共用門鎖 {#doorlock-types}
- 事實：門鎖有 `key_public` 0／1 兩型。UI 原文：「『私人門鎖』為個人房間的門鎖，只能綁定一個物件；『共用門鎖』為大樓大門、住家大門等公用的門鎖，可以綁定多個物件」；「私人門鎖：房東與租客可各自設定一組密碼」；「共用門鎖：房東可設置共用密碼讓您的租客使用」。另有共用門鎖密碼通知信（`iot_share_passcode`）。
- 引用：`resources/views/iot/doorlock/basic.blade.php`（型別選項與定義）；`resources/views/iot/doorlock/password.blade.php`；`app/Notification.php:iot_share_passcode`；`app/Iot.php`。
- ⚠️ 2026-09-07 一個 scout 回報「程式只有電錶沒有門鎖」——**錯**，它只掃了 `Admin/IotManagementController`；否定結論要帶正對照。
- 對應格：C39（可答；售前層級只講「兩型與綁定範圍」，密碼操作屬業者知識）。

## 物件 {#estates}

### 物件自訂標籤 {#estate-labels}
- 事實：`Label` 模型，`TARGET_MAP['ESTATE']=1`（也可掛合約 `=2`）；預設 6 個物件標籤：可帶看、待清潔、待簽約、維修中、不出租、待完善；標籤依角色（團隊）自訂與篩選（`findLabelsByRoleId`、`createLabel／updateLabel`）。
- 引用：`app/Label.php:TARGET_MAP`、`DEFAULT_LABEL`。
- 對應格：C15。業主裁（2026-09-07）：為售前寫一句（能力層級：物件可貼團隊自訂狀態標籤方便篩選，預設六種）。

## 方案與匯入 {#plans}

### 免費方案預設額度 {#free-plan-quota}
- 事實：`config/defaultplan.php`：`estate_limit=5`、`contract_limit=null`、`team_limit=0`、`big_landlord_limit=0`、`iot_switch=0`、`vr_switch=0`、`plan_cycle=month`。建法人／社宅房東角色時寫入 `roles.plan_estate_limit`；`Role::remainEstatesCount()` 依此擋新增。免費試用一個月與免費方案在程式上是同一個 `plan_type='free'`。
- 引用：`config/defaultplan.php`；`app/User.php` 建角色寫入 `plan_estate_limit`；`app/Role.php:remainEstatesCount`。
- ⚠️ 這是**程式預設**，各角色實值在 `roles.plan_estate_limit`（DB），可被後台改；知識只能說「預設」，當前值走 API（[[project_jgb_system_knowledge]] 原則）。
- 對應格：C07。

### 批次匯入的範圍 {#batch-import-scope}
- 事實：可匯入＝物件（一般／社宅 `estates.general.batch`、`estates.social-housing.batch`）、社區（`communities.batch`）、租客（`LesseeImportValidator`，web 路由未見）、大房東（`BigLandlordImportValidator`）、帳單（`bills.excel.batch.import`、`bills.invoice.import`）。**不可匯入＝合約**（無 `ContractImportValidator`）。帳單匯入對應 `draftBillExport_new` 匯出的欄位結構，是「匯出草稿→填→匯回」的更新流程，**不是把歷史帳單當新紀錄建進來**。
- 引用：`app/Services/ImportPreview/Validators/`（各 Validator）；`BillBatchImportValidator.php` 註解「對應 draftBillExport_new 匯出的 Excel 欄位結構」。
- 對應格：C43（partial 正確，且正本那句「匯入後會成為待發送的新帳單」與程式不符，要改）。

## 一般建議題 {#advice}

### 水電費分算 {#utility-split-advice}
- 性質：一般建議題（map-v2 `ADVICE`），非產品事實；系統面只有「帳單可按合約設定分算」。
- 業主裁（2026-09-07）：列現有不足，對外說法固定為「**系統支援按合約分算，金額看合約**」。
- 對應格：C31。

## 模組命名 {#modules}

### 沒有叫「系統管理」的模組 {#no-system-management-module}
- 事實：業者端程式（`resources/`、`app/` 非 Admin）無「系統管理」字樣（正對照：「團隊管理」5 檔）。平台後台 `AdminSetting::FUNCTIONS_SETTING` 有 15 組（權限／會員／客戶／功能配置／客服專區／物件／合約／帳務／金流／統計／後台紀錄／多語／平台設定／站內工具／文件套版），那是 JGB 內部後台，不對業者開放。
- 引用：`app/Abstracts/AdminSetting.php:FUNCTIONS_SETTING`。
- 對應格：C52（可答的邊界題：「沒有這個模組；您要找的功能多半在團隊管理」＋把「系統管理」掛成講法）。

## 修繕 {#repair}

### 修繕單分享頁免登入，任何拿到網址的人都看得到 {#repair-share-public}
- 事實：`/repair/share/<id>` 被登入檢查排除（`app/Http/Middleware/LoginCheck.php`：`$exceptApiUrls = ['/repair/share'];`），分享 API 無 need_login。廠商點連結不需 JGB 帳號；頁面顯示該單房東方（個人房東本人或團隊公司）的電話／Email、物件區域（國／市／區）、報修照片、廠商電話；修繕金額 API 也會回傳（`complete_note.total`，`$isShare` 的 unset 區塊沒有拿掉），只是畫面上以 `showAmount` 限房東身分登入才渲染。幫助中心叫它「分享主頁」，程式畫面叫「分享訊息」／「分享」／「分享修繕申請單」。
- 引用：`app/Http/Middleware/LoginCheck.php:$exceptApiUrls`；`routes/web.php` 的 `/api2/repairItem/share` 無 `need_login`；`app/Http/Controllers/RepairController.php:share`（`$isShare` unset 區塊）；公開頁 `src/pages/repair/share/Index.vue:showAmount`；分享燈箱 `src/pages/repair/edit/_parts/ApplicationDetail.vue`（drafts-F `repair-edit-share-to-vendor`／`repair-share-public-link` evidence）。釘住 commit `b2ee2ac382ce`，2026-09-20。
- ⚠️ 舊正本曾寫成「分享給租客」——錯；幫助中心「分享主頁給維修業者」才對。
- 待裁：公開頁揭露聯絡方式要不要在知識裡提醒（總表 F 架）。

### 「通知及同步租客」與「緊急修繕」兩個開關顯示但不生效 {#repair-apply-dead-switches}
- 事實：`src/pages/repair/applyProcess/_parts/Detail.vue` 用 `<SwitchButton :model="repairForm.is_notice_tenant" />` 與 `<input :model="repairForm.is_urgent" … type="checkbox" />` 綁定（元件 prop 是 `modelValue`，同檔其餘 10 處用 `v-model`），沒有 change 事件 ⇒ 房東代租客報修時該單不會同步到租客的修繕單總表、緊急修繕永遠送出非緊急。
- 引用：`src/pages/repair/applyProcess/_parts/Detail.vue`（`:model=`）。釘住 commit `b2ee2ac382ce`，2026-09-20。
- 待裁：是程式缺陷，要不要排修（總表 F 架）；知識裡寫「目前沒有實際作用」。

### `Repair::EMERGENCY_STATUS` 常數名與用法相反 {#repair-emergency-constant-inverted}
- 事實：`app/Repair.php` 定義 `EMERGENCY_NON_STATUS=1 //緊急`、`EMERGENCY_STATUS=2 //非緊急`；`RepairController`／`UserController`／`RepairService` 都以 `is_urgent = (status === EMERGENCY_STATUS)` 當「緊急」用，`External/RepairApiController` 卻把它對應成中文「非緊急」。
- 引用：`app/Repair.php:EMERGENCY_STATUS`；`app/Http/Controllers/External/RepairApiController.php`。釘住 commit `b2ee2ac382ce`，2026-09-20。
- ⚠️ 與 memory `project_conversational_repair_session` 的「emergency_status 語義反轉」同一地雷；讀常數名會被誤導，以呼叫端用法為準。

## 帳務（2026-09-20 補） {#billing-2026-09-20}

### 「財務報表」頁（`bills.sheet`）沒有入口、「下載」無動作 {#bills-sheet-unwired}
- 事實：前端整份程式沒有任何連結或選單指向路由 `bills.sheet`（`/bills/sheet`）；頁面右上「下載」只是文字未綁事件；`rowType`（按物件／按項目）只從 `route.query` 讀、無處賦值。幫助中心無對應頁。
- 引用：`src/routes/bills.js:bills.sheet`；`src/pages/bills/sheet/`（drafts-E `bill-sheet-report-title`／`bill-sheet-two-views` not_supported_greps）。釘住 commit `b2ee2ac382ce`，2026-09-20。
- 待裁：整頁疑未接線，要不要留在大綱（總表 E 架）。

### 大房東對帳表「年度累計」欄 2026-04-30 起刻意隱藏 {#biglandlord-sheet-yearly-hidden}
- 事實：`SelectBar.jsx` 的 `const SHOW_YEARLY_COLUMN = false`（註解「2026-04-30 Joanna 拍板暫時隱藏」）與 `Sheet.vue` 對應區塊 `v-if="false"` 都關閉此欄，畫面不顯示年度累計金額。
- 引用：`src/pages/bigLandlords/sheet/_parts/SelectBar.jsx:SHOW_YEARLY_COLUMN`、`src/pages/bigLandlords/sheet/_parts/Sheet.vue`。釘住 commit `b2ee2ac382ce`，2026-09-20。

### 電表「開立發票」頁籤只剩「是否自動開立發票」一個選項 {#power-meter-invoice-tab-fields}
- 事實：出租方統編、稅別、承租方統編、買受人名稱等欄位與其 script 變數全部被註解掉（ticket #14336，2024-09-04 PM 要求拿掉「出租方統編」相關欄位），畫面不渲染、也送不出資料。
- 引用：`src/pages/iots/_parts/Invoice.vue`（grep `14336`；drafts-G `power-meter-invoice-tab-fields` open_questions）。釘住 commit `b2ee2ac382ce`，2026-09-20。
- ⚠️ 派工 brief 曾把這批欄位當現有功能——錯；死碼不得寫成功能。

## 方案與金流（2026-09-20 補） {#plans-2026-09-20}

### 自動續訂扣款失敗＝清空方案、限額歸零、物件全部下架，無寬限期 {#subscription-charge-failure}
- 事實：`app/Console/Commands/AutoRenewSubscription.php`：`if (!$role->checkCreditAgreed() || !$role->isSubscriptionRenewable())` 後註解「如果扣款失敗 則清空訂閱方案資料與下架物件」，呼叫 `$role->clearSubscription();`。
- 引用：`app/Console/Commands/AutoRenewSubscription.php:clearSubscription`。釘住 commit `b2ee2ac382ce`，2026-09-20。

### 金流開通資格依身分與方案 {#payment-gateway-eligibility}
- 事實：`UserController::getPaymentSupportedVendors`——身分為個人房東（`Role::RULE_KEY_LANDLORD_INDIVIDUAL`）時，藍新／國泰世華／永豐（`Payment::PAYMENT_NEWEBPAY`／`PAYMENT_CATHAYBK`／`PAYMENT_SINOPAC`）標為不可開通；非個人房東但方案為「免費方案」或「體驗方案」時，只有國泰世華／永豐不可開通。不可開通者點選後不出表單、紅字「您無法開通此收款方式，若有問題請洽詢JGB客服」（文案在 `UserController.php` 與 `_parts/Ctbc.vue`）；選單灰階是另一件事＝該金流已開滿三組帳號（`每個金流至多可開通三組帳號。`）。
- 引用：`app/Http/Controllers/UserController.php:getPaymentSupportedVendors`；`src/pages/users/payment/routerView/Add.vue:isLimitVendorAdd`。釘住 commit `b2ee2ac382ce`，2026-09-20。
- ⚠️ 方案頁 FAQ 說免費方案「擁有智能合約及自動對帳功能」，免費試用彈窗（`LightboxFreePlan.vue`）卻把自動對帳列在不支援並註「無法申請國泰、永豐可申請藍新、中信」——文案互相矛盾，待裁（總表 I 架）。

### 「財政部包租業租金收據範本」只有法人／社宅團隊看得到 {#receipt-template-gates}
- 事實：`src/pages/users/payment/_parts/Receipt.vue` 以 `const isTeam = [3, 4].includes(store.state?.userData?.role?.config_rule_key)` 決定選單；個人房東只有「超商繳費單、JGB系統收據」「超商繳費單、不檢附收據」兩種，法人／社宅多三種含財政部範本或 JGB 系統繳費單的組合。選財政部範本須先在團隊資訊填公司登記證日期／縣市／證號。
- 引用：`src/pages/users/payment/_parts/Receipt.vue:isTeam`；`src/utils/constants/paymentSetting.ts`。釘住 commit `b2ee2ac382ce`，2026-09-20。

### 任務管理器提前開單天數兩個頁面說法不一（30 vs 45 天） {#task-manager-lead-time-conflict}
- 事實：任務列表頁 `src/pages/control-panel/taskManagement/Index.vue` 寫「指定週期的前三十天完成單據的開立」；新增／編輯頁 `taskManagement/edit/Index.jsx` 寫「觸發時間前 45 天完成單據的開立，並寄信通知。系統後續會在觸發時間的 30 天前、15 天前寄送通知信」。
- 引用：上述兩檔。釘住 commit `b2ee2ac382ce`，2026-09-20。
- 待裁：哪份是現行（總表 I 架）；知識裡暫不寫具體天數。

## 幫助中心 {#help-center}

### 幫助中心首頁停留 60 秒彈「立即免費試用」視窗 {#help-center-trial-popup}
- 事實：只在路由名等於幫助中心首頁時起計時（`src/entry/listings.js`：`if ('listings.helpCenter'.includes(route.name))`）；分類／文章／搜尋頁不觸發。視窗文案「現在註冊享有免費試用30天」，四欄（公司名/姓名、電話、Email、簡述您有興趣的原因）都填才可送出（`return notDoneFields.length == 0`），右上角可關閉。
- 引用：`src/pages/help-center/Index.vue`；`src/entry/listings.js`。釘住 commit `b2ee2ac382ce`，2026-09-20。
