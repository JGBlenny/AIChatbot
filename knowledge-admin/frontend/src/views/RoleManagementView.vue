<template>
  <div>
    <h2>🔐 角色管理</h2>

    <!-- 搜尋與篩選 -->
    <div class="toolbar">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="🔍 搜尋角色名稱或說明..."
      />
      <select v-model="filterSystem">
        <option value="all">全部角色</option>
        <option value="true">系統角色</option>
        <option value="false">自訂角色</option>
      </select>
      <button
        v-permission="'role:create'"
        class="btn-primary btn-sm"
        @click="openCreateModal"
      >
        ➕ 新增角色
      </button>
    </div>

    <!-- 載入中 -->
    <div v-if="isLoading" class="loading-container">
      <div class="spinner"></div>
      <p>載入中...</p>
    </div>

    <!-- 錯誤訊息 -->
    <div v-else-if="errorMessage" class="error-container">
      <p>{{ errorMessage }}</p>
      <button class="btn-secondary" @click="fetchRoles">重試</button>
    </div>

    <!-- 角色列表 -->
    <div v-else class="roles-container">
      <div v-if="filteredRoles.length === 0" class="empty-state">
        <p>找不到符合條件的角色</p>
      </div>

      <div v-else class="roles-table-wrapper">
        <table class="roles-table">
          <thead>
            <tr>
              <th>角色名稱</th>
              <th>角色代碼</th>
              <th>說明</th>
              <th>類型</th>
              <th>權限數量</th>
              <th>用戶數量</th>
              <th>創建時間</th>
              <th class="actions-column">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="role in filteredRoles" :key="role.id" class="role-row">
              <!-- 角色名稱 -->
              <td class="role-name">
                <span class="name-text">{{ role.display_name }}</span>
                <span v-if="role.name === 'super_admin'" class="badge badge-special">超級管理員</span>
              </td>

              <!-- 角色代碼 -->
              <td>
                <code class="role-code">{{ role.name }}</code>
              </td>

              <!-- 說明 -->
              <td class="description">
                {{ role.description || '-' }}
              </td>

              <!-- 類型 -->
              <td>
                <span v-if="role.is_system" class="badge badge-system">系統</span>
                <span v-else class="badge badge-custom">自訂</span>
              </td>

              <!-- 權限數量 -->
              <td>
                <span class="count-badge permission-count">
                  {{ role.permission_count || 0 }} 個
                </span>
              </td>

              <!-- 用戶數量 -->
              <td>
                <span class="count-badge user-count">
                  {{ role.user_count || 0 }} 人
                </span>
              </td>

              <!-- 創建時間 -->
              <td class="date">
                {{ formatDate(role.created_at) }}
              </td>

              <!-- 操作 -->
              <td class="actions">
                <button
                  v-permission="'role:view'"
                  class="btn-icon"
                  title="查看詳情"
                  @click="viewRole(role)"
                >
                  👁
                </button>
                <button
                  v-permission="'role:edit'"
                  class="btn-icon"
                  title="編輯"
                  @click="openEditModal(role)"
                >
                  ✏️
                </button>
                <button
                  v-if="!role.is_system"
                  v-permission="'role:delete'"
                  class="btn-icon btn-danger"
                  title="刪除"
                  @click="confirmDelete(role)"
                >
                  🗑
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 角色表單彈窗 -->
    <RoleFormModal
      :is-open="isModalOpen"
      :role="currentRole"
      :permission-groups="permissionGroups"
      @close="closeModal"
      @success="handleSuccess"
    />

    <!-- 角色詳情彈窗 -->
    <RoleDetailModal
      :is-open="isDetailModalOpen"
      :role="detailRole"
      @close="closeDetailModal"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePermission } from '../composables/usePermission'
import RoleFormModal from '../components/RoleFormModal.vue'
import RoleDetailModal from '../components/RoleDetailModal.vue'
import axios from 'axios'
import { API_BASE_URL } from '@/config/api'

const { can } = usePermission()

// 資料狀態
const roles = ref([])
const permissionGroups = ref([])
const isLoading = ref(false)
const errorMessage = ref('')

// 搜尋與篩選
const searchQuery = ref('')
const filterSystem = ref('all')

// 彈窗狀態
const isModalOpen = ref(false)
const currentRole = ref(null)
const isDetailModalOpen = ref(false)
const detailRole = ref(null)

// 篩選後的角色列表
const filteredRoles = computed(() => {
  let filtered = roles.value

  // 按系統/自訂篩選
  if (filterSystem.value !== 'all') {
    const isSystem = filterSystem.value === 'true'
    filtered = filtered.filter(r => r.is_system === isSystem)
  }

  // 按搜尋關鍵字篩選
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(r =>
      r.name.toLowerCase().includes(query) ||
      r.display_name.toLowerCase().includes(query) ||
      (r.description && r.description.toLowerCase().includes(query))
    )
  }

  return filtered
})

