<template>
  <div>
    <h2>🏢 業態類型管理</h2>

    <!-- 說明區塊 -->
    <InfoPanel :config="helpTexts.businessTypes" />

    <!-- 工具列 -->
    <div class="toolbar">
      <select v-model="filterActive" @change="loadBusinessTypes">
        <option value="true">已啟用</option>
        <option value="">全部狀態</option>
        <option value="false">已停用</option>
      </select>
      <button @click="showCreateModal" class="btn-primary btn-sm">新增業態類型</button>
    </div>

    <!-- 業態類型列表 -->
    <div v-if="loading" class="loading"><p>載入中...</p></div>

    <div v-else-if="businessTypesList.length === 0" class="empty-state">
      <p>沒有找到業態類型配置</p>
    </div>

    <div v-else class="business-types-list">
      <table>
        <thead>
          <tr>
            <th width="60">ID</th>
            <th width="150">類型值</th>
            <th>顯示名稱</th>
            <th>說明</th>
            <th width="80">顏色</th>
            <th width="80">狀態</th>
            <th width="200">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="type in businessTypesList" :key="type.id">
            <td>{{ type.id }}</td>
            <td><code>{{ type.type_value }}</code></td>
            <td>
              <span class="badge" :class="'type-' + (type.color || 'gray')">
                {{ type.display_name }}
              </span>
            </td>
            <td><small>{{ type.description || '-' }}</small></td>
            <td>
              <span class="color-badge" :class="'color-' + (type.color || 'gray')">
                {{ type.color || '-' }}
              </span>
            </td>
            <td>
              <span class="status" :class="type.is_active ? 'active' : 'inactive'">
                {{ type.is_active ? '✓ 啟用' : '✗ 停用' }}
              </span>
            </td>
            <td>
              <button @click="editBusinessType(type)" class="btn-edit btn-sm">編輯</button>
              <button
                v-if="type.is_active"
                @click="toggleActive(type)"
                class="btn-delete btn-sm"
              >
                停用
              </button>
              <button
                v-else
                @click="toggleActive(type)"
                class="btn-success btn-sm"
              >
                啟用
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 編輯/新增 Modal -->
    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop style="max-width: 600px;">
        <h2>{{ editingItem ? '✏️ 編輯業態類型' : '➕ 新增業態類型' }}</h2>

        <form @submit.prevent="saveBusinessType">
          <div class="form-group">
            <label>類型值 *</label>
            <input
              v-model="formData.type_value"
              required
              placeholder="例如：full_service, property_management"
              :disabled="editingItem"
              maxlength="50"
              pattern="[a-z_]+"
              title="只能使用小寫英文字母和底線"
            />
            <small v-if="!editingItem">類型值一旦建立不可修改（用於 vendors.business_types 陣列）</small>
            <small v-else style="color: #999;">類型值不可修改</small>
          </div>

          <div class="form-group">
            <label>顯示名稱 *</label>
            <input
              v-model="formData.display_name"
              required
              placeholder="例如：包租型、代管型"
              maxlength="100"
            />
            <small>在前端顯示的名稱</small>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>顏色標籤</label>
              <select v-model="formData.color">
                <option value="">無</option>
                <option value="blue">藍色 (Blue)</option>
                <option value="green">綠色 (Green)</option>
                <option value="orange">橙色 (Orange)</option>
                <option value="purple">紫色 (Purple)</option>
                <option value="red">紅色 (Red)</option>
                <option value="gray">灰色 (Gray)</option>
              </select>
              <small>用於前端顯示</small>
            </div>
          </div>

          <div class="form-group">
            <label>說明</label>
            <textarea
              v-model="formData.description"
              rows="3"
              placeholder="描述此業態類型的特點和用途..."
            ></textarea>
          </div>

          <div class="form-group">
            <label>語氣 Prompt</label>
            <textarea
              v-model="formData.tone_prompt"
              rows="8"
              placeholder="填寫此業態的語氣調整 Prompt，用於 LLM 優化器...

例如：
業種特性：包租型業者 - 提供全方位服務，直接負責租賃管理

語氣要求：
• 使用主動承諾語氣：「我們會」、「公司將」
• 避免被動引導：不要用「請您聯繫」、「建議」等

範例轉換：
❌ 「請您與房東聯繫處理」
✅ 「我們會立即為您處理」"
            ></textarea>
            <small>這段 prompt 會在 LLM 生成回答時用於調整語氣（可選）</small>
          </div>

          <div class="form-actions">
            <button type="button" @click="closeModal" class="btn-secondary btn-sm">取消</button>
            <button type="submit" class="btn-primary btn-sm" :disabled="saving">
              {{ saving ? '儲存中...' : '儲存' }}
            </button>
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

const API_BASE = `${API_BASE_URL}/rag-api/v1`;  // 使用統一的 API 配置

