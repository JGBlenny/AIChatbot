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
- **🔄 Reranker 二階段檢索**：Cross-Encoder 重排序，準確率提升 3 倍
- **📋 SOP 流程自動化**：智能 SOP 觸發與執行（manual/immediate/auto）
- **📝 表單管理系統**：動態表單創建、填寫、提交與 API 整合
- **🎨 LLM 參數注入**：智能調整業者差異化參數
- **🔐 三層知識範圍**：global < vendor < customized
- **⚡ Redis 三層緩存**：問題/向量/結果緩存，節省 70-90% API 成本
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
│  │                  │          │                  │            │
│  │  核心服務:       │          │  管理功能:       │            │
│  │  ✓ 意圖分類      │          │  ✓ 知識庫管理    │            │
│  │  ✓ RAG 檢索      │          │  ✓ SOP 管理      │            │
│  │  ✓ Reranker 優化 │          │  ✓ 表單編輯器    │            │
│  │  ✓ LLM 優化      │          │  ✓ 業者管理      │            │
│  │  ✓ 參數注入      │          │  ✓ 審核中心      │            │
│  │  ✓ SOP 協調器    │  🆕      │  ✓ Chat 測試     │            │
│  │  ✓ 表單管理器    │  🆕      └──────────────────┘            │
│  │  ✓ Chat API      │                                           │
│  │  ✓ 流式 API      │                                           │
│  │                  │                                           │
│  │  Phase 2:        │                                           │
│  │  ⏳ 租客識別     │                                           │
│  │  ⏳ 外部 API     │                                           │
│  │                  │                                           │
│  └──────────────────┘                                           │
│           ↓                                                     │
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │  Embedding API   │          │  Knowledge Admin │            │
│  │  (FastAPI)       │  🆕      │  API (FastAPI)   │            │
│  │  Port: 5001      │          │  Port: 8000      │            │
│  │                  │          │                  │            │
│  │  ✓ 向量生成      │          │  ✓ CRUD API      │            │
│  │  ✓ Redis 緩存    │          │  ✓ 測試情境管理  │            │
│  └──────────────────┘          └──────────────────┘            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                          資料與緩存層                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  PostgreSQL 15 + pgvector                              │    │
│  │  Database: aichatbot                                   │    │
│  │  Port: 5432                                            │    │
│  ├────────────────────────────────────────────────────────┤    │
│  │  核心資料表:                                            │    │
│  │  ✓ knowledge_base (知識庫 + 向量)                       │    │
│  │  ✓ intents (意圖)                                      │    │
│  │  ✓ vendors (業者)                                      │    │
│  │  ✓ vendor_configs (業者配置)                           │    │
│  │                                                        │    │
│  │  SOP 系統表: 🆕                                         │    │
│  │  ✓ vendor_sop_categories (SOP 分類)                    │    │
│  │  ✓ vendor_sop_items (SOP 項目)                         │    │
│  │  ✓ vendor_sop_groups (SOP 群組)                        │    │
│  │  ✓ vendor_sop_intent_intents (SOP 意圖關聯)            │    │
│  │                                                        │    │
│  │  表單系統表: 🆕                                         │    │
│  │  ✓ form_schemas (表單定義)                             │    │
│  │  ✓ form_submissions (表單提交記錄)                      │    │
│  │  ✓ form_field_values (表單欄位值)                       │    │
│  │                                                        │    │
│  │  其他系統表:                                            │    │
│  │  ✓ chat_history (對話歷史)                             │    │
│  │  ✓ unclear_questions (未知問題)                         │    │
│  │  ✓ suggested_intents (意圖建議)                         │    │
│  │  ✓ test_scenarios (測試情境)                           │    │
│  │                                                        │    │
│  │  Phase 2:                                              │    │
│  │  ⏳ tenants (租客)                                     │    │
│  │  ⏳ vendor_apis (外部 API)                             │    │
│  │  ⏳ vendor_api_logs (API 日誌)                         │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Redis 7                                               │ 🆕 │
│  │  Port: 6381                                            │    │
│  ├────────────────────────────────────────────────────────┤    │
│  │  三層緩存:                                              │    │
│  │  ✓ 問題緩存 (TTL: 1小時)                               │    │
│  │  ✓ 向量緩存 (TTL: 24小時)                              │    │
│  │  ✓ 結果緩存 (TTL: 1小時)                               │    │
│  │                                                        │    │
│  │  SOP 上下文緩存:                                        │    │
│  │  ✓ SOP 狀態 (TTL: 10分鐘 - 1小時)                      │    │
│  │                                                        │    │
│  │  表單會話緩存:                                          │    │
│  │  ✓ 表單狀態 (TTL: 30分鐘)                              │    │
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
│  │  ✓ Reranker 重排 │                                           │
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
| **FastAPI** | 0.104+ | Web 框架 |
| **SQLAlchemy** | 2.0+ | ORM |
| **Pydantic** | 2.0+ | 資料驗證 |
| **OpenAI SDK** | 1.0+ | LLM 整合 |
| **pgvector** | 0.2+ | 向量搜尋 |
| **asyncpg** | 0.28+ | 異步 PostgreSQL 驅動 |
| **Redis** | 7.0+ | 緩存系統 🆕 |

