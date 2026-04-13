# Task 11.3 缺口分析報告

> 建立時間：2026-03-28
> 分析者：AI Assistant

---

## 執行摘要

Task 11.3「實作知識審核 Tab」的**後端 API 與前端基礎功能已完成**（Task 6.1-6.6），但**批量審核前端功能尚未實作**。

**結論**：需要在現有的 `LoopKnowledgeReviewTab.vue` 中補充批量審核功能，而非建立新元件。

---

## 已完成項目

### 1. 後端 API（Task 6.1-6.6）✅

**檔案**：`rag-orchestrator/routers/loop_knowledge.py`（39KB，3月27日建立）

**已實作端點**：
- ✅ GET `/api/v1/loop-knowledge/pending` - 查詢待審核知識
- ✅ POST `/api/v1/loop-knowledge/{knowledge_id}/review` - 單一審核
- ✅ POST `/api/v1/loop-knowledge/batch-review` - 批量審核

**測試檔案**：
- `routers/test_loop_knowledge_query.py`
- `routers/test_loop_knowledge_review.py`
- `routers/test_loop_knowledge_batch_review.py`

### 2. 批量審核需求文件（Task 9.2）✅

**檔案**：`docs/frontend/batch_review_requirements.md`（717 行）

**定義內容**：
- 全選核取方塊（當前頁/所有頁）
- 篩選後全選功能
- 批量操作工具列
- 確認對話框（統計、警告提示）
- 處理進度顯示（進度條、當前項目、已處理列表）
- 結果摘要對話框（成功/失敗統計、重試功能）

### 3. 前端基礎實作 ✅

**檔案**：`knowledge-admin/frontend/src/components/review/LoopKnowledgeReviewTab.vue`（714 行）

**已實作功能**：
- ✅ 統計卡片（待審核、待審核 SOP、已通過、已拒絕）
- ✅ 類型篩選（全部、僅 SOP、一般知識）
- ✅ 待審核知識列表顯示
- ✅ 單一審核功能（批准/拒絕）
- ✅ SOP 特殊欄位處理（業者、類別、群組選擇）
- ✅ 審核備註輸入

**整合狀態**：
- ✅ 已整合在 `ReviewCenterView.vue` 的第 5 個 Tab（🔄 迴圈知識審核）
- ✅ 可透過 http://localhost:8087/review-center 存取

---

## 缺少項目（Task 11.3）

根據 `batch_review_requirements.md` 的定義，`LoopKnowledgeReviewTab.vue` 還缺少以下功能：

### 1. 全選核取方塊 ❌

**位置**：表格標題列（thead）第一欄

**功能**：
- 點擊後選取/取消選取當前頁所有項目
- 狀態顯示：未選取 / 全選 / 部分選取（indeterminate）

**需要新增**：
```vue
<template>
  <thead>
    <tr>
      <th>
        <input
          type="checkbox"
          :checked="allSelected"
          :indeterminate="someSelected"
          @change="toggleSelectAll"
        />
      </th>
      <!-- 其他欄位 -->
    </tr>
  </thead>
  <tbody>
    <tr v-for="item in items" :key="item.id">
      <td>
        <input
          type="checkbox"
          :checked="selectedIds.includes(item.id)"
          @change="toggleSelectItem(item.id)"
        />
      </td>
      <!-- 其他欄位 -->
    </tr>
  </tbody>
</template>

<script>
export default {
  data() {
    return {
      selectedIds: [], // 新增
    };
  },
  computed: {
    allSelected() {
      return this.items.length > 0 && this.items.every(item => this.selectedIds.includes(item.id));
    },
    someSelected() {
      return !this.allSelected && this.items.some(item => this.selectedIds.includes(item.id));
    },
  },
  methods: {
    toggleSelectAll() {
      if (this.allSelected) {
        this.selectedIds = [];
      } else {
        this.selectedIds = this.items.map(item => item.id);
      }
    },
    toggleSelectItem(id) {
      const index = this.selectedIds.indexOf(id);
      if (index > -1) {
        this.selectedIds.splice(index, 1);
      } else {
        this.selectedIds.push(id);
      }
    },
  },
};
</script>
```

---

