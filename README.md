# AIChatbot - 多業者 RAG AI 客服知識庫系統

基於 RAG（Retrieval-Augmented Generation）的多業者 SaaS AI 客服知識庫系統，專注於租屋管理領域。整合向量語義檢索、SOP 流程編排、表單填寫、知識完善迴圈與多業者隔離，所有 AI 生成內容皆需人工審核。

> 完整文檔請見 [docs/INDEX.md](./docs/INDEX.md)（任務導向索引）與 [docs/README.md](./docs/README.md)（技術演進總覽）。

---

## 核心功能

### RAG 智能檢索與回答
- **向量語義搜尋**：PostgreSQL + pgvector 進行相似度檢索
- **分離式分數 pipeline**：vector → keyword → keyword_boost → reranker → finalize，各 stage 寫入獨立欄位（詳見 [retriever-pipeline](./docs/architecture/retriever-pipeline.md)）
- **語義重排序（Reranker）**：本地 sentence-transformers / bge-reranker 二階段重排（可選）
- **信心度評估**：高/中/低信心度判斷，低信心度標記為「未釐清問題」
- **LLM 答案優化**：以業者參數動態合成、優化答案

### 知識管理
- **多元知識來源**：通用知識庫（knowledge_base）、SOP 知識（vendor_sop_*）、測試場景（test_scenarios）
- **知識主題分類多值化**：知識可同時掛多個分類（`categories[]`），並支援兩層分類（`category_config.parent_value`）
- **目標用戶隔離**：租客、房東、物業經理、系統管理員等角色隔離
- **業態類型過濾**：依不同業態（租屋、商辦等）過濾知識
- **知識匯入/匯出**：Excel/JSON/TXT 批量匯入，雙層去重（文字精確 + 向量語意）

### SOP 編排與表單
- **SOP 智能編排**：多輪對話流程、語義觸發、Reranker 重排
- **動態表單填寫**：表單生成、驗證、參數解析、表單串接（form-chaining）

### 知識完善迴圈（Knowledge Completion Loop）
- 回測執行 → 失敗分析 → AI 分類（SOP/表單/系統配置）→ 缺口聚類 → 知識生成 → 人工審核 → 迭代驗證
- 全程記錄 OpenAI token 與成本，所有生成知識進入審核佇列

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
| RAG Orchestrator | aichatbot-rag-orchestrator | FastAPI | 8100 | 智能問答、SOP 編排、表單、知識完善迴圈 |
| 知識管理 API | aichatbot-knowledge-admin-api | FastAPI | 8000 | 知識/測試場景/業者 CRUD、自動向量更新 |
| 知識管理前端 | aichatbot-knowledge-admin-web | Vue.js 3 + Nginx | 8087 | 審核中心、知識/業者/分類管理 |
| Embedding API | aichatbot-embedding-api | FastAPI | 5001 | 統一向量生成、Redis 快取 |
| Semantic Model | aichatbot-semantic-model | FastAPI | 8002 | 語義重排序模型服務 |
| PostgreSQL | aichatbot-postgres | pgvector/pg16 | 5432 | 資料庫、向量儲存 |
| Redis | aichatbot-redis | Redis 7 | 6381 | Embedding + RAG 快取 |

> 前端正式環境 Port 由 `.env` 的 `WEB_PORT` 控制（本地預設 8087，線上預設 80）。

詳見 [系統架構文件](./docs/architecture/SYSTEM_ARCHITECTURE.md) 與 [完整對話架構](./docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md)。

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
├── rag-orchestrator/     # 主服務：RAG 編排、SOP、表單、知識完善迴圈
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
| 系統架構 | [docs/architecture/SYSTEM_ARCHITECTURE.md](./docs/architecture/SYSTEM_ARCHITECTURE.md) |
| 資料庫 Schema | [docs/architecture/DATABASE_SCHEMA.md](./docs/architecture/DATABASE_SCHEMA.md) |
| API 文件索引 | [docs/api/README.md](./docs/api/README.md) |
| 功能文件索引 | [docs/features/README.md](./docs/features/README.md) |
| SOP 系統 | [docs/features/sop/README.md](./docs/features/sop/README.md) |
| 認證系統 | [docs/features/AUTH_SYSTEM_README.md](./docs/features/AUTH_SYSTEM_README.md) |
| 回測入門 | [docs/backtest/GETTING_STARTED.md](./docs/backtest/GETTING_STARTED.md) |
| 變更日誌 | [CHANGELOG.md](./CHANGELOG.md) |

---

## License

MIT
