# 🚀 生產環境部署檢查清單

**分析時間**: 2025-10-29
**當前環境**: Development
**目標環境**: Production
**分析方式**: Ultrathink 全面盤查

---

## 📋 執行摘要

經過全面盤查，發現 **21 個關鍵問題** 需要在部署生產環境前解決：

- 🔴 **嚴重安全問題**: 8 項（API Keys 洩露、CORS 開放、認證缺失）
- 🟠 **重要配置問題**: 7 項（硬編碼 URL、環境變數管理）
- 🟡 **性能優化問題**: 4 項（日誌過多、缺少監控）
- 🔵 **維護改進建議**: 2 項（文檔、備份策略）

**預估修復時間**: 16-24 工作小時
**建議優先級**: 先解決紅色警告（1-3 天），再處理橙色和黃色項目（3-5 天）

---

## 🔴 嚴重安全問題（必須立即解決）

### 1. ❌ API Keys 和敏感資訊洩露

**問題位置**: `.env` (Lines 2, 70-71)

```bash
# ❌ 明文儲存的 API Keys
OPENAI_API_KEY=sk-proj-hOD5TuV5gt9rxOnhJLtq...（完整 key 洩露）
AWS_ACCESS_KEY_ID=AKIAZCV2LGRI7JOCEDQ4
AWS_SECRET_ACCESS_KEY=JDbRrKqfnG7rP9Bx0BLQ...
```

**風險等級**: 🔴 極高
**影響**:
- OpenAI API 濫用（每月可能數千至數萬美元損失）
- AWS 資源被盜用（S3 bucket 可能被清空或惡意上傳）
- 數據洩露風險

**解決方案**:

1. **立即撤銷所有洩露的 Keys**:
   ```bash
   # 1. 前往 OpenAI Platform 撤銷舊 key
   # 2. 前往 AWS IAM 刪除並重新生成 Access Key
   ```

2. **使用環境變數或密鑰管理服務**:
   ```bash
   # 選項 A: 使用 AWS Secrets Manager
   aws secretsmanager create-secret \
     --name aichatbot/openai-api-key \
     --secret-string "your-new-key"

   # 選項 B: 使用 Docker Secrets（推薦）
   echo "your-new-key" | docker secret create openai_api_key -
   ```

3. **更新 .env.example（移除真實 keys）**:
   ```bash
   # .env.example
   OPENAI_API_KEY=your_openai_api_key_here
   AWS_ACCESS_KEY_ID=your_aws_access_key_here
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
   ```

4. **確保 .env 在 .gitignore 中**:
   ```bash
   # ✅ 已在 .gitignore 第 29 行，但需確認沒有被 commit
   git log --all --full-history -- .env  # 檢查歷史記錄

   # 如果發現已提交，使用 BFG Repo-Cleaner 清除歷史
   ```

---

### 2. ❌ CORS 完全開放（allow_origins=["*"]）

**問題位置**:
- `rag-orchestrator/app.py` (Line ~120)
- `knowledge-admin/backend/app.py` (Line ~50)

```python
# ❌ 當前配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 任何域名都能訪問！
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**風險等級**: 🔴 高
**影響**:
- CSRF 攻擊風險
- 數據竊取風險
- 惡意網站可冒充前端調用 API

**解決方案**:

```python
# ✅ 生產環境配置
import os

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "https://yourdomain.com,https://admin.yourdomain.com"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # 只允許特定域名
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # 明確指定方法
    allow_headers=["Content-Type", "Authorization"],
)
```

**docker-compose.yml 配置**:
```yaml
rag-orchestrator:
  environment:
    ALLOWED_ORIGINS: "https://yourdomain.com,https://admin.yourdomain.com"
```

---

### 3. ❌ 缺少 API 認證和授權機制

**問題位置**: 所有 API 端點（knowledge-admin, rag-orchestrator）

**現狀**:
- ❌ 沒有 API Key 驗證
- ❌ 沒有 JWT Token 認證
- ❌ 沒有 Rate Limiting
- ❌ 任何人都能直接訪問 API

**風險等級**: 🔴 極高
**影響**:
- API 濫用（OpenAI API 成本暴增）
- 數據被任意讀取或修改
- DDoS 攻擊無防護

**解決方案**:

**階段 1: 實施 API Key 認證（2-4 小時）**

```python
# services/auth_service.py
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """驗證 API Key"""
    valid_keys = os.getenv("VALID_API_KEYS", "").split(",")

    if not api_key or api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key"
        )
    return api_key

