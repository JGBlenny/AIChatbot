# `C4b-gated-resolver-validation` **v2**：**NOT_VALIDATED**（與 v1 同一跳、同一形狀）

> 2026-08-25｜協議 `c4b-gated-resolver-validation-v2-protocol-frozen.md`（`068bb0d`，先於執行 commit）
> evidence：`evidence/c4b-gated-resolver-v2.json` ＋ `…-stdout.log`
> 預算：`target_scope_calls = 3`（上限 30）／`all_provider_calls = 15`（上限 60）／retry 0
> ⚠️ v1 的 NOT_VALIDATED 與舊 C4b 歷史**皆未回填**。

## 0. 結果

```text
verdict = NOT_VALIDATED
3/3 仍停在**第一跳**：bill_diagnosis → scope=switch、**delegate_to=None**
  → switch_without_delegate → 不 commit → 兜底文案
  fail_open = **false**（三次皆 reason=responsibility_contract，是真的模型判定）
  session rows = 0
```

## 1. 修法確實送達（**裁決前提已驗證，零成本**）

```text
✓ fixture 寫入・還原      測試庫現存 responsibility 為 None ＝ 已正確還原
✓ 契約解析                delegate_specs == (('billing_anomaly', '帳單金額組成/看不到帳單'),)
✓ prompt 逐字渲染         「…允許轉交的對象（括號內為該對象負責的情況）：
                           billing_anomaly（帳單金額組成/看不到帳單）。…」
```

⇒ **`when` 這條修法本身有效落地**，模型看得到語義對應，仍未填 `delegate_facet_key`。

## 2. 依 v2 協議 §5 事前定死的解讀（**不臨場發明**）

> 仍停在第一跳 `switch + no delegate`
> → `when` 已排除「key↔語義對應不足」
> → 問題**升級為 evaluator／output-contract 問題**

```text
已排除    contract representation 缺乏語義對應（v2 補上仍不填）
已排除    resolver control flow（三個分支皆照設計運作，v1 已證）
已排除    fixture／parsing／白名單／prompt 傳遞（兩輪各自查證）
已排除    fail-open 混過去（三次皆 model verdict）
剩下      **evaluator 的輸出契約**：模型「判得出不屬於我」，卻不肯／不會**指名**接手者
```

## 3. ⚠️ 一個必須先補的 evidence gap（**零成本，補完才值得再花錢**）

目前 resolver 各跳只記到正規化**之後**的結果，**未保留 brain 的原始 JSON**。
因此無法區分三種情況：

```text
(a) 模型完全沒輸出該欄位
(b) 模型輸出了，但鍵名不同（如 delegate／face／target）→ 被我們丟棄
(c) 模型輸出了白名單外的值 → 被正規化丟棄（這種目前也看不到）
```

⇒ **在補上原始輸出捕捉之前，不應再開下一次付費執行**——否則第三輪仍會得到
同一句「沒填」，而分不出是誰的問題。捕捉點在**測試側**（spy `conversational_step` 的回傳），
**不需要**改 production 程式。

## 4. 本輪已確定、不必再驗

```text
✅ `when` 的實作與渲染正確（並有 unit 鎖住「拿 when 當 key 會被丟棄」）
✅ 兩條 edge 的 fixture 一次補齊、且逐字取自 authoritative persona wording
✅ gate 隔離、fixture 還原、預算與 fail_open 記錄機制都可用
✅ 這不是「為了變綠改尺」——尺與 resolver 全程未動
```

## 5. 尚未做（等裁示）

```text
❌ 未補 raw brain output 捕捉（§3，零成本）
❌ 未再執行第三輪（需授權，且應在 §3 補完之後）
❌ 未改 evaluator 的輸出契約（那是下一個修法候選，需先有 §3 的證據才知道要改哪一種）
❌ 未動 production：gate 仍 false、DB 無 delegates、categories／threshold／ownership 未改
```
