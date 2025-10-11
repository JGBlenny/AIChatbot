# AIChatbot 快速參考指南

快速查找常用命令、API 端點和配置的參考手冊。

---

## 🚀 快速啟動

```bash
# 1. 設定環境變數
cp .env.example .env
nano .env  # 填入 OPENAI_API_KEY

# 2. 啟動所有服務
docker-compose up -d

# 3. 查看服務狀態
docker-compose ps

# 4. 查看日誌
docker-compose logs -f rag-orchestrator
```

---

## 🌐 服務端點

| 服務 | URL | 文檔 |
|------|-----|------|
| 知識管理後台 | http://localhost:8080 | - |
| 知識管理 API | http://localhost:8000/docs | Swagger UI |
| Embedding API | http://localhost:5001/docs | Swagger UI |
| **RAG Orchestrator** | http://localhost:8100/docs | Swagger UI |
| pgAdmin | http://localhost:5050 | admin@aichatbot.com / admin |

---

## 🔧 常用命令

### Docker 管理

```bash
# 重啟特定服務
docker restart aichatbot-rag-orchestrator

# 重建並啟動
docker-compose up -d --build

# 查看日誌
docker-compose logs -f [service-name]

# 停止所有服務
docker-compose down

# 清理所有容器和資料（⚠️ 謹慎使用）
docker-compose down -v
```

### 資料庫操作

```bash
# 連線到 PostgreSQL
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin

# 查看 Intent 列表
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin \
  -c "SELECT id, name, type, is_enabled FROM intents;"

# 查看業者列表
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin \
  -c "SELECT id, name, is_active FROM vendors;"

# 匯出資料庫
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > backup.sql

# 匯入資料庫
cat backup.sql | docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin
```

### 回測執行

```bash
# 執行煙霧測試（5 個測試）
echo "" | python3 scripts/knowledge_extraction/backtest_framework.py \
  --test-file test_scenarios_smoke.xlsx

# 執行完整測試
echo "" | python3 scripts/knowledge_extraction/backtest_framework.py \
  --test-file test_scenarios_full.xlsx

# 查看回測結果
cat output/backtest/backtest_results_summary.txt
```

---

## 📡 API 快速參考

### 1. 多業者 Chat API ⭐

```bash
# 基本對話
curl -X POST 'http://localhost:8100/api/v1/message' \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "租金如何計算？",
    "vendor_id": 1,
    "mode": "tenant",
    "top_k": 5,
    "include_sources": true
  }'

# 響應結構（含多 Intent）
{
  "answer": "...",
  "intent_name": "合約規定",
  "all_intents": ["合約規定", "帳務查詢"],      # 所有意圖
  "secondary_intents": ["帳務查詢"],           # 次要意圖
  "intent_ids": [2, 6],                        # Intent IDs
  "confidence": 0.8,
  "sources": [...],
  "source_count": 5,
  "vendor_id": 1
}
```

### 2. 業者管理 API

```bash
# 獲取業者列表
curl http://localhost:8100/api/v1/vendors

# 獲取業者配置
curl http://localhost:8100/api/v1/vendors/1/configs

# 獲取業者統計
curl http://localhost:8100/api/v1/vendors/1/stats

# 測試業者配置
curl http://localhost:8100/api/v1/vendors/1/test
```

### 3. Intent 管理 API

```bash
# 獲取 Intent 列表
curl http://localhost:8100/api/v1/intents

# 創建新 Intent
curl -X POST 'http://localhost:8100/api/v1/intents' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "設備問題",
    "type": "knowledge",
    "description": "房屋設備相關問題",
    "keywords": ["設備", "損壞", "報修"],
    "confidence_threshold": 0.7,
    "is_enabled": true
  }'

# 更新 Intent
curl -X PUT 'http://localhost:8100/api/v1/intents/1' \
  -H 'Content-Type: application/json' \
  -d '{
    "keywords": ["設備", "損壞", "報修", "維護"]
  }'

# 重新載入 Intent 配置
curl -X POST 'http://localhost:8100/api/v1/reload'
```

### 4. 知識庫 API

```bash
# 獲取知識列表
curl 'http://localhost:8000/api/knowledge?limit=10&offset=0'

# 新增知識
curl -X POST 'http://localhost:8000/api/knowledge' \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "退租流程",
    "category": "合約問題",
    "audience": "租客",
    "content": "# 退租流程\n\n1. 提前30天通知...",
    "keywords": ["退租", "合約"],
    "question_summary": "如何申請退租"
  }'

# 更新知識（自動重新生成向量）
curl -X PUT 'http://localhost:8000/api/knowledge/1' \
  -H 'Content-Type: application/json' \
  -d '{
    "content": "更新後的內容..."
  }'

# 刪除知識
curl -X DELETE 'http://localhost:8000/api/knowledge/1'
```

