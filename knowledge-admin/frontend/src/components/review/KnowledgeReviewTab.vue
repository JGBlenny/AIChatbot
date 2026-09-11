<template>
  <div class="knowledge-review-tab">
    <!-- 頁面標題 -->
    <div class="page-title">
      <h3>🤖 AI 知識候選審核</h3>
      <p class="subtitle">審核 AI 自動生成的知識候選答案</p>
    </div>

    <!-- AI 知識候選區域 -->
    <div class="content-area">
      <!-- 篩選模式提示 -->
      <div v-if="isFilterMode" class="filter-mode-banner">
        <div class="filter-info">
          <span class="filter-icon">🔍</span>
          <span class="filter-text">
            正在顯示 <strong>{{ filteredCandidates.length }}</strong> 個指定的候選知識
          </span>
        </div>
        <button @click="clearFilter" class="btn-clear-filter">
          查看全部 ({{ aiCandidates.length }})
        </button>
      </div>

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
      <div v-else-if="filteredCandidates.length === 0 && !isFilterMode" class="empty-state">
        <div class="empty-icon">🎉</div>
        <h3>目前沒有待審核的 AI 知識候選</h3>
        <p>您可以在「測試題庫管理」頁面為已批准且無知識的測試情境生成知識</p>
      </div>

      <!-- 篩選模式下找不到候選 -->
      <div v-else-if="filteredCandidates.length === 0 && isFilterMode" class="empty-state">
        <div class="empty-icon">🔍</div>
        <h3>找不到指定的候選知識</h3>
        <p>候選可能已被審核或不存在</p>
        <button @click="clearFilter" class="btn-primary">查看全部候選</button>
      </div>

      <!-- AI 候選列表 -->
      <div v-else class="candidates-list">
        <div
          v-for="candidate in filteredCandidates"
          :key="'ai-' + candidate.id"
          :id="`ai-candidate-${candidate.id}`"
          :class="['candidate-card', { 'highlighted': highlightCandidateId === candidate.id }]"
        >
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
              <h5>❓ AI 生成的問題 <span v-if="candidate.edited_question" class="edit-badge">已編輯</span></h5>
              <textarea
                v-if="editingCandidates[candidate.id]"
                v-model="editForms[candidate.id].question"
                rows="2"
                class="edit-textarea"
              ></textarea>
              <p v-else class="generated-question">{{ candidate.edited_question || candidate.question }}</p>
            </div>

            <!-- AI 生成的答案 -->
            <div class="section">
              <h5>💡 AI 生成的答案 <span v-if="candidate.edited_answer" class="edit-badge">已編輯</span></h5>
              <textarea
                v-if="editingCandidates[candidate.id]"
                v-model="editForms[candidate.id].answer"
                rows="8"
                class="edit-textarea"
              ></textarea>
              <p v-else class="generated-answer">{{ candidate.edited_answer || candidate.generated_answer }}</p>
            </div>

            <!-- 警告 -->
            <div v-if="candidate.warnings && candidate.warnings.length > 0" class="warnings-section">
              <h5>⚠️ AI 警告</h5>
              <ul class="warnings-list">
                <li v-for="(warning, idx) in candidate.warnings" :key="idx">{{ warning }}</li>
              </ul>
            </div>

            <!-- 推薦意圖 -->
            <div v-if="candidateIntents[candidate.id]" class="intent-section">
              <h5>🎯 推薦意圖</h5>
              <div class="intent-info">
                <div class="intent-row">
                  <span class="intent-label">意圖名稱：</span>
                  <span class="intent-value">{{ candidateIntents[candidate.id].intent_name }}</span>
                </div>
                <div class="intent-row">
                  <span class="intent-label">意圖 ID：</span>
                  <span class="intent-value">{{ candidateIntents[candidate.id].intent_id }}</span>
                </div>
                <div class="intent-row">
                  <span class="intent-label">信心度：</span>
                  <span class="intent-confidence" :class="getIntentConfidenceClass(candidateIntents[candidate.id].confidence)">
                    {{ candidateIntents[candidate.id].confidence }}
                  </span>
                </div>
                <div v-if="candidateIntents[candidate.id].reasoning !== '無'" class="intent-reasoning">
                  <span class="intent-label">推薦理由：</span>
                  <span class="intent-reasoning-text">{{ candidateIntents[candidate.id].reasoning }}</span>
                </div>
              </div>
            </div>

            <!-- 來源資訊 -->
            <div v-if="candidate.suggested_sources && candidate.suggested_sources.length > 0" class="source-section">
              <h5>📄 來源檔案</h5>
              <div class="source-info">
                <span class="source-badge" v-for="(source, idx) in candidate.suggested_sources" :key="idx">
                  {{ getCleanFileName(source) }}
                </span>
              </div>
            </div>

            <!-- 生成資訊（用於偵錯） -->
            <div v-if="candidate.generation_prompt" class="generation-info">
              <details>
                <summary style="cursor: pointer; color: #6c757d; font-size: 0.9em;">🔍 查看詳細生成資訊</summary>
                <div class="generation-details">
                  <p><strong>生成提示：</strong> {{ candidate.generation_prompt }}</p>
                  <p v-if="candidate.generation_reasoning"><strong>生成推理：</strong></p>
                  <pre v-if="candidate.generation_reasoning" class="reasoning-text">{{ candidate.generation_reasoning }}</pre>
                </div>
              </details>
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
import { API_ENDPOINTS } from '@/config/api';

