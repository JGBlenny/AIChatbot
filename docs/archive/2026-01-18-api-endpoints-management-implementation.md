# API Endpoints 動態管理系統實作總結

**日期**: 2026-01-18
**狀態**: ✅ 已完成
**目的**: 替代硬編碼的 API endpoint 選項，實現動態管理

**🔄 重要更新 (2026-01-21)**:
- ❌ `handler_function` 欄位已被移除（已棄用）
- ✅ 改用 `custom_handler_name`（配合 `implementation_type` 使用）
- 📝 詳見：`/tmp/HANDLER_FUNCTION_CLEANUP_REPORT.md`

---

## 📋 問題背景

### 原有問題
在之前的實作中，API Endpoint 選項是**硬編碼在前端代碼**中的：

**KnowledgeView.vue** (寫死 5 個選項):
```html
<option value="billing_inquiry">📋 帳單查詢</option>
<option value="verify_tenant_identity">🔐 租客身份驗證</option>
<option value="resend_invoice">📧 重新發送帳單</option>
<option value="maintenance_request">🔧 報修申請</option>
<option value="rent_history">💰 查詢租金紀錄</option>
```

**FormEditorView.vue** (寫死 3 個選項):
```html
<option value="billing_inquiry">📋 帳單查詢</option>
<option value="maintenance_request">🔧 報修申請</option>
<option value="rent_history">💰 查詢租金紀錄</option>
```

### 問題點
1. **每次新增 API 都要改代碼** - 修改 Vue 文件、重新編譯、重新部署
2. **沒有管理頁面** - 無法通過 UI 管理 API endpoints
3. **不易維護** - 兩個頁面的選項不一致，容易出錯
4. **無法控制可見性** - 不能針對知識庫/表單分別控制哪些 API 可用

---

## 🎯 解決方案

### 核心設計
創建一個**API Endpoints 管理系統**，將 API 選項存儲在數據庫中，並提供管理頁面動態配置。

### 系統架構
```
數據庫 (api_endpoints 表)
  ↓
後端 API (CRUD endpoints)
  ↓
前端管理頁面 (新增/編輯/刪除)
  ↓
動態載入到下拉選單 (KnowledgeView / FormEditorView)
```

---

## 📦 實作內容

### 1. 數據庫設計

**文件**: `database/migrations/create_api_endpoints_table.sql`

