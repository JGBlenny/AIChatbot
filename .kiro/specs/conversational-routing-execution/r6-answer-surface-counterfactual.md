# R6：summary→answer 的 counterfactual（2026-08-29）

- 母體先拆：**R6-A answer-bearing 19 筆**／**R6-B empty-answer anchor 4 筆**（4656×3、4657×1）
  ⚠️ anchor 的 coverage 由 Face／downstream capability 定義，**不由 answer 定義**
  ⇒ ⛔ 不得拿空字串低分當反證、⛔ 不得人工補 capability description（那是設計新 document）
  ⇒ R6-B 的 root cause **維持 OPEN**，另作 anchor scoring-surface investigation
- intervention **只有一項**：送進 reranker 的 document text（利用服務端既有
  `text = summary if summary else (answer or content)`，送空 summary 即改用 frozen answer）
  ⇒ **同一 model、同一 endpoint**；vector／keyword／finalize 公式一律 production 原值
- endpoint 用 production boundary：`final = 0.1×vector + 0.9×rerank` 是否從 `<0.65` 跨到 `>=0.65`
  ⛔ 未新增任何「delta 多少算 meaningful」的事後量尺

## 主表（R6-A，n=19）

```text
C1 ANSWER_SURFACE_RESCUES      **9**
C2 IMPROVES_NOT_ENOUGH           4
C3 NO_ANSWER_ADVANTAGE           6
C4 NOT_TESTABLE                  0
```

⇒ **C1 未過半（9/19）**，⛔ 不足以把 summary-only 輸入定成 answer-bearing 集合的主因。

## 逐 expected_row —— 機制是 **row-specific**，不是全域

```text
row    n   rerank_summary(med)  rerank_answer(med)   C1
3406   9        **0.1658**          **0.7982**       **6**   ← 集中在此列
3402   1          0.6433              0.9927           1
3498   5          0.5503              0.5995           2
3495   1          0.3765              0.4844           0
3496   1          0.6360            **0.4717**         0   ← answer **更差**
3519   2          0.6486            **0.5961**         0   ← answer **更差**
```

## ⚠️ same-row positive controls 排除了「長文本天生高分」

```text
row    n   rerank_summary(med)  rerank_answer(med)
3402   3       **0.9661**            0.9758
3406   3       **0.9698**            0.9751
3495   3       **0.9363**            0.9136
3496   3       **0.9867**            0.7975
3498   3       **0.9185**          **0.1131**
3519   3       **0.8762**            0.9746

delta(answer − summary)
  FAIL cases   min −0.5703  median **+0.1367**  max +0.9244
  CONTROLS     min −0.8821  median **−0.0122**  max +0.1812
```

⇒ 對照組的 **summary 本來就高（0.876–0.987），不需要救援**；
且 answer **並未**系統性優於 summary（中位差 −0.012，3498 甚至掉到 0.113）
⇒ ⛔ 「answer 比較長所以分數比較高」**被排除**。

## 結論（嚴格版）

```text
✅ 對 **3406** 這一列：summary-only reranker input **是** confirmed causal mechanism
   （9 筆失敗中 6 筆，只換 document 即跨回既有 production threshold；
     summary median 0.166 → answer median 0.798）
✅ 該機制**不是**「長文本優勢」——同列對照組已排除
⛔ **不得**推廣成 answer-bearing 19 筆的主因（C1 僅 9/19）
⛔ **不得**推廣成 23 筆 threshold-loss 的 root cause
⚠️ 3495／3496／3519 的失敗**不被此機制解釋**（answer 反而更差）⇒ 另有機制，仍 OPEN
⛔ **不得**據此主張「production 應改成 rerank answer」——那是修法；
   且舊設計文件明載曾有「answer 稀釋 intent」的實測依據（R5 引用），
   任何修法必須重新處理該 tradeoff，⛔ 不得因這批 failure 直接反轉歷史設計
⛔ **不得**外推到 empty-answer anchors（R6-B 4 筆）
```

## 狀態

```text
retrieval scoring surface mismatch  **CONFIRMED for row 3406**，⛔ 非全域
score/calibration locus             ESTABLISHED（R4）
reranker itself defective           NOT ESTABLISHED
root cause of the 23 cases          **PARTIALLY ESTABLISHED**
  ・3406 的 6 筆    → scoring surface mismatch（已解釋）
  ・3495/3496/3519  → **OPEN**（answer surface 反而更差）
  ・3498 的 5 筆    → 僅 2 筆可被解釋，其餘 OPEN
  ・R6-B anchor 4 筆 → **OPEN**（不可用本方法檢驗）
candidate-generation 6／40｜ranking 11／40  維持 secondary
⛔ 未改 production、未改 threshold、未串 summary+answer、未新增 capability text
⏸ gate authorization／3.4／gate enable／scope expansion／release 全部 PAUSED
```
