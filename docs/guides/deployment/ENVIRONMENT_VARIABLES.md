# 環境變數參考

本文檔列出 AIChatbot 專案所有環境變數的定義、預設值和使用說明。

## 📋 命名規範

所有環境變數遵循以下規範：
- ✅ 使用 **大寫字母**
- ✅ 使用 **下劃線** 分隔單詞
- ✅ 使用 **清晰的前綴** 分類（DB_、REDIS_、OPENAI_）
- ✅ API URLs 使用 **`*_API_URL`** 後綴
- ✅ 提供 **合理的預設值**

## 🔑 必需變數

### OpenAI API

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `OPENAI_API_KEY` | OpenAI API 金鑰，用於 Embedding 和 LLM | 無 | ✅ |

**使用位置**：
- `embedding-service` - 生成向量嵌入
- `rag-orchestrator` - 對話回合（`AGENT_MODEL`）、查詢改寫、知識生成、文件轉換
- `knowledge-admin-api` - 回測框架

**範例**：
```bash
OPENAI_API_KEY=sk-proj-your-api-key-here
```

### 對話模型專用端點（選用，只供本機接 Bedrock）

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `AGENT_LLM_BASE_URL` | 只給 `rag-orchestrator` 對話回合用的 OpenAI 相容端點（本機：`https://bedrock-runtime.ap-northeast-1.amazonaws.com/openai/v1`） | 未設 | ❌ |
| `AGENT_LLM_API_KEY_FILE` | 該端點的金鑰**檔案路徑**（Compose secret：`/run/secrets/agent_llm_api_key`）；⛔ 把金鑰本身放環境變數 | 未設 | ❌ |

- 兩者須成對設定；只設其一、或同時設了 `OPENAI_BASE_URL` ⇒ 啟動失敗。未設時一切照舊（正式機現況）。
- 照片辨識、文件歸納、健康檢查、embedding 不受影響，仍用 `OPENAI_API_KEY`。
- 本機啟動：`docker compose -f docker-compose.prod.yml -f docker-compose.bedrock-local.yml up -d --build rag-orchestrator`（覆寫檔寫死 `USE_MOCK_JGB_API=true`）。

## 🗄️ 資料庫變數

### PostgreSQL

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `DB_HOST` | PostgreSQL 主機位址 | `localhost` / `postgres` (Docker) | ❌ |
| `DB_PORT` | PostgreSQL 埠號 | `5432` | ❌ |
| `DB_NAME` | 資料庫名稱 | `aichatbot_admin` | ❌ |
| `DB_USER` | 資料庫使用者 | `aichatbot` | ❌ |
| `DB_PASSWORD` | 資料庫密碼 | `aichatbot_password` | ❌ |

**使用位置**：
- `rag-orchestrator` - 讀取意圖、知識庫、業者資料
- `knowledge-admin-api` - 知識管理、測試情境管理

**Docker 預設值**：
```bash
DB_HOST=postgres  # 容器名稱
DB_PORT=5432
DB_NAME=aichatbot_admin
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password
```

**本地開發預設值**：
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aichatbot_admin
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password
```

## 🔴 Redis 變數

### Redis 連線配置

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `REDIS_HOST` | Redis 主機位址 | `localhost` / `redis` (Docker) | ❌ |
| `REDIS_PORT` | Redis 埠號 | `6379` | ❌ |

**使用位置**：
- `embedding-service` - Embedding 快取
- `rag-orchestrator` - 三層緩存系統（Phase 3）

**Docker 預設值**：
```bash
REDIS_HOST=redis  # 容器名稱
REDIS_PORT=6379
```

**本地開發預設值**：
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

### Redis 緩存配置 ⭐ NEW (Phase 3)

Phase 3 引入**三層緩存架構**，顯著降低 API 成本（70-90%）並提升回應速度。

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `CACHE_ENABLED` | 是否啟用緩存系統 | `true` | ❌ |
| `CACHE_TTL_QUESTION` | Layer 1 問題緩存 TTL（秒） | `3600` (1小時) | ❌ |
| `CACHE_TTL_VECTOR` | Layer 2 向量緩存 TTL（秒） | `7200` (2小時) | ❌ |
| `CACHE_TTL_RAG_RESULT` | Layer 3 RAG 結果緩存 TTL（秒） | `1800` (30分鐘) | ❌ |

**使用位置**：
- `rag-orchestrator` - 智能緩存管理

**緩存層說明**：
- **Layer 1 - 問題緩存**: 完全相同的問題直接返回（節省 90% 成本）
- **Layer 2 - 向量緩存**: 相同問題不重複呼叫 embedding API（節省 70% 成本）
- **Layer 3 - 結果緩存**: 相同檢索結果快取（節省 50% 成本）

**範例**：
```bash
CACHE_ENABLED=true
CACHE_TTL_QUESTION=3600      # 1 小時
CACHE_TTL_VECTOR=7200        # 2 小時
CACHE_TTL_RAG_RESULT=1800    # 30 分鐘
```

**效能影響**：
- 啟用緩存後，重複問題回應時間從 2-3 秒降至 50-200ms
- API 成本可降低 70-90%

## 🌐 API URLs

### 微服務 URLs

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `EMBEDDING_API_URL` | Embedding API 端點 | `http://localhost:5001/api/v1/embeddings` | ❌ |
| `RAG_API_URL` | RAG Orchestrator 端點 | `http://localhost:8100` | ❌ |

