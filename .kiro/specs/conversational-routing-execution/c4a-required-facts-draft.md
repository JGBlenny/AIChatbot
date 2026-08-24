# 5.2 草案：`required_grounding_facts`（**待審，尚未 FROZEN**）

> 2026-08-24｜語言 zh-TW｜對象：`c4a-case-set-frozen.md`（FROZEN，`451c0d2`）的 4 案
> **四案一字未改。** 本檔只定尺，不動案例、不動 extractor、不動 fixture。

## 判定原則（每案適用）

```text
required_grounding_facts
  ≠ all observable facts
  ≠ all API-returned facts
  ≠ all formatter-emitted facts
```

> **問的是：對這個已凍結問題，要形成 grounded answer，最低限度哪些 production facts 不可缺。**

每個 required fact 必須有**獨立的 necessity 理由**，且 `requirement source` 一律指向
**production contract**（jgb2 原始碼／External projection／`getMapping()`），
**不得**從 formatter 輸出反推。

---

## `c4a-diag-01`

```text
query                   幫我查點退帳單金額
execution_face          bill_diagnosis          fixture_bill_id  900003
observation_contract    diagnosis_bracket_fact_extractor
secondary_call_required true
```

**required_grounding_facts**

```text
- amount_due
    requirement source
      **產品語義**：應收金額——jgb2 `total` 欄（BillApiController.php:143，在 33 欄投影內）；
      rag 端定義 `_bill_amount_due()`「應收金額（帳單明細合計）。無值回 None，不代 0。」
      （services/jgb/bills.py:50-53）。
    why necessary
      問句直接問金額；缺此事實即無 grounded answer。
```

⚠️ 本 key 由 **observation-contract v2 amendment** 才得以觀測——
其正當性來自 production grounding **本來就有**該表示（audit O-1／O-2 已查證），
**不是**為了讓本案可測而新增。

**explicitly_not_required**

```text
final_total（實收金額）
  → `_bill_amount_received()` 定義為**實收**，與問句所問的帳單金額（應收）是**不同事實**；
    兩欄都存在**不構成**兩者皆 required
send_determination／cancel_determination／manual_complete_determination
  → 「金額多少」不需要任何可否操作的判定
```

**✅ 原 unresolved_requirement 已解除（β 成功）**

```text
原狀    `bill_diagnosis` 的 observer 只映射三個 determination key，無金額 key
        → 「金額已作為 fact 送達」在充分性維度無法表達
處置    業主裁定走 (β) measurement-instrument amendment：
        先凍結 audit rule（a221c11 的 O-1～O-6），再查核 production grounding
查核結果 O-1 ✅ `_format_bill_status()`（services/jgb/bills.py:526-538）確有
             `• 金額：{_money(total)}`，且 `total = _bill_amount_due(bill)`（:531）
         O-2 ✅ 可用 deterministic label ＋ 金額渲染觀測：`金額\s*[：:]\s*NT\$`
             （不綁 bullet；`（系統未記錄）` 缺值標記刻意不匹配）
         O-3 ✅ observer 仍不含 sufficiency policy
         O-4 ✅ 未改 production formatter
         O-5 ✅ 未查看 5.3／5.4（尚未執行）
→ **β 成功，未落入 γ**；observer 已加入 `amount_due` 並重新 freeze。
```

⚠️ **`amount_due` ≠ `amount_stored`**：前者是本問句所需的**應收**事實，
後者是 anomaly observer 對 `帳單金額 …（系統存值）` 的呈現語義。
兩觀測器**互不越界**（已具名測試）。

---

## `c4a-diag-02`

```text
query                   這張帳單現在還能不能收回
execution_face          bill_diagnosis          fixture_bill_id  900001
observation_contract    diagnosis_bracket_fact_extractor
secondary_call_required true
```

**required_grounding_facts**

```text
- cancel_determination
    requirement source
      jgb2 `Bill::canCancel()`（app/Bill.php:11289-11296）：
        `$status = [BILL_READY => true, BILL_PREPARE_TO_READY => true];
         return isset($status[$this->status]);`
      → **可否收回的完整條件就是 status 落在 {2, 32}**，**無其他欄位參與**、無型態限制。
      鏡射於 rag 端 `_diagnose_cannot_cancel()`（services/jgb/bills.py:387-390，
      並註明 20260731 R-33 勘誤：舊版「只有待發送能取消」方向相反）。
    why necessary
      問句直接問「能不能收回」；缺此判定即無 grounded answer。
```

