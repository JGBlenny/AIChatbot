# 5.2：`required_grounding_facts`（**FROZEN**）

> 2026-08-24｜語言 zh-TW｜對象：`c4a-case-set-frozen.md`（FROZEN，`451c0d2`）的 4 案
> **四案一字未改。** 本檔只定尺，不動案例、不動 extractor、不動 fixture。
> **狀態：FROZEN（業主 2026-08-24）**——①（`amount_due`）走 β 已完成；②（`billing_period`）已裁定。

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

## 業主裁定（2026-08-24）：兩題皆已結

### ① `c4a-diag-01` → 走 **(β)**，已完成（見上方 §c4a-diag-01）

### ② `c4a-anom-01` → **5.2 只凍結 `billing_period`；底層雙值送達證明交 5.3**

```text
Sufficiency semantics（5.2）  「回答『計費期間是哪一段』最低需要什麼事實？」→ billing_period
Delivery / provenance（5.3）  「該 billing_period 是否真由 start ＋ end 兩個來源值送達？」
                              → date_start 與 date_end **皆須 machine-assert**
```

⚠️ **為何不把 `date_start`／`date_end` 列為 required**：那會把 API／source schema 欄位
**提升成回答層的 semantic facts**。與本檔排除 `bill_status`（`cancel_determination` 的輸入）
是**同一原則**：

```text
計算／組成答案所需的**底層輸入** ≠ 回答層的 required fact
```

`billing_period` 才是問句要求的 proposition；`date_start + date_end` 是它的 **grounding provenance**。

---

## 交給 5.3 的 execution obligations（**由本次 freeze 補出，不得事後再議**）

⚠️ 下列為 **frozen 5.2 補出的 execution obligation**——
**不得**等看到實跑結果後才決定要不要加。

### OB-1｜`c4a-anom-01` 的雙值 delivery assertion

```text
grounding_must_contain:
  - fixture 900002 的 date_start 之 production-rendered value
  - fixture 900002 的 date_end   之 production-rendered value
AND
observed_fact_keys ∋ billing_period
```

⚠️ **expected value 一律自 frozen fixture 取得**，**不得**在測試中另抄一份日期——
否則會產生第二個 truth source。

三層必須分得乾淨，缺任何一層都不算 closure：

```text
兩個來源值有送達      → delivery
billing_period 被觀測  → semantic observation
billing_period 是必需  → sufficiency
```

### OB-2｜`c4a-anom-01` 的 negative control

```text
只有 date_start、缺 date_end（反向亦然）
→ 即使 grounding 出現「計費期間」標籤
→ **MUST NOT** 通過該 case 的 chain closure
```

⚠️ 這條直接殺掉本檔指出的假綠：**欄位名在、來源值只送一半**。
⚠️ **不因此修改 anomaly observer**——observer 仍只負責 canonical semantic observation，
來源完整性由 delivery assertion 負責。

### OB-3｜C-1b（承 case-set protocol）

```text
每案 MUST machine-assert 實際請求的 bill_ref／detail path 對應該案 fixture_bill_id
```

---

## 四案定案

| case | required_grounding_facts | 額外 execution obligation |
|---|---|---|
| `c4a-diag-01` | `amount_due` | — |
| `c4a-diag-02` | `cancel_determination` | — |
| `c4a-anom-01` | `billing_period` | **OB-1／OB-2**（date_start＋date_end） |
| `c4a-anom-02` | `bill_status` | — |

**全案共同**：OB-3（case→fixture identity）。

## 持續守住的三條否定式

```text
required_grounding_facts
  ≠ underlying API columns
  ≠ all formatter output
  ≠ all computation inputs
```
