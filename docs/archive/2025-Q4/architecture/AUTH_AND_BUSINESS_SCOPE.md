# 認證與業務範圍整合方案

## 概述

`user_role` 應該從**認證 token**自動判斷，而非由前端手動傳遞。

## 架構流程

```
1. 用戶登入
   ↓
2. 取得 JWT Token (包含用戶身份資訊)
   ↓
3. 發送 API 請求 (攜帶 Token)
   ↓
4. Backend 解析 Token → 判斷 user_role
   ↓
5. 根據 user_role → 決定 business_scope
   ↓
6. 套用 audience 過濾
```

## JWT Token 設計

### Token Payload 範例

```json
{
  "user_id": "user123",
  "vendor_id": 1,
  "user_type": "customer",
  "customer_type": "tenant",
  "exp": 1234567890,
  "iat": 1234567890
}
```

或

```json
{
  "user_id": "staff456",
  "vendor_id": 1,
  "user_type": "staff",
  "staff_role": "vendor_admin",
  "exp": 1234567890,
  "iat": 1234567890
}
```

### User Type 定義

| user_type | 說明 | Business Scope | 範例 |
|-----------|------|----------------|------|
| `customer` | 終端客戶 | external | 租客、房東 |
| `tenant` | 租客 | external | 使用租屋服務的客戶 |
| `landlord` | 房東 | external | 提供房屋的業主 |
| `staff` | 員工 | internal | 業者員工、系統管理員 |
| `vendor_staff` | 業者員工 | internal | 包租代管公司員工 |
| `vendor_admin` | 業者管理員 | internal | 業者管理人員 |
| `system_admin` | 系統管理員 | internal | 系統商管理員 |

## 實作方案

### 方案 A：修改 API 使用 Auth Dependency

**建議實作** (`rag-orchestrator/dependencies/auth.py`):

```python
from fastapi import Header, HTTPException, Depends
from typing import Optional
import jwt

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"

class CurrentUser:
    """當前用戶資訊"""
    def __init__(
        self,
        user_id: str,
        vendor_id: int,
        user_type: str,
        user_role: str,
        token: str
    ):
        self.user_id = user_id
        self.vendor_id = vendor_id
        self.user_type = user_type
        self.user_role = user_role  # customer 或 staff
        self.token = token

    @property
    def business_scope(self) -> str:
        """根據用戶角色自動決定業務範圍"""
        return "external" if self.user_role == "customer" else "internal"


async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> CurrentUser:
    """
    從 Authorization header 解析當前用戶

    Header 格式: "Bearer <token>"
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header"
        )

    try:
        # 解析 Bearer token
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication scheme"
            )

        # 解析 JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id = payload.get("user_id")
        vendor_id = payload.get("vendor_id")
        user_type = payload.get("user_type")

        if not all([user_id, vendor_id, user_type]):
            raise HTTPException(
                status_code=401,
                detail="Invalid token payload"
            )

        # 判斷 user_role
        user_role = determine_user_role(user_type)

        return CurrentUser(
            user_id=user_id,
            vendor_id=vendor_id,
            user_type=user_type,
            user_role=user_role,
            token=token
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.JWTError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )


def determine_user_role(user_type: str) -> str:
    """
    根據 user_type 決定 user_role

    Args:
        user_type: Token 中的用戶類型

    Returns:
        "customer" 或 "staff"
    """
    CUSTOMER_TYPES = {"customer", "tenant", "landlord"}
    STAFF_TYPES = {"staff", "vendor_staff", "vendor_admin", "system_admin"}

    if user_type in CUSTOMER_TYPES:
        return "customer"
    elif user_type in STAFF_TYPES:
        return "staff"
    else:
        # 預設為 customer (安全起見)
        return "customer"


# 可選：不需要認證的 dependency（用於測試）
async def get_current_user_optional(
    authorization: Optional[str] = Header(None)
) -> Optional[CurrentUser]:
    """
    可選的認證 dependency
    如果沒有 token 則返回 None
    """
    if not authorization:
        return None

    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None
```

### 更新 Chat API

**修改後的 `/message` endpoint**:

```python
from dependencies.auth import get_current_user, CurrentUser

@router.post("/message", response_model=VendorChatResponse)
async def vendor_chat_message(
    request: VendorChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    req: Request
):
    """
    多業者通用聊天端點

    需要認證：
    - Header: Authorization: Bearer <token>
    - Token 中包含 user_id, vendor_id, user_type

    Business scope 自動判斷：
    - customer type → external (B2C)
    - staff type → internal (B2B)
    """
    try:
        # ✅ 驗證 vendor_id 與 token 中的一致
        if request.vendor_id != current_user.vendor_id:
            raise HTTPException(
                status_code=403,
                detail="Vendor ID mismatch"
            )

        # ✅ 使用認證系統判斷的 business_scope
        business_scope = current_user.business_scope
        allowed_audiences = get_allowed_audiences_for_scope(business_scope)

        # ... 原有邏輯 ...
```

### 簡化的 Request Model

```python
class VendorChatRequest(BaseModel):
    """多業者聊天請求"""
    message: str = Field(..., description="使用者訊息", min_length=1, max_length=2000)
    vendor_id: int = Field(..., description="業者 ID", ge=1)
    # ❌ 移除 user_role，改從認證 token 取得
    session_id: Optional[str] = Field(None, description="會話 ID")
    top_k: int = Field(3, description="返回知識數量", ge=1, le=10)
    include_sources: bool = Field(True, description="是否包含知識來源")
    disable_answer_synthesis: bool = Field(False, description="禁用答案合成")
```

