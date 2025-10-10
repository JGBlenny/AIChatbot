# 🤖 AIChatbot - AI 客服知識庫系統

完整的 SaaS 多租戶 AI 客服知識庫管理系統，包含 LINE 對話分析、向量生成、知識管理後台，支援 RAG 檢索整合與多業者隔離。

## ✨ 主要功能

### 核心功能
- 📱 **LINE 對話分析**: 自動處理 LINE 對話記錄，使用 OpenAI API 提取客服 Q&A
- 🔍 **向量化知識庫**: 使用 PostgreSQL + pgvector 儲存和檢索向量資料
- 📝 **知識管理後台**: Web 介面管理知識，支援 Markdown 編輯與即時預覽
- 🔄 **自動向量更新**: 編輯知識時自動重新生成並更新向量
- ⚡ **Embedding API**: 統一的向量生成服務，支援 Redis 快取（節省 70-90% API 成本）

### 🤖 RAG Orchestrator（智能問答系統）
- 🎯 **多 Intent 分類** ⭐ - 支援一個問題同時匹配多個意圖（主要 + 次要）
- 🔍 **混合檢索策略** - Intent 過濾 + 向量相似度，差異化加成（1.5x / 1.2x）
- 📊 **信心度評估** - 三級信心度判斷（高/中/低）
- 📝 **未釐清問題記錄** - 自動記錄低信心度問題
- ✨ **LLM 答案優化** - 使用 GPT-4o-mini 優化答案品質
- 🧠 **意圖建議引擎** - OpenAI 自動分析未知問題並建議新意圖

### 🏢 Phase 1: 多業者支援（Multi-Vendor SaaS）⭐
- 🏪 **業者管理系統** - 完整的業者 CRUD、啟用/停用控制
- ⚙️ **業者參數配置** - 分類管理（帳務、合約、服務、聯絡）
- 🎨 **LLM 智能參數注入** - 不使用模板變數，AI 自動根據業者參數調整答案
- 🔐 **多租戶知識隔離** - 三層知識範圍（global, vendor, customized）
- 💬 **B2C Chat API** - 租客對業者的智能客服對話
- 🖥️ **管理界面** - 業者管理、參數配置、Chat 測試頁面

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

                        ┌──────────────────┐
                        │ RAG Orchestrator │◀────── 多業者 Chat API
                        │  (FastAPI)       │
                        │  Port: 8100      │
                        └──────────────────┘
```

## 📦 服務列表

| 服務 | 技術 | Port | 功能 |
|------|------|------|------|
| **知識管理前端** | Vue.js 3 | 8080 | Web UI、Markdown 編輯器、知識管理、業者管理 |
| **知識管理 API** | FastAPI | 8000 | CRUD API、自動向量更新 |
| **Embedding API** | FastAPI | 5001 | 統一向量生成、Redis 快取 |
| **RAG Orchestrator** ⭐ | FastAPI | 8100 | 智能問答、意圖分類、多業者支援 |
| **PostgreSQL** | pgvector/pgvector | 5432 | 資料庫、向量儲存、業者資料 |
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
  - 知識庫管理
  - 業者管理
  - 業者配置
  - Chat 測試
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
│       │   ├── views/
│       │   │   ├── VendorManagementView.vue    # 業者管理
│       │   │   ├── VendorConfigView.vue        # 業者配置
│       │   │   └── ChatTestView.vue            # Chat 測試
│       │   └── main.js
│       ├── package.json
│       └── Dockerfile
│
├── rag-orchestrator/        # RAG 協調器 ⭐
│   ├── app.py              # FastAPI 主服務
│   ├── routers/            # API 路由
│   │   ├── chat.py         # 聊天 API (含多業者支援)
│   │   ├── vendors.py      # 業者管理 API
│   │   ├── intents.py      # 意圖管理 API
│   │   ├── knowledge.py    # 知識分類 API
│   │   ├── suggested_intents.py    # 意圖建議 API
│   │   └── unclear_questions.py    # 未釐清問題 API
│   ├── services/           # 核心服務
│   │   ├── intent_classifier.py           # 意圖分類
│   │   ├── rag_engine.py                  # RAG 檢索
│   │   ├── confidence_evaluator.py        # 信心度評估
│   │   ├── unclear_question_manager.py    # 未釐清問題管理
│   │   ├── llm_answer_optimizer.py        # LLM 答案優化 + 參數注入
│   │   ├── suggestion_engine.py           # 意圖建議引擎
│   │   ├── vendor_knowledge_retriever.py  # 多業者知識檢索
│   │   └── vendor_parameter_resolver.py   # 業者參數解析
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
│       ├── 03-create-rag-tables.sql
│       ├── 04-create-intent-suggestion.sql
│       ├── 05-create-business-scope.sql
│       ├── 06-vendors-and-configs.sql          # 業者相關表
│       ├── 07-extend-knowledge-base.sql        # 知識庫多業者擴展
│       └── 08-remove-templates-use-generic-values.sql  # 移除模板變數
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
│   ├── rag-system/
│   │   └── RAG_IMPLEMENTATION_PLAN.md
│   ├── PHASE1_MULTI_VENDOR_IMPLEMENTATION.md  # Phase 1 文件
│   ├── API_REFERENCE_PHASE1.md                # API 參考
│   └── PHASE2_PLANNING.md                      # Phase 2 規劃
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

### 快速導覽
- 📘 **快速開始指南**: [QUICKSTART.md](./QUICKSTART.md)
- 📖 **完整文檔導覽**: [docs/README.md](./docs/README.md) ⭐

### 核心功能文檔
- 🎯 **多 Intent 分類系統**: [docs/MULTI_INTENT_CLASSIFICATION.md](./docs/MULTI_INTENT_CLASSIFICATION.md) ⭐ **NEW**
- 🏛️ **系統架構文件**: [docs/architecture/SYSTEM_ARCHITECTURE.md](./docs/architecture/SYSTEM_ARCHITECTURE.md)
- 🏢 **Phase 1 多業者實作**: [docs/PHASE1_MULTI_VENDOR_IMPLEMENTATION.md](./docs/PHASE1_MULTI_VENDOR_IMPLEMENTATION.md)
- 📋 **Phase 2 規劃**: [docs/PHASE2_PLANNING.md](./docs/PHASE2_PLANNING.md)
- 🔧 **回測優化指南**: [BACKTEST_OPTIMIZATION_GUIDE.md](./BACKTEST_OPTIMIZATION_GUIDE.md)

### 技術參考
- 🎯 **Intent 管理指南**: [docs/INTENT_MANAGEMENT_README.md](./docs/INTENT_MANAGEMENT_README.md)
- 📚 **知識分類指南**: [docs/KNOWLEDGE_CLASSIFICATION_COMPLETE.md](./docs/KNOWLEDGE_CLASSIFICATION_COMPLETE.md)
- 🧪 **知識提取指南**: [docs/KNOWLEDGE_EXTRACTION_GUIDE.md](./docs/KNOWLEDGE_EXTRACTION_GUIDE.md)
- 📡 **API 參考文檔**: [docs/API_REFERENCE_PHASE1.md](./docs/API_REFERENCE_PHASE1.md)
- 🔧 **pgvector 設定**: [PGVECTOR_SETUP.md](./PGVECTOR_SETUP.md)

## 🔧 常用指令

```bash
# 停止所有服務
docker-compose stop

