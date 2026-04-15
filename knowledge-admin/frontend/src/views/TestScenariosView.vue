<template>
  <div class="test-scenarios-view">
    <h2>🧪 測試題庫管理</h2>

    <!-- 說明區塊 -->
    <InfoPanel :config="helpTexts.testScenarios" />

    <div class="toolbar">
      <button @click="showCreateDialog = true" class="btn-primary btn-sm">
        ➕ 新增測試情境
      </button>
    </div>

    <!-- 篩選區域 -->
    <div class="filter-section">
      <div class="filter-group">
        <label>搜尋：</label>
        <input
          v-model="filters.search"
          type="text"
          placeholder="搜尋測試問題..."
          @input="onSearchInput"
          class="search-input"
        />
      </div>
      <div class="filter-group">
        <label>測試結果：</label>
        <select v-model="filters.testResult" @change="loadScenarios">
          <option value="">全部</option>
          <option value="passed">✅ 通過</option>
          <option value="failed">❌ 未通過</option>
          <option value="not_tested">⚪ 未測驗</option>
        </select>
      </div>
    </div>

    <!-- 統計區域 -->
    <div class="stats-section" v-if="stats">
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
            <th width="35%">測試問題</th>
            <th width="8%">難度</th>
            <th width="8%">優先級</th>
            <th width="8%">狀態</th>
            <th width="18%">最近測試</th>
            <th width="18%">操作</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="scenario in scenarios" :key="scenario.id">
            <tr>
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
              <td class="last-test-cell">
                <div v-if="scenario.last_run_at" class="test-result clickable" @click="toggleTestDetails(scenario.id)" :title="'點擊查看測試詳情'">
                  <div class="result-badge">
                    <span v-if="scenario.last_result === 'passed'" class="badge badge-passed" title="測試通過">
                      ✅ 通過
                    </span>
                    <span v-else-if="scenario.last_result === 'failed'" class="badge badge-failed" title="測試失敗">
                      ❌ 失敗
                    </span>
                    <span v-else class="badge badge-unknown">
                      ⚪ {{ scenario.last_result }}
                    </span>
                    <span class="expand-icon">{{ expandedScenario === scenario.id ? '▼' : '▶' }}</span>
                  </div>
                  <div class="test-meta">
                    <div class="score" v-if="scenario.avg_score" :title="'測試分數: ' + scenario.avg_score.toFixed(2)">
                      📊 {{ (scenario.avg_score * 100).toFixed(0) }}分
                    </div>
                    <div class="time" :title="scenario.last_run_at">
                      🕐 {{ formatRelativeTime(scenario.last_run_at) }}
                    </div>
                  </div>
                </div>
                <div v-else class="no-test clickable" @click="toggleTestDetails(scenario.id)" :title="'點擊展開生成 AI 知識'">
                  <span class="badge badge-no-test">未測試</span>
                  <span class="expand-icon">{{ expandedScenario === scenario.id ? '▼' : '▶' }}</span>
                </div>
              </td>
              <td class="actions-cell">
                <button @click="editScenario(scenario)" class="btn-edit btn-sm">
                  編輯
                </button>
                <button @click="deleteScenario(scenario.id)" class="btn-danger btn-sm" title="刪除">
                  刪除
                </button>
              </td>
            </tr>
            <!-- 測試詳情展開區 -->
            <tr v-if="expandedScenario === scenario.id" class="test-details-row">
              <td colspan="7" class="test-details-cell">
                <div v-if="loadingDetails" class="loading-details">
                  <span>⏳ 載入測試詳情...</span>
                </div>

                <!-- 未測試狀態：直接顯示 AI 生成區域 -->
                <div v-else-if="!scenario.last_run_at" class="no-test-details">
                  <div class="info-message">
                    <p>📝 此測試場景尚未執行測試</p>
                    <p>如果沒有對應的知識，可以使用 AI 生成知識候選</p>
                  </div>

                  <!-- AI 生成知識區域（未測試場景專用） -->
                  <div class="ai-generate-section">
                    <!-- 狀態 1: 已批准 - 顯示知識連結 -->
                    <div v-if="knowledgeStatus && knowledgeStatus.status === 'approved' && knowledgeStatus.knowledge_id" class="approved-knowledge">
                      <div class="status-badge badge-approved">✅ 已批准並建立知識</div>
                      <router-link :to="`/knowledge?ids=${knowledgeStatus.knowledge_id}`" class="knowledge-link">
                        <span class="knowledge-icon">📖</span>
                        <span>查看知識 #{{ knowledgeStatus.knowledge_id }}</span>
                      </router-link>
                    </div>

                    <!-- 狀態 2: 審核中 - 顯示審核中狀態 -->
                    <div v-else-if="knowledgeStatus && knowledgeStatus.status === 'pending_review'" class="pending-review">
                      <div class="status-badge badge-pending">⏳ 審核中</div>
                      <router-link :to="`/review-center?candidate_id=${knowledgeStatus.candidate_id}`" class="candidate-link">
                        前往審核頁面
                      </router-link>
                    </div>

                    <!-- 狀態 3: 已拒絕或無候選 - 顯示生成按鈕 -->
                    <div v-else>
                      <div v-if="knowledgeStatus && knowledgeStatus.status === 'rejected'" class="status-badge badge-rejected">
                        ❌ 已拒絕 - 可重新生成
                      </div>
                      <button
                        v-if="!generatingKnowledge[scenario.id]"
                        @click="generateKnowledge(scenario)"
                        class="btn-primary btn-ai-generate"
                      >
                        🤖 AI 生成知識
                      </button>
                      <div v-else class="generating-status">
                        ⏳ 正在生成知識，請稍後前往 AI 知識審核頁面查看...
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 已測試狀態：顯示測試詳情 -->
                <div v-else-if="testDetails.length > 0" class="test-details-container">
                  <h4>📊 上次測試詳情</h4>
                  <div class="detail-item">
                    <div class="detail-header">
                      <span :class="['result-icon', testDetails[0].passed ? 'passed' : 'failed']">
                        {{ testDetails[0].passed ? '✅' : '❌' }}
                      </span>
                      <span class="detail-time">{{ formatDetailTime(testDetails[0].tested_at) }}</span>
                      <span class="detail-score" v-if="testDetails[0].overall_score != null">
                        綜合評分: {{ (testDetails[0].overall_score * 100).toFixed(0) }}
                      </span>
                      <span class="detail-score" v-else-if="testDetails[0].score != null">
                        分數: {{ (testDetails[0].score * 100).toFixed(0) }}
                      </span>
                      <span class="detail-intent">意圖: {{ testDetails[0].actual_intent || '未識別' }}</span>
                      <span class="detail-confidence" v-if="testDetails[0].confidence != null">信心度: {{ (testDetails[0].confidence * 100).toFixed(0) }}%</span>
                    </div>
                    <div class="detail-sources" :class="{ 'no-sources': !testDetails[0].source_count || testDetails[0].source_count === 0 }">
                      <strong>📚 知識來源 ({{ testDetails[0].source_count || 0 }}個):</strong>

                      <!-- 有知識來源時顯示 -->
                      <div v-if="testDetails[0].source_count > 0 && testDetails[0].knowledge_sources" class="sources-list">
                        <div v-for="(source, index) in parseKnowledgeSources(testDetails[0].knowledge_sources)" :key="index" class="source-item">
                          <router-link :to="`/knowledge?ids=${source.id}`" class="source-id-link" :title="'點擊查看知識 #' + source.id">
                            <span class="source-id">{{ source.id }}</span>
                          </router-link>
                          <span class="source-text">{{ source.text }}</span>
                        </div>
                      </div>

                      <!-- 沒有知識來源時，根據候選狀態顯示不同 UI -->
                      <div v-if="(!testDetails[0].source_count || testDetails[0].source_count === 0) && (scenario.status === 'approved' || scenario.last_result === 'not_tested')" class="ai-generate-section">

                        <!-- 狀態 1: 已批准 - 顯示知識連結 -->
                        <div v-if="knowledgeStatus && knowledgeStatus.status === 'approved' && knowledgeStatus.knowledge_id" class="approved-knowledge">
                          <div class="status-badge badge-approved">✅ 已批准並建立知識</div>
                          <router-link :to="`/knowledge?ids=${knowledgeStatus.knowledge_id}`" class="knowledge-link">
                            <span class="knowledge-icon">📖</span>
                            <span>查看知識 #{{ knowledgeStatus.knowledge_id }}</span>
                          </router-link>
                        </div>

                        <!-- 狀態 2: 審核中 - 顯示審核中狀態 -->
                        <div v-else-if="knowledgeStatus && knowledgeStatus.status === 'pending_review'" class="pending-review">
                          <div class="status-badge badge-pending">⏳ 審核中</div>
                          <router-link :to="`/review-center?candidate_id=${knowledgeStatus.candidate_id}`" class="candidate-link">
                            前往審核頁面
                          </router-link>
                        </div>

                        <!-- 狀態 3: 已拒絕或無候選 - 顯示生成按鈕 -->
                        <div v-else>
                          <div v-if="knowledgeStatus && knowledgeStatus.status === 'rejected'" class="status-badge badge-rejected">
                            ❌ 已拒絕 - 可重新生成
                          </div>
                          <button
                            v-if="!generatingKnowledge[scenario.id]"
                            @click="generateKnowledge(scenario)"
                            class="btn-primary btn-ai-generate"
                          >
                            🤖 AI 生成知識
                          </button>
                          <div v-else class="generating-status">
                            ⏳ 正在生成知識，請稍後前往 AI 知識審核頁面查看...
                          </div>
                        </div>
                      </div>
                    </div>
                    <div class="detail-answer">
                      <strong>系統回答:</strong>
                      <p>{{ testDetails[0].system_answer || '無回答' }}</p>
                    </div>
                    <div v-if="testDetails[0].quality_reasoning" class="detail-reasoning">
                      <strong>評分原因:</strong>
                      <p>{{ testDetails[0].quality_reasoning }}</p>
                    </div>
                  </div>
                </div>
                <div v-else class="no-details">
                  <span>暫無測試詳情</span>
                </div>
              </td>
            </tr>
          </template>
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
import InfoPanel from '@/components/InfoPanel.vue';
import helpTexts from '@/config/help-texts.js';

