<template>
  <div>
    <h2>📚 知識庫管理</h2>

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
      <button @click="showCreateModal" class="btn-primary btn-sm">
        新增知識
      </button>
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
            <th>標題</th>
            <th width="120">分類</th>
            <th width="120">意圖</th>
            <th width="100">對象</th>
            <th width="120">業態類型</th>
            <th width="180">更新時間</th>
            <th width="150">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in knowledgeList" :key="item.id">
            <td>{{ item.id }}</td>
            <td>{{ item.title || item.question_summary || '(無標題)' }}</td>
            <td><span class="badge">{{ item.category }}</span></td>
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
            <td>{{ item.audience }}</td>
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
    <div v-if="stats && knowledgeList.length > 0" style="margin-top: 20px; display: flex; justify-content: space-between; align-items: center;">
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
    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <h2>{{ editingItem ? '✏️ 編輯知識' : '➕ 新增知識' }}</h2>

        <form @submit.prevent="saveKnowledge">
          <div class="form-group">
            <label>標題 *</label>
            <input v-model="formData.title" required placeholder="例如：租金逾期處理" />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>分類 *</label>
              <select v-model="formData.category" required>
                <option value="">請選擇</option>
                <option
                  v-for="cat in categories"
                  :key="cat.category_value"
                  :value="cat.category_value"
                >
                  {{ cat.display_name }}
                </option>
              </select>
            </div>

            <div class="form-group">
              <label>對象 *</label>
              <select v-model="formData.audience" required @change="onAudienceChange">
                <option value="">請選擇</option>
                <optgroup label="🏠 B2C - 終端用戶（External）" v-if="availableAudiences.external.length > 0">
                  <option
                    v-for="aud in availableAudiences.external"
                    :key="aud.audience_value"
                    :value="aud.audience_value"
                  >
                    {{ aud.display_name }}
                  </option>
                </optgroup>
                <optgroup label="🏢 B2B - 內部管理（Internal）" v-if="availableAudiences.internal.length > 0">
                  <option
                    v-for="aud in availableAudiences.internal"
                    :key="aud.audience_value"
                    :value="aud.audience_value"
                  >
                    {{ aud.display_name }}
                  </option>
                </optgroup>
                <optgroup label="📌 通用" v-if="availableAudiences.both.length > 0">
                  <option
                    v-for="aud in availableAudiences.both"
                    :key="aud.audience_value"
                    :value="aud.audience_value"
                  >
                    {{ aud.display_name }}
                  </option>
                </optgroup>
              </select>
              <small class="audience-hint">💡 {{ audienceHint }}</small>
            </div>
          </div>

          <!-- 業態類型選擇 -->
          <div class="form-group">
            <label>業態類型（可選擇多個，未選擇=通用）</label>
            <div class="business-type-selector">
              <div v-for="btype in availableBusinessTypes" :key="btype.type_value" class="btype-checkbox">
                <label>
                  <input
                    type="checkbox"
                    :value="btype.type_value"
                    v-model="selectedBusinessTypes"
                  />
                  <span class="btype-icon" v-if="btype.icon">{{ btype.icon }}</span>
                  {{ btype.display_name }}
                  <small v-if="btype.description" class="btype-desc">{{ btype.description }}</small>
                </label>
              </div>
              <p v-if="selectedBusinessTypes.length === 0" class="hint-text">💡 未選擇業態=通用知識（適用所有業態）</p>
              <p v-else class="hint-text">✅ 僅適用於：{{ selectedBusinessTypes.map(v => getBusinessTypeDisplay(v)).join('、') }}</p>
            </div>
          </div>

          <div class="form-group">
            <label>問題摘要</label>
            <input
              v-model="formData.question_summary"
              placeholder="簡短描述問題（可選）"
            />
          </div>

          <div class="form-group">
            <label>關鍵字（用逗號分隔）</label>
            <input
              v-model="keywordsString"
              placeholder="租金, 逾期, 提醒"
            />
          </div>

          <!-- 多意圖選擇 -->
          <div class="form-group">
            <label>意圖關聯（可選擇多個）</label>
            <div class="intent-selector">
              <div v-for="intent in availableIntents" :key="intent.id" class="intent-checkbox">
                <label>
                  <input
                    type="checkbox"
                    :value="intent.id"
                    v-model="selectedIntents"
                    @change="updateIntentType(intent.id)"
                  />
                  {{ intent.name }}
                  <span v-if="selectedIntents.includes(intent.id)" class="intent-type-selector">
                    <select v-model="intentTypes[intent.id]" class="inline-select">
                      <option value="primary">主要</option>
                      <option value="secondary">次要</option>
                    </select>
                  </span>
                </label>
              </div>
              <p v-if="selectedIntents.length === 0" class="hint-text">💡 未選擇意圖的知識將標記為「未分類」</p>
            </div>
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

