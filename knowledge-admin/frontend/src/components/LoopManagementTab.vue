<template>
  <div class="loop-management-tab">
    <h3>🔄 知識完善迴圈管理</h3>

    <!-- 覆蓋率統計 -->
    <div v-if="coverageStats && !selectedLoopId" class="coverage-stats-card">
      <div class="coverage-header">
        <span class="coverage-title">回測覆蓋率</span>
        <span class="coverage-percentage" :class="getCoverageClass(coverageStats.coverage_rate)">
          {{ coverageStats.coverage_rate }}%
        </span>
      </div>
      <div class="coverage-progress-bar">
        <div class="coverage-progress-fill" :style="{ width: coverageStats.coverage_rate + '%' }" :class="getCoverageClass(coverageStats.coverage_rate)"></div>
      </div>
      <div class="coverage-details">
        <span>已覆蓋 {{ coverageStats.covered_scenarios }} / {{ coverageStats.total_scenarios }} 題</span>
        <span v-if="coverageStats.uncovered_scenarios > 0" class="uncovered-hint">
          （剩餘 {{ coverageStats.uncovered_scenarios }} 題未測）
        </span>
      </div>
    </div>

    <!-- 工具列（⚠️ 執行面已於 2026-09 移除，見 loops.py 檔頭說明；本頁僅供檢視與知識審核） -->
    <div class="toolbar">
      <button @click="refreshLoops" class="btn btn-refresh" :disabled="loading">
        🔄 {{ loading ? '載入中...' : '重新整理' }}
      </button>
    </div>

    <!-- 載入狀態 -->
    <div v-if="loading && loops.length === 0" class="loading-state">
      <p>載入迴圈列表中...</p>
    </div>

    <!-- 錯誤狀態 -->
    <div v-else-if="error" class="error-state">
      <p class="error-message">❌ {{ error }}</p>
      <button @click="refreshLoops" class="btn btn-secondary">重試</button>
    </div>

    <!-- 迴圈列表 -->
    <div v-else-if="loops.length > 0" class="loops-table-container">
      <!-- 選中迴圈提示 -->
      <div v-if="selectedLoopId && displayLoops.length > 0" class="selected-loop-info">
        📌 當前查看：迴圈 #{{ selectedLoopId }}
      </div>
      <div v-else-if="selectedLoopId && displayLoops.length === 0" class="no-loop-selected">
        ⚠️ 找不到迴圈 #{{ selectedLoopId }}
      </div>

      <table class="loops-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>名稱</th>
            <th>業者</th>
            <th>狀態</th>
            <th>迭代</th>
            <th>通過率</th>
            <th>測試集大小</th>
            <th>更新時間</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="loop in displayLoops" :key="loop.loop_id" :class="{ 'row-running': isRunningStatus(loop.status) }">
            <td>{{ loop.loop_id }}</td>
            <td class="loop-name clickable" @click="$emit('loop-selected', loop.loop_id)">{{ loop.loop_name }}</td>
            <td>{{ getVendorName(loop.vendor_id) }}</td>
            <td>
              <span class="status-badge" :class="`status-${loop.status.toLowerCase()}`">
                {{ getStatusLabel(loop.status) }}
              </span>
            </td>
            <td>{{ loop.current_iteration }}</td>
            <td>
              <span class="pass-rate" :class="getPassRateClass(loop.current_pass_rate)">
                {{ formatPassRate(loop.current_pass_rate) }}
              </span>
            </td>
            <td>{{ loop.total_scenarios }} 題</td>
            <td class="timestamp">{{ formatDateTime(loop.updated_at) }}</td>
            <td class="actions">
              <button @click="viewDetails(loop)" class="btn-action btn-view" title="查看詳情">
                👁️
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 空狀態 -->
    <div v-else class="empty-state">
      <p>尚無迴圈記錄</p>
    </div>

    <!-- 查看迴圈詳情 Modal -->
    <div v-if="showDetailsModal" class="modal-overlay" @click.self="closeDetailsModal">
      <div class="modal-content modal-large">
        <div class="modal-header">
          <h3>🔍 迴圈詳情</h3>
          <button class="close-btn" @click="closeDetailsModal">✕</button>
        </div>
        <div class="modal-body">
          <div v-if="loadingDetails" class="loading-details">
            <p>載入詳情中...</p>
          </div>
          <div v-else-if="selectedLoop" class="details-content">
            <!-- 基本資訊 -->
            <div class="details-section">
              <h4>📋 基本資訊</h4>
              <div class="info-grid">
                <div class="info-item">
                  <label>迴圈 ID：</label>
                  <span>{{ selectedLoop.loop_id }}</span>
                </div>
                <div class="info-item">
                  <label>迴圈名稱：</label>
                  <span>{{ selectedLoop.loop_name }}</span>
                </div>
                <div class="info-item">
                  <label>業者：</label>
                  <span>{{ getVendorName(selectedLoop.vendor_id) }}</span>
                </div>
                <div class="info-item">
                  <label>狀態：</label>
                  <span class="status-badge" :class="`status-${selectedLoop.status.toLowerCase()}`">
                    {{ getStatusLabel(selectedLoop.status) }}
                  </span>
                </div>
                <div class="info-item">
                  <label>當前迭代：</label>
                  <span>{{ selectedLoop.current_iteration }}</span>
                </div>
                <div class="info-item">
                  <label>目標通過率：</label>
                  <span>{{ formatPassRate(selectedLoop.target_pass_rate) }}</span>
                </div>
                <div class="info-item">
                  <label>當前通過率：</label>
                  <span class="pass-rate" :class="getPassRateClass(selectedLoop.current_pass_rate)">
                    {{ formatPassRate(selectedLoop.current_pass_rate) }}
                  </span>
                </div>
                <div class="info-item">
                  <label>建立時間：</label>
                  <span>{{ formatDateTime(selectedLoop.created_at) }}</span>
                </div>
                <div class="info-item">
                  <label>更新時間：</label>
                  <span>{{ formatDateTime(selectedLoop.updated_at) }}</span>
                </div>
                <div class="info-item" v-if="selectedLoop.completed_at">
                  <label>完成時間：</label>
                  <span>{{ formatDateTime(selectedLoop.completed_at) }}</span>
                </div>
              </div>
            </div>

            <!-- 固定測試集 -->
            <div class="details-section">
              <h4>📝 固定測試集</h4>
              <div class="test-set-info">
                <div class="info-item">
                  <label>測試集大小：</label>
                  <span>{{ selectedLoop.total_scenarios }} 題</span>
                </div>
                <div class="info-item">
                  <label>選取策略：</label>
                  <span>分層隨機抽樣</span>
                </div>
                <div v-if="selectedLoop.scenario_ids && selectedLoop.scenario_ids.length > 0" class="info-item">
                  <label>測試集 ID：</label>
                  <span class="scenario-ids">{{ formatScenarioIds(selectedLoop.scenario_ids) }}</span>
                </div>
              </div>
            </div>

            <!-- 迭代歷史 -->
            <div class="details-section">
              <h4>📊 迭代歷史</h4>
              <div v-if="iterationHistory.length === 0" class="empty-history">
                <p>尚無迭代記錄</p>
              </div>
              <div v-else>
                <table class="iteration-table">
                  <thead>
                    <tr>
                      <th>迭代輪次</th>
                      <th>通過率</th>
                      <th>改善幅度</th>
                      <th>通過數</th>
                      <th>失敗數</th>
                      <th>生成知識</th>
                      <th>執行時間</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(iteration, index) in iterationHistory" :key="iteration.iteration"
                        :class="{ 'current-iteration': iteration.iteration === selectedLoop.current_iteration }">
                      <td>
                        <span class="iteration-badge" :class="{ 'is-current': iteration.iteration === selectedLoop.current_iteration }">
                          第 {{ iteration.iteration }} 輪
                        </span>
                      </td>
                      <td>
                        <span class="pass-rate" :class="getPassRateClass(iteration.pass_rate)">
                          {{ formatPassRate(iteration.pass_rate) }}
                        </span>
                      </td>
                      <td>
                        <span v-if="index > 0" class="improvement-badge" :class="getImprovementClass(iteration.pass_rate, iterationHistory[index - 1].pass_rate)">
                          {{ formatImprovement(iteration.pass_rate, iterationHistory[index - 1].pass_rate) }}
                        </span>
                        <span v-else class="improvement-badge neutral">-</span>
                      </td>
                      <td class="pass-count">{{ iteration.passed }}</td>
                      <td class="fail-count">{{ iteration.failed }}</td>
                      <td>{{ iteration.knowledge_generated }}</td>
                      <td class="timestamp">{{ formatDateTime(iteration.completed_at) }}</td>
                    </tr>
                  </tbody>
                </table>

                <!-- 通過率趨勢圖 -->
                <div class="chart-container">
                  <h5>📈 通過率趨勢</h5>
                  <canvas ref="trendChart" width="400" height="200"></canvas>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="closeDetailsModal" class="btn btn-secondary">關閉</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'LoopManagementTab',
  props: {
    selectedLoopId: {
      type: Number,
      default: null
    }
  },
  data() {
    return {
      loops: [],
      loading: false,
      error: null,
      coverageStats: null,
      // 查看詳情相關
      showDetailsModal: false,
      loadingDetails: false,
      selectedLoop: null,
      iterationHistory: [],
      trendChartInstance: null
    };
  },
  computed: {
    displayLoops() {
      // 如果有選中的迴圈，只顯示該迴圈；否則顯示所有
      if (this.selectedLoopId) {
        return this.loops.filter(loop => loop.loop_id === this.selectedLoopId);
      }
      return this.loops;
    }
  },
  mounted() {
    this.loadLoops();
    this.loadCoverageStats();
  },
  watch: {
    selectedLoopId(newVal) {
      // 當選中的迴圈改變時，重新載入資料
      if (newVal !== null) {
        this.loadLoops();
      }
    }
  },
  methods: {
    async loadLoops() {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.get('/rag-api/v1/loops/');
        this.loops = response.data;
      } catch (err) {
        console.error('載入迴圈列表失敗：', err);
        this.error = err.response?.data?.detail || err.message || '載入失敗';
      } finally {
        this.loading = false;
      }
    },
    async refreshLoops() {
      await this.loadLoops();
      await this.loadCoverageStats();
    },
    async loadCoverageStats() {
      try {
        const response = await axios.get('/rag-api/v1/loops/coverage-stats');
        this.coverageStats = response.data;
      } catch (err) {
        console.error('載入覆蓋率統計失敗：', err);
      }
    },
    getCoverageClass(rate) {
      if (rate >= 80) return 'coverage-high';
      if (rate >= 50) return 'coverage-medium';
      return 'coverage-low';
    },
    isRunningStatus(status) {
      const runningStatuses = ['running', 'backtesting', 'analyzing', 'generating', 'validating', 'syncing'];
      return runningStatuses.includes(status.toLowerCase());
    },
    getStatusLabel(status) {
      const labels = {
        pending: '待啟動',
        running: '執行中',
        backtesting: '回測中',
        analyzing: '分析中',
        generating: '生成中',
        reviewing: '審核中',
        validating: '驗證中',
        syncing: '同步中',
        paused: '已暫停',
        completed: '已完成',
        failed: '失敗',
        cancelled: '已取消',
        terminated: '已終止'
      };
      return labels[status.toLowerCase()] || status;
    },
    getVendorName(vendorId) {
      const vendors = {
        1: '心巢房屋',
        2: '富喬物業',
        3: '愛租屋'
      };
      return vendors[vendorId] || `業者 ${vendorId}`;
    },
    formatPassRate(rate) {
      if (rate === null || rate === undefined) return '-';
      return `${(rate * 100).toFixed(1)}%`;
    },
    getPassRateClass(rate) {
      if (rate === null || rate === undefined) return '';
      if (rate >= 0.85) return 'excellent';
      if (rate >= 0.70) return 'good';
      if (rate >= 0.50) return 'moderate';
      return 'poor';
    },
    formatDateTime(dateStr) {
      if (!dateStr) return '-';
      const date = new Date(dateStr);
      return date.toLocaleString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    },
    formatImprovement(currentRate, previousRate) {
      if (currentRate === null || currentRate === undefined || previousRate === null || previousRate === undefined) {
        return '-';
      }
      const diff = (currentRate - previousRate) * 100;
      const sign = diff > 0 ? '↑' : diff < 0 ? '↓' : '';
      return `${sign} ${Math.abs(diff).toFixed(1)}%`;
    },
    getImprovementClass(currentRate, previousRate) {
      if (currentRate === null || currentRate === undefined || previousRate === null || previousRate === undefined) {
        return 'neutral';
      }
      const diff = currentRate - previousRate;
      if (diff > 0.05) return 'great';  // 改善超過 5%
      if (diff > 0) return 'good';      // 有改善
      if (diff < 0) return 'negative';  // 退步
      return 'neutral';                  // 持平
    },
    async viewDetails(loop) {
      this.showDetailsModal = true;
      this.loadingDetails = true;
      this.selectedLoop = null;
      this.iterationHistory = [];

      try {
        // 1. 載入迴圈詳情
        const loopResponse = await axios.get(`/rag-api/v1/loops/${loop.loop_id}`);
        this.selectedLoop = loopResponse.data;

        // 2. 載入迭代歷史（從 loop_execution_logs 表）
        const historyResponse = await axios.get(`/rag-api/v1/loops/${loop.loop_id}/iterations`);
        this.iterationHistory = historyResponse.data;

        // 3. 繪製通過率趨勢圖
        this.$nextTick(() => {
          this.drawTrendChart();
        });
      } catch (err) {
        console.error('載入迴圈詳情失敗：', err);
        alert(`❌ 載入迴圈詳情失敗：\n\n${err.response?.data?.detail || err.message || '未知錯誤'}`);
        this.closeDetailsModal();
      } finally {
        this.loadingDetails = false;
      }
    },
    closeDetailsModal() {
      this.showDetailsModal = false;
      this.selectedLoop = null;
      this.iterationHistory = [];
      if (this.trendChartInstance) {
        this.trendChartInstance.destroy();
        this.trendChartInstance = null;
      }
    },
    formatScenarioIds(scenarioIds) {
      if (!scenarioIds || scenarioIds.length === 0) return '無';
      if (scenarioIds.length <= 10) {
        return scenarioIds.join(', ');
      }
      return `${scenarioIds.slice(0, 10).join(', ')} ... (共 ${scenarioIds.length} 個)`;
    },
    drawTrendChart() {
      if (!this.$refs.trendChart || this.iterationHistory.length === 0) return;

      const ctx = this.$refs.trendChart.getContext('2d');

      // 銷毀舊的圖表實例
      if (this.trendChartInstance) {
        this.trendChartInstance.destroy();
      }

      // 準備數據
      const labels = this.iterationHistory.map(iter => `迭代 ${iter.iteration}`);
      const passRates = this.iterationHistory.map(iter => (iter.pass_rate * 100).toFixed(1));
      const targetRate = this.selectedLoop.target_pass_rate * 100;

      // 創建簡易折線圖（不使用 Chart.js，手動繪製）
      this.drawSimpleLineChart(ctx, labels, passRates, targetRate);
    },
    drawSimpleLineChart(ctx, labels, data, targetLine) {
      const canvas = ctx.canvas;
      const width = canvas.width;
      const height = canvas.height;
      const padding = 40;

      // 清空畫布
      ctx.clearRect(0, 0, width, height);

      // 設定樣式
      ctx.font = '12px Arial';
      ctx.strokeStyle = '#333';
      ctx.fillStyle = '#333';

      // 繪製座標軸
      ctx.beginPath();
      ctx.moveTo(padding, padding);
      ctx.lineTo(padding, height - padding);
      ctx.lineTo(width - padding, height - padding);
      ctx.stroke();

      // 繪製 Y 軸標籤
      for (let i = 0; i <= 10; i++) {
        const y = height - padding - (i * (height - 2 * padding) / 10);
        const value = i * 10;
        ctx.fillText(`${value}%`, 5, y + 4);

        // 繪製網格線
        ctx.strokeStyle = '#e0e0e0';
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
        ctx.strokeStyle = '#333';
      }

      // 繪製目標線
      if (targetLine) {
        const targetY = height - padding - (targetLine / 100) * (height - 2 * padding);
        ctx.strokeStyle = '#ff9800';
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(padding, targetY);
        ctx.lineTo(width - padding, targetY);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = '#ff9800';
        ctx.fillText(`目標: ${targetLine}%`, width - padding + 5, targetY + 4);
        ctx.fillStyle = '#333';
      }

      // 計算點的位置
      const pointSpacing = (width - 2 * padding) / Math.max(1, data.length - 1);
      const points = data.map((value, index) => ({
        x: padding + (index * pointSpacing),
        y: height - padding - (value / 100) * (height - 2 * padding)
      }));

      // 繪製折線
      ctx.strokeStyle = '#4CAF50';
      ctx.lineWidth = 2;
      ctx.beginPath();
      points.forEach((point, index) => {
        if (index === 0) {
          ctx.moveTo(point.x, point.y);
        } else {
          ctx.lineTo(point.x, point.y);
        }
      });
      ctx.stroke();
      ctx.lineWidth = 1;

      // 繪製數據點
      ctx.fillStyle = '#4CAF50';
      points.forEach((point, index) => {
        ctx.beginPath();
        ctx.arc(point.x, point.y, 4, 0, Math.PI * 2);
        ctx.fill();

        // 繪製數值標籤
        ctx.fillStyle = '#333';
        ctx.fillText(`${data[index]}%`, point.x - 15, point.y - 10);
        ctx.fillStyle = '#4CAF50';
      });

      // 繪製 X 軸標籤
      ctx.fillStyle = '#666';
      points.forEach((point, index) => {
        if (labels[index]) {
          ctx.fillText(labels[index], point.x - 20, height - padding + 20);
        }
      });
    }
  }
};
</script>

