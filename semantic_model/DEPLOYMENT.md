# 語義模型部署指南

## 部署架構

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  主系統 API │────▶│ 語義模型服務 │────▶│  PostgreSQL │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  模型快取    │
                    └──────────────┘
```

## 1. Docker 部署（推薦）

### 建立映像檔
```bash
cd /Users/lenny/jgb/AIChatbot/semantic_model
docker build -t semantic-model:latest .
```

### 啟動服務
```bash
# 單獨啟動
docker run -d \
  --name semantic_model \
  -p 8001:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  semantic-model:latest

# 使用 docker-compose（整合到現有系統）
docker-compose up -d
```

## 2. 整合到主系統

### 修改主系統 docker-compose.yml
```yaml
services:
  # ... 現有服務 ...

  semantic-model:
    build: ./semantic_model
    container_name: semantic_model_service
    ports:
      - "8001:8000"
    volumes:
      - ./semantic_model/data:/app/data
      - ./semantic_model/config:/app/config
      - semantic_model_cache:/app/models
    environment:
      - DATABASE_URL=postgresql://aichatbot:aichatbot_password@db:5432/aichatbot
    networks:
      - aichatbot_network
    depends_on:
      - db
```

### API 整合範例
```python
# 在主系統中呼叫語義模型
import requests

def semantic_search(query: str, top_k: int = 5):
    """呼叫語義模型服務"""
    response = requests.post(
        "http://semantic-model:8000/search",
        json={
            "query": query,
            "top_k": top_k,
            "min_score": 0.1
        }
    )
    return response.json()

# 使用範例
result = semantic_search("電費帳單寄送區間")
for item in result["results"]:
    print(f"ID: {item['knowledge_id']}, 分數: {item['score']}")
    if item['form_id']:
        # 觸發表單填寫
        trigger_form(item['form_id'])
```

## 3. 性能優化

### 模型快取
第一次載入模型需要下載（約 400MB），之後會使用快取：
- 本地快取位置：`~/.cache/huggingface/`
- Docker 快取：使用 volume 保存

### 預載模型（加速首次啟動）
```bash
# 在 Dockerfile 中已包含
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('BAAI/bge-reranker-base')"
```

### 批次處理
API 已實作批次處理，每批 100 個候選：
```python
batch_size = 100  # 可調整
```

## 4. 監控與維護

### 健康檢查
```bash
# 檢查服務狀態
curl http://localhost:8001/

# 獲取系統指標
curl http://localhost:8001/metrics
```

### 重新載入知識庫（不重啟服務）
```bash
curl -X POST http://localhost:8001/reload
```

### 日誌查看
```bash
# Docker 日誌
docker logs semantic_model_service

# Docker Compose 日誌
docker-compose logs -f semantic-model
```

## 5. 生產環境設定

### 環境變數
```bash
# .env 檔案
MODEL_NAME=BAAI/bge-reranker-base
API_PORT=8000
LOG_LEVEL=INFO
DATABASE_URL=postgresql://user:pass@host:5432/db

# GPU 加速（如果有）
CUDA_VISIBLE_DEVICES=0
```

### 資源需求
- **CPU**: 2 核心以上
- **記憶體**: 4GB 以上（模型約需 1.5GB）
- **儲存**: 2GB（含模型快取）
- **網路**: 首次需下載模型

### 擴展性
```yaml
# 多實例部署（負載平衡）
services:
  semantic-model:
    image: semantic-model:latest
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

## 6. 故障排除

### 模型載入失敗
```bash
# 檢查網路連線
docker exec semantic_model_service ping huggingface.co

# 手動下載模型
docker exec semantic_model_service python -c "
from sentence_transformers import CrossEncoder
model = CrossEncoder('BAAI/bge-reranker-base')
print('Model loaded successfully')
"
```

### 記憶體不足
```bash
# 調整 Docker 記憶體限制
docker run -m 4g semantic-model:latest
```

### API 連線問題
```bash
# 檢查端口
docker ps | grep semantic_model
netstat -tulpn | grep 8001

# 測試內部連線
docker exec main_app curl http://semantic-model:8000/
```

## 7. 更新流程

### 更新知識庫
```bash
# 1. 更新 data/knowledge_base.json
# 2. 重新載入（無需重啟）
curl -X POST http://localhost:8001/reload
```

### 更新模型
```bash
# 1. 修改 config/models.json
# 2. 重建映像檔
docker build -t semantic-model:latest .
# 3. 重啟服務
docker-compose restart semantic-model
```

## 8. 備份與還原

### 備份
```bash
# 備份設定和資料
tar -czf semantic_model_backup.tar.gz \
  semantic_model/config \
  semantic_model/data
```

### 還原
```bash
# 解壓備份
tar -xzf semantic_model_backup.tar.gz

# 重啟服務
docker-compose restart semantic-model
```

## 問題回報
如有問題，請提供：
1. 錯誤日誌：`docker logs semantic_model_service`
2. 系統狀態：`curl http://localhost:8001/metrics`
3. 知識庫大小：`wc -l data/knowledge_base.json`