# 在路由中使用
@router.post("/chat")
async def chat(
    request: ChatRequest,
    api_key: str = Depends(verify_api_key)  # 添加認證
):
    # ... 原有邏輯
```

**階段 2: 實施 Rate Limiting（1-2 小時）**

```python
# 使用 slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/chat")
@limiter.limit("100/hour")  # 每小時 100 次請求
async def chat(request: ChatRequest):
    # ... 原有邏輯
```

**階段 3: （可選）JWT Token 認證（4-8 小時）**

適用於需要用戶登入的場景。

---

### 4. ❌ 資料庫密碼過於簡單且硬編碼

**問題位置**:
- `.env` (Lines 5-9)
- `docker-compose.yml` (Lines 7-9, 69-73)

```bash
# ❌ 弱密碼
DB_PASSWORD=aichatbot_password
POSTGRES_PASSWORD=aichatbot_password
```

**風險等級**: 🔴 高
**影響**:
- 資料庫被入侵風險
- 敏感數據（業者資料、用戶問題）洩露

**解決方案**:

```bash
# 1. 生成強密碼
openssl rand -base64 32

# 2. 使用 Docker Secrets 管理
echo "your-strong-password-here" | docker secret create postgres_password -

# 3. 更新 docker-compose.yml
postgres:
  environment:
    POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
  secrets:
    - postgres_password

secrets:
  postgres_password:
    external: true
```

---

### 5. ❌ PgAdmin 暴露在公網（端口 5050）

**問題位置**: `docker-compose.yml` (Lines 36-48)

```yaml
# ❌ 當前配置
pgadmin:
  ports:
    - "5050:80"  # 任何人都能訪問！
  environment:
    PGADMIN_DEFAULT_PASSWORD: admin  # 弱密碼
```

**風險等級**: 🔴 高
**影響**:
- 資料庫管理介面暴露
- 可能被用來執行惡意 SQL

**解決方案**:

**選項 A: 完全移除（推薦）**
```yaml
# 生產環境不需要 PgAdmin
# 直接註釋或刪除整個 pgadmin 服務
```

**選項 B: 限制訪問**
```yaml
pgadmin:
  ports:
    - "127.0.0.1:5050:80"  # 只允許本地訪問
  environment:
    PGADMIN_DEFAULT_PASSWORD: ${PGADMIN_PASSWORD}  # 使用強密碼
  profiles:
    - debug  # 只在 debug profile 時啟動
```

---

### 6. ❌ Redis 端口暴露且無密碼保護

**問題位置**: `docker-compose.yml` (Lines 22-33)

```yaml
# ❌ 當前配置
redis:
  ports:
    - "6381:6379"  # 外部可訪問
  # ❌ 沒有密碼保護
```

**風險等級**: 🟠 中高
**影響**:
- 緩存數據可能被讀取或刪除
- Redis 可能被用作跳板攻擊

**解決方案**:

```yaml
redis:
  command: redis-server --requirepass ${REDIS_PASSWORD}
  ports:
    - "127.0.0.1:6381:6379"  # 只允許本地訪問
  environment:
    REDIS_PASSWORD: ${REDIS_PASSWORD}

# .env
REDIS_PASSWORD=your-strong-redis-password
```

**更新應用配置**:
```python
# services/cache_service.py
self.redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    password=os.getenv("REDIS_PASSWORD"),  # 添加密碼
    decode_responses=True
)
```

---

### 7. ❌ PostgreSQL 端口 5432 暴露在公網

**問題位置**: `docker-compose.yml` (Lines 10-11)

```yaml
# ❌ 當前配置
postgres:
  ports:
    - "5432:5432"  # 任何人都能嘗試連接
```

**風險等級**: 🔴 極高
**影響**:
- 暴力破解攻擊
- 數據庫直接被入侵
- 敏感數據洩露

**解決方案**:

```yaml
# ✅ 生產環境配置
postgres:
  ports:
    - "127.0.0.1:5432:5432"  # 只允許本地連接
  # 或者完全移除 ports（容器內部訪問即可）
  # ports: []  # 不暴露任何端口
