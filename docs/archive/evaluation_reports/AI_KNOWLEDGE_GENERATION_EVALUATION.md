# AI 自動生成知識庫資料 - 功能評估報告

**評估日期：** 2025-10-11
**評估者：** Claude
**需求來源：** 使用者提議

---

## 📋 需求摘要

**核心需求：**
> 當管理者批准一個測試問題時，如果知識庫沒有對應的知識，系統可以使用 OpenAI API 生成一份或多份候選答案供管理者審核，確認後加入知識庫。

**觸發條件：**
1. 測試情境狀態為 `approved`（已批准）
2. 知識庫中無對應答案（向量相似度 < 0.75）
3. 管理者主動觸發生成（或批准時自動提示）

**審核機制：**
- 🔒 **必須人工審核**：AI 生成的內容不會直接進入知識庫
- ✏️ **支援編輯修改**：管理者可編輯後再批准
- 📝 **記錄完整資訊**：保留 AI 模型、prompt、信心度等詳情

---

## ✅ 可行性評估

### 技術可行性：⭐⭐⭐⭐⭐ (5/5)

**理由：**
1. ✅ 已具備 OpenAI API 整合經驗（Embedding、LLM 優化）
2. ✅ 已有審核流程框架（test_scenarios 審核機制）
3. ✅ 已有向量相似度搜尋（pgvector + ivfflat）
4. ✅ 前端審核 UI 可重用（Vue 3 + Element UI）

**技術棧：**
- 後端：FastAPI + asyncpg + httpx
- AI：OpenAI GPT-3.5-turbo / GPT-4
- 資料庫：PostgreSQL + pgvector
- 前端：Vue 3 + Composition API

### 業務價值：⭐⭐⭐⭐ (4/5)

#### 優點

| 優點 | 說明 | 預估效益 |
|-----|------|---------|
| 🚀 **加速知識庫建設** | 減少人工撰寫時間 | 節省 60-80% 時間 |
| 📝 **提供寫作參考** | 即使不直接使用，也能啟發管理者 | 提升答案品質 |
| 🎯 **快速回應高頻問題** | 測試情境頻率高 = 使用者需求強烈 | 改善使用者體驗 |
| 📊 **保持品質控制** | 人工審核機制確保準確性 | 維持信任度 |
| 🔍 **可追溯性** | 記錄 AI 生成來源和修改歷史 | 利於審計和改進 |

#### 限制

| 限制 | 風險等級 | 緩解措施 |
|-----|---------|---------|
| ⚠️ 不能完全取代人工 | 中 | 必須人工審核 + 編輯 |
| ⚠️ 法律/合約類需謹慎 | 高 | 類別白名單機制 |
| ⚠️ AI 可能產生錯誤資訊 | 中 | 信心度評分 + 警告標註 |
| ⚠️ 成本考量（API 費用） | 低 | 使用 GPT-3.5-turbo（較便宜）|

### 風險等級：⭐⭐⭐ (3/5 - 中等風險)

**風險分析：**

#### 1. 準確性風險（中高）

**問題：** AI 可能產生錯誤、過時或不適用的資訊

**緩解措施：**
- ✅ 信心度評分（AI 自評 0.0-1.0）
- ✅ 人工審核機制（必須批准才能加入知識庫）
- ✅ 警告標註（AI 標註不確定之處）
- ✅ 類別白名單（只為低風險類別生成）

**白名單類別（安全）：**
```
✅ 設施使用
✅ 社區規範
✅ 常見問題
✅ 公共空間
✅ 垃圾處理
✅ 停車規定
```

**限制類別（不自動生成）：**
```
⛔ 租金計算    （需要精確數字）
⛔ 合約條款    （法律風險）
⛔ 退租流程    （涉及金錢）
⛔ 押金處理    （爭議敏感）
⛔ 法律諮詢    （專業要求高）
```

#### 2. 成本風險（低）

**預估成本：**

