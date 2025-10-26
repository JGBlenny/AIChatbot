# 回測優化跳轉流程設計

## 📋 需求分析

### 當前系統能力
- ✅ KnowledgeView.vue 支持 URL 參數：
  - `?ids=1,2,3` - 批量查詢多個知識 ID
  - `?search=關鍵字` - 搜尋關鍵字
- ✅ BacktestView.vue 有基本的 optimizeKnowledge 函數
- ✅ 回測結果包含：test_question, actual_intent, source_ids, source_count, quality_overall

### 失敗案例分類（基於 Run #11 數據）

#### 類型 A：完全無知識來源（3/5 cases）
```
問題：我想養寵物可以嗎？/ 我可以養寵物嗎 / 可以養寵物嗎
意圖：寵物飼養
source_ids：空
source_count：0
原因：知識庫缺少該主題內容
```
**優化動作**：新增知識 → 引導到"新增知識"頁面，預填問題和意圖

#### 類型 B：有知識但質量不佳（2/5 cases）
```
問題：客服電話是什麼？
意圖：服務說明
source_ids：222,223,224,225,226
source_count：5
quality_overall：0.4/5.0
原因：檢索到5個知識，但內容不相關或不完整
```
**優化動作**：修改知識 → 批量查詢這5個知識，逐一檢查和修改

```
問題：我的合約什麼時候到期？
意圖：租約查詢
source_ids：243
source_count：1
quality_overall：0.6/5.0
原因：檢索到的知識內容不完整
```
**優化動作**：補充知識 → 查看 ID 243，補充完整信息

## 🎯 優化策略設計

### 策略 1：智能路由判斷

```javascript
function optimizeKnowledge(result) {
  const hasSource = result.source_ids && result.source_ids.trim();
  const sourceCount = result.source_count || 0;
  const qualityScore = result.quality_overall || result.score || 0;
  const intent = result.actual_intent;
  const question = result.test_question;

  if (!hasSource) {
    // 類型 A：無知識來源 → 引導新增
    handleNoKnowledgeCase(question, intent);
  } else if (sourceCount > 1) {
    // 類型 B.1：多個知識來源 → 批量查看
    handleMultipleSourcesCase(result.source_ids, question, intent);
  } else {
    // 類型 B.2：單個知識來源 → 直接編輯
    handleSingleSourceCase(result.source_ids, question, intent);
  }
}
```

### 策略 2：詳細實現方案

#### A. 無知識來源 → 新增知識流程

**跳轉目標**：知識庫頁面（KnowledgeView）
**攜帶信息**：
- question：測試問題
- intent：實際意圖
- action：create（表示要新增）

**URL 示例**：
```
/#/?action=create&question=我可以養寵物嗎&intent=寵物飼養
```

**需要修改 KnowledgeView.vue**：
1. mounted 中檢測 action=create 參數
2. 自動打開新增 Modal
3. 預填 question 到 question_summary
4. 根據 intent 自動選擇對應的意圖

#### B. 多個知識來源 → 批量查詢流程

**跳轉目標**：知識庫頁面（KnowledgeView）
**攜帶信息**：
- ids：逗號分隔的知識 ID 列表
- context：測試問題（用於高亮顯示）

**URL 示例**：
```
/#/?ids=222,223,224,225,226&context=客服電話是什麼？
```

**當前已支持**：
- ✅ ids 參數批量查詢
- ⚠️ context 參數需要新增（用於在知識列表中高亮顯示相關性）

#### C. 單個知識來源 → 直接編輯流程

**跳轉目標**：知識庫頁面（KnowledgeView）
**攜帶信息**：
- ids：單個知識 ID
- edit：true（自動打開編輯）

**URL 示例**：
```
/#/?ids=243&edit=true
```

**需要修改 KnowledgeView.vue**：
1. 檢測 edit=true 參數
2. 自動打開編輯 Modal
3. 載入對應知識內容

## 📊 UI/UX 改進建議

