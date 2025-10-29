# Ultrathink 深度分析：平台 SOP「說明/群組」欄位缺失問題

**分析時間**: 2025-10-29
**問題來源**: 用戶在 `http://localhost:8087/platform-sop/universal/edit` 頁面看不到「說明」欄位
**問題類型**: 前端 UI 功能缺失

---

## 一、問題定位

### 1.1 用戶反饋

> 「但我在 http://localhost:8087/platform-sop/universal/edit 沒看到原說明欄」

**翻譯**：
- 用戶在平台 SOP 通用範本編輯頁面
- 看不到「說明」（即 `platform_sop_groups.group_name`）欄位
- 期望能夠在新增/編輯 SOP 項目時選擇或創建「群組/說明」

### 1.2 數據結構回顧

**資料庫結構（3 層）**：
```
platform_sop_categories (分類)
  ↓
platform_sop_groups (說明/群組) ← 這層缺少管理 UI！
  ↓
platform_sop_templates (應備欄位/項目)
```

**Excel 對應關係**：
```
分類 → platform_sop_categories.category_name
說明 → platform_sop_groups.group_name ← 缺失！
應備欄位 → platform_sop_templates.item_name
JGB範本 → platform_sop_templates.content
```

### 1.3 現狀分析

**後端 API 現狀**：
| 功能 | Categories | Groups | Templates |
|------|------------|--------|-----------|
| GET (List) | ✅ /categories | ✅ /groups | ✅ /templates |
| POST (Create) | ✅ /categories | ❌ 缺失 | ✅ /templates |
| PUT (Update) | ❌ 缺失 | ❌ 缺失 | ✅ /templates/{id} |
| DELETE | ❌ 缺失 | ❌ 缺失 | ✅ /templates/{id} |

**前端 UI 現狀（PlatformSOPEditView.vue）**：

編輯表單欄位：
- ✅ 所屬分類 (category_id) - Line 138-146
- ❌ **所屬群組 (group_id) - 缺失！**
- ✅ 項次編號 (item_number) - Line 148-152
- ✅ 優先級 (priority) - Line 154-158
- ✅ 項目名稱 (item_name) - Line 160-163
- ✅ 範本內容 (content) - Line 165-169
- ✅ 關聯意圖 (intent_ids) - Line 176-191
- ✅ 範本說明 (template_notes) - Line 198-202
- ✅ 自訂提示 (customization_hint) - Line 204-208

`templateForm` 數據結構（Line 369-379）：
```javascript
templateForm: {
  category_id: null,
  business_type: null,
  item_number: 1,
  item_name: '',
  content: '',
  intent_ids: [],
  priority: 50,
  template_notes: '',
  customization_hint: ''
  // ❌ 缺少 group_id!
}
```

---

## 二、問題根因分析

### 2.1 為什麼會缺失？

**時間線推測**：
1. **初始設計（2 層結構）**：
   - 最初系統可能只有 Categories → Templates 兩層
   - 表單設計時沒有 group_id 欄位

2. **數據結構升級（3 層結構）**：
   - 後期在資料庫中添加了 `platform_sop_groups` 表
   - 添加了 GET `/groups` API 端點
   - **但前端 UI 沒有同步更新！**

3. **數據遷移**：
   - 部分模板（ID 1-28）被分配到群組
   - 但沒有提供 UI 來管理這個分配關係

### 2.2 影響範圍

**受影響功能**：
1. ❌ 無法在前端UI新增/編輯模板時選擇群組
2. ❌ 無法在前端UI創建新群組
3. ❌ 無法在前端UI編輯群組信息
4. ❌ 無法在前端UI刪除群組
5. ⚠️  新增的模板 `group_id` 會是 NULL
6. ⚠️  編輯現有模板時，會丟失 `group_id` 信息

**數據一致性風險**：
- 通過前端新增的模板 → `group_id = NULL`
- 通過SQL腳本導入的模板 → `group_id = [有值]`
- 導致數據結構不一致

---

## 三、完整解決方案設計

### 3.1 後端 API 設計

#### API 1: 創建群組
```http
POST /api/v1/platform/sop/groups
Content-Type: application/json

{
  "category_id": 1,
  "group_name": "租賃申請流程：介紹如何申請租賃、所需文件、申請時間等。",
  "description": "詳細描述...",
  "display_order": 1
}

Response 201:
{
  "id": 10,
  "category_id": 1,
  "group_name": "...",
  "description": "...",
  "display_order": 1,
  "template_count": 0,
  "is_active": true,
  "created_at": "2025-10-29T..."
}
```

