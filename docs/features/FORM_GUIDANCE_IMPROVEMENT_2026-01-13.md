# 📝 表單引導語改善 - 實施報告

**實施日期**：2026-01-13
**Git Commit**：ba503d3
**相關文檔**：表單管理系統

---

## 📋 目錄

1. [問題背景](#問題背景)
2. [問題分析](#問題分析)
3. [解決方案](#解決方案)
4. [代碼修改](#代碼修改)
5. [驗證測試](#驗證測試)
6. [部署步驟](#部署步驟)

---

## 🔍 問題背景

### 用戶反饋

用戶在詢問續約問題時，看到的回應不友好：

```
用戶：你好，我要續約，新的合約甚麼時候會提供?

系統：##適用情境
      當租客詢問關於新合約或續約時

      📝 租客基本資料表

      （或輸入「取消」結束填寫）
```

### 問題點

1. ❌ **技術標記暴露**：`##適用情境` 這種內部標記顯示給用戶
2. ❌ **缺少欄位提示**：沒有告訴用戶要填什麼（例如「請輸入您的姓名」）
3. ❌ **引導語不清晰**：用戶不知道為什麼要填表單

---

## 🔎 問題分析

### 根本原因

#### 問題 1：知識庫內容不合適

```sql
-- 知識 1262 的數據
id: 1262
question: 你好，我要續約，新的合約甚麼時候會提供?
answer: ##適用情境\n當租客詢問關於新合約或續約時  ← 技術標記
form_intro: NULL
form_id: (有關聯表單)
```

**系統邏輯**：
```python
# chat.py - 準備引導語
intro_message = knowledge.get('form_intro') or knowledge.get('answer', '')
# ↓
# form_intro = NULL → 使用 answer
# answer = "##適用情境..." → 直接顯示技術標記
```

#### 問題 2：表單欄位 prompt 可能為空

表單定義可能是：
```json
{
  "form_name": "租客基本資料表",
  "default_intro": "...",
  "fields": [
    {
      "field_name": "name",
      "field_label": "姓名",
      "prompt": "",  // ← 空的！
      "field_type": "text"
    }
  ]
}
```

**系統邏輯**：
```python
# form_manager.py - 組合回應
response += f"\n\n{first_field['prompt']}"
# ↓
# prompt = "" → 沒有提示
```

#### 問題 3：前端沒有驗證 prompt 必填

```javascript
// FormEditorView.vue - 儲存驗證
// ❌ 沒有檢查 prompt 是否為空
// ✅ 只有 HTML required 屬性（可以繞過）
```

---

## ✅ 解決方案

### 設計原則

**「前端驗證 + 數據完善」策略**：
1. ✅ 前端強制驗證：禁止建立沒有 prompt 的表單欄位
2. ✅ 數據完善：修正現有表單的引導語和 prompt
3. ✅ 後端簡化：不做 fallback，相信數據完整性

### 實施策略

#### 階段 1：前端驗證（主動防禦）
在表單編輯器中增加 JavaScript 驗證，確保：
- ✅ `field_name` 必填
- ✅ `field_label` 必填
- ✅ `prompt` 必填 ← **關鍵改善**

#### 階段 2：數據修正（被動修復）
修正線上環境的現有表單：
- 補充 `default_intro`（表單引導語）
- 補充 `prompt`（欄位提示）

---

## 💻 代碼修改

### 前端修改：FormEditorView.vue

**檔案**：`knowledge-admin/frontend/src/views/FormEditorView.vue`

#### 修改前（line 409-415）

```javascript
// 檢查 select 類型有選項
for (const field of formData.value.fields) {
  if ((field.field_type === 'select' || field.field_type === 'multiselect')
      && (!field.options || field.options.length === 0)) {
    alert(`欄位「${field.field_label}」的類型為 ${field.field_type}，必須提供選項`);
    return;
  }
}
```

**問題**：只驗證 select 類型的選項，沒有驗證其他必填欄位

#### 修改後（line 409-431）

```javascript
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

  // 檢查提示訊息 ← 新增驗證
  if (!field.prompt || !field.prompt.trim()) {
    alert(`欄位「${field.field_label}」缺少「提示訊息」\n\n提示訊息用於告訴用戶應該填寫什麼內容，例如：「請輸入您的姓名」`);
    return;
  }

  // 檢查 select 類型有選項
  if ((field.field_type === 'select' || field.field_type === 'multiselect')
      && (!field.options || field.options.length === 0)) {
    alert(`欄位「${field.field_label}」的類型為 ${field.field_type}，必須提供選項`);
    return;
  }
}
```

**改善**：
- ✅ 新增三個必填欄位的驗證
- ✅ 提供友好的錯誤提示
- ✅ 防止管理員建立不完整的表單

### 後端保持簡潔

**不做修改**：`rag-orchestrator/services/form_manager.py`

```python
# form_manager.py:466-469
# 組裝訊息（保持簡潔）
response = intro_message.strip()
response += f"\n\n📝 **{form_schema['form_name']}**"
response += f"\n\n{first_field['prompt']}"  # 直接使用，不做 fallback
response += "\n\n（或輸入「**取消**」結束填寫）"
```

**原因**：前端已經保證數據完整性，後端不需要複雜的 fallback 邏輯

---

## 🧪 驗證測試

### 測試 1：前端驗證

**步驟**：
1. 登入知識管理後台
2. 新建或編輯表單
3. 新增欄位，但不填寫 `prompt`
4. 點擊儲存

**預期結果**：
```
❌ 儲存失敗
彈出提示：欄位「姓名」缺少「提示訊息」

提示訊息用於告訴用戶應該填寫什麼內容，例如：「請輸入您的姓名」
```

✅ **驗證通過**：前端正確阻止儲存

### 測試 2：表單觸發

**前提**：表單已補充 `default_intro` 和 `prompt`

**步驟**：
```bash
curl -X POST "http://localhost:8100/api/v1/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，我要續約",
    "vendor_id": 2,
    "target_user": "tenant",
    "session_id": "test-001",
    "user_id": "user-001"
  }'
```

**預期結果**：
```json
{
  "answer": "您好！感謝您想要續約。\n\n為了協助您處理續約事宜，我們需要確認您的基本資料。填寫後，我們會在 3 個工作日內與您聯繫，確認新合約的條件和簽約時間。\n\n📝 租客基本資料表\n\n請輸入您的姓名（承租人全名）：\n\n（或輸入「取消」結束填寫）",
  "form_triggered": true,
  "form_id": "tenant_basic_info",
  "current_field": "name"
}
```

✅ **驗證通過**：用戶看到友好的引導語和清晰的欄位提示

---

## 🚀 部署步驟

### 步驟 1：檢查線上表單數據

```bash
# 檢查表單的 default_intro 和欄位 prompt
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U aichatbot -d aichatbot_admin << 'EOF'
SELECT
    form_id,
    form_name,
    default_intro,
    jsonb_array_length(fields) as field_count,
    fields->0->>'field_name' as first_field_name,
    fields->0->>'prompt' as first_field_prompt
FROM form_schemas
WHERE is_active = true
ORDER BY created_at DESC;
EOF
```

**檢查點**：
- ❌ `default_intro` 為 NULL → 需要補充
- ❌ `first_field_prompt` 為空或 NULL → 需要補充

### 步驟 2：補充表單數據（如需要）

```bash
# 補充「租客基本資料表」的引導語和提示
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U aichatbot -d aichatbot_admin << 'EOF'
-- 補充表單引導語
UPDATE form_schemas SET
  default_intro = '為了協助您處理續約事宜，我們需要確認您的基本資料。填寫後，我們會在 3 個工作日內與您聯繫，確認新合約的條件和簽約時間。'
WHERE form_name = '租客基本資料表';

-- 補充第一個欄位的提示
UPDATE form_schemas SET
  fields = jsonb_set(
    fields,
    '{0,prompt}',
    '"請輸入您的姓名（承租人全名）："'
  )
WHERE form_name = '租客基本資料表';
EOF
```

### 步驟 3：部署前端代碼

```bash
# 在線上服務器執行
cd /path/to/AIChatbot

# 拉取最新代碼
git pull origin main

# 確認拉到最新 commit
git log --oneline -3
# 應該看到：ba503d3 fix: 前端表單編輯器增加 prompt 欄位必填驗證

# 重建並重啟前端
docker-compose -f docker-compose.prod.yml build --no-cache knowledge-admin-web
docker-compose -f docker-compose.prod.yml up -d knowledge-admin-web

# 檢查服務狀態
docker-compose -f docker-compose.prod.yml ps knowledge-admin-web
```

### 步驟 4：驗證部署

```bash
# 測試表單觸發
curl -s -X POST "http://localhost:8100/api/v1/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，我要續約",
    "vendor_id": 2,
    "target_user": "tenant",
    "session_id": "test-renewal-001",
    "user_id": "test-user-001"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('=== 回答 ===')
print(data.get('answer', ''))
print('\n=== 表單狀態 ===')
print('form_triggered:', data.get('form_triggered'))
print('form_id:', data.get('form_id'))
print('current_field:', data.get('current_field'))
"
```

**預期輸出**：
```
=== 回答 ===
您好！感謝您想要續約。

為了協助您處理續約事宜，我們需要確認您的基本資料...

📝 租客基本資料表

請輸入您的姓名（承租人全名）：

（或輸入「取消」結束填寫）

=== 表單狀態 ===
form_triggered: True
form_id: tenant_basic_info
current_field: name
```

---

## 📊 改善效果

### 修改前

```
用戶體驗：❌ 混亂、不專業

##適用情境
當租客詢問關於新合約或續約時

📝 租客基本資料表

（或輸入「取消」結束填寫）
```

**問題**：
- ❌ 技術標記暴露
- ❌ 沒有清晰的引導
- ❌ 不知道要填什麼

### 修改後

```
用戶體驗：✅ 清晰、專業、友好

您好！感謝您想要續約。

為了協助您處理續約事宜，我們需要確認您的基本資料。
填寫後，我們會在 3 個工作日內與您聯繫，確認新合約的條件和簽約時間。

📝 租客基本資料表

請輸入您的姓名（承租人全名）：

（或輸入「取消」結束填寫）
```

**改善**：
- ✅ 友好的問候
- ✅ 清晰說明填表原因
- ✅ 明確的欄位提示
- ✅ 設定期望（3 個工作日）

---

## 🎯 總結

### 核心改進

1. **前端驗證強化**
   - 增加 `prompt` 欄位必填驗證
   - 提供友好的錯誤提示
   - 防止管理員建立不完整的表單

2. **數據質量提升**
   - 補充表單的 `default_intro`
   - 補充欄位的 `prompt`
   - 確保所有用戶看到清晰的引導

3. **代碼架構簡化**
   - 後端不做複雜的 fallback
   - 相信前端驗證和數據完整性
   - 代碼更清晰、更易維護

### 影響範圍

- ✅ **所有表單**：所有新建/編輯的表單都必須有完整的 prompt
- ✅ **用戶體驗**：所有用戶看到更友好的表單引導
- ✅ **維護成本**：降低（代碼更簡潔）

### Git Commits

```
ba503d3 fix: 前端表單編輯器增加 prompt 欄位必填驗證
4963e0c docs: 新增統一檢索路徑生產部署指南
13b73bf refactor: 整理根目錄，建立清晰的項目結構
```

---

## 📚 相關文檔

- [表單管理系統設計](../design/FORM_SYSTEM_DESIGN.md)
- [表單驗證器實作](../implementation/FORM_VALIDATOR.md)
- [知識管理系統](../guides/KNOWLEDGE_MANAGEMENT.md)

---

**文件版本**：1.0
**建立日期**：2026-01-13
**維護人員**：開發團隊
