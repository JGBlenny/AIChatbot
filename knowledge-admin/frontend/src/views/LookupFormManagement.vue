<template>
  <div>
    <div class="page-header">
      <h2>📋 Lookup 表單管理</h2>
      <p class="subtitle">管理系統內建的 Lookup 查詢表單（全域共用）</p>
    </div>

    <!-- 統計卡片 -->
    <div class="stats-cards">
      <div class="stat-card">
        <div class="stat-label">已建立表單</div>
        <div class="stat-value">{{ existingForms.length }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">可建立 Category</div>
        <div class="stat-value">{{ availableCategories.length }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">總 Category 數</div>
        <div class="stat-value">{{ allCategories.length }}</div>
      </div>
    </div>

    <!-- 工具列 -->
    <div class="toolbar">
      <button @click="showCreateModal" class="btn-primary">
        ➕ 建立 Lookup 表單
      </button>
      <button @click="loadForms" class="btn-secondary">
        🔄 刷新
      </button>
    </div>

    <!-- 載入狀態 -->
    <div v-if="loading" class="loading">
      <p>載入中...</p>
    </div>

    <!-- 已建立的表單列表 -->
    <div v-else class="forms-section">
      <h3>📝 已建立的 Lookup 表單 ({{ existingForms.length }})</h3>

      <div v-if="existingForms.length === 0" class="empty-state">
        <p>尚未建立任何 Lookup 表單</p>
      </div>

      <table v-else class="forms-table">
        <thead>
          <tr>
            <th width="200">表單 ID</th>
            <th width="150">表單名稱</th>
            <th width="150">Category</th>
            <th width="120">Endpoint 類型</th>
            <th width="80">欄位數</th>
            <th width="100">關聯知識</th>
            <th width="100">狀態</th>
            <th width="200">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="form in existingForms" :key="form.form_id">
            <td><code>{{ form.form_id }}</code></td>
            <td><strong>{{ form.form_name }}</strong></td>
            <td>
              <span class="badge badge-category">
                {{ getCategoryDisplayName(form.api_config?.static_params?.category) }}
              </span>
            </td>
            <td>
              <span class="badge" :class="form.api_config?.endpoint === 'lookup_generic' ? 'badge-generic' : 'badge-lookup'">
                {{ form.api_config?.endpoint }}
              </span>
            </td>
            <td class="center">{{ form.fields?.length || 0 }}</td>
            <td class="center">
              <span class="kb-count" :class="{ 'has-kb': form.stats?.linked_kb_count > 0 }">
                {{ form.stats?.linked_kb_count || 0 }} 筆
              </span>
            </td>
            <td>
              <span class="status-badge" :class="form.is_active ? 'status-active' : 'status-inactive'">
                {{ form.is_active ? '✓ 啟用' : '✗ 停用' }}
              </span>
            </td>
            <td>
              <button @click="viewStats(form)" class="btn-sm btn-info" title="查看統計">📊</button>
              <button @click="viewForm(form)" class="btn-sm btn-info">查看</button>
              <button @click="editForm(form)" class="btn-sm btn-warning">編輯</button>
              <button @click="deleteForm(form)" class="btn-sm btn-danger">刪除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 可建立的 Category 列表 -->
    <div class="forms-section" style="margin-top: 40px;">
      <h3>💡 可建立的 Category ({{ availableCategories.length }})</h3>

      <div v-if="availableCategories.length === 0" class="empty-state">
        <p>所有 Category 都已建立表單</p>
      </div>

      <div v-else class="category-grid">
        <div
          v-for="cat in availableCategories"
          :key="cat.id"
          class="category-card"
          @click="quickCreateForm(cat)"
        >
          <div class="category-icon">📋</div>
          <div class="category-name">{{ cat.display_name }}</div>
          <div class="category-id"><code>{{ cat.id }}</code></div>
          <button class="btn-sm btn-primary">建立表單</button>
        </div>
      </div>
    </div>

    <!-- 建立/編輯表單 Modal -->
    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop style="max-width: 800px;">
        <div class="modal-header">
          <h3>{{ editingForm ? '✏️ 編輯 Lookup 表單' : '➕ 建立 Lookup 表單' }}</h3>
          <button @click="closeModal" class="btn-close">✕</button>
        </div>

        <div class="modal-body">
          <!-- 基本資訊 -->
          <div class="form-section">
            <h4>基本資訊</h4>

            <div class="form-group">
              <label>Category *</label>
              <select v-model="formData.category" :disabled="!!editingForm" required>
                <option value="">請選擇 Category</option>
                <option v-for="cat in allCategories" :key="cat.id" :value="cat.id">
                  {{ cat.display_name }} ({{ cat.id }})
                </option>
              </select>
              <small class="hint">選擇後無法修改</small>
            </div>

            <div class="form-group">
              <label>表單名稱 *</label>
              <input
                v-model="formData.form_name"
                type="text"
                placeholder="例如：電費資訊查詢"
                required
              />
            </div>

            <div class="form-group">
              <label>表單 ID</label>
              <input
                v-model="computedFormId"
                type="text"
                disabled
              />
              <small class="hint">自動生成：{{ formData.category }}_form_v2</small>
            </div>

            <div class="form-group">
              <label>引導語（可選）</label>
              <textarea
                v-model="formData.default_intro"
                rows="2"
                placeholder="例如：請提供物件地址以查詢電費資訊"
              ></textarea>
            </div>
          </div>

          <!-- API 配置 -->
          <div class="form-section">
            <h4>API 配置</h4>

            <div class="form-group">
              <label>Endpoint 類型 *</label>
              <div class="radio-group">
                <label class="radio-label">
                  <input type="radio" v-model="formData.endpoint" value="lookup_generic" />
                  <span>lookup_generic</span>
                  <small>單一查詢鍵（僅 address）</small>
                </label>
                <label class="radio-label">
                  <input type="radio" v-model="formData.endpoint" value="lookup" />
                  <span>lookup</span>
                  <small>複合查詢鍵（address + key2）</small>
                </label>
              </div>
            </div>
          </div>

          <!-- 表單欄位 -->
          <div class="form-section">
            <h4>表單欄位</h4>

            <!-- 第一個欄位（address，必填） -->
            <div class="field-card">
              <div class="field-header">
                <strong>欄位 1：地址（必填）</strong>
                <span class="badge">固定欄位</span>
              </div>
              <div class="field-body">
                <div class="form-group">
                  <label>欄位標籤</label>
                  <input v-model="formData.field1_label" type="text" placeholder="物件地址" />
                </div>
                <div class="form-group">
                  <label>提示訊息</label>
                  <input v-model="formData.field1_prompt" type="text" placeholder="請輸入完整的物件地址" />
                </div>
              </div>
            </div>

            <!-- 第二個欄位（key2，可選） -->
            <div v-if="formData.endpoint === 'lookup'" class="field-card">
              <div class="field-header">
                <strong>欄位 2：查詢鍵 2（必填）</strong>
                <span class="badge badge-warning">lookup 專用</span>
              </div>
              <div class="field-body">
                <div class="form-group">
                  <label>欄位名稱</label>
                  <input v-model="formData.field2_name" type="text" placeholder="parking_spot" />
                  <small class="hint">英文名稱，用於 API 參數</small>
                </div>
                <div class="form-group">
                  <label>欄位標籤</label>
                  <input v-model="formData.field2_label" type="text" placeholder="車位號碼" />
                </div>
                <div class="form-group">
                  <label>提示訊息</label>
                  <input v-model="formData.field2_prompt" type="text" placeholder="請輸入車位號碼" />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeModal" class="btn-secondary">取消</button>
          <button @click="saveForm" class="btn-primary" :disabled="!isFormValid">
            {{ editingForm ? '更新' : '建立' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 查看表單統計 Modal -->
    <div v-if="viewingStats" class="modal-overlay" @click="viewingStats = null">
      <div class="modal-content" @click.stop style="max-width: 800px;">
        <div class="modal-header">
          <h3>📊 {{ viewingStats.form_name }} - 統計資訊</h3>
          <button @click="viewingStats = null" class="btn-close">✕</button>
        </div>

        <div class="modal-body">
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-item-label">表單 ID</div>
              <div class="stat-item-value"><code>{{ viewingStats.form_id }}</code></div>
            </div>
            <div class="stat-item">
              <div class="stat-item-label">Category</div>
              <div class="stat-item-value">{{ viewingStats.category }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-item-label">API Endpoint</div>
              <div class="stat-item-value"><code>{{ viewingStats.endpoint }}</code></div>
            </div>
            <div class="stat-item">
              <div class="stat-item-label">關聯知識庫</div>
              <div class="stat-item-value highlight">{{ viewingStats.linked_kb_count }} 筆</div>
            </div>
          </div>

          <h4 style="margin-top: 20px;">📡 使用的 API 端點</h4>
          <div class="api-endpoint-info">
            <div class="info-row">
              <span class="info-label">端點 ID：</span>
              <code>{{ viewingStats.api_endpoint?.endpoint_id }}</code>
            </div>
            <div class="info-row">
              <span class="info-label">端點名稱：</span>
              <span>{{ viewingStats.api_endpoint?.endpoint_name }}</span>
            </div>
          </div>

          <h4 style="margin-top: 20px;">🔗 關聯的知識庫 ({{ viewingStats.linked_kb_count }} 筆)</h4>
          <div v-if="viewingStats.linked_kb_ids && viewingStats.linked_kb_ids.length > 0" class="kb-list">
            <div v-for="kbId in viewingStats.linked_kb_ids" :key="kbId" class="kb-item">
              <span class="kb-id">KB #{{ kbId }}</span>
              <a :href="`/knowledge?id=${kbId}`" target="_blank" class="btn-sm btn-link">查看</a>
            </div>
          </div>
          <div v-else class="empty-state-small">
            <p>尚未有知識庫使用此表單</p>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="viewingStats = null" class="btn-secondary">關閉</button>
        </div>
      </div>
    </div>

    <!-- 查看表單 Modal -->
    <div v-if="viewingForm" class="modal-overlay" @click="viewingForm = null">
      <div class="modal-content" @click.stop style="max-width: 700px;">
        <div class="modal-header">
          <h3>📋 {{ viewingForm.form_name }}</h3>
          <button @click="viewingForm = null" class="btn-close">✕</button>
        </div>

        <div class="modal-body">
          <div class="detail-row">
            <span class="detail-label">表單 ID：</span>
            <code>{{ viewingForm.form_id }}</code>
          </div>
          <div class="detail-row">
            <span class="detail-label">Category：</span>
            <span>{{ viewingForm.api_config?.static_params?.category }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Endpoint：</span>
            <code>{{ viewingForm.api_config?.endpoint }}</code>
          </div>
          <div class="detail-row">
            <span class="detail-label">欄位數量：</span>
            <span>{{ viewingForm.fields?.length || 0 }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">狀態：</span>
            <span :class="viewingForm.is_active ? 'success' : 'muted'">
              {{ viewingForm.is_active ? '已啟用' : '已停用' }}
            </span>
          </div>

          <h4 style="margin-top: 20px;">表單欄位</h4>
          <div v-for="(field, index) in viewingForm.fields" :key="index" class="field-detail">
            <strong>{{ index + 1 }}. {{ field.field_label }}</strong>
            <div><small>欄位名稱：{{ field.field_name }}</small></div>
            <div><small>提示：{{ field.prompt }}</small></div>
            <div><small>類型：{{ field.field_type }} {{ field.required ? '(必填)' : '' }}</small></div>
          </div>

          <h4 style="margin-top: 20px;">API 配置</h4>
          <pre class="code-block">{{ JSON.stringify(viewingForm.api_config, null, 2) }}</pre>
        </div>

        <div class="modal-footer">
          <button @click="editForm(viewingForm); viewingForm = null" class="btn-warning">編輯</button>
          <button @click="viewingForm = null" class="btn-secondary">關閉</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

const RAG_API = '/rag-api';

// 所有 Lookup Category 定義
const ALL_CATEGORIES = [
  { id: 'utility_electricity', display_name: '電費資訊' },
  { id: 'utility_water', display_name: '水費資訊' },
  { id: 'utility_gas', display_name: '瓦斯費資訊' },
  { id: 'rent_info', display_name: '租金資訊' },
  { id: 'deposit_info', display_name: '押金資訊' },
  { id: 'management_fee', display_name: '管理費資訊' },
  { id: 'parking_fee', display_name: '停車費資訊' },
  { id: 'community_facilities', display_name: '公共設施' },
  { id: 'parcel_service', display_name: '包裹代收服務' },
  { id: 'customer_service', display_name: '客服聯絡方式' },
  { id: 'service_hours', display_name: '服務時間' },
  { id: 'payment_methods', display_name: '繳費方式' },
  { id: 'vendor_contacts', display_name: '業者聯絡資訊' }
];

export default {
  name: 'LookupFormManagement',
  data() {
    return {
      loading: false,
      existingForms: [],
      allCategories: ALL_CATEGORIES,
      showModal: false,
      editingForm: null,
      viewingForm: null,
      viewingStats: null,
      formData: {
        category: '',
        form_name: '',
        default_intro: '',
        endpoint: 'lookup_generic',
        field1_label: '物件地址',
        field1_prompt: '請輸入完整的物件地址',
        field2_name: '',
        field2_label: '',
        field2_prompt: ''
      }
    };
  },
  computed: {
    availableCategories() {
      const existingCategories = this.existingForms.map(
        f => f.api_config?.static_params?.category
      );
      return this.allCategories.filter(cat => !existingCategories.includes(cat.id));
    },
    computedFormId() {
      return this.formData.category ? `${this.formData.category}_form_v2` : '';
    },
    isFormValid() {
      if (!this.formData.category || !this.formData.form_name) return false;
      if (this.formData.endpoint === 'lookup') {
        return !!(this.formData.field2_name && this.formData.field2_label);
      }
      return true;
    }
  },
  mounted() {
    this.loadForms();
  },
  methods: {
    async loadForms() {
      this.loading = true;
      try {
        const response = await axios.get(`${RAG_API}/v1/forms`);
        // 只顯示 Lookup 表單
        this.existingForms = (response.data || []).filter(
          f => f.api_config?.endpoint === 'lookup' || f.api_config?.endpoint === 'lookup_generic'
        );

        // 為每個表單載入統計資訊
        await this.loadFormsStats();
      } catch (error) {
        console.error('載入表單失敗', error);
        alert('載入失敗: ' + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },

    async loadFormsStats() {
      // 並行載入所有表單的統計資訊
      const statsPromises = this.existingForms.map(async (form) => {
        try {
          const response = await axios.get(`${RAG_API}/v1/lookup-forms/${form.form_id}/stats`);
          form.stats = response.data;
        } catch (error) {
          console.error(`載入表單 ${form.form_id} 統計失敗:`, error);
          form.stats = { linked_kb_count: 0 };
        }
      });

      await Promise.all(statsPromises);
    },

    async viewStats(form) {
      try {
        const response = await axios.get(`${RAG_API}/v1/lookup-forms/${form.form_id}/stats`);
        this.viewingStats = response.data;
      } catch (error) {
        console.error('載入統計失敗:', error);
        alert('載入統計失敗: ' + (error.response?.data?.detail || error.message));
      }
    },

    getCategoryDisplayName(categoryId) {
      const cat = this.allCategories.find(c => c.id === categoryId);
      return cat ? cat.display_name : categoryId;
    },

    showCreateModal() {
      this.editingForm = null;
      this.formData = {
        category: '',
        form_name: '',
        default_intro: '',
        endpoint: 'lookup_generic',
        field1_label: '物件地址',
        field1_prompt: '請輸入完整的物件地址',
        field2_name: '',
        field2_label: '',
        field2_prompt: ''
      };
      this.showModal = true;
    },

    quickCreateForm(category) {
      this.editingForm = null;
      this.formData = {
        category: category.id,
        form_name: `${category.display_name}查詢`,
        default_intro: `請提供物件地址以查詢${category.display_name}`,
        endpoint: 'lookup_generic',
        field1_label: '物件地址',
        field1_prompt: '請輸入完整的物件地址',
        field2_name: '',
        field2_label: '',
        field2_prompt: ''
      };
      this.showModal = true;
    },

    viewForm(form) {
      this.viewingForm = form;
    },

    editForm(form) {
      this.editingForm = form;

      // 解析現有表單資料
      const field1 = form.fields[0] || {};
      const field2 = form.fields[1] || {};

      this.formData = {
        category: form.api_config?.static_params?.category || '',
        form_name: form.form_name,
        default_intro: form.default_intro || '',
        endpoint: form.api_config?.endpoint || 'lookup_generic',
        field1_label: field1.field_label || '物件地址',
        field1_prompt: field1.prompt || '請輸入完整的物件地址',
        field2_name: field2.field_name || '',
        field2_label: field2.field_label || '',
        field2_prompt: field2.prompt || ''
      };

      this.showModal = true;
    },

    async saveForm() {
      try {
        const fields = [
          {
            field_name: 'address',
            field_label: this.formData.field1_label,
            field_type: 'text',
            prompt: this.formData.field1_prompt,
            required: true,
            validation_type: 'address'
          }
        ];

        // 如果是 lookup 類型，加入第二個欄位
        if (this.formData.endpoint === 'lookup' && this.formData.field2_name) {
          fields.push({
            field_name: this.formData.field2_name,
            field_label: this.formData.field2_label,
            field_type: 'text',
            prompt: this.formData.field2_prompt,
            required: true
          });
        }

        // 構建 API 配置
        const apiConfig = {
          endpoint: this.formData.endpoint,
          static_params: {
            category: this.formData.category
          },
          params_from_form: this.formData.endpoint === 'lookup_generic'
            ? { address: 'address' }
            : { key: 'address', key2: this.formData.field2_name }
        };

        const payload = {
          form_name: this.formData.form_name,
          description: `Lookup 查詢表單 - ${this.getCategoryDisplayName(this.formData.category)}`,
          default_intro: this.formData.default_intro,
          fields: fields,
          vendor_id: null,  // 全域表單
          is_active: true,
          on_complete_action: 'call_api',
          api_config: apiConfig
        };

        if (this.editingForm) {
          // 更新表單
          await axios.put(`${RAG_API}/v1/forms/${this.editingForm.form_id}`, payload);
          alert('✅ 表單更新成功');
        } else {
          // 建立表單
          payload.form_id = this.computedFormId;
          await axios.post(`${RAG_API}/v1/forms`, payload);
          alert('✅ 表單建立成功');
        }

        this.closeModal();
        this.loadForms();
      } catch (error) {
        console.error('儲存表單失敗', error);
        alert('❌ 儲存失敗: ' + (error.response?.data?.detail || error.message));
      }
    },

    async deleteForm(form) {
      if (!confirm(`確定要刪除表單「${form.form_name}」嗎？\n\n此操作無法復原！`)) {
        return;
      }

      try {
        await axios.delete(`${RAG_API}/v1/forms/${form.form_id}`);
        alert('✅ 表單已刪除');
        this.loadForms();
      } catch (error) {
        console.error('刪除表單失敗', error);
        alert('❌ 刪除失敗: ' + (error.response?.data?.detail || error.message));
      }
    },

    closeModal() {
      this.showModal = false;
      this.editingForm = null;
    }
  }
};
</script>

<style scoped>
.page-header {
  margin-bottom: 30px;
}

.subtitle {
  color: #909399;
  font-size: 14px;
  margin-top: 8px;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #303133;
}

.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.forms-section {
  margin-bottom: 40px;
}

.forms-section h3 {
  margin-bottom: 20px;
  color: #303133;
}

.forms-table {
  width: 100%;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.forms-table th {
  background: #f5f7fa;
  padding: 15px;
  text-align: left;
  font-weight: 600;
  color: #606266;
  font-size: 14px;
  border-bottom: 2px solid #e4e7ed;
}

.forms-table td {
  padding: 15px;
  border-bottom: 1px solid #ebeef5;
  font-size: 14px;
  color: #2d3748;
}

.forms-table tr:hover {
  background: #f5f7fa;
}

.forms-table td.center {
  text-align: center;
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
}

.category-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}

.category-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.category-icon {
  font-size: 40px;
  margin-bottom: 10px;
}

.category-name {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 8px;
}

.category-id {
  font-size: 12px;
  color: #909399;
  margin-bottom: 15px;
}

.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.badge-category {
  background: #e1f3ff;
  color: #0078d4;
}

.badge-generic {
  background: #d4edda;
  color: #155724;
}

.badge-lookup {
  background: #fff3cd;
  color: #856404;
}

.badge-warning {
  background: #fff3cd;
  color: #856404;
}

.badge-current {
  background: #d1f2eb;
  color: #0c5460;
  margin-left: 10px;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.status-active {
  background: #d1e7dd;
  color: #0f5132;
}

.status-inactive {
  background: #f8d7da;
  color: #842029;
}

.form-section {
  margin-bottom: 30px;
  padding: 20px;
  background: #f9fafb;
  border-radius: 8px;
}

.form-section h4 {
  margin-bottom: 15px;
  color: #303133;
  font-size: 16px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #303133;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
}

.form-group input:disabled {
  background: #f5f7fa;
  color: #909399;
}

.form-group .hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}

.radio-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.radio-label {
  display: flex;
  align-items: flex-start;
  padding: 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
}

.radio-label:hover {
  border-color: #409eff;
  background: #f0f9ff;
}

.radio-label input[type="radio"] {
  margin-right: 10px;
  margin-top: 2px;
}

.radio-label span {
  flex: 1;
}

.radio-label small {
  display: block;
  color: #909399;
  margin-top: 4px;
}

.field-card {
  background: white;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 15px;
  border: 1px solid #e4e7ed;
}

.field-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ebeef5;
}

.field-body {
  display: grid;
  grid-template-columns: 1fr;
  gap: 15px;
}

.detail-row {
  padding: 12px 0;
  border-bottom: 1px solid #f5f5f5;
}

.detail-label {
  font-weight: 600;
  color: #606266;
  margin-right: 10px;
}

.field-detail {
  background: #f9fafb;
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 10px;
}

.code-block {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
}

.loading,
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #909399;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  transition: all 0.3s;
  margin-right: 5px;
}

.btn-primary {
  background: #409eff;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-primary:hover {
  background: #66b1ff;
}

.btn-primary:disabled {
  background: #a0cfff;
  cursor: not-allowed;
}

.btn-secondary {
  background: #dcdfe6;
  color: #606266;
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-secondary:hover {
  background: #c6c9cf;
}

.btn-info {
  background: #67c23a;
  color: white;
}

.btn-info:hover {
  background: #85ce61;
}

.btn-warning {
  background: #e6a23c;
  color: white;
}

.btn-warning:hover {
  background: #ebb563;
}

.btn-danger {
  background: #f56c6c;
  color: white;
}

.btn-danger:hover {
  background: #f78989;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  max-height: 90vh;
  overflow-y: auto;
  width: 90%;
}

.modal-header {
  padding: 20px 30px;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #909399;
  padding: 0;
  width: 32px;
  height: 32px;
  border-radius: 4px;
  transition: all 0.3s;
}

.btn-close:hover {
  background: #f5f7fa;
  color: #606266;
}

.modal-body {
  padding: 30px;
}

.modal-footer {
  padding: 15px 30px;
  border-top: 1px solid #ebeef5;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.success {
  color: #67c23a;
}

.muted {
  color: #909399;
}

/* 新增: 知識庫數量樣式 */
.kb-count {
  font-size: 13px;
  color: #909399;
}

.kb-count.has-kb {
  color: #409eff;
  font-weight: 600;
}

/* 新增: 統計 Modal 樣式 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.stat-item {
  background: #f9fafb;
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.stat-item-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-item-value {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.stat-item-value.highlight {
  color: #409eff;
}

.api-endpoint-info {
  background: #f9fafb;
  padding: 15px;
  border-radius: 8px;
  margin-top: 15px;
}

.info-row {
  padding: 8px 0;
  display: flex;
  align-items: center;
}

.info-label {
  font-weight: 600;
  color: #606266;
  margin-right: 10px;
  min-width: 180px;
}

.highlight {
  color: #409eff;
  font-weight: 600;
}

.kb-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 300px;
  overflow-y: auto;
  margin-top: 10px;
}

.kb-item {
  background: #f9fafb;
  padding: 12px 15px;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid #e4e7ed;
}

.kb-id {
  font-family: monospace;
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.btn-link {
  background: #409eff;
  color: white;
  text-decoration: none;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  transition: all 0.3s;
}

.btn-link:hover {
  background: #66b1ff;
}

.empty-state-small {
  text-align: center;
  padding: 30px;
  color: #909399;
  background: #f9fafb;
  border-radius: 4px;
}
</style>
