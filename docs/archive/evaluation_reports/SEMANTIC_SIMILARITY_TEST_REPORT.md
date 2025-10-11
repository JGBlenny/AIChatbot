# 語義相似度功能測試報告

## 功能概述

實作了針對 `unclear_questions` 表的語義相似度去重功能，解決了您提出的問題：

> **用戶問題**：「如果是 我可以養寵物嗎 我想養寵物 之類語意有些微差異的情況呢」

**解決方案**：使用 OpenAI Embeddings 進行語義相似度比對，當新問題與已存在問題的相似度超過閾值（預設 0.85）時，不建立新記錄，而是累加已存在問題的頻率。

## 實作內容

### 1. 資料庫層（Database Migrations）

#### 檔案：`database/migrations/11-add-semantic-similarity-to-unclear-questions.sql`

**變更內容：**
- 新增 `question_embedding vector(1536)` 欄位儲存問題的向量表示
- 建立 `ivfflat` 索引以加速向量相似度搜尋
- 建立函數 `find_similar_unclear_question` 尋找語義相似的問題
- 建立函數 `record_unclear_question_with_semantics` 進行語義去重
- 建立視圖 `v_unclear_questions_with_clusters` 展示問題聚類

**關鍵函數簽章：**
```sql
CREATE FUNCTION record_unclear_question_with_semantics(
    p_question TEXT,
    p_question_embedding vector(1536),
    p_intent_guess VARCHAR(100) DEFAULT NULL,
    p_similarity_threshold DECIMAL DEFAULT 0.85
)
RETURNS TABLE (
    unclear_question_id INTEGER,
    is_new_question BOOLEAN,
    matched_similar_question TEXT,
    sim_score DECIMAL,
    current_frequency INTEGER
)
```

**邏輯流程：**
1. 檢查是否有精確文字匹配 → 有則更新頻率
2. 檢查是否有語義相似問題（使用向量相似度）→ 有則更新頻率
3. 若都沒有，建立新記錄

### 2. 應用層（RAG Orchestrator）

#### 檔案：`rag-orchestrator/services/unclear_question_manager.py`

**變更內容：**
- 新增 `_get_embedding(text)` 方法呼叫 Embedding API
- 更新 `record_unclear_question()` 方法使用語義去重
- 新增 `_record_without_semantics()` 作為 fallback 方案

**關鍵程式碼：**
```python
async def record_unclear_question(
    self,
    question: str,
    ...
    semantic_similarity_threshold: float = 0.85
) -> int:
    # 1. 生成問題的向量表示
    question_embedding = await self._get_embedding(question)

    # 2. 使用資料庫函數進行語義去重
    result = await conn.fetchrow("""
        SELECT * FROM record_unclear_question_with_semantics(
            $1::TEXT, $2::vector, $3::VARCHAR(100), $4::DECIMAL
        )
    """, question, vector_str, intent_type, semantic_similarity_threshold)

    # 3. 記錄結果（新問題/精確匹配/語義匹配）
    if is_new:
        print(f"✅ 記錄新的未釐清問題 (ID: {unclear_question_id})")
    elif matched_question == question:
        print(f"♻️  精確匹配已存在問題 (ID: {unclear_question_id}), 頻率: {frequency}")
    else:
        print(f"🔗 語義匹配已存在問題 (ID: {unclear_question_id})")
        print(f"   新問題: {question}")
        print(f"   相似問題: {matched_question}")
        print(f"   相似度: {sim_score:.4f}, 頻率: {frequency}")
```

## 測試結果

### 測試環境
- RAG Orchestrator: `docker-compose` 部署
- PostgreSQL + pgvector: v16
- Embedding API: OpenAI text-embedding-ada-002 (1536 維)
- 測試日期: 2025-10-11

### 測試案例

| # | 測試問題 | 匹配類型 | 相似問題 | 相似度 | unclear_question_id | 頻率 | 結果 |
|---|---------|---------|---------|--------|-------------------|------|------|
| 1 | 我可以養寵物嗎 | 新問題 | - | - | 23 | 1 | ✅ 通過 |
| 2 | 我想養寵物 | 語義匹配 | 我可以養寵物嗎 | 0.8549 | 23 | 2 | ✅ 通過 |
| 3 | 我可以養寵物嗎 | 精確匹配 | 我可以養寵物嗎 | 1.0000 | 23 | 3 | ✅ 通過 |
| 4 | 能養寵物嗎 | 語義匹配 | 我可以養寵物嗎 | 0.8973 | 23 | 4 | ✅ 通過 |

### 日誌輸出

