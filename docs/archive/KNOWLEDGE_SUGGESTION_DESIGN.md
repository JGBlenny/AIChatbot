# 知識庫建議功能設計文檔

**版本：** v1.0
**日期：** 2025-10-11
**狀態：** 設計中

---

## 📌 功能概述

當系統收到無法回答的問題，且判斷該問題屬於包租代管業務範圍時，AI 自動生成建議的知識庫條目，供管理者審核後加入知識庫。

---

## 🎯 核心目標

1. **自動發現知識盲點** - 識別知識庫無法回答的業務問題
2. **AI 輔助生成答案** - 使用 LLM 生成建議答案
3. **人工審核質量** - 管理者審核確保答案準確性
4. **持續擴充知識庫** - 不斷填補知識庫空白

---

## 🔄 完整工作流程

### 階段 1: 問題收集

```
用戶提問: "租客可以養寵物嗎？"
    ↓
RAG 系統處理:
    - Intent Classification → unclear (信心度 < 0.6)
    - Knowledge Retrieval → 最高分數 0.25 (無相關知識)
    ↓
記錄到 unclear_questions 表
    - question_text: "租客可以養寵物嗎？"
    - classification_result: "unclear"
    - retrieval_score: 0.25
    - frequency: 1 (若重複提問則累加)
```

### 階段 2: 業務範圍判斷

```python
# 使用 LLM 判斷是否屬於包租代管業務
prompt = f"""
判斷以下問題是否屬於「包租代管」業務範圍：

問題: {question_text}

包租代管業務範圍包括：
- 租賃管理（租金、押金、租約）
- 物件管理（維修、設備、環境）
- 租客服務（入住、退租、規定）
- 房東服務（收益、報稅、委託）

請回答 YES 或 NO，並簡述原因。
"""

result = llm.generate(prompt)
# 解析結果
is_in_scope = parse_yes_no(result)
reasoning = extract_reasoning(result)
```

### 階段 3: AI 生成建議答案

```python
# 生成建議的知識庫內容
prompt = f"""
作為包租代管業務的客服專家，請為以下問題生成標準答案：

用戶問題: {question_text}

請提供：
1. 建議的標準問題（清晰、專業的表述）
2. 詳細答案（200-500字，包含具體做法和注意事項）
3. 建議的分類（從以下選擇）：
   - 租賃管理
   - 物件管理
   - 租客服務
   - 房東服務
   - 帳務問題
   - 法律規定
4. 關鍵字（5-8個）

輸出格式：JSON
"""

suggestion = llm.generate_json(prompt)
# 結果示例:
# {
#   "suggested_question": "租客是否可以在租屋處飼養寵物？",
#   "suggested_answer": "根據租約規定，租客飼養寵物需要符合以下條件...",
#   "suggested_category": "租客服務",
#   "suggested_keywords": ["寵物", "飼養", "租約", "房東同意", "押金"],
#   "confidence": 0.85
# }
```

### 階段 4: 創建待審核建議

```sql
INSERT INTO suggested_knowledge (
    source_unclear_question_id,
    suggested_question,
    suggested_answer,
    suggested_category,
    suggested_keywords,
    is_in_business_scope,
    scope_reasoning,
    ai_confidence,
    status,
    created_at
) VALUES (
    123,  -- unclear_questions.id
    '租客是否可以在租屋處飼養寵物？',
    '根據租約規定，租客飼養寵物需要符合以下條件...',
    '租客服務',
    ARRAY['寵物', '飼養', '租約', '房東同意', '押金'],
    TRUE,  -- 業務範圍內
    'This question is about tenant pet policies, which is within property management scope.',
    0.85,
    'pending',  -- 待審核
    NOW()
);
```

### 階段 5: 管理者審核

