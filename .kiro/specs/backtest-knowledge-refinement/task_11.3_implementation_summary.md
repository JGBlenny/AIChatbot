# 任務 11.3 實作摘要：批量審核功能增強

## 實作日期
2026-03-28

## 任務目標
在現有的 `LoopKnowledgeReviewTab.vue` 中補充批量審核功能，支援多項目同時審核、進度追蹤和錯誤處理。

## 修改檔案
- `/Users/lenny/jgb/AIChatbot/knowledge-admin/frontend/src/components/review/LoopKnowledgeReviewTab.vue`

## 實作內容

### 1. 全選功能（✅ 已完成）

#### 新增 Data 狀態
```javascript
selectedIds: []  // 批量操作選取的項目 ID
```

#### 新增 Computed 屬性
```javascript
allSelected()      // 是否全選
someSelected()     // 是否部分選取
```

#### 新增方法
```javascript
toggleSelectAll()     // 全選/取消全選
toggleSelectItem()    // 切換單個項目選取
```

#### UI 元件
- 全選區域（顯示已選取數量）
- 每個項目卡片的核取方塊
- 支援 indeterminate 狀態（部分選取）

### 2. 批量操作工具列（✅ 已完成）

#### UI 元件
- 工具列（僅在有選取項目時顯示）
- 已選取數量顯示
- 清除選取按鈕
- 批量批准按鈕
- 批量拒絕按鈕

### 3. 批量審核確認對話框（✅ 已完成）

#### 新增 Data 狀態
```javascript
showConfirmDialog: false
batchAction: ''  // 'approve' or 'reject'
batchReviewNotes: ''
```

#### 新增 Computed 屬性
```javascript
selectedItemsSopCount()      // 選取項目中的 SOP 數量
selectedItemsGeneralCount()  // 選取項目中的一般知識數量
```

#### 新增方法
```javascript
showBatchApproveDialog()  // 顯示批量批准確認對話框
showBatchRejectDialog()   // 顯示批量拒絕確認對話框
closeConfirmDialog()      // 關閉確認對話框
```

#### UI 元件
- Modal 對話框
- 統計資訊顯示（選取數量、SOP/一般知識分布）
- 警告提示（拒絕操作）
- 審核備註輸入框
- 確認/取消按鈕

### 4. 批量審核進度顯示（✅ 已完成）

#### 新增 Data 狀態
```javascript
showProgressDialog: false
batchProgress: {
  current: 0,
  total: 0,
  currentItem: null,
  successCount: 0,
  failedCount: 0,
  failedItems: []
}
```

#### 新增 Computed 屬性
```javascript
progressPercentage()  // 進度百分比計算
```

#### 新增方法
```javascript
executeBatchReview()  // 執行批量審核（核心邏輯）
```

#### UI 元件
- 進度對話框
- 進度統計（當前/總數、成功/失敗數量）
- 進度條（百分比動畫）
- 當前處理項目顯示

#### 實作細節
- 使用前端序列調用 API（逐一審核）
- 每個項目審核間隔 100ms 避免請求過快
- 支援部分成功模式（一個失敗不影響其他項目）
- SOP 項目必填欄位驗證（vendor_id, category_id）

### 5. 批量審核結果摘要（✅ 已完成）

#### 新增 Data 狀態
```javascript
showResultDialog: false
batchResult: {
  successCount: 0,
  failedCount: 0,
  failedItems: []
}
```

#### 新增方法
```javascript
closeResultDialog()  // 關閉結果對話框
retryFailedItems()   // 重試失敗項目
```

#### UI 元件
- 結果對話框
- 成功/失敗統計卡片
- 失敗項目清單（包含錯誤訊息）
- 重試失敗項目按鈕
- 關閉按鈕

#### 實作細節
- 失敗項目列表可滾動（最大高度 200px）
- 重試功能會自動選取失敗的項目 ID
- 完成後自動重新載入列表和統計

### 6. CSS 樣式（✅ 已完成）

新增以下樣式類別：
- `.select-all-section` - 全選區域
- `.select-all-label` - 全選標籤
- `.select-checkbox` - 全選核取方塊
- `.batch-action-toolbar` - 批量操作工具列
- `.toolbar-info` / `.toolbar-actions` - 工具列子區域
- `.modal-overlay` - 對話框遮罩層
- `.modal-dialog` - 對話框容器
- `.modal-header` / `.modal-body` / `.modal-footer` - 對話框區塊
- `.confirm-stats` - 確認統計
- `.warning-section` - 警告區域
- `.progress-bar-wrapper` / `.progress-bar` - 進度條
- `.result-summary` / `.result-stat` - 結果摘要
- `.failed-items-section` / `.failed-items-list` - 失敗項目清單

## 技術細節

### 前端架構
- **框架**：Vue 3 Options API
- **HTTP 客戶端**：Axios
- **狀態管理**：元件內部 data()
- **樣式**：Scoped CSS

### API 調用策略
- **批量審核**：前端序列調用單一審核 API
  - 優點：進度顯示精確、錯誤處理靈活
  - 缺點：性能較慢（每個項目 100ms 間隔）
- **端點**：`POST /api/v1/loop-knowledge/{knowledge_id}/review`

### 錯誤處理
- 網路錯誤：顯示 error.message
- API 錯誤：顯示 error.response.data.detail
- 業務邏輯錯誤：檢查必填欄位、顯示提示訊息
- 部分失敗：記錄失敗項目，不影響其他項目