export default {
  name: 'TestScenariosView',

  components: {
    InfoPanel
  },
  data() {
    return {
      helpTexts,
      scenarios: [],
      stats: null,
      loading: false,
      showCreateDialog: false,
      editingScenario: null,
      generatingKnowledge: {}, // 追蹤正在生成知識的測試情境 ID

      // 測試詳情相關
      expandedScenario: null,  // 當前展開的測試情境 ID
      testDetails: [],         // 測試詳情列表
      loadingDetails: false,   // 是否正在載入測試詳情
      knowledgeStatus: null,   // 知識候選狀態

      filters: {
        search: '',      // 搜尋測試問題文字
        testResult: '',  // 測試結果篩選：'' = 全部, 'passed' = 通過, 'failed' = 未通過, 'not_tested' = 未測驗
        status: 'approved'  // 固定只顯示已批准的測試情境
      },
      searchTimer: null,

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
          offset: this.offset,
          status: this.filters.status  // 固定傳遞 status 參數
        };

        if (this.filters.testResult) params.last_result = this.filters.testResult;
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

    onSearchInput() {
      clearTimeout(this.searchTimer);
      this.searchTimer = setTimeout(() => {
        this.offset = 0;
        this.loadScenarios();
      }, 300);
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
      if (!confirm(`確定要為「${scenario.test_question}」生成知識嗎？\n\n這將使用 AI 生成 1 個候選答案供您審核。`)) {
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
          { num_candidates: 1 }
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

        // 如果當前展開的就是這個測試情境，重新載入詳情
        if (this.expandedScenario === scenario.id) {
          const response = await axios.get(`/api/test/scenarios/${scenario.id}/results?limit=1`);
          this.testDetails = response.data.results || [];
          this.knowledgeStatus = response.data.knowledge_status || null;
        }
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
    },

    formatRelativeTime(timestamp) {
      if (!timestamp) return '';

      const now = new Date();
      const testTime = new Date(timestamp);
      const diffMs = now - testTime;
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffMins < 1) return '剛剛';
      if (diffMins < 60) return `${diffMins}分鐘前`;
      if (diffHours < 24) return `${diffHours}小時前`;
      if (diffDays === 1) return '昨天';
      if (diffDays < 7) return `${diffDays}天前`;
      if (diffDays < 30) return `${Math.floor(diffDays / 7)}週前`;
      if (diffDays < 365) return `${Math.floor(diffDays / 30)}個月前`;
      return `${Math.floor(diffDays / 365)}年前`;
    },

    formatDetailTime(timestamp) {
      if (!timestamp) return '';
      const date = new Date(timestamp);
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      return `${month}-${day} ${hours}:${minutes}`;
    },

    parseKnowledgeSources(sourcesStr) {
      if (!sourcesStr) return [];

      // 格式: "[498] 我沒有wifi" 或 "[495] 問題1; [444] 問題2"
      const sources = [];
      const parts = sourcesStr.split(';');

      parts.forEach(part => {
        const match = part.trim().match(/\[(\d+)\]\s*(.+)/);
        if (match) {
          sources.push({
            id: match[1],
            text: match[2].trim()
          });
        }
      });

      return sources;
    },

    async toggleTestDetails(scenarioId) {
      // 如果點擊的是已展開的項目，則收起
      if (this.expandedScenario === scenarioId) {
        this.expandedScenario = null;
        this.testDetails = [];
        this.knowledgeStatus = null;
        return;
      }

      // 展開新的項目
      this.expandedScenario = scenarioId;
      this.loadingDetails = true;
      this.testDetails = [];
      this.knowledgeStatus = null;

      try {
        // 只取最後一次測試記錄，同時獲取知識候選狀態
        const response = await axios.get(`/api/test/scenarios/${scenarioId}/results?limit=1`);
        this.testDetails = response.data.results || [];
        this.knowledgeStatus = response.data.knowledge_status || null;
      } catch (error) {
        console.error('載入測試詳情失敗:', error);
        alert('載入測試詳情失敗: ' + (error.response?.data?.detail || error.message));
        this.expandedScenario = null;
      } finally {
        this.loadingDetails = false;
      }
    }
  }
};
</script>

