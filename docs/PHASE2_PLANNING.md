# Phase 2: B2B 完整功能規劃文件

## 📋 目錄

- [概述](#概述)
- [目標與範圍](#目標與範圍)
- [功能需求](#功能需求)
- [技術架構](#技術架構)
- [資料庫設計](#資料庫設計)
- [後端服務](#後端服務)
- [API 設計](#api-設計)
- [前端頁面](#前端頁面)
- [實作計劃](#實作計劃)
- [風險與挑戰](#風險與挑戰)

---

## 概述

### 當前狀態（Phase 1）

✅ **已完成：**
- B2C 聊天路徑：租客 → 業者
- 多業者 SaaS 架構
- LLM 智能參數注入系統
- 業者管理與配置
- 知識庫管理（三層範圍）
- 意圖分類系統

### Phase 2 目標

🎯 **新增功能：**
- **B2B 聊天路徑**：業者客服 → 平台系統 → 外部 API
- **租客身份識別**：從自然語言對話中提取租客資訊
- **外部 API 整合**：呼叫業者既有系統（ERP/CRM）
- **客服助理增強**：整合知識查詢 + 資料查詢 + 操作執行

---

## 目標與範圍

### 業務價值

Phase 2 將實現完整的 B2B 功能，讓**業者客服人員**能夠：

1. **提高效率**：透過 AI 助理快速查詢租客資料和知識
2. **減少錯誤**：自動化操作執行，避免人工輸入錯誤
3. **統一介面**：整合多個外部系統，單一入口存取
4. **智能輔助**：AI 自動識別租客身份，無需手動輸入

### 使用場景

#### 場景 1：客服查詢租客繳費記錄

```
客服：林小姐這個月繳費了嗎？
AI：正在為您查詢林小姐的繳費記錄...
    [識別租客：林小姐 → tenant_id: 12345]
    [呼叫外部 API: GET /api/payments?tenant_id=12345&month=10]

AI：林小姐（租約編號：A-2024-001）已於 10 月 3 日繳清本月租金 15,000 元。
    繳費方式：信用卡自動扣款
    下期繳費日：11 月 1 日
```

#### 場景 2：客服協助租客報修

```
客服：幫我登記 302 房的報修，冷氣不冷
AI：正在為您登記報修...
    [識別房號：302 → tenant_id: 67890]
    [呼叫外部 API: POST /api/maintenance]
    [傳送參數：tenant_id=67890, issue="冷氣不冷", category="電器維修"]

AI：已成功登記報修！
    工單編號：MR-2024-10-0123
    房號：302（租客：王先生）
    問題：冷氣不冷
    預計處理時間：24 小時內
    維修人員會於今日下午 2-5 點聯絡租客。
```

#### 場景 3：混合查詢（知識 + 資料）

```
客服：提前解約要怎麼辦理？順便查一下 A-2024-001 的租約還剩多久？
AI：關於提前解約流程：
    [知識庫查詢]
    1. 需於 30 天前提出書面申請
    2. 可能需支付違約金（詳見合約）
    3. 需繳清所有費用並完成房屋檢查

    關於林小姐（A-2024-001）的租約資訊：
    [外部 API 查詢]
    - 租約起始日：2024-01-01
    - 租約到期日：2024-12-31
    - 剩餘天數：82 天
    - 提前解約違約金：約 10,000 元（1 個月租金）
```

---

## 功能需求

### 1. 租客身份識別（Tenant Identification）

#### 需求描述

從客服人員的自然語言輸入中，自動識別租客身份。

#### 識別方式

| 識別方式 | 範例 | 說明 |
|---------|------|------|
| 姓名 | "林小姐"、"王先生" | 常見但可能重複 |
| 租約編號 | "A-2024-001" | 唯一識別碼 |
| 房號 | "302 房"、"3F-A" | 需處理多種格式 |
| 電話 | "0912-345-678" | 高準確度 |
| 身份證字號 | "A123456789" | 最準確（敏感資訊） |
| 模糊描述 | "上次打來的那個租客" | 需要上下文記憶 |

#### 技術實作

1. **LLM 提取資訊**：使用 GPT 從對話中提取關鍵資訊
2. **模糊比對**：支援拼音、簡稱、別名
3. **多候選處理**：如有多個符合，要求客服確認
4. **上下文記憶**：對話中記住已識別的租客

#### 資料表需求

```sql
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER REFERENCES vendors(id) NOT NULL,
    tenant_code VARCHAR(50) UNIQUE,           -- 租約編號（如 A-2024-001）
    name VARCHAR(100) NOT NULL,               -- 姓名
    phone VARCHAR(20),                        -- 電話
    id_number VARCHAR(20),                    -- 身份證字號（加密）
    room_number VARCHAR(50),                  -- 房號
    email VARCHAR(100),
    contract_start_date DATE,                 -- 租約起始日
    contract_end_date DATE,                   -- 租約結束日
    status VARCHAR(20) DEFAULT 'active',      -- active, expired, terminated
    external_id VARCHAR(100),                 -- 外部系統 ID
    aliases JSONB DEFAULT '[]',               -- 別名、暱稱
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(vendor_id, tenant_code)
);

CREATE INDEX idx_tenants_vendor_id ON tenants(vendor_id);
CREATE INDEX idx_tenants_name ON tenants(name);
CREATE INDEX idx_tenants_phone ON tenants(phone);
CREATE INDEX idx_tenants_room_number ON tenants(room_number);
```

---

### 2. 外部 API 整合框架（External API Integration）

#### 需求描述

讓業者能夠配置自己的既有系統（ERP、CRM、物業管理系統）API，AI 客服可以呼叫這些 API 查詢資料或執行操作。

#### 功能特點

- **彈性配置**：支援不同業者的不同 API 系統
- **安全認證**：支援多種認證方式（API Key、OAuth、Basic Auth）
- **參數對應**：將 AI 提取的資訊對應到 API 參數
- **錯誤處理**：API 失敗時的備用方案
- **日誌記錄**：完整記錄 API 呼叫歷史

#### 資料表需求

```sql
-- API 配置表
CREATE TABLE vendor_apis (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER REFERENCES vendors(id) NOT NULL,
    api_name VARCHAR(100) NOT NULL,           -- API 名稱（如 "繳費查詢 API"）
    base_url VARCHAR(500) NOT NULL,           -- API 基礎 URL
    auth_type VARCHAR(50) DEFAULT 'none',     -- none, api_key, oauth, basic
    auth_config JSONB DEFAULT '{}',           -- 認證配置（加密）
    timeout_ms INTEGER DEFAULT 10000,         -- 超時時間
    retry_count INTEGER DEFAULT 3,            -- 重試次數
    is_active BOOLEAN DEFAULT true,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(vendor_id, api_name)
);

-- API 端點表
CREATE TABLE vendor_api_endpoints (
    id SERIAL PRIMARY KEY,
    api_id INTEGER REFERENCES vendor_apis(id) ON DELETE CASCADE,
    endpoint_name VARCHAR(100) NOT NULL,      -- 端點名稱（如 "查詢繳費記錄"）
    intent_id INTEGER REFERENCES intents(id), -- 對應的意圖（可選）
    http_method VARCHAR(10) NOT NULL,         -- GET, POST, PUT, DELETE
    path VARCHAR(500) NOT NULL,               -- API 路徑（如 /api/payments）
    param_mapping JSONB DEFAULT '{}',         -- 參數對應規則
    response_mapping JSONB DEFAULT '{}',      -- 回應欄位對應
    is_active BOOLEAN DEFAULT true,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(api_id, endpoint_name)
);

-- API 呼叫日誌表
CREATE TABLE vendor_api_logs (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER REFERENCES vendors(id),
    endpoint_id INTEGER REFERENCES vendor_api_endpoints(id),
    conversation_id VARCHAR(100),             -- 對話 ID
    request_params JSONB,                     -- 請求參數
    response_data JSONB,                      -- 回應資料
    status_code INTEGER,                      -- HTTP 狀態碼
    response_time_ms INTEGER,                 -- 回應時間
    error_message TEXT,                       -- 錯誤訊息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_api_logs_vendor_id ON vendor_api_logs(vendor_id);
CREATE INDEX idx_api_logs_created_at ON vendor_api_logs(created_at);
```

---

### 3. 意圖擴展（Intent Enhancement）

#### 新增意圖類型

Phase 1 主要處理 `knowledge` 意圖，Phase 2 需擴展：

| 意圖類型 | 說明 | 範例 |
|---------|------|------|
| `knowledge` | 知識查詢 | "提前解約怎麼辦理？" |
| `data_query` | 資料查詢（需呼叫 API） | "林小姐繳費了嗎？" |
| `action` | 操作執行（需呼叫 API） | "幫我登記報修" |
| `mixed` | 混合查詢 | "解約流程是什麼？順便查一下 A-2024-001 的租約" |

#### 資料表擴展

```sql
ALTER TABLE intents
    ADD COLUMN requires_api BOOLEAN DEFAULT false,   -- 是否需要呼叫 API
    ADD COLUMN api_endpoint_id INTEGER REFERENCES vendor_api_endpoints(id),
    ADD COLUMN requires_tenant_id BOOLEAN DEFAULT false;  -- 是否需要租客識別
```

---

## 技術架構

### 系統流程圖

```
客服輸入問題
    ↓
意圖分類（IntentClassifier）
    ↓
[判斷意圖類型]
    ↓
    ├─ knowledge → RAG 檢索 → LLM 優化 → 返回答案
    ↓
    ├─ data_query → 租客識別 → 呼叫外部 API → 格式化結果 → 返回答案
    ↓
    ├─ action → 租客識別 → 呼叫外部 API → 確認執行結果 → 返回答案
    ↓
    └─ mixed → [並行處理知識查詢 + 資料查詢] → 整合結果 → 返回答案
```

### 服務架構

```
rag-orchestrator/services/
├── llm_answer_optimizer.py          [Phase 1] LLM 答案優化
├── vendor_parameter_resolver.py     [Phase 1] 業者參數處理
├── vendor_knowledge_retriever.py    [Phase 1] 知識檢索
├── tenant_identifier.py             [Phase 2] 租客身份識別 🆕
├── external_api_client.py           [Phase 2] 外部 API 客戶端 🆕
└── customer_service_assistant.py    [Phase 2] 客服助理整合服務 🆕
```

---

## 後端服務

### 1. TenantIdentifier（租客識別服務）

**位置：** `rag-orchestrator/services/tenant_identifier.py`

**功能：**
- 從自然語言提取租客識別資訊
- 支援多種識別方式（姓名、房號、電話、租約編號）
- 模糊比對與多候選處理
- 對話上下文記憶

**核心方法：**

```python
class TenantIdentifier:
    def identify_tenant(
        self,
        message: str,
        vendor_id: int,
        conversation_context: Dict = None
    ) -> Dict:
        """
        識別租客身份

        Returns:
            {
                "tenant_id": 12345,
                "tenant_code": "A-2024-001",
                "name": "林小姐",
                "confidence": 0.95,
                "identification_method": "tenant_code",
                "candidates": []  # 如有多個候選
            }
        """

    def extract_tenant_info(self, message: str) -> Dict:
        """使用 LLM 從訊息中提取租客資訊"""

    def fuzzy_match_tenant(self, info: Dict, vendor_id: int) -> List[Dict]:
        """模糊比對租客資料"""
```

---

### 2. ExternalAPIClient（外部 API 客戶端）

**位置：** `rag-orchestrator/services/external_api_client.py`

**功能：**
- 呼叫業者配置的外部 API
- 處理不同的認證方式
- 參數對應與回應格式化
- 錯誤處理與重試機制
- 日誌記錄

**核心方法：**

```python
class ExternalAPIClient:
    def call_api(
        self,
        vendor_id: int,
        endpoint_name: str,
        params: Dict,
        context: Dict = None
    ) -> Dict:
        """
        呼叫外部 API

        Returns:
            {
                "success": true,
                "data": {...},
                "response_time_ms": 234,
                "formatted_answer": "林小姐已於 10 月 3 日繳清..."
            }
        """

    def _authenticate(self, api_config: Dict) -> Dict:
        """處理 API 認證"""

    def _map_parameters(self, params: Dict, mapping: Dict) -> Dict:
        """參數對應"""

    def _format_response(self, response: Dict, mapping: Dict) -> str:
        """格式化回應為自然語言"""
```

---

### 3. CustomerServiceAssistant（客服助理整合服務）

**位置：** `rag-orchestrator/services/customer_service_assistant.py`

**功能：**
- 整合所有服務（意圖分類、知識檢索、租客識別、API 呼叫）
- 處理混合查詢（知識 + 資料）
- 對話上下文管理
- 統一回應格式

**核心方法：**

```python
class CustomerServiceAssistant:
    def process_message(
        self,
        message: str,
        vendor_id: int,
        user_id: str,
        conversation_id: str = None
    ) -> Dict:
        """
        處理客服訊息（完整流程）

        Returns:
            {
                "answer": "完整的回答內容",
                "intent_type": "data_query",
                "tenant_identified": true,
                "tenant_info": {...},
                "api_called": true,
                "api_response": {...},
                "knowledge_used": [...],
                "confidence": 0.92
            }
        """
```

---

## API 設計

### 1. B2B Chat API

#### `POST /chat/v2/customer-service`

客服專用聊天端點

**請求：**

```json
{
  "message": "林小姐這個月繳費了嗎？",
  "vendor_id": 1,
  "user_id": "cs_staff_001",
  "conversation_id": "conv_20241010_001",
  "context": {
    "previous_tenant_id": 12345  // 可選，上下文中的租客 ID
  }
}
```

**回應：**

```json
{
  "answer": "林小姐（租約編號：A-2024-001）已於 10 月 3 日繳清本月租金 15,000 元。繳費方式：信用卡自動扣款。下期繳費日：11 月 1 日。",
  "intent_type": "data_query",
  "intent_name": "繳費查詢",
  "confidence": 0.95,

  "tenant_identified": true,
  "tenant_info": {
    "tenant_id": 12345,
    "tenant_code": "A-2024-001",
    "name": "林小姐",
    "room_number": "302"
  },

  "api_called": true,
  "api_endpoint": "查詢繳費記錄",
  "api_response": {
    "payment_date": "2024-10-03",
    "amount": 15000,
    "method": "信用卡自動扣款",
    "next_due_date": "2024-11-01"
  },

  "processing_details": {
    "tenant_identification_time_ms": 156,
    "api_call_time_ms": 234,
    "total_time_ms": 567
  },

  "conversation_id": "conv_20241010_001",
  "timestamp": "2024-10-10T14:30:00Z"
}
```

---

### 2. Tenant Management API

#### `GET /api/v1/vendors/{vendor_id}/tenants`

獲取租客列表

**查詢參數：**
- `status`: 租約狀態（active, expired, terminated）
- `search`: 搜尋關鍵字（姓名、房號、租約編號）
- `page`, `limit`: 分頁

#### `POST /api/v1/vendors/{vendor_id}/tenants`

建立租客資料

#### `PUT /api/v1/tenants/{tenant_id}`

更新租客資料

#### `GET /api/v1/tenants/search`

搜尋租客（用於身份識別）

**請求：**

```json
{
  "vendor_id": 1,
  "name": "林小姐",
  "fuzzy": true
}
```

---

### 3. External API Configuration

#### `GET /api/v1/vendors/{vendor_id}/apis`

獲取業者的 API 配置列表

#### `POST /api/v1/vendors/{vendor_id}/apis`

建立 API 配置

**請求範例：**

```json
{
  "api_name": "繳費查詢 API",
  "base_url": "https://erp.vendor-a.com/api",
  "auth_type": "api_key",
  "auth_config": {
    "api_key": "encrypted_key_here",
    "header_name": "X-API-Key"
  },
  "timeout_ms": 5000,
  "description": "查詢租客繳費記錄"
}
```

#### `POST /api/v1/apis/{api_id}/endpoints`

建立 API 端點配置

**請求範例：**

```json
{
  "endpoint_name": "查詢繳費記錄",
  "intent_id": 5,
  "http_method": "GET",
  "path": "/api/payments",
  "param_mapping": {
    "tenant_id": "tenant_code",
    "month": "payment_month"
  },
  "response_mapping": {
    "payment_date": "data.paymentDate",
    "amount": "data.amount",
    "method": "data.paymentMethod"
  }
}
```

#### `GET /api/v1/vendors/{vendor_id}/api-logs`

查詢 API 呼叫日誌

---

## 前端頁面

### 1. 客服助理頁面（新增）

**路由：** `/customer-service`

**功能：**
- 客服專用聊天介面
- 租客快速識別輸入
- 對話歷史記錄
- API 呼叫狀態顯示
- 知識來源參考

**介面設計：**

```
┌─────────────────────────────────────────────────────┐
│ 🎧 客服助理                         [業者: 甲山林] │
├─────────────────────────────────────────────────────┤
│ 當前租客: 林小姐 (A-2024-001, 302 房)  [變更租客]   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  👤 客服: 林小姐這個月繳費了嗎？                      │
│                                                     │
│  🤖 AI: 林小姐（租約編號：A-2024-001）已於 10 月     │
│        3 日繳清本月租金 15,000 元。                  │
│        繳費方式：信用卡自動扣款                       │
│        下期繳費日：11 月 1 日                        │
│                                                     │
│        [📊 來源: 繳費查詢 API]  [⏱️ 234ms]          │
│                                                     │
│  👤 客服: 提前解約要怎麼辦？                         │
│                                                     │
│  🤖 AI: 關於提前解約流程：                           │
│        1. 需於 30 天前提出書面申請                   │
│        2. 可能需支付違約金（詳見合約）                 │
│        ...                                         │
│                                                     │
│        [📚 來源: 知識庫]                            │
│                                                     │
├─────────────────────────────────────────────────────┤
│ [輸入訊息...]                              [傳送]   │
└─────────────────────────────────────────────────────┘
```

---

### 2. 租客管理頁面（新增）

**路由：** `/vendors/{vendor_id}/tenants`

**功能：**
- 租客列表（CRUD）
- 搜尋與過濾
- 租約狀態管理
- 匯入/匯出 CSV
- 查看對話歷史

---

### 3. API 配置頁面（新增）

**路由：** `/vendors/{vendor_id}/api-settings`

**功能：**
- API 配置管理
- 端點配置
- 參數對應設定
- 測試 API 連線
- 查看呼叫日誌

---

### 4. API 日誌頁面（新增）

**路由：** `/vendors/{vendor_id}/api-logs`

**功能：**
- API 呼叫歷史
- 過濾（成功/失敗、端點、時間範圍）
- 查看詳細請求/回應
- 統計圖表（呼叫次數、成功率、平均回應時間）

---

## 實作計劃

### 階段 1：租客識別（預計 2 週）

**Week 1：資料庫與基礎服務**
- [ ] 建立 `tenants` 表
- [ ] 實作 Tenant Management API
- [ ] 建立租客管理前端頁面
- [ ] 匯入測試租客資料

**Week 2：身份識別服務**
- [ ] 實作 `TenantIdentifier` 服務
- [ ] LLM 資訊提取
- [ ] 模糊比對算法
- [ ] 單元測試

---

### 階段 2：外部 API 整合（預計 3 週）

**Week 3：API 配置框架**
- [ ] 建立 `vendor_apis`, `vendor_api_endpoints`, `vendor_api_logs` 表
- [ ] 實作 API Configuration API
- [ ] 建立 API 配置前端頁面

**Week 4：API 客戶端**
- [ ] 實作 `ExternalAPIClient` 服務
- [ ] 支援多種認證方式
- [ ] 參數對應與回應格式化
- [ ] 錯誤處理與重試
- [ ] 日誌記錄

**Week 5：測試與整合**
- [ ] 建立 Mock API 伺服器（測試用）
- [ ] API 連線測試功能
- [ ] 整合測試
- [ ] API 日誌前端頁面

---

### 階段 3：客服助理整合（預計 2 週）

**Week 6：整合服務**
- [ ] 實作 `CustomerServiceAssistant` 服務
- [ ] 擴展意圖分類（data_query, action, mixed）
- [ ] 實作 B2B Chat API (`/chat/v2/customer-service`)
- [ ] 對話上下文管理

**Week 7：客服前端**
- [ ] 建立客服助理頁面
- [ ] 租客識別 UI
- [ ] 對話歷史
- [ ] API 狀態顯示
- [ ] 整合測試

---

### 階段 4：優化與上線（預計 1 週）

**Week 8：**
- [ ] 性能優化（API 呼叫快取、並行處理）
- [ ] 安全審計（API 憑證加密、權限控制）
- [ ] 完整測試（E2E、壓力測試）
- [ ] 文件撰寫
- [ ] 生產環境部署

---

## 風險與挑戰

### 技術挑戰

| 挑戰 | 影響 | 應對方案 |
|------|------|---------|
| **租客識別準確度** | 高 | 1. 多種識別方式互補<br>2. 多候選確認機制<br>3. 人工覆核選項 |
| **外部 API 穩定性** | 高 | 1. 超時與重試機制<br>2. 備用知識庫回答<br>3. 降級策略 |
| **API 參數對應複雜度** | 中 | 1. 可視化配置介面<br>2. 參數對應驗證<br>3. 範例與文件 |
| **LLM 成本** | 中 | 1. 快取常見查詢<br>2. 使用較小模型（gpt-4o-mini）<br>3. 批次處理 |
| **安全性（API 憑證）** | 高 | 1. 憑證加密儲存<br>2. HTTPS 傳輸<br>3. 權限控制 |

### 業務挑戰

| 挑戰 | 影響 | 應對方案 |
|------|------|---------|
| **業者系統差異大** | 高 | 彈性配置框架，支援各種 API 格式 |
| **資料品質不一** | 中 | 資料清洗工具、匯入驗證 |
| **使用者培訓** | 中 | 完整教學文件、影片教學、客服支援 |

---

## 成功指標

### 功能指標

- ✅ 租客識別準確率 > 90%
- ✅ API 呼叫成功率 > 95%
- ✅ 平均回應時間 < 2 秒
- ✅ 支援至少 3 種外部 API 認證方式

### 業務指標

- ✅ 客服查詢效率提升 50%
- ✅ 人工輸入錯誤減少 70%
- ✅ 客服滿意度 > 85%

---

## 附錄

### A. 範例 API 配置

**業者 A - ERP 系統繳費查詢**

```json
{
  "api_name": "ERP 繳費查詢",
  "base_url": "https://erp.vendor-a.com/api/v1",
  "auth_type": "api_key",
  "auth_config": {
    "api_key": "***",
    "header_name": "X-API-Key"
  },
  "endpoints": [
    {
      "endpoint_name": "查詢繳費記錄",
      "http_method": "GET",
      "path": "/payments",
      "param_mapping": {
        "tenant_id": "contract_id",
        "month": "query_month"
      },
      "response_mapping": {
        "payment_date": "data.paidDate",
        "amount": "data.totalAmount",
        "method": "data.paymentType"
      }
    }
  ]
}
```

### B. Mock API 範例

用於測試的 Mock API 回應：

```json
GET /api/payments?contract_id=A-2024-001&query_month=10

Response:
{
  "success": true,
  "data": {
    "contractId": "A-2024-001",
    "tenantName": "林小姐",
    "paidDate": "2024-10-03",
    "totalAmount": 15000,
    "paymentType": "信用卡自動扣款",
    "nextDueDate": "2024-11-01"
  }
}
```

---

## 文件版本

- **版本：** 1.0
- **建立日期：** 2025-10-10
- **作者：** Claude Code
- **狀態：** 規劃中（Planning）
- **預計開始：** TBD
- **預計完成：** TBD（預估 8 週）
