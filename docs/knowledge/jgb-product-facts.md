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
- 事實：委託合約 `EntrustedContract` 以 `lease_type` 區分——`LEASE_TYPE_CHARTER=1`（包租）、`LEASE_TYPE_MANAGEMENT=2`（代管）。代管必填服務費計算模式、幣別、服務費或服務費比例（`service_fee_type／service_fee_currency／service_fee`）；計算制度、週期、約定日期（`service_fee_cycle_type／cycle／cycle_date`）兩者都必填，只是標籤不同（代管叫「服務費…」、包租叫「包租租金…」）。合約範本按身分分版（原房東／包租業／代租代管）。
- 引用：`app/EntrustedContract.php:LEASE_TYPE_CHARTER`、`LEASE_TYPE_MANAGEMENT`、`service_fee_type` 驗證規則（`Rule::requiredIf($this->lease_type === self::LEASE_TYPE_MANAGEMENT)`）、`'service_fee_cycle_type'            => 'required',`（空白照原檔）。
- ⚠️ 2026-09-27 更正（Plan 9.15 帳本複核 verifier，程式反證）：原句把欄位與標籤配錯（計算制度／週期／約定日期兩種都必填）。
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

## Plan 9.14 對源事實（2026-09-25，jgb2 `b2ee2ac382ce`） {#p914}

> 來源：Plan 9.14 S3（步 5b）對 145 個真實問句缺口格的唯讀盤查；每條皆過機械複驗（證據為釘住 commit 內某行的逐字子字串）。「對應格」是 repo 外 run 目錄的 `cell_id`，⛔ 題目原文不進 repo。引用同本檔慣例：路徑＋可 grep 的符號或字串。
> ⚠️ 主 session 抽查時更正兩條：`p914-email-encrypted-no-lowercase`（scout 原判「定序不分大小寫」被推翻）與 `p914-account-phone-bound`（原句「系統無自助改手機入口」超出證據，已收窄）；fresh verifier 再推翻一條：`p914-renewal-deposit-diff`（只限新北住都延長續約）。

### 合約

#### 既存合約可加「其他租客」，上限 10 筆 {#p914-contract-additional-tenants}
- 事實：**既存合約**（紙本上傳或自製合約）的租客資訊頁有「新增租客」，每筆填承租方名稱與身分證字號／統一編號，存於 `additional_tenant`，達 10 筆即不能再加；**電子範本合約沒有這個功能**。這是業者頁面，不是內部後台的 `addTenantToContract`。
- 引用：`src/pages/contracts/edit/tenantInfo/Index.jsx:addAdditionalTenant`、`additional_tenant?.length >= 10`、`Boolean(props.editStore?.options?.is_existed) && <>`；`app/Http/Controllers/ContractController.php`（`'is_existed'=> $contract->contract_is_existing`）。
- ⚠️ 2026-09-27 更正（Plan 9.15 帳本複核 verifier，程式反證）：原句未限定既存合約、欄位名寫成「暱稱／證件字號」。
- 對應格：`32e60ab5d92d`、`90170e3f51de`、`c528fcf3fd47`。

#### 租客資料逐筆記錄 {#p914-lessee-records}
- 事實：租客資料以逐筆承租人紀錄（`existed_lessee`／`prospective_lessee`）建立，姓名、公司名稱、身分類型、聯絡方式逐筆填寫。
- 引用：`app/Services/LesseeService.php`（`'lessee_name as name'`）。
- 對應格：`217194eecdb1`。

#### 社宅合約可加代理人，最多 3 位 {#p914-contract-agents}
- 事實：**社宅合約**編輯的租客資料頁（路由 `contracts.edit.socialHousing.tenantBasic`）有「新增代理人」，存於 `to_user_pdf_agents`，未滿 3 位才可新增；關係選項為父、母、監護人（法定代理）。一般合約的租客資訊頁（`tenantInfo`）沒有這個功能。
- 引用：`src/pages/contracts/edit/tenantBasic/Index.vue`（`新增代理人`、`to_user_pdf_agents.length < 3`）；`src/routes/contracts.js`（`contracts.edit.socialHousing.tenantBasic`）。
- ⚠️ 2026-09-27 更正：原句未限定社宅合約（Plan 9.15 S3 D 架 verifier 發現）。
- 對應格：`d799d0d69999`。

