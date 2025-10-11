# 意圖管理系統 - Phase B 完成報告

## ✅ 已完成功能總覽

### Phase A: 資料庫 + 基礎服務 (100% 完成)
1. ✅ 資料庫 Schema（3個新表 + 2個修改表）
2. ✅ IntentManager 服務（完整 CRUD）
3. ✅ IntentClassifier 修改（從資料庫載入）
4. ✅ YAML 遷移腳本（10個意圖導入）
5. ✅ 完整測試驗證

### Phase B: 新意圖發現機制 (100% 完成)
1. ✅ IntentSuggestionEngine 服務
2. ✅ Chat API 整合
3. ✅ Suggested Intents API Router
4. ✅ Business Scope API Router
5. ✅ Intents API Router
6. ✅ 完整測試驗證

---

## 📋 Phase B 核心功能詳解

### 1. IntentSuggestionEngine 服務
**檔案**: `/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/intent_suggestion_engine.py`

**核心功能**:
- `analyze_unclear_question()`: 使用 OpenAI Function Calling 判斷unclear問題是否屬於業務範圍
- `record_suggestion()`: 記錄建議意圖到資料庫（支援重複檢測、頻率累加）
- `get_suggestions()`: 取得建議列表（支援狀態過濾、多種排序）
- `approve_suggestion()`: 採納建議並自動建立新意圖
- `reject_suggestion()`: 拒絕建議
- `merge_suggestions()`: 合併多個相似建議為單一意圖
- `reload_business_scope()`: 動態重新載入業務範圍配置

**OpenAI Function Calling 設計**:
```python
# 分析unclear問題，返回：
{
    "is_relevant": bool,           # 是否與業務相關
    "relevance_score": float,      # 相關性分數 (0-1)
    "suggested_intent": {          # 建議的意圖
        "name": str,
        "type": str,               # knowledge/data_query/action/hybrid
        "description": str,
        "keywords": List[str]
    },
    "reasoning": str,              # OpenAI 推理說明
    "should_record": bool          # 是否應該記錄（score >= 0.7）
}
```

**業務範圍配置**:
- 當前啟用: "包租代管業者（外部使用）"
- 可切換: "系統商（內部使用）"
- 配置內容: 業務描述、範例問題、範例意圖、自訂prompt

### 2. Chat API 整合
**檔案**: `/Users/lenny/jgb/AIChatbot/rag-orchestrator/routers/chat.py`

**新增流程**:
```python
if intent_result['intent_name'] == 'unclear' or intent_result['intent_type'] == 'unclear':
    # 分析問題
    analysis = suggestion_engine.analyze_unclear_question(
        question=request.question,
        user_id=request.user_id
    )

    # 如果屬於業務範圍，記錄建議
    if analysis.get('should_record'):
        suggested_intent_id = suggestion_engine.record_suggestion(
            question=request.question,
            analysis=analysis,
            user_id=request.user_id
        )
```

**ChatResponse 新增欄位**:
- `is_new_intent_suggested`: bool
- `suggested_intent_id`: Optional[int]

**conversation_logs 新增欄位**:
- `suggested_intent_id`: 建議意圖 ID
- `is_new_intent_suggested`: 是否建議新意圖

### 3. API 端點總覽

#### Suggested Intents API (`/api/v1/suggested-intents`)
- `GET /suggested-intents` - 取得建議列表（支援狀態過濾、排序）
- `GET /suggested-intents/stats` - 建議統計資訊
- `GET /suggested-intents/{id}` - 取得特定建議
- `POST /suggested-intents/{id}/approve` - 採納建議（自動建立意圖 + 重載分類器）
- `POST /suggested-intents/{id}/reject` - 拒絕建議
- `POST /suggested-intents/merge` - 合併建議

#### Business Scope API (`/api/v1/business-scope`)
- `GET /business-scope` - 取得所有業務範圍
- `GET /business-scope/active` - 取得當前啟用的業務範圍
- `GET /business-scope/{scope_name}` - 取得特定業務範圍
- `PUT /business-scope/{scope_name}` - 更新業務範圍配置
- `POST /business-scope/switch` - 切換業務範圍（自動重載建議引擎）