<style scoped>
.loop-management-tab {
  padding: 20px;
}

/* 覆蓋率統計卡片 */
.coverage-stats-card {
  background: #f8f9fa;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 16px;
}

.coverage-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.coverage-title {
  font-weight: 600;
  font-size: 14px;
  color: #4a5568;
}

.coverage-percentage {
  font-weight: 700;
  font-size: 20px;
}

.coverage-percentage.coverage-high { color: #38a169; }
.coverage-percentage.coverage-medium { color: #d69e2e; }
.coverage-percentage.coverage-low { color: #e53e3e; }

.coverage-progress-bar {
  width: 100%;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.coverage-progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.coverage-progress-fill.coverage-high { background: #38a169; }
.coverage-progress-fill.coverage-medium { background: #d69e2e; }
.coverage-progress-fill.coverage-low { background: #e53e3e; }

.coverage-details {
  font-size: 13px;
  color: #718096;
}

.uncovered-hint {
  color: #e53e3e;
}

.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s ease;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background-color: #4CAF50;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #45a049;
}

.btn-refresh {
  background-color: #2196F3;
  color: white;
}

.btn-refresh:hover:not(:disabled) {
  background-color: #0b7dda;
}

.btn-secondary {
  background-color: #757575;
  color: white;
}

.loading-state, .error-state, .empty-state {
  text-align: center;
  padding: 40px;
  color: #666;
}

.error-message {
  color: #f44336;
  margin-bottom: 10px;
}

.loops-table-container {
  overflow-x: auto;
}

.loops-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.loops-table thead {
  background-color: #f5f5f5;
}

.loops-table th, .loops-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

.loops-table th {
  font-weight: 600;
  color: #333;
}

.loops-table tbody tr:hover {
  background-color: #f9f9f9;
}

.loops-table tbody tr.row-running {
  background-color: #e3f2fd;
}

.loop-name {
  font-weight: 500;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.loop-name.clickable {
  cursor: pointer;
  color: #2b6cb0;
}

.loop-name.clickable:hover {
  text-decoration: underline;
}

.timestamp {
  font-size: 12px;
  color: #666;
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

/* 狀態顏色 */
.status-pending { background-color: #9e9e9e; color: white; }
.status-running { background-color: #2196F3; color: white; animation: pulse 2s infinite; }
.status-backtesting { background-color: #9C27B0; color: white; }
.status-analyzing { background-color: #673AB7; color: white; }
.status-generating { background-color: #3F51B5; color: white; }
.status-reviewing { background-color: #FF9800; color: white; }
.status-validating { background-color: #00BCD4; color: white; }
.status-syncing { background-color: #009688; color: white; }
.status-paused { background-color: #FFC107; color: #333; }
.status-completed { background-color: #4CAF50; color: white; }
.status-failed { background-color: #F44336; color: white; }
.status-cancelled { background-color: #757575; color: white; }
.status-terminated { background-color: #424242; color: white; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.pass-rate {
  font-weight: 600;
}

.pass-rate.excellent { color: #4CAF50; }
.pass-rate.good { color: #8BC34A; }
.pass-rate.moderate { color: #FF9800; }
.pass-rate.poor { color: #F44336; }

.actions {
  display: flex;
  gap: 4px;
}

.btn-action {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.btn-action:hover {
  background-color: #f0f0f0;
}

.btn-action:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* 查看詳情 Modal 樣式 */
.modal-large {
  max-width: 900px;
  max-height: 90vh;
  overflow-y: auto;
}

.loading-details {
  text-align: center;
  padding: 40px;
  color: #666;
}

.details-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.details-section {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  background-color: #fafafa;
}

.details-section h4 {
  margin: 0 0 16px 0;
  color: #333;
  font-size: 16px;
  font-weight: 600;
}

.details-section h5 {
  margin: 16px 0 8px 0;
  color: #555;
  font-size: 14px;
  font-weight: 600;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 12px;
}

.test-set-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-item {
  display: flex;
  gap: 8px;
  align-items: baseline;
}

.info-item label {
  font-weight: 600;
  color: #666;
  min-width: 100px;
}

.info-item span {
  color: #333;
}

.scenario-ids {
  font-family: monospace;
  font-size: 12px;
  color: #666;
  word-break: break-all;
}

.empty-history {
  text-align: center;
  padding: 20px;
  color: #999;
}

.iteration-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 12px;
}

.iteration-table thead {
  background-color: #f5f5f5;
}

.iteration-table th,
.iteration-table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

.iteration-table th {
  font-weight: 600;
  color: #555;
  font-size: 13px;
}

.iteration-table td {
  font-size: 14px;
}

.iteration-table tbody tr:hover {
  background-color: #f9f9f9;
}

.pass-count {
  color: #4CAF50;
  font-weight: 600;
}

.fail-count {
  color: #F44336;
  font-weight: 600;
}

.iteration-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
  background-color: #e0e0e0;
  color: #333;
}

.iteration-badge.is-current {
  background-color: #2196F3;
  color: white;
  animation: pulse 2s infinite;
}

.current-iteration {
  background-color: #e3f2fd;
}

.improvement-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
}

.improvement-badge.great {
  background-color: #4CAF50;
  color: white;
}

.improvement-badge.good {
  background-color: #8BC34A;
  color: white;
}

.improvement-badge.negative {
  background-color: #F44336;
  color: white;
}

.improvement-badge.neutral {
  background-color: #e0e0e0;
  color: #666;
}

.chart-container {
  margin-top: 24px;
  padding: 16px;
  background-color: white;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}

.chart-container canvas {
  display: block;
  max-width: 100%;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 16px;
  border-top: 1px solid #e0e0e0;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.close-btn:hover {
  background-color: #f5f5f5;
  color: #333;
}

.modal-body {
  padding: 20px;
}

/* 選中迴圈提示 */
.selected-loop-info {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 12px 20px;
  border-radius: 8px;
  margin-bottom: 15px;
  font-weight: 600;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.no-loop-selected {
  background: #fff3cd;
  color: #856404;
  padding: 12px 20px;
  border-radius: 8px;
  margin-bottom: 15px;
  font-weight: 500;
  font-size: 14px;
  border: 1px solid #ffc107;
}
</style>
