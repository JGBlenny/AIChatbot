# 產品功能面 × 正本細目 覆蓋盤查（步 0b，2026-09-18）

- 分母：`inputs/feature-surface-20260918.json`（步 0a StepEnvelope）`payload.units[]` — action 45／help 298／route 832，去重後 **1,148 個唯一 unit_id**（原始 1,175 筆含 27 個重複 unit_id，逐格判定按唯一 id 出一格）。
- 產品版本：`payload.sources.jgb2_sha` = `b2ee2ac382ce06763798a7238e4fd5c9411fcfaa`（jgb2 `master`）。
- 逐格判定在 **`feature-coverage-20260918.json`**（每個 unit 恰一格，⛔ 不增刪合併）。本檔只放計數與待補清單，⛔ 不複製 1,148 列。
- 範圍規則：DSP-060（只做包租／代管客群）、DSP-060a（社宅支援不主推）、DSP-054（租客線未開）。
- 驗收：`python3 .claude/skills/outline-curation/scripts/feature_coverage_check.py --surface … --coverage …` → ✅（exit 0）。

## §0 計數

### 依 verdict

| verdict | 數 | 佔比 | 意義 |
|---|---:|---:|---|
| `covered` | 524 | 45.6% | 有細目直接答 |
| `partial` | 276 | 24.0% | 有相近細目但沒答這個功能本身／route 名不明需對碼 |
| `missing` | 88 | 7.7% | 無細目 |
| `tenant_not_open` | 17 | 1.5% | DSP-054 租客線未開，不計缺口 |
| `internal` | 219 | 19.1% | `Admin\*` JGB 內部後台，非客戶功能 |
| `out_of_scope` | 24 | 2.1% | DSP-060 範圍外（學校宿舍、產業內容行銷文） |
| **合計** | **1148** | 100% | |

客戶功能分母（扣掉 `internal` 219 ＋ `tenant_not_open` 17 ＋ `out_of_scope` 24）＝ **888**；其中 `covered` 524（59.0%）、`partial` 276、`missing` 88 ⇒ **缺口 364（41.0%）**。

### 依 unit 種類

| kind | `covered` | `partial` | `missing` | `tenant_not_open` | `internal` | `out_of_scope` | 合計 |
|---|---:|---:|---:|---:|---:|---:|---:|
| action | 31 | 10 | 4 | 0 | 0 | 0 | 45 |
| help | 204 | 32 | 9 | 9 | 0 | 17 | 271 |
| route | 289 | 234 | 75 | 8 | 219 | 7 | 832 |

### 依架（架＝該格對應細目所在架；無細目者依提議歸位）

| 架 | `covered` | `partial` | `missing` | `tenant_not_open` | `internal` | `out_of_scope` | 合計 | 該架現有細目數 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A 帳號與身分 | 36 | 5 | 0 | 0 | 0 | 0 | 41 | 16 |
| B 團隊、人員與大房東 | 44 | 42 | 23 | 0 | 0 | 0 | 109 | 17 |
| C 社區與物件 | 76 | 5 | 16 | 0 | 0 | 0 | 97 | 22 |
| D 租約 | 145 | 30 | 18 | 0 | 0 | 0 | 193 | 55 |
| E 帳務 | 145 | 59 | 1 | 0 | 0 | 0 | 205 | 48 |
| F 修繕 | 17 | 1 | 1 | 0 | 0 | 0 | 19 | 26 |
| G 裝置 | 36 | 0 | 0 | 0 | 0 | 0 | 36 | 12 |
| H 幫助中心 | 0 | 0 | 13 | 0 | 0 | 0 | 13 | 0 |
| I 方案與導入 | 25 | 30 | 16 | 0 | 0 | 0 | 71 | 14 |
| — 無架（基建／內部／範圍外） | 0 | 104 | 0 | 17 | 219 | 24 | 364 | — |

⚠️ **H 架 0 細目**（正對照：A–G、I 八架皆有細目，合計 210；`payload.canon_titles` 內 `shelf=="H"` 為 0 筆，`rag-orchestrator/canon/jgb/H.md` 只有 front matter 與 `## 幫助中心 {#H}`，front matter 自陳「目前空架，存廢另裁」）。幫助中心入口與站內 AI 客服共 14 格全部 `missing`。

## §1 待補清單（`missing` 與 `partial`，依架分組）

同一提議細目會對應多個 unit（一個功能通常散在數條 route／教學段落），以下每行＝一條提議細目：**提議細目標題** ｜ 現況 ｜ 涵蓋 N 格 ｜ 起草來源（代表性 unit_id）。

### B 團隊、人員與大房東（25 條提議、涵蓋 65 格）

