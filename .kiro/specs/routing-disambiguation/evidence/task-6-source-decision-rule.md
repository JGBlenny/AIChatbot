# 任務 6：holdout 來源決策規則（**於查證 production 之前凍結**）

> 2026-08-24｜語言 zh-TW｜_Requirements: 9.2, 9.3_
> **凍結時點：先於 production 查證**——避免看到資料形狀後再挑對 candidate 有利的來源。

## 已封死的來源

| | 來源 | 裁定 | 理由 |
|---|---|---|---|
| S3 assistant-reports | 37 份 | **CLOSED** | 37/37 已參與 KB／routing 修正／回測語料建構（見 source-provenance-audit）|
| A | 等新回報累積 | **不採** | 26 天零新增，無法給出可執行完成時間；spec 已走到 candidate 生死裁決，不懸置 |
| B | 既有 corpus 未參與分區 | **不採** | **KB row ≠ user utterance**；由 KB wording 改寫問句＝另一種 authored-from-source 污染，
且 candidate 本身就是 lexical ruleset，更不適用 |

## C 的合格條件（兩層都要過）

```text
① 存在性：production chat_history／conversation_logs 有原文且有時間範圍
② contamination audit 後，clean pool 仍能形成 **≥30 個可判定 unseen utterances**
```

排除條件（任一命中即不得進池）：曾進 assistant reports／KB 建構／migrations／
regression 或 backtest corpus／research.md 或 ruleset 建構。

**去識別化限制**：只得替換帳號、姓名、電話、實際編號等**值**；
**SHALL NOT 改寫語句結構**——改了就污染本案真正要測的 lexical variation。

**抽樣須先凍結，不得看到 utterance 後人工挑**：

```text
freeze eligible time window → freeze sampling rule／seed → 抽樣
→ 盲標 judgeability ＋ intended class
→ 不可判定者排出 accuracy 分母
→ 可判定 <30 時，**依原抽樣規則補抽**（不得改規則、不得手挑）
```

⚠️ 人工挑「這句像 instance、那句像 rule」會讓 holdout 變成
**curator-designed challenge set**，而非真實分布的未見樣本。

## C → D 的 fallback（**現在就寫死**）

```text
C 兩層任一不過 → 正式記錄 "C unavailable" → 立即走 D，不回頭考慮 A／B
```

## D：隔離作者流程

**隔離是契約，不是宣稱。** 作者**不得**取得：

```text
instance_evidence.py／ruleset patterns／research.md／protocol v1 與 P3 變體／
candidate 任何輸出／現行 route／KB wording／assistant-report 原始案例
```

作者**只**取得：

```text
① 產品功能／業務場景描述
② 要產生的 domain／intent 類型（如帳單領域）
③ 每類需要多少自然使用者說法
④ 不得複製既有例句的要求
```

⚠️ **SHALL NOT 告訴作者 candidate 的失敗模式**（例如「現行 regex 抓不到『計算方式是什麼』」）——
一講，作者就會反向針對 ruleset 造測資，那也不再是 holdout。

**已失格的作者（不得擔任）**：

```text
本 session（我）：ruleset 由我撰寫，我寫就不是隔離
業主：本對話中已看過 P3 失敗模式與整套 candidate 行為
```

**作者與標註者最好再分離**：

```text
Author   → 只產 unseen utterances，不知 candidate
Labeler  → 看 utterance ＋ 產品規則，不看 candidate verdict
→ freeze labels ＋ dataset digest → candidate 最後才看見資料
```

若僅能有一個隔離 session 同時撰寫與標註，**仍可接受，但 SHALL 記錄證據強度較低**。

## 流程

```text
6.1 查 C 存在性（只查 count／時間範圍，不讀內容）
    ├ 有資料 → contamination audit → clean pool ≥30 → 走 C
    └ 無資料／不足 → 記錄 C unavailable → 走 D
6.2 產生／取得 unseen utterances
6.3 盲標 → freeze labels ＋ dataset digest（commit）
6.4 candidate **首次**執行
6.5 PASS ／ REFUTED
```

⚠️ **這批 holdout 一經 candidate 執行即燒毀**：FAIL 後可用它研究失敗原因，
但**修改 regex 後不得再用同一批證明泛化**，須另取真正未見的新批。