#### 送出邀請時比對既有會員；事後註冊可經邀請連結認領 {#p914-contract-invite-account-match}
- 事實：送出邀請時，以合約填的租客 Email 比對已註冊會員（比對到才代入該會員資料，並把合約上的租客 Email 改成會員的註冊 Email）；以電話比對時只認已完成手機驗證（`phone_verified_at` 非空）的帳號。
- 事實：租客事後才註冊時，如果是**在同一個瀏覽器點開該合約的邀請連結後、在工作階段有效期間內（預設 120 分鐘）接著註冊或登入**，且合約仍是「待租客簽回」尚未綁定帳號，系統會自動認領這份合約；換裝置、隔太久才註冊，或合約已簽署完成、已綁定其他帳號，都不會自動綁定。
- 事實：承租人 Email 存在各合約自己的 `to_user_email`，程式未見「同一 Email 跨合約須唯一」的檢查。
- 引用：`app/Http/Controllers/ContractController.php`（`User::where('email', xxtea_base64_encrypt($contract->to_user_email))`、`$contract->to_user_email = $user->email;`、`whereNotNull('phone_verified_at')`）；`app/Http/Controllers/EstateController.php`（`session()->put('contract_invitation', [$contract->id]);`）；`app/Http/Controllers/AuthController.php`（`receiveContractInvitation('contract', $contractId)`）；`app/User.php:receiveContractInvitation`；`config/session.php`（`'lifetime' => env('SESSION_LIFETIME', 120)`）。
- ⚠️ 2026-09-27 更正（Plan 9.15 帳本複核 verifier，程式反證）：原句「租客事後註冊不會自動綁回」與程式相反。
- 對應格：`1e16fa69fcc7`、`94fead8a36a8`、`c46c210386be`。

#### 會員 Email 加密存放，比對前不轉小寫 {#p914-email-encrypted-no-lowercase}
- 事實：`User::setEmailAttribute` 以 XXTEA 加密後存入 `email`；比對會員時以加密後字串做相等查詢（`where('email', xxtea_base64_encrypt(…))`），`setEmailAttribute` 寫入前與合約邀請比對前都未轉小寫 ⇒ 資料庫定序「不分大小寫」不適用於這個比對，大小寫不同會被當成不同 Email。email 相關的 `strtolower` 只出現在統計／匯出報表、內部後台（`Admin/*`）與外部 API（`External/TeamMemberApiController`），不在業者端的邀請比對路徑上；內部後台 `Admin/TenantInfoUpdateController::emailMatchCandidates` 的註解另指出 `users.email` 目前明文與密文並存。
- 引用：`app/User.php:setEmailAttribute`；`app/Libraries/XXTEA.php:xxtea_base64_encrypt`；`app/Http/Controllers/ContractController.php`。
- ⚠️ 主 session 對碼更正：scout 原以 `config/database.php` 的 `utf8mb4_unicode_ci` 判「本來就不分大小寫」——錯，欄位存的是密文。登入流程未逐檔追到，若要對外講「登入是否分大小寫」需再對碼。
- 對應格：`77cba6a26bca`。

#### 新合約不動舊合約；同一物件最多 10 份使用中合約 {#p914-contract-new-vs-old}
- 事實：建立新合約不會自動作廢或改動既有合約。同一物件「使用中」（未刪除、未轉歷史：`is_history = 0` 且 `active = 1`）的合約達 `MAX_ACTIVE_CONTRACTS_COUNT`（10）才擋新增，合約結束轉歷史後不再佔名額；不檢查新舊租期是否重疊。「取消邀請」對一般合約是退回待發送，只有續約草稿會被停用。
- 引用：`app/Http/Controllers/ContractController.php`（`activeContracts()->count() >= self::MAX_ACTIVE_CONTRACTS_COUNT`）；`app/Contract.php`（`scopeActiveContracts`、`Contract::reset` 的 `isRenewContract()` 分支）。
- ⚠️ 2026-09-27 更正（Plan 9.15 帳本複核 verifier，程式反證）：原句「取消邀請即停用」只對續約草稿成立；計數排除歷史合約。
- 對應格：`10e43c55dc28`、`2d5a4c136de5`。

#### 只有「待發送」的合約可刪除 {#p914-contract-delete-draft-only}
- 事實：刪除合約僅限待發送狀態，且需有編輯合約權限；已進入其他流程狀態的合約不能刪。
- 引用：`app/Http/Controllers/ContractController.php`（`僅能刪除待發送狀態的合約`）；`routes/web.php` 的 `contracts.delete`。
- 對應格：`8fdbb638e81c`。

#### 免註冊租客的合約成立即為已簽名 {#p914-contract-exempt-register-signed}
- 事實：租客免註冊的合約，成立行為（`CONTRACT_CONFIRM_LOG`）直接把狀態設為 `CONTRACT_SIGNED`，不經過「待租客簽回」（`CONTRACT_INVITING`）與「待管理者簽名」（`CONTRACT_INVITING_NEXT`）。
- 引用：`app/Services/ContractService.php`（`免註冊合約不用簽約流程`）。
- 對應格：`2db2376f49f4`。

#### 租賃範圍由物件空間型態決定 {#p914-contract-lease-scope}
- 事實：物件空間型態為整戶（`flat`／`office_flat`）時合約租賃範圍為「全部」，其餘一律「部分」，不由使用者另外勾選。
- 引用：`app/Contract.php`（`若物件的空間型態為整戶，則租賃範圍為全部，其他狀況下必是部分`）。
- 對應格：`4953441607e2`。