```

---

### 8. ❌ vite.config.js 中的 ngrok allowedHosts 配置

**問題位置**: `knowledge-admin/frontend/vite.config.js` (Lines 16-20)

```javascript
// ❌ 開發環境配置
allowedHosts: [
  '.ngrok-free.app',  // 生產環境不需要
  '.ngrok.io',
  'localhost'
],
```

**風險等級**: 🟡 低
**影響**:
- 生產環境不應使用 ngrok
- 可能被用於繞過安全限制

**解決方案**:

**使用環境變數區分**:
```javascript
// vite.config.js
export default defineConfig(({ mode }) => ({
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: mode === 'development'
      ? ['.ngrok-free.app', '.ngrok.io', 'localhost']
      : undefined,  // 生產環境不需要
  }
}))
```

---

## 🟠 重要配置問題（高優先級）

### 9. ⚠️ 前端硬編碼 localhost URL

**問題位置**: 10+ 個前端文件

```javascript
// ❌ 硬編碼
const RAG_API = 'http://localhost:8100/api/v1';
await axios.get('http://localhost:8100/api/v1/knowledge-candidates/pending');
```

**受影響文件**:
- `VendorSOPManager.vue`
- `UnclearQuestionReviewTab.vue`
- `KnowledgeReviewTab.vue`
- `IntentReviewTab.vue`
- `PlatformSOPView.vue`
- ... 等 6+ 個文件

**風險等級**: 🟠 高
**影響**:
- 生產環境 API 調用失敗
- 無法正常使用

**解決方案**:

**步驟 1: 創建環境變數配置文件**

```javascript
// src/config/api.js
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
const RAG_API_BASE_URL = import.meta.env.VITE_RAG_API_BASE_URL || '';

export const API_ENDPOINTS = {
  // Knowledge Admin API
  knowledgeCandidates: `${API_BASE_URL}/api/knowledge-candidates`,
  vendors: `${API_BASE_URL}/api/vendors`,

  // RAG Orchestrator API
  chat: `${RAG_API_BASE_URL}/api/v1/chat`,
  intents: `${RAG_API_BASE_URL}/api/v1/intents`,
  unclearQuestions: `${RAG_API_BASE_URL}/api/v1/unclear-questions`,
};

export default API_ENDPOINTS;
```

**步驟 2: 創建環境變數文件**

```bash
# .env.development
VITE_API_BASE_URL=http://localhost:8000
VITE_RAG_API_BASE_URL=http://localhost:8100

# .env.production
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_RAG_API_BASE_URL=https://rag.yourdomain.com
```

**步驟 3: 更新所有組件**

```javascript
// ❌ 之前
const response = await axios.get('http://localhost:8100/api/v1/intents');

// ✅ 之後
import API_ENDPOINTS from '@/config/api';
const response = await axios.get(API_ENDPOINTS.intents);
```

**預估工作量**: 2-3 小時（需要修改 10+ 個文件）

---

### 10. ⚠️ Docker Compose 使用開發模式

**問題位置**: `docker-compose.yml` (Lines 95-115, 199-206)

```yaml
# ❌ 開發模式配置
knowledge-admin-web:
  command: npm run dev  # 開發模式
  volumes:
    - ./knowledge-admin/frontend/src:/app/src  # 源碼掛載
  environment:
    - NODE_ENV=development

rag-orchestrator:
  volumes:
    - ./rag-orchestrator/routers:/app/routers  # 源碼掛載
    - ./rag-orchestrator/services:/app/services
```

**風險等級**: 🟠 高
**影響**:
- 性能較差（熱重載機制開啟）
- 安全性低（源碼暴露）
- 錯誤訊息詳細（洩露內部信息）

**解決方案**:

**創建 docker-compose.prod.yml**（已存在，但需完善）:

```yaml
# docker-compose.prod.yml
services:
  # 前端：使用 Nginx 提供靜態文件
  knowledge-admin-web:
    build:
      context: ./knowledge-admin/frontend
      target: production  # 使用 production stage
    restart: always
    volumes:
      - ./knowledge-admin/frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    environment:
      - NODE_ENV=production
    # ✅ 移除源碼掛載

  # 後端 API
  knowledge-admin-api:
    restart: always
    volumes:
      # ✅ 移除源碼掛載，只保留必要的數據卷
      - ./output:/app/output
      - ./scripts:/app/scripts:ro
    environment:
      - PYTHON_ENV=production

  # RAG Orchestrator
  rag-orchestrator:
    restart: always
    volumes: []  # ✅ 移除所有源碼掛載
    environment:
      - PYTHON_ENV=production
