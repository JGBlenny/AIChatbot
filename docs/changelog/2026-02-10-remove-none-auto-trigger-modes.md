# 移除 none 和 auto 觸發模式更新

## 更新日期
2026-02-10

## 更新摘要
移除了 SOP 系統中的 `none` 和 `auto` 觸發模式，簡化系統邏輯，僅保留 `manual`（排查型）和 `immediate`（行動型）兩種觸發模式。

## 更新原因

### 1. none 觸發模式的冗餘性
- `trigger_mode='none'` 與 `next_action='none'` 功能重疊
- 若要建立純資訊型 SOP，只需將 `next_action` 設為 `'none'` 即可
- 不需要額外的觸發模式來表示「不觸發」

### 2. auto 觸發模式未實作
- 經檢查，`auto` 模式聲稱的「系統智能判斷」功能從未實作
- 實際上只是資料庫中的預設值，沒有對應的智能判斷邏輯
- 移除未實作的功能以避免混淆

## 技術變更

### 後端更新

#### 1. sop_trigger_handler.py
- 移除 `TriggerMode.NONE` 和 `TriggerMode.AUTO` 枚舉值
- 刪除 `_handle_auto_mode` 函數
- 更新處理邏輯以支援 `null` trigger_mode

#### 2. vendors.py
- 將 `trigger_mode` 改為 `Optional[str]`，預設值為 `None`
- 更新 API 模型驗證邏輯

#### 3. chat.py
- 移除 `trigger_mode == 'none'` 的檢查
- 移除 `trigger_mode` 的 `'auto'` 預設值
- 當 `trigger_mode` 為 `null` 或未定義時，降級為 `direct_answer`

### 前端更新

#### VendorSOPManager.vue
- 移除觸發模式選項中的 `'none'` 和 `'auto'`
- 更新 `getTriggerModeLabel` 函數
- 將預設值從預設字串改為 `null`
- 新增「請選擇觸發模式...」選項

### 資料庫更新
- 89 筆 `trigger_mode='none'` 的記錄已更新為 `NULL`
- 1 筆 `trigger_mode='auto'` 的記錄已更新為 `'manual'`

## 影響範圍

### 對現有功能的影響
- **無影響**：純資訊型 SOP 仍可透過設定 `next_action='none'` 實現
- **無影響**：現有的 `manual` 和 `immediate` 模式繼續正常運作

### 對使用者的影響
- 使用者介面更簡潔，選項更清晰
- 移除了未實作的 `auto` 選項，避免誤導
- 觸發模式現在是可選的（當 `next_action='none'` 時不需要）

## 觸發模式對照表

| 舊系統 | 新系統 | 說明 |
|--------|--------|------|
| `trigger_mode='none'` | `trigger_mode=null` + `next_action='none'` | 純資訊型 SOP |
| `trigger_mode='manual'` | `trigger_mode='manual'` | 排查型（等待關鍵詞觸發） |
| `trigger_mode='immediate'` | `trigger_mode='immediate'` | 行動型（主動詢問） |
| `trigger_mode='auto'` | `trigger_mode='manual'` | 預設轉為排查型 |

## 相關檔案
- `/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/sop_trigger_handler.py`
- `/Users/lenny/jgb/AIChatbot/rag-orchestrator/routers/vendors.py`
- `/Users/lenny/jgb/AIChatbot/rag-orchestrator/routers/chat.py`
- `/Users/lenny/jgb/AIChatbot/knowledge-admin/frontend/src/components/VendorSOPManager.vue`
- `/Users/lenny/jgb/AIChatbot/docs/user-guides/VENDOR_SOP_USER_GUIDE.md`
- `/Users/lenny/jgb/AIChatbot/docs/architecture/SYSTEM_ARCHITECTURE.md`

## 測試建議
1. 確認純資訊型 SOP（`next_action='none'`）正常運作
2. 測試 `manual` 模式的關鍵詞觸發功能
3. 測試 `immediate` 模式的主動詢問功能
4. 確認前端介面正確顯示選項
5. 驗證資料庫更新後的資料完整性