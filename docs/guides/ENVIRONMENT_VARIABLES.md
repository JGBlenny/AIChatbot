# 環境變數參考

本文檔列出 AIChatbot 專案所有環境變數的定義、預設值和使用說明。

## 📋 命名規範

所有環境變數遵循以下規範：
- ✅ 使用 **大寫字母**
- ✅ 使用 **下劃線** 分隔單詞
- ✅ 使用 **清晰的前綴** 分類（DB_、REDIS_、OPENAI_）
- ✅ API URLs 使用 **`*_API_URL`** 後綴
- ✅ 提供 **合理的預設值**

## 🔑 必需變數

### OpenAI API

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `OPENAI_API_KEY` | OpenAI API 金鑰，用於 Embedding 和 LLM | 無 | ✅ |

**使用位置**：
- `embedding-service` - 生成向量嵌入
- `rag-orchestrator` - 意圖分類、答案優化、知識生成
- `knowledge-admin-api` - 回測框架

**範例**：
```bash
OPENAI_API_KEY=sk-proj-your-api-key-here
```

## 🗄️ 資料庫變數

### PostgreSQL

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `DB_HOST` | PostgreSQL 主機位址 | `localhost` / `postgres` (Docker) | ❌ |
| `DB_PORT` | PostgreSQL 埠號 | `5432` | ❌ |
| `DB_NAME` | 資料庫名稱 | `aichatbot_admin` | ❌ |
| `DB_USER` | 資料庫使用者 | `aichatbot` | ❌ |
| `DB_PASSWORD` | 資料庫密碼 | `aichatbot_password` | ❌ |

**使用位置**：
- `rag-orchestrator` - 讀取意圖、知識庫、業者資料
- `knowledge-admin-api` - 知識管理、測試情境管理

**Docker 預設值**：
```bash
DB_HOST=postgres  # 容器名稱
DB_PORT=5432
DB_NAME=aichatbot_admin
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password
```

**本地開發預設值**：
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aichatbot_admin
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password
```

## 🔴 Redis 變數

### Redis 快取

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `REDIS_HOST` | Redis 主機位址 | `localhost` / `redis` (Docker) | ❌ |
| `REDIS_PORT` | Redis 埠號 | `6379` | ❌ |

**使用位置**：
- `embedding-service` - Embedding 快取（節省 70-90% API 成本）

**Docker 預設值**：
```bash
REDIS_HOST=redis  # 容器名稱
REDIS_PORT=6379
```

**本地開發預設值**：
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
```

## 🌐 API URLs

### 微服務 URLs

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `EMBEDDING_API_URL` | Embedding API 端點 | `http://localhost:5001/api/v1/embeddings` | ❌ |
| `RAG_API_URL` | RAG Orchestrator 端點 | `http://localhost:8100` | ❌ |
| `KNOWLEDGE_ADMIN_API_URL` | 知識管理 API 端點 | `http://localhost:8000/api` | ❌ |

**使用位置**：
- `rag-orchestrator` → `EMBEDDING_API_URL`
- `knowledge-admin-api` → `EMBEDDING_API_URL`, `RAG_API_URL`

**Docker 預設值**：
```bash
EMBEDDING_API_URL=http://embedding-api:5000/api/v1/embeddings
RAG_API_URL=http://rag-orchestrator:8100
KNOWLEDGE_ADMIN_API_URL=http://knowledge-admin-api:8000/api
```

## 🤖 AI 模型配置

### 知識生成模型

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `KNOWLEDGE_GEN_MODEL` | AI 知識生成使用的模型 | `gpt-3.5-turbo` | ❌ |

**使用位置**：
- `rag-orchestrator` - AI 知識生成功能

**可選值**：
- `gpt-3.5-turbo` （預設，成本低）
- `gpt-4o-mini` （更高品質）
- `gpt-4` （最高品質，成本高）

**範例**：
```bash
KNOWLEDGE_GEN_MODEL=gpt-4o-mini
```

## 🧪 回測框架變數

### 回測配置

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `BACKTEST_SELECTION_STRATEGY` | 測試選擇策略 | `full` | ❌ |
| `BACKTEST_QUALITY_MODE` | 品質評估模式 | `basic` | ❌ |
| `BACKTEST_USE_DATABASE` | 是否使用資料庫載入測試 | `false` | ❌ |
| `BACKTEST_NON_INTERACTIVE` | 非互動模式 | `false` | ❌ |
| `BACKTEST_SAMPLE_SIZE` | 樣本數量限制 | 無限制 | ❌ |
| `BACKTEST_INCREMENTAL_LIMIT` | 增量測試數量 | `100` | ❌ |
| `BACKTEST_FAILED_LIMIT` | 失敗測試數量 | `50` | ❌ |

