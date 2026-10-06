# Plan 9.31 業主抽查 30 句（目標驗收規格 §2.2）

> 抽樣：`random.Random(20261006).sample(母體, 30)`；母體＝正本 `jgb.json` 已審細目全部內容句（依檔內順序，元素＝(細目 id, 句序)），共 **1538** 句；正本 `canon_sha256 = 8a5844bcc85dfe43d2f52f135d285e3beae8fbbf8858adac9b4f1ff09d4ec62f`；HEAD `3d0cba8ad72111a97eee689fcc2b1d55daf02c31`。腳本與重現檢查見計畫 §6。
> **判定方式**（業主 2026-10-06 改定「指定獨立代理判，我只裁疑義句 (Recommended)」）：一位 fresh 獨立代理逐句對源（混 1 條誘餌、誘餌有抓到），判不成立的 4 句由業主裁定。結果：**成立 26／30、不成立 4**（#2、#5、#14、#26），轉下一份計畫修正。
> **來源怎麼看**：`code:<路徑>` ＝ jgb2 commit `b2ee2ac382ce` 的該檔；`help:<檔名>` ＝ 幫助中心交付檔；`docs:<路徑>#<錨點>` ＝ 本 repo 事實帳本該條。
> ⚠️ **句序限制**：drafts 的引文句序已知有 23 條細目錯位（沒有清單）。所以每節列出該細目**全部**引文；標「drafts 自報對應本句」的只是 drafts 記的句序，**請以引文內容判斷是否支持本句**，不要只看標記。標「⚠️ 來源位置需人工指認」的節，表示機械對應失敗。

## 1. `jgb/E/bill-cycle-amortization` 第 2 句

- 粗目：建立與編輯帳單（單筆、批次、週期批次）
- 細目標題：「總額（自動分攤）」欄位什麼時候才會出現？（只有新增週期帳單、且團隊開通社區投報率時）
- target_user：property_manager
- **抽查句**：「金額輸入方式」預設是「每期金額」，費用欄位填的金額會套用到每一期；改選「總額（自動分攤）」時，費用欄位改填整筆總金額，由系統拆分到各期。
- sources：`code:src/pages/bills/edit/_parts/BillBasicInfoSection.vue`
- 引文（該細目全部 3 筆）：
  - [同細目其他句的引文｜drafts 句序 0] `code:src/pages/bills/edit/_parts/BillBasicInfoSection.vue`：`canUseAmortization: computed(()=>route.name === 'bills.create.cycleBatch' && features.isCommunityRoiEnabled.value),`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 1] `code:src/pages/bills/edit/_parts/BillBasicInfoSection.vue`：`canUseAmortization: computed(()=>route.name === 'bills.create.cycleBatch' && features.isCommunityRoiEnabled.value),`
  - [同細目其他句的引文｜drafts 句序 2] `code:src/components/Lightbox/BillCycleConfirmBeforeSend.vue`：`// 該模式的金額是「總額平均分成 N 份、零頭歸最後一期」，一旦改某期起訖日就按比例`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 2. `jgb/A/notification-settings-extra-emails` 第 3 句

- 粗目：通知收件設定與發送報表（通知收件信箱最多再加 3 組）
- 細目標題：通知收件信箱最多能加幾組？（每個通知分類最多再加 3 組電子信箱）
- target_user：property_manager
- **抽查句**：每個通知分類卡片內都可各自新增/移除最多 3 組自訂收件信箱，每組都是標準 Email 格式輸入框且為必填，彼此分類互不共用額度。
- sources：`code:src/pages/users/notification/Index.vue`
- 引文（該細目全部 9 筆）：
  - [同細目其他句的引文｜drafts 句序 0] `code:src/pages/users/notification/Index.vue`：`t('每個通知信最多可再新增 3 組電子信箱收取通知信件。')`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/users/notification/Index.vue`：`v-model="formData.defaultEmail"`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/users/notification/Index.vue`：`disabled`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 2] `code:src/pages/users/notification/Index.vue`：`mailAmountLimit: 3,`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 2] `code:src/pages/users/notification/Index.vue`：`type="email"`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/users/notification/Index.vue`：`hasPermissionToEdit: computed(()=>store.state.userData?.permission?.edit_notification || false),`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/users/notification/Index.vue`：`<template v-if="state.hasPermissionToEdit">`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/users/notification/Index.vue`：`:class="['relative', `${ state.hasPermissionToEdit ? '' : 'disabled' }`]">`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/users/notification/Index.vue`：`if (!state.hasPermissionToEdit){`
- **判定**：**不成立**（獨立代理判不成立，業主 2026-10-06 裁定：「不成立 (Recommended)」）。代理理由：src/pages/users/notification/Index.vue：每分類上限 `mailAmountLimit: 3,`、輸入框 `type="email"` 加 `required`、額度以 `formData.emailData?.[category.key]?.custom_emails?.length < state.mailAmountLimit` 逐分類計算，這幾點成立。但句子寫「每個通知分類卡片內都可各自新增/移除」是絕對句，漏了權限例外：「新增信箱」按鈕的條件是 `&& state.hasPermissionToEdit`，`handleAddEmail`／`handleRemoveEmail` 一開頭就 `if (!state.hasPermissionToEdit){ return }`，權限來源是 `store.state.userData?.permission?.edit_notification`。沒有 edit_notification 權限的人不能新增或移除（判定規則 4）。

## 3. `jgb/I/pricing-plan-tiers-overview` 第 1 句

- 粗目：方案、價格與免費試用
- 細目標題：JGB 有哪些方案？（免費試用、體驗方案、入門／熱門／專業四級距、企業方案）
- target_user：property_manager, prospect
- **抽查句**：方案頁把付費方案分成「體驗方案」「入門方案」「熱門方案」「專業方案」四個級距，其中入門方案涵蓋 50、100、150 個物件，熱門方案涵蓋 200 到 450 個物件並標示為最熱門，專業方案為 500 個物件。
- sources：`code:src/pages/listings/pricing/Home.vue`；`code:src/pages/listings/pricing/parts/PlanForm.vue`；`code:app/Http/Controllers/ApiController.php`；`code:src/pages/listings/pricing/parts/PlanAndDevice.vue`
- 引文（該細目全部 4 筆）：
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:app/Http/Controllers/ApiController.php`：`'title' => '入門方案',`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/listings/pricing/parts/PlanAndDevice.vue`：`不綁信用卡的[s1]天的試用方案，歡迎體驗！`
  - [同細目其他句的引文｜drafts 句序 2] `code:src/pages/listings/pricing/parts/PlanForm.vue`：`{ label: t('月費'), value: 'monthly' },`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/listings/pricing/parts/PlanAndDevice.vue`：`{ t('深入了解企業方案', null, store.state.listingsI18n) }`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 4. `jgb/D/contract-create-entry` 第 4 句

- 粗目：合約列表與搜尋
- 細目標題：怎麼建立一份新合約？（合約總表右上角「建立合約」，或物件總表小齒輪選建立合約）
- target_user：property_manager
- **抽查句**：一個物件使用中（未刪除、未轉為歷史合約）的合約最多可以有 10 份，例如同一物件的舊租約仍在執行中，也可以先跟新租客預先簽下一份合約，等舊約到期銜接。
- sources：`help:landlordonboarding04lease_zh-Hant.html`；`docs:knowledge/jgb-product-facts.md#p914-contract-new-vs-old`；`docs:.kiro/specs/knowledge-outline-and-intent-architecture/inputs/review-sheet-9.15-S2-DE-20260927.md#109`；`code:src/components/Lightbox/SelectContractMethod.jsx`；`code:src/pages/contracts/list/_parts/PageTop.vue`；`code:config/role.php`
- 引文（該細目全部 11 筆）：
  - [同細目其他句的引文｜drafts 句序 0] `help:landlordonboarding04lease_zh-Hant.html`：`1-1.於【合約管理】中的【合約總表】點按右上角的【建立合約】`
  - [同細目其他句的引文｜drafts 句序 1] `help:landlordonboarding04lease_zh-Hant.html`：`2-1.於【物件管理】中的【物件總表】，對你想創建合約的物件，點按小齒輪，選擇【建立合約】。`
  - [同細目其他句的引文｜drafts 句序 2] `help:landlordonboarding04lease_zh-Hant.html`：`選擇建立電子合約（公版）/電子合約（客製化契約書）/紙本簽約`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 3] `help:landlordonboarding04lease_zh-Hant.html`：`一個物件可以綁定至多十個合約。`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 3] `code:app/Http/Controllers/ContractController.php`：`const MAX_ACTIVE_CONTRACTS_COUNT = 10;`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 3] `code:app/Http/Controllers/ContractController.php`：`if ($estate->contracts()->actualContracts()->activeContracts()->count() >= self::MAX_ACTIVE_CONTRACTS_COUNT) {`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 3] `code:app/Contract.php`：`return $query->where('is_history', 0)->where('active', 1);`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 3] `help:landlordonboarding04lease_zh-Hant.html`：`該物件 A租約即將到期，可以預先將物件刊登廣告、開放招租，若有 B租客有意願要承租，亦可以先進行簽約動作。`
  - [同細目其他句的引文｜drafts 句序 4] `docs:knowledge/jgb-product-facts.md#p914-contract-new-vs-old`：`建立新合約不會自動作廢或改動既有合約。同一物件「使用中」（未刪除、未轉歷史：`is_history = 0` 且 `active = 1`）`
  - [同細目其他句的引文｜drafts 句序 5] `docs:.kiro/specs/knowledge-outline-and-intent-architecture/inputs/review-sheet-9.15-S2-DE-20260927.md#109`：`採用：只寫程式證實的系統行為，其餘走個案客服`
  - [同細目其他句的引文｜drafts 句序 5] `docs:knowledge/jgb-product-facts.md#p914-contract-new-vs-old`：`不檢查新舊租期是否重疊`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 5. `jgb/D/contract-list-row-gear-actions` 第 1 句