```
管理者在審核中心查看 → 知識庫審核 Tab

看到建議卡片:
┌─────────────────────────────────────────────┐
│ 📚 #建議 123  [AI 生成] [信心度: 85%] [業務範圍內] │
├─────────────────────────────────────────────┤
│ 來源問題: "租客可以養寵物嗎？"                    │
│ 出現頻率: 3 次                                  │
│                                                │
│ 建議問題: "租客是否可以在租屋處飼養寵物？"        │
│                                                │
│ 建議答案: (顯示前 200 字...)                    │
│ [展開全文]                                      │
│                                                │
│ 建議分類: 租客服務                              │
│ 關鍵字: 寵物, 飼養, 租約, 房東同意, 押金         │
│                                                │
│ AI 推理: This question is about tenant...     │
├─────────────────────────────────────────────┤
│ [✏️ 編輯] [✅ 採納] [❌ 拒絕]                   │
└─────────────────────────────────────────────┘
```

### 階段 6: 採納後加入知識庫

```sql
-- 管理者點擊「採納」
BEGIN;

-- 1. 插入到知識庫
INSERT INTO knowledge_base (
    vendor_id,
    question,
    answer,
    category,
    keywords,
    source,
    created_by,
    created_at
) VALUES (
    1,  -- JGB 業者
    '租客是否可以在租屋處飼養寵物？',
    '根據租約規定，租客飼養寵物需要符合以下條件...',
    '租客服務',
    ARRAY['寵物', '飼養', '租約', '房東同意', '押金'],
    'ai_suggestion',  -- 來源標記
    'admin',
    NOW()
)
RETURNING id;  -- 假設返回 knowledge_id = 456

-- 2. 更新建議狀態
UPDATE suggested_knowledge
SET status = 'approved',
    knowledge_id = 456,  -- 關聯到知識庫
    reviewed_by = 'admin',
    reviewed_at = NOW()
WHERE id = 123;

-- 3. 標記原始問題已處理
UPDATE unclear_questions
SET is_resolved = TRUE,
    resolved_at = NOW()
WHERE id = 123;

COMMIT;
```

---

## 📊 資料庫設計

### 新增表：suggested_knowledge

```sql
CREATE TABLE suggested_knowledge (
    id SERIAL PRIMARY KEY,

    -- 來源追蹤
    source_unclear_question_id INTEGER REFERENCES unclear_questions(id),

    -- AI 建議的內容
    suggested_question TEXT NOT NULL,
    suggested_answer TEXT NOT NULL,
    suggested_category VARCHAR(100),
    suggested_keywords TEXT[],

    -- 業務範圍判斷
    is_in_business_scope BOOLEAN DEFAULT FALSE,
    scope_reasoning TEXT,  -- LLM 判斷原因

    -- AI 信心度
    ai_confidence DECIMAL(3,2),  -- 0.00 - 1.00

    -- 審核狀態
    status VARCHAR(20) DEFAULT 'pending',  -- pending, approved, rejected, edited
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    review_notes TEXT,

    -- 關聯到知識庫（採納後）
    knowledge_id INTEGER REFERENCES knowledge_base(id),

    -- 時間戳
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_suggested_knowledge_status ON suggested_knowledge(status);
CREATE INDEX idx_suggested_knowledge_source ON suggested_knowledge(source_unclear_question_id);
CREATE INDEX idx_suggested_knowledge_created ON suggested_knowledge(created_at DESC);
```

### 輔助視圖

```sql
CREATE VIEW v_knowledge_suggestions AS
SELECT
    sk.id,
    sk.suggested_question,
    sk.suggested_answer,
    sk.suggested_category,
    sk.suggested_keywords,
    sk.is_in_business_scope,
    sk.scope_reasoning,
    sk.ai_confidence,
    sk.status,
    sk.reviewed_by,
    sk.reviewed_at,

    -- 來源問題信息
    uq.question_text as source_question,
    uq.frequency as question_frequency,
    uq.classification_result,
    uq.retrieval_best_score,

    -- 知識庫關聯（如已採納）
    kb.id as knowledge_id,
    kb.question as final_question,

    sk.created_at
FROM suggested_knowledge sk
LEFT JOIN unclear_questions uq ON sk.source_unclear_question_id = uq.id
LEFT JOIN knowledge_base kb ON sk.knowledge_id = kb.id
ORDER BY
    CASE sk.status
        WHEN 'pending' THEN 1
        WHEN 'edited' THEN 2
        ELSE 3
    END,
    sk.created_at DESC;
```

