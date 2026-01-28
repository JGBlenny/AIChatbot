# 更新日誌 - 2026-01-28

## 智能檢索系統修復與完善

### 📋 概述

在智能檢索系統初步實施後，完成了5個關鍵修復，確保系統能夠完整顯示 SOP 和知識庫的比較資訊。

---

## 🔧 修復清單

### 1. SOP 候選顯示修復

**問題**: SOP 候選項目在 debug_info 中顯示為空陣列

**根本原因**: `_build_debug_info` 函數驗證候選項目時，要求必須有 `item_name` 和 `boosted_similarity` 鍵，但構建時只提供了 `title` 鍵，導致所有候選被過濾掉。

**修復文件**: `rag-orchestrator/routers/chat.py`

**修復位置**: Lines 1636-1644

**修復內容**:
- 添加 `item_name` 鍵（用於後端驗證）
- 添加 `boosted_similarity` 鍵（必需欄位）
- 保留 `title` 鍵（用於前端顯示）

**影響**: ✅ SOP 候選現在可以正常顯示在 debug_info 中

---

### 2. SOP 路徑 comparison_metadata 傳遞修復

**問題**: 當選擇 SOP 路徑時，`comparison_metadata` 為 null

**根本原因**: `_build_orchestrator_response` 函數不接受 `decision` 參數，無法獲取比較元數據。

**修復文件**: `rag-orchestrator/routers/chat.py`

**修復內容**:

1. **函數簽名修改** (Line 852):
   - 添加 `decision: dict = None` 參數

2. **提取 comparison_metadata** (Lines 921-964):
   - 從 `decision` 中提取 `comparison_metadata`
   - 同時提取知識庫候選（即使選擇了 SOP）
   - 傳遞給 `_build_debug_info`

3. **呼叫處修改** (Line 2329):
   - 傳遞 `decision` 參數到函數

**影響**: ✅ SOP 和知識庫路徑都能正確顯示 comparison_metadata

---

### 3. 前端處理路徑映射修復

**問題**: 前端顯示 `sop_orchestrator` 為原始值，沒有中文名稱

**根本原因**: `getProcessingPathName` 函數缺少 `sop_orchestrator` 的映射

**修復文件**: `knowledge-admin/frontend/src/views/ChatTestView.vue`

**修復位置**: Line 707

**修復內容**:
```javascript
'sop_orchestrator': 'SOP 標準流程',  // 新增
```

**影響**: ✅ 前端正確顯示「SOP 標準流程」

---

### 4. 前端 LLM 策略映射修復

**問題**: 前端顯示 `orchestrated` 為原始值

**根本原因**: `getLLMStrategyName` 函數缺少 `orchestrated` 的映射

**修復文件**: `knowledge-admin/frontend/src/views/ChatTestView.vue`

**修復位置**: Line 726

**修復內容**:
```javascript
'orchestrated': 'SOP 編排執行',  // 新增
```

**影響**: ✅ 前端正確顯示「SOP 編排執行」

---

### 5. 測試知識條目配置修復

**問題**: "我想要報修" 觸發 API 超時

**根本原因**: 知識庫 ID 1267 配置了測試用的 `test_timeout` 端點

**修復方式**: SQL 更新
```sql
UPDATE knowledge_base 
SET 
    action_type = 'direct_answer',
    api_config = NULL 
WHERE id = 1267;
```

**影響**: ✅ 報修問題可以正常返回答案

---

## 📊 測試驗證

### 測試案例 1: SOP 顯著更高
- **問題**: "租金怎麼繳"
- **SOP 分數**: 0.967
- **知識庫分數**: 0.616
- **決策**: ✅ 選擇 SOP
- **顯示**: ✅ 完整的候選和比較資訊

### 測試案例 2: 知識庫顯著更高
- **問題**: "押金是多少"
- **SOP 分數**: 0.000
- **知識庫分數**: 0.842
- **決策**: ✅ 選擇知識庫
- **顯示**: ✅ 完整的候選和比較資訊

### 測試案例 3: 分數接近 + SOP 有動作
- **問題**: "我想要報修"
- **SOP 分數**: 0.929 (有表單填寫)
- **知識庫分數**: 0.960
- **差距**: 0.031 < 0.15
- **決策**: ✅ 選擇 SOP（因有業務流程）
- **顯示**: ✅ 同時顯示 SOP 和知識庫候選

---

## 📁 修改的文件

### 後端
1. `/rag-orchestrator/routers/chat.py`
   - Lines 852: 函數簽名
   - Lines 921-964: comparison_metadata 提取
   - Lines 1636-1644: SOP 候選結構
   - Line 2329: 參數傳遞

### 前端
1. `/knowledge-admin/frontend/src/views/ChatTestView.vue`
   - Line 707: 處理路徑映射
   - Line 726: LLM 策略映射

### 資料庫
1. `knowledge_base` table
   - ID 1267: 修改 action_type

---

## 🎯 系統狀態

**狀態**: ✅ 完全運作正常

**驗證項目**:
- ✅ 並行檢索 SOP 和知識庫
- ✅ 公平分數比較
- ✅ SOP 候選完整顯示
- ✅ 知識庫候選完整顯示
- ✅ comparison_metadata 兩個路徑都填充
- ✅ 前端正確顯示處理路徑
- ✅ 前端正確顯示 LLM 策略
- ✅ SOP 和知識庫嚴格隔離
- ✅ 答案合成僅在知識庫路徑觸發

---

## 📖 相關文檔

- **完整實施報告**: `docs/SMART_RETRIEVAL_IMPLEMENTATION.md`
- **測試腳本**: `/tmp/test_smart_retrieval.sh`

---

## 🔄 後續建議

1. **收集真實使用數據**: 監控不同決策類型的分佈
2. **調整閾值**: 基於實際數據優化 `SCORE_GAP_THRESHOLD` (目前 0.15)
3. **優化日誌**: 考慮添加更多決策理由的說明
4. **前端增強**: 添加分數比較的視覺化圖表

---

**修復完成時間**: 2026-01-28 下午 5:35
**修復人**: AI 助理
**驗證狀態**: ✅ 全部通過
