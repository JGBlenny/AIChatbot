<template>
  <div class="qb-backtest">
    <!-- ① 發起回測 -->
    <div class="panel launch-panel">
      <h3>🧪 發起題庫回測</h3>
      <p class="hint">選擇題庫（與迴圈無關）——受眾決定請求形狀：業者/售前走 b2b、租客走 b2c，鏡像生產呼叫。</p>
      <div class="filter-row">
        <label>題庫受眾：
          <select v-model="filters.target_user" @change="refreshCount">
            <option value="">全部</option>
            <option value="property_manager">業者（JGB 系統知識）</option>
            <option value="tenant">租客（服務/SOP）</option>
            <option value="prospect">售前</option>
          </select>
        </label>
        <label>來源：
          <select v-model="filters.source" @change="refreshCount">
            <option value="">全部</option>
            <option value="imported">imported</option>
            <option value="auto_generated">auto_generated</option>
            <option value="user_question">user_question</option>
            <option value="manual">manual</option>
          </select>
        </label>
        <label>難度：
          <select v-model="filters.difficulty" @change="refreshCount">
            <option value="">全部</option>
            <option value="easy">easy</option>
            <option value="medium">medium</option>
            <option value="hard">hard</option>
          </select>
        </label>
        <span class="count-preview">
          符合題數：<b>{{ countLoading ? '…' : matchedCount }}</b>
        </span>
      </div>
      <div class="filter-row">
        <label>每批題數：
          <input type="number" v-model.number="batchSize" min="5" max="500" style="width:70px" />
        </label>
        <label>品質模式：
          <select v-model="qualityMode">
            <option value="detailed">detailed</option>
            <option value="hybrid">hybrid</option>
            <option value="basic">basic</option>
          </select>
        </label>
        <button class="btn-run" :disabled="launching || !matchedCount" @click="launch">
          {{ launching ? '啟動中…' : '▶ 執行回測' }}
        </button>
        <span v-if="launchMsg" class="launch-msg">{{ launchMsg }}</span>
      </div>
    </div>

    <!-- ② 回測記錄 -->
    <div class="panel">
      <div class="runs-header">
        <h3>📜 回測記錄</h3>
        <button class="btn-sm" @click="loadRuns">🔄 重新整理</button>
      </div>
      <table class="runs-table">
        <thead>
          <tr><th>Run</th><th>狀態</th><th>進度</th><th>通過率</th><th>開始時間</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="run in runs" :key="run.id" :class="{ selected: selectedRun === run.id }">
            <td>#{{ run.id }}</td>
            <td>
              <span class="status-dot" :class="run.status">{{ statusLabel(run.status) }}</span>
            </td>
            <td>{{ run.executed_scenarios || 0 }}/{{ run.total_scenarios || '?' }}</td>
            <td>{{ run.pass_rate != null ? run.pass_rate.toFixed ? run.pass_rate.toFixed(1) : run.pass_rate : '—' }}%</td>
            <td>{{ fmtTime(run.started_at) }}</td>
            <td><button class="btn-sm" @click="viewRun(run.id)">查看</button></td>
          </tr>
        </tbody>
      </table>

      <!-- 選中 run：評級分佈＋結果 -->
      <div v-if="selectedRun" class="run-detail">
        <div v-if="gradeDist && Object.keys(gradeDist).length" class="grade-dist">
          <span class="grade-dist-label">評級分佈（v3）：</span>
          <span v-for="g in gradeOrder" :key="g">
            <span v-if="gradeDist[g]" class="grade-chip" :class="'grade-' + g.toLowerCase()">
              {{ gradeLabel(g) }} {{ gradeDist[g] }}
            </span>
          </span>
          <span v-if="passRateV3 != null" class="v3-rate">合格率 {{ passRateV3 }}%</span>
        </div>
        <table class="results-table">
          <thead>
            <tr><th style="width:38%">題目</th><th style="width:110px">評級</th><th>系統回答（摘要）</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in runResults" :key="r.id">
              <td>{{ r.test_question }}</td>
              <td>
                <span v-if="r.grade" class="grade-chip" :class="'grade-' + r.grade.toLowerCase()"
                      :title="r.grade_reason || ''">{{ gradeLabel(r.grade) }}</span>
                <span v-else>{{ r.passed ? '✅' : '❌' }}</span>
              </td>
              <td class="answer-cell">{{ (r.system_answer || '').slice(0, 120) }}</td>
            </tr>
          </tbody>
        </table>
        <div class="pager">
          <button class="btn-sm" :disabled="resultOffset === 0" @click="pageResults(-1)">上一頁</button>
          <span>{{ resultOffset + 1 }}–{{ resultOffset + runResults.length }} / {{ resultTotal }}</span>
          <button class="btn-sm" :disabled="resultOffset + resultLimit >= resultTotal" @click="pageResults(1)">下一頁</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

