/**
 * API 請求工具
 * 自動處理認證 token 和錯誤處理
 */
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

// 使用空字符串讓所有請求走相對路徑，通過 Vite 代理轉發到後端
// 這樣可以避免跨域問題，並且請求會自動攜帶 cookies/localStorage
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

/**
 * 統一的 API 請求函數
 * 自動附加 Authorization header
 * 自動處理 401 未授權錯誤
 *
 * @param {string} url - API 端點（相對路徑）
 * @param {object} options - fetch options
 * @returns {Promise<Response>}
 */
export async function apiRequest(url, options = {}) {
  const authStore = useAuthStore()

  // 構建完整 URL
  const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`

  // 準備 headers
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  }

  // 自動附加 Authorization header（如果已登入）
  if (authStore.token) {
    headers['Authorization'] = `Bearer ${authStore.token}`
  }

  // 發送請求
  try {
    const response = await fetch(fullUrl, {
      ...options,
      headers
    })

    // 處理 401 未授權錯誤
    if (response.status === 401) {
      // 清除登入狀態
      authStore.logout()

      // 重定向到登入頁（保留當前路徑用於登入後跳轉）
      router.push({
        name: 'Login',
        query: { redirect: router.currentRoute.value.fullPath }
      })

      throw new Error('未授權訪問，請重新登入')
    }

    return response
  } catch (error) {
    // 網路錯誤或其他錯誤
    console.error('API 請求失敗:', error)
    throw error
  }
}

/**
 * GET 請求
 */
export async function apiGet(url, options = {}) {
  const response = await apiRequest(url, {
    ...options,
    method: 'GET'
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'GET 請求失敗')
  }

  return response.json()
}

/**
 * POST 請求
 */
export async function apiPost(url, data = null, options = {}) {
  const response = await apiRequest(url, {
    ...options,
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'POST 請求失敗')
  }

  return response.json()
}

/**
 * PUT 請求
 */
export async function apiPut(url, data = null, options = {}) {
  const response = await apiRequest(url, {
    ...options,
    method: 'PUT',
    body: data ? JSON.stringify(data) : undefined
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'PUT 請求失敗')
  }

  return response.json()
}

/**
 * DELETE 請求
 */
export async function apiDelete(url, options = {}) {
  const response = await apiRequest(url, {
    ...options,
    method: 'DELETE'
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'DELETE 請求失敗')
  }

  return response.json()
}

/**
 * 使用範例：
 *
 * // 在 Vue 組件中
 * import { apiGet, apiPost, apiPut, apiDelete } from '@/utils/api'
 *
 * // GET 請求
 * const knowledge = await apiGet('/api/knowledge')
 *
 * // POST 請求
 * const newKnowledge = await apiPost('/api/knowledge', {
 *   question_summary: '測試問題',
 *   content: '測試答案'
 * })
 *
 * // PUT 請求
 * const updated = await apiPut('/api/knowledge/1', {
 *   question_summary: '更新的問題'
 * })
 *
 * // DELETE 請求
 * await apiDelete('/api/knowledge/1')
 */
