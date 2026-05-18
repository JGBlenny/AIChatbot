# 權限系統 UI 設計文檔

## 📐 介面設計概覽

本文檔詳細說明權限管理系統的前端介面設計，包括頁面布局、組件設計和交互流程。

---

## 🎨 整體風格指南

### 設計原則

1. **直觀易用** - 權限管理操作清晰明了
2. **視覺層次** - 重要功能突出顯示
3. **即時反饋** - 操作後立即顯示結果
4. **防呆設計** - 避免誤操作（如刪除確認）

### 色彩系統

```
主色調：#667eea （紫色）- 主要按鈕、連結
成功：  #48bb78 （綠色）- 成功訊息、啟用狀態
警告：  #f6ad55 （橙色）- 警告訊息
危險：  #f56565 （紅色）- 刪除、停用按鈕
中性：  #718096 （灰色）- 次要文字、邊框
```

---

## 📄 頁面設計

### 1. 角色管理頁面 (RoleManagementView.vue)

#### 頁面布局

```
┌─────────────────────────────────────────────────────────┐
│ 🏠 首頁 > 系統管理 > 角色管理                              │
├─────────────────────────────────────────────────────────┤
│ 角色管理                                   [ + 新增角色 ]  │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 🔍 搜尋角色...              [ 系統角色 ▼ ]          │ │
│ └─────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│ 角色列表                                               │
│ ┌───────┬──────────┬────────────┬────────┬──────────┐ │
│ │ 角色名 │ 說明     │ 權限數量    │ 人數   │ 操作     │ │
│ ├───────┼──────────┼────────────┼────────┼──────────┤ │
│ │ 🔐超級 │ 擁有所有 │ 所有權限   │ 2 人   │ 查看 編輯│ │
│ │ 管理員 │ 權限     │            │        │          │ │
│ │ [系統] │          │            │        │          │ │
│ ├───────┼──────────┼────────────┼────────┼──────────┤ │
│ │ 📚知識 │ 管理知識 │ 15 個權限  │ 5 人   │ 查看 編輯│ │
│ │ 庫管理員│ 庫和意圖 │            │        │ 刪除     │ │
│ │ [系統] │          │            │        │          │ │
│ ├───────┼──────────┼────────────┼────────┼──────────┤ │
│ │ 🧪測試 │ 執行測試 │ 8 個權限   │ 3 人   │ 查看 編輯│ │
│ │ 人員   │ 和回測   │            │        │ 刪除     │ │
│ │ [自訂] │          │            │        │          │ │
│ └───────┴──────────┴────────────┴────────┴──────────┘ │
│                                           第 1/3 頁 ►  │
└─────────────────────────────────────────────────────────┘
```

#### 功能說明

**主要功能**:
- ✅ 角色列表展示（表格）
- ✅ 新增自訂角色
- ✅ 編輯角色權限
- ✅ 刪除自訂角色（系統角色不可刪除）
- ✅ 查看角色詳情（權限列表、成員列表）
- ✅ 搜尋和篩選

**互動行為**:
1. 點擊「新增角色」→ 開啟新增角色彈窗
2. 點擊「編輯」→ 開啟編輯角色彈窗
3. 點擊「刪除」→ 確認對話框
4. 點擊角色名稱 → 查看詳情頁面

---

### 2. 角色詳情/編輯彈窗 (RoleFormModal.vue)

#### 彈窗布局

