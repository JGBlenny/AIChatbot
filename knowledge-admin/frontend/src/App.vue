<template>
  <div id="app">
    <!-- 左側導航欄 (VendorChatDemo 頁面不顯示) -->
    <aside v-if="!isStandalonePage" class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <div class="logo">
          <span class="logo-icon">📚</span>
          <span class="logo-text">AI 知識庫</span>
        </div>
      </div>

      <nav class="sidebar-nav">
        <!-- 對話邏輯層 -->
        <div class="nav-layer">
          <div class="layer-title">對話邏輯層</div>

          <!-- 知識庫管理 -->
          <div class="nav-group">
            <div class="nav-group-header" @click="toggleGroup('knowledge')">
              <span class="group-icon">{{ expandedGroups.knowledge ? '▼' : '▶' }}</span>
              <span class="group-title">知識庫管理</span>
            </div>
            <div class="nav-group-items" v-if="expandedGroups.knowledge">
              <router-link to="/knowledge/universal" class="nav-item nav-item-sub">
                <span class="nav-icon">🌐</span>
                <span class="nav-text">通用知識庫</span>
              </router-link>
              <router-link to="/knowledge/industry" class="nav-item nav-item-sub">
                <span class="nav-icon">🏠</span>
                <span class="nav-text">產業知識庫</span>
              </router-link>
              <router-link to="/knowledge/jgb" class="nav-item nav-item-sub">
                <span class="nav-icon">💼</span>
                <span class="nav-text">JGB知識庫</span>
              </router-link>
              <router-link to="/intents" class="nav-item nav-item-sub">
                <span class="nav-icon">🎯</span>
                <span class="nav-text">意圖設定</span>
              </router-link>
              <router-link to="/target-users-config" class="nav-item nav-item-sub">
                <span class="nav-icon">👥</span>
                <span class="nav-text">目標設定</span>
              </router-link>
            </div>
          </div>

          <!-- 業者管理 -->
          <div class="nav-group">
            <div class="nav-group-header" @click="toggleGroup('vendor')">
              <span class="group-icon">{{ expandedGroups.vendor ? '▼' : '▶' }}</span>
              <span class="group-title">業者管理</span>
            </div>
            <div class="nav-group-items" v-if="expandedGroups.vendor">
              <router-link to="/vendors" class="nav-item nav-item-sub">
                <span class="nav-icon">👥</span>
                <span class="nav-text">業者列表</span>
              </router-link>
              <router-link to="/business-types-config" class="nav-item nav-item-sub">
                <span class="nav-icon">🏢</span>
                <span class="nav-text">業態設定</span>
              </router-link>
              <router-link to="/platform-sop" class="nav-item nav-item-sub">
                <span class="nav-icon">📋</span>
                <span class="nav-text">範本設定</span>
              </router-link>
            </div>
          </div>
        </div>

        <!-- 對話測試層 -->
        <div class="nav-layer">
          <div class="layer-title">對話測試層</div>
          <router-link to="/chat-test" class="nav-item">
            <span class="nav-icon">💬</span>
            <span class="nav-text">Chat測試</span>
          </router-link>
        </div>

        <!-- 資料工具層 -->
        <div class="nav-layer">
          <div class="layer-title">資料工具層</div>
          <router-link to="/knowledge-import" class="nav-item">
            <span class="nav-icon">📥</span>
            <span class="nav-text">知識庫匯入</span>
          </router-link>
          <router-link to="/knowledge-export" class="nav-item">
            <span class="nav-icon">📤</span>
            <span class="nav-text">知識庫匯出</span>
          </router-link>
          <router-link to="/document-converter" class="nav-item">
            <span class="nav-icon">🤖</span>
            <span class="nav-text">規格書轉換</span>
          </router-link>
        </div>

        <!-- 知識優化層 -->
        <div class="nav-layer">
          <div class="layer-title">知識優化層</div>
          <router-link to="/review-center" class="nav-item">
            <span class="nav-icon">🔍</span>
            <span class="nav-text">審核管理</span>
          </router-link>
          <router-link to="/knowledge-reclassify" class="nav-item">
            <span class="nav-icon">⚙️</span>
            <span class="nav-text">意圖分配</span>
          </router-link>
          <router-link to="/test-scenarios" class="nav-item">
            <span class="nav-icon">🧪</span>
            <span class="nav-text">測試管理</span>
          </router-link>
          <router-link to="/backtest" class="nav-item">
            <span class="nav-icon">📊</span>
            <span class="nav-text">回測管理</span>
          </router-link>
        </div>

        <!-- 系統設定層 -->
        <div class="nav-layer">
          <div class="layer-title">系統設定層</div>
          <router-link to="/cache-management" class="nav-item">
            <span class="nav-icon">⚡</span>
            <span class="nav-text">緩存管理</span>
          </router-link>
          <router-link to="/admin-management" class="nav-item">
            <span class="nav-icon">👥</span>
            <span class="nav-text">用戶管理</span>
          </router-link>
          <router-link to="/role-management" class="nav-item" v-permission="'role:view'">
            <span class="nav-icon">🔐</span>
            <span class="nav-text">角色管理</span>
          </router-link>
        </div>
      </nav>

      <div class="sidebar-footer">
        <div class="footer-info">
          <div class="footer-version">v1.0.0</div>
          <div class="footer-copyright">© 2025 AI Chatbot</div>
        </div>
      </div>
    </aside>

    <!-- 主內容區 (VendorChatDemo 使用獨立容器) -->
    <div v-if="!isStandalonePage" class="main-container">
      <header class="app-header">
        <h1 class="page-title">{{ currentPageTitle }}</h1>
        <div class="header-actions">
          <div class="user-info" v-if="currentUser">
            <span class="user-name">{{ currentUser.full_name || currentUser.username }}</span>
            <span class="user-role">管理員</span>
          </div>
          <button class="header-btn change-password-btn" @click="showChangePasswordModal = true" title="修改密碼">
            🔑 修改密碼
          </button>
          <button class="header-btn logout-btn" @click="handleLogout" title="登出">
            🚪 登出
          </button>
        </div>
      </header>

      <main class="app-main">
        <router-view />
      </main>
    </div>

    <!-- 獨立頁面容器 (VendorChatDemo) -->
    <div v-if="isStandalonePage" class="standalone-container">
      <router-view />
    </div>

    <!-- 修改密碼對話框 -->
    <ChangePasswordModal
      v-if="showChangePasswordModal"
      @close="showChangePasswordModal = false"
      @success="handleChangePasswordSuccess"
    />
  </div>