| 模型 | 每次生成成本 | 每月 100 次 | 每月 500 次 |
|-----|-------------|-----------|-----------|
| GPT-3.5-turbo | $0.002 | $0.20 | $1.00 |
| GPT-4 | $0.03 | $3.00 | $15.00 |

**建議：**
- 使用 **GPT-3.5-turbo**（成本僅 GPT-4 的 1/15）
- 設定每月生成次數上限（如：50 次）
- 重要類別才使用 GPT-4

#### 3. 過度依賴風險（中）

**問題：** 管理者可能過度信任 AI，降低審核標準

**緩解措施：**
- ✅ 明確標註「AI 生成」徽章
- ✅ 顯示信心度分數（<0.7 需特別注意）
- ✅ 提供「需要修訂」選項（而非直接批准）
- ✅ 定期檢視 AI 生成知識的使用者反饋

---

## 🏗️ 架構設計

### 系統架構圖

```
┌─────────────────────────────────────────────────────────────┐
│                      測試情境審核流程                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
                  test_scenario (status: pending_review)
                              ↓
                   管理者點擊「批准」按鈕
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 系統檢查：是否已有對應知識？                                   │
│ check_test_scenario_has_knowledge(scenario_id)               │
│                                                              │
│ 使用向量相似度搜尋（閾值 0.75）                                │
└─────────────────────────────────────────────────────────────┘
           ↓ YES                              ↓ NO
   ┌──────────────────┐           ┌──────────────────────┐
   │ 已有對應知識       │           │ 無對應知識              │
   │ 直接批准並關聯     │           │ 彈出提示對話框          │
   └──────────────────┘           └──────────────────────┘
                                              ↓
                              ┌─────────────────────────┐
                              │ 是否生成 AI 知識候選？    │
                              │                         │
                              │ [生成知識] [仍然批准]     │
                              └─────────────────────────┘
                                       ↓ 生成知識
                    ┌──────────────────────────────────────┐
                    │ OpenAI API 生成候選答案 (1-3 個)       │
                    │ - 使用結構化 prompt                    │
                    │ - 包含相關現有知識作為參考              │
                    │ - 返回信心度、警告、來源建議             │
                    └──────────────────────────────────────┘
                                       ↓
          ┌────────────────────────────────────────────────┐
          │ ai_generated_knowledge_candidates 表            │
          │ (status: pending_review)                       │
          │                                                │
          │ - 保留原始 AI 生成內容                          │
          │ - 提供編輯欄位                                  │
          │ - 記錄 AI 模型、prompt、信心度                   │
          └────────────────────────────────────────────────┘
                                       ↓
          ┌────────────────────────────────────────────────┐
          │ 前端：AI 知識審核 Tab                           │
          │                                                │
          │ 顯示：                                          │
          │ - AI 生成答案（只讀）                           │
          │ - 編輯區域（可修改）                            │
          │ - 信心度分數                                    │
          │ - 警告訊息                                      │
          │ - 建議來源                                      │
          │                                                │
          │ 操作：                                          │
          │ [✓ 批准] [✏️ 需要修訂] [✗ 拒絕]                 │
          └────────────────────────────────────────────────┘
                         ↓ 批准
          ┌────────────────────────────────────────────────┐
          │ approve_ai_knowledge_candidate()               │
          │                                                │
          │ 1. 決定使用原始版本或編輯版本                    │
          │ 2. 插入 knowledge 表（source_type: ai_generated)│
          │ 3. 記錄 generation_metadata (JSON)             │
          │ 4. 更新候選狀態為 approved                       │
          │ 5. 關聯到 test_scenario (linked_knowledge_ids) │
          └────────────────────────────────────────────────┘
                                       ↓
                          ✅ 知識已加入知識庫
```

### 資料庫架構

#### 新增表：`ai_generated_knowledge_candidates`

| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | SERIAL | 主鍵 |
| test_scenario_id | INTEGER | 來源測試情境 |
| question | TEXT | 問題（可編輯） |
| generated_answer | TEXT | AI 生成的原始答案 |
| confidence_score | DECIMAL(3,2) | 信心度 (0.00-1.00) |
| generation_prompt | TEXT | 使用的 prompt |
| ai_model | VARCHAR(50) | AI 模型名稱 |
| generation_reasoning | TEXT | AI 的推理過程 |
| suggested_sources | TEXT[] | 建議參考來源 |
| warnings | TEXT[] | 警告訊息 |
| status | VARCHAR(20) | 狀態（pending_review/needs_revision/approved/rejected） |
| reviewed_by | VARCHAR(100) | 審核者 |
| reviewed_at | TIMESTAMP | 審核時間 |
| review_notes | TEXT | 審核備註 |
| edited_question | TEXT | 編輯後的問題 |
| edited_answer | TEXT | 編輯後的答案 |
| edit_summary | TEXT | 編輯摘要 |

#### 擴展表：`test_scenarios`

| 新增欄位 | 類型 | 說明 |
|---------|------|------|
| has_knowledge | BOOLEAN | 是否已有對應知識 |
| linked_knowledge_ids | INTEGER[] | 關聯的知識 ID 陣列 |

#### 擴展表：`knowledge`

| 新增欄位 | 類型 | 說明 |
|---------|------|------|
| source_type | VARCHAR(20) | 來源類型（manual/ai_generated/imported） |
| source_test_scenario_id | INTEGER | 來源測試情境 ID |
| generation_metadata | JSONB | AI 生成詳情 |

### 核心函數

#### 1. `check_test_scenario_has_knowledge()`

**功能：** 檢查測試情境是否已有對應知識

```sql
SELECT * FROM check_test_scenario_has_knowledge(20, 0.75);

-- 返回：
-- has_knowledge: true/false
-- matched_knowledge_ids: {1, 5, 8}
-- match_count: 3
-- highest_similarity: 0.89
-- related_knowledge: [{...}, {...}]  -- JSON 格式，包含相關知識摘要
```

#### 2. `approve_ai_knowledge_candidate()`

**功能：** 批准 AI 候選並轉為正式知識

```sql
SELECT approve_ai_knowledge_candidate(
    candidate_id := 1,
    reviewed_by := 'admin_name',
    review_notes := '答案正確，已加入知識庫',
    use_edited := TRUE  -- 使用編輯後的版本
);

-- 返回：新建立的 knowledge.id
```

---

## 💡 實作建議

### Phase 1: MVP（最小可行產品）

**時程：** 3-5 天

**範圍：**
- ✅ 僅支援**安全類別**（設施使用、社區規範、常見問題）
- ✅ 使用 **GPT-3.5-turbo**（成本低）
- ✅ 生成 **2 個候選答案**（供比較）
- ✅ **必須人工審核**才能加入知識庫
- ✅ 明確標註「AI 生成」

**交付內容：**
1. ✅ 資料庫 migration（已完成）
2. ✅ 後端服務 `KnowledgeGenerator`（已完成）
3. API 端點：
   - `POST /test-scenarios/{id}/check-knowledge`
   - `POST /test-scenarios/{id}/generate-knowledge`
   - `GET /knowledge-candidates/pending`
   - `POST /knowledge-candidates/{id}/approve`
   - `POST /knowledge-candidates/{id}/reject`
4. 前端：「AI 知識審核」Tab

**成本預估：**
- 開發時間：3-5 天
- API 成本：每月 $5-20（假設 50-200 次生成）

### Phase 2: 優化（1-2 週後）

**新增功能：**
- 📊 **多候選比較**：並列顯示 3 個候選，選擇最佳
- 🔍 **自動品質檢查**：
  - 答案長度驗證（150-500 字）
  - 敏感詞檢測（避免「可能」「也許」過多）
  - 格式檢查（是否有明確結論）
- 📈 **統計儀表板**：
  - AI 生成通過率
  - 平均信心度
  - 編輯率（多少候選需要修改）
- 🎯 **批量生成**：為多個測試情境一次生成

### Phase 3: 進階（未來擴展）

