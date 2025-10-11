<template>
  <div class="ai-knowledge-review-view">
    <div class="page-header">
      <h2>🤖 AI 知識候選審核</h2>
      <div class="header-actions">
        <button @click="refreshData" class="btn-secondary">
          🔄 重新整理
        </button>
      </div>
    </div>

    <!-- 統計區域 -->
    <div class="stats-section" v-if="stats">
      <div class="stat-card">
        <div class="stat-value">{{ stats.pending_count }}</div>
        <div class="stat-label">待審核</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.approved_count }}</div>
        <div class="stat-label">已批准</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.approval_rate?.toFixed(0) || 0 }}%</div>
        <div class="stat-label">批准率</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.edit_rate?.toFixed(0) || 0 }}%</div>
        <div class="stat-label">編輯率</div>
      </div>
    </div>

    <!-- 候選列表 -->
    <div class="candidates-list" v-if="!loading">
      <div v-if="candidates.length === 0" class="empty-state">
        <p>🎉 太好了！目前沒有待審核的 AI 知識候選</p>
        <p>您可以在「測試題庫管理」頁面為已批准且無知識的測試情境生成知識</p>
      </div>

      <div v-for="candidate in candidates" :key="candidate.id" class="candidate-card">
        <div class="candidate-header">
          <div class="candidate-meta">
            <span class="candidate-id">候選 #{{ candidate.id }}</span>
            <span class="test-scenario-link">
              測試情境 #{{ candidate.test_scenario_id }}
            </span>
            <span :class="['badge', 'badge-' + candidate.difficulty]">
              {{ candidate.difficulty }}
            </span>
            <span class="category-badge">{{ candidate.category }}</span>
          </div>
          <div class="ai-meta">
            <span class="ai-model">🤖 {{ candidate.ai_model }}</span>
            <span :class="['confidence-score', getConfidenceClass(candidate.confidence_score)]">
              信心度: {{ (candidate.confidence_score * 100).toFixed(0) }}%
            </span>
          </div>
        </div>

        <div class="candidate-content">
          <!-- 原始測試問題 -->
          <div class="section">
            <h4>📝 原始測試問題</h4>
            <p class="test-question">{{ candidate.test_question }}</p>
          </div>

          <!-- AI 生成的問題 -->
          <div class="section">
            <h4>❓ AI 生成的問題</h4>
            <textarea
              v-if="editingCandidates[candidate.id]"
              v-model="editForms[candidate.id].question"
              rows="2"
              class="edit-textarea"
            ></textarea>
            <p v-else class="generated-question">{{ candidate.question }}</p>
          </div>

          <!-- AI 生成的答案 -->
          <div class="section">
            <h4>💡 AI 生成的答案</h4>
            <textarea
              v-if="editingCandidates[candidate.id]"
              v-model="editForms[candidate.id].answer"
              rows="8"
              class="edit-textarea"
            ></textarea>
            <p v-else class="generated-answer">{{ candidate.generated_answer }}</p>
          </div>

          <!-- 警告 -->
          <div v-if="candidate.warnings && candidate.warnings.length > 0" class="warnings-section">
            <h4>⚠️ AI 警告</h4>
            <ul class="warnings-list">
              <li v-for="(warning, idx) in candidate.warnings" :key="idx">
                {{ warning }}
              </li>
            </ul>
          </div>

          <!-- 編輯摘要 -->
          <div v-if="editingCandidates[candidate.id]" class="section">
            <h4>📋 編輯摘要（說明您做了哪些修改）</h4>
            <textarea
              v-model="editForms[candidate.id].edit_summary"
              rows="2"
              placeholder="例如：修正了語氣、補充了細節說明..."
              class="edit-textarea"
            ></textarea>
          </div>
        </div>

        <div class="candidate-actions">
          <div v-if="editingCandidates[candidate.id]" class="edit-actions">
            <button @click="cancelEdit(candidate.id)" class="btn-secondary">
              取消編輯
            </button>
            <button @click="saveEdit(candidate.id)" class="btn-primary">
              💾 儲存編輯
            </button>
          </div>
          <div v-else class="review-actions">
            <button @click="startEdit(candidate)" class="btn-secondary">
              ✏️ 編輯
            </button>
            <button @click="rejectCandidate(candidate.id)" class="btn-danger">
              ❌ 拒絕
            </button>
            <button @click="approveCandidate(candidate)" class="btn-success">
              ✅ 批准並加入知識庫
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="loading-state">
      <p>⏳ 載入中...</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'AIKnowledgeReviewView',

  data() {
    return {
      candidates: [],
      stats: null,
      loading: false,
      editingCandidates: {},
      editForms: {}
    };
  },

  mounted() {
    this.loadStats();
    this.loadCandidates();
  },

  methods: {
    async loadStats() {
      try {
        const response = await axios.get('http://localhost:8100/api/v1/knowledge-candidates/stats');
        this.stats = response.data;
      } catch (error) {
        console.error('載入統計失敗:', error);
      }
    },

    async loadCandidates() {
      this.loading = true;
      try {
        const response = await axios.get('http://localhost:8100/api/v1/knowledge-candidates/pending', {
          params: { limit: 50 }
        });
        this.candidates = response.data.candidates;
      } catch (error) {
        console.error('載入候選失敗:', error);
        alert('載入候選失敗');
      } finally {
        this.loading = false;
      }
    },

    getConfidenceClass(score) {
      if (score >= 0.8) return 'confidence-high';
      if (score >= 0.6) return 'confidence-medium';
      return 'confidence-low';
    },

    startEdit(candidate) {
      this.$set(this.editingCandidates, candidate.id, true);
      this.$set(this.editForms, candidate.id, {
        question: candidate.question,
        answer: candidate.generated_answer,
        edit_summary: ''
      });
    },

    cancelEdit(candidateId) {
      this.$delete(this.editingCandidates, candidateId);
      this.$delete(this.editForms, candidateId);
    },

    async saveEdit(candidateId) {
      const form = this.editForms[candidateId];

      if (!form.edit_summary.trim()) {
        alert('請填寫編輯摘要，說明您做了哪些修改');
        return;
      }

      try {
        await axios.put(`http://localhost:8100/api/v1/knowledge-candidates/${candidateId}/edit`, {
          edited_question: form.question,
          edited_answer: form.answer,
          edit_summary: form.edit_summary
        });

        alert('✅ 編輯已儲存！');
        this.cancelEdit(candidateId);
        this.loadCandidates();
      } catch (error) {
        console.error('儲存編輯失敗:', error);
        alert('儲存編輯失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    async approveCandidate(candidate) {
      const hasEdits = candidate.has_edits || this.editingCandidates[candidate.id];
      const confirmMsg = hasEdits
        ? `確定要批准候選 #${candidate.id} 嗎？\n\n將使用編輯後的版本加入知識庫。`
        : `確定要批准候選 #${candidate.id} 嗎？\n\n將使用 AI 原始版本加入知識庫。`;

      if (!confirm(confirmMsg)) return;

      try {
        const response = await axios.post(
          `http://localhost:8100/api/v1/knowledge-candidates/${candidate.id}/review`,
          {
            action: 'approve',
            reviewer_name: 'admin',
            review_notes: hasEdits ? '已審核並編輯' : '已審核，直接批准'
          }
        );

        alert(`✅ 已批准！新知識 ID: ${response.data.new_knowledge_id}\n\n已加入知識庫。`);
        this.loadCandidates();
        this.loadStats();
      } catch (error) {
        console.error('批准失敗:', error);
        alert('批准失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    async rejectCandidate(candidateId) {
      const reason = prompt('請說明拒絕原因：');
      if (!reason) return;

      try {
        await axios.post(
          `http://localhost:8100/api/v1/knowledge-candidates/${candidateId}/review`,
          {
            action: 'reject',
            reviewer_name: 'admin',
            review_notes: reason
          }
        );

        alert('✅ 已拒絕該候選');
        this.loadCandidates();
        this.loadStats();
      } catch (error) {
        console.error('拒絕失敗:', error);
        alert('拒絕失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    refreshData() {
      this.loadStats();
      this.loadCandidates();
    }
  }
};
</script>

<style scoped>
.ai-knowledge-review-view {
  width: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.page-header h2 {
  margin: 0;
  font-size: 28px;
  color: #333;
}

.header-actions {
  display: flex;
  gap: 10px;
}

/* 統計區域 */
.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  text-align: center;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #667eea;
  margin-bottom: 8px;
}

.stat-label {
  color: #666;
  font-size: 14px;
}

/* 候選列表 */
.candidates-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.candidate-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  overflow: hidden;
  border: 2px solid #e9ecef;
  transition: all 0.3s;
}

.candidate-card:hover {
  box-shadow: 0 6px 20px rgba(0,0,0,0.15);
  border-color: #667eea;
}

.candidate-header {
  background: #f8f9fa;
  padding: 15px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e9ecef;
}

.candidate-meta {
  display: flex;
  gap: 12px;
  align-items: center;
}

.candidate-id {
  font-weight: bold;
  color: #667eea;
  font-size: 16px;
}

.test-scenario-link {
  color: #666;
  font-size: 14px;
}

.category-badge {
  background: #e7f3ff;
  color: #0066cc;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.ai-meta {
  display: flex;
  gap: 12px;
  align-items: center;
}

.ai-model {
  font-size: 13px;
  color: #666;
}

.confidence-score {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.confidence-high { background: #d4edda; color: #155724; }
.confidence-medium { background: #fff3cd; color: #856404; }
.confidence-low { background: #f8d7da; color: #721c24; }

/* 候選內容 */
.candidate-content {
  padding: 20px;
}

.section {
  margin-bottom: 20px;
}

.section h4 {
  margin: 0 0 10px 0;
  font-size: 14px;
  font-weight: 600;
  color: #495057;
}

.test-question {
  background: #e7f3ff;
  padding: 12px;
  border-radius: 6px;
  margin: 0;
  color: #0066cc;
  font-weight: 500;
}

.generated-question {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 6px;
  margin: 0;
  font-weight: 500;
}

.generated-answer {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  margin: 0;
  line-height: 1.6;
  white-space: pre-wrap;
}

.edit-textarea {
  width: 100%;
  padding: 12px;
  border: 2px solid #667eea;
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  box-sizing: border-box;
}

.edit-textarea:focus {
  outline: none;
  border-color: #5568d3;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.warnings-section {
  background: #fff3cd;
  padding: 15px;
  border-radius: 6px;
  border-left: 4px solid #ffc107;
}

.warnings-section h4 {
  color: #856404;
  margin-bottom: 10px;
}

.warnings-list {
  margin: 0;
  padding-left: 20px;
  color: #856404;
}

.warnings-list li {
  margin-bottom: 5px;
}

/* 操作按鈕 */
.candidate-actions {
  padding: 15px 20px;
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
}

.review-actions, .edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn-primary, .btn-secondary, .btn-success, .btn-danger {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover {
  background: #5568d3;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-secondary {
  background: #e9ecef;
  color: #495057;
}

.btn-secondary:hover {
  background: #dee2e6;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-success:hover {
  background: #218838;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(40, 167, 69, 0.4);
}

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn-danger:hover {
  background: #c82333;
}

/* 徽章 */
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

/* 空狀態 */
.empty-state, .loading-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.empty-state p:first-child {
  font-size: 20px;
  color: #28a745;
  margin-bottom: 10px;
}
</style>