### 2. 批量操作工具列 ❌

**位置**：表格上方，篩選欄下方

**顯示條件**：`selectedIds.length > 0`

**功能**：
- 顯示已選取數量
- 顯示類型分布（SOP / 一般）
- 提供批量批准/拒絕按鈕
- 提供取消選取按鈕

**需要新增**：
```vue
<template>
  <div class="batch-actions" v-if="selectedIds.length > 0">
    <div class="batch-info">
      <span class="count">已選取 {{ selectedIds.length }} 個項目</span>
      <span class="type-breakdown">
        （SOP: {{ sopCount }}, 一般: {{ generalCount }}）
      </span>
    </div>
    <div class="batch-buttons">
      <button @click="showBatchConfirm('approve')" class="btn-approve">
        批量批准
      </button>
      <button @click="showBatchConfirm('reject')" class="btn-reject">
        批量拒絕
      </button>
      <button @click="clearSelection" class="btn-secondary">
        取消選取
      </button>
    </div>
  </div>
</template>

<script>
export default {
  computed: {
    sopCount() {
      return this.selectedIds
        .map(id => this.items.find(i => i.id === id))
        .filter(item => item?.knowledge_type === 'sop')
        .length;
    },
    generalCount() {
      return this.selectedIds.length - this.sopCount;
    },
  },
  methods: {
    clearSelection() {
      this.selectedIds = [];
    },
  },
};
</script>
```

---

### 3. 批量審核確認對話框 ❌

**觸發時機**：點擊「批量批准」或「批量拒絕」按鈕

**功能**：
- 顯示選取數量與類型分布
- 顯示重複警告統計
- 提供確認/取消按鈕

**需要新增**：
```vue
<template>
  <div v-if="showBatchConfirmDialog" class="modal-overlay" @click.self="closeBatchConfirm">
    <div class="modal-content">
      <div class="modal-header">
        <h3>批量{{ batchAction === 'approve' ? '批准' : '拒絕' }}確認</h3>
        <button class="close-btn" @click="closeBatchConfirm">✕</button>
      </div>
      <div class="modal-body">
        <p>您即將{{ batchAction === 'approve' ? '批准' : '拒絕' }} <strong>{{ selectedIds.length }}</strong> 個知識項目：</p>

        <h4>知識類型分布：</h4>
        <ul>
          <li>SOP 知識：{{ typeStats.sop }} 個</li>
          <li>一般知識：{{ typeStats.general }} 個</li>
        </ul>

        <h4>重複警告統計：</h4>
        <ul>
          <li>無警告：{{ warningStats.no_warning }} 個</li>
          <li v-if="warningStats.has_warning > 0" class="warning">
            有警告：{{ warningStats.has_warning }} 個
            （相似度 {{ warningStats.min_similarity }}-{{ warningStats.max_similarity }}%）
          </li>
        </ul>

        <div v-if="warningStats.has_warning > 0" class="alert-warning">
          ⚠️ 有 {{ warningStats.has_warning }} 個項目檢測到重複警告，建議人工確認後再批准。
        </div>
      </div>
      <div class="modal-footer">
        <button @click="closeBatchConfirm" class="btn-secondary">取消</button>
        <button @click="confirmBatchReview" class="btn-primary">
          確認{{ batchAction === 'approve' ? '批准' : '拒絕' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      showBatchConfirmDialog: false,
      batchAction: 'approve', // 'approve' | 'reject'
    };
  },
  computed: {
    typeStats() {
      const selected = this.selectedIds.map(id => this.items.find(i => i.id === id));
      return {
        sop: selected.filter(i => i.knowledge_type === 'sop').length,
        general: selected.filter(i => i.knowledge_type === null).length,
      };
    },
    warningStats() {
      const selected = this.selectedIds.map(id => this.items.find(i => i.id === id));
      const withWarning = selected.filter(i => i.duplication_warning);

      if (withWarning.length === 0) {
        return { has_warning: 0, no_warning: selected.length };
      }

      const similarities = withWarning.map(i => {
        const score = i.similar_knowledge?.items[0]?.similarity_score || 0;
        return Math.round(score * 100);
      });

      return {
        has_warning: withWarning.length,
        no_warning: selected.length - withWarning.length,
        min_similarity: Math.min(...similarities),
        max_similarity: Math.max(...similarities),
      };
    },
  },
  methods: {
    showBatchConfirm(action) {
      this.batchAction = action;
      this.showBatchConfirmDialog = true;
    },
    closeBatchConfirm() {
      this.showBatchConfirmDialog = false;
    },
  },
};
</script>
```

