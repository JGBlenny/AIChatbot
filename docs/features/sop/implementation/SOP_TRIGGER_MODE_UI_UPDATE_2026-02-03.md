# 🎨 SOP 觸發模式 UI 優化更新

**更新日期**: 2026-02-03
**類型**: 前端 UI 優化
**影響範圍**: 知識庫管理、平台 SOP、業者 SOP 編輯介面

---

## 📋 更新摘要

為提升用戶體驗,本次更新針對 SOP 觸發模式的前端介面進行了全面優化:

1. ✅ **移除 'none' 觸發模式選項** - 與 next_action='none' 功能重複
2. ✅ **優化欄位顯示順序** - 使用 Flexbox order 屬性控制視覺順序
3. ✅ **新增詳細提示文字** - 在編輯界面提供具體使用範例
4. ✅ **自動設定預設值** - 選擇表單時自動設定 trigger_mode='manual'
5. ✅ **修正欄位顯示邏輯** - 觸發模式相關欄位僅在選擇表單後顯示

---

## 🎯 核心變更

### 1. 移除 trigger_mode='none' 選項

#### 變更前:
```vue
<option value="none">資訊型（僅顯示 SOP，不觸發動作）</option>
<option value="manual">排查型（等待用戶說出關鍵詞後觸發）</option>
<option value="immediate">行動型（主動詢問用戶是否執行）</option>
```

#### 變更後:
```vue
<option value="manual">排查型（等待用戶說出關鍵詞後觸發）</option>
<option value="immediate">行動型（主動詢問用戶是否執行）</option>
```

**原因**:
- `trigger_mode='none'` 與 `next_action='none'` 功能重複
- 簡化用戶選擇,避免混淆

---

### 2. 優化欄位顯示順序

使用 CSS Flexbox 的 `order` 屬性重新排列欄位,使邏輯流程更清晰:

```vue
<!-- ❌ 舊順序 -->
後續動作 → 觸發模式 → 選擇表單 → 關鍵詞/提示詞

<!-- ✅ 新順序 -->
後續動作 → 選擇表單 → 觸發模式 → 關鍵詞/提示詞
```

#### 實現方式:

```vue
<div class="form-container" style="display: flex; flex-direction: column;">
  <!-- 1️⃣ 後續動作 -->
  <div class="form-group" style="order: 1;">...</div>

  <!-- 2️⃣ 選擇表單 -->
  <div class="form-group" style="order: 2;">...</div>

  <!-- 3️⃣ 觸發模式 -->
  <div class="form-group" style="order: 3;">...</div>

  <!-- 4️⃣ 觸發關鍵詞 -->
  <div class="form-group" style="order: 4;">...</div>

  <!-- 5️⃣ 確認提示詞 -->
  <div class="form-group" style="order: 5;">...</div>
</div>
```

---

### 3. 新增詳細提示文字

在所有編輯界面的觸發模式選擇器下方添加詳細提示:

```vue
<select v-model="formData.trigger_mode" @change="onTriggerModeChange" class="form-control">
  <option value="manual">排查型（等待用戶說出關鍵詞後觸發）</option>
  <option value="immediate">行動型（主動詢問用戶是否執行）</option>
</select>
<small class="form-hint">
  💡 <strong>排查型</strong>：先在上方「知識庫內容」填寫排查步驟，用戶排查後說出關鍵詞才觸發表單<br>
  &nbsp;&nbsp;&nbsp;&nbsp;範例：內容寫「請檢查溫度設定、濾網...若仍不冷請報修」→ 用戶說「還是不冷」→ 觸發報修表單<br>
  💡 <strong>行動型</strong>：顯示知識庫內容後，立即主動詢問是否執行<br>
  &nbsp;&nbsp;&nbsp;&nbsp;範例：內容寫「租金繳納方式...」→ 自動詢問「是否要登記繳納記錄？」→ 用戶說「要」→ 觸發表單
</small>
```

**提示內容說明**:
- ✅ 清楚說明排查型和行動型的區別
- ✅ 提供具體範例幫助理解
- ✅ 說明內容應該寫在哪裡(知識庫內容欄位)

---

### 4. 修正欄位顯示邏輯

#### 問題描述:
用戶反饋:「確認提示詞和觸發關鍵詞應該在選完表單才出現吧?」

