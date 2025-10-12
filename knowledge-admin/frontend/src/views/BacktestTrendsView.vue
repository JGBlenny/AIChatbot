<template>
  <div class="trends-view">
    <h2>📈 回測趨勢分析</h2>

    <!-- 警報區塊 -->
    <div v-if="alerts && alerts.length > 0" class="alerts-section">
      <h3 class="section-title">
        🚨 品質警報
        <span class="alert-badge critical" v-if="alertSummary.critical_count > 0">
          {{ alertSummary.critical_count }} Critical
        </span>
        <span class="alert-badge warning" v-if="alertSummary.warning_count > 0">
          {{ alertSummary.warning_count }} Warning
        </span>
      </h3>
      <div class="alerts-grid">
        <div v-for="(alert, index) in alerts" :key="index"
             class="alert-card"
             :class="'alert-' + alert.level">
          <div class="alert-header">
            <span class="alert-icon">
              {{ alert.level === 'critical' ? '🔴' : alert.level === 'warning' ? '⚠️' : 'ℹ️' }}
            </span>
            <span class="alert-metric">{{ alert.metric }}</span>
            <span class="alert-level">{{ alert.level.toUpperCase() }}</span>
          </div>
          <div class="alert-message">{{ alert.message }}</div>
          <div class="alert-recommendation">💡 {{ alert.recommendation }}</div>
          <div class="alert-timestamp">{{ formatDate(alert.timestamp) }}</div>
        </div>
      </div>
    </div>

    <!-- 時間範圍選擇 -->
    <div class="toolbar">
      <div class="filter-group">
        <label>時間範圍：</label>
        <select v-model="timeRange" @change="loadTrends">
          <option value="7d">最近 7 天</option>
          <option value="30d">最近 30 天</option>
          <option value="90d">最近 90 天</option>
          <option value="all">全部</option>
        </select>
      </div>

      <button @click="loadAllData" class="btn-refresh">
        🔄 重新載入
      </button>
    </div>

    <!-- 載入中 -->
    <div v-if="loading" class="loading">
      <p>載入中...</p>
    </div>

    <!-- 錯誤訊息 -->
    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button @click="loadAllData" class="btn-primary">重試</button>
    </div>

    <!-- 趨勢圖表 -->
    <div v-else-if="trendsData" class="trends-container">
      <!-- 摘要統計卡片 -->
      <div v-if="trendsData.summary" class="summary-section">
        <h3 class="section-title">📊 趨勢摘要 ({{ trendsData.summary.total_runs }} 次回測)</h3>
        <div class="summary-cards">
          <div class="summary-card">
            <div class="card-label">通過率</div>
            <div class="card-value" :class="getTrendClass(trendsData.summary.pass_rate.trend)">
              {{ trendsData.summary.pass_rate.latest }}%
            </div>
            <div class="card-range">
              範圍: {{ trendsData.summary.pass_rate.min }}% - {{ trendsData.summary.pass_rate.max }}%
            </div>
            <div class="card-trend" :class="getTrendClass(trendsData.summary.pass_rate.trend)">
              {{ getTrendIcon(trendsData.summary.pass_rate.trend) }} {{ trendsData.summary.pass_rate.trend }}
            </div>
          </div>

          <div class="summary-card">
            <div class="card-label">平均分數</div>
            <div class="card-value" :class="getTrendClass(trendsData.summary.avg_score.trend)">
              {{ trendsData.summary.avg_score.latest }}
            </div>
            <div class="card-range">
              範圍: {{ trendsData.summary.avg_score.min }} - {{ trendsData.summary.avg_score.max }}
            </div>
            <div class="card-trend" :class="getTrendClass(trendsData.summary.avg_score.trend)">
              {{ getTrendIcon(trendsData.summary.avg_score.trend) }} {{ trendsData.summary.avg_score.trend }}
            </div>
          </div>

          <div class="summary-card">
            <div class="card-label">平均信心度</div>
            <div class="card-value" :class="getTrendClass(trendsData.summary.avg_confidence.trend)">
              {{ trendsData.summary.avg_confidence.latest }}
            </div>
            <div class="card-range">
              範圍: {{ trendsData.summary.avg_confidence.min }} - {{ trendsData.summary.avg_confidence.max }}
            </div>
            <div class="card-trend" :class="getTrendClass(trendsData.summary.avg_confidence.trend)">
              {{ getTrendIcon(trendsData.summary.avg_confidence.trend) }} {{ trendsData.summary.avg_confidence.trend }}
            </div>
          </div>
        </div>
      </div>

      <!-- 圖表區域 -->
      <div class="charts-section">
        <div class="chart-container">
          <h3 class="section-title">通過率趨勢</h3>
          <canvas ref="passRateChart"></canvas>
        </div>

        <div class="chart-container">
          <h3 class="section-title">分數與信心度趨勢</h3>
          <canvas ref="scoreChart"></canvas>
        </div>
      </div>

      <!-- 對比分析 -->
      <div v-if="comparison" class="comparison-section">
        <h3 class="section-title">📊 期間對比 (最近 7 天 vs 前 7 天)</h3>
        <div class="comparison-grid">
          <div class="comparison-card">
            <div class="period-label">當前期間</div>
            <div class="period-stats">
              <div class="stat-item">
                <span class="stat-name">回測次數:</span>
                <span class="stat-value">{{ comparison.current_period.statistics.total_runs }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-name">平均通過率:</span>
                <span class="stat-value">{{ comparison.current_period.statistics.avg_pass_rate.toFixed(1) }}%</span>
              </div>
              <div class="stat-item">
                <span class="stat-name">平均分數:</span>
                <span class="stat-value">{{ comparison.current_period.statistics.avg_score.toFixed(3) }}</span>
              </div>
            </div>
          </div>

          <div class="comparison-card">
            <div class="period-label">前一期間</div>
            <div class="period-stats">
              <div class="stat-item">
                <span class="stat-name">回測次數:</span>
                <span class="stat-value">{{ comparison.previous_period.statistics.total_runs }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-name">平均通過率:</span>
                <span class="stat-value">
                  {{ comparison.previous_period.statistics.avg_pass_rate > 0 ?
                     comparison.previous_period.statistics.avg_pass_rate.toFixed(1) + '%' : 'N/A' }}
                </span>
              </div>
              <div class="stat-item">
                <span class="stat-name">平均分數:</span>
                <span class="stat-value">
                  {{ comparison.previous_period.statistics.avg_score > 0 ?
                     comparison.previous_period.statistics.avg_score.toFixed(3) : 'N/A' }}
                </span>
              </div>
            </div>
          </div>

          <div class="comparison-card changes">
            <div class="period-label">變化</div>
            <div class="period-stats">
              <div class="stat-item" v-if="comparison.changes.avg_pass_rate">
                <span class="stat-name">通過率:</span>
                <span class="stat-value change" :class="getChangeClass(comparison.changes.avg_pass_rate.direction)">
                  {{ getChangeIcon(comparison.changes.avg_pass_rate.direction) }}
                  {{ comparison.changes.avg_pass_rate.percentage !== null ?
                     comparison.changes.avg_pass_rate.percentage + '%' : 'NEW' }}
                </span>
              </div>
              <div class="stat-item" v-if="comparison.changes.avg_score">
                <span class="stat-name">分數:</span>
                <span class="stat-value change" :class="getChangeClass(comparison.changes.avg_score.direction)">
                  {{ getChangeIcon(comparison.changes.avg_score.direction) }}
                  {{ comparison.changes.avg_score.percentage !== null ?
                     comparison.changes.avg_score.percentage + '%' : 'NEW' }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空狀態 -->
    <div v-else class="empty-state">
      <p>📭 無趨勢數據</p>
      <p>請先執行回測以產生趨勢數據</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { Chart, registerables } from 'chart.js';

Chart.register(...registerables);

const API_BASE = '/api';

export default {
  name: 'BacktestTrendsView',
  data() {
    return {
      timeRange: '30d',
      trendsData: null,
      comparison: null,
      alerts: [],
      alertSummary: null,
      loading: false,
      error: null,
      passRateChartInstance: null,
      scoreChartInstance: null
    };
  },
  mounted() {
    this.loadAllData();
  },
  beforeUnmount() {
    // 清理圖表實例
    if (this.passRateChartInstance) {
      this.passRateChartInstance.destroy();
    }
    if (this.scoreChartInstance) {
      this.scoreChartInstance.destroy();
    }
  },
  methods: {
    async loadAllData() {
      this.loading = true;
      this.error = null;

      try {
        await Promise.all([
          this.loadTrends(),
          this.loadComparison(),
          this.loadAlerts()
        ]);
      } catch (error) {
        console.error('載入數據失敗', error);
        this.error = '載入失敗：' + (error.response?.data?.detail || error.message);
      } finally {
        this.loading = false;
      }
    },

    async loadTrends() {
      try {
        const response = await axios.get(`${API_BASE}/backtest/trends/overview`, {
          params: { time_range: this.timeRange }
        });
        this.trendsData = response.data;

        // 等待 DOM 更新後繪製圖表
        this.$nextTick(() => {
          this.renderCharts();
        });
      } catch (error) {
        console.error('載入趨勢失敗', error);
        throw error;
      }
    },

    async loadComparison() {
      try {
        const response = await axios.get(`${API_BASE}/backtest/trends/comparison`, {
          params: { current_days: 7 }
        });
        this.comparison = response.data;
      } catch (error) {
        console.error('載入對比失敗', error);
        // 不拋出錯誤，允許繼續載入其他數據
      }
    },

    async loadAlerts() {
      try {
        const response = await axios.get(`${API_BASE}/backtest/trends/alerts`);
        this.alerts = response.data.alerts;
        this.alertSummary = response.data.summary;
      } catch (error) {
        console.error('載入警報失敗', error);
        // 不拋出錯誤，允許繼續載入其他數據
      }
    },

    renderCharts() {
      if (!this.trendsData || !this.trendsData.data_points || this.trendsData.data_points.length === 0) {
        return;
      }

      const dataPoints = this.trendsData.data_points;
      const labels = dataPoints.map(dp => new Date(dp.timestamp).toLocaleDateString('zh-TW', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      }));

      // 通過率圖表
      this.renderPassRateChart(labels, dataPoints);

      // 分數與信心度圖表
      this.renderScoreChart(labels, dataPoints);
    },

    renderPassRateChart(labels, dataPoints) {
      const ctx = this.$refs.passRateChart;
      if (!ctx) return;

      // 銷毀舊圖表
      if (this.passRateChartInstance) {
        this.passRateChartInstance.destroy();
      }

      this.passRateChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: '通過率 (%)',
            data: dataPoints.map(dp => dp.pass_rate),
            borderColor: '#67c23a',
            backgroundColor: 'rgba(103, 194, 58, 0.1)',
            tension: 0.4,
            fill: true
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: true,
              position: 'top'
            },
            tooltip: {
              callbacks: {
                label: function(context) {
                  return context.dataset.label + ': ' + context.parsed.y.toFixed(1) + '%';
                }
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              max: 100,
              ticks: {
                callback: function(value) {
                  return value + '%';
                }
              }
            }
          }
        }
      });
    },

    renderScoreChart(labels, dataPoints) {
      const ctx = this.$refs.scoreChart;
      if (!ctx) return;

      // 銷毀舊圖表
      if (this.scoreChartInstance) {
        this.scoreChartInstance.destroy();
      }

      this.scoreChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [
            {
              label: '平均分數',
              data: dataPoints.map(dp => dp.avg_score),
              borderColor: '#409eff',
              backgroundColor: 'rgba(64, 158, 255, 0.1)',
              tension: 0.4,
              yAxisID: 'y'
            },
            {
              label: '平均信心度',
              data: dataPoints.map(dp => dp.avg_confidence),
              borderColor: '#e6a23c',
              backgroundColor: 'rgba(230, 162, 60, 0.1)',
              tension: 0.4,
              yAxisID: 'y'
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: true,
              position: 'top'
            }
          },
          scales: {
            y: {
              type: 'linear',
              display: true,
              position: 'left',
              beginAtZero: true,
              max: 1,
              ticks: {
                callback: function(value) {
                  return value.toFixed(2);
                }
              }
            }
          }
        }
      });
    },

    getTrendClass(trend) {
      if (trend === 'improving') return 'trend-improving';
      if (trend === 'declining') return 'trend-declining';
      return 'trend-stable';
    },

    getTrendIcon(trend) {
      if (trend === 'improving') return '📈';
      if (trend === 'declining') return '📉';
      return '➡️';
    },

    getChangeClass(direction) {
      if (direction === 'up') return 'change-positive';
      if (direction === 'down') return 'change-negative';
      if (direction === 'new') return 'change-new';
      return 'change-stable';
    },

    getChangeIcon(direction) {
      if (direction === 'up') return '▲';
      if (direction === 'down') return '▼';
      if (direction === 'new') return '✨';
      return '▪';
    },

    formatDate(isoString) {
      if (!isoString) return '-';
      const date = new Date(isoString);
      return date.toLocaleString('zh-TW', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    }
  }
};
</script>

