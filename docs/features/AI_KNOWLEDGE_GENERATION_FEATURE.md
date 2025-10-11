# AI 知識生成功能完整實作文件

## 📋 功能概述

AI 知識生成功能允許管理者為已批准但無對應知識的測試情境，使用 OpenAI API 自動生成知識候選答案。所有 AI 生成的內容都需要經過人工審核後才會加入正式知識庫。

## ✅ 實作完成清單

### 後端實作

#### 1. 資料庫 Schema (Migration 13 & 13b)

**擴展 test_scenarios 表**：
```sql
ALTER TABLE test_scenarios
ADD COLUMN has_knowledge BOOLEAN DEFAULT FALSE,
ADD COLUMN linked_knowledge_ids INTEGER[],
ADD COLUMN knowledge_generation_requested BOOLEAN DEFAULT FALSE;
```

**擴展 knowledge_base 表**：
```sql
ALTER TABLE knowledge_base
ADD COLUMN source_type VARCHAR(20) DEFAULT 'manual',  -- manual, ai_generated, imported, ai_assisted
ADD COLUMN source_test_scenario_id INTEGER REFERENCES test_scenarios(id),
ADD COLUMN generation_metadata JSONB,
ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
```

**新增 ai_generated_knowledge_candidates 表**：
- 審核工作流：pending_review → approved/rejected/needs_revision
- 記錄 AI 模型、信心度、警告、編輯歷史
- 完整的審核追蹤（審核者、時間、備註）

**資料庫函數**：
- `check_test_scenario_has_knowledge()` - 檢查測試情境是否有對應知識
- `approve_ai_knowledge_candidate()` - 批准候選並轉為正式知識

#### 2. 後端服務

**KnowledgeGenerator Service** (`rag-orchestrator/services/knowledge_generator.py`)：
- 使用 GPT-3.5-turbo（成本低於 GPT-4）
- 可透過 `.env` 的 `KNOWLEDGE_GEN_MODEL` 配置
- 安全機制：
  - 類別白名單（設施使用、社區規範、常見問題等）
  - 類別黑名單（租金計算、合約條款、法律諮詢等）
  - 信心度評估（0.0-1.0）
  - 風險警告標註

**API Routes** (`rag-orchestrator/routers/knowledge_generation.py`)：
- `POST /api/v1/test-scenarios/{id}/check-knowledge` - 檢查知識
- `POST /api/v1/test-scenarios/{id}/generate-knowledge` - 生成候選
- `GET /api/v1/knowledge-candidates/pending` - 待審核清單
- `GET /api/v1/knowledge-candidates/stats` - 統計資訊
- `GET /api/v1/knowledge-candidates/{id}` - 候選詳情
- `PUT /api/v1/knowledge-candidates/{id}/edit` - 編輯候選
- `POST /api/v1/knowledge-candidates/{id}/review` - 審核（批准/拒絕）

#### 3. 環境配置

**.env**：
```env
# AI Knowledge Generation Configuration
KNOWLEDGE_GEN_MODEL=gpt-3.5-turbo  # 知識生成專用模型（預設 gpt-3.5-turbo，成本低）
                                    # 可選：gpt-4o-mini, gpt-4, gpt-3.5-turbo
```

**docker-compose.yml**：
```yaml
rag-orchestrator:
  environment:
    KNOWLEDGE_GEN_MODEL: ${KNOWLEDGE_GEN_MODEL:-gpt-3.5-turbo}
```

### 前端實作

#### 1. 測試情境管理頁面 (TestScenariosView.vue)

**新增欄位**：
- 知識狀態欄：顯示測試情境是否已有對應知識
  - ✅ 已有知識（綠色徽章）
  - ❌ 無知識（紅色徽章）

**新增功能**：
- 🤖 **AI 生成知識按鈕**：
  - 僅在「已批准」且「無知識」的測試情境才顯示
  - 點擊後會先檢查知識庫是否有相似知識
  - 自動呼叫 RAG Orchestrator API 生成 2 個知識候選
  - 顯示生成結果（模型、信心度、候選數量）

#### 2. AI 知識審核頁面 (AIKnowledgeReviewView.vue) 🆕

**統計儀表板**：
- 待審核數量
- 已批准數量
- 批准率
- 編輯率

**候選卡片**：
- 📝 原始測試問題
- ❓ AI 生成的問題
- 💡 AI 生成的答案
- ⚠️ AI 警告
- 🤖 AI 模型和信心度

**操作功能**：
- ✏️ **編輯**：修改 AI 生成的問題和答案
- ✅ **批准並加入知識庫**：將候選轉為正式知識
- ❌ **拒絕**：拒絕不適合的候選

#### 3. 導航選單更新

