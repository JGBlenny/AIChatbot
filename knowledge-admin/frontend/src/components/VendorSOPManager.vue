<template>
  <div class="vendor-sop-manager">
    <!-- Tab 導航 -->
    <div class="sop-tabs">
      <button
        @click="activeTab = 'overview'"
        :class="['sop-tab', { active: activeTab === 'overview' }]"
      >
        📚 SOP 範本概覽
      </button>
      <button
        @click="activeTab = 'my-sop'"
        :class="['sop-tab', { active: activeTab === 'my-sop' }]"
      >
        📝 我的 SOP
        <span v-if="mySOP.length" class="badge">{{ mySOP.length }}</span>
      </button>
    </div>

    <!-- SOP 範本概覽 Tab -->
    <div v-if="activeTab === 'overview'" class="tab-content">
      <div class="section-header">
        <h3>SOP 範本概覽</h3>
        <p class="hint">查看符合您業種的完整 SOP 範本，可一鍵複製整份範本</p>
      </div>

      <div v-if="loadingTemplates" class="loading">載入範本資訊中...</div>

      <div v-else>
        <!-- 範本總覽卡片 -->
        <div class="overview-card">
          <div class="overview-header">
            <div class="business-type-info">
              <h4>{{ getBusinessTypeLabel(vendor.business_type) }} SOP 範本</h4>
              <p>為您準備的完整標準作業流程</p>
            </div>
            <div class="overview-stats">
              <div class="stat-item">
                <div class="stat-number">{{ totalCategories }}</div>
                <div class="stat-label">個分類</div>
              </div>
              <div class="stat-item">
                <div class="stat-number">{{ totalTemplates }}</div>
                <div class="stat-label">個項目</div>
              </div>
            </div>
          </div>

          <!-- 範本狀態 -->
          <div v-if="hasCopiedTemplates" class="status-section status-copied-section">
            <div class="status-icon">✅</div>
            <div class="status-content">
              <h5>已複製 SOP 範本</h5>
              <p>您已複製 {{ copiedCount }} 個 SOP 項目，可前往「我的 SOP」標籤進行編輯</p>
            </div>
            <button @click="activeTab = 'my-sop'" class="btn btn-secondary">
              查看我的 SOP
            </button>
          </div>

          <div v-else class="status-section status-empty-section">
            <div class="status-icon">📋</div>
            <div class="status-content">
              <h5>尚未複製 SOP 範本</h5>
              <p>點擊下方按鈕一次複製完整的 SOP 範本（{{ totalCategories }} 個分類，{{ totalTemplates }} 個項目）</p>
            </div>
            <button @click="showCopyAllModal = true" class="btn btn-primary btn-large">
              📋 複製整份 SOP 範本 ({{ totalTemplates }} 個項目)
            </button>
          </div>

          <!-- 分類預覽（3 層結構） -->
          <div class="categories-preview-section">
            <h5>範本分類預覽</h5>
            <div class="categories-grid">
              <div v-for="category in categoryTemplates" :key="category.categoryId" class="category-preview-card">
                <div class="category-preview-header">
                  <span class="category-icon">📁</span>
                  <h6>{{ category.categoryName }}</h6>
                </div>
                <p class="category-preview-description">{{ category.categoryDescription }}</p>
                <div class="category-preview-footer">
                  <span class="items-count">{{ category.groups.length }} 個群組</span>
                  <button
                    @click="toggleCategoryExpand(category)"
                    class="expand-btn"
                  >
                    {{ category.expanded ? '收起' : '展開' }}
                  </button>
                </div>

                <!-- 展開的群組列表 -->
                <div v-if="category.expanded" class="groups-list-compact">
                  <div v-for="group in category.groups" :key="group.groupId" class="group-item-compact">
                    <div class="group-item-header">
                      <span class="group-icon">📂</span>
                      <span class="group-title">{{ group.groupName }}</span>
                      <span class="group-item-count">({{ group.templates.length }})</span>
                    </div>
                    <!-- 群組內的範本列表 -->
                    <div class="templates-list-compact">
                      <div v-for="template in group.templates" :key="template.template_id" class="template-item-compact">
                        <span class="item-num">#{{ template.item_number }}</span>
                        <span class="item-title">{{ template.item_name }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 我的 SOP Tab -->
    <div v-if="activeTab === 'my-sop'" class="tab-content">
      <div class="section-header">
        <h3>我的 SOP</h3>
        <p class="hint">管理您的 SOP，可自由編輯調整</p>
      </div>

      <div v-if="loadingMySOP" class="loading">載入我的 SOP 中...</div>

      <div v-else-if="mySOP.length === 0" class="empty-state">
        <p>尚未複製任何 SOP</p>
        <p class="help-text">前往「SOP 範本概覽」標籤複製整份範本</p>
        <button @click="activeTab = 'overview'" class="btn btn-primary">
          前往複製範本
        </button>
      </div>

      <div v-else>
        <!-- 按分類和群組分組顯示（3 層結構） -->
        <div v-for="category in mySOPByCategory" :key="category.category_id" class="category-section">
          <div class="category-section-header">
            <h4>{{ category.category_name }}</h4>
            <span class="items-count-badge">{{ category.groups.length }} 個群組</span>
          </div>

          <!-- 群組列表 -->
          <div v-for="group in category.groups" :key="group.group_id" class="group-section-mysop">
            <div class="group-section-header">
              <span class="group-icon">📂</span>
              <h5>{{ group.group_name }}</h5>
              <span class="group-items-count">{{ group.items.length }} 個項目</span>
            </div>

            <div class="sop-list">
              <div v-for="sop in group.items" :key="sop.id" class="sop-card">
                <div class="sop-header">
                  <span class="sop-number">#{{ sop.item_number }}</span>
                  <h6>{{ sop.item_name }}</h6>
                  <span v-if="sop.template_item_name" class="source-badge" :title="`來源範本: ${sop.template_item_name}`">
                    📋 範本
                  </span>
                </div>

                <div class="sop-content">
                  <p>{{ sop.content }}</p>
                </div>

                <div class="sop-actions">
                  <button @click="editSOP(sop)" class="btn btn-sm btn-secondary">
                    ✏️ 編輯
                  </button>
                  <button @click="deleteSOP(sop.id)" class="btn btn-sm btn-danger">
                    🗑️ 刪除
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 複製整份範本確認 Modal -->
    <div v-if="showCopyAllModal" class="modal-overlay" @click="showCopyAllModal = false">
      <div class="modal-content" @click.stop>
        <h2>複製整份 SOP 範本</h2>
        <p class="hint">確認要複製完整的業種範本嗎？</p>

        <div class="modal-info">
          <div class="info-row">
            <strong>業種類型:</strong>
            <span>{{ getBusinessTypeLabel(vendor.business_type) }}</span>
          </div>
          <div class="info-row">
            <strong>分類數量:</strong>
            <span>{{ totalCategories }} 個分類</span>
          </div>
          <div class="info-row">
            <strong>項目數量:</strong>
            <span>{{ totalTemplates }} 個 SOP 項目</span>
          </div>
        </div>

        <div class="warning-box" :class="{ 'warning-box-danger': mySOP.length > 0 }">
          <strong>⚠️ {{ mySOP.length > 0 ? '重要警告' : '注意' }}</strong>
          <p v-if="mySOP.length > 0" class="warning-text-danger">
            此操作將<strong>刪除所有現有 SOP</strong>（{{ mySOPByCategory.length }} 個分類，{{ mySOP.length }} 個項目），然後重新複製整份範本。此操作無法復原！
          </p>
          <p v-else>
            複製後將自動創建 {{ totalCategories }} 個分類並匯入所有 SOP 項目，之後您可以自由編輯調整。
          </p>
        </div>

        <div class="modal-actions">
          <button @click="copyAllTemplates" class="btn btn-large" :class="mySOP.length > 0 ? 'btn-danger' : 'btn-primary'">
            <span v-if="mySOP.length > 0">⚠️ 確認覆蓋並複製 {{ totalTemplates }} 個項目</span>
            <span v-else>✅ 確認複製 {{ totalTemplates }} 個項目</span>
          </button>
          <button @click="showCopyAllModal = false" class="btn btn-secondary">取消</button>
        </div>
      </div>
    </div>

    <!-- 編輯 SOP Modal -->
    <div v-if="showEditModal" class="modal-overlay" @click="closeEditModal">
      <div class="modal-content modal-large" @click.stop>
        <h2>編輯 SOP</h2>
        <p class="hint">編輯您的 SOP 內容</p>

        <form @submit.prevent="saveSOP">
          <div class="form-group">
            <label>項目名稱 *</label>
            <input v-model="editingForm.item_name" type="text" required class="form-control" />
          </div>

          <div class="form-group">
            <label>內容 *</label>
            <textarea v-model="editingForm.content" required class="form-control" rows="6"></textarea>
          </div>

          <div class="form-group">
            <label>關聯意圖（可複選）</label>
            <div class="intent-checkboxes">
              <label v-for="intent in intents" :key="intent.id" class="checkbox-label">
                <input
                  type="checkbox"
                  :value="intent.id"
                  v-model="editingForm.intent_ids"
                  class="checkbox-input"
                />
                <span class="checkbox-text">{{ intent.name }}</span>
              </label>
            </div>
            <p class="hint" v-if="editingForm.intent_ids.length === 0">未選擇任何意圖</p>
            <p class="hint" v-else>已選擇 {{ editingForm.intent_ids.length }} 個意圖</p>
          </div>

          <div class="form-group">
            <label>優先級 (0-100)</label>
            <input v-model.number="editingForm.priority" type="number" min="0" max="100" class="form-control" />
          </div>

          <div class="modal-actions">
            <button type="submit" class="btn btn-primary">💾 儲存</button>
            <button type="button" @click="closeEditModal" class="btn btn-secondary">取消</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { API_ENDPOINTS, API_BASE_URL } from '@/config/api';

const RAG_API = API_BASE_URL;  // 使用統一的 API 配置

export default {
  name: 'VendorSOPManager',

  props: {
    vendorId: {
      type: Number,
      required: true
    }
  },

  data() {
    return {
      activeTab: 'overview',
      vendor: {},
      templates: [],
      categoryTemplates: [],
      mySOP: [],
      mySOPByCategory: [],
      intents: [],
      loadingTemplates: false,
      loadingMySOP: false,
      showCopyAllModal: false,
      showEditModal: false,
      editingForm: {
        id: null,
        item_name: '',
        content: '',
        intent_ids: [],  // 多意圖支援（陣列）
        priority: 50
      }
    };
  },

  computed: {
    totalCategories() {
      return this.categoryTemplates.length;
    },
    totalGroups() {
      return this.categoryTemplates.reduce((sum, cat) => sum + cat.groups.length, 0);
    },
    totalTemplates() {
      return this.templates.length;
    },
    hasCopiedTemplates() {
      return this.mySOP.some(sop => sop.template_id !== null);
    },
    copiedCount() {
      return this.mySOP.filter(sop => sop.template_id !== null).length;
    }
  },

  mounted() {
    this.loadVendorInfo();
    this.loadTemplates();
    this.loadMySOP();
    this.loadIntents();
  },

  methods: {
    async loadVendorInfo() {
      try {
        const response = await axios.get(`${RAG_API}/api/v1/vendors/${this.vendorId}`);
        this.vendor = response.data;
      } catch (error) {
        console.error('載入業者資訊失敗:', error);
      }
    },

    async loadTemplates() {
      this.loadingTemplates = true;
      try {
        const response = await axios.get(`${RAG_API}/api/v1/vendors/${this.vendorId}/sop/available-templates`);
        this.templates = response.data;
        this.groupTemplatesByCategory();
      } catch (error) {
        console.error('載入範本失敗:', error);
        alert('載入範本失敗: ' + (error.response?.data?.detail || error.message));
      } finally {
        this.loadingTemplates = false;
      }
    },

    groupTemplatesByCategory() {
      const categoryMap = new Map();

      this.templates.forEach(template => {
        if (!categoryMap.has(template.category_id)) {
          categoryMap.set(template.category_id, {
            categoryId: template.category_id,
            categoryName: template.category_name,
            categoryDescription: template.category_description,
            groups: new Map(),
            expanded: false
          });
        }

        const category = categoryMap.get(template.category_id);

        // Group by groups within category
        if (!category.groups.has(template.group_id)) {
          category.groups.set(template.group_id, {
            groupId: template.group_id,
            groupName: template.group_name,
            templates: [],
            expanded: false
          });
        }

        const group = category.groups.get(template.group_id);
        group.templates.push(template);
      });

      // Convert groups Map to Array for each category
      this.categoryTemplates = Array.from(categoryMap.values()).map(cat => ({
        ...cat,
        groups: Array.from(cat.groups.values())
      })).sort((a, b) =>
        a.categoryName.localeCompare(b.categoryName, 'zh-TW')
      );
    },

    async loadMySOP() {
      this.loadingMySOP = true;
      try {
        const response = await axios.get(`${RAG_API}/api/v1/vendors/${this.vendorId}/sop/items`);
        this.mySOP = response.data;
        this.groupMYSOPByCategory();
      } catch (error) {
        console.error('載入我的 SOP 失敗:', error);
        alert('載入我的 SOP 失敗: ' + (error.response?.data?.detail || error.message));
      } finally {
        this.loadingMySOP = false;
      }
    },

    async groupMYSOPByCategory() {
      // 先取得所有分類
      const response = await axios.get(`${RAG_API}/api/v1/vendors/${this.vendorId}/sop/categories`);
      const categories = response.data;

      // 按分類和群組分組 SOP
      this.mySOPByCategory = categories.map(cat => {
        const catItems = this.mySOP.filter(sop => sop.category_id === cat.id);

        // Group items by group_id
        const groupMap = new Map();
        catItems.forEach(item => {
          if (!groupMap.has(item.group_id)) {
            groupMap.set(item.group_id, {
              group_id: item.group_id,
              group_name: item.group_name,
              items: []
            });
          }
          groupMap.get(item.group_id).items.push(item);
        });

        // Sort items within each group
        groupMap.forEach(group => {
          group.items.sort((a, b) => a.item_number - b.item_number);
        });

        return {
          category_id: cat.id,
          category_name: cat.category_name,
          groups: Array.from(groupMap.values())
        };
      }).filter(cat => cat.groups.length > 0);
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

    async copyAllTemplates() {
      try {
        const response = await axios.post(
          `${RAG_API}/api/v1/vendors/${this.vendorId}/sop/copy-all-templates`
        );

        let message = `✅ ${response.data.message}\n\n`;

        // 顯示刪除資訊（如果有）
        if (response.data.deleted_items > 0) {
          message += `已刪除:\n`;
          message += `  - ${response.data.deleted_categories} 個分類\n`;
          message += `  - ${response.data.deleted_items} 個項目\n\n`;
        }

        // 顯示新建資訊
        message += `已創建:\n`;
        message += `  - ${response.data.categories_created} 個分類\n`;
        message += `  - ${response.data.total_items_copied} 個 SOP 項目`;

        alert(message);

        this.showCopyAllModal = false;
        this.loadTemplates();
        this.loadMySOP();
        this.activeTab = 'my-sop';
      } catch (error) {
        console.error('複製整份範本失敗:', error);
        alert('複製失敗: ' + (error.response?.data?.detail || error.message));
      }
    },

    toggleCategoryExpand(category) {
      category.expanded = !category.expanded;
    },

    editSOP(sop) {
      this.editingForm = {
        id: sop.id,
        item_name: sop.item_name,
        content: sop.content,
        intent_ids: sop.intent_ids && sop.intent_ids.length > 0 ? [...sop.intent_ids] : [],  // 複製陣列
        priority: sop.priority || 50
      };
      this.showEditModal = true;
    },

    closeEditModal() {
      this.showEditModal = false;
      this.editingForm = {
        id: null,
        item_name: '',
        content: '',
        intent_ids: [],
        priority: 50
      };
    },

    async saveSOP() {
      try {
        await axios.put(
          `${RAG_API}/api/v1/vendors/${this.vendorId}/sop/items/${this.editingForm.id}`,
          {
            item_name: this.editingForm.item_name,
            content: this.editingForm.content,
            intent_ids: this.editingForm.intent_ids,  // 傳送意圖陣列
            priority: this.editingForm.priority
          }
        );
        alert('✅ SOP 已更新！');
        this.closeEditModal();
        this.loadMySOP();
      } catch (error) {
        console.error('更新 SOP 失敗:', error);
        alert('更新失敗: ' + (error.response?.data?.detail || error.message));
      }
    },

    async deleteSOP(sopId) {
      if (!confirm('確定要刪除此 SOP 嗎？')) return;

      try {
        await axios.delete(`${RAG_API}/api/v1/vendors/${this.vendorId}/sop/items/${sopId}`);
        alert('✅ SOP 已刪除');
        this.loadMySOP();
      } catch (error) {
        console.error('刪除 SOP 失敗:', error);
        alert('刪除失敗: ' + (error.response?.data?.detail || error.message));
      }
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
.vendor-sop-manager {
  background: white;
  border-radius: 8px;
  padding: 0;
}

/* Tabs */
.sop-tabs {
  display: flex;
  gap: 0;
  border-bottom: 2px solid #e5e7eb;
}

.sop-tab {
  padding: 12px 24px;
  background: none;
  border: none;
  border-bottom: 3px solid transparent;
  cursor: pointer;
  transition: all 0.3s;
  font-weight: 500;
  color: #666;
}

.sop-tab:hover {
  color: #667eea;
}

.sop-tab.active {
  color: #667eea;
  border-bottom-color: #667eea;
  font-weight: bold;
}

.sop-tab .badge {
  display: inline-block;
  background: #667eea;
  color: white;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  margin-left: 6px;
}

/* Tab Content */
.tab-content {
  padding: 25px;
}

.section-header {
  margin-bottom: 20px;
}

.section-header h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
  color: #333;
}

.hint {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.loading,
.empty-state {
  text-align: center;
  padding: 40px;
  color: #999;
}

.help-text {
  color: #999;
  font-size: 13px;
  margin-top: 8px;
}

/* Overview Card */
.overview-card {
  background: #fafafa;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  padding: 0;
  overflow: hidden;
}

.overview-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 30px;
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.business-type-info h4 {
  margin: 0 0 8px 0;
  font-size: 24px;
}

.business-type-info p {
  margin: 0;
  opacity: 0.9;
  font-size: 14px;
}

.overview-stats {
  display: flex;
  gap: 30px;
}

.stat-item {
  text-align: center;
}

.stat-number {
  font-size: 32px;
  font-weight: bold;
  line-height: 1;
}

.stat-label {
  font-size: 12px;
  opacity: 0.9;
  margin-top: 4px;
}

/* Status Section */
.status-section {
  padding: 30px;
  display: flex;
  align-items: center;
  gap: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.status-icon {
  font-size: 48px;
  flex-shrink: 0;
}

.status-content {
  flex: 1;
}

.status-content h5 {
  margin: 0 0 8px 0;
  font-size: 18px;
  color: #333;
}

.status-content p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.status-copied-section {
  background: #E8F5E9;
}

.status-empty-section {
  background: #FFF3E0;
}

/* Categories Preview */
.categories-preview-section {
  padding: 30px;
}

.categories-preview-section h5 {
  margin: 0 0 20px 0;
  font-size: 16px;
  color: #333;
}

.categories-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.category-preview-card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  transition: all 0.2s;
}

.category-preview-card:hover {
  border-color: #667eea;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1);
}

.category-preview-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.category-icon {
  font-size: 24px;
}

.category-preview-header h6 {
  margin: 0;
  font-size: 16px;
  color: #333;
}

.category-preview-description {
  color: #666;
  font-size: 13px;
  margin: 0 0 12px 0;
  line-height: 1.5;
}

.category-preview-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.items-count {
  color: #999;
  font-size: 12px;
}

.expand-btn {
  background: none;
  border: none;
  color: #667eea;
  cursor: pointer;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
}

.expand-btn:hover {
  background: #f0f0f0;
}

.templates-list-compact {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #eee;
}

.template-item-compact {
  padding: 6px 0;
  font-size: 13px;
  color: #666;
  display: flex;
  gap: 8px;
}

.item-num {
  color: #999;
  font-weight: bold;
  min-width: 30px;
}

.item-title {
  flex: 1;
}

/* My SOP Section */
.category-section {
  margin-bottom: 30px;
}

.category-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid #e0e0e0;
}

.category-section-header h4 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.items-count-badge {
  background: #E3F2FD;
  color: #1976D2;
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
}

.sop-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sop-card {
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
}

.sop-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.sop-number {
  background: #9E9E9E;
  color: white;
  padding: 4px 10px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 13px;
}

.sop-header h5 {
  font-size: 16px;
  color: #333;
  margin: 0;
  flex: 1;
}

.source-badge {
  background: #F3E5F5;
  color: #7B1FA2;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.sop-content p {
  margin: 0 0 12px 0;
  color: #666;
  font-size: 14px;
  line-height: 1.6;
  padding: 12px;
  background: white;
  border-radius: 4px;
}

.sop-actions {
  display: flex;
  gap: 8px;
}

/* Buttons */
.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  font-weight: 500;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.btn-large {
  padding: 14px 28px;
  font-size: 16px;
  font-weight: 600;
}

.btn-primary {
  background: #4CAF50;
  color: white;
}

.btn-primary:hover {
  background: #45a049;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(76, 175, 80, 0.3);
}

.btn-secondary {
  background: #2196F3;
  color: white;
}

.btn-secondary:hover {
  background: #0b7dda;
}

.btn-danger {
  background: #f44336;
  color: white;
}

.btn-danger:hover {
  background: #da190b;
}

/* Modal */
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
  border-radius: 12px;
  padding: 30px;
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
  margin-bottom: 16px;
}

.modal-info {
  background: #f5f5f5;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.info-row {
  display: flex;
  margin-bottom: 12px;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-row strong {
  min-width: 100px;
  color: #555;
  font-size: 14px;
}

.info-row span {
  color: #333;
  font-size: 14px;
  font-weight: 600;
}

.warning-box {
  background: #FFF3E0;
  border-left: 4px solid #FF9800;
  padding: 16px;
  border-radius: 4px;
  margin-bottom: 20px;
}

.warning-box strong {
  display: block;
  color: #E65100;
  margin-bottom: 8px;
  font-size: 14px;
}

.warning-box p {
  margin: 0;
  color: #666;
  font-size: 13px;
  line-height: 1.6;
}

.warning-box-danger {
  background: #FFEBEE;
  border-left-color: #F44336;
}

.warning-box-danger strong {
  color: #C62828;
}

.warning-text-danger {
  color: #D32F2F !important;
  font-weight: 500;
}

.warning-text-danger strong {
  font-weight: 700;
  text-decoration: underline;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #555;
  font-weight: 600;
  font-size: 14px;
}

.form-control {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.form-control:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

/* 群組樣式（概覽標籤） */
.groups-list-compact {
  margin-top: 12px;
  padding-left: 12px;
  border-left: 3px solid #E3F2FD;
}

.group-item-compact {
  margin-bottom: 12px;
  padding: 8px;
  background: #F5F5F5;
  border-radius: 4px;
}

.group-item-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-weight: 600;
  color: #1976D2;
}

.group-icon {
  font-size: 14px;
}

.group-title {
  flex: 1;
  font-size: 14px;
}

.group-item-count {
  font-size: 12px;
  color: #666;
  font-weight: normal;
}

/* 群組樣式（我的 SOP 標籤） */
.group-section-mysop {
  margin-bottom: 20px;
  padding: 16px;
  background: #F8F9FA;
  border-radius: 8px;
  border-left: 4px solid #2196F3;
}

.group-section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid #E3F2FD;
}

.group-section-header h5 {
  margin: 0;
  font-size: 16px;
  color: #1976D2;
  flex: 1;
}

.group-items-count {
  font-size: 13px;
  color: #666;
  background: white;
  padding: 4px 12px;
  border-radius: 12px;
}

.sop-card h6 {
  font-size: 15px;
  margin: 0;
  color: #333;
  flex: 1;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

/* 意圖多選框樣式 */
.intent-checkboxes {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid transparent;
}

.checkbox-label:hover {
  background: #e3f2fd;
  border-color: #2196F3;
}

.checkbox-input {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #667eea;
}

.checkbox-text {
  font-size: 14px;
  color: #333;
  user-select: none;
}

.checkbox-label:has(.checkbox-input:checked) {
  background: #E8F5E9;
  border-color: #4CAF50;
}

.checkbox-label:has(.checkbox-input:checked) .checkbox-text {
  font-weight: 600;
  color: #2E7D32;
}
</style>