### 前端

| 技術 | 版本 | 用途 |
|------|------|------|
| **Vue.js** | 3.3+ | 前端框架 |
| **Vue Router** | 4.0+ | 路由管理 |
| **Axios** | 1.0+ | HTTP 客戶端 |
| **Vite** | 4.0+ | 建置工具 |
| **SimpleMDE** | 2.18+ | Markdown 編輯器 |
| **vuedraggable** | 4.1+ | 拖拽排序 🆕 |

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
| **Redis** | 7.0+ | 緩存與會話存儲 🆕 |

---

## 核心服務

### 1. RAG Orchestrator（核心引擎）

**位置：** `rag-orchestrator/`

**職責：**
- 意圖分類與路由
- RAG 知識檢索
- Reranker 二階段優化
- LLM 答案優化
- 業者參數管理
- SOP 流程協調 🆕
- 表單管理與填寫 🆕
- Chat API 提供

**技術架構：**

```
rag-orchestrator/
├── main.py                          # FastAPI 應用入口
├── routers/
│   ├── chat.py                      # Chat API 路由
│   ├── vendors.py                   # 業者管理 API
│   ├── knowledge.py                 # 知識庫 API
│   ├── intents.py                   # 意圖管理 API
│   ├── forms.py                     # 表單管理 API 🆕
│   └── cache.py                     # 緩存管理 API 🆕
├── services/
│   ├── intent_classifier.py         # 意圖分類服務
│   ├── rag_engine.py                # RAG 檢索服務
│   ├── reranker_service.py          # Reranker 重排序 🆕
│   ├── llm_answer_optimizer.py      # LLM 優化服務
│   ├── cache_service.py             # 三層緩存服務 🆕
│   ├── vendor_parameter_resolver.py # 業者參數解析
│   ├── vendor_knowledge_retriever.py# 業者知識檢索
│   ├── vendor_sop_retriever.py      # SOP 檢索服務 🆕
│   ├── sop_orchestrator.py          # SOP 協調器 🆕
│   ├── sop_trigger_handler.py       # SOP 觸發處理 🆕
│   ├── form_manager.py              # 表單管理器 🆕
│   ├── tenant_identifier.py         # [Phase 2] 租客識別
│   ├── external_api_client.py       # [Phase 2] 外部 API
│   └── customer_service_assistant.py# [Phase 2] 客服助理
├── models/
│   └── database.py                  # SQLAlchemy 模型
└── utils/
    ├── vector_utils.py              # 向量處理工具
    └── redis_client.py              # Redis 客戶端 🆕
```

**核心流程：**

