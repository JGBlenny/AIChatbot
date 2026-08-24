# 需求規格：routing-authority-model（第一批）

> 2026-08-24｜語言 zh-TW｜依據：[discovery-summary.md](./discovery-summary.md)
> **狀態：已依業主 review 修文（R2／R3／R4 must-fix、R5 revise），待 approve**
> ⚠️ 本批**先回答問題，不指定元件**——不出現「用 LLM／用 intent classifier／用某張表」。
> ⚠️ 每條標 **provenance 等級**，NECESSARY 與 SUPPORTED 不得混寫。

## ⭐ META-RULE（適用於本批**每一條**需求的驗收）

> **任何 requirement 的驗收 SHALL NOT 只證明「元件存在」；
> MUST 證明其 stated authority 能在對應 routing decision 上產生
> **反事實可觀察的效果**（counterfactually observable effect）。**

v1 的最大教訓逐條對應：

```text
gate exists     ≠ gate can affect outcome     （v1：block 11 筆，實際 suppression 0）
signal exists   ≠ signal is authorized        （v1：manifest not_run → 恆不生效）
consumer exists ≠ veto actually works         （R2 must-fix 的由來）
```

⚠️ **故 EARS 展開時，每條驗收 SHALL 天然帶 negative control**（拿掉該 authority 即應觀察到不同結果）。

---

## R1（provenance：**N1 NECESSARY**）｜業主裁定：**APPROVE**

> **WHEN** 一個 Face entry 由 **retrieval-derived Hint** 造成，
> **THEN** 系統 SHALL NOT 僅以 **answer similarity ＋ category** 作為 applicability authority。

- 1.1 判別資訊 SHALL 包含**不等價於**檢索相似度與分類字串的**新增**資訊。
- 1.2 ⚠️ 「把 metadata 搬到另一張表，再以同一類 similarity 判斷」**不構成**新增 applicability information
  （P7；前案 3.4 anchor 已實測 REFUTED）。
- 1.3 本條**不指定**取得該資訊的機制。

**📌 EARS 展開時 SHALL 明確定義「新增」**（業主 review 指定，否則易被形式滿足）：

```text
new applicability information
  ≠ answer retrieval score 的重新包裝
  ≠ category membership 的重新編碼
  ≠ 同一 evidence 的另一個 threshold
```

**反證條件**：出現一個僅用 similarity＋category 即可穩定分離 rule／instance 的實測方案。

---

## R2（provenance：**N2 NECESSARY**）｜業主裁定：**APPROVE WITH MUST-FIX（已修）**

> **WHEN** routing contract 取得一項**被宣告為可否決該 entry 的有效（authorized）
> applicability evidence**，且其判定為「不適用」，
> **THEN** 該 evidence MUST 在 Face entry 成為 **irreversible／early-return 之前**
> 被明確 consumer 消費，且**其否決結果 MUST 能改變 routing outcome**。

- 2.1 ⚠️ **「已取得」不等於「有效」**：低可信度的純 observation signal **不因本條**
  自動取得否決權。本條治的是**被 contract 認可為可作用**的 evidence。
- 2.2 ⚠️ **明確排除的形式滿足**：

  ```text
  consumer 有讀 → 寫 log → 仍照樣 enter Face     ← 形式符合、實質違反 N2
  ```

- 2.3 本條**不要求**所有 Face 共用同一個 gate，只要求
  **對欲治理的 entry source，該判斷真的有權改變 routing outcome**。

**反證條件**：出現「authorized evidence 判否決、無 consumer，但 routing 結果仍正確」的實測案例。
**既有反例**（支持本條）：v1 holdout `#11`／`#30`——**判對了 block，routing 仍錯**。

---

## R3（provenance：**SUPPORTED**——由 Q1 矩陣導出，非 necessary）｜業主裁定：**APPROVE WITH MUST-FIX（已修）**

> **Routing authority contract MUST 明確區分三種責任：
> candidate proposal ／ applicability evidence ／ final enter-reject authority；
> 對一次 routing decision，三者的來源與最終決策關係 MUST 可追溯。**

- 3.1 ⚠️ **順序不可倒置**：先有**責任模型**，才談**可追溯**。
  ⚠️ 本條 **SHALL NOT** 被降級為 observability 需求
  （「多印三個 log 欄位」不滿足本條——那只是把責任模型的缺席記錄下來）。
- 3.2 現況五路 entry 的 authority source 各異且**無共同契約**（Q1 矩陣），故本條為架構要求。
- 3.3 ⚠️ 尚無「因不可追溯而導致 failure」的實測反例——
  **不得因其合理而升為 NECESSARY**。

---

## R4（provenance：**CONFIRMED institutional failure**）｜業主裁定：**APPROVE WITH MUST-FIX（已修）**

> **凡 routing correctness invariant 可由機器判定者，MUST 有 executable enforcement；
> 人工維護規約 MAY 作補充（defense-in-depth），
> 但 MUST NOT 作為**唯一** correctness enforcement。**

- 4.1 **counterexample 已存在，且形態完整**：

  ```text
  docstring warning existed        （「補標時須一併考量」逐字寫在 gate docstring）
  + human process rule existed
  + machine enforcement absent
  → regression occurred            （20260731 補掛面向分類 → 3 筆實測 REGRESSION）
  ```

- 4.2 ⚠️ 本條治的是**流程約束無 enforcement**，**不是**「categories 不該存在」，
  **也不是**全面禁止人工 review／checklist。

---

## R5（provenance：**SUPPORTED architecture requirement，非已證實 necessary invariant**）｜業主裁定：**REVISE（已改寫）**

> **Authority model MUST NOT assume all entry sources share the same evidence semantics,
> nor that query text alone is sufficient.
> Different entry sources MAY use different evidence providers and applicability rules.**

窄化陳述（由 Q1 直接支持）：

> **A query-only classifier MUST NOT be treated as sufficient authority for entry sources
> whose authority is derived from non-query evidence
> such as session state, caller assertion, or vision.**

- 5.1 ⚠️ **原稿「不得要求單一 classifier」已撤回**——那是**從 evidence 跳到 solution prohibition**。
  Q1 證明的是「不同 entry source 的 authority semantics 不同」，
  **未證明**任何形式的 single classifier 都不可能建模它們
  （例如輸入同時含 query／session state／caller assertion／image evidence／entry-source type 者，
  已非本條所指的 query-only classifier）。
- 5.2 ⚠️ **標記等級不得升寫**：目前僅為 coverage gap，
  **無** trigger／vision／session 的實測 misrouting counterexample（N3 降級理由）。
- 5.3 **升格條件**：出現該三路任一的實測 misrouting。
- 5.4 ⚠️ **共同 authority contract ≠ 共同 classifier**——可統一授權格式與責任，
  不得預設五種 entry source 共享同一種 evidence。

---

## 明確不在本批回答（**維持 unresolved**）

```text
L2／L3／L4／L6 何者為主責任層           INSUFFICIENT EVIDENCE
H1／H2／H3 是否有單一 root-cause winner  INSUFFICIENT EVIDENCE
routing false-reject 的可接受代價        **產品裁示，尚未進行**
```

⚠️ **第三項在進 design 前很可能成為真正的 dependency**：
Q2 已證明 direct-answer 的 precision-first loss function **不能自動繼承到 routing**
（誤殺代價：答題側＝一次誠實查無；routing 側＝本應取得 instance-specific capability 卻掉回通則回答）。

⚠️ **本批不進 design**：R1／R2 是**契約下限**，滿足方式有多種，
目前**沒有證據支持選定其中任何一種**；亦**不新增第六條 solution requirement**。
