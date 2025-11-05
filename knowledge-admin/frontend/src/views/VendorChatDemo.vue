<template>
  <div class="vendor-chat-demo">
    <!-- 頭部 -->
    <div class="chat-header">
      <div class="vendor-info" v-if="vendor">
        <h2>🏢 {{ vendor.name }}</h2>
        <div class="vendor-meta">
          <span class="vendor-code">{{ vendor.code }}</span>
          <span class="vendor-type" v-if="vendor.business_type">
            {{ getBusinessTypeLabel(vendor.business_type) }}
          </span>
        </div>
      </div>
      <div class="header-actions">
        <button @click="clearChat" class="btn-secondary btn-sm">
          🗑️ 清除對話
        </button>
      </div>
    </div>

    <!-- 錯誤提示 -->
    <div v-if="error" class="error-banner">
      ❌ {{ error }}
    </div>

    <!-- 對話區域 -->
    <div class="chat-messages" ref="messagesContainer">
      <!-- 歡迎訊息 -->
      <div v-if="messages.length === 0" class="welcome-message">
        <div class="message-bubble ai-message">
          <div class="message-content">
            <p>您好！我是 {{ vendor?.name || '智能' }} 的客服小助手 🤖</p>
            <p>有什麼可以幫助您的嗎？</p>
          </div>
          <div class="message-time">{{ currentTime }}</div>
        </div>
      </div>

      <!-- 對話記錄 -->
      <div
        v-for="message in messages"
        :key="message.id"
        :class="['message-wrapper', message.role === 'user' ? 'user-wrapper' : 'ai-wrapper']"
      >
        <div :class="['message-bubble', message.role === 'user' ? 'user-message' : 'ai-message']">
          <div class="message-content" v-html="renderMarkdown(message.content)"></div>
          <div class="message-footer">
            <span class="message-time">{{ formatTime(message.timestamp) }}</span>
            <span v-if="message.metadata" class="message-metadata">
              <span class="intent-tag">{{ message.metadata.intent }}</span>
              <span
                class="confidence-badge"
                :class="getConfidenceClass(message.metadata.confidence)"
              >
                {{ (message.metadata.confidence * 100).toFixed(0) }}%
              </span>
            </span>
          </div>
        </div>
      </div>

      <!-- 載入中指示器 -->
      <div v-if="isLoading" class="message-wrapper ai-wrapper">
        <div class="message-bubble ai-message loading-message">
          <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 輸入區域 -->
    <div class="chat-input-area">
      <textarea
        v-model="inputMessage"
        @keydown.enter.prevent="handleEnter"
        placeholder="輸入訊息..."
        class="chat-input"
        rows="1"
        ref="inputField"
      ></textarea>
      <button
        @click="sendMessage"
        :disabled="!inputMessage.trim() || isLoading"
        class="btn-send"
      >
        📤
      </button>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { marked } from 'marked';
import { API_BASE_URL } from '@/config/api';

const RAG_API = `${API_BASE_URL}/rag-api/v1`;  // RAG Orchestrator API

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true
});