<style scoped>
.test-scenarios-view {
  /* width 由 app-main 統一管理 */
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

/* 測試結果樣式 */
.last-test-cell {
  font-size: 13px;
}

.test-result {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-badge {
  margin-bottom: 2px;
}

.badge-passed {
  background: #d4edda;
  color: #155724;
}

.badge-failed {
  background: #f8d7da;
  color: #721c24;
}

.badge-unknown {
  background: #e2e3e5;
  color: #383d41;
}

.badge-no-test {
  background: #ffeaa7;
  color: #856404;
}

.test-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: #666;
}

.test-meta .score {
  font-weight: 600;
  color: #667eea;
}

.test-meta .time {
  color: #999;
}

.no-test {
  color: #999;
  font-style: italic;
}

/* 可點擊樣式 */
.clickable {
  cursor: pointer;
  transition: background-color 0.2s;
}

.clickable:hover {
  background-color: #f8f9fa;
}

.expand-icon {
  margin-left: 6px;
  font-size: 10px;
  color: #999;
}

/* 測試詳情展開區 */
.test-details-row {
  background-color: #f8f9fa;
}

.test-details-cell {
  padding: 20px !important;
}

.loading-details {
  text-align: center;
  padding: 20px;
  color: #999;
}

.test-details-container {
  background: white;
  border-radius: 8px;
  padding: 20px;
}

.test-details-container h4 {
  margin: 0 0 16px 0;
  color: #333;
  font-size: 16px;
  border-bottom: 2px solid #667eea;
  padding-bottom: 8px;
}

.details-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: 600px;
  overflow-y: auto;
}

