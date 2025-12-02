<template>
  <div class="backtest-view">
    <h2>🧪 回測結果與優化</h2>

    <!-- 說明區塊 -->
    <InfoPanel :config="helpTexts.backtest" />

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
    </div>

    <!-- 品質評估統計卡片 -->
    <div v-if="statistics && statistics.quality" class="quality-stats-section">
      <h3 class="section-title">🎯 LLM 品質評估統計 ({{ statistics.quality.count }} 個測試)</h3>
      <div class="stats-cards quality-cards">
        <div class="stat-card quality">
          <div class="stat-label">相關性</div>
          <div class="stat-value">{{ statistics.quality.avg_relevance.toFixed(2) }}</div>
          <div class="stat-rating">{{ getQualityRating(statistics.quality.avg_relevance) }}</div>
        </div>
        <div class="stat-card quality">
          <div class="stat-label">完整性</div>
          <div class="stat-value">{{ statistics.quality.avg_completeness.toFixed(2) }}</div>
          <div class="stat-rating">{{ getQualityRating(statistics.quality.avg_completeness) }}</div>
        </div>
        <div class="stat-card quality">
          <div class="stat-label">準確性</div>
          <div class="stat-value">{{ statistics.quality.avg_accuracy.toFixed(2) }}</div>
          <div class="stat-rating">{{ getQualityRating(statistics.quality.avg_accuracy) }}</div>
        </div>
        <div class="stat-card quality">
          <div class="stat-label">意圖匹配</div>
          <div class="stat-value">{{ statistics.quality.avg_intent_match.toFixed(2) }}</div>
          <div class="stat-rating">{{ getQualityRating(statistics.quality.avg_intent_match) }}</div>
        </div>
        <div class="stat-card quality">
          <div class="stat-label">綜合評分</div>
          <div class="stat-value">{{ statistics.quality.avg_quality_overall.toFixed(2) }}</div>
          <div class="stat-rating">{{ getQualityRating(statistics.quality.avg_quality_overall) }}</div>
        </div>
      </div>
    </div>

    <!-- 工具列 -->
    <div class="toolbar">
      <div class="filter-group">
        <label>📜 回測記錄：</label>
        <select v-model="selectedRunId" @change="onRunSelected" class="run-selector">
          <option v-for="run in backtestRuns" :key="run.id" :value="run.id">
            Run #{{ run.id }} - {{ formatRunDate(run.started_at) }}
            ({{ run.quality_mode }}, {{ run.executed_scenarios }} 個測試, 通過率 {{ run.pass_rate }}%)
          </option>
        </select>
      </div>

      <div class="filter-group">
        <label>狀態篩選：</label>
        <select v-model="statusFilter" @change="loadResults">
          <option value="all">全部</option>
          <option value="failed">僅失敗</option>
          <option value="passed">僅通過</option>
        </select>
      </div>

      <div class="filter-group">
        <label>品質模式：</label>
        <select v-model="backtestConfig.quality_mode">
          <option value="detailed">Detailed - LLM 深度評估 (推薦)</option>
          <option value="hybrid">Hybrid - 混合評估</option>
        </select>
      </div>

      <div class="filter-group">
        <label>測試策略：</label>
        <select v-model="backtestConfig.test_strategy">
          <option value="incremental">Incremental - 智能增量（新增+失敗+過時）</option>
          <option value="full">Full - 完整測試（所有已批准）</option>
          <option value="failed_only">Failed + Untested - 失敗 + 未測試</option>
        </select>
      </div>

      <button @click="runBacktest" class="btn-run" :disabled="isRunning">
        <span v-if="isRunning">⏳ 執行中...</span>
        <span v-else>▶️ 執行回測</span>
      </button>

      <button @click="loadResults" class="btn-refresh" :disabled="isRunning">
        🔄 重新載入
      </button>

      <button @click="cancelBacktest" class="btn-cancel" v-if="isRunning" style="background-color: #ff4d4f; color: white;">
        🛑 中斷回測
      </button>

      <button @click="forceStopMonitoring" class="btn-stop" v-if="isRunning" style="background-color: #fa8c16; color: white; margin-left: 10px;">
        ⏸️ 停止監控
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
      <p>⏳ 回測執行中...</p>
      <div v-if="runningProgress" class="progress-details">
        <p class="progress-text">
          進度: {{ runningProgress.executed_scenarios }}/{{ runningProgress.total_scenarios }}
          ({{ runningProgress.progress_pct }}%)
        </p>
        <div class="progress-bar-container">
          <div class="progress-bar-fill" :style="{ width: runningProgress.progress_pct + '%' }"></div>
        </div>
        <p class="progress-info">
          已運行: {{ runningProgress.elapsed }} |
          預估剩餘: {{ runningProgress.estimated_remaining }}
        </p>
      </div>
      <p class="hint" v-else>系統會自動刷新結果，請稍候</p>
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
            <th width="120">實際意圖</th>
            <th width="90">完整性</th>
            <th width="90">綜合評分</th>
            <th width="100">操作</th>
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
              <span class="badge" :class="{ 'badge-unclear': result.actual_intent === 'unclear' }">
                {{ result.actual_intent || 'N/A' }}
              </span>
            </td>
            <td>
              <span class="quality-badge" :class="getQualityClass(result.completeness)">
                {{ formatQualityScore(result.completeness) }}/5.0
              </span>
            </td>
            <td>
              <span class="quality-badge" :class="getQualityClass(result.quality_overall)">
                {{ formatQualityScore(result.quality_overall) }}/5.0
              </span>
            </td>
            <td>
              <button @click="showDetail(result)" class="btn-detail">
                詳情
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
      <p>點擊上方 <strong>🚀 開始回測</strong> 按鈕執行回測</p>
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
                <td><strong>完整性:</strong></td>
                <td>
                  <span class="quality-badge" :class="getQualityClass(selectedResult.completeness)">
                    {{ formatQualityScore(selectedResult.completeness) }}/5.0
                  </span>
                </td>
              </tr>
              <tr>
                <td><strong>綜合評分:</strong></td>
                <td>
                  <span class="quality-badge" :class="getQualityClass(selectedResult.quality_overall)">
                    {{ formatQualityScore(selectedResult.quality_overall) }}/5.0
                  </span>
                </td>
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

          <!-- 品質評估詳情 -->
          <div v-if="selectedResult.quality" class="detail-section quality-evaluation">
            <h3>🎯 LLM 品質評估</h3>
            <div class="quality-metrics-grid">
              <div class="quality-metric-item">
                <div class="metric-label">相關性</div>
                <div class="metric-score">{{ selectedResult.quality.relevance }}/5</div>
                <div class="star-rating">
                  <span v-for="i in 5" :key="i"
                        :class="['star', i <= selectedResult.quality.relevance ? 'filled' : 'empty']">
                    ★
                  </span>
                </div>
              </div>
              <div class="quality-metric-item">
                <div class="metric-label">完整性</div>
                <div class="metric-score">{{ selectedResult.quality.completeness }}/5</div>
                <div class="star-rating">
                  <span v-for="i in 5" :key="i"
                        :class="['star', i <= selectedResult.quality.completeness ? 'filled' : 'empty']">
                    ★
                  </span>
                </div>
              </div>
              <div class="quality-metric-item">
                <div class="metric-label">準確性</div>
                <div class="metric-score">{{ selectedResult.quality.accuracy }}/5</div>
                <div class="star-rating">
                  <span v-for="i in 5" :key="i"
                        :class="['star', i <= selectedResult.quality.accuracy ? 'filled' : 'empty']">
                    ★
                  </span>
                </div>
              </div>
              <div class="quality-metric-item">
                <div class="metric-label">意圖匹配</div>
                <div class="metric-score">{{ selectedResult.quality.intent_match }}/5</div>
                <div class="star-rating">
                  <span v-for="i in 5" :key="i"
                        :class="['star', i <= selectedResult.quality.intent_match ? 'filled' : 'empty']">
                    ★
                  </span>
                </div>
              </div>
              <div class="quality-metric-item overall">
                <div class="metric-label">綜合評分</div>
                <div class="metric-score">{{ selectedResult.quality.quality_overall }}/5</div>
                <div class="star-rating">
                  <span v-for="i in 5" :key="i"
                        :class="['star', i <= selectedResult.quality.quality_overall ? 'filled' : 'empty']">
                    ★
                  </span>
                </div>
              </div>
            </div>
            <div v-if="selectedResult.quality.quality_reasoning" class="quality-reasoning">
              <strong>評分理由：</strong>
              <p>{{ selectedResult.quality.quality_reasoning }}</p>
            </div>
          </div>

          <div v-if="selectedResult.source_ids" class="detail-section knowledge-sources">
            <h3>📚 知識來源</h3>
            <div class="knowledge-info">
              <p><strong>來源摘要:</strong></p>
              <p class="sources-summary">{{ selectedResult.knowledge_sources || '無來源' }}</p>

              <div v-if="selectedResult.source_ids" class="knowledge-links-box">
                <p><strong>🔗 查看知識:</strong></p>
                <a
                  :href="`/knowledge?ids=${selectedResult.source_ids}`"
                  target="_blank"
                  class="batch-link"
                >
                  📦 查看相關知識 ({{ selectedResult.source_ids }})
                </a>
              </div>
            </div>
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
            {{ getOptimizeButtonText(selectedResult) }}
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
import InfoPanel from '@/components/InfoPanel.vue';
import helpTexts from '@/config/help-texts.js';