- 🟡 **成員／簽約身分列表端點，route 名不明，需對碼** ｜ 無對應細目 ｜ 7 格 ｜ 來源：`route:UserController@/`、`route:UserController@/add`、`route:UserController@/list`…等 7 個
- ❌ **無細目：簽核流程（專案／流程審批）；route 名空白，是否客戶功能需對碼** ｜ 無對應細目 ｜ 6 格 ｜ 來源：`route:ApprovalController@/add`、`route:ApprovalController@/process`、`route:ApprovalController@/process/update/{id}`…等 6 個
- ❌ **無細目：任務管理（週期任務、範圍、複製）** ｜ 無對應細目 ｜ 6 格 ｜ 來源：`route:TaskManagementController@/cycleOptions`、`route:TaskManagementController@/scopeOptions`、`route:TaskManagementController@/search`…等 6 個
- 🟡 **只答「有報表、可排程寄送」；缺報表頁在哪、寄送對象怎麼挑、寄送結果與重算怎麼看** ｜ 現有細目 `jgb/B/owner-report-collection-remit` ｜ 6 格 ｜ 來源：`route:BiglandlordController@/report`、`route:BiglandlordController@/report/fixItemGroupId`、`route:BiglandlordController@/report/markDirty`…等 6 個
- 🟡 **缺「大房東登入後看得到哪些分頁、手機版怎麼看」** ｜ 現有細目 `jgb/B/add-owner-landlord-and-access`、`jgb/B/owner-report-collection-remit` ｜ 5 格 ｜ 來源：`help:Landlordonboarding00_zh-Hant.html#瀏覽物件所屬修繕`、`help:Landlordonboarding00_zh-Hant.html#瀏覽物件所屬合約`、`help:Landlordonboarding00_zh-Hant.html#瀏覽物件所屬帳務`…等 5 個
- 🟡 **缺「大房東手機版看得到什麼」** ｜ 現有細目 `jgb/B/add-owner-landlord-and-access`、`jgb/B/owner-report-collection-remit` ｜ 5 格 ｜ 來源：`help:Landlordonboarding00phone_zh-Hant.html#瀏覽物件所屬修繕`、`help:Landlordonboarding00phone_zh-Hant.html#瀏覽物件所屬合約`、`help:Landlordonboarding00phone_zh-Hant.html#瀏覽物件所屬帳務`…等 5 個
- ❌ **無細目：幣別／匯率設定** ｜ 無對應細目 ｜ 3 格 ｜ 來源：`route:ApiController@/currencyRates`、`route:ApiController@exchangeCurrency`、`route:IndexController@exchange_currency`
- 🟡 **權限細目列有「通知」模組；缺通知中心本身** ｜ 現有細目 `jgb/B/role-permission-granularity` ｜ 3 格 ｜ 來源：`route:IndexController@users.notification`、`route:NotificationController@notifications.index`、`route:NotificationController@notifications.navbar`
- ❌ **無細目：幣別設定** ｜ 無對應細目 ｜ 2 格 ｜ 來源：`route:RoleController@/getCurrency`、`route:RoleController@/setCurrency`
- ❌ **無細目：週期折扣設定** ｜ 無對應細目 ｜ 2 格 ｜ 來源：`route:RoleController@api3.users.advance.getCycleDiscount`、`route:RoleController@api3.users.advance.setCycleDiscount`
- ❌ **無細目：郵件群組怎麼設、寄給誰** ｜ 無對應細目 ｜ 2 格 ｜ 來源：`route:UserController@/mailGroups`、`route:UserController@/mailGroups/update`
- 🟡 **與聯絡簿匯入是否同一功能，route 名不明，需對碼** ｜ 現有細目 `jgb/B/owner-landlord-contact-book-import-export` ｜ 2 格 ｜ 來源：`route:BiglandlordController@api.biglandlord.record.excel.confirm`、`route:BiglandlordController@api.biglandlord.record.excel.preview`
- 🟡 **缺物件月結單在哪看、內容是什麼、與大房東月報的關係** ｜ 現有細目 `jgb/B/owner-report-collection-remit` ｜ 2 格 ｜ 來源：`route:EstateController@/monthlyReport/list`、`route:EstateController@api.get.estate.monthly.report.list`
- 🟡 **缺「怎麼建團隊、團隊資訊有哪些欄位、能不能刪團隊」的業者操作** ｜ 現有細目 `jgb/B/team-management-overview` ｜ 2 格 ｜ 來源：`route:UserController@/company/create`、`route:UserController@/company/delete`
- 🟡 **缺報表寄送操作（對象、排程、結果）** ｜ 現有細目 `jgb/B/owner-report-collection-remit` ｜ 2 格 ｜ 來源：`route:UserController@/sendMultiTeamReport`、`route:UserController@/sendReport`
- ❌ **無細目：團隊通知信怎麼編輯、系統會發哪些通知** ｜ 無對應細目 ｜ 1 格 ｜ 來源：`action:edit_notification`
- ❌ **無細目：簽核流程（專案／流程審批）** ｜ 無對應細目 ｜ 1 格 ｜ 來源：`route:IndexController@users.approval`
- 🟡 **只答「有報表、可排程寄送」；缺報表頁在哪、寄送對象怎麼挑、寄送結果怎麼查** ｜ 現有細目 `jgb/B/owner-report-collection-remit` ｜ 1 格 ｜ 來源：`action:show_biglandlord_report`
- 🟡 **權限細目列有「通知」模組；缺通知中心在哪看、有哪些通知** ｜ 現有細目 `jgb/B/role-permission-granularity` ｜ 1 格 ｜ 來源：`action:show_notification`
- 🟡 **缺大房東登入後看得到哪些合約分頁** ｜ 現有細目 `jgb/B/add-owner-landlord-and-access` ｜ 1 格 ｜ 來源：`action:show_owner_contract`
- 🟡 **缺大房東端歷史合約檢視範圍** ｜ 現有細目 `jgb/B/add-owner-landlord-and-access`、`jgb/D/contract-history-retention` ｜ 1 格 ｜ 來源：`action:show_owner_contract_history`
- 🟡 **缺大房東端已簽署合約檢視範圍** ｜ 現有細目 `jgb/B/add-owner-landlord-and-access` ｜ 1 格 ｜ 來源：`action:show_owner_contract_signed`
- 🟡 **缺大房東端修繕檢視範圍** ｜ 現有細目 `jgb/B/add-owner-landlord-and-access`、`jgb/F/repair-progress-followup-scope` ｜ 1 格 ｜ 來源：`action:show_owner_repair`
- 🟡 **缺「怎麼建團隊」的業者操作步驟（現有細目是售前語氣）** ｜ 現有細目 `jgb/B/team-management-overview` ｜ 1 格 ｜ 來源：`help:Landlordonboarding02_zh-Hant.html#創建團隊`
- 🟡 **缺「團隊資訊有哪些欄位、在哪改」** ｜ 現有細目 `jgb/B/team-management-overview`、`jgb/A/account-profile-settings` ｜ 1 格 ｜ 來源：`help:Landlordonboarding02_zh-Hant.html#團隊設置`

