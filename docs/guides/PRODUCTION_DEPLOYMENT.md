# 🚀 線上部署指南

## 概述

本指南說明如何將 AIChatbot 優先級系統重構部署到生產環境。

## 前置需求

- ✅ 伺服器環境（Linux 推薦 Ubuntu 20.04+）
- ✅ Docker & Docker Compose 已安裝
- ✅ Git 已安裝
- ✅ 80 端口可用（前端）
- ✅ 5432, 6381, 8000, 8100 端口可用（後端服務）
- ✅ OpenAI API Key

## 📦 部署步驟

### 1. 推送代碼到 GitHub

在本地執行：

```bash
# 確認所有變更已提交
git status

# 推送到遠端倉庫
git push origin main
```

### 2. 在伺服器上拉取最新代碼

SSH 登入伺服器後：

```bash
# 拉取最新代碼
cd /path/to/AIChatbot
git pull origin main

# 確認已經是最新版本
git log --oneline -1
# 應該看到: ffe6713 feat: 知識優先級系統重構 - 從分級制改為開關制
```

### 3. 構建前端

```bash
# 進入前端目錄
cd knowledge-admin/frontend

# 安裝依賴（首次部署需要）
npm install

# 構建生產版本
npm run build

# 確認 dist 目錄已生成
ls -lh dist/
```

### 4. 配置環境變數

在伺服器上編輯 `.env` 檔案：

```bash
cd /path/to/AIChatbot
nano .env  # 或使用 vim
```

**必要配置**：

```bash
# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# 優先級系統配置（新增）
PRIORITY_BOOST=0.15

# AWS S3 配置（如需影片功能）
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=ap-northeast-1
S3_BUCKET_NAME=your_bucket_name
CLOUDFRONT_DOMAIN=your_cloudfront_domain

# 其他配置（可選）
RAG_TOP_K=5
KB_SIMILARITY_THRESHOLD=0.65
CACHE_ENABLED=true
```

### 5. 啟動服務

```bash
# 停止舊服務（如果有）
docker-compose -f docker-compose.prod.yml down

# 重新構建並啟動服務
docker-compose -f docker-compose.prod.yml up -d --build

# 查看服務狀態
docker-compose -f docker-compose.prod.yml ps
```

### 6. 驗證部署

#### 6.1 檢查容器狀態

```bash
docker-compose -f docker-compose.prod.yml ps
```

所有服務應該都是 `Up` 狀態：

```
NAME                              STATUS
aichatbot-embedding-api           Up
aichatbot-knowledge-admin-api     Up
aichatbot-knowledge-admin-web     Up
aichatbot-postgres                Up (healthy)
aichatbot-rag-orchestrator        Up
aichatbot-redis                   Up (healthy)
```

#### 6.2 檢查優先級配置

```bash
# 檢查環境變數是否生效
docker exec aichatbot-rag-orchestrator env | grep PRIORITY_BOOST

# 應該輸出: PRIORITY_BOOST=0.15
```

#### 6.3 檢查日誌

```bash
# 查看 RAG Orchestrator 日誌
docker-compose -f docker-compose.prod.yml logs -f rag-orchestrator

# 查看 Knowledge Admin API 日誌
docker-compose -f docker-compose.prod.yml logs -f knowledge-admin-api
```

#### 6.4 測試前端

打開瀏覽器訪問：

```
http://your-server-ip/knowledge
```

應該能看到知識管理介面，並且：
- ✅ 編輯知識時有「啟用優先級加成」checkbox
- ✅ 表格中顯示優先級標記（☑/☐）

#### 6.5 測試優先級功能

1. **測試單筆設定**：
   - 進入知識管理頁面
   - 編輯任一知識
   - 勾選「啟用優先級加成」
   - 儲存並確認表格顯示 ☑

2. **測試批量匯入**：
   - 進入知識匯入頁面
   - 上傳 CSV 檔案
   - 勾選「直接加入知識庫（跳過審核）」
   - 勾選「統一啟用優先級」
   - 確認匯入後所有知識 priority=1

3. **測試 RAG 加成**：

```bash
# 在伺服器上執行
curl -X POST "http://localhost:8100/api/v1/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "測試優先級",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "test_deploy"
  }'
```

檢查返回的知識是否包含優先級標記的知識。

### 7. 資料庫遷移（如需要）

如果您的生產資料庫已有舊的 priority 值（>1），需要執行遷移：

```bash
# 連接到 PostgreSQL
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin

# 執行遷移 SQL
UPDATE knowledge_base
SET priority = CASE
    WHEN priority > 1 THEN 1
    ELSE priority
END;

# 檢查結果
SELECT priority, COUNT(*) FROM knowledge_base GROUP BY priority;

# 退出
\q
```

