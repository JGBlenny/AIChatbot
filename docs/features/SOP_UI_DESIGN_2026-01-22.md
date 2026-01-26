# 🎨 SOP 後續動作 UI 設計方案

**日期**: 2026-01-22
**目的**: 在 Knowledge Admin 中新增 SOP 後續動作的管理介面
**目標**: 讓非技術人員也能輕鬆配置 SOP 的自動觸發邏輯

---

## 📋 需求分析

### 新增欄位
1. **next_action** - 後續動作類型（none/form_fill/api_call/form_then_api）
2. **next_form_id** - 要觸發的表單
3. **next_api_config** - API 配置
4. **trigger_keywords** - 觸發關鍵詞陣列
5. **followup_prompt** - 引導語

### 設計原則
✅ **漸進式揭露** - 根據選擇動態顯示相關欄位
✅ **易於理解** - 使用直觀的語言和圖示
✅ **預設值** - 提供常用的預設配置
✅ **即時預覽** - 顯示配置後的效果

---

## 🎯 UI 設計方案

### 方案一：擴展現有編輯 Modal（推薦）⭐

在現有的「編輯 SOP Modal」中新增「後續動作」區塊。

#### 優點
- ✅ 不改變現有操作流程
- ✅ 所有設定集中在一處
- ✅ 實作簡單

#### 缺點
- ⚠️ Modal 內容變多，可能需要滾動

---

### 方案二：新增「進階設定」Tab

在 SOP 卡片中新增「進階設定」按鈕，點擊後展開或進入新頁面。

#### 優點
- ✅ 不干擾基本編輯流程
- ✅ 適合進階功能

#### 缺點
- ❌ 多一個點擊步驟
- ❌ 功能不易被發現

---

## 🎨 推薦設計：擴展編輯 Modal

### UI 結構

```
┌─────────────────────────────────────────────┐
│  編輯 SOP                                   │
│  ─────────────────────────────────────────  │
│                                             │
│  基本資訊                                   │
│  ┌─────────────────────────────────────┐   │
│  │ 項目名稱 *                          │   │
│  │ [冷氣無法啟動                    ]   │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ SOP 內容（排查步驟）*               │   │
│  │ [                               ]   │   │
│  │ [  檢查電源插座、控制面板...     ]   │   │
│  │ [  若無法解決，請提交維修請求   ]   │   │
│  │ [                               ]   │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ─────────────────────────────────────────  │
│                                             │
│  🔄 後續動作設定（選填）                    │
│  ┌─────────────────────────────────────┐   │
│  │ 當用戶排查無效時，自動執行：        │   │
│  │                                     │   │
│  │ ○ 無後續動作（預設）                │   │
│  │ ○ 觸發表單填寫                      │   │
│  │ ○ 調用 API                          │   │
│  │ ● 填寫表單後調用 API ←────────┐    │   │
│  └─────────────────────────────────────┘   │
│                                      ↓      │
│  ┌─────────────────────────────────────┐   │
│  │ 📋 要填寫的表單                     │   │
│  │ [ 報修申請表          ▼ ]          │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ 🔑 觸發關鍵詞（每行一個）           │   │
│  │ [                               ]   │   │
│  │ [ 還是不行                       ]   │   │
│  │ [ 試過了                         ]   │   │
│  │ [ 需要維修                       ]   │   │
│  │ [ 請幫我報修                     ]   │   │
│  │ [                               ]   │   │
│  │ ℹ️ 當用戶說出這些關鍵詞時，自動觸發│   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ 💬 觸發時的引導語                   │   │
│  │ [                               ]   │   │
│  │ [ 好的，我來協助您提交維修請求。]   │   │
│  │ [ 請提供一些詳細資訊。           ]   │   │
│  │ [                               ]   │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ 🔧 API 設定（進階）                 │   │
│  │ [顯示/隱藏▼]                        │   │
│  └─────────────────────────────────────┘   │
│    ↓ 展開後                                │
│  ┌─────────────────────────────────────┐   │
│  │ API 端點                            │   │
│  │ [ maintenance_request   ▼ ]        │   │
│  │                                     │   │
│  │ 預設參數（JSON）                    │   │
│  │ {                                   │   │
│  │   "problem_category": "ac_...",     │   │
│  │   "urgency_level": "urgent"         │   │
│  │ }                                   │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ─────────────────────────────────────────  │
│                                             │
│  📝 效果預覽                                │
│  ┌─────────────────────────────────────┐   │
│  │ 租戶：「冷氣壞了」                   │   │
│  │ ↓                                   │   │
│  │ 系統：返回 SOP 排查步驟              │   │
│  │ ↓                                   │   │
│  │ 租戶：「試過了，還是不行」← 觸發     │   │
│  │ ↓                                   │   │
│  │ 系統：「好的，我來協助您提交維修...」│   │
│  │ ↓                                   │   │
│  │ 開始填寫「報修申請表」               │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  [💾 儲存]  [取消]                          │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 📝 欄位詳細說明

### 1. 後續動作類型（next_action）

**UI 元件**: Radio Button Group
**必填**: 否
**預設值**: `none`

```html
<div class="form-group">
  <label>🔄 後續動作設定</label>
  <p class="hint">當用戶排查無效時，自動執行：</p>

  <div class="radio-group">
    <label class="radio-option">
      <input type="radio" v-model="editingForm.next_action" value="none" />
      <div class="radio-content">
        <strong>無後續動作</strong>
        <p>只返回 SOP 內容，不觸發任何動作</p>
      </div>
    </label>

    <label class="radio-option">
      <input type="radio" v-model="editingForm.next_action" value="form_fill" />
      <div class="radio-content">
        <strong>📋 觸發表單填寫</strong>
        <p>引導用戶填寫表單收集詳細資訊</p>
      </div>
    </label>

    <label class="radio-option">
      <input type="radio" v-model="editingForm.next_action" value="api_call" />
      <div class="radio-content">
        <strong>🔌 調用 API</strong>
        <p>直接調用 API（適合不需要收集額外資訊的場景）</p>
      </div>
    </label>

    <label class="radio-option recommended">
      <input type="radio" v-model="editingForm.next_action" value="form_then_api" />
      <div class="radio-content">
        <strong>📋🔌 填寫表單後調用 API</strong>
        <span class="badge badge-primary">推薦</span>
        <p>先收集資訊，表單完成後自動調用 API</p>
      </div>
    </label>
  </div>
