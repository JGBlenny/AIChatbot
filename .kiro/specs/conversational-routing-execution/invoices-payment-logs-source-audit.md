# `/invoices` 與 `/payment-logs` 端點盤查（jgb2 原始碼逐條對照）

> 2026-08-25｜語言 zh-TW｜零 OpenAI 呼叫、未碰 staging／production
> 來源：`InvoiceApiController.php`（181 行）／`PaymentLogApiController.php`（140 行）
> 依 `transport-migration-inventory.md` §7 六步協議；§8 第 5 項。

## 一、`/invoices`（`jgb_invoices`）

### 契約

```text
投影   formatInvoice() 逐鍵 26 欄（:107-135）
model  App\Invoice **無 $casts、無 accessor** → 全部是原始欄位值
加工   tax_rate = `$invoice->tax_rate ? (float) : null` ⇒ **0 會變成 null**（:125）
where  join bills、bills.active=1（:40-41）；viewer 圈定走 VisibleScope::billIdsQuery
篩選   user_id（whereExists contracts.to_user_id + active）／bill_id／status
排序   invoices.id **desc**（:71）
分頁   50／200；total_pages 在 total=0 時為 0
枚舉   status 0-4／category B2B・B2C／tax_type 1・2・3・**9**（App\Invoice:9-23）
```

### 抓到的偏差

```text
I1  bill_id／status **兩個參數整個被忽略**（mock 回固定兩列）→ 已修
I2  排序反了：production id desc，舊 mock 固定 5001 在前 → 已修
I3  pagination 寫死 total=2／total_pages=1，不隨過濾改變 → 已修
✅  投影 26 鍵與三組枚舉值**逐一相符**，未動
```

### GAP-I1（登記缺口，不修）

`user_id` 的過濾跨 invoices→bills→contracts 三張表。替身的發票掛在 bill 12345／12340，
帳單 fixture 是 900001-3、合約 fixture 是 678／600——**三個 fixture 宇宙不連通**
（與 GAP-B1 同源）。目前照舊忽略，並由具名測試鎖住現況、標明不得讀成已證。

## 二、`/payment-logs`（`jgb_payment_logs`）——**本輪最嚴重的一格**

### 契約

```text
回應信封  {success, bill_id, payments:[...], payment_logs:[...],
           summary:{payment_count, payment_log_count, has_successful_payment}}（:110-119）
          ⚠️ **沒有 data、沒有 mapping、沒有 pagination**
必填      role_id **與** bill_id，缺任一 → 400（:24-30）
授權      帳單需 owner_role_id = role_id 且 active=1，否則 → 404（:34-43）
payments  取自 payments 表（paymentable_type='App\Bill'），**涵蓋手動到帳**；
          price／final_price 被 (float) 轉型（:71-72）；id desc
logs      只取 whereIn payment_id（來自上一步）；id desc
summary   has_successful_payment = payments 中存在 status == 2（:116）
```

### 抓到的偏差（P 系列）

```text
P1  **信封完全不同**：舊 mock 回 {mapping, data, pagination}，把日誌放在 `data`。
    消費端 jgb_response_formatter → diagnose_payment_logs 讀的正是 `data`
    ⇒ **production 永遠拿到空清單**，面向一律回「查無此帳單的金流交易日誌」。
    與 get_tenant_contracts 同型的靜默失效：mock 全綠、線上無聲失能。→ 已修
P2  adapter 允許只帶 role_id／payment_id，而 production 缺 bill_id 直接 400
    ⇒ 線上必然失敗。→ 已修為缺 bill_id 即降級，不發那個注定失敗的請求。
P3  adapter 送 payment_id／transaction_id，**production 兩者都不讀**。→ 已修（不再送出）
P4  舊 mock 的日誌列有 `response` 欄；controller 的列映射（:92-105）**不投影它**。
    `payment_logs` 表確實有 request／response（App/Payment.php:4263 等處寫入），
    但外部 API 不回 ⇒ 診斷引擎讀 response.Status／Message 的**原因碼分析在線上無資料**，
    只能退回 note（note 有投影）。→ 已在 services/jgb/payments.py 檔頭標明，
    並用測試禁止再靠這個欄位寫邏輯。
P5  production 的 payments 列（含手動到帳）與 summary.has_successful_payment
    才是「已付款但帳單沒更新」P01 診斷真正該用的資料，舊 mock 完全沒有。→ 已補上
```

### adapter 層正規化（明示，不是捏造）

`get_payment_logs` 回傳 `data` = `payment_logs` 逐列（值全部來自回應本身），
並同時帶出 `payments`／`summary`／`bill_id`。理由：消費端契約讀 `data`，
而 production 沒有這個鍵；正規化寫在 adapter 才不會讓每個消費端各自猜。

## 三、仍未涵蓋

```text
· viewer 圈定（VisibleScope::billIdsQuery）——同 bills 的 GAP-B2，替身射程外
· 404（帳單不屬於此團隊）與 400（缺參數）的區分：我方一律折疊為 success:False
· payments/payment_logs 的真實筆數分佈與 status 值域實況
· response 欄若日後被加進投影，P4 的原因碼分析才有辦法驗
```
