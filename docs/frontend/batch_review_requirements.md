# 前端批量選取功能需求定義

> **版本**: 1.0
> **建立時間**: 2026-03-27
> **對應任務**: Task 9.2

## 概述

本文件定義審核中心的批量操作界面需求，支援高效審核 10-100 個知識項目的批量操作功能。

---

## 功能需求

### 1. 全選核取方塊

#### 1.1 當前頁全選

**位置**: 表格標題列（thead）第一欄

**功能**:
- 點擊後選取/取消選取當前頁所有項目
- 狀態顯示：
  - ☐ 未選取（當前頁無項目被選中）
  - ☑ 全選（當前頁所有項目被選中）
  - ☑ 部分選取（當前頁部分項目被選中，使用中間狀態圖標）

**互動行為**:
```typescript
interface SelectAllBehavior {
  onClick: () => {
    if (allSelected) {
      // 取消選取所有項目
      selectedIds = [];
    } else {
      // 選取當前頁所有項目
      selectedIds = currentPageItems.map(item => item.id);
    }
  };
}
```

**UI 範例**:
```vue
<template>
  <th>
    <input
      type="checkbox"
      :checked="allSelected"
      :indeterminate="someSelected"
      @change="toggleSelectAll"
    />
  </th>
</template>

<script setup>
const allSelected = computed(() =>
  currentPageItems.length > 0 &&
  currentPageItems.every(item => selectedIds.includes(item.id))
);

const someSelected = computed(() =>
  !allSelected.value &&
  currentPageItems.some(item => selectedIds.includes(item.id))
);
</script>
```

#### 1.2 所有頁全選（進階功能）

**位置**: 批量操作工具列

**觸發條件**: 當篩選條件變更或點擊「全選所有頁」按鈕時

**功能**:
- 提供「選取所有符合條件的項目」功能
- 顯示提示訊息：「已選取所有 150 個項目（跨 3 頁）」
- 提供「僅選取當前頁」選項

**警告提示**:
```
⚠️ 您即將選取所有 150 個項目（跨 3 頁），是否繼續？
- 這可能需要較長處理時間
- 建議單次批量審核不超過 100 個項目
```

---

### 2. 篩選後全選功能

#### 2.1 篩選條件

**支援的篩選維度**:

| 篩選項目 | 類型 | 選項 | 說明 |
|---------|------|------|------|
| 迴圈 | 下拉選單 | 所有迴圈 / 特定迴圈 | 篩選特定迴圈的知識 |
| 知識類型 | 下拉選單 | 所有類型 / SOP / 通用 | 篩選 knowledge_type |
| 重複警告 | 下拉選單 | 全部 / 有警告 / 無警告 | 篩選 duplication_warning |
| 狀態 | 下拉選單 | pending / approved / rejected | 篩選 status |

**篩選邏輯**:
```typescript
const filteredItems = computed(() => {
  let items = allItems.value;

  // 迴圈篩選
  if (filters.loop_id) {
    items = items.filter(item => item.loop_id === filters.loop_id);
  }

  // 知識類型篩選
  if (filters.knowledge_type === 'sop') {
    items = items.filter(item => item.knowledge_type === 'sop');
  } else if (filters.knowledge_type === 'general') {
    items = items.filter(item => item.knowledge_type === null);
  }

  // 重複警告篩選
  if (filters.duplication_warning === 'has_warning') {
    items = items.filter(item => item.duplication_warning);
  } else if (filters.duplication_warning === 'no_warning') {
    items = items.filter(item => !item.duplication_warning);
  }

  // 狀態篩選
  if (filters.status) {
    items = items.filter(item => item.status === filters.status);
  }

  return items;
});
```

#### 2.2 篩選後全選

**使用場景範例**:
1. 篩選「重複警告 = 無」→ 全選 → 批量批准
2. 篩選「知識類型 = SOP」→ 全選 → 批量批准
3. 篩選「迴圈 = 123」→ 全選 → 批量批准

**UI 提示**:
```
已篩選出 45 個項目（無重複警告）
[全選篩選結果] [清除篩選]
```

---

### 3. 批量操作工具列

**位置**: 表格上方，篩選欄下方

**顯示條件**: `selectedIds.length > 0`

