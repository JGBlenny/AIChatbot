# C4a case-set protocol（**凍結於產生任何案例之前**）

> 2026-08-24｜語言 zh-TW｜業主裁定：走 **(2) 另立 case-set freeze**——
> 不得把 routing cohort 或 tasks 的「例：」升格為正式案例。
> 前置：任務 5.1 已完成（`e75e7c3`）；**5.2 尚未開始**；**4.6／5.3／5.4 皆未執行**。

## 為何需要本檔

第①步盤點的結果：**C4a 沒有一份封閉的案例清單**。

```text
已凍結  面向恰為兩個：bill_diagnosis（有 secondary_call）／billing_anomaly（無）
        每案的鏈路形狀（5.3）、fixture 三筆（4.4）、closure scope（numeric_bill_ref）
未凍結  具體 query／情境、case_id、數量、兩面向各自的分配
```

`requirements.md` 3.1–3.3 只規定鏈路與「至少兩個面向」；`design.md` 定義了
`ChainClosureAssertion` 的欄位（含 `query`）但**未列任何 query**；
`tasks.md` 5.2 的兩句帶「**例：**」，無 case identity、無數量、無 freeze provenance。

⚠️ 若不先凍結本協議就產案例，會製造這個自由度：
**看到 formatter 與 fixture 現況 → 決定測哪些案例 → 再定尺**。那會讓「先定尺再量」在第一步失效。

---

## ⭐ 第一鐵則：case set 與 Face ownership **脫鉤**

C4a 要驗的是：

> **在 Face 已經是 execution context 的前提下，grounding chain 是否真的閉合。**

它**不驗**：

> 這句 query 應不應該被 router 分到這個 Face。

因此案例中的 `execution_face` 定義為 **test execution context**，
**不是** normative routing label。寫死如下：

```text
C4a case inclusion SHALL NOT be cited as evidence of query→Face routing ownership.
```

⚠️ 沒有這條，5.x 會偷偷替今天剛封住的 `routing-authority-model`
（`BLOCKED_BY_EXTERNAL_DECISION`）解題。有了這條，我們才能為 `billing_anomaly` 建 C4a case，
而**不需要**解決「我的收據在哪」到底該歸 anomaly 還是 diagnosis。

---

## 1. 案例數量（**產生前寫死**）

先查證：`5.3`／`5.4` **未**規定最低案例數（僅規定鏈路形狀與「無 secondary_call 的對照組」）。
依業主指示「若沒有，就在 protocol 中明確裁定一次」，**本檔裁定**：

```text
bill_diagnosis    2 cases
billing_anomaly   2 cases
合計              4 cases（不多不少）
```

**為何是 2 而不是 1 或 5**（理由與 4.4 的差異矩陣直接相連）：

```text
1 case  不足：無法排除「無論問什麼都回傳同一筆」——單筆通過不能證明收斂是被查詢條件驅動的
2 cases 足夠：**同一面向的兩案 MUST 收斂到不同的 fixture_bill_id**，
        故「恆回同一筆」的實作必然在其中一案失敗
≥3      本階段無額外鑑別力：第三筆只增加自然語言多樣性，而 C4a 要辨識的是**執行差異**
```

⚠️ 這是**事前裁定**，不得因產生後覺得太少／太多而調整。

## 2. Inclusion axes（**產生前寫死**）

案例須覆蓋 C4a 真正要辨識的**執行差異**，不是自然語言多樣性。每案必須在下列軸上明示取值：

```text
execution_face          bill_diagnosis ／ billing_anomaly
fixture_bill_id         900001／900002／900003（4.4 已凍結）
secondary_call_required bill_diagnosis = true ／ billing_anomaly = false（5.3／5.4 已凍結的對照結構）
grounded_property_asked 該題要求的是哪一類 grounded 事實（狀態／金額／期間／可否操作…）
```

**跨案硬性條件**：

```text
C-1  同一面向的兩案 MUST 使用**不同**的 fixture_bill_id
C-2  四案合計 MUST 至少涵蓋 2 個不同的 contract_id（4.4 矩陣：700100／700200）
C-3  兩個面向的 secondary_call_required MUST 相反（有／無的對照即本組存在的理由）
```

