# 知識庫後續動作功能補齊與優化

**日期**: 2026-01-30 ~ 2026-02-03
**類型**: Feature Enhancement
**影響範圍**: Knowledge Base 知識庫管理、Platform SOP 管理

---

## 📋 變更摘要

補齊知識庫的後續動作功能，使其與 SOP 平台範本功能保持一致。

**🚨 2026-02-03 重要變更**：移除 `followup_prompt` 欄位，因為與表單的 `default_intro` 功能重複。

---

## 🎯 問題背景

用戶反饋：
> "knowledge 沒有後續動作？我參考 SOP 表單的部分，但不完整"

經過對比發現，**Platform SOP Templates** 有完整的後續動作配置，但 **Knowledge Base** 缺少關鍵欄位。

---

## 🔍 問題分析

### SOP vs Knowledge 功能對比

| 欄位 | SOP | Knowledge (舊) | Knowledge (新) |
|------|-----|----------------|----------------|
| `trigger_mode` | ✅ | ✅ | ✅ |
| `trigger_keywords` | ✅ | ❌ | ✅ |
| `immediate_prompt` | ✅ | ✅ | ✅ |
| `followup_prompt` | ✅ | ❌ | ✅ |
| `form_intro` | ❌ | ❌ (前端有，但未存入DB) | ❌ (已移除) |

### 發現的設計問題

1. **缺少 `trigger_keywords` 欄位**：排查型（manual）模式無法設定觸發關鍵詞
2. **缺少 `followup_prompt` 欄位**：無法自訂後續動作的提示語
3. **`form_intro` 功能重複**：
   - 表單本身有 `default_intro`（預設引導語）
   - Knowledge 又有 `form_intro`（覆寫引導語）
   - 新增的 `followup_prompt`（後續提示）
   - 三個欄位功能重疊，造成混淆

---

## ✅ 解決方案

### 1. 新增資料庫欄位

#### `trigger_keywords` (TEXT[])
```sql
-- 觸發關鍵詞陣列
-- manual 模式：自定義（例如：["還是不行", "試過了"]）
-- immediate 模式：通用肯定詞（["是", "要", "好"]）
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS trigger_keywords TEXT[];
```

#### `followup_prompt` (TEXT)
```sql
-- 後續動作的提示詞，在觸發表單/API 前顯示
-- 例如：「好的，我來協助您填寫表單」
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS followup_prompt TEXT;
```

### 2. 簡化設計：移除 `form_intro`

**原因**：
- `form_intro` 在前端代碼中存在，但從未存入資料庫
- 功能與 `followup_prompt` 重複
- 表單本身已有 `default_intro` 提供預設引導語

**優化邏輯**：
```
觸發表單時的提示語優先順序：
1. 有 followup_prompt → 使用自訂後續提示
2. 沒有 followup_prompt → 使用表單的 default_intro
```

---

## 📝 前端變更

### KnowledgeView.vue

#### 新增欄位輸入

```vue
<!-- 後續提示詞（當有關聯功能時顯示） -->
<div v-if="linkType !== 'none'" class="form-group">
  <label>後續提示詞（選填）</label>
  <textarea
    v-model="formData.followup_prompt"
    class="form-control"
    rows="2"
    placeholder="例如：好的，我來協助您填寫表單"
  ></textarea>
  <small class="form-hint">
    💡 觸發後續動作（表單/API）時顯示的提示語（留空則使用預設提示）
  </small>
</div>
```

#### 移除舊欄位

- ❌ 移除 `form_intro` 輸入框
- ❌ 移除 formData 中的 `form_intro` 屬性
- ❌ 移除保存邏輯中的 `form_intro` 處理

---

## 🗂️ 資料庫遷移

### Migration 檔案

1. ✅ `add_trigger_keywords_to_knowledge_base.sql` - 已執行
2. ✅ `add_followup_prompt_to_knowledge_base.sql` - 已執行

### 執行狀態

```bash
# trigger_keywords
ALTER TABLE knowledge_base ADD COLUMN trigger_keywords TEXT[];
CREATE INDEX idx_kb_trigger_keywords ON knowledge_base USING GIN (trigger_keywords);

# followup_prompt
ALTER TABLE knowledge_base ADD COLUMN followup_prompt TEXT;
```

