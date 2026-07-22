-- ==========================================
-- 權限系統資料庫遷移腳本
-- 版本: 1.0.0
-- 日期: 2026-01-07
-- ==========================================

BEGIN;

-- ==========================================
-- 1. 建立 roles 表 (角色)
-- ==========================================

CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE roles IS '角色表 - 定義系統中的角色';
COMMENT ON COLUMN roles.name IS '角色代碼（英文），如: super_admin';
COMMENT ON COLUMN roles.display_name IS '角色顯示名稱（中文），如: 超級管理員';
COMMENT ON COLUMN roles.is_system IS '是否為系統預設角色（不可刪除）';

-- ==========================================
-- 2. 建立 permissions 表 (權限)
-- ==========================================

CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE permissions IS '權限表 - 定義系統中的所有權限';
COMMENT ON COLUMN permissions.name IS '權限代碼，格式: resource:action，如: knowledge:view';
COMMENT ON COLUMN permissions.resource IS '資源類型，如: knowledge, intent, admin';
COMMENT ON COLUMN permissions.action IS '操作類型，如: view, create, edit, delete';

CREATE INDEX IF NOT EXISTS idx_permissions_resource ON permissions(resource);
CREATE INDEX IF NOT EXISTS idx_permissions_name ON permissions(name);

-- ==========================================
-- 3. 建立 role_permissions 表 (角色權限關聯)
-- ==========================================

CREATE TABLE IF NOT EXISTS role_permissions (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(role_id, permission_id)
);

COMMENT ON TABLE role_permissions IS '角色權限關聯表';

CREATE INDEX IF NOT EXISTS idx_role_permissions_role ON role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission ON role_permissions(permission_id);

-- ==========================================
-- 4. 建立 admin_roles 表 (管理員角色關聯)
-- ==========================================

CREATE TABLE IF NOT EXISTS admin_roles (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(admin_id, role_id)
);

COMMENT ON TABLE admin_roles IS '管理員角色關聯表 - 一個管理員可擁有多個角色';