#### 合約範本清單與限制 {#p914-contract-templates}
- 事實：可選範本由 `config/contract.php` 的 `template`，依出租方身分與團隊組出（`ContractController` 以 `$contractTemplateNames` 組單）：個人房東只有內政部中文版（原房東）、內政部英文版、英泰文版與公會中文版等少數幾種；一般法人另有代租代管、包租轉租等；特定合作團隊有專屬範本。
- 事實：轉租合約是一般合約實體的一種範本（`config/contract.php` 的 `轉租合約`）；合約列表的 ID 欄即該合約紀錄主鍵，唯一。
- 事實：內政部英文版的補充條款**會**印在合約書第 4 頁；只有編輯時的「補充條款預覽」對這個範本不套背景、改用空白頁。
- 引用：`app/Http/Controllers/ContractController.php`（`$contractTemplateNames[] =`）；`app/Contract.php`（`$position[$positionPage][3]['write'] = $writes; // 補充條款;`）；`config/contract.php`（`內政部英文版 住宅租賃契約書`、`'label' => '轉租合約'`）；`tests/Unit/ContractController/ResolveAdditionalTermsPositionTest.php`；`src/pages/contracts/list/_parts/ListTable.vue`（`ContractColumnKey.ID`）。
- ⚠️ 2026-09-27 更正（Plan 9.15 帳本複核 verifier，程式反證）：原引用的 `resources/structures/contract/edit/options.php` 無載入點；原「英文版不印補充條款」只對預覽成立，正式合約書會印。
- 對應格：`7b5c41b4e638`、`5736c4b359de`、`9df22ffd2431`。

#### 合約起始日是使用者填的 `date_start` {#p914-contract-date-start}
- 事實：合約起始日取使用者填寫的 `date_start`，帳務以它為起算基準，與合約資料建立進系統的時間無關。
- 引用：`app/Contract.php`（`'date_start',`）；`app/Services/BalanceInvoiceService.php`（`$activeContract->date_start`）。
- 對應格：`0e7435239e8e`。

#### 合約可設「第四台」費用項 {#p914-contract-cable-tv-fee}
- 事實：合約費用項目有「第四台」，可設金額、是否由房客自行負擔、是否內含於租金。
- 引用：`resources/structures/contract/edit/form.php`（`"第四台"=> [`）。
- 對應格：`48d6f1f589a7`。

#### 執行中合約的齒輪選單順序 {#p914-contract-gear-menu}
- 事實：合約總表（`ContractController@webList`）對執行中合約（雙方簽名完成／點交／點退各階段）的齒輪選單依序為：查看物件（有查看物件權限時）、查看帳單（一律出現，整條續約鏈沒有帳單時停用）；社宅包租另有「新增轉租契約書」；房東方（租客身分看不到）再依序為點交物件、取消點交邀請、點退押金、取消點退邀請；非社宅合約另有續約、提前解約。各項依狀態與權限可能是停用狀態。
- 引用：`app/Http/Controllers/ContractController.php`（`定義 $actions 這段應該挪到前端`、`'text' => ___('查看帳單'),`、`'text' => ___('取消點交邀請'),`、`$this->roleType !== 'tenant'`）；`routes/web.php`（`/api2/contract/list/{action?}/{status?}` → `webList`）。
- ⚠️ 2026-09-27 更正：原句只列五項，取自非合約總表的 `index()`，漏了查看帳單與兩個取消邀請（Plan 9.15 S3 D 架 verifier 發現）。
- 對應格：`a288657cdbab`。

#### 續約＝複製出一份全新合約；註冊租客要簽署，免註冊租客直接成立 {#p914-contract-renewal}
- 事實：續約以 `replicate()` 建立全新合約紀錄，並剝除從舊合約繼承的「歷史合約」位元。租客已註冊時走續約邀請（待租客簽回），雙方完成簽署才成立；租客免註冊時建立即沿用原合約狀態、不需簽約。成立不必等舊合約到期。
- 引用：`app/Services/ContractService.php`（`$renewContract = $contract->replicate();`、`續約合約為全新合約，去掉自父合約繼承來的「歷史合約」位元`、`CONTRACT_RENEW_INVITE_LOG`、`CONTRACT_RENEW_CONFIRM_LOG`）。
- ⚠️ 2026-09-27 更正（Plan 9.15 帳本複核 verifier，程式反證）：原引用的 `CONTRACT_SIGNED` 位於「父合約已是歷史時還原」分支，不是租客簽署；原句把兩條流程混為一條。
- 對應格：`ac9b1fdb963f`、`7b6556bf7ee8`。

