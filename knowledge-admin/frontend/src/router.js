import { createRouter, createWebHistory } from 'vue-router';
import KnowledgeView from './views/KnowledgeView.vue';
import IntentsView from './views/IntentsView.vue';
import SuggestedIntentsView from './views/SuggestedIntentsView.vue';
import BusinessScopeView from './views/BusinessScopeView.vue';
import KnowledgeReclassifyView from './views/KnowledgeReclassifyView.vue';
// Phase 1: Multi-Vendor Support
import VendorManagementView from './views/VendorManagementView.vue';
import VendorConfigView from './views/VendorConfigView.vue';
import ChatTestView from './views/ChatTestView.vue';
// Knowledge Import from LINE chats
import KnowledgeImportView from './views/KnowledgeImportView.vue';
// Backtest Results
import BacktestView from './views/BacktestView.vue';

const routes = [
  {
    path: '/',
    name: 'Knowledge',
    component: KnowledgeView
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
    path: '/business-scope',
    name: 'BusinessScope',
    component: BusinessScopeView
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
    path: '/chat-test',
    name: 'ChatTest',
    component: ChatTestView
  },
  {
    path: '/backtest',
    name: 'Backtest',
    component: BacktestView
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;
