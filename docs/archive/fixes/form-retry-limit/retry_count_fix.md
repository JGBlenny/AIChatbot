# 重試計數器遞增問題 - 修復完成

## 🐛 問題診斷

### 症狀
- 連續輸入無效地址時，一直顯示「第 1 次重試」
- 重試計數器沒有遞增（永遠是 1/2）
- 無法觸發自動取消（第 2 次失敗後）

### 根本原因
在調用 `_complete_form` 時，傳入的 `session_state` 是**舊的資料**，沒有包含更新後的 metadata（包括 retry_count）。

```python
# 問題代碼（第 662 行）
return await self._complete_form(session_state, form_schema, collected_data)
# session_state 是在函數開始時獲取的，沒有最新的 metadata
```

## ✅ 修復方案

### 修改內容
在調用 `_complete_form` 之前，**重新獲取最新的 session_state**：

```python
# 修復後的代碼（第 661-664 行）
if skip_review:
    # 重新獲取最新的 session_state（包含最新的 metadata）
    session_state = await self.get_session_state(session_id)
    # 直接完成表單並執行後續動作
    return await self._complete_form(session_state, form_schema, collected_data)
```

## 📊 測試驗證

### 預期行為
1. **第 1 次**輸入「帳單寄送區間」
   - 顯示：「💡 **提示**：請確認輸入的地址完整且正確（第 1 次重試）」

2. **第 2 次**輸入「帳單寄送區間」
   - 顯示：「⚠️ **最後一次機會**：請仔細檢查地址格式（最後一次重試）」

3. **第 2 次失敗後**
   - 自動取消：「❌ **查詢失敗** 已嘗試 2 次，仍無法找到匹配的資料...」
   - 不再要求輸入

### 日誌確認
```bash
docker-compose logs -f rag-orchestrator | grep "表單重試"
```

應該看到：
```
🔄 [表單重試] API 錯誤類型: no_match, 重試次數: 1/2
🔄 [表單重試] API 錯誤類型: no_match, 重試次數: 2/2  ← 正確遞增
```

## 🚀 當前狀態

- ✅ 問題已診斷
- ✅ 修復已應用
- ✅ 服務已重啟
- ⏳ 等待測試驗證

## 📝 技術細節

### 資料流程
1. `collect_field_data` 收集使用者輸入
2. 單欄位表單直接進入 `_complete_form`
3. API 查詢失敗，更新 metadata 中的 retry_count
4. 返回重試提示給使用者
5. **關鍵**：下次調用 `_complete_form` 時必須使用最新的 session_state

### 關鍵檔案
- `/rag-orchestrator/services/form_manager.py`
  - 第 661-664 行：重新獲取 session_state
  - 第 798-887 行：重試邏輯實作