```python
# Chat API 處理流程（2026-02-03 最新版本）
async def process_chat_message(message, vendor_id, user_role, session_id):
    # 0. 檢查 SOP 上下文（如果存在）
    sop_context = await sop_orchestrator.check_context(session_id)
    if sop_context:
        # 處理 SOP 觸發關鍵詞或表單填寫
        result = await sop_orchestrator.handle_context(message, sop_context)
        if result:
            return result

    # 1. 意圖分類
    intent = await intent_classifier.classify(message)

    # 2. RAG 檢索（語義搜尋）
    search_results = await rag_service.search(
        query=message,
        intent_id=intent.id,
        vendor_id=vendor_id,
        user_role=user_role
    )

    # 3. Reranker 二階段重排序
    reranked_results = await reranker_service.rerank(
        query=message,
        documents=search_results
    )

    # 4. 檢查是否有 SOP 匹配
    sop_result = await sop_orchestrator.process_query(
        user_message=message,
        vendor_id=vendor_id,
        user_role=user_role,
        session_id=session_id,
        user_id=user_id
    )

    # 5. 獲取業者參數
    vendor_params = await parameter_resolver.get_vendor_parameters(vendor_id)
    vendor_name = await get_vendor_name(vendor_id)

    # 6. LLM 優化 + 參數注入
    result = await llm_optimizer.optimize_answer(
        question=message,
        search_results=reranked_results,
        sop_result=sop_result,  # 🆕 SOP 結果
        confidence_level=intent.confidence_level,
        intent_info=intent,
        vendor_params=vendor_params,
        vendor_name=vendor_name
    )

    return result
```

---

### 2. SOP Orchestrator（SOP 協調器）🆕

**職責：**
- SOP 匹配與檢索
- SOP 觸發模式處理（manual/immediate/auto）
- SOP 上下文管理（Redis）
- 觸發關鍵詞偵測
- 表單觸發與執行

**觸發模式：**

| 模式 | 說明 | 流程 |
|------|------|------|
| **manual** (排查型) | 顯示 SOP 內容後，等待用戶主動說觸發關鍵詞 | SOP 內容 → 等待關鍵詞 → 執行動作 |
| **immediate** (行動型) | 顯示 SOP 內容後，立即詢問是否執行 | SOP 內容 → 確認提示 → 執行動作 |
| **auto** (自動型) | 直接執行，不等待確認 | 直接執行動作（表單/API） |

**核心方法：**

```python
class SOPOrchestrator:
    async def process_query(self, user_message, vendor_id, session_id, **kwargs):
        """處理用戶查詢，檢查 SOP 匹配"""

        # 1. 檢查現有上下文
        context = await self._check_context(session_id)

        # 2. 如果有上下文，處理觸發
        if context:
            return await self._handle_trigger(user_message, context)

        # 3. 搜尋 SOP
        sop_results = await sop_retriever.search(
            query=user_message,
            vendor_id=vendor_id,
            user_role=kwargs.get('user_role')
        )

        # 4. 根據觸發模式處理
        if best_match:
            trigger_mode = best_match.get('trigger_mode')

            if trigger_mode == 'manual':
                return await self._handle_manual_mode(best_match, session_id)
            elif trigger_mode == 'immediate':
                return await self._handle_immediate_mode(best_match, session_id)
            elif trigger_mode == 'auto':
                return await self._handle_auto_mode(best_match, session_id)
```

---

### 3. Form Manager（表單管理器）🆕

**職責：**
- 動態表單創建與編輯
- 表單填寫流程管理
- 表單驗證（台灣姓名、電話、地址等）
- 表單提交與存儲
- API 整合（on_complete_action）

**表單完成後動作：**

| 動作類型 | 說明 | 用途 |
|----------|------|------|
| **show_knowledge** | 顯示知識庫答案 | 一般資料收集 |
| **call_api** | 調用外部 API | 將表單數據傳送到業者系統 |
| **both** | 兩者都執行 | 同時顯示訊息並調用 API |

**API 配置結構：**

```json
{
  "method": "POST",
  "endpoint": "https://api.example.com/submit",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer TOKEN"
  },
  "params": {
    "source": "chatbot",
    "notify": true
  }
}
```

---

### 4. Embedding API（向量服務）🆕

**位置：** `embedding-service/`

**職責：**
- 統一向量生成
- Redis 向量緩存
- 批量向量處理

**緩存策略：**
- TTL: 24 小時
- 命中率目標: 70-90%
- 節省成本: OpenAI API 調用減少 70-90%

