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
        <select v-model="selectedRunId" @change="onRunSelected" class="run-selector" :disabled="backtestRuns.length === 0">
          <option v-if="backtestRuns.length === 0" value="" disabled>尚無回測記錄</option>
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
        <label>測試業者：</label>
        <select v-model="backtestConfig.vendor_id">
          <option :value="1">心巢房屋股份有限公司</option>
          <option :value="2">富喬物業管理顧問股份有限公司</option>
          <option :value="3">愛租屋資產管理</option>
        </select>
      </div>
    </div>

    <!-- Smart Batch Toggle -->
    <div class="smart-batch-toggle-section">
      <label class="smart-batch-toggle-label">
        <input type="checkbox" v-model="enableSmartBatch" />
        <span class="toggle-text">🎯 智能分批模式</span>
      </label>
    </div>

    <!-- Smart Batch Controls (when enabled) -->
    <div v-if="enableSmartBatch" class="smart-batch-controls">
      <h3 class="section-title">📦 智能分批設定</h3>
      <div class="smart-batch-grid">
        <div class="filter-group">
          <label>批量大小：</label>
          <select v-model.number="smartBatchConfig.batch_size" @change="updateBatchInfo">
            <option :value="50">50 題/批</option>
            <option :value="100">100 題/批</option>
            <option :value="200">200 題/批 (推薦)</option>
            <option :value="500">500 題/批</option>
          </select>
        </div>

        <div class="filter-group">
          <label>題目狀態：</label>
          <select v-model="smartBatchConfig.status" @change="updateBatchInfo">
            <option value="">全部</option>
            <option value="pending_review">待審核</option>
            <option value="approved">已批准</option>
            <option value="rejected">已拒絕</option>
          </select>
        </div>

        <div class="filter-group">
          <label>題目來源：</label>
          <select v-model="smartBatchConfig.source" @change="updateBatchInfo">
            <option value="">全部</option>
            <option value="imported">匯入</option>
            <option value="manual">手動建立</option>
            <option value="user_question">用戶問題</option>
          </select>
        </div>

        <div class="filter-group">
          <label>難度：</label>
          <select v-model="smartBatchConfig.difficulty" @change="updateBatchInfo">
            <option value="">全部</option>
            <option value="easy">簡單</option>
            <option value="medium">中等</option>
            <option value="hard">困難</option>
          </select>
        </div>
      </div>

      <div v-if="batchInfo" class="batch-info-display">
        <p>
          📊 符合條件的題目總數: <strong>{{ batchInfo.total }}</strong> 題 |
          批量大小: <strong>{{ smartBatchConfig.batch_size }}</strong> 題/批 |
          預估批次數: <strong>{{ Math.ceil(batchInfo.total / smartBatchConfig.batch_size) }}</strong> 批
        </p>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="toolbar">
      <button v-if="enableSmartBatch" @click="runSmartBatch()" class="btn-run" :disabled="isRunning">
        <span v-if="isRunning">⏳ 執行中...</span>
        <span v-else>🎯 執行分批回測</span>
      </button>

      <button v-if="enableSmartBatch" @click="runContinuousBatch()" class="btn-continuous" :disabled="isRunning">
        🚀 連續分批執行全部
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
        <!-- 連續分批模式顯示批次進度 -->
        <p v-if="runningProgress.total_batches" class="batch-progress-text">
          📦 批次進度: {{ runningProgress.completed_batches }}/{{ runningProgress.total_batches }}
          ({{ Math.round(runningProgress.completed_batches / runningProgress.total_batches * 100) }}%)
        </p>
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
            <th width="120">信心度分數</th>
            <th width="90">信心等級</th>
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
                <span v-if="result.is_form" class="form-badge">📝 表單</span>
                {{ result.system_answer.substring(0, 100) }}...
              </div>
            </td>
            <td>
              <span class="badge" :class="{ 'badge-unclear': result.actual_intent === 'unclear' }">
                {{ result.actual_intent || 'N/A' }}
              </span>
            </td>
            <td>
              <span class="confidence-badge" :class="getConfidenceScoreClass(result.confidence_score)">
                {{ formatConfidenceScore(result.confidence_score) }}
              </span>
            </td>
            <td>
              <span class="confidence-level-badge" :class="'level-' + (result.confidence_level || 'unknown')">
                {{ formatConfidenceLevel(result.confidence_level) }}
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
                <td><strong>信心度分數:</strong></td>
                <td>
                  <span class="confidence-badge" :class="getConfidenceScoreClass(selectedResult.confidence_score)">
                    {{ formatConfidenceScore(selectedResult.confidence_score) }}
                  </span>
                </td>
              </tr>
              <tr>
                <td><strong>信心等級:</strong></td>
                <td>
                  <span class="confidence-level-badge" :class="'level-' + (selectedResult.confidence_level || 'unknown')">
                    {{ formatConfidenceLevel(selectedResult.confidence_level) }}
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
              <span v-if="selectedResult.is_form" class="form-badge-large">📝 表單類型</span>
              <p>{{ selectedResult.system_answer }}</p>
            </div>
          </div>

          <!-- V2 信心度計算詳情 -->
          <div class="detail-section confidence-evaluation">
            <h3>🎯 信心度計算詳情</h3>
            <div class="confidence-metrics-grid">
              <div class="confidence-metric-item main">
                <div class="metric-label">Confidence Score</div>
                <div class="metric-value">
                  <span class="confidence-badge" :class="getConfidenceScoreClass(selectedResult.confidence_score)">
                    {{ formatConfidenceScore(selectedResult.confidence_score) }}
                  </span>
                  <span class="confidence-level-badge" :class="'level-' + (selectedResult.confidence_level || 'unknown')">
                    {{ formatConfidenceLevel(selectedResult.confidence_level) }}
                  </span>
                </div>
              </div>

              <div class="confidence-metric-item">
                <div class="metric-label">
                  <span class="label-text">最高文檔相似度</span>
                  <span class="label-weight">(權重 70%)</span>
                </div>
                <div class="metric-value">{{ formatFloat(selectedResult.max_similarity) }}</div>
                <div class="progress-bar">
                  <div class="progress-fill" :style="{width: (parseFloat(selectedResult.max_similarity || 0) * 100) + '%'}"></div>
                </div>
              </div>

              <div class="confidence-metric-item">
                <div class="metric-label">
                  <span class="label-text">檢索文檔數量</span>
                  <span class="label-weight">(權重 20%)</span>
                </div>
                <div class="metric-value">{{ selectedResult.result_count || 0 }} 篇</div>
                <div class="progress-bar">
                  <div class="progress-fill" :style="{width: Math.min((parseInt(selectedResult.result_count || 0) / 5 * 100), 100) + '%'}"></div>
                </div>
              </div>

              <div class="confidence-metric-item">
                <div class="metric-label">
                  <span class="label-text">關鍵字匹配率</span>
                  <span class="label-weight">(權重 10%)</span>
                </div>
                <div class="metric-value">{{ formatFloat(selectedResult.keyword_match_rate) }}</div>
                <div class="progress-bar">
                  <div class="progress-fill" :style="{width: (parseFloat(selectedResult.keyword_match_rate || 0) * 100) + '%'}"></div>
                </div>
              </div>
            </div>

            <!-- 計算公式說明 -->
            <div class="formula-explanation">
              <strong>📐 計算公式：</strong>
              <pre class="formula">confidence_score = max_similarity × 0.7 + min(result_count/5, 1.0) × 0.2 + keyword_match_rate × 0.1</pre>
              <pre class="formula-example" v-if="selectedResult.max_similarity && selectedResult.result_count && selectedResult.keyword_match_rate">
                             = {{ formatFloat(selectedResult.max_similarity) }} × 0.7 + min({{ selectedResult.result_count }}/5, 1.0) × 0.2 + {{ formatFloat(selectedResult.keyword_match_rate) }} × 0.1
                             = {{ formatFloat(parseFloat(selectedResult.max_similarity || 0) * 0.7) }} + {{ formatFloat(Math.min(parseFloat(selectedResult.result_count || 0) / 5, 1.0) * 0.2) }} + {{ formatFloat(parseFloat(selectedResult.keyword_match_rate || 0) * 0.1) }}
                             ≈ {{ formatConfidenceScore(selectedResult.confidence_score) }}
              </pre>
            </div>

            <!-- 通過/失敗原因 -->
            <div class="pass-reason">
              <strong v-if="selectedResult.passed">✅ 通過原因：</strong>
              <strong v-else>❌ 失敗原因：</strong>
              <p v-if="selectedResult.failure_reason">{{ selectedResult.failure_reason }}</p>
              <p v-else-if="selectedResult.passed && selectedResult.confidence_score >= 0.85">
                高信心度 (confidence_score ≥ 0.85)
              </p>
              <p v-else-if="selectedResult.passed && selectedResult.confidence_score >= 0.70">
                中信心度 (confidence_score ≥ 0.70)
              </p>
              <p v-else-if="selectedResult.passed && selectedResult.confidence_score >= 0.60">
                及格信心度 (confidence_score ≥ 0.60)
              </p>
              <p v-else-if="!selectedResult.passed">
                信心度不足 (confidence_score < 0.60)
              </p>
            </div>
          </div>

          <div v-if="selectedResult.source_ids" class="detail-section knowledge-sources">
            <h3>📚 知識來源 (共 {{ selectedResult.result_count || getSourceCount(selectedResult.source_ids) }} 篇)</h3>
            <div class="knowledge-info">
              <p><strong>來源摘要:</strong></p>
              <p class="sources-summary">{{ selectedResult.knowledge_sources || '無來源' }}</p>

              <div v-if="selectedResult.source_ids" class="knowledge-links-box">
                <p><strong>🔗 查看知識:</strong></p>
                <div class="source-ids-list">
                  <a
                    v-for="id in getSourceIdArray(selectedResult.source_ids)"
                    :key="id"
                    :href="`/knowledge?ids=${id}`"
                    target="_blank"
                    class="source-id-link"
                  >
                    📄 知識 #{{ id }}
                  </a>
                </div>
                <a
                  :href="`/knowledge?ids=${selectedResult.source_ids}`"
                  target="_blank"
                  class="batch-link"
                >
                  📦 一次查看全部 ({{ selectedResult.source_ids }})
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
        vendor_id: 2  // 預設使用富喬物業
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
      runningProgress: null,   // 正在運行的回測進度信息
      // Smart Batch 配置
      enableSmartBatch: false,
      smartBatchConfig: {
        batch_size: 200,
        quality_mode: 'hybrid',
        status: '',
        source: '',
        difficulty: ''
      },
      batchInfo: null          // 批次信息（總數、範圍等）
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

    // 預先載入批次資訊，避免點擊按鈕時延遲
    if (this.enableSmartBatch) {
      await this.updateBatchInfo();
    }
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
      if (!hasSource || relevance < 5.0 || completeness < 5.0) {
        // 類型 A：知識缺失、不相關或不完整 → 引導新增
        queryParams = {
          action: 'create',
          question: question,
          intent: intent
        };
        if (!hasSource) {
          notificationMessage = `知識庫缺少相關內容，將為您創建新知識`;
        } else if (relevance < 5.0) {
          notificationMessage = `檢索到的知識不相關（相關性 ${relevance.toFixed(1)}/10.0），建議新增正確知識`;
        } else {
          notificationMessage = `檢索到的知識不完整（完整性 ${completeness.toFixed(1)}/10.0），建議新增完整知識`;
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
      if (!hasSource || relevance < 5.0 || completeness < 5.0) {
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
      if (score >= 8.0) return 'quality-excellent';
      if (score >= 6.0) return 'quality-good';
      if (score >= 4.0) return 'quality-fair';
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
      if (score >= 8.0) return '🎉 優秀';
      if (score >= 7.0) return '✅ 良好';
      if (score >= 6.0) return '⚠️ 中等';
      return '❌ 需改善';
    },

    async updateBatchInfo() {
      try {
        const params = {
          status: this.smartBatchConfig.status || null,
          source: this.smartBatchConfig.source || null,
          difficulty: this.smartBatchConfig.difficulty || null
        };

        const response = await axios.post(`${API_BASE}/test-scenarios/count`, params);
        const total = response.data.total;

        this.batchInfo = {
          total
        };
      } catch (error) {
        console.error('獲取題數統計失敗', error);
        this.batchInfo = null;
      }
    },

    async runSmartBatch() {
      if (!this.batchInfo) {
        await this.updateBatchInfo();
      }

      const firstBatchCount = Math.min(this.smartBatchConfig.batch_size, this.batchInfo.total);

      const confirmMsg = `🎯 確定要執行分批回測嗎？\n\n` +
        `📦 批量設定：${this.smartBatchConfig.batch_size} 題/批\n` +
        `🔢 執行批次：第 1 批\n` +
        `📊 符合條件總數：${this.batchInfo.total} 題\n` +
        `🧪 本次測試：${firstBatchCount} 題\n\n` +
        `⚙️ 品質模式：${this.backtestConfig.quality_mode}\n` +
        `${this.smartBatchConfig.status ? `📌 狀態篩選：${this.smartBatchConfig.status}\n` : ''}` +
        `${this.smartBatchConfig.source ? `📌 來源篩選：${this.smartBatchConfig.source}\n` : ''}` +
        `${this.smartBatchConfig.difficulty ? `📌 難度篩選：${this.smartBatchConfig.difficulty}\n` : ''}`;

      if (!confirm(confirmMsg)) {
        return;
      }

      try {
        const requestData = {
          batch_size: this.smartBatchConfig.batch_size,
          batch_number: 1,  // 固定執行第 1 批
          quality_mode: this.backtestConfig.quality_mode,
          vendor_id: this.backtestConfig.vendor_id,
          status: this.smartBatchConfig.status || null,
          source: this.smartBatchConfig.source || null,
          difficulty: this.smartBatchConfig.difficulty || null
        };

        const response = await axios.post(`${API_BASE}/backtest/run/smart-batch`, requestData);

        const successMsg = `✅ ${response.data.message}\n\n` +
          `📦 ${response.data.batch_info.range}\n` +
          `🧪 測試數量：${response.data.batch_info.actual_count} 題\n` +
          `⏱️ ${response.data.estimated_time}`;

        alert(successMsg);

        // 開始監控狀態
        this.isRunning = true;
        this.startStatusMonitoring();
      } catch (error) {
        console.error('執行分批回測失敗', error);
        if (error.response?.status === 409) {
          alert('⚠️ 回測已在執行中，請等待完成後再試');
        } else if (error.response?.status === 400) {
          alert('❌ ' + (error.response?.data?.detail || '參數錯誤'));
        } else {
          alert('執行失敗：' + (error.response?.data?.detail || error.message));
        }
      }
    },

    async runContinuousBatch() {
      // 先更新批次信息
      if (!this.batchInfo) {
        await this.updateBatchInfo();
      }

      // 檢查是否成功獲取批次信息
      if (!this.batchInfo || !this.batchInfo.total) {
        alert('❌ 無法獲取測試題目數量，請確認：\n1. 是否已登入系統\n2. 資料庫是否有測試題目');
        return;
      }

      const total = this.batchInfo.total;
      const batchSize = this.smartBatchConfig.batch_size;
      const totalBatches = Math.ceil(total / batchSize);
      const estimatedMinutes = Math.ceil(total * 0.1 / 60); // 假設每題 0.1 秒

      const confirmMsg = `🚀 確定要執行連續分批回測嗎？\n\n` +
        `📊 符合條件總數：${total} 題\n` +
        `📦 批量設定：${batchSize} 題/批\n` +
        `🔢 總批次數：${totalBatches} 批\n\n` +
        `⚙️ 品質模式：${this.backtestConfig.quality_mode}\n` +
        `${this.smartBatchConfig.status ? `📌 狀態篩選：${this.smartBatchConfig.status}\n` : ''}` +
        `${this.smartBatchConfig.source ? `📌 來源篩選：${this.smartBatchConfig.source}\n` : ''}` +
        `${this.smartBatchConfig.difficulty ? `📌 難度篩選：${this.smartBatchConfig.difficulty}\n` : ''}\n` +
        `⏱️ 預估耗時：約 ${estimatedMinutes} 分鐘\n\n` +
        `⚠️ 注意：\n` +
        `• 系統將自動執行所有 ${totalBatches} 個批次\n` +
        `• 所有結果將合併到同一個報告中\n` +
        `• 您可以關閉瀏覽器，執行會在背景繼續\n` +
        `• 您可以隨時回到此頁面查看進度`;

      if (!confirm(confirmMsg)) {
        return;
      }

      try {
        const requestData = {
          batch_size: batchSize,
          quality_mode: this.backtestConfig.quality_mode,
          vendor_id: this.backtestConfig.vendor_id,
          status: this.smartBatchConfig.status || null,
          source: this.smartBatchConfig.source || null,
          difficulty: this.smartBatchConfig.difficulty || null
        };

        const response = await axios.post(`${API_BASE}/backtest/run/continuous-batch`, requestData);

        const successMsg = `✅ ${response.data.message}\n\n` +
          `🆔 Run ID: ${response.data.run_id}\n` +
          `📦 總批次數: ${response.data.total_batches}\n` +
          `🧪 總測試數: ${response.data.total_scenarios} 題\n` +
          `⏱️ ${response.data.estimated_time}\n\n` +
          `💡 系統將在背景自動執行，請稍候...`;

        alert(successMsg);

        // 開始監控狀態
        this.isRunning = true;
        this.startStatusMonitoring();
      } catch (error) {
        console.error('執行連續分批回測失敗', error);
        if (error.response?.status === 409) {
          alert('⚠️ 回測已在執行中，請等待完成後再試');
        } else if (error.response?.status === 400) {
          alert('❌ ' + (error.response?.data?.detail || '參數錯誤'));
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
    },

    formatConfidenceScore(score) {
      if (score === null || score === undefined) return 'N/A';
      const num = Number(score);
      if (isNaN(num)) return 'N/A';
      return num.toFixed(3);
    },

    formatConfidenceLevel(level) {
      const levelMap = {
        'high': '🟢 高',
        'medium': '🟡 中',
        'low': '🔴 低'
      };
      return levelMap[level] || 'N/A';
    },

    formatFloat(value) {
      if (value === null || value === undefined) return 'N/A';
      const num = Number(value);
      if (isNaN(num)) return 'N/A';
      return num.toFixed(3);
    },

    getSourceIdArray(sourceIds) {
      if (!sourceIds) return [];
      return sourceIds.toString().split(',').map(id => id.trim()).filter(id => id);
    },

    getSourceCount(sourceIds) {
      return this.getSourceIdArray(sourceIds).length;
    },

    getConfidenceScoreClass(score) {
      if (score === null || score === undefined) return 'confidence-na';
      if (score >= 0.85) return 'confidence-high';
      if (score >= 0.70) return 'confidence-medium';
      return 'confidence-low';
    }
  }
};
</script>

<style scoped>
/* ==================== 全局容器 ==================== */
.backtest-view {
  /* width 由 app-main 統一管理 */
  animation: fadeIn 0.4s ease-in;
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

/* ==================== 統計卡片區域 ==================== */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 24px;
  margin-bottom: 32px;
}

.stat-card {
  position: relative;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 28px 24px;
  border-radius: 16px;
  text-align: center;
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.25);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.1) 0%, transparent 100%);
  pointer-events: none;
}

