# 🤖 AIChatbot - AI 客服知識庫系統

完整的 AI 客服知識庫管理系統，包含 LINE 對話分析、向量生成、知識管理後台，支援 RAG 檢索整合。

## ✨ 主要功能

- 📱 **LINE 對話分析**: 自動處理 LINE 對話記錄，使用 OpenAI API 提取客服 Q&A
- 🔍 **向量化知識庫**: 使用 PostgreSQL + pgvector 儲存和檢索向量資料
- 📝 **知識管理後台**: Web 介面管理知識，支援 Markdown 編輯與即時預覽
- 🔄 **自動向量更新**: 編輯知識時自動重新生成並更新向量
- ⚡ **Embedding API**: 統一的向量生成服務，支援 Redis 快取（節省 70-90% API 成本）
- 🤖 **RAG Orchestrator** (Phase 2 + Phase 3): 智能問答系統
  - 🎯 意圖分類 (11 種意圖類型)
  - 🔍 向量相似度搜尋
  - 📊 信心度評估
  - 📝 未釐清問題記錄
  - ✨ **LLM 答案優化** (Phase 3) - 使用 GPT-4o-mini 優化答案品質

## 🏗️ 系統架構

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ 知識管理後台 Web │────▶│ 知識管理 API     │────▶│ PostgreSQL      │
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
```

## 📦 服務列表

| 服務 | 技術 | Port | 功能 |
|------|------|------|------|
| **知識管理前端** | Vue.js 3 | 8080 | Web UI、Markdown 編輯器、知識管理 |
| **知識管理 API** | FastAPI | 8000 | CRUD API、自動向量更新 |
| **Embedding API** | FastAPI | 5001 | 統一向量生成、Redis 快取 |
| **RAG Orchestrator** ⭐ | FastAPI | 8100 | 智能問答、意圖分類、信心度評估 |
| **PostgreSQL** | pgvector/pgvector | 5432 | 資料庫、向量儲存 |
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

- 🌐 **知識庫管理後台**: http://localhost:8080
- 📚 **知識管理 API 文件**: http://localhost:8000/docs
- 🔤 **Embedding API 文件**: http://localhost:5001/docs
- 🤖 **RAG Orchestrator API 文件**: http://localhost:8100/docs ⭐
- 🗄️ **pgAdmin**: http://localhost:5050 (帳號: `admin@aichatbot.com` / 密碼: `admin`)

### 4. (首次使用) 處理 LINE 對話記錄

```bash
# 確保你有 LINE 對話 txt 檔案在 data/ 目錄
ls data/[LINE]*.txt

# 執行對話分析腳本
OPENAI_API_KEY="your-key" python3 scripts/process_line_chats.py

# 結果會儲存在 data/客服QA整理_測試結果.xlsx
```

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
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── frontend/            # 前端 Web UI
│       ├── src/
│       │   ├── App.vue      # 主應用 (Vue.js + Markdown 編輯器)
│       │   └── main.js
│       ├── package.json
│       └── Dockerfile
│
├── rag-orchestrator/        # RAG 協調器 (Phase 2 + Phase 3) ⭐
│   ├── app.py              # FastAPI 主服務
│   ├── routers/            # API 路由
│   │   ├── chat.py         # 聊天 API
│   │   └── unclear_questions.py  # 未釐清問題 API
│   ├── services/           # 核心服務
│   │   ├── intent_classifier.py      # 意圖分類
│   │   ├── rag_engine.py             # RAG 檢索
│   │   ├── confidence_evaluator.py   # 信心度評估
│   │   ├── unclear_question_manager.py  # 未釐清問題管理
│   │   └── llm_answer_optimizer.py   # LLM 答案優化 (Phase 3) ✨
│   ├── models/             # 資料模型
│   ├── config/             # 配置檔案
│   │   └── intents.yaml    # 意圖定義
│   ├── requirements.txt
│   └── Dockerfile
│
├── database/                # 資料庫初始化
│   └── init/
│       ├── 01-enable-pgvector.sql
│       ├── 02-create-knowledge-base.sql
│       └── 03-create-rag-tables.sql  # RAG 相關表
│
├── scripts/                 # 資料處理腳本
│   └── process_line_chats.py  # LINE 對話分析
│
├── data/                    # 資料目錄
│   ├── [LINE]*.txt          # LINE 對話原始檔
│   └── *.xlsx               # 處理結果
│
├── docs/                    # 文件
│   ├── architecture/
│   │   └── SYSTEM_ARCHITECTURE.md
│   └── rag-system/
│       └── RAG_IMPLEMENTATION_PLAN.md  # RAG 實作計畫
│
├── docker-compose.yml       # Docker Compose 配置
├── .env.example             # 環境變數範例
├── QUICKSTART.md           # 快速開始指南
└── README.md               # 本檔案
```

## 🛠️ 技術棧

### 後端
- **語言**: Python 3.11
- **框架**: FastAPI 0.104+
- **AI**: OpenAI API (text-embedding-3-small, gpt-4o-mini)
- **資料庫**: PostgreSQL 16 + pgvector
- **快取**: Redis 7
- **HTTP 客戶端**: httpx, requests

### 前端
- **框架**: Vue.js 3
- **編輯器**: SimpleMDE (Markdown)
- **HTTP**: Axios
- **樣式**: 原生 CSS

### 基礎設施
- **容器化**: Docker & Docker Compose
- **資料庫管理**: pgAdmin 4
- **向量儲存**: pgvector extension

## 📚 使用文件

