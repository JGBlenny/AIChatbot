# 對話邏輯修正報告 - 2026-01-24

**日期**：2026-01-24
**修正內容**：對話流程優先級修正、高質量過濾順序調整、PAUSED 狀態支援
**影響範圍**：`rag-orchestrator/routers/chat.py`
**Git Commit**：待提交

---

## 📋 修正總覽

| 問題編號 | 問題描述 | 嚴重程度 | 狀態 |
|---------|---------|---------|------|
| 問題 1 | action_type 檢查在高質量過濾之前，可能觸發低質量知識的表單 | 🔴 高 | ✅ 已修正 |
| 問題 2 | PAUSED 狀態未在主流程中處理 | 🟡 中 | ✅ 已修正 |
| 問題 3 | action_type 降級邏輯不明確 | 🟡 中 | ✅ 已修正 |

---

## 🔍 問題 1：action_type 檢查順序錯誤

### 問題描述

在 `_build_knowledge_response()` 函數中，**action_type 檢查發生在高質量過濾之前**，導致低質量知識（similarity < 0.8）也可能觸發表單或 API 調用。

### 影響場景

```
用戶：「冷氣壞了」
→ 知識庫檢索（閾值 0.55）
→ 找到知識 A: similarity=0.6, action_type='form_fill'
→ ❌ 直接觸發表單（跳過高質量過濾）
→ 低質量知識觸發表單，可能不相關
```

### 修正前邏輯

```python
# Lines 1007-1072 (修正前)
if knowledge_list:
    best_knowledge = knowledge_list[0]  # 使用未過濾的知識
    action_type = best_knowledge.get('action_type')

    if action_type == 'form_fill':
        return trigger_form()  # 直接返回，跳過高質量過濾

# Lines 1078-1094 (永遠不會執行到這裡)
filtered_knowledge_list = [k for k in knowledge_list if k['similarity'] >= 0.8]
if not filtered_knowledge_list:
    return _handle_no_knowledge_found()
```

### 修正後邏輯

```python
# ⭐ 步驟 1：高質量過濾（先過濾）
high_quality_threshold = 0.8
filtered_knowledge_list = [k for k in knowledge_list if k['similarity'] >= high_quality_threshold]

if not filtered_knowledge_list:
    return await _handle_no_knowledge_found()

# ⭐ 步驟 2：檢查 action_type（使用過濾後的知識）
best_knowledge = filtered_knowledge_list[0]
action_type = best_knowledge.get('action_type')
print(f"🎯 [action_type] 知識 {best_knowledge['id']} 的 action_type: {action_type}, similarity: {best_knowledge.get('similarity', 0):.3f}")

if action_type == 'form_fill':
    # 確保只有高質量知識才會觸發表單
    ...

# ⭐ 步驟 3：direct_answer 流程
...
```

### 修正效果

✅ **高質量保證**：只有 similarity >= 0.8 的知識才會觸發表單/API
✅ **流程清晰**：步驟 1 過濾 → 步驟 2 檢查 action_type → 步驟 3 生成答案
✅ **日誌改進**：在日誌中顯示 similarity 分數供追蹤

---

## 🔍 問題 2：PAUSED 狀態未處理

### 問題描述

表單的 **PAUSED 狀態**（用於 SOP `form_then_api` 場景）未在主流程的表單會話檢查中處理。

### 影響場景

```
SOP form_then_api 流程：
1. 用戶觸發 SOP → 顯示資訊
2. 用戶確認 → 開始填表單
3. 表單填到一半 → 調用 pause_form()，狀態 = PAUSED
4. 用戶繼續輸入 → ❌ PAUSED 狀態未被處理
   → 系統誤認為新問題
   → 走知識庫檢索流程
   → 表單資料遺失
```

### 修正前代碼

```python
# Line 1746 (修正前)
if session_state and session_state['state'] in ['COLLECTING', 'DIGRESSION']:
    # 處理收集狀態
    ...
# ❌ PAUSED 狀態不在檢查範圍內
```

### 修正後代碼