const API_BASE = '/api';

export default {
  name: 'KnowledgeView',
  data() {
    return {
      knowledgeList: [],
      availableIntents: [],
      availableAudiences: {
        external: [],
        internal: [],
        both: []
      },
      availableBusinessTypes: [],
      searchQuery: '',
      showModal: false,
      editingItem: null,
      saving: false,
      loading: false,
      stats: null,
      pagination: {
        limit: 50,
        offset: 0,
        total: 0
      },
      formData: {
        title: '',
        category: '',
        audience: '',
        content: '',
        keywords: [],
        question_summary: '',
        intent_mappings: [],
        business_types: []
      },
      keywordsString: '',
      selectedIntents: [],
      intentTypes: {},
      selectedBusinessTypes: [],
      searchTimeout: null,
      isIdSearch: false,
      targetIds: [],
      audienceHint: '選擇對象後將顯示適用場景'
    };
  },
  computed: {
    markdownPreview() {
      if (!this.formData.content) {
        return '<p style="color: #999;">Markdown 預覽區</p>';
      }
      return marked(this.formData.content);
    },
    currentPage() {
      return Math.floor(this.pagination.offset / this.pagination.limit) + 1;
    },
    totalPages() {
      return Math.ceil(this.pagination.total / this.pagination.limit);
    }
  },
  mounted() {
    // 檢查 URL 查詢參數
    const urlParams = new URLSearchParams(window.location.hash.split('?')[1]);
    const idsParam = urlParams.get('ids');
    const searchParam = urlParams.get('search');

    if (idsParam) {
      // 如果有 ids 參數，使用逗號分隔的 ID 列表進行搜尋
      const ids = idsParam.split(',').map(id => id.trim());
      this.searchQuery = ids.join(' OR ');
      // 設置一個標記，表示這是 ID 批量查詢
      this.isIdSearch = true;
      this.targetIds = ids;
    } else if (searchParam) {
      // 如果有 search 參數，使用它作為搜尋關鍵字
      this.searchQuery = searchParam;
    }

    this.loadKnowledge();
    this.loadIntents();
    this.loadAudiences();
    this.loadBusinessTypes();
    this.loadStats();
  },
  methods: {
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


    getBusinessTypeDisplay(typeValue) {
      const btype = this.availableBusinessTypes.find(b => b.type_value === typeValue);
      return btype ? btype.display_name : typeValue;
    },
    getBusinessTypeColor(typeValue) {
      const btype = this.availableBusinessTypes.find(b => b.type_value === typeValue);
      return btype && btype.color ? btype.color : 'gray';
    },
    onAudienceChange() {
      // 根據選擇的 audience 更新提示文字
      const audienceHints = {
        '租客': 'B2C - 租客使用業者 AI 客服時可見（user_role=customer + external scope）',
        '房東': 'B2C - 房東使用業者 AI 客服時可見（user_role=customer + external scope）',
        '租客|管理師': 'B2C + B2B - 租客和管理師都可見（混合場景）',
        '房東|租客': 'B2C - 房東和租客都可見（user_role=customer + external scope）',
        '房東|租客|管理師': 'B2C + B2B - 所有終端用戶和管理師都可見',
        '管理師': 'B2B - 業者員工使用內部系統時可見（user_role=staff + internal scope）',
        '系統管理員': 'B2B - 系統管理員專用（user_role=staff + internal scope）',
        '房東/管理師': 'B2B - 房東相關的內部管理（user_role=staff + internal scope）',
        'general': '通用 - 所有業務範圍都可見（B2C 和 B2B）'
      };

      this.audienceHint = audienceHints[this.formData.audience] || '選擇對象後將顯示適用場景';
    },

    async loadIntents() {
      try {
        const response = await axios.get(`${API_BASE}/intents`);
        this.availableIntents = response.data.intents;
      } catch (error) {
        console.error('載入意圖失敗', error);
      }
    },

    async loadAudiences() {
      try {
        const response = await axios.get('/rag-api/v1/audience-config/grouped');
        this.availableAudiences = response.data;
      } catch (error) {
        console.error('載入受眾選項失敗', error);
        // 如果載入失敗，使用預設選項（fallback）
        this.availableAudiences = {
          external: [
            { audience_value: '租客', display_name: '租客', description: 'B2C - 租客專用知識' },
            { audience_value: '房東', display_name: '房東', description: 'B2C - 房東專用知識' }
          ],
          internal: [
            { audience_value: '管理師', display_name: '管理師', description: 'B2B - 管理師專用知識' }
          ],
          both: [
            { audience_value: 'general', display_name: '所有人（通用）', description: '所有業務範圍都可見' }
          ]
        };
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
        title: '',
        category: '',
        audience: '',
        content: '',
        keywords: [],
        question_summary: '',
        intent_mappings: [],
        business_types: []
      };
      this.keywordsString = '';
      this.selectedIntents = [];
      this.intentTypes = {};
      this.selectedBusinessTypes = [];
      this.showModal = true;
    },

    async editKnowledge(item) {
      this.editingItem = item;

      // Load full knowledge data including intent mappings
      try {
        const response = await axios.get(`${API_BASE}/knowledge/${item.id}`);
        const knowledge = response.data;

        this.formData = {
          title: knowledge.title || knowledge.question_summary || '',
          category: knowledge.category || '',
          audience: knowledge.audience || '',
          content: knowledge.content || '',
          keywords: knowledge.keywords || [],
          question_summary: knowledge.question_summary || '',
          intent_mappings: knowledge.intent_mappings || [],
          business_types: knowledge.business_types || []
        };

        this.keywordsString = (knowledge.keywords || []).join(', ');

        // 設定已選擇的意圖和類型
        this.selectedIntents = (knowledge.intent_mappings || []).map(m => m.intent_id);
        this.intentTypes = {};
        (knowledge.intent_mappings || []).forEach(m => {
          this.intentTypes[m.intent_id] = m.intent_type;
        });

        // 設定已選擇的業態類型
        this.selectedBusinessTypes = knowledge.business_types || [];

        console.log('📖 載入的知識資料:', {
          id: knowledge.id,
          title: knowledge.title,
          business_types: knowledge.business_types,
          selectedBusinessTypes: this.selectedBusinessTypes
        });

        // 更新 audience 提示
        this.onAudienceChange();

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

        console.log('📝 準備儲存的資料:', {
          title: this.formData.title,
          business_types: this.formData.business_types,
          selectedBusinessTypes: this.selectedBusinessTypes
        });

        if (this.editingItem) {
          // 更新
          await axios.put(
            `${API_BASE}/knowledge/${this.editingItem.id}`,
            this.formData
          );
          alert('✅ 知識已更新，向量已重新生成！');
        } else {
          // 新增
          await axios.post(`${API_BASE}/knowledge`, this.formData);
          alert('✅ 知識已新增！');
        }

        this.closeModal();
        this.loadKnowledge();
        this.loadStats();
      } catch (error) {
        console.error('儲存失敗', error);
        alert('儲存失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.saving = false;
      }
    },

    async deleteKnowledge(id) {
      if (!confirm('確定要刪除這筆知識嗎？刪除後無法復原。')) return;

      try {
        await axios.delete(`${API_BASE}/knowledge/${id}`);
        alert('✅ 已刪除');
        this.loadKnowledge();
        this.loadStats();
      } catch (error) {
        console.error('刪除失敗', error);
        alert('刪除失敗：' + (error.response?.data?.detail || error.message));
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
      // 清除 URL 參數
      window.history.replaceState({}, document.title, window.location.pathname + window.location.hash.split('?')[0]);
      this.loadKnowledge();
    }
  }
};
</script>

<style scoped>
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
  background: #f56c6c;
  color: white;
  border: none;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  transition: all 0.3s;
}

.btn-clear-search:hover {
  background: #f78989;
  transform: translateY(-50%) scale(1.1);
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

/* Audience 提示樣式 */
.audience-hint {
  display: block;
  margin-top: 6px;
  color: #409EFF;
  font-size: 12px;
  line-height: 1.5;
  font-style: italic;
  padding: 6px 10px;
  background: #ecf5ff;
  border-radius: 4px;
  border-left: 3px solid #409EFF;
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
</style>
