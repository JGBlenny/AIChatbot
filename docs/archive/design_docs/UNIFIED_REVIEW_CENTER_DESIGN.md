# 統一審核中心設計文檔

**版本：** v1.0
**日期：** 2025-10-11
**狀態：** 設計中

---

## 📌 設計目標

將分散的審核功能整合為統一的審核中心，提供一致的審核體驗。

### 整合範圍

1. **審核意圖** - 審核 AI 推薦的意圖（來自 SuggestedIntentsView）
2. **審核測試情境** - 審核待批准的測試情境（來自 PendingReviewView）
3. **審核知識庫** ⭐ NEW - 基於測試情境審核推薦的知識庫條目

---

## 🎨 UI 設計

### 頁面結構

```
┌─────────────────────────────────────────────────────────┐
│  🔍 審核中心                                              │
│  ┌───────────┬───────────────┬─────────────────┐         │
│  │ 意圖審核   │ 測試情境審核   │ 知識庫審核      │         │
│  └───────────┴───────────────┴─────────────────┘         │
│                                                           │
│  ┌─────────────────────────────────────────────┐         │
│  │  統計卡片區域                                  │         │
│  │  [待審核: 12] [已批准: 45] [已拒絕: 8]         │         │
│  └─────────────────────────────────────────────┘         │
│                                                           │
│  ┌─────────────────────────────────────────────┐         │
│  │  篩選器區域                                    │         │
│  │  [狀態] [排序] [搜尋]                          │         │
│  └─────────────────────────────────────────────┘         │
│                                                           │
│  ┌─────────────────────────────────────────────┐         │
│  │  審核項目卡片列表                               │         │
│  │  ┌─────────────────────────────────────┐     │         │
│  │  │ 審核項目 #1                           │     │         │
│  │  │ [詳細資訊]                             │     │         │
│  │  │ [✅ 批准] [❌ 拒絕] [✏️ 編輯]          │     │         │
│  │  └─────────────────────────────────────┘     │         │
│  └─────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────┘
```

### Tab 切換設計

使用 Vue.js 的動態組件切換，保持各 Tab 的狀態：

```vue
<template>
  <div class="review-center">
    <h2>🔍 審核中心</h2>

    <!-- Tab 導航 -->
    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab', { active: currentTab === tab.key }]"
        @click="currentTab = tab.key"
      >
        {{ tab.icon }} {{ tab.label }}
        <span v-if="tab.count > 0" class="badge">{{ tab.count }}</span>
      </button>
    </div>

    <!-- Tab 內容 -->
    <keep-alive>
      <component :is="currentTabComponent" />
    </keep-alive>
  </div>
</template>
```

---

## 📊 資料結構

### 1. 意圖審核（Intent Review）

**API：** `GET http://localhost:8100/api/v1/suggested-intents`

**資料模型：**
```typescript
interface SuggestedIntent {
  id: number;
  suggested_name: string;
  suggested_description: string;
  suggested_type: 'knowledge' | 'data_query' | 'action' | 'hybrid';
  suggested_keywords: string[];
  trigger_question: string;
  relevance_score: number;
  frequency: number;
  reasoning: string;
  status: 'pending' | 'approved' | 'rejected' | 'merged';
  reviewed_by?: string;
  review_note?: string;
}
```

**操作：**
- ✅ 採納（創建新意圖）
- ❌ 拒絕
- 🔗 合併到現有意圖

---

### 2. 測試情境審核（Test Scenario Review）

**API：** `GET http://localhost:8000/api/test/scenarios/pending`

**資料模型：**
```typescript
interface PendingTestScenario {
  id: number;
  test_question: string;
  expected_category: string;
  expected_keywords: string[];
  difficulty: 'easy' | 'medium' | 'hard';
  priority: number;
  status: 'pending_review' | 'approved' | 'rejected';
  source: 'manual' | 'user_question' | 'ai_generated';
  question_frequency?: number;
  notes?: string;
}
```

**操作：**
- ✅ 批准
- ❌ 拒絕
- ✏️ 編輯後再審核

---

### 3. 知識庫審核（Knowledge Review）⭐ NEW

**設計思路：**
基於測試情境的執行結果，推薦需要審核的知識庫條目。

**觸發條件：**
1. 測試情境失敗（分數 < 0.6）
2. 檢索到的知識庫不相關
3. 缺少預期關鍵字
4. 用戶反饋不準確

**API 設計：** `GET http://localhost:8000/api/knowledge/review-candidates`

**資料模型：**
```typescript
interface KnowledgeReviewCandidate {
  id: number;
  knowledge_id: number;
  knowledge_question: string;
  knowledge_answer: string;
  knowledge_category: string;
  issue_type: 'low_score' | 'irrelevant' | 'missing_keywords' | 'user_feedback';
  test_scenario_id?: number;
  test_question?: string;
  test_score?: number;
  suggested_action: 'update_keywords' | 'update_category' | 'update_content' | 'deprecate';
  reasoning: string;
}
```

**操作：**
- ✏️ 編輯知識庫（跳轉到知識庫編輯頁）
- ✅ 標記為已處理
- ❌ 忽略建議
- 📊 查看測試詳情（關聯的測試情境）

---

## 🔄 工作流程

### 意圖審核流程

