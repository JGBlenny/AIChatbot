<template>
  <div class="platform-sop-view">
    <h2>🏢 平台 SOP 範本管理</h2>

    <!-- 說明區塊 -->
    <InfoPanel :config="helpTexts.platformSOP" />

    <!-- 操作按鈕區 -->
    <div class="action-bar">
      <button @click="showCategoryModal = true" class="btn-primary btn-sm">
        新增分類
      </button>
    </div>

    <!-- 載入中 -->
    <div v-if="loading" class="loading">
      <span class="spinner"></span> 載入中...
    </div>

    <!-- SOP 範本列表（按業種 → 分類分組） -->
    <div v-else class="sop-business-types">
      <!-- 包租業範本 -->
      <div class="business-type-section clickable-section" @click="navigateToBusinessType('full_service')">
        <div class="business-type-header">
          <div class="business-type-info">
            <h2>🏠 包租業範本</h2>
            <p class="business-type-description">適用於包租型業者的 SOP 範本</p>
            <p class="business-type-count">共 {{ getTemplateCountByBusinessType('full_service') }} 個 SOP 項目</p>
          </div>
          <div class="business-type-actions" @click.stop>
            <button @click="navigateToBusinessType('full_service')" class="btn-primary btn-sm">
              管理 SOP
            </button>
          </div>
        </div>
      </div>

      <!-- 代管業範本 -->
      <div class="business-type-section clickable-section" @click="navigateToBusinessType('property_management')">
        <div class="business-type-header">
          <div class="business-type-info">
            <h2>🔑 代管業範本</h2>
            <p class="business-type-description">適用於代管型業者的 SOP 範本</p>
            <p class="business-type-count">共 {{ getTemplateCountByBusinessType('property_management') }} 個 SOP 項目</p>
          </div>
          <div class="business-type-actions" @click.stop>
            <button @click="navigateToBusinessType('property_management')" class="btn-primary btn-sm">
              管理 SOP
            </button>
          </div>
        </div>
      </div>

      <!-- 通用範本 -->
      <div class="business-type-section clickable-section" @click="navigateToBusinessType('universal')">
        <div class="business-type-header">
          <div class="business-type-info">
            <h2>🌐 通用範本</h2>
            <p class="business-type-description">適用於所有業種的通用 SOP 範本</p>
            <p class="business-type-count">共 {{ getTemplateCountByBusinessType(null) }} 個 SOP 項目</p>
          </div>
          <div class="business-type-actions" @click.stop>
            <button @click="navigateToBusinessType('universal')" class="btn-primary btn-sm">
              管理 SOP
            </button>
          </div>
        </div>
      </div>

      <div v-if="categories.length === 0" class="no-categories">
        尚未建立任何分類，請先建立分類
      </div>
    </div>

    <!-- 新增/編輯分類 Modal -->
    <div v-if="showCategoryModal" class="modal-overlay" @click="showCategoryModal = false">
      <div class="modal-content" @click.stop>
        <h2>{{ editingCategory ? '編輯分類' : '新增分類' }}</h2>
        <form @submit.prevent="saveCategory">
          <div class="form-group">
            <label>分類名稱 *</label>
            <input v-model="categoryForm.category_name" type="text" required class="form-control" />
          </div>

          <div class="form-group">
            <label>分類說明</label>
            <textarea v-model="categoryForm.description" class="form-control" rows="3"></textarea>
          </div>

          <div class="form-group">
            <label>範本說明（幫助業者理解此分類）</label>
            <textarea v-model="categoryForm.template_notes" class="form-control" rows="2"></textarea>
          </div>

          <div class="modal-actions">
            <button type="submit" class="btn-primary btn-sm">儲存</button>
            <button type="button" @click="closeCategoryModal" class="btn-secondary btn-sm">取消</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 新增/編輯範本 Modal -->
    <div v-if="showTemplateModal" class="modal-overlay" @click="showTemplateModal = false">
      <div class="modal-content modal-large" @click.stop>
        <h2>{{ editingTemplate ? '編輯範本' : '新增範本' }}</h2>
        <form @submit.prevent="saveTemplate">
          <!-- 基本資訊 -->
          <div class="form-section">
            <h3>基本資訊</h3>

            <div class="form-group">
              <label>所屬分類 *</label>
              <select v-model.number="templateForm.category_id" required class="form-control">
                <option :value="null">請選擇分類</option>
                <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                  {{ cat.category_name }}
                </option>
              </select>
            </div>

            <div class="form-group">
              <label>業種類型</label>
              <div v-if="!editingTemplate" class="form-control-static">
                <span v-if="templateForm.business_type === 'full_service'" class="badge badge-business-type business-type-full_service">
                  🏠 包租型業者
                </span>
                <span v-else-if="templateForm.business_type === 'property_management'" class="badge badge-business-type business-type-property_management">
                  🔑 代管型業者
                </span>
                <span v-else class="badge badge-universal">
                  🌐 通用範本（適用所有業種）
                </span>
                <small class="form-hint">業種類型在新增後無法修改</small>
              </div>
              <select v-else v-model="templateForm.business_type" class="form-control">
                <option :value="null">通用範本（適用所有業種）</option>
                <option value="full_service">🏠 包租型業者</option>
                <option value="property_management">🔑 代管型業者</option>
              </select>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>項次編號 *</label>
                <input v-model.number="templateForm.item_number" type="number" min="1" required class="form-control" />
              </div>

              <div class="form-group">
                <label>優先級 (0-100)</label>
                <input v-model.number="templateForm.priority" type="number" min="0" max="100" class="form-control" />
              </div>
            </div>

            <div class="form-group">
              <label>項目名稱 *</label>
              <input v-model="templateForm.item_name" type="text" required class="form-control" />
            </div>

            <div class="form-group">
              <label>範本內容 *</label>
              <textarea v-model="templateForm.content" required class="form-control" rows="4"></textarea>
              <small class="form-hint">此內容將作為業者複製的基礎，業者複製後可自行編輯調整</small>
            </div>
          </div>

          <!-- 關聯設定 -->
          <div class="form-section">
            <h3>關聯設定</h3>

            <div class="form-group">
              <label>關聯意圖</label>
              <select v-model.number="templateForm.related_intent_id" class="form-control">
                <option :value="null">無</option>
                <option v-for="intent in intents" :key="intent.id" :value="intent.id">
                  {{ intent.name }}
                </option>
              </select>
            </div>
          </div>

          <!-- 範本引導 -->
          <div class="form-section">
            <h3>範本引導（幫助業者自訂）</h3>

            <div class="form-group">
              <label>範本說明</label>
              <textarea v-model="templateForm.template_notes" class="form-control" rows="2"></textarea>
              <small class="form-hint">解釋此 SOP 的目的和適用場景</small>
            </div>

            <div class="form-group">
              <label>自訂提示</label>
              <textarea v-model="templateForm.customization_hint" class="form-control" rows="2"></textarea>
              <small class="form-hint">建議業者如何根據自身情況調整內容</small>
            </div>
          </div>

          <div class="modal-actions">
            <button type="submit" class="btn-primary btn-sm">儲存</button>
            <button type="button" @click="closeTemplateModal" class="btn-secondary btn-sm">取消</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 範本使用情況 Modal -->
    <div v-if="showUsageModal" class="modal-overlay" @click="showUsageModal = false">
      <div class="modal-content" @click.stop>
        <h2>範本使用情況: {{ currentTemplateUsage.template_name }}</h2>

        <div v-if="currentTemplateUsage.usage.length > 0" class="usage-list">
          <div v-for="usage in currentTemplateUsage.usage" :key="usage.vendor_id" class="usage-item">
            <div class="usage-vendor">
              <strong>{{ usage.vendor_name }}</strong>
            </div>
            <div class="usage-status" :class="`status-${usage.override_type}`">
              {{ getOverrideTypeLabel(usage.override_type) }}
            </div>
            <div v-if="usage.override_reason" class="usage-reason">
              原因: {{ usage.override_reason }}
            </div>
          </div>
        </div>

        <div v-else class="no-data">
          目前沒有業者使用此範本
        </div>

        <div class="modal-actions">
          <button @click="showUsageModal = false" class="btn-secondary btn-sm">關閉</button>
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

