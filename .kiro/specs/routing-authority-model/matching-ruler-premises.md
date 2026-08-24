# Matching ruler：推導前提凍結（**在觀測 score distribution 之前**）

> 2026-08-24｜語言 zh-TW｜依 M3：**六項前提先凍結，才准研究分佈**
> ⚠️ 本檔 commit 時，**尚未執行任何 score 觀測**。

## 本步驟的輸出邊界（業主 2026-08-24 鎖定）

```text
允許輸出：source population 定義｜score field｜descriptive statistics
          ｜matching statistic｜frozen algorithm 的計算結果｜最終 tolerance／matching rule

禁止輸出：哪些 utterance 看起來適合配對｜applicability label
          ｜opposite pair 候選｜candidate／member output
          ｜**為了湊 minimum pair count 而試 tolerance**
```

> **本步驟只回答**：在**不知道語義答案**的前提下，
> 什麼樣的 score proximity 可事前定義為「retrieval evidence 足夠接近」？
> **不回答**：哪幾筆剛好能構成我們想要的 challenge pair。

---

## 六項凍結前提

### ① source population

```text
既有**已凍結** artifact 中的 utterance 全集：
  v1 holdout utterances                       50  （BURNED，此處僅作 diagnostic：**只取分數，不取 labels**）
  protocol v1 case sets（RULE4/INSTANCE4/CONTROL5/BLAST7/UNDECIDED2）  22
  ────────────────────────────────────────────
  合計 72（去重後以實際為準）
```

⚠️ **不得**為本步驟產生任何新 utterance。
⚠️ 使用 v1 burned holdout **僅取 similarity 數值**，不觸及其 labels——label-blind 成立。

### ② score field

```text
`similarity`（production `retrieve_knowledge_hybrid` 回傳之 final score；0.1×向量 ＋ 0.9×rerank）
檢索條件沿用已凍結者：top_k=5｜kb_threshold｜target_user=property_manager｜mode=b2b
前處理：`_drop_empty_answer_rows`（複刻 production 執行順序）
```

### ③ matching statistic

```text
per-utterance adjacency gap  g = |similarity(rank1) − similarity(rank2)|
  （僅計後處理後仍有 ≥2 列者；不足 2 列者不計入）
```

**理由**：`g` 是系統**自身例行的候選鄰接差**。
若兩筆的分數差小於系統慣常的鄰接差，即可稱其 retrieval evidence
「與系統自己分不開的程度相當」——此定義**不需要任何語義標註**。

### ④ tolerance derivation algorithm（**單一、事前指定，無備選**）

```text
tolerance = median(g)          ← 固定取**中位數**（50th percentile）
```

⚠️ **刻意只指定一個統計量**：不設「若不夠再改用 P75」之類的備選路徑——
備選本身就是 M3 要封的後門。

### ⑤ minimum required pair count

```text
Experiment B 的最低可判定 opposite-label pair 數 = **20**
```

⚠️ 此數字**在任何 yield 未知之前**選定。依據：
低於此量無法支撐「穩定 discrimination」之主張（v1 holdout 的 ≥30 為統計效力門檻，
本 challenge set 為刻意構造之難例，故取較低但仍非個位數之 20）。

### ⑥ insufficient-pair consequence

```text
依 frozen rule 實配 < 20 → **INSUFFICIENT_EVIDENCE**
SHALL NOT 放寬 tolerance、SHALL NOT 更換統計量、SHALL NOT 擴大 population 去湊數
```

---

## 推導階段的盲性（M3）

**SHALL NOT 看見**：

```text
applicability labels ｜ candidate／member outputs
哪個 tolerance 會讓某 family 比較好看 ｜ **實際配出的 opposite-pair 數**
```

⚠️ 執行順序：**先算 tolerance 並 freeze，才准知道它能配出幾組。**

## 時序（業主確認保持）

```text
matching ruler **可以先於** concrete member freeze（它是 member-independent 的量尺）
但 challenge cases 在**揭露給作者之前**，member 必須已 freeze
⚠️ 不得為求形式整齊把兩者混成「所有東西必須同時 freeze」
```
