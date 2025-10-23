# 🤖 AIChatbot - AI 客服知識庫系統

完整的 SaaS 多租戶 AI 客服知識庫管理系統，包含智能問答、測試情境管理、知識審核、回測框架，支援 RAG 檢索整合與多業者隔離。

## ✨ 核心功能

### 🤖 RAG Orchestrator（智能問答系統）
- 🎯 **多 Intent 分類** - 支援一個問題同時匹配多個意圖（主要 + 次要）
- 🔍 **混合檢索策略** - Intent 過濾 + 向量相似度，差異化加成（1.5x / 1.2x）
- 📊 **三級信心度評估** - 高/中/低信心度判斷
- ✨ **LLM 答案優化** - 使用 GPT-4o-mini 優化答案品質
- 🧠 **意圖建議引擎** - OpenAI 自動分析未知問題並建議新意圖
- ⚡ **三層緩存系統** ⭐ NEW - Redis 快取（問題/向量/結果），節省 70-90% API 成本
- 🌊 **流式聊天 API** ⭐ NEW - Server-Sent Events (SSE)，即時反饋用戶體驗
- 📋 **SOP 智能整合** ⭐ NEW - 業者 SOP 模板，支援金流模式和業種類型動態調整

### 🧪 測試情境管理系統 ⭐ NEW
- 📝 **測試題庫資料庫** - 管理測試問題、預期答案、難度分級
- 🔄 **用戶問題自動轉換** - 頻率 ≥2 自動創建測試情境
- 🎯 **智能重試機制** - 被拒絕情境達高頻（≥5）自動重試
- 👥 **審核中心** - 統一介面審核：測試情境、用戶問題、意圖建議、AI 知識候選
- 📊 **回測框架** - 支援 3 種品質評估模式（basic, detailed, hybrid）

### 🏢 多業者支援（Multi-Vendor SaaS）
- 🏪 **業者管理系統** - 完整的業者 CRUD、啟用/停用控制
- ⚙️ **業者參數配置** - 分類管理（帳務、合約、服務、聯絡）
- 🎨 **LLM 智能參數注入** - 不使用模板變數，AI 自動根據業者參數調整答案
- 🔐 **多租戶知識隔離** - 三層知識範圍（global, vendor, customized）
- 🎯 **動態業務範圍** - 基於 user_role 自動決定 B2B/B2C 場景 ⭐ NEW
- 💬 **雙場景 Chat API** - 同時支援 B2C (客戶) 和 B2B (員工) 對話

### 📚 知識庫管理
- 🔍 **向量化知識庫** - PostgreSQL + pgvector 語義搜尋
- 📝 **Markdown 編輯器** - 即時預覽、版本追蹤
- 🤖 **AI 知識生成** - OpenAI 自動從測試情境生成知識
- 🏷️ **知識分類系統** - 意圖分類、業務範圍管理
- ⚡ **Embedding API** - 統一向量生成服務，Redis 快取節省 70-90% 成本
- 📥 **知識匯入系統** ⭐ NEW - 批量匯入 Excel/JSON/TXT，雙層去重（文字+語意）

## 🏗️ 系統架構

```
┌─────────────────────────────────────────────────────────────────┐
│                     審核中心 (Review Center)                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────┐ │
│  │ 測試情境審核  │ │ 用戶問題審核  │ │ 意圖建議審核  │ │ AI知識  │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ 知識管理前端     │────▶│ 知識管理 API     │────▶│ PostgreSQL      │
│  (Vue.js)       │     │  (FastAPI)       │     │  + pgvector     │
│  Port: 8080     │     │  Port: 8000      │     │  Port: 5432     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                           ▲
                               │                           │
                               ▼                           │
                        ┌──────────────────┐              │
                        │ Embedding API    │──────────────┘
                        │  (FastAPI)       │
                        │  Port: 5001      │
                        └──────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │ Redis Cache      │
                        │  Port: 6379      │
                        └──────────────────┘

                        ┌──────────────────┐
                        │ RAG Orchestrator │◀────── Chat API (多業者)
                        │  (FastAPI)       │
                        │  Port: 8100      │
                        └──────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │ 回測框架          │
                        │ (Python Script)  │
                        └──────────────────┘
```

