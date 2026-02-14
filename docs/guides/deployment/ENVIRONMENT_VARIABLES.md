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
- `rag-orchestrator` - 意圖分類、答案優化、知識生成
- `knowledge-admin-api` - 回測框架

**範例**：
```bash
OPENAI_API_KEY=sk-proj-your-api-key-here
```

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
| `KNOWLEDGE_ADMIN_API_URL` | 知識管理 API 端點 | `http://localhost:8000/api` | ❌ |

**使用位置**：
- `rag-orchestrator` → `EMBEDDING_API_URL`
- `knowledge-admin-api` → `EMBEDDING_API_URL`, `RAG_API_URL`

**Docker 預設值**：
```bash
EMBEDDING_API_URL=http://embedding-api:5000/api/v1/embeddings
RAG_API_URL=http://rag-orchestrator:8100
KNOWLEDGE_ADMIN_API_URL=http://knowledge-admin-api:8000/api
```

## 🤖 AI 模型配置

### LLM 主模型

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `OPENAI_MODEL` | RAG 答案生成的主模型 | `gpt-3.5-turbo` | ❌ |

**使用位置**：
- `rag-orchestrator` - 答案生成、參數注入、答案合成

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

### 意圖分類器模型 ⭐ NEW (Phase 3)

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `INTENT_CLASSIFIER_MODEL` | 意圖分類使用的模型 | `gpt-3.5-turbo` | ❌ |
| `INTENT_CLASSIFIER_TEMPERATURE` | 意圖分類溫度（0-2） | `0.1` | ❌ |
| `INTENT_CLASSIFIER_MAX_TOKENS` | 意圖分類最大 tokens | `500` | ❌ |

**使用位置**：
- `rag-orchestrator` - 多意圖分類（1 主意圖 + 2 次要意圖）

**說明**：
- **Temperature 0.1**: 低溫度確保分類結果穩定
- **Max Tokens 500**: 意圖分類回應較短，500 tokens 足夠

**範例**：
```bash
INTENT_CLASSIFIER_MODEL=gpt-3.5-turbo
INTENT_CLASSIFIER_TEMPERATURE=0.1
INTENT_CLASSIFIER_MAX_TOKENS=500
```

---

### 知識生成模型

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `KNOWLEDGE_GEN_MODEL` | AI 知識生成使用的模型 | `gpt-3.5-turbo` | ❌ |

**使用位置**：
- `rag-orchestrator` - AI 知識生成功能

**可選值**：
- `gpt-3.5-turbo` （預設，成本低）
- `gpt-4o-mini` （更高品質）
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

## 🎯 RAG 檢索配置 ⭐ NEW (Phase 3)

### 相似度閾值

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `RAG_SIMILARITY_THRESHOLD` | RAG 向量檢索相似度閾值 | `0.6` | ❌ |

**使用位置**：
- `rag-orchestrator` - 控制知識檢索的最低相似度

**說明**：
- 向量相似度低於此閾值的知識不會被檢索
- 閾值範圍：0.0 - 1.0
- 較高閾值（0.7+）：更精準但可能漏掉相關知識
- 較低閾值（0.5-）：更廣泛但可能包含不相關知識

**範例**：
```bash
RAG_SIMILARITY_THRESHOLD=0.6
```

---

## 🎨 答案合成配置 ⭐ NEW (Phase 3 - SOP 整合)

### 多來源答案合成

當檢索到多個 SOP 項目時，系統可以使用 LLM 合成統一的答案。

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `ENABLE_ANSWER_SYNTHESIS` | 是否啟用答案合成 | `true` | ❌ |
| `SYNTHESIS_THRESHOLD` | 合成閾值（相似度） | `0.99` | ❌ |
| `SYNTHESIS_MIN_RESULTS` | 最少合成來源數 | `2` | ❌ |
| `SYNTHESIS_MAX_RESULTS` | 最多合成來源數 | `5` | ❌ |
| `SOP_SIMILARITY_SCORE` | SOP 相似度分數 | `0.70` | ❌ |

**使用位置**：
- `rag-orchestrator` - SOP 多項目答案合成

**說明**：
- **SYNTHESIS_THRESHOLD**: SOP 相似度通常為 1.0，設為 0.99 可確保只合成 SOP 項目
- **SYNTHESIS_MIN_RESULTS**: 至少 2 個來源才進行合成，避免單一來源浪費 LLM 呼叫
- **SYNTHESIS_MAX_RESULTS**: 最多合成 5 個來源，避免過長的 prompt

