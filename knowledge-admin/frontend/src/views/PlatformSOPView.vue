<template>
  <div class="platform-sop-view">
    <h2>🏢 平台 SOP 範本管理</h2>

    <!-- 說明區塊 -->
    <InfoPanel :config="helpTexts.platformSOP" />

    <!-- 操作按鈕區 -->
    <div class="action-bar">
      <button @click="showImportModal = true" class="btn-success btn-sm">
        📥 匯入 Excel
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
    <div v-if="showCategoryModal" class="modal-overlay" @mousedown.self="showCategoryModal = false">
      <div class="modal-content" @mousedown.stop>
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

    <!-- Excel 匯入 Modal -->
    <div v-if="showImportModal" class="modal-overlay" @mousedown.self="showImportModal = false">
      <div class="modal-content" @mousedown.stop>
        <h2>📥 匯入 Excel 替換 SOP 資料</h2>

        <div class="import-warning" style="background: #fff3cd; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
          <strong>⚠️ 警告：</strong>
          <p>匯入將會<strong>替換指定業種</strong>的所有現有範本資料。</p>
          <p>• 會刪除該業種的舊範本，並創建新範本</p>
          <p>• 不會影響其他業種的範本</p>
          <p>請確保 Excel 檔案格式正確，否則可能導致資料遺失。</p>
        </div>

        <form @submit.prevent="importExcel">
          <div class="form-group">
            <label>選擇 Excel 檔案 *</label>
            <input
              type="file"
              @change="handleFileSelect"
              accept=".xlsx,.xls"
              class="form-control"
              required
            />
            <small style="color: #666; display: block; margin-top: 5px;">
              支援格式：.xlsx, .xls | 檔案必須包含 Sheet1
            </small>
          </div>

          <div class="form-group">
            <label>選擇業種 *</label>
            <select v-model="importBusinessType" class="form-control" required>
              <option value="universal">通用範本（所有業種共用）</option>
              <option value="full_service">包租業範本</option>
              <option value="property_management">代管業範本</option>
            </select>
            <small style="color: #666; display: block; margin-top: 5px;">
              選擇此次匯入的 SOP 資料適用的業種類型
            </small>
          </div>

          <div v-if="selectedFile" class="file-info" style="margin: 15px 0; padding: 10px; background: #f8f9fa; border-radius: 4px;">
            <strong>已選擇檔案：</strong> {{ selectedFile.name }}<br>
            <strong>檔案大小：</strong> {{ (selectedFile.size / 1024).toFixed(2) }} KB
          </div>

          <div v-if="importing" class="importing-progress">
            <div class="spinner"></div>
            <p>正在匯入資料，請稍候...</p>
          </div>

          <div v-if="importResult" class="import-result" :class="{'success': importResult.success, 'error': !importResult.success}">
            <h4>{{ importResult.success ? '✅ 匯入成功！' : '❌ 匯入失敗' }}</h4>
            <p>{{ importResult.message }}</p>
            <div v-if="importResult.statistics" class="statistics">
              <p>• 分類：{{ importResult.statistics.categories_created }} 個</p>
              <p>• 群組：{{ importResult.statistics.groups_created }} 個</p>
              <p>• 範本：{{ importResult.statistics.templates_created }} 個</p>
            </div>
          </div>

          <div class="modal-actions">
            <button type="submit" :disabled="!selectedFile || importing" class="btn-success btn-sm">
              {{ importing ? '匯入中...' : '開始匯入' }}
            </button>
            <button type="button" @click="closeImportModal" :disabled="importing" class="btn-secondary btn-sm">
              {{ importResult ? '關閉' : '取消' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 新增/編輯範本 Modal -->
    <div v-if="showTemplateModal" class="modal-overlay" @mousedown.self="showTemplateModal = false">
      <div class="modal-content modal-large" @mousedown.stop>
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

          <!-- 流程配置 -->
          <div class="form-section flow-config-section" style="display: flex; flex-direction: column;">
            <h3>🔄 流程配置（進階）</h3>

            <div class="form-group" style="order: 1;">
              <label>後續動作 *</label>
              <select v-model="templateForm.next_action" @change="onNextActionChange" class="form-control">
                <option value="none">無（僅顯示 SOP 內容）</option>
                <option value="form_fill">觸發表單（引導用戶填寫表單）</option>
                <option value="api_call">調用 API（查詢或處理資料）</option>
              </select>
              <small class="form-hint">
                💡 <strong>無</strong>：只顯示 SOP 內容，不執行其他動作<br>
                💡 <strong>觸發表單</strong>：引導用戶填寫表單（例如：報修申請），表單內可設定是否完成後調用 API<br>
                💡 <strong>調用 API</strong>：直接調用 API（例如：查詢帳單）
              </small>
            </div>

            <!-- 表單選擇 -->
            <div v-if="templateForm.next_action === 'form_fill'" class="form-group" style="order: 2;">
              <label>選擇表單 *</label>
              <select v-model="templateForm.next_form_id" @change="onFormSelect" class="form-control">
                <option :value="null">請選擇表單...</option>
                <option v-for="form in availableForms" :key="form.form_id" :value="form.form_id">
                  {{ form.form_name }} ({{ form.form_id }})
                </option>
              </select>
              <p v-if="templateForm.next_form_id" class="form-hint" style="color: #10b981;">
                ✅ 已關聯表單：{{ getFormName(templateForm.next_form_id) }}
              </p>
              <p v-else class="form-hint" style="color: #ef4444;">
                ⚠️ 請選擇表單，否則後續動作將無法執行
              </p>
            </div>

            <!-- 觸發模式（選擇表單後才顯示） -->
            <div v-if="templateForm.next_action === 'form_fill' && templateForm.next_form_id" class="form-group" style="order: 3;">
              <label>觸發模式 *</label>
              <select v-model="templateForm.trigger_mode" @change="onTriggerModeChange" class="form-control">
                <option value="manual">排查型（等待用戶說出關鍵詞後觸發）</option>
                <option value="immediate">行動型（主動詢問用戶是否執行）</option>
              </select>
              <small class="form-hint">
                💡 <strong>排查型</strong>：先在上方「SOP 內容」填寫排查步驟，用戶排查後說出關鍵詞才觸發表單<br>
                &nbsp;&nbsp;&nbsp;&nbsp;範例：內容寫「請檢查溫度設定、濾網...若仍不冷請報修」→ 用戶說「還是不冷」→ 觸發報修表單<br>
                💡 <strong>行動型</strong>：顯示 SOP 內容後，立即主動詢問是否執行<br>
                &nbsp;&nbsp;&nbsp;&nbsp;範例：內容寫「租金繳納方式...」→ 自動詢問「是否要登記繳納記錄？」→ 用戶說「要」→ 觸發表單
              </small>
            </div>

            <!-- manual 模式：觸發關鍵詞 -->
            <div v-if="templateForm.next_action === 'form_fill' && templateForm.next_form_id && templateForm.trigger_mode === 'manual'" class="form-group" style="order: 4;">
              <label>觸發關鍵詞 *</label>
              <KeywordsInput
                v-model="templateForm.trigger_keywords"
                placeholder="輸入關鍵詞後按 Enter 或逗號"
                hint="💡 用戶說出這些關鍵詞後，才會觸發後續動作。例如：「還是不行」、「需要維修」、「我要預約」"
                :max-keywords="10"
              />
            </div>

            <!-- immediate 模式：確認提示詞（可選） -->
            <div v-if="templateForm.next_action === 'form_fill' && templateForm.next_form_id && templateForm.trigger_mode === 'immediate'" class="form-group" style="order: 5;">
              <label>確認提示詞（選填）</label>
              <textarea
                v-model="templateForm.immediate_prompt"
                class="form-control"
                rows="3"
                placeholder="例如：📋 是否要登記本月租金繳納記錄？"
              ></textarea>
              <small class="form-hint">
                💡 <strong>作用</strong>：顯示 SOP 內容後，自動附加此詢問提示<br>
                💡 <strong>留空則使用預設</strong>：「需要安排處理嗎？回覆『要』或『需要』即可開始填寫表單」<br>
                💡 <strong>自訂範例</strong>：「📋 是否要登記本月租金繳納記錄？（回覆『是』或『要』即可開始登記）」<br>
                <br>
                如需自訂更具體的詢問（例如：「需要安排維修嗎？」），請在上方輸入。
              </small>
            </div>

            <!-- API 配置 -->
            <div v-if="templateForm.next_action === 'api_call'" class="form-group" style="order: 7;">
              <label>API 配置 *</label>

              <!-- 選擇器模式 -->
              <div v-if="!useCustomApiConfig">
                <select v-model="selectedApiEndpointId" @change="onApiEndpointChange" class="form-control">
                  <option value="">請選擇 API 端點...</option>
                  <option v-for="api in availableApiEndpoints" :key="api.endpoint_id" :value="api.endpoint_id">
                    {{ api.endpoint_icon || '🔌' }} {{ api.endpoint_name }} ({{ api.endpoint_id }})
                  </option>
                </select>

                <p v-if="selectedApiEndpointId" class="form-hint" style="color: #10b981; margin-top: 8px;">
                  ✅ 已選擇 API：{{ getApiEndpointName(selectedApiEndpointId) }}
                </p>
                <p v-else-if="templateForm.next_api_config" class="form-hint" style="color: #10b981; margin-top: 8px;">
                  ✅ 已配置自訂 API
                </p>
                <p v-else class="form-hint" style="color: #ef4444; margin-top: 8px;">
                  ⚠️ 請選擇 API 端點或使用自訂配置
                </p>
              </div>

              <!-- 自訂 JSON 編輯器 -->
              <div style="margin-top: 10px;">
                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                  <input
                    type="checkbox"
                    v-model="useCustomApiConfig"
                    @change="onCustomApiConfigToggle"
                  />
                  <span>手動編輯 API 配置 JSON（進階）</span>
                </label>

                <textarea
                  v-if="useCustomApiConfig"
                  v-model="apiConfigJson"
                  @blur="updateApiConfigFromJson"
                  class="form-control json-editor"
                  rows="6"
                  placeholder='{"method": "POST", "endpoint": "...", "params": {}}'
                  style="margin-top: 10px; font-family: 'Courier New', monospace; font-size: 0.9em;"
                ></textarea>

                <small v-if="useCustomApiConfig" class="form-hint">
                  💡 JSON 格式範例：<br>
                  <code style="display: block; background: #f5f5f5; padding: 8px; border-radius: 4px; margin-top: 4px;">
                    {<br>
                    &nbsp;&nbsp;"method": "POST",<br>
                    &nbsp;&nbsp;"endpoint": "http://api.example.com/...",<br>
                    &nbsp;&nbsp;"params": {}<br>
                    }
                  </code>
                </small>
              </div>
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
    <div v-if="showUsageModal" class="modal-overlay" @mousedown.self="showUsageModal = false">
      <div class="modal-content" @mousedown.stop>
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
import KeywordsInput from '@/components/KeywordsInput.vue';
import helpTexts from '@/config/help-texts.js';
import { API_BASE_URL } from '@/config/api';

const RAG_API = `${API_BASE_URL}/rag-api/v1`;  // RAG Orchestrator API

export default {
  name: 'PlatformSOPView',

  components: {
    InfoPanel,
    KeywordsInput
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
      showImportModal: false,

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
        customization_hint: '',
        // 流程配置欄位
        trigger_mode: 'manual',  // 默認為排查型
        next_action: 'none',
        trigger_keywords: [],
        immediate_prompt: '',
        next_form_id: null,
        next_api_config: null
      },

      // 表單和 API 相關
      availableForms: [],
      availableApiEndpoints: [],
      selectedApiEndpointId: '',
      useCustomApiConfig: false,
      apiConfigJson: '',

      currentTemplateUsage: {
        template_id: null,
        template_name: '',
        usage: []
      },

      // Excel 匯入
      selectedFile: null,
      importBusinessType: 'universal',  // 預設為通用範本
      importing: false,
      importResult: null
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
    this.loadAvailableForms();
    this.loadAvailableApiEndpoints();
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

    async loadAvailableForms() {
      try {
        const response = await axios.get(`/api/forms`);
        this.availableForms = response.data || [];
      } catch (error) {
        console.error('載入表單列表失敗:', error);
        this.availableForms = [];
      }
    },

    async loadAvailableApiEndpoints() {
      try {
        const response = await axios.get(`/api/api-endpoints`);
        this.availableApiEndpoints = response.data || [];
      } catch (error) {
        console.error('載入 API 端點列表失敗:', error);
        this.availableApiEndpoints = [];
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
        customization_hint: template.customization_hint || '',
        // 流程配置欄位
        trigger_mode: template.trigger_mode || 'manual',
        next_action: template.next_action || 'none',
        trigger_keywords: template.trigger_keywords || [],
        immediate_prompt: template.immediate_prompt || '',
        next_form_id: template.next_form_id || null,
        next_api_config: template.next_api_config || null
      };

      // 載入 API 配置到輔助變數
      if (template.next_api_config) {
        // 檢查是否為預定義的 API 端點
        const endpointId = template.next_api_config.endpoint;
        const isStandardEndpoint = this.availableApiEndpoints.some(api => api.endpoint_id === endpointId);

        if (isStandardEndpoint) {
          // 使用選擇器模式
          this.selectedApiEndpointId = endpointId;
          this.useCustomApiConfig = false;
          this.apiConfigJson = JSON.stringify(template.next_api_config, null, 2);
        } else {
          // 使用自訂 JSON 模式
          this.selectedApiEndpointId = '';
          this.useCustomApiConfig = true;
          this.apiConfigJson = JSON.stringify(template.next_api_config, null, 2);
        }
      } else {
        // 無 API 配置
        this.selectedApiEndpointId = '';
        this.useCustomApiConfig = false;
        this.apiConfigJson = '';
      }

      console.log('📋 載入範本編輯:', {
        id: template.id,
        trigger_mode: this.templateForm.trigger_mode,
        next_action: this.templateForm.next_action,
        has_keywords: this.templateForm.trigger_keywords.length > 0,
        has_form: !!this.templateForm.next_form_id,
        has_api: !!this.templateForm.next_api_config
      });

      this.showTemplateModal = true;
    },

    // 流程配置相關方法
    onFormSelect() {
      // 當選擇表單時，確保 trigger_mode 有值
      if (this.templateForm.next_form_id) {
        // 如果沒有值，設為 'manual'
        if (!this.templateForm.trigger_mode || this.templateForm.trigger_mode === '') {
          this.templateForm.trigger_mode = 'manual';
        }
        console.log('📋 表單選擇後 trigger_mode:', this.templateForm.trigger_mode);
        // 強制觸發 Vue 的響應式更新
        this.$forceUpdate();
      }
    },

    onTriggerModeChange() {
      // 切換 trigger_mode 時清空相關欄位
      if (this.templateForm.trigger_mode !== 'manual') {
        this.templateForm.trigger_keywords = [];
      }
      if (this.templateForm.trigger_mode !== 'immediate') {
        this.templateForm.immediate_prompt = '';
      }
    },

    onNextActionChange() {
      // 切換 next_action 時清空相關欄位
      if (this.templateForm.next_action !== 'form_fill') {
        this.templateForm.next_form_id = null;
      }
      if (this.templateForm.next_action !== 'api_call') {
        this.templateForm.next_api_config = null;
        this.selectedApiEndpointId = '';
        this.useCustomApiConfig = false;
        this.apiConfigJson = '';
      }
    },

    onApiEndpointChange() {
      if (this.selectedApiEndpointId) {
        // 使用選中的 API 端點構建配置
        this.templateForm.next_api_config = {
          endpoint: this.selectedApiEndpointId,
          params: {},
          combine_with_knowledge: true
        };
        this.useCustomApiConfig = false;
        this.apiConfigJson = JSON.stringify(this.templateForm.next_api_config, null, 2);
      } else if (!this.useCustomApiConfig) {
        this.templateForm.next_api_config = null;
        this.apiConfigJson = '';
      }
    },

    onCustomApiConfigToggle() {
      if (this.useCustomApiConfig) {
        // 切換到手動編輯模式，初始化 JSON
        this.apiConfigJson = this.templateForm.next_api_config
          ? JSON.stringify(this.templateForm.next_api_config, null, 2)
          : '{\n  "method": "POST",\n  "endpoint": "",\n  "params": {}\n}';
        this.selectedApiEndpointId = '';
      } else {
        // 切換回選擇器模式
        try {
          if (this.apiConfigJson.trim()) {
            this.templateForm.next_api_config = JSON.parse(this.apiConfigJson);
          }
        } catch (e) {
          alert('API 配置 JSON 格式錯誤，請檢查');
        }
      }
    },

    updateApiConfigFromJson() {
      // 當 JSON 編輯器內容改變時，更新 next_api_config
      try {
        if (this.apiConfigJson.trim()) {
          this.templateForm.next_api_config = JSON.parse(this.apiConfigJson);
        } else {
          this.templateForm.next_api_config = null;
        }
      } catch (e) {
        // JSON 格式錯誤，不更新
        console.error('JSON 格式錯誤:', e);
      }
    },

    getFormName(formId) {
      const form = this.availableForms.find(f => f.form_id === formId);
      return form ? form.form_name : formId;
    },

    getApiEndpointName(endpointId) {
      const api = this.availableApiEndpoints.find(a => a.endpoint_id === endpointId);
      return api ? api.endpoint_name : endpointId;
    },

    async saveTemplate() {
      try {
        // ===== 驗證流程配置 =====

        // 驗證 manual 模式
        if (this.templateForm.trigger_mode === 'manual') {
          if (!this.templateForm.trigger_keywords || this.templateForm.trigger_keywords.length === 0) {
            alert('❌ 觸發模式選擇「排查型（等待關鍵詞）」時，必須設定至少一個觸發關鍵詞');
            return;
          }
        }

        // immediate 模式不需要驗證 immediate_prompt（系統自動生成）

        // 驗證表單關聯
        if (this.templateForm.next_action === 'form_fill') {
          if (!this.templateForm.next_form_id) {
            alert('❌ 後續動作選擇「觸發表單」時，必須選擇表單');
            return;
          }
        }

        // 驗證 API 配置
        if (this.templateForm.next_action === 'api_call') {
          if (!this.templateForm.next_api_config) {
            alert('❌ 後續動作選擇「調用 API」時，必須配置 API');
            return;
          }

          // 如果使用自訂 JSON，驗證 JSON 格式
          if (this.useCustomApiConfig) {
            try {
              const config = JSON.parse(this.apiConfigJson);
              this.templateForm.next_api_config = config;
            } catch (e) {
              alert('❌ API 配置 JSON 格式錯誤，請檢查：\n' + e.message);
              return;
            }
          }
        }

        // ===== 提交資料 =====
        if (this.editingTemplate) {
          // Update
          await axios.put(
            `${RAG_API}/platform/sop/templates/${this.editingTemplate.id}`,
            this.templateForm
          );
          alert('✅ 範本已更新');
        } else {
          // Create
          await axios.post(
            `${RAG_API}/platform/sop/templates`,
            this.templateForm
          );
          alert('✅ 範本已建立');
        }
        this.closeTemplateModal();
        this.loadTemplates();
      } catch (error) {
        console.error('儲存範本失敗:', error);
        alert('❌ 儲存範本失敗: ' + (error.response?.data?.detail || error.message));
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
        customization_hint: '',
        // 流程配置欄位
        trigger_mode: 'manual',  // 默認為排查型
        next_action: 'none',
        trigger_keywords: [],
        immediate_prompt: '',
        next_form_id: null,
        next_api_config: null
      };
      // 重置輔助變數
      this.selectedApiEndpointId = '';
      this.useCustomApiConfig = false;
      this.apiConfigJson = '';
    },

    // Excel 匯入相關方法
    handleFileSelect(event) {
      const file = event.target.files[0];
      if (file) {
        this.selectedFile = file;
        this.importResult = null;  // 重置結果
      }
    },

    async importExcel() {
      if (!this.selectedFile) {
        alert('請先選擇 Excel 檔案');
        return;
      }

      const businessTypeNames = {
        'universal': '通用範本',
        'full_service': '包租業範本',
        'property_management': '代管業範本'
      };
      const typeName = businessTypeNames[this.importBusinessType] || this.importBusinessType;

      if (!confirm(`⚠️ 確定要匯入嗎？\n\n這將會替換 "${typeName}" 的所有現有範本。\n其他業種的範本不受影響。\n\n此操作無法復原！`)) {
        return;
      }

      this.importing = true;
      this.importResult = null;

      try {
        const formData = new FormData();
        formData.append('file', this.selectedFile);

        const response = await axios.post(
          `${RAG_API}/platform/sop/import-excel?replace_mode=replace&business_type=${this.importBusinessType}`,
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data'
            }
          }
        );

        this.importResult = response.data;

        if (response.data.success) {
          alert(`✅ 匯入成功！\n\n• 分類：${response.data.statistics.categories_created} 個\n• 群組：${response.data.statistics.groups_created} 個\n• 範本：${response.data.statistics.templates_created} 個`);

          // 重新載入資料
          await this.loadCategories();
          await this.loadTemplates();

          // 延遲關閉 modal
          setTimeout(() => {
            this.closeImportModal();
          }, 2000);
        }
      } catch (error) {
        console.error('匯入失敗:', error);
        this.importResult = {
          success: false,
          message: error.response?.data?.detail || error.message || '匯入失敗'
        };
        alert(`❌ 匯入失敗：\n${this.importResult.message}`);
      } finally {
        this.importing = false;
      }
    },

    closeImportModal() {
      this.showImportModal = false;
      this.selectedFile = null;
      this.importBusinessType = 'universal';  // 重置為預設值
      this.importing = false;
      this.importResult = null;
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


.action-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.loading {
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

.modal-content {
  padding: 24px;
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
  gap: 16px;
}

.form-hint {
  display: block;
  margin-top: 4px;
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