---

## 🔌 API 設計

### 1. 獲取知識庫建議列表

```
GET /api/knowledge/suggestions

Query Parameters:
- status: pending | approved | rejected | edited
- min_frequency: 最低問題頻率（過濾低頻問題）
- min_confidence: 最低 AI 信心度
- limit: 結果數量
- offset: 分頁偏移

Response:
{
  "suggestions": [
    {
      "id": 123,
      "source_question": "租客可以養寵物嗎？",
      "question_frequency": 3,
      "suggested_question": "租客是否可以在租屋處飼養寵物？",
      "suggested_answer": "根據租約規定...",
      "suggested_category": "租客服務",
      "suggested_keywords": ["寵物", "飼養", "租約"],
      "is_in_business_scope": true,
      "scope_reasoning": "This question is about...",
      "ai_confidence": 0.85,
      "status": "pending",
      "created_at": "2025-10-11T10:30:00"
    }
  ],
  "total": 15,
  "pending_count": 12
}
```

### 2. 獲取單個建議詳情

```
GET /api/knowledge/suggestions/:id

Response:
{
  "id": 123,
  "source_question": "租客可以養寵物嗎？",
  "question_frequency": 3,
  "classification_result": "unclear",
  "retrieval_best_score": 0.25,
  "suggested_question": "租客是否可以在租屋處飼養寵物？",
  "suggested_answer": "根據租約規定，租客飼養寵物需要符合以下條件...",
  "suggested_category": "租客服務",
  "suggested_keywords": ["寵物", "飼養", "租約", "房東同意", "押金"],
  "is_in_business_scope": true,
  "scope_reasoning": "This question is about tenant pet policies...",
  "ai_confidence": 0.85,
  "status": "pending",
  "created_at": "2025-10-11T10:30:00"
}
```

### 3. 審核建議（採納）

```
POST /api/knowledge/suggestions/:id/approve

Body:
{
  "reviewed_by": "admin",
  "notes": "審核備註（選填）",
  "vendor_id": 1,  // 加入哪個業者的知識庫

  // 可選：覆蓋 AI 建議的內容
  "final_question": "租客是否可以在租屋處飼養寵物？",  // 如不提供則使用 suggested_question
  "final_answer": "...",  // 如不提供則使用 suggested_answer
  "final_category": "租客服務",
  "final_keywords": ["寵物", "飼養"]
}

Response:
{
  "success": true,
  "message": "知識庫建議已採納",
  "suggestion_id": 123,
  "knowledge_id": 456,  // 新創建的知識庫 ID
  "status": "approved"
}
```

### 4. 審核建議（編輯）

```
PUT /api/knowledge/suggestions/:id/edit

Body:
{
  "suggested_question": "修改後的問題",
  "suggested_answer": "修改後的答案",
  "suggested_category": "修改後的分類",
  "suggested_keywords": ["關鍵字1", "關鍵字2"]
}

Response:
{
  "success": true,
  "message": "建議已更新",
  "suggestion_id": 123,
  "status": "edited"  // 標記為已編輯，等待再次審核
}
```

### 5. 審核建議（拒絕）

```
POST /api/knowledge/suggestions/:id/reject

Body:
{
  "reviewed_by": "admin",
  "notes": "拒絕原因（必填）"
}

Response:
{
  "success": true,
  "message": "建議已拒絕",
  "suggestion_id": 123,
  "status": "rejected"
}
```

### 6. 觸發 AI 生成建議（手動）