**範例**：
```bash
ENABLE_ANSWER_SYNTHESIS=true
SYNTHESIS_THRESHOLD=0.99
SYNTHESIS_MIN_RESULTS=2
SYNTHESIS_MAX_RESULTS=5
SOP_SIMILARITY_SCORE=0.70
```

---

## 🔍 信心度評估配置 ⭐ NEW (Phase 3)

### 信心度閾值

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `CONFIDENCE_HIGH_THRESHOLD` | 高信心度閾值 | `0.85` | ❌ |
| `CONFIDENCE_MEDIUM_THRESHOLD` | 中等信心度閾值 | `0.70` | ❌ |

**使用位置**：
- `rag-orchestrator` - 意圖分類信心度評估

**說明**：
- **≥ 0.85**: 高信心度 → 直接使用分類結果
- **0.70 - 0.85**: 中等信心度 → 使用但標記為不確定
- **< 0.70**: 低信心度 → 標記為 unclear

**範例**：
```bash
CONFIDENCE_HIGH_THRESHOLD=0.85
CONFIDENCE_MEDIUM_THRESHOLD=0.70
```

---

## ⚡ 條件式優化配置 ⭐ NEW (Phase 3 - 智能路由)

### 快速路徑與模板處理

Phase 3 引入**智能路由策略**，根據相似度和信心度選擇最佳處理路徑。

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `FAST_PATH_THRESHOLD` | 快速路徑閾值（跳過 LLM） | `0.75` | ❌ |
| `TEMPLATE_MIN_SCORE` | 模板最低信心度 | `0.55` | ❌ |
| `TEMPLATE_MAX_SCORE` | 模板最高信心度 | `0.75` | ❌ |
| `LLM_PARAM_INJECTION_TEMP` | LLM 參數注入溫度 | `0.1` | ❌ |
| `LLM_SYNTHESIS_TEMP` | LLM 答案合成溫度 | `0.5` | ❌ |

**使用位置**：
- `rag-orchestrator` - 智能路由決策

**路徑決策邏輯**：
```
相似度 ≥ 0.75 → 快速路徑（直接返回，不呼叫 LLM）
0.55 ≤ 相似度 < 0.75 → LLM 參數注入（溫度 0.1）
相似度 < 0.55 → 完整 LLM 生成（溫度 0.5）
```

**範例**：
```bash
FAST_PATH_THRESHOLD=0.75
TEMPLATE_MIN_SCORE=0.55
TEMPLATE_MAX_SCORE=0.75
LLM_PARAM_INJECTION_TEMP=0.1
LLM_SYNTHESIS_TEMP=0.5
```

**效能影響**：
- 快速路徑可節省 90% LLM API 成本
- 平均回應時間從 2-3 秒降至 0.5-1 秒

---

## 💡 意圖建議配置 ⭐ NEW (Phase 3)

### 自動意圖建議

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `INTENT_SUGGESTION_TEMP` | 意圖建議溫度 | `0.2` | ❌ |
| `INTENT_SUGGESTION_MAX_TOKENS` | 意圖建議最大 tokens | `800` | ❌ |
| `INTENT_SUGGESTION_SIMILARITY_THRESHOLD` | 🆕 語義相似度去重閾值 | `0.80` | ❌ |

**使用位置**：
- `rag-orchestrator` - 未釐清問題自動建議意圖

**說明**：
- 當問題無法分類為現有意圖時，系統會建議新的意圖
- 低溫度（0.2）確保建議穩定且精準
- 🆕 **語義相似度去重**：新建議與現有pending建議相似度 ≥ 0.80 時，更新頻率而非新增重複建議
  - 使用 pgvector 餘弦相似度比對 `suggested_embedding` 欄位
  - 降低閾值會提高去重靈敏度（更容易判定為重複）
  - 提高閾值會降低去重靈敏度（僅非常相似的才判定為重複）

**範例**：
```bash
INTENT_SUGGESTION_TEMP=0.2
INTENT_SUGGESTION_MAX_TOKENS=800
INTENT_SUGGESTION_SIMILARITY_THRESHOLD=0.80  # 語義去重閾值（推薦 0.75-0.85）
```

---

## ❓ 未釐清問題配置 ⭐ NEW (Phase 3)

### 語義去重閾值

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `UNCLEAR_SEMANTIC_THRESHOLD` | 語義相似度閾值 | `0.80` | ❌ |
| `UNCLEAR_PINYIN_THRESHOLD` | 拼音相似度閾值 | `0.80` | ❌ |

**使用位置**：
- `rag-orchestrator` - 未釐清問題去重

**說明**：
- 新問題與現有未釐清問題相似度 ≥ 0.80 視為重複
- 同時檢查語義（embedding）和拼音相似度
- 避免相似問題重複提交到審核中心