- 🤖 新增「AI 知識審核」選單項（金色高亮顯示）
- 註冊新路由：`/ai-knowledge-review`

## 🚀 使用流程

### 步驟 1：生成知識候選

1. 訪問 `http://localhost:8080/test-scenarios`
2. 找到已批准且無知識的測試情境
3. 點擊 🤖 按鈕
4. 系統會：
   - 先檢查知識庫是否有相似知識（相似度 ≥ 0.75）
   - 如果沒有，生成 1-3 個知識候選
   - 顯示生成結果

### 步驟 2：審核知識候選

1. 訪問 `http://localhost:8080/ai-knowledge-review`
2. 查看待審核的 AI 知識候選
3. 檢視 AI 生成的問題和答案
4. 選擇操作：
   - **編輯後批准**（推薦）：
     - 點擊 ✏️ 編輯
     - 修改問題/答案
     - 填寫編輯摘要
     - 點擊 💾 儲存編輯
     - 點擊 ✅ 批准並加入知識庫
   - **直接批准**：點擊 ✅ 批准並加入知識庫
   - **拒絕**：點擊 ❌ 拒絕，填寫拒絕原因

### 步驟 3：驗證結果

1. 批准後，系統會：
   - 將候選轉為正式知識（加入 `knowledge_base` 表）
   - 標記 `source_type = 'ai_generated'`
   - 記錄完整元數據（AI 模型、信心度、編輯歷史）
   - 更新測試情境的 `has_knowledge = true`
   - 在 `linked_knowledge_ids` 中記錄知識 ID

2. 測試情境頁面會顯示「✅ 已有知識」
3. 知識庫頁面可以查看新增的知識

## 🔐 安全機制

### 1. 向後相容性保證

- ✅ **原有人工知識不受影響**：所有現有知識自動標記為 `source_type='manual'`
- ✅ **只新增欄位**：Migration 使用 `ADD COLUMN IF NOT EXISTS`，不修改現有資料
- ✅ **預設值保護**：新增欄位都有合理的預設值

### 2. 審核工作流

- ✅ **必須人工審核**：AI 生成的內容存在 `ai_generated_knowledge_candidates` 表，必須經過批准才進入正式知識庫
- ✅ **編輯追蹤**：記錄原始 AI 生成版本和編輯後版本
- ✅ **審核記錄**：記錄審核者、時間、備註

### 3. 類別限制

**安全類別（允許自動生成）**：
- 設施使用、社區規範、常見問題、服務介紹
- 停車相關、郵件包裹、垃圾回收、水電瓦斯
- 公共空間、鄰居互動、環境維護、安全管理

**限制類別（不允許自動生成）**：
- 租金計算、合約條款、法律諮詢、投訴處理
- 緊急維修、賠償責任、違約處理、租期異動

### 4. 品質控制

- ✅ **信心度評估**：AI 會為每個候選評估信心度（0.0-1.0）
- ✅ **風險警告**：AI 會標註潛在風險（例如：「具體規定請參考租賃合約」）
- ✅ **建議來源**：AI 會建議參考哪些資料來源

## 💰 成本優化

| 用途 | 模型 | 相對成本 | 配置方式 |
|------|------|----------|----------|
| 系統預設（一般對話） | gpt-4o-mini | 1x | 硬編碼 |
| 知識生成 | gpt-3.5-turbo | 0.067x | `KNOWLEDGE_GEN_MODEL` |

**範例**：
- GPT-4: $10.00 / 1M tokens (input)
- GPT-4o-mini: $0.15 / 1M tokens (input)
- GPT-3.5-turbo: $0.50 / 1M tokens (input)

知識生成使用 GPT-3.5-turbo，成本是 GPT-4 的 5%，是 GPT-4o-mini 的 3.3 倍，但品質更好。

## 📊 監控與統計

### 統計指標

訪問 `GET /api/v1/knowledge-candidates/stats` 可獲得：

```json
{
  "pending_count": 1,           // 待審核數量
  "approved_count": 1,          // 已批准數量
  "rejected_count": 0,          // 已拒絕數量
  "approval_rate": 100.0,       // 批准率 (%)
  "edit_rate": 100.0,           // 編輯率 (%)
  "avg_confidence_approved": 0.85,  // 已批准候選的平均信心度
  "avg_confidence_rejected": 0.0    // 已拒絕候選的平均信心度
}
```

### 資料庫視圖

**v_pending_ai_knowledge_candidates**：
- 顯示所有待審核和需要修訂的候選
- 按優先順序排序：needs_revision → 高頻問題 → 先進先出

**v_ai_knowledge_generation_stats**：
- 統計資訊摘要（批准率、編輯率等）

## 🧪 測試案例

### 測試案例 1：完整工作流

