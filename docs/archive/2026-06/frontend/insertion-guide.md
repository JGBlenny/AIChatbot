# 前端代碼插入位置詳細指南

**日期**: 2026-01-18
**文件**: `knowledge-admin/frontend/src/views/KnowledgeView.vue`

---

## 📍 精確插入位置

### 位置 1：action_type 選擇器

**插入位置**: 在「意圖關聯」區塊之後，「表單關聯」區塊之前

**當前代碼** (第 290-294 行左右):
```html
          </div>

          <!-- 表單關聯 -->
          <div class="form-group">
```

**在這裡插入** ⬇️

```html
          </div>

          <!-- ⭐⭐⭐ 新增：動作類型選擇器 ⭐⭐⭐ -->
          <div class="form-group">
            <label>
              動作類型 <span class="required">*</span>
              <span class="field-hint">（決定知識的執行行為）</span>
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
          <!-- ⭐⭐⭐ 新增結束 ⭐⭐⭐ -->

          <!-- 表單關聯 -->
          <div class="form-group">
```

---

### 位置 2：修改表單關聯區塊（添加條件顯示）

**當前代碼** (第 294-315 行):
```html
          <!-- 表單關聯 -->
          <div class="form-group">
            <label>表單關聯 <span class="field-hint">（選填，關聯後用戶詢問時會觸發表單）</span></label>
```

**修改為** ⬇️

```html
          <!-- 表單關聯（條件顯示）-->
          <div class="form-group" v-if="showFormField">
            <label>表單關聯 <span class="required">*</span></label>
```

**說明**:
- 添加 `v-if="showFormField"` 條件
- 當 `action_type` 為 `form_fill` 或 `form_then_api` 時才顯示

---

### 位置 3：API 配置區塊

**插入位置**: 在「表單關聯」區塊結束之後，「內容 (Markdown)」區塊之前

**當前代碼** (第 315-318 行左右):
```html
            </div>
          </div>

          <div class="form-group">
            <label>內容 (Markdown) *</label>
```

**在這裡插入** ⬇️

```html
            </div>
          </div>

          <!-- ⭐⭐⭐ 新增：API 配置區塊 ⭐⭐⭐ -->
          <div class="form-group" v-if="showApiConfig">
            <label>
              API 配置
              <span class="field-hint">（配置 API 調用參數）</span>
            </label>

            <!-- API Endpoint 選擇 -->
            <div class="config-row">
              <label class="sub-label">API Endpoint:</label>
              <select v-model="apiConfigData.endpoint" class="form-select">
                <option value="">請選擇...</option>
                <option value="billing_inquiry">📋 帳單查詢</option>
                <option value="verify_tenant_identity">🔐 租客身份驗證</option>
                <option value="resend_invoice">📧 重新發送帳單</option>
                <option value="maintenance_request">🔧 報修申請</option>
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
                  <button @click="removeParam(index)" class="btn-sm btn-delete" type="button">✕</button>
                </div>
                <button @click="addParam" class="btn-sm btn-secondary" type="button">＋ 添加參數</button>
              </div>
              <p class="hint-text">
                💡 提示：使用 <code>{session.user_id}</code> 獲取登入用戶ID，
                使用 <code>{session.vendor_id}</code> 獲取業者ID
              </p>
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
                class="form-control"
              ></textarea>
              <p class="hint-text">💡 當 API 調用失敗時，顯示此訊息（可包含知識答案）</p>
            </div>

            <!-- JSON 預覽 -->
            <details class="json-preview">
              <summary style="cursor: pointer; color: #409eff; margin-top: 10px;">
                🔍 查看生成的 JSON 配置
              </summary>
              <pre style="background: #f5f7fa; padding: 10px; border-radius: 4px; margin-top: 10px;">{{ apiConfigPreview }}</pre>
            </details>
          </div>
          <!-- ⭐⭐⭐ 新增結束 ⭐⭐⭐ -->

          <div class="form-group">
            <label>內容 (Markdown) *</label>
```

---

## 📝 需要添加的 JavaScript 代碼

### 在 `data()` 中添加

**位置**: 在 `data()` 函數的 `formData` 對象中

**當前代碼** (大約第 435 行):
```javascript
data() {
  return {
    // ... 其他數據
    formData: {
      question_summary: '',
      answer: '',
      keywords: [],
      scope: 'customized',
      vendor_id: null,
      form_id: '',
      // ... 其他欄位
    }
  }
}
```

**修改為** ⬇️

