# v4（output-contract repair）：**delegation chain 成立 3/3；③④ 卡在 jgb2 替身，非本修法**

> 2026-08-25｜協議 `c4b-gated-resolver-validation-v4-protocol-frozen.md`（`94c0f78`，先於執行 commit）
> evidence：`evidence/c4b-gated-resolver-v4.json` ＋ `…-stdout.log`
> 預算：`target_scope_calls = 12`（上限 30）／`all_provider_calls = 12`（上限 60）／retry 0
> ⚠️ v1／v2／v3 與舊 C4b 紀錄**皆未回填**。

## 0. 結果一句話

> **(a) 有效**：把 `delegate_facet_key` 升格進規則宣告的輸出形狀之後，
> 模型 3/3 都產生了該欄位，chain 完整走完並只 commit 最後一個面向。
> 整體仍記 **NOT VALIDATED**——因為協議要求五項同時成立，而 ③④ 未達成，
> **但 ③④ 的成因是 jgb2 替身的限制，不是 delegation 修法**。

## 1. 五項逐項（3/3 完全一致）

```text
① chain     ✅ bill_diagnosis  → switch ＋ delegate=billing_anomaly   （raw drop_reason = **kept**）
               billing_anomaly → switch ＋ delegate=contract_closeout （raw drop_reason = **kept**）
               contract_closeout → stay
② session   ✅ 只 commit contract_closeout；form_sessions 僅一列（COLLECTING）
③ grounding ⚠️ contract_closeout 的 `jgb_contracts` **確實執行了**（回應就是它的候選列表），
               但**未收斂單筆** → 沒有進入 converge
④ answer    ✗ value_not_used（收到的是候選列，非 grounded answer）
⑤ verdict   ✅ 三跳 `fail_open = false`，全為真模型判定
```

v3 的 `missing` 在 v4 變成 `kept`——**這正是 (a) 的因果證據**：

```text
v3 raw keys  action／extracted_fields／next_question／scope／face
v4 raw keys  action／extracted_fields／next_question／scope／face／**delegate_facet_key**
唯一改變      delegation field 進入規則宣告的輸出形狀（其餘一切未動）
```

三次 raw 逐字（節錄）：

```json
{"…","scope":"switch","face":"","delegate_facet_key":"billing_anomaly"}
{"…","scope":"switch","face":"","delegate_facet_key":"contract_closeout"}
```

## 2. ③④ 的成因（已定位，**不在本修法範圍**）

turn 2 給「678」後，`contract_closeout` 以 `jgb_contracts` 取資料，
但 **`_mock_get_contracts(role_id, user_id, status)` 的簽章不吃 `contract_ids`／`keyword`**——
方法級 mock **無法依識別過濾**，恆回 2 筆：

```text
1. 信義區套房A｜2026/01/01｜2026/12/31
2. 中山區雅房B｜2025/01/01｜2025/12/31
```

⇒ 引擎依設計走 N 筆分流（列候選請使用者選），**不會**收斂 → 沒有 grounded answer。
⚠️ 再補一輪「選 1」也**無法**收斂：插點 A 會把 id 填回槽位重查，
而該 mock 仍不過濾，結果依舊 2 筆。

```text
根因   `contracts` **尚未遷移**到 JGBMockTransport
       （`MIGRATED_ENDPOINTS = {"bills", "bill_detail"}`，spec conversational-routing-execution
         任務 4 刻意只遷這兩個端點）
性質   **jgb2 替身的能力邊界**，與 delegation output contract 無關
```

## 3. 依 v4 協議 §4 的裁決

```text
列 1（三跳 kept ＋ commit ＋ grounding ＋ grounded answer）→ **未全部成立** → 整體 NOT VALIDATED
列 2（raw 仍 missing 3/3 → (a) 被反證）                    → **不適用**：raw 全為 kept
```

⇒ **(a) 未被反證，且對其所針對的問題有直接因果證據。**
⚠️ 但依協議不得因此宣稱 vertical slice VALIDATED——③④ 尚未實測成立。

## 4. 可以安全宣稱／不可宣稱

```text
✅ 在此 predeclared case 上，把 delegation 納入宣告形狀後，evaluator **會**產生該欄位（3/3）
✅ resolver 依契約走完三跳、只 commit stay 的面向、且不留 transient session（3/3）
❌ 不可說：vertical slice VALIDATED（③④ 未成立）
❌ 不可說：diag-01 已修好／routing 已正確／可開 production gate／其他 Face 亦然
❌ 不可說：persona schema 是正確的長期方案（那要 (b) 的獨立研究）
```

## 5. 下一步的**互斥**選項（本檔不選，待裁示）

```text
(i)  把 `contracts` 遷入 JGBMockTransport（可依識別過濾）→ 才能實測 ③④
     ⚠️ 那是 spec conversational-routing-execution 任務 4 的延伸，範圍與 fixture 契約都要另凍
(ii) 換一個 grounding 走**已遷移端點**的 delegation 目標來驗 ③④
     ⚠️ 會改變本案的 predeclared case，等於換題目
(iii) 就把 v4 收在「delegation chain 已證、grounding 端待替身補齊」，先不驗 ③④
```

⚠️ 三者都不得在未凍結前執行；本輪**未**改 parser／resolver／ruler／production，
gate 仍 false，fixture（含規則原文）已還原。
