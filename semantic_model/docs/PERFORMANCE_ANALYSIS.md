# 語義模型性能分析

## 效能測試結果

### 本地測試（CPU）
| 操作 | 耗時 | 說明 |
|------|------|------|
| 模型載入 | 9.71 秒 | 只需載入一次 |
| 20 個候選評分 | 1.65 秒 | 包含「電費帳單」查詢 |
| 20 個候選評分 | 0.43 秒 | 包含「我要報修」查詢 |
| 20 個候選評分 | 0.18 秒 | 包含「租金多少」查詢 |

**平均延遲：0.75 秒/查詢（20個候選）**

### 預期生產環境效能

| 環境 | 候選數 | 預期延遲 | 吞吐量 |
|------|--------|----------|---------|
| CPU (2核) | 20 | 500-800ms | 1-2 QPS |
| CPU (4核) | 50 | 800-1200ms | 2-4 QPS |
| GPU (T4) | 100 | 100-200ms | 20-50 QPS |
| GPU (V100) | 200 | 50-100ms | 50-100 QPS |

## 架構優化方案

### 方案 A：全量語義（不建議）
```
用戶查詢 → 語義模型 → 1274個知識點評分 → 返回
```
- ❌ 延遲：5-10 秒
- ❌ 成本：高
- ✅ 準確度：最高

### 方案 B：兩階段檢索（推薦）
```
用戶查詢 → 向量檢索(快) → Top 50 → 語義重排(準) → Top 5
```
- ✅ 延遲：200-500ms
- ✅ 成本：中等
- ✅ 準確度：高

### 方案 C：智能路由（最優）
```
         ┌─→ 簡單查詢 → 向量檢索 → 返回
用戶查詢 ┤
         └─→ 複雜查詢 → 向量檢索 → 語義重排 → 返回
```
- ✅ 延遲：簡單 <100ms，複雜 200-500ms
- ✅ 成本：低
- ✅ 準確度：按需調整

## 實作建議

### 1. 快取策略
```python
# 快取熱門查詢結果
@lru_cache(maxsize=1000)
def semantic_search_cached(query_hash):
    return semantic_model.search(query)

# 使用 Redis 快取
def search_with_cache(query):
    cache_key = f"semantic:{hash(query)}"
    cached = redis.get(cache_key)
    if cached:
        return json.loads(cached)

    result = semantic_model.search(query)
    redis.setex(cache_key, 3600, json.dumps(result))
    return result
```

### 2. 批次處理
```python
# 批次處理多個查詢
async def batch_search(queries: List[str]):
    # 並行處理
    tasks = [semantic_search(q) for q in queries]
    results = await asyncio.gather(*tasks)
    return results
```

### 3. 智能降級
```python
def search_with_fallback(query, timeout=1.0):
    try:
        # 嘗試語義模型（設定超時）
        return semantic_search(query, timeout=timeout)
    except TimeoutError:
        # 降級到向量檢索
        logger.warning(f"Semantic search timeout, fallback to vector")
        return vector_search(query)
```

## 性能優化技巧

### 1. 預篩選優化
```python
# 只對高相似度候選使用語義模型
candidates = vector_search(query, top_k=100)
high_score_candidates = [c for c in candidates if c.score > 0.7]

if len(high_score_candidates) > 0:
    # 只重排高分候選
    return semantic_rerank(high_score_candidates[:20])
else:
    # 沒有高分，使用前 20 個
    return semantic_rerank(candidates[:20])
```

### 2. 異步處理
```python
# 主系統 API 整合
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # 並行執行
    vector_task = vector_search_async(request.query)
    semantic_task = semantic_search_async(request.query, top_k=5)

    # 等待兩個結果
    vector_results, semantic_results = await asyncio.gather(
        vector_task, semantic_task
    )

    # 合併結果
    return merge_results(vector_results, semantic_results)
```

### 3. 模型優化
```python
# 使用量化模型（犧牲少量準確度換取速度）
model = CrossEncoder('BAAI/bge-reranker-base')
model.model = torch.quantization.quantize_dynamic(
    model.model, {torch.nn.Linear}, dtype=torch.qint8
)
# 速度提升 2-4 倍，準確度降低 <1%
```

## 建議部署架構

```yaml
# docker-compose.yml 優化配置
services:
  semantic-model:
    image: semantic-model:latest
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
    environment:
      - OMP_NUM_THREADS=4  # 優化 CPU 使用
      - MKL_NUM_THREADS=4
      - BATCH_SIZE=50       # 批次大小
      - CACHE_SIZE=1000     # 快取大小
```

## 監控指標

需要監控的關鍵指標：
1. **P50/P90/P99 延遲**
2. **QPS（每秒查詢數）**
3. **快取命中率**
4. **CPU/記憶體使用率**
5. **降級次數**

## 結論

### 回答您的問題：

1. **是否所有對話都使用語義模型？**
   - 不需要，建議使用智能路由
   - 簡單查詢用向量，複雜查詢用語義

2. **會慢很多嗎？**
   - 兩階段檢索：增加 200-500ms（可接受）
   - 使用快取後：熱門查詢 <100ms
   - GPU 加速：可達到 50-100ms

### 最佳實踐：
```python
# 根據查詢類型決定策略
if query_type == "form_trigger":  # 表單觸發類
    return semantic_search(query)  # 需要高準確度
elif query_type == "faq":  # 常見問題
    return cached_search(query)  # 使用快取
else:  # 一般查詢
    return vector_search(query)  # 快速返回
```