```
┌─────────────────────────────────────────────────────────┐
│ 📝 編輯角色 - 知識庫管理員                      [ × ]    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 基本資訊                                                 │
│ ┌─────────────────────────────────────────────────────┐│
│ │ 角色名稱 *                                           ││
│ │ ┌─────────────────────────────────────────────────┐││
│ │ │ 知識庫管理員                                     │││
│ │ └─────────────────────────────────────────────────┘││
│ │                                                     ││
│ │ 角色說明                                             ││
│ │ ┌─────────────────────────────────────────────────┐││
│ │ │ 管理知識庫和意圖，包括新增、編輯、刪除等操作       │││
│ │ └─────────────────────────────────────────────────┘││
│ └─────────────────────────────────────────────────────┘│
│                                                         │
│ 權限配置                              [ ✓ 全選 ] [ × 清空 ]│
│ ┌─────────────────────────────────────────────────────┐│
│ │ 📚 知識庫管理                         [ ▼ ]          ││
│ │   ☑ knowledge:view      查看知識                    ││
│ │   ☑ knowledge:create    新增知識                    ││
│ │   ☑ knowledge:edit      編輯知識                    ││
│ │   ☑ knowledge:delete    刪除知識                    ││
│ │   ☑ knowledge:import    匯入知識                    ││
│ │   ☑ knowledge:export    匯出知識                    ││
│ │   ☑ knowledge:reclassify 重新分類                   ││
│ │   ☑ knowledge:review    審核知識                    ││
│ │   ☑ knowledge:ai_review AI 審核                     ││
│ │                                                     ││
│ │ 🎯 意圖管理                           [ ▼ ]          ││
│ │   ☑ intent:view         查看意圖                    ││
│ │   ☑ intent:create       新增意圖                    ││
│ │   ☑ intent:edit         編輯意圖                    ││
│ │   ☑ intent:delete       刪除意圖                    ││
│ │   ☑ intent:suggest      意圖建議                    ││
│ │                                                     ││
│ │ 🧪 測試與回測                         [ ▼ ]          ││
│ │   ☐ test:backtest       執行回測                    ││
│ │   ☐ test:chat           對話測試                    ││
│ │   ☐ test:scenarios      測試情境                    ││
│ │                                                     ││
│ │ 🏢 業者管理                           [ ▼ ]          ││
│ │   ☐ vendor:view         查看業者                    ││
│ │   ☐ vendor:create       新增業者                    ││
│ │   ... (收合)                                        ││
│ └─────────────────────────────────────────────────────┘│
│                                                         │
│ 已選擇 15 個權限                                         │
│                                                         │
│                                   [ 取消 ]  [ 💾 儲存 ] │
└─────────────────────────────────────────────────────────┘
```

#### 功能說明

**表單欄位**:
1. **角色名稱** (必填) - 英文代碼，如 `knowledge_manager`
2. **顯示名稱** (必填) - 中文名稱，如「知識庫管理員」
3. **角色說明** (選填) - 描述角色的職責

**權限選擇器**:
- 按功能分組（可折疊）
- 每組顯示圖標和標題
- 支援全選/清空
- 顯示已選權限數量
- 支援搜尋權限

**驗證規則**:
- 角色名稱：必填，英文和底線，3-50 字元
- 至少選擇 1 個權限

---

### 3. 管理員角色分配 (AdminManagementView.vue 擴展)

在現有的管理員管理頁面中，新增角色分配功能。

#### 修改後的管理員列表

```
┌─────────────────────────────────────────────────────────┐
│ 管理員列表                                               │
│ ┌──────┬──────┬─────────┬──────────┬────────┬────────┐ │
│ │ 帳號  │ 姓名 │ Email   │ 角色      │ 狀態   │ 操作   │ │
│ ├──────┼──────┼─────────┼──────────┼────────┼────────┤ │
│ │ admin│ 系統 │ admin@  │ 🔐 超級   │ ✅ 啟用│ 編輯   │ │
│ │      │ 管理員│ ai...   │ 管理員    │        │        │ │
│ ├──────┼──────┼─────────┼──────────┼────────┼────────┤ │
│ │ john │ John │ john@   │ 📚 知識庫 │ ✅ 啟用│ 編輯   │ │
│ │      │ Wang │ ai...   │ 管理員    │        │ 重設密碼│ │
│ │      │      │         │ 🧪 測試人員│        │ 停用   │ │
│ ├──────┼──────┼─────────┼──────────┼────────┼────────┤ │
│ │ mary │ Mary │ mary@   │ 👁 唯讀   │ ✅ 啟用│ 編輯   │ │
│ │      │ Chen │ ai...   │ 用戶      │        │ 重設密碼│ │
│ │      │      │         │           │        │ 停用   │ │
│ └──────┴──────┴─────────┴──────────┴────────┴────────┘ │
└─────────────────────────────────────────────────────────┘
```

#### 管理員編輯彈窗（新增角色選擇）

