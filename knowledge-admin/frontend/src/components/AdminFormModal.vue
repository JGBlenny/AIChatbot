<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h3>{{ isEditMode ? '編輯管理員' : '新增管理員' }}</h3>
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
              placeholder="管理員姓名"
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
            <label>狀態</label>
            <div class="checkbox-group">
              <label>
                <input type="checkbox" v-model="formData.is_active" />
                啟用
              </label>
            </div>
            <div v-if="isSelfEdit" class="form-hint warning">
              ⚠️ 注意：你不能停用自己的帳號
            </div>
          </div>

          <!-- 重設密碼（僅編輯模式） -->
          <div v-if="isEditMode && !isSelfEdit" class="form-group">
            <label>密碼</label>
            <div class="checkbox-group">
              <label>
                <input type="checkbox" v-model="resetPassword" @change="handleResetPasswordToggle" />
                重設密碼
              </label>
            </div>

            <div v-if="resetPassword" class="reset-password-fields">
              <div class="warning-box">
                <span class="warning-icon">⚠️</span>
                <div>
                  <p>此操作將重設該管理員的密碼。請務必將新密碼告知該管理員。</p>
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

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

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
      confirm_new_password: ''
    })

    const errors = ref({})
    const submitting = ref(false)
    const showPassword = ref(false)
    const showNewPassword = ref(false)
    const showConfirmPassword = ref(false)
    const resetPassword = ref(false)

    // 編輯模式：填充現有資料
    watch(() => props.admin, (newAdmin) => {
      if (newAdmin) {
        formData.value = {
          username: newAdmin.username || '',
          password: '',
          email: newAdmin.email || '',
          full_name: newAdmin.full_name || '',
          is_active: newAdmin.is_active,
          new_password: '',
          confirm_new_password: ''
        }
        // 重置重設密碼狀態
        resetPassword.value = false
      }
    }, { immediate: true })

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
          // 1. 更新基本資料
          const updateUrl = `${API_BASE_URL}/api/admins/${props.admin.id}`
          const updateBody = {
            email: formData.value.email,
            full_name: formData.value.full_name,
            is_active: formData.value.is_active
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
            throw new Error(error.detail || '更新管理員失敗')
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

            alert('管理員資料已更新，密碼已重設成功')
          } else {
            alert('管理員資料已更新')
          }
        } else {
          // 新增模式
          const url = `${API_BASE_URL}/api/admins`
          const body = {
            username: formData.value.username,
            password: formData.value.password,
            email: formData.value.email,
            full_name: formData.value.full_name
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
            throw new Error(error.detail || '新增管理員失敗')
          }

          alert('管理員已新增成功')
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
      validateUsername,
      validatePassword,
      validateEmail,
      handleResetPasswordToggle,
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
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

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
  display: flex;
  justify-content: space-between;
  align-items: center;
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
  margin-bottom: 6px;
  font-weight: 500;
  color: #495057;
  font-size: 14px;
}

.required {
  color: #dc3545;
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
  margin-top: 4px;
}

/* 提示訊息 */
.form-hint {
  font-size: 12px;
  color: #6c757d;
  margin-top: 4px;
}

.form-hint.warning {
  color: #856404;
}

/* 勾選框群組 */
.checkbox-group {
  margin: 0;
}

.checkbox-group label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: normal;
  cursor: pointer;
  margin: 0;
  color: #495057;
}

.checkbox-group input[type="checkbox"] {
  margin: 0;
  cursor: pointer;
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
  display: flex;
  justify-content: flex-end;
  gap: 10px;
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
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #5a6268;
  border-color: #545b62;
}

.btn-primary {
  background: #007bff;
  border-color: #007bff;
  color: white;
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