**詳細說明**：請參閱 [回測環境變數參考](../backtest/backtest_env_vars.md)

## 🐳 前端開發變數

### Node.js 環境

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `NODE_ENV` | Node.js 環境模式 | `production` | ❌ |

**可選值**：
- `development` - 開發模式（熱重載、詳細錯誤）
- `production` - 生產模式（優化、壓縮）

## 🛠️ 其他變數

### 專案配置

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `PROJECT_ROOT` | 專案根目錄路徑 | 自動檢測 | ❌ |

**使用位置**：
- `knowledge-admin-api` - 回測框架執行時需要專案路徑

## 📝 .env 文件範例

### 最小配置（僅必需變數）

```bash
# OpenAI API Key
OPENAI_API_KEY=sk-proj-your-api-key-here
```

### 完整配置（所有變數）

```bash
# ==========================================
# OpenAI API
# ==========================================
OPENAI_API_KEY=sk-proj-your-api-key-here

# ==========================================
# PostgreSQL 資料庫
# ==========================================
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aichatbot_admin
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password

# ==========================================
# Redis 快取
# ==========================================
REDIS_HOST=localhost
REDIS_PORT=6379

# ==========================================
# API URLs（本地開發）
# ==========================================
EMBEDDING_API_URL=http://localhost:5001/api/v1/embeddings
RAG_API_URL=http://localhost:8100
KNOWLEDGE_ADMIN_API_URL=http://localhost:8000/api

# ==========================================
# AI 模型配置
# ==========================================
KNOWLEDGE_GEN_MODEL=gpt-3.5-turbo

# ==========================================
# 回測框架
# ==========================================
BACKTEST_SELECTION_STRATEGY=incremental
BACKTEST_QUALITY_MODE=basic
BACKTEST_USE_DATABASE=true
BACKTEST_NON_INTERACTIVE=true

# ==========================================
# 前端開發
# ==========================================
NODE_ENV=development
```

## 🔒 安全注意事項

### ⚠️ 敏感變數

以下變數包含敏感資訊，**絕不可提交到版本控制**：

- ✋ `OPENAI_API_KEY` - API 金鑰
- ✋ `DB_PASSWORD` - 資料庫密碼

### ✅ 最佳實踐

1. **使用 .env 文件**
   ```bash
   cp .env.example .env
   nano .env  # 編輯並填入真實值
   ```

2. **確認 .gitignore**
   ```gitignore
   .env
   .env.local
   *.env
   ```

3. **不要在代碼中硬編碼**
   ```python
   # ❌ 錯誤
   OPENAI_API_KEY = "sk-proj-..."

   # ✅ 正確
   OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
   ```

4. **生產環境使用環境變數**
   ```bash
   # Kubernetes Secret
   kubectl create secret generic aichatbot-secrets \
     --from-literal=OPENAI_API_KEY=sk-proj-...

   # Docker Compose
   docker-compose up -d --env-file .env.prod
   ```

## 🔍 故障排除

### 常見問題

**Q: 為什麼我的 API Key 不生效？**

A: 檢查：
1. .env 文件是否在專案根目錄
2. Docker 容器是否已重啟（`docker-compose restart`）
3. 變數名稱是否正確（`OPENAI_API_KEY` 而非 `OPENAI_KEY`）

**Q: 本地開發時資料庫連接失敗？**

A: 確認：
1. `DB_HOST` 設為 `localhost` 而非 `postgres`
2. PostgreSQL 服務已啟動
3. 埠號 5432 未被佔用

**Q: Docker 環境下服務無法互相連接？**

A: 檢查：
1. 使用容器名稱而非 localhost（如 `postgres` 而非 `localhost`）
2. API URLs 指向容器內部端點（如 `http://embedding-api:5000`）
3. 所有服務在同一個 Docker 網路

## 📚 相關文件

- [Docker Compose 指南](./DOCKER_COMPOSE_GUIDE.md)
- [回測環境變數參考](../backtest/backtest_env_vars.md)
- [快速開始指南](../../QUICKSTART.md)
- [開發工作流程](./DEVELOPMENT_WORKFLOW.md)

---

**最後更新**: 2025-10-13
**維護者**: 開發團隊