**表結構**:
```sql
CREATE TABLE api_endpoints (
    id SERIAL PRIMARY KEY,
    endpoint_id VARCHAR(100) UNIQUE NOT NULL,      -- API 識別碼
    endpoint_name VARCHAR(200) NOT NULL,            -- 顯示名稱
    endpoint_icon VARCHAR(10) DEFAULT '🔌',         -- Emoji 圖示
    description TEXT,                               -- 描述
    handler_function VARCHAR(200),                  -- 後端處理函數名稱

    -- 可用範圍
    available_in_knowledge BOOLEAN DEFAULT TRUE,    -- 知識庫中可用
    available_in_form BOOLEAN DEFAULT TRUE,         -- 表單中可用

    -- 參數定義
    default_params JSONB DEFAULT '[]',

    -- 狀態
    is_active BOOLEAN DEFAULT TRUE,
    display_order INTEGER DEFAULT 0,                -- 顯示順序
    vendor_id INTEGER REFERENCES vendors(id),       -- 業者限制

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**初始數據** (5 個 API endpoints):
| endpoint_id | endpoint_name | icon | 知識庫 | 表單 |
|-------------|---------------|------|--------|------|
| billing_inquiry | 帳單查詢 | 📋 | ✓ | ✓ |
| verify_tenant_identity | 租客身份驗證 | 🔐 | ✓ | ✗ |
| resend_invoice | 重新發送帳單 | 📧 | ✓ | ✗ |
| maintenance_request | 報修申請 | 🔧 | ✓ | ✓ |
| rent_history | 查詢租金紀錄 | 💰 | ✓ | ✓ |

---

### 2. 後端 API 實作

**文件**: `rag-orchestrator/routers/api_endpoints.py`

**功能**: 提供完整的 CRUD API

#### API Endpoints

| 方法 | 路徑 | 功能 | 參數 |
|------|------|------|------|
| GET | `/api/v1/api-endpoints` | 列出所有 API endpoints | `scope`(knowledge/form), `is_active`, `vendor_id` |
| GET | `/api/v1/api-endpoints/{endpoint_id}` | 獲取單個 endpoint 詳情 | - |
| POST | `/api/v1/api-endpoints` | 創建新 endpoint | JSON body |
| PUT | `/api/v1/api-endpoints/{endpoint_id}` | 更新 endpoint | JSON body |
| DELETE | `/api/v1/api-endpoints/{endpoint_id}` | 刪除 endpoint | - |

#### 請求/響應格式

**ApiEndpointCreate** (POST):
```json
{
  "endpoint_id": "rent_history",
  "endpoint_name": "查詢租金紀錄",
  "endpoint_icon": "💰",
  "description": "查詢歷史租金繳納紀錄",
  "handler_function": "handle_rent_history",
  "available_in_knowledge": true,
  "available_in_form": true,
  "is_active": true,
  "display_order": 5,
  "vendor_id": null
}
```

**ApiEndpointResponse**:
```json
{
  "id": 5,
  "endpoint_id": "rent_history",
  "endpoint_name": "查詢租金紀錄",
  "endpoint_icon": "💰",
  "description": "查詢歷史租金繳納紀錄",
  "handler_function": "handle_rent_history",
  "available_in_knowledge": true,
  "available_in_form": true,
  "default_params": [],
  "is_active": true,
  "display_order": 5,
  "vendor_id": null,
  "created_at": "2026-01-18T10:00:00",
  "updated_at": "2026-01-18T10:00:00"
}
```

#### 刪除保護
刪除前檢查是否有知識或表單正在使用：
```python
knowledge_count = await conn.fetchval(
    "SELECT COUNT(*) FROM knowledge WHERE api_config->>'endpoint' = $1",
    endpoint_id
)
form_count = await conn.fetchval(
    "SELECT COUNT(*) FROM form_schemas WHERE api_config->>'endpoint' = $1",
    endpoint_id
)

if knowledge_count > 0 or form_count > 0:
    raise HTTPException(
        status_code=400,
        detail=f"無法刪除：有 {knowledge_count} 筆知識和 {form_count} 筆表單正在使用此 API"
    )
```

#### 路由註冊

**文件**: `rag-orchestrator/app.py`

```python
from routers import api_endpoints

app.include_router(
    api_endpoints.router,
    prefix="/api/v1",
    tags=["api_endpoints"]
)
```

---

### 3. 前端管理頁面

**文件**: `knowledge-admin/frontend/src/views/ApiEndpointsView.vue`

**功能**: 完整的 API Endpoints 管理界面

#### 頁面結構
```
┌─ 說明區塊 ─────────────────────────┐
│  功能說明、使用方式              │
└───────────────────────────────────┘
┌─ 工具列 ───────────────────────────┐
│  [過濾範圍▼] [過濾狀態▼] [新增▼] │
└───────────────────────────────────┘
┌─ 統計卡片 ─────────────────────────┐
│  總數 | 已啟用 | 知識庫 | 表單   │
└───────────────────────────────────┘
┌─ API Endpoints 列表 ───────────────┐
│  ID | 圖示 | Endpoint | 名稱 | ... │
└───────────────────────────────────┘
```

#### 核心功能
1. **列表顯示**: 顯示所有 API endpoints 及其配置
2. **過濾功能**: 按範圍(知識庫/表單)、狀態篩選
3. **新增/編輯**: Modal 表單編輯
4. **啟用/停用**: 一鍵切換狀態
5. **刪除**: 帶保護的刪除功能
6. **統計信息**: 實時統計展示

#### 關鍵代碼

**載入 API Endpoints**:
```javascript
async loadEndpoints() {
  const params = {};
  if (this.filterScope) params.scope = this.filterScope;
  if (this.filterStatus !== '') params.is_active = this.filterStatus === 'true';

  const response = await axios.get(`${RAG_API}/api-endpoints`, { params });
  this.endpointList = response.data;
}
```

**保存 Endpoint**:
```javascript
async saveEndpoint() {
  if (this.editingItem) {
    // 更新
    await axios.put(`${RAG_API}/api-endpoints/${this.editingItem.endpoint_id}`, this.formData);
  } else {
    // 新增
    await axios.post(`${RAG_API}/api-endpoints`, this.formData);
  }
  this.loadEndpoints();
}
```

#### 路由配置

**文件**: `knowledge-admin/frontend/src/router.js`

```javascript
import ApiEndpointsView from './views/ApiEndpointsView.vue';