</div>
```

---

### 2. 表單選擇（next_form_id）

**UI 元件**: Select Dropdown
**顯示條件**: next_action = 'form_fill' 或 'form_then_api'
**必填**: 是（當顯示時）

```html
<div v-if="needsFormSelection" class="form-group">
  <label>📋 要填寫的表單 *</label>
  <select v-model="editingForm.next_form_id" required class="form-control">
    <option value="">請選擇表單</option>
    <option value="maintenance_troubleshooting">維修問題排查表</option>
    <option value="maintenance_dispatch">維修派工資訊表</option>
    <option value="rental_application">租屋申請表</option>
    <option value="rental_inquiry">租屋詢問表</option>
  </select>
  <p class="hint">💡 建議：維護類 SOP 使用「維修問題排查表」</p>
</div>
```

---

### 3. 觸發關鍵詞（trigger_keywords）

**UI 元件**: Textarea（每行一個關鍵詞）
**顯示條件**: next_action != 'none'
**必填**: 是（當顯示時）

```html
<div v-if="needsTriggerKeywords" class="form-group">
  <label>🔑 觸發關鍵詞 *</label>
  <textarea
    v-model="triggerKeywordsText"
    class="form-control"
    rows="5"
    placeholder="還是不行&#10;試過了&#10;都不行&#10;需要維修&#10;請幫我報修"
    required
  ></textarea>
  <p class="hint">
    ℹ️ 每行一個關鍵詞。當用戶說出這些詞時，自動觸發後續動作。
  </p>

  <!-- 快速插入常用關鍵詞 -->
  <div class="quick-keywords">
    <span class="label">快速插入：</span>
    <button type="button" @click="addKeyword('還是不行')" class="btn-tag">還是不行</button>
    <button type="button" @click="addKeyword('試過了')" class="btn-tag">試過了</button>
    <button type="button" @click="addKeyword('需要維修')" class="btn-tag">需要維修</button>
    <button type="button" @click="addKeyword('請幫我報修')" class="btn-tag">請幫我報修</button>
    <button type="button" @click="addKeyword('無法解決')" class="btn-tag">無法解決</button>
  </div>