</template>

<script>
import { useAuthStore } from './stores/auth'
import ChangePasswordModal from './components/ChangePasswordModal.vue'

export default {
  name: 'App',

  components: {
    ChangePasswordModal
  },

  data() {
    return {
      expandedGroups: {
        knowledge: true,  // 預設展開知識庫管理
        vendor: true      // 預設展開業者管理
      },
      currentUser: null,
      showChangePasswordModal: false,
      pageTitles: {
        '/': '產業知識庫',
        '/knowledge': '知識庫管理',
        '/knowledge/industry': '產業知識庫 (B2C)',
        '/knowledge/jgb': 'JGB知識庫 (B2B)',
        '/knowledge/universal': '通用知識庫',
        '/intents': '意圖管理',
        '/review-center': '審核中心',
        '/business-scope': '業務範圍管理',
        '/knowledge-reclassify': '知識意圖分類',
        '/knowledge-import': '知識匯入',
        '/vendors': '業者管理',
        '/platform-sop': 'SOP 範本管理',
        '/chat-test': 'Chat 測試',
        '/test-scenarios': '測試題庫',
        '/backtest': '回測結果',
        '/cache-management': '緩存管理',
        '/target-users-config': '目標用戶配置',
        '/business-types-config': '業態類型配置',
        '/admin-management': '用戶管理',
        '/role-management': '角色管理'
      }
    };
  },

  computed: {
    currentPageTitle() {
      return this.pageTitles[this.$route.path] || 'AI 知識庫管理系統';
    },

    isStandalonePage() {
      // 檢查是否為獨立頁面（不需要側邊欄和 header）
      return this.$route.name === 'VendorChatDemo' || this.$route.name === 'Login';
    }
  },

  methods: {
    toggleGroup(groupName) {
      this.expandedGroups[groupName] = !this.expandedGroups[groupName];
      // 儲存展開狀態到 localStorage
      localStorage.setItem('expandedGroups', JSON.stringify(this.expandedGroups));
    },

    async handleLogout() {
      const authStore = useAuthStore()

      if (confirm('確定要登出嗎？')) {
        authStore.logout()
        this.$router.push('/login')
      }
    },

    handleChangePasswordSuccess() {
      const authStore = useAuthStore()

      this.showChangePasswordModal = false
      // 修改密碼成功後登出，要求用戶使用新密碼重新登入
      authStore.logout()
      this.$router.push('/login')
    },

    async loadCurrentUser() {
      const authStore = useAuthStore()

      if (authStore.isAuthenticated && authStore.user) {
        this.currentUser = authStore.user
      } else if (authStore.isAuthenticated) {
        try {
          await authStore.fetchCurrentUser()
          this.currentUser = authStore.user
        } catch (error) {
          console.error('載入用戶資料失敗:', error)
        }
      }
    }
  },

  async mounted() {
    // 恢復群組展開狀態
    const expandedGroups = localStorage.getItem('expandedGroups');
    if (expandedGroups !== null) {
      try {
        this.expandedGroups = JSON.parse(expandedGroups);
      } catch (e) {
        console.error('Failed to parse expandedGroups from localStorage:', e);
      }
    }

    // 初始化認證狀態（會載入用戶資料和權限）
    const authStore = useAuthStore()
    await authStore.initialize()

    // 載入當前用戶資料
    this.loadCurrentUser()
  },

  watch: {
    '$route'() {
      // 路由變化時更新用戶資料
      this.loadCurrentUser()
    }
  }
};
</script>

