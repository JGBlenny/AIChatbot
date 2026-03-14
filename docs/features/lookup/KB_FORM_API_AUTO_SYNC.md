# 知識庫、表單與 API 端點自動關聯機制

**創建日期**: 2026-03-13
**版本**: 2.0
**狀態**: ✅ 已實作並測試（含雙引用方式修復）

---

## 📋 目錄

1. [概述](#概述)
2. [三角關係圖](#三角關係圖)
3. [資料庫設計](#資料庫設計)
4. [Trigger 自動同步機制](#trigger-自動同步機制)
5. [後端 API](#後端-api)
6. [前端顯示](#前端顯示)
7. [使用指南](#使用指南)
8. [測試驗證](#測試驗證)
9. [常見問題](#常見問題)

---

## 概述

### 問題背景

在 Lookup 系統中,存在三個核心實體之間的關聯:

1. **知識庫 (knowledge_base)** - 儲存問答內容
2. **表單 (form_schemas)** - 定義 Lookup 表單結構
3. **API 端點 (api_endpoints)** - 定義 Lookup API 執行邏輯

**核心問題**: 知識庫有**兩種方式**引用 API 端點:
- **方式 A** (通過表單): 知識庫.form_id → form_schemas.api_config→'endpoint' → api_endpoints
- **方式 B** (直接引用): 知識庫.api_config→'endpoint' → api_endpoints（不需要表單）

如何讓系統自動追蹤哪些知識庫使用了哪個 API 端點?

### 解決方案

實作資料庫 Trigger,在知識庫變更時自動更新 `api_endpoints.related_kb_ids` 欄位,**同時支援兩種引用方式**。

### 設計目標

- ✅ **自動化**: 知識庫變更時,自動更新 API 端點關聯
- ✅ **即時性**: INSERT/UPDATE/DELETE 即時生效
- ✅ **一致性**: 保證資料一致,無需手動維護
- ✅ **可視化**: 前端可查看關聯統計

---

## 三角關係圖

```
┌─────────────────────────────────────────────────────────────┐
│                    使用者操作流程                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    在 /knowledge 頁面編輯知識庫
                    設定 form_id = 'parcel_service_form_v2'
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  knowledge_base 表                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ id: 1397                                              │   │
│  │ question_summary: "包裹代收服務說明"                   │   │
│  │ form_id: "parcel_service_form_v2"  ← 使用者設定       │   │
│  │ action_type: "form_then_api"                         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    Trigger 偵測到變更
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  form_schemas 表                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ form_id: "parcel_service_form_v2"                    │   │
│  │ form_name: "包裹代收服務查詢"                          │   │
│  │ api_config: {                                        │   │
│  │   "endpoint": "lookup"  ← Trigger 讀取此欄位          │   │
│  │ }                                                    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    Trigger 更新 API 端點
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  api_endpoints 表                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ endpoint_id: "lookup"                                │   │
│  │ endpoint_name: "通用查詢 API"                          │   │
│  │ related_kb_ids: {1394, 1396, 1397}  ← 自動更新        │   │
│  │                        ↑                             │   │
│  │                        └─ 包含 KB #1397              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
              在 /lookup-forms 或 /api-endpoints 頁面查看
```

### 關鍵數據流

**方式 A (通過表單)**:
```
知識庫 (form_id) → 表單 (api_config.endpoint) → API 端點 (related_kb_ids)
```

**範例 A**:
- KB #1397 設定 `form_id = 'parcel_service_form_v2'`
- parcel_service_form_v2 的 `api_config.endpoint = 'lookup'`
- Trigger 自動將 1397 加入 `api_endpoints.related_kb_ids`

**方式 B (直接引用)**:
```
知識庫 (api_config.endpoint) → API 端點 (related_kb_ids)
```

**範例 B**:
- KB #1403 設定 `api_config = {"endpoint": "lookup", "static_params": {"key": "客服專線", "category": "customer_service"}}`
- Trigger 自動將 1403 加入 `api_endpoints.related_kb_ids`
- **不需要 form_id**,直接使用 API

**實際案例 (lookup endpoint)**:
- 方式 A: KB #1394, #1396, #1397（3個）
- 方式 B: KB #1403, #1405, #1406, #1407, #1408（5個）
- **Total**: 8 個知識庫,Trigger 自動維護

---

## 資料庫設計

### api_endpoints 表結構

```sql
CREATE TABLE api_endpoints (
    id SERIAL PRIMARY KEY,
    endpoint_id VARCHAR(100) UNIQUE NOT NULL,
    endpoint_name VARCHAR(200) NOT NULL,
    -- ... 其他欄位 ...

    -- ⭐ 關鍵欄位: 關聯的知識庫 ID 陣列
    related_kb_ids INTEGER[] DEFAULT '{}',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引優化
CREATE INDEX idx_api_endpoints_related_kb_ids
ON api_endpoints USING GIN(related_kb_ids);
```

### 關聯查詢邏輯

```sql
-- 查詢某個 API 端點關聯的所有知識庫
SELECT kb.*
FROM knowledge_base kb
WHERE kb.id = ANY(
    SELECT related_kb_ids
    FROM api_endpoints
    WHERE endpoint_id = 'lookup'
);

-- 查詢某個表單關聯的知識庫
SELECT kb.*
FROM knowledge_base kb
WHERE kb.form_id = 'parcel_service_form_v2';
```

---

## Trigger 自動同步機制

### Trigger 函數實作

**文件位置**:
- 原始版本: `database/migrations/add_api_endpoint_kb_sync_trigger.sql`
- **修復版本 (v2.0)**: `database/migrations/fix_api_endpoint_kb_sync_trigger.sql`

```sql
CREATE OR REPLACE FUNCTION sync_api_endpoint_kb_ids()
RETURNS TRIGGER AS $$
DECLARE
  affected_endpoint_ids TEXT[];
  old_endpoint_ids TEXT[];
  new_endpoint_ids TEXT[];
BEGIN
  -- ========================================
  -- 處理 DELETE 操作
  -- ========================================
  IF (TG_OP = 'DELETE') THEN
    -- 方式 A：通過 form_id 引用的 endpoints
    IF OLD.form_id IS NOT NULL THEN
      SELECT ARRAY_AGG(DISTINCT api_config->>'endpoint')
      INTO old_endpoint_ids
      FROM form_schemas
      WHERE form_id = OLD.form_id
        AND api_config->>'endpoint' IS NOT NULL;
    END IF;

    -- 方式 B：直接在 api_config 引用的 endpoint
    IF OLD.api_config IS NOT NULL AND OLD.api_config->>'endpoint' IS NOT NULL THEN
      old_endpoint_ids := ARRAY(
        SELECT DISTINCT unnest(
          COALESCE(old_endpoint_ids, '{}') || ARRAY[OLD.api_config->>'endpoint']
        )
      );
    END IF;

    affected_endpoint_ids := old_endpoint_ids;

  -- ========================================
  -- 處理 UPDATE 操作
  -- ========================================
  ELSIF (TG_OP = 'UPDATE') THEN
    -- 方式 A：form_id 改變時,需要更新舊的和新的 endpoints
    IF OLD.form_id IS NOT NULL AND OLD.form_id != COALESCE(NEW.form_id, '') THEN
      SELECT ARRAY_AGG(DISTINCT api_config->>'endpoint')
      INTO old_endpoint_ids
      FROM form_schemas
      WHERE form_id = OLD.form_id
        AND api_config->>'endpoint' IS NOT NULL;
    END IF;

    IF NEW.form_id IS NOT NULL THEN
      SELECT ARRAY_AGG(DISTINCT api_config->>'endpoint')
      INTO new_endpoint_ids
      FROM form_schemas
      WHERE form_id = NEW.form_id
        AND api_config->>'endpoint' IS NOT NULL;
    END IF;

    -- 方式 B：api_config 中的 endpoint 改變時
    IF OLD.api_config IS NOT NULL AND OLD.api_config->>'endpoint' IS NOT NULL THEN
      old_endpoint_ids := ARRAY(
        SELECT DISTINCT unnest(
          COALESCE(old_endpoint_ids, '{}') || ARRAY[OLD.api_config->>'endpoint']
        )
      );
    END IF;

    IF NEW.api_config IS NOT NULL AND NEW.api_config->>'endpoint' IS NOT NULL THEN
      new_endpoint_ids := ARRAY(
        SELECT DISTINCT unnest(
          COALESCE(new_endpoint_ids, '{}') || ARRAY[NEW.api_config->>'endpoint']
        )
      );
    END IF;

    -- 合併所有受影響的 endpoints
    affected_endpoint_ids := ARRAY(
      SELECT DISTINCT unnest(COALESCE(old_endpoint_ids, '{}') || COALESCE(new_endpoint_ids, '{}'))
    );

  -- ========================================
  -- 處理 INSERT 操作
  -- ========================================
  ELSE
    -- 方式 A：通過 form_id 引用的 endpoints
    IF NEW.form_id IS NOT NULL THEN
      SELECT ARRAY_AGG(DISTINCT api_config->>'endpoint')
      INTO new_endpoint_ids
      FROM form_schemas
      WHERE form_id = NEW.form_id
        AND api_config->>'endpoint' IS NOT NULL;
    END IF;

    -- 方式 B：直接在 api_config 引用的 endpoint
    IF NEW.api_config IS NOT NULL AND NEW.api_config->>'endpoint' IS NOT NULL THEN
      new_endpoint_ids := ARRAY(
        SELECT DISTINCT unnest(
          COALESCE(new_endpoint_ids, '{}') || ARRAY[NEW.api_config->>'endpoint']
        )
      );
    END IF;

    affected_endpoint_ids := new_endpoint_ids;
  END IF;

  -- ========================================
  -- 更新所有受影響的 API 端點
  -- ========================================
  IF affected_endpoint_ids IS NOT NULL AND array_length(affected_endpoint_ids, 1) > 0 THEN
    FOR i IN 1..array_length(affected_endpoint_ids, 1) LOOP
      UPDATE api_endpoints
      SET related_kb_ids = (
        SELECT ARRAY_AGG(DISTINCT kb.id ORDER BY kb.id)
        FROM knowledge_base kb
        LEFT JOIN form_schemas fs ON kb.form_id = fs.form_id
        WHERE (
          -- 方式 A：通過 form_id 關聯
          (fs.api_config->>'endpoint' = affected_endpoint_ids[i])
          OR
          -- 方式 B：直接在 api_config 關聯
          (kb.api_config->>'endpoint' = affected_endpoint_ids[i])
        )
      )
      WHERE endpoint_id = affected_endpoint_ids[i];
    END LOOP;
  END IF;

  RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- 建立 Trigger
CREATE TRIGGER trigger_sync_api_endpoint_kb_ids
AFTER INSERT OR UPDATE OR DELETE ON knowledge_base
FOR EACH ROW
EXECUTE FUNCTION sync_api_endpoint_kb_ids();
```

### Trigger 工作原理

1. **偵測變更**: 監聽 knowledge_base 的 INSERT/UPDATE/DELETE
2. **雙路徑查詢**:
   - **方式 A**: 如果知識庫有 `form_id`,查詢 form_schemas 的 `api_config.endpoint`
   - **方式 B**: 如果知識庫有 `api_config.endpoint`,直接讀取
3. **合併端點**: 將方式 A 和方式 B 找到的所有受影響端點合併
4. **更新端點**: 重新計算 API 端點的 `related_kb_ids` 陣列（同時查詢方式 A 和 B）
5. **去重排序**: 使用 `ARRAY_AGG(DISTINCT ... ORDER BY)` 保證唯一性和順序

**關鍵改進（v2.0）**:
- ✅ 支援方式 B（直接 api_config 引用）
- ✅ 使用 `LEFT JOIN` 而非 `JOIN`,允許知識庫沒有 form_id
- ✅ `WHERE` 條件使用 `OR`,同時匹配兩種方式

### 一次性資料清理

```sql
-- 初次建立 Trigger 後,需要執行一次性資料清理（v2.0 修復版）
UPDATE api_endpoints
SET related_kb_ids = (
  SELECT ARRAY_AGG(DISTINCT kb.id ORDER BY kb.id)
  FROM knowledge_base kb
  LEFT JOIN form_schemas fs ON kb.form_id = fs.form_id
  WHERE (
    -- 方式 A：通過 form_id 關聯
    (fs.api_config->>'endpoint' = api_endpoints.endpoint_id)
    OR
    -- 方式 B：直接在 api_config 關聯
    (kb.api_config->>'endpoint' = api_endpoints.endpoint_id)
  )
)
WHERE endpoint_id LIKE 'lookup%';  -- 只更新 Lookup 相關的 endpoints
```

**執行結果範例**:
```
UPDATE 10
lookup endpoint: {1394, 1396, 1397, 1403, 1405, 1406, 1407, 1408} (8 筆)
lookup_generic endpoint: {1388, 1389, 1390, 1391, 1392, 1393} (6 筆)
```

---

## 後端 API

### API 1: 取得 Lookup 表單統計

**端點**: `GET /api/v1/lookup-forms/{form_id}/stats`

**文件位置**: `rag-orchestrator/routers/forms.py` (Line 148-238)

**功能**: 查詢 Lookup 表單的統計資訊,包含關聯的知識庫和使用的 API 端點。

**請求範例**:
```bash
curl "http://localhost:8100/api/v1/lookup-forms/parcel_service_form_v2/stats"
```

**回應範例**:
```json
{
  "form_id": "parcel_service_form_v2",
  "form_name": "包裹代收服務查詢",
  "category": "parcel_service",
  "endpoint": "lookup",
  "linked_kb_ids": [1397],
  "linked_kb_count": 1,
  "api_endpoint": {
    "endpoint_id": "lookup",
    "endpoint_name": "通用查詢 API",
    "related_kb_ids": [1394, 1396, 1397],
    "total_kb_using": 3
  }
}
```

**實作細節**:
```python
@router.get("/lookup-forms/{form_id}/stats")
async def get_lookup_form_stats(request: Request, form_id: str):
    """取得 Lookup 表單的統計資訊"""
    db_pool = request.app.state.db_pool

    async with db_pool.acquire() as conn:
        # 1. 取得表單基本資訊
        form_query = """
            SELECT
                fs.form_id,
                fs.form_name,
                fs.api_config->>'endpoint' as endpoint,
                fs.api_config->'static_params'->>'category' as category
            FROM form_schemas fs
            WHERE fs.form_id = $1
                AND fs.api_config->>'endpoint' IN ('lookup', 'lookup_generic')
        """
        form_row = await conn.fetchrow(form_query, form_id)

        # 2. 取得關聯的知識庫 IDs
        kb_query = """
            SELECT ARRAY_AGG(id ORDER BY id) as kb_ids
            FROM knowledge_base
            WHERE form_id = $1
        """
        kb_row = await conn.fetchrow(kb_query, form_id)
        linked_kb_ids = kb_row['kb_ids'] if kb_row and kb_row['kb_ids'] else []

        # 3. 取得 API 端點資訊
        endpoint_id = form_row['endpoint']
        endpoint_query = """
            SELECT
                ae.endpoint_id,
                ae.endpoint_name,
                ae.related_kb_ids,
                array_length(ae.related_kb_ids, 1) as total_kb_using
            FROM api_endpoints ae
            WHERE ae.endpoint_id = $1
        """
        endpoint_row = await conn.fetchrow(endpoint_query, endpoint_id)

        # 組合回應
        result = {
            "form_id": form_row['form_id'],
            "form_name": form_row['form_name'],
            "category": form_row['category'],
            "endpoint": form_row['endpoint'],
            "linked_kb_ids": linked_kb_ids,
            "linked_kb_count": len(linked_kb_ids),
            "api_endpoint": {
                "endpoint_id": endpoint_row['endpoint_id'] if endpoint_row else None,
                "endpoint_name": endpoint_row['endpoint_name'] if endpoint_row else None,
                "related_kb_ids": endpoint_row['related_kb_ids'] if endpoint_row else [],
                "total_kb_using": endpoint_row['total_kb_using'] if endpoint_row else 0
            }
        }

        return result
```

### API 2: 取得 API 端點關聯的表單

**端點**: `GET /api/v1/api-endpoints/{endpoint_id}/related-forms`

**文件位置**: `rag-orchestrator/routers/api_endpoints.py` (Line 211-269)

**功能**: 查詢某個 API 端點關聯的所有 Lookup 表單及知識庫。

**請求範例**:
```bash
curl "http://localhost:8100/api/v1/api-endpoints/lookup/related-forms"
```

**回應範例**:
```json
{
  "endpoint_id": "lookup",
  "endpoint_name": "通用查詢 API",
  "related_forms_count": 3,
  "related_forms": [
    {
      "form_id": "parking_fee_form_v2",
      "form_name": "停車費資訊查詢",
      "category": "parking_fee",
      "kb_id": 1394,
      "kb_question": "停車費金額和繳費方式查詢"
    },
    {
      "form_id": "community_facilities_form_v2",
      "form_name": "公共設施查詢",
      "category": "community_facilities",
      "kb_id": 1396,
      "kb_question": "社區公共設施有哪些"
    },
    {
      "form_id": "parcel_service_form_v2",
      "form_name": "包裹代收服務查詢",
      "category": "parcel_service",
      "kb_id": 1397,
      "kb_question": "包裹代收服務說明"
    }
  ]
}
```

---

## 前端顯示

### LookupFormManagement.vue 組件

**文件位置**: `knowledge-admin/frontend/src/views/LookupFormManagement.vue`

**新增功能**:
1. 表格新增「關聯知識」欄位
2. 新增「📊 統計」按鈕
3. 統計 Modal 顯示表單統計資訊

#### 1. 表格欄位

```vue
<template>
  <table class="form-table">
    <thead>
      <tr>
        <th>表單 ID</th>
        <th>表單名稱</th>
        <th>Lookup 類別</th>
        <th>API 端點</th>
        <th width="100">關聯知識</th>  <!-- ⭐ 新增 -->
        <th>操作</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="form in existingForms" :key="form.form_id">
        <!-- ... 其他欄位 ... -->

        <!-- ⭐ 關聯知識數量 -->
        <td class="center">
          <span class="kb-count" :class="{ 'has-kb': form.stats?.linked_kb_count > 0 }">
            {{ form.stats?.linked_kb_count || 0 }} 筆
          </span>
        </td>

        <td class="actions">
          <!-- ⭐ 統計按鈕 -->
          <button @click="viewStats(form)" class="btn-sm btn-info" title="查看統計">
            📊
          </button>
          <!-- ... 其他按鈕 ... -->
        </td>
      </tr>
    </tbody>
  </table>
</template>
```

#### 2. 載入統計資料

```javascript
async loadFormsStats() {
  // 為每個表單載入統計資料
  const statsPromises = this.existingForms.map(async (form) => {
    try {
      const response = await axios.get(
        `${RAG_API}/v1/lookup-forms/${form.form_id}/stats`
      );
      form.stats = response.data;
    } catch (error) {
      console.error(`載入表單 ${form.form_id} 統計失敗:`, error);
      form.stats = { linked_kb_count: 0 };
    }
  });

  await Promise.all(statsPromises);
}
```

#### 3. 統計 Modal

```vue
<div v-if="viewingStats" class="modal-overlay" @click="viewingStats = null">
  <div class="modal-content stats-modal" @click.stop>
    <div class="modal-header">
      <h3>📊 Lookup 表單統計</h3>
      <button @click="viewingStats = null" class="btn-close">✕</button>
    </div>

    <div class="modal-body">
      <!-- 表單基本資訊 -->
      <div class="stats-section">
        <h4>📋 表單資訊</h4>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">表單 ID：</span>
            <code>{{ viewingStats.form_id }}</code>
          </div>
          <div class="info-item">
            <span class="info-label">表單名稱：</span>
            <span>{{ viewingStats.form_name }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Lookup 類別：</span>
            <code>{{ viewingStats.category }}</code>
          </div>
        </div>
      </div>

      <!-- API 端點資訊 -->
      <h4 style="margin-top: 20px;">📡 使用的 API 端點</h4>
      <div class="api-endpoint-info">
        <div class="info-row">
          <span class="info-label">端點 ID：</span>
          <code>{{ viewingStats.api_endpoint?.endpoint_id }}</code>
        </div>
        <div class="info-row">
          <span class="info-label">端點名稱：</span>
          <span>{{ viewingStats.api_endpoint?.endpoint_name }}</span>
        </div>
      </div>

      <!-- 關聯的知識庫 -->
      <h4 style="margin-top: 20px;">
        🔗 關聯的知識庫 ({{ viewingStats.linked_kb_count }} 筆)
      </h4>
      <div v-if="viewingStats.linked_kb_ids && viewingStats.linked_kb_ids.length > 0"
           class="kb-list">
        <div v-for="kbId in viewingStats.linked_kb_ids" :key="kbId" class="kb-item">
          <span class="kb-id">KB #{{ kbId }}</span>
          <a :href="`/knowledge?id=${kbId}`" target="_blank" class="btn-sm btn-link">
            查看
          </a>
        </div>
      </div>
      <div v-else class="no-data">
        目前沒有知識庫使用此表單
      </div>
    </div>
  </div>
</div>
```

#### 4. CSS 樣式

```css
.kb-count {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  background: #f0f0f0;
  color: #666;
  font-size: 0.9em;
}

.kb-count.has-kb {
  background: #e3f2fd;
  color: #1976d2;
  font-weight: 500;
}

.kb-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.kb-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f5f5f5;
  border-radius: 4px;
}

.kb-id {
  font-family: monospace;
  font-weight: 500;
  color: #1976d2;
}
```

### ApiEndpointsView.vue 組件（v2.0 更新）

**文件位置**: `knowledge-admin/frontend/src/views/ApiEndpointsView.vue`

**重要修改**: `related_kb_ids` 欄位改為**唯讀顯示**

#### 唯讀欄位設計

```vue
<div class="form-group">
  <label>🔒 關聯的知識庫 ID <small>(由系統自動維護)</small></label>
  <div style="padding: 10px; background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; color: #666;">
    <span v-if="formData.related_kb_ids && formData.related_kb_ids.length > 0">
      {{ formData.related_kb_ids.join(', ') }}
      <small style="margin-left: 10px;">(共 {{ formData.related_kb_ids.length }} 筆)</small>
    </span>
    <span v-else style="font-style: italic;">
      尚無關聯知識庫
    </span>
    <div style="margin-top: 5px; font-size: 12px; color: #999;">
      ℹ️ 當知識庫設定 form_id 或 api_config 引用此 endpoint 時，系統會自動更新此欄位
    </div>
  </div>
</div>
```

**關鍵設計點**:
1. 🔒 圖示表示唯讀
2. 灰色背景視覺提示這是系統欄位
3. 顯示知識庫 ID 列表和數量
4. 說明文字解釋自動更新機制（**包含兩種引用方式**）

#### 保存邏輯修改

```javascript
async saveEndpoint() {
  this.saving = true;

  try {
    // related_kb_ids 由系統自動維護，從 payload 中移除以避免覆蓋
    const payload = {
      ...this.formData
    };
    delete payload.related_kb_ids;  // 確保不發送此欄位給後端

    if (this.editingItem) {
      await axios.put(`${RAG_API}/api-endpoints/${this.editingItem.endpoint_id}`, payload);
      alert('✅ API Endpoint 已更新！');
    } else {
      await axios.post(`${RAG_API}/api-endpoints`, payload);
      alert('✅ API Endpoint 已新增！');
    }

    this.closeModal();
    this.loadEndpoints();
  } catch (error) {
    console.error('儲存失敗', error);
    alert('儲存失敗：' + (error.response?.data?.detail || error.message));
  } finally {
    this.saving = false;
  }
}
```

**關鍵改變**:
- ❌ 移除 `relatedKbIdsInput` 變數（不再需要）
- ❌ 移除手動輸入轉換邏輯
- ✅ `delete payload.related_kb_ids` 確保不發送給後端
- ✅ 前端只顯示，不修改

---

## 使用指南

### 情境 1: 建立新的 Lookup 表單和知識庫

**步驟**:

1. **建立 Lookup 表單** (`/lookup-forms`)
   - 建立表單,例如: `parcel_service_form_v2`
   - 設定 API 端點為 `lookup`
   - **不需要**設定知識庫關聯

2. **建立知識庫** (`/knowledge`)
   - 建立新知識,例如: "包裹代收服務說明"
   - 在「動作設定」選擇 `form_id = 'parcel_service_form_v2'`
   - 儲存

3. **自動同步**
   - Trigger 自動偵測到新知識庫
   - 查詢表單的 `api_config.endpoint` = `lookup`
   - 自動將知識庫 ID 加入 `api_endpoints.related_kb_ids`

4. **查看結果** (`/lookup-forms`)
   - 回到 Lookup 表單管理頁面
   - 點擊「📊」按鈕查看統計
   - 可看到「關聯的知識庫」包含新建立的知識

### 情境 2: 修改知識庫的表單關聯

**步驟**:

1. **編輯知識庫** (`/knowledge`)
   - 找到現有知識,例如: KB #1397
   - 將 `form_id` 從 `parcel_service_form_v2` 改為 `parking_fee_form_v2`
   - 儲存

2. **自動同步**
   - Trigger 偵測到 UPDATE 操作
   - 同時更新舊表單和新表單的 API 端點
   - `lookup` 端點的 `related_kb_ids` 自動更新

3. **驗證結果**
   ```sql
   -- 查詢 API 端點的關聯知識庫
   SELECT endpoint_id, related_kb_ids
   FROM api_endpoints
   WHERE endpoint_id = 'lookup';
   ```

### 情境 3: 刪除知識庫

**步驟**:

1. **刪除知識庫** (`/knowledge`)
   - 刪除知識,例如: KB #1397

2. **自動同步**
   - Trigger 偵測到 DELETE 操作
   - 從 `api_endpoints.related_kb_ids` 移除該 ID
   - 更新 `lookup` 端點的關聯陣列

3. **驗證結果**
   - 在 `/lookup-forms` 查看統計
   - 「關聯知識」數量自動減少

### 情境 4: 建立直接使用 API 的知識庫（方式 B）

**步驟**:

1. **建立知識庫** (`/knowledge`)
   - 建立新知識,例如: "客服專線電話"
   - **不設定 form_id**（留空）
   - 在「動作設定」選擇 `action_type = 'api_call'`
   - 在 `api_config` 欄位設定:
     ```json
     {
       "endpoint": "lookup",
       "static_params": {
         "key": "客服專線",
         "category": "customer_service"
       }
     }
     ```
   - 儲存

2. **自動同步**
   - Trigger 偵測到新知識庫有 `api_config.endpoint = 'lookup'`
   - 自動將知識庫 ID 加入 `api_endpoints.related_kb_ids`
   - **不需要表單**,直接引用 API

3. **驗證結果** (`/api-endpoints`)
   - 訪問 API 端點管理頁面
   - 編輯 `lookup` endpoint
   - 查看「🔒 關聯的知識庫 ID」欄位
   - 可看到新建立的知識庫 ID 已自動加入

**適用場景**:
- 簡單查詢,不需要用戶填寫表單
- 使用固定參數的 API 調用
- 避免建立只用一次的表單

---

## 測試驗證

### 測試 1: Trigger INSERT 操作

```sql
-- 1. 查詢當前狀態
SELECT endpoint_id, related_kb_ids
FROM api_endpoints
WHERE endpoint_id = 'lookup';
-- 假設結果: {1394, 1396, 1397}

-- 2. 插入新知識庫
INSERT INTO knowledge_base (
    question_summary,
    answer,
    form_id,
    action_type
) VALUES (
    '測試問題',
    '測試答案',
    'parcel_service_form_v2',
    'form_then_api'
);
-- 假設新 ID = 1398

-- 3. 驗證 Trigger 已更新
SELECT endpoint_id, related_kb_ids
FROM api_endpoints
WHERE endpoint_id = 'lookup';
-- 預期結果: {1394, 1396, 1397, 1398}
```

### 測試 2: Trigger UPDATE 操作

```sql
-- 1. 更新知識庫的 form_id
UPDATE knowledge_base
SET form_id = 'parking_fee_form_v2'
WHERE id = 1397;

-- 2. 驗證兩個端點都更新了
SELECT endpoint_id, related_kb_ids
FROM api_endpoints
WHERE endpoint_id IN ('lookup', 'lookup_generic');

-- 預期:
-- lookup: 不再包含 1397
-- lookup_generic: 可能包含 1397 (如果 parking_fee_form_v2 使用此端點)
```

### 測試 3: Trigger DELETE 操作

```sql
-- 1. 刪除知識庫
DELETE FROM knowledge_base WHERE id = 1398;

-- 2. 驗證已從陣列移除
SELECT endpoint_id, related_kb_ids
FROM api_endpoints
WHERE endpoint_id = 'lookup';
-- 預期: 不包含 1398
```

### 測試 4: 前端 API 測試

```bash
# 測試表單統計 API
curl "http://localhost:8100/api/v1/lookup-forms/parcel_service_form_v2/stats" | jq

# 測試 API 端點關聯 API
curl "http://localhost:8100/api/v1/api-endpoints/lookup/related-forms" | jq
```

### 測試 5: 前端 UI 測試

1. 訪問 `http://localhost:8087/lookup-forms`
2. 檢查「關聯知識」欄位顯示正確數量
3. 點擊「📊」按鈕查看統計
4. 驗證統計 Modal 顯示正確資料

---

## 常見問題

### Q1: 為什麼不在 Lookup 表單頁面設定知識庫關聯?

**A**: 設計理念是「知識庫驅動」,而非「表單驅動」。

- ✅ **正確流程**: 知識庫 → 選擇表單 → 系統自動維護關聯
- ❌ **錯誤流程**: 表單 → 選擇知識庫 → 手動維護關聯

**原因**:
1. 知識庫是核心,表單只是執行工具
2. 一個知識可能關聯多種動作 (表單、API、純展示)
3. 避免雙向維護導致資料不一致

### Q2: 為什麼不在 API 端點頁面設定知識庫關聯?

**A**: API 端點是底層技術配置,關聯關係應由知識庫定義,不應反向維護。

**設計原因**:
1. **單向資料流**: 知識庫 → API 端點（而非雙向）
2. **自動追蹤**: Trigger 自動偵測兩種引用方式（form_id 和 api_config）
3. **避免衝突**: 手動設定會被 Trigger 覆蓋,失去意義
4. **統計用途**: `related_kb_ids` 是**唯讀統計資料**,用於查看使用情況

**前端實作（v2.0）**:
- ✅ 改為唯讀顯示（灰色背景 + 🔒 圖示）
- ✅ 說明文字：「由系統自動維護」
- ✅ 保存時 `delete payload.related_kb_ids`,不發送給後端
- ✅ 顯示知識庫數量和列表

### Q3: related_kb_ids 會不會不準確?

**A**: 不會,因為使用 Trigger 機制保證即時同步。

- INSERT/UPDATE/DELETE 操作都會觸發 Trigger
- Trigger 重新計算所有相關知識庫,保證一致性
- 使用 `ARRAY_AGG(DISTINCT ... ORDER BY)` 去重和排序

### Q4: 如果表單的 api_config.endpoint 改變了怎麼辦?

**A**: 目前需要手動處理,未來可擴充 Trigger。

**臨時解決方案**:
```sql
-- 重新同步所有 API 端點
UPDATE api_endpoints ae
SET related_kb_ids = (
  SELECT ARRAY_AGG(DISTINCT kb.id ORDER BY kb.id)
  FROM knowledge_base kb
  JOIN form_schemas fs ON kb.form_id = fs.form_id
  WHERE fs.api_config->>'endpoint' = ae.endpoint_id
);
```

**未來改進**: 為 `form_schemas` 表也建立 Trigger,監聽 `api_config` 變更。

### Q5: 效能會不會有問題?

**A**: 不會,原因:

1. Trigger 只在知識庫變更時執行,頻率不高
2. 使用索引優化查詢 (`GIN` 索引)
3. 只更新受影響的 API 端點,不是全表更新
4. 陣列操作在 PostgreSQL 中效能很好

**效能監控**:
```sql
-- 查看最大的 related_kb_ids 陣列
SELECT endpoint_id, array_length(related_kb_ids, 1) as kb_count
FROM api_endpoints
ORDER BY kb_count DESC
LIMIT 10;
```

### Q6: lookup 和 lookup_generic 有什麼區別?

**A**: 兩個不同的 API 端點,使用不同的查詢邏輯。

- **lookup**: 通用查詢 API,使用 `category` 參數
- **lookup_generic**: 地址型查詢 API,使用複合鍵查詢

兩者都會被 Trigger 自動維護 `related_kb_ids`。

---

## 相關文檔

- [Lookup Table System 設計](./LOOKUP_TABLE_SYSTEM_DESIGN.md)
- [Lookup 重構完成總結](./LOOKUP_REFACTORING_COMPLETE_SUMMARY.md)
- [資料庫架構文檔](../../architecture/DATABASE_SCHEMA.md)
- [API 端點完整清單](../../API_ENDPOINTS_COMPLETE_INVENTORY.md)

---

## 版本歷史

| 版本 | 日期 | 變更內容 | 作者 |
|-----|------|---------|------|
| 1.0 | 2026-03-13 | 初始版本,記錄自動同步機制（僅支援方式 A） | Claude Code |
| 2.0 | 2026-03-13 | 修復 Trigger 支援雙引用方式（方式 A + 方式 B）<br>前端 UI 改為唯讀顯示<br>完整文件更新 | Claude Code |

**主要改進（v2.0）**:
- ✅ 修復 Trigger,支援直接在 `api_config` 引用 endpoint
- ✅ 修復數據不完整問題（`lookup` endpoint 從 3 個知識庫更新為 8 個）
- ✅ 前端 `related_kb_ids` 欄位改為唯讀顯示
- ✅ 移除前端手動輸入邏輯,避免覆蓋 Trigger 自動維護的數據
- ✅ 完整文件說明兩種引用方式和使用場景

---

**文檔狀態**: ✅ 已完成並測試（v2.0）
**最後更新**: 2026-03-13
**負責人**: Claude Code
