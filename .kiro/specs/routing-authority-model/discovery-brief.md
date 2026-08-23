# Discovery Brief：routing-authority-model

> 2026-08-24｜語言 zh-TW｜**phase: discovery**
> 前案：[routing-disambiguation](../routing-disambiguation/tasks.md)　**REFUTED — CLOSED**（`91c589a`）
> 解剖：[post-mortem-01](../routing-disambiguation/post-mortem-01-refuted-candidate.md)（`8747c57`／`5fbbec2`）

## 核心問題（唯一）

> **當 Knowledge retrieval 提出 Face Routing Hint 時，
> 系統應由什麼 authority 判斷該 Hint 是否真的適用於這個 query？**

⚠️ 本案**高於** v1 一層：不是再問「怎麼分 rule／instance」，
而是問「**誰有資格讓一個 Routing Hint 生效**」。

## 已證實前提（accepted premises，**不重做**）

```text
P1  content evidence ＋ Routing Hint 共居具有 144+ exposure surface
P2  misrouting 已跨 8 Faces／3 families（帳務 7／合約 2／物件 1）
P3  signal coverage（A）與 routing authority（B）是可分離問題
P4  單修 A 不足（#11／#30：signal 判對，authority 不及）
P5  單修 B 不足（#8／#43：authority 完備，signal 缺席）
P6  lexical query-side candidate 已被 unseen holdout REFUTED（routing effect 0/50）
P7  另一個 similarity-based routing representation **不構成新 authority**
    （否則即 3.4 anchor 問題換皮）
```

⚠️ **不得**在 discovery 重新論證 P1–P7；要挑戰它們須直接引用 v1 證據並提出反證。

## 三組固定研究探針（任何新架構都要能解釋，而非只讓原四筆 regression 轉綠）

| 探針 | 案例 | 形態 |
|---|---|---|
| **T-1** | #11 已經發給房客的帳單還能改金額嗎／#30 押金退還也需要開一張帳單嗎 | **signal 正確 ＋ authority 不足**（判 block，落點 Face 在 scope 外）|
| **T-2** | #8 點退完之後的費用是系統幫我算…／#43 這個月總共收了多少，哪裡看得到 | **authority 足夠 ＋ signal 不足**（落點在 Level A 內，abstain）|
| **T-3** | #4 刷卡繳的話手續費是誰要吸收 | **signal 本身錯誤**（`卡` 命中「刷**卡**」，字面規則無詞義邊界）|

## Discovery 要回答的三題

**Q1｜Routing Hint 現在到底擁有多少 authority？**
把 production 真實 authority chain 畫清楚：
`retrieval top-1 → categories → config_for_category → Face entry`，
逐節點記錄「誰在此決定 Hint 生效與否、依據什麼、可否被否決」。

**Q2｜有哪些既有 first-class signal 可以成為 authority source？**
判準**不是**「訊號準不準」，而是**它有無獨立於 answer similarity 的語義來源**。
候選面向：intent／action 表示、Face contract、execution semantics、session state。

**Q3｜H1／H2／H3 哪些是必要條件、哪些只是伴隨症狀？**
每個結論**須附 falsifier**；**允許最後仍然沒有 winner**（v1 的 gap 階段已證明
「no winner」是合法且有價值的結論）。

```text
H1  KB Hint overloading           → routing authority 不應來自 answer-evidence row
H2  缺 first-class query semantics → routing 缺的是 query intent／operation representation
H3  Face applicability contract 不完整 → Face 沒有足夠契約判定哪些 query 可進
```

## ⛔ discovery 階段明確不做

```text
❌ 新 regex                              ❌ 新 anchor
❌ 擴 Level-A allowlist                  ❌ 把 categories 搬到另一張表就宣稱解耦
❌ 重啟 intent classifier 就宣稱 H2 成立   ❌ 新增 applicability prompt 就宣稱 H3 成立
```

以上皆為 **implementation candidate**，不是 **authority discovery**。
⚠️ 提出任一者之前，必須先回答 Q1／Q2——否則只是換一個地方重跑 v1。

## 承接自 v1 的紀律（不重述細節，僅列指標）

- 量尺先凍結、看過結果不得改尺（Req.3.5 形態）
- holdout 一經 candidate 接觸即燒毀；v1 那 50 句**已 BURNED**，不得再用於證明泛化
- 隔離作者／盲標為契約而非宣稱（v1 D1／D2 皆 `tool_uses=0`）
- **provenance ≠ justification**：現行 route／metadata／migration 只解釋「今天為何如此」
- 結論分級：CONFIRMED／SUPPORTED HYPOTHESIS／INSUFFICIENT EVIDENCE
