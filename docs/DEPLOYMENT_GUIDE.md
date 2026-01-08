# 線上部署指南

## 📋 部署前準備

### 1. 環境需求
- Docker 和 Docker Compose
- Git
- 域名（可選，用於 HTTPS）
- 至少 4GB RAM
- 20GB 磁碟空間

### 2. 環境變數
創建 `.env` 文件：
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

## 🚀 部署步驟

### 步驟 1：克隆代碼庫
```bash
git clone <your-repository-url>
cd AIChatbot
```

### 步驟 2：配置環境變數
```bash
cp .env.example .env
nano .env  # 編輯並填入 OPENAI_API_KEY
```

### 步驟 3：啟動服務
```bash
# 構建並啟動所有服務
docker-compose up -d --build

# 查看服務狀態
docker-compose ps

# 查看日誌（可選）
docker-compose logs -f
```

### 步驟 4：等待服務就緒
```bash
# 等待數據庫健康檢查通過
docker-compose exec postgres pg_isready -U aichatbot

# 檢查 API 服務
curl http://localhost:8000/docs
```

### 步驟 5：初始化權限系統
權限和角色已在數據庫初始化腳本中自動創建，包括：
- ✅ 6 個預設角色（超級管理員、知識庫管理員、測試人員等）
- ✅ 所有系統權限
- ✅ 角色與權限的關聯

### 步驟 6：創建第一個管理員帳號

**方法 1：交互式創建（推薦）**
```bash
docker-compose exec knowledge-admin-api python create_admin.py
```

按提示輸入：
- 帳號
- 密碼（兩次確認）
- Email
- 姓名（可選）

**方法 2：使用命令行參數**
```bash
docker-compose exec knowledge-admin-api python create_admin.py \
  --username admin \
  --password your_secure_password \
  --email admin@example.com \
  --full-name "系統管理員"
```

**創建成功後會顯示：**
```
✅ 成功創建管理員帳號
   帳號：admin
   Email：admin@example.com
   角色：超級管理員（擁有所有權限）
```

### 步驟 7：訪問管理後台
打開瀏覽器訪問：
```
http://your-server-ip:8087
```

使用剛才創建的帳號登入。

## 🔒 安全建議

### 1. 修改默認端口（生產環境）
編輯 `docker-compose.yml`：
```yaml
ports:
  - "8087:5173"  # 前端（建議改為非標準端口或使用反向代理）
  - "8000:8000"  # API（建議改為非標準端口或使用反向代理）
  - "5432:5432"  # 資料庫（建議移除或改為僅內網訪問）
```

### 2. 配置 HTTPS（使用 Nginx 反向代理）
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # 前端
    location / {
        proxy_pass http://localhost:8087;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. 修改數據庫密碼
編輯 `docker-compose.yml` 中的數據庫配置：
```yaml
environment:
  POSTGRES_PASSWORD: your_strong_password_here
  DB_PASSWORD: your_strong_password_here
```

### 4. 限制 CORS（生產環境）
編輯 `knowledge-admin/backend/app.py`：
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],  # 改為實際域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 5. 啟用防火牆
```bash
# 只開放必要端口
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
```

## 📊 服務說明

| 服務名稱 | 端口 | 說明 |
|---------|------|------|
| postgres | 5432 | PostgreSQL 資料庫 |
| redis | 6381 | Redis 緩存 |
| pgadmin | 5050 | 資料庫管理界面 |
| embedding-api | 5001 | Embedding 向量服務 |
| knowledge-admin-api | 8000 | 後台 API |
| knowledge-admin-web | 8087 | 管理後台前端 |
| rag-orchestrator | 8100 | RAG 協調服務 |

## 🔧 常用維護命令

### 查看服務狀態
```bash
docker-compose ps
```

### 查看日誌
```bash
# 查看所有服務日誌
docker-compose logs -f

# 查看特定服務日誌
docker-compose logs -f knowledge-admin-api
```

### 重啟服務
```bash
# 重啟所有服務
docker-compose restart

# 重啟特定服務
docker-compose restart knowledge-admin-api
```

### 停止服務
```bash
docker-compose down
```

### 更新代碼
```bash
git pull
docker-compose up -d --build
```

### 備份數據庫
```bash
docker-compose exec postgres pg_dump -U aichatbot aichatbot_admin > backup.sql
```

### 還原數據庫
```bash
cat backup.sql | docker-compose exec -T postgres psql -U aichatbot aichatbot_admin
```

## 🔍 故障排查

### 問題 1：服務無法啟動
```bash
# 檢查日誌
docker-compose logs

# 檢查端口佔用
netstat -tuln | grep -E '5432|6381|8000|8087|8100'
```

### 問題 2：無法連接資料庫
```bash
# 進入容器檢查
docker-compose exec postgres psql -U aichatbot -d aichatbot_admin -c "SELECT 1"
```

### 問題 3：前端無法訪問 API
檢查 `knowledge-admin/frontend/.env` 或構建配置中的 API 地址。

### 問題 4：權限系統未初始化
```bash
# 檢查權限和角色是否存在
docker-compose exec postgres psql -U aichatbot -d aichatbot_admin -c "SELECT COUNT(*) FROM permissions"
docker-compose exec postgres psql -U aichatbot -d aichatbot_admin -c "SELECT COUNT(*) FROM roles"
```

## 📝 初始化後的後續步驟

1. **登入管理後台**
   - 訪問 `http://your-server:8087`
   - 使用創建的管理員帳號登入

2. **創建其他角色（可選）**
   - 進入「角色管理」
   - 根據需要創建自訂角色
   - 分配適當的權限

3. **創建其他用戶**
   - 進入「用戶管理」
   - 新增用戶並分配角色

4. **測試權限系統**
   - 使用不同角色的帳號登入
   - 驗證權限控制是否正常

5. **開始使用系統**
   - 導入知識庫
   - 配置業者資料
   - 設置測試情境

## ⚠️ 注意事項

1. **首次部署時間**
   - 首次構建可能需要 5-10 分鐘
   - 等待所有服務的健康檢查通過

2. **數據持久化**
   - 數據存儲在 Docker volumes 中
   - 刪除容器不會丟失數據
   - 使用 `docker-compose down -v` 會刪除所有數據

3. **資源使用**
   - 建議至少 4GB RAM
   - 監控磁碟使用情況

4. **密碼安全**
   - 使用強密碼
   - 定期更換密碼
   - 不要在公開倉庫中提交包含密碼的配置文件

## 🆘 支援

如遇問題，請查看：
- 服務日誌：`docker-compose logs -f`
- API 文檔：`http://localhost:8000/docs`
- 數據庫狀態：`docker-compose exec postgres pg_isready`