```
POST /api/knowledge/suggestions/generate

Body:
{
  "unclear_question_id": 123
}

Response:
{
  "success": true,
  "message": "AI 建議已生成",
  "suggestion_id": 456,
  "ai_confidence": 0.85
}
```

---

## 🤖 AI 生成邏輯

### Prompt 模板

#### 1. 業務範圍判斷

```python
SCOPE_JUDGMENT_PROMPT = """
你是一位包租代管業務專家。請判斷以下問題是否屬於包租代管業務範圍。

包租代管業務範圍包括：
1. **租賃管理**：租金、押金、租約、續約、租金調整
2. **物件管理**：維修、設備、清潔、安全、環境
3. **租客服務**：入住、退租、規定、問題處理、寵物政策
4. **房東服務**：收益、報稅、委託、物件評估
5. **帳務問題**：繳費、退費、收據、對帳
6. **法律規定**：租賃法規、消防安全、建築法規

用戶問題：{question_text}

請以 JSON 格式回答：
{{
    "is_in_scope": true/false,
    "reasoning": "判斷原因（中文，50-100字）",
    "suggested_category": "建議的分類（如果屬於業務範圍）"
}}
"""
```

#### 2. 答案生成

```python
ANSWER_GENERATION_PROMPT = """
你是 JGB 包租代管公司的資深客服專家。請為以下用戶問題生成專業、準確的答案。

用戶問題：{question_text}

請提供：
1. **標準化問題**：將用戶問題改寫為清晰、專業的標準問題
2. **詳細答案**：
   - 200-500 字
   - 包含具體做法、流程、注意事項
   - 如涉及法規，請說明相關規定
   - 如需聯繫客服，請提供聯繫方式
   - 語氣友善、專業
3. **分類**：從以下分類中選擇最適合的
   - 租賃管理 / 物件管理 / 租客服務 / 房東服務 / 帳務問題 / 法律規定
4. **關鍵字**：5-8 個最相關的關鍵字（用於檢索）

輸出格式：JSON
{{
    "suggested_question": "標準化問題",
    "suggested_answer": "詳細答案",
    "suggested_category": "分類",
    "suggested_keywords": ["關鍵字1", "關鍵字2", ...],
    "confidence": 0.0-1.0  // AI 對答案質量的信心度
}}
"""
```

### 實作範例

```python
async def generate_knowledge_suggestion(unclear_question_id: int):
    """
    為 unclear question 生成知識庫建議
    """
    # 1. 獲取原始問題
    uq = await db.get_unclear_question(unclear_question_id)
    if not uq:
        raise ValueError("Unclear question not found")

    question_text = uq['question_text']

    # 2. 判斷業務範圍
    scope_result = await llm.generate(
        SCOPE_JUDGMENT_PROMPT.format(question_text=question_text),
        response_format="json"
    )

    is_in_scope = scope_result['is_in_scope']
    if not is_in_scope:
        logger.info(f"Question {unclear_question_id} is out of scope")
        return None

    # 3. 生成答案建議
    answer_result = await llm.generate(
        ANSWER_GENERATION_PROMPT.format(question_text=question_text),
        response_format="json"
    )

    # 4. 創建建議記錄
    suggestion = await db.create_knowledge_suggestion({
        'source_unclear_question_id': unclear_question_id,
        'suggested_question': answer_result['suggested_question'],
        'suggested_answer': answer_result['suggested_answer'],
        'suggested_category': answer_result['suggested_category'],
        'suggested_keywords': answer_result['suggested_keywords'],
        'is_in_business_scope': is_in_scope,
        'scope_reasoning': scope_result['reasoning'],
        'ai_confidence': answer_result['confidence'],
        'status': 'pending'
    })

    return suggestion
```

---

## 🚀 自動化流程

### 定時任務：批量生成建議

