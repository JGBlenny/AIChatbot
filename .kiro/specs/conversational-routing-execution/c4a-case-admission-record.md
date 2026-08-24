# C4a case admission record（**尚未 freeze — 缺 1 案，待裁定**）

> 2026-08-24｜語言 zh-TW｜依 `c4a-case-set-protocol-frozen.md`（FROZEN，`64fb3e9`）§5 執行
> **狀態：BLOCKED**——`bill_diagnosis` 依 frozen admission rule 只通過 **1 案**，協議要求 **2 案**。
> ⚠️ 本檔**不是** case set freeze；在補齊之前不得被引用為已凍結案例。

## 判定依據的界線（先寫清楚）

依協議 §3，admission 只依 **frozen External projection（33 欄）＋ 4.4 fixture facts** 判定。

```text
✅ 依據：query 要回答所需的事實，是否存在於 frozen projection ／ fixture
❌ 未依據：formatter 目前輸出什麼、哪種問法現在比較容易滿足（§3 明文禁止）
```

⚠️ 這個區別是本次 admission 有效性的關鍵：**若改以 formatter 輸出判 admission，
就是「看實作挑會過的案例」**——正是本協議存在的理由。

---

## `bill_diagnosis`：四句逐句 admission（來源 `test_facet_entry_routing_req.py:189-194`）

| # | query | A-1 numeric ref 可完成 | A-2 bill-specific grounded | A-3 可走 frozen chain | A-4 不依賴未決 ownership | 判定 |
|---|---|---|---|---|---|---|
| 1 | 我的這張點退帳單金額怎麼算出來的 | ✅ | ⚠️ 需**逐項明細** | ❌ | ✅ | **EXCLUDED** |
| 2 | 我這筆點退帳單怎麼會是這個數字 | ✅ | ⚠️ 需**逐項明細** | ❌ | ✅ | **EXCLUDED** |
| 3 | 幫我查點退帳單金額 | ✅ | ✅ | ✅ | ✅ | **ADMITTED** |
| 4 | 這張帳單的收據金額多少 | ✅ | ❌ 需**收據**欄位 | ❌ | ✅ | **EXCLUDED** |

### 排除理由（逐筆，附依據）

```text
#1／#2  「怎麼算出來的」「怎麼會是這個數字」要求的是**金額的組成**（逐項明細）。
        External detail 回應雖含 `details`，但 **4.4 frozen fixture 未建模 details**
        （4.5 已列為 known-unmodelled，理由：fixture 投影不含，補上等同虛構）。
        → 在 frozen artifacts 內**無法 ground**，A-3 不成立。

#4      「收據金額」需要**收據**概念。frozen projection 的 33 欄
        （`EXTERNAL_BILL_FIELDS`）**無任何收據欄位**——收據屬另一組資料。
        → A-2／A-3 不成立。
```

⚠️ **三筆排除與「它們目前 routing 進哪個 Face」無關**——協議 §5 明文禁止以此為 criterion，
本次亦未使用。

### `ADMITTED` 的一案（草案，未凍結）

```text
case_id:                  c4a-diag-01
source_type:              pre_existing
source_ref:               tests/integration/conversational/test_facet_entry_routing_req.py:192
execution_face:           bill_diagnosis        ⚠️ test execution context，非 routing ownership label
query:                    幫我查點退帳單金額
fixture_bill_id:          900003                （type=2 點退；contract 700200）
closure_scope:            numeric_bill_ref
expected_chain:
  adapter:                bill_ref 數字分支
  primary_call:           bills
  secondary_call_required: true
routing_claim:            prohibited
required_grounding_facts: NOT_DEFINED_HERE      ← 屬 5.2
admission:                A-1 ✅／A-2 ✅（total／final_total 在 projection 與 fixture 皆有）／
                          A-3 ✅／A-4 ✅
```

---

## 為何停在這裡（不自行補案）

協議只授權兩種來源：

```text
§5  bill_diagnosis  → pre_existing（BILLING_INSTANCE_CASES）依 A-1～A-4 admission
§6  billing_anomaly → protocol_generated synthetic execution case
```

**§6 的 protocol_generated 只授權給 `billing_anomaly`**。
`bill_diagnosis` 缺的第二案若由我自行以 synthetic 補上，等於**擅自擴張 §6 的適用面向**——
而協議正是為了消除這種臨時自由度才凍結的。

⚠️ 同樣不可行的替代：**放寬 A-1～A-4** 讓 #1／#2／#4 其中一筆進來。
那會使 admission 變成「調到剛好湊滿 2 案」，且 #1／#2 進來後必然因
fixture 未建模 details 而紅——那是**測資缺口**，不是執行鏈缺陷，會直接污染 5.5 的判型。

## 需業主裁定的三條路（**不預選**）

```text
(i)   擴張 §6：允許 bill_diagnosis 亦可 protocol_generated
      → 補一案 synthetic（綁不同 fixture_bill_id，滿足 C-1a）
      代價：diagnosis 側從「全部沿用既有來源」變成「一半 synthetic」

(ii)  擴充 fixture：讓 4.4 建模 `details`，使 #1／#2 可 admission
      代價：**動已凍結的 4.4**，且 4.5 已把 details 列為 known-unmodelled；
            需重跑 4.4／4.5 驗收，且 fixture 擴充本身要有 External 契約依據

(iii) 改 N：把 bill_diagnosis 降為 1 案
      代價：**直接廢掉 N=2 的論證**——單案無法排除「恆回同一筆」，
            C-1a／C-1b 對該面向失效。**我認為這條最弱。**
```

⚠️ `billing_anomaly` 的兩案（§6 protocol_generated）**尚未產生**——
待 `bill_diagnosis` 的路線裁定後一併產出並凍結，避免分兩次凍結造成不一致。
