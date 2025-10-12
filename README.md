# 🤖 AIChatbot - AI 客服知識庫系統

完整的 SaaS 多租戶 AI 客服知識庫管理系統，包含智能問答、測試情境管理、知識審核、回測框架，支援 RAG 檢索整合與多業者隔離。

## ✨ 核心功能

### 🤖 RAG Orchestrator（智能問答系統）
- 🎯 **多 Intent 分類** - 支援一個問題同時匹配多個意圖（主要 + 次要）
- 🔍 **混合檢索策略** - Intent 過濾 + 向量相似度，差異化加成（1.5x / 1.2x）
- 📊 **三級信心度評估** - 高/中/低信心度判斷
- ✨ **LLM 答案優化** - 使用 GPT-4o-mini 優化答案品質
- 🧠 **意圖建議引擎** - OpenAI 自動分析未知問題並建議新意圖

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
| **知識管理前端** | Vue.js 3 + Vue Router | 8080 | 審核中心、知識管理、業者管理、測試情境管理 |
| **知識管理 API** | FastAPI | 8000 | Knowledge CRUD、測試情境 CRUD、自動向量更新 |
| **Embedding API** | FastAPI | 5001 | 統一向量生成、Redis 快取 |
| **RAG Orchestrator** | FastAPI | 8100 | 智能問答、意圖分類、多業者支援、知識生成 |
| **PostgreSQL** | pgvector/pgvector | 5432 | 資料庫、向量儲存、業者資料、測試題庫 |
| **Redis** | Redis 7 | 6379 | Embedding 快取 |
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

- 🌐 **審核中心**: http://localhost:8080/review-center
  - 測試情境審核
  - 用戶問題審核
  - 意圖建議審核
  - AI 知識候選審核
- 📚 **知識庫管理**: http://localhost:8080/knowledge
- 🏢 **業者管理**: http://localhost:8080/vendors
- 🧪 **Chat 測試**: http://localhost:8080/chat-test
- 📊 **回測執行**: http://localhost:8080/backtest
- 📘 **API 文件**:
  - 知識管理 API: http://localhost:8000/docs
  - Embedding API: http://localhost:5001/docs
  - RAG Orchestrator: http://localhost:8100/docs
