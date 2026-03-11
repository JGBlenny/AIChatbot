<template>
  <div>
    <div class="page-header">
      <h2>⚙️ 業者配置 - {{ vendor ? vendor.name : '載入中...' }}</h2>
      <button @click="goBack" class="btn-secondary">← 返回業者列表</button>
    </div>

    <div v-if="loading" class="loading"><p>載入中...</p></div>

    <div v-else-if="vendor">
      <!-- 業者資訊 -->
      <div class="vendor-summary">
        <div class="summary-item">
          <strong>代碼：</strong>{{ vendor.code }}
        </div>
        <div class="summary-item">
          <strong>業務範圍：</strong>
          <span class="scope-badge" :class="'scope-' + vendor.business_scope_name">
            {{ getScopeLabel(vendor.business_scope_name) }}
          </span>
        </div>
        <div class="summary-item">
          <strong>訂閱方案：</strong>{{ vendor.subscription_plan }}
        </div>
        <div class="summary-item">
          <strong>狀態：</strong>
          <span :class="vendor.is_active ? 'status-active' : 'status-inactive'">
            {{ vendor.is_active ? '啟用' : '停用' }}
          </span>
        </div>
      </div>

      <!-- 分類標籤 -->
      <div class="category-tabs">
        <button
          v-for="cat in categories"
          :key="cat.value"
          @click="selectedCategory = cat.value"
          :class="['tab', { active: selectedCategory === cat.value }]"
        >
          {{ cat.icon }} {{ cat.label }}
          <span class="count" v-if="getConfigCount(cat.value)">{{ getConfigCount(cat.value) }}</span>
        </button>
      </div>

      <!-- 配置表單 (非 SOP 非 Lookup) -->
      <div v-if="selectedCategory !== 'sop' && selectedCategory !== 'lookup'" class="config-section">
        <div class="section-header">
          <h3>{{ getCategoryInfo(selectedCategory).label }}</h3>
          <div class="header-actions">
            <button @click="showPreview" class="btn-info">👁️ 預覽效果</button>
          </div>
        </div>

        <div class="config-grid">
          <div v-for="(config, index) in currentCategoryConfigs" :key="index" class="config-item">
            <div class="config-label">
              <label>{{ config.display_name || config.param_key }}</label>
              <small v-if="config.description">{{ config.description }}</small>
            </div>

            <div class="config-input-group">
              <input
                v-if="config.data_type === 'string' || config.data_type === 'number'"
                v-model="config.param_value"
                :type="config.data_type === 'number' ? 'number' : 'text'"
                :placeholder="getPlaceholder(config)"
                class="config-input"
              />
              <select v-else-if="config.data_type === 'boolean'" v-model="config.param_value" class="config-input">
                <option value="true">是</option>
                <option value="false">否</option>
              </select>
              <textarea
                v-else
                v-model="config.param_value"
                rows="2"
                class="config-input"
              ></textarea>

              <span v-if="config.unit" class="unit-label">{{ config.unit }}</span>
            </div>
          </div>

          <!-- 空狀態 -->
          <div v-if="currentCategoryConfigs.length === 0" class="empty-state-small">
            <p>此分類尚無系統參數</p>
          </div>
        </div>
      </div>

      <!-- SOP 管理介面（新架構：範本+覆寫）-->
      <div v-else-if="selectedCategory === 'sop'" class="config-section">
        <VendorSOPManager :vendorId="Number(vendorId)" />
      </div>

      <!-- Lookup 數據管理 -->
      <div v-else-if="selectedCategory === 'lookup'" class="config-section">
        <VendorLookupManager :vendorId="Number(vendorId)" />
      </div>

      <!-- 儲存按鈕（僅在 payment/contract/service/contact 標籤顯示）-->
      <div v-if="selectedCategory !== 'sop' && selectedCategory !== 'lookup'" class="action-bar">
        <button @click="saveConfigs" :disabled="saving" class="btn-primary btn-large">
          {{ saving ? '⏳ 儲存中...' : '💾 儲存所有配置' }}
        </button>
      </div>
    </div>

    <!-- 預覽 Modal -->
    <div v-if="showPreviewModal" class="modal-overlay" @click="closePreview">
      <div class="modal-content" @click.stop style="max-width: 800px;">
        <h2>👁️ 模板預覽</h2>
        <p class="help-text">以下是使用當前配置參數後的實際效果</p>

        <div class="preview-section">
          <h3>範例 1：繳費日期說明</h3>
          <div class="template-box">
            <div class="template-label">模板：</div>
            <div class="template-text" v-pre>您的租金繳費日為每月 {{payment_day}}，請務必在期限前完成繳費。</div>
          </div>
          <div class="resolved-box">
            <div class="resolved-label">實際顯示：</div>
            <div class="resolved-text">{{ resolvedExample1 }}</div>
          </div>
        </div>

        <div class="preview-section">
          <h3>範例 2：逾期說明</h3>
          <div class="template-box">
            <div class="template-label">模板：</div>
            <div class="template-text" v-pre>超過繳費日 {{grace_period}} 後，將加收 {{late_fee}} 的逾期手續費。</div>
          </div>
          <div class="resolved-box">
            <div class="resolved-label">實際顯示：</div>
            <div class="resolved-text">{{ resolvedExample2 }}</div>
          </div>
        </div>

        <div class="preview-section">
          <h3>範例 3：客服資訊</h3>
          <div class="template-box">
            <div class="template-label">模板：</div>
            <div class="template-text" v-pre>如有問題請撥打 {{service_hotline}}，服務時間：{{service_hours}}</div>
          </div>
          <div class="resolved-box">
            <div class="resolved-label">實際顯示：</div>
            <div class="resolved-text">{{ resolvedExample3 }}</div>
          </div>
        </div>

        <div class="form-actions">
          <button @click="closePreview" class="btn-primary">關閉</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import axios from 'axios';