#### Intents API (`/api/v1/intents`)
- `GET /intents` - 取得所有意圖（支援過濾、排序）
- `GET /intents/stats` - 意圖統計資訊
- `GET /intents/{id}` - 取得特定意圖
- `POST /intents` - 新增意圖（自動重載分類器）
- `PUT /intents/{id}` - 更新意圖（自動重載分類器）
- `DELETE /intents/{id}` - 刪除意圖（軟刪除，自動重載分類器）
- `PATCH /intents/{id}/toggle` - 啟用/停用意圖（自動重載分類器）
- `POST /intents/reload` - 手動重新載入意圖配置

---

## 🧪 測試驗證結果

### 1. Health Check
```bash
curl http://localhost:8100/api/v1/health
```
✅ 結果:
```json
{
    "status": "healthy",
    "services": {
        "suggestion_engine": "ready (Phase B)"
    }
}
```

### 2. IntentSuggestionEngine 測試
**測試腳本**: `/tmp/test_intent_suggestion.py`

**測試結果**:
| 問題 | 相關性 | 分數 | 結果 |
|------|--------|------|------|
| "你們公司的logo顏色是什麼？" | ❌ 不相關 | 0.10 | ✅ 正確拒絕 |
| "今天天氣如何？" | ❌ 不相關 | 0.00 | ✅ 正確拒絕 |
| "房東可以隨時進入我的房間嗎？" | ✅ 相關 | 0.80 | ✅ **成功建議新意圖** |

**建議意圖詳情**:
```json
{
    "id": 1,
    "suggested_name": "房東進入房間的權利",
    "suggested_type": "knowledge",
    "suggested_description": "解釋房東在租約中進入租客房間的權利和限制",
    "suggested_keywords": ["房東", "租約", "進入房間", "租客權利", "隱私權"],
    "relevance_score": 0.8,
    "status": "pending"
}
```

### 3. 採納建議測試
```bash
curl -X POST http://localhost:8100/api/v1/suggested-intents/1/approve \
  -d '{"reviewed_by": "admin", "create_intent": true}'
```
✅ 結果:
- 建立新意圖 ID: 12
- 自動重載 IntentClassifier
- 建議狀態更新為 "approved"

### 4. 新意圖驗證
```bash
curl http://localhost:8100/api/v1/intents/12
```
✅ 結果:
```json
{
    "id": 12,
    "name": "房東進入房間的權利",
    "type": "knowledge",
    "keywords": ["房東", "租約", "進入房間", "租客權利", "隱私權"],
    "is_enabled": true,
    "created_by": "admin"
}
```

---

## 🔄 完整工作流程

### 使用者提問 → 意圖建議 → 採納 → 新意圖生效

1. **使用者提問**:
   ```
   "房東可以隨時進入我的房間嗎？"
   ```

2. **IntentClassifier 分類**:
   - 結果: `intent_type = "unclear"` （找不到匹配的現有意圖）

3. **IntentSuggestionEngine 分析**:
   - OpenAI 判斷: 與業務範圍相關（包租代管）
   - 相關性分數: 0.80
   - 建議新增意圖: "房東進入房間的權利"

4. **記錄到資料庫**:
   - 表: `suggested_intents`
   - 狀態: `pending`
   - 頻率: 1

5. **管理員審核**:
   - 在 Knowledge Admin 查看建議
   - 決定採納/拒絕/合併

6. **採納建議**:
   - 自動建立新意圖 → `intents` 表
   - IntentClassifier 自動重載
   - 建議狀態更新為 `approved`

7. **下次相同問題**:
   - IntentClassifier 成功匹配新意圖
   - 不再觸發 unclear 流程

---

## 📊 資料庫使用情況

### suggested_intents 表
```sql
SELECT COUNT(*) FROM suggested_intents;
-- 結果: 1

SELECT * FROM suggested_intents WHERE status = 'pending';
-- 結果: 0 (已採納)

SELECT * FROM suggested_intents WHERE status = 'approved';
-- 結果: 1
```

### intents 表
```sql
SELECT COUNT(*) FROM intents WHERE is_enabled = true;
-- 結果: 11 (原10個 + 新增1個)

SELECT name FROM intents ORDER BY id DESC LIMIT 1;
-- 結果: "房東進入房間的權利"
```

