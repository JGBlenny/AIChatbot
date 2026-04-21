<template>
  <div class="category-config-view">
    <div class="page-header">
      <h2>類別設定</h2>
      <button @click="showCreateModal = true" class="btn-primary">新增類別</button>
    </div>

    <div class="category-list">
      <table>
        <thead>
          <tr>
            <th width="60">排序</th>
            <th>類別值</th>
            <th>顯示名稱</th>
            <th>說明</th>
            <th width="80">使用數</th>
            <th width="80">狀態</th>
            <th width="120">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="cat in categories" :key="cat.id">
            <td>{{ cat.display_order }}</td>
            <td><code>{{ cat.category_value }}</code></td>
            <td>{{ cat.display_name }}</td>
            <td>{{ cat.description || '-' }}</td>
            <td>{{ cat.usage_count || 0 }}</td>
            <td>
              <span :class="['badge', cat.is_active ? 'badge-active' : 'badge-inactive']">
                {{ cat.is_active ? '啟用' : '停用' }}
              </span>
            </td>
            <td>
              <button @click="editCategory(cat)" class="btn-sm">編輯</button>
              <button @click="toggleActive(cat)" class="btn-sm btn-toggle">
                {{ cat.is_active ? '停用' : '啟用' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="categories.length === 0" class="empty">尚無類別設定</p>
    </div>

    <!-- 新增/編輯 Modal -->
    <div v-if="showCreateModal || editingItem" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <h3>{{ editingItem ? '編輯類別' : '新增類別' }}</h3>
        <div class="form-group">
          <label>類別值 (英文代碼)</label>
          <input v-model="form.category_value" :disabled="!!editingItem" placeholder="例：maintenance" />
        </div>
        <div class="form-group">
          <label>顯示名稱</label>
          <input v-model="form.display_name" placeholder="例：報修維護" />
        </div>
        <div class="form-group">
          <label>說明</label>
          <input v-model="form.description" placeholder="選填" />
        </div>
        <div class="form-group">
          <label>排序 (數字越小越前)</label>
          <input v-model.number="form.display_order" type="number" />
        </div>
        <div class="modal-actions">
          <button @click="closeModal" class="btn-cancel">取消</button>
          <button @click="saveCategory" class="btn-primary" :disabled="saving">
            {{ saving ? '儲存中...' : '儲存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

const API_BASE = '/api';

export default {
  name: 'CategoryConfigView',
  data() {
    return {
      categories: [],
      showCreateModal: false,
      editingItem: null,
      saving: false,
      form: {
        category_value: '',
        display_name: '',
        description: '',
        display_order: 0
      }
    };
  },
  async mounted() {
    await this.loadCategories();
  },
  methods: {
    async loadCategories() {
      try {
        const res = await axios.get(`${API_BASE}/category-config`);
        this.categories = res.data.categories || [];
      } catch (e) {
        console.error('載入類別失敗', e);
      }
    },
    editCategory(cat) {
      this.editingItem = cat;
      this.form = {
        category_value: cat.category_value,
        display_name: cat.display_name,
        description: cat.description || '',
        display_order: cat.display_order || 0
      };
    },
    closeModal() {
      this.showCreateModal = false;
      this.editingItem = null;
      this.form = { category_value: '', display_name: '', description: '', display_order: 0 };
    },
    async saveCategory() {
      if (!this.form.category_value || !this.form.display_name) return;
      this.saving = true;
      try {
        if (this.editingItem) {
          await axios.put(`${API_BASE}/category-config/${this.editingItem.id}`, this.form);
        } else {
          await axios.post(`${API_BASE}/category-config`, {
            ...this.form,
            is_active: true
          });
        }
        this.closeModal();
        await this.loadCategories();
      } catch (e) {
        alert(e.response?.data?.detail || '儲存失敗');
      } finally {
        this.saving = false;
      }
    },
    async toggleActive(cat) {
      try {
        await axios.put(`${API_BASE}/category-config/${cat.id}`, {
          ...cat,
          is_active: !cat.is_active
        });
        await this.loadCategories();
      } catch (e) {
        alert('操作失敗');
      }
    }
  }
};
</script>

<style scoped>
.category-config-view { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; }
th { background: #f8f9fa; font-weight: 600; }
code { background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 13px; }
.badge { padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.badge-active { background: #d4edda; color: #155724; }
.badge-inactive { background: #f8d7da; color: #721c24; }
.btn-primary { background: #4a90d9; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
.btn-primary:hover { background: #357abd; }
.btn-primary:disabled { opacity: 0.6; }
.btn-sm { padding: 4px 10px; border: 1px solid #ccc; background: white; border-radius: 3px; cursor: pointer; margin-right: 4px; }
.btn-sm:hover { background: #f0f0f0; }
.btn-toggle { color: #666; }
.empty { text-align: center; color: #999; padding: 40px; }
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: white; padding: 24px; border-radius: 8px; width: 450px; }
.modal h3 { margin-top: 0; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 4px; font-weight: 500; font-size: 14px; }
.form-group input { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }
.btn-cancel { padding: 8px 16px; border: 1px solid #ccc; background: white; border-radius: 4px; cursor: pointer; }
</style>
