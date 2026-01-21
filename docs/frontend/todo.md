# 前端待辦清單（簡化版）

**優先級**: 🔴 高
**預計工時**: 4-6 天
**狀態**: ❌ 尚未開始

---

## 🎯 快速總覽

**需要修改的頁面**: 3 個
1. 知識庫管理頁面（KnowledgeView.vue）
2. 表單管理頁面（FormManagementView.vue）
3. 表單編輯器頁面（FormEditorView.vue）

**需要添加的欄位**: 4 個
- `action_type` (知識庫)
- `api_config` (知識庫)
- `on_complete_action` (表單)
- `api_config` (表單)

---

## ✅ 任務清單

### 📋 Phase 1：知識庫管理（2 天）

#### 任務 1.1：添加 action_type 選擇器

**文件**: `knowledge-admin/frontend/src/views/KnowledgeView.vue`

**位置**: 表單模態框，「關聯表單」欄位之前

**要添加的 HTML**:
```html
<div class="form-group">
  <label>動作類型 <span class="required">*</span></label>
  <select v-model="formData.action_type" required>
    <option value="direct_answer">📝 純知識問答</option>
    <option value="form_fill">📋 表單 + 知識答案</option>
    <option value="api_call">🔌 API 調用 + 知識答案</option>
    <option value="form_then_api">📋🔌 表單 → API → 知識</option>
  </select>
</div>
```

**要添加的數據**:
```javascript
data() {
  return {
    formData: {
      // ... 現有欄位
      action_type: 'direct_answer',  // ⭐ 新增這行
    }
  }
}
```

**檢查**:
- [ ] 下拉選單顯示 4 個選項
- [ ] 預設值為 `direct_answer`
- [ ] 可以正常切換選項

---

#### 任務 1.2：添加 API 配置區塊（簡易版）

**位置**: 「關聯表單」欄位之後

**要添加的 HTML**:
```html
<div class="form-group" v-if="showApiConfig">
  <label>API 配置</label>

  <!-- API Endpoint -->
  <div style="margin-bottom: 10px;">
    <label class="sub-label">API Endpoint:</label>
    <select v-model="apiConfigData.endpoint">
      <option value="">請選擇...</option>
      <option value="billing_inquiry">帳單查詢</option>
      <option value="verify_tenant_identity">租客身份驗證</option>
      <option value="resend_invoice">重新發送帳單</option>
      <option value="maintenance_request">報修申請</option>
    </select>
  </div>

  <!-- 合併知識答案 -->
  <div>
    <label>
      <input type="checkbox" v-model="apiConfigData.combine_with_knowledge" />
      合併知識答案
    </label>
  </div>
</div>
```

**要添加的數據和計算屬性**:
```javascript
data() {
  return {
    apiConfigData: {
      endpoint: '',
      combine_with_knowledge: true
    }
  }
},

computed: {
  showApiConfig() {
    return ['api_call', 'form_then_api'].includes(this.formData.action_type);
  }
}
```

**檢查**:
- [ ] 當 action_type 為 `api_call` 或 `form_then_api` 時顯示
- [ ] 可以選擇 API endpoint
- [ ] 可以勾選/取消「合併知識答案」

---

#### 任務 1.3：修改保存邏輯

**位置**: `saveKnowledge()` 方法

**要修改的代碼**:
```javascript
async saveKnowledge() {
  // 組裝 API 配置
  let apiConfig = null;
  if (this.showApiConfig && this.apiConfigData.endpoint) {
    apiConfig = {
      endpoint: this.apiConfigData.endpoint,
      params: { user_id: '{session.user_id}' },  // 先用固定值
      combine_with_knowledge: this.apiConfigData.combine_with_knowledge
    };
  }

  const payload = {
    question_summary: this.formData.question_summary,
    answer: this.formData.answer,
    action_type: this.formData.action_type,  // ⭐ 新增
    api_config: apiConfig,                   // ⭐ 新增
    form_id: this.showFormField ? this.formData.form_id : null,
    // ... 其他欄位
  };

  // 提交到後端 ...
}
```

