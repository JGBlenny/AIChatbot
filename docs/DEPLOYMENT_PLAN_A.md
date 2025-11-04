# 🚀 生產環境部署指南 - 方案 A（本地構建）

**目標域名**: chatai.jgbsmart.com
**部署端口**: 80
**適用場景**: 小規格伺服器（RAM ≤ 2GB）

---

## 📋 方案概述

**方案 A（本地構建 + 預構建部署）** 是針對小規格伺服器的最佳解決方案：

- ✅ **不需要在伺服器上構建前端**（避免 OOM）
- ✅ **部署速度快**（秒級啟動）
- ✅ **零記憶體壓力**（直接使用 nginx:alpine）
- ✅ **適合小規格機器**（512MB RAM 即可運行）

### 工作流程

```
開發機器                          生產伺服器
--------                          --------
1. npm run build       →          4. 解壓 dist.tar.gz
2. 打包 dist           →          5. docker-compose up -d
3. 上傳到伺服器        →          6. 驗證部署
```

---

## 🔧 前置準備

### 1. 開發機器要求

- Node.js 18+
- npm 或 yarn
- Git
- SSH 訪問生產伺服器
- 足夠的 RAM 構建前端（至少 2GB）

### 2. 生產伺服器要求

✅ **已完成檢查清單**：

- [ ] Docker 已安裝（`docker --version`）
- [ ] Docker Compose 已安裝（`docker-compose --version`）
- [ ] 防火牆開放 80 端口（`sudo ufw allow 80`）
- [ ] DNS 已配置（`nslookup chatai.jgbsmart.com`）
- [ ] 磁碟空間充足（至少 10GB 可用）
- [ ] SSH 訪問已設置
- [ ] 代碼已拉取到伺服器

---

## 🚀 部署步驟

### 方式 1: 使用自動化腳本（推薦）

#### 步驟 1: 在開發機器上構建並打包

```bash
# 1. 進入專案目錄
cd /path/to/AIChatbot

# 2. 執行本地構建腳本
bash scripts/deploy_local_build.sh
```

腳本會自動完成：
- ✅ 進入前端目錄
- ✅ 安裝依賴（如果需要）
- ✅ 構建前端（`npm run build`）
- ✅ 打包 dist 目錄為 `dist_YYYYMMDD_HHMMSS.tar.gz`

**輸出示例**：
```
✅ 本地構建完成！
📦 打包文件: dist_20251103_120000.tar.gz
📊 文件大小: 2.5M
```

#### 步驟 2: 上傳文件到伺服器

使用 SCP 上傳（替換為你的伺服器信息）：

```bash
# 設置變量（替換為實際值）
SERVER_USER="your-username"
SERVER_IP="your-server-ip"
SERVER_PATH="/path/to/AIChatbot"
ARCHIVE_NAME="dist_20251103_120000.tar.gz"

# 上傳打包文件
scp ${ARCHIVE_NAME} ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/

# 上傳配置文件
scp docker-compose.prod-prebuilt.yml ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/
scp knowledge-admin/frontend/nginx.conf ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/knowledge-admin/frontend/
scp scripts/deploy_server_prebuilt.sh ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/scripts/
```

或使用 rsync（更快，支持斷點續傳）：

```bash
rsync -avz --progress ${ARCHIVE_NAME} ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/
rsync -avz --progress docker-compose.prod-prebuilt.yml ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/
rsync -avz --progress knowledge-admin/frontend/nginx.conf ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/knowledge-admin/frontend/
rsync -avz --progress scripts/deploy_server_prebuilt.sh ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/scripts/
```

#### 步驟 3: 在伺服器上部署

SSH 到伺服器並執行部署腳本：

```bash
# 1. SSH 登入伺服器
ssh ${SERVER_USER}@${SERVER_IP}

# 2. 進入專案目錄
cd ${SERVER_PATH}

# 3. 執行部署腳本（使用剛上傳的打包文件名）
bash scripts/deploy_server_prebuilt.sh dist_20251103_120000.tar.gz
```

腳本會自動完成：
1. ✅ 備份資料庫
2. ✅ 執行資料庫遷移
3. ✅ 停止舊容器
4. ✅ 解壓 dist 目錄
5. ✅ 驗證配置文件
6. ✅ 啟動生產環境
7. ✅ 驗證部署

**成功輸出示例**：
```
🎉 部署完成！

訪問地址：
- 內部: http://localhost:80
- 外部: http://chatai.jgbsmart.com

✅ 前端訪問測試: 成功
✅ Nginx 運行檢查: 成功
✅ 端口綁定檢查: 成功
✅ 靜態文件檢查: 成功
```

