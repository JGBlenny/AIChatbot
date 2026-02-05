<template>
  <div>
    <h2>{{ pageTitle }}</h2>
    <p v-if="pageDescription" style="color: #909399; font-size: 14px; margin-bottom: 20px;">
      {{ pageDescription }}
    </p>

    <!-- 說明區塊 -->
    <InfoPanel :config="helpTexts.knowledge" />

    <!-- 工具列 -->
    <div class="toolbar">
      <div style="flex: 1; position: relative;">
        <input
          v-model="searchQuery"
          :placeholder="isIdSearch ? `📌 批量查詢 IDs: ${targetIds.join(', ')}` : '🔍 搜尋知識...'"
          @input="searchKnowledge"
          :class="{ 'id-search-input': isIdSearch }"
        />
        <button
          v-if="isIdSearch"
          @click="clearIdSearch"
          class="btn-clear-search"
          title="清除 ID 查詢"
        >
          ✕
        </button>
      </div>
      <button @click="regenerateEmbeddings" class="btn-secondary btn-sm" :disabled="regenerating" style="margin-right: 10px;">
        {{ regenerating ? '生成中...' : '🔄 批量生成向量' }}
      </button>
      <button @click="showCreateModal" class="btn-primary btn-sm">
        新增知識
      </button>
    </div>

    <!-- 回測優化上下文橫幅 -->
    <div v-if="backtestContext" class="backtest-context-banner">
      <div class="banner-content">
        <span class="banner-icon">🎯</span>
        <div class="banner-text">
          <strong>正在優化回測失敗案例：</strong>
          <span class="context-question">{{ backtestContext }}</span>
        </div>
        <button @click="clearContext" class="btn-close-banner" title="關閉提示">✕</button>
      </div>
    </div>

    <!-- 知識列表 -->
    <div v-if="loading" class="loading">
      <p>載入中...</p>
    </div>

    <div v-else-if="knowledgeList.length === 0" class="empty-state">
      <p>沒有找到知識</p>
      <button @click="showCreateModal" class="btn-primary btn-sm" style="margin-top: 20px;">
        新增第一筆知識
      </button>
    </div>

    <div v-else class="knowledge-list">
      <table>
        <thead>
          <tr>
            <th width="60">ID</th>
            <th>問題摘要</th>
            <th width="120">意圖</th>
            <th width="120">業態類型</th>
            <th width="120">業者</th>
            <th width="80">優先級</th>
            <th width="90">向量</th>
            <th width="180">更新時間</th>
            <th width="150">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in knowledgeList" :key="item.id">
            <td>{{ item.id }}</td>
            <td>{{ item.question_summary || '(無標題)' }}</td>
            <td>
              <div v-if="item.intent_mappings && item.intent_mappings.length > 0" class="intent-badges">
                <span
                  v-for="mapping in item.intent_mappings"
                  :key="mapping.intent_id"
                  :class="['badge', 'badge-intent', mapping.intent_type === 'primary' ? 'badge-primary' : 'badge-secondary']"
                  :title="`${mapping.intent_type === 'primary' ? '主要' : '次要'}意圖`"
                >
                  {{ mapping.intent_name }}
                  <sup v-if="mapping.intent_type === 'primary'">★</sup>
                </span>
              </div>
              <span v-else class="badge badge-unclassified">未分類</span>
            </td>
            <td>
              <div v-if="item.business_types && item.business_types.length > 0" class="business-types-badges">
                <span
                  v-for="btype in item.business_types"
                  :key="btype"
                  class="badge badge-btype"
                  :class="'type-' + getBusinessTypeColor(btype)"
                >
                  {{ getBusinessTypeDisplay(btype) }}
                </span>
              </div>
              <span v-else class="badge badge-universal">通用</span>
            </td>
            <td>
              <span v-if="item.vendor_name" class="badge badge-vendor" :title="`業者 ID: ${item.vendor_id}`">
                {{ item.vendor_name }}
              </span>
              <span v-else class="badge badge-global">全域</span>
            </td>
            <td style="text-align: center;">
              <span
                class="priority-badge"
                :class="item.priority > 0 ? 'priority-enabled' : 'priority-disabled'"
                :title="item.priority > 0 ? '已啟用優先級加成 (+0.15)' : '一般知識'"
              >
                {{ item.priority > 0 ? '☑' : '☐' }}
              </span>
            </td>
            <td style="text-align: center;">
              <span v-if="item.has_embedding" class="badge" style="background: #67c23a; color: white;" title="向量已生成">✓</span>
              <span v-else class="badge" style="background: #e6a23c; color: white;" title="向量未生成">✗</span>
            </td>
            <td>{{ formatDate(item.updated_at) }}</td>
            <td>
              <button @click="editKnowledge(item)" class="btn-edit btn-sm">
                編輯
              </button>
              <button @click="deleteKnowledge(item.id)" class="btn-delete btn-sm">
                刪除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 統計資訊和分頁控制 -->
    <div v-if="knowledgeList.length > 0 && pagination.total > 0" style="margin-top: 20px; display: flex; justify-content: space-between; align-items: center;">
      <div style="color: #606266;">
        總計 {{ pagination.total }} 筆知識，顯示第 {{ pagination.offset + 1 }} - {{ Math.min(pagination.offset + pagination.limit, pagination.total) }} 筆
      </div>
      <div class="pagination-controls">
        <button
          @click="previousPage"
          :disabled="pagination.offset === 0"
          class="btn-pagination"
        >
          ← 上一頁
        </button>
        <span style="margin: 0 15px; color: #606266;">
          第 {{ currentPage }} / {{ totalPages }} 頁
        </span>
        <button
          @click="nextPage"
          :disabled="pagination.offset + pagination.limit >= pagination.total"
          class="btn-pagination"
        >
          下一頁 →
        </button>
        <select v-model="pagination.limit" @change="changePageSize" style="margin-left: 15px; padding: 5px;">
          <option :value="20">每頁 20 筆</option>
          <option :value="50">每頁 50 筆</option>
          <option :value="100">每頁 100 筆</option>
        </select>
      </div>
    </div>

    <!-- 編輯/新增 Modal -->
    <div v-if="showModal" class="modal-overlay">
      <div class="modal-content">
        <h2>{{ editingItem ? '✏️ 編輯知識' : '➕ 新增知識' }}</h2>

        <!-- Phase 3: 在 Modal 中顯示回測優化上下文 -->
        <div v-if="backtestContext" class="modal-context-hint">
          <span class="hint-icon">🎯</span>
          <div class="hint-text-content">
            <strong>優化目標：</strong>
            <span>{{ backtestContext }}</span>
          </div>
        </div>

        <form @submit.prevent="saveKnowledge">
          <div class="form-group">
            <label>問題摘要 *</label>
            <input v-model="formData.question_summary" required placeholder="例如：租金逾期如何處理？" />
          </div>

          <!-- 業態類型選擇 -->
          <div class="form-group">
            <label>業態類型 <span class="field-hint">（點擊標籤選擇，未選擇=通用）</span></label>
            <div class="tag-selector">
              <button
                v-for="btype in availableBusinessTypes"
                :key="btype.type_value"
                type="button"
                class="tag-btn"
                :class="{ 'selected': selectedBusinessTypes.includes(btype.type_value) }"
                @click="toggleBusinessType(btype.type_value)"
              >
                {{ btype.display_name }}
              </button>
            </div>
            <p v-if="selectedBusinessTypes.length === 0" class="hint-text">💡 未選擇=通用知識（適用所有業態）</p>
            <p v-else class="hint-text">✅ 僅適用於：{{ selectedBusinessTypes.map(v => getBusinessTypeDisplay(v)).join('、') }}</p>
          </div>

          <!-- 目標用戶選擇 -->
          <div class="form-group">
            <label>目標用戶 <span class="field-hint">（點擊標籤選擇，未選擇=所有人可見）</span></label>
            <div class="tag-selector">
              <button
                v-for="user in availableTargetUsers"
                :key="user.user_value"
                type="button"
                class="tag-btn"
                :class="{ 'selected': selectedTargetUsers.includes(user.user_value) }"
                @click="toggleTargetUser(user.user_value)"
              >
                {{ user.display_name }}
              </button>
            </div>
            <p v-if="selectedTargetUsers.length === 0" class="hint-text">💡 未選擇=通用知識（所有人可見）</p>
            <p v-else class="hint-text">✅ 僅顯示給：{{ selectedTargetUsers.map(v => availableTargetUsers.find(u => u.user_value === v)?.display_name).join('、') }}</p>
          </div>

          <div class="form-group">
            <label>關鍵字（用逗號分隔）</label>
            <input
              v-model="keywordsString"
              placeholder="租金, 逾期, 提醒"
            />
          </div>

          <!-- 優先級設定 -->
          <div class="form-group">
            <label>
              優先級加成
              <span class="field-hint">（啟用後，搜尋時固定加成 +0.15）</span>
            </label>
            <div class="priority-checkbox-wrapper">
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  v-model="priorityEnabled"
                  class="priority-checkbox"
                />
                <span class="checkbox-text">
                  <strong>啟用優先級加成</strong>
                  <span class="boost-indicator" v-if="priorityEnabled">
                    ✓ 相似度 +0.15
                  </span>
                </span>
              </label>
            </div>
            <p class="hint-text">
              💡 啟用後，此知識在搜尋結果中會獲得固定的優先排序加成
            </p>
          </div>

          <!-- 多意圖選擇 -->
          <div class="form-group">
            <label>意圖關聯 <span class="field-hint">（點擊標籤選擇）</span></label>
            <div class="tag-selector intent-tags">
              <div v-for="intent in availableIntents" :key="intent.id" class="intent-tag-wrapper">
                <button
                  type="button"
                  class="tag-btn"
                  :class="{
                    'selected': selectedIntents.includes(intent.id),
                    'primary-intent': intentTypes[intent.id] === 'primary'
                  }"
                  @click="toggleIntent(intent.id)"
                >
                  {{ intent.name }}
                </button>
                <select
                  v-if="selectedIntents.includes(intent.id)"
                  v-model="intentTypes[intent.id]"
                  class="intent-type-select"
                  @click.stop
                >
                  <option value="primary">主要</option>
                  <option value="secondary">次要</option>
                </select>
              </div>
            </div>
            <p v-if="selectedIntents.length === 0" class="hint-text">💡 未選擇意圖的知識將標記為「未分類」</p>
          </div>

          <!-- 1️⃣ 後續動作 -->
          <div class="form-group">
            <label>後續動作 *</label>
            <select v-model="linkType" @change="onLinkTypeChange" class="form-control">
              <option value="none">無（僅顯示知識庫內容）</option>
              <option value="form">觸發表單（引導用戶填寫表單）</option>
              <option value="api">調用 API（查詢或處理資料）</option>
            </select>
            <small class="form-hint">
              💡 <strong>無</strong>：只顯示知識庫內容，不執行其他動作<br>
              💡 <strong>觸發表單</strong>：引導用戶填寫表單（例如：報修申請），表單內可設定是否完成後調用 API<br>
              💡 <strong>調用 API</strong>：直接調用 API（例如：查詢帳單）
            </small>
          </div>

          <!-- 2️⃣ 表單選擇（選擇「表單」後才顯示） -->
          <div v-if="linkType === 'form'" class="form-group">
            <label>選擇表單 *</label>
            <select v-model="formData.form_id" @change="onFormSelect" class="form-select">
              <option value="">請選擇表單...</option>
              <option v-for="form in availableForms" :key="form.form_id" :value="form.form_id">
                {{ form.form_name }} ({{ form.form_id }})
              </option>
            </select>
            <p v-if="!formData.form_id" class="hint-text">💡 請選擇一個表單</p>
            <p v-else class="hint-text">✅ 已關聯表單：{{ getFormName(formData.form_id) }}</p>
          </div>

          <!-- 3️⃣ 觸發模式（選擇表單後才顯示） -->
          <div v-if="linkType === 'form' && formData.form_id" class="form-group">
            <label>觸發模式 *</label>
            <select v-model="formData.trigger_mode" @change="onTriggerModeChange" class="form-control">
              <option value="auto">自動（系統根據用戶意圖智能判斷）</option>
              <option value="manual">排查型（等待用戶說出關鍵詞後觸發）</option>
              <option value="immediate">行動型（主動詢問用戶是否執行）</option>
            </select>
            <small class="form-hint">
              💡 <strong>自動</strong>：系統智能判斷用戶是否需要填表（詢問時不觸發，執行時觸發）<br>
              &nbsp;&nbsp;&nbsp;&nbsp;範例：「退租流程？」→ 只顯示答案；「我要退租」→ 觸發退租表單<br>
              💡 <strong>排查型</strong>：先在上方「知識庫內容」填寫排查步驟，用戶排查後說出關鍵詞才觸發表單<br>
              &nbsp;&nbsp;&nbsp;&nbsp;範例：內容寫「請檢查溫度設定、濾網...若仍不冷請報修」→ 用戶說「還是不冷」→ 觸發報修表單<br>
              💡 <strong>行動型</strong>：顯示知識庫內容後，立即主動詢問是否執行<br>
              &nbsp;&nbsp;&nbsp;&nbsp;範例：內容寫「租金繳納方式...」→ 自動詢問「是否要登記繳納記錄？」→ 用戶說「要」→ 觸發表單
            </small>
          </div>

          <!-- 4️⃣ manual 模式：觸發關鍵詞 -->
          <div v-if="linkType === 'form' && formData.form_id && formData.trigger_mode === 'manual'" class="form-group">
            <label>觸發關鍵詞 *</label>
            <KeywordsInput
              v-model="formData.trigger_keywords"
              :placeholder="'輸入關鍵詞後按 Enter，例如：還是不行、試過了、無法解決'"
            />
            <small class="form-hint">
              💡 用戶說出任一關鍵詞後，系統會觸發表單填寫
            </small>
          </div>

          <!-- 5️⃣ immediate 模式：確認提示詞 -->
          <div v-if="linkType === 'form' && formData.form_id && formData.trigger_mode === 'immediate'" class="form-group">
            <label>確認提示詞（選填）</label>
            <textarea
              v-model="formData.immediate_prompt"
              class="form-control"
              rows="2"
              placeholder="例如：📋 是否要登記本月租金繳納記錄？"
            ></textarea>
            <small class="form-hint">
              💡 <strong>作用</strong>：顯示知識庫內容後，自動附加此詢問提示<br>
              💡 <strong>留空則使用預設</strong>：「需要安排處理嗎？回覆『要』或『需要』即可開始填寫表單」<br>
              💡 <strong>自訂範例</strong>：「📋 是否要登記本月租金繳納記錄？（回覆『是』或『要』即可開始登記）」
            </small>
          </div>

            <!-- API 端點選擇（選擇「API」後才顯示） -->
            <div v-if="linkType === 'api'" style="margin-top: 15px;">
              <label>選擇 API 端點 *</label>
              <select
                v-model="selectedApiEndpointId"
                class="form-select"
                @change="onApiEndpointChange"
              >
                <option value="">請選擇 API 端點...</option>
                <option
                  v-for="api in availableApiEndpoints"
                  :key="api.endpoint_id"
                  :value="api.endpoint_id"
                >
                  {{ api.endpoint_icon }} {{ api.endpoint_name }} ({{ api.endpoint_id }})
                </option>
              </select>

              <!-- 顯示選中的 API 資訊 -->
              <div v-if="selectedApi" class="api-info-box" style="margin-top: 10px; padding: 10px; background: #f5f5f5; border-radius: 5px;">
                <p><strong>{{ selectedApi.endpoint_icon }} {{ selectedApi.endpoint_name }}</strong></p>
                <p v-if="selectedApi.description" style="font-size: 0.9em; color: #666;">{{ selectedApi.description }}</p>
                <p style="font-size: 0.85em; color: #999;">
                  {{ selectedApi.http_method }} {{ selectedApi.api_url }}
                </p>
                <p v-if="selectedApi.param_mappings && selectedApi.param_mappings.length > 0" style="font-size: 0.85em; color: #666; margin-top: 5px;">
                  📋 需要參數：{{ selectedApi.param_mappings.map(p => p.param_name).join(', ') }}
                </p>
              </div>

              <p v-if="!selectedApiEndpointId" class="hint-text">💡 請選擇一個 API 端點</p>
              <p v-else class="hint-text">✅ 已關聯 API：{{ selectedApi?.endpoint_name }}</p>
            </div>

          <div class="form-group">
            <label>內容 (Markdown) *</label>
            <div class="editor-container">
              <textarea
                v-model="formData.content"
                rows="15"
                class="markdown-editor"
                required
                placeholder="## 適用情境&#10;當租客租金逾期時...&#10;&#10;## 處理步驟&#10;1. 系統自動發送提醒&#10;2. 管理師手動通知"
              ></textarea>
              <div class="markdown-preview" v-html="markdownPreview"></div>
            </div>
          </div>

          <!-- 影片上傳功能 -->
          <div class="form-group">
            <label>📹 教學影片（選填）</label>

            <!-- 上傳區域 -->
            <div v-if="!formData.video_url" class="video-upload-zone">
              <input
                type="file"
                ref="videoInput"
                accept="video/mp4,video/webm,video/quicktime"
                @change="handleVideoSelect"
                style="display: none"
              />

              <button
                type="button"
                @click="$refs.videoInput.click()"
                class="btn-upload-video"
                :disabled="uploading"
              >
                {{ uploading ? '⏳ 上傳中...' : '📤 選擇影片' }}
              </button>

              <p class="upload-hint">
                支援 MP4、WebM、MOV 格式，最大 500MB
              </p>

              <!-- 上傳進度 -->
              <div v-if="uploading" class="upload-progress">
                <div class="progress-bar">
                  <div class="progress-fill" :style="{width: uploadProgress + '%'}"></div>
                </div>
                <span>{{ uploadProgress }}%</span>
              </div>
            </div>

            <!-- 預覽區域 -->
            <div v-else class="video-preview">
              <video controls :src="formData.video_url" class="preview-player"></video>
              <div class="video-info">
                <span v-if="formData.video_file_size">📦 {{ formatFileSize(formData.video_file_size) }}</span>
                <span v-if="formData.video_duration">⏱️ {{ formData.video_duration }}秒</span>
              </div>
              <button
                type="button"
                @click="removeVideo"
                class="btn-remove-video"
              >
                🗑️ 移除影片
              </button>
            </div>
          </div>

          <div class="form-actions">
            <button type="submit" class="btn-primary btn-sm" :disabled="saving">
              {{ saving ? '儲存中...' : '儲存並更新向量' }}
            </button>
            <button type="button" @click="closeModal" class="btn-secondary btn-sm">
              取消
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { marked } from 'marked';
import InfoPanel from '@/components/InfoPanel.vue';
import KeywordsInput from '@/components/KeywordsInput.vue';
import helpTexts from '@/config/help-texts.js';