### C 社區與物件（8 條提議、涵蓋 21 格）

- ❌ **無細目：買賣物件怎麼刊登、與招租差在哪** ｜ 無對應細目 ｜ 6 格 ｜ 來源：`help:property_zh-Hant.html#買賣`、`route:EstateController@api2.estate.sell-close`、`route:EstateController@estates.sell-close`…等 6 個
- ❌ **無細目：物件刪除／批次刪除的條件與後果** ｜ 無對應細目 ｜ 4 格 ｜ 來源：`route:EstateController@api2.estate.batchDelete`、`route:EstateController@api2.estate.batchPreValidate`、`route:EstateController@api2.estate.delete`…等 4 個
- 🟡 **缺加密連結公開頁是什麼、分享給誰、對方能填什麼** ｜ 現有細目 `jgb/C/storefront-entry-share` ｜ 4 格 ｜ 來源：`route:IndexController@users.info`、`route:UserController@api3.get.users.estates`、`route:UserController@api3.get.users.infos`…等 4 個
- ❌ **無細目：社區投報率／投資成本與報表；route 名空白需對碼** ｜ 無對應細目 ｜ 3 格 ｜ 來源：`route:CommunityRoiController@/investments`、`route:CommunityRoiController@/operationDates`、`route:CommunityRoiController@/report`
- ❌ **無細目：物件清單怎麼匯出、匯出哪些欄位** ｜ 無對應細目 ｜ 1 格 ｜ 來源：`action:export_estate`
- ❌ **無細目：複製現有物件怎麼做（正本只有合約複製，沒有物件複製）** ｜ 無對應細目 ｜ 1 格 ｜ 來源：`help:onboarding4_zh-Hant.html#二、複製現有物件`
- ❌ **無細目：複製現有物件怎麼做** ｜ 無對應細目 ｜ 1 格 ｜ 來源：`route:EstateController@estates.copy`
- 🟡 **需對碼：estates.edit 實際指向 estates/monthlyUpload** ｜ 現有細目 `jgb/C/property-edit-vs-publish` ｜ 1 格 ｜ 來源：`route:IndexController@estates.edit`

### D 租約（18 條提議、涵蓋 48 格）

