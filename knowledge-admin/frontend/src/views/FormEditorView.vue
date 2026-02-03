<template>
  <div class="form-editor">
    <div class="editor-header">
      <h2>{{ isNew ? '新增表單' : '編輯表單' }}</h2>
      <div class="header-actions">
        <button @click="$router.back()" class="btn-secondary">← 返回</button>
        <button @click="saveForm" class="btn-primary" :disabled="saving">
          {{ saving ? '儲存中...' : '儲存表單' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading">載入中...</div>

    <div v-else class="editor-container">
      <!-- 左側：基本設定 -->
      <div class="editor-sidebar">
        <div class="section">
          <h3>基本資訊</h3>

          <div class="form-group">
            <label>表單ID * <small>(唯一識別碼，建立後不可修改)</small></label>
            <input
              v-model="formData.form_id"
              :disabled="!isNew"
              required
              placeholder="例如：customer_service"
              pattern="[a-z_]+"
              title="只能使用小寫英文和底線"
            />
          </div>

          <div class="form-group">
            <label>表單名稱 *</label>
            <input v-model="formData.form_name" required placeholder="例如：客服申請表" />
          </div>

          <div class="form-group">
            <label>描述</label>
            <textarea v-model="formData.description" rows="3" placeholder="表單用途說明..."></textarea>
          </div>

          <div class="form-group">
            <label>引導語</label>
            <textarea v-model="formData.default_intro" rows="3" placeholder="觸發表單時顯示的引導訊息..."></textarea>
          </div>

          <div class="form-group">
            <label>業者</label>
            <select v-model.number="formData.vendor_id">
              <option :value="null">全局表單</option>
              <option :value="1">業者 1</option>
            </select>
          </div>

          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_active" />
              啟用表單
            </label>
          </div>
        </div>

        <!-- 完成後動作 -->
        <div class="section">
          <h3>完成後動作</h3>
          <p class="hint">使用者填完表單後，系統要執行什麼動作？</p>

          <div class="form-group">
            <label>動作類型 *</label>
            <select v-model="formData.on_complete_action">
              <option value="show_knowledge">僅顯示完成訊息</option>
              <option value="call_api">調用 API（表單數據會傳給 API）</option>
              <option value="both">顯示完成訊息 + 調用 API</option>
            </select>
            <small class="form-hint">
              • <strong>僅顯示完成訊息</strong>：適合一般資料收集<br>
              • <strong>調用 API</strong>：將表單數據傳送到外部系統<br>
              • <strong>兩者都做</strong>：同時顯示完成訊息並調用 API
            </small>
          </div>

          <!-- API 配置（當選擇 call_api 或 both 時顯示） -->
          <div v-if="formData.on_complete_action === 'call_api' || formData.on_complete_action === 'both'" class="api-config">
            <h4 style="margin-top: 1rem; margin-bottom: 0.5rem;">API 配置</h4>

            <div class="form-group">
              <label>HTTP 方法 *</label>
              <select v-model="formData.api_config.method">
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
                <option value="PATCH">PATCH</option>
                <option value="GET">GET</option>
              </select>
            </div>

            <div class="form-group">
              <label>API Endpoint * <small>(完整的 URL)</small></label>
              <input
                v-model="formData.api_config.endpoint"
                type="url"
                placeholder="https://api.example.com/submit"
                required
              />
              <small class="form-hint">
                例如：https://your-domain.com/api/forms/submit
              </small>
            </div>

            <div class="form-group">
              <label>Headers（選填）<small>(JSON 格式)</small></label>
              <textarea
                v-model="formData.api_config.headers"
                rows="3"
                placeholder='{"Authorization": "Bearer YOUR_TOKEN"}'
              ></textarea>
              <small class="form-hint">
                如需認證，可在此設定 Authorization header
              </small>
            </div>

            <div class="form-group">
              <label>額外參數（選填）<small>(JSON 格式)</small></label>
              <textarea
                v-model="formData.api_config.params"
                rows="3"
                placeholder='{"source": "chatbot", "version": "1.0"}'
              ></textarea>
              <small class="form-hint">
                這些參數會與表單數據一起傳送給 API
              </small>
            </div>
          </div>
        </div>

        <!-- 欄位模板 -->
        <div class="section">
          <h3>新增欄位</h3>
          <div class="field-templates">
            <button @click="addField('text')" class="template-btn">單行文字</button>
            <button @click="addField('textarea')" class="template-btn">多行文字</button>
            <button @click="addField('select')" class="template-btn">單選</button>
            <button @click="addField('number')" class="template-btn">數字</button>
            <button @click="addField('email')" class="template-btn">Email</button>
            <button @click="addField('date')" class="template-btn">日期</button>
          </div>
        </div>
      </div>

      <!-- 右側：欄位編輯 -->
      <div class="editor-main">
        <div class="section">
          <div class="section-header">
            <h3>📋 表單欄位 ({{ formData.fields.length }})</h3>
            <small v-if="formData.fields.length === 0" class="hint">請從左側新增欄位</small>
          </div>

          <div v-if="formData.fields.length === 0" class="empty-fields">
            <p>👈 點擊左側按鈕新增表單欄位</p>
          </div>

          <draggable
            v-model="formData.fields"
            item-key="key"
            handle=".drag-handle"
            class="fields-list"
          >
            <template #item="{ element: field, index }">
              <div class="field-editor" :class="{ 'editing': editingIndex === index }">
                <div class="field-toolbar">
                  <span class="drag-handle">⋮⋮</span>
                  <span class="field-number">{{ index + 1 }}</span>
                  <span class="field-title">
                    <strong>{{ field.field_label || '(未命名)' }}</strong>
                    <code>{{ field.field_name }}</code>
                    <span class="badge" :class="'type-' + field.field_type">{{ field.field_type }}</span>
                  </span>
                  <div class="field-actions">
                    <button @click="toggleEdit(index)" class="btn-sm">
                      {{ editingIndex === index ? '收合' : '展開' }}
                    </button>
                    <button @click="moveField(index, -1)" :disabled="index === 0" class="btn-sm">↑</button>
                    <button @click="moveField(index, 1)" :disabled="index === formData.fields.length - 1" class="btn-sm">↓</button>
                    <button @click="duplicateField(index)" class="btn-sm">複製</button>
                    <button @click="deleteField(index)" class="btn-sm btn-delete">刪除</button>
                  </div>
                </div>

                <div v-if="editingIndex === index" class="field-details">
                  <div class="form-row">
                    <div class="form-group">
                      <label>欄位名稱 (英文) *</label>
                      <input
                        v-model="field.field_name"
                        required
                        pattern="[a-z_]+"
                        placeholder="例如：phone"
                        title="只能使用小寫英文和底線"
                      />
                    </div>
                    <div class="form-group">
                      <label>欄位標籤 (中文) *</label>
                      <input v-model="field.field_label" required placeholder="例如：聯絡電話" />
                    </div>
                  </div>

                  <div class="form-group">
                    <label>提示訊息 *</label>
                    <textarea
                      v-model="field.prompt"
                      required
                      rows="2"
                      placeholder="詢問用戶的訊息，例如：請提供您的聯絡電話"
                    ></textarea>
                  </div>

                  <div class="form-row">
                    <div class="form-group">
                      <label>欄位類型 *</label>
                      <select v-model="field.field_type" required>
                        <option value="text">text - 單行文字</option>
                        <option value="textarea">textarea - 多行文字</option>
                        <option value="select">select - 單選</option>
                        <option value="multiselect">multiselect - 多選</option>
                        <option value="number">number - 數字</option>
                        <option value="email">email - Email</option>
                        <option value="date">date - 日期</option>
                      </select>
                    </div>
                    <div class="form-group">
                      <label>驗證類型</label>
                      <select v-model="field.validation_type">
                        <option value="">無驗證</option>
                        <option value="taiwan_name">taiwan_name - 台灣姓名</option>
                        <option value="taiwan_id">taiwan_id - 身分證字號</option>
                        <option value="phone">phone - 電話號碼</option>
                        <option value="email">email - Email 格式</option>
                        <option value="address">address - 地址</option>
                      </select>
                    </div>
                  </div>

                  <div class="form-row">
                    <div class="form-group">
                      <label>
                        <input type="checkbox" v-model="field.required" />
                        必填欄位
                      </label>
                    </div>
                    <div class="form-group" v-if="field.field_type === 'text' || field.field_type === 'textarea'">
                      <label>最大長度</label>
                      <input v-model.number="field.max_length" type="number" min="1" placeholder="例如：500" />
                    </div>
                    <div class="form-group" v-if="field.field_type === 'number'">
                      <label>最小值</label>
                      <input v-model.number="field.min" type="number" placeholder="例如：0" />
                    </div>
                    <div class="form-group" v-if="field.field_type === 'number'">
                      <label>最大值</label>
                      <input v-model.number="field.max" type="number" placeholder="例如：100" />
                    </div>
                  </div>

                  <!-- 選項設定（select/multiselect） -->
                  <div v-if="field.field_type === 'select' || field.field_type === 'multiselect'" class="form-group">
                    <label>選項 * <small>(每行一個選項)</small></label>
                    <textarea
                      v-model="field._optionsText"
                      rows="4"
                      placeholder="選項1&#10;選項2&#10;選項3"
                      @input="updateOptionsArray(field)"
                    ></textarea>
                    <small class="hint">當前選項：{{ field.options?.length || 0 }} 個</small>
                  </div>
                </div>
              </div>
            </template>
          </draggable>
        </div>

        <!-- 預覽 -->
        <div class="section" v-if="formData.fields.length > 0">
          <h3>👁️ 表單預覽</h3>
          <div class="form-preview">
            <div class="preview-intro" v-if="formData.default_intro">
              <p>{{ formData.default_intro }}</p>
            </div>
            <h4>📝 {{ formData.form_name || '(未命名表單)' }}</h4>
            <div v-for="(field, index) in formData.fields" :key="index" class="preview-field">
              <label>
                {{ field.field_label }}
                <span v-if="field.required" class="required">*</span>
              </label>
              <p class="preview-prompt">{{ field.prompt }}</p>
              <div class="preview-input">
                <input v-if="field.field_type === 'text' || field.field_type === 'email'" disabled placeholder="(範例輸入)" />
                <textarea v-else-if="field.field_type === 'textarea'" disabled rows="3" placeholder="(範例輸入)"></textarea>
                <select v-else-if="field.field_type === 'select'" disabled>
                  <option v-for="(opt, i) in field.options" :key="i">{{ opt }}</option>
                </select>
                <input v-else-if="field.field_type === 'number'" type="number" disabled placeholder="(範例輸入)" />
                <input v-else-if="field.field_type === 'date'" type="date" disabled />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import draggable from 'vuedraggable';
import api from '../utils/api';

export default {
  name: 'FormEditorView',
  components: {
    draggable
  },
  setup() {
    const router = useRouter();
    const route = useRoute();
    const loading = ref(false);
    const saving = ref(false);
    const editingIndex = ref(null);

    const formId = computed(() => route.params.formId);
    const isNew = computed(() => {
      const pathIsNew = route.path === '/forms/new' || route.path.startsWith('/forms/new/');
      const paramIsNew = formId.value === 'new';
      return pathIsNew || paramIsNew;
    });

    const formData = ref({
      form_id: '',
      form_name: '',
      description: '',
      default_intro: '',
      vendor_id: null,
      is_active: true,
      on_complete_action: 'show_knowledge',  // 完成後動作
      api_config: {  // API 配置
        method: 'POST',
        endpoint: '',
        headers: '{}',  // 使用字符串以便在 textarea 中顯示
        params: '{}'    // 使用字符串以便在 textarea 中顯示
      },
      fields: []
    });

    // 載入表單（編輯模式）
    const loadForm = async () => {
      console.log('[FormEditor] loadForm called', {
        path: route.path,
        formId: formId.value,
        isNew: isNew.value
      });

      if (isNew.value) {
        console.log('[FormEditor] 新建模式，跳過載入');
        return;
      }

      loading.value = true;
      try {
        const data = await api.get(`/rag-api/v1/forms/${formId.value}`);

        // 處理 API 配置：將 JSON 對象轉換為字符串以便在 textarea 中顯示
        let processedApiConfig = {
          method: 'POST',
          endpoint: '',
          headers: '{}',
          params: '{}'
        };

        if (data.api_config) {
          processedApiConfig = {
            method: data.api_config.method || 'POST',
            endpoint: data.api_config.endpoint || '',
            // 將對象轉換為格式化的 JSON 字符串
            headers: typeof data.api_config.headers === 'object'
              ? JSON.stringify(data.api_config.headers, null, 2)
              : (data.api_config.headers || '{}'),
            params: typeof data.api_config.params === 'object'
              ? JSON.stringify(data.api_config.params, null, 2)
              : (data.api_config.params || '{}')
          };
        }

        formData.value = {
          form_id: data.form_id,
          form_name: data.form_name,
          description: data.description || '',
          default_intro: data.default_intro || '',
          vendor_id: data.vendor_id,
          is_active: data.is_active,
          on_complete_action: data.on_complete_action || 'show_knowledge',
          api_config: processedApiConfig,
          fields: data.fields.map((f, index) => ({
            ...f,
            key: `loaded_${index}_${Date.now()}`,  // 添加穩定的內部 ID
            _optionsText: f.options ? f.options.join('\n') : ''
          }))
        };
      } catch (error) {
        console.error('載入表單失敗:', error);
        alert('載入表單失敗: ' + error.message);
        router.back();
      } finally {
        loading.value = false;
      }
    };

    // 新增欄位
    const addField = (type) => {
      const timestamp = Date.now();
      const field = {
        key: `temp_${timestamp}`,  // 穩定的內部 ID，用於 Vue key
        field_name: `field_${timestamp}`,
        field_label: '',
        field_type: type,
        prompt: '',
        required: true,
        validation_type: type === 'email' ? 'email' : '',
        _optionsText: ''
      };

      if (type === 'select' || type === 'multiselect') {
        field.options = [];
        field._optionsText = '選項1\n選項2\n選項3';
        field.options = ['選項1', '選項2', '選項3'];
      }

      formData.value.fields.push(field);
      editingIndex.value = formData.value.fields.length - 1;
    };

    // 更新選項陣列
    const updateOptionsArray = (field) => {
      if (!field._optionsText) {
        field.options = [];
        return;
      }
      field.options = field._optionsText
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0);
    };

    // 展開/收合欄位
    const toggleEdit = (index) => {
      editingIndex.value = editingIndex.value === index ? null : index;
    };

    // 移動欄位
    const moveField = (index, direction) => {
      const newIndex = index + direction;
      if (newIndex < 0 || newIndex >= formData.value.fields.length) return;

      const fields = [...formData.value.fields];
      [fields[index], fields[newIndex]] = [fields[newIndex], fields[index]];
      formData.value.fields = fields;

      if (editingIndex.value === index) {
        editingIndex.value = newIndex;
      } else if (editingIndex.value === newIndex) {
        editingIndex.value = index;
      }
    };

    // 複製欄位
    const duplicateField = (index) => {
      const field = { ...formData.value.fields[index] };
      field.key = `copy_${Date.now()}`;  // 生成新的 key
      field.field_name = `${field.field_name}_copy`;
      formData.value.fields.splice(index + 1, 0, field);
    };

    // 刪除欄位
    const deleteField = (index) => {
      if (!confirm('確定要刪除此欄位嗎？')) return;
      formData.value.fields.splice(index, 1);
      if (editingIndex.value === index) {
        editingIndex.value = null;
      }
    };

    // 儲存表單
    const saveForm = async () => {
      // 驗證
      if (!formData.value.form_id || !formData.value.form_name) {
        alert('請填寫必填欄位');
        return;
      }

      if (formData.value.fields.length === 0) {
        alert('表單至少需要一個欄位');
        return;
      }

      // 檢查欄位名稱不重複
      const fieldNames = formData.value.fields.map(f => f.field_name);
      const duplicates = fieldNames.filter((name, index) => fieldNames.indexOf(name) !== index);
      if (duplicates.length > 0) {
        alert(`欄位名稱重複: ${duplicates.join(', ')}`);
        return;
      }

      // 檢查必填欄位
      for (const field of formData.value.fields) {
        // 檢查欄位名稱
        if (!field.field_name || !field.field_name.trim()) {
          alert(`請填寫所有欄位的「欄位名稱」`);
          return;
        }
        // 檢查欄位標籤
        if (!field.field_label || !field.field_label.trim()) {
          alert(`欄位「${field.field_name}」缺少「欄位標籤」`);
          return;
        }
        // 檢查提示訊息
        if (!field.prompt || !field.prompt.trim()) {
          alert(`欄位「${field.field_label}」缺少「提示訊息」\n\n提示訊息用於告訴用戶應該填寫什麼內容，例如：「請輸入您的姓名」`);
          return;
        }
        // 檢查 select 類型有選項
        if ((field.field_type === 'select' || field.field_type === 'multiselect') && (!field.options || field.options.length === 0)) {
          alert(`欄位「${field.field_label}」的類型為 ${field.field_type}，必須提供選項`);
          return;
        }
      }

      // 處理 API 配置（解析 JSON 字段）
      let processedApiConfig = null;
      if (formData.value.on_complete_action === 'call_api' || formData.value.on_complete_action === 'both') {
        try {
          // 解析 headers（如果有的話）
          let parsedHeaders = {};
          if (formData.value.api_config?.headers && typeof formData.value.api_config.headers === 'string' && formData.value.api_config.headers.trim()) {
            parsedHeaders = JSON.parse(formData.value.api_config.headers);
          } else if (typeof formData.value.api_config?.headers === 'object') {
            parsedHeaders = formData.value.api_config.headers;
          }

          // 解析 params（如果有的話）
          let parsedParams = {};
          if (formData.value.api_config?.params && typeof formData.value.api_config.params === 'string' && formData.value.api_config.params.trim()) {
            parsedParams = JSON.parse(formData.value.api_config.params);
          } else if (typeof formData.value.api_config?.params === 'object') {
            parsedParams = formData.value.api_config.params;
          }

          processedApiConfig = {
            method: formData.value.api_config?.method || 'POST',
            endpoint: formData.value.api_config?.endpoint || '',
            headers: parsedHeaders,
            params: parsedParams
          };

          // 驗證 endpoint 不能為空
          if (!processedApiConfig.endpoint || !processedApiConfig.endpoint.trim()) {
            alert('當選擇「呼叫 API」或「兩者都要」時，API Endpoint 不能為空');
            return;
          }
        } catch (error) {
          alert('API 配置的 JSON 格式不正確，請檢查 Headers 和 Params\n\n錯誤訊息: ' + error.message);
          return;
        }
      }

      saving.value = true;
      try {
        // 準備資料（移除內部屬性）
        const data = {
          ...formData.value,
          api_config: processedApiConfig,  // 使用處理過的 API 配置
          fields: formData.value.fields.map(f => {
            const { _optionsText, key, ...field } = f;  // 移除 key 和 _optionsText
            // 移除空值（但保留必填欄位，即使是空字串）
            const requiredFields = ['field_name', 'field_label', 'field_type', 'prompt', 'required'];
            Object.keys(field).forEach(key => {
              // 如果是必填欄位，即使是空字串也保留
              if (requiredFields.includes(key)) {
                return;
              }
              // 移除 null, undefined, 或空字串的選填欄位
              if (field[key] === '' || field[key] === null || field[key] === undefined) {
                delete field[key];
              }
            });
            return field;
          })
        };

        console.log('[Debug] 準備發送的數據:', JSON.stringify(data, null, 2));

        if (isNew.value) {
          console.log('[Debug] 執行 POST /rag-api/v1/forms');
          await api.post('/rag-api/v1/forms', data);
          alert('表單建立成功！');
        } else {
          const { form_id, ...updateData } = data;
          console.log('[Debug] 執行 PUT /rag-api/v1/forms/' + formId.value);
          console.log('[Debug] 更新數據:', JSON.stringify(updateData, null, 2));
          await api.put(`/rag-api/v1/forms/${formId.value}`, updateData);
          alert('表單更新成功！');
        }

        router.push('/forms');
      } catch (error) {
        console.error('儲存失敗 - 完整錯誤:', error);
        console.error('Error message:', error.message);
        console.error('Error response:', error.response);
        console.error('Error response data:', error.response?.data);

        let errorMessage = '儲存失敗';

        if (error.response?.data) {
          // 如果後端返回的是字符串
          if (typeof error.response.data === 'string') {
            errorMessage += ': ' + error.response.data;
          }
          // 如果後端返回的是對象
          else if (error.response.data.detail) {
            errorMessage += ': ' + error.response.data.detail;
          }
          // 如果有其他錯誤信息
          else if (error.response.data.message) {
            errorMessage += ': ' + error.response.data.message;
          }
          // 否則顯示完整的 data
          else {
            errorMessage += ': ' + JSON.stringify(error.response.data);
          }
        } else if (error.message) {
          errorMessage += ': ' + error.message;
        }

        alert(errorMessage);
      } finally {
        saving.value = false;
      }
    };

    onMounted(() => {
      console.log('[FormEditor] onMounted', {
        path: route.path,
        formId: formId.value,
        isNew: isNew.value,
        routeName: route.name
      });

      // 只有在編輯模式才載入表單
      if (route.name !== 'FormNew' && formId.value && formId.value !== 'new') {
        loadForm();
      } else {
        console.log('[FormEditor] 跳過載入 - 新建模式');
      }
    });

    return {
      loading,
      saving,
      isNew,
      formData,
      editingIndex,
      addField,
      updateOptionsArray,
      toggleEdit,
      moveField,
      duplicateField,
      deleteField,
      saveForm
    };
  }
};
</script>

<style scoped>
.form-editor {
  max-width: 1400px;
  margin: 0 auto;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 2px solid #eee;
}

.editor-header h2 {
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.editor-container {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 20px;
}

.editor-sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 20px;
}

.section h3 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #333;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.hint {
  color: #999;
  font-size: 0.9em;
}