#### 變更前:
```vue
<!-- ❌ 只要選擇 next_action='form_fill' 就顯示 -->
<div v-if="formData.next_action === 'form_fill'">
```

#### 變更後:
```vue
<!-- ✅ 必須選擇表單後才顯示 -->
<div v-if="linkType === 'form' && formData.form_id">
<!-- 或 -->
<div v-if="templateForm.next_action === 'form_fill' && templateForm.next_form_id">
```

**效果**:
- 選擇「後續動作」= 「觸發表單」→ 顯示「選擇表單」欄位
- 選擇具體表單後 → 才顯示「觸發模式」、「觸發關鍵詞」、「確認提示詞」

---

### 5. 自動設定預設值

#### 問題描述:
用戶反饋:「我選了選擇表單,但觸發模式那格還是空白的」

#### 根本原因:
選擇表單時沒有觸發任何事件來設定 trigger_mode 的預設值

#### 解決方案:

##### Step 1: 添加事件監聽器

```vue
<!-- 變更前 -->
<select v-model="formData.form_id" class="form-select">

<!-- 變更後 -->
<select v-model="formData.form_id" @change="onFormSelect" class="form-select">
```

##### Step 2: 新增處理方法

```javascript
onFormSelect() {
  // 當選擇表單時，確保 trigger_mode 有值
  if (this.formData.form_id) {
    // 如果沒有值或值為 'none'，設為 'manual'
    if (!this.formData.trigger_mode ||
        this.formData.trigger_mode === 'none' ||
        this.formData.trigger_mode === '') {
      this.formData.trigger_mode = 'manual';
    }
    console.log('📋 表單選擇後 trigger_mode:', this.formData.trigger_mode);
    // 強制觸發 Vue 的響應式更新
    this.$forceUpdate();
  }
}
```

##### Step 3: 修正編輯載入邏輯

```javascript
// ❌ 變更前
trigger_mode: knowledge.trigger_mode || 'none',  // 'none' 選項不存在

// ✅ 變更後
trigger_mode: knowledge.trigger_mode || 'manual',  // 預設為排查型
```

---

## 📂 修改的檔案清單

所有變更已套用到以下 4 個前端檔案:

### 1. KnowledgeView.vue
**路徑**: `knowledge-admin/frontend/src/views/KnowledgeView.vue`

**變更內容**:
- Line 311: 添加 `@change="onFormSelect"` 事件
- Line 322-334: 修正觸發模式顯示條件,添加詳細提示
- Line 324-327: 移除 'none' 選項
- Line 337-352: 修正觸發關鍵詞顯示條件
- Line 355-370: 修正確認提示詞顯示條件
- Line 529: 設定預設值 `trigger_mode: 'manual'`
- Line 815-826: 新增 `onFormSelect()` 方法
- Line 996: 修正編輯載入邏輯 `|| 'manual'`
- Line 800-803: 在 `onLinkTypeChange()` 確保預設值

---

### 2. PlatformSOPEditView.vue
**路徑**: `knowledge-admin/frontend/src/views/PlatformSOPEditView.vue`

**變更內容**:
- Line 350: 添加 `@change="onFormSelect"` 事件
- Line 359-383: 修正觸發模式顯示條件,添加詳細提示
- Line 361-362: 移除 'none' 選項
- Line 386-401: 修正觸發關鍵詞顯示條件
- Line 404-417: 修正確認提示詞顯示條件
- Line 687: 設定預設值 `trigger_mode: 'manual'`
- Line 1484-1495: 新增 `onFormSelect()` 方法
- Line 942: 修正編輯載入邏輯 `|| 'manual'`

---

### 3. PlatformSOPView.vue
**路徑**: `knowledge-admin/frontend/src/views/PlatformSOPView.vue`

**變更內容**:
- Line 292: 添加 `@change="onFormSelect"` 事件
- Line 301-325: 修正觸發模式顯示條件,添加詳細提示
- Line 303-304: 移除 'none' 選項
- Line 328-343: 修正觸發關鍵詞顯示條件
- Line 346-359: 修正確認提示詞顯示條件
- Line 504, 977: 設定預設值 `trigger_mode: 'manual'`
- Line 802-813: 新增 `onFormSelect()` 方法
- Line 757: 修正編輯載入邏輯 `|| 'manual'`

