import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from './stores/auth';
import KnowledgeView from './views/KnowledgeView.vue';
import LoginView from './views/LoginView.vue';
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
// Knowledge Export to Excel
import KnowledgeExportView from './views/KnowledgeExportView.vue';
// Document Converter (Word/PDF to Q&A)
import DocumentConverterView from './views/DocumentConverterView.vue';
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
// Admin Management
import AdminManagementView from './views/AdminManagementView.vue';
// Role Management
import RoleManagementView from './views/RoleManagementView.vue';

const routes = [
  {
    path: '/',
    name: 'Home',
    redirect: '/knowledge/universal',
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: { requiresAuth: false }
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: KnowledgeView,
    meta: {
      requiresAuth: true,
      permissions: ['knowledge:view']
    }
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
  {
    path: '/knowledge-export',
    name: 'KnowledgeExport',
    component: KnowledgeExportView
  },
  {
    path: '/document-converter',
    name: 'DocumentConverter',
    component: DocumentConverterView
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
  // Audience Config - Redirect to Target Users (舊功能已遷移)
  {
    path: '/audience-config',
    redirect: '/target-users-config'
  },
  // Admin Management
  {
    path: '/admin-management',
    name: 'AdminManagement',
    component: AdminManagementView,
    meta: {
      requiresAuth: true,
      permissions: ['admin:view']
    }
  },
  // Role Management
  {
    path: '/role-management',
    name: 'RoleManagement',
    component: RoleManagementView,
    meta: {
      requiresAuth: true,
      permissions: ['role:view']
    }
  },
  // Vendor Chat Demo - 業者測試頁面（放在最後以避免路由衝突）
  {
    path: '/:vendorCode/chat',
    name: 'VendorChatDemo',
    component: VendorChatDemo,
    meta: { requiresAuth: false }  // 展示頁不需要登入
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// 路由守衛 - 保護需要認證的路由並檢查權限
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // 檢查路由是否需要認證（預設為 true）
  const requiresAuth = to.meta.requiresAuth !== false

  // 1. 檢查登入狀態
  if (requiresAuth && !authStore.isAuthenticated) {
    // 需要登入但未登入，重定向到登入頁
    return next({
      name: 'Login',
      query: { redirect: to.fullPath }  // 記錄原本要去的頁面
    })
  }

  // 2. 已登入用戶訪問登入頁，重定向到首頁
  if (to.name === 'Login' && authStore.isAuthenticated) {
    return next({ name: 'Home' })
  }

  // 3. 確保已載入權限（頁面刷新時需要）
  if (authStore.isAuthenticated && authStore.permissions.length === 0) {
    try {
      await authStore.fetchUserPermissions()
    } catch (err) {
      console.error('載入權限失敗:', err)
      // 如果載入權限失敗，可能是 token 過期，登出並重定向到登入頁
      authStore.logout()
      return next({ name: 'Login', query: { redirect: to.fullPath } })
    }
  }

  // 4. 檢查權限（如果路由有設定權限要求）
  if (to.meta.permissions && to.meta.permissions.length > 0) {
    const hasPermission = authStore.hasAnyPermission(to.meta.permissions)

    if (!hasPermission) {
      // 無權限，顯示警告並停留在當前頁面
      console.warn(`缺少權限: ${to.meta.permissions.join(', ')}`)
      alert('您沒有權限訪問此頁面')
      return next(false)  // 取消導航
    }
  }

  // 5. 檢查角色（如果路由有設定角色要求）
  if (to.meta.roles && to.meta.roles.length > 0) {
    const hasRole = to.meta.roles.some(role => authStore.hasRole(role))

    if (!hasRole) {
      console.warn(`缺少角色: ${to.meta.roles.join(', ')}`)
      alert('您沒有權限訪問此頁面')
      return next(false)
    }
  }

  // 6. 其他情況正常通過
  next()
})

export default router;