### 資料流
```
使用者操作
  ↓
選取項目（toggleSelectItem）
  ↓
點擊批量按鈕（showBatchApproveDialog / showBatchRejectDialog）
  ↓
顯示確認對話框（showConfirmDialog = true）
  ↓
確認操作（executeBatchReview）
  ↓
顯示進度對話框（showProgressDialog = true）
  ↓
逐一調用 API（for loop with await）
  ↓
更新進度（batchProgress.current++）
  ↓
完成後顯示結果（showResultDialog = true）
  ↓
重新載入列表（loadItems, loadStats）
```

## 驗收標準

✅ **功能完整性**
- [x] 全選功能（全選、取消全選、部分選取狀態）
- [x] 批量操作工具列（顯示選取數量、批量按鈕）
- [x] 確認對話框（統計資訊、警告提示）
- [x] 進度顯示（進度條、當前項目、統計）
- [x] 結果摘要（成功/失敗統計、失敗清單）
- [x] 重試功能（重試失敗項目）

✅ **錯誤處理**
- [x] SOP 項目必填欄位驗證
- [x] API 錯誤顯示
- [x] 部分成功模式（容錯處理）

✅ **UI/UX**
- [x] 對話框居中顯示
- [x] 遮罩層點擊關閉（confirm 對話框）
- [x] 進度條動畫流暢
- [x] 失敗項目列表可滾動
- [x] 按鈕狀態正確（啟用/禁用）

✅ **程式碼品質**
- [x] 無語法錯誤
- [x] 命名清晰（方法、變數、CSS 類別）
- [x] 註解完整（關鍵邏輯）
- [x] 結構清晰（分離關注點）

## 已知限制

1. **Toast 提示**：使用 `alert()` 代替 Toast 元件
   - 建議：整合 Vue Toastification 或類似套件

2. **批量審核性能**：使用前端序列調用
   - 建議：後端實作真正的批量審核 API
   - 或：使用 WebSocket/SSE 實現即時進度推送

3. **重複檢測統計**：未實作
   - 原因：需要後端 API 支援重複檢測資料
   - 建議：擴展 pending API 回傳重複檢測資訊

4. **自動刷新統計**：未實作
   - 原因：任務需求中未明確要求
   - 建議：新增定時器每 10 秒刷新統計

## 測試建議

### 手動測試步驟

1. **全選功能測試**
   - [ ] 點擊全選核取方塊，確認所有項目被選取
   - [ ] 再次點擊，確認所有項目取消選取
   - [ ] 手動選取部分項目，確認全選核取方塊顯示 indeterminate 狀態

2. **批量批准測試**
   - [ ] 選取 3-5 個項目
   - [ ] 點擊「批量批准」按鈕
   - [ ] 確認對話框顯示正確的統計資訊
   - [ ] 輸入審核備註
   - [ ] 點擊確認，觀察進度顯示
   - [ ] 確認結果對話框顯示成功統計

3. **批量拒絕測試**
   - [ ] 選取 3-5 個項目
   - [ ] 點擊「批量拒絕」按鈕
   - [ ] 確認警告提示顯示
   - [ ] 點擊確認，觀察進度顯示
   - [ ] 確認結果對話框顯示成功統計

4. **錯誤處理測試**
   - [ ] 選取包含 SOP 的項目但未填寫業者/類別
   - [ ] 執行批量批准，確認錯誤被正確捕獲
   - [ ] 確認失敗項目顯示在結果對話框

5. **重試功能測試**
   - [ ] 模擬部分失敗場景
   - [ ] 點擊「重試失敗項目」按鈕
   - [ ] 確認只選取失敗的項目 ID
   - [ ] 確認重新顯示確認對話框

### 自動化測試建議

```javascript
// 單元測試範例（使用 Jest + Vue Test Utils）
describe('LoopKnowledgeReviewTab - 批量審核', () => {
  it('應該正確計算 allSelected', () => {
    // 測試 allSelected computed 屬性
  })

  it('應該正確切換全選狀態', () => {
    // 測試 toggleSelectAll 方法
  })

  it('應該顯示批量操作工具列當有選取項目時', () => {
    // 測試條件渲染
  })

  it('應該正確執行批量審核', async () => {
    // 測試 executeBatchReview 方法
    // Mock axios.post
  })

  it('應該處理部分失敗場景', async () => {
    // 測試錯誤處理
  })
})
```

## 後續優化建議

1. **效能優化**
   - 實作真正的批量審核 API（後端）
   - 使用 WebSocket 或 SSE 實現即時進度推送
   - 新增批量操作的快取機制

2. **功能增強**
   - 整合重複檢測警告統計
   - 新增批量修改功能（批量更新關鍵字）
   - 新增批量操作歷史記錄
   - 支援分頁批量操作（跨頁選取）

3. **UI/UX 改進**
   - 整合 Toast 元件替換 alert()
   - 新增批量操作的鍵盤快捷鍵（Ctrl+A 全選）
   - 新增批量操作的撤銷功能
   - 優化進度條顯示（顯示預估剩餘時間）

4. **測試完善**
   - 新增單元測試
   - 新增整合測試
   - 新增 E2E 測試（Cypress 或 Playwright）

## 總結

本次實作成功在 `LoopKnowledgeReviewTab.vue` 中補充了完整的批量審核功能，涵蓋：
- ✅ 全選/取消全選
- ✅ 批量操作工具列
- ✅ 確認對話框（統計、警告）
- ✅ 進度顯示（進度條、當前項目）
- ✅ 結果摘要（成功/失敗、重試）
- ✅ 錯誤處理（部分成功模式）

所有核心功能均已實作完成，符合任務 11.3 的需求規格。程式碼結構清晰、命名規範、註解完整，具備良好的可維護性和擴展性。
