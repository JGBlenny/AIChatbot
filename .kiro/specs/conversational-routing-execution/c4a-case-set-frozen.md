# C4a case set（**FROZEN**，4 案，一次凍結）

> 2026-08-24｜語言 zh-TW
> 依 `c4a-case-set-protocol-frozen.md`（v1，FROZEN `64fb3e9`）
> ＋ `c4a-case-set-protocol-v2-amendment.md`（v2，FROZEN `a0cd97a`）產生。
> admission 過程見 `c4a-case-admission-record.md`（`2721e85`）。
> **狀態：FROZEN**——`5.2` 的 `required_grounding_facts` 尚未定義；`4.6`／`5.3`／`5.4` 尚未執行。

## ⚠️ 全域條款（每案適用）

```text
execution_face            **test execution context**，不是 routing ownership label
routing_claim             prohibited
closure_scope             numeric_bill_ref（部分閉環）
required_grounding_facts  NOT_DEFINED_HERE（屬 5.2）
```

> **C4a case inclusion SHALL NOT be cited as evidence of query→Face routing ownership.**

**證據身份（v1 §9 claim ceiling）**：protocol-frozen design/acceptance cohort，
**不是** blind／generalization evidence。

---

## 跨案條件查核（協議 §2）

| 條件 | 要求 | 實際 | |
|---|---|---|---|
| **C-1a** | 同面向兩案綁不同 `fixture_bill_id` | diagnosis `900003`／`900001`；anomaly `900002`／`900003` | ✅ |
| **C-1b** | execution 須 machine-assert 實際請求對應該案 fixture | 5.3／5.4 實作時必須落實（本檔為其斷言基準） | ⏳ |
| **C-2** | 四案至少涵蓋 2 個 `contract_id` | `700200`（900003）／`700100`（900001、900002） | ✅ |
| **C-3** | 兩面向 `secondary_call_required` 相反 | diagnosis `true`／anomaly `false` | ✅ |

---

## Case 1｜`c4a-diag-01`

```text
case_id:                  c4a-diag-01
source_type:              pre_existing
source_ref:               tests/integration/conversational/test_facet_entry_routing_req.py:192
execution_face:           bill_diagnosis
query:                    幫我查點退帳單金額
fixture_bill_id:          900003          （type=2 點退；contract 700200；status=8 待對帳）
expected_chain:
  adapter:                bill_ref 數字分支
  primary_call:           bills
  secondary_call_required: true
admission:                A-1 ✅ numeric ref 可完成
                          A-2 ✅ total／final_total 在 33 欄投影與 fixture 皆有
                          A-3 ✅ 可走 adapter → transport → secondary_call
                          A-4 ✅ 不依賴未決 ownership
```

## Case 2｜`c4a-diag-02`（v2 protocol_generated）

```text
case_id:                  c4a-diag-02
source_type:              protocol_generated
source_ref:               依 v2 amendment §D-1～D-8
execution_face:           bill_diagnosis
query:                    這張帳單現在還能不能收回
fixture_bill_id:          900001          （contract 700100；status=2 待繳費）
expected_chain:
  adapter:                bill_ref 數字分支
  primary_call:           bills
  secondary_call_required: true
generation_basis:
  D-1 ✅ 所需 fact＝`status`，在 frozen External projection 的 33 欄內
  D-2 ✅ `status` 已存在於 frozen 4.4 fixture（900001 = 2）
  D-3 ✅ 未查看 formatter output
  D-4 ✅ 未查看 adapter／5.3 execution result（該二者尚未執行）
  D-5 ✅ 未新增 fixture field
  D-6 ✅ **不是**被排除需求的簡化版——被排除的是 details composition／receipt amount；
         本案問的是**可否操作**（收回），與金額組成、收據皆無關
  D-7 ✅ fixture 900001 ≠ c4a-diag-01 的 900003
  D-8 ✅ inclusion 未引用目前 routing 結果
```

⚠️ **本案刻意不追求語意多樣性**（v2 明訂）：它的目的是
**用另一筆 fixture 驗相同 execution contract 不會永遠黏在第一筆資料**（constant-record falsifier）。

## Case 3｜`c4a-anom-01`（protocol_generated，v1 §6）

```text
case_id:                  c4a-anom-01
source_type:              protocol_generated
source_ref:               v1 protocol §6
execution_face:           billing_anomaly
query:                    這張帳單的計費期間是哪一段
fixture_bill_id:          900002          （contract 700100；期間 20260901~20260930）
expected_chain:
  adapter:                bill_ref 數字分支
  primary_call:           bills
  secondary_call_required: false
generation_basis:
  D-1 ✅ 所需 fact＝`date_start`／`date_end`，皆在 33 欄投影內
  D-2 ✅ 兩者皆存在於 frozen fixture（900002 = 20260901／20260930）
  D-3／D-4 ✅ 未查看 formatter output 與 execution result
  D-5 ✅ 未新增 fixture field
  D-6 ✅ 與 details composition／receipt amount 無關
  D-8 ✅ 未引用目前 routing 結果
```

## Case 4｜`c4a-anom-02`（protocol_generated，v1 §6）

```text
case_id:                  c4a-anom-02
source_type:              protocol_generated
source_ref:               v1 protocol §6
execution_face:           billing_anomaly
query:                    這張帳單現在的狀態是什麼
fixture_bill_id:          900003          （contract 700200；status=8 待對帳）
expected_chain:
  adapter:                bill_ref 數字分支
  primary_call:           bills
  secondary_call_required: false
generation_basis:
  D-1 ✅ 所需 fact＝`status`，在 33 欄投影內
  D-2 ✅ 存在於 frozen fixture（900003 = 8）
  D-3／D-4 ✅ 未查看 formatter output 與 execution result
  D-5 ✅ 未新增 fixture field
  D-6 ✅ 與 details composition／receipt amount 無關
  D-7 ✅ fixture 900003 ≠ c4a-anom-01 的 900002
  D-8 ✅ 未引用目前 routing 結果
```

---

## 兩點必須攤開的取捨

**其一，`c4a-diag-02` 與 `c4a-anom-02` 都以 `status` 為所需 fact，但綁不同 fixture、
且分屬不同 execution_face 與不同 `secondary_call_required`。**
這是刻意的：本輪要辨識的是**執行差異**（哪一筆、有無二次查詢），不是自然語言差異。
若日後認為兩案語義過近，應以「增加執行軸」處理，而非改寫問句。

**其二，`c4a-diag-01` 與 `c4a-anom-02` 共用 fixture `900003`。**
協議只要求**同面向內**不同（C-1a），跨面向共用不違規；
且兩案的 `secondary_call_required` 相反，執行路徑本就不同。

## 本檔**未**做

```text
❌ 未定義任何 required_grounding_facts（屬 5.2）
❌ 未執行 4.6／5.3／5.4
❌ 未改 v1／v2 協議，未改 4.4 fixture
❌ 未把被排除的三筆重新納入（維持 NOT_ADMITTED_TO_CURRENT_C4A_COHORT）
```
