<template>
  <div class="knowledge-import">
    <h2>📤 知識庫匯入</h2>

    <!-- 說明區塊 -->
    <InfoPanel :config="helpTexts.knowledgeImport" />

    <p class="subtitle">上傳知識庫文件，支援多種格式，自動提取知識並智能去重</p>

    <!-- 處理流程說明 -->
    <div class="process-info">
      <div class="process-flow">
        <span class="flow-step">📤 上傳檔案</span>
        <span class="flow-arrow">→</span>
        <span class="flow-step">🤖 AI 提取知識</span>
        <span class="flow-arrow">→</span>
        <span class="flow-step">🧠 生成向量</span>
        <span class="flow-arrow">→</span>
        <span class="flow-step">📋 進入審核佇列</span>
      </div>
    </div>

    <!-- 業者選擇器 -->
    <div class="vendor-selector">
      <label for="vendor-select">
        <strong>🏢 選擇業者：</strong>
      </label>
      <select id="vendor-select" v-model="selectedVendorId" class="vendor-dropdown">
        <option :value="null">通用知識（所有業者共用）</option>
        <option v-for="vendor in vendors" :key="vendor.id" :value="vendor.id">
          {{ vendor.name }} ({{ vendor.code }})
        </option>
      </select>
      <span v-if="selectedVendorId" class="selected-vendor-badge">
        已選擇: {{ vendors.find(v => v.id === selectedVendorId)?.name }}
      </span>
    </div>

    <!-- 業態類型選擇器 -->
    <div class="business-type-selector">
      <label>
        <strong>🏷️ 選擇業態類型（可複選）：</strong>
        <span class="info-text">選擇此批知識適用的業態類型</span>
      </label>
      <div class="business-type-options">
        <label
          v-for="type in businessTypes"
          :key="type.type_value"
          class="business-type-checkbox"
          :class="{ selected: selectedBusinessTypes.includes(type.type_value) }"
        >
          <input
            type="checkbox"
            :value="type.type_value"
            v-model="selectedBusinessTypes"
          />
          <span class="type-icon">{{ type.icon }}</span>
          <div class="type-info">
            <div class="type-name">{{ type.display_name }}</div>
            <div class="type-desc">{{ type.description }}</div>
          </div>
        </label>
      </div>
      <div v-if="selectedBusinessTypes.length > 0" class="selected-types-summary">
        已選擇 {{ selectedBusinessTypes.length }} 個業態：
        <span v-for="typeValue in selectedBusinessTypes" :key="typeValue" class="type-tag">
          {{ businessTypes.find(t => t.type_value === typeValue)?.display_name }}
        </span>
      </div>
    </div>

    <!-- 匯入選項（佇列級別） -->
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

      <!-- 質量評估選項 -->
      <label class="checkbox-option quality-eval-option">
        <input type="checkbox" v-model="enableQualityEvaluation" />
        <span class="option-text">
          <strong>啟用質量評估</strong>
          <span class="info-text">⚡ 大量資料建議關閉以加速匯入（關閉後不會進行問答品質檢查）</span>
        </span>
      </label>

      <!-- 去重選項 -->
      <label class="checkbox-option dedup-option">
        <input type="checkbox" v-model="enableDeduplication" />
        <span class="option-text">
          <strong>啟用去重檢查</strong>
          <span class="info-text">⚠️ 如果資料已在審核佇列中，建議關閉以強制匯入</span>
        </span>
      </label>
    </div>

    <!-- 檔案管理器 -->
    <div class="step-content">
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
              <div class="file-name">
                {{ fileItem.name }}
                <!-- 來源類型 badge -->
                <span v-if="fileItem.sourceDescription" class="source-badge"
                      :class="{
                        'source-system': fileItem.sourceType === 'system_export',
                        'source-chat': fileItem.sourceType === 'line_chat',
                        'source-external': fileItem.sourceType === 'external_file'
                      }">
                  {{ fileItem.sourceDescription }}
                </span>
              </div>
              <div class="file-meta">
                <span class="file-size">{{ formatFileSize(fileItem.size) }}</span>
                <span class="file-type">{{ getFileExtension(fileItem.name) }}</span>
              </div>
            </div>
          </div>

          <div class="file-item-status">
            <!-- 狀態標記 -->
            <span v-if="fileItem.status === 'pending'" class="badge badge-gray">⏳ 待處理</span>
            <span v-if="fileItem.status === 'error'" class="badge badge-red">❌ 失敗</span>

            <!-- 處理中：顯示階段指示器和進度 -->
            <div v-if="fileItem.status === 'processing'" class="processing-stages">
              <div class="stage-indicators">
                <span class="stage-icon" :class="{active: fileItem.stage === 'uploading', completed: isStageCompleted(fileItem.stage, 'uploading')}">
                  📤 上傳
                </span>
                <span class="stage-icon" :class="{active: fileItem.stage === 'extracting', completed: isStageCompleted(fileItem.stage, 'extracting')}">
                  🤖 提取
                </span>
                <span class="stage-icon" :class="{active: fileItem.stage === 'embedding', completed: isStageCompleted(fileItem.stage, 'embedding')}">
                  🧠 向量化
                </span>
                <span class="stage-icon" :class="{active: fileItem.stage === 'saving', completed: isStageCompleted(fileItem.stage, 'saving')}">
                  💾 儲存
                </span>
              </div>
              <!-- 🎯 改進：更大更明顯的進度條 -->
              <div class="enhanced-progress">
                <div class="progress-header">
                  <span class="progress-stage-label">
                    {{ getStageLabel(fileItem.stage) }}
                  </span>
                  <span class="progress-percentage">{{ fileItem.progress || 0 }}%</span>
                </div>
                <div class="progress-bar-container">
                  <div class="progress-bar-bg">
                    <div
                      class="progress-bar-fill"
                      :class="{'progress-pulsing': fileItem.progress > 0 && fileItem.progress < 100}"
                      :style="{width: (fileItem.progress || 0) + '%'}"
                    >
                      <div class="progress-bar-shine"></div>
                    </div>
                  </div>
                </div>
                <!-- 📊 顯示詳細進度資訊 -->
                <div v-if="fileItem.progressDetail" class="progress-detail">
                  處理進度: {{ fileItem.progressDetail.current || 0 }} / {{ fileItem.progressDetail.total || 0 }}
                </div>
              </div>
            </div>

            <!-- 完成：顯示簡潔標記 -->
            <span v-if="fileItem.status === 'completed'" class="badge badge-green">✅ 已完成</span>

            <!-- 結果統計（完成時顯示） -->
            <div v-if="fileItem.status === 'completed' && fileItem.result" class="file-result">
              <!-- 審核模式：顯示詳細統計 -->
              <template v-if="fileItem.result.mode === 'review_queue'">
                <span class="result-stat result-success">
                  ✅ 待審核: {{ fileItem.result.pending_review || 0 }}
                </span>
                <span v-if="fileItem.result.auto_rejected > 0" class="result-stat result-rejected">
                  🚫 自動拒絕: {{ fileItem.result.auto_rejected }}
                </span>
                <span v-if="fileItem.result.test_scenarios_created > 0" class="result-stat result-info">
                  📝 測試情境: {{ fileItem.result.test_scenarios_created }}
                </span>
                <button @click="goToReviewCenter" class="btn-goto-review">
                  前往審核中心 →
                </button>
              </template>

              <!-- 直接匯入模式 -->
              <template v-else-if="fileItem.result.mode === 'direct_import'">
                <span class="result-stat result-success">
                  ✅ 已加入知識庫: {{ fileItem.result.imported || 0 }}
                </span>
                <span v-if="fileItem.result.skipped > 0" class="result-stat result-skipped">
                  ⏭️ 跳過: {{ fileItem.result.skipped }}
                </span>
              </template>

              <!-- 測試情境模式 -->
              <template v-else-if="fileItem.result.mode === 'test_scenarios'">
                <span class="result-stat">
                  新增測試情境: {{ fileItem.result.added || 0 }}
                </span>
                <span class="result-stat">跳過: {{ fileItem.result.skipped || 0 }}</span>
              </template>

              <!-- 直接模式（後端返回 "direct"） -->
              <template v-else-if="fileItem.result.mode === 'direct'">
                <span class="result-stat result-success">
                  ✅ 已加入知識庫: {{ fileItem.result.imported || 0 }}
                </span>
                <span v-if="fileItem.result.test_scenarios_created > 0" class="result-stat result-info">
                  📝 測試情境: {{ fileItem.result.test_scenarios_created }}
                </span>
                <span v-if="fileItem.result.skipped > 0" class="result-stat result-skipped">
                  ⏭️ 跳過: {{ fileItem.result.skipped }}
                </span>
              </template>

              <!-- 舊格式兼容 -->
              <template v-else>
                <span class="result-stat">
                  新增{{ fileItem.result.type || '知識' }}: {{ fileItem.result.added || 0 }}
                </span>
                <span class="result-stat">跳過: {{ fileItem.result.skipped || 0 }}</span>
              </template>

              <!-- 展開/折疊詳情按鈕 -->
              <button
                v-if="fileItem.result.items && fileItem.result.items.length > 0"
                @click="toggleFileDetails(index)"
                class="btn-details-toggle"
              >
                {{ fileItem.showDetails ? '▲ 收起' : '▼ 詳情' }}
              </button>
            </div>

            <!-- 展開的詳細結果（測試情境列表） -->
            <div v-if="fileItem.status === 'completed' && fileItem.showDetails && fileItem.result?.items?.length > 0" class="file-details-expanded">
              <div class="details-header">創建的測試情境：</div>
              <ul class="scenario-list">
                <li v-for="(item, idx) in fileItem.result.items" :key="item.id" class="scenario-item">
                  <span class="scenario-number">{{ idx + 1 }}.</span>
                  <span class="scenario-question">{{ item.question }}</span>
                  <span class="scenario-id">(ID: {{ item.id }})</span>
                </li>
              </ul>
            </div>

            <!-- 錯誤訊息 -->
            <div v-if="fileItem.status === 'error' && fileItem.error" class="file-error">
              {{ fileItem.error }}
            </div>
          </div>

          <!-- 待確認：顯示測試情境列表供用戶選擇 -->
          <div v-if="fileItem.status === 'awaiting_confirmation' && fileItem.scenarios" class="scenario-confirmation">
            <div class="confirmation-header">
              <span class="badge badge-warning">⏳ 待確認</span>
              <span class="confirmation-title">請勾選要創建的測試情境（共 {{ fileItem.scenarios.length }} 個）</span>
            </div>

            <div class="scenarios-selection">
              <div class="selection-toolbar">
                <button @click="selectAllScenarios(index)" class="btn-link">全選</button>
                <span class="separator">|</span>
                <button @click="deselectAllScenarios(index)" class="btn-link">全不選</button>
                <span class="selected-count">已選: {{ fileItem.selectedScenarios?.length || 0 }} / {{ fileItem.scenarios.length }}</span>
              </div>

              <div class="scenarios-list">
                <div v-for="(scenario, sIdx) in fileItem.scenarios" :key="sIdx" class="scenario-checkbox-item">
                  <input
                    type="checkbox"
                    :id="`scenario-${index}-${sIdx}`"
                    :value="sIdx"
                    v-model="fileItem.selectedScenarios"
                  />
                  <label :for="`scenario-${index}-${sIdx}`" class="scenario-label">
                    <span class="scenario-index">{{ sIdx + 1 }}.</span>
                    <span class="scenario-question-text">{{ scenario.question }}</span>
                    <span class="scenario-difficulty badge badge-{{ scenario.difficulty }}">{{ scenario.difficulty }}</span>
                  </label>
                </div>
              </div>
            </div>
          </div>

          <!-- 待處理：顯示預覽確認區塊 -->
          <div v-if="fileItem.status === 'pending' && fileItem.sourceDescription" class="file-preview-confirm">
            <div class="preview-info">
              <div class="preview-row">
                <span class="preview-label">📋 檔案來源：</span>
                <span class="preview-value">{{ fileItem.sourceDescription }}</span>
              </div>
              <div v-if="fileItem.sourceType === 'line_chat'" class="preview-warning">
                💬 對話記錄將只創建測試情境，不會生成知識（不經過提取知識、生成向量階段）
              </div>
              <div v-else-if="fileItem.importSource === 'system_export' && skipReview" class="preview-tip">
                ✅ 系統匯出檔案 + 跳過審核 = 直接匯入知識庫
              </div>
              <div v-else-if="fileItem.importSource === 'system_export'" class="preview-tip">
                ℹ️ 系統匯出檔案，建議勾選「直接加入知識庫」跳過審核
              </div>
              <div v-else class="preview-tip">
                ℹ️ 外部檔案，建議進入審核佇列由人工確認
              </div>
            </div>
          </div>

          <div class="file-item-actions">
            <!-- 待確認：可以確認創建或取消 -->
            <button
              v-if="fileItem.status === 'awaiting_confirmation'"
              @click="confirmScenarios(index)"
              class="btn-small btn-success"
              :disabled="!fileItem.selectedScenarios || fileItem.selectedScenarios.length === 0"
            >
              ✓ 確認創建 ({{ fileItem.selectedScenarios?.length || 0 }})
            </button>

            <!-- 待處理：可以處理或移除 -->
            <button
              v-if="fileItem.status === 'pending'"
              @click="processSingleFile(index)"
              class="btn-small btn-primary"
              :disabled="isProcessingAny"
            >
              ✓ 確認處理
            </button>

            <!-- 處理中：顯示取消按鈕（暫不實現取消功能） -->
            <button
              v-if="fileItem.status === 'processing'"
              class="btn-small btn-secondary"
              disabled
            >
              處理中...
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

      // 業者選擇
      vendors: [],
      selectedVendorId: null,

      // 業態類型選擇
      businessTypes: [],
      selectedBusinessTypes: [],

      // 檔案佇列管理
      fileQueue: [],  // 檔案佇列：[{file, name, size, status, progress, result, error, jobId, stage}]

      skipReview: false,  // 是否跳過審核
      enablePriority: false,  // 是否統一啟用優先級
      enableQualityEvaluation: true,  // 是否啟用質量評估（預設啟用）
      enableDeduplication: true,  // 是否啟用去重（預設啟用）

      importJobs: [],
      currentProcessingIndex: null,  // 當前處理的檔案索引
    };
  },

  computed: {
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
    this.loadVendors();
    this.loadBusinessTypes();
    this.loadImportJobs();
  },

  methods: {
    async loadVendors() {
      try {
        const response = await axios.get(`${API_BASE}/vendors`);
        this.vendors = response.data;
      } catch (error) {
        console.error('載入業者失敗', error);
        alert('載入業者失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    async loadBusinessTypes() {
      try {
        const response = await axios.get(`${API_BASE}/business-types-config`);
        this.businessTypes = response.data.business_types || [];
      } catch (error) {
        console.error('載入業態類型失敗', error);
        // 不顯示錯誤提示，因為業態類型是可選的
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
          const newFile = {
            file: file,
            name: file.name,
            size: file.size,
            status: 'pending',  // pending, processing, completed, error
            progress: 0,
            result: null,
            error: null,
            jobId: null,
            stage: null,  // uploading, extracting, embedding, saving
            sourceType: null,  // 來源類型
            sourceDescription: null,  // 來源描述
            showDetails: false  // 詳情展開狀態
          };
          this.fileQueue.push(newFile);

          // 異步獲取預覽資訊（不阻塞）
          this.fetchPreviewInfo(this.fileQueue.length - 1);
        }
      });

      // 清空 input，允許重複選擇相同檔案
      this.$refs.fileInput.value = '';
    },

    // 判斷階段是否已完成
    isStageCompleted(currentStage, checkStage) {
      const stages = ['uploading', 'extracting', 'embedding', 'saving'];
      const currentIndex = stages.indexOf(currentStage);
      const checkIndex = stages.indexOf(checkStage);
      return currentIndex > checkIndex;
    },

    // 🎯 新增：獲取階段的中文標籤
    getStageLabel(stage) {
      const stageLabels = {
        'uploading': '正在上傳檔案...',
        'extracting': '正在提取知識內容...',
        'embedding': '正在生成向量嵌入...',
        'saving': '正在儲存到資料庫...',
        'processing': '正在處理...'
      };
      return stageLabels[stage] || '處理中...';
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

    toggleFileDetails(index) {
      const fileItem = this.fileQueue[index];
      if (fileItem) {
        // 切換展開/折疊狀態
        fileItem.showDetails = !fileItem.showDetails;
      }
    },

    selectAllScenarios(index) {
      const fileItem = this.fileQueue[index];
      if (fileItem && fileItem.scenarios) {
        fileItem.selectedScenarios = fileItem.scenarios.map((s, idx) => idx);
      }
    },

    deselectAllScenarios(index) {
      const fileItem = this.fileQueue[index];
      if (fileItem) {
        fileItem.selectedScenarios = [];
      }
    },

    async confirmScenarios(index) {
      const fileItem = this.fileQueue[index];
      if (!fileItem || !fileItem.jobId || !fileItem.selectedScenarios || fileItem.selectedScenarios.length === 0) {
        alert('請至少選擇一個測試情境');
        return;
      }

      if (!confirm(`確定要創建 ${fileItem.selectedScenarios.length} 個測試情境嗎？`)) {
        return;
      }

      try {
        fileItem.status = 'processing';
        fileItem.stage = 'saving';
        fileItem.progress = 50;

        const response = await axios.post(
          `${API_BASE}/knowledge-import/jobs/${fileItem.jobId}/confirm`,
          {
            selected_indices: fileItem.selectedScenarios
          }
        );

        // 創建完成，更新為完成狀態
        fileItem.status = 'completed';
        fileItem.stage = null;
        fileItem.progress = 100;

        const resultData = response.data;
        fileItem.result = {
          added: resultData.created || 0,
          skipped: resultData.skipped || 0,
          failed: resultData.errors || 0,
          mode: 'test_scenarios',
          type: '測試情境',
          items: resultData.items || []
        };

        alert(`✅ 測試情境創建完成！\n\n新建: ${resultData.created}\n跳過: ${resultData.skipped}\n失敗: ${resultData.errors}`);
      } catch (error) {
        fileItem.status = 'error';
        fileItem.stage = null;
        fileItem.error = error.response?.data?.detail || error.message;
        alert('創建測試情境失敗：' + fileItem.error);
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
      const fileItem = this.fileQueue[index];
      // 只處理 pending 狀態的檔案
      if (!fileItem || fileItem.status !== 'pending') {
        console.warn(`檔案 ${index} 狀態不是 pending (${fileItem?.status})，跳過處理`);
        return;
      }
      await this.processFileByIndex(index);
    },

    async processAllFiles() {
      // 取得所有待處理的檔案索引（快照，避免處理過程中狀態變化）
      const pendingIndexes = this.fileQueue
        .map((f, i) => ({index: i, file: f}))
        .filter(item => item.file.status === 'pending')
        .map(item => item.index);

      if (pendingIndexes.length === 0) {
        alert('沒有待處理的檔案');
        return;
      }

      console.log(`開始批次處理 ${pendingIndexes.length} 個檔案:`, pendingIndexes);

      // 逐個處理
      for (const index of pendingIndexes) {
        // 再次檢查狀態（避免處理過程中狀態被改變）
        const fileItem = this.fileQueue[index];
        if (fileItem && fileItem.status === 'pending') {
          await this.processFileByIndex(index);
        } else {
          console.warn(`檔案 ${index} 狀態已變更 (${fileItem?.status})，跳過`);
        }
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
      fileItem.stage = 'uploading';  // 初始階段

      try {
        // 上傳檔案
        const formData = new FormData();
        formData.append('file', fileItem.file);
        formData.append('skip_review', this.skipReview);
        formData.append('enable_quality_evaluation', this.enableQualityEvaluation);
        formData.append('enable_deduplication', this.enableDeduplication);

        // 添加業者 ID（如果已選擇）
        if (this.selectedVendorId) {
          formData.append('vendor_id', this.selectedVendorId);
        }

        // 添加業態類型（如果已選擇）
        if (this.selectedBusinessTypes.length > 0) {
          formData.append('business_types', JSON.stringify(this.selectedBusinessTypes));
        }

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
            const progressData = response.data.progress || {};

            // 更新進度和階段
            fileItem.progress = progressData.current || 0;
            fileItem.stage = progressData.stage || 'uploading';  // 從後端獲取階段

            // 🎯 保存詳細進度資訊（current/total）
            if (progressData.total) {
              fileItem.progressDetail = {
                current: progressData.current || 0,
                total: progressData.total || 100
              };
            }

            if (status === 'awaiting_confirmation') {
              // 等待用戶確認測試情境
              clearInterval(pollInterval);
              fileItem.status = 'awaiting_confirmation';
              fileItem.stage = null;

              const resultData = response.data.result || {};
              fileItem.scenarios = resultData.scenarios || [];
              fileItem.selectedScenarios = fileItem.scenarios.map((s, idx) => idx);  // 預設全選

              console.log(`📝 待確認: ${fileItem.scenarios.length} 個測試情境`);
              resolve();
            } else if (status === 'completed') {
              clearInterval(pollInterval);
              fileItem.status = 'completed';
              fileItem.stage = null;  // 完成後清除階段

              // 處理不同模式的結果格式
              const resultData = response.data.result || {};

              // 直接使用後端返回的完整數據結構
              fileItem.result = {
                mode: resultData.mode || 'unknown',
                // 審核模式的字段
                pending_review: resultData.pending_review || 0,
                auto_rejected: resultData.auto_rejected || 0,
                test_scenarios_created: resultData.test_scenarios_created || 0,
                imported: resultData.imported || 0,
                total: resultData.total || 0,
                skipped: resultData.skipped || 0,
                errors: resultData.errors || 0,
                // 測試情境模式的字段
                added: resultData.created || resultData.added || 0,
                failed: resultData.failed || 0,
                items: resultData.items || [],
                // 舊格式兼容
                type: resultData.mode === 'test_scenarios' ? '測試情境' : '知識'
              };

              resolve();
            } else if (status === 'failed') {
              clearInterval(pollInterval);
              fileItem.status = 'error';
              fileItem.stage = null;
              fileItem.error = response.data.error || '未知錯誤';
              resolve();
            }
          } catch (error) {
            console.error('輪詢進度失敗:', error);
            // 繼續輪詢，不中斷
          }
        }, 2000);  // 每 2 秒查詢一次

        // 設置超時保護（60 分鐘）- 大批量資料需要更長時間
        setTimeout(() => {
          clearInterval(pollInterval);
          if (fileItem.status === 'processing') {
            fileItem.status = 'error';
            fileItem.error = '處理超時（超過 60 分鐘）';
          }
          resolve();
        }, 60 * 60 * 1000);
      });
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
    },

    // 獲取預覽資訊（異步，不阻塞上傳）
    async fetchPreviewInfo(index) {
      const fileItem = this.fileQueue[index];
      if (!fileItem) return;

      try {
        const formData = new FormData();
        formData.append('file', fileItem.file);

        const response = await axios.post(
          `${API_BASE}/knowledge-import/preview`,
          formData,
          { headers: { 'Content-Type': 'multipart/form-data' } }
        );

        // 更新來源類型資訊
        fileItem.sourceType = response.data.source_type;
        fileItem.sourceDescription = response.data.detected_source_description;
      } catch (error) {
        console.error('獲取預覽資訊失敗:', error);
        // 失敗不影響匯入流程，靜默處理
      }
    },

    // 跳轉到審核中心
    goToReviewCenter() {
      this.$router.push('/review-center');
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
  margin-bottom: 20px;
}

