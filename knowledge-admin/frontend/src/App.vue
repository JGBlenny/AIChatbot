<template>
  <div id="app">
    <!-- 左側導航欄 -->
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <div class="logo">
          <span class="logo-icon">📚</span>
          <span class="logo-text" v-if="!sidebarCollapsed">AI 知識庫</span>
        </div>
        <button class="collapse-btn" @click="toggleSidebar" :title="sidebarCollapsed ? '展開' : '收起'">
          {{ sidebarCollapsed ? '☰' : '✕' }}
        </button>
      </div>

      <nav class="sidebar-nav">
        <!-- 核心功能 -->
        <div class="nav-group">
          <div class="nav-group-title" v-if="!sidebarCollapsed">核心功能</div>
          <router-link to="/" class="nav-item" :title="sidebarCollapsed ? '知識庫' : ''">
            <span class="nav-icon">📖</span>
            <span class="nav-text" v-if="!sidebarCollapsed">知識庫</span>
          </router-link>
          <router-link to="/intents" class="nav-item" :title="sidebarCollapsed ? '意圖管理' : ''">
            <span class="nav-icon">🎯</span>
            <span class="nav-text" v-if="!sidebarCollapsed">意圖管理</span>
          </router-link>
          <router-link to="/business-scope" class="nav-item" :title="sidebarCollapsed ? '業務範圍' : ''">
            <span class="nav-icon">🏢</span>
            <span class="nav-text" v-if="!sidebarCollapsed">業務範圍</span>
          </router-link>
          <router-link to="/vendors" class="nav-item" :title="sidebarCollapsed ? '業者管理' : ''">
            <span class="nav-icon">👥</span>
            <span class="nav-text" v-if="!sidebarCollapsed">業者管理</span>
          </router-link>
          <router-link to="/platform-sop" class="nav-item" :title="sidebarCollapsed ? 'SOP 範本' : ''">
            <span class="nav-icon">📋</span>
            <span class="nav-text" v-if="!sidebarCollapsed">SOP 範本</span>
          </router-link>
        </div>

        <!-- AI 功能 -->
        <div class="nav-group">
          <div class="nav-group-title" v-if="!sidebarCollapsed">AI 功能</div>
          <router-link to="/review-center" class="nav-item nav-item-highlight" :title="sidebarCollapsed ? '審核中心' : ''">
            <span class="nav-icon">🔍</span>
            <span class="nav-text" v-if="!sidebarCollapsed">審核中心</span>
          </router-link>
          <router-link to="/knowledge-reclassify" class="nav-item" :title="sidebarCollapsed ? '重新分類' : ''">
            <span class="nav-icon">🔄</span>
            <span class="nav-text" v-if="!sidebarCollapsed">重新分類</span>
          </router-link>
        </div>

        <!-- 數據管理 -->
        <div class="nav-group">
          <div class="nav-group-title" v-if="!sidebarCollapsed">數據管理</div>
          <router-link to="/knowledge-import" class="nav-item" :title="sidebarCollapsed ? '知識匯入' : ''">
            <span class="nav-icon">📥</span>
            <span class="nav-text" v-if="!sidebarCollapsed">知識匯入</span>
          </router-link>
        </div>

        <!-- 測試與監控 -->
        <div class="nav-group">
          <div class="nav-group-title" v-if="!sidebarCollapsed">測試與監控</div>
          <router-link to="/chat-test" class="nav-item" :title="sidebarCollapsed ? 'Chat 測試' : ''">
            <span class="nav-icon">💬</span>
            <span class="nav-text" v-if="!sidebarCollapsed">Chat 測試</span>
          </router-link>
          <router-link to="/test-scenarios" class="nav-item" :title="sidebarCollapsed ? '測試題庫' : ''">
            <span class="nav-icon">🧪</span>
            <span class="nav-text" v-if="!sidebarCollapsed">測試題庫</span>
          </router-link>
          <router-link to="/backtest" class="nav-item" :title="sidebarCollapsed ? '回測結果' : ''">
            <span class="nav-icon">📊</span>
            <span class="nav-text" v-if="!sidebarCollapsed">回測結果</span>
          </router-link>
        </div>
      </nav>

      <div class="sidebar-footer" v-if="!sidebarCollapsed">
        <div class="footer-info">
          <div class="footer-version">v1.0.0</div>
          <div class="footer-copyright">© 2025 AI Chatbot</div>
        </div>
      </div>
    </aside>

    <!-- 主內容區 -->
    <div class="main-container" :class="{ expanded: sidebarCollapsed }">
      <header class="app-header">
        <h1 class="page-title">{{ currentPageTitle }}</h1>
        <div class="header-actions">
          <button class="header-btn" title="通知">
            🔔
            <span class="notification-badge">3</span>
          </button>
          <button class="header-btn" title="設定">⚙️</button>
          <button class="header-btn" title="使用者">👤</button>
        </div>
      </header>

      <main class="app-main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script>
