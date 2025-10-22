<template>
  <div class="platform-sop-edit-view">
    <div class="page-header">
      <button @click="$router.back()" class="btn btn-back">
        ← 返回
      </button>
      <div class="header-content">
        <h1>{{ businessTypeTitle }}</h1>
        <p class="subtitle">{{ businessTypeDescription }}</p>
      </div>
      <button @click="openNewTemplateModal" class="btn btn-primary">
        ➕ 新增 SOP 項目
      </button>
    </div>

    <!-- 載入中 -->
    <div v-if="loading" class="loading">
      <span class="spinner"></span> 載入中...
    </div>

    <!-- SOP 範本列表（3 層結構：分類 → 群組 → 範本） -->
    <div v-else class="sop-categories">
      <div
        v-for="category in categories"
        :key="category.id"
        class="category-section"
      >
        <template v-if="getGroupsByCategory(category.id).length > 0">
          <!-- 第 1 層：分類 -->
          <div
            class="category-header-collapsible"
            @click="toggleCategory(category.id)"
          >
            <span class="collapse-icon">{{ isCategoryExpanded(category.id) ? '▼' : '▶' }}</span>
            <h2>{{ category.category_name }}</h2>
            <span class="category-count">{{ getGroupsByCategory(category.id).length }} 個群組</span>
          </div>

          <!-- 第 2 層：群組列表 -->
          <div v-show="isCategoryExpanded(category.id)" class="groups-list">
            <div
              v-for="group in getGroupsByCategory(category.id)"
              :key="group.id"
              class="group-section"
            >
              <div
                class="group-header-collapsible"
                @click="toggleGroup(group.id)"
              >
                <span class="collapse-icon">{{ isGroupExpanded(group.id) ? '▼' : '▶' }}</span>
                <h3>{{ group.group_name }}</h3>
                <span class="group-count">{{ getTemplatesByGroup(group.id).length }} 項</span>
              </div>

              <!-- 第 3 層：範本列表 -->
              <div v-show="isGroupExpanded(group.id)" class="templates-list">
                <div
                  v-for="template in getTemplatesByGroup(group.id)"
                  :key="template.id"
                  class="template-card"
                >
                  <div class="template-header">
                    <span class="template-number">#{{ template.item_number }}</span>
                    <h4>{{ template.item_name }}</h4>
                    <span
                      v-for="intentId in (template.intent_ids || [])"
                      :key="intentId"
                      class="badge badge-intent"
                    >
                      🎯 {{ getIntentName(intentId) }}
                    </span>
                    <span class="badge badge-priority" :class="getPriorityClass(template.priority)">
                      優先級: {{ template.priority }}
                    </span>
                  </div>

                  <div class="template-content">
                    <div class="content-section">
                      <strong>範本內容:</strong>
                      <p>{{ template.content }}</p>
                    </div>

                    <div v-if="template.template_notes" class="content-section template-guide">
                      <strong>📝 範本說明:</strong>
                      <p>{{ template.template_notes }}</p>
                    </div>

                    <div v-if="template.customization_hint" class="content-section template-guide">
                      <strong>💡 自訂提示:</strong>
                      <p>{{ template.customization_hint }}</p>
                    </div>
                  </div>

                  <div class="template-actions">
                    <button @click="editTemplate(template)" class="btn btn-sm btn-secondary">
                      ✏️ 編輯
                    </button>
                    <button @click="viewTemplateUsage(template.id)" class="btn btn-sm btn-info">
                      👥 使用情況
                    </button>
                    <button @click="deleteTemplate(template.id)" class="btn btn-sm btn-danger">
                      🗑️ 刪除
                    </button>
                  </div>
                </div>

                <!-- 如果群組內沒有範本 -->
                <div v-if="getTemplatesByGroup(group.id).length === 0" class="no-templates-in-group">
                  此群組尚未建立任何 SOP 項目
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>

      <div v-if="filteredTemplates.length === 0" class="no-templates">
        此業種尚未建立任何 SOP 項目，請點擊「➕ 新增 SOP 項目」開始建立
      </div>
    </div>

    <!-- 新增/編輯範本 Modal -->
    <div v-if="showTemplateModal" class="modal-overlay" @click="showTemplateModal = false">
      <div class="modal-content modal-large" @click.stop>
        <h2>{{ editingTemplate ? '編輯 SOP 項目' : '新增 SOP 項目' }}</h2>
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
              <label>關聯意圖（可複選）</label>
              <div class="intent-checkboxes">
                <label v-for="intent in intents" :key="intent.id" class="checkbox-label">
                  <input
                    type="checkbox"
                    :value="intent.id"
                    v-model="templateForm.intent_ids"
                    class="checkbox-input"
                  />
                  <span class="checkbox-text">{{ intent.name }}</span>
                </label>
              </div>
              <p class="form-hint" v-if="templateForm.intent_ids.length === 0">未選擇任何意圖</p>
              <p class="form-hint" v-else>已選擇 {{ templateForm.intent_ids.length }} 個意圖</p>
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
            <button type="submit" class="btn btn-primary">💾 儲存</button>
            <button type="button" @click="closeTemplateModal" class="btn btn-secondary">取消</button>
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
            <div class="usage-status">
              {{ usage.has_copied ? '✅ 已使用' : '⚪ 未使用' }}
            </div>
            <div v-if="usage.copied_at" class="usage-date">
              複製時間: {{ new Date(usage.copied_at).toLocaleString('zh-TW') }}
            </div>
          </div>
        </div>

        <div v-else class="no-data">
          目前沒有業者使用此範本
        </div>

        <div class="modal-actions">
          <button @click="showUsageModal = false" class="btn btn-secondary">關閉</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