### 1. 優化按鈕文案
根據失敗類型顯示不同的按鈕文案：

```javascript
getOptimizeButtonText(result) {
  if (!result.source_ids) {
    return '➕ 新增知識';  // 無知識來源
  } else if (result.source_count > 1) {
    return `📦 查看 ${result.source_count} 個知識`;  // 多個來源
  } else {
    return '✏️ 編輯知識';  // 單個來源
  }
}
```

### 2. 優化提示信息
使用更友好的提示方式，取代 alert：

```javascript
// 使用 Toast 或內聯提示
this.$notify({
  type: 'info',
  title: '🎯 優化提示',
  message: '已為您定位到相關知識，請檢查並優化'
});
```

### 3. 添加上下文高亮
在知識庫頁面顯示回測問題，幫助用戶理解優化目標：

```vue
<!-- 在 KnowledgeView.vue 頂部添加 -->
<div v-if="backtestContext" class="backtest-context-banner">
  🎯 正在優化回測失敗案例：
  <strong>{{ backtestContext }}</strong>
  <button @click="clearContext">✕</button>
</div>
```

## 🔧 實施步驟

### Phase 1：改進 BacktestView.vue 的 optimizeKnowledge 函數（優先）
1. 實現智能路由判斷邏輯
2. 使用批量 IDs 參數（?ids=）替代單個 search
3. 根據場景攜帶不同參數（action, edit, context）
4. 改進按鈕文案動態顯示

### Phase 2：增強 KnowledgeView.vue 的參數處理（建議）
1. 支持 action=create 自動打開新增 Modal
2. 支持 edit=true 自動打開編輯 Modal
3. 支持 context 參數顯示上下文提示橫幅
4. 自動根據 intent 參數預選意圖

### Phase 3：UI/UX 優化（可選）
1. 用 Notification/Toast 替代 alert
2. 添加上下文高亮顯示
3. 在知識編輯頁面顯示回測問題引用
4. 添加"優化完成"反饋機制

## 💡 示例場景

### 場景 1：養寵物問題（無知識）
```
用戶點擊 ⚡ 優化
→ 跳轉到 /#/?action=create&question=我可以養寵物嗎&intent=寵物飼養
→ 自動打開新增 Modal
→ question_summary 預填：我可以養寵物嗎
→ 意圖自動選擇：寵物飼養
→ 用戶填寫答案並保存
```

### 場景 2：客服電話問題（多個來源）
```
用戶點擊 ⚡ 優化
→ 跳轉到 /#/?ids=222,223,224,225,226&context=客服電話是什麼？
→ 頁面顯示這5個知識
→ 頂部顯示：🎯 正在優化回測失敗案例：客服電話是什麼？
→ 用戶逐一檢查，發現 ID 225 不相關，刪除或修改
→ 發現缺少直接回答客服電話的知識，新增
```

### 場景 3：合約到期問題（單個來源）
```
用戶點擊 ⚡ 優化
→ 跳轉到 /#/?ids=243&edit=true
→ 自動打開編輯 Modal，載入 ID 243 的知識
→ 用戶發現內容不完整，補充詳細信息
→ 保存後系統提示：✅ 知識已更新
```

## 📈 預期效果

1. **效率提升**：
   - 從"點擊優化"到"開始編輯"縮短到 1-2 步
   - 減少用戶思考和搜尋時間

2. **準確性提升**：
   - 自動定位到相關知識，減少誤操作
   - 批量查詢讓用戶完整了解現有知識

3. **體驗提升**：
   - 智能引導不同優化動作
   - 上下文信息始終可見
   - 減少警告彈窗干擾

## 🎯 建議實施順序

1. **立即實施（高優先級）**：
   - Phase 1 全部：改進 optimizeKnowledge 函數使用批量 IDs

2. **近期實施（中優先級）**：
   - Phase 2 部分：支持 action=create 和 edit=true 參數

3. **長期優化（低優先級）**：
   - Phase 3：UI/UX 細節優化