**UI 設計**:
```
┌─────────────────────────────────────────────────────────────┐
│  已選取 15 個項目  [批量批准] [批量拒絕] [取消選取]        │
└─────────────────────────────────────────────────────────────┘
```

**元件結構**:
```vue
<template>
  <div class="batch-actions" v-if="selectedIds.length > 0">
    <div class="batch-info">
      <span class="count">已選取 {{ selectedIds.length }} 個項目</span>
      <span class="type-breakdown" v-if="showTypeBreakdown">
        （SOP: {{ sopCount }}, 通用: {{ generalCount }}）
      </span>
    </div>
    <div class="batch-buttons">
      <button @click="batchApprove" class="btn-approve">
        批量批准
      </button>
      <button @click="batchReject" class="btn-reject">
        批量拒絕
      </button>
      <button @click="clearSelection" class="btn-secondary">
        取消選取
      </button>
    </div>
  </div>
</template>

<script setup>
const sopCount = computed(() =>
  selectedIds.value
    .map(id => items.find(i => i.id === id))
    .filter(item => item?.knowledge_type === 'sop')
    .length
);

const generalCount = computed(() =>
  selectedIds.value.length - sopCount.value
);
</script>
```

---

### 4. 確認對話框

**觸發時機**: 點擊「批量批准」或「批量拒絕」按鈕

**對話框內容**:

#### 4.1 標題
```
批量批准確認
```

#### 4.2 摘要資訊
```
您即將批准 15 個知識項目：

知識類型分布：
- SOP 知識：8 個
- 通用知識：7 個

重複警告統計：
- 無警告：12 個
- 有警告：3 個（相似度 85%-95%）

⚠️ 有 3 個項目檢測到重複警告，建議人工確認後再批准。
```

#### 4.3 操作按鈕
```
[確認批准] [返回檢查] [取消]
```

**UI 實作**:
```vue
<template>
  <el-dialog
    v-model="showConfirmDialog"
    title="批量批准確認"
    width="600px"
  >
    <div class="confirm-summary">
      <p>您即將批准 <strong>{{ selectedIds.length }}</strong> 個知識項目：</p>

      <h4>知識類型分布：</h4>
      <ul>
        <li>SOP 知識：{{ typeStats.sop }} 個</li>
        <li>通用知識：{{ typeStats.general }} 個</li>
      </ul>

      <h4>重複警告統計：</h4>
      <ul>
        <li>無警告：{{ warningStats.no_warning }} 個</li>
        <li v-if="warningStats.has_warning > 0" class="warning">
          有警告：{{ warningStats.has_warning }} 個
          （相似度 {{ warningStats.min_similarity }}-{{ warningStats.max_similarity }}%）
        </li>
      </ul>

      <el-alert
        v-if="warningStats.has_warning > 0"
        type="warning"
        :closable="false"
      >
        有 {{ warningStats.has_warning }} 個項目檢測到重複警告，建議人工確認後再批准。
      </el-alert>
    </div>

    <template #footer>
      <el-button @click="showConfirmDialog = false">取消</el-button>
      <el-button @click="reviewWarningItems">返回檢查</el-button>
      <el-button type="primary" @click="confirmBatchApprove">
        確認批准
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
const typeStats = computed(() => {
  const selected = selectedIds.value.map(id =>
    items.value.find(i => i.id === id)
  );

  return {
    sop: selected.filter(i => i.knowledge_type === 'sop').length,
    general: selected.filter(i => i.knowledge_type === null).length
  };
});

const warningStats = computed(() => {
  const selected = selectedIds.value.map(id =>
    items.value.find(i => i.id === id)
  );

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
    max_similarity: Math.max(...similarities)
  };
});
</script>
```

---

### 5. 處理進度顯示

**觸發時機**: 點擊「確認批准」後

**顯示內容**:

#### 5.1 進度條
```
批量批准處理中... 8/15 (53%)

[████████████░░░░░░░░░░] 53%
```

#### 5.2 當前處理項目
```
正在處理：租金繳納日期說明 (#12345)
```

#### 5.3 已處理項目列表（可選）
```
✓ #12340 - 租約續約流程
✓ #12341 - 報修申請說明
✗ #12342 - 繳費方式查詢（錯誤：embedding API 超時）
✓ #12343 - 停車位申請
...
```

