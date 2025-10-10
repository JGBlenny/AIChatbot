<template>
  <div class="knowledge-import">
    <h2>📤 知識庫匯入</h2>
    <p class="subtitle">上傳 LINE 聊天記錄 txt 文件，自動提取知識庫並智能去重</p>

    <!-- 步驟指示器 -->
    <div class="steps">
      <div class="step" :class="{active: currentStep === 1, completed: currentStep > 1}">
        <div class="step-number">1</div>
        <div class="step-title">上傳文件</div>
      </div>
      <div class="step" :class="{active: currentStep === 2, completed: currentStep > 2}">
        <div class="step-number">2</div>
        <div class="step-title">預覽確認</div>
      </div>
      <div class="step" :class="{active: currentStep === 3, completed: currentStep > 3}">
        <div class="step-number">3</div>
        <div class="step-title">處理中</div>
      </div>
      <div class="step" :class="{active: currentStep === 4}">
        <div class="step-number">4</div>
        <div class="step-title">完成</div>
      </div>
    </div>

    <!-- Step 1: 上傳文件 -->
    <div v-if="currentStep === 1" class="step-content">
      <div class="upload-area" @dragover.prevent @drop.prevent="handleDrop">
        <input
          ref="fileInput"
          type="file"
          accept=".txt"
          @change="handleFileSelect"
          style="display: none"
        />

        <div v-if="!selectedFile" class="upload-placeholder" @click="$refs.fileInput.click()">
          <div class="upload-icon">📁</div>
          <p><strong>點擊或拖曳文件至此</strong></p>
          <p class="hint">支援 .txt 格式的 LINE 聊天記錄</p>
        </div>

        <div v-else class="file-selected">
          <div class="file-info">
            <div class="file-icon">📄</div>
            <div class="file-details">
              <div class="file-name">{{ selectedFile.name }}</div>
              <div class="file-size">{{ formatFileSize(selectedFile.size) }}</div>
            </div>
            <button @click="clearFile" class="btn-remove">✕</button>
          </div>
        </div>
      </div>

      <!-- 匯入選項 -->
      <div class="import-options">
        <h3>匯入選項</h3>

        <div class="option-group">
          <label>
            <input type="radio" v-model="importMode" value="new" />
            <span class="option-label">
              <strong>新增知識</strong>
              <small>提取新的問答對並添加到知識庫</small>
            </span>
          </label>

          <label>
            <input type="radio" v-model="importMode" value="optimize" />
            <span class="option-label">
              <strong>優化現有</strong>
              <small>分析現有知識並優化內容（較少 token 消耗）</small>
            </span>
          </label>
        </div>

        <div class="option-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="enableDeduplication" />
            <span>
              <strong>啟用智能去重</strong>
              <small>自動跳過已存在的知識，避免浪費 token</small>
            </span>
          </label>
        </div>

        <div class="option-group" v-if="vendors.length > 0">
          <label>
            業者（可選）:
            <select v-model="selectedVendor">
              <option :value="null">通用知識（適用所有業者）</option>
              <option v-for="vendor in vendors" :key="vendor.id" :value="vendor.id">
                {{ vendor.name }}
              </option>
            </select>
          </label>
        </div>
      </div>

      <div class="actions">
        <button
          @click="previewFile"
          :disabled="!selectedFile || previewing"
          class="btn-primary"
        >
          {{ previewing ? '⏳ 預覽中...' : '👁️ 預覽文件（不消耗 token）' }}
        </button>
      </div>
    </div>

    <!-- Step 2: 預覽確認 -->
    <div v-if="currentStep === 2" class="step-content">
      <div class="preview-summary">
        <h3>文件預覽</h3>

        <div class="summary-grid">
          <div class="summary-item">
            <div class="summary-label">文件名稱</div>
            <div class="summary-value">{{ preview.filename }}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">文件大小</div>
            <div class="summary-value">{{ preview.file_size_kb?.toFixed(2) }} KB</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">總行數</div>
            <div class="summary-value">{{ preview.total_lines }}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">預估問答對</div>
            <div class="summary-value">~{{ preview.estimated_qa_pairs }} 個</div>
          </div>
        </div>

        <div class="preview-content">
          <h4>前 20 行預覽：</h4>
          <pre>{{ preview.preview_lines?.join('\n') }}</pre>
        </div>

        <div class="info-box">
          <strong>💡 提示：</strong> {{ preview.message }}
        </div>
      </div>

      <div class="actions">
        <button @click="currentStep = 1" class="btn-secondary">← 返回</button>
        <button @click="startImport" :disabled="importing" class="btn-primary">
          {{ importing ? '⏳ 開始匯入...' : '🚀 確認匯入（開始消耗 token）' }}
        </button>
      </div>
    </div>

    <!-- Step 3: 處理中 -->
    <div v-if="currentStep === 3" class="step-content">
      <div class="processing">
        <div class="spinner"></div>
        <h3>正在處理中...</h3>

        <div class="progress-bar">
          <div class="progress-fill" :style="{width: importProgress + '%'}"></div>
        </div>
        <div class="progress-text">{{ importProgress.toFixed(1) }}%</div>

        <div class="processing-stats">
          <div class="stat">
            <div class="stat-label">已處理訊息</div>
            <div class="stat-value">{{ jobStatus.processed_messages || 0 }} / {{ jobStatus.total_messages || 0 }}</div>
          </div>
          <div class="stat">
            <div class="stat-label">提取問答對</div>
            <div class="stat-value">{{ jobStatus.extracted_qa_pairs || 0 }}</div>
          </div>
          <div class="stat">
            <div class="stat-label">去重跳過</div>
            <div class="stat-value">{{ jobStatus.duplicates_skipped || 0 }}</div>
          </div>
        </div>

        <p class="hint">請保持頁面開啟，處理可能需要數分鐘...</p>
      </div>
    </div>

    <!-- Step 4: 完成 -->
    <div v-if="currentStep === 4" class="step-content">
      <div class="completion">
        <div class="success-icon">✅</div>
        <h3>匯入完成！</h3>

        <div class="result-summary">
          <div class="result-item">
            <span class="result-label">提取問答對：</span>
            <span class="result-value">{{ jobStatus.extracted_qa_pairs }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">去重跳過：</span>
            <span class="result-value">{{ jobStatus.duplicates_skipped }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">處理時間：</span>
            <span class="result-value">{{ processingTime }}</span>
          </div>
        </div>

        <div class="actions">
          <button @click="viewKnowledge" class="btn-primary">查看知識庫</button>
          <button @click="resetImport" class="btn-secondary">再次匯入</button>
        </div>
      </div>
    </div>

    <!-- 匯入歷史 -->
    <div class="import-history" v-if="importJobs.length > 0">
      <h3>匯入歷史</h3>
      <table>
        <thead>
          <tr>
            <th>文件名稱</th>
            <th>狀態</th>
            <th>問答對</th>
            <th>去重</th>
            <th>時間</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="job in importJobs" :key="job.job_id">
            <td>{{ job.filename }}</td>
            <td>
              <span class="status-badge" :class="'status-' + job.status">
                {{ getStatusLabel(job.status) }}
              </span>
            </td>
            <td>{{ job.extracted_qa_pairs }}</td>
            <td>{{ job.duplicates_skipped }}</td>
            <td>{{ formatDate(job.created_at) }}</td>
            <td>
              <button @click="deleteJob(job.job_id)" class="btn-delete btn-sm">刪除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

const API_BASE = '/rag-api/v1';

export default {
  name: 'KnowledgeImportView',

  data() {
    return {
      currentStep: 1,
      selectedFile: null,
      importMode: 'new',
      enableDeduplication: true,
      selectedVendor: null,
      vendors: [],

      previewing: false,
      preview: {},

      importing: false,
      importProgress: 0,
      jobId: null,
      jobStatus: {},

      importJobs: [],
      pollingInterval: null
    };
  },

  computed: {
    processingTime() {
      if (!this.jobStatus.created_at || !this.jobStatus.updated_at) return '-';
      const start = new Date(this.jobStatus.created_at);
      const end = new Date(this.jobStatus.updated_at);
      const seconds = Math.floor((end - start) / 1000);
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      return `${minutes}分${remainingSeconds}秒`;
    }
  },

  mounted() {
    this.loadVendors();
    this.loadImportJobs();
  },

  beforeUnmount() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
    }
  },

  methods: {
    async loadVendors() {
      try {
        const response = await axios.get(`${API_BASE}/vendors`);
        this.vendors = response.data;
      } catch (error) {
        console.error('載入業者失敗', error);
      }
    },

    async loadImportJobs() {
      try {
        const response = await axios.get(`${API_BASE}/knowledge-import/jobs`);
        this.importJobs = response.data;
      } catch (error) {
        console.error('載入匯入歷史失敗', error);
      }
    },

    handleFileSelect(event) {
      const file = event.target.files[0];
      if (file) {
        this.selectedFile = file;
      }
    },

    handleDrop(event) {
      const file = event.dataTransfer.files[0];
      if (file && file.name.endsWith('.txt')) {
        this.selectedFile = file;
      } else {
        alert('請上傳 .txt 文件');
      }
    },

    clearFile() {
      this.selectedFile = null;
      this.$refs.fileInput.value = '';
    },

    async previewFile() {
      if (!this.selectedFile) return;

      this.previewing = true;

      try {
        const formData = new FormData();
        formData.append('file', this.selectedFile);

        const response = await axios.post(
          `${API_BASE}/knowledge-import/preview`,
          formData,
          {headers: {'Content-Type': 'multipart/form-data'}}
        );

        this.preview = response.data;
        this.currentStep = 2;
      } catch (error) {
        alert('預覽失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.previewing = false;
      }
    },

    async startImport() {
      if (!this.selectedFile) return;

      this.importing = true;

      try {
        const formData = new FormData();
        formData.append('file', this.selectedFile);
        formData.append('mode', this.importMode);
        formData.append('enable_deduplication', this.enableDeduplication);
        if (this.selectedVendor) {
          formData.append('vendor_id', this.selectedVendor);
        }

        const response = await axios.post(
          `${API_BASE}/knowledge-import/upload`,
          formData,
          {headers: {'Content-Type': 'multipart/form-data'}}
        );

        this.jobId = response.data.job_id;
        this.jobStatus = response.data;
        this.currentStep = 3;

        // 開始輪詢任務狀態
        this.startPolling();
      } catch (error) {
        alert('匯入失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.importing = false;
      }
    },

    startPolling() {
      this.pollingInterval = setInterval(async () => {
        try {
          const response = await axios.get(
            `${API_BASE}/knowledge-import/jobs/${this.jobId}`
          );

          this.jobStatus = response.data;
          this.importProgress = response.data.progress;

          if (response.data.status === 'completed') {
            clearInterval(this.pollingInterval);
            this.currentStep = 4;
            this.loadImportJobs();
          } else if (response.data.status === 'failed') {
            clearInterval(this.pollingInterval);
            alert('匯入失敗：' + response.data.error_message);
            this.currentStep = 1;
          }
        } catch (error) {
          console.error('輪詢失敗', error);
        }
      }, 2000);  // 每 2 秒查詢一次
    },

    async deleteJob(jobId) {
      if (!confirm('確定要刪除這個匯入記錄嗎？')) return;

      try {
        await axios.delete(`${API_BASE}/knowledge-import/jobs/${jobId}`);
        this.loadImportJobs();
      } catch (error) {
        alert('刪除失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    resetImport() {
      this.currentStep = 1;
      this.selectedFile = null;
      this.preview = {};
      this.jobStatus = {};
      this.importProgress = 0;
      this.clearFile();
    },

    viewKnowledge() {
      this.$router.push('/knowledge');
    },

    formatFileSize(bytes) {
      if (bytes < 1024) return bytes + ' B';
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
      return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    },

    formatDate(dateString) {
      if (!dateString) return '-';
      const date = new Date(dateString);
      return date.toLocaleString('zh-TW');
    },

    getStatusLabel(status) {
      const labels = {
        pending: '等待中',
        processing: '處理中',
        completed: '已完成',
        failed: '失敗'
      };
      return labels[status] || status;
    }
  }
};
</script>

<style scoped>
.knowledge-import {
  max-width: 900px;
  margin: 0 auto;
}

.subtitle {
  color: #666;
  margin-bottom: 30px;
}

/* 步驟指示器 */
.steps {
  display: flex;
  justify-content: space-between;
  margin-bottom: 40px;
  position: relative;
}

.steps::before {
  content: '';
  position: absolute;
  top: 20px;
  left: 10%;
  right: 10%;
  height: 2px;
  background: #e0e0e0;
  z-index: 0;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  position: relative;
  z-index: 1;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #e0e0e0;
  color: #999;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-bottom: 10px;
  transition: all 0.3s;
}

.step.active .step-number {
  background: #4CAF50;
  color: white;
}

.step.completed .step-number {
  background: #2196F3;
  color: white;
}

.step-title {
  font-size: 14px;
  color: #666;
}

/* 上傳區域 */
.upload-area {
  border: 2px dashed #ccc;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  background: #fafafa;
  margin-bottom: 30px;
  transition: all 0.3s;
}

.upload-area:hover {
  border-color: #4CAF50;
  background: #f0f8f0;
}

.upload-placeholder {
  cursor: pointer;
}

.upload-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.hint {
  color: #999;
  font-size: 14px;
  margin-top: 10px;
}

.file-selected {
  padding: 20px;
  background: white;
  border-radius: 8px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.file-icon {
  font-size: 48px;
}

.file-details {
  flex: 1;
  text-align: left;
}

.file-name {
  font-weight: bold;
  margin-bottom: 5px;
}

.file-size {
  color: #666;
  font-size: 14px;
}

.btn-remove {
  background: #f44336;
  color: white;
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
}

/* 匯入選項 */
.import-options {
  background: white;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  margin-bottom: 30px;
}

.option-group {
  margin-bottom: 20px;
}

.option-group label {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 15px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 10px;
}

.option-group label:hover {
  background: #f5f5f5;
  border-color: #4CAF50;
}

.option-label {
  display: flex;
  flex-direction: column;
}

.option-label small {
  color: #666;
  margin-top: 5px;
}

/* 預覽 */
.preview-summary {
  background: white;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
  margin: 20px 0;
}

.summary-item {
  padding: 15px;
  background: #f5f5f5;
  border-radius: 8px;
}

.summary-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 5px;
}

.summary-value {
  font-size: 18px;
  font-weight: bold;
  color: #333;
}

.preview-content pre {
  background: #f5f5f5;
  padding: 15px;
  border-radius: 8px;
  overflow: auto;
  max-height: 300px;
  font-size: 12px;
  line-height: 1.6;
}

.info-box {
  background: #e3f2fd;
  padding: 15px;
  border-radius: 8px;
  border-left: 4px solid #2196F3;
  margin-top: 20px;
}

/* 處理中 */
.processing {
  text-align: center;
  padding: 40px;
}

.spinner {
  width: 60px;
  height: 60px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #4CAF50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.progress-bar {
  width: 100%;
  height: 30px;
  background: #f0f0f0;
  border-radius: 15px;
  overflow: hidden;
  margin: 20px 0;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
  transition: width 0.3s;
}

.progress-text {
  font-size: 24px;
  font-weight: bold;
  color: #4CAF50;
  margin: 10px 0;
}

.processing-stats {
  display: flex;
  justify-content: center;
  gap: 30px;
  margin-top: 30px;
}

.stat {
  text-align: center;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 5px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #333;
}

/* 完成 */
.completion {
  text-align: center;
  padding: 40px;
}

.success-icon {
  font-size: 80px;
  margin-bottom: 20px;
}

.result-summary {
  background: white;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  margin: 20px auto;
  max-width: 500px;
}

.result-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}

.result-item:last-child {
  border-bottom: none;
}

.result-label {
  color: #666;
}

.result-value {
  font-weight: bold;
  color: #4CAF50;
}

/* 匯入歷史 */
.import-history {
  margin-top: 40px;
  background: white;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
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

/* 按鈕 */
.actions {
  display: flex;
  gap: 15px;
  justify-content: center;
  margin-top: 30px;
}

.btn-primary, .btn-secondary {
  padding: 12px 30px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary {
  background: #4CAF50;
  color: white;
}

.btn-primary:hover {
  background: #45a049;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-secondary {
  background: #f0f0f0;
  color: #333;
}

.btn-secondary:hover {
  background: #e0e0e0;
}
</style>