- 粗目：合約列表與搜尋
- 細目標題：合約總表列的小齒輪可以做什麼操作？（不論狀態都有「查看帳單」；其餘依合約狀態、身分與權限增減）
- target_user：property_manager
- **抽查句**：合約總表每一列的小齒輪內容，是依這份合約目前的狀態、登入身分與權限來決定的。
- sources：`code:app/Http/Controllers/ContractController.php`；`code:routes/web.php`；`code:src/pages/contracts/list/Index.vue`；`code:app/Contract.php`；`code:src/components/SurelyVue/Contract/ActionCell.jsx`
- 引文（該細目全部 9 筆）：
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:routes/web.php`：`Route::match(['get', 'post'], '/api2/contract/list/{action?}/{status?}', 'ContractController@webList')`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:src/pages/contracts/list/Index.vue`：`api2/contract/list/getList`
  - [同細目其他句的引文｜drafts 句序 1] `code:app/Http/Controllers/ContractController.php`：`'text' => ___('查看物件'),`
  - [同細目其他句的引文｜drafts 句序 2] `code:app/Http/Controllers/ContractController.php`：`'text' => ___('查看帳單'),`
  - [同細目其他句的引文｜drafts 句序 3] `code:app/Http/Controllers/ContractController.php`：`'text' => ___('更換綁定信用卡'),`
  - [同細目其他句的引文｜drafts 句序 4] `code:app/Http/Controllers/ContractController.php`：`'text' => ___('取消邀請'),`
  - [同細目其他句的引文｜drafts 句序 5] `code:app/Http/Controllers/ContractController.php`：`'text' => ___('取消點交邀請'),`
  - [同細目其他句的引文｜drafts 句序 5] `code:app/Http/Controllers/ContractController.php`：`'text' => ___('取消點退邀請'),`
  - [同細目其他句的引文｜drafts 句序 7] `code:app/Http/Controllers/ContractController.php`：`續約例外名單：租期已過而被歸為歷史合約，原本齒輪選單不會出現「續約」`
- **判定**：**不成立**（獨立代理判不成立，業主 2026-10-06 裁定：「不成立 (Recommended)」）。代理理由：app/Http/Controllers/ContractController.php `webList`（action getList）裡組 `$LVreturn['actions']` 的條件確實包含狀態、`$this->roleType === 'tenant'`、`$LVtoThis_userPermission[...]`。但句子把決定因素列成只有「狀態、身分、權限」三項，屬排他列舉；程式還依其他條件增減或停用選項：合約業態 `property_purpose_key == Contract::SOCIAL_HOUSING`（社會住宅合約另走一套）、`is_tenant_registered == 1`、`isRenewExpiredAllowed()`、續約鏈帳單數決定「查看帳單」是否 `'disabled'`，以及特定合作團隊的簽核狀態（`Role::hasToneSangPermission` 區塊會把「提前終止合約」改成 disabled）。違反判定規則 6，也漏了規則 4 列的社會住宅與特定合作團隊例外。

## 6. `jgb/E/bill-monthly-report-upload` 第 2 句

- 粗目：帳單統計與報表
- 細目標題：「每月報表」跟「每月對帳單」分頁在做什麼？（依社區/物件上傳與下載每月的物件報表、對帳單檔案）
- target_user：property_manager
- **抽查句**：「每月對帳單」分頁底下是「物件對帳單」，一樣可以篩選後按「新增對帳單」上傳。
- sources：`code:src/pages/bills/stat/_parts/MonthlyReport.vue`
- 引文（該細目全部 5 筆）：
  - [同細目其他句的引文｜drafts 句序 0] `code:src/pages/bills/stat/_parts/MonthlyReport.vue`：`<div class="pb-4 text-[24px]">{ t('物件報表')}</div>`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 1] `code:src/pages/bills/stat/_parts/MonthlyReport.vue`：`<div class="pb-4 text-[24px]">{ t('物件對帳單')}</div>`
  - [同細目其他句的引文｜drafts 句序 2] `code:src/pages/bills/stat/_parts/MonthlyReport.vue`：`<div className="mb-2 text-center">{t('尚未上傳任何報表')}</div>`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/bills/stat/_parts/MonthlyReport.vue`：`}}>{t('社區')}</div>`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/bills/stat/_parts/MonthlyReport.vue`：`<ErrorsTip status="normal" errors={[t('請選擇物件。')]} />`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 7. `jgb/C/community-estates-add-batch-copy` 第 1 句

- 粗目：社區底下的物件（管理端清單：總覽／招租／買賣切換、編輯社區、預覽廣告頁）
- 細目標題：怎麼在社區底下新增物件？（新增／批次新增／複製現有物件，受物件數量上限限制）
- target_user：property_manager
- **抽查句**：有新增物件權限的使用者，在社區物件清單「所有物件」分類下可以點「新增物件」直接建立、選「批次新增」上傳表格，或選「複製現有物件」以既有物件為範本。
- sources：`code:src/pages/communities/estates/Index.vue`
- 引文（該細目全部 3 筆）：
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:src/pages/communities/estates/Index.vue`：`onClick={handleBatchAddEstate}>{ t('批次新增') }</a>`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/communities/estates/Index.vue`：`store.commit('lightbox', 'subscribedPlanIsFull')`
  - [同細目其他句的引文｜drafts 句序 2] `code:src/pages/communities/estates/Index.vue`：`return searchState.data?.list?.length === 1 && searchState.data?.list[0].property_purpose_key === 3`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 8. `jgb/E/recharge-account-mismatch-and-duplicate` 第 1 句

