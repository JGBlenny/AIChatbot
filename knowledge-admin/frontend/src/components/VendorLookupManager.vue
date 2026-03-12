<template>
  <div class="lookup-manager">
    <div class="section-header">
      <h3>💾 Lookup 數據管理</h3>
      <div class="header-actions">
        <button @click="loadLookupData" class="btn-secondary btn-sm">🔄 刷新</button>
        <button @click="clearAllLookupData" class="btn-danger btn-sm">🗑️ 清除 Lookup</button>
        <button @click="exportToExcel" class="btn-success btn-sm">📤 匯出 Excel</button>
        <button @click="showImportModal" class="btn-info btn-sm">📥 匯入 Excel</button>
      </div>
    </div>

    <!-- 篩選區 -->
    <div class="filter-bar">
      <div class="filter-group">
        <label>類別篩選:</label>
        <select v-model="filterCategory" @change="loadLookupData" class="filter-select">
          <option value="">全部類別</option>
          <option v-for="cat in categories" :key="cat.category" :value="cat.category">
            {{ cat.category_name || cat.category }} ({{ cat.count }})
          </option>
        </select>
      </div>

      <div class="filter-group">
        <label>搜尋:</label>
        <input
          v-model="searchQuery"
          @input="filterLookupData"
          type="text"
          placeholder="搜尋 Key 或 Value..."
          class="filter-input"
        />
      </div>

      <div class="filter-group">
        <label>狀態:</label>
        <select v-model="filterStatus" @change="filterLookupData" class="filter-select">
          <option value="all">全部</option>
          <option value="active">啟用</option>
          <option value="inactive">停用</option>
        </select>
      </div>
    </div>

    <!-- 統計卡片 -->
    <div v-if="stats" class="stats-cards">
      <div class="stat-card">
        <div class="stat-label">總記錄數</div>
        <div class="stat-value">{{ stats.total_records || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">啟用記錄</div>
        <div class="stat-value">{{ stats.active_records || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">類別數</div>
        <div class="stat-value">{{ stats.categories_count || 0 }}</div>
      </div>
    </div>

    <!-- 載入狀態 -->
    <div v-if="loading" class="loading">
      <p>⏳ 載入中...</p>
    </div>

    <!-- 數據表格 -->
    <div v-else-if="filteredLookupData.length > 0" class="lookup-table-container">
      <table class="lookup-table">
        <thead>
          <tr>
            <th width="50">ID</th>
            <th width="150">類別</th>
            <th width="250">Lookup Key</th>
            <th width="200">Lookup Value</th>
            <th width="150">說明</th>
            <th width="80">狀態</th>
            <th width="150">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in filteredLookupData" :key="item.id">
            <td>{{ item.id }}</td>
            <td>
              <span class="category-badge">{{ item.category_name || item.category }}</span>
            </td>
            <td>
              <code class="lookup-key">{{ item.lookup_key }}</code>
            </td>
            <td>
              <span class="lookup-value">{{ formatLookupValue(item) }}</span>
            </td>
            <td>
              <small>{{ getMetadataDescription(item.metadata) }}</small>
            </td>
            <td>
              <span class="status-badge" :class="item.is_active ? 'status-active' : 'status-inactive'">
                {{ item.is_active ? '✓ 啟用' : '✗ 停用' }}
              </span>
            </td>
            <td>
              <button @click="editLookup(item)" class="btn-edit btn-xs">編輯</button>
              <button @click="toggleStatus(item)" class="btn-warning btn-xs">
                {{ item.is_active ? '停用' : '啟用' }}
              </button>
              <button @click="deleteLookup(item)" class="btn-delete btn-xs">刪除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 分頁 -->
      <div v-if="totalPages > 1" class="pagination">
        <button @click="currentPage--" :disabled="currentPage === 1" class="btn-secondary btn-sm">上一頁</button>
        <span class="page-info">第 {{ currentPage }} / {{ totalPages }} 頁</span>
        <button @click="currentPage++" :disabled="currentPage === totalPages" class="btn-secondary btn-sm">下一頁</button>
      </div>
    </div>

    <!-- 空狀態 -->
    <div v-else class="empty-state">
      <p>📭 尚無 Lookup 數據</p>
      <p class="hint">點擊「新增 Lookup」開始建立查詢數據</p>
    </div>

    <!-- 新增/編輯 Modal -->
    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop style="max-width: 600px;">
        <div class="modal-header">
          <h3>{{ editingItem ? '編輯 Lookup' : '新增 Lookup' }}</h3>
          <button @click="closeModal" class="btn-close">✕</button>
        </div>

        <form @submit.prevent="saveLookup">
          <div class="modal-body">
            <div class="form-group">
              <label>類別 *</label>
              <input
                v-model="formData.category"
                required
                placeholder="例如: billing_interval"
                :disabled="editingItem"
              />
              <small class="hint">類別 ID，建立後不可修改</small>
            </div>

            <div class="form-group">
              <label>類別顯示名稱</label>
              <input
                v-model="formData.category_name"
                placeholder="例如: 帳單週期"
              />
            </div>

            <div class="form-group">
              <label>Lookup Key *</label>
              <input
                v-model="formData.lookup_key"
                required
                placeholder="例如: 新北市板橋區忠孝路48巷4弄8號"
              />
              <small class="hint">查詢鍵，用於匹配</small>
            </div>

            <div class="form-group">
              <label>Lookup Value *</label>
              <input
                v-model="formData.lookup_value"
                required
                placeholder="例如: 每月5號"
              />
              <small class="hint">查詢結果值</small>
            </div>

            <div class="form-group">
              <label>元數據 (JSON)</label>
              <textarea
                v-model="formData.metadata"
                rows="3"
                placeholder='{"description": "說明文字", "unit": "元"}'
              ></textarea>
              <small class="hint">選填，JSON 格式的額外數據</small>
            </div>

            <div class="form-group">
              <label>
                <input type="checkbox" v-model="formData.is_active" />
                啟用此 Lookup
              </label>
            </div>
          </div>

          <div class="modal-footer">
            <button type="button" @click="closeModal" class="btn-secondary btn-sm">取消</button>
            <button type="submit" class="btn-primary btn-sm" :disabled="saving">
              {{ saving ? '儲存中...' : '儲存' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 匯入 Excel Modal -->
    <div v-if="showImportExcelModal" class="modal-overlay" @click="closeImportModal">
      <div class="modal-content" @click.stop style="max-width: 700px;">
        <div class="modal-header">
          <h3>📥 批量匯入 Lookup 數據</h3>
          <button @click="closeImportModal" class="btn-close">✕</button>
        </div>

        <div class="modal-body">
          <div class="import-info">
            <h4>📋 Excel 格式說明</h4>
            <p>請下載並填寫業務格式範本，範本包含以下分頁：</p>
            <div class="import-notes">
              <ul>
                <li><strong>電費資訊</strong>：物件地址、電號、寄送區間、計費方式等</li>
                <li><strong>水費資訊</strong>：水費相關設定</li>
                <li><strong>瓦斯費資訊</strong>：瓦斯費相關設定</li>
                <li><strong>租金資訊</strong>：租金相關設定</li>
                <li><strong>其他服務資訊</strong>：停車費、管理費、客服聯絡方式等</li>
              </ul>
              <p><strong>注意事項：</strong></p>
              <ul>
                <li>每個分頁的第一行為範例，請從第二行開始填寫</li>
                <li>「物件地址」為必填欄位，需完整填寫</li>
                <li>系統會自動將業務格式轉換為 Lookup 格式</li>
                <li>填寫完成後匯入即可</li>
              </ul>
            </div>
            <button @click="downloadTemplate" class="btn-secondary btn-sm">📄 下載範本</button>
          </div>

          <div class="form-group" style="margin-top: 20px;">
            <label>選擇 Excel 檔案 *</label>
            <input
              type="file"
              ref="fileInput"
              @change="handleFileSelect"
              accept=".xlsx,.xls,.csv"
              class="file-input"
            />
            <small class="hint">支援 .xlsx, .xls, .csv 格式</small>
          </div>

          <div v-if="selectedFile" class="file-preview">
            <p>📎 已選擇：{{ selectedFile.name }}</p>
            <p>大小：{{ (selectedFile.size / 1024).toFixed(2) }} KB</p>
          </div>

          <div v-if="importProgress.show" class="import-progress">
            <p>{{ importProgress.message }}</p>
            <div v-if="importProgress.success !== null" class="import-result">
              <p v-if="importProgress.success" class="success-msg">
                ✅ 成功匯入 {{ importProgress.successCount }} 筆，失敗 {{ importProgress.failCount }} 筆
              </p>
              <p v-else class="error-msg">
                ❌ 匯入失敗：{{ importProgress.error }}
              </p>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button type="button" @click="closeImportModal" class="btn-secondary btn-sm">取消</button>
          <button
            @click="performImport"
            class="btn-primary btn-sm"
            :disabled="!selectedFile || importing"
          >
            {{ importing ? '匯入中...' : '開始匯入' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { API_BASE_URL } from '@/config/api';

const RAG_API = `${API_BASE_URL}/rag-api/v1`;

export default {
  name: 'VendorLookupManager',
  props: {
    vendorId: {
      type: Number,
      required: true
    }
  },
  data() {
    return {
      loading: false,
      saving: false,
      lookupData: [],
      filteredLookupData: [],
      categories: [],
      stats: null,
      filterCategory: '',
      filterStatus: 'all',
      searchQuery: '',
      currentPage: 1,
      itemsPerPage: 20,
      showModal: false,
      editingItem: null,
      formData: {
        category: '',
        category_name: '',
        lookup_key: '',
        lookup_value: '',
        metadata: '',
        is_active: true
      },
      // 匯入相關
      showImportExcelModal: false,
      selectedFile: null,
      importing: false,
      importProgress: {
        show: false,
        message: '',
        success: null,
        successCount: 0,
        failCount: 0,
        error: ''
      }
    };
  },
  computed: {
    totalPages() {
      return Math.ceil(this.filteredLookupData.length / this.itemsPerPage);
    }
  },
  mounted() {
    console.log('🎯 [DEBUG] VendorLookupManager mounted, vendorId:', this.vendorId);
    this.loadCategories();
    this.loadStats();
    this.loadLookupData();
  },
  methods: {
    async loadCategories() {
      try {
        const response = await axios.get(`${RAG_API}/lookup/categories`, {
          params: { vendor_id: this.vendorId }
        });
        this.categories = response.data.categories || [];
      } catch (error) {
        console.error('載入類別失敗:', error);
      }
    },

    async loadStats() {
      try {
        const response = await axios.get(`${RAG_API}/lookup/stats`, {
          params: { vendor_id: this.vendorId }
        });
        this.stats = response.data;
      } catch (error) {
        console.error('載入統計失敗:', error);
      }
    },

    async loadLookupData() {
      this.loading = true;
      console.log('🔍 [DEBUG] loadLookupData 開始, vendorId:', this.vendorId);
      try {
        const params = {
          vendor_id: this.vendorId
        };
        if (this.filterCategory) {
          params.category = this.filterCategory;
        }

        console.log('🔍 [DEBUG] API 請求參數:', params);
        console.log('🔍 [DEBUG] API 路徑:', `${RAG_API}/lookup/manage`);
        const response = await axios.get(`${RAG_API}/lookup/manage`, { params });
        console.log('🔍 [DEBUG] API 響應:', response.data);
        this.lookupData = response.data.records || [];
        console.log('🔍 [DEBUG] lookupData 長度:', this.lookupData.length);
        this.filterLookupData();
        console.log('🔍 [DEBUG] filteredLookupData 長度:', this.filteredLookupData.length);
      } catch (error) {
        console.error('❌ [ERROR] 載入 Lookup 數據失敗:', error);
        alert('載入失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },

    filterLookupData() {
      let filtered = [...this.lookupData];

      // 狀態篩選
      if (this.filterStatus === 'active') {
        filtered = filtered.filter(item => item.is_active);
      } else if (this.filterStatus === 'inactive') {
        filtered = filtered.filter(item => !item.is_active);
      }

      // 搜尋篩選
      if (this.searchQuery.trim()) {
        const query = this.searchQuery.toLowerCase();
        filtered = filtered.filter(item =>
          item.lookup_key.toLowerCase().includes(query) ||
          item.lookup_value.toLowerCase().includes(query) ||
          (item.category && item.category.toLowerCase().includes(query))
        );
      }

      this.filteredLookupData = filtered;
      this.currentPage = 1;
    },

    showAddModal() {
      this.editingItem = null;
      this.formData = {
        category: '',
        category_name: '',
        lookup_key: '',
        lookup_value: '',
        metadata: '',
        is_active: true
      };
      this.showModal = true;
    },

    editLookup(item) {
      this.editingItem = item;
      this.formData = {
        category: item.category,
        category_name: item.category_name || '',
        lookup_key: item.lookup_key,
        lookup_value: item.lookup_value,
        metadata: item.metadata ? JSON.stringify(item.metadata, null, 2) : '',
        is_active: item.is_active
      };
      this.showModal = true;
    },

    async saveLookup() {
      this.saving = true;
      try {
        // 解析 metadata JSON
        let metadata = null;
        if (this.formData.metadata.trim()) {
          try {
            metadata = JSON.parse(this.formData.metadata);
          } catch (e) {
            alert('❌ Metadata 格式錯誤，請確認為有效的 JSON');
            this.saving = false;
            return;
          }
        }

        if (this.editingItem) {
          // 更新 API
          const payload = {
            category_name: this.formData.category_name || null,
            lookup_key: this.formData.lookup_key,
            lookup_value: this.formData.lookup_value,
            metadata: metadata,
            is_active: this.formData.is_active
          };

          await axios.put(`${RAG_API}/lookup/${this.editingItem.id}`, payload);
          alert('✅ Lookup 已更新！');
        } else {
          // 新增 API
          const payload = {
            vendor_id: this.vendorId,
            category: this.formData.category,
            category_name: this.formData.category_name || null,
            lookup_key: this.formData.lookup_key,
            lookup_value: this.formData.lookup_value,
            metadata: metadata,
            is_active: this.formData.is_active
          };

          await axios.post(`${RAG_API}/lookup`, payload);
          alert('✅ Lookup 已新增！');
        }

        this.closeModal();
        this.loadLookupData();
        this.loadStats();
        this.loadCategories();
      } catch (error) {
        console.error('儲存失敗', error);
        alert('儲存失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.saving = false;
      }
    },

    async toggleStatus(item) {
      if (!confirm(`確定要${item.is_active ? '停用' : '啟用'}此 Lookup 嗎？`)) return;

      try {
        await axios.put(`${RAG_API}/lookup/${item.id}`, {
          is_active: !item.is_active
        });

        alert(`✅ 已${item.is_active ? '停用' : '啟用'}！`);
        this.loadLookupData();
        this.loadStats();
      } catch (error) {
        alert('操作失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    async deleteLookup(item) {
      if (!confirm(`確定要刪除此 Lookup 嗎？\n\nKey: ${item.lookup_key}\nValue: ${item.lookup_value}`)) return;

      try {
        await axios.delete(`${RAG_API}/lookup/${item.id}`);
        alert('✅ Lookup 已刪除！');
        this.loadLookupData();
        this.loadStats();
        this.loadCategories();
      } catch (error) {
        alert('刪除失敗：' + (error.response?.data?.detail || error.message));
      }
    },

    closeModal() {
      this.showModal = false;
      this.editingItem = null;
    },

    getMetadataDescription(metadata) {
      if (!metadata) return '-';
      if (typeof metadata === 'string') {
        try {
          metadata = JSON.parse(metadata);
        } catch (e) {
          return metadata.substring(0, 30);
        }
      }
      return metadata.description || metadata.note || '-';
    },

    formatLookupValue(item) {
      const jsonCategories = ['utility_electricity', 'utility_water', 'utility_gas'];

      // 如果是 JSON 類別，嘗試解析並格式化顯示
      if (jsonCategories.includes(item.category)) {
        try {
          let data;
          if (typeof item.lookup_value === 'string') {
            data = JSON.parse(item.lookup_value);
          } else {
            data = item.lookup_value;
          }

          // 只顯示非空值的關鍵欄位
          const keyFields = [];
          for (const [key, value] of Object.entries(data)) {
            if (value && value !== '' && value !== 'null') {
              keyFields.push(`${key}: ${value}`);
            }
          }

          // 限制顯示前 3 個欄位，避免過長
          if (keyFields.length > 3) {
            return keyFields.slice(0, 3).join(' | ') + ` ...等${keyFields.length}項`;
          }
          return keyFields.join(' | ') || '-';

        } catch (e) {
          // 如果解析失敗，顯示原始值的前 50 字元
          return String(item.lookup_value).substring(0, 50) + '...';
        }
      }

      // 非 JSON 類別，直接顯示原始值
      return item.lookup_value;
    },

    // ===== 匯入/匯出功能 =====

    showImportModal() {
      this.showImportExcelModal = true;
      this.selectedFile = null;
      this.importProgress = {
        show: false,
        message: '',
        success: null,
        successCount: 0,
        failCount: 0,
        error: ''
      };
    },

    closeImportModal() {
      this.showImportExcelModal = false;
      this.selectedFile = null;
      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = '';
      }
    },

    handleFileSelect(event) {
      const file = event.target.files[0];
      if (file) {
        this.selectedFile = file;
      }
    },

    async performImport() {
      if (!this.selectedFile) {
        alert('請選擇檔案');
        return;
      }

      this.importing = true;
      this.importProgress = {
        show: true,
        message: '正在上傳並處理檔案...',
        success: null,
        successCount: 0,
        failCount: 0,
        error: ''
      };

      try {
        const formData = new FormData();
        formData.append('file', this.selectedFile);

        const response = await axios.post(
          `${RAG_API}/lookup/import?vendor_id=${this.vendorId}`,
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data'
            }
          }
        );

        this.importProgress = {
          show: true,
          message: '匯入完成',
          success: true,
          successCount: response.data.success_count || 0,
          failCount: response.data.fail_count || 0,
          error: ''
        };

        // 重新載入數據
        this.loadLookupData();
        this.loadStats();
        this.loadCategories();
      } catch (error) {
        console.error('匯入失敗:', error);
        this.importProgress = {
          show: true,
          message: '',
          success: false,
          successCount: 0,
          failCount: 0,
          error: error.response?.data?.detail || error.message
        };
      } finally {
        this.importing = false;
      }
    },

    async clearAllLookupData() {
      const confirmed = confirm(
        `⚠️ 警告：此操作將清除該業者的所有 Lookup 資料！\n\n確定要繼續嗎？此操作無法復原。`
      );

      if (!confirmed) {
        return;
      }

      // 計算總記錄數
      const totalRecords = this.stats?.categories?.reduce((sum, cat) => sum + cat.record_count, 0) || 0;

      // 二次確認
      const doubleConfirmed = confirm(
        `🚨 最後確認：真的要刪除所有 ${totalRecords} 筆 Lookup 記錄嗎？`
      );

      if (!doubleConfirmed) {
        return;
      }

      try {
        const response = await axios.delete(
          `${RAG_API}/lookup/batch?vendor_id=${this.vendorId}`
        );

        if (response.data.success) {
          alert(`✅ ${response.data.message}`);
          await this.loadLookupData(); // 重新載入資料
        }
      } catch (error) {
        console.error('清除失敗:', error);
        alert(`❌ 清除失敗: ${error.response?.data?.detail || error.message}`);
      }
    },

    async exportToExcel() {
      try {
        const params = {
          vendor_id: this.vendorId
        };
        if (this.filterCategory) {
          params.category = this.filterCategory;
        }

        // 使用 blob 方式下載
        const response = await axios.get(`${RAG_API}/lookup/export`, {
          params,
          responseType: 'blob'
        });

        // 建立下載連結
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;

        // 設定檔名
        const filename = `vendor_knowledge_vendor${this.vendorId}_${new Date().toISOString().split('T')[0]}.xlsx`;
        link.setAttribute('download', filename);

        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);

        alert(`✅ Excel 檔案已下載！`);
      } catch (error) {
        console.error('匯出失敗:', error);

        // 處理 Blob 格式的錯誤回應
        if (error.response?.data instanceof Blob) {
          try {
            const text = await error.response.data.text();
            const errorData = JSON.parse(text);
            alert('匯出失敗：' + (errorData.detail || error.message));
          } catch (e) {
            alert('匯出失敗：' + error.message);
          }
        } else {
          alert('匯出失敗：' + (error.response?.data?.detail || error.message));
        }
      }
    },

    async downloadTemplate() {
      try {
        const response = await axios.get(`${RAG_API}/lookup/template`, {
          responseType: 'blob'
        });

        // 建立下載連結
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'Lookup匯入範本.xlsx');
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
      } catch (error) {
        console.error('下載範本失敗:', error);
        alert('下載範本失敗：' + (error.response?.data?.detail || error.message));
      }
    }
  }
};
</script>

<style scoped>
.lookup-manager {
  padding: 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 2px solid #f3f4f6;
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

/* 篩選區 */
.filter-bar {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
  padding: 15px;
  background: #f9fafb;
  border-radius: 6px;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-group label {
  font-size: 13px;
  font-weight: 500;
  color: #666;
  white-space: nowrap;
}

.filter-select {
  padding: 6px 12px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 13px;
  min-width: 150px;
}

.filter-input {
  padding: 6px 12px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 13px;
  min-width: 200px;
}

/* 統計卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15px;
  margin-bottom: 20px;
}

.stat-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
}

.stat-label {
  font-size: 13px;
  opacity: 0.9;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
}

/* 表格 */
.lookup-table-container {
  background: white;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
}

.lookup-table {
  width: 100%;
  border-collapse: collapse;
}

.lookup-table th {
  background: #f9fafb;
  padding: 12px;
  text-align: left;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  border-bottom: 2px solid #e5e7eb;
}

.lookup-table td {
  padding: 12px;
  border-bottom: 1px solid #f3f4f6;
  font-size: 13px;
}

.lookup-table tbody tr:hover {
  background: #f9fafb;
}

.category-badge {
  display: inline-block;
  padding: 4px 10px;
  background: #e0e7ff;
  color: #4338ca;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.lookup-key {
  font-family: monospace;
  font-size: 12px;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 3px;
  color: #1f2937;
  display: inline-block;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lookup-value {
  color: #059669;
  font-weight: 500;
}

.status-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.status-badge.status-active {
  background: #d1fae5;
  color: #065f46;
}

.status-badge.status-inactive {
  background: #f3f4f6;
  color: #6b7280;
}

/* 按鈕 */
.btn-xs {
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  margin-right: 5px;
  transition: all 0.2s;
}

.btn-edit {
  background: #3b82f6;
  color: white;
}

.btn-edit:hover {
  background: #2563eb;
}

.btn-warning {
  background: #f59e0b;
  color: white;
}

.btn-warning:hover {
  background: #d97706;
}

.btn-delete {
  background: #ef4444;
  color: white;
}

.btn-delete:hover {
  background: #dc2626;
}

/* 分頁 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
  padding: 15px;
  border-top: 1px solid #e5e7eb;
}

.page-info {
  font-size: 13px;
  color: #666;
}

/* 空狀態 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #9ca3af;
}

.empty-state p {
  margin: 10px 0;
}

.empty-state .hint {
  font-size: 13px;
}

/* 載入狀態 */
.loading {
  text-align: center;
  padding: 40px;
  color: #9ca3af;
}

/* Modal 樣式 */
.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-weight: 500;
  margin-bottom: 8px;
  color: #374151;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 14px;
  font-family: inherit;
}

.form-group input:disabled {
  background: #f3f4f6;
  cursor: not-allowed;
}

.form-group textarea {
  font-family: monospace;
  font-size: 12px;
}

.form-group .hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

.form-group input[type="checkbox"] {
  width: auto;
  margin-right: 8px;
}

/* 匯入 Modal 樣式 */
.import-info {
  background: #f9fafb;
  padding: 20px;
  border-radius: 6px;
  margin-bottom: 20px;
}

.import-info h4 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #374151;
}

.format-table {
  width: 100%;
  border-collapse: collapse;
  margin: 15px 0;
  font-size: 12px;
}

.format-table th,
.format-table td {
  border: 1px solid #d1d5db;
  padding: 8px;
  text-align: left;
}

.format-table th {
  background: #e5e7eb;
  font-weight: 600;
}

.format-table td {
  background: white;
  font-family: monospace;
}

.import-notes {
  background: #fff3cd;
  border-left: 4px solid #ffc107;
  padding: 15px;
  margin: 15px 0;
}

.import-notes p {
  margin: 0 0 10px 0;
  font-weight: 600;
}

.import-notes ul {
  margin: 0;
  padding-left: 20px;
}

.import-notes li {
  margin: 5px 0;
  font-size: 13px;
}

.file-input {
  width: 100%;
  padding: 10px;
  border: 2px dashed #d1d5db;
  border-radius: 6px;
  background: #f9fafb;
  cursor: pointer;
  transition: all 0.2s;
}

.file-input:hover {
  border-color: #667eea;
  background: #f0f9ff;
}

.file-preview {
  background: #e0e7ff;
  border-left: 4px solid #667eea;
  padding: 15px;
  border-radius: 4px;
  margin-top: 15px;
}

.file-preview p {
  margin: 5px 0;
  font-size: 14px;
}

.import-progress {
  margin-top: 20px;
  padding: 15px;
  background: #f0f9ff;
  border-radius: 6px;
}

.import-result {
  margin-top: 10px;
}

.success-msg {
  color: #059669;
  font-weight: 600;
}

.error-msg {
  color: #dc2626;
  font-weight: 600;
}

.btn-success {
  background: #10b981;
  color: white;
}

.btn-success:hover {
  background: #059669;
}
</style>
