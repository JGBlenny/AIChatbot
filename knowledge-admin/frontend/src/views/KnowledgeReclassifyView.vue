<template>
  <div class="knowledge-reclassify-container">
    <!-- ⚠️ 孤兒頁（2026-09-11 盤查）：⚠️ 本頁**不在 `router.js` 的路由表中**，使用者目前到不了；且它打的 `/intents` 端點**從未掛載過**（`app.py` 的 include_router 清單裡沒有），而 `/knowledge/classify/batch` 仍在線。⇒ 即使補上路由，意圖那半也不會動。⛔ 兩者都不是本次舊鏈退役造成的。 -->
    <h2>⚙️ 知識庫意圖分類工具</h2>

    <!-- 說明區塊 -->
    <InfoPanel :config="helpTexts.knowledgeReclassify" />

    <!-- 步驟指示 -->
    <div class="steps-guide">
      <div class="step" :class="{ active: currentStep >= 1 }">
        <div class="step-number">1</div>
        <div class="step-content">
          <div class="step-title">查看統計</div>
          <div class="step-desc">了解知識庫的分類狀況</div>
        </div>
      </div>
      <div class="step-arrow">→</div>
      <div class="step" :class="{ active: currentStep >= 2 }">
        <div class="step-number">2</div>
        <div class="step-content">
          <div class="step-title">選擇快捷操作</div>
          <div class="step-desc">決定要處理哪些知識</div>
        </div>
      </div>
      <div class="step-arrow">→</div>
      <div class="step" :class="{ active: currentStep >= 3 }">
        <div class="step-number">3</div>
        <div class="step-content">
          <div class="step-title">預覽並執行</div>
          <div class="step-desc">確認影響範圍後開始</div>
        </div>
      </div>
    </div>

    <!-- 統計資訊 -->
    <div class="section-card">
      <div class="section-header">
        <h3>📊 步驟 1: 當前統計</h3>
      </div>

      <div class="stats-cards" v-if="stats">
        <div class="stat-card">
          <div class="stat-label">總知識數</div>
          <div class="stat-value">{{ stats.overall.total_knowledge }}</div>
        </div>
        <div class="stat-card highlight-success">
          <div class="stat-label">✅ 已分類</div>
          <div class="stat-value">{{ stats.overall.classified_count }}</div>
          <div class="stat-detail">{{ getPercentage(stats.overall.classified_count, stats.overall.total_knowledge) }}</div>
        </div>
        <div class="stat-card highlight-warning">
          <div class="stat-label">⚠️ 未分類</div>
          <div class="stat-value">{{ stats.overall.unclassified_count }}</div>
          <div class="stat-detail">需要處理</div>
        </div>
        <div class="stat-card highlight-info">
          <div class="stat-label">📉 低信心度</div>
          <div class="stat-value">{{ stats.overall.low_confidence_count }}</div>
          <div class="stat-detail">&lt; 0.7</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">平均信心度</div>
          <div class="stat-value medium">
            {{ stats.overall.avg_confidence ? stats.overall.avg_confidence.toFixed(2) : 'N/A' }}
          </div>
        </div>
      </div>

      <div v-else class="loading-state">
        <p>⏳ 載入統計資訊中...</p>
      </div>
    </div>

    <!-- 快捷操作 -->
    <div class="section-card">
      <div class="section-header">
        <h3>⚡ 步驟 2: 快捷操作</h3>
        <p class="section-desc">一鍵處理常見場景</p>
      </div>

      <div class="quick-actions">
        <div class="quick-action-card" @click="quickActionLowConfidence">
          <div class="qa-icon">📉</div>
          <div class="qa-title">處理低信心度知識</div>
          <div class="qa-desc">意圖分類所有信心度 &lt; 0.7 的知識</div>
          <div class="qa-badge" v-if="stats">{{ stats.overall.low_confidence_count }} 筆</div>
        </div>

        <div class="quick-action-card" @click="quickActionUnclassified">
          <div class="qa-icon">📦</div>
          <div class="qa-title">分類未分類知識</div>
          <div class="qa-desc">自動分類所有尚未指定意圖的知識</div>
          <div class="qa-badge" v-if="stats">{{ stats.overall.unclassified_count }} 筆</div>
        </div>
      </div>
    </div>


    <!-- 預估資訊 -->
    <div class="section-card preview-card" v-if="preview">
      <div class="section-header">
        <h3>📊 預估結果</h3>
      </div>
      <div class="preview-grid">
        <div class="preview-item">
          <div class="preview-label">符合條件的知識</div>
          <div class="preview-value">{{ preview.total_to_process }} 筆</div>
        </div>
        <div class="preview-item">
          <div class="preview-label">預估批次數</div>
          <div class="preview-value">{{ preview.estimated_batches }}</div>
        </div>
        <div class="preview-item">
          <div class="preview-label">預估 API 成本</div>
          <div class="preview-value">${{ (preview.total_to_process * 0.002).toFixed(2) }}</div>
        </div>
        <div class="preview-item">
          <div class="preview-label">預估處理時間</div>
          <div class="preview-value">{{ Math.ceil(preview.total_to_process / 10) }} 分鐘</div>
        </div>
      </div>

      <!-- 知識列表詳情 -->
      <div v-if="preview.preview_items && preview.preview_items.length > 0" class="preview-knowledge-list">
        <div class="preview-list-header">
          <div>
            <h4>📋 知識列表示例</h4>
            <p class="preview-hint">
              <span v-if="preview.has_more" class="warning-text">
                ⚠️ 顯示前 {{ preview.preview_limit }} 筆示例，
                還有 <strong>{{ preview.total_to_process - preview.preview_limit }}</strong> 筆未顯示
              </span>
              <span v-else class="info-text">
                ✓ 共 {{ preview.preview_items.length }} 筆，已全部顯示
              </span>
            </p>
          </div>
          <button @click="showPreviewDetails = !showPreviewDetails" class="btn-primary btn-sm btn-toggle-details">
            {{ showPreviewDetails ? '▼ 收起' : '▶ 展開詳情' }}
          </button>
        </div>

        <div v-if="showPreviewDetails" class="knowledge-items">
          <div v-for="item in preview.preview_items" :key="item.id" class="knowledge-item">
            <div class="knowledge-item-header">
              <span class="knowledge-id">ID: {{ item.id }}</span>
              <span v-if="item.current_intent_name" class="knowledge-current-intent">
                當前意圖: {{ item.current_intent_name }}
              </span>
              <span v-else class="knowledge-unclassified">未分類</span>
              <span v-if="item.current_confidence"
                    :class="['knowledge-confidence', getConfidenceClass(item.current_confidence)]">
                信心度: {{ item.current_confidence.toFixed(2) }}
              </span>
            </div>
            <div class="knowledge-item-body">
              <div v-if="item.question_summary" class="knowledge-question">
                <strong>問題：</strong>{{ item.question_summary }}
              </div>
              <div class="knowledge-answer">
                <strong>答案：</strong>{{ item.answer }}
              </div>
              <div class="knowledge-meta">
                <span v-if="item.assigned_by">
                  分類來源: {{ item.assigned_by === 'auto' ? '自動' : '手動' }}
                </span>
                <span v-if="item.classified_at">
                  分類時間: {{ formatDate(item.classified_at) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 操作按鈕 -->
    <div class="section-card">
      <div class="section-header">
        <h3>🚀 步驟 3: 執行操作</h3>
        <p class="section-desc">先預覽確認影響範圍，再開始執行</p>
      </div>

      <div class="actions">
        <button @click="previewReclassify" class="btn-info btn-sm" :disabled="loading">
          🔍 步驟 3.1: 預覽結果
        </button>
        <button @click="startReclassify" class="btn-primary btn-sm" :disabled="loading || !preview">
          🚀 步驟 3.2: 開始意圖分類
        </button>
        <button @click="resetAll" class="btn-secondary btn-sm" :disabled="loading">
          ↺ 重置所有設定
        </button>
      </div>

      <div class="action-hints">
        <p v-if="!preview" class="hint warning">⚠️ 請先點擊「預覽結果」查看會處理多少筆知識</p>
        <p v-else class="hint success">✅ 已預覽完成，確認後可開始執行</p>
      </div>
    </div>

    <!-- 處理進度 -->
    <div class="section-card progress-card" v-if="processing">
      <div class="section-header">
        <h3>⏳ 處理中...</h3>
      </div>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progress + '%' }"></div>
        <div class="progress-text">{{ progress }}%</div>
      </div>
      <p class="process-status">{{ processStatus }}</p>
    </div>

    <!-- 處理結果 -->
    <div class="section-card result-card" v-if="result">
      <div class="section-header">
        <h3>✅ 處理完成</h3>
      </div>
      <div class="result-grid">
        <div class="result-item">
          <div class="result-label">總處理數</div>
          <div class="result-value">{{ result.total_processed }}</div>
        </div>
        <div class="result-item success">
          <div class="result-label">✅ 成功</div>
          <div class="result-value">{{ result.success_count }}</div>
        </div>
        <div class="result-item danger">
          <div class="result-label">❌ 失敗</div>
          <div class="result-value">{{ result.failed_count }}</div>
        </div>
        <div class="result-item warning">
          <div class="result-label">❓ Unclear</div>
          <div class="result-value">{{ result.unclear_count }}</div>
        </div>
      </div>
      <p class="result-note">💡 統計資訊已自動更新，可查看上方統計卡片</p>

      <!-- 詳細結果列表 -->
      <div v-if="result.details && result.details.length > 0" class="result-details-section">
        <div class="result-details-header">
          <h4>📋 分類詳情</h4>
          <button @click="showResultDetails = !showResultDetails" class="btn-toggle-details">
            {{ showResultDetails ? '▼ 收起' : '▶ 展開詳情' }}
          </button>
        </div>

        <div v-if="showResultDetails" class="result-items">
          <div v-for="item in result.details" :key="item.knowledge_id" class="result-detail-item">
            <div class="result-item-header">
              <span class="knowledge-id">ID: {{ item.knowledge_id }}</span>
              <span v-if="item.classified" class="status-badge success">✅ 成功</span>
              <span v-else-if="item.intent_name === 'unclear'" class="status-badge unclear">❓ Unclear</span>
              <span v-else class="status-badge failed">❌ 失敗</span>
            </div>

            <div v-if="item.classified" class="result-item-intents">
              <div class="intent-label">分配意圖:</div>
              <div class="intent-badges">
                <span class="intent-badge primary">
                  ★ {{ item.intent_name }}
                </span>
                <span
                  v-for="secondaryIntent in item.secondary_intents || []"
                  :key="secondaryIntent"
                  class="intent-badge secondary"
                >
                  {{ secondaryIntent }}
                </span>
              </div>
              <div class="result-item-meta">
                <span class="confidence-badge" :class="getConfidenceClass(item.confidence)">
                  信心度: {{ item.confidence ? item.confidence.toFixed(2) : 'N/A' }}
                </span>
              </div>
            </div>

            <div v-else-if="item.intent_name === 'unclear'" class="result-item-unclear">
              <span class="unclear-reason">{{ item.reason || '信心度過低或意圖不明確' }}</span>
              <span class="confidence-badge confidence-low">
                信心度: {{ item.confidence ? item.confidence.toFixed(2) : 'N/A' }}
              </span>
            </div>

            <div v-else class="result-item-error">
              <span class="error-reason">❌ {{ item.reason || item.error || '分類失敗' }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 按意圖統計 -->
    <div class="section-card" v-if="stats && stats.by_intent && stats.by_intent.length > 0">
      <div class="section-header">
        <h3>📈 按意圖統計</h3>
      </div>
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>意圖名稱</th>
              <th>類型</th>
              <th>知識數量</th>
              <th>平均信心度</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in stats.by_intent.filter(i => i.knowledge_count > 0)" :key="item.id">
              <td><strong>{{ item.name }}</strong></td>
              <td>
                <span :class="`type-badge type-${item.type}`">
                  {{ typeLabels[item.type] || item.type }}
                </span>
              </td>
              <td>{{ item.knowledge_count }}</td>
              <td>
                <span :class="getConfidenceClass(item.avg_confidence)">
                  {{ item.avg_confidence ? item.avg_confidence.toFixed(2) : 'N/A' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import InfoPanel from '@/components/InfoPanel.vue';
import helpTexts from '@/config/help-texts.js';
import { API_BASE_URL } from '@/config/api';

const RAG_API = `${API_BASE_URL}/rag-api/v1`;

export default {
  name: 'KnowledgeReclassifyView',
  components: {
    InfoPanel
  },
  data() {
    return {
      helpTexts,
      currentStep: 1,
      stats: null,
      intents: [],
      filters: {
        selectedIntents: [],
        confidenceMode: 'all',
        customConfidence: 0.7,
        olderThanDays: null,
        assignedBy: '',
        unclassified: false
      },
      batchSize: 100,
      preview: null,
      showPreviewDetails: false,
      showResultDetails: false,
      loading: false,
      processing: false,
      progress: 0,
      processStatus: '',
      result: null,
      typeLabels: {
        knowledge: '知識',
        data_query: '資料查詢',
        action: '動作',
        hybrid: '混合'
      }
    };
  },
  mounted() {
    this.loadStats();
    this.loadIntents();
  },
  methods: {
    async loadStats() {
      this.loading = true;
      try {
        const response = await axios.get(`${RAG_API}/knowledge/stats`);
        this.stats = response.data;
        this.currentStep = Math.max(this.currentStep, 1);
      } catch (error) {
        console.error('載入統計失敗:', error);
        alert('載入統計失敗: ' + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },

    async loadIntents() {
      try {
        const response = await axios.get(`${RAG_API}/intents`);
        this.intents = response.data.intents;
      } catch (error) {
        console.error('載入意圖列表失敗:', error);
      }
    },

    quickActionLowConfidence() {
      this.filters = {
        selectedIntents: [],
        confidenceMode: 'low',
        customConfidence: 0.7,
        olderThanDays: null,
        assignedBy: '',
        unclassified: false
      };
      this.currentStep = 2;
      this.previewReclassify();
    },

    quickActionUnclassified() {
      this.filters = {
        selectedIntents: [],
        confidenceMode: 'all',
        customConfidence: 0.7,
        olderThanDays: null,
        assignedBy: '',
        unclassified: true
      };
      this.currentStep = 2;
      this.previewReclassify();
    },

    buildFilters() {
      const filters = {};

      // 未分類過濾器
      if (this.filters.unclassified) {
        filters.unclassified = true;
      }

      if (this.filters.selectedIntents && this.filters.selectedIntents.length > 0) {
        filters.intent_ids = this.filters.selectedIntents.filter(id => id !== '');
      }

      if (this.filters.confidenceMode === 'low') {
        filters.max_confidence = 0.7;
      } else if (this.filters.confidenceMode === 'custom') {
        filters.max_confidence = this.filters.customConfidence;
      }

      if (this.filters.olderThanDays) {
        filters.older_than_days = this.filters.olderThanDays;
      }

      if (this.filters.assignedBy) {
        filters.assigned_by = this.filters.assignedBy;
      }

      return filters;
    },

    async previewReclassify() {
      this.loading = true;
      try {
        const payload = {
          filters: this.buildFilters(),
          batch_size: this.batchSize,
          dry_run: true
        };

        const response = await axios.post(`${RAG_API}/knowledge/classify/batch`, payload);
        this.preview = response.data;
        this.currentStep = 3;

        if (this.preview.total_to_process === 0) {
          alert('⚠️ 沒有符合條件的知識需要處理');
        } else {
          alert(`✅ 預覽完成！\n\n將處理 ${this.preview.total_to_process} 筆知識\n預估成本: $${(this.preview.total_to_process * 0.002).toFixed(2)} USD`);
        }
      } catch (error) {
        console.error('預覽失敗:', error);
        alert('預覽失敗: ' + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },

    async startReclassify() {
      if (!this.preview) {
        alert('請先點擊「預覽結果」');
        return;
      }

      if (this.preview.total_to_process === 0) {
        alert('沒有需要處理的知識');
        return;
      }

      if (!confirm(`確定要意圖分類 ${this.preview.total_to_process} 筆知識嗎？\n\n預估成本: $${(this.preview.total_to_process * 0.002).toFixed(2)} USD\n預估時間: ${Math.ceil(this.preview.total_to_process / 10)} 分鐘`)) {
        return;
      }

      this.processing = true;
      this.progress = 0;
      this.processStatus = '開始處理...';

      // 初始化累積結果
      const accumulatedResult = {
        total_processed: 0,
        success_count: 0,
        failed_count: 0,
        unclear_count: 0,
        details: []
      };

      try {
        const totalToProcess = this.preview.total_to_process;
        let processedCount = 0;

        // 循環處理直到所有項目都處理完
        while (processedCount < totalToProcess) {
          const payload = {
            filters: this.buildFilters(),
            batch_size: this.batchSize,
            dry_run: false
          };

          // 更新狀態
          this.processStatus = `處理中... ${processedCount}/${totalToProcess}`;
          this.progress = Math.floor((processedCount / totalToProcess) * 100);

          // 發送批次請求
          const response = await axios.post(`${RAG_API}/knowledge/classify/batch`, payload);
          const batchResult = response.data;

          // 累積結果
          accumulatedResult.total_processed += batchResult.total_processed || 0;
          accumulatedResult.success_count += batchResult.success_count || 0;
          accumulatedResult.failed_count += batchResult.failed_count || 0;
          accumulatedResult.unclear_count += batchResult.unclear_count || 0;

          // 累積詳細結果
          if (batchResult.details && Array.isArray(batchResult.details)) {
            accumulatedResult.details.push(...batchResult.details);
          }

          processedCount += batchResult.total_processed || 0;

          // 如果這一批沒有處理任何項目，可能是所有符合條件的都已處理完畢
          if (batchResult.total_processed === 0) {
            console.log('本批次沒有處理任何項目，停止循環');
            break;
          }

          // 稍微延遲避免 API 請求過於密集
          if (processedCount < totalToProcess) {
            await new Promise(resolve => setTimeout(resolve, 500));
          }
        }

        // 設定最終結果
        this.result = accumulatedResult;
        this.progress = 100;
        this.processStatus = '處理完成！';

        alert(`✅ 意圖分類完成！\n\n總處理數: ${this.result.total_processed}\n成功: ${this.result.success_count}\n失敗: ${this.result.failed_count}\nUnclear: ${this.result.unclear_count}`);

        // 重新載入統計
        await this.loadStats();

        // 清除預覽，讓用戶可以重新預覽
        this.preview = null;

      } catch (error) {
        console.error('意圖分類失敗:', error);
        alert('意圖分類失敗: ' + (error.response?.data?.detail || error.message));
      } finally {
        this.processing = false;
      }
    },

    resetAll() {
      this.filters = {
        selectedIntents: [],
        confidenceMode: 'all',
        customConfidence: 0.7,
        olderThanDays: null,
        assignedBy: '',
        unclassified: false
      };
      this.batchSize = 100;
      this.preview = null;
      this.result = null;
      this.currentStep = 1;
    },

    getPercentage(value, total) {
      if (total === 0) return '0%';
      return Math.round((value / total) * 100) + '%';
    },

    getConfidenceClass(confidence) {
      if (!confidence) return '';
      if (confidence >= 0.8) return 'confidence-high';
      if (confidence >= 0.7) return 'confidence-medium';
      return 'confidence-low';
    },

    formatDate(dateStr) {
      if (!dateStr) return 'N/A';
      const date = new Date(dateStr);
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
.knowledge-reclassify-container {
  /* width 和 margin 由 app-main 統一管理 */
}

/* 頁面標題 */

.page-header h2 {
  margin: 0;
  color: #333;
}

/* btn-refresh 改用全域 .btn-info .btn-sm */

/* 步驟指示 */
.steps-guide {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 30px;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
}

.step {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 15px 20px;
  background: rgba(255,255,255,0.2);
  border-radius: 8px;
  opacity: 0.6;
  transition: all 0.3s;
}

.step.active {
  opacity: 1;
  background: rgba(255,255,255,0.3);
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}

.step-number {
  width: 32px;
  height: 32px;
  background: white;
  color: #667eea;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 16px;
}

.step-content {
  color: white;
}

.step-title {
  font-weight: bold;
  font-size: 14px;
}

.step-desc {
  font-size: 12px;
  opacity: 0.9;
}

.step-arrow {
  color: white;
  font-size: 24px;
  opacity: 0.6;
}

/* 區塊卡片 */
.section-card {
  background: white;
  border-radius: 12px;
  padding: 25px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.section-header {
  margin-bottom: 20px;
  position: relative;
}

.section-header h3 {
  margin: 0 0 5px 0;
  color: #333;
  font-size: 18px;
}

.section-desc {
  color: #666;
  font-size: 14px;
  margin: 5px 0 0 0;
}

/* 統計卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 15px;
}

.stat-card {
  background: #f8f9fa;
  transition: all 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.stat-card.highlight-success {
  background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
  border: 2px solid #28a745;
}

.stat-card.highlight-warning {
  background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
  border: 2px solid #ffc107;
}

.stat-card.highlight-danger {
  background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
  border: 2px solid #dc3545;
}

.stat-card.highlight-info {
  background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
  border: 2px solid #17a2b8;
}

.stat-label {
  margin-bottom: 8px;
  font-weight: 500;
}

.stat-value {
  font-size: 28px;
  color: #333;
  margin-bottom: 5px;
}

.stat-value.medium {
  font-size: 24px;
}

.stat-detail {
  font-size: 12px;
  color: #888;
}

/* 快捷操作 */
.quick-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
}

.quick-action-card {
  padding: 25px;
  border: 2px solid #e9ecef;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
}

.quick-action-card:hover {
  border-color: #667eea;
  transform: translateY(-4px);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.3);
}

.qa-icon {
  font-size: 40px;
  margin-bottom: 15px;
}

.qa-title {
  font-size: 16px;
  font-weight: bold;
  color: #333;
  margin-bottom: 8px;
}

.qa-desc {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
}

.qa-badge {
  position: absolute;
  top: 15px;
  right: 15px;
  background: #667eea;
  color: white;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: bold;
}

/* 預覽卡片 */
.preview-card {
  background: linear-gradient(135deg, #e7f3ff 0%, #d4e9ff 100%);
  border: 2px solid #007bff;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 20px;
}

.preview-item {
  text-align: center;
}

.preview-label {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
}

.preview-value {
  font-size: 24px;
  font-weight: bold;
  color: #007bff;
}

/* 操作按鈕 - 改用全域 CSS */
.actions {
  gap: 15px;
  margin-bottom: 15px;
  flex-wrap: wrap;
}

.action-hints {
  margin-top: 10px;
}

.hint {
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 14px;
  margin: 0;
}

.hint.warning {
  background: #fff3cd;
  color: #856404;
  border-left: 4px solid #ffc107;
}

.hint.success {
  background: #d4edda;
  color: #155724;
  border-left: 4px solid #28a745;
}

/* 進度卡片 */
.progress-card {
  background: linear-gradient(135deg, #fff9e6 0%, #fff3cd 100%);
  border: 2px solid #ffc107;
}

.progress-bar {
  width: 100%;
  height: 40px;
  background: #e9ecef;
  border-radius: 20px;
  overflow: hidden;
  margin: 15px 0;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  transition: width 0.5s ease-out;
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-weight: bold;
  color: #333;
  z-index: 1;
}

.process-status {
  text-align: center;
  color: #666;
  font-size: 14px;
}

/* 結果卡片 */
.result-card {
  background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
  border: 2px solid #28a745;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  margin-bottom: 15px;
}

.result-item {
  padding: 15px;
  background: white;
  border-radius: 8px;
  text-align: center;
}

.result-item.success {
  border-left: 4px solid #28a745;
}

.result-item.danger {
  border-left: 4px solid #dc3545;
}

.result-item.warning {
  border-left: 4px solid #ffc107;
}

.result-label {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
}

.result-value {
  font-size: 24px;
  font-weight: bold;
  color: #333;
}

.result-note {
  text-align: center;
  color: #666;
  font-size: 14px;
  margin: 15px 0 0 0;
}

/* 統計表格 */
.table-responsive {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e9ecef;
}

.data-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #495057;
  font-size: 13px;
}

.data-table tr:hover {
  background: #f8f9fa;
}

.type-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  display: inline-block;
}

.type-knowledge { background: #e3f2fd; color: #1976d2; }
.type-data_query { background: #f3e5f5; color: #7b1fa2; }
.type-action { background: #fff3e0; color: #f57c00; }
.type-hybrid { background: #e8f5e9; color: #388e3c; }

.confidence-high {
  color: #28a745;
  font-weight: bold;
}

.confidence-medium {
  color: #ffc107;
  font-weight: bold;
}

.confidence-low {
  color: #dc3545;
  font-weight: bold;
}

.loading-state {
  text-align: center;
  padding: 40px;
  color: #666;
}

/* 預覽知識列表 */
.preview-knowledge-list {
  margin-top: 25px;
  padding-top: 25px;
  border-top: 2px solid rgba(0,123,255,0.2);
}

.preview-list-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
  gap: 15px;
}

.preview-list-header h4 {
  margin: 0 0 5px 0;
  color: #333;
  font-size: 16px;
}

.preview-hint {
  margin: 5px 0 0 0;
  font-size: 13px;
}

.warning-text {
  color: #856404;
  background: #fff3cd;
  padding: 6px 12px;
  border-radius: 4px;
  display: inline-block;
  border-left: 3px solid #ffc107;
}

.info-text {
  color: #155724;
  background: #d4edda;
  padding: 6px 12px;
  border-radius: 4px;
  display: inline-block;
  border-left: 3px solid #28a745;
}

/* btn-toggle-details 改用全域 .btn-primary .btn-sm */
.btn-toggle-details {
  white-space: nowrap;
  flex-shrink: 0;
}

.knowledge-items {
  display: flex;
  flex-direction: column;
  gap: 15px;
  max-height: 500px;
  overflow-y: auto;
  padding-right: 10px;
}

.knowledge-item {
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 15px;
  transition: all 0.2s;
}

.knowledge-item:hover {
  border-color: #007bff;
  box-shadow: 0 2px 8px rgba(0,123,255,0.15);
}

.knowledge-item-header {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f0f0f0;
}

.knowledge-id {
  font-weight: bold;
  color: #495057;
  background: #f8f9fa;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
}

.knowledge-current-intent {
  background: #e3f2fd;
  color: #1976d2;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
}

.knowledge-unclassified {
  background: #fff3cd;
  color: #856404;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
}

.knowledge-confidence {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: bold;
}

.knowledge-item-body {
  font-size: 14px;
  line-height: 1.6;
}

.knowledge-question {
  margin-bottom: 10px;
  padding: 10px;
  background: #f8f9fa;
  border-left: 3px solid #007bff;
  border-radius: 4px;
}

.knowledge-answer {
  margin-bottom: 10px;
  padding: 10px;
  background: #f1f8ff;
  border-left: 3px solid #28a745;
  border-radius: 4px;
}

.knowledge-meta {
  display: flex;
  gap: 20px;
  font-size: 12px;
  color: #6c757d;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #f0f0f0;
}

.knowledge-meta span {
  display: flex;
  align-items: center;
  gap: 5px;
}

/* 滾動條樣式 */
.knowledge-items::-webkit-scrollbar {
  width: 8px;
}

.knowledge-items::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.knowledge-items::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;
}

.knowledge-items::-webkit-scrollbar-thumb:hover {
  background: #555;
}

/* 結果詳情樣式 */
.result-details-section {
  margin-top: 25px;
  padding-top: 25px;
  border-top: 2px solid rgba(40, 167, 69, 0.2);
}

.result-details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.result-details-header h4 {
  margin: 0;
  color: #333;
  font-size: 16px;
}

.result-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 500px;
  overflow-y: auto;
  padding-right: 10px;
}

.result-detail-item {
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 15px;
  transition: all 0.2s;
}

.result-detail-item:hover {
  border-color: #28a745;
  box-shadow: 0 2px 8px rgba(40, 167, 69, 0.15);
}

.result-item-header {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f0f0f0;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.status-badge.success {
  background: #d4edda;
  color: #155724;
}

.status-badge.failed {
  background: #f8d7da;
  color: #721c24;
}

.status-badge.unclear {
  background: #fff3cd;
  color: #856404;
}

.result-item-intents {
  padding: 10px;
  background: #f8f9fa;
  border-radius: 6px;
}

.intent-label {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
  font-weight: 500;
}

.intent-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}

.intent-badge {
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  display: inline-block;
}

.intent-badge.primary {
  background: #409EFF;
  color: white;
  font-weight: bold;
}

.intent-badge.secondary {
  background: #67C23A;
  color: white;
}

.result-item-meta {
  display: flex;
  gap: 10px;
  font-size: 12px;
  color: #6c757d;
}

.confidence-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
}

.result-item-unclear {
  padding: 10px;
  background: #fff3cd;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.unclear-reason {
  color: #856404;
  font-size: 13px;
}

.result-item-error {
  padding: 10px;
  background: #f8d7da;
  border-radius: 6px;
}

.error-reason {
  color: #721c24;
  font-size: 13px;
  font-weight: 500;
}

/* 結果詳情滾動條 */
.result-items::-webkit-scrollbar {
  width: 8px;
}

.result-items::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.result-items::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;
}

.result-items::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>
