# 🚀 EC2 生產環境部署檢查清單（只開放 8087）

**部署方式**: EC2 + Docker Compose
**對外端口**: 僅 8087 (前端)
**環境變數**: .env 未上傳 Git ✅

---

## ✅ 已經安全的配置

由於你只開放 8087 端口，以下問題**已經不是問題**：

### 1. ✅ PostgreSQL 端口 5432
- **狀態**: 安全 ✅
- **原因**: EC2 防火牆未開放，只有容器內部可訪問
- **無需修改**

### 2. ✅ Redis 端口 6381
- **狀態**: 安全 ✅
- **原因**: EC2 防火牆未開放，只有容器內部可訪問
- **無需修改**

### 3. ✅ PgAdmin 端口 5050
- **狀態**: 安全 ✅
- **原因**: EC2 防火牆未開放，外部無法訪問
- **建議**: 仍可移除（生產環境不需要）

### 4. ✅ 後端 API 8000 和 RAG API 8100
- **狀態**: 安全 ✅
- **原因**: 通過 Nginx 反向代理訪問（/api/ 和 /rag-api/）
- **無需修改**

### 5. ✅ API Keys 洩露風險
- **狀態**: 風險大幅降低 ✅
- **原因**: .env 未上 Git，只在 EC2 服務器上
- **建議**: 仍需注意 EC2 訪問控制

---

## 🔴 仍需解決的問題（8 個）

### 1. ❌ CORS 仍然開放 allow_origins=["*"]

**問題**: 即使只開放 8087，惡意網站仍可通過 Nginx proxy 調用 API

**當前風險**: 🟠 中等（已降低，但仍存在）

**攻擊場景**:
```javascript
// 惡意網站 evil.com 的代碼
fetch('https://your-ec2-domain.com:8087/api/vendors/1/chat', {
  method: 'POST',
  body: JSON.stringify({ question: '...' }),
  credentials: 'include'  // 帶上用戶 cookie
})
```

**解決方案**:
```python
# rag-orchestrator/app.py & knowledge-admin/backend/app.py
ALLOWED_ORIGINS = [
    "https://your-domain.com",
    "https://your-ec2-public-ip:8087",
    "http://localhost:8087"  # 開發環境
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
```

**優先級**: 🟠 中（1-2 小時）

---

### 2. ❌ 缺少 API 認證（仍然是問題！）

**問題**: 任何知道你域名的人都能調用 API

**當前風險**: 🔴 高

**為什麼仍然是問題**:
- 惡意用戶可以直接通過瀏覽器 F12 看到 API 請求
- 複製請求 → 無限調用 → OpenAI 成本暴增
- 可以讀取所有業者數據

**解決方案 A: API Key（最簡單，2 小時）**

```python
# middleware/auth.py
from fastapi import Security, HTTPException, Header

async def verify_api_key(x_api_key: str = Header(None)):
    """驗證 API Key"""
    valid_keys = os.getenv("VALID_API_KEYS", "").split(",")

    if not x_api_key or x_api_key not in valid_keys:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

# 在路由中使用
@router.post("/chat")
async def chat(
    request: ChatRequest,
    api_key: str = Depends(verify_api_key)
):
    # ... 原有邏輯
```

**前端配置**:
```javascript
// src/config/api.js
const API_KEY = import.meta.env.VITE_API_KEY;

axios.defaults.headers.common['X-API-Key'] = API_KEY;
```

**環境變數**:
```bash
# .env (服務器端)
VALID_API_KEYS=your-random-api-key-here,another-key-for-backup

# .env.production (前端)
VITE_API_KEY=your-random-api-key-here
```

**優先級**: 🔴 高（2 小時）

---

### 3. ❌ 缺少 Rate Limiting

**問題**: 即使有 API Key，仍可能被濫用

**當前風險**: 🟠 中

**解決方案**:

```python
# requirements.txt
slowapi==0.1.9

# app.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 在路由中使用
@router.post("/chat")
@limiter.limit("100/hour")  # 每小時 100 次
async def chat(request: Request, chat_request: ChatRequest):
    # ... 原有邏輯
```

**優先級**: 🟠 中（1 小時）

---

### 4. ❌ 前端硬編碼 localhost URL（仍需修改）

**問題位置**: 10+ 個前端 Vue 文件

**當前風險**: 🔴 高（生產環境會失效）

**為什麼仍是問題**:
```javascript
// ❌ 當前代碼
const response = await axios.get('http://localhost:8100/api/v1/intents');
// 在 EC2 上會失敗！因為 localhost 指向用戶的電腦，不是服務器
```

**解決方案**:

**步驟 1: 創建 API 配置文件**
```javascript
// src/config/api.js
const getBaseURL = () => {
  // 生產環境：使用相對路徑（通過 Nginx proxy）
  if (import.meta.env.PROD) {
    return '';  // 空字符串 = 相對路徑
  }
  // 開發環境：使用 localhost
  return 'http://localhost:8100';
};

export const API_BASE_URL = getBaseURL();

export const API_ENDPOINTS = {
  chat: `${API_BASE_URL}/rag-api/v1/chat`,
  intents: `${API_BASE_URL}/rag-api/v1/intents`,
  vendors: `${API_BASE_URL}/api/vendors`,
  // ... 其他端點
};
```

**步驟 2: 更新所有組件**（需修改 10+ 個文件）
```javascript
// ❌ 之前
const response = await axios.get('http://localhost:8100/api/v1/intents');

// ✅ 之後
import { API_ENDPOINTS } from '@/config/api';
const response = await axios.get(API_ENDPOINTS.intents);
```

**受影響文件清單**:
1. `VendorSOPManager.vue`
2. `UnclearQuestionReviewTab.vue`
3. `KnowledgeReviewTab.vue`
4. `IntentReviewTab.vue`
5. `PlatformSOPView.vue`
6. `PlatformSOPEditView.vue`
7. `BacktestView.vue`
8. ... 等 3+ 個文件

**優先級**: 🔴 極高（2-3 小時，否則生產環境無法使用）

---

### 5. ❌ Nginx 缺少安全 Headers

**問題位置**: `knowledge-admin/frontend/nginx.conf`

**當前風險**: 🟡 中低

**解決方案**:
```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # ✅ 添加安全 Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # ✅ 啟用 Gzip 壓縮
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # ✅ 靜態文件緩存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://knowledge-admin-api:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /rag-api/ {
        rewrite ^/rag-api/(.*)$ /api/$1 break;
        proxy_pass http://rag-orchestrator:8100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**優先級**: 🟡 中（30 分鐘）

---

### 6. ❌ 缺少 HTTPS/SSL（如果使用自定義域名）

**問題**: 如果你使用自定義域名，必須配置 HTTPS

**當前風險**: 🔴 高（如果有域名）/ 🟢 低（如果只用 IP）

**解決方案 A: 使用 Let's Encrypt（免費）**

```bash
# 1. 安裝 Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# 2. 獲取 SSL 證書
sudo certbot --nginx -d yourdomain.com

# 3. 自動續期
sudo certbot renew --dry-run
```

**解決方案 B: 使用 AWS Certificate Manager（如果用 ALB）**

**優先級**:
- 🔴 高（有域名）
- 🟢 低（只用 IP）

---

### 7. ⚠️ 生產環境使用開發模式

**問題位置**: `docker-compose.yml`

**當前配置**:
```yaml
knowledge-admin-web:
  command: npm run dev  # ❌ 開發模式
  volumes:
    - ./knowledge-admin/frontend/src:/app/src  # ❌ 掛載源碼
```

**風險**: 🟡 中（性能較差，但不影響安全）

**解決方案**:

**創建部署腳本**:
```bash
#!/bin/bash
# scripts/deploy_production.sh

echo "🚀 部署生產環境..."

# 1. 停止開發環境
docker-compose down

# 2. 構建生產版本
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# 3. 啟動生產環境
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 4. 檢查健康狀態
sleep 10
docker-compose ps

echo "✅ 部署完成！"
echo "前端: http://your-ec2-ip:8087"
```

**docker-compose.prod.yml** (完善現有文件):
```yaml
services:
  knowledge-admin-web:
    build:
      context: ./knowledge-admin/frontend
      target: production
    command: nginx -g 'daemon off;'
    volumes:
      - ./knowledge-admin/frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      # ✅ 不掛載源碼
    environment:
      - NODE_ENV=production
    restart: always

  knowledge-admin-api:
    volumes:
      # ✅ 只保留必要的掛載
      - ./output:/app/output
    restart: always

  rag-orchestrator:
    volumes: []  # ✅ 不掛載源碼
    restart: always
```

**優先級**: 🟡 中（1 小時）

---

### 8. ⚠️ 缺少日誌和監控

**問題**: 生產環境需要知道系統狀態和錯誤

**當前風險**: 🟡 中（影響維護）

**解決方案 A: 基本日誌（最簡單，1 小時）**

```python
# services/logger.py
import logging
import sys