```python
# 每天執行一次，為高頻 unclear questions 生成建議
@scheduler.scheduled_job('cron', hour=2, minute=0)  # 每天凌晨 2:00
async def auto_generate_suggestions():
    """
    自動為高頻 unclear questions 生成知識庫建議
    """
    # 1. 獲取高頻且未處理的 unclear questions
    unclear_questions = await db.query("""
        SELECT id, question_text, frequency
        FROM unclear_questions
        WHERE frequency >= 2  -- 至少出現 2 次
          AND is_resolved = FALSE
          AND id NOT IN (
              SELECT source_unclear_question_id
              FROM suggested_knowledge
              WHERE source_unclear_question_id IS NOT NULL
          )
        ORDER BY frequency DESC
        LIMIT 20  -- 每次處理前 20 個
    """)

    logger.info(f"Found {len(unclear_questions)} high-frequency unclear questions")

    # 2. 批量生成建議
    for uq in unclear_questions:
        try:
            suggestion = await generate_knowledge_suggestion(uq['id'])
            if suggestion:
                logger.info(f"Generated suggestion {suggestion['id']} for question {uq['id']}")
            else:
                logger.info(f"Question {uq['id']} is out of business scope, skipped")
        except Exception as e:
            logger.error(f"Failed to generate suggestion for question {uq['id']}: {e}")

    logger.info("Auto-generation completed")
```

---

## 📈 統計與監控

### 統計 API

```
GET /api/knowledge/suggestions/stats

Response:
{
  "pending": 12,      // 待審核
  "approved": 45,     // 已採納
  "rejected": 8,      // 已拒絕
  "edited": 3,        // 已編輯（待再次審核）
  "total": 68,

  // 採納率
  "approval_rate": 0.75,  // 45 / (45 + 8) = 84%

  // 平均信心度
  "avg_confidence": 0.82,

  // 分類分佈
  "by_category": {
    "租客服務": 20,
    "物件管理": 15,
    "帳務問題": 10,
    ...
  },

  // 最近 7 天趨勢
  "recent_trend": [
    {"date": "2025-10-05", "generated": 5, "approved": 3},
    {"date": "2025-10-06", "generated": 8, "approved": 5},
    ...
  ]
}
```

---

## 🎯 前端整合

### 更新 KnowledgeReviewTab.vue

