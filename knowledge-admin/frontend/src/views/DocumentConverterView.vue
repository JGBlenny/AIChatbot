<template>
  <div class="document-converter">
    <h1>📄 規格書轉換器</h1>
    <p class="subtitle">將 Word 規格書自動轉換為知識庫 Q&A</p>

    <!-- 步驟指示器 -->
    <div class="steps">
      <div class="step" :class="{ active: currentStep >= 1, completed: currentStep > 1 }">
        <div class="step-number">1</div>
        <div class="step-label">上傳文件</div>
      </div>
      <div class="step" :class="{ active: currentStep >= 2, completed: currentStep > 2 }">
        <div class="step-number">2</div>
        <div class="step-label">解析預覽</div>
      </div>
      <div class="step" :class="{ active: currentStep >= 3, completed: currentStep > 3 }">
        <div class="step-number">3</div>
        <div class="step-label">AI 轉換</div>
      </div>
      <div class="step" :class="{ active: currentStep >= 4 }">
        <div class="step-number">4</div>
        <div class="step-label">審核編輯</div>
      </div>
    </div>

    <!-- Step 1: 上傳文件 -->
    <div v-if="currentStep === 1" class="step-content">
      <div class="upload-area" @click="triggerFileInput" @drop.prevent="handleDrop" @dragover.prevent>
        <input
          ref="fileInput"
          type="file"
          accept=".docx,.pdf"
          @change="handleFileSelect"
          style="display: none"
        />
        <div v-if="!uploading">
          <div class="upload-icon">📄</div>
          <p>點擊或拖曳檔案到此處</p>
          <p class="upload-hint">支援格式: .docx, .pdf (最大 50MB)</p>
        </div>
        <div v-else class="uploading">
          <div class="spinner"></div>
          <p>上傳中...</p>
        </div>
      </div>

      <div v-if="jobInfo && !uploading" class="file-info">
        <h3>✅ 文件已上傳</h3>
        <p><strong>檔名:</strong> {{ jobInfo.file_name }}</p>
        <p><strong>大小:</strong> {{ (jobInfo.file_size / 1024).toFixed(1) }} KB</p>
        <p><strong>格式:</strong> {{ jobInfo.file_type.toUpperCase() }}</p>
        <button @click="nextStep" class="btn-primary">下一步：解析文件</button>
      </div>
    </div>

    <!-- Step 2: 解析預覽 -->
    <div v-if="currentStep === 2" class="step-content">
      <div v-if="parsing" class="loading">
        <div class="spinner"></div>
        <p>正在解析文件...</p>
      </div>

      <div v-else-if="jobInfo.content" class="preview-area">
        <h3>📄 文件內容預覽</h3>
        <div class="content-stats">
          <span>📊 字元數: {{ jobInfo.content.length.toLocaleString() }}</span>
          <span>📝 段落數: {{ jobInfo.content.split('\n').length }}</span>
        </div>
        <div class="content-preview">
          {{ jobInfo.content.substring(0, 2000) }}
          <span v-if="jobInfo.content.length > 2000">...</span>
        </div>

        <div class="cost-estimate" v-if="costEstimate">
          <h4>💰 預估轉換成本</h4>
          <p>Tokens: {{ costEstimate.estimated_input_tokens.toLocaleString() }}</p>
          <p>成本: ${{ costEstimate.estimated_cost_usd }}</p>
          <p class="hint">使用模型: {{ costEstimate.model }}</p>
        </div>

        <div class="actions">
          <button @click="currentStep = 1" class="btn-secondary">上一步</button>
          <button @click="nextStep" class="btn-primary">下一步：AI 轉換</button>
        </div>
      </div>
    </div>

    <!-- Step 3: AI 轉換 -->
    <div v-if="currentStep === 3" class="step-content">
      <div v-if="converting" class="loading">
        <div class="spinner"></div>
        <p>AI 正在分析並提取 Q&A...</p>
        <p class="hint">這可能需要 30-60 秒</p>
      </div>

      <div v-else-if="!converting && !jobInfo.qa_list" class="convert-prompt">
        <h3>🤖 AI 提取設定</h3>
        <p>系統將使用 AI 自動從規格書中提取使用者問題和答案</p>

        <div class="prompt-section">
          <label>
            <input type="checkbox" v-model="useCustomPrompt" />
            使用自訂提示詞（進階）
          </label>
          <textarea
            v-if="useCustomPrompt"
            v-model="customPrompt"
            placeholder="輸入自訂的提示詞..."
            rows="5"
          ></textarea>
        </div>

        <div class="actions">
          <button @click="currentStep = 2" class="btn-secondary">上一步</button>
          <button @click="startConversion" class="btn-primary">開始轉換</button>
        </div>
      </div>

      <div v-else-if="jobInfo.qa_list" class="conversion-success">
        <h3>✅ 轉換完成！</h3>
        <p>成功提取 <strong>{{ jobInfo.qa_list.length }}</strong> 個 Q&A</p>
        <button @click="nextStep" class="btn-primary">下一步：審核編輯</button>
      </div>
    </div>

    <!-- Step 4: 審核編輯 -->
    <div v-if="currentStep === 4" class="step-content">
      <h3>📝 Q&A 審核與編輯</h3>
      <p>共 {{ qaList.length }} 個項目</p>

      <div class="qa-actions">
        <button @click="addNewQA" class="btn-secondary">+ 新增 Q&A</button>
        <button @click="exportToCSV" class="btn-secondary">📥 匯出 CSV</button>
        <div class="priority-setting">
          <label>
            <input type="checkbox" v-model="defaultPriority" :true-value="1" :false-value="0" />
            預設啟用優先級（所有 Q&A 將直接啟用）
          </label>
        </div>
        <button @click="importToKnowledge" class="btn-primary">✅ 確認匯入知識庫（直接匯入）</button>
      </div>

      <div class="qa-list">
        <div v-for="(qa, index) in qaList" :key="index" class="qa-item">
          <div class="qa-header">
            <span class="qa-number">#{{ index + 1 }}</span>
            <button @click="removeQA(index)" class="btn-delete">刪除</button>
          </div>

          <div class="qa-field">
            <label>問題標題:</label>
            <input
              v-model="qa.question_summary"
              type="text"
              placeholder="簡短的問題標題"
            />
          </div>

          <div class="qa-field">
            <label>答案內容:</label>
            <textarea
              v-model="qa.content"
              rows="3"
              placeholder="完整的答案內容"
            ></textarea>
          </div>

          <div class="qa-field">
            <label>關鍵詞 (逗號分隔):</label>
            <input
              v-model="qa.keywords_str"
              type="text"
              placeholder="關鍵詞1,關鍵詞2,關鍵詞3"
              @blur="updateKeywords(qa)"
            />
          </div>

          <div class="qa-field intent-field">
            <label>推薦意圖:</label>
            <div class="intent-selection">
              <select v-model="qa.selected_intent_id" class="intent-select">
                <option :value="null">未分類</option>
                <option
                  v-for="intent in availableIntents"
                  :key="intent.id"
                  :value="intent.id"
                >
                  {{ intent.name }}
                  <span v-if="intent.id === qa.recommended_intent?.intent_id">
                    ⭐ (推薦 - {{ (qa.recommended_intent.confidence * 100).toFixed(0) }}%)
                  </span>
                </option>
              </select>

              <div v-if="qa.recommended_intent?.reasoning" class="intent-reasoning">
                💡 {{ qa.recommended_intent.reasoning }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="qaList.length === 0" class="empty-state">
        <p>尚無 Q&A 項目</p>
        <button @click="addNewQA" class="btn-primary">新增第一個 Q&A</button>
      </div>
    </div>

    <!-- 錯誤訊息 -->
    <div v-if="error" class="error-message">
      ❌ {{ error }}
    </div>
  </div>
</template>

<script>
import axios from 'axios';

const API_BASE = '/rag-api/v1';

export default {
  name: 'DocumentConverterView',
  data() {
    return {
      currentStep: 1,
      jobInfo: null,
      uploading: false,
      parsing: false,
      converting: false,
      error: null,
      costEstimate: null,
      useCustomPrompt: false,
      customPrompt: '',
      qaList: [],
      defaultPriority: 1,  // 預設優先級：1=啟用，0=停用
      availableIntents: []  // 可用的意圖列表
    };
  },
  methods: {
    triggerFileInput() {
      this.$refs.fileInput.click();
    },

    async handleFileSelect(event) {
      const file = event.target.files[0];
      if (file) {
        await this.uploadFile(file);
      }
    },

    async handleDrop(event) {
      const file = event.dataTransfer.files[0];
      if (file) {
        await this.uploadFile(file);
      }
    },

    async uploadFile(file) {
      // 驗證文件
      const validExts = ['.docx', '.pdf'];
      const fileExt = '.' + file.name.split('.').pop().toLowerCase();

      if (!validExts.includes(fileExt)) {
        this.error = `不支援的檔案格式: ${fileExt}`;
        return;
      }

      if (file.size > 50 * 1024 * 1024) {
        this.error = '檔案過大！最大限制 50MB';
        return;
      }

      this.uploading = true;
      this.error = null;

      try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await axios.post(
          `${API_BASE}/document-converter/upload`,
          formData,
          {
            headers: { 'Content-Type': 'multipart/form-data' }
          }
        );

        this.jobInfo = response.data;
        console.log('✅ 上傳成功:', this.jobInfo);

      } catch (error) {
        this.error = error.response?.data?.detail || '上傳失敗';
        console.error('上傳錯誤:', error);
      } finally {
        this.uploading = false;
      }
    },

    async nextStep() {
      if (this.currentStep === 1) {
        // 步驟 1 → 2: 解析文件
        await this.parseDocument();
      } else if (this.currentStep === 2) {
        // 步驟 2 → 3: 準備轉換
        await this.estimateCost();
        this.currentStep = 3;
      } else if (this.currentStep === 3) {
        // 步驟 3 → 4: 進入編輯
        this.prepareQAList();
        this.currentStep = 4;
      }
    },

    async parseDocument() {
      this.parsing = true;
      this.error = null;

      try {
        const response = await axios.post(
          `${API_BASE}/document-converter/${this.jobInfo.job_id}/parse`
        );

        this.jobInfo = response.data;
        this.currentStep = 2;
        console.log('✅ 解析成功');

      } catch (error) {
        this.error = error.response?.data?.detail || '解析失敗';
        console.error('解析錯誤:', error);
      } finally {
        this.parsing = false;
      }
    },

    async estimateCost() {
      try {
        const response = await axios.post(
          `${API_BASE}/document-converter/${this.jobInfo.job_id}/estimate-cost`
        );
        this.costEstimate = response.data;
      } catch (error) {
        console.error('估算成本失敗:', error);
      }
    },

    async startConversion() {
      this.converting = true;
      this.error = null;

      try {
        const response = await axios.post(
          `${API_BASE}/document-converter/${this.jobInfo.job_id}/convert`,
          {
            custom_prompt: this.useCustomPrompt ? this.customPrompt : null
          }
        );

        this.jobInfo = response.data;
        console.log(`✅ 轉換成功，提取 ${this.jobInfo.qa_list.length} 個 Q&A`);

      } catch (error) {
        this.error = error.response?.data?.detail || '轉換失敗';
        console.error('轉換錯誤:', error);
      } finally {
        this.converting = false;
      }
    },

    prepareQAList() {
      // 轉換 keywords 陣列為字串以便編輯
      // 設定 selected_intent_id 預設值為推薦的意圖
      this.qaList = this.jobInfo.qa_list.map(qa => ({
        ...qa,
        keywords_str: Array.isArray(qa.keywords) ? qa.keywords.join(',') : qa.keywords,
        selected_intent_id: qa.recommended_intent?.intent_id || null
      }));
    },

    updateKeywords(qa) {
      // 將逗號分隔的字串轉回陣列
      qa.keywords = qa.keywords_str.split(',').map(k => k.trim()).filter(k => k);
    },

    addNewQA() {
      this.qaList.push({
        question_summary: '',
        content: '',
        keywords: [],
        keywords_str: ''
      });
    },

    removeQA(index) {
      if (confirm('確定要刪除這個 Q&A 嗎？')) {
        this.qaList.splice(index, 1);
      }
    },

    async exportToCSV() {
      try {
        // 更新後端的 Q&A 列表
        await this.updateQAList();

        const response = await axios.post(
          `${API_BASE}/document-converter/${this.jobInfo.job_id}/export-csv`
        );

        // 下載 CSV
        const blob = new Blob([response.data.csv_content], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = response.data.filename;
        link.click();

        alert('✅ CSV 已匯出');
      } catch (error) {
        this.error = error.response?.data?.detail || '匯出失敗';
      }
    },

    async updateQAList() {
      // 確保所有 keywords 是陣列格式，並包含意圖資訊
      const qaListToSave = this.qaList.map(qa => ({
        question_summary: qa.question_summary,
        content: qa.content,
        keywords: Array.isArray(qa.keywords) ? qa.keywords : qa.keywords_str.split(',').map(k => k.trim()).filter(k => k),
        selected_intent_id: qa.selected_intent_id,
        recommended_intent: qa.recommended_intent
      }));

      try {
        await axios.put(
          `${API_BASE}/document-converter/${this.jobInfo.job_id}/qa-list`,
          { qa_list: qaListToSave }
        );
        console.log('✅ Q&A 列表已更新');
      } catch (error) {
        console.error('更新 Q&A 列表失敗:', error);
        throw error;
      }
    },

    async importToKnowledge() {
      const priorityText = this.defaultPriority === 1 ? '（已啟用）' : '（未啟用）';
      if (!confirm(`確定要將 ${this.qaList.length} 個 Q&A 直接匯入知識庫嗎？\n\n預設優先級：${priorityText}\n\n⚠️ 將直接加入正式知識庫，不經審核流程。`)) {
        return;
      }

      try {
        // 先更新 Q&A 列表
        await this.updateQAList();

        // 匯出為 CSV
        const response = await axios.post(
          `${API_BASE}/document-converter/${this.jobInfo.job_id}/export-csv`
        );

        // 創建 CSV Blob 並準備上傳到知識匯入 API
        const csvBlob = new Blob([response.data.csv_content], { type: 'text/csv' });
        const csvFile = new File([csvBlob], response.data.filename, { type: 'text/csv' });

        const formData = new FormData();
        formData.append('file', csvFile);
        formData.append('skip_review', 'true');  // 直接匯入知識庫，不需審核
        formData.append('default_priority', this.defaultPriority.toString());  // 預設優先級

        // 上傳到知識匯入 API
        const importResponse = await axios.post(
          `${API_BASE}/knowledge-import/upload`,
          formData
        );

        alert(`✅ 已成功將 ${this.qaList.length} 個 Q&A 直接匯入知識庫！\n\n優先級：${priorityText}\n\n知識已可立即使用於對話回應。`);

        // 重置頁面
        this.resetConverter();

      } catch (error) {
        this.error = error.response?.data?.detail || '匯入失敗';
        console.error('匯入錯誤:', error);
      }
    },

    resetConverter() {
      this.currentStep = 1;
      this.jobInfo = null;
      this.qaList = [];
      this.error = null;
      this.costEstimate = null;
    },

    async loadIntents() {
      try {
        const response = await axios.get(`${API_BASE}/intents`);
        this.availableIntents = response.data.intents;
        console.log(`✅ 載入 ${this.availableIntents.length} 個意圖`);
      } catch (error) {
        console.error('載入意圖列表失敗:', error);
        this.availableIntents = [];
      }
    }
  },

  mounted() {
    // 頁面載入時取得意圖列表
    this.loadIntents();
  }
};
</script>

<style scoped>
.document-converter {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

h1 {
  margin-bottom: 10px;
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
  left: 25%;
  right: 25%;
  height: 2px;
  background: #ddd;
  z-index: 0;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  position: relative;
  z-index: 1;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #e0e0e0;
  color: #666;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
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

.step-label {
  font-size: 14px;
  color: #666;
}

/* 上傳區域 */
.upload-area {
  border: 2px dashed #ccc;
  border-radius: 8px;
  padding: 60px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}

.upload-area:hover {
  border-color: #4CAF50;
  background: #f9f9f9;
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 10px;
}

.upload-hint {
  font-size: 14px;
  color: #999;
  margin-top: 5px;
}

/* 檔案資訊 */
.file-info {
  margin-top: 20px;
  padding: 20px;
  background: #f5f5f5;
  border-radius: 8px;
}

/* 預覽區域 */
.preview-area {
  margin-top: 20px;
}

.content-stats {
  display: flex;
  gap: 20px;
  margin: 15px 0;
  font-size: 14px;
  color: #666;
}

.content-preview {
  background: #f5f5f5;
  padding: 20px;
  border-radius: 8px;
  max-height: 400px;
  overflow-y: auto;
  white-space: pre-wrap;
  font-family: monospace;
  font-size: 12px;
  line-height: 1.6;
}

/* 成本估算 */
.cost-estimate {
  margin: 20px 0;
  padding: 15px;
  background: #fff3cd;
  border-left: 4px solid #ffc107;
  border-radius: 4px;
}

.cost-estimate h4 {
  margin-top: 0;
}

/* Q&A 列表 */
.qa-actions {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  align-items: center;
  flex-wrap: wrap;
}

.priority-setting {
  padding: 8px 15px;
  background: #e3f2fd;
  border-radius: 6px;
  border: 1px solid #2196f3;
}

.priority-setting label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #1976d2;
  font-weight: 500;
  margin: 0;
}

.priority-setting input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.qa-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.qa-item {
  padding: 20px;
  background: #f9f9f9;
  border-radius: 8px;
  border: 1px solid #ddd;
}

.qa-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 15px;
}

.qa-number {
  font-weight: bold;
  color: #2196F3;
}

.qa-field {
  margin-bottom: 10px;
}

.qa-field label {
  display: block;
  font-weight: bold;
  margin-bottom: 5px;
  font-size: 14px;
}

.qa-field input,
.qa-field textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

/* 按鈕 */
.actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.btn-primary,
.btn-secondary,
.btn-delete {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.btn-primary {
  background: #4CAF50;
  color: white;
}

.btn-primary:hover {
  background: #45a049;
}

.btn-secondary {
  background: #f0f0f0;
  color: #333;
}

.btn-secondary:hover {
  background: #e0e0e0;
}

.btn-delete {
  background: #f44336;
  color: white;
  padding: 5px 15px;
  font-size: 12px;
}

.btn-delete:hover {
  background: #da190b;
}

/* 載入動畫 */
.loading,
.uploading {
  text-align: center;
  padding: 40px;
}

.spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #4CAF50;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 錯誤訊息 */
.error-message {
  margin: 20px 0;
  padding: 15px;
  background: #ffebee;
  color: #c62828;
  border-left: 4px solid #c62828;
  border-radius: 4px;
}

/* 提示文字 */
.hint {
  font-size: 12px;
  color: #999;
  margin-top: 5px;
}

/* 空狀態 */
.empty-state {
  text-align: center;
  padding: 40px;
  color: #999;
}

/* 轉換成功 */
.conversion-success {
  text-align: center;
  padding: 40px;
}

.conversion-success h3 {
  color: #4CAF50;
  margin-bottom: 20px;
}

/* 提示詞區域 */
.prompt-section {
  margin: 20px 0;
}

.prompt-section textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  margin-top: 10px;
}

.convert-prompt {
  padding: 20px;
}

/* 意圖選擇樣式 */
.intent-field {
  margin-top: 12px;
}

.intent-selection {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.intent-select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  background-color: white;
  cursor: pointer;
}

.intent-select:focus {
  outline: none;
  border-color: #2196f3;
  box-shadow: 0 0 0 2px rgba(33, 150, 243, 0.1);
}

.intent-reasoning {
  padding: 8px 12px;
  background: #e3f2fd;
  border-left: 3px solid #2196f3;
  border-radius: 4px;
  font-size: 13px;
  color: #1565c0;
  line-height: 1.5;
}
</style>
