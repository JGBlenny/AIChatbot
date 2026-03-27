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

    <!-- 列表區域 -->
    <div class="items-section" v-if="!loading">
      <div v-if="items.length === 0" class="empty-state">
        <p>✅ 沒有待審核的項目</p>
      </div>

      <div v-for="item in items" :key="item.id" class="knowledge-item">
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

    <div v-if="loading" class="loading-state">
      <p>載入中...</p>
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
    };
  },
  mounted() {
    this.loadStats();
    this.loadItems();
    this.loadVendors();
  },
  methods: {
    async loadVendors() {
      try {
        const response = await axios.get(API_ENDPOINTS.vendors);
        this.vendors = response.data.vendors || [];
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
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 15px;
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
</style>