---

### 4. 批量審核進度顯示 ❌

**觸發時機**：點擊「確認批准」後

**功能**：
- 顯示進度條（百分比）
- 顯示當前處理項目
- 顯示已處理項目列表（成功/失敗）

**需要新增**：
```vue
<template>
  <div v-if="showBatchProgressDialog" class="modal-overlay">
    <div class="modal-content">
      <div class="modal-header">
        <h3>批量{{ batchAction === 'approve' ? '批准' : '拒絕' }}處理中</h3>
      </div>
      <div class="modal-body">
        <h4>處理進度... {{ batchProgress.processed }}/{{ batchProgress.total }} ({{ batchProgress.percentage }}%)</h4>

        <div class="progress-bar-container">
          <div class="progress-bar" :style="{ width: batchProgress.percentage + '%' }"></div>
        </div>

        <p v-if="batchProgress.currentItem" class="current-item">
          正在處理：{{ batchProgress.currentItem.question }} (#{{ batchProgress.currentItem.id }})
        </p>

        <div class="processed-list" v-if="batchProgress.processedItems.length > 0">
          <h5>已處理項目：</h5>
          <ul>
            <li
              v-for="item in batchProgress.processedItems"
              :key="item.id"
              :class="{ success: item.success, failed: !item.success }"
            >
              <span class="icon">{{ item.success ? '✓' : '✗' }}</span>
              <span class="id">#{{ item.id }}</span>
              <span class="question">{{ item.question }}</span>
              <span v-if="!item.success" class="error">（{{ item.error }}）</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      showBatchProgressDialog: false,
      batchProgress: {
        total: 0,
        processed: 0,
        currentItem: null,
        processedItems: [],
      },
    };
  },
  computed: {
    'batchProgress.percentage'() {
      return this.batchProgress.total > 0
        ? Math.round((this.batchProgress.processed / this.batchProgress.total) * 100)
        : 0;
    },
  },
};
</script>
```

---

### 5. 批量審核結果摘要 ❌

**觸發時機**：批量處理完成後

**功能**：
- 顯示成功/失敗統計
- 顯示執行時間
- 顯示失敗項目列表
- 提供重試失敗項目功能

**需要新增**：
```vue
<template>
  <div v-if="showBatchResultDialog" class="modal-overlay" @click.self="closeBatchResult">
    <div class="modal-content">
      <div class="modal-header">
        <h3>批量{{ batchAction === 'approve' ? '批准' : '拒絕' }}完成</h3>
        <button class="close-btn" @click="closeBatchResult">✕</button>
      </div>
      <div class="modal-body">
        <div class="result-summary">
          <p>總計：<strong>{{ batchResult.total }}</strong> 個項目</p>
          <p class="success">成功：<strong>{{ batchResult.successful }}</strong> 個</p>
          <p v-if="batchResult.failed > 0" class="failed">失敗：<strong>{{ batchResult.failed }}</strong> 個</p>
          <p class="duration">耗時：<strong>{{ (batchResult.duration_ms / 1000).toFixed(1) }}</strong> 秒</p>
        </div>

        <div v-if="batchResult.failed > 0" class="failed-items">
          <h4>失敗項目：</h4>
          <ul>
            <li v-for="item in batchResult.failed_items" :key="item.knowledge_id">
              #{{ item.knowledge_id }} - {{ getQuestionById(item.knowledge_id) }}
              <br>
              <span class="error">錯誤：{{ item.error }}</span>
            </li>
          </ul>
        </div>
      </div>
      <div class="modal-footer">
        <button @click="closeBatchResult" class="btn-secondary">關閉</button>
        <button
          v-if="batchResult.failed > 0"
          @click="retryFailedItems"
          class="btn-primary"
        >
          重試失敗項目（{{ batchResult.failed }}）
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      showBatchResultDialog: false,
      batchResult: {
        total: 0,
        successful: 0,
        failed: 0,
        failed_items: [],
        duration_ms: 0,
      },
    };
  },
  methods: {
    getQuestionById(id) {
      return this.items.find(i => i.id === id)?.question || '未知';
    },
    closeBatchResult() {
      this.showBatchResultDialog = false;
    },
    retryFailedItems() {
      const failedIds = this.batchResult.failed_items.map(i => i.knowledge_id);
      this.selectedIds = failedIds;
      this.closeBatchResult();
      this.showBatchConfirm(this.batchAction);
    },
  },
};
</script>
```

