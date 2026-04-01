<template>
  <div class="loop-management-tab">
    <h3>🔄 知識完善迴圈管理</h3>

    <!-- 工具列 -->
    <div class="toolbar">
      <button @click="refreshLoops" class="btn btn-refresh" :disabled="loading">
        🔄 {{ loading ? '載入中...' : '重新整理' }}
      </button>
      <button @click="showCreateLoopModal" class="btn btn-primary">
        ➕ 新增迴圈
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
            <td class="loop-name">{{ loop.loop_name }}</td>
            <td>{{ getVendorName(loop.vendor_id) }}</td>
            <td>
              <span class="status-badge" :class="`status-${loop.status.toLowerCase()}`">
                {{ getStatusLabel(loop.status) }}
              </span>
            </td>
            <td>{{ loop.current_iteration }} / {{ loop.max_iterations }}</td>
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
              <button
                v-if="canExecuteIteration(loop)"
                @click="executeIteration(loop)"
                class="btn-action btn-execute"
                title="執行迭代"
              >
                ▶️
              </button>
              <button
                v-if="canPause(loop)"
                @click="pauseLoop(loop)"
                class="btn-action btn-pause"
                title="暫停"
              >
                ⏸️
              </button>
              <button
                v-if="canResume(loop)"
                @click="resumeLoop(loop)"
                class="btn-action btn-resume"
                title="恢復"
              >
                ▶️
              </button>
              <button
                v-if="canCancel(loop)"
                @click="cancelLoop(loop)"
                class="btn-action btn-cancel"
                title="取消"
              >
                🚫
              </button>
              <button
                v-if="canCompleteBatch(loop)"
                @click="completeBatch(loop)"
                class="btn-action btn-complete"
                title="完成批次"
              >
                ✅
              </button>
              <button
                v-if="canStartNextBatch(loop)"
                @click="showStartNextBatchModal(loop)"
                class="btn-action btn-next-batch"
                title="啟動下一批次"
              >
                ➡️
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 空狀態 -->
    <div v-else class="empty-state">
      <p>尚無迴圈記錄</p>
      <button @click="showCreateLoopModal" class="btn btn-primary">建立第一個迴圈</button>
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
                  <span>{{ selectedLoop.current_iteration }} / {{ selectedLoop.max_iterations }}</span>
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

    <!-- 啟動新迴圈 Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>🚀 啟動新迴圈</h3>
          <button class="close-btn" @click="closeModal">✕</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="submitLoop" class="loop-form">
            <!-- 迴圈名稱 -->
            <div class="form-group">
              <label for="loop-name">迴圈名稱 <span class="required">*</span></label>
              <input
                id="loop-name"
                v-model="formData.loop_name"
                type="text"
                placeholder="例：第2批-包租業知識完善"
                required
                maxlength="200"
              />
              <span v-if="validationErrors.loop_name" class="error-text">{{ validationErrors.loop_name }}</span>
            </div>

            <!-- 業者選擇 -->
            <div class="form-group">
              <label for="vendor-id">業者 ID <span class="required">*</span></label>
              <select id="vendor-id" v-model="formData.vendor_id" required>
                <option value="" disabled>請選擇業者</option>
                <option :value="1">心巢房屋股份有限公司</option>
                <option :value="2">富喬物業管理顧問股份有限公司</option>
                <option :value="3">愛租屋資產管理</option>
              </select>
            </div>

            <!-- 批量大小 -->
            <div class="form-group">
              <label for="batch-size">批量大小 <span class="required">*</span></label>
              <select id="batch-size" v-model.number="formData.batch_size" required>
                <option :value="20">20 題（快速測試）</option>
                <option :value="50">50 題（標準）</option>
                <option :value="100">100 題（完整）</option>
                <option :value="200">200 題（大規模）</option>
              </select>
              <span class="help-text">選取的測試情境數量</span>
            </div>

            <!-- 最大迭代次數 -->
            <div class="form-group">
              <label for="max-iterations">最大迭代次數 <span class="required">*</span></label>
              <select id="max-iterations" v-model.number="formData.max_iterations" required>
                <option :value="5">5 次（快速）</option>
                <option :value="10">10 次（標準）</option>
                <option :value="20">20 次（深度）</option>
              </select>
            </div>

            <!-- 目標通過率 -->
            <div class="form-group">
              <label for="target-pass-rate">目標通過率 <span class="required">*</span></label>
              <select id="target-pass-rate" v-model.number="formData.target_pass_rate" required>
                <option :value="0.80">80%</option>
                <option :value="0.85">85%（建議）</option>
                <option :value="0.90">90%</option>
                <option :value="0.95">95%</option>
              </select>
            </div>

            <!-- 難度分布預覽 -->
            <div class="form-group">
              <label>難度分布（分層隨機抽樣）</label>
              <div class="difficulty-preview">
                <div class="difficulty-item">
                  <span class="difficulty-label easy">簡單</span>
                  <span class="difficulty-value">20% ({{ Math.round(formData.batch_size * 0.2) }} 題)</span>
                </div>
                <div class="difficulty-item">
                  <span class="difficulty-label medium">中等</span>
                  <span class="difficulty-value">50% ({{ Math.round(formData.batch_size * 0.5) }} 題)</span>
                </div>
                <div class="difficulty-item">
                  <span class="difficulty-label hard">困難</span>
                  <span class="difficulty-value">30% ({{ Math.round(formData.batch_size * 0.3) }} 題)</span>
                </div>
              </div>
            </div>

            <!-- 父迴圈選擇（可選） -->
            <div class="form-group">
              <label for="parent-loop">父迴圈 ID（可選）</label>
              <select id="parent-loop" v-model.number="formData.parent_loop_id">
                <option :value="null">無（第一批）</option>
                <option v-for="loop in completedLoops" :key="loop.loop_id" :value="loop.loop_id">
                  #{{ loop.loop_id }} - {{ loop.loop_name }} ({{ loop.total_scenarios }} 題已使用)
                </option>
              </select>
              <span class="help-text">選擇父迴圈可避免重複選取測試情境</span>
            </div>

            <!-- 預算上限（可選） -->
            <div class="form-group">
              <label for="budget-limit">預算上限（USD，可選）</label>
              <input
                id="budget-limit"
                v-model.number="formData.budget_limit_usd"
                type="number"
                min="0"
                step="0.01"
                placeholder="例：50.00"
              />
              <span class="help-text">留空表示無限制</span>
            </div>

            <!-- 表單操作按鈕 -->
            <div class="form-actions">
              <button type="button" class="btn btn-secondary" @click="closeModal">取消</button>
              <button type="submit" class="btn btn-primary" :disabled="submitting">
                {{ submitting ? '啟動中...' : '啟動迴圈' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- 啟動下一批次 Modal -->
    <div v-if="showNextBatchModal" class="modal-overlay" @click.self="closeNextBatchModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>➡️ 啟動下一批次</h3>
          <button class="close-btn" @click="closeNextBatchModal">✕</button>
        </div>
        <div class="modal-body">
          <!-- 父迴圈資訊 -->
          <div class="parent-loop-info">
            <h4>📦 父迴圈資訊</h4>
            <div class="info-grid">
              <div class="info-item">
                <label>父迴圈 ID：</label>
                <span>#{{ nextBatchParentLoop?.loop_id }}</span>
              </div>
              <div class="info-item">
                <label>父迴圈名稱：</label>
                <span>{{ nextBatchParentLoop?.loop_name }}</span>
              </div>
              <div class="info-item">
                <label>狀態：</label>
                <span class="status-badge status-completed">已完成</span>
              </div>
              <div class="info-item">
                <label>已使用測試集：</label>
                <span class="highlight">{{ nextBatchParentLoop?.total_scenarios }} 題</span>
              </div>
            </div>
            <div class="info-note">
              📊 系統將自動排除父迴圈的 {{ nextBatchParentLoop?.total_scenarios }} 題，從剩餘題庫中選取新的測試集
            </div>
          </div>

          <!-- 新迴圈設定表單 -->
          <form @submit.prevent="submitNextBatch" class="loop-form">
            <!-- 迴圈名稱 -->
            <div class="form-group">
              <label for="next-loop-name">新迴圈名稱 <span class="required">*</span></label>
              <input
                id="next-loop-name"
                v-model="nextBatchFormData.loop_name"
                type="text"
                placeholder="例：第2批-包租業知識完善"
                required
                maxlength="200"
              />
            </div>

            <!-- 批量大小 -->
            <div class="form-group">
              <label for="next-batch-size">批量大小 <span class="required">*</span></label>
              <select id="next-batch-size" v-model.number="nextBatchFormData.batch_size" required>
                <option :value="20">20 題（快速測試）</option>
                <option :value="50">50 題（標準）</option>
                <option :value="100">100 題（完整）</option>
                <option :value="200">200 題（大規模）</option>
              </select>
            </div>

            <!-- 最大迭代次數 -->
            <div class="form-group">
              <label for="next-max-iterations">最大迭代次數 <span class="required">*</span></label>
              <select id="next-max-iterations" v-model.number="nextBatchFormData.max_iterations" required>
                <option :value="5">5 次（快速）</option>
                <option :value="10">10 次（標準）</option>
                <option :value="20">20 次（深度）</option>
              </select>
            </div>

            <!-- 目標通過率 -->
            <div class="form-group">
              <label for="next-target-pass-rate">目標通過率 <span class="required">*</span></label>
              <select id="next-target-pass-rate" v-model.number="nextBatchFormData.target_pass_rate" required>
                <option :value="0.80">80%</option>
                <option :value="0.85">85%（建議）</option>
                <option :value="0.90">90%</option>
                <option :value="0.95">95%</option>
              </select>
            </div>

            <!-- 難度分布預覽 -->
            <div class="form-group">
              <label>難度分布（分層隨機抽樣）</label>
              <div class="difficulty-preview">
                <div class="difficulty-item">
                  <span class="difficulty-label easy">簡單</span>
                  <span class="difficulty-value">20% ({{ Math.round(nextBatchFormData.batch_size * 0.2) }} 題)</span>
                </div>
                <div class="difficulty-item">
                  <span class="difficulty-label medium">中等</span>
                  <span class="difficulty-value">50% ({{ Math.round(nextBatchFormData.batch_size * 0.5) }} 題)</span>
                </div>
                <div class="difficulty-item">
                  <span class="difficulty-label hard">困難</span>
                  <span class="difficulty-value">30% ({{ Math.round(nextBatchFormData.batch_size * 0.3) }} 題)</span>
                </div>
              </div>
            </div>

            <!-- 表單操作按鈕 -->
            <div class="form-actions">
              <button type="button" class="btn btn-secondary" @click="closeNextBatchModal">取消</button>
              <button type="submit" class="btn btn-primary" :disabled="submitting">
                {{ submitting ? '啟動中...' : '啟動下一批次' }}
              </button>
            </div>
          </form>
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
      pollingTimer: null,
      pollingInterval: 30000, // 30 seconds (減少頻率)
      showModal: false,
      submitting: false,
      formData: {
        loop_name: '',
        vendor_id: '',
        batch_size: 50,
        max_iterations: 10,
        target_pass_rate: 0.85,
        parent_loop_id: null,
        budget_limit_usd: null,
        scenario_filters: {}
      },
      validationErrors: {},
      // 查看詳情相關
      showDetailsModal: false,
      loadingDetails: false,
      selectedLoop: null,
      iterationHistory: [],
      trendChartInstance: null,
      // 啟動下一批次相關
      showNextBatchModal: false,
      nextBatchParentLoop: null,
      nextBatchFormData: {
        loop_name: '',
        batch_size: 50,
        max_iterations: 10,
        target_pass_rate: 0.85
      }
    };
  },
  computed: {
    hasRunningLoops() {
      return this.loops.some(loop => this.isRunningStatus(loop.status));
    },
    completedLoops() {
      return this.loops.filter(loop => loop.status.toLowerCase() === 'completed');
    },
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
    // 停用自動輪詢，避免不必要的重新整理
    // this.startPolling();
  },
  beforeUnmount() {
    this.stopPolling();
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
    },
    startPolling() {
      // 只有在有 RUNNING 狀態的迴圈時才輪詢
      this.pollingTimer = setInterval(() => {
        if (this.hasRunningLoops) {
          this.loadLoops();
        }
      }, this.pollingInterval);
    },
    stopPolling() {
      if (this.pollingTimer) {
        clearInterval(this.pollingTimer);
        this.pollingTimer = null;
      }
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
    // 操作權限判斷
    canExecuteIteration(loop) {
      return ['pending', 'running', 'reviewing'].includes(loop.status.toLowerCase());
    },
    canPause(loop) {
      return this.isRunningStatus(loop.status);
    },
    canResume(loop) {
      return loop.status.toLowerCase() === 'paused';
    },
    canCancel(loop) {
      return !['completed', 'cancelled', 'terminated', 'failed'].includes(loop.status.toLowerCase());
    },
    canCompleteBatch(loop) {
      return loop.status.toLowerCase() === 'reviewing';
    },
    canStartNextBatch(loop) {
      return loop.status.toLowerCase() === 'completed';
    },
    // Modal 控制
    showCreateLoopModal() {
      this.resetForm();
      this.showModal = true;
    },
    closeModal() {
      this.showModal = false;
      this.resetForm();
    },
    resetForm() {
      this.formData = {
        loop_name: '',
        vendor_id: '',
        batch_size: 50,
        max_iterations: 10,
        target_pass_rate: 0.85,
        parent_loop_id: null,
        budget_limit_usd: null,
        scenario_filters: {}
      };
      this.validationErrors = {};
    },
    // 表單驗證
    validateForm() {
      this.validationErrors = {};
      let isValid = true;

      // 迴圈名稱驗證
      if (!this.formData.loop_name || this.formData.loop_name.trim().length === 0) {
        this.validationErrors.loop_name = '迴圈名稱不能為空';
        isValid = false;
      } else if (this.formData.loop_name.length > 200) {
        this.validationErrors.loop_name = '迴圈名稱不能超過 200 字元';
        isValid = false;
      }

      // 業者 ID 驗證
      if (!this.formData.vendor_id) {
        this.validationErrors.vendor_id = '請選擇業者';
        isValid = false;
      }

      // 批量大小驗證
      if (this.formData.batch_size < 1 || this.formData.batch_size > 3000) {
        this.validationErrors.batch_size = '批量大小必須在 1-3000 之間';
        isValid = false;
      }

      // 最大迭代次數驗證
      if (this.formData.max_iterations < 1 || this.formData.max_iterations > 50) {
        this.validationErrors.max_iterations = '最大迭代次數必須在 1-50 之間';
        isValid = false;
      }

      // 目標通過率驗證
      if (this.formData.target_pass_rate < 0 || this.formData.target_pass_rate > 1) {
        this.validationErrors.target_pass_rate = '目標通過率必須在 0-1 之間';
        isValid = false;
      }

      // 預算上限驗證（可選）
      if (this.formData.budget_limit_usd !== null && this.formData.budget_limit_usd < 0) {
        this.validationErrors.budget_limit_usd = '預算上限不能為負數';
        isValid = false;
      }

      return isValid;
    },
    // 提交表單
    async submitLoop() {
      if (!this.validateForm()) {
        return;
      }

      this.submitting = true;
      try {
        // 準備請求數據
        const payload = {
          loop_name: this.formData.loop_name.trim(),
          vendor_id: parseInt(this.formData.vendor_id),
          batch_size: parseInt(this.formData.batch_size),
          max_iterations: parseInt(this.formData.max_iterations),
          target_pass_rate: parseFloat(this.formData.target_pass_rate),
          scenario_filters: this.formData.scenario_filters || {}
        };

        // 添加可選欄位
        if (this.formData.parent_loop_id) {
          payload.parent_loop_id = parseInt(this.formData.parent_loop_id);
        }
        if (this.formData.budget_limit_usd) {
          payload.budget_limit_usd = parseFloat(this.formData.budget_limit_usd);
        }

        // 發送 API 請求
        const response = await axios.post('/rag-api/v1/loops/start', payload);

        // 成功提示
        alert(`✅ 迴圈啟動成功！\n\n迴圈 ID: ${response.data.loop_id}\n迴圈名稱: ${response.data.loop_name}\n測試集大小: ${response.data.selected_scenarios.length} 題\n\n系統將開始執行第一次迭代。`);

        // 關閉 Modal 並刷新列表
        this.closeModal();
        await this.loadLoops();

      } catch (err) {
        console.error('啟動迴圈失敗：', err);
        const errorMsg = err.response?.data?.detail || err.message || '啟動失敗';
        alert(`❌ 啟動迴圈失敗：\n\n${errorMsg}`);
      } finally {
        this.submitting = false;
      }
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
    },
    async executeIteration(loop) {
      // 確認執行
      const confirmed = confirm(`確定要執行迴圈 #${loop.loop_id} 的迭代嗎？\n\n這將啟動回測、分析和知識生成流程。`);
      if (!confirmed) return;

      try {
        // 調用 API 執行迭代（非同步模式）
        const response = await axios.post(
          `/rag-api/v1/loops/${loop.loop_id}/execute-iteration`,
          { async_mode: true }
        );

        alert(`✅ 迭代執行已啟動！\n\n執行任務 ID: ${response.data.execution_task_id || 'N/A'}\n迴圈狀態: ${response.data.status}\n\n系統將在背景執行，請稍後查看進度。`);

        // 立即刷新列表以顯示最新狀態
        await this.loadLoops();

      } catch (err) {
        console.error('執行迭代失敗：', err);
        const errorMsg = err.response?.data?.detail || err.message || '執行失敗';
        alert(`❌ 執行迭代失敗：\n\n${errorMsg}`);
      }
    },
    async pauseLoop(loop) {
      try {
        const response = await axios.post(
          `/rag-api/v1/loops/${loop.loop_id}/pause`
        );

        alert(`✅ 迴圈已暫停！\n\n迴圈 ID: ${loop.loop_id}\n新狀態: ${response.data.status}`);

        // 刷新列表以顯示最新狀態
        await this.loadLoops();

      } catch (err) {
        console.error('暫停迴圈失敗：', err);
        const errorMsg = err.response?.data?.detail || err.message || '暫停失敗';
        alert(`❌ 暫停迴圈失敗：\n\n${errorMsg}`);
      }
    },
    async resumeLoop(loop) {
      try {
        const response = await axios.post(
          `/rag-api/v1/loops/${loop.loop_id}/resume`
        );

        alert(`✅ 迴圈已恢復！\n\n迴圈 ID: ${loop.loop_id}\n新狀態: ${response.data.status}`);

        // 刷新列表以顯示最新狀態
        await this.loadLoops();

      } catch (err) {
        console.error('恢復迴圈失敗：', err);
        const errorMsg = err.response?.data?.detail || err.message || '恢復失敗';
        alert(`❌ 恢復迴圈失敗：\n\n${errorMsg}`);
      }
    },
    async cancelLoop(loop) {
      // 確認對話框（取消操作不可逆）
      const confirmed = confirm(`⚠️ 確定要取消迴圈 #${loop.loop_id} 嗎？\n\n此操作不可恢復！\n迴圈將被標記為 CANCELLED 狀態。`);
      if (!confirmed) return;

      try {
        const response = await axios.post(
          `/rag-api/v1/loops/${loop.loop_id}/cancel`
        );

        alert(`✅ 迴圈已取消！\n\n迴圈 ID: ${loop.loop_id}\n新狀態: ${response.data.status}`);

        // 刷新列表以顯示最新狀態
        await this.loadLoops();

      } catch (err) {
        console.error('取消迴圈失敗：', err);
        const errorMsg = err.response?.data?.detail || err.message || '取消失敗';
        alert(`❌ 取消迴圈失敗：\n\n${errorMsg}`);
      }
    },
    async completeBatch(loop) {
      // 確認對話框（完成批次會結束迴圈）
      const confirmed = confirm(`確定要完成迴圈 #${loop.loop_id} 的批次嗎？\n\n迴圈將被標記為 COMPLETED 狀態。`);
      if (!confirmed) return;

      try {
        const response = await axios.post(
          `/rag-api/v1/loops/${loop.loop_id}/complete-batch`
        );

        // 顯示統計摘要
        const summary = response.data.summary || {};
        alert(`✅ 批次已完成！\n\n迴圈 ID: ${loop.loop_id}\n新狀態: ${response.data.status}\n總迭代: ${summary.total_iterations || 'N/A'}\n最終通過率: ${summary.final_pass_rate ? (summary.final_pass_rate * 100).toFixed(1) + '%' : 'N/A'}\n生成知識數: ${summary.total_knowledge_generated || 'N/A'}`);

        // 刷新列表以顯示最新狀態
        await this.loadLoops();

      } catch (err) {
        console.error('完成批次失敗：', err);
        const errorMsg = err.response?.data?.detail || err.message || '完成失敗';
        alert(`❌ 完成批次失敗：\n\n${errorMsg}`);
      }
    },
    showStartNextBatchModal(loop) {
      // 設定父迴圈資訊
      this.nextBatchParentLoop = loop;

      // 自動生成新迴圈名稱建議
      const batchNumber = this.getBatchNumber(loop.loop_name) + 1;
      const vendorName = this.getVendorShortName(loop.vendor_id);

      this.nextBatchFormData = {
        loop_name: `第${batchNumber}批-${vendorName}知識完善`,
        batch_size: 50,
        max_iterations: 10,
        target_pass_rate: 0.85
      };

      this.showNextBatchModal = true;
    },
    closeNextBatchModal() {
      this.showNextBatchModal = false;
      this.nextBatchParentLoop = null;
      this.nextBatchFormData = {
        loop_name: '',
        batch_size: 50,
        max_iterations: 10,
        target_pass_rate: 0.85
      };
    },
    getBatchNumber(loopName) {
      // 從迴圈名稱提取批次編號（例如「第1批」→ 1）
      const match = loopName.match(/第(\d+)批/);
      return match ? parseInt(match[1]) : 1;
    },
    getVendorShortName(vendorId) {
      const vendors = {
        1: '心巢',
        2: '富喬',
        3: '愛租屋'
      };
      return vendors[vendorId] || `業者${vendorId}`;
    },
    async submitNextBatch() {
      this.submitting = true;
      try {
        // 準備請求數據
        const payload = {
          loop_name: this.nextBatchFormData.loop_name.trim(),
          vendor_id: this.nextBatchParentLoop.vendor_id,
          batch_size: parseInt(this.nextBatchFormData.batch_size),
          max_iterations: parseInt(this.nextBatchFormData.max_iterations),
          target_pass_rate: parseFloat(this.nextBatchFormData.target_pass_rate),
          parent_loop_id: this.nextBatchParentLoop.loop_id,  // 關鍵：父迴圈 ID
          scenario_filters: {}
        };

        // 發送 API 請求
        const response = await axios.post('/rag-api/v1/loops/start-next-batch', payload);

        // 成功提示
        alert(`✅ 下一批次啟動成功！\n\n迴圈 ID: ${response.data.loop_id}\n迴圈名稱: ${response.data.loop_name}\n測試集大小: ${response.data.scenario_ids.length} 題\n\n系統已自動排除父迴圈的 ${this.nextBatchParentLoop.total_scenarios} 題。`);

        // 關閉 Modal 並刷新列表
        this.closeNextBatchModal();
        await this.loadLoops();

      } catch (err) {
        console.error('啟動下一批次失敗：', err);
        const errorMsg = err.response?.data?.detail || err.message || '啟動失敗';
        alert(`❌ 啟動下一批次失敗：\n\n${errorMsg}`);
      } finally {
        this.submitting = false;
      }
    }
  }
};
</script>

