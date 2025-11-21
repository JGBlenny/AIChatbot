# 知識匯入語意去重功能 - 完整修復文檔

## 📋 問題總覽

知識匯入功能在語意去重階段失敗，錯誤訊息：
```
function check_knowledge_exists_by_similarity(vector, unknown) does not exist
column ts.question_embedding does not exist
```

## 🔍 根本原因分析

### 問題 1：缺失的資料庫函數
Migration 29 和 32 中定義的相似度檢查函數未整合到資料庫初始化腳本：
- `find_similar_knowledge()` - 查詢知識庫中的相似知識
- `find_similar_knowledge_candidate()` - 查詢審核佇列中的相似知識
- `find_similar_test_scenario()` - 查詢測試情境中的相似問題
- `check_knowledge_exists_by_similarity()` - 綜合查詢函數

### 問題 2：缺失的資料表欄位
- `ai_generated_knowledge_candidates.question_embedding` - 缺失
- `test_scenarios.question_embedding` - 缺失

### 問題 3：程式碼類型轉換問題
SQL 查詢中缺少明確的參數類型轉換。

## ✅ 完整修復方案

### 修復 1：添加相似度檢查函數

**檔案**: `database/fixes/add_similarity_check_functions.sql`

```sql
-- 1. find_similar_knowledge - 查詢知識庫
CREATE OR REPLACE FUNCTION find_similar_knowledge(
    p_question_embedding vector(1536),
    p_similarity_threshold DECIMAL DEFAULT 0.85
)
RETURNS TABLE (...)

-- 2. find_similar_knowledge_candidate - 查詢審核佇列
CREATE OR REPLACE FUNCTION find_similar_knowledge_candidate(
    p_question_embedding vector(1536),
    p_similarity_threshold DECIMAL DEFAULT 0.85
)
RETURNS TABLE (...)

-- 3. find_similar_test_scenario - 查詢測試情境
CREATE OR REPLACE FUNCTION find_similar_test_scenario(
    p_question_embedding vector(1536),
    p_similarity_threshold DECIMAL DEFAULT 0.85
)
RETURNS TABLE (...)

-- 4. check_knowledge_exists_by_similarity - 綜合查詢
CREATE OR REPLACE FUNCTION check_knowledge_exists_by_similarity(
    p_question_embedding vector(1536),
    p_similarity_threshold DECIMAL DEFAULT 0.85
)
RETURNS TABLE (...)
```

**執行命令**:
```bash
docker-compose exec -T postgres psql -U aichatbot -d aichatbot_admin < database/fixes/add_similarity_check_functions.sql
```

### 修復 2：添加 question_embedding 欄位

**檔案**: `database/fixes/add_test_scenario_embedding_column.sql`

```sql
-- 為 test_scenarios 添加 question_embedding 欄位
ALTER TABLE test_scenarios
ADD COLUMN IF NOT EXISTS question_embedding vector(1536);

-- 添加向量索引
CREATE INDEX IF NOT EXISTS idx_test_scenarios_question_embedding
ON test_scenarios
USING ivfflat (question_embedding vector_cosine_ops)
WITH (lists = 100);
```

**執行命令**:
```bash
docker-compose exec -T postgres psql -U aichatbot -d aichatbot_admin < database/fixes/add_test_scenario_embedding_column.sql
```

### 修復 3：程式碼類型轉換

**檔案**: `rag-orchestrator/services/knowledge_import_service.py:618`

```python
# 修改前
result = await conn.fetchrow("""
    SELECT * FROM check_knowledge_exists_by_similarity($1::vector, $2)
""", vector_str, threshold)

# 修改後
result = await conn.fetchrow("""
    SELECT * FROM check_knowledge_exists_by_similarity($1::vector, $2::DECIMAL)
""", vector_str, threshold)
```

### 修復 4：生成測試情境 Embedding

**檔案**: `scripts/generate_test_scenario_embeddings.py`

**執行命令**:
```bash
python3 scripts/generate_test_scenario_embeddings.py
```

這個腳本會：
1. 連接資料庫
2. 查找所有缺少 embedding 的測試情境
3. 使用 OpenAI API 生成向量嵌入
4. 更新資料庫

## 🧪 驗證

執行驗證腳本確認所有功能正常：

```bash
python3 scripts/verify_similarity_functions.py
```

預期輸出：
```
✅ 所有函數和欄位都已就緒
✅ 知識匯入的語意去重功能可以正常使用
```

## 📊 功能說明

### 語意去重流程

知識匯入時會執行兩階段去重：

#### 階段 1：文字精確匹配去重
檔案位置: `knowledge_import_service.py:542-578`

檢查三個地方：
1. `knowledge_base` - 正式知識庫
2. `ai_generated_knowledge_candidates` - 審核佇列
3. `test_scenarios` - 測試情境

```sql
SELECT COUNT(*) FROM (
    SELECT 1 FROM knowledge_base
    WHERE question_summary = $1 AND answer = $2
    UNION ALL
    SELECT 1 FROM ai_generated_knowledge_candidates
    WHERE question = $1 AND generated_answer = $2
    UNION ALL
    SELECT 1 FROM test_scenarios
    WHERE test_question = $1
) AS combined
```

#### 階段 2：語意相似度去重
檔案位置: `knowledge_import_service.py:580-638`

使用向量相似度（閾值：0.85）檢查：
1. 將問題轉換為 1536 維向量
2. 調用 `check_knowledge_exists_by_similarity()` 函數
3. 查詢三個表中相似度 >= 0.85 的知識
4. 跳過相似的知識

```python
result = await conn.fetchrow("""
    SELECT * FROM check_knowledge_exists_by_similarity($1::vector, $2::DECIMAL)
""", vector_str, threshold)
```

