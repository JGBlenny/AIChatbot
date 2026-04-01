<template>
  <div class="backtest-view">
    <div class="page-header">
      <h2>🔄 知識完善迴圈系統</h2>
      <p class="page-description">透過迴圈管理、知識審核與回測結果，持續優化 AI 知識庫品質</p>
    </div>

    <!-- 迴圈選擇器（全域） -->
    <div class="global-loop-selector">
      <div class="selector-label">
        <span class="label-icon">🎯</span>
        <span class="label-text">當前迴圈：</span>
      </div>
      <select v-model="selectedLoopId" @change="onLoopChange" class="loop-select">
        <option :value="null">請選擇迴圈...</option>
        <option v-for="loop in availableLoops" :key="loop.loop_id" :value="loop.loop_id">
          #{{ loop.loop_id }} - {{ loop.loop_name }}
          ({{ getStatusLabel(loop.status) }}, 迭代: {{ loop.current_iteration }}/{{ loop.max_iterations }})
        </option>
      </select>
      <button @click="refreshLoops" class="btn-refresh-loops" :disabled="loadingLoops">
        {{ loadingLoops ? '載入中...' : '🔄 重新整理' }}
      </button>
      <div v-if="selectedLoopId" class="quick-info">
        <span class="info-item">業者: {{ getVendorName(selectedLoop?.vendor_id) }}</span>
        <span class="info-item">測試集: {{ selectedLoop?.total_scenarios || 0 }} 題</span>
        <span class="info-item">通過率: {{ formatPassRate(selectedLoop?.current_pass_rate) }}</span>
      </div>
    </div>

    <!-- Tab 導航 -->
    <div class="tab-navigation">
      <div
        class="tab-item"
        :class="{ active: activeTab === 'loop-management' }"
        @click="activeTab = 'loop-management'"
      >
        <span class="tab-icon">🔄</span>
        <span class="tab-label">迴圈管理</span>
      </div>
      <div
        class="tab-item"
        :class="{ active: activeTab === 'knowledge-review' }"
        @click="activeTab = 'knowledge-review'"
      >
        <span class="tab-icon">📝</span>
        <span class="tab-label">知識審核</span>
      </div>
      <div
        class="tab-item"
        :class="{ active: activeTab === 'backtest-results' }"
        @click="activeTab = 'backtest-results'"
      >
        <span class="tab-icon">📊</span>
        <span class="tab-label">回測結果</span>
      </div>
      <div
        class="tab-item"
        :class="{ active: activeTab === 'validation' }"
        @click="activeTab = 'validation'"
        title="可選功能"
      >
        <span class="tab-icon">✅</span>
        <span class="tab-label">驗證回測</span>
        <span class="beta-badge">Beta</span>
      </div>
    </div>

    <!-- Tab 內容區 -->
    <div class="tab-content">
      <!-- 迴圈管理 Tab -->
      <div v-if="activeTab === 'loop-management'" class="tab-pane">
        <LoopManagementTab :selected-loop-id="selectedLoopId" @loop-selected="onLoopSelected" />
      </div>

      <!-- 知識審核 Tab -->
      <div v-if="activeTab === 'knowledge-review'" class="tab-pane">
        <LoopKnowledgeReviewTab :loop-id="selectedLoopId" />
      </div>

      <!-- 回測結果 Tab -->
      <div v-if="activeTab === 'backtest-results'" class="tab-pane">
        <BacktestResultsTab :loop-id="selectedLoopId" />
      </div>

      <!-- 驗證回測 Tab -->
      <div v-if="activeTab === 'validation'" class="tab-pane">
        <ValidationTabPlaceholder />
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { API_ENDPOINTS } from '@/config/api';
import LoopManagementTab from '@/components/LoopManagementTab.vue';
import LoopKnowledgeReviewTab from '@/components/review/LoopKnowledgeReviewTab.vue';
import BacktestResultsTab from '@/components/BacktestResultsTab.vue';

