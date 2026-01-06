# API 保護指南

## 如何保護現有的 API 端點

### 方法 1: 使用 Depends 裝飾器（推薦）

在 `app.py` 中導入認證依賴：

```python
from routes_auth import get_current_user
from fastapi import Depends
```

然後在需要保護的 API 端點中添加 `user = Depends(get_current_user)`：

```python
# 範例：保護知識庫 API
@app.get("/api/knowledge")
async def get_all_knowledge(user: dict = Depends(get_current_user)):
    """
    獲取所有知識（需要認證）

    只有已登入的管理員才能訪問此 API
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM ai_knowledge ORDER BY id DESC")
            knowledge = cur.fetchall()
            return {"knowledge": knowledge}
    finally:
        conn.close()
```

### 方法 2: 全局中間件（可選）

如果要保護所有 API（除了登入頁面），可以添加全局中間件：

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # 公開路由（不需要認證）
    public_paths = [
        "/api/auth/login",
        "/docs",
        "/openapi.json",
        "/health"
    ]

    # 展示頁路由（不需要認證）
    # 例如: /VENDOR_A/chat
    if request.url.path.endswith("/chat"):
        return await call_next(request)

    # 如果是公開路由，直接通過
    if any(request.url.path.startswith(path) for path in public_paths):
        return await call_next(request)

    # 檢查 Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"detail": "未授權訪問"}
        )

    # 驗證 token（使用 auth_utils）
    token = auth_header.replace("Bearer ", "")
    payload = decode_access_token(token)
    if payload is None:
        return JSONResponse(
            status_code=401,
            content={"detail": "Token 無效"}
        )

    # Token 有效，繼續處理請求
    return await call_next(request)
```

## 推薦的保護策略

### 需要保護的 API（管理後台）

- ✅ `/api/knowledge` - 知識庫管理
- ✅ `/api/intents` - 意圖管理
- ✅ `/api/vendors` - 業者管理
- ✅ `/api/platform-sop` - SOP 管理
- ✅ `/api/test-scenarios` - 測試場景
- ✅ `/api/cache` - 緩存管理
- ✅ 所有 CRUD 操作

### 公開 API（不需要保護）

- ❌ `/api/auth/login` - 登入端點
- ❌ `/api/auth/health` - 健康檢查
- ❌ `/:vendorCode/chat` - 展示頁（客戶訪問）
- ❌ `/docs` - API 文檔（可選）
- ❌ `/health` - 服務健康檢查

## 前端如何發送認證請求

前端需要在 HTTP 請求中附加 Authorization header：

```javascript
const token = localStorage.getItem('auth_token')

fetch('http://localhost:8000/api/knowledge', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
```

## 錯誤處理

當認證失敗時，API 會返回：

```json
{
  "detail": "Invalid authentication credentials"
}
```

前端應該：
1. 清除本地 token
2. 重定向到登入頁
3. 提示用戶重新登入
