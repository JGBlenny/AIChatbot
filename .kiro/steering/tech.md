# Tech Steering

## 技術棧

### 後端核心
- **Python 3.x**: 主要開發語言
- **FastAPI**: 高效能非同步 Web 框架
- **Uvicorn**: ASGI 伺服器
- **Pydantic**: 資料驗證與設定管理

### 資料庫
- **PostgreSQL**: 主要資料庫，使用 asyncpg (非同步) 和 psycopg2 (同步)
- **pgvector**: 向量相似度搜尋擴充功能
- **Redis**: 快取層，用於提升查詢效能

### AI/ML
- **OpenAI**:
  - 對話回合（`AGENT_MODEL`）、查詢改寫、知識生成、文件轉換：各自的 env 與程式預設見「AI 呼叫慣例」
  - Embedding API: 向量嵌入生成
- **sentence-transformers**: 本地語義重排序模型
- **torch**: PyTorch，支援 sentence-transformers

### 中文處理
- **jieba**: 中文分詞
- **pypinyin**: 拼音轉換

### 資料處理
- **pandas**: 資料分析與處理
- **numpy**: 數值計算
- **openpyxl, xlsxwriter**: Excel 檔案處理
- **python-docx**: Word 文檔處理
- **beautifulsoup4, lxml**: HTML 解析

### 基礎設施
- **Docker & Docker Compose**: 容器化部署
- **AWS S3 (boto3)**: 視頻檔案儲存
- **python-dotenv**: 環境變數管理

### 工具庫
- **aiohttp, httpx, requests**: HTTP 客戶端（同步/非同步）
- **tenacity**: 重試機制
- **tqdm**: 進度條顯示
- **pyyaml**: YAML 設定檔解析

## 架構設計

### 微服務架構
```
AIChatbot (Multi-container Docker Compose)
├── aichatbot-rag-orchestrator (FastAPI - 核心服務)
│   ├── routers/ (API 路由層)
│   ├── services/ (業務邏輯層)
│   ├── models/ (資料模型)
│   ├── config/ (配置管理)
│   └── tools/ (離線工具與評估腳本)
├── aichatbot-postgres (PostgreSQL with pgvector)
├── aichatbot-embedding-service (向量嵌入服務)
├── aichatbot-knowledge-admin (管理後台)
└── aichatbot-semantic-model (語義模型服務)
```

### 分層架構 (RAG Orchestrator)
```
Routers (路由層)
  ├── agent.py - `/api/v1/agent/openapi.json`・`/health`・`/trace`（`APIRouter(prefix="/api/v1/agent")`）；對話入口 `/mcp` 不在這裡，由 `rag-orchestrator/app.py` 以 `Mount("/mcp", app=_mcp_facade.build_asgi_app(_mcp_server))` 掛上，應用本體在 `services/agent/mcp_facade.py`
  ├── agent_entry.py - ⚠️ strangler 遷移橋，上游已滅、無 APIRouter、⛔ 掛不起來
  ├── forms.py - 表單後台 CRUD（對話填單引擎已退役）
  ├── platform_sop.py - 平台管理員的 SOP 範本後台 CRUD（15 條路由）
  ├── api_endpoints.py - 外部 API 管理
  ├── lookup.py - Lookup 表管理
  └── ...（完整清單見 .kiro/steering/structure.md，該樹依檔案系統維護）

Services (服務層)
  ├── services/agent/ - ⭐ 現役核心（30 檔＋canon／tools 兩個子套件）
  │   ├── runtime.py - AgentRuntime.run_turn；建構依賴裡⛔ 沒有任何協定或門面
  │   ├── mcp_facade.py - /mcp 門面（AgentRuntime 的四個門面之一）
  │   ├── turn_segments.py / turn_context.py / exit_gates.py - 一回合的四段
  │   ├── verifier.py - Output Verifier（逐句驗引用）
  │   ├── canon/ - 知識路 A：git canon 正本 → FineIndex → CandidateSelector
  │   └── tools/ - registry.py（in-process 呼叫）／jgb2.py（六域 16 face）／kb.py（知識路 B）
  ├── services/jgb/ - 六域 face builders ＋ jgb2 轉接
  ├── base_retriever.py / vendor_knowledge_retriever_v2.py / semantic_reranker.py - 檢索
  ├── decision_layer.py - 檢索門檻
  ├── knowledge_completion_loop/ - ⚠️ 程式只剩 embedding_client.py（另有 `__init__.py`、`create_missing_indexes.sql`），執行面已刪
  └── ...

Models (模型層)
  ├── Pydantic models for request/response validation
  └── Database schema definitions

Utils（無獨立 `utils/` 目錄，檔案在 `services/` 下）
  ├── services/db_utils.py - 資料庫工具
  ├── services/embedding_utils.py - 向量嵌入工具
  └── services/sop_utils.py - SOP 工具
```

