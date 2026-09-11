<template>
  <div>
    <h2>👥 用戶管理</h2>

    <!-- 工具列 -->
    <div class="toolbar">
      <div style="flex: 1; display: flex; gap: 10px;">
        <input
          v-model="searchQuery"
          placeholder="🔍 搜尋用戶（帳號、姓名、Email）..."
          @input="handleSearch"
          style="flex: 1;"
        />
        <select v-model="statusFilter" @change="loadAdmins">
          <option value="all">全部狀態</option>
          <option value="true">啟用</option>
          <option value="false">停用</option>
        </select>
      </div>
      <button v-permission="'admin:create'" @click="showCreateModal" class="btn-primary btn-sm">
        ➕ 新增用戶
      </button>
    </div>

    <!-- 載入中 -->
    <div v-if="loading" class="loading">
      <p>載入中...</p>
    </div>

    <!-- 用戶列表 -->
    <div v-else-if="admins.length === 0" class="empty-state">
      <p>沒有找到用戶</p>
      <button @click="showCreateModal" class="btn-primary btn-sm" style="margin-top: 20px;">
        新增第一個用戶
      </button>
    </div>

    <div v-else class="admin-list">
      <table class="admin-list">
        <thead>
          <tr>
            <th width="60">ID</th>
            <th width="150">帳號</th>
            <th width="150">姓名</th>
            <th width="200">Email</th>
            <th width="80">狀態</th>
            <th width="180">最後登入</th>
            <th width="180">創建時間</th>
            <th width="220">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="admin in admins" :key="admin.id">
            <td>{{ admin.id }}</td>
            <td>
              <strong>{{ admin.username }}</strong>
              <span v-if="admin.id === currentUser?.id" class="badge badge-self">自己</span>
            </td>
            <td>{{ admin.full_name || '-' }}</td>
            <td>{{ admin.email || '-' }}</td>
            <td>
              <span :class="['badge', admin.is_active ? 'badge-active' : 'badge-inactive']">
                {{ admin.is_active ? '✅ 啟用' : '❌ 停用' }}
              </span>
            </td>
            <td>{{ formatDateTime(admin.last_login_at) }}</td>
            <td>{{ formatDateTime(admin.created_at) }}</td>
            <td>
              <div class="action-buttons">
                <button v-permission="'admin:edit'" @click="showEditModal(admin)" class="btn-sm btn-secondary" title="編輯" data-test="edit-button">
                  ✏️ 編輯
                </button>
                <button
                  v-if="admin.id !== currentUser?.id && admin.is_active"
                  v-permission="'admin:edit'"
                  @click="confirmDisable(admin)"
                  class="btn-sm btn-danger"
                  title="停用"
                >
                  🚫 停用
                </button>
                <button
                  v-if="!admin.is_active"
                  v-permission="'admin:edit'"
                  @click="enableAdmin(admin)"
                  class="btn-sm btn-success"
                  title="啟用"
                >
                  ✅ 啟用
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 統計資訊和分頁控制 -->
    <div v-if="admins.length > 0 && total > 0" style="margin-top: 20px; display: flex; justify-content: space-between; align-items: center;">
      <div style="color: #606266;">
        總計 {{ total }} 筆用戶，顯示第 {{ offset + 1 }} - {{ Math.min(offset + limit, total) }} 筆
      </div>
      <div class="pagination-controls">
        <button
          @click="prevPage"
          :disabled="offset === 0"
          class="btn-pagination"
        >
          ← 上一頁
        </button>
        <span style="margin: 0 15px; color: #606266;">
          第 {{ currentPage }} / {{ totalPages }} 頁
        </span>
        <button
          @click="nextPage"
          :disabled="offset + limit >= total"
          class="btn-pagination"
        >
          下一頁 →
        </button>
      </div>
    </div>

    <!-- 新增/編輯用戶對話框 -->
    <AdminFormModal
      v-if="showFormModal"
      :admin="selectedAdmin"
      @close="closeFormModal"
      @success="handleFormSuccess"
    />
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import AdminFormModal from '@/components/AdminFormModal.vue'
import { API_BASE_URL } from '@/config/api'