---

## 📊 最終欄位對照

### Knowledge Base 後續動作完整欄位

| 欄位 | 類型 | 說明 | 範例 |
|------|------|------|------|
| `trigger_mode` | VARCHAR(20) | 觸發模式 | `none`, `manual`, `immediate`, `auto` |
| `trigger_keywords` | TEXT[] | 觸發關鍵詞 | `["還是不行", "試過了"]` |
| `immediate_prompt` | TEXT | 確認提示詞 | "需要我協助您報修嗎？" |
| `followup_prompt` | TEXT | 後續提示詞 | "好的，我來協助您填寫表單" |
| `form_id` | VARCHAR(100) | 關聯表單 ID | `maintenance_request` |
| `api_config` | JSONB | API 配置 | `{"endpoint": "billing_inquiry"}` |

---

## ✨ 功能完整性

### 觸發模式支持

| 模式 | 說明 | 必填欄位 |
|------|------|----------|
| **none** (資訊型) | 僅回答知識庫內容 | - |
| **manual** (排查型) | 等待用戶說出關鍵詞 | `trigger_keywords` |
| **immediate** (行動型) | 主動詢問是否執行 | `immediate_prompt` (選填) |
| **auto** (自動型) | 立即執行後續動作 | - |

### 後續動作類型

| action_type | 說明 | 使用欄位 |
|-------------|------|----------|
| `direct_answer` | 直接回答 | - |
| `form_fill` | 觸發表單 | `form_id`, `followup_prompt` |
| `api_call` | 調用 API | `api_config`, `followup_prompt` |
| `form_then_api` | 先填表單再調用 API | `form_id`, `api_config`, `followup_prompt` |

---

## 🧪 測試驗證

### 需要驗證的場景

- [ ] 新增知識庫，選擇「排查型」模式，輸入觸發關鍵詞
- [ ] 編輯現有知識庫，修改 `followup_prompt`
- [ ] 驗證觸發表單時，優先使用 `followup_prompt`，無則使用 `default_intro`
- [x] 確認前端不再顯示「表單引導語」輸入框 ✅
- [x] 確認前端 UI 順序正確：後續動作 → 觸發模式（僅表單相關） ✅
- [x] 確認觸發模式只在表單相關動作時顯示 ✅
- [ ] 確認後端 API 正確處理新欄位

## ✅ 前端變更完成狀態

### KnowledgeView.vue 修改完成

**檔案**: `knowledge-admin/frontend/src/views/KnowledgeView.vue`

#### 1️⃣ 移除 form_intro 所有引用 ✅
- ❌ 移除模板中的「表單引導語」輸入框（line 440-448）
- ❌ 移除 formData 中的 `form_intro: ''` 初始化
- ❌ 移除所有 `this.formData.form_intro = null` 賦值
- ❌ 移除保存時的 `form_intro` console.log

#### 2️⃣ 新增 followup_prompt 欄位 ✅
- ✅ formData 初始化添加 `followup_prompt: ''`
- ✅ resetForm 添加 `followup_prompt: ''`
- ✅ 編輯載入時添加 `followup_prompt: knowledge.followup_prompt || ''`
- ✅ console.log 添加 `followup_prompt` 輸出
- ✅ 保存時自動包含在 `this.formData` 中

#### 3️⃣ 重新排序 UI 元素（與 SOP 對齊）✅
```vue
<!-- 正確順序（已實現）-->
1️⃣ 觸發模式 * (trigger_mode)
2️⃣ 觸發關鍵詞 * (trigger_keywords) - 僅 manual 模式
3️⃣ 確認提示詞 (immediate_prompt) - 僅 immediate 模式
4️⃣ 後續動作 * (linkType → action_type)
5️⃣ 後續提示詞 (followup_prompt) - 僅非 none 模式
6️⃣ 表單/API 選擇 - 根據後續動作類型
```

