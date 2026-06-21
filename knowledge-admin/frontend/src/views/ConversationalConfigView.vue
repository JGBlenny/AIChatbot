<template>
  <div class="cc-page">
    <div class="cc-header">
      <h2>💬 對話式回答設定</h2>
      <p class="cc-sub">管理哪些角色／主題走「多輪對話→收斂」模式（資料驅動，存檔即時生效）。</p>
      <button class="btn btn-primary" @click="openNew">＋ 新增設定</button>
    </div>

    <table class="cc-table">
      <thead>
        <tr>
          <th>角色</th><th>標題</th><th>模式</th><th>主題範圍</th><th>grounding</th><th>啟用</th><th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in items" :key="c.id">
          <td>{{ c.target_user }}</td>
          <td>{{ c.label }}</td>
          <td>{{ c.config.answer_mode || 'conversational' }}</td>
          <td>{{ topicLabel(c.config.topic_scope) }}</td>
          <td>{{ (c.config.grounding_scope && c.config.grounding_scope.select) || 'vector' }}</td>
          <td>{{ (c.config.enabled !== false) ? '✅' : '⛔' }}</td>
          <td>
            <button class="btn-link" @click="openEdit(c)">編輯</button>
            <button class="btn-link danger" @click="remove(c)">刪除</button>
          </td>
        </tr>
        <tr v-if="!items.length"><td colspan="7" class="empty">尚無設定</td></tr>
      </tbody>
    </table>

    <!-- 編輯彈窗 -->
    <div v-if="editing" class="cc-modal-mask" @click.self="editing=null">
      <div class="cc-modal">
        <h3>{{ form.id ? '編輯設定' : '新增設定' }}</h3>

        <label>標題</label>
        <input v-model="form.label" placeholder="如：對話規則：售前顧問" />

        <label>角色 (target_user)</label>
        <select v-model="form.target_user">
          <option v-for="r in roles" :key="r" :value="r">{{ r }}</option>
        </select>

        <label><input type="checkbox" v-model="form.is_active" /> 此筆資料啟用</label>
        <label><input type="checkbox" v-model="form.enabled" /> 對話模式啟用 (enabled)</label>

        <label>回答模式 (answer_mode)</label>
        <select v-model="form.answer_mode">
          <option value="conversational">conversational（多輪對話）</option>
          <option value="direct">direct（單次直答）</option>
        </select>

        <label>persona 規則文字</label>
        <textarea v-model="form.rules_text" rows="6" placeholder="brain 的人格與規則…"></textarea>

        <label>主題範圍 (topic_scope)</label>
        <select v-model="form.topic_mode">
          <option value="all">all（整角色都對話，如 prospect）</option>
          <option value="category">category（只有該分類問題才進）</option>
          <option value="keywords">keywords（關鍵字命中才進）</option>
        </select>
        <input v-if="form.topic_mode==='category'" v-model="form.topic_category" placeholder="主題分類，如：退租結算" />
        <input v-if="form.topic_mode==='keywords'" v-model="form.topic_keywords" placeholder="關鍵字，逗號分隔" />

        <label>grounding 選材 (grounding_scope.select)</label>
        <select v-model="form.g_select">
          <option value="vector">vector（語意檢索，廣主題）</option>
          <option value="category">category（整批撈某分類，決定性，窄主題）</option>
          <option value="ids">ids（明列知識 id，最決定性）</option>
        </select>
        <template v-if="form.g_select==='vector'">
          <input v-model="form.g_target_user" placeholder="grounding target_user，如 prospect" />
          <select v-model="form.g_mode"><option value="b2b">b2b</option><option value="b2c">b2c</option></select>
          <input v-model="form.g_vendor_id" placeholder="vendor_id（選填，預設 1）" />
        </template>
        <input v-if="form.g_select==='category'" v-model="form.g_category" placeholder="grounding 分類，如：退租結算" />
        <input v-if="form.g_select==='ids'" v-model="form.g_ids" placeholder="知識 id，逗號分隔，如 3596,3597" />

        <label>入口 (entry，選填)：選單 form_id</label>
        <input v-model="form.entry_form_id" placeholder="如：presales_entry（無則留空）" />
        <input v-model="form.entry_values" placeholder="入口選項 value，逗號分隔，如 fit,pain" />

        <label>seed（選填）</label>
        <input v-model="form.seed" placeholder="起手主軸（選填）" />

        <div class="cc-actions">
          <button class="btn" @click="editing=null">取消</button>
          <button class="btn btn-primary" @click="save">儲存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
const RAG_API = '/rag-api/v1';

