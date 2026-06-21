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

        <datalist id="cc-categories">
          <option v-for="c in availableCategories" :key="c.category_value" :value="c.category_value">
            {{ c.category_label || c.category_value }}
          </option>
        </datalist>

        <label>標題（顯示用名稱）</label>
        <input v-model="form.label" placeholder="如：對話規則：售前顧問" />

        <label>角色 target_user（這套對話給哪個角色用）</label>
        <select v-model="form.target_user">
          <option v-for="r in roles" :key="r" :value="r">{{ r }}</option>
        </select>

        <label class="cc-check"><input type="checkbox" v-model="form.is_active" /> 此筆資料啟用（停用＝整筆忽略）</label>
        <label class="cc-check"><input type="checkbox" v-model="form.enabled" /> 對話模式啟用 enabled（關＝該角色不走對話）</label>

        <label>回答模式 answer_mode</label>
        <select v-model="form.answer_mode">
          <option value="conversational">conversational（多輪對話→收斂）</option>
          <option value="direct">direct（單次直答）</option>
        </select>

        <label>persona 規則文字（brain 的人格與行為規則，會餵給 LLM）</label>
        <textarea v-model="form.rules_text" rows="6" placeholder="例：你是…顧問。每輪先判斷…"></textarea>

        <hr/>
        <label>進入方式 trigger（這套對話什麼時候啟動）</label>
        <select v-model="form.trigger">
          <option value="freetext">自由問答：整角色打字就進（engine-first，如 prospect）</option>
          <option value="topic">主題命中：命中某分類/關鍵字的問題才進</option>
        </select>
        <template v-if="form.trigger==='topic'">
          <label class="cc-hint">主題分類（下拉既有或自行輸入；擇一）</label>
          <input v-model="form.topic_category" list="cc-categories" placeholder="如：退租結算" />
          <label class="cc-hint">或觸發關鍵字（逗號分隔；擇一）</label>
          <input v-model="form.topic_keywords" placeholder="如：退租,押金,結算" />
        </template>

        <hr/>
        <label>grounding 選材 grounding_scope.select（收斂時參考哪批知識）</label>
        <select v-model="form.g_select">
          <option value="vector">vector：語意檢索（廣主題，如 presales）</option>
          <option value="category">category：整批撈某分類（決定性，窄主題推薦）</option>
          <option value="ids">ids：明列知識 id（最決定性）</option>
        </select>
        <template v-if="form.g_select==='vector'">
          <label class="cc-hint">檢索知識角色：自動沿用上方「角色 = {{ form.target_user }}」（不需另設）</label>
          <label class="cc-hint">檢索 mode（b2b 業者/售前、b2c 租客）</label>
          <select v-model="form.g_mode"><option value="b2b">b2b</option><option value="b2c">b2c</option></select>
          <!-- vendor_id 僅 b2c 業者範圍知識才需要；prospect/b2b 系統知識不需 -->
          <template v-if="form.g_mode==='b2c'">
            <label class="cc-hint">vendor_id（b2c 限定某業者範圍時填，選填）</label>
            <input v-model="form.g_vendor_id" placeholder="某業者 id（選填）" />
          </template>
        </template>
        <template v-if="form.g_select==='category'">
          <label class="cc-hint">grounding 分類（整批撈此分類的知識）</label>
          <input v-model="form.g_category" list="cc-categories" placeholder="選擇或輸入，如：退租結算" />
        </template>
        <template v-if="form.g_select==='ids'">
          <label class="cc-hint">知識 id（逗號分隔）</label>
          <input v-model="form.g_ids" placeholder="如：3596,3597,3598" />
        </template>

        <hr/>
        <label>seed 起手主軸（選填）</label>
        <input v-model="form.seed" placeholder="選填" />

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
    return { items: [], editing: null, roles: ['prospect','tenant','landlord','property_manager','system_admin'],
      availableCategories: [], form: {} };
  },
  mounted() { this.load(); this.loadCategories(); },
  methods: {
    async loadCategories() {
      try {
        const r = await axios.get('/api/category-config');
        this.availableCategories = (r.data.categories || []).filter(c => c.is_active !== false);
      } catch (e) { /* 分類載入失敗不阻斷，欄位仍可自行輸入 */ }
    },
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
        answer_mode: 'conversational', rules_text: '', trigger: 'freetext', topic_category: '', topic_keywords: '',
        g_select: 'vector', g_mode: 'b2b', g_vendor_id: '', g_category: '', g_ids: '', seed: '' };
      this.editing = true;
    },
    openEdit(c) {
      const cfg = c.config || {}, ts = cfg.topic_scope || {mode:'all'}, gs = cfg.grounding_scope || {};
      const trigger = (ts.mode === 'category' || ts.mode === 'keywords') ? 'topic' : 'freetext';
      this.form = {
        id: c.id, label: c.label, target_user: c.target_user, is_active: c.is_active,
        enabled: cfg.enabled !== false, answer_mode: cfg.answer_mode || 'conversational', rules_text: c.rules_text,
        trigger, topic_category: ts.category || '', topic_keywords: (ts.keywords||[]).join(','),
        g_select: gs.select || 'vector', g_mode: gs.mode || 'b2b',
        g_vendor_id: gs.vendor_id || '', g_category: gs.category || '', g_ids: (gs.kb_ids||[]).join(','),
        seed: cfg.seed || '' };
      this.editing = true;
    },
    buildConfig() {
      const f = this.form;
      let topic_scope = { mode: 'all' };
      if (f.trigger === 'topic') {
        topic_scope = f.topic_category ? { mode: 'category', category: f.topic_category }
          : { mode: 'keywords', keywords: f.topic_keywords.split(',').map(s=>s.trim()).filter(Boolean) };
      }
      let grounding_scope = {};
      if (f.g_select === 'category') grounding_scope = { select: 'category', category: f.g_category, target_user: f.target_user };
      else if (f.g_select === 'ids') grounding_scope = { select: 'ids', kb_ids: f.g_ids.split(',').map(s=>parseInt(s.trim())).filter(n=>!isNaN(n)) };
      else { grounding_scope = { select: 'vector', target_user: f.target_user, mode: f.g_mode }; if (f.g_mode === 'b2c' && f.g_vendor_id) grounding_scope.vendor_id = parseInt(f.g_vendor_id); }
      const cfg = { key: f.target_user, answer_mode: f.answer_mode, topic_scope, grounding_scope, enabled: f.enabled };
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
.cc-modal label.cc-hint { font-weight: 400; font-size: 12px; color: #777; margin: 8px 0 3px; }
.cc-modal label.cc-check { font-weight: 400; }
.cc-modal hr { border: none; border-top: 1px solid #eee; margin: 16px 0 4px; }
.cc-modal input, .cc-modal select, .cc-modal textarea { width: 100%; padding: 7px 9px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
.cc-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 18px; }
</style>