- 📘 **快速開始指南**: [QUICKSTART.md](./QUICKSTART.md)
- 🏛️ **系統架構文件**: [docs/architecture/SYSTEM_ARCHITECTURE.md](./docs/architecture/SYSTEM_ARCHITECTURE.md)
- 🤖 **RAG 系統實作計畫**: [docs/rag-system/RAG_IMPLEMENTATION_PLAN.md](./docs/rag-system/RAG_IMPLEMENTATION_PLAN.md)
- 🎯 **RAG Orchestrator 使用說明**: [rag-orchestrator/README.md](./rag-orchestrator/README.md)
- 🔧 **pgvector 設定說明**: [PGVECTOR_SETUP.md](./PGVECTOR_SETUP.md)
- 📝 **知識管理系統說明**: [knowledge-admin/README.md](./knowledge-admin/README.md)

## 🔧 常用指令

```bash
# 停止所有服務
docker-compose stop

# 停止並移除容器
docker-compose down

# 重新建置並啟動
docker-compose up -d --build

# 查看特定服務日誌
docker-compose logs -f knowledge-admin-api

# 連線到 PostgreSQL
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin
```

## 🔍 API 使用範例

### 1. 生成向量

```bash
curl -X POST http://localhost:5001/api/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"text": "如何申請退租？"}'
```

### 2. 新增知識

```bash
curl -X POST http://localhost:8000/api/knowledge \
  -H "Content-Type: application/json" \
  -d '{
    "title": "退租流程",
    "category": "合約問題",
    "audience": "租客",
    "content": "# 退租流程\n\n1. 提前30天通知...",
    "keywords": ["退租", "合約"],
    "question_summary": "如何申請退租"
  }'
```

### 3. 向量相似度搜尋

```sql
-- 在 PostgreSQL 中執行
SELECT
    title,
    category,
    1 - (embedding <=> '[0.1, 0.2, ...]') AS similarity
FROM knowledge_base
ORDER BY embedding <=> '[0.1, 0.2, ...]'
LIMIT 5;
```

### 4. RAG 智能問答（Phase 2 + Phase 3 LLM 優化）⭐

```bash
# 發送問題到 RAG Orchestrator
curl -X POST http://localhost:8100/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "退租要怎麼辦理？",
    "user_id": "user123"
  }'

# 回應範例（含 LLM 優化的自然答案）
{
  "question": "退租要怎麼辦理？",
  "answer": "退租的流程如下：\n\n### 退租步驟\n\n1. **提前通知**：在預定的退租日期前30天，請以書面方式通知房東。\n2. **繳清費用**：確保所有的租金及水電費已經繳清。\n3. **房屋檢查**：與房東約定一個時間，進行房屋的檢查。\n4. **押金退還**：如果房屋狀況良好，房東應在7個工作天內退還押金。\n\n如果有其他問題，隨時可以詢問！",
  "confidence_score": 0.53,
  "confidence_level": "medium",
  "intent": {
    "intent_type": "knowledge",
    "intent_name": "退租流程",
    "keywords": ["退租", "辦理"]
  },
  "retrieved_docs": [...],
  "processing_time_ms": 7725,
  "requires_human": true,
  "unclear_question_id": 3
}
```

**Phase 3 LLM 優化特色**:
- ✨ 使用 GPT-4o-mini 將知識庫內容優化成自然對話
- 🎯 自動適應信心度等級（高/中信心度自動優化）
- 💰 Token 追蹤與成本控制（max 800 tokens/request）
- 🔄 錯誤自動降級（API 失敗時使用原始答案）

### 5. 查詢未釐清問題

```bash
# 取得待處理的未釐清問題
curl -X GET "http://localhost:8100/api/v1/unclear-questions?status=pending&limit=20"

# 更新問題狀態
curl -X PUT http://localhost:8100/api/v1/unclear-questions/1 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "resolved",
    "resolution_note": "已新增相關知識"
  }'

# 取得統計資訊
curl -X GET http://localhost:8100/api/v1/unclear-questions-stats
```

## 📊 專案狀態

| 功能 | 狀態 |
|------|------|
| LINE 對話分析 | ✅ 完成 |
| Embedding API | ✅ 完成 |
| PostgreSQL + pgvector | ✅ 完成 |
| 知識管理後台 (前端) | ✅ 完成 |
| 知識管理 API (後端) | ✅ 完成 |
| Docker 部署 | ✅ 完成 |
| **RAG Orchestrator (Phase 2)** | ✅ **完成** |
| └─ 意圖分類 | ✅ 完成 |
| └─ RAG 檢索引擎 | ✅ 完成 |
| └─ 信心度評估 | ✅ 完成 |
| └─ 未釐清問題記錄 | ✅ 完成 |
| **LLM 答案優化 (Phase 3)** | ✅ **完成** |
| └─ GPT-4o-mini 答案優化 | ✅ 完成 |
| └─ Token 追蹤與成本控制 | ✅ 完成 |
| └─ 自動錯誤降級處理 | ✅ 完成 |
| 外部 API 整合 (Phase 4) | 📋 已規劃 |
| 監控儀表板 (Phase 5) | 📋 已規劃 |

## 🤝 開發

### 本地開發 - 後端

```bash
cd knowledge-admin/backend
pip install -r requirements.txt
export DB_HOST=localhost
export EMBEDDING_API_URL=http://localhost:5001/api/v1/embeddings
python app.py
```

### 本地開發 - 前端

```bash
cd knowledge-admin/frontend
npm install
npm run dev
```

## 🐛 故障排除

詳見 [QUICKSTART.md](./QUICKSTART.md) 的故障排除章節。

## 📝 License

MIT

---

**維護者**: Claude Code
**最後更新**: 2025-10-10 (Phase 3 LLM 優化完成)
