<template>
  <div>
    <h2>💡 建議意圖審核</h2>

    <!-- 統計資訊 -->
    <div v-if="stats" class="stats-cards">
      <div class="stat-card">
        <div class="stat-title">待審核</div>
        <div class="stat-value warning">{{ stats.pending }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">已採納</div>
        <div class="stat-value success">{{ stats.approved }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">已拒絕</div>
        <div class="stat-value muted">{{ stats.rejected }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">已合併</div>
        <div class="stat-value">{{ stats.merged }}</div>
      </div>
    </div>

    <!-- 工具列 -->
    <div class="toolbar">
      <select v-model="filterStatus" @change="loadSuggestions">
        <option value="">全部狀態</option>
        <option value="pending">待審核</option>
        <option value="approved">已採納</option>
        <option value="rejected">已拒絕</option>
        <option value="merged">已合併</option>
      </select>
      <select v-model="orderBy" @change="loadSuggestions">
        <option value="frequency">按頻率排序</option>
        <option value="latest">按時間排序</option>
        <option value="score">按分數排序</option>
      </select>
    </div>

    <!-- 建議列表 -->
    <div v-if="loading" class="loading"><p>載入中...</p></div>

    <div v-else-if="suggestionList.length === 0" class="empty-state">
      <p>沒有建議意圖</p>
    </div>

    <div v-else class="suggestions-grid">
      <div v-for="suggestion in suggestionList" :key="suggestion.id" class="suggestion-card">
        <div class="suggestion-header">
          <h3>{{ suggestion.suggested_name }}</h3>
          <span class="badge" :class="'status-' + suggestion.status">{{ getStatusLabel(suggestion.status) }}</span>
        </div>

        <div class="suggestion-body">
          <div class="info-row">
            <span class="label">類型:</span>
            <span class="badge" :class="'type-' + suggestion.suggested_type">{{ getTypeLabel(suggestion.suggested_type) }}</span>
          </div>

          <div class="info-row">
            <span class="label">描述:</span>
            <span>{{ suggestion.suggested_description }}</span>
          </div>

          <div class="info-row">
            <span class="label">關鍵字:</span>
            <span class="keywords">{{ (suggestion.suggested_keywords || []).join(', ') }}</span>
          </div>

          <div class="info-row">
            <span class="label">觸發問題:</span>
            <span class="trigger-question">"{{ suggestion.trigger_question }}"</span>
          </div>

          <div class="info-row">
            <span class="label">相關性分數:</span>
            <span class="score" :class="getScoreClass(suggestion.relevance_score)">
              {{ (suggestion.relevance_score * 100).toFixed(0) }}%
            </span>
          </div>

          <div class="info-row">
            <span class="label">頻率:</span>
            <span>{{ suggestion.frequency }} 次</span>
          </div>

          <div v-if="suggestion.reasoning" class="reasoning">
            <span class="label">OpenAI 推理:</span>
            <p>{{ suggestion.reasoning }}</p>
          </div>

          <div v-if="suggestion.reviewed_by" class="review-info">
            <span class="label">審核人:</span>
            <span>{{ suggestion.reviewed_by }}</span>
            <span v-if="suggestion.review_note" class="review-note"> - {{ suggestion.review_note }}</span>
          </div>
        </div>

        <div v-if="suggestion.status === 'pending'" class="suggestion-actions">
          <button @click="approve(suggestion)" class="btn-success">✓ 採納</button>
          <button @click="reject(suggestion)" class="btn-danger">✗ 拒絕</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

const RAG_API = 'http://localhost:8100/api/v1';

export default {
  name: 'SuggestedIntentsView',
  data() {
    return {
      suggestionList: [],
      filterStatus: '',
      orderBy: 'frequency',
      loading: false,
      stats: null
    };
  },
  mounted() {
    this.loadSuggestions();
    this.loadStats();
  },
  methods: {
    async loadSuggestions() {
      this.loading = true;
      try {
        const params = {};
        if (this.filterStatus) params.status = this.filterStatus;
        params.order_by = this.orderBy;

        const response = await axios.get(`${RAG_API}/suggested-intents`, { params });
        this.suggestionList = response.data.suggestions;
      } catch (error) {
        console.error('載入失敗', error);
        alert('載入失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },

    async loadStats() {
      try {
        const response = await axios.get(`${RAG_API}/suggested-intents/stats`);
        this.stats = response.data;
      } catch (error) {
        console.error('載入統計失敗', error);
      }
    },

    async approve(suggestion) {
      const note = prompt('審核備註（可選）:');
      if (note === null) return; // 取消

      try {
        await axios.post(`${RAG_API}/suggested-intents/${suggestion.id}/approve`, {
          reviewed_by: 'admin',
          review_note: note || '已採納',
          create_intent: true
        });

        alert(`✅ 已採納建議「${suggestion.suggested_name}」並建立新意圖！`);
        this.loadSuggestions();
        this.loadStats();
      } catch (error) {
        alert('採納失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    async reject(suggestion) {
      const note = prompt('拒絕原因:');
      if (!note) return;

      try {
        await axios.post(`${RAG_API}/suggested-intents/${suggestion.id}/reject`, {
          reviewed_by: 'admin',
          review_note: note
        });

        alert(`✅ 已拒絕建議「${suggestion.suggested_name}」`);
        this.loadSuggestions();
        this.loadStats();
      } catch (error) {
        alert('拒絕失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    getStatusLabel(status) {
      const labels = {
        pending: '待審核',
        approved: '已採納',
        rejected: '已拒絕',
        merged: '已合併'
      };
      return labels[status] || status;
    },

    getTypeLabel(type) {
      const labels = {
        knowledge: '知識',
        data_query: '資料',
        action: '操作',
        hybrid: '混合'
      };
      return labels[type] || type;
    },

    getScoreClass(score) {
      if (score >= 0.8) return 'score-high';
      if (score >= 0.6) return 'score-medium';
      return 'score-low';
    }
  }
};
</script>

<style scoped>
.stats-cards {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
}

.stat-card {
  flex: 1;
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 15px;
  text-align: center;
}

.stat-title {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-value.warning { color: #E6A23C; }
.stat-value.success { color: #67C23A; }
.stat-value.muted { color: #909399; }

.suggestions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.suggestion-card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 20px;
}

.suggestion-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 2px solid #f0f0f0;
}

.suggestion-header h3 {
  margin: 0;
  font-size: 18px;
}

.badge.status-pending { background: #E6A23C; }
.badge.status-approved { background: #67C23A; }
.badge.status-rejected { background: #F56C6C; }
.badge.status-merged { background: #909399; }

.suggestion-body {
  margin-bottom: 15px;
}

.info-row {
  margin-bottom: 10px;
  font-size: 14px;
}

.info-row .label {
  font-weight: bold;
  color: #666;
  margin-right: 8px;
}

.trigger-question {
  font-style: italic;
  color: #409EFF;
}

.keywords {
  color: #67C23A;
}

.score {
  font-weight: bold;
}

.score-high { color: #67C23A; }
.score-medium { color: #E6A23C; }
.score-low { color: #F56C6C; }

.reasoning {
  background: #f8f9fa;
  padding: 10px;
  border-radius: 5px;
  margin-top: 10px;
}

.reasoning p {
  margin: 5px 0 0 0;
  font-size: 13px;
  color: #606266;
}

.review-info {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #eee;
  font-size: 13px;
  color: #909399;
}

.review-note {
  font-style: italic;
}

.suggestion-actions {
  display: flex;
  gap: 10px;
}
</style>