---

### 5. Knowledge Admin（管理後台）

**位置：** `knowledge-admin/frontend/`

**職責：**
- 業者管理（CRUD）
- 業者配置管理
- 知識庫管理
- SOP 管理 🆕
- 表單編輯器 🆕
- 意圖管理
- 審核中心 🆕
- Chat 測試介面

**頁面架構：**

```
frontend/src/
├── views/
│   ├── KnowledgeView.vue            # 知識庫管理
│   ├── IntentsView.vue              # 意圖管理
│   ├── VendorManagementView.vue     # 業者管理
│   ├── VendorConfigView.vue         # 業者配置
│   ├── ChatTestView.vue             # Chat 測試
│   ├── ReviewCenterView.vue         # 審核中心 🆕
│   ├── FormEditorView.vue           # 表單編輯器 🆕
│   ├── FormListView.vue             # 表單列表 🆕
│   ├── TenantManagementView.vue     # [Phase 2] 租客管理
│   ├── APIConfigView.vue            # [Phase 2] API 配置
│   └── CustomerServiceView.vue      # [Phase 2] 客服助理
├── components/
│   ├── VendorSOPManager.vue         # SOP 管理組件 🆕
│   └── review/                      # 審核組件 🆕
│       ├── ScenarioReviewTab.vue
│       ├── UnclearQuestionReviewTab.vue
│       ├── IntentReviewTab.vue
│       └── KnowledgeReviewTab.vue
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

🆕 SOP 系統表:

┌───────────────────┐         ┌───────────────────┐
│ vendor_sop_       │────1:N──│ vendor_sop_items  │
│ categories        │         │                   │
│ - id              │         │ - id              │
│ - name            │         │ - category_id(FK) │
│ - vendor_id (FK)  │         │ - title           │
└───────────────────┘         │ - content         │
                              │ - trigger_mode    │
                              │ - next_action     │
                              │ - next_form_id    │
                              │ - trigger_keywords│
                              │ - immediate_prompt│
                              └───────────────────┘

🆕 表單系統表:

┌───────────────┐         ┌───────────────────┐         ┌────────────────┐
│ form_schemas  │────1:N──│ form_submissions  │────1:N──│ form_field_    │
│               │         │                   │         │ values         │
│ - form_id(PK) │         │ - id              │         │                │
│ - form_name   │         │ - form_id (FK)    │         │ - id           │
│ - vendor_id   │         │ - session_id      │         │ - submission_id│
│ - fields      │         │ - submitted_at    │         │ - field_name   │
│ - on_complete │ 🆕      │ - status          │         │ - field_value  │
│ - api_config  │ 🆕      └───────────────────┘         └────────────────┘
└───────────────┘

其他系統表:

┌───────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ chat_history  │    │ unclear_questions│    │ suggested_intents│
│               │    │                  │    │                  │
│ - id          │    │ - id             │    │ - id             │
│ - session_id  │    │ - question       │    │ - question_id    │
│ - vendor_id   │    │ - frequency      │    │ - suggested_name │
│ - question    │    │ - status         │    │ - confidence     │
│ - answer      │    └──────────────────┘    └──────────────────┘
└───────────────┘

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
```

### 核心資料表

#### Phase 1（已實作）

| 表名 | 說明 | 主要欄位 |
|------|------|---------|
| `knowledge_base` | 知識庫 | question, answer, embedding, vendor_id, scope |
| `intents` | 意圖 | name, intent_type, keywords, example_questions |
| `vendors` | 業者 | code, name, subscription_plan, is_active |
| `vendor_configs` | 業者配置 | vendor_id, category, param_key, param_value |
| `vendor_sop_categories` 🆕 | SOP 分類 | name, vendor_id, sort_order |
| `vendor_sop_items` 🆕 | SOP 項目 | title, content, trigger_mode, next_action |
| `vendor_sop_groups` 🆕 | SOP 群組 | name, vendor_id |
| `form_schemas` 🆕 | 表單定義 | form_id, form_name, fields, on_complete_action, api_config |
| `form_submissions` 🆕 | 表單提交 | form_id, session_id, status, submitted_at |
| `form_field_values` 🆕 | 表單欄位值 | submission_id, field_name, field_value |
| `chat_history` | 對話歷史 | session_id, vendor_id, question, answer |
| `unclear_questions` | 未知問題 | question, frequency, status, last_asked |
| `suggested_intents` | 意圖建議 | question_id, suggested_name, confidence |
| `test_scenarios` | 測試情境 | question, expected_answer, difficulty, status |

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
CREATE INDEX idx_sop_vendor ON vendor_sop_items(vendor_id);
CREATE INDEX idx_form_vendor ON form_schemas(vendor_id);