## 開發慣例

### 非同步優先
- **API 路由**: 使用 `async def` 定義所有端點
- **資料庫操作**: 優先使用 `asyncpg` 進行非同步查詢
- **HTTP 請求**: 使用 `aiohttp` 或 `httpx` 進行非同步請求
- **同步場景**: 回測腳本等批次處理可使用同步 API (psycopg2)

### 資料庫連接管理
- **連接池**: 使用 `asyncpg.create_pool()` 建立連接池
- **生命週期管理**: 在 FastAPI lifespan 中初始化與關閉連接池
- **同步連接**: 批次腳本使用 `psycopg2.connect()` 直接連接

### 錯誤處理
- **HTTPException**: 統一使用 FastAPI 的 HTTPException 回報錯誤
- **重試機制**: 使用 `tenacity` 處理暫時性錯誤（網路、API 限流）
- **日誌記錄**: 使用 `print()` 進行即時日誌輸出（簡化調試）

### 配置管理
- **環境變數**: 使用 `.env` 檔案管理環境變數
- **預設值**: 所有配置都應有合理的預設值 (`os.getenv("KEY", "default")`)
- **資料庫配置**: vendor_configs 表動態管理業者級配置

### 向量處理
- **Embedding API**: 統一透過 `embedding_utils.get_embedding_client()` 取得客戶端
- **Embedding 輸入規則**: 只用標題生成 embedding（知識庫用 `question_summary`，SOP 用 `item_name`），keywords 不混入 embedding，透過獨立的關鍵字搜尋機制處理
- **SOP Embedding**: 統一由 `sop_embedding_generator.py` 生成（primary=item_name, fallback=content），所有寫入 vendor_sop_items 的路徑都觸發此生成器
- **向量搜尋**: 使用 PostgreSQL pgvector 的 `<=>` 運算子進行相似度搜尋

### Retriever Pipeline 分數欄位（重要）

> 詳見 [docs/architecture/retriever-pipeline.md](../../docs/architecture/retriever-pipeline.md)

- **分離式分數欄位**（2026-04 重構）：每個 pipeline stage 寫入獨立欄位，不互相覆寫
  - `vector_similarity`：純向量 cosine 分數（Stage 1 `_vector_search`）
  - `keyword_score`：關鍵字 normalized 分數（Stage 2 `_keyword_search`，不再 cap 0.70）
  - `keyword_boost`：關鍵字命中加成倍率（Stage 3 `_apply_keyword_boost`）
  - `rerank_score`：bge-reranker-base 輸出（Stage 4 `_apply_semantic_reranker`）
  - `similarity`：final 組合分數，由 Stage 5 `_finalize_scores` 依階層公式計算
  - `score_source`：`"rerank"` / `"keyword"` / `"vector"`，debug 用
- **檢索策略**: Stage 1 vector → Stage 2 keyword_fallback → Stage 3 keyword_boost → Stage 4 reranker → Stage 5 finalize → application threshold 過濾 → top_k
- **Final similarity 公式**（階層式）：
  - 有 rerank → `0.1 × vector + 0.9 × rerank`
  - 有 keyword（無 rerank）→ `min(1.0, max(vector, keyword) × boost)`
  - 純 vector → `min(1.0, vector × boost)`
