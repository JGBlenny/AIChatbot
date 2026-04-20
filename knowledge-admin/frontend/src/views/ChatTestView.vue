<template>
  <div class="chat-test-view">
    <h2>💬 Chat API 測試</h2>

    <!-- ✅ 新增：顯示當前用戶角色 -->
    <div v-if="userRole && userRole !== 'customer'" class="user-role-badge">
      <span class="role-icon">👤</span>
      <span class="role-text">當前角色: <strong>{{ getUserRoleLabel(userRole) }}</strong></span>
      <span class="role-value">({{ userRole }})</span>
    </div>

    <!-- 模式與業者選擇器 -->
    <div class="vendor-selector">
      <div class="selector-row">
        <div class="selector-group">
          <label>測試模式：</label>
          <select v-model="chatMode" @change="onModeChange" class="mode-select">
            <option value="b2c">🏠 B2C - 租客對業者 (b2c)</option>
            <option value="b2b">🏢 B2B - 業者對我們 (b2b)</option>
          </select>
        </div>

        <div class="selector-group">
          <label>用戶角色：</label>
          <select v-model="userRole" class="role-select">
            <option value="tenant">🏠 租客 (tenant)</option>
            <option value="landlord">🏡 房東 (landlord)</option>
            <option value="property_manager">👔 物業管理師 (property_manager)</option>
            <option value="system_admin">⚙️ 系統管理員 (system_admin)</option>
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

        <div class="selector-group">
          <label>
            <input type="checkbox" v-model="debugMode" />
            顯示處理流程詳情
          </label>
        </div>
      </div>

      <!-- B2B 模式：JGB 身份參數 -->
      <div v-if="chatMode === 'b2b'" class="selector-row jgb-identity-row">
        <div class="selector-group">
          <label>JGB Role ID：</label>
          <input v-model="jgbRoleId" type="text" placeholder="例如：200" class="jgb-input" />
        </div>
        <div class="selector-group">
          <label>JGB User ID：</label>
          <input v-model="jgbUserId" type="text" placeholder="例如：100" class="jgb-input" />
        </div>
      </div>

      <!-- 模式說明 -->
      <div class="mode-description">
        <span v-if="chatMode === 'b2c'" class="mode-badge b2c">
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
        <div>
          <strong>代碼：</strong>
          <a :href="`/${selectedVendor.code}/chat`" target="_blank" class="vendor-code-link">
            {{ selectedVendor.code }}
          </a>
        </div>
        <div><strong>名稱：</strong>{{ selectedVendor.name }}</div>
      </div>
    </div>

    <!-- 聊天區域 -->
    <div v-if="selectedVendorId" class="chat-container">
      <!-- 表單填寫狀態提示 -->
      <div v-if="isFillingForm" class="form-status-banner">
        <span class="status-icon">📋</span>
        <div class="status-content">
          <strong>表單填寫中：{{ currentFormId }}</strong>
          <span class="status-hint">目前欄位：{{ currentField }}</span>
        </div>
        <button @click="cancelForm" class="btn-cancel-form">取消填寫</button>
      </div>

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

          <!-- 調試資訊面板 -->
          <!-- 只有當訊息包含 debug_info 時才顯示 -->
          <div v-if="msg.role === 'assistant' && msg.debug_info" class="debug-panel">
            <button @click="toggleDebug(index)" class="debug-toggle">
              {{ showDebug[index] ? '▼' : '▶' }} 查看處理流程詳情
            </button>

            <div v-show="showDebug[index]" class="debug-content">

              <!-- 有 debug_info 才顯示詳細資訊 -->
              <template v-if="msg.debug_info">
              <!-- 處理路徑 -->
              <div class="debug-section">
                <h4>🛤️ 處理路徑</h4>
                <div v-if="msg.debug_info.system_config" class="config-items">
                  <span v-for="(config, path) in msg.debug_info.system_config.processing_paths" :key="path"
                        :class="['config-item', path === msg.debug_info.processing_path ? 'current' : '']">
                    {{ path === msg.debug_info.processing_path ? '✅' : '○' }} {{ getProcessingPathName(path) }}
                    <code class="path-code">{{ path }}</code>
                    <code v-if="config.threshold" class="threshold-code">≥{{ config.threshold }}</code>
                  </span>
                </div>
                <div v-else>
                  <span class="path-badge" :class="`path-${msg.debug_info.processing_path}`">
                    {{ getProcessingPathName(msg.debug_info.processing_path) }}
                  </span>
                  <code class="path-code">{{ msg.debug_info.processing_path }}</code>
                </div>
              </div>

              <!-- 意圖分析詳情 -->
              <div class="debug-section">
                <h4>🎯 意圖分析</h4>
                <div>主要意圖: <strong>{{ msg.debug_info.intent_details.primary_intent }}</strong>
                  ({{ msg.debug_info.intent_details.primary_confidence.toFixed(2) }})
                </div>
                <div v-if="msg.debug_info.intent_details.secondary_intents && msg.debug_info.intent_details.secondary_intents.length > 0">
                  次要意圖: {{ msg.debug_info.intent_details.secondary_intents.join(', ') }}
                </div>
              </div>

              <!-- 候選 SOP 列表 -->
              <div class="debug-section" v-if="msg.debug_info.sop_candidates && msg.debug_info.sop_candidates.length > 0">
                <h4>📋 候選 SOP ({{ msg.debug_info.sop_candidates.length }})</h4>
                <div class="table-container">
                  <table class="candidates-table">
                    <thead>
                      <tr>
                        <th>選取</th>
                        <th>ID</th>
                        <th>項目名稱</th>
                        <th>群組</th>
                        <th>基礎相似度</th>
                        <th>Rerank分數</th>
                        <th>意圖加成</th>
                        <th>最終相似度 (10/90)</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="s in msg.debug_info.sop_candidates" :key="s.id"
                          :class="{ 'selected': s.is_selected }">
                        <td>{{ s.is_selected ? '✅' : '' }}</td>
                        <td>
                          <a :href="`/vendors/${selectedVendorId}/configs?category=sop&sop_id=${s.id}`"
                             target="_blank"
                             class="id-link"
                             title="在新分頁打開 SOP 管理">
                            {{ s.id }}
                          </a>
                        </td>
                        <td class="text-left">
                          <a :href="`/vendors/${selectedVendorId}/configs?category=sop&sop_id=${s.id}`"
                             target="_blank"
                             class="item-link"
                             title="在新分頁打開 SOP 管理">
                            {{ s.item_name }}
                          </a>
                        </td>
                        <td class="text-left">{{ s.group_name || '-' }}</td>
                        <td>{{ s.base_similarity.toFixed(3) }}</td>
                        <td>
                          <span v-if="s.rerank_score !== undefined && s.rerank_score !== null" class="rerank-score">
                            {{ s.rerank_score.toFixed(4) }}
                          </span>
                          <span v-else class="no-rerank">-</span>
                        </td>
                        <td>{{ s.intent_boost }}x</td>
                        <td>{{ s.boosted_similarity.toFixed(3) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- 候選知識列表 -->
              <div class="debug-section" v-if="msg.debug_info.knowledge_candidates && msg.debug_info.knowledge_candidates.length > 0">
                <h4>📚 候選知識 ({{ msg.debug_info.knowledge_candidates.length }})</h4>
                <div class="table-container">
                  <table class="candidates-table">
                    <thead>
                      <tr>
                        <th>選取</th>
                        <th>ID</th>
                        <th>摘要</th>
                        <th>Scope</th>
                        <th>基礎相似度</th>
                        <th>Rerank分數</th>
                        <th>優先級加成</th>
                        <th>最終相似度 (10/90)</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="k in msg.debug_info.knowledge_candidates" :key="k.id"
                          :class="{ 'selected': k.is_selected }">
                        <td>{{ k.is_selected ? '✅' : '' }}</td>
                        <td>
                          <a :href="`/knowledge?ids=${k.id}&edit=true`"
                             target="_blank"
                             class="id-link"
                             title="在新分頁打開知識編輯">
                            {{ k.id }}
                          </a>
                        </td>
                        <td class="text-left">
                          <a :href="`/knowledge?ids=${k.id}&edit=true`"
                             target="_blank"
                             class="item-link"
                             title="在新分頁打開知識編輯">
                            {{ k.question_summary }}
                          </a>
                        </td>
                        <td><span class="scope-badge" :class="`scope-${k.scope}`">{{ k.scope }}</span></td>
                        <td>{{ k.base_similarity.toFixed(3) }}</td>
                        <td>
                          <span v-if="k.rerank_score !== undefined && k.rerank_score !== null" class="rerank-score">
                            {{ k.rerank_score.toFixed(4) }}
                          </span>
                          <span v-else class="no-rerank">-</span>
                        </td>
                        <td>{{ k.priority_boost ? '+' + k.priority_boost.toFixed(3) : '0' }}</td>
                        <td>{{ k.boosted_similarity.toFixed(3) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- LLM 優化策略 -->
              <div class="debug-section">
                <h4>🤖 LLM 優化策略</h4>
                <div v-if="msg.debug_info.system_config" class="config-items">
                  <span v-for="(config, strategy) in msg.debug_info.system_config.llm_strategies" :key="strategy"
                        :class="['config-item', strategy === msg.debug_info.llm_strategy ? 'current' : '']">
                    {{ strategy === msg.debug_info.llm_strategy ? '✅' : '○' }} {{ getLLMStrategyName(strategy) }}
                    <code class="strategy-code">{{ strategy }}</code>
                    <code v-if="config.threshold" class="threshold-code">≥{{ config.threshold }}</code>
                  </span>
                </div>
                <div v-else>
                  <span class="strategy-badge">{{ getLLMStrategyName(msg.debug_info.llm_strategy) }}</span>
                  <code class="strategy-code">{{ msg.debug_info.llm_strategy }}</code>
                </div>
              </div>

              <!-- 答案合成資訊 -->
              <div class="debug-section" v-if="msg.debug_info.synthesis_info">
                <h4>🔗 答案合成</h4>
                <div>合成來源: {{ msg.debug_info.synthesis_info.sources_count }} 個</div>
                <div>來源 ID: {{ msg.debug_info.synthesis_info.sources_ids.join(', ') }}</div>
                <div>合成原因: {{ msg.debug_info.synthesis_info.synthesis_reason }}</div>
              </div>

              <!-- 業者參數 -->
              <div class="debug-section" v-if="msg.debug_info.vendor_params_injected && msg.debug_info.vendor_params_injected.length > 0">
                <h4>⚙️ 注入的業者參數 ({{ msg.debug_info.vendor_params_injected.length }})</h4>
                <div v-for="p in msg.debug_info.vendor_params_injected" :key="p.param_key" class="param-item">
                  <strong>{{ p.display_name }}:</strong> {{ p.value }}{{ p.unit || '' }}
                  <code class="param-key">{{ p.param_key }}</code>
                </div>
              </div>

              <!-- 閾值資訊 -->
              <div class="debug-section">
                <h4>📊 相似度閾值</h4>
                <div class="thresholds">
                  <span>SOP: {{ msg.debug_info.thresholds.sop_threshold }}</span>
                  <span>檢索: {{ msg.debug_info.thresholds.knowledge_retrieval_threshold }}</span>
                  <span>高質量: {{ msg.debug_info.thresholds.high_quality_threshold }}</span>
                </div>
              </div>
              </template>
              <!-- 結束 debug_info 內容 -->
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
      chatMode: 'b2c', // 'b2c' or 'b2b'
      vendors: [],
      selectedVendorId: '',
      selectedVendor: null,
      vendorParams: null,
      messages: [],
      userInput: '',
      loading: false,
      userRole: 'tenant',  // 用戶角色（可從 UI 選擇或 URL 讀取）
      targetUserConfig: [],   // 從 API 獲取的目標用戶配置
      debugMode: true,  // 是否開啟調試模式（默認開啟）
      showDebug: {},  // 控制每個訊息的調試面板展開/摺疊 {messageIndex: boolean}
      // 表單填寫支援
      sessionId: null,  // 會話 ID（用於表單追蹤）
      userId: null,  // 用戶 ID
      jgbRoleId: '',  // JGB 系統角色 ID（B2B 模式用）
      jgbUserId: '',  // JGB 系統用戶 ID（B2B 模式用）
      isFillingForm: false,  // 是否正在填寫表單
      currentFormId: null,  // 當前表單 ID
      currentField: null  // 當前填寫的欄位
    };
  },
  computed: {
    vendorParamsWithValues() {
      if (!this.vendorParams) return [];

      return Object.keys(this.vendorParams)
        .filter(key => {
          const value = this.vendorParams[key].value;
          return value !== null && value !== undefined && value !== '';
        })
        .map(key => ({
          key,
          displayName: this.vendorParams[key].display_name || key,
          value: this.vendorParams[key].value,
          unit: this.vendorParams[key].unit
        }));
    }
  },
  mounted() {
    console.log('🚀 [ChatTestView] mounted() 被調用');

    // 初始化 session_id 和 user_id（用於表單追蹤）
    this.sessionId = this.generateUUID();
    this.userId = `test_user_${Date.now()}`;
    console.log('📋 初始化會話:', { sessionId: this.sessionId, userId: this.userId });

    this.loadVendors();
    this.loadTargetUserConfig();  // ✅ 新增：載入目標用戶配置

    // ✅ 新增：從 URL 讀取參數
    const urlParams = new URLSearchParams(window.location.search);

    // 讀取 target_user 參數（向後兼容 user_role）
    const urlTargetUser = urlParams.get('target_user') || urlParams.get('user_role');
    const validRoles = ['tenant', 'landlord', 'property_manager', 'system_admin'];

    if (urlTargetUser && validRoles.includes(urlTargetUser)) {
      this.userRole = urlTargetUser;
      console.log('🔑 從 URL 設定 target_user:', this.userRole);
    } else if (urlTargetUser) {
      console.warn('⚠️  無效的 target_user 參數:', urlTargetUser, '使用預設值: tenant');
    }

    // 讀取 vendor_id 參數（自動選擇業者）
    const vendorId = urlParams.get('vendor_id');
    if (vendorId) {
      this.selectedVendorId = vendorId;
      console.log('🏢 從 URL 設定 vendor_id:', vendorId);
      // 等業者列表載入後再載入業者資訊
      this.$nextTick(() => {
        setTimeout(() => {
          this.loadVendorInfo();
        }, 500);
      });
    }
  },
  methods: {
    formatParamValue(value, unit) {
      if (!value) return '';

      // 處理換行符（如繳費方式）
      let formattedValue = value.toString().replace(/\\n/g, '、');

      // 添加單位
      if (unit) {
        formattedValue += ` ${unit}`;
      }

      return formattedValue;
    },
    async loadVendors() {
      try {
        console.log('🔄 [loadVendors] 開始載入業者列表...');
        console.log('🔄 [loadVendors] RAG_API:', RAG_API);
        console.log('🔄 [loadVendors] 完整 URL:', `${RAG_API}/v1/vendors`);
        const response = await axios.get(`${RAG_API}/v1/vendors`);
        console.log('✅ [loadVendors] API 回應成功:', response.data);
        this.vendors = response.data;
        console.log('✅ [loadVendors] vendors 已更新:', this.vendors);
        console.log('✅ [loadVendors] vendors 數量:', this.vendors.length);
      } catch (error) {
        console.error('❌ [loadVendors] 載入業者失敗', error);
        console.error('❌ [loadVendors] error.response:', error.response);
        alert('載入業者失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    // ✅ 新增：從 API 載入目標用戶配置
    async loadTargetUserConfig() {
      try {
        const response = await axios.get(`${API_BASE_URL}/target-users-config`);
        this.targetUserConfig = response.data;
        console.log('✅ 已載入目標用戶配置:', this.targetUserConfig);
      } catch (error) {
        console.error('⚠️  載入目標用戶配置失敗', error);
        // 如果 API 失敗，使用預設配置
        this.targetUserConfig = [
          { user_value: 'tenant', display_name: '租客' },
          { user_value: 'landlord', display_name: '房東' },
          { user_value: 'property_manager', display_name: '物業管理師' },
          { user_value: 'system_admin', display_name: '系統管理員' }
        ];
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
        if (this.chatMode === 'b2c') {
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
        // ✅ 修改：優先使用從 URL 讀取的 userRole
        // 如果沒有從 URL 設定，則根據 chatMode 決定
        let userRole = this.userRole;

        console.log('📤 發送訊息，target_user:', userRole, 'mode:', this.chatMode);

        const payload = {
          message: message,
          vendor_id: parseInt(this.selectedVendorId),
          mode: this.chatMode,
          target_user: userRole,
          include_sources: true,
          include_debug_info: this.debugMode,
          session_id: this.sessionId,
          user_id: this.userId
        };
        // B2B 模式帶入 JGB 身份參數
        if (this.chatMode === 'b2b') {
          if (this.jgbRoleId) payload.role_id = this.jgbRoleId;
          if (this.jgbUserId) payload.user_id = this.jgbUserId;
        }
        const response = await axios.post(`${RAG_API}/v1/message`, payload);

        // 檢查是否觸發表單
        if (response.data.form_triggered) {
          this.isFillingForm = true;
          this.currentFormId = response.data.form_id;
          this.currentField = response.data.current_field;
          console.log('📋 表單已觸發:', {
            formId: this.currentFormId,
            currentField: this.currentField,
            progress: response.data.progress
          });
        } else if (response.data.form_completed) {
          this.isFillingForm = false;
          this.currentFormId = null;
          this.currentField = null;
          console.log('✅ 表單填寫完成');
        } else if (response.data.form_cancelled) {
          this.isFillingForm = false;
          this.currentFormId = null;
          this.currentField = null;
          console.log('❌ 表單已取消');
        }

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
            video_format: response.data.video_format,
            // 表單資訊
            form_triggered: response.data.form_triggered,
            form_completed: response.data.form_completed,
            form_cancelled: response.data.form_cancelled,
            form_id: response.data.form_id,
            current_field: response.data.current_field,
            progress: response.data.progress
          },
          debug_info: response.data.debug_info  // 新增：調試資訊
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
        if (this.chatMode === 'b2c') {
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
    },

    // ✅ 新增：從配置中獲取角色的中文標籤
    getUserRoleLabel(role) {
      // 🛡️ 安全檢查：確保 targetUserConfig 是數組
      if (Array.isArray(this.targetUserConfig) && this.targetUserConfig.length > 0) {
        const config = this.targetUserConfig.find(c => c.user_value === role);
        if (config && config.display_name) {
          return config.display_name;
        }
      }

      // Fallback 預設標籤
      const defaultLabels = {
        tenant: '租客',
        landlord: '房東',
        property_manager: '物業管理師',
        system_admin: '系統管理員'
      };

      // 如果都找不到，返回預設標籤或原始值
      return defaultLabels[role] || role;
    },

    // 切換調試面板顯示/隱藏
    toggleDebug(index) {
      // Vue 3: 直接賦值即可，不需要 $set
      this.showDebug[index] = !this.showDebug[index];
    },

    // 取得處理路徑的中文名稱
    getProcessingPathName(path) {
      const pathNames = {
        'sop': 'SOP 標準流程',
        'sop_orchestrator': 'SOP 標準流程',  // 🆕 新增：SOP Orchestrator 映射
        'knowledge': '知識庫流程',
        'rag_fallback': 'RAG 降級檢索',
        'param_answer': '參數查詢',
        'no_knowledge_found': '找不到知識（兜底）',
        'unclear': '意圖不明確'
      };
      return pathNames[path] || path;
    },

    // 取得 LLM 策略的中文名稱
    getLLMStrategyName(strategy) {
      const strategyNames = {
        'perfect_match': '完美匹配（直接返回）',
        'fast_path': '快速路徑（簡單格式化）',
        'template': '模板格式化',
        'synthesis': '答案合成（多來源）',
        'llm': 'LLM 完整優化',
        'direct': '直接返回（SOP）',
        'orchestrated': 'SOP 編排執行',  // 🆕 新增：SOP Orchestrator 策略
        'param_query': '參數查詢',
        'fallback': '兜底回應',
        'none': '無優化',
        'unknown': '未知策略'
      };
      return strategyNames[strategy] || strategy;
    },

    // 生成 UUID（用於 session_id）
    generateUUID() {
      return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
      });
    },

    // 取消表單填寫
    async cancelForm() {
      if (!confirm('確定要取消表單填寫嗎？')) return;

      // 發送「取消」訊息給後端
      await this.sendMessage('取消');
    }
  }
};
</script>

<style scoped>
.chat-test-view {
  width: 100%;
}

/* ✅ 新增：用戶角色標籤 */
.user-role-badge {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  padding: 12px 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.user-role-badge .role-icon {
  font-size: 20px;
}

.user-role-badge .role-text {
  font-size: 15px;
  flex: 1;
}

.user-role-badge .role-value {
  font-size: 13px;
  opacity: 0.8;
  font-family: 'Courier New', monospace;
  background: rgba(255, 255, 255, 0.2);
  padding: 2px 8px;
  border-radius: 4px;
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

.jgb-identity-row {
  margin-top: 8px;
  padding: 8px 12px;
  background: #fef3c7;
  border-radius: 6px;
  border: 1px solid #f59e0b;
}

.jgb-input {
  padding: 4px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  width: 120px;
  font-size: 14px;
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

.vendor-code-link {
  color: white;
  text-decoration: none;
  font-weight: bold;
  padding: 4px 12px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  transition: all 0.2s;
  display: inline-block;
}

.vendor-code-link:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
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

/* 調試面板 */
.debug-panel {
  margin-top: 15px;
  border: 2px solid #e0e7ff;
  border-radius: 8px;
  overflow: hidden;
  background: #f8fafc;
}

.debug-toggle {
  width: 100%;
  padding: 12px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  cursor: pointer;
  font-weight: bold;
  font-size: 14px;
  text-align: left;
  transition: all 0.2s;
}

.debug-toggle:hover {
  background: linear-gradient(135deg, #5568d3 0%, #653a8f 100%);
}

.debug-content {
  padding: 20px;
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    max-height: 0;
  }
  to {
    opacity: 1;
    max-height: 2000px;
  }
}

.debug-section {
  margin-bottom: 20px;
  padding: 15px;
  background: white;
  border-radius: 6px;
  border-left: 4px solid #667eea;
}

.debug-section h4 {
  margin: 0 0 10px 0;
  color: #374151;
  font-size: 15px;
}

.path-badge {
  display: inline-block;
  padding: 6px 16px;
  border-radius: 20px;
  font-weight: bold;
  font-size: 13px;
  text-transform: uppercase;
}

.path-badge.path-knowledge {
  background: #dcfce7;
  color: #166534;
}

.path-badge.path-sop {
  background: #fef3c7;
  color: #92400e;
}

.path-badge.path-fallback {
  background: #fee2e2;
  color: #991b1b;
}

.strategy-badge {
  display: inline-block;
  padding: 6px 14px;
  background: #e0e7ff;
  color: #3730a3;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 600;
}

/* 處理路徑和策略的英文代碼 */
.path-code,
.strategy-code {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 8px;
  background: #f1f5f9;
  color: #64748b;
  border-radius: 4px;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 11px;
  font-weight: normal;
}

/* 系統配置狀態樣式 */
.config-items {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.config-item {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  font-size: 12px;
  color: #4b5563;
  transition: all 0.2s;
}

.config-item.current {
  background: #dbeafe;
  border-color: #3b82f6;
  color: #1e40af;
  font-weight: 600;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.threshold-code {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 6px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 10px;
  color: #6b7280;
}

.table-container {
  overflow-x: auto;
  margin-top: 10px;
}

.candidates-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.candidates-table thead {
  background: #f3f4f6;
}

.candidates-table th {
  padding: 10px 8px;
  text-align: center;
  font-weight: 600;
  color: #374151;
  border-bottom: 2px solid #d1d5db;
  white-space: nowrap;
}

.candidates-table td {
  padding: 8px;
  text-align: center;
  border-bottom: 1px solid #e5e7eb;
}

.candidates-table td.text-left {
  text-align: left;
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.candidates-table tr.selected {
  background: #f0fdf4;
  font-weight: 600;
}

.candidates-table tr:hover {
  background: #f9fafb;
}

/* 候選項連結樣式 */
.candidates-table .id-link,
.candidates-table .item-link {
  color: #2563eb;
  text-decoration: none;
  font-weight: 500;
  transition: all 0.2s;
}

.candidates-table .id-link:hover,
.candidates-table .item-link:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

.candidates-table .id-link {
  font-family: 'Courier New', monospace;
  font-weight: 600;
}

/* Rerank 分數樣式 */
.candidates-table .rerank-score {
  display: inline-block;
  padding: 2px 8px;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  border-radius: 4px;
  font-weight: 600;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.candidates-table .no-rerank {
  color: #9ca3af;
  font-style: italic;
}

.param-item {
  margin-bottom: 8px;
  padding: 8px 12px;
  background: #f9fafb;
  border-radius: 4px;
  font-size: 13px;
}

.param-key {
  margin-left: 8px;
  padding: 2px 6px;
  background: #e0e7ff;
  color: #3730a3;
  border-radius: 4px;
  font-size: 11px;
  font-family: 'Courier New', monospace;
}

.thresholds {
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
}

.thresholds span {
  padding: 6px 12px;
  background: #f3f4f6;
  border-radius: 6px;
  font-size: 13px;
  font-family: monospace;
}

.role-select {
  min-width: 220px;
}

/* 表單填寫狀態橫幅 */
.form-status-banner {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
  padding: 15px 20px;
  border-radius: 8px;
  margin-bottom: 15px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3);
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

.form-status-banner .status-icon {
  font-size: 24px;
}

.form-status-banner .status-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-status-banner .status-hint {
  font-size: 13px;
  opacity: 0.9;
}

.form-status-banner .btn-cancel-form {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.form-status-banner .btn-cancel-form:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
}
</style>
