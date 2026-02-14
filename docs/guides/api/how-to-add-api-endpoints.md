# 如何新增或修改 API Endpoint 選項

**日期**: 2026-01-18
**適用範圍**: 知識庫動作系統、表單完成後動作

---

## 📋 概述

API Endpoint 選項是硬編碼在前端 Vue 文件中的下拉選單選項。當你需要新增或修改 API 時，需要手動修改這些文件。

---

## 📁 需要修改的文件

| 文件 | 路徑 | 行數 | 選項數量 |
|------|------|------|----------|
| **KnowledgeView.vue** | `knowledge-admin/frontend/src/views/KnowledgeView.vue` | 347-354 | 5 個 |
| **FormEditorView.vue** | `knowledge-admin/frontend/src/views/FormEditorView.vue` | 79-84 | 3 個 |

---

## 🔧 修改方法

### 文件 1: KnowledgeView.vue

**位置**: `knowledge-admin/frontend/src/views/KnowledgeView.vue:347-354`

**當前選項**:
```html
<select v-model="apiConfigData.endpoint" class="form-select">
  <option value="">請選擇...</option>
  <option value="billing_inquiry">📋 帳單查詢</option>
  <option value="verify_tenant_identity">🔐 租客身份驗證</option>
  <option value="resend_invoice">📧 重新發送帳單</option>
  <option value="maintenance_request">🔧 報修申請</option>
  <option value="rent_history">💰 查詢租金紀錄</option>
</select>
```

**新增方法**:
```html
<!-- 在 </select> 前面新增一行 -->
<option value="your_api_endpoint_name">🎯 你的功能名稱</option>
```

---

### 文件 2: FormEditorView.vue

**位置**: `knowledge-admin/frontend/src/views/FormEditorView.vue:79-84`

**當前選項**:
```html
<select v-model="apiConfigData.endpoint" class="form-select">
  <option value="">請選擇...</option>
  <option value="billing_inquiry">📋 帳單查詢</option>
  <option value="maintenance_request">🔧 報修申請</option>
  <option value="rent_history">💰 查詢租金紀錄</option>
</select>
```

**新增方法**:
```html
<!-- 在 </select> 前面新增一行 -->
<option value="your_api_endpoint_name">🎯 你的功能名稱</option>
```

---

## 📝 完整範例：新增「查詢租金紀錄」API

### 步驟 1: 在 KnowledgeView.vue 新增選項

```html
<option value="rent_history">💰 查詢租金紀錄</option>
```

### 步驟 2: 在 FormEditorView.vue 新增選項

```html
<option value="rent_history">💰 查詢租金紀錄</option>
```

### 步驟 3: 實作後端 API Handler

在 `rag-orchestrator/services/api_call_handler.py` 新增對應的處理邏輯：

```python
async def handle_rent_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    處理租金紀錄查詢
    """
    user_id = params.get('user_id')
    # 實作你的 API 邏輯
    return {
        "status": "success",
        "data": {...}
    }
```

並在 `execute_api_call()` 中註冊：

```python
async def execute_api_call(self, api_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    endpoint = api_config.get('endpoint')

    if endpoint == 'rent_history':
        return await self.handle_rent_history(params)
    # ... 其他 endpoint
```

---

## 🎨 選項格式說明

### value 屬性
- **格式**: 小寫英文 + 底線 (snake_case)
- **用途**: 傳給後端的 API endpoint 識別名稱
- **範例**: `billing_inquiry`, `rent_history`, `maintenance_request`

### 顯示文字
- **格式**: Emoji + 中文名稱
- **用途**: 前端下拉選單顯示給用戶看的文字
- **範例**: `📋 帳單查詢`, `💰 查詢租金紀錄`

### 推薦的 Emoji 對照表

| 功能類型 | 推薦 Emoji | 範例 |
|----------|-----------|------|
| 查詢/搜尋 | 📋 🔍 | 帳單查詢、資料查詢 |
| 身份驗證 | 🔐 🔑 | 租客身份驗證 |
| 發送/通知 | 📧 📨 | 重新發送帳單 |
| 維修/報修 | 🔧 🛠️ | 報修申請 |
| 金錢/租金 | 💰 💵 | 租金紀錄、繳費 |
| 預約/排程 | 📅 ⏰ | 預約參觀 |
| 文件/合約 | 📄 📑 | 合約查詢 |
| 用戶/租客 | 👤 👥 | 租客資料 |

