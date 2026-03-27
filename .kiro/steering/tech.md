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
  - GPT-4o: LLM 驅動的答案優化、知識生成、分類聚類
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
│   └── utils/ (工具函數)
├── aichatbot-postgres (PostgreSQL with pgvector)
├── aichatbot-embedding-service (向量嵌入服務)
├── aichatbot-knowledge-admin (管理後台)
└── aichatbot-semantic-model (語義模型服務)
```

### 分層架構 (RAG Orchestrator)
```
Routers (路由層)
  ├── chat.py - 聊天對話 API
  ├── knowledge.py - 知識管理 API
  ├── platform_sop.py - SOP 編排 API
  ├── forms.py - 表單管理 API
  ├── api_endpoints.py - 外部 API 管理
  ├── lookup.py - Lookup 表管理
  └── ...

Services (服務層)
  ├── rag_engine.py - RAG 檢索引擎
  ├── intent_classifier.py - 意圖分類器
  ├── confidence_evaluator.py - 信心度評估器
  ├── llm_answer_optimizer.py - LLM 答案優化器
  ├── sop_orchestrator.py - SOP 編排器
  ├── form_manager.py - 表單管理器
  ├── knowledge_completion_loop/ - 知識完善迴圈
  │   ├── coordinator.py - 迴圈協調器
  │   ├── gap_analyzer.py - 缺口分析器
  │   ├── action_type_classifier.py - 動作類型分類器
  │   ├── gap_classifier.py - 缺口聚類分類器
  │   ├── knowledge_generator.py - 知識生成器
  │   └── cost_tracker.py - 成本追蹤器
  └── ...

Models (模型層)
  ├── Pydantic models for request/response validation
  └── Database schema definitions

Utils (工具層)
  ├── db_utils.py - 資料庫工具
  ├── embedding_utils.py - 向量嵌入工具
  └── sop_utils.py - SOP 工具
```

## 開發慣例

### 非同步優先
- **API 路由**: 使用 `async def` 定義所有端點
- **資料庫操作**: 優先使用 `asyncpg` 進行非同步查詢
- **HTTP 請求**: 使用 `aiohttp` 或 `httpx` 進行非同步請求
- **同步場景**: 回測腳本、知識完善迴圈等批次處理可使用同步 API (psycopg2)

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
- **向量搜尋**: 使用 PostgreSQL pgvector 的 `<=>` 運算子進行相似度搜尋
- **相似度閾值**: 預設 0.6，可依業務需求調整
- **優先級加成**: 支援對高品質答案 (>0.7) 進行固定加成 (+0.15)

### 快取策略
- **Redis**: 使用 Redis 快取常用查詢結果
- **TTL**: 設定合理的過期時間
- **失效策略**: 知識更新時主動清除相關快取

### AI 呼叫慣例
- **OpenAI Client**: 使用 `openai.OpenAI(api_key=...)` 初始化
- **模型選擇**:
  - GPT-4o: 複雜任務（答案合成、知識生成、分類）
  - GPT-4o-mini: 簡單任務（分類、標題生成）
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
- **整合測試**: 測試端到端流程（回測、知識完善迴圈）
- **批次測試**: 使用 `run_backtest_db.py` 進行批量回測

### 文檔與註釋
- **Docstrings**: 所有公開函數使用 Google 風格的 docstrings
- **類型註解**: 使用 Python type hints (`typing` 模組)
- **中文註釋**: 允許使用繁體中文進行詳細註釋
- **英文程式碼**: 變數名、函數名使用英文

## 命名慣例

### 檔案與目錄
- **服務**: `{service_name}.py` (如 `rag_engine.py`)
- **路由**: `{resource}.py` (如 `chat.py`, `knowledge.py`)
- **測試**: `test_{module}.py` (如 `test_rag_engine.py`)
- **配置**: `{config_name}_config.py` (如 `deduplication_config.py`)

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
- **路徑**: `/api/v1/{resource}` (如 `/api/v1/chat`, `/api/v1/knowledge`)
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
- **批次限制**: 使用環境變數控制批次大小 (BACKTEST_BATCH_LIMIT)
- **快取**: 對常用查詢結果進行快取
- **限流**: 避免短時間內大量 API 呼叫（使用 sleep、tenacity）

### 向量搜尋優化
- **檢索限制**: RAG_RETRIEVAL_LIMIT 預設為 5，降低檢索成本
- **閾值過濾**: 只返回相似度 > threshold 的結果
- **語義重排序**: 可選功能，預設關閉，避免額外成本