export default {
  name: 'BacktestView',

  components: {
    LoopManagementTab,
    LoopKnowledgeReviewTab,
    BacktestResultsTab,
    ValidationTabPlaceholder: {
      template: `
        <div class="placeholder-tab">
          <div class="placeholder-content">
            <div class="placeholder-icon">🚧</div>
            <h3>驗證回測功能開發中</h3>
            <p>此功能為可選功能，用於快速驗證知識改善效果並檢測 Regression。</p>
            <div class="feature-list">
              <h4>規劃功能：</h4>
              <ul>
                <li>✅ 選擇驗證範圍（僅失敗、失敗+抽樣、全部）</li>
                <li>✅ 自訂抽樣比例（10%, 20%, 30%）</li>
                <li>✅ 執行驗證回測</li>
                <li>✅ Regression 檢測與警告</li>
                <li>✅ 驗證結果詳細報告</li>
              </ul>
            </div>
            <p class="note">
              <strong>注意：</strong>目前可透過「迴圈管理」Tab 執行完整迭代來驗證知識改善效果。
            </p>
          </div>
        </div>
      `
    }
  },

  data() {
    return {
      activeTab: 'loop-management',
      selectedLoopId: null,
      availableLoops: [],
      loadingLoops: false,
      vendors: []  // 從 API 載入
    };
  },

  computed: {
    selectedLoop() {
      if (!this.selectedLoopId) return null;
      return this.availableLoops.find(loop => loop.loop_id === this.selectedLoopId);
    }
  },

  async mounted() {
    // 同時載入迴圈列表和業者列表
    await Promise.all([
      this.loadLoops(),
      this.loadVendors()
    ]);

    // 從 URL query 參數讀取預設 Tab
    const tab = this.$route.query.tab;
    if (tab && ['loop-management', 'knowledge-review', 'backtest-results', 'validation'].includes(tab)) {
      this.activeTab = tab;
    }

    // 從 URL query 參數讀取 loopId
    const loopId = this.$route.query.loopId;
    if (loopId) {
      this.selectedLoopId = parseInt(loopId);
    }
  },

  watch: {
    activeTab(newTab) {
      if (this.$route.query.tab !== newTab) {
        this.$router.push({
          query: {
            ...this.$route.query,
            tab: newTab
          }
        });
      }
    },

    selectedLoopId(newLoopId) {
      // 更新 URL
      if (newLoopId !== null) {
        this.$router.push({
          query: {
            ...this.$route.query,
            loopId: newLoopId
          }
        });
      }
    }
  },

  methods: {
    async loadLoops() {
      this.loadingLoops = true;
      try {
        const response = await axios.get('/rag-api/v1/loops/');
        this.availableLoops = response.data;
      } catch (error) {
        console.error('載入迴圈列表失敗', error);
      } finally {
        this.loadingLoops = false;
      }
    },

    async loadVendors() {
      try {
        const response = await axios.get(API_ENDPOINTS.ragVendors);
        this.vendors = response.data.vendors || [];
      } catch (error) {
        console.error('載入業者列表失敗', error);
        this.vendors = [];
      }
    },

    async refreshLoops() {
      await Promise.all([
        this.loadLoops(),
        this.loadVendors()
      ]);
    },

    onLoopChange() {
      // 迴圈切換時通知子元件
      console.log('迴圈已切換:', this.selectedLoopId);
    },

    onLoopSelected(loopId) {
      // 從 LoopManagementTab 接收選中的迴圈
      this.selectedLoopId = loopId;
    },

    getStatusLabel(status) {
      const labels = {
        pending: '待啟動',
        running: '執行中',
        reviewing: '審核中',
        paused: '已暫停',
        completed: '已完成',
        failed: '失敗',
        cancelled: '已取消'
      };
      return labels[status?.toLowerCase()] || status;
    },

    getVendorName(vendorId) {
      const vendor = this.vendors.find(v => v.id === vendorId);
      return vendor?.name || `業者 ${vendorId}`;
    },

    formatPassRate(rate) {
      if (rate === null || rate === undefined) return '-';
      return `${(rate * 100).toFixed(1)}%`;
    }
  }
};
</script>