- 粗目：固定虛擬帳號管理（租客虛擬帳號、餘額、歷程）
- 細目標題：租客重複匯款時系統怎麼處理？（國泰世華單筆帳單 ATM 帳號已付款後重複匯入會略過；固定虛擬帳號多匯的部分留在儲值餘額）
- target_user：property_manager
- **抽查句**：如果匯到國泰世華單筆帳單 ATM 帳號的這筆帳單已經付款完成，租客又重複匯款進來，系統只會在內部記錄這筆訂單已被處理並略過，不會再沖到任何帳單。
- sources：`docs:knowledge/jgb-product-facts.md#p914-duplicate-remittance`；`code:app/Payment.php`；`code:app/RechargeAccount.php`；`code:app/Services/Payment/SinopacVaNotifyService.php`
- 引文（該細目全部 9 筆）：
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `docs:knowledge/jgb-product-facts.md#p914-duplicate-remittance`：`再入金只記錄「該訂單已被處理」並略過，不會沖到任何帳單`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:app/Payment.php`：`$errors[] = '該訂單已被處理 payment_id:' . $payment->id . ' account:' . $account;`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:app/Payment.php`：`if (!empty($payment->payment_completed_at)) {`
  - [同細目其他句的引文｜drafts 句序 1] `docs:knowledge/jgb-product-facts.md#p914-duplicate-remittance`：`多匯的部分留作餘額抵扣後續帳單；同一筆銀行入帳通知重送時以指紋去重，不會重複儲值`
  - [同細目其他句的引文｜drafts 句序 1] `code:app/RechargeAccount.php`：`public function settleReadyBills(array $allowlists)`
  - [同細目其他句的引文｜drafts 句序 1] `code:app/RechargeAccount.php`：`->whereIn("bills.owner_role_id", $allowlists);`
  - [同細目其他句的引文｜drafts 句序 1] `code:app/RechargeAccount.php`：`$result = self::_addLog($rechargeAccount, $value, $param);`
  - [同細目其他句的引文｜drafts 句序 1] `code:app/RechargeAccount.php`：`$allowlists = app(\App\Services\Features\FeaturePermissionService::class)->autoReconcileRechargeAccountRoleIds();`
  - [同細目其他句的引文｜drafts 句序 1] `code:app/Services/Payment/SinopacVaNotifyService.php`：`// 重送情境：前次可能已經把錢加進去但沒來得及標記完成，先看儲值歷程有沒有這筆通知的指紋。`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 9. `jgb/C/estate-edit-vr-720` 第 1 句

- 粗目：物件資料編輯（基本資料、建物謄本、附設傢俱、標題與照片、物件介紹、720 VR）
- 細目標題：物件的720 VR全景照怎麼拍？（需先安裝 VR Maker App 掃 QR Code 拍攝，可設定是否用於廣告）
- target_user：property_manager
- **抽查句**：拍攝720 VR全景照之前，需要先在手機安裝「VR Maker」App，接著在物件的720 VR分頁掃描 QR Code 進行拍攝。
- sources：`code:src/pages/estates/edit/vr/Index.vue`
- 引文（該細目全部 3 筆）：
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:src/pages/estates/edit/vr/Index.vue`：`<div class="mb-5">{{ t('拍攝 720 VR 全景照之前，請先確認已安裝「VR Maker」。') }}</div>`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/estates/edit/vr/Index.vue`：`<div class="text-grey-600">{{ t('目前不支援以手機編輯 VR 全景照，請使用 PC 開啟') }}</div>`
  - [同細目其他句的引文｜drafts 句序 2] `code:src/pages/estates/edit/vr/Index.vue`：`{{ t('於招租廣告、買賣廣告中使用 720 VR 全景照。') }}`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 10. `jgb/E/balance-invoice-list-columns` 第 2 句

- 粗目：差額發票（群組、底租、社區層開關）
- 細目標題：差額發票群組總表列表裡看得到哪些欄位？（ID／出租物件數／本月發票狀態／累積成本／累積收入／累積發票金額）
- target_user：property_manager
- **抽查句**：「群組」欄位顯示的是差額發票群組的名稱。
- sources：`code:src/pages/balanceInvoices/list/_parts/ListTable.vue`
- 引文（該細目全部 4 筆）：
  - [同細目其他句的引文｜drafts 句序 0] `code:src/pages/balanceInvoices/list/_parts/ListTable.vue`：`title: t('累積發票金額'),`
  - [同細目其他句的引文｜drafts 句序 0] `code:src/pages/balanceInvoices/list/_parts/ListTable.vue`：`title: 'ID',`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 1] `code:src/pages/balanceInvoices/list/_parts/ListTable.vue`：`title: t('群組'),`
  - [同細目其他句的引文｜drafts 句序 2] `code:src/pages/balanceInvoices/list/_parts/ListTable.vue`：`title: t('出租物件數'),`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 11. `jgb/F/repair-share-content` 第 2 句

- 粗目：修繕單分享頁
- 細目標題：修繕單分享頁看得到什麼？（修繕申請單標題與是否緊急、照片、報修細節、安排的廠商資訊、房東備註與房客備註，全部都是唯讀；不會顯示物件廣告連結、縮圖，也沒有房東／承租方資訊側欄）
- target_user：property_manager
- **抽查句**：接下來會顯示報修時的照片、聯絡電話或Email、物件區域與時區、分類、問題、備註、預約時段等報修細節。
- sources：`code:src/pages/repair/share/Index.vue`；`code:app/Http/Controllers/RepairController.php`
- 引文（該細目全部 5 筆）：
  - [同細目其他句的引文｜drafts 句序 0] `code:src/pages/repair/share/Index.vue`：`{{ t('修繕申請單') }}`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 1] `code:src/pages/repair/share/Index.vue`：`labelKey: '物件區域',`
  - [同細目其他句的引文｜drafts 句序 2] `code:src/pages/repair/share/Index.vue`：`:canEditRepair="false" />`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/repair/share/Index.vue`：`:isAllowedEdit="false"`
  - [同細目其他句的引文｜drafts 句序 4] `code:app/Http/Controllers/RepairController.php`：`unset($data['data']['aside_panel']);`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 12. `jgb/E/balance-invoice-group-basic-info` 第 1 句

- 粗目：差額發票（群組、底租、社區層開關）
- 細目標題：建立差額發票群組要填哪些基本資料？（群組名稱／底租／租期／前期餘額／房屋座落地址／房屋稅籍編號）
- target_user：property_manager
- **抽查句**：建立差額發票群組要填「群組名稱」，這是必填欄位。
- sources：`code:src/pages/balanceInvoices/edit/basicInfo/Index.vue`
- 引文（該細目全部 5 筆）：
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:src/pages/balanceInvoices/edit/basicInfo/Index.vue`：`<div class="after-required mb-2 font-500">{{ t('群組名稱') }}</div>`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/balanceInvoices/edit/basicInfo/Index.vue`：`<div class="mb-2 font-500">{{ t('底租') }}</div>`
  - [同細目其他句的引文｜drafts 句序 2] `code:src/pages/balanceInvoices/edit/basicInfo/Index.vue`：`<div class="mb-2 font-500">{{ t('租期') }}</div>`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/balanceInvoices/edit/basicInfo/Index.vue`：`<div class="mb-2 font-500">{{ t('前期餘額') }}</div>`
  - [同細目其他句的引文｜drafts 句序 4] `code:src/pages/balanceInvoices/edit/basicInfo/Index.vue`：`<div class="mb-2 font-500">{{ t('房屋稅籍編號') }}</div>`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 13. `jgb/I/subscription-renewal-charge-failure` 第 3 句

- 粗目：訂閱、付款與訂單
- 細目標題：自動續訂扣款失敗會怎樣？（方案資料整個清空、限額歸零、所有物件立即下架，沒有寬限期）
- target_user：property_manager
- **抽查句**：物件下架的範圍是目前所有「刊登中」或「買賣廣告」的物件，會被直接改成非刊登、非上架狀態。
- sources：`code:app/Console/Commands/AutoRenewSubscription.php`；`code:app/Role.php`
- 引文（該細目全部 5 筆）：
  - [同細目其他句的引文｜drafts 句序 0] `code:app/Console/Commands/AutoRenewSubscription.php`：`if (!$role->checkCreditAgreed() || !$role->isSubscriptionRenewable()) {`
  - [同細目其他句的引文｜drafts 句序 0] `code:app/Console/Commands/AutoRenewSubscription.php`：`// 如果扣款失敗 則清空訂閱方案資料與下架物件`
  - [同細目其他句的引文｜drafts 句序 1] `code:app/Role.php`：`$this->plan_estate_limit = 0; // 方案物件數量`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 2] `code:app/Role.php`：`$estates = $this->estates()->whereRaw('(is_open != 0 or sell_is_open != 0)')->get();`
  - [同細目其他句的引文｜drafts 句序 3] `code:app/Console/Commands/AutoRenewSubscription.php`：`$role->clearSubscription();`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 14. `jgb/E/recharge-account-history-content` 第 1 句

