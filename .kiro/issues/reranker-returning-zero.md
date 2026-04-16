# Issue: SemanticReranker 間歇性回傳 0 分

> 建立時間：2026-04-17
> 狀態：**根因已定位 + Hotfix 已上線並驗證**（2026-04-17）
> 優先級：高（影響 retriever 排序品質，可能間接影響產線答案）
> 發現時機：`retriever-similarity-refactor` 重構後手測驗證

---

## 🎯 根因確認（2026-04-17）

**client HTTP timeout (15s) < server 實際處理時間 (25–30s)**。

從 `aichatbot-semantic-model` 容器日誌直接觀察：

```
Batches: 2/2 [00:27<00:00, 13.42s/it]   ← 2 批次共 27 秒
INFO: "POST /rerank HTTP/1.1" 200 OK      ← 最終有成功返回
```

`semantic_reranker.py::rerank` 的 `timeout=15` 在 client 端就斷線，catch 到 exception 回傳 `candidates[:top_k]`（無 `semantic_score`），觸發我之前加的「全 0 防護」。

符合實測觀察：
| 路徑 | 候選數 | batches | 時間 | timeout=15s | 結果 |
|------|-------|---------|------|------------|------|
| SOP | 15 | 1 | ~4s | ✅ | 多數成功 |
| SOP | 15 | 1 | ~14s（邊緣）| ⚠️ | 偶爾失敗 |
| KB | 56 | 2 | ~27s | ❌ 100% 超時 | 全失敗 |

「第一次正常、之後失效」的假設被否定 — SOP 間歇性成功跟批次處理時間在 15s 邊緣擺盪有關；KB 批次大小直接決定必超時。

---

## ✅ Hotfix 已實作（2026-04-17）

### 三層防護

**1. HTTP timeout：15s → 60s**（`semantic_reranker.py`）

```python
rerank_timeout = int(os.getenv("RERANKER_HTTP_TIMEOUT", "60"))
response = requests.post(..., timeout=rerank_timeout)
```

**2. 送 rerank 前兩層過濾**（`base_retriever.py`）：

a) 下限過濾：`vector_similarity < RERANKER_MIN_VECTOR_SIMILARITY`（預設 0.3）直接丟棄
   - 這些低分 vector 項 rerank 後幾乎不可能進 top_k，送進去浪費推論時間
   - keyword_fallback 項目不受下限影響（其 vector_similarity=0 是設計預設值）

b) 上限截斷：若剩餘候選超過 `RERANKER_INPUT_LIMIT`（預設 20），優先保留 keyword_fallback，再以 vector_similarity 補足 vector 項

實測效果：
- KB 56 筆 → 下限砍 46 筆 → 剩 10 筆 → rerank ~3-4s（原 ~27s）
- SOP 15 筆 → 下限砍 8 筆 → 剩 7 筆 → rerank ~2s（原 ~4s）

**3. 全 0 防護（先前已加）**：若 reranker 仍意外全回 0，退回 vector 分支避免 pipeline 崩壞

### 驗證結果

重啟後手測「合約簽署」：

```
向量檢索: 找到 56 個結果
Reranker 截斷: 56 → 20 筆（依 vector_similarity 保留前 20，避免 CPU 推論超時）
Reranker: 已重排序
[Finalize] 計算 5 筆，分數來源: rerank=5, keyword=0, vector=0  ← rerank=5 成功！
```

SOP: `base=0.6103 rerank=0.9994` / KB: `rerank 0.03–0.05`（語義不相關 → 低分合理）。

### 環境變數

已加到 `.env.example` 與 `docker-compose.prod.yml`：
- `RERANKER_INPUT_LIMIT=20` — 送進 reranker 的候選數上限
- `RERANKER_MIN_VECTOR_SIMILARITY=0.3` — vector 下限（過濾不可能進 top_k 的低分）
- `RERANKER_HTTP_TIMEOUT=60` — HTTP client timeout（秒）

---

## 之前的暫行解法（仍保留）

`BaseRetriever._apply_semantic_reranker` 已加入全 0 偵測防護：

- 若 reranker 回傳所有項目 semantic_score == 0，視為服務異常
- 不寫入 rerank_score，直接回傳原始 candidates
- `_finalize_scores` 退回走 vector / keyword 分支（相當於 reranker 失效時的 graceful degradation）

