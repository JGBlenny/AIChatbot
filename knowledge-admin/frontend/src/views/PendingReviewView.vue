<template>
  <div class="pending-review-view">
    <div class="page-header">
      <h2>📝 測試情境審核</h2>
      <button @click="loadPendingScenarios" class="btn-secondary btn-sm">
        重新整理
      </button>
    </div>

    <div class="pending-count" v-if="!loading">
      <p>待審核測試情境：<strong>{{ scenarios.length }}</strong> 個</p>
    </div>

    <div v-if="!loading && scenarios.length > 0" class="scenarios-list">
      <div
        v-for="scenario in scenarios"
        :key="scenario.id"
        class="scenario-card"
      >
        <div class="card-header">
          <span class="scenario-id">#{{ scenario.id }}</span>
          <span v-if="scenario.source === 'user_question'" class="source-badge">
            👤 來自用戶問題
          </span>
          <span v-else class="source-badge">
            ✏️ {{ scenario.source }}
          </span>
        </div>

        <div class="card-body">
          <div class="question-section">
            <h3>測試問題</h3>
            <p class="question-text">{{ scenario.test_question }}</p>
          </div>

          <div class="info-grid">
            <div class="info-item">
              <label>難度：</label>
              <span :class="['badge', 'badge-' + scenario.difficulty]">
                {{ scenario.difficulty }}
              </span>
            </div>

            <div class="info-item">
              <label>優先級：</label>
              <span :class="['badge', priorityBadgeClass(scenario.priority)]">
                {{ priorityLabel(scenario.priority) }}
              </span>
            </div>

            <div class="info-item" v-if="scenario.question_frequency">
              <label>問題頻率：</label>
              <span class="frequency-badge">{{ scenario.question_frequency }} 次</span>
            </div>
          </div>

          <div v-if="scenario.notes" class="notes-section">
            <label>備註：</label>
            <p>{{ scenario.notes }}</p>
          </div>

          <div class="metadata">
            <small>建立時間：{{ formatDate(scenario.created_at) }}</small>
            <small v-if="scenario.created_by">建立者：{{ scenario.created_by }}</small>
          </div>
        </div>

        <div class="card-actions">
          <button
            @click="editBeforeReview(scenario)"
            class="btn-edit btn-sm"
          >
            編輯
          </button>

          <button
            @click="approveScenario(scenario.id)"
            class="btn-success btn-sm"
          >
            批准
          </button>

          <button
            @click="rejectScenario(scenario.id)"
            class="btn-delete btn-sm"
          >
            拒絕
          </button>
        </div>
      </div>
    </div>

    <div v-else-if="!loading" class="empty-state">
      <p>🎉 沒有待審核的測試情境！</p>
      <p>所有測試情境都已處理完畢</p>
    </div>

    <div v-if="loading" class="loading-state">
      <p>⏳ 載入中...</p>
    </div>

    <!-- 審核對話框 -->
    <div v-if="reviewingScenario" class="modal-overlay" @click.self="closeReviewDialog">
      <div class="modal-content">
        <h3>{{ reviewAction === 'approve' ? '批准' : '拒絕' }}測試情境</h3>

        <div class="review-summary">
          <p><strong>問題：</strong>{{ reviewingScenario.test_question }}</p>
        </div>

        <form @submit.prevent="submitReview">
          <div class="form-actions">
            <button type="button" @click="closeReviewDialog" class="btn-secondary btn-sm">
              取消
            </button>
            <button
              type="submit"
              class="btn-sm"
              :class="reviewAction === 'approve' ? 'btn-success' : 'btn-delete'"
            >
              確認{{ reviewAction === 'approve' ? '批准' : '拒絕' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 編輯對話框 -->
    <div v-if="editingScenario" class="modal-overlay" @click.self="closeEditDialog">
      <div class="modal-content">
        <h3>編輯測試情境</h3>

        <form @submit.prevent="saveEdit">
          <div class="form-group">
            <label>測試問題 *</label>
            <textarea
              v-model="editForm.test_question"
              required
              rows="3"
            ></textarea>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>難度 *</label>
              <select v-model="editForm.difficulty" required>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>

            <div class="form-group">
              <label>優先級 *</label>
              <select v-model.number="editForm.priority" required>
                <option :value="30">低優先級（30）</option>
                <option :value="50">中等優先級（50）</option>
                <option :value="80">高優先級（80）</option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label>備註</label>
            <textarea v-model="editForm.notes" rows="2"></textarea>
          </div>

          <div class="form-actions">
            <button type="button" @click="closeEditDialog" class="btn-secondary btn-sm">
              取消
            </button>
            <button type="submit" class="btn-primary btn-sm">
              儲存
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'PendingReviewView',

  data() {
    return {
      scenarios: [],
      loading: false,

      reviewingScenario: null,
      reviewAction: null, // 'approve' or 'reject'
      reviewForm: {
        notes: ''
      },

      editingScenario: null,
      editForm: {
        test_question: '',
        difficulty: 'medium',
        priority: 50,
        notes: ''
      }
    };
  },

  mounted() {
    this.loadPendingScenarios();
  },

  methods: {
    async loadPendingScenarios() {
      this.loading = true;
      try {
        const response = await axios.get('/api/test/scenarios/pending');
        this.scenarios = response.data.scenarios;
      } catch (error) {
        console.error('載入待審核情境失敗:', error);
        alert('載入失敗');
      } finally {
        this.loading = false;
      }
    },

    approveScenario(scenarioId) {
      const scenario = this.scenarios.find(s => s.id === scenarioId);
      this.reviewingScenario = scenario;
      this.reviewAction = 'approve';
      this.reviewForm = {
        notes: ''
      };
    },

    rejectScenario(scenarioId) {
      const scenario = this.scenarios.find(s => s.id === scenarioId);
      this.reviewingScenario = scenario;
      this.reviewAction = 'reject';
      this.reviewForm = {
        notes: ''
      };
    },

    async submitReview() {
      try {
        const data = {
          action: this.reviewAction,
          notes: this.reviewForm.notes
        };

        await axios.post(
          `/api/test/scenarios/${this.reviewingScenario.id}/review`,
          data
        );

        alert(`測試情境已${this.reviewAction === 'approve' ? '批准' : '拒絕'}！`);
        this.closeReviewDialog();
        this.loadPendingScenarios();
      } catch (error) {
        console.error('審核失敗:', error);
        alert('審核失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    editBeforeReview(scenario) {
      this.editingScenario = scenario;
      this.editForm = {
        test_question: scenario.test_question,
        difficulty: scenario.difficulty,
        priority: scenario.priority || 50,
        notes: scenario.notes || ''
      };
    },

    async saveEdit() {
      try {
        const data = {
          ...this.editForm
        };

        await axios.put(`/api/test/scenarios/${this.editingScenario.id}`, data);
        alert('測試情境已更新！');
        this.closeEditDialog();
        this.loadPendingScenarios();
      } catch (error) {
        console.error('更新失敗:', error);
        alert('更新失敗');
      }
    },

    closeReviewDialog() {
      this.reviewingScenario = null;
      this.reviewAction = null;
      this.reviewForm = { notes: '' };
    },

    closeEditDialog() {
      this.editingScenario = null;
    },

    formatDate(dateString) {
      if (!dateString) return '-';
      const date = new Date(dateString);
      return date.toLocaleString('zh-TW');
    },

    priorityLabel(priority) {
      const labels = {
        30: '低',
        50: '中',
        80: '高'
      };
      return labels[priority] || priority;
    },

    priorityBadgeClass(priority) {
      const classes = {
        30: 'badge-easy',      // Green
        50: 'badge-medium',    // Yellow
        80: 'badge-hard'       // Red
      };
      return classes[priority] || 'badge-medium';
    }
  }
};
</script>

<style scoped>
.pending-review-view {
  width: 100%;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 28px;
  color: #333;
}

.pending-count {
  background: white;
  padding: 15px 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-bottom: 20px;
}

.pending-count strong {
  color: #667eea;
  font-size: 20px;
}

/* 情境卡片 */
.scenarios-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.scenario-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  overflow: hidden;
  transition: transform 0.3s, box-shadow 0.3s;
}

.scenario-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(0,0,0,0.15);
}

.card-header {
  background: #f8f9fa;
  padding: 15px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 2px solid #e9ecef;
}

.scenario-id {
  font-weight: bold;
  color: #667eea;
}

.source-badge {
  padding: 4px 12px;
  background: #e7f3ff;
  color: #0066cc;
  border-radius: 12px;
}

.card-body {
  padding: 20px;
}

.question-section h3 {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #666;
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

.frequency-badge {
  display: inline-block;
  padding: 4px 10px;
  background: #fff3cd;
  color: #856404;
  border-radius: 12px;
  font-weight: 600;
  font-size: 14px !important;
}

.badge {
  font-weight: 600;
}

.keywords-section,
.notes-section {
  margin: 15px 0;
}

.keywords-section label,
.notes-section label {
  display: block;
  font-size: 12px;
  color: #999;
  font-weight: 600;
  margin-bottom: 8px;
}

.keyword-tag {
  display: inline-block;
  padding: 4px 10px;
  margin: 4px;
  background: #e7f3ff;
  color: #0066cc;
  border-radius: 12px;
  font-size: 12px;
}

.notes-section p {
  margin: 0;
  color: #666;
  font-size: 14px;
  line-height: 1.6;
}

.metadata {
  display: flex;
  gap: 20px;
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #e9ecef;
}

.metadata small {
  color: #999;
  font-size: 12px;
}

/* 操作按鈕 */
.card-actions {
  display: flex;
  gap: 10px;
  padding: 15px 20px;
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
}

/* 空狀態和載入狀態 */
.empty-state,
.loading-state {
  text-align: center;
  padding: 60px 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  color: #999;
}

.empty-state p:first-child {
  font-size: 24px;
  margin-bottom: 10px;
}

/* 對話框 */
.modal-overlay {
  background: rgba(0,0,0,0.5);
}

.modal-content {
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
}

.modal-content h3 {
  margin-top: 0;
  margin-bottom: 20px;
  color: #333;
}

.review-summary {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.review-summary p {
  margin: 0;
  color: #333;
}


.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #333;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-group textarea {
  resize: vertical;
  font-family: inherit;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: normal;
  cursor: pointer;
}

</style>
