# 移除業者管理頁面的業務範圍欄位

## 背景

根據 Business Scope 重構（commit 87697ce），業務範圍（business_scope）現在是**請求層級動態決定**的，不再是業者的固定屬性。系統會根據 `user_role` 參數自動決定：
- `user_role=customer` → `business_scope=external` (B2C)
- `user_role=staff` → `business_scope=internal` (B2B)

因此，業者管理頁面中的「業務範圍」欄位已經不再需要，應該移除。

## 變更內容

### 檔案: `knowledge-admin/frontend/src/views/VendorManagementView.vue`

**變更統計**: 7 insertions(+), 46 deletions(-)

### 1. 移除表格中的業務範圍欄位

#### 變更前:
```vue
<thead>
  <tr>
    <th width="60">ID</th>
    <th width="120">代碼</th>
    <th>名稱</th>
    <th>簡稱</th>
    <th width="120">業務範圍</th>  ← 移除
    <th>聯絡電話</th>
    <th>訂閱方案</th>
    <th width="80">狀態</th>
    <th width="280">操作</th>
  </tr>
</thead>

<tbody>
  <tr v-for="vendor in vendorList" :key="vendor.id">
    ...
    <td>{{ vendor.short_name || '-' }}</td>
    <td>  ← 移除
      <span class="badge" :class="'scope-' + vendor.business_scope_name">
        {{ getScopeLabel(vendor.business_scope_name) }}
      </span>
    </td>
    <td>{{ vendor.contact_phone || '-' }}</td>
    ...
  </tr>
</tbody>
```

#### 變更後:
```vue
<thead>
  <tr>
    <th width="60">ID</th>
    <th width="120">代碼</th>
    <th>名稱</th>
    <th>簡稱</th>
    <th>聯絡電話</th>
    <th>訂閱方案</th>
    <th width="80">狀態</th>
    <th width="280">操作</th>
  </tr>
</thead>

<tbody>
  <tr v-for="vendor in vendorList" :key="vendor.id">
    ...
    <td>{{ vendor.short_name || '-' }}</td>
    <td>{{ vendor.contact_phone || '-' }}</td>
    ...
  </tr>
</tbody>
```

### 2. 移除新增/編輯表單中的業務範圍欄位

#### 變更前:
```vue
<div class="form-row">
  <div class="form-group">  ← 移除整個欄位
    <label>業務範圍 *</label>
    <select v-model="formData.business_scope_name" required>
      <option value="external">external - 業者對終端用戶（租客、房東）</option>
      <option value="internal">internal - 系統商對業者（後台管理）</option>
    </select>
    <small style="color: #909399; display: block; margin-top: 5px;">
      💡 大部分業者使用 external（對外服務），internal 用於系統商內部管理功能
    </small>
  </div>

  <div class="form-group">
    <label>訂閱方案</label>
    <select v-model="formData.subscription_plan">
      <option value="basic">Basic - 基礎方案</option>
      <option value="standard">Standard - 標準方案</option>
      <option value="premium">Premium - 進階方案</option>
    </select>
  </div>
</div>
```

#### 變更後:
```vue
<div class="form-group">
  <label>訂閱方案</label>
  <select v-model="formData.subscription_plan">
    <option value="basic">Basic - 基礎方案</option>
    <option value="standard">Standard - 標準方案</option>
    <option value="premium">Premium - 進階方案</option>
  </select>
</div>
```

### 3. 移除 JavaScript 中的 business_scope_name

#### 變更: data()
```javascript
// 變更前
formData: {
  code: '',
  name: '',
  short_name: '',
  contact_phone: '',
  contact_email: '',
  address: '',
  business_scope_name: 'external',  ← 移除
  subscription_plan: 'basic',
  is_active: true
}

// 變更後
formData: {
  code: '',
  name: '',
  short_name: '',
  contact_phone: '',
  contact_email: '',
  address: '',
  subscription_plan: 'basic',
  is_active: true
}
```

#### 變更: showCreateModal()
```javascript
// 移除 business_scope_name: 'external'
this.formData = {
  code: '',
  name: '',
  short_name: '',
  contact_phone: '',
  contact_email: '',
  address: '',
  // business_scope_name: 'external',  ← 移除
  subscription_plan: 'basic',
  is_active: true
};
```

