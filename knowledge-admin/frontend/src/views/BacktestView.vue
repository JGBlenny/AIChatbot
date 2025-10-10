<template>
  <div class="backtest-view">
    <h2>🧪 回測結果與優化</h2>

    <!-- 統計卡片 -->
    <div v-if="statistics" class="stats-cards">
      <div class="stat-card">
        <div class="stat-label">總測試數</div>
        <div class="stat-value">{{ statistics.total_tests }}</div>
      </div>
      <div class="stat-card success">
        <div class="stat-label">通過測試</div>
        <div class="stat-value">{{ statistics.passed_tests }}</div>
      </div>
      <div class="stat-card fail">
        <div class="stat-label">失敗測試</div>
        <div class="stat-value">{{ statistics.failed_tests }}</div>
      </div>
      <div class="stat-card rate">
        <div class="stat-label">通過率</div>
        <div class="stat-value">{{ statistics.pass_rate }}%</div>
      </div>
      <div class="stat-card score">
        <div class="stat-label">平均分數</div>
        <div class="stat-value">{{ statistics.avg_score }}</div>
      </div>
      <div class="stat-card confidence">
        <div class="stat-label">平均信心度</div>
        <div class="stat-value">{{ statistics.avg_confidence }}</div>
      </div>
    </div>

    <!-- 工具列 -->
    <div class="toolbar">
      <div class="filter-group">
        <label>狀態篩選：</label>
        <select v-model="statusFilter" @change="loadResults">
          <option value="all">全部</option>
          <option value="failed">僅失敗</option>
          <option value="passed">僅通過</option>
        </select>
      </div>

      <button @click="runBacktest" class="btn-run" :disabled="isRunning">
        <span v-if="isRunning">⏳ 執行中...</span>
        <span v-else>▶️ 執行回測</span>
      </button>

      <button @click="loadResults" class="btn-refresh" :disabled="isRunning">
        🔄 重新載入
      </button>

      <button @click="showSummary" class="btn-summary">
        📊 查看摘要
      </button>

      <span v-if="lastRunTime" class="last-run-time">
        最後執行: {{ formatRunTime(lastRunTime) }}
      </span>
    </div>

    <!-- 執行狀態提示 -->
    <div v-if="isRunning" class="running-status">
      <div class="loading-bar"></div>
      <p>⏳ 回測執行中，預計需要 3-5 分鐘...</p>
      <p class="hint">系統會自動刷新結果，請稍候</p>
    </div>

    <!-- 載入中 -->
    <div v-if="loading" class="loading">
      <p>載入中...</p>
    </div>

    <!-- 錯誤訊息 -->
    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button @click="loadResults" class="btn-primary">重試</button>
    </div>

    <!-- 回測結果表格 -->
    <div v-else-if="results.length > 0" class="results-container">
      <div class="results-info">
        顯示 {{ results.length }} 筆結果（共 {{ total }} 筆）
      </div>

      <table class="results-table">
        <thead>
          <tr>
            <th width="60">ID</th>
            <th width="80">狀態</th>
            <th>測試問題</th>
            <th width="120">預期分類</th>
            <th width="120">實際意圖</th>
            <th width="100">分數</th>
            <th width="100">信心度</th>
            <th width="150">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="result in results" :key="result.test_id" :class="{ 'failed-row': !result.passed }">
            <td>{{ result.test_id }}</td>
            <td>
              <span v-if="result.passed" class="badge badge-success">✅ 通過</span>
              <span v-else class="badge badge-fail">❌ 失敗</span>
            </td>
            <td class="question-cell">
              <div class="question-text">{{ result.test_question }}</div>
              <div v-if="result.system_answer" class="answer-preview">
                {{ result.system_answer.substring(0, 100) }}...
              </div>
            </td>
            <td>
              <span class="badge">{{ result.expected_category || 'N/A' }}</span>
            </td>
            <td>
              <span class="badge" :class="{ 'badge-unclear': result.actual_intent === 'unclear' }">
                {{ result.actual_intent || 'N/A' }}
              </span>
            </td>
            <td>
              <span class="score-badge" :class="getScoreClass(result.score)">
                {{ result.score.toFixed(2) }}
              </span>
            </td>
            <td>
              <span class="confidence-badge" :class="getConfidenceClass(result.confidence)">
                {{ result.confidence.toFixed(2) }}
              </span>
            </td>
            <td>
              <button @click="showDetail(result)" class="btn-detail">
                👁️ 詳情
              </button>
              <button v-if="!result.passed" @click="optimizeKnowledge(result)" class="btn-optimize">
                ⚡ 優化
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 分頁控制 -->
      <div class="pagination-controls">
        <button
          @click="previousPage"
          :disabled="pagination.offset === 0"
          class="btn-pagination"
        >
          ← 上一頁
        </button>
        <span class="page-info">
          第 {{ currentPage }} 頁
        </span>
        <button
          @click="nextPage"
          :disabled="pagination.offset + pagination.limit >= total"
          class="btn-pagination"
        >
          下一頁 →
        </button>
        <select v-model.number="pagination.limit" @change="changePageSize" class="page-size-select">
          <option :value="20">每頁 20 筆</option>
          <option :value="50">每頁 50 筆</option>
          <option :value="100">每頁 100 筆</option>
        </select>
      </div>
    </div>

    <!-- 空狀態 -->
    <div v-else class="empty-state">
      <p>📭 尚無回測結果</p>
      <p>請先執行回測：</p>
      <pre>cd /Users/lenny/jgb/AIChatbot