---

## ⚠️ 注意事項

### 1. 兩個文件必須同步修改
如果你在 `KnowledgeView.vue` 新增了一個 API endpoint，也建議在 `FormEditorView.vue` 新增（除非該 API 不適用於表單場景）。

### 2. value 必須與後端一致
前端選項的 `value` 屬性必須與後端 `api_call_handler.py` 中的 endpoint 名稱完全一致。

### 3. 後端實作必須完成
新增前端選項後，必須在後端實作對應的 API handler，否則調用時會失敗。

### 4. 重新編譯前端
修改 Vue 文件後，需要重新編譯前端：

```bash
cd knowledge-admin/frontend
npm run build
```

或者在開發模式下會自動熱重載：

```bash
npm run dev
```

---

## 🔄 完整工作流程

```
1. 確定需求
   ↓
2. 設計 API endpoint 名稱 (例如: rent_history)
   ↓
3. 修改前端文件
   ├─ KnowledgeView.vue (新增選項)
   └─ FormEditorView.vue (新增選項)
   ↓
4. 實作後端 API Handler
   ├─ api_call_handler.py (新增處理方法)
   └─ 註冊到 execute_api_call()
   ↓
5. 測試
   ├─ 在知識庫管理頁面測試
   └─ 在表單編輯器頁面測試
   ↓
6. 部署
   ├─ 重新編譯前端
   └─ 重啟後端服務
```

---

## 🧪 測試檢查清單

### 前端測試
- [ ] KnowledgeView.vue 下拉選單顯示新選項
- [ ] FormEditorView.vue 下拉選單顯示新選項
- [ ] 選擇新選項後可以保存
- [ ] 重新編輯時選項正確載入

### 後端測試
- [ ] API handler 正確實作
- [ ] 參數正確傳遞
- [ ] 返回格式正確
- [ ] 錯誤處理完整

### 集成測試
- [ ] 在聊天介面觸發知識
- [ ] API 正確調用
- [ ] 返回結果正確格式化
- [ ] 合併知識答案功能正常

---

## 📚 相關文檔

- [API 配置指南](./design/API_CONFIGURATION_GUIDE.md)
- [API Call Handler 實作](./design/API_CALL_HANDLER_IMPLEMENTATION.md)
- [前端實作總結](./FRONTEND_IMPLEMENTATION_SUMMARY.md)
- [知識動作系統設計](./design/KNOWLEDGE_ACTION_SYSTEM_DESIGN.md)

---

## 🛠️ 快速修改腳本

如果你經常需要新增 API endpoint，可以使用以下腳本自動化：

```bash
#!/bin/bash
# add_api_endpoint.sh

ENDPOINT_VALUE="$1"
ENDPOINT_LABEL="$2"

if [ -z "$ENDPOINT_VALUE" ] || [ -z "$ENDPOINT_LABEL" ]; then
  echo "用法: ./add_api_endpoint.sh <endpoint_value> <emoji_label>"
  echo "範例: ./add_api_endpoint.sh rent_history '💰 查詢租金紀錄'"
  exit 1
fi

# 修改 KnowledgeView.vue
sed -i '' "/<option value=\"maintenance_request\">/a\\
                <option value=\"$ENDPOINT_VALUE\">$ENDPOINT_LABEL</option>
" knowledge-admin/frontend/src/views/KnowledgeView.vue

# 修改 FormEditorView.vue
sed -i '' "/<option value=\"maintenance_request\">/a\\
                <option value=\"$ENDPOINT_VALUE\">$ENDPOINT_LABEL</option>
" knowledge-admin/frontend/src/views/FormEditorView.vue

echo "✅ 已新增 API endpoint: $ENDPOINT_VALUE ($ENDPOINT_LABEL)"
echo "⚠️  請記得實作後端 API handler"
```

使用方式：
```bash
chmod +x add_api_endpoint.sh
./add_api_endpoint.sh rent_history "💰 查詢租金紀錄"
```

---

**維護者**: Claude Code
**更新日期**: 2026-01-18
**版本**: 1.0