```
┌─────────────────────────────────────────────────────────┐
│ 📝 編輯管理員 - john                            [ × ]    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 基本資訊                                                 │
│ ┌─────────────────────────────────────────────────────┐│
│ │ 帳號：john (不可修改)                                 ││
│ │                                                     ││
│ │ 姓名                                                 ││
│ │ ┌─────────────────────────────────────────────────┐││
│ │ │ John Wang                                       │││
│ │ └─────────────────────────────────────────────────┘││
│ │                                                     ││
│ │ Email                                               ││
│ │ ┌─────────────────────────────────────────────────┐││
│ │ │ john@aichatbot.com                              │││
│ │ └─────────────────────────────────────────────────┘││
│ └─────────────────────────────────────────────────────┘│
│                                                         │
│ 角色分配                                                 │
│ ┌─────────────────────────────────────────────────────┐│
│ │ 選擇角色（可多選）：                                   ││
│ │                                                     ││
│ │ ☑ 📚 知識庫管理員                                    ││
│ │    管理知識庫和意圖 (15 個權限)                       ││
│ │                                                     ││
│ │ ☑ 🧪 測試人員                                        ││
│ │    執行測試和回測 (8 個權限)                          ││
│ │                                                     ││
│ │ ☐ 🏢 業者管理員                                      ││
│ │    管理業者設定 (6 個權限)                            ││
│ │                                                     ││
│ │ ☐ ⚙️ 配置管理員                                      ││
│ │    管理系統配置 (5 個權限)                            ││
│ │                                                     ││
│ │ ☐ 👁 唯讀用戶                                         ││
│ │    只能查看資料 (5 個權限)                            ││
│ │                                                     ││
│ │ [ 查看所有權限 ]                                     ││
│ └─────────────────────────────────────────────────────┘│
│                                                         │
│ 狀態                                                     │
│ ┌─────────────────────────────────────────────────────┐│
│ │ ⚫ 啟用   ⚪ 停用                                      ││
│ └─────────────────────────────────────────────────────┘│
│                                                         │
│                                   [ 取消 ]  [ 💾 儲存 ] │
└─────────────────────────────────────────────────────────┘
```

---

### 4. 權限總覽頁面 (PermissionManagementView.vue)

#### 頁面布局

```
┌─────────────────────────────────────────────────────────┐
│ 🏠 首頁 > 系統管理 > 權限管理                              │
├─────────────────────────────────────────────────────────┤
│ 權限管理                                                 │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 🔍 搜尋權限...              [ 資源類型 ▼ ]          │ │
│ └─────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 📚 知識庫管理 (9 個權限)                                  │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ knowledge:view      | 查看知識 | 被 5 個角色使用     │ │
│ │ knowledge:create    | 新增知識 | 被 3 個角色使用     │ │
│ │ knowledge:edit      | 編輯知識 | 被 3 個角色使用     │ │
│ │ knowledge:delete    | 刪除知識 | 被 2 個角色使用     │ │
│ │ knowledge:import    | 匯入知識 | 被 2 個角色使用     │ │
│ │ knowledge:export    | 匯出知識 | 被 2 個角色使用     │ │
│ │ knowledge:reclassify| 重新分類 | 被 2 個角色使用     │ │
│ │ knowledge:review    | 審核知識 | 被 2 個角色使用     │ │
│ │ knowledge:ai_review | AI 審核  | 被 1 個角色使用     │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ 🎯 意圖管理 (5 個權限)                                    │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ intent:view         | 查看意圖 | 被 4 個角色使用     │ │
│ │ intent:create       | 新增意圖 | 被 2 個角色使用     │ │
│ │ ...                                                 │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ 🧪 測試與回測 (5 個權限)                                  │
│ ...                                                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### 功能說明

**主要功能**:
- ✅ 按資源分組顯示所有權限
- ✅ 顯示每個權限被多少角色使用
- ✅ 點擊權限可查看使用此權限的角色列表
- ✅ 搜尋和篩選權限

**設計考量**:
- 唯讀頁面（權限通常在代碼中定義，不支援動態新增）
- 提供權限使用情況的可視化
- 幫助管理員了解權限分配狀態

---

## 🧩 組件設計

### 1. PermissionSelector.vue - 權限選擇器

可重用的權限選擇組件。

```vue
<template>
  <div class="permission-selector">
    <!-- 工具列 -->
    <div class="toolbar">
      <input
        type="text"
        v-model="searchQuery"
        placeholder="🔍 搜尋權限..."
        class="search-input"
      />
      <button @click="selectAll" class="btn-link">✓ 全選</button>
      <button @click="clearAll" class="btn-link">× 清空</button>
    </div>

    <!-- 權限分組列表 -->
    <div class="permission-groups">
      <div
        v-for="group in filteredGroups"
        :key="group.resource"
        class="permission-group"
      >
        <!-- 分組標題 -->
        <div class="group-header" @click="toggleGroup(group.resource)">
          <span class="group-icon">{{ group.icon }}</span>
          <span class="group-title">{{ group.title }}</span>
          <span class="group-count">({{ group.permissions.length }} 個權限)</span>
          <span class="toggle-icon">{{ isExpanded(group.resource) ? '▼' : '▶' }}</span>
        </div>

        <!-- 權限清單 -->
        <transition name="slide">
          <div v-show="isExpanded(group.resource)" class="group-content">
            <div
              v-for="permission in group.permissions"
              :key="permission.name"
              class="permission-item"
            >
              <label class="permission-label">
                <input
                  type="checkbox"
                  :value="permission.name"
                  v-model="selectedPermissions"
                  @change="$emit('update:modelValue', selectedPermissions)"
                />
                <span class="permission-name">{{ permission.name }}</span>
                <span class="permission-desc">{{ permission.description }}</span>
              </label>
            </div>
          </div>
        </transition>
      </div>
    </div>

    <!-- 統計 -->
    <div class="footer">
      已選擇 <strong>{{ selectedPermissions.length }}</strong> 個權限
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
  permissionGroups: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['update:modelValue'])

