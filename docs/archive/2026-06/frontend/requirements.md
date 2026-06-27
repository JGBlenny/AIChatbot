# 前端修改需求規格

**日期**: 2026-01-18
**版本**: v1.1.0
**相關**: Knowledge Action System - 方式 2 自動格式化

---

## ⚠️ 重要說明

**目前狀態**: ❌ 前端尚未修改
**影響範圍**: 知識庫管理後台（knowledge-admin/frontend）
**優先級**: 🔴 高（管理員無法配置新功能）

---

## 📋 修改總覽

### 需要修改的前端頁面

| 頁面 | 文件路徑 | 需要添加的欄位 | 優先級 |
|------|---------|---------------|--------|
| **知識庫管理** | `knowledge-admin/frontend/src/views/KnowledgeView.vue` | `action_type`, `api_config` | 🔴 高 |
| **表單管理** | `knowledge-admin/frontend/src/views/FormManagementView.vue` | `on_complete_action`, `api_config` | 🔴 高 |
| **表單編輯器** | `knowledge-admin/frontend/src/views/FormEditorView.vue` | `on_complete_action`, `api_config` | 🔴 高 |

---

## 📂 詳細修改需求

---

## 1️⃣ 知識庫管理頁面（KnowledgeView.vue）

### 📍 修改位置

**文件**: `knowledge-admin/frontend/src/views/KnowledgeView.vue`

### 當前欄位（已有）

```javascript
formData: {
  question_summary: '',
  answer: '',
  keywords: [],
  scope: 'customized',
  vendor_id: null,
  form_id: '',  // ✅ 已有
  // ...其他欄位
}
```

### 需要添加的欄位

```javascript
formData: {
  // ... 現有欄位
  action_type: 'direct_answer',  // ⭐ 新增
  api_config: null,               // ⭐ 新增
}
```

---

### UI 設計規格

#### A. 表單欄位：action_type（動作類型）

**位置**: 放在「關聯表單」欄位之前

**UI 元件**: `<select>` 下拉選單

**選項**:
```html
<div class="form-group">
  <label>
    動作類型 <span class="required">*</span>
    <span class="info-icon" title="決定知識的執行行為">ℹ️</span>
  </label>
  <select v-model="formData.action_type" required class="form-select">
    <option value="direct_answer">📝 純知識問答</option>
    <option value="form_fill">📋 表單 + 知識答案</option>
    <option value="api_call">🔌 API 調用 + 知識答案</option>
    <option value="form_then_api">📋🔌 表單 → API → 知識</option>
  </select>

  <!-- 提示說明 -->
  <p class="hint-text" v-if="formData.action_type === 'direct_answer'">
    💡 只返回知識答案，不觸發表單或 API
  </p>
  <p class="hint-text" v-if="formData.action_type === 'form_fill'">
    ✅ 先收集用戶資料（表單），再顯示知識答案
  </p>
  <p class="hint-text" v-if="formData.action_type === 'api_call'">
    🔌 直接調用 API 查詢數據，合併知識答案（適合已登入用戶）
  </p>
  <p class="hint-text" v-if="formData.action_type === 'form_then_api'">
    📝 先填表單 → 調用 API → 顯示結果（適合需要驗證身份或收集參數）
  </p>
</div>
```

**邏輯控制**:
```javascript
computed: {
  // 根據 action_type 顯示/隱藏相關欄位
  showFormField() {
    return ['form_fill', 'form_then_api'].includes(this.formData.action_type);
  },
  showApiConfig() {
    return ['api_call', 'form_then_api'].includes(this.formData.action_type);
  }
}
```

---

#### B. 表單欄位：api_config（API 配置）

**位置**: 放在「關聯表單」欄位之後

**UI 元件**: 條件顯示的 JSON 編輯器或自訂表單

**方式 1：簡易模式（推薦初期使用）**