const RAG_API = import.meta.env.VITE_RAG_API || 'http://localhost:8100';

export default {
  name: 'PlatformSOPEditView',

  data() {
    return {
      loading: false,
      categories: [],
      groups: [],
      templates: [],
      intents: [],

      // Accordion states
      expandedCategories: {},
      expandedGroups: {},

      // Modal states
      showTemplateModal: false,
      showUsageModal: false,

      // Editing state
      editingTemplate: null,

      // Forms
      templateForm: {
        category_id: null,
        business_type: null,
        item_number: 1,
        item_name: '',
        content: '',
        intent_ids: [],
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

  computed: {
    businessType() {
      const type = this.$route.params.businessType;
      return type === 'universal' ? null : type;
    },

    businessTypeTitle() {
      const type = this.$route.params.businessType;
      if (type === 'full_service') return '🏠 包租業範本管理';
      if (type === 'property_management') return '🔑 代管業範本管理';
      return '🌐 通用範本管理';
    },

    businessTypeDescription() {
      const type = this.$route.params.businessType;
      if (type === 'full_service') return '管理適用於包租型業者的 SOP 範本';
      if (type === 'property_management') return '管理適用於代管型業者的 SOP 範本';
      return '管理適用於所有業種的通用 SOP 範本';
    },

    filteredTemplates() {
      return this.templates.filter(t => t.business_type === this.businessType);
    }
  },

  watch: {
    'templateForm.category_id'(newCategoryId) {
      // 當選擇分類時，自動設置下一個可用的項次編號（僅在新增模式下）
      if (!this.editingTemplate && newCategoryId) {
        this.templateForm.item_number = this.getNextItemNumber(newCategoryId);
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
          this.loadGroups(),
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
      const response = await axios.get(`${RAG_API}/api/v1/platform/sop/categories`);
      this.categories = response.data.categories;
    },

    async loadGroups() {
      const response = await axios.get(`${RAG_API}/api/v1/platform/sop/groups`);
      this.groups = response.data.groups;
    },

    async loadTemplates() {
      const response = await axios.get(`${RAG_API}/api/v1/platform/sop/templates`);
      this.templates = response.data.templates;
    },

    async loadIntents() {
      try {
        const response = await axios.get(`${RAG_API}/api/v1/intents`);
        this.intents = response.data.intents || [];
      } catch (error) {
        console.error('載入意圖失敗:', error);
        this.intents = [];
      }
    },

    getTemplatesByCategory(categoryId) {
      return this.filteredTemplates.filter(t => t.category_id === categoryId);
    },

    getGroupsByCategory(categoryId) {
      return this.groups.filter(g => g.category_id === categoryId);
    },

    getTemplatesByGroup(groupId) {
      return this.filteredTemplates.filter(t => t.group_id === groupId);
    },

    // Accordion methods
    toggleCategory(categoryId) {
      this.expandedCategories = {
        ...this.expandedCategories,
        [categoryId]: !this.expandedCategories[categoryId]
      };
    },

    isCategoryExpanded(categoryId) {
      return !!this.expandedCategories[categoryId];
    },

    toggleGroup(groupId) {
      this.expandedGroups = {
        ...this.expandedGroups,
        [groupId]: !this.expandedGroups[groupId]
      };
    },

    isGroupExpanded(groupId) {
      return !!this.expandedGroups[groupId];
    },

    // Template CRUD
    getNextItemNumber(categoryId) {
      if (!categoryId) return 1;

      const categoryTemplates = this.templates.filter(t =>
        t.category_id === categoryId && t.business_type === this.businessType
      );

      if (categoryTemplates.length === 0) return 1;

      const maxItemNumber = Math.max(...categoryTemplates.map(t => t.item_number));
      return maxItemNumber + 1;
    },

    openNewTemplateModal() {
      // 重置表單
      this.editingTemplate = null;
      this.templateForm = {
        category_id: null,
        business_type: this.businessType,
        item_number: 1,
        item_name: '',
        content: '',
        intent_ids: [],
        priority: 50,
        template_notes: '',
        customization_hint: ''
      };

      this.showTemplateModal = true;
    },

    editTemplate(template) {
      this.editingTemplate = template;
      this.templateForm = {
        category_id: template.category_id,
        business_type: template.business_type || null,
        item_number: template.item_number,
        item_name: template.item_name,
        content: template.content,
        intent_ids: template.intent_ids && template.intent_ids.length > 0 ? [...template.intent_ids] : [],
        priority: template.priority,
        template_notes: template.template_notes || '',
        customization_hint: template.customization_hint || ''
      };
      this.showTemplateModal = true;
    },

    async saveTemplate() {
      try {
        // Validate required fields
        if (!this.templateForm.category_id) {
          alert('請選擇所屬分類');
          return;
        }

        // Set the business_type based on current view
        this.templateForm.business_type = this.businessType;

        if (this.editingTemplate) {
          // Update
          await axios.put(
            `${RAG_API}/api/v1/platform/sop/templates/${this.editingTemplate.id}`,
            this.templateForm
          );
          alert('範本已更新');
        } else {
          // Create
          await axios.post(
            `${RAG_API}/api/v1/platform/sop/templates`,
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
        await axios.delete(`${RAG_API}/api/v1/platform/sop/templates/${templateId}`);
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
        intent_ids: [],
        priority: 50,
        template_notes: '',
        customization_hint: ''
      };
    },

    async viewTemplateUsage(templateId) {
      try {
        const response = await axios.get(`${RAG_API}/api/v1/platform/sop/templates/${templateId}/usage`);
        this.currentTemplateUsage = response.data;
        this.showUsageModal = true;
      } catch (error) {
        console.error('載入使用情況失敗:', error);
        alert('載入使用情況失敗: ' + error.message);
      }
    },

    // Helper methods
    getIntentName(intentId) {
      const intent = this.intents.find(i => i.id === intentId);
      return intent ? intent.name : `ID:${intentId}`;
    },

    getPriorityClass(priority) {
      if (priority >= 90) return 'priority-high';
      if (priority >= 70) return 'priority-medium';
      return 'priority-low';
    }
  }
};
</script>

<style scoped>
/* Import common styles from PlatformSOPView - you can extract these to a shared CSS file if needed */
.platform-sop-edit-view {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 30px;
  display: flex;
  align-items: center;
  gap: 20px;
}

.btn-back {
  padding: 10px 20px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.btn-back:hover {
  background: #5a6268;
}

.header-content {
  flex: 1;
}

.page-header h1 {
  font-size: 28px;
  color: #333;
  margin: 0 0 8px 0;
}

.subtitle {
  color: #666;
  font-size: 14px;
  margin: 0;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.btn-primary {
  background: #4CAF50;
  color: white;
}

.btn-primary:hover {
  background: #45a049;
}

.btn-secondary {
  background: #2196F3;
  color: white;
}

.btn-secondary:hover {
  background: #0b7dda;
}

.btn-info {
  background: #FF9800;
  color: white;
}

.btn-info:hover {
  background: #e68900;
}

.btn-danger {
  background: #f44336;
  color: white;
}

.btn-danger:hover {
  background: #da190b;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
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

.sop-categories {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.category-section {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.category-header-collapsible {
  background: #f8f9fa;
  padding: 15px 20px;
  border-left: 4px solid #4CAF50;
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

.category-header-collapsible h2 {
  margin: 0;
  font-size: 20px;
  color: #333;
  font-weight: 600;
  flex: 1;
}

.collapse-icon {
  font-size: 14px;
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

/* 群組樣式（第 2 層） */
.groups-list {
  padding: 10px 20px 20px 20px;
}

.group-section {
  background: #f9f9f9;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  margin-bottom: 12px;
  overflow: hidden;
}

.group-header-collapsible {
  background: #ffffff;
  padding: 12px 16px;
  border-left: 4px solid #2196F3;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all 0.2s;
  user-select: none;
}

.group-header-collapsible:hover {
  background: #f5f5f5;
  border-left-color: #1976D2;
}

.group-header-collapsible h3 {
  margin: 0;
  font-size: 16px;
  color: #444;
  font-weight: 600;
  flex: 1;
}

.group-count {
  background: #2196F3;
  color: white;
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
}

.templates-list {
  padding: 16px;
}

.no-templates-in-group {
  text-align: center;
  padding: 30px 20px;
  color: #aaa;
  font-size: 14px;
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

.template-header h4 {
  font-size: 15px;
  color: #333;
  margin: 0;
  flex: 1;
  font-weight: 600;
}

.badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
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

.no-templates {
  text-align: center;
  padding: 60px 20px;
  color: #999;
  font-size: 16px;
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
  font-size: 13px;
  color: #666;
  margin-bottom: 4px;
}

.usage-date {
  font-size: 12px;
  color: #999;
  font-style: italic;
}

.no-data {
  text-align: center;
  padding: 40px;
  color: #999;
  font-style: italic;
}

/* Checkbox styles for multi-intent selection */
.intent-checkboxes {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-top: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: white;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.checkbox-label:hover {
  border-color: #4CAF50;
  background: #f5f5f5;
}

.checkbox-label:has(.checkbox-input:checked) {
  background: #E8F5E9;
  border-color: #4CAF50;
}

.checkbox-input {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #4CAF50;
}

.checkbox-text {
  font-size: 14px;
  color: #333;
  flex: 1;
}

.checkbox-label:has(.checkbox-input:checked) .checkbox-text {
  font-weight: 600;
  color: #2E7D32;
}
</style>