```

**部署命令**:
```bash
# 開發環境
docker-compose up -d

# 生產環境
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

### 11. ⚠️ 缺少 .env 環境變數驗證

**問題**: 如果忘記設置某個環境變數，服務會靜默失敗或使用錯誤的默認值

**解決方案**:

```python
# services/config_validator.py
import os
import sys

REQUIRED_ENV_VARS = [
    "OPENAI_API_KEY",
    "DB_HOST",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "EMBEDDING_API_URL",
]

OPTIONAL_ENV_VARS = {
    "REDIS_PASSWORD": "建議設置 Redis 密碼",
    "ALLOWED_ORIGINS": "建議限制 CORS origins",
}

def validate_environment():
    """驗證必要的環境變數"""
    missing = []
    warnings = []

    # 檢查必要變數
    for var in REQUIRED_ENV_VARS:
        if not os.getenv(var):
            missing.append(var)

    # 檢查可選但建議的變數
    for var, message in OPTIONAL_ENV_VARS.items():
        if not os.getenv(var):
            warnings.append(f"{var}: {message}")

    if missing:
        print(f"❌ 缺少必要的環境變數: {', '.join(missing)}")
        sys.exit(1)

    if warnings:
        print("⚠️  建議設置以下環境變數:")
        for warning in warnings:
            print(f"   - {warning}")

    print("✅ 環境變數驗證通過")

# 在 app.py 啟動時調用
if __name__ == "__main__":
    from services.config_validator import validate_environment
    validate_environment()
    # ... 啟動應用
```

---

### 12. ⚠️ 前端生產構建配置缺失

**問題位置**: `knowledge-admin/frontend/vite.config.js`

**缺少的優化配置**:

```javascript
// vite.config.js
export default defineConfig({
  // ... 現有配置

  build: {
    // 生產環境優化
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,  // 移除 console.log
        drop_debugger: true,
      },
    },
    rollupOptions: {
      output: {
        // 代碼分割
        manualChunks: {
          'vendor': ['vue', 'vue-router'],
          'ui': ['element-plus'],
          'utils': ['axios', 'lodash'],
        },
      },
    },
    chunkSizeWarningLimit: 1000,
    sourcemap: false,  // 生產環境不生成 sourcemap
  },
})
```

---

### 13. ⚠️ Nginx 缺少安全 Headers

**問題位置**: `knowledge-admin/frontend/nginx.conf`

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
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

    # ✅ 啟用 Gzip 壓縮
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json;

    # ✅ 靜態資源緩存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf)$ {
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

        # ✅ 超時設置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

---

### 14. ⚠️ 缺少健康檢查端點

**問題**: 生產環境需要健康檢查來監控服務狀態

**解決方案**:

```python
# rag-orchestrator/app.py
@app.get("/health")
async def health_check():
    """健康檢查端點"""
    try:
        # 檢查資料庫連接
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")

        # 檢查 Redis 連接
        if cache_service:
            cache_service.redis_client.ping()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "database": "ok",
                "redis": "ok",
                "embedding_api": "ok"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }, 503
```

**在 docker-compose.yml 中配置**:
```yaml
rag-orchestrator:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8100/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
```

---

### 15. ⚠️ 缺少請求日誌和監控

**問題**: 目前有 452 個 `print()` 語句，生產環境需要結構化日誌

**解決方案**:

**步驟 1: 配置 Python Logging**

```python
# services/logger.py
import logging
import sys
from datetime import datetime

def setup_logger(name: str, level: str = "INFO"):
    """設置結構化日誌"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # JSON Formatter（生產環境）
    formatter = logging.Formatter(
        '{"time": "%(asctime)s", "level": "%(levelname)s", '
        '"logger": "%(name)s", "message": "%(message)s", '
        '"function": "%(funcName)s", "line": %(lineno)d}'
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    return logger

# 使用
logger = setup_logger(__name__)
logger.info("RAG Orchestrator started")
logger.error("Database connection failed", exc_info=True)
```

**步驟 2: 替換所有 print() 為 logger**

```python
# ❌ 之前
print(f"✅ 資料庫連接池已建立")

# ✅ 之後
logger.info("Database connection pool established", extra={
    "min_size": 2,
    "max_size": 10
})
```

**預估工作量**: 8-10 小時（需要替換 452 個 print 語句）