python3 scripts/knowledge_extraction/backtest_framework.py</pre>
    </div>

    <!-- 詳情 Modal -->
    <div v-if="showDetailModal" class="modal-overlay" @click="closeDetailModal">
      <div class="modal-content large" @click.stop>
        <h2>測試詳情</h2>

        <div v-if="selectedResult" class="detail-content">
          <div class="detail-section">
            <h3>測試資訊</h3>
            <table class="detail-table">
              <tr>
                <td><strong>測試 ID:</strong></td>
                <td>{{ selectedResult.test_id }}</td>
              </tr>
              <tr>
                <td><strong>狀態:</strong></td>
                <td>
                  <span v-if="selectedResult.passed" class="badge badge-success">✅ 通過</span>
                  <span v-else class="badge badge-fail">❌ 失敗</span>
                </td>
              </tr>
              <tr>
                <td><strong>分數:</strong></td>
                <td>{{ selectedResult.score.toFixed(2) }} / 1.0</td>
              </tr>
              <tr>
                <td><strong>信心度:</strong></td>
                <td>{{ selectedResult.confidence.toFixed(2) }}</td>
              </tr>
              <tr>
                <td><strong>難度:</strong></td>
                <td>{{ selectedResult.difficulty }}</td>
              </tr>
            </table>
          </div>

          <div class="detail-section">
            <h3>問題與答案</h3>
            <div class="question-box">
              <strong>測試問題:</strong>
              <p>{{ selectedResult.test_question }}</p>
            </div>
            <div class="answer-box">
              <strong>系統回答:</strong>
              <p>{{ selectedResult.system_answer }}</p>
            </div>
          </div>

          <div class="detail-section">
            <h3>分類比對</h3>
            <table class="detail-table">
              <tr>
                <td><strong>預期分類:</strong></td>
                <td>{{ selectedResult.expected_category }}</td>
              </tr>
              <tr>
                <td><strong>實際意圖:</strong></td>
                <td>{{ selectedResult.actual_intent }}</td>
              </tr>
              <tr>
                <td><strong>是否匹配:</strong></td>
                <td>
                  <span v-if="selectedResult.expected_category === selectedResult.actual_intent"
                        class="badge badge-success">✅ 匹配</span>
                  <span v-else class="badge badge-fail">❌ 不匹配</span>
                </td>
              </tr>
            </table>
          </div>

          <div v-if="selectedResult.optimization_tips" class="detail-section optimization-hints">
            <h3>💡 優化建議</h3>
            <div class="optimization-tips-content">
              <pre>{{ selectedResult.optimization_tips }}</pre>
            </div>
          </div>
        </div>

        <div class="modal-actions">
          <button @click="optimizeKnowledge(selectedResult)" class="btn-primary" v-if="!selectedResult.passed">
            ⚡ 前往優化
          </button>
          <button @click="closeDetailModal" class="btn-secondary">
            關閉
          </button>
        </div>
      </div>
    </div>

    <!-- 摘要 Modal -->
    <div v-if="showSummaryModal" class="modal-overlay" @click="closeSummaryModal">
      <div class="modal-content large" @click.stop>
        <h2>📊 回測摘要報告</h2>
        <pre class="summary-text">{{ summaryText }}</pre>
        <div class="modal-actions">
          <button @click="closeSummaryModal" class="btn-secondary">
            關閉
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

