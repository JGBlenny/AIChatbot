<template>
  <div class="knowledge-import">
    <h2>📤 知識庫匯入</h2>

    <!-- 說明區塊 -->
    <InfoPanel :config="helpTexts.knowledgeImport" />

    <p class="subtitle">上傳知識庫文件，支援多種格式，自動提取知識並智能去重</p>

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

    <!-- Step 1: 檔案管理器 -->
    <div v-if="currentStep === 1" class="step-content">
      <!-- 檔案佇列標題 -->
      <div class="queue-header">
        <h3>📋 檔案佇列 ({{ fileQueue.length }})</h3>
        <button @click="addFiles" class="btn-primary btn-add-files">
          ➕ 添加檔案
        </button>
        <input
          ref="fileInput"
          type="file"
          multiple
          accept=".txt,.xlsx,.xls,.csv,.json"
          @change="handleFileSelect"
          style="display: none"
        />
      </div>

      <!-- 檔案清單 -->
      <div v-if="fileQueue.length > 0" class="file-queue">
        <div v-for="(fileItem, index) in fileQueue" :key="index" class="file-item">
          <div class="file-item-info">
            <div class="file-icon">
              📄
            </div>
            <div class="file-details">
              <div class="file-name">{{ fileItem.name }}</div>
              <div class="file-meta">
                <span class="file-size">{{ formatFileSize(fileItem.size) }}</span>
                <span class="file-type">{{ getFileExtension(fileItem.name) }}</span>
              </div>
            </div>
          </div>

          <div class="file-item-status">
            <!-- 狀態標記 -->
            <span v-if="fileItem.status === 'pending'" class="badge badge-gray">⏳ 待處理</span>
            <span v-if="fileItem.status === 'processing'" class="badge badge-blue">🔄 處理中</span>
            <span v-if="fileItem.status === 'completed'" class="badge badge-green">✅ 已完成</span>
            <span v-if="fileItem.status === 'error'" class="badge badge-red">❌ 失敗</span>

            <!-- 進度條（處理中時顯示） -->
            <div v-if="fileItem.status === 'processing' && fileItem.progress !== undefined" class="mini-progress">
              <div class="mini-progress-bar" :style="{width: fileItem.progress + '%'}"></div>
              <span class="mini-progress-text">{{ fileItem.progress }}%</span>
            </div>

            <!-- 結果統計（完成時顯示） -->
            <div v-if="fileItem.status === 'completed' && fileItem.result" class="file-result">
              <span class="result-stat">新增: {{ fileItem.result.added || 0 }}</span>
              <span class="result-stat">跳過: {{ fileItem.result.skipped || 0 }}</span>
            </div>

            <!-- 錯誤訊息 -->
            <div v-if="fileItem.status === 'error' && fileItem.error" class="file-error">
              {{ fileItem.error }}
            </div>
          </div>

          <div class="file-item-actions">
            <!-- 待處理：可以處理或移除 -->
            <button
              v-if="fileItem.status === 'pending'"
              @click="processSingleFile(index)"
              class="btn-small btn-primary"
              :disabled="isProcessingAny"
            >
              處理
            </button>

            <!-- 處理中：顯示取消按鈕（暫不實現取消功能） -->
            <button
              v-if="fileItem.status === 'processing'"
              class="btn-small btn-secondary"
              disabled
            >
              處理中...
            </button>

            <!-- 完成：可以查看詳情 -->
            <button
              v-if="fileItem.status === 'completed'"
              @click="viewFileResult(index)"
              class="btn-small btn-info"
            >
              詳情
            </button>

            <!-- 失敗：可以重試 -->
            <button
              v-if="fileItem.status === 'error'"
              @click="retryFile(index)"
              class="btn-small btn-warning"
              :disabled="isProcessingAny"
            >
              重試
            </button>

            <!-- 移除按鈕（處理中不能移除） -->
            <button
              v-if="fileItem.status !== 'processing'"
              @click="removeFile(index)"
              class="btn-small btn-remove"
            >
              ✕
            </button>
          </div>
        </div>
      </div>

      <!-- 空狀態提示 -->
      <div v-else class="empty-queue">
        <div class="empty-icon">📂</div>
        <p>檔案佇列為空</p>
        <p class="hint">點擊上方「➕ 添加檔案」開始上傳</p>
      </div>

      <!-- 批次操作按鈕 -->
      <div v-if="fileQueue.length > 0" class="queue-actions">
        <button
          @click="processAllFiles"
          :disabled="isProcessingAny || !hasPendingFiles"
          class="btn-primary"
        >
          🚀 處理全部待處理檔案 ({{ pendingFilesCount }})
        </button>
        <button
          @click="clearCompleted"
          :disabled="!hasCompletedFiles"
          class="btn-secondary"
        >
          🗑️ 清除已完成 ({{ completedFilesCount }})
        </button>
        <button
          @click="clearAll"
          :disabled="isProcessingAny"
          class="btn-secondary"
        >
          清空佇列
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

        <!-- 匯入選項 -->
        <div class="import-options">
          <label class="checkbox-option">
            <input type="checkbox" v-model="skipReview" />
            <span class="option-text">
              <strong>直接加入知識庫（跳過審核）</strong>
              <span class="warning-text">⚠️ 跳過審核將直接影響線上回答，請謹慎使用</span>
            </span>
          </label>

          <!-- 優先級選項（僅在跳過審核時顯示） -->
          <div v-if="skipReview" class="priority-option">
            <label class="checkbox-option">
              <input type="checkbox" v-model="enablePriority" />
              <span class="option-text">
                <strong>統一啟用優先級</strong>
                <span class="info-text">✨ 所有匯入的知識將獲得 +0.15 相似度加成</span>
              </span>
            </label>
          </div>
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
            <span class="result-value">{{ jobStatus.result?.imported || 0 }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">去重跳過：</span>
            <span class="result-value">{{ jobStatus.result?.skipped || 0 }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">處理時間：</span>
            <span class="result-value">{{ processingTime }}</span>
          </div>
        </div>

        <div class="info-box" style="margin-top: 20px;">
          <strong>⚠️ 重要提醒：</strong> 從 LINE 對話匯入的知識需要經過人工審核。
          請前往 <strong>審核中心（Review Center）</strong> 批准這些知識，才會正式加入知識庫。
        </div>

        <div class="actions">
          <button @click="goToReviewCenter" class="btn-primary">前往審核中心</button>
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
import InfoPanel from '@/components/InfoPanel.vue';
import helpTexts from '@/config/help-texts.js';

const API_BASE = '/rag-api/v1';

export default {
  name: 'KnowledgeImportView',

  components: {
    InfoPanel
  },
  data() {
    return {
      helpTexts,
      currentStep: 1,
      selectedFile: null,

      // 檔案佇列管理
      fileQueue: [],  // 檔案佇列：[{file, name, size, status, progress, result, error, jobId}]

      previewing: false,
      preview: {},

      importing: false,
      importProgress: 0,
      jobId: null,
      jobStatus: {},
      skipReview: false,  // 是否跳過審核
      enablePriority: false,  // 是否統一啟用優先級

      importJobs: [],
      pollingInterval: null,
      currentProcessingIndex: null,  // 當前處理的檔案索引
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
    },

    // 檔案佇列統計
    isProcessingAny() {
      return this.fileQueue.some(f => f.status === 'processing');
    },
    hasPendingFiles() {
      return this.fileQueue.some(f => f.status === 'pending');
    },
    hasCompletedFiles() {
      return this.fileQueue.some(f => f.status === 'completed');
    },
    pendingFilesCount() {
      return this.fileQueue.filter(f => f.status === 'pending').length;
    },
    completedFilesCount() {
      return this.fileQueue.filter(f => f.status === 'completed').length;
    }
  },

  mounted() {
    this.loadImportJobs();
  },

  beforeUnmount() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
    }
  },

  methods: {
    async loadImportJobs() {
      try {
        const response = await axios.get(`${API_BASE}/knowledge-import/jobs`);
        this.importJobs = response.data;
      } catch (error) {
        console.error('載入匯入歷史失敗', error);
      }
    },

    // ==================== 檔案佇列管理 ====================
    addFiles() {
      this.$refs.fileInput.click();
    },

    handleFileSelect(event) {
      const files = Array.from(event.target.files);
      if (files.length === 0) return;

      // 將新檔案加入佇列
      files.forEach(file => {
        // 檢查是否已存在（避免重複添加）
        const exists = this.fileQueue.some(f => f.name === file.name && f.size === file.size);
        if (!exists) {
          this.fileQueue.push({
            file: file,
            name: file.name,
            size: file.size,
            status: 'pending',  // pending, processing, completed, error
            progress: 0,
            result: null,
            error: null,
            jobId: null
          });
        }
      });

      // 清空 input，允許重複選擇相同檔案
      this.$refs.fileInput.value = '';
    },

    removeFile(index) {
      this.fileQueue.splice(index, 1);
    },

    clearCompleted() {
      this.fileQueue = this.fileQueue.filter(f => f.status !== 'completed');
    },

    clearAll() {
      if (confirm('確定要清空所有檔案嗎？')) {
        this.fileQueue = [];
      }
    },

    getFileExtension(filename) {
      return filename.split('.').pop().toUpperCase();
    },

    viewFileResult(index) {
      const fileItem = this.fileQueue[index];
      if (fileItem.result) {
        alert(`處理結果：\n\n新增知識：${fileItem.result.added || 0} 筆\n跳過重複：${fileItem.result.skipped || 0} 筆\n處理失敗：${fileItem.result.failed || 0} 筆`);
      }
    },

    retryFile(index) {
      const fileItem = this.fileQueue[index];
      fileItem.status = 'pending';
      fileItem.error = null;
      fileItem.progress = 0;
      fileItem.result = null;
      fileItem.jobId = null;
    },

    // ==================== 批次處理邏輯 ====================
    async processSingleFile(index) {
      await this.processFileByIndex(index);
    },

    async processAllFiles() {
      // 取得所有待處理的檔案索引
      const pendingIndexes = this.fileQueue
        .map((f, i) => ({index: i, file: f}))
        .filter(item => item.file.status === 'pending')
        .map(item => item.index);

      // 逐個處理
      for (const index of pendingIndexes) {
        await this.processFileByIndex(index);
      }

      // 全部完成後顯示通知
      alert(`✅ 批次處理完成！\n\n成功：${this.completedFilesCount} 個檔案\n失敗：${this.fileQueue.filter(f => f.status === 'error').length} 個檔案`);
    },

    async processFileByIndex(index) {
      const fileItem = this.fileQueue[index];
      if (!fileItem || fileItem.status !== 'pending') return;

      this.currentProcessingIndex = index;
      fileItem.status = 'processing';
      fileItem.progress = 0;

      try {
        // 上傳檔案
        const formData = new FormData();
        formData.append('file', fileItem.file);
        formData.append('skip_review', this.skipReview);

        if (this.skipReview && this.enablePriority) {
          formData.append('default_priority', 1);
        }

        const uploadResponse = await axios.post(
          `${API_BASE}/knowledge-import/upload`,
          formData,
          {headers: {'Content-Type': 'multipart/form-data'}}
        );

        fileItem.jobId = uploadResponse.data.job_id;

        // 輪詢處理進度
        await this.pollFileProgress(index);

      } catch (error) {
        fileItem.status = 'error';
        fileItem.error = error.response?.data?.detail || error.message;
        console.error(`處理檔案 ${fileItem.name} 失敗:`, error);
      } finally {
        this.currentProcessingIndex = null;
      }
    },

    async pollFileProgress(index) {
      const fileItem = this.fileQueue[index];
      if (!fileItem || !fileItem.jobId) return;

      return new Promise((resolve) => {
        const pollInterval = setInterval(async () => {
          try {
            const response = await axios.get(
              `${API_BASE}/knowledge-import/jobs/${fileItem.jobId}`
            );

            const status = response.data.status;
            const progress = response.data.progress?.current || 0;

            fileItem.progress = progress;

            if (status === 'completed') {
              clearInterval(pollInterval);
              fileItem.status = 'completed';
              fileItem.result = {
                added: response.data.total_added || 0,
                skipped: response.data.duplicates_skipped || 0,
                failed: response.data.total_failed || 0
              };
              resolve();
            } else if (status === 'failed') {
              clearInterval(pollInterval);
              fileItem.status = 'error';
              fileItem.error = response.data.error || '未知錯誤';
              resolve();
            }
          } catch (error) {
            console.error('輪詢進度失敗:', error);
            // 繼續輪詢，不中斷
          }
        }, 2000);  // 每 2 秒查詢一次

        // 設置超時保護（10 分鐘）
        setTimeout(() => {
          clearInterval(pollInterval);
          if (fileItem.status === 'processing') {
            fileItem.status = 'error';
            fileItem.error = '處理超時（超過 10 分鐘）';
          }
          resolve();
        }, 10 * 60 * 1000);
      });
    },

    // ==================== 原有方法 ====================
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
        formData.append('enable_deduplication', true);
        formData.append('skip_review', this.skipReview);

        // 如果跳過審核且啟用優先級，傳送 priority=1
        if (this.skipReview && this.enablePriority) {
          formData.append('default_priority', 1);
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
          // Fix: Progress is nested in progress object
          this.importProgress = response.data.progress?.current || 0;

          if (response.data.status === 'completed') {
            clearInterval(this.pollingInterval);
            this.currentStep = 4;
            this.loadImportJobs();
          } else if (response.data.status === 'failed') {
            clearInterval(this.pollingInterval);
            alert('匯入失敗：' + response.data.error);
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
      this.skipReview = false;
      this.enablePriority = false;
      this.clearFile();
    },

    viewKnowledge() {
      this.$router.push('/knowledge');
    },

    goToReviewCenter() {
      this.$router.push('/review-center');
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
  /* 寬度和內邊距由 app-main 統一管理 */
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
  background: #ff5252;
  color: white;
  border: none;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.btn-remove:hover {
  background: #ff1744;
  transform: scale(1.05);
  box-shadow: 0 3px 6px rgba(255, 23, 68, 0.3);
}

.btn-remove:active {
  transform: scale(0.95);
}

/* 匯入選項樣式已移除（說明已整合到 InfoPanel） */

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

/* 匯入選項 */
.import-options {
  margin-top: 20px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.checkbox-option {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.checkbox-option input[type="checkbox"] {
  margin-top: 3px;
  cursor: pointer;
  width: 18px;
  height: 18px;
}

.option-text {
  display: flex;
  flex-direction: column;
  gap: 5px;
  flex: 1;
}

.option-text strong {
  color: #2c3e50;
  font-size: 15px;
}

.warning-text {
  color: #e67e22;
  font-size: 13px;
  font-weight: 500;
}

.info-text {
  color: #3498db;
  font-size: 13px;
  font-weight: 500;
}

.priority-option {
  margin-top: 15px;
  padding: 12px;
  background-color: #e3f2fd;
  border-radius: 6px;
  border: 1px solid #90caf9;
}

/* ==================== 檔案佇列樣式 ==================== */
.queue-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 2px solid #e0e0e0;
}

.queue-header h3 {
  margin: 0;
  font-size: 20px;
  color: #333;
}

.btn-add-files {
  padding: 10px 20px;
  font-size: 14px;
}

.file-queue {
  background: #f9f9f9;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 20px;
}

.file-item {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 15px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 15px;
  transition: all 0.2s;
}

.file-item:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.file-item-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.file-icon {
  font-size: 28px;
  flex-shrink: 0;
}

.file-details {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-weight: 500;
  color: #333;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  display: flex;
  gap: 10px;
  margin-top: 4px;
  font-size: 12px;
  color: #666;
}

.file-type {
  padding: 2px 6px;
  background: #e3f2fd;
  border-radius: 3px;
  font-weight: 500;
}

.file-item-status {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 200px;
}

.badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.badge-gray {
  background: #f0f0f0;
  color: #666;
}

.badge-blue {
  background: #e3f2fd;
  color: #1976d2;
}

.badge-green {
  background: #e8f5e9;
  color: #4caf50;
}

.badge-red {
  background: #ffebee;
  color: #f44336;
}

.mini-progress {
  flex: 1;
  height: 20px;
  background: #f0f0f0;
  border-radius: 10px;
  overflow: hidden;
  position: relative;
}

.mini-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
  transition: width 0.3s;
}

.mini-progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 11px;
  font-weight: bold;
  color: #333;
}

.file-result {
  display: flex;
  gap: 10px;
  font-size: 12px;
}

.result-stat {
  padding: 2px 8px;
  background: #f0f0f0;
  border-radius: 4px;
  color: #666;
}

.file-error {
  flex: 1;
  font-size: 12px;
  color: #f44336;
  padding: 4px 8px;
  background: #ffebee;
  border-radius: 4px;
}

.file-item-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
}

.btn-small {
  padding: 6px 12px;
  font-size: 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.btn-small:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-small.btn-primary {
  background: #4CAF50;
  color: white;
}

.btn-small.btn-primary:hover:not(:disabled) {
  background: #45a049;
}

.btn-small.btn-secondary {
  background: #9e9e9e;
  color: white;
}

.btn-small.btn-info {
  background: #2196f3;
  color: white;
}

.btn-small.btn-info:hover:not(:disabled) {
  background: #0b7dda;
}

.btn-small.btn-warning {
  background: #ff9800;
  color: white;
}

.btn-small.btn-warning:hover:not(:disabled) {
  background: #e68900;
}

.btn-small.btn-remove {
  background: transparent;
  color: #f44336;
  border: 1px solid #f44336;
  font-weight: bold;
  min-width: 30px;
  padding: 6px;
}

.btn-small.btn-remove:hover:not(:disabled) {
  background: #f44336;
  color: white;
}

.empty-queue {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

.empty-icon {
  font-size: 60px;
  margin-bottom: 15px;
  opacity: 0.5;
}

.empty-queue p {
  margin: 8px 0;
}

.empty-queue .hint {
  font-size: 14px;
  color: #bbb;
}

.queue-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e0e0e0;
}

.queue-actions button {
  padding: 10px 20px;
}
</style>
