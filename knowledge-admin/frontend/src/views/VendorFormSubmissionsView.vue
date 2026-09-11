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
      <div class="toolbar-left">
        <select v-model="filterFormId" @change="loadSubmissions" class="filter-select">
          <option value="">全部表單</option>
          <option v-for="form in availableForms" :key="form.form_id" :value="form.form_id">
            {{ form.form_name }}
          </option>
        </select>
      </div>

      <div class="toolbar-right">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="🔍 搜尋名稱、內容..."
          class="search-input"
        />

        <select v-model="filterStatus" class="filter-select">
          <option value="">全部狀態</option>
          <option value="pending">⏳ 待處理</option>
          <option value="processing">🔄 處理中</option>
          <option value="completed">✅ 已完成</option>
          <option value="rejected">❌ 已拒絕</option>
        </select>
      </div>
    </div>

    <!-- 載入狀態 -->
    <div v-if="loading" class="loading">
      <p>載入中...</p>
    </div>

    <!-- 空狀態 -->
    <div v-else-if="filteredSubmissions.length === 0" class="empty-state">
      <p>{{ submissions.length === 0 ? '尚無表單提交記錄' : '沒有符合條件的記錄' }}</p>
    </div>

    <!-- 表單記錄列表 -->
    <div v-else class="submissions-list">
      <table>
        <thead>
          <tr>
            <th width="60">ID</th>
            <th width="150">表單名稱</th>
            <th width="100">狀態</th>
            <th width="180">觸發問題</th>
            <th>提交資料</th>
            <th width="120">用戶ID</th>
            <th width="180">提交時間</th>
            <th width="120">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in filteredSubmissions" :key="item.id">
            <td>{{ item.id }}</td>
            <td>
              <span class="badge badge-form">{{ item.form_name || item.form_id }}</span>
            </td>
            <td>
              <span class="status-badge" :class="'status-' + (item.status || 'pending')">
                {{ getStatusLabel(item.status) }}
              </span>
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
    <div v-if="filteredSubmissions.length > 0" class="pagination-info">
      <div style="color: #606266;">
        <span v-if="searchQuery || filterStatus">
          符合條件：{{ filteredSubmissions.length }} 筆 / 總計：{{ pagination.total }} 筆
        </span>
        <span v-else>
          總計 {{ pagination.total }} 筆記錄，顯示第 {{ pagination.offset + 1 }} - {{ Math.min(pagination.offset + pagination.limit, pagination.total) }} 筆
        </span>
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

          <div class="detail-section">
            <h3>處理狀態</h3>
            <div class="status-editor">
              <div class="form-field">
                <label>狀態</label>
                <select v-model="editingStatus" class="status-select">
                  <option value="pending">⏳ 待處理</option>
                  <option value="processing">🔄 處理中</option>
                  <option value="completed">✅ 已完成</option>
                  <option value="rejected">❌ 已拒絕</option>
                </select>
              </div>
              <div class="form-field">
                <label>備註說明</label>
                <textarea
                  v-model="editingNotes"
                  class="notes-textarea"
                  placeholder="請輸入處理備註..."
                  rows="4"
                ></textarea>
              </div>
              <button @click="updateStatus" class="btn-save" :disabled="saving">
                {{ saving ? '儲存中...' : '💾 儲存變更' }}
              </button>
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
      saving: false,
      submissions: [],
      availableForms: [],
      filterFormId: '',
      filterStatus: '',
      searchQuery: '',
      pagination: {
        total: 0,
        limit: 20,
        offset: 0
      },
      showModal: false,
      selectedItem: null,
      formSchemas: {},
      editingStatus: 'pending',
      editingNotes: ''
    };
  },
  computed: {
    currentPage() {
      return Math.floor(this.pagination.offset / this.pagination.limit) + 1;
    },
    totalPages() {
      return Math.ceil(this.pagination.total / this.pagination.limit);
    },
    filteredSubmissions() {
      let filtered = this.submissions;

      // 狀態篩選
      if (this.filterStatus) {
        filtered = filtered.filter(item => item.status === this.filterStatus);
      }

      // 搜尋篩選（搜尋名稱和提交資料內容）
      if (this.searchQuery) {
        const query = this.searchQuery.toLowerCase();
        filtered = filtered.filter(item => {
          // 搜尋表單名稱
          if (item.form_name && item.form_name.toLowerCase().includes(query)) {
            return true;
          }

          // 搜尋觸發問題
          if (item.trigger_question && item.trigger_question.toLowerCase().includes(query)) {
            return true;
          }

          // 搜尋用戶ID
          if (item.user_id && item.user_id.toLowerCase().includes(query)) {
            return true;
          }

          // 搜尋提交資料的值
          if (item.submitted_data) {
            const dataValues = Object.values(item.submitted_data);
            return dataValues.some(value =>
              String(value).toLowerCase().includes(query)
            );
          }

          return false;
        });
      }

      return filtered;
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

    getStatusLabel(status) {
      const labels = {
        pending: '⏳ 待處理',
        processing: '🔄 處理中',
        completed: '✅ 已完成',
        rejected: '❌ 已拒絕'
      };
      return labels[status] || labels.pending;
    },

    viewDetails(item) {
      this.selectedItem = item;
      this.editingStatus = item.status || 'pending';
      this.editingNotes = item.notes || '';
      this.showModal = true;
    },

    async updateStatus() {
      if (!this.selectedItem) return;

      this.saving = true;
      try {
        await axios.patch(`${RAG_API}/v1/form-submissions/${this.selectedItem.id}`, {
          status: this.editingStatus,
          notes: this.editingNotes,
          updated_by: this.vendor?.code || 'vendor'
        });

        alert('✅ 狀態已更新！');

        // 更新本地資料
        const index = this.submissions.findIndex(s => s.id === this.selectedItem.id);
        if (index !== -1) {
          this.submissions[index].status = this.editingStatus;
          this.submissions[index].notes = this.editingNotes;
        }

        this.selectedItem.status = this.editingStatus;
        this.selectedItem.notes = this.editingNotes;
      } catch (error) {
        console.error('更新狀態失敗', error);
        alert('更新失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.saving = false;
      }
    },

    closeModal() {
      this.showModal = false;
      this.selectedItem = null;
      this.editingStatus = 'pending';
      this.editingNotes = '';
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
  gap: 20px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-select {
  padding: 8px 36px 8px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  cursor: pointer;
  min-width: 160px;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23606266' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
  background-repeat: no-repeat;
  background-position: right 10px center;
  background-size: 18px;
  transition: all 0.3s;
}

.filter-select:hover {
  border-color: #409eff;
  background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23409eff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
}

.filter-select:focus {
  outline: none;
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.1);
}

.search-input {
  padding: 8px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  min-width: 260px;
  transition: all 0.3s;
}

.search-input:hover {
  border-color: #409eff;
}

.search-input:focus {
  outline: none;
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.1);
}

.search-input::placeholder {
  color: #909399;
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
  border-radius: 4px;
  font-size: 13px;
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
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  padding: 25px 30px;
  border-bottom: 1px solid #f0f0f0;
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

/* 狀態標籤樣式 */
.status-badge {
  padding: 5px 12px;
  white-space: nowrap;
}

.status-pending {
  border: 1px solid #ffc107;
}

.status-processing {
  background: #cfe2ff;
  color: #084298;
  border: 1px solid #0d6efd;
}

.status-completed {
  border: 1px solid #198754;
}

.status-rejected {
  background: #f8d7da;
  color: #842029;
  border: 1px solid #dc3545;
}

/* 狀態編輯器 */
.status-editor {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-field label {
  display: block;
  font-size: 13px;
  color: #555;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-select {
  padding: 10px 14px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 15px;
  background: white;
  cursor: pointer;
  transition: all 0.3s;
}

.status-select:hover {
  border-color: #667eea;
}

.status-select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.notes-textarea {
  padding: 12px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  transition: all 0.3s;
}

.notes-textarea:hover {
  border-color: #667eea;
}

.notes-textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.btn-save {
  padding: 12px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  align-self: flex-start;
}

.btn-save:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