### 5. Embedding API

```bash
# 生成向量
curl -X POST 'http://localhost:5001/api/v1/embeddings' \
  -H 'Content-Type: application/json' \
  -d '{"text": "如何申請退租？"}'

# 響應
{
  "embedding": [0.123, -0.456, ...],  # 1536 維向量
  "cached": false,
  "processing_time": 0.234
}

# 查看快取統計
curl 'http://localhost:5001/api/v1/cache/stats'
```

---

## 🗂️ 資料庫結構快速參考

### 核心表

```sql
-- Intents（意圖定義）
SELECT id, name, type, is_enabled FROM intents;

-- Knowledge Base（知識庫）
SELECT id, title, intent_id, vendor_id, scope, priority
FROM knowledge_base
LIMIT 10;

-- Vendors（業者）
SELECT id, name, code, is_active FROM vendors;

-- Vendor Configs（業者配置）
SELECT vendor_id, category, param_key, param_value
FROM vendor_configs
WHERE vendor_id = 1;

-- Conversation Logs（對話記錄）
SELECT id, question, intent_type, confidence_score, created_at
FROM conversation_logs
ORDER BY created_at DESC
LIMIT 10;
```

---

## ⚙️ 環境變數

### 必需配置

```env
# OpenAI API
OPENAI_API_KEY=sk-proj-your-key-here

# 資料庫
DB_HOST=postgres
DB_PORT=5432
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password
DB_NAME=aichatbot_admin

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
```

### 可選配置

```env
# RAG 配置
RAG_SIMILARITY_THRESHOLD=0.6
RAG_TOP_K=5
RAG_CONFIDENCE_THRESHOLD=0.7

# LLM 配置
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=1000

# Embedding 配置
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_CACHE_TTL=3600
```

---

## 🎯 多 Intent 分類系統

### 工作原理

```
問題：「租金如何計算？」

↓ Intent Classifier (OpenAI Function Calling)

{
  "primary_intent": "合約規定",
  "secondary_intents": ["帳務查詢"],
  "confidence": 0.8
}

↓ Hybrid Retrieval (差異化加成)

主要 Intent (1.5x boost):
  ★ ID 178: 租金計算方式... (0.744 → 1.116)
  ★ ID 173: 首月租金計算... (0.684 → 1.026)

次要 Intent (1.2x boost):
  ☆ ID 175: 租金差額處理... (0.701 → 0.842)

↓ LLM Answer Optimizer

整合多個知識來源，生成完整答案
```

### 調優參數

```python
# intent_classifier.py
"confidence_threshold": 0.70,  # 意圖分類信心度閾值
"max_intents": 2,              # 最多次要意圖數量

# vendor_knowledge_retriever.py
PRIMARY_INTENT_BOOST = 1.5     # 主要意圖加成
SECONDARY_INTENT_BOOST = 1.2   # 次要意圖加成
```

---

## 📊 監控與除錯

### 查看日誌

```bash
# RAG Orchestrator 日誌（含 Intent 分類和檢索）
docker logs aichatbot-rag-orchestrator -f

# Embedding API 日誌（含快取命中率）
docker logs aichatbot-embedding-api -f

# 知識管理 API 日誌
docker logs aichatbot-knowledge-admin-api -f
```

### 檢查服務健康狀態

```bash
# 檢查所有容器狀態
docker-compose ps

# 檢查特定服務
docker inspect aichatbot-rag-orchestrator

# 檢查網路連接
docker network inspect aichatbot_default
```

### 常見問題排查

```bash
# 1. RAG 沒有返回結果
# 檢查 Intent 是否啟用
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin \
  -c "SELECT name, is_enabled FROM intents WHERE is_enabled = false;"

# 2. 相似度太低
# 查看知識庫向量狀態
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin \
  -c "SELECT id, title, (embedding IS NULL) as missing_vector FROM knowledge_base WHERE embedding IS NULL LIMIT 10;"

# 3. 業者配置未生效
# 檢查業者配置
curl http://localhost:8100/api/v1/vendors/1/test | python3 -m json.tool
```

---

## 📚 完整文檔

- 📖 [完整文檔導覽](docs/README.md)
- 🎯 [多 Intent 分類系統](docs/MULTI_INTENT_CLASSIFICATION.md)
- 🏛️ [系統架構文檔](docs/architecture/SYSTEM_ARCHITECTURE.md)
- 📘 [快速開始指南](QUICKSTART.md)
- 📋 [變更日誌](CHANGELOG.md)

---

## 🆘 尋求幫助

1. 檢查 [故障排除](#-監控與除錯) 章節
2. 查看服務日誌
3. 參考 [完整文檔](docs/README.md)
4. 聯繫開發團隊

---

**最後更新**: 2025-10-11
**維護者**: 開發團隊