```vue
<template>
  <div class="knowledge-review-tab">
    <!-- 統計卡片 -->
    <div class="stats-cards">
      <div class="stat-card">
        <div class="stat-title">待審核</div>
        <div class="stat-value warning">{{ stats.pending }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">已採納</div>
        <div class="stat-value success">{{ stats.approved }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">採納率</div>
        <div class="stat-value">{{ (stats.approval_rate * 100).toFixed(0) }}%</div>
      </div>
    </div>

    <!-- 建議列表 -->
    <div class="suggestions-list">
      <div v-for="suggestion in suggestions" :key="suggestion.id" class="suggestion-card">
        <div class="card-header">
          <span class="suggestion-id">#建議 {{ suggestion.id }}</span>
          <span class="badge ai-badge">AI 生成</span>
          <span class="badge" :class="'confidence-' + getConfidenceClass(suggestion.ai_confidence)">
            信心度: {{ (suggestion.ai_confidence * 100).toFixed(0) }}%
          </span>
        </div>

        <div class="card-body">
          <!-- 來源問題 -->
          <div class="source-section">
            <h5>來源問題</h5>
            <p class="source-question">"{{ suggestion.source_question }}"</p>
            <span class="frequency">出現 {{ suggestion.question_frequency }} 次</span>
          </div>

          <!-- AI 建議 -->
          <div class="suggestion-section">
            <h5>建議問題</h5>
            <p class="suggested-question">{{ suggestion.suggested_question }}</p>

            <h5>建議答案</h5>
            <p class="suggested-answer" v-if="!suggestion.expanded">
              {{ truncate(suggestion.suggested_answer, 150) }}
              <a @click="suggestion.expanded = true" class="expand-link">展開全文</a>
            </p>
            <p class="suggested-answer" v-else>
              {{ suggestion.suggested_answer }}
              <a @click="suggestion.expanded = false" class="collapse-link">收起</a>
            </p>

            <div class="meta-info">
              <span><strong>分類：</strong>{{ suggestion.suggested_category }}</span>
              <span><strong>關鍵字：</strong>{{ suggestion.suggested_keywords.join(', ') }}</span>
            </div>
          </div>

          <!-- AI 推理 -->
          <div class="reasoning-section">
            <h5>AI 推理</h5>
            <p>{{ suggestion.scope_reasoning }}</p>
          </div>
        </div>

        <div class="card-actions">
          <button @click="editSuggestion(suggestion)" class="btn btn-edit">
            ✏️ 編輯
          </button>
          <button @click="approveSuggestion(suggestion.id)" class="btn btn-approve">
            ✅ 採納
          </button>
          <button @click="rejectSuggestion(suggestion.id)" class="btn btn-reject">
            ❌ 拒絕
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      suggestions: [],
      stats: {},
      loading: false
    };
  },

  mounted() {
    this.loadSuggestions();
    this.loadStats();
  },

  methods: {
    async loadSuggestions() {
      this.loading = true;
      try {
        const response = await axios.get('/api/knowledge/suggestions', {
          params: { status: 'pending', limit: 50 }
        });
        this.suggestions = response.data.suggestions.map(s => ({
          ...s,
          expanded: false  // 控制展開/收起
        }));
      } catch (error) {
        alert('載入失敗：' + error.message);
      } finally {
        this.loading = false;
      }
    },

    async loadStats() {
      try {
        const response = await axios.get('/api/knowledge/suggestions/stats');
        this.stats = response.data;

        // 通知父組件更新待審核數量
        this.$emit('update-count', {
          tab: 'knowledge',
          count: this.stats.pending || 0
        });
      } catch (error) {
        console.error('載入統計失敗', error);
      }
    },

    async approveSuggestion(id) {
      const note = prompt('審核備註（可選）:');
      if (note === null) return;

      try {
        await axios.post(`/api/knowledge/suggestions/${id}/approve`, {
          reviewed_by: 'admin',
          notes: note || '',
          vendor_id: 1  // JGB
        });

        alert('✅ 知識庫建議已採納！');
        this.loadSuggestions();
        this.loadStats();
      } catch (error) {
        alert('採納失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    async rejectSuggestion(id) {
      const note = prompt('拒絕原因:');
      if (!note) return;

      try {
        await axios.post(`/api/knowledge/suggestions/${id}/reject`, {
          reviewed_by: 'admin',
          notes: note
        });

        alert('✅ 建議已拒絕');
        this.loadSuggestions();
        this.loadStats();
      } catch (error) {
        alert('拒絕失敗：' + error.message);
      }
    },

    truncate(text, length) {
      return text.length > length ? text.substring(0, length) + '...' : text;
    },

    getConfidenceClass(confidence) {
      if (confidence >= 0.8) return 'high';
      if (confidence >= 0.6) return 'medium';
      return 'low';
    }
  }
};
</script>
```

---

## ✅ 實施檢查清單

### 後端開發

- [ ] 創建 `suggested_knowledge` 資料表
- [ ] 創建 `v_knowledge_suggestions` 視圖
- [ ] 實作業務範圍判斷 LLM
- [ ] 實作答案生成 LLM
- [ ] 實作 6 個 API 端點
- [ ] 實作定時任務（批量生成）
- [ ] 單元測試

### 前端開發

- [ ] 更新 KnowledgeReviewTab.vue
- [ ] 實作編輯對話框
- [ ] 實作採納/拒絕邏輯
- [ ] 整合統計 API
- [ ] UI/UX 優化

### 測試驗證

- [ ] 端到端測試
- [ ] 性能測試（大量建議）
- [ ] AI 生成質量評估
- [ ] 用戶體驗測試

---

**最後更新：** 2025-10-11 15:45
**設計者：** Claude Code
**狀態：** 設計完成，待實作