<style scoped>
.loop-management-tab {
  padding: 20px;
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

/* 啟動下一批次 Modal 樣式 */
.parent-loop-info {
  background-color: #f0f7ff;
  border: 1px solid #2196F3;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
}

.parent-loop-info h4 {
  margin: 0 0 12px 0;
  color: #1976D2;
  font-size: 14px;
  font-weight: 600;
}

.info-note {
  margin-top: 12px;
  padding: 8px 12px;
  background-color: #e3f2fd;
  border-left: 3px solid #2196F3;
  font-size: 13px;
  color: #1565C0;
  border-radius: 4px;
}

.highlight {
  font-weight: 600;
  color: #FF9800;
}

.btn-next-batch {
  background-color: #FF9800;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  font-size: 14px;
}

.btn-next-batch:hover {
  background-color: #F57C00;
}

.difficulty-preview {
  display: flex;
  gap: 12px;
  padding: 12px;
  background-color: #f9f9f9;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
}

.difficulty-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  text-align: center;
}

.difficulty-label {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.difficulty-label.easy {
  background-color: #4CAF50;
  color: white;
}

.difficulty-label.medium {
  background-color: #FF9800;
  color: white;
}

.difficulty-label.hard {
  background-color: #F44336;
  color: white;
}

.difficulty-value {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.loop-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-weight: 600;
  color: #333;
  font-size: 14px;
}

.required {
  color: #F44336;
}

.form-group input,
.form-group select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: #2196F3;
  box-shadow: 0 0 0 2px rgba(33, 150, 243, 0.1);
}

.help-text {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
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