**UI 實作**:
```vue
<template>
  <el-dialog
    v-model="showProgressDialog"
    title="批量批准處理中"
    width="700px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
  >
    <div class="progress-container">
      <div class="progress-summary">
        <h4>批量批准處理中... {{ processed }}/{{ total }} ({{ percentage }}%)</h4>
      </div>

      <el-progress
        :percentage="percentage"
        :status="progressStatus"
      ></el-progress>

      <div class="current-item" v-if="currentItem">
        <p>正在處理：{{ currentItem.question }} (#{{ currentItem.id }})</p>
      </div>

      <div class="processed-list">
        <h5>已處理項目：</h5>
        <ul>
          <li
            v-for="item in processedItems"
            :key="item.id"
            :class="{ success: item.success, failed: !item.success }"
          >
            <span class="icon">{{ item.success ? '✓' : '✗' }}</span>
            <span class="id">#{{ item.id }}</span>
            <span class="question">{{ item.question }}</span>
            <span v-if="!item.success" class="error">
              （{{ item.error }}）
            </span>
          </li>
        </ul>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
const processed = ref(0);
const total = ref(0);
const currentItem = ref(null);
const processedItems = ref([]);

const percentage = computed(() =>
  total.value > 0 ? Math.round((processed.value / total.value) * 100) : 0
);

const progressStatus = computed(() => {
  if (processed.value === total.value) {
    return processedItems.value.every(i => i.success) ? 'success' : 'warning';
  }
  return undefined;
});

async function processBatchReview() {
  total.value = selectedIds.value.length;
  processed.value = 0;
  processedItems.value = [];

  for (const id of selectedIds.value) {
    const item = items.value.find(i => i.id === id);
    currentItem.value = item;

    try {
      await reviewKnowledge(id, 'approve');
      processedItems.value.push({
        id: item.id,
        question: item.question,
        success: true
      });
    } catch (error) {
      processedItems.value.push({
        id: item.id,
        question: item.question,
        success: false,
        error: error.message
      });
    }

    processed.value++;
  }

  currentItem.value = null;
}
</script>
```

---

### 6. 結果摘要對話框

**觸發時機**: 批量處理完成後

**顯示內容**:

#### 6.1 成功/失敗統計
```
批量批准完成

總計：15 個項目
成功：13 個
失敗：2 個
耗時：5.4 秒
```

#### 6.2 失敗項目列表
```
失敗項目：

#12342 - 繳費方式查詢
錯誤：embedding API 超時

#12348 - 租約到期通知
錯誤：知識不存在
```

#### 6.3 操作按鈕
```
[重試失敗項目] [關閉]
```

**UI 實作**:
```vue
<template>
  <el-dialog
    v-model="showResultDialog"
    title="批量批准完成"
    width="700px"
  >
    <div class="result-summary">
      <el-result
        :icon="resultIcon"
        :title="resultTitle"
      >
        <template #sub-title>
          <div class="stats">
            <p>總計：{{ result.total }} 個項目</p>
            <p class="success">成功：{{ result.successful }} 個</p>
            <p class="failed" v-if="result.failed > 0">
              失敗：{{ result.failed }} 個
            </p>
            <p class="duration">耗時：{{ (result.duration_ms / 1000).toFixed(1) }} 秒</p>
          </div>
        </template>

        <template #extra>
          <div v-if="result.failed > 0" class="failed-items">
            <h4>失敗項目：</h4>
            <el-table
              :data="result.failed_items"
              border
              max-height="300"
            >
              <el-table-column prop="knowledge_id" label="ID" width="80" />
              <el-table-column label="問題" min-width="200">
                <template #default="{ row }">
                  {{ getQuestionById(row.knowledge_id) }}
                </template>
              </el-table-column>
              <el-table-column prop="error" label="錯誤訊息" min-width="200" />
            </el-table>
          </div>
        </template>
      </el-result>
    </div>

    <template #footer>
      <el-button @click="showResultDialog = false">關閉</el-button>
      <el-button
        v-if="result.failed > 0"
        type="primary"
        @click="retryFailedItems"
      >
        重試失敗項目（{{ result.failed }}）
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
const resultIcon = computed(() =>
  result.value.failed === 0 ? 'success' : 'warning'
);

const resultTitle = computed(() =>
  result.value.failed === 0
    ? `成功批准 ${result.value.successful} 個知識項目`
    : `批准完成，${result.value.failed} 個項目失敗`
);

function getQuestionById(id: number): string {
  return items.value.find(i => i.id === id)?.question || '未知';
}

async function retryFailedItems() {
  const failedIds = result.value.failed_items.map(i => i.knowledge_id);
  selectedIds.value = failedIds;
  showResultDialog.value = false;
  await processBatchReview();
}
</script>
```