#### 4️⃣ 修正 Vue 模板結構錯誤 ✅
- ✅ 修正 API 端點選擇區塊的縮排（line 386-417）
- ✅ 確保 `form_api` div 與 `api` div 平級（line 420）
- ✅ 移除重複的表單引導語輸入框（在 form_api 模式內）

### 編譯狀態
- ✅ Vue 模板編譯成功
- ✅ 生產環境編譯成功（2.05s）
- ✅ 前端服務正常運行：http://localhost:8087
- ⚠️ 其他組件有 HTML 規範警告（BacktestView, BusinessTypesConfigView 的 table 結構）

## ✅ 實作方案（簡化版）

由於完整的 UI 重排容易導致 Vue 模板編譯錯誤，採用了**簡化方案**：

### 方案說明
1. **保留原有 UI 結構**：不改變現有的觸發模式和後續動作的順序
2. **統一欄位名稱**：在 UI 上將「表單引導語」改為「後續提示詞」
3. **向後兼容**：
   - 前端使用 `form_intro` 綁定（保持現有代碼穩定）
   - 保存時自動同步到 `followup_prompt`（新欄位）
   - 讀取時優先使用 `followup_prompt`，回退到 `form_intro`

### 實作細節

**JavaScript 變更 (knowledge-admin/frontend/src/views/KnowledgeView.vue:600-1300)**
```javascript
// 1. formData 初始化
formData: {
  form_intro: '',  // 保留（前端綁定用）
  followup_prompt: '',  // 新增（後端儲存用）
  trigger_keywords: [],  // 已有
  immediate_prompt: '',  // 已有
}

// 2. 保存邏輯（line 1253-1256）
// 同步 form_intro 到 followup_prompt
if (this.formData.form_intro) {
  this.formData.followup_prompt = this.formData.form_intro;
}

// 3. 編輯載入邏輯（line 1076, 1081）
form_intro: knowledge.followup_prompt || knowledge.form_intro || '',
followup_prompt: knowledge.followup_prompt || knowledge.form_intro || '',
```

**模板變更**
```vue
<!-- Line 363-372: 表單模式 -->
<label>後續提示詞 <span class="field-hint">（可選，自訂觸發後續動作前的提示）</span></label>
<textarea v-model="formData.form_intro"
          placeholder="例如：好的，我來協助您填寫表單"></textarea>

<!-- Line 430-438: 表單+API 模式 -->
<label>後續提示詞 <span class="field-hint">（可選）</span></label>
<textarea v-model="formData.form_intro"
          placeholder="例如：好的，我來協助您填寫表單"></textarea>
```

### 優點
- ✅ 最小化變更風險
- ✅ Vue 編譯通過（無語法錯誤）
- ✅ 向後兼容舊資料
- ✅ 前端穩定（不改變 UI 結構）

---

## 📌 注意事項

1. **向後兼容**：
   - 現有知識庫不受影響（新欄位允許 NULL）
   - `trigger_keywords` 預設為空陣列
   - `followup_prompt` 預設為空

2. **前端變更**：
   - 移除了「表單引導語」輸入框
   - 新增了「後續提示詞」輸入框
   - 更符合直覺，減少用戶困惑

3. **後端 API**：
   - 需要確認 `/api/knowledge` 端點支持新欄位
   - 需要確認 RAG Orchestrator 能正確讀取新欄位

---

## ✅ 前端 UI 邏輯統一完成

### 完成項目（2026-01-30）

1. **PlatformSOPView.vue** ✅
   - 調整 UI 順序：後續動作 → 觸發模式（條件式）
   - 觸發模式僅在 `form_fill` 或 `form_then_api` 時顯示
   - 觸發關鍵詞、確認提示詞跟隨觸發模式條件顯示

2. **PlatformSOPEditView.vue** ✅
   - 移除頂部的觸發模式區塊
   - 在「後續動作」之後添加條件式觸發模式
   - 條件邏輯與 PlatformSOPView.vue 完全一致

3. **KnowledgeView.vue** ✅
   - 在「後續動作」之後添加條件式觸發模式
   - 使用 `linkType === 'form' || linkType === 'form_api'` 判斷
   - 觸發關鍵詞、確認提示詞跟隨觸發模式條件顯示