import VendorSOPManager from '../components/VendorSOPManager.vue';
import VendorLookupManager from '../components/VendorLookupManager.vue';
import { API_BASE_URL } from '@/config/api';

const RAG_API = `${API_BASE_URL}/rag-api/v1`;

export default {
  name: 'VendorConfigView',

  components: {
    VendorSOPManager,
    VendorLookupManager
  },

  data() {
    return {
      vendorId: null,
      vendor: null,
      configs: {},
      selectedCategory: 'payment',
      loading: false,
      saving: false,
      showPreviewModal: false,
      categories: [
        { value: 'payment', label: '帳務設定', icon: '💰' },
        { value: 'contract', label: '合約設定', icon: '📝' },
        { value: 'service', label: '服務設定', icon: '🛎️' },
        { value: 'contact', label: '聯絡資訊', icon: '📞' },
        { value: 'sop', label: 'SOP 管理', icon: '📋' },
        { value: 'lookup', label: 'Lookup 數據', icon: '💾' }
      ]
    };
  },
  computed: {
    currentCategoryConfigs() {
      return this.configs[this.selectedCategory] || [];
    },
    resolvedExample1() {
      const template = '您的租金繳費日為每月 ' + String.fromCharCode(123, 123) + 'payment_day' + String.fromCharCode(125, 125) + '，請務必在期限前完成繳費。';
      return this.resolveTemplate(template);
    },
    resolvedExample2() {
      const template = '超過繳費日 ' + String.fromCharCode(123, 123) + 'grace_period' + String.fromCharCode(125, 125) + ' 後，將加收 ' + String.fromCharCode(123, 123) + 'late_fee' + String.fromCharCode(125, 125) + ' 的逾期手續費。';
      return this.resolveTemplate(template);
    },
    resolvedExample3() {
      const template = '如有問題請撥打 ' + String.fromCharCode(123, 123) + 'service_hotline' + String.fromCharCode(125, 125) + '，服務時間：' + String.fromCharCode(123, 123) + 'service_hours' + String.fromCharCode(125, 125);
      return this.resolveTemplate(template);
    }
  },
  mounted() {
    this.vendorId = this.$route.params.id;
    this.loadVendor();
    this.loadConfigs();

    // 檢查是否有 category 參數，如果有則自動切換到對應標籤
    const category = this.$route.query.category;
    if (category && this.categories.some(c => c.value === category)) {
      this.selectedCategory = category;
    }
  },
  methods: {
    async loadVendor() {
      try {
        const response = await axios.get(`${RAG_API}/vendors/${this.vendorId}`);
        this.vendor = response.data;
      } catch (error) {
        alert('載入業者失敗：' + (error.response?.data?.detail || error.message));
        this.goBack();
      }
    },

    async loadConfigs() {
      this.loading = true;
      try {
        const response = await axios.get(`${RAG_API}/vendors/${this.vendorId}/configs`);
        this.configs = response.data;
      } catch (error) {
        console.error('載入配置失敗', error);
        alert('載入配置失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },

    async saveConfigs() {
      this.saving = true;
      try {
        // 整理所有配置為扁平列表
        const allConfigs = [];
        for (const category in this.configs) {
          for (const config of this.configs[category]) {
            allConfigs.push({
              category: category,
              param_key: config.param_key,
              // 確保 param_value 是字符串（後端 Pydantic 模型要求）
              param_value: String(config.param_value || ''),
              data_type: config.data_type || 'string',
              display_name: config.display_name,
              description: config.description,
              unit: config.unit
            });
          }
        }

        await axios.put(`${RAG_API}/vendors/${this.vendorId}/configs`, {
          configs: allConfigs
        });

        alert('✅ 配置已儲存！');
      } catch (error) {
        console.error('儲存失敗', error);

        // 改進錯誤處理：正確顯示 Pydantic 驗證錯誤
        let errorMessage = '未知錯誤';
        if (error.response?.data?.detail) {
          const detail = error.response.data.detail;
          if (Array.isArray(detail)) {
            // Pydantic 驗證錯誤格式：[{loc: [...], msg: "..."}]
            errorMessage = detail.map(err => {
              const field = err.loc?.join('.') || '未知欄位';
              return `${field}: ${err.msg}`;
            }).join('\n');
          } else if (typeof detail === 'string') {
            errorMessage = detail;
          } else {
            errorMessage = JSON.stringify(detail);
          }
        } else if (error.message) {
          errorMessage = error.message;
        }

        alert('儲存失敗：\n' + errorMessage);
      } finally {
        this.saving = false;
      }
    },

    showPreview() {
      this.showPreviewModal = true;
    },

    closePreview() {
      this.showPreviewModal = false;
    },

    resolveTemplate(template) {
      let result = template;

      // 替換所有分類的參數
      for (const category in this.configs) {
        for (const config of this.configs[category]) {
          const placeholder = `{{${config.param_key}}}`;
          let value = config.param_value;

          // 格式化值
          if (config.data_type === 'number' && config.unit) {
            value = `${value} ${config.unit}`;
          }

          result = result.replace(new RegExp(placeholder, 'g'), value);
        }
      }

      return result;
    },

    getConfigCount(category) {
      return this.configs[category]?.length || 0;
    },

    getCategoryInfo(category) {
      return this.categories.find(c => c.value === category) || {};
    },

    getPlaceholder(config) {
      const placeholders = {
        payment_day: '1',
        payment_method: '銀行轉帳、超商繳費',
        late_fee: '200',
        grace_period: '5',
        service_hotline: '02-1234-5678'
      };
      return placeholders[config.param_key] || '';
    },

    getScopeLabel(scope) {
      const labels = {
        external: '外部 (B2C 包租代管)',
        internal: '內部 (B2B 系統商)'
      };
      return labels[scope] || scope;
    },


    goBack() {
      this.$router.push('/vendors');
    }
  }
};
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

/* 業者摘要 */
.vendor-summary {
  display: flex;
  gap: 30px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.summary-item strong {
  margin-right: 8px;
}

.status-active {
  color: #4ade80;
  font-weight: bold;
}

.status-inactive {
  color: #f87171;
  font-weight: bold;
}

.scope-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: bold;
  color: white;
}

.scope-badge.scope-external {
  background: #67C23A;
}

.scope-badge.scope-internal {
  background: #E6A23C;
}

/* 分類標籤 */
.category-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  border-bottom: 2px solid #e5e7eb;
}

.tab {
  padding: 12px 20px;
  background: none;
  border: none;
  border-bottom: 3px solid transparent;
  cursor: pointer;
  transition: all 0.3s;
  font-weight: 500;
  color: #666;
}

.tab:hover {
  color: #667eea;
}

.tab.active {
  color: #667eea;
  border-bottom-color: #667eea;
  font-weight: bold;
}

.tab .count {
  display: inline-block;
  background: #667eea;
  color: white;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  margin-left: 6px;
}

/* 配置區域 */
.config-section {
  background: white;
  border-radius: 8px;
  padding: 25px;
  border: 1px solid #e5e7eb;
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 2px solid #f3f4f6;
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

/* 配置網格 */
.config-grid {
  display: grid;
  gap: 20px;
}

.config-item {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 15px;
  align-items: start;
  padding: 15px;
  background: #f9fafb;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.config-label label {
  font-weight: bold;
  display: block;
  margin-bottom: 4px;
}

.config-label small {
  display: block;
  color: #666;
  font-size: 12px;
}

.config-input-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.config-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 14px;
}

.config-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.unit-label {
  color: #666;
  font-size: 13px;
  white-space: nowrap;
}

/* 空狀態 */
.empty-state-small {
  text-align: center;
  padding: 40px;
  color: #9ca3af;
}

/* 操作列 */
.action-bar {
  display: flex;
  gap: 15px;
  justify-content: center;
}

.btn-large {
  padding: 12px 30px;
  font-size: 16px;
}

/* 預覽 */
.preview-section {
  margin-bottom: 25px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.preview-section:last-of-type {
  border-bottom: none;
}

.preview-section h3 {
  margin-bottom: 12px;
  font-size: 15px;
  color: #667eea;
}

.template-box, .resolved-box {
  margin-bottom: 10px;
}

.template-label, .resolved-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 6px;
  font-weight: bold;
}

.template-text {
  background: #f3f4f6;
  padding: 12px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 13px;
  color: #666;
  border-left: 3px solid #9ca3af;
}

.resolved-text {
  background: #f0f9ff;
  padding: 12px;
  border-radius: 4px;
  font-size: 14px;
  border-left: 3px solid #667eea;
  line-height: 1.6;
}

.help-text {
  color: #666;
  margin-bottom: 20px;
}

</style>
