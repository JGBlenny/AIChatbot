# SOP 與意圖關聯架構說明文檔

## 目錄
1. [架構概述](#架構概述)
2. [數據庫結構](#數據庫結構)
3. [API 端點](#api-端點)
4. [前端實現](#前端實現)
5. [流程示例](#流程示例)

---

## 架構概述

該項目採用**複製-編輯模式**（Copy-Edit Pattern），而非早期的模板覆蓋模式。核心設計：

1. **平台級**：平台管理員定義 SOP 範本（按業種分類）
2. **業者級**：業者複製平台範本後自行編輯調整
3. **意圖關聯**：SOP 項目可關聯到特定意圖，用於智能檢索和回答生成

### 演進史
- **Migration 33**：初版架構（支援金流模式調整）
- **Migration 35**：添加平台範本系統（Template + Override 架構）
- **Migration 36**：簡化架構，移除覆蓋機制，改為複製-編輯模式

---

## 數據庫結構

### 1. 核心表

#### 1.1 平台級表

**platform_sop_categories** - 平台 SOP 分類
```sql
id SERIAL PRIMARY KEY
category_name VARCHAR(200) UNIQUE         -- 分類名稱（全局唯一）
description TEXT                          -- 分類說明
display_order INTEGER                     -- 顯示順序
template_notes TEXT                       -- 範本說明（幫助業者理解）
is_active BOOLEAN DEFAULT TRUE
created_at / updated_at TIMESTAMP
```

**platform_sop_templates** - 平台 SOP 範本
```sql
id SERIAL PRIMARY KEY
category_id INTEGER (FK to platform_sop_categories)
business_type VARCHAR(50)                 -- 業種類型
                                          -- 取值：'full_service'(包租型)、
                                          --      'property_management'(代管型)、
                                          --      NULL(通用)

item_number INTEGER                       -- 項次編號
item_name VARCHAR(200)                    -- 項目名稱
content TEXT NOT NULL                     -- 範本內容

-- 關聯設定
related_intent_id INTEGER (FK to intents) -- 預設關聯意圖
priority INTEGER DEFAULT 50               -- 優先級（0-100）

-- 範本引導
template_notes TEXT                       -- 範本說明
customization_hint TEXT                   -- 自訂提示

is_active BOOLEAN DEFAULT TRUE
created_at / updated_at TIMESTAMP

CONSTRAINT unique_template_item_number UNIQUE(category_id, item_number)
```

**索引**
```sql
idx_platform_sop_templates_category
idx_platform_sop_templates_intent      -- 用於意圖查詢
idx_platform_sop_templates_business_type
idx_platform_sop_templates_active
idx_platform_sop_templates_priority
```

---

#### 1.2 業者級表

**vendors** - 業者基本信息
```sql
id SERIAL PRIMARY KEY
code VARCHAR(50)
name VARCHAR(200)
business_type VARCHAR(50)                 -- 業種類型（full_service/property_management）
cashflow_model VARCHAR(50)                -- 金流模式（已移至配置，保留用於查詢優化）
is_active BOOLEAN
...
```

**vendor_sop_categories** - 業者 SOP 分類
```sql
id SERIAL PRIMARY KEY
vendor_id INTEGER (FK to vendors)
category_name VARCHAR(200)
description TEXT
display_order INTEGER
is_active BOOLEAN
created_at / updated_at TIMESTAMP
```

**vendor_sop_items** - 業者 SOP 項目（最重要）
```sql
id SERIAL PRIMARY KEY
category_id INTEGER (FK to vendor_sop_categories)
vendor_id INTEGER (FK to vendors)

item_number INTEGER                       -- 項次
item_name VARCHAR(200)                    -- 項目名稱
content TEXT NOT NULL                     -- 業者自訂的內容

-- 來源追蹤
template_id INTEGER (FK to platform_sop_templates) -- 記錄來自哪個範本

-- 關聯與優先級
related_intent_id INTEGER (FK to intents) -- 關聯意圖（核心！）
priority INTEGER DEFAULT 0                -- 優先級

is_active BOOLEAN DEFAULT TRUE
created_at / updated_at TIMESTAMP
```

**索引**
```sql
idx_sop_items_vendor
idx_sop_items_category
idx_sop_items_intent                    -- 用於按意圖檢索
idx_sop_items_cashflow_check
idx_sop_items_active
```

---

#### 1.3 意圖表

**intents** - 意圖定義
```sql
id SERIAL PRIMARY KEY
name VARCHAR(100)                         -- 意圖名稱（如「租賃問詢」）
category VARCHAR(100)                     -- 分類
is_active BOOLEAN
created_at / updated_at TIMESTAMP
```

---

### 2. 檢視

#### v_vendor_available_sop_templates
根據業者業種過濾可用的平台範本
```
SELECT
  v.id, v.business_type,
  pt.id as template_id,
  pc.category_name,
  pt.item_name,
  pt.related_intent_id,
  CASE WHEN vsi.id IS NOT NULL THEN true ELSE false END AS already_copied,
  vsi.id AS vendor_sop_item_id
FROM vendors v
CROSS JOIN platform_sop_templates pt
...
WHERE pt.is_active AND (pt.business_type = v.business_type OR pt.business_type IS NULL)
```

#### v_platform_sop_template_usage
統計每個範本的使用情況
```
SELECT
  pt.id,
  COUNT(DISTINCT vsi.vendor_id) AS copied_by_vendor_count,
  usage_percentage
```

---

## API 端點

### 平台管理員 API（platform_sop.py）

#### 分類管理
```
GET    /api/v1/platform/sop/categories
POST   /api/v1/platform/sop/categories
PUT    /api/v1/platform/sop/categories/{category_id}
DELETE /api/v1/platform/sop/categories/{category_id}
```

**POST 新增分類範例**
```json
{
  "category_name": "租金繳納",
  "description": "關於租金繳納方式的規定",
  "display_order": 1,
  "template_notes": "業者可根據自身金流模式調整"
}
```

#### 範本管理
```
GET    /api/v1/platform/sop/templates
POST   /api/v1/platform/sop/templates
PUT    /api/v1/platform/sop/templates/{template_id}
DELETE /api/v1/platform/sop/templates/{template_id}
```

**POST 新增範本範例**（包含意圖關聯）
```json
{
  "category_id": 1,
  "business_type": null,              // 通用範本
  "item_number": 1,
  "item_name": "租金如何繳納",
  "content": "租金應於每月 X 號之前繳納...",
  
  "related_intent_id": 5,             // 關聯到「租金問詢」意圖
  "priority": 80,
  
  "template_notes": "此 SOP 適用於所有業者",
  "customization_hint": "業者可根據實際情況調整繳納方式"
}
```

#### 統計 API
```
GET /api/v1/platform/sop/statistics/usage
GET /api/v1/platform/sop/templates/{template_id}/usage
```

---

### 業者管理 API（vendors.py）

#### SOP 分類管理
```
GET  /api/v1/vendors/{vendor_id}/sop/categories
POST /api/v1/vendors/{vendor_id}/sop/categories
```

#### SOP 項目管理
```
GET    /api/v1/vendors/{vendor_id}/sop/items
PUT    /api/v1/vendors/{vendor_id}/sop/items/{item_id}
DELETE /api/v1/vendors/{vendor_id}/sop/items/{item_id}
POST   /api/v1/vendors/{vendor_id}/sop/items
```

**PUT 更新 SOP 項目（含意圖關聯）**
```json
{
  "item_name": "租金繳納規定",
  "content": "我們的租金繳納規定是...",
  "related_intent_id": 5,             // 更新關聯意圖
  "priority": 90                      // 優先級
}
```

#### 範本複製 API（核心功能）
```
GET  /api/v1/vendors/{vendor_id}/sop/available-templates
POST /api/v1/vendors/{vendor_id}/sop/copy-template
POST /api/v1/vendors/{vendor_id}/sop/copy-category-templates
POST /api/v1/vendors/{vendor_id}/sop/copy-all-templates
```

**POST 複製單個範本**
```json
{
  "template_id": 42,                  // 要複製的範本
  "category_id": 5,                   // 目標業者分類
  "item_number": null                 // 自動分配
}

// 返回
{
  "id": 100,
  "item_name": "租金如何繳納",
  "content": "範本內容被複製到業者 SOP",
  "related_intent_id": 5,             // 自動保留關聯意圖
  "priority": 80,
  "template_id": 42,                  // 記錄來源
  "message": "範本已成功複製，可以進行編輯調整"
}
```

**POST 複製整份業種範本**
```json
{}  // 無需參數

// 返回
{
  "message": "成功複製整份 SOP 範本",
  "business_type": "full_service",
  "categories_created": 5,
  "total_items_copied": 45,
  "categories": [
    {"category_id": 1, "category_name": "租賃流程", "items_count": 10},
    ...
  ]
}
```

---

## 前端實現

### 1. VendorSOPManager.vue
**路徑**: `/Users/lenny/jgb/AIChatbot/knowledge-admin/frontend/src/components/VendorSOPManager.vue`

**功能**：業者管理自己的 SOP

**主要功能**：
- Tab 1: SOP 範本概覽
  - 顯示符合業種的所有平台範本
  - 按分類組織
  - 複製整份範本按鈕
  
- Tab 2: 我的 SOP
  - 顯示已複製的 SOP
  - 編輯功能
  - 刪除功能

**編輯 Modal 中的意圖關聯**
```vue
<div class="form-group">
  <label>關聯意圖</label>
  <select v-model.number="editingForm.related_intent_id" class="form-control">
    <option :value="null">無</option>
    <option v-for="intent in intents" :key="intent.id" :value="intent.id">
      {{ intent.name }}
    </option>
  </select>
</div>
```

**關鍵 API 調用**
```javascript
// 加載可用範本
const response = await axios.get(
  `${RAG_API}/api/v1/vendors/${this.vendorId}/sop/available-templates`
);

// 更新 SOP 項目（包括意圖）
await axios.put(
  `${RAG_API}/api/v1/vendors/${this.vendorId}/sop/items/${this.editingForm.id}`,
  {
    item_name: this.editingForm.item_name,
    content: this.editingForm.content,
    related_intent_id: this.editingForm.related_intent_id,
    priority: this.editingForm.priority
  }
);

// 複製整份範本
const response = await axios.post(
  `${RAG_API}/api/v1/vendors/${this.vendorId}/sop/copy-all-templates`
);
```

---

### 2. PlatformSOPView.vue
**路徑**: `/Users/lenny/jgb/AIChatbot/knowledge-admin/frontend/src/views/PlatformSOPView.vue`

**功能**：平台管理員管理 SOP 範本

**顯示內容**：
- 按業種分組（包租型、代管型、通用）
- 各業種下的分類統計
- 分類和範本管理按鈕

---

### 3. PlatformSOPEditView.vue
**路徑**: `/Users/lenny/jgb/AIChatbot/knowledge-admin/frontend/src/views/PlatformSOPEditView.vue`

**功能**：編輯特定業種的 SOP 範本

**編輯表單中的意圖關聯**
```vue
<div class="form-group">
  <label>關聯意圖</label>
  <select v-model.number="templateForm.related_intent_id" class="form-control">
    <option :value="null">無</option>
    <option v-for="intent in intents" :key="intent.id" :value="intent.id">
      {{ intent.name }}
    </option>
  </select>
</div>
```

**範本卡片顯示意圖**
```vue
<span v-if="template.related_intent_name" class="badge badge-intent">
  🎯 {{ template.related_intent_name }}
</span>
```

---

## 流程示例

### 場景 1：平台管理員建立 SOP 範本

```
1. 進入 PlatformSOPView
   ↓
2. 點擊「新增分類」→ 建立「租金繳納」分類
   ↓
3. 點擊「管理 SOP」→ 進入 PlatformSOPEditView
   ↓
4. 點擊「新增 SOP 項目」→ 填寫表單
   ├─ item_name: "租金如何繳納"
   ├─ content: "租金應於每月 X 號前繳納..."
   ├─ related_intent_id: 5（「租金問詢」意圖）
   └─ priority: 80
   ↓
5. 保存 → INSERT into platform_sop_templates
   ↓
6. 模板現在可被業者複製
```

### 場景 2：業者複製並編輯 SOP

```
1. 業者進入 VendorSOPManager
   ↓
2. 看到「SOP 範本概覽」Tab
   ├─ 顯示 5 個分類，45 個項目
   └─ 顯示「複製整份 SOP 範本」按鈕
   ↓
3. 點擊「複製整份 SOP 範本」
   ↓
4. 後端執行：
   a. 刪除現有 SOP（如有）
   b. 按業種查詢平台範本
   c. 逐個 INSERT into vendor_sop_items
      - 複製 item_name, content, related_intent_id, priority 等
      - 記錄 template_id（來源追蹤）
   d. 自動建立業者分類
   ↓
5. 業者看到「我的 SOP」Tab
   ├─ 5 個分類
   ├─ 45 個項目
   └─ 每項可編輯
   ↓
6. 業者點擊「編輯」某個 SOP
   ↓
7. 編輯 Modal 顯示：
   ├─ item_name
   ├─ content
   ├─ related_intent_id（下拉選單，可改）
   └─ priority
   ↓
8. 業者可修改內容或關聯意圖
   ↓
9. 保存 → PUT vendor_sop_items.related_intent_id
```

### 場景 3：根據意圖檢索 SOP

```
1. 用戶提問：「租金怎麼繳？」
   ↓
2. NLU 分類為意圖 ID = 5（租金問詢）
   ↓
3. RAG 系統調用 vendor_sop_retriever.retrieve_sop_by_intent()
   ↓
4. 後端執行 SQL：
   SELECT * FROM vendor_sop_items
   WHERE vendor_id = ? 
   AND related_intent_id = 5
   AND is_active = TRUE
   ORDER BY priority DESC
   ↓
5. 返回相關 SOP 項目列表（已排序）
   ↓
6. LLM 使用 SOP 內容生成回答
   ↓
7. 用戶收到業者自訂的租金繳納規定
```

---

## 關鍵設計要點

### 1. 意圖關聯的用途

| 用途 | 說明 |
|------|------|
| 智能檢索 | 根據用戶意圖快速定位相關 SOP |
| 回答優化 | LLM 使用意圖相關的 SOP 生成準確回答 |
| 優先級排序 | 同一分類下的多個 SOP 按意圖和優先級排序 |
| 分類引導 | 幫助業者理解 SOP 應該關聯哪個意圖 |

### 2. 複製-編輯模式 vs 覆蓋模式

**複製-編輯（當前）**：
- 優點：業者可完全自由編輯，不依賴範本
- 缺點：範本更新不會自動應用到已複製的 SOP
- 適用：業者個性化需求強

**覆蓋模式（已廢棄）**：
- 優點：業者只覆寫差異部分，節省空間
- 缺點：複雜度高，維護困難
- 原因：簡化架構，迎合用戶習慣

### 3. 業種過濾

```sql
WHERE (pt.business_type = v.business_type OR pt.business_type IS NULL)
```

- `NULL` 業種 = 通用範本（所有業種可見）
- `full_service` 業種 = 只有包租型業者可見
- 業者複製時自動檢查業種匹配

---

## 文件位置總結

| 類型 | 路徑 |
|------|------|
| **數據庫 Migration** | 
| 業者 SOP 表 | `/Users/lenny/jgb/AIChatbot/database/migrations/33-create-vendor-sop-tables.sql` |
| 平台 SOP 範本 | `/Users/lenny/jgb/AIChatbot/database/migrations/35-create-platform-sop-templates.sql` |
| 架構簡化 | `/Users/lenny/jgb/AIChatbot/database/migrations/36-simplify-sop-architecture.sql` |
| **後端 API** |
| 平台管理員 | `/Users/lenny/jgb/AIChatbot/rag-orchestrator/routers/platform_sop.py` |
| 業者管理 | `/Users/lenny/jgb/AIChatbot/rag-orchestrator/routers/vendors.py`（行 472+） |
| SOP 檢索 | `/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/vendor_sop_retriever.py` |
| **前端組件** |
| 業者 SOP 管理 | `/Users/lenny/jgb/AIChatbot/knowledge-admin/frontend/src/components/VendorSOPManager.vue` |
| 平台 SOP 瀏覽 | `/Users/lenny/jgb/AIChatbot/knowledge-admin/frontend/src/views/PlatformSOPView.vue` |
| 平台 SOP 編輯 | `/Users/lenny/jgb/AIChatbot/knowledge-admin/frontend/src/views/PlatformSOPEditView.vue` |

---

## 數據流圖

```
┌─────────────────────────────────────────────────────────────────┐
│                    平台管理員界面                                    │
│              (PlatformSOPView / PlatformSOPEditView)              │
└────────────────────────┬──────────────────────────────────────────┘
                         │
                         ▼
         ┌────────────────────────────────┐
         │  platform_sop.py API           │
         │ - 建立範本                      │
         │ - 設定 related_intent_id       │
         │ - 發佈到平台                    │
         └────────────┬───────────────────┘
                      │
                      ▼
         ┌────────────────────────────────┐
         │ platform_sop_templates 表       │
         │ - item_name                    │
         │ - content                      │
         │ - related_intent_id ◄──────┐  │
         │ - priority                     │
         │ - business_type                │
         └────────────┬───────────────────┘
                      │
                      │ (業者查看可用範本)
                      ▼
         ┌────────────────────────────────┐
         │ vendors.py API                 │
         │ - /sop/available-templates     │
         │ - /sop/copy-template           │
         │ - /sop/copy-all-templates      │
         └────────────┬───────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────────────┐
│               業者界面 (VendorSOPManager.vue)                      │
│  - 查看可用範本 (v_vendor_available_sop_templates 檢視)           │
│  - 複製範本                                                       │
│  - 編輯 SOP (包括 related_intent_id)                             │
└────────────────────┬──────────────────────────────────────────────┘
                     │
                     ▼
         ┌────────────────────────────────┐
         │ vendor_sop_items 表             │
         │ - id                           │
         │ - item_name (已編輯)           │
         │ - content (已編輯)             │
         │ - related_intent_id ◄──────┐  │
         │ - template_id (來源追蹤)      │
         │ - priority                     │
         │ - vendor_id                    │
         └────────────┬───────────────────┘
                      │
                      │ (用戶提問時)
                      ▼
         ┌────────────────────────────────┐
         │ vendor_sop_retriever.py         │
         │ retrieve_sop_by_intent()        │
         └────────────┬───────────────────┘
                      │
                      ▼
         ┌────────────────────────────────┐
         │ SQL 查詢                        │
         │ WHERE related_intent_id = ?    │
         │ ORDER BY priority DESC         │
         └────────────┬───────────────────┘
                      │
                      ▼
    ┌──────────────────────────────────────┐
    │ LLM Answer Optimizer                 │
    │ - 使用 SOP 生成準確回答              │
    └──────────────────────────────────────┘
```

