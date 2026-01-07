# 帳號權限系統設計文檔

## 📋 系統概述

基於 **RBAC (Role-Based Access Control)** 設計，實現細粒度的權限控制系統。

### 設計目標

- ✅ 基於角色的權限管理
- ✅ 細粒度的功能權限控制
- ✅ 前端路由與 UI 元素權限控制
- ✅ 後端 API 權限驗證
- ✅ 靈活的權限分配機制
- ✅ 良好的用戶體驗

---

## 🎯 核心概念

### 1. 權限 (Permission)

最小的權限單位，代表一個具體的操作。

**命名規範**：`<資源>:<操作>`

```
knowledge:view      # 查看知識
knowledge:create    # 新增知識
knowledge:edit      # 編輯知識
knowledge:delete    # 刪除知識
knowledge:import    # 匯入知識
knowledge:export    # 匯出知識
```

### 2. 角色 (Role)

權限的集合，代表一類用戶的職責。

```
super_admin         # 超級管理員
knowledge_manager   # 知識庫管理員
tester              # 測試人員
vendor_manager      # 業者管理員
config_manager      # 配置管理員
viewer              # 唯讀用戶
```

### 3. 用戶角色關聯

一個用戶可以擁有一個或多個角色。

---

## 📊 數據模型設計

### 資料庫結構

#### 1. `roles` 表 - 角色定義

```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,           -- 角色代碼 (如: super_admin)
    display_name VARCHAR(100) NOT NULL,         -- 角色顯示名稱
    description TEXT,                           -- 角色說明
    is_system BOOLEAN DEFAULT false,            -- 是否為系統預設角色（不可刪除）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入預設角色
INSERT INTO roles (name, display_name, description, is_system) VALUES
('super_admin', '超級管理員', '擁有所有權限', true),
('knowledge_manager', '知識庫管理員', '管理知識庫和意圖', true),
('tester', '測試人員', '執行測試和回測', true),
('vendor_manager', '業者管理員', '管理業者設定', true),
('config_manager', '配置管理員', '管理系統配置', true),
('viewer', '唯讀用戶', '只能查看資料', true);
```

#### 2. `permissions` 表 - 權限定義

```sql
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,          -- 權限代碼 (如: knowledge:view)
    display_name VARCHAR(100) NOT NULL,         -- 權限顯示名稱
    resource VARCHAR(50) NOT NULL,              -- 資源類型
    action VARCHAR(50) NOT NULL,                -- 操作類型
    description TEXT,                           -- 權限說明
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_permissions_resource ON permissions(resource);
CREATE INDEX idx_permissions_name ON permissions(name);
```

#### 3. `role_permissions` 表 - 角色權限關聯

```sql
CREATE TABLE role_permissions (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(role_id, permission_id)
);

CREATE INDEX idx_role_permissions_role ON role_permissions(role_id);
CREATE INDEX idx_role_permissions_permission ON role_permissions(permission_id);
```

#### 4. `admin_roles` 表 - 管理員角色關聯

```sql
CREATE TABLE admin_roles (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(admin_id, role_id)
);

CREATE INDEX idx_admin_roles_admin ON admin_roles(admin_id);
CREATE INDEX idx_admin_roles_role ON admin_roles(role_id);
```

---

## 🔐 權限列表定義

### 功能分類與權限設計

基於現有的 24 個前端視圖，設計以下權限結構：

#### 1️⃣ 知識庫管理 (Knowledge Management)

| 權限代碼 | 顯示名稱 | 說明 | 對應視圖 |
|---------|---------|------|----------|
| `knowledge:view` | 查看知識 | 查看知識列表和詳情 | KnowledgeView |
| `knowledge:create` | 新增知識 | 新增知識項目 | KnowledgeView |
| `knowledge:edit` | 編輯知識 | 修改知識內容 | KnowledgeView |
| `knowledge:delete` | 刪除知識 | 刪除知識項目 | KnowledgeView |
| `knowledge:import` | 匯入知識 | 批量匯入知識 | KnowledgeImportView |
| `knowledge:export` | 匯出知識 | 匯出知識資料 | KnowledgeExportView |
| `knowledge:reclassify` | 重新分類 | 重新分類知識 | KnowledgeReclassifyView |
| `knowledge:review` | 審核知識 | 審核待審核知識 | PendingReviewView, ReviewCenterView |
| `knowledge:ai_review` | AI 審核 | 使用 AI 審核知識 | AIKnowledgeReviewView |

