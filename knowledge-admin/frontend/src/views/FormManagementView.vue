<template>
  <div>
    <h2>📋 表單管理</h2>

    <!-- 工具列 -->
    <div class="toolbar">
      <select v-model="filterVendor" @change="loadForms">
        <option value="">全部業者</option>
        <option value="null">全局表單</option>
        <option value="1">業者 1</option>
      </select>
      <select v-model="filterActive" @change="loadForms">
        <option value="">全部狀態</option>
        <option value="true">已啟用</option>
        <option value="false">已停用</option>
      </select>
      <button @click="$router.push('/forms/new')" class="btn-primary btn-sm">新增表單</button>
    </div>

    <!-- 統計資訊 -->
    <div v-if="stats" class="stats-cards">
      <div class="stat-card">
        <div class="stat-title">總表單數</div>
        <div class="stat-value">{{ stats.total }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">已啟用</div>
        <div class="stat-value success">{{ stats.active }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">全局表單</div>
        <div class="stat-value info">{{ stats.global }}</div>
      </div>
    </div>

    <!-- 表單列表 -->
    <div v-if="loading" class="loading"><p>載入中...</p></div>

    <div v-else-if="formList.length === 0" class="empty-state">
      <p>尚無表單，請點擊「新增表單」開始建立。</p>
    </div>

    <div v-else class="knowledge-list">
      <table>
        <thead>
          <tr>
            <th width="150">表單ID</th>
            <th>表單名稱</th>
            <th width="200">描述</th>
            <th width="80">欄位數</th>
            <th width="100">業者</th>
            <th width="80">狀態</th>
            <th width="100">建立時間</th>
            <th width="250">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(form, index) in formList" :key="form.id || form.form_id || index">
            <td><code>{{ form.form_id }}</code></td>
            <td><strong>{{ form.form_name }}</strong></td>
            <td>{{ form.description || '-' }}</td>
            <td class="center">{{ form.fields.length }}</td>
            <td class="center">
              <span v-if="form.vendor_id" class="badge">業者 {{ form.vendor_id }}</span>
              <span v-else class="badge type-global">全局</span>
            </td>
            <td>
              <span class="status" :class="form.is_active ? 'enabled' : 'disabled'">
                {{ form.is_active ? '✓ 啟用' : '✗ 停用' }}
              </span>
            </td>
            <td>{{ formatDate(form.created_at) }}</td>
            <td>
              <button @click="viewForm(form)" class="btn-sm btn-info">查看</button>
              <button @click="editForm(form)" class="btn-sm btn-edit">編輯</button>
              <button @click="toggleActive(form)" class="btn-sm" :class="form.is_active ? 'btn-warning' : 'btn-success'">
                {{ form.is_active ? '停用' : '啟用' }}
              </button>
              <button @click="deleteForm(form)" class="btn-sm btn-delete">刪除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 查看表單 Modal -->
    <div v-if="viewingForm" class="modal-overlay" @click="viewingForm = null">
      <div class="modal-content" @click.stop style="max-width: 800px;">
        <h2>查看表單</h2>

        <div class="form-detail">
          <div class="detail-row">
            <label>表單ID：</label>
            <code>{{ viewingForm.form_id }}</code>
          </div>
          <div class="detail-row">
            <label>表單名稱：</label>
            <span>{{ viewingForm.form_name }}</span>
          </div>
          <div class="detail-row" v-if="viewingForm.description">
            <label>描述：</label>
            <span>{{ viewingForm.description }}</span>
          </div>
          <div class="detail-row" v-if="viewingForm.default_intro">
            <label>引導語：</label>
            <span>{{ viewingForm.default_intro }}</span>
          </div>
          <div class="detail-row">
            <label>業者：</label>
            <span>{{ viewingForm.vendor_id ? `業者 ${viewingForm.vendor_id}` : '全局' }}</span>
          </div>
          <div class="detail-row">
            <label>狀態：</label>
            <span :class="viewingForm.is_active ? 'success' : 'muted'">
              {{ viewingForm.is_active ? '已啟用' : '已停用' }}
            </span>
          </div>

          <h3 style="margin-top: 20px;">📝 表單欄位 ({{ viewingForm.fields.length }})</h3>
          <div class="field-list">
            <div v-for="(field, index) in viewingForm.fields" :key="index" class="field-item">
              <div class="field-header">
                <span class="field-number">{{ index + 1 }}</span>
                <strong>{{ field.field_label }}</strong>
                <code class="field-name">{{ field.field_name }}</code>
                <span class="badge" :class="'type-' + field.field_type">{{ field.field_type }}</span>
                <span v-if="field.required" class="required">*必填</span>
              </div>
              <div class="field-body">
                <p class="field-prompt">💬 {{ field.prompt }}</p>
                <div class="field-meta">
                  <span v-if="field.validation_type">驗證：{{ field.validation_type }}</span>
                  <span v-if="field.max_length">長度：≤ {{ field.max_length }}</span>
                  <span v-if="field.options">選項：{{ field.options.join(', ') }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 關聯的知識 -->
          <h3 style="margin-top: 20px;">🔗 關聯的知識</h3>
          <div v-if="loadingKnowledge" class="loading-small">載入中...</div>
          <div v-else-if="relatedKnowledge.length === 0" class="empty-hint">
            此表單尚未與任何知識關聯
          </div>
          <ul v-else class="knowledge-links">
            <li v-for="kb in relatedKnowledge" :key="kb.id">
              <strong>{{ kb.question_summary }}</strong>
              <span class="meta">(ID: {{ kb.id }}, {{ kb.scope }})</span>
            </li>
          </ul>
        </div>

        <div class="modal-actions">
          <button @click="editForm(viewingForm)" class="btn-edit">✏️ 編輯</button>
          <button @click="viewingForm = null" class="btn-secondary">關閉</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import api from '../utils/api';

export default {
  name: 'FormManagementView',
  setup() {
    const router = useRouter();
    const formList = ref([]);
    const loading = ref(false);
    const filterVendor = ref('');
    const filterActive = ref('');
    const viewingForm = ref(null);
    const relatedKnowledge = ref([]);
    const loadingKnowledge = ref(false);

    // 統計數據
    const stats = computed(() => {
      if (!Array.isArray(formList.value) || formList.value.length === 0) return null;
      return {
        total: formList.value.length,
        active: formList.value.filter(f => f && f.is_active).length,
        global: formList.value.filter(f => f && !f.vendor_id).length
      };
    });

    // 載入表單列表
    const loadForms = async () => {
      loading.value = true;

      // 臨時測試：使用硬編碼數據
      console.log('[Debug] loadForms function called');

      try {
        const params = {};
        if (filterVendor.value) {
          params.vendor_id = filterVendor.value === 'null' ? null : parseInt(filterVendor.value);
        }
        if (filterActive.value) {
          params.is_active = filterActive.value === 'true';
        }

        console.log('[Debug] Requesting /rag-api/v1/forms with params:', params);
        const response = await api.get('/rag-api/v1/forms', { params });
        console.log('[Debug] Response received:', response);
        console.log('[Debug] Response type:', typeof response);
        console.log('[Debug] Is Array?', Array.isArray(response));

        // 確保返回的是數組
        let rawData = [];
        if (Array.isArray(response)) {
          rawData = response;
        } else if (response && Array.isArray(response.forms)) {
          rawData = response.forms;
        } else if (response && response.data && Array.isArray(response.data)) {
          rawData = response.data;
        } else {
          console.error('[Debug] Unexpected response format:', response);
          formList.value = [];
          alert('API 返回格式錯誤');
          return;
        }

        // 過濾掉無效的項目，確保每個項目都有 form_id
        formList.value = rawData.filter(item => {
          if (!item) {
            console.warn('[Debug] Found null/undefined item in response');
            return false;
          }
          if (!item.form_id) {
            console.warn('[Debug] Found item without form_id:', item);
            return false;
          }
          return true;
        });

        console.log('[Debug] formList.value after filtering:', formList.value);
        console.log('[Debug] Total valid forms:', formList.value.length);
      } catch (error) {
        console.error('載入表單失敗:', error);
        alert('載入表單失敗: ' + error.message);
        formList.value = [];
      } finally {
        loading.value = false;
      }
    };

    // 查看表單
    const viewForm = async (form) => {
      if (!form || !form.form_id) {
        console.error('Invalid form object:', form);
        alert('表單資料錯誤');
        return;
      }

      viewingForm.value = form;

      // 載入關聯的知識
      loadingKnowledge.value = true;
      try {
        const response = await api.get(`/rag-api/v1/forms/${form.form_id}/related-knowledge`);
        relatedKnowledge.value = Array.isArray(response) ? response : [];
      } catch (error) {
        console.error('載入關聯知識失敗:', error);
        relatedKnowledge.value = [];
      } finally {
        loadingKnowledge.value = false;
      }
    };

    // 編輯表單
    const editForm = (form) => {
      if (!form || !form.form_id) {
        console.error('Invalid form object:', form);
        alert('表單資料錯誤');
        return;
      }
      router.push(`/forms/${form.form_id}/edit`);
    };

    // 切換啟用狀態
    const toggleActive = async (form) => {
      if (!form || !form.form_id) {
        console.error('Invalid form object:', form);
        alert('表單資料錯誤');
        return;
      }

      if (!confirm(`確定要${form.is_active ? '停用' : '啟用'}此表單嗎？`)) {
        return;
      }

      try {
        await api.put(`/rag-api/v1/forms/${form.form_id}`, {
          is_active: !form.is_active
        });
        alert('更新成功');
        loadForms();
      } catch (error) {
        console.error('更新失敗:', error);
        alert('更新失敗: ' + (error.response?.data?.detail || error.message));
      }
    };

    // 刪除表單
    const deleteForm = async (form) => {
      if (!form || !form.form_id) {
        console.error('Invalid form object:', form);
        alert('表單資料錯誤');
        return;
      }

      if (!confirm(`確定要刪除表單「${form.form_name}」嗎？\n\n⚠️ 如果有知識關聯到此表單，刪除會失敗。`)) {
        return;
      }

      try {
        await api.delete(`/rag-api/v1/forms/${form.form_id}`);
        alert('刪除成功');
        loadForms();
      } catch (error) {
        console.error('刪除失敗:', error);
        alert('刪除失敗: ' + (error.response?.data?.detail || error.message));
      }
    };

    // 格式化日期
    const formatDate = (dateString) => {
      const date = new Date(dateString);
      return date.toLocaleDateString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      });
    };

    onMounted(() => {
      loadForms();
    });

    return {
      formList,
      loading,
      filterVendor,
      filterActive,
      stats,
      viewingForm,
      relatedKnowledge,
      loadingKnowledge,
      loadForms,
      viewForm,
      editForm,
      toggleActive,
      deleteForm,
      formatDate
    };
  }
};
</script>

<style scoped>
/* 統計卡片 */
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

/* 表格樣式 */
.knowledge-list table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.knowledge-list th {
  padding: 12px;
  text-align: left;
  background: #f5f7fa;
  border-bottom: 2px solid #dcdfe6;
  font-weight: 600;
  color: #606266;
}

.knowledge-list td {
  padding: 12px;
  border-bottom: 1px solid #ebeef5;
}

.knowledge-list tbody tr:hover {
  background: #f5f7fa;
}

/* 代碼標籤 */
code {
  background: #f4f4f5;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 13px;
  color: #606266;
  font-family: 'Monaco', 'Menlo', monospace;
}

/* 徽章樣式 */
.badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.type-global {
  background: #909399;
  color: white;
}

/* 狀態標籤 */
.status {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status.enabled {
  background: #67C23A;
  color: white;
}

.status.disabled {
  background: #909399;
  color: white;
}

/* 按鈕樣式 */
.btn-sm {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  margin-right: 5px;
  min-width: 70px;
  text-align: center;
  display: inline-block;
  line-height: 1.5;
}

.btn-primary {
  background: #409EFF;
  color: white;
}

.btn-primary:hover {
  background: #66B1FF;
}

.btn-info {
  background: #909399;
  color: white;
}

.btn-info:hover {
  background: #a6a9ad;
}

.btn-edit {
  background: #E6A23C;
  color: white;
}

.btn-edit:hover {
  background: #ebb563;
}

.btn-success {
  background: #67C23A;
  color: white;
}

.btn-success:hover {
  background: #85ce61;
}

.btn-warning {
  background: #E6A23C;
  color: white;
}

.btn-warning:hover {
  background: #ebb563;
}

.btn-delete {
  background: #F56C6C;
  color: white;
}

.btn-delete:hover {
  background: #f78989;
}

.center {
  text-align: center;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #909399;
  background: white;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #909399;
  background: white;
}

/* Modal 樣式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  padding: 30px;
  max-width: 800px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
}

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 20px;
  color: #303133;
  border-bottom: 1px solid #ebeef5;
  padding-bottom: 15px;
}

/* 表單詳情 */
.form-detail {
  margin: 20px 0;
}

.detail-row {
  padding: 12px 0;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  gap: 15px;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-row label {
  font-weight: 600;
  min-width: 100px;
  color: #606266;
  font-size: 14px;
}

.detail-row span, .detail-row code {
  flex: 1;
  color: #303133;
}

/* 欄位列表 */
.field-list {
  margin-top: 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.field-item {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

.field-item:hover {
  border-color: #409EFF;
}

.field-header {
  background: #f5f7fa;
  padding: 12px 15px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid #dcdfe6;
}

.field-number {
  background: #409EFF;
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.field-title {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.field-type-badge {
  background: #ecf5ff;
  color: #409EFF;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 12px;
  font-weight: 500;
}

.field-name {
  margin-left: auto;
  color: #909399;
  font-size: 12px;
  font-family: 'Monaco', 'Menlo', monospace;
}

.field-content {
  padding: 12px 15px;
  background: white;
}

.field-property {
  display: flex;
  padding: 6px 0;
  font-size: 13px;
}

.field-property strong {
  min-width: 90px;
  color: #606266;
  font-weight: 600;
}

.field-property span {
  color: #303133;
}

/* 關聯知識樣式 */
.related-knowledge {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.related-knowledge h3 {
  color: #303133;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
}

.knowledge-item {
  background: #f5f7fa;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px 12px;
  margin-bottom: 8px;
  font-size: 13px;
  color: #606266;
}

.knowledge-item:hover {
  background: #ecf5ff;
  border-color: #409EFF;
}

.required {
  color: #F56C6C;
  font-weight: bold;
}

.field-body {
  padding: 12px;
}

.field-prompt {
  margin: 0 0 8px 0;
  color: #303133;
}

.field-meta {
  display: flex;
  gap: 10px;
  font-size: 0.9em;
  color: #606266;
}

.field-meta span {
  padding: 3px 8px;
  background: #f4f4f5;
  border-radius: 3px;
}

/* 知識連結 */
.knowledge-links {
  list-style: none;
  padding: 0;
  margin: 10px 0;
}

.knowledge-links li {
  padding: 8px 12px;
  background: #f5f7fa;
  border-left: 3px solid #409EFF;
  margin-bottom: 6px;
}

.knowledge-links .meta {
  color: #909399;
  font-size: 0.9em;
  margin-left: 10px;
}

.empty-hint {
  color: #909399;
  font-style: italic;
  padding: 15px;
  text-align: center;
  background: #f5f7fa;
  border-radius: 4px;
}

.loading-small {
  text-align: center;
  padding: 15px;
  color: #909399;
}
</style>