**日誌範例**：
```
⚠️ Reranker 回傳全 0 分（5 筆），視為服務異常，fallback 到原始候選（rerank_score 保持 None）
[Finalize] 計算 56 筆，分數來源: rerank=0, keyword=0, vector=56
```

**測試覆蓋**：
- `test_reranker_all_zero_scores_falls_back_to_original_candidates`
- `test_reranker_mixed_zero_and_nonzero_still_writes_scores`（混合情況不觸發，避免誤傷）
- `test_reranker_empty_candidates_no_crash`

**效果**：
- reranker 失效時，final similarity 從 `0.1 × vector`（約 0.04–0.08）升為 `vector × boost`（約 0.3–0.6）
- 大幅提升門檻通過率，產線不會因 reranker 間歇性失效而誤回兜底回應
- 仍需解決根因（semantic-model 服務為何間歇性回 0），但至少使用者體驗不受影響

---

---

## 症狀

`SemanticReranker.rerank()` 在相同 query + 相同 candidates 的情況下，回傳的 `semantic_score` 會在「高分（接近真實語義相關度）」與「全部 0 分」之間跳動。

## 具體案例

**查詢**：`"合約簽署"`（vendor_id=2）

**Case A - rerank 正常**（某次 chat-test 呼叫）：
| SOP ID | item_name | rerank_score |
|--------|-----------|--------------|
| 655 | 合約簽署流程 | 0.9994 |
| 657 | 合約內容制定方式 | 0.9466 |
| 654 | 合約變更與終止 | 0.0060 |

Rerank 合理：655 完全對應問題，657 相關，654 次要。

**Case B - rerank 全部回 0**（同一查詢，不同時點）：
| SOP ID | item_name | rerank_score |
|--------|-----------|--------------|
| 655 | 合約簽署流程 | 0.0000 |
| 657 | 合約內容制定方式 | 0.0000 |
| 654 | 合約變更與終止 | 0.0000 |

無論 SOP 或 KB 候選，所有項目 rerank_score 一律 0。

## 下游影響

1. **final similarity 計算失真**：
   ```
   similarity = 0.1 × vector_similarity + 0.9 × rerank_score
   ```
   當 rerank = 0，所有候選 final 值只剩 10% 的 vector_similarity（約 0.04–0.08 範圍），全部低於 `SOP_SIMILARITY_THRESHOLD=0.75` 與 `KB_SIMILARITY_THRESHOLD=0.65`。

2. **處理路徑降級**：原本可以走 SOP 或 knowledge 路徑的查詢，在 rerank=0 時 fallback 到 `no_knowledge_found`（兜底回應）。使用者會收到「我目前沒有找到符合您問題的資訊」而非正確答案。

3. **debug_info 誤導**：chat-test 上看到的 `similarity` 欄位會是 0.04–0.08，讓人誤以為是 retriever 排序問題，實際是 reranker 服務問題。

## 程式碼位置

`rag-orchestrator/services/semantic_reranker.py::rerank` (line 56+)：

```python
reranked_ids = [r["id"] for r in result.get("results", [])]
id_to_candidate = {c["id"]: c for c in candidates}
reranked = []
for rid in reranked_ids:
    if rid in id_to_candidate:
        candidate = id_to_candidate[rid]
        score_info = next((r for r in result["results"] if r["id"] == rid), {})
        candidate["semantic_score"] = score_info.get("score", 0)  # ← 這裡 fallback 到 0
        reranked.append(candidate)
```

若 `result["results"]` 中每項的 `score` 欄位缺失或為 0，整批 rerank 就會全 0。

## 疑似根因（待驗證）

1. **semantic-model 服務內部模型加載異常**：bge-reranker-base 模型在容器首次啟動/重啟時可能還沒完全 warm-up，造成前幾次呼叫回 0
2. **HTTP payload 序列化問題**：某些 candidate content 含特殊字元導致 semantic-model 無法解析，回傳空結果
3. **semantic-model 服務超時後的 graceful degradation**：超時時可能回傳空 `results` 陣列或 `score=0`
4. **Batch 大小影響**：當 candidates 數量達某閾值時（如 60+），模型推論失敗後 fallback 為 0
5. **快取污染**：semantic-model 若有自己的結果快取，某個 bad cache entry 會反覆污染同 query
6. **⭐ HTTP client session/連線池污染**（新線索，2026-04-17）：
   三次連續呼叫觀察到**只有第一次 SOP reranker 正常**，第二次起全 0。
   這不符合 warm-up 假設（warm-up 應該是後續變好），反而像：
   - `httpx.Client` 單例在第一次 request 後某個狀態被污染
   - semantic-model 容器內部在首次請求後有 session state 退化
   - Python 的 `use_httpx` flag 在 rerank 間切換
   建議重點排查：`semantic_reranker.py` 是否每次建新 Client，是否有 async context manager 誤用