#### 2️⃣ 意圖管理 (Intent Management)

| 權限代碼 | 顯示名稱 | 說明 | 對應視圖 |
|---------|---------|------|----------|
| `intent:view` | 查看意圖 | 查看意圖列表 | IntentsView |
| `intent:create` | 新增意圖 | 新增意圖 | IntentsView |
| `intent:edit` | 編輯意圖 | 修改意圖 | IntentsView |
| `intent:delete` | 刪除意圖 | 刪除意圖 | IntentsView |
| `intent:suggest` | 意圖建議 | 查看和管理建議意圖 | SuggestedIntentsView |

#### 3️⃣ 測試與回測 (Testing & Backtest)

| 權限代碼 | 顯示名稱 | 說明 | 對應視圖 |
|---------|---------|------|----------|
| `test:backtest` | 執行回測 | 執行和查看回測結果 | BacktestView |
| `test:chat` | 對話測試 | 測試對話功能 | ChatTestView |
| `test:scenarios` | 測試情境 | 管理測試情境 | TestScenariosView |
| `test:scenarios_create` | 新增測試情境 | 新增測試案例 | TestScenariosView |
| `test:scenarios_edit` | 編輯測試情境 | 修改測試案例 | TestScenariosView |

#### 4️⃣ 業者管理 (Vendor Management)

| 權限代碼 | 顯示名稱 | 說明 | 對應視圖 |
|---------|---------|------|----------|
| `vendor:view` | 查看業者 | 查看業者列表 | VendorManagementView |
| `vendor:create` | 新增業者 | 新增業者 | VendorManagementView |
| `vendor:edit` | 編輯業者 | 修改業者資料 | VendorManagementView |
| `vendor:delete` | 刪除業者 | 刪除業者 | VendorManagementView |
| `vendor:config` | 業者配置 | 配置業者設定 | VendorConfigView |

#### 5️⃣ 平台 SOP (Platform SOP)

| 權限代碼 | 顯示名稱 | 說明 | 對應視圖 |
|---------|---------|------|----------|
| `sop:view` | 查看 SOP | 查看平台 SOP | PlatformSOPView |
| `sop:create` | 新增 SOP | 新增 SOP 文檔 | PlatformSOPView |
| `sop:edit` | 編輯 SOP | 修改 SOP 內容 | PlatformSOPEditView |
| `sop:delete` | 刪除 SOP | 刪除 SOP 文檔 | PlatformSOPView |

#### 6️⃣ 配置管理 (Configuration)

| 權限代碼 | 顯示名稱 | 說明 | 對應視圖 |
|---------|---------|------|----------|
| `config:business_types` | 業態配置 | 管理業態類型 | BusinessTypesConfigView |
| `config:target_users` | 目標用戶配置 | 管理目標用戶設定 | TargetUserConfigView |
| `config:cache` | 快取管理 | 管理系統快取 | CacheManagementView |

#### 7️⃣ 文檔處理 (Document Processing)

| 權限代碼 | 顯示名稱 | 說明 | 對應視圖 |
|---------|---------|------|----------|
| `document:convert` | 文檔轉換 | 轉換文檔格式 | DocumentConverterView |

#### 8️⃣ 系統管理 (System Administration)

| 權限代碼 | 顯示名稱 | 說明 | 對應視圖 |
|---------|---------|------|----------|
| `admin:view` | 查看管理員 | 查看管理員列表 | AdminManagementView |
| `admin:create` | 新增管理員 | 新增管理員帳號 | AdminManagementView |
| `admin:edit` | 編輯管理員 | 修改管理員資料 | AdminManagementView |
| `admin:delete` | 刪除管理員 | 刪除管理員 | AdminManagementView |
| `admin:reset_password` | 重設密碼 | 重設其他管理員密碼 | AdminManagementView |
| `role:view` | 查看角色 | 查看角色列表 | RoleManagementView (待開發) |
| `role:create` | 新增角色 | 新增自訂角色 | RoleManagementView (待開發) |
| `role:edit` | 編輯角色 | 修改角色權限 | RoleManagementView (待開發) |
| `role:delete` | 刪除角色 | 刪除自訂角色 | RoleManagementView (待開發) |