#### API 2: 更新群組
```http
PUT /api/v1/platform/sop/groups/{group_id}
Content-Type: application/json

{
  "group_name": "更新後的名稱",
  "description": "更新後的描述",
  "display_order": 2
}

Response 200:
{
  "id": 10,
  "category_id": 1,
  "group_name": "更新後的名稱",
  ...
}
```

#### API 3: 刪除群組
```http
DELETE /api/v1/platform/sop/groups/{group_id}

Response 200:
{
  "message": "群組已刪除",
  "deleted_group_id": 10,
  "moved_templates_count": 5  # 關聯的模板被移到其他群組或設為NULL
}
```

#### API 4: 依分類查詢群組（已存在，可能需優化）
```http
GET /api/v1/platform/sop/groups?category_id=1

Response 200:
{
  "groups": [
    {
      "id": 1,
      "category_id": 1,
      "group_name": "租賃申請流程：介紹如何申請租賃、所需文件、申請時間等。",
      "description": "...",
      "display_order": 1,
      "template_count": 4,
      "is_active": true
    },
    ...
  ]
}
```

### 3.2 前端 UI 設計

#### 修改 1: 表單添加「群組」欄位

**位置**: `PlatformSOPEditView.vue` Line 138-146 之後

```vue
<div class="form-group">
  <label>所屬分類 *</label>
  <select v-model.number="templateForm.category_id" required class="form-control">
    <option :value="null">請選擇分類</option>
    <option v-for="cat in categories" :key="cat.id" :value="cat.id">
      {{ cat.category_name }}
    </option>
  </select>
</div>

<!-- ✨ 新增：群組選擇欄位 -->
<div class="form-group" v-if="templateForm.category_id">
  <label>
    所屬群組（說明）
    <button
      type="button"
      @click="showCreateGroupModal = true"
      class="btn-inline btn-sm btn-success"
      title="為此分類新增群組"
    >
      ➕ 新增群組
    </button>
  </label>
  <select v-model.number="templateForm.group_id" class="form-control">
    <option :value="null">（未分組）</option>
    <option v-for="group in availableGroups" :key="group.id" :value="group.id">
      {{ group.group_name }} ({{ group.template_count || 0 }} 個項目)
    </option>
  </select>
  <small class="form-hint">群組用於將同類型的 SOP 項目分組顯示</small>
</div>
```

**數據綁定**：
```javascript
data() {
  return {
    // 現有...
    groups: [],  // 所有群組列表
    availableGroups: [],  // 當前分類的可用群組
    showCreateGroupModal: false,

    // 群組表單
    groupForm: {
      category_id: null,
      group_name: '',
      description: '',
      display_order: 1
    },

    // 模板表單（修改）
    templateForm: {
      category_id: null,
      group_id: null,  // ✨ 新增
      business_type: null,
      item_number: 1,
      item_name: '',
      content: '',
      intent_ids: [],
      priority: 50,
      template_notes: '',
      customization_hint: ''
    }
  }
},

watch: {
  'templateForm.category_id'(newCategoryId) {
    // 當選擇分類時，載入該分類的群組
    if (newCategoryId) {
      this.loadGroupsByCategory(newCategoryId);
      this.templateForm.item_number = this.getNextItemNumber(newCategoryId);
      this.templateForm.group_id = null;  // 重置群組選擇
    } else {
      this.availableGroups = [];
    }
  }
}
```

#### 修改 2: 新增群組管理 Modal

**位置**: `PlatformSOPEditView.vue` Line 275 之後

```vue
<!-- 新增/編輯群組 Modal -->
<div v-if="showCreateGroupModal" class="modal-overlay" @click="showCreateGroupModal = false">
  <div class="modal-content" @click.stop>
    <h2>{{ editingGroup ? '編輯群組' : '新增群組' }}</h2>
    <p class="modal-description">群組用於將同類型的 SOP 項目分組，對應 Excel 中的「說明」欄位</p>

    <form @submit.prevent="saveGroup">
      <div class="form-group">
        <label>群組名稱（說明）*</label>
        <textarea
          v-model="groupForm.group_name"
          required
          class="form-control"
          rows="2"
          placeholder="例如：租賃申請流程：介紹如何申請租賃、所需文件、申請時間等。"
        ></textarea>
        <small class="form-hint">建議包含簡要說明，方便業者理解此群組的用途</small>
      </div>

      <div class="form-group">
        <label>詳細描述</label>
        <textarea
          v-model="groupForm.description"
          class="form-control"
          rows="3"
          placeholder="進一步說明此群組包含的內容和適用場景"
        ></textarea>
      </div>

      <div class="form-group">
        <label>顯示順序</label>
        <input
          v-model.number="groupForm.display_order"
          type="number"
          min="1"
          class="form-control"
        />
        <small class="form-hint">數字越小越靠前</small>
      </div>

      <div class="modal-actions">
        <button type="submit" class="btn btn-primary">💾 儲存</button>
        <button type="button" @click="closeCreateGroupModal" class="btn btn-secondary">取消</button>
      </div>
    </form>
  </div>
</div>
```

