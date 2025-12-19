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
              <h4>SOP 範本總覽</h4>
              <p>按業態選擇並複製您需要的 SOP 範本</p>
            </div>
            <div class="overview-stats">
              <div class="stat-item">
                <div class="stat-number">{{ businessTypeTemplates.length }}</div>
                <div class="stat-label">個業態</div>
              </div>
              <div class="stat-item">
                <div class="stat-number">{{ totalTemplates }}</div>
                <div class="stat-label">個範本</div>
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
              <h5>開始建立您的 SOP</h5>
              <p>請從下方選擇適合的業態，複製對應的 SOP 範本到您的工作區</p>
            </div>
          </div>

          <!-- 業態預覽 -->
          <div class="business-types-preview-section">
            <h5>按業態選擇範本</h5>
            <div class="business-types-grid">
              <div v-for="businessType in businessTypeTemplates" :key="businessType.businessType" class="business-type-card">
                <div class="business-type-header">
                  <span class="business-type-icon">{{ getBusinessTypeIcon(businessType.businessType) }}</span>
                  <h6>{{ businessType.businessTypeLabel }}</h6>
                  <span class="business-type-badge">{{ businessType.totalTemplates }} 個範本</span>
                </div>

                <div class="business-type-actions">
                  <button
                    @click="toggleBusinessTypeExpand(businessType)"
                    class="expand-btn"
                  >
                    {{ businessType.expanded ? '收起' : '查看詳情' }}
                  </button>
                  <button
                    @click="copyBusinessType(businessType)"
                    class="copy-business-type-btn"
                    :disabled="businessType.copying"
                  >
                    {{ businessType.copying ? '複製中...' : '📋 複製此業態' }}
                  </button>
                </div>

                <!-- 展開的分類列表 -->
                <div v-if="businessType.expanded" class="categories-list-under-business-type">
                  <div v-for="category in businessType.categories" :key="category.categoryId" class="category-item-compact">
                    <div class="category-item-header">
                      <span class="category-icon-small">📁</span>
                      <span class="category-title">{{ category.categoryName }}</span>
                      <span class="category-item-count">({{ category.groups.length }} 個群組)</span>
                    </div>

                    <!-- 群組列表 -->
                    <div class="groups-list-compact">
                      <div v-for="group in category.groups" :key="group.groupId" class="group-item-compact">
                        <div class="group-item-header">
                          <span class="group-icon">📂</span>
                          <span class="group-title">{{ group.groupName }}</span>
                          <span class="group-item-count">({{ group.templates.length }})</span>
                        </div>
                        <!-- 範本列表 -->
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
      </div>
    </div>

    <!-- 我的 SOP Tab -->
    <div v-if="activeTab === 'my-sop'" class="tab-content">
      <div class="section-header">
        <h3>我的 SOP</h3>
        <div class="header-actions">
          <button @click="showImportModal = true" class="btn btn-primary">
            📤 匯入 Excel
          </button>
        </div>
      </div>
      <p class="hint">管理您的 SOP，可自由編輯調整</p>

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

    <!-- 匯入 Excel Modal -->
    <div v-if="showImportModal" class="modal-overlay" @click="showImportModal = false">
      <div class="modal-content" @click.stop>
        <h2>📤 匯入 Excel 檔案</h2>
        <p class="hint">從 Excel 檔案批量匯入 SOP 項目</p>

        <div class="warning-box" :class="{ 'warning-box-danger': mySOP.length > 0 }">
          <strong>⚠️ {{ mySOP.length > 0 ? '重要警告' : '注意' }}</strong>
          <p v-if="mySOP.length > 0" class="warning-text-danger">
            匯入將<strong>覆蓋所有現有 SOP</strong>（{{ mySOPByCategory.length }} 個分類，{{ mySOP.length }} 個項目）。此操作無法復原！
          </p>
          <p v-else>
            匯入後將自動創建分類並匯入所有 SOP 項目，之後您可以自由編輯調整。
          </p>
        </div>

        <div class="excel-format-hint">
          <h4>📋 支援的 Excel 格式</h4>
          <ul>
            <li>第一欄：分類名稱</li>
            <li>第二欄：分類說明</li>
            <li>第三欄：項目序號</li>
            <li>第四欄：項目名稱</li>
            <li>第五欄：項目內容</li>
          </ul>
          <p class="hint">檔案格式：.xlsx 或 .xls</p>
        </div>

        <form @submit.prevent="uploadExcel">
          <div class="form-group">
            <label>選擇 Excel 檔案 *</label>
            <input
              type="file"
              ref="fileInput"
              accept=".xlsx,.xls"
              @change="handleFileSelect"
              class="file-input"
              required
            />
            <p v-if="selectedFile" class="selected-file">
              已選擇：{{ selectedFile.name }} ({{ formatFileSize(selectedFile.size) }})
            </p>
          </div>

          <div class="modal-actions">
            <button type="submit" class="btn btn-large" :class="mySOP.length > 0 ? 'btn-danger' : 'btn-primary'" :disabled="uploading || !selectedFile">
              <span v-if="uploading">⏳ 上傳中...</span>
              <span v-else-if="mySOP.length > 0">⚠️ 確認覆蓋並匯入</span>
              <span v-else>✅ 確認匯入</span>
            </button>
            <button type="button" @click="closeImportModal" class="btn btn-secondary" :disabled="uploading">取消</button>
          </div>
        </form>
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

