# Design Discovery：architecture families 與 falsification

> 2026-08-24｜語言 zh-TW｜requirements 已凍結（`e4c340a`）＋EARS 契約（`2f53b46`）
> ⚠️ **本階段只列候選與做 falsification，不選定 design、不進 implementation。**
> ⚠️ **允許的結論包含「沒有一個候選足以進 design」**——requirements 完成**不蘊含**必有 winner。

## 本階段不做的事

```text
❌ 先選 L2／L3／L4／L6 主責任層
❌ 先訂 routing false-reject 門檻（如 ≤5%）
❌ 現在產生新的 unseen holdout 給 design 作者看
❌ 把「把 Hint 搬到另一張表」當成一個候選（P7 已封死）
```

## `routing_false_reject_exposure` 欄位定義（業主 2026-08-24）

```text
none       設計本身不會因 applicability uncertainty 阻止原本正確的 Face entry
possible   某些判定會 veto 正確 entry，但**不是設計必然**
intrinsic  候選本質即 precision-first veto，**必然存在**錯拒 trade-off
```

⚠️ **僅** `possible`／`intrinsic` 且進入 finalist 時，才觸發產品裁示。
⚠️ 現在不得訂數字——**loss function 必須連同 failure consequence 一起裁**：
錯拒之後是回到 single answer／clarification／換另一個 Face／保留原 entry／其他 recovery，
目前**尚未知**，訂 threshold 沒有意義。

## ⭐ H1 不是第五個候選，而是貫穿四者的**資料責任維度**

```text
❌ content KB.categories → 搬到 routing-only KB.categories → 完成    （P7 已封死）
✅ 對每個候選問三題：
   ① Hint 的提出依據是什麼？
   ② 它是否具有獨立於 answer evidence 的 authority source？
   ③ 移出 answer row 是否**真的改變 information provenance**，還是只換了儲存位置？
```

---

## D1 — Candidate-specific applicability adjudication

```text
routing source → propose Face X → applicability evidence(query × Face X) → authority → enter/reject
```

| 欄 | 內容 |
|---|---|
| **New information source (R1)** | `query × Face X` 的 applicability 判定。⚠️ 待證：它是否**獨立於** similarity／category |
| **Authority consumer (R2)** | 進場 seam；須在 irreversible 之前（R2.2）|
| **Counterfactual effect (META)** | 原理上可達（三態對照可構造）|
| **Responsibility model (R3)** | proposer＝retrieval／evidence＝adjudicator／authority＝seam，**三者可區分** |
| **Executable invariant (R4)** | 「治理範圍內的 entry 不得未經 adjudication」為機器可判定 |
| **Entry-source assumptions (R5)** | 僅治理 retrieval-derived；其餘須**明示 scope-out ＋ 理由** |
| **False-reject exposure** | **intrinsic**——本質即 veto |
| **Known evidence** | Q2：`query × KB` 存在此類訊號（0 放行／44% 誤殺）；`scope=stay\|switch` 為 `query × 單一 Face`，**通過 pre-entry falsifier**，但 per-Face（N Face → N 次判定）且非決定性 |
| **Falsifier** | adjudication 的依據若來自**同一份 KB wording／metadata 的重述**，即違反 R1 |
| **Disposition** | **INSUFFICIENT_EVIDENCE**——缺「`query × Face` 判定的錯誤形態是否可接受」之證據；成本結構（N 次判定）亦未評估 |

## D2 — First-class query semantics

```text
query → structured semantic representation → candidate routing → authority
```

| 欄 | 內容 |
|---|---|
| **New information source (R1)** | 結構化 query representation。⚠️ **不得**以「intent classifier」當答案 |
| **Authority consumer (R2)** | 未定：representation 本身不含 authority，須另接 |
| **Counterfactual effect (META)** | 待證 |
| **Responsibility model (R3)** | representation 提供 evidence，但 **final authority 歸屬未定** |
| **Executable invariant (R4)** | 可構造（representation schema 可機器驗）|
| **Entry-source assumptions (R5)** | ⚠️ **最容易踩 R5.2**：query-only representation 對 session／caller assertion／vision **不足** |
| **False-reject exposure** | **possible**（取決於 routing 如何消費）|
| **Known evidence** | Q2 支持「query 中存在 similarity 未表達的 applicability information」——但那是 **`query × KB`**，**不是 query-alone**；⚠️ **v1 的 lexical candidate 正是本 family 中最便宜的一個實例，已被 unseen holdout REFUTED（64% abstain）** |
| **Falsifier** | representation ＝ retrieval category 的另一種編碼；或對「similarity／category 相同、期望相反」的 pair **無法產生區別** |
| **Disposition** | **INSUFFICIENT_EVIDENCE**——⚠️ 且本 family **已有一個成員被實測反證**，新成員須說明**為何不重蹈** |