```
1. AI 分析用戶問題 → 推薦新意圖
2. 管理者在審核中心查看推薦
3. 決策：
   - 採納 → 創建新意圖 → 標記為 approved
   - 拒絕 → 標記為 rejected + 填寫原因
   - 合併 → 選擇現有意圖 → 標記為 merged
```

### 測試情境審核流程

```
1. 用戶問題轉為測試情境（狀態：pending_review）
2. 管理者在審核中心查看
3. 決策：
   - 批准 → 標記為 approved → 加入回測
   - 拒絕 → 標記為 rejected + 填寫原因
   - 編輯 → 修改內容 → 重新審核
```

### 知識庫審核流程 ⭐ NEW

```
1. 回測執行 → 識別問題知識庫
2. 系統生成審核候選列表
3. 管理者在審核中心查看
4. 決策：
   - 編輯 → 跳轉到知識庫編輯頁 → 修改內容
   - 標記已處理 → 記錄處理時間
   - 忽略 → 標記為已審核但不處理
5. 重新回測驗證改善
```

---

## 🛠️ 技術實作

### 組件架構

```
ReviewCenterView.vue (主容器)
├── ReviewTabs.vue (Tab 切換組件)
├── IntentReviewTab.vue (意圖審核)
│   ├── IntentReviewCard.vue
│   └── IntentReviewDialog.vue
├── ScenarioReviewTab.vue (測試情境審核)
│   ├── ScenarioReviewCard.vue
│   └── ScenarioEditDialog.vue
└── KnowledgeReviewTab.vue (知識庫審核) ⭐ NEW
    ├── KnowledgeReviewCard.vue
    └── KnowledgeReviewDialog.vue
```

### 狀態管理

使用 Vue 3 Composition API 或 Pinia 管理全局審核狀態：

```typescript
interface ReviewState {
  intentsPending: number;
  scenariosPending: number;
  knowledgePending: number;
  currentTab: 'intents' | 'scenarios' | 'knowledge';
  lastRefresh: Date;
}
```

### API 端點整合

| 功能 | 端點 | 服務 |
|------|------|------|
| 意圖審核列表 | `GET /api/v1/suggested-intents` | RAG Orchestrator (8100) |
| 意圖採納 | `POST /api/v1/suggested-intents/:id/approve` | RAG Orchestrator (8100) |
| 意圖拒絕 | `POST /api/v1/suggested-intents/:id/reject` | RAG Orchestrator (8100) |
| 測試情境列表 | `GET /api/test/scenarios/pending` | Knowledge Admin (8000) |
| 測試情境批准 | `POST /api/test/scenarios/:id/review` | Knowledge Admin (8000) |
| 知識庫候選 | `GET /api/knowledge/review-candidates` ⭐ NEW | Knowledge Admin (8000) |
| 知識庫標記處理 | `POST /api/knowledge/:id/mark-reviewed` ⭐ NEW | Knowledge Admin (8000) |

---

## 🎯 優勢

### 用戶體驗

1. **統一入口** - 一個頁面處理所有審核任務
2. **快速切換** - Tab 切換保持各審核類型的狀態
3. **待審核數量一目了然** - Badge 顯示各類型待審核數量
4. **一致的操作模式** - 統一的批准/拒絕/編輯流程

### 開發維護

1. **模組化設計** - 各審核類型獨立組件
2. **可擴展** - 未來新增審核類型只需添加新 Tab
3. **程式碼復用** - 共享審核對話框和卡片組件
4. **統一樣式** - 一致的 UI 設計語言

---

## 📋 實施計劃

### Phase 1: 核心架構（第 1 天）

- [x] 設計架構文檔
- [ ] 創建 ReviewCenterView.vue 主容器
- [ ] 實作 Tab 切換邏輯
- [ ] 設計統一的卡片樣式

### Phase 2: 整合現有功能（第 2 天）

- [ ] 整合意圖審核（IntentReviewTab）
- [ ] 整合測試情境審核（ScenarioReviewTab）
- [ ] 測試現有功能正常運作

### Phase 3: 新增知識庫審核（第 3 天）⭐ NEW

- [ ] 設計知識庫審核 API
- [ ] 實作後端邏輯（識別問題知識庫）
- [ ] 實作前端 KnowledgeReviewTab
- [ ] 整合回測結果分析

### Phase 4: 優化與測試（第 4 天）

- [ ] 優化 UI/UX
- [ ] 端到端測試
- [ ] 更新路由和導航
- [ ] 更新文檔

---

## 🔍 待決定事項

1. **知識庫審核觸發時機**
   - 選項 A：回測後自動生成候選列表
   - 選項 B：管理者手動觸發分析
   - **建議：選項 A（自動化）**

2. **審核優先級排序**
   - 依據：頻率、分數、影響範圍
   - **建議：可配置的排序選項**

3. **批量操作支持**
   - 是否需要批量批准/拒絕功能
   - **建議：Phase 2 實作**

---

## 📚 參考資料

- 現有實作：SuggestedIntentsView.vue
- 現有實作：PendingReviewView.vue
- Material Design: Tabs Pattern
- Ant Design: Review Workflow Pattern

---

**最後更新：** 2025-10-11 14:30
**設計者：** Claude Code
**狀態：** 待實作
