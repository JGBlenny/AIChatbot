# 🤖 RAG Orchestrator - 智能問答協調器

> 🎯 **本檔寫現況，不是設計依據。目標：本系統是對話服務，不是 MCP 系統；呼叫端走專用對話 API，`/mcp` 不是最終入口；JGB 工具要搬出本系統，由 JGB 維護。** 分工與完整架構見 `docs/architecture/TARGET_ARCHITECTURE.md`。


**對話核心是 `AgentRuntime`**（`services/agent/runtime.py`）：模型持有回合、自己決定
呼叫哪支工具，輸出逐句經 Verifier 驗引用。**`/mcp` 是它的門面之一**，也是目前唯一
掛著的對外入口（`routers/agent.py`）。本服務同時承載檢索與一批後台 CRUD 路由。

⛔ 架構請讀 [`docs/architecture/SYSTEM_ARCHITECTURE.md`](../docs/architecture/SYSTEM_ARCHITECTURE.md)
與 [`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`](../docs/architecture/AGENTIC_MCP_ARCHITECTURE.md)；
`/mcp` 契約讀 [`docs/api/mcp-facade.md`](../docs/api/mcp-facade.md)。

## 📋 目錄

- [系統概述](#系統概述)
- [核心功能](#核心功能)
- [系統架構](#系統架構)
- [意圖類型](#意圖類型)
- [API 文件](#api-文件)
- [配置說明](#配置說明)
- [使用範例](#使用範例)
- [本地開發](#本地開發)

---

## 系統概述

```
POST /mcp  （唯一掛著的對外對話入口，X-API-Key 無條件必帶）
   ↓ services/agent/mcp_facade.py —— 13 步進場契約、額度計量、照片前處理
   ↓ services/agent/runtime.py::AgentRuntime.run_turn —— 核心（建構依賴裡沒有協定）
        段一 turn_segments      六條程式終止路徑
        段二 turn_context       九段注入（user_message 永遠最後）
        段三 模型迴圈           registry.call（in-process）＋ Verifier 逐句驗引用
        段四 exit_gates         四道閘依序，⛔ 順序即契約
   ↓ 全回合共 13 個終止點
```

**工具**：六域 `jgb2.query.*`（15 個 face）、`kb.search`／`kb.get`、`help.read`、
寫入類與確認卡。**受眾**只有 `prospect` 與 `property_manager`。

🔴 **⛔ 以下全部不存在**（2026-09-11 隨舊 REST 對話鏈刪除，DSP-046）：
`/api/v1/message`、`/api/v1/chat/stream`（實測皆 404）、意圖分類（11 種意圖）、
信心度評估、Phase 3 LLM 答案優化、SOP 編排、表單狀態機。
⛔ 不要照它們設計新東西，也不要拿它們解釋現行行為。

## 後台維護面（仍存活，但⛔ 不在對話回合路徑上）

未釐清問題（`/api/v1/unclear-questions*`）、Redis 快取、知識匯入匯出、業者與 SOP
後台 CRUD、表單後台 CRUD、迴圈查詢與審核。
⚠️ **SOP 與表單改了不會影響機器人回答**——對話路徑對它們零讀取。

## API 文件

### 主要端點

> ⚠️ **2026-09-11 舊鏈退役**：`/api/v1/message`、`/api/v1/chat/stream`、
> `/api/v1/conversations`、`/api/v1/conversations/{id}`、
> `/api/v1/conversations/{id}/feedback` 五支端點**均已刪除**（2026-09-11 砍除舊
> REST 對話鏈，31 個產品模組隨之移除）。對話能力現在**只**經 `/mcp` 門面
> （server-to-server，非公開 REST，也不支援瀏覽器直連），契約見
> `docs/api/mcp-facade.md`。⛔ 下面這行「已移除請改用 xxx」的舊警語**指向的
> 兩個替代端點自己也已經死了**，勿依此串接：
>
> ~~`/api/v1/chat` 端點已於 2025-10-21 移除。請使用 `/api/v1/message` 或
> `/api/v1/chat/stream` 替代。`~~ ⛔ 上一句是 2025-10-21 的歷史記錄，其推薦的
> 替代端點也已於 2026-09-11 一併刪除。

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | `/api/v1/unclear-questions` | 取得未釐清問題列表 |
| GET | `/api/v1/unclear-questions/{id}` | 取得問題詳情 |
| PUT | `/api/v1/unclear-questions/{id}` | 更新問題狀態 |
| DELETE | `/api/v1/unclear-questions/{id}` | 刪除問題 |
| GET | `/api/v1/unclear-questions-stats` | 取得統計資訊 |
| GET | `/api/v1/unclear-questions-search` | 搜尋問題 |
| POST | `/api/v1/unclear-questions-batch-update` | 批次更新 |

### 完整 API 文件

啟動服務後，存取 http://localhost:8100/docs 查看互動式 API 文件。

---

## 配置說明

### 環境變數

```bash
# OpenAI API Key (必需)
OPENAI_API_KEY=sk-proj-xxx

# 資料庫連線 (必需)
DB_HOST=postgres
DB_PORT=5432
DB_NAME=aichatbot_admin
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password

# Embedding API URL (必需)
EMBEDDING_API_URL=http://embedding-api:5000/api/v1/embeddings

# Redis 緩存配置 (可選)
REDIS_HOST=redis
REDIS_PORT=6379
CACHE_ENABLED=true                # 是否啟用緩存 (true/false)
CACHE_TTL_QUESTION=3600           # 問題緩存 TTL（秒）- 預設 1 小時
CACHE_TTL_VECTOR=7200             # 向量緩存 TTL（秒）- 預設 2 小時
CACHE_TTL_RAG_RESULT=1800         # RAG 結果緩存 TTL（秒）- 預設 30 分鐘

# 服務配置 (可選)
HOST=0.0.0.0
PORT=8100
```

### 意圖配置 (intents.yaml)

可自定義意圖類型：

```yaml
intents:
  - name: "自定義意圖名稱"
    type: "knowledge"  # knowledge, data_query, action, hybrid
    keywords: ["關鍵字1", "關鍵字2"]
    confidence_threshold: 0.80
    api_required: false  # 是否需要外部 API
    api_endpoint: "endpoint_name"  # API 端點名稱
    api_action: "action_name"  # API 操作名稱
```

### 信心度閾值配置

在 `services/confidence_evaluator.py` 中可調整：

```python
config = {
    "high_confidence_threshold": 0.85,    # 高信心度閾值
    "medium_confidence_threshold": 0.70,  # 中信心度閾值
    "similarity_weight": 0.6,             # 相似度權重
    "result_count_weight": 0.2,           # 結果數權重
    "keyword_match_weight": 0.2           # 關鍵字權重
}
```

---

## 本地開發

### 前置需求

- Python 3.11+
- PostgreSQL 16+ (with pgvector)
- Redis 7+ (for Embedding API)
- OpenAI API Key

### 安裝依賴

```bash
cd rag-orchestrator
pip install -r requirements.txt
```

### 設定環境變數

```bash
# 建立 .env 檔案
cat > .env << EOF
OPENAI_API_KEY=sk-proj-your-key-here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aichatbot_admin
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password
EMBEDDING_API_URL=http://localhost:5001/api/v1/embeddings
EOF
```

### 啟動服務

```bash
# 確保 PostgreSQL 和 Embedding API 已啟動
docker-compose up -d postgres redis embedding-api

# 啟動 RAG Orchestrator
python app.py
```

服務將在 http://localhost:8100 啟動。

### 開發模式

使用 uvicorn 的 reload 功能：

```bash
uvicorn app:app --host 0.0.0.0 --port 8100 --reload
```

### 測試

```bash
# 健康檢查
curl http://localhost:8100/api/v1/health

# 統計資訊
curl http://localhost:8100/api/v1/stats

# 互動式 API 文件
open http://localhost:8100/docs
```

---

## 資料庫表結構

### conversation_logs 表

記錄所有對話內容和處理結果：

```sql
CREATE TABLE conversation_logs (
    id SERIAL PRIMARY KEY,
    conversation_id UUID DEFAULT gen_random_uuid(),
    user_id VARCHAR(100),
    question TEXT NOT NULL,
    intent_type VARCHAR(50),
    sub_category VARCHAR(100),
    keywords TEXT[],
    retrieved_docs JSONB,
    similarity_scores FLOAT[],
    confidence_score FLOAT,
    api_called BOOLEAN DEFAULT false,
    api_endpoints TEXT[],
    api_responses JSONB,
    final_answer TEXT,
    answer_source VARCHAR(50),
    processing_time_ms INTEGER,
    user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 5),
    user_feedback TEXT,
    is_resolved BOOLEAN DEFAULT true,
    escalated_to_human BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### unclear_questions 表

記錄低信心度的未釐清問題：

```sql
CREATE TABLE unclear_questions (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    user_id VARCHAR(100),
    intent_type VARCHAR(50),
    similarity_score FLOAT,
    retrieved_docs JSONB,
    frequency INTEGER DEFAULT 1,
    first_asked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_asked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    assigned_to VARCHAR(100),
    resolved_at TIMESTAMP,
    resolution_note TEXT,
    suggested_answers TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 效能監控

### 關鍵指標

- **回應時間**：目標 < 500ms (含 RAG 檢索)
- **信心度分布**：高 > 70%, 中 < 20%, 低 < 10%
- **準確率**：使用者評分 >= 4 的比例 > 80%
- **轉人工率**：< 15%

### 監控端點

```bash
# 服務狀態
curl http://localhost:8100/api/v1/health

# 統計資訊
curl http://localhost:8100/api/v1/stats
```

---

## 故障排除

### 問題 1：OpenAI API 連線失敗

**症狀**：對話回合起不來、`agent.turn` 回錯

**解決方法**：
```bash
# 檢查 API Key
echo $OPENAI_API_KEY

# 測試連線
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### 問題 2：Embedding API 連線失敗

**症狀**：RAG 檢索失敗

**解決方法**：
```bash
# 檢查 Embedding API 狀態
curl http://localhost:5001/api/v1/health

# 檢查環境變數
echo $EMBEDDING_API_URL
```

### 問題 3：資料庫連線失敗

**症狀**：啟動時報錯 "Connection refused"

**解決方法**：
```bash
# 檢查 PostgreSQL 狀態
docker-compose ps postgres

# 測試連線
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "SELECT 1;"
```

### 問題 4：intents.yaml 載入失敗

**症狀**：啟動時報錯 "Config file not found"

**解決方法**：
```bash
# 檢查檔案是否存在
ls -la config/intents.yaml

# 檢查 YAML 格式
python -c "import yaml; yaml.safe_load(open('config/intents.yaml'))"
```

---

## 後續規劃

⛔ **原本的 Phase 3／4／5 規劃已刪除（2026-09-12）**：Phase 3「LLM 答案優化」標著
「✅ 已完成」，而 `llm_answer_optimizer.py` 2026-09-11 已刪；Phase 4／5 建立在
同一條舊鏈上。現行路線圖見 `.kiro/specs/` 各 spec 與 `.claude/DECISIONS.md`。

## 參考文件

- [系統架構（現況全景）](../docs/architecture/SYSTEM_ARCHITECTURE.md) ⭐
- [Agentic-MCP 對話架構](../docs/architecture/AGENTIC_MCP_ARCHITECTURE.md) ⭐（§2b 流程、§4b 轉人來源）
- [`/mcp` 串接契約](../docs/api/mcp-facade.md)
- [API 完整文件](http://localhost:8100/docs) (啟動後存取)
- [知識管理系統說明](../knowledge-admin/README.md)

---

**維護者**: Claude Code
**最後對碼**: 2026-09-12（agentic-MCP 單線）
