<template>
  <div>
    <h2>🏢 業者管理</h2>

    <!-- 說明區塊 -->
    <InfoPanel :config="helpTexts.vendors" />

    <!-- 工具列 -->
    <div class="toolbar">
      <button @click="showCreateModal" class="btn-primary btn-sm">新增業者</button>
    </div>

    <!-- 業者列表 -->
    <div v-if="loading" class="loading"><p>載入中...</p></div>

    <div v-else class="vendor-list">
      <table>
        <thead>
          <tr>
            <th width="50">ID</th>
            <th width="110">代碼</th>
            <th width="180">名稱</th>
            <th width="120">聯絡電話</th>
            <th width="150">業態類型</th>
            <th width="100">訂閱方案</th>
            <th width="80">狀態</th>
            <th width="80">展示頁</th>
            <th width="80">表單</th>
            <th width="220">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="vendor in vendorList" :key="vendor.id">
            <td>{{ vendor.id }}</td>
            <td><code>{{ vendor.code }}</code></td>
            <td><strong>{{ vendor.name }}</strong></td>
            <td>{{ vendor.contact_phone || '-' }}</td>
            <td>
              <span
                v-for="(type, idx) in vendor.business_types"
                :key="idx"
                class="badge"
                :class="getBusinessTypeColorClass(type)"
              >
                {{ getBusinessTypeLabel(type) }}
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
              <a :href="`/${vendor.code}/chat`" target="_blank" class="btn-demo btn-sm">
                🔗 展示
              </a>
            </td>
            <td>
              <a :href="`/${vendor.code}/form-submissions`" target="_blank" class="btn-info btn-sm">
                📋 表單
              </a>
            </td>
            <td>
              <button @click="editVendor(vendor)" class="btn-edit btn-sm">編輯</button>
              <button @click="viewConfig(vendor)" class="btn-success btn-sm">配置</button>
              <button @click="deleteVendor(vendor.id)" class="btn-delete btn-sm">停用</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 編輯/新增 Modal -->
    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content vendor-modal" @click.stop>
        <div class="modal-header">
          <h3>{{ editingItem ? '編輯業者' : '新增業者' }}</h3>
          <button @click="closeModal" class="btn-close">✕</button>
        </div>

        <form @submit.prevent="saveVendor">
          <div class="modal-body">
            <!-- 基本資訊 -->
            <div class="form-section">
              <h4 class="section-title">基本資訊</h4>
              <div class="form-row">
                <div class="form-group">
                  <label>代碼 *</label>
                  <input v-model="formData.code" required placeholder="VENDOR_A" :disabled="editingItem" />
                  <small v-if="!editingItem" class="hint">業者代碼一旦建立不可修改</small>
                </div>

                <div class="form-group">
                  <label>名稱 *</label>
                  <input v-model="formData.name" required placeholder="甲山林包租代管股份有限公司" />
                </div>
              </div>
            </div>

            <!-- 聯絡資訊 -->
            <div class="form-section">
              <h4 class="section-title">聯絡資訊</h4>
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
            </div>

            <!-- 業務配置 -->
            <div class="form-section">
              <h4 class="section-title">業務配置</h4>
              <div class="form-row">
                <div class="form-group">
                  <label>訂閱方案</label>
                  <select v-model="formData.subscription_plan">
                    <option value="basic">Basic - 基礎方案</option>
                    <option value="standard">Standard - 標準方案</option>
                    <option value="premium">Premium - 進階方案</option>
                  </select>
                </div>

                <div v-if="editingItem" class="form-group">
                  <label>狀態</label>
                  <select v-model="formData.is_active">
                    <option :value="true">啟用</option>
                    <option :value="false">停用</option>
                  </select>
                </div>
              </div>

              <div class="form-group">
                <label>業態類型 *</label>
                <small class="hint">可多選，至少選一項</small>
                <div class="business-type-checkboxes">
                  <label
                    v-for="btype in availableBusinessTypes"
                    :key="btype.type_value"
                    class="btype-option"
                    :class="{ 'checked': formData.business_types.includes(btype.type_value) }"
                  >
                    <input
                      type="checkbox"
                      :value="btype.type_value"
                      v-model="formData.business_types"
                    />
                    <div class="btype-content">
                      <div class="btype-text">
                        <div class="btype-name">{{ btype.display_name }}</div>
                        <div class="btype-desc-small" v-if="btype.description">{{ btype.description }}</div>
                      </div>
                    </div>
                  </label>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button type="button" @click="closeModal" class="btn-secondary btn-sm">取消</button>
            <button type="submit" class="btn-primary btn-sm" :disabled="saving">
              {{ saving ? '儲存中...' : '儲存' }}
            </button>
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
          <button @click="closeStatsModal" class="btn-secondary btn-sm">關閉</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import InfoPanel from '@/components/InfoPanel.vue';
import helpTexts from '@/config/help-texts.js';
import { API_BASE_URL } from '@/config/api';

const RAG_API = `${API_BASE_URL}/rag-api/v1`;

