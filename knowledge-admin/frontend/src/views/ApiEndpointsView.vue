<template>
  <div>
    <h2>🔌 API Endpoints 管理</h2>

    <!-- 說明區塊 -->
    <div class="info-panel">
      <p>
        <strong>功能說明：</strong>
        管理系統中可用的 API endpoints。這些 API 會出現在知識庫管理和表單管理的下拉選單中。
      </p>
      <ul>
        <li>新增/編輯/刪除 API endpoint 選項</li>
        <li>設定 API 圖示、名稱、描述</li>
        <li>控制在知識庫/表單中的可見性</li>
        <li>調整顯示順序</li>
      </ul>
    </div>

    <!-- 工具列 -->
    <div class="toolbar">
      <select v-model="filterScope" @change="loadEndpoints">
        <option value="">全部範圍</option>
        <option value="knowledge">知識庫可用</option>
        <option value="form">表單可用</option>
      </select>
      <select v-model="filterStatus" @change="loadEndpoints">
        <option value="">全部狀態</option>
        <option value="true">已啟用</option>
        <option value="false">已停用</option>
      </select>
      <button @click="showCreateModal" class="btn-primary btn-sm">新增 API Endpoint</button>
    </div>

    <!-- 統計資訊 -->
    <div v-if="stats" class="stats-cards">
      <div class="stat-card">
        <div class="stat-title">總 API 數</div>
        <div class="stat-value">{{ stats.total }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">已啟用</div>
        <div class="stat-value success">{{ stats.active }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">知識庫可用</div>
        <div class="stat-value">{{ stats.knowledge }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">表單可用</div>
        <div class="stat-value">{{ stats.form }}</div>
      </div>
    </div>

    <!-- API Endpoints 列表 -->
    <div v-if="loading" class="loading"><p>載入中...</p></div>

    <div v-else-if="endpointList.length === 0" class="empty-state">
      <p>沒有找到 API Endpoint</p>
      <button @click="showCreateModal" class="btn-primary btn-sm" style="margin-top: 20px;">
        新增第一個 API Endpoint
      </button>
    </div>

    <div v-else class="knowledge-list">
      <table>
        <thead>
          <tr>
            <th width="50">ID</th>
            <th width="60">圖示</th>
            <th width="150">Endpoint ID</th>
            <th>名稱</th>
            <th>描述</th>
            <th width="80">知識庫</th>
            <th width="80">表單</th>
            <th width="80">順序</th>
            <th width="60">狀態</th>
            <th width="200">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="endpoint in endpointList" :key="endpoint.id">
            <td>{{ endpoint.id }}</td>
            <td style="text-align: center; font-size: 24px;">{{ endpoint.endpoint_icon }}</td>
            <td><code>{{ endpoint.endpoint_id }}</code></td>
            <td><strong>{{ endpoint.endpoint_name }}</strong></td>
            <td>{{ endpoint.description || '-' }}</td>
            <td style="text-align: center;">
              <span v-if="endpoint.available_in_knowledge" class="badge badge-success">✓</span>
              <span v-else class="badge badge-muted">✗</span>
            </td>
            <td style="text-align: center;">
              <span v-if="endpoint.available_in_form" class="badge badge-success">✓</span>
              <span v-else class="badge badge-muted">✗</span>
            </td>
            <td style="text-align: center;">{{ endpoint.display_order }}</td>
            <td>
              <span class="status" :class="endpoint.is_active ? 'enabled' : 'disabled'">
                {{ endpoint.is_active ? '✓' : '✗' }}
              </span>
            </td>
            <td>
              <button @click="editEndpoint(endpoint)" class="btn-edit btn-sm">編輯</button>
              <button @click="toggleEndpoint(endpoint)" class="btn-sm" :class="endpoint.is_active ? 'btn-secondary' : 'btn-success'">
                {{ endpoint.is_active ? '停用' : '啟用' }}
              </button>
              <button @click="deleteEndpoint(endpoint)" class="btn-delete btn-sm">刪除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 編輯/新增 Modal -->
    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop style="max-width: 800px;">
        <h2>{{ editingItem ? '✏️ 編輯 API Endpoint' : '➕ 新增 API Endpoint' }}</h2>

        <form @submit.prevent="saveEndpoint">
          <div class="form-row">
            <div class="form-group">
              <label>Endpoint ID * <small>(唯一識別碼，建議使用 snake_case)</small></label>
              <input
                v-model="formData.endpoint_id"
                required
                placeholder="例如：billing_inquiry"
                pattern="[a-z_]+"
                title="只能使用小寫英文和底線"
                :disabled="editingItem !== null"
              />
            </div>

            <div class="form-group">
              <label>圖示 * <small>(Emoji)</small></label>
              <input v-model="formData.endpoint_icon" required placeholder="🔌" maxlength="10" />
            </div>
          </div>

          <div class="form-group">
            <label>顯示名稱 *</label>
            <input v-model="formData.endpoint_name" required placeholder="例如：帳單查詢" />
          </div>

          <div class="form-group">
            <label>描述</label>
            <textarea v-model="formData.description" rows="2" placeholder="描述這個 API 的功能..."></textarea>
          </div>

          <div class="form-group">
            <label>業者 <small>(選填，留空表示全局可用)</small></label>
            <select v-model.number="formData.vendor_id">
              <option :value="null">全局可用</option>
              <option v-for="vendor in vendors" :key="vendor.id" :value="vendor.id">
                {{ vendor.short_name || vendor.name }} (ID: {{ vendor.id }})
              </option>
            </select>
          </div>

          <div class="form-group">
            <label style="font-weight: bold; margin-bottom: 10px; display: block;">可用範圍</label>
            <div style="display: flex; gap: 20px;">
              <label style="display: flex; align-items: center; gap: 5px;">
                <input type="checkbox" v-model="formData.available_in_knowledge" />
                <span>知識庫管理中可選</span>
              </label>
              <label style="display: flex; align-items: center; gap: 5px;">
                <input type="checkbox" v-model="formData.available_in_form" />
                <span>表單管理中可選</span>
              </label>
            </div>
          </div>

          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_active" />
              啟用此 API Endpoint
            </label>
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
import { API_BASE_URL } from '@/config/api';

const RAG_API = `${API_BASE_URL}/rag-api/v1`;

export default {
  name: 'ApiEndpointsView',
  data() {
    return {
      endpointList: [],
      vendors: [],
      filterScope: '',
      filterStatus: '',
      showModal: false,
      editingItem: null,
      saving: false,
      loading: false,
      stats: {
        total: 0,
        active: 0,
        knowledge: 0,
        form: 0
      },
      formData: {
        endpoint_id: '',
        endpoint_name: '',
        endpoint_icon: '🔌',
        description: '',
        available_in_knowledge: true,
        available_in_form: true,
        is_active: true,
        display_order: 0,
        vendor_id: null
      }
    };
  },
  mounted() {
    this.loadEndpoints();
    this.loadVendors();
  },
  methods: {
    async loadEndpoints() {
      this.loading = true;
      try {
        const params = {};
        if (this.filterScope) params.scope = this.filterScope;
        if (this.filterStatus !== '') params.is_active = this.filterStatus === 'true';

        const response = await axios.get(`${RAG_API}/api-endpoints`, { params });
        this.endpointList = response.data;

        // 計算統計
        this.stats.total = this.endpointList.length;
        this.stats.active = this.endpointList.filter(e => e.is_active).length;
        this.stats.knowledge = this.endpointList.filter(e => e.available_in_knowledge).length;
        this.stats.form = this.endpointList.filter(e => e.available_in_form).length;
      } catch (error) {
        console.error('載入失敗', error);
        alert('載入失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },

    async loadVendors() {
      try {
        const response = await axios.get(`${RAG_API}/vendors`);
        this.vendors = response.data || [];
        console.log('🏢 已載入業者列表:', this.vendors.length, '個');
      } catch (error) {
        console.error('載入業者列表失敗', error);
        this.vendors = [];
      }
    },

    showCreateModal() {
      this.editingItem = null;
      this.formData = {
        endpoint_id: '',
        endpoint_name: '',
        endpoint_icon: '🔌',
        description: '',
        available_in_knowledge: true,
        available_in_form: true,
        is_active: true,
        display_order: 0,
        vendor_id: null
      };
      this.showModal = true;
    },

    editEndpoint(item) {
      this.editingItem = item;
      this.formData = {
        endpoint_id: item.endpoint_id,
        endpoint_name: item.endpoint_name,
        endpoint_icon: item.endpoint_icon,
        description: item.description || '',
        available_in_knowledge: item.available_in_knowledge,
        available_in_form: item.available_in_form,
        is_active: item.is_active,
        display_order: item.display_order,
        vendor_id: item.vendor_id
      };
      this.showModal = true;
    },

    async saveEndpoint() {
      this.saving = true;

      try {
        if (this.editingItem) {
          // 更新現有 endpoint
          await axios.put(`${RAG_API}/api-endpoints/${this.editingItem.endpoint_id}`, this.formData);
          alert('✅ API Endpoint 已更新！');
        } else {
          // 新增 endpoint
          await axios.post(`${RAG_API}/api-endpoints`, this.formData);
          alert('✅ API Endpoint 已新增！');
        }

        this.closeModal();
        this.loadEndpoints();
      } catch (error) {
        console.error('儲存失敗', error);
        alert('儲存失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.saving = false;
      }
    },

    async toggleEndpoint(endpoint) {
      try {
        await axios.put(`${RAG_API}/api-endpoints/${endpoint.endpoint_id}`, {
          is_active: !endpoint.is_active
        });
        alert(`✅ API Endpoint 已${!endpoint.is_active ? '啟用' : '停用'}！`);
        this.loadEndpoints();
      } catch (error) {
        alert('操作失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    async deleteEndpoint(endpoint) {
      if (!confirm(`確定要刪除 API Endpoint "${endpoint.endpoint_name}" 嗎？\n\n⚠️ 注意：如果有知識或表單正在使用此 API，刪除將會失敗。`)) {
        return;
      }

      try {
        await axios.delete(`${RAG_API}/api-endpoints/${endpoint.endpoint_id}`);
        alert('✅ API Endpoint 已刪除！');
        this.loadEndpoints();
      } catch (error) {
        console.error('刪除失敗', error);
        alert('刪除失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    closeModal() {
      this.showModal = false;
      this.editingItem = null;
    }
  }
};
</script>

<style scoped>
.info-panel {
  background: #f0f9ff;
  border-left: 4px solid #409eff;
  padding: 15px 20px;
  margin-bottom: 20px;
  border-radius: 4px;
}

.info-panel p {
  margin: 0 0 10px 0;
}

.info-panel ul {
  margin: 5px 0 0 20px;
  padding: 0;
}

.info-panel li {
  margin: 5px 0;
}

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

.status.enabled {
  color: #67C23A;
  font-weight: bold;
  font-size: 18px;
}

.status.disabled {
  color: #909399;
  font-size: 18px;
}

.badge.badge-success {
  background: #67c23a;
  color: white;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.badge.badge-muted {
  background: #e4e7ed;
  color: #909399;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 12px;
}

code {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #e6523a;
}
</style>