---

## 👥 預設角色權限配置

### 1. Super Admin (超級管理員)

**擁有所有權限** - 通配符 `*:*` 或所有具體權限

### 2. Knowledge Manager (知識庫管理員)

```
✅ knowledge:*          # 所有知識庫權限
✅ intent:*             # 所有意圖權限
✅ document:convert     # 文檔轉換
```

### 3. Tester (測試人員)

```
✅ knowledge:view       # 查看知識（唯讀）
✅ intent:view          # 查看意圖（唯讀）
✅ test:*               # 所有測試權限
```

### 4. Vendor Manager (業者管理員)

```
✅ vendor:*             # 所有業者權限
✅ knowledge:view       # 查看知識
✅ intent:view          # 查看意圖
```

### 5. Config Manager (配置管理員)

```
✅ config:*             # 所有配置權限
✅ sop:*                # 所有 SOP 權限
✅ knowledge:view       # 查看知識
```

### 6. Viewer (唯讀用戶)

```
✅ knowledge:view       # 查看知識
✅ intent:view          # 查看意圖
✅ test:backtest        # 查看回測（唯讀）
✅ vendor:view          # 查看業者
✅ sop:view             # 查看 SOP
```

---

## 🎨 前端設計方案

### 1. 權限 Store 擴展

擴展現有的 `auth.js`，新增權限管理功能。

**檔案位置**: `knowledge-admin/frontend/src/stores/auth.js`

```javascript
export const useAuthStore = defineStore('auth', () => {
  // ... 現有的 state
  const permissions = ref([])  // 用戶權限列表
  const roles = ref([])        // 用戶角色列表

  // Getters - 權限檢查
  const hasPermission = computed(() => (permission) => {
    // 超級管理員擁有所有權限
    if (permissions.value.includes('*:*')) return true

    // 檢查具體權限
    if (permissions.value.includes(permission)) return true

    // 檢查通配符權限 (如 knowledge:*)
    const [resource, action] = permission.split(':')
    return permissions.value.includes(`${resource}:*`)
  })

  const hasRole = computed(() => (role) => {
    return roles.value.includes(role)
  })

  const hasAnyPermission = computed(() => (permissionList) => {
    return permissionList.some(p => hasPermission.value(p))
  })

  const hasAllPermissions = computed(() => (permissionList) => {
    return permissionList.every(p => hasPermission.value(p))
  })

  // Actions - 獲取用戶權限
  async function fetchUserPermissions() {
    if (!token.value) return

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/permissions`, {
        headers: {
          'Authorization': `Bearer ${token.value}`
        }
      })

      if (!response.ok) throw new Error('獲取權限失敗')

      const data = await response.json()
      permissions.value = data.permissions || []
      roles.value = data.roles || []

      return data
    } catch (err) {
      console.error('獲取權限失敗:', err)
      throw err
    }
  }

  // 登入時同時獲取權限
  async function login(username, password) {
    // ... 現有登入邏輯
    await fetchUserPermissions()
    return data
  }

  return {
    // ... 現有返回值
    permissions,
    roles,
    hasPermission,
    hasRole,
    hasAnyPermission,
    hasAllPermissions,
    fetchUserPermissions
  }
})
```

---

### 2. Vue 自訂指令 - v-permission

創建全局指令用於控制 UI 元素的顯示/隱藏。

**檔案位置**: `knowledge-admin/frontend/src/directives/permission.js`

```javascript
/**
 * v-permission 指令
 * 根據用戶權限控制元素的顯示/隱藏
 *
 * 用法：
 * v-permission="'knowledge:create'"           // 單一權限
 * v-permission="['knowledge:create', 'knowledge:edit']"  // 多個權限（OR）
 * v-permission.all="['knowledge:create', 'knowledge:edit']"  // 多個權限（AND）
 */