const API_BASE = '/api';

export default {
  name: 'BacktestView',
  components: {
    InfoPanel
  },
  data() {
    return {
      helpTexts,
      results: [],
      statistics: null,
      total: 0,
      loading: false,
      error: null,
      statusFilter: 'all',
      backtestConfig: {
        quality_mode: 'detailed',
        test_strategy: 'incremental'
      },
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
      statusCheckInterval: null,
      backtestRuns: [],        // 歷史回測執行記錄列表
      selectedRunId: null,      // 當前選擇的執行 ID (null = Excel)
      runningProgress: null     // 正在運行的回測進度信息
    };
  },
  computed: {
    currentPage() {
      return Math.floor(this.pagination.offset / this.pagination.limit) + 1;
    }
  },
  async mounted() {
    this.checkBacktestStatus();
    await this.loadBacktestRuns();  // 載入歷史記錄列表

    // 自動選擇最新的數據庫記錄（而不是 Excel）
    if (this.backtestRuns.length > 0) {
      this.selectedRunId = this.backtestRuns[0].id;
      console.log('自動選擇最新的回測記錄:', this.selectedRunId);
    }

    this.loadResults();
  },
  beforeUnmount() {
    if (this.statusCheckInterval) {
      clearInterval(this.statusCheckInterval);
    }
  },
  methods: {
    async loadBacktestRuns() {
      try {
        const response = await axios.get(`${API_BASE}/backtest/runs`, {
          params: { limit: 20, offset: 0 }
        });
        this.backtestRuns = response.data.runs;
      } catch (error) {
        console.error('載入歷史記錄失敗', error);
        // 不顯示錯誤，靜默失敗
      }
    },

    onRunSelected() {
      // 切換到第一頁並重新載入結果
      this.pagination.offset = 0;
      this.loadResults();
    },

    async loadResults() {
      this.loading = true;
      this.error = null;

      try {
        // 確保選擇了有效的 Run ID
        if (!this.selectedRunId) {
          this.error = '請選擇一個回測記錄';
          this.loading = false;
          return;
        }

        const params = {
          status_filter: this.statusFilter,
          limit: this.pagination.limit,
          offset: this.pagination.offset
        };

        // 從資料庫載入回測記錄
        const response = await axios.get(`${API_BASE}/backtest/runs/${this.selectedRunId}/results`, { params });

        this.results = response.data.results;
        this.total = response.data.total;
        this.statistics = response.data.statistics;

        // 資料庫使用 id 和 tested_at，前端需要 test_id 和 timestamp
        this.results = this.results.map(result => ({
          ...result,
          test_id: result.id,
          timestamp: result.tested_at
        }));

      } catch (error) {
        console.error('載入回測結果失敗', error);
        if (error.response?.status === 404) {
          this.error = `找不到 Run ID ${this.selectedRunId} 的回測記錄`;
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

      const hasSource = result.source_ids && result.source_ids.trim();
      const sourceCount = result.source_count || 0;
      const relevance = result.relevance || 0;
      const completeness = result.completeness || 0;
      const question = result.test_question;
      const intent = result.actual_intent;

      // 構建查詢參數
      let queryParams = {};
      let notificationMessage = '';

      // 智能判斷：無知識 OR 相關性很低 OR 完整性不足 → 新增知識
      if (!hasSource || relevance < 3.0 || completeness < 3.0) {
        // 類型 A：知識缺失、不相關或不完整 → 引導新增
        queryParams = {
          action: 'create',
          question: question,
          intent: intent
        };
        if (!hasSource) {
          notificationMessage = `知識庫缺少相關內容，將為您創建新知識`;
        } else if (relevance < 3.0) {
          notificationMessage = `檢索到的知識不相關（相關性 ${relevance.toFixed(1)}/5.0），建議新增正確知識`;
        } else {
          notificationMessage = `檢索到的知識不完整（完整性 ${completeness.toFixed(1)}/5.0），建議新增完整知識`;
        }
      } else if (sourceCount > 1) {
        // 類型 B.1：多個相關且完整的知識來源 → 批量查詢
        queryParams = {
          ids: result.source_ids,
          context: question
        };
        notificationMessage = `已定位到 ${sourceCount} 個相關知識，請逐一檢查優化`;
      } else {
        // 類型 B.2：單個相關且完整的知識來源 → 直接編輯
        queryParams = {
          ids: result.source_ids,
          edit: 'true'
        };
        notificationMessage = `將直接編輯知識 ID: ${result.source_ids}`;
      }

      // 構建完整的 URL（使用新分頁打開）
      const queryString = new URLSearchParams(queryParams).toString();
      const url = `/knowledge?${queryString}`;
      window.open(url, '_blank');

      this.showNotification('info', '已在新分頁打開', notificationMessage);
    },

    getOptimizeButtonText(result) {
      if (!result) return '⚡ 優化';

      const hasSource = result.source_ids && result.source_ids.trim();
      const sourceCount = result.source_count || 0;
      const relevance = result.relevance || 0;
      const completeness = result.completeness || 0;

      // 無知識 OR 相關性很低 OR 完整性不足 → 新增
      if (!hasSource || relevance < 3.0 || completeness < 3.0) {
        return '➕ 新增知識';
      } else if (sourceCount > 1) {
        return `📦 查看 ${sourceCount} 個知識`;
      } else {
        return '✏️ 編輯知識';
      }
    },

    showNotification(type, title, message) {
      // 簡單的通知實現，可以後續替換為更好的通知組件
      const typeEmoji = {
        'info': 'ℹ️',
        'success': '✅',
        'warning': '⚠️',
        'error': '❌'
      };

      const notification = document.createElement('div');
      notification.className = `notification notification-${type}`;
      notification.innerHTML = `
        <strong>${typeEmoji[type] || 'ℹ️'} ${title}</strong>
        <p>${message}</p>
      `;

      document.body.appendChild(notification);

      // 3秒後自動移除
      setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
      }, 3000);
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

    getQualityClass(score) {
      if (score === null || score === undefined) return 'quality-na';
      if (score >= 4.0) return 'quality-excellent';
      if (score >= 3.0) return 'quality-good';
      if (score >= 2.0) return 'quality-fair';
      return 'quality-poor';
    },

    formatQualityScore(score) {
      if (score === null || score === undefined) {
        console.log('formatQualityScore: score is null or undefined', score);
        return 'N/A';
      }
      const num = Number(score);
      if (isNaN(num)) {
        console.log('formatQualityScore: score is NaN', score);
        return 'N/A';
      }
      return num.toFixed(1);
    },

    parseSourceIds(sourceIdsStr) {
      if (!sourceIdsStr || !sourceIdsStr.trim()) {
        return [];
      }
      return sourceIdsStr.split(',').map(id => id.trim()).filter(id => id);
    },

    getQualityRating(score) {
      if (score >= 4.0) return '🎉 優秀';
      if (score >= 3.5) return '✅ 良好';
      if (score >= 3.0) return '⚠️ 中等';
      return '❌ 需改善';
    },

    async runBacktest() {
      const modeText = {
        'detailed': 'Detailed LLM 深度評估（推薦）',
        'hybrid': 'Hybrid 混合評估'
      };

      const strategyText = {
        'incremental': 'Incremental - 智能增量（新增+失敗+過時）',
        'full': 'Full - 完整測試（所有已批准）',
        'failed_only': 'Failed + Untested - 失敗 + 未測試'
      };

      if (!confirm(`確定要執行回測嗎？\n模式：${modeText[this.backtestConfig.quality_mode]}\n策略：${strategyText[this.backtestConfig.test_strategy]}`)) {
        return;
      }

      try {
        const response = await axios.post(`${API_BASE}/backtest/run`, this.backtestConfig);
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

          // 如果正在運行，獲取最新的 run 進度
          if (response.data.is_running) {
            try {
              const runsResponse = await axios.get(`${API_BASE}/backtest/runs?limit=1`);
              if (runsResponse.data.runs && runsResponse.data.runs.length > 0) {
                const latestRun = runsResponse.data.runs[0];

                // 計算進度信息
                const progressPct = Math.round((latestRun.executed_scenarios / latestRun.total_scenarios) * 100);
                const elapsedSeconds = latestRun.duration_seconds || 0;
                const elapsedMin = Math.floor(elapsedSeconds / 60);
                const elapsedSec = elapsedSeconds % 60;

                // 預估剩餘時間
                const remainingTests = latestRun.total_scenarios - latestRun.executed_scenarios;
                const avgTimePerTest = latestRun.executed_scenarios > 0 ? elapsedSeconds / latestRun.executed_scenarios : 10;
                const estimatedRemainingSeconds = remainingTests * avgTimePerTest;
                const estimatedRemainingMin = Math.floor(estimatedRemainingSeconds / 60);

                this.runningProgress = {
                  executed_scenarios: latestRun.executed_scenarios,
                  total_scenarios: latestRun.total_scenarios,
                  progress_pct: progressPct,
                  elapsed: `${elapsedMin}分${elapsedSec}秒`,
                  estimated_remaining: `約${estimatedRemainingMin}分鐘`
                };
              }
            } catch (err) {
              console.error('獲取進度失敗', err);
            }
          }

          if (!response.data.is_running && this.isRunning) {
            // 回測完成
            this.isRunning = false;
            this.runningProgress = null;
            this.lastRunTime = response.data.last_run_time;
            clearInterval(this.statusCheckInterval);
            this.statusCheckInterval = null;

            // 重新載入歷史記錄列表
            await this.loadBacktestRuns();

            // 自動切換到最新的資料庫記錄（如果有的話）
            if (this.backtestRuns.length > 0) {
              this.selectedRunId = this.backtestRuns[0].id;
            }

            // 自動重新載入結果
            await this.loadResults();
            alert('✅ 回測執行完成！結果已自動刷新。');
          }
        } catch (error) {
          console.error('監控狀態失敗', error);
        }
      }, 5000);
    },

    async cancelBacktest() {
      if (confirm('⚠️ 確定要中斷當前回測嗎？\n\n中斷後：\n✓ 已完成的測試結果會保留\n✓ 可以在列表中查看部分結果\n✗ 未完成的測試不會繼續執行')) {
        try {
          const response = await axios.post(`${API_BASE}/backtest/cancel`);

          if (response.data.success) {
            alert(`✅ ${response.data.message}`);

            // 停止監控
            if (this.statusCheckInterval) {
              clearInterval(this.statusCheckInterval);
              this.statusCheckInterval = null;
            }

            // 重置狀態
            this.isRunning = false;
            this.runningProgress = null;

            // 重新載入回測記錄列表
            await this.loadBacktestRuns();

            // 重新載入結果
            await this.loadResults();
          } else {
            alert(`❌ ${response.data.message}`);
          }
        } catch (error) {
          console.error('中斷回測失敗', error);
          alert('❌ 中斷回測失敗，請稍後再試');
        }
      }
    },

    forceStopMonitoring() {
      if (confirm('確定要停止進度監控嗎？\n\n這只會停止前端的進度更新，不會中斷回測本身。\n\n如果要中斷回測，請使用「🛑 中斷回測」按鈕。')) {
        // 清除定時器
        if (this.statusCheckInterval) {
          clearInterval(this.statusCheckInterval);
          this.statusCheckInterval = null;
        }

        // 重置狀態
        this.isRunning = false;
        this.runningProgress = null;

        // 重新檢查狀態
        this.checkBacktestStatus();

        // 重新載入結果
        this.loadResults();

        alert('✅ 監控已停止，回測仍在背景運行');
      }
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
    },

    formatRunDate(isoString) {
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
.backtest-view {
  /* width 由 app-main 統一管理 */
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

.stat-card.quality {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
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

.stat-rating {
  font-size: 14px;
  margin-top: 5px;
  opacity: 0.95;
}

/* 品質統計區塊 */
.quality-stats-section {
  margin-bottom: 30px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 15px;
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

.run-selector {
  min-width: 300px;
  max-width: 500px;
  padding: 8px 12px;
  border: 2px solid #667eea;
  border-radius: 4px;
  font-size: 14px;
  background: white;
  font-weight: 500;
  cursor: pointer;
}

.run-selector:focus {
  outline: none;
  border-color: #5568d3;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
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

.progress-details {
  margin-top: 15px;
}

.progress-text {
  font-size: 18px;
  font-weight: 600;
  color: #d46b08;
  margin-bottom: 10px;
}

.progress-bar-container {
  width: 100%;
  height: 24px;
  background: #f0f0f0;
  border-radius: 12px;
  overflow: hidden;
  margin: 10px 0;
  border: 1px solid #d9d9d9;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #52c41a 0%, #73d13d 100%);
  transition: width 0.5s ease;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 10px;
  color: white;
  font-weight: 600;
  font-size: 12px;
}

.progress-info {
  font-size: 14px;
  color: #595959;
  margin-top: 8px;
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

.score-badge, .confidence-badge, .quality-badge {
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

/* 品質評分樣式 */
.quality-excellent {
  background: #67c23a;
  color: white;
}

.quality-good {
  background: #409eff;
  color: white;
}

.quality-fair {
  background: #e6a23c;
  color: white;
}

.quality-poor {
  background: #f56c6c;
  color: white;
}

.quality-na {
  background: #909399;
  color: white;
}

/* 知識 ID 按鈕樣式 */
.knowledge-ids-section {
  margin-top: 12px;
}

.knowledge-id-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.knowledge-id-btn {
  display: inline-block;
  padding: 6px 12px;
  background: #409eff;
  color: white;
  border-radius: 4px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  border: 1px solid #409eff;
}

.knowledge-id-btn:hover {
  background: #66b1ff;
  border-color: #66b1ff;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(64, 158, 255, 0.3);
}

.score-low, .confidence-low {
  background: #f56c6c;
  color: white;
}

/* 按鈕 */
.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #5568d3 0%, #64398f 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.btn-primary:disabled {
  background: #e9ecef;
  color: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
  transform: none;
  box-shadow: none;
}

.btn-secondary {
  background: #e9ecef;
  color: #495057;
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-secondary:hover:not(:disabled) {
  background: #d3d9df;
  transform: translateY(-1px);
}

.btn-detail, .btn-optimize {
  padding: 6px 12px;
  margin: 2px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-detail {
  background-color: #667eea;
  color: white;
}

.btn-detail:hover {
  background-color: #5568d3;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.btn-optimize {
  background-color: #e6a23c;
  color: white;
}

.btn-optimize:hover {
  background-color: #cf912c;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(230, 162, 60, 0.3);
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
  background: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-pagination:hover:not(:disabled) {
  background: #5568d3;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.btn-pagination:disabled {
  background: #e9ecef;
  color: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
  transform: none;
  box-shadow: none;
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

/* 知識來源區塊 */
.knowledge-sources {
  background: #f0f9ff;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #91d5ff;
}

.knowledge-sources h3 {
  color: #0050b3;
  margin-top: 0;
}

.knowledge-info {
  font-size: 14px;
  line-height: 1.8;
}

.knowledge-info p {
  margin: 10px 0;
}

.sources-summary {
  background: white;
  padding: 12px;
  border-radius: 6px;
  color: #303133;
  font-size: 13px;
  border: 1px solid #d9d9d9;
}

.knowledge-links-box {
  background: white;
  padding: 15px;
  border-radius: 6px;
  margin-top: 15px;
  border: 1px solid #d9d9d9;
}

.knowledge-links-box p {
  margin: 0 0 10px 0;
  font-weight: 500;
}

.batch-link {
  display: inline-block;
  padding: 10px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white !important;
  text-decoration: none;
  border-radius: 6px;
  font-weight: 500;
  transition: all 0.3s;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.batch-link:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5);
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
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

/* 品質評估詳情 */
.quality-evaluation {
  background: #f0f9ff;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #91d5ff;
}

.quality-evaluation h3 {
  color: #0050b3;
  margin-top: 0;
}

.quality-metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.quality-metric-item {
  background: white;
  padding: 15px;
  border-radius: 6px;
  text-align: center;
  border: 1px solid #d9d9d9;
}

.quality-metric-item.overall {
  border: 2px solid #667eea;
  background: linear-gradient(135deg, #f8f9ff 0%, #fff 100%);
}

.metric-label {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
  font-weight: 500;
}

.metric-score {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 5px;
}

.star-rating {
  display: flex;
  justify-content: center;
  gap: 2px;
}

.star {
  font-size: 18px;
  transition: all 0.2s;
}

.star.filled {
  color: #fadb14;
  text-shadow: 0 0 2px rgba(250, 219, 20, 0.5);
}

.star.empty {
  color: #d9d9d9;
}

.quality-reasoning {
  background: white;
  padding: 15px;
  border-radius: 6px;
  border: 1px solid #d9d9d9;
}

.quality-reasoning strong {
  display: block;
  margin-bottom: 8px;
  color: #0050b3;
}

.quality-reasoning p {
  margin: 0;
  line-height: 1.6;
  color: #303133;
  font-size: 14px;
}

/* Notification Styles */
.notification {
  position: fixed;
  top: 80px;
  right: 20px;
  min-width: 300px;
  max-width: 400px;
  padding: 16px 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 9999;
  animation: slideIn 0.3s ease-out;
  transition: opacity 0.3s ease;
}

.notification strong {
  display: block;
  margin-bottom: 8px;
  font-size: 15px;
  color: #303133;
}

.notification p {
  margin: 0;
  font-size: 14px;
  color: #606266;
  line-height: 1.5;
}

.notification-info {
  border-left: 4px solid #1890ff;
}

.notification-success {
  border-left: 4px solid #52c41a;
}

.notification-warning {
  border-left: 4px solid #faad14;
}

.notification-error {
  border-left: 4px solid #f5222d;
}

@keyframes slideIn {
  from {
    transform: translateX(400px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
</style>
