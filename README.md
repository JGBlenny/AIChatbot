# 🤖 AIChatbot - AI 客服知識庫系統

完整的 AI 客服知識庫管理系統，包含 LINE 對話分析、向量生成、知識管理後台，支援 RAG 檢索整合。

## ✨ 主要功能

- 📱 **LINE 對話分析**: 自動處理 LINE 對話記錄，使用 OpenAI API 提取客服 Q&A
- 🔍 **向量化知識庫**: 使用 PostgreSQL + pgvector 儲存和檢索向量資料
- 📝 **知識管理後台**: Web 介面管理知識，支援 Markdown 編輯與即時預覽
- 🔄 **自動向量更新**: 編輯知識時自動重新生成並更新向量
- ⚡ **Embedding API**: 統一的向量生成服務，支援 Redis 快取（節省 70-90% API 成本）
- 🎯 **RAG 就緒**: 向量資料可直接用於 RAG 檢索系統

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
├── database/                # 資料庫初始化
│   └── init/
│       ├── 01-enable-pgvector.sql
│       └── 02-create-knowledge-base.sql
│
├── scripts/                 # 資料處理腳本
│   └── process_line_chats.py  # LINE 對話分析
│
├── data/                    # 資料目錄
│   ├── [LINE]*.txt          # LINE 對話原始檔
│   └── *.xlsx               # 處理結果
│
├── docs/                    # 文件
│   └── architecture/
│       └── SYSTEM_ARCHITECTURE.md  # 系統架構詳細文件
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

## 📊 專案狀態

| 功能 | 狀態 |
|------|------|
| LINE 對話分析 | ✅ 完成 |
| Embedding API | ✅ 完成 |
| PostgreSQL + pgvector | ✅ 完成 |
| 知識管理後台 (前端) | ✅ 完成 |
| 知識管理 API (後端) | ✅ 完成 |
| Docker 部署 | ✅ 完成 |
| RAG 查詢系統 | 🔜 規劃中 |
| 監控儀表板 | 🔜 規劃中 |

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
**最後更新**: 2025-10-09