- 粗目：固定虛擬帳號管理（租客虛擬帳號、餘額、歷程）
- 細目標題：點開「歷程」看得到哪些內容？（每筆金額變動的時間／類型／金額／前後餘額／操作人員，有連結帳單可以點開查看）
- target_user：property_manager
- **抽查句**：點開「歷程」會列出這組虛擬帳號每一筆金額變動紀錄，包含時間、類型、變動金額、變動前餘額、變動後餘額、操作人員。
- sources：`code:src/pages/users/rechargeAccountList/Index.vue`
- 引文（該細目全部 5 筆）：
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:src/pages/users/rechargeAccountList/Index.vue`：`<th class="py-2 px-2">{t('類型')}</th>`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:src/pages/users/rechargeAccountList/Index.vue`：`<th class="py-2 px-2 text-right">{t('變動金額')}</th>`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/users/rechargeAccountList/Index.vue`：`{log.bill_id ? (`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/users/rechargeAccountList/Index.vue`：`onClick={() => openBillDetail(log.bill_id)}></i>`
  - [同細目其他句的引文｜drafts 句序 2] `code:src/pages/users/rechargeAccountList/Index.vue`：`<div class="py-8 text-center text-grey-500">{t('目前尚無歷程記錄')}</div>`
- **判定**：**不成立**（獨立代理判不成立，業主 2026-10-06 裁定：「不成立 (Recommended)」）。代理理由：欄位成立：src/pages/users/rechargeAccountList/Index.vue `金額變動歷程` lightbox 有 `t('時間')` `t('類型')` `t('變動金額')` `t('變動前餘額')` `t('變動後餘額')` `t('操作人員')`。但「列出…每一筆金額變動紀錄」不成立：前端 `openHistoryLightbox` 呼叫 `/api/recharge-accounts/${record.id}/history` 時沒帶參數，也沒有分頁或載入更多；後端 app/Http/Controllers/RechargeAccountListController `history()` 是 `$perPage = min(100, max(1, (int) $request->input('per_page', 50)))` 搭配 `->paginate(...)`、`orderBy('id', 'desc')`。所以畫面只會出現最近 50 筆。

## 15. `jgb/A/forget-account-flow` 第 5 句

- 粗目：忘記帳號、忘記密碼
- 細目標題：忘記帳號怎麼辦？（用已綁定的手機號碼簡訊驗證找回 Email 提示）
- target_user：property_manager
- **抽查句**：驗證成功畫面的最下方寫著「如有其他問題，請聯繫 JGB 客服」
- sources：`code:src/pages/users/auth/parts/forget/Account.vue`；`code:app/Http/Controllers/AuthController.php`；`code:app/User.php`
- 引文（該細目全部 10 筆）：
  - [同細目其他句的引文｜drafts 句序 0] `code:src/pages/users/auth/parts/forget/Account.vue`：`t('請輸入當初綁定在帳號上的手機號碼，完成驗證後，JGB 將寄送帳號相關細節給您；如果未綁定手機號碼，請聯繫 JGB 客服。')`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/users/auth/parts/forget/Account.vue`：`如果未綁定手機號碼，請聯繫 JGB 客服`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/users/auth/parts/forget/Account.vue`：`如果未綁定手機號碼，請聯繫 JGB 客服`
  - [同細目其他句的引文｜drafts 句序 2] `code:app/Http/Controllers/AuthController.php`：`$result['data']['field_errors']['phone'] = ___('手機號碼格式錯誤或無此號碼對應的帳號。');`
  - [同細目其他句的引文｜drafts 句序 2] `code:app/User.php`：`->whereNotNull('phone_verified_at')`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/users/auth/parts/forget/Account.vue`：`t('身份驗證成功！以下為您的帳號提示：')`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/users/auth/parts/forget/Account.vue`：`state.response.showEmailHint?.data?.email_hint`
  - [同細目其他句的引文｜drafts 句序 3] `code:app/Http/Controllers/AuthController.php`：`$account = asterisks($account, $showCount);`
  - [同細目其他句的引文｜drafts 句序 3] `code:app/Http/Controllers/AuthController.php`：`$result['data']['email_hint'] = $account . '@' . $platform;`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 4] `code:src/pages/users/auth/parts/forget/Account.vue`：`t('如有其他問題，請聯繫 JGB 客服。')`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 16. `jgb/B/member-invite` 第 1 句

- 粗目：成員列表（邀請、角色、成員名下資料）
- 細目標題：怎麼邀請新成員加入團隊？（用 Email 或手機號碼搜尋，對方要先是 JGB 會員）
- target_user：property_manager
- **抽查句**：點擊成員列表的「邀請」按鈕會開啟「新增成員」視窗，可以選擇用 Email 或手機號碼搜尋要邀請的對象。
- sources：`code:resources/views/users/team/index.blade.php`
- 引文（該細目全部 8 筆）：
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:resources/views/users/team/index.blade.php`：`{{___('新增成員')}}`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:resources/views/users/team/index.blade.php`：`<span class="col">{{___('手機號碼')}}</span>`
  - [同細目其他句的引文｜drafts 句序 1] `code:resources/views/users/team/index.blade.php`：`受邀請的對象如果不是 JGB 會員，將無法新增為團隊成員。`
  - [同細目其他句的引文｜drafts 句序 1] `code:resources/views/users/team/index.blade.php`：`受邀請的對象如果不是 JGB 會員，將無法新增為團隊成員。`
  - [同細目其他句的引文｜drafts 句序 1] `code:app/Http/Controllers/UserController.php`：`'message'=> ___('您輸入的帳號不存在'),`
  - [同細目其他句的引文｜drafts 句序 1] `code:resources/views/users/team/index.blade.php`：`<errors-tip class="mt-2" :errors="$store.state.team.invite.accountValidationFailedMsg">`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/store/modules/team/invite.js`：`context.dispatch('update', {'team.invite.accountValidationFailedMsg': result.data.message}, {root: true});`
  - [同細目其他句的引文｜drafts 句序 2] `code:resources/views/users/team/index.blade.php`：`{{___('即將新增成員')}}`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 17. `jgb/A/register-password-rule` 第 1 句

- 粗目：註冊帳號（Email／SSO、驗證碼、手機綁定）
- 細目標題：註冊密碼格式要求是什麼？（至少 6 碼、須同時包含英文與數字）
- target_user：property_manager, prospect
- **抽查句**：密碼長度至少需 6 個字元（含）以上。
- sources：`code:src/pages/users/auth/parts/AccountSetting.vue`
- 引文（該細目全部 3 筆）：
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:src/pages/users/auth/parts/AccountSetting.vue`：`length: state.password.length >= 6`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/users/auth/parts/AccountSetting.vue`：`format: /[0-9]/.test(state.password) && /[a-zA-Z]/.test(state.password)`
  - [同細目其他句的引文｜drafts 句序 2] `code:src/pages/users/auth/parts/AccountSetting.vue`：`same: state.password && state.password === state.password_confirmation`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 18. `jgb/C/estate-edit-basic-orientation` 第 1 句

- 粗目：物件資料編輯（基本資料、建物謄本、附設傢俱、標題與照片、物件介紹、720 VR）
- 細目標題：物件基本資料可以填朝向嗎？
- target_user：property_manager
- **抽查句**：物件基本資料分頁有「朝向」欄位可以填寫。
- sources：`code:src/pages/estates/edit/basic/Index.vue`
- 引文（該細目全部 1 筆）：
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:src/pages/estates/edit/basic/Index.vue`：`<h4 class="mb-2">{{ t('朝向') }}</h4>`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 19. `jgb/B/member-role-permission-list` 第 2 句

- 粗目：成員列表（邀請、角色、成員名下資料）
- 細目標題：怎麼查看每個角色能做什麼？（點「角色權限說明」的「這裡」開啟角色權限列表，每一列是一項權限、每一欄是一個角色，用勾號／叉號表示有沒有這項權限）
- target_user：property_manager
- **抽查句**：如果團隊目前還沒有建立任何角色，角色權限列表會顯示「目前團隊還沒有任何角色，您可以選擇：」，並提供「新增角色」的按鈕。
- sources：`code:resources/views/users/team/index.blade.php`；`code:resources/views/layouts/lightbox/character-capability-edit.blade.php`
- 引文（該細目全部 5 筆）：
  - [同細目其他句的引文｜drafts 句序 0] `code:resources/views/users/team/index.blade.php`：`<div class="lg:mt-4 mt-2">{!!___('角色權限說明請點擊 [s1]。', ['<span class="btn btn-text" @click="lightboxOpen(\'character--Table\')">' . ___('這裡') . '</span>'])!!}</div>`
  - [同細目其他句的引文｜drafts 句序 0] `code:resources/views/layouts/lightbox/character-capability-edit.blade.php`：`<span class="lg:text-[28px] text-[22px]">{{___('角色權限列表')}}</span>`
  - [同細目其他句的引文｜drafts 句序 0] `code:src/store/modules/team/capabilityEdit.js`：`headerName: t('權限列表'),`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 1] `code:resources/views/layouts/lightbox/character-capability-edit.blade.php`：`<div class="mb-6">{{___('目前團隊還沒有任何角色，您可以選擇：')}}</div>`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 1] `code:resources/views/layouts/lightbox/character-capability-edit.blade.php`：`}">{{___('新增角色')}}</div>`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 20. `jgb/A/notification-settings-extra-emails` 第 1 句

