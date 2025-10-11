<template>
  <div class="knowledge-review-tab">
    <!-- 頁面標題 -->
    <div class="page-title">
      <h3>🤖 AI 知識候選審核</h3>
      <p class="subtitle">審核 AI 自動生成的知識候選答案</p>
    </div>

    <!-- AI 知識候選區域 -->
    <div class="content-area">
      <!-- 頂部操作 -->
      <div class="top-actions">
        <button @click="loadAICandidates" class="btn-refresh" :disabled="loading">
          {{ loading ? '載入中...' : '🔄 刷新' }}
        </button>
      </div>

      <!-- AI 候選統計卡片 -->
      <div class="stats-cards">
        <div class="stat-card">
          <div class="stat-title">待審核</div>
          <div class="stat-value warning">{{ aiStats.pending_count }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-title">已批准</div>
          <div class="stat-value success">{{ aiStats.approved_count }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-title">批准率</div>
          <div class="stat-value info">{{ aiStats.approval_rate?.toFixed(0) || 0 }}%</div>
        </div>
        <div class="stat-card">
          <div class="stat-title">編輯率</div>
          <div class="stat-value muted">{{ aiStats.edit_rate?.toFixed(0) || 0 }}%</div>
        </div>
      </div>

      <!-- 載入狀態 -->
      <div v-if="loading" class="loading-indicator">
        <div class="spinner"></div>
        <p>載入中...</p>
      </div>

      <!-- 空狀態 -->
      <div v-else-if="aiCandidates.length === 0" class="empty-state">
        <div class="empty-icon">🎉</div>
        <h3>目前沒有待審核的 AI 知識候選</h3>
        <p>您可以在「測試題庫管理」頁面為已批准且無知識的測試情境生成知識</p>
      </div>

      <!-- AI 候選列表 -->
      <div v-else class="candidates-list">
        <div v-for="candidate in aiCandidates" :key="'ai-' + candidate.id" class="candidate-card">
          <div class="candidate-header">
            <div class="candidate-meta">
              <span class="candidate-id">候選 #{{ candidate.id }}</span>
              <span class="test-scenario-link">測試情境 #{{ candidate.test_scenario_id }}</span>
              <span :class="['badge', 'badge-' + candidate.difficulty]">{{ candidate.difficulty }}</span>
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
              <h5>📝 原始測試問題</h5>
              <p class="test-question">{{ candidate.test_question }}</p>
            </div>

            <!-- AI 生成的問題 -->
            <div class="section">
              <h5>❓ AI 生成的問題</h5>
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
              <h5>💡 AI 生成的答案</h5>
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
              <h5>⚠️ AI 警告</h5>
              <ul class="warnings-list">
                <li v-for="(warning, idx) in candidate.warnings" :key="idx">{{ warning }}</li>
              </ul>
            </div>

            <!-- 編輯摘要 -->
            <div v-if="editingCandidates[candidate.id]" class="section">
              <h5>📋 編輯摘要（說明您做了哪些修改）</h5>
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
              <button @click="cancelAIEdit(candidate.id)" class="btn btn-secondary">取消編輯</button>
              <button @click="saveAIEdit(candidate.id)" class="btn btn-primary">💾 儲存編輯</button>
            </div>
            <div v-else class="review-actions">
              <button @click="startAIEdit(candidate)" class="btn btn-edit">✏️ 編輯</button>
              <button @click="rejectAICandidate(candidate)" class="btn btn-reject">❌ 拒絕</button>
              <button @click="approveAICandidate(candidate)" class="btn btn-approve">✅ 批准並加入知識庫</button>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'KnowledgeReviewTab',

  emits: ['update-count'],

  data() {
    return {
      // AI 候選數據
      aiCandidates: [],
      aiStats: {
        pending_count: 0,
        approved_count: 0,
        approval_rate: 0,
        edit_rate: 0
      },
      editingCandidates: {},
      editForms: {},

      loading: false
    };
  },

  mounted() {
    this.loadAICandidates();
    this.loadAIStats();
  },

  methods: {
    // ===== AI 候選方法 =====
    async loadAICandidates() {
      this.loading = true;
      try {
        const response = await axios.get('http://localhost:8100/api/v1/knowledge-candidates/pending', {
          params: { limit: 50 }
        });
        this.aiCandidates = response.data.candidates;
        this.updateTotalCount();
      } catch (error) {
        console.error('載入 AI 候選失敗:', error);
        alert('載入 AI 候選失敗');
      } finally {
        this.loading = false;
      }
    },

    async loadAIStats() {
      try {
        const response = await axios.get('http://localhost:8100/api/v1/knowledge-candidates/stats');
        this.aiStats = response.data;
        this.updateTotalCount();
      } catch (error) {
        console.error('載入 AI 統計失敗:', error);
      }
    },

    getConfidenceClass(score) {
      if (score >= 0.8) return 'confidence-high';
      if (score >= 0.6) return 'confidence-medium';
      return 'confidence-low';
    },

    startAIEdit(candidate) {
      this.editingCandidates[candidate.id] = true;
      this.editForms[candidate.id] = {
        question: candidate.question,
        answer: candidate.generated_answer,
        edit_summary: ''
      };
    },

    cancelAIEdit(candidateId) {
      delete this.editingCandidates[candidateId];
      delete this.editForms[candidateId];
    },

    async saveAIEdit(candidateId) {
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
        this.cancelAIEdit(candidateId);
        this.loadAICandidates();
      } catch (error) {
        console.error('儲存編輯失敗:', error);
        alert('儲存編輯失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    async approveAICandidate(candidate) {
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

        // 清除測試題庫管理頁面的 localStorage 記錄
        this.clearPendingGenerationStatus(candidate.test_scenario_id);

        this.loadAICandidates();
        this.loadAIStats();
      } catch (error) {
        console.error('批准失敗:', error);
        alert('批准失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    async rejectAICandidate(candidate) {
      if (!confirm('確定要拒絕此候選知識嗎？')) return;

      try {
        await axios.post(
          `http://localhost:8100/api/v1/knowledge-candidates/${candidate.id}/review`,
          {
            action: 'reject',
            reviewer_name: 'admin',
            review_notes: '已拒絕'
          }
        );
        alert('✅ 已拒絕該候選');

        // 清除測試題庫管理頁面的 localStorage 記錄
        this.clearPendingGenerationStatus(candidate.test_scenario_id);

        this.loadAICandidates();
        this.loadAIStats();
      } catch (error) {
        console.error('拒絕失敗:', error);
        alert('拒絕失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    // ===== 共用方法 =====
    clearPendingGenerationStatus(scenarioId) {
      // 清除測試題庫管理頁面中對應情境的 localStorage 記錄
      try {
        const pendingScenarios = JSON.parse(localStorage.getItem('pendingKnowledgeGeneration') || '{}');
        if (pendingScenarios[scenarioId]) {
          delete pendingScenarios[scenarioId];
          localStorage.setItem('pendingKnowledgeGeneration', JSON.stringify(pendingScenarios));
          console.log(`✅ 已清除測試情境 #${scenarioId} 的生成中狀態`);
        }
      } catch (error) {
        console.error('清除 localStorage 失敗:', error);
      }
    },

    updateTotalCount() {
      this.$emit('update-count', {
        tab: 'knowledge',
        count: this.aiStats.pending_count
      });
    }
  }
};
</script>

<style scoped>
.knowledge-review-tab {
  width: 100%;
}

/* 頁面標題 */
.page-title {
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 2px solid #e9ecef;
}

.page-title h3 {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 700;
  color: #2c3e50;
}

.page-title .subtitle {
  margin: 0;
  font-size: 14px;
  color: #666;
}

/* 內容區域 */
.content-area {
  width: 100%;
}

/* 頂部操作 */
.top-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 20px;
}

.btn-refresh {
  padding: 8px 16px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-refresh:hover:not(:disabled) {
  background: #5568d3;
  transform: translateY(-1px);
}

.btn-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 統計卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: white;
  border: none;
  border-radius: 16px;
  padding: 24px;
  text-align: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.stat-title {
  font-size: 14px;
  color: #999;
  margin-bottom: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  color: #303133;
  line-height: 1;
}

.stat-value.warning {
  color: #e6a23c;
  text-shadow: 0 2px 4px rgba(230, 162, 60, 0.2);
}
.stat-value.success {
  color: #67c23a;
  text-shadow: 0 2px 4px rgba(103, 194, 58, 0.2);
}
.stat-value.muted {
  color: #909399;
}
.stat-value.info {
  color: #409eff;
  text-shadow: 0 2px 4px rgba(64, 158, 255, 0.2);
}

/* 載入狀態 */
.loading-indicator {
  text-align: center;
  padding: 60px 20px;
}

.spinner {
  width: 40px;
  height: 40px;
  margin: 0 auto 20px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 空狀態 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.empty-state h3 {
  margin: 0 0 15px 0;
  font-size: 20px;
  color: #333;
}

.empty-state p {
  margin: 10px 0;
  font-size: 14px;
  line-height: 1.6;
}

/* AI 候選卡片 */
.candidates-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.candidate-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  overflow: hidden;
  border: 1px solid #e9ecef;
  transition: all 0.3s;
}

.candidate-card:hover {
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.15);
  border-color: #667eea;
  transform: translateY(-2px);
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

.candidate-content {
  padding: 20px;
}

.section {
  margin-bottom: 20px;
}

.section:last-child {
  margin-bottom: 0;
}

.section h5 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #666;
  font-weight: 600;
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

.warnings-section h5 {
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

.candidate-actions {
  padding: 20px;
  background: linear-gradient(180deg, #f8f9fa 0%, #ffffff 100%);
  border-top: 1px solid #e9ecef;
}

.review-actions, .edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

/* 按鈕 */
.btn {
  padding: 11px 20px;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  white-space: nowrap;
}

.btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.btn:active:not(:disabled) {
  transform: translateY(0);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none !important;
}

.btn-edit {
  background: linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%);
  color: white;
}

.btn-edit:hover:not(:disabled) {
  background: linear-gradient(135deg, #7f8c8d 0%, #6c7a7b 100%);
}

.btn-approve {
  background: linear-gradient(135deg, #67c23a 0%, #5daf34 100%);
  color: white;
}

.btn-approve:hover:not(:disabled) {
  background: linear-gradient(135deg, #5daf34 0%, #529b2e 100%);
}

.btn-reject {
  background: linear-gradient(135deg, #f56c6c 0%, #f45454 100%);
  color: white;
}

.btn-reject:hover:not(:disabled) {
  background: linear-gradient(135deg, #f45454 0%, #e84242 100%);
}

.btn-secondary {
  background: #e9ecef;
  color: #495057;
}

.btn-secondary:hover:not(:disabled) {
  background: #d3d9df;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #5568d3 0%, #64398f 100%);
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
</style>