```html
<div class="form-group" v-if="showApiConfig">
  <label>
    API 配置
    <span class="info-icon" title="配置 API 調用參數">ℹ️</span>
  </label>

  <!-- API endpoint 選擇 -->
  <div class="config-row">
    <label class="sub-label">API Endpoint:</label>
    <select v-model="apiConfigData.endpoint" class="form-select">
      <option value="">請選擇...</option>
      <option value="billing_inquiry">帳單查詢</option>
      <option value="verify_tenant_identity">租客身份驗證</option>
      <option value="resend_invoice">重新發送帳單</option>
      <option value="maintenance_request">報修申請</option>
    </select>
  </div>

  <!-- 參數配置 -->
  <div class="config-row" v-if="apiConfigData.endpoint">
    <label class="sub-label">參數配置:</label>
    <div class="param-builder">
      <div v-for="(param, index) in apiConfigData.params" :key="index" class="param-row">
        <input
          v-model="param.key"
          placeholder="參數名（如: user_id）"
          class="param-key"
        />
        <input
          v-model="param.value"
          placeholder="值（如: {session.user_id}）"
          class="param-value"
        />
        <button @click="removeParam(index)" class="btn-sm btn-delete">✕</button>
      </div>
      <button @click="addParam" class="btn-sm btn-secondary">＋ 添加參數</button>
    </div>
  </div>

  <!-- 回應配置 -->
  <div class="config-row">
    <label class="sub-label">
      <input type="checkbox" v-model="apiConfigData.combine_with_knowledge" />
      合併知識答案
    </label>
    <p class="hint-text">✅ 勾選後，API 結果會與知識答案一起顯示</p>
  </div>

  <!-- 降級訊息 -->
  <div class="config-row">
    <label class="sub-label">API 失敗時的降級訊息:</label>
    <textarea
      v-model="apiConfigData.fallback_message"
      placeholder="⚠️ 目前無法查詢，請稍後再試。"
      rows="3"
    ></textarea>
  </div>

  <!-- JSON 預覽 -->
  <details class="json-preview">
    <summary>查看 JSON 配置 🔍</summary>
    <pre>{{ JSON.stringify(apiConfigJSON, null, 2) }}</pre>
  </details>
</div>
```

**方式 2：進階模式（JSON 編輯器）**

```html
<div class="form-group" v-if="showApiConfig">
  <label>
    API 配置（JSON 格式）
    <span class="info-icon" title="進階配置，請參考文檔">ℹ️</span>
  </label>

  <!-- 切換模式 -->
  <div class="mode-switch">
    <button
      @click="apiConfigMode = 'simple'"
      :class="{ active: apiConfigMode === 'simple' }"
      class="btn-sm"
    >
      簡易模式
    </button>
    <button
      @click="apiConfigMode = 'advanced'"
      :class="{ active: apiConfigMode === 'advanced' }"
      class="btn-sm"
    >
      進階模式（JSON）
    </button>
  </div>

  <!-- JSON 編輯器 -->
  <div v-if="apiConfigMode === 'advanced'">
    <textarea
      v-model="apiConfigJSON"
      @blur="validateJSON"
      rows="12"
      class="json-editor"
      placeholder='{
  "endpoint": "billing_inquiry",
  "params": {
    "user_id": "{session.user_id}"
  },
  "combine_with_knowledge": true
}'
    ></textarea>
    <p v-if="jsonError" class="error-text">❌ {{ jsonError }}</p>
    <p v-else class="success-text">✅ JSON 格式正確</p>
  </div>

  <!-- 範例連結 -->
  <a href="/docs/api-config-examples" target="_blank" class="help-link">
    📚 查看配置範例
  </a>
</div>
```

**數據結構**:
```javascript
data() {
  return {
    // ... 現有數據
    apiConfigMode: 'simple',  // 'simple' | 'advanced'
    apiConfigData: {
      endpoint: '',
      params: [],  // [{ key: 'user_id', value: '{session.user_id}' }]
      combine_with_knowledge: true,
      fallback_message: ''
    },
    apiConfigJSON: '',
    jsonError: null
  }
},

computed: {
  // 將簡易模式的數據轉換為 JSON
  apiConfigJSON() {
    if (this.apiConfigMode === 'simple') {
      const params = {};
      this.apiConfigData.params.forEach(p => {
        if (p.key) params[p.key] = p.value;
      });

      return JSON.stringify({
        endpoint: this.apiConfigData.endpoint,
        params: params,
        combine_with_knowledge: this.apiConfigData.combine_with_knowledge,
        fallback_message: this.apiConfigData.fallback_message || undefined
      }, null, 2);
    }
    return this.apiConfigJSON;
  }
},

methods: {
  addParam() {
    this.apiConfigData.params.push({ key: '', value: '' });
  },

  removeParam(index) {
    this.apiConfigData.params.splice(index, 1);
  },

  validateJSON() {
    try {
      JSON.parse(this.apiConfigJSON);
      this.jsonError = null;
    } catch (e) {
      this.jsonError = 'JSON 格式錯誤：' + e.message;
    }
  }
}
```

