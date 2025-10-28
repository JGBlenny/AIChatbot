# 配置管理系統更新摘要

**更新日期**: 2025-10-28

## 🎯 快速概覽

本次更新優化了所有配置管理功能，主要包括：

1. ✅ 新增 **Target User Config** 管理頁面
2. ✅ 移除舊的 **Audience Config** 頁面
3. ✅ 移除不必要的 **icon** 和 **display_order** 欄位
4. ✅ 優化排序機制，改用 **id** 排序

## 📊 配置管理系統總覽

### 1. Business Types Config (業態類型配置)

**管理頁面**: `http://localhost:8087/business-types-config`

**用途**: 定義知識庫支援的業態類型（如：租屋、買房、物業管理等）

**欄位**:
- `type_value` - 業態值（系統內部使用）
- `display_name` - 顯示名稱
- `description` - 描述
- `color` - 顏色標記
- `tone_prompt` - 語氣提示詞
- `is_active` - 是否啟用

**變更**:
- ❌ 移除 `icon` 欄位顯示
- ❌ 移除 `display_order` 排序
- ✅ 改用 `ORDER BY id`

### 2. Target User Config (目標用戶配置) 🆕

**管理頁面**: `http://localhost:8087/target-users-config`

**用途**: 定義知識庫的目標用戶類型（如：租客、房東、物業管理師等）

**欄位**:
- `user_value` - 用戶值（系統內部使用，建立後不可修改）
- `display_name` - 顯示名稱
- `description` - 描述
- `is_active` - 是否啟用

**特色**:
- ✅ 完整 CRUD 功能
- ✅ 軟刪除機制（is_active）
- ✅ 清晰的功能說明和警告提示
- ✅ 簡潔的 UI 設計（無 icon、無 display_order）

**⚠️ 注意**: 目前功能尚未生效，需要整合用戶登入系統

### 3. Category Config (分類配置)

**管理頁面**: `http://localhost:8087/category-config`

**用途**: 定義知識庫的分類標籤

**欄位**:
- `category_value` - 分類值
- `display_name` - 顯示名稱
- `description` - 描述
- `usage_count` - 使用次數
- `is_active` - 是否啟用

**變更**:
- ❌ 移除 `display_order` 排序
- ✅ 改用 `ORDER BY id`

### 4. ~~Audience Config (受眾配置)~~ ❌ 已移除

**狀態**: 已被 Target User Config 取代

**遷移**:
- 舊路由 `/audience-config` 現在重定向到 `/target-users-config`
- 導航選單已更新為 "目標用戶" 👥

## 🗄️ 資料庫架構

### 配置表結構

```sql
-- Business Types Config
CREATE TABLE business_types_config (
    id SERIAL PRIMARY KEY,
    type_value VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    color VARCHAR(50),
    tone_prompt TEXT,
    icon VARCHAR(50),              -- ❌ 不再使用
    display_order INTEGER,         -- ❌ 不再使用
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Target User Config
CREATE TABLE target_user_config (
    id SERIAL PRIMARY KEY,
    user_value VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(50),              -- ❌ 不再使用
    display_order INTEGER,         -- ❌ 不再使用
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Category Config
CREATE TABLE category_config (
    id SERIAL PRIMARY KEY,
    category_value VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    display_order INTEGER,         -- ❌ 不再使用
    usage_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Knowledge Base 使用方式

```sql
CREATE TABLE knowledge_base (
    id SERIAL PRIMARY KEY,
    question_summary TEXT NOT NULL,
    answer TEXT NOT NULL,
    keywords TEXT[],
    business_types VARCHAR(50)[],  -- 參照 business_types_config.type_value
    target_user VARCHAR(50)[],     -- 參照 target_user_config.user_value
    category VARCHAR(50),           -- 參照 category_config.category_value
    -- ... 其他欄位
);
```

## 🔄 API 端點總覽

### Business Types Config

```
GET    /api/business-types-config          # 列表（管理用）
POST   /api/business-types-config          # 新增
PUT    /api/business-types-config/{id}     # 更新
DELETE /api/business-types-config/{id}     # 停用
```

### Target User Config

```
GET    /api/target-users                   # 啟用列表（選擇器用）
GET    /api/target-users-config            # 完整列表（管理用）
POST   /api/target-users-config            # 新增
PUT    /api/target-users-config/{user_value}  # 更新
DELETE /api/target-users-config/{user_value}  # 停用
```

### Category Config

```
GET    /api/category-config                # 列表
POST   /api/category-config                # 新增
PUT    /api/category-config/{id}           # 更新
DELETE /api/category-config/{id}           # 停用
```

## 🎨 前端頁面路由

```javascript
// 配置管理相關路由
{
  path: '/business-types-config',
  name: 'BusinessTypesConfig',
  component: BusinessTypesConfigView
},
{
  path: '/target-users-config',      // 🆕 新增
  name: 'TargetUsersConfig',
  component: TargetUserConfigView
},
{
  path: '/category-config',
  name: 'CategoryConfig',
  component: CategoryConfigView
},
{
  path: '/audience-config',          // ❌ 重定向
  redirect: '/target-users-config'
}
```

## 📝 使用範例

### 1. 管理員配置目標用戶

```javascript
// 訪問管理頁面
http://localhost:8087/target-users-config