## 📦 服務列表

| 服務 | 技術 | Port | 功能 |
|------|------|------|------|
| **知識管理前端（開發）** | Vue.js 3 + Vite | 8087 | 審核中心、知識管理、業者管理、測試情境管理（熱重載）|
| **知識管理前端（正式）** | Vue.js 3 + Nginx | 8081 | 靜態檔案服務（需指定 profile）|
| **知識管理 API** | FastAPI | 8000 | Knowledge CRUD、測試情境 CRUD、自動向量更新 |
| **Embedding API** | FastAPI | 5001 | 統一向量生成、Redis 快取 |
| **RAG Orchestrator** | FastAPI | 8100 | 智能問答、意圖分類、緩存管理、知識生成 |
| **PostgreSQL** | pgvector/pgvector | 5432 | 資料庫、向量儲存、業者資料、測試題庫 |
| **Redis** | Redis 7 | 6381 | Embedding + RAG 三層快取 |
| **pgAdmin** | pgAdmin 4 | 5050 | 資料庫管理工具 |

## 🚀 快速開始

### 前置需求
- Docker & Docker Compose
- OpenAI API Key
- (可選) Python 3.9+ & Node.js 18+ (本地開發)

### 1. 設定環境變數

```bash
# 複製範例檔案
cp .env.example .env

# 編輯 .env，填入你的 OpenAI API Key
nano .env
```

**修改 `.env` 檔案：**
```env
OPENAI_API_KEY=sk-proj-your-actual-api-key-here
```

### 2. 啟動所有服務

```bash
# 啟動所有服務
docker-compose up -d

# 查看服務狀態
docker-compose ps

# 查看日誌
docker-compose logs -f
```

### 3. 存取服務

**開發模式（預設）**:
- 🌐 **審核中心**: http://localhost:8087/review-center
  - 測試情境審核
  - 用戶問題審核
  - 意圖建議審核
  - AI 知識候選審核
- 📚 **知識庫管理**: http://localhost:8087/knowledge
- 🏢 **業者管理**: http://localhost:8087/vendors
- 🧪 **Chat 測試**: http://localhost:8087/chat-test
- 📊 **回測執行**: http://localhost:8087/backtest
- 🔄 **知識意圖分類**: http://localhost:8087/knowledge-reclassify

**API 文件**:
- 知識管理 API: http://localhost:8000/docs
- Embedding API: http://localhost:5001/docs
- RAG Orchestrator: http://localhost:8100/docs

**管理工具**:
- 🗄️ **pgAdmin**: http://localhost:5050 (帳號: `admin@aichatbot.com` / 密碼: `admin`)

**註**: 正式模式使用 port 8081，需指定 `--profile production`

## 📖 專案結構

