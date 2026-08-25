# v3（attribution-only）：**`missing` 3/3——模型根本沒產生 delegation field**

> 2026-08-25｜evidence：`evidence/c4b-gated-resolver-v3-attribution.json` ＋ `…-stdout.log`
> 預算：`target_scope_calls = 3`（上限 30）／`all_provider_calls = 15`（上限 60）／retry 0
> ⚠️ 本輪**只做 attribution，不做修法驗證**：prompt／parser／resolver／ruler 全程未動。
> ⚠️ evidence 檔內部 variant 標籤仍寫 `-v2`（同一支 harness 的第三次執行），
> 檔名以 `-v3-attribution` 區分；v1／v2 紀錄皆未回填。

## 0. 歸因結果（三次完全一致）

```text
normalization_drop_reason = **missing**  ×3
raw_scope                 = switch       ×3      normalized_scope = switch ×3
allowed_delegates         = ['billing_anomaly']  ×3
raw_delegate_related_keys = ['face']     ×3      （值為 ""，不是誤放）
normalized_delegate_facet_key = None     ×3
fail_open                 = false        ×3      （真模型判定）
```

三次的 provider 原始 JSON（逐字）：

```json
{"action":"ask","extracted_fields":{},"next_question":"請提供帳單編號，或是合約編號、物件名稱，我們才能協助查詢。","scope":"switch","face":""}
{"action":"ask","extracted_fields":{},"next_question":"請提供帳單編號、合約編號或物件名稱，以便查詢相關帳單。","scope":"switch","face":""}
{"action":"ask","extracted_fields":{},"next_question":"請提供該帳單的編號或合約編號，以便進一步查詢。","scope":"switch","face":""}
```

⇒ **原始 JSON 裡根本沒有 `delegate_facet_key`。**

## 1. 依事前定死的處置表

| v3 歸因 | 結論 | 下一步 |
|---|---|---|
| **`missing` 3/3** | **模型根本沒產生 delegation field** | 查 **output contract／response schema／prompt obligation**；**不要動 parser** |

### 正式排除 parser

```text
provider raw JSON 本來就沒有 delegate_facet_key
→ parser 沒東西可保留
→ normalization 不是成因
```

⇒ 問題乾淨地落在 **evaluator output contract**，不必再猜「是不是 normalization 吃掉」。

⇒ 同時可**停止再堆自然語言 `when`**：v1→v2 已證責任語義送達（prompt 逐字渲染），
再加 wording 會走回補丁路線。

## 2. 一項**觀察**（不是 attribution 分類的一部分，未改任何東西）

persona 規則自身載明每輪的輸出形狀：

```text
每輪輸出 JSON：{"action":…,"converge_kind":…,"extracted_fields":{…},
                "next_question":…,"scope":"stay"|"switch","face":"…（如有）"}
```

而三次原始輸出的鍵集合恰為 **`action／extracted_fields／next_question／scope／face`**——
與規則宣告的形狀逐鍵吻合，且**不含**我們在規則之後才附加的 `delegate_facet_key`。

⚠️ 這是一個**與證據相容的假說**（模型照規則宣告的 schema 產出，附加段落沒有進入輸出契約），
**不是**已驗證的結論；驗證屬下一輪修法，本輪不做。

## 3. 本輪之後**不得**做的事（依裁定）

```text
❌ 不得在同一次執行後直接改碼重跑
❌ 不得動 parser（已被排除）
❌ 不得繼續加 when／wording
❌ 不得改 resolver、ruler、categories、threshold；production gate 仍 false
```

## 4. 已可據以決定的下一個修法方向（**待裁示**）

問題已收斂到單一句：**如何讓 delegation 成為 evaluator 輸出契約的一部分**。
可能的做法彼此互斥，需先選一個再凍結：

```text
(a) 把 delegate_facet_key 納入**規則所宣告的 JSON 形狀**（資料側：改 persona 規則的 schema 行）
(b) 以 **response_format / JSON schema** 在 API 層強制該欄位（程式側，模型必須輸出）
(c) 把 delegation 拆成**獨立的一次判定**（scope 判完再問一次「交給誰」），不與現有 schema 混用
```

⚠️ 三者的代價不同（(a) 動資料、(b) 動呼叫契約且影響所有面向、(c) 多一次呼叫），
**本檔不選**。