const RAG_API = `${API_BASE_URL}/rag-api/v1`;  // RAG Orchestrator API

export default {
  name: 'PlatformSOPView',

  components: {
    InfoPanel
  },
  data() {
    return {
      helpTexts,
      loading: false,
      categories: [],
      templates: [],
      intents: [],

      // Accordion states (track expanded categories)
      expandedCategories: {},

      // Modal states
      showCategoryModal: false,
      showTemplateModal: false,
      showUsageModal: false,

      // Editing states
      editingCategory: null,
      editingTemplate: null,

      // Forms
      categoryForm: {
        category_name: '',
        description: '',
        display_order: 0,
        template_notes: ''
      },

      templateForm: {
        category_id: null,
        business_type: null,
        item_number: 1,
        item_name: '',
        content: '',
        related_intent_id: null,
        priority: 50,
        template_notes: '',
        customization_hint: ''
      },

      currentTemplateUsage: {
        template_id: null,
        template_name: '',
        usage: []
      }
    };
  },

  watch: {
    'templateForm.category_id'(newCategoryId) {
      // 當選擇分類時，自動設置下一個可用的項次編號（僅在新增模式下）
      if (!this.editingTemplate && newCategoryId) {
        this.templateForm.item_number = this.getNextItemNumber(newCategoryId, this.templateForm.business_type);
      }
    }
  },

  mounted() {
    this.loadData();
    this.loadIntents();
  },

  methods: {
    async loadData() {
      this.loading = true;
      try {
        await Promise.all([
          this.loadCategories(),
          this.loadTemplates()
        ]);
      } catch (error) {
        console.error('載入資料失敗:', error);
        alert('載入資料失敗: ' + error.message);
      } finally {
        this.loading = false;
      }
    },

    async loadCategories() {
      const response = await axios.get(`${RAG_API}/platform/sop/categories`);
      this.categories = response.data.categories;
    },

    async loadTemplates() {
      const response = await axios.get(`${RAG_API}/platform/sop/templates`);
      this.templates = response.data.templates;
    },

    async loadIntents() {
      try {
        const response = await axios.get(`${RAG_API}/intents`);
        this.intents = response.data.intents || [];
      } catch (error) {
        console.error('載入意圖失敗:', error);
        this.intents = [];
      }
    },

    getTemplatesByCategory(categoryId) {
      return this.templates.filter(t => t.category_id === categoryId);
    },

    getTemplatesByCategoryAndBusinessType(categoryId, businessType) {
      return this.templates.filter(t => {
        const matchCategory = t.category_id === categoryId;
        const matchBusinessType = businessType === null
          ? t.business_type === null
          : t.business_type === businessType;
        return matchCategory && matchBusinessType;
      });
    },

    getNextItemNumber(categoryId, businessType) {
      if (!categoryId) return 1;

      const categoryTemplates = this.templates.filter(t =>
        t.category_id === categoryId && t.business_type === businessType
      );

      if (categoryTemplates.length === 0) return 1;

      const maxItemNumber = Math.max(...categoryTemplates.map(t => t.item_number));
      return maxItemNumber + 1;
    },

    addTemplateForBusinessType(businessType) {
      this.editingTemplate = null;
      this.templateForm = {
        category_id: null,
        business_type: businessType,
        item_number: 1,
        item_name: '',
        content: '',
        related_intent_id: null,
        priority: 50,
        template_notes: '',
        customization_hint: ''
      };
      this.showTemplateModal = true;
    },

    // Accordion methods
    toggleCategory(businessType, categoryId) {
      const key = `${businessType}_${categoryId}`;
      // Use spread to ensure Vue reactivity
      this.expandedCategories = {
        ...this.expandedCategories,
        [key]: !this.expandedCategories[key]
      };
    },

    isCategoryExpanded(businessType, categoryId) {
      const key = `${businessType}_${categoryId}`;
      return !!this.expandedCategories[key];
    },

    getTemplateCountByBusinessType(businessType) {
      if (businessType === 'full_service' || businessType === 'property_management') {
        return this.templates.filter(t => t.business_type === businessType).length;
      } else {
        // null or 'universal'
        return this.templates.filter(t => t.business_type === null).length;
      }
    },

    navigateToBusinessType(businessType) {
      this.$router.push({
        name: 'PlatformSOPEdit',
  components: {
    InfoPanel
  },
        params: { businessType }
      });
    },

    // Category CRUD
    editCategory(category) {
      this.editingCategory = category;
      this.categoryForm = {
        category_name: category.category_name,
        description: category.description || '',
        display_order: category.display_order || 0,
        template_notes: category.template_notes || ''
      };
      this.showCategoryModal = true;
    },

    async saveCategory() {
      try {
        if (this.editingCategory) {
          // Update
          await axios.put(
            `${RAG_API}/platform/sop/categories/${this.editingCategory.id}`,
            this.categoryForm
          );
          alert('分類已更新');
        } else {
          // Create
          await axios.post(
            `${RAG_API}/platform/sop/categories`,
            this.categoryForm
          );
          alert('分類已建立');
        }
        this.closeCategoryModal();
        this.loadCategories();
      } catch (error) {
        console.error('儲存分類失敗:', error);
        alert('儲存分類失敗: ' + (error.response?.data?.detail || error.message));
      }
    },

    async deleteCategory(categoryId) {
      if (!confirm('確定要刪除此分類嗎？此操作會同時停用該分類下的所有範本。')) return;

      try {
        await axios.delete(`${RAG_API}/platform/sop/categories/${categoryId}`);
        alert('分類已刪除');
        this.loadData();
      } catch (error) {
        console.error('刪除分類失敗:', error);
        alert('刪除分類失敗: ' + (error.response?.data?.detail || error.message));
      }
    },

    closeCategoryModal() {
      this.showCategoryModal = false;
      this.editingCategory = null;
      this.categoryForm = {
        category_name: '',
        description: '',
        display_order: 0,
        template_notes: ''
      };
    },

    // Template CRUD
    editTemplate(template) {
      this.editingTemplate = template;
      this.templateForm = {
        category_id: template.category_id,
        business_type: template.business_type || null,
        item_number: template.item_number,
        item_name: template.item_name,
        content: template.content,
        related_intent_id: template.related_intent_id,
        priority: template.priority,
        template_notes: template.template_notes || '',
        customization_hint: template.customization_hint || ''
      };
      this.showTemplateModal = true;
    },

    async saveTemplate() {
      try {
        if (this.editingTemplate) {
          // Update
          await axios.put(
            `${RAG_API}/platform/sop/templates/${this.editingTemplate.id}`,
            this.templateForm
          );
          alert('範本已更新');
        } else {
          // Create
          await axios.post(
            `${RAG_API}/platform/sop/templates`,
            this.templateForm
          );
          alert('範本已建立');
        }
        this.closeTemplateModal();
        this.loadTemplates();
      } catch (error) {
        console.error('儲存範本失敗:', error);
        alert('儲存範本失敗: ' + (error.response?.data?.detail || error.message));
      }
    },

    async deleteTemplate(templateId) {
      if (!confirm('確定要刪除此範本嗎？')) return;

      try {
        await axios.delete(`${RAG_API}/platform/sop/templates/${templateId}`);
        alert('範本已刪除');
        this.loadTemplates();
      } catch (error) {
        console.error('刪除範本失敗:', error);
        alert('刪除範本失敗: ' + (error.response?.data?.detail || error.message));
      }
    },

    closeTemplateModal() {
      this.showTemplateModal = false;
      this.editingTemplate = null;
      this.templateForm = {
        category_id: null,
        business_type: null,
        item_number: 1,
        item_name: '',
        content: '',
        related_intent_id: null,
        priority: 50,
        template_notes: '',
        customization_hint: ''
      };
    },

    async viewTemplateUsage(templateId) {
      try {
        const response = await axios.get(`${RAG_API}/platform/sop/templates/${templateId}/usage`);
        this.currentTemplateUsage = response.data;
        this.showUsageModal = true;
      } catch (error) {
        console.error('載入使用情況失敗:', error);
        alert('載入使用情況失敗: ' + error.message);
      }
    },

    // Helper methods
    getPriorityClass(priority) {
      if (priority >= 90) return 'priority-high';
      if (priority >= 70) return 'priority-medium';
      return 'priority-low';
    },

    getOverrideTypeLabel(type) {
      const labels = {
        use_template: '使用範本',
        partial_override: '部分覆寫',
        full_override: '完全覆寫',
        disabled: '已停用'
      };
      return labels[type] || type;
    },

    getBusinessTypeLabel(type) {
      const labels = {
        full_service: '🏠 包租型',
        property_management: '🔑 代管型'
      };
      return labels[type] || type;
    }
  }
};
</script>

