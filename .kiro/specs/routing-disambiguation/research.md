# 研究記錄：routing-disambiguation

> 建立時間：2026-08-23｜語言 zh-TW
> 目的：記錄 design 階段的技術調查、架構決策與相依性分析。
> ⚠️ **gap 階段的六層盤查與 disposition 見 [gap-analysis.md](./gap-analysis.md)**（APPROVED，no winner）。
> 本檔只記錄 **design 階段新增**的調查，不重述 gap 結論。

## 摘要

### 調查範圍
承接 gap 階段的核心結論——「問句是否指涉特定個體」目前沒有被 production 以
**可供 routing 穩定消費的第一級訊號**顯式表示。本階段調查：該訊號**能不能被
deterministic 地產生**、**由誰消費**、以及**現有哪些宣告可以複用**。

### 關鍵發現
- **deterministic 表層特徵在凍結案例集上完全可分**（dialog 11/11、誤判 0/9）
  ——但**這是看著案例集寫出來的規則**，20 筆遠低於 Req.9.3 的 ≥30，**不得當作已驗證的解法**。
- **`explain_ask` 是強力的反向標記**：8/9 single 案例命中、11 筆 dialog 僅 1 筆命中。
  判別可同時使用**正向（instance）與反向（explanation）證據**，而非只找正向特徵。
- **Face 側的「需要什麼個體識別」宣告已經存在**：`grounding_scope.required_slots`
  （`bill_diagnosis: ["bill_ref"]`）——缺的是**問句側**的對應表示，不是 Face 側。
- 前案已立但**從未落地**的原則「routing evidence ≠ answer evidence」正是本案的架構槓桿：
  現行進場只看 top-1，答案證據與路由證據綁在同一列。

---

## 研究主題

### 主題 1：deterministic 表層特徵的分離力

**調查問題**：`InstanceEvidence` 能否由**零 LLM、決定性**的規則產生？
（若不能，L1 就無法承擔訊號產生，須回到 L3／L4 的非決定性方案。）

**研究方法**：現有程式碼分析 ＋ 對 protocol v1 凍結案例集實測（零 LLM）。

**發現**（20 筆：RULE 4／INSTANCE 4／BLAST 7／CONTROL 5）：

| 特徵 | 命中 dialog | 誤判 single |
|---|---|---|
| `id_token`（2–15 位數字）| 1/11 | 0/9 |
| `possessive`（我的／我這／這張／這筆／這期）| 4/11 | 0/9 |
| `problem`（為什麼／怎麼會／怪怪的／失敗／不了／不出／卡）| 5/11 | 0/9 |
| `lookup_verb`（幫我查／查一下／多少錢）| 4/11 | 0/9 |
| **`explain_ask`**（怎麼算／是怎麼／在哪裡／有哪些／哪幾種／…嗎）| **1/11** | **8/9** ⬅ **反向標記** |
| **組合** `possessive ∨ id ∨ lookup ∨ problem` | **11/11** | **0/9** |

**結論與建議**：
訊號**可以**由 deterministic 規則產生——這解除了 L1 的最大疑慮（`SUPPORTED` 的
「覆蓋率待量」得到初步答案）。但：

> ⚠️ **本結果不得作為驗收證據。** 特徵集是**看著凍結案例集事後挑出**的，
> 20 筆樣本、規則與資料同源，屬定義上的 overfit。
> Req.9.3 要求比較性結論 ≥30 可判定案例，且 Req.3.5 的 protocol v1 明訂
> 擾動與門檻須先凍結——**本測量屬 design 探索，非 acceptance**。

**必要的後續**：特徵集 SHALL 於**未見過**的案例上驗證，且案例 SHALL 自
144 筆 exposure surface 抽樣（非只取帳單域），否則無法支持 Req.2.5 的範圍宣告。

---

### 主題 2：Face 側的宣告可否複用

**調查問題**：判別是否需要在 KB 新增 metadata（L2 的 schema 變更）？