```javascript
data() {
  return {
    // ... 其他數據
    formData: {
      question_summary: '',
      answer: '',
      keywords: [],
      scope: 'customized',
      vendor_id: null,
      action_type: 'direct_answer',  // ⭐ 新增
      form_id: '',
      // ... 其他欄位
    },

    // ⭐⭐⭐ 新增：API 配置數據 ⭐⭐⭐
    apiConfigData: {
      endpoint: '',
      params: [],  // [{ key: 'user_id', value: '{session.user_id}' }]
      combine_with_knowledge: true,
      fallback_message: ''
    }
    // ⭐⭐⭐ 新增結束 ⭐⭐⭐
  }
}
```

---

### 在 `computed` 中添加

**位置**: 在 `computed` 對象中

**添加以下計算屬性**:

```javascript
computed: {
  // ... 現有的計算屬性

  // ⭐⭐⭐ 新增計算屬性 ⭐⭐⭐
  showFormField() {
    // 當 action_type 為 form_fill 或 form_then_api 時顯示表單欄位
    return ['form_fill', 'form_then_api'].includes(this.formData.action_type);
  },

  showApiConfig() {
    // 當 action_type 為 api_call 或 form_then_api 時顯示 API 配置
    return ['api_call', 'form_then_api'].includes(this.formData.action_type);
  },

  apiConfigPreview() {
    // 生成 API 配置的 JSON 預覽
    if (!this.apiConfigData.endpoint) {
      return '// 請先選擇 API Endpoint';
    }

    const params = {};
    this.apiConfigData.params.forEach(p => {
      if (p.key) params[p.key] = p.value;
    });

    const config = {
      endpoint: this.apiConfigData.endpoint,
      params: params,
      combine_with_knowledge: this.apiConfigData.combine_with_knowledge
    };

    if (this.apiConfigData.fallback_message) {
      config.fallback_message = this.apiConfigData.fallback_message;
    }

    return JSON.stringify(config, null, 2);
  }
  // ⭐⭐⭐ 新增結束 ⭐⭐⭐
}
```

---

### 在 `methods` 中添加

**位置**: 在 `methods` 對象中

**添加以下方法**:

```javascript
methods: {
  // ... 現有的方法

  // ⭐⭐⭐ 新增方法 ⭐⭐⭐
  addParam() {
    this.apiConfigData.params.push({ key: '', value: '' });
  },

  removeParam(index) {
    this.apiConfigData.params.splice(index, 1);
  },

  buildApiConfig() {
    // 組裝 API 配置
    if (!this.showApiConfig || !this.apiConfigData.endpoint) {
      return null;
    }

    const params = {};
    this.apiConfigData.params.forEach(p => {
      if (p.key) params[p.key] = p.value;
    });

    const config = {
      endpoint: this.apiConfigData.endpoint,
      params: params,
      combine_with_knowledge: this.apiConfigData.combine_with_knowledge
    };

    if (this.apiConfigData.fallback_message) {
      config.fallback_message = this.apiConfigData.fallback_message;
    }

    return config;
  },
  // ⭐⭐⭐ 新增結束 ⭐⭐⭐
}
```

---

### 修改 `saveKnowledge()` 方法

**位置**: 在現有的 `saveKnowledge()` 方法中

**找到這段代碼** (大約第 910-920 行):
```javascript
async saveKnowledge() {
  // ... 驗證邏輯

  const payload = {
    question_summary: this.formData.question_summary,
    answer: this.formData.answer,
    // ... 其他欄位
  };
}
```

**修改為** ⬇️

```javascript
async saveKnowledge() {
  // ... 驗證邏輯

  // ⭐ 組裝 API 配置
  const apiConfig = this.buildApiConfig();

  const payload = {
    question_summary: this.formData.question_summary,
    answer: this.formData.answer,
    action_type: this.formData.action_type,  // ⭐ 新增
    api_config: apiConfig,                   // ⭐ 新增
    form_id: this.showFormField ? this.formData.form_id : null,  // ⭐ 修改為條件判斷
    // ... 其他欄位
  };
}
```

---

### 修改 `showEditModal()` 方法（載入數據）

**位置**: 在 `showEditModal(item)` 方法中

**找到這段代碼** (大約第 822-840 行):
```javascript
async showEditModal(item) {
  this.editingItem = item;

  // ... 載入知識數據

  this.formData = {
    question_summary: knowledge.question_summary || '',
    answer: knowledge.answer || '',
    // ... 其他欄位
    form_id: knowledge.form_id || '',
  };
}
```

**修改為** ⬇️

