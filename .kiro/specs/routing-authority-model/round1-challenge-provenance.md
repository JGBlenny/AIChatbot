# Round 1 challenge：provenance 定性與 claim ceiling（**凍結於看見 raw cohort 之前**）

> 2026-08-24｜語言 zh-TW
> ⚠️ 本檔 commit 時：隔離作者**仍在執行**，**尚未看見任何 case**、**尚未跑任何 member**。

## ⭐ 定性：這是一批 **axis-conditioned challenge set**

```text
member_blind = true
axis_blind   = false
```

作者不知道 D1／D3 member，但**知道產品面向的粗粒度角色**，
而粗粒度角色**已包含「某一筆實際狀況」這個 applicability 軸**。

⚠️ **兩件事不得混為一談**：member-blind ≠ axis-blind。

```text
axis_exposure（已揭露給作者）
  candidate Face 的粗粒度角色（一行）
  instance-specific real-state orientation（「會查該筆的實際狀況」）

not_exposed（未揭露）
  D1 demand artifact ｜ D3 responsibility contract ｜ 細部 applicability 規則
  member evaluator（class／model／prompt）｜ member outputs
  v1／Q1／Q2 的 failure cases 與 wording ｜ similarity scores
  numeric matching tolerance ｜ 讓 case 通過 B matching 的技巧
```

## 對兩個 member 的影響**不同**

**D1（影響最大）**：若 A／B 表現好，可證

> D1 能在未見 wording、production-shaped ambiguity 下，
> **執行一個事前指定的 `instance-specific applicability` 軸**。

⚠️ **不得**擴寫成「D1 自己發現了正確的 routing applicability semantics」——
該軸在 challenge generation **之前**就已由產品角色描述植入。

```text
可以證明：pre-specified semantic axis → member representation／evaluator 能否穩定辨識
不能證明：該 axis 是否由資料自然導出，或是否為完整的 routing authority semantics
```

**D3（影響不同）**：`handles／does_not_handle／self_scope_rule` **未**洩漏給作者，
故 challenge **不是**照 D3 contract 逐條出題。若 D3 通過，可測到

> Face-owned responsibility semantics 能否對**沒看過 contract** 的自然對比 wording 做 discrimination。

⚠️ 但仍**不能**說 challenge 完全獨立於 Face responsibility——作者至少知道三個 Face 的粗粒度角色。

---

## ⭐ CLAIM CEILING（凍結；限制**結果可被解讀到哪裡**，非改 acceptance ruler）

> **A／B PASS may establish execution／discrimination of the predeclared
> applicability axis; it SHALL NOT by itself validate the normative correctness
> or completeness of that axis.**

**明令禁止的擴寫**：

```text
❌ D1 PASS → 「rule/instance 就是 routing 正確的 first-class semantics」
❌ D3 PASS → 「這六個 Face responsibility contract 已完整定義產品 routing boundary」
```

---

## Step ⑥ 協定：**對 labeler 隱藏 pair mapping**

⚠️ 作者被要求產 opposite-applicability contrast pairs，
故 **pair membership 本身就是一種弱 supervision**（「這兩句理論上應該不同」）。

```text
60 句 → **隨機排序** → **去除 pair id** → 單句獨立呈現
labeler 只看到：query ｜ candidate Face ｜必要的獨立產品資料
labels freeze 後 → **才**恢復 pair mapping 供 Experiment A／B
```

⚠️ **若一組的兩句被盲標成同一 applicability，SHALL NOT 人工修正**——
那代表**作者意圖未成功轉成產品 ground truth**，照實留下。

## Step ⑥ ground truth source 優先序（由強到弱）

```text
1. 獨立既有 product／business specification
2. Face seed 中 **D3 artifact 轉譯前**的 authoritative source
3. product owner adjudication
4. D3 responsibility artifact 本身   ← 落到此層則：normative_dependence = present，D3 證據**降級**
```

⚠️ **`D1 demand spec` 亦不得作為 label ground truth**——否則 D1 形成自身的 circularity。
⚠️ 若無更獨立來源，**如實標記**，**不補造獨立性**。

## 資料生命週期（不得刪 case）

```text
isolated author → **raw cohort freeze（原封不動，不刪任何 case）** → dataset digest
→ blind labels freeze（pair-hidden）
──────────────────────────────────────
A：使用符合 A contract 的 cohort
B：自 frozen cohort **依 frozen ruler 機械導出** eligible matched subset（**演算法產物，非人工挑選**）
```
