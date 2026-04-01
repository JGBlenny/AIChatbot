# 前端迴圈管理界面需求定義

> **版本**: 1.0
> **建立時間**: 2026-03-27
> **對應任務**: Task 9.3

## 概述

本文件定義前端管理介面的迴圈管理功能需求，支援完整的知識完善迴圈生命週期管理。

---

## 功能需求

### 1. 啟動迴圈對話框

**觸發方式**: 點擊「啟動新迴圈」按鈕

**對話框標題**: `啟動知識完善迴圈`

**表單欄位**:

#### 1.1 迴圈名稱 (必填)

```vue
<el-form-item label="迴圈名稱" prop="loop_name" required>
  <el-input
    v-model="form.loop_name"
    placeholder="例如：包租業知識完善-第1批"
    maxlength="200"
    show-word-limit
  />
  <div class="field-hint">建議格式：業態-目的-批次編號</div>
</el-form-item>
```

**驗證規則**:
- 必填
- 最多 200 字元
- 建議包含批次編號（如「第1批」、「第2批」）

#### 1.2 批次大小 (必填)

```vue
<el-form-item label="批次大小" prop="batch_size" required>
  <el-input-number
    v-model="form.batch_size"
    :min="1"
    :max="3000"
    :step="50"
  />
  <div class="field-hint">
    建議值：
    <el-tag size="small" @click="form.batch_size = 50">50（快速驗證）</el-tag>
    <el-tag size="small" @click="form.batch_size = 500">500（標準測試）</el-tag>
    <el-tag size="small" @click="form.batch_size = 3000">3000（全面評估）</el-tag>
  </div>
</el-form-item>
```

**驗證規則**:
- 範圍：1-3000
- 建議值：50（快速驗證）、500（標準測試）、3000（全面評估）
- 預設值：50

#### 1.3 目標通過率 (必填)

```vue
<el-form-item label="目標通過率" prop="target_pass_rate" required>
  <el-slider
    v-model="form.target_pass_rate"
    :min="0"
    :max="100"
    :step="5"
    :format-tooltip="(val) => `${val}%`"
  />
  <div class="current-value">{{ form.target_pass_rate }}%</div>
  <div class="field-hint">
    迭代會持續執行直到通過率達到此目標或達到最大迭代次數
  </div>
</el-form-item>
```

**驗證規則**:
- 範圍：0-100%
- 步進：5%
- 預設值：85%
- 建議值：75%（寬鬆）、85%（標準）、95%（嚴格）

#### 1.4 最大迭代次數 (必填)

```vue
<el-form-item label="最大迭代次數" prop="max_iterations" required>
  <el-input-number
    v-model="form.max_iterations"
    :min="1"
    :max="50"
    :step="1"
  />
  <div class="field-hint">
    建議值：3-5 次（快速驗證）、10 次（標準測試）
  </div>
</el-form-item>
```

**驗證規則**:
- 範圍：1-50
- 預設值：10
- 建議值：3-5（快速驗證）、10（標準測試）

#### 1.5 成本預算上限 (選填)

```vue
<el-form-item label="成本預算上限（USD）" prop="budget_limit_usd">
  <el-input-number
    v-model="form.budget_limit_usd"
    :min="0"
    :precision="2"
    :step="10"
  />
  <div class="field-hint">
    選填。若設定，當成本超過此上限時迴圈會自動停止。
  </div>
</el-form-item>
```

**驗證規則**:
- 選填
- 最小值：0
- 精度：小數點後 2 位
- 建議值：50 題約 $10-20、500 題約 $50-100

#### 1.6 測試情境篩選 (進階選項)

```vue
<el-collapse v-model="activeAdvanced">
  <el-collapse-item title="進階選項" name="advanced">
    <el-form-item label="難度分布">
      <el-row :gutter="10">
        <el-col :span="8">
          <el-input-number
            v-model="form.difficulty_distribution.easy"
            :min="0"
            :max="100"
            placeholder="簡單 %"
          />
        </el-col>
        <el-col :span="8">
          <el-input-number
            v-model="form.difficulty_distribution.medium"
            :min="0"
            :max="100"
            placeholder="中等 %"
          />
        </el-col>
        <el-col :span="8">
          <el-input-number
            v-model="form.difficulty_distribution.hard"
            :min="0"
            :max="100"
            placeholder="困難 %"
          />
        </el-col>
      </el-row>
      <div class="field-hint">
        預設分布：簡單 20%、中等 50%、困難 30%
      </div>
    </el-form-item>

    <el-form-item label="父迴圈 ID（批次關聯）">
      <el-select
        v-model="form.parent_loop_id"
        placeholder="選擇父迴圈"
        clearable
      >
        <el-option
          v-for="loop in completedLoops"
          :key="loop.id"
          :label="`${loop.loop_name} (ID: ${loop.id})`"
          :value="loop.id"
        />
      </el-select>
      <div class="field-hint">
        若設定，系統會自動排除父迴圈已使用的測試情境
      </div>
    </el-form-item>
  </el-collapse-item>
</el-collapse>
```

