# 系統架構文件

## 📋 目錄

- [概述](#概述)
- [系統架構圖](#系統架構圖)
- [技術棧](#技術棧)
- [核心服務](#核心服務)
- [資料庫設計](#資料庫設計)
- [API 架構](#api-架構)
- [部署架構](#部署架構)
- [安全性設計](#安全性設計)
- [擴展性設計](#擴展性設計)

---

## 概述

### 系統定位

**AI Chatbot for Rental Management** 是一個專為包租代管業者設計的 **SaaS 多租戶 AI 客服平台**。

### 核心特點

- **🏪 SaaS 多租戶架構**：支援多個業者，資料完全隔離
- **🤖 RAG 智能問答**：結合知識庫檢索與 LLM 優化
- **🎨 LLM 參數注入**：智能調整業者差異化參數
- **🔐 三層知識範圍**：global < vendor < customized
- **📡 外部 API 整合**（Phase 2）：整合業者既有系統

### 業務模型

```
平台提供商（您）
    ↓ 提供 SaaS 服務
包租代管業者 A、B、C...（互為競爭對手）
    ↓ 服務終端使用者
租客（B2C）/ 業者客服（B2B）
```

---

## 系統架構圖

### 高階架構

```
┌─────────────────────────────────────────────────────────────────┐
│                          使用者層                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  租客 App    │  │  業者客服    │  │  管理後台    │          │
│  │  (LINE/Web)  │  │  介面        │  │  (Admin)     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                          API 閘道層                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Nginx (Reverse Proxy)                                 │    │
│  │  - 路由轉發                                             │    │
│  │  - 負載平衡                                             │    │
│  │  - SSL/TLS 終止                                        │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                          應用服務層                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │  RAG Orchestrator │          │  Knowledge Admin │            │
│  │  (FastAPI)        │          │  (Vue.js 3)      │            │
│  │  Port: 8100       │          │  Port: 8087(dev) │            │
│  ├──────────────────┤          │  Port: 8081(prod)│            │
│  │                  │                                           │
│  │  核心服務:       │                                           │
│  │  ✓ 意圖分類      │                                           │
│  │  ✓ RAG 檢索      │                                           │
│  │  ✓ LLM 優化      │                                           │
│  │  ✓ 參數注入      │                                           │
│  │  ✓ Chat API      │                                           │
│  │                  │                                           │
│  │  Phase 2:        │                                           │
│  │  ⏳ 租客識別     │                                           │
│  │  ⏳ 外部 API     │                                           │
│  │                  │                                           │
│  └──────────────────┘                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                          資料層                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  PostgreSQL 15 + pgvector                              │    │
│  │  Database: aichatbot_admin                             │    │
│  │  Port: 5432                                            │    │
│  ├────────────────────────────────────────────────────────┤    │
│  │  資料表:                                                │    │
│  │  ✓ knowledge_base (知識庫 + 向量)                       │    │
│  │  ✓ intents (意圖)                                      │    │
│  │  ✓ vendors (業者)                                      │    │
│  │  ✓ vendor_configs (業者配置)                           │    │
│  │                                                        │    │
│  │  Phase 2:                                              │    │
│  │  ⏳ tenants (租客)                                     │    │
│  │  ⏳ vendor_apis (外部 API)                             │    │
│  │  ⏳ vendor_api_logs (API 日誌)                         │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                          外部服務層                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │  OpenAI API      │          │  業者外部系統    │            │
│  │  (GPT-4o-mini)   │          │  (Phase 2)       │            │
│  │                  │          │  - ERP           │            │
│  │  功能:           │          │  - CRM           │            │
│  │  ✓ 意圖分類      │          │  - 物業管理系統  │            │
│  │  ✓ 向量嵌入      │          └──────────────────┘            │
│  │  ✓ LLM 優化      │                                           │
│  │  ✓ 參數注入      │                                           │
│  └──────────────────┘                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 技術棧

### 後端

| 技術 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.11+ | 主要開發語言 |
| **FastAPI** | 0.100+ | Web 框架 |
| **SQLAlchemy** | 2.0+ | ORM |
| **Pydantic** | 2.0+ | 資料驗證 |
| **OpenAI SDK** | 1.0+ | LLM 整合 |
| **pgvector** | 0.2+ | 向量搜尋 |
| **asyncpg** | 0.28+ | 異步 PostgreSQL 驅動 |

### 前端

| 技術 | 版本 | 用途 |
|------|------|------|
| **Vue.js** | 3.3+ | 前端框架 |
| **Vue Router** | 4.0+ | 路由管理 |
| **Axios** | 1.0+ | HTTP 客戶端 |
| **Vite** | 4.0+ | 建置工具 |

### 資料庫

| 技術 | 版本 | 用途 |
|------|------|------|
| **PostgreSQL** | 15+ | 關聯式資料庫 |
| **pgvector** | 0.5+ | 向量搜尋擴展 |

### 基礎設施

| 技術 | 版本 | 用途 |
|------|------|------|
| **Docker** | 24.0+ | 容器化 |
| **Docker Compose** | 2.20+ | 容器編排 |
| **Nginx** | 1.24+ | 反向代理 |

---

## 核心服務

### 1. RAG Orchestrator（核心引擎）

**位置：** `rag-orchestrator/`

**職責：**
- 意圖分類與路由
- RAG 知識檢索
- LLM 答案優化
- 業者參數管理
- Chat API 提供

**技術架構：**

```
rag-orchestrator/
├── main.py                          # FastAPI 應用入口
├── routers/
│   ├── chat.py                      # Chat API 路由
│   ├── vendors.py                   # 業者管理 API
│   ├── knowledge.py                 # 知識庫 API
│   └── intents.py                   # 意圖管理 API
├── services/
│   ├── intent_classifier.py         # 意圖分類服務
│   ├── rag_service.py               # RAG 檢索服務
│   ├── llm_answer_optimizer.py      # LLM 優化服務 ⭐
│   ├── vendor_parameter_resolver.py # 業者參數解析
│   ├── vendor_knowledge_retriever.py# 業者知識檢索
│   ├── tenant_identifier.py         # [Phase 2] 租客識別
│   ├── external_api_client.py       # [Phase 2] 外部 API
│   └── customer_service_assistant.py# [Phase 2] 客服助理
├── models/
│   └── database.py                  # SQLAlchemy 模型
└── utils/
    ├── vector_utils.py              # 向量處理工具
    └── cache.py                     # 快取管理
```

**核心流程：**

```python
# Chat API 處理流程
async def process_chat_message(message, vendor_id):
    # 1. 意圖分類
    intent = await intent_classifier.classify(message)

    # 2. RAG 檢索
    search_results = await rag_service.search(
        query=message,
        intent_id=intent.id,
        vendor_id=vendor_id
    )

    # 3. 獲取業者參數
    vendor_params = await parameter_resolver.get_vendor_parameters(vendor_id)
    vendor_name = await get_vendor_name(vendor_id)

    # 4. LLM 優化 + 參數注入
    result = await llm_optimizer.optimize_answer(
        question=message,
        search_results=search_results,
        confidence_level=intent.confidence_level,
        intent_info=intent,
        vendor_params=vendor_params,  # ⭐ 參數注入
        vendor_name=vendor_name
    )

    return result
```

---

### 2. Knowledge Admin（管理後台）

**位置：** `knowledge-admin/frontend/`

**職責：**
- 業者管理（CRUD）
- 業者配置管理
- 知識庫管理
- 意圖管理
- Chat 測試介面

**頁面架構：**

```
frontend/src/
├── views/
│   ├── KnowledgeView.vue            # 知識庫管理
│   ├── IntentsView.vue              # 意圖管理
│   ├── VendorManagementView.vue     # 業者管理 ⭐
│   ├── VendorConfigView.vue         # 業者配置 ⭐
│   ├── ChatTestView.vue             # Chat 測試 ⭐
│   ├── TenantManagementView.vue     # [Phase 2] 租客管理
│   ├── APIConfigView.vue            # [Phase 2] API 配置
│   └── CustomerServiceView.vue      # [Phase 2] 客服助理
├── components/
│   └── [各頁面的元件]
└── router/
    └── index.js                      # Vue Router 配置
```

---

## 資料庫設計

### ER 圖（Entity Relationship Diagram）

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   vendors   │────1:N──│ vendor_configs   │         │ knowledge_base  │
│             │         │                  │         │                 │
│ - id        │         │ - id             │         │ - id            │
│ - code      │         │ - vendor_id (FK) │         │ - question      │
│ - name      │         │ - category       │         │ - answer        │
│ - is_active │         │ - param_key      │         │ - vendor_id (FK)│
└─────────────┘         │ - param_value    │         │ - intent_id (FK)│
      │                 │ - data_type      │         │ - scope         │
      │                 └──────────────────┘         │ - priority      │
      │                                              │ - embedding     │
      │                                              └─────────────────┘
      │                                                      │
      │                 ┌──────────────────┐                │
      └────────1:N──────│    intents       │────────N:1─────┘
                        │                  │
                        │ - id             │
                        │ - name           │
                        │ - intent_type    │
                        │ - keywords       │
                        └──────────────────┘

Phase 2 新增表格:

┌─────────────┐         ┌──────────────────┐
│  tenants    │         │  vendor_apis     │
│             │         │                  │
│ - id        │         │ - id             │
│ - vendor_id │◄────1:N─│ - vendor_id (FK) │
│ - name      │         │ - api_name       │
│ - phone     │         │ - base_url       │
│ - room_no   │         │ - auth_type      │
└─────────────┘         └──────────────────┘
                                │
                                │1:N
                                ↓
                        ┌──────────────────────┐
                        │ vendor_api_endpoints │
                        │                      │
                        │ - id                 │
                        │ - api_id (FK)        │
                        │ - endpoint_name      │
                        │ - http_method        │
                        │ - path               │
                        └──────────────────────┘
```

### 核心資料表

#### Phase 1（已實作）

| 表名 | 說明 | 主要欄位 |
|------|------|---------|
| `knowledge_base` | 知識庫 | question, answer, embedding, vendor_id, scope |
| `intents` | 意圖 | name, intent_type, keywords, example_questions |
| `vendors` | 業者 | code, name, subscription_plan, is_active |
| `vendor_configs` | 業者配置 | vendor_id, category, param_key, param_value |

#### Phase 2（待實作）

| 表名 | 說明 | 主要欄位 |
|------|------|---------|
| `tenants` | 租客 | vendor_id, name, phone, room_number, contract_code |
| `vendor_apis` | API 配置 | vendor_id, api_name, base_url, auth_type |
| `vendor_api_endpoints` | API 端點 | api_id, endpoint_name, http_method, path |
| `vendor_api_logs` | API 日誌 | vendor_id, endpoint_id, request, response, status |

### 索引策略

```sql
-- 向量搜尋索引
CREATE INDEX idx_knowledge_embedding ON knowledge_base
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 業者隔離索引
CREATE INDEX idx_knowledge_vendor ON knowledge_base(vendor_id);
CREATE INDEX idx_configs_vendor ON vendor_configs(vendor_id);

-- 意圖查詢索引
CREATE INDEX idx_knowledge_intent ON knowledge_base(intent_id);

-- 複合索引（業者 + 意圖）
CREATE INDEX idx_knowledge_vendor_intent ON knowledge_base(vendor_id, intent_id);
```

---

## API 架構

### RESTful API 設計原則

1. **資源導向**：使用名詞而非動詞
2. **HTTP 方法**：GET（查詢）、POST（建立）、PUT（更新）、DELETE（刪除）
3. **版本控制**：`/api/v1/`, `/chat/v1/`
4. **回應格式**：統一 JSON 格式
5. **錯誤處理**：標準 HTTP 狀態碼 + 詳細錯誤訊息

### API 分層

```
┌─────────────────────────────────────────────────┐
│  Public API (面向終端使用者)                     │
├─────────────────────────────────────────────────┤
│  POST /chat/v1/message                          │
│  - B2C 聊天（租客）                              │
│  - vendor_id 識別業者                            │
│  - 返回客製化答案                                │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  Internal API (面向業者客服) [Phase 2]          │
├─────────────────────────────────────────────────┤
│  POST /chat/v2/customer-service                 │
│  - B2B 聊天（客服）                              │
│  - 支援租客識別 + 外部 API 整合                  │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  Management API (面向管理後台)                   │
├─────────────────────────────────────────────────┤
│  /api/v1/vendors/*        - 業者管理             │
│  /api/v1/knowledge/*      - 知識庫管理           │
│  /api/v1/intents/*        - 意圖管理             │
│  /api/v1/tenants/*        - [Phase 2] 租客管理   │
│  /api/v1/apis/*           - [Phase 2] API 配置   │
└─────────────────────────────────────────────────┘
```

### API 安全性

| 機制 | 實作方式 | 狀態 |
|------|---------|------|
| **HTTPS** | Nginx SSL/TLS 終止 | ✅ 生產環境 |
| **API Key** | Header: `X-API-Key` | ⏳ 待實作 |
| **Rate Limiting** | 基於 IP 或 API Key | ⏳ 待實作 |
| **CORS** | FastAPI CORS Middleware | ✅ 已實作 |
| **Input Validation** | Pydantic Models | ✅ 已實作 |

---

## 部署架構

### Docker Compose 架構

```yaml
version: '3.8'

services:
  # 反向代理
  nginx:
    image: nginx:1.24-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - rag-orchestrator
      - knowledge-admin

  # 核心後端服務
  rag-orchestrator:
    build: ./rag-orchestrator
    ports:
      - "8100:8100"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/aichatbot_admin
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - postgres

  # 管理後台前端
  knowledge-admin:
    build: ./knowledge-admin/frontend
    ports:
      - "8200:80"

  # PostgreSQL 資料庫
  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=aichatbot
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=aichatbot_admin
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init:/docker-entrypoint-initdb.d

volumes:
  postgres_data:
```

### 環境變數管理

```bash
# .env 檔案
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://aichatbot:password@localhost:5432/aichatbot_admin
ENVIRONMENT=development  # development, staging, production
LOG_LEVEL=INFO
```

---

## 安全性設計

### 資料安全

| 項目 | 實作方式 |
|------|---------|
| **業者資料隔離** | 所有查詢必須包含 `vendor_id` WHERE 條件 |
| **敏感資料加密** | API 憑證、租客身份證字號加密儲存 |
| **資料庫加密** | PostgreSQL SSL 連線 |
| **日誌脫敏** | 敏感資訊（電話、身份證）打碼記錄 |

### 應用安全

| 項目 | 實作方式 |
|------|---------|
| **SQL 注入防護** | SQLAlchemy ORM，參數化查詢 |
| **XSS 防護** | Vue.js 自動轉義，Content Security Policy |
| **CSRF 防護** | Token 驗證（API 為 stateless，暫不需要） |
| **輸入驗證** | Pydantic 強制驗證所有輸入 |

### 存取控制（Phase 2）

```
┌─────────────────────────────────────────┐
│  角色權限設計（待實作）                  │
├─────────────────────────────────────────┤
│  - Platform Admin: 全平台管理            │
│  - Vendor Admin: 業者管理                │
│  - CS Staff: 客服查詢                    │
│  - Tenant: 租客查詢（B2C）               │
└─────────────────────────────────────────┘
```

---

## 擴展性設計

### 水平擴展

```
                    Load Balancer
                         ↓
        ┌────────────────┼────────────────┐
        ↓                ↓                ↓
  Orchestrator #1  Orchestrator #2  Orchestrator #3
        ↓                ↓                ↓
        └────────────────┼────────────────┘
                         ↓
                  PostgreSQL
                  (Read Replicas)
```

**支援方式：**
- RAG Orchestrator 為無狀態服務，可水平擴展
- PostgreSQL 讀寫分離（主從複製）
- Redis 快取層（待實作）

### 效能優化

| 優化項目 | 實作方式 | 狀態 |
|---------|---------|------|
| **參數快取** | 記憶體快取業者參數 | ✅ 已實作 |
| **向量索引** | IVFFlat 索引加速搜尋 | ✅ 已實作 |
| **連線池** | SQLAlchemy 連線池 | ✅ 已實作 |
| **非同步處理** | FastAPI async/await | ✅ 已實作 |
| **Redis 快取** | 快取 LLM 回應 | ⏳ 待實作 |
| **CDN** | 靜態資源加速 | ⏳ 待實作 |

### 監控與日誌

```
┌─────────────────────────────────────────┐
│  監控系統（待實作）                      │
├─────────────────────────────────────────┤
│  - Prometheus: 指標收集                  │
│  - Grafana: 儀表板                       │
│  - ELK Stack: 日誌聚合                   │
│  - Sentry: 錯誤追蹤                      │
└─────────────────────────────────────────┘
```

---

## 資料流圖

### B2C 聊天流程（Phase 1）

```
租客輸入問題
    ↓
[POST /chat/v1/message]
    vendor_id: 1
    message: "繳費日是幾號？"
    ↓
意圖分類
    ↓ intent_id: 5 (帳務查詢)
RAG 向量搜尋
    ↓ 知識庫 (scope: global)
    "您的租金繳費日為每月 5 號..."
    ↓
獲取業者參數
    ↓ vendor_configs
    payment_day: 1
    late_fee: 200
    ↓
LLM 智能參數注入
    ↓ GPT-4o-mini 分析與調整
    "5 號" → "1 號"
    "300 元" → "200 元"
    ↓
返回客製化答案
    ↓
"您的租金繳費日為每月 1 號..."
```

### B2B 客服流程（Phase 2）

```
客服輸入問題
    ↓
[POST /chat/v2/customer-service]
    vendor_id: 1
    message: "林小姐這個月繳費了嗎？"
    ↓
意圖分類
    ↓ intent_type: data_query
租客識別
    ↓ LLM 提取 → 資料庫比對
    tenant_id: 12345 (林小姐, A-2024-001)
    ↓
呼叫外部 API
    ↓ GET /api/payments?tenant_id=12345
    {
      "paid_date": "2024-10-03",
      "amount": 15000
    }
    ↓
格式化回應
    ↓
"林小姐（A-2024-001）已於 10 月 3 日繳清..."
```

---

## 文件版本

- **版本：** 2.0
- **建立日期：** 2025-10-09
- **最後更新：** 2025-10-10
- **作者：** Claude Code
- **適用系統版本：** Phase 1 完成 + Phase 2 規劃
- **變更紀錄：**
  - v2.0 (2025-10-10): 更新為 Phase 1 多業者架構 + LLM 智能參數注入
  - v1.0 (2025-10-09): 初始版本
