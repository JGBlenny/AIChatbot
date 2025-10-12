<template>
  <div>
    <h2>⚙️ 業務範圍配置</h2>

    <div v-if="loading" class="loading"><p>載入中...</p></div>

    <div v-else class="scopes-container">
      <div v-for="scope in scopes" :key="scope.id" class="scope-card">
        <div class="scope-header">
          <h3>{{ scope.display_name }}</h3>
          <span class="badge scope-type-badge">{{ scope.scope_type }}</span>
        </div>

        <div class="scope-body">
          <div class="info-row">
            <span class="label">範圍名稱:</span>
            <span><code>{{ scope.scope_name }}</code></span>
          </div>

          <div class="info-row">
            <span class="label">範圍類型:</span>
            <span><code>{{ scope.scope_type }}</code></span>
          </div>

          <div class="info-section">
            <span class="label">業務描述:</span>
            <p>{{ scope.business_description }}</p>
          </div>

          <div class="info-section">
            <span class="label">範例問題:</span>
            <ul>
              <li v-for="(q, i) in scope.example_questions" :key="i">{{ q }}</li>
            </ul>
          </div>

          <div class="info-section">
            <span class="label">範例意圖:</span>
            <div class="keywords">
              <span v-for="(intent, i) in scope.example_intents" :key="i" class="badge">{{ intent }}</span>
            </div>
          </div>

          <div v-if="scope.relevance_prompt" class="info-section">
            <span class="label">自訂判斷 Prompt:</span>
            <pre>{{ scope.relevance_prompt }}</pre>
          </div>

          <div class="info-row">
            <span class="label">最後更新:</span>
            <span>{{ formatDate(scope.updated_at) }}</span>
            <span v-if="scope.updated_by"> by {{ scope.updated_by }}</span>
          </div>
        </div>

        <div class="scope-actions">
          <button @click="editScope(scope)" class="btn-primary">✏️ 編輯配置</button>
        </div>
      </div>
    </div>

    <!-- 編輯 Modal -->
    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content modal-large" @click.stop>
        <h2>✏️ 編輯業務範圍配置</h2>

        <form @submit.prevent="saveScope">
          <div class="form-group">
            <label>顯示名稱 *</label>
            <input v-model="formData.display_name" required />
          </div>

          <div class="form-group">
            <label>業務描述 *</label>
            <textarea v-model="formData.business_description" rows="3" required></textarea>
          </div>

          <div class="form-group">
            <label>範例問題（一行一個）</label>
            <textarea v-model="exampleQuestionsString" rows="4" placeholder="如何退租？&#10;押金什麼時候退還？"></textarea>
          </div>

          <div class="form-group">
            <label>範例意圖（用逗號分隔）</label>
            <input v-model="exampleIntentsString" placeholder="退租流程, 押金處理, 設備報修" />
          </div>

          <div class="form-group">
            <label>自訂 OpenAI 判斷 Prompt（可選）</label>
            <textarea v-model="formData.relevance_prompt" rows="5" placeholder="留空則使用預設prompt"></textarea>
            <small style="color: #909399;">提示：這個 prompt 將用於 OpenAI 判斷問題是否屬於業務範圍</small>
          </div>

          <div class="form-actions">
            <button type="submit" class="btn-primary" :disabled="saving">
              {{ saving ? '⏳ 儲存中...' : '💾 儲存' }}
            </button>
            <button type="button" @click="closeModal" class="btn-secondary">❌ 取消</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

const RAG_API = 'http://localhost:8100/api/v1';