- 🟡 **只提到租客資料卡；缺租客名單模組本身** ｜ 現有細目 `jgb/D/contract-lookup` ｜ 13 格 ｜ 來源：`route:IndexController@users.lesseeList`、`route:LesseeController@/subscribe`、`route:LesseeController@api.lessee.archive`…等 13 個
- 🟡 **缺批次刪除合約的條件與 archive 分類意義** ｜ 現有細目 `jgb/D/contract-cancel-delete` ｜ 5 格 ｜ 來源：`route:ContractController@/archive/{category}`、`route:ContractController@api2.contract.batchDelete`、`route:ContractController@api2.contract.batchPreValidate`…等 5 個
- ❌ **無細目：社宅清冊列表怎麼產生、編輯、匯出** ｜ 無對應細目 ｜ 4 格 ｜ 來源：`action:edit_social_housing_sheet`、`help:Landlordonboarding09Socialhousing_zh-Hant.html#清冊列表功能`、`route:BillController@/api2/bill/socialHousingSheets/{action?}/{subAction?}`…等 4 個
- ❌ **無細目：租客批次匯入（範本、預覽、確認）** ｜ 無對應細目 ｜ 4 格 ｜ 來源：`route:LesseeController@api.lessee.batch.confirm`、`route:LesseeController@api.lessee.batch.import`、`route:LesseeController@api.lessee.batch.preview`…等 4 個
- ❌ **無細目：房東節稅（一般房東／公益出租人／社宅包管）** ｜ 無對應細目 ｜ 3 格 ｜ 來源：`help:rentallaw.pt5_zh-Hant.html#【公益出租人】`、`help:rentallaw.pt5_zh-Hant.html#【委託包租代管的一般房東】`、`help:rentallaw.pt5_zh-Hant.html#【社宅包租代管房東】`
- ❌ **無細目：租客信用評等** ｜ 無對應細目 ｜ 3 格 ｜ 來源：`route:TenantCreditRatingController@api.lessee.creditRating.overview`、`route:TenantCreditRatingController@api.lessee.creditRating.store`、`route:TenantCreditRatingController@api.lessee.creditRating.update`
- 🟡 **細目講系統內歷史合約保留；缺法定契約保存期限與請求權時效** ｜ 現有細目 `jgb/D/contract-history-retention` ｜ 3 格 ｜ 來源：`help:law20250520_zh-Hant.html#一、租賃契約書的保存期限（法律雖無明文強制，實務仍建議保留）`、`help:law20250520_zh-Hant.html#二、相關法律追溯期（請求權時效）`、`help:law20250520_zh-Hant.html#總結建議`
- ❌ **無細目：租賃專法對房東／租客各自的影響與常見糾紛保障** ｜ 無對應細目 ｜ 2 格 ｜ 來源：`help:rentallaw.pt2_zh-Hant.html#一、對房東的影響——房東常見的租屋糾紛是否能以租賃專法保障？`、`help:rentallaw.pt2_zh-Hant.html#二、對租客的影響——租客常見的租屋糾紛是否能以租賃專法保障？`
- 🟡 **細目只寫電子簽約 72 小時審閱期；缺法定契約審閱權與各類契約最少審閱天數** ｜ 現有細目 `jgb/D/esign-legal-validity` ｜ 2 格 ｜ 來源：`help:contract_review_period_zh-Hant.html#1.契約審閱權`、`help:contract_review_period_zh-Hant.html#2.不動產租賃相關契約至少之審閱天數`
- ❌ **無細目：租賃專法重點** ｜ 無對應細目 ｜ 1 格 ｜ 來源：`help:rentallaw.pt1_zh-Hant.html`
- ❌ **無細目：DIY 合約；是否已對客戶開放需對碼** ｜ 無對應細目 ｜ 1 格 ｜ 來源：`route:Jgb3\ContractController@contracts.diyContract`
- 🟡 **只寫建約時在「經理人資訊」選；缺已建合約怎麼改派經理人** ｜ 現有細目 `jgb/D/contract-esign-flow` ｜ 1 格 ｜ 來源：`action:assign_contract`
- 🟡 **只答單份合約 PDF；缺合約清單匯出 Excel 的入口與欄位** ｜ 現有細目 `jgb/D/contract-pdf-download` ｜ 1 格 ｜ 來源：`action:export_contract`
- 🟡 **只提到租客資料卡；缺租客名單模組本身（新增／封存／狀態／一鍵聯繫）** ｜ 現有細目 `jgb/D/contract-lookup` ｜ 1 格 ｜ 來源：`action:show_lessee`
- 🟡 **缺「社宅團隊怎麼建、跟一般團隊差在哪」** ｜ 現有細目 `jgb/D/social-housing-lease` ｜ 1 格 ｜ 來源：`help:Landlordonboarding09Socialhousing_zh-Hant.html#創建社宅團隊`
- 🟡 **缺「租客資料卡看得到哪些聯絡方式、一鍵聯繫怎麼用」** ｜ 現有細目 `jgb/D/contract-lookup` ｜ 1 格 ｜ 來源：`help:slug101_zh-Hant.html#📌 小提醒`
- 🟡 **實價登錄檔案下載，route 名不明，需對碼** ｜ 無對應細目 ｜ 1 格 ｜ 來源：`route:DownloadController@actual-price-registrations/{filename}`
- 🟡 **缺補充條款範本怎麼建與套用** ｜ 現有細目 `jgb/D/contract-attachments-notes-limits` ｜ 1 格 ｜ 來源：`route:UserController@/customAdditionalTermsTemplate`

