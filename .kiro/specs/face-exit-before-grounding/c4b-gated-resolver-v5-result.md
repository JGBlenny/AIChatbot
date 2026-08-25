# v5：**全段跑通，機器判紅落在我選的字面上**——ruler_false_red 候選

> 2026-08-25｜協議 `c4b-gated-resolver-validation-v5-protocol-frozen.md`（`0925294`，先於執行 commit）
> evidence：`evidence/c4b-gated-resolver-v5.json` ＋ `…-stdout.log`
> 預算：`target_scope_calls = 12`（上限 30）／`all_provider_calls = 15`（上限 60）／retry 0
> ⚠️ v1–v4 與舊 C4b 紀錄**皆未回填**；**尺未改**。

## 0. 逐項（3/3 完全一致）

```text
① chain     ✅ bill_diagnosis →(billing_anomaly)→ billing_anomaly →(contract_closeout)→ stay
               兩跳 attribution 皆 **kept**
② session   ✅ 只 commit contract_closeout，form_sessions 僅一列
③ grounding ✅ **收斂單筆**——contracts 遷入 transport 後，第二次依識別重查真的過濾到 678
④ answer    ⚠️ 機器判 `value_not_used`：我列的 `25,000|25000`（rent）不在答案中
⑤ verdict   ✅ 三跳 fail_open 皆 false
```

## 1. 但答案**確實**使用了該筆 fixture 的值

三次回答（節錄，逐字）：

```text
編號｜信義區套房A
合約「信義區套房A」目前狀態為「已點交（執行中）」。目前尚不可點退，因為合約不在可點退的階段；
合約到期日為 2026/12/31，需到期前 30 天（2026/12/01）起才可發送點退。
```

對照 fixture（id 678）：

```text
title                      信義區套房A        → 三次皆命中（matched_spans 記錄兩處）
date_end                   20261231           → 「2026/12/31」
early_termination_days     30                 → 「到期前 30 天」與推得的「2026/12/01」
bit_status                 47                 → 「已點交（執行中）」的狀態語義
rent                       25000.00           → **答案未提及**（本面向的 facts 不談租金）
```

⇒ **grounding 有被使用**；沒被使用的是「我在尺裡挑的那個字面」。

## 2. 歸因：ruler literal selection defect（**不是**系統缺陷）

`contract_closeout` 的 formatter facts 談的是**可否點退／解約時程／封存**，
本來就不會渲染 `rent`。我在 v4 建尺時把 `rent` 當必要字面，是**選錯了**——
違反 C4b v2 尺自己的原則：`answer_must_contain` 應是「回答該問句所必需的值」。

依 C4b v2 amendment 的失敗分類，這屬 **`ruler_false_red`**：

```text
machine verdict   value_not_used（原樣保留，不修改）
待人工裁決         accepted / ruler_false_red？
```

⚠️ 依 v5 協議與既有紀律，**我未改尺、未重跑**——
「改尺救綠」正是這條線一路防的事。

## 3. 這一輪確定成立的事

```text
✅ contracts 遷入 transport 後，「第二次依識別重查 → 收斂單筆」**可被實測**
   （v4 時恆回 2 筆、永遠列候選；v5 三次都收斂）
✅ 完整鏈路 delegation → commit → execution → grounding **全段跑通**
✅ 最終答案由該筆 fixture 的欄位組成（title／date_end／early_termination_days／bit_status）
```

## 4. 待裁示（互斥）

```text
(A) 裁為 ruler_false_red → 承認 vertical slice 實質成立，並**另立**一版修正過的尺
    （把 must_contain 換成本面向 facts 真正會渲染的值，如 date_end／狀態語義），
    再跑一次確認——**新尺要先凍結**。
(B) 維持機器判定 NOT_VALIDATED，不再花錢；把「答案確實使用 fixture 值」記為觀察，
    等 governance 決定後再一起處理。
(C) 認為選錯字面即測試設計失敗，要求重做整個 case 設計（包含 query 與目標面向）。
```

⚠️ 我建議 (A)，但**不自行執行**：修尺再跑必須先凍結新尺，且舊紀錄不得回填。