# 停止並移除容器
docker-compose down

# 重新建置並啟動
docker-compose up -d --build

# 查看特定服務日誌
docker-compose logs -f rag-orchestrator

# 連線到 PostgreSQL
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin

# 重啟特定服務
docker restart aichatbot-rag-orchestrator
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

### 3. 多業者 Chat API（Phase 1）⭐

```bash
# 業者 A 的租客詢問繳費日
curl -X POST http://localhost:8100/api/v1/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "繳費日是幾號？",
    "vendor_id": 1,
    "mode": "tenant",
    "include_sources": true
  }'

# 回應範例（LLM 自動注入業者 A 的參數）
{
  "answer": "您的租金繳費日為每月 1 號。請務必在這個日期前完成繳費，以避免逾期手續費。如果在繳費日後的 5 天內仍未繳納，將會加收 200 元的逾期手續費。",
  "intent_name": "帳務查詢",
  "confidence": 0.9,
  "sources": [...],
  "vendor_id": 1,
  "mode": "tenant"
}

# 業者 B 詢問相同問題（自動得到不同答案）
curl -X POST http://localhost:8100/api/v1/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "繳費日是幾號？",
    "vendor_id": 2,
    "mode": "tenant"
  }'

# 回應：繳費日變成 5 號，逾期費變成 300 元
```

**Phase 1 LLM 智能參數注入特色**:
- ✨ 不使用 `{{模板變數}}`，直接在知識庫寫通用數值（如 "5 號"、"300 元"）
- 🎯 LLM 自動根據業者配置調整參數
- 🔄 支援多種參數類型（日期、金額、電話、地址等）
- 💡 當業者參數與通用值相同時，LLM 智能保持原值

### 4. RAG 智能問答（含 LLM 優化）

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
  "requires_human": true
}
```

### 5. 業者管理 API

```bash
# 獲取業者列表
curl http://localhost:8100/api/v1/vendors

# 獲取業者配置參數
curl http://localhost:8100/api/v1/vendors/1/configs

# 獲取業者統計
curl http://localhost:8100/api/v1/vendors/1/stats
```

### 6. 意圖建議 API

```bash
# 獲取待審核的意圖建議
curl "http://localhost:8100/api/v1/suggested-intents?status=pending"

# 批准意圖建議（自動建立新意圖）
curl -X POST http://localhost:8100/api/v1/suggested-intents/1/approve \
  -H "Content-Type: application/json" \
  -d '{
    "approved_by": "admin",
    "notes": "確認為有效意圖"
  }'
