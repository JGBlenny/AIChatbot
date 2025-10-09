<template>
  <div id="app">
    <h1>📚 知識庫管理系統</h1>

    <!-- 工具列 -->
    <div class="toolbar">
      <input
        v-model="searchQuery"
        placeholder="🔍 搜尋知識..."
        @input="searchKnowledge"
      />
      <select v-model="selectedCategory" @change="loadKnowledge">
        <option value="">全部分類</option>
        <option v-for="cat in categories" :key="cat">{{ cat }}</option>
      </select>
      <button @click="showCreateModal" class="btn-primary">
        ➕ 新增知識
      </button>
    </div>

    <!-- 統計資訊 -->
    <div v-if="stats" style="margin-bottom: 20px; color: #606266;">
      總計 {{ stats.total_knowledge }} 筆知識
    </div>

    <!-- 知識列表 -->
    <div v-if="loading" class="loading">
      <p>載入中...</p>
    </div>

    <div v-else-if="knowledgeList.length === 0" class="empty-state">
      <p>沒有找到知識</p>
      <button @click="showCreateModal" class="btn-primary" style="margin-top: 20px;">
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
            <th width="100">對象</th>
            <th width="180">更新時間</th>
            <th width="150">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in knowledgeList" :key="item.id">
            <td>{{ item.id }}</td>
            <td>{{ item.title || item.question_summary || '(無標題)' }}</td>
            <td><span class="badge">{{ item.category }}</span></td>
            <td>{{ item.audience }}</td>
            <td>{{ formatDate(item.updated_at) }}</td>
            <td>
              <button @click="editKnowledge(item)" class="btn-edit">
                ✏️ 編輯
              </button>
              <button @click="deleteKnowledge(item.id)" class="btn-delete">
                🗑️
              </button>
            </td>
          </tr>
        </tbody>
      </table>
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
                <option>帳務問題</option>
                <option>合約問題</option>
                <option>物件問題</option>
                <option>帳號問題</option>
                <option>IOT設備問題</option>
                <option>操作問題</option>
                <option>其他</option>
              </select>
            </div>

            <div class="form-group">
              <label>對象 *</label>
              <select v-model="formData.audience" required>
                <option value="">請選擇</option>
                <option>房東</option>
                <option>租客</option>
                <option>管理師</option>
                <option>業者</option>
                <option>全部</option>
              </select>
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
            <button type="submit" class="btn-primary" :disabled="saving">
              {{ saving ? '⏳ 儲存中...' : '💾 儲存並更新向量' }}
            </button>
            <button type="button" @click="closeModal" class="btn-secondary">
              ❌ 取消
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
  name: 'App',
  data() {
    return {
      knowledgeList: [],
      categories: [],
      searchQuery: '',
      selectedCategory: '',
      showModal: false,
      editingItem: null,
      saving: false,
      loading: false,
      stats: null,
      formData: {
        title: '',
        category: '',
        audience: '',
        content: '',
        keywords: [],
        question_summary: ''
      },
      keywordsString: '',
      searchTimeout: null
    };
  },
  computed: {
    markdownPreview() {
      if (!this.formData.content) {
        return '<p style="color: #999;">Markdown 預覽區</p>';
      }
      return marked(this.formData.content);
    }
  },
  mounted() {
    this.loadKnowledge();
    this.loadCategories();
    this.loadStats();
  },
  methods: {
    async loadKnowledge() {
      this.loading = true;
      try {
        const params = {};
        if (this.selectedCategory) params.category = this.selectedCategory;
        if (this.searchQuery) params.search = this.searchQuery;

        const response = await axios.get(`${API_BASE}/knowledge`, { params });
        this.knowledgeList = response.data.items;
      } catch (error) {
        console.error('載入失敗', error);
        alert('載入失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },

    async loadCategories() {
      try {
        const response = await axios.get(`${API_BASE}/categories`);
        this.categories = response.data.categories;
      } catch (error) {
        console.error('載入分類失敗', error);
      }
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
        question_summary: ''
      };
      this.keywordsString = '';
      this.showModal = true;
    },

    editKnowledge(item) {
      this.editingItem = item;
      this.formData = {
        title: item.title || item.question_summary || '',
        category: item.category || '',
        audience: item.audience || '',
        content: item.content || '',
        keywords: item.keywords || [],
        question_summary: item.question_summary || ''
      };
      this.keywordsString = (item.keywords || []).join(', ');
      this.showModal = true;
    },

    async saveKnowledge() {
      this.saving = true;

      try {
        // 處理關鍵字
        this.formData.keywords = this.keywordsString
          .split(',')
          .map(k => k.trim())
          .filter(k => k);

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
    }
  }
};
</script>