/* 處理流程說明 */
.process-info {
  background: #f8f9fa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 25px;
}

.process-flow {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 12px;
}

.flow-step {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  padding: 8px 12px;
  background: white;
  border: 1px solid #d0d0d0;
  border-radius: 6px;
  white-space: nowrap;
}

.flow-arrow {
  color: #666;
  font-size: 16px;
  font-weight: bold;
}

/* 業者選擇器 */
.vendor-selector {
  margin-top: 20px;
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f0f8ff;
  border: 1px solid #b0d4f1;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 15px;
}

.vendor-selector label {
  color: #2c3e50;
  font-size: 15px;
  margin: 0;
}

.vendor-dropdown {
  flex: 1;
  max-width: 400px;
  padding: 10px 15px;
  font-size: 14px;
  border: 1px solid #c0d4e8;
  border-radius: 6px;
  background-color: white;
  cursor: pointer;
  transition: all 0.3s;
}

.vendor-dropdown:hover {
  border-color: #4CAF50;
}

.vendor-dropdown:focus {
  outline: none;
  border-color: #4CAF50;
  box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.1);
}

.selected-vendor-badge {
  padding: 6px 12px;
  background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
  color: white;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 2px 4px rgba(76, 175, 80, 0.3);
}

/* 業態類型選擇器 */
.business-type-selector {
  margin-top: 20px;
  margin-bottom: 20px;
  padding: 20px;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 12px;
  border: 2px solid #dee2e6;
}

