# 權限系統快速開始指南

本指南提供實作權限系統的步驟式教學，適合開發者快速上手。

---

## 📋 前置檢查

確認以下項目已完成：

- ✅ 認證系統已部署（JWT Token 認證）
- ✅ 管理員管理功能正常運作
- ✅ 前端 Pinia store 正常運作
- ✅ 資料庫連線正常

---

## 🚀 實作步驟

### 階段 1: 資料庫建置 (第 1 天)

#### 步驟 1.1: 創建資料庫遷移腳本

創建檔案：`database/migrations/add_permission_system.sql`

```sql
-- ==========================================
-- 權限系統資料庫遷移腳本
-- ==========================================

-- 1. 建立 roles 表
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 建立 permissions 表
CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_permissions_resource ON permissions(resource);
CREATE INDEX idx_permissions_name ON permissions(name);

-- 3. 建立 role_permissions 表
CREATE TABLE IF NOT EXISTS role_permissions (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(role_id, permission_id)
);

CREATE INDEX idx_role_permissions_role ON role_permissions(role_id);
CREATE INDEX idx_role_permissions_permission ON role_permissions(permission_id);

-- 4. 建立 admin_roles 表
CREATE TABLE IF NOT EXISTS admin_roles (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(admin_id, role_id)
);

CREATE INDEX idx_admin_roles_admin ON admin_roles(admin_id);
CREATE INDEX idx_admin_roles_role ON admin_roles(role_id);

-- ==========================================
-- 插入預設角色
-- ==========================================

INSERT INTO roles (name, display_name, description, is_system) VALUES
('super_admin', '超級管理員', '擁有所有權限，可管理系統所有功能', true),
('knowledge_manager', '知識庫管理員', '管理知識庫和意圖，包括新增、編輯、刪除等操作', true),
('tester', '測試人員', '執行測試和回測，查看測試結果', true),
('vendor_manager', '業者管理員', '管理業者資料和配置', true),
('config_manager', '配置管理員', '管理系統配置和設定', true),
('viewer', '唯讀用戶', '只能查看資料，無法進行任何修改操作', true);

-- ==========================================
-- 插入所有權限
-- ==========================================

-- 知識庫管理權限
INSERT INTO permissions (name, display_name, resource, action, description) VALUES
('knowledge:view', '查看知識', 'knowledge', 'view', '查看知識列表和詳情'),
('knowledge:create', '新增知識', 'knowledge', 'create', '新增知識項目'),
('knowledge:edit', '編輯知識', 'knowledge', 'edit', '修改知識內容'),
('knowledge:delete', '刪除知識', 'knowledge', 'delete', '刪除知識項目'),
('knowledge:import', '匯入知識', 'knowledge', 'import', '批量匯入知識'),
('knowledge:export', '匯出知識', 'knowledge', 'export', '匯出知識資料'),
('knowledge:reclassify', '重新分類', 'knowledge', 'reclassify', '重新分類知識'),
('knowledge:review', '審核知識', 'knowledge', 'review', '審核待審核知識'),
('knowledge:ai_review', 'AI 審核', 'knowledge', 'ai_review', '使用 AI 審核知識');

-- 意圖管理權限
INSERT INTO permissions (name, display_name, resource, action, description) VALUES
('intent:view', '查看意圖', 'intent', 'view', '查看意圖列表'),
('intent:create', '新增意圖', 'intent', 'create', '新增意圖'),
('intent:edit', '編輯意圖', 'intent', 'edit', '修改意圖'),
('intent:delete', '刪除意圖', 'intent', 'delete', '刪除意圖'),
('intent:suggest', '意圖建議', 'intent', 'suggest', '查看和管理建議意圖');

-- 測試與回測權限
INSERT INTO permissions (name, display_name, resource, action, description) VALUES
('test:backtest', '執行回測', 'test', 'backtest', '執行和查看回測結果'),
('test:chat', '對話測試', 'test', 'chat', '測試對話功能'),
('test:scenarios', '測試情境', 'test', 'scenarios', '查看測試情境'),
('test:scenarios_create', '新增測試情境', 'test', 'scenarios_create', '新增測試案例'),
('test:scenarios_edit', '編輯測試情境', 'test', 'scenarios_edit', '修改測試案例');

-- 業者管理權限
INSERT INTO permissions (name, display_name, resource, action, description) VALUES
('vendor:view', '查看業者', 'vendor', 'view', '查看業者列表'),
('vendor:create', '新增業者', 'vendor', 'create', '新增業者'),
('vendor:edit', '編輯業者', 'vendor', 'edit', '修改業者資料'),
('vendor:delete', '刪除業者', 'vendor', 'delete', '刪除業者'),
('vendor:config', '業者配置', 'vendor', 'config', '配置業者設定');

-- 平台 SOP 權限
INSERT INTO permissions (name, display_name, resource, action, description) VALUES
('sop:view', '查看 SOP', 'sop', 'view', '查看平台 SOP'),
('sop:create', '新增 SOP', 'sop', 'create', '新增 SOP 文檔'),
('sop:edit', '編輯 SOP', 'sop', 'edit', '修改 SOP 內容'),
('sop:delete', '刪除 SOP', 'sop', 'delete', '刪除 SOP 文檔');

-- 配置管理權限
INSERT INTO permissions (name, display_name, resource, action, description) VALUES
('config:business_types', '業態配置', 'config', 'business_types', '管理業態類型'),
('config:target_users', '目標用戶配置', 'config', 'target_users', '管理目標用戶設定'),
('config:cache', '快取管理', 'config', 'cache', '管理系統快取');

-- 文檔處理權限
INSERT INTO permissions (name, display_name, resource, action, description) VALUES
('document:convert', '文檔轉換', 'document', 'convert', '轉換文檔格式');

-- 系統管理權限
INSERT INTO permissions (name, display_name, resource, action, description) VALUES
('admin:view', '查看管理員', 'admin', 'view', '查看管理員列表'),
('admin:create', '新增管理員', 'admin', 'create', '新增管理員帳號'),
('admin:edit', '編輯管理員', 'admin', 'edit', '修改管理員資料'),
('admin:delete', '刪除管理員', 'admin', 'delete', '刪除管理員'),
('admin:reset_password', '重設密碼', 'admin', 'reset_password', '重設其他管理員密碼'),
('role:view', '查看角色', 'role', 'view', '查看角色列表'),
('role:create', '新增角色', 'role', 'create', '新增自訂角色'),
('role:edit', '編輯角色', 'role', 'edit', '修改角色權限'),
('role:delete', '刪除角色', 'role', 'delete', '刪除自訂角色');

-- ==========================================
-- 分配權限給角色
-- ==========================================

-- Super Admin - 擁有所有權限
INSERT INTO role_permissions (role_id, permission_id)
SELECT
    (SELECT id FROM roles WHERE name = 'super_admin'),
    id
FROM permissions;

-- Knowledge Manager - 知識庫和意圖管理
INSERT INTO role_permissions (role_id, permission_id)
SELECT
    (SELECT id FROM roles WHERE name = 'knowledge_manager'),
    id
FROM permissions
WHERE resource IN ('knowledge', 'intent', 'document');

-- Tester - 測試相關權限 + 唯讀知識和意圖
INSERT INTO role_permissions (role_id, permission_id)
SELECT
    (SELECT id FROM roles WHERE name = 'tester'),
    id
FROM permissions
WHERE resource = 'test'
   OR (resource = 'knowledge' AND action = 'view')
   OR (resource = 'intent' AND action = 'view');

-- Vendor Manager - 業者管理 + 唯讀知識和意圖
INSERT INTO role_permissions (role_id, permission_id)
SELECT
    (SELECT id FROM roles WHERE name = 'vendor_manager'),
    id
FROM permissions
WHERE resource = 'vendor'
   OR (resource = 'knowledge' AND action = 'view')
   OR (resource = 'intent' AND action = 'view');

-- Config Manager - 配置和 SOP 管理
INSERT INTO role_permissions (role_id, permission_id)
SELECT
    (SELECT id FROM roles WHERE name = 'config_manager'),
    id
FROM permissions
WHERE resource IN ('config', 'sop')
   OR (resource = 'knowledge' AND action = 'view');

-- Viewer - 只能查看
INSERT INTO role_permissions (role_id, permission_id)
SELECT
    (SELECT id FROM roles WHERE name = 'viewer'),
    id
FROM permissions
WHERE action = 'view';

-- ==========================================
-- 為預設管理員分配超級管理員角色
-- ==========================================

INSERT INTO admin_roles (admin_id, role_id)
SELECT
    (SELECT id FROM admins WHERE username = 'admin'),
    (SELECT id FROM roles WHERE name = 'super_admin')
ON CONFLICT DO NOTHING;

-- 完成
SELECT '✅ 權限系統資料庫建置完成！' AS status;
```

