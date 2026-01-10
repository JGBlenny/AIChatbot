<template>
  <div>
    <h2>📋 表單提交記錄</h2>
    <p style="color: #909399; font-size: 14px; margin-bottom: 20px;">
      查看用戶透過聊天機器人提交的表單資料
    </p>

    <!-- 過濾器 -->
    <div class="toolbar">
      <div class="filters">
        <select v-model="filterFormId" @change="loadSubmissions" style="margin-right: 10px;">
          <option value="">全部表單</option>
          <option v-for="form in availableForms" :key="form.form_id" :value="form.form_id">
            {{ form.form_name }}
          </option>
        </select>

        <select v-model="filterVendorId" @change="loadSubmissions">
          <option value="">全部業者</option>
          <option v-for="vendor in availableVendors" :key="vendor.id" :value="vendor.id">
            {{ vendor.name }}
          </option>
        </select>
      </div>
    </div>

    <!-- 提交記錄列表 -->
    <div v-if="loading" class="loading">
      <p>載入中...</p>
    </div>

    <div v-else-if="submissions.length === 0" class="empty-state">
      <p>尚無表單提交記錄</p>
    </div>

    <div v-else class="submissions-list">
      <table>
        <thead>
          <tr>
            <th width="60">ID</th>
            <th width="150">表單名稱</th>
            <th width="150">業者</th>
            <th width="120">用戶ID</th>
            <th width="200">觸發問題</th>
            <th>提交資料</th>
            <th width="180">提交時間</th>
            <th width="100">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in submissions" :key="item.id">
            <td>{{ item.id }}</td>
            <td>
              <span class="badge badge-form">{{ item.form_name || item.form_id }}</span>
            </td>
            <td>
              <span v-if="item.vendor_name" class="badge badge-vendor">
                {{ item.vendor_name }}
              </span>
              <span v-else class="badge badge-global">全域</span>
            </td>
            <td><code style="font-size: 12px;">{{ item.user_id }}</code></td>
            <td>
              <div class="trigger-question">
                {{ item.trigger_question || '-' }}
              </div>
            </td>
            <td>
              <div class="submitted-data">
                <span v-for="(value, key) in item.submitted_data" :key="key" class="data-item">
                  <strong>{{ getFieldLabel(item.form_id, key) }}:</strong> {{ value }}
                </span>
              </div>
            </td>
            <td>{{ formatDate(item.submitted_at) }}</td>
            <td>
              <button @click="viewDetails(item)" class="btn-success btn-sm">
                詳情
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分頁 -->
    <div v-if="submissions.length > 0 && pagination.total > 0" class="pagination-info">
      <div style="color: #606266;">
        總計 {{ pagination.total }} 筆記錄，顯示第 {{ pagination.offset + 1 }} - {{ Math.min(pagination.offset + pagination.limit, pagination.total) }} 筆
      </div>
      <div class="pagination-controls">
        <button
          @click="previousPage"
          :disabled="pagination.offset === 0"
          class="btn-pagination"
        >
          ← 上一頁
        </button>
        <span style="margin: 0 15px; color: #606266;">
          第 {{ currentPage }} / {{ totalPages }} 頁
        </span>
        <button
          @click="nextPage"
          :disabled="pagination.offset + pagination.limit >= pagination.total"
          class="btn-pagination"
        >
          下一頁 →
        </button>
      </div>
    </div>

    <!-- 詳情 Modal -->
    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop style="max-width: 600px;">
        <div class="modal-header">
          <h3>📋 提交詳情 #{{ selectedItem.id }}</h3>
          <button @click="closeModal" class="btn-close">✕</button>
        </div>

        <div class="modal-body" style="padding: 30px;">
          <div class="detail-section">
            <h4>基本資訊</h4>
            <div class="detail-row">
              <span class="detail-label">表單名稱：</span>
              <span>{{ selectedItem.form_name || selectedItem.form_id }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">業者：</span>
              <span>{{ selectedItem.vendor_name || '全域' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">用戶ID：</span>
              <code>{{ selectedItem.user_id }}</code>
            </div>
            <div class="detail-row">
              <span class="detail-label">觸發問題：</span>
              <span>{{ selectedItem.trigger_question || '-' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">提交時間：</span>
              <span>{{ formatDate(selectedItem.submitted_at) }}</span>
            </div>
          </div>

          <div class="detail-section">
            <h4>提交資料</h4>
            <div v-for="(value, key) in selectedItem.submitted_data" :key="key" class="detail-row">
              <span class="detail-label">{{ getFieldLabel(selectedItem.form_id, key) }}：</span>
              <span class="detail-value">{{ value }}</span>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeModal" class="btn-secondary">關閉</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

const RAG_API = '/rag-api';

export default {
  name: 'FormSubmissionsView',
  data() {
    return {
      loading: false,
      submissions: [],
      availableForms: [],
      availableVendors: [],
      filterFormId: '',
      filterVendorId: '',
      pagination: {
        total: 0,
        limit: 50,
        offset: 0
      },
      showModal: false,
      selectedItem: null,
      formSchemas: {} // 儲存表單結構以便顯示欄位標籤
    };
  },
  computed: {
    currentPage() {
      return Math.floor(this.pagination.offset / this.pagination.limit) + 1;
    },
    totalPages() {
      return Math.ceil(this.pagination.total / this.pagination.limit);
    }
  },
  async mounted() {
    await this.loadForms();
    await this.loadVendors();
    await this.loadSubmissions();
  },
  methods: {
    async loadForms() {
      try {
        const response = await axios.get(`${RAG_API}/v1/forms`);
        this.availableForms = response.data || [];

        // 載入所有表單結構
        for (const form of this.availableForms) {
          this.formSchemas[form.form_id] = form;
        }
      } catch (error) {
        console.error('載入表單列表失敗', error);
      }
    },

    async loadVendors() {
      try {
        const response = await axios.get('/api/vendors');
        this.availableVendors = response.data || [];
      } catch (error) {
        console.error('載入業者列表失敗', error);
      }
    },

    async loadSubmissions() {
      this.loading = true;
      try {
        const params = {
          limit: this.pagination.limit,
          offset: this.pagination.offset
        };

        if (this.filterFormId) {
          params.form_id = this.filterFormId;
        }

        if (this.filterVendorId) {
          params.vendor_id = this.filterVendorId;
        }

        const response = await axios.get(`${RAG_API}/v1/form-submissions`, { params });
        // 解析 submitted_data（從 JSON 字串轉為物件）
        const items = (response.data.items || []).map(item => ({
          ...item,
          submitted_data: typeof item.submitted_data === 'string'
            ? JSON.parse(item.submitted_data)
            : item.submitted_data
        }));
        this.submissions = items;
        this.pagination.total = response.data.total || 0;
      } catch (error) {
        console.error('載入表單提交記錄失敗', error);
        alert('載入失敗: ' + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },

    getFieldLabel(formId, fieldName) {
      const schema = this.formSchemas[formId];
      if (!schema || !schema.fields) return fieldName;

      const field = schema.fields.find(f => f.field_name === fieldName);
      return field ? field.field_label : fieldName;
    },

    formatDate(dateString) {
      if (!dateString) return '-';
      const date = new Date(dateString);
      return date.toLocaleString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    },

    viewDetails(item) {
      this.selectedItem = item;
      this.showModal = true;
    },

    closeModal() {
      this.showModal = false;
      this.selectedItem = null;
    },

    previousPage() {
      if (this.pagination.offset > 0) {
        this.pagination.offset = Math.max(0, this.pagination.offset - this.pagination.limit);
        this.loadSubmissions();
      }
    },

    nextPage() {
      if (this.pagination.offset + this.pagination.limit < this.pagination.total) {
        this.pagination.offset += this.pagination.limit;
        this.loadSubmissions();
      }
    }
  }
};
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.filters {
  display: flex;
  gap: 10px;
}

.filters select {
  padding: 8px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
  background: white;
  cursor: pointer;
}

.filters select:hover {
  border-color: #409eff;
}

.loading, .empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #909399;
}

.submissions-list table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.submissions-list th {
  background: #f5f7fa;
  padding: 15px;
  text-align: left;
  font-weight: 600;
  color: #606266;
  border-bottom: 2px solid #e4e7ed;
}

.submissions-list td {
  padding: 15px;
  border-bottom: 1px solid #ebeef5;
  color: #606266;
}

.submissions-list tr:hover {
  background: #f5f7fa;
}

.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
}

.badge-form {
  background: #e1f3ff;
  color: #0078d4;
}

.badge-vendor {
  background: #f0f9ff;
  color: #0284c7;
}

.badge-global {
  background: #f3f4f6;
  color: #6b7280;
}

.trigger-question {
  font-size: 13px;
  color: #606266;
  font-style: italic;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.submitted-data {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
}

.data-item {
  padding: 4px 8px;
  background: #f9fafb;
  border-radius: 4px;
  border-left: 3px solid #409eff;
}

.data-item strong {
  color: #303133;
  margin-right: 6px;
}

.pagination-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
  padding: 15px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.pagination-controls {
  display: flex;
  align-items: center;
}

.btn-pagination {
  padding: 8px 16px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  color: #606266;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-pagination:hover:not(:disabled) {
  border-color: #409eff;
  color: #409eff;
}

.btn-pagination:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.detail-section {
  margin-bottom: 30px;
}

.detail-section h4 {
  font-size: 16px;
  color: #303133;
  margin-bottom: 15px;
  padding-bottom: 8px;
  border-bottom: 2px solid #f0f0f0;
}

.detail-row {
  display: flex;
  padding: 12px 0;
  border-bottom: 1px solid #f5f5f5;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  font-weight: 600;
  color: #606266;
  min-width: 120px;
  flex-shrink: 0;
}

.detail-value {
  color: #303133;
  flex: 1;
  word-break: break-word;
}

/* 按鈕樣式 */
.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-success {
  background: #67c23a;
  color: white;
}

.btn-success:hover {
  background: #85ce61;
}

.btn-secondary {
  padding: 10px 24px;
  background: #dcdfe6;
  color: #606266;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-secondary:hover {
  background: #c6c9cf;
}

/* Modal 樣式 */
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
  line-height: 1;
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

.modal-footer {
  padding: 15px 30px;
  border-top: 1px solid #ebeef5;
  display: flex;
  justify-content: flex-end;
}
</style>