.business-type-selector > label {
  display: block;
  color: #2c3e50;
  font-size: 15px;
  margin-bottom: 15px;
}

.business-type-selector .info-text {
  margin-left: 8px;
  color: #6c757d;
  font-size: 13px;
  font-weight: normal;
}

.business-type-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 12px;
  margin-bottom: 15px;
}

.business-type-checkbox {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px;
  background: white;
  border: 2px solid #e0e0e0;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s;
}

.business-type-checkbox:hover {
  border-color: #4CAF50;
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.2);
}

.business-type-checkbox.selected {
  background: linear-gradient(135deg, #e8f5e9 0%, #f1f8f4 100%);
  border-color: #4CAF50;
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
}

.business-type-checkbox input[type="checkbox"] {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

.type-icon {
  font-size: 32px;
  line-height: 1;
}

.type-info {
  flex: 1;
}

.type-name {
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 4px;
}

.type-desc {
  font-size: 13px;
  color: #6c757d;
  line-height: 1.4;
}

.selected-types-summary {
  padding: 12px 15px;
  background: white;
  border-radius: 8px;
  border: 1px solid #4CAF50;
  color: #2c3e50;
  font-size: 14px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.type-tag {
  display: inline-block;
  padding: 4px 10px;
  background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
  color: white;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
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

.quality-eval-option {
  margin-top: 15px;
  padding: 12px;
  background-color: #fff9e6;
  border-radius: 6px;
  border: 1px solid #ffe066;
}

.dedup-option {
  margin-top: 15px;
  padding: 12px;
  background-color: #ffe6e6;
  border-radius: 6px;
  border: 1px solid #ffb3b3;
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

/* 處理階段指示器 */
.processing-stages {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stage-indicators {
  display: flex;
  gap: 6px;
  align-items: center;
}

.stage-icon {
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 4px;
  background: #f0f0f0;
  color: #999;
  white-space: nowrap;
  transition: all 0.3s;
  border: 1px solid #e0e0e0;
}

.stage-icon.active {
  background: #e3f2fd;
  color: #1976d2;
  border-color: #90caf9;
  font-weight: 500;
  box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.1);
}

.stage-icon.completed {
  background: #e8f5e9;
  color: #4caf50;
  border-color: #a5d6a7;
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

/* 🎯 改進的進度顯示 */
.enhanced-progress {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 300px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.progress-stage-label {
  font-weight: 500;
  color: #1976d2;
  font-size: 13px;
}

.progress-percentage {
  font-weight: 600;
  color: #2e7d32;
  font-size: 15px;
}

.progress-bar-container {
  width: 100%;
}

.progress-bar-bg {
  height: 32px;
  background: #e3f2fd;
  border-radius: 16px;
  overflow: hidden;
  position: relative;
  border: 2px solid #90caf9;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #1976d2 0%, #42a5f5 50%, #64b5f6 100%);
  transition: width 0.5s ease-out;
  position: relative;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(25, 118, 210, 0.3);
}

.progress-bar-fill.progress-pulsing {
  animation: progress-pulse 2s ease-in-out infinite;
}

@keyframes progress-pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.85;
  }
}

.progress-bar-shine {
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0) 0%,
    rgba(255, 255, 255, 0.3) 50%,
    rgba(255, 255, 255, 0) 100%
  );
  animation: progress-shine 2s ease-in-out infinite;
}

@keyframes progress-shine {
  0% {
    left: -100%;
  }
  100% {
    left: 200%;
  }
}

.progress-detail {
  font-size: 12px;
  color: #666;
  text-align: right;
}

/* 保留舊的 mini-progress 樣式以防需要回退 */
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
  padding: 4px 10px;
  background: #f0f0f0;
  border-radius: 4px;
  color: #666;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.result-stat.result-success {
  background: #e8f5e9;
  color: #2e7d32;
  border: 1px solid #a5d6a7;
}

.result-stat.result-rejected {
  background: #ffebee;
  color: #c62828;
  border: 1px solid #ef9a9a;
}

.result-stat.result-info {
  background: #e3f2fd;
  color: #1565c0;
  border: 1px solid #90caf9;
}

.result-stat.result-skipped {
  background: #fff3e0;
  color: #e65100;
  border: 1px solid #ffcc80;
}

.btn-goto-review {
  padding: 6px 14px;
  font-size: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
  margin-left: 8px;
}

.btn-goto-review:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
}

.btn-goto-review:active {
  transform: translateY(0);
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
/* 來源類型 badge 樣式 */
.source-badge {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  vertical-align: middle;
}

.source-badge.source-system {
  background: #d4edda;
  color: #155724;
}

.source-badge.source-chat {
  background: #fff3cd;
  color: #856404;
}

.source-badge.source-external {
  background: #d1ecf1;
  color: #0c5460;
}

/* 預覽確認區塊樣式 */
.file-preview-confirm {
  margin-top: 12px;
  padding: 12px;
  background: #f8f9fa;
  border-left: 3px solid #007bff;
  border-radius: 4px;
}

.preview-info {
  font-size: 13px;
}

.preview-row {
  margin-bottom: 8px;
}

.preview-label {
  font-weight: 600;
  color: #495057;
}

.preview-value {
  color: #212529;
  margin-left: 4px;
}

.preview-warning {
  margin-top: 8px;
  padding: 8px;
  background: #fff3cd;
  border-left: 3px solid #ffc107;
  border-radius: 3px;
  color: #856404;
  font-size: 12px;
}

.preview-tip {
  margin-top: 8px;
  padding: 8px;
  background: #e7f3ff;
  border-left: 3px solid #007bff;
  border-radius: 3px;
  color: #004085;
  font-size: 12px;
}

/* 測試情境確認區塊 */
.scenario-confirmation {
  margin-top: 12px;
  padding: 16px;
  background: #fffbf0;
  border: 2px solid #ffc107;
  border-radius: 6px;
}

.confirmation-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ffe599;
}

.confirmation-title {
  font-weight: 600;
  color: #856404;
  font-size: 14px;
}

.scenarios-selection {
  margin-top: 12px;
}

.selection-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: white;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
}