## 3. 作者可看與不可看（**防事後適配**）

```text
✅ 可看  已凍結的 requirements／design；Face 的 execution contract；
        External API contract（research 主題 7）；4.4 fixture facts
❌ 不可看／不可利用
        哪種 query 現在 formatter 剛好比較容易滿足
        adapter 實跑結果
        5.3／5.4 的 pass/fail
        （事後）為了救紅燈而修改案例
```

⚠️ **現況聲明**：本檔撰寫時 `4.6`／`5.3`／`5.4` **均未執行**，
故上述執行結果**目前不存在**——這是本次 freeze 因果順序成立的實況基礎，不是承諾。

## 4. 本階段**不得**產出的東西

```text
❌ required_grounding_facts —— 屬 5.2
```

case artifact 中該欄位一律寫 `NOT_DEFINED_HERE`，
**刻意保留該行**，提醒 case freeze 不得偷偷兼做 5.2。
否則案例與充分性量尺同時生成，又混在一起。

---

## 5. `bill_diagnosis`：既有候選來源的 admission 規則

```text
BILLING_INSTANCE_CASES（tests/integration/conversational/test_facet_entry_routing_req.py:189-194）
  → **pre-existing candidate source, not automatically admitted**
```

四句逐句以**事前 inclusion rule** 判定，不得憑感覺挑：

```text
A-1  是否是 numeric_bill_ref 可完成的 scenario？
A-2  要求的是否為 bill-specific grounded answer？
A-3  是否能走 5.3 已凍結的 adapter → transport → secondary_call chain？
A-4  是否**不依賴** unresolved Face ownership 才能成立？
```

⚠️ **不得**以「它們目前 routing 進哪個 Face」作為 inclusion criterion——
那會把 routing 現況偷渡成案例正當性。
⚠️ 若四句最後只留兩句，那是**依 frozen rule 排除**的結果，不是「挑會過的」。

## 6. `billing_anomaly`：來源禁令與生成方式

```text
BILLING_INSTANCE_FACET_UNDECIDED  →  **prohibited as normative source**
```

那兩句（「我的收據在哪」／「我這筆點退的錢怎麼怪怪的」）本身就是**產品 ownership 未決事項**，
拿來支撐 anomaly 等於用未決問題證明未決問題。

改以 **protocol-generated synthetic execution case**：

```text
Given:
  active execution context = billing_anomaly      ← execution context，非 routing 主張
  numeric bill reference   = 90000X（4.4 fixture）
User asks:
  一個**必須**有帳單實際狀態／金額／期間等 grounding 才能回答的 instance question
```

⚠️ synthetic 在此**沒有問題**：這不是 unseen routing holdout，
本組只驗「Face 內 execution closure」，**不聲稱** router 應把自然對話送來這裡。
真正要防的是「看到 implementation output → 寫一個剛好會過的 query」——
而該風險已由 §3 與「協議先於案例」的順序擋住。

---

## 7. Case artifact 格式（**每案必填**）

```text
case_id:
source_type:            pre_existing ／ protocol_generated
source_ref:             （pre_existing 須附檔案:行號；protocol_generated 註明依本協議 §6）
execution_face:         ⚠️ test execution context，**不是** routing ownership label
query:
fixture_bill_id:
closure_scope:          numeric_bill_ref
expected_chain:
  adapter:
  primary_call:
  secondary_call_required:  true ／ false
routing_claim:          prohibited
required_grounding_facts: NOT_DEFINED_HERE     ← 屬 5.2，本階段不得填
admission:              （pre_existing 須逐條記錄 A-1～A-4 的判定）
```

## 8. 凍結後的順序

```text
本協議 freeze
  ↓
依協議產生／篩選案例 → **case set freeze**
  ↓
5.2 對 frozen cases 定 required_grounding_facts → freeze
  ↓
4.6 改 execution path
  ↓
5.3／5.4 以 frozen ruler 跑 frozen cases
  ↓
5.5 判型（🔍V）
```

⚠️ 4.6 動手之前，我們會同時擁有：**案例 ✅、充分性量尺 ✅、execution implementation 尚未改**。
這是最乾淨的實驗順序，也是本次另立 freeze 的全部目的。
