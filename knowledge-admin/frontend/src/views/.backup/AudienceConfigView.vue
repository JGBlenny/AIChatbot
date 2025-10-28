<template>
  <div>
    <h2>👥 受眾配置管理</h2>

    <div class="info-box">
      <p><strong>📝 說明：</strong></p>
      <ul>
        <li>受眾（Audience）用於定義知識的目標對象（如：租客、管理師、房東）</li>
        <li>每個受眾可以用於知識庫的篩選和分類</li>
        <li>業態類型（如包租型、代管型）會在業者層級控制知識可見性</li>
      </ul>
    </div>

    <!-- 工具列 -->
    <div class="toolbar">
      <select v-model="filterActive" @change="loadAudiences">
        <option value="true">已啟用</option>
        <option value="">全部狀態</option>
        <option value="false">已停用</option>
      </select>
      <button @click="showCreateModal" class="btn-primary btn-sm">新增受眾</button>
      <button @click="clearCache" class="btn-info btn-sm" title="清除緩存">清除緩存</button>
    </div>

    <!-- 受眾列表 -->
    <div v-if="loading" class="loading"><p>載入中...</p></div>

    <div v-else-if="audienceList.length === 0" class="empty-state">
      <p>沒有找到受眾配置</p>
    </div>

    <div v-else class="audience-list">
      <table>
        <thead>
          <tr>
            <th width="60">ID</th>
            <th width="40">順序</th>
            <th width="150">受眾值</th>
            <th>顯示名稱</th>
            <th>說明</th>
            <th width="80">狀態</th>
            <th width="180">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="audience in audienceList" :key="audience.id">
            <td>{{ audience.id }}</td>
            <td>{{ audience.display_order }}</td>
            <td><code>{{ audience.audience_value }}</code></td>
            <td><strong>{{ audience.display_name }}</strong></td>
            <td><small>{{ audience.description || '-' }}</small></td>
            <td>
              <span class="status" :class="audience.is_active ? 'active' : 'inactive'">
                {{ audience.is_active ? '✓ 啟用' : '✗ 停用' }}
              </span>
            </td>
            <td>
              <button @click="editAudience(audience)" class="btn-edit btn-sm">編輯</button>
              <button
                v-if="audience.is_active"
                @click="toggleActive(audience)"
                class="btn-delete btn-sm"
              >
                停用
              </button>
              <button
                v-else
                @click="toggleActive(audience)"
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
        <h2>{{ editingItem ? '✏️ 編輯受眾' : '➕ 新增受眾' }}</h2>

        <form @submit.prevent="saveAudience">
          <div class="form-group">
            <label>受眾值 *</label>
            <input
              v-model="formData.audience_value"
              required
              placeholder="例如：租客、管理師、租客|管理師"
              :disabled="editingItem"
              maxlength="50"
            />
            <small v-if="!editingItem">受眾值一旦建立不可修改（用於 knowledge_base.audience 欄位）</small>
            <small v-else style="color: #999;">受眾值不可修改</small>
          </div>

          <div class="form-group">
            <label>顯示名稱 *</label>
            <input
              v-model="formData.display_name"
              required
              placeholder="例如：租客、管理師"
              maxlength="100"
            />
            <small>在前端下拉選單顯示的名稱</small>
          </div>

          <div class="form-group">
            <label>顯示順序</label>
            <input
              v-model.number="formData.display_order"
              type="number"
              placeholder="0"
              min="0"
            />
            <small>數字越小越前面</small>
          </div>

          <div class="form-group">
            <label>說明</label>
            <textarea
              v-model="formData.description"
              rows="3"
              placeholder="簡短說明此受眾的用途..."
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

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8100/api/v1';

export default {
  name: 'AudienceConfigView',
  data() {
    return {
      audienceList: [],
      filterActive: 'true',
      loading: false,
      showModal: false,
      editingItem: null,
      saving: false,
      formData: {
        audience_value: '',
        display_name: '',
        description: '',
        display_order: 0
      }
    };
  },
  mounted() {
    this.loadAudiences();
  },
  methods: {
    async loadAudiences() {
      this.loading = true;
      try {
        const params = {};
        if (this.filterActive !== '') params.is_active = this.filterActive === 'true';

        const response = await axios.get(`${API_BASE}/audience-config`, { params });
        this.audienceList = response.data.audiences || [];
      } catch (error) {
        console.error('載入受眾配置失敗', error);
        alert('載入失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },

    showCreateModal() {
      this.editingItem = null;
      this.formData = {
        audience_value: '',
        display_name: '',
        description: '',
        display_order: 0
      };
      this.showModal = true;
    },

    editAudience(audience) {
      this.editingItem = audience;
      this.formData = {
        audience_value: audience.audience_value,
        display_name: audience.display_name,
        description: audience.description || '',
        display_order: audience.display_order
      };
      this.showModal = true;
    },

    closeModal() {
      this.showModal = false;
      this.editingItem = null;
    },

    async saveAudience() {
      this.saving = true;
      try {
        const payload = {
          display_name: this.formData.display_name,
          description: this.formData.description,
          display_order: this.formData.display_order,
          business_scope: 'both'  // 統一設為 both，不再區分
        };

        if (this.editingItem) {
          // 更新
          await axios.put(
            `${API_BASE}/audience-config/${this.editingItem.audience_value}`,
            payload
          );
          alert('✅ 受眾配置已更新');
        } else {
          // 新增
          await axios.post(`${API_BASE}/audience-config`, {
            audience_value: this.formData.audience_value,
            ...payload
          });
          alert('✅ 受眾配置已新增');
        }

        this.closeModal();
        this.loadAudiences();
      } catch (error) {
        console.error('儲存失敗', error);
        alert('❌ 儲存失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.saving = false;
      }
    },

    async toggleActive(audience) {
      const action = audience.is_active ? '停用' : '啟用';
      if (!confirm(`確定要${action}「${audience.display_name}」嗎？`)) return;

      try {
        if (audience.is_active) {
          // 停用
          await axios.delete(`${API_BASE}/audience-config/${audience.audience_value}`);
        } else {
          // 啟用
          await axios.put(`${API_BASE}/audience-config/${audience.audience_value}`, {
            is_active: true
          });
        }

        alert(`✅ 已${action}受眾配置`);
        this.loadAudiences();
      } catch (error) {
        console.error('操作失敗', error);
        alert('❌ 操作失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    async clearCache() {
      if (!confirm('確定要清除 audience 映射緩存嗎？\n清除後下次查詢會自動從數據庫重新載入。')) return;

      try {
        await axios.post(`${API_BASE}/audience-config/clear-cache`);
        alert('✅ 緩存已清除');
      } catch (error) {
        console.error('清除緩存失敗', error);
        alert('❌ 清除緩存失敗：' + (error.response?.data?.detail || error.message));
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
  padding: 60px 20px;
  color: #909399;
  background: #f5f7fa;
  border-radius: 4px;
}

.audience-list table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.audience-list th,
.audience-list td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #ebeef5;
}

.audience-list th {
  background: #f5f7fa;
  font-weight: 600;
  color: #606266;
}

.audience-list tbody tr:hover {
  background: #f5f7fa;
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
