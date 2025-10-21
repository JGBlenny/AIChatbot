# 🎯 系統待開發/完善功能清單

生成日期: 2025-10-13
系統狀態: Phase 1 完成 ✅

---

## 📊 功能狀態總覽

### ✅ Phase 1 已完成 (100%)
- RAG 智能問答系統
- 多業者 SaaS 架構
- 知識庫管理（向量搜尋 + LLM 優化）
- 測試情境管理系統
- 審核中心（4 個審核模組）
- 意圖管理與建議引擎
- 知識匯入系統（批量 + 去重）
- 回測框架（3 種評估模式）
- Business Scope 動態切換（B2B/B2C）

### ⏳ Phase 2 待開發 (0%) - **外部 API 整合**

---

## 🔥 Phase 2: 高優先級功能（規劃中）

### 1️⃣ 租客身份識別系統 🆕
**功能描述**: 從自然語言對話中自動識別租客身份

**需求**:
- [ ] 建立 `tenants` 資料表
- [ ] 實作 TenantIdentifier 服務（LLM 提取 + 模糊比對）
- [ ] 支援多種識別方式：
  - 姓名（"林小姐"）
  - 租約編號（"A-2024-001"）
  - 房號（"302 房"）
  - 電話（"0912-345-678"）
  - 身份證字號
- [ ] 多候選處理（如有多個符合，要求確認）
- [ ] 對話上下文記憶

**資料表**:
```sql
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER REFERENCES vendors(id),
    tenant_code VARCHAR(50) UNIQUE,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    room_number VARCHAR(50),
    contract_start_date DATE,
    contract_end_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    external_id VARCHAR(100),
    ...
);
```

**API 端點**:
- `GET /api/v1/vendors/{vendor_id}/tenants` - 租客列表
- `POST /api/v1/vendors/{vendor_id}/tenants` - 建立租客
- `GET /api/v1/tenants/search` - 搜尋租客（支援模糊比對）

**前端頁面**:
- 租客管理頁面 (`/vendors/{vendor_id}/tenants`)
- 租客 CRUD 介面
- CSV 匯入/匯出

**預計時程**: 2 週

---

### 2️⃣ 外部 API 整合框架 🆕
**功能描述**: 讓業者配置自己的既有系統 API，AI 可呼叫查詢資料或執行操作

**需求**:
- [ ] 建立 `vendor_apis`, `vendor_api_endpoints`, `vendor_api_logs` 資料表
- [ ] 實作 ExternalAPIClient 服務
- [ ] 支援多種認證方式：
  - API Key
  - OAuth 2.0
  - Basic Auth
- [ ] 參數對應與回應格式化
- [ ] 錯誤處理與重試機制（timeout, retry_count）
- [ ] 完整日誌記錄

**資料表**:
```sql
CREATE TABLE vendor_apis (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER REFERENCES vendors(id),
    api_name VARCHAR(100),
    base_url VARCHAR(500),
    auth_type VARCHAR(50),  -- none, api_key, oauth, basic
    auth_config JSONB,      -- 加密儲存
    timeout_ms INTEGER DEFAULT 10000,
    retry_count INTEGER DEFAULT 3,
    ...
);

CREATE TABLE vendor_api_endpoints (
    id SERIAL PRIMARY KEY,
    api_id INTEGER REFERENCES vendor_apis(id),
    endpoint_name VARCHAR(100),
    intent_id INTEGER REFERENCES intents(id),
    http_method VARCHAR(10),
    path VARCHAR(500),
    param_mapping JSONB,     -- 參數對應規則
    response_mapping JSONB,  -- 回應格式化
    ...
);

CREATE TABLE vendor_api_logs (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER,
    endpoint_id INTEGER,
    request_params JSONB,
    response_data JSONB,
    status_code INTEGER,
    response_time_ms INTEGER,
    error_message TEXT,
    ...
);
```

**API 端點**:
- `GET /api/v1/vendors/{vendor_id}/apis` - API 配置列表
- `POST /api/v1/vendors/{vendor_id}/apis` - 建立 API 配置
- `POST /api/v1/apis/{api_id}/endpoints` - 建立端點配置
- `POST /api/v1/apis/{api_id}/test` - 測試 API 連線
- `GET /api/v1/vendors/{vendor_id}/api-logs` - 查詢呼叫日誌

