# 6.1：C4b 斷言量尺（**FROZEN**）

> 2026-08-25｜語言 zh-TW｜**零 OpenAI 成本產生**（未跑 6.2，未呼叫 OpenAI）。
> 量尺實作：`tests/support/brain_grounding.py`
> 量尺自驗：`tests/unit/api/test_brain_grounding_assertion_req.py`（**17 passed**，本次實跑）
> 前置：`c4b-entry-path-equivalence-resolved.md`（供裝前置已解除）

## 這把尺量什麼、不量什麼

```text
C4a  chain_closure.py     斷言 grounding；**禁止**碰回答文字（腳本化 brain 的輸出是測試自己寫的）
C4b  brain_grounding.py   斷言**回答文字**；grounding 已送達由 C4a 證明
```

兩個維度（任務 6.1 明訂，**只有**這兩個）：

```text
answer_must_contain        該筆實際值字面是否出現（每組＝同一值的可接受寫法，任一命中即可）
answer_must_not_contain    是否引用到**別筆**（別筆 fixture 的字面）
generic_fallback_markers   是否**退回泛用 KB 答案**（推託／泛論／要求再給已給過的識別）
```

⚠️ **不鎖措辭**是硬約束，不是善意提醒：量尺對字面長度（≤16 字）與句讀設了結構性拒絕，
寫成句子的斷言**進不了**這把尺。

## 四條結構性禁令（拋例外，已具名測試）

| # | 禁令 | 例外類別 |
|---|---|---|
| 1 | `answer_must_contain` 為空 | `GroundingUseNotAssertedError` |
| 2 | 待驗字面出現在**凍結的使用者輸入**中 | `LiteralFedByTestError` |
| 3 | 字面過長（>16）或含句讀 | `WordingLockError` |
| 4 | `generic_fallback_markers` 為空 | `FallbackNotAssertedError` |

⚠️ 禁令 2 就是任務 6.3 🔍V 理由（「需獨立確認引用字面不是測試自己餵進去的」）的**機制落點**：
帳單編號由使用者輸入提供，故 **`900001`／`900002`／`900003` 一律不得列入 `answer_must_contain`**。

## 案例集：**沿用 C4a 的四案，一字未改**

```text
來源  c4a-case-set-frozen.md（FROZEN 451c0d2）——同 query、同 fixture、同 execution_face
理由  C4a 證「grounding 送達」、C4b 證「brain 使用」，兩者問的是**同一組案例的兩層**；
      換案例會讓兩層證據無法對齊，且需重跑一次 admission
```

⚠️ 兩輪輸入形狀（與 C4a 腳本化 brain 的 turn 結構相同）：
第 1 輪＝原 query（**不含數字**）→ 真 `conversational_step` 追問；
第 2 輪＝該案 `fixture_bill_id` → 決定性填槽 → API grounding → 收斂（真合成 LLM）。

---

## 逐案定尺

### `c4b-diag-01`（`bill_diagnosis`／fixture 900003）

```text
user_turns              「幫我查點退帳單金額」／「900003」
answer_must_contain     ("7,500", "7500")                       ← 900003.total
answer_must_not_contain "18,000" "18000" "1,200" "1200"          ← 900001／900002 的 total
generic_fallback_markers 見下方共同清單
discriminating?         ✅ 三筆 total 互異
```

### `c4b-diag-02`（`bill_diagnosis`／fixture 900001）

```text
user_turns              「這張帳單現在還能不能收回」／「900001」
answer_must_contain     ("待繳費",)            ← 900001.status=2 之權威標籤
                        ("2026年8月租金",)      ← 900001.title（實例辨識）
answer_must_not_contain "待對帳" "已繳費"                       ← 別筆狀態
                        "無法收回" "不能收回" "不可收回" "已失效"  ← 反向判定
discriminating?         ✅ 狀態與標題皆三筆互異
```

