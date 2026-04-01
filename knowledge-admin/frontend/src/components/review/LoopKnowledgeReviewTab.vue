<template>
  <div class="loop-knowledge-review-tab">
    <!-- 統計區域 -->
    <div class="stats-section" v-if="stats">
      <div class="stat-card">
        <div class="stat-value">{{ stats.pending_count }}</div>
        <div class="stat-label">待審核（全部）</div>
      </div>
      <div class="stat-card sop">
        <div class="stat-value">{{ stats.sop_pending_count }}</div>
        <div class="stat-label">待審核 SOP</div>
      </div>
      <div class="stat-card approved">
        <div class="stat-value">{{ stats.approved_count }}</div>
        <div class="stat-label">已通過</div>
      </div>
      <div class="stat-card rejected">
        <div class="stat-value">{{ stats.rejected_count }}</div>
        <div class="stat-label">已拒絕</div>
      </div>
    </div>

    <!-- 篩選器 -->
    <div class="filter-section">
      <label>
        類型篩選：
        <select v-model="filterType" @change="loadItems">
          <option value="">全部</option>
          <option value="sop">僅 SOP</option>
          <option value="general">一般知識</option>
        </select>
      </label>
      <button @click="loadItems" class="refresh-btn">🔄 重新整理</button>
    </div>

    <!-- 全選區域 -->
    <div class="select-all-section" v-if="items.length > 0">
      <label class="select-all-label">
        <input
          type="checkbox"
          :checked="allSelected"
          :indeterminate.prop="someSelected"
          @change="toggleSelectAll"
          class="select-checkbox"
        />
        <span>全選（已選取 {{ selectedIds.length }} / {{ items.length }} 項）</span>
      </label>
    </div>

    <!-- 批量操作工具列 -->
    <div class="batch-action-toolbar" v-if="selectedIds.length > 0">
      <div class="toolbar-info">
        <span class="selected-count">✓ 已選取 {{ selectedIds.length }} 項</span>
        <button @click="selectedIds = []" class="btn-clear-selection">清除選取</button>
      </div>
      <div class="toolbar-actions">
        <button @click="showBatchApproveDialog" class="btn-batch-approve">
          ✅ 批量批准
        </button>
        <button @click="showBatchRejectDialog" class="btn-batch-reject">
          ❌ 批量拒絕
        </button>
      </div>
    </div>

    <!-- 列表區域 -->
    <div class="items-section" v-if="!loading">
      <div v-if="items.length === 0" class="empty-state">
        <p>✅ 沒有待審核的項目</p>
      </div>

      <div v-for="item in items" :key="item.id" class="knowledge-item">
        <div class="item-checkbox-wrapper">
          <input
            type="checkbox"
            :checked="selectedIds.includes(item.id)"
            @change="toggleSelectItem(item.id)"
            class="item-checkbox"
          />
        </div>
        <div class="item-content">
          <div class="item-header">
            <span class="item-id">#{{ item.id }}</span>
            <span v-if="item.knowledge_type === 'sop'" class="badge sop-badge">SOP</span>
            <span v-else class="badge knowledge-badge">知識</span>
            <span class="loop-info">迴圈 {{ item.loop_id }} - 第 {{ item.iteration }} 次</span>
            <span class="item-date">{{ formatDate(item.created_at) }}</span>
          </div>

        <div class="item-body">
          <div class="question-section">
            <strong>{{ item.knowledge_type === 'sop' ? 'SOP 名稱' : '問題' }}：</strong>
            <p>{{ item.question }}</p>
          </div>

          <div class="answer-section">
            <strong>{{ item.knowledge_type === 'sop' ? 'SOP 內容' : '答案' }}：</strong>
            <p class="answer-text">{{ item.answer }}</p>
          </div>

          <!-- SOP 特殊欄位 -->
          <div v-if="item.sop_config" class="sop-config-section">
            <div class="config-row">
              <strong>觸發模式：</strong>
              <span>{{ item.sop_config.trigger_mode || 'keyword' }}</span>
            </div>
            <div class="config-row">
              <strong>觸發關鍵詞：</strong>
              <span class="keywords">
                <span v-for="(keyword, idx) in item.sop_config.trigger_keywords" :key="idx" class="keyword-tag">
                  {{ keyword }}
                </span>
              </span>
            </div>
            <div class="config-row" v-if="item.sop_config.next_action">
              <strong>後續動作：</strong>
              <span>{{ item.sop_config.next_action }}</span>
            </div>
          </div>

          <!-- 關鍵詞 -->
          <div v-if="item.keywords && item.keywords.length > 0" class="keywords-section">
            <strong>關鍵詞：</strong>
            <span v-for="(keyword, idx) in item.keywords" :key="idx" class="keyword-tag">
              {{ keyword }}
            </span>
          </div>
        </div>

        <!-- 一般知識 Vendor 選擇器 (只在非 SOP 時顯示) -->
        <div v-if="item.knowledge_type !== 'sop'" class="vendor-selector-section">
          <div class="selector-header">
            <strong>業者選擇</strong>
            <span class="hint">（請選擇要同步到哪個業者）</span>
          </div>

          <div class="selector-row">
            <label>
              <strong>業者：</strong>
              <select
                v-model="selectedVendors[item.id]"
                class="select-input"
              >
                <option value="">-- 請選擇業者 --</option>
                <option v-for="vendor in vendors" :key="vendor.id" :value="vendor.id">
                  {{ vendor.name }} ({{ vendor.short_name }})
                </option>
              </select>
            </label>
          </div>
        </div>

        <!-- SOP 選擇器區域 (只在 SOP 時顯示) -->
        <div v-if="item.knowledge_type === 'sop'" class="sop-selector-section">
          <div class="selector-header">
            <strong>SOP 分類資訊</strong>
            <span class="hint">（系統已預填建議值，請確認或修改）</span>
          </div>

          <!-- 業者選擇 -->
          <div class="selector-row">
            <label>
              <strong>業者：</strong>
              <select
                v-model="selectedVendors[item.id]"
                @change="onVendorChange(item.id)"
                class="select-input"
                required
              >
                <option value="">-- 請選擇業者 --</option>
                <option v-for="vendor in vendors" :key="vendor.id" :value="vendor.id">
                  {{ vendor.name }} ({{ vendor.short_name }})
                </option>
              </select>
            </label>
          </div>

          <!-- 類別選擇 (依賴業者) -->
          <div class="selector-row" v-if="selectedVendors[item.id]">
            <label>
              <strong>選擇 SOP 類別：</strong>
              <select
                v-model="selectedCategories[item.id]"
                @change="onCategoryChange(item.id)"
                class="select-input"
                required
              >
                <option value="">-- 請選擇類別 --</option>
                <option
                  v-for="category in (categories[selectedVendors[item.id]] || [])"
                  :key="category.id"
                  :value="category.id"
                >
                  {{ category.name }} {{ category.description ? `(${category.description})` : '' }}
                </option>
              </select>
            </label>
          </div>

          <!-- 群組選擇 (依賴類別，選填) -->
          <div class="selector-row" v-if="selectedVendors[item.id] && selectedCategories[item.id]">
            <label>
              <strong>選擇 SOP 群組（選填）：</strong>
              <select
                v-model="selectedGroups[item.id]"
                class="select-input"
              >
                <option value="">-- 不指定群組 --</option>
                <option
                  v-for="group in (groups[`${selectedVendors[item.id]}-${selectedCategories[item.id]}`] || [])"
                  :key="group.id"
                  :value="group.id"
                >
                  {{ group.name }} {{ group.description ? `(${group.description})` : '' }}
                </option>
              </select>
            </label>
          </div>
        </div>

          <div class="item-actions">
            <input
              v-model="item.reviewNotes"
              type="text"
              placeholder="審核備註（選填）"
              class="review-notes-input"
            />
            <button @click="reviewItem(item, 'approve')" class="btn-approve">
              ✅ 通過
            </button>
            <button @click="reviewItem(item, 'reject')" class="btn-reject">
              ❌ 拒絕
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <p>載入中...</p>
    </div>

    <!-- 批量審核確認對話框 -->
    <div v-if="showConfirmDialog" class="modal-overlay" @click.self="closeConfirmDialog">
      <div class="modal-dialog confirm-dialog">
        <div class="modal-header">
          <h3>{{ batchAction === 'approve' ? '✅ 批量批准確認' : '❌ 批量拒絕確認' }}</h3>
          <button @click="closeConfirmDialog" class="btn-close">✕</button>
        </div>
        <div class="modal-body">
          <div class="confirm-stats">
            <p class="stat-row">
              <span class="stat-label">選取項目數量：</span>
              <span class="stat-value">{{ selectedIds.length }} 項</span>
            </p>
            <p class="stat-row">
              <span class="stat-label">SOP 項目：</span>
              <span class="stat-value">{{ selectedItemsSopCount }} 項</span>
            </p>
            <p class="stat-row">
              <span class="stat-label">一般知識：</span>
              <span class="stat-value">{{ selectedItemsGeneralCount }} 項</span>
            </p>
          </div>
          <div class="warning-section" v-if="batchAction === 'reject'">
            <p>⚠️ 警告：拒絕的項目將無法復原，請確認您的決定。</p>
          </div>
          <div class="notes-section">
            <label>
              <strong>審核備註（選填）：</strong>
              <textarea
                v-model="batchReviewNotes"
                placeholder="輸入批量審核備註..."
                class="batch-notes-textarea"
                rows="3"
              ></textarea>
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="closeConfirmDialog" class="btn-cancel">取消</button>
          <button @click="executeBatchReview" :class="batchAction === 'approve' ? 'btn-confirm-approve' : 'btn-confirm-reject'">
            確定{{ batchAction === 'approve' ? '批准' : '拒絕' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 批量審核進度對話框 -->
    <div v-if="showProgressDialog" class="modal-overlay">
      <div class="modal-dialog progress-dialog">
        <div class="modal-header">
          <h3>⏳ 批量審核進行中...</h3>
        </div>
        <div class="modal-body">
          <div class="progress-stats">
            <p>進度：{{ batchProgress.current }} / {{ batchProgress.total }}</p>
            <p>成功：{{ batchProgress.successCount }} 項</p>
            <p>失敗：{{ batchProgress.failedCount }} 項</p>
          </div>
          <div class="progress-bar-wrapper">
            <div class="progress-bar" :style="{ width: progressPercentage + '%' }"></div>
          </div>
          <div class="current-item" v-if="batchProgress.currentItem">
            <p>正在處理：#{{ batchProgress.currentItem.id }} - {{ batchProgress.currentItem.question }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 批量審核結果對話框 -->
    <div v-if="showResultDialog" class="modal-overlay" @click.self="closeResultDialog">
      <div class="modal-dialog result-dialog">
        <div class="modal-header">
          <h3>{{ batchResult.failedCount === 0 ? '✅ 批量審核完成' : '⚠️ 批量審核完成（部分失敗）' }}</h3>
          <button @click="closeResultDialog" class="btn-close">✕</button>
        </div>
        <div class="modal-body">
          <div class="result-summary">
            <div class="result-stat success">
              <span class="result-icon">✅</span>
              <span class="result-label">成功：</span>
              <span class="result-value">{{ batchResult.successCount }} 項</span>
            </div>
            <div class="result-stat failed" v-if="batchResult.failedCount > 0">
              <span class="result-icon">❌</span>
              <span class="result-label">失敗：</span>
              <span class="result-value">{{ batchResult.failedCount }} 項</span>
            </div>
          </div>
          <div class="failed-items-section" v-if="batchResult.failedItems.length > 0">
            <h4>失敗項目清單：</h4>
            <ul class="failed-items-list">
              <li v-for="item in batchResult.failedItems" :key="item.id">
                #{{ item.id }} - {{ item.question }}
                <span class="error-message">（{{ item.error }}）</span>
              </li>
            </ul>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="closeResultDialog" class="btn-primary">確定</button>
          <button v-if="batchResult.failedCount > 0" @click="retryFailedItems" class="btn-retry">
            🔄 重試失敗項目
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { API_ENDPOINTS } from '../../config/api';

export default {
  name: 'LoopKnowledgeReviewTab',
  data() {
    return {
      stats: null,
      items: [],
      loading: true,
      filterType: '', // '', 'sop', 'general'
      vendors: [], // 業者列表
      categories: {}, // 業者的類別列表（按業者 ID 分組）
      groups: {}, // 類別的群組列表（按 vendor_id-category_id 分組）
      selectedVendors: {}, // 為每個項目記錄選擇的業者 ID
      selectedCategories: {}, // 為每個項目記錄選擇的類別 ID
      selectedGroups: {}, // 為每個項目記錄選擇的群組 ID
      selectedIds: [], // 批量操作選取的項目 ID
      // 批量審核對話框狀態
      showConfirmDialog: false,
      batchAction: '', // 'approve' or 'reject'
      batchReviewNotes: '',
      // 批量審核進度狀態
      showProgressDialog: false,
      batchProgress: {
        current: 0,
        total: 0,
        currentItem: null,
        successCount: 0,
        failedCount: 0,
        failedItems: []
      },
      // 批量審核結果狀態
      showResultDialog: false,
      batchResult: {
        successCount: 0,
        failedCount: 0,
        failedItems: []
      }
    };
  },
  mounted() {
    this.loadStats();
    this.loadItems();
    this.loadVendors();
  },
  computed: {
    // 是否全選
    allSelected() {
      return this.items.length > 0 && this.selectedIds.length === this.items.length;
    },
    // 是否部分選取
    someSelected() {
      return this.selectedIds.length > 0 && this.selectedIds.length < this.items.length;
    },
    // 選取項目中的 SOP 數量
    selectedItemsSopCount() {
      return this.items.filter(item =>
        this.selectedIds.includes(item.id) && item.knowledge_type === 'sop'
      ).length;
    },
    // 選取項目中的一般知識數量
    selectedItemsGeneralCount() {
      return this.items.filter(item =>
        this.selectedIds.includes(item.id) && item.knowledge_type !== 'sop'
      ).length;
    },
    // 批量審核進度百分比
    progressPercentage() {
      if (this.batchProgress.total === 0) return 0;
      return Math.round((this.batchProgress.current / this.batchProgress.total) * 100);
    },
  },
  methods: {
    // 全選/取消全選
    toggleSelectAll() {
      if (this.allSelected) {
        this.selectedIds = [];
      } else {
        this.selectedIds = this.items.map(item => item.id);
      }
    },
    // 切換單個項目的選取狀態
    toggleSelectItem(itemId) {
      const index = this.selectedIds.indexOf(itemId);
      if (index > -1) {
        this.selectedIds.splice(index, 1);
      } else {
        this.selectedIds.push(itemId);
      }
    },

    // 顯示批量批准確認對話框
    showBatchApproveDialog() {
      if (this.selectedIds.length === 0) {
        alert('請先選取要批准的項目');
        return;
      }
      this.batchAction = 'approve';
      this.batchReviewNotes = '';
      this.showConfirmDialog = true;
    },

    // 顯示批量拒絕確認對話框
    showBatchRejectDialog() {
      if (this.selectedIds.length === 0) {
        alert('請先選取要拒絕的項目');
        return;
      }
      this.batchAction = 'reject';
      this.batchReviewNotes = '';
      this.showConfirmDialog = true;
    },

    // 關閉確認對話框
    closeConfirmDialog() {
      this.showConfirmDialog = false;
      this.batchAction = '';
      this.batchReviewNotes = '';
    },

    // 執行批量審核
    async executeBatchReview() {
      this.showConfirmDialog = false;

      // 初始化進度狀態
      this.batchProgress = {
        current: 0,
        total: this.selectedIds.length,
        currentItem: null,
        successCount: 0,
        failedCount: 0,
        failedItems: []
      };
      this.showProgressDialog = true;

      // 逐一審核每個項目
      const selectedItems = this.items.filter(item => this.selectedIds.includes(item.id));

      for (const item of selectedItems) {
        this.batchProgress.currentItem = item;
        this.batchProgress.current++;

        try {
          const payload = {
            action: this.batchAction,
            review_notes: this.batchReviewNotes || null,
            reviewed_by: 'admin' // TODO: 從登入狀態取得
          };

          // 如果是 SOP，加上 vendor_id, category_id, group_id
          if (item.knowledge_type === 'sop') {
            payload.vendor_id = this.selectedVendors[item.id];
            payload.category_id = this.selectedCategories[item.id];
            payload.group_id = this.selectedGroups[item.id] || null;

            // 檢查必填欄位
            if (this.batchAction === 'approve' && (!payload.vendor_id || !payload.category_id)) {
              throw new Error('SOP 項目缺少必填的業者或類別');
            }
          }

          await axios.post(
            API_ENDPOINTS.loopKnowledgeReview(item.id),
            payload
          );

          this.batchProgress.successCount++;
        } catch (error) {
          console.error(`審核項目 #${item.id} 失敗:`, error);
          this.batchProgress.failedCount++;
          this.batchProgress.failedItems.push({
            id: item.id,
            question: item.question,
            error: error.response?.data?.detail || error.message
          });
        }

        // 小延遲避免請求過快
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      // 關閉進度對話框
      this.showProgressDialog = false;

      // 顯示結果對話框
      this.batchResult = {
        successCount: this.batchProgress.successCount,
        failedCount: this.batchProgress.failedCount,
        failedItems: this.batchProgress.failedItems
      };
      this.showResultDialog = true;

      // 更新列表和統計
      await this.loadItems();
      await this.loadStats();
    },

    // 關閉結果對話框
    closeResultDialog() {
      this.showResultDialog = false;
      this.batchResult = {
        successCount: 0,
        failedCount: 0,
        failedItems: []
      };
    },

    // 重試失敗項目
    retryFailedItems() {
      // 只選取失敗的項目 ID
      this.selectedIds = this.batchResult.failedItems.map(item => item.id);
      this.closeResultDialog();
      // 重新顯示確認對話框
      if (this.batchAction === 'approve') {
        this.showBatchApproveDialog();
      } else {
        this.showBatchRejectDialog();
      }
    },

    async loadVendors() {
      try {
        const response = await axios.get(API_ENDPOINTS.ragVendors);
        // API 直接返回陣列，不是 { vendors: [...] } 格式
        this.vendors = Array.isArray(response.data) ? response.data : (response.data.vendors || []);
      } catch (error) {
        console.error('載入業者列表失敗:', error);
      }
    },

    async loadCategories(vendorId) {
      try {
        const response = await axios.get(API_ENDPOINTS.sopCategories, {
          params: { vendor_id: vendorId }
        });
        this.categories[vendorId] = response.data.categories || [];
      } catch (error) {
        console.error('載入類別失敗:', error);
      }
    },

    async loadGroups(vendorId, categoryId) {
      try {
        const response = await axios.get(API_ENDPOINTS.sopGroups, {
          params: { vendor_id: vendorId, category_id: categoryId }
        });
        const key = `${vendorId}-${categoryId}`;
        this.groups[key] = response.data.groups || [];
      } catch (error) {
        console.error('載入群組失敗:', error);
      }
    },

    async onVendorChange(itemId) {
      const vendorId = this.selectedVendors[itemId];
      if (vendorId) {
        // 清空類別和群組選擇
        delete this.selectedCategories[itemId];
        delete this.selectedGroups[itemId];

        // 載入該業者的類別
        await this.loadCategories(vendorId);
      }
    },

    async onCategoryChange(itemId) {
      const vendorId = this.selectedVendors[itemId];
      const categoryId = this.selectedCategories[itemId];
      if (vendorId && categoryId) {
        // 清空群組選擇
        delete this.selectedGroups[itemId];

        // 載入該類別的群組
        await this.loadGroups(vendorId, categoryId);
      }
    },

    async loadStats() {
      try {
        const response = await axios.get(API_ENDPOINTS.loopKnowledgeStats);
        this.stats = response.data;
      } catch (error) {
        console.error('載入統計失敗:', error);
      }
    },

    async loadItems() {
      this.loading = true;
      this.selectedIds = []; // 重新載入時清空選取
      try {
        const params = { limit: 50 };
        if (this.filterType) {
          params.knowledge_type = this.filterType;
        }

        const response = await axios.get(API_ENDPOINTS.loopKnowledgePending, { params });
        this.items = response.data.items.map(item => ({
          ...item,
          reviewNotes: ''
        }));

        // 為 SOP 項目預填 vendor_id, category_id, group_id
        for (const item of this.items) {
          if (item.knowledge_type === 'sop' && item.sop_config) {
            const config = typeof item.sop_config === 'string'
              ? JSON.parse(item.sop_config)
              : item.sop_config;

            // 預填 vendor_id
            if (config.vendor_id) {
              this.selectedVendors[item.id] = config.vendor_id;
              // 載入該業者的類別
              await this.loadCategories(config.vendor_id);
            }

            // 預填 category_id
            if (config.category_id) {
              this.selectedCategories[item.id] = config.category_id;
              // 載入該類別的群組
              if (config.vendor_id) {
                await this.loadGroups(config.vendor_id, config.category_id);
              }
            }

            // 預填 group_id
            if (config.group_id) {
              this.selectedGroups[item.id] = config.group_id;
            }
          }
        }
      } catch (error) {
        console.error('載入列表失敗:', error);
        alert('載入失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },

    async reviewItem(item, action) {
      const actionText = action === 'approve' ? '通過' : '拒絕';

      // 如果是 SOP 且要通過，檢查是否選擇必填欄位
      if (item.knowledge_type === 'sop' && action === 'approve') {
        if (!this.selectedVendors[item.id]) {
          alert('請選擇業者');
          return;
        }
        if (!this.selectedCategories[item.id]) {
          alert('請選擇 SOP 類別');
          return;
        }
      }

      if (!confirm(`確定要${actionText}這個${item.knowledge_type === 'sop' ? 'SOP' : '知識'}嗎？`)) {
        return;
      }

      try {
        const payload = {
          action: action,
          review_notes: item.reviewNotes || null,
          reviewed_by: 'admin' // TODO: 從登入狀態取得
        };

        // 如果是 SOP，加上 vendor_id, category_id, group_id
        if (item.knowledge_type === 'sop') {
          payload.vendor_id = this.selectedVendors[item.id];
          payload.category_id = this.selectedCategories[item.id];
          payload.group_id = this.selectedGroups[item.id] || null;
        }

        const response = await axios.post(
          API_ENDPOINTS.loopKnowledgeReview(item.id),
          payload
        );

        alert(response.data.message);

        // 從列表中移除
        this.items = this.items.filter(i => i.id !== item.id);

        // 更新統計
        this.loadStats();

      } catch (error) {
        console.error('審核失敗:', error);
        alert('審核失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    formatDate(dateString) {
      if (!dateString) return '';
      const date = new Date(dateString);
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
.loop-knowledge-review-tab {
  padding: 20px;
}

/* 統計區域 */
.stats-section {
  display: flex;
  gap: 15px;
  margin-bottom: 25px;
}

.stat-card {
  flex: 1;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 15px;
  text-align: center;
}

.stat-card.sop {
  border-left: 4px solid #9c27b0;
}

.stat-card.approved {
  border-left: 4px solid #4caf50;
}

.stat-card.rejected {
  border-left: 4px solid #f44336;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-top: 5px;
}

/* 篩選器 */
.filter-section {
  display: flex;
  gap: 15px;
  align-items: center;
  margin-bottom: 20px;
  padding: 15px;
  background: #f5f5f5;
  border-radius: 8px;
}

/* 全選區域 */
.select-all-section {
  padding: 12px 15px;
  background: #e3f2fd;
  border-radius: 8px;
  margin-bottom: 15px;
  border-left: 4px solid #2196f3;
}

.select-all-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-weight: 500;
  color: #1565c0;
  user-select: none;
}

.select-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

/* 批量操作工具列 */
.batch-action-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: #fff3e0;
  border: 2px solid #ff9800;
  border-radius: 8px;
  margin-bottom: 20px;
}

.toolbar-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.selected-count {
  font-weight: 600;
  color: #e65100;
  font-size: 15px;
}

.btn-clear-selection {
  padding: 6px 12px;
  background: white;
  border: 1px solid #ff9800;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  color: #e65100;
}

.btn-clear-selection:hover {
  background: #ffe0b2;
}

.toolbar-actions {
  display: flex;
  gap: 10px;
}

.btn-batch-approve,
.btn-batch-reject {
  padding: 10px 24px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  font-size: 14px;
}

.btn-batch-approve {
  background: #4caf50;
  color: white;
}

.btn-batch-approve:hover {
  background: #45a049;
}

.btn-batch-reject {
  background: #f44336;
  color: white;
}

.btn-batch-reject:hover {
  background: #da190b;
}

.filter-section label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-section select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.refresh-btn {
  padding: 8px 16px;
  background: #2196f3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.refresh-btn:hover {
  background: #1976d2;
}

/* 項目列表 */
.knowledge-item {
  display: flex;
  gap: 15px;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 15px;
}

.item-checkbox-wrapper {
  display: flex;
  align-items: flex-start;
  padding-top: 5px;
}

.item-checkbox {
  width: 20px;
  height: 20px;
  cursor: pointer;
  margin: 0;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f0f0f0;
}

.item-id {
  font-weight: bold;
  color: #666;
}

.badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
}

.sop-badge {
  background: #e1bee7;
  color: #6a1b9a;
}

.knowledge-badge {
  background: #bbdefb;
  color: #1565c0;
}

.loop-info {
  color: #999;
  font-size: 13px;
}

.item-date {
  margin-left: auto;
  color: #999;
  font-size: 13px;
}

/* 內容區域 */
.item-body {
  margin-bottom: 20px;
}

.question-section,
.answer-section {
  margin-bottom: 15px;
}

.answer-text {
  white-space: pre-wrap;
  line-height: 1.6;
  background: #f9f9f9;
  padding: 12px;
  border-radius: 4px;
  margin-top: 8px;
}

/* SOP 配置 */
.sop-config-section {
  background: #f3e5f5;
  padding: 12px;
  border-radius: 4px;
  margin-top: 15px;
}

.config-row {
  display: flex;
  gap: 10px;
  margin-bottom: 8px;
}

.config-row:last-child {
  margin-bottom: 0;
}

/* 關鍵詞 */
.keywords-section {
  margin-top: 10px;
}

.keyword-tag {
  display: inline-block;
  background: #e3f2fd;
  color: #1976d2;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  margin-right: 6px;
  margin-top: 4px;
}

/* SOP 選擇器區域 */
.sop-selector-section {
  margin-top: 15px;
  padding: 15px;
  background: #fff3cd;
  border-left: 4px solid #ffc107;
  border-radius: 4px;
}

.selector-header {
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ffc107;
}

.selector-header strong {
  color: #856404;
  font-size: 15px;
}

.selector-header .hint {
  margin-left: 8px;
  color: #856404;
  font-size: 13px;
  font-weight: normal;
}

.selector-row {
  margin-bottom: 12px;
}

.selector-row:last-child {
  margin-bottom: 0;
}

.selector-row label {
  display: flex;
  align-items: center;
  gap: 10px;
}

.select-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  background: white;
  cursor: pointer;
}

.select-input:required:invalid {
  border-color: #f44336;
}

.select-input:focus {
  outline: none;
  border-color: #ffc107;
  box-shadow: 0 0 0 2px rgba(255, 193, 7, 0.2);
}

/* 動作按鈕 */
.item-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 15px;
}

.review-notes-input {
  flex: 1;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.btn-approve,
.btn-reject {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  font-size: 14px;
}

.btn-approve {
  background: #4caf50;
  color: white;
}

.btn-approve:hover {
  background: #45a049;
}

.btn-reject {
  background: #f44336;
  color: white;
}

.btn-reject:hover {
  background: #da190b;
}

/* 狀態 */
.empty-state,
.loading-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
  font-size: 16px;
}

/* 對話框共用樣式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-dialog {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e0e0e0;
  background: #f5f5f5;
}

.modal-header h3 {
  margin: 0;
  font-size: 20px;
  color: #333;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.btn-close:hover {
  background: #e0e0e0;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid #e0e0e0;
  background: #f5f5f5;
}

/* 確認對話框 */
.confirm-stats {
  background: #f9f9f9;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 15px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.stat-row:last-child {
  margin-bottom: 0;
}

.stat-label {
  color: #666;
}

.stat-value {
  font-weight: bold;
  color: #333;
}

.warning-section {
  background: #fff3e0;
  border-left: 4px solid #ff9800;
  padding: 12px;
  margin-bottom: 15px;
  border-radius: 4px;
}

.warning-section p {
  margin: 0;
  color: #e65100;
  font-weight: 500;
}

.notes-section {
  margin-bottom: 15px;
}

.notes-section label {
  display: block;
}

.batch-notes-textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  margin-top: 8px;
  font-family: inherit;
  resize: vertical;
}

.btn-cancel {
  padding: 10px 24px;
  background: #757575;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
}

.btn-cancel:hover {
  background: #616161;
}

.btn-confirm-approve {
  padding: 10px 24px;
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.btn-confirm-approve:hover {
  background: #45a049;
}

.btn-confirm-reject {
  padding: 10px 24px;
  background: #f44336;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.btn-confirm-reject:hover {
  background: #da190b;
}

/* 進度對話框 */
.progress-dialog {
  max-width: 500px;
}

.progress-stats {
  background: #f9f9f9;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.progress-stats p {
  margin: 8px 0;
  font-size: 15px;
}

.progress-bar-wrapper {
  width: 100%;
  height: 30px;
  background: #e0e0e0;
  border-radius: 15px;
  overflow: hidden;
  margin-bottom: 20px;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #4caf50, #66bb6a);
  transition: width 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
}

.current-item {
  background: #e3f2fd;
  padding: 12px;
  border-radius: 8px;
  border-left: 4px solid #2196f3;
}

.current-item p {
  margin: 0;
  font-size: 14px;
  color: #1565c0;
}

/* 結果對話框 */
.result-summary {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
}

.result-stat {
  flex: 1;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
}

.result-stat.success {
  background: #e8f5e9;
  border: 2px solid #4caf50;
}

.result-stat.failed {
  background: #ffebee;
  border: 2px solid #f44336;
}

.result-icon {
  font-size: 32px;
  display: block;
  margin-bottom: 10px;
}

.result-label {
  display: block;
  color: #666;
  font-size: 14px;
  margin-bottom: 5px;
}

.result-value {
  display: block;
  font-size: 24px;
  font-weight: bold;
  color: #333;
}

.failed-items-section {
  background: #fff3e0;
  padding: 15px;
  border-radius: 8px;
  border-left: 4px solid #ff9800;
}

.failed-items-section h4 {
  margin: 0 0 15px 0;
  color: #e65100;
  font-size: 16px;
}

.failed-items-list {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 200px;
  overflow-y: auto;
}

.failed-items-list li {
  background: white;
  padding: 10px;
  margin-bottom: 8px;
  border-radius: 4px;
  border: 1px solid #ffe0b2;
}

.error-message {
  color: #d32f2f;
  font-size: 13px;
  display: block;
  margin-top: 4px;
}

.btn-primary {
  padding: 10px 24px;
  background: #2196f3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.btn-primary:hover {
  background: #1976d2;
}

.btn-retry {
  padding: 10px 24px;
  background: #ff9800;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.btn-retry:hover {
  background: #f57c00;
}
</style>