---

#### C. 欄位顯示邏輯

```html
<!-- 關聯表單欄位：只在特定 action_type 時顯示 -->
<div class="form-group" v-if="showFormField">
  <label>關聯表單</label>
  <select v-model="formData.form_id" class="form-select">
    <option value="">不關聯表單</option>
    <option v-for="form in availableForms" :key="form.form_id" :value="form.form_id">
      {{ form.form_name }} ({{ form.form_id }})
    </option>
  </select>
</div>

<!-- API 配置：只在特定 action_type 時顯示 -->
<div v-if="showApiConfig">
  <!-- API 配置 UI（如上） -->
</div>
```

---

#### D. 列表顯示優化

在知識列表中添加 action_type 欄位顯示：

```html
<table>
  <thead>
    <tr>
      <th width="60">ID</th>
      <th>問題摘要</th>
      <th width="100">動作類型</th>  <!-- ⭐ 新增 -->
      <th width="120">意圖</th>
      <!-- ... 其他欄位 -->
    </tr>
  </thead>
  <tbody>
    <tr v-for="item in knowledgeList" :key="item.id">
      <td>{{ item.id }}</td>
      <td>{{ item.question_summary }}</td>
      <td>  <!-- ⭐ 新增 -->
        <span class="badge" :class="'action-' + item.action_type">
          {{ getActionTypeLabel(item.action_type) }}
        </span>
      </td>
      <!-- ... 其他欄位 -->
    </tr>
  </tbody>
</table>
```

**輔助方法**:
```javascript
methods: {
  getActionTypeLabel(type) {
    const labels = {
      'direct_answer': '📝 知識',
      'form_fill': '📋 表單',
      'api_call': '🔌 API',
      'form_then_api': '📋🔌 表單+API'
    };
    return labels[type] || type;
  }
}
```

**CSS 樣式**:
```css
.badge.action-direct_answer { background: #67c23a; }
.badge.action-form_fill { background: #409eff; }
.badge.action-api_call { background: #e6a23c; }
.badge.action-form_then_api { background: #f56c6c; }
```

---

#### E. 保存邏輯修改

```javascript
async saveKnowledge() {
  // 組裝 API 配置
  let apiConfig = null;
  if (this.showApiConfig) {
    if (this.apiConfigMode === 'simple') {
      // 從簡易模式組裝
      const params = {};
      this.apiConfigData.params.forEach(p => {
        if (p.key) params[p.key] = p.value;
      });

      apiConfig = {
        endpoint: this.apiConfigData.endpoint,
        params: params,
        combine_with_knowledge: this.apiConfigData.combine_with_knowledge
      };

      if (this.apiConfigData.fallback_message) {
        apiConfig.fallback_message = this.apiConfigData.fallback_message;
      }
    } else {
      // 從 JSON 解析
      try {
        apiConfig = JSON.parse(this.apiConfigJSON);
      } catch (e) {
        this.$message.error('API 配置 JSON 格式錯誤');
        return;
      }
    }
  }

  // 準備提交數據
  const payload = {
    question_summary: this.formData.question_summary,
    answer: this.formData.answer,
    action_type: this.formData.action_type,  // ⭐ 新增
    api_config: apiConfig,                   // ⭐ 新增
    form_id: this.showFormField ? this.formData.form_id : null,
    // ... 其他欄位
  };

  // 提交到後端
  const response = await fetch(`${API_BASE}/knowledge/${this.editingItem?.id || ''}`, {
    method: this.editingItem ? 'PUT' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  // ...
}
```

---

## 2️⃣ 表單管理頁面（FormManagementView.vue）

