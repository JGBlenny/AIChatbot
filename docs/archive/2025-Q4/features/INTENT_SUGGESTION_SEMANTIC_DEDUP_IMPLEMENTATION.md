# 🧬 意圖建議語義相似度去重實現報告

**實現日期**: 2025-10-22
**功能名稱**: 意圖建議語義相似度檢查（Semantic Similarity Deduplication for Intent Suggestions）
**閾值**: 0.80
**狀態**: ✅ 已完成

---

## 📋 需求概述

### 背景問題
在系統運作過程中，當使用者提出的問題無法分類到現有意圖時，系統會自動建議新增意圖。然而，僅依靠**字串完全匹配**無法有效防止語義相似的重複建議：

```
範例：
- 建議 A: "租金繳納時間"
- 建議 B: "租金何時要繳" （語義相似，但字串不同）
```

原有的去重機制只能檢測：
1. 完全相同的意圖名稱
2. 完全相同的觸發問題

導致大量語義相似的建議堆積在審核佇列中。

### 解決方案
實現基於 **pgvector 餘弦相似度**的語義去重檢查，閾值設定為 **0.80**。

---

## 🎯 實現功能

### 1. 資料庫層級

#### 新增欄位
在 `suggested_intents` 表新增 `suggested_embedding` 欄位：

```sql
-- Migration: 08-add-suggested-embedding-column.sql
ALTER TABLE suggested_intents
ADD COLUMN IF NOT EXISTS suggested_embedding vector(1536);

COMMENT ON COLUMN suggested_intents.suggested_embedding IS
'建議意圖的向量表示（1536維），用於語義相似度去重檢查（閾值 0.80）';
```

**欄位說明**:
- 類型: `vector(1536)` （OpenAI text-embedding-ada-002 模型維度）
- 用途: 儲存建議意圖名稱的 embedding
- 索引: 待資料量達到 100+ 筆後建立 ivfflat/hnsw 索引

#### 相似度查詢
使用 pgvector 的餘弦相似度運算子：

```sql
SELECT
    id, suggested_name, frequency,
    1 - (suggested_embedding <=> %s::vector) as similarity
FROM suggested_intents
WHERE suggested_embedding IS NOT NULL
  AND status = 'pending'
  AND 1 - (suggested_embedding <=> %s::vector) >= 0.80
ORDER BY similarity DESC
LIMIT 1;
```

**說明**:
- `<=>`: pgvector 餘弦距離運算子（cosine distance）
- `1 - cosine_distance = cosine_similarity`
- 只檢查 `status = 'pending'` 的建議（已審核的不納入比對）

---

### 2. 應用層級

#### IntentSuggestionEngine 更新

**檔案**: `rag-orchestrator/services/intent_suggestion_engine.py`

##### 2.1 新增依賴

```python
import asyncio
from .embedding_utils import get_embedding_client
```

##### 2.2 初始化配置

```python
def __init__(self):
    # Embedding 客戶端
    self.embedding_client = get_embedding_client()

    # 語義相似度閾值（從環境變數讀取）
    self.semantic_similarity_threshold = float(
        os.getenv("INTENT_SUGGESTION_SIMILARITY_THRESHOLD", "0.80")
    )
```

##### 2.3 新增方法: `check_semantic_duplicates()`

```python
def check_semantic_duplicates(
    self,
    suggested_name: str,
    embedding: List[float]
) -> Optional[Dict[str, Any]]:
    """
    檢查是否有語義相似的建議意圖（閾值 0.80）

    Returns:
        如果找到相似建議，返回該建議的資訊字典；否則返回 None
    """
```

**功能**:
- 使用 pgvector 查詢語義相似的 pending 建議
- 返回最相似的一筆建議（如果相似度 ≥ 0.80）
- 詳細日誌輸出（建議名稱、相似度、頻率）

##### 2.4 更新方法: `record_suggestion()`

**新增流程**:

```python
def record_suggestion(...):
    # 1. 生成 embedding
    embedding = loop.run_until_complete(
        self.embedding_client.get_embedding(suggested['name'])
    )

    # 2. 檢查語義重複
    if embedding:
        similar_suggestion = self.check_semantic_duplicates(
            suggested['name'],
            embedding
        )

        if similar_suggestion:
            # 3. 發現重複：更新現有建議的頻率
            UPDATE suggested_intents
            SET frequency = frequency + 1,
                last_suggested_at = CURRENT_TIMESTAMP
            WHERE id = similar_suggestion['id']

            return similar_suggestion['id']

    # 4. 無重複：插入新建議（含 embedding）
    INSERT INTO suggested_intents (..., suggested_embedding)
    VALUES (..., embedding_str::vector)
```

**關鍵邏輯**:
1. **生成 embedding**: 使用 EmbeddingClient 生成意圖名稱的向量
2. **檢查重複**: 呼叫 `check_semantic_duplicates()` 查詢相似建議
3. **更新頻率**: 如果發現相似建議（≥ 0.80），更新其頻率而非新增
4. **插入新建議**: 如果無相似建議，插入新記錄並儲存 embedding

