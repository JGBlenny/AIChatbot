# Target User Config 實作完成報告

**日期**: 2025-10-28
**狀態**: ✅ 完成

## 📋 概述

本次更新實作了完整的目標用戶配置管理系統，取代舊有的受眾配置（Audience Config），並優化了所有配置管理介面，移除不必要的欄位，簡化系統維護。

## 🎯 主要功能

### 1. Target User Config 管理頁面

創建了完整的目標用戶配置 CRUD 管理介面：

**前端頁面**: `/target-users-config`
- ✅ 列表展示所有目標用戶類型
- ✅ 新增目標用戶類型
- ✅ 編輯目標用戶資訊
- ✅ 啟用/停用目標用戶（軟刪除）
- ✅ 警告提示框說明功能尚未生效（需要用戶登入系統）

**後端 API 端點**:
- `GET /api/target-users` - 取得啟用的目標用戶列表（供知識庫選擇器使用）
- `GET /api/target-users-config` - 取得所有目標用戶配置（管理用）
- `POST /api/target-users-config` - 新增目標用戶
- `PUT /api/target-users-config/{user_value}` - 更新目標用戶
- `DELETE /api/target-users-config/{user_value}` - 停用目標用戶（軟刪除）

### 2. 遷移與清理

#### 2.1 從 Audience Config 遷移到 Target User Config

**移除的檔案**:
- `AudienceConfigView.vue` - 舊的受眾配置頁面

**更新的路由**:
```javascript
// 舊路由重定向到新路由
{
  path: '/audience-config',
  redirect: '/target-users-config'
}
```

**更新的導航選單**:
- 名稱: "受眾配置" → "目標用戶"
- 圖示: 👤 → 👥
- 路徑: `/audience-config` → `/target-users-config`

#### 2.2 移除不必要的欄位

**移除的欄位**:
1. **icon** (圖示)
   - 前端表單：完全移除 icon 輸入欄位
   - 前端顯示：移除知識庫選擇器中的圖示顯示
   - 資料庫：將所有表的 icon 欄位設為 NULL

2. **display_order** (顯示順序)
   - 前端表單：完全移除 display_order 輸入欄位
   - 後端排序：改用 `ORDER BY id` 取代 `ORDER BY display_order`

**資料庫清理**:
```sql
-- 清除 business_types_config 的 icon
UPDATE business_types_config SET icon = NULL;  -- 影響 3 筆資料

-- 清除 target_user_config 的 icon
UPDATE target_user_config SET icon = NULL;  -- 影響 4 筆資料
```

### 3. 排序機制優化

**變更的檔案**:

1. **knowledge-admin/backend/app.py**
   - Line 575: `/api/target-users` - 改用 `ORDER BY id`
   - Line 607: `/api/target-users-config` - 改用 `ORDER BY id`
   - Line 1509: Category config - 改用 `ORDER BY id`

2. **rag-orchestrator/routers/business_types_config.py**
   - Line 71: Business types config - 改用 `ORDER BY id`

**優點**:
- 自動按照建立順序排列
- 不需要手動維護排序數字
- 查詢效率更好（id 是主鍵，有索引）

## 📁 檔案變更清單

### 新增檔案

```
knowledge-admin/frontend/src/views/TargetUserConfigView.vue
```

### 修改檔案

```
knowledge-admin/backend/app.py
  - 新增 target_user_config CRUD API 端點
  - 更新排序邏輯（移除 display_order）

knowledge-admin/frontend/src/router.js
  - 新增 TargetUserConfigView 路由
  - 新增 /audience-config 重定向
  - 移除 AudienceConfigView 引用

knowledge-admin/frontend/src/App.vue
  - 更新導航選單項目
  - 更新頁面標題對應

knowledge-admin/frontend/src/views/KnowledgeView.vue
  - 移除業態類型選擇器的 icon 顯示
  - 移除目標用戶選擇器的 icon 顯示

rag-orchestrator/routers/business_types_config.py
  - 更新排序邏輯（移除 display_order）
```

### 移除檔案

```
knowledge-admin/frontend/src/views/AudienceConfigView.vue (透過重定向處理)
```

## 🗄️ 資料庫變更

### 清理資料

```sql
-- Target User Config
UPDATE target_user_config SET icon = NULL;

-- Business Types Config
UPDATE business_types_config SET icon = NULL;
```

### 欄位使用變更

- **icon**: 不再使用（資料設為 NULL）
- **display_order**: 不再使用於排序（改用 id）

