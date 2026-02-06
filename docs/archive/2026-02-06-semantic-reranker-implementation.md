# 語義重排序實作說明

## 實作總結

### 問題背景
系統在處理「電費帳單寄送區間」等查詢時，原本會返回不相關的「租屋須知」內容，而非觸發正確的表單（ID 1296）。

### 根本原因
1. **不是系統問題**：系統邏輯正確，能找到正確的知識 ID 1296
2. **是測試問題**：API 請求缺少必要的 `session_id` 和 `user_id` 參數
3. **安全機制**：系統設計上表單觸發需要 session 追蹤，缺少時自動降級為文字回答

### 解決方案
實作了基於 BAAI/bge-reranker-base 的語義重排序服務，提升檢索準確度。

## 技術架構

### 兩階段檢索
```
查詢 → [第一階段] 向量檢索（快速） → [第二階段] 語義重排序（精準） → 最終結果
```

### 關鍵元件
1. **語義模型服務** (`semantic_model/`)
   - 使用 BAAI/bge-reranker-base 預訓練模型
   - FastAPI 提供 REST API
   - Docker 容器化部署

2. **RAG 整合** (`rag-orchestrator/services/semantic_reranker.py`)
   - 連接語義模型服務
   - 處理重排序請求
   - 容錯降級機制

## 實際效果

### 測試案例：「電費帳單寄送區間」
- ✅ ID 1296（電費查詢表單）：0.687 → **0.974**（重排序後）
- ✅ ID 677（電費帳單解釋）：0.601 → 0.725
- ❌ ID 1657（租屋須知）：0.466（分數低，正確排除）

### API 使用要點

**正確的請求格式：**
```json
{
  "vendor_id": 1,
  "message": "電費帳單寄送區間",
  "session_id": "unique-session-id",  // 必須
  "user_id": "unique-user-id"        // 必須
}
```

缺少 `session_id` 或 `user_id` 時，表單會降級為文字回答。

## 配置說明

### Docker Compose 環境變數
```yaml
# 啟用語義重排序
USE_SEMANTIC_RERANK: true
ENABLE_RERANKER: true
ENABLE_KNOWLEDGE_RERANKER: true

# 相似度閾值
SOP_SIMILARITY_THRESHOLD: 0.75
KB_SIMILARITY_THRESHOLD: 0.55
HIGH_QUALITY_THRESHOLD: 0.8
```

## 部署狀態
- ✅ 語義模型服務運行中（port 8002）
- ✅ RAG Orchestrator 已整合
- ✅ 所有查詢變化都能正確觸發表單

## 注意事項
1. 首次啟動需下載模型（約 1.1GB）
2. 前端整合時確保每個請求都包含 session_id 和 user_id
3. 系統有健康檢查機制，服務不可用時自動降級