# 🚀 快速開始指南

## 📋 前置需求

- Docker 和 Docker Compose
- Node.js 18+ （僅本地開發需要）
- Make（可選，提供快捷命令）

## ⚡ 快速啟動

### **方式 1：使用 Make 命令（推薦）**

```bash
# 查看所有可用命令
make help

# 啟動生產環境
make prod-up

# 啟動開發環境
make dev-up

# 前端快速開發（熱重載）
make backend-only  # 啟動後端
make frontend-dev  # 啟動前端 Vite（另一個終端）
```

### **方式 2：直接使用 Docker Compose**

```bash
# 生產環境
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 開發環境
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## 🌐 訪問服務

| 服務 | URL | 說明 |
|------|-----|------|
| 知識庫管理前端 | http://localhost:8080 | Vue.js 前端界面 |
| 知識庫管理 API | http://localhost:8000 | FastAPI 後端 |
| RAG Orchestrator | http://localhost:8100 | RAG 服務 |
| PostgreSQL | localhost:5432 | 資料庫 |
| Redis | localhost:6379 | 緩存 |
| pgAdmin | http://localhost:5050 | 資料庫管理界面 |

## 🔧 開發模式選擇

### **1. 生產模式（推薦用於測試/部署）**
```bash
make prod-up
```
- ✅ 使用 Docker image 內的編譯文件
- ✅ 最穩定
- ⚠️ 修改後需要重建 Docker

### **2. 開發模式（推薦用於快速開發）**
```bash
make dev-up
cd knowledge-admin/frontend
npm run build  # 每次修改後執行
```
- ✅ 修改後只需編譯，無需重建 Docker
- ✅ 開發效率高

### **3. 熱重載模式（推薦用於前端開發）**⚡
```bash
make backend-only  # 終端 1
make frontend-dev  # 終端 2
```
- ✅ 修改代碼立即生效
- ✅ 開發體驗最佳
- ✅ 支持 Source Map 調試

## 📝 常見操作

### 前端開發

```bash
# 生產模式 - 修改前端代碼
make prod-build            # 重建前端
make prod-restart-web      # 或直接重啟前端服務

# 開發模式 - 修改前端代碼
make frontend-build        # 編譯前端
# 刷新瀏覽器即可

# 熱重載模式 - 修改前端代碼
# 自動生效，無需任何操作
```

### 後端開發

```bash
# 修改後端代碼後，重啟對應服務
docker-compose restart knowledge-admin-api
# 或
make prod-down && make prod-up
```

### 查看日誌

```bash
# 生產環境日誌
make prod-logs

# 開發環境日誌
make dev-logs

# 特定服務日誌
docker-compose logs -f knowledge-admin-api
```

### 重置環境

```bash
# 停止並清理容器
make clean

# 停止並清理容器 + volumes（完全重置）
make clean-all
```

## 🐛 故障排除

### 前端顯示空白或錯誤

```bash
# 檢查容器狀態
docker-compose ps

# 查看前端日誌
docker logs aichatbot-knowledge-admin-web

# 強制重建
make prod-down
make prod-build
make prod-up
```

### 資料庫連接失敗

```bash
# 檢查 PostgreSQL 是否正常
docker-compose ps postgres

# 查看資料庫日誌
docker logs aichatbot-postgres
```

### 開發模式下 dist 目錄不存在

```bash
cd knowledge-admin/frontend
npm install
npm run build
```

## 📚 詳細文檔

- **完整配置說明**: [DOCKER_COMPOSE_GUIDE.md](./DOCKER_COMPOSE_GUIDE.md)
- **系統架構**: [docs/architecture/SYSTEM_ARCHITECTURE.md](./docs/architecture/SYSTEM_ARCHITECTURE.md)

## 🎯 推薦工作流程

### 日常前端開發
```bash
make backend-only  # 一次性啟動
make frontend-dev  # 開發時使用
```

### 測試完整系統
```bash
make dev-up
make frontend-build  # 修改後執行
```

### 部署前驗證
```bash
make prod-build
make prod-up
```

## 💡 提示

1. 首次啟動可能需要幾分鐘來下載 Docker images
2. 確保 `.env` 文件配置了 `OPENAI_API_KEY`
3. 開發模式下的修改不會影響 Docker image
4. 生產模式每次修改都需要重建 image

---

需要幫助？查看 [DOCKER_COMPOSE_GUIDE.md](./DOCKER_COMPOSE_GUIDE.md) 獲取更多細節！
