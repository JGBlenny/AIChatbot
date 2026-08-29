# 76 筆 INSTANCE_PROPOSAL 的 authority relevance 分桶（2026-08-29）

- 方法：**純機械 join**——`row → 全部 nomination candidates → 各 Face requirement → Level-A scope`
- ⛔ **未打開任何一筆的內容**；本步驟不需要語義判斷

⚠️ 判定單位是 **row × 全部候選**，⛔ 不是「第一個 Face」——
先前已證明多候選存在且執行端不得去重；若 `candidate A=NOT_REQUIRED、candidate B=REQUIRED`，
該 row 仍屬 authority-relevant。

## 分桶結果

```text
A CURRENT_GATE_RELEVANT    n=**3**   至少一個 REQUIRED 候選且落在 LEVEL_A_INSTANCE_GATE_SCOPE
B AUTHORITY_RELEVANT       n=18     有 REQUIRED 候選，但不在 Level-A scope
C FACE_UNKNOWN             n=0      無 REQUIRED，但有 UNKNOWN 候選
D NON_APPLICABLE_NOW       n=55     無候選，或全部候選皆 NOT_REQUIRED
                                    ────
                                     76
```

**A 的三筆**：`4640`、`4656`、`4657` —— 皆指向 `bill_diagnosis`。

⇒ **需要人工確認的工作量從 76 縮到 3。**

## ⚠️ 兩種「影響」不得混談

```text
current gate authorization relevance  ＝ A（3 筆）
potential authority relevance         ＝ A ＋ B（21 筆）
目前 gate 為 OFF ⇒ **76 筆對 runtime routing 的直接影響 ＝ 0**
```

⚠️ `C FACE_UNKNOWN` 本批為 0，但**若未來 `account_binding` 補上 requirement**，
桶 D 中經由該面向提名的 row 可能重新變成 relevant。
⛔ 因此 D **不得**被讀成「永久無關」。

⚠️ B 也**不是沒價值**——只是在未裁定擴大 `PREENTRY_ROUTABILITY_FACETS` 之前，
⛔ 它們不應偷跑成這輪 gate population 的 blocker。（scope 不擴就只驗 scope。）

## Level-A scope 的 truth 缺口（`bill_diagnosis`）

提名 `bill_diagnosis` 的知識共 **10 筆**：

```text
已宣告 instance（deterministic evidence）   4
UNKNOWN — 屬 INSTANCE_PROPOSAL              3   ← 即桶 A 的 4640／4656／4657
UNKNOWN — 屬 general review queue           3
```

⇒ **要讓 Level-A gate scope 的 knowledge truth 完整，只剩 6 筆待決。**

⚠️ 那 3 筆 general review queue 特別關鍵：它們提名 `bill_diagnosis`（REQUIRED），
若被誤標 general，交叉判定會得到 `INELIGIBLE` ⇒ **靜默抑制本該進場的 Face**。
依裁定②，它們必須取得**正面 reviewed declaration**，
⛔ 不得沿用盲標合議（該法已被 3509 正對照證偽）。

## 下一步的最小集合

```text
6 筆（3 proposal ＋ 3 general queue）
→ reviewed declaration
→ Level-A scope 的兩軸 truth 完整
→ 才輪到 gate authorization 的其他前置
⏸ 3.4 仍 PAUSED
```
