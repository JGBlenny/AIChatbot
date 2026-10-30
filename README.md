# AIChatbot - 多業者 RAG AI 客服知識庫系統

> 🎯 **本檔寫現況，不是設計依據。目標：本系統是對話服務，不是 MCP 系統；呼叫端走專用對話 API，`/mcp` 不是最終入口；JGB 工具要搬出本系統，由 JGB 維護。** 分工與完整架構見 `docs/architecture/TARGET_ARCHITECTURE.md`。

多業者 SaaS AI 客服系統，專注於租屋管理領域。

**對話核心是 `AgentRuntime`**（`rag-orchestrator/services/agent/runtime.py`）——模型持有回合、
自己決定呼叫哪支工具，輸出逐句經 Verifier 驗引用。**`/mcp` 是它的門面之一**，
也是目前唯一掛著的對外入口。知識走兩條路：git canon 正本每回合自動注入，
以及模型自己呼叫 `kb.search`／`kb.get`。

⛔ **先讀 [`docs/architecture/SYSTEM_ARCHITECTURE.md`](./docs/architecture/SYSTEM_ARCHITECTURE.md)**
（現況全景）與 [`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`](./docs/architecture/AGENTIC_MCP_ARCHITECTURE.md)
（§2b 一回合完整流程、§4b 為什麼被轉人）。

> 完整文檔請見 [docs/INDEX.md](./docs/INDEX.md)（任務導向索引）與 [docs/README.md](./docs/README.md)（技術演進總覽）。

---

## 核心功能

### 對話回合（agentic-MCP，唯一活線）
- **`AgentRuntime.run_turn`**：程式段 → 九段脈絡注入 → 模型工具迴圈＋Verifier → 四道出口閘（順序即契約）
- **工具**：`jgb2.query.*` 六域 15 個 face（帳單／合約／修繕／電表／帳號／物件）、`kb.search`／`kb.get`、寫入類與確認卡
- **受眾只有兩種**：`prospect` 與 `property_manager`；⛔ `tenant` 在新線不存在（無 `canon/tenant.md`）
- **引用驗證**：逐句驗，擋不住就走轉人固定句

### 檢索
- **向量語義搜尋**：PostgreSQL + pgvector
- **分離式分數 pipeline**：vector → keyword → keyword_boost → reranker → finalize（詳見 [retriever-pipeline](./docs/architecture/retriever-pipeline.md)）
- **語義重排序（Reranker）**：本地 bge-reranker 二階段重排。⚠️ 它會靜默永久停用，容器／稽核／健檢 API 三者都看不出來

### 知識管理
- **多元知識來源**：通用知識庫（knowledge_base）、SOP 知識（vendor_sop_*）、測試場景（test_scenarios）
- **知識主題分類多值化**：知識可同時掛多個分類（`categories[]`），並支援兩層分類（`category_config.parent_value`）
- **目標用戶隔離**：租客、房東、物業經理、系統管理員等角色隔離
- **業態類型過濾**：依不同業態（租屋、商辦等）過濾知識
- **知識匯入/匯出**：Excel/JSON/TXT 批量匯入，雙層去重（文字精確 + 向量語意）

### 後台維護面（⛔ 對話路徑不讀）
- **SOP**（`vendor_sop_items`）：後台 CRUD 可用、存檔仍重算 embedding，但**改 SOP 不影響機器人回答**——編排器與觸發器已於 2026-09-11 刪除
- **表單**：後台 CRUD 可用；對話填單引擎已退役，`form_sessions` 表被新線借用來存多輪狀態
- **知識完善迴圈**：只剩查詢與審核，⛔ 沒有端點可以啟動新迴圈；想跑改善輪走 `.claude/skills/retrieval-improvement-loop/`（打 `/mcp`）

### 多業者 SaaS 與審核
- 資料庫層級 `vendor_id` 隔離、業者動態配置（vendor_configs）
- 審核中心集中管理未釐清問題、待審核知識、測試場景

### 認證與安全
- **管理後台認證**：JWT + bcrypt，保護所有管理 API（詳見 [認證系統](./docs/features/AUTH_SYSTEM_README.md)）
- **服務對服務 API Key 認證**：`api_keys` 表（只存 SHA-256 雜湊），由環境變數 `RAG_API_AUTH_ENFORCE` 控制開關，預設關閉以利安全上線

---

## 系統架構

| 服務 | 容器名 | 技術 | Port（本地） | 功能 |
|------|--------|------|------|------|
| RAG Orchestrator | aichatbot-rag-orchestrator | FastAPI | 8100 | `/mcp` 門面＋`AgentRuntime`（對話核心）、檢索、後台 CRUD |
| 知識管理 API | aichatbot-knowledge-admin-api | FastAPI | 8000 | 知識/測試場景/業者 CRUD、自動向量更新 |
| 知識管理前端 | aichatbot-knowledge-admin-web | Vue.js 3 + Nginx | 8087 | 審核中心、知識/業者/分類管理 |
| Embedding API | aichatbot-embedding-api | FastAPI | 5001 | 統一向量生成、Redis 快取 |
| Semantic Model | aichatbot-semantic-model | FastAPI | 8002 | 語義重排序模型服務 |
| PostgreSQL | aichatbot-postgres | pgvector/pg16 | 5432 | 資料庫、向量儲存 |
| Redis | aichatbot-redis | Redis 7 | 6381 | Embedding + RAG 快取 |

