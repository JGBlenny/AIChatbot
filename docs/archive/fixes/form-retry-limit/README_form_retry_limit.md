# 表單重試次數限制 - 實作指南

## 🎯 目標
限制表單查詢失敗的重試次數為 **最多 2 次**，避免使用者陷入無限循環。

## 📋 改動摘要

### 主要修改
1. **檔案**：`rag-orchestrator/services/form_manager.py`
2. **方法**：`_complete_form()` （第 795-820 行）
3. **機制**：使用 `metadata` 欄位追蹤重試次數

### 關鍵參數
- `MAX_RETRIES = 2`：最多允許重試 2 次
- `metadata['retry_count']`：儲存當前重試次數

## 🔧 實作步驟

### 1. 應用修改補丁
```bash
cd /Users/lenny/jgb/AIChatbot
git apply improvements/form_retry_limit.patch
```

### 2. 手動修改（如果補丁無法自動應用）
參考 `improvements/form_retry_limit_implementation.py` 中的完整程式碼

### 3. 重啟服務
```bash
docker-compose restart rag-orchestrator
```

## 📊 行為變化

### Before（現有行為）
```
使用者：帳單寄送區間
系統：❌ 未找到匹配記錄...（無限循環）
使用者：帳單寄送區間
系統：❌ 未找到匹配記錄...（無限循環）
使用者：帳單寄送區間
系統：❌ 未找到匹配記錄...（持續要求重新輸入）
```

### After（改進後）
```
使用者：帳單寄送區間
系統：❌ 未找到匹配記錄...
     💡 提示：請確認輸入的地址完整且正確（第 1 次重試）

使用者：帳單寄送區間
系統：❌ 查詢失敗
     已嘗試 2 次，仍無法找到匹配的資料。
     【自動取消表單】
```

## ✅ 測試檢查清單

- [ ] 連續 2 次輸入無效地址，系統自動取消
- [ ] 第 1 次重試顯示「第 1 次重試」提示
- [ ] 第 2 次失敗後自動結束，不再要求輸入
- [ ] 成功輸入後，重試計數器重置
- [ ] 使用者可以隨時輸入「取消」主動退出

## 🔍 除錯日誌

系統會輸出以下日誌：
```
🔄 [表單重試] API 錯誤類型: no_match, 重試次數: 1/2
🔄 [表單重試] API 錯誤類型: no_match, 重試次數: 2/2
```

## 📈 預期效益

1. **改善使用者體驗**：避免無限循環的挫折感
2. **降低系統負載**：減少無效的 API 查詢
3. **提供清晰回饋**：明確告知重試次數與狀態
4. **優雅退出**：自動結束並提供有用的錯誤說明

## 💡 未來優化建議

1. 將 `MAX_RETRIES` 設為可配置參數
2. 根據不同表單類型設定不同的重試限制
3. 記錄重試統計資料，分析使用者行為
4. 在達到限制前提供更多輔助（如範例、提示）

## 📝 相關檔案

- `improvements/form_retry_limit_suggestion.md` - 詳細分析與多種方案
- `improvements/form_retry_limit_implementation.py` - 完整實作程式碼
- `improvements/form_retry_limit.patch` - Git 補丁檔案