**發現**：`grounding_scope` 已宣告 Face 需要什麼個體識別——
`bill_diagnosis`：`required_slots: ["bill_ref"]`、`search_params: [{bill_ref: "{form.bill_ref}"}]`。
**Face 側「我需要一個具體個體」的資訊已經是第一級的、契約化的、可程式讀取的。**

**結論與建議**：**缺口是單邊的**——問句側沒有對應表示。
故 L2 的必要性下降：**未必需要新 KB 欄位**，而是需要一個
「問句側 instance evidence」× 「Face 側 required_slots 宣告」的比對契約。
⚠️ 但這**不等於 L2 被否決**——`categories` 的雙重語義（144 筆共居）仍是獨立問題，
只是它屬**資料衛生**，未必是**判別機制**的必要前提（見 gap L6 的「不得寫成必要」）。

---

### 主題 3：現行進場只看 top-1 —— 架構槓桿

**現有程式碼分析**：
- `routers/chat.py:797` `_diagnosis_config_for_knowledge` 只取 `best_knowledge`（top-1）
- `services/decision_layer.py:191` `facet_entry_eligible(best_knowledge, config)` 同樣只看 top-1
- 進場分類來自 `_knowledge_category(best_knowledge)`——**路由證據＝答案證據＝同一列**

**發現**：前案已明文立下但**從未落地**的原則：

> **routing evidence ≠ answer evidence**——觸發面向的 KB 不應自動成為回答依據。
> （前案 research.md 主題 1「仍然成立的接縫原則」第 3 條）

現行實作把兩者**綁在同一列**，正是 144 筆共居問題在**程式側**的鏡像：
資料側「一列同時承載 evidence 與 hint」，程式側「同一列同時決定答案與路由」。

**結論與建議**：本案的架構槓桿是**把兩者拆開**——
routing decision 可消費 top-1 以外的訊號（query 側 evidence、候選集中的錨點、Face 宣告），
而 answer evidence 仍取 top-1。這與 L6 的資料側分離是**同一原則的兩面**。

---

## 技術選型

### 選型 1：`InstanceEvidence` 訊號的產生層與消費層

**候選方案**：

| 方案 | 產生 | 消費 | 優點 | 缺點 |
|---|---|---|---|---|
| **A. Deterministic evidence ＋ 決定性 gate** | L1 規則抽取（正向＋反向標記）| 進場 seam 比對 Face 的 `required_slots` | 零 LLM、**決定性**（直接滿足 Req.3.1 的「不由邊際決定」）、可單元測試 | 規則覆蓋率須以未見案例驗證；語言變體長尾 |
| **B. LLM applicability judge** | 沿用 `_preentry_routable` ＋ 新 prompt | 同左 | 覆蓋率高、不需維護規則 | **實測非決定性**（無擾動即翻面）；每次進場多一次 LLM；成本 |
| **C. Intent taxonomy 增維** | L3 新增 rule／instance 維度 | intent 階段分流 | 概念最乾淨 | 主路徑 Step 3 為 stub（~1.5s 復啟成本）；54 筆 intent 需重標；`api_required` 0/54 未供裝 |
| **D. A ＋ B 混合** | A 為主、B 於 A 判不出時 fallback | 同 A | 兼顧決定性與覆蓋率 | 兩套機制的一致性與可解釋性成本 |

**評估標準**：決定性（Req.3.1／3.4）＞ 可驗證性（Req.3.5 量尺）＞ 覆蓋率 ＞ 成本 ＞ 可維護性。

**傾向**：**方案 A 為主幹、D 為備案**。理由：Req.3 的核心要求是「判別不得由相似度邊際決定」，
而 B／C 各自有已實測的硬傷（B 非決定性；C 訊號未供裝且維度正交）。
⚠️ **本節為傾向，非定案**——design.md 的技術決策節才做選擇，且須通過 protocol v1。

---

## 現有程式碼分析

### 相關模式與慣例