**步驟 3: 添加請求日誌中間件**

```python
# middleware/logging_middleware.py
import time
from fastapi import Request

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """記錄所有 HTTP 請求"""
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info("HTTP Request", extra={
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "process_time": f"{process_time:.3f}s",
        "client_ip": request.client.host,
    })

    return response
```

---

## 🟡 性能優化問題（建議解決）

### 16. 📊 缺少性能監控和 APM

**建議**: 集成 Application Performance Monitoring

**選項 A: Sentry（推薦，開源友好）**

```python
# requirements.txt
sentry-sdk[fastapi]==1.40.0

# app.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENVIRONMENT", "development"),
    traces_sample_rate=1.0 if os.getenv("ENVIRONMENT") == "production" else 0.1,
    integrations=[FastApiIntegration()],
)
```

**選項 B: Prometheus + Grafana**

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
```

---

### 17. 📊 缺少錯誤追蹤和告警

**建議**: 配置錯誤告警通知

```python
# services/error_notifier.py
import requests
import os

def send_error_notification(error_message: str, context: dict):
    """發送錯誤通知到 Slack/Discord/Email"""

    # Slack Webhook
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if webhook_url:
        requests.post(webhook_url, json={
            "text": f"🚨 Production Error: {error_message}",
            "attachments": [{
                "color": "danger",
                "fields": [
                    {"title": k, "value": str(v), "short": True}
                    for k, v in context.items()
                ]
            }]
        })

# 在異常處理中使用
try:
    # ... 業務邏輯
except Exception as e:
    logger.error(f"Critical error: {e}", exc_info=True)
    send_error_notification(str(e), {
        "service": "rag-orchestrator",
        "endpoint": "/api/v1/chat",
        "user_id": user_id,
    })
    raise
```

---

### 18. 📊 數據庫連接池配置需優化

**問題位置**: `rag-orchestrator/app.py` (Lines 46-54)

```python
# ❌ 當前配置
db_pool = await asyncpg.create_pool(
    min_size=2,  # 過小
    max_size=10  # 可能不足
)
```

**建議配置**（根據負載調整）:

```python
# ✅ 生產環境配置
db_pool = await asyncpg.create_pool(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    min_size=int(os.getenv("DB_POOL_MIN_SIZE", "5")),
    max_size=int(os.getenv("DB_POOL_MAX_SIZE", "20")),
    max_queries=50000,  # 每個連接最多執行 50000 次查詢後回收
    max_inactive_connection_lifetime=300,  # 閒置 5 分鐘後回收
    timeout=30,  # 獲取連接超時時間
    command_timeout=60,  # SQL 執行超時時間
)
```

---

### 19. 📊 Redis 緩存策略需優化

**建議**: 添加緩存預熱和降級策略

```python
# services/cache_service.py
class CacheService:
    def __init__(self):
        self.redis_client = redis.Redis(...)
        self.fallback_cache = {}  # 內存降級緩存

    async def get_with_fallback(self, key: str):
        """帶降級的緩存獲取"""
        try:
            # 嘗試從 Redis 獲取
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
        except redis.ConnectionError:
            logger.warning("Redis unavailable, using fallback cache")
            # 降級到內存緩存
            return self.fallback_cache.get(key)

        return None

    async def set_with_fallback(self, key: str, value: any, ttl: int):
        """帶降級的緩存設置"""
        try:
            self.redis_client.setex(key, ttl, json.dumps(value))
        except redis.ConnectionError:
            logger.warning("Redis unavailable, using fallback cache")
            self.fallback_cache[key] = value

    async def warmup_cache(self):
        """緩存預熱"""
        logger.info("Starting cache warmup")
        # 預載常用數據
        common_queries = await db_pool.fetch(
            "SELECT DISTINCT question FROM chat_history ORDER BY created_at DESC LIMIT 100"
        )
        for query in common_queries:
            # 預先生成 embedding 並緩存
            await self.get_or_generate_embedding(query["question"])
        logger.info("Cache warmup completed")
```

---

## 🔵 維護改進建議（可選但推薦）

### 20. 📝 環境變數文檔化

**創建**: `docs/ENVIRONMENT_VARIABLES.md`

```markdown
# 環境變數說明文檔

## 必要變數