export default {
  name: 'VendorManagementView',
  components: {
    InfoPanel
  },
  data() {
    return {
      helpTexts,
      vendorList: [],
      availableBusinessTypes: [],
      showModal: false,
      showStatsModal: false,
      editingItem: null,
      saving: false,
      loading: false,
      statsData: {},
      formData: {
        code: '',
        name: '',
        contact_phone: '',
        contact_email: '',
        address: '',
        subscription_plan: 'basic',
        business_types: [],
        is_active: true
      }
    };
  },
  mounted() {
    this.loadBusinessTypes();
    this.loadVendors();
  },
  methods: {
    async loadBusinessTypes() {
      try {
        const response = await axios.get(`${RAG_API}/business-types-config`, {
          params: { is_active: true }
        });
        this.availableBusinessTypes = response.data.business_types || [];

        // 設定預設業態類型為第一個
        if (this.availableBusinessTypes.length > 0 && this.formData.business_types.length === 0) {
          this.formData.business_types = [this.availableBusinessTypes[0].type_value];
        }
      } catch (error) {
        console.error('載入業態類型失敗:', error);
        // Fallback: 如果 API 失敗，使用預設值
        this.availableBusinessTypes = [
          { type_value: 'property_management', display_name: '代管型', description: 'Property Management' }
        ];
        this.formData.business_types = ['property_management'];
      }
    },

    async loadVendors() {
      this.loading = true;
      try {
        const response = await axios.get(`${RAG_API}/vendors`);
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
      // 預設選擇第一個業態類型
      const defaultBusinessType = this.availableBusinessTypes.length > 0
        ? [this.availableBusinessTypes[0].type_value]
        : [];

      this.formData = {
        code: '',
        name: '',
        contact_phone: '',
        contact_email: '',
        address: '',
        subscription_plan: 'basic',
        business_types: defaultBusinessType,
        is_active: true
      };
      this.showModal = true;
    },

    editVendor(vendor) {
      this.editingItem = vendor;
      // 如果業者沒有業態類型，使用第一個可用的業態類型
      const defaultBusinessType = this.availableBusinessTypes.length > 0
        ? [this.availableBusinessTypes[0].type_value]
        : [];

      this.formData = {
        code: vendor.code,
        name: vendor.name,
        contact_phone: vendor.contact_phone || '',
        contact_email: vendor.contact_email || '',
        address: vendor.address || '',
        subscription_plan: vendor.subscription_plan,
        business_types: vendor.business_types || defaultBusinessType,
        is_active: vendor.is_active
      };
      this.showModal = true;
    },

    async saveVendor() {
      // 驗證至少選擇一個業態類型
      if (!this.formData.business_types || this.formData.business_types.length === 0) {
        alert('❌ 請至少選擇一種業態類型');
        return;
      }

      this.saving = true;
      try {
        if (this.editingItem) {
          // 更新
          await axios.put(`${RAG_API}/vendors/${this.editingItem.id}`, {
            name: this.formData.name,
            contact_phone: this.formData.contact_phone,
            contact_email: this.formData.contact_email,
            address: this.formData.address,
            subscription_plan: this.formData.subscription_plan,
            business_types: this.formData.business_types,
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
      const businessType = this.availableBusinessTypes.find(bt => bt.type_value === type);
      return businessType ? businessType.display_name : type;
    },

    getBusinessTypeColorClass(type) {
      const businessType = this.availableBusinessTypes.find(bt => bt.type_value === type);
      return businessType && businessType.color ? `type-${businessType.color}` : 'type-gray';
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
/* 業者列表 */
.vendor-list table {
  width: 100%;
  background: white;
}

.vendor-list th {
  padding: 16px 20px;
  white-space: nowrap;
}

.vendor-list td {
  padding: 16px 20px;
  vertical-align: middle;
}

.vendor-list td code {
  font-size: 13px;
}

.vendor-list td strong {
  font-size: 14px;
  color: #2c3e50;
}

/* 業態類型標籤容器 */
.vendor-list td .badge {
  display: inline-block;
  margin-right: 6px;
  margin-bottom: 6px;
  padding: 5px 12px;
  font-size: 12px;
  white-space: nowrap;
}

/* 編輯業者 Modal 優化 */
.vendor-modal {
  max-width: 800px;
}

.form-section {
  margin-bottom: 30px;
  padding-bottom: 25px;
  border-bottom: 1px solid #e5e7eb;
}

.form-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 20px 0;
  padding-left: 12px;
  border-left: 4px solid #409EFF;
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

/* 業態類型多選 Checkbox - 現代卡片式設計 */
.business-type-checkboxes {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.btype-option {
  position: relative;
  display: block;
  padding: 16px;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.25s ease;
}

.btype-option:hover {
  border-color: #409EFF;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.15);
  transform: translateY(-1px);
}

.btype-option.checked {
  background: linear-gradient(135deg, #e3f2fd 0%, #f0f7ff 100%);
  border-color: #409EFF;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.btype-option input[type="checkbox"] {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 20px;
  height: 20px;
  cursor: pointer;
  accent-color: #409EFF;
}

.btype-content {
  display: flex;
  align-items: center;
  padding-right: 35px;
}

.btype-text {
  flex: 1;
}

.btype-name {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 2px;
}

.btype-desc-small {
  font-size: 12px;
  color: #95a5a6;
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

/* 表單按鈕樣式 */
.btn-info {
  background: #17a2b8;
  color: white;
  text-decoration: none;
  display: inline-block;
  padding: 6px 12px;
  font-size: 13px;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-info:hover {
  background: #138496;
}
</style>