---

### 3. 環境變數配置

#### 新增變數

**檔案**: `.env`

```bash
# ==================== 意圖建議引擎配置 ====================
INTENT_SUGGESTION_SIMILARITY_THRESHOLD=0.80  # 語義相似度閾值（判斷建議意圖是否重複）
```

**說明**:
- **預設值**: `0.80` （推薦範圍 0.75-0.85）
- **調整建議**:
  - 降低閾值 (如 0.75): 提高去重靈敏度，更容易判定為重複
  - 提高閾值 (如 0.85): 降低去重靈敏度，僅非常相似的才判定為重複

#### 文檔更新

**檔案**: `docs/guides/ENVIRONMENT_VARIABLES.md`

新增變數說明：

```markdown
| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `INTENT_SUGGESTION_SIMILARITY_THRESHOLD` | 🆕 語義相似度去重閾值 | `0.80` | ❌ |

**說明**：
- 新建議與現有pending建議相似度 ≥ 0.80 時，更新頻率而非新增重複建議
- 使用 pgvector 餘弦相似度比對 `suggested_embedding` 欄位
```

---

## 🔬 技術細節

### Embedding 生成

**使用模型**: OpenAI `text-embedding-ada-002`
**維度**: 1536
**API 端點**: `http://embedding-api:5000/api/v1/embeddings`

**生成流程**:
```python
# 使用 asyncio 執行異步 embedding 生成
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
embedding = loop.run_until_complete(
    self.embedding_client.get_embedding(suggested['name'], verbose=False)
)
loop.close()
```

**容錯處理**:
- 如果 embedding 生成失敗，系統會記錄警告並繼續執行
- 無 embedding 的建議仍會被儲存，但無法進行語義去重

### 相似度計算

**使用公式**: 餘弦相似度（Cosine Similarity）

```
similarity = 1 - cosine_distance
           = 1 - (1 - cos(θ))
           = cos(θ)
```

其中 θ 是兩個向量之間的夾角。

**閾值解釋**:
- `similarity = 1.00`: 完全相同（0°）
- `similarity = 0.80`: 高度相似（約 36.87°）
- `similarity = 0.50`: 中等相似（60°）
- `similarity = 0.00`: 正交（90°）

### 性能考量

**查詢優化**:
1. **WHERE 過濾**: 只查詢 `status = 'pending'` 的建議
2. **索引建議**: 當資料量達到 100+ 筆後，建立 ivfflat 或 hnsw 索引

```sql
-- HNSW 索引（適合小數據集，精確度高）
CREATE INDEX idx_suggested_intents_embedding
ON suggested_intents USING hnsw (suggested_embedding vector_cosine_ops);

-- IVFFlat 索引（適合大數據集，速度快）
CREATE INDEX idx_suggested_intents_embedding
ON suggested_intents USING ivfflat (suggested_embedding vector_cosine_ops)
WITH (lists = 100);
```

**查詢效能**:
- 無索引: O(n) 線性掃描（資料量 < 100 筆時可接受）
- 有索引: O(log n) 近似查詢（資料量 > 100 筆時建議使用）

---

## 📊 日誌輸出

### 成功去重範例

```
🧬 生成意圖名稱 embedding: 租金何時要繳
🔍 發現語義相似的建議意圖:
   建議名稱: 租金繳納時間 (ID: 42)
   相似度: 0.8745 (閾值: 0.80)
   頻率: 3
🔄 發現語義相似建議，更新頻率: 租金繳納時間 (ID: 42)
✅ 語義相似建議頻率已更新: 租金繳納時間 (ID: 42, 新頻率: 4)
```

### 無重複建議範例

```
🧬 生成意圖名稱 embedding: 寵物飼養規定
✅ 未發現語義相似的建議（閾值: 0.80）
✅ 記錄新建議意圖（含 embedding）: 寵物飼養規定 (ID: 58)
```

### 失敗容錯範例

```
🧬 生成意圖名稱 embedding: 退租流程
⚠️ Embedding 生成失敗，將繼續執行（不進行語義去重）
✅ 記錄新建議意圖（無 embedding）: 退租流程 (ID: 59)
   ⚠️ 建議：檢查 embedding API 是否正常運作
```

---

## 🧪 測試建議

### 手動測試步驟

1. **建立第一個建議**:
```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我想知道租金何時要繳？",
    "vendor_id": 1,
    "user_role": "customer"
  }'
```

2. **建立語義相似的建議**（應該被去重）:
```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "請問租金繳納時間是什麼時候？",
    "vendor_id": 1,
    "user_role": "customer"
  }'
```

3. **檢查資料庫**:
```sql
SELECT
    id,
    suggested_name,
    frequency,
    1 - (suggested_embedding <=> (
        SELECT suggested_embedding
        FROM suggested_intents
        WHERE id = [第一筆ID]
    )) as similarity
FROM suggested_intents
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 5;
```