### 📍 修改位置

**文件**: `knowledge-admin/frontend/src/views/FormManagementView.vue`

### 列表顯示優化

在表單列表中添加 `on_complete_action` 欄位：

```html
<table>
  <thead>
    <tr>
      <th width="150">表單ID</th>
      <th>表單名稱</th>
      <th width="120">完成後動作</th>  <!-- ⭐ 新增 -->
      <th width="80">欄位數</th>
      <!-- ... 其他欄位 -->
    </tr>
  </thead>
  <tbody>
    <tr v-for="form in formList" :key="form.form_id">
      <td><code>{{ form.form_id }}</code></td>
      <td><strong>{{ form.form_name }}</strong></td>
      <td>  <!-- ⭐ 新增 -->
        <span class="badge" :class="'complete-' + form.on_complete_action">
          {{ getCompleteActionLabel(form.on_complete_action) }}
        </span>
      </td>
      <!-- ... 其他欄位 -->
    </tr>
  </tbody>
</table>
```

**輔助方法**:
```javascript
methods: {
  getCompleteActionLabel(action) {
    const labels = {
      'show_knowledge': '📝 顯示知識',
      'call_api': '🔌 調用 API',
      'both': '📝🔌 兩者都執行'
    };
    return labels[action] || '📝 顯示知識';
  }
}
```

---

## 3️⃣ 表單編輯器頁面（FormEditorView.vue）

### 📍 修改位置

**文件**: `knowledge-admin/frontend/src/views/FormEditorView.vue`

### 需要添加的欄位

```javascript
data() {
  return {
    formData: {
      form_id: '',
      form_name: '',
      description: '',
      fields: [],
      on_complete_action: 'show_knowledge',  // ⭐ 新增
      api_config: null,                      // ⭐ 新增
      vendor_id: null,
      is_active: true
    },
    // ... API 配置相關數據（同 KnowledgeView）
  }
}
```

### UI 設計規格

#### A. 表單欄位：on_complete_action

**位置**: 放在表單基本資訊區塊

```html
<div class="form-section">
  <h3>表單完成後動作</h3>

  <div class="form-group">
    <label>
      完成後執行 <span class="required">*</span>
      <span class="info-icon" title="決定表單完成後的行為">ℹ️</span>
    </label>
    <select v-model="formData.on_complete_action" required class="form-select">
      <option value="show_knowledge">📝 只顯示知識答案</option>
      <option value="call_api">🔌 只調用 API</option>
      <option value="both">📝🔌 兩者都執行</option>
    </select>

    <!-- 提示說明 -->
    <p class="hint-text" v-if="formData.on_complete_action === 'show_knowledge'">
      💡 表單完成後，顯示關聯知識的答案
    </p>
    <p class="hint-text" v-if="formData.on_complete_action === 'call_api'">
      🔌 表單完成後，調用 API 並顯示結果（不顯示知識答案）
    </p>
    <p class="hint-text" v-if="formData.on_complete_action === 'both'">
      ✅ 表單完成後，先調用 API，再顯示知識答案
    </p>
  </div>
</div>
```

#### B. API 配置區塊

```html
<div class="form-section" v-if="formData.on_complete_action !== 'show_knowledge'">
  <h3>API 配置</h3>

  <!-- 複用 KnowledgeView 的 API 配置 UI -->
  <!-- 同上面的 API 配置設計 -->

  <!-- 額外的表單參數映射 -->
  <div class="form-group">
    <label>表單參數映射</label>
    <p class="hint-text">將表單欄位映射到 API 參數</p>

    <div class="param-mapping">
      <div v-for="(mapping, index) in formParamMappings" :key="index" class="mapping-row">
        <select v-model="mapping.apiParam" class="form-select" placeholder="API 參數名">
          <option value="">選擇 API 參數...</option>
          <option value="user_id">user_id</option>
          <option value="tenant_id">tenant_id</option>
          <option value="location">location</option>
          <option value="description">description</option>
        </select>
        <span>←</span>
        <select v-model="mapping.formField" class="form-select">
          <option value="">選擇表單欄位...</option>
          <option v-for="field in formData.fields" :key="field.field_name" :value="field.field_name">
            {{ field.field_label }} ({{ field.field_name }})
          </option>
        </select>
        <button @click="removeMapping(index)" class="btn-sm btn-delete">✕</button>
      </div>
      <button @click="addMapping" class="btn-sm btn-secondary">＋ 添加映射</button>
    </div>
  </div>
</div>
```