{
  path: '/api-endpoints',
  name: 'ApiEndpoints',
  component: ApiEndpointsView,
  meta: { requiresAuth: true }
}
```

#### 導航菜單

**文件**: `knowledge-admin/frontend/src/App.vue`

```html
<router-link to="/api-endpoints" class="nav-item nav-item-sub">
  <span class="nav-icon">🔌</span>
  <span class="nav-text">API 端點管理</span>
</router-link>
```

---

### 4. 前端動態載入實作

#### 4.1 KnowledgeView.vue 修改

**HTML 修改** (line 345-357):
```html
<!-- 修改前：硬編碼 -->
<option value="billing_inquiry">📋 帳單查詢</option>
<option value="verify_tenant_identity">🔐 租客身份驗證</option>
...

<!-- 修改後：動態載入 -->
<select v-model="apiConfigData.endpoint" class="form-select">
  <option value="">請選擇...</option>
  <option
    v-for="endpoint in availableApiEndpoints"
    :key="endpoint.endpoint_id"
    :value="endpoint.endpoint_id"
  >
    {{ endpoint.endpoint_icon }} {{ endpoint.endpoint_name }}
  </option>
</select>
```

**JavaScript 修改**:

1. **新增數據欄位** (line 507):
```javascript
data() {
  return {
    availableApiEndpoints: [],  // ⭐ 新增
    // ... 其他欄位
  }
}
```

2. **新增載入方法** (line 793-802):
```javascript
async loadApiEndpoints() {
  try {
    const response = await axios.get('/rag-api/v1/api-endpoints?scope=knowledge&is_active=true');
    this.availableApiEndpoints = response.data || [];
    console.log('🔌 已載入 API Endpoints:', this.availableApiEndpoints.length, '個');
  } catch (error) {
    console.error('載入 API Endpoints 失敗', error);
    this.availableApiEndpoints = [];
  }
}
```

3. **mounted 調用** (line 659):
```javascript
async mounted() {
  await this.loadIntents();
  await this.loadBusinessTypes();
  await this.loadTargetUsers();
  await this.loadForms();
  await this.loadApiEndpoints();  // ⭐ 新增
  this.loadStats();
  await this.loadKnowledge();
}
```

#### 4.2 FormEditorView.vue 修改

**HTML 修改** (line 77-89):
```html
<!-- 修改前：硬編碼 -->
<option value="billing_inquiry">📋 帳單查詢</option>
<option value="maintenance_request">🔧 報修申請</option>
<option value="rent_history">💰 查詢租金紀錄</option>

<!-- 修改後：動態載入 -->
<select v-model="apiConfigData.endpoint" class="form-select">
  <option value="">請選擇...</option>
  <option
    v-for="endpoint in availableApiEndpoints"
    :key="endpoint.endpoint_id"
    :value="endpoint.endpoint_id"
  >
    {{ endpoint.endpoint_icon }} {{ endpoint.endpoint_name }}
  </option>
</select>
```

**JavaScript 修改** (Composition API):

1. **新增 ref** (line 326):
```javascript
const availableApiEndpoints = ref([]);
```

2. **新增載入方法** (line 329-338):
```javascript
const loadApiEndpoints = async () => {
  try {
    const data = await api.get('/rag-api/v1/api-endpoints?scope=form&is_active=true');
    availableApiEndpoints.value = data || [];
    console.log('🔌 已載入 API Endpoints:', availableApiEndpoints.value.length, '個');
  } catch (error) {
    console.error('載入 API Endpoints 失敗', error);
    availableApiEndpoints.value = [];
  }
};
```

3. **onMounted 調用** (line 607):
```javascript
onMounted(async () => {
  await loadApiEndpoints();  // ⭐ 新增

  if (route.name !== 'FormNew' && formId.value && formId.value !== 'new') {
    loadForm();
  }
});
```

4. **return 暴露** (line 624):
```javascript
return {
  loading,
  saving,
  isNew,
  formData,
  apiConfigData,
  showApiConfig,
  availableApiEndpoints,  // ⭐ 新增
  // ... 其他方法
};
```

---

## 🔄 數據流

### 完整流程
```
1. 管理員訪問 /api-endpoints 頁面
   ↓