## 重現步驟

1. 重啟 `aichatbot-semantic-model` 容器：`docker restart aichatbot-semantic-model`
2. 立即跑：`curl -X POST http://localhost:8100/api/v1/message -H "Content-Type: application/json" -d '{"message":"合約簽署","vendor_id":2,"include_debug_info":true}'`
3. 觀察 debug_info 中 SOP 與 KB 候選的 rerank_score
4. 重複 10 次，統計 rerank=0 的比例

### 實測樣本（2026-04-17）

零散觀察（樣本不足，尚不能下結論）：

| 時點 | SOP reranker | KB reranker | 情境 |
|------|--------------|-------------|------|
| chat-test UI 手測 | ✅ 0.9994 | （未觀察）| 使用者原始操作 |
| curl #1（重啟後）| ❌ 全 0 | ❌ 全 0 | 首次 |
| curl #2（再重啟後）| ✅ 0.9994 | （無資料）| 首次 |
| 3-probe call 1 | ✅ 0.9994 | ❌ 全 0 | 首次 |
| 3-probe call 2, 3 | ❌ 全 0 | ❌ 全 0 | 後續 |

**觀察（待驗證，不可當結論）**：
- 「剛重啟後第一次一定正常」**已被自身資料反駁**（curl #1 剛重啟就失效）
- KB 成功率遠低於 SOP（可能與 batch 大小有關：KB 56 筆 vs SOP 15 筆）
- SOP 有時正常有時失效，pattern 未知

### 待執行的系統化驗證

跑腳本 30 次，統計：
- [ ] SOP reranker 成功率（rerank_score 非全 0 的比例）
- [ ] KB reranker 成功率
- [ ] 成功率 vs batch size（控制 top_k 調整 batch）
- [ ] 並發呼叫（asyncio.gather）vs 序列呼叫的成功率差異
- [ ] semantic-model 容器同期的日誌有無 error/warning/timeout

## 調查建議

- [ ] 抓 `aichatbot-semantic-model` 容器日誌：是否有 exception、OOM、model load error
- [ ] 直接呼叫 semantic-model HTTP API 繞過 rag-orchestrator：`curl -X POST http://localhost:8001/rerank -d '{...}'` 驗證是否 reranker 服務本身就回 0
- [ ] 在 `semantic_reranker.py::rerank` 加 logging：印出 `response.json()` 的原始內容，確認 `results` 陣列形狀
- [ ] 檢查 semantic-model 容器是否有 warm-up 機制（startup probe）
- [ ] 考慮加 retry：若 rerank 全 0 且 candidates 非空，重試一次

## 暫行解法

### 選項 1：Retrieval 層 fallback（推薦）

`BaseRetriever._apply_semantic_reranker`：
```python
reranked = self.semantic_reranker.rerank(query, prepared, top_k=top_k)

# 防護：若 rerank 全 0，視同 rerank 失敗，回傳 candidates（不寫 rerank_score）
if reranked and all(item.get('semantic_score', 0) == 0 for item in reranked):
    print("⚠️ Reranker 全回 0，視為失敗，fallback 到 pre-rerank 候選")
    return candidates  # 原始候選，rerank_score 仍為 None → finalize 走 vector/keyword 分支

for item in reranked:
    item['rerank_score'] = item.get('semantic_score', 0)
return reranked
```

### 選項 2：semantic-model 加 warm-up

容器啟動後先跑一次 dummy rerank，確保模型已 warm-up。

### 選項 3：重試

若 rerank 回全 0，重試一次；仍 0 則 fallback。

## 關聯

- 此問題可能是 `sop-candidates-intermittent-empty.md` 的上游根因
- 與 `retriever-similarity-refactor` 重構無關（重構前一樣有此問題，只是沒被發現）
- 若要真正解決，需 semantic-model 容器端的問題排查