```
AIChatbot/
├── embedding-service/        # Embedding API 服務
│   ├── app.py               # FastAPI 應用
│   ├── requirements.txt
│   └── Dockerfile
│
├── knowledge-admin/          # 知識管理系統
│   ├── backend/             # 後端 API
│   │   ├── app.py
│   │   ├── routes_test_scenarios.py    # 測試情境 CRUD API
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── frontend/            # 前端 Web UI
│       ├── src/
│       │   ├── App.vue
│       │   ├── router.js                # Vue Router 路由
│       │   ├── views/
│       │   │   ├── ReviewCenterView.vue      # 審核中心 ⭐
│       │   │   ├── TestScenariosView.vue     # 測試情境管理 ⭐
│       │   │   ├── KnowledgeView.vue         # 知識庫管理
│       │   │   ├── VendorManagementView.vue  # 業者管理
│       │   │   ├── ChatTestView.vue          # Chat 測試
│       │   │   └── BacktestView.vue          # 回測執行
│       │   └── components/
│       │       └── review/                   # 審核組件 ⭐
│       │           ├── ScenarioReviewTab.vue       # 測試情境審核
│       │           ├── UnclearQuestionReviewTab.vue # 用戶問題審核
│       │           ├── IntentReviewTab.vue         # 意圖建議審核
│       │           └── KnowledgeReviewTab.vue      # AI 知識審核
│       ├── package.json
│       └── Dockerfile
│
├── rag-orchestrator/        # RAG 協調器
│   ├── app.py              # FastAPI 主服務
│   ├── routers/            # API 路由
│   │   ├── chat.py                    # 聊天 API (多業者 + 流式)
│   │   ├── cache.py                   # 緩存管理 API ⭐ NEW
│   │   ├── vendors.py                 # 業者管理
│   │   ├── intents.py                 # 意圖管理
│   │   ├── suggested_intents.py       # 意圖建議
│   │   ├── knowledge.py               # 知識分類
│   │   ├── knowledge_generation.py    # AI 知識生成 ⭐
│   │   ├── knowledge_import.py        # 知識匯入 ⭐ NEW
│   │   └── business_scope.py          # 業務範圍
│   ├── services/           # 核心服務
│   │   ├── intent_classifier.py           # 意圖分類
│   │   ├── rag_engine.py                  # RAG 檢索
│   │   ├── cache_service.py               # 三層緩存服務 ⭐ NEW
│   │   ├── llm_answer_optimizer.py        # LLM 答案優化 + 參數注入
│   │   ├── knowledge_generator.py         # AI 知識生成器 ⭐
│   │   ├── knowledge_import_service.py    # 知識匯入服務 ⭐ NEW
│   │   ├── intent_manager.py              # 意圖管理器 ⭐
│   │   ├── unclear_question_manager.py    # 用戶問題管理 ⭐
│   │   ├── vendor_knowledge_retriever.py  # 多業者知識檢索
│   │   └── vendor_parameter_resolver.py   # 業者參數解析
│   ├── requirements.txt
│   └── Dockerfile
│
├── database/                # 資料庫
│   ├── init/               # 初始化腳本
│   │   └── *.sql          # 資料庫初始化 SQL
│   ├── migrations/         # 資料庫遷移（28 個，按編號順序）⭐
│   │   ├── README.md       # Migration 說明文檔
│   │   ├── 09-37-*.sql    # 遷移文件（編號已優化，無衝突）✅
│   │   ├── 33-fix-knowledge-approval-embedding-intent.sql
│   │   ├── 37-create-vendor-sop-tables.sql  # SOP 範本系統 ⭐
│   │   └── ...            # 其他遷移
│   └── seeds/              # 測試種子數據 ✅ NEW
│       ├── README.md       # 使用說明
│       ├── sop_templates.sql
│       └── *.sql          # 其他種子數據
│
├── scripts/                 # 實用腳本 ✅
│   ├── README.md           # 腳本使用指南
│   ├── knowledge_extraction/  # 知識提取工具
│   │   └── backtest_framework.py    # 回測框架 ⭐
│   ├── tools/              # 開發工具（預留）
│   ├── import_sop_from_excel.py      # SOP 匯入工具
│   └── *.py               # 其他生產腳本
│
├── docs/                   # 📚 完整文檔（已重組優化）✅
│   ├── guides/             # 使用指南（含 DEPLOYMENT, QUICKSTART）
│   ├── features/           # 功能文檔（含 SOP 架構文檔）
│   ├── api/               # API 參考文檔
│   ├── backtest/          # 回測框架文檔
│   ├── planning/          # 規劃文檔（含待開發功能）
│   ├── examples/          # 測試數據範例
│   ├── archive/           # 歷史文檔（已優化 27%）✅
│   │   ├── README.md      # 歸檔說明
│   │   ├── completion_reports/  (20 個)
│   │   ├── evaluation_reports/  (8 個)
│   │   └── database_migrations/ (舊參考)
│   ├── FILE_STRUCTURE_ANALYSIS.md   # 項目結構分析
│   └── FILE_CLEANUP_REPORT.md       # 整理報告
│
├── tests/                  # 🧪 測試文件（已結構化）✅
│   ├── integration/        # 整合測試
│   │   ├── test_business_logic_matrix.py  # 業務邏輯測試
│   │   ├── test_fallback_mechanism.py
│   │   └── *.py           # 其他整合測試
│   ├── deduplication/      # 去重檢測測試 ✅ NEW
│   │   ├── README.md       # 測試說明
│   │   ├── test_enhanced_detection.py
│   │   ├── verify_duplicate_detection.py
│   │   └── *.py           # 其他去重測試
│   └── run_*_tests.sh     # 測試執行腳本
│
├── docker-compose.yml      # Docker Compose 配置
├── docker-compose.dev.yml  # 開發環境配置
├── docker-compose.prod.yml # 生產環境配置
├── Makefile               # 快速指令
├── .env.example           # 環境變數範例
├── QUICKSTART.md         # 快速開始指南
├── CHANGELOG.md          # 變更日誌
└── README.md             # 本檔案
```