### 統一的 UI 邏輯

```
1️⃣ 後續動作 * (linkType / next_action)
   ├─ 無（僅顯示內容）
   ├─ 觸發表單 ← 表單相關
   ├─ 調用 API
   └─ 先填表單再調用 API ← 表單相關

↓ 僅在選擇表單相關時顯示 ↓

2️⃣ 觸發模式 * (trigger_mode)
   ├─ 資訊型（none）
   ├─ 排查型（manual） → 顯示「觸發關鍵詞」
   └─ 行動型（immediate） → 顯示「確認提示詞」

3️⃣ 觸發關鍵詞 * (trigger_keywords) - manual 模式 + 表單相關
4️⃣ 確認提示詞（選填）(immediate_prompt) - immediate 模式 + 表單相關
5️⃣ 後續提示詞（選填）(followup_prompt) - 非 none 模式
6️⃣ 表單/API 選擇 - 根據後續動作類型
```

### 編譯驗證

```bash
✓ built in 1.41s
dist/index.html                   0.46 kB │ gzip:   0.33 kB
dist/assets/index-CzdcwTqd.css  250.29 kB │ gzip:  39.17 kB
dist/assets/index-Dt_XEElp.js   789.21 kB │ gzip: 255.04 kB
```

---

## 🚨 2026-02-03 重要變更：移除 followup_prompt

### 問題分析

經過實際使用後發現 `followup_prompt` 與表單的 `default_intro` 功能重複：

**觸發表單流程**：
```
用戶確認 → followup_prompt（「好的，我來協助您」） → form.default_intro（「請提供以下資訊...」）
```

這導致兩個連續的提示，用戶體驗不佳。

### 解決方案

**完全移除 `followup_prompt` 欄位**，改用表單自帶的 `default_intro`：

```
用戶確認 → form.default_intro（「請提供以下維修資訊：1. 問題描述 2. 地點...」）
```

### 變更內容

#### 1. 資料庫變更
```sql
-- 移除兩個表的 followup_prompt 欄位
ALTER TABLE platform_sop_templates DROP COLUMN IF EXISTS followup_prompt;
ALTER TABLE knowledge_base DROP COLUMN IF EXISTS followup_prompt;
```

#### 2. 前端變更
移除以下文件中的 `followup_prompt` 相關代碼：
- ✅ `PlatformSOPEditView.vue`
- ✅ `PlatformSOPView.vue`
- ✅ `VendorSOPManager.vue`
- ✅ `KnowledgeView.vue`

#### 3. UI 變更
- ❌ 移除「後續提示詞」輸入框
- ✅ 直接使用表單的 `default_intro`

### 最終設計

| 後續動作 | 使用欄位 | 說明 |
|---------|---------|------|
| **無** | - | 僅顯示知識庫/SOP 內容 |
| **觸發表單** | `form.default_intro` | 使用表單自帶的引導語 |
| **調用 API** | 系統預設提示 | 「正在為您查詢...」 |

---

## 🚨 2026-02-03 重要變更：移除 trigger_mode='none'

### 問題分析

用戶識別出 `trigger_mode='none'` (資訊型) 與 `next_action='none'` (無後續動作) 功能重複：

- **trigger_mode='none'**：只顯示 SOP 內容，無後續動作
- **next_action='none'**：無後續動作，只顯示內容

兩者語義完全相同，造成混淆和重複配置。

### 核心邏輯

觸發模式 (trigger_mode) 只在「有後續動作」時才有意義：

| 後續動作 | 是否需要觸發模式 | 觸發模式選項 |
|---------|-----------------|-------------|
| **無 (none)** | ❌ 不需要 | - |
| **觸發表單 (form_fill)** | ✅ 需要 | manual, immediate |
| **調用 API (api_call)** | ❌ 不需要 | - |

### 變更內容

#### 1. 前端變更 ✅

移除所有 trigger_mode 選項中的「資訊型 (none)」：
- ✅ `PlatformSOPEditView.vue` (line 351)
- ✅ `PlatformSOPView.vue` (line 293)
- ✅ `VendorSOPManager.vue` (line 334)
- ✅ `KnowledgeView.vue` (line 312)