const selectedPermissions = ref([...props.modelValue])
const searchQuery = ref('')
const expandedGroups = ref(new Set())

// 篩選後的分組
const filteredGroups = computed(() => {
  if (!searchQuery.value) return props.permissionGroups

  return props.permissionGroups.map(group => ({
    ...group,
    permissions: group.permissions.filter(p =>
      p.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.value.toLowerCase())
    )
  })).filter(group => group.permissions.length > 0)
})

function selectAll() {
  const allPermissions = props.permissionGroups.flatMap(g => g.permissions.map(p => p.name))
  selectedPermissions.value = allPermissions
  emit('update:modelValue', selectedPermissions.value)
}

function clearAll() {
  selectedPermissions.value = []
  emit('update:modelValue', selectedPermissions.value)
}

function toggleGroup(resource) {
  if (expandedGroups.value.has(resource)) {
    expandedGroups.value.delete(resource)
  } else {
    expandedGroups.value.add(resource)
  }
}

function isExpanded(resource) {
  return expandedGroups.value.has(resource)
}
</script>

<style scoped>
.permission-selector {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  background: #f7fafc;
}

.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}

.search-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #cbd5e0;
  border-radius: 6px;
}

.permission-groups {
  max-height: 500px;
  overflow-y: auto;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: white;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.group-header:hover {
  background: #edf2f7;
}

.permission-item {
  padding: 8px 12px;
  margin-left: 24px;
}

.permission-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.footer {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
  text-align: center;
  color: #4a5568;
}
</style>
```

---

### 2. RoleBadge.vue - 角色標籤

顯示角色的小標籤組件。

```vue
<template>
  <span class="role-badge" :class="roleClass">
    <span class="role-icon">{{ roleIcon }}</span>
    <span class="role-name">{{ roleName }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  role: {
    type: String,
    required: true
  }
})

const roleConfig = {
  super_admin: { icon: '🔐', name: '超級管理員', class: 'badge-admin' },
  knowledge_manager: { icon: '📚', name: '知識庫管理員', class: 'badge-knowledge' },
  tester: { icon: '🧪', name: '測試人員', class: 'badge-tester' },
  vendor_manager: { icon: '🏢', name: '業者管理員', class: 'badge-vendor' },
  config_manager: { icon: '⚙️', name: '配置管理員', class: 'badge-config' },
  viewer: { icon: '👁', name: '唯讀用戶', class: 'badge-viewer' }
}

const roleIcon = computed(() => roleConfig[props.role]?.icon || '❓')
const roleName = computed(() => roleConfig[props.role]?.name || props.role)
const roleClass = computed(() => roleConfig[props.role]?.class || 'badge-default')
</script>

<style scoped>
.role-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
}

.badge-admin {
  background: #e6fffa;
  color: #047857;
  border: 1px solid #6ee7b7;
}

.badge-knowledge {
  background: #dbeafe;
  color: #1e40af;
  border: 1px solid #93c5fd;
}

.badge-tester {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fcd34d;
}

.badge-vendor {
  background: #e0e7ff;
  color: #3730a3;
  border: 1px solid #a5b4fc;
}

.badge-config {
  background: #f3e8ff;
  color: #6b21a8;
  border: 1px solid #c084fc;
}

.badge-viewer {
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #cbd5e1;
}
</style>
```

---

### 3. PermissionGuard.vue - 權限保護包裝器

```vue
<template>
  <div v-if="hasPermission">
    <slot></slot>
  </div>
  <div v-else-if="$slots.fallback">
    <slot name="fallback"></slot>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { usePermission } from '@/composables/usePermission'