- 粗目：通知收件設定與發送報表（通知收件信箱最多再加 3 組）
- 細目標題：通知收件信箱最多能加幾組？（每個通知分類最多再加 3 組電子信箱）
- target_user：property_manager
- **抽查句**：「通知收件設定」頁面說明每個通知信分類最多可再新增 3 組電子信箱收取通知信件。
- sources：`code:src/pages/users/notification/Index.vue`
- 引文（該細目全部 9 筆）：
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:src/pages/users/notification/Index.vue`：`t('每個通知信最多可再新增 3 組電子信箱收取通知信件。')`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/users/notification/Index.vue`：`v-model="formData.defaultEmail"`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/users/notification/Index.vue`：`disabled`
  - [同細目其他句的引文｜drafts 句序 2] `code:src/pages/users/notification/Index.vue`：`mailAmountLimit: 3,`
  - [同細目其他句的引文｜drafts 句序 2] `code:src/pages/users/notification/Index.vue`：`type="email"`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/users/notification/Index.vue`：`hasPermissionToEdit: computed(()=>store.state.userData?.permission?.edit_notification || false),`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/users/notification/Index.vue`：`<template v-if="state.hasPermissionToEdit">`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/users/notification/Index.vue`：`:class="['relative', `${ state.hasPermissionToEdit ? '' : 'disabled' }`]">`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/users/notification/Index.vue`：`if (!state.hasPermissionToEdit){`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 21. `jgb/I/control-panel-access-restriction` 第 3 句

- 粗目：控制台（設定、通知信範本、自動化任務）
- 細目標題：誰能用控制台的任務管理與通知信設定？（僅限特定合作團隊角色；控制台首頁本身沒有這層檢查，只有進到「設定」子路徑才會擋）
- target_user：property_manager
- **抽查句**：新增任務、編輯任務與通知信設定這三個頁面都額外標記租客角色不允許使用。
- sources：`code:src/routes/controlPanel.js`
- 引文（該細目全部 4 筆）：
  - [同細目其他句的引文｜drafts 句序 0] `code:src/routes/controlPanel.js`：`if (!['controlPanel', 'tongSang'].includes(specialRoleGroup.key)){`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/routes/controlPanel.js`：`name: 'controlPanel.index',`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/routes/controlPanel.js`：`name: 'controlPanel.setting',`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 2] `code:src/routes/controlPanel.js`：`notAllowedRoles: ['tenant']`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 22. `jgb/C/estate-dashboard-runnings-vs-memos` 第 1 句

- 粗目：物件儀表板（招租表現、合約歷程、帳務收支、修繕紀錄、附件清單、房東流水帳、合約附件、物件記事本、每月報表、每月對帳單；入口直接轉到招租表現）
- 細目標題：「房東流水帳」跟「物件記事本」差在哪？（流水帳要記收入或支出與金額，記事本沒有金額欄位；兩者都能附檔）
- target_user：property_manager
- **抽查句**：「房東流水帳」新增一筆時，要填時間、費用類別（收入或支出）、幣別與金額；說明與對象可以留空。
- sources：`code:src/pages/estates/dashboard/runnings/Index.vue`；`code:src/pages/estates/dashboard/memos/Index.vue`；`code:src/pages/estates/dashboard/runnings/_parts/LedgerContainer.vue`；`code:src/pages/estates/dashboard/memos/_parts/MemoContainer.vue`；`code:app/Http/Controllers/EstateController.php`
- 引文（該細目全部 18 筆）：
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:app/Http/Controllers/EstateController.php`：`'date' => 'required',`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:app/Http/Controllers/EstateController.php`：`'fee_type' => 'required',`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:app/Http/Controllers/EstateController.php`：`'currencySelected' => 'required',`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:app/Http/Controllers/EstateController.php`：`'price' => 'required|gte:0'`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:src/pages/estates/dashboard/runnings/_parts/LedgerContainer.vue`：`{{ t('費用類別') }}`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:src/pages/estates/dashboard/runnings/_parts/LedgerContainer.vue`：`{{ t('費用') }}`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:src/pages/estates/dashboard/runnings/_parts/LedgerContainer.vue`：`labelKey: '說明',`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:app/Http/Controllers/EstateController.php`：`$note = !empty($requestData['note']) ? $requestData['note'] : null; // 說明，再做一次判斷`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/estates/dashboard/runnings/_parts/LedgerContainer.vue`：`maxNumberOfFiles: 3 - (props.form?.attachments?.length || 0),`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/estates/dashboard/runnings/_parts/LedgerContainer.vue`：`maxFileSize: 10 * 1024 * 1024,`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/estates/dashboard/runnings/_parts/LedgerContainer.vue`：`allowedFileTypes: ['image/*', '.pdf'],`
  - [同細目其他句的引文｜drafts 句序 2] `code:app/Http/Controllers/EstateController.php`：`if ($estate->hasPermission($this->user, 'edit_estate') || ($estate->agent_user_id == $this->user->id && $estate->hasPermission($this->user, 'add_estate'))) {`
  - [同細目其他句的引文｜drafts 句序 2] `code:app/Http/Controllers/EstateController.php`：`'message' => ___('權限不足！')`
  - [同細目其他句的引文｜drafts 句序 3] `code:app/Http/Controllers/EstateController.php`：`$targetName = !empty($requestData['target_name']) ? $requestData['target_name'] : null;`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/estates/dashboard/memos/_parts/MemoContainer.vue`：`labelKey: '時間',`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/estates/dashboard/memos/_parts/MemoContainer.vue`：`labelKey: '對象',`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/estates/dashboard/memos/_parts/MemoContainer.vue`：`maxNumberOfFiles: 3 - (props.form?.attachments?.length || 0),`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/estates/dashboard/memos/_parts/MemoContainer.vue`：`{{ t('新增記事') }}`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 23. `jgb/E/bill-actions-expense-unconfirmed` 第 1 句

- 粗目：帳單列表與帳單狀態
- 細目標題：「待對帳」狀態的支出帳單，房東跟租客各能做什麼？（房東：前往付款／通知已匯款／取消帳單；租客：沒有齒輪動作）
- target_user：property_manager
- **抽查句**：待對帳的支出帳單，房東端一樣有「前往付款」「通知已匯款」「取消帳單」；這個狀態租客端沒有齒輪動作。
- sources：`code:src/use/config/useBillTypes.js`
- 引文（該細目全部 1 筆）：
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:src/use/config/useBillTypes.js`：`case 'expense-unconfirmed':`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 24. `jgb/F/repair-status-tabs` 第 3 句

- 粗目：修繕單列表與狀態（申請修繕、安排修繕、完成修繕、結單、封存）
- 細目標題：修繕單總表有哪些狀態分頁？（申請修繕、安排修繕、完成修繕、結單、封存）
- target_user：property_manager, prospect
- **抽查句**：進入畫面後不需要自己選分頁，系統會直接停在「申請修繕」這個分頁。
- sources：`code:src/routes/repairs.js`；`code:src/pages/repair/Index.vue`；`code:app/Repair.php`；`code:routes/web.php`；`help:repair_zh-Hant.html`
- 引文（該細目全部 4 筆）：
  - [同細目其他句的引文｜drafts 句序 0] `code:src/routes/repairs.js`：`labelKey: '安排修繕',`
  - [同細目其他句的引文｜drafts 句序 1] `help:repair_zh-Hant.html`：`<p>➡安排修繕</p>`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 2] `code:src/pages/repair/Index.vue`：`router.push({ name: 'repair.apply' })`
  - [同細目其他句的引文｜drafts 句序 3] `code:routes/web.php`：`->name('repairs.index')->middleware('need_login');`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 25. `jgb/D/general-contract-notary-tab` 第 8 句

- 粗目：租約公證（公證分頁與公證服務）
- 細目標題：一般合約的「公證」分頁怎麼設定？（是否辦理公證，同意時可複選三項應逕受強制執行事項；只有部分合約範本有此選項）
- target_user：property_manager
- **抽查句**：車位合約，以及部分特定合作團隊的專用範本，合約編輯畫面不會出現「公證」分頁；車位合約即使用的是有「辦理公證」選項的範本，也一樣沒有這個分頁。
- sources：`code:src/pages/contracts/edit/publicNotary/General.vue`；`code:src/use/config/useContractRequiredField.js`；`code:config/contract.php`；`code:src/pages/contracts/edit/Index.vue`
- 引文（該細目全部 44 筆）：
  - [同細目其他句的引文｜drafts 句序 0] `code:src/pages/contracts/edit/publicNotary/General.vue`：`t('本分租賃合約如同意辦理公證，請於下方設定相關細節。')`
  - [同細目其他句的引文｜drafts 句序 0] `code:src/pages/contracts/edit/publicNotary/General.vue`：`{{ t('辦理公證') }}`
  - [同細目其他句的引文｜drafts 句序 0] `code:src/pages/contracts/edit/publicNotary/General.vue`：`{{ t('同意辦理') }}`
  - [同細目其他句的引文｜drafts 句序 0] `code:src/pages/contracts/edit/publicNotary/General.vue`：`{{ t('不同意辦理') }}`
  - [同細目其他句的引文｜drafts 句序 0] `code:src/pages/contracts/edit/publicNotary/General.vue`：`<div v-if="contractHasPublicNotary">`
  - [同細目其他句的引文｜drafts 句序 1] `code:config/contract.php`：`'label' => '114年內政部住宅租賃契約(原房東)',`
  - [同細目其他句的引文｜drafts 句序 1] `code:config/contract.php`：`'label' => '113年內政部轉租契約(包租轉租)',`
  - [同細目其他句的引文｜drafts 句序 1] `code:config/contract.php`：`'label' => '代租代管契約(參考114年租賃契約)',`
  - [同細目其他句的引文｜drafts 句序 1] `code:config/contract.php`：`'label' => '公會中文版 租賃契約書 原房東',`
  - [同細目其他句的引文｜drafts 句序 1] `code:config/contract.php`：`'label' => '公會中文版 租賃契約書 包租業',`
  - [同細目其他句的引文｜drafts 句序 1] `code:config/contract.php`：`'label' => '公會中文版 租賃契約書 代租代管',`
  - [同細目其他句的引文｜drafts 句序 1] `code:config/contract.php`：`'label' => '內政部英文版 租賃契約書 包租業',`
  - [同細目其他句的引文｜drafts 句序 1] `code:config/contract.php`：`'label' => '英泰文版 租賃契約書 原房東',`
  - [同細目其他句的引文｜drafts 句序 1] `code:config/contract.php`：`'label' => '英泰文版 租賃契約書 代租代管',`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/use/config/useContractRequiredField.js`：`[ContractTemplate.en_us_corporation]: [`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/use/config/useContractRequiredField.js`：`[ContractTemplate.th_th_individual]: [`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/use/config/useContractRequiredField.js`：`[ContractTemplate.th_th_management]: [`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/use/config/useContractRequiredField.js`：`[ContractTemplate.tw_zh_corporation_union]: [`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/use/config/useContractRequiredField.js`：`FormField.hasPublicNotary,`
  - [同細目其他句的引文｜drafts 句序 2] `code:src/pages/contracts/edit/publicNotary/General.vue`：`{{ t('強制執行事項') }}`
  - [同細目其他句的引文｜drafts 句序 2] `code:src/pages/contracts/edit/publicNotary/General.vue`：`{{ t('辦理公證後，請選擇應逕受強制執行的項目(可複選)。') }}`
  - [同細目其他句的引文｜drafts 句序 2] `code:src/pages/contracts/edit/publicNotary/General.vue`：`{{ t('1：承租方如於租期屆滿後不返還租賃住宅。') }}`
  - [同細目其他句的引文｜drafts 句序 2] `code:src/pages/contracts/edit/publicNotary/General.vue`：`{{ t('2：承租方未依約給付之欠繳租金、費用及出租方或租賃住宅所有權人代繳之管理費，或違約時應支付之金額。') }}`
  - [同細目其他句的引文｜drafts 句序 2] `code:src/pages/contracts/edit/publicNotary/General.vue`：`{{ t('3：出租方如於租期屆滿或本契約終止時，應返還承租方之全部或一部分押金。') }}`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/pages/contracts/edit/publicNotary/General.vue`：`editStore.form.public_notary_content = ['1', '2', '3']`
  - [同細目其他句的引文｜drafts 句序 4] `code:src/pages/contracts/edit/publicNotary/General.vue`：`{{ t('公證書載明下列事項應逕受強制執行') }}`
  - [同細目其他句的引文｜drafts 句序 4] `code:src/pages/contracts/edit/publicNotary/General.vue`：`<div v-if="contractHasPublicNotaryDistraint">`
  - [同細目其他句的引文｜drafts 句序 4] `code:src/use/config/useContractRequiredField.js`：`FormField.hasPublicNotaryDistraint,`
  - [同細目其他句的引文｜drafts 句序 4] `code:src/use/config/useContractRequiredField.js`：`[ContractTemplate.tw_zh_management]: [`
  - [同細目其他句的引文｜drafts 句序 5] `code:src/pages/contracts/edit/publicNotary/General.vue`：`t('保證人效力')`
  - [同細目其他句的引文｜drafts 句序 5] `code:src/pages/contracts/edit/publicNotary/General.vue`：`<div v-html="t('公證書載明金錢債務逕受強制執行時，如有保證人者，前項後段第 [s1] 款之效力及於保證人。',[string])"></div>`
  - [同細目其他句的引文｜drafts 句序 5] `code:src/pages/contracts/edit/Index.vue`：`return editStore.form.public_notary_content.sort((a, b)=>Number(a) - Number(b))`
  - [同細目其他句的引文｜drafts 句序 6] `code:src/pages/contracts/edit/publicNotary/General.vue`：`{{ t('*目前英文與英越文版合約不支援此項目。') }}`
  - [同細目其他句的引文｜drafts 句序 6] `code:src/use/config/useContractRequiredField.js`：`[ContractTemplate.EN201608]: [FormField.hasCondoRegulations],`
  - [同細目其他句的引文｜drafts 句序 6] `code:src/use/config/useContractRequiredField.js`：`[ContractTemplate.VN202005]: [FormField.hasCondoRegulations],`
  - [同細目其他句的引文｜drafts 句序 6] `code:src/use/config/useContractRequiredField.js`：`} else if (!RequiredField[contractTemplate]){`
  - [同細目其他句的引文｜drafts 句序 6] `code:src/use/config/useContractRequiredField.js`：`// 紙本/DIY 合約無 contract_template_selected，但現況補充與建物謄本仍需顯示實價登錄相關欄位`
  - [同細目其他句的引文｜drafts 句序 6] `code:config/contract.php`：`'label' => '內政部英文版 租賃契約書 原房東',`
  - [同細目其他句的引文｜drafts 句序 6] `code:config/contract.php`：`'label' => '內政部英文版 租賃契約書 代租代管',`
  - [同細目其他句的引文｜drafts 句序 6] `code:config/contract.php`：`'label' => '英越文版 租賃契約書',`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 7] `code:src/use/useEditStore.js`：`if (editStore.form.premises_use_for === 'parking_space'){`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 7] `code:src/use/useEditStore.js`：`const basicRoutes = ['contracts.edit.tenantInfo', 'contracts.edit.billSetting', 'contracts.edit.dealerBasic', 'contracts.edit.rentBasic', 'contracts.edit.rent', 'contracts.edit.payment', 'contracts.edit.situation', 'contracts.edit.landlordAttachment', 'contracts.edit.additionalConvention']`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 7] `code:src/use/useEditStore.js`：`myRoutes = myRoutes.filter(node=>node.name !== 'contracts.edit.publicNotary')`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 7] `code:src/use/useEditStore.js`：`if (editStore.form.contract_template_selected === 'nthurc_social_housing'){`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 26. `jgb/D/contract-invite-and-review-period` 第 1 句

- 粗目：簽約與合約檢視
- 細目標題：合約邀請發出後租客有多久審閱期？（預設 3 天／72 小時，逾期連結失效，天數為團隊可調整設定）
- target_user：property_manager, prospect
- **抽查句**：房東送出合約邀請後，系統會給租客一段審閱期才能簽約；天數其實是讀團隊設定，沒有設定才用預設的 3 天（72 小時）。
- sources：`code:app/Http/Controllers/ContractController.php`；`code:app/Http/Controllers/Internal/ContractWriteController.php`；`help:landlordonboarding04lease_zh-Hant.html`；`docs:knowledge/jgb-product-facts.md#p914-contract-invite-account-match`；`docs:knowledge/jgb-product-facts.md#p914-email-encrypted-no-lowercase`；`docs:.kiro/specs/knowledge-outline-and-intent-architecture/inputs/review-sheet-9.15-S2-DE-20260927.md#113`
- 引文（該細目全部 10 筆）：
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:app/Http/Controllers/ContractController.php`：`->getSettings('contract_review_renew_period', (int) optional($this->role)->id)['review_days'] ?? 3);`
  - [同細目其他句的引文｜drafts 句序 1] `code:app/Http/Controllers/ContractController.php`：`$contract->contract_inviting_expire_at = date('Y-m-d H:i:s', strtotime("+{$reviewDays} days"));`
  - [同細目其他句的引文｜drafts 句序 2] `help:landlordonboarding04lease_zh-Hant.html`：`從您發送邀請時開始計算，租客需要在72小時內進行簽約，否則該連結就會失效。`
  - [同細目其他句的引文｜drafts 句序 3] `docs:knowledge/jgb-product-facts.md#p914-contract-invite-account-match`：`送出邀請時，以合約填的租客 Email 比對已註冊會員（比對到才代入該會員資料，並把合約上的租客 Email 改成會員的註冊 Email）；`
  - [同細目其他句的引文｜drafts 句序 3] `code:app/Http/Controllers/ContractController.php`：`$userQ = User::where('phone_country_id', $contract->to_user_phone_country_id)->where('phone', xxtea_base64_encrypt($contract->to_user_phone))->whereNotNull('phone_verified_at');`
  - [同細目其他句的引文｜drafts 句序 3] `code:app/Http/Controllers/ContractController.php`：`$userQ = User::where('phone_country_id', $targetCountryId)->where('phone', xxtea_base64_encrypt($targetPhone));`
  - [同細目其他句的引文｜drafts 句序 3] `code:app/Http/Controllers/ContractController.php`：`if ($contract->property_purpose_key == Contract::SOCIAL_HOUSING) {`
  - [同細目其他句的引文｜drafts 句序 3] `code:app/Http/Controllers/ContractController.php`：`if ($contract->property_purpose_key == Contract::GENERAL_HOUSING){`
  - [同細目其他句的引文｜drafts 句序 4] `docs:knowledge/jgb-product-facts.md#p914-email-encrypted-no-lowercase`：``User::setEmailAttribute` 以 XXTEA 加密後存入 `email`；比對會員時以加密後字串做相等查詢（`wher`
  - [同細目其他句的引文｜drafts 句序 5] `docs:.kiro/specs/knowledge-outline-and-intent-architecture/inputs/review-sheet-9.15-S2-DE-20260927.md#113`：`採用：只寫程式證實的系統行為，其餘走個案客服`