export default {
  name: 'QuestionBankBacktestTab',
  data() {
    return {
      filters: { target_user: 'property_manager', source: '', difficulty: '' },
      matchedCount: null,
      countLoading: false,
      batchSize: 50,
      qualityMode: 'detailed',
      launching: false,
      launchMsg: '',
      runs: [],
      selectedRun: null,
      gradeDist: null,
      passRateV3: null,
      runResults: [],
      resultTotal: 0,
      resultOffset: 0,
      resultLimit: 20,
      pollTimer: null,
      gradeOrder: ['GOOD', 'ASK_OK', 'ASK_BAD', 'WRONG', 'NOFOUND', 'BROKEN', 'EVAL_ERR'],
    };
  },
  mounted() {
    this.refreshCount();
    this.loadRuns();
    this.pollTimer = setInterval(() => {
      if (this.runs.some(r => r.status === 'running')) this.loadRuns();
    }, 5000);
  },
  beforeUnmount() {
    if (this.pollTimer) clearInterval(this.pollTimer);
  },
  methods: {
    payloadFilters() {
      const p = {};
      for (const k of ['target_user', 'source', 'difficulty']) {
        if (this.filters[k]) p[k] = this.filters[k];
      }
      return p;
    },
    async refreshCount() {
      this.countLoading = true;
      try {
        const r = await axios.post(`${API_BASE_URL}/api/test-scenarios/count`, this.payloadFilters());
        this.matchedCount = r.data.total ?? 0;
      } catch (e) {
        this.matchedCount = null;
      } finally {
        this.countLoading = false;
      }
    },
    async launch() {
      this.launching = true;
      this.launchMsg = '';
      try {
        const body = {
          batch_size: this.batchSize,
          batch_number: 1,
          quality_mode: this.qualityMode,
          vendor_id: 2,
          ...this.payloadFilters(),
        };
        const r = await axios.post(`${API_BASE_URL}/api/backtest/run/smart-batch`, body);
        this.launchMsg = `✅ 已啟動（${r.data.run_id ? 'Run #' + r.data.run_id : '見下方記錄'}）`;
        setTimeout(this.loadRuns, 2000);
      } catch (e) {
        this.launchMsg = `❌ ${e.response?.data?.detail || e.message}`;
      } finally {
        this.launching = false;
      }
    },
    async loadRuns() {
      try {
        const r = await axios.get(`${API_BASE_URL}/api/backtest/runs`, { params: { limit: 10 } });
        this.runs = r.data.runs || r.data || [];
      } catch (e) { /* 靜默 */ }
    },
    async viewRun(id) {
      this.selectedRun = id;
      this.resultOffset = 0;
      await Promise.all([this.loadDist(), this.loadResults()]);
    },
    async loadDist() {
      try {
        const r = await axios.get(`${API_BASE_URL}/api/backtest/runs/${this.selectedRun}/grade-distribution`);
        this.gradeDist = r.data.distribution || {};
        this.passRateV3 = r.data.pass_rate_v3;
      } catch (e) { this.gradeDist = null; this.passRateV3 = null; }
    },
    async loadResults() {
      try {
        const r = await axios.get(`${API_BASE_URL}/api/backtest/runs/${this.selectedRun}/results`,
          { params: { limit: this.resultLimit, offset: this.resultOffset } });
        this.runResults = r.data.results || [];
        this.resultTotal = r.data.total || this.runResults.length;
      } catch (e) { this.runResults = []; }
    },
    pageResults(dir) {
      this.resultOffset = Math.max(0, this.resultOffset + dir * this.resultLimit);
      this.loadResults();
    },
    gradeLabel(g) {
      const map = { GOOD: '✔ 直答', ASK_OK: '↩ 合理追問', ASK_BAD: '⚠ 過度追問',
                    WRONG: '✖ 錯位', NOFOUND: '∅ 查無', BROKEN: '💥 異常', EVAL_ERR: '? 評審失敗' };
      return map[g] || g;
    },
    statusLabel(s) {
      return { running: '執行中', completed: '完成', cancelled: '已取消', failed: '失敗' }[s] || s;
    },
    fmtTime(t) {
      return t ? new Date(t).toLocaleString('zh-TW', { hour12: false }) : '—';
    },
  },
};
</script>

<style scoped>
.qb-backtest { display: flex; flex-direction: column; gap: 16px; }
.panel { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; }
.hint { color: #888; font-size: 12px; margin: 4px 0 10px; }
.filter-row { display: flex; flex-wrap: wrap; gap: 14px; align-items: center; margin-bottom: 8px; }
.filter-row label { font-size: 13px; color: #444; }
.filter-row select, .filter-row input { margin-left: 4px; padding: 3px 6px; }
.count-preview { font-size: 13px; color: #333; }
.btn-run { background: #2563eb; color: #fff; border: none; border-radius: 6px; padding: 6px 16px; cursor: pointer; }
.btn-run:disabled { background: #a5b4fc; cursor: not-allowed; }
.launch-msg { font-size: 13px; }
.runs-header { display: flex; justify-content: space-between; align-items: center; }
.btn-sm { padding: 2px 8px; font-size: 12px; cursor: pointer; }
.runs-table, .results-table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 13px; }
.runs-table th, .runs-table td, .results-table th, .results-table td { border-bottom: 1px solid #eee; padding: 6px 8px; text-align: left; }
.runs-table tr.selected { background: #eef4ff; }
.status-dot { padding: 1px 8px; border-radius: 8px; font-size: 12px; }
.status-dot.running { background: #fff7e0; color: #b26a00; }
.status-dot.completed { background: #e6f7e6; color: #1a7f1a; }
.status-dot.failed, .status-dot.cancelled { background: #fdecea; color: #b3261e; }
.run-detail { margin-top: 12px; }
.answer-cell { color: #555; }
.pager { display: flex; gap: 10px; align-items: center; margin-top: 8px; font-size: 13px; }
.grade-dist { margin: 8px 0; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.grade-dist-label { font-size: 13px; color: #666; }
.v3-rate { font-size: 13px; font-weight: 600; margin-left: 6px; }
.grade-chip { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; white-space: nowrap; }
.grade-good { background: #e6f7e6; color: #1a7f1a; }
.grade-ask_ok { background: #e8f1fb; color: #1a5fa8; }
.grade-ask_bad { background: #fff3e0; color: #b26a00; }
.grade-wrong { background: #fdecea; color: #b3261e; }
.grade-nofound { background: #f0f0f0; color: #666; }
.grade-broken { background: #fce4ec; color: #ad1457; }
.grade-eval_err { background: #f5f5f5; color: #999; }
</style>
