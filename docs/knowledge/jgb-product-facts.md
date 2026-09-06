# JGB 產品事實帳本（受眾中立、逐條對碼）

> **這是什麼**：AI 客服知識的「第 0 層」——只記**程式證明的產品事實**，不寫任何受眾的說法。每條附 jgb2 程式引用（`path:symbol`）、查證日期與分支。售前正本（`rag-orchestrator/canon/prospect.md`）與業者正本各自從這裡**改寫成自己的層級**（售前＝能力／邊界，業者＝操作／狀態），⛔ 不得把一個受眾的細目直接開放給另一個受眾（R3.6）。
> **怎麼引用**：正本細目 `sources: [docs:knowledge/jgb-product-facts.md#<anchor>]`。
> **怎麼維護**：事實變了改這裡、附新引用；⛔ 不在正本裡各自改數字。引用只寫可 grep 的符號，行號只當輔助。
> **查證來源**：`/Users/lenny/jgb/project/jgb/jgb2`（master，2026-09-04 tip，工作樹乾淨）；幫助中心 HTML `JGB幫助中心_HTML_交付_20260818/*_zh-Hant.html`（92 頁）。查證日 2026-09-07。

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
