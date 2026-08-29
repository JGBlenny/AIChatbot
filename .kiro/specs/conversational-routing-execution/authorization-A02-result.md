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

## 待業主裁定（⛔ 我不預選）

```text
【甲】接受本輪 INCONCLUSIVE，另開 A03，並在**新協議**中處理「無指涉診斷句」
     ⚠️ 若作法是「要求作者在 instance 題都加上『我的／這張』」，
        那等於**為了讓 oracle 一致而改題目**——⛔ 需明確意識到這是在調整測試使其通過
【乙】改變 truth oracle：把「無指涉的故障診斷句」定義成**第三類**（如 `context_dependent`），
     並在協議中預先規定它不進 Layer B 分母
【丙】重新檢視 query 層 truth 是否為正確的評估 oracle
     （受測系統其實是依 **top1 knowledge 宣告**判定，而非依 query）
⚠️ 另需裁定：是否要在 INCONCLUSIVE 之下仍執行一次 implementation 取得診斷資訊
   ——代價是 corpus 就此 BURNED，且結果**不得**用於授權。
```