import { useAuthStore } from '@/stores/auth'

export default {
  mounted(el, binding) {
    const authStore = useAuthStore()
    const { value, modifiers } = binding

    let hasPermission = false

    if (Array.isArray(value)) {
      // 多個權限
      if (modifiers.all) {
        // AND 邏輯 - 需要擁有所有權限
        hasPermission = authStore.hasAllPermissions(value)
      } else {
        // OR 邏輯 - 擁有任一權限即可
        hasPermission = authStore.hasAnyPermission(value)
      }
    } else if (typeof value === 'string') {
      // 單一權限
      hasPermission = authStore.hasPermission(value)
    }

    if (!hasPermission) {
      // 移除元素
      el.parentNode?.removeChild(el)
    }
  }
}
```

**註冊指令**: `knowledge-admin/frontend/src/main.js`

```javascript
import permissionDirective from './directives/permission'

const app = createApp(App)
app.directive('permission', permissionDirective)
```

---

### 3. 路由權限守衛擴展

擴展現有的路由守衛，增加權限檢查。

**檔案位置**: `knowledge-admin/frontend/src/router.js`

```javascript
const routes = [
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: KnowledgeView,
    meta: {
      requiresAuth: true,
      permissions: ['knowledge:view']  // 需要的權限
    }
  },
  {
    path: '/admin-management',
    name: 'AdminManagement',
    component: AdminManagementView,
    meta: {
      requiresAuth: true,
      permissions: ['admin:view'],
      roles: ['super_admin']  // 或者限制角色
    }
  },
  // ... 其他路由
]

// 路由守衛擴展
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // 1. 檢查登入
  const requiresAuth = to.meta.requiresAuth !== false
  if (requiresAuth && !authStore.isAuthenticated) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }

  // 2. 檢查權限
  if (to.meta.permissions) {
    const hasPermission = authStore.hasAnyPermission(to.meta.permissions)
    if (!hasPermission) {
      // 無權限，跳轉到 403 頁面
      return next({ name: 'Forbidden' })
    }
  }

  // 3. 檢查角色
  if (to.meta.roles) {
    const hasRole = to.meta.roles.some(role => authStore.hasRole(role))
    if (!hasRole) {
      return next({ name: 'Forbidden' })
    }
  }

  next()
})
```

---

### 4. 組合式函數 (Composable)

創建可重用的權限檢查函數。

**檔案位置**: `knowledge-admin/frontend/src/composables/usePermission.js`

```javascript
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function usePermission() {
  const authStore = useAuthStore()

  const can = (permission) => {
    return authStore.hasPermission(permission)
  }

  const canAny = (permissions) => {
    return authStore.hasAnyPermission(permissions)
  }

  const canAll = (permissions) => {
    return authStore.hasAllPermissions(permissions)
  }

  const hasRole = (role) => {
    return authStore.hasRole(role)
  }

  const isAdmin = computed(() => hasRole('super_admin'))

  return {
    can,
    canAny,
    canAll,
    hasRole,
    isAdmin
  }
}
```

**使用範例**:

```vue
<template>
  <div>
    <!-- 使用指令 -->
    <button v-permission="'knowledge:create'">新增知識</button>
    <button v-permission="['knowledge:edit', 'knowledge:delete']">編輯或刪除</button>

    <!-- 使用組合式函數 -->
    <button v-if="can('knowledge:create')">新增知識</button>
    <button v-if="canAny(['knowledge:edit', 'knowledge:delete'])">編輯或刪除</button>
  </div>
</template>

<script setup>
import { usePermission } from '@/composables/usePermission'

const { can, canAny, canAll, isAdmin } = usePermission()
</script>
```

---

### 5. 菜單/導航權限控制

根據權限動態生成菜單。

**檔案位置**: `knowledge-admin/frontend/src/config/menu.js`

```javascript
/**
 * 菜單配置
 * 每個菜單項可以設定 permissions 或 roles 來控制顯示
 */