.detail-item {
  background: #f8f9fa;
  border-left: 4px solid #667eea;
  border-radius: 4px;
  padding: 12px;
}

.detail-item:hover {
  background: #e9ecef;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.result-icon {
  font-size: 16px;
}

.result-icon.passed {
  color: #28a745;
}

.result-icon.failed {
  color: #dc3545;
}

.detail-time {
  color: #666;
  font-size: 13px;
  font-weight: 500;
}

.detail-score,
.detail-intent,
.detail-confidence {
  background: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: #555;
}

.detail-score {
  font-weight: 600;
  color: #667eea;
}

.detail-sources {
  margin-top: 8px;
  padding: 10px;
  background: #e7f3ff;
  border-radius: 4px;
  border-left: 3px solid #667eea;
}

.detail-sources strong {
  display: block;
  margin-bottom: 8px;
  color: #333;
  font-size: 13px;
}

.detail-sources.no-sources {
  background: #fff3cd;
  border-left: 3px solid #ffc107;
}

.ai-generate-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #ffc107;
}

.btn-ai-generate {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.btn-ai-generate:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-ai-generate:active {
  transform: translateY(0);
}

.generating-status {
  padding: 10px 16px;
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 6px;
  color: #856404;
  font-size: 13px;
  font-weight: 500;
  text-align: center;
}

.status-badge {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
}

.status-badge.badge-approved {
  background: #d4edda;
  color: #155724;
}

.status-badge.badge-pending {
  background: #fff3cd;
  color: #856404;
}

.status-badge.badge-rejected {
  background: #f8d7da;
  color: #721c24;
}

.approved-knowledge,
.pending-review {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.knowledge-link,
.candidate-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: white;
  border: 2px solid #667eea;
  border-radius: 6px;
  color: #667eea;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.3s;
  align-self: flex-start;
}

.knowledge-link:hover,
.candidate-link:hover {
  background: #667eea;
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.knowledge-icon {
  font-size: 16px;
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.source-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: white;
  border-radius: 4px;
  font-size: 12px;
  transition: all 0.2s;
}

.source-item:hover {
  background: #f8f9fa;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.source-id-link {
  text-decoration: none;
  transition: transform 0.2s;
}

.source-id-link:hover {
  transform: scale(1.05);
}

.source-id-link:hover .source-id {
  background: #5568d3;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
}

.source-id {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  padding: 2px 8px;
  background: #667eea;
  color: white;
  border-radius: 12px;
  font-weight: 600;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
}

.source-text {
  flex: 1;
  color: #555;
  line-height: 1.4;
}

.detail-answer {
  margin-top: 8px;
  padding: 10px;
  background: white;
  border-radius: 4px;
}

.detail-answer strong {
  display: block;
  margin-bottom: 6px;
  color: #333;
  font-size: 13px;
}

.detail-answer p {
  margin: 0;
  line-height: 1.6;
  color: #555;
  font-size: 13px;
  white-space: pre-wrap;
}

.detail-reasoning {
  margin-top: 8px;
  padding: 10px;
  background: #fff3cd;
  border-radius: 4px;
  border-left: 3px solid #ffc107;
}

.detail-reasoning strong {
  display: block;
  margin-bottom: 6px;
  color: #856404;
  font-size: 13px;
}

.detail-reasoning p {
  margin: 0;
  line-height: 1.6;
  color: #856404;
  font-size: 12px;
}

.no-details {
  text-align: center;
  padding: 40px;
  color: #999;
  font-style: italic;
}

.actions-cell {
  white-space: nowrap;
}

/* 操作按鈕樣式 */
.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
  margin-right: 6px;
}

.btn-edit {
  background-color: #667eea;
  color: white;
}

.btn-edit:hover {
  background-color: #5568d3;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.btn-danger {
  background-color: #dc3545;
  color: white;
}

.btn-danger:hover {
  background-color: #c82333;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(220, 53, 69, 0.3);
}

.btn-danger:disabled {
  background-color: #e9ecef;
  color: #6c757d;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
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