<style>
/* 全局樣式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background: #f5f7fa;
  color: #2c3e50;
}

#app {
  display: flex;
  height: 100vh;
  overflow: hidden;
}
</style>

<style scoped>
/* ==================== 側邊欄樣式 ==================== */
.sidebar {
  width: 260px;
  background: linear-gradient(180deg, #1e293b 0%, #334155 50%, #1e293b 100%);
  color: white;
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 20px rgba(0, 0, 0, 0.25);
  position: relative;
  z-index: 1000;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
}

.sidebar::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 30%, rgba(102, 126, 234, 0.1) 0%, transparent 50%),
    radial-gradient(circle at 80% 70%, rgba(118, 75, 162, 0.08) 0%, transparent 50%);
  pointer-events: none;
}

/* 側邊欄頭部 */
.sidebar-header {
  padding: 18px 15px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  min-height: 65px;
  background: rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(10px);
  position: relative;
  z-index: 1;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 700;
  font-size: 18px;
}

.logo-icon {
  font-size: 28px;
  transition: transform 0.3s;
}

.logo-icon:hover {
  transform: rotate(10deg) scale(1.1);
}

.logo-text {
  white-space: nowrap;
  overflow: hidden;
  animation: fadeIn 0.3s;
}

/* 側邊欄導航 */
.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 15px 0;
}

.sidebar-nav::-webkit-scrollbar {
  width: 6px;
}

.sidebar-nav::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
}

.sidebar-nav::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
}

/* 層級容器 */
.nav-layer {
  margin-bottom: 20px;
}

/* 層級標題 */
.layer-title {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: rgba(255, 255, 255, 0.5);
  padding: 10px 15px 10px 12px;
  font-weight: 700;
  border-left: 3px solid rgba(102, 126, 234, 0.8);
  margin: 12px 0 8px 0;
  background: linear-gradient(90deg, rgba(102, 126, 234, 0.15), transparent);
  animation: fadeIn 0.3s;
  position: relative;
}

.nav-group {
  margin-bottom: 8px;
}

/* 可展開的群組標題 */
.nav-group-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 15px;
  margin: 0 8px;
  color: rgba(255, 255, 255, 0.85);
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  font-size: 13px;
  font-weight: 600;
  user-select: none;
  border-radius: 8px;
  position: relative;
}

.nav-group-header::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
  border-radius: 0 2px 2px 0;
  opacity: 0;
  transition: opacity 0.25s;
}

.nav-group-header:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
  transform: translateX(2px);
}

.nav-group-header:hover::before {
  opacity: 1;
}

.group-icon {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.7);
  transition: transform 0.3s;
  font-weight: bold;
}

.group-title {
  flex: 1;
  letter-spacing: 0.3px;
}

/* 群組項目容器 */
.nav-group-items {
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.nav-group-title {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: rgba(255, 255, 255, 0.5);
  padding: 0 15px 6px;
  font-weight: 600;
  animation: fadeIn 0.3s;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 15px;
  margin: 2px 8px;
  color: rgba(255, 255, 255, 0.85);
  text-decoration: none;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  letter-spacing: 0.2px;
}

.nav-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
  border-radius: 0 2px 2px 0;
  opacity: 0;
  transition: opacity 0.25s;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.12);
  color: white;
  transform: translateX(2px);
}

.nav-item:hover::before {
  opacity: 0.6;
}

.nav-item.router-link-active {
  background: linear-gradient(90deg, rgba(102, 126, 234, 0.2), rgba(102, 126, 234, 0.05));
  color: white;
  font-weight: 600;
}

.nav-item.router-link-active::before {
  opacity: 1;
}