## 🛠️ 技術棧

### 後端
- **語言**: Python 3.11
- **框架**: FastAPI 0.104+
- **AI**: OpenAI API (text-embedding-3-small, gpt-4o-mini, gpt-3.5-turbo)
- **資料庫**: PostgreSQL 16 + pgvector
- **快取**: Redis 7
- **HTTP 客戶端**: httpx, requests

### 前端
- **框架**: Vue.js 3 + Vue Router
- **UI 組件**: 自定義組件系統
- **編輯器**: SimpleMDE (Markdown)
- **HTTP**: Axios
- **樣式**: 原生 CSS

### 基礎設施
- **容器化**: Docker & Docker Compose
- **資料庫管理**: pgAdmin 4
- **向量儲存**: pgvector extension (IVFFlat index)

## 📚 文件導覽

**📖 文檔中心**: [docs/README.md](./docs/README.md) - 完整文檔導覽與分類索引 ⭐

### 🚀 快速開始
- 📘 **快速開始指南**: [QUICKSTART.md](./QUICKSTART.md)
- 📖 **開發工作流程**: [docs/guides/DEVELOPMENT_WORKFLOW.md](./docs/guides/DEVELOPMENT_WORKFLOW.md)

### ⭐ 最新功能文檔
- 📥 **知識匯入系統** ⭐ NEW:
  - [知識匯入功能文檔](./docs/features/KNOWLEDGE_IMPORT_FEATURE.md)
  - [知識匯入 API 參考](./docs/api/KNOWLEDGE_IMPORT_API.md)
- 🧪 **測試情境系統**:
  - [測試情境狀態管理](./docs/features/TEST_SCENARIO_STATUS_MANAGEMENT.md)
  - [拒絕情境智能重試](./docs/features/REJECTED_SCENARIO_RETRY_IMPLEMENTATION.md)
  - [測試情境遷移指南](./docs/guides/TEST_SCENARIOS_MIGRATION_GUIDE.md)
- 🎯 **多 Intent 分類**: [docs/features/MULTI_INTENT_CLASSIFICATION.md](./docs/features/MULTI_INTENT_CLASSIFICATION.md)
- 🤖 **AI 知識生成**: [docs/features/AI_KNOWLEDGE_GENERATION_FEATURE.md](./docs/features/AI_KNOWLEDGE_GENERATION_FEATURE.md)

### 🏛️ 系統架構
- 📐 **系統架構文件**: [docs/architecture/SYSTEM_ARCHITECTURE.md](./docs/architecture/SYSTEM_ARCHITECTURE.md)
- 🏢 **Phase 1 多業者實作**: [docs/planning/PHASE1_MULTI_VENDOR_IMPLEMENTATION.md](./docs/planning/PHASE1_MULTI_VENDOR_IMPLEMENTATION.md)
- 📋 **Phase 2 規劃**: [docs/planning/PHASE2_PLANNING.md](./docs/planning/PHASE2_PLANNING.md)
- 🎯 **Business Scope 重構**: [docs/architecture/BUSINESS_SCOPE_REFACTORING.md](./docs/architecture/BUSINESS_SCOPE_REFACTORING.md) ⭐ NEW
- 🔐 **認證與業務範圍整合**: [docs/architecture/AUTH_AND_BUSINESS_SCOPE.md](./docs/architecture/AUTH_AND_BUSINESS_SCOPE.md) ⭐ NEW
- 🔌 **B2B API 整合框架設計**: [docs/B2B_API_INTEGRATION_DESIGN.md](./docs/B2B_API_INTEGRATION_DESIGN.md) ⭐ NEW