export default {
  name: 'AdminManagementView',
  components: {
    AdminFormModal
  },
  setup() {
    const authStore = useAuthStore()
    const currentUser = computed(() => authStore.user)

    const admins = ref([])
    const loading = ref(false)
    const searchQuery = ref('')
    const statusFilter = ref('all')
    const total = ref(0)
    const limit = ref(50)
    const offset = ref(0)

    const showFormModal = ref(false)
    const selectedAdmin = ref(null)

    let searchTimeout = null

    // 載入用戶列表
    const loadAdmins = async () => {
      loading.value = true
      try {
        const token = localStorage.getItem('auth_token')
        const params = new URLSearchParams({
          limit: limit.value,
          offset: offset.value
        })

        if (searchQuery.value) {
          params.append('search', searchQuery.value)
        }

        if (statusFilter.value !== 'all') {
          params.append('is_active', statusFilter.value)
        }

        const response = await fetch(`${API_BASE_URL}/api/admins?${params}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })

        if (!response.ok) {
          throw new Error('載入用戶列表失敗')
        }

        const data = await response.json()
        admins.value = data.items
        total.value = data.total
      } catch (error) {
        console.error('載入用戶失敗:', error)
        alert('載入用戶列表失敗')
      } finally {
        loading.value = false
      }
    }

    // 搜尋處理（防抖）
    const handleSearch = () => {
      clearTimeout(searchTimeout)
      searchTimeout = setTimeout(() => {
        offset.value = 0
        loadAdmins()
      }, 500)
    }

    // 分頁
    const nextPage = () => {
      offset.value += limit.value
      loadAdmins()
    }

    const prevPage = () => {
      offset.value = Math.max(0, offset.value - limit.value)
      loadAdmins()
    }

    // 顯示新增對話框
    const showCreateModal = () => {
      selectedAdmin.value = null
      showFormModal.value = true
    }

    // 顯示編輯對話框
    const showEditModal = (admin) => {
      console.log('showEditModal 被調用', admin)
      console.log('showFormModal 之前的值:', showFormModal.value)
      selectedAdmin.value = admin
      showFormModal.value = true
      console.log('showFormModal 之後的值:', showFormModal.value)
      console.log('selectedAdmin:', selectedAdmin.value)
    }

    // 關閉表單對話框
    const closeFormModal = () => {
      showFormModal.value = false
      selectedAdmin.value = null
    }

    // 表單提交成功
    const handleFormSuccess = () => {
      closeFormModal()
      loadAdmins()
    }

    // 確認停用
    const confirmDisable = (admin) => {
      if (confirm(`確定要停用用戶「${admin.username}」嗎？\n\n停用後該用戶將無法登入系統。\n你可以隨時重新啟用此帳號。`)) {
        disableAdmin(admin)
      }
    }

    // 停用用戶
    const disableAdmin = async (admin) => {
      try {
        const token = localStorage.getItem('auth_token')
        const response = await fetch(`${API_BASE_URL}/api/admins/${admin.id}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || '停用用戶失敗')
        }

        alert('用戶已停用')
        loadAdmins()
      } catch (error) {
        console.error('停用用戶失敗:', error)
        alert(error.message)
      }
    }

    // 啟用用戶
    const enableAdmin = async (admin) => {
      try {
        const token = localStorage.getItem('auth_token')
        const response = await fetch(`${API_BASE_URL}/api/admins/${admin.id}`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ is_active: true })
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || '啟用用戶失敗')
        }

        alert('用戶已啟用')
        loadAdmins()
      } catch (error) {
        console.error('啟用用戶失敗:', error)
        alert(error.message)
      }
    }

    // 格式化時間
    const formatDateTime = (dateString) => {
      if (!dateString) return '-'
      const date = new Date(dateString)
      const now = new Date()
      const diff = now - date
      const minutes = Math.floor(diff / 60000)
      const hours = Math.floor(diff / 3600000)
      const days = Math.floor(diff / 86400000)

      if (minutes < 1) return '剛剛'
      if (minutes < 60) return `${minutes} 分鐘前`
      if (hours < 24) return `${hours} 小時前`
      if (days < 7) return `${days} 天前`

      return date.toLocaleString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    }

    // 初始化載入
    onMounted(() => {
      loadAdmins()
    })

    // Computed properties for pagination
    const currentPage = computed(() => Math.floor(offset.value / limit.value) + 1)
    const totalPages = computed(() => Math.ceil(total.value / limit.value))

    return {
      admins,
      loading,
      searchQuery,
      statusFilter,
      total,
      limit,
      offset,
      showFormModal,
      selectedAdmin,
      currentUser,
      currentPage,
      totalPages,
      loadAdmins,
      handleSearch,
      nextPage,
      prevPage,
      showCreateModal,
      showEditModal,
      closeFormModal,
      handleFormSuccess,
      confirmDisable,
      enableAdmin,
      formatDateTime
    }
  }
}
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