export const menuItems = [
  {
    title: '知識庫管理',
    icon: 'book',
    permissions: ['knowledge:view'],
    children: [
      {
        title: '知識列表',
        path: '/knowledge',
        permissions: ['knowledge:view']
      },
      {
        title: '知識匯入',
        path: '/knowledge-import',
        permissions: ['knowledge:import']
      },
      {
        title: '知識匯出',
        path: '/knowledge-export',
        permissions: ['knowledge:export']
      },
      {
        title: '待審核知識',
        path: '/pending-review',
        permissions: ['knowledge:review']
      }
    ]
  },
  {
    title: '意圖管理',
    icon: 'target',
    permissions: ['intent:view'],
    children: [
      {
        title: '意圖列表',
        path: '/intents',
        permissions: ['intent:view']
      },
      {
        title: '建議意圖',
        path: '/suggested-intents',
        permissions: ['intent:suggest']
      }
    ]
  },
  {
    title: '測試中心',
    icon: 'test-tube',
    permissions: ['test:backtest', 'test:chat', 'test:scenarios'],
    children: [
      {
        title: '回測',
        path: '/backtest',
        permissions: ['test:backtest']
      },
      {
        title: '對話測試',
        path: '/chat-test',
        permissions: ['test:chat']
      },
      {
        title: '測試情境',
        path: '/test-scenarios',
        permissions: ['test:scenarios']
      }
    ]
  },
  {
    title: '業者管理',
    icon: 'building',
    permissions: ['vendor:view'],
    children: [
      {
        title: '業者列表',
        path: '/vendor-management',
        permissions: ['vendor:view']
      },
      {
        title: '業者配置',
        path: '/vendor-config',
        permissions: ['vendor:config']
      }
    ]
  },
  {
    title: '系統管理',
    icon: 'settings',
    roles: ['super_admin'],
    children: [
      {
        title: '管理員管理',
        path: '/admin-management',
        permissions: ['admin:view']
      },
      {
        title: '角色管理',
        path: '/role-management',
        permissions: ['role:view']
      },
      {
        title: '配置管理',
        path: '/config',
        permissions: ['config:business_types', 'config:target_users', 'config:cache']
      }
    ]
  }
]
```

**菜單過濾組件**: `knowledge-admin/frontend/src/components/AppMenu.vue`

```vue
<template>
  <nav>
    <template v-for="item in filteredMenu" :key="item.title">
      <div v-if="item.children && item.children.length > 0">
        <h3>{{ item.title }}</h3>
        <ul>
          <li v-for="child in item.children" :key="child.path">
            <router-link :to="child.path">{{ child.title }}</router-link>
          </li>
        </ul>
      </div>
    </template>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { menuItems } from '@/config/menu'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const filteredMenu = computed(() => {
  return menuItems
    .filter(item => hasMenuPermission(item))
    .map(item => ({
      ...item,
      children: item.children?.filter(child => hasMenuPermission(child)) || []
    }))
})

