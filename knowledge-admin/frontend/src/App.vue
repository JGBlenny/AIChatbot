<template>
  <div id="app">
    <header class="app-header">
      <h1>📚 AI 知識庫管理系統</h1>
      <nav class="main-nav">
        <router-link to="/" class="nav-item">知識庫</router-link>
        <router-link to="/intents" class="nav-item">意圖管理</router-link>
        <router-link to="/suggested-intents" class="nav-item">建議審核</router-link>
        <router-link to="/business-scope" class="nav-item">業務範圍</router-link>
        <router-link to="/knowledge-reclassify" class="nav-item">知識分類</router-link>
        <router-link to="/knowledge-import" class="nav-item">知識匯入</router-link>
        <router-link to="/vendors" class="nav-item">業者管理</router-link>
        <router-link to="/chat-test" class="nav-item">Chat 測試</router-link>
        <router-link to="/backtest" class="nav-item">回測結果</router-link>
      </nav>
    </header>

    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script>
export default {
  name: 'App'
};
</script>

<style>
/* 重置和全局樣式保留原有的 */
</style>

<style scoped>
.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px 40px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.app-header h1 {
  margin: 0 0 15px 0;
  font-size: 28px;
}

.main-nav {
  display: flex;
  gap: 10px;
}

.nav-item {
  padding: 8px 16px;
  background: rgba(255,255,255,0.2);
  border-radius: 20px;
  text-decoration: none;
  color: white;
  transition: all 0.3s;
  font-size: 14px;
}

.nav-item:hover {
  background: rgba(255,255,255,0.3);
  transform: translateY(-2px);
}

.nav-item.router-link-active {
  background: white;
  color: #667eea;
  font-weight: bold;
}

.app-main {
  padding: 30px 40px;
  max-width: 1400px;
  margin: 0 auto;
}
</style>
