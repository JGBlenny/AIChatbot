# 21 筆 diagnostic knowledge 的 ownership census

- 日期：2026-08-29｜母體＝帶 `條件診斷：*`（六個未 mapping 分類）的全部知識，**全量非抽樣**
- 這是有限集合的 census ⇒ 可做決定性設定稽核；`n<30` 的率宣稱限制不妨礙存在性事實

## ⚠️ 先修正兩個前提（否則整份 census 會讀歪）

```text
① 「這 21 筆零 mapping」不成立 —— 那是 category 層事實。
   19 筆帶第二個 category 且該 category 有 mapping ⇒ row 層可提名。
② 「有人接」≠「接得對」—— 本 census 的判準是**能力**，不是名稱相似度。
   ⛔ 不得因為 category 叫「條件診斷：合約」就塞給 contract_closeout。
```

## 判定規則（先寫死再套用，不邊跑邊改）

```text
OWNER_EXISTS          有面向提名，且該面向取用**與被攔截表單相同的端點**
OWNER_EXISTS_PARTIAL  有面向提名且具 API 能力，但**取的不是同一份資料**
AMBIGUOUS             有面向提名但**無任何執行能力**；正確歸屬未定 → 產品裁定
NO_OWNER              無面向、無表單
GENERAL_ONLY          本質不需個別資料（本批無此類——六個分類皆診斷型）
判定單位＝**知識（row）**，不是 (知識,面向) 配對：只要有一個面向接得住就算接住。
```

## 逐筆結果

| 判定 | 筆數 | 知識 | 被攔截表單端點 → 面向實取 |
|---|---:|---|---|
| **OWNER_EXISTS** | 11 | 3490–3494, 3507, 3510–3513, 4255 | `jgb_contracts` → `contract_diag` 取 `jgb_contracts`（**同端點**） |
| **OWNER_EXISTS** | 3 | 3497, 3500, 3501 | `jgb_payment_logs` → `billing_flow` secondary 取 `jgb_payment_logs`（**同端點**） |
| **OWNER_EXISTS_PARTIAL** | 1 | 3502 虛擬帳號過期或轉帳失敗 | `jgb_bill_detail` → 實取 `jgb_bills`／`jgb_payment_logs` |
| **OWNER_EXISTS_PARTIAL** | 2 | 3503 發票為什麼沒有開出來<br>3504 發票為什麼作廢不了 | `jgb_invoice_logs` → 實取 `jgb_bills`／`jgb_invoices` |
| **AMBIGUOUS** | 2 | 3505 為什麼不能新增物件<br>3506 物件為什麼突然全部下架 | `jgb_subscription` → `estate_guide` **無 API 能力** |
| **OWNER_EXISTS**（by design） | 1 | 3508 IoT 廠商帳號綁定失敗 | 無面向 ⇒ 表單照開；不變量 1 明文豁免（廠商選擇分流） |
| **NO_OWNER** | 1 | 3509 訂閱扣款失敗導致功能異常 | 無表單、無面向、`direct_answer` |

## 三筆 PARTIAL 裡，3503／3504 有額外實據

```text
services/jgb/invoices.py::_diagnose_issue_failure
  docstring = 「I01：發票為什麼沒有開出來」  ← **就是知識 3503 的標題**
該引擎只在 jgb_invoice_logs 被取用時觸發（jgb_response_formatter 的 endpoint 分派），
而 billing_invoice 的 grounding_scope 取 jgb_bills + secondary jgb_invoices
⇒ **專屬診斷引擎存在，卻永遠到不了。**
```

⇒ 這是「⛔ 不得把 `select=api` 升格為產品公理」的直接實據：
兩個面向都是 `select=api`，能力卻不等價。不變量 9 因此加了端點涵蓋層。

## census 的收束結論

**2026-07 面向化遷移漏掉的，主要不是 mapping，而是能力。**

```text
少 mapping？        ❌ 幾乎沒有——19/21 早就有提名路徑
少 capability？      ✅ 是主因
                    ・訂閱域**完全沒有面向**（3505／3506／3509 三筆同指這一件事）
                    ・發票診斷面向取錯資料層（清單 vs 開立日誌）
                    ・帳單明細診斷端點未被任何面向取用
responsibility 切法不完整？ ✅ 次要但真實
                    22 個面向只有 2 個宣告 responsibility contract
                    ⇒ 「誰該負責」目前無機器證據可稽核，只能靠能力反推
```

## 待裁定（⛔ 我不自行決定）

