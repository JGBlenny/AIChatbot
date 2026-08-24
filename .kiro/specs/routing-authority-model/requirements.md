# 需求規格：routing-authority-model（第一批）

> 2026-08-24｜語言 zh-TW｜依據：[discovery-summary.md](./discovery-summary.md)
> ⚠️ 本批**先回答問題，不指定元件**——不出現「用 LLM／用 intent classifier／用某張表」。
> ⚠️ 每條標 **provenance 等級**，避免 NECESSARY 與 SUPPORTED 被混為一談。

## R1（provenance：**N1 NECESSARY**）

> **WHEN** 一個 Face entry 由 **retrieval-derived Hint** 造成，
> **THEN** 系統 SHALL NOT 僅以 **answer similarity ＋ category** 作為 applicability authority。

- 1.1 判別資訊 SHALL 包含**不等價於**檢索相似度與分類字串的新增資訊。
- 1.2 ⚠️ 「把同一段 routing metadata 搬到另一張表後再做一次 similarity」
  **SHALL NOT** 視為滿足本條（P7；前案 3.4 anchor 已實測 REFUTED）。
- 1.3 本條**不指定**取得該資訊的機制。

**反證條件**：出現一個僅用 similarity＋category 即可穩定分離 rule／instance 的實測方案。

## R2（provenance：**N2 NECESSARY**）

> **WHEN** 系統已取得「此 query 不適用於候選 entry」的有效 evidence，
> **THEN** 該 evidence SHALL 在 entry 成為 **irreversible／early-return** 之前具有明確 consumer。

- 2.1 evidence **SHALL NOT** 只是旁路資訊（產生了但無人消費）。
- 2.2 ⚠️ 本條**不要求**所有 Face 共用同一個 gate，只要求
  **對欲治理的 entry source，該判斷真的有權改變 routing outcome**。

**反證條件**：出現「evidence 正確、無消費者，但 routing 結果仍正確」的實測案例。
**既有反例**（支持本條）：v1 holdout `#11`／`#30`。

## R3（provenance：**SUPPORTED**——由 Q1 矩陣導出，非 necessary）

> authority source SHALL 可追溯：**誰提出 candidate、誰提供 applicability evidence、
> 誰有最終 enter／reject 權限**，三者要能區分。

- 3.1 現況五路 entry 的 authority source 各異且**無共同契約**（Q1 矩陣），故本條為架構要求。
- 3.2 ⚠️ 尚無「因不可追溯而導致 failure」的實測反例——**故不得標為 NECESSARY**。

## R4（provenance：**CONFIRMED institutional failure**）

> 系統 **SHALL NOT** 以人工維護規約（如「補 categories 時記得一起考量」）
> 作為 correctness invariant；**可機器判定的 routing invariant SHALL 有 executable enforcement。**

- 4.1 **counterexample 已存在**：該警告逐字寫在 `_top1_relevance_gate` docstring，
  而 20260731 補掛面向分類正是它警告的動作，結果為 3 筆實測 REGRESSION。
- 4.2 ⚠️ 本條治的是**流程約束無 enforcement**，不是「categories 不該存在」。

## R5（provenance：**SUPPORTED architecture requirement，非已證實 necessary invariant**）

> 不同 entry source **MAY** 使用不同 evidence；
> **SHALL NOT** 要求單一 query classifier 人為覆蓋
> session／caller assertion／vision 等不同 authority semantics。

- 5.1 ⚠️ **標記等級不得升寫**：目前僅為 coverage gap，
  **無** trigger／vision／session 的實測 misrouting counterexample（N3 降級理由）。
- 5.2 升格條件：出現該三路任一的實測 misrouting。
- 5.3 ⚠️ **共同 authority contract ≠ 共同 classifier**——可統一授權格式與責任，
  不得預設五種 entry source 共享同一種 evidence。

---

## 明確不在本批回答

```text
L2／L3／L4／L6 何者為主責任層          （INSUFFICIENT EVIDENCE，discovery 未改變此判定）
H1／H2／H3 是否有單一 root-cause winner （同上）
routing false-reject 的可接受代價        （產品裁示，尚未進行）
```

⚠️ **本批不進 design**：R1／R2 是**契約下限**，滿足方式有多種，
目前**沒有證據支持選定其中任何一種**。
