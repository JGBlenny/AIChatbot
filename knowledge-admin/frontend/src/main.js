import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'
import axios from 'axios'
import permissionDirective from './directives/permission'

// === 全局 Axios 攔截器 - 自動附加認證 Token ===
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// === 全局 Axios 響應攔截器 - 處理 401 錯誤 ===
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // 清除登入狀態
      localStorage.removeItem('auth_token')
      // 重定向到登入頁
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// === 全局 Fetch 攔截器 - 自動附加認證 Token ===
const originalFetch = window.fetch
window.fetch = function(url, options = {}) {
  // 只攔截 API 請求（不攔截外部資源）
  if (url.startsWith('/api') || url.startsWith('http://localhost:8000')) {
    const token = localStorage.getItem('auth_token')
    if (token) {
      // 確保 headers 物件存在
      options.headers = options.headers || {}
      // 添加 Authorization header
      options.headers['Authorization'] = `Bearer ${token}`
    }
  }
  return originalFetch(url, options)
}

const app = createApp(App)
const pinia = createPinia()

// 註冊權限指令
app.directive('permission', permissionDirective)

app.use(pinia)
app.use(router)
app.mount('#app')
