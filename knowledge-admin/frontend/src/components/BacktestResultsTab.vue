<template>
  <div class="backtest-results-tab">
    <!-- 空狀態提示 -->
    <div v-if="!loopId" class="empty-state">
      <div class="empty-icon">🎯</div>
      <h3>請選擇迴圈</h3>
      <p>請在頂部的「當前迴圈」選擇器中選擇一個迴圈，以查看回測結果。</p>
    </div>

    <!-- 迴圈資訊卡片 -->
    <div v-else-if="loopInfo" class="loop-info-card">
      <h3>🔄 迴圈資訊</h3>
      <div class="loop-details">
        <div class="loop-detail-item">
          <span class="label">迴圈名稱：</span>
          <span class="value">{{ loopInfo.loop_name }}</span>
        </div>
        <div class="loop-detail-item">
          <span class="label">迴圈 ID：</span>
          <span class="value">#{{ loopInfo.loop_id }}</span>
        </div>
        <div class="loop-detail-item">
          <span class="label">當前迭代：</span>
          <span class="value">第 {{ loopInfo.current_iteration }} 次</span>
        </div>
        <div class="loop-detail-item">
          <span class="label">固定測試集：</span>
          <span class="value">{{ loopInfo.total_scenarios }} 題</span>
        </div>
        <div class="loop-detail-item">
          <span class="label">目標通過率：</span>
          <span class="value">{{ (loopInfo.target_pass_rate * 100).toFixed(0) }}%</span>
        </div>
      </div>
    </div>

    <!-- 迭代輪次選擇器（新功能） -->
    <div v-if="iterationComparison && iterationComparison.length > 0" class="iteration-selector-section">
      <h3>📊 選擇迭代輪次</h3>
      <div class="iteration-tabs">
        <button
          v-for="iter in iterationComparison"
          :key="iter.iteration"
          class="iteration-tab"
          :class="{ 'active': selectedIteration === iter.iteration, 'is-current': iter.is_current }"
          @click="selectIteration(iter.iteration)"
        >
          <span class="tab-label">🔄 第 {{ iter.iteration }} 輪</span>
          <span class="tab-stats">{{ (iter.pass_rate * 100).toFixed(0) }}%</span>
          <span v-if="iter.improvement !== null" class="tab-improvement" :class="getImprovementClass(iter.improvement)">
            {{ iter.improvement > 0 ? '↑' : '↓' }}{{ Math.abs(iter.improvement * 100).toFixed(1) }}%
          </span>
          <span v-if="iter.is_current" class="tab-current-badge">最新</span>
        </button>
        <button
          class="iteration-tab"
          :class="{ 'active': selectedIteration === null }"
          @click="selectIteration(null)"
        >
          <span class="tab-label">📋 全部輪次</span>
        </button>
      </div>

      <!-- 選中迭代的摘要 -->
      <div v-if="selectedIteration !== null" class="selected-iteration-summary">
        <div class="summary-item">
          <span class="summary-label">當前選擇：</span>
          <span class="summary-value">第 {{ selectedIteration }} 輪</span>
        </div>
        <div class="summary-item" v-if="selectedIterationInfo">
          <span class="summary-label">通過率：</span>
          <span class="summary-value" :class="getPassRateClass(selectedIterationInfo.pass_rate * 100)">
            {{ (selectedIterationInfo.pass_rate * 100).toFixed(1) }}%
          </span>
        </div>
        <div class="summary-item" v-if="selectedIterationInfo">
          <span class="summary-label">測試數：</span>
          <span class="summary-value">{{ selectedIterationInfo.passed }}/{{ selectedIterationInfo.total }}</span>
        </div>
        <div class="summary-item" v-if="loopInfo">
          <span class="summary-label">目標：</span>
          <span class="summary-value">{{ (loopInfo.target_pass_rate * 100).toFixed(0) }}%</span>
          <span v-if="selectedIterationInfo" :class="{ 'achieved': selectedIterationInfo.pass_rate >= loopInfo.target_pass_rate }">
            {{ selectedIterationInfo.pass_rate >= loopInfo.target_pass_rate ? '✅' : '⏳' }}
          </span>
        </div>
      </div>
    </div>

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
        <label>📜 該輪次的回測記錄：</label>
        <select v-model="selectedRunId" @change="onRunSelected" class="run-selector" :disabled="filteredBacktestRuns.length === 0">
          <option v-if="filteredBacktestRuns.length === 0" value="" disabled>
            {{ selectedIteration !== null ? `第 ${selectedIteration} 輪尚無回測記錄` : '尚無回測記錄' }}
          </option>
          <option v-for="run in filteredBacktestRuns" :key="run.id" :value="run.id">
            Run #{{ run.id }} - {{ formatRunDate(run.started_at) }}
            ({{ run.executed_scenarios }} 題, 通過率 {{ run.pass_rate }}%)
          </option>
        </select>
        <span v-if="filteredBacktestRuns.length > 0" class="run-count">
          共 {{ filteredBacktestRuns.length }} 次回測
        </span>
      </div>

      <div class="filter-group">
        <label>狀態篩選：</label>
        <select v-model="statusFilter" @change="loadResults">
          <option value="all">全部</option>
          <option value="failed">僅失敗</option>
          <option value="passed">僅通過</option>
        </select>
      </div>
    </div>

    <!-- 載入狀態 -->
    <div v-if="loading" class="loading">
      <p>⏳ 載入中...</p>
    </div>

    <!-- 錯誤訊息 -->
    <div v-else-if="error" class="error-message">
      <p>❌ {{ error }}</p>
    </div>

    <!-- 回測結果表格 -->
    <div v-else-if="results.length > 0" class="results-section">
      <h3>📋 回測結果 (共 {{ total }} 筆)</h3>

      <table class="results-table">
        <thead>
          <tr>
            <th style="width: 60px;">ID</th>
            <th style="width: 80px;">狀態</th>
            <th style="width: 300px;">測試問題</th>
            <th style="width: 150px;">意圖</th>
            <th style="width: 100px;">信心分數</th>
            <th style="width: 100px;">信心等級</th>
            <th style="width: 80px;">來源數</th>
            <th style="width: 120px;">品質評分</th>
            <th style="width: 100px;">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="result in results" :key="result.test_id" :class="{ 'failed-row': !result.passed }">
            <td>{{ result.test_id }}</td>
            <td>
              <span class="status-badge" :class="result.passed ? 'passed' : 'failed'">
                {{ result.passed ? '✅ 通過' : '❌ 失敗' }}
              </span>
            </td>
            <td class="question-cell">{{ result.test_question }}</td>
            <td>{{ result.actual_intent || 'N/A' }}</td>
            <td>{{ formatConfidenceScore(result.confidence_score) }}</td>
            <td>{{ formatConfidenceLevel(result.confidence_level) }}</td>
            <td>{{ result.source_count || 0 }}</td>
            <td>
              <span v-if="result.quality_overall" class="quality-score" :class="getQualityClass(result.quality_overall)">
                {{ formatFloat(result.quality_overall) }}
              </span>
              <span v-else>-</span>
            </td>
            <td>
              <button @click="showDetail(result)" class="btn-detail">詳情</button>
              <button @click="optimizeKnowledge(result)" class="btn-optimize" title="優化知識">🔧</button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 分頁控制 -->
      <div class="pagination">
        <button @click="previousPage" :disabled="pagination.offset === 0">上一頁</button>
        <span>第 {{ currentPage }} 頁</span>
        <button @click="nextPage" :disabled="pagination.offset + pagination.limit >= total">下一頁</button>

        <select v-model.number="pagination.limit" @change="changePageSize" class="page-size-selector">
          <option :value="20">20 筆/頁</option>
          <option :value="50">50 筆/頁</option>
          <option :value="100">100 筆/頁</option>
        </select>
      </div>
    </div>

    <!-- 無結果提示 -->
    <div v-else class="no-results">
      <p>📭 目前沒有回測結果</p>
    </div>

    <!-- 詳情 Modal -->
    <div v-if="showDetailModal" class="modal-overlay" @click.self="closeDetailModal">
      <div class="modal-content detail-modal">
        <div class="modal-header">
          <h3>📝 回測詳情 - Test #{{ selectedResult.test_id }}</h3>
          <button @click="closeDetailModal" class="btn-close">✕</button>
        </div>
        <div class="modal-body">
          <div class="detail-section">
            <h4>測試資訊</h4>
            <div class="detail-row">
              <span class="detail-label">測試問題：</span>
              <span class="detail-value">{{ selectedResult.test_question }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">預期意圖：</span>
              <span class="detail-value">{{ selectedResult.expected_intent || 'N/A' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">實際意圖：</span>
              <span class="detail-value">{{ selectedResult.actual_intent || 'N/A' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">測試時間：</span>
              <span class="detail-value">{{ formatRunDate(selectedResult.timestamp) }}</span>
            </div>
          </div>

          <div class="detail-section">
            <h4>系統回應</h4>
            <div class="detail-row">
              <span class="detail-label">回應內容：</span>
              <pre class="detail-value response-text">{{ selectedResult.actual_response || 'N/A' }}</pre>
            </div>
            <div class="detail-row">
              <span class="detail-label">信心分數：</span>
              <span class="detail-value">{{ formatConfidenceScore(selectedResult.confidence_score) }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">信心等級：</span>
              <span class="detail-value">{{ formatConfidenceLevel(selectedResult.confidence_level) }}</span>
            </div>
          </div>

          <div v-if="selectedResult.quality_overall" class="detail-section">
            <h4>品質評估</h4>
            <div class="detail-row">
              <span class="detail-label">相關性：</span>
              <span class="detail-value">{{ formatFloat(selectedResult.relevance) }} / 10.0</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">完整性：</span>
              <span class="detail-value">{{ formatFloat(selectedResult.completeness) }} / 10.0</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">準確性：</span>
              <span class="detail-value">{{ formatFloat(selectedResult.accuracy) }} / 10.0</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">意圖匹配：</span>
              <span class="detail-value">{{ formatFloat(selectedResult.intent_match) }} / 10.0</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">綜合評分：</span>
              <span class="detail-value">{{ formatFloat(selectedResult.quality_overall) }} / 10.0</span>
            </div>
          </div>

          <div class="detail-section">
            <h4>知識來源</h4>
            <div class="detail-row">
              <span class="detail-label">來源數量：</span>
              <span class="detail-value">{{ selectedResult.source_count || 0 }}</span>
            </div>
            <div v-if="selectedResult.source_ids" class="detail-row">
              <span class="detail-label">來源 ID：</span>
              <span class="detail-value">{{ selectedResult.source_ids }}</span>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="optimizeKnowledge(selectedResult)" class="btn-primary">🔧 優化知識</button>
          <button @click="closeDetailModal" class="btn-secondary">關閉</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { API_ENDPOINTS } from '@/config/api';

const API_BASE = '/api';

export default {
  name: 'BacktestResultsTab',

  props: {
    // 迴圈 ID（可選，如果提供則顯示迴圈資訊）
    loopId: {
      type: Number,
      default: null
    }
  },

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
      backtestRuns: [],
      selectedRunId: null,
      // 迴圈相關資料（新增）
      loopInfo: null,
      iterationComparison: [],
      // 迭代輪次選擇
      selectedIteration: null  // null 表示全部，數字表示特定輪次
    };
  },

  computed: {
    currentPage() {
      return Math.floor(this.pagination.offset / this.pagination.limit) + 1;
    },

    // 根據選中的迭代過濾回測記錄
    filteredBacktestRuns() {
      if (this.selectedIteration === null) {
        // 顯示全部
        return this.backtestRuns;
      }
      // 只顯示選中迭代的記錄
      return this.backtestRuns.filter(run => run.iteration === this.selectedIteration);
    },

    // 選中迭代的詳細資訊
    selectedIterationInfo() {
      if (this.selectedIteration === null || !this.iterationComparison) {
        return null;
      }
      return this.iterationComparison.find(iter => iter.iteration === this.selectedIteration);
    }
  },

  watch: {
    // 監聽父組件傳入的 loopId prop 變化
    loopId: {
      immediate: true,  // 立即執行，包含初始值
      async handler(newLoopId, oldLoopId) {
        if (newLoopId && newLoopId !== oldLoopId) {
          // 清空當前數據
          this.loopInfo = null;
          this.iterationComparison = [];
          this.backtestRuns = [];
          this.selectedRunId = null;
          this.results = [];
          this.statistics = null;

          // 不要重置 selectedIteration，保留從 URL 讀取的值
          // this.selectedIteration = null;

          // 載入新迴圈的數據
          await this.loadLoopData();
          await this.loadBacktestRuns();

          // 如果有從 URL 載入的 iteration，自動選中對應的 run
          if (this.selectedIteration !== null && this.filteredBacktestRuns.length === 1) {
            this.selectedRunId = this.filteredBacktestRuns[0].id;
            this.loadResults();
          }
          // 否則自動選擇第一個 run
          else if (this.selectedIteration === null && this.backtestRuns.length > 0) {
            this.selectedRunId = this.backtestRuns[0].id;
            this.loadResults();
          }
        }
      }
    }
  },

  mounted() {
    // 從 URL 參數讀取 iteration
    const iterationParam = this.$route.query.iteration;
    if (iterationParam) {
      this.selectedIteration = parseInt(iterationParam, 10);
    }

    // watch 會自動處理 loopId 的初始值和變化
    // 不需要在這裡重複載入
  },

  methods: {
    async loadLoopData() {
      if (!this.loopId) return;

      await this.loadLoopInfo();
      await this.loadIterationComparison();
    },

    async loadBacktestRuns() {
      try {
        if (!this.loopId) {
          this.backtestRuns = [];
          return;
        }

        // 使用 iterationComparison 中的數據構建 backtestRuns
        // 每個 iteration 對應一個 run
        this.backtestRuns = this.iterationComparison.map(iter => ({
          id: iter.run_id,
          iteration: iter.iteration,
          started_at: iter.started_at,
          completed_at: iter.completed_at,
          executed_scenarios: iter.total,
          pass_rate: (iter.pass_rate * 100).toFixed(1),
          passed_count: iter.passed,
          failed_count: iter.total - iter.passed
        }));

      } catch (error) {
        console.error('載入歷史記錄失敗', error);
      }
    },

    selectIteration(iteration) {
      this.selectedIteration = iteration;
      // 清空當前選中的 run，讓用戶重新選擇
      this.selectedRunId = null;
      this.results = [];
      this.statistics = null;

      // 更新 URL 參數，保留選中的 iteration
      const query = { ...this.$route.query };
      if (iteration !== null) {
        query.iteration = iteration;
      } else {
        delete query.iteration;
      }
      this.$router.replace({ query });

      // 如果過濾後只有一個 run，自動選中
      if (this.filteredBacktestRuns.length === 1) {
        this.selectedRunId = this.filteredBacktestRuns[0].id;
        this.loadResults();
      }
    },

    async loadLoopInfo() {
      try {
        const response = await axios.get(API_ENDPOINTS.loopById(this.loopId));
        this.loopInfo = {
          loop_id: response.data.loop_id,
          loop_name: response.data.loop_name,
          current_iteration: response.data.current_iteration,
          total_scenarios: response.data.total_scenarios,
          target_pass_rate: response.data.target_pass_rate
        };
      } catch (error) {
        console.error('載入迴圈資訊失敗', error);
      }
    },

    async loadIterationComparison() {
      try {
        // 獲取該迴圈的所有迭代回測結果
        const response = await axios.get(API_ENDPOINTS.loopIterations(this.loopId));
        const iterations = response.data || [];

        // 計算改善幅度
        this.iterationComparison = iterations.map((iter, index) => {
          const improvement = index > 0
            ? iter.pass_rate - iterations[index - 1].pass_rate
            : null;

          return {
            iteration: iter.iteration,
            pass_rate: iter.pass_rate,
            passed: iter.passed,
            total: iter.total,
            improvement: improvement,
            is_current: iter.iteration === this.loopInfo?.current_iteration,
            run_id: iter.run_id,
            started_at: iter.started_at,
            completed_at: iter.completed_at
          };
        });
      } catch (error) {
        console.error('載入迭代對比失敗', error);
        this.iterationComparison = [];
      }
    },

    onRunSelected() {
      this.pagination.offset = 0;
      this.loadResults();
    },

    async loadResults() {
      this.loading = true;
      this.error = null;

      try {
        if (!this.loopId) {
          this.error = '請在頂部選擇一個迴圈';
          this.loading = false;
          return;
        }

        if (!this.selectedRunId) {
          this.error = '請選擇一個回測記錄';
          this.loading = false;
          return;
        }

        // 找到對應的 iteration
        const selectedRun = this.backtestRuns.find(run => run.id === this.selectedRunId);
        if (!selectedRun) {
          this.error = '找不到對應的回測記錄';
          this.loading = false;
          return;
        }

        const iteration = selectedRun.iteration;

        const params = {
          limit: this.pagination.limit,
          offset: this.pagination.offset
        };

        // 使用新的迴圈回測 API
        const response = await axios.get(
          API_ENDPOINTS.loopIterationResults(this.loopId, iteration),
          { params }
        );

        this.results = response.data.results || [];
        this.total = response.data.total || 0;
        this.statistics = response.data.summary ? {
          total_tests: response.data.summary.total,
          passed_tests: response.data.summary.passed,
          failed_tests: response.data.summary.failed,
          pass_rate: (response.data.summary.pass_rate * 100).toFixed(1),
          avg_score: response.data.summary.avg_score?.toFixed(2) || 'N/A'
        } : null;

        // 將 API 回傳的欄位映射到前端需要的格式
        this.results = this.results.map(result => ({
          test_id: result.id,
          test_question: result.test_question,
          actual_intent: result.actual_intent,
          expected_intent: result.expected_category,
          actual_response: result.system_answer,
          confidence_score: result.confidence_score,  // 使用 RAG 檢索信心度，而非意圖分類信心度
          confidence_level: result.confidence_level,  // 使用 API 計算的信心度等級
          source_count: result.source_count,
          passed: result.passed,
          timestamp: result.tested_at,
          // 品質評分欄位
          relevance: result.relevance,
          completeness: result.completeness,
          accuracy: result.accuracy,
          intent_match: null, // API 目前沒有這個欄位
          quality_overall: result.overall_score,
          // 其他欄位
          source_ids: null // API 目前沒有這個欄位
        }));

      } catch (error) {
        console.error('載入回測結果失敗', error);
        if (error.response?.status === 404) {
          this.error = `找不到迴圈 ${this.loopId} 的回測記錄`;
        } else {
          this.error = '載入失敗：' + (error.response?.data?.detail || error.message);
        }
      } finally {
        this.loading = false;
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

    optimizeKnowledge(result) {
      this.showDetailModal = false;

      const hasSource = result.source_ids && result.source_ids.trim();
      const sourceCount = result.source_count || 0;
      const relevance = result.relevance || 0;
      const completeness = result.completeness || 0;
      const question = result.test_question;
      const intent = result.actual_intent;

      let queryParams = {};
      let notificationMessage = '';

      // 智能判斷：無知識 OR 相關性很低 OR 完整性不足 → 新增知識
      if (!hasSource || relevance < 5.0 || completeness < 5.0) {
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
          notificationMessage = `回應不完整（完整性 ${completeness.toFixed(1)}/10.0），建議新增完整知識`;
        }
      } else {
        // 類型 B：知識相關但品質不佳 → 引導修改
        queryParams = {
          action: 'edit',
          source_ids: result.source_ids,
          question: question,
          intent: intent,
          actual_response: result.actual_response
        };
        notificationMessage = `檢索到 ${sourceCount} 個知識來源，將為您優化現有知識`;
      }

      // 使用 Vue Router 跳轉
      this.$router.push({
        path: '/knowledge',
        query: queryParams
      });

      // 延遲顯示通知，確保路由跳轉完成
      setTimeout(() => {
        alert(`🔧 ${notificationMessage}`);
      }, 300);
    },

    getQualityRating(score) {
      if (score >= 8.0) return '🎉 優秀';
      if (score >= 7.0) return '✅ 良好';
      if (score >= 6.0) return '⚠️ 中等';
      return '❌ 需改善';
    },

    getQualityClass(score) {
      if (score >= 8.0) return 'excellent';
      if (score >= 7.0) return 'good';
      if (score >= 6.0) return 'medium';
      return 'poor';
    },

    getPassRateClass(rate) {
      if (rate >= 85) return 'excellent';
      if (rate >= 70) return 'good';
      if (rate >= 50) return 'moderate';
      return 'poor';
    },

    getImprovementClass(improvement) {
      if (improvement > 0.05) return 'great';   // 改善超過 5%
      if (improvement > 0) return 'positive';   // 有改善
      if (improvement < 0) return 'negative';   // 退步
      return 'neutral';                         // 持平
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
      return num.toFixed(2);
    },

    getConfidenceLevelFromScore(score) {
      if (score === null || score === undefined) return 'low';
      const num = Number(score);
      if (isNaN(num)) return 'low';
      if (num >= 0.8) return 'high';
      if (num >= 0.5) return 'medium';
      return 'low';
    },

    getStatusLabel(status) {
      const statusMap = {
        'draft': '草稿',
        'ready': '就緒',
        'running': '執行中',
        'reviewing': '審核中',
        'completed': '已完成',
        'failed': '失敗',
        'paused': '暫停'
      };
      return statusMap[status] || status;
    }
  }
};
</script>

<style scoped>
.backtest-results-tab {
  padding: 20px;
}

/* 迴圈資訊卡片樣式 */
.loop-info-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 10px;
  margin-bottom: 20px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.loop-info-card h3 {
  margin: 0 0 15px 0;
  font-size: 18px;
}

.loop-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.loop-detail-item {
  display: flex;
  align-items: center;
}

.loop-detail-item .label {
  font-weight: 600;
  margin-right: 8px;
}

.loop-detail-item .value {
  font-size: 16px;
}

/* 迭代對比區塊樣式 */
/* 迭代選擇器區塊 */
.iteration-selector-section {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.iteration-selector-section h3 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #333;
}

.iteration-tabs {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 15px;
}

.iteration-tab {
  background: white;
  border: 2px solid #e0e0e0;
  padding: 10px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 120px;
}

.iteration-tab:hover {
  border-color: #2196F3;
  background: #f0f7ff;
}

.iteration-tab.active {
  background: #2196F3;
  border-color: #2196F3;
  color: white;
}

.iteration-tab.active .tab-label,
.iteration-tab.active .tab-stats,
.iteration-tab.active .tab-improvement {
  color: white;
}

.iteration-tab.is-current:not(.active) {
  border-color: #4CAF50;
  background: #f1f8f4;
}

.tab-label {
  font-weight: 600;
  font-size: 14px;
  color: #333;
}

.tab-stats {
  font-size: 16px;
  font-weight: 700;
  color: #2196F3;
}

.tab-improvement {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  background: #e0e0e0;
  color: #666;
  align-self: flex-start;
}

.tab-improvement.great {
  background: #4CAF50;
  color: white;
}

.tab-improvement.positive {
  background: #8BC34A;
  color: white;
}

.tab-improvement.negative {
  background: #F44336;
  color: white;
}

.tab-current-badge {
  font-size: 10px;
  background: #4CAF50;
  color: white;
  padding: 2px 6px;
  border-radius: 8px;
  align-self: flex-start;
  margin-top: 4px;
}

.selected-iteration-summary {
  background: white;
  padding: 12px 16px;
  border-radius: 6px;
  border-left: 4px solid #2196F3;
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.summary-item {
  display: flex;
  gap: 6px;
  align-items: center;
}

.summary-label {
  font-weight: 600;
  color: #666;
  font-size: 14px;
}

.summary-value {
  font-weight: 700;
  color: #333;
  font-size: 14px;
}

.summary-value.excellent { color: #4CAF50; }
.summary-value.good { color: #8BC34A; }
.summary-value.moderate { color: #FF9800; }
.summary-value.poor { color: #F44336; }

.summary-item .achieved {
  color: #4CAF50;
  font-weight: 700;
}

.run-count {
  margin-left: 10px;
  color: #666;
  font-size: 13px;
  font-style: italic;
}

/* 舊的 iteration-comparison 樣式保留以防萬一 */
.iteration-comparison {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.iteration-comparison h3 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #333;
}

.comparison-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.comparison-item {
  background: white;
  padding: 12px 16px;
  border-radius: 6px;
  border-left: 4px solid #e0e0e0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.comparison-item.current {
  border-left-color: #667eea;
  background: #f0f4ff;
}

.iteration-label {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.badge-current {
  background: #667eea;
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
}

.iteration-stats {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pass-rate {
  font-weight: 600;
  color: #333;
}

.pass-count {
  color: #666;
  font-size: 14px;
}

.improvement {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
}

.improvement.great {
  background-color: #4CAF50;
  color: white;
}

.improvement.positive {
  background-color: #8BC34A;
  color: white;
}

.improvement.negative {
  background-color: #F44336;
  color: white;
}

.improvement.neutral {
  background-color: #e0e0e0;
  color: #666;
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
  animation: pulse-iteration 2s infinite;
}

@keyframes pulse-iteration {
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

.target-gap {
  background: white;
  padding: 12px 16px;
  border-radius: 6px;
  border: 2px dashed #ffc107;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}

.target-gap .label {
  font-weight: 600;
  color: #333;
}

.target-gap .value {
  font-weight: 600;
  color: #ffc107;
  font-size: 16px;
}

.target-gap .gap {
  color: #666;
  font-size: 14px;
}

.target-gap .gap.achieved {
  color: #28a745;
  font-weight: 600;
}

/* 統計卡片樣式 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 15px;
  margin-bottom: 25px;
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  text-align: center;
}

.stat-card.success {
  border-left: 4px solid #28a745;
}

.stat-card.fail {
  border-left: 4px solid #dc3545;
}

.stat-card.rate {
  border-left: 4px solid #17a2b8;
}

.stat-card.score {
  border-left: 4px solid #ffc107;
}

.stat-card.quality {
  border-left: 4px solid #6f42c1;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #333;
}

.stat-rating {
  font-size: 13px;
  margin-top: 5px;
  color: #666;
}

/* 品質統計區塊 */
.quality-stats-section {
  margin-bottom: 25px;
}

.section-title {
  font-size: 16px;
  margin-bottom: 15px;
  color: #333;
}

/* 工具列樣式 */
.toolbar {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-group label {
  font-weight: 600;
  font-size: 14px;
}

.filter-group select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.run-selector {
  min-width: 400px;
}

/* 回測結果表格樣式 */
.results-section h3 {
  margin-bottom: 15px;
  font-size: 16px;
}

.results-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 20px;
}

.results-table th {
  background: #f8f9fa;
  padding: 12px;
  text-align: left;
  font-weight: 600;
  border-bottom: 2px solid #dee2e6;
  font-size: 14px;
}

.results-table td {
  padding: 12px;
  border-bottom: 1px solid #dee2e6;
  font-size: 13px;
}

.results-table tr:hover {
  background: #f8f9fa;
}

.failed-row {
  background: #fff5f5;
}

.question-cell {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.status-badge.passed {
  background: #d4edda;
  color: #155724;
}

.status-badge.failed {
  background: #f8d7da;
  color: #721c24;
}

.quality-score {
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.quality-score.excellent {
  background: #d4edda;
  color: #155724;
}

.quality-score.good {
  background: #d1ecf1;
  color: #0c5460;
}

.quality-score.medium {
  background: #fff3cd;
  color: #856404;
}

.quality-score.poor {
  background: #f8d7da;
  color: #721c24;
}

.btn-detail {
  padding: 4px 12px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  margin-right: 5px;
}

.btn-detail:hover {
  background: #0056b3;
}

.btn-optimize {
  padding: 4px 8px;
  background: #ffc107;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-optimize:hover {
  background: #e0a800;
}

/* 分頁控制 */
.pagination {
  display: flex;
  align-items: center;
  gap: 15px;
  justify-content: center;
  margin-top: 20px;
}

.pagination button {
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.pagination button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.pagination button:hover:not(:disabled) {
  background: #0056b3;
}

.page-size-selector {
  padding: 6px 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

/* 載入與錯誤狀態 */
.loading, .error-message, .no-results {
  text-align: center;
  padding: 40px;
  font-size: 16px;
  color: #666;
}

.error-message {
  color: #dc3545;
}

/* Modal 樣式 */
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
  border-radius: 8px;
  max-width: 800px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #dee2e6;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
}

.btn-close:hover {
  color: #000;
}

.modal-body {
  padding: 20px;
}

.detail-section {
  margin-bottom: 25px;
}

.detail-section h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #333;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 8px;
}

.detail-row {
  display: flex;
  margin-bottom: 10px;
  gap: 10px;
}

.detail-label {
  font-weight: 600;
  min-width: 120px;
  color: #666;
}

.detail-value {
  flex: 1;
  color: #333;
}

.response-text {
  white-space: pre-wrap;
  background: #f8f9fa;
  padding: 10px;
  border-radius: 4px;
  font-family: inherit;
  margin: 0;
}

.modal-footer {
  padding: 15px 20px;
  border-top: 1px solid #dee2e6;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn-primary {
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-primary:hover {
  background: #0056b3;
}

.btn-secondary {
  padding: 8px 16px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-secondary:hover {
  background: #545b62;
}
</style>
