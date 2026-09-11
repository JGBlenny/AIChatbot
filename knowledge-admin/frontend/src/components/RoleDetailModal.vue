<template>
  <div v-if="isOpen && role" class="modal-overlay" @click.self="handleClose">
    <div class="modal-container">
      <!-- 標題列 -->
      <div class="modal-header">
        <h2>角色詳情</h2>
        <button class="close-btn" @click="handleClose">×</button>
      </div>

      <!-- 內容 -->
      <div class="modal-body">
        <!-- 基本資訊 -->
        <section class="section">
          <h3 class="section-title">基本資訊</h3>
          <div class="info-grid">
            <div class="info-item">
              <label>角色名稱</label>
              <div class="info-value">{{ role.display_name }}</div>
            </div>
            <div class="info-item">
              <label>角色代碼</label>
              <div class="info-value">
                <code class="role-code">{{ role.name }}</code>
              </div>
            </div>
            <div class="info-item">
              <label>類型</label>
              <div class="info-value">
                <span v-if="role.is_system" class="badge badge-system">系統角色</span>
                <span v-else class="badge badge-custom">自訂角色</span>
              </div>
            </div>
            <div class="info-item">
              <label>創建時間</label>
              <div class="info-value">{{ formatDate(role.created_at) }}</div>
            </div>
            <div class="info-item full-width">
              <label>說明</label>
              <div class="info-value">{{ role.description || '無' }}</div>
            </div>
          </div>
        </section>

        <!-- 統計資訊 -->
        <section class="section">
          <h3 class="section-title">統計資訊</h3>
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-icon">🔐</div>
              <div class="stat-value">{{ role.permission_count || 0 }}</div>
              <div class="stat-label">權限數量</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon">👥</div>
              <div class="stat-value">{{ role.user_count || 0 }}</div>
              <div class="stat-label">用戶數量</div>
            </div>
          </div>
        </section>

        <!-- 權限列表 -->
        <section class="section">
          <h3 class="section-title">
            權限列表 ({{ role.permissions?.length || 0 }} 個)
          </h3>

          <div v-if="!role.permissions || role.permissions.length === 0" class="empty-state">
            此角色尚未配置任何權限
          </div>

          <div v-else class="permissions-list">
            <div
              v-for="group in groupedPermissions"
              :key="group.resource"
              class="permission-group"
            >
              <div class="group-header">
                <span class="group-icon">{{ group.icon }}</span>
                <span class="group-title">{{ group.title }}</span>
                <span class="group-count">({{ group.permissions.length }} 個)</span>
              </div>
              <div class="group-permissions">
                <div
                  v-for="perm in group.permissions"
                  :key="perm.id"
                  class="permission-tag"
                >
                  <span class="perm-name">{{ perm.display_name }}</span>
                  <code class="perm-code">{{ perm.name }}</code>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- 底部 -->
      <div class="modal-footer">
        <button class="btn-secondary" @click="handleClose">關閉</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  role: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close'])

// 資源圖示和名稱對應
const resourceMeta = {
  knowledge: { icon: '📚', title: '知識庫管理' },
  intent: { icon: '🎯', title: '意圖管理' },
  test: { icon: '🧪', title: '測試與回測' },
  vendor: { icon: '🏢', title: '業者管理' },
  sop: { icon: '📄', title: '平台 SOP' },
  config: { icon: '⚙️', title: '配置管理' },
  document: { icon: '📝', title: '文檔處理' },
  admin: { icon: '👤', title: '管理員管理' },
  role: { icon: '🔐', title: '角色管理' }
}

// 按資源分組權限
const groupedPermissions = computed(() => {
  if (!props.role?.permissions) return []

  const groups = {}

  props.role.permissions.forEach(perm => {
    const resource = perm.resource
    if (!groups[resource]) {
      groups[resource] = {
        resource,
        title: resourceMeta[resource]?.title || resource,
        icon: resourceMeta[resource]?.icon || '📦',
        permissions: []
      }
    }
    groups[resource].permissions.push(perm)
  })

  return Object.values(groups)
})

function handleClose() {
  emit('close')
}

function formatDate(dateString) {
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
  max-width: 900px;
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

.section {
  margin-bottom: 32px;
}

.section:last-child {
  margin-bottom: 0;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #2d3748;
  margin: 0 0 16px 0;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-item.full-width {
  grid-column: 1 / -1;
}

.info-item label {
  font-size: 13px;
  color: #718096;
  font-weight: 500;
}

.info-value {
  font-size: 14px;
  color: #2d3748;
}

.role-code {
  font-family: 'Courier New', monospace;
  background: #edf2f7;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 13px;
  color: #667eea;
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

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.stat-card {
  background: #f7fafc;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}

.stat-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #667eea;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: #718096;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #a0aec0;
  font-size: 14px;
}

.permissions-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.permission-group {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
}

.group-header {
  background: #f7fafc;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid #e2e8f0;
}

.group-icon {
  font-size: 18px;
}

.group-title {
  font-weight: 600;
  color: #2d3748;
  flex: 1;
}

.group-count {
  font-size: 13px;
  color: #718096;
}

.group-permissions {
  padding: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.permission-tag {
  background: white;
  border: 1px solid #cbd5e0;
  border-radius: 6px;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.perm-name {
  font-size: 13px;
  color: #2d3748;
  font-weight: 500;
}

.perm-code {
  font-family: 'Courier New', monospace;
  font-size: 11px;
  color: #667eea;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
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