- **判定**：**不成立**（獨立代理判不成立，業主 2026-10-06 裁定：「不成立 (Recommended)」）。代理理由：後半句成立：app/Http/Controllers/ContractController.php `getSettings('contract_review_renew_period', (int) optional($this->role)->id)['review_days'] ?? 3)` → `contract_inviting_expire_at = date(... strtotime("+{$reviewDays} days"))`。但前半句「系統會給租客一段審閱期才能簽約」把這段期間寫成簽約前必須等待的期間。程式裡它是簽約邀請的失效期限（`contract_inviting_expire_at`、app/Contract.php `getInviteRemainAttribute` 算剩餘時間），租客可以在期限內隨時簽。help landlordonboarding04lease_zh-Hant.html 也寫「租客需要在72小時內進行簽約，否則該連結就會失效」。程式裡找不到「等滿才能簽」的閘門，與審核單 #113「只寫程式證實的系統行為」不一致。

## 27. `jgb/C/estate-list-filters-space-type-and-others` 第 1 句

- 粗目：物件列表與篩選
- 細目標題：物件總表篩選還有哪些條件？（空間類型多選、「更多」：VR、有電梯、可開伙、可養寵物）
- target_user：property_manager
- **抽查句**：進階搜尋提供「空間類型」多選篩選（例如整戶、套房、雅房等）。
- sources：`code:src/pages/estates/list/_parts/EstatesAdvanceSearchBlock.jsx`；`code:src/components/AdvGroupSelect.jsx`；`code:src/components/AdvGroupSelectMobile.jsx`
- 引文（該細目全部 3 筆）：
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:src/pages/estates/list/_parts/EstatesAdvanceSearchBlock.jsx`：`keyName={EstateSearchKey.space_type}`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/estates/list/_parts/EstatesAdvanceSearchBlock.jsx`：`is_show_vr: 'VR',`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/components/AdvGroupSelect.jsx`：`{ t('更多') }`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 28. `jgb/A/register-tenant-contract-invitation` 第 7 句

- 粗目：註冊帳號（Email／SSO、驗證碼、手機綁定）
- 細目標題：租客從電子合約邀請怎麼註冊？（房東建約發邀請，租客點「查看合約」再點「立即註冊」接續完成）
- target_user：property_manager, prospect
- **抽查句**：房東建立合約時若選「租客免註冊」，租客不需要註冊 JGB 會員，改由房東／管理者協助填寫租客資訊。
- sources：`help:onboarding1_zh-Hant.html`；`code:app/Http/Controllers/AuthController.php`；`code:src/pages/contracts/edit/tenantInfo/Index.jsx`；`code:app/Notification.php`；`code:resources/views/emails/zh-TW/contracts/invite.blade.php`；`code:resources/views/estate/show.blade.php`；`code:src/pages/users/auth/parts/LoginForm.vue`；`code:src/components/SurelyVue/Contract/CategoryCell.jsx`；`code:app/Http/Controllers/EstateController.php`；`code:app/Http/Middleware/LoginCheck.php`
- 引文（該細目全部 15 筆）：
  - [同細目其他句的引文｜drafts 句序 0] `code:src/pages/contracts/edit/tenantInfo/Index.jsx`：`{ t('合約邀請聯繫方式') }`
  - [同細目其他句的引文｜drafts 句序 0] `code:src/pages/contracts/edit/tenantInfo/Index.jsx`：`label: t('租客註冊'),`
  - [同細目其他句的引文｜drafts 句序 0] `code:src/components/SurelyVue/Contract/CategoryCell.jsx`：`label = t('待租客簽回')`
  - [同細目其他句的引文｜drafts 句序 1] `help:onboarding1_zh-Hant.html`：`租客點選郵件內之「查看合約」按鈕後，會進入該物件廣告頁供租客參考`
  - [同細目其他句的引文｜drafts 句序 1] `code:resources/views/emails/zh-TW/contracts/invite.blade.php`：`<p><a class="btn inFrameLink" target="_blank" href="{{ $url }}">查看合約</a></p>`
  - [同細目其他句的引文｜drafts 句序 1] `code:app/Notification.php`：`route('estates.house', array('no' => trans_jgb_no($contract->estate_id), 'action' => trans_jgb_no($contract->id), 'r_type' => 'tenant'))`
  - [同細目其他句的引文｜drafts 句序 2] `code:app/Notification.php`：`sms($configCountry[$toUserPhoneCountryKey]['code'], $contract->to_user_phone, $message, 'l1');`
  - [同細目其他句的引文｜drafts 句序 2] `code:app/Notification.php`：`$msgData = [$userName, short_url($redirectUrl)];`
  - [同細目其他句的引文｜drafts 句序 3] `code:resources/views/estate/show.blade.php`：`{{___('查看合約')}}</a>`
  - [同細目其他句的引文｜drafts 句序 3] `code:app/Http/Middleware/LoginCheck.php`：`// 如果沒有 session 則當下狀態為未登入`
  - [同細目其他句的引文｜drafts 句序 4] `code:src/pages/users/auth/parts/LoginForm.vue`：`{{ t('立即註冊') }}`
  - [同細目其他句的引文｜drafts 句序 5] `code:app/Http/Controllers/EstateController.php`：`session()->put('contract_invitation', [$contract->id]);`
  - [同細目其他句的引文｜drafts 句序 5] `code:app/Http/Controllers/AuthController.php`：`$fatherUser->receiveContractInvitation('contract', $contractId);`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 6] `code:src/pages/contracts/edit/tenantInfo/Index.jsx`：`label: t('租客免註冊'),`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 6] `code:src/pages/contracts/edit/tenantInfo/Index.jsx`：`t('租客免註冊：租客因無需註冊 JGB 會員而需要管理者協助填寫以下租客資訊。')`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 29. `jgb/A/notification-settings-report-buttons` 第 2 句

