<template>
  <div class="usage-stats-view">
    <!-- 頁首（沿全站 page-header 慣例） -->
    <div class="page-header">
      <h2>📈 使用量統計</h2>
      <div class="header-actions">
        <button class="btn btn-primary" @click="exportCsv">⬇ 匯出 CSV</button>
      </div>
    </div>
    <p class="page-hint">AI 客服使用頻率（未來計費依據）——各業者×使用者類型的訊息/對話/token 成本。內部流量（回測/迴圈）預設排除；「估算成本」為 LLM token 成本參考（USD），非對業者售價。</p>

    <!-- 篩選（沿 filter-section 慣例） -->
    <div class="filter-section">
      <div class="filter-group">
        <label>期間</label>
        <input type="date" v-model="dateFrom" @change="load" />
        <span class="tilde">～</span>
        <input type="date" v-model="dateTo" @change="load" />
      </div>
      <div class="filter-group">
        <label>業者</label>
        <select v-model="vendorId" @change="load">
          <option value="">全部</option>
          <option v-for="v in vendors" :key="v.id" :value="String(v.id)">{{ v.name || ('Vendor ' + v.id) }}</option>
        </select>
      </div>
      <div class="filter-group">
        <label>粒度</label>
        <select v-model="granularity" @change="load">
          <option value="day">日</option>
          <option value="month">月</option>
        </select>
      </div>
      <div class="filter-group checkbox-group">
        <label><input type="checkbox" v-model="includeInternal" @change="load" /> 含內部流量</label>
      </div>
    </div>

    <!-- 總計卡（沿 stats-grid/stat-card 慣例） -->
    <div v-if="totals" class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">💬</div>
        <div class="stat-content"><div class="stat-value">{{ fmt(totals.messages) }}</div><div class="stat-label">訊息數</div></div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">🗨️</div>
        <div class="stat-content"><div class="stat-value">{{ fmt(totals.sessions) }}</div><div class="stat-label">對話數</div></div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">🔤</div>
        <div class="stat-content"><div class="stat-value">{{ fmt(totals.prompt_tokens + totals.completion_tokens) }}</div><div class="stat-label">Tokens（p+c）</div></div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">💵</div>
        <div class="stat-content"><div class="stat-value">${{ totals.est_cost_usd }}</div><div class="stat-label">估算成本 USD</div></div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">⚠️</div>
        <div class="stat-content"><div class="stat-value">{{ totals.errors }}</div><div class="stat-label">失敗數</div></div>
      </div>
    </div>

    <!-- 業者排行 -->
    <div v-if="vendorRank.length" class="table-card">
      <h3>業者排行</h3>
      <table>
        <thead><tr><th>業者</th><th>訊息數</th><th>對話數</th><th>估算成本 USD</th></tr></thead>
        <tbody>
          <tr v-for="r in vendorRank" :key="r.vendor_id">
            <td class="question-cell">{{ vendorName(r.vendor_id) }}</td>
            <td>{{ fmt(r.messages) }}</td><td>{{ fmt(r.sessions) }}</td>
            <td>{{ r.cost != null ? '$' + r.cost.toFixed(4) : '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 明細 -->
    <div v-if="groups.length" class="table-card">
      <h3>明細（{{ granularity === 'day' ? '日' : '月' }} × 業者 × 使用者類型）</h3>
      <table>
        <thead><tr>
          <th>期間</th><th>業者</th><th>使用者類型</th><th>訊息數</th><th>對話數</th>
          <th>去重使用者</th><th>tokens (p/c)</th><th>成本 USD</th><th>失敗</th>
        </tr></thead>
        <tbody>
          <tr v-for="(g, i) in groups" :key="i" :class="{ 'row-internal': g.user_type === 'internal' }">
            <td>{{ g.bucket }}</td>
            <td>{{ vendorName(g.vendor_id) }}</td>
            <td><span class="badge" :class="typeBadge(g.user_type)">{{ typeLabel(g.user_type) }}</span></td>
            <td>{{ fmt(g.messages) }}</td><td>{{ fmt(g.sessions) }}</td><td>{{ g.distinct_users }}</td>
            <td>{{ fmt(g.prompt_tokens) }} / {{ fmt(g.completion_tokens) }}</td>
            <td>{{ g.est_cost_usd != null ? '$' + g.est_cost_usd.toFixed(4) : '—' }}</td>
            <td>{{ g.errors }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <!-- 使用者明細（2026-07-06 改判開放：user_id＝JGB 系統編號，jgb2 呼叫必帶） -->
    <div v-if="userRows.length" class="table-card">
      <h3>使用者明細（Top {{ userLimit }}，依訊息數）</h3>
      <table>
        <thead><tr>
          <th>JGB user_id</th><th>業者</th><th>類型</th><th>訊息數</th><th>對話數</th>
          <th>tokens (p/c)</th><th>成本 USD</th><th>最近使用</th>
        </tr></thead>
        <tbody>
          <tr v-for="(u, i) in userRows" :key="i">
            <td class="question-cell">{{ u.user_id }}</td>
            <td>{{ vendorName(u.vendor_id) }}</td>
            <td><span class="badge" :class="typeBadge(u.user_type)">{{ typeLabel(u.user_type) }}</span></td>
            <td>{{ fmt(u.messages) }}</td><td>{{ fmt(u.sessions) }}</td>
            <td>{{ fmt(u.prompt_tokens) }} / {{ fmt(u.completion_tokens) }}</td>
            <td>{{ u.est_cost_usd != null ? '$' + u.est_cost_usd.toFixed(4) : '—' }}</td>
            <td>{{ shortTs(u.last_seen) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 額度管理（quota-management）：三色進度條＋inline 設定 -->
    <div class="table-card">
      <h3>額度管理（月訊息額度）</h3>
      <table>
        <thead><tr>
          <th>業者</th><th style="width:34%">本月用量</th><th>額度</th><th>警示閾值</th>
          <th>達限攔截</th><th>狀態</th><th>操作</th>
        </tr></thead>
        <tbody>
          <tr v-for="q in quotaRows" :key="q.vendor_id">
            <td class="question-cell">{{ vendorName(q.vendor_id) }}</td>
            <td>
              <div class="q-bar"><div class="q-fill" :class="'q-' + q.state"
                   :style="{ width: Math.min(q.pct, 100) + '%' }"></div></div>
              <span class="q-text">{{ fmt(q.used_this_month) }} / {{ fmt(q.monthly_message_quota) }}（{{ q.pct }}%）</span>
            </td>
            <td>
              <input v-if="editing === q.vendor_id" type="number" v-model.number="editForm.monthly_message_quota" class="q-input" />
              <span v-else>{{ fmt(q.monthly_message_quota) }}</span>
            </td>
            <td>
              <input v-if="editing === q.vendor_id" type="number" v-model.number="editForm.warn_threshold_pct" class="q-input q-narrow" min="1" max="99" />
              <span v-else>{{ q.warn_threshold_pct }}%</span>
            </td>
            <td>
              <input v-if="editing === q.vendor_id" type="checkbox" v-model="editForm.block_on_exceed" />
              <span v-else>{{ q.block_on_exceed ? '✅ 攔截' : '🕊️ 寬限' }}</span>
            </td>
            <td>
              <span class="badge" :class="{'badge-tenant': q.state==='ok', 'badge-prospect': q.state==='warn',
                                           'badge-unknown': q.state==='blocked', 'badge-internal': q.state==='none'}">
                {{ {ok:'正常', warn:'警示', blocked:'已達限', none:'停用'}[q.state] }}
              </span>
            </td>
            <td>
              <template v-if="editing === q.vendor_id">
                <button class="btn-sm" @click="saveQuota(q.vendor_id)">儲存</button>
                <button class="btn-sm btn-plain" @click="editing = null">取消</button>
              </template>
              <template v-else>
                <button class="btn-sm" @click="startEdit(q)">編輯</button>
                <button v-if="q.is_active" class="btn-sm btn-plain" @click="deactivateQuota(q.vendor_id)">停用</button>
              </template>
            </td>
          </tr>
          <!-- 未管制業者：提供設定入口 -->
          <tr v-for="v in unmanagedVendors" :key="'u' + v.id" class="row-internal">
            <td class="question-cell">{{ v.name || ('Vendor ' + v.id) }}</td>
            <td colspan="4">未管制（不限額度）</td>
            <td><span class="badge badge-internal">未設定</span></td>
            <td><button class="btn-sm" @click="startCreate(v.id)">設定額度</button></td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="!loading && !groups.length && !userRows.length" class="empty-state">
      📭 此期間無真實使用事件
      <div v-if="!includeInternal && internalCount > 0" class="empty-hint">
        （另有內部流量 {{ internalCount }} 筆——回測/迴圈/開發測試；勾選上方「含內部流量」查看）
      </div>
    </div>
    <div v-if="error" class="error-message">❌ {{ error }}</div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'UsageStatsView',
  data() {
    const today = new Date();
    const first = new Date(today.getFullYear(), today.getMonth(), 1);
    const iso = d => d.toISOString().slice(0, 10);
    return {
      dateFrom: iso(first), dateTo: iso(today),
      vendorId: '', granularity: 'day', includeInternal: false,
      groups: [], totals: null, vendors: [], userRows: [], userLimit: 50, internalCount: 0, quotaRows: [], editing: null,
      editForm: { monthly_message_quota: 5000, warn_threshold_pct: 80, block_on_exceed: true, is_active: true },
      loading: false, error: null,
    };
  },
  computed: {
    unmanagedVendors() {
      const managed = new Set(this.quotaRows.map(q => String(q.vendor_id)));
      return this.vendors.filter(v => !managed.has(String(v.id)));
    },
    vendorRank() {
      const agg = {};
      for (const g of this.groups) {
        const k = g.vendor_id ?? '—';
        agg[k] = agg[k] || { vendor_id: g.vendor_id, messages: 0, sessions: 0, cost: 0 };
        agg[k].messages += g.messages;
        agg[k].sessions += g.sessions;
        agg[k].cost += g.est_cost_usd || 0;
      }
      return Object.values(agg).sort((a, b) => b.messages - a.messages);
    },
  },
  mounted() {
    this.loadVendors();
    this.load();
  },
  methods: {
    params() {
      const p = { date_from: this.dateFrom, date_to: this.dateTo,
                  granularity: this.granularity, include_internal: this.includeInternal };
      if (this.vendorId) p.vendor_id = this.vendorId;
      return p;
    },
    async load() {
      this.loading = true; this.error = null;
      try {
        const [r, ru] = await Promise.all([
          axios.get('/api/usage/stats', { params: this.params() }),
          axios.get('/api/usage/users', { params: { ...this.params(), limit: this.userLimit } }),
        ]);
        this.groups = r.data.groups || [];
        this.totals = r.data.totals || null;
        this.userRows = ru.data.users || [];
        const rq = await axios.get('/api/usage/quotas');
        this.quotaRows = rq.data.quotas || [];
        this.internalCount = 0;
        if (!this.includeInternal && !this.groups.length) {
          const ri = await axios.get('/api/usage/stats',
            { params: { ...this.params(), include_internal: true } });
          this.internalCount = ri.data.totals?.messages || 0;
        }
      } catch (e) {
        this.error = e.response?.data?.detail || e.message;
        this.groups = []; this.totals = null;
      } finally { this.loading = false; }
    },
    async loadVendors() {
      try {
        const r = await axios.get('/rag-api/v1/vendors');
        this.vendors = r.data.vendors || r.data || [];
      } catch (e) { this.vendors = []; }
    },
    exportCsv() {
      const q = new URLSearchParams(this.params()).toString();
      const token = localStorage.getItem('token') || localStorage.getItem('access_token') || '';
      fetch(`/api/usage/export.csv?${q}`, { headers: { Authorization: `Bearer ${token}` } })
        .then(r => r.blob()).then(b => {
          const a = document.createElement('a');
          a.href = URL.createObjectURL(b);
          a.download = `usage_${this.dateFrom}_${this.dateTo}.csv`;
          a.click();
        });
    },
    startEdit(q) {
      this.editing = q.vendor_id;
      this.editForm = { monthly_message_quota: q.monthly_message_quota,
                        warn_threshold_pct: q.warn_threshold_pct,
                        block_on_exceed: q.block_on_exceed, is_active: true };
    },
    startCreate(vendorId) {
      this.quotaRows.push({ vendor_id: vendorId, monthly_message_quota: 5000,
                            warn_threshold_pct: 80, block_on_exceed: true,
                            is_active: true, used_this_month: 0, pct: 0, state: 'ok' });
      this.startEdit(this.quotaRows[this.quotaRows.length - 1]);
    },
    async saveQuota(vendorId) {
      try {
        await axios.put(`/api/usage/quotas/${vendorId}`, this.editForm);
        this.editing = null;
        this.load();
      } catch (e) { this.error = e.response?.data?.detail || e.message; }
    },
    async deactivateQuota(vendorId) {
      try {
        await axios.delete(`/api/usage/quotas/${vendorId}`);
        this.load();
      } catch (e) { this.error = e.response?.data?.detail || e.message; }
    },
    vendorName(id) {
      if (id == null) return '—';
      const v = this.vendors.find(x => String(x.id) === String(id));
      return v ? (v.name || `Vendor ${id}`) : `Vendor ${id}`;
    },
    typeLabel(t) {
      return { tenant: '🏠 租客', property_manager: '🏢 業者用戶', prospect: '🔍 潛在客戶',
               internal: '⚙️ 內部', unknown: '❓ 未標' }[t] || t;
    },
    typeBadge(t) {
      return { tenant: 'badge-tenant', property_manager: 'badge-pm', prospect: 'badge-prospect',
               internal: 'badge-internal', unknown: 'badge-unknown' }[t] || 'badge-unknown';
    },
    shortTs(ts) {
      if (!ts) return '—';
      const d = new Date(ts);
      return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
    },
    fmt(n) { return (n || 0).toLocaleString(); },
  },
};
</script>

<style scoped>
.usage-stats-view { padding: 20px; }

/* 頁首（全站慣例） */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.page-header h2 { margin: 0; font-size: 28px; color: #333; }
.header-actions { display: flex; gap: 10px; }
.page-hint { color: #7f8c8d; font-size: 13px; margin: 0 0 20px; }
.btn {
  padding: 8px 16px; border: none; border-radius: 4px;
  cursor: pointer; font-size: 14px;
}
.btn-primary { background: #007bff; color: #fff; }
.btn-primary:hover { background: #0069d9; }

/* 篩選（全站 filter-section 慣例） */
.filter-section {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-bottom: 20px;
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  align-items: center;
}
.filter-group { display: flex; align-items: center; gap: 8px; }
.filter-group label { font-size: 14px; color: #333; font-weight: 500; }
.filter-group input[type="date"], .filter-group select {
  padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px;
}
.tilde { color: #999; }
.checkbox-group label { display: flex; align-items: center; gap: 6px; font-weight: 400; }

/* 統計卡（全站 stats-grid/stat-card 慣例） */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}
.stat-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.stat-icon { font-size: 28px; margin-right: 14px; }
.stat-value { font-size: 24px; font-weight: 700; color: #333; }
.stat-label { font-size: 13px; color: #7f8c8d; }

/* 表格白卡（全站 table 慣例） */
.table-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  overflow: hidden;
  margin-bottom: 20px;
  padding: 0 0 4px;
}
.table-card h3 { margin: 0; padding: 16px 20px 8px; font-size: 16px; color: #333; }
table { width: 100%; border-collapse: collapse; }
th {
  background: #f8f9fa; padding: 12px; text-align: left;
  font-weight: 600; color: #333; border-bottom: 2px solid #e9ecef; font-size: 14px;
}
td { padding: 12px; border-bottom: 1px solid #e9ecef; font-size: 14px; }
.question-cell { font-weight: 500; }
tr.row-internal { color: #999; background: #fafafa; }

/* 使用者類型章（全站 badge 慣例） */
.badge {
  display: inline-block; padding: 4px 10px; border-radius: 12px;
  font-size: 12px; font-weight: 600;
}
.badge-tenant { background: #d4edda; color: #155724; }
.badge-pm { background: #cce5ff; color: #004085; }
.badge-prospect { background: #fff3cd; color: #856404; }
.badge-internal { background: #e2e3e5; color: #383d41; }
.badge-unknown { background: #f8d7da; color: #721c24; }

.q-bar { background: #eee; border-radius: 6px; height: 12px; width: 100%; overflow: hidden; }
.q-fill { height: 100%; border-radius: 6px; transition: width .3s; }
.q-ok { background: #28a745; }
.q-warn { background: #ffc107; }
.q-blocked { background: #dc3545; }
.q-none { background: #adb5bd; }
.q-text { font-size: 12px; color: #666; }
.q-input { width: 90px; padding: 4px 6px; border: 1px solid #ddd; border-radius: 4px; }
.q-narrow { width: 60px; }
.btn-sm { padding: 4px 10px; font-size: 12px; border: none; border-radius: 4px;
          background: #007bff; color: #fff; cursor: pointer; margin-right: 4px; }
.btn-plain { background: #6c757d; }
.empty-state { color: #999; padding: 40px; text-align: center; background: white; border-radius: 8px; }
.empty-hint { margin-top: 8px; font-size: 13px; color: #b8860b; }
.error-message { color: #c0392b; margin-top: 10px; }
</style>
