# Responsibility Authority Contract（設計層第一步：**先定語義，再比 carrier**）

> 2026-08-24｜語言 zh-TW｜業主裁定：封口 R-e discovery；下一步**不是**再掃 source、
> 也**不是**直接做 D1／D3 member，而是**先定義 first-class Responsibility Authority Contract**。
> 前置：`r6-derived-design-constraint.md`｜`re-mapping-discovery-result.md`（`63351cd`）

## 為何先定 contract，而不是先選 carrier

避免這個常見倒序：

```text
❌ 先新增 responsibility_registry → 再倒推它應該放什麼
✅ 先定「新 authority 必須是什麼」 → 再比較誰來承載
```

⚠️ 本檔**不選 carrier**、**不設計 schema**、**不開任何 member**。

---

## 1. Contract semantics

### Input

```text
- candidate Face                     （由 retrieval Hint／trigger／session 等來源提出者）
- qualified runtime proofs           （N1／N2／N3 類；已於 1f077f6 通過 E1–E6）
- 必要的 query-derived structured evidence（若有；本輪尚未證成任何一項）
```

### Output

```text
applicable ／ not_applicable ／ unknown
```

### E5 硬綁（**不因進入設計層而放寬**）

```text
proof 不足  →  unknown
proof 不足  ≠  not_applicable
```

⚠️ 這是本線連續三次 precision-first collapse 的唯一防線
（v1 大量 abstain／Q2 誤殺 44%／Round 1 過度拒絕 17 對過度放行 0）。
把 unknown 折成 not_applicable，等於用 API 版本再做一次同樣的失敗。

---

## 2. Admission gates（**R1–R5 在新發現下的具體化**）

| gate | 要求 | 對應既有 requirement／證據 |
|---|---|---|
| **G-a｜Face-specific** | 在**同一組 instance proof** 下，能真正區別候選 Face | 直接來自 semantic-role review：N1／N2／N3 皆 R-e ❌。⚠️ 分不開＝沒有 R-e |
| **G-b｜Runtime enforceable** | 結果**不是 advisory**；接上 seam 後 MUST 能**反事實改變** entry | R2（N2）＋ META-RULE：驗收不得只證元件存在 |
| **G-c｜Open-Face compatible** | 新增 Face **不要求**先封閉全世界 Face taxonomy | G1 FAIL 的直接教訓：Face 集合後台可增、零改程式 |
| **G-d｜No self-attestation** | Face **不得**僅因自己宣告「我負責」即成立 | 沿用 D3-member-1 已明訂的 self-attestation 禁令；B4（`grounding_scope` 宣告無 enforcement）即反例 |
| **G-e｜No similarity laundering** | **不得**把 similarity／category 換個名字塞進 authority | R1 §1.2（已實測 REFUTED）；B2 即現行違例形態 |
| **G-f｜Traceable** | **proof provider ／ responsibility authority ／ final routing authority** 三者可區分 | R3：三種責任（candidate proposal／applicability evidence／final enter-reject）必須可追溯 |

⚠️ **G-b 與 G-d 是一組**：只有宣告而無獨立 enforcer，兩條同時不過（B4 的形態）。
⚠️ **B5 證明這一組是做得到的**（宣告＋consumer 強制），但那是 feasibility precedent，**不是**方案。

---

## 3. Carrier shapes（**三種並列，不預選**）

| | shape | 形態 | 必須回答的同一題 |
|---|---|---|---|
| **A** | Central responsibility authority | 獨立 registry／policy source：`facts × candidate Face → applicability` | 它新增的 authority **來自哪裡**？ |
| **B** | Face-local declaration ＋ independent executable validation | Face 宣告自己接受哪些 proof semantics，但由**外部 consumer／enforcer** 驗證 | 同上 |
| **C** | Capability-bound authority | Face 與 machine-enforced capability／action binding；runtime facts 與 capability requirements **機械 join** | 同上 |

### 三者共同的**當場失敗條件**

```text
若「它新增的 authority 來自哪裡？」的答案仍是：
    「Face RULES 寫了這樣」
→ **直接失敗**（G-d ＋ G-e）
```

⚠️ 這條寫在比較之前，是為了讓比較有可能得出「三個都不合格」這個結果。

### 各 shape 目前已知的**待答問題**（不是評分，是尚未回答的事）

```text
A  authority 的內容由誰產生、由誰維護？若仍是人工填表 → G-b 的 enforcement 從哪來？
B  外部 enforcer 憑什麼判定「Face 宣告的 proof semantics」成立？
   （B4 已證明：只有宣告端、沒有強制端 → 不成立）
C  平台**沒有 Face 概念**（63351cd 實證）→ capability binding 的 Face 那一側從何而來？
   若答案是「在對話層另建一份對應」，那它就退化成 A 或 B
```

⚠️ 以上皆為**待答**，**不構成**對任一 shape 的淘汰或推薦。

---

## 4. D1／D3 的狀態再收斂一次

**不是**兩條獨立路徑各缺一半，而是**已收斂到同一個 missing authority**：

```text
D1   runtime demand facts ✅（N1／N2）      facet responsibility authority ❌
D3   runtime prerequisite facts ✅（N1／N2／N3）  facet responsibility authority ❌
```

> **因此此刻沒必要先決定「重開 D1 還是 D3」。**

先把 responsibility authority 定義出來，**再**看它的 provenance：

```text
routing-owned                       → 更像 D1
Face-owned but independently enforced → 更像 D3
neutral／capability-owned            → 可能讓 D1／D3 這個分類**本身失去重要性**
```

⚠️ 最後一種結果是允許的，且不該被視為失敗——它會說明我們一開始的 family 切法不是關鍵軸。

---

## 5. 本檔的界線

```text
✅ 只定 contract semantics ＋ admission gates ＋ 並列 carrier shapes
❌ 不選 carrier、不設計 schema、不主張新增某張表／某個 registry
❌ 不開 D1-member-2／D3-member-next／D4；D2 仍 deferred
❌ 不改 family disposition（D1／D3 皆維持 INSUFFICIENT_EVIDENCE）
❌ 不改已凍結的 R1–R5（R6 以 derived design constraint 獨立成檔）
❌ 不動 production；不產測資；ruler 0.058928 仍凍結未用
```

## 下一步（待業主裁定，**不預選**）

```text
① 逐條審這份 contract semantics 與 G-a～G-f
② 通過後才進 carrier 比較（A／B／C），且比較前應先凍結比較判準
   —— 與 G1 的教訓一致：判準要在看到候選之前定
```