</div>
```

---

### 4. 引導語（followup_prompt）

**UI 元件**: Textarea
**顯示條件**: next_action != 'none'
**必填**: 是（當顯示時）

```html
<div v-if="needsFollowupPrompt" class="form-group">
  <label>💬 觸發時的引導語 *</label>
  <textarea
    v-model="editingForm.followup_prompt"
    class="form-control"
    rows="3"
    placeholder="好的，我來協助您提交維修請求。請提供一些詳細資訊。"
    required
  ></textarea>
  <p class="hint">ℹ️ 觸發後續動作時，向用戶顯示的訊息。</p>

  <!-- 預設範本 -->
  <div class="quick-templates">
    <span class="label">範本：</span>
    <button type="button" @click="usePromptTemplate('maintenance')" class="btn-tag">
      維修請求範本
    </button>
    <button type="button" @click="usePromptTemplate('inquiry')" class="btn-tag">
      詢問範本
    </button>
  </div>
</div>
```

---

### 5. API 配置（next_api_config）- 進階

**UI 元件**: Collapsible Section + JSON Editor
**顯示條件**: next_action = 'api_call' 或 'form_then_api'
**必填**: 否（有預設值）

```html
<div v-if="needsApiConfig" class="form-group">
  <div class="collapsible-header" @click="apiConfigExpanded = !apiConfigExpanded">
    <span>🔧 API 設定（進階）</span>
    <span class="toggle-icon">{{ apiConfigExpanded ? '▼' : '▶' }}</span>
  </div>

  <div v-if="apiConfigExpanded" class="collapsible-content">
    <div class="form-group">
      <label>API 端點</label>
      <select v-model="apiEndpoint" class="form-control">
        <option value="maintenance_request">維修派工 API</option>
        <option value="billing_inquiry">帳單查詢 API</option>
        <option value="custom">自訂...</option>
      </select>
    </div>

    <div class="form-group">
      <label>預設參數（JSON 格式）</label>
      <textarea
        v-model="apiParamsJson"
        class="form-control code-editor"
        rows="8"
        placeholder='{
  "problem_category": "ac_maintenance",
  "specific_problem": "ac_not_starting",
  "urgency_level": "urgent"
}'
      ></textarea>
      <p class="hint">
        ℹ️ 這些參數會預先填入表單，減少用戶輸入。支援變數：
        <code>{{user_id}}</code>, <code>{{vendor_id}}</code>
      </p>
    </div>

    <!-- 快速範本 -->
    <div class="api-templates">
      <span class="label">範本：</span>
      <button type="button" @click="useApiTemplate('ac_maintenance')" class="btn-tag">
        冷氣維修
      </button>
      <button type="button" @click="useApiTemplate('water_leak')" class="btn-tag">
        漏水問題
      </button>
      <button type="button" @click="useApiTemplate('door_lock')" class="btn-tag">
        門鎖問題
      </button>
    </div>
  </div>
</div>
```

---

### 6. 效果預覽（選填）

```html
<div v-if="editingForm.next_action !== 'none'" class="preview-section">
  <h4>📝 效果預覽</h4>
  <div class="conversation-preview">
    <div class="message user">
      <div class="avatar">👤</div>
      <div class="bubble">{{ editingForm.item_name || '問題描述' }}</div>
    </div>

    <div class="message bot">
      <div class="avatar">🤖</div>
      <div class="bubble" v-html="formatSOPContent(editingForm.content)"></div>
    </div>

    <div class="message user">
      <div class="avatar">👤</div>
      <div class="bubble">{{ firstTriggerKeyword || '觸發關鍵詞' }}</div>
    </div>

    <div class="message bot">
      <div class="avatar">🤖</div>
      <div class="bubble">{{ editingForm.followup_prompt || '引導語' }}</div>
    </div>

    <div class="message bot form-indicator">
      <div class="avatar">📋</div>
      <div class="bubble">
        開始填寫「{{ selectedFormName }}」
      </div>
    </div>
  </div>
</div>
```

---

## 💻 前端實作重點

### VendorSOPManager.vue 修改

#### 1. Data 新增欄位

```javascript
editingForm: {
  id: null,
  item_name: '',
  content: '',

  // 新增欄位
  next_action: 'none',
  next_form_id: null,
  next_api_config: null,
  trigger_keywords: [],
  followup_prompt: ''
},

// UI 狀態
triggerKeywordsText: '',  // textarea 繫結（換行分隔）
apiEndpoint: 'maintenance_request',
apiParamsJson: '{}',
apiConfigExpanded: false,

