<template>
  <div class="intent-review-tab">
    <!-- 統計卡片 -->
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

    <!-- 篩選器 -->
    <div class="filter-toolbar">
      <select v-model="filterStatus" @change="loadSuggestions" class="filter-select">
        <option value="">全部狀態</option>
        <option value="pending">待審核</option>
        <option value="approved">已採納</option>
        <option value="rejected">已拒絕</option>
        <option value="merged">已合併</option>
      </select>
      <select v-model="orderBy" @change="loadSuggestions" class="filter-select">
        <option value="frequency">按頻率排序</option>
        <option value="latest">按時間排序</option>
        <option value="score">按分數排序</option>
      </select>
    </div>

    <!-- 載入狀態 -->
    <div v-if="loading" class="loading-state">
      <p>⏳ 載入中...</p>
    </div>

    <!-- 空狀態 -->
    <div v-else-if="suggestionList.length === 0" class="empty-state">
      <p>🎉 沒有待審核的意圖建議</p>
    </div>

    <!-- 建議列表 -->
    <div v-else class="suggestions-grid">
      <div v-for="suggestion in suggestionList" :key="suggestion.id" class="suggestion-card">
        <div class="card-header">
          <h3>{{ suggestion.suggested_name }}</h3>
          <span class="badge" :class="'status-' + suggestion.status">
            {{ getStatusLabel(suggestion.status) }}
          </span>
        </div>

        <div class="card-body">
          <div class="info-row">
            <span class="label">類型：</span>
            <span class="badge type-badge" :class="'type-' + suggestion.suggested_type">
              {{ getTypeLabel(suggestion.suggested_type) }}
            </span>
          </div>

          <div class="info-row">
            <span class="label">描述：</span>
            <span>{{ suggestion.suggested_description }}</span>
          </div>

          <div class="info-row">
            <span class="label">關鍵字：</span>
            <span class="keywords">{{ (suggestion.suggested_keywords || []).join(', ') }}</span>
          </div>

          <div class="info-row">
            <span class="label">觸發問題：</span>
            <span class="trigger-question">"{{ suggestion.trigger_question }}"</span>
          </div>

          <div class="info-row">
            <span class="label">相關性分數：</span>
            <span class="score" :class="getScoreClass(suggestion.relevance_score)">
              {{ (suggestion.relevance_score * 100).toFixed(0) }}%
            </span>
          </div>

          <div class="info-row">
            <span class="label">頻率：</span>
            <span>{{ suggestion.frequency }} 次</span>
          </div>

          <div v-if="suggestion.reasoning" class="reasoning-section">
            <span class="label">AI 推理：</span>
            <p>{{ suggestion.reasoning }}</p>
          </div>

          <div v-if="suggestion.reviewed_by" class="review-info">
            <span class="label">審核人：</span>
            <span>{{ suggestion.reviewed_by }}</span>
            <span v-if="suggestion.review_note" class="review-note"> - {{ suggestion.review_note }}</span>
          </div>
        </div>

        <div v-if="suggestion.status === 'pending'" class="card-actions">
          <button @click="approve(suggestion)" class="btn btn-approve">
            ✓ 採納
          </button>
          <button @click="reject(suggestion)" class="btn btn-reject">
            ✗ 拒絕
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { API_BASE_URL } from '@/config/api';

const RAG_API = `${API_BASE_URL}/rag-api/v1`;

export default {
  name: 'IntentReviewTab',

  emits: ['update-count'],

  data() {
    return {
      suggestionList: [],
      filterStatus: 'pending',  // 預設只顯示待審核
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

        // 通知父組件更新待審核數量
        this.$emit('update-count', {
          tab: 'intents',
          count: this.stats.pending || 0
        });
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
.intent-review-tab {
  width: 100%;
}

/* 統計卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
  margin-bottom: 25px;
}

.stat-card {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}

.stat-title {
  font-size: 14px;
  color: #666;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #303133;
}

.stat-value.warning { color: #e6a23c; }
.stat-value.success { color: #67c23a; }
.stat-value.muted { color: #909399; }

/* 篩選器 */
.filter-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 25px;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  cursor: pointer;
}

/* 建議卡片網格 */
.suggestions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.suggestion-card {
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 12px;
  padding: 20px;
  transition: all 0.3s;
}

.suggestion-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 2px solid #f0f0f0;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  color: white;
}

.badge.status-pending { background: #e6a23c; }
.badge.status-approved { background: #67c23a; }
.badge.status-rejected { background: #f56c6c; }
.badge.status-merged { background: #909399; }

.type-badge {
  background: #667eea !important;
  color: white !important;
}

.card-body {
  margin-bottom: 15px;
}

.info-row {
  margin-bottom: 12px;
  font-size: 14px;
  line-height: 1.6;
}

.info-row .label {
  font-weight: 600;
  color: #666;
  margin-right: 8px;
}

.trigger-question {
  font-style: italic;
  color: #409eff;
}

.keywords {
  color: #67c23a;
  font-weight: 500;
}

.score {
  font-weight: bold;
}

.score-high { color: #67c23a; }
.score-medium { color: #e6a23c; }
.score-low { color: #f56c6c; }

.reasoning-section {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 6px;
  margin-top: 10px;
}

.reasoning-section p {
  margin: 5px 0 0 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
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

/* 操作按鈕 */
.card-actions {
  display: flex;
  gap: 10px;
}

.btn {
  flex: 1;
  padding: 10px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-approve {
  background: #67c23a;
  color: white;
}

.btn-approve:hover {
  background: #529e2e;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.4);
}

.btn-reject {
  background: #f56c6c;
  color: white;
}

.btn-reject:hover {
  background: #d9534f;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(245, 108, 108, 0.4);
}

/* 狀態顯示 */
.loading-state,
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
  font-size: 16px;
}

.empty-state p {
  font-size: 18px;
}
</style>
