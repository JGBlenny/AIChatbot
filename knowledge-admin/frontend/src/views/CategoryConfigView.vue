<template>
  <div class="category-config-view">
    <h2>📂 分類配置管理</h2>

    <!-- 說明區塊 -->
    <InfoPanel :config="helpTexts.categories" />

    <div class="toolbar">
      <button @click="showAddModal" class="btn-primary btn-sm">
        新增分類
      </button>
    </div>

    <div v-if="loading" class="loading">載入中...</div>

    <div v-else class="category-list">
      <table>
      <thead>
        <tr>
          <th width="60">排序</th>
          <th width="150">分類名稱</th>
          <th>說明</th>
          <th width="100">使用次數</th>
          <th width="80">狀態</th>
          <th width="200">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="cat in categories" :key="cat.id" :class="{ inactive: !cat.is_active }">
          <td class="text-center">{{ cat.display_order }}</td>
          <td>
            <strong>{{ cat.display_name }}</strong>
            <div class="category-value">{{ cat.category_value }}</div>
          </td>
          <td class="description">{{ cat.description || '-' }}</td>
          <td class="text-center">
            <span class="badge badge-count">{{ cat.usage_count }}</span>
          </td>
          <td class="text-center">
            <span :class="['badge', cat.is_active ? 'badge-active' : 'badge-inactive']">
              {{ cat.is_active ? '啟用' : '停用' }}
            </span>
          </td>
          <td>
            <button @click="editCategory(cat)" class="btn-edit btn-sm">編輯</button>
            <button
              @click="deleteCategory(cat)"
              class="btn-danger btn-sm"
              :disabled="cat.usage_count > 0 && cat.is_active"
              :title="cat.usage_count > 0 ? '有知識使用中，只能停用' : '刪除分類'"
            >
              {{ cat.usage_count > 0 ? '停用' : '刪除' }}
            </button>
          </td>
        </tr>
      </tbody>
      </table>
    </div>

    <div v-if="!loading && categories.length === 0" class="empty-state">
      <p>暫無分類配置</p>
    </div>

    <!-- 新增/編輯 Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content category-modal">
        <div class="modal-header">
          <h3>{{ editingCategory ? '編輯分類' : '新增分類' }}</h3>
          <button @click="closeModal" class="btn-close">✕</button>
        </div>

        <div class="modal-body">
          <div class="form-group">
            <label>分類代碼 *</label>
            <input
              v-model="formData.category_value"
              :disabled="!!editingCategory"
              placeholder="例如：合約問題"
              required
              class="form-control"
            />
            <small v-if="editingCategory" class="hint">分類代碼建立後不可修改</small>
          </div>

          <div class="form-group">
            <label>顯示名稱 *</label>
            <input
              v-model="formData.display_name"
              placeholder="例如：合約問題"
              required
              class="form-control"
            />
          </div>

          <div class="form-group">
            <label>說明</label>
            <textarea
              v-model="formData.description"
              rows="3"
              placeholder="描述此分類的用途和範圍..."
              class="form-control"
            ></textarea>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>顯示順序</label>
              <input
                v-model.number="formData.display_order"
                type="number"
                min="0"
                placeholder="0"
                class="form-control"
              />
              <small class="hint">數字越小越靠前</small>
            </div>
          </div>

          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="formData.is_active" />
              <span>啟用此分類</span>
            </label>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeModal" class="btn-secondary btn-sm">取消</button>
          <button @click="saveCategory" class="btn-primary btn-sm" :disabled="saving">
            {{ saving ? '儲存中...' : '儲存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import InfoPanel from '@/components/InfoPanel.vue';
import helpTexts from '@/config/help-texts.js';

const API_BASE = '/api';

export default {
  name: 'CategoryConfigView',
  components: {
    InfoPanel
  },
  data() {
    return {
      helpTexts,
      categories: [],
      showModal: false,
      editingCategory: null,
      saving: false,
      loading: false,
      formData: {
        category_value: '',
        display_name: '',
        description: '',
        display_order: 0,
        is_active: true
      }
    };
  },
  async mounted() {
    await this.loadCategories();
  },
  methods: {
    async loadCategories() {
      this.loading = true;
      try {
        const response = await axios.get(`${API_BASE}/category-config`);
        this.categories = response.data.categories || [];
      } catch (error) {
        console.error('載入分類失敗', error);
        alert('載入分類失敗: ' + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },

    showAddModal() {
      this.editingCategory = null;
      this.formData = {
        category_value: '',
        display_name: '',
        description: '',
        display_order: this.categories.length + 1,
        is_active: true
      };
      this.showModal = true;
    },

    editCategory(cat) {
      this.editingCategory = cat;
      this.formData = {
        category_value: cat.category_value,
        display_name: cat.display_name,
        description: cat.description || '',
        display_order: cat.display_order,
        is_active: cat.is_active
      };
      this.showModal = true;
    },

    closeModal() {
      this.showModal = false;
      this.editingCategory = null;
    },

    async saveCategory() {
      // 驗證
      if (!this.formData.category_value || !this.formData.display_name) {
        alert('請填寫必填欄位');
        return;
      }

      this.saving = true;
      try {
        if (this.editingCategory) {
          // 更新
          await axios.put(
            `${API_BASE}/category-config/${this.editingCategory.id}`,
            this.formData
          );
          alert('分類已更新');
        } else {
          // 新增
          await axios.post(`${API_BASE}/category-config`, this.formData);
          alert('分類已新增');
        }

        this.closeModal();
        await this.loadCategories();
      } catch (error) {
        console.error('儲存失敗', error);
        alert('儲存失敗: ' + (error.response?.data?.detail || error.message));
      } finally {
        this.saving = false;
      }
    },

    async deleteCategory(cat) {
      const action = cat.usage_count > 0 ? '停用' : '刪除';
      const message = cat.usage_count > 0
        ? `確定要停用「${cat.display_name}」嗎？\n（有 ${cat.usage_count} 筆知識使用中）`
        : `確定要刪除「${cat.display_name}」嗎？`;

      if (!confirm(message)) return;

      try {
        const response = await axios.delete(`${API_BASE}/category-config/${cat.id}`);
        alert(response.data.message);
        await this.loadCategories();
      } catch (error) {
        console.error('操作失敗', error);
        alert('操作失敗: ' + (error.response?.data?.detail || error.message));
      }
    }
  }
};
</script>

<style scoped>
.category-config-view {
  /* padding 由 app-main 統一管理 */
}

/* 分類列表 */
.category-list table {
  width: 100%;
  background: white;
}

.category-list th {
  padding: 16px 20px;
  white-space: nowrap;
}

.category-list td {
  padding: 16px 20px;
  vertical-align: middle;
}

.category-list td strong {
  font-size: 14px;
  color: #2c3e50;
}

.category-value {
  font-size: 12px;
  color: #7f8c8d;
  margin-top: 4px;
}

.description {
  max-width: 400px;
  color: #7f8c8d;
}
</style>
