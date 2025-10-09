# AIChatbot 後台管理系統 - 專案概覽

## 🎯 專案目標

建立一個完整的後台系統，用於：
1. 匯入和管理 LINE 對話記錄
2. 使用 AI 自動處理和分類對話
3. 生成 Markdown 知識庫檔案
4. 支援 RAG（檢索增強生成）系統

---

## 📁 專案結構

```
AIChatbot/
├── README.md                    # 專案說明
├── NEXT_STEPS.md               # 下一步行動指南
├── PROJECT_OVERVIEW.md         # 本檔案
│
├── backend/                    # FastAPI 後端
│   ├── app/
│   │   ├── api/               # API 路由
│   │   │   ├── conversations.py    # 對話管理 API
│   │   │   └── processing.py       # AI 處理 API
│   │   ├── core/              # 核心配置
│   │   │   ├── config.py          # 環境配置
│   │   │   └── database.py        # 資料庫連接
│   │   ├── models/            # SQLAlchemy 模型
│   │   │   └── conversation.py    # 對話資料模型
│   │   ├── schemas/           # Pydantic Schemas
│   │   │   └── conversation.py    # 資料驗證模型
│   │   ├── services/          # 業務邏輯
│   │   │   ├── line_parser.py     # LINE 對話解析
│   │   │   └── openai_service.py  # OpenAI API 整合
│   │   ├── utils/             # 工具函數
│   │   └── main.py            # FastAPI 應用入口
│   ├── tests/                 # 測試
│   ├── requirements.txt       # Python 依賴
│   ├── .env.example          # 環境變數範例
│   ├── test_example.py       # 測試腳本
│   └── test_conversation.txt # 測試資料
│
├── frontend/                  # React 前端 (待建立)
│
├── knowledge-base/            # Markdown 知識庫檔案
│
└── docs/                      # 文件
    ├── QUICKSTART.md         # 快速開始指南
    └── API_USAGE.md          # API 使用文件
```

---

## 🛠️ 技術棧

### 後端
- **語言**: Python 3.11+
- **框架**: FastAPI 0.109
- **資料庫**: PostgreSQL 16 + SQLAlchemy (Async)
- **AI**: OpenAI API (GPT-4/GPT-3.5)
- **向量資料庫**: pgvector (免費) 或 Pinecone
- **任務隊列**: Celery + Redis (選用)

### 前端 (待建立)
- **語言**: TypeScript
- **框架**: React 18 + Vite
- **UI**: Ant Design 或 Material-UI
- **狀態管理**: React Query + Zustand
- **HTTP**: Axios

---

## 🔄 資料流程

```
┌─────────────────┐
│ LINE 對話文字   │
│ (純文字或JSON)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  1. 匯入解析    │  ← line_parser.py
│  - 解析訊息格式  │
│  - 識別參與者    │
│  - 提取時間戳記  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. 儲存資料庫   │  ← conversations.py
│  - 原始對話     │
│  - 來源資訊     │
│  - 狀態: pending │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. AI 處理      │  ← openai_service.py
│  - 品質評估 (1-10)│
│  - 自動分類     │
│  - 內容清理改寫  │
│  - 實體提取     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. 人工審核     │  ← processing.py
│  - 檢視 AI 結果  │
│  - 手動調整     │
│  - 批准/拒絕    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. 生成 MD      │  ← (待實作)
│  - 按分類組織   │
│  - Q&A 格式化   │
│  - 加入元數據   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 6. 向量化       │  ← (待實作)
│  - 語義分塊     │
│  - 生成嵌入     │
│  - 儲存 pgvector │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 7. RAG 檢索     │  ← (待實作)
│  - 用戶查詢     │
│  - 相似度搜尋   │
│  - 生成回答     │
└─────────────────┘
```

---

## 📊 資料庫 Schema

### conversations 表
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | UUID | 主鍵 |
| raw_content | JSONB | 原始對話內容 |
| processed_content | JSONB | AI 處理結果 |
| source | String | 來源 (line/manual) |
| status | Enum | 狀態 (pending/processing/reviewed/approved/rejected) |
| quality_score | Integer | 品質分數 1-10 |
| primary_category | String | 主要分類 |
| tags | Array | 標籤 |
| created_at | DateTime | 建立時間 |

### knowledge_files 表
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | UUID | 主鍵 |
| file_path | String | MD 檔案路徑 |
| category | String | 分類 |
| content | Text | MD 內容 |
| version | Integer | 版本號 |
| vectorized_at | DateTime | 向量化時間 |

詳細 Schema 請見：`backend/app/models/conversation.py`

---

## 🔌 API 端點

### 對話管理
```
POST   /api/conversations/import/line/text    # 匯入文字檔
POST   /api/conversations/import/line         # 匯入 JSON
GET    /api/conversations/                    # 列表查詢
GET    /api/conversations/{id}                # 查詢詳情
PUT    /api/conversations/{id}                # 更新
DELETE /api/conversations/{id}                # 刪除
GET    /api/conversations/stats/summary       # 統計
```

### AI 處理
```
POST /api/processing/{id}/process-all    # 完整處理
POST /api/processing/{id}/evaluate       # 品質評估
POST /api/processing/{id}/categorize     # 分類
POST /api/processing/{id}/clean          # 清理改寫
POST /api/processing/{id}/extract        # 提取實體
POST /api/processing/{id}/approve        # 批准
POST /api/processing/{id}/reject         # 拒絕
POST /api/processing/batch/process       # 批次處理
```

詳細文件：[docs/API_USAGE.md](docs/API_USAGE.md)

---

## 💡 核心功能說明