- **SQL 不再過濾 threshold**：`_vector_search` 用 LIMIT（SOP 50、KB 100）控制回傳量，application 端用 `similarity >= threshold` 過濾
- **閾值對應欄位**：
  - `KB_SIMILARITY_THRESHOLD`（預設 0.65，`services/decision_layer.py`）比對 `similarity`（final）
  - ⛔ `PERFECT_MATCH_THRESHOLD`／`SOP_SIMILARITY_THRESHOLD`／`HIGH_QUALITY_THRESHOLD`／`SYNTHESIS_THRESHOLD` 無程式讀者（舊鏈已刪）
- **優先級加成**: 支援對高品質答案 (>0.7) 進行固定加成 (+0.15)

### 快取策略
- **Redis**: 使用 Redis 快取常用查詢結果
- **TTL**: 設定合理的過期時間
- **失效策略**: 知識更新時主動清除相關快取

### AI 呼叫慣例
- **OpenAI Client**: 使用 `openai.OpenAI(api_key=...)` 初始化
- **模型選擇**（預設值，可用環境變數覆蓋）:
  - 對話回合：`AGENT_MODEL`→`OPENAI_MODEL`→`gpt-4o-mini`（`services/agent/runtime.py`）；採用哪個模型是決策，見 `.claude/DECISIONS.md` DSP-075／DSP-080
  - 文件轉換（`services/document_converter_service.py`）：`DOCUMENT_CONVERTER_MODEL`→`KNOWLEDGE_GEN_MODEL`→`gpt-4o`；知識匯入（`services/knowledge_import_service.py`）同一鏈
  - 知識生成（`services/knowledge_generator.py`）：`KNOWLEDGE_GEN_MODEL`，程式預設 `gpt-4o-mini`
  - 查詢改寫: QUERY_REWRITE_MODEL（fallback: OPENAI_MODEL），temperature **0**
  - ⛔ 意圖分類（INTENT_CLASSIFIER_MODEL）已無程式讀者——分類器 2026-09-11 刪除
- **Temperature**:
  - 0.0-0.3: 確定性任務（分類、提取）
  - 0.7-0.9: 創造性任務（生成、重寫）
- **重試**: 使用 `tenacity` 處理 API 限流與暫時性錯誤
- **成本控制**:
  - 追蹤 token 使用與費用
  - 支援批次大小限制
  - 提供停止條件（成本上限、時間限制）

### 測試慣例
- **測試檔案**: 命名為 `test_*.py`
- **單元測試**: 測試個別服務邏輯
- **整合測試**: 測試端到端流程

### 文檔與註釋
- **Docstrings**: 所有公開函數使用 Google 風格的 docstrings
- **類型註解**: 使用 Python type hints (`typing` 模組)
- **中文註釋**: 允許使用繁體中文進行詳細註釋
- **英文程式碼**: 變數名、函數名使用英文

## 命名慣例

### 檔案與目錄
- **服務**: `{service_name}.py`（如 `unclear_question_manager.py`、`semantic_reranker.py`）
- **路由**: `{resource}.py`（如 `forms.py`、`vendors.py`）
- **測試**: `test_{module}_req.py`（`_req` 對應 `@pytest.mark.req(...)` 追溯標記，
  見 `.kiro/steering/testing-code.md`；如 `tests/unit/security/test_api_key_auth_req.py`）
- **配置**: `{config_name}_config.py`（⚠️ 目前無存活範例；`config/` 只有 `business_types.py` 與 `agent_verifier_rules.json`）

### 變數與函數
- **snake_case**: 變數、函數、方法使用小寫加底線
- **PascalCase**: 類別名稱使用大寫駝峰
- **UPPER_CASE**: 常數使用全大寫加底線
- **私有成員**: 使用單底線前綴 `_private_method`

### 資料庫
- **表名**: 複數形式，小寫加底線 (如 `test_scenarios`, `vendor_sop_items`)
- **欄位**: 小寫加底線 (如 `vendor_id`, `created_at`)
- **外鍵**: `{table}_id` (如 `vendor_id`, `category_id`)
- **時間戳**: 使用 `created_at`, `updated_at`