export default {
  name: 'KnowledgeReviewTab',

  props: {
    candidateId: {
      type: Number,
      default: null
    }
  },

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

      loading: false,
      highlightCandidateId: null  // 需要高亮的候選 ID
    };
  },

  watch: {
    candidateId(newId) {
      if (newId) {
        this.highlightCandidateId = newId;
        // 延遲滾動，等待列表載入完成
        setTimeout(() => {
          this.scrollToCandidate(newId);
        }, 800);
      }
    }
  },

  computed: {
    // 過濾後的候選列表
    filteredCandidates() {
      if (!this.candidateId) {
        // 沒有指定 ID，返回所有候選
        return this.aiCandidates;
      }

      // 解析候選 ID（支援單個或逗號分隔的多個）
      const candidateIds = String(this.candidateId).split(',').map(id => parseInt(id.trim()));

      // 過濾候選列表
      return this.aiCandidates.filter(candidate => candidateIds.includes(candidate.id));
    },

    // 是否為篩選模式
    isFilterMode() {
      return this.candidateId !== null && this.candidateId !== undefined;
    },

    // 解析每個候選的推薦意圖資訊
    candidateIntents() {
      const intents = {};
      this.aiCandidates.forEach(candidate => {
        if (candidate.generation_reasoning) {
          const intentMatch = candidate.generation_reasoning.match(/【推薦意圖】\n意圖 ID: (.+?)\n意圖名稱: (.+?)\n信心度: (.+?)\n推薦理由: (.+?)(?:\n\n|$)/s);
          if (intentMatch) {
            intents[candidate.id] = {
              intent_id: intentMatch[1].trim(),
              intent_name: intentMatch[2].trim(),
              confidence: intentMatch[3].trim(),
              reasoning: intentMatch[4].trim()
            };
          }
        }
      });
      return intents;
    }
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
        const response = await axios.get(API_ENDPOINTS.knowledgeCandidatesPending, {
          params: { limit: 100 }
        });

        // 按建立時間排序，最新的在最上面
        this.aiCandidates = response.data.candidates.sort((a, b) => {
          return new Date(b.created_at) - new Date(a.created_at);
        });

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
        const response = await axios.get(API_ENDPOINTS.knowledgeCandidatesStats);
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

    getCleanFileName(fullPath) {
      // 移除 UUID 前綴（格式：xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx_filename.ext）
      const fileName = fullPath.split('/').pop(); // 取得檔名
      const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_/i;
      return fileName.replace(uuidPattern, '');
    },

    getIntentConfidenceClass(confidence) {
      const score = parseFloat(confidence);
      if (score >= 0.8) return 'confidence-high';
      if (score >= 0.6) return 'confidence-medium';
      return 'confidence-low';
    },

    startAIEdit(candidate) {
      // 使用 Object.assign 確保響應式更新
      // 優先使用已編輯的版本，如果沒有則使用原始版本
      this.editForms = Object.assign({}, this.editForms, {
        [candidate.id]: {
          question: candidate.edited_question || candidate.question,
          answer: candidate.edited_answer || candidate.generated_answer
        }
      });

      this.editingCandidates = Object.assign({}, this.editingCandidates, {
        [candidate.id]: true
      });
    },

    cancelAIEdit(candidateId) {
      // 使用 Object.assign 確保響應式更新
      const newEditingCandidates = Object.assign({}, this.editingCandidates);
      delete newEditingCandidates[candidateId];
      this.editingCandidates = newEditingCandidates;

      const newEditForms = Object.assign({}, this.editForms);
      delete newEditForms[candidateId];
      this.editForms = newEditForms;
    },

    async saveAIEdit(candidateId) {
      const form = this.editForms[candidateId];

      try {
        await axios.put(API_ENDPOINTS.knowledgeCandidateEdit(candidateId), {
          edited_question: form.question,
          edited_answer: form.answer
        });
        alert('✅ 編輯已儲存！');
        this.cancelAIEdit(candidateId);
        this.loadAICandidates();
      } catch (error) {
        console.error('儲存編輯失敗:', error);

        // 處理 Pydantic 驗證錯誤（detail 是數組）
        let errorMsg = '儲存編輯失敗';
        if (error.response?.data?.detail) {
          const detail = error.response.data.detail;
          if (Array.isArray(detail)) {
            // Pydantic 驗證錯誤
            errorMsg += '：\n' + detail.map(err => {
              const field = err.loc ? err.loc[err.loc.length - 1] : 'unknown';
              return `- ${field}: ${err.msg}`;
            }).join('\n');
          } else if (typeof detail === 'string') {
            errorMsg += '：' + detail;
          } else {
            errorMsg += '：' + JSON.stringify(detail);
          }
        } else if (error.message) {
          errorMsg += '：' + error.message;
        }

        alert(errorMsg);
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
          API_ENDPOINTS.knowledgeCandidateReview(candidate.id),
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
          API_ENDPOINTS.knowledgeCandidateReview(candidate.id),
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
    },

    scrollToCandidate(candidateId) {
      // 滾動到指定的候選知識卡片
      const element = document.getElementById(`ai-candidate-${candidateId}`);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // 3秒後移除高亮
        setTimeout(() => {
          this.highlightCandidateId = null;
        }, 3000);
      } else {
        // 找不到該候選，可能不在 pending 列表中
        console.warn(`候選 #${candidateId} 不在當前列表中`);
        alert(`候選 #${candidateId} 不在待審核列表中，可能已被審核。`);
        this.highlightCandidateId = null;
      }
    },

    clearFilter() {
      // 清除篩選，返回審核中心首頁
      this.$router.push('/review-center');
    }
  }
};
</script>

