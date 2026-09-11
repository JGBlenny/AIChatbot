<template>
  <div class="knowledge-export">
    <h2>📥 知識庫匯出</h2>

    <!-- 說明區塊 -->
    <InfoPanel :config="helpTexts.knowledgeExport" />

    <p class="subtitle">匯出所有知識庫為 Excel 格式（標準格式，與匯入兼容，支援大量資料分批處理）</p>

    <!-- 匯出進行中通知 -->
    <div v-if="currentExportJob" class="export-notification">
      <div class="notification-icon">⏳</div>
      <div class="notification-content">
        <div class="notification-title">正在匯出知識庫...</div>
        <div class="notification-message">
          Job ID: {{ currentExportJob.job_id }}
          <span v-if="currentExportJob.exported_count">
            - 已匯出 {{ currentExportJob.exported_count }} 筆
          </span>
        </div>
        <div class="notification-progress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{width: currentExportJob.progress + '%'}"></div>
          </div>
          <span class="progress-text">{{ currentExportJob.progress }}%</span>
        </div>
      </div>
    </div>

    <!-- 匯出成功通知 -->
    <div v-if="showSuccessNotification" class="success-notification">
      <div class="notification-icon">✅</div>
      <div class="notification-content">
        <div class="notification-title">匯出完成！</div>
        <div class="notification-message">
          成功匯出 {{ lastCompletedJob?.exported_count || 0 }} 筆知識，檔案大小 {{ lastCompletedJob?.file_size_kb || 0 }} KB
        </div>
      </div>
      <button @click="showSuccessNotification = false" class="notification-close">✕</button>
    </div>

    <!-- 匯出配置區 -->
    <div class="export-config-section">
      <h3>📋 知識庫匯出</h3>

      <div class="config-form">
        <!-- 說明 -->
        <div class="form-group">
          <div class="info-box">
            <strong>ℹ️  標準匯出格式</strong>
            <p>將匯出<strong>所有知識庫資料</strong>為標準 Excel 格式，包含所有必要欄位（問題、答案、作用域、業者ID、業態等），可直接用於知識庫匯入功能。</p>
            <p style="margin-top: 8px; color: #666; font-size: 13px;">✓ 支援大量資料分批處理<br>✓ 匯出檔案可直接匯入<br>✓ 包含所有供應商的知識</p>
          </div>
        </div>

        <!-- 開始匯出按鈕 -->
        <div class="form-actions">
          <button
            @click="startExport"
            :disabled="isExporting"
            class="btn-primary btn-large"
          >
            {{ isExporting ? '⏳ 建立匯出任務中...' : '🚀 開始匯出所有知識' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 匯出歷史 -->
    <div class="export-history-section" v-if="exportJobs.length > 0">
      <h3>📊 匯出歷史</h3>

      <div class="jobs-table">
        <table>
          <thead>
            <tr>
              <th>狀態</th>
              <th>進度</th>
              <th>匯出數量</th>
              <th>檔案大小</th>
              <th>建立時間</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in exportJobs" :key="job.job_id">
              <td>
                <span class="status-badge" :class="'status-' + job.status">
                  {{ getStatusLabel(job.status) }}
                </span>
              </td>
              <td>
                <!-- 進度條 -->
                <div v-if="job.status === 'processing'" class="table-progress">
                  <div class="table-progress-bar" :style="{width: job.progress + '%'}"></div>
                  <span class="table-progress-text">{{ job.progress }}%</span>
                </div>
                <span v-else-if="job.status === 'completed'">✅ 完成</span>
                <span v-else-if="job.status === 'failed'">❌ 失敗</span>
                <span v-else>⏳ 等待中</span>
              </td>
              <td>{{ job.exported_count || 0 }} 筆</td>
              <td>{{ job.file_size_kb ? job.file_size_kb + ' KB' : '-' }}</td>
              <td>{{ formatDate(job.created_at) }}</td>
              <td class="table-actions">
                <button
                  v-if="job.status === 'completed'"
                  @click="downloadFile(job.job_id)"
                  class="btn-download btn-sm"
                >
                  ⬇️ 下載
                </button>
                <button
                  v-if="job.status === 'failed'"
                  @click="viewError(job)"
                  class="btn-info btn-sm"
                >
                  查看錯誤
                </button>
                <button
                  @click="deleteJob(job.job_id)"
                  class="btn-delete btn-sm"
                  :disabled="job.status === 'processing'"
                >
                  刪除
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 空狀態提示 -->
    <div v-else class="empty-state">
      <div class="empty-icon">📦</div>
      <p>尚無匯出記錄</p>
      <p class="hint">配置並開始您的第一次匯出</p>
    </div>

    <!-- 統計資訊 -->
    <div class="statistics-section" v-if="statistics">
      <h3>📈 匯出統計</h3>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon">📁</div>
          <div class="stat-content">
            <div class="stat-value">{{ statistics.total_exports || 0 }}</div>
            <div class="stat-label">總匯出次數</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">✅</div>
          <div class="stat-content">
            <div class="stat-value">{{ statistics.successful_exports || 0 }}</div>
            <div class="stat-label">成功匯出</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">📊</div>
          <div class="stat-content">
            <div class="stat-value">{{ statistics.total_exported_rows || 0 }}</div>
            <div class="stat-label">總匯出筆數</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">🕒</div>
          <div class="stat-content">
            <div class="stat-value">{{ formatDate(statistics.last_export_at) }}</div>
            <div class="stat-label">最後匯出</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import InfoPanel from '@/components/InfoPanel.vue';
import helpTexts from '@/config/help-texts.js';

const API_BASE = '/rag-api/v1';

export default {
  name: 'KnowledgeExportView',

  components: {
    InfoPanel
  },

  data() {
    return {
      helpTexts,
      exportJobs: [],
      statistics: null,
      isExporting: false,
      pollingInterval: null,
      currentExportJob: null,  // 當前正在執行的匯出任務
      showSuccessNotification: false,  // 是否顯示成功通知
      lastCompletedJob: null  // 最後完成的任務
    };
  },

  mounted() {
    this.loadExportJobs();
    this.loadStatistics();
    this.startPolling();
  },

  beforeUnmount() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
    }
  },

  methods: {
    async loadExportJobs() {
      try {
        const response = await axios.get(`${API_BASE}/knowledge-export/jobs`);
        const newJobs = response.data.jobs || response.data;

        // 檢查是否有進行中的任務
        const processingJob = newJobs.find(j => j.status === 'processing');

        // 如果有之前的 currentExportJob，檢查它是否完成了
        if (this.currentExportJob && this.currentExportJob.status === 'processing') {
          const updatedJob = newJobs.find(j => j.job_id === this.currentExportJob.job_id);
          if (updatedJob && updatedJob.status === 'completed') {
            // 任務完成，顯示成功通知
            this.lastCompletedJob = updatedJob;
            this.showSuccessNotification = true;
            this.currentExportJob = null;

            // 5 秒後自動關閉成功通知
            setTimeout(() => {
              this.showSuccessNotification = false;
            }, 5000);
          } else if (updatedJob && updatedJob.status === 'failed') {
            // 任務失敗
            this.currentExportJob = null;
            alert(`匯出失敗：${updatedJob.error || '未知錯誤'}`);
          } else if (updatedJob) {
            // 更新進度
            this.currentExportJob = updatedJob;
          }
        }

        // 如果沒有 currentExportJob 但有新的 processing job
        if (!this.currentExportJob && processingJob) {
          this.currentExportJob = processingJob;
        }

        this.exportJobs = newJobs;
      } catch (error) {
        console.error('載入匯出歷史失敗', error);
      }
    },

    async loadStatistics() {
      try {
        const response = await axios.get(`${API_BASE}/knowledge-export/statistics`);
        this.statistics = response.data;
      } catch (error) {
        console.error('載入統計資訊失敗', error);
      }
    },

    async startExport() {
      this.isExporting = true;

      try {
        const payload = {
          vendor_id: null,  // 匯出所有知識，不限定供應商
          export_mode: 'standard',
          include_intents: false,
          include_metadata: false
        };

        const response = await axios.post(`${API_BASE}/knowledge-export/export`, payload);

        // 設置當前匯出任務
        this.currentExportJob = {
          job_id: response.data.job_id,
          status: 'processing',
          progress: 0,
          exported_count: 0
        };

        // 重新載入列表
        await this.loadExportJobs();
        await this.loadStatistics();

        // 滾動到匯出歷史區域（如果有的話）
        this.$nextTick(() => {
          const historySection = document.querySelector('.export-history-section');
          if (historySection) {
            historySection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          }
        });

      } catch (error) {
        console.error('建立匯出任務失敗', error);
        alert('建立匯出任務失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.isExporting = false;
      }
    },

    async downloadFile(jobId) {
      try {
        const response = await axios.get(
          `${API_BASE}/knowledge-export/jobs/${jobId}/download`,
          { responseType: 'blob' }
        );

        // 從 Content-Disposition header 獲取檔案名稱
        const contentDisposition = response.headers['content-disposition'];
        let filename = 'knowledge_export.xlsx';
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
          if (filenameMatch && filenameMatch[1]) {
            filename = filenameMatch[1].replace(/['"]/g, '');
          }
        }

        // 建立下載連結
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);

      } catch (error) {
        console.error('下載檔案失敗', error);
        alert('下載檔案失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    async deleteJob(jobId) {
      if (!confirm('確定要刪除這個匯出記錄嗎？')) return;

      try {
        await axios.delete(`${API_BASE}/knowledge-export/jobs/${jobId}`);
        await this.loadExportJobs();
        await this.loadStatistics();
      } catch (error) {
        console.error('刪除任務失敗', error);
        alert('刪除任務失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    viewError(job) {
      alert(`匯出失敗詳情：\n\nJob ID: ${job.job_id}\n錯誤訊息: ${job.error || '未知錯誤'}`);
    },

    startPolling() {
      // 每 2 秒更新一次（有進行中任務時更頻繁更新）
      this.pollingInterval = setInterval(async () => {
        if (this.currentExportJob || this.exportJobs.some(j => j.status === 'processing')) {
          await this.loadExportJobs();
        }
      }, 2000);
    },

    getStatusLabel(status) {
      const labels = {
        pending: '等待中',
        processing: '處理中',
        completed: '已完成',
        failed: '失敗'
      };
      return labels[status] || status;
    },

    formatDate(dateString) {
      if (!dateString) return '-';
      const date = new Date(dateString);
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

<style scoped>
.knowledge-export {
  /* 寬度和內邊距由 app-main 統一管理 */
}

.subtitle {
  color: #666;
  margin-bottom: 30px;
}

/* ==================== 通知區塊 ==================== */
.export-notification {
  display: flex;
  align-items: flex-start;
  gap: 15px;
  padding: 20px;
  background: #fff3cd;
  border: 2px solid #ffc107;
  border-radius: 8px;
  margin-bottom: 20px;
  animation: slideDown 0.3s ease-out;
}

.success-notification {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  background: #d1e7dd;
  border: 2px solid #4CAF50;
  border-radius: 8px;
  margin-bottom: 20px;
  position: relative;
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.notification-icon {
  font-size: 32px;
  flex-shrink: 0;
}

.notification-content {
  flex: 1;
}

.notification-title {
  font-size: 16px;
  font-weight: bold;
  color: #333;
  margin-bottom: 6px;
}

.notification-message {
  font-size: 14px;
  color: #666;
  margin-bottom: 10px;
}

.notification-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
}

.progress-bar {
  flex: 1;
  height: 24px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
  transition: width 0.5s ease-out;
  border-radius: 12px;
}

.progress-text {
  font-size: 14px;
  font-weight: bold;
  color: #333;
  min-width: 45px;
  text-align: right;
}

.notification-close {
  position: absolute;
  top: 10px;
  right: 10px;
  background: transparent;
  border: none;
  font-size: 24px;
  color: #666;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.notification-close:hover {
  background: rgba(0, 0, 0, 0.1);
  color: #333;
}

/* ==================== 匯出配置區 ==================== */
.export-config-section {
  background: white;
  padding: 25px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  margin-bottom: 30px;
}

.export-config-section h3 {
  margin-top: 0;
  margin-bottom: 20px;
  color: #333;
}

.config-form {
  max-width: 700px;
}

.form-group {
  margin-bottom: 25px;
}

.form-label {
  display: block;
  font-weight: bold;
  color: #333;
  margin-bottom: 10px;
  font-size: 14px;
}

.form-select {
  width: 100%;
  padding: 10px 15px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  cursor: pointer;
  transition: border-color 0.2s;
}

.form-select:focus {
  outline: none;
  border-color: #4CAF50;
}

.form-hint {
  margin-top: 6px;
  font-size: 12px;
  color: #999;
}

.info-box {
  background: #e3f2fd;
  border-left: 4px solid #2196f3;
  padding: 15px;
  border-radius: 6px;
  line-height: 1.6;
}

.info-box strong {
  color: #1976d2;
  display: block;
  margin-bottom: 8px;
}

.info-box p {
  margin: 0;
  color: #333;
}

/* 單選按鈕組 */
.radio-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.radio-option {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 15px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fafafa;
}

.radio-option:hover {
  border-color: #4CAF50;
  background: #f0f8f0;
}

.radio-option input[type="radio"] {
  margin-top: 3px;
  cursor: pointer;
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.radio-option input[type="radio"]:checked + .radio-content {
  color: #4CAF50;
}

.radio-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.radio-content strong {
  font-size: 15px;
  color: #333;
}

.radio-desc {
  font-size: 13px;
  color: #666;
}

/* 複選框組 */
.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.checkbox-option {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
  padding: 10px;
  border-radius: 6px;
  transition: background 0.2s;
}

.checkbox-option:hover {
  background: #f5f5f5;
}

.checkbox-option input[type="checkbox"] {
  cursor: pointer;
  width: 18px;
  height: 18px;
}

.form-actions {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #e0e0e0;
}

.btn-large {
  padding: 14px 32px;
  font-size: 16px;
}

/* ==================== 匯出歷史區 ==================== */
.export-history-section {
  background: white;
  padding: 25px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  margin-bottom: 30px;
}

.export-history-section h3 {
  margin-top: 0;
  margin-bottom: 20px;
  color: #333;
}

.jobs-table {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

thead {
  background: #f5f5f5;
}

th {
  padding: 12px;
  text-align: left;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #e0e0e0;
}

td {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}

tbody tr:hover {
  background: #fafafa;
}

.mode-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.mode-basic {
  background: #e3f2fd;
  color: #1976d2;
}

.mode-formatted {
  background: #f3e5f5;
  color: #7b1fa2;
}

.mode-optimized {
  background: #fff3e0;
  color: #e65100;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.status-pending {
  background: #fff3cd;
  color: #856404;
}

.status-processing {
  background: #cfe2ff;
  color: #084298;
}

.status-completed {
  background: #d1e7dd;
  color: #0f5132;
}

.status-failed {
  background: #f8d7da;
  color: #842029;
}

.table-progress {
  position: relative;
  width: 100px;
  height: 18px;
  background: #f0f0f0;
  border-radius: 9px;
  overflow: hidden;
}

.table-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
  transition: width 0.3s;
}

.table-progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 10px;
  font-weight: bold;
  color: #333;
}

.table-actions {
  white-space: nowrap;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  margin-right: 6px;
}

.btn-sm:last-child {
  margin-right: 0;
}

.btn-sm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-download {
  background: #4CAF50;
  color: white;
}

.btn-download:hover:not(:disabled) {
  background: #45a049;
}

.btn-info {
  background: #2196f3;
  color: white;
}

.btn-info:hover:not(:disabled) {
  background: #0b7dda;
}

.btn-delete {
  background: #f44336;
  color: white;
}

.btn-delete:hover:not(:disabled) {
  background: #d32f2f;
}

/* ==================== 空狀態 ==================== */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
  background: white;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  margin-bottom: 30px;
}

.empty-icon {
  font-size: 60px;
  margin-bottom: 15px;
  opacity: 0.5;
}

.empty-state p {
  margin: 8px 0;
}

.hint {
  font-size: 14px;
  color: #bbb;
}

/* ==================== 統計區 ==================== */
.statistics-section {
  background: white;
  padding: 25px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}

.statistics-section h3 {
  margin-top: 0;
  margin-bottom: 20px;
  color: #333;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  background: #f9f9f9;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  transition: all 0.2s;
}

.stat-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  transform: translateY(-2px);
}

.stat-icon {
  font-size: 36px;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #333;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: #666;
}

/* ==================== 按鈕通用樣式 ==================== */
.btn-primary {
  background: #4CAF50;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #45a049;
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}
</style>
