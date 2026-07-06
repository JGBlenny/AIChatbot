# 研究紀錄：billing-conversational-facets（jgb2 帳務 ground truth 盤查）

> 建立時間：2026-07-03　來源：`/Users/lenny/jgb/project/jgb_interrogation/jgb2`（Laravel，**master 分支**）五路平行盤查，皆附 file:line 證據。
> ⚠️ 分支前提：盤查基準為 master；「G1–G4＋帳務擴充欄位」只在 **preview 分支**（commit d2b0117f2e），未併 master——見 §五。

## 一、金流狀態機（繳費金流排障面向的 grounding 基礎）

- **雙欄位與合約同構**：`bills.status`（當前）＋`bills.bit_status`（歷程位元）。枚舉（`Bill.php:39-45`）：`1 待發送(PREPARE)｜2 待繳費(READY)｜8 待對帳(PAYED)｜16 已到帳(COMPLETE)｜32 排定發送｜64 已失效(僅儲值型)`。
- **狀態轉移鏈**：1 →(schedule)→ 32 →(bill:batch-send 12:00-15:00 或手動，取虛擬帳號＋寫 ready_at)→ 2 →(租客繳費，寫 pay_at)→ 8 →(webhook/排程/手動到帳，寫 complete_at)→ 16。旁路：8→(revertToReady 清 pay_*)→2；2/32→(cancel 收回，**payment_id 清空**)→1。
- **「繳了狀態沒跳」的核心分支**：
  - **超商條碼（國泰）是唯一天然停在「待對帳」的通道**：每日 12:00 排程查詢寫入 pay_at（狀態→8）；**撥付到帳每月逢 5/15/25（假日順延）** 才批次 setComplete（`BillReconcileAccount.php:214-268`、`Kernel.php:176-177`）。
  - ATM 類（國泰即時入金 webhook `cathaybkXml`、藍新 ATM）通知一到 setPaid＋setComplete 一步到位（`Payment.php:5497-5517`、`PaymentController.php:1391-1400`）。
  - **金額不符** → 只 setPaid＋setAbnormal，卡待對帳等人工（`Payment.php:5423-5477`）→ 導客服分支的精確判準。
  - 補救排程：`cathaybk:reconcile-deposits` 每 5 分（掉單補沖）、`cathaybk:repair-paid-bills` 每小時（payment 已 paid 但 bill 未 complete）、固定 VA `bill:recharge-account` 每日 03:00。
- **虛擬帳號（口徑修正）**：
  - **國泰 ATM 帳號「沒有」失效時限**（`Payment.php:2782` 程式註解明說）——客服口徑「虛擬帳號過期」需修正歸因。
  - 有效期概念只在：藍新 ATM 180 天（`Bill.php:1765`）、國泰超商條碼代收期 3 個月（`Payment.php:2791-2796`）；且**系統無主動判 VA 過期的邏輯**。
  - **「收回重發會刷新帳號」證實**：cancel 清 payment_id（`Bill.php:11334`）→ 重發 new Payment 重新取號（`Bill.php:1724-1768`）；同 payment 同金額會沿用舊號（`Payment.php:2755`）——刷新的關鍵是 cancel 斷開。
- **手動到帳**：`manualComplete`（`Bill.php:11453-11495`）——已 COMPLETE 擋重複、無 pay_at 自動補、可回溯到帳日；非當日到帳不開發票（`:11550`）。

## 二、帳單產生與金額組成（帳單異常面向的 grounding 基礎）

- **產生時點**：`bill:gen` 每日 01:31（`Kernel.php:192`）；**最早提前一個月**產出（`Contract.php:26618` 時間閘「本月1號+1月 ≥ 帳單起始月」）。
- **過去起始日補產**：簽約完成當下以 `contract_finish_sign_at` 為基準**遞迴補產到當期**（`ContractController.php:15352`、`Contract.php:27266-27275`）。
- **金額鏈**：租金（`getDiscountedRent`，is_discount/週期折扣）＋首期押金＋fees 品項，各項 `rate=實際天數/名目週期天數` 比例後 round → `calcTotal()`（data 加總）→ `migrateDataToDetail()` 落 items/details → `setTotal()` 覆寫；**`final_total` 只在實際付款時寫入**（`Bill.php:11429`）。
- **期限**：合約 `cycle_date`（「N 日前支付」，距今不足 5 天延為今日+5，`Contract.php:26641-26647`）；另有 `cycle_date_type`（1 提前截止/2 同月截止）。
- **發送**：團隊 `batch_send_bill_days`（到期前 N 天）→ `bill:auto-batch-send` 07:00 排定＋`bill:batch-send` 12:00-15:00 發送。
- **租客「看不到帳單」三條件**（`BillController.php:723-727`）：必須同時 (a) 自己是付款方 payer_role_id、(b) **status=BILL_READY（已發送，有 ready_at）**、(c) active=1（未封存）——待發送/排定發送租客看不到。
- **封存影響**：active=0 後所有正常列表消失、催繳全停（notify-pay/notify-overdue 皆 where active=1）。