#### 押金差額入帳只限新北住都延長續約 {#p914-renewal-deposit-diff}
- 事實：押金差額只由新北住都延長續約寫入原押金（`ContractService::nthurcExtension` 寫 `previous_deposit_amount`）。第一張帳單以新押金減原押金：一般押金差額為負列「退押金」（支出）、為正列「押金」補收；**車位押金**不走退押金分支，差額為負時列負數的「車位押金」。
- 事實：非新北住都團隊的一般續約（`ContractService::renew`），第一張帳單不列押金品項（`empty($prevBill) && !$this->isRenewContract()` 才加押金）。
- 邊界：押金區塊的守衛是 `canSeeNthurcSocialHousing() && isRenewContract() && empty($prevBill)`，只看「新北住都綁定團隊＋續約」，沒限定來自 `nthurcExtension`；新北住都團隊的合約若走一般續約，會進這個區塊、原押金缺值時以 0 計（＝列全額押金）。齒輪選單對社宅用途合約不顯示「續約」，但新北住都團隊的非社宅合約能否走到一般續約**未追證**。
- 引用：`app/Contract.php`（`新北住都續約第一筆帳單繳押金計算方式`、`$addToDataForDeposit = function`、`if ($title === '押金' && $isRenewMethod){`、`'title'  => '退押金',`）；`app/Services/ContractService.php:nthurcExtension`；`app/Http/Controllers/ContractController.php`（`property_purpose_key != Contract::SOCIAL_HOUSING`）。
- ⚠️ 主 session 初寫成「續約通用」，fresh verifier 以上述守衛條件推翻（2026-09-26），已收窄；邊界與車位押金兩點是收尾 verifier 的 P3／P4 建議，主 session 對碼後補上。
- 對應格：無（原掛的格改判，見 `p914-no-deposit-carryover`）。

#### 押金不能轉入另一份新合約 {#p914-no-deposit-carryover}
- 事實：系統沒有把舊合約押金移轉到另一份新合約的功能；非續約的新合約第一張帳單一律列全額押金，舊合約的押金走「點退押金」結算。唯一會用原押金算差額的是新北住都延長續約（`p914-renewal-deposit-diff`）。
- 引用：`app/Contract.php`（`if (empty($prevBill) && !$this->isRenewContract()) {`）；`app/Http/Controllers/ContractController.php`（`點退押金`）。
- 否定查詢：`押金轉入|押金轉至|轉押金|押金移轉|沿用押金|押金沿用|押金帶入|transferDeposit` 於 `app`、`src`、`resources`（排除後台與 i18n）0 命中；同範圍正對照「點退押金」65 命中。
- 對應格：`30961bcd1289`（absent，主 session 重新對源）。

#### 提前解約後的帳單 {#p914-early-termination-bills}
- 事實：提前解約確認時把合約 `date_end` 改寫為解約日；每日排程 `bill:gen` 只對 `date_end` 不早於當天的合約產生下一期租金帳單 ⇒ 解約日之後不會再自動產生新帳單。
- 事實：確認解約的流程不刪除也不封存既有帳單。**開啟「合約預覽帳單」的團隊（預設）**在合約成立時已產生全租期帳單，解約日之後的各期都要業者自行封存；關閉預覽帳單的團隊（特定合作團隊）由排程逐月產生，最多多出到下個月的帳單。
- 引用：`app/Services/ContractService.php`（`$contract->date_end = $contract->early_termination_wish_date_end;`）；`app/Console/Commands/CreateRentBill.php`（`$contractsQ->where('date_end', '>=', $now);`、`帳單起始日不得超過本月＋1 月`）；`app/Role.php`（`'IS_OPEN_CONTRACT_BILL_SETTING' => true, // 是否開啟合約預覽帳單`）；`app/Services/ContractService.php:createBillFromDrafts`。
- ⚠️ 2026-09-27 更正（Plan 9.15 帳本複核 verifier，程式反證）：原句「最多多到下個月」只對關閉預覽帳單的團隊成立；原引用的 `BillController:archive` 路由已註解，現行封存走帳單列表／單張的「封存」。
- 對應格：`c18cbfb4fdc7`、`e093019fff73`。

#### 租客不確認點退時，只能由房東取消點退邀請重發 {#p914-moveout-cancel}
- 事實：租客遲不確認點退結果時，系統沒有逾期自動放行；房東可手動取消點退邀請（`cancelMoveOutInvite`，紀錄為「取消點退邀請」），合約退回點退送出前，再重新發送點退清單。
- 引用：`app/Contract.php:CONTRACT_MOVE_OUT_CANCEL_LOG`；`app/Services/ContractService.php:cancelMoveOut`；`app/Http/Controllers/ContractController.php`（`cancelMoveOutInvite`）。
- 對應格：`ebdf63d65846`。

#### 合約匯出 Excel {#p914-contract-export}
- 事實：業者在合約列表勾選後按「匯出合約」（需 `export_contract` 權限），以批次任務（`/api2/getBatchCode` → `JgbJob` → `ContractService::generateReportExcel`）產出 Excel；欄位含租期、每期租金、合約押金等，沒有名為「戶號」的欄位。
- 引用：`src/pages/contracts/list/Index.vue`（`job_name: 'contract_export'`、`permission?.export_contract`）；`app/Jobs/JgbJob.php`（`generateReportExcel`）；`app/Services/ContractService.php`（`___('合約押金', $lang)`）。
- 對應格：`32bef8bcfc9a`、`f481e3a449af`。

#### 合約列表的「標籤」與「是否通知」是兩件事 {#p914-contract-list-tags}
- 事實：合約列表「標籤」欄可逐筆加註（`SurelyVueEstateLabelsCell` 編輯 `record.labels`）；「是否通知」是**物件儀表板合約清單**上的另一欄（寄送通知給租客；以租客身分登入時不顯示這一欄），兩者互相獨立。
- ⚠️ 2026-09-27 更正（Plan 9.15 帳本複核 verifier，程式反證）：原句易讀成兩欄都在合約列表。
- 引用：`src/pages/contracts/list/_parts/ListTable.vue`（`ContractColumnKey.TAGS`）；`src/pages/estates/dashboard/contracts/Index.vue`（`是否通知`）。
- 對應格：`12a91709003b`。