export default {
  name: 'BusinessScopeView',
  data() {
    return {
      scopes: [],
      loading: false,
      showModal: false,
      editingScope: null,
      saving: false,
      formData: {
        display_name: '',
        business_description: '',
        example_questions: [],
        example_intents: [],
        relevance_prompt: '',
        updated_by: 'admin'
      },
      exampleQuestionsString: '',
      exampleIntentsString: ''
    };
  },
  mounted() {
    this.loadScopes();
  },
  methods: {
    async loadScopes() {
      this.loading = true;
      try {
        const response = await axios.get(`${RAG_API}/business-scope`);
        this.scopes = response.data.scopes;
      } catch (error) {
        console.error('載入失敗', error);
        alert('載入失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },

    editScope(scope) {
      this.editingScope = scope;
      this.formData = {
        display_name: scope.display_name,
        business_description: scope.business_description,
        example_questions: scope.example_questions || [],
        example_intents: scope.example_intents || [],
        relevance_prompt: scope.relevance_prompt || '',
        updated_by: 'admin'
      };
      this.exampleQuestionsString = (scope.example_questions || []).join('\n');
      this.exampleIntentsString = (scope.example_intents || []).join(', ');
      this.showModal = true;
    },

    async saveScope() {
      this.saving = true;

      try {
        // 處理範例問題
        this.formData.example_questions = this.exampleQuestionsString
          .split('\n')
          .map(q => q.trim())
          .filter(q => q);

        // 處理範例意圖
        this.formData.example_intents = this.exampleIntentsString
          .split(',')
          .map(i => i.trim())
          .filter(i => i);

        await axios.put(
          `${RAG_API}/business-scope/${this.editingScope.scope_name}`,
          this.formData
        );

        alert('✅ 業務範圍配置已更新！');
        this.closeModal();
        this.loadScopes();
      } catch (error) {
        console.error('儲存失敗', error);
        alert('儲存失敗：' + (error.response?.data?.detail || error.message));
      } finally {
        this.saving = false;
      }
    },

    closeModal() {
      this.showModal = false;
      this.editingScope = null;
    },

    formatDate(dateStr) {
      if (!dateStr) return '-';
      const date = new Date(dateStr);
      return date.toLocaleString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    }
  }
};
</script>

<style scoped>
/* 資訊橫幅 */
.info-banner {
  display: flex;
  gap: 15px;
  background: linear-gradient(135deg, #e0f2fe 0%, #dbeafe 100%);
  border: 2px solid #3b82f6;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 25px;
  align-items: flex-start;
}

.info-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.info-content {
  flex: 1;
}

.info-content strong {
  color: #1e40af;
  display: block;
  margin-bottom: 8px;
  font-size: 16px;
}

.info-content p {
  margin: 6px 0;
  color: #1e3a8a;
  line-height: 1.6;
  font-size: 14px;
}

.info-content code {
  background: white;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
  color: #7c3aed;
  font-weight: bold;
}

.info-note {
  display: flex;
  gap: 12px;
  background: white;
  border: 1px solid #93c5fd;
  border-radius: 6px;
  padding: 15px;
  margin-top: 12px;
  align-items: flex-start;
}

.note-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.info-note p {
  margin: 4px 0;
  font-size: 13px;
}

.info-note ul {
  margin: 8px 0 0 0;
  padding-left: 20px;
}

.info-note li {
  margin: 4px 0;
  font-size: 13px;
  line-height: 1.5;
}

.scopes-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(550px, 1fr));
  gap: 25px;
}

.scope-card {
  background: white;
  border: 2px solid #e4e7ed;
  border-radius: 12px;
  padding: 24px;
  transition: all 0.3s;
}

.scope-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.scope-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 2px solid #e4e7ed;
}

.scope-header h3 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.scope-type-badge {
  background: #909399;
  color: white;
  font-weight: 600;
  padding: 6px 12px;
  font-size: 12px;
  text-transform: uppercase;
}

.scope-body {
  margin-bottom: 20px;
}

.info-row {
  margin-bottom: 12px;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 6px;
  font-size: 14px;
}

.info-row .label {
  font-weight: 600;
  color: #409EFF;
  margin-right: 8px;
}

.info-row code {
  background: white;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid #ddd;
  font-size: 13px;
}

.info-section {
  margin-bottom: 20px;
  padding: 15px;
  background: #fafbfc;
  border-left: 4px solid #409EFF;
  border-radius: 6px;
}

.info-section .label {
  font-weight: 600;
  color: #409EFF;
  display: block;
  margin-bottom: 10px;
  font-size: 15px;
}

.info-section p {
  margin: 0;
  color: #303133;
  line-height: 1.7;
  padding: 8px 0;
}

.info-section ul {
  margin: 0;
  padding-left: 20px;
}

.info-section ul li {
  color: #606266;
  margin-bottom: 8px;
  line-height: 1.6;
}

.info-section pre {
  background: #f0f2f5;
  padding: 12px;
  border-radius: 6px;
  font-size: 13px;
  overflow-x: auto;
  margin: 8px 0 0 0;
  border: 1px solid #dcdfe6;
  color: #303133;
}

.keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
}

.keywords .badge {
  background: #409EFF;
  color: white;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
}

.scope-actions {
  display: flex;
  gap: 10px;
  padding-top: 15px;
  border-top: 1px solid #e4e7ed;
}

.modal-large {
  max-width: 800px;
}
</style>
