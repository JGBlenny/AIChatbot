# Lookup API URL 修正記錄

## 📅 修正日期
2026-03-12

## 🎯 問題描述

當 Lookup 路由器的 prefix 從 `/api` 修正為 `/api/v1` 後，資料庫中 `api_endpoints` 表的 URL 配置沒有同步更新，導致所有表單調用 Lookup API 時失敗。

## ❌ 問題根源

### 路由器修正
**檔案：** `rag-orchestrator/routers/lookup.py:26`

```python
# 修正前
router = APIRouter(prefix="/api", tags=["lookup"])

# 修正後
router = APIRouter(prefix="/api/v1", tags=["lookup"])
```

### 資料庫配置未同步

資料庫 `api_endpoints` 表中的 URL 仍然使用舊路徑：

```
❌ 舊路徑: http://localhost:8100/api/lookup
✅ 新路徑: http://localhost:8100/api/v1/lookup
```

## ✅ 修正內容

### 批量更新所有 Lookup API 端點

```sql
UPDATE api_endpoints
SET api_url = REPLACE(api_url, 'http://localhost:8100/api/lookup', 'http://localhost:8100/api/v1/lookup')
WHERE api_url LIKE 'http://localhost:8100/api/lookup%';
```

**影響端點數：** 8 個

### 修正後的端點列表

| endpoint_id | 修正前 URL | 修正後 URL | 狀態 |
|-------------|-----------|-----------|------|
| lookup_generic | `http://localhost:8100/api/lookup` | `http://localhost:8100/api/v1/lookup` | ✅ |
| lookup_billing_interval | `http://localhost:8100/api/lookup` | `http://localhost:8100/api/v1/lookup` | ✅ |
| lookup_community_facilities | `http://localhost:8100/api/lookup/all` | `http://localhost:8100/api/v1/lookup/all` | ✅ |
| lookup_customer_service | `http://localhost:8100/api/lookup/all` | `http://localhost:8100/api/v1/lookup/all` | ✅ |
| lookup_maintenance_flow | `http://localhost:8100/api/lookup/all` | `http://localhost:8100/api/v1/lookup/all` | ✅ |
| lookup_parcel_service | `http://localhost:8100/api/lookup/all` | `http://localhost:8100/api/v1/lookup/all` | ✅ |
| lookup_payment_methods | `http://localhost:8100/api/lookup/all` | `http://localhost:8100/api/v1/lookup/all` | ✅ |
| lookup_service_hours | `http://localhost:8100/api/v1/lookup/all` | `http://localhost:8100/api/v1/lookup/all` | ✅ |
| lookup_vendor_contacts | `http://localhost:8100/api/v1/lookup/all` | `http://localhost:8100/api/v1/lookup/all` | ✅ |

### 未修正的端點

| endpoint_id | URL | 原因 | 建議 |
|-------------|-----|------|------|
| lookup | `http://127.0.0.1:8000/api/lookup` | 指向 knowledge-admin-api 的舊實現 | 考慮停用或刪除 |

## 🧪 驗證測試

### 1. 直接 API 測試

```bash
# 測試 lookup_generic
curl -s -G "http://localhost:8100/api/v1/lookup" \
  --data-urlencode "category=billing_interval" \
  --data-urlencode "key=台北市大安區信義路三段125號5樓之3" \
  --data-urlencode "vendor_id=2" \
  --data-urlencode "fuzzy=true"
```

**預期結果：**
```json
{
  "success": true,
  "match_type": "exact",
  "category": "billing_interval",
  "key": "台北市大安區信義路三段125號5樓之3",
  "value": "雙月",
  "note": "您的電費帳單將於每【雙月】寄送。"
}
```

### 2. 表單流程測試

1. 在聊天介面輸入：「電費資訊查詢」
2. 填寫地址：「台北市大安區信義路三段125號5樓之3」
3. 應該返回：「✅ 查詢成功 ... 雙月」

**修正前：** ❌ 查詢失敗
**修正後：** ✅ 查詢成功

## 📊 影響範圍

### 受影響的功能

✅ **所有表單驅動的 Lookup 查詢**
- 電費寄送區間查詢
- 社區設施查詢
- 客服聯絡方式查詢
- 包裹代收服務查詢
- 繳費方式查詢
- 服務時間查詢
- 配合廠商查詢
- 維修流程查詢

✅ **知識庫觸發的 Lookup API 調用**

### 未受影響的功能

- 自定義代碼實現的 API（如 billing_inquiry, maintenance_request 等）
- 直接 Lookup API 調用（如 `/api/v1/lookup` 端點本身）

## 🔄 系統架構說明

### API 端點類型

系統中有兩種 API 端點實現方式：

#### 1. **Custom 實現** (implementation_type = 'custom')
- 由代碼直接實現的 API 處理器
- 在 `services/api_call_handler.py` 的 `api_registry` 中註冊
- 例如：`billing_inquiry`, `verify_tenant_identity` 等
- **不需要** `api_url` 配置

#### 2. **Dynamic 實現** (implementation_type = 'dynamic')
- 透過 HTTP 調用外部或內部 API
- 需要在 `api_endpoints` 表中配置 `api_url`
- 例如：所有 `lookup_*` 端點
- **需要確保** `api_url` 正確

### Lookup 系統路由

```
前端/表單
  ↓
form_manager.py (表單管理器)
  ↓
api_call_handler.py (API 調用處理器)
  ↓
universal_api_handler.py (通用 API 處理器)
  ↓
HTTP 請求 → http://localhost:8100/api/v1/lookup
  ↓
rag-orchestrator (Lookup 路由器)
  ↓
資料庫查詢 → lookup_tables 表
```

## 🚨 未來預防措施

### 1. 版本化 API 路徑

**建議：** 所有內部 API 路由都應該使用版本化路徑

```python
# ✅ 正確
router = APIRouter(prefix="/api/v1", tags=["xxx"])

# ❌ 錯誤
router = APIRouter(prefix="/api", tags=["xxx"])
```

### 2. 資料庫遷移腳本

當修改 API 路由 prefix 時，應該同時提供資料庫遷移腳本：

```sql
-- database/migrations/update_api_endpoints_urls.sql

-- 更新所有 Lookup API 端點
UPDATE api_endpoints
SET api_url = REPLACE(api_url, '/api/lookup', '/api/v1/lookup')
WHERE api_url LIKE '%/api/lookup%';

-- 驗證結果
SELECT endpoint_id, api_url
FROM api_endpoints
WHERE api_url LIKE '%lookup%';
```

### 3. 自動化測試

**建議：** 建立端到端測試，驗證：
- API 路由是否正確
- 資料庫配置是否與路由一致
- 表單流程是否能正常調用 API

### 4. 文檔更新檢查清單

修改 API 路由時，檢查以下項目：

- [ ] 路由器代碼（routers/*.py）
- [ ] 資料庫配置（api_endpoints 表）
- [ ] API 文檔（OpenAPI/Swagger）
- [ ] 前端 API 調用（如有直接調用）
- [ ] 環境變數配置（如有）
- [ ] nginx 代理配置（如有）

## 📝 相關文檔

- [Lookup 重構完整總結](./LOOKUP_REFACTORING_COMPLETE_SUMMARY.md)
- [前端顯示修復](./FRONTEND_DISPLAY_FIX.md)
- [測試指引](./TESTING_GUIDE.md)

---

**文檔版本：** 1.0
**最後更新：** 2026-03-12
**負責人：** AI Assistant
**狀態：** ✅ 已修正並驗證