<style scoped>
.knowledge-review-tab {
  width: 100%;
}

/* 篩選模式橫幅 */
.filter-mode-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  margin-bottom: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  animation: slideDown 0.3s ease-out;
}

.filter-info {
  display: flex;
  align-items: center;
  gap: 12px;
  color: white;
}

.filter-icon {
  font-size: 24px;
}

.filter-text {
  font-size: 15px;
  font-weight: 500;
}

.filter-text strong {
  font-weight: 700;
  font-size: 18px;
}

.btn-clear-filter {
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 2px solid white;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  backdrop-filter: blur(10px);
}

.btn-clear-filter:hover {
  background: white;
  color: #667eea;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
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
  align-items: center;
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

.candidate-card.highlighted {
  border-color: #667eea;
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.2), 0 4px 12px rgba(0,0,0,0.1);
  animation: pulse-highlight 2s ease-in-out;
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

/* 意圖多選複選框 */
.intent-checkboxes {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 400px;
  overflow-y: auto;
  padding: 10px;
  background: #fafafa;
  border-radius: 6px;
  border: 2px solid #e0e0e0;
}

.intent-checkbox-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: white;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.intent-checkbox-item:hover {
  border-color: #9c27b0;
  background: #f9f5fb;
}

.intent-checkbox-item.checked {
  border-color: #9c27b0;
  background: #f3e5f5;
  box-shadow: 0 2px 4px rgba(156, 39, 176, 0.2);
}

.intent-checkbox-item input[type="checkbox"] {
  margin-top: 2px;
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #9c27b0;
}

.intent-checkbox-label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.intent-checkbox-label strong {
  color: #7b1fa2;
  font-size: 14px;
}

.intent-desc {
  color: #666;
  font-size: 13px;
  line-height: 1.4;
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

/* 推薦意圖區塊 */
.intent-section {
  background: #f3e5f5;
  padding: 15px;
  border-radius: 6px;
  border-left: 4px solid #9c27b0;
  margin-top: 15px;
}

.intent-section h5 {
  color: #7b1fa2;
  margin-bottom: 12px;
  font-size: 14px;
}

.intent-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.intent-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.intent-label {
  font-weight: 600;
  color: #6a1b9a;
  min-width: 80px;
}

.intent-value {
  color: #4a148c;
  font-weight: 500;
}

.intent-confidence {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.intent-confidence.confidence-high {
  background: #c8e6c9;
  color: #2e7d32;
}

.intent-confidence.confidence-medium {
  background: #fff9c4;
  color: #f57f17;
}

.intent-confidence.confidence-low {
  background: #ffcdd2;
  color: #c62828;
}

.intent-reasoning {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 4px;
}

.intent-reasoning-text {
  color: #6a1b9a;
  font-size: 13px;
  line-height: 1.5;
  padding-left: 80px;
}

/* 來源資訊區塊 */
.source-section {
  background: #e3f2fd;
  padding: 15px;
  border-radius: 6px;
  border-left: 4px solid #2196f3;
  margin-top: 15px;
}

.source-section h5 {
  color: #1565c0;
  margin-bottom: 10px;
  font-size: 14px;
}

.source-info {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.source-badge {
  background: #2196f3;
  color: white;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

/* 生成資訊區塊 */
.generation-info {
  margin-top: 15px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 6px;
  border: 1px solid #dee2e6;
}

.generation-details {
  margin-top: 10px;
  padding: 10px;
  background: white;
  border-radius: 4px;
}

.generation-details p {
  margin: 8px 0;
  color: #495057;
  font-size: 13px;
}

.reasoning-text {
  background: #f1f3f5;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  color: #495057;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 200px;
  overflow-y: auto;
  margin: 8px 0;
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

/* 高亮動畫 */
@keyframes pulse-highlight {
  0%, 100% {
    box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.2), 0 4px 12px rgba(0,0,0,0.1);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(102, 126, 234, 0.4), 0 4px 16px rgba(102, 126, 234, 0.3);
  }
}

/* 已編輯徽章 */
.edit-badge {
  display: inline-block;
  padding: 2px 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  margin-left: 8px;
  vertical-align: middle;
}
</style>
