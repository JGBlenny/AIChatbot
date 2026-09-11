<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h3>{{ isEditMode ? '編輯用戶' : '新增用戶' }}</h3>
        <button @click="$emit('close')" class="btn-close">&times;</button>
      </div>

      <div class="modal-body">
        <form @submit.prevent="handleSubmit">
          <!-- 帳號 -->
          <div class="form-group">
            <label>
              帳號 <span class="required">*</span>
            </label>
            <input
              v-model="formData.username"
              type="text"
              :disabled="isEditMode"
              :class="['form-control', { 'is-invalid': errors.username }]"
              placeholder="3-50 字元，只能包含英數字和底線"
              @blur="validateUsername"
            />
            <div v-if="errors.username" class="error-message">{{ errors.username }}</div>
            <div v-if="isEditMode" class="form-hint">帳號創建後不可修改</div>
          </div>

          <!-- 密碼（僅新增模式） -->
          <div v-if="!isEditMode" class="form-group">
            <label>
              密碼 <span class="required">*</span>
            </label>
            <div class="password-input-wrapper">
              <input
                v-model="formData.password"
                :type="showPassword ? 'text' : 'password'"
                :class="['form-control', { 'is-invalid': errors.password }]"
                placeholder="請輸入密碼"
                @input="validatePassword"
              />
              <button type="button" @click="showPassword = !showPassword" class="btn-toggle-password">
                {{ showPassword ? '👁️' : '👁️‍🗨️' }}
              </button>
            </div>
            <div v-if="errors.password" class="error-message">{{ errors.password }}</div>

            <!-- 密碼強度指示器 -->
            <div v-if="formData.password" class="password-strength">
              <div class="strength-bar">
                <div :class="['strength-fill', `strength-${passwordStrength.level}`]" :style="{width: passwordStrength.percent + '%'}"></div>
              </div>
              <div :class="['strength-text', `strength-${passwordStrength.level}`]">
                {{ passwordStrength.text }} ({{ passwordStrength.percent }}%)
              </div>
            </div>
          </div>

          <!-- 姓名 -->
          <div class="form-group">
            <label>姓名</label>
            <input
              v-model="formData.full_name"
              type="text"
              class="form-control"
              placeholder="用戶姓名"
            />
          </div>

          <!-- Email -->
          <div class="form-group">
            <label>Email</label>
            <input
              v-model="formData.email"
              type="email"
              :class="['form-control', { 'is-invalid': errors.email }]"
              placeholder="example@domain.com"
              @blur="validateEmail"
            />
            <div v-if="errors.email" class="error-message">{{ errors.email }}</div>
          </div>

          <!-- 狀態（僅編輯模式） -->
          <div v-if="isEditMode" class="form-group">
            <label class="form-label">狀態</label>
            <div class="checkbox-wrapper">
              <div class="checkbox-item" @click="formData.is_active = !formData.is_active">
                <input
                  type="checkbox"
                  v-model="formData.is_active"
                  @click.stop
                  class="checkbox-input"
                />
                <div class="checkbox-content">
                  <div class="checkbox-text">啟用此帳號</div>
                </div>
              </div>
            </div>
            <div v-if="isSelfEdit" class="form-hint warning">
              ⚠️ 注意：你不能停用自己的帳號
            </div>
          </div>

          <!-- 重設密碼（僅編輯模式） -->
          <div v-if="isEditMode && !isSelfEdit" class="form-group">
            <label class="form-label">密碼設定</label>
            <div class="checkbox-wrapper">
              <div class="checkbox-item" @click="toggleResetPassword">
                <input
                  type="checkbox"
                  v-model="resetPassword"
                  @click.stop
                  @change="handleResetPasswordToggle"
                  class="checkbox-input"
                />
                <div class="checkbox-content">
                  <div class="checkbox-text">重設密碼</div>
                </div>
              </div>
            </div>

            <div v-if="resetPassword" class="reset-password-fields">
              <div class="warning-box">
                <span class="warning-icon">⚠️</span>
                <div>
                  <p>此操作將重設該用戶的密碼。請務必將新密碼告知該用戶。</p>
                </div>
              </div>

              <!-- 新密碼 -->
              <div class="form-group">
                <label>
                  新密碼 <span class="required">*</span>
                </label>
                <div class="password-input-wrapper">
                  <input
                    v-model="formData.new_password"
                    :type="showNewPassword ? 'text' : 'password'"
                    :class="['form-control', { 'is-invalid': errors.new_password }]"
                    placeholder="請輸入新密碼"
                    @input="validateNewPassword"
                  />
                  <button type="button" @click="showNewPassword = !showNewPassword" class="btn-toggle-password">
                    {{ showNewPassword ? '👁️' : '👁️‍🗨️' }}
                  </button>
                </div>
                <div v-if="errors.new_password" class="error-message">{{ errors.new_password }}</div>

                <!-- 密碼強度指示器 -->
                <div v-if="formData.new_password" class="password-strength">
                  <div class="strength-bar">
                    <div :class="['strength-fill', `strength-${newPasswordStrength.level}`]" :style="{width: newPasswordStrength.percent + '%'}"></div>
                  </div>
                  <div :class="['strength-text', `strength-${newPasswordStrength.level}`]">
                    {{ newPasswordStrength.text }} ({{ newPasswordStrength.percent }}%)
                  </div>
                </div>
              </div>

              <!-- 確認新密碼 -->
              <div class="form-group">
                <label>
                  確認新密碼 <span class="required">*</span>
                </label>
                <div class="password-input-wrapper">
                  <input
                    v-model="formData.confirm_new_password"
                    :type="showConfirmPassword ? 'text' : 'password'"
                    :class="['form-control', { 'is-invalid': errors.confirm_new_password }]"
                    placeholder="請再次輸入新密碼"
                    @input="validateConfirmNewPassword"
                  />
                  <button type="button" @click="showConfirmPassword = !showConfirmPassword" class="btn-toggle-password">
                    {{ showConfirmPassword ? '👁️' : '👁️‍🗨️' }}
                  </button>
                </div>
                <div v-if="errors.confirm_new_password" class="error-message">{{ errors.confirm_new_password }}</div>
              </div>
            </div>
          </div>

          <!-- 角色分配 -->
          <div class="form-group">
            <label>角色分配</label>
            <div class="role-selector">
              <div v-if="rolesLoading" class="loading-text">載入中...</div>
              <div v-else-if="availableRoles.length === 0" class="empty-text">無可用角色</div>
              <div v-else class="role-list">
                <div
                  v-for="role in availableRoles"
                  :key="role.id"
                  class="role-item"
                  @click="toggleRole(role.id)"
                >
                  <input
                    type="checkbox"
                    :value="role.id"
                    v-model="formData.role_ids"
                    @click.stop
                    class="role-checkbox"
                  />
                  <div class="role-content">
                    <div class="role-name">{{ role.display_name }}</div>
                    <div class="role-meta">
                      <code>{{ role.name }}</code>
                      <span v-if="role.description" class="role-divider">·</span>
                      <span v-if="role.description">{{ role.description }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="!rolesLoading && availableRoles.length > 0" class="role-hint">
              已選擇 {{ formData.role_ids?.length || 0 }} 個角色
            </div>
          </div>

          <!-- 創建資訊（僅編輯模式） -->
          <div v-if="isEditMode && admin" class="info-group">
            <div class="info-item">
              <span class="info-label">創建時間：</span>
              <span>{{ formatDateTime(admin.created_at) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">最後登入：</span>
              <span>{{ formatDateTime(admin.last_login_at) }}</span>
            </div>
          </div>

          <!-- 按鈕 -->
          <div class="modal-footer">
            <button type="button" @click="$emit('close')" class="btn btn-secondary">
              取消
            </button>
            <button type="submit" :disabled="submitting || !isFormValid" class="btn btn-primary">
              {{ submitting ? '處理中...' : (isEditMode ? '儲存變更' : '確認新增') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { API_BASE_URL } from '@/config/api'

export default {
  name: 'AdminFormModal',
  props: {
    admin: {
      type: Object,
      default: null
    }
  },
  emits: ['close', 'success'],
  setup(props, { emit }) {
    const authStore = useAuthStore()
    const isEditMode = computed(() => !!props.admin)
    const isSelfEdit = computed(() => props.admin?.id === authStore.user?.id)

    const formData = ref({
      username: '',
      password: '',
      email: '',
      full_name: '',
      is_active: true,
      new_password: '',
      confirm_new_password: '',
      role_ids: []
    })

    const errors = ref({})
    const submitting = ref(false)
    const showPassword = ref(false)
    const showNewPassword = ref(false)
    const showConfirmPassword = ref(false)
    const resetPassword = ref(false)

    // 角色相關狀態
    const availableRoles = ref([])
    const rolesLoading = ref(false)

    // 加載角色列表
    const loadAvailableRoles = async () => {
      rolesLoading.value = true
      try {
        const token = localStorage.getItem('auth_token')
        const response = await fetch(`${API_BASE_URL}/api/roles`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        if (!response.ok) {
          throw new Error('載入角色列表失敗')
        }
        const data = await response.json()
        availableRoles.value = data.items || []
      } catch (error) {
        console.error('載入角色列表失敗:', error)
      } finally {
        rolesLoading.value = false
      }
    }

    // 加載用戶的角色
    const loadAdminRoles = async (adminId) => {
      try {
        const token = localStorage.getItem('auth_token')
        const response = await fetch(`${API_BASE_URL}/api/admins/${adminId}/roles`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        if (!response.ok) {
          throw new Error('載入用戶角色失敗')
        }
        const data = await response.json()
        formData.value.role_ids = data.roles.map(r => r.id)
      } catch (error) {
        console.error('載入用戶角色失敗:', error)
        formData.value.role_ids = []
      }
    }

    // 編輯模式：填充現有資料
    watch(() => props.admin, async (newAdmin) => {
      if (newAdmin) {
        formData.value = {
          username: newAdmin.username || '',
          password: '',
          email: newAdmin.email || '',
          full_name: newAdmin.full_name || '',
          is_active: newAdmin.is_active,
          new_password: '',
          confirm_new_password: '',
          role_ids: []
        }
        // 重置重設密碼狀態
        resetPassword.value = false
        // 載入用戶的角色
        await loadAdminRoles(newAdmin.id)
      } else {
        formData.value.role_ids = []
      }
    }, { immediate: true })

    // 組件掛載時加載角色列表
    loadAvailableRoles()

    // 密碼強度計算函數
    const calculatePasswordStrength = (pwd) => {
      if (!pwd) return { percent: 0, level: 'weak', text: '弱' }

      let score = 0
      if (pwd.length >= 8) score += 20
      if (pwd.length >= 12) score += 10
      if (/[a-z]/.test(pwd)) score += 20
      if (/[A-Z]/.test(pwd)) score += 20
      if (/\d/.test(pwd)) score += 20
      if (/[^a-zA-Z0-9]/.test(pwd)) score += 10

      let level = 'weak'
      let text = '弱'
      if (score >= 80) {
        level = 'strong'
        text = '強'
      } else if (score >= 50) {
        level = 'medium'
        text = '中'
      }

      return { percent: score, level, text }
    }

    // 新增模式密碼強度
    const passwordStrength = computed(() => {
      return calculatePasswordStrength(formData.value.password)
    })

    // 重設密碼強度
    const newPasswordStrength = computed(() => {
      return calculatePasswordStrength(formData.value.new_password)
    })

    // 表單驗證
    const validateUsername = () => {
      errors.value.username = ''
      const username = formData.value.username

      if (!username) {
        errors.value.username = '帳號不能為空'
      } else if (username.length < 3 || username.length > 50) {
        errors.value.username = '帳號長度必須在 3-50 字元之間'
      } else if (!/^[a-zA-Z0-9_]+$/.test(username)) {
        errors.value.username = '帳號只能包含英數字和底線'
      }
    }

    const validatePassword = () => {
      errors.value.password = ''
      const pwd = formData.value.password

      if (!isEditMode.value) {
        if (!pwd) {
          errors.value.password = '密碼不能為空'
        }
      }
    }

    const validateEmail = () => {
      errors.value.email = ''
      const email = formData.value.email

      if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        errors.value.email = 'Email 格式不正確'
      }
    }

    // 處理重設密碼勾選
    const handleResetPasswordToggle = () => {
      if (!resetPassword.value) {
        // 取消勾選時清空密碼欄位和錯誤訊息
        formData.value.new_password = ''
        formData.value.confirm_new_password = ''
        errors.value.new_password = ''
        errors.value.confirm_new_password = ''
      }
    }

    // 切換重設密碼 checkbox
    const toggleResetPassword = () => {
      resetPassword.value = !resetPassword.value
      handleResetPasswordToggle()
    }

    // 切換角色選擇
    const toggleRole = (roleId) => {
      const index = formData.value.role_ids.indexOf(roleId)
      if (index > -1) {
        formData.value.role_ids.splice(index, 1)
      } else {
        formData.value.role_ids.push(roleId)
      }
    }

    // 驗證新密碼
    const validateNewPassword = () => {
      errors.value.new_password = ''
      const pwd = formData.value.new_password

      if (resetPassword.value && !pwd) {
        errors.value.new_password = '新密碼不能為空'
      }

      // 重新驗證確認密碼
      if (formData.value.confirm_new_password) {
        validateConfirmNewPassword()
      }
    }

    // 驗證確認新密碼
    const validateConfirmNewPassword = () => {
      errors.value.confirm_new_password = ''

      if (resetPassword.value) {
        if (!formData.value.confirm_new_password) {
          errors.value.confirm_new_password = '請再次輸入新密碼'
        } else if (formData.value.new_password !== formData.value.confirm_new_password) {
          errors.value.confirm_new_password = '兩次輸入的密碼不一致'
        }
      }
    }

    // 表單是否有效
    const isFormValid = computed(() => {
      if (isEditMode.value) {
        // 編輯模式
        const basicValid = !errors.value.email

        // 如果勾選重設密碼，需要額外驗證
        if (resetPassword.value) {
          return basicValid &&
                 formData.value.new_password &&
                 formData.value.confirm_new_password &&
                 formData.value.new_password === formData.value.confirm_new_password &&
                 !errors.value.new_password &&
                 !errors.value.confirm_new_password
        }

        return basicValid
      } else {
        // 新增模式
        return formData.value.username &&
               formData.value.password &&
               !errors.value.username &&
               !errors.value.password &&
               !errors.value.email
      }
    })

    // 提交表單
    const handleSubmit = async () => {
      // 驗證所有欄位
      if (!isEditMode.value) {
        validateUsername()
        validatePassword()
      }
      validateEmail()

      // 如果勾選重設密碼，驗證新密碼
      if (resetPassword.value) {
        validateNewPassword()
        validateConfirmNewPassword()
      }

      if (!isFormValid.value) return

      submitting.value = true

      try {
        const token = localStorage.getItem('auth_token')

        // 編輯模式
        if (isEditMode.value) {
          // 1. 更新基本資料和角色
          const updateUrl = `${API_BASE_URL}/api/admins/${props.admin.id}`
          const updateBody = {
            email: formData.value.email,
            full_name: formData.value.full_name,
            is_active: formData.value.is_active,
            role_ids: formData.value.role_ids
          }

          const updateResponse = await fetch(updateUrl, {
            method: 'PUT',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(updateBody)
          })

          if (!updateResponse.ok) {
            const error = await updateResponse.json()
            throw new Error(error.detail || '更新用戶失敗')
          }

          // 2. 如果勾選重設密碼，調用重設密碼 API
          if (resetPassword.value) {
            const resetPwdUrl = `${API_BASE_URL}/api/admins/${props.admin.id}/reset-password`
            const resetPwdBody = {
              new_password: formData.value.new_password
            }

            const resetPwdResponse = await fetch(resetPwdUrl, {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              },
              body: JSON.stringify(resetPwdBody)
            })

            if (!resetPwdResponse.ok) {
              const error = await resetPwdResponse.json()
              throw new Error(error.detail || '重設密碼失敗')
            }

            alert('用戶資料已更新，密碼已重設成功')
          } else {
            alert('用戶資料已更新')
          }
        } else {
          // 新增模式
          const url = `${API_BASE_URL}/api/admins`
          const body = {
            username: formData.value.username,
            password: formData.value.password,
            email: formData.value.email,
            full_name: formData.value.full_name,
            role_ids: formData.value.role_ids
          }

          const response = await fetch(url, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
          })

          if (!response.ok) {
            const error = await response.json()
            throw new Error(error.detail || '新增用戶失敗')
          }

          alert('用戶已新增成功')
        }

        emit('success')
      } catch (error) {
        console.error('提交失敗:', error)
        alert(error.message)
      } finally {
        submitting.value = false
      }
    }

    // 格式化時間
    const formatDateTime = (dateString) => {
      if (!dateString) return '-'
      const date = new Date(dateString)
      return date.toLocaleString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    }

    return {
      isEditMode,
      isSelfEdit,
      formData,
      errors,
      submitting,
      showPassword,
      showNewPassword,
      showConfirmPassword,
      resetPassword,
      passwordStrength,
      newPasswordStrength,
      isFormValid,
      availableRoles,
      rolesLoading,
      validateUsername,
      validatePassword,
      validateEmail,
      handleResetPasswordToggle,
      toggleResetPassword,
      toggleRole,
      validateNewPassword,
      validateConfirmNewPassword,
      handleSubmit,
      formatDateTime
    }
  }
}
</script>

<style scoped>
/* 彈窗遮罩 */

/* 彈窗主體 */
.modal-content {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 560px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

/* 彈窗標題列 */
.modal-header {
  padding: 20px 24px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #212529;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #6c757d;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background 0.2s;
}

.btn-close:hover {
  background: #e9ecef;
  color: #495057;
}

/* 彈窗內容 */
.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.modal-body::-webkit-scrollbar {
  width: 6px;
}

.modal-body::-webkit-scrollbar-track {
  background: transparent;
}

.modal-body::-webkit-scrollbar-thumb {
  background: #dee2e6;
  border-radius: 3px;
}

.modal-body::-webkit-scrollbar-thumb:hover {
  background: #adb5bd;
}

/* 表單群組 */
.form-group {
  margin-bottom: 18px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #2d3748;
  font-size: 14px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #2d3748;
  font-size: 14px;
}

.required {
  color: #f56565;
}

/* 輸入框 */
.form-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
  transition: border-color 0.15s;
  background: white;
  color: #495057;
}

.form-control:focus {
  outline: none;
  border-color: #80bdff;
  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}

.form-control.is-invalid {
  border-color: #dc3545;
}

.form-control.is-invalid:focus {
  box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.25);
}

.form-control:disabled {
  background: #e9ecef;
  color: #6c757d;
  cursor: not-allowed;
}

/* 密碼輸入框容器 */
.password-input-wrapper {
  position: relative;
}

.password-input-wrapper .form-control {
  padding-right: 40px;
}

.btn-toggle-password {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 18px;
  padding: 0 10px;
  color: #6c757d;
  transition: color 0.15s;
}

.btn-toggle-password:hover {
  color: #495057;
}

/* 密碼強度指示器 */
.password-strength {
  margin-top: 8px;
}

.strength-bar {
  height: 6px;
  background: #e9ecef;
  border-radius: 3px;
  overflow: hidden;
}

.strength-fill {
  height: 100%;
  transition: width 0.3s, background 0.3s;
}

.strength-fill.strength-weak {
  background: #dc3545;
}

.strength-fill.strength-medium {
  background: #ffc107;
}

.strength-fill.strength-strong {
  background: #28a745;
}

.strength-text {
  font-size: 12px;
  margin-top: 4px;
  font-weight: 500;
}

.strength-text.strength-weak {
  color: #dc3545;
}

.strength-text.strength-medium {
  color: #856404;
}

.strength-text.strength-strong {
  color: #155724;
}

/* 錯誤訊息 */
.error-message {
  color: #dc3545;
  font-size: 12px;
}

/* 提示訊息 */
.form-hint {
  color: #718096;
  line-height: 1.5;
}

.form-hint.warning {
  color: #c05621;
  background: #fffaf0;
  padding: 8px 12px;
  border-radius: 6px;
  border-left: 3px solid #ed8936;
  margin-top: 8px;
}

/* Checkbox 樣式（參考權限選擇器） */
.checkbox-wrapper {
  padding: 0;
}

.checkbox-item {
  display: flex;
  align-items: flex-start;
  padding: 8px 10px;
  margin-bottom: 4px;
  cursor: pointer;
  border-radius: 3px;
  transition: background 0.1s;
}

.checkbox-item:hover {
  background: #f5f5f5;
}

.checkbox-input {
  width: 16px;
  min-width: 16px;
  max-width: 16px;
  height: 16px;
  margin: 1px 12px 0 0;
  cursor: pointer;
  flex: 0 0 16px;
}

.checkbox-content {
  flex: 1 1 auto;
  min-width: 0;
  width: 100%;
}

.checkbox-text {
  font-size: 14px;
  color: #333;
  line-height: 1.4;
}

/* 角色選擇器 */
.role-selector {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  background: #fafafa;
  max-height: 320px;
  overflow-y: auto;
}

.role-selector::-webkit-scrollbar {
  width: 6px;
}

.role-selector::-webkit-scrollbar-track {
  background: transparent;
}

.role-selector::-webkit-scrollbar-thumb {
  background: #d0d0d0;
  border-radius: 3px;
}

.loading-text,
.empty-text {
  text-align: center;
  color: #999;
  padding: 32px 16px;
  font-size: 14px;
}

.role-list {
  padding: 8px;
}

.role-item {
  display: flex;
  align-items: flex-start;
  padding: 8px 10px;
  margin-bottom: 2px;
  cursor: pointer;
  border-radius: 3px;
  background: white;
  transition: background 0.1s;
}

.role-item:last-child {
  margin-bottom: 0;
}

.role-item:hover {
  background: #f5f5f5;
}

.role-checkbox {
  width: 16px;
  min-width: 16px;
  max-width: 16px;
  height: 16px;
  margin: 1px 12px 0 0;
  cursor: pointer;
  flex: 0 0 16px;
}

.role-content {
  flex: 1 1 auto;
  min-width: 0;
  width: 100%;
}

.role-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 4px;
}

.role-meta {
  font-size: 12px;
  color: #888;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.role-meta code {
  font-family: 'Consolas', 'Monaco', monospace;
  color: #666;
  background: #f0f0f0;
  padding: 1px 5px;
  border-radius: 2px;
  font-size: 11px;
}

.role-divider {
  color: #ddd;
}

.role-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #666;
}

/* 資訊群組 */
.info-group {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 4px;
  margin-top: 16px;
  border: 1px solid #dee2e6;
}

.info-item {
  display: flex;
  gap: 8px;
  font-size: 13px;
  margin-bottom: 6px;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-label {
  font-weight: 500;
  color: #6c757d;
  min-width: 80px;
}

.info-item > span:last-child {
  color: #495057;
}

/* 彈窗底部按鈕區 */
.modal-footer {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #dee2e6;
}

.btn {
  padding: 8px 16px;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 400;
  transition: all 0.15s;
}

.btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.btn-secondary {
  background: #6c757d;
  border-color: #6c757d;
}

.btn-secondary:hover:not(:disabled) {
  background: #5a6268;
  border-color: #545b62;
}

.btn-primary {
  background: #007bff;
  border-color: #007bff;
}

.btn-primary:hover:not(:disabled) {
  background: #0069d9;
  border-color: #0062cc;
}

/* 重設密碼區塊 */
.reset-password-fields {
  margin-top: 12px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 4px;
  border: 1px solid #dee2e6;
}

/* 警告提示框 */
.warning-box {
  display: flex;
  gap: 10px;
  padding: 12px;
  background: #fff3cd;
  border: 1px solid #ffeeba;
  border-radius: 4px;
  margin-bottom: 16px;
}

.warning-icon {
  font-size: 18px;
  flex-shrink: 0;
  line-height: 1.5;
}

.warning-box p {
  margin: 0;
  font-size: 13px;
  color: #856404;
  line-height: 1.5;
}
</style>
