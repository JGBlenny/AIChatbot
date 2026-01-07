# 帳號權限系統 - 總覽文檔

## 🎯 系統概述

本系統基於 **RBAC (Role-Based Access Control)** 設計，為管理後台提供靈活的權限管理功能。

### 核心特性

✅ **基於角色的權限管理** - 將權限分配給角色，再將角色分配給用戶
✅ **細粒度權限控制** - 40+ 個具體權限，覆蓋所有功能模組
✅ **前端權限控制** - 路由守衛、UI 元素顯示/隱藏、組件級權限控制
✅ **後端 API 保護** - 基於權限的 API 訪問控制
✅ **預設角色配置** - 6 個預設角色，開箱即用
✅ **靈活擴展** - 支援自訂角色和權限組合

---

## 📚 文檔導航

### 🚀 快速開始

如果你想**立即實作**權限系統，請閱讀：

👉 **[權限系統快速開始指南](./PERMISSION_QUICK_START.md)**

這份文檔提供：
- ✅ 步驟式實作教學
- ✅ 資料庫建置腳本
- ✅ 後端 API 代碼範例
- ✅ 前端整合步驟
- ✅ 驗證清單和常見問題

**預估時間：5-7 天完成基礎功能**

---

### 📐 系統設計

如果你想**深入了解**系統架構和設計理念，請閱讀：

👉 **[權限系統設計文檔](./PERMISSION_SYSTEM_DESIGN.md)**

這份文檔包含：
- 🎯 核心概念（權限、角色、用戶關聯）
- 📊 完整的資料庫設計
- 🔐 40+ 個權限定義
- 👥 6 個預設角色配置
- 🎨 前端架構設計（Store、指令、Composable）
- 🔧 後端 API 設計
- 📝 實作階段規劃

**適合：** 系統架構師、技術負責人

---

### 🎨 UI 設計

如果你想了解**前端介面**和用戶體驗設計，請閱讀：

👉 **[權限系統 UI 設計文檔](./PERMISSION_UI_DESIGN.md)**

這份文檔包含：
- 📄 完整的頁面布局設計
- 🧩 可重用組件設計
- 🔄 交互流程圖
- 📱 響應式設計方案
- 🎯 無障礙設計考量
- 💡 組件代碼範例

**適合：** 前端工程師、UI/UX 設計師

---

## 🏗️ 系統架構

### 數據模型

```
┌─────────────┐
│   Admins    │ (管理員)
└──────┬──────┘
       │
       │ N:M
       ↓
┌─────────────┐      ┌─────────────┐
│ Admin_Roles │ ←──→ │    Roles    │ (角色)
└─────────────┘      └──────┬──────┘
                            │
                            │ N:M
                            ↓
                     ┌─────────────────┐
                     │ Role_Permissions│
                     └────────┬────────┘
                              │
                              ↓
                     ┌─────────────┐
                     │ Permissions │ (權限)
                     └─────────────┘
```

### 權限檢查流程

```
用戶請求
   ↓
路由守衛檢查
   ├─ 需要登入？
   │   ├─ 是 → 檢查 Token
   │   └─ 否 → 允許訪問
   ↓
權限檢查
   ├─ 檢查路由權限
   ├─ 檢查用戶角色
   └─ 檢查具體權限
   ↓
允許訪問 / 跳轉 403
```

---

## 🎭 預設角色

系統提供 6 個預設角色：

| 角色 | 代碼 | 權限範圍 | 適用對象 |
|------|------|----------|----------|
| 🔐 超級管理員 | `super_admin` | 所有權限 | 系統管理員 |
| 📚 知識庫管理員 | `knowledge_manager` | 知識庫、意圖管理 | 內容管理人員 |
| 🧪 測試人員 | `tester` | 測試、回測功能 | QA 工程師 |
| 🏢 業者管理員 | `vendor_manager` | 業者資料管理 | 客戶服務人員 |
| ⚙️ 配置管理員 | `config_manager` | 系統配置、SOP | 運營人員 |
| 👁 唯讀用戶 | `viewer` | 只能查看 | 外部顧問、實習生 |