/* 子項目樣式（群組內的項目） */
.nav-item-sub {
  padding-left: 38px;
  font-size: 13px;
  background: rgba(0, 0, 0, 0.15);
  margin-left: 12px;
  margin-right: 12px;
}

.nav-item-sub .nav-icon {
  font-size: 15px;
  opacity: 0.9;
}

.nav-item-sub::before {
  left: 12px;
  width: 2px;
  background: rgba(102, 126, 234, 0.6);
}

.nav-item-sub:hover {
  background: rgba(255, 255, 255, 0.13);
}

.nav-item-sub.router-link-active {
  background: linear-gradient(90deg, rgba(102, 126, 234, 0.25), rgba(102, 126, 234, 0.08));
}

/* AI 功能特殊高亮 */
.nav-item-ai.router-link-active::before {
  background: linear-gradient(180deg, #ffd700 0%, #ffed4e 100%);
}

.nav-item-ai.router-link-active {
  background: rgba(255, 215, 0, 0.15);
}

/* 審核中心特殊高亮 */
.nav-item-highlight.router-link-active::before {
  background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
}

.nav-icon {
  font-size: 18px;
  min-width: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.3s, filter 0.3s;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
}

.nav-item:hover .nav-icon {
  transform: scale(1.15) rotate(-5deg);
}

.nav-item.router-link-active .nav-icon {
  filter: drop-shadow(0 2px 4px rgba(102, 126, 234, 0.5));
}

.nav-text {
  white-space: nowrap;
  overflow: hidden;
  flex: 1;
  animation: fadeIn 0.3s;
}

.nav-badge {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 10px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

/* 側邊欄底部 */
.sidebar-footer {
  padding: 15px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  animation: fadeIn 0.3s;
}

.footer-info {
  text-align: center;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  line-height: 1.6;
}

.footer-version {
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 4px;
}

/* ==================== 主內容區樣式 ==================== */
.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  width: calc(100% - 260px);
  background: #f5f7fa;
  margin-bottom: 80px;
}

.app-header {
  background: white;
  padding: 15px 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 60px;
  border-bottom: 1px solid #e8eaed;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #2c3e50;
  margin: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.user-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  padding: 10px 18px;
  background: white;
  border-radius: 12px;
  border: 2px solid #e8eaed;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}

.user-info:hover {
  border-color: #667eea;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
}

.user-name {
  font-size: 15px;
  font-weight: 700;
  color: #1a202c;
  line-height: 1.3;
  letter-spacing: -0.01em;
}

.user-role {
  font-size: 12px;
  color: #667eea;
  font-weight: 600;
  margin-top: 3px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.header-btn {
  position: relative;
  height: 42px;
  padding: 0 20px;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-weight: 600;
  letter-spacing: 0.01em;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
}

.header-btn:active {
  transform: translateY(-1px);
}

.change-password-btn {
  background: linear-gradient(135deg, #f59e0b 0%, #f97316 100%);
  color: white;
  border: 2px solid transparent;
}

.change-password-btn:hover {
  background: linear-gradient(135deg, #ea580c 0%, #dc2626 100%);
  box-shadow: 0 6px 24px rgba(249, 115, 22, 0.4);
}

.logout-btn {
  background: white;
  color: #667eea;
  border: 2px solid #667eea;
}

.logout-btn:hover {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
  box-shadow: 0 6px 24px rgba(102, 126, 234, 0.4);
}

.notification-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
  color: white;
  font-size: 10px;
  font-weight: 700;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid white;
}

.app-main {
  flex: 1;
  overflow-y: auto;
  padding: 0;
  background: #f5f7fa;
  display: flex;
  justify-content: center;
}

/* 統一內容寬度容器 */
.app-main > * {
  width: 100%;
  max-width: 1600px;
  padding: 30px 40px;
  margin: 0 auto;
}

.app-main::-webkit-scrollbar {
  width: 10px;
}

.app-main::-webkit-scrollbar-track {
  background: #f5f7fa;
}

.app-main::-webkit-scrollbar-thumb {
  background: #cbd5e0;
  border-radius: 5px;
}

.app-main::-webkit-scrollbar-thumb:hover {
  background: #a0aec0;
}

/* ==================== 獨立頁面容器 ==================== */
.standalone-container {
  width: 100%;
  height: 100vh;
  overflow: hidden;
}

/* ==================== 動畫 ==================== */
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* ==================== 響應式設計 ==================== */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    height: 100vh;
    z-index: 1000;
  }

  .main-container {
    width: 100%;
  }

  .app-header {
    padding: 10px 15px;
  }

  /* 移動設備上調整內邊距 */
  .app-main > * {
    padding: 20px 15px;
  }
}
</style>