-- 意圖查詢索引
CREATE INDEX idx_knowledge_intent ON knowledge_base(intent_id);

-- 複合索引（業者 + 意圖）
CREATE INDEX idx_knowledge_vendor_intent ON knowledge_base(vendor_id, intent_id);

-- SOP 檢索索引
CREATE INDEX idx_sop_embedding ON vendor_sop_items
USING ivfflat (primary_embedding vector_cosine_ops)
WITH (lists = 50);

-- 表單會話索引
CREATE INDEX idx_form_submissions_session ON form_submissions(session_id);
```

---

## API 架構

### RESTful API 設計原則

1. **資源導向**：使用名詞而非動詞
2. **HTTP 方法**：GET（查詢）、POST（建立）、PUT（更新）、DELETE（刪除）
3. **版本控制**：`/api/v1/`
4. **回應格式**：統一 JSON 格式
5. **錯誤處理**：標準 HTTP 狀態碼 + 詳細錯誤訊息

### API 分層

```
┌─────────────────────────────────────────────────┐
│  Public API (面向終端使用者)                     │
├─────────────────────────────────────────────────┤
│  POST /api/v1/message                           │
│  - B2C 聊天（租客）                              │
│  - vendor_id 識別業者                            │
│  - 支援 SOP 觸發與表單填寫 🆕                     │
│  - 返回客製化答案                                │
│                                                 │
│  POST /api/v1/chat/stream 🆕                    │
│  - 流式聊天（Server-Sent Events）                │
│  - 即時反饋                                      │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  Internal API (面向業者客服) [Phase 2]          │
├─────────────────────────────────────────────────┤
│  POST /api/v2/customer-service                  │
│  - B2B 聊天（客服）                              │
│  - 支援租客識別 + 外部 API 整合                  │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  Management API (面向管理後台)                   │
├─────────────────────────────────────────────────┤
│  /api/v1/vendors/*        - 業者管理             │
│  /api/v1/knowledge/*      - 知識庫管理           │
│  /api/v1/intents/*        - 意圖管理             │
│  /api/v1/forms/*          - 表單管理 🆕          │
│  /api/v1/sop/*            - SOP 管理 🆕          │
│  /api/v1/cache/*          - 緩存管理 🆕          │
│  /api/v1/tenants/*        - [Phase 2] 租客管理   │
│  /api/v1/apis/*           - [Phase 2] API 配置   │
└─────────────────────────────────────────────────┘
```

### 主要 API 端點

#### Chat API

```bash
# 標準聊天
POST /api/v1/message
{
  "message": "租金怎麼繳？",
  "vendor_id": 1,
  "user_role": "customer",
  "session_id": "abc123"
}

# 流式聊天 🆕
POST /api/v1/chat/stream
Content-Type: application/json
Accept: text/event-stream

{
  "question": "租金怎麼繳？",
  "vendor_id": 1,
  "user_role": "customer",
  "session_id": "abc123"
}
```

#### 表單 API 🆕

```bash
# 獲取表單定義
GET /api/v1/forms/{form_id}

# 創建表單
POST /api/v1/forms
{
  "form_id": "rental_inquiry",
  "form_name": "租屋詢問表",
  "fields": [...],
  "on_complete_action": "call_api",
  "api_config": {...}
}

# 更新表單
PUT /api/v1/forms/{form_id}

# 刪除表單
DELETE /api/v1/forms/{form_id}
```

#### SOP API 🆕

```bash
# 獲取 SOP 分類
GET /api/v1/sop/categories?vendor_id=1

# 創建 SOP
POST /api/v1/sop/items
{
  "title": "垃圾分類說明",
  "content": "...",
  "trigger_mode": "immediate",
  "next_action": "form_fill",
  "next_form_id": "waste_sorting_form"
}

# 更新 SOP
PUT /api/v1/sop/items/{sop_id}
```

#### 緩存 API 🆕

```bash
# 清除緩存
DELETE /api/v1/cache/clear?cache_type=all

# 查看緩存統計
GET /api/v1/cache/stats
```

### API 安全性

| 機制 | 實作方式 | 狀態 |
|------|---------|------|
| **HTTPS** | Nginx SSL/TLS 終止 | ✅ 生產環境 |
| **API Key** | Header: `X-API-Key` | ⏳ 待實作 |
| **Rate Limiting** | 基於 IP 或 API Key | ⏳ 待實作 |
| **CORS** | FastAPI CORS Middleware | ✅ 已實作 |
| **Input Validation** | Pydantic Models | ✅ 已實作 |
| **Redis Session** | Session 存儲與驗證 | ✅ 已實作 🆕 |

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
      - knowledge-admin-web

  # 核心後端服務
  rag-orchestrator:
    build: ./rag-orchestrator
    ports:
      - "8100:8100"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/aichatbot
      - REDIS_URL=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - EMBEDDING_API_URL=http://embedding-api:5001
    depends_on:
      - postgres
      - redis

  # Embedding API 🆕
  embedding-api:
    build: ./embedding-service
    ports:
      - "5001:5001"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - redis

  # 知識管理 API
  knowledge-admin-api:
    build: ./knowledge-admin/backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/aichatbot
    depends_on:
      - postgres

  # 管理後台前端（開發模式）
  knowledge-admin-web:
    build: ./knowledge-admin/frontend
    ports:
      - "8087:5173"  # Vite dev server
    volumes:
      - ./knowledge-admin/frontend:/app
    profiles:
      - dev

  # PostgreSQL 資料庫
  postgres:
    image: pgvector/pgvector:pg15
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=aichatbot_user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=aichatbot
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init:/docker-entrypoint-initdb.d

  # Redis 緩存 🆕
  redis:
    image: redis:7-alpine
    ports:
      - "6381:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  postgres_data:
  redis_data:
```

### 環境變數管理

```bash
# .env 檔案
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://aichatbot_user:password@localhost:5432/aichatbot
REDIS_URL=redis://localhost:6381/0
EMBEDDING_API_URL=http://localhost:5001
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
| **Redis 安全** 🆕 | 密碼保護、網路隔離 |

### 應用安全

| 項目 | 實作方式 |
|------|---------|
| **SQL 注入防護** | SQLAlchemy ORM，參數化查詢 |
| **XSS 防護** | Vue.js 自動轉義，Content Security Policy |
| **CSRF 防護** | Token 驗證（API 為 stateless，暫不需要） |
| **輸入驗證** | Pydantic 強制驗證所有輸入 |
| **表單驗證** 🆕 | 台灣姓名、電話、地址格式驗證 |

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
            ┌────────────┴────────────┐
            ↓                         ↓
       PostgreSQL                  Redis
    (Read Replicas)              (Cluster)
```

**支援方式：**
- RAG Orchestrator 為無狀態服務，可水平擴展
- PostgreSQL 讀寫分離（主從複製）
- Redis Cluster 模式（分片與複製）🆕

### 效能優化

| 優化項目 | 實作方式 | 狀態 |
|---------|---------|------|
| **參數快取** | 記憶體快取業者參數 | ✅ 已實作 |
| **向量索引** | IVFFlat 索引加速搜尋 | ✅ 已實作 |
| **連線池** | SQLAlchemy 連線池 | ✅ 已實作 |
| **非同步處理** | FastAPI async/await | ✅ 已實作 |
| **Redis 三層緩存** 🆕 | 問題/向量/結果緩存 | ✅ 已實作 |
| **Reranker 優化** 🆕 | Cross-Encoder 重排序 | ✅ 已實作 |
| **SOP 上下文緩存** 🆕 | Redis TTL 管理 | ✅ 已實作 |
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
│  - Redis Monitoring: 緩存效能 🆕         │
└─────────────────────────────────────────┘
```

---

## 資料流圖

### B2C 聊天流程（2026-02-03 最新版本）

```
租客輸入問題
    ↓
[POST /api/v1/message]
    vendor_id: 2
    session_id: "abc123"
    message: "垃圾分類還是不行"
    ↓
檢查 SOP 上下文（Redis）
    ↓ 找到 SOP 上下文（MANUAL_WAITING 狀態）
    ↓
檢測觸發關鍵詞
    ↓ 匹配到 "還是不行" → 觸發關鍵詞
    ↓
執行 SOP 後續動作（next_action）
    ↓ next_action: "form_fill"
    ↓ next_form_id: "rental_inquiry"
    ↓
啟動表單填寫
    ↓
[Form Manager]
    ↓
返回第一個問題
    ↓
"請問您的姓名是？"
    ↓
用戶填寫表單
    ↓
提交表單
    ↓
執行完成後動作（on_complete_action）
    ↓
┌──────────────┬──────────────┬──────────────┐
│ show_knowledge│   call_api   │    both      │
│              │              │              │
│ 顯示知識答案  │ 調用外部API  │  兩者都執行   │
└──────────────┴──────────────┴──────────────┘
```

### SOP 觸發模式流程圖 🆕

```
用戶問題: "垃圾分類"
    ↓
意圖分類 + SOP 檢索
    ↓
找到匹配的 SOP
    ↓
┌─────────────┬─────────────┬─────────────┐
│   manual    │  immediate  │    auto     │
│  (排查型)   │  (行動型)   │  (自動型)   │
└─────────────┴─────────────┴─────────────┘
       │              │              │
       ↓              ↓              ↓
  顯示 SOP 內容   顯示 SOP 內容   直接執行動作
       │              │
       ↓              ↓
  等待觸發關鍵詞  附加確認提示
       │         (immediate_prompt)
       ↓              │
  用戶說關鍵詞      ↓
  "還是不行"    用戶確認 "要"
       │              │
       └──────┬───────┘
              ↓
        執行後續動作
              ↓
     ┌────────┴────────┐
     │                 │
  form_fill        api_call
     │                 │
  啟動表單         調用API
```

### B2B 客服流程（Phase 2）

```
客服輸入問題
    ↓
[POST /api/v2/customer-service]
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

- **版本：** 3.0
- **建立日期：** 2025-10-09
- **最後更新：** 2026-02-03
- **作者：** Claude Code
- **適用系統版本：** Phase 1 完成 + SOP 系統 + 表單管理 + Phase 2 規劃
- **變更紀錄：**
  - v3.0 (2026-02-03): 🆕 添加 SOP 系統、表單管理、Redis 緩存、Reranker、API 配置
  - v2.0 (2025-10-10): 更新為 Phase 1 多業者架構 + LLM 智能參數注入
  - v1.0 (2025-10-09): 初始版本

---

## 🆕 最新功能（2026-02-03）

### SOP 系統
- ✅ 三種觸發模式（manual/immediate/auto）
- ✅ SOP 上下文管理（Redis TTL）
- ✅ 觸發關鍵詞偵測
- ✅ 表單/API 後續動作執行

### 表單管理系統
- ✅ 動態表單創建與編輯
- ✅ 表單填寫流程管理
- ✅ 台灣格式驗證（姓名、電話、地址）
- ✅ 完成後動作（show_knowledge/call_api/both）
- ✅ API 配置（method, endpoint, headers, params）

### Redis 緩存系統
- ✅ 三層緩存（問題/向量/結果）
- ✅ SOP 上下文緩存
- ✅ 表單會話緩存
- ✅ 節省 70-90% OpenAI API 成本

### Reranker 優化
- ✅ Cross-Encoder 二階段重排序
- ✅ 準確率提升 3 倍（25%→75%）
- ✅ 智能檢索路由

### 流式聊天
- ✅ Server-Sent Events (SSE)
- ✅ 即時反饋用戶體驗
