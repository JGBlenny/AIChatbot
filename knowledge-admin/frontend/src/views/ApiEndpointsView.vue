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
            <label>🔒 關聯的知識庫 ID <small>(由系統自動維護)</small></label>
            <div style="padding: 10px; background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; color: #666;">
              <span v-if="formData.related_kb_ids && formData.related_kb_ids.length > 0">
                {{ formData.related_kb_ids.join(', ') }}
                <small style="margin-left: 10px;">(共 {{ formData.related_kb_ids.length }} 筆)</small>
              </span>
              <span v-else style="font-style: italic;">
                尚無關聯知識庫
              </span>
              <div style="margin-top: 5px; font-size: 12px; color: #999;">
                ℹ️ 當知識庫設定 form_id 或 api_config 引用此 endpoint 時，系統會自動更新此欄位
              </div>
            </div>
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

          <!-- 外部 API 設定 -->
          <div class="api-config-section">
            <h3 style="margin: 20px 0 10px; padding-top: 15px; border-top: 1px solid #e5e7eb;">🌐 外部 API 設定</h3>

            <div class="form-group">
              <label>實作類型</label>
              <select v-model="formData.implementation_type">
                <option value="custom">Custom（程式碼內建）</option>
                <option value="dynamic">Dynamic（外部 API 呼叫）</option>
              </select>
              <small class="hint">Custom = api_registry 中的內建處理器；Dynamic = 透過 URL 呼叫外部 API</small>
            </div>

            <template v-if="formData.implementation_type === 'dynamic'">
              <div class="form-row">
                <div class="form-group" style="flex: 0 0 120px;">
                  <label>HTTP 方法</label>
                  <select v-model="formData.http_method">
                    <option value="GET">GET</option>
                    <option value="POST">POST</option>
                    <option value="PUT">PUT</option>
                    <option value="DELETE">DELETE</option>
                  </select>
                </div>
                <div class="form-group" style="flex: 1;">
                  <label>API URL *</label>
                  <input v-model="formData.api_url" placeholder="https://www.jgbsmart.com/api/external/v1/bills" />
                  <small class="hint">支援變數：{session.role_id}、{form.field_name}、{user_input.xxx}</small>
                </div>
              </div>

              <div class="form-group">
                <label>Request Headers <small>(JSON)</small></label>
                <textarea v-model="formData.request_headers_text" rows="3" placeholder='{"X-API-Key": "your-api-key", "Content-Type": "application/json"}'></textarea>
              </div>

              <div class="form-group">
                <label>參數映射 <small>(JSON，將 session/form 資料映射到 API 參數)</small></label>
                <textarea v-model="formData.param_mappings_text" rows="4" :placeholder="paramMappingsPlaceholder"></textarea>
                <small class="hint">格式：[{"param_name": "role_id", "source": "session.role_id"}, {"param_name": "keyword", "source": "form.bill_keyword"}]</small>
              </div>

              <div class="form-group">
                <label>回應模板 <small>(用 {data.field} 引用回傳欄位)</small></label>
                <textarea v-model="formData.response_template" rows="3" placeholder="帳單 {data.title}，狀態：{data.status}，金額：NT$ {data.total}"></textarea>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label>逾時 (秒)</label>
                  <input type="number" v-model.number="formData.request_timeout" min="1" max="120" />
                </div>
                <div class="form-group">
                  <label>重試次數</label>
                  <input type="number" v-model.number="formData.retry_times" min="0" max="5" />
                </div>
                <div class="form-group">
                  <label>快取 (秒, 0=不快取)</label>
                  <input type="number" v-model.number="formData.cache_ttl" min="0" />
                </div>
              </div>
            </template>

            <template v-if="formData.implementation_type === 'custom'">
              <div class="form-group">
                <label>Custom Handler 名稱 <small>(對應 api_registry 中的 key)</small></label>
                <input v-model="formData.custom_handler_name" placeholder="例如：jgb_bills" />
                <small class="hint">此名稱必須與程式碼中 api_registry 的 key 一致</small>
              </div>
            </template>
          </div>

          <div class="form-group" style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #e5e7eb;">
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
        vendor_id: null,
        related_kb_ids: [],
        implementation_type: 'custom',
        api_url: '',
        http_method: 'GET',
        request_headers_text: '',
        param_mappings_text: '',
        response_template: '',
        request_timeout: 30,
        retry_times: 0,
        cache_ttl: 0,
        custom_handler_name: ''
      },
      paramMappingsPlaceholder: '[{"param_name": "role_id", "source": "session.role_id"}, {"param_name": "user_id", "source": "session.user_id"}]'
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
        vendor_id: null,
        related_kb_ids: [],
        implementation_type: 'custom',
        api_url: '',
        http_method: 'GET',
        request_headers_text: '',
        param_mappings_text: '',
        response_template: '',
        request_timeout: 30,
        retry_times: 0,
        cache_ttl: 0,
        custom_handler_name: ''
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
        vendor_id: item.vendor_id,
        related_kb_ids: item.related_kb_ids || [],
        implementation_type: item.implementation_type || 'custom',
        api_url: item.api_url || '',
        http_method: item.http_method || 'GET',
        request_headers_text: item.request_headers ? JSON.stringify(item.request_headers, null, 2) : '',
        param_mappings_text: item.param_mappings ? JSON.stringify(item.param_mappings, null, 2) : '',
        response_template: item.response_template || '',
        request_timeout: item.request_timeout || 30,
        retry_times: item.retry_times || 0,
        cache_ttl: item.cache_ttl || 0,
        custom_handler_name: item.custom_handler_name || ''
      };
      this.showModal = true;
    },

    async saveEndpoint() {
      this.saving = true;

      try {
        const payload = {
          ...this.formData
        };
        delete payload.related_kb_ids;

        // JSON 文字欄位轉回物件
        if (payload.request_headers_text) {
          try { payload.request_headers = JSON.parse(payload.request_headers_text); }
          catch (e) { alert('Request Headers JSON 格式錯誤'); this.saving = false; return; }
        } else {
          payload.request_headers = null;
        }
        delete payload.request_headers_text;

        if (payload.param_mappings_text) {
          try { payload.param_mappings = JSON.parse(payload.param_mappings_text); }
          catch (e) { alert('參數映射 JSON 格式錯誤'); this.saving = false; return; }
        } else {
          payload.param_mappings = null;
        }
        delete payload.param_mappings_text;

        if (this.editingItem) {
          // 更新現有 endpoint
          await axios.put(`${RAG_API}/api-endpoints/${this.editingItem.endpoint_id}`, payload);
          alert('✅ API Endpoint 已更新！');
        } else {
          // 新增 endpoint
          await axios.post(`${RAG_API}/api-endpoints`, payload);
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