### 1. LINE 對話解析器 (`line_parser.py`)

**支援格式**:
```
# 格式 1: 完整時間戳記
2024/01/15 14:30 張三: 訊息內容

# 格式 2: 括號格式
[2024-01-15 14:30:00] 張三: 訊息內容

# 格式 3: 僅時間
14:30 張三: 訊息內容
```

**功能**:
- 自動識別訊息格式
- 提取參與者
- 時間戳記解析
- 轉換為標準 JSON
- 格式化為 Q&A

### 2. OpenAI 服務 (`openai_service.py`)

**功能**:

#### 品質評估
```python
{
  "score": 8,
  "reasoning": "對話完整且內容相關...",
  "suggestions": ["建議..."]
}
```

#### 自動分類
```python
{
  "primary": "技術支援",
  "secondary": ["功能詢問", "使用教學"],
  "confidence": 0.92
}
```

#### 內容清理
```python
{
  "question": "如何使用這個功能？",
  "answer": "使用方式如下：...",
  "context": "對話時間：...",
  "tags": ["設定", "教學"],
  "confidence": 0.95
}
```

#### 實體提取
```python
{
  "entities": {
    "products": ["產品A"],
    "features": ["功能X"],
    "versions": ["v2.0"]
  },
  "intents": ["詢問", "求助"],
  "sentiment": "positive",
  "keywords": ["設定", "教學"]
}
```

---

## 📈 使用情境

### 情境 1: 客服對話整理
1. 匯出 LINE 客服對話記錄
2. 上傳到系統
3. AI 自動分類為：產品功能、技術支援、計費問題等
4. 人工審核確認
5. 生成 FAQ 知識庫

### 情境 2: 產品文件建立
1. 收集用戶與客服的對話
2. AI 提取產品功能相關問答
3. 整理為使用教學文件
4. 向量化後支援 AI 問答

### 情境 3: 品質分析
1. 定期匯入對話
2. 評估客服回答品質
3. 識別常見問題
4. 改進服務流程

---

## 🔒 安全性考量

### 環境變數
- 所有敏感資訊存放在 `.env`
- 不提交到版本控制
- 使用強隨機 `SECRET_KEY`

### API 安全
- CORS 限制來源
- 未來加入 JWT 認證
- Rate Limiting

### 資料隱私
- 對話內容加密儲存（可選）
- 定期清理舊資料
- 遵守 GDPR（如適用）

---

## 💰 成本預估

### OpenAI API 成本（每月）

| 方案 | 模型 | 處理量 | 預估成本 |
|------|------|--------|---------|
| 超省 | GPT-3.5-Turbo | 500 筆 | $5-10 |
| 經濟 | GPT-4o-mini | 2000 筆 | $20-30 |
| 標準 | GPT-4-Turbo | 5000 筆 | $100-150 |

**計算方式**:
- 每筆對話約 500 tokens
- 處理 3 次（評估 + 分類 + 清理）
- GPT-3.5: $0.001/1K tokens
- GPT-4: $0.01/1K tokens

### 向量資料庫成本

| 方案 | 成本 |
|------|------|
| pgvector | $0（使用現有 PostgreSQL）|
| Pinecone Starter | $70/月 |
| Weaviate 自架 | $0（需伺服器）|

**建議**: 小資料量使用 **pgvector**

---

## 🚀 效能優化

### 資料庫
- 建立索引（status, category, created_at）
- 使用連接池
- 分頁查詢

### API
- 非同步處理（FastAPI + SQLAlchemy Async）
- 背景任務（批次處理）
- 快取（Redis，選用）

### AI 處理
- 批次呼叫（減少 API 請求）
- 平行處理（asyncio.gather）
- 結果快取

---

## 🧪 測試

### 單元測試
```bash
cd backend
pytest tests/
```

### API 測試
```bash
# 使用測試腳本
python test_example.py

# 或使用 pytest
pytest tests/test_api.py
```

### 負載測試
```bash
# 使用 locust
pip install locust
locust -f tests/locustfile.py
```

---

## 📦 部署

### 開發環境
- 本地 PostgreSQL
- Uvicorn 自動重載
- DEBUG=True

### 生產環境建議
- Docker Compose
- PostgreSQL（雲端或自架）
- Nginx 反向代理
- Gunicorn + Uvicorn Workers
- Supervisor 或 systemd

**Docker Compose 範例**:
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://...
      - OPENAI_API_KEY=...
    ports:
      - "8000:8000"

  db:
    image: postgres:16
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
```

---

## 📖 學習資源

### FastAPI
- [官方教學](https://fastapi.tiangolo.com/tutorial/)
- [非同步資料庫](https://fastapi.tiangolo.com/advanced/async-sql-databases/)

### LangChain
- [快速開始](https://python.langchain.com/docs/get_started/quickstart)
- [RAG 教學](https://python.langchain.com/docs/use_cases/question_answering/)

### PostgreSQL
- [pgvector 教學](https://github.com/pgvector/pgvector)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)

---

## 🤝 貢獻指南

### 開發流程
1. Fork 專案
2. 建立 feature branch
3. 提交變更
4. 建立 Pull Request

### 程式規範
- 使用 Black 格式化
- 遵循 PEP 8
- 撰寫單元測試
- 更新文件

---

## 📄 授權

MIT License

---

## 👨‍💻 作者

建立於 2024 年，使用 Claude Code 協助開發

---

**開始使用**: 請參考 [快速開始指南](docs/QUICKSTART.md)

**API 文件**: 請參考 [API 使用說明](docs/API_USAGE.md)

**下一步**: 請參考 [NEXT_STEPS.md](NEXT_STEPS.md)
