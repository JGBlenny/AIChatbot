<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h3>修改密碼</h3>
        <button @click="$emit('close')" class="btn-close">&times;</button>
      </div>

      <div class="modal-body">
        <form @submit.prevent="handleSubmit">
          <!-- 舊密碼 -->
          <div class="form-group">
            <label>
              舊密碼 <span class="required">*</span>
            </label>
            <div class="password-input-wrapper">
              <input
                v-model="formData.current_password"
                :type="showCurrentPassword ? 'text' : 'password'"
                :class="['form-control', { 'is-invalid': errors.current_password }]"
                placeholder="請輸入目前的密碼"
                @input="errors.current_password = ''"
              />
              <button type="button" @click="showCurrentPassword = !showCurrentPassword" class="btn-toggle-password">
                {{ showCurrentPassword ? '👁️' : '👁️‍🗨️' }}
              </button>
            </div>
            <div v-if="errors.current_password" class="error-message">{{ errors.current_password }}</div>
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
                <div :class="['strength-fill', `strength-${passwordStrength.level}`]" :style="{width: passwordStrength.percent + '%'}"></div>
              </div>
              <div :class="['strength-text', `strength-${passwordStrength.level}`]">
                {{ passwordStrength.text }} ({{ passwordStrength.percent }}%)
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
                v-model="formData.confirm_password"
                :type="showConfirmPassword ? 'text' : 'password'"
                :class="['form-control', { 'is-invalid': errors.confirm_password }]"
                placeholder="請再次輸入新密碼"
                @input="validateConfirmPassword"
              />
              <button type="button" @click="showConfirmPassword = !showConfirmPassword" class="btn-toggle-password">
                {{ showConfirmPassword ? '👁️' : '👁️‍🗨️' }}
              </button>
            </div>
            <div v-if="errors.confirm_password" class="error-message">{{ errors.confirm_password }}</div>
          </div>

          <!-- 按鈕 -->
          <div class="modal-footer">
            <button type="button" @click="$emit('close')" class="btn btn-secondary">
              取消
            </button>
            <button type="submit" :disabled="submitting || !isFormValid" class="btn btn-primary">
              {{ submitting ? '處理中...' : '確認修改' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { API_BASE_URL } from '@/config/api'

export default {
  name: 'ChangePasswordModal',
  emits: ['close', 'success'],
  setup(props, { emit }) {
    const formData = ref({
      current_password: '',
      new_password: '',
      confirm_password: ''
    })

    const errors = ref({})
    const submitting = ref(false)
    const showCurrentPassword = ref(false)
    const showNewPassword = ref(false)
    const showConfirmPassword = ref(false)

    // 密碼強度計算
    const passwordStrength = computed(() => {
      const pwd = formData.value.new_password
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
    })

    // 驗證新密碼
    const validateNewPassword = () => {
      errors.value.new_password = ''
      const pwd = formData.value.new_password

      if (!pwd) {
        errors.value.new_password = '新密碼不能為空'
      }

      // 重新驗證確認密碼
      if (formData.value.confirm_password) {
        validateConfirmPassword()
      }
    }

    // 驗證確認密碼
    const validateConfirmPassword = () => {
      errors.value.confirm_password = ''

      if (!formData.value.confirm_password) {
        errors.value.confirm_password = '請再次輸入新密碼'
      } else if (formData.value.new_password !== formData.value.confirm_password) {
        errors.value.confirm_password = '兩次輸入的密碼不一致'
      }
    }

    // 表單是否有效
    const isFormValid = computed(() => {
      return formData.value.current_password &&
             formData.value.new_password &&
             formData.value.confirm_password &&
             formData.value.new_password === formData.value.confirm_password &&
             !errors.value.current_password &&
             !errors.value.new_password &&
             !errors.value.confirm_password
    })

    // 提交表單
    const handleSubmit = async () => {
      // 驗證所有欄位
      if (!formData.value.current_password) {
        errors.value.current_password = '請輸入舊密碼'
      }
      validateNewPassword()
      validateConfirmPassword()

      if (!isFormValid.value) return

      submitting.value = true

      try {
        const token = localStorage.getItem('auth_token')
        const response = await fetch(`${API_BASE_URL}/api/admins/me/change-password`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            current_password: formData.value.current_password,
            new_password: formData.value.new_password
          })
        })

        if (!response.ok) {
          const error = await response.json()

          // 特殊處理舊密碼錯誤
          if (error.detail?.includes('舊密碼')) {
            errors.value.current_password = error.detail
            throw new Error('請檢查您輸入的舊密碼')
          }

          throw new Error(error.detail || '修改密碼失敗')
        }

        alert('密碼修改成功！請使用新密碼重新登入')
        emit('success')
      } catch (error) {
        console.error('修改密碼失敗:', error)
        alert(error.message)
      } finally {
        submitting.value = false
      }
    }

    return {
      formData,
      errors,
      submitting,
      showCurrentPassword,
      showNewPassword,
      showConfirmPassword,
      passwordStrength,
      isFormValid,
      validateNewPassword,
      validateConfirmPassword,
      handleSubmit
    }
  }
}
</script>

<style scoped>

.modal-content {
  max-width: 500px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-header {
  padding: 20px;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-close:hover {
  color: #333;
}

.modal-body {
  padding: 20px;
}


.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #333;
}

.required {
  color: #d32f2f;
}

.form-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-control:focus {
  outline: none;
  border-color: #1976d2;
}

.form-control.is-invalid {
  border-color: #d32f2f;
}

.password-input-wrapper {
  position: relative;
}

.btn-toggle-password {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  cursor: pointer;
  font-size: 18px;
}

.password-strength {
  margin-top: 8px;
}

.strength-bar {
  height: 6px;
  background: #eee;
  border-radius: 3px;
  overflow: hidden;
}

.strength-fill {
  height: 100%;
  transition: width 0.3s, background 0.3s;
}

.strength-fill.strength-weak {
  background: #d32f2f;
}

.strength-fill.strength-medium {
  background: #f57c00;
}

.strength-fill.strength-strong {
  background: #388e3c;
}

.strength-text {
  font-size: 12px;
  margin-top: 4px;
}

.strength-text.strength-weak {
  color: #d32f2f;
}

.strength-text.strength-medium {
  color: #f57c00;
}

.strength-text.strength-strong {
  color: #388e3c;
}

.error-message {
  color: #d32f2f;
  font-size: 12px;
}

.modal-footer {
  gap: 12px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: #757575;
}

.btn-secondary:hover:not(:disabled) {
  background: #616161;
}

.btn-primary {
  background: #1976d2;
}

.btn-primary:hover:not(:disabled) {
  background: #1565c0;
}
</style>
