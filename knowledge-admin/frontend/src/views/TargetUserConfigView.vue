<template>
  <div>
    <h2>👥 目標用戶管理</h2>

    <!-- 說明區塊 -->
    <InfoPanel :config="helpTexts.targetUsers" />

    <!-- 工具列 -->
    <div class="toolbar">
      <button @click="showCreateModal" class="btn-primary btn-sm">新增目標用戶</button>
    </div>

    <!-- 目標用戶列表 -->
    <div v-if="loading" class="loading"><p>載入中...</p></div>

    <div v-else-if="targetUsersList.length === 0" class="empty-state">
      <p>沒有找到目標用戶配置</p>
    </div>

    <div v-else class="target-users-list">
      <table>
        <thead>
          <tr>
            <th width="60">ID</th>
            <th width="150">用戶值</th>
            <th>顯示名稱</th>
            <th>說明</th>
            <th width="80">狀態</th>
            <th width="200">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in targetUsersList" :key="user.id">
            <td>{{ user.id }}</td>
            <td><code>{{ user.user_value }}</code></td>
            <td>
              <span class="badge badge-user">
                {{ user.display_name }}
              </span>
            </td>
            <td><small>{{ user.description || '-' }}</small></td>
            <td>
              <span class="status" :class="user.is_active ? 'active' : 'inactive'">
                {{ user.is_active ? '✓ 啟用' : '✗ 停用' }}
              </span>
            </td>
            <td>
              <button @click="editTargetUser(user)" class="btn-edit btn-sm">編輯</button>
              <button
                v-if="user.is_active"
                @click="toggleActive(user)"
                class="btn-delete btn-sm"
              >
                停用
              </button>
              <button
                v-else
                @click="toggleActive(user)"
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
        <h2>{{ editingItem ? '✏️ 編輯目標用戶' : '➕ 新增目標用戶' }}</h2>

        <form @submit.prevent="saveTargetUser">
          <div class="form-group">
            <label>用戶值 *</label>
            <input
              v-model="formData.user_value"
              required
              placeholder="例如：tenant, landlord, property_manager"
              :disabled="editingItem"
              maxlength="50"
              pattern="[a-z_]+"
              title="只能使用小寫英文字母和底線"
            />
            <small v-if="!editingItem">用戶值一旦建立不可修改（用於 knowledge_base.target_user 陣列）</small>
            <small v-else style="color: #999;">用戶值不可修改</small>
          </div>

          <div class="form-group">
            <label>顯示名稱 *</label>
            <input
              v-model="formData.display_name"
              required
              placeholder="例如：租客、房東、物業管理師"
              maxlength="100"
            />
            <small>在前端顯示的名稱</small>
          </div>

          <div class="form-group">
            <label>說明</label>
            <textarea
              v-model="formData.description"
              rows="3"
              placeholder="描述此目標用戶的特徵和用途..."
            ></textarea>
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

const API_BASE = '/api';

export default {
  name: 'TargetUserConfigView',
  components: {
    InfoPanel
  },
  data() {
    return {
      helpTexts,
      targetUsersList: [],
      loading: false,
      showModal: false,
      editingItem: null,
      saving: false,
      formData: {
        user_value: '',
        display_name: '',
        description: ''
      }
    };
  },
  mounted() {
    this.loadTargetUsers();
  },
  methods: {
    async loadTargetUsers() {
      this.loading = true;
      try {
        const response = await axios.get(`${API_BASE}/target-users-config`);
        this.targetUsersList = response.data.target_users || [];
      } catch (error) {
        console.error('載入目標用戶失敗', error);
        alert('載入失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },

    showCreateModal() {
      this.editingItem = null;
      this.formData = {
        user_value: '',
        display_name: '',
        description: ''
      };
      this.showModal = true;
    },

    editTargetUser(user) {
      this.editingItem = user;
      this.formData = {
        user_value: user.user_value,
        display_name: user.display_name,
        description: user.description || ''
      };
      this.showModal = true;
    },

    closeModal() {
      this.showModal = false;
      this.editingItem = null;
    },

    async saveTargetUser() {
      this.saving = true;
      try {
        if (this.editingItem) {
          // 更新
          await axios.put(
            `${API_BASE}/target-users-config/${this.editingItem.user_value}`,
            {
              display_name: this.formData.display_name,
              description: this.formData.description
            }
          );
          alert('✅ 目標用戶已更新');
        } else {
          // 新增
          await axios.post(`${API_BASE}/target-users-config`, this.formData);
          alert('✅ 目標用戶已新增');
        }

        this.closeModal();
        this.loadTargetUsers();
      } catch (error) {
        console.error('儲存失敗', error);
        alert('❌ 儲存失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.saving = false;
      }
    },

    async toggleActive(user) {
      const action = user.is_active ? '停用' : '啟用';
      if (!confirm(`確定要${action}「${user.display_name}」嗎？`)) return;

      try {
        if (user.is_active) {
          // 停用
          await axios.delete(`${API_BASE}/target-users-config/${user.user_value}`);
        } else {
          // 啟用
          await axios.put(`${API_BASE}/target-users-config/${user.user_value}`, {
            display_name: user.display_name,
            description: user.description,
            is_active: true
          });
        }

        alert(`✅ 已${action}目標用戶`);
        this.loadTargetUsers();
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

.warning-box {
  background: #fef0f0;
  border-left: 4px solid #f56c6c;
  padding: 15px 20px;
  margin-bottom: 20px;
  border-radius: 4px;
}

.warning-box p {
  margin: 0 0 10px 0;
  color: #333;
  line-height: 1.6;
}

.warning-box p:last-child {
  margin-bottom: 0;
}

.warning-box code {
  background: #fff;
  padding: 2px 6px;
  border-radius: 3px;
  color: #f56c6c;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  align-items: center;
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

.target-users-list table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.target-users-list th,
.target-users-list td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #ebeef5;
}

.target-users-list th {
  background: #f5f7fa;
  font-weight: 600;
  color: #606266;
}

.target-users-list tbody tr:hover {
  background: #f5f7fa;
}

.text-center {
  text-align: center !important;
}

.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 3px;
  font-size: 12px;
  font-weight: 500;
}

.badge-user {
  background: #e1f3ff;
  color: #409eff;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

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
</style>