CREATE INDEX IF NOT EXISTS idx_admin_roles_admin ON admin_roles(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_roles_role ON admin_roles(role_id);

-- ==========================================
-- 插入預設角色
-- ==========================================

INSERT INTO roles (name, display_name, description, is_system) VALUES
('super_admin', '超級管理員', '擁有所有權限，可管理系統所有功能', true),
('knowledge_manager', '知識庫管理員', '管理知識庫和意圖，包括新增、編輯、刪除等操作', true),
('tester', '測試人員', '執行測試和回測，查看測試結果', true),
('vendor_manager', '業者管理員', '管理業者資料和配置', true),
('config_manager', '配置管理員', '管理系統配置和設定', true),
('viewer', '唯讀用戶', '只能查看資料，無法進行任何修改操作', true)
ON CONFLICT (name) DO NOTHING;

-- ==========================================
-- 插入所有權限
-- ==========================================

-- 知識庫管理權限 (9 個)
INSERT INTO permissions (name, display_name, resource, action, description) VALUES
('knowledge:view', '查看知識', 'knowledge', 'view', '查看知識列表和詳情'),
('knowledge:create', '新增知識', 'knowledge', 'create', '新增知識項目'),
('knowledge:edit', '編輯知識', 'knowledge', 'edit', '修改知識內容'),
('knowledge:delete', '刪除知識', 'knowledge', 'delete', '刪除知識項目'),
('knowledge:import', '匯入知識', 'knowledge', 'import', '批量匯入知識'),
('knowledge:export', '匯出知識', 'knowledge', 'export', '匯出知識資料'),
('knowledge:reclassify', '重新分類', 'knowledge', 'reclassify', '重新分類知識'),
('knowledge:review', '審核知識', 'knowledge', 'review', '審核待審核知識'),
('knowledge:ai_review', 'AI 審核', 'knowledge', 'ai_review', '使用 AI 審核知識')
ON CONFLICT (name) DO NOTHING;

-- 意圖管理權限 (5 個)
INSERT INTO permissions (name, display_name, resource, action, description) VALUES
('intent:view', '查看意圖', 'intent', 'view', '查看意圖列表'),
('intent:create', '新增意圖', 'intent', 'create', '新增意圖'),
('intent:edit', '編輯意圖', 'intent', 'edit', '修改意圖'),
('intent:delete', '刪除意圖', 'intent', 'delete', '刪除意圖'),
('intent:suggest', '意圖建議', 'intent', 'suggest', '查看和管理建議意圖')
ON CONFLICT (name) DO NOTHING;

-- 測試與回測權限 (5 個)
INSERT INTO permissions (name, display_name, resource, action, description) VALUES
('test:backtest', '執行回測', 'test', 'backtest', '執行和查看回測結果'),
('test:chat', '對話測試', 'test', 'chat', '測試對話功能'),
('test:scenarios', '測試情境', 'test', 'scenarios', '查看測試情境'),
('test:scenarios_create', '新增測試情境', 'test', 'scenarios_create', '新增測試案例'),
('test:scenarios_edit', '編輯測試情境', 'test', 'scenarios_edit', '修改測試案例')
ON CONFLICT (name) DO NOTHING;

-- 業者管理權限 (5 個)
INSERT INTO permissions (name, display_name, resource, action, description) VALUES
('vendor:view', '查看業者', 'vendor', 'view', '查看業者列表'),
('vendor:create', '新增業者', 'vendor', 'create', '新增業者'),
('vendor:edit', '編輯業者', 'vendor', 'edit', '修改業者資料'),
('vendor:delete', '刪除業者', 'vendor', 'delete', '刪除業者'),
('vendor:config', '業者配置', 'vendor', 'config', '配置業者設定')
ON CONFLICT (name) DO NOTHING;

-- 平台 SOP 權限 (4 個)
INSERT INTO permissions (name, display_name, resource, action, description) VALUES
('sop:view', '查看 SOP', 'sop', 'view', '查看平台 SOP'),
('sop:create', '新增 SOP', 'sop', 'create', '新增 SOP 文檔'),
('sop:edit', '編輯 SOP', 'sop', 'edit', '修改 SOP 內容'),
('sop:delete', '刪除 SOP', 'sop', 'delete', '刪除 SOP 文檔')
ON CONFLICT (name) DO NOTHING;

-- 配置管理權限 (3 個)
INSERT INTO permissions (name, display_name, resource, action, description) VALUES
('config:business_types', '業態配置', 'config', 'business_types', '管理業態類型'),
('config:target_users', '目標用戶配置', 'config', 'target_users', '管理目標用戶設定'),
('config:cache', '快取管理', 'config', 'cache', '管理系統快取')
ON CONFLICT (name) DO NOTHING;

-- 文檔處理權限 (1 個)
INSERT INTO permissions (name, display_name, resource, action, description) VALUES
('document:convert', '文檔轉換', 'document', 'convert', '轉換文檔格式')
ON CONFLICT (name) DO NOTHING;

-- 系統管理權限 (9 個)
INSERT INTO permissions (name, display_name, resource, action, description) VALUES
('admin:view', '查看管理員', 'admin', 'view', '查看管理員列表'),
('admin:create', '新增管理員', 'admin', 'create', '新增管理員帳號'),
('admin:edit', '編輯管理員', 'admin', 'edit', '修改管理員資料'),
('admin:delete', '刪除管理員', 'admin', 'delete', '刪除管理員'),
('admin:reset_password', '重設密碼', 'admin', 'reset_password', '重設其他管理員密碼'),
('role:view', '查看角色', 'role', 'view', '查看角色列表'),
('role:create', '新增角色', 'role', 'create', '新增自訂角色'),
('role:edit', '編輯角色', 'role', 'edit', '修改角色權限'),
('role:delete', '刪除角色', 'role', 'delete', '刪除自訂角色')
ON CONFLICT (name) DO NOTHING;

-- ==========================================
-- 分配權限給角色
-- ==========================================

-- Super Admin - 擁有所有權限
INSERT INTO role_permissions (role_id, permission_id)
SELECT
    (SELECT id FROM roles WHERE name = 'super_admin'),
    id
FROM permissions
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Knowledge Manager - 知識庫和意圖管理
INSERT INTO role_permissions (role_id, permission_id)
SELECT
    (SELECT id FROM roles WHERE name = 'knowledge_manager'),
    id
FROM permissions
WHERE resource IN ('knowledge', 'intent', 'document')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Tester - 測試相關權限 + 唯讀知識和意圖
INSERT INTO role_permissions (role_id, permission_id)
SELECT
    (SELECT id FROM roles WHERE name = 'tester'),
    id
FROM permissions
WHERE resource = 'test'
   OR (resource = 'knowledge' AND action = 'view')
   OR (resource = 'intent' AND action = 'view')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Vendor Manager - 業者管理 + 唯讀知識和意圖
INSERT INTO role_permissions (role_id, permission_id)
SELECT
    (SELECT id FROM roles WHERE name = 'vendor_manager'),
    id
FROM permissions
WHERE resource = 'vendor'
   OR (resource = 'knowledge' AND action = 'view')
   OR (resource = 'intent' AND action = 'view')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Config Manager - 配置和 SOP 管理
INSERT INTO role_permissions (role_id, permission_id)
SELECT
    (SELECT id FROM roles WHERE name = 'config_manager'),
    id
FROM permissions
WHERE resource IN ('config', 'sop')
   OR (resource = 'knowledge' AND action = 'view')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Viewer - 只能查看
INSERT INTO role_permissions (role_id, permission_id)
SELECT
    (SELECT id FROM roles WHERE name = 'viewer'),
    id
FROM permissions
WHERE action = 'view'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- ==========================================
-- 為預設管理員分配超級管理員角色
-- ==========================================

INSERT INTO admin_roles (admin_id, role_id)
SELECT
    (SELECT id FROM admins WHERE username = 'admin' LIMIT 1),
    (SELECT id FROM roles WHERE name = 'super_admin')
WHERE EXISTS (SELECT 1 FROM admins WHERE username = 'admin')
ON CONFLICT (admin_id, role_id) DO NOTHING;

COMMIT;

-- ==========================================
-- 驗證和報告
-- ==========================================

-- 顯示統計資訊
DO $$
DECLARE
    roles_count INTEGER;
    permissions_count INTEGER;
    role_permissions_count INTEGER;
    admin_roles_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO roles_count FROM roles;
    SELECT COUNT(*) INTO permissions_count FROM permissions;
    SELECT COUNT(*) INTO role_permissions_count FROM role_permissions;
    SELECT COUNT(*) INTO admin_roles_count FROM admin_roles;

    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '✅ 權限系統資料庫建置完成！';
    RAISE NOTICE '========================================';
    RAISE NOTICE '角色數量: %', roles_count;
    RAISE NOTICE '權限數量: %', permissions_count;
    RAISE NOTICE '角色權限關聯: %', role_permissions_count;
    RAISE NOTICE '管理員角色關聯: %', admin_roles_count;
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
END $$;

-- 顯示角色列表
SELECT
    '角色列表:' AS info,
    name AS 角色代碼,
    display_name AS 顯示名稱,
    CASE WHEN is_system THEN '系統' ELSE '自訂' END AS 類型
FROM roles
ORDER BY id;
