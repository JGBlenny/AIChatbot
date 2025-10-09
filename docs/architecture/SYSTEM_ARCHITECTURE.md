# 🏗️ AIChatbot 系統架構文件

> 最後更新：2025-10-09
> 版本：1.0.0

---

## 📋 目錄

- [系統概述](#系統概述)
- [整體架構](#整體架構)
- [核心元件](#核心元件)
- [資料流程](#資料流程)
- [技術棧](#技術棧)
- [部署架構](#部署架構)
- [API 文件](#api-文件)

---

## 系統概述

### 專案目標

建立一個基於 RAG (Retrieval-Augmented Generation) 的客服知識庫系統，能夠：

1. 從 LINE 對話記錄自動提取客服問答
2. 生成向量並儲存到資料庫
3. 提供語義搜尋能力
4. 透過 Web 介面管理知識庫
5. 自動更新向量資料

### 核心功能

| 功能模組 | 說明 | 狀態 |
|---------|------|------|
| 對話分析 | LINE 對話 → 結構化問答 | ✅ 已完成 |
| 向量生成 | 文字 → 向量 (Embedding) | ✅ 已完成 |
| 知識管理 | Web 介面編輯知識庫 | 🚧 開發中 |
| RAG 查詢 | 語義搜尋 + AI 回答 | ⏳ 規劃中 |
| 監控儀表板 | API 使用統計 | ⏳ 規劃中 |

---

## 整體架構

### 系統架構圖

```
┌────────────────────────────────────────────────────────────────┐
│                        前端應用層                                │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │ 知識庫管理後台    │  │  RAG ChatBot      │  │ 監控儀表板    │ │
│  │  Vue.js          │  │  Web UI           │  │ Dashboard    │ │
│  │  Port: 8080      │  │  Port: 3001       │  │ Port: 5000   │ │
│  └────────┬─────────┘  └────────┬──────────┘  └──────┬───────┘ │
│           │                     │                     │          │
└───────────┼─────────────────────┼─────────────────────┼─────────┘
            ↓                     ↓                     ↓
┌────────────────────────────────────────────────────────────────┐
│                        API 服務層                                │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │ 知識管理 API      │  │  RAG 查詢 API     │  │ Embedding API│ │
│  │  FastAPI         │  │  FastAPI          │  │ FastAPI      │ │
│  │  Port: 8000      │  │  Port: 8001       │  │ Port: 5000   │ │
│  └────────┬─────────┘  └────────┬──────────┘  └──────┬───────┘ │
│           │                     │                     │          │
│           └─────────────────────┴─────────────────────┘          │
│                              ↓                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               ↓
┌────────────────────────────────────────────────────────────────┐
│                        資料儲存層                                │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │ PostgreSQL       │  │  Redis            │  │ 檔案系統      │ │
│  │  + pgvector      │  │  快取層           │  │ Markdown 檔   │ │
│  │  Port: 5432      │  │  Port: 6379       │  │              │ │
│  └──────────────────┘  └──────────────────┘  └──────────────┘ │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
                               ↓
┌────────────────────────────────────────────────────────────────┐
│                        外部服務                                  │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐                                          │
│  │ OpenAI API       │                                          │
│  │  - Embeddings    │                                          │
│  │  - ChatCompletion│                                          │
│  └──────────────────┘                                          │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## 核心元件

### 1. 對話分析模組

**位置：** `scripts/process_line_chats.py`

**功能：**
- 解析 LINE 對話記錄 (.txt)
- 使用 OpenAI API 提取問答
- 輸出結構化 Excel

**輸入/輸出：**
```
輸入：data/[LINE]*.txt
處理：OpenAI GPT-4o-mini 分析
輸出：data/客服QA整理_測試結果.xlsx
```

**關鍵技術：**
- 正則表達式解析對話
- OpenAI Chat Completion API
- Pandas Excel 處理

---

### 2. Embedding API 服務

**位置：** `embedding-service/app.py`

**功能：**
- 統一的向量生成 API
- Redis 快取機制
- 批次處理支援

**API 端點：**

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/v1/embeddings` | POST | 生成單一文字向量 |
| `/api/v1/embeddings/batch` | POST | 批次生成向量 |
| `/api/v1/health` | GET | 健康檢查 |
| `/api/v1/stats` | GET | 使用統計 |

**Request 範例：**
```json
{
  "text": "租金逾期怎麼辦？",
  "model": "text-embedding-3-small"
}
```

**Response 範例：**
```json
{
  "embedding": [0.234, -0.567, ...],
  "model": "text-embedding-3-small",
  "dimensions": 1536,
  "cached": false
}
```

---

### 3. PostgreSQL + pgvector

**資料庫：** `aichatbot_admin`

**主要表格：**

#### knowledge_base (知識庫)

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | SERIAL | 主鍵 |
| title | VARCHAR(255) | 標題 |
| category | VARCHAR(100) | 分類 |
| question_summary | TEXT | 問題摘要 |
| answer | TEXT | 答案內容 |
| audience | VARCHAR(50) | 對象（房東/租客/管理師） |
| keywords | TEXT[] | 關鍵字陣列 |
| source_file | VARCHAR(255) | 來源檔案 |
| source_date | DATE | 來源日期 |
| **embedding** | **vector(1536)** | **向量資料** |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 更新時間 |

**索引：**
```sql
-- 向量索引（加速相似度搜尋）
CREATE INDEX idx_kb_embedding ON knowledge_base
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 一般索引
CREATE INDEX idx_kb_category ON knowledge_base(category);
CREATE INDEX idx_kb_audience ON knowledge_base(audience);
CREATE INDEX idx_kb_keywords ON knowledge_base USING GIN(keywords);
```

#### chat_history (對話歷史)

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | SERIAL | 主鍵 |
| user_id | VARCHAR(100) | 使用者 ID |
| user_role | VARCHAR(50) | 角色 |
| question | TEXT | 問題 |
| answer | TEXT | 回答 |
| related_kb_ids | INTEGER[] | 相關知識 ID |
| feedback_score | INTEGER | 評分 (1-5) |
| feedback_comment | TEXT | 評論 |
| created_at | TIMESTAMP | 建立時間 |

---

### 4. 知識庫管理後台

**後端 API：** `knowledge-admin/backend/app.py`

**技術棧：**
- FastAPI
- psycopg2 (PostgreSQL 驅動)
- requests (呼叫 Embedding API)

**API 端點：**

| 端點 | 方法 | 說明 |
|------|------|------|
| `GET /api/knowledge` | GET | 列出所有知識 |
| `GET /api/knowledge/{id}` | GET | 取得單一知識 |
| `POST /api/knowledge` | POST | 新增知識 |
| `PUT /api/knowledge/{id}` | PUT | 更新知識（自動重新生成向量） |
| `DELETE /api/knowledge/{id}` | DELETE | 刪除知識 |
| `GET /api/categories` | GET | 取得所有分類 |

**前端介面：** `knowledge-admin/frontend/src/App.vue`

**技術棧：**
- Vue.js 3
- Axios (HTTP 請求)
- marked (Markdown 渲染)

**功能：**
- 📋 列表檢視（分頁、搜尋、篩選）
- ✏️  Markdown 編輯器 + 即時預覽
- 💾 儲存時自動重新生成向量
- 🗑️ 刪除知識

---

## 資料流程

### 1. 知識建立流程

```
1. LINE 對話記錄
   ↓
   [scripts/process_line_chats.py]
   ↓
2. OpenAI API 分析
   ↓
3. Excel 輸出
   data/客服QA整理_測試結果.xlsx
   ↓
   [手動匯入或腳本]
   ↓
4. 生成向量
   Embedding API → OpenAI text-embedding-3-small
   ↓
5. 儲存到 PostgreSQL
   knowledge_base 表
   (包含向量資料)
```

### 2. 知識更新流程

```
1. 使用者在後台編輯
   知識管理後台 (Port 8080)
   ↓
2. 提交更新
   PUT /api/knowledge/{id}
   ↓
3. 後端處理
   - 更新基本資料
   - 呼叫 Embedding API 生成新向量
   ↓
4. 重新生成向量
   POST http://embedding-api:5000/api/v1/embeddings
   ↓
5. 更新資料庫
   UPDATE knowledge_base
   SET answer = ..., embedding = ..., updated_at = NOW()
   ↓
6. 完成
   回傳成功訊息給前端
```

### 3. RAG 查詢流程（規劃中）

```
1. 使用者問問題
   "房客沒繳錢怎麼辦？"
   ↓
2. 問題轉向量
   Embedding API → [0.791, 0.229, ...]
   ↓
3. 向量相似度搜尋
   SELECT * FROM knowledge_base
   ORDER BY embedding <=> query_vector
   LIMIT 3
   ↓
4. 取得相關知識
   - 租金逾期處理 (94.2%)
   - 帳單催繳流程 (87.3%)
   - 違約金計算 (76.1%)
   ↓
5. 組合 Prompt
   "根據以下知識回答：[知識1][知識2][知識3]"
   ↓
6. ChatGPT 生成回答
   OpenAI Chat Completion API
   ↓
7. 回傳給使用者
```

---

## 技術棧

### 後端

| 技術 | 版本 | 用途 |
|------|------|------|
| Python | 3.9+ | 主要開發語言 |
| FastAPI | 0.104+ | Web 框架 |
| OpenAI SDK | 1.0+ | AI 功能 |
| psycopg2 | 2.9+ | PostgreSQL 驅動 |
| pandas | 2.0+ | 資料處理 |
| redis-py | 5.0+ | Redis 客戶端 |

### 前端

| 技術 | 版本 | 用途 |
|------|------|------|
| Vue.js | 3.x | 前端框架 |
| Axios | 1.x | HTTP 請求 |
| marked | 11.x | Markdown 渲染 |
| Chart.js | 4.x | 圖表（儀表板） |

### 資料庫

| 技術 | 版本 | 用途 |
|------|------|------|
| PostgreSQL | 16 | 主資料庫 |
| pgvector | 0.5+ | 向量擴充 |
| Redis | 7 | 快取 |

### 容器化

| 技術 | 版本 | 用途 |
|------|------|------|
| Docker | 24+ | 容器化 |
| Docker Compose | 2.20+ | 多容器編排 |

### AI 服務

| 服務 | 模型 | 用途 |
|------|------|------|
| OpenAI Embeddings | text-embedding-3-small | 向量生成 |
| OpenAI Chat | gpt-4o-mini | 對話分析、RAG 回答 |

---

## 部署架構

### Docker Compose 服務

```yaml
services:
  # 資料庫
  postgres:        # Port 5432
  redis:           # Port 6379
  pgadmin:         # Port 5050

  # API 服務
  embedding-api:   # Port 5000
  knowledge-admin-api:  # Port 8000
  rag-api:         # Port 8001 (規劃中)

  # 前端
  knowledge-admin-web:  # Port 8080
  chatbot-web:     # Port 3001 (規劃中)
```

### 連線埠對應

| 服務 | 內部埠號 | 外部埠號 | 說明 |
|------|---------|---------|------|
| PostgreSQL | 5432 | 5432 | 資料庫 |
| Redis | 6379 | 6379 | 快取 |
| pgAdmin | 80 | 5050 | 資料庫管理 |
| Embedding API | 5000 | 5000 | 向量生成 |
| 知識管理 API | 8000 | 8000 | 後台 API |
| 知識管理前端 | 80 | 8080 | 後台 UI |

### 環境變數

```env
# OpenAI
OPENAI_API_KEY=sk-proj-...

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aichatbot_admin
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# API URLs
EMBEDDING_API_URL=http://localhost:5000/api/v1/embeddings
```

---

## API 文件

### Embedding API

**Base URL:** `http://localhost:5000/api/v1`

#### POST /embeddings

生成文字向量

**Request:**
```json
{
  "text": "租金逾期怎麼辦？",
  "model": "text-embedding-3-small"
}
```

**Response:**
```json
{
  "embedding": [0.234, -0.567, ..., 0.789],
  "model": "text-embedding-3-small",
  "dimensions": 1536,
  "cached": false
}
```

---

### 知識管理 API

**Base URL:** `http://localhost:8000/api`

#### GET /knowledge

列出所有知識

**Query Parameters:**
- `category` (optional): 篩選分類
- `search` (optional): 搜尋關鍵字
- `limit` (default: 50): 每頁筆數
- `offset` (default: 0): 偏移量

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "title": "租金逾期處理",
      "category": "帳務問題",
      "audience": "管理師",
      "content": "...",
      "keywords": ["租金", "逾期"],
      "created_at": "2025-10-09T12:00:00",
      "updated_at": "2025-10-09T12:00:00"
    }
  ],
  "total": 11
}
```

#### PUT /knowledge/{id}

更新知識（自動重新生成向量）

**Request:**
```json
{
  "title": "租金逾期處理",
  "category": "帳務問題",
  "audience": "管理師",
  "content": "租金逾期時...",
  "keywords": ["租金", "逾期", "提醒"]
}
```

**Response:**
```json
{
  "success": true,
  "message": "知識已更新，向量已重新生成",
  "id": 1,
  "title": "租金逾期處理",
  "updated_at": "2025-10-09T14:30:00"
}
```

---

## 版本歷史

### v1.0.0 (2025-10-09)

**新增功能：**
- ✅ LINE 對話分析腳本
- ✅ PostgreSQL + pgvector 設定
- ✅ Embedding API 服務
- ✅ 知識庫管理後台（開發中）

**待開發：**
- ⏳ RAG 查詢 API
- ⏳ ChatBot 前端介面
- ⏳ 監控儀表板

---

## 相關文件

- [快速開始指南](../QUICKSTART.md)
- [pgvector 設定說明](../PGVECTOR_SETUP.md)
- [資料庫 Schema](../database/README.md)
- [API 使用文件](../API_USAGE.md)

---

**維護者：** Claude Code
**最後更新：** 2025-10-09
