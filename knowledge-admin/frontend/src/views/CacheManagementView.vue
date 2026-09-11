<template>
  <div class="cache-management-view">
    <h2>⚡ 緩存管理</h2>

    <!-- 健康狀態 -->
    <div class="health-status" :class="healthStatusClass">
      <div class="status-icon">{{ healthStatusIcon }}</div>
      <div class="status-info">
        <div class="status-title">{{ healthStatusTitle }}</div>
        <div class="status-message">{{ healthStatusMessage }}</div>
      </div>
      <button @click="fetchCacheHealth" class="btn-refresh" title="重新檢查">
        🔄
      </button>
    </div>

    <!-- 統計卡片 -->
    <div class="stats-grid">
      <!-- 問題緩存 -->
      <div class="stat-card">
        <div class="stat-icon">💬</div>
        <div class="stat-content">
          <div class="stat-label">問題緩存</div>
          <div class="stat-value">{{ stats.cache_counts?.question_cache || 0 }}</div>
          <div class="stat-meta">TTL: {{ formatTTL(stats.ttl_config?.question_cache) }}</div>
        </div>
      </div>

      <!-- 向量緩存 -->
      <div class="stat-card">
        <div class="stat-icon">🔢</div>
        <div class="stat-content">
          <div class="stat-label">向量緩存</div>
          <div class="stat-value">{{ stats.cache_counts?.vector_cache || 0 }}</div>
          <div class="stat-meta">TTL: {{ formatTTL(stats.ttl_config?.vector_cache) }}</div>
        </div>
      </div>

      <!-- RAG 結果緩存 -->
      <div class="stat-card">
        <div class="stat-icon">📝</div>
        <div class="stat-content">
          <div class="stat-label">RAG 結果緩存</div>
          <div class="stat-value">{{ stats.cache_counts?.rag_result_cache || 0 }}</div>
          <div class="stat-meta">TTL: {{ formatTTL(stats.ttl_config?.rag_result_cache) }}</div>
        </div>
      </div>

      <!-- 關聯追蹤 -->
      <div class="stat-card">
        <div class="stat-icon">🔗</div>
        <div class="stat-content">
          <div class="stat-label">關聯追蹤</div>
          <div class="stat-value">{{ stats.cache_counts?.relation_tracking || 0 }}</div>
          <div class="stat-meta">知識/意圖/業者關聯</div>
        </div>
      </div>
    </div>

    <!-- 內存使用情況 -->
    <div class="memory-card" v-if="stats.memory_used_mb">
      <h3>💾 內存使用</h3>
      <div class="memory-stats">
        <div class="memory-item">
          <span class="memory-label">當前使用：</span>
          <span class="memory-value">{{ stats.memory_used_mb }} MB</span>
        </div>
        <div class="memory-item">
          <span class="memory-label">峰值：</span>
          <span class="memory-value">{{ stats.peak_memory_mb }} MB</span>
        </div>
        <div class="memory-item">
          <span class="memory-label">Redis 主機：</span>
          <span class="memory-value">{{ stats.redis_host }}:{{ stats.redis_port }}</span>
        </div>
      </div>
    </div>

    <!-- 操作按鈕 -->
    <div class="actions">
      <button @click="fetchCacheStats" class="btn-primary" :disabled="loading">
        <span v-if="loading">⏳</span>
        <span v-else>🔄</span>
        刷新統計
      </button>
      <button @click="confirmClearCache" class="btn-danger" :disabled="loading">
        <span v-if="loading">⏳</span>
        <span v-else>🗑️</span>
        清除所有緩存
      </button>
    </div>

    <!-- 緩存配置資訊 -->
    <div class="config-info">
      <h3>⚙️ 緩存配置</h3>
      <div class="config-grid">
        <div class="config-item">
          <span class="config-label">狀態：</span>
          <span class="config-value" :class="stats.enabled ? 'enabled' : 'disabled'">
            {{ stats.enabled ? '✅ 已啟用' : '❌ 已停用' }}
          </span>
        </div>
        <div class="config-item">
          <span class="config-label">問題緩存 TTL：</span>
          <span class="config-value">{{ formatTTL(stats.ttl_config?.question_cache) }}</span>
        </div>
        <div class="config-item">
          <span class="config-label">向量緩存 TTL：</span>
          <span class="config-value">{{ formatTTL(stats.ttl_config?.vector_cache) }}</span>
        </div>
        <div class="config-item">
          <span class="config-label">RAG 結果 TTL：</span>
          <span class="config-value">{{ formatTTL(stats.ttl_config?.rag_result_cache) }}</span>
        </div>
      </div>
      <div class="config-note">
        💡 提示：可通過環境變量 CACHE_TTL_* 調整 TTL 配置
      </div>
    </div>
  </div>
</template>

<script>
import { API_BASE_URL } from '@/config/api';

const RAG_API = `${API_BASE_URL}/rag-api/v1`;