### business_scope_config 表
```sql
SELECT scope_name, is_active FROM business_scope_config;
-- 結果:
--   internal: false
--   external: true (當前使用「包租代管業者」範圍)
```

---

## 🎯 OpenAI 相關性判斷標準

### 判斷 Prompt (from business_scope_config)
```
判斷以下問題是否與「包租代管服務」相關。
包租代管業務包含：租約管理、繳費問題、維修報修、退租流程、
合約規定、設備使用、物件資訊等。
```

### 判斷標準
- **相關性 ≥ 0.7**: 屬於業務範圍，建議新增意圖
- **相關性 0.4-0.7**: 可能相關，但需要更多資訊（目前不記錄）
- **相關性 < 0.4**: 不相關，不建議新增

### 實際案例分析
| 問題 | 判斷 | 理由 |
|------|------|------|
| "logo顏色" | 0.10 不相關 | 品牌識別，非業務範圍 |
| "停車位租金" | 0.30 不相關 | OpenAI認為停車位非包租代管核心業務（可調整） |
| "寵物飼養" | 0.20 不相關 | OpenAI認為寵物規定非包租代管核心（可調整） |
| "房東進入權限" | 0.80 **相關** | ✅ 屬於租約規定和租客權利 |

**注意**: 停車位和寵物問題的判斷可能過於嚴格，可透過:
1. 調整 `business_description` 明確包含這些情境
2. 修改 `relevance_prompt` 提供更詳細的判斷標準
3. 降低 `relevance_threshold` (目前 0.7)

---

## 🔧 配置與自訂

### 1. 調整業務範圍
```bash
curl -X PUT http://localhost:8100/api/v1/business-scope/external \
  -H "Content-Type: application/json" \
  -d '{
    "business_description": "包租代管客服系統，包含：租約管理、繳費問題、維修報修、退租流程、合約規定、設備使用、物件資訊、**停車位管理、寵物政策**等",
    "updated_by": "admin"
  }'
```

### 2. 切換到內部使用（系統商）
```bash
curl -X POST http://localhost:8100/api/v1/business-scope/switch \
  -H "Content-Type: application/json" \
  -d '{
    "scope_name": "internal",
    "updated_by": "admin"
  }'
```

### 3. 調整相關性閾值
修改 `intent_suggestion_engine.py`:
```python
# 第 278 行
analysis["should_record"] = is_relevant and relevance_score >= 0.6  # 原 0.7
```

---

## 🚀 啟動狀態

### Docker 容器
```bash
docker ps | grep rag-orchestrator
# ✅ aichatbot-rag-orchestrator   Up 10 minutes   0.0.0.0:8100->8100/tcp
```

### 服務啟動日誌
```
🚀 初始化 RAG Orchestrator...
✅ 資料庫連接池已建立
✅ 從資料庫載入 10 個意圖
✅ 意圖分類器已初始化
✅ RAG 檢索引擎已初始化
✅ 信心度評估器已初始化
✅ 未釐清問題管理器已初始化
✅ LLM 答案優化器已初始化 (Phase 3)
✅ 意圖建議引擎已初始化 (Phase B)
🎉 RAG Orchestrator 啟動完成！（含 Phase 3 LLM 優化 + Phase B 意圖建議）
📝 API 文件: http://localhost:8100/docs
```

---

## 📝 待完成: Phase C - 前端 UI

### 需要新增的前端頁面

#### 1. 意圖管理頁面 (`IntentsView.vue`)
**功能**:
- 查看所有意圖列表
- 新增/編輯/刪除意圖
- 啟用/停用意圖
- 查看意圖統計（使用次數、知識庫覆蓋率）
- 手動重載意圖配置

**API 使用**:
- `GET /api/v1/intents`
- `POST /api/v1/intents`
- `PUT /api/v1/intents/{id}`
- `PATCH /api/v1/intents/{id}/toggle`
- `GET /api/v1/intents/stats`

#### 2. 建議意圖審核頁面 (`SuggestedIntentsView.vue`)
**功能**:
- 查看待審核的建議意圖列表
- 顯示觸發問題、相關性分數、OpenAI 推理
- 採納建議（自動建立意圖）
- 拒絕建議
- 合併多個相似建議
- 查看已處理的建議歷史