### 🧪 回測與測試
- 🔧 **回測優化指南**: [docs/guides/BACKTEST_OPTIMIZATION_GUIDE.md](./docs/guides/BACKTEST_OPTIMIZATION_GUIDE.md)
- 📊 **回測品質整合**: [docs/backtest/BACKTEST_QUALITY_INTEGRATION.md](./docs/backtest/BACKTEST_QUALITY_INTEGRATION.md)

### 🔧 技術參考
- 🎯 **Intent 管理**: [docs/features/INTENT_MANAGEMENT_README.md](./docs/features/INTENT_MANAGEMENT_README.md)
- 🧬 **知識提取**: [docs/guides/KNOWLEDGE_EXTRACTION_GUIDE.md](./docs/guides/KNOWLEDGE_EXTRACTION_GUIDE.md)
- 📡 **API 參考**: [docs/api/API_REFERENCE_PHASE1.md](./docs/api/API_REFERENCE_PHASE1.md)
- 🐘 **pgvector 設定**: [docs/guides/PGVECTOR_SETUP.md](./docs/guides/PGVECTOR_SETUP.md)
- 💻 **前端開發模式**: [docs/guides/FRONTEND_DEV_MODE.md](./docs/guides/FRONTEND_DEV_MODE.md) ⭐ NEW

### 📊 測試與驗證
- ✅ **Business Scope 測試報告**: [docs/architecture/BUSINESS_SCOPE_REFACTORING_TEST_REPORT.md](./docs/architecture/BUSINESS_SCOPE_REFACTORING_TEST_REPORT.md) ⭐ NEW

### 📋 系統報告
- 🔍 **系統盤查報告 (2025-10-13)**: [docs/SYSTEM_AUDIT_REPORT_2025-10-13.md](./docs/SYSTEM_AUDIT_REPORT_2025-10-13.md) - 系統健康檢查與改善建議 ⭐ NEW
- 📝 **Business Scope 重構總結**: [docs/BUSINESS_SCOPE_REFACTORING_SUMMARY.md](./docs/BUSINESS_SCOPE_REFACTORING_SUMMARY.md)
- 📝 **文檔更新總結**: [docs/DOCUMENTATION_UPDATE_SUMMARY.md](./docs/DOCUMENTATION_UPDATE_SUMMARY.md)

## 🔧 常用指令

### Docker 操作
```bash
# 啟動所有服務
docker-compose up -d

# 開發模式（動態掛載程式碼）
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 停止所有服務
docker-compose stop

# 停止並移除容器
docker-compose down

# 重新建置並啟動
docker-compose up -d --build

# 查看特定服務日誌
docker-compose logs -f rag-orchestrator

# 重啟特定服務
docker restart aichatbot-rag-orchestrator
```

### Makefile 快捷指令
```bash
# 開發環境啟動
make dev-up

# 生產環境啟動
make prod-up

# 停止所有服務
make down

# 查看日誌
make logs

# 前端重新編譯
make rebuild-frontend
```

### 資料庫操作
```bash
# 連線到 PostgreSQL
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin

# 檢查 migrations 執行狀態
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "SELECT * FROM schema_migrations ORDER BY id;"

# 執行回測
docker exec -it aichatbot-knowledge-admin-api python scripts/knowledge_extraction/backtest_framework.py
```

## 🔍 API 使用範例

### 1. 智能問答 Chat API

