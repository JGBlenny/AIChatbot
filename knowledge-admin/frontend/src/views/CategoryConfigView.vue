<template>
  <div class="category-config-view">
    <div class="page-header">
      <h2>類別設定</h2>
      <button @click="openCreate" class="btn-primary">新增類別</button>
    </div>

    <div class="cat-groups">
      <!-- 父層群組卡片 -->
      <div
        v-for="g in groupedView.groups"
        :key="g.parent.id"
        class="group-card"
        :class="{ inactive: !g.parent.is_active }"
      >
        <div class="group-header">
          <div class="group-title">
            <span class="group-name">{{ g.parent.display_name }}</span>
            <span class="group-count">·共 {{ g.parent.usage_count || 0 }} 筆</span>
            <span v-if="!g.parent.is_active" class="badge badge-inactive">停用</span>
          </div>
          <div class="group-actions">
            <button @click="editCategory(g.parent)" class="btn-sm">編輯</button>
            <button @click="addChild(g.parent)" class="btn-sm btn-add">＋子類</button>
          </div>
        </div>
        <div class="group-children">
          <button
            v-for="c in g.children"
            :key="c.id"
            class="cat-chip"
            :class="{ inactive: !c.is_active }"
            :title="'編輯 ' + c.display_name + (c.is_active ? '' : '（已停用）')"
            @click="editCategory(c)"
          >
            {{ stripParentPrefix(c.display_name, g.parent.category_value) }}
            <span class="chip-count">·{{ c.usage_count || 0 }}</span>
          </button>
          <span v-if="g.children.length === 0" class="chip-empty">尚無子分類，點「＋子類」新增</span>
        </div>
      </div>

      <!-- 未分組（頂層葉子）-->
      <div class="group-card ungrouped" v-if="groupedView.ungrouped.length">
        <div class="group-header">
          <div class="group-title">
            <span class="group-name">未分組（頂層）</span>
            <span class="group-count">·{{ groupedView.ungrouped.length }} 項</span>
          </div>
        </div>
        <div class="group-children">
          <button
            v-for="c in groupedView.ungrouped"
            :key="c.id"
            class="cat-chip"
            :class="{ inactive: !c.is_active }"
            :title="'編輯 ' + c.display_name + (c.is_active ? '' : '（已停用）')"
            @click="editCategory(c)"
          >
            {{ c.display_name }}<span class="chip-count">·{{ c.usage_count || 0 }}</span>
          </button>
        </div>
      </div>

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
          <label>父層分類（兩層分類；留空＝頂層）</label>
          <select v-model="form.parent_value" :disabled="editingHasChildren">
            <option :value="null">（無，頂層）</option>
            <option
              v-for="p in parentOptions"
              :key="p.id"
              :value="p.category_value"
              :disabled="editingItem && p.category_value === editingItem.category_value"
            >
              {{ p.display_name }}
            </option>
          </select>
          <p v-if="editingHasChildren" class="parent-hint">此分類底下已有子分類，無法再設父層（維持兩層）。</p>
        </div>
        <div class="form-group">
          <label>說明</label>
          <input v-model="form.description" placeholder="選填" />
        </div>
        <div class="form-group">
          <label>排序 (數字越小越前)</label>
          <input v-model.number="form.display_order" type="number" />
        </div>
        <div class="form-group">
          <label class="inline-check"><input type="checkbox" v-model="form.is_active" /> 啟用（取消＝停用，從下拉/篩選隱藏）</label>
        </div>
        <div class="modal-actions">
          <button v-if="editingItem" @click="deleteCategory" class="btn-danger">刪除</button>
          <span class="modal-spacer"></span>
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
        display_order: 0,
        parent_value: null,
        is_active: true
      }
    };
  },
  computed: {
    // 群組卡片視圖：父層群組 + 未分組頂層
    groupedView() {
      const cats = this.categories;
      const parentVals = new Set(cats.filter(c => c.parent_value).map(c => c.parent_value));
      const groups = cats
        .filter(c => parentVals.has(c.category_value))
        .map(p => ({ parent: p, children: cats.filter(c => c.parent_value === p.category_value) }));
      const ungrouped = cats.filter(c => !c.parent_value && !parentVals.has(c.category_value));
      return { groups, ungrouped };
    },
    // 可當父層的選項（頂層列）
    parentOptions() {
      return this.categories.filter(c => !c.parent_value);
    },
    // 編輯中的分類本身是否已有子分類（有→不能再設父層，維持兩層）
    editingHasChildren() {
      if (!this.editingItem) return false;
      return this.categories.some(c => c.parent_value === this.editingItem.category_value);
    }
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
        display_order: cat.display_order || 0,
        parent_value: cat.parent_value || null,
        is_active: cat.is_active !== false
      };
    },
    openCreate() {
      this.editingItem = null;
      this.form = { category_value: '', display_name: '', description: '', display_order: 0, parent_value: null, is_active: true };
      this.showCreateModal = true;
    },
    addChild(parent) {
      this.editingItem = null;
      this.form = { category_value: '', display_name: '', description: '', display_order: 100, parent_value: parent.category_value, is_active: true };
      this.showCreateModal = true;
    },
    // 子類顯示去掉父層前綴：售前競品→競品
    stripParentPrefix(value, parent) {
      if (!parent || !value.startsWith(parent)) return value;
      const rest = value.slice(parent.length).replace(/^[\s:：_\-／/]+/, '');
      return rest || value;
    },
    closeModal() {
      this.showCreateModal = false;
      this.editingItem = null;
      this.form = { category_value: '', display_name: '', description: '', display_order: 0, parent_value: null, is_active: true };
    },
    async saveCategory() {
      if (!this.form.category_value || !this.form.display_name) return;
      this.saving = true;
      const editing = this.editingItem;
      try {
        if (editing) {
          await axios.put(`${API_BASE}/category-config/${editing.id}`, this.form);
          // 停用連動清理：剛由啟用→停用、且仍有知識在用 → 問是否一併移除
          const justDeactivated = (editing.is_active !== false) && !this.form.is_active;
          const usage = editing.usage_count || 0;
          if (justDeactivated && usage > 0 &&
              confirm(`已停用「${editing.display_name}」。\n仍有 ${usage} 筆知識掛著此分類，要一併從知識移除嗎？`)) {
            await axios.post(`${API_BASE}/category-config/${editing.id}/remove-from-knowledge`);
          }
        } else {
          await axios.post(`${API_BASE}/category-config`, { ...this.form, is_active: true });
        }
        this.closeModal();
        await this.loadCategories();
      } catch (e) {
        alert(e.response?.data?.detail || '儲存失敗');
      } finally {
        this.saving = false;
      }
    },
    async deleteCategory() {
      const cat = this.editingItem;
      if (!cat) return;
      if (this.categories.some(c => c.parent_value === cat.category_value)) {
        alert('此分類底下有子分類，請先移除或改掛子分類後再刪除。');
        return;
      }
      const usage = cat.usage_count || 0;
      if (usage > 0) {
        if (!confirm(`「${cat.display_name}」有 ${usage} 筆知識使用。\n\n確定＝從這些知識一併移除此分類，再刪除分類。\n取消＝不動作。`)) return;
        try {
          await axios.post(`${API_BASE}/category-config/${cat.id}/remove-from-knowledge`);
        } catch (e) {
          alert(e.response?.data?.detail || '移除失敗'); return;
        }
      } else if (!confirm(`確定刪除「${cat.display_name}」？`)) {
        return;
      }
      try {
        await axios.delete(`${API_BASE}/category-config/${cat.id}`);
        this.closeModal();
        await this.loadCategories();
      } catch (e) {
        alert(e.response?.data?.detail || '刪除失敗');
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
.parent-hint { margin: 6px 0 0; font-size: 12px; color: #b8860b; }

/* 群組卡片 */
.cat-groups { display: flex; flex-direction: column; gap: 14px; }
.group-card {
  border: 1px solid #e3e8ef;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  overflow: hidden;
}
.group-card.inactive { opacity: 0.6; }
.group-card.ungrouped { border-style: dashed; background: #fcfcfd; }
.group-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
  background: linear-gradient(0deg, #f7f9fc, #fbfcfe);
  border-bottom: 1px solid #eef1f5;
}
.group-title { display: flex; align-items: center; gap: 8px; }
.group-name { font-size: 15px; font-weight: 700; color: #2c3e50; }
.group-count { font-size: 12px; color: #8a94a6; }
.group-actions { display: flex; gap: 6px; }
.group-children {
  display: flex; flex-wrap: wrap; gap: 8px;
  padding: 14px 16px;
}
.cat-chip {
  display: inline-flex; align-items: center; gap: 2px;
  padding: 6px 12px;
  border: 1px solid #d6dee9;
  background: #f2f6fc;
  color: #2c3e50;
  border-radius: 16px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.12s;
}
.cat-chip:hover { background: #e1ecfb; border-color: #4a90d9; }
.cat-chip.inactive { background: #f3f4f6; color: #9aa0aa; border-style: dashed; }
.chip-count { font-size: 11px; color: #8a94a6; }
.chip-empty { font-size: 12px; color: #aab; font-style: italic; }
.btn-add { color: #fff; background: #4a90d9; border-color: #4a90d9; }
.btn-add:hover { background: #357abd; }
.inline-check { display: flex; align-items: center; gap: 6px; font-weight: 500; cursor: pointer; }
.modal-spacer { flex: 1; }
.btn-danger { padding: 8px 16px; border: 1px solid #e74c3c; background: #fff; color: #e74c3c; border-radius: 4px; cursor: pointer; }
.btn-danger:hover { background: #e74c3c; color: #fff; }
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
