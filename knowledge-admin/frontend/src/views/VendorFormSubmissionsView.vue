<template>
  <div class="vendor-submissions-container">
    <div class="header">
      <div class="header-content">
        <h1>📋 表單提交記錄</h1>
        <p v-if="vendor" class="vendor-name">{{ vendor.name }}</p>
      </div>
      <a :href="`/${vendorCode}/chat`" class="btn-back">
        ← 返回聊天
      </a>
    </div>

    <!-- 工具列 -->
    <div class="toolbar">
      <select v-model="filterFormId" @change="loadSubmissions" class="filter-select">
        <option value="">全部表單</option>
        <option v-for="form in availableForms" :key="form.form_id" :value="form.form_id">
          {{ form.form_name }}
        </option>
      </select>
    </div>

    <!-- 載入狀態 -->
    <div v-if="loading" class="loading">
      <p>載入中...</p>
    </div>

    <!-- 空狀態 -->
    <div v-else-if="submissions.length === 0" class="empty-state">
      <p>尚無表單提交記錄</p>
    </div>

    <!-- 表單記錄列表 -->
    <div v-else class="submissions-list">
      <table>
        <thead>
          <tr>
            <th width="60">ID</th>
            <th width="150">表單名稱</th>
            <th width="200">觸發問題</th>
            <th>提交資料</th>
            <th width="120">用戶ID</th>
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
            <td><code style="font-size: 12px;">{{ truncateUserId(item.user_id) }}</code></td>
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

    <!-- 統計資訊和分頁控制 -->
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
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>表單詳情 #{{ selectedItem.id }}</h2>
          <button @click="closeModal" class="btn-close">✕</button>
        </div>

        <div class="modal-body">
          <div class="detail-section">
            <h3>基本資訊</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <label>表單名稱</label>
                <div>{{ selectedItem.form_name || selectedItem.form_id }}</div>
              </div>
              <div class="detail-item">
                <label>觸發問題</label>
                <div>{{ selectedItem.trigger_question || '-' }}</div>
              </div>
              <div class="detail-item">
                <label>提交時間</label>
                <div>{{ formatDate(selectedItem.submitted_at) }}</div>
              </div>
              <div class="detail-item">
                <label>用戶ID</label>
                <code>{{ selectedItem.user_id }}</code>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <h3>提交資料</h3>
            <div class="detail-grid">
              <div v-for="(value, key) in selectedItem.submitted_data" :key="key" class="detail-item">
                <label>{{ getFieldLabel(selectedItem.form_id, key) }}</label>
                <div class="detail-value">{{ value }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeModal" class="btn-modal-close">關閉</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

const RAG_API = '/rag-api';

export default {
  name: 'VendorFormSubmissionsView',
  data() {
    return {
      vendorCode: null,
      vendor: null,
      loading: false,
      submissions: [],
      availableForms: [],
      filterFormId: '',
      pagination: {
        total: 0,
        limit: 20,
        offset: 0
      },
      showModal: false,
      selectedItem: null,
      formSchemas: {}
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
    this.vendorCode = this.$route.params.vendorCode;
    await this.loadVendor();
    await this.loadForms();
    await this.loadSubmissions();
  },
  methods: {
    async loadVendor() {
      try {
        const response = await axios.get(`${RAG_API}/v1/vendors/by-code/${this.vendorCode}`);
        this.vendor = response.data;
      } catch (error) {
        console.error('載入業者資訊失敗', error);
        alert('找不到業者資訊');
      }
    },

    async loadForms() {
      try {
        const response = await axios.get(`${RAG_API}/v1/forms`, {
          params: { vendor_id: this.vendor?.id }
        });
        this.availableForms = response.data || [];

        // 載入表單結構
        for (const form of this.availableForms) {
          this.formSchemas[form.form_id] = form;
        }
      } catch (error) {
        console.error('載入表單列表失敗', error);
      }
    },

    async loadSubmissions() {
      if (!this.vendor) return;

      this.loading = true;
      try {
        const params = {
          vendor_id: this.vendor.id,
          limit: this.pagination.limit,
          offset: this.pagination.offset
        };

        if (this.filterFormId) {
          params.form_id = this.filterFormId;
        }

        const response = await axios.get(`${RAG_API}/v1/form-submissions`, { params });

        // 解析 submitted_data
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
        alert('載入失敗');
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

    truncateUserId(userId) {
      if (!userId) return '-';
      if (userId.length <= 20) return userId;
      return userId.substring(0, 17) + '...';
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
.vendor-submissions-container {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 20px;
}

.header {
  max-width: 1400px;
  margin: 0 auto 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 20px 30px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.header-content h1 {
  color: #303133;
  margin: 0 0 5px 0;
  font-size: 24px;
}

.vendor-name {
  color: #909399;
  margin: 0;
  font-size: 14px;
}

.btn-back {
  padding: 8px 16px;
  background: #409eff;
  color: white;
  border: none;
  border-radius: 4px;
  text-decoration: none;
  transition: all 0.3s;
  font-size: 14px;
}

.btn-back:hover {
  background: #66b1ff;
}

.toolbar {
  max-width: 1400px;
  margin: 0 auto 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
  background: white;
  cursor: pointer;
  min-width: 200px;
}

.filter-select:hover {
  border-color: #409eff;
}

.loading, .empty-state {
  max-width: 1400px;
  margin: 60px auto;
  text-align: center;
  padding: 60px 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  color: #909399;
}

.submissions-list {
  max-width: 1400px;
  margin: 0 auto;
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
  font-size: 14px;
}

.submissions-list td {
  padding: 15px;
  border-bottom: 1px solid #ebeef5;
  color: #606266;
  font-size: 14px;
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

.pagination-info {
  max-width: 1400px;
  margin: 20px auto 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
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

/* Modal 樣式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  padding: 25px 30px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
  color: white;
}

.btn-close {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  font-size: 24px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
}

.btn-close:hover {
  background: rgba(255, 255, 255, 0.3);
}

.modal-body {
  padding: 30px;
}

.detail-section {
  margin-bottom: 30px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-section h3 {
  font-size: 16px;
  color: #333;
  margin: 0 0 15px 0;
  padding-bottom: 10px;
  border-bottom: 2px solid #f0f0f0;
}

.detail-grid {
  display: grid;
  gap: 15px;
}

.detail-item label {
  display: block;
  font-size: 12px;
  color: #888;
  margin-bottom: 6px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-item div,
.detail-value {
  font-size: 15px;
  color: #333;
  padding: 10px 12px;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 3px solid #667eea;
}

.detail-item code {
  font-family: 'Courier New', monospace;
  background: #f8f9fa;
  padding: 10px 12px;
  border-radius: 6px;
  display: block;
  font-size: 13px;
  border-left: 3px solid #667eea;
}

.modal-footer {
  padding: 20px 30px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: flex-end;
}

.btn-modal-close {
  padding: 10px 24px;
  background: #f0f0f0;
  color: #333;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s;
}

.btn-modal-close:hover {
  background: #e0e0e0;
}
</style>
