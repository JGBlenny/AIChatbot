# 知識庫管理 - Audience 選擇器改進

## 概述

基於最近的 Business Scope 重構（基於 user_role 動態決定 B2B/B2C 場景），本次改進優化了知識庫管理頁面的「對象（audience）」選擇器，讓使用者在新增或編輯知識時，能清楚了解該知識將在哪些業務場景中被使用。

## 改進內容

### 1. 分組式 Audience 選擇器

將原本扁平的選項列表改為分組顯示，清楚區分不同業務範圍：

#### 🏠 B2C - 終端用戶（External）
- **租客** - 租客直接使用業者 AI 客服
- **房東** - 房東直接使用業者 AI 客服
- **租客|管理師** - 混合場景（B2C + B2B）
- **房東|租客** - 房東和租客共用
- **房東|租客|管理師** - 所有終端用戶和管理師

#### 🏢 B2B - 內部管理（Internal）
- **管理師** - 業者員工使用內部系統
- **系統管理員** - 系統管理員專用
- **房東/管理師** - 房東相關的內部管理

#### 📌 通用
- **general (所有人)** - 不區分業務範圍，所有場景都可見

### 2. 即時提示文字

選擇 audience 後，會在下方顯示清晰的提示，說明該知識將在哪些場景中被使用：

```
💡 B2C - 租客使用業者 AI 客服時可見（user_role=customer + external scope）
💡 B2B - 業者員工使用內部系統時可見（user_role=staff + internal scope）
💡 B2C + B2B - 租客和管理師都可見（混合場景）
```

### 3. 視覺設計優化

- 使用藍色提示框（`#ecf5ff` 背景 + `#409EFF` 邊框）
- 左側藍色邊條突出顯示
- 適當的內距和圓角，提升閱讀體驗

## 技術實作

### 前端變更

**檔案：** `knowledge-admin/frontend/src/views/KnowledgeView.vue`

#### 1. 模板更新

```vue
<div class="form-group">
  <label>對象 *</label>
  <select v-model="formData.audience" required @change="onAudienceChange">
    <option value="">請選擇</option>
    <optgroup label="🏠 B2C - 終端用戶（External）">
      <option value="租客">租客</option>
      <option value="房東">房東</option>
      ...
    </optgroup>
    <optgroup label="🏢 B2B - 內部管理（Internal）">
      <option value="管理師">管理師</option>
      ...
    </optgroup>
    <optgroup label="📌 通用">
      <option value="general">所有人（通用）</option>
    </optgroup>
  </select>
  <small class="audience-hint">💡 {{ audienceHint }}</small>
</div>
```

#### 2. 新增響應式邏輯

```javascript
data() {
  return {
    // ...
    audienceHint: '選擇對象後將顯示適用場景'
  };
},
methods: {
  onAudienceChange() {
    const audienceHints = {
      '租客': 'B2C - 租客使用業者 AI 客服時可見（user_role=customer + external scope）',
      '房東': 'B2C - 房東使用業者 AI 客服時可見（user_role=customer + external scope）',
      '租客|管理師': 'B2C + B2B - 租客和管理師都可見（混合場景）',
      '房東|租客': 'B2C - 房東和租客都可見（user_role=customer + external scope）',
      '房東|租客|管理師': 'B2C + B2B - 所有終端用戶和管理師都可見',
      '管理師': 'B2B - 業者員工使用內部系統時可見（user_role=staff + internal scope）',
      '系統管理員': 'B2B - 系統管理員專用（user_role=staff + internal scope）',
      '房東/管理師': 'B2B - 房東相關的內部管理（user_role=staff + internal scope）',
      'general': '通用 - 所有業務範圍都可見（B2C 和 B2B）'
    };

    this.audienceHint = audienceHints[this.formData.audience] || '選擇對象後將顯示適用場景';
  },

  // 在編輯知識時也觸發提示更新
  async editKnowledge(item) {
    // ... 載入知識資料 ...

    // 更新 audience 提示
    this.onAudienceChange();

    this.showModal = true;
  }
}
```