### API 路由
- **RESTful**: 使用標準 REST 動詞 (GET, POST, PUT, PATCH, DELETE)
- **路徑**: `/api/v1/{resource}` (如 `/api/v1/agent`, `/api/v1/knowledge`；⛔ `/api/v1/chat` 無對應 router)
- **參數**: query parameters 使用 snake_case

## 部署

### Docker 慣例
- **命名**: `aichatbot-{service}` (如 `aichatbot-rag-orchestrator`)
- **網路**: 使用 Docker Compose 內部網路
- **環境變數**: 透過 `.env` 注入容器
- **資料持久化**: PostgreSQL 資料使用 named volume

### 環境變數管理
- **本地開發**: `.env` 檔案（不納入版控）
- **生產環境**: 透過 Docker Compose 或 K8s ConfigMap/Secret 注入
- **必要變數**: OPENAI_API_KEY, DB_HOST, DB_PASSWORD
- **可選變數**: 所有可選變數都應有預設值

## 效能考量

### 資料庫優化
- **索引**: 在 vendor_id, created_at, status 等常用過濾欄位建立索引
- **向量索引**: pgvector 使用 IVFFlat 或 HNSW 索引加速相似度搜尋
- **連接池**: 合理設定 min_size 和 max_size，避免連接耗盡

### API 成本控制
- **快取**: 對常用查詢結果進行快取
- **限流**: 避免短時間內大量 API 呼叫（使用 sleep、tenacity）

### 向量搜尋優化
- **閾值過濾**: 只返回相似度 > threshold 的結果
- **語義重排序**: 可選功能，預設關閉，避免額外成本

---

## 2026-07 現況增補（本節為最新，與上文衝突時以本節與 `docs/architecture/SYSTEM_ARCHITECTURE.md` 為準）

- **對話面向體系（🔴 2026-09-12 逐項對碼更正）**：**16 個 face、六域**
  （帳單 5／合約 5／帳號 2／電表 1／物件 1／修繕 2），在註冊時由
  `_jgb2_spec(domain, sorted(builders.keys()))` **現算**——⛔ 不是「資料驅動、一筆設定＝一個面向」，
  ⛔ 也不是 21＋、⛔ 不是五域。加一個 face 要改 `services/jgb/<域>.py` 的 `*_FACE_BUILDERS`（寫程式）。
  機械判定用 `*_FACE_BUILDERS` 決定性算 facts、LLM 只照 facts 組話（這條仍成立）。
  - **寫入類**改走 `services/agent/tools/action.py` 的兩支（`bill_due_extend`／`repair_create`）
    ＋ `services/agent/confirm_card.py::render` 產確認卡；⛔ 不再有 `grounding_scope.execute_endpoint`
    這種配置驅動（`conversational_engine.py` 已於 2026-09-11 刪除）。
  - **可見性**改為 `AGENT_WRITE_TOOLS_ENABLED` AND `ToolSpec.stage`（DSP-038-1）。
  - **SOP 對話路徑零讀取**：後台 CRUD 仍活，但改 SOP 不影響機器人回答。
  - 擴充判準見 `docs/guides/development/how-to-add-a-query-capability.md`。
- **資料體系分工（定案）**：`vendor_configs`＝通用單值參數（{{param}} 模板）；`lookup_tables`＝案場級（Excel 匯入＋錨點）；SOP＝b2c 專用（b2b 不走）；jgb API＝個資（role_id+user_id 雙證）。
- **計量與額度**：usage_events 每請求計量（token/成本/內部流量標記）；vendor_quotas 月額度（達限攔截/警示寄信）。
- **品質三層**：unit（make test-unit）／系統回測（迴圈＋多輪模擬＋v3 評審＋金標，按受眾分庫）／不變量稽核（make audit，修一類 bug＝加一條）。驗收鐵則：改引擎行為以系統路徑實跑收案。
- **單一真相源**：`docs/architecture/SYSTEM_ARCHITECTURE.md`（全景）；`docs/architecture-overview.md` 現為指路檔；部署走 `docs/deployment-runbook.md`。
