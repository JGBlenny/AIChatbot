<template>
  <div>
    <h2>🎯 意圖管理</h2>

    <!-- 說明區塊 - 使用共用組件 -->
    <InfoPanel :config="helpTexts.intents" />

    <!-- 工具列 -->
    <div class="toolbar">
      <select v-model="filterType" @change="loadIntents">
        <option value="">全部類型</option>
        <option value="knowledge">知識查詢</option>
        <option value="data_query">資料查詢</option>
        <option value="action">操作請求</option>
        <option value="hybrid">混合型</option>
      </select>
      <select v-model="filterEnabled" @change="loadIntents">
        <option value="">全部狀態</option>
        <option value="true">已啟用</option>
        <option value="false">已停用</option>
      </select>
      <button @click="showCreateModal" class="btn-primary btn-sm">新增意圖</button>
    </div>

    <!-- 統計資訊 -->
    <div v-if="stats" class="stats-cards">
      <div class="stat-card">
        <div class="stat-title">總意圖數</div>
        <div class="stat-value">{{ stats.total_intents }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">已啟用</div>
        <div class="stat-value success">{{ stats.enabled_intents }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">已停用</div>
        <div class="stat-value muted">{{ stats.disabled_intents }}</div>
      </div>
    </div>

    <!-- 意圖列表 -->
    <div v-if="loading" class="loading"><p>載入中...</p></div>

    <div v-else class="knowledge-list">
      <table>
        <thead>
          <tr>
            <th width="50">ID</th>
            <th>名稱</th>
            <th width="100">類型</th>
            <th>描述</th>
            <th width="80">閾值</th>
            <th width="80">使用次數</th>
            <th width="60">狀態</th>
            <th width="200">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="intent in intentList" :key="intent.id">
            <td>{{ intent.id }}</td>
            <td><strong>{{ intent.name }}</strong></td>
            <td><span class="badge" :class="'type-' + intent.type">{{ getTypeLabel(intent.type) }}</span></td>
            <td>{{ intent.description }}</td>
            <td>{{ intent.confidence_threshold }}</td>
            <td>{{ intent.usage_count || 0 }}</td>
            <td>
              <span class="status" :class="intent.is_enabled ? 'enabled' : 'disabled'">
                {{ intent.is_enabled ? '✓ 啟用' : '✗ 停用' }}
              </span>
            </td>
            <td>
              <button @click="editIntent(intent)" class="btn-edit btn-sm">編輯</button>
              <button @click="toggleIntent(intent)" class="btn-sm" :class="intent.is_enabled ? 'btn-delete' : 'btn-success'">
                {{ intent.is_enabled ? '停用' : '啟用' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 編輯/新增 Modal -->
    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop style="max-width: 700px;">
        <h2>{{ editingItem ? '✏️ 編輯意圖' : '➕ 新增意圖' }}</h2>

        <form @submit.prevent="saveIntent">
          <div class="form-group">
            <label>名稱 *</label>
            <input v-model="formData.name" required placeholder="例如：退租流程" />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>類型 *</label>
              <select v-model="formData.type" required>
                <option value="">請選擇</option>
                <option value="knowledge">knowledge - 知識查詢</option>
                <option value="data_query">data_query - 資料查詢</option>
                <option value="action">action - 操作請求</option>
                <option value="hybrid">hybrid - 混合型</option>
              </select>
            </div>

            <div class="form-group">
              <label>信心度閾值 *</label>
              <input v-model.number="formData.confidence_threshold" type="number" step="0.01" min="0" max="1" required />
            </div>
          </div>

          <div class="form-group">
            <label>描述</label>
            <input v-model="formData.description" placeholder="描述這個意圖的用途" />
          </div>

          <div class="form-group">
            <label>關鍵字（用逗號分隔）</label>
            <input v-model="keywordsString" placeholder="退租, 解約, 搬離" />
          </div>

          <div class="form-group">
            <label>是否需要 API</label>
            <select v-model="formData.api_required">
              <option :value="false">否</option>
              <option :value="true">是</option>
            </select>
          </div>

          <div v-if="formData.api_required" class="form-row">
            <div class="form-group">
              <label>API 端點</label>
              <input v-model="formData.api_endpoint" placeholder="lease_system" />
            </div>

            <div class="form-group">
              <label>API 動作</label>
              <input v-model="formData.api_action" placeholder="get_contract" />
            </div>
          </div>

          <div class="form-actions">
            <button type="submit" class="btn-primary btn-sm" :disabled="saving">
              {{ saving ? '儲存中...' : '儲存' }}
            </button>
            <button type="button" @click="closeModal" class="btn-secondary btn-sm">取消</button>
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
import { API_BASE_URL } from '@/config/api';

const RAG_API = `${API_BASE_URL}/rag-api/v1`;

export default {
  name: 'IntentsView',
  components: {
    InfoPanel
  },
  data() {
    return {
      intentList: [],
      filterType: '',
      filterEnabled: '',
      showModal: false,
      editingItem: null,
      saving: false,
      loading: false,
      stats: null,
      formData: {
        name: '',
        type: '',
        description: '',
        keywords: [],
        confidence_threshold: 0.80,
        api_required: false,
        api_endpoint: '',
        api_action: '',
        created_by: 'admin'
      },
      keywordsString: '',
      helpTexts
    };
  },
  mounted() {
    this.loadIntents();
    this.loadStats();
  },
  methods: {
    async loadIntents() {
      this.loading = true;
      try {
        const params = {};
        if (this.filterType) params.intent_type = this.filterType;
        if (this.filterEnabled) params.enabled_only = this.filterEnabled === 'true';

        const response = await axios.get(`${RAG_API}/intents`, { params });
        this.intentList = response.data.intents;
      } catch (error) {
        console.error('載入失敗', error);
        alert('載入失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },

    async loadStats() {
      try {
        const response = await axios.get(`${RAG_API}/intents/stats`);
        this.stats = response.data;
      } catch (error) {
        console.error('載入統計失敗', error);
      }
    },

    showCreateModal() {
      this.editingItem = null;
      this.formData = {
        name: '',
        type: '',
        description: '',
        keywords: [],
        confidence_threshold: 0.80,
        priority: 0,
        api_required: false,
        api_endpoint: '',
        api_action: '',
        created_by: 'admin'
      };
      this.keywordsString = '';
      this.showModal = true;
    },

    editIntent(item) {
      this.editingItem = item;
      this.formData = {
        name: item.name,
        type: item.type,
        description: item.description || '',
        keywords: item.keywords || [],
        confidence_threshold: item.confidence_threshold,
        api_required: item.api_required,
        api_endpoint: item.api_endpoint || '',
        api_action: item.api_action || '',
        updated_by: 'admin'
      };
      this.keywordsString = (item.keywords || []).join(', ');
      this.showModal = true;
    },

    async saveIntent() {
      this.saving = true;

      try {
        this.formData.keywords = this.keywordsString
          .split(',')
          .map(k => k.trim())
          .filter(k => k);

        if (this.editingItem) {
          const response = await axios.put(`${RAG_API}/intents/${this.editingItem.id}`, this.formData);

          alert('✅ 意圖已更新！');
        } else {
          await axios.post(`${RAG_API}/intents`, this.formData);
          alert('✅ 意圖已新增！');
        }

        // 重新載入 IntentClassifier 的意圖配置
        await this.reloadIntentClassifier();

        this.closeModal();
        this.loadIntents();
        this.loadStats();
      } catch (error) {
        console.error('儲存失敗', error);
        alert('儲存失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.saving = false;
      }
    },

    async toggleIntent(intent) {
      try {
        await axios.patch(`${RAG_API}/intents/${intent.id}/toggle`, {
          is_enabled: !intent.is_enabled
        });
        alert(`✅ 意圖已${!intent.is_enabled ? '啟用' : '停用'}！`);

        // 重新載入 IntentClassifier 的意圖配置
        await this.reloadIntentClassifier();

        this.loadIntents();
        this.loadStats();
      } catch (error) {
        alert('操作失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    async reloadIntentClassifier() {
      try {
        await axios.post(`${RAG_API}/knowledge/reload`);
        console.log('✅ IntentClassifier 已重新載入意圖配置');
      } catch (error) {
        console.error('⚠️ 重新載入 IntentClassifier 失敗:', error);
        // 不阻斷主流程，只記錄錯誤
      }
    },

    closeModal() {
      this.showModal = false;
      this.editingItem = null;
    },

    getTypeLabel(type) {
      const labels = {
        knowledge: '知識',
        data_query: '資料',
        action: '操作',
        hybrid: '混合'
      };
      return labels[type] || type;
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

.stat-value.success {
  color: #67C23A;
}

.stat-value.muted {
  color: #909399;
}

.status.enabled {
  color: #67C23A;
  font-weight: bold;
}

.status.disabled {
  color: #909399;
}

.badge.type-knowledge { background: #409EFF; color: white; }
.badge.type-data_query { background: #E6A23C; color: white; }
.badge.type-action { background: #F56C6C; color: white; }
.badge.type-hybrid { background: #67C23A; color: white; }
</style>