#### 實價登錄匯出 {#p914-real-price-registration}
- 事實：匯出時申報義務人身分可選「不動產經紀業」或「租賃住宅包租業」。
- 事實：建號以物件的 `building_serial_no` 為主，空白時才從物件的建物謄本資料（`building_registration_transcript`）取，不以合約上另填的建號為主。
- 引用：`src/components/Lightbox/EstateTransactionExport.vue`（`不動產經紀業`、`租賃住宅包租業`）；`app/Services/ContractService.php`（`$estate->building_serial_no`、`building_registration_transcript`）。
- 對應格：`b720ccce05ea`、`d5cf3bfccf2d`。

### 帳單、收款與發票

#### 帳單通知的管道與對象 {#p914-bill-notify}
- 事實：**免註冊租客**的帳單通知可分別開關 Email 與簡訊（`should_send_sms` 取自 `lessee_phone_notify_status`），管理者可在租客列表關閉；**已註冊租客**固定收 Email 與站內通知，已綁定 LINE／FB 者另收推播，租客列表的開關對其不可操作，簡訊只有特定合作團隊發送。
- 事實：通知對象是帳單記錄的單一承租人使用者（`bill.user_id`），以其名下的手機與 Email 發送，不會同時發給合約上另一位掛名承租人。
- 引用：`app/Services/BillService.php`（`'should_send_sms' => (bool)$lessee->lessee_phone_notify_status`）；`app/Jobs/BillReadyJob.php`（`$lesseeUserId = $bill->user_id;`）；`src/pages/users/lesseeList/parts/PageTop.vue`（`當通知開關關閉時，租客將無法收到所有的通知`）；`app/Notification.php`（`case 'bill_open'`、`botbonnie_api`）。
- ⚠️ 2026-09-27 更正（Plan 9.15 帳本複核 verifier，程式反證）：原句漏了註冊／免註冊兩種身分的差異。
- 對應格：`085a8e26b78d`、`9def85e08184`、`ac0d6e0e0d61`。

#### 發票預設在帳單收款時開立、依帳單各自開立 {#p914-invoice-per-bill}
- 事實：**預設**發票在帳單被標記已收款時開立；發票依帳單各自開立，不會把不同物件的帳單合併成一張 ⇒ 多個物件各自出帳單就各自開票。
- 例外（程式可證，細節未逐條追）：團隊開啟「預先開立發票」時可選在發送帳單等時機先開；有立即開立權限的團隊可跳過到帳檢查手動先開；有多張發票功能的團隊一張帳單可拆成多張發票。
- 引用：`app/Services/InvoiceService.php`（`發票只在「帳單被標記已收款的那一瞬間」開立`、`// 有立即開立權限的團隊可以跳過到帳檢查`、`isMultiInvoiceEnabledForTeam`）；`src/pages/users/payment/_parts/Invoice.vue`（`labelKey: '預先開立發票',`）。
- ⚠️ 2026-09-27 更正：原句「一張帳單對應一張發票」「收款當下開立」寫成絕對，漏了三種例外（Plan 9.15 S3 E1 verifier 發現）。
- 對應格：`2a20291a87fa`。

#### 線上作廢發票只支援 ezPay {#p914-invoice-void-ezpay}
- 事實：業者可在帳單詳細頁作廢該帳單已開立的發票，但只支援 ezPay；其他發票廠商會被擋下。已開立折讓的發票依 ezPay 規則不可作廢，退費要改走折讓。
- 引用：`app/Services/InvoiceService.php`（`作廢帳單已開立的發票`、`僅支援 ezPay 作廢`）；`app/Http/Controllers/BillController.php:voidInvoice`。
- 對應格：`d7510c45674f`。

#### 差額發票收支表的退款／減免記負數 {#p914-balance-invoice-refund}
- 事實：差額發票收支表把租金退款／減免列在「租金增(減)(B)」欄、以負數（括號）表示，以符合 `F=(A+B)-(C+D)`。
- 引用：`app/Services/BalanceInvoiceService.php`（`記負數(減)以符合 F=(A+B)-(C+D)`）。
- 對應格：`c108fb6b2760`。

#### 不足月租金按天數比例，兩種產帳方式算法不同 {#p914-proration}
- 事實：不足月租金依天數比例，不是固定除以 30。開啟合約預覽帳單的團隊（預設）以「剩餘天數 ÷ 該月曆天數」折算；關閉預覽帳單的團隊與排程逐月產帳以「實際天數 ÷ 該期帳單天數」折算。
- 引用：`app/Services/ContractService.php`（`$realTotalDays / $billTotalDays`，為 `unitCount` 的備援；註解「不足月的情況才看天」）；`app/Services/BillService.php:getMonthCountWithRemainDays`（`date('t',$unixPrevMonth)`）；`app/Contract.php:genBill`。
- ⚠️ 2026-09-27 更正（Plan 9.15 帳本複核 verifier，程式反證）：原句只寫了逐月產帳的算法。
- 對應格：`51f2b99334dd`。

