# Round 1：challenge／evaluation contract（**Step ③ freeze**）

> 2026-08-24｜語言 zh-TW｜matching ruler 已凍結（`326ce04`，tolerance `0.058928`）
> ⚠️ 本檔為 **Step ③**：凍結評估契約。**尚未定義 concrete member（Step ④）、尚未產 cases（Step ⑤）。**

## Round 1 範圍

```text
Round 1
├ D1-member-1   candidate-specific applicability adjudication
└ D3-member-1   Face-owned applicability contract

Deferred（**皆非淘汰**）
├ D2  INSUFFICIENT_EVIDENCE / deferred
└ D4  INSUFFICIENT_EVIDENCE / dependency not ready
```

### ⚠️ D2 暫緩的理由（**更正紀錄**）

我先前寫「因為 D2 已有一個 member 被反證，故降低優先級」——
**那句話本身違反 M1**（member 失敗不得外推到 family），業主已更正。正確表述：

> **D2 deferred in Round 1 because current positive evidence is
> `query × KB` ／ `query × Face` applicability, **not query-alone semantics**.
> Before testing a new D2 member, it MUST state what first-class representation
> supplies R1 information, and why that representation is not merely a new member
> of the already-refuted lexical approach.**

⚠️ v1 的 64% abstain 是**新 member 必須回答的歷史風險**，
**不是**延後 D2 的證據資格理由。

### D4 暫緩的理由

D4 的定義**已自認不產生 R1 的新 information**。
在**沒有任何受支持的 upstream evidence member** 之前，它的核心問題

```text
same upstream evidence：with D4 vs without D4 → correctness property 是否增加？
```

無從回答；第一輪只能測 wiring／architecture shape，**極易退化成 R3 的「看起來很乾淨」**。

---

## ⭐ 三項新增凍結（專為 D1／D3 共用 cohort）

### ① evaluation unit

```text
evaluation unit = **query × fixed candidate Face**
```

### ② ground truth

```text
ground truth = **該 Face 對該 query 是否 applicable**
             ≠ rule／instance label        ← 這是 v1 的混淆，不得重演
label 值域   = applicable ／ not_applicable ／ undecidable
```

### ③ case-generation neutrality

```text
作者**可以**知道：要產 semantic contrast pairs
作者**不得**知道：D1／D3 的具體 prompt、contract wording、
                 implementation output、已知 failure pattern
```

⚠️ **challenge author SHALL NOT 被要求「出能分出 D1 與 D3 的題」**——
否則測資會退化為 **architecture-comparison set**。
它只負責產生**對 R1 有效的 opposite-applicability pairs**。

---

## Information provenance 必須先切開（否則兩 member 會糊在一起）

```text
D1-member-1
  query × candidate Face ＋ **routing-owned** applicability evidence → adjudication
  ⚠️ Face 本身**不得**是該 evidence 的唯一作者／authority source

D3-member-1
  query ＋ **Face-owned** explicit responsibility contract → applicability evaluation
  ⚠️ Face 的「我適用」宣告**本身不成立**；仍須 query evidence 與 contract **可驗證地匹配**
```

**兩者各自要回答的問題不同**：

```text
D1：**獨立 adjudicator** 能否取得 query×Face 的新 applicability information？
D3：把 responsibility 變成 Face 的 **executable semantic contract**，能否提供這份新 information？
```

⚠️ **若 D1 直接讀 D3 那份 Face-owned contract 且無其他獨立 evidence，
兩個 family 在第一輪就糊在一起** → 該輪結果對 family disposition 無效。

---

## Negative control：兩者的**被測 premise 不同**（更正）

⚠️ 我先前說「D3 的自證 NC 正好能檢驗 D1」——**那是錯的**，業主已更正。
D3 的 NC 反證的是 **D3 自證**；D1 需要**自己的等價 NC**：

```text
D3-NC（self-attestation）
  Face 宣告自己適用 ＋ query 不符 responsibility contract → **SHALL reject**

D1-NC（proposal-momentum）
  candidate Face 已被 proposer 提出
  ＋ routing metadata／Face identity **強烈暗示**適用
  ＋ 獨立 applicability evidence **不支持**
  → **SHALL NOT** 因「candidate 已被提出」而自動判 applicable
```

**可用同一 challenge case，但 NC 的 premise 各自獨立。**

---

## 最小差異設計（**盡量控制，做不到就記 confound**）

```text
共同：query × Face → applicability evaluator → evidence
      同一 evaluator class ｜同一 model／config ｜同一 output schema ｜同一 execution protocol

僅變：authority-information source
      D1 → routing-owned applicability specification
      D3 → Face-owned executable responsibility contract
```

⚠️ 這**不是**規定必須用 LLM；是實驗控制。
⚠️ 若連 evaluator 都完全不同，則 D1 優於或劣於 D3 時
**無法區分是 architecture family 還是 classifier quality**。
⚠️ 若 family 定義使該控制**不可能**，**直接記 confound，不硬湊**。

---

## 其他沿用（不重述細節，僅列指標）

```text
matching ruler       tolerance 0.058928｜ruler_digest 1e6afd527d2ed79e（326ce04）
minimum pairs        20；不足 → INSUFFICIENT_EVIDENCE（不得放寬）
樣本來源             S1 v1 burned（僅 diagnostic，不得單獨作證據）／S2 spec-derived／S3 隔離作者
穩定性維度           paired discrimination｜phrasing perturbation｜repeated execution
                     ｜order perturbation｜不得依賴 similarity／category mutation
                     ⚠️ 門檻於 candidate implementation 前一次凍結
Experiment A         causal independence（非 accuracy）；A 通過須由 B production-shaped 複驗
disposition          member 兩級推 family（M1）；允許全部出局
```

## 時序（**不得對調**）

```text
③ 本檔 freeze ✅
↓
④ freeze D1-member-1 ＋ D3-member-1（member contract／implementation）
↓
⑤ isolated generation ＋ challenge freeze（cases 可更早產，但須封存不示作者）
↓
⑥ blind applicability labels freeze
──────────────────────────────────
⑦ first exposure：Experiment A → 通過者 B
↓
⑧ member disposition → 依 M1 更新 family disposition
```
