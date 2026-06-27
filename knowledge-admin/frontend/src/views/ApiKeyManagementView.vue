<template>
  <div class="api-key-view">
    <div class="page-header">
      <div>
        <h2>API 金鑰管理</h2>
        <p class="subtitle">服務對服務金鑰（rag 驗證用）。只存雜湊，明文僅建立時顯示一次。</p>
      </div>
      <button @click="openCreate" class="btn-primary">新增金鑰</button>
    </div>

    <table class="key-table">
      <thead>
        <tr>
          <th>名稱</th>
          <th>金鑰前綴</th>
          <th>說明</th>
          <th width="90">狀態</th>
          <th width="160">最後使用</th>
          <th width="160">建立時間</th>
          <th width="140">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="k in keys" :key="k.id" :class="{ inactive: !k.is_active }">
          <td>{{ k.name }}</td>
          <td><code>{{ k.key_prefix }}…</code></td>
          <td>{{ k.description || '-' }}</td>
          <td>
            <span :class="['badge', k.is_active ? 'badge-active' : 'badge-inactive']">
              {{ k.is_active ? '啟用' : '停用' }}
            </span>
          </td>
          <td>{{ fmt(k.last_used_at) }}</td>
          <td>{{ fmt(k.created_at) }}</td>
          <td>
            <button @click="toggle(k)" class="btn-sm">{{ k.is_active ? '停用' : '啟用' }}</button>
            <button @click="remove(k)" class="btn-sm btn-danger">刪除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="keys.length === 0" class="empty">尚無 API 金鑰，點「新增金鑰」建立。</p>

    <!-- 新增 Modal -->
    <div v-if="showCreate" class="modal-overlay" @click.self="closeCreate">
      <div class="modal">
        <h3>新增 API 金鑰</h3>
        <div class="form-group">
          <label>名稱（哪個系統用，如 A / B / C）</label>
          <input v-model="form.name" placeholder="例：JGB 平台後端" />
        </div>
        <div class="form-group">
          <label>說明（選填）</label>
          <input v-model="form.description" placeholder="用途備註" />
        </div>
        <div class="modal-actions">
          <button @click="closeCreate" class="btn-cancel">取消</button>
          <button @click="create" class="btn-primary" :disabled="saving">{{ saving ? '建立中...' : '建立' }}</button>
        </div>
      </div>
    </div>

    <!-- 明文金鑰顯示（只一次）Modal -->
    <div v-if="newKey" class="modal-overlay" @click.self="newKey = null">
      <div class="modal">
        <h3>🔑 金鑰已建立</h3>
        <p class="warn">⚠️ 這是「{{ newKey.name }}」的完整金鑰，<b>只顯示這一次</b>，關閉後無法再查看。請立即複製保存。</p>
        <div class="key-box">
          <code>{{ newKey.api_key }}</code>
          <button @click="copyKey" class="btn-sm">{{ copied ? '已複製 ✓' : '複製' }}</button>
        </div>
        <p class="hint">使用方式：呼叫 rag 時帶 Header <code>X-API-Key: {{ newKey.key_prefix }}…</code></p>
        <div class="modal-actions">
          <button @click="newKey = null" class="btn-primary">我已保存,關閉</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
const API_BASE = '/api';

export default {
  name: 'ApiKeyManagementView',
  data() {
    return {
      keys: [],
      showCreate: false,
      saving: false,
      form: { name: '', description: '' },
      newKey: null,
      copied: false
    };
  },
  async mounted() {
    await this.load();
  },
  methods: {
    fmt(ts) {
      if (!ts) return '—';
      return new Date(ts).toLocaleString('zh-TW', { hour12: false });
    },
    async load() {
      try {
        const res = await axios.get(`${API_BASE}/api-keys`);
        this.keys = res.data.api_keys || [];
      } catch (e) {
        console.error('載入金鑰失敗', e);
      }
    },
    openCreate() {
      this.form = { name: '', description: '' };
      this.showCreate = true;
    },
    closeCreate() {
      this.showCreate = false;
    },
    async create() {
      if (!this.form.name.trim()) return;
      this.saving = true;
      try {
        const res = await axios.post(`${API_BASE}/api-keys`, this.form);
        this.showCreate = false;
        this.newKey = res.data;
        this.copied = false;
        await this.load();
      } catch (e) {
        alert(e.response?.data?.detail || '建立失敗');
      } finally {
        this.saving = false;
      }
    },
    async toggle(k) {
      try {
        await axios.put(`${API_BASE}/api-keys/${k.id}`, { is_active: !k.is_active });
        await this.load();
      } catch (e) {
        alert(e.response?.data?.detail || '操作失敗');
      }
    },
    async remove(k) {
      if (!confirm(`確定刪除金鑰「${k.name}」？使用此金鑰的系統將立即無法存取。`)) return;
      try {
        await axios.delete(`${API_BASE}/api-keys/${k.id}`);
        await this.load();
      } catch (e) {
        alert(e.response?.data?.detail || '刪除失敗');
      }
    },
    async copyKey() {
      try {
        await navigator.clipboard.writeText(this.newKey.api_key);
        this.copied = true;
      } catch (e) {
        alert('複製失敗,請手動選取複製');
      }
    }
  }
};
</script>

<style scoped>
.api-key-view { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.subtitle { color: #8a94a6; font-size: 13px; margin: 4px 0 0; }
.key-table { width: 100%; border-collapse: collapse; }
.key-table th, .key-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; }
.key-table th { background: #f8f9fa; font-weight: 600; }
.key-table tr.inactive { opacity: 0.55; }
code { background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 13px; }
.badge { padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.badge-active { background: #d4edda; color: #155724; }
.badge-inactive { background: #f8d7da; color: #721c24; }
.btn-primary { background: #4a90d9; color: #fff; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; }
.btn-sm { padding: 4px 10px; border: 1px solid #ccc; background: #fff; border-radius: 3px; cursor: pointer; margin-right: 4px; }
.btn-danger { color: #e74c3c; border-color: #e74c3c; }
.btn-danger:hover { background: #e74c3c; color: #fff; }
.btn-cancel { padding: 8px 16px; border: 1px solid #ccc; background: #fff; border-radius: 4px; cursor: pointer; }
.empty { text-align: center; color: #999; padding: 40px; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #fff; padding: 24px; border-radius: 8px; width: 520px; max-width: 92vw; }
.modal h3 { margin-top: 0; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 4px; font-weight: 500; font-size: 14px; }
.form-group input { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }
.warn { background: #fff3cd; color: #856404; padding: 10px 12px; border-radius: 6px; font-size: 13px; }
.key-box { display: flex; align-items: center; gap: 8px; background: #f5f7fa; padding: 12px; border-radius: 6px; margin: 12px 0; }
.key-box code { flex: 1; word-break: break-all; background: none; }
.hint { font-size: 12px; color: #8a94a6; }
</style>
