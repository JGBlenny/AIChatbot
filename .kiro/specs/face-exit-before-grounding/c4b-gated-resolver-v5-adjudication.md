# v5 人工裁決：`ruler_false_red` — vertical slice **實質成立**

> 2026-08-25｜裁決人：**業主**｜對象：`c4b-gated-resolver-v5-result.md`（machine verdict）
> ⚠️ **裁決與機器判定分開存放，machine verdict 永久保留、不被本檔覆寫。**

## 0. 兩層並存的結論

```text
v5 machine verdict     = NOT_VALIDATED ／ value_not_used   ← **永久保留**
v5 human adjudication  = ruler_false_red
                       = substantive vertical slice **ACCEPTED**
```

⚠️ **SHALL NOT** 表述為 `v5 machine PASS`——它沒有通過機器尺。

## 1. 裁決依據

最終答案明確使用了**同一筆 fixture 678** 的多個 grounding facts：

```text
title                   → 信義區套房A
date_end                → 2026/12/31
early_termination_days  → 到期前 30 天 ／ 2026/12/01
bit_status              → 已點交（執行中）
```

而 `rent` **不是**這個 `contract_closeout` 問句需要回答的事實，
也不是 formatter 對該 action 的正常輸出。把它列入 `answer_must_contain`，
違反本線既有的 ruler 原則：

> must-contain 必須是**回答該問句所必要、且該 execution contract 應產生的 grounding value**。

⇒ 這不是「答案沒用 grounding」，而是**尺要求了一個不屬於答案責任的 fixture literal**。

## 2. 分層宣告（本 case 上）

```text
structured delegation output contract              VALIDATED
pre-commit responsibility resolver                 VALIDATED（on this causal path）
bill_diagnosis → billing_anomaly → contract_closeout  VALIDATED
transient-session avoidance                        VALIDATED
contract filtering through JGBMockTransport        VALIDATED
single-row grounding                               VALIDATED
grounding-to-final-answer substantive use          ACCEPTED（after ruler_false_red adjudication）
```

⇒ 整條 **delegation → execution → grounding → grounded final answer**
判為 **substantively validated on this case**。

## 3. provenance（裁決所依賴的完整鏈）

```text
唯一 committed session   → contract_closeout（form_sessions 僅一列）
JGB request             → 依識別過濾至 fixture 678
grounding               → single row 678
final answer            → 含多個 678-specific facts（見 §1）
三跳 fail_open           → 全 false（真模型判定）
```

## 4. 修正後的機器尺：**只能是 post-hoc regression ruler**

若日後建立 v6：

```text
⚠️ 此 ruler 在 **v5 output 已被觀察之後**建立，
   故 **SHALL NOT** 作為 v5 的獨立驗證，
   **SHALL NOT** 消除或改寫原 `value_not_used`；
   僅作未來 **regression guard**。
```

且其 `answer_must_contain` **不得**照 v5 文案抄，
應自 **query obligation ＋ formatter contract ＋ fixture** 事前推導，例如：

```text
instance identity      信義區套房A（若前段已另證 identity，可不要求答案重複）
eligibility／現況證據   已點交（執行中）或對應之 authoritative status semantics
timing 證據            2026/12/31 ／ 2026/12/01 ／ 到期前 30 天
```

具體用哪幾組 OR／AND，須由 formatter／domain contract 推導後**先凍結**。

## 5. 未採用的兩個選項與理由

```text
(B) 維持 NOT_VALIDATED 不再處理  → 低估已取得的 evidence：provenance 已完整釘住（見 §3）
(C) 判 case 設計失敗、整案重做    → case 本身沒有失敗——它依序暴露了 entry nomination／
    delegation output contract／contracts mock seam／ruler literal selection 四層問題，
    且修完前三層後 production path 已真的走到正確 Face、正確 fixture、正確 grounded answer
```

## 6. 本檔**未**改變的事

```text
❌ 未改 v5 evidence 或 machine verdict     ❌ 未改任何 ruler
❌ 未重跑                                  ❌ 未動 production（gate 仍 false、DB 無 delegates）
❌ 不代表 diag-01 已修好／routing 已正確／可開 production gate／其他 Face 亦然
```