**注意**: 欄位本身仍保留在資料庫中，但不再使用。未來可考慮移除這些欄位。

## 🎨 UI/UX 改進

### 1. TargetUserConfigView 介面設計

**資訊提示框**:
```
📝 說明：
- 目標用戶用於定義知識庫針對的用戶類型（如：租客、房東、物業管理師）
- 每筆知識可以選擇一種或多種目標用戶
- 未指定目標用戶的知識視為「通用知識」，對所有用戶可見
- ⚠️ 停用目標用戶前，請確認相關知識的可見性設定
```

**警告提示框**:
```
⚠️ 目前此功能尚未生效

由於系統缺少用戶登入機制，無法識別用戶身份（tenant/landlord/property_manager 等），
因此 target_user 過濾功能暫時無作用。

當前所有用戶都能看到所有知識，不受 target_user 設定限制。

待整合：當您的應用系統接入並在聊天請求中傳入正確的 user_role 參數時，此功能將自動生效。
```

**表單欄位** (簡化設計):
1. **用戶值** (user_value)
   - 必填
   - 只能使用小寫英文字母和底線
   - 建立後不可修改
   - 用於 `knowledge_base.target_user` 陣列

2. **顯示名稱** (display_name)
   - 必填
   - 在前端顯示的名稱
   - 可以是中文

3. **說明** (description)
   - 選填
   - 描述此目標用戶的特徵和用途

### 2. KnowledgeView 選擇器簡化

**之前**:
```vue
<span v-if="btype.icon" class="tag-icon">{{ btype.icon }}</span>
{{ btype.display_name }}
```

**之後**:
```vue
{{ btype.display_name }}
```

## 🔧 技術實作細節

### API 設計模式

採用 RESTful API 設計：

```python
# Pydantic 模型
class TargetUserConfigCreate(BaseModel):
    user_value: str
    display_name: str
    description: Optional[str] = None

class TargetUserConfigUpdate(BaseModel):
    display_name: str
    description: Optional[str] = None
    is_active: Optional[bool] = None
```

### 軟刪除模式

使用 `is_active` 標記而非硬刪除：

```python
# 停用（軟刪除）
DELETE /api/target-users-config/{user_value}
→ UPDATE target_user_config SET is_active = FALSE

# 啟用
PUT /api/target-users-config/{user_value}
→ UPDATE target_user_config SET is_active = TRUE
```

### 前端狀態管理

```vue
<script>
export default {
  data() {
    return {
      targetUsersList: [],
      loading: false,
      showModal: false,
      editingItem: null,
      saving: false,
      formData: {
        user_value: '',
        display_name: '',
        description: ''
      }
    };
  }
}
</script>
```

## 📊 Target User 功能說明

### 運作流程

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 管理員在「目標用戶管理頁面」配置                           │
│    http://localhost:8087/target-users-config                 │
│                                                              │
│    定義系統支援的用戶類型：                                   │
│    • tenant (租客)                                           │
│    • landlord (房東)                                         │
│    • property_manager (物業管理師)                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. 管理員在「知識庫管理」新增知識                             │
│    http://localhost:8087/knowledge                           │
│                                                              │
│    知識 A：「租金逾期如何處理？」                             │
│    目標用戶：☑ 租客  ☑ 物業管理師                            │
│    → knowledge_base.target_user = ['tenant', 'property_manager']
│                                                              │
│    知識 B：「如何催繳租金？」                                 │
│    目標用戶：☑ 房東  ☑ 物業管理師                            │
│    → knowledge_base.target_user = ['landlord', 'property_manager']
│                                                              │
│    知識 C：「租金繳費方式」                                   │
│    目標用戶：未選擇（通用知識）                               │
│    → knowledge_base.target_user = NULL                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. 用戶提問時，系統傳入 user_role 參數                       │
│                                                              │
│    租客提問：「租金逾期怎麼辦？」                             │
│    → user_role = 'tenant'                                    │
│    → RAG 過濾：target_user IS NULL OR 'tenant' = ANY(target_user)
│    → ✅ 返回知識 A、C（不返回知識 B）                        │
│                                                              │
│    房東提問：「租金逾期怎麼辦？」                             │
│    → user_role = 'landlord'                                  │
│    → RAG 過濾：target_user IS NULL OR 'landlord' = ANY(target_user)
│    → ✅ 返回知識 B、C（不返回知識 A）                        │
└─────────────────────────────────────────────────────────────┘
```

### 資料表關係

**target_user_config 表** (配置表):
- 作用：定義「系統支援哪些用戶類型選項」
- 類比：建立「下拉選單的選項」

**knowledge_base.target_user 欄位** (PostgreSQL ARRAY):
- 作用：每條知識可以指定「適用於哪些用戶類型」
- 類比：「這條知識給誰看」

**聊天請求的 user_role 參數**:
- 作用：表示「當前用戶的身份」
- 類比：「我是誰」

## ⚠️ 已知限制

### 1. 功能尚未生效

**原因**: 系統缺少用戶登入機制

**影響**:
- 無法識別用戶身份（tenant/landlord/property_manager 等）
- `target_user` 過濾功能暫時無作用
- 當前所有用戶都能看到所有知識，不受 target_user 設定限制

**解決方案**:
- 當應用系統接入並在聊天請求中傳入正確的 `user_role` 參數時，此功能將自動生效
- 後端 RAG 檢索邏輯已完成，只需前端整合用戶認證系統

### 2. 欄位保留

**保留的欄位**:
- `icon` - 已設為 NULL，但欄位仍存在
- `display_order` - 已不再使用，但欄位仍存在

**原因**:
- 避免大規模資料庫 schema 變更
- 保留彈性，未來可能重新使用

**未來考慮**:
- 可以建立 migration 腳本移除這些欄位
- 或保持現狀，僅在應用層面不使用

## 🧪 測試建議

### 1. 功能測試

```bash
# 1. 測試 Target User Config CRUD
curl http://localhost:5001/api/target-users-config