**API 使用**:
- `GET /api/v1/suggested-intents`
- `POST /api/v1/suggested-intents/{id}/approve`
- `POST /api/v1/suggested-intents/{id}/reject`
- `POST /api/v1/suggested-intents/merge`
- `GET /api/v1/suggested-intents/stats`

#### 3. 業務範圍配置頁面 (`BusinessScopeView.vue`)
**功能**:
- 查看所有業務範圍配置
- 切換業務範圍（內部/外部）
- 編輯業務描述、範例問題、範例意圖
- 自訂 OpenAI 判斷 Prompt

**API 使用**:
- `GET /api/v1/business-scope`
- `GET /api/v1/business-scope/active`
- `PUT /api/v1/business-scope/{scope_name}`
- `POST /api/v1/business-scope/switch`

### 前端技術棧
- Vue 3 + Composition API
- Vue Router 4（已加入 package.json）
- Axios（已安裝）
- 簡潔的 CSS 樣式（參考現有 style.css）

### 下一步驟
1. 安裝 dependencies: `docker exec aichatbot-knowledge-admin npm install`
2. 建立 router 配置
3. 建立3個 View 元件
4. 修改 App.vue 加入導航選單
5. 建置並測試

---

## 📈 完成度總結

### Phase A: 100% ✅
- 資料庫 Schema ✅
- IntentManager 服務 ✅
- IntentClassifier 修改 ✅
- 完整測試 ✅

### Phase B: 100% ✅
- IntentSuggestionEngine ✅
- Chat API 整合 ✅
- Suggested Intents API ✅
- Business Scope API ✅
- Intents API ✅
- 完整測試 ✅

### Phase C: 10%（待完成前端）
- Router 配置 ⏳
- 意圖管理頁面 ⏳
- 建議審核頁面 ⏳
- 業務範圍配置頁面 ⏳

### 整體完成度: **70%**

---

## 🔗 相關檔案清單

### 後端服務
- `/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/intent_suggestion_engine.py` (新增)
- `/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/intent_manager.py` (新增)
- `/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/intent_classifier.py` (修改)

### API 路由
- `/Users/lenny/jgb/AIChatbot/rag-orchestrator/routers/suggested_intents.py` (新增)
- `/Users/lenny/jgb/AIChatbot/rag-orchestrator/routers/business_scope.py` (新增)
- `/Users/lenny/jgb/AIChatbot/rag-orchestrator/routers/intents.py` (新增)
- `/Users/lenny/jgb/AIChatbot/rag-orchestrator/routers/chat.py` (修改)
- `/Users/lenny/jgb/AIChatbot/rag-orchestrator/app.py` (修改)

### 資料庫
- `/Users/lenny/jgb/AIChatbot/database/migrations/04-create-intent-management-tables.sql`
- `/tmp/insert_intents.sql`

### 測試腳本
- `/tmp/test_intent_manager.py`
- `/tmp/test_intent_suggestion.py`

### 前端
- `/Users/lenny/jgb/AIChatbot/knowledge-admin/frontend/package.json` (修改 - 加入 vue-router)

---

## 🎉 成果展示

### 1. OpenAI 成功發現業務相關的新意圖
```
問題: "房東可以隨時進入我的房間嗎？"
↓
OpenAI 分析: 相關性 0.80，屬於租約規定和租客權利
↓
建議新增意圖: "房東進入房間的權利"
↓
管理員採納
↓
自動建立新意圖 + 重載分類器
```

### 2. 動態意圖管理
- 新增意圖後，IntentClassifier 自動重載
- 下次相同問題直接匹配新意圖
- 無需重啟服務

### 3. 業務範圍可配置
- 內部使用（系統商）vs 外部使用（包租代管）
- 可自訂業務描述和判斷標準
- 切換後自動生效

### 4. 完整的審核工作流
- 建議記錄 → 待審核 → 採納/拒絕 → 歷史追蹤
- 支援合併相似建議
- 頻率統計（相同問題累加）

---

**報告時間**: 2025-10-10
**Phase B 狀態**: ✅ 完成並測試通過
**下一步**: 完成 Phase C 前端 UI