**數據結構**:
```javascript
data() {
  return {
    formData: {
      // ... 現有欄位
      on_complete_action: 'show_knowledge',
      api_config: null
    },
    formParamMappings: [
      // { apiParam: 'user_id', formField: 'tenant_id' }
    ]
  }
},

methods: {
  addMapping() {
    this.formParamMappings.push({ apiParam: '', formField: '' });
  },

  removeMapping(index) {
    this.formParamMappings.splice(index, 1);
  },

  buildApiConfig() {
    // 組裝 API 配置
    const params_from_form = {};
    this.formParamMappings.forEach(m => {
      if (m.apiParam && m.formField) {
        params_from_form[m.apiParam] = m.formField;
      }
    });

    return {
      endpoint: this.apiConfigData.endpoint,
      params_from_form: params_from_form,
      combine_with_knowledge: this.apiConfigData.combine_with_knowledge,
      fallback_message: this.apiConfigData.fallback_message
    };
  }
}
```

---

## 🎨 UI/UX 設計規範

### 顏色規範

```css
/* action_type 標籤 */
.badge.action-direct_answer {
  background: #67c23a;
  color: white;
}

.badge.action-form_fill {
  background: #409eff;
  color: white;
}

.badge.action-api_call {
  background: #e6a23c;
  color: white;
}

.badge.action-form_then_api {
  background: #f56c6c;
  color: white;
}

/* on_complete_action 標籤 */
.badge.complete-show_knowledge {
  background: #67c23a;
  color: white;
}

.badge.complete-call_api {
  background: #e6a23c;
  color: white;
}

.badge.complete-both {
  background: #f56c6c;
  color: white;
}

/* API 配置區塊 */
.config-row {
  margin-bottom: 15px;
}

.param-builder, .param-mapping {
  border: 1px solid #dcdfe6;
  padding: 15px;
  border-radius: 4px;
  background: #f5f7fa;
}

.param-row, .mapping-row {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
  align-items: center;
}

.param-key, .param-value {
  flex: 1;
  padding: 8px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}

.json-editor {
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 13px;
  background: #2d2d2d;
  color: #f8f8f2;
  padding: 15px;
  border-radius: 4px;
  line-height: 1.5;
}

.json-preview {
  margin-top: 10px;
  border: 1px solid #dcdfe6;
  padding: 10px;
  border-radius: 4px;
}

.json-preview pre {
  background: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
}

.mode-switch {
  display: flex;
  gap: 5px;
  margin-bottom: 10px;
}

.mode-switch button {
  flex: 1;
}

.mode-switch button.active {
  background: #409eff;
  color: white;
}

.help-link {
  display: inline-block;
  margin-top: 10px;
  color: #409eff;
  text-decoration: none;
}

.help-link:hover {
  text-decoration: underline;
}
```

---

## 📦 後端 API 檢查

### 需要確認的 API Endpoints

```javascript
// 1. 知識庫 API 需要接受新欄位
POST   /api/knowledge
PUT    /api/knowledge/:id
{
  "question_summary": "...",
  "answer": "...",
  "action_type": "api_call",      // ⭐ 新增
  "api_config": { ... },          // ⭐ 新增
  "form_id": "..."
}

// 2. 表單 API 需要接受新欄位
POST   /api/forms
PUT    /api/forms/:id
{
  "form_id": "...",
  "form_name": "...",
  "fields": [...],
  "on_complete_action": "call_api",  // ⭐ 新增
  "api_config": { ... }              // ⭐ 新增
}

// 3. 確認 GET API 返回新欄位
GET    /api/knowledge
GET    /api/knowledge/:id
回應應包含：action_type, api_config

GET    /api/forms
GET    /api/forms/:id
回應應包含：on_complete_action, api_config
```

---

## 🧪 測試檢查清單

### 前端功能測試

#### 知識庫管理