**檢查**:
- [ ] 保存時包含 `action_type`
- [ ] 保存時包含 `api_config`（如果有配置）
- [ ] 後端成功接收並保存

---

#### 任務 1.4：列表顯示 action_type

**位置**: 知識列表 `<table>`

**要修改的 HTML**:
```html
<table>
  <thead>
    <tr>
      <th width="60">ID</th>
      <th>問題摘要</th>
      <th width="100">動作類型</th>  <!-- ⭐ 新增 -->
      <!-- ... -->
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
      <!-- ... -->
    </tr>
  </tbody>
</table>
```

**要添加的方法**:
```javascript
methods: {
  getActionTypeLabel(type) {
    const labels = {
      'direct_answer': '📝 知識',
      'form_fill': '📋 表單',
      'api_call': '🔌 API',
      'form_then_api': '📋🔌 表單+API'
    };
    return labels[type] || '📝 知識';
  }
}
```

**要添加的 CSS**:
```css
.badge.action-direct_answer { background: #67c23a; color: white; }
.badge.action-form_fill { background: #409eff; color: white; }
.badge.action-api_call { background: #e6a23c; color: white; }
.badge.action-form_then_api { background: #f56c6c; color: white; }
```

**檢查**:
- [ ] 列表顯示 action_type 欄位
- [ ] 標籤顏色正確
- [ ] 標籤文字正確

---

### 📋 Phase 2：表單管理（1 天）

#### 任務 2.1：表單列表顯示 on_complete_action

**文件**: `knowledge-admin/frontend/src/views/FormManagementView.vue`

**要修改的 HTML**:
```html
<table>
  <thead>
    <tr>
      <th width="150">表單ID</th>
      <th>表單名稱</th>
      <th width="120">完成後動作</th>  <!-- ⭐ 新增 -->
      <!-- ... -->
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
      <!-- ... -->
    </tr>
  </tbody>
</table>
```

**要添加的方法**:
```javascript
methods: {
  getCompleteActionLabel(action) {
    const labels = {
      'show_knowledge': '📝 顯示知識',
      'call_api': '🔌 調用 API',
      'both': '📝🔌 兩者'
    };
    return labels[action] || '📝 顯示知識';
  }
}
```

**檢查**:
- [ ] 列表顯示 on_complete_action 欄位
- [ ] 標籤顏色和文字正確

---

### 📋 Phase 3：表單編輯器（1-2 天）

#### 任務 3.1：添加 on_complete_action 選擇器

**文件**: `knowledge-admin/frontend/src/views/FormEditorView.vue`

**位置**: 表單基本資訊區塊

**要添加的 HTML**:
```html
<div class="form-group">
  <label>表單完成後執行 <span class="required">*</span></label>
  <select v-model="formData.on_complete_action" required>
    <option value="show_knowledge">📝 只顯示知識答案</option>
    <option value="call_api">🔌 只調用 API</option>
    <option value="both">📝🔌 兩者都執行</option>
  </select>
</div>
```

**要添加的數據**:
```javascript
data() {
  return {
    formData: {
      // ... 現有欄位
      on_complete_action: 'show_knowledge',  // ⭐ 新增
      api_config: null                       // ⭐ 新增
    }
  }
}
```

**檢查**:
- [ ] 下拉選單顯示 3 個選項
- [ ] 預設值為 `show_knowledge`

---

#### 任務 3.2：添加 API 配置區塊

**位置**: on_complete_action 欄位之後