#### 退押金等付給租客的帳單不走固定虛擬帳號 {#p914-refund-bill-account}
- 事實：收款方為租客的支出帳單（如退押金）顯示租客本人的收款銀行帳戶，不使用固定虛擬帳號（那是租客繳款給業者用的）。
- 引用：`app/Http/Controllers/BillController.php`（`固定虛擬帳號是租客繳款用的業者收款帳戶，不適用於退款方向`）。
- 對應格：`4430c67bb850`。

#### 藍新 ATM 虛擬帳號有效 180 天 {#p914-newebpay-atm-expiry}
- 事實：租客線上繳費走藍新取號產生的 ATM 虛擬帳號，呼叫端明帶 `addExpireDays` 180（程式註解記由預設 7 天改為 180 天）；`Payment.php` 的通用預設 7 天只在呼叫端未指定時使用。這是單筆取號的效期，與固定虛擬帳號不同。
- 引用：`app/Http/Controllers/BillController.php`（`'addExpireDays' => 180,`）；`app/Payment.php`（`strtotime('+7 days', $this->payment_ts)`）。
- 對應格：`50586cf08df3`。

#### 信用卡分期是付款方式之一 {#p914-credit-installment}
- 事實：帳單繳費支援信用卡分期（`credit_inst_active`），歸在信用卡類付款方式，依角色的付款設定啟用。
- 引用：`app/Http/Controllers/BillController.php`（`credit_inst_active`）。
- 對應格：`6e235e575ae0`。

#### 「通知已匯款」只出現在非線上收款帳單 {#p914-notify-remittance}
- 事實：租客在「我的帳單」→「待繳帳單」按「通知已匯款」，輸入匯款帳號後五碼送出，也可上傳繳款證明。
- 事實：帳單改走線上金流收款後，「通知已匯款」按鈕與上傳證明畫面都不顯示（`!props.is_online_payment`）。
- 引用：幫助中心 `slug21_zh-Hant.html`；`src/components/Lightbox/BillPayInfo.vue`（`labelKey: '通知已匯款',`、`!props.is_online_payment`）。
- 對應格：`71396382186b`、`7e397e6901b7`、`71e19718ea13`。

#### ATM 匯款金額與帳單不符：國泰／中信／永豐轉待對帳，藍新不動帳 {#p914-atm-amount-mismatch}
- 事實：國泰、中信、永豐的虛擬帳號收到與帳單金額不符的匯款時，帳單轉入待對帳，並寄「收款差額通知」給房東，請其與承租方聯繫或到待對帳確認；這是設計內的正式情境，不是設定異常。**藍新 ATM** 金額不符時刻意不把帳單標成已付款，帳單維持應到帳（仍會通知）。
- 引用：`app/Notification.php`（`租客匯款金額不匹配（國泰ATM），發送通知給房東`）；`app/Payment.php`、`app/Http/Controllers/InternalController.php`（`setAbnormal` 後 `setPaid`）；`app/Http/Controllers/PaymentController.php`（`刻意不自動把帳單標成已付款`）。
- ⚠️ 2026-09-27 更正：原句未分銀行，漏了藍新 ATM 的例外（Plan 9.15 S3 E2 verifier 發現）。
- 對應格：`b1bee098e0f1`。

#### 租客重複匯款時系統怎麼處理 {#p914-duplicate-remittance}
- 事實：匯到**單筆帳單的國泰 ATM 帳號**，若該筆付款已完成（`payment_completed_at` 有值），再入金只記錄「該訂單已被處理」並略過，不會沖到任何帳單。
- 事實：匯到**固定虛擬帳號**的錢一律進該帳號的儲值餘額（`RechargeAccount::recharge()`，內含自動銷帳），多匯的部分留作餘額抵扣後續帳單；同一筆銀行入帳通知重送時以指紋去重，不會重複儲值。
- 引用：`app/Payment.php`（`該訂單已被處理`、`儲值歷程已有本筆指紋，不重複儲值`）；`app/Services/Payment/SinopacVaNotifyService.php`（`把錢加進該固定虛擬帳號的餘額`）。
- 未證：業者端是否有「退還重複匯款」的操作，未追證。
- 對應格：`31b33da327f0`（主 session 重新對源）。

#### 帳單到帳時自動寄收據給租客，前端沒有重寄按鈕 {#p914-receipt-email}
- 事實：帳單轉為已付款（線上付款，或業者手動移至已到帳）時，系統寄款項確認 email 給租客並附收據 PDF（特定客製角色改附其專屬押金收據或不附）；前端沒有「重寄收據」的按鈕。
- 引用：`app/Notification.php`（`case 'bill_paid': // 線上已付款 or 線下按下移至已到帳`、`['Receipt' => $receipt]`）；`app/Bill.php:suppressReceiptEmailAttachment`。
- 否定查詢：`重寄|重新寄送|再次寄送|resend` 於 `src` 0 命中；同範圍正對照「寄送」72 命中。
- 對應格：`b360fbefe4b2`（主 session 重新對源）。

