/**
 * v-permission 指令
 * 根據用戶權限控制元素的顯示/隱藏
 *
 * 用法：
 * v-permission="'knowledge:create'"                              // 單一權限
 * v-permission="['knowledge:create', 'knowledge:edit']"          // 多個權限（OR）
 * v-permission.all="['knowledge:create', 'knowledge:edit']"      // 多個權限（AND）
 *
 * 範例：
 * <button v-permission="'knowledge:create'">新增知識</button>
 * <button v-permission="['knowledge:edit', 'knowledge:delete']">編輯或刪除</button>
 * <button v-permission.all="['knowledge:edit', 'knowledge:delete']">完整操作</button>
 */
import { useAuthStore } from '@/stores/auth'

export default {
  mounted(el, binding) {
    const authStore = useAuthStore()
    const { value, modifiers } = binding

    let hasPermission = false

    if (Array.isArray(value)) {
      // 多個權限
      if (modifiers.all) {
        // AND 邏輯 - 需要擁有所有權限
        hasPermission = authStore.hasAllPermissions(value)
      } else {
        // OR 邏輯 - 擁有任一權限即可（預設）
        hasPermission = authStore.hasAnyPermission(value)
      }
    } else if (typeof value === 'string') {
      // 單一權限
      hasPermission = authStore.hasPermission(value)
    } else {
      console.warn('v-permission: 無效的權限值', value)
    }

    if (!hasPermission) {
      // 移除元素（不顯示）
      el.parentNode?.removeChild(el)
    }
  },

  // 當綁定值更新時也檢查（用於動態權限）
  updated(el, binding) {
    // 由於元素已經被移除，updated 不會被調用
    // 如果需要動態更新，考慮使用 v-if="can(...)" 而不是指令
  }
}