2. 新增/編輯 API Endpoint
   POST /api/v1/api-endpoints
   {
     "endpoint_id": "new_api",
     "endpoint_name": "新功能",
     "endpoint_icon": "🎯",
     "available_in_knowledge": true,
     "available_in_form": true,
     "is_active": true
   }
   ↓
3. 後端保存到數據庫
   INSERT INTO api_endpoints (...)
   ↓
4. 用戶打開知識庫管理頁面
   ↓
5. KnowledgeView.vue mounted()
   GET /api/v1/api-endpoints?scope=knowledge&is_active=true
   ↓
6. 後端查詢並返回
   SELECT * FROM api_endpoints
   WHERE available_in_knowledge = TRUE AND is_active = TRUE
   ↓
7. 前端渲染下拉選單
   <option v-for="endpoint in availableApiEndpoints">
     {{ endpoint.endpoint_icon }} {{ endpoint.endpoint_name }}
   </option>
   ↓
8. 用戶選擇 API，保存知識
   {
     "api_config": {
       "endpoint": "new_api",
       "params": {...},
       "combine_with_knowledge": true
     }
   }
```

---

## 📊 修改統計

### 文件統計
| 類別 | 文件數 | 新增 | 修改 | 總行數 |
|------|--------|------|------|--------|
| **數據庫** | 1 | 1 | 0 | ~130 行 |
| **後端 API** | 2 | 1 | 1 | ~360 行 |
| **前端頁面** | 3 | 1 | 2 | ~470 行 |
| **路由/配置** | 2 | 0 | 2 | ~20 行 |
| **文檔** | 2 | 2 | 0 | ~600 行 |
| **總計** | **10** | **5** | **5** | **~1580 行** |

### 詳細清單
| 文件 | 狀態 | 變更類型 | 行數 |
|------|------|----------|------|
| `database/migrations/create_api_endpoints_table.sql` | 新增 | 數據庫 Schema | ~130 |
| `rag-orchestrator/routers/api_endpoints.py` | 新增 | 後端 API | ~340 |
| `rag-orchestrator/app.py` | 修改 | 路由註冊 | +2 |
| `knowledge-admin/frontend/src/views/ApiEndpointsView.vue` | 新增 | 管理頁面 | ~360 |
| `knowledge-admin/frontend/src/views/KnowledgeView.vue` | 修改 | 動態載入 | +18 |
| `knowledge-admin/frontend/src/views/FormEditorView.vue` | 修改 | 動態載入 | +22 |
| `knowledge-admin/frontend/src/router.js` | 修改 | 路由配置 | +7 |
| `knowledge-admin/frontend/src/App.vue` | 修改 | 導航菜單 | +11 |
| `docs/HOW_TO_ADD_API_ENDPOINTS.md` | 新增 | 使用指南 | ~320 |
| `docs/API_ENDPOINTS_MANAGEMENT_IMPLEMENTATION.md` | 新增 | 實作總結 | ~280 |

---

## ✅ 功能驗證

### 1. 數據庫驗證

**查詢初始數據**:
```bash
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin \
  -c "SELECT endpoint_id, endpoint_name, endpoint_icon FROM api_endpoints;"
```

**結果**:
```
      endpoint_id       | endpoint_name | endpoint_icon
------------------------+---------------+---------------
 billing_inquiry        | 帳單查詢      | 📋
 verify_tenant_identity | 租客身份驗證  | 🔐
 resend_invoice         | 重新發送帳單  | 📧
 maintenance_request    | 報修申請      | 🔧
 rent_history           | 查詢租金紀錄  | 💰