```bash
# 租客詢問問題（多業者支持 + SOP 整合 + RAG 檢索 + LLM 優化）
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "退租要怎麼辦理？",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "user123",
    "mode": "tenant",
    "include_sources": true
  }'

# 或使用流式端點（即時反饋）
curl -X POST http://localhost:8100/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "question": "退租要怎麼辦理？",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "user123"
  }'

# 回應範例
{
  "question": "退租要怎麼辦理？",
  "answer": "退租的流程如下：\n\n1. **提前通知**：在預定的退租日期前30天，請以書面方式通知房東。\n2. **繳清費用**：確保所有的租金及水電費已經繳清。\n3. **房屋檢查**：與房東約定時間進行檢查。\n4. **押金退還**：房屋狀況良好時，房東應在7個工作天內退還押金。",
  "confidence_score": 0.85,
  "confidence_level": "high",
  "intent": {
    "intent_type": "knowledge",
    "intent_name": "退租流程"
  },
  "retrieved_docs": [...],
  "processing_time_ms": 1250
}
```

### 2. 多業者 Chat API (雙場景支援) ⭐

```bash
# B2C 場景：租客詢問繳費日
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "繳費日是幾號？",
    "vendor_id": 1,
    "user_role": "customer"
  }'

# LLM 自動注入業者 A 的參數
{
  "answer": "您的租金繳費日為每月 1 號。請務必在這個日期前完成繳費，逾期 5 天後將加收 200 元手續費。",
  "intent_name": "帳務查詢",
  "confidence": 0.9,
  "vendor_id": 1
}

# B2B 場景：業者員工詢問系統管理問題
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "如何管理租約到期提醒？",
    "vendor_id": 1,
    "user_role": "staff"
  }'

# 回應：自動識別為內部管理場景，返回 B2B 知識
{
  "answer": "管理租約到期提醒的方式如下：\n\n1. **使用系統功能**：系統會自動發送租約到期提醒...",
  "intent_name": "租約查詢",
  "confidence": 0.8,
  "vendor_id": 1
}
```

**重要**: `user_role` 參數決定業務範圍：
- `"customer"` → B2C 外部場景（租客、房東知識）
- `"staff"` → B2B 內部場景（管理師、系統管理員知識）

### 3. 測試情境管理 API ⭐

```bash
# 獲取所有測試情境
curl http://localhost:8000/api/test-scenarios

# 獲取用戶問題候選列表（可轉為測試情境）
curl http://localhost:8000/api/test/unclear-questions/candidates

# 手動將用戶問題轉為測試情境
curl -X POST http://localhost:8000/api/test/unclear-questions/37/to-scenario \
  -H "Content-Type: application/json" \
  -d '{
    "difficulty": "medium",
    "created_by": "admin"
  }'

# 審核測試情境
curl -X POST http://localhost:8000/api/test-scenarios/20/review \
  -H "Content-Type: application/json" \
  -d '{
    "status": "approved",
    "reviewed_by": "admin",
    "review_notes": "測試情境合理"
  }'
```

### 4. AI 知識生成 API ⭐

```bash
# 從測試情境生成知識
curl -X POST http://localhost:8100/api/v1/knowledge/generate \
  -H "Content-Type: application/json" \
  -d '{
    "test_scenario_id": 20,
    "vendor_id": 1,
    "mode": "auto"
  }'

# 回應範例
{
  "knowledge_id": 45,
  "title": "社區游泳池開放時間",
  "content": "# 社區游泳池開放時間\n\n游泳池開放時間為每日 06:00-22:00...",
  "status": "pending_review",
  "generated_at": "2025-10-12T10:30:00"
}
```

### 5. 回測執行

```bash
# 基礎模式回測（快速）
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "quality_mode": "basic",
    "sample_size": 10
  }'

# Hybrid 模式回測（LLM 深度評估）
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "quality_mode": "hybrid",
    "difficulty": "medium",
    "sample_size": 20
  }'
```

### 6. 知識匯入 ⭐ NEW