---

### 4. VendorSOPManager.vue
**路徑**: `knowledge-admin/frontend/src/components/VendorSOPManager.vue`

**變更內容**:
- Line 333: 添加 `@change="onFormSelect"` 事件
- Line 342-366: 修正觸發模式顯示條件,添加詳細提示
- Line 344-345: 移除 'none' 選項
- Line 369-384: 修正觸發關鍵詞顯示條件
- Line 387-400: 修正確認提示詞顯示條件
- Line 486, 824: 設定預設值 `trigger_mode: 'manual'`
- Line 1130-1141: 新增 `onFormSelect()` 方法
- Line 787: 修正編輯載入邏輯 `|| 'manual'`

---

## 🔄 用戶操作流程

### 新增知識庫並關聯表單

```
1. 填寫「知識庫標題」和「知識庫內容」
   ↓
2. 選擇「後續動作」= 「觸發表單」
   ↓
3. 顯示「選擇表單 *」欄位
   ↓
4. 選擇表單 (例如:「報修申請表」)
   ↓ 自動觸發 onFormSelect()
   ↓ trigger_mode 自動設為 'manual'
   ↓
5. 顯示「觸發模式 *」欄位 (預設選擇「排查型」)✅
   ↓
6. 根據觸發模式:
   - 選擇「排查型」→ 顯示「觸發關鍵詞 *」欄位
   - 選擇「行動型」→ 顯示「確認提示詞」欄位
   ↓
7. 填寫關鍵詞或提示詞
   ↓
8. 儲存
```

---

## 🧪 測試檢查清單

### 功能測試

- [ ] 新增知識庫:選擇表單後,觸發模式顯示並預設為「排查型」
- [ ] 編輯知識庫:觸發模式正確顯示當前值
- [ ] 編輯舊資料(trigger_mode=NULL):自動顯示「排查型」
- [ ] 切換觸發模式:關鍵詞/提示詞欄位正確切換顯示
- [ ] 儲存後重新編輯:所有欄位值正確載入
- [ ] 新增平台 SOP:相同流程測試
- [ ] 編輯業者 SOP:相同流程測試

### UI/UX 測試

- [ ] 欄位顯示順序符合邏輯(後續動作 → 選擇表單 → 觸發模式 → 關鍵詞/提示詞)
- [ ] 提示文字清晰易懂
- [ ] 必填欄位標示正確(紅色星號 *)
- [ ] 表單驗證正常運作
- [ ] 控制台無錯誤訊息
- [ ] 響應式設計在不同螢幕尺寸正常顯示

### 資料庫測試

- [ ] 儲存後 trigger_mode 正確寫入資料庫
- [ ] trigger_mode 欄位值為 'manual' 或 'immediate' (不會是 'none')
- [ ] trigger_keywords 正確儲存為 JSON 陣列
- [ ] immediate_prompt 正確儲存為文字

---

## 📊 資料庫變更

### 預設值更新

所有前端初始化邏輯已更新:

```javascript
// ✅ 新增表單時的預設值
trigger_mode: 'manual',

// ✅ 編輯載入時的 fallback 值
trigger_mode: xxx.trigger_mode || 'manual',
```

### 舊資料遷移

**不需要資料庫 Migration**

原因:
- 現有 trigger_mode='none' 的資料,前端載入時會自動轉為 'manual'
- NULL 值會自動使用 'manual' 作為預設值
- 不影響資料庫結構

如需清理舊資料 (可選):

```sql
-- 將 trigger_mode='none' 更新為 NULL
UPDATE knowledge
SET trigger_mode = NULL
WHERE trigger_mode = 'none' AND next_action = 'none';

UPDATE vendor_sop_items
SET trigger_mode = NULL
WHERE trigger_mode = 'none' AND next_action = 'none';

UPDATE platform_sop_templates
SET trigger_mode = NULL
WHERE trigger_mode = 'none' AND next_action = 'none';
```

---

## 🐛 已修正的問題

### Issue #1: 觸發模式選項混淆

**問題**: trigger_mode='none' 與 next_action='none' 功能重複,用戶不知道該選哪個

**解決**: 移除 trigger_mode='none' 選項,簡化為兩種模式