---

### 6. 批量審核執行邏輯 ❌

**需要新增**：
```javascript
async confirmBatchReview() {
  // 關閉確認對話框，開啟進度對話框
  this.showBatchConfirmDialog = false;
  this.showBatchProgressDialog = true;

  // 初始化進度
  this.batchProgress = {
    total: this.selectedIds.length,
    processed: 0,
    currentItem: null,
    processedItems: [],
  };

  const startTime = Date.now();

  // 逐一處理（與後端 batch-review API 不同，這裡是前端逐一調用以顯示即時進度）
  for (const id of this.selectedIds) {
    const item = this.items.find(i => i.id === id);
    this.batchProgress.currentItem = item;

    try {
      // 調用單一審核 API
      await this.reviewItem(item, this.batchAction);

      this.batchProgress.processedItems.push({
        id: item.id,
        question: item.question,
        success: true,
      });
    } catch (error) {
      this.batchProgress.processedItems.push({
        id: item.id,
        question: item.question,
        success: false,
        error: error.response?.data?.detail || error.message,
      });
    }

    this.batchProgress.processed++;
  }

  this.batchProgress.currentItem = null;

  // 計算結果統計
  const successful = this.batchProgress.processedItems.filter(i => i.success).length;
  const failed = this.batchProgress.processedItems.filter(i => !i.success).length;
  const duration_ms = Date.now() - startTime;

  this.batchResult = {
    total: this.selectedIds.length,
    successful,
    failed,
    failed_items: this.batchProgress.processedItems
      .filter(i => !i.success)
      .map(i => ({ knowledge_id: i.id, error: i.error })),
    duration_ms,
  };

  // 關閉進度對話框，開啟結果對話框
  this.showBatchProgressDialog = false;
  this.showBatchResultDialog = true;

  // 清空選取
  this.selectedIds = [];

  // 重新載入列表與統計
  await this.loadItems();
  await this.loadStats();
}
```

**注意**：這裡使用前端逐一調用單一審核 API（`reviewItem`），而非直接調用後端的批量審核 API（`POST /api/v1/loop-knowledge/batch-review`），因為：
1. 可以顯示即時進度（當前處理項目、已處理列表）
2. 可以逐項顯示成功/失敗狀態
3. 前端有更細緻的控制權

但這樣的缺點是：
- 網路開銷較大（N 次 API 調用 vs 1 次批量 API）
- 處理時間較長

**可選方案**：使用後端批量 API + 輪詢進度端點（需要後端補充進度查詢 API）

---

### 7. 分頁功能 ❌

**目前問題**：
- 列表只顯示前 50 筆（limit: 50）
- 無法查看後續項目
- 無法跳頁

**需要新增**：
```vue
<template>
  <div class="pagination" v-if="total > filters.limit">
    <button
      @click="previousPage"
      :disabled="filters.offset === 0"
      class="btn-secondary"
    >
      ← 上一頁
    </button>
    <span class="page-info">
      第 {{ currentPage }} 頁 / 共 {{ totalPages }} 頁
    </span>
    <button
      @click="nextPage"
      :disabled="filters.offset + filters.limit >= total"
      class="btn-secondary"
    >
      下一頁 →
    </button>
  </div>
</template>

<script>
export default {
  data() {
    return {
      filters: {
        limit: 50,
        offset: 0,
      },
      total: 0, // 需要從 API 回應取得
    };
  },
  computed: {
    currentPage() {
      return Math.floor(this.filters.offset / this.filters.limit) + 1;
    },
    totalPages() {
      return Math.ceil(this.total / this.filters.limit);
    },
  },
  methods: {
    previousPage() {
      if (this.filters.offset > 0) {
        this.filters.offset -= this.filters.limit;
        this.loadItems();
      }
    },
    nextPage() {
      if (this.filters.offset + this.filters.limit < this.total) {
        this.filters.offset += this.filters.limit;
        this.loadItems();
      }
    },
  },
};
</script>
```