### 預期結果

- ✅ 第二次建議應該更新第一筆建議的頻率（`frequency = 2`）
- ✅ 不應該產生新的建議記錄
- ✅ 日誌中顯示相似度 ≥ 0.80

---

## 📁 變更檔案清單

### 新增檔案
1. ✅ `docs/archive/database_migrations/08-add-suggested-embedding-column.sql`
   - 資料庫 migration script
   - 新增 `suggested_embedding` 欄位

2. ✅ `docs/features/INTENT_SUGGESTION_SEMANTIC_DEDUP_IMPLEMENTATION.md`
   - 本實現報告

### 修改檔案
1. ✅ `rag-orchestrator/services/intent_suggestion_engine.py`
   - 新增 `check_semantic_duplicates()` 方法
   - 更新 `record_suggestion()` 方法
   - 新增 embedding 生成和相似度檢查邏輯
   - 約 150 行新增代碼

2. ✅ `.env`
   - 新增 `INTENT_SUGGESTION_SIMILARITY_THRESHOLD=0.80`

3. ✅ `docs/guides/ENVIRONMENT_VARIABLES.md`
   - 新增變數說明和使用範例

### 資料庫變更
1. ✅ `suggested_intents` 表
   - 新增 `suggested_embedding vector(1536)` 欄位

---

## 🔄 部署步驟

### 1. 資料庫 Migration

```bash
# 執行 migration
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin \
  -f /path/to/08-add-suggested-embedding-column.sql

# 或直接執行 SQL
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "ALTER TABLE suggested_intents ADD COLUMN IF NOT EXISTS suggested_embedding vector(1536);"
```

### 2. 更新環境變數

```bash
# 編輯 .env 檔案
echo "INTENT_SUGGESTION_SIMILARITY_THRESHOLD=0.80" >> .env
```

### 3. 重啟服務

```bash
docker-compose restart rag-orchestrator
```

### 4. 驗證部署

```bash
# 檢查服務日誌
docker logs aichatbot-rag-orchestrator --tail 50

# 預期看到:
# ✅ 意圖建議引擎已初始化 (Phase B)
```

---

## 🎯 效益評估

### 預期效益

1. **減少重複建議**: 語義相似的建議會自動合併，減少審核負擔
2. **提升審核效率**: 審核人員只需處理真正不同的意圖建議
3. **頻率統計更準確**: 相似建議的頻率會累加，更能反映實際需求
4. **資料庫空間節省**: 避免儲存大量相似建議

### 實際數據（待測試後補充）

| 指標 | 實施前 | 實施後 | 改善幅度 |
|------|-------|-------|---------|
| 待審核建議數量 | - | - | - |
| 語義重複率 | - | - | - |
| 審核處理時間 | - | - | - |

---

## ⚠️ 注意事項

### 1. Embedding API 依賴
- 系統依賴 embedding-api 服務運作
- 如果 embedding-api 故障，建議仍會被儲存但無法去重
- 建議監控 embedding-api 的可用性

### 2. 歷史資料處理
- 此更新僅影響新建立的建議
- 現有的 `suggested_intents` 記錄 `suggested_embedding` 為 NULL
- 如需補齊歷史資料，需要執行批次 backfill script

### 3. 相似度閾值調整
- 閾值 0.80 是推薦值，可根據實際情況調整
- 建議範圍：0.75 - 0.85
- 過低會誤判不相似的為重複，過高會漏判相似的

### 4. 資料庫索引建議
- 當 `suggested_intents` 記錄數超過 100 筆時
- 建議建立 pgvector 索引以提升查詢效能
- 選擇 HNSW（精確）或 IVFFlat（快速）索引

---

## 🔮 後續優化方向

### 短期優化
1. **歷史資料補齊**: 為現有建議生成 embedding
2. **索引建立**: 根據資料量建立適當的 pgvector 索引
3. **監控面板**: 新增去重統計到審核中心

### 中期優化
1. **閾值動態調整**: 根據審核反饋自動調整相似度閾值
2. **批次去重**: 定期執行批次去重任務，合併歷史重複建議
3. **多語言支援**: 支援其他 embedding 模型（如中文特化模型）

### 長期優化
1. **建議群聚**: 使用聚類算法將相似建議分組展示
2. **智能合併**: 自動建議將多個相似建議合併為最佳表述
3. **A/B 測試**: 測試不同閾值對系統的影響

---

## 📞 維護與支援

**實現者**: Claude Code
**維護團隊**: AIChatbot Development Team
**問題回報**: GitHub Issues

**相關文檔**:
- [Database Schema + ERD](../DATABASE_SCHEMA_ERD.md)
- [環境變數參考](../guides/ENVIRONMENT_VARIABLES.md)
- [Intent Management README](./INTENT_MANAGEMENT_README.md)

---

**報告結束**
**日期**: 2025-10-22
**版本**: v1.0