---

## 使用流程

### 標準批量審核流程

```
1. 使用者進入審核中心
   ↓
2. 設定篩選條件（如：無重複警告）
   ↓
3. 點擊「全選篩選結果」或手動勾選項目
   ↓
4. 批量操作工具列顯示「已選取 X 個項目」
   ↓
5. 點擊「批量批准」按鈕
   ↓
6. 確認對話框顯示統計資訊
   ↓
7. 點擊「確認批准」
   ↓
8. 進度對話框顯示處理進度
   ↓
9. 結果摘要對話框顯示成功/失敗統計
   ↓
10. 若有失敗項目，可點擊「重試失敗項目」
```

---

## 技術規格

### API 調用

```typescript
// 批量審核 API
async function batchReview(knowledgeIds: number[], action: 'approve' | 'reject') {
  const response = await fetch('/api/v1/loop-knowledge/batch-review', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ knowledge_ids: knowledgeIds, action })
  });

  const result = await response.json();
  return result; // { total, successful, failed, failed_items, duration_ms }
}
```

### 狀態管理

```typescript
// Pinia store
import { defineStore } from 'pinia';

export const useReviewStore = defineStore('review', {
  state: () => ({
    items: [],
    selectedIds: [],
    filters: {
      loop_id: null,
      knowledge_type: null,
      duplication_warning: null,
      status: 'pending'
    },
    total: 0,
    limit: 50,
    offset: 0
  }),

  getters: {
    filteredItems(state) {
      // 前端篩選邏輯
    },

    selectedItems(state) {
      return state.selectedIds.map(id =>
        state.items.find(item => item.id === id)
      );
    },

    typeStats(state) {
      const selected = this.selectedItems;
      return {
        sop: selected.filter(i => i.knowledge_type === 'sop').length,
        general: selected.filter(i => i.knowledge_type === null).length
      };
    }
  },

  actions: {
    async fetchPendingKnowledge() {
      // 調用 API
    },

    toggleSelectAll() {
      if (this.allSelected) {
        this.selectedIds = [];
      } else {
        this.selectedIds = this.filteredItems.map(i => i.id);
      }
    },

    async batchReview(action: 'approve' | 'reject') {
      // 調用批量審核 API
    }
  }
});
```

---

## 效能要求

| 指標 | 目標值 | 說明 |
|-----|--------|------|
| 篩選回應時間 | < 300ms | 前端篩選邏輯 |
| 批量審核處理時間（10 個） | < 5 秒 | 包含 API 調用與 embedding 生成 |
| 批量審核處理時間（50 個） | < 20 秒 | 包含 API 調用與 embedding 生成 |
| 批量審核處理時間（100 個） | < 40 秒 | 包含 API 調用與 embedding 生成 |
| 進度更新頻率 | 即時 | 每處理一個項目更新一次 |

---

## UI/UX 設計原則

1. **明確的視覺回饋**
   - 選取狀態清晰可見（核取方塊、高亮背景）
   - 重複警告使用警告色圖標
   - 處理進度即時更新

2. **容錯設計**
   - 部分成功模式（一個失敗不影響其他）
   - 提供重試失敗項目功能
   - 顯示詳細錯誤訊息

3. **防止誤操作**
   - 批量操作前顯示確認對話框
   - 重複警告項目特別提示
   - 處理過程中禁用操作按鈕

4. **效能優化**
   - 前端篩選（減少 API 調用）
   - 虛擬滾動（大量項目時）
   - 分批處理（避免一次處理過多項目）

---

## 變更歷史

| 日期 | 版本 | 變更內容 | 修改者 |
|------|------|---------|--------|
| 2026-03-27 | 1.0 | 初始版本 | AI Assistant |

---

**相關文件**:
- [知識審核 API 文檔](../api/loop_knowledge_api.md)
- [迴圈管理界面需求](./loop_management_requirements.md)
- [設計文件](../../.kiro/specs/backtest-knowledge-refinement/design.md)