**範例**：
```bash
UNCLEAR_SEMANTIC_THRESHOLD=0.80
UNCLEAR_PINYIN_THRESHOLD=0.80
```

---

### 知識優先級配置

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `PRIORITY_BOOST` | 優先級加成值 | `0.15` | ❌ |
| `PRIORITY_QUALITY_THRESHOLD` | 優先級品質門檻 | `0.70` | ❌ |

**使用位置**：
- `rag-orchestrator` - RAG 向量檢索引擎

**說明**：
- `PRIORITY_BOOST`: 對標記為優先的知識加分（固定加成值）
- `PRIORITY_QUALITY_THRESHOLD`: 品質門檻，只有原始相似度 >= 此值的答案才能獲得優先級加分
- **條件式加分機制**：防止低品質答案濫用優先級

**加分邏輯**：
```
最終分數 = 原始相似度 * 意圖係數 +
          (priority > 0 且 原始相似度 >= 0.70 ? 0.15 : 0)
```

**效果範例**（假設無意圖加成）：

| 原始分數 | 是否優先 | 品質門檻 | 最終分數 | 說明 |
|---------|---------|---------|---------|------|
| 0.60 | 是 | 0.70 | 0.60 | 低於門檻，不加分 ❌ |
| 0.65 | 是 | 0.70 | 0.65 | 低於門檻，不加分 ❌ |
| 0.70 | 是 | 0.70 | 0.85 | 達到門檻，+0.15 ✅ |
| 0.75 | 是 | 0.70 | 0.90 | 高品質，+0.15 ✅ |
| 0.80 | 是 | 0.70 | 0.95 | 高品質，+0.15 ✅ |

**範例**：
```bash
PRIORITY_BOOST=0.15                  # 加分值 0.15
PRIORITY_QUALITY_THRESHOLD=0.70      # 品質門檻 0.70
```

---

## 🧪 回測框架變數

### 回測配置

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `BACKTEST_SELECTION_STRATEGY` | 測試選擇策略 | `full` | ❌ |
| `BACKTEST_QUALITY_MODE` | 品質評估模式 | `basic` | ❌ |
| `BACKTEST_USE_DATABASE` | 是否使用資料庫載入測試 | `false` | ❌ |
| `BACKTEST_NON_INTERACTIVE` | 非互動模式 | `false` | ❌ |
| `BACKTEST_SAMPLE_SIZE` | 樣本數量限制 | 無限制 | ❌ |
| `BACKTEST_INCREMENTAL_LIMIT` | 增量測試數量 | `100` | ❌ |
| `BACKTEST_FAILED_LIMIT` | 失敗測試數量 | `50` | ❌ |

**詳細說明**：請參閱 [回測環境變數參考](../BACKTEST_ENV_VARS.md)

## 🐳 前端開發變數

### Node.js 環境

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `NODE_ENV` | Node.js 環境模式 | `production` | ❌ |

**可選值**：
- `development` - 開發模式（熱重載、詳細錯誤）
- `production` - 生產模式（優化、壓縮）

## 🛠️ 其他變數

### 專案配置

| 變數名 | 說明 | 預設值 | 必需 |
|--------|------|--------|------|
| `PROJECT_ROOT` | 專案根目錄路徑 | 自動檢測 | ❌ |

**使用位置**：
- `knowledge-admin-api` - 回測框架執行時需要專案路徑

## 📝 .env 文件範例

### 最小配置（僅必需變數）

```bash
# OpenAI API Key
OPENAI_API_KEY=sk-proj-your-api-key-here
```

### 完整配置（所有變數）⭐ 更新至 Phase 3

