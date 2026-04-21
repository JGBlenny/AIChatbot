# 前端頁面使用說明

## ✅ 已完成功能

### 1. 知識庫管理頁面 (`/`)
**URL**: http://localhost:8080/

**功能**:
- 查看所有知識庫
- 新增/編輯/刪除知識
- 搜尋和過濾
- Markdown 編輯器預覽

---

### 2. 建議意圖審核頁面 (`/suggested-intents`)
**URL**: http://localhost:8080/suggested-intents

**功能**:
- 查看 OpenAI 建議的新意圖
- 顯示觸發問題
- 顯示相關性分數
- 顯示 OpenAI 推理說明
- 顯示建議頻率
- 採納建議（自動建立新意圖）
- 拒絕建議
- 查看統計資訊（待審核、已採納、已拒絕、已合併）

**使用流程**:
1. 當使用者提問 unclear 問題時，系統自動分析
2. 如果 OpenAI 判斷與業務相關（分數 ≥ 0.7），記錄為建議
3. 管理員在此頁面審核
4. 點擊「✓ 採納」→ 輸入審核備註 → 自動建立新意圖
5. 點擊「✗ 拒絕」→ 輸入拒絕原因 → 標記為已拒絕

**注意**:
- 採納後會自動建立新意圖並重載 IntentClassifier
- 相同問題會累加頻率
- 高頻建議表示多人遇到相同問題

---

### 3. 業務範圍配置頁面 (`/business-scope`)
**URL**: http://localhost:8080/business-scope

**功能**:
- 查看所有業務範圍配置
- 切換業務範圍（內部/外部）
- 編輯業務描述
- 編輯範例問題
- 編輯範例意圖
- 自訂 OpenAI 判斷 Prompt

**預設配置**:
- **external (包租代管業者)**: 當前使用 ✓
  - 用途: 外部客戶使用
  - 業務範圍: 租約管理、繳費、維修、退租、合約、設備、物件資訊

- **internal (系統商)**:
  - 用途: 內部使用
  - 業務範圍: 系統功能、技術支援

**切換業務範圍**:
1. 點擊「切換使用」按鈕
2. 確認後，IntentSuggestionEngine 自動重載
3. 之後的 unclear 問題將使用新的業務範圍判斷

---

## 🧪 測試流程

### 測試 1: 觸發新意圖建議
在 Chat API 提問一個業務相關但不在現有意圖中的問題：

```bash
curl -X POST http://localhost:8100/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "請問可以提前兩個月退租嗎？需要付違約金嗎？",
    "user_id": "test_user"
  }'
```

如果問題觸發 unclear 且 OpenAI 判斷相關，會記錄建議。

### 測試 2: 審核建議意圖
1. 開啟 http://localhost:8080/suggested-intents
2. 查看待審核的建議
3. 點擊「✓ 採納」
4. 輸入審核備註（如「常見問題，值得新增」）
5. 確認後自動建立新意圖

### 測試 3: 業務範圍配置
1. 開啟 http://localhost:8080/business-scope
2. 查看當前使用的業務範圍（external）
3. 點擊「✏️ 編輯配置」
4. 修改業務描述、範例問題
5. 儲存後生效

---

## 🎨 頁面截圖說明

### 導航選單
- 位於頁面頂部
- 3 個選項卡：知識庫、建議審核、業務範圍
- 當前頁面高亮顯示

### 建議意圖審核頁面
- 統計卡片：待審核、已採納、已拒絕、已合併
- 卡片佈局：每個建議一個卡片
- 顯示資訊：名稱、類型、描述、關鍵字、觸發問題、相關性分數、頻率、OpenAI推理
- 操作按鈕：採納、拒絕（僅待審核狀態）

### 業務範圍配置頁面
- 卡片佈局：每個業務範圍一個卡片
- 當前使用的範圍有藍色邊框和 ✓ 標記
- 顯示資訊：範圍名稱、類型、業務描述、範例問題、範例意圖、自訂Prompt
- 操作按鈕：編輯配置、切換使用

---

## 🔗 API 端點對應

### 建議意圖審核頁面
- GET http://localhost:8100/api/v1/suggested-intents
- POST http://localhost:8100/api/v1/suggested-intents/{id}/approve
- POST http://localhost:8100/api/v1/suggested-intents/{id}/reject
- GET http://localhost:8100/api/v1/suggested-intents/stats

### 業務範圍配置頁面
- GET http://localhost:8100/api/v1/business-scope
- PUT http://localhost:8100/api/v1/business-scope/{scope_name}
- POST http://localhost:8100/api/v1/business-scope/switch

---

## 💡 使用技巧

1. **意圖優先級**: 數字越大優先級越高，當多個意圖匹配時優先使用高優先級
2. **信心度閾值**: 建議 knowledge 類型用 0.80，data_query 和 action 用 0.75
3. **業務範圍描述**: 越詳細越好，OpenAI 會根據這個判斷問題是否相關
4. **建議頻率**: 頻率高的建議表示多人遇到，應優先處理
5. **重載配置**: 修改意圖後系統會自動重載，不需要手動重啟

---

## 🚀 快速開始

1. **開啟主頁面**: http://localhost:8080/
2. **點擊「建議審核」**: 查看 OpenAI 建議的新意圖
3. **點擊「業務範圍」**: 查看和配置業務範圍

---

## 🎯 完成狀態

✅ Phase A: 資料庫 + 基礎服務 (100%)
✅ Phase B: 新意圖發現機制 (100%)
✅ Phase C: 前端 UI (100%)

**整體完成度: 100%**

所有功能已實作完成並可在瀏覽器中使用！