### E 帳務（22 條提議、涵蓋 60 格）

- 🟡 **細目答概念與金額計算；缺模組操作（重產 Excel／重開／作廢／群組／報表／操作紀錄）** ｜ 現有細目 `jgb/E/differential-invoice` ｜ 12 格 ｜ 來源：`route:BalanceInvoiceController@/`、`route:BalanceInvoiceController@activityLogs`、`route:BalanceInvoiceController@export`…等 12 個
- 🟡 **細目只講帳單繳費後下載收據；缺押金收據編號設定與批次預覽／匯出 PDF** ｜ 現有細目 `jgb/E/bill-receipt-pdf` ｜ 8 格 ｜ 來源：`route:BillController@bills.deposit_receipt.confirm`、`route:BillController@bills.deposit_receipt.export`、`route:BillController@bills.deposit_receipt.export_pdf`…等 8 個
- 🟡 **E 架金流清單未含愛金卡（I 架有提）；缺愛金卡怎麼開通、租客怎麼付** ｜ 現有細目 `jgb/E/payment-gateway-options` ｜ 7 格 ｜ 來源：`route:Vendors\ICashPayController@/getMemberRegisterUrl`、`route:Vendors\ICashPayController@api.icashpay.receiveICPMemberRegister`、`route:Vendors\ICashPayController@api.icashpay.receivePaymentInfo`…等 7 個
- 🟡 **EscrowUser（履約／代收付專戶？）語意不明，需對碼** ｜ 無對應細目 ｜ 5 格 ｜ 來源：`route:EscrowUserController@/add`、`route:EscrowUserController@/delete/{escrowUserId}`、`route:EscrowUserController@/list`…等 5 個
- 🟡 **缺批次編輯帳單費用的入口與可改範圍** ｜ 現有細目 `jgb/E/bill-contents-extra-fees` ｜ 4 格 ｜ 來源：`help:Landlordonboarding06Finance_zh-Hant.html#批次編輯帳單`、`route:BillController@bills.batch_fee_edit.confirm`、`route:BillController@bills.batch_fee_edit.load`…等 4 個
- 🟡 **缺「款項撥到哪、何時撥、金流後台怎麼提款」** ｜ 現有細目 `jgb/E/payment-gateway-setup` ｜ 4 格 ｜ 來源：`help:advanced12_zh-Hant.html#⚠️ 版本更新`、`help:advanced12_zh-Hant.html#個人房東：登入藍新後台`、`help:advanced12_zh-Hant.html#法人（團隊）房東：登入藍新後台`…等 4 個
- 🟡 **缺「款項匯到哪、怎麼提領」的獨立細目** ｜ 現有細目 `jgb/E/payment-gateway-options`、`jgb/E/payment-gateway-setup` ｜ 2 格 ｜ 來源：`help:paymentapply_zh-Hant.html#款項會匯到哪裡？`、`help:paymentapply_zh-Hant.html#款項要怎麼提領？`
- 🟡 **「ziyu」是否為通用批次改單功能，route 名不明，需對碼** ｜ 現有細目 `jgb/E/bill-contents-extra-fees` ｜ 2 格 ｜ 來源：`route:BillController@bills.batch_edit_ziyu.export`、`route:BillController@bills.batch_edit_ziyu.import`
- 🟡 **只在差額發票細目順帶提到可匯出租金收支明細表；缺申報入口與申報代理人設定，route 名不明需對碼** ｜ 現有細目 `jgb/E/differential-invoice` ｜ 2 格 ｜ 來源：`route:ContractController@/declaration/export`、`route:ContractController@/declaration/reporting-agents`
- 🟡 **缺團隊層自訂費用品項在哪維護、影響哪些帳單** ｜ 現有細目 `jgb/E/bill-contents-extra-fees` ｜ 2 格 ｜ 來源：`route:RoleController@/additions`、`route:RoleController@feeCategories`
- ❌ **無細目：帳單操作紀錄（誰改了什麼、何時改）** ｜ 無對應細目 ｜ 1 格 ｜ 來源：`route:BillController@bills.activity_logs`
- 🟡 **缺社宅帳務模組（清冊、押租金、補貼分帳）的操作** ｜ 現有細目 `jgb/E/differential-invoice` ｜ 1 格 ｜ 來源：`help:Landlordonboarding09Socialhousing_zh-Hant.html#社宅帳務功能`
- 🟡 **缺金流後台登入與帳號規則說明** ｜ 現有細目 `jgb/E/payment-gateway-setup` ｜ 1 格 ｜ 來源：`help:advanced12_zh-Hant.html#企業會員帳號：統一編號`
- 🟡 **缺金流後台登入與預設密碼說明** ｜ 現有細目 `jgb/E/payment-gateway-setup` ｜ 1 格 ｜ 來源：`help:advanced12_zh-Hant.html#個人房東預設密碼：身分證字號`
- 🟡 **細目寫「只能綁一家」；「單一金流設定多組帳號」說法需對碼** ｜ 現有細目 `jgb/E/payment-gateway-setup` ｜ 1 格 ｜ 來源：`help:landlordonboarding05Paymentsettings_zh-Hant.html#單一金流設定多組帳號`
- 🟡 **缺物件層自訂費用品項怎麼設** ｜ 現有細目 `jgb/E/bill-contents-extra-fees` ｜ 1 格 ｜ 來源：`route:EstateController@estates.custom_fees`
- 🟡 **需對碼：中信入帳內部端點是否屬自動對帳鏈** ｜ 現有細目 `jgb/E/bill-status-reconciliation` ｜ 1 格 ｜ 來源：`route:InternalController@/internal_api/ctbc_received/{payment}`
- 🟡 **需對碼：deviceType mode 是否即六種電費模式** ｜ 現有細目 `jgb/E/utility-meter-billing-and-reading` ｜ 1 格 ｜ 來源：`route:IotController@/{deviceType}/mode`
- 🟡 **缺信用卡退刷怎麼處理** ｜ 現有細目 `jgb/E/payment-amount-mismatch` ｜ 1 格 ｜ 來源：`route:PaymentController@payments.credit_card.refund`
- 🟡 **細目金流清單只列藍新／永豐／國泰／中信，未含台新；是否已上線需對碼** ｜ 現有細目 `jgb/E/payment-gateway-options` ｜ 1 格 ｜ 來源：`route:TaishinVaNotifyController@payments.taishin.va_received`
- 🟡 **細目金流清單未含 ubot（聯邦？）；需對碼** ｜ 現有細目 `jgb/E/payment-gateway-options` ｜ 1 格 ｜ 來源：`route:UbotVaNotifyController@payments.ubot.va_received`
- 🟡 **缺自訂費用品項在哪維護** ｜ 現有細目 `jgb/E/bill-contents-extra-fees` ｜ 1 格 ｜ 來源：`route:UserController@/customFeeItems/{action?}`