<style scoped>
.platform-sop-view {
  /* 寬度和內邊距由 app-main 統一管理 */
}

.page-header {
  margin-bottom: 30px;
}

.page-header h1 {
  font-size: 28px;
  color: #333;
  margin-bottom: 8px;
}

.subtitle {
  color: #666;
  font-size: 14px;
}

.action-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #666;
}

.spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #4CAF50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.category-section {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  margin-bottom: 20px;
  overflow: hidden;
}

.category-header {
  background: #f5f5f5;
  padding: 20px;
  border-bottom: 1px solid #ddd;
}

.category-header h2 {
  font-size: 22px;
  color: #333;
  margin: 0 0 8px 0;
}

.category-order {
  display: inline-block;
  background: #2196F3;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 14px;
  margin-right: 8px;
}

.category-description {
  color: #666;
  margin: 8px 0;
  font-size: 14px;
}

.category-notes {
  color: #FF9800;
  font-size: 13px;
  margin: 8px 0;
}

.category-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.templates-list {
  padding: 20px;
}

.template-card {
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 16px;
}

.template-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.template-number {
  background: #9E9E9E;
  color: white;
  padding: 4px 10px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 13px;
}

.template-header h3 {
  font-size: 18px;
  color: #333;
  margin: 0;
  flex: 1;
}

.badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.badge-business-type {
  font-weight: 600;
}

.business-type-full_service {
  background: #E8F5E9;
  color: #2E7D32;
}

.business-type-property_management {
  background: #E3F2FD;
  color: #1565C0;
}

.badge-universal {
  background: #FFF3E0;
  color: #EF6C00;
}

.badge-intent {
  background: #F3E5F5;
  color: #7B1FA2;
}

.badge-priority {
  background: #E8F5E9;
  color: #388E3C;
}

.priority-high {
  background: #FFEBEE;
  color: #C62828;
}

.priority-medium {
  background: #FFF3E0;
  color: #EF6C00;
}

.priority-low {
  background: #E8F5E9;
  color: #388E3C;
}

.template-content {
  margin: 12px 0;
}

.content-section {
  margin-bottom: 12px;
}

.content-section strong {
  display: block;
  color: #555;
  margin-bottom: 4px;
  font-size: 13px;
}

.content-section p {
  margin: 0;
  color: #666;
  font-size: 14px;
  line-height: 1.6;
  padding: 8px;
  background: white;
  border-radius: 4px;
}

.template-guide {
  background: #FFFDE7;
  padding: 8px;
  border-radius: 4px;
  border-left: 3px solid #FBC02D;
}

.template-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.no-templates,
.no-categories,
.no-data {
  text-align: center;
  padding: 40px;
  color: #999;
  font-style: italic;
}