- 粗目：通知收件設定與發送報表（通知收件信箱最多再加 3 組）
- 細目標題：「發送報表」「多團隊合併報表」按鈕是做什麼的？（選起始日與終止日，把加盟分潤報表寄到自訂通知信箱；僅限加盟分潤報表分類，多團隊合併僅限特定團隊）
- target_user：property_manager
- **抽查句**：在視窗裡選好「起始日」與「終止日」後按「發送」，系統會把這段期間的加盟分潤報表寄到這個分類設定的自訂通知信箱，成功時會顯示「報表已發送至指定信箱」。
- sources：`code:src/use/config/useForwardNotificationEmails.ts`；`code:src/pages/users/notification/Index.vue`；`code:src/components/Lightbox/NotificationMailReport.vue`；`code:app/Services/FranchiseProfitShareService.php`
- 引文（該細目全部 15 筆）：
  - [同細目其他句的引文｜drafts 句序 0] `code:src/use/config/useForwardNotificationEmails.ts`：`showMailReportButton: true,`
  - [同細目其他句的引文｜drafts 句序 0] `code:src/use/config/useForwardNotificationEmails.ts`：`return specialRolesState.getSpecialGroupsByRole(store.state.userData?.role?.id)?.includes(SpecialRole.franchiseProfitShare)`
  - [同細目其他句的引文｜drafts 句序 0] `code:src/pages/users/notification/Index.vue`：`{{ t('發送報表') }}`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 1] `code:src/components/Lightbox/NotificationMailReport.vue`：`{{ t('起始日') }}`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 1] `code:src/components/Lightbox/NotificationMailReport.vue`：`{{ t('終止日') }}`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 1] `code:src/components/Lightbox/NotificationMailReport.vue`：`window.globalNoticeShow(t('報表已發送至指定信箱'))`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 1] `code:app/Services/FranchiseProfitShareService.php`：`if (isset($emailGroups['franchiseProfitShare']['custom_emails'])) {`
  - [同細目其他句的引文｜drafts 句序 2] `code:app/Services/FranchiseProfitShareService.php`：`'message' => '查無分潤資料',`
  - [同細目其他句的引文｜drafts 句序 2] `code:app/Services/FranchiseProfitShareService.php`：`'message' => '未設定收件人',`
  - [同細目其他句的引文｜drafts 句序 2] `code:src/components/Lightbox/NotificationMailReport.vue`：`window.globalNoticeShow(errorMessage, 'error')`
  - [同細目其他句的引文｜drafts 句序 3] `code:src/use/config/useForwardNotificationEmails.ts`：`return roleId === 21228`
  - [同細目其他句的引文｜drafts 句序 4] `code:app/Services/FranchiseProfitShareService.php`：`new \App\Exports\FranchiseProfitShareMultiTeamExport($allTeamData),`
  - [同細目其他句的引文｜drafts 句序 4] `code:app/Services/FranchiseProfitShareService.php`：`$recipients = $emailGroups['franchiseProfitShare']['custom_emails'] ?? [];`
  - [同細目其他句的引文｜drafts 句序 4] `code:src/pages/users/notification/Index.vue`：`{{ t('多團隊合併報表') }}`
  - [同細目其他句的引文｜drafts 句序 5] `code:src/pages/users/notification/Index.vue`：`function handleClickMailReport(categoryKey: CategoryKey){`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）

