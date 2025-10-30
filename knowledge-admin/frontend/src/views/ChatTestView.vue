<template>
  <div class="chat-test-view">
    <h2>💬 Chat API 測試</h2>

    <!-- 模式與業者選擇器 -->
    <div class="vendor-selector">
      <div class="selector-row">
        <div class="selector-group">
          <label>測試模式：</label>
          <select v-model="chatMode" @change="onModeChange" class="mode-select">
            <option value="tenant">🏠 B2C - 租客對業者 (tenant)</option>
            <option value="customer_service">🏢 B2B - 業者對我們 (customer_service)</option>
          </select>
        </div>

        <div class="selector-group">
          <label>選擇業者：</label>
          <select v-model="selectedVendorId" @change="loadVendorInfo">
            <option value="">請選擇業者...</option>
            <option v-for="vendor in vendors" :key="vendor.id" :value="vendor.id">
              {{ vendor.name }} ({{ vendor.code }})
            </option>
          </select>
        </div>

        <button @click="loadVendors" class="btn-secondary">
          🔄 重新載入業者
        </button>
      </div>

      <!-- 模式說明 -->
      <div class="mode-description">
        <span v-if="chatMode === 'tenant'" class="mode-badge b2c">
          <strong>B2C 模式：</strong>模擬租客直接使用業者提供的 AI 客服（業者的終端客戶使用）
        </span>
        <span v-else class="mode-badge b2b">
          <strong>B2B 模式：</strong>業者員工使用我們的系統查詢業務資訊（可整合租客資料與外部 API）
        </span>
      </div>
    </div>

    <!-- 業者資訊顯示 -->
    <div v-if="selectedVendor" class="vendor-info">
      <h3>業者資訊</h3>
      <div class="info-grid">
        <div><strong>代碼：</strong>{{ selectedVendor.code }}</div>
        <div><strong>名稱：</strong>{{ selectedVendor.name }}</div>
        <div><strong>業務範圍：</strong>
          <span class="scope-badge" :class="'scope-' + selectedVendor.business_scope_name">
            {{ getScopeLabel(selectedVendor.business_scope_name) }}
          </span>
        </div>
        <div><strong>訂閱方案：</strong>{{ selectedVendor.subscription_plan }}</div>
        <div><strong>狀態：</strong><span :class="selectedVendor.is_active ? 'status-active' : 'status-inactive'">
          {{ selectedVendor.is_active ? '啟用' : '停用' }}
        </span></div>
      </div>
      <div class="params-preview" v-if="vendorParams && chatMode === 'tenant'">
        <strong>業者參數：</strong>
        <span class="param-badge" v-for="(param, key) in vendorParams" :key="key">
          {{ param.display_name || key }}: {{ param.value }}
        </span>
      </div>
    </div>

    <!-- 聊天區域 -->
    <div v-if="selectedVendorId" class="chat-container">
      <!-- 訊息歷史 -->
      <div class="chat-messages" ref="messagesContainer">
        <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
          <div class="message-header">
            <span class="role-label">{{ msg.role === 'user' ? '👤 使用者' : '🤖 AI' }}</span>
            <span class="timestamp">{{ formatTime(msg.timestamp) }}</span>
          </div>
          <div class="message-content">{{ msg.content }}</div>

          <!-- 影片播放器 -->
          <div v-if="msg.role === 'assistant' && msg.metadata && msg.metadata.video_url" class="message-video">
            <video controls :src="msg.metadata.video_url" class="video-player"></video>
            <div class="video-info">
              <span v-if="msg.metadata.video_file_size">📦 {{ formatFileSize(msg.metadata.video_file_size) }}</span>
              <span v-if="msg.metadata.video_duration">⏱️ {{ msg.metadata.video_duration }}秒</span>
              <span v-if="msg.metadata.video_format">🎬 {{ msg.metadata.video_format.toUpperCase() }}</span>
            </div>
          </div>

          <!-- AI 回應的額外資訊 -->
          <div v-if="msg.role === 'assistant' && msg.metadata" class="message-metadata">
            <div class="metadata-item">
              <strong>意圖：</strong>{{ msg.metadata.intent_name }} ({{ msg.metadata.confidence?.toFixed(2) }})
            </div>
            <div v-if="msg.metadata.sources && msg.metadata.sources.length > 0" class="metadata-item">
              <strong>知識來源 ({{ msg.metadata.source_count }})：</strong>
              <div v-for="(source, idx) in msg.metadata.sources" :key="idx" class="source-item">
                <span class="scope-badge" :class="`scope-${source.scope}`">{{ source.scope }}</span>
                {{ source.question_summary }}
                <span v-if="source.is_template" class="template-badge">模板</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="loading" class="message assistant">
          <div class="message-content">
            <div class="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 輸入區域 -->
      <div class="chat-input-container">
        <div class="quick-questions">
          <strong>快速測試問題：</strong>
          <button @click="sendMessage('每月繳費日期是什麼時候？')" class="btn-quick">繳費日期</button>
          <button @click="sendMessage('繳費方式有哪些？')" class="btn-quick">繳費方式</button>
          <button @click="sendMessage('逾期繳費會怎樣？')" class="btn-quick">逾期處理</button>
          <button @click="sendMessage('客服專線是多少？')" class="btn-quick">客服專線</button>
          <button @click="sendMessage('提前解約怎麼辦？')" class="btn-quick">提前解約</button>
        </div>

        <div class="input-row">
          <input
            v-model="userInput"
            @keypress.enter="handleSend"
            placeholder="輸入訊息... (按 Enter 發送)"
            :disabled="loading || !selectedVendorId"
          />
          <button @click="handleSend" :disabled="!userInput.trim() || loading" class="btn-send">
            {{ loading ? '⏳ 發送中...' : '📤 發送' }}
          </button>
          <button @click="clearMessages" class="btn-secondary">🗑️ 清空</button>
        </div>
      </div>
    </div>

    <!-- 未選擇業者提示 -->
    <div v-else class="empty-state">
      <p>👆 請先選擇一個業者開始測試</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { formatAIResponse } from '@/utils/textFormatter';