export default {
  name: 'VendorChatDemo',

  data() {
    return {
      vendorCode: null,
      vendor: null,
      messages: [],
      inputMessage: '',
      isLoading: false,
      error: null,
      messageIdCounter: 1,
      currentStreamingMessage: null,  // 正在流式輸出的訊息
      streamingMetadata: {}  // 收集流式過程中的 metadata
    };
  },

  computed: {
    currentTime() {
      return new Date().toLocaleTimeString('zh-TW', {
        hour: '2-digit',
        minute: '2-digit'
      });
    }
  },

  async mounted() {
    this.vendorCode = this.$route.params.vendorCode;
    await this.loadVendor();
    this.loadChatHistory();

    // 自動 focus 輸入框
    this.$nextTick(() => {
      this.$refs.inputField?.focus();
    });
  },

  methods: {
    async loadVendor() {
      try {
        // 獲取所有業者列表
        const response = await axios.get(`${RAG_API}/vendors`);

        if (response.data && response.data.length > 0) {
          // 客戶端過濾，找出匹配的業者代碼（不區分大小寫）
          const vendor = response.data.find(
            v => v.code && v.code.toLowerCase() === this.vendorCode.toLowerCase()
          );

          if (vendor) {
            this.vendor = vendor;
          } else {
            this.error = `找不到業者代碼: ${this.vendorCode}`;
          }
        } else {
          this.error = '無法載入業者列表';
        }
      } catch (err) {
        console.error('載入業者失敗', err);
        this.error = '載入業者資訊失敗';
      }
    },

    async sendMessage() {
      if (!this.inputMessage.trim() || this.isLoading || !this.vendor) return;

      const userMessage = this.inputMessage.trim();
      this.inputMessage = '';

      // 添加用戶訊息
      this.addMessage('user', userMessage);

      // 調用 Message API（改用非串流版本以提升穩定性）
      this.isLoading = true;

      try {
        const response = await axios.post(`${RAG_API}/message`, {
          message: userMessage,
          vendor_id: this.vendor.id,
          mode: 'tenant',
          user_role: 'customer',
          include_sources: false
        });

        // 添加 AI 回應
        const messageId = this.messageIdCounter++;
        this.messages.push({
          id: messageId,
          role: 'assistant',
          content: response.data.answer,
          timestamp: new Date().toISOString(),
          metadata: {
            intent: response.data.intent_name || 'unknown',
            confidence: response.data.confidence || 0,
            sources_count: response.data.source_count || 0
          }
        });

      } catch (err) {
        console.error('發送訊息失敗', err);

        // 添加錯誤訊息
        this.addMessage('assistant', '抱歉，系統發生錯誤，請稍後再試。', {
          intent: 'error',
          confidence: 0
        });
      } finally {
        this.isLoading = false;

        // 滾動到底部
        this.$nextTick(() => {
          this.scrollToBottom();
        });

        // 儲存對話記錄
        this.saveChatHistory();
      }
    },

    async handleStreamEvent(data) {
      // 處理不同的 SSE 事件
      if (data.chunk) {
        // answer_chunk 事件：逐字追加內容
        if (this.currentStreamingMessage) {
          this.currentStreamingMessage.content += data.chunk;

          // 即時滾動到底部
          this.$nextTick(() => {
            this.scrollToBottom();
          });
        }
      } else if (data.intent_name) {
        // intent 事件：儲存意圖信息
        this.streamingMetadata.intent_name = data.intent_name;
        this.streamingMetadata.confidence = data.confidence;
      } else if (data.doc_count !== undefined) {
        // search 事件：儲存檢索結果數量
        this.streamingMetadata.doc_count = data.doc_count;
      } else if (data.confidence_score !== undefined) {
        // metadata 或 confidence 事件：儲存信心度
        this.streamingMetadata.confidence_score = data.confidence_score;
        this.streamingMetadata.confidence_level = data.confidence_level;
      }
    },

    handleEnter(event) {
      if (!event.shiftKey) {
        // Enter 不按 Shift = 發送
        this.sendMessage();
      } else {
        // Shift + Enter = 換行（預設行為）
      }
    },

    addMessage(role, content, metadata = null) {
      this.messages.push({
        id: this.messageIdCounter++,
        role,
        content,
        timestamp: new Date().toISOString(),
        metadata
      });
    },

    clearChat() {
      if (confirm('確定要清除所有對話記錄嗎？')) {
        this.messages = [];
        this.messageIdCounter = 1;
        localStorage.removeItem(`chat_${this.vendorCode}`);
      }
    },

    loadChatHistory() {
      try {
        const saved = localStorage.getItem(`chat_${this.vendorCode}`);
        if (saved) {
          const data = JSON.parse(saved);
          this.messages = data.messages || [];
          this.messageIdCounter = data.counter || 1;
        }
      } catch (err) {
        console.error('載入對話記錄失敗', err);
      }
    },

    saveChatHistory() {
      try {
        localStorage.setItem(`chat_${this.vendorCode}`, JSON.stringify({
          messages: this.messages,
          counter: this.messageIdCounter
        }));
      } catch (err) {
        console.error('儲存對話記錄失敗', err);
      }
    },

    renderMarkdown(text) {
      return marked(text);
    },

    formatTime(timestamp) {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('zh-TW', {
        hour: '2-digit',
        minute: '2-digit'
      });
    },

    getConfidenceClass(confidence) {
      if (confidence >= 0.8) return 'confidence-high';
      if (confidence >= 0.6) return 'confidence-medium';
      return 'confidence-low';
    },

    getBusinessTypeLabel(type) {
      const labels = {
        'property_management': '代管型業者',
        'full_service': '包租型業者',
        'system_provider': '系統商'
      };
      return labels[type] || type;
    },

    scrollToBottom() {
      const container = this.$refs.messagesContainer;
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    }
  }
};
</script>

