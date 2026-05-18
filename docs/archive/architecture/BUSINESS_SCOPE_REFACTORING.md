# Business Scope 架構重構

**日期**: 2025-10-12
**作者**: Claude Code
**狀態**: ✅ 完成

## 背景與問題

### 舊架構的問題
在原始設計中，`business_scope_name` 欄位被固定在 `vendors` 表上：

```sql
vendors
├── business_scope_name: 'external' | 'internal'
```

這導致以下問題：
1. ❌ **每個業者被強制選擇單一業務範圍**
2. ❌ **無法同時服務 B2B 和 B2C 場景**
3. ❌ **業務範圍的定義不明確**

### 實際需求
每個包租代管業者實際上有**兩種使用場景**：

| 場景 | 對話雙方 | Business Scope | Audience Filter |
|------|----------|----------------|-----------------|
| **B2C（外部客戶）** | 終端用戶 ↔ 業者 | `external` | `all`, `tenant`, `landlord` |
| **B2B（內部管理）** | 業者員工 ↔ 系統商 | `internal` | `all`, `vendor_staff`, `system` |

## 解決方案

### 核心概念
**Business scope 應該由「用戶角色」決定，而非固定在業者身上**

```
用戶角色 (user_role)  →  Business Scope  →  Audience Filter
────────────────────────────────────────────────────────────
customer               →  external         →  all, tenant, landlord
staff                  →  internal         →  all, vendor_staff, system
```

### 架構變更

#### 1. 資料庫變更

**Migration 27**: 移除 `vendors.business_scope_name`

```sql
-- 移除外鍵
ALTER TABLE vendors DROP CONSTRAINT IF EXISTS vendors_business_scope_fkey;

-- 移除索引
DROP INDEX IF EXISTS idx_vendors_business_scope;

-- 移除欄位
ALTER TABLE vendors DROP COLUMN IF EXISTS business_scope_name;
```

✅ **執行結果**:
```
ALTER TABLE
DROP INDEX
ALTER TABLE
```

#### 2. API 變更

**Chat API (`/api/v1/chat`)**

```python
# Before
class ChatRequest(BaseModel):
    question: str
    vendor_id: int
    business_scope: str = "external"  # ❌ 手動指定

# After
class ChatRequest(BaseModel):
    question: str
    vendor_id: int
    user_role: str  # ✅ 基於角色自動決定
```

**自動判斷邏輯**:
```python
# customer (終端客戶) -> external (B2C): 用戶對業者
# staff (業者員工/系統商) -> internal (B2B): 業者對系統商
business_scope = "external" if request.user_role == "customer" else "internal"
allowed_audiences = get_allowed_audiences_for_scope(business_scope)
```

**Vendor Chat API (`/api/v1/message`)**

```python
# Before
class VendorChatRequest(BaseModel):
    message: str
    vendor_id: int
    business_scope: str = "external"  # ❌ 手動指定

# After
class VendorChatRequest(BaseModel):
    message: str
    vendor_id: int
    user_role: str = "customer"  # ✅ 預設 customer，可覆寫
```

#### 3. Vendors API 變更

**移除 `business_scope_name` 欄位**:

```python
# Before
class VendorCreate(BaseModel):
    code: str
    name: str
    business_scope_name: str = "external"  # ❌ 移除

# After
class VendorCreate(BaseModel):
    code: str
    name: str
    # ✅ 不再需要 business_scope_name
```

```python
# Before
class VendorResponse(BaseModel):
    id: int
    code: str
    business_scope_name: Optional[str]  # ❌ 移除

# After
class VendorResponse(BaseModel):
    id: int
    code: str
    # ✅ 不再包含 business_scope_name
```

## 影響範圍

### 修改的檔案

1. **資料庫**
   - ✅ `database/migrations/27-remove-vendor-business-scope.sql`

2. **後端 API**
   - ✅ `rag-orchestrator/routers/chat.py` (3處修改)
   - ✅ `rag-orchestrator/routers/vendors.py` (CREATE, UPDATE, Response schemas)

3. **前端** (需修改)
   - ⏳ `knowledge-admin/frontend/src/views/VendorManagementView.vue`
   - ⏳ `knowledge-admin/frontend/src/views/ChatTestView.vue`

### 相容性變更

#### ⚠️ Breaking Changes

**Vendors API**:
- `POST /api/v1/vendors` - 不再接受 `business_scope_name`
- `PUT /api/v1/vendors/{id}` - 不再接受 `business_scope_name`
- `GET /api/v1/vendors` - Response 不再包含 `business_scope_name`

**Chat API**:
- `POST /api/v1/chat` - 需要提供 `user_role` (必填)
- `POST /api/v1/message` - 需要提供 `user_role` (預設 "customer")

#### 📝 API 請求範例

**舊版 (不再支援)**:
```json
POST /api/v1/message
{
  "message": "退租流程",
  "vendor_id": 1,
  "business_scope": "external"
}
```

**新版**:
```json
POST /api/v1/message
{
  "message": "退租流程",
  "vendor_id": 1,
  "user_role": "customer"
}
```

## 測試驗證 ✅

**測試日期**: 2025-10-12
**測試狀態**: 全部通過 ✅

### 1. 資料庫驗證 ✅