#### 步驟 1.2: 執行遷移

```bash
# 開發環境
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin < database/migrations/add_permission_system.sql

# 生產環境
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U aichatbot -d aichatbot_admin < database/migrations/add_permission_system.sql
```

#### 步驟 1.3: 驗證資料

```bash
# 檢查角色
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "SELECT name, display_name FROM roles;"

# 檢查權限數量
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "SELECT COUNT(*) FROM permissions;"

# 檢查預設管理員角色
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
SELECT a.username, r.display_name
FROM admin_roles ar
JOIN admins a ON ar.admin_id = a.id
JOIN roles r ON ar.role_id = r.id;
"
```

---

### 階段 2: 後端 API 開發 (第 2-3 天)

#### 步驟 2.1: 更新認證工具 (auth_utils.py)

```python
# knowledge-admin/backend/auth_utils.py

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

def require_permission(permission: str):
    """創建權限檢查依賴"""
    async def permission_checker(user: dict = Depends(get_current_user)):
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
```

#### 步驟 2.2: 新增權限查詢 API (routes_auth.py)

在現有的 `routes_auth.py` 中添加：

```python
@router.get("/permissions")
async def get_current_user_permissions(user: dict = Depends(get_current_user)):
    """
    獲取當前用戶的所有權限和角色
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 查詢用戶的角色
            cur.execute("""
                SELECT r.name, r.display_name
                FROM roles r
                JOIN admin_roles ar ON r.id = ar.role_id
                WHERE ar.admin_id = %s
            """, (user['id'],))
            roles = [{'name': row['name'], 'display_name': row['display_name']}
                    for row in cur.fetchall()]

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

#### 步驟 2.3: 測試後端 API

```bash
# 1. 登入獲取 token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.access_token')