**使用位置**：
- `rag-orchestrator` → `EMBEDDING_API_URL`
- `knowledge-admin-api` → `EMBEDDING_API_URL`, `RAG_API_URL`

**Docker 預設值**：
```bash
EMBEDDING_API_URL=http://embedding-api:5000/api/v1/embeddings
RAG_API_URL=http://rag-orchestrator:8100
```

## 🤖 AI 模型配置

### LLM 主模型

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `OPENAI_MODEL` | RAG 答案生成的主模型 | `gpt-3.5-turbo` | ❌ |

**使用位置**：
- `rag-orchestrator` - 對話回合的答案生成（⛔ 參數注入與答案合成的程式已於 2026-09-11 刪除）

**可選值**：
- `gpt-3.5-turbo` （預設，速度快 2-3 倍，成本低 70%）
- `gpt-4o-mini` （平衡品質和成本）
- `gpt-4o` （高品質）
- `gpt-4` （最高品質，成本最高）

**範例**：
```bash
OPENAI_MODEL=gpt-3.5-turbo
```

---

### 知識生成模型

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `KNOWLEDGE_GEN_MODEL` | AI 知識生成使用的模型 | `gpt-4o-mini` | ❌ |

**使用位置**：
- `rag-orchestrator` - AI 知識生成功能

**可選值**：
- `gpt-4o-mini` （預設，平衡品質和成本）
- `gpt-4o` （高品質）
- `gpt-4` （最高品質，成本高）

**範例**：
```bash
KNOWLEDGE_GEN_MODEL=gpt-4o-mini
```

---

### 規格書轉換模型

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `DOCUMENT_CONVERTER_MODEL` | 規格書轉換使用的模型 | `gpt-4o` | ❌ |

**使用位置**：
- `rag-orchestrator` - 文件轉換服務 (Word/PDF → Q&A)

**說明**：
- 用於將 Word 或 PDF 規格書轉換為知識庫 Q&A
- 需要更強的理解能力和大 context 處理能力
- 不限制 max_tokens，確保完整提取所有內容

**可選值**：
- `gpt-4o` （預設，128K context，高品質）
- `gpt-4` （最高品質，成本高）
- `gpt-3.5-turbo` （不推薦，context 較小）

**範例**：
```bash
DOCUMENT_CONVERTER_MODEL=gpt-4o
```

## 🔐 服務對服務認證

### rag API Key 認證

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `RAG_API_AUTH_ENFORCE` | rag-orchestrator 服務對服務 API Key 認證開關。關（預設）→ 不強制（安全上線）；開 → 除豁免路徑外，請求須帶 Header `X-API-Key`，以 SHA-256 比對 `api_keys` 表（`is_active`）驗證 | `false`（關） | ❌ |

**接受的開啟值**：`1` / `true` / `yes` / `on`（不分大小寫），其餘一律視為關。

**使用位置**：
- `rag-orchestrator` - middleware 攔截驗證（豁免：`/`、`/api/v1/health`、`/docs`、`/redoc`、`/openapi`）

**金鑰來源**：`api_keys` 表（只存 SHA-256 雜湊），由 knowledge-admin 後台 `/api/api-keys` 建立 / 停用；明文僅建立當下回傳一次。

```bash
# 啟用 rag API Key 認證（正式環境建議開啟）
RAG_API_AUTH_ENFORCE=true
```

## 📝 .env 文件範例

⛔ **本檔不再抄一份 .env 範例。** 正本是 repo 根目錄的 `.env.example`——
2026-09-12 已逐鍵對碼。抄第二份的代價已經看過：這裡曾留著一整批零讀者的鍵，
而且是可以直接複製貼上的形態。

```bash
cp .env.example .env    # 然後至少填 OPENAI_API_KEY
```

新線（agentic-MCP）的模型與旗標組態見
[`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`](../../architecture/AGENTIC_MCP_ARCHITECTURE.md) §6。