(5 rows)
```

### 2. API 測試

**列出知識庫可用的 API**:
```bash
curl http://localhost:8100/api/v1/api-endpoints?scope=knowledge&is_active=true
```

**預期結果**: 返回 5 個 API endpoints (全部標記為 available_in_knowledge=true)

**列出表單可用的 API**:
```bash
curl http://localhost:8100/api/v1/api-endpoints?scope=form&is_active=true
```

**預期結果**: 返回 3 個 API endpoints (billing_inquiry, maintenance_request, rent_history)

### 3. 前端測試

#### 管理頁面測試
1. ✅ 訪問 http://localhost:3000/api-endpoints
2. ✅ 查看 API endpoints 列表
3. ✅ 新增一個新的 API endpoint
4. ✅ 編輯現有 endpoint
5. ✅ 啟用/停用 endpoint
6. ✅ 刪除 endpoint (若未被使用)

#### 動態載入測試
1. ✅ 訪問知識庫管理頁面
2. ✅ 選擇 action_type = "API 調用"
3. ✅ 檢查 API Endpoint 下拉選單
4. ✅ 應顯示從數據庫載入的選項（而非硬編碼）

---

## 🎯 對比：改動前後

### 改動前 (硬編碼)
```
需求：新增一個 API endpoint "查詢合約"

步驟：
1. 修改 KnowledgeView.vue，添加 <option> (5 分鐘)
2. 修改 FormEditorView.vue，添加 <option> (5 分鐘)
3. 重新編譯前端 npm run build (2 分鐘)
4. 重啟前端服務 docker restart (1 分鐘)
5. 實作後端 handler (30 分鐘)

總耗時：~43 分鐘
風險：可能忘記修改其中一個文件，導致不一致
```

### 改動後 (動態管理)
```
需求：新增一個 API endpoint "查詢合約"

步驟：
1. 訪問 /api-endpoints 頁面 (10 秒)
2. 點擊「新增 API Endpoint」 (10 秒)
3. 填寫表單並保存：
   - Endpoint ID: contract_inquiry
   - 名稱：查詢合約
   - 圖示：📄
   - 勾選：知識庫可用、表單可用
   (30 秒)
4. 實作後端 handler (30 分鐘)

總耗時：~31 分鐘
風險：無，UI 自動更新，保證一致性
```

**節省時間**: ~12 分鐘/次
**降低風險**: 消除了代碼修改和部署風險

---

## 🚀 後續擴展建議

### 1. 參數模板功能
為每個 API endpoint 定義參數模板：
```json
{
  "endpoint_id": "billing_inquiry",
  "default_params": [
    {
      "name": "user_id",
      "type": "string",
      "required": true,
      "source": "session",
      "description": "用戶 ID"
    },
    {
      "name": "month",
      "type": "string",
      "required": false,
      "source": "form",
      "description": "查詢月份"
    }
  ]
}
```

### 2. API 測試功能
在管理頁面中加入測試功能：
- 配置測試參數
- 調用 API
- 查看返回結果
- 驗證格式化效果

### 3. 使用統計
追蹤每個 API endpoint 的使用頻率：
```sql
ALTER TABLE api_endpoints ADD COLUMN usage_count INTEGER DEFAULT 0;
```

### 4. 版本控制
為 API 配置添加版本管理：
- 記錄修改歷史
- 支持回滾
- 審計日誌

---

## 📚 相關文檔

- 如何新增 API Endpoints - 操作指南
- 前端實作總結 - 前端修改詳情
- [知識動作系統設計](../design/KNOWLEDGE_ACTION_SYSTEM_DESIGN.md) - 系統架構
- API Call Handler 實作 - 後端處理

---

## 🎉 總結

### 已完成
- ✅ 數據庫表設計並創建
- ✅ 後端 CRUD API 實作
- ✅ 前端管理頁面開發
- ✅ KnowledgeView.vue 動態載入
- ✅ FormEditorView.vue 動態載入
- ✅ 路由和導航配置
- ✅ Migration 執行成功
- ✅ 初始數據載入成功

### 優勢
1. **易維護**: 通過 UI 管理，無需修改代碼
2. **一致性**: 單一數據源，消除不一致風險
3. **靈活性**: 可控制每個 API 在不同場景的可見性
4. **可擴展**: 支持業者級別的 API 配置
5. **安全性**: 刪除保護，防止誤刪正在使用的 API

### 影響範圍
- 對現有功能**完全兼容**
- 不影響已存在的知識和表單配置
- 向後兼容所有現有 API endpoint ID

---

**維護者**: Claude Code
**實作日期**: 2026-01-18
**版本**: 1.0
**狀態**: ✅ 生產就緒
