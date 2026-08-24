# Discovery Summary：routing-authority-model

> 2026-08-24｜語言 zh-TW｜**discovery 封口**
> 前案：[routing-disambiguation](../routing-disambiguation/tasks.md) `REFUTED — CLOSED`

## 核心問題（discovery 已回答到可進 requirements 的程度）

> **當 Knowledge retrieval 提出 Face Routing Hint 時，
> 系統應由什麼 authority 判斷該 Hint 是否真的適用於這個 query？**

---

## Q1 — 現行 authority topology：**CONFIRMED**

五種 Face entry source 使用**不同 authority standards**，其中**四種沒有 applicability veto**；
Knowledge direct-answer 雖有 veto，但 **Face Routing Hint 可在 veto 之前生效並 early-return**。

```text
session 續談   ← 既有 state        │ trigger_facet_key ← 呼叫端斷言
損傷圖改道     ← 圖片辨識           │ prospect         ← target_user 欄位
分類路由       ← KB similarity＋categories
唯一 veto：_top1_relevance_gate（LLM，b2b fail-closed）——**只掛答題路徑**
```

### ⚠️ 比「程式缺一個 gate」更重要的制度問題

> **bypass 並非未知行為**：`_top1_relevance_gate` 的 docstring 已明確警告
> 「替知識補 categories 等於把它移進一條繞過本閘門的路徑，補標時須一併考量」。
> **真正失效的是「補標時須一併考量」這個人工流程約束——它沒有機制 enforcement。**
> 而 v1 的根因（20260731 補掛面向分類）正是該警告描述的動作。

**這直接影響 requirements：下一版不得再依賴「維護者記得一起考量」。**

---

## Q2 — 是否已有可利用的 first-class signal：**signal value CONFIRMED，作為 routing authority 為 INSUFFICIENT EVIDENCE**

```text
judgeable pairs = 31

semantic gate           agreement 24/31 = 77%｜not-applicable reject 15/15｜applicable retain 9/16
best scalar threshold   overall   23/31 = 74%
```

⚠️ **不得寫成「semantic 明顯比 similarity 準」**——整體正確率只差一筆。真正成立的是：

> 若要求與 semantic gate 同樣做到 **0 個不適用 pair 被放行**，
> scalar similarity threshold 須提高到 **>0.945**，此時 16 個適用 pair **只剩 1 個**保留；
> semantic applicability judgment 在同樣零放行下保留 **9/16**。

**Existence proof**：

> **`query × KB` 中存在 similarity margin 沒有充分表示的 applicability information。**

但它仍：①不知道 Face；②不能決定「該不該進任何 Face」；③不能決定「該進哪個 Face」；
④不覆蓋所有 entry source；⑤routing false-reject loss 尚未裁定。**故不可升格為 candidate。**

---

## Q3 — Necessary vs manifestation

```text
NECESSARY
  N1  routing 必須取得**不等價於 similarity ＋ category** 的新增 applicability information
  N2  該 applicability evidence 必須接上**能實際改變 routing outcome** 的 authority

SUPPORTED REQUIREMENT
  N3  共同 authority contract ≠ 共同 classifier；entry-source-specific evidence 可能必要
      （目前為 coverage gap，缺 failure counterexample——**不得以「沒有 query input」本身當 failure**）

MANIFESTATION
  lexical abstain 64%｜Level A allowlist 過窄｜KB／Hint 共居｜top1 gate 44% false reject｜LLM nondeterminism

INSUFFICIENT EVIDENCE
  L2／L3／L4／L6 哪一層應承擔主責｜H1／H2／H3 是否存在單一 root-cause winner
```

### ⭐ discovery 的關鍵結論

> **目前沒有證據支持「選一層」就能解本案；
> N1 是 information contract，N2 是 enforcement contract，兩者可能天然跨層。**

⚠️ 此結論的作用是**防止 requirements 階段被迫回答「到底 L3 還是 L4」**。

---

## N3 何時值得再查（**不是現在，且不得為了升格而找反例**）

```text
情況一  requirements／design candidate **宣稱要統一治理五種 entry source**
        → 必須查 trigger／vision／session 的實際 failure history，否則可能過度設計
情況二  候選方案**只治理 classification routing**
        → 可明確 scope-out 其他三路，N3 不必升格；
          但須證明該 scope 是**有意識的**，而非又一次 Level-A 式無證據白名單
```

> **N3 是否需要升格，取決於下一版宣告要解多大的問題**，而不是 discovery 現在非得把它升成 NECESSARY。

---

## 一句話帶到 requirements

> **v2 的最低契約不是「需要一個更好的 classifier」，而是
> 「需要新增 applicability information，並讓它在 routing decision 上擁有
> 真正、可追溯、可執行的 authority」。**
