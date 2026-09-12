# 部署腳本

此目錄包含用於部署和啟動服務的腳本。

## 📋 腳本清單

### 1. setup.sh
- **用途**: 初始化專案環境
- **功能**:
  - 創建必要目錄
  - 複製環境變數範例
  - 檢查 Docker 環境
  - 初始化資料庫
- **執行**: `bash scripts/deployment/setup.sh`

### 2. deploy-frontend.sh
- **用途**: 部署前端應用
- **功能**:
  - 編譯 Vue.js 前端
  - 複製靜態文件
  - 配置 Nginx
  - 重啟前端服務
- **執行**: `bash scripts/deployment/deploy-frontend.sh`

### 3. start_rag_services.sh
- **用途**: 啟動 RAG 相關服務
- **功能**:
  - 啟動 RAG Orchestrator
  - 啟動 Embedding Service
  - 啟動 Redis Cache
  - 健康檢查
- **執行**: `bash scripts/deployment/start_rag_services.sh`

## 🚀 使用指南

### 首次部署

```bash
# 1. 執行初始化
cd /Users/lenny/jgb/AIChatbot
bash scripts/deployment/setup.sh

# 2. 設定環境變數
cp .env.example .env
nano .env  # 填入 OPENAI_API_KEY

# 3. 啟動所有服務
docker-compose up -d

# 4. 部署前端（正式環境）
bash scripts/deployment/deploy-frontend.sh
```

### 日常操作

```bash
# 啟動 RAG 服務
bash scripts/deployment/start_rag_services.sh

# 重新部署前端
bash scripts/deployment/deploy-frontend.sh

# 重啟所有服務
docker-compose restart
```

## 📝 腳本詳情

### setup.sh

**檢查項目**:
- ✅ Docker 安裝狀態
- ✅ Docker Compose 版本
- ✅ .env 文件存在
- ✅ 必要目錄結構

**創建目錄**:
```
data/
logs/
backups/
```

### deploy-frontend.sh

**執行步驟**:
1. 進入前端目錄
2. 安裝依賴 (npm install)
3. 編譯生產版本 (npm run build)
4. 複製到部署目錄
5. 重啟 Nginx 容器

### start_rag_services.sh

**啟動順序**:
1. Redis Cache
2. Embedding Service
3. RAG Orchestrator
4. 健康檢查（等待服務就緒）

**健康檢查端點**:
- Redis: `redis-cli ping`
- Embedding: `http://localhost:5001/health`
- RAG: `http://localhost:8100/health`

## ⚠️ 注意事項

### 權限要求
```bash
# 確保腳本有執行權限
chmod +x scripts/deployment/*.sh
```

### 環境變數
確保設定以下環境變數：
- `OPENAI_API_KEY` - OpenAI API 金鑰
- `DATABASE_URL` - PostgreSQL 連接字串
- `REDIS_URL` - Redis 連接字串

### 資料庫遷移
首次部署或更新後，檢查資料庫遷移：
```bash
docker exec -it aichatbot-postgres-1 \
  psql -U postgres -d jgb_chatbot \
  -c "SELECT * FROM schema_migrations ORDER BY id;"
```

## 🔧 故障排除

### 問題：腳本執行失敗

**解決方案**:
```bash
# 檢查日誌
docker-compose logs -f

# 檢查服務狀態
docker-compose ps

# 重啟服務
docker-compose restart
```

### 問題：前端編譯失敗

**解決方案**:
```bash
# 清理 node_modules
cd knowledge-admin/frontend
rm -rf node_modules
npm install

# 手動編譯
npm run build
```

### 問題：RAG 服務無法啟動

**解決方案**:
```bash
# 檢查依賴服務
docker-compose ps postgres redis

# 查看詳細錯誤
docker-compose logs rag-orchestrator

# 重啟相關服務
docker-compose restart postgres redis rag-orchestrator
```

## 🔄 遷移記錄

**遷移日期**: 2025-10-28
**原位置**: 根目錄
**新位置**: `scripts/deployment/`
**原因**: 整理項目結構，統一部署腳本管理

## 📚 相關文檔

- 部署指南（檔已不存在）
- Docker Compose 指南（檔已不存在）
- 快速開始（檔已不存在）
- 開發工作流程（檔已不存在）

## 🎯 最佳實踐

1. **版本控制**: 腳本變更前先備份
2. **測試**: 在開發環境測試後再用於正式環境
3. **日誌**: 保留部署日誌以便追蹤問題
4. **回滾**: 準備回滾方案（如 Git tag、Docker image tag）

---

**維護**: DevOps 團隊
**狀態**: 活躍使用中
**更新頻率**: 依需求更新
