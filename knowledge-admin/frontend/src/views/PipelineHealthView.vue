<template>
  <div class="pipeline-health-view">
    <h2>🏥 Pipeline 健康儀表板</h2>

    <!-- 載入狀態 -->
    <div v-if="loading" class="loading-state">
      <div class="loading-icon">⏳</div>
      <div class="loading-text">正在檢查各元件健康狀態...</div>
    </div>

    <!-- 錯誤狀態 -->
    <div v-else-if="error" class="error-state">
      <div class="error-icon">❌</div>
      <div class="error-info">
        <div class="error-title">無法取得健康狀態</div>
        <div class="error-message">{{ error }}</div>
      </div>
      <button @click="fetchPipelineHealth" class="btn-refresh" title="重新檢查">
        🔄
      </button>
    </div>

    <!-- 正常顯示 -->
    <template v-else-if="healthData">
      <!-- 整體狀態摘要 -->
      <div class="overall-status" :class="overallStatusClass">
        <div class="overall-icon">{{ overallStatusIcon }}</div>
        <div class="overall-info">
          <div class="overall-title">{{ healthData.healthy_count }}/{{ healthData.total_count }} 元件正常</div>
          <div class="overall-message">{{ overallStatusText }}</div>
        </div>
        <button @click="fetchPipelineHealth" class="btn-refresh" title="重新檢查">
          🔄
        </button>
      </div>

      <!-- 元件狀態 Grid -->
      <div class="components-grid">
        <div
          v-for="component in healthData.components"
          :key="component.name"
          class="component-card"
          :class="componentStatusClass(component.status)"
        >
          <div class="component-header">
            <span class="component-icon">{{ statusEmoji(component.status) }}</span>
            <span class="component-name">{{ component.name }}</span>
            <span v-if="component.is_core" class="core-badge">核心</span>
          </div>
          <div class="component-details">
            <div class="detail-item">
              <span class="detail-label">延遲：</span>
              <span class="detail-value">{{ formatLatency(component.latency_ms) }}</span>
            </div>
            <div class="detail-item" v-if="component.version">
              <span class="detail-label">版本：</span>
              <span class="detail-value">{{ component.version }}</span>
            </div>
          </div>
          <div v-if="component.status === 'unhealthy' && component.error" class="component-error">
            {{ component.error }}
          </div>
          <div v-if="component.status === 'degraded' && component.degradation_impact" class="component-degraded">
            {{ component.degradation_impact }}
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
import { API_ENDPOINTS } from '@/config/api';

export default {
  name: 'PipelineHealthView',
  data() {
    return {
      healthData: null,
      loading: false,
      error: null,
    };
  },
  computed: {
    overallStatusClass() {
      if (!this.healthData) return '';
      return `status-${this.healthData.overall_status}`;
    },
    overallStatusIcon() {
      if (!this.healthData) return '❓';
      const icons = {
        healthy: '✅',
        unhealthy: '❌',
        degraded: '⚠️',
      };
      return icons[this.healthData.overall_status] || '❓';
    },
    overallStatusText() {
      if (!this.healthData) return '';
      const texts = {
        healthy: '所有元件運作正常',
        unhealthy: '有核心元件異常，Pipeline 無法正常運作',
        degraded: '部分非核心元件異常，Pipeline 以降級模式運作',
      };
      return texts[this.healthData.overall_status] || '狀態未知';
    },
  },
  mounted() {
    this.fetchPipelineHealth();
  },
  methods: {
    async fetchPipelineHealth() {
      this.loading = true;
      this.error = null;
      try {
        const response = await fetch(API_ENDPOINTS.pipelineHealth);
        if (response.ok) {
          this.healthData = await response.json();
        } else {
          this.error = `伺服器回應錯誤：${response.status} ${response.statusText}`;
        }
      } catch (err) {
        console.error('取得 Pipeline 健康狀態錯誤:', err);
        this.error = `無法連接到 RAG Orchestrator 服務：${err.message}`;
      } finally {
        this.loading = false;
      }
    },
    statusEmoji(status) {
      const icons = {
        healthy: '✅',
        unhealthy: '❌',
        degraded: '⚠️',
      };
      return icons[status] || '❓';
    },
    componentStatusClass(status) {
      return `status-${status}`;
    },
    formatLatency(ms) {
      if (ms == null) return 'N/A';
      return `${Math.round(ms)} ms`;
    },
  },
};
</script>

<style scoped>
.pipeline-health-view {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

h2 {
  margin-bottom: 20px;
  color: #2c3e50;
}

/* 載入狀態 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #666;
}

.loading-icon {
  font-size: 3rem;
  margin-bottom: 15px;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.loading-text {
  font-size: 1.1rem;
}

/* 錯誤狀態 */
.error-state {
  display: flex;
  align-items: center;
  padding: 20px;
  border-radius: 8px;
  border: 2px solid #dc3545;
  background: #f8d7da;
  color: #721c24;
  margin-bottom: 20px;
}

.error-icon {
  font-size: 2rem;
  margin-right: 15px;
}

.error-info {
  flex: 1;
}

.error-title {
  font-size: 1.2rem;
  font-weight: bold;
  margin-bottom: 5px;
}

.error-message {
  font-size: 0.9rem;
  opacity: 0.9;
}

/* 整體狀態摘要 */
.overall-status {
  display: flex;
  align-items: center;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  border: 2px solid;
}

.overall-icon {
  font-size: 2.5rem;
  margin-right: 15px;
}

.overall-info {
  flex: 1;
}

.overall-title {
  font-size: 1.3rem;
  font-weight: bold;
  margin-bottom: 5px;
}

.overall-message {
  font-size: 0.95rem;
  opacity: 0.9;
}

/* 狀態顏色 */
.status-healthy {
  background: #d4edda;
  border-color: #28a745;
  color: #155724;
}

.status-unhealthy {
  background: #f8d7da;
  border-color: #dc3545;
  color: #721c24;
}

.status-degraded {
  background: #fff3cd;
  border-color: #ffc107;
  color: #856404;
}

/* 重新檢查按鈕 */
.btn-refresh {
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 1.2rem;
}

.btn-refresh:hover {
  background: #f8f9fa;
}

/* 元件狀態 Grid */
.components-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.component-card {
  background: white;
  border: 2px solid;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.component-header {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.component-icon {
  font-size: 1.5rem;
  margin-right: 10px;
}

.component-name {
  font-size: 1.1rem;
  font-weight: bold;
  color: #2c3e50;
  flex: 1;
}

.core-badge {
  background: #007bff;
  color: white;
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: bold;
}

.component-details {
  margin-bottom: 8px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 0.9rem;
}

.detail-label {
  color: #666;
}

.detail-value {
  font-weight: bold;
  color: #2c3e50;
}

.component-error {
  margin-top: 10px;
  padding: 10px;
  background: #f8d7da;
  border-left: 3px solid #dc3545;
  border-radius: 4px;
  font-size: 0.85rem;
  color: #721c24;
}

.component-degraded {
  margin-top: 10px;
  padding: 10px;
  background: #fff3cd;
  border-left: 3px solid #ffc107;
  border-radius: 4px;
  font-size: 0.85rem;
  color: #856404;
}
</style>
