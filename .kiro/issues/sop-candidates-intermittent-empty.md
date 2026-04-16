# Issue: SOP candidates 間歇性空結果

> 建立時間：2026-04-17
> 狀態：待調查
> 優先級：中（影響 chat-test debug 可觀察性，不影響產線答案正確性）
> 發現時機：`retriever-similarity-refactor` 盤查 + followup-debug-visibility 實作驗證時

---

## 症狀

同一查詢「合約簽署」在 `POST /api/v1/message` 的兩次連續呼叫中，`debug_info.sop_candidates` 出現不一致：

**第 1 次呼叫**（重啟後首次）：
```json
"sop_candidates": [
  {"id": 655, "base_similarity": 0.6103, "rerank_score": 0.9994, "score_source": "rerank"},
  {"id": 657, "base_similarity": 0.5461, "rerank_score": 0.9466, "score_source": "rerank"}
]
```

**第 2 次呼叫**（立刻再打同一 request）：
```json
"sop_candidates": []
```

`comparison_metadata` 顯示 `sop_candidates: 0` 但 retriever 日誌顯示 SOP 向量檢索有 15 筆結果。

## 觀察到的佐證

從 rag-orchestrator 容器日誌：

```
# 第 1 次：SOP 路徑跑完整
🔍 [統一檢索] 查詢: 合約簽署
   向量檢索: 找到 15 個結果
   [Finalize] 計算 5 筆，分數來源: rerank=5
   閾值過濾: 5 → 2 筆 (>= 0.75)
   最終結果: 2 個

# 第 2 次：同樣查詢，但 SOP 通通過不了 threshold
🔍 [統一檢索] 查詢: 合約簽署
   向量檢索: 找到 15 個結果
   [Finalize] 計算 5 筆，分數來源: rerank=5
   閾值過濾: 5 → 0 筆 (>= 0.75)
   最終結果: 0 個
```

注意：兩次 `Finalize` 都顯示 `rerank=5`，但 rerank_score 大幅不同（第一次 ≈ 0.99，第二次 ≈ 0）。

## 疑似根因（待驗證）

1. **semantic-model 服務間歇性失效**：reranker 有時回傳高分、有時回傳 0。這與 issue `reranker-returning-zero.md` 可能是同一問題
2. **sop_orchestrator session state 副作用**：process_message 會根據 session_id 累積狀態；如果 session 被誤用，可能影響第二次查詢的處理路徑
3. **Redis 快取混入錯誤資料**：debug_info 本該跳過快取（`🔍 [DEBUG MODE] 檢測到 debug_info，跳過緩存`），但可能有路徑沒套用這條
4. **時序/並發問題**：asyncio.gather 同時跑 SOP + KB，兩個 task 的 reranker 呼叫搶同一 HTTP client

## 關聯

- 本問題可能是 `reranker-returning-zero.md` 的下游症狀
- 與 `retriever-similarity-refactor` 的重構無關（重構前也可能存在，只是缺乏 debug 可觀察性看不到）

## 重現步驟

1. 重啟 `aichatbot-rag-orchestrator` 容器
2. `curl -X POST http://localhost:8100/api/v1/message -H "Content-Type: application/json" -d '{"message":"合約簽署","vendor_id":2,"user_id":"u1","include_debug_info":true}'`
3. 立刻重複步驟 2（不改 user_id，不等 Redis TTL）
4. 比對兩次 `debug_info.sop_candidates` 與 `comparison_metadata.sop_score`
5. 觀察是否出現不一致

## 調查建議

- [ ] 抓取 reranker 服務 `semantic-model` 容器日誌，確認是否有 HTTP 超時 / 5xx / timeout
- [ ] 在 `semantic_reranker.py::rerank` 加 input/output logging，抓兩次呼叫的 request/response diff
- [ ] 檢查 `sop_orchestrator.process_message` 是否依賴 session_id 的 Redis 狀態，若是，兩次呼叫是否共用 session 導致 state 污染
- [ ] 檢查 Redis 快取鍵是否有對 vendor_id + user_id 做正確隔離
- [ ] 若確認是 reranker 服務問題，先處理 `reranker-returning-zero.md`

## 暫行解法

目前無需緊急處理：
- 產線答案路徑：SOP 低分會 fallback 到 knowledge_list 或 no_knowledge_found，不會給錯答案
- Debug 可觀察性：使用者可手動多試幾次觀察分數範圍