| 位置 | 模式 |
|---|---|
| `services/conversational_engine.py:88,113,118,137,241` | 既有 deterministic 抽取：`_looks_like_identifier`、id-like token、`_parse_ordinal`——**本案要複用的正是這個慣例**，非新造 |
| `services/decision_layer.py:191` | `facet_entry_eligible` 為**決定性子決策**、門檻唯一讀值點——新 gate 應沿此形態放入決策中樞 |
| `routers/chat.py:737` | `_preentry_routable` 的 **fail-open** 慣例：gate 故障不阻斷既有行為 |
| `scripts/audit/check_invariants.sh` | 「修一類 bug ＝ 加一條不變量」＋ negative control（前案新增） |

**整合點**：新訊號應在 `_diagnosis_config_for_knowledge` 之前或之內產生，
並由 `decision_layer` 消費——**與現行門檻 gate 同層**，避免另建平行決策路徑
（前案 Req.6.7：pre-entry gate 實測 1/13 已證明沒有理由新造中央 selector）。

---

## 風險登記

| 風險 | 類型 | 影響 | 機率 | 緩解策略 | 狀態 |
|---|---|---|---|---|---|
| **特徵集 overfit 於 20 筆凍結案例** | 技術 | **高**——會重演 3.4「對著測試集調」的失敗 | **高** | 未見案例驗證 ＋ 自 144 exposure surface 抽 ≥30；protocol v1 已凍結，不得事後改尺 | 開放 |
| 規則對語言變體的長尾覆蓋不足 | 技術 | 中 | 高 | 反向標記（`explain_ask`）補強；必要時方案 D fallback | 開放 |
| 判別上移至進場＝新增全域 routing 訊號 | 技術／範圍 | 中 | 中 | 前案 Req.8 排除全域 heuristic；本案須在 Req.2.5 明示範圍並評估 | 開放 |
| 144 筆 exposure surface 的產品判定成本 | 時程 | 中 | 高 | 兩級 scope（Level A 帳單域／Level B 跨域），不強制一次做完 | 開放 |
| 新 gate 故障阻斷對話 | 技術 | 高 | 低 | 沿 `_preentry_routable` 的 fail-open 慣例 | 已緩解（設計約束）|

---

## 開放問題

### 問題 1：`explain_ask` 反向標記的角色
**描述**：反向標記在本案例集上比任一正向特徵更強（8/9 vs 最高 5/11）。
它應是 **veto**（命中即判 rule）、還是**加權證據**？
**影響範圍**：判別的決定性與可解釋性；veto 較決定性但誤殺風險高。
**可能解法**：A. veto／B. 正反證據皆須成立／C. 僅在正向證據缺席時生效。
**決策狀態**：待決定（design.md 技術決策節）。

### 問題 2：clarification（L5）的角色
**描述**：gap 階段 L5 為 `INSUFFICIENT_EVIDENCE`，**不得默默消失**。
**影響範圍**：訊號不足以安全判定時的處置。
**可能解法**：A. 作為 fallback（正反證據皆不明確時反問）／B. 不需要（fail-open 進 Face 後由既有反問處理）。
⚠️ 前案原則：**缺執行欄位 → 進 Face 後反問**是**正確處置**；
故 B 可能已足夠——「沒有 instance evidence 但主題相符」未必需要新的澄清機制。
**決策狀態**：待決定（design.md 須明確回答，不得略過）。

### 問題 3：Req.2.5 的適用範圍
**描述**：Level A（帳單域）vs Level B（跨 144 筆 exposure surface）。
**影響範圍**：驗證成本與結論可宣稱的強度。
**決策狀態**：待決定——取決於問題 1 的規則是否能在跨域案例上維持分離力。

---

## 時間軸

| 日期 | 活動 | 結果 | 後續行動 |
|---|---|---|---|
| 2026-08-23 | Req.3.5 量尺凍結 | protocol v1，digest `4690a258f502d98d` | 所有後續量測沿用 |
| 2026-08-23 | gap：六層盤查 ＋ L4／L3 實測 | no winner；L3-a／L4-a `REJECTED` | 帶兩個結構發現進 design |
| 2026-08-23 | design：deterministic 特徵分離力 | 20 筆全分（**overfit 警告**）；`explain_ask` 為反向標記 | 未見案例驗證為必要後續 |

---

*本文件持續更新，記錄設計階段的所有重要調查與決策過程。*
