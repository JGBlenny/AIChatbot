<template>
  <div class="info-section">
    <div class="info-header" @click="toggleInfo">
      <span class="info-icon">{{ isOpen ? '▼' : '▶' }}</span>
      <strong>{{ config.title }}</strong>
      <span class="toggle-hint">(點擊展開/收合)</span>
      <span v-if="config.lastUpdated" class="last-updated">最後更新: {{ config.lastUpdated }}</span>
    </div>

    <transition name="slide">
      <div v-if="isOpen" class="info-content">
        <div class="info-grid">
          <!-- 動態渲染各個區塊 -->
          <div
            v-for="(section, index) in config.sections"
            :key="index"
            class="info-card"
            :class="{
              'highlight': section.important,
              'warning': section.type === 'warning'
            }"
          >
            <h3>
              <span v-if="section.icon">{{ section.icon }} </span>
              {{ section.title }}
            </h3>

            <!-- 內容段落 -->
            <p v-if="section.content" v-html="section.content"></p>

            <!-- 列表項目 -->
            <ul v-if="section.items && section.items.length">
              <li v-for="(item, idx) in section.items" :key="idx" v-html="item"></li>
            </ul>

            <!-- 範例區塊 -->
            <div v-if="section.example" class="example-box" v-html="section.example"></div>

            <!-- 表格 -->
            <table v-if="section.table" class="info-table">
              <thead v-if="section.table.headers">
                <tr>
                  <th v-for="(header, idx) in section.table.headers" :key="idx">{{ header }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in section.table.rows" :key="idx">
                  <td v-for="(cell, cellIdx) in row" :key="cellIdx">
                    <span v-if="cell.badge" class="badge" :class="cell.badgeClass">{{ cell.text }}</span>
                    <span v-else v-html="cell"></span>
                  </td>
                </tr>
              </tbody>
            </table>

            <!-- 提示框 -->
            <div v-if="section.note" class="note-box" v-html="section.note"></div>
          </div>
        </div>

        <!-- 快速提示 -->
        <div v-if="config.tips" class="quick-tips">
          <h3>💡 {{ config.tips.title || '使用建議' }}</h3>
          <ul>
            <li v-for="(tip, idx) in config.tips.items" :key="idx" v-html="tip"></li>
          </ul>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
export default {
  name: 'InfoPanel',
  props: {
    config: {
      type: Object,
      required: true
    },
    defaultOpen: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      isOpen: this.defaultOpen
    };
  },
  methods: {
    toggleInfo() {
      this.isOpen = !this.isOpen;
    }
  }
};
</script>

<style scoped>
/* 說明區塊樣式 */
.info-section {
  background: white;
  border: 2px solid #e1e8f0;
  border-radius: 16px;
  margin-bottom: 28px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.08);
  transition: all 0.3s ease;
}

.info-section:hover {
  box-shadow: 0 6px 30px rgba(102, 126, 234, 0.12);
  border-color: #667eea;
}

.info-header {
  padding: 18px 24px;
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  gap: 12px;
  background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%);
  border-bottom: 1px solid #e8eef5;
  transition: all 0.3s ease;
}

.info-header:hover {
  background: linear-gradient(135deg, #eef2ff 0%, #e6ecff 100%);
}

.info-icon {
  color: #667eea;
  font-size: 16px;
  font-weight: bold;
  transition: transform 0.3s ease;
}

.info-header strong {
  color: #4a5568;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.2px;
}

.toggle-hint {
  color: #a0aec0;
  font-size: 12px;
  margin-left: auto;
  font-weight: 500;
  transition: color 0.3s;
}

.info-header:hover .toggle-hint {
  color: #667eea;
}

.last-updated {
  color: #a0aec0;
  font-size: 11px;
  font-style: italic;
  background: rgba(102, 126, 234, 0.08);
  padding: 4px 10px;
  border-radius: 12px;
}

.info-content {
  padding: 28px;
  background: #fafbfd;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 24px;
  margin-bottom: 24px;
}

.info-card {
  background: white;
  border: 1px solid #e8eef5;
  border-radius: 12px;
  padding: 24px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.info-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.15);
  border-color: #c7d2fe;
}

.info-card h3 {
  margin: 0 0 16px 0;
  font-size: 17px;
  font-weight: 700;
  color: #2d3748;
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-card p {
  margin: 0 0 10px 0;
  font-size: 14px;
  line-height: 1.6;
  color: #606266;
}

.info-card ul {
  margin: 10px 0;
  padding-left: 20px;
}

.info-card li {
  margin: 8px 0;
  font-size: 14px;
  line-height: 1.6;
  color: #606266;
}

.info-card.highlight {
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 20%, #fffef9 100%);
  border: 2px solid #fbbf24;
  border-left: 5px solid #f59e0b;
  box-shadow: 0 4px 16px rgba(251, 191, 36, 0.15);
}

.info-card.highlight:hover {
  box-shadow: 0 8px 28px rgba(251, 191, 36, 0.25);
  border-color: #f59e0b;
}

.info-card.warning {
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 20%, #fffef9 100%);
  border: 2px solid #f87171;
  border-left: 5px solid #ef4444;
  box-shadow: 0 4px 16px rgba(248, 113, 113, 0.15);
}

.info-card.warning:hover {
  box-shadow: 0 8px 28px rgba(248, 113, 113, 0.25);
  border-color: #ef4444;
}

.example-box {
  background: linear-gradient(135deg, #fef3c7 0%, #fefce8 100%);
  border-left: 4px solid #f59e0b;
  padding: 16px;
  margin-top: 16px;
  font-size: 13px;
  line-height: 1.8;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.1);
}

.info-table {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0;
  font-size: 13px;
}

.info-table thead {
  background: #f5f7fa;
}

.info-table th {
  padding: 10px;
  text-align: left;
  font-weight: 600;
  color: #303133;
  border-bottom: 2px solid #DCDFE6;
}

.info-table tr {
  border-bottom: 1px solid #e1e8ed;
}

.info-table td {
  padding: 10px 8px;
  vertical-align: top;
  color: #606266;
}

.badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  color: white;
}

.badge.type-knowledge { background: #409EFF; }
.badge.type-data_query { background: #E6A23C; }
.badge.type-action { background: #F56C6C; }
.badge.type-hybrid { background: #67C23A; }
.badge.boost-primary { background: #67C23A; }
.badge.boost-secondary { background: #409EFF; }
.badge.boost-normal { background: #909399; }

.note-box {
  background: linear-gradient(135deg, #dbeafe 0%, #eff6ff 100%);
  border-left: 4px solid #3b82f6;
  padding: 16px;
  margin-top: 16px;
  font-size: 13px;
  line-height: 1.8;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
}

.quick-tips {
  background: linear-gradient(135deg, #fef3c7 0%, #fefce8 100%);
  border: 2px solid #fbbf24;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 4px 16px rgba(251, 191, 36, 0.1);
}

.quick-tips h3 {
  margin: 0 0 16px 0;
  font-size: 17px;
  font-weight: 700;
  color: #92400e;
  display: flex;
  align-items: center;
  gap: 8px;
}

.quick-tips ul {
  margin: 0;
  padding-left: 24px;
}

.quick-tips li {
  margin: 10px 0;
  font-size: 14px;
  line-height: 1.8;
  color: #78350f;
}

/* 滑動動畫 */
.slide-enter-active, .slide-leave-active {
  transition: all 0.3s ease;
  max-height: 3000px;
}

.slide-enter-from, .slide-leave-to {
  max-height: 0;
  opacity: 0;
  padding-top: 0;
  padding-bottom: 0;
}
</style>