import { API_BASE_URL } from '@/config/api';

const RAG_API = `${API_BASE_URL}/rag-api`;

export default {
  name: 'ChatTestView',
  data() {
    return {
      chatMode: 'tenant', // 'tenant' or 'customer_service'
      vendors: [],
      selectedVendorId: '',
      selectedVendor: null,
      vendorParams: null,
      messages: [],
      userInput: '',
      loading: false
    };
  },
  mounted() {
    this.loadVendors();
  },
  methods: {
    async loadVendors() {
      try {
        const response = await axios.get(`${RAG_API}/v1/vendors`);
        this.vendors = response.data;
      } catch (error) {
        console.error('載入業者失敗', error);
        alert('載入業者失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    async loadVendorInfo() {
      if (!this.selectedVendorId) {
        this.selectedVendor = null;
        this.vendorParams = null;
        this.messages = [];
        return;
      }

      try {
        // 獲取業者詳情
        const vendorResponse = await axios.get(`${RAG_API}/v1/vendors/${this.selectedVendorId}`);
        this.selectedVendor = vendorResponse.data;

        // 獲取業者參數
        const testResponse = await axios.get(`${RAG_API}/v1/vendors/${this.selectedVendorId}/test`);
        this.vendorParams = testResponse.data.parameters;

        // 清空訊息
        this.messages = [];

        // 根據模式添加不同的歡迎訊息
        if (this.chatMode === 'tenant') {
          // B2C: 租客視角
          this.messages.push({
            role: 'assistant',
            content: `您好！我是 ${this.selectedVendor.name} 的 AI 客服助理，有什麼可以幫助您的嗎？`,
            timestamp: new Date()
          });
        } else {
          // B2B: 業者員工視角
          this.messages.push({
            role: 'assistant',
            content: `歡迎使用 JGB Smart Property 金箍棒智慧物管系統！\n\n當前業者：${this.selectedVendor.name}\n\n您可以查詢該業者的業務規則、參數設定等資訊。\n\n💡 提示：B2B 模式可整合租客資料與外部 API（Phase 2 功能）`,
            timestamp: new Date()
          });
        }

      } catch (error) {
        console.error('載入業者資訊失敗', error);
        alert('載入業者資訊失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    async sendMessage(text) {
      const message = text || this.userInput.trim();
      if (!message) return;

      // 添加使用者訊息
      this.messages.push({
        role: 'user',
        content: message,
        timestamp: new Date()
      });

      this.userInput = '';
      this.loading = true;

      // 滾動到底部
      this.$nextTick(() => {
        this.scrollToBottom();
      });

      try {
        // 根據模式設定用戶角色
        // B2B (customer_service) = staff (業者員工/系統商)
        // B2C (tenant) = customer (終端客戶)
        const userRole = this.chatMode === 'customer_service' ? 'staff' : 'customer';

        const response = await axios.post(`${RAG_API}/v1/message`, {
          message: message,
          vendor_id: parseInt(this.selectedVendorId),
          mode: this.chatMode,
          user_role: userRole,
          include_sources: true
        });

        // 添加 AI 回應（使用條件式格式化）
        this.messages.push({
          role: 'assistant',
          content: formatAIResponse(response.data.answer),
          timestamp: new Date(),
          metadata: {
            intent_name: response.data.intent_name,
            intent_type: response.data.intent_type,
            confidence: response.data.confidence,
            sources: response.data.sources,
            source_count: response.data.source_count,
            // 影片資訊
            video_url: response.data.video_url,
            video_file_size: response.data.video_file_size,
            video_duration: response.data.video_duration,
            video_format: response.data.video_format
          }
        });

      } catch (error) {
        console.error('發送訊息失敗', error);
        this.messages.push({
          role: 'assistant',
          content: `❌ 錯誤：${error.response?.data?.detail || error.message}`,
          timestamp: new Date()
        });
      } finally {
        this.loading = false;
        this.$nextTick(() => {
          this.scrollToBottom();
        });
      }
    },

    handleSend() {
      this.sendMessage();
    },

    onModeChange() {
      // 切換模式時清空訊息並重新載入
      this.messages = [];
      if (this.selectedVendor) {
        this.loadVendorInfo();
      }
    },

    clearMessages() {
      this.messages = [];
      if (this.selectedVendor) {
        if (this.chatMode === 'tenant') {
          this.messages.push({
            role: 'assistant',
            content: `您好！我是 ${this.selectedVendor.name} 的 AI 客服助理，有什麼可以幫助您的嗎？`,
            timestamp: new Date()
          });
        } else {
          this.messages.push({
            role: 'assistant',
            content: `歡迎使用 JGB Smart Property 金箍棒智慧物管系統！\n\n當前業者：${this.selectedVendor.name}\n\n您可以查詢該業者的業務規則、參數設定等資訊。\n\n💡 提示：B2B 模式可整合租客資料與外部 API（Phase 2 功能）`,
            timestamp: new Date()
          });
        }
      }
    },

    scrollToBottom() {
      const container = this.$refs.messagesContainer;
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    },

    formatTime(date) {
      return new Date(date).toLocaleTimeString('zh-TW', {
        hour: '2-digit',
        minute: '2-digit'
      });
    },

    getScopeLabel(scope) {
      const labels = {
        external: 'B2C 外部（包租代管）',
        internal: 'B2B 內部（系統商）'
      };
      return labels[scope] || scope;
    },

    formatFileSize(bytes) {
      if (!bytes) return '';
      const mb = bytes / (1024 * 1024);
      return mb.toFixed(2) + ' MB';
    }
  }
};
</script>

<style scoped>
.chat-test-view {
  width: 100%;
}

/* 業者選擇器 */
.vendor-selector {
  background: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  border: 1px solid #ddd;
}

.selector-row {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
  margin-bottom: 15px;
}

.selector-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.selector-group label {
  font-weight: bold;
  white-space: nowrap;
}

.vendor-selector select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  min-width: 250px;
}

.mode-select {
  min-width: 320px;
  font-weight: 500;
}

.mode-description {
  padding: 12px;
  background: #f9fafb;
  border-radius: 6px;
  border-left: 4px solid #667eea;
}

.mode-badge {
  display: block;
  font-size: 14px;
  line-height: 1.6;
}

.mode-badge.b2c {
  color: #166534;
}

.mode-badge.b2b {
  color: #92400e;
}

/* 業者資訊 */
.vendor-info {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.vendor-info h3 {
  margin: 0 0 15px 0;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
  margin-bottom: 15px;
}

.status-active {
  color: #4ade80;
  font-weight: bold;
}

.status-inactive {
  color: #f87171;
  font-weight: bold;
}

.scope-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: bold;
  color: white;
  margin-left: 5px;
}

.scope-badge.scope-external {
  background: #67C23A;
}

.scope-badge.scope-internal {
  background: #E6A23C;
}

.params-preview {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid rgba(255,255,255,0.3);
}

.param-badge {
  display: inline-block;
  background: rgba(255,255,255,0.2);
  padding: 4px 10px;
  border-radius: 12px;
  margin-right: 8px;
  margin-bottom: 8px;
  font-size: 13px;
}

/* 聊天容器 */
.chat-container {
  background: white;
  border-radius: 8px;
  border: 1px solid #ddd;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 600px;
}

/* 訊息區域 */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f9fafb;
}

.message {
  margin-bottom: 20px;
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.role-label {
  font-weight: bold;
  font-size: 13px;
}

.timestamp {
  font-size: 12px;
  color: #999;
}

.message-content {
  background: white;
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  white-space: pre-wrap;
  line-height: 1.6;
}

.message.user .message-content {
  background: #667eea;
  color: white;
  border-color: #667eea;
  margin-left: 20%;
}

.message.assistant .message-content {
  background: white;
  margin-right: 20%;
}

/* 訊息影片播放器 */
.message-video {
  margin-top: 12px;
  border-radius: 8px;
  overflow: hidden;
  background: #000;
  border: 1px solid #e5e7eb;
  max-width: 480px;  /* 限制容器最大寬度 */
}

.video-player {
  width: 100%;
  max-height: 360px;  /* 調整最大高度，保持 4:3 比例 */
  display: block;
  background: #000;
}

.message-video .video-info {
  padding: 8px 12px;
  background: #f9fafb;
  display: flex;
  gap: 15px;
  font-size: 12px;
  color: #666;
  border-top: 1px solid #e5e7eb;
}

.message-video .video-info span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* 訊息元數據 */
.message-metadata {
  margin-top: 10px;
  padding: 12px;
  background: #f0f9ff;
  border-radius: 6px;
  border-left: 3px solid #3b82f6;
  font-size: 13px;
}

.metadata-item {
  margin-bottom: 8px;
}

.metadata-item:last-child {
  margin-bottom: 0;
}

.source-item {
  padding: 6px 10px;
  background: white;
  border-radius: 4px;
  margin-top: 6px;
  border: 1px solid #e5e7eb;
}

.scope-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: bold;
  margin-right: 6px;
}

.scope-badge.scope-global {
  background: #dbeafe;
  color: #1e40af;
}

.scope-badge.scope-vendor {
  background: #fef3c7;
  color: #92400e;
}

.scope-badge.scope-customized {
  background: #dcfce7;
  color: #166534;
}

.template-badge {
  display: inline-block;
  padding: 2px 6px;
  background: #f3e8ff;
  color: #6b21a8;
  border-radius: 8px;
  font-size: 10px;
  margin-left: 6px;
}

/* Loading indicator */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 8px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #999;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.7; }
  30% { transform: translateY(-10px); opacity: 1; }
}

/* 輸入區域 */
.chat-input-container {
  border-top: 1px solid #e5e7eb;
  background: white;
  padding: 15px;
}

.quick-questions {
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e5e7eb;
}

.quick-questions strong {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  color: #666;
}

.btn-quick {
  padding: 6px 12px;
  margin-right: 8px;
  margin-bottom: 6px;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 16px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-quick:hover {
  background: #e5e7eb;
  border-color: #9ca3af;
}

.input-row {
  display: flex;
  gap: 10px;
}

.input-row input {
  flex: 1;
  padding: 10px 15px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.input-row input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.btn-send {
  padding: 10px 20px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: bold;
}

.btn-send:hover:not(:disabled) {
  background: #5568d3;
}

.btn-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 空狀態 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  background: white;
  border-radius: 8px;
  border: 2px dashed #d1d5db;
  color: #9ca3af;
  font-size: 18px;
}
</style>