#### 待發送與已到帳帳單都可直接封存 {#p914-bill-archive-states}
- 事實：封存允許「待發送」與「已到帳」兩種狀態，不需先把待發送改成已到帳。
- 引用：`app/Bill.php`（`待發送 & 已到帳 狀態訂單可封存`）。
- 對應格：`b8e89b124c27`。

#### 押金收據號碼是特定團隊的客製功能，手動填、不自動編號 {#p914-deposit-receipt-no}
- 事實：押金收據號碼是**特定合作團隊的客製功能**：由 xlsx 匯出後手填再匯入，同團隊不得重號，系統不自動產生流水號；一般團隊沒有這個欄位。
- 引用：`app/Services/Bills/BillDepositReceiptService.php`（`deposit_receipt_no`）；`app/Http/Controllers/BillController.php:updateDepositReceiptNo`（`此團隊未啟用押金收據功能`）。
- ⚠️ 2026-09-27 更正（Plan 9.15 帳本複核 verifier，程式反證）：原句未限定特定團隊。
- 對應格：`d0e5d8d61fa4`。

#### 草稿帳單電費度數留空、排定／發送時補抓空值、不覆寫已有度數 {#p914-power-reading-draft}
- 事實：草稿帳單的電費度數預設留空，管理者可在編輯頁按「取得即時電錶度數」先帶入；**走排定發送**的帳單（每日自動排定、業者手動排入排定發送清單，以及排定批次寄出）在度數仍為空或 0 時由 `prepareIotMeterForSend()` 自動補抓；已有非 0 度數者不重抓覆寫。**業者直接立即發送**（單張或批次「發送帳單」）不補抓，以畫面現值寄出（`refetchMeterReadingOnSend` 已停用、直接回 false）。
- 引用：`app/Bill.php`（`現在草稿階段度數留空`、`排定發送則由 prepareIotMeterForSend() 補值。`、`if (!is_null($detail->measurement_after) && $detail->measurement_after != 0) continue;`）；呼叫端 `app/Console/Commands/BillAutoBatchSend.php`、`app/Http/Controllers/BillController.php`、`app/Console/Commands/BillBatchSend.php`（`prepareIotMeterForSend()`）。
- 另引：`app/Http/Controllers/BillController.php`（`人工排入排定發送清單時也補入 IoT 電費度數`、`// 注意：本（手動批次）路徑無補值機制`）。
- ⚠️ 2026-09-27 更正兩次：原句「發送一律沿用畫面上的度數」漏了排定發送會補空值；第一次更正寫成「發送當下也補抓」又過頭——立即發送不補（Plan 9.15 S3 E1 兩位 verifier 發現）。
- 對應格：`e6f52da32989`。

#### 常用現金收款帳戶可刪除 {#p914-cash-account-delete}
- 事實：「現金收款帳戶」頁可刪除常用收款帳戶，確認彈窗按「刪除」後即從清單移除。
- 引用：`resources/views/users/payment.blade.php`（`willDeleteCashBank`）。
- 對應格：`4fd26264af84`。

### 物件

#### 真實地址與對外顯示地址是兩個欄位 {#p914-estate-address-fields}
- 事實：物件有 `address`（真實地址）與 `display_address`（對外顯示地址）兩個獨立欄位，改顯示地址不影響真實地址。
- 引用：`resources/structures/estate/edit/form.php`（`'address' => [`、`'display_address' => [`）。
- 對應格：`df73d4aec5d8`。

#### 養寵物／開伙是物件的出租條件，不帶進合約 {#p914-estate-pet-cooking}
- 事實：物件出租資料可設「養寵物」「開伙」條件（`pet_limit`／`fires_limit`），用於招租搜尋篩選，也會出現在合約匯出報表的「條件要求」欄；合約本身（合約資料、範本版位、合約編輯頁）不帶這兩個欄位。要在合約上約定，只能寫進合約的「補充條款」。
- 引用：`app/Estate.php`（`// 是否可養寵物`）；`src/pages/estates/edit/rent_detail/Index.jsx`（`t('養寵物')`）；`app/Jobs/ContractsAllExportJob.php`（`條件要求-養寵物`）；`src/pages/contracts/edit/additionalConvention/Index.vue`（`t('補充條款')`）。
- 否定查詢：`pet_limit|fires_limit` 於 `app/Contract.php`、`config/contract.php`、`app/Services/ContractService.php`、`resources/views/contract`、`src/pages/contracts` 0 命中；同範圍正對照 `deposit` 350 命中。
- 對應格：`c79cb91a25c7`（主 session 重新對源）。

#### 出租與出售刊登是兩個獨立狀態 {#p914-estate-rent-sell}
- 事實：物件以 `is_open`（出租刊登中）與 `sell_is_open`（出售刊登中）兩個欄位分別控制，搜尋可各自篩選。
- 引用：`app/Http/Controllers/EstateController.php`（`"sell_is_open",`、`$searchCriteria['is_open'] = true;`）。
- 對應格：`3c3b910c76d8`。