---

## 🔐 權限分類

系統共定義 **40+ 個權限**，分為 8 大類別：

### 1. 知識庫管理 (9 個權限)
- `knowledge:view` - 查看知識
- `knowledge:create` - 新增知識
- `knowledge:edit` - 編輯知識
- `knowledge:delete` - 刪除知識
- `knowledge:import` - 匯入知識
- `knowledge:export` - 匯出知識
- `knowledge:reclassify` - 重新分類
- `knowledge:review` - 審核知識
- `knowledge:ai_review` - AI 審核

### 2. 意圖管理 (5 個權限)
- `intent:view` - 查看意圖
- `intent:create` - 新增意圖
- `intent:edit` - 編輯意圖
- `intent:delete` - 刪除意圖
- `intent:suggest` - 意圖建議

### 3. 測試與回測 (5 個權限)
- `test:backtest` - 執行回測
- `test:chat` - 對話測試
- `test:scenarios` - 測試情境
- `test:scenarios_create` - 新增測試情境
- `test:scenarios_edit` - 編輯測試情境

### 4. 業者管理 (5 個權限)
- `vendor:view` - 查看業者
- `vendor:create` - 新增業者
- `vendor:edit` - 編輯業者
- `vendor:delete` - 刪除業者
- `vendor:config` - 業者配置

### 5. 平台 SOP (4 個權限)
- `sop:view` - 查看 SOP
- `sop:create` - 新增 SOP
- `sop:edit` - 編輯 SOP
- `sop:delete` - 刪除 SOP

### 6. 配置管理 (3 個權限)
- `config:business_types` - 業態配置
- `config:target_users` - 目標用戶配置
- `config:cache` - 快取管理

### 7. 文檔處理 (1 個權限)
- `document:convert` - 文檔轉換

### 8. 系統管理 (9 個權限)
- `admin:view` - 查看管理員
- `admin:create` - 新增管理員
- `admin:edit` - 編輯管理員
- `admin:delete` - 刪除管理員
- `admin:reset_password` - 重設密碼
- `role:view` - 查看角色
- `role:create` - 新增角色
- `role:edit` - 編輯角色
- `role:delete` - 刪除角色

---

## 💻 前端使用範例

### 1. 使用 v-permission 指令

```vue
<template>
  <!-- 單一權限 -->
  <button v-permission="'knowledge:create'">新增知識</button>

  <!-- 多個權限 (OR) -->
  <button v-permission="['knowledge:edit', 'knowledge:delete']">
    編輯或刪除
  </button>

  <!-- 多個權限 (AND) -->
  <button v-permission.all="['knowledge:edit', 'knowledge:delete']">
    編輯且刪除
  </button>
</template>
```

### 2. 使用 Composable

```vue
<template>
  <button v-if="can('knowledge:create')">新增知識</button>
  <button v-if="canAny(['knowledge:edit', 'knowledge:delete'])">
    編輯或刪除
  </button>
  <button v-if="isAdmin">管理員專屬功能</button>
</template>

<script setup>
import { usePermission } from '@/composables/usePermission'

const { can, canAny, canAll, isAdmin } = usePermission()
</script>
```

### 3. 路由權限控制

```javascript
{
  path: '/knowledge',
  name: 'Knowledge',
  component: KnowledgeView,
  meta: {
    requiresAuth: true,
    permissions: ['knowledge:view']  // 需要的權限
  }
}
```

---

## 🔧 後端使用範例

### 1. 使用權限裝飾器

```python
from auth_utils import require_permission

@app.get("/api/knowledge", dependencies=[Depends(require_permission("knowledge:view"))])
async def list_knowledge():
    # ...
```

### 2. 在函數內檢查

```python
@app.post("/api/knowledge")
async def create_knowledge(data: KnowledgeCreate, user: dict = Depends(get_current_user)):
    if not await has_permission(user['id'], 'knowledge:create'):
        raise HTTPException(status_code=403, detail="缺少權限")
    # ...
```