**前端頁面**:
- API 配置頁面 (`/vendors/{vendor_id}/api-settings`)
- API 端點管理
- 參數對應設定（可視化介面）
- 測試連線功能
- API 日誌頁面 (`/vendors/{vendor_id}/api-logs`)
  - 過濾（成功/失敗、端點、時間）
  - 統計圖表（呼叫次數、成功率、回應時間）

**預計時程**: 3 週

---

### 3️⃣ 客服助理整合服務 🆕
**功能描述**: 整合所有服務，支援混合查詢（知識 + 資料）

**需求**:
- [ ] 實作 CustomerServiceAssistant 服務
- [ ] 擴展意圖類型：
  - `knowledge` - 知識查詢
  - `data_query` - 資料查詢（需呼叫 API）
  - `action` - 操作執行（需呼叫 API）
  - `mixed` - 混合查詢
- [ ] 對話上下文管理
- [ ] 統一回應格式

**API 端點**:
- `POST /api/v1/chat/customer-service` - 客服專用聊天端點

**請求範例**:
```json
{
  "message": "林小姐這個月繳費了嗎？",
  "vendor_id": 1,
  "user_id": "cs_staff_001",
  "conversation_id": "conv_20241010_001"
}
```

**回應範例**:
```json
{
  "answer": "林小姐（租約編號：A-2024-001）已於 10 月 3 日繳清本月租金 15,000 元...",
  "intent_type": "data_query",
  "tenant_identified": true,
  "tenant_info": {...},
  "api_called": true,
  "api_response": {...},
  "processing_details": {...}
}
```

**前端頁面**:
- 客服助理頁面 (`/customer-service`)
- 租客快速識別輸入
- 對話歷史記錄
- API 呼叫狀態顯示
- 知識來源參考

**預計時程**: 2 週

**總計 Phase 2 時程**: 預估 7-8 週

---

## 🟡 中優先級功能（未規劃）

### 4️⃣ 分析與報表系統
**功能描述**: 使用量統計和數據分析

**需求**:
- [ ] 對話量統計（按日/週/月）
- [ ] 熱門問題排行榜
- [ ] 意圖分布統計
- [ ] 信心度分布分析
- [ ] 業者使用情況統計
- [ ] API 呼叫統計（Phase 2 後）
- [ ] Dashboard 視覺化

**前端頁面**:
- 統計儀表板 (`/analytics`)
- 圖表視覺化（Chart.js / ECharts）

**預計時程**: 2-3 週

---

### 5️⃣ 用戶認證與權限系統
**功能描述**: 多角色用戶管理

**需求**:
- [ ] 用戶登入/註冊
- [ ] JWT Token 認證
- [ ] 角色權限管理：
  - 超級管理員（系統管理）
  - 業者管理員（業者資料管理）
  - 客服人員（只能使用 Chat）
  - 租客（只能問問題）
- [ ] API 權限中介層
- [ ] 前端路由守衛

**資料表**:
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    role VARCHAR(50),
    vendor_id INTEGER REFERENCES vendors(id),
    is_active BOOLEAN DEFAULT true,
    ...
);