- [ ] 可以選擇 action_type（4 個選項）
- [ ] 根據 action_type 正確顯示/隱藏欄位
- [ ] 可以配置 API（簡易模式）
- [ ] 可以配置 API（JSON 模式）
- [ ] JSON 格式驗證正常
- [ ] 參數可以添加/刪除
- [ ] 保存時正確組裝數據
- [ ] 列表正確顯示 action_type 標籤
- [ ] 編輯時正確載入配置

#### 表單管理

- [ ] 列表正確顯示 on_complete_action
- [ ] 可以選擇 on_complete_action（3 個選項）
- [ ] 可以配置表單完成後的 API
- [ ] 表單參數映射功能正常
- [ ] 保存時正確組裝數據

---

## 📋 開發優先級建議

### Phase 1（必須，2-3 天）

1. ✅ **KnowledgeView.vue** - action_type 選擇器
2. ✅ **KnowledgeView.vue** - 簡易模式 API 配置
3. ✅ **FormEditorView.vue** - on_complete_action 選擇器
4. ✅ **後端 API** - 確認接受新欄位

### Phase 2（重要，1-2 天）

5. ✅ **KnowledgeView.vue** - JSON 模式 API 配置
6. ✅ **FormEditorView.vue** - 表單參數映射
7. ✅ **列表顯示** - action_type 和 on_complete_action 標籤

### Phase 3（優化，1 天）

8. ⭐ UI/UX 優化（圖示、顏色、提示）
9. ⭐ 錯誤處理和驗證
10. ⭐ 幫助文檔集成

---

## 📚 相關文檔

- [API 配置指南](../design/API_CONFIGURATION_GUIDE.md) - 給用戶的配置說明
- 完整變更日誌 - 後端變更詳情
- 更新摘要 - 快速了解

---

## 💡 實作建議

### 組件化建議

可以將 API 配置 UI 抽取為獨立組件：

```
components/
  ├── ApiConfigEditor.vue        # API 配置編輯器（可重用）
  ├── ActionTypeSelector.vue     # action_type 選擇器
  └── CompleteActionSelector.vue # on_complete_action 選擇器
```

**ApiConfigEditor.vue**:
```vue
<template>
  <div class="api-config-editor">
    <!-- API 配置 UI -->
  </div>
</template>

<script>
export default {
  name: 'ApiConfigEditor',
  props: {
    modelValue: {
      type: Object,
      default: null
    },
    mode: {
      type: String,
      default: 'simple'  // 'simple' | 'advanced'
    }
  },
  emits: ['update:modelValue'],
  // ...
}
</script>
```

**使用方式**:
```vue
<!-- KnowledgeView.vue -->
<ApiConfigEditor
  v-if="showApiConfig"
  v-model="formData.api_config"
  mode="simple"
/>

<!-- FormEditorView.vue -->
<ApiConfigEditor
  v-if="formData.on_complete_action !== 'show_knowledge'"
  v-model="formData.api_config"
  :form-fields="formData.fields"
  mode="simple"
/>
```

---

## 🐛 已知問題與解決方案

### 問題 1：JSON 編輯器體驗不佳

**解決方案**：集成專業的 JSON 編輯器

```bash
npm install vue-json-editor
```

```vue
<template>
  <JsonEditor
    v-model="apiConfigJSON"
    :mode="'code'"
    :modes="['code', 'tree']"
  />
</template>
```

### 問題 2：參數映射複雜

**解決方案**：提供預設模板

```javascript
const API_TEMPLATES = {
  billing_inquiry: {
    endpoint: 'billing_inquiry',
    params: {
      user_id: '{session.user_id}'
    },
    combine_with_knowledge: true
  },
  maintenance_request: {
    endpoint: 'maintenance_request',
    params_from_form: {
      user_id: '{session.user_id}',
      location: 'location',
      description: 'issue_description'
    },
    combine_with_knowledge: false
  }
};

// 使用模板
methods: {
  loadTemplate(templateName) {
    const template = API_TEMPLATES[templateName];
    if (template) {
      this.apiConfigData = JSON.parse(JSON.stringify(template));
    }
  }
}
```

---

**最後更新**: 2026-01-18
**優先級**: 🔴 高
**預計工時**: 4-6 天
