<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="handleCancel">
    <div class="modal-container">
      <!-- 標題列 -->
      <div class="modal-header">
        <h2>{{ isEditMode ? '編輯角色' : '新增角色' }}</h2>
        <button class="close-btn" @click="handleCancel">×</button>
      </div>

      <!-- 表單內容 -->
      <div class="modal-body">
        <form @submit.prevent="handleSubmit">
          <!-- 角色代碼（僅新增時可編輯） -->
          <div class="form-group">
            <label class="form-label">
              角色代碼 <span class="required">*</span>
            </label>
            <input
              v-model="formData.name"
              type="text"
              class="form-input"
              placeholder="例如: custom_manager"
              :disabled="isEditMode"
              required
            />
            <p class="form-hint">3-50 字元，只能包含英數字和底線，創建後不可修改</p>
          </div>

          <!-- 顯示名稱 -->
          <div class="form-group">
            <label class="form-label">
              顯示名稱 <span class="required">*</span>
            </label>
            <input
              v-model="formData.display_name"
              type="text"
              class="form-input"
              placeholder="例如: 自訂管理員"
              required
            />
            <p class="form-hint">用於 UI 顯示的友好名稱</p>
          </div>

          <!-- 說明 -->
          <div class="form-group">
            <label class="form-label">角色說明</label>
            <textarea
              v-model="formData.description"
              class="form-textarea"
              placeholder="描述此角色的職責和用途..."
              rows="3"
            ></textarea>
          </div>

          <!-- 權限選擇 -->
          <div class="form-group">
            <label class="form-label">
              權限設定 <span class="required">*</span>
            </label>
            <PermissionSelector
              v-model="formData.permission_ids"
              :permission-groups="permissionGroups"
            />
            <p class="form-hint">選擇此角色擁有的權限</p>
          </div>

          <!-- 錯誤訊息 -->
          <div v-if="errorMessage" class="error-message">
            {{ errorMessage }}
          </div>

          <!-- 按鈕區 -->
          <div class="modal-footer">
            <button type="button" class="btn-secondary" @click="handleCancel">
              取消
            </button>
            <button type="submit" class="btn-primary" :disabled="isSubmitting">
              {{ isSubmitting ? '處理中...' : (isEditMode ? '保存' : '創建') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import PermissionSelector from './PermissionSelector.vue'
import axios from 'axios'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  role: {
    type: Object,
    default: null
  },
  permissionGroups: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['close', 'success'])

// 表單資料
const formData = ref({
  name: '',
  display_name: '',
  description: '',
  permission_ids: []
})

const isSubmitting = ref(false)
const errorMessage = ref('')

// 是否為編輯模式
const isEditMode = computed(() => !!props.role)

// 監聽 role prop 變化，填充表單
watch(() => props.role, (newRole) => {
  if (newRole) {
    formData.value = {
      name: newRole.name || '',
      display_name: newRole.display_name || '',
      description: newRole.description || '',
      permission_ids: newRole.permissions?.map(p => p.id) || []
    }
  } else {
    resetForm()
  }
}, { immediate: true })

// 重置表單
function resetForm() {
  formData.value = {
    name: '',
    display_name: '',
    description: '',
    permission_ids: []
  }
  errorMessage.value = ''
}

// 取消
function handleCancel() {
  resetForm()
  emit('close')
}

// 提交表單
async function handleSubmit() {
  errorMessage.value = ''
  isSubmitting.value = true

  try {
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

    if (isEditMode.value) {
      // 編輯模式：PUT /api/roles/{id}
      const updateData = {
        display_name: formData.value.display_name,
        description: formData.value.description,
        permission_ids: formData.value.permission_ids
      }

      await axios.put(`${API_BASE_URL}/api/roles/${props.role.id}`, updateData)
    } else {
      // 新增模式：POST /api/roles
      const createData = {
        name: formData.value.name,
        display_name: formData.value.display_name,
        description: formData.value.description
      }

      const response = await axios.post(`${API_BASE_URL}/api/roles`, createData)

      // 創建角色後，立即更新權限
      if (formData.value.permission_ids.length > 0) {
        await axios.put(`${API_BASE_URL}/api/roles/${response.data.id}`, {
          permission_ids: formData.value.permission_ids
        })
      }
    }

    // 成功後通知父組件
    emit('success')
    resetForm()
    emit('close')
  } catch (error) {
    console.error('保存角色失敗:', error)
    if (error.response?.data?.detail) {
      errorMessage.value = error.response.data.detail
    } else {
      errorMessage.value = isEditMode.value ? '更新角色失敗' : '創建角色失敗'
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
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
  padding: 20px;
}

.modal-container {
  background: white;
  border-radius: 12px;
  width: 100%;
  max-width: 800px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #2d3748;
}

.close-btn {
  background: none;
  border: none;
  font-size: 32px;
  color: #a0aec0;
  cursor: pointer;
  line-height: 1;
  padding: 0;
  width: 32px;
  height: 32px;
  transition: color 0.2s;
}

.close-btn:hover {
  color: #4a5568;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.form-group {
  margin-bottom: 24px;
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

.form-input,
.form-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #cbd5e0;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-input:disabled {
  background: #f7fafc;
  color: #a0aec0;
  cursor: not-allowed;
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
  font-family: inherit;
}

.form-hint {
  margin-top: 6px;
  font-size: 12px;
  color: #718096;
}

.error-message {
  padding: 12px;
  background: #fff5f5;
  border: 1px solid #fc8181;
  border-radius: 6px;
  color: #c53030;
  font-size: 14px;
  margin-bottom: 16px;
}

.modal-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
}

.btn-primary,
.btn-secondary {
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #5568d3;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.btn-primary:disabled {
  background: #cbd5e0;
  cursor: not-allowed;
}

.btn-secondary {
  background: white;
  color: #4a5568;
  border: 1px solid #cbd5e0;
}

.btn-secondary:hover {
  background: #f7fafc;
  border-color: #a0aec0;
}
</style>