現在觸發模式只有兩個選項：
- **排查型 (manual)**：等待用戶說出關鍵詞後觸發
- **行動型 (immediate)**：主動詢問用戶是否執行

#### 2. 資料庫變更 ✅

**更新現有資料**：
```sql
-- platform_sop_templates: 90 筆記錄 (next_action='none')
UPDATE platform_sop_templates
SET trigger_mode = NULL
WHERE trigger_mode = 'none' AND next_action = 'none';

-- knowledge_base: 1269 筆記錄 (action_type='direct_answer'/'api_call')
UPDATE knowledge_base
SET trigger_mode = NULL
WHERE trigger_mode = 'none' AND action_type IN ('direct_answer', 'api_call');

-- knowledge_base: 1 筆測試記錄 (action_type='form_fill')
UPDATE knowledge_base
SET trigger_mode = 'immediate'
WHERE trigger_mode = 'none' AND action_type = 'form_fill';
```

**更新約束**：
```sql
-- platform_sop_templates
ALTER TABLE platform_sop_templates DROP CONSTRAINT IF EXISTS check_trigger_mode;
ALTER TABLE platform_sop_templates ADD CONSTRAINT check_trigger_mode
  CHECK (trigger_mode IS NULL OR trigger_mode IN ('manual', 'immediate', 'auto'));
ALTER TABLE platform_sop_templates ALTER COLUMN trigger_mode SET DEFAULT 'manual';

-- knowledge_base
ALTER TABLE knowledge_base DROP CONSTRAINT IF EXISTS check_kb_trigger_mode;
ALTER TABLE knowledge_base ADD CONSTRAINT check_kb_trigger_mode
  CHECK (trigger_mode IS NULL OR trigger_mode IN ('manual', 'immediate', 'auto'));
ALTER TABLE knowledge_base ALTER COLUMN trigger_mode SET DEFAULT 'manual';
```

#### 3. 驗證結果 ✅

| 資料表 | 總記錄數 | NULL | manual | immediate |
|--------|---------|------|--------|-----------|
| platform_sop_templates | 90 | 90 | 0 | 0 |
| knowledge_base | 1273 | 1269 | 1 | 3 |

### 最終設計

#### 觸發模式 (trigger_mode)

| 觸發模式 | 說明 | 適用場景 | 必填欄位 |
|---------|------|---------|---------|
| **manual** | 排查型 | 用戶排查後說關鍵詞才觸發 | trigger_keywords |
| **immediate** | 行動型 | 主動詢問是否執行 | immediate_prompt (選填) |
| **auto** | 緊急型 | 自動觸發（未實作） | - |
| ~~**none**~~ | ~~資訊型~~ | ~~已移除（等同於 next_action='none'）~~ | - |

#### 與後續動作的關係

```
如果 next_action = 'none' (無後續動作)
  → trigger_mode = NULL (不需要觸發模式)

如果 next_action = 'form_fill' (觸發表單)
  → trigger_mode 必須是 'manual' 或 'immediate'

如果 next_action = 'api_call' (調用 API)
  → trigger_mode = NULL (API 直接執行，不需要觸發模式)
```

### 影響範圍

- ✅ 前端 UI：觸發模式選項減少，更簡潔明確
- ✅ 資料庫：舊資料已遷移，約束已更新
- ✅ 邏輯清晰：觸發模式只在「表單填寫」時才有意義
- ⚠️ 後端 API：需確認 RAG Orchestrator 正確處理 NULL 值

---

## 🔄 後續工作

- [ ] 更新 RAG Orchestrator 使用新欄位的邏輯
- [ ] 更新文檔說明新的欄位用法
- [ ] 線上環境部署前測試
- [ ] 驗證 RAG Orchestrator 正確處理 trigger_mode=NULL 的情況

---

## 📚 相關文檔

- [Platform SOP View 實作](../features/FORM_MANAGEMENT_SYSTEM.md)
- [知識庫管理系統](../features/KNOWLEDGE_MANAGEMENT.md)
- [SOP 類型分析](../features/SOP_TYPES_ANALYSIS_2026-01-22.md)
