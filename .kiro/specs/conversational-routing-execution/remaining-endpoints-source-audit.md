# 其餘七支端點盤查（原判 C 級 → 查證後**全部是 live**）

> 2026-08-25｜語言 zh-TW｜零 OpenAI 呼叫、未碰 staging／production
> `transport-migration-inventory.md` §8 第 9 項。

## 分級改判

C 級的前提是「repo 內 seed 未見面向引用」。實際查 dev DB（業主裁定本地≡線上）後：
`jgb_contract_checkin`／`jgb_payments`／`jgb_repairs`／`jgb_tenant_summary`／
`jgb_invoice_logs`／`jgb_subscription`／`jgb_iot_manufacturers` **在 knowledge_base 或
form_schemas 都有設定**，`jgb_repair_categories` 則由 `repair_prefill.py:116` 直接呼叫。
⇒ **八個全部是 live**，C 級這一層不存在，改為逐一盤查。

## 一、`/invoice-logs`——這一支問題最大

```text
契約  bill_id **或** invoice_id 至少一個，皆缺 → 400（:23-25）
      ⚠️ 本端點**完全不看 role_id**（controller 沒有任何 role 圈定）
      篩選 bill_id／invoice_id／action；orderBy id desc；回應只有 data＋pagination
投影  formatLog()：id, invoice_id, bill_id, manufacturer, action, type, http_code,
      **response_parsed**, note, created_at
```

```text
L1  ⚠️ production **不外露原始 request_data／response_data**（含買受人 email、載具號碼），
    只回白名單化的 `response_parsed = {status, message, invoice_number,
    random_number, invoice_date}`，且 `Result` 巢狀 JSON 由它先解一層（:97-131）。
    舊 mock 回的是原始 `response_data`，而 services/jgb/invoices.py **三處**都讀那個鍵
    ⇒ 線上永遠取不到回應內容。已修替身，並在消費端加 `_log_response()` 正規化
    （以 response_parsed 為主、response_data 為相容備援）。
L2  舊 mock 憑空回了 `mapping`——production 這支沒有。已移除。
L3  adapter 只要求 role_id；production 要求 bill_id 或 invoice_id。已改為缺兩者即降級。
L4  三個篩選參數與排序未實作 → 已實作；並新增一列 `response_parsed = None`
    （production 對空回應回 null，:100-103），讓消費端的 null 分支測得到。
```

## 二、`/payments`

```text
✅ 投影 28 鍵（formatPayment:113-143）本來就對
P-1 四個篩選（user_id／bill_id→**paymentable_id**／status／month）全部被忽略 → 已實作
P-2 排序未實作（production orderBy payments.id desc）→ 已實作
P-3 pagination 寫死 total=2 → 已改為隨過濾結果計算
```

## 三、`/repairs`

```text
✅ 投影 38 鍵（formatRepair:394-...）本來就對
R-1 篩選 status／estate_id／category_id／**is_urgent→emergency_status**／keyword 全被忽略 → 已實作
    ⚠️ `emergency_status` 的語義曾經反轉過（conversational-repair 的地雷），不可望文生義
R-2 pagination 寫死 → 已改
```

## 四、四支本來就忠實的端點（**未改，只補測試釘住**）

```text
/repairs/categories        {id, name, items:[{id, name, broken_reasons[]}]} ✅
/roles/{id}/subscription   14 鍵＋estate_usage；limit = plan_estate_limit + coupon + extra、
                           remain = max(0, limit - current)（:35-40）——production **不投影**
                           coupon／extra，故替身的 limit 必須自洽（55 = 50 + 5）✅
/iot-manufacturers         嚴格白名單 select，**不含 manufacturer_password**（:27-31）✅
/tenants/{uid}/summary     tenant_info／contract_summary／bill_summary 三段 ✅
/contracts/{id}/checkin-eligibility
                           eligible／contract_status／first_bill_status／deposit_status／
                           checkin_blockers ✅（形狀對；但替身只有 eligible=true 一種情境，
                           三個 blocker 分支未涵蓋——列為後續 scenario 工作）
```

## 五、仍未涵蓋

```text
· checkin 的三個 blocker 分支（contract_not_signed／first_bill_unpaid／deposit_insufficient）
  與「無帳單」label，替身只有全綠情境
· 押金計算：deposit_type=1 走固定金額、否則 deposit × rent（:110-117）——未以替身覆蓋
· tenant_summary 的加密個資欄位（lessee_name／email／phone）真實形狀
· 各端點 404／403 與 400 的區分：我方一律折疊為 success:False