.admin-list table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  border: 2px solid #f0f0f0;
}

.admin-list th,
.admin-list td {
  padding: 15px;
  text-align: left;
}

.admin-list th {
  background: #fafafa;
  font-weight: 600;
  color: #2c3e50;
  font-size: 14px;
  border: none;
  border-bottom: 2px solid #e0e0e0;
  text-align: center;
}

.admin-list tbody tr {
  transition: all 0.3s ease;
  border-bottom: 1px solid #f0f0f0;
}

.admin-list tbody tr:last-child {
  border-bottom: none;
}

.admin-list tbody tr:hover {
  background: linear-gradient(90deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
  transform: scale(1.01);
  box-shadow: 0 2px 12px rgba(102, 126, 234, 0.1);
}

.admin-list td {
  color: #2c3e50;
  font-size: 14px;
}

.admin-list td strong {
  color: #2d3748;
  font-weight: 500;
}

.badge {
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  letter-spacing: 0.3px;
}

.badge-active {
  background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
  color: #155724;
  border: 1px solid #b1dfbb;
}

.badge-inactive {
  background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
  color: #721c24;
  border: 1px solid #f1b0b7;
}

.badge-self {
  background: linear-gradient(135deg, #cfe2ff 0%, #b6d4fe 100%);
  color: #052c65;
  border: 1px solid #9ec5fe;
  margin-left: 8px;
  font-weight: 700;
}

.action-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.action-buttons .btn-sm {
  padding: 8px 14px;
  font-size: 13px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.action-buttons .btn-sm:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.pagination-controls {
  display: flex;
  align-items: center;
}

.btn-pagination {
  padding: 8px 16px;
  background: #409EFF;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-pagination:hover:not(:disabled) {
  background: #66B1FF;
  transform: translateY(-1px);
}

.btn-pagination:disabled {
  background: #C0C4CC;
  cursor: not-allowed;
  opacity: 0.6;
}

.loading,
.empty-state {
  text-align: center;
  padding: 60px 20px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  border: 2px solid #f0f0f0;
}

.loading p,
.empty-state p {
  font-size: 16px;
  color: #64748b;
  margin-bottom: 20px;
}

.btn-sm {
  padding: 10px 16px;
  font-size: 13px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.btn-sm:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover {
  background: linear-gradient(135deg, #5568d3 0%, #6a3f8f 100%);
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
}

.btn-secondary {
  background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%);
  color: white;
}

.btn-secondary:hover {
  background: linear-gradient(135deg, #5a6268 0%, #495057 100%);
}

.btn-warning {
  background: linear-gradient(135deg, #ffc107 0%, #ff9800 100%);
  color: #1a202c;
}

.btn-warning:hover {
  background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
}

.btn-danger {
  background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
  color: white;
}

.btn-danger:hover {
  background: linear-gradient(135deg, #c82333 0%, #bd2130 100%);
}

.btn-success {
  background: linear-gradient(135deg, #28a745 0%, #218838 100%);
  color: white;
}

.btn-success:hover {
  background: linear-gradient(135deg, #218838 0%, #1e7e34 100%);
}
</style>