#### 3. CSS 樣式

```css
.audience-hint {
  display: block;
  margin-top: 6px;
  color: #409EFF;
  font-size: 12px;
  line-height: 1.5;
  font-style: italic;
  padding: 6px 10px;
  background: #ecf5ff;
  border-radius: 4px;
  border-left: 3px solid #409EFF;
}
```

## 與 Business Scope 架構的整合

本改進與 Business Scope 重構完美整合：

### 1. 業務範圍映射

對應後端的 `business_scope_utils.py`：

```python
BUSINESS_SCOPE_AUDIENCE_MAPPING = {
    'external': {
        'allowed_audiences': ['租客', '房東', 'tenant', 'general', ...]
    },
    'internal': {
        'allowed_audiences': ['管理師', '系統管理員', 'general', ...]
    }
}
```

### 2. User Role 對應

- **user_role=customer** → business_scope=external → 可見 B2C 受眾（租客、房東）
- **user_role=staff** → business_scope=internal → 可見 B2B 受眾（管理師、系統管理員）
- **audience=general** → 所有 business_scope 都可見

### 3. 知識檢索流程

```
1. 使用者發起對話，帶上 user_role (customer/staff)
2. 系統根據 user_role 決定 business_scope (external/internal)
3. RAG 引擎使用 business_scope 過濾 audience
4. 只返回符合當前業務範圍的知識
```

## 使用情境範例

### 情境 1：B2C 租客諮詢

- **user_role**: customer
- **business_scope**: external
- **可見 audience**: 租客、房東、租客|管理師、房東|租客、房東|租客|管理師、general

### 情境 2：B2B 業者員工查詢

- **user_role**: staff
- **business_scope**: internal
- **可見 audience**: 管理師、系統管理員、租客|管理師、房東|租客|管理師、房東/管理師、general

### 情境 3：通用知識

- **audience**: general
- **可見於**: 所有 business_scope（不論 user_role）

## 優勢

### 1. 語意更清晰
- 使用者一眼就能看出知識適用的業務場景
- 分組顯示讓選擇邏輯更直觀

### 2. 減少錯誤
- 即時提示幫助使用者理解 audience 的影響
- 避免錯誤配置導致知識無法被正確檢索

### 3. 符合架構設計
- 與 Business Scope 重構的設計理念一致
- 前後端邏輯完美對應

### 4. 易於維護
- 提示文字集中在一個 mapping object
- 未來新增 audience 類型只需更新此 mapping

## 測試結果

### 前端建置
```bash
✓ 113 modules transformed
✓ built in 1.04s
```

### 功能測試
- ✅ 新增知識：audience 選擇器正常顯示分組和提示
- ✅ 編輯知識：載入現有 audience 並顯示對應提示
- ✅ 提示文字：隨著 audience 選擇即時更新
- ✅ 視覺效果：提示框樣式正確顯示

## 後續建議

### 短期
1. 在業者配置頁面也添加類似的 business_scope 說明
2. 在聊天測試頁面顯示當前使用的 business_scope

### 中期
1. 增加「預覽知識可見範圍」功能
2. 在知識列表頁面用顏色標記不同 audience

### 長期
1. 支援更細粒度的 audience 組合
2. 提供 audience 使用統計和建議

## 相關文件

- [Business Scope 重構總結](./docs/BUSINESS_SCOPE_REFACTORING_SUMMARY.md)
- [Business Scope 詳細說明](./docs/architecture/BUSINESS_SCOPE_REFACTORING.md)
- [業務範圍工具](./rag-orchestrator/services/business_scope_utils.py)
- [認證與業務範圍整合](./docs/architecture/AUTH_AND_BUSINESS_SCOPE.md)

---

**實作日期**: 2025-10-12
**影響範圍**: 前端 - 知識庫管理頁面
**建置狀態**: ✅ 成功
**測試狀態**: ✅ 通過