#### 變更: editVendor()
```javascript
// 移除 business_scope_name 的載入
this.formData = {
  code: vendor.code,
  name: vendor.name,
  short_name: vendor.short_name || '',
  contact_phone: vendor.contact_phone || '',
  contact_email: vendor.contact_email || '',
  address: vendor.address || '',
  // business_scope_name: vendor.business_scope_name || 'external',  ← 移除
  subscription_plan: vendor.subscription_plan,
  is_active: vendor.is_active
};
```

#### 變更: saveVendor()
```javascript
// 更新 API 請求，移除 business_scope_name
await axios.put(`${RAG_API}/vendors/${this.editingItem.id}`, {
  name: this.formData.name,
  short_name: this.formData.short_name,
  contact_phone: this.formData.contact_phone,
  contact_email: this.formData.contact_email,
  address: this.formData.address,
  // business_scope_name: this.formData.business_scope_name,  ← 移除
  subscription_plan: this.formData.subscription_plan,
  is_active: this.formData.is_active,
  updated_by: 'admin'
});
```

#### 變更: methods
```javascript
// 移除 getScopeLabel() 方法
/*
getScopeLabel(scope) {
  const labels = {
    external: '對外服務',
    internal: '內部管理'
  };
  return labels[scope] || scope;
},
*/
```

### 4. 移除相關 CSS 樣式

```css
/* 移除以下樣式 */
/*
.badge.scope-external {
  background: #67C23A;
}

.badge.scope-internal {
  background: #E6A23C;
}
*/
```

## 測試結果

### 前端建置
```bash
✓ 113 modules transformed
✓ built in 817ms
```

### 功能測試
- ✅ 業者列表頁面：業務範圍欄位已移除
- ✅ 新增業者：表單中無業務範圍選項
- ✅ 編輯業者：表單中無業務範圍選項
- ✅ API 請求：不再發送 business_scope_name 參數
- ✅ 頁面渲染：無 JavaScript 錯誤

## 與 Business Scope 重構的對應

### 後端變更（已完成）
根據 commit 87697ce，後端已經完成以下變更：

1. **資料庫**:
   - Migration 27: 移除 `vendors.business_scope_name` 欄位

2. **API**:
   - `POST /api/v1/vendors` - 不再接受 `business_scope_name`
   - `PUT /api/v1/vendors/{id}` - 不再接受 `business_scope_name`
   - `GET /api/v1/vendors` - Response 不再包含 `business_scope_name`

3. **Chat API**:
   - `POST /api/v1/chat` - 需要提供 `user_role` (必填)
   - `POST /api/v1/message` - 需要提供 `user_role` (預設 "customer")

### 前端變更（本次完成）
- ✅ 業者管理頁面：移除業務範圍欄位
- ✅ 表單邏輯：移除 business_scope_name 處理
- ✅ API 請求：不再發送 business_scope_name

## 業務邏輯說明

### 現在的架構

業務範圍不再是業者的固定屬性，而是**根據使用者角色動態決定**：

```
使用者發起對話
    ↓
前端傳送 user_role
    ↓
後端判斷 business_scope
    ↓
- user_role = "customer" → business_scope = "external" (B2C)
- user_role = "staff"    → business_scope = "internal" (B2B)
    ↓
RAG 引擎根據 business_scope 過濾知識
    ↓
返回適合該業務場景的知識
```

### 優勢

1. **更靈活**: 同一個業者可以同時服務 B2C 和 B2B 場景
2. **語意清晰**: user_role 清楚表達「誰在使用」
3. **簡化管理**: 業者配置更簡單，無需手動選擇業務範圍
4. **符合實際**: 業務範圍是對話層級的屬性，不是業者屬性

## 相關文件

- [Business Scope 重構總結](./docs/BUSINESS_SCOPE_REFACTORING_SUMMARY.md)
- [Business Scope 詳細說明](./docs/architecture/BUSINESS_SCOPE_REFACTORING.md)
- [Business Scope 測試報告](./docs/architecture/BUSINESS_SCOPE_REFACTORING_TEST_REPORT.md)
- [業務範圍工具](./rag-orchestrator/services/business_scope_utils.py)

---

**實作日期**: 2025-10-12
**影響範圍**: 前端 - 業者管理頁面
**變更統計**: 7 insertions(+), 46 deletions(-)
**建置狀態**: ✅ 成功 (817ms)
**測試狀態**: ✅ 通過