**新增功能：**
- 🧠 **Few-shot learning**：使用現有知識作為範例（提升品質）
- 🔗 **自動關聯相關知識**：生成後自動建立知識間的關聯
- 🌐 **多語言支援**：生成英文版本（國際化）
- 📝 **持續學習**：根據使用者反饋改進 prompt

---

## ⚠️ 風險緩解措施

### 1. 類別白名單機制

```python
# knowledge_generator.py

safe_categories = [
    "設施使用",
    "社區規範",
    "常見問題",
    "公共空間",
    "垃圾處理",
    "停車規定"
]

restricted_categories = [
    "租金計算",   # 需要精確數字
    "合約條款",   # 法律風險
    "退租流程",   # 涉及金錢
    "押金處理",   # 爭議敏感
    "法律諮詢"    # 專業要求高
]

def is_safe_to_generate(category: str) -> bool:
    if category in restricted_categories:
        return False
    return category in safe_categories or category == "其他"
```

### 2. 自動品質檢查

```python
def validate_ai_response(answer: str, confidence: float) -> List[str]:
    """
    驗證 AI 生成的答案品質
    返回警告列表（空列表表示通過）
    """
    warnings = []

    # 檢查長度
    if len(answer) < 150:
        warnings.append("答案過短，建議補充更多細節")
    elif len(answer) > 800:
        warnings.append("答案過長，建議精簡")

    # 檢查信心度
    if confidence < 0.6:
        warnings.append("AI 信心度較低，需仔細審核")

    # 檢查模糊表達
    uncertainty_words = ["可能", "也許", "大概", "應該"]
    uncertainty_count = sum(answer.count(word) for word in uncertainty_words)
    if uncertainty_count > 3:
        warnings.append("答案包含過多不確定表達，建議修改為更明確的說法")

    # 檢查是否有結論
    if not any(word in answer for word in ["建議", "請", "務必", "可以", "需要"]):
        warnings.append("答案缺少明確指引或建議")

    return warnings
```

### 3. 審核工作流程

```
AI 生成
    ↓
自動品質檢查（warnings 標註）
    ↓
人工審核
    ├─ 信心度 >= 0.8，warnings = 0 → 可快速批准
    ├─ 信心度 0.6-0.8 或 warnings > 0 → 需仔細審核
    └─ 信心度 < 0.6 → 建議「需要修訂」或拒絕
    ↓
編輯修改（可選）
    ↓
二次確認
    ↓
批准並加入知識庫
```

### 4. 版本控制與可追溯性

**記錄內容：**
- ✅ 原始 AI 生成版本（`generated_answer`）
- ✅ 人工編輯版本（`edited_answer`）
- ✅ 編輯摘要（`edit_summary`）
- ✅ 生成 metadata（`generation_metadata` JSONB）:
  ```json
  {
    "ai_model": "gpt-3.5-turbo",
    "confidence_score": 0.85,
    "generated_at": "2025-10-11T10:30:00Z",
    "reviewed_by": "admin_name",
    "reviewed_at": "2025-10-11T11:00:00Z",
    "was_edited": true,
    "edit_summary": "修正部分措辭，補充聯絡方式",
    "reasoning": "基於一般租屋慣例推斷...",
    "warnings": ["實際規定請以租賃合約為準"]
  }
  ```

**好處：**
- 📊 可分析 AI 生成的準確度
- 🔍 可追溯修改歷史
- 📈 可持續改進 prompt

---

## 📊 成功指標

### KPI 定義

| 指標 | 目標值 | 衡量方式 |
|-----|--------|---------|
| **AI 生成通過率** | >= 60% | approved / (approved + rejected) |
| **平均信心度** | >= 0.75 | AVG(confidence_score WHERE status='approved') |
| **編輯率** | <= 50% | COUNT(edited_answer IS NOT NULL) / COUNT(*) |
| **知識庫增長速度** | +30% | 比較使用前後的每月新增知識數量 |
| **管理者滿意度** | >= 4/5 | 問卷調查 |
| **成本控制** | <= $50/月 | OpenAI API 帳單 |