```python
# Line 1746 (修正後)
if session_state and session_state['state'] in ['COLLECTING', 'DIGRESSION', 'PAUSED']:
    # 處理收集狀態（包括 PAUSED）
    # PAUSED 狀態：表單暫停（例如 SOP form_then_api），用戶訊息可能是要恢復表單
    print(f"📋 檢測到進行中的表單會話（{session_state['form_id']}, 狀態: {session_state['state']}），使用表單收集流程")
    ...
```

### 修正效果

✅ **PAUSED 狀態支援**：SOP form_then_api 場景中暫停的表單可以正確處理
✅ **日誌改進**：顯示當前狀態供追蹤
✅ **表單完整性**：確保暫停的表單可以恢復，資料不會遺失

---

## 🔍 問題 3：action_type 降級邏輯不明確

### 問題描述

當 action_type 為 `form_fill`、`api_call` 或 `form_then_api` 但缺少必要參數時，只有 **print 警告訊息**，沒有明確設置降級行為。

### 影響場景

```
知識：action_type='form_fill', 但 form_id=NULL
→ print("⚠️ 缺少 form_id，降級為 direct_answer")
→ ❌ action_type 仍然是 'form_fill'
→ 繼續執行後續代碼
→ 可能出現未預期的錯誤
```

### 修正前代碼

```python
# Lines 1017-1018 (修正前)
if not form_id:
    print(f"⚠️  action_type={action_type} 但缺少 form_id，降級為 direct_answer")
    # ❌ 沒有明確降級，action_type 仍是 'form_fill'
```

### 修正後代碼

```python
# Lines 1035-1040 (修正後)
if not form_id:
    print(f"⚠️  action_type={action_type} 但缺少 form_id，降級為 direct_answer")
    action_type = 'direct_answer'  # ✅ 明確降級
elif not request.session_id or not request.user_id:
    print(f"⚠️  知識 {best_knowledge['id']} 需要表單，但缺少 session_id 或 user_id，降級為 direct_answer")
    action_type = 'direct_answer'  # ✅ 明確降級
```

### 所有降級場景

| action_type | 缺少參數 | 降級行為 |
|------------|---------|---------|
| `form_fill` | `form_id` | 降級為 `direct_answer` |
| `form_fill` | `session_id` 或 `user_id` | 降級為 `direct_answer` |
| `api_call` | `api_config` | 降級為 `direct_answer` |
| `form_then_api` | `form_id` | 降級為 `direct_answer` |
| `form_then_api` | `session_id` | 降級為 `direct_answer` |

### 修正效果

✅ **明確降級**：所有降級場景都明確設置 `action_type = 'direct_answer'`
✅ **避免錯誤**：防止因缺少參數導致的未預期錯誤
✅ **流程清晰**：降級後繼續執行 direct_answer 流程

---

## 📊 修正統計

### 代碼修改

| 文件 | 修改行數 | 說明 |
|-----|---------|------|
| `rag-orchestrator/routers/chat.py` | 約 100 行重組 | 調整 `_build_knowledge_response()` 邏輯順序 |
| `rag-orchestrator/routers/chat.py` | +1 行 | 加入 PAUSED 狀態檢查 |
| `rag-orchestrator/routers/chat.py` | +5 行 | 明確降級邏輯 |

### 影響分析

| 影響範圍 | 影響程度 | 說明 |
|---------|---------|------|
| 表單觸發邏輯 | 🔴 高 | 確保只有高質量知識才會觸發表單 |
| SOP form_then_api | 🟡 中 | PAUSED 狀態現在可以正確處理 |
| 錯誤處理 | 🟢 低 | 降級邏輯更明確，減少潛在錯誤 |

---

## 🎯 修正後的完整流程