**要添加的 HTML**:
```html
<div v-if="formData.on_complete_action !== 'show_knowledge'">
  <h4>API 配置</h4>

  <div class="form-group">
    <label>API Endpoint:</label>
    <select v-model="apiConfigData.endpoint">
      <option value="">請選擇...</option>
      <option value="billing_inquiry">帳單查詢</option>
      <option value="maintenance_request">報修申請</option>
    </select>
  </div>

  <div class="form-group">
    <label>
      <input type="checkbox" v-model="apiConfigData.combine_with_knowledge" />
      合併知識答案
    </label>
  </div>
</div>
```

**要添加的數據**:
```javascript
data() {
  return {
    apiConfigData: {
      endpoint: '',
      combine_with_knowledge: true
    }
  }
}
```

**檢查**:
- [ ] 當 on_complete_action 為 `call_api` 或 `both` 時顯示
- [ ] 可以選擇 API endpoint

---

#### 任務 3.3：修改保存邏輯

**位置**: 保存表單的方法

**要修改的代碼**:
```javascript
async saveForm() {
  // 組裝 API 配置
  let apiConfig = null;
  if (this.formData.on_complete_action !== 'show_knowledge' && this.apiConfigData.endpoint) {
    apiConfig = {
      endpoint: this.apiConfigData.endpoint,
      params_from_form: {},  // 先用空對象
      combine_with_knowledge: this.apiConfigData.combine_with_knowledge
    };
  }

  const payload = {
    form_id: this.formData.form_id,
    form_name: this.formData.form_name,
    fields: this.formData.fields,
    on_complete_action: this.formData.on_complete_action,  // ⭐ 新增
    api_config: apiConfig,                                 // ⭐ 新增
    // ... 其他欄位
  };

  // 提交到後端 ...
}
```

**檢查**:
- [ ] 保存時包含 `on_complete_action`
- [ ] 保存時包含 `api_config`（如果有配置）

---

## 🧪 測試檢查清單

完成所有任務後，進行以下測試：

### 知識庫管理測試

- [ ] 新增知識時可以選擇 action_type
- [ ] 選擇 `api_call` 時顯示 API 配置
- [ ] 選擇 `form_then_api` 時同時顯示表單和 API 配置
- [ ] 保存後重新編輯，配置正確載入
- [ ] 列表正確顯示 action_type 標籤

### 表單管理測試

- [ ] 表單列表顯示 on_complete_action
- [ ] 新增表單時可以選擇 on_complete_action
- [ ] 選擇 `call_api` 或 `both` 時顯示 API 配置
- [ ] 保存後重新編輯，配置正確載入

### 集成測試

- [ ] 創建一個 `action_type = api_call` 的知識
- [ ] 創建一個 `on_complete_action = call_api` 的表單
- [ ] 在聊天測試頁面驗證功能

---

## 📚 參考資料

- [詳細前端規格](./FRONTEND_REQUIREMENTS.md) - 完整的 UI 設計和實作細節
- [API 配置指南](./design/API_CONFIGURATION_GUIDE.md) - 了解 API 配置的格式
- [後端變更日誌](./CHANGELOG_2026-01-18.md) - 了解後端的變更

---

## 💡 快速開始

### Step 1: 啟動開發環境

```bash
cd knowledge-admin/frontend
npm install
npm run dev
```

### Step 2: 開始 Phase 1 任務

從「任務 1.1：添加 action_type 選擇器」開始

### Step 3: 測試

每完成一個任務就測試一次，確保功能正常

---

## ❓ 遇到問題？

1. **不確定要改哪裡？**
   - 查看 [詳細前端規格](./FRONTEND_REQUIREMENTS.md)

2. **不知道 API 配置格式？**
   - 查看 [API 配置指南](./design/API_CONFIGURATION_GUIDE.md) 的範例

3. **後端 API 不接受新欄位？**
   - 確認後端已經執行資料庫遷移
   - 查看 [後端變更日誌](./CHANGELOG_2026-01-18.md)

---

**最後更新**: 2026-01-18
**預計完成**: Phase 1 (2天) + Phase 2 (1天) + Phase 3 (1-2天) = 4-6 天
