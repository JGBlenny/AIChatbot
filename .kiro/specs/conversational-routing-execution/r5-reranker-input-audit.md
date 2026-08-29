# R5：reranker 輸入架構的 code-path audit（2026-08-29）

- ⛔ 純程式碼追查：**未跑 A03、未改參數、未改 KB**
- 追到真正送進 model 的 payload，⛔ 不停在函式名稱或中間變數

## 結論：**`ANSWER_COVERAGE_NOT_REPRESENTED_IN_RERANK_INPUT` ＝ CONFIRMED（輸入架構層）**

服務端 `semantic_model/scripts/api_server.py::rerank`（原文）：

```python
# 只用 question_summary 評分（與 embedding 一致）
# 原因：answer/content 會稀釋標題的意圖訊號，
# 實測拿掉後差距提升 99%，正確率不變（見 knowledge.md §5）
pairs = []
for candidate in request.candidates:
    question = candidate.get("question_summary", "")
    text = question if question else (candidate.get("answer") or candidate.get("content", ""))
    pairs.append([request.query, text])
```

⚠️ **這是刻意的設計決策，不是遺漏**——註解寫明了理由與實測依據。
⇒ 但它的必然後果，正是 R4 量到的東西。

## 逐項回答

```text
① candidate text 的實際組裝公式
   text = question_summary  若非空
        = answer or content 僅在 question_summary **為空** 時
   ⛔ 不含 categories／keywords／title／answer（正常情況）
   ⇒ **answer 的內容不進 reranker 的 document text**

② 空 answer anchor（4640／4656／4657）
   它們的 question_summary **非空**（如「帳單收據金額 收據多少錢」）
   ⇒ 走與一般 row **完全相同**的路徑，⛔ 無特殊 shape、⛔ 無 fallback 觸發
   ⚠️ 反向情形（question_summary 空）才會 fallback 到 answer——本批不適用

③ truncation
   scoring 輸入是 question_summary（短），⛔ 無截斷問題
   ⚠️ `content[:200]` 只出現在**回應 payload**，⛔ 不影響評分

④ query/document 順序
   `pairs.append([request.query, text])` —— query 在前、document 在後
   ⛔ 無反接、⛔ 無特殊 prefix

⑤ rerank_score 是否有中間 transform
   server：`"score": float(score)`（model.predict 原值）
   client：`candidate["semantic_score"] = score_info.get("score", 0)`  ← 鍵名映射在此
           `item['rerank_score'] = item.get('semantic_score', 0)`
   ⇒ **無 calibration、無縮放**，Step 6 用的就是 model 原始分數
```

## 這如何契合 R4 的量測

```text
3406 的 question_summary ＝「帳單收據 繳費證明 PDF 下載」（**關鍵詞串，非句子**）
其 answer 才描述「帳單詳情頁 → 繳費後 → PDF 下載」的操作語義

R2 判 COVERED 依據的是 **answer 內容**
reranker 評分依據的是 **question_summary**
⇒ 形成：**answer semantic coverage 存在，但 retrieval scoring surface 沒有暴露該 coverage**
```

⚠️ 對照組之所以高分，形態上也一致：
`I1` 的 query「我這張收據實際金額是多少」對 summary「帳單收據金額 收據多少錢」——**詞面高度重疊**；
而失敗案例多為依賴 answer 操作語義的自然改寫。

## ⛔ 尚未證明的部分（claim ceiling）

```text
✅ 已證明：**輸入架構**確實只用 question_summary 評分
⛔ **未證明**：這就是那 23 筆的 root cause

還缺 causal coverage：需逐筆量
   query ↔ answer 的語義相符度  vs  query ↔ question_summary 的語義相符度
若失敗案例普遍是「與 answer 強相符、與 summary 弱相符」，才構成因果。
⇒ 那是 **R6**，⛔ 本輪不做。
```

## 狀態

```text
score/calibration locus            ESTABLISHED（R4：binding component ＝ rerank_score）
reranker input-text hypothesis     **CONFIRMED as input architecture**（R5）
reranker itself defective          **NOT ESTABLISHED**
  ⚠️ 目前證據顯示 reranker 是在**被給定的文字**上正常運作；
     問題在於**給它看的是哪段文字**——那是設計決策，不是模型故障
root cause of the 23 cases         **NOT YET ESTABLISHED**（待 R6 causal coverage）
⛔ 未提修法、未改任何參數
⏸ gate authorization／3.4／gate enable／scope expansion／release 全部 PAUSED
```
