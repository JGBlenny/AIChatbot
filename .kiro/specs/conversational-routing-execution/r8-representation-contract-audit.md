# R8：Retrieval Representation Contract Audit（2026-08-29）

- 對象：frozen Level-A **10 rows** 全量 census
- ⛔ 未改任何 scoring surface、未改 KB、未設計新欄位、未跑語料

## ⚠️ 一個必須先建立的區分：coverage 要**逐 surface** 判

```text
embedding surface  = question_summary ＋ keywords（部分路徑）
reranker surface   = question_summary **only**（R5 已證，keywords ⛔ 不進）
```

⇒ 同一列可能「在 embedding 有代表、在 reranker 沒有」。
⛔ 不得用單一「representation_coverage」欄位掩蓋這個差異。

## R8.3 —— **現有系統沒有任何此類契約**

```text
搜尋 scripts/audit/ 與契約模組：**無**任何機器可讀規則要求
「retrieval representation 必須覆蓋 responsibility envelope」
⇒ `question_summary` 同時被當成：
     人類可讀題意 ／ embedding surface ／ reranker surface
   而 capability envelope 可以遠大於它，**沒有任何守衛**
```

## R8.1／R8.2 —— 逐列 census

```text
row   envelope_source        embedding_surface      reranker_surface    coverage
                             (summary＋keywords)    (summary only)
```

### answer 完整表示語義者

```text
3402  ANSWER              summary＋7 keywords        summary          **COMPLETE**
      evidence：keywords 含 點退帳單／退房結算／賠償／押金互抵／搬出後帳單
              ——涵蓋 answer 承諾的自動產生／結算項目／押金互抵
3519  ANSWER              summary＋6 keywords        summary          **COMPLETE**
      evidence：190 字 answer 的算法／正負號／押金結算，keywords 有 押金結算／點退計算／退款金額
```

### ⚠️ surface 之間不一致者

```text
3406  ANSWER              summary＋7 keywords        summary          **embedding COMPLETE
                                                                     ／reranker PARTIAL**
      evidence：keywords 明確含「下載收據／收據列印／收據怎麼拿」
              ——正是 R6 中失敗 query 的語彙
              但 **keywords 不進 reranker** ⇒ reranker 只看到
              「帳單收據 繳費證明 PDF 下載」
      ⇒ 這解釋了為何 3406 有 causal counterexample：
        代表性**存在於系統中，卻不存在於決定分數的那個 surface**
```

### coverage 來自 capability、文字只涵蓋一部分者（＝B2 家族）

```text
3495  ANSWER_AND_CAPABILITY  summary＋5 keywords     summary          **PARTIAL**
      evidence：answer 僅 28 字「狀態不對、金額未填、度數未填」，
              而 capability 是 `_diagnose_cannot_send` 對**該筆**做狀態判斷
3496  ANSWER_AND_CAPABILITY  summary＋6 keywords     summary          **PARTIAL**
      evidence：answer 34 字只給狀態條件；capability 診斷該筆為何不能取消
3498  ANSWER_AND_CAPABILITY  summary＋6 keywords     summary          **PARTIAL**
      evidence：answer 48 字僅公式；capability 用該筆實值判「為何被收」
3499  ANSWER_AND_CAPABILITY  summary＋6 keywords     summary          **PARTIAL**
      ⚠️ answer 22 字寫「常見三種」**卻沒有列出來** ⇒ 文字本身即不完整（R1 已記）
```

### coverage 幾乎全在 capability（＝anchors）

```text
4640  CAPABILITY          summary＋**3** keywords    summary          **PARTIAL**
      evidence：summary「帳單收據金額 收據多少錢」與 capability（查該筆收據金額）**貼合**
              ⚠️ 佐證：A03 的 I1-explicit **10/10 全對**
4657  CAPABILITY          summary＋**3** keywords    summary          **PARTIAL**
      evidence：summary「合約的點退帳單金額 查點退金額」與 capability 貼合；I3-explicit 7/10
4656  CAPABILITY          summary＋**3** keywords    summary          **MISSING**
      evidence：summary「查帳單 帳單編號查詢」＋keywords 帳單／查詢／編號
              而 capability 是 `_format_bill_status`——**該筆帳單的完整現況**
              ⛔ 狀態／已繳未繳／已寄出／草稿／到期 **一個都沒出現**
              ⚠️ 佐證：A03 的 I2-explicit **僅 3/10**，失敗 query 正是
                     「到底繳了沒」「已寄出還是草稿」
```

## 結論

```text
① **不是 anchor exception**：PARTIAL 橫跨 answer-bearing（3495/3496/3498/3499）
   與 anchors（4640/4657），MISSING 出現在 4656
   ⇒ 這是 **architecture contract 缺口**，⛔ 不是少數特例
② 三個 anchors 的 keywords 只有 **3 個泛詞**，而 7 個 answer-bearing row 有 5–7 個
   ⚠️ **語義全在 capability 的那三列，反而擁有最薄的 scoring surface**
③ ⚠️ 3406 揭示的是**另一種**問題：代表性存在（在 keywords）但
   **不在決定分數的 surface 上** ⇒ ⛔ 不能與 3495/4656 的「根本沒有」混為一談
④ **coverage 與 A03 表現一致**（可交叉驗證，非事後合理化）：
     4640 PARTIAL-貼合 → I1 10/10
     4657 PARTIAL-貼合 → I3 7/10
     4656 MISSING      → I2 3/10
```

## Candidate invariant（⛔ **不落地**，待 R9）

> **被 routing authority 視為可承接某 semantic responsibility 的 Knowledge row，
> 其 retrieval representation 必須能機器可驗地覆蓋該 responsibility；
> ⛔ 不得讓 capability 只存在 downstream、卻完全缺席於 retrieval scoring surface。**

⚠️ R8 已證明它**不是**局部例外（結論①），但落地前仍需回答：
```text
・「覆蓋」如何機器可驗？（詞面？語義？由誰宣告？）
・keywords 進 embedding 不進 reranker 的不一致要不要一併處理？
・修法會不會反轉「answer 稀釋 intent」的歷史 tradeoff（R5 已降級但未推翻）
```

## 狀態

```text
representation contract gap    **CONFIRMED as structural**（⛔ 非 anchor exception）
machine-readable contract      **不存在**（R8.3）
surface inconsistency          **CONFIRMED**（keywords 進 embedding 不進 reranker）
B1 semantic generalization     保持 CONFIRMED failure shape；
                               reranker generalization defect **NOT YET ESTABLISHED**
B3 model discrimination        CANDIDATE（2 筆），⛔ 待 representation contract 定清後再測
⛔ 未改任何 scoring surface、未設計新欄位
⏸ gate authorization／3.4／gate enable／scope expansion／release 全部 PAUSED
```
