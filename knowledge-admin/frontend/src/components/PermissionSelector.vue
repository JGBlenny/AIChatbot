<template>
  <div class="permission-selector">
    <!-- 頂部工具列 -->
    <div class="selector-header">
      <div class="selected-count">
        已選 <span class="count">{{ selectedPermissionIds.length }}</span> 項
      </div>
      <div class="actions">
        <button @click="selectAll" class="action-btn">全選</button>
        <button @click="clearAll" class="action-btn">清空</button>
      </div>
    </div>

    <!-- 搜尋框 -->
    <div class="search-box">
      <input
        type="text"
        v-model="searchQuery"
        placeholder="搜尋權限名稱..."
        class="search-input"
      />
    </div>

    <!-- 權限分組列表 -->
    <div class="groups-container">
      <div
        v-for="group in filteredGroups"
        :key="group.resource"
        class="group"
      >
        <!-- 分組標題（可點擊展開/收合） -->
        <div class="group-title" @click="toggleGroup(group.resource)">
          <span class="expand-icon">{{ isExpanded(group.resource) ? '−' : '+' }}</span>
          <span class="icon">{{ group.icon }}</span>
          <span class="title-text">{{ group.title }}</span>
          <span class="badge">{{ getSelectedInGroup(group) }} / {{ group.permissions.length }}</span>
        </div>

        <!-- 權限列表 -->
        <div v-show="isExpanded(group.resource)" class="permissions-list">
          <div
            v-for="permission in group.permissions"
            :key="permission.id"
            class="permission-item"
            @click="togglePermission(permission.id)"
          >
            <input
              type="checkbox"
              :value="permission.id"
              :checked="selectedPermissionIds.includes(permission.id)"
              @change.stop="togglePermission(permission.id)"
              class="perm-checkbox"
            />
            <div class="perm-info">
              <div class="perm-name">{{ permission.display_name }}</div>
              <div class="perm-code">{{ permission.name }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
  permissionGroups: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['update:modelValue'])

const selectedPermissionIds = ref([...props.modelValue])
const searchQuery = ref('')
const expandedGroups = ref(new Set())

// 初始展開第一個分組
if (props.permissionGroups.length > 0) {
  expandedGroups.value.add(props.permissionGroups[0].resource)
}

// 監聽外部變更
watch(() => props.modelValue, (newVal) => {
  selectedPermissionIds.value = [...newVal]
})

// 監聽內部變更
watch(selectedPermissionIds, (newVal) => {
  emit('update:modelValue', newVal)
}, { deep: true })

// 篩選後的分組
const filteredGroups = computed(() => {
  if (!searchQuery.value) return props.permissionGroups

  return props.permissionGroups.map(group => ({
    ...group,
    permissions: group.permissions.filter(p =>
      p.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      p.display_name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      (p.description && p.description.toLowerCase().includes(searchQuery.value.toLowerCase()))
    )
  })).filter(group => group.permissions.length > 0)
})

function selectAll() {
  const allPermissionIds = props.permissionGroups.flatMap(g => g.permissions.map(p => p.id))
  selectedPermissionIds.value = allPermissionIds
}

function clearAll() {
  selectedPermissionIds.value = []
}

function toggleGroup(resource) {
  if (expandedGroups.value.has(resource)) {
    expandedGroups.value.delete(resource)
  } else {
    expandedGroups.value.add(resource)
  }
}

function isExpanded(resource) {
  return expandedGroups.value.has(resource)
}

function togglePermission(permissionId) {
  const index = selectedPermissionIds.value.indexOf(permissionId)
  if (index > -1) {
    selectedPermissionIds.value.splice(index, 1)
  } else {
    selectedPermissionIds.value.push(permissionId)
  }
}

function getSelectedInGroup(group) {
  return group.permissions.filter(p => selectedPermissionIds.value.includes(p.id)).length
}
</script>

<style scoped>
.permission-selector {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
}

/* 頂部工具列 */
.selector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: #f8f9fa;
  border-bottom: 1px solid #e0e0e0;
}

.selected-count {
  font-size: 13px;
  color: #555;
  font-weight: 500;
}

.selected-count .count {
  display: inline-block;
  min-width: 20px;
  padding: 1px 6px;
  background: #007bff;
  color: white;
  border-radius: 10px;
  font-weight: 600;
  font-size: 12px;
  text-align: center;
  margin: 0 3px;
}

.actions {
  display: flex;
  gap: 6px;
}

.action-btn {
  padding: 4px 10px;
  border: 1px solid #d0d0d0;
  background: white;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
  color: #333;
  transition: all 0.15s;
}

.action-btn:hover {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

/* 搜尋框 */
.search-box {
  padding: 8px 12px;
  background: white;
  border-bottom: 1px solid #e0e0e0;
}

.search-input {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid #d0d0d0;
  border-radius: 3px;
  font-size: 13px;
  box-sizing: border-box;
}

.search-input:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.1);
}

/* 權限分組容器 */
.groups-container {
  max-height: 400px;
  overflow-y: auto;
  padding: 6px;
}

.groups-container::-webkit-scrollbar {
  width: 6px;
}

.groups-container::-webkit-scrollbar-track {
  background: #f5f5f5;
}

.groups-container::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

.groups-container::-webkit-scrollbar-thumb:hover {
  background: #999;
}

/* 權限分組 */
.group {
  margin-bottom: 6px;
  border: 1px solid #e8e8e8;
  border-radius: 3px;
  overflow: hidden;
}

.group:last-child {
  margin-bottom: 0;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: #f8f9fa;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}

.group-title:hover {
  background: #e9ecef;
}

.expand-icon {
  width: 14px;
  height: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
  color: #666;
  flex-shrink: 0;
}

.icon {
  font-size: 16px;
  flex-shrink: 0;
}

.title-text {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.badge {
  padding: 2px 7px;
  background: #e0e0e0;
  border-radius: 10px;
  font-size: 11px;
  color: #555;
  font-weight: 500;
}

/* 權限列表 */
.permissions-list {
  padding: 8px;
  background: white;
}

.permission-item {
  display: flex;
  align-items: flex-start;
  padding: 6px 8px;
  margin-bottom: 2px;
  cursor: pointer;
  border-radius: 3px;
  transition: background 0.1s;
}

.permission-item:hover {
  background: #f5f5f5;
}

.perm-checkbox {
  width: 16px;
  min-width: 16px;
  max-width: 16px;
  height: 16px;
  margin: 1px 12px 0 0;
  cursor: pointer;
  flex: 0 0 16px;
}

.perm-info {
  flex: 1 1 auto;
  min-width: 0;
  width: 100%;
}

.perm-name {
  font-size: 13px;
  color: #333;
  margin-bottom: 2px;
}

.perm-code {
  font-size: 11px;
  color: #888;
  font-family: 'Consolas', monospace;
}
</style>