---

### 方式 2: 手動部署

如果不想使用腳本，可以手動執行以下步驟：

#### 在開發機器上：

```bash
# 1. 構建前端
cd knowledge-admin/frontend
npm install
npm run build

# 2. 打包 dist
tar -czf dist.tar.gz dist/

# 3. 移動到專案根目錄
mv dist.tar.gz ../../

# 4. 上傳到伺服器
cd ../..
scp dist.tar.gz user@server:/path/to/AIChatbot/
scp docker-compose.prod-prebuilt.yml user@server:/path/to/AIChatbot/
scp knowledge-admin/frontend/nginx.conf user@server:/path/to/AIChatbot/knowledge-admin/frontend/
```

#### 在生產伺服器上：

```bash
# 1. 進入專案目錄
cd /path/to/AIChatbot

# 2. 備份資料庫
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin \
  > backup_$(date +%Y%m%d_%H%M%S).sql

# 3. 執行資料庫遷移（如果有）
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin \
  < database/fixes/fix_approve_function.sql

docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin \
  < database/fixes/fix_check_knowledge_function.sql

# 4. 停止舊容器
docker-compose stop knowledge-admin-web

# 5. 解壓 dist
tar -xzf dist.tar.gz -C knowledge-admin/frontend/

# 6. 啟動生產環境
docker-compose -f docker-compose.yml -f docker-compose.prod-prebuilt.yml up -d knowledge-admin-web

# 7. 檢查狀態
docker-compose ps knowledge-admin-web
curl -I http://localhost:80
```

---

## ✅ 部署驗證

### 自動驗證（腳本已包含）

如果使用自動化腳本，驗證會自動執行並顯示結果。

### 手動驗證步驟

#### 1. 容器狀態檢查

```bash
# 檢查容器運行狀態
docker-compose ps knowledge-admin-web

# 應顯示：
# - STATE: Up
# - PORTS: 0.0.0.0:80->80/tcp
```

#### 2. Nginx 檢查

```bash
# 確認使用 Nginx（不是 Vite）
docker-compose exec knowledge-admin-web nginx -v

# 應輸出: nginx version: nginx/x.x.x
```

#### 3. 網絡訪問測試

```bash
# 本地訪問
curl -I http://localhost:80
# 應返回: HTTP/1.1 200 OK

# 外部訪問（在本地電腦執行）
curl -I http://chatai.jgbsmart.com
# 應返回: HTTP/1.1 200 OK
```

#### 4. API 代理測試

```bash
# 測試 RAG API 代理
curl http://localhost:80/rag-api/v1/intents
# 應返回 JSON 數據

# 測試 Knowledge Admin API 代理
curl http://localhost:80/api/vendors
# 應返回 JSON 數據
```

#### 5. 靜態文件檢查

```bash
# 檢查 dist 文件是否正確掛載
docker-compose exec knowledge-admin-web ls -la /usr/share/nginx/html

# 應該看到：
# - index.html
# - assets/
# - favicon.ico
# 等前端文件
```

#### 6. 功能測試

在瀏覽器訪問 http://chatai.jgbsmart.com 並測試：

- [ ] 首頁載入正常
- [ ] 導航功能正常
- [ ] 業者管理頁面可訪問
- [ ] 知識庫管理可訪問
- [ ] Platform SOP 頁面可訪問（`/platform-sop`）
- [ ] Excel 匯入功能：
  - [ ] 點擊「📥 匯入 Excel」
  - [ ] 選擇業種（通用範本/包租業/代管業）
  - [ ] 上傳測試文件
  - [ ] 驗證匯入成功
- [ ] 知識庫審核功能正常
- [ ] 意圖列表顯示正常

#### 7. 日誌檢查

```bash
# 查看前端日誌（應無錯誤）
docker-compose logs --tail=50 knowledge-admin-web

# 持續監控
docker-compose logs -f knowledge-admin-web
```

---

## 🆘 故障排除

### 問題 1: 無法訪問 80 端口

**症狀**：
```
curl: (7) Failed to connect to localhost port 80
```

**排查步驟**：

```bash
# 1. 檢查容器狀態
docker-compose ps knowledge-admin-web

# 2. 檢查端口綁定
docker-compose port knowledge-admin-web 80

# 3. 檢查日誌
docker-compose logs knowledge-admin-web

# 4. 檢查防火牆
sudo ufw status
sudo iptables -L -n | grep 80
```

**解決方案**：