⚠️ **本案的已知量尺侷限（不得事後改尺補救）**：
`answer_must_contain` 鎖的是 `canCancel()` 的**輸入值**（狀態），不是判定本身；
判定方向由 `answer_must_not_contain` 的**列舉式**反向字面把關，**非窮舉**。
若真 LLM 用未列舉的說法否定，本案會**假綠**——這是已登記的 ceiling，6.3 報告必須原樣帶出。

### `c4b-anom-01`（`billing_anomaly`／fixture 900002）

```text
user_turns              「這張帳單的計費期間是哪一段」／「900002」
answer_must_contain     ("2026/09/01", "2026年9月1日", "20260901")    ← 900002.date_start
                        ("2026/09/30", "2026年9月30日", "20260930")   ← 900002.date_end
                        ("管理費",)                                   ← 900002.title 的辨識片段
answer_must_not_contain "2026/08/01" "20260801" "2026年8月租金" "點退結算"
discriminating?         ⚠️ **期間兩值無法辨識實例**——900003 的期間與 900002 完全相同。
                        辨識力由第三組（`管理費`）提供，且**必須列入** `known_non_discriminating`。
```

⚠️ 承 5.2 的 **OB-1**：兩個底層來源值（`date_start`／`date_end`）**各自**都要命中，
不得以「出現某種期間字串」代過（OB-2 的假綠正是這一型）。本尺以**兩個獨立字面組**落實。

### `c4b-anom-02`（`billing_anomaly`／fixture 900003）

```text
user_turns              「這張帳單現在的狀態是什麼」／「900003」
answer_must_contain     ("待對帳",)              ← 900003.status=8 之權威標籤
                        ("點退結算",)            ← 900003.title 的辨識片段
answer_must_not_contain "待繳費" "已繳費" "待發送" "排定發送" "已失效"
                        "2026年8月租金" "管理費"
discriminating?         ✅
```

⚠️ **已登記的假紅風險**：若回答寫成「是待對帳，不是待繳費」，會撞上 `待繳費` 這條反向字面。
**處置事前定死**：此種紅**歸入失敗分類 `ruler_false_red`**（見凍結參數檔），
由 6.3 人工裁決，**不得**當場改尺救綠。

---

## 共同 `generic_fallback_markers`（四案一致）

```text
"請洽客服"  "請聯繫客服"  "聯繫客服"  "一般來說"  "通常來說"
"無法查詢"  "查詢不到"    "請提供帳單編號"        "NO_MATCH"
```

理由：這些是**未落地**的標記（推託、泛論、要求再給已給過的識別、`kb_search` 未命中哨符
`services/llm_answer_optimizer.NO_MATCH_SENTINEL`），
**不是**「正確回答的措辭」——禁止它們不會限制正確答案怎麼寫。

⚠️ `NO_MATCH` 對這兩個面向**理論上不可能出現**（診斷面向不掛 `kb_search` 工具，
見 `c4b-entry-path-equivalence-resolved.md`）；保留它是**成本為零的反向哨兵**——
若它真的出現，代表工具注入條件被改動，那本身就是必須知道的事。

## 期望值的來源：**一律自 frozen fixture 取，不得手抄**

```text
金額   f"{fixture['total']:,.0f}"  與 f"{fixture['total']:.0f}"
日期   由 fixture 的 YYYYMMDD 整數推導三種寫法
狀態   services/jgb/bills.STATUS_LABELS[fixture['status']]
標題   fixture['title']（辨識片段以標題子字串宣告）
```

⚠️ 這條同時**清掉 D-A4 的同型債**：C4a 的 diagnosis 側期望值為手抄常數；
C4b **不得**沿用該做法，否則會出現第二個 truth source。

## 本檔**未**做

```text
❌ 未執行 6.2（未呼叫 OpenAI）
❌ 未改 C4a 的案例、required facts、observation contract、fixture
❌ 未定 model／runs／budget／retry（屬凍結參數檔，另立一檔）
❌ 未對「答案品質」下任何斷言——本尺只問「有沒有用這筆的值」與「有沒有退回泛用答案」
```