### 相似度閾值說明

| 相似度範圍 | 說明 | 處理方式 |
|----------|------|---------|
| 1.0 | 完全相同 | 視為重複，跳過 |
| 0.85-0.99 | 高度相似 | 視為重複，跳過 |
| < 0.85 | 不相似 | 保留，繼續匯入 |

## 🎯 使用指南

### 1. 知識匯入流程

正常的知識匯入會自動執行去重：

```python
# 1. 解析檔案
knowledge_list = await self._parse_file(file_path, file_type)

# 2. 文字去重（精確匹配）
knowledge_list = await self._deduplicate_exact_match(knowledge_list)

# 3. 生成問題摘要（LLM）
await self._generate_question_summaries(knowledge_list)

# 4. 生成向量嵌入
await self._generate_embeddings(knowledge_list)

# 5. 語意去重（向量相似度）
knowledge_list = await self._deduplicate_by_similarity(knowledge_list)

# 6. 匯入審核佇列
await self._import_to_review_queue(knowledge_list)
```

### 2. 手動為測試情境生成 Embedding

如果新增測試情境後沒有自動生成 embedding，可手動執行：

```bash
python3 scripts/generate_test_scenario_embeddings.py
```

### 3. 查詢相似知識

可直接使用 SQL 查詢相似知識：

```sql
-- 查詢知識庫中的相似知識
SELECT * FROM find_similar_knowledge(
    '[0.1,0.2,...]'::vector(1536),
    0.85
);

-- 綜合查詢（知識庫 + 審核佇列 + 測試情境）
SELECT * FROM check_knowledge_exists_by_similarity(
    '[0.1,0.2,...]'::vector(1536),
    0.85
);
```

## 📁 相關檔案清單

### 資料庫修復腳本
- `database/fixes/add_similarity_check_functions.sql` - 添加相似度檢查函數
- `database/fixes/add_test_scenario_embedding_column.sql` - 添加 question_embedding 欄位
- `database/fixes/fix_test_scenario_similarity.sql` - 臨時禁用測試情境向量檢查（已被完整方案取代）

### Python 腳本
- `scripts/generate_test_scenario_embeddings.py` - 生成測試情境的向量嵌入
- `scripts/verify_similarity_functions.py` - 驗證相似度功能

### 程式碼修改
- `rag-orchestrator/services/knowledge_import_service.py:618` - 修復類型轉換

### 文檔
- `docs/KNOWLEDGE_IMPORT_SIMILARITY_FIX.md` - 本文檔

## 🔄 未來維護

### 添加新的測試情境時

1. **選項 A：自動生成 embedding（推薦）**
   在插入測試情境時自動生成 embedding：

   ```python
   # 生成 embedding
   response = await openai_client.embeddings.create(
       model="text-embedding-3-small",
       input=test_question
   )
   embedding = response.data[0].embedding

   # 插入時包含 embedding
   await conn.execute("""
       INSERT INTO test_scenarios (test_question, question_embedding, ...)
       VALUES ($1, $2::vector, ...)
   """, test_question, '[' + ','.join(str(x) for x in embedding) + ']', ...)
   ```

2. **選項 B：批量生成（適用於大量數據）**
   ```bash
   python3 scripts/generate_test_scenario_embeddings.py
   ```

### 監控建議

定期檢查 embedding 覆蓋率：

```sql
-- 檢查各表的 embedding 統計
SELECT
    'knowledge_base' as table_name,
    COUNT(*) as total,
    COUNT(embedding) as with_embedding,
    ROUND(COUNT(embedding)::numeric / COUNT(*) * 100, 2) as coverage_pct
FROM knowledge_base
UNION ALL
SELECT
    'ai_generated_knowledge_candidates',
    COUNT(*),
    COUNT(question_embedding),
    ROUND(COUNT(question_embedding)::numeric / COUNT(*) * 100, 2)
FROM ai_generated_knowledge_candidates
UNION ALL
SELECT
    'test_scenarios',
    COUNT(*),
    COUNT(question_embedding),
    ROUND(COUNT(question_embedding)::numeric / COUNT(*) * 100, 2)
FROM test_scenarios;
```

### 性能優化

如果相似度查詢變慢：

1. **檢查索引**
   ```sql
   -- 確認向量索引存在
   SELECT indexname, indexdef
   FROM pg_indexes
   WHERE tablename IN (
       'knowledge_base',
       'ai_generated_knowledge_candidates',
       'test_scenarios'
   )
   AND indexname LIKE '%embedding%';
   ```

2. **調整 IVFFlat 參數**
   ```sql
   -- 重建索引並調整列表數量
   DROP INDEX idx_test_scenarios_question_embedding;
   CREATE INDEX idx_test_scenarios_question_embedding
   ON test_scenarios
   USING ivfflat (question_embedding vector_cosine_ops)
   WITH (lists = 200);  -- 增加列表數量
   ```

## 🎉 總結

### 修復成果
✅ 4 個相似度檢查函數已創建
✅ 3 個表的 embedding 欄位已補齊
✅ 程式碼類型轉換已修復
✅ 測試情境 embedding 已生成
✅ 所有服務已重啟並正常運行

### 功能狀態
- ✅ 文字精確匹配去重：正常運作
- ✅ 語意相似度去重：正常運作
- ✅ 跨表去重檢查：正常運作（知識庫 + 審核佇列 + 測試情境）

### 測試建議
1. 訪問 `http://localhost/` 知識管理後台
2. 測試知識匯入功能
3. 上傳包含重複或相似知識的檔案
4. 確認去重功能正常運作

---

**文檔版本**: 1.0
**最後更新**: 2025-01-15
**修復完成**: ✅ 完整方案已實施
