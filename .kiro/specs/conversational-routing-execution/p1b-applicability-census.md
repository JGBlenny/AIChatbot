# P1b：instance applicability 全量 deterministic census（2026-08-29，**已凍結**）

- 母體：873 筆 active 情境知識（排除 `對話規則`／`系統脈絡`）
- 產出：`scripts/analysis/p1b_census.json`（逐筆）＋ `scripts/analysis/p1b_applicability_census.py`（可重播）
- ⛔ **未寫入任何 DB**——依業主定案「先產 census、凍結、再決定 population」

## 結果

```text
DETERMINISTIC_INSTANCE     34    3.9%
DETERMINISTIC_GENERAL       0    0.0%
CONFLICT                    0    0.0%
UNKNOWN                   839   96.1%
```

## ⚠️ 最重要的結構性發現：**證據是單向的**

```text
instance 側有 deterministic evidence source：
  E1_ENGINE_TITLE     知識標題 ＝ 診斷引擎 docstring（14 條，可追溯到 file::function）
  E2_IDENTIFIER_FORM  active 表單 → 使用者範圍讀取端點，且收識別欄位
  E3_ACTION_API       action_type=api_call／form_then_api → 使用者範圍端點

general 側 **不存在任何 deterministic evidence source**。
  要證明「這一題不依賴使用者資料」需要**正面**證據，
  而 repository 內沒有這樣的機器事實。
  ⛔ 「沒有 instance 跡象」**不是** general 的證據（同否定結論紀律）。
⇒ 96.1% UNKNOWN 不是掃描不力，是**結構性的**。
```

## `CONFLICT = 0` 的正確讀法

```text
⛔ 不得讀成「沒有衝突」。
   只有一個方向的證據源存在 ⇒ **在結構上不可能產生分歧**。
   等 general 側有證據源（例如標註）之後，CONFLICT 才會是有意義的量。
```

## 正對照組：census 有**已知的漏抓**

```text
✅ 3503／3504／3505／3506／3497／3490／3502／3508  皆被偵測
❌ 3509「訂閱扣款失敗導致功能異常」→ **UNKNOWN**
   ・引擎 docstring 是「S01：訂閱扣款失敗」，標題多了「導致功能異常」⇒ E1 不匹配
   ・direct_answer、無 form_id ⇒ E2／E3 皆不適用
   ・但它**確實**必須查該帳號訂閱狀態（本輪 runtime smoke 已實證）
⇒ 正對照組抓到了 census 自己的 false negative：
   **34 是下界，不是「instance 的總數」。**
```

## 證據源分布

```text
E2 單獨            25 筆
E1 ＋ E2            8 筆   ← E1 從未單獨命中：有引擎的都同時掛了表單
E3 單獨             1 筆
```

⇒ E1 目前的作用是**加強證據**而非擴大召回。它的價值在於可追溯性
（能指到 `services/jgb/invoices.py::_diagnose_issue_failure（I01）`）。

## 三條判準的遵守情形

```text
① 只允許 machine-supported disposition   ✅ 34 筆皆附可重播 evidence；不足者一律 UNKNOWN
② execution capability 只當 evidence     ✅ E2/E3 皆額外要求「端點屬使用者範圍」，
                                            ⛔ 未把「有表單」單獨當規則；
                                            3509 反證（無表單卻需實值）已寫進 P1a 測試
③ 先 census、凍結、再決定 population      ✅ 零 DB 寫入
```

## 這個結果如何決定下一步

```text
若要讓 applicability 真正有 coverage，**必須**取得 general 側證據，
而 general 側在 repository 內結構性缺席 ⇒ 只剩兩條路：

【A】isolated blind labeling（走 holdout-validation skill）
     ⚠️ 需要動用 Agent；本 session 未獲授權，⛔ 未執行
【B】把宣告變成**知識工程流程的一部分**（新增/編輯知識時必填）
     ⇒ coverage 隨時間長，存量仍需 A 或人工回填
```

⚠️ 但 **34 筆 DETERMINISTIC_INSTANCE 已經足以支撐 P1c**：
gate consumer 的 deterministic matrix 需要的是「有明示 instance 的 row」與
「明示 general 的 row」與「UNKNOWN 的 row」三種形狀——
前者已有真實樣本，後兩者可用 fixture 覆蓋語義，**不必等全量 population**。

## 本 census **不能**回答

```text
⛔ 839 筆 UNKNOWN 裡有多少其實是 instance —— 那正是漏抓的部分（3509 已證存在）
⛔ 任何 production 流量分布
```
