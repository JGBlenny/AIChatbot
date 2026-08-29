# R7-B：10 筆 residual 的 static semantic decomposition（2026-08-29）

- 母體鎖定 **10 筆**：3406 residual 3／3495 1／3498 residual 3／3496 1／3519 2
  ⛔ anchors 4656/4657 ×4 **不混入**
- ⛔ 未跑新模型實驗、未改參數、未碰 KB；只用既有分數 ＋ frozen 文字做靜態比對

## 判準（互斥，⛔ 不靠「我覺得很像」）

```text
B1 QUERY_SEMANTIC_EXPANSION    文字有相關概念，但 query 用了同義／更抽象的表達，
                               需 semantic generalization 才能對上
B2 ROW_REPRESENTATION_INCOMPLETE  capability 明確涵蓋，但 summary／answer **根本沒寫出那段責任**
B3 RERANKER_SEMANTIC_FAILURE   query 的關鍵詞**直接出現在** document，
                               且分數遠低於**詞面重疊相當**的同-row controls
B4 AMBIGUOUS
```

## ⚠️ B3 的證據：同-row、詞面重疊相當，分數卻天差地別

```text
row 3406  summary「帳單收據 繳費證明 PDF 下載」

  control  「收據的 PDF 要去哪裡下載」        sum **0.970**
  RESID    「收據下載的路徑麻煩告知一下」      sum **0.175**   ← 收據／下載 皆在 summary 內

  control  「繳費證明怎麼拿到電子檔」          sum **0.987**
  RESID    「想問繳費證明的取得方式謝謝」      sum **0.629**   ← 繳費證明 在 summary 內
```

⇒ 兩組意圖近乎同義、關鍵詞同樣落在 document 內，分數卻差 0.35–0.80
⇒ **B3 ×2**（#27、#25）

## 逐筆裁定

```text
#27  3406  sum 0.175 ans 0.164  「收據下載的路徑麻煩告知一下」        **B3**
#25  3406  sum 0.629 ans 0.585  「想問繳費證明的取得方式謝謝」        **B3**
#23  3406  sum 0.018 ans 0.209  「後台哪裡可以匯出收據」              **B1**（匯出≈下載，需同義推廣）
#166 3498  sum 0.220 ans 0.000  「編號 2205 的帳單多了一筆滯納金為什麼」**B1**（滯納金≈逾期費／延遲金）
#146 3496  sum 0.636 ans 0.472  「這張帳單取消時跳錯誤是什麼意思」     **B1**（跳錯誤≈取消不了）
#42  3519  sum 0.296 ans 0.596  「押金不夠扣的話金額會怎麼呈現」       **B1**（query 缺「點退」錨詞）
#50  3519  sum 0.649 ans 0.340  「結算金額包含哪些項目」               **B1**（同上，缺「點退」）
#167 3498  sum 0.514 ans 0.600  「這張帳單逾期費算的日期我覺得不對」   **B2**
#169 3498  sum 0.605 ans 0.034  「那筆帳單房客明明有繳為何還算逾期」   **B2**
#127 3495  sum 0.377 ans 0.484  「這張帳單一直顯示發送中是怎樣」       **B2**
```

### B2 的共同形狀：coverage 來自 **capability**，不來自文字

```text
3498 的 answer 只有公式「租金 × 遲繳天數 × 費率%；遲繳天數 = 付款日 − 到期日 − 緩衝天數」
3495 的 answer 只有「常見原因：狀態不對、金額未填、度數未填」
而 R2 判 COVERED 的依據是：兩列皆宣告 instance ＋ Face 會診斷**那一筆**
⇒ capability envelope ≫ text envelope
⇒ retrieval **看不到**那段責任 —— 與 anchors（R7-C）同型，只是程度較輕
```

### #42 的補充：answer 明文寫了，卻仍不足

```text
3519 answer：「正數則代表押金扣完還不夠，租客需要補繳差額」
#42 問的正是這件事，answer counterfactual 也只到 0.596（未跨 0.65）
⚠️ 但 query 缺少「點退／結算」錨詞，而同-row controls 皆帶該錨詞
   （「押金會不會直接在**點退帳單**裡扣掉」sum 0.876）
⇒ 判 **B1** 而非 B3：差異可由錨詞缺失解釋，⛔ 不需訴諸模型失能
```

## 主表

```text
B1 QUERY_SEMANTIC_EXPANSION      **5**
B2 ROW_REPRESENTATION_INCOMPLETE **3**
B3 RERANKER_SEMANTIC_FAILURE     **2**
B4 AMBIGUOUS                      0
```

## 結論

```text
⇒ **no single residual mechanism** —— 10 筆分散在三種不同機制上
⛔ 不得為了找 root cause 強行合併
```

## 三個機制各自的下一步（⛔ 本檔不提修法，只標定方向）

```text
B2（3 筆）→ 屬 **representation architecture／KB contract**，⛔ 非 reranker tuning
             與 R7-C 的 anchor 問題同源：能力語義未進 retrieval surface
B1（5 筆）→ 值得研究 reranker 對自然 paraphrase／同義詞／錨詞缺失的泛化能力
B3（2 筆）→ **唯一**有資格開 model/reranker discrimination test 的一組
             （同-row、詞面重疊相當、分數差 0.35–0.80）
```

## 狀態

```text
threshold-policy defect globally  NOT ESTABLISHED
  對 3496／3519 的 3 個 case：threshold contribution = NOT_SUPPORTED（R7-A，⛔ 不改寫成「threshold 沒問題」）
score/scoring locus               ESTABLISHED
residual mechanism                **無單一機制**：B1 5／B2 3／B3 2
reranker semantic failure         **CANDIDATE**（僅 #27／#25 兩筆有資格）
anchors 4656/4657 ×4              OPEN（R7-C 已證架構事實，causal 未證）
⛔ 未改任何 production 參數
⏸ gate authorization／3.4／gate enable／scope expansion／release 全部 PAUSED
```
