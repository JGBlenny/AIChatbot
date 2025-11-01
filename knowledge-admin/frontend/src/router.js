import { createRouter, createWebHistory } from 'vue-router';
import KnowledgeView from './views/KnowledgeView.vue';
import IntentsView from './views/IntentsView.vue';
import SuggestedIntentsView from './views/SuggestedIntentsView.vue';
import KnowledgeReclassifyView from './views/KnowledgeReclassifyView.vue';
// Phase 1: Multi-Vendor Support
import VendorManagementView from './views/VendorManagementView.vue';
import VendorConfigView from './views/VendorConfigView.vue';
import ChatTestView from './views/ChatTestView.vue';
import VendorChatDemo from './views/VendorChatDemo.vue';
// Platform SOP Template Management
import PlatformSOPView from './views/PlatformSOPView.vue';
import PlatformSOPEditView from './views/PlatformSOPEditView.vue';
// Knowledge Import from LINE chats
import KnowledgeImportView from './views/KnowledgeImportView.vue';
// Backtest Results
import BacktestView from './views/BacktestView.vue';
// Test Scenarios Management
import TestScenariosView from './views/TestScenariosView.vue';
import PendingReviewView from './views/PendingReviewView.vue';
// Unified Review Center
import ReviewCenterView from './views/ReviewCenterView.vue';
// Cache Management
import CacheManagementView from './views/CacheManagementView.vue';
// Business Types Config Management
import BusinessTypesConfigView from './views/BusinessTypesConfigView.vue';
// Target User Config Management
import TargetUserConfigView from './views/TargetUserConfigView.vue';
// Category Config Management
import CategoryConfigView from './views/CategoryConfigView.vue';

const routes = [
  {
    path: '/',
    name: 'Home',
    redirect: '/knowledge/universal'
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: KnowledgeView
  },
  // 知識庫分類路由（重定向到主頁面但帶過濾參數）
  {
    path: '/knowledge/industry',
    name: 'IndustryKnowledge',
    redirect: to => ({ path: '/knowledge', query: { filter: 'b2c' }})
  },
  {
    path: '/knowledge/jgb',
    name: 'JGBKnowledge',
    redirect: to => ({ path: '/knowledge', query: { filter: 'b2b' }})
  },
  {
    path: '/knowledge/universal',
    name: 'UniversalKnowledge',
    redirect: to => ({ path: '/knowledge', query: { filter: 'universal' }})
  },
  {
    path: '/intents',
    name: 'Intents',
    component: IntentsView
  },
  {
    path: '/suggested-intents',
    name: 'SuggestedIntents',
    component: SuggestedIntentsView
  },
  {
    path: '/knowledge-reclassify',
    name: 'KnowledgeReclassify',
    component: KnowledgeReclassifyView
  },
  {
    path: '/knowledge-import',
    name: 'KnowledgeImport',
    component: KnowledgeImportView
  },
  // Phase 1: Multi-Vendor Routes
  {
    path: '/vendors',
    name: 'Vendors',
    component: VendorManagementView
  },
  {
    path: '/vendors/:id/configs',
    name: 'VendorConfig',
    component: VendorConfigView
  },
  {
    path: '/platform-sop',
    name: 'PlatformSOP',
    component: PlatformSOPView
  },
  {
    path: '/platform-sop/:businessType/edit',
    name: 'PlatformSOPEdit',
    component: PlatformSOPEditView
  },
  {
    path: '/chat-test',
    name: 'ChatTest',
    component: ChatTestView
  },
  {
    path: '/backtest',
    name: 'Backtest',
    component: BacktestView
  },
  {
    path: '/test-scenarios',
    name: 'TestScenarios',
    component: TestScenariosView
  },
  {
    path: '/test-scenarios/pending',
    name: 'PendingReview',
    component: PendingReviewView
  },
  // Unified Review Center (NEW)
  {
    path: '/review-center',
    name: 'ReviewCenter',
    component: ReviewCenterView
  },
  // AI Knowledge Review - redirect to Review Center (功能已合併)
  {
    path: '/ai-knowledge-review',
    redirect: '/review-center'
  },
  // Cache Management
  {
    path: '/cache-management',
    name: 'CacheManagement',
    component: CacheManagementView
  },
  // Business Types Config Management
  {
    path: '/business-types-config',
    name: 'BusinessTypesConfig',
    component: BusinessTypesConfigView
  },
  // Target User Config Management
  {
    path: '/target-users-config',
    name: 'TargetUsersConfig',
    component: TargetUserConfigView
  },
  // Category Config Management
  {
    path: '/category-config',
    name: 'CategoryConfig',
    component: CategoryConfigView
  },
  // Audience Config - Redirect to Target Users (舊功能已遷移)
  {
    path: '/audience-config',
    redirect: '/target-users-config'
  },
  // Vendor Chat Demo - 業者測試頁面（放在最後以避免路由衝突）
  {
    path: '/:vendorCode/chat',
    name: 'VendorChatDemo',
    component: VendorChatDemo
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;