**注意**：需要確認後端 API 是否返回 `total` 欄位。

---

## 實作策略

### 方案 A：逐步補充（推薦）

按照優先級逐步補充功能：

1. **Phase 1**：全選核取方塊 + 批量操作工具列（核心功能）
2. **Phase 2**：批量審核確認對話框（防止誤操作）
3. **Phase 3**：批量審核進度顯示 + 結果摘要（使用者體驗）
4. **Phase 4**：分頁功能（可選）

每個 Phase 完成後進行測試，確認功能正常再進行下一 Phase。

### 方案 B：直接調用後端批量 API

使用後端已實作的批量審核 API（`POST /api/v1/loop-knowledge/batch-review`），簡化前端邏輯：

**優點**：
- 網路開銷小（1 次 API 調用）
- 處理速度快（後端批次處理）
- 前端邏輯簡單

**缺點**：
- 無法顯示即時進度（需要後端補充進度查詢 API 或使用 WebSocket）
- 無法逐項顯示成功/失敗狀態（只能在最後顯示摘要）

**建議**：Phase 1-2 使用方案 A（前端逐一調用），Phase 3 可考慮改用方案 B（後端批量 API）+ 進度輪詢。

---

## 測試計畫

### 單元測試
- 全選/取消全選功能
- 部分選取狀態（indeterminate）
- 類型統計計算（sopCount, generalCount）
- 重複警告統計計算（warningStats）
- 分頁計算（currentPage, totalPages）

### 整合測試
- 選取 → 批量批准 → 確認 → 處理 → 結果顯示
- 選取 → 批量拒絕 → 確認 → 處理 → 結果顯示
- 部分失敗情境（embedding API 超時、知識不存在）
- 重試失敗項目功能

### 端對端測試
- 篩選 → 全選 → 批量批准 → 確認警告項目 → 執行 → 結果確認
- 分頁 → 跨頁選取 → 批量操作

---

## 時間估計

| Phase | 工作項目 | 預估時間 | 複雜度 |
|-------|---------|---------|--------|
| 1 | 全選核取方塊 + selectedIds 狀態管理 | 1-2 小時 | 低 |
| 1 | 批量操作工具列（UI + 統計計算） | 1-2 小時 | 低 |
| 2 | 批量審核確認對話框（UI + 統計計算） | 2-3 小時 | 中 |
| 3 | 批量審核進度顯示（UI + 即時更新） | 3-4 小時 | 高 |
| 3 | 批量審核結果摘要（UI + 重試功能） | 2-3 小時 | 中 |
| 3 | 批量審核執行邏輯（API 調用 + 錯誤處理） | 3-4 小時 | 高 |
| 4 | 分頁功能 | 1-2 小時 | 低 |
| - | 測試與除錯 | 3-4 小時 | - |
| **總計** | - | **16-24 小時** | - |

---

## 建議

1. **優先實作 Phase 1-2**（全選 + 批量操作工具列 + 確認對話框），這是批量審核的最低可用版本（MVP）。

2. **Phase 3（進度顯示 + 結果摘要）可延後實作**，如果時間緊迫，可以先使用簡單的載入動畫 + alert 提示。

3. **分頁功能視需求而定**，如果待審核知識數量通常 < 50 筆，可以暫時不實作。

4. **考慮使用後端批量 API**，可大幅簡化前端邏輯，但需要評估進度顯示的需求。

5. **參考 `batch_review_requirements.md` 的 UI 設計**，確保實作符合需求文件的規格。

---

## 相關文件

- [批量審核需求文件](../../docs/frontend/batch_review_requirements.md)
- [知識審核 API 文檔](../../docs/api/loop_knowledge_api.md)
- [設計文件](./design.md)
- [任務清單](./tasks.md)