```bash
# 上傳 Excel 檔案批量匯入知識
curl -X POST http://localhost:8100/api/v1/knowledge-import/upload \
  -F "file=@test_knowledge_data.xlsx" \
  -F "vendor_id=1" \
  -F "import_mode=append" \
  -F "enable_deduplication=true"

# 回應範例
{
  "job_id": "f87958b1-a660-477f-8725-17b074da76f0",
  "status": "processing",
  "message": "檔案上傳成功，開始處理中。所有知識將進入審核佇列..."
}

# 查詢處理狀態
curl http://localhost:8100/api/v1/knowledge-import/jobs/f87958b1-a660-477f-8725-17b074da76f0

# 回應範例（完成）
{
  "job_id": "f87958b1-a660-477f-8725-17b074da76f0",
  "status": "completed",
  "result": {
    "imported": 10,
    "skipped": 0,
    "errors": 0,
    "test_scenarios_created": 8,
    "mode": "review_queue"
  }
}
```

**功能特色**：
- ✅ 支援 Excel/JSON/TXT 多種格式
- 🔍 雙層去重：文字精確匹配 + 向量語意相似度（閾值 0.85）
- 🤖 AI 自動處理：問題生成、向量嵌入、意圖推薦
- 🧪 自動創建測試情境（B2C 知識）
- 📋 所有知識進入審核佇列，需人工審核
- 💰 成本優化：文字去重在 LLM 前執行，節省 API 成本

## 📊 專案狀態

### ✅ 已完成功能

| 功能模組 | 狀態 | 完成日期 |
|---------|------|---------|
| **基礎設施** | | |
| PostgreSQL + pgvector | ✅ | 2025-10-09 |
| Embedding API + Redis 快取 | ✅ | 2025-10-09 |
| 知識管理後台 (Vue.js) | ✅ | 2025-10-09 |
| Docker 完整部署 | ✅ | 2025-10-09 |
| **RAG 核心** | | |
| 多 Intent 分類系統 | ✅ | 2025-10-11 |
| 混合檢索策略（差異化加成） | ✅ | 2025-10-10 |
| 三級信心度評估 | ✅ | 2025-10-10 |
| LLM 答案優化 | ✅ | 2025-10-10 |
| 回測框架（3 種模式） | ✅ | 2025-10-11 |
| **意圖管理** | | |
| 意圖 CRUD + 訓練語句 | ✅ | 2025-10-11 |
| 意圖建議引擎（OpenAI） | ✅ | 2025-10-11 |
| 業務範圍管理 | ✅ | 2025-10-11 |
| **測試情境系統** ⭐ | | |
| 測試題庫資料庫設計 | ✅ | 2025-10-11 |
| 測試情境 CRUD API | ✅ | 2025-10-12 |
| 自動創建觸發器（頻率 ≥2） | ✅ | 2025-10-12 |
| 拒絕重試機制（頻率 ≥5） | ✅ | 2025-10-12 |
| 審核中心統一介面 | ✅ | 2025-10-12 |
| 用戶問題審核介面 | ✅ | 2025-10-12 |
| AI 知識生成器 | ✅ | 2025-10-12 |
| **多業者支援** | | |
| 業者管理系統 | ✅ | 2025-10-11 |
| 業者參數配置 | ✅ | 2025-10-11 |
| LLM 智能參數注入 | ✅ | 2025-10-11 |
| 多租戶知識隔離 | ✅ | 2025-10-11 |
| 動態業務範圍（user_role）| ✅ | 2025-10-12 |
| 雙場景 Chat API（B2B + B2C）| ✅ | 2025-10-12 |
| **知識匯入系統** ⭐ | | |
| 檔案解析（Excel/JSON/TXT）| ✅ | 2025-10-12 |
| 文字去重（精確匹配） | ✅ | 2025-10-12 |
| 語意去重（向量相似度 0.85）| ✅ | 2025-10-12 |
| AI 自動處理（問題/向量/意圖）| ✅ | 2025-10-12 |
| 測試情境自動創建（B2C）| ✅ | 2025-10-12 |
| 審核佇列整合 | ✅ | 2025-10-12 |
| 背景任務處理 | ✅ | 2025-10-12 |
| **系統清理與重構** ⭐ | | |
| Business Scope 架構重構 | ✅ | 2025-10-12 |
| 文檔重組（60+ 文件） | ✅ | 2025-10-12 |
| Migration 編號修復 | ✅ | 2025-10-12 |
| 資料庫重複數據清理 | ✅ | 2025-10-12 |
| 前端開發模式（熱重載）| ✅ | 2025-10-12 |
| **系統審計與清理** ⭐ | | |
| 系統盤查報告生成 | ✅ | 2025-10-13 |
| 遺留代碼歸檔（backend → archive）| ✅ | 2025-10-13 |
| 文檔中心創建（docs/README.md）| ✅ | 2025-10-13 |
| 重複配置文件清理 | ✅ | 2025-10-13 |