/* 欄位模板按鈕 */
.field-templates {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.template-btn {
  padding: 10px;
  background: #f8f9fa;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.template-btn:hover {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

/* 空白狀態 */
.empty-fields {
  text-align: center;
  padding: 60px 20px;
  color: #999;
  background: #f8f9fa;
  border-radius: 6px;
  font-size: 16px;
}

/* 欄位列表 */
.fields-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.field-editor {
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  transition: all 0.2s;
}

.field-editor.editing {
  border-color: #007bff;
  box-shadow: 0 0 0 3px rgba(0,123,255,0.1);
}

.field-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 15px;
  background: #f8f9fa;
  border-bottom: 1px solid #ddd;
}

.drag-handle {
  cursor: move;
  color: #999;
  font-size: 16px;
  user-select: none;
}

.field-number {
  background: #007bff;
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
}

.field-title {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.field-title code {
  background: #e9ecef;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.85em;
}

.field-actions {
  display: flex;
  gap: 5px;
}

.field-details {
  padding: 20px;
}

/* 預覽 */
.form-preview {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 6px;
}

.preview-intro {
  background: #e7f3ff;
  padding: 15px;
  border-left: 3px solid #007bff;
  margin-bottom: 20px;
  border-radius: 4px;
}

.preview-field {
  margin-bottom: 20px;
  padding: 15px;
  background: white;
  border-radius: 6px;
  border: 1px solid #ddd;
}

.preview-field label {
  font-weight: bold;
  display: block;
  margin-bottom: 5px;
}

.preview-prompt {
  color: #666;
  font-size: 0.9em;
  margin: 5px 0 10px 0;
}

.preview-input input,
.preview-input textarea,
.preview-input select {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: #fafafa;
}

.required {
  color: #dc3545;
}
</style>