CREATE TABLE user_permissions (
    user_id INTEGER REFERENCES users(id),
    resource VARCHAR(100),
    actions JSONB,  -- ["read", "write", "delete"]
    ...
);
```

**API 端點**:
- `POST /api/v1/auth/login` - 登入
- `POST /api/v1/auth/register` - 註冊
- `POST /api/v1/auth/refresh` - 刷新 Token
- `GET /api/v1/users` - 用戶列表
- `POST /api/v1/users/{user_id}/permissions` - 設定權限

**預計時程**: 2-3 週

---

### 6️⃣ 通知系統
**功能描述**: 事件通知機制

**需求**:
- [ ] 系統通知（知識審核、測試情境審核完成）
- [ ] Email 通知
- [ ] Webhook 通知（給業者系統）
- [ ] 站內通知（前端顯示）

**資料表**:
```sql
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    type VARCHAR(50),
    title VARCHAR(200),
    message TEXT,
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    ...
);
```

**API 端點**:
- `GET /api/v1/notifications` - 取得通知列表
- `POST /api/v1/notifications/{id}/read` - 標記已讀

**預計時程**: 1-2 週

---

## 🟢 低優先級功能（未來規劃）

### 7️⃣ 多語言支援
**功能描述**: 支援多國語言（英文、日文等）

**需求**:
- [ ] 知識庫多語言版本
- [ ] 前端 i18n（Vue I18n）
- [ ] LLM 多語言回答
- [ ] 語言自動偵測

**預計時程**: 3-4 週

---

### 8️⃣ 進階回測功能
**功能描述**: 更強大的回測能力

**需求**:
- [ ] A/B Testing 框架
- [ ] 模型版本比較
- [ ] 回測報告視覺化（前端）
- [ ] 自動化回測排程
- [ ] 回測結果歷史記錄查詢

**預計時程**: 2-3 週

---

### 9️⃣ 知識版本控制
**功能描述**: 類似 Git 的知識版本管理

**需求**:
- [ ] 知識歷史版本記錄
- [ ] 版本比較（Diff）
- [ ] 版本回滾
- [ ] 知識變更審核流程

**預計時程**: 2-3 週

---

## 🐛 已知需要完善的功能

### 🔧 當前系統中的 TODO

1. **認證系統整合** (`knowledge_import.py:656, 659`)
   ```python
   # TODO: 從認證取得真實使用者 ID
   user_id="admin"  # 目前寫死為 "admin"
   ```

2. **拼音去重檢測優化** (`unclear_question_manager.py`)
   - 向量轉換問題需修復（PostgreSQL vector 類型轉換）
   - 拼音檢測實際未正常運作（只有 5/6 測試通過）

3. **Phase 2 架構準備** (`chat.py:434`)
   ```python
   # Phase 2 將支援 customer_service 模式（需要租客辨識 + 外部 API）
   ```

---

## 📅 建議開發順序

### 短期（1-2 個月）
1. **Phase 2.1 基礎** - 租客識別 + API 框架（5 週）
2. **認證系統** - 用戶登入/權限管理（3 週）

### 中期（3-4 個月）
3. **Phase 2.2 完整** - 客服助理整合（2 週）
4. **分析報表** - Dashboard 視覺化（2 週）
5. **通知系統** - 事件通知（1 週）

### 長期（6 個月+）
6. **多語言支援** - i18n 整合（4 週）
7. **進階回測** - A/B Testing（3 週）
8. **知識版本控制** - Git-like 系統（3 週）

---

## 💡 功能完善建議

### 1. 修復拼音去重檢測
- 修復 PostgreSQL vector 類型轉換問題
- 改進拼音相似度算法
- 增加測試覆蓋率

### 2. 增強錯誤處理
- API 超時處理（外部 API）
- LLM 錯誤回退機制
- 資料庫連接池管理

### 3. 性能優化
- 向量搜尋索引優化（IVFFlat → HNSW）
- API 呼叫快取策略
- 並行處理（租客識別 + API 呼叫）

### 4. 測試完善
- E2E 測試（Playwright）
- API 整合測試
- 壓力測試

---

## 📊 功能完成度統計

| 模組 | 完成度 | 備註 |
|------|--------|------|
| Phase 1 核心功能 | 100% | ✅ 完成 |
| Phase 2 B2B 功能 | 0% | ⏳ 規劃中 |
| 分析報表 | 0% | 未規劃 |
| 認證系統 | 0% | 未規劃 |
| 通知系統 | 0% | 未規劃 |
| 多語言支援 | 0% | 未規劃 |
| 進階回測 | 30% | 基礎完成 |
| 知識版本控制 | 0% | 未規劃 |

**整體完成度**: Phase 1 完成（約佔整體系統 40-50%）

---

**生成時間**: 2025-10-13
**系統版本**: Phase 1 Complete
**下一里程碑**: Phase 2 - B2B 功能（租客識別 + 外部 API）