// Vendor SOP API 端點在 RAG Orchestrator 中，必須使用 /rag-api 前綴
const RAG_API = '/rag-api';

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
      businessTypeTemplates: [],  // 按業態分組的範本
      mySOP: [],
      mySOPByCategory: [],
      loadingTemplates: false,
      loadingMySOP: false,
      showCopyAllModal: false,
      showEditModal: false,
      showImportModal: false,  // Excel 匯入 Modal
      uploading: false,  // 上傳中狀態
      selectedFile: null,  // 已選擇的檔案
      editingForm: {
        id: null,
        item_name: '',
        content: ''
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

  async mounted() {
    this.loadVendorInfo();
    this.loadTemplates();
    await this.loadMySOP();

    // 檢查是否有 sop_id 參數，如果有則自動打開編輯
    const sopId = this.$route.query.sop_id;
    if (sopId) {
      // 等待 SOP 列表載入後，找到對應的 SOP 並打開編輯
      this.$nextTick(() => {
        const sop = this.mySOP.find(s => s.id === parseInt(sopId));
        if (sop) {
          this.editSOP(sop);
        }
      });
    }
  },

  methods: {
    async loadVendorInfo() {
      try {
        const response = await axios.get(`${RAG_API}/v1/vendors/${this.vendorId}`);
        this.vendor = response.data;
      } catch (error) {
        console.error('載入業者資訊失敗:', error);
      }
    },

    async loadTemplates() {
      this.loadingTemplates = true;
      try {
        const response = await axios.get(`${RAG_API}/v1/vendors/${this.vendorId}/sop/available-templates`);
        this.templates = response.data;
        this.groupTemplatesByBusinessType();
      } catch (error) {
        console.error('載入範本失敗:', error);
        alert('載入範本失敗: ' + (error.response?.data?.detail || error.message));
      } finally {
        this.loadingTemplates = false;
      }
    },

    groupTemplatesByBusinessType() {
      // 按業態分組
      const businessTypeMap = new Map();

      this.templates.forEach(template => {
        // 取得業態類型，正確處理 null（通用型）
        // business_type 可能是 'full_service'、'property_management' 或 null（通用型）
        const businessType = template.business_type !== undefined ? template.business_type : null;

        if (!businessTypeMap.has(businessType)) {
          businessTypeMap.set(businessType, {
            businessType: businessType,
            businessTypeLabel: this.getBusinessTypeLabel(businessType),
            categories: new Map(),
            totalTemplates: 0,
            expanded: false,
            copying: false
          });
        }

        const businessTypeGroup = businessTypeMap.get(businessType);

        // 按分類分組
        if (!businessTypeGroup.categories.has(template.category_id)) {
          businessTypeGroup.categories.set(template.category_id, {
            categoryId: template.category_id,
            categoryName: template.category_name,
            categoryDescription: template.category_description,
            groups: new Map()
          });
        }

        const category = businessTypeGroup.categories.get(template.category_id);

        // 按群組分組
        if (!category.groups.has(template.group_id)) {
          category.groups.set(template.group_id, {
            groupId: template.group_id,
            groupName: template.group_name,
            templates: []
          });
        }

        const group = category.groups.get(template.group_id);
        group.templates.push(template);
        businessTypeGroup.totalTemplates++;
      });

      // 轉換為陣列
      this.businessTypeTemplates = Array.from(businessTypeMap.values()).map(bt => ({
        ...bt,
        categories: Array.from(bt.categories.values()).map(cat => ({
          ...cat,
          groups: Array.from(cat.groups.values())
        }))
      })).sort((a, b) => {
        // 排序：包租型 > 代管型 > 通用型
        const order = { 'full_service': 1, 'property_management': 2, null: 3 };
        return (order[a.businessType] || 99) - (order[b.businessType] || 99);
      });

      // 保留舊的 categoryTemplates 以兼容其他功能
      this.categoryTemplates = [];
    },

    async loadMySOP() {
      this.loadingMySOP = true;
      try {
        const response = await axios.get(`${RAG_API}/v1/vendors/${this.vendorId}/sop/items`);
        this.mySOP = response.data;
        await this.groupMYSOPByCategory();  // 添加 await 等待分組完成
      } catch (error) {
        console.error('載入我的 SOP 失敗:', error);
        alert('載入我的 SOP 失敗: ' + (error.response?.data?.detail || error.message));
      } finally {
        this.loadingMySOP = false;
      }
    },

    async groupMYSOPByCategory() {
      // 先取得所有分類
      const response = await axios.get(`${RAG_API}/v1/vendors/${this.vendorId}/sop/categories`);
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


    async copyAllTemplates() {
      try {
        const response = await axios.post(
          `${RAG_API}/v1/vendors/${this.vendorId}/sop/copy-all-templates`
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
        message += `  - ${response.data.groups_created} 個群組\n`;
        message += `  - ${response.data.total_items_copied} 個 SOP 項目`;

        // 顯示 embedding 生成資訊
        if (response.data.embedding_generation_triggered > 0) {
          message += `\n\n🚀 已觸發背景生成 ${response.data.embedding_generation_triggered} 個 embeddings`;
        }

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

    async copySingleCategory(category, overwrite = false) {
      // 設定複製中狀態
      category.copying = true;

      try {
        const url = `${RAG_API}/v1/vendors/${this.vendorId}/sop/copy-category/${category.categoryId}${overwrite ? '?overwrite=true' : ''}`;
        const response = await axios.post(url);

        let message = `✅ ${response.data.message}\n\n`;
        message += `分類：${response.data.category_name}\n`;
        message += `群組數：${response.data.groups_created}\n`;
        message += `項目數：${response.data.items_copied}\n`;
        message += `Embeddings：${response.data.embeddings_generated} 個成功`;

        if (response.data.overwritten) {
          message += `\n\n⚠️ 已覆蓋原有分類（刪除 ${response.data.deleted_items} 個項目）`;
        }

        alert(message);

        // 重新載入資料
        this.loadTemplates();
        this.loadMySOP();
      } catch (error) {
        console.error('複製分類失敗:', error);

        // 處理 409 衝突（分類已存在）
        if (error.response?.status === 409) {
          const shouldOverwrite = confirm(
            `分類「${category.categoryName}」已存在。\n\n是否要覆蓋現有的分類？\n（會刪除該分類下的所有現有項目）`
          );

          if (shouldOverwrite) {
            // 遞迴調用，設定 overwrite=true
            await this.copySingleCategory(category, true);
            return;
          }
        } else {
          alert('複製失敗: ' + (error.response?.data?.detail || error.message));
        }
      } finally {
        // 清除複製中狀態
        category.copying = false;
      }
    },

    editSOP(sop) {
      this.editingForm = {
        id: sop.id,
        item_name: sop.item_name,
        content: sop.content
      };
      this.showEditModal = true;
    },

    closeEditModal() {
      this.showEditModal = false;
      this.editingForm = {
        id: null,
        item_name: '',
        content: ''
      };
    },

    async saveSOP() {
      try {
        await axios.put(
          `${RAG_API}/v1/vendors/${this.vendorId}/sop/items/${this.editingForm.id}`,
          {
            item_name: this.editingForm.item_name,
            content: this.editingForm.content
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
        await axios.delete(`${RAG_API}/v1/vendors/${this.vendorId}/sop/items/${sopId}`);
        alert('✅ SOP 已刪除');
        this.loadMySOP();
      } catch (error) {
        console.error('刪除 SOP 失敗:', error);
        alert('刪除失敗: ' + (error.response?.data?.detail || error.message));
      }
    },

    getBusinessTypeLabel(type) {
      const labels = {
        full_service: '包租型',
        property_management: '代管型',
        null: '通用型',
        'null': '通用型'
      };
      return labels[type] || '通用型';
    },

    getBusinessTypeIcon(type) {
      const icons = {
        full_service: '🏠',
        property_management: '🔑',
        null: '📋',
        'null': '📋'
      };
      return icons[type] || '📋';
    },

    toggleBusinessTypeExpand(businessType) {
      businessType.expanded = !businessType.expanded;
    },

    async copyBusinessType(businessType, overwrite = false) {
      businessType.copying = true;

      try {
        // 將 business_type 轉換為 API 參數
        let businessTypeParam = businessType.businessType;
        if (businessTypeParam === null || businessTypeParam === 'null') {
          businessTypeParam = 'universal';
        }

        // 使用統一的 copy-all-templates 端點，帶上 business_type 參數
        const url = `${RAG_API}/v1/vendors/${this.vendorId}/sop/copy-all-templates?business_type=${businessTypeParam}`;
        const response = await axios.post(url);

        let message = `✅ ${response.data.message}\n\n`;
        message += `業態：${response.data.business_type_copied}\n`;
        message += `分類數：${response.data.categories_created}\n`;
        message += `群組數：${response.data.groups_created}\n`;
        message += `項目數：${response.data.total_items_copied}\n`;

        if (response.data.embedding_generation_triggered > 0) {
          message += `Embeddings：已觸發背景生成 ${response.data.embedding_generation_triggered} 個項目`;
        }

        if (response.data.deleted_categories > 0) {
          message += `\n\n⚠️ 已覆蓋原有內容（刪除 ${response.data.deleted_items} 個項目）`;
        }

        alert(message);

        // 重新載入資料
        this.loadTemplates();
        this.loadMySOP();
        this.activeTab = 'my-sop';
      } catch (error) {
        console.error('複製業態失敗:', error);
        alert('複製失敗: ' + (error.response?.data?.detail || error.message));
      } finally {
        businessType.copying = false;
      }
    },

    // ========== Excel 匯入功能 ==========

    handleFileSelect(event) {
      const file = event.target.files[0];
      if (file) {
        // 檢查檔案大小（限制 10MB）
        if (file.size > 10 * 1024 * 1024) {
          alert('檔案過大，請選擇小於 10MB 的檔案');
          this.$refs.fileInput.value = '';
          this.selectedFile = null;
          return;
        }

        // 檢查檔案類型
        if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
          alert('不支援的檔案格式，請上傳 .xlsx 或 .xls 檔案');
          this.$refs.fileInput.value = '';
          this.selectedFile = null;
          return;
        }

        this.selectedFile = file;
      }
    },

    async uploadExcel() {
      if (!this.selectedFile) {
        alert('請選擇要上傳的 Excel 檔案');
        return;
      }

      this.uploading = true;

      try {
        // 創建 FormData
        const formData = new FormData();
        formData.append('file', this.selectedFile);

        // 決定是否覆蓋
        const overwrite = this.mySOP.length > 0;

        // 發送請求
        const url = `${RAG_API}/v1/vendors/${this.vendorId}/sop/import-excel?overwrite=${overwrite}`;
        const response = await axios.post(url, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });

        // 顯示成功訊息
        let message = `✅ ${response.data.message}\n\n`;
        message += `檔案名稱：${response.data.file_name}\n`;

        if (response.data.deleted_categories > 0) {
          message += `已刪除：${response.data.deleted_categories} 個分類、${response.data.deleted_items} 個項目\n`;
        }

        message += `已創建：${response.data.created_categories} 個分類、${response.data.created_items} 個項目\n`;

        if (response.data.embedding_generation_triggered > 0) {
          message += `\n🚀 已觸發背景生成 ${response.data.embedding_generation_triggered} 個 embeddings`;
        }

        alert(message);

        // 關閉 Modal 並重新載入資料
        this.closeImportModal();
        this.loadMySOP();
        this.activeTab = 'my-sop';

      } catch (error) {
        console.error('匯入 Excel 失敗:', error);

        let errorMessage = '匯入失敗: ';
        if (error.response?.status === 409) {
          errorMessage += error.response.data.detail;
        } else {
          errorMessage += error.response?.data?.detail || error.message;
        }

        alert(errorMessage);
      } finally {
        this.uploading = false;
      }
    },

    closeImportModal() {
      this.showImportModal = false;
      this.selectedFile = null;
      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = '';
      }
    },

    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
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

/* Business Types Preview */
.business-types-preview-section {
  padding: 30px;
}

.business-types-preview-section h5 {
  margin: 0 0 20px 0;
  font-size: 16px;
  color: #333;
  font-weight: 600;
}

.business-types-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.business-type-card {
  background: white;
  border: 2px solid #ddd;
  border-radius: 12px;
  padding: 20px;
  transition: all 0.3s;
}

.business-type-card:hover {
  border-color: #667eea;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
  transform: translateY(-2px);
}

.business-type-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 2px solid #f0f0f0;
}

.business-type-icon {
  font-size: 32px;
}

.business-type-header h6 {
  margin: 0;
  font-size: 18px;
  color: #333;
  flex: 1;
  font-weight: 600;
}

.business-type-badge {
  background: #E3F2FD;
  color: #1976D2;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
}

.business-type-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.copy-business-type-btn {
  background: #4CAF50;
  color: white;
  border: none;
  cursor: pointer;
  font-size: 14px;
  padding: 10px 20px;
  border-radius: 6px;
  font-weight: 600;
  transition: all 0.2s;
}

.copy-business-type-btn:hover:not(:disabled) {
  background: #45a049;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(76, 175, 80, 0.3);
}

.copy-business-type-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
  opacity: 0.6;
}

.categories-list-under-business-type {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 2px solid #f0f0f0;
}

.category-item-compact {
  margin-bottom: 16px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #2196F3;
}

.category-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-weight: 600;
  color: #1976D2;
  font-size: 14px;
}

.category-icon-small {
  font-size: 16px;
}

.category-title {
  flex: 1;
}

.category-item-count {
  font-size: 12px;
  color: #666;
  font-weight: normal;
}

/* Categories Preview (舊樣式，保留以防需要) */
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

.category-actions {
  display: flex;
  gap: 8px;
  align-items: center;
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

.copy-category-btn {
  background: #4CAF50;
  color: white;
  border: none;
  cursor: pointer;
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 4px;
  font-weight: 500;
  transition: all 0.2s;
}

.copy-category-btn:hover:not(:disabled) {
  background: #45a049;
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(76, 175, 80, 0.3);
}

.copy-category-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
  opacity: 0.6;
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

/* Excel 匯入 Modal 樣式 */
.excel-format-hint {
  background: #F0F9FF;
  border: 1px solid #BAE6FD;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}

.excel-format-hint h4 {
  margin: 0 0 12px 0;
  color: #0369A1;
  font-size: 15px;
}

.excel-format-hint ul {
  margin: 8px 0;
  padding-left: 24px;
  color: #0C4A6E;
}

.excel-format-hint li {
  margin-bottom: 6px;
  font-size: 13px;
}

.file-input {
  width: 100%;
  padding: 12px;
  border: 2px dashed #ddd;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  background: #FAFAFA;
}

.file-input:hover {
  border-color: #667eea;
  background: #F5F7FF;
}

.selected-file {
  margin-top: 12px;
  padding: 12px;
  background: #E8F5E9;
  border: 1px solid #4CAF50;
  border-radius: 6px;
  color: #2E7D32;
  font-size: 14px;
  font-weight: 500;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header h3 {
  margin: 0;
}
</style>