.stat-card:hover {
  transform: translateY(-6px) scale(1.02);
  box-shadow: 0 12px 32px rgba(102, 126, 234, 0.35);
}

.stat-card.success {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.25);
}

.stat-card.success:hover {
  box-shadow: 0 12px 32px rgba(16, 185, 129, 0.35);
}

.stat-card.fail {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  box-shadow: 0 8px 24px rgba(239, 68, 68, 0.25);
}

.stat-card.fail:hover {
  box-shadow: 0 12px 32px rgba(239, 68, 68, 0.35);
}

.stat-card.rate {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.25);
}

.stat-card.rate:hover {
  box-shadow: 0 12px 32px rgba(59, 130, 246, 0.35);
}

.stat-card.score {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  box-shadow: 0 8px 24px rgba(245, 158, 11, 0.25);
}

.stat-card.score:hover {
  box-shadow: 0 12px 32px rgba(245, 158, 11, 0.35);
}

.stat-card.confidence {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  box-shadow: 0 8px 24px rgba(139, 92, 246, 0.25);
}

.stat-card.confidence:hover {
  box-shadow: 0 12px 32px rgba(139, 92, 246, 0.35);
}

.stat-card.quality {
  background: linear-gradient(135deg, #ec4899 0%, #db2777 100%);
  box-shadow: 0 8px 24px rgba(236, 72, 153, 0.25);
}

.stat-card.quality:hover {
  box-shadow: 0 12px 32px rgba(236, 72, 153, 0.35);
}

.stat-label {
  position: relative;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  opacity: 0.92;
  margin-bottom: 12px;
}

.stat-value {
  position: relative;
  font-size: 38px;
  font-weight: 700;
  letter-spacing: -0.5px;
  line-height: 1.2;
}

.stat-rating {
  position: relative;
  font-size: 13px;
  margin-top: 8px;
  opacity: 0.9;
  font-weight: 500;
}

/* ==================== 品質統計區塊 ==================== */
.quality-stats-section {
  margin-bottom: 32px;
}

.section-title {
  font-size: 19px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 18px;
  letter-spacing: -0.3px;
}

.quality-cards {
  gap: 20px;
}

/* ==================== 工具列 ==================== */
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  margin-bottom: 24px;
  padding: 20px 24px;
  background: linear-gradient(to bottom, #ffffff, #f9fafb);
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.filter-group label {
  font-weight: 600;
  font-size: 14px;
  color: #374151;
}

.filter-group select {
  padding: 10px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  background: white;
  transition: all 0.2s ease;
  cursor: pointer;
}

.filter-group select:hover {
  border-color: #9ca3af;
}

.filter-group select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.run-selector {
  min-width: 320px;
  max-width: 520px;
  padding: 10px 14px;
  border: 2px solid #667eea;
  border-radius: 8px;
  font-size: 14px;
  background: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.run-selector:hover {
  border-color: #5568d3;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.15);
}

.run-selector:focus {
  outline: none;
  border-color: #5568d3;
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.12);
}

.run-selector:disabled {
  background: #f3f4f6;
  border-color: #d1d5db;
  color: #9ca3af;
  cursor: not-allowed;
  opacity: 0.6;
}

.btn-run {
  padding: 10px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.btn-run:hover:not(:disabled) {
  transform: translateY(-3px);
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
  background: linear-gradient(135deg, #5568d3 0%, #64398f 100%);
}

.btn-run:active:not(:disabled) {
  transform: translateY(-1px);
}

.btn-run:disabled {
  background: linear-gradient(135deg, #d1d5db 0%, #9ca3af 100%);
  cursor: not-allowed;
  opacity: 0.6;
  box-shadow: none;
}

.btn-continuous {
  padding: 10px 20px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.btn-continuous:hover:not(:disabled) {
  transform: translateY(-3px);
  box-shadow: 0 8px 20px rgba(59, 130, 246, 0.4);
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
}

.btn-continuous:active:not(:disabled) {
  transform: translateY(-1px);
}

.btn-continuous:disabled {
  background: linear-gradient(135deg, #d1d5db 0%, #9ca3af 100%);
  cursor: not-allowed;
  opacity: 0.6;
  box-shadow: none;
}

.btn-refresh, .btn-summary {
  padding: 10px 20px;
  background: linear-gradient(to bottom, #667eea, #5568d3);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
}

.btn-refresh:hover:not(:disabled), .btn-summary:hover {
  background: linear-gradient(to bottom, #5568d3, #4451b8);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.btn-refresh:disabled {
  background: #d1d5db;
  cursor: not-allowed;
  opacity: 0.6;
  box-shadow: none;
}

.last-run-time {
  margin-left: auto;
  color: #6b7280;
  font-size: 13px;
  font-weight: 500;
}

/* ==================== Smart Batch Controls ==================== */
.smart-batch-toggle-section {
  margin: 20px 0;
  padding: 0;
}

.smart-batch-toggle-label {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  font-weight: 600;
  color: #1f2937;
  padding: 12px 20px;
  background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
  border-radius: 12px;
  border: 2px solid #e5e7eb;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.smart-batch-toggle-label:hover {
  border-color: #667eea;
  background: linear-gradient(135deg, #f0f4ff 0%, #ffffff 100%);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
  transform: translateY(-2px);
}

.smart-batch-toggle-label input[type="checkbox"] {
  width: 22px;
  height: 22px;
  cursor: pointer;
  accent-color: #667eea;
  margin: 0;
}

.smart-batch-toggle-label .toggle-text {
  font-size: 15px;
  user-select: none;
}

.smart-batch-controls {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 2px solid #667eea;
  border-radius: 16px;
  padding: 28px;
  margin-bottom: 24px;
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.1);
}

.smart-batch-controls .section-title {
  margin-top: 0;
  color: #667eea;
  font-size: 20px;
}

.smart-batch-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.smart-batch-grid .filter-group {
  flex-direction: column;
  align-items: stretch;
}

.smart-batch-grid .filter-group label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 8px;
  letter-spacing: 0.2px;
}

.smart-batch-grid .filter-group select,
.smart-batch-grid .filter-group input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  background: white;
  transition: all 0.2s ease;
}

.smart-batch-grid .filter-group select:focus,
.smart-batch-grid .filter-group input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.smart-batch-grid .filter-group input[type="number"] {
  -moz-appearance: textfield;
}

.smart-batch-grid .filter-group input[type="number"]::-webkit-outer-spin-button,
.smart-batch-grid .filter-group input[type="number"]::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.batch-info-display {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 16px 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.batch-info-display p {
  margin: 0;
  font-size: 14px;
  color: #1f2937;
  line-height: 1.8;
  font-weight: 500;
}

.batch-info-display strong {
  color: #667eea;
  font-weight: 700;
}

.batch-info-display .warning {
  color: #ef4444;
  font-weight: 700;
  margin-left: 10px;
}

/* ==================== 執行狀態 ==================== */
.running-status {
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
  border: 2px solid #fbbf24;
  border-radius: 16px;
  padding: 28px;
  margin-bottom: 24px;
  text-align: center;
  box-shadow: 0 4px 16px rgba(251, 191, 36, 0.15);
}

.running-status p {
  margin: 8px 0;
  color: #b45309;
  font-size: 17px;
  font-weight: 600;
}

.running-status .hint {
  font-size: 14px;
  color: #78716c;
  font-weight: 500;
}

.progress-details {
  margin-top: 20px;
}

.batch-progress-text {
  font-size: 17px;
  font-weight: 700;
  color: #2563eb;
  margin-bottom: 10px;
}

.progress-text {
  font-size: 19px;
  font-weight: 700;
  color: #b45309;
  margin-bottom: 14px;
}

.progress-bar-container {
  width: 100%;
  height: 28px;
  background: #f3f4f6;
  border-radius: 14px;
  overflow: hidden;
  margin: 14px 0;
  border: 2px solid #e5e7eb;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.06);
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981 0%, #059669 50%, #10b981 100%);
  background-size: 200% 100%;
  animation: shimmer 2s infinite;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 12px;
  color: white;
  font-weight: 700;
  font-size: 13px;
  box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.3);
}

@keyframes shimmer {
  0% {
    background-position: 0% 0%;
  }
  50% {
    background-position: 100% 0%;
  }
  100% {
    background-position: 0% 0%;
  }
}

.progress-info {
  font-size: 14px;
  color: #57534e;
  margin-top: 10px;
  font-weight: 500;
}

.loading-bar {
  width: 100%;
  height: 5px;
  background: #f3f4f6;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 18px;
}

.loading-bar::after {
  content: '';
  display: block;
  width: 40%;
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  animation: loading 2s ease-in-out infinite;
  box-shadow: 0 0 10px rgba(102, 126, 234, 0.5);
}

@keyframes loading {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(350%);
  }
}

/* ==================== 結果表格 ==================== */
.results-container {
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  border: 1px solid #e5e7eb;
}

.results-info {
  padding: 18px 24px;
  background: linear-gradient(to bottom, #f9fafb, #f3f4f6);
  border-bottom: 2px solid #e5e7eb;
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.results-table {
  width: 100%;
  border-collapse: collapse;
}

.results-table thead {
  background: linear-gradient(to bottom, #f9fafb, #f3f4f6);
}

.results-table th {
  padding: 16px 14px;
  text-align: left;
  font-weight: 700;
  font-size: 13px;
  color: #1f2937;
  border-bottom: 2px solid #d1d5db;
  letter-spacing: 0.3px;
  text-transform: uppercase;
}

.results-table tbody tr {
  border-bottom: 1px solid #f3f4f6;
  transition: all 0.2s ease;
}

.results-table tbody tr:hover {
  background: #f9fafb;
  box-shadow: inset 0 0 0 2px #e5e7eb;
}

.results-table tbody tr.failed-row {
  background: #fef2f2;
}

.results-table tbody tr.failed-row:hover {
  background: #fee2e2;
  box-shadow: inset 0 0 0 2px #fecaca;
}

.results-table tbody tr:nth-child(even):not(.failed-row) {
  background: #fafafa;
}

.results-table td {
  padding: 16px 14px;
  vertical-align: top;
}

.question-cell {
  max-width: 400px;
}

.question-text {
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 8px;
  line-height: 1.5;
}

.answer-preview {
  font-size: 13px;
  color: #6b7280;
  line-height: 1.5;
}

/* ==================== Badge 樣式（統一規格）==================== */
.badge {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  background: #e5e7eb;
  color: #374151;
  letter-spacing: 0.3px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  min-width: 85px;
  text-align: center;
  line-height: 1.4;
  vertical-align: middle;
}

.badge-success {
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.25);
}

.badge-fail {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.25);
}

.badge-unclear {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: white;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.25);
}

.score-badge, .confidence-badge, .quality-badge {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 13px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  letter-spacing: 0.3px;
  min-width: 85px;
  text-align: center;
  line-height: 1.4;
  vertical-align: middle;
}

.score-high, .confidence-high {
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
}

.score-medium, .confidence-medium {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: white;
}

.score-low, .confidence-low {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
}

.confidence-na {
  background: linear-gradient(135deg, #6b7280, #4b5563);
  color: white;
  font-style: italic;
}

/* 品質評分樣式 */
.quality-excellent {
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
}

.quality-good {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
}

.quality-fair {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: white;
}

.quality-poor {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
}

.quality-na {
  background: #9ca3af;
  color: white;
}

/* Confidence Level Badge */
.confidence-level-badge {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 13px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  letter-spacing: 0.3px;
  min-width: 85px;
  text-align: center;
  line-height: 1.4;
  vertical-align: middle;
}

.confidence-level-badge.level-high {
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
}

.confidence-level-badge.level-medium {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: white;
}

.confidence-level-badge.level-low {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
}

.confidence-level-badge.level-unknown {
  background: linear-gradient(135deg, #6b7280, #4b5563);
  color: white;
  font-style: italic;
}

/* ==================== 表單標記樣式 ==================== */
.form-badge {
  display: inline-block;
  padding: 2px 8px;
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
  color: white;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  margin-right: 6px;
  vertical-align: middle;
}

.form-badge-large {
  display: inline-block;
  padding: 4px 12px;
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
  color: white;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  margin-left: 10px;
  vertical-align: middle;
}

/* ==================== 知識 ID 按鈕樣式 ==================== */
.knowledge-ids-section {
  margin-top: 14px;
}

.knowledge-id-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
}

.knowledge-id-btn {
  display: inline-block;
  padding: 8px 16px;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  border-radius: 8px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s ease;
  border: none;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.25);
}

.knowledge-id-btn:hover {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.35);
}

/* ==================== 按鈕 ==================== */
.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #5568d3 0%, #64398f 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
}

.btn-primary:active:not(:disabled) {
  transform: translateY(0);
}

.btn-primary:disabled {
  background: #d1d5db;
  color: #9ca3af;
  cursor: not-allowed;
  opacity: 0.6;
  transform: none;
  box-shadow: none;
}

.btn-secondary {
  background: linear-gradient(to bottom, #f3f4f6, #e5e7eb);
  color: #374151;
  padding: 10px 20px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.btn-secondary:hover:not(:disabled) {
  background: linear-gradient(to bottom, #e5e7eb, #d1d5db);
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.btn-detail, .btn-optimize {
  padding: 7px 14px;
  margin: 2px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.3s ease;
}

.btn-detail {
  background: linear-gradient(135deg, #667eea, #5568d3);
  color: white;
  box-shadow: 0 2px 6px rgba(102, 126, 234, 0.25);
}

.btn-detail:hover {
  background: linear-gradient(135deg, #5568d3, #4451b8);
  transform: translateY(-2px);
  box-shadow: 0 4px 10px rgba(102, 126, 234, 0.35);
}

.btn-optimize {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: white;
  box-shadow: 0 2px 6px rgba(245, 158, 11, 0.25);
}

.btn-optimize:hover {
  background: linear-gradient(135deg, #d97706, #b45309);
  transform: translateY(-2px);
  box-shadow: 0 4px 10px rgba(245, 158, 11, 0.35);
}

/* ==================== 分頁控制 ==================== */
.pagination-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 24px;
  border-top: 2px solid #f3f4f6;
  background: linear-gradient(to top, #fafafa, white);
}

.btn-pagination {
  padding: 10px 20px;
  background: linear-gradient(135deg, #667eea, #5568d3);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.25);
}

.btn-pagination:hover:not(:disabled) {
  background: linear-gradient(135deg, #5568d3, #4451b8);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.35);
}

.btn-pagination:active:not(:disabled) {
  transform: translateY(0);
}

.btn-pagination:disabled {
  background: #d1d5db;
  color: #9ca3af;
  cursor: not-allowed;
  opacity: 0.6;
  transform: none;
  box-shadow: none;
}

.page-info {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.page-size-select {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  background: white;
  cursor: pointer;
  transition: all 0.2s ease;
}

.page-size-select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

/* ==================== 狀態樣式 ==================== */
.loading, .empty-state, .error-state {
  text-align: center;
  padding: 80px 24px;
  color: #6b7280;
}

.empty-state pre {
  background: #f9fafb;
  padding: 18px;
  border-radius: 8px;
  text-align: left;
  display: inline-block;
  margin-top: 18px;
  font-size: 13px;
  border: 1px solid #e5e7eb;
}

/* ==================== Modal ==================== */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeInOverlay 0.3s ease;
}

@keyframes fadeInOverlay {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.modal-content {
  background: white;
  border-radius: 20px;
  padding: 36px;
  max-width: 600px;
  width: 90%;
  max-height: 85vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-content.large {
  max-width: 920px;
}

.modal-content h2 {
  margin-top: 0;
  color: #1f2937;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.detail-content {
  margin: 24px 0;
}

.detail-section {
  margin-bottom: 28px;
  padding-bottom: 24px;
  border-bottom: 2px solid #f3f4f6;
}

.detail-section:last-child {
  border-bottom: none;
}

.detail-section h3 {
  color: #374151;
  font-size: 17px;
  font-weight: 700;
  margin-bottom: 16px;
}

.detail-table {
  width: 100%;
  border-collapse: collapse;
}

.detail-table td {
  padding: 14px 12px;
  border-bottom: 1px solid #f3f4f6;
  vertical-align: middle;
}

.detail-table td:first-child {
  width: 150px;
  font-weight: 600;
  color: #6b7280;
}

.detail-table td:last-child {
  font-weight: 500;
  color: #111827;
}

.question-box, .answer-box {
  background: linear-gradient(to bottom, #f9fafb, #f3f4f6);
  padding: 18px;
  border-radius: 10px;
  margin-bottom: 16px;
  border: 1px solid #e5e7eb;
}

.question-box strong, .answer-box strong {
  display: block;
  margin-bottom: 10px;
  color: #374151;
  font-weight: 700;
}

.question-box p, .answer-box p {
  margin: 0;
  line-height: 1.7;
  color: #1f2937;
}

.optimization-hints {
  background: linear-gradient(135deg, #fffbeb, #fef3c7);
  padding: 24px;
  border-radius: 12px;
  border: 2px solid #fbbf24;
}

.optimization-hints h3 {
  color: #b45309;
  margin-top: 0;
  font-weight: 700;
}

.optimization-hints ul {
  margin: 0;
  padding-left: 24px;
}

.optimization-hints li {
  margin-bottom: 16px;
  line-height: 1.7;
}

.optimization-hints strong {
  color: #b45309;
  display: block;
  margin-bottom: 6px;
  font-weight: 700;
}

.optimization-hints p {
  margin: 6px 0 0 0;
  color: #374151;
  font-size: 14px;
}

.optimization-tips-content {
  background: white;
  padding: 18px;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
}

.optimization-tips-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  font-size: 14px;
  line-height: 1.8;
  color: #1f2937;
}

/* ==================== 知識來源區塊 ==================== */
.knowledge-sources {
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  padding: 24px;
  border-radius: 12px;
  border: 2px solid #3b82f6;
}

.knowledge-sources h3 {
  color: #1e40af;
  margin-top: 0;
  font-weight: 700;
}

.knowledge-info {
  font-size: 14px;
  line-height: 1.8;
}

.knowledge-info p {
  margin: 12px 0;
}

.sources-summary {
  background: white;
  padding: 14px;
  border-radius: 8px;
  color: #1f2937;
  font-size: 13px;
  border: 1px solid #d1d5db;
}

.knowledge-links-box {
  background: white;
  padding: 18px;
  border-radius: 10px;
  margin-top: 16px;
  border: 1px solid #d1d5db;
}

.knowledge-links-box p {
  margin: 0 0 12px 0;
  font-weight: 600;
}

.batch-link {
  display: inline-block;
  padding: 12px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white !important;
  text-decoration: none;
  border-radius: 10px;
  font-weight: 700;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.batch-link:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 18px rgba(102, 126, 234, 0.5);
  background: linear-gradient(135deg, #5568d3 0%, #64398f 100%);
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 2px solid #f3f4f6;
}

.summary-text {
  background: #f9fafb;
  padding: 24px;
  border-radius: 10px;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.7;
  max-height: 60vh;
  overflow-y: auto;
  border: 1px solid #e5e7eb;
}

/* ==================== V2 信心度計算詳情 ==================== */
.confidence-evaluation {
  background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
  padding: 24px;
  border-radius: 12px;
  border: 2px solid #0ea5e9;
}

.confidence-evaluation h3 {
  color: #0c4a6e;
  margin-top: 0;
  font-weight: 700;
  margin-bottom: 20px;
}

.confidence-metrics-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  margin-bottom: 24px;
}

.confidence-metric-item {
  background: white;
  padding: 16px;
  border-radius: 10px;
  border: 1px solid #d1d5db;
  transition: all 0.3s ease;
}

.confidence-metric-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.confidence-metric-item.main {
  border: 2px solid #0ea5e9;
  background: linear-gradient(135deg, #f0f9ff 0%, #fff 100%);
  padding: 20px;
}

.metric-label {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 8px;
  font-weight: 600;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.label-text {
  flex: 1;
}

.label-weight {
  font-size: 11px;
  color: #9ca3af;
  font-weight: 400;
}

.metric-value {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.confidence-metric-item.main .metric-value {
  font-size: 24px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #0ea5e9, #06b6d4);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.progress-fill.warning {
  background: linear-gradient(90deg, #f59e0b, #ef4444);
}

.formula-explanation {
  background: white;
  padding: 16px;
  border-radius: 10px;
  border: 1px solid #d1d5db;
  margin-bottom: 16px;
}

.formula-explanation strong {
  display: block;
  margin-bottom: 10px;
  color: #0c4a6e;
  font-weight: 700;
}

.formula {
  background: #f8fafc;
  padding: 12px;
  border-radius: 6px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #1e40af;
  margin: 0 0 8px 0;
  overflow-x: auto;
  border-left: 3px solid #0ea5e9;
}

.formula-example {
  background: #ecfeff;
  padding: 10px 12px;
  border-radius: 6px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #0e7490;
  margin: 0;
  overflow-x: auto;
  border-left: 3px solid #06b6d4;
  line-height: 1.6;
}

.pass-reason {
  background: white;
  padding: 16px;
  border-radius: 10px;
  border: 1px solid #d1d5db;
}

.pass-reason strong {
  display: block;
  margin-bottom: 8px;
  font-weight: 700;
}

.pass-reason p {
  margin: 0;
  line-height: 1.6;
  color: #374151;
  font-size: 14px;
}

/* ==================== Notification Styles ==================== */
.notification {
  position: fixed;
  top: 90px;
  right: 24px;
  min-width: 320px;
  max-width: 420px;
  padding: 18px 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  z-index: 9999;
  animation: slideInRight 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  transition: opacity 0.3s ease;
  border: 1px solid #e5e7eb;
}

@keyframes slideInRight {
  from {
    transform: translateX(450px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.notification strong {
  display: block;
  margin-bottom: 10px;
  font-size: 15px;
  font-weight: 700;
  color: #1f2937;
}

.notification p {
  margin: 0;
  font-size: 14px;
  color: #374151;
  line-height: 1.6;
}

.notification-info {
  border-left: 5px solid #3b82f6;
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.2);
}

.notification-success {
  border-left: 5px solid #10b981;
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.2);
}

.notification-warning {
  border-left: 5px solid #f59e0b;
  box-shadow: 0 8px 24px rgba(245, 158, 11, 0.2);
}

.notification-error {
  border-left: 5px solid #ef4444;
  box-shadow: 0 8px 24px rgba(239, 68, 68, 0.2);
}
</style>