# 2. 獲取權限
curl http://localhost:8000/api/auth/permissions \
  -H "Authorization: Bearer $TOKEN" | jq
```

預期輸出：
```json
{
  "roles": [
    {
      "name": "super_admin",
      "display_name": "超級管理員"
    }
  ],
  "permissions": [
    "knowledge:view",
    "knowledge:create",
    ...
  ]
}
```

---

### 階段 3: 前端基礎建設 (第 4-5 天)

#### 步驟 3.1: 擴展 Auth Store

編輯 `knowledge-admin/frontend/src/stores/auth.js`：

```javascript
export const useAuthStore = defineStore('auth', () => {
  // 現有 state
  const token = ref(localStorage.getItem('auth_token') || null)
  const user = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // 新增 - 權限相關 state
  const permissions = ref([])
  const roles = ref([])

  // 現有 getters
  const isAuthenticated = computed(() => !!token.value)

  // 新增 - 權限檢查 getters
  const hasPermission = computed(() => (permission) => {
    if (permissions.value.includes('*:*')) return true
    if (permissions.value.includes(permission)) return true

    const [resource, action] = permission.split(':')
    return permissions.value.includes(`${resource}:*`)
  })

  const hasRole = computed(() => (role) => {
    return roles.value.some(r => r.name === role)
  })

  const hasAnyPermission = computed(() => (permissionList) => {
    return permissionList.some(p => hasPermission.value(p))
  })

  const hasAllPermissions = computed(() => (permissionList) => {
    return permissionList.every(p => hasPermission.value(p))
  })

  // 新增 - 獲取權限
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

  // 修改 - 登入時同時獲取權限
  async function login(username, password) {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || '登入失敗')
      }

      const data = await response.json()

      token.value = data.access_token
      user.value = data.user
      localStorage.setItem('auth_token', data.access_token)

      // 獲取權限
      await fetchUserPermissions()

      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // 修改 - 登出時清除權限
  function logout() {
    token.value = null
    user.value = null
    permissions.value = []
    roles.value = []
    error.value = null
    localStorage.removeItem('auth_token')
  }

  return {
    // State
    token,
    user,
    loading,
    error,
    permissions,
    roles,
    // Getters
    isAuthenticated,
    hasPermission,
    hasRole,
    hasAnyPermission,
    hasAllPermissions,
    // Actions
    login,
    logout,
    fetchCurrentUser,
    fetchUserPermissions,
    initialize
  }
})
```

#### 步驟 3.2: 創建權限指令

創建 `knowledge-admin/frontend/src/directives/permission.js`：

```javascript
import { useAuthStore } from '@/stores/auth'