#### 物件列表可批次刊登／取消刊登 {#p914-estate-batch-listing}
- 事實：物件列表可勾選多筆，批次刊登或批次取消刊登招租廣告。
- 引用：`src/utils/constants/estate.js`（`closeRent: 'estate_batch_close_rent'`）；`src/pages/estates/list/_parts/ListTable.vue`（`批次取消刊登招租廣告`）。
- 對應格：`980f642804b8`。

#### 用途改成車位後看不到「建立合約」 {#p914-estate-parking-create-contract}
- 事實：物件能否建立合約由一組必填欄位（含格局 `space_type`）決定；用途切成車位（`parking_space`）時格局被清空、多數角色看不到該欄 ⇒ 檢查不過、不顯示「建立合約」；改回住宅類用途並填格局即恢復。
- 引用：`app/Estate.php`（`"space_type", // 格局`）；`src/pages/estates/edit/basic/Index.vue`（`editStore.form.space_type = ''`、`premises_use_for === 'parking_space'`）。
- 對應格：`c31398b39a74`。

#### 社區 id 依建立順序遞增 {#p914-community-id}
- 事實：社區資料表 `role_communities` 的 `id` 為自動遞增，依建立順序產生。
- 引用：jgb2 `docs/4-database.md`（`role_communities` 的 `AUTO_INCREMENT`；來源為 jgb2 自帶的 schema 文件，非 migration）。
- 對應格：`97dfb61d7ba5`。

#### 儀表板出租率＝租約中物件數／物件數 {#p914-dashboard-vacancy}
- 事實：儀表板「即時物件出租率」於頁面載入時呼叫 `/api3/users/landlord/vacancy` 取數，公式寫在畫面提示：租約中的物件數量除以物件數量。
- 引用：`src/pages/users/dashboard/parts/Block_Vacancy.vue`（`api3/users/landlord/vacancy`）。
- 對應格：`6daeac687fa1`。

### 帳號、團隊與入口

#### 已綁定的手機在帳號設定頁唯讀 {#p914-account-phone-bound}
- 事實：帳號設定頁手機欄在已綁定時是唯讀停用的輸入框；「前往綁定」按鈕只在未綁定時出現（連到 `users.verify`）。綁定後可用手機號碼登入。
- 邊界：這只證明「帳號設定頁上沒有修改入口」；`/users/verify/phone` 路由本身未限定只給未綁定者，已綁定者能否經由它換號未追證 ⇒ ⛔ 不得說「系統不能改手機」。
- 引用：`resources/views/users/account.blade.php`（`@if( $infoBasic['is_phone_verified'] )`、`前往綁定`）；`routes/web.php:users.verify`；`src/pages/users/auth/parts/PhoneVerify.vue`（`未來可使用電話號碼進行登入`）。
- 對應格：`6b5e55ab0fed`、`f8aefdcdf204`。

#### 團隊成員與大房東分兩頁新增 {#p914-team-vs-big-landlord}
- 事實：團隊頁依路由 `type` 分成「成員」與「大房東」兩頁，同一個新增彈窗依頁面類型只會是其中一種，要分別到兩頁新增。
- 引用：`routes/web.php`（`'/team/{type?}/{action?}/{actionType?}'`）；`resources/views/users/team/index.blade.php`（`USER_RELATED_TYPE_BIG_LANDLORD`）。
- 對應格：`f0130cf80871`。

#### 用瀏覽器使用，沒有原生 APP {#p914-web-not-app}
- 事實：客戶端是瀏覽器存取的 Vue 3 單頁應用（`createWebHistory()`），不是原生手機 APP。
- 引用：`src/routes/index.js`（`createWebHistory()`）。
- 對應格：`cb3aaadfc2e7`。

#### 幫助中心有租客註冊教學文 {#p914-help-tenant-register}
- 事實：幫助中心有「租客系統操作教學—註冊篇」，說明租客收到合約邀請後如何註冊，可分享給租客。
- 引用：幫助中心 `tenantintro.register_zh-Hant.html`。
- 對應格：`c1b660dda7d0`。

### 智慧設備

#### 租客看得到自己合約物件綁定的設備 {#p914-iot-tenant-devices}
- 事實：租客登入後，系統依其執行中的合約找到物件，列出該物件已綁定的 IoT 設備（含電表）。
- 引用：`app/Http/Controllers/IotController.php`（`房客需要從目前執行中的合約找到物件在看是否有綁定iot設備`）。
- 對應格：`612da4251cf4`。

#### 租客專屬門鎖密碼開關掛在裝置上 {#p914-doorlock-tenant-password}
- 事實：租客專屬密碼（預設手機末四碼，租客可自改、房東不能改）的啟用開關是門鎖裝置本身的 `enable_tenant_setlock`，切換即改寫該裝置，沒有依合約生效日或新舊合約區分的邏輯。
- 引用：`resources/views/iot/doorlock/password.blade.php`（`此組預設密碼為租客手機號碼末四碼`）；`app/Http/Controllers/IotController.php`（`$iot->enable_tenant_setlock = $passwordEnable;`）。
- 對應格：`f0da808c0df7`。