**相關方法**：
```javascript
methods: {
  // 載入群組列表
  async loadGroups() {
    try {
      const response = await axios.get(`${RAG_API}/api/v1/platform/sop/groups`);
      this.groups = response.data.groups || [];
    } catch (error) {
      console.error('載入群組失敗:', error);
      this.groups = [];
    }
  },

  // 依分類載入群組
  async loadGroupsByCategory(categoryId) {
    try {
      const response = await axios.get(
        `${RAG_API}/api/v1/platform/sop/groups?category_id=${categoryId}`
      );
      this.availableGroups = response.data.groups || [];
    } catch (error) {
      console.error('載入群組失敗:', error);
      this.availableGroups = [];
    }
  },

  // 新增/編輯群組
  async saveGroup() {
    try {
      // 設置當前選中的分類
      this.groupForm.category_id = this.templateForm.category_id;

      if (this.editingGroup) {
        // 更新
        await axios.put(
          `${RAG_API}/api/v1/platform/sop/groups/${this.editingGroup.id}`,
          this.groupForm
        );
        alert('群組已更新');
      } else {
        // 新增
        const response = await axios.post(
          `${RAG_API}/api/v1/platform/sop/groups`,
          this.groupForm
        );
        alert('群組已建立');

        // 自動選中新建的群組
        this.templateForm.group_id = response.data.id;
      }

      this.closeCreateGroupModal();
      await this.loadGroupsByCategory(this.templateForm.category_id);
    } catch (error) {
      console.error('儲存群組失敗:', error);
      alert('儲存群組失敗: ' + (error.response?.data?.detail || error.message));
    }
  },

  closeCreateGroupModal() {
    this.showCreateGroupModal = false;
    this.editingGroup = null;
    this.groupForm = {
      category_id: null,
      group_name: '',
      description: '',
      display_order: 1
    };
  }
}
```

#### 修改 3: 列表顯示優化（可選）

**在模板卡片中顯示群組信息**：

```vue
<div class="template-header">
  <span class="template-number">#{{ template.item_number }}</span>

  <!-- ✨ 新增：顯示群組 -->
  <span v-if="template.group_name" class="badge badge-group">
    📁 {{ template.group_name }}
  </span>

  <h4>{{ template.item_name }}</h4>

  <!-- 意圖 badges... -->
</div>
```

**CSS**：
```css
.badge-group {
  background: #E3F2FD;
  color: #1976D2;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

### 3.3 資料庫欄位完整性

**驗證 platform_sop_templates 表結構**：
```sql
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'platform_sop_templates'
  AND column_name IN ('group_id', 'category_id', 'business_type', 'item_number', 'item_name');
```

**預期結果**：
```
column_name   | data_type | is_nullable | column_default
--------------+-----------+-------------+---------------
category_id   | integer   | NO          | null
group_id      | integer   | YES         | null  ← 允許為空
business_type | varchar   | YES         | null
item_number   | integer   | NO          | null
item_name     | varchar   | NO          | null
```

**約束檢查**：
```sql
SELECT
    conname AS constraint_name,
    contype AS constraint_type,
    pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'platform_sop_templates'::regclass;