⚠️ **依業主指示重新問過「`status` 是否真的足以回答」**：
**是**——`canCancel()` 的條件式**只讀 `status`**，不需 cancellation condition 之外的欄位。
故本案 required 只有一項，且其正當性來自 **jgb2 contract**，
**不是**因為 fixture 剛好只有 status、也不是因為 formatter 能呈現 status。

**explicitly_not_required**

```text
bill_status（狀態值本身）
  → 使用者問的是**可否操作**，不是狀態；狀態是 canCancel 的**輸入**，不是答案。
    ⚠️ 若把它也列 required，等於把「實作用到的中間值」誤當「回答所必需的事實」。
send_determination／manual_complete_determination
  → 與「能不能收回」無關
amount_stored／final_total／billing_period
  → 與可否收回無關（`canCancel()` 不讀任何金額或期間欄位）
```

**unresolved_requirement**：無。

---

## `c4a-anom-01`

```text
query                   這張帳單的計費期間是哪一段
execution_face          billing_anomaly         fixture_bill_id  900002
observation_contract    anomaly_labeled_field_extractor
secondary_call_required false
```

**required_grounding_facts**

```text
- billing_period
    requirement source
      External projection 的 `date_start` 與 `date_end`
      （BillApiController.php:146-147，`formatBill` 逐鍵；亦在 4.4 frozen fixture 內）。
    why necessary
      問句所問即計費期間本身；缺之則無可作答的事實。
```

**explicitly_not_required**

```text
due_date（繳費期限 `date_expire`）
  → 期限與期間是**不同欄位、不同語義**；問期間不需要期限
bill_status／amount_stored
  → 與期間無關
```

**⚠️ unresolved_requirement**

```text
canonical key `billing_period` 是**觀測層的複合**：其底層 production facts 是
`date_start` 與 `date_end` **兩個欄位**。

→ 僅斷言 `billing_period` 已觀測到，**不足以**證明兩個底層欄位皆已送達
  （例如只送 start、end 缺漏但仍印出某種期間字串的情形，本層看不出來）。
⚠️ 補救屬**送達性維度**（`grounding_must_contain` 兩個日期字面），
   但那是 **5.3 的斷言規格**，不是 5.2 的尺——故此處只標記，不在本檔決定。
```

---

## `c4a-anom-02`

```text
query                   這張帳單現在的狀態是什麼
execution_face          billing_anomaly         fixture_bill_id  900003
observation_contract    anomaly_labeled_field_extractor
secondary_call_required false
```

**required_grounding_facts**

```text
- bill_status
    requirement source
      External projection 的 `status` 欄（BillApiController.php:138）
      ＋ `getMapping()['status']` 的六個權威標籤（同檔 :176-183）：
        1 待發送／2 待繳費／8 待對帳／16 已繳費／32 排定發送／64 已失效。
      ⚠️ canonical semantics 取自 **API 的 mapping**，**不是**從 anomaly formatter 反推。
    why necessary
      問句所問即狀態本身。
```

**explicitly_not_required**

```text
bit_status
  → `status`（單一現值）與 `bit_status`（累積位元遮罩）是**兩件事**；
    問「現在的狀態」對應的是 `status`，不需要走過的里程碑
amount_stored／billing_period／due_date／invoice_status
  → 與「現在的狀態」無關
cancel_determination 等判定
  → 問狀態不需要可否操作的判定
```

**unresolved_requirement**：無。

---

## 待業主裁定（**本檔不預選**）

```text
① c4a-diag-01 的充分性無法在 frozen observation contract 下表達（金額不是 diagnosis 的 canonical key）
   可能方向（皆需裁定，我不選）：
     (α) 該案的充分性維度**明示不適用**，只驗送達性——但這會與「空 required 不構成通過」抵觸
     (β) 擴充 diagnosis observation contract 使金額成為 canonical key
         ⚠️ 那是**改觀測契約以配合案例**，因果與本輪相反
     (γ) 承認 case↔extractor 配對本身有問題 → 但案例已 FROZEN，不得由本檔改動

② c4a-anom-01 的 `billing_period` 是複合觀測，是否要求 5.3 以送達性補足兩個底層日期字面
```

### ① 已裁定並完成（β 成功）

四案的尺**皆已非空**。剩下 ② 仍待裁定：

```text
② c4a-anom-01 的 `billing_period` 是複合觀測——是否要求 5.3 以送達性
   補足 `date_start`／`date_end` 兩個底層日期字面？
   （本檔立場：屬 5.3 斷言規格，不在 5.2 決定；此處僅標記）
```

⚠️ ② 裁定後即可 FROZEN。
