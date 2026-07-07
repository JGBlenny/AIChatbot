# 帳務 API 欄位契約（交付 jgb2 端）

> 交付日期：2026-07-03　來源：billing-conversational-facets research.md §五（master 分支盤查，file:line 齊）
> 消費端一律**存在性驅動**：欄位/端點出現即自動啟用分支，缺失走降級——**不需與 AIChatbot 同步上版**。

## 驗證狀態（2026-07-03，jgb2 preview 修復後重盤）

| 項目 | 結果 |
|---|---|
| B1 status 欄補正 | ✅ 已修復並驗證：bills index 同給 `status`（單值）＋`bit_status`（歷程位元），真資料 709739 status=2/bit=35 語意正確 |
| `/bills/{id}` 直查 | ✅ 可用（`role_id` 為必填參數）；回應含 `details` 明細——帳單異常面向金額逐項有真資料源 |
| B3 pay_info/cvs_info 白名單 | ✅ 結構已露出（含 `expire_ymd`、頂層 `cvs_info` 鍵）；未取號帳單值為 null，消費端存在性驅動即啟用 |
| 消費端配套 | `_bill_status()` 優先序反轉（status 優先、無鍵 fallback bit_status），舊版單發診斷 5 處直讀一併收斂；e2e 對 preview 真資料全綠 |

## 第 0 層：把 preview 併回 master（既有工作，只差併版）

以下已在 preview 分支（commit d2b0117f2e）實作完成、AIChatbot 已對 preview 驗證通過，**併版即生效**：

| 項目 | 用途 |
|---|---|
| `contracts/status-overview` 滯納金三欄（enable_late_fee／late_fee_percent／calc_late_fee_buffer_days） | 滯納金面向：規則講解 |
| `GET /external/v1/bills/{id}` 直查端點 | 帳單識別鏈：編號直查 |
| bills 的 `is_archived`／`archive_ymd` | 排除封存帳單誤答 |
| （同批：合約 G1 簽署時間戳×4、G2 to_user_login_email、G4 is_newest） | 合約 spec 已驗畢 |

## 第 1 層：必要修正與新增（本 spec 首波）

| # | 項目 | 現況（file:line） | 需求 |
|---|---|---|---|
| B1 | **bills index `status` 欄補正（bug）** | `BillApiController.php:123` 寫 `'bit_status' => $bill->status`——key 叫 bit_status、值是 status，真 bit_status 遺失且無 status key | 回應同時給 `status`（單值）與 `bit_status`（歷程位元），語意對齊 contracts |
| B2 | bills index 支援 `bill_id` 查詢參數 | 現僅 contract_id（單數）/month/status/type | 識別鏈直查（若第 0 層 `/bills/{id}` 併版，此項可降選配） |
| B3 | 虛擬帳號效期露出 | 內部 `bills.pay_info.atmInfo.expire/expire_ymd`（preview `/bills/{id}` 已做白名單）；**超商代碼效期（newebpay_cvs_info.ExpireDate）連 preview 都沒露** | `/bills/{id}` pay_info 白名單補超商代碼與效期——回答「繳費代碼/帳號還能不能用」 |

## 第 2 層：選配增強（提升排障完整度，可分批）

| # | 項目 | 內部來源 | 用途 |
|---|---|---|---|
| B4 | `payment_bit_status`（各通道取號狀態） | `Bill.php:1963-1966` | 判斷帳單已開通哪些繳費管道 |
| B5 | 對帳操作人/時間（complete_user_id/role_id＋manual_complete log） | `Bill.php:3507/11479-11534` | 回答「這筆誰手動確認到帳的」 |
| B6 | 付款人轉出銀行/帳號末五碼（PayBank/PayerAccount5Code，**解析後白名單，勿回原始 response**） | `PaymentController.php:1279-1280`（現埋在 payment_logs 原始欄） | 對帳爭議核對 |
| B7 | payment-logs 支援 `payment_id` 過濾＋分頁 | 現僅 role_id＋bill_id 全回 | 多次重試付款時精準定位 |

## 第 3 層：個資收斂建議（安全向，非功能需求）

| 項目 | 現況 | 建議 |
|---|---|---|
| invoice-logs `request_data/response_data` | **原始 JSON 未過濾**（含買受人 email/載具）`InvoiceLogApiController.php:90-91` | 白名單化（status/message/invoice_number/日期即可） |
| payments `data` 欄 | 含卡號/帳號末碼 | AIChatbot 端已不消費此欄；建議評估是否需要露出 |

## 消費端承諾

- 全部存在性驅動：第 0/1 層未到位前，對應分支自動降級（通用指引/引導問句），不阻斷、不虛構。
- 非預期格式防護：欄位值非預期型態（如密文）視同不可用（沿合約 G2 教訓，已有既例）。
- 個資輸出遮罩：任何帶到回覆的識別性欄位按遮罩協定處理。

## 優先序建議

**第 0 層（併版）→ B1（bug 修正，一行）** 就能讓帳務五面向首版全功能上線；B2–B7 依 jgb2 排程分批，到一項啟用一項。