export default {
  name: 'ConversationalConfigView',
  data() {
    return { items: [], editing: null, roles: ['prospect','tenant','landlord','property_manager','system_admin'], form: {} };
  },
  mounted() { this.load(); },
  methods: {
    topicLabel(ts) {
      if (!ts || ts.mode === 'all' || !ts.mode) return 'all';
      return ts.mode === 'category' ? `category:${ts.category||''}` : `keywords`;
    },
    async load() {
      try { this.items = (await axios.get(`${RAG_API}/conversational-configs`)).data; }
      catch (e) { alert('載入失敗：' + e); }
    },
    openNew() {
      this.form = { id: null, label: '', target_user: 'prospect', is_active: true, enabled: true,
        answer_mode: 'conversational', rules_text: '', topic_mode: 'all', topic_category: '', topic_keywords: '',
        g_select: 'vector', g_target_user: 'prospect', g_mode: 'b2b', g_vendor_id: '', g_category: '', g_ids: '',
        entry_form_id: '', entry_values: '', seed: '' };
      this.editing = true;
    },
    openEdit(c) {
      const cfg = c.config || {}, ts = cfg.topic_scope || {mode:'all'}, gs = cfg.grounding_scope || {};
      this.form = {
        id: c.id, label: c.label, target_user: c.target_user, is_active: c.is_active,
        enabled: cfg.enabled !== false, answer_mode: cfg.answer_mode || 'conversational', rules_text: c.rules_text,
        topic_mode: ts.mode || 'all', topic_category: ts.category || '', topic_keywords: (ts.keywords||[]).join(','),
        g_select: gs.select || 'vector', g_target_user: gs.target_user || '', g_mode: gs.mode || 'b2b',
        g_vendor_id: gs.vendor_id || '', g_category: gs.category || '', g_ids: (gs.kb_ids||[]).join(','),
        entry_form_id: (cfg.entry||{}).form_id || '', entry_values: ((cfg.entry||{}).option_values||[]).join(','),
        seed: cfg.seed || '' };
      this.editing = true;
    },
    buildConfig() {
      const f = this.form;
      const topic_scope = f.topic_mode === 'category' ? { mode: 'category', category: f.topic_category }
        : f.topic_mode === 'keywords' ? { mode: 'keywords', keywords: f.topic_keywords.split(',').map(s=>s.trim()).filter(Boolean) }
        : { mode: 'all' };
      let grounding_scope = {};
      if (f.g_select === 'category') grounding_scope = { select: 'category', category: f.g_category, target_user: f.target_user };
      else if (f.g_select === 'ids') grounding_scope = { select: 'ids', kb_ids: f.g_ids.split(',').map(s=>parseInt(s.trim())).filter(n=>!isNaN(n)) };
      else { grounding_scope = { select: 'vector', target_user: f.g_target_user || f.target_user, mode: f.g_mode }; if (f.g_vendor_id) grounding_scope.vendor_id = parseInt(f.g_vendor_id); }
      const cfg = { key: f.target_user, answer_mode: f.answer_mode, topic_scope, grounding_scope, enabled: f.enabled };
      if (f.entry_form_id) cfg.entry = { form_id: f.entry_form_id, option_values: f.entry_values.split(',').map(s=>s.trim()).filter(Boolean) };
      if (f.seed) cfg.seed = f.seed;
      return cfg;
    },
    async save() {
      const f = this.form;
      if (!f.label || !f.rules_text) { alert('標題與規則文字必填'); return; }
      try {
        await axios.post(`${RAG_API}/conversational-configs`, {
          id: f.id, label: f.label, target_user: f.target_user, rules_text: f.rules_text,
          is_active: f.is_active, config: this.buildConfig() });
        this.editing = null; this.load();
        alert('已儲存（新設定即時生效）');
      } catch (e) { alert('儲存失敗：' + (e.response?.data?.detail || e)); }
    },
    async remove(c) {
      if (!confirm(`刪除設定「${c.label}」？`)) return;
      try { await axios.delete(`${RAG_API}/conversational-configs/${c.id}`); this.load(); }
      catch (e) { alert('刪除失敗：' + e); }
    },
  },
};
</script>

<style scoped>
.cc-page { padding: 20px; max-width: 1000px; }
.cc-header { margin-bottom: 16px; }
.cc-sub { color: #666; font-size: 14px; margin: 4px 0 12px; }
.cc-table { width: 100%; border-collapse: collapse; }
.cc-table th, .cc-table td { border: 1px solid #e5e5e5; padding: 8px 10px; text-align: left; font-size: 14px; }
.cc-table th { background: #f7f7f7; }
.empty { text-align: center; color: #999; }
.btn { padding: 6px 14px; border: 1px solid #ccc; border-radius: 6px; background: #fff; cursor: pointer; }
.btn-primary { background: #2563eb; color: #fff; border-color: #2563eb; }
.btn-link { background: none; border: none; color: #2563eb; cursor: pointer; margin-right: 8px; }
.btn-link.danger { color: #dc2626; }
.cc-modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.cc-modal { background: #fff; border-radius: 10px; padding: 20px 24px; width: 560px; max-height: 88vh; overflow-y: auto; }
.cc-modal label { display: block; margin: 12px 0 4px; font-weight: 600; font-size: 13px; }
.cc-modal input, .cc-modal select, .cc-modal textarea { width: 100%; padding: 7px 9px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
.cc-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 18px; }
</style>