## 三、發票（發票面向的 grounding 基礎）

- **狀態枚舉**：發票主檔 `Invoice.status`（`Invoice.php:9-13`）：`0 未開｜1 已開立｜2 作廢｜3 折讓｜4 作廢折讓`；帳單層 `bills.invoice_status`：`0 未開｜1 已開｜2 異常`。
- **⚠️ 失敗沒有獨立狀態值**：開立失敗時 Invoice.status 也可能是 1——**判準是 `number` 是否為空**（`InvoiceService.php:1123-1129` 防重複註解明說）。
- **失敗分類器現成**（`InvoiceFailureClassifier.php:11-27`）：`設定缺失/期間內無可用合約/字軌不足/API 錯誤/資料錯誤/已到帳未開票/其他`——直接可作面向分支語意；每日 09:00 稽核排程。
- **開立時點三軌**：預設 postBillingIssue（到帳才開，setComplete/markAsCompleted 觸發）；團隊設 preBillingIssue 走每日 05:00 排程（onSend/beforeDue/afterDue±offset）；手動/後台補開。
- **設定層級**：帳單自身 `is_auto_generate_invoice` 是硬條件（建單時繼承合約，可個別覆寫；合約改設定回寫未完成帳單）；「何時開」由 Role `invoice_mode` 決定；金鑰 `role_invoices`（ezPay/eCloud，須 active=1 否則例外）。
- **補開條件**（客服模組 `InvoiceSupplementService.php:80-86`）：已有有效發票→拒絕；未付款→拒絕；重開要求原發票已作廢。
- **差額發票是完整子系統**（包租業月結差額，財政部 107 年令）：群組月結、每月 1 日 03:00 排程；群組內帳單開一般發票會**剔除租金品項**——面向設計上差額群組操作導客服，只做解讀。

## 四、滯納金（口徑修正：兩套獨立機制，非四版本）

- **機制 A「延遲金」（付款後結算）**：僅統上團隊白名單（`tone_sang_bind_role_ids`）＋合約 `enable_late_fee=1` 雙閘。到帳當下結算：`租金 ×（付款日−期限−緩衝天數）× late_fee_percent%`（`Bill.php:17018-17032`），開獨立 type=4 罰款單、到期日=產生日、含三行式計算備註（`late_fee_info.note`）。**「備註版」＝此版本身，非獨立客製版**。
- **機制 B「滯納金排程」（對未付款帳單開單）**——**證偽「付款後才結算」的全稱敘述**：
  - 住都階梯式（每日 02:00）：`租金 × 2%`（逾 30 天改加重費率），**不乘天數**，每帳單最多 2 筆，到期日=合約迄日。
  - 富喬固定額（每日 00:00）：逾期恰滿 5 天觸發一次、固定 500、到期日=當月最後一天、**滯納金單不標逾期**。
- **共同**：各帳單各自結算不累加；滯納金/延遲金單不再生滯納金（type 過濾證實）。
- **手動途徑**：merge 把歷史待收滯納金併入點退/租金單（`BillController.php:10334`）；帳單編輯品項名「延遲金」可直接指定金額（`BillService.php:670-673`）。無「一鍵產生獨立滯納金單」API。
- **→ 既有知識 3531/3532 需修正**：全稱「付款後結算」限縮為統上版；刪「備註版」獨立版本敘述；補「排程版對未付款開單」與各版到期日差異。

## 五、外部 API 露出面與 G 清單