const API_BASE = '/api';

export default {
  name: 'BacktestView',
  data() {
    return {
      results: [],
      statistics: null,
      total: 0,
      loading: false,
      error: null,
      statusFilter: 'all',
      pagination: {
        limit: 50,
        offset: 0
      },
      showDetailModal: false,
      selectedResult: null,
      showSummaryModal: false,
      summaryText: '',
      isRunning: false,
      lastRunTime: null,
      statusCheckInterval: null
    };
  },
  computed: {
    currentPage() {
      return Math.floor(this.pagination.offset / this.pagination.limit) + 1;
    }
  },
  mounted() {
    this.checkBacktestStatus();
    this.loadResults();
  },
  beforeUnmount() {
    if (this.statusCheckInterval) {
      clearInterval(this.statusCheckInterval);
    }
  },
  methods: {
    async loadResults() {
      this.loading = true;
      this.error = null;

      try {
        const params = {
          status_filter: this.statusFilter,
          limit: this.pagination.limit,
          offset: this.pagination.offset
        };

        const response = await axios.get(`${API_BASE}/backtest/results`, { params });

        this.results = response.data.results;
        this.total = response.data.total;
        this.statistics = response.data.statistics;

      } catch (error) {
        console.error('載入回測結果失敗', error);
        if (error.response?.status === 404) {
          this.error = '回測結果文件不存在。請先執行回測：\npython3 scripts/knowledge_extraction/backtest_framework.py';
        } else {
          this.error = '載入失敗：' + (error.response?.data?.detail || error.message);
        }
      } finally {
        this.loading = false;
      }
    },

    async showSummary() {
      try {
        const response = await axios.get(`${API_BASE}/backtest/summary`);
        this.summaryText = response.data.summary;
        this.showSummaryModal = true;
      } catch (error) {
        alert('無法載入摘要：' + (error.response?.data?.detail || error.message));
      }
    },

    previousPage() {
      if (this.pagination.offset >= this.pagination.limit) {
        this.pagination.offset -= this.pagination.limit;
        this.loadResults();
      }
    },

    nextPage() {
      if (this.pagination.offset + this.pagination.limit < this.total) {
        this.pagination.offset += this.pagination.limit;
        this.loadResults();
      }
    },

    changePageSize() {
      this.pagination.offset = 0;
      this.loadResults();
    },

    showDetail(result) {
      this.selectedResult = result;
      this.showDetailModal = true;
    },

    closeDetailModal() {
      this.showDetailModal = false;
      this.selectedResult = null;
    },

    closeSummaryModal() {
      this.showSummaryModal = false;
    },

    optimizeKnowledge(result) {
      // 關閉 modal
      this.showDetailModal = false;

      // 跳轉到知識庫頁面並搜尋相關問題
      this.$router.push({
        path: '/',
        query: { search: result.test_question.substring(0, 50) }
      });

      alert(`💡 提示：請在知識庫中搜尋「${result.test_question.substring(0, 30)}...」相關的知識進行優化`);
    },

    getScoreClass(score) {
      if (score >= 0.8) return 'score-high';
      if (score >= 0.6) return 'score-medium';
      return 'score-low';
    },

    getConfidenceClass(confidence) {
      if (confidence >= 0.7) return 'confidence-high';
      if (confidence >= 0.5) return 'confidence-medium';
      return 'confidence-low';
    },

    async runBacktest() {
      if (!confirm('確定要執行回測嗎？這將需要 3-5 分鐘時間。')) {
        return;
      }

      try {
        const response = await axios.post(`${API_BASE}/backtest/run`);
        alert(`✅ ${response.data.message}\n預計時間：${response.data.estimated_time}`);

        // 開始監控狀態
        this.isRunning = true;
        this.startStatusMonitoring();
      } catch (error) {
        console.error('執行回測失敗', error);
        if (error.response?.status === 409) {
          alert('⚠️ 回測已在執行中，請等待完成後再試');
        } else if (error.response?.status === 404) {
          alert('❌ ' + (error.response?.data?.detail || '測試場景文件不存在'));
        } else {
          alert('執行失敗：' + (error.response?.data?.detail || error.message));
        }
      }
    },

    async checkBacktestStatus() {
      try {
        const response = await axios.get(`${API_BASE}/backtest/status`);
        this.isRunning = response.data.is_running;
        this.lastRunTime = response.data.last_run_time;

        if (this.isRunning && !this.statusCheckInterval) {
          this.startStatusMonitoring();
        }
      } catch (error) {
        console.error('檢查狀態失敗', error);
      }
    },

    startStatusMonitoring() {
      // 每 5 秒檢查一次狀態
      if (this.statusCheckInterval) {
        clearInterval(this.statusCheckInterval);
      }

      this.statusCheckInterval = setInterval(async () => {
        try {
          const response = await axios.get(`${API_BASE}/backtest/status`);

          if (!response.data.is_running && this.isRunning) {
            // 回測完成
            this.isRunning = false;
            this.lastRunTime = response.data.last_run_time;
            clearInterval(this.statusCheckInterval);
            this.statusCheckInterval = null;

            // 自動重新載入結果
            await this.loadResults();
            alert('✅ 回測執行完成！結果已自動刷新。');
          }
        } catch (error) {
          console.error('監控狀態失敗', error);
        }
      }, 5000);
    },

    formatRunTime(isoString) {
      if (!isoString) return '-';
      const date = new Date(isoString);
      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / 60000);

      if (diffMins < 1) return '剛剛';
      if (diffMins < 60) return `${diffMins} 分鐘前`;
      if (diffMins < 1440) return `${Math.floor(diffMins / 60)} 小時前`;
      return date.toLocaleString('zh-TW', {
        year: 'numeric',
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
.backtest-view {
  max-width: 1400px;
  margin: 0 auto;
}

/* 統計卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 12px;
  text-align: center;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.stat-card.success {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
}

.stat-card.fail {
  background: linear-gradient(135deg, #ee0979 0%, #ff6a00 100%);
}

.stat-card.rate {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.stat-card.score {
  background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
}

.stat-card.confidence {
  background: linear-gradient(135deg, #30cfd0 0%, #330867 100%);
}

.stat-label {
  font-size: 14px;
  opacity: 0.9;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
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

.btn-run {
  padding: 8px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s;
}

.btn-run:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-run:disabled {
  background: linear-gradient(135deg, #c0c4cc 0%, #909399 100%);
  cursor: not-allowed;
  opacity: 0.6;
}

.btn-refresh, .btn-summary {
  padding: 8px 16px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-refresh:hover:not(:disabled), .btn-summary:hover {
  background: #5568d3;
  transform: translateY(-1px);
}

.btn-refresh:disabled {
  background: #c0c4cc;
  cursor: not-allowed;
  opacity: 0.6;
}

.last-run-time {
  margin-left: auto;
  color: #909399;
  font-size: 13px;
}

/* 執行狀態 */
.running-status {
  background: linear-gradient(135deg, #fff5e6 0%, #ffe8cc 100%);
  border: 1px solid #ffd591;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  text-align: center;
}

.running-status p {
  margin: 5px 0;
  color: #d46b08;
  font-size: 16px;
  font-weight: 500;
}

.running-status .hint {
  font-size: 14px;
  color: #8c8c8c;
  font-weight: normal;
}

.loading-bar {
  width: 100%;
  height: 4px;
  background: #f0f0f0;
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 15px;
}

.loading-bar::after {
  content: '';
  display: block;
  width: 30%;
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  animation: loading 2s ease-in-out infinite;
}

@keyframes loading {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(400%);
  }
}

/* 結果表格 */
.results-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  overflow: hidden;
}

.results-info {
  padding: 15px 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
  font-size: 14px;
  color: #606266;
}

.results-table {
  width: 100%;
  border-collapse: collapse;
}

.results-table thead {
  background: #f5f7fa;
}

.results-table th {
  padding: 12px;
  text-align: left;
  font-weight: 600;
  color: #303133;
  border-bottom: 2px solid #dee2e6;
}

.results-table tbody tr {
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.2s;
}

.results-table tbody tr:hover {
  background: #f8f9fa;
}

.results-table tbody tr.failed-row {
  background: #fff5f5;
}

.results-table tbody tr.failed-row:hover {
  background: #ffe8e8;
}

.results-table td {
  padding: 12px;
  vertical-align: top;
}

.question-cell {
  max-width: 400px;
}

.question-text {
  font-weight: 500;
  color: #303133;
  margin-bottom: 5px;
}

.answer-preview {
  font-size: 13px;
  color: #909399;
  line-height: 1.4;
}

/* Badge 樣式 */
.badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  background: #e4e7ed;
  color: #606266;
}

.badge-success {
  background: #67c23a;
  color: white;
}

.badge-fail {
  background: #f56c6c;
  color: white;
}

.badge-unclear {
  background: #e6a23c;
  color: white;
}

.score-badge, .confidence-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 14px;
}

.score-high, .confidence-high {
  background: #67c23a;
  color: white;
}

.score-medium, .confidence-medium {
  background: #e6a23c;
  color: white;
}

.score-low, .confidence-low {
  background: #f56c6c;
  color: white;
}

/* 按鈕 */
.btn-detail, .btn-optimize {
  padding: 6px 12px;
  margin: 2px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.btn-detail {
  background: #409eff;
  color: white;
}

.btn-detail:hover {
  background: #66b1ff;
}

.btn-optimize {
  background: #e6a23c;
  color: white;
}

.btn-optimize:hover {
  background: #ebb563;
}

/* 分頁控制 */
.pagination-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  padding: 20px;
  border-top: 1px solid #f0f0f0;
}

.btn-pagination {
  padding: 8px 16px;
  background: #409eff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-pagination:hover:not(:disabled) {
  background: #66b1ff;
  transform: translateY(-1px);
}

.btn-pagination:disabled {
  background: #c0c4cc;
  cursor: not-allowed;
  opacity: 0.6;
}

.page-info {
  font-size: 14px;
  color: #606266;
}

.page-size-select {
  padding: 6px 10px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
}

/* 狀態樣式 */
.loading, .empty-state, .error-state {
  text-align: center;
  padding: 60px 20px;
  color: #909399;
}

.empty-state pre {
  background: #f4f4f5;
  padding: 15px;
  border-radius: 4px;
  text-align: left;
  display: inline-block;
  margin-top: 15px;
  font-size: 13px;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  padding: 30px;
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 10px 40px rgba(0,0,0,0.3);
}

.modal-content.large {
  max-width: 900px;
}

.modal-content h2 {
  margin-top: 0;
  color: #303133;
}

.detail-content {
  margin: 20px 0;
}

.detail-section {
  margin-bottom: 25px;
  padding-bottom: 20px;
  border-bottom: 1px solid #f0f0f0;
}

.detail-section:last-child {
  border-bottom: none;
}

.detail-section h3 {
  color: #606266;
  font-size: 16px;
  margin-bottom: 15px;
}

.detail-table {
  width: 100%;
  border-collapse: collapse;
}

.detail-table td {
  padding: 10px;
  border-bottom: 1px solid #f0f0f0;
}

.detail-table td:first-child {
  width: 150px;
}

.question-box, .answer-box {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  margin-bottom: 15px;
}

.question-box strong, .answer-box strong {
  display: block;
  margin-bottom: 8px;
  color: #606266;
}

.question-box p, .answer-box p {
  margin: 0;
  line-height: 1.6;
  color: #303133;
}

.optimization-hints {
  background: #fffbe6;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #ffe58f;
}

.optimization-hints h3 {
  color: #d46b08;
  margin-top: 0;
}

.optimization-hints ul {
  margin: 0;
  padding-left: 20px;
}

.optimization-hints li {
  margin-bottom: 15px;
  line-height: 1.6;
}

.optimization-hints strong {
  color: #d46b08;
  display: block;
  margin-bottom: 5px;
}

.optimization-hints p {
  margin: 5px 0 0 0;
  color: #606266;
  font-size: 14px;
}

.optimization-tips-content {
  background: white;
  padding: 15px;
  border-radius: 6px;
}

.optimization-tips-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  font-size: 14px;
  line-height: 1.8;
  color: #303133;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
}

.btn-primary, .btn-secondary {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-primary {
  background: #409eff;
  color: white;
}

.btn-primary:hover {
  background: #66b1ff;
}

.btn-secondary {
  background: #dcdfe6;
  color: #606266;
}

.btn-secondary:hover {
  background: #c8cdd3;
}

.summary-text {
  background: #f4f4f5;
  padding: 20px;
  border-radius: 6px;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.6;
  max-height: 60vh;
  overflow-y: auto;
}
</style>