# 2. 測試新增目標用戶
curl -X POST http://localhost:5001/api/target-users-config \
  -H "Content-Type: application/json" \
  -d '{
    "user_value": "test_user",
    "display_name": "測試用戶",
    "description": "測試用"
  }'

# 3. 測試更新目標用戶
curl -X PUT http://localhost:5001/api/target-users-config/test_user \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "測試用戶 (已更新)",
    "description": "更新後的描述"
  }'

# 4. 測試停用目標用戶
curl -X DELETE http://localhost:5001/api/target-users-config/test_user
```

### 2. UI 測試

1. **管理頁面測試**:
   - 訪問 `http://localhost:8087/target-users-config`
   - 確認列表正確顯示
   - 測試新增、編輯、啟用、停用功能
   - 確認警告提示框正確顯示

2. **知識庫編輯測試**:
   - 訪問 `http://localhost:8087/knowledge`
   - 編輯或新增知識
   - 確認目標用戶選擇器正確顯示（無圖示）
   - 確認可以多選目標用戶

3. **路由重定向測試**:
   - 訪問 `http://localhost:8087/audience-config`
   - 確認自動重定向到 `/target-users-config`

### 3. 資料庫驗證

```sql
-- 驗證 icon 已清除
SELECT user_value, display_name, icon
FROM target_user_config;

SELECT type_value, display_name, icon
FROM business_types_config;

-- 驗證排序使用 id
-- 應該看到資料按 id 順序排列，而非 display_order
```

## 📚 相關文檔

- [Business Types Config 測試報告](../2025-Q4/testing/BUSINESS_TYPE_TEST_REPORT.md)
- [受眾選擇器改進報告](./AUDIENCE_SELECTOR_IMPROVEMENT.md)
- [系統架構文檔](../../architecture/SYSTEM_ARCHITECTURE.md)
- [業務範圍認證架構](../2025-Q4/architecture/AUTH_AND_BUSINESS_SCOPE.md)

## 🎉 總結

本次更新成功實作了 Target User Config 管理系統，並優化了整體配置管理介面：

**完成項目**:
- ✅ 創建完整的目標用戶配置 CRUD 介面
- ✅ 從 Audience Config 平滑遷移到 Target User Config
- ✅ 移除不必要的 icon 和 display_order 欄位
- ✅ 清理資料庫中的冗餘資料
- ✅ 優化排序機制，使用 id 排序
- ✅ 更新所有相關 API 端點
- ✅ 添加清晰的使用說明和警告提示

**系統改進**:
- 介面更簡潔，易於維護
- 排序邏輯更高效
- 程式碼更清晰，減少技術債
- 為未來用戶認證整合做好準備

**下一步**:
- 整合用戶登入/認證系統
- 實作 user_role 參數傳遞機制
- 測試 target_user 過濾功能
- 考慮移除資料庫中不再使用的欄位