export default {
  mounted(el, binding) {
    const authStore = useAuthStore()
    const { value, modifiers } = binding

    let hasPermission = false

    if (Array.isArray(value)) {
      hasPermission = modifiers.all
        ? authStore.hasAllPermissions(value)
        : authStore.hasAnyPermission(value)
    } else if (typeof value === 'string') {
      hasPermission = authStore.hasPermission(value)
    }

    if (!hasPermission) {
      el.parentNode?.removeChild(el)
    }
  }
}
```

#### 步驟 3.3: 註冊指令

修改 `knowledge-admin/frontend/src/main.js`：

```javascript
import permissionDirective from './directives/permission'

const app = createApp(App)

// 註冊權限指令
app.directive('permission', permissionDirective)

app.use(pinia)
app.use(router)
app.mount('#app')
```

#### 步驟 3.4: 創建 Composable

創建 `knowledge-admin/frontend/src/composables/usePermission.js`：

```javascript
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function usePermission() {
  const authStore = useAuthStore()

  const can = (permission) => authStore.hasPermission(permission)
  const canAny = (permissions) => authStore.hasAnyPermission(permissions)
  const canAll = (permissions) => authStore.hasAllPermissions(permissions)
  const hasRole = (role) => authStore.hasRole(role)
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

#### 步驟 3.5: 測試前端權限

在任意組件中測試：

```vue
<template>
  <div>
    <h1>權限測試</h1>

    <!-- 使用指令 -->
    <button v-permission="'knowledge:create'">新增知識</button>

    <!-- 使用 composable -->
    <button v-if="can('knowledge:edit')">編輯知識</button>

    <!-- 調試資訊 -->
    <pre>{{ JSON.stringify(permissions, null, 2) }}</pre>
  </div>
</template>

<script setup>
import { usePermission } from '@/composables/usePermission'
import { useAuthStore } from '@/stores/auth'

const { can } = usePermission()
const authStore = useAuthStore()
const permissions = computed(() => authStore.permissions)
</script>
```

---

## ✅ 驗證清單

完成每個階段後，使用此清單驗證：

### 資料庫階段
- [ ] 4 個表格已創建 (roles, permissions, role_permissions, admin_roles)
- [ ] 6 個預設角色已插入
- [ ] 40+ 個權限已插入
- [ ] 預設管理員已分配 super_admin 角色

### 後端階段
- [ ] `/api/auth/permissions` API 正常運作
- [ ] 使用 token 可以獲取權限列表
- [ ] 超級管理員可獲取所有權限

### 前端階段
- [ ] auth store 包含 permissions 和 roles
- [ ] 登入後自動獲取權限
- [ ] `v-permission` 指令可正常使用
- [ ] `usePermission` composable 可正常使用
- [ ] 權限檢查邏輯正確

---

## 🐛 常見問題

### 問題 1: 權限 API 返回空陣列

**原因**: 管理員未分配角色

**解決**:
```sql
-- 為管理員分配角色
INSERT INTO admin_roles (admin_id, role_id)
VALUES (
    (SELECT id FROM admins WHERE username = 'your_username'),
    (SELECT id FROM roles WHERE name = 'super_admin')
);
```

### 問題 2: v-permission 指令不起作用

**原因**: 指令未註冊或權限未載入

**解決**:
1. 確認 `main.js` 中已註冊指令
2. 檢查登入後是否呼叫 `fetchUserPermissions()`
3. 檢查 store 中 permissions 陣列是否有值

### 問題 3: 所有用戶都顯示無權限

**原因**: 權限檢查邏輯錯誤

**解決**:
1. 檢查後端返回的權限格式
2. 確認前端 hasPermission 邏輯正確
3. 檢查是否有通配符權限 `*:*`

---

## 📚 下一步

完成基礎建設後，可以：

1. **開發角色管理 UI** - 參考 [PERMISSION_UI_DESIGN.md](../../design/PERMISSION_UI_DESIGN.md)
2. **為現有頁面添加權限控制** - 更新路由 meta 和組件
3. **為 API 添加權限驗證** - 使用 `require_permission` 裝飾器
4. **撰寫單元測試** - 測試權限邏輯

---

## 📞 需要幫助？

- 查看 [完整設計文檔](../../design/PERMISSION_SYSTEM_DESIGN.md)
- 查看 [UI 設計文檔](../../design/PERMISSION_UI_DESIGN.md)
- 檢查 測試案例 (待創建)

---

**文檔版本：** 1.0.0
**最後更新：** 2026-01-06
**預估時間：** 5-7 天完成基礎功能
