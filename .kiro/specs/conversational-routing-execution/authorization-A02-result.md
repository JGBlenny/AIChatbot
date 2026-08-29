# A02 執行結果（2026-08-29）——**INCONCLUSIVE ／ CORPUS_INSUFFICIENT**

⛔ **未跑 frozen implementation**：協議順序為
`integrity → label quality → corpus sufficiency → labels 凍結 → 才執行`，
sufficiency 未過即停。**corpus 尚未 BURNED。**

## 逐關結果

```text
① integrity           ✅  200/200 兩位皆齊；序號無越界／無漏標；
                          兩位皆 tool_uses = 1 且各只讀自己的語料檔
② label quality       ✅  L1 exact agreement = **94.5%**（>= 90%）
                          L2 Cohen's kappa   = **0.890**（>= 0.70）
③ corpus sufficiency  ❌  **I4 = 14/20、I5 = 14/20**（門檻 >= 15）
```

```text
G1 18 ✅   G2 20 ✅   G3 20 ✅   I1 20 ✅   I2 19 ✅
I3 20 ✅   **I4 14 ❌**   **I5 14 ❌**   I6 19 ✅   I7 17 ✅
總 judgeable 181（instance 123／general 58）
```

⇒ 依凍結協議：**A02 = INCONCLUSIVE**。
⛔ 不得補題、⛔ 不得合併 strata、⛔ 不得擴 oracle、⛔ 不得放寬門檻。

## ⚠️ 失敗形狀非常單一——**11 個分歧全是同一型**

```text
A=instance  B=undecidable   11 筆
A/B 之間 **instance ↔ general 的實質矛盾 = 0**
```

⇒ 兩位標註者**沒有對語義判斷相反**；B 只是對某一類句子選擇棄權。

## 那一類句子是什麼

```text
[I4] 帳單為什麼寄不出來 ／ 帳單送不出去是什麼原因 ／ 帳單開好了卻發不出去 哪裡有問題
     為什麼帳單發送鈕是灰的 ／ 帳單無法寄給租客 怎麼回事
[I5] 帳單取消鈕消失了 是什麼原因 ／ 帳單想作廢但按不下去
     取消帳單顯示不允許 為什麼 ／ 帳單無法取消的原因麻煩說明一下
```

共同特徵：**缺少明確的指涉標記**（沒有「我的」「這張」「編號 X」）。

⇒ 這類句子在 query 層**天生歧義**：

```text
可讀成「請說明一般會有哪些原因」   → general
也可讀成「診斷我這一張為什麼失敗」 → instance
```

⚠️ **這不是 authoring 缺陷**——作者被要求寫自然、簡略、口語的真實問法，
而真實使用者確實這樣打字。**這是現象本身。**

## ⚠️ 最重要的判讀：失敗發生在**評估 oracle**，不必然在系統

```text
受測系統的判定輸入 ＝ **retrieval top1 的 knowledge 宣告**（已凍結）
query 層 truth 只是**評估用的 oracle**

⇒ I4／I5 的 judgeable 不足，說的是
   「**這個 oracle 對『無指涉的故障診斷句』量不準**」，
   ⛔ **不是**「gate 在這類句子上會判錯」——後者本輪根本沒有量到。
```

⚠️ 這與 U1 的結論同源：applicability 不總是能從表層文字回復。
A01 是**來源**不足，A02 是**oracle**對特定語言形態不足——兩者都不是 gate correctness 的結論。

## 現況

```text
A02 corpus  digest 9921c5f36eafea79，**未 BURNED**（實作尚未看過）
labels      L1 94.5%／κ 0.890，已落檔（未凍結為 authorization 用）
gate        仍 OFF｜Level-A population 與 implementation 維持凍結
⏸ 3.4／gate enable／擴 scope／release 全部維持 PAUSED
```

## 業主裁定（2026-08-29）——A02 正式收案

```text
A02 = INCONCLUSIVE ／ reason = CORPUS_INSUFFICIENT（I4 = 14/20、I5 = 14/20）
⛔ 不修改原 protocol       ⛔ 不把 context_dependent 偷補進 A02
⛔ 不補題                  ⛔ **不跑 frozen implementation**
```

⚠️ **不為診斷而跑的理由**：失敗發生在 implementation **之前**；
而 P1f 的 consumer wiring 已有 deterministic matrix、authority-transfer death controls、
mutation 證明。現在燒掉只會得到「在一份不能用於授權的 corpus 上系統跑出了什麼」，
對主線價值不高，卻會失去一批 implementation-unseen 語料。

### ⚠️ A02 corpus 的精確狀態（⛔ 不可含混）

```text
**尚未被 implementation burn**，但**已因 protocol outcome 被看過**
⇒ ⛔ 不得在修改後的 A03 protocol 中重新拿來形成新的 authorization claim
✅ 可留作日後 **diagnostic corpus**，⛔ 但不是 A03 holdout
```

## 本輪找到的架構邊界（**比失敗本身重要**）

> **Applicability truth 是 Knowledge contract 的事實；
> 但 ambiguous query 要映射到哪個 Knowledge truth，
> 仍然是 retrieval／context interpretation 的責任。**

```text
⛔ 不能要求 applicability gate 去解決
   「帳單寄不出去」到底是在問一般原因、還是在診斷我的帳單

P1f 的責任**從這裡才開始**：
   retrieval 已選 3495 → 3495 明示 instance → bill_diagnosis REQUIRED → ELIGIBLE
```

⇒ 延續整條線的同一原則：**authority 不應偷偷承擔 nomination／interpretation 的責任。**

## 後續

```text
A03 另開協議（query oracle 改三態，semantic 與 authority 分開授權）
⏸ gate enable／3.4／release 繼續 PAUSED
```