```bash
# ==========================================
# OpenAI API
# ==========================================
OPENAI_API_KEY=sk-proj-your-api-key-here

# ==========================================
# PostgreSQL 資料庫
# ==========================================
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aichatbot_admin
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password

# ==========================================
# Redis 連線
# ==========================================
REDIS_HOST=localhost
REDIS_PORT=6379

# ==========================================
# Redis 緩存配置（Phase 3 三層架構）
# ==========================================
CACHE_ENABLED=true
CACHE_TTL_QUESTION=3600       # Layer 1 問題緩存（1小時）
CACHE_TTL_VECTOR=7200         # Layer 2 向量緩存（2小時）
CACHE_TTL_RAG_RESULT=1800     # Layer 3 RAG 結果緩存（30分鐘）

# ==========================================
# API URLs（本地開發）
# ==========================================
EMBEDDING_API_URL=http://localhost:5001/api/v1/embeddings
RAG_API_URL=http://localhost:8100
KNOWLEDGE_ADMIN_API_URL=http://localhost:8000/api

# ==========================================
# AI 模型配置
# ==========================================
OPENAI_MODEL=gpt-3.5-turbo    # 主 LLM 模型

# 意圖分類器（Phase 3）
INTENT_CLASSIFIER_MODEL=gpt-3.5-turbo
INTENT_CLASSIFIER_TEMPERATURE=0.1
INTENT_CLASSIFIER_MAX_TOKENS=500

# 知識生成
KNOWLEDGE_GEN_MODEL=gpt-3.5-turbo

# 規格書轉換
DOCUMENT_CONVERTER_MODEL=gpt-4o

# ==========================================
# RAG 檢索配置（Phase 3）
# ==========================================
RAG_SIMILARITY_THRESHOLD=0.6

# ==========================================
# 答案合成配置（Phase 3 SOP 整合）
# ==========================================
ENABLE_ANSWER_SYNTHESIS=true
SYNTHESIS_THRESHOLD=0.99
SYNTHESIS_MIN_RESULTS=2
SYNTHESIS_MAX_RESULTS=5
SOP_SIMILARITY_SCORE=0.70

# ==========================================
# 信心度評估（Phase 3）
# ==========================================
CONFIDENCE_HIGH_THRESHOLD=0.85
CONFIDENCE_MEDIUM_THRESHOLD=0.70

# ==========================================
# 條件式優化配置（Phase 3 智能路由）
# ==========================================
FAST_PATH_THRESHOLD=0.75
TEMPLATE_MIN_SCORE=0.55
TEMPLATE_MAX_SCORE=0.75
LLM_PARAM_INJECTION_TEMP=0.1
LLM_SYNTHESIS_TEMP=0.5

# ==========================================
# 意圖建議配置（Phase 3）
# ==========================================
INTENT_SUGGESTION_TEMP=0.2
INTENT_SUGGESTION_MAX_TOKENS=800

# ==========================================
# 未釐清問題配置（Phase 3）
# ==========================================
UNCLEAR_SEMANTIC_THRESHOLD=0.80
UNCLEAR_PINYIN_THRESHOLD=0.80

# ==========================================
# 回測框架
# ==========================================
BACKTEST_SELECTION_STRATEGY=incremental
BACKTEST_QUALITY_MODE=basic
BACKTEST_USE_DATABASE=true
BACKTEST_NON_INTERACTIVE=true

# ==========================================
# 前端開發
# ==========================================
NODE_ENV=development
```

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

- [Docker Compose 指南](./DOCKER_COMPOSE_GUIDE.md)
- [回測環境變數參考](../BACKTEST_ENV_VARS.md)
- [快速開始指南](../../QUICKSTART.md)
- [開發工作流程](./DEVELOPMENT_WORKFLOW.md)

---

## 📊 環境變數統計

| 類別 | 變數數量 | Phase |
|-----|---------|-------|
| OpenAI API | 1 | Phase 1 |
| PostgreSQL | 5 | Phase 1 |
| Redis 連線 | 2 | Phase 1 |
| **Redis 緩存** ⭐ | **4** | **Phase 3** |
| API URLs | 3 | Phase 1 |
| **LLM 模型** ⭐ | **5** | **Phase 1 + 3** |
| **RAG 檢索** ⭐ | **1** | **Phase 3** |
| **答案合成** ⭐ | **5** | **Phase 3** |
| **信心度評估** ⭐ | **2** | **Phase 3** |
| **條件式優化** ⭐ | **5** | **Phase 3** |
| **意圖建議** ⭐ | **2** | **Phase 3** |
| **未釐清問題** ⭐ | **2** | **Phase 3** |
| 回測框架 | 7 | Phase 2 |
| 前端開發 | 1 | Phase 1 |
| **總計** | **45** | - |

**Phase 3 新增**: **23 個環境變數** ⭐

---

## 🔄 版本歷史

### v3.0 (2025-10-22) - Phase 3 完整更新

**新增環境變數（23 個）**：
- ✅ Redis 緩存配置（4 個）- 三層緩存架構
- ✅ LLM 模型配置（4 個）- 意圖分類器獨立配置
- ✅ RAG 檢索配置（1 個）- 相似度閾值
- ✅ 答案合成配置（5 個）- SOP 整合
- ✅ 信心度評估（2 個）- 高/中信心度閾值
- ✅ 條件式優化（5 個）- 智能路由策略
- ✅ 意圖建議（2 個）- 自動建議配置
- ✅ 未釐清問題（2 個）- 語義去重閾值

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