### F 修繕（2 條提議、涵蓋 2 格）

- ❌ **無細目：修繕清單怎麼匯出** ｜ 無對應細目 ｜ 1 格 ｜ 來源：`action:export_repair`
- 🟡 **需對碼：修繕單分享連結** ｜ 現有細目 `jgb/F/repair-dispatch-and-close` ｜ 1 格 ｜ 來源：`route:RepairController@/api2/repairItem/share/{id?}`

### H 幫助中心（3 條提議、涵蓋 13 格）

- ❌ **H 架 0 細目：幫助中心入口與站內 AI 客服無細目** ｜ 無對應細目 ｜ 9 格 ｜ 來源：`route:HelpAssistantController@/api2/assistant/chat`、`route:HelpAssistantController@/api2/assistant/chat-scenarios`、`route:HelpAssistantController@/api2/assistant/enabled`…等 9 個
- ❌ **H 架 0 細目：幫助中心入口無細目** ｜ 無對應細目 ｜ 3 格 ｜ 來源：`route:IndexController@/api2/helpCenter/{action?}`、`route:UserController@users.help`、`route:UserController@users.help-content`
- ❌ **H 架 0 細目：幫助中心頁面入口無細目** ｜ 無對應細目 ｜ 1 格 ｜ 來源：`route:ListingController@/help/{any?}/{slug?}`

### I 方案與導入（15 條提議、涵蓋 46 格）