## D3 — Face-owned applicability contract

```text
Face X 宣告自己的 applicability／responsibility contract → 以 query 對其求值 → authority
```

| 欄 | 內容 |
|---|---|
| **New information source (R1)** | Face 側的**明示契約**。⚠️ **不得**再走 slot-derived shortcut——v1 已證 `required_slots ≠ requires instance` |
| **Authority consumer (R2)** | 求值結果須有 pre-entry consumer |
| **Counterfactual effect (META)** | 待證 |
| **Responsibility model (R3)** | Face 同時是 evidence 提供者與被判對象——⚠️ **須說明如何避免自證** |
| **Executable invariant (R4)** | 契約若有 executable semantics 則可；否則直接被 R4 打掉 |
| **Entry-source assumptions (R5)** | 僅覆蓋有 Face 的路徑；trigger／vision／session 的 authority **不在 Face 側** |
| **False-reject exposure** | **possible**（若契約作為硬過濾）|
| **Known evidence** | v1 erratum 01 的 `requires_instance_reference` **正是本 family 的一個部分實例**——它證明**宣告本身不足**（仍需 evidence ＋ authority，即 N1／N2）；`scope=stay\|switch` 是 Face 擁有的 runtime 契約，但以 prompt 規則表達＝**非 executable、非決定性** |
| **Falsifier** | 契約最終仍只是另一組人工 categories／keywords 且**無 executable semantics** → R4 打掉 |
| **Disposition** | **INSUFFICIENT_EVIDENCE** |

## D4 — Source-specific authority adapters ＋ common decision contract

```text
session／caller assertion／vision／KB-derived proposal／prospect context
   → 各自 evidence adapter → **共同**的 proposal／evidence／authority responsibility 契約
```

| 欄 | 內容 |
|---|---|
| **New information source (R1)** | ⚠️ **本身不提供新資訊**——它是責任模型，**不滿足 R1**，須與 D1／D2／D3 之一併用 |
| **Authority consumer (R2)** | 契約層指定 final authority，可滿足 |
| **Counterfactual effect (META)** | 取決於併用的 evidence source |
| **Responsibility model (R3)** | **直接對準**（本 family 的核心）|
| **Executable invariant (R4)** | 契約合規性可機器驗 |
| **Entry-source assumptions (R5)** | **直接對準**：不要求共同 classifier，只要求共同**表達方式** |
| **False-reject exposure** | **none**（本身不 veto）|
| **Known evidence** | Q1 五路矩陣（五種 authority source 無共同契約）|
| **Falsifier** | 若它**未提供**任何「只治理 classification routing」所沒有的 correctness property → 即為 architectural elegance 而非必要 |
| **Disposition** | **INSUFFICIENT_EVIDENCE**——⚠️ **R3／R5 為 SUPPORTED 而非 NECESSARY，不足以證成 D4 必要** |

---

## 目前的整體判定

```text
D1  INSUFFICIENT_EVIDENCE     D2  INSUFFICIENT_EVIDENCE（且 family 內已有成員被反證）
D3  INSUFFICIENT_EVIDENCE     D4  INSUFFICIENT_EVIDENCE（且單獨不滿足 R1）

**沒有任何候選目前為 SUPPORTED。**
```

⚠️ 這是**誠實的當前狀態**，不是拖延：四者都缺**同一類證據**——

> **「該 evidence source 對 `(similarity, category)` 相同而期望相反的實例，能否穩定產生區別」**（R1.1／R1.2 的核心）。

## 新 holdout 的時序（**現在不產**）

```text
requirements frozen ✅
→ design discovery（現在）
→ candidate architecture selected
→ design contract frozen
→ robustness／acceptance ruler frozen
→ **隔離**產生新的 unseen holdout → blind labels freeze
────────────────────────────────────────────
→ candidate implementation／final evaluation
```

⚠️ 現在產出 unseen utterances 給 design 作者看，等於**先污染再設計**。
若要更早由完全隔離者產生並封存亦可，但 **design 作者不得看內容**；
實務上現階段**沒有必要增加該保管成本**。

⚠️ **v1 burned holdout** 可繼續作 **diagnostic／counterexample corpus**，
**不得**作新版泛化證據。