function hasMenuPermission(item) {
  // 檢查角色
  if (item.roles && !item.roles.some(role => authStore.hasRole(role))) {
    return false
  }

  // 檢查權限
  if (item.permissions) {
    return authStore.hasAnyPermission(item.permissions)
  }

  return true
}
</script>
```

---

## 🔧 後端 API 設計

### 1. 新增權限查詢 API

**檔案位置**: `knowledge-admin/backend/routes_auth.py`

```python
@router.get("/permissions")
async def get_current_user_permissions(user: dict = Depends(get_current_user)):
    """
    獲取當前用戶的所有權限和角色

    Returns:
        {
            "roles": ["super_admin"],
            "permissions": ["*:*"] 或 ["knowledge:view", "knowledge:create", ...]
        }
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 查詢用戶的角色
            cur.execute("""
                SELECT r.name
                FROM roles r
                JOIN admin_roles ar ON r.id = ar.role_id
                WHERE ar.admin_id = %s
            """, (user['id'],))
            roles = [row['name'] for row in cur.fetchall()]

            # 查詢角色對應的權限
            cur.execute("""
                SELECT DISTINCT p.name
                FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                JOIN admin_roles ar ON rp.role_id = ar.role_id
                WHERE ar.admin_id = %s
            """, (user['id'],))
            permissions = [row['name'] for row in cur.fetchall()]

            return {
                "roles": roles,
                "permissions": permissions
            }
    finally:
        conn.close()
```

### 2. 權限驗證依賴函數

**檔案位置**: `knowledge-admin/backend/auth_utils.py`

```python
from fastapi import HTTPException, Depends, status

def require_permission(permission: str):
    """
    創建一個權限檢查依賴

    用法:
    @app.get("/api/knowledge", dependencies=[Depends(require_permission("knowledge:view"))])
    """
    async def permission_checker(user: dict = Depends(get_current_user)):
        # 從資料庫查詢用戶權限
        user_permissions = await get_user_permissions(user['id'])

        # 超級管理員
        if '*:*' in user_permissions:
            return user

        # 檢查具體權限
        if permission in user_permissions:
            return user

        # 檢查通配符權限
        resource, action = permission.split(':')
        if f'{resource}:*' in user_permissions:
            return user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"缺少權限: {permission}"
        )

    return permission_checker

async def get_user_permissions(admin_id: int) -> list:
    """查詢用戶的所有權限"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT p.name
                FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                JOIN admin_roles ar ON rp.role_id = ar.role_id
                WHERE ar.admin_id = %s
            """, (admin_id,))
            return [row['name'] for row in cur.fetchall()]
    finally:
        conn.close()
```

**使用範例**:

```python
# 方式 1: 使用 dependencies
@app.get("/api/knowledge", dependencies=[Depends(require_permission("knowledge:view"))])
async def list_knowledge():
    # ...

# 方式 2: 在函數內檢查
@app.post("/api/knowledge")
async def create_knowledge(data: KnowledgeCreate, user: dict = Depends(get_current_user)):
    # 檢查權限
    if not await has_permission(user['id'], 'knowledge:create'):
        raise HTTPException(status_code=403, detail="缺少權限")
    # ...
```

---

## 📝 實作階段規劃

### 階段 1: 資料庫設計 (1-2 天)

- [ ] 創建資料庫遷移腳本
- [ ] 建立 roles, permissions, role_permissions, admin_roles 表
- [ ] 插入預設角色和權限數據
- [ ] 為預設管理員分配 super_admin 角色

### 階段 2: 後端 API 開發 (2-3 天)

- [ ] 實作權限查詢 API (`/api/auth/permissions`)
- [ ] 實作角色管理 API (`/api/roles/*`)
- [ ] 實作權限管理 API (`/api/permissions/*`)
- [ ] 實作用戶角色分配 API (`/api/admins/{id}/roles`)
- [ ] 更新現有 API，加入權限檢查
- [ ] 編寫單元測試

### 階段 3: 前端基礎建設 (2-3 天)

- [ ] 擴展 auth store，新增權限管理
- [ ] 創建 `v-permission` 指令
- [ ] 創建 `usePermission` composable
- [ ] 更新路由守衛，加入權限檢查
- [ ] 創建 403 Forbidden 頁面

### 階段 4: 前端 UI 開發 (3-4 天)

- [ ] 開發角色管理頁面 (`RoleManagementView.vue`)
- [ ] 開發權限管理頁面 (`PermissionManagementView.vue`)
- [ ] 更新管理員管理頁面，加入角色分配功能
- [ ] 創建菜單配置和過濾邏輯
- [ ] 更新現有頁面，加入權限控制元素

### 階段 5: 測試與優化 (2-3 天)

- [ ] 功能測試：各種角色權限組合
- [ ] UI/UX 測試：權限不足時的用戶體驗
- [ ] 性能測試：權限查詢效率
- [ ] 文檔撰寫：使用手冊和開發文檔
- [ ] 修復 bug 和優化

**總計：10-15 天**

---

## 📚 相關文檔

- [認證系統總覽](./AUTH_SYSTEM_README.md)
- [部署指南](./AUTH_DEPLOYMENT_GUIDE.md)
- [前端開發規範](./FRONTEND_DEVELOPMENT_GUIDE.md) (待創建)

---

**文檔版本：** 1.0.0
**最後更新：** 2026-01-06
**作者：** AIChatbot Team