### ⏳ 待開發功能（Phase 2）

| 功能模組 | 優先級 | 預計時程 |
|---------|-------|---------|
| **B2B 進階功能** | | |
| 租客身份識別 | 🔥 高 | Phase 2.1 |
| 外部 API 整合框架 ([設計文檔](./docs/B2B_API_INTEGRATION_DESIGN.md)) | 🔥 高 | Phase 2.1 |
| 資料查詢 API | 🔥 高 | Phase 2.2 |
| 操作執行 API | 🔥 高 | Phase 2.2 |
| **分析與報表** | | |
| 使用量統計 | 🟡 中 | Phase 2.3 |
| 熱門問題排行 | 🟡 中 | Phase 2.3 |
| **進階功能** | | |
| 多語言支援 | 🟢 低 | Phase 3 |
| 通知系統 | 🟢 低 | Phase 3 |

## 🐛 故障排除

詳見 [QUICKSTART.md](./QUICKSTART.md) 的故障排除章節。

常見問題：
- **macOS 檔案權限問題**: 使用 `xattr -c` 清除擴展屬性
- **Docker 建置未更新**: 使用 `docker-compose up -d --build`
- **前端路由 404**: 檢查 nginx.conf 的 `try_files` 配置
- **Migration 未執行**: 檢查 `schema_migrations` 表
- **回測失敗**: 確認 OPENAI_API_KEY 已設定

## 📝 License

MIT

---

**維護者**: Claude Code
**專案建立**: 2024
**最後更新**: 2025-10-22
**當前版本**: Phase 1 完成 + Phase 3 性能優化 + 文檔重組

**最新更新** (2025-10-22):
- 📊 **Database Schema + ERD** - 完整資料庫架構文檔，16 個表 + Mermaid 關係圖 ⭐ NEW
- 📝 **文檔審計報告** - 全面盤查 130+ 文檔，建立更新優先級矩陣 ⭐ NEW
- 🔄 **術語統一** - 「重新分類」→「意圖分類」（前端 12 處更新） ⭐ NEW
- ⚙️ **環境變數支援** - 意圖分類器模型可通過 ENV 配置 ⭐ NEW
- 📘 **README 更新** - 修正 port、補充緩存和流式聊天說明 ⭐ NEW

**Phase 3 功能** (2025-10-21):
- ⚡ **三層緩存系統** - Redis 快取（問題/向量/結果），節省 70-90% API 成本
- 🌊 **流式聊天 API** - Server-Sent Events (SSE)，即時反饋用戶體驗
- 🔧 **條件式優化** - 智能路由策略，依信心度選擇處理路徑
- 📋 **SOP 系統整合** - 業者 SOP 模板，支援金流模式和業種類型動態調整

**近期功能** (2025-10-12):
- 📥 **知識匯入系統** - 批量匯入 Excel/JSON/TXT，雙層去重（文字+語意）
- 🎯 **Business Scope 重構** - 基於 user_role 動態決定 B2B/B2C 場景
- 🧪 **測試情境管理** - 自動轉換 + 智能重試機制
- 📊 **審核中心** - 統一介面審核 4 類候選項目

**下一階段**: Phase 2 (外部 API 整合 + 認證系統) 規劃中
