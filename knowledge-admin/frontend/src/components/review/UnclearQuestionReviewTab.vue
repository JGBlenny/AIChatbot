<template>
  <div class="unclear-question-review-tab">
    <!-- 統計信息 -->
    <div class="stats-banner">
      <p>可轉換的用戶問題：<strong class="count-highlight">{{ candidates.length }}</strong> 個</p>
      <p class="sub-info">系統會自動將頻率 ≥2 的問題轉為測試情境，這裡顯示尚未自動轉換的候選問題</p>
    </div>

    <!-- 載入狀態 -->
    <div v-if="loading" class="loading-state">
      <p>⏳ 載入中...</p>
    </div>

    <!-- 空狀態 -->
    <div v-else-if="candidates.length === 0" class="empty-state">
      <p>🎉 沒有待處理的用戶問題！</p>
      <p class="empty-subtitle">所有高頻問題都已自動轉為測試情境</p>
    </div>

    <!-- 候選問題列表 -->
    <div v-else class="candidates-list">
      <div
        v-for="candidate in candidates"
        :key="candidate.unclear_question_id"
        class="candidate-card"
      >
        <div class="card-header">
          <span class="question-id">#{{ candidate.unclear_question_id }}</span>
          <span class="frequency-badge" :class="getFrequencyClass(candidate.frequency)">
            📊 被問 {{ candidate.frequency }} 次
          </span>

          <!-- 高頻重試特殊標識 -->
          <span v-if="candidate.is_high_freq_retry" class="retry-badge">
            🔄 高頻重試
          </span>

          <span v-if="candidate.unclear_status === 'in_progress'" class="status-badge in-progress">
            處理中
          </span>
          <span v-else class="status-badge pending">
            待處理
          </span>
        </div>

        <div class="card-body">
          <div class="question-section">
            <h3>用戶問題</h3>
            <p class="question-text">{{ candidate.question }}</p>
          </div>

          <div class="info-grid">
            <div class="info-item">
              <label>首次提問：</label>
              <span>{{ formatDate(candidate.first_asked_at) }}</span>
            </div>

            <div class="info-item">
              <label>最近提問：</label>
              <span>{{ formatDate(candidate.last_asked_at) }}</span>
            </div>

            <div class="info-item" v-if="candidate.intent_type">
              <label>意圖類型：</label>
              <span>{{ candidate.intent_type }}</span>
            </div>

            <div class="info-item">
              <label>自動轉換：</label>
              <span v-if="candidate.can_create_scenario" class="status-yes">
                ✅ 可轉換
              </span>
              <span v-else class="status-no">
                ❌ 已存在（情境 #{{ candidate.existing_scenario_id }}）
              </span>
            </div>
          </div>

          <!-- 已轉換情境信息 -->
          <div v-if="candidate.existing_scenario_id" class="existing-info" :class="getScenarioStatusClass(candidate.scenario_status)">
            <div class="info-header">
              <span v-if="candidate.scenario_status === 'rejected'" class="status-icon">⚠️</span>
              <span v-else-if="candidate.scenario_status === 'approved'" class="status-icon">✅</span>
              <span v-else class="status-icon">📝</span>

              <strong>
                {{ getScenarioStatusText(candidate.scenario_status) }}
              </strong>
            </div>

            <p class="info-detail">
              測試情境 #{{ candidate.existing_scenario_id }}
              <span v-if="candidate.scenario_status === 'rejected' && candidate.is_high_freq_retry">
                曾被拒絕，但問題頻率持續上升，建議重新審核
              </span>
              <span v-else-if="candidate.scenario_status === 'rejected'">
                已被拒絕（頻率達 5 次時可自動重新創建）
              </span>
            </p>
          </div>
        </div>

        <div class="card-actions" v-if="candidate.can_create_scenario">
          <button
            @click="convertToScenario(candidate)"
            class="btn btn-primary"
            :disabled="converting[candidate.unclear_question_id]"
          >
            {{ converting[candidate.unclear_question_id] ? '轉換中...' : '🔄 轉為測試情境' }}
          </button>

          <button
            @click="ignoreQuestion(candidate)"
            class="btn btn-secondary"
          >
            🚫 忽略
          </button>
        </div>

        <div class="card-actions" v-else>
          <a
            :href="`#/test-scenarios?highlight=${candidate.existing_scenario_id}`"
            class="btn btn-link"
          >
            📋 查看測試情境
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { API_ENDPOINTS } from '@/config/api';