#### 1.7 操作按鈕

```vue
<template #footer>
  <el-button @click="dialogVisible = false">取消</el-button>
  <el-button type="primary" @click="submitForm" :loading="submitting">
    啟動迴圈
  </el-button>
</template>
```

**完整表單範例**:
```vue
<template>
  <el-dialog
    v-model="dialogVisible"
    title="啟動知識完善迴圈"
    width="700px"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="140px"
    >
      <el-form-item label="迴圈名稱" prop="loop_name" required>
        <el-input
          v-model="form.loop_name"
          placeholder="例如：包租業知識完善-第1批"
          maxlength="200"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="批次大小" prop="batch_size" required>
        <el-input-number
          v-model="form.batch_size"
          :min="1"
          :max="3000"
          :step="50"
        />
        <el-button-group class="quick-set">
          <el-button size="small" @click="form.batch_size = 50">50</el-button>
          <el-button size="small" @click="form.batch_size = 500">500</el-button>
          <el-button size="small" @click="form.batch_size = 3000">3000</el-button>
        </el-button-group>
      </el-form-item>

      <el-form-item label="目標通過率" prop="target_pass_rate" required>
        <el-slider
          v-model="targetPassRatePercent"
          :min="0"
          :max="100"
          :step="5"
        />
        <span class="value-display">{{ targetPassRatePercent }}%</span>
      </el-form-item>

      <el-form-item label="最大迭代次數" prop="max_iterations" required>
        <el-input-number
          v-model="form.max_iterations"
          :min="1"
          :max="50"
        />
      </el-form-item>

      <el-form-item label="成本預算上限" prop="budget_limit_usd">
        <el-input-number
          v-model="form.budget_limit_usd"
          :min="0"
          :precision="2"
          placeholder="USD"
        />
      </el-form-item>

      <!-- 進階選項 -->
      <el-collapse v-model="activeAdvanced">
        <el-collapse-item title="進階選項" name="advanced">
          <!-- ... 難度分布、父迴圈 ID -->
        </el-collapse-item>
      </el-collapse>
    </el-form>

    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button
        type="primary"
        @click="submitForm"
        :loading="submitting"
      >
        啟動迴圈
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

const form = ref({
  loop_name: '',
  batch_size: 50,
  target_pass_rate: 0.85,
  max_iterations: 10,
  budget_limit_usd: null,
  difficulty_distribution: {
    easy: 20,
    medium: 50,
    hard: 30
  },
  parent_loop_id: null
});

const targetPassRatePercent = computed({
  get: () => Math.round(form.value.target_pass_rate * 100),
  set: (val) => { form.value.target_pass_rate = val / 100; }
});

const rules = {
  loop_name: [
    { required: true, message: '請輸入迴圈名稱', trigger: 'blur' },
    { max: 200, message: '最多 200 字元', trigger: 'blur' }
  ],
  batch_size: [
    { required: true, message: '請輸入批次大小', trigger: 'change' },
    { type: 'number', min: 1, max: 3000, message: '範圍：1-3000', trigger: 'change' }
  ],
  target_pass_rate: [
    { required: true, message: '請設定目標通過率', trigger: 'change' }
  ],
  max_iterations: [
    { required: true, message: '請設定最大迭代次數', trigger: 'change' },
    { type: 'number', min: 1, max: 50, message: '範圍：1-50', trigger: 'change' }
  ]
};

async function submitForm() {
  const valid = await formRef.value.validate();
  if (!valid) return;

  submitting.value = true;
  try {
    const response = await fetch('/api/v1/loops/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value)
    });

    const result = await response.json();

    // 跳轉到迴圈詳情頁面
    router.push({ name: 'LoopDetail', params: { id: result.loop_id } });

    dialogVisible.value = false;
  } catch (error) {
    ElMessage.error(`啟動失敗：${error.message}`);
  } finally {
    submitting.value = false;
  }
}
</script>
```