## 30. `jgb/B/advance-community-labels` 第 1 句

- 粗目：進階設定（費用項目、租金折扣、滯納金、補充條款範本、自訂標籤、時區語系；介面路徑「團隊管理 > 進階設定」）
- 細目標題：「社區管理」的城市／區域／位置設定是做什麼？（只有特定合作團隊看得到，用來建立社區可選用的城市、區域、位置標籤）
- target_user：property_manager
- **抽查句**：進階設定的「社區管理」區塊只會顯示給特定合作團隊，一般團隊看不到這個區塊。
- sources：`code:src/pages/users/advance/Index.jsx`
- 引文（該細目全部 5 筆）：
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:src/pages/users/advance/Index.jsx`：`state.isBeyond360 && <div class="mb-4 bg-white px-5 py-8 lg:px-10">`
  - [drafts 自報對應本句（句序未經驗證）｜drafts 句序 0] `code:src/pages/users/advance/Index.jsx`：`title={t('社區管理')}`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/users/advance/Index.jsx`：`title={t('城市設定')}`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/users/advance/Index.jsx`：`title={t('區域設定')}`
  - [同細目其他句的引文｜drafts 句序 1] `code:src/pages/users/advance/Index.jsx`：`title={t('位置設定')}`
- **判定**：成立（業主指定的獨立代理判定；依據見 `verification/20261006-p931-spotcheck-judgment.json`）