export default {
  name: 'UnclearQuestionReviewTab',

  emits: ['update-count'],

  data() {
    return {
      candidates: [],
      loading: false,
      converting: {}  // Track conversion status per question
    };
  },

  mounted() {
    this.loadCandidates();
  },

  methods: {
    async loadCandidates() {
      this.loading = true;
      try {
        const response = await axios.get('/api/test/unclear-questions/candidates');
        this.candidates = response.data.candidates;

        // 通知父組件更新待審核數量
        const convertibleCount = this.candidates.filter(c => c.can_create_scenario).length;
        this.$emit('update-count', {
          tab: 'unclear-questions',
          count: convertibleCount
        });
      } catch (error) {
        console.error('載入候選問題失敗:', error);
        alert('載入失敗');
      } finally {
        this.loading = false;
      }
    },

    async convertToScenario(candidate) {
      if (!confirm(`確定要將問題「${candidate.question}」轉為測試情境嗎？`)) {
        return;
      }

      this.converting[candidate.unclear_question_id] = true;

      try {
        const response = await axios.post(
          `/api/test/unclear-questions/${candidate.unclear_question_id}/convert`,
          {
            difficulty: this.getDifficultyByFrequency(candidate.frequency)
          }
        );

        alert(`✅ 已創建測試情境 #${response.data.scenario_id}！\n\n該情境已進入待審核狀態，請到「測試情境審核」標籤查看。`);

        // 重新載入列表
        this.loadCandidates();
      } catch (error) {
        console.error('轉換失敗:', error);
        alert('轉換失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.converting[candidate.unclear_question_id] = false;
      }
    },

    async ignoreQuestion(candidate) {
      if (!confirm(`確定要忽略問題「${candidate.question}」嗎？\n\n此操作會將問題狀態設為「已忽略」。`)) {
        return;
      }

      try {
        await axios.put(
          API_ENDPOINTS.unclearQuestionById(candidate.unclear_question_id),
          { status: 'ignored' }
        );

        alert('✅ 已忽略該問題');
        this.loadCandidates();
      } catch (error) {
        console.error('忽略失敗:', error);
        alert('操作失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    getDifficultyByFrequency(frequency) {
      if (frequency >= 5) return 'easy';  // 高頻問題通常是常見問題，較簡單
      if (frequency >= 3) return 'medium';
      return 'hard';  // 低頻但達標的問題可能較複雜
    },

    getFrequencyClass(frequency) {
      if (frequency >= 5) return 'high';
      if (frequency >= 3) return 'medium';
      return 'low';
    },

    formatDate(dateString) {
      if (!dateString) return '-';
      const date = new Date(dateString);
      return date.toLocaleString('zh-TW');
    },

    getScenarioStatusClass(status) {
      if (status === 'rejected') return 'status-rejected';
      if (status === 'approved') return 'status-approved';
      return 'status-pending';
    },

    getScenarioStatusText(status) {
      const statusMap = {
        'pending_review': '測試情境待審核',
        'approved': '測試情境已批准',
        'rejected': '測試情境已拒絕'
      };
      return statusMap[status] || '未知狀態';
    }
  }
};
</script>

<style scoped>
.unclear-question-review-tab {
  width: 100%;
}

/* 統計橫幅 */
.stats-banner {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
  padding: 24px;
  border-radius: 12px;
  margin-bottom: 25px;
  text-align: center;
}

.stats-banner p {
  margin: 0;
  font-size: 16px;
}

.stats-banner p:first-child {
  margin-bottom: 8px;
}

.sub-info {
  font-size: 13px !important;
  opacity: 0.9;
}

.count-highlight {
  font-size: 32px;
  font-weight: bold;
  margin: 0 5px;
}

/* 候選問題列表 */
.candidates-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.candidate-card {
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s;
}

.candidate-card:hover {
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
  transform: translateY(-4px);
}

.card-header {
  background: #f8f9fa;
  padding: 15px 20px;
  display: flex;
  justify-content: flex-start;
  align-items: center;
  gap: 12px;
  border-bottom: 2px solid #e9ecef;
}

.question-id {
  font-weight: bold;
  color: #f5576c;
  font-size: 16px;
}

.frequency-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
  color: white;
}

.frequency-badge.high {
  background: #e74c3c;
}

.frequency-badge.medium {
  background: #f39c12;
}

.frequency-badge.low {
  background: #3498db;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  margin-left: auto;
}

.status-badge.pending {
  background: #fff3cd;
  color: #856404;
}

.status-badge.in-progress {
  background: #d1ecf1;
  color: #0c5460;
}

.card-body {
  padding: 20px;
}

.question-section h3 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #666;
  font-weight: 600;
}

.question-text {
  font-size: 18px;
  font-weight: 500;
  color: #333;
  margin: 0 0 20px 0;
  line-height: 1.6;
}



.info-item label {
  font-size: 12px;
  color: #999;
  font-weight: 600;
}

.info-item span {
  font-size: 14px;
  color: #333;
}

.status-yes {
  color: #28a745;
  font-weight: 600;
}

.status-no {
  color: #6c757d;
}

.existing-info {
  padding: 15px;
  border-radius: 8px;
  margin-top: 15px;
  border-left: 4px solid;
}

.existing-info.status-pending {
  background: #e7f3ff;
  border-left-color: #409eff;
}

.existing-info.status-approved {
  background: #f0f9ff;
  border-left-color: #67c23a;
}

.existing-info.status-rejected {
  background: #fef0f0;
  border-left-color: #f56c6c;
}

.existing-info .info-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.existing-info .status-icon {
  font-size: 18px;
}

.existing-info .info-header strong {
  font-size: 14px;
  color: #333;
}

.existing-info .info-detail {
  margin: 0;
  font-size: 13px;
  color: #666;
  line-height: 1.6;
}

/* 高頻重試標識 */
.retry-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

/* 操作按鈕 */
.card-actions {
  display: flex;
  gap: 10px;
  padding: 15px 20px;
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  text-decoration: none;
  display: inline-block;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  flex: 1;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(245, 87, 108, 0.4);
}

.btn-secondary {
  background: #e9ecef;
  color: #495057;
}

.btn-secondary:hover {
  background: #dee2e6;
}

.btn-link {
  background: #667eea;
  color: white;
  text-align: center;
}

.btn-link:hover {
  background: #5568d3;
}

/* 狀態顯示 */
.loading-state,
.empty-state {
  color: #999;
}

.empty-state p:first-child {
  font-size: 24px;
  margin-bottom: 10px;
}

.empty-subtitle {
  font-size: 14px;
  color: #aaa;
}
</style>