---

### 2. 迴圈列表頁面

**頁面路徑**: `/knowledge-completion/loops`

**布局結構**:
```
┌────────────────────────────────────────────────────────────┐
│  知識完善迴圈管理                        [啟動新迴圈]      │
├────────────────────────────────────────────────────────────┤
│  篩選：[狀態] [業者] [搜尋]                    [重新整理] │
├────────────────────────────────────────────────────────────┤
│  ID  │ 迴圈名稱  │ 狀態  │ 迭代 │ 通過率 │ 測試數 │ 操作 │
├────────────────────────────────────────────────────────────┤
│ 123  │ 包租...  │ 執行中 │ 2/10 │ 72%   │ 50    │ ... │
│ 122  │ 代管...  │ 審核中 │ 3/10 │ 78%   │ 50    │ ... │
│ 121  │ 包租...  │ 已完成 │ 5/10 │ 88%   │ 50    │ ... │
└────────────────────────────────────────────────────────────┘
│  顯示 1-20 筆，共 50 筆            [上一頁] [下一頁]      │
└────────────────────────────────────────────────────────────┘
```

#### 2.1 表格欄位

| 欄位 | 寬度 | 說明 | 範例 |
|------|------|------|------|
| ID | 80px | 迴圈 ID | 123 |
| 迴圈名稱 | 200px | loop_name，可點擊查看詳情 | 包租業知識完善-第1批 |
| 狀態 | 100px | 狀態標籤（不同顏色） | 執行中（藍色）、審核中（橙色）、已完成（綠色）、失敗（紅色） |
| 迭代進度 | 100px | current_iteration / max_iterations | 2/10 |
| 當前通過率 | 100px | current_pass_rate，進度條顯示 | 72% ████░░ |
| 目標通過率 | 100px | target_pass_rate | 85% |
| 測試情境數 | 100px | total_scenarios | 50 |
| 建立時間 | 150px | created_at，相對時間 | 2 小時前 |
| 操作 | 150px | 快捷操作按鈕 | 查看、執行、暫停、取消 |

#### 2.2 狀態標籤

```vue
<template>
  <el-tag :type="statusType(status)">
    {{ statusText(status) }}
  </el-tag>
</template>

<script setup>
function statusType(status: string): string {
  const map = {
    pending: 'info',
    running: 'primary',
    reviewing: 'warning',
    validating: 'warning',
    completed: 'success',
    failed: 'danger',
    paused: 'info',
    cancelled: 'info'
  };
  return map[status] || 'info';
}

function statusText(status: string): string {
  const map = {
    pending: '等待執行',
    running: '執行中',
    reviewing: '審核中',
    validating: '驗證中',
    completed: '已完成',
    failed: '執行失敗',
    paused: '已暫停',
    cancelled: '已取消'
  };
  return map[status] || status;
}
</script>
```

#### 2.3 快捷操作按鈕

```vue
<template>
  <el-table-column label="操作" width="180" fixed="right">
    <template #default="{ row }">
      <el-button-group>
        <!-- 查看詳情 -->
        <el-button
          size="small"
          icon="View"
          @click="viewDetail(row.loop_id)"
        >
          查看
        </el-button>

        <!-- 執行迭代（僅 reviewing 狀態） -->
        <el-button
          v-if="row.status === 'reviewing'"
          size="small"
          type="primary"
          icon="CaretRight"
          @click="executeIteration(row.loop_id)"
        >
          執行
        </el-button>

        <!-- 暫停（僅 running 狀態） -->
        <el-button
          v-if="row.status === 'running'"
          size="small"
          type="warning"
          icon="VideoPause"
          @click="pauseLoop(row.loop_id)"
        >
          暫停
        </el-button>

        <!-- 恢復（僅 paused 狀態） -->
        <el-button
          v-if="row.status === 'paused'"
          size="small"
          type="success"
          icon="VideoPlay"
          @click="resumeLoop(row.loop_id)"
        >
          恢復
        </el-button>

        <!-- 更多操作 -->
        <el-dropdown trigger="click">
          <el-button size="small" icon="More" />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                icon="Delete"
                @click="cancelLoop(row.loop_id)"
              >
                取消迴圈
              </el-dropdown-item>
              <el-dropdown-item
                icon="Download"
                @click="exportLoop(row.loop_id)"
              >
                匯出結果
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-button-group>
    </template>
  </el-table-column>
</template>
```