```bash
# 重啟容器
docker-compose -f docker-compose.yml -f docker-compose.prod-prebuilt.yml restart knowledge-admin-web

# 如果還不行，重新部署
docker-compose -f docker-compose.yml -f docker-compose.prod-prebuilt.yml down knowledge-admin-web
docker-compose -f docker-compose.yml -f docker-compose.prod-prebuilt.yml up -d knowledge-admin-web
```

### 問題 2: 404 Not Found（找不到靜態文件）

**症狀**: 訪問頁面返回 404 或白屏

**原因**: dist 目錄未正確掛載

**解決方案**：

```bash
# 1. 檢查 dist 目錄是否存在
ls -la knowledge-admin/frontend/dist/

# 2. 檢查容器內的文件
docker-compose exec knowledge-admin-web ls -la /usr/share/nginx/html

# 3. 如果文件不存在，重新解壓
tar -xzf dist_YYYYMMDD_HHMMSS.tar.gz -C knowledge-admin/frontend/

# 4. 重啟容器
docker-compose -f docker-compose.yml -f docker-compose.prod-prebuilt.yml restart knowledge-admin-web
```

### 問題 3: API 請求失敗

**症狀**: 前端顯示 API 錯誤或超時

**排查步驟**：

```bash
# 1. 檢查後端容器狀態
docker-compose ps rag-orchestrator knowledge-admin-api

# 2. 測試容器間網絡
docker-compose exec knowledge-admin-web ping rag-orchestrator

# 3. 檢查 nginx 配置
docker-compose exec knowledge-admin-web cat /etc/nginx/conf.d/default.conf

# 4. 查看後端日誌
docker-compose logs rag-orchestrator knowledge-admin-api
```

### 問題 4: Excel 上傳失敗（413 Request Entity Too Large）

**症狀**: 上傳 Excel 時顯示 413 錯誤

**解決方案**：

```bash
# 1. 確認 nginx.conf 包含上傳大小限制
grep "client_max_body_size" knowledge-admin/frontend/nginx.conf

# 應輸出: client_max_body_size 100M;

# 2. 如果沒有，添加到 nginx.conf 的 server 塊中
# 然後重啟容器
docker-compose -f docker-compose.yml -f docker-compose.prod-prebuilt.yml restart knowledge-admin-web
```

### 問題 5: 域名無法訪問

**症狀**: http://chatai.jgbsmart.com 無法訪問

**排查步驟**：

```bash
# 1. 檢查 DNS 解析
nslookup chatai.jgbsmart.com
dig chatai.jgbsmart.com

# 2. 檢查本地訪問是否正常
curl -I http://localhost:80

# 3. 檢查防火牆和安全組
sudo ufw status
# 雲服務商：檢查安全組規則是否允許 80 端口入站
```

**解決方案**：
- 確認 DNS A 記錄已指向伺服器 IP
- 等待 DNS 生效（可能需要幾分鐘到幾小時）
- 檢查雲服務商的安全組設定，確保允許 80 端口

---

## 🔄 回滾計畫

如果部署出現嚴重問題，可以快速回滾：

```bash
# 1. 停止生產容器
docker-compose stop knowledge-admin-web

# 2. 還原舊的 dist（如果有備份）
rm -rf knowledge-admin/frontend/dist
mv knowledge-admin/frontend/dist.backup.YYYYMMDD_HHMMSS knowledge-admin/frontend/dist

# 3. 重啟容器
docker-compose -f docker-compose.yml -f docker-compose.prod-prebuilt.yml up -d knowledge-admin-web

# 4. 還原資料庫（如果需要）
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin \
  < backup_YYYYMMDD_HHMMSS.sql

# 5. 驗證
curl -I http://localhost:80
```

---

## 🔄 更新部署

當需要更新前端時：

### 快速更新流程

```bash
# 1. 在開發機器上構建新版本
cd /path/to/AIChatbot
git pull origin main  # 拉取最新代碼
bash scripts/deploy_local_build.sh

# 2. 上傳到伺服器
scp dist_YYYYMMDD_HHMMSS.tar.gz user@server:/path/to/AIChatbot/

# 3. 在伺服器上重新部署
ssh user@server
cd /path/to/AIChatbot
bash scripts/deploy_server_prebuilt.sh dist_YYYYMMDD_HHMMSS.tar.gz
```

### 零停機更新（進階）

```bash
# 在伺服器上
cd /path/to/AIChatbot

# 解壓新的 dist 到臨時目錄
mkdir -p /tmp/new_dist
tar -xzf dist_YYYYMMDD_HHMMSS.tar.gz -C /tmp/new_dist

# 原子替換（幾乎零停機）
mv knowledge-admin/frontend/dist knowledge-admin/frontend/dist.old
mv /tmp/new_dist/dist knowledge-admin/frontend/dist

# Nginx 會自動讀取新文件，無需重啟容器
# 確認一切正常後刪除舊版本
rm -rf knowledge-admin/frontend/dist.old
```