const props = defineProps({
  permission: {
    type: [String, Array],
    required: true
  },
  mode: {
    type: String,
    default: 'any',  // 'any' 或 'all'
    validator: (value) => ['any', 'all'].includes(value)
  }
})

const { can, canAny, canAll } = usePermission()

const hasPermission = computed(() => {
  if (Array.isArray(props.permission)) {
    return props.mode === 'all'
      ? canAll(props.permission)
      : canAny(props.permission)
  }
  return can(props.permission)
})
</script>
```

**使用範例**:

```vue
<template>
  <!-- 有權限時顯示按鈕，無權限時隱藏 -->
  <PermissionGuard permission="knowledge:create">
    <button>新增知識</button>
  </PermissionGuard>

  <!-- 有權限時顯示按鈕，無權限時顯示提示 -->
  <PermissionGuard permission="knowledge:delete">
    <button>刪除</button>
    <template #fallback>
      <span class="text-gray-400">無刪除權限</span>
    </template>
  </PermissionGuard>
</template>
```

---

## 🔄 交互流程

### 1. 新增角色流程

```
1. 點擊「新增角色」按鈕
   ↓
2. 開啟「新增角色」彈窗
   ↓
3. 填寫角色資訊
   - 角色名稱（英文代碼）
   - 顯示名稱（中文）
   - 說明
   ↓
4. 選擇權限（使用 PermissionSelector 組件）
   - 按分組展開/收合
   - 勾選權限
   - 使用全選/清空
   - 搜尋權限
   ↓
5. 驗證表單
   - 角色名稱不可重複
   - 至少選擇 1 個權限
   ↓
6. 提交表單
   ↓
7. 後端驗證並創建角色
   ↓
8. 顯示成功訊息，刷新角色列表
   ↓
9. 關閉彈窗
```

### 2. 分配角色給管理員流程

```
1. 在管理員列表點擊「編輯」
   ↓
2. 開啟「編輯管理員」彈窗
   ↓
3. 在「角色分配」區塊勾選角色
   - 可多選角色
   - 顯示每個角色的權限數量
   ↓
4. 點擊「查看所有權限」展開詳細權限列表（可選）
   ↓
5. 點擊「儲存」
   ↓
6. 後端更新管理員角色關聯
   ↓
7. 前端更新本地狀態
   - 如果是當前用戶，重新獲取權限
   ↓
8. 顯示成功訊息，刷新列表
   ↓
9. 關閉彈窗
```

### 3. 權限檢查流程（前端）

```
用戶訪問頁面
   ↓
路由守衛檢查
   ↓
是否需要認證？
   ├─ 否 → 允許訪問
   └─ 是 → 檢查 token
          ├─ 無效 → 跳轉登入頁
          └─ 有效 → 檢查路由權限
                    ├─ 有權限 → 允許訪問
                    └─ 無權限 → 跳轉 403 頁面

頁面載入後
   ↓
組件渲染時檢查
   ├─ v-permission 指令 → 移除無權限元素
   ├─ v-if="can(...)" → 條件渲染
   └─ PermissionGuard → 組件級控制
```

---

## 📱 響應式設計

### 桌面版 (> 1024px)

- 表格完整顯示所有欄位
- 彈窗寬度 600-800px
- 側邊選單展開

### 平板版 (768px - 1024px)

- 表格隱藏次要欄位
- 彈窗寬度 90%
- 側邊選單可折疊

### 手機版 (< 768px)

- 表格改為卡片式布局
- 彈窗全螢幕
- 側邊選單抽屜式

---

## 🎯 無障礙設計 (A11y)

1. **鍵盤導航**
   - Tab 鍵可順序聚焦所有互動元素
   - Enter 鍵可操作按鈕和連結
   - Esc 鍵可關閉彈窗

2. **螢幕閱讀器支援**
   - 使用語義化 HTML 標籤
   - 提供 aria-label 屬性
   - 表單欄位關聯 label

3. **視覺對比**
   - 文字與背景對比度 > 4.5:1
   - 互動元素明確的視覺反饋

---

## 📚 相關文檔

- [權限系統設計](./PERMISSION_SYSTEM_DESIGN.md)
- 組件開發規範 (待創建)
- API 文檔 (待創建)

---

**文檔版本：** 1.0.0
**最後更新：** 2026-01-06
**作者：** AIChatbot Team
