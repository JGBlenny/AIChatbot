<template>
  <div>
    <h2>🏢 業態類型配置</h2>

    <!-- 說明區塊 -->
    <InfoPanel :config="helpTexts.businessTypes" />

    <!-- 業態類型列表 - 兩層結構 -->
    <div class="business-categories">
      <div
        v-for="(category, categoryCode) in BUSINESS_CATEGORIES"
        :key="categoryCode"
        class="category-section"
      >
        <!-- 類別標題 -->
        <div class="category-header" :class="'category-' + category.color">
          <div class="category-info">
            <span class="category-icon">{{ category.icon }}</span>
            <h3>{{ category.name }}</h3>
          </div>
          <p class="category-description">{{ category.description }}</p>
        </div>

        <!-- 業態列表 -->
        <div class="business-types-grid">
          <div
            v-for="type in category.types"
            :key="type.type_value"
            class="type-card"
            :class="'type-' + type.color"
          >
            <div class="type-header">
              <span class="type-icon">{{ type.icon }}</span>
              <h4>{{ type.display_name }}</h4>
              <span class="type-code">{{ type.type_value }}</span>
            </div>

            <p class="type-description">{{ type.description }}</p>

            <div class="type-features">
              <div class="features-title">主要特點：</div>
              <ul>
                <li v-for="(feature, idx) in type.features" :key="idx">
                  {{ feature }}
                </li>
              </ul>
            </div>

            <div class="type-actions">
              <button @click="viewDetails(type, category)" class="btn-view btn-sm">
                查看詳情
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 詳情 Modal -->
    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop style="max-width: 800px;">
        <h2>
          <span>{{ selectedType?.icon }}</span>
          {{ selectedType?.display_name }}
          <span class="type-badge" :class="'badge-' + selectedType?.color">
            {{ selectedCategory?.code }}
          </span>
        </h2>

        <div class="detail-section">
          <h3>基本資訊</h3>
          <table class="detail-table">
            <tr>
              <th>類型代碼</th>
              <td><code>{{ selectedType?.type_value }}</code></td>
            </tr>
            <tr>
              <th>顯示名稱</th>
              <td>{{ selectedType?.display_name }}</td>
            </tr>
            <tr>
              <th>業務類別</th>
              <td>
                <span class="badge" :class="'badge-' + selectedCategory?.color">
                  {{ selectedCategory?.icon }} {{ selectedCategory?.name }}
                </span>
              </td>
            </tr>
            <tr>
              <th>說明</th>
              <td>{{ selectedType?.description }}</td>
            </tr>
          </table>
        </div>

        <div class="detail-section">
          <h3>主要特點</h3>
          <ul class="features-list">
            <li v-for="(feature, idx) in selectedType?.features" :key="idx">
              <span class="feature-bullet">✓</span>
              {{ feature }}
            </li>
          </ul>
        </div>

        <div class="detail-section">
          <h3>語氣 Prompt</h3>
          <div class="tone-prompt">
            <pre>{{ selectedType?.tone_prompt }}</pre>
          </div>
          <small class="prompt-note">
            💡 此 Prompt 用於 LLM 回答優化，根據不同業態調整回覆語氣和風格
          </small>
        </div>

        <div class="form-actions">
          <button type="button" @click="closeModal" class="btn-primary btn-sm">關閉</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import InfoPanel from '@/components/InfoPanel.vue';
import helpTexts from '@/config/help-texts.js';
import { BUSINESS_CATEGORIES } from '@/config/business-types.js';

export default {
  name: 'BusinessTypesConfigView',
  components: {
    InfoPanel
  },
  data() {
    return {
      helpTexts,
      BUSINESS_CATEGORIES,
      showModal: false,
      selectedType: null,
      selectedCategory: null
    };
  },
  methods: {
    viewDetails(type, category) {
      this.selectedType = type;
      this.selectedCategory = category;
      this.showModal = true;
    },

    closeModal() {
      this.showModal = false;
      this.selectedType = null;
      this.selectedCategory = null;
    }
  }
};
</script>

<style scoped>
/* ==================== 類別區塊 ==================== */
.business-categories {
  display: flex;
  flex-direction: column;
  gap: 48px;
}

.category-section {
  background: transparent;
}

.category-header {
  padding: 0 0 24px 0;
  border: none;
  background: transparent;
  margin-bottom: 20px;
}

.category-info {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 10px;
}

.category-icon {
  font-size: 36px;
}

.category-header h3 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.3px;
  color: #1f2937;
}

.category-description {
  margin: 0;
  color: #9ca3af;
  font-size: 14px;
  font-weight: 400;
  margin-left: 52px;
}

