/**
 * 認證 Store
 * 管理用戶登入狀態、token 和用戶資料
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// 使用空字符串讓所有請求走相對路徑，通過 Vite 代理轉發到後端
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export const useAuthStore = defineStore('auth', () => {
  // State
  const token = ref(localStorage.getItem('auth_token') || null)
  const user = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // 權限相關 state
  const permissions = ref([])
  const roles = ref([])

  // Getters
  const isAuthenticated = computed(() => !!token.value)

  // 權限檢查 getters
  const hasPermission = computed(() => (permission) => {
    // 超級管理員擁有所有權限
    if (permissions.value.includes('*:*')) return true

    // 檢查具體權限
    if (permissions.value.includes(permission)) return true

    // 檢查通配符權限（如 knowledge:*）
    if (permission.includes(':')) {
      const [resource, action] = permission.split(':', 2)
      if (permissions.value.includes(`${resource}:*`)) return true
    }

    return false
  })

  const hasRole = computed(() => (role) => {
    return roles.value.some(r => r.name === role)
  })

  const hasAnyPermission = computed(() => (permissionList) => {
    return permissionList.some(p => hasPermission.value(p))
  })

  const hasAllPermissions = computed(() => (permissionList) => {
    return permissionList.every(p => hasPermission.value(p))
  })

  const isSuperAdmin = computed(() => hasRole.value('super_admin'))

  // Actions
  async function login(username, password) {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || '登入失敗')
      }

      const data = await response.json()

      // 儲存 token 和用戶資料
      token.value = data.access_token
      user.value = data.user
      localStorage.setItem('auth_token', data.access_token)

      // 獲取權限
      await fetchUserPermissions()

      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  function logout() {
    // 清除本地狀態
    token.value = null
    user.value = null
    permissions.value = []
    roles.value = []
    error.value = null
    localStorage.removeItem('auth_token')
  }

  async function fetchUserPermissions() {
    if (!token.value) {
      return
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/permissions`, {
        headers: {
          'Authorization': `Bearer ${token.value}`
        }
      })

      if (!response.ok) {
        throw new Error('獲取權限失敗')
      }

      const data = await response.json()
      permissions.value = data.permissions || []
      roles.value = data.roles || []

      return data
    } catch (err) {
      console.error('獲取權限失敗:', err)
      // 不拋出錯誤，避免影響登入流程
    }
  }

  async function fetchCurrentUser() {
    if (!token.value) {
      return
    }

    loading.value = true
    error.value = null

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token.value}`
        }
      })

      if (!response.ok) {
        // Token 無效，清除登入狀態
        logout()
        throw new Error('認證失敗')
      }

      const data = await response.json()
      user.value = data

      return data
    } catch (err) {
      error.value = err.message
      logout()
      throw err
    } finally {
      loading.value = false
    }
  }

  // 初始化時檢查 token 有效性
  async function initialize() {
    if (token.value) {
      try {
        await fetchCurrentUser()
        await fetchUserPermissions()
      } catch (err) {
        console.error('Token 驗證失敗:', err)
      }
    }
  }

  return {
    // State
    token,
    user,
    loading,
    error,
    permissions,
    roles,
    // Getters
    isAuthenticated,
    hasPermission,
    hasRole,
    hasAnyPermission,
    hasAllPermissions,
    isSuperAdmin,
    // Actions
    login,
    logout,
    fetchCurrentUser,
    fetchUserPermissions,
    initialize
  }
})