export default {
  name: 'App',

  data() {
    return {
      sidebarCollapsed: false,
      pageTitles: {
        '/': '知識庫管理',
        '/intents': '意圖管理',
        '/review-center': '審核中心',
        '/business-scope': '業務範圍管理',
        '/knowledge-reclassify': '知識重新分類',
        '/knowledge-import': '知識匯入',
        '/vendors': '業者管理',
        '/platform-sop': 'SOP 範本管理',
        '/chat-test': 'Chat 測試',
        '/test-scenarios': '測試題庫',
        '/backtest': '回測結果'
      }
    };
  },

  computed: {
    currentPageTitle() {
      return this.pageTitles[this.$route.path] || 'AI 知識庫管理系統';
    }
  },

  methods: {
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed;
      localStorage.setItem('sidebarCollapsed', this.sidebarCollapsed);
    }
  },

  mounted() {
    // 恢復側邊欄狀態
    const collapsed = localStorage.getItem('sidebarCollapsed');
    if (collapsed !== null) {
      this.sidebarCollapsed = collapsed === 'true';
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
  background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%);
  color: white;
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 2px 0 12px rgba(0, 0, 0, 0.15);
  position: relative;
  z-index: 1000;
}

.sidebar.collapsed {
  width: 70px;
}

/* 側邊欄頭部 */
.sidebar-header {
  padding: 15px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  min-height: 60px;
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

.sidebar:not(.collapsed) .logo-icon:hover {
  transform: rotate(10deg) scale(1.1);
}

.logo-text {
  white-space: nowrap;
  overflow: hidden;
  animation: fadeIn 0.3s;
}

.collapse-btn {
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: white;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.collapse-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.1);
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

.nav-group {
  margin-bottom: 16px;
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
  gap: 10px;
  padding: 10px 15px;
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  transition: all 0.3s;
  position: relative;
  font-size: 14px;
  font-weight: 500;
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 10px 0;
}

.nav-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 0;
  background: white;
  border-radius: 0 3px 3px 0;
  transition: height 0.3s;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.nav-item:hover::before {
  height: 70%;
}

.nav-item.router-link-active {
  background: rgba(255, 255, 255, 0.15);
  color: white;
  font-weight: 600;
}

.nav-item.router-link-active::before {
  height: 100%;
  background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
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
  font-size: 20px;
  min-width: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-text {
  white-space: nowrap;
  overflow: hidden;
  flex: 1;
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
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: #f5f7fa;
}

.main-container.expanded {
  width: calc(100% - 70px);
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

.header-btn {
  position: relative;
  width: 40px;
  height: 40px;
  border: none;
  background: #f5f7fa;
  border-radius: 10px;
  cursor: pointer;
  font-size: 18px;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-btn:hover {
  background: #e8eaed;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
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
  padding: 20px;
  background: #f5f7fa;
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

  .sidebar.collapsed {
    left: -260px;
  }

  .main-container {
    width: 100%;
  }

  .app-header {
    padding: 10px 15px;
  }

  .app-main {
    padding: 15px;
  }
}
</style>