/* Modal styles */
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
  padding: 24px;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-large {
  max-width: 900px;
}

.modal-content h2 {
  margin-top: 0;
  color: #333;
  font-size: 22px;
  margin-bottom: 20px;
}

.form-section {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #eee;
}

.form-section:last-of-type {
  border-bottom: none;
}

.form-section h3 {
  font-size: 16px;
  color: #555;
  margin-top: 0;
  margin-bottom: 16px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  color: #555;
  font-weight: 500;
  font-size: 14px;
}

.form-control {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-control:focus {
  outline: none;
  border-color: #4CAF50;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-hint {
  display: block;
  margin-top: 4px;
  color: #999;
  font-size: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: auto;
  margin: 0;
}

.cashflow-versions {
  background: #F5F5F5;
  padding: 16px;
  border-radius: 6px;
  margin-top: 12px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

/* Usage Modal */
.usage-list {
  margin: 20px 0;
}

.usage-item {
  padding: 12px;
  background: #f9f9f9;
  border-radius: 6px;
  margin-bottom: 10px;
  border-left: 3px solid #4CAF50;
}

.usage-vendor {
  margin-bottom: 6px;
}

.usage-status {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  margin-bottom: 6px;
}

.status-use_template {
  background: #E8F5E9;
  color: #388E3C;
}

.status-partial_override {
  background: #FFF3E0;
  color: #EF6C00;
}

.status-full_override {
  background: #E3F2FD;
  color: #1976D2;
}

.status-disabled {
  background: #FFEBEE;
  color: #C62828;
}

.usage-reason {
  font-size: 13px;
  color: #666;
  font-style: italic;
}

/* Business Type Sections */
.sop-business-types {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.business-type-section {
  background: white;
  border: 2px solid #ddd;
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.clickable-section {
  cursor: pointer;
}

.clickable-section:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
  border-color: #667eea;
}

.business-type-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 30px 40px;
  color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 30px;
  min-height: 140px;
}

.business-type-info {
  flex: 1;
}

.business-type-header h2 {
  margin: 0 0 10px 0;
  font-size: 28px;
}

.business-type-description {
  margin: 0 0 8px 0;
  font-size: 15px;
  opacity: 0.9;
}

.business-type-count {
  margin: 0;
  font-size: 14px;
  opacity: 0.85;
  font-weight: 500;
}

.business-type-actions {
  display: flex;
  align-items: center;
}

.categories-container {
  padding: 20px;
}

.category-header-collapsible {
  background: #f8f9fa;
  padding: 12px 20px;
  border-left: 4px solid #4CAF50;
  margin-bottom: 10px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.2s;
  user-select: none;
}

.category-header-collapsible:hover {
  background: #e9ecef;
  border-left-color: #45a049;
}

.category-header-collapsible h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
  font-weight: 600;
  flex: 1;
}

.collapse-icon {
  font-size: 12px;
  color: #4CAF50;
  font-weight: bold;
  transition: transform 0.2s;
}

.category-count {
  background: #4CAF50;
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 500;
}

.template-card h4 {
  font-size: 16px;
  color: #333;
  margin: 0;
  flex: 1;
}

.form-control-static {
  padding: 10px 0;
}

.form-control-static .badge {
  font-size: 14px;
  padding: 6px 12px;
}

.form-control-static .form-hint {
  display: block;
  margin-top: 8px;
}
</style>