### 監控儀表板（建議實作）

```sql
-- 查看 AI 知識生成統計
SELECT * FROM v_ai_knowledge_generation_stats;

-- 結果：
-- pending_count: 5
-- needs_revision_count: 2
-- approved_count: 45
-- rejected_count: 8
-- avg_confidence_approved: 0.82
-- avg_confidence_rejected: 0.58
-- approved_with_edits: 22
-- approved_without_edits: 23
```

---

## 👍 建議決策

### ✅ 強烈建議實作，條件如下：

#### 1. 明確範圍限制

**階段 1（MVP）：**
- ✅ 只為**安全類別**生成（設施使用、社區規範、常見問題）
- ❌ 不為**限制類別**生成（租金計算、合約條款、法律諮詢）

**階段 2（擴展）：**
- 評估 Phase 1 成效後，逐步開放其他類別

#### 2. 嚴格審核機制

- ✅ **必須人工審核**：AI 生成內容不會自動進入知識庫
- ✅ **支援編輯修改**：管理者可以調整後再批准
- ✅ **記錄完整歷史**：保留原始版本、編輯版本、審核備註

#### 3. 清楚標註來源

- ✅ 在知識庫中標註「🤖 AI 生成」徽章
- ✅ 顯示生成時間、AI 模型、審核者
- ✅ 提供「查看生成詳情」連結

#### 4. 持續監控品質

- 📊 每月檢視 AI 生成知識的使用者反饋
- 📈 追蹤信心度 vs 實際準確度的相關性
- 🔧 根據數據調整 prompt 或禁用特定類別

---

## 🎯 總結

### 核心優勢

1. **技術成熟度高**：已有 OpenAI 整合經驗，風險低
2. **業務價值明確**：顯著加速知識庫建設（60-80% 時間節省）
3. **品質可控**：嚴格的人工審核機制
4. **成本可控**：使用 GPT-3.5-turbo，每月僅 $5-20
5. **可追溯性強**：完整記錄生成和編輯歷史

### 實作優先順序

| 優先級 | 功能 | 時程 | 價值 |
|-------|-----|------|------|
| 🔥 **P0** | 基礎 AI 生成 + 人工審核流程 | 3-5 天 | 立即見效 |
| 🔥 **P0** | 類別白名單機制 | 1 天 | 風險控制 |
| ⭐ **P1** | 自動品質檢查 | 2 天 | 提升品質 |
| ⭐ **P1** | 統計儀表板 | 2 天 | 監控效果 |
| 📌 **P2** | 多候選比較 | 3 天 | 改善體驗 |
| 📌 **P2** | 批量生成 | 2 天 | 提升效率 |

### 最終建議

✅ **建議立即實作 Phase 1 (MVP)**

**理由：**
- 技術可行性高（5/5）
- 業務價值高（4/5）
- 風險可控（3/5，已有緩解措施）
- 成本低（每月 $5-20）
- 開發時間短（3-5 天）

**關鍵成功要素：**
1. 嚴格的類別白名單（避免高風險類別）
2. 必須的人工審核機制（不可跳過）
3. 清晰的 AI 生成標註（透明度）
4. 持續的品質監控（數據驅動改進）

---

**評估結論：** 這是一個**高價值、低風險、快速見效**的功能，強烈建議實作。

**下一步行動：**
1. ✅ 執行資料庫 migration（已完成）
2. ✅ 部署後端服務（已完成程式碼）
3. 🔧 實作 API 端點（3 小時）
4. 🎨 開發前端 UI（1-2 天）
5. 🧪 內部測試（1 天）
6. 🚀 上線並監控（持續）

---

**文件版本：** v1.0.0
**最後更新：** 2025-10-11
**相關文件：**
- `database/migrations/13-ai-knowledge-generation.sql`
- `rag-orchestrator/services/knowledge_generator.py`
- `SEMANTIC_SIMILARITY_COMPREHENSIVE_TEST_REPORT.md`