- **⚠️ 分支風險（部署級）**：`contracts/status-overview` 的滯納金三欄、G1 簽署時間戳、G2 login_email、G4 is_newest、`bills/{id}` 直查端點、bills 的 is_archived——**全部只在 preview 分支（d2b0117f2e），未併 master**。我方所有驗證打的是 preview 環境。**合約與帳務兩個 spec 的 prod 部署都依賴 jgb2 把 preview 併回 master**（存在性驅動保證不併也不炸，但完整分支不啟用）。
- **端點欄位清單**（master）：bills index（30 欄含 total/final_total/date_expire/pay_at/complete_at/invoice_status/online_payment_action）；payments（含 data 個資欄）；payment-logs（三段：payments[]＋payment_logs[]（不含 request/response 原始，良好）＋summary.has_successful_payment）；invoices（29 欄含 buyer 個資）；invoice-logs（**request/response 原始 JSON 未過濾——個資收斂候選**）。
- **⚠️ bills index 現行 bug**：`BillApiController.php:123` `'bit_status' => $bill->status`——輸出 key 叫 bit_status、塞的是 status 值，真 bit_status 遺失且無 status key。**消費端判讀帳單狀態時實際拿到的是 status（單值）**——v1.1 `diagnose_bill` 的 STATUS_LABELS 恰好按單值寫所以沒炸，但欄位語意錯位要修（G 候選：補正 status 欄）。
- **bills 查詢參數**（master）：role_id 必填、user_id、**contract_id（單數）**、status、type、**month（YYYY-MM 比對 date_expire）**、排序、分頁；**無 bill_id 直查**（preview 才有 GET /bills/{id}）。
- **payment-logs**：role_id＋bill_id 必填；一筆繳費=payments 1 列＋payment_logs N 列（含取號/回調事件）；手動到帳只有 payments 列。
- **G 清單候選**（欄位｜來源｜掛哪｜用途）：滯納金三欄（preview 併回）｜VA 效期 expire_ymd（preview bills/{id} 已做；超商代碼效期連 preview 都沒露）｜payment_bit_status（取號狀態）｜complete_user/role_id＋manual_complete log（誰對的帳）｜PayBank/末五碼（解析白名單，勿回原始）｜**bills status 欄補正（bug fix）**｜is_archived（preview 併回）｜payment-logs 支援 payment_id 過濾＋分頁｜invoice-logs 原始欄白名單化（個資收斂）。
- **個資面**：payments.data（卡號/帳號末碼）、recharge-accounts 完整虛擬帳號＋租客三聯絡欄、invoices buyer 五欄、invoice-logs 原始 JSON——面向 facts 輸出需遮罩協定（沿 G2 教訓：非明文防護）。

## 六、對既有規劃的修正結論

1. **識別鏈需要 adapter**（設計核心決策）：master 的 bills index 無 bill_id 直查、無名稱 keyword——「使用者給帳單編號」與「給物件名稱」都不能單靠一個端點的 search_params。解法：`jgb_system_api.get_bills` 做識別 adapter（數字→試 bill_detail 直查；文字→先 contracts?keyword 取 contract_id → bills?contract_id 列候選帶期別/金額 label），屬 JGB 領域檔職責，零改引擎。
2. **「虛擬帳號過期」知識要照真碼寫**：國泰 ATM 無效期；解法「收回重發刷新帳號」有效但歸因改為「重發產生新繳費資訊」。
3. **滯納金知識 3531/3532 修正**（見 §四）。
4. **發票失敗判準**用 `invoice_status=2`＋分類器語意，不可只看 Invoice.status。
5. **超商待對帳的「預期時程」可寫死**：撥付每月逢 5/15/25（假日順延）——回答「要等多久」有據。
6. **租客看不到帳單三條件**可機械判：payer＋READY＋active。
7. formatter 面向感知沿 face 貫穿；**帳務 builder 吃的列來自多端點**（bills 列/bill_detail/payment-logs 三段/invoices）——FACE_BUILDERS 簽名沿 (row, question)，row=attach 後的複合資料（secondary_call 機制現成）。

## 參考

- 五路盤查完整報告：本次 session 子代理輸出（金流狀態機/帳單產生/發票/滯納金/API 露出面），關鍵 file:line 已內嵌上文。
- 既有 ground truth：`contract-conversational-facets/research.md`（面向化路徑、快照原則）、`conversational-diagnosis`（v1.1 引擎）。