```
用戶訊息
    ↓
Step 0: 表單會話檢查
    ├─ REVIEWING → 確認/取消/編輯
    ├─ EDITING → 收集編輯值
    ├─ COLLECTING/DIGRESSION/PAUSED → 收集欄位 ⭐ 新增 PAUSED
    └─ 無表單 ↓

Step 1: 驗證業者
Step 2: 緩存檢查
Step 3: 意圖分類
Step 3.5: SOP Orchestrator
    ↓
Step 6: 知識庫檢索（閾值 0.55）
    ├─ 無知識 → Step 8
    └─ 有知識 ↓

Step 9: 構建知識回應
    │
    ├─ ⭐ 步驟 1：高質量過濾（閾值 0.8）
    │   └─ 無高質量知識 → Step 8
    │
    ├─ ⭐ 步驟 2：檢查 action_type（使用 filtered_knowledge_list[0]）
    │   ├─ form_fill
    │   │   ├─ 有完整參數 → 觸發表單 ✅
    │   │   └─ 缺少參數 → 降級為 direct_answer ⭐
    │   ├─ api_call
    │   │   ├─ 有 api_config → 調用 API ✅
    │   │   └─ 缺少 api_config → 降級為 direct_answer ⭐
    │   ├─ form_then_api
    │   │   ├─ 有完整參數 → 觸發表單 + API ✅
    │   │   └─ 缺少參數 → 降級為 direct_answer ⭐
    │   └─ direct_answer ↓
    │
    └─ ⭐ 步驟 3：direct_answer 流程
        ├─ 信心度評估
        ├─ LLM 優化答案
        └─ 返回優化答案 ✅

Step 8: 無知識處理
    ├─ 參數答案 ✅
    └─ 兜底回應 + 記錄場景 ✅
```

---

## 🧪 驗證方法

### 1. 高質量過濾驗證

```bash
# 測試低質量知識不會觸發表單
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "測試問題",
    "vendor_id": 1,
    "session_id": "test_quality_filter",
    "user_id": "test_user"
  }'

# 檢查日誌
docker-compose logs rag-orchestrator | grep "高質量過濾"
```

### 2. PAUSED 狀態驗證

```bash
# 觸發 SOP form_then_api 流程
# 1. 觸發 SOP
# 2. 確認開始填表單
# 3. 暫停表單（PAUSED）
# 4. 繼續輸入 → 應該正確處理

# 檢查日誌
docker-compose logs rag-orchestrator | grep "狀態: PAUSED"
```

### 3. 降級邏輯驗證

```bash
# 檢查降級日誌
docker-compose logs rag-orchestrator | grep "降級為 direct_answer"
```

---

## 📝 部署步驟

### 1. 重建服務

```bash
cd /Users/lenny/jgb/AIChatbot
docker-compose build rag-orchestrator
docker-compose restart rag-orchestrator
```

### 2. 驗證啟動

```bash
docker-compose logs rag-orchestrator | tail -25
```

### 3. 健康檢查

```bash
curl http://localhost:8100/api/v1/health
```

---

## 🔄 回滾方案

如果出現問題，可以回滾到修正前的版本：

```bash
# 1. 查看提交歷史
git log --oneline -5

# 2. 回滾代碼
git checkout <previous_commit> rag-orchestrator/routers/chat.py

# 3. 重建服務
docker-compose build rag-orchestrator
docker-compose restart rag-orchestrator
```

---

## 📚 相關文檔

- **對話流程完整分析**：[CHAT_FLOW_ANALYSIS_2026-01-24.md](../analysis/CHAT_FLOW_ANALYSIS_2026-01-24.md)
- **表單狀態機文檔**：[FORM_STATE_MACHINE.md](../features/FORM_STATE_MACHINE.md)
- **SOP Next Action 文檔**：[SOP_NEXT_ACTION.md](../features/SOP_NEXT_ACTION.md)

---

## ✅ 修正檢查清單

- [x] 問題 1：調整 action_type 檢查順序
- [x] 問題 2：加入 PAUSED 狀態處理
- [x] 問題 3：明確 action_type 降級邏輯
- [x] 重建並重啟服務
- [x] 驗證服務啟動成功
- [x] 創建修正文檔
- [ ] 提交 Git commit
- [ ] 部署到生產環境

---

**文檔維護人員**：Claude
**最後更新**：2026-01-24
**狀態**：✅ 修正完成，待提交