.btn-link {
  background: none;
  border: none;
  color: #007bff;
  cursor: pointer;
  font-size: 13px;
  padding: 0;
  text-decoration: underline;
}

.btn-link:hover {
  color: #0056b3;
}

.separator {
  color: #ccc;
}

.selected-count {
  margin-left: auto;
  font-size: 13px;
  font-weight: 600;
  color: #28a745;
}

.scenarios-list {
  max-height: 400px;
  overflow-y: auto;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 8px;
}

.scenario-checkbox-item {
  display: flex;
  align-items: center;
  padding: 8px;
  margin-bottom: 4px;
  border-radius: 4px;
  transition: background 0.2s;
}

.scenario-checkbox-item:hover {
  background: #f8f9fa;
}

.scenario-checkbox-item input[type="checkbox"] {
  margin-right: 10px;
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.scenario-label {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  cursor: pointer;
  font-size: 13px;
}

.scenario-index {
  color: #6c757d;
  font-weight: 600;
  min-width: 30px;
}

.scenario-question-text {
  flex: 1;
  color: #212529;
}

.scenario-difficulty {
  font-size: 11px;
  padding: 3px 8px;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #218838;
}

.btn-success:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 詳情展開/折疊按鈕 */
.btn-details-toggle {
  padding: 2px 10px;
  font-size: 11px;
  background: #f0f0f0;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  color: #666;
  margin-left: 8px;
}

.btn-details-toggle:hover {
  background: #e0e0e0;
  color: #333;
}

/* 展開的詳情區域 */
.file-details-expanded {
  margin-top: 8px;
  padding: 12px;
  background: #f8f9fa;
  border-left: 3px solid #28a745;
  border-radius: 4px;
  font-size: 13px;
}

.details-header {
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.scenario-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.scenario-item {
  padding: 6px 0;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  align-items: center;
  gap: 8px;
}

.scenario-item:last-child {
  border-bottom: none;
}

.scenario-number {
  color: #6c757d;
  font-weight: 600;
  min-width: 25px;
}

.scenario-question {
  color: #2c3e50;
  flex: 1;
}

.scenario-id {
  color: #999;
  font-size: 11px;
}
</style>