---

### 3. 迴圈詳情對話框

**觸發方式**: 點擊迴圈名稱或「查看」按鈕

**對話框標題**: `迴圈詳情 - {loop_name}`

**分頁結構**:
```
[基本資訊] [固定測試集] [迭代歷史] [生成知識統計]
```

#### 3.1 基本資訊頁籤

```vue
<template>
  <el-descriptions :column="2" border>
    <el-descriptions-item label="迴圈 ID">
      {{ loop.loop_id }}
    </el-descriptions-item>
    <el-descriptions-item label="迴圈名稱">
      {{ loop.loop_name }}
    </el-descriptions-item>
    <el-descriptions-item label="業者 ID">
      {{ loop.vendor_id }}
    </el-descriptions-item>
    <el-descriptions-item label="狀態">
      <el-tag :type="statusType(loop.status)">
        {{ statusText(loop.status) }}
      </el-tag>
    </el-descriptions-item>
    <el-descriptions-item label="迭代進度">
      {{ loop.current_iteration }} / {{ loop.max_iterations }}
    </el-descriptions-item>
    <el-descriptions-item label="當前通過率">
      <el-progress
        :percentage="Math.round((loop.current_pass_rate || 0) * 100)"
        :color="progressColor"
      />
    </el-descriptions-item>
    <el-descriptions-item label="目標通過率">
      {{ Math.round(loop.target_pass_rate * 100) }}%
    </el-descriptions-item>
    <el-descriptions-item label="測試情境數">
      {{ loop.total_scenarios }}
    </el-descriptions-item>
    <el-descriptions-item label="建立時間">
      {{ formatDate(loop.created_at) }}
    </el-descriptions-item>
    <el-descriptions-item label="完成時間">
      {{ loop.completed_at ? formatDate(loop.completed_at) : '-' }}
    </el-descriptions-item>
  </el-descriptions>
</template>
```

#### 3.2 固定測試集頁籤

```vue
<template>
  <div class="scenario-info">
    <h4>測試集資訊</h4>
    <el-descriptions :column="2" border>
      <el-descriptions-item label="選取策略">
        {{ strategyText(loop.scenario_selection_strategy) }}
      </el-descriptions-item>
      <el-descriptions-item label="總數">
        {{ loop.scenario_ids.length }}
      </el-descriptions-item>
      <el-descriptions-item label="難度分布" :span="2">
        <el-row :gutter="10">
          <el-col :span="8">
            <el-statistic title="簡單" :value="loop.difficulty_distribution.easy" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="中等" :value="loop.difficulty_distribution.medium" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="困難" :value="loop.difficulty_distribution.hard" />
          </el-col>
        </el-row>
      </el-descriptions-item>
    </el-descriptions>

    <h4>測試情境 ID 列表</h4>
    <el-tag
      v-for="id in loop.scenario_ids"
      :key="id"
      class="scenario-tag"
    >
      #{{ id }}
    </el-tag>
  </div>
</template>
```

#### 3.3 迭代歷史頁籤

```vue
<template>
  <el-timeline>
    <el-timeline-item
      v-for="iter in iterations"
      :key="iter.iteration"
      :timestamp="formatDate(iter.created_at)"
      placement="top"
    >
      <el-card>
        <h4>迭代 {{ iter.iteration }}</h4>
        <p>通過率：{{ Math.round(iter.pass_rate * 100) }}%</p>
        <p>生成知識：{{ iter.knowledge_generated }} 個</p>
        <p>已批准：{{ iter.knowledge_approved }} 個</p>
        <p>耗時：{{ formatDuration(iter.duration_seconds) }}</p>
        <el-button
          size="small"
          @click="viewIterationDetail(iter.iteration)"
        >
          查看詳情
        </el-button>
      </el-card>
    </el-timeline-item>
  </el-timeline>
</template>
```

#### 3.4 生成知識統計頁籤

```vue
<template>
  <div class="knowledge-stats">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-statistic title="總生成數" :value="stats.total_generated" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="已批准" :value="stats.approved" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="已拒絕" :value="stats.rejected" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="待審核" :value="stats.pending" />
      </el-col>
    </el-row>

    <h4>知識類型分布</h4>
    <div ref="chartRef" style="height: 300px"></div>
  </div>
</template>

<script setup>
import * as echarts from 'echarts';

onMounted(() => {
  const chart = echarts.init(chartRef.value);
  chart.setOption({
    title: { text: '知識類型分布' },
    series: [{
      type: 'pie',
      data: [
        { name: 'SOP 知識', value: stats.sop_count },
        { name: '通用知識', value: stats.general_count }
      ]
    }]
  });
});
</script>
```

