# 研究記錄：pipeline-health-dashboard

> **建立時間**：2026-04-18T06:25:00Z
> **探索類型**：Light Discovery（既有系統擴展）

---

## 探索範圍

分析既有健康檢查基礎設施、前端 UI 模式、認證機制，確定新功能的整合策略。

## 關鍵發現

### 1. 既有健康檢查端點

- `GET /api/v1/health`：直接掛在 FastAPI app，測試 DB 連線 + 列出服務狀態
- `GET /api/v1/cache/health`：在 cache router，測試 Redis PING + 寫入測試
- `SemanticReranker._check_service()`：HTTP GET 到 semantic model，2s timeout
- Embedding API：`GET /api/v1/health` 回傳 `{status, redis, model}`
- LLM（OpenAI）：無健康檢查，僅 try-catch 在呼叫時

### 2. 前端 UI 模式

- CacheManagementView.vue 是最佳參考：fetch → 狀態卡片 → 手動重新整理
- 使用 emoji 狀態圖示（✅❌⚠️）+ CSS class（`status-healthy`）
- Grid 佈局：`repeat(auto-fit, minmax(250px, 1fr))`
- 無 polling，手動觸發

### 3. Router 與認證

- 後端：`APIRouter(prefix="/api/v1")` + `app.include_router()`
- 前端：router.js 配置 `meta: { requiresAuth: true }`
- API 路徑：前端用 `/rag-api/v1/*`，經 Nginx/Vite proxy 到 `rag-orchestrator:8100/api/v1/*`

## 設計決策

### D1: 單一聚合端點 vs 多端點
- **決定**：單一 `GET /api/v1/system/pipeline-health` 端點，內部並行檢查所有元件
- **理由**：減少前端請求數，確保一致性快照；各元件檢查有獨立 timeout 不互相阻塞

### D2: 端到端測試端點
- **決定**：獨立 `POST /api/v1/system/pipeline-e2e-test` 端點
- **理由**：端到端測試耗時較長（需實際跑 pipeline），不應混在快速健康檢查中

### D3: 元件分類（核心 vs 非核心）
- **決定**：核心 = PostgreSQL, Embedding API, LLM API；非核心 = Redis, Semantic Reranker
- **理由**：符合實際降級行為 — Redis 掛了有 DB fallback，Reranker 掛了用原始排序

### D4: LLM 健康檢查方式
- **決定**：呼叫 OpenAI API 的 `models.list()` 而非發送實際 completion
- **理由**：models.list 速度快、不消耗 token、能驗證 API key 有效性

### D5: Vector/Keyword Search 測試
- **決定**：歸入端到端測試，不在元件健康檢查中單獨測試
- **理由**：Vector Search 需要 DB + Embedding 同時可用才有意義，本質上是整合測試而非元件檢查

## 合成結論

### 泛化
- 所有元件檢查共用相同的結果結構（名稱、狀態、延遲、版本、錯誤），可設計統一的 checker 介面

### Build vs Adopt
- 使用 `asyncio.gather` 並行執行檢查（已有依賴）
- 無需引入額外健康檢查框架

### 簡化
- 移除原需求中 Vector Search / Keyword Search 的獨立檢查，併入端到端測試（減少重複）
- 前端沿用 CacheManagementView 的 fetch + card 模式，無需新 UI 框架