const API_BASE = '/api';

export default {
  name: 'KnowledgeView',
  components: {
    InfoPanel,
    KeywordsInput
  },
  data() {
    return {
      helpTexts,
      pageTitle: '📚 知識庫管理',
      pageDescription: '',
      knowledgeList: [],
      availableIntents: [],
      availableBusinessTypes: [],
      availableTargetUsers: [],  // 從 API 載入
      availableForms: [],  // 從 API 載入可用表單
      availableApiEndpoints: [],  // 從 API 載入可用 API 端點
      searchQuery: '',
      showModal: false,
      editingItem: null,
      saving: false,
      regenerating: false,
      loading: false,
      stats: null,
      filterMode: null, // 'b2c', 'b2b', 'universal', null
      pagination: {
        limit: 50,
        offset: 0,
        total: 0
      },
      formData: {
        question_summary: '',
        content: '',
        keywords: [],
        intent_mappings: [],
        business_types: [],
        target_user: [],  // 新增：目標用戶類型
        priority: 0,  // 新增：優先級（0-10）
        // 表單關聯
        form_id: '',
        // 🆕 表單觸發模式
        trigger_mode: 'auto',  // 默認為自動
        trigger_keywords: [],  // manual 模式的觸發關鍵詞
        immediate_prompt: '',  // immediate 模式的確認提示詞
        // 動作類型和 API 配置
        action_type: 'direct_answer',
        api_config: null,
        // 影片欄位
        video_url: null,
        video_s3_key: null,
        video_file_size: null,
        video_duration: null,
        video_format: null
      },
      linkType: 'none',  // 關聯類型：'none', 'form', 'api'
      selectedApiEndpointId: '',  // 臨時變量：選中的 API 端點 ID
      keywordsString: '',
      selectedIntents: [],
      intentTypes: {},
      selectedBusinessTypes: [],
      selectedTargetUsers: [],
      searchTimeout: null,
      isIdSearch: false,
      targetIds: [],
      // Phase 2: 回測優化支援
      backtestContext: null,
      autoCreateMode: false,
      autoEditMode: false,
      pendingQuestion: null,
      pendingIntent: null,
      // 影片上傳狀態
      uploading: false,
      uploadProgress: 0
    };
  },
  computed: {
    markdownPreview() {
      if (!this.formData.content) {
        return '<p style="color: #999;">Markdown 預覽區</p>';
      }
      return marked(this.formData.content);
    },
    selectedApi() {
      if (!this.selectedApiEndpointId) {
        return null;
      }
      return this.availableApiEndpoints.find(api => api.endpoint_id === this.selectedApiEndpointId);
    },
    currentPage() {
      return Math.floor(this.pagination.offset / this.pagination.limit) + 1;
    },
    totalPages() {
      return Math.ceil(this.pagination.total / this.pagination.limit);
    },
    priorityEnabled: {
      get() {
        return this.formData.priority > 0;
      },
      set(value) {
        this.formData.priority = value ? 1 : 0;
      }
    }
  },

  watch: {
    '$route.query.filter'(newFilter) {
      // 當過濾參數改變時，更新頁面並重新加載
      this.updateFilterMode(newFilter);
      this.pagination.offset = 0; // 重置到第一頁
      this.loadKnowledge();
    }
  },
  async mounted() {
    // 使用 Vue Router 的標準方式讀取查詢參數
    const query = this.$route.query;
    const idsParam = query.ids;
    const searchParam = query.search;
    const actionParam = query.action;
    const editParam = query.edit;
    const contextParam = query.context;
    const questionParam = query.question;
    const intentParam = query.intent;
    const filterParam = query.filter;

    // 處理過濾模式
    this.updateFilterMode(filterParam);

    // Phase 2: 處理 context 參數（顯示回測優化橫幅）
    if (contextParam) {
      this.backtestContext = contextParam;
    }

    // Phase 2: 處理 action=create 參數（自動打開新增 Modal）
    if (actionParam === 'create') {
      this.autoCreateMode = true;
      this.pendingQuestion = questionParam || null;
      this.pendingIntent = intentParam || null;
    }

    // Phase 2: 處理 edit=true 參數（自動打開編輯 Modal）
    if (editParam === 'true' && idsParam) {
      this.autoEditMode = true;
    }

    if (idsParam) {
      // 如果有 ids 參數，使用逗號分隔的 ID 列表進行搜尋
      const ids = idsParam.split(',').map(id => id.trim());
      this.searchQuery = ids.join(', ');  // 顯示格式：222, 223, 224
      // 設置一個標記，表示這是 ID 批量查詢
      this.isIdSearch = true;
      this.targetIds = ids;
    } else if (searchParam) {
      // 如果有 search 參數，使用它作為搜尋關鍵字
      this.searchQuery = searchParam;
    }

    // 載入基礎資料
    await this.loadIntents();
    await this.loadBusinessTypes();
    await this.loadTargetUsers();
    await this.loadForms();
    await this.loadApiEndpoints();
    this.loadStats();

    // 載入知識列表
    await this.loadKnowledge();

    // Phase 2: 執行自動動作
    if (this.autoCreateMode) {
      // 延遲一點打開 Modal，確保所有資料已載入
      this.$nextTick(() => {
        this.handleAutoCreate();
      });
    } else if (this.autoEditMode && this.knowledgeList.length > 0) {
      // 自動編輯第一個查詢到的知識
      this.$nextTick(() => {
        this.editKnowledge(this.knowledgeList[0]);
      });
    }
  },
  methods: {
    async regenerateEmbeddings() {
      if (!confirm('確定要批量生成所有缺失的向量嗎？')) {
        return;
      }

      this.regenerating = true;
      try {
        const response = await axios.post(`${API_BASE}/knowledge/regenerate-embeddings`);

        if (response.data.success) {
          this.showNotification(
            'success',
            '批量生成完成',
            `成功生成 ${response.data.generated}/${response.data.total} 個向量`
          );

          // 重新加載知識列表
          await this.loadKnowledge();
        }
      } catch (error) {
        console.error('批量生成向量失敗', error);
        this.showNotification('error', '生成失敗', error.response?.data?.detail || '批量生成向量失敗');
      } finally {
        this.regenerating = false;
      }
    },

    updateFilterMode(filterParam) {
      this.filterMode = filterParam || null;
      if (filterParam === 'b2c') {
        this.pageTitle = '🏢 產業知識庫 (B2C)';
        this.pageDescription = '包租型、代管型業態專用知識';
      } else if (filterParam === 'b2b') {
        this.pageTitle = '💼 JGB知識庫 (B2B)';
        this.pageDescription = '系統商業態專用知識';
      } else if (filterParam === 'universal') {
        this.pageTitle = '🌐 通用知識庫';
        this.pageDescription = '適用所有業態的通用知識';
      } else {
        this.pageTitle = '📚 知識庫管理';
        this.pageDescription = '';
      }
    },

    async loadBusinessTypes() {
      try {
        const response = await axios.get('/rag-api/v1/business-types-config');
        this.availableBusinessTypes = response.data.business_types || [];
      } catch (error) {
        console.error('載入業態類型失敗', error);
        // Fallback
        this.availableBusinessTypes = [
          { type_value: 'system_provider', display_name: '系統商', icon: '🖥️' },
          { type_value: 'full_service', display_name: '包租型', icon: '🏠' },
          { type_value: 'property_management', display_name: '代管型', icon: '🔑' }
        ];
      }
    },

    async loadTargetUsers() {
      try {
        const response = await axios.get(`${API_BASE}/target-users`);
        this.availableTargetUsers = response.data.target_users || [];
      } catch (error) {
        console.error('載入目標用戶類型失敗', error);
        // Fallback
        this.availableTargetUsers = [
          { user_value: 'tenant', display_name: '租客', icon: '👤' },
          { user_value: 'landlord', display_name: '房東', icon: '🏠' },
          { user_value: 'property_manager', display_name: '物業管理師', icon: '👔' },
          { user_value: 'system_admin', display_name: '系統管理員', icon: '⚙️' }
        ];
      }
    },

    getBusinessTypeDisplay(typeValue) {
      const btype = this.availableBusinessTypes.find(b => b.type_value === typeValue);
      return btype ? btype.display_name : typeValue;
    },
    getBusinessTypeColor(typeValue) {
      const btype = this.availableBusinessTypes.find(b => b.type_value === typeValue);
      return btype && btype.color ? btype.color : 'gray';
    },

    async loadIntents() {
      try {
        const response = await axios.get(`${API_BASE}/intents`);
        this.availableIntents = response.data.intents;
      } catch (error) {
        console.error('載入意圖失敗', error);
      }
    },

    async loadForms() {
      try {
        const response = await axios.get('/rag-api/v1/forms?is_active=true');
        this.availableForms = response.data || [];
        console.log('📋 已載入表單列表:', this.availableForms.length, '個');
      } catch (error) {
        console.error('載入表單列表失敗', error);
        this.availableForms = [];
      }
    },

    async loadApiEndpoints() {
      try {
        const response = await axios.get('/rag-api/v1/api-endpoints?scope=knowledge&is_active=true');
        this.availableApiEndpoints = response.data || [];
        console.log('🔌 已載入 API 端點列表:', this.availableApiEndpoints.length, '個');
      } catch (error) {
        console.error('載入 API 端點列表失敗', error);
        this.availableApiEndpoints = [];
      }
    },

    getFormName(formId) {
      const form = this.availableForms.find(f => f.form_id === formId);
      return form ? form.form_name : formId;
    },

    onLinkTypeChange() {
      // 切換關聯類型時，清空對應的欄位並設定 action_type
      if (this.linkType === 'none') {
        this.formData.form_id = null;
        this.formData.action_type = 'direct_answer';
        this.formData.api_config = null;
        this.selectedApiEndpointId = '';
      } else if (this.linkType === 'form') {
        this.formData.action_type = 'form_fill';
        this.formData.api_config = null;
        this.selectedApiEndpointId = '';
        // 確保 trigger_mode 有預設值
        if (!this.formData.trigger_mode || this.formData.trigger_mode === 'none') {
          this.formData.trigger_mode = 'auto';
        }
      } else if (this.linkType === 'api') {
        this.formData.form_id = null;
        this.formData.action_type = 'api_call';
        // api_config 會在選擇 API 時構建
      } else if (this.linkType === 'form_api') {
        // 新增：表單+API 模式
        this.formData.action_type = 'form_then_api';
        // 保留表單和 API 配置
      }
    },

    onFormSelect() {
      // 當選擇表單時，確保 trigger_mode 有值
      if (this.formData.form_id) {
        // 如果沒有值或值為 'none'，設為 'auto'
        if (!this.formData.trigger_mode || this.formData.trigger_mode === 'none' || this.formData.trigger_mode === '') {
          this.formData.trigger_mode = 'auto';
        }
        console.log('📋 表單選擇後 trigger_mode:', this.formData.trigger_mode);
      }
    },

    onTriggerModeChange() {
      // 切換 trigger_mode 時清空相關欄位
      if (this.formData.trigger_mode !== 'manual') {
        this.formData.trigger_keywords = [];
      }
      if (this.formData.trigger_mode !== 'immediate') {
        this.formData.immediate_prompt = '';
      }
      console.log('🔄 觸發模式切換:', this.formData.trigger_mode);
    },

    onApiEndpointChange() {
      // API 端點改變時構建 api_config
      if (this.selectedApiEndpointId) {
        this.formData.api_config = {
          endpoint: this.selectedApiEndpointId,
          params: {},
          combine_with_knowledge: true
        };
        console.log('🔌 已構建 api_config:', this.formData.api_config);
      } else {
        this.formData.api_config = null;
      }
    },

    updateIntentType(intentId) {
      // 當意圖被選中時，如果沒有設定類型，預設為 primary
      if (this.selectedIntents.includes(intentId) && !this.intentTypes[intentId]) {
        this.intentTypes[intentId] = this.selectedIntents.length === 1 ? 'primary' : 'secondary';
      }
      // 如果取消選中，移除類型設定
      if (!this.selectedIntents.includes(intentId)) {
        delete this.intentTypes[intentId];
      }
    },

    toggleBusinessType(typeValue) {
      const index = this.selectedBusinessTypes.indexOf(typeValue);
      if (index > -1) {
        this.selectedBusinessTypes.splice(index, 1);
      } else {
        this.selectedBusinessTypes.push(typeValue);
      }
    },

    toggleTargetUser(userValue) {
      const index = this.selectedTargetUsers.indexOf(userValue);
      if (index > -1) {
        this.selectedTargetUsers.splice(index, 1);
      } else {
        this.selectedTargetUsers.push(userValue);
      }
    },

    toggleIntent(intentId) {
      const index = this.selectedIntents.indexOf(intentId);
      if (index > -1) {
        this.selectedIntents.splice(index, 1);
        delete this.intentTypes[intentId];
      } else {
        this.selectedIntents.push(intentId);
        this.updateIntentType(intentId);
      }
    },
    async loadKnowledge() {
      this.loading = true;
      try {
        // 如果是 ID 批量查詢，使用特殊處理
        if (this.isIdSearch && this.targetIds.length > 0) {
          // 方法：逐個查詢每個 ID
          const promises = this.targetIds.map(id =>
            axios.get(`${API_BASE}/knowledge/${id}`).catch(err => {
              console.warn(`ID ${id} 查詢失敗:`, err);
              return null;
            })
          );

          const results = await Promise.all(promises);
          this.knowledgeList = results
            .filter(r => r !== null)
            .map(r => r.data);
          this.pagination.total = this.knowledgeList.length;
          this.pagination.offset = 0;
        } else {
          // 正常的分頁查詢
          const params = {
            limit: this.pagination.limit,
            offset: this.pagination.offset
          };
          if (this.searchQuery && !this.isIdSearch) params.search = this.searchQuery;

          // 根據過濾模式添加業態過濾
          if (this.filterMode === 'b2c') {
            params.business_types = 'full_service,property_management';
          } else if (this.filterMode === 'b2b') {
            params.business_types = 'system_provider';
          } else if (this.filterMode === 'universal') {
            params.universal_only = 'true';
          }

          const response = await axios.get(`${API_BASE}/knowledge`, { params });
          this.knowledgeList = response.data.items;
          this.pagination.total = response.data.total;
        }
      } catch (error) {
        console.error('載入失敗', error);
        alert('載入失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },

    previousPage() {
      if (this.pagination.offset >= this.pagination.limit) {
        this.pagination.offset -= this.pagination.limit;
        this.loadKnowledge();
      }
    },

    nextPage() {
      if (this.pagination.offset + this.pagination.limit < this.pagination.total) {
        this.pagination.offset += this.pagination.limit;
        this.loadKnowledge();
      }
    },

    changePageSize() {
      this.pagination.offset = 0; // 重置到第一頁
      this.loadKnowledge();
    },

    async loadStats() {
      try {
        const response = await axios.get(`${API_BASE}/stats`);
        this.stats = response.data;
      } catch (error) {
        console.error('載入統計失敗', error);
      }
    },

    searchKnowledge() {
      clearTimeout(this.searchTimeout);
      this.searchTimeout = setTimeout(() => {
        this.loadKnowledge();
      }, 500);
    },

    showCreateModal() {
      this.editingItem = null;
      this.formData = {
        question_summary: '',
        content: '',
        keywords: [],
        intent_mappings: [],
        business_types: [],
        target_user: [],
        form_id: null,
        trigger_mode: 'auto',  // 🆕 默認為自動
        trigger_keywords: [],  // 🆕 manual 模式的觸發關鍵詞
        immediate_prompt: '',  // 🆕
        action_type: 'direct_answer',
        api_config: null
      };
      this.linkType = 'none';
      this.selectedApiEndpointId = '';
      this.keywordsString = '';
      this.selectedIntents = [];
      this.intentTypes = {};
      this.selectedBusinessTypes = [];
      this.selectedTargetUsers = [];
      this.showModal = true;
    },

    async editKnowledge(item) {
      this.editingItem = item;

      // Load full knowledge data including intent mappings
      try {
        const response = await axios.get(`${API_BASE}/knowledge/${item.id}`);
        const knowledge = response.data;

        this.formData = {
          question_summary: knowledge.question_summary || '',
          content: knowledge.content || '',
          keywords: knowledge.keywords || [],
          intent_mappings: knowledge.intent_mappings || [],
          business_types: knowledge.business_types || '',
          target_user: knowledge.target_user || [],
          priority: knowledge.priority || 0,  // 載入優先級
          // 表單關聯
          form_id: knowledge.form_id || '',
          // 表單觸發模式
          trigger_mode: knowledge.trigger_mode || 'auto',  // 預設為自動
          trigger_keywords: knowledge.trigger_keywords ? [...knowledge.trigger_keywords] : [],
          immediate_prompt: knowledge.immediate_prompt || '',
          // 動作類型和 API 配置
          action_type: knowledge.action_type || 'direct_answer',
          api_config: knowledge.api_config || null,
          // 影片欄位
          video_url: knowledge.video_url || null,
          video_s3_key: knowledge.video_s3_key || null,
          video_file_size: knowledge.video_file_size || null,
          video_duration: knowledge.video_duration || null,
          video_format: knowledge.video_format || null
        };

        // 根據 action_type 判斷關聯類型
        if (knowledge.action_type === 'form_then_api') {
          // 修正：form_then_api 應該設為 form_api，不是 api
          this.linkType = 'form_api';
          // 載入表單資訊（formData.form_id 已在 Line 1017 設定）
          console.log('📋 載入表單:', knowledge.form_id);
          // 載入 API 資訊
          if (knowledge.api_config && knowledge.api_config.endpoint) {
            this.selectedApiEndpointId = knowledge.api_config.endpoint;
            console.log('🔌 載入 API 端點:', this.selectedApiEndpointId);
          }
        } else if (knowledge.action_type === 'api_call') {
          this.linkType = 'api';
          // 從 api_config 解析出 endpoint
          if (knowledge.api_config && knowledge.api_config.endpoint) {
            this.selectedApiEndpointId = knowledge.api_config.endpoint;
            console.log('🔌 載入 API 端點:', this.selectedApiEndpointId);
          }
        } else if (knowledge.action_type === 'form_fill') {
          this.linkType = 'form';
        } else {
          this.linkType = 'none';
        }

        this.keywordsString = (knowledge.keywords || []).join(', ');

        // 設定已選擇的意圖和類型
        this.selectedIntents = (knowledge.intent_mappings || []).map(m => m.intent_id);
        this.intentTypes = {};
        (knowledge.intent_mappings || []).forEach(m => {
          this.intentTypes[m.intent_id] = m.intent_type;
        });

        // 設定已選擇的業態類型
        this.selectedBusinessTypes = knowledge.business_types || [];

        // 設定已選擇的目標用戶
        this.selectedTargetUsers = knowledge.target_user || [];

        console.log('📖 載入的知識資料:', {
          id: knowledge.id,
          question_summary: knowledge.question_summary,
          business_types: knowledge.business_types,
          selectedBusinessTypes: this.selectedBusinessTypes
        });

        this.showModal = true;
      } catch (error) {
        console.error('載入知識詳情失敗', error);
        alert('載入知識詳情失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    async saveKnowledge() {
      this.saving = true;

      try {
        // 處理關鍵字
        this.formData.keywords = this.keywordsString
          .split(',')
          .map(k => k.trim())
          .filter(k => k);

        // 處理意圖關聯
        this.formData.intent_mappings = this.selectedIntents.map(intentId => ({
          intent_id: intentId,
          intent_type: this.intentTypes[intentId] || 'secondary',
          confidence: 1.0
        }));

        // 處理業態類型（空陣列或 null 表示通用）
        this.formData.business_types = this.selectedBusinessTypes.length > 0
          ? this.selectedBusinessTypes
          : null;

        // 處理目標用戶（空陣列或 null 表示通用/所有人可見）
        this.formData.target_user = this.selectedTargetUsers.length > 0
          ? this.selectedTargetUsers
          : null;

        // 🆕 驗證觸發模式（當有關聯功能時）
        if (this.linkType !== 'none') {
          if (!this.formData.trigger_mode) {
            this.showNotification('error', '請選擇觸發模式', '選擇關聯功能後，必須設定觸發模式');
            this.saving = false;
            return;
          }

          // 驗證 manual 模式必須設定觸發關鍵詞
          if (this.formData.trigger_mode === 'manual') {
            if (!this.formData.trigger_keywords || this.formData.trigger_keywords.length === 0) {
              this.showNotification('error', '請設定觸發關鍵詞', '觸發模式選擇「排查型」時，必須設定至少一個觸發關鍵詞');
              this.saving = false;
              return;
            }
          }
        }

        // 根據關聯類型處理表單和 API 欄位
        if (this.linkType === 'form') {
          // 選擇了表單，必須選擇一個表單
          if (!this.formData.form_id) {
            this.showNotification('error', '請選擇表單', '關聯功能選擇「表單」時，必須選擇一個表單');
            this.saving = false;
            return;
          }
          // 設定 action_type
          this.formData.action_type = 'form_fill';
          this.formData.api_config = null;
        } else if (this.linkType === 'api') {
          // 選擇了 API，必須選擇一個 API 端點
          if (!this.selectedApiEndpointId) {
            this.showNotification('error', '請選擇 API 端點', '關聯功能選擇「API」時，必須選擇一個 API 端點');
            this.saving = false;
            return;
          }
          // 設定 action_type 和構建 api_config
          this.formData.action_type = 'api_call';
          this.formData.api_config = {
            endpoint: this.selectedApiEndpointId,
            params: {},
            combine_with_knowledge: true
          };
          // 清空表單關聯
          this.formData.form_id = null;
            // 🆕 清空表單觸發模式（API 模式不需要）
          this.formData.trigger_mode = 'none';
          this.formData.immediate_prompt = null;
        } else if (this.linkType === 'form_api') {
          // 新增：表單+API 模式
          // 驗證：必須同時選擇表單和 API 端點
          if (!this.formData.form_id) {
            this.showNotification('error', '請選擇表單', '關聯功能選擇「表單+API」時，必須選擇表單');
            this.saving = false;
            return;
          }
          if (!this.selectedApiEndpointId) {
            this.showNotification('error', '請選擇 API 端點', '關聯功能選擇「表單+API」時，必須選擇 API 端點');
            this.saving = false;
            return;
          }
          // 設定 action_type 為 form_then_api
          this.formData.action_type = 'form_then_api';
          // 構建 api_config
          this.formData.api_config = {
            endpoint: this.selectedApiEndpointId,
            params: {},
            combine_with_knowledge: true
          };
          // 保留 form_id（不清空）
        } else {
          // 選擇了「無」，清空所有關聯
          this.formData.action_type = 'direct_answer';
          this.formData.form_id = null;
            this.formData.api_config = null;
          // 🆕 清空表單觸發模式
          this.formData.trigger_mode = 'none';
          this.formData.immediate_prompt = null;
        }

        console.log('📝 準備儲存的資料:', {
          question_summary: this.formData.question_summary,
          business_types: this.formData.business_types,
          target_user: this.formData.target_user,
          form_id: this.formData.form_id,
          trigger_mode: this.formData.trigger_mode,
          trigger_keywords: this.formData.trigger_keywords,
          immediate_prompt: this.formData.immediate_prompt,
          action_type: this.formData.action_type,
          api_config: this.formData.api_config,
          selectedBusinessTypes: this.selectedBusinessTypes,
          selectedTargetUsers: this.selectedTargetUsers
        });

        if (this.editingItem) {
          // 更新
          await axios.put(
            `${API_BASE}/knowledge/${this.editingItem.id}`,
            this.formData
          );
          this.showNotification('success', '知識已更新', '向量已重新生成，可以重新執行回測驗證效果');
        } else {
          // 新增
          await axios.post(`${API_BASE}/knowledge`, this.formData);
          this.showNotification('success', '知識已新增', '新知識已加入知識庫，向量已生成');
        }

        this.closeModal();
        this.loadKnowledge();
        this.loadStats();
      } catch (error) {
        console.error('儲存失敗', error);
        this.showNotification('error', '儲存失敗', error.response?.data?.detail || error.message);
      } finally {
        this.saving = false;
      }
    },

    async deleteKnowledge(id) {
      if (!confirm('確定要刪除這筆知識嗎？刪除後無法復原。')) return;

      try {
        await axios.delete(`${API_BASE}/knowledge/${id}`);
        this.showNotification('success', '刪除成功', '知識已從知識庫中移除');
        this.loadKnowledge();
        this.loadStats();
      } catch (error) {
        console.error('刪除失敗', error);
        this.showNotification('error', '刪除失敗', error.response?.data?.detail || error.message);
      }
    },

    closeModal() {
      this.showModal = false;
      this.editingItem = null;
    },

    formatDate(dateStr) {
      if (!dateStr) return '-';
      const date = new Date(dateStr);
      return date.toLocaleString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    },

    clearIdSearch() {
      this.isIdSearch = false;
      this.targetIds = [];
      this.searchQuery = '';
      // 使用 Vue Router 清除所有查詢參數
      this.$router.replace({ query: {} });
      this.loadKnowledge();
    },

    // Phase 2: 處理自動創建知識
    handleAutoCreate() {
      this.editingItem = null;
      this.formData = {
        question_summary: this.pendingQuestion || '',
        content: '',
        keywords: [],
        intent_mappings: [],
        business_types: [],
        target_user: []
      };
      this.keywordsString = '';
      this.selectedIntents = [];
      this.intentTypes = {};
      this.selectedBusinessTypes = [];
      this.selectedTargetUsers = [];

      // 根據 intent 參數自動選擇意圖
      if (this.pendingIntent) {
        const matchedIntent = this.availableIntents.find(
          intent => intent.name === this.pendingIntent
        );
        if (matchedIntent) {
          this.selectedIntents = [matchedIntent.id];
          this.intentTypes[matchedIntent.id] = 'primary';
        }
      }

      this.showModal = true;
    },

    // Phase 2: 清除回測上下文
    clearContext() {
      this.backtestContext = null;
      // 使用 Vue Router 清除 context 參數
      const query = { ...this.$route.query };
      delete query.context;
      this.$router.replace({ query });
    },

    // Phase 3: 通知系統（替代 alert）
    showNotification(type, title, message) {
      const typeEmoji = {
        'info': 'ℹ️',
        'success': '✅',
        'warning': '⚠️',
        'error': '❌'
      };

      const notification = document.createElement('div');
      notification.className = `notification notification-${type}`;
      notification.innerHTML = `
        <strong>${typeEmoji[type] || 'ℹ️'} ${title}</strong>
        <p>${message}</p>
      `;

      document.body.appendChild(notification);

      // 3秒後自動移除
      setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
      }, 3000);
    },

    // ==================== 影片處理方法 ====================

    async handleVideoSelect(event) {
      const file = event.target.files[0];
      if (!file) return;

      // 檢查檔案大小（500MB）
      const MAX_SIZE = 500 * 1024 * 1024;
      if (file.size > MAX_SIZE) {
        alert(`檔案過大！最大支援 500MB（目前 ${(file.size / (1024*1024)).toFixed(1)}MB）`);
        return;
      }

      // 檢查檔案類型
      const allowedTypes = ['video/mp4', 'video/webm', 'video/quicktime'];
      if (!allowedTypes.includes(file.type)) {
        alert('不支援的影片格式。請使用 MP4、WebM 或 MOV 格式');
        return;
      }

      this.uploading = true;
      this.uploadProgress = 0;

      try {
        // 如果是編輯模式且已有知識ID，直接上傳
        // 如果是新增模式，需要先儲存知識才能上傳影片
        if (!this.editingItem?.id) {
          alert('請先儲存知識後再上傳影片');
          this.uploading = false;
          return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('knowledge_id', this.editingItem.id);

        const response = await fetch('/rag-api/v1/videos/upload', {
          method: 'POST',
          body: formData
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || '上傳失敗');
        }

        const result = await response.json();

        // 更新表單資料
        this.formData.video_url = result.data.url;
        this.formData.video_s3_key = result.data.s3_key;
        this.formData.video_file_size = result.data.size;
        this.formData.video_format = result.data.format;

        this.showNotification('✅ 影片上傳成功！', 'success');

      } catch (error) {
        console.error('上傳錯誤:', error);
        alert('❌ 上傳失敗：' + error.message);
      } finally {
        this.uploading = false;
        this.uploadProgress = 0;
        // 清除 input，允許重新選擇同一個檔案
        if (this.$refs.videoInput) {
          this.$refs.videoInput.value = '';
        }
      }
    },

    async removeVideo() {
      if (!confirm('確定要移除影片嗎？')) return;

      if (!this.editingItem?.id) {
        // 如果是新增模式，只清除前端資料
        this.formData.video_url = null;
        this.formData.video_s3_key = null;
        this.formData.video_file_size = null;
        this.formData.video_duration = null;
        this.formData.video_format = null;
        return;
      }

      try {
        const response = await fetch(
          `/rag-api/v1/videos/${this.editingItem.id}`,
          { method: 'DELETE' }
        );

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || '刪除失敗');
        }

        // 清除表單資料
        this.formData.video_url = null;
        this.formData.video_s3_key = null;
        this.formData.video_file_size = null;
        this.formData.video_duration = null;
        this.formData.video_format = null;

        this.showNotification('✅ 影片已移除', 'success');

      } catch (error) {
        console.error('刪除錯誤:', error);
        alert('❌ 移除失敗：' + error.message);
      }
    },

    formatFileSize(bytes) {
      if (!bytes) return '';
      const mb = bytes / (1024 * 1024);
      return mb.toFixed(2) + ' MB';
    }
  }
};
</script>

<style scoped>
/* 優先級樣式 */
.priority-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  text-align: center;
  min-width: 35px;
}

.priority-enabled {
  background: #e1f3ff;
  color: #409eff;
}

.priority-disabled {
  background: #f4f4f5;
  color: #c0c4cc;
}

.priority-checkbox-wrapper {
  padding: 12px 0;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  padding: 12px;
  border: 2px solid #dcdfe6;
  border-radius: 8px;
  transition: all 0.2s;
}

.checkbox-label:hover {
  border-color: #409eff;
  background: #f5f9ff;
}

.priority-checkbox {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

.checkbox-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.boost-indicator {
  color: #67c23a;
  font-size: 13px;
  font-weight: 600;
}

/* ID 查詢樣式 */
.id-search-input {
  background: #f0f9ff !important;
  border: 2px solid #409EFF !important;
  font-weight: 500;
}

.btn-clear-search {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  color: #909399;
  border: none;
  border-radius: 4px;
  width: 28px;
  height: 28px;
  cursor: pointer;
  font-size: 16px;
  line-height: 28px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-clear-search:hover {
  background: #f5f7fa;
  color: #f56c6c;
  transform: translateY(-50%) scale(1.05);
}

.btn-pagination {
  padding: 8px 16px;
  background: #409EFF;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-pagination:hover:not(:disabled) {
  background: #66B1FF;
  transform: translateY(-1px);
}

.btn-pagination:disabled {
  background: #C0C4CC;
  cursor: not-allowed;
  opacity: 0.6;
}

.pagination-controls {
  display: flex;
  align-items: center;
}

.badge-intent {
  background: #67C23A;
}

.badge-intent:hover {
  background: #85CE61;
}

/* 意圖選擇器樣式 */
.intent-selector {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 6px;
  max-height: 300px;
  overflow-y: auto;
}

.intent-checkbox {
  margin: 8px 0;
  padding: 8px;
  background: white;
  border-radius: 4px;
  transition: background 0.2s;
}

.intent-checkbox:hover {
  background: #ecf5ff;
}

.intent-checkbox label {
  display: flex;
  align-items: center;
  cursor: pointer;
  font-size: 14px;
}

.intent-checkbox input[type="checkbox"] {
  margin-right: 10px;
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.intent-type-selector {
  margin-left: auto;
  padding-left: 15px;
}

.inline-select {
  padding: 4px 8px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 13px;
  background: white;
  cursor: pointer;
}

.inline-select option[value="primary"] {
  font-weight: bold;
  color: #409EFF;
}

.inline-select option[value="secondary"] {
  color: #67C23A;
}

.hint-text {
  color: #909399;
  font-size: 13px;
  font-style: italic;
  margin: 10px 0 0 0;
}

/* 意圖徽章樣式 */
.intent-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.badge-primary {
  background: #409EFF !important;
  color: white !important;
  font-weight: bold;
}

.badge-secondary {
  background: #67C23A !important;
  color: white !important;
}

.badge-unclassified {
  background: #909399 !important;
  color: white !important;
}

.badge sup {
  font-size: 10px;
  margin-left: 2px;
}

/* 業態類型選擇器樣式 */
.business-type-selector {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 6px;
}

.btype-checkbox {
  margin: 8px 0;
  padding: 10px;
  background: white;
  border-radius: 4px;
  transition: background 0.2s;
}

.btype-checkbox:hover {
  background: #ecf5ff;
}

.btype-checkbox label {
  display: flex;
  align-items: center;
  cursor: pointer;
  font-size: 14px;
  gap: 8px;
}

.btype-checkbox input[type="checkbox"] {
  margin-right: 5px;
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.btype-icon {
  font-size: 18px;
}

.btype-desc {
  display: block;
  color: #909399;
  font-size: 12px;
  margin-left: 30px;
  margin-top: 4px;
}

/* 業態類型徽章樣式 */
.business-types-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.badge-universal {
  background: #909399 !important;
  color: white !important;
  font-style: italic;
}

/* 業者徽章樣式 */
.badge-vendor {
  background: #8b5cf6 !important;
  color: white !important;
  font-weight: 500;
}

.badge-global {
  background: #6b7280 !important;
  color: white !important;
  font-style: italic;
}

/* 業態類型顏色樣式 */
.type-blue {
  background: #409eff !important;
  color: white !important;
}
.type-green {
  background: #67c23a !important;
  color: white !important;
}
.type-orange {
  background: #e6a23c !important;
  color: white !important;
}
.type-red {
  background: #f56c6c !important;
  color: white !important;
}
.type-purple {
  background: #9b59b6 !important;
  color: white !important;
}
.type-teal {
  background: #20c997 !important;
  color: white !important;
}
.type-gray {
  background: #909399 !important;
  color: white !important;
}

/* Phase 2: 回測優化上下文橫幅樣式 */
.backtest-context-banner {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 16px 20px;
  margin-bottom: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
  animation: slideDown 0.4s ease-out;
}

@keyframes slideDown {
  from {
    transform: translateY(-20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.banner-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.banner-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.banner-text strong {
  font-size: 14px;
  opacity: 0.95;
}

.context-question {
  font-size: 16px;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.15);
  padding: 6px 12px;
  border-radius: 4px;
  display: inline-block;
  margin-top: 4px;
}

.btn-close-banner {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: none;
  border-radius: 50%;
  width: 28px;
  height: 28px;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  transition: all 0.3s;
  flex-shrink: 0;
}

.btn-close-banner:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: rotate(90deg);
}

/* Phase 3: Modal 內的回測優化上下文提示 */
.modal-context-hint {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
  padding: 12px 16px;
  margin: -20px -30px 20px -30px;
  border-radius: 8px 8px 0 0;
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 2px 8px rgba(245, 87, 108, 0.2);
}

.hint-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.hint-text-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 14px;
}

.hint-text-content strong {
  opacity: 0.9;
  font-size: 13px;
}

.hint-text-content span {
  font-size: 15px;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.15);
  padding: 4px 10px;
  border-radius: 4px;
  display: inline-block;
  margin-top: 2px;
}

/* Phase 3: 通知系統樣式 */
.notification {
  position: fixed;
  top: 80px;
  right: 20px;
  min-width: 300px;
  max-width: 400px;
  padding: 16px 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 9999;
  animation: slideInRight 0.3s ease-out;
  transition: opacity 0.3s ease;
}

.notification strong {
  display: block;
  margin-bottom: 8px;
  font-size: 15px;
}

.notification p {
  margin: 0;
  color: #606266;
  font-size: 14px;
  line-height: 1.5;
}

.notification-info {
  border-left: 4px solid #1890ff;
}

.notification-success {
  border-left: 4px solid #67c23a;
}

.notification-warning {
  border-left: 4px solid #e6a23c;
}

.notification-error {
  border-left: 4px solid #f56c6c;
}

@keyframes slideInRight {
  from {
    transform: translateX(400px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

/* 現代化標籤選擇器樣式 */
.field-hint {
  color: #909399;
  font-size: 12px;
  font-weight: normal;
}

.form-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
  color: #606266;
  background-color: #fff;
  transition: border-color 0.2s;
}

.form-select:focus {
  outline: none;
  border-color: #409eff;
}

.tag-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 6px;
  min-height: 50px;
}

.tag-btn {
  padding: 8px 16px;
  border: 2px solid #dcdfe6;
  border-radius: 20px;
  background: white;
  color: #606266;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.tag-btn:hover {
  border-color: #409eff;
  color: #409eff;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(64, 158, 255, 0.2);
}

.tag-btn.selected {
  background: #409eff;
  border-color: #409eff;
  color: white;
}

.tag-btn.selected.primary-intent {
  background: #e6a23c;
  border-color: #e6a23c;
}

.tag-icon {
  font-size: 16px;
}

/* 意圖標籤專用樣式 */
.intent-tags {
  gap: 8px;
}

.intent-tag-wrapper {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.intent-type-select {
  padding: 4px 8px;
  border: 1px solid #dcdfe6;
  border-radius: 12px;
  font-size: 12px;
  background: white;
  cursor: pointer;
  outline: none;
}

.intent-type-select:focus {
  border-color: #409eff;
}

/* ==================== 影片上傳樣式 ==================== */

.video-upload-zone {
  border: 2px dashed #dcdfe6;
  padding: 30px;
  text-align: center;
  border-radius: 8px;
  background: #fafafa;
  transition: all 0.3s;
}

.video-upload-zone:hover {
  border-color: #409eff;
  background: #ecf5ff;
}

.btn-upload-video {
  padding: 12px 24px;
  background: #409eff;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 500;
  transition: all 0.3s;
}

.btn-upload-video:hover:not(:disabled) {
  background: #66b1ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(64, 158, 255, 0.3);
}

.btn-upload-video:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.upload-hint {
  margin-top: 12px;
  font-size: 13px;
  color: #909399;
}

.upload-progress {
  margin-top: 20px;
  text-align: center;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #ebeef5;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #409eff, #66b1ff);
  transition: width 0.3s;
  animation: progress-animation 1.5s infinite;
}

@keyframes progress-animation {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.video-preview {
  border: 1px solid #dcdfe6;
  padding: 15px;
  border-radius: 8px;
  background: white;
}

.preview-player {
  width: 100%;
  max-height: 400px;
  border-radius: 6px;
  background: #000;
}

.video-info {
  display: flex;
  gap: 20px;
  margin: 12px 0;
  color: #606266;
  font-size: 14px;
}

.video-info span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.btn-remove-video {
  padding: 8px 16px;
  background: #f56c6c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-remove-video:hover {
  background: #f78989;
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(245, 108, 108, 0.3);
}
</style>