```

---

## 四、實作優先級與步驟

### Phase 1: 後端 API 實作（必要）

**優先級**: ⭐⭐⭐⭐⭐ **最高**

**任務清單**：
1. ✅ 驗證資料庫表結構
2. 🔄 實作 `POST /api/v1/platform/sop/groups`
3. 🔄 實作 `PUT /api/v1/platform/sop/groups/{id}`
4. 🔄 實作 `DELETE /api/v1/platform/sop/groups/{id}`
5. 🔄 優化 `GET /api/v1/platform/sop/groups` 支持 category_id 過濾
6. 🔄 修改 `POST /PUT /api/v1/platform/sop/templates` 支持 group_id

**預計時間**: 2-3 小時

### Phase 2: 前端 UI 修改（必要）

**優先級**: ⭐⭐⭐⭐⭐ **最高**

**任務清單**：
1. 修改 `templateForm` 添加 `group_id`
2. 添加「群組選擇」下拉選單
3. 實作 `loadGroupsByCategory()` 方法
4. 添加「新增群組」按鈕和 Modal
5. 實作群組保存邏輯
6. 修改 `saveTemplate()` 包含 `group_id`

**預計時間**: 2-3 小時

### Phase 3: 群組管理功能（建議）

**優先級**: ⭐⭐⭐ **中等**

**任務清單**：
1. 添加群組列表頁面（可選，可在分類頁面管理）
2. 支持編輯群組
3. 支持刪除群組（需處理關聯的模板）
4. 批量操作（移動模板到其他群組）

**預計時間**: 3-4 小時

### Phase 4: UI 優化（可選）

**優先級**: ⭐⭐ **低**

**任務清單**：
1. 在列表中顯示群組信息
2. 支持按群組篩選
3. 支持群組折疊/展開（已有分類折疊，可添加群組層）
4. 拖放排序

**預計時間**: 2-3 小時

---

## 五、資料遷移與兼容性

### 5.1 現有資料處理

**問題**: 現有的 28 個模板已經有 `group_id`，但新增的模板會是 NULL

**方案 1**: 強制要求選擇群組（推薦）
```javascript
// 表單驗證
if (!this.templateForm.group_id) {
  alert('請選擇所屬群組，或先創建新群組');
  return;
}
```

**方案 2**: 允許未分組
```javascript
// 允許 group_id = NULL
// 但在列表中標記為「未分組」
```

**建議**: 採用方案 2（允許未分組），但在 UI 中提示用戶最好選擇群組

### 5.2 回測與驗證

**測試用例**：
1. ✅ 新增模板時選擇群組
2. ✅ 新增模板時不選擇群組（group_id = NULL）
3. ✅ 編輯現有模板，修改群組
4. ✅ 新增群組
5. ✅ 刪除群組（有模板關聯）
6. ✅ 刪除群組（無模板關聯）

---

## 六、風險評估與緩解

### 6.1 潛在風險

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| 資料不一致 | 中 | 添加資料驗證，確保 `group_id` 對應的 `category_id` 一致 |
| 刪除群組導致模板孤立 | 中 | 刪除群組前檢查關聯模板數量，提示用戶 |
| API 變更破壞現有功能 | 低 | `group_id` 為可選欄位，不影響現有 API |
| 前端表單過於複雜 | 低 | 使用級聯選擇，簡化操作流程 |

### 6.2 數據一致性約束（建議添加）

```sql
-- 確保 group_id 對應的 category_id 一致
ALTER TABLE platform_sop_templates
ADD CONSTRAINT check_group_category_consistency
CHECK (
  group_id IS NULL OR
  EXISTS (
    SELECT 1 FROM platform_sop_groups g
    WHERE g.id = group_id AND g.category_id = platform_sop_templates.category_id
  )
);
```

**註**：這個約束可能影響性能，建議在應用層驗證。

---

## 七、結論與建議

### 7.1 問題總結

✅ **已確認**：
1. 資料庫結構完整（3 層：Categories → Groups → Templates）
2. 後端有 GET `/groups` API
3. 前端表單缺少 `group_id` 欄位
4. 現有 28 個模板已正確分配群組
5. 新增模板時 `group_id` 會是 NULL

### 7.2 最小可行方案（MVP）

**Phase 1 only**（4-6 小時）：
1. ✅ 實作群組 CRUD API
2. ✅ 前端表單添加群組選擇欄位
3. ✅ 支持創建新群組

**效果**：
- 用戶可以在新增/編輯模板時選擇群組
- 用戶可以創建新群組
- 解決「看不到說明欄」的問題

### 7.3 完整方案（MVP + Phase 2-4）

**預計時間**: 10-15 小時

**效果**：
- 完整的群組管理功能
- 優化的列表顯示
- 批量操作支持

### 7.4 立即行動

**建議**：先實作 Phase 1，解決用戶當前遇到的問題

**開始執行**：
```bash
# 1. 修改後端 API (platform_sop.py)
# 2. 修改前端表單 (PlatformSOPEditView.vue)
# 3. 測試驗證
# 4. Commit 提交
```

---

**分析完成時間**: 2025-10-29
**結論**: 問題根因明確，解決方案清晰，建議立即執行 Phase 1 🚀
