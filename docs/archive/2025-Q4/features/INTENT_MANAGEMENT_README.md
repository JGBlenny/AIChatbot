# 意圖管理系統完整文檔

## 📚 文檔總覽

本意圖管理系統已完整實作，包含後端 API、OpenAI 整合和前端管理頁面。

### 文檔清單

1. **[intent_management_phase_b_complete.md](../../completion_reports/intent_management_phase_b_complete.md)** ⭐
   - Phase B 完整實作報告
   - 後端 API 詳細文檔
   - 測試結果和驗證
   - 資料庫使用情況
   - OpenAI Function Calling 設計

2. **[FRONTEND_USAGE_GUIDE.md](../../../guides/development/FRONTEND_USAGE_GUIDE.md)** ⭐
   - 前端頁面使用指南
   - 4 個管理頁面說明
   - 完整測試流程
   - API 端點對應

---

## 🎯 快速開始

### 1. 開啟前端頁面
```bash
# 瀏覽器訪問
open http://localhost:8080/
```

### 2. 導航選項
- **知識庫** (`/`) - 原有知識庫管理
- **意圖管理** (`/intents`) - 管理所有意圖
- **建議審核** (`/suggested-intents`) - 審核 OpenAI 建議
- **業務範圍** (`/business-scope`) - 配置業務範圍

### 3. 測試新意圖建議功能
```bash
# 提問一個業務相關但 unclear 的問題
curl -X POST http://localhost:8100/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "房東可以隨時進入我的房間嗎？",
    "user_id": "test_user"
  }'

# 查看建議意圖
open http://localhost:8080/suggested-intents
```

---

## 📁 專案結構

### 後端服務
```
rag-orchestrator/
├── services/
│   ├── intent_classifier.py          # 意圖分類器（修改）
│   ├── intent_manager.py              # 意圖管理服務（新增）
│   └── intent_suggestion_engine.py    # 意圖建議引擎（新增）
├── routers/
│   ├── chat.py                        # Chat API（修改）
│   ├── intents.py                     # 意圖管理 API（新增）
│   ├── suggested_intents.py           # 建議意圖 API（新增）
│   └── business_scope.py              # 業務範圍 API（新增）
└── tests/
    ├── test_intent_manager.py         # IntentManager 測試
    └── test_intent_suggestion.py      # IntentSuggestionEngine 測試
```

### 前端頁面
```
knowledge-admin/frontend/
├── src/
│   ├── router.js                      # Vue Router 配置（新增）
│   ├── App.vue                        # 主框架（修改）
│   ├── main.js                        # 入口（修改）
│   └── views/
│       ├── KnowledgeView.vue          # 知識庫管理
│       ├── IntentsView.vue            # 意圖管理（新增）
│       ├── SuggestedIntentsView.vue   # 建議審核（新增）
│       └── BusinessScopeView.vue      # 業務範圍（新增）
└── package.json                       # 加入 vue-router
```

### 資料庫
```
database/migrations/
├── 04-create-intent-management-tables.sql  # 意圖管理 Schema
└── insert_intents.sql                       # 初始意圖資料
```

---

## 🔧 核心功能

### 1. 意圖分類（IntentClassifier）
- 從資料庫載入意圖配置
- 使用 OpenAI Function Calling 分類問題
- 支援動態重載配置
- 自動記錄使用次數

### 2. 意圖管理（IntentManager）
- 完整 CRUD 操作
- 啟用/停用控制
- 優先級管理
- 統計資訊

### 3. 意圖建議引擎（IntentSuggestionEngine）⭐
- 分析 unclear 問題
- OpenAI 判斷業務相關性
- 自動建議新意圖
- 支援採納/拒絕/合併
- 頻率追蹤

### 4. 業務範圍配置
- 內部/外部範圍切換
- 可自訂業務描述
- 可自訂 OpenAI Prompt
- 動態生效

---

## 🎨 前端頁面功能

### 意圖管理頁面
✅ 查看所有意圖
✅ 新增/編輯/刪除意圖
✅ 啟用/停用切換
✅ 統計資訊展示
✅ 手動重載配置

### 建議審核頁面
✅ 顯示 OpenAI 建議
✅ 顯示觸發問題
✅ 顯示相關性分數
✅ 顯示推理說明
✅ 一鍵採納建議
✅ 拒絕建議
✅ 統計資訊

### 業務範圍配置頁面
✅ 查看所有範圍
✅ 切換業務範圍
✅ 編輯配置
✅ 即時生效

---

## 📊 完成度

| 階段 | 內容 | 進度 |
|------|------|------|
| Phase A | 資料庫 + 基礎服務 | ✅ 100% |
| Phase B | OpenAI 新意圖發現 | ✅ 100% |
| Phase C | 前端 UI | ✅ 100% |
| **總計** | **完整系統** | **✅ 100%** |

---

## 🧪 測試

### 執行測試腳本
```bash
# 測試 IntentManager
docker exec aichatbot-rag-orchestrator python3 /app/tests/test_intent_manager.py

# 測試 IntentSuggestionEngine
docker exec aichatbot-rag-orchestrator python3 /app/tests/test_intent_suggestion.py
```

### 手動測試流程
詳見 [FRONTEND_USAGE_GUIDE.md](../../../guides/development/FRONTEND_USAGE_GUIDE.md) 的「測試流程」章節。

---

## 🔗 API 文檔

### Swagger UI
http://localhost:8100/docs

### 主要端點
- **意圖管理**: `/api/v1/intents`
- **建議審核**: `/api/v1/suggested-intents`
- **業務範圍**: `/api/v1/business-scope`
- **Chat**: `/api/v1/chat`

詳細 API 說明請參考 [intent_management_phase_b_complete.md](../../completion_reports/intent_management_phase_b_complete.md)。

---

## 🚀 部署狀態

### 服務狀態
```bash
docker-compose ps
```

應該看到：
- ✅ rag-orchestrator (http://localhost:8100)
- ✅ knowledge-admin-web (http://localhost:8080)
- ✅ knowledge-admin-api (http://localhost:8000)
- ✅ postgres
- ✅ redis
- ✅ embedding-api

### 健康檢查
```bash
curl http://localhost:8100/api/v1/health
```

應該回傳：
```json
{
  "status": "healthy",
  "services": {
    "intent_classifier": "ready",
    "suggestion_engine": "ready (Phase B)"
  }
}
```

---

## 💡 使用建議

1. **意圖命名**: 使用清晰的中文名稱（如「退租流程」而非「intent_1」）
2. **關鍵字設定**: 每個意圖 5-10 個關鍵字為佳
3. **信心度閾值**: knowledge 用 0.80，data_query 用 0.75
4. **優先級設定**: 重要意圖設定較高優先級（如 10）
5. **業務範圍**: 定期檢視並優化業務描述，提高 OpenAI 判斷準確度

---

## 🎯 下一步建議

雖然系統已完整實作，未來可考慮：

1. **知識庫自動分類**: 新增知識時自動分配到對應意圖
2. **意圖分析報表**: 統計最常用意圖、時間趨勢
3. **批次操作**: 支援批次啟用/停用、批次刪除
4. **權限管理**: 不同角色有不同的操作權限
5. **審核工作流**: 建議意圖的多級審核流程

---

## 📞 支援

如有問題，請參考：
1. [Phase B 完整報告](../../completion_reports/intent_management_phase_b_complete.md)
2. [前端使用指南](../../../guides/development/FRONTEND_USAGE_GUIDE.md)
3. API 文檔: http://localhost:8100/docs

---

**文檔更新時間**: 2025-10-10
**系統版本**: 1.0.0
**完成度**: 100%