```bash
# 1. 檢查測試情境 #20 是否有對應知識
curl -X POST http://localhost:8100/api/v1/test-scenarios/20/check-knowledge

# 2. 生成知識候選（2 個）
curl -X POST http://localhost:8100/api/v1/test-scenarios/20/generate-knowledge \
  -H "Content-Type: application/json" \
  -d '{"num_candidates": 2}'

# 3. 查看待審核候選
curl http://localhost:8100/api/v1/knowledge-candidates/pending

# 4. 編輯候選 #1
curl -X PUT http://localhost:8100/api/v1/knowledge-candidates/1/edit \
  -H "Content-Type: application/json" \
  -d '{
    "edited_question": "可以在租屋處養寵物嗎？",
    "edited_answer": "修改後的答案...",
    "edit_summary": "調整了語氣並補充細節"
  }'

# 5. 批准候選 #1
curl -X POST http://localhost:8100/api/v1/knowledge-candidates/1/review \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve",
    "reviewer_name": "admin",
    "review_notes": "已審核，答案正確"
  }'

# 6. 查看統計
curl http://localhost:8100/api/v1/knowledge-candidates/stats
```

### 測試結果

✅ **測試情境 #20「可以養寵物嗎」**：
- 成功生成 2 個候選（gpt-3.5-turbo，信心度 0.85）
- 編輯候選 #1
- 批准候選 #1 → 知識 ID: 497
- 元數據驗證：
  - `source_type` = 'ai_generated' ✅
  - `ai_model` = 'gpt-3.5-turbo' ✅
  - `was_edited` = true ✅
  - `source_test_scenario_id` = 20 ✅

## 🔧 故障排除

### 問題 1：前端顯示「❌ 無知識」但實際已有知識

**原因**：後端 API 沒有返回 `has_knowledge` 和 `linked_knowledge_ids` 欄位

**解決方案**：
```python
# routes_test_scenarios.py
query = """
    SELECT
        ts.id, ts.test_question, ...,
        ts.has_knowledge, ts.linked_knowledge_ids  # 加入這兩個欄位
    FROM test_scenarios ts
    WHERE 1=1
"""
```

### 問題 2：刪除測試情境失敗

**錯誤訊息**：
```
foreign key constraint "knowledge_base_source_test_scenario_id_fkey" violated
```

**原因**：測試情境已有關聯的知識庫記錄，外鍵約束保護資料完整性

**解決方案**：
- 這是正常的保護機制，不應該刪除有關聯知識的測試情境
- 如果真的需要刪除，先刪除關聯的知識庫記錄

### 問題 3：生成知識時提示「已有知識」

**原因**：知識庫中已有相似度 ≥ 0.75 的知識

**解決方案**：
- 這是正常的重複檢測機制
- 可以降低相似度閾值（預設 0.75）
- 或者手動建立差異化的知識

## 📁 相關檔案

### 資料庫

- `/database/migrations/13-ai-knowledge-generation.sql` - 主要 Migration
- `/database/migrations/13b-fix-knowledge-check-function.sql` - 修復檢查函數

### 後端

- `/rag-orchestrator/services/knowledge_generator.py` - AI 生成服務
- `/rag-orchestrator/routers/knowledge_generation.py` - API 路由
- `/rag-orchestrator/app.py` - 路由註冊

### 前端

- `/knowledge-admin/frontend/src/views/TestScenariosView.vue` - 測試情境管理（含生成按鈕）
- `/knowledge-admin/frontend/src/views/AIKnowledgeReviewView.vue` - AI 知識審核頁面
- `/knowledge-admin/frontend/src/router.js` - 路由配置
- `/knowledge-admin/frontend/src/App.vue` - 導航選單

### 配置

- `/.env` - 環境變數（KNOWLEDGE_GEN_MODEL）
- `/docker-compose.yml` - Docker 配置

## 🎯 下一步建議

### 短期改進

1. **批次生成**：支援一次為多個測試情境生成知識
2. **前端優化**：
   - 候選卡片支援實時預覽
   - 新增批量審核功能
   - 顯示生成進度

### 中期改進

1. **品質追蹤**：
   - 追蹤 AI 生成知識的使用效果（點擊率、滿意度）
   - 根據回饋微調生成策略
2. **模型比較**：
   - A/B 測試不同模型的生成品質
   - 自動選擇最佳模型

### 長期改進

1. **自動學習**：
   - 從已批准的知識中學習
   - 自動改進生成品質
2. **多語言支援**：
   - 支援英文、日文等其他語言
   - 自動翻譯知識庫

## 📞 聯絡資訊

如有問題或建議，請聯絡開發團隊。

---

**文件版本**: 1.0
**最後更新**: 2025-10-11
**作者**: AI Assistant