<style scoped>
.trends-view {
  width: 100%;
  padding: 20px;
}

/* 警報區塊 */
.alerts-section {
  margin-bottom: 30px;
}

.section-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 15px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.alert-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.alert-badge.critical {
  background: #f56c6c;
  color: white;
}

.alert-badge.warning {
  background: #e6a23c;
  color: white;
}

.alerts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 15px;
}

.alert-card {
  border-left: 4px solid;
  padding: 15px;
  border-radius: 8px;
  background: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.alert-card.alert-critical {
  border-color: #f56c6c;
  background: #fef0f0;
}

.alert-card.alert-warning {
  border-color: #e6a23c;
  background: #fdf6ec;
}

.alert-card.alert-info {
  border-color: #409eff;
  background: #ecf5ff;
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.alert-icon {
  font-size: 20px;
}

.alert-metric {
  flex: 1;
  font-weight: 600;
  color: #303133;
}

.alert-level {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(0,0,0,0.1);
}

.alert-message {
  font-size: 14px;
  color: #606266;
  margin-bottom: 8px;
}

.alert-recommendation {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
  line-height: 1.5;
}

.alert-timestamp {
  font-size: 12px;
  color: #c0c4cc;
  text-align: right;
}

/* 工具列 */
.toolbar {
  display: flex;
  gap: 15px;
  align-items: center;
  margin-bottom: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.filter-group label {
  font-weight: 500;
}

.filter-group select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.btn-refresh {
  padding: 8px 16px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-refresh:hover {
  background: #5568d3;
  transform: translateY(-1px);
}

/* 摘要卡片 */
.summary-section {
  margin-bottom: 30px;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.summary-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 25px;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.card-label {
  font-size: 14px;
  opacity: 0.9;
  margin-bottom: 10px;
}

.card-value {
  font-size: 36px;
  font-weight: bold;
  margin-bottom: 8px;
}

.card-range {
  font-size: 13px;
  opacity: 0.85;
  margin-bottom: 8px;
}

.card-trend {
  font-size: 14px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 12px;
  display: inline-block;
}

.trend-improving {
  background: rgba(103, 194, 58, 0.3);
}

.trend-declining {
  background: rgba(245, 108, 108, 0.3);
}

.trend-stable {
  background: rgba(144, 147, 153, 0.3);
}

/* 圖表區域 */
.charts-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
  gap: 30px;
  margin-bottom: 30px;
}

.chart-container {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.chart-container canvas {
  height: 300px !important;
}

/* 對比分析 */
.comparison-section {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-bottom: 30px;
}

.comparison-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.comparison-card {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
}

.comparison-card.changes {
  background: linear-gradient(135deg, #fef0f0 0%, #ecf5ff 100%);
}

.period-label {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 15px;
}

.period-stats {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0,0,0,0.05);
}

.stat-name {
  color: #606266;
  font-size: 14px;
}

.stat-value {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.stat-value.change {
  font-size: 16px;
}

.change-positive {
  color: #67c23a;
}

.change-negative {
  color: #f56c6c;
}

.change-new {
  color: #409eff;
}

.change-stable {
  color: #909399;
}

/* 狀態樣式 */
.loading, .empty-state, .error-state {
  text-align: center;
  padding: 60px 20px;
  color: #909399;
}

.btn-primary {
  padding: 10px 20px;
  background: #409eff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-primary:hover {
  background: #66b1ff;
}
</style>