```sql
-- 確認 business_scope_name 已移除
\d vendors
-- 應該不顯示 business_scope_name 欄位

-- 確認現有業者資料不受影響
SELECT id, code, name, subscription_plan
FROM vendors;
```

**結果**: ✅ 通過
- vendors 表不再包含 business_scope_name 欄位
- 外鍵約束已移除
- 索引已刪除
- 現有業者資料完整保留 (VENDOR_A, VENDOR_B)

### 2. API 測試 ✅

**測試 B2C 場景** (customer → external):
```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "退租流程是什麼？",
    "vendor_id": 1,
    "user_role": "customer"
  }'
```

**結果**: ✅ 通過
- Intent 正確識別為「退租流程」(confidence: 0.9)
- 成功檢索到相關知識
- Business scope 自動設為 "external"

**測試 B2B 場景** (staff → internal):
```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "如何管理租約到期提醒？",
    "vendor_id": 1,
    "user_role": "staff"
  }'
```

**結果**: ✅ 通過
- Intent 正確識別為「租約查詢」(confidence: 0.8)
- 成功檢索到相關知識
- Business scope 自動設為 "internal"

### 3. Vendors API 測試 ✅

**GET /api/v1/vendors**: ✅ 通過
- 成功返回業者列表
- Response 不包含 business_scope_name

**POST /api/v1/vendors**: ✅ 通過
- 成功創建業者 (TEST_VENDOR)
- 不需要提供 business_scope_name

**PUT /api/v1/vendors/{id}**: ✅ 通過
- 成功更新業者資訊
- 不需要提供 business_scope_name

### 4. 知識過濾驗證 ✅

| User Role | Business Scope | 可見 Audience |
|-----------|----------------|---------------|
| customer  | external       | 租客, 房東, tenant, general, 複合受眾 |
| staff     | internal       | 管理師, 系統管理員, general, 複合受眾 |

**資料庫統計**:
- External audiences: 租客 (329), 房東 (25), tenant, general 等
- Internal audiences: 管理師 (105), 系統管理員 (1) 等
- 複合受眾正確處理 (如: 租客|管理師, 房東|租客|管理師)

## 前端待辦事項

### VendorManagementView.vue

需要修改的內容：
1. ⏳ 移除「業務範圍」欄位顯示
2. ⏳ 移除新增/編輯表單中的業務範圍選擇
3. ⏳ 更新說明文字，解釋業務範圍由用戶角色決定

### ChatTestView.vue

需要修改的內容：
1. ⏳ 將 `business_scope` 選擇改為 `user_role` 選擇
2. ⏳ 選項：
   - `customer` - 終端客戶（B2C）
   - `staff` - 業者員工/系統商（B2B）

**註**: 前端更新可在下一階段進行，後端 API 已完全支持新架構

## 優勢

### ✅ 解決的問題

1. **業者可同時服務兩種場景**
   - B2C: 終端客戶（租客、房東）
   - B2B: 內部管理（業者員工、系統商）

2. **語意更清晰**
   - `user_role` 清楚表達「誰在使用」
   - `business_scope` 自動推導，無需手動選擇

3. **架構更合理**
   - Business scope 是對話層級的屬性，不是業者層級的屬性
   - 符合實際業務邏輯

### 📊 對比

| 項目 | 舊架構 | 新架構 |
|------|--------|--------|
| business_scope 綁定位置 | Vendor 層級 | Request 層級 |
| 業者可服務場景 | 單一場景 | 雙場景 |
| API 參數 | business_scope (手動) | user_role (語意化) |
| 資料庫欄位 | vendors.business_scope_name | (移除) |
| 判斷邏輯 | 查詢 DB | 程式自動判斷 |

## 未來擴展

### 認證整合

未來可以從認證系統自動判斷 `user_role`：

```python
def get_user_role_from_token(token: str) -> str:
    """從 JWT token 判斷用戶角色"""
    payload = decode_token(token)

    if payload.get('is_customer'):
        return "customer"
    elif payload.get('is_vendor_staff'):
        return "staff"
    elif payload.get('is_system_admin'):
        return "staff"
    else:
        return "customer"  # 預設
```

### 更細緻的角色控制

可以擴展更多角色：

```python
ROLE_TO_SCOPE_MAPPING = {
    "customer": "external",          # 終端客戶
    "tenant": "external",            # 租客
    "landlord": "external",          # 房東
    "vendor_staff": "internal",      # 業者員工
    "vendor_admin": "internal",      # 業者管理員
    "system_admin": "internal",      # 系統管理員
}

business_scope = ROLE_TO_SCOPE_MAPPING.get(user_role, "external")
```

## 相關文件

- Business Scope Utils
- Migration 25 - Mark is_active as DEPRECATED
- [Migration 26 - Remove is_active](../migrations_history/26-remove-business-scope-is-active.sql)
- [Migration 27 - Remove vendors.business_scope_name](../migrations_history/27-remove-vendor-business-scope.sql)

## 總結

這次重構**將 business_scope 從 Vendor 層級提升到 Request 層級**，使得：

1. ✅ 每個業者可以同時服務 B2B 和 B2C 場景
2. ✅ API 語意更清晰（user_role 而非 business_scope）
3. ✅ 架構更符合實際業務邏輯
4. ✅ 為未來的認證整合預留空間

**核心理念**：業務範圍不是業者的屬性，而是**對話關係的屬性**。