<style scoped>
.vendor-chat-demo {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 1400px;
  margin: 0 auto;
  background: #f5f5f5;
  padding: 0 2rem;
}

@media (max-width: 768px) {
  .vendor-chat-demo {
    padding: 0 1rem;
  }
}

/* 頭部 */
.chat-header {
  background: white;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.vendor-info h2 {
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
  color: #2c3e50;
}

.vendor-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.9rem;
}

.vendor-code {
  background: #e3f2fd;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  color: #1976d2;
  font-weight: 500;
}

.vendor-type {
  background: #f3e5f5;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  color: #7b1fa2;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

/* 錯誤提示 */
.error-banner {
  background: #ffebee;
  color: #c62828;
  padding: 1rem;
  text-align: center;
  border-bottom: 1px solid #ef5350;
}

/* 對話區域 */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 2rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.message-wrapper {
  display: flex;
  align-items: flex-start;
}

.user-wrapper {
  justify-content: flex-end;
}

.ai-wrapper {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 70%;
  padding: 1rem 1.25rem;
  border-radius: 18px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.user-message {
  background: #1976d2;
  color: white;
  border-bottom-right-radius: 4px;
}

.ai-message {
  background: white;
  color: #2c3e50;
  border-bottom-left-radius: 4px;
}

.message-content {
  line-height: 1.6;
}

.message-content :deep(h1),
.message-content :deep(h2),
.message-content :deep(h3) {
  margin: 0.5em 0 0.3em 0;
  color: inherit;
}

.message-content :deep(p) {
  margin: 0.5em 0;
}

.message-content :deep(ul),
.message-content :deep(ol) {
  margin: 0.5em 0;
  padding-left: 1.5em;
}

.message-content :deep(strong) {
  font-weight: 600;
}

.message-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.5rem;
  font-size: 0.75rem;
  opacity: 0.7;
}

.message-metadata {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.intent-tag {
  background: rgba(0,0,0,0.05);
  padding: 0.15rem 0.5rem;
  border-radius: 8px;
  font-size: 0.7rem;
}

.user-message .intent-tag {
  background: rgba(255,255,255,0.2);
}

.confidence-badge {
  padding: 0.15rem 0.5rem;
  border-radius: 8px;
  font-size: 0.7rem;
  font-weight: 600;
}

.confidence-high {
  background: #c8e6c9;
  color: #2e7d32;
}

.confidence-medium {
  background: #fff9c4;
  color: #f57f17;
}

.confidence-low {
  background: #ffcdd2;
  color: #c62828;
}

/* 歡迎訊息 */
.welcome-message .ai-message {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

/* 載入中動畫 */
.loading-message {
  padding: 0.75rem 1.25rem;
}

.typing-indicator {
  display: flex;
  gap: 0.3rem;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #bbb;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-10px);
  }
}

/* 輸入區域 */
.chat-input-area {
  background: white;
  padding: 1rem 1.5rem;
  border-top: 1px solid #e0e0e0;
  display: flex;
  gap: 0.75rem;
  align-items: flex-end;
  box-shadow: 0 -2px 8px rgba(0,0,0,0.05);
}

.chat-input {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 2px solid #e0e0e0;
  border-radius: 20px;
  resize: none;
  font-size: 1rem;
  font-family: inherit;
  transition: border-color 0.2s;
  max-height: 120px;
}

.chat-input:focus {
  outline: none;
  border-color: #1976d2;
}

.btn-send {
  padding: 0.75rem 1.5rem;
  background: #1976d2;
  color: white;
  border: none;
  border-radius: 20px;
  font-size: 1.2rem;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 60px;
}

.btn-send:hover:not(:disabled) {
  background: #1565c0;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(25, 118, 210, 0.3);
}

.btn-send:disabled {
  background: #bbb;
  cursor: not-allowed;
}

/* 按鈕樣式 */
.btn-secondary {
  background: #f5f5f5;
  color: #666;
  border: 1px solid #ddd;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: #e0e0e0;
}

.btn-sm {
  font-size: 0.85rem;
  padding: 0.4rem 0.8rem;
}

/* 響應式設計 */
@media (max-width: 768px) {
  .message-bubble {
    max-width: 85%;
  }

  .quick-questions-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .vendor-info h2 {
    font-size: 1.2rem;
  }
}
</style>