## 🔧 故障排除

### 問題 1: 前端無法訪問

**症狀**: 瀏覽器顯示無法連接

**解決**:
```bash
# 檢查 Nginx 容器狀態
docker logs aichatbot-knowledge-admin-web

# 檢查 80 端口是否被佔用
sudo netstat -tlnp | grep :80

# 重啟前端容器
docker-compose -f docker-compose.prod.yml restart knowledge-admin-web
```

### 問題 2: 優先級未生效

**症狀**: 設定 priority=1 但排名沒變化

**解決**:
```bash
# 1. 確認環境變數
docker exec aichatbot-rag-orchestrator env | grep PRIORITY_BOOST

# 2. 重啟 RAG 服務
docker-compose -f docker-compose.prod.yml restart rag-orchestrator

# 3. 查看日誌確認啟動成功
docker-compose -f docker-compose.prod.yml logs rag-orchestrator | grep -i priority
```

### 問題 3: 資料庫連接失敗

**症狀**: API 無法啟動，日誌顯示 DB 連接錯誤

**解決**:
```bash
# 檢查 PostgreSQL 健康狀態
docker exec aichatbot-postgres pg_isready -U aichatbot

# 檢查數據庫是否存在
docker exec -it aichatbot-postgres psql -U aichatbot -l

# 重啟數據庫
docker-compose -f docker-compose.prod.yml restart postgres
```

### 問題 4: 前端構建失敗

**症狀**: `npm run build` 報錯

**解決**:
```bash
# 清除 node_modules 重新安裝
cd knowledge-admin/frontend
rm -rf node_modules package-lock.json
npm install

# 檢查 Node.js 版本（建議 16+）
node --version

# 重新構建
npm run build
```

## 📊 監控與維護

### 日誌查看

```bash
# 查看所有服務日誌
docker-compose -f docker-compose.prod.yml logs -f

# 查看特定服務日誌
docker-compose -f docker-compose.prod.yml logs -f rag-orchestrator

# 查看最近 100 行日誌
docker-compose -f docker-compose.prod.yml logs --tail=100 rag-orchestrator
```

### 資源監控

```bash
# 查看容器資源使用
docker stats

# 查看磁碟使用
df -h

# 查看 Docker volume 使用
docker volume ls
docker system df
```

### 定期維護

**每週**:
- 檢查日誌是否有異常
- 確認所有容器運行正常

**每月**:
- 清理無用的 Docker 映像和容器
- 檢查資料庫大小

```bash
# 清理無用資源
docker system prune -a --volumes

# 查看資料庫大小
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
SELECT
    pg_size_pretty(pg_database_size('aichatbot_admin')) as db_size;
"
```

## 🔄 更新部署

當有新版本時：

```bash
# 1. 拉取最新代碼
git pull origin main

# 2. 構建前端（如果前端有變更）
cd knowledge-admin/frontend
npm install
npm run build
cd ../..

# 3. 重新構建並重啟服務
docker-compose -f docker-compose.prod.yml up -d --build

# 4. 檢查服務狀態
docker-compose -f docker-compose.prod.yml ps
```

## 🔒 安全建議

1. **使用 HTTPS**：
   - 在 Nginx 前加上 SSL/TLS（使用 Let's Encrypt）
   - 修改前端 API 配置使用 HTTPS

2. **環境變數保護**：
   - 確保 `.env` 檔案權限為 600
   - 不要將 `.env` 提交到 Git

3. **防火牆設定**：
   ```bash
   # 只開放必要端口
   sudo ufw allow 80/tcp    # HTTP
   sudo ufw allow 443/tcp   # HTTPS
   sudo ufw allow 22/tcp    # SSH
   sudo ufw enable
   ```

4. **定期備份**：
   ```bash
   # 備份數據庫
   docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > backup_$(date +%Y%m%d).sql

   # 備份到遠端
   scp backup_*.sql user@backup-server:/backups/
   ```

## 📝 變更清單

本次部署包含的主要變更：

- ✅ 優先級系統重構（0-10 分級 → 0/1 開關）
- ✅ 批量匯入統一優先級功能
- ✅ 前端 UI 優化（Checkbox + 優先級標記）
- ✅ RAG 加成公式優化（固定 +0.15）
- ✅ 完整 API 支援
- ✅ 環境變數配置更新

## 🆘 需要幫助？

- 📖 查看完整文檔：`docs/features/PRIORITY_SYSTEM.md`
- 📝 快速參考：`docs/guides/PRIORITY_QUICK_REFERENCE.md`
- 🐛 問題回報：GitHub Issues

---

**最後更新**: 2025-11-17
**適用版本**: commit `ffe6713` 及之後