## 前端整合

### 登入流程

```javascript
// 1. 用戶登入
const loginResponse = await axios.post('/api/v1/auth/login', {
  username: 'user@example.com',
  password: 'password',
  vendor_code: 'VENDOR_A'
});

// 2. 儲存 token
const { access_token, user_info } = loginResponse.data;
localStorage.setItem('access_token', access_token);
localStorage.setItem('user_info', JSON.stringify(user_info));
```

### 發送訊息

```javascript
// 3. 發送聊天請求（自動攜帶 token）
const response = await axios.post(
  '/api/v1/message',
  {
    message: '退租流程是什麼？',
    vendor_id: 1
    // ✅ user_role 從 token 自動判斷，不需要傳遞
  },
  {
    headers: {
      Authorization: `Bearer ${access_token}`
    }
  }
);
```

### Axios Interceptor (全局設定)

```javascript
// 設定全局 Authorization header
axios.interceptors.request.use(
  config => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => Promise.reject(error)
);

// 處理 401 錯誤（token 過期）
axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Token 過期，導向登入頁
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_info');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

## 測試模式

### Development/Testing 模式

在開發或測試環境，可以保留 `user_role` 參數作為 fallback：

```python
@router.post("/message")
async def vendor_chat_message(
    request: VendorChatRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    req: Request
):
    """支援測試模式的聊天端點"""

    # 生產環境：強制認證
    if os.getenv("ENVIRONMENT") == "production" and not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # 開發/測試環境：允許 fallback
    if current_user:
        # 使用認證系統的判斷
        business_scope = current_user.business_scope
        user_id = current_user.user_id
    else:
        # Fallback: 使用請求中的 user_role（僅開發/測試）
        business_scope = "external" if request.user_role == "customer" else "internal"
        user_id = request.user_id or "anonymous"

    # ... 原有邏輯 ...
```

## 安全考量

### 1. Token 驗證

```python
# ✅ DO: 驗證 token 簽名
jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

# ❌ DON'T: 信任前端傳遞的 user_role
# user_role = request.user_role  # 不安全！
```

### 2. Vendor ID 驗證

```python
# ✅ DO: 驗證請求的 vendor_id 與 token 中的一致
if request.vendor_id != current_user.vendor_id:
    raise HTTPException(status_code=403, detail="Vendor ID mismatch")
```

### 3. 權限檢查

```python
# ✅ DO: 根據 user_role 限制可訪問的 API
if endpoint.requires_staff and current_user.user_role != "staff":
    raise HTTPException(status_code=403, detail="Staff only")
```

## 實作優先順序

### Phase 1: 保留相容性（當前）
- ✅ API 接受 `user_role` 參數
- ✅ 允許手動指定（用於開發測試）
- ⚠️ 不強制認證（backwards compatible）

### Phase 2: 加入認證支援（建議）
- 🔄 實作 `get_current_user` dependency
- 🔄 修改 API 支援 token 認證
- 🔄 優先使用 token，fallback 到 user_role

### Phase 3: 強制認證（生產環境）
- 🔄 生產環境強制要求 token
- 🔄 移除 user_role 參數
- 🔄 完全基於 token 判斷

## 範例：完整流程

### 1. B2C 場景（租客）

```bash
# 登入
curl -X POST http://api.example.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "tenant@example.com",
    "password": "password",
    "vendor_code": "VENDOR_A"
  }'

# Response
{
  "access_token": "eyJhbGc...",
  "user_info": {
    "user_id": "tenant123",
    "vendor_id": 1,
    "user_type": "tenant",
    "user_role": "customer"
  }
}

# 發送訊息（自動識別為 B2C）
curl -X POST http://api.example.com/api/v1/message \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "message": "退租流程是什麼？",
    "vendor_id": 1
  }'

# Backend 自動判斷:
# user_type: tenant → user_role: customer → business_scope: external
```

### 2. B2B 場景（業者員工）

```bash
# 登入
curl -X POST http://api.example.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "staff@vendor-a.com",
    "password": "password",
    "vendor_code": "VENDOR_A"
  }'

# Response
{
  "access_token": "eyJhbGc...",
  "user_info": {
    "user_id": "staff456",
    "vendor_id": 1,
    "user_type": "vendor_staff",
    "user_role": "staff"
  }
}

# 發送訊息（自動識別為 B2B）
curl -X POST http://api.example.com/api/v1/message \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "message": "如何管理系統設定？",
    "vendor_id": 1
  }'

# Backend 自動判斷:
# user_type: vendor_staff → user_role: staff → business_scope: internal
```

## 總結

**核心概念**：`user_role` 應該從**認證 token**自動判斷，確保安全性。

| 項目 | 當前實作 | 建議實作 |
|------|----------|----------|
| user_role 來源 | 請求參數 | JWT Token |
| 安全性 | ⚠️ 可被前端偽造 | ✅ 後端驗證 |
| 實作複雜度 | 簡單 | 中等 |
| 適用場景 | 開發/測試 | 生產環境 |

**下一步**：實作 `dependencies/auth.py` 並整合到 chat API。
