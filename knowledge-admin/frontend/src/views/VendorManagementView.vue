<template>
  <div>
    <h2>🏢 業者管理</h2>

    <!-- 工具列 -->
    <div class="toolbar">
      <select v-model="filterActive" @change="loadVendors">
        <option value="">全部狀態</option>
        <option value="true">已啟用</option>
        <option value="false">已停用</option>
      </select>
      <button @click="showCreateModal" class="btn-primary">➕ 新增業者</button>
    </div>

    <!-- 業者列表 -->
    <div v-if="loading" class="loading"><p>載入中...</p></div>

    <div v-else class="vendor-list">
      <table>
        <thead>
          <tr>
            <th width="60">ID</th>
            <th width="120">代碼</th>
            <th>名稱</th>
            <th>簡稱</th>
            <th>聯絡電話</th>
            <th width="120">業態類型</th>
            <th>訂閱方案</th>
            <th width="80">狀態</th>
            <th width="280">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="vendor in vendorList" :key="vendor.id">
            <td>{{ vendor.id }}</td>
            <td><code>{{ vendor.code }}</code></td>
            <td><strong>{{ vendor.name }}</strong></td>
            <td>{{ vendor.short_name || '-' }}</td>
            <td>{{ vendor.contact_phone || '-' }}</td>
            <td>
              <span class="badge" :class="'type-' + vendor.business_type">
                {{ getBusinessTypeLabel(vendor.business_type) }}
              </span>
            </td>
            <td>
              <span class="badge" :class="'plan-' + vendor.subscription_plan">
                {{ getPlanLabel(vendor.subscription_plan) }}
              </span>
            </td>
            <td>
              <span class="status" :class="vendor.is_active ? 'active' : 'inactive'">
                {{ vendor.is_active ? '✓ 啟用' : '✗ 停用' }}
              </span>
            </td>
            <td>
              <button @click="editVendor(vendor)" class="btn-edit btn-sm">✏️ 編輯</button>
              <button @click="viewConfig(vendor)" class="btn-success btn-sm">⚙️ 配置</button>
              <button @click="viewStats(vendor)" class="btn-info btn-sm">📊 統計</button>
              <button @click="deleteVendor(vendor.id)" class="btn-delete btn-sm">🗑️ 停用</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 編輯/新增 Modal -->
    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop style="max-width: 700px;">
        <h2>{{ editingItem ? '✏️ 編輯業者' : '➕ 新增業者' }}</h2>

        <form @submit.prevent="saveVendor">
          <div class="form-row">
            <div class="form-group">
              <label>代碼 *</label>
              <input v-model="formData.code" required placeholder="VENDOR_A" :disabled="editingItem" />
              <small v-if="!editingItem">業者代碼一旦建立不可修改</small>
            </div>

            <div class="form-group">
              <label>簡稱</label>
              <input v-model="formData.short_name" placeholder="甲山林" />
            </div>
          </div>

          <div class="form-group">
            <label>名稱 *</label>
            <input v-model="formData.name" required placeholder="甲山林包租代管股份有限公司" />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>聯絡電話</label>
              <input v-model="formData.contact_phone" placeholder="02-1234-5678" />
            </div>

            <div class="form-group">
              <label>聯絡郵箱</label>
              <input v-model="formData.contact_email" type="email" placeholder="service@example.com" />
            </div>
          </div>

          <div class="form-group">
            <label>公司地址</label>
            <input v-model="formData.address" placeholder="台北市信義區..." />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>訂閱方案</label>
              <select v-model="formData.subscription_plan">
                <option value="basic">Basic - 基礎方案</option>
                <option value="standard">Standard - 標準方案</option>
                <option value="premium">Premium - 進階方案</option>
              </select>
            </div>

            <div class="form-group">
              <label>業態類型 *</label>
              <select v-model="formData.business_type" required>
                <option value="full_service">包租型 (Full Service)</option>
                <option value="property_management">代管型 (Property Management)</option>
              </select>
              <small>影響 AI 回答的語氣風格</small>
            </div>
          </div>

          <div v-if="editingItem" class="form-row">
            <div class="form-group">
              <label>狀態</label>
              <select v-model="formData.is_active">
                <option :value="true">啟用</option>
                <option :value="false">停用</option>
              </select>
            </div>
          </div>

          <div class="form-actions">
            <button type="submit" class="btn-primary" :disabled="saving">
              {{ saving ? '⏳ 儲存中...' : '💾 儲存' }}
            </button>
            <button type="button" @click="closeModal" class="btn-secondary">❌ 取消</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 統計 Modal -->
    <div v-if="showStatsModal" class="modal-overlay" @click="closeStatsModal">
      <div class="modal-content" @click.stop style="max-width: 600px;">
        <h2>📊 業者統計 - {{ statsData.vendor?.name }}</h2>

        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">配置參數總數</div>
            <div class="stat-value">{{ statsData.total_configs || 0 }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">業者專屬知識</div>
            <div class="stat-value">{{ statsData.knowledge?.vendor_knowledge || 0 }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">客製化知識</div>
            <div class="stat-value">{{ statsData.knowledge?.customized_knowledge || 0 }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">知識總計</div>
            <div class="stat-value">{{ statsData.knowledge?.total_knowledge || 0 }}</div>
          </div>
        </div>

        <div v-if="statsData.config_counts" class="config-breakdown">
          <h3>配置參數分類</h3>
          <table>
            <thead>
              <tr>
                <th>分類</th>
                <th>數量</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(count, category) in statsData.config_counts" :key="category">
                <td>{{ getCategoryLabel(category) }}</td>
                <td><strong>{{ count }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="form-actions">
          <button @click="closeStatsModal" class="btn-secondary">關閉</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

const RAG_API = '/rag-api/v1';

export default {
  name: 'VendorManagementView',
  data() {
    return {
      vendorList: [],
      filterActive: '',
      showModal: false,
      showStatsModal: false,
      editingItem: null,
      saving: false,
      loading: false,
      statsData: {},
      formData: {
        code: '',
        name: '',
        short_name: '',
        contact_phone: '',
        contact_email: '',
        address: '',
        subscription_plan: 'basic',
        business_type: 'property_management',
        is_active: true
      }
    };
  },
  mounted() {
    this.loadVendors();
  },
  methods: {
    async loadVendors() {
      this.loading = true;
      try {
        const params = {};
        if (this.filterActive !== '') {
          params.is_active = this.filterActive === 'true';
        }

        const response = await axios.get(`${RAG_API}/vendors`, { params });
        this.vendorList = response.data;
      } catch (error) {
        console.error('載入失敗', error);
        alert('載入失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },

    showCreateModal() {
      this.editingItem = null;
      this.formData = {
        code: '',
        name: '',
        short_name: '',
        contact_phone: '',
        contact_email: '',
        address: '',
        subscription_plan: 'basic',
        business_type: 'property_management',
        is_active: true
      };
      this.showModal = true;
    },

    editVendor(vendor) {
      this.editingItem = vendor;
      this.formData = {
        code: vendor.code,
        name: vendor.name,
        short_name: vendor.short_name || '',
        contact_phone: vendor.contact_phone || '',
        contact_email: vendor.contact_email || '',
        address: vendor.address || '',
        subscription_plan: vendor.subscription_plan,
        business_type: vendor.business_type || 'property_management',
        is_active: vendor.is_active
      };
      this.showModal = true;
    },

    async saveVendor() {
      this.saving = true;
      try {
        if (this.editingItem) {
          // 更新
          await axios.put(`${RAG_API}/vendors/${this.editingItem.id}`, {
            name: this.formData.name,
            short_name: this.formData.short_name,
            contact_phone: this.formData.contact_phone,
            contact_email: this.formData.contact_email,
            address: this.formData.address,
            subscription_plan: this.formData.subscription_plan,
            business_type: this.formData.business_type,
            is_active: this.formData.is_active,
            updated_by: 'admin'
          });
          alert('✅ 業者已更新！');
        } else {
          // 新增
          await axios.post(`${RAG_API}/vendors`, {
            ...this.formData,
            created_by: 'admin'
          });
          alert('✅ 業者已新增！');
        }

        this.closeModal();
        this.loadVendors();
      } catch (error) {
        console.error('儲存失敗', error);
        alert('儲存失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.saving = false;
      }
    },

    async deleteVendor(id) {
      if (!confirm('確定要停用這個業者嗎？')) return;

      try {
        await axios.delete(`${RAG_API}/vendors/${id}`);
        alert('✅ 業者已停用');
        this.loadVendors();
      } catch (error) {
        alert('停用失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    async viewStats(vendor) {
      try {
        const response = await axios.get(`${RAG_API}/vendors/${vendor.id}/stats`);
        this.statsData = response.data;
        this.showStatsModal = true;
      } catch (error) {
        alert('載入統計失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    viewConfig(vendor) {
      this.$router.push(`/vendors/${vendor.id}/configs`);
    },

    closeModal() {
      this.showModal = false;
      this.editingItem = null;
    },

    closeStatsModal() {
      this.showStatsModal = false;
      this.statsData = {};
    },

    getPlanLabel(plan) {
      const labels = {
        basic: 'Basic',
        standard: 'Standard',
        premium: 'Premium'
      };
      return labels[plan] || plan;
    },

    getBusinessTypeLabel(type) {
      const labels = {
        full_service: '📦 包租型',
        property_management: '🏢 代管型'
      };
      return labels[type] || type;
    },

    getCategoryLabel(category) {
      const labels = {
        payment: '帳務',
        contract: '合約',
        service: '服務',
        contact: '聯絡'
      };
      return labels[category] || category;
    }
  }
};
</script>

<style scoped>
.vendor-list table {
  width: 100%;
  background: white;
}

.status.active {
  color: #67C23A;
  font-weight: bold;
}

.status.inactive {
  color: #909399;
}

.badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
  color: white;
}

.badge.plan-basic {
  background: #909399;
}

.badge.plan-standard {
  background: #409EFF;
}

.badge.plan-premium {
  background: #F56C6C;
}

.badge.type-full_service {
  background: #67C23A;
}

.badge.type-property_management {
  background: #409EFF;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
  margin-right: 5px;
}

code {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
  color: #e83e8c;
}

/* 統計 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
  margin: 20px 0;
}

.stat-card {
  background: #f0f9ff;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
}

.stat-label {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #1e40af;
}

.config-breakdown {
  margin-top: 20px;
}

.config-breakdown h3 {
  margin-bottom: 10px;
  font-size: 16px;
}

.config-breakdown table {
  width: 100%;
}

.config-breakdown td, .config-breakdown th {
  text-align: left;
  padding: 8px;
}
</style>