export default {
  name: 'CacheManagementView',
  data() {
    return {
      stats: {},
      health: {},
      loading: false,
    };
  },
  computed: {
    healthStatusClass() {
      if (!this.health.status) return 'status-unknown';
      return `status-${this.health.status}`;
    },
    healthStatusIcon() {
      const icons = {
        healthy: '✅',
        unhealthy: '❌',
        disabled: '⚠️',
        unknown: '❓'
      };
      return icons[this.health.status] || '❓';
    },
    healthStatusTitle() {
      const titles = {
        healthy: '緩存服務正常',
        unhealthy: '緩存服務異常',
        disabled: '緩存服務已停用',
        unknown: '狀態未知'
      };
      return titles[this.health.status] || '狀態未知';
    },
    healthStatusMessage() {
      if (this.health.status === 'healthy') {
        return 'Redis 連接正常，讀寫測試通過';
      } else if (this.health.status === 'disabled') {
        return '緩存功能已停用（CACHE_ENABLED=false）';
      } else if (this.health.error) {
        return `錯誤：${this.health.error}`;
      }
      return '正在檢查緩存狀態...';
    }
  },
  mounted() {
    this.fetchCacheStats();
    this.fetchCacheHealth();
  },
  methods: {
    async fetchCacheStats() {
      this.loading = true;
      try {
        const response = await fetch(`${RAG_API}/cache/stats`);
        if (response.ok) {
          this.stats = await response.json();
        } else {
          console.error('獲取緩存統計失敗:', response.statusText);
        }
      } catch (error) {
        console.error('獲取緩存統計錯誤:', error);
        alert('無法連接到 RAG Orchestrator 服務');
      } finally {
        this.loading = false;
      }
    },
    async fetchCacheHealth() {
      try {
        const response = await fetch(`${RAG_API}/cache/health`);
        if (response.ok) {
          this.health = await response.json();
        } else {
          this.health = { status: 'unhealthy', error: response.statusText };
        }
      } catch (error) {
        console.error('獲取緩存健康狀態錯誤:', error);
        this.health = { status: 'unknown', error: error.message };
      }
    },
    confirmClearCache() {
      if (confirm('確定要清除所有緩存嗎？此操作不可恢復。')) {
        this.clearAllCache();
      }
    },
    async clearAllCache() {
      this.loading = true;
      try {
        const response = await fetch(`${RAG_API}/cache/clear`, {
          method: 'DELETE'
        });
        if (response.ok) {
          const result = await response.json();
          alert(result.message || '所有緩存已清除');
          // 重新載入統計
          await this.fetchCacheStats();
        } else {
          alert('清除緩存失敗：' + response.statusText);
        }
      } catch (error) {
        console.error('清除緩存錯誤:', error);
        alert('清除緩存失敗：' + error.message);
      } finally {
        this.loading = false;
      }
    },
    formatTTL(seconds) {
      if (!seconds) return 'N/A';
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      if (hours > 0) {
        return `${hours} 小時${minutes > 0 ? ` ${minutes} 分鐘` : ''}`;
      }
      return `${minutes} 分鐘`;
    }
  }
};
</script>

<style scoped>
.cache-management-view {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

h2 {
  margin-bottom: 20px;
  color: #2c3e50;
}

h3 {
  margin: 0 0 15px 0;
  font-size: 1.1rem;
  color: #34495e;
}

/* 健康狀態 */
.health-status {
  display: flex;
  align-items: center;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  border: 2px solid;
}

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

.status-disabled {
  background: #fff3cd;
  border-color: #ffc107;
  color: #856404;
}

.status-unknown {
  background: #e7f3ff;
  border-color: #007bff;
  color: #004085;
}

.status-icon {
  font-size: 2rem;
  margin-right: 15px;
}

.status-info {
  flex: 1;
}

.status-title {
  font-size: 1.2rem;
  font-weight: bold;
  margin-bottom: 5px;
}

.status-message {
  font-size: 0.9rem;
  opacity: 0.9;
}

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

/* 統計卡片 */
.stats-grid {
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
}

.stat-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.stat-icon {
  font-size: 2.5rem;
  margin-right: 15px;
}

.stat-content {
  flex: 1;
}

.stat-label {
  font-size: 0.9rem;
  margin-bottom: 5px;
}

.stat-value {
  font-size: 2rem;
  color: #2c3e50;
}

.stat-meta {
  font-size: 0.8rem;
  color: #999;
  margin-top: 5px;
}

/* 內存卡片 */
.memory-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.memory-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.memory-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 4px;
}

.memory-label {
  color: #666;
  font-size: 0.9rem;
}

.memory-value {
  font-weight: bold;
  color: #2c3e50;
}

/* 操作按鈕 */
.actions {
  gap: 10px;
  margin-bottom: 20px;
}


/* 配置資訊 */
.config-info {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 15px;
  margin-bottom: 15px;
}

.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 4px;
}

.config-label {
  color: #666;
  font-size: 0.9rem;
}

.config-value {
  font-weight: bold;
  color: #2c3e50;
}

.config-value.enabled {
  color: #28a745;
}

.config-value.disabled {
  color: #dc3545;
}

.config-note {
  padding: 10px;
  background: #e7f3ff;
  border-left: 3px solid #007bff;
  border-radius: 4px;
  font-size: 0.9rem;
  color: #004085;
}
</style>