<style scoped>
.backtest-view {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

/* 頁面標題 */
.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0 0 10px 0;
  font-size: 28px;
  color: #333;
}

.page-description {
  margin: 0;
  font-size: 14px;
  color: #666;
}

/* 全域迴圈選擇器 */
.global-loop-selector {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  border-radius: 12px;
  margin-bottom: 25px;
  box-shadow: 0 4px 6px rgba(102, 126, 234, 0.3);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 15px;
}

.selector-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
  font-weight: 600;
  font-size: 16px;
}

.label-icon {
  font-size: 20px;
}

.loop-select {
  flex: 1;
  min-width: 300px;
  padding: 10px 15px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.95);
  font-size: 14px;
  font-weight: 500;
  color: #333;
  cursor: pointer;
  transition: all 0.2s;
}

.loop-select:hover {
  border-color: rgba(255, 255, 255, 0.6);
  background: white;
}

.loop-select:focus {
  outline: none;
  border-color: white;
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.3);
}

.btn-refresh-loops {
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.2);
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-radius: 8px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-refresh-loops:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.6);
}

.btn-refresh-loops:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.quick-info {
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
  width: 100%;
  margin-top: 5px;
}

.info-item {
  background: rgba(255, 255, 255, 0.2);
  padding: 6px 12px;
  border-radius: 6px;
  color: white;
  font-size: 13px;
  font-weight: 500;
}

/* Tab 導航樣式 */
.tab-navigation {
  display: flex;
  border-bottom: 2px solid #e0e0e0;
  margin-bottom: 30px;
  gap: 5px;
}

.tab-item {
  position: relative;
  padding: 14px 24px;
  cursor: pointer;
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 500;
  color: #666;
  user-select: none;
}

.tab-item:hover {
  background: #f5f5f5;
  color: #333;
}

.tab-item.active {
  color: #667eea;
  border-bottom-color: #667eea;
  background: #f0f4ff;
}

.tab-icon {
  font-size: 18px;
}

.tab-label {
  font-size: 15px;
}

.beta-badge {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Tab 內容區 */
.tab-content {
  min-height: 600px;
}

.tab-pane {
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 占位元件樣式 */
.placeholder-tab {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 500px;
  padding: 40px;
}

.placeholder-content {
  max-width: 600px;
  text-align: center;
  background: white;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.placeholder-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.placeholder-content h3 {
  margin: 0 0 15px 0;
  font-size: 24px;
  color: #333;
}

.placeholder-content p {
  margin: 0 0 20px 0;
  font-size: 15px;
  color: #666;
  line-height: 1.6;
}

.feature-list {
  text-align: left;
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin: 20px 0;
}

.feature-list h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #333;
}

.feature-list ul {
  margin: 0;
  padding-left: 20px;
}

.feature-list li {
  margin-bottom: 8px;
  color: #666;
  font-size: 14px;
  line-height: 1.5;
}

.note {
  background: #fff3cd;
  border: 1px solid #ffc107;
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 13px;
  color: #856404;
  text-align: left;
}

.note strong {
  color: #533f03;
}

/* 響應式設計 */
@media (max-width: 768px) {
  .backtest-view {
    padding: 15px;
  }

  .page-header h2 {
    font-size: 24px;
  }

  .tab-navigation {
    overflow-x: auto;
    flex-wrap: nowrap;
  }

  .tab-item {
    padding: 12px 16px;
    font-size: 14px;
    white-space: nowrap;
  }

  .tab-icon {
    font-size: 16px;
  }

  .placeholder-content {
    padding: 30px 20px;
  }

  .placeholder-icon {
    font-size: 48px;
  }
}
</style>