```javascript
async showEditModal(item) {
  this.editingItem = item;

  // ... 載入知識數據

  this.formData = {
    question_summary: knowledge.question_summary || '',
    answer: knowledge.answer || '',
    action_type: knowledge.action_type || 'direct_answer',  // ⭐ 新增
    // ... 其他欄位
    form_id: knowledge.form_id || '',
  };

  // ⭐⭐⭐ 新增：載入 API 配置 ⭐⭐⭐
  if (knowledge.api_config) {
    this.apiConfigData = {
      endpoint: knowledge.api_config.endpoint || '',
      params: [],
      combine_with_knowledge: knowledge.api_config.combine_with_knowledge !== false,
      fallback_message: knowledge.api_config.fallback_message || ''
    };

    // 轉換 params 為陣列格式
    if (knowledge.api_config.params) {
      Object.entries(knowledge.api_config.params).forEach(([key, value]) => {
        this.apiConfigData.params.push({ key, value });
      });
    }
  } else {
    // 重置 API 配置
    this.apiConfigData = {
      endpoint: '',
      params: [],
      combine_with_knowledge: true,
      fallback_message: ''
    };
  }
  // ⭐⭐⭐ 新增結束 ⭐⭐⭐
}
```

---

## 🎨 需要添加的 CSS 樣式

**位置**: 在 `<style scoped>` 區塊中

**添加以下樣式**:

```css
/* ⭐⭐⭐ 新增：API 配置樣式 ⭐⭐⭐ */
.config-row {
  margin-bottom: 15px;
}

.sub-label {
  display: block;
  font-weight: 500;
  margin-bottom: 5px;
  color: #606266;
  font-size: 14px;
}

.param-builder {
  border: 1px solid #dcdfe6;
  padding: 15px;
  border-radius: 4px;
  background: #f5f7fa;
  margin-top: 5px;
}

.param-row {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
  align-items: center;
}

.param-key,
.param-value {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
}

.param-key {
  max-width: 200px;
}

.json-preview {
  margin-top: 15px;
  border: 1px solid #dcdfe6;
  padding: 10px;
  border-radius: 4px;
  background: #fff;
}

.json-preview pre {
  background: #2d2d2d;
  color: #f8f8f2;
  padding: 15px;
  border-radius: 4px;
  overflow-x: auto;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
}

/* action_type 標籤樣式 */
.badge.action-direct_answer {
  background: #67c23a;
  color: white;
  padding: 4px 8px;
  border-radius: 3px;
  font-size: 12px;
}

.badge.action-form_fill {
  background: #409eff;
  color: white;
  padding: 4px 8px;
  border-radius: 3px;
  font-size: 12px;
}

.badge.action-api_call {
  background: #e6a23c;
  color: white;
  padding: 4px 8px;
  border-radius: 3px;
  font-size: 12px;
}

.badge.action-form_then_api {
  background: #f56c6c;
  color: white;
  padding: 4px 8px;
  border-radius: 3px;
  font-size: 12px;
}
/* ⭐⭐⭐ 新增結束 ⭐⭐⭐ */
```

---

## ✅ 檢查清單

完成所有修改後，檢查以下項目：

### HTML 模板
- [ ] action_type 選擇器已添加（在「意圖關聯」和「表單關聯」之間）
- [ ] 表單關聯添加了 `v-if="showFormField"` 條件
- [ ] API 配置區塊已添加（在「表單關聯」和「內容 (Markdown)」之間）
- [ ] API 配置區塊有 `v-if="showApiConfig"` 條件

### JavaScript
- [ ] `formData.action_type` 已添加（預設值 'direct_answer'）
- [ ] `apiConfigData` 對象已添加
- [ ] `showFormField` 計算屬性已添加
- [ ] `showApiConfig` 計算屬性已添加
- [ ] `apiConfigPreview` 計算屬性已添加
- [ ] `addParam()` 方法已添加
- [ ] `removeParam()` 方法已添加
- [ ] `buildApiConfig()` 方法已添加
- [ ] `saveKnowledge()` 方法已修改（包含 action_type 和 api_config）
- [ ] `showEditModal()` 方法已修改（載入 API 配置）

### CSS
- [ ] API 配置相關樣式已添加
- [ ] action_type 標籤樣式已添加

---

## 🧪 測試步驟

1. **啟動開發環境**:
   ```bash
   cd knowledge-admin/frontend
   npm run dev
   ```

2. **測試新增知識**:
   - 點擊「新增知識」
   - 檢查是否顯示「動作類型」選擇器
   - 選擇不同的 action_type，觀察表單和 API 配置區塊的顯示/隱藏

3. **測試 API 配置**:
   - 選擇 `api_call`
   - 選擇 API Endpoint
   - 添加參數
   - 查看 JSON 預覽

4. **測試保存**:
   - 填寫完整表單
   - 保存知識
   - 檢查控制台是否有錯誤
   - 檢查後端是否成功接收數據

5. **測試編輯**:
   - 編輯剛才創建的知識
   - 檢查 action_type 和 api_config 是否正確載入

---

**需要幫助？** 查看 FRONTEND_TODO.md 或 FRONTEND_REQUIREMENTS.md

**最後更新**: 2026-01-18