| 變數名 | 說明 | 範例 | 預設值 |
|--------|------|------|--------|
| OPENAI_API_KEY | OpenAI API 金鑰 | sk-proj-xxx | ❌ 必須設置 |
| DB_HOST | 資料庫主機 | postgres | localhost |
| DB_PASSWORD | 資料庫密碼 | ❌ 使用強密碼 | ❌ 必須設置 |

## 可選變數

| 變數名 | 說明 | 範例 | 預設值 |
|--------|------|------|--------|
| CACHE_ENABLED | 是否啟用緩存 | true | true |
| REDIS_PASSWORD | Redis 密碼 | ❌ 建議設置 | 空（不安全） |
...
```

---

### 21. 🔄 建立自動化備份策略

**創建**: `scripts/backup_database.sh`

```bash
#!/bin/bash
# 自動備份 PostgreSQL 資料庫

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/aichatbot_backup_$TIMESTAMP.sql.gz"

# 備份資料庫
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin | gzip > "$BACKUP_FILE"

# 上傳到 S3
aws s3 cp "$BACKUP_FILE" "s3://your-backup-bucket/database-backups/"

# 保留最近 30 天的備份
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
```

**配置 Crontab**:
```bash
# 每天凌晨 2 點備份
0 2 * * * /path/to/scripts/backup_database.sh >> /var/log/backup.log 2>&1
```

---

## 📋 部署步驟總結

### 階段 1: 安全性修復（必須，1-3 天）

1. ✅ 撤銷並重新生成所有 API Keys
2. ✅ 配置 CORS 白名單
3. ✅ 實施 API Key 認證和 Rate Limiting
4. ✅ 更新所有弱密碼（DB、Redis）
5. ✅ 移除或限制管理介面訪問（PgAdmin）
6. ✅ 限制資料庫和 Redis 端口訪問

### 階段 2: 配置調整（重要，2-3 天）

1. ✅ 替換所有硬編碼的 localhost URL
2. ✅ 完善 docker-compose.prod.yml
3. ✅ 配置環境變數驗證
4. ✅ 優化前端生產構建
5. ✅ 添加 Nginx 安全 Headers
6. ✅ 實施健康檢查端點
7. ✅ 配置結構化日誌（替換 452 個 print）

### 階段 3: 性能優化（建議，1-2 天）

1. ✅ 集成 APM 監控（Sentry 或 Prometheus）
2. ✅ 配置錯誤告警
3. ✅ 優化資料庫連接池
4. ✅ 實施緩存降級策略

### 階段 4: 維護準備（可選，1 天）

1. ✅ 編寫環境變數文檔
2. ✅ 建立自動化備份策略
3. ✅ 編寫部署手冊

---

## 🚀 快速啟動檢查清單

**部署前必須完成** ✅:

- [ ] 所有 API Keys 已撤銷並重新生成
- [ ] .env 文件已加入 .gitignore（確認未提交到 Git）
- [ ] CORS 已配置為特定域名（非 `*`）
- [ ] API 認證已實施（至少 API Key）
- [ ] 所有弱密碼已更新（DB、Redis、PgAdmin）
- [ ] PgAdmin 已移除或訪問受限
- [ ] PostgreSQL 和 Redis 端口已限制或內部化
- [ ] 前端 URL 已改為環境變數
- [ ] docker-compose.prod.yml 已配置並測試
- [ ] 健康檢查端點已實施
- [ ] 日誌系統已配置（至少基本的 Python logging）
- [ ] 環境變數驗證已實施
- [ ] 備份策略已建立

**可選但強烈建議** 🔶:

- [ ] Rate Limiting 已配置
- [ ] APM 監控已集成（Sentry/Prometheus）
- [ ] 錯誤告警已配置（Slack/Email）
- [ ] Nginx 安全 Headers 已添加
- [ ] 緩存降級策略已實施
- [ ] 環境變數文檔已編寫

---

## 📞 緊急聯絡和回滾計劃

### 回滾步驟

如果部署後出現問題：

```bash
# 1. 立即切回開發環境配置
docker-compose down
docker-compose up -d

# 2. 恢復資料庫（如有需要）
gunzip < /backups/aichatbot_backup_YYYYMMDD_HHMMSS.sql.gz | \
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin

# 3. 檢查日誌
docker-compose logs --tail=100 rag-orchestrator
docker-compose logs --tail=100 knowledge-admin-api
```

---

**文檔版本**: v1.0
**最後更新**: 2025-10-29
**審查週期**: 每月一次