---

## 📅 實作時程規劃

### 階段 1: 資料庫建置 (1-2 天)
- [ ] 創建 4 個資料表
- [ ] 插入預設角色和權限
- [ ] 測試資料完整性

### 階段 2: 後端 API 開發 (2-3 天)
- [ ] 權限查詢 API
- [ ] 角色管理 API
- [ ] 權限驗證中介軟體
- [ ] 單元測試

### 階段 3: 前端基礎建設 (2-3 天)
- [ ] 擴展 Auth Store
- [ ] 創建權限指令和 Composable
- [ ] 更新路由守衛
- [ ] 創建 403 頁面

### 階段 4: UI 開發 (3-4 天)
- [ ] 角色管理頁面
- [ ] 權限管理頁面
- [ ] 管理員角色分配
- [ ] 菜單權限過濾

### 階段 5: 測試與優化 (2-3 天)
- [ ] 功能測試
- [ ] UI/UX 測試
- [ ] 性能測試
- [ ] 文檔撰寫

**總計：10-15 天**

---

## ✅ 驗證檢查清單

### 資料庫
- [ ] 4 個表格正確創建
- [ ] 6 個預設角色已插入
- [ ] 40+ 個權限已插入
- [ ] 角色權限關聯正確
- [ ] 預設管理員已分配角色

### 後端
- [ ] `/api/auth/permissions` API 正常
- [ ] 權限驗證中介軟體運作正常
- [ ] 超級管理員可訪問所有 API
- [ ] 無權限用戶被正確拒絕 (403)

### 前端
- [ ] 登入後自動獲取權限
- [ ] `v-permission` 指令正常運作
- [ ] 路由守衛正確攔截
- [ ] 菜單根據權限過濾
- [ ] 403 頁面正確顯示

### 用戶體驗
- [ ] 權限不足時有明確提示
- [ ] 無權限的按鈕正確隱藏
- [ ] 角色管理介面直觀易用
- [ ] 權限分配流程順暢

---

## 🔗 相關文檔

### 權限系統
- [快速開始指南](./PERMISSION_QUICK_START.md) ⭐ 推薦
- [系統設計文檔](./PERMISSION_SYSTEM_DESIGN.md)
- [UI 設計文檔](./PERMISSION_UI_DESIGN.md)

### 認證系統
- [認證系統總覽](./AUTH_SYSTEM_README.md)
- [認證部署指南](./AUTH_DEPLOYMENT_GUIDE.md)
- [認證實作總結](./AUTH_IMPLEMENTATION_SUMMARY.md)

### 管理功能
- [管理員管理計劃](./ADMIN_MANAGEMENT_PLAN.md)

---

## 💡 最佳實踐

### 1. 權限粒度
- ✅ 使用細粒度權限（如 `knowledge:create`）
- ❌ 避免過於籠統的權限（如 `knowledge:all`）

### 2. 角色設計
- ✅ 基於職責設計角色
- ✅ 一個用戶可擁有多個角色
- ❌ 避免創建過多相似角色

### 3. 前端實作
- ✅ 使用指令隱藏無權限元素
- ✅ 路由守衛阻止未授權訪問
- ⚠️ 前端權限僅用於 UI，安全依賴後端

### 4. 後端實作
- ✅ 所有 API 都應檢查權限
- ✅ 使用中介軟體統一處理
- ✅ 記錄權限驗證失敗日誌

---

## 📞 需要幫助？

- 💬 查看文檔中的範例代碼
- 🐛 檢查常見問題章節
- 📧 聯絡系統管理員

---

**文檔版本：** 1.0.0
**最後更新：** 2026-01-06
**維護者：** AIChatbot Team
**預估實作時間：** 10-15 天

---

## 🎯 從這裡開始

1. **閱讀** → [快速開始指南](./PERMISSION_QUICK_START.md)
2. **實作** → 跟隨步驟建置系統
3. **測試** → 使用驗證清單檢查
4. **部署** → 發布到生產環境

祝你實作順利！🚀