---

### 4. 執行迭代按鈕

**位置**: 迴圈詳情對話框底部 / 迴圈列表操作欄

**顯示條件**:
- `status === 'reviewing'` 或 `status === 'pending'`
- `current_iteration < max_iterations`

**按鈕樣式**:
```vue
<el-button
  type="primary"
  icon="CaretRight"
  :loading="executing"
  @click="executeIteration"
>
  執行迭代
</el-button>
```

**觸發行為**:
1. 顯示確認對話框
2. 調用 API: `POST /loops/{loop_id}/execute-iteration`
3. 啟動輪詢機制（每 5 秒查詢狀態）
4. 顯示進度對話框

**確認對話框**:
```vue
<el-message-box
  type="warning"
  title="執行迭代確認"
  message="即將執行第 3 次迭代，預計耗時 10-15 分鐘，是否繼續？"
  show-cancel-button
  confirm-button-text="確認執行"
  cancel-button-text="取消"
/>
```

---

### 5. 輪詢狀態機制

**輪詢頻率**: 每 5 秒

**觸發條件**: `status === 'running'`

**停止條件**:
- `status === 'reviewing'`
- `status === 'completed'`
- `status === 'failed'`
- 用戶離開頁面

**實作範例**:
```typescript
let pollingInterval: number | null = null;

function startPolling(loopId: number) {
  stopPolling(); // 先停止舊的輪詢

  pollingInterval = setInterval(async () => {
    try {
      const response = await fetch(`/api/v1/loops/${loopId}`);
      const status = await response.json();

      // 更新狀態
      loopStatus.value = status;

      // 檢查是否應停止輪詢
      if (['reviewing', 'completed', 'failed', 'cancelled'].includes(status.status)) {
        stopPolling();

        // 顯示通知
        if (status.status === 'reviewing') {
          ElNotification({
            title: '迭代執行完成',
            message: '請前往審核中心審核生成的知識',
            type: 'success',
            duration: 0
          });
        } else if (status.status === 'failed') {
          ElNotification({
            title: '迭代執行失敗',
            message: status.progress.message || '請查看詳情',
            type: 'error',
            duration: 0
          });
        }
      }
    } catch (error) {
      console.error('輪詢失敗:', error);
    }
  }, 5000);
}

function stopPolling() {
  if (pollingInterval) {
    clearInterval(pollingInterval);
    pollingInterval = null;
  }
}

onUnmounted(() => {
  stopPolling();
});
```

---

### 6. 進度顯示

**顯示位置**:
- 迴圈詳情對話框內（即時更新）
- 迴圈列表頁面的狀態欄（簡化顯示）

**進度資訊**:
```typescript
interface Progress {
  phase: string;        // backtest/analyzing/classifying/generating/reviewing
  percentage: number;   // 0-100
  message: string;      // 詳細進度說明
}
```

**UI 實作**:
```vue
<template>
  <div class="progress-display" v-if="loopStatus.status === 'running'">
    <h4>{{ phaseText(loopStatus.progress.phase) }}</h4>
    <el-progress
      :percentage="loopStatus.progress.percentage"
      :status="progressStatus"
    >
      <template #default="{ percentage }">
        <span class="percentage-value">{{ percentage }}%</span>
      </template>
    </el-progress>
    <p class="progress-message">{{ loopStatus.progress.message }}</p>
  </div>
</template>

<script setup>
function phaseText(phase: string): string {
  const map = {
    backtest: '執行回測',
    analyzing: '分析失敗案例',
    classifying: '智能分類',
    clustering: '聚類分析',
    generating: '生成知識',
    reviewing: '等待審核',
    validating: '驗證回測'
  };
  return map[phase] || phase;
}

const progressStatus = computed(() => {
  const percentage = loopStatus.value.progress.percentage;
  if (percentage === 100) return 'success';
  if (percentage >= 80) return 'warning';
  return undefined;
});
</script>
```

**進度訊息範例**:
- `"正在執行回測：已完成 22/50 個測試情境"`
- `"正在分析失敗案例：已找到 14 個知識缺口"`
- `"正在智能分類：已分類 10/14 個缺口"`
- `"正在生成知識：已處理 8/14 個失敗案例"`

---

### 7. 暫停/恢復/取消按鈕

