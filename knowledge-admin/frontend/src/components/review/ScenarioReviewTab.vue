<template>
  <div class="scenario-review-tab">
    <!-- 統計信息 -->
    <div class="stats-banner">
      <p>待審核測試情境：<strong class="count-highlight">{{ scenarios.length }}</strong> 個</p>
    </div>

    <!-- 載入狀態 -->
    <div v-if="loading" class="loading-state">
      <p>⏳ 載入中...</p>
    </div>

    <!-- 空狀態 -->
    <div v-else-if="scenarios.length === 0" class="empty-state">
      <p>🎉 沒有待審核的測試情境！</p>
      <p class="empty-subtitle">所有測試情境都已處理完畢</p>
    </div>

    <!-- 情境列表 -->
    <div v-else class="scenarios-list">
      <div
        v-for="scenario in scenarios"
        :key="scenario.id"
        class="scenario-card"
      >
        <div class="card-header">
          <span class="scenario-id">#{{ scenario.id }}</span>
          <span v-if="scenario.source === 'user_question'" class="source-badge user">
            👤 用戶問題
          </span>
          <span v-else class="source-badge manual">
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
              <label>預期分類：</label>
              <span>{{ scenario.expected_category || '-' }}</span>
            </div>

            <div class="info-item">
              <label>難度：</label>
              <span :class="['badge', 'badge-' + scenario.difficulty]">
                {{ scenario.difficulty }}
              </span>
            </div>

            <div class="info-item">
              <label>優先級：</label>
              <span>{{ scenario.priority }}</span>
            </div>

            <div class="info-item" v-if="scenario.question_frequency">
              <label>問題頻率：</label>
              <span class="frequency-badge">{{ scenario.question_frequency }} 次</span>
            </div>
          </div>

          <div v-if="scenario.expected_keywords && scenario.expected_keywords.length > 0" class="keywords-section">
            <label>預期關鍵字：</label>
            <span
              v-for="(keyword, idx) in scenario.expected_keywords"
              :key="idx"
              class="keyword-tag"
            >
              {{ keyword }}
            </span>
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
            class="btn btn-edit"
          >
            ✏️ 編輯
          </button>

          <button
            @click="approveScenario(scenario.id)"
            class="btn btn-approve"
          >
            ✅ 批准
          </button>

          <button
            @click="rejectScenario(scenario.id)"
            class="btn btn-reject"
          >
            ❌ 拒絕
          </button>
        </div>
      </div>
    </div>

    <!-- 審核對話框 -->
    <div v-if="reviewingScenario" class="modal-overlay" @click.self="closeReviewDialog">
      <div class="modal-content">
        <h3>{{ reviewAction === 'approve' ? '批准' : '拒絕' }}測試情境</h3>

        <div class="review-summary">
          <p><strong>問題：</strong>{{ reviewingScenario.test_question }}</p>
        </div>

        <form @submit.prevent="submitReview">
          <div class="form-group">
            <label>審核備註</label>
            <textarea
              v-model="reviewForm.notes"
              rows="3"
              :placeholder="reviewAction === 'approve' ? '批准原因（選填）' : '拒絕原因（建議填寫）'"
            ></textarea>
          </div>

          <div class="form-actions">
            <button type="button" @click="closeReviewDialog" class="btn btn-secondary">
              取消
            </button>
            <button
              type="submit"
              :class="reviewAction === 'approve' ? 'btn btn-approve' : 'btn btn-reject'"
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
              <label>預期分類</label>
              <input v-model="editForm.expected_category" />
            </div>

            <div class="form-group">
              <label>難度 *</label>
              <select v-model="editForm.difficulty" required>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label>預期關鍵字（逗號分隔）</label>
            <input
              v-model="editForm.expected_keywords"
              placeholder="關鍵字1, 關鍵字2"
            />
          </div>

          <div class="form-group">
            <label>優先級（1-100）</label>
            <input
              v-model.number="editForm.priority"
              type="number"
              min="1"
              max="100"
            />
          </div>

          <div class="form-group">
            <label>備註</label>
            <textarea v-model="editForm.notes" rows="2"></textarea>
          </div>

          <div class="form-actions">
            <button type="button" @click="closeEditDialog" class="btn btn-secondary">
              取消
            </button>
            <button type="submit" class="btn btn-primary">
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
  name: 'ScenarioReviewTab',

  emits: ['update-count'],

  data() {
    return {
      scenarios: [],
      loading: false,

      reviewingScenario: null,
      reviewAction: null,
      reviewForm: {
        notes: ''
      },

      editingScenario: null,
      editForm: {
        test_question: '',
        expected_category: '',
        expected_keywords: '',
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

        // 通知父組件更新待審核數量
        this.$emit('update-count', {
          tab: 'scenarios',
          count: this.scenarios.length
        });
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

        alert(`✅ 測試情境已${this.reviewAction === 'approve' ? '批准' : '拒絕'}！`);
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
        expected_category: scenario.expected_category || '',
        expected_keywords: scenario.expected_keywords?.join(', ') || '',
        difficulty: scenario.difficulty,
        priority: scenario.priority,
        notes: scenario.notes || ''
      };
    },

    async saveEdit() {
      try {
        const data = {
          ...this.editForm,
          expected_keywords: this.editForm.expected_keywords
            .split(',')
            .map(k => k.trim())
            .filter(k => k)
        };

        await axios.put(`/api/test/scenarios/${this.editingScenario.id}`, data);
        alert('✅ 測試情境已更新！');
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
    }
  }
};
</script>

<style scoped>
.scenario-review-tab {
  width: 100%;
}

/* 統計橫幅 */
.stats-banner {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 12px;
  margin-bottom: 25px;
  text-align: center;
}

.stats-banner p {
  margin: 0;
  font-size: 16px;
}

.count-highlight {
  font-size: 28px;
  font-weight: bold;
  margin: 0 5px;
}

/* 情境列表 */
.scenarios-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.scenario-card {
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s;
}

.scenario-card:hover {
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
  transform: translateY(-4px);
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
  font-size: 16px;
}

.source-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  color: white;
}

.source-badge.user {
  background: #409eff;
}

.source-badge.manual {
  background: #909399;
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

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
  margin-bottom: 15px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
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

.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.badge-easy { background: #d4edda; color: #155724; }
.badge-medium { background: #fff3cd; color: #856404; }
.badge-hard { background: #f8d7da; color: #721c24; }

.frequency-badge {
  display: inline-block;
  padding: 4px 10px;
  background: #fff3cd;
  color: #856404;
  border-radius: 12px;
  font-weight: 600;
  font-size: 14px !important;
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

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-edit {
  background: #e9ecef;
  color: #495057;
}

.btn-edit:hover {
  background: #dee2e6;
}

.btn-approve {
  background: #28a745;
  color: white;
  flex: 1;
}

.btn-approve:hover {
  background: #218838;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(40, 167, 69, 0.4);
}

.btn-reject {
  background: #dc3545;
  color: white;
  flex: 1;
}

.btn-reject:hover {
  background: #c82333;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(220, 53, 69, 0.4);
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover {
  background: #5568d3;
}

.btn-secondary {
  background: #e9ecef;
  color: #495057;
}

.btn-secondary:hover {
  background: #dee2e6;
}

/* 狀態顯示 */
.loading-state,
.empty-state {
  text-align: center;
  padding: 60px 20px;
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

/* 對話框樣式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
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

.form-group {
  margin-bottom: 20px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #333;
  font-size: 14px;
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

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 30px;
}
</style>