/* ==================== 業態卡片網格 ==================== */
.business-types-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
  padding: 0;
}

.type-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 24px;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  border: 2px solid;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.type-card.type-blue {
  border-color: #3b82f6;
}

.type-card.type-green {
  border-color: #10b981;
}

.type-card.type-purple {
  border-color: #8b5cf6;
}

.type-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.type-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f3f4f6;
}

.type-icon {
  font-size: 32px;
}

.type-header h4 {
  flex: 1;
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}

.type-code {
  font-size: 11px;
  font-family: 'Monaco', 'Courier New', monospace;
  padding: 6px 12px;
  border-radius: 6px;
  font-weight: 600;
  color: #ffffff;
}

.type-card.type-blue .type-code {
  background: #3b82f6;
}

.type-card.type-green .type-code {
  background: #10b981;
}

.type-card.type-purple .type-code {
  background: #8b5cf6;
}

.type-description {
  color: #4b5563;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 20px;
}

.type-features {
  flex: 1;
  margin-bottom: 20px;
}

.features-title {
  font-size: 11px;
  font-weight: 700;
  color: #6b7280;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.type-features ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

.type-features li {
  margin-bottom: 8px;
  line-height: 1.6;
  padding-left: 20px;
  position: relative;
  color: #374151;
  font-size: 14px;
}

.type-features li::before {
  content: '✓';
  position: absolute;
  left: 0;
  font-weight: 700;
  font-size: 14px;
}

.type-card.type-blue .type-features li::before {
  color: #3b82f6;
}

.type-card.type-green .type-features li::before {
  color: #10b981;
}

.type-card.type-purple .type-features li::before {
  color: #8b5cf6;
}

.type-actions {
  display: flex;
  gap: 8px;
}

.btn-view {
  flex: 1;
  background: #f9fafb;
  color: #374151;
  border: 1px solid #e5e7eb;
  padding: 10px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
  transition: all 0.2s;
}

.type-card.type-blue .btn-view:hover {
  background: #3b82f6;
  color: #ffffff;
  border-color: #3b82f6;
}

.type-card.type-green .btn-view:hover {
  background: #10b981;
  color: #ffffff;
  border-color: #10b981;
}

.type-card.type-purple .btn-view:hover {
  background: #8b5cf6;
  color: #ffffff;
  border-color: #8b5cf6;
}

/* ==================== 詳情 Modal ==================== */
.type-badge {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 4px;
  font-weight: 600;
  margin-left: 10px;
  background: #ffffff;
  border: 1.5px solid;
}

.type-badge.badge-blue {
  color: #2563eb;
  border-color: #3b82f6;
}

/* .type-badge.badge-purple {
  color: #7c3aed;
  border-color: #8b5cf6;
} */

.detail-section {
  margin-bottom: 32px;
}

.detail-section h3 {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e7eb;
  text-transform: uppercase;
  letter-spacing: 0.8px;
}

.detail-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

.detail-table th {
  text-align: left;
  padding: 12px 14px;
  background: #f9fafb;
  font-weight: 500;
  color: #6b7280;
  width: 140px;
  border: 1px solid #e5e7eb;
  border-right: none;
  font-size: 12px;
}

.detail-table td {
  padding: 12px 14px;
  border: 1px solid #e5e7eb;
  border-left: none;
  color: #374151;
  font-size: 14px;
}

.detail-table code {
  background: #f3f4f6;
  padding: 3px 8px;
  border-radius: 4px;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  color: #4b5563;
  font-weight: 500;
}

.features-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}

.features-list li {
  padding: 10px 12px;
  background: #f9fafb;
  border-left: 2px solid #e5e7eb;
  border-radius: 4px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: #4b5563;
}

.feature-bullet {
  color: #9ca3af;
  font-weight: 600;
  font-size: 14px;
  line-height: 1;
}

.tone-prompt {
  background: #f9fafb;
  border-radius: 6px;
  padding: 14px;
  overflow-x: auto;
  border: 1px solid #e5e7eb;
}

.tone-prompt pre {
  margin: 0;
  color: #6b7280;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.prompt-note {
  display: block;
  margin-top: 8px;
  color: #6b7280;
  font-size: 12px;
}

/* ==================== 通用樣式 ==================== */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  background: #ffffff;
  border: 1.5px solid;
}

.badge.badge-blue {
  color: #2563eb;
  border-color: #3b82f6;
}

/* .badge.badge-purple {
  color: #7c3aed;
  border-color: #8b5cf6;
} */
</style>