def setup_logger(name: str):
    """配置日誌"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

# 使用
logger = setup_logger(__name__)
logger.info("Chat request received", extra={"vendor_id": 1})
logger.error("Database error", exc_info=True)
```

**查看日誌**:
```bash
# 實時查看
docker-compose logs -f rag-orchestrator

# 保存到文件
docker-compose logs rag-orchestrator > /var/log/rag-orchestrator.log
```

**解決方案 B: CloudWatch Logs（AWS 原生，推薦）**

```bash
# 安裝 CloudWatch agent
sudo wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb

# 配置日誌收集
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -c file:/opt/aws/cloudwatch-config.json \
  -s
```

**優先級**: 🟡 中（1-2 小時）

---

## 📋 優先級總結（只需修復 8 個問題）

### 🔴 必須立即解決（否則無法使用）

| 問題 | 影響 | 時間 |
|------|------|------|
| 1. 前端硬編碼 localhost | 生產環境 API 失效 | 2-3h |
| 2. 缺少 API 認證 | OpenAI 成本風險 | 2h |

**總計**: 4-5 小時（半天內完成）

---

### 🟠 強烈建議解決（安全和性能）

| 問題 | 影響 | 時間 |
|------|------|------|
| 3. CORS 開放 | CSRF 風險 | 1h |
| 4. Rate Limiting | 濫用風險 | 1h |
| 5. HTTPS/SSL（如有域名） | 數據加密 | 1h |
| 6. 生產模式部署 | 性能優化 | 1h |

**總計**: 4 小時（半天內完成）

---

### 🟡 建議解決（維護便利）

| 問題 | 影響 | 時間 |
|------|------|------|
| 7. Nginx 安全 Headers | 額外防護 | 30min |
| 8. 日誌監控 | 問題排查 | 1-2h |

**總計**: 1.5-2.5 小時

---

## 🎯 最小部署方案（1 天完成）

如果時間緊迫，按這個順序：

### 上午（4 小時）
1. ✅ **修復前端 localhost URL**（2-3h）
   - 創建 API 配置文件
   - 更新 10+ 個 Vue 組件
   - 測試開發和生產模式

2. ✅ **添加 API Key 認證**（1-2h）
   - 實施 API Key 驗證
   - 前端配置 Header
   - 測試認證流程

### 下午（3 小時）
3. ✅ **配置 CORS 白名單**（30min）
4. ✅ **添加 Rate Limiting**（1h）
5. ✅ **配置生產模式部署**（1h）
6. ✅ **測試完整流程**（30min）

---

## ✅ 部署檢查清單（簡化版）

**部署前必須完成**:
- [ ] 前端 URL 已改為相對路徑或環境變數
- [ ] API Key 認證已實施
- [ ] CORS 已配置白名單
- [ ] Rate Limiting 已配置
- [ ] docker-compose.prod.yml 已配置
- [ ] Nginx 配置已更新（安全 Headers）
- [ ] 基本日誌已配置

**可選但建議**:
- [ ] HTTPS/SSL 已配置（如有域名）
- [ ] CloudWatch Logs 已配置
- [ ] 健康檢查已實施

---

## 🚀 快速部署命令

```bash
# 1. 確認 EC2 安全組只開放 8087
# AWS Console > EC2 > Security Groups > Inbound Rules
# 應該只有: Custom TCP | 8087 | 0.0.0.0/0

# 2. 連接到 EC2
ssh -i your-key.pem ubuntu@your-ec2-ip

# 3. 更新代碼
cd /path/to/AIChatbot
git pull origin main

# 4. 更新環境變數
nano .env  # 添加 VALID_API_KEYS, ALLOWED_ORIGINS

# 5. 部署生產環境
bash scripts/deploy_production.sh

# 6. 檢查狀態
docker-compose ps
curl http://localhost:8087/health

# 7. 查看日誌
docker-compose logs -f --tail=100
```

---

## 📊 風險對比

| 風險 | 開發環境 | 只開 8087 | 完整修復 |
|------|----------|-----------|----------|
| 數據庫被攻擊 | 🔴 高 | ✅ 安全 | ✅ 安全 |
| API Keys 洩露 | 🔴 高 | 🟡 中 | ✅ 安全 |
| API 濫用 | 🔴 極高 | 🟠 高 | ✅ 安全 |
| CSRF 攻擊 | 🔴 高 | 🟠 中 | ✅ 安全 |
| 前端無法使用 | 🟢 正常 | 🔴 失效 | ✅ 正常 |

---

**結論**: 你的配置已經比標準開發環境安全很多！只需要修復 **2 個關鍵問題**（前端 URL + API 認證）就能部署，其他 6 個問題可以逐步改進。

**預估總時間**: 4-8 小時（1 個工作日內完成）