## 最小配置（僅必需變數）

```bash
# OpenAI API Key
OPENAI_API_KEY=sk-proj-your-api-key-here
```

### 完整配置

⛔ **本檔不抄第二份**——正本是 repo 根目錄的 `.env.example`（2026-09-12 逐鍵對碼過）。

🔴 原本這裡有一份「Phase 3 完整配置」，其中九組鍵**全部零程式讀者**，
且是可以直接複製貼上的形態——最危險的那種。2026-09-12 整段刪除。
要看舊版：`git show HEAD:docs/guides/deployment/ENVIRONMENT_VARIABLES.md`。

## 🔒 安全注意事項

### ⚠️ 敏感變數

以下變數包含敏感資訊，**絕不可提交到版本控制**：

- ✋ `OPENAI_API_KEY` - API 金鑰
- ✋ `DB_PASSWORD` - 資料庫密碼

### ✅ 最佳實踐

1. **使用 .env 文件**
   ```bash
   cp .env.example .env
   nano .env  # 編輯並填入真實值
   ```

2. **確認 .gitignore**
   ```gitignore
   .env
   .env.local
   *.env
   ```

3. **不要在代碼中硬編碼**
   ```python
   # ❌ 錯誤
   OPENAI_API_KEY = "sk-proj-..."

   # ✅ 正確
   OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
   ```

4. **生產環境使用環境變數**
   ```bash
   # Kubernetes Secret
   kubectl create secret generic aichatbot-secrets \
     --from-literal=OPENAI_API_KEY=sk-proj-...

   # Docker Compose
   docker-compose up -d --env-file .env.prod
   ```

## 🔍 故障排除

### 常見問題

**Q: 為什麼我的 API Key 不生效？**

A: 檢查：
1. .env 文件是否在專案根目錄
2. Docker 容器是否已重啟（`docker-compose restart`）
3. 變數名稱是否正確（`OPENAI_API_KEY` 而非 `OPENAI_KEY`）

**Q: 本地開發時資料庫連接失敗？**

A: 確認：
1. `DB_HOST` 設為 `localhost` 而非 `postgres`
2. PostgreSQL 服務已啟動
3. 埠號 5432 未被佔用

**Q: Docker 環境下服務無法互相連接？**

A: 檢查：
1. 使用容器名稱而非 localhost（如 `postgres` 而非 `localhost`）
2. API URLs 指向容器內部端點（如 `http://embedding-api:5000`）
3. 所有服務在同一個 Docker 網路

## 📚 相關文件

- Docker Compose 指南
- 回測環境變數參考
- [快速開始指南](../getting-started/QUICKSTART.md)
- 開發工作流程

---

## 📊 環境變數統計

🔴 **2026-09-12 逐鍵對碼後，刪掉 9 個整節死掉的分類**（RAG 檢索、答案合成、信心度評估、
條件式優化、意圖建議、未釐清問題、回測框架、前端開發、其他）——這些鍵在
`rag-orchestrator` 非測試 `.py` 完全沒有讀者，主體隨舊 REST 對話鏈於 2026-09-11 刪除。
**本檔現在列的每一個鍵都有非測試程式讀者**（`OPENAI_KEY` 例外，那是故障排除節刻意留的反例）。

| 類別 | 變數數量 |
|-----|---------|
| OpenAI API | 1 |
| PostgreSQL | 5 |
| Redis（連線＋緩存） | 6 |
| API URLs | 2 |
| LLM 模型 | 3 |
| 服務對服務認證 | 1 |

⛔ 要看舊旋鈕請 `git show HEAD:docs/guides/deployment/ENVIRONMENT_VARIABLES.md`。
新線（agentic-MCP）的模型與旗標組態見
[`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`](../../architecture/AGENTIC_MCP_ARCHITECTURE.md) §6。

## 🔄 版本歷史

### v3.0 (2025-10-22) - Phase 3 完整更新

🔴 **2026-09-12：本節原列的「新增 23 個環境變數」清單已刪除**——其中意圖分類器、
答案合成、信心度評估、條件式優化、意圖建議、未釐清問題共 6 組全部零程式讀者，
主體隨舊 REST 對話鏈於 2026-09-11 刪除（DSP-046）。

**文檔改進**：
- 新增詳細的使用說明和範例
- 新增效能影響說明
- 新增完整的 .env 範例（45 個變數）
- 新增環境變數統計表

### v2.0 (2025-10-13)

**新增環境變數**：
- 回測框架配置（7 個）

### v1.0 (2025-01-XX)

**初始版本**：
- 核心環境變數（15 個）

---

**最後更新**: 2025-10-22
**維護者**: Claude Code
**文件版本**: 3.0