```
測試 1: 新問題
✅ 記錄新的未釐清問題 (ID: 23): 我可以養寵物嗎

測試 2: 語義相似問題
🔗 語義匹配已存在問題 (ID: 23)
   新問題: 我想養寵物
   相似問題: 我可以養寵物嗎
   相似度: 0.8549, 頻率: 2

測試 3: 精確匹配
♻️  精確匹配已存在問題 (ID: 23), 頻率: 3

測試 4: 另一個語義相似變體
🔗 語義匹配已存在問題 (ID: 23)
   新問題: 能養寵物嗎
   相似問題: 我可以養寵物嗎
   相似度: 0.8973, 頻率: 4
```

### 資料庫驗證

```sql
SELECT id, question, frequency, question_embedding IS NOT NULL as has_embedding
FROM unclear_questions
WHERE id = 23;

 id |    question    | frequency | has_embedding
----+----------------+-----------+---------------
 23 | 我可以養寵物嗎 |         4 | t
```

**結論：**
- ✅ 只建立了 1 條記錄（ID: 23）
- ✅ 4 個語義相似的問題都正確累加到同一條記錄
- ✅ Embedding 成功儲存
- ✅ 語義相似度計算準確（0.8549、0.8973 都超過 0.85 閾值）

## 效能考量

### 1. Embedding API 呼叫
- **頻率**：每次記錄 unclear_question 時呼叫一次
- **延遲**：約 200-500ms（視 OpenAI API 回應時間）
- **快取**：Embedding API 本身有 Redis 快取（15分鐘）

### 2. 向量相似度搜尋
- **索引類型**：ivfflat（近似最近鄰搜尋）
- **查詢複雜度**：O(log n) 近似
- **索引參數**：`lists = 100`（適合中小型資料集）

### 3. Fallback 機制
當 Embedding API 失敗時，自動回退到精確文字匹配模式，確保系統可用性。

## 配置參數

### 相似度閾值
```python
semantic_similarity_threshold: float = 0.85  # 預設值
```

**建議值：**
- `0.90+`：嚴格模式，只匹配非常相似的問題
- `0.85`：平衡模式（預設），適合大多數情況
- `0.80-`：寬鬆模式，可能產生誤匹配

### 調整方式
在呼叫 `record_unclear_question()` 時傳入參數：
```python
await unclear_manager.record_unclear_question(
    question="我可以養寵物嗎",
    semantic_similarity_threshold=0.90  # 自訂閾值
)
```

## 後續改進建議

### 1. 監控與分析
- 建立 dashboard 展示語義匹配率
- 追蹤誤匹配案例（false positives）
- 分析最佳閾值

### 2. 批次處理
對於歷史資料，可建立批次腳本：
```sql
-- 為舊記錄生成 embedding
UPDATE unclear_questions
SET question_embedding = (
    SELECT embedding FROM get_embedding(question)
)
WHERE question_embedding IS NULL;
```

### 3. 聚類視圖
使用 `v_unclear_questions_with_clusters` 視圖找出語義重複的問題集群：
```sql
SELECT q1_text, q2_text, similarity, combined_frequency
FROM v_unclear_questions_with_clusters
WHERE similarity >= 0.85
ORDER BY combined_frequency DESC
LIMIT 20;
```

## 相關檔案

### 新增檔案
- `database/migrations/11-add-semantic-similarity-to-unclear-questions.sql`
- `database/migrations/11b-fix-semantic-function.sql`
- `SEMANTIC_SIMILARITY_TEST_REPORT.md`（本文件）

### 修改檔案
- `rag-orchestrator/services/unclear_question_manager.py`

### 相依服務
- Embedding API (`http://embedding-api:5000/api/v1/embeddings`)
- PostgreSQL + pgvector extension

## 總結

✅ **功能已完整實作並測試通過**

語義相似度功能成功解決了原始問題：
- 「我可以養寵物嗎」、「我想養寵物」、「能養寵物嗎」等語義相似的問題現在會正確地累加到同一個 unclear_question 記錄
- 系統會自動識別相似度超過 0.85 的問題並合併頻率
- 保留了精確匹配和 fallback 機制，確保系統穩定性

**測試統計：**
- ✅ 4/4 測試案例通過
- ✅ 精確匹配正常
- ✅ 語義匹配正常（相似度 0.8549、0.8973）
- ✅ 頻率累加正確（1 → 2 → 3 → 4）
- ✅ Embedding 儲存成功

---
**測試執行者**：Claude
**測試日期**：2025-10-11
**版本**：v1.0.0