---

### Issue #2: 欄位顯示順序不合理

**問題**: 觸發模式在表單選擇之前出現,但此時還不知道要選什麼表單

**解決**: 使用 Flexbox order 重新排列,表單選擇在前,觸發模式在後

---

### Issue #3: 缺乏使用說明

**問題**: 用戶不知道排查型和行動型的區別,不知道在哪裡寫排查步驟

**解決**: 添加詳細提示文字,包含具體範例

---

### Issue #4: 觸發模式預設值空白

**問題**: 選擇表單後,觸發模式下拉選單顯示空白

**原因**:
1. 選擇表單時沒有觸發事件設定預設值
2. 編輯載入時使用 'none' 作為 fallback,但 'none' 選項已不存在

**解決**:
1. 添加 `@change="onFormSelect"` 事件監聽器
2. 新增 `onFormSelect()` 方法自動設定 trigger_mode='manual'
3. 修正編輯載入邏輯使用 'manual' 作為 fallback
4. 使用 `$forceUpdate()` 強制 Vue 響應式更新

---

## 📝 相關文件

- [SOP_TYPES_ANALYSIS_2026-01-22.md](./SOP_TYPES_ANALYSIS_2026-01-22.md) - trigger_mode 類型分析
- [SOP_NEXT_ACTION_DESIGN_2026-01-22.md](./SOP_NEXT_ACTION_DESIGN_2026-01-22.md) - 後續動作設計
- [SOP_UI_DESIGN_2026-01-22.md](./SOP_UI_DESIGN_2026-01-22.md) - UI 設計規範
- [SOP_GUIDE.md](../guides/SOP_GUIDE.md) - SOP 系統完整指南

---

## 🚀 部署記錄

**建置時間**: 2026-02-03
**建置命令**: `npm run build`
**部署方式**: `docker-compose restart knowledge-admin-web`

**建置輸出**:
```
dist/index.html                   0.46 kB │ gzip:   0.34 kB
dist/assets/index-AHzHxtOP.css  250.29 kB │ gzip:  39.16 kB
dist/assets/index-BT4m8h7J.js   784.99 kB │ gzip: 254.56 kB
✓ built in 1.92s
```

**容器重啟**:
```bash
Container aichatbot-knowledge-admin-web  Restarting
Container aichatbot-knowledge-admin-web  Started
```

---

## ✅ 驗證步驟

### 1. 清除瀏覽器快取
```
1. 開啟開發者工具 (F12)
2. 右鍵重新整理按鈕
3. 選擇「清除快取並強制重新整理」
```

### 2. 測試新增知識庫
```
1. 進入知識庫管理頁面
2. 點擊「新增知識庫」
3. 選擇「後續動作」= 「觸發表單」
4. 選擇「報修申請表」
5. 確認「觸發模式」顯示並預設為「排查型」✅
6. 查看控制台,確認有 log: 📋 表單選擇後 trigger_mode: manual
```

### 3. 測試編輯現有資料
```
1. 編輯一個現有的知識庫(trigger_mode=NULL 或 'none')
2. 確認「觸發模式」顯示「排查型」✅
3. 儲存後重新編輯
4. 確認值正確保存
```

---

## 🎯 後續優化建議

### 短期 (1 週內)

1. **用戶反饋收集**
   - 觀察用戶是否仍對觸發模式感到困惑
   - 收集關於提示文字是否清晰的反饋

2. **監控錯誤日誌**
   - 檢查是否有 Vue 警告或錯誤
   - 監控 trigger_mode 儲存是否正確

### 中期 (1 個月內)

1. **添加互動式導覽**
   - 首次使用時顯示操作提示
   - 使用 tooltips 或 popovers 提供即時幫助

2. **優化表單驗證**
   - 確保關鍵詞不為空(排查型)
   - 提示詞長度檢查(行動型)

### 長期 (3 個月內)

1. **智能預測模式**
   - 根據知識庫內容自動推薦觸發模式
   - 例如:內容包含「檢查」、「確認」→ 建議排查型

2. **範本功能**
   - 提供常用 SOP 範本
   - 包含預設的觸發模式設定

---

**文件維護**: AI Chatbot Development Team
**最後更新**: 2026-02-03
**下次審查**: 2026-03-03