- 🗄️ **pgAdmin**: http://localhost:5050 (帳號: `admin@aichatbot.com` / 密碼: `admin`)

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
│   │   ├── chat.py                    # 聊天 API (多業者)
│   │   ├── vendors.py                 # 業者管理
│   │   ├── intents.py                 # 意圖管理
│   │   ├── suggested_intents.py       # 意圖建議
│   │   ├── knowledge.py               # 知識分類
│   │   ├── knowledge_generation.py    # AI 知識生成 ⭐
│   │   └── business_scope.py          # 業務範圍
│   ├── services/           # 核心服務
│   │   ├── intent_classifier.py           # 意圖分類
│   │   ├── rag_engine.py                  # RAG 檢索
│   │   ├── llm_answer_optimizer.py        # LLM 答案優化 + 參數注入
│   │   ├── knowledge_generator.py         # AI 知識生成器 ⭐
│   │   ├── intent_manager.py              # 意圖管理器 ⭐
│   │   ├── unclear_question_manager.py    # 用戶問題管理 ⭐
│   │   ├── vendor_knowledge_retriever.py  # 多業者知識檢索
│   │   └── vendor_parameter_resolver.py   # 業者參數解析
│   ├── requirements.txt
│   └── Dockerfile
│
├── database/                # 資料庫
│   ├── init/               # 初始化腳本
│   │   ├── 01-enable-pgvector.sql
│   │   ├── 02-create-knowledge-base.sql
│   │   ├── 03-create-rag-tables.sql
│   │   ├── 06-vendors-and-configs.sql
│   │   ├── 07-extend-knowledge-base.sql
│   │   ├── 08-remove-templates-use-generic-values.sql
│   │   └── 09-create-test-scenarios.sql    # 測試題庫表 ⭐
│   └── migrations/         # 資料庫變更 ⭐
│       ├── README.md       # Migration 說明文檔
│       ├── 09-knowledge-multi-intent.sql
│       ├── 11-add-source-tracking-to-knowledge-candidates.sql
│       ├── 12-remove-suggested-knowledge.sql
│       ├── 13-add-auto-scenario-creation-trigger.sql      # 自動創建測試情境 ⭐
│       ├── 14-add-rejected-scenario-retry-logic.sql       # 拒絕重試機制 ⭐
│       ├── 15-update-candidates-view-for-rejected-scenarios.sql
│       ├── 16-fix-candidates-view-filter.sql
│       ├── 17-fix-candidates-view-check-all-scenarios.sql # 完整情境檢查 ⭐
│       └── 18-24-*.sql    # 歷史 migrations
│
├── scripts/                 # 工具腳本
│   └── knowledge_extraction/
│       └── backtest_framework.py    # 回測框架 ⭐
│
├── docs/                   # 文件（已重組） ⭐
│   ├── guides/             # 使用指南 (9 個)
│   │   ├── BACKTEST_OPTIMIZATION_GUIDE.md
│   │   ├── DEVELOPMENT_WORKFLOW.md
│   │   ├── DOCKER_COMPOSE_GUIDE.md
│   │   ├── KNOWLEDGE_EXTRACTION_GUIDE.md
│   │   ├── PGVECTOR_SETUP.md
│   │   └── TEST_SCENARIOS_MIGRATION_GUIDE.md
│   ├── features/           # 功能文檔 (6 個)
│   │   ├── INTENT_MANAGEMENT_README.md
│   │   ├── REJECTED_SCENARIO_RETRY_IMPLEMENTATION.md ⭐
│   │   └── TEST_SCENARIO_STATUS_MANAGEMENT.md ⭐
│   ├── api/               # API 參考 (2 個)
│   ├── backtest/          # 回測文檔 (4 個)
│   ├── planning/          # 規劃文檔 (2 個)
│   ├── examples/          # 測試數據
│   │   ├── test_data/    # 測試情境 Excel
│   │   └── extracted_data/
│   └── archive/           # 歷史文檔
│       ├── completion_reports/    (9 個)
│       ├── evaluation_reports/    (8 個)
│       ├── fix_reports/           (1 個)
│       └── deprecated_guides/     (6 個)
│
├── tests/                  # 測試 ⭐
│   └── integration/       # 整合測試
│       ├── test_multi_intent.py
│       ├── test_scoring_quality.py
│       └── test_classifier_direct.py
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

### 🚀 快速開始
- 📘 **快速開始指南**: [QUICKSTART.md](./QUICKSTART.md)
- 📖 **開發工作流程**: [docs/guides/DEVELOPMENT_WORKFLOW.md](./docs/guides/DEVELOPMENT_WORKFLOW.md)

### ⭐ 最新功能文檔
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
# 租客詢問問題（自動意圖分類 + RAG 檢索 + LLM 優化）
curl -X POST http://localhost:8100/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "退租要怎麼辦理？",
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
| **系統清理與重構** ⭐ | | |
| Business Scope 架構重構 | ✅ | 2025-10-12 |
| 文檔重組（60+ 文件） | ✅ | 2025-10-12 |
| Migration 編號修復 | ✅ | 2025-10-12 |
| 資料庫重複數據清理 | ✅ | 2025-10-12 |
| 前端開發模式（熱重載）| ✅ | 2025-10-12 |

### ⏳ 待開發功能（Phase 2）

| 功能模組 | 優先級 | 預計時程 |
|---------|-------|---------|
| **B2B 進階功能** | | |
| 租客身份識別 | 🔥 高 | Phase 2.1 |
| 外部 API 整合框架 | 🔥 高 | Phase 2.1 |
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
**最後更新**: 2025-10-12
**當前版本**: Phase 1 完成 + 測試情境管理系統 + Business Scope 重構

**最新功能** (2025-10-12):
- 🎯 **Business Scope 重構** - 基於 user_role 動態決定 B2B/B2C 場景
- 🔄 **雙場景支援** - 每個業者可同時服務客戶和員工
- 💻 **前端開發模式** - 支援熱重載，提升開發效率
- 🧪 **測試情境管理** - 自動轉換 + 智能重試機制
- 📊 **審核中心** - 統一介面審核 4 類候選項目
- 🤖 **AI 知識生成** - 從測試情境自動生成知識
- 📁 **系統清理** - 60+ 文件整理完成

**下一階段**: Phase 2 (外部 API 整合 + 認證系統) 規劃中
