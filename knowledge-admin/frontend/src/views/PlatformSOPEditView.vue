<template>
  <div class="platform-sop-edit-view">
    <div class="page-header">
      <button @click="$router.back()" class="btn btn-back">
        ← 返回
      </button>
      <div class="header-content">
        <h1>{{ businessTypeTitle }}</h1>
        <p class="subtitle">{{ businessTypeDescription }}</p>
      </div>
      <div class="header-actions">
        <button v-if="businessType !== null" @click="showCopyModalHandler" class="btn btn-info">
          📋 從通用範本複製
        </button>
        <button @click="showCategoryModal = true" class="btn btn-secondary">
          📁 新增分類
        </button>
        <button @click="openNewTemplateModal" class="btn btn-primary">
          ➕ 新增 SOP 項目
        </button>
      </div>
    </div>

    <!-- 載入中 -->
    <div v-if="loading" class="loading">
      <span class="spinner"></span> 載入中...
    </div>

    <!-- SOP 範本列表（3 層結構：分類 → 群組 → 範本） -->
    <div v-else class="sop-categories">
      <div
        v-for="category in filteredCategories"
        :key="category.id"
        class="category-section"
      >
        <!-- 第 1 層：分類 -->
        <div class="category-header-collapsible">
          <span class="collapse-icon" @click="toggleCategory(category.id)">
            {{ isCategoryExpanded(category.id) ? '▼' : '▶' }}
          </span>
          <h2 @click="toggleCategory(category.id)">{{ category.category_name }}</h2>
          <span class="category-count" @click="toggleCategory(category.id)">
            {{ getTemplatesByCategory(category.id).length }} 個項目
          </span>
          <!-- 刪除按鈕：所有分類都顯示 -->
          <button
            @click.stop="deleteCategory(category.id, category.category_name)"
            class="btn btn-sm btn-danger category-delete-btn"
            :title="getCategoryTotalTemplates(category.id) > 0 ? '刪除分類及其下所有範本' : '刪除空分類'"
          >
            🗑️ 刪除
          </button>
        </div>

        <!-- 第 2 層：群組列表 -->
        <div v-show="isCategoryExpanded(category.id)" class="groups-list">
          <div
            v-for="group in getGroupsByCategory(category.id)"
            :key="group.id"
            class="group-section"
          >
            <div class="group-header-collapsible">
              <span class="collapse-icon" @click="toggleGroup(group.id)">
                {{ isGroupExpanded(group.id) ? '▼' : '▶' }}
              </span>
              <h3 @click="toggleGroup(group.id)">{{ group.group_name }}</h3>
              <span class="group-count" @click="toggleGroup(group.id)">
                {{ getTemplatesByGroup(group.id).length }} 個項目
              </span>
              <button
                @click.stop="deleteGroup(group.id, group.group_name, category.id)"
                class="btn btn-sm btn-danger group-delete-btn"
                :title="getTemplatesByGroup(group.id).length > 0 ? '刪除群組（可選擇移動模板）' : '刪除空群組'"
              >
                🗑️ 刪除
              </button>
            </div>

            <!-- 第 3 層：範本列表 -->
            <div v-show="isGroupExpanded(group.id)" class="templates-list">
              <div
                v-for="template in getTemplatesByGroup(group.id)"
                :key="template.id"
                class="template-card"
              >
                <div class="template-header">
                  <span class="template-number">#{{ template.item_number }}</span>
                  <h4>{{ template.item_name }}</h4>
                  <span
                    v-for="intentId in (template.intent_ids || [])"
                    :key="intentId"
                    class="badge badge-intent"
                  >
                    🎯 {{ getIntentName(intentId) }}
                  </span>
                  <span class="badge badge-priority" :class="getPriorityClass(template.priority)">
                    優先級: {{ template.priority }}
                  </span>
                </div>

                <div class="template-content">
                  <div class="content-section">
                    <strong>範本內容:</strong>
                    <p>{{ template.content }}</p>
                  </div>

                  <div v-if="template.template_notes" class="content-section template-guide">
                    <strong>📝 範本說明:</strong>
                    <p>{{ template.template_notes }}</p>
                  </div>

                  <div v-if="template.customization_hint" class="content-section template-guide">
                    <strong>💡 自訂提示:</strong>
                    <p>{{ template.customization_hint }}</p>
                  </div>
                </div>

                <div class="template-actions">
                  <button @click="editTemplate(template)" class="btn btn-sm btn-secondary">
                    ✏️ 編輯
                  </button>
                  <button @click="viewTemplateUsage(template.id)" class="btn btn-sm btn-info">
                    👥 使用情況
                  </button>
                  <button @click="deleteTemplate(template.id)" class="btn btn-sm btn-danger">
                    🗑️ 刪除
                  </button>
                </div>
              </div>
            </div>

            <!-- 如果群組內沒有範本 -->
            <div v-show="isGroupExpanded(group.id)" v-if="getTemplatesByGroup(group.id).length === 0" class="no-templates-in-group">
              <p>此群組尚未建立任何 SOP 項目</p>
            </div>
          </div>

          <!-- 未分組的範本 -->
          <div v-if="getUngroupedTemplates(category.id).length > 0" class="group-section">
            <div class="group-header-collapsible ungrouped">
              <span class="collapse-icon" @click="toggleGroup('ungrouped_' + category.id)">
                {{ isGroupExpanded('ungrouped_' + category.id) ? '▼' : '▶' }}
              </span>
              <h3 @click="toggleGroup('ungrouped_' + category.id)">（未分組）</h3>
              <span class="group-count" @click="toggleGroup('ungrouped_' + category.id)">
                {{ getUngroupedTemplates(category.id).length }} 個項目
              </span>
            </div>

            <!-- 未分組的範本列表 -->
            <div v-show="isGroupExpanded('ungrouped_' + category.id)" class="templates-list">
              <div
                v-for="template in getUngroupedTemplates(category.id)"
                :key="template.id"
                class="template-card"
              >
                <div class="template-header">
                  <span class="template-number">#{{ template.item_number }}</span>
                  <h4>{{ template.item_name }}</h4>
                  <span
                    v-for="intentId in (template.intent_ids || [])"
                    :key="intentId"
                    class="badge badge-intent"
                  >
                    🎯 {{ getIntentName(intentId) }}
                  </span>
                  <span class="badge badge-priority" :class="getPriorityClass(template.priority)">
                    優先級: {{ template.priority }}
                  </span>
                </div>

                <div class="template-content">
                  <div class="content-section">
                    <strong>範本內容:</strong>
                    <p>{{ template.content }}</p>
                  </div>

                  <div v-if="template.template_notes" class="content-section template-guide">
                    <strong>📝 範本說明:</strong>
                    <p>{{ template.template_notes }}</p>
                  </div>

                  <div v-if="template.customization_hint" class="content-section template-guide">
                    <strong>💡 自訂提示:</strong>
                    <p>{{ template.customization_hint }}</p>
                  </div>
                </div>

                <div class="template-actions">
                  <button @click="editTemplate(template)" class="btn btn-sm btn-secondary">
                    ✏️ 編輯
                  </button>
                  <button @click="viewTemplateUsage(template.id)" class="btn btn-sm btn-info">
                    👥 使用情況
                  </button>
                  <button @click="deleteTemplate(template.id)" class="btn btn-sm btn-danger">
                    🗑️ 刪除
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 如果分類內沒有任何範本 -->
        <div v-show="isCategoryExpanded(category.id)" v-if="getTemplatesByCategory(category.id).length === 0" class="no-templates-in-category">
          <p>此分類尚未建立任何 SOP 項目</p>
          <button @click="openNewTemplateModalForCategory(category.id)" class="btn btn-sm btn-primary">
            ➕ 為此分類新增項目
          </button>
        </div>
      </div>

      <div v-if="filteredCategories.length === 0" class="no-templates">
        <p>📋 此業種尚未建立任何 SOP 項目</p>
        <div class="hint-box">
          <p><strong>建立方式：</strong></p>
          <ul>
            <li v-if="businessType !== null">方式一：點擊「📋 從通用範本複製」快速複製通用範本</li>
            <li>方式{{ businessType !== null ? '二' : '一' }}：點擊「📁 新增分類」建立分類，再點擊「➕ 新增 SOP 項目」逐一建立</li>
          </ul>
        </div>
      </div>
    </div>

    <!-- 新增/編輯範本 Modal -->
    <div v-if="showTemplateModal" class="modal-overlay" @click="showTemplateModal = false">
      <div class="modal-content modal-large" @click.stop>
        <h2>{{ editingTemplate ? '編輯 SOP 項目' : '新增 SOP 項目' }}</h2>
        <form @submit.prevent="saveTemplate">
          <!-- 基本資訊 -->
          <div class="form-section">
            <h3>基本資訊</h3>

            <div class="form-group">
              <label>所屬分類 *</label>
              <select v-model.number="templateForm.category_id" required class="form-control">
                <option :value="null">請選擇分類</option>
                <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                  {{ cat.category_name }}
                </option>
              </select>
            </div>

            <div class="form-group" v-if="templateForm.category_id">
              <label>
                所屬群組（說明）
                <button
                  type="button"
                  @click="showCreateGroupModal = true"
                  class="btn-inline btn-sm"
                  title="為此分類新增群組"
                >
                  ➕ 新增群組
                </button>
              </label>
              <select v-model.number="templateForm.group_id" class="form-control">
                <option :value="null">（未分組）</option>
                <option v-for="group in availableGroups" :key="group.id" :value="group.id">
                  {{ group.group_name }} ({{ group.template_count || 0 }} 個項目)
                </option>
              </select>
              <small class="form-hint">群組用於將同類型的 SOP 項目分組顯示（對應 Excel 的「說明」欄位）</small>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>項次編號 *</label>
                <input v-model.number="templateForm.item_number" type="number" min="1" required class="form-control" />
              </div>

              <div class="form-group">
                <label>優先級 (0-100)</label>
                <input v-model.number="templateForm.priority" type="number" min="0" max="100" class="form-control" />
              </div>
            </div>

            <div class="form-group">
              <label>項目名稱 *</label>
              <input v-model="templateForm.item_name" type="text" required class="form-control" />
            </div>

            <div class="form-group">
              <label>範本內容 *</label>
              <textarea v-model="templateForm.content" required class="form-control" rows="4"></textarea>
              <small class="form-hint">此內容將作為業者複製的基礎，業者複製後可自行編輯調整</small>
            </div>
          </div>

          <!-- 關聯設定 -->
          <div class="form-section">
            <h3>關聯設定</h3>

            <div class="form-group">
              <label>關聯意圖（可複選）</label>
              <div class="intent-checkboxes">
                <label v-for="intent in intents" :key="intent.id" class="checkbox-label">
                  <input
                    type="checkbox"
                    :value="intent.id"
                    v-model="templateForm.intent_ids"
                    class="checkbox-input"
                  />
                  <span class="checkbox-text">{{ intent.name }}</span>
                </label>
              </div>
              <p class="form-hint" v-if="templateForm.intent_ids.length === 0">未選擇任何意圖</p>
              <p class="form-hint" v-else>已選擇 {{ templateForm.intent_ids.length }} 個意圖</p>
            </div>
          </div>

          <!-- 範本引導 -->
          <div class="form-section">
            <h3>範本引導（幫助業者自訂）</h3>

            <div class="form-group">
              <label>範本說明</label>
              <textarea v-model="templateForm.template_notes" class="form-control" rows="2"></textarea>
              <small class="form-hint">解釋此 SOP 的目的和適用場景</small>
            </div>

            <div class="form-group">
              <label>自訂提示</label>
              <textarea v-model="templateForm.customization_hint" class="form-control" rows="2"></textarea>
              <small class="form-hint">建議業者如何根據自身情況調整內容</small>
            </div>
          </div>

          <!-- 流程配置 -->
          <div class="form-section flow-config-section">
            <h3>🔄 流程配置（進階）</h3>

            <div class="form-group">
              <label>觸發模式 *</label>
              <select v-model="templateForm.trigger_mode" @change="onTriggerModeChange" class="form-control">
                <option value="none">資訊型（僅回答 SOP 內容，無後續動作）</option>
                <option value="manual">排查型（等待用戶說出關鍵詞後觸發）</option>
                <option value="immediate">行動型（主動詢問用戶是否執行）</option>
                <!-- <option value="auto">自動執行型（立即執行後續動作）</option> ⚠️ 暫不實作 -->
              </select>
              <small class="form-hint">
                💡 <strong>資訊型</strong>：只顯示 SOP 內容<br>
                💡 <strong>排查型</strong>：用戶說出關鍵詞後才觸發（例如：「還是不行」→ 執行報修）<br>
                💡 <strong>行動型</strong>：主動詢問是否執行（例如：「需要立即報修嗎？」）
              </small>
            </div>

            <!-- manual 模式：觸發關鍵詞 -->
            <div v-if="templateForm.trigger_mode === 'manual'" class="form-group">
              <label>觸發關鍵詞 *</label>
              <KeywordsInput
                v-model="templateForm.trigger_keywords"
                placeholder="輸入關鍵詞後按 Enter 或逗號"
                hint="💡 用戶說出這些關鍵詞後，才會觸發後續動作。例如：「還是不行」、「需要維修」、「我要預約」"
                :max-keywords="10"
              />
            </div>

            <!-- immediate 模式：確認提示詞（可選） -->
            <div v-if="templateForm.trigger_mode === 'immediate'" class="form-group">
              <label>確認提示詞（選填）</label>
              <textarea
                v-model="templateForm.immediate_prompt"
                class="form-control"
                rows="3"
                placeholder="留空則使用系統預設提示詞"
              ></textarea>
              <small class="form-hint">
                💡 <strong>預設提示詞：</strong><br>
                💡 **需要安排處理嗎？**<br>
                • 回覆「要」或「需要」→ 立即填寫表單<br>
                • 回覆「不用」→ 繼續為您解答其他問題<br>
                <br>
                如需自訂（例如：改為「需要安排維修嗎？」），請在上方輸入。
              </small>
            </div>

            <div class="form-group">
              <label>後續動作 *</label>
              <select v-model="templateForm.next_action" @change="onNextActionChange" class="form-control">
                <option value="none">無（僅顯示 SOP 內容）</option>
                <option value="form_fill">觸發表單（引導用戶填寫表單）</option>
                <option value="api_call">調用 API（查詢或處理資料）</option>
                <option value="form_then_api">先填表單再調用 API（完整流程）</option>
              </select>
              <small class="form-hint">
                💡 <strong>無</strong>：只顯示 SOP 內容，不執行其他動作<br>
                💡 <strong>觸發表單</strong>：引導用戶填寫表單（例如：報修申請）<br>
                💡 <strong>調用 API</strong>：直接調用 API（例如：查詢帳單）<br>
                💡 <strong>先填表單再調用 API</strong>：表單完成後自動提交（例如：租屋申請）
              </small>
            </div>

            <!-- 後續提示詞 -->
            <div v-if="templateForm.next_action !== 'none'" class="form-group">
              <label>後續提示詞（可選）</label>
              <textarea
                v-model="templateForm.followup_prompt"
                class="form-control"
                rows="2"
                placeholder="例如：好的，我來協助您填寫表單"
              ></textarea>
              <small class="form-hint">💡 觸發後續動作時顯示的提示語（留空則使用預設提示）</small>
            </div>

            <!-- 表單選擇 -->
            <div v-if="['form_fill', 'form_then_api'].includes(templateForm.next_action)" class="form-group">
              <label>選擇表單 *</label>
              <select v-model="templateForm.next_form_id" class="form-control">
                <option :value="null">請選擇表單...</option>
                <option v-for="form in availableForms" :key="form.form_id" :value="form.form_id">
                  {{ form.form_name }} ({{ form.form_id }})
                </option>
              </select>
              <p v-if="templateForm.next_form_id" class="form-hint" style="color: #10b981;">
                ✅ 已關聯表單：{{ getFormName(templateForm.next_form_id) }}
              </p>
              <p v-else class="form-hint" style="color: #ef4444;">
                ⚠️ 請選擇表單，否則後續動作將無法執行
              </p>
            </div>

            <!-- API 配置 -->
            <div v-if="['api_call', 'form_then_api'].includes(templateForm.next_action)" class="form-group">
              <label>API 配置 *</label>

              <!-- 選擇器模式 -->
              <div v-if="!useCustomApiConfig">
                <select v-model="selectedApiEndpointId" @change="onApiEndpointChange" class="form-control">
                  <option value="">請選擇 API 端點...</option>
                  <option v-for="api in availableApiEndpoints" :key="api.endpoint_id" :value="api.endpoint_id">
                    {{ api.endpoint_icon || '🔌' }} {{ api.endpoint_name }} ({{ api.endpoint_id }})
                  </option>
                </select>

                <p v-if="selectedApiEndpointId" class="form-hint" style="color: #10b981; margin-top: 8px;">
                  ✅ 已選擇 API：{{ getApiEndpointName(selectedApiEndpointId) }}
                </p>
                <p v-else-if="templateForm.next_api_config" class="form-hint" style="color: #10b981; margin-top: 8px;">
                  ✅ 已配置自訂 API
                </p>
                <p v-else class="form-hint" style="color: #ef4444; margin-top: 8px;">
                  ⚠️ 請選擇 API 端點或使用自訂配置
                </p>
              </div>

              <!-- 自訂 JSON 編輯器 -->
              <div style="margin-top: 10px;">
                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                  <input
                    type="checkbox"
                    v-model="useCustomApiConfig"
                    @change="onCustomApiConfigToggle"
                  />
                  <span>手動編輯 API 配置 JSON（進階）</span>
                </label>

                <textarea
                  v-if="useCustomApiConfig"
                  v-model="apiConfigJson"
                  @blur="updateApiConfigFromJson"
                  class="form-control json-editor"
                  rows="6"
                  placeholder='{"method": "POST", "endpoint": "...", "params": {}}'
                  style="margin-top: 10px; font-family: 'Courier New', monospace; font-size: 0.9em;"
                ></textarea>

                <small v-if="useCustomApiConfig" class="form-hint">
                  💡 JSON 格式範例：<br>
                  <code style="display: block; background: #f5f5f5; padding: 8px; border-radius: 4px; margin-top: 4px;">
                    {<br>
                    &nbsp;&nbsp;"method": "POST",<br>
                    &nbsp;&nbsp;"endpoint": "http://api.example.com/...",<br>
                    &nbsp;&nbsp;"params": {}<br>
                    }
                  </code>
                </small>
              </div>
            </div>
          </div>

          <div class="modal-actions">
            <button type="submit" class="btn btn-primary">💾 儲存</button>
            <button type="button" @click="closeTemplateModal" class="btn btn-secondary">取消</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 範本使用情況 Modal -->
    <div v-if="showUsageModal" class="modal-overlay" @click="showUsageModal = false">
      <div class="modal-content" @click.stop>
        <h2>範本使用情況: {{ currentTemplateUsage.template_name }}</h2>

        <div v-if="currentTemplateUsage.usage.length > 0" class="usage-list">
          <div v-for="usage in currentTemplateUsage.usage" :key="usage.vendor_id" class="usage-item">
            <div class="usage-vendor">
              <strong>{{ usage.vendor_name }}</strong>
            </div>
            <div class="usage-status">
              {{ usage.has_copied ? '✅ 已使用' : '⚪ 未使用' }}
            </div>
            <div v-if="usage.copied_at" class="usage-date">
              複製時間: {{ new Date(usage.copied_at).toLocaleString('zh-TW') }}
            </div>
          </div>
        </div>

        <div v-else class="no-data">
          目前沒有業者使用此範本
        </div>

        <div class="modal-actions">
          <button @click="showUsageModal = false" class="btn btn-secondary">關閉</button>
        </div>
      </div>
    </div>

    <!-- 新增分類 Modal -->
    <div v-if="showCategoryModal" class="modal-overlay" @click="showCategoryModal = false">
      <div class="modal-content" @click.stop>
        <h2>📁 新增分類</h2>
        <div v-if="businessType !== null" class="info-box">
          <p><strong>💡 提示：</strong></p>
          <p>新增的分類需要添加 {{ businessTypeTitle.replace('範本管理', '') }} 的 SOP 項目後才會顯示在列表中。</p>
          <p>儲存後將自動引導您添加第一個項目。</p>
        </div>
        <form @submit.prevent="saveCategory">
          <div class="form-group">
            <label>分類名稱 *</label>
            <input v-model="categoryForm.category_name" type="text" required class="form-control" placeholder="例如：租賃流程相關資訊" />
          </div>

          <div class="form-group">
            <label>分類說明</label>
            <textarea v-model="categoryForm.description" class="form-control" rows="3" placeholder="簡述此分類的用途"></textarea>
          </div>

          <div class="modal-actions">
            <button type="submit" class="btn btn-primary">💾 儲存並新增項目</button>
            <button type="button" @click="closeCategoryModal" class="btn btn-secondary">取消</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 新增群組 Modal -->
    <div v-if="showCreateGroupModal" class="modal-overlay" @click="showCreateGroupModal = false">
      <div class="modal-content" @click.stop>
        <h2>➕ 新增群組（說明）</h2>
        <div class="info-box">
          <p><strong>💡 提示：</strong></p>
          <p>群組用於將同類型的 SOP 項目分組顯示，對應 Excel 檔案的「說明」欄位。</p>
          <p>例如：「租賃流程」分類下可建立「承租流程」「退租流程」等群組。</p>
        </div>
        <form @submit.prevent="saveGroup">
          <div class="form-group">
            <label>群組名稱 *</label>
            <input v-model="groupForm.group_name" type="text" required class="form-control" placeholder="例如：承租流程" />
          </div>

          <div class="form-group">
            <label>群組說明</label>
            <textarea v-model="groupForm.description" class="form-control" rows="2" placeholder="簡述此群組的用途"></textarea>
          </div>

          <div class="form-group">
            <label>顯示順序</label>
            <input v-model.number="groupForm.display_order" type="number" min="1" class="form-control" />
            <small class="form-hint">數字越小越靠前</small>
          </div>

          <div class="modal-actions">
            <button type="submit" class="btn btn-primary">💾 儲存</button>
            <button type="button" @click="closeCreateGroupModal" class="btn btn-secondary">取消</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 從通用範本複製 Modal -->
    <div v-if="showCopyModal" class="modal-overlay" @click="showCopyModal = false">
      <div class="modal-content modal-large" @click.stop>
        <h2>📋 從通用範本複製</h2>
        <p class="modal-description">將通用範本複製為 {{ businessTypeTitle }}，複製後可自行調整內容</p>

        <div v-if="copyLoading" class="loading">
          <span class="spinner"></span> 載入通用範本中...
        </div>

        <div v-else class="copy-options">
          <div class="select-all-section">
            <label class="select-all-checkbox">
              <input type="checkbox" v-model="copyAllCategories" @change="toggleAllCategories" />
              <strong>✅ 全選所有分類（共 {{ universalTemplateCount }} 個通用範本）</strong>
            </label>
          </div>

          <div class="categories-checklist">
            <div v-for="category in universalCategories" :key="category.id" class="category-checkbox-group">
              <label class="category-checkbox">
                <input
                  type="checkbox"
                  :value="category.id"
                  v-model="selectedCategoryIds"
                  @change="updateCopyAll"
                />
                <strong>{{ category.category_name }}</strong>
                <span class="item-count">({{ getUniversalTemplatesByCategory(category.id).length }} 個項目)</span>
              </label>

              <div v-if="selectedCategoryIds.includes(category.id)" class="templates-preview">
                <div v-for="template in getUniversalTemplatesByCategory(category.id)" :key="template.id" class="template-preview-item">
                  <span class="template-number">#{{ template.item_number }}</span>
                  <span class="template-name">{{ template.item_name }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-actions">
          <button @click="copyUniversalTemplates" :disabled="selectedCategoryIds.length === 0 || copying" class="btn btn-primary">
            {{ copying ? '⏳ 複製中...' : `📋 複製選中的範本 (${getSelectedTemplateCount()} 個項目)` }}
          </button>
          <button @click="closeCopyModal" class="btn btn-secondary">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { API_BASE_URL } from '@/config/api';
import KeywordsInput from '../components/KeywordsInput.vue';

const RAG_API = `${API_BASE_URL}/rag-api/v1`;  // RAG Orchestrator API

export default {
  name: 'PlatformSOPEditView',

  components: {
    KeywordsInput
  },

  data() {
    return {
      loading: false,
      categories: [],
      templates: [],
      intents: [],
      groups: [],
      availableGroups: [],

      // Accordion states
      expandedCategories: {},
      expandedGroups: {},

      // Modal states
      showTemplateModal: false,
      showUsageModal: false,
      showCategoryModal: false,
      showCopyModal: false,
      showCreateGroupModal: false,

      // Copy universal templates
      copyLoading: false,
      copying: false,
      universalTemplates: [],
      universalCategories: [],
      selectedCategoryIds: [],
      copyAllCategories: false,

      // Editing state
      editingTemplate: null,

      // Forms
      categoryForm: {
        category_name: '',
        description: ''
      },

      groupForm: {
        category_id: null,
        group_name: '',
        description: '',
        display_order: 1
      },

      templateForm: {
        category_id: null,
        group_id: null,
        business_type: null,
        item_number: 1,
        item_name: '',
        content: '',
        intent_ids: [],
        priority: 50,
        template_notes: '',
        customization_hint: '',
        // 流程配置欄位
        trigger_mode: 'none',
        next_action: 'none',
        trigger_keywords: [],
        immediate_prompt: '',
        followup_prompt: '',
        next_form_id: null,
        next_api_config: null
      },

      // 表單和 API 相關
      availableForms: [],
      availableApiEndpoints: [],
      selectedApiEndpointId: '',
      useCustomApiConfig: false,
      apiConfigJson: '',

      currentTemplateUsage: {
        template_id: null,
        template_name: '',
        usage: []
      }
    };
  },

  computed: {
    businessType() {
      const type = this.$route.params.businessType;
      return type === 'universal' ? null : type;
    },

    businessTypeTitle() {
      const type = this.$route.params.businessType;
      if (type === 'full_service') return '🏠 包租業範本管理';
      if (type === 'property_management') return '🔑 代管業範本管理';
      return '🌐 通用範本管理';
    },

    businessTypeDescription() {
      const type = this.$route.params.businessType;
      if (type === 'full_service') return '管理適用於包租型業者的 SOP 範本';
      if (type === 'property_management') return '管理適用於代管型業者的 SOP 範本';
      return '管理適用於所有業種的通用 SOP 範本';
    },

    filteredTemplates() {
      return this.templates.filter(t => t.business_type === this.businessType);
    },

    // 只顯示有該業態範本的分類
    filteredCategories() {
      return this.categories.filter(category => {
        // 檢查該分類下是否有該業態的範本
        return this.filteredTemplates.some(t => t.category_id === category.id);
      });
    },

    // 通用範本統計
    universalTemplateCount() {
      return this.universalTemplates.length;
    }
  },

  watch: {
    'templateForm.category_id'(newCategoryId) {
      // 當選擇分類時，自動設置下一個可用的項次編號（僅在新增模式下）
      if (!this.editingTemplate && newCategoryId) {
        this.templateForm.item_number = this.getNextItemNumber(newCategoryId);
      }
      // 載入該分類的群組
      if (newCategoryId) {
        this.loadGroupsByCategory(newCategoryId);
        this.templateForm.group_id = null;
      } else {
        this.availableGroups = [];
      }
    }
  },

  mounted() {
    this.loadData();
    this.loadIntents();
    this.loadAllGroups();
    this.loadAvailableForms();
    this.loadAvailableApiEndpoints();
  },

  methods: {
    async loadData() {
      this.loading = true;
      try {
        await Promise.all([
          this.loadCategories(),
          this.loadTemplates()
        ]);
      } catch (error) {
        console.error('載入資料失敗:', error);
        alert('載入資料失敗: ' + error.message);
      } finally {
        this.loading = false;
      }
    },

    async loadCategories() {
      const response = await axios.get(`${RAG_API}/platform/sop/categories`);
      this.categories = response.data.categories;
    },

    async loadTemplates() {
      const response = await axios.get(`${RAG_API}/platform/sop/templates`);
      this.templates = response.data.templates;
    },

    async loadIntents() {
      try {
        const response = await axios.get(`${RAG_API}/intents`);
        this.intents = response.data.intents || [];
      } catch (error) {
        console.error('載入意圖失敗:', error);
        this.intents = [];
      }
    },

    async loadAllGroups() {
      try {
        const response = await axios.get(`${RAG_API}/platform/sop/groups`);
        this.groups = response.data.groups || [];
      } catch (error) {
        console.error('載入所有群組失敗:', error);
        this.groups = [];
      }
    },

    async loadGroupsByCategory(categoryId) {
      try {
        const response = await axios.get(`${RAG_API}/platform/sop/groups?category_id=${categoryId}`);
        this.availableGroups = response.data.groups || [];
      } catch (error) {
        console.error('載入群組失敗:', error);
        this.availableGroups = [];
      }
    },

    getTemplatesByCategory(categoryId) {
      return this.filteredTemplates.filter(t => t.category_id === categoryId);
    },

    getGroupsByCategory(categoryId) {
      return this.groups.filter(g => g.category_id === categoryId && g.is_active);
    },

    getTemplatesByGroup(groupId) {
      return this.filteredTemplates.filter(t => t.group_id === groupId);
    },

    getUngroupedTemplates(categoryId) {
      return this.filteredTemplates.filter(t => t.category_id === categoryId && !t.group_id);
    },

    getCategoryTotalTemplates(categoryId) {
      // 檢查該分類下的所有範本（不分業態）
      return this.templates.filter(t => t.category_id === categoryId).length;
    },

    // Accordion methods
    toggleCategory(categoryId) {
      this.expandedCategories = {
        ...this.expandedCategories,
        [categoryId]: !this.expandedCategories[categoryId]
      };
    },

    isCategoryExpanded(categoryId) {
      return !!this.expandedCategories[categoryId];
    },

    toggleGroup(groupId) {
      this.expandedGroups = {
        ...this.expandedGroups,
        [groupId]: !this.expandedGroups[groupId]
      };
    },

    isGroupExpanded(groupId) {
      return !!this.expandedGroups[groupId];
    },

    // Template CRUD
    getNextItemNumber(categoryId) {
      if (!categoryId) return 1;

      // 取得該分類下當前業態的範本
      // 修改後的約束允許不同業態使用相同的 item_number
      const categoryTemplates = this.templates.filter(t =>
        t.category_id === categoryId && t.business_type === this.businessType
      );

      if (categoryTemplates.length === 0) return 1;

      const maxItemNumber = Math.max(...categoryTemplates.map(t => t.item_number));
      return maxItemNumber + 1;
    },

    openNewTemplateModal() {
      // 重置表單
      this.editingTemplate = null;
      this.templateForm = {
        category_id: null,
        group_id: null,
        business_type: this.businessType,
        item_number: 1,
        item_name: '',
        content: '',
        intent_ids: [],
        priority: 50,
        template_notes: '',
        customization_hint: ''
      };

      this.showTemplateModal = true;
    },

    openNewTemplateModalForCategory(categoryId) {
      // 為指定分類打開新增範本 modal
      this.editingTemplate = null;
      this.templateForm = {
        category_id: categoryId,
        group_id: null,
        business_type: this.businessType,
        item_number: this.getNextItemNumber(categoryId),
        item_name: '',
        content: '',
        intent_ids: [],
        priority: 50,
        template_notes: '',
        customization_hint: ''
      };

      // 載入該分類的群組
      this.loadGroupsByCategory(categoryId);
      this.showTemplateModal = true;
    },

    editTemplate(template) {
      this.editingTemplate = template;
      this.templateForm = {
        category_id: template.category_id,
        group_id: template.group_id || null,
        business_type: template.business_type || null,
        item_number: template.item_number,
        item_name: template.item_name,
        content: template.content,
        intent_ids: template.intent_ids && template.intent_ids.length > 0 ? [...template.intent_ids] : [],
        priority: template.priority,
        template_notes: template.template_notes || '',
        customization_hint: template.customization_hint || '',
        // 流程配置欄位
        trigger_mode: template.trigger_mode || 'none',
        next_action: template.next_action || 'none',
        trigger_keywords: template.trigger_keywords ? [...template.trigger_keywords] : [],
        immediate_prompt: template.immediate_prompt || '',
        followup_prompt: template.followup_prompt || '',
        next_form_id: template.next_form_id || null,
        next_api_config: template.next_api_config || null
      };

      // 如果有 API 配置，初始化選擇器
      if (template.next_api_config && template.next_api_config.endpoint_id) {
        this.selectedApiEndpointId = template.next_api_config.endpoint_id;
      } else {
        this.selectedApiEndpointId = '';
      }

      // 載入該分類的群組
      if (template.category_id) {
        this.loadGroupsByCategory(template.category_id);
      }
      this.showTemplateModal = true;
    },

    async saveTemplate() {
      try {
        // Validate required fields
        if (!this.templateForm.category_id) {
          alert('請選擇所屬分類');
          return;
        }

        // Set the business_type based on current view
        this.templateForm.business_type = this.businessType;

        // ===== 驗證流程配置 =====

        // 驗證 manual 模式
        if (this.templateForm.trigger_mode === 'manual') {
          if (!this.templateForm.trigger_keywords || this.templateForm.trigger_keywords.length === 0) {
            alert('❌ 觸發模式選擇「排查型（等待關鍵詞）」時，必須設定至少一個觸發關鍵詞');
            return;
          }
        }

        // immediate 模式不需要驗證 immediate_prompt（系統自動生成）

        // 驗證表單關聯
        if (['form_fill', 'form_then_api'].includes(this.templateForm.next_action)) {
          if (!this.templateForm.next_form_id) {
            alert('❌ 後續動作選擇「觸發表單」或「先填表單再調用 API」時，必須選擇表單');
            return;
          }
        }

        // 驗證 API 配置
        if (['api_call', 'form_then_api'].includes(this.templateForm.next_action)) {
          if (!this.templateForm.next_api_config) {
            alert('❌ 後續動作選擇「調用 API」或「先填表單再調用 API」時，必須配置 API');
            return;
          }

          // 如果使用自訂 JSON，驗證 JSON 格式
          if (this.useCustomApiConfig) {
            try {
              const config = JSON.parse(this.apiConfigJson);
              this.templateForm.next_api_config = config;
            } catch (e) {
              alert('❌ API 配置 JSON 格式錯誤，請檢查：\n' + e.message);
              return;
            }
          }
        }

        if (this.editingTemplate) {
          // Update
          await axios.put(
            `${RAG_API}/platform/sop/templates/${this.editingTemplate.id}`,
            this.templateForm
          );
          alert('範本已更新');
        } else {
          // Create
          await axios.post(
            `${RAG_API}/platform/sop/templates`,
            this.templateForm
          );
          alert('範本已建立');
        }
        this.closeTemplateModal();
        this.loadTemplates();
      } catch (error) {
        console.error('儲存範本失敗:', error);
        alert('儲存範本失敗: ' + (error.response?.data?.detail || error.message));
      }
    },

    async deleteTemplate(templateId) {
      if (!confirm('確定要刪除此範本嗎？')) return;

      try {
        await axios.delete(`${RAG_API}/platform/sop/templates/${templateId}`);
        alert('範本已刪除');
        this.loadTemplates();
      } catch (error) {
        console.error('刪除範本失敗:', error);
        alert('刪除範本失敗: ' + (error.response?.data?.detail || error.message));
      }
    },

    closeTemplateModal() {
      this.showTemplateModal = false;
      this.editingTemplate = null;
      this.templateForm = {
        category_id: null,
        group_id: null,
        business_type: null,
        item_number: 1,
        item_name: '',
        content: '',
        intent_ids: [],
        priority: 50,
        template_notes: '',
        customization_hint: ''
      };
      this.availableGroups = [];
    },

    async viewTemplateUsage(templateId) {
      try {
        const response = await axios.get(`${RAG_API}/platform/sop/templates/${templateId}/usage`);
        this.currentTemplateUsage = response.data;
        this.showUsageModal = true;
      } catch (error) {
        console.error('載入使用情況失敗:', error);
        alert('載入使用情況失敗: ' + error.message);
      }
    },

    // Helper methods
    getIntentName(intentId) {
      const intent = this.intents.find(i => i.id === intentId);
      return intent ? intent.name : `ID:${intentId}`;
    },

    getPriorityClass(priority) {
      if (priority >= 90) return 'priority-high';
      if (priority >= 70) return 'priority-medium';
      return 'priority-low';
    },

    // Category management
    async saveCategory() {
      try {
        const response = await axios.post(`${RAG_API}/platform/sop/categories`, this.categoryForm);
        const newCategory = response.data;

        this.closeCategoryModal();
        await this.loadCategories(); // 重新載入分類列表

        // 新增分類成功後，自動打開新增 SOP 項目 modal 並預選該分類
        alert(`✅ 分類「${newCategory.category_name}」已新增\n\n接下來請為此分類添加 SOP 項目`);

        this.editingTemplate = null;
        this.templateForm = {
          category_id: newCategory.id, // 預選新建的分類
          business_type: this.businessType,
          item_number: 1,
          item_name: '',
          content: '',
          intent_ids: [],
          priority: 50,
          template_notes: '',
          customization_hint: ''
        };
        this.showTemplateModal = true;
      } catch (error) {
        console.error('新增分類失敗:', error);
        alert('❌ 新增分類失敗: ' + (error.response?.data?.detail || error.message));
      }
    },

    closeCategoryModal() {
      this.showCategoryModal = false;
      this.categoryForm = {
        category_name: '',
        description: ''
      };
    },

    // Group management
    async saveGroup() {
      try {
        // 設定群組所屬的分類
        this.groupForm.category_id = this.templateForm.category_id;

        const response = await axios.post(`${RAG_API}/platform/sop/groups`, this.groupForm);
        const newGroup = response.data;

        alert(`✅ 群組「${newGroup.group_name}」已新增`);

        this.closeCreateGroupModal();

        // 重新載入所有群組（用於列表顯示）
        await this.loadAllGroups();
        // 重新載入該分類的群組（用於表單選擇）
        await this.loadGroupsByCategory(this.templateForm.category_id);

        // 自動選擇新建的群組
        this.templateForm.group_id = newGroup.id;
      } catch (error) {
        console.error('新增群組失敗:', error);
        alert('❌ 新增群組失敗: ' + (error.response?.data?.detail || error.message));
      }
    },

    closeCreateGroupModal() {
      this.showCreateGroupModal = false;
      this.groupForm = {
        category_id: null,
        group_name: '',
        description: '',
        display_order: 1
      };
    },

    async deleteGroup(groupId, groupName, categoryId) {
      const templatesInGroup = this.getTemplatesByGroup(groupId);
      const templateCount = templatesInGroup.length;

      let confirmMessage = '';
      let moveToGroupId = null;

      if (templateCount === 0) {
        // 空群組，直接刪除
        confirmMessage = `確定要刪除空群組「${groupName}」嗎？`;
      } else {
        // 有模板的群組，詢問是否移動
        const otherGroups = this.getGroupsByCategory(categoryId).filter(g => g.id !== groupId);

        if (otherGroups.length > 0) {
          confirmMessage = `群組「${groupName}」包含 ${templateCount} 個模板。\n\n您可以：\n`;
          confirmMessage += `1. 將這些模板移動到其他群組\n`;
          confirmMessage += `2. 將這些模板設為「未分組」\n\n`;
          confirmMessage += `是否要將模板移動到其他群組？\n`;
          confirmMessage += `（點「確定」選擇目標群組，點「取消」設為未分組）`;

          const shouldMove = confirm(confirmMessage);

          if (shouldMove) {
            // 讓用戶選擇目標群組
            let groupOptions = '請輸入目標群組編號：\n\n';
            otherGroups.forEach((g, index) => {
              groupOptions += `${index + 1}. ${g.group_name} (${this.getTemplatesByGroup(g.id).length} 個項目)\n`;
            });

            const selection = prompt(groupOptions);
            if (selection === null) {
              return; // 用戶取消
            }

            const selectedIndex = parseInt(selection) - 1;
            if (selectedIndex >= 0 && selectedIndex < otherGroups.length) {
              moveToGroupId = otherGroups[selectedIndex].id;
            } else {
              alert('無效的選擇，將設為未分組');
              moveToGroupId = null;
            }
          }
          // 如果 shouldMove 為 false，moveToGroupId 保持為 null（未分組）
        } else {
          // 沒有其他群組，只能設為未分組
          confirmMessage = `群組「${groupName}」包含 ${templateCount} 個模板。\n\n`;
          confirmMessage += `刪除後，這些模板將設為「未分組」。\n\n`;
          confirmMessage += `確定要繼續嗎？`;

          if (!confirm(confirmMessage)) {
            return;
          }
        }
      }

      // 最後確認
      if (templateCount === 0 && !confirm(confirmMessage)) {
        return;
      }

      try {
        const url = moveToGroupId
          ? `${RAG_API}/platform/sop/groups/${groupId}?move_to_group_id=${moveToGroupId}`
          : `${RAG_API}/platform/sop/groups/${groupId}`;

        await axios.delete(url);

        const moveMsg = moveToGroupId
          ? `，模板已移動到其他群組`
          : templateCount > 0 ? `，${templateCount} 個模板已設為未分組` : '';

        alert(`✅ 群組「${groupName}」已刪除${moveMsg}`);

        // 重新載入資料
        await this.loadAllGroups();
        await this.loadTemplates();
      } catch (error) {
        console.error('刪除群組失敗:', error);
        alert('❌ 刪除群組失敗: ' + (error.response?.data?.detail || error.message));
      }
    },

    async deleteCategory(categoryId, categoryName) {
      const currentBusinessTypeTemplates = this.getTemplatesByCategory(categoryId);
      const totalTemplates = currentBusinessTypeTemplates.length;

      let confirmMessage = '';
      let businessTypeLabel = '';

      if (this.businessType === null) {
        businessTypeLabel = '通用';
      } else if (this.businessType === 'full_service') {
        businessTypeLabel = '包租業';
      } else if (this.businessType === 'property_management') {
        businessTypeLabel = '代管業';
      }

      if (totalTemplates === 0) {
        confirmMessage = `確定要從 ${businessTypeLabel} 移除分類「${categoryName}」嗎？\n\n此分類在 ${businessTypeLabel} 下目前沒有任何範本。`;
      } else {
        confirmMessage = `⚠️ 警告：確定要永久刪除「${categoryName}」分類下的所有 ${businessTypeLabel} 範本嗎？\n\n`;
        confirmMessage += `將永久刪除 ${totalTemplates} 個 ${businessTypeLabel} 範本\n`;
        confirmMessage += `• 其他業態的範本不受影響\n`;
        confirmMessage += `• 此操作無法復原\n\n`;
        confirmMessage += `確定要繼續嗎？`;
      }

      if (!confirm(confirmMessage)) {
        return;
      }

      try {
        // 逐一永久刪除該分類下當前業態的所有範本
        let successCount = 0;
        let errorCount = 0;

        for (const template of currentBusinessTypeTemplates) {
          try {
            // 添加 ?permanent=true 參數進行永久刪除
            await axios.delete(`${RAG_API}/platform/sop/templates/${template.id}?permanent=true`);
            successCount++;
          } catch (error) {
            console.error(`刪除範本 ${template.id} 失敗:`, error);
            errorCount++;
          }
        }

        if (successCount > 0) {
          alert(`✅ 已永久刪除 ${successCount} 個 ${businessTypeLabel} 範本${errorCount > 0 ? `\n❌ ${errorCount} 個刪除失敗` : ''}`);
        } else {
          alert(`✅ 已從 ${businessTypeLabel} 移除此分類`);
        }

        await this.loadCategories(); // 重新載入分類列表
        await this.loadTemplates(); // 重新載入範本列表
      } catch (error) {
        console.error('刪除失敗:', error);
        alert('❌ 刪除失敗: ' + (error.response?.data?.detail || error.message));
      }
    },

    // Copy universal templates
    async showCopyModalHandler() {
      this.showCopyModal = true;
      this.copyLoading = true;

      try {
        // 重新載入所有範本（確保 this.templates 是最新的）
        await this.loadTemplates();

        // 載入通用範本
        const response = await axios.get(`${RAG_API}/platform/sop/templates`);
        this.universalTemplates = response.data.templates.filter(t => t.business_type === null);

        // 取得有通用範本的分類
        const categoryIds = [...new Set(this.universalTemplates.map(t => t.category_id))];
        this.universalCategories = this.categories.filter(c => categoryIds.includes(c.id));
      } catch (error) {
        console.error('載入通用範本失敗:', error);
        alert('載入通用範本失敗: ' + (error.response?.data?.detail || error.message));
      } finally {
        this.copyLoading = false;
      }
    },

    getUniversalTemplatesByCategory(categoryId) {
      return this.universalTemplates.filter(t => t.category_id === categoryId);
    },

    toggleAllCategories() {
      if (this.copyAllCategories) {
        this.selectedCategoryIds = this.universalCategories.map(c => c.id);
      } else {
        this.selectedCategoryIds = [];
      }
    },

    updateCopyAll() {
      this.copyAllCategories = this.selectedCategoryIds.length === this.universalCategories.length;
    },

    getSelectedTemplateCount() {
      return this.universalTemplates.filter(t => this.selectedCategoryIds.includes(t.category_id)).length;
    },

    async copyUniversalTemplates() {
      if (this.selectedCategoryIds.length === 0) {
        alert('請至少選擇一個分類');
        return;
      }

      const selectedTemplates = this.universalTemplates.filter(t => this.selectedCategoryIds.includes(t.category_id));

      if (!confirm(`確定要複製 ${selectedTemplates.length} 個範本到 ${this.businessTypeTitle} 嗎？`)) {
        return;
      }

      this.copying = true;

      try {
        let successCount = 0;
        let errorCount = 0;
        const errors = [];

        // 按分類分組範本，以便為每個分類計算正確的 item_number
        const templatesByCategory = {};
        selectedTemplates.forEach(t => {
          if (!templatesByCategory[t.category_id]) {
            templatesByCategory[t.category_id] = [];
          }
          templatesByCategory[t.category_id].push(t);
        });

        // 為每個分類複製範本
        for (const [categoryId, templates] of Object.entries(templatesByCategory)) {
          // 取得該分類當前最大的 item_number（檢查所有業態）
          const categoryIdInt = parseInt(categoryId);
          let nextItemNumber = this.getNextItemNumber(categoryIdInt);

          console.log(`分類 ${categoryIdInt} 的下一個項次編號:`, nextItemNumber);

          // 按 item_number 排序，保持原有順序
          templates.sort((a, b) => a.item_number - b.item_number);

          for (const template of templates) {
            const payload = {
              category_id: template.category_id,
              business_type: this.businessType,
              group_id: template.group_id || null,  // 複製群組ID
              item_number: nextItemNumber,
              item_name: template.item_name,
              content: template.content,
              intent_ids: template.intent_ids || [],
              priority: template.priority,
              template_notes: template.template_notes,
              customization_hint: template.customization_hint
            };

            console.log(`準備複製範本「${template.item_name}」:`, payload);

            try {
              await axios.post(`${RAG_API}/platform/sop/templates`, payload);
              console.log(`✅ 成功複製「${template.item_name}」，item_number: ${nextItemNumber}`);
              successCount++;
              nextItemNumber++; // 為下一個範本遞增
            } catch (error) {
              console.error(`❌ 複製範本「${template.item_name}」失敗:`, error.response?.data || error.message);
              errors.push({
                name: template.item_name,
                error: error.response?.data?.detail || error.message
              });
              errorCount++;
            }
          }
        }

        // 顯示結果
        let message = `複製完成！\n✅ 成功：${successCount} 個\n❌ 失敗：${errorCount} 個`;

        if (errors.length > 0 && errors.length <= 5) {
          message += '\n\n失敗項目：';
          errors.forEach(e => {
            message += `\n• ${e.name}: ${e.error}`;
          });
        } else if (errors.length > 5) {
          message += '\n\n部分失敗項目：';
          errors.slice(0, 5).forEach(e => {
            message += `\n• ${e.name}: ${e.error}`;
          });
          message += `\n... 還有 ${errors.length - 5} 個錯誤`;
        }

        alert(message);

        if (successCount > 0) {
          this.closeCopyModal();
          await this.loadTemplates(); // 重新載入範本
        }
      } catch (error) {
        console.error('複製失敗:', error);
        alert('複製失敗: ' + (error.response?.data?.detail || error.message));
      } finally {
        this.copying = false;
      }
    },

    closeCopyModal() {
      this.showCopyModal = false;
      this.selectedCategoryIds = [];
      this.copyAllCategories = false;
      this.universalTemplates = [];
      this.universalCategories = [];
    },

    // ===== 流程配置相關方法 =====

    // 載入可用表單列表
    async loadAvailableForms() {
      try {
        const response = await axios.get(`${RAG_API}/forms`);
        this.availableForms = response.data;
      } catch (error) {
        console.error('載入表單列表失敗:', error);
      }
    },

    // 載入可用 API 端點列表
    async loadAvailableApiEndpoints() {
      try {
        const response = await axios.get(`${RAG_API}/api-endpoints`);
        this.availableApiEndpoints = response.data;
      } catch (error) {
        console.error('載入 API 端點列表失敗:', error);
      }
    },

    // 觸發模式改變時的處理
    onTriggerModeChange() {
      // 切換模式時清空相關欄位
      if (this.templateForm.trigger_mode !== 'manual') {
        this.templateForm.trigger_keywords = [];
      }
      // immediate 模式的提示詞由後端自動生成，不需要前端處理
    },

    // 後續動作改變時的處理
    onNextActionChange() {
      // 切換動作時清空相關欄位
      if (!['form_fill', 'form_then_api'].includes(this.templateForm.next_action)) {
        this.templateForm.next_form_id = null;
      }
      if (!['api_call', 'form_then_api'].includes(this.templateForm.next_action)) {
        this.templateForm.next_api_config = null;
        this.selectedApiEndpointId = '';
        this.apiConfigJson = '';
      }
      if (this.templateForm.next_action === 'none') {
        this.templateForm.followup_prompt = '';
      }
    },

    // API 端點選擇改變
    onApiEndpointChange() {
      if (!this.selectedApiEndpointId) {
        this.templateForm.next_api_config = null;
        return;
      }

      const selectedApi = this.availableApiEndpoints.find(
        api => api.endpoint_id === this.selectedApiEndpointId
      );

      if (selectedApi) {
        this.templateForm.next_api_config = {
          endpoint_id: selectedApi.endpoint_id,
          endpoint_name: selectedApi.endpoint_name,
          method: selectedApi.method || 'GET',
          endpoint: selectedApi.endpoint_url
        };
      }
    },

    // 切換自訂 API 配置模式
    onCustomApiConfigToggle() {
      if (this.useCustomApiConfig) {
        // 切換到自訂模式：從現有配置載入 JSON
        if (this.templateForm.next_api_config) {
          this.apiConfigJson = JSON.stringify(this.templateForm.next_api_config, null, 2);
        } else {
          this.apiConfigJson = '{\n  "method": "POST",\n  "endpoint": "",\n  "params": {}\n}';
        }
        this.selectedApiEndpointId = '';
      } else {
        // 切換到選擇器模式：清空 JSON
        this.apiConfigJson = '';
      }
    },

    // 從 JSON 更新 API 配置
    updateApiConfigFromJson() {
      if (!this.useCustomApiConfig) return;

      try {
        const config = JSON.parse(this.apiConfigJson);
        this.templateForm.next_api_config = config;
      } catch (e) {
        console.error('API 配置 JSON 格式錯誤:', e);
      }
    },

    // 取得表單名稱
    getFormName(formId) {
      const form = this.availableForms.find(f => f.form_id === formId);
      return form ? form.form_name : formId;
    },

    // 取得 API 端點名稱
    getApiEndpointName(endpointId) {
      const api = this.availableApiEndpoints.find(a => a.endpoint_id === endpointId);
      return api ? api.endpoint_name : endpointId;
    }
  }
};
</script>

<style scoped>
/* Import common styles from PlatformSOPView - you can extract these to a shared CSS file if needed */
.platform-sop-edit-view {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 30px;
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-actions {
  display: flex;
  gap: 10px;
  margin-left: auto;
}

.btn-back {
  padding: 10px 20px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.btn-back:hover {
  background: #5a6268;
}

.header-content {
  flex: 1;
}

.page-header h1 {
  font-size: 28px;
  color: #333;
  margin: 0 0 8px 0;
}

.subtitle {
  color: #666;
  font-size: 14px;
  margin: 0;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.btn-primary {
  background: #4CAF50;
  color: white;
}

.btn-primary:hover {
  background: #45a049;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
}

.btn-info {
  background: #17a2b8;
  color: white;
}

.btn-info:hover {
  background: #138496;
}

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn-danger:hover {
  background: #c82333;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}

.btn-inline {
  display: inline-block;
  padding: 4px 10px;
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  margin-left: 8px;
  transition: all 0.2s;
  vertical-align: middle;
}

.btn-inline:hover {
  background: #45a049;
  transform: translateY(-1px);
}

.loading {
  text-align: center;
  padding: 40px;
  color: #666;
}

.spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #4CAF50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.sop-categories {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.category-section {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.category-header-collapsible {
  background: #f8f9fa;
  padding: 15px 20px;
  border-left: 4px solid #4CAF50;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.2s;
  user-select: none;
}

.category-header-collapsible:hover {
  background: #e9ecef;
  border-left-color: #45a049;
}

.category-header-collapsible .collapse-icon,
.category-header-collapsible h2,
.category-header-collapsible .category-count {
  cursor: pointer;
}

.category-delete-btn {
  margin-left: auto;
  opacity: 0.7;
}

.category-delete-btn:hover {
  opacity: 1;
}

.category-header-collapsible h2 {
  margin: 0;
  font-size: 20px;
  color: #333;
  font-weight: 600;
}

.collapse-icon {
  font-size: 14px;
  color: #4CAF50;
  font-weight: bold;
  transition: transform 0.2s;
}

.category-count {
  background: #4CAF50;
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 500;
}

/* 群組樣式（第 2 層） */
.groups-list {
  padding: 10px 20px 20px 20px;
}

.group-section {
  background: #f9f9f9;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  margin-bottom: 12px;
  overflow: hidden;
}

.group-header-collapsible {
  background: #ffffff;
  padding: 12px 16px;
  border-left: 4px solid #2196F3;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all 0.2s;
  user-select: none;
}

.group-header-collapsible:hover {
  background: #f5f5f5;
  border-left-color: #1976D2;
}

.group-header-collapsible.ungrouped {
  border-left-color: #9E9E9E;
  background: #fafafa;
}

.group-header-collapsible.ungrouped:hover {
  background: #f0f0f0;
  border-left-color: #757575;
}

.group-header-collapsible.ungrouped h3 {
  color: #999;
  font-style: italic;
}

.group-header-collapsible h3 {
  margin: 0;
  font-size: 16px;
  color: #444;
  font-weight: 600;
  flex: 1;
}

.group-delete-btn {
  margin-left: auto;
  opacity: 0.7;
}

.group-delete-btn:hover {
  opacity: 1;
}

.group-count {
  background: #2196F3;
  color: white;
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
}

.templates-list {
  padding: 16px;
}

.no-templates-in-group {
  text-align: center;
  padding: 30px 20px;
  color: #aaa;
  font-size: 14px;
}

.template-card {
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 16px;
}

.template-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.template-number {
  background: #9E9E9E;
  color: white;
  padding: 4px 10px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 13px;
}

.template-header h4 {
  font-size: 15px;
  color: #333;
  margin: 0;
  flex: 1;
  font-weight: 600;
}

.badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.badge-intent {
  background: #F3E5F5;
  color: #7B1FA2;
}

.badge-priority {
  background: #E8F5E9;
  color: #388E3C;
}

.priority-high {
  background: #FFEBEE;
  color: #C62828;
}

.priority-medium {
  background: #FFF3E0;
  color: #EF6C00;
}

.priority-low {
  background: #E8F5E9;
  color: #388E3C;
}

.template-content {
  margin: 12px 0;
}

.content-section {
  margin-bottom: 12px;
}

.content-section strong {
  display: block;
  color: #555;
  margin-bottom: 4px;
  font-size: 13px;
}

.content-section p {
  margin: 0;
  color: #666;
  font-size: 14px;
  line-height: 1.6;
  padding: 8px;
  background: white;
  border-radius: 4px;
}

.template-guide {
  background: #FFFDE7;
  padding: 8px;
  border-radius: 4px;
  border-left: 3px solid #FBC02D;
}

.template-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.no-templates {
  text-align: center;
  padding: 60px 20px;
  color: #999;
  font-size: 16px;
}

/* Modal styles */
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

.modal-content {
  background: white;
  border-radius: 8px;
  padding: 24px;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-large {
  max-width: 900px;
}

.modal-content h2 {
  margin-top: 0;
  color: #333;
  font-size: 22px;
  margin-bottom: 20px;
}

.form-section {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #eee;
}

.form-section:last-of-type {
  border-bottom: none;
}

.form-section h3 {
  font-size: 16px;
  color: #555;
  margin-top: 0;
  margin-bottom: 16px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  color: #555;
  font-weight: 500;
  font-size: 14px;
}

.form-control {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-control:focus {
  outline: none;
  border-color: #4CAF50;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-hint {
  display: block;
  margin-top: 4px;
  color: #999;
  font-size: 12px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

/* Usage Modal */
.usage-list {
  margin: 20px 0;
}

.usage-item {
  padding: 12px;
  background: #f9f9f9;
  border-radius: 6px;
  margin-bottom: 10px;
  border-left: 3px solid #4CAF50;
}

.usage-vendor {
  margin-bottom: 6px;
}

.usage-status {
  font-size: 13px;
  color: #666;
  margin-bottom: 4px;
}

.usage-date {
  font-size: 12px;
  color: #999;
  font-style: italic;
}

.no-data {
  text-align: center;
  padding: 40px;
  color: #999;
  font-style: italic;
}

/* Checkbox styles for multi-intent selection */
.intent-checkboxes {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-top: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: white;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.checkbox-label:hover {
  border-color: #4CAF50;
  background: #f5f5f5;
}

.checkbox-label:has(.checkbox-input:checked) {
  background: #E8F5E9;
  border-color: #4CAF50;
}

.checkbox-input {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #4CAF50;
}

.checkbox-text {
  font-size: 14px;
  color: #333;
  flex: 1;
}

.checkbox-label:has(.checkbox-input:checked) .checkbox-text {
  font-weight: 600;
  color: #2E7D32;
}

/* Copy modal styles */
.modal-description {
  color: #666;
  font-size: 14px;
  margin-bottom: 20px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid #4CAF50;
}

.copy-options {
  margin-top: 20px;
}

.select-all-section {
  background: #e3f2fd;
  border: 2px solid #2196F3;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}

.select-all-checkbox {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  user-select: none;
  margin: 0;
}

.select-all-checkbox input[type="checkbox"] {
  width: 22px;
  height: 22px;
  cursor: pointer;
  accent-color: #2196F3;
}

.select-all-checkbox strong {
  color: #1976D2;
  font-size: 16px;
}

.categories-checklist {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 16px;
  max-height: 400px;
  overflow-y: auto;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
}

.category-checkbox-group {
  background: white;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  transition: all 0.2s;
}

.category-checkbox-group:has(input:checked) {
  border-color: #4CAF50;
  background: #f1f8f4;
}

.category-checkbox {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.category-checkbox input[type="checkbox"] {
  width: 20px;
  height: 20px;
  cursor: pointer;
  accent-color: #4CAF50;
}

.category-checkbox strong {
  flex: 1;
  color: #333;
  font-size: 16px;
}

.item-count {
  color: #666;
  font-size: 14px;
  font-weight: normal;
  padding: 4px 10px;
  background: #e8f5e9;
  border-radius: 12px;
}

.templates-preview {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.template-preview-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 4px;
  font-size: 13px;
}

.template-preview-item .template-number {
  font-size: 12px;
  padding: 3px 8px;
}

.template-preview-item .template-name {
  color: #555;
  flex: 1;
}

.no-templates-in-category {
  text-align: center;
  padding: 30px 20px;
  color: #aaa;
  font-size: 14px;
}

.no-templates-in-category p {
  margin: 0 0 12px 0;
  font-style: italic;
}

.no-templates-in-category .btn {
  margin: 0 auto;
}

.hint-box {
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 8px;
  padding: 16px;
  margin-top: 16px;
  text-align: left;
}

.hint-box p {
  margin: 0 0 8px 0;
  color: #856404;
  font-size: 14px;
}

.hint-box ul {
  margin: 8px 0 0 0;
  padding-left: 24px;
  color: #856404;
}

.hint-box li {
  margin-bottom: 6px;
  line-height: 1.5;
}

.info-box {
  background: #d1ecf1;
  border: 1px solid #17a2b8;
  border-left: 4px solid #17a2b8;
  border-radius: 6px;
  padding: 14px;
  margin-bottom: 20px;
}

.info-box p {
  margin: 0 0 6px 0;
  color: #0c5460;
  font-size: 13px;
  line-height: 1.5;
}

.info-box p:last-child {
  margin-bottom: 0;
}

.info-box strong {
  color: #0c5460;
}
</style>