// 載入角色列表
async function fetchRoles() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const params = {}
    if (searchQuery.value) params.search = searchQuery.value
    if (filterSystem.value !== 'all') params.is_system = filterSystem.value

    const response = await axios.get(`${API_BASE_URL}/api/roles`, { params })
    roles.value = response.data.items || []
  } catch (error) {
    console.error('載入角色列表失敗:', error)
    errorMessage.value = '載入角色列表失敗，請稍後再試'
  } finally {
    isLoading.value = false
  }
}

// 載入權限分組
async function fetchPermissionGroups() {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/roles/permissions/all`)
    permissionGroups.value = response.data || []
  } catch (error) {
    console.error('載入權限列表失敗:', error)
  }
}

// 打開新增彈窗
function openCreateModal() {
  currentRole.value = null
  isModalOpen.value = true
}

// 打開編輯彈窗
async function openEditModal(role) {
  try {
    // 獲取完整角色資料（含權限列表）
    const response = await axios.get(`${API_BASE_URL}/api/roles/${role.id}`)
    currentRole.value = response.data
    isModalOpen.value = true
  } catch (error) {
    console.error('載入角色詳情失敗:', error)
    alert('載入角色詳情失敗')
  }
}

// 查看角色詳情
async function viewRole(role) {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/roles/${role.id}`)
    detailRole.value = response.data
    isDetailModalOpen.value = true
  } catch (error) {
    console.error('載入角色詳情失敗:', error)
    alert('載入角色詳情失敗')
  }
}

// 關閉彈窗
function closeModal() {
  isModalOpen.value = false
  currentRole.value = null
}

function closeDetailModal() {
  isDetailModalOpen.value = false
  detailRole.value = null
}

// 成功後重新載入
function handleSuccess() {
  fetchRoles()
}

// 確認刪除
function confirmDelete(role) {
  if (confirm(`確定要刪除角色「${role.display_name}」嗎？\n\n此操作將同時移除該角色的所有權限配置和用戶關聯。`)) {
    deleteRole(role.id)
  }
}

// 刪除角色
async function deleteRole(roleId) {
  try {
    await axios.delete(`${API_BASE_URL}/api/roles/${roleId}`)
    alert('角色已刪除')
    fetchRoles()
  } catch (error) {
    console.error('刪除角色失敗:', error)
    if (error.response?.data?.detail) {
      alert(`刪除失敗: ${error.response.data.detail}`)
    } else {
      alert('刪除角色失敗')
    }
  }
}

// 格式化日期
function formatDate(dateString) {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

// 初始化
onMounted(() => {
  fetchRoles()
  fetchPermissionGroups()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  align-items: center;
  background: white;
  padding: 20px;
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  border: 2px solid #f0f0f0;
}

.toolbar input,
.toolbar select {
  padding: 12px 16px;
  border: 2px solid #e8eaed;
  border-radius: 10px;
  font-size: 14px;
  transition: all 0.3s;
  background: white;
}

.toolbar input:focus,
.toolbar select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.toolbar input:hover,
.toolbar select:hover {
  border-color: #667eea;
}

.loading-container,
.error-container,
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #718096;
}

.spinner {
  border: 3px solid #f3f4f6;
  border-top: 3px solid #667eea;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.roles-table-wrapper {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.roles-table {
  width: 100%;
  border-collapse: collapse;
}

.roles-table thead {
  background: #f7fafc;
  border-bottom: 2px solid #e2e8f0;
}

.roles-table th {
  padding: 15px;
  text-align: left;
  font-weight: 600;
  color: #4a5568;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.roles-table td {
  padding: 15px;
  border-bottom: 1px solid #e2e8f0;
  font-size: 14px;
  color: #2d3748;
}

.role-row:hover {
  background: #f7fafc;
}

.name-text {
  font-weight: 500;
}

.badge-special {
  margin-left: 8px;
}

.role-code {
  font-family: 'Courier New', monospace;
  background: #edf2f7;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: #667eea;
}

.description {
  max-width: 300px;
  color: #718096;
}

.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.badge-system {
  background: #bee3f8;
  color: #2c5282;
}

.badge-custom {
  background: #c6f6d5;
  color: #276749;
}

.badge-special {
  background: #feebc8;
  color: #c05621;
}

.count-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
}

.permission-count {
  background: #e6fffa;
  color: #285e61;
}

.user-count {
  background: #fef5e7;
  color: #975a16;
}

.date {
  color: #718096;
  font-size: 13px;
}

.actions {
  white-space: nowrap;
}

.actions-column {
  text-align: center;
  width: 150px;
}

.btn-icon {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 6px;
  transition: background 0.2s;
}

.btn-icon:hover {
  background: #edf2f7;
}

.btn-danger:hover {
  background: #fff5f5;
}

.btn-secondary {
  background: white;
  color: #4a5568;
  border: 1px solid #cbd5e0;
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: #f7fafc;
  border-color: #a0aec0;
}
</style>
