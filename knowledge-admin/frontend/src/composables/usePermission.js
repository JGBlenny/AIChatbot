/**
 * usePermission Composable
 * 提供權限檢查的便捷函數
 *
 * 用法：
 * import { usePermission } from '@/composables/usePermission'
 *
 * const { can, canAny, canAll, hasRole, isAdmin } = usePermission()
 *
 * <button v-if="can('knowledge:create')">新增知識</button>
 * <button v-if="canAny(['knowledge:edit', 'knowledge:delete'])">編輯或刪除</button>
 * <button v-if="isAdmin">管理員功能</button>
 */
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function usePermission() {
  const authStore = useAuthStore()

  /**
   * 檢查是否擁有特定權限
   * @param {string} permission - 權限名稱，如 'knowledge:view'
   * @returns {boolean}
   */
  const can = (permission) => {
    return authStore.hasPermission(permission)
  }

  /**
   * 檢查是否擁有任一權限（OR 邏輯）
   * @param {string[]} permissions - 權限列表
   * @returns {boolean}
   */
  const canAny = (permissions) => {
    return authStore.hasAnyPermission(permissions)
  }

  /**
   * 檢查是否擁有所有權限（AND 邏輯）
   * @param {string[]} permissions - 權限列表
   * @returns {boolean}
   */
  const canAll = (permissions) => {
    return authStore.hasAllPermissions(permissions)
  }

  /**
   * 檢查是否擁有特定角色
   * @param {string} role - 角色名稱，如 'super_admin'
   * @returns {boolean}
   */
  const hasRole = (role) => {
    return authStore.hasRole(role)
  }

  /**
   * 檢查是否為超級管理員
   * @returns {boolean}
   */
  const isAdmin = computed(() => authStore.isSuperAdmin)

  /**
   * 獲取當前用戶的所有權限
   * @returns {Ref<string[]>}
   */
  const permissions = computed(() => authStore.permissions)

  /**
   * 獲取當前用戶的所有角色
   * @returns {Ref<Array<{name: string, display_name: string}>>}
   */
  const roles = computed(() => authStore.roles)

  return {
    can,
    canAny,
    canAll,
    hasRole,
    isAdmin,
    permissions,
    roles
  }
}