#### 7.1 暫停按鈕

**顯示條件**: `status === 'running'`

**按鈕樣式**:
```vue
<el-button
  type="warning"
  icon="VideoPause"
  @click="pauseLoop"
>
  暫停迴圈
</el-button>
```

**確認對話框**:
```vue
<el-message-box
  type="warning"
  title="暫停迴圈確認"
  message="暫停後可稍後恢復執行。當前步驟會執行完畢後才會暫停。是否繼續？"
  show-cancel-button
/>
```

**API 調用**:
```typescript
async function pauseLoop(loopId: number) {
  const confirmed = await ElMessageBox.confirm(
    '暫停後可稍後恢復執行。當前步驟會執行完畢後才會暫停。是否繼續？',
    '暫停迴圈確認',
    { type: 'warning' }
  );

  if (confirmed) {
    await fetch(`/api/v1/loops/${loopId}/pause`, { method: 'POST' });
    ElMessage.success('迴圈已暫停');
    await refreshLoopStatus();
  }
}
```

#### 7.2 恢復按鈕

**顯示條件**: `status === 'paused'`

**按鈕樣式**:
```vue
<el-button
  type="success"
  icon="VideoPlay"
  @click="resumeLoop"
>
  恢復迴圈
</el-button>
```

**API 調用**:
```typescript
async function resumeLoop(loopId: number) {
  await fetch(`/api/v1/loops/${loopId}/resume`, { method: 'POST' });
  ElMessage.success('迴圈已恢復');
  startPolling(loopId);
  await refreshLoopStatus();
}
```

#### 7.3 取消按鈕

**顯示條件**: `status !== 'completed' && status !== 'cancelled'`

**按鈕樣式**:
```vue
<el-button
  type="danger"
  icon="Close"
  @click="cancelLoop"
>
  取消迴圈
</el-button>
```

**確認對話框**:
```vue
<el-message-box
  type="error"
  title="取消迴圈確認"
  message="取消後無法恢復執行，已生成但未審核的知識將保留。是否確定取消？"
  show-cancel-button
  confirm-button-text="確定取消"
  cancel-button-text="我再想想"
/>
```

**API 調用**:
```typescript
async function cancelLoop(loopId: number) {
  const confirmed = await ElMessageBox.confirm(
    '取消後無法恢復執行，已生成但未審核的知識將保留。是否確定取消？',
    '取消迴圈確認',
    {
      type: 'error',
      confirmButtonText: '確定取消',
      cancelButtonText: '我再想想'
    }
  );

  if (confirmed) {
    await fetch(`/api/v1/loops/${loopId}/cancel`, { method: 'POST' });
    ElMessage.success('迴圈已取消');
    stopPolling();
    await refreshLoopStatus();
  }
}
```

---

## 頁面路由設計

```typescript
const routes = [
  {
    path: '/knowledge-completion',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      {
        path: 'loops',
        name: 'LoopList',
        component: () => import('@/views/LoopManagement/LoopList.vue'),
        meta: { title: '迴圈管理', icon: 'Loop' }
      },
      {
        path: 'loops/:id',
        name: 'LoopDetail',
        component: () => import('@/views/LoopManagement/LoopDetail.vue'),
        meta: { title: '迴圈詳情', hidden: true }
      },
      {
        path: 'review-center',
        name: 'ReviewCenter',
        component: () => import('@/views/ReviewCenter/Index.vue'),
        meta: { title: '審核中心', icon: 'Document' }
      }
    ]
  }
];
```

---

## 效能要求

| 指標 | 目標值 | 說明 |
|-----|--------|------|
| 列表頁面載入時間 | < 1 秒 | 顯示 20 筆迴圈記錄 |
| 詳情頁面載入時間 | < 500ms | 包含基本資訊、固定測試集、迭代歷史 |
| 輪詢 API 回應時間 | < 300ms | GET /loops/{loop_id} |
| 執行迭代 API 回應時間 | < 1 秒 | POST /loops/{loop_id}/execute-iteration（非同步模式） |

---

## 變更歷史

| 日期 | 版本 | 變更內容 | 修改者 |
|------|------|---------|--------|
| 2026-03-27 | 1.0 | 初始版本 | AI Assistant |

---

**相關文件**:
- [迴圈管理 API 文檔](../api/loops_api.md)
- [批量選取功能需求](./batch_review_requirements.md)
- [設計文件](../../.kiro/specs/backtest-knowledge-refinement/design.md)