```text
1. 3505／3506／3509 —— 訂閱域要不要有面向？
   （三筆同源：新增物件受阻、物件全部下架、扣款失敗導致功能異常，
     真因都是訂閱方案狀態，而 jgb_subscription 端點與 diagnose_subscription 引擎**都已存在**）
2. 3503／3504 —— billing_invoice 是否補 jgb_invoice_logs 為 secondary？
   （純設定，可逆；但會改變該面向的答題資料面，屬產品行為變更）
3. 3502 —— billing_flow 是否補 jgb_bill_detail？同上
```

## 本 census **不能**回答

```text
⛔ production 上這些情境實際被問了多少次
⛔ 通用答案是否對使用者已足夠（那是 Layer 0 問題）
⇒ 本 census 只證明**架構上誰接得住、接住後拿不拿得到那份資料**。
```

---

# 能力回補後的 census（2026-08-29，業主裁定 YES／YES／YES 之後）

## 實測 first-commit 面向（依 `categories` 陣列順序，first-commit-wins）

```text
3502 虛擬帳號過期或轉帳失敗 → billing_flow      (api)  ＋ jgb_bill_detail
3503 發票為什麼沒有開出來   → billing_invoice   (api)  ＋ jgb_invoice_logs
3504 發票為什麼作廢不了     → billing_invoice   (api)  ＋ jgb_invoice_logs
3505 為什麼不能新增物件     → **subscription_diag** (api)
3506 物件為什麼突然全部下架 → **subscription_diag** (api)
3509 訂閱扣款失敗導致功能異常 → **subscription_diag** (api)
3507 物件為什麼不能建立合約 → contract_diag    ⛔ 未動（合約建立受阻，非訂閱）
3508 IoT 廠商帳號綁定失敗   → 無面向，表單照開  ⛔ 未動（by-design 豁免）
```

⇒ 判定變化與業主預期一致，**其餘 14 筆 ＋ 3508 未動**：

```text
3502／3503／3504  OWNER_EXISTS_PARTIAL → OWNER_EXISTS
3505／3506        AMBIGUOUS（能力遺失） → OWNER_EXISTS
3509              NO_OWNER              → OWNER_EXISTS
```

## ⚠️ 兩個「設定看起來對、能力仍失效」的假綠已擋掉

```text
① 診斷引擎是靠 **endpoint 分派** 觸發的，secondary_call 只把資料 attach 到主列
   ⇒ 只加端點宣告，`_diagnose_issue_failure`／`_diagnose_atm_expired` 仍到不了。
   已改 consumer（services/jgb/bills.py）以 attach 重用**同一個引擎**，⛔ 不複製判斷邏輯。
② 引擎把**非 list** 的 secondary 結果丟成 `[]`（主查詢卻會 `[rows]` 包起來）
   ⇒ `jgb_bill_detail` 回 dict，資料根本不會到達 consumer。
   已修成與主查詢同式，並用測試鎖住那段程式碼形狀。
```

## 驗收證據（⛔ 不以「audit 變綠」作為收案）

```text
Runtime reachability  10 條 unit（容器內）
  ・invoice_logs attach → 輸出含「發票開立紀錄」**且**含這張帳單實際的失敗訊息
  ・bill_detail attach → 輸出含該筆虛擬帳號／效期
  ・三條負控制：無 attach 不虛構、非 ATM 問題不硬塞 ATM 診斷
Responsibility        訂閱面向只掛 `條件診斷：訂閱`，⛔ 未掛 `訂閱方案`（5 筆制度說明走單發）
Preemption            `array_prepend` 有測試守住——用 append 會讓 estate_guide 仍先 commit
不動他人              測試斷言 migration 可執行語句中不得出現 3507
全 unit 層            1498 passed / 0 failed（無回歸）
不變量 9              FAIL 0（原 2）；WARN 2＝3548 分流表單、3366 jgb_payments 未涵蓋
```

## 仍紅／仍 WARN 的，照實記

```text
❌ 不變量 3：容器與本地不一致 —— 我改了 conversational_engine.py 與 jgb/bills.py 的**源碼**，
   本機容器仍是舊 image。這是 source 已驗、runtime 未同步，⛔ 不得宣稱線上已生效。
⚠️ 3366「繳費成功 繳費紀錄」表單端點 `jgb_payments` 未被 billing_flow 涵蓋
   —— 本輪未授權處置（不在三題裁定內），列為下一輪候選。
⚠️ 3548 分流表單 —— 同 3508／3522 家族，屬 by-design，維持 WARN。
⚠️ 不變量 4：`修繕報修` 查無系統脈絡（既有 WARN，與本輪無關）。
```
