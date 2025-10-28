<template>
  <div class="review-center">
    <div class="page-header">
      <h2>🔍 審核中心</h2>
      <button @click="refreshAll" class="btn-secondary">
        🔄 重新整理全部
      </button>
    </div>

    <!-- Tab 導航 -->
    <div class="tabs-nav">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab-button', { active: currentTab === tab.key }]"
        @click="switchTab(tab.key)"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        <span class="tab-label">{{ tab.label }}</span>
        <span v-if="tab.count > 0" class="tab-badge">{{ tab.count }}</span>
      </button>
    </div>

    <!-- Tab 內容區域 -->
    <div class="tab-content">
      <keep-alive>
        <component
          :is="currentTabComponent"
          @update-count="updateTabCount"
          :candidate-id="candidateId"
        />
      </keep-alive>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import IntentReviewTab from '../components/review/IntentReviewTab.vue';
import ScenarioReviewTab from '../components/review/ScenarioReviewTab.vue';
import KnowledgeReviewTab from '../components/review/KnowledgeReviewTab.vue';
import UnclearQuestionReviewTab from '../components/review/UnclearQuestionReviewTab.vue';

export default {
  name: 'ReviewCenterView',

  components: {
    IntentReviewTab,
    ScenarioReviewTab,
    KnowledgeReviewTab,
    UnclearQuestionReviewTab
  },

  setup() {
    const route = useRoute();
    const currentTab = ref('intents');
    const candidateId = ref(null);

    // 檢查 URL 參數
    onMounted(() => {
      // 如果有 candidate_id 參數，自動切換到知識庫審核 tab
      if (route.query.candidate_id) {
        candidateId.value = parseInt(route.query.candidate_id);
        currentTab.value = 'knowledge';
      }
    });

    const tabs = ref([
      {
        key: 'intents',
        label: '意圖審核',
        icon: '💡',
        count: 0,
        component: 'IntentReviewTab'
      },
      {
        key: 'scenarios',
        label: '測試情境審核',
        icon: '🧪',
        count: 0,
        component: 'ScenarioReviewTab'
      },
      {
        key: 'unclear-questions',
        label: '用戶問題',
        icon: '❓',
        count: 0,
        component: 'UnclearQuestionReviewTab'
      },
      {
        key: 'knowledge',
        label: '知識庫審核',
        icon: '📚',
        count: 0,
        component: 'KnowledgeReviewTab'
      }
    ]);

    const currentTabComponent = computed(() => {
      const tab = tabs.value.find(t => t.key === currentTab.value);
      return tab ? tab.component : 'IntentReviewTab';
    });

    const switchTab = (tabKey) => {
      currentTab.value = tabKey;
    };

    const updateTabCount = (data) => {
      const tab = tabs.value.find(t => t.key === data.tab);
      if (tab) {
        tab.count = data.count;
      }
    };

    const refreshAll = () => {
      // 觸發所有 Tab 的刷新
      window.location.reload();
    };

    return {
      currentTab,
      tabs,
      currentTabComponent,
      switchTab,
      updateTabCount,
      refreshAll,
      candidateId
    };
  }
};
</script>

<style scoped>
.review-center {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e9ecef;
}

.page-header h2 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: #2c3e50;
  display: flex;
  align-items: center;
  gap: 10px;
}

/* Tab 導航樣式 */
.tabs-nav {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  background: white;
  padding: 8px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.tab-button {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 24px;
  border: none;
  background: transparent;
  color: #666;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  border-radius: 8px;
  position: relative;
  flex: 1;
  justify-content: center;
}

.tab-button:hover {
  color: #667eea;
  background: #f8f9fa;
  transform: translateY(-2px);
}

.tab-button.active {
  color: white;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.tab-icon {
  font-size: 20px;
}

.tab-label {
  font-weight: 600;
}

.tab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 7px;
  background: rgba(255, 255, 255, 0.3);
  color: white;
  border-radius: 11px;
  font-size: 12px;
  font-weight: bold;
}

.tab-button:not(.active) .tab-badge {
  background: #e6a23c;
  color: white;
}

/* Tab 內容區域 */
.tab-content {
  flex: 1;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  padding: 30px;
  overflow-y: auto;
}

/* 響應式設計 */
@media (max-width: 768px) {
  .tabs-nav {
    flex-direction: column;
    gap: 8px;
  }

  .tab-button {
    justify-content: flex-start;
  }

  .tab-content {
    padding: 20px;
  }
}
</style>