- 🟡 **對外開放 API，是否對客戶／合作夥伴開放需對碼（售前會問能不能串自家系統）** ｜ 無對應細目 ｜ 22 格 ｜ 來源：`route:External\BillApiController@api.external.bills.index`、`route:External\BillApiController@api.external.bills.show`、`route:External\ContractApiController@api.external.contracts.status-overview`…等 22 個
- 🟡 **外部介接 token／端點，是否對客戶開放需對碼** ｜ 無對應細目 ｜ 4 格 ｜ 來源：`route:ExternalController@/external_api/estate`、`route:ExternalController@/external_api/nthurc`、`route:ExternalController@/external_api/thinkcloud/{action?}`…等 4 個
- ❌ **無細目：新手「必做事項」引導** ｜ 無對應細目 ｜ 3 格 ｜ 來源：`route:ApiController@/mustDo`、`route:ApiController@/mustDo/completed`、`route:ApiController@/mustDo/readLog`
- ❌ **無細目：LINE bot／LIFF 串接** ｜ 無對應細目 ｜ 3 格 ｜ 來源：`route:LineController@lines.bot`、`route:LineController@lines.liff`、`route:LineController@lines.log`
- ❌ **無細目：LINE 官方帳號（Botbonnie）串接怎麼綁** ｜ 無對應細目 ｜ 2 格 ｜ 來源：`route:BotbonnieSettingController@admin.botbonnie.bind`、`route:BotbonnieSettingController@admin.botbonnie.callback`
- ❌ **無細目：新人禮／行銷獎勵** ｜ 無對應細目 ｜ 2 格 ｜ 來源：`route:IndexController@/api2/marketingBonus`、`route:IndexController@marketing.welcome-bonus`
- 🟡 **缺訂閱付款／訂單紀錄在哪查** ｜ 現有細目 `jgb/I/subscription-change-renewal` ｜ 2 格 ｜ 來源：`route:IndexController@users.orders`、`route:IndexController@users.payment`
- ❌ **無細目：LINE 官方帳號（Botbonnie）webhook** ｜ 無對應細目 ｜ 1 格 ｜ 來源：`route:BotbonnieWebhookController@admin.botbonnie.webhook`
- ❌ **無細目：行銷邀請碼** ｜ 無對應細目 ｜ 1 格 ｜ 來源：`route:MarketingInviteController@marketing.invite`
- ❌ **無細目：促銷活動代碼** ｜ 無對應細目 ｜ 1 格 ｜ 來源：`route:PromotionController@promotion.index`
- ❌ **無細目：推薦制度／推薦碼** ｜ 無對應細目 ｜ 1 格 ｜ 來源：`route:ReferralController@referral.users.create`
- ❌ **無細目：優惠券／折扣碼** ｜ 無對應細目 ｜ 1 格 ｜ 來源：`route:UserController@users.coupon`
- ❌ **無細目：LINE 對話／串接** ｜ 無對應細目 ｜ 1 格 ｜ 來源：`route:UserController@users.lineChat`
- 🟡 **缺訂閱扣款紀錄在哪查、看得到哪些欄位** ｜ 現有細目 `jgb/I/subscription-change-renewal` ｜ 1 格 ｜ 來源：`route:PaymentController@/rolePayments`
- 🟡 **缺訂閱扣款紀錄在哪查** ｜ 現有細目 `jgb/I/subscription-change-renewal` ｜ 1 格 ｜ 來源：`route:UserController@users.paymentLogs`

### A 帳號與身分（3 條提議、涵蓋 5 格）

- 🟡 **細目只教「聯繫客服查發送紀錄」；缺業者自己在哪查 E-mail 發送紀錄** ｜ 現有細目 `jgb/A/verification-code-not-received` ｜ 3 格 ｜ 來源：`action:show_email_log`、`route:UserController@getDashboardEmailLogs`、`route:UserController@users.roleEmail`
- 🟡 **缺「團隊資訊有哪些欄位、在哪改」** ｜ 現有細目 `jgb/A/account-profile-settings`、`jgb/B/team-management-overview` ｜ 1 格 ｜ 來源：`help:onboarding2_zh-Hant.html#二、團隊帳號篇：`
- 🟡 **缺「租客沒上傳身分證時怎麼繼續簽約」** ｜ 現有細目 `jgb/A/account-profile-settings`、`jgb/D/contract-esign-flow` ｜ 1 格 ｜ 來源：`help:qa07_zh-Hant.html#📌 小提醒`

### — 無架（基建／內部／範圍外）（7 條提議、涵蓋 104 格）