// 可用的表單選項
availableForms: []
```

#### 2. Computed Properties

```javascript
computed: {
  needsFormSelection() {
    return ['form_fill', 'form_then_api'].includes(this.editingForm.next_action);
  },

  needsTriggerKeywords() {
    return this.editingForm.next_action !== 'none';
  },

  needsFollowupPrompt() {
    return this.editingForm.next_action !== 'none';
  },

  needsApiConfig() {
    return ['api_call', 'form_then_api'].includes(this.editingForm.next_action);
  },

  firstTriggerKeyword() {
    const keywords = this.triggerKeywordsText.split('\n').filter(k => k.trim());
    return keywords[0] || '';
  },

  selectedFormName() {
    const form = this.availableForms.find(f => f.form_id === this.editingForm.next_form_id);
    return form ? form.form_name : '';
  }
}
```

#### 3. Methods

```javascript
methods: {
  async loadAvailableForms() {
    try {
      const response = await axios.get(`${API_BASE_URL}/form-schemas?vendor_id=${this.vendorId}`);
      this.availableForms = response.data;
    } catch (error) {
      console.error('載入表單列表失敗:', error);
    }
  },

  editSOP(sop) {
    this.editingForm = {
      id: sop.id,
      item_name: sop.item_name,
      content: sop.content,
      next_action: sop.next_action || 'none',
      next_form_id: sop.next_form_id,
      next_api_config: sop.next_api_config,
      trigger_keywords: sop.trigger_keywords || [],
      followup_prompt: sop.followup_prompt || ''
    };

    // 轉換陣列為換行文字
    this.triggerKeywordsText = (sop.trigger_keywords || []).join('\n');

    // 解析 API 配置
    if (sop.next_api_config) {
      this.apiEndpoint = sop.next_api_config.endpoint || 'maintenance_request';
      this.apiParamsJson = JSON.stringify(sop.next_api_config.params || {}, null, 2);
    }

    this.showEditModal = true;
  },

  async saveSOP() {
    // 轉換換行文字為陣列
    const keywords = this.triggerKeywordsText
      .split('\n')
      .map(k => k.trim())
      .filter(k => k.length > 0);

    // 構建 API 配置
    let apiConfig = null;
    if (this.needsApiConfig) {
      try {
        apiConfig = {
          endpoint: this.apiEndpoint,
          params: JSON.parse(this.apiParamsJson),
          combine_with_knowledge: false
        };
      } catch (error) {
        alert('API 參數 JSON 格式錯誤');
        return;
      }
    }

    const payload = {
      item_name: this.editingForm.item_name,
      content: this.editingForm.content,
      next_action: this.editingForm.next_action,
      next_form_id: this.needsFormSelection ? this.editingForm.next_form_id : null,
      next_api_config: apiConfig,
      trigger_keywords: this.needsTriggerKeywords ? keywords : [],
      followup_prompt: this.needsFollowupPrompt ? this.editingForm.followup_prompt : null
    };

    try {
      await axios.put(`${RAG_API}/v1/vendors/${this.vendorId}/sop/items/${this.editingForm.id}`, payload);
      alert('儲存成功！');
      this.closeEditModal();
      this.loadMySOP();
    } catch (error) {
      console.error('儲存失敗:', error);
      alert('儲存失敗: ' + (error.response?.data?.detail || error.message));
    }
  },

  // 快速插入關鍵詞
  addKeyword(keyword) {
    const current = this.triggerKeywordsText.trim();
    if (current) {
      this.triggerKeywordsText = current + '\n' + keyword;
    } else {
      this.triggerKeywordsText = keyword;
    }
  },

  // 使用引導語範本
  usePromptTemplate(type) {
    const templates = {
      maintenance: '好的，我來協助您提交維修請求。請提供一些詳細資訊，以便我們安排最合適的維修人員。',
      inquiry: '我會協助您了解這個問題。請提供一些詳細資訊。'
    };
    this.editingForm.followup_prompt = templates[type] || '';
  },

  // 使用 API 參數範本
  useApiTemplate(type) {
    const templates = {
      ac_maintenance: {
        problem_category: 'ac_maintenance',
        urgency_level: 'urgent'
      },
      water_leak: {
        problem_category: 'water_leak',
        urgency_level: 'critical'
      },
      door_lock: {
        problem_category: 'door_lock',
        urgency_level: 'urgent'
      }
    };
    this.apiParamsJson = JSON.stringify(templates[type] || {}, null, 2);
  }
}
```

---

## 🎨 CSS 樣式建議

```css
/* 後續動作選項 */
.radio-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.radio-option {
  display: flex;
  align-items: flex-start;
  padding: 16px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.radio-option:hover {
  border-color: #2196F3;
  background: #f5f5f5;
}

.radio-option input[type="radio"] {
  margin-top: 4px;
  margin-right: 12px;
}

.radio-option input[type="radio"]:checked ~ .radio-content {
  color: #2196F3;
}

.radio-option.recommended {
  border-color: #4CAF50;
  background: #f1f8f4;
}

.radio-content strong {
  display: block;
  margin-bottom: 4px;
}

.radio-content p {
  margin: 0;
  color: #666;
  font-size: 0.9em;
}

/* 快速插入按鈕 */
.quick-keywords,
.quick-templates,
.api-templates {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.quick-keywords .label,
.quick-templates .label,
.api-templates .label {
  font-size: 0.9em;
  color: #666;
}

.btn-tag {
  padding: 4px 12px;
  border: 1px solid #ddd;
  border-radius: 16px;
  background: white;
  cursor: pointer;
  font-size: 0.85em;
  transition: all 0.2s;
}

.btn-tag:hover {
  border-color: #2196F3;
  background: #e3f2fd;
  color: #2196F3;
}

/* 可折疊區塊 */
.collapsible-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f5f5f5;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 8px;
}

.collapsible-header:hover {
  background: #e0e0e0;
}

.toggle-icon {
  color: #666;
  font-size: 0.8em;
}

.collapsible-content {
  padding: 16px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  margin-bottom: 16px;
}

/* 程式碼編輯器樣式 */
.code-editor {
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 0.9em;
  background: #f8f8f8;
  border: 1px solid #ddd;
}

/* 對話預覽 */
.conversation-preview {
  background: #f9f9f9;
  padding: 16px;
  border-radius: 8px;
  max-width: 600px;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.message.user {
  flex-direction: row-reverse;
}

.message .avatar {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2em;
  flex-shrink: 0;
}

.message .bubble {
  background: white;
  padding: 12px 16px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  max-width: 70%;
}

.message.user .bubble {
  background: #2196F3;
  color: white;
}

.message.bot.form-indicator .bubble {
  background: #4CAF50;
  color: white;
}
```

---

## 📦 後端 API 調整

### 需要修改的 API Endpoint

**PUT** `/v1/vendors/{vendor_id}/sop/items/{item_id}`

新增欄位到 request body schema：

```python
class VendorSOPItemUpdate(BaseModel):
    item_name: Optional[str]
    content: Optional[str]

    # 新增欄位
    next_action: Optional[str] = 'none'
    next_form_id: Optional[str] = None
    next_api_config: Optional[dict] = None
    trigger_keywords: Optional[List[str]] = []
    followup_prompt: Optional[str] = None
```

### GET 查詢也要包含新欄位

**GET** `/v1/vendors/{vendor_id}/sop/items`

確保 SQL 查詢包含新欄位：

```sql
SELECT
    id, item_name, content,
    next_action, next_form_id, next_api_config,
    trigger_keywords, followup_prompt,
    ...
FROM vendor_sop_items
```

---

## ✅ 實施步驟

### Phase 1: 後端準備（1 天）
1. 執行 migration - 新增欄位到資料庫
2. 修改 API endpoint - 支援新欄位的讀寫
3. 測試 API

### Phase 2: 前端開發（2 天）
4. 修改 VendorSOPManager.vue - 新增 UI 元件
5. 實作資料綁定和驗證邏輯
6. 新增 CSS 樣式
7. 實作快速插入和範本功能

### Phase 3: 測試與優化（1 天）
8. 端到端測試
9. UI/UX 優化
10. 錯誤處理完善

---

## 🎯 成功指標

1. ✅ 非技術人員可以在 5 分鐘內完成一個 SOP 的後續動作配置
2. ✅ 介面直觀，不需要查看文檔就能理解每個欄位的作用
3. ✅ 配置錯誤時有清楚的提示訊息
4. ✅ 配置完成後可以立即預覽效果

---

**文檔版本**: 1.0
**最後更新**: 2026-01-22