export default {
  name: 'BusinessTypesConfigView',
  components: {
    InfoPanel
  },
  data() {
    return {
      helpTexts,
      businessTypesList: [],
      filterActive: 'true',
      loading: false,
      showModal: false,
      editingItem: null,
      saving: false,
      formData: {
        type_value: '',
        display_name: '',
        description: '',
        color: '',
        tone_prompt: ''
      }
    };
  },
  mounted() {
    this.loadBusinessTypes();
  },
  methods: {
    async loadBusinessTypes() {
      this.loading = true;
      try {
        const params = {};
        if (this.filterActive !== '') params.is_active = this.filterActive === 'true';

        const response = await axios.get(`${API_BASE}/business-types-config`, { params });
        this.businessTypesList = response.data.business_types || [];
      } catch (error) {
        console.error('載入業態類型失敗', error);
        alert('載入失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },

    showCreateModal() {
      this.editingItem = null;
      this.formData = {
        type_value: '',
        display_name: '',
        description: '',
        color: '',
        tone_prompt: ''
      };
      this.showModal = true;
    },

    editBusinessType(type) {
      this.editingItem = type;
      this.formData = {
        type_value: type.type_value,
        display_name: type.display_name,
        description: type.description || '',
        color: type.color || '',
        tone_prompt: type.tone_prompt || ''
      };
      this.showModal = true;
    },

    closeModal() {
      this.showModal = false;
      this.editingItem = null;
    },

    async saveBusinessType() {
      this.saving = true;
      try {
        if (this.editingItem) {
          // 更新
          await axios.put(
            `${API_BASE}/business-types-config/${this.editingItem.type_value}`,
            {
              display_name: this.formData.display_name,
              description: this.formData.description,
              color: this.formData.color,
              tone_prompt: this.formData.tone_prompt
            }
          );
          alert('✅ 業態類型已更新');
        } else {
          // 新增
          await axios.post(`${API_BASE}/business-types-config`, this.formData);
          alert('✅ 業態類型已新增');
        }

        this.closeModal();
        this.loadBusinessTypes();
      } catch (error) {
        console.error('儲存失敗', error);
        alert('❌ 儲存失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.saving = false;
      }
    },

    async toggleActive(type) {
      const action = type.is_active ? '停用' : '啟用';
      if (!confirm(`確定要${action}「${type.display_name}」嗎？`)) return;

      try {
        if (type.is_active) {
          // 停用
          await axios.delete(`${API_BASE}/business-types-config/${type.type_value}`);
        } else {
          // 啟用
          await axios.put(`${API_BASE}/business-types-config/${type.type_value}`, {
            is_active: true
          });
        }

        alert(`✅ 已${action}業態類型`);
        this.loadBusinessTypes();
      } catch (error) {
        console.error('操作失敗', error);
        alert('❌ 操作失敗：' + (error.response?.data?.detail || error.message));
      }
    }
  }
};
</script>

<style scoped>
.info-box {
  background: #f0f7ff;
  border-left: 4px solid #409eff;
  padding: 15px 20px;
  margin-bottom: 20px;
  border-radius: 4px;
}

.info-box p {
  margin: 0 0 10px 0;
  color: #333;
}

.info-box ul {
  margin: 5px 0 0 20px;
  color: #666;
}

.info-box li {
  margin: 5px 0;
}

.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  align-items: center;
}

.toolbar select {
  padding: 8px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: white;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #909399;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #909399;
  background: #f5f7fa;
  border-radius: 4px;
}

.business-types-list table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.business-types-list th,
.business-types-list td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #ebeef5;
}

.business-types-list th {
  background: #f5f7fa;
  font-weight: 600;
  color: #606266;
}

.business-types-list tbody tr:hover {
  background: #f5f7fa;
}

.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 3px;
  font-size: 12px;
  font-weight: 500;
}

.badge-small {
  padding: 2px 6px;
  font-size: 11px;
}

.type-blue { background: #e1f3ff; color: #409eff; }
.type-green { background: #e1f3d8; color: #67c23a; }
.type-orange { background: #fdf6ec; color: #e6a23c; }
.type-purple { background: #f4e8ff; color: #9c27b0; }
.type-red { background: #fef0f0; color: #f56c6c; }
.type-gray { background: #e4e7ed; color: #606266; }

.color-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 500;
  border: 1px solid #dcdfe6;
}

.color-blue { background: #409eff; color: white; }
.color-green { background: #67c23a; color: white; }
.color-orange { background: #e6a23c; color: white; }
.color-purple { background: #9c27b0; color: white; }
.color-red { background: #f56c6c; color: white; }
.color-gray { background: #909399; color: white; }

.status {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 3px;
  font-size: 12px;
  font-weight: 500;
}

.status.active {
  background: #e1f3d8;
  color: #67c23a;
}

.status.inactive {
  background: #fef0f0;
  color: #f56c6c;
}

.link {
  color: #409eff;
  cursor: pointer;
  text-decoration: underline;
}

.link:hover {
  color: #66b1ff;
}

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
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 20px;
  color: #303133;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #606266;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-group small {
  display: block;
  margin-top: 5px;
  color: #909399;
  font-size: 12px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.usage-header {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
}

.usage-list {
  max-height: 400px;
  overflow-y: auto;
}

.usage-list table {
  width: 100%;
  border-collapse: collapse;
}

.usage-list th,
.usage-list td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #ebeef5;
}

.usage-list th {
  background: #f5f7fa;
  font-weight: 600;
  color: #606266;
  position: sticky;
  top: 0;
}
</style>