- 🟡 **route 名不明，需對碼** ｜ 無對應細目 ｜ 45 格 ｜ 來源：`route:AdvertisementController@/redirect/{adType}/{adId}`、`route:Api\FacilitiesController@/config`、`route:Api\FeatureConfigApiController@/config`…等 45 個
- 🟡 **`Internal\` 命名空間＝AI／維運內部 API，0a 未標 internal，歸類需對碼** ｜ 無對應細目 ｜ 20 格 ｜ 來源：`route:Internal\AgentManageController@/agents`、`route:Internal\AgentManageController@/agents/{id}/active`、`route:Internal\AgentManageController@/agents/{id}/permissions`…等 20 個
- 🟡 **基礎資料／前端資產端點，route 名不明，需對碼** ｜ 無對應細目 ｜ 15 格 ｜ 來源：`route:ApiController@/`、`route:ApiController@/api2/getAside`、`route:ApiController@/api2/getCurrentUser`…等 15 個
- 🟡 **工具／代登入端點，route 名不明，需對碼** ｜ 無對應細目 ｜ 10 格 ｜ 來源：`route:ToolController@/cmd`、`route:ToolController@/recharge/{key}`、`route:ToolController@/short_url/{key}`…等 10 個
- 🟡 **Monday 工單統計，疑為 JGB 內部管理但 0a 未標 internal，歸類需對碼** ｜ 無對應細目 ｜ 8 格 ｜ 來源：`route:MondayStatisticController@/export`、`route:MondayStatisticController@/import`、`route:MondayStatisticController@/send-email`…等 8 個
- 🟡 **SEO sitemap 端點，非客戶功能，歸類需對碼** ｜ 無對應細目 ｜ 5 格 ｜ 來源：`route:SitemapController@sitemaps.estate_ad`、`route:SitemapController@sitemaps.help_center`、`route:SitemapController@sitemaps.index`…等 5 個
- 🟡 **第三方 log viewer，0a 未標 internal，歸類需對碼** ｜ 無對應細目 ｜ 1 格 ｜ 來源：`route:\Rap2hpoutre\LaravelLogViewer\LogViewerController@admin.tools.laravel_log`

## §2 判定備註

1. **自動歸類（不逐格判斷）**：`internal=true`（219 格，全為 `Admin\*`）一律 `internal`；`side=租客側` 且非 internal（17 格）一律 `tenant_not_open`（DSP-054）。⚠️ 有 4 格 `Admin\CustomerServiceController@admin.customer_service.add_tenant*` 同時 `internal=true` 且 `side=租客側`，本檔以 internal 優先。
2. **route 判定以 controller 為預設、route name 為覆寫**，但每個 unit 仍各出一格。route name 空白或語意不明者一律 `partial` ＋ 註記「需對碼」，⛔ 不猜功能——共 166 格（含 `Internal\*` 20、`External\*` 22、`ApiController` 基礎資料 15、`ToolController` 10、`MondayStatisticController` 8、`SitemapController` 5 等）。
3. **`internal` 旗標只涵蓋 `Admin\*`**：`Internal\*`（AI／維運內部 API）、`MondayStatisticController`（Monday 工單統計）、`\Rap2hpoutre\…\LogViewerController`（第三方 log viewer）、`SitemapController`（SEO）在 0a 未標 internal，本檔依契約不自行改判，一律 `partial`＋註記歸類需對碼。**這批 34 格若改判 internal，客戶功能分母會再降。**
4. **`out_of_scope`（24 格）**：`NthurcController`／`NthurcParkingController`／`IndexController@nthurc.*`（清大宿舍＝學校宿舍客群，DSP-060 不納入）＋ 4 篇產業／時事內容行銷文（`beike`／`esg`／`propmarket2`／`sea-internet`）的 17 個段落。
5. **社宅（DSP-060a 支援不主推）仍計缺口**：社宅合約、社宅物件批次、押租金帳單皆 `covered`；但「社宅清冊列表」（`action:edit_social_housing_sheet` 有專屬 permission action）4 格全 `missing`。
6. **架間不一致（已標 partial，需裁決）**：(a) `jgb/E/payment-gateway-options` 只列藍新／永豐／國泰／中信，但 route 有 `payments.taishin.va_received`、`payments.ubot.va_received`、`Vendors\ICashPayController`（愛金卡）——愛金卡在 `jgb/I/why-choose-jgb` 有提、E 架沒有；(b) `jgb/A/verification-code-not-received` 教「聯繫客服查發送紀錄」，但產品有 `actions.show_email_log` 與 `users.roleEmail`／`getDashboardEmailLogs` 自助查詢入口。
7. **否定結論的正對照**：判「正本沒有某功能」前，同一輪 grep 必含已知必然命中的詞。實測 `報表`（B/E/I 命中）、`押金`（D 121 次）、`門鎖`（G 33 次）命中，而 `簽核`／`審批`／`任務`／`待辦`／`評等`／`介接`／`幣別` 在 `rag-orchestrator/canon/jgb/[A-I].md` 全部 0 命中 ⇒ 工具正常、`missing` 結論成立。
8. **可重跑的查證指令**：
   - 驗收：`python3 .claude/skills/outline-curation/scripts/feature_coverage_check.py --surface .kiro/specs/knowledge-outline-and-intent-architecture/inputs/feature-surface-20260918.json --coverage .kiro/specs/knowledge-outline-and-intent-architecture/inputs/feature-coverage-20260918.json`
   - H 架空架：`grep -c '^### ' rag-orchestrator/canon/jgb/H.md`（預期 0）
   - 某功能是否在正本：`grep -n '<關鍵詞>' rag-orchestrator/canon/jgb/[A-I].md`（⛔ 必附一個已知會命中的正對照詞）