> 前端正式環境 Port 由 `.env` 的 `WEB_PORT` 控制（本地預設 8087，線上預設 80）。

詳見 [系統架構文件](./docs/architecture/SYSTEM_ARCHITECTURE.md) 與 [Agentic-MCP 對話架構](./docs/architecture/AGENTIC_MCP_ARCHITECTURE.md)。

---

## 快速開始

詳細步驟請見 [快速開始指南](./docs/guides/getting-started/QUICKSTART.md) 與 [部署指南](./docs/deployment/DEPLOY_GUIDE.md)。

### 前置需求
- Docker & Docker Compose
- OpenAI API Key

### 1. 設定環境變數
```bash
cp .env.example .env
# 編輯 .env，至少填入 OPENAI_API_KEY
```

### 2. 啟動服務
```bash
# 生產 / 統一配置
docker-compose -f docker-compose.prod.yml up -d --build

# 開發（熱重載）
docker-compose -f docker-compose.dev.yml up -d --build

# 查看狀態與日誌
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f rag-orchestrator
```

### 3. 存取服務
- 管理後台（審核中心 / 知識 / 業者 / 分類管理）：http://localhost:8087
- RAG Orchestrator API 文件：http://localhost:8100/docs
- 知識管理 API 文件：http://localhost:8000/docs
- Embedding API 文件：http://localhost:5001/docs

---

## 技術棧

- **後端**：Python 3 / FastAPI / Uvicorn / Pydantic
- **資料庫**：PostgreSQL 16 + pgvector、Redis 7
- **AI/ML**：OpenAI（gpt-4o / gpt-4o-mini / gpt-3.5-turbo、text-embedding-3-small）、sentence-transformers（本地重排）
- **前端**：Vue.js 3 + Vite + Nginx
- **基礎設施**：Docker & Docker Compose、AWS S3（圖片/視頻）

主要環境變數說明請見 `.env.example` 與 [.kiro/steering/tech.md](./.kiro/steering/tech.md)。

---

## 專案結構

```
AIChatbot/
├── rag-orchestrator/     # 主服務：AgentRuntime 對話核心、/mcp 門面、檢索、後台 CRUD
│   ├── routers/          # API 路由層
│   ├── services/         # 業務邏輯層（含 knowledge_completion_loop/）
│   ├── config/           # 配置（intents.yaml、business_types 等）
│   └── tests/            # 測試
├── knowledge-admin/      # 管理後台（backend FastAPI + frontend Vue.js）
├── embedding-service/    # 向量嵌入服務
├── semantic_model/       # 語義重排序模型服務
├── database/             # init / migrations / seeds
├── scripts/              # 全域腳本（回測等）
├── docs/                 # 文檔（見 docs/INDEX.md）
├── tests/                # 跨服務測試
├── docker-compose.prod.yml
├── docker-compose.dev.yml
└── .env.example
```

更完整的結構與命名規範見 [.kiro/steering/structure.md](./.kiro/steering/structure.md)。

---

## 文件導覽

| 主題 | 文件 |
|------|------|
| 文檔索引（任務導向） | [docs/INDEX.md](./docs/INDEX.md) |
| 技術演進總覽 | [docs/README.md](./docs/README.md) |
| 快速開始 | [docs/guides/getting-started/QUICKSTART.md](./docs/guides/getting-started/QUICKSTART.md) |
| 部署指南 | [docs/deployment/DEPLOY_GUIDE.md](./docs/deployment/DEPLOY_GUIDE.md) |
| **系統架構（現況全景）** ⭐ | [docs/architecture/SYSTEM_ARCHITECTURE.md](./docs/architecture/SYSTEM_ARCHITECTURE.md) |
| **對話線內部＋為什麼被轉人** ⭐ | [docs/architecture/AGENTIC_MCP_ARCHITECTURE.md](./docs/architecture/AGENTIC_MCP_ARCHITECTURE.md) |
| `/mcp` 串接契約 | [docs/api/mcp-facade.md](./docs/api/mcp-facade.md) |
| 資料庫 Schema | [docs/architecture/DATABASE_SCHEMA.md](./docs/architecture/DATABASE_SCHEMA.md) |
| API 文件索引 | [docs/api/README.md](./docs/api/README.md) |
| 功能文件索引 | [docs/features/README.md](./docs/features/README.md) |
| SOP 系統 | [docs/features/sop/README.md](./docs/features/sop/README.md) |
| 認證系統 | [docs/features/AUTH_SYSTEM_README.md](./docs/features/AUTH_SYSTEM_README.md) |
| 變更日誌 | [CHANGELOG.md](./CHANGELOG.md) |

---

## License

MIT