```

## 📊 專案狀態

### ✅ 已完成功能

| 功能模組 | 狀態 | 說明 |
|---------|------|------|
| **基礎設施** | | |
| LINE 對話分析 | ✅ 完成 | OpenAI 自動提取 Q&A |
| Embedding API | ✅ 完成 | Redis 快取、成本節省 70-90% |
| PostgreSQL + pgvector | ✅ 完成 | 向量儲存與搜尋 |
| 知識管理後台 | ✅ 完成 | Vue.js + Markdown 編輯器 |
| 知識管理 API | ✅ 完成 | FastAPI CRUD |
| Docker 部署 | ✅ 完成 | 完整容器化 |
| **RAG 核心** | | |
| 多 Intent 分類系統 | ✅ 完成 | 主要 + 次要意圖，回測通過率 +50% ⭐ |
| 混合檢索策略 | ✅ 完成 | 差異化加成（1.5x / 1.2x）⭐ |
| 意圖分類器 | ✅ 完成 | 11 種意圖類型 |
| RAG 檢索引擎 | ✅ 完成 | pgvector 語義搜尋 |
| 信心度評估 | ✅ 完成 | 三級評估（高/中/低） |
| 未釐清問題記錄 | ✅ 完成 | 自動記錄與管理 |
| LLM 答案優化 | ✅ 完成 | GPT-4o-mini 優化 |
| 回測框架 | ✅ 完成 | 支援多 Intent 評估、模糊匹配 ⭐ |
| **Phase A: 意圖管理** | | |
| 意圖 CRUD | ✅ 完成 | 完整管理介面 |
| 訓練語句管理 | ✅ 完成 | 新增/編輯訓練語句 |
| 意圖啟用/停用 | ✅ 完成 | 動態控制 |
| 業務範圍管理 | ✅ 完成 | 定義業務邊界 |
| **Phase B: 意圖建議** | | |
| 意圖建議引擎 | ✅ 完成 | OpenAI 自動分析 |
| 建議審核機制 | ✅ 完成 | 人工審核後建立 |
| 建議合併功能 | ✅ 完成 | 合併相似建議 |
| **Phase 1: 多業者支援** | | |
| 業者管理系統 | ✅ 完成 | CRUD、啟用/停用 |
| 業者參數配置 | ✅ 完成 | 分類管理（帳務、合約、服務、聯絡）|
| LLM 智能參數注入 | ✅ 完成 | 取代模板變數系統 |
| 多租戶知識隔離 | ✅ 完成 | 三層範圍 + 優先級 |
| B2C Chat API | ✅ 完成 | 租客對業者聊天 |
| 業者管理介面 | ✅ 完成 | Vue.js 完整 UI |

### ⏳ 待開發功能（Phase 2）

| 功能模組 | 優先級 | 說明 |
|---------|-------|------|
| **B2B 進階功能** | 🔥 高 | |
| 租客身份識別 | 🔥 高 | 從對話提取租客資訊 |
| 外部 API 整合框架 | 🔥 高 | API 配置與呼叫管理 |
| 資料查詢 API | 🔥 高 | 租約、帳務查詢 |
| 操作執行 API | 🔥 高 | 報修、預約功能 |
| 客服權限管理 | 🟡 中 | RBAC 系統 |
| **分析與報表** | 🟡 中 | |
| 使用量統計 | 🟡 中 | 業者使用分析 |
| 熱門問題排行 | 🟡 中 | 問題趨勢分析 |
| 績效儀表板 | 🟡 中 | 視覺化報表 |
| **進階功能** | 🟢 低 | |
| 多語言支援 | 🟢 低 | 英/日文介面 |
| 文件自動解析 | 🟢 低 | PDF/Word 轉知識 |
| 通知系統 | 🟢 低 | Line/Email/SMS |
| 知識版本控制 | 🟢 低 | 歷史版本管理 |

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

### 本地開發 - RAG Orchestrator

```bash
cd rag-orchestrator
pip install -r requirements.txt
export DB_HOST=localhost
export OPENAI_API_KEY=your-key
python app.py
```

## 🐛 故障排除

詳見 [QUICKSTART.md](./QUICKSTART.md) 的故障排除章節。

常見問題：
- **macOS 檔案權限問題**: 使用 `xattr -c` 清除擴展屬性
- **Docker 建置未更新**: 使用 `docker cp` 手動複製檔案
- **前端 API 連線失敗**: 檢查 nginx 代理配置
- **LLM 參數未注入**: 確認業者配置已儲存

## 📝 License

MIT

---

**維護者**: Claude Code
**專案建立**: 2024
**最後更新**: 2025-10-11
**當前版本**: Phase 1 (多業者支援) + 多 Intent 分類系統 完成
**最新功能**: 多 Intent 分類（回測通過率從 40% 提升到 60%）⭐
**下一階段**: Phase 2 (外部 API 整合) 規劃中