// 新增目標用戶
{
  "user_value": "tenant",
  "display_name": "租客",
  "description": "租屋用戶，關注租金、維修、合約等問題"
}
```

### 2. 在知識庫中使用

```javascript
// 編輯知識時選擇目標用戶
http://localhost:8087/knowledge

// 知識配置
{
  "question_summary": "租金逾期如何處理？",
  "answer": "...",
  "business_types": ["rent"],           // 業態類型
  "target_user": ["tenant", "property_manager"],  // 目標用戶 🆕
  "category": "payment"                 // 分類
}
```

### 3. RAG 檢索時過濾 (未來功能)

```javascript
// 聊天請求
POST /api/v1/chat
{
  "question": "租金逾期怎麼辦？",
  "vendor_id": 1,
  "user_role": "tenant"  // 🆕 用戶身份
}

// 後端會自動過濾知識：
// WHERE target_user IS NULL OR 'tenant' = ANY(target_user)
```

## 🔧 技術改進

### 排序機制

**之前**:
```sql
ORDER BY display_order, user_value
```

**現在**:
```sql
ORDER BY id
```

**優點**:
- ✅ 自動按建立順序排列
- ✅ 不需手動維護排序數字
- ✅ 查詢效率更好（id 是主鍵）

### UI 簡化

**之前**:
```vue
<span v-if="item.icon">{{ item.icon }}</span>
{{ item.display_name }}
<input v-model="formData.display_order" type="number" />
```

**現在**:
```vue
{{ item.display_name }}
```

## ⚠️ 注意事項

### 1. Target User 功能尚未生效

**原因**:
- 系統缺少用戶登入機制
- 無法識別用戶身份 (user_role)

**現況**:
- 所有用戶看到所有知識
- target_user 過濾暫時無作用

**啟用條件**:
- 前端整合用戶登入系統
- 聊天請求傳入正確的 `user_role` 參數

### 2. 保留的欄位

**保留但不使用的欄位**:
- `icon` - 已設為 NULL
- `display_order` - 已不用於排序

**原因**:
- 避免大規模 schema 變更
- 保留未來彈性

**可選操作**:
- 未來可建立 migration 移除這些欄位
- 或保持現狀（推薦）

## 📚 詳細文檔

- [Target User Config 實作完成報告](./archive/completion_reports/TARGET_USER_CONFIG_IMPLEMENTATION.md)
- [系統架構文檔](./architecture/SYSTEM_ARCHITECTURE.md)
- [業務範圍認證架構](./architecture/AUTH_AND_BUSINESS_SCOPE.md)

## 🚀 下一步計劃

1. **整合用戶認證系統**
   - 實作用戶登入功能
   - 在聊天請求中傳入 user_role
   - 測試 target_user 過濾

2. **資料庫優化** (可選)
   - 評估是否移除 icon 欄位
   - 評估是否移除 display_order 欄位
   - 建立 migration 腳本

3. **測試與驗證**
   - 端到端測試 target_user 過濾
   - 效能測試
   - 用戶體驗測試

## 📊 變更統計

**新增**:
- 1 個新頁面 (TargetUserConfigView)
- 5 個新 API 端點
- 1 個新路由

**修改**:
- 4 個檔案的排序邏輯
- 1 個導航選單項目
- 2 個知識庫選擇器顯示

**移除**:
- 1 個舊頁面 (AudienceConfigView，透過重定向)
- 2 個表單欄位 (icon, display_order)
- 3 個排序參數 (display_order)

**資料庫清理**:
- 7 筆 icon 資料設為 NULL

---

**更新完成時間**: 2025-10-28
**狀態**: ✅ 已完成並測試
**維護者**: 系統開發團隊
