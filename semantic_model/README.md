# 語義重排序模型 (Semantic Reranker)

## 概述
本模組使用 BAAI/bge-reranker-base 模型提供語義重排序服務，提升 RAG 系統的檢索準確度。

## 系統架構

### 兩階段檢索
1. **向量搜索** - 快速初篩（OpenAI Embeddings + pgvector）
2. **語義重排序** - 精準排序（BAAI/bge-reranker-base）

## 檔案結構
```
semantic_model/
├── Dockerfile                 # Docker 映像配置
├── docker-compose.yml        # 獨立部署配置
├── requirements.txt          # Python 依賴
└── scripts/
    └── api_server.py         # FastAPI 服務
```

## API 端點

### POST /rerank
對候選結果進行語義重排序

**請求範例：**
```json
{
  "query": "電費帳單寄送區間",
  "candidates": [
    {"id": 1, "content": "租屋須知與規定"},
    {"id": 2, "content": "電費帳單查詢與寄送時間"}
  ],
  "top_k": 2
}
```

**回應範例：**
```json
{
  "results": [
    {"id": 2, "score": 0.937, "content": "電費帳單查詢與寄送時間"},
    {"id": 1, "score": 0.003, "content": "租屋須知與規定"}
  ]
}
```

## 部署

### 使用 Docker Compose（推薦）
```bash
docker-compose up -d
```

### 環境變數
- `MODEL_NAME`: BAAI/bge-reranker-base（預設）
- `PORT`: 8000（容器內部）

## 整合到主系統

在主系統的 `docker-compose.prod.yml` 中已配置：
```yaml
semantic-model:
  build: ./semantic_model
  container_name: aichatbot-semantic-model
  ports:
    - "8002:8000"
  restart: unless-stopped
```

RAG Orchestrator 相關環境變數：
```yaml
USE_SEMANTIC_RERANK: true
ENABLE_RERANKER: true
ENABLE_KNOWLEDGE_RERANKER: true
SEMANTIC_MODEL_API_URL: http://aichatbot-semantic-model:8000
```

## 測試

### 健康檢查
```bash
curl http://localhost:8002/
```

### 重排序測試
```bash
curl -X POST http://localhost:8002/rerank \
  -H "Content-Type: application/json" \
  -d '{
    "query": "電費帳單寄送區間",
    "candidates": [
      {"id": 1, "content": "租屋須知"},
      {"id": 2, "content": "電費帳單寄送時間"}
    ],
    "top_k": 2
  }'
```

## 效能考量

- 首次啟動需下載模型（約 1.1GB）
- 建議配置至少 4GB 記憶體
- 支援 GPU 加速（如可用）
- 批次處理自動優化

## 實際效果

查詢「電費帳單寄送區間」時的分數變化：
- ID 1296（電費查詢）: 0.687 → 0.974（重排序後）
- ID 1657（租屋須知）: 0.466（原始分數低，不會被誤選）

系統能正確區分語義相關性，避免關鍵字匹配的誤判。