---

## 📊 性能監控

### 資源使用檢查

```bash
# CPU 和記憶體使用
docker stats --no-stream knowledge-admin-web

# 應該非常低：
# - CPU: < 1%
# - MEM: 10-20MB（nginx:alpine 非常輕量）
```

### 磁碟空間檢查

```bash
# 檢查磁碟空間
df -h

# 清理舊的備份文件（保留最近 3 個）
ls -t backup_*.sql | tail -n +4 | xargs rm -f
ls -t dist_*.tar.gz | tail -n +4 | xargs rm -f
```

### 日誌管理

```bash
# 限制 Docker 日誌大小
# 在 docker-compose.prod-prebuilt.yml 中添加：
services:
  knowledge-admin-web:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## 🎯 最佳實踐

### 1. 自動化部署腳本

創建一鍵部署腳本（在開發機器上）：

```bash
# deploy.sh
#!/bin/bash
set -e

# 配置
SERVER="user@server-ip"
SERVER_PATH="/path/to/AIChatbot"

# 構建
bash scripts/deploy_local_build.sh

# 獲取最新的打包文件名
ARCHIVE=$(ls -t dist_*.tar.gz | head -1)

# 上傳
echo "上傳 ${ARCHIVE}..."
scp ${ARCHIVE} ${SERVER}:${SERVER_PATH}/

# 部署
echo "部署到伺服器..."
ssh ${SERVER} "cd ${SERVER_PATH} && bash scripts/deploy_server_prebuilt.sh ${ARCHIVE}"

echo "✅ 部署完成！"
```

### 2. 定期備份

設置每日自動備份（在伺服器上）：

```bash
# 創建備份腳本
cat > /usr/local/bin/backup-aichatbot.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/aichatbot"
mkdir -p ${BACKUP_DIR}
cd /path/to/AIChatbot

# 備份資料庫
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin \
  > ${BACKUP_DIR}/db_$(date +%Y%m%d_%H%M%S).sql

# 備份 dist
tar -czf ${BACKUP_DIR}/dist_$(date +%Y%m%d_%H%M%S).tar.gz \
  knowledge-admin/frontend/dist/

# 只保留最近 7 天的備份
find ${BACKUP_DIR} -name "*.sql" -mtime +7 -delete
find ${BACKUP_DIR} -name "*.tar.gz" -mtime +7 -delete

echo "✅ 備份完成: $(date)"
EOF

chmod +x /usr/local/bin/backup-aichatbot.sh

# 添加到 crontab（每天凌晨 2 點執行）
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup-aichatbot.sh") | crontab -
```

### 3. 監控告警

設置簡單的健康檢查（在伺服器上）：

```bash
# 創建健康檢查腳本
cat > /usr/local/bin/healthcheck-aichatbot.sh << 'EOF'
#!/bin/bash
if ! curl -sf http://localhost:80 > /dev/null; then
    echo "❌ 前端服務異常: $(date)" | tee -a /var/log/aichatbot-health.log
    # 可以在這裡添加告警通知（郵件、Slack 等）
    # 自動重啟
    cd /path/to/AIChatbot
    docker-compose -f docker-compose.yml -f docker-compose.prod-prebuilt.yml restart knowledge-admin-web
fi
EOF

chmod +x /usr/local/bin/healthcheck-aichatbot.sh

# 每 5 分鐘檢查一次
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/healthcheck-aichatbot.sh") | crontab -
```

---

## 📁 相關文件

- `docker-compose.prod-prebuilt.yml` - 預構建模式的 Docker Compose 配置
- `scripts/deploy_local_build.sh` - 本地構建腳本
- `scripts/deploy_server_prebuilt.sh` - 伺服器部署腳本
- `knowledge-admin/frontend/nginx.conf` - Nginx 配置文件

---

## 🎉 總結

**方案 A 的優勢**：
- ✅ **無需在伺服器上構建**，避免 OOM 問題
- ✅ **部署速度極快**，從上傳到啟動不到 1 分鐘
- ✅ **資源消耗極低**，Nginx 只需 10-20MB 記憶體
- ✅ **穩定可靠**，靜態文件服務非常穩定

**適用場景**：
- 小規格伺服器（≤ 2GB RAM）
- 需要快速部署和更新
- 預算有限的專案
- 不需要在伺服器上進行開發

如有任何問題或需要協助，請查看故障排除部分或聯絡技術支援。

**🎉 祝部署順利！**
