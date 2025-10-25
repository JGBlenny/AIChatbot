<template>
  <div class="test-scenarios-view">
    <div class="page-header">
      <h2>🧪 測試題庫管理</h2>
      <div class="header-actions">
        <button @click="showCreateDialog = true" class="btn-primary">
          ➕ 新增測試情境
        </button>
        <button @click="refreshData" class="btn-secondary">
          🔄 重新整理
        </button>
      </div>
    </div>

    <!-- 篩選區域 -->
    <div class="filter-section">
      <div class="filter-group">
        <label>難度：</label>
        <select v-model="filters.difficulty" @change="loadScenarios">
          <option value="">全部難度</option>
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </select>
      </div>

      <div class="filter-group">
        <label>狀態：</label>
        <select v-model="filters.status" @change="loadScenarios">
          <option value="approved">已批准</option>
          <option value="pending_review">待審核</option>
          <option value="draft">草稿</option>
          <option value="rejected">已拒絕</option>
        </select>
      </div>

      <div class="filter-group">
        <label>搜尋：</label>
        <input
          v-model="filters.search"
          @input="debouncedSearch"
          placeholder="搜尋問題或分類..."
          class="search-input"
        />
      </div>
    </div>

    <!-- 統計區域 -->
    <div class="stats-section" v-if="stats">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_scenarios }}</div>
        <div class="stat-label">總測試數</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.by_status?.find(s => s.status === 'approved')?.count || 0 }}</div>
        <div class="stat-label">已批准</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.pending_review_count || 0 }}</div>
        <div class="stat-label">待審核</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.run_statistics?.overall_pass_rate?.toFixed(1) || 0 }}%</div>
        <div class="stat-label">通過率</div>
      </div>
    </div>

    <!-- 測試情境列表 -->
    <div class="scenarios-table" v-if="!loading">
      <table>
        <thead>
          <tr>
            <th width="5%">ID</th>
            <th width="30%">測試問題</th>
            <th width="8%">難度</th>
            <th width="8%">優先級</th>
            <th width="8%">狀態</th>
            <th width="10%">知識狀態</th>
            <th width="12%">統計</th>
            <th width="19%">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="scenario in scenarios" :key="scenario.id">
            <td>{{ scenario.id }}</td>
            <td class="question-cell">{{ scenario.test_question }}</td>
            <td>
              <span :class="['badge', 'badge-' + scenario.difficulty]">
                {{ scenario.difficulty }}
              </span>
            </td>
            <td>
              <span :class="['badge', priorityBadgeClass(scenario.priority)]">
                {{ priorityLabels[scenario.priority] }}
              </span>
            </td>
            <td>
              <span :class="['badge', 'badge-' + scenario.status]">
                {{ statusLabels[scenario.status] }}
              </span>
            </td>
            <td class="knowledge-status-cell">
              <span v-if="scenario.has_knowledge" class="badge badge-has-knowledge" :title="'已關聯知識 ID: ' + (scenario.linked_knowledge_ids || []).join(', ')">
                ✅ 已有知識
              </span>
              <span v-else class="badge badge-no-knowledge">
                ❌ 無知識
              </span>
            </td>
            <td class="stats-cell">
              <div v-if="scenario.total_runs > 0">
                <div>執行: {{ scenario.total_runs }}</div>
                <div>通過: {{ scenario.pass_count }}</div>
                <div class="pass-rate">{{ ((scenario.pass_count / scenario.total_runs) * 100).toFixed(0) }}%</div>
              </div>
              <div v-else class="no-stats">未執行</div>
            </td>
            <td class="actions-cell">
              <button @click="editScenario(scenario)" class="btn-sm btn-edit" title="編輯">
                ✏️
              </button>
              <button
                v-if="scenario.status === 'approved' && !scenario.has_knowledge && !generatingKnowledge[scenario.id]"
                @click="generateKnowledge(scenario)"
                class="btn-sm btn-ai"
                title="AI 生成知識"
              >
                🤖
              </button>
              <span
                v-if="scenario.status === 'approved' && !scenario.has_knowledge && generatingKnowledge[scenario.id]"
                class="btn-sm btn-pending"
                title="待審核中，請前往 AI 知識審核頁面"
              >
                ⏳
              </span>
              <button @click="deleteScenario(scenario.id)" class="btn-sm btn-delete" title="刪除">
                🗑️
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="scenarios.length === 0" class="empty-state">
        <p>😔 沒有找到測試情境</p>
        <p>請調整篩選條件或新增測試情境</p>
      </div>

      <!-- 分頁 -->
      <div class="pagination" v-if="total > limit">
        <button
          @click="prevPage"
          :disabled="offset === 0"
          class="btn-secondary"
        >
          ⬅️ 上一頁
        </button>
        <span class="page-info">
          第 {{ Math.floor(offset / limit) + 1 }} 頁 / 共 {{ Math.ceil(total / limit) }} 頁
          (總共 {{ total }} 筆)
        </span>
        <button
          @click="nextPage"
          :disabled="offset + limit >= total"
          class="btn-secondary"
        >
          下一頁 ➡️
        </button>
      </div>
    </div>

    <div v-else class="loading-state">
      <p>⏳ 載入中...</p>
    </div>

    <!-- 新增/編輯對話框 -->
    <div v-if="showCreateDialog || editingScenario" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h3>{{ editingScenario ? '編輯測試情境' : '新增測試情境' }}</h3>

        <form @submit.prevent="saveScenario">
          <div class="form-group">
            <label>測試問題 *</label>
            <textarea
              v-model="formData.test_question"
              required
              rows="3"
              placeholder="輸入要測試的問題..."
            ></textarea>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>難度 *</label>
              <select v-model="formData.difficulty" required>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>

            <div class="form-group">
              <label>優先級 *</label>
              <select v-model.number="formData.priority" required>
                <option :value="30">低優先級（30）</option>
                <option :value="50">中等優先級（50）</option>
                <option :value="80">高優先級（80）</option>
              </select>
              <small class="hint">優先級影響測試執行順序</small>
            </div>
          </div>

          <div class="form-group">
            <label>備註</label>
            <textarea
              v-model="formData.notes"
              rows="3"
              placeholder="其他說明..."
            ></textarea>
          </div>

          <div class="form-actions">
            <button type="button" @click="closeDialog" class="btn-secondary">
              取消
            </button>
            <button type="submit" class="btn-primary">
              {{ editingScenario ? '更新' : '建立' }}
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
  name: 'TestScenariosView',

  data() {
    return {
      scenarios: [],
      stats: null,
      loading: false,
      showCreateDialog: false,
      editingScenario: null,
      generatingKnowledge: {}, // 追蹤正在生成知識的測試情境 ID

      filters: {
        difficulty: '',
        status: 'approved',
        search: ''
      },

      limit: 50,
      offset: 0,
      total: 0,

      formData: {
        test_question: '',
        difficulty: 'medium',
        priority: 50,
        notes: ''
      },

      statusLabels: {
        'pending_review': '待審核',
        'approved': '已批准',
        'rejected': '已拒絕',
        'draft': '草稿'
      },

      priorityLabels: {
        30: '低',
        50: '中',
        80: '高'
      }
    };
  },

  mounted() {
    this.loadStats();
    this.loadScenarios();

    // 從 localStorage 恢復「待審核」狀態
    const pendingScenarios = JSON.parse(localStorage.getItem('pendingKnowledgeGeneration') || '{}');
    Object.keys(pendingScenarios).forEach(scenarioId => {
      this.generatingKnowledge[parseInt(scenarioId)] = true;
    });
  },

  methods: {
    async loadStats() {
      try {
        const response = await axios.get('/api/test/stats');
        this.stats = response.data;
      } catch (error) {
        console.error('載入統計失敗:', error);
      }
    },

    async loadScenarios() {
      this.loading = true;
      try {
        const params = {
          limit: this.limit,
          offset: this.offset
        };

        if (this.filters.difficulty) params.difficulty = this.filters.difficulty;
        if (this.filters.status) params.status = this.filters.status;
        if (this.filters.search) params.search = this.filters.search;

        const response = await axios.get('/api/test/scenarios', { params });
        this.scenarios = response.data.scenarios;
        this.total = response.data.total;
      } catch (error) {
        console.error('載入測試情境失敗:', error);
        alert('載入測試情境失敗');
      } finally {
        this.loading = false;
      }
    },

    debouncedSearch() {
      clearTimeout(this.searchTimeout);
      this.searchTimeout = setTimeout(() => {
        this.offset = 0;
        this.loadScenarios();
      }, 500);
    },

    editScenario(scenario) {
      this.editingScenario = scenario;
      this.formData = {
        test_question: scenario.test_question,
        difficulty: scenario.difficulty,
        priority: scenario.priority || 50,
        notes: scenario.notes || ''
      };
    },

    priorityBadgeClass(priority) {
      const classes = {
        30: 'badge-info',
        50: 'badge-active',
        80: 'badge-count'
      };
      return classes[priority] || 'badge-active';
    },

    async saveScenario() {
      try {
        const data = {
          test_question: this.formData.test_question,
          difficulty: this.formData.difficulty,
          priority: this.formData.priority,
          notes: this.formData.notes
        };

        if (this.editingScenario) {
          await axios.put(`/api/test/scenarios/${this.editingScenario.id}`, data);
          alert('測試情境已更新！');
        } else {
          await axios.post('/api/test/scenarios', data);
          alert('測試情境已建立！');
        }

        this.closeDialog();
        this.loadScenarios();
        this.loadStats();
      } catch (error) {
        console.error('儲存失敗:', error);
        alert('儲存失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    async deleteScenario(id) {
      if (!confirm('確定要刪除此測試情境嗎？')) return;

      try {
        await axios.delete(`/api/test/scenarios/${id}`);
        alert('測試情境已刪除！');
        this.loadScenarios();
        this.loadStats();
      } catch (error) {
        console.error('刪除失敗:', error);
        alert('刪除失敗');
      }
    },

    async generateKnowledge(scenario) {
      if (!confirm(`確定要為「${scenario.test_question}」生成知識嗎？\n\n這將使用 AI 生成 1-3 個候選答案供您審核。`)) {
        return;
      }

      // 立即標記為生成中，防止重複點擊
      this.generatingKnowledge[scenario.id] = true;

      try {
        // 先檢查是否已有知識
        const checkResponse = await axios.post(
          `/rag-api/v1/test-scenarios/${scenario.id}/check-knowledge`
        );

        if (checkResponse.data.has_knowledge) {
          alert(`此測試情境已有對應的知識（相似度 ${(checkResponse.data.highest_similarity * 100).toFixed(0)}%）\n\n關聯知識 ID: ${checkResponse.data.matched_knowledge_ids.join(', ')}`);
          // 已有知識，重置狀態
          delete this.generatingKnowledge[scenario.id];
          return;
        }

        // 生成知識候選
        const generateResponse = await axios.post(
          `/rag-api/v1/test-scenarios/${scenario.id}/generate-knowledge`,
          { num_candidates: 2 }
        );

        const result = generateResponse.data;

        // 將狀態儲存到 localStorage，以便刷新頁面後保持
        const pendingScenarios = JSON.parse(localStorage.getItem('pendingKnowledgeGeneration') || '{}');
        pendingScenarios[scenario.id] = {
          candidateIds: result.candidate_ids,
          generatedAt: new Date().toISOString()
        };
        localStorage.setItem('pendingKnowledgeGeneration', JSON.stringify(pendingScenarios));

        alert(`✅ ${result.message}\n\n候選 ID: ${result.candidate_ids.join(', ')}\n\n請前往「審核中心 > 知識庫審核」頁面查看並審核這些候選答案。`);

        // 重新整理列表
        this.loadScenarios();
      } catch (error) {
        console.error('生成知識失敗:', error);
        const errorMsg = error.response?.data?.detail || error.message;

        // 如果是「已有待審核候選」的錯誤，保持待審核狀態
        if (errorMsg.includes('待審核') || errorMsg.includes('候選')) {
          const pendingScenarios = JSON.parse(localStorage.getItem('pendingKnowledgeGeneration') || '{}');
          pendingScenarios[scenario.id] = {
            candidateIds: [],
            generatedAt: new Date().toISOString()
          };
          localStorage.setItem('pendingKnowledgeGeneration', JSON.stringify(pendingScenarios));
        } else {
          // 其他錯誤，重置狀態以允許重試
          delete this.generatingKnowledge[scenario.id];
        }

        alert('生成知識失敗：' + errorMsg);
      }
    },

    closeDialog() {
      this.showCreateDialog = false;
      this.editingScenario = null;
      this.formData = {
        test_question: '',
        difficulty: 'medium',
        priority: 50,
        notes: ''
      };
    },

    refreshData() {
      this.loadStats();
      this.loadScenarios();
    },

    nextPage() {
      if (this.offset + this.limit < this.total) {
        this.offset += this.limit;
        this.loadScenarios();
      }
    },

    prevPage() {
      if (this.offset > 0) {
        this.offset -= this.limit;
        this.loadScenarios();
      }
    }
  }
};
</script>

<style scoped>
.test-scenarios-view {
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

/* 篩選區域 */
.filter-section {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-bottom: 20px;
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-group label {
  font-weight: 600;
  color: #666;
  white-space: nowrap;
}

.filter-group select,
.search-input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.search-input {
  min-width: 250px;
}

/* 統計區域 */
.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
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

/* 表格樣式 */
.scenarios-table {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  overflow: hidden;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th {
  background: #f8f9fa;
  padding: 12px;
  text-align: left;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #e9ecef;
}

td {
  padding: 12px;
  border-bottom: 1px solid #e9ecef;
}

.question-cell {
  font-weight: 500;
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

.badge-approved { background: #d4edda; color: #155724; }
.badge-pending_review { background: #fff3cd; color: #856404; }
.badge-rejected { background: #f8d7da; color: #721c24; }
.badge-draft { background: #e2e3e5; color: #383d41; }

.badge-has-knowledge { background: #d4edda; color: #155724; }
.badge-no-knowledge { background: #f8d7da; color: #721c24; }

.stats-cell {
  font-size: 12px;
}

.pass-rate {
  font-weight: bold;
  color: #28a745;
}

.no-stats {
  color: #999;
  font-style: italic;
}

.actions-cell {
  white-space: nowrap;
}

/* 頁面專用按鈕樣式 */
.btn-ai {
  color: #667eea;
}

.btn-ai:hover {
  color: #5568d3;
}

.btn-pending {
  color: #ffc107;
  cursor: not-allowed;
  opacity: 0.8;
}

.btn-pending:hover {
  transform: none;
}

/* 空狀態 */
.empty-state, .loading-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

/* 分頁 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  padding: 20px;
  border-top: 1px solid #e9ecef;
}

.page-info {
  color: #666;
  font-size: 14px;
}

/* 對話框 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
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

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 30px;
}
</style>
