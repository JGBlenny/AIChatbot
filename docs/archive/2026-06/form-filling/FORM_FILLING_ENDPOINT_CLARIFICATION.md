# 表單填寫功能 - 端點整合說明

> 釐清現有的對話流程端點，確認表單功能應該整合到哪裡

---

## 📋 現有對話端點盤查

### ❌ 已廢棄端點（不要碰）

**端點**：`POST /api/v1/chat`

**狀態**：已於 **2025-10-21 移除**

**移除原因**：
- 功能被更強大的端點替代
- 前端未使用此端點
- 無外部系統依賴

**相關文件**：
- `docs/archive/completion_reports/CHAT_ENDPOINT_REMOVAL_AUDIT.md`（盤查報告）
- `docs/archive/api/CHAT_API_MIGRATION_GUIDE.md`（遷移指南）

**代碼痕跡**：
```python
# routers/chat.py 第 1238 行
# ========================================
# /api/v1/chat 端點已於 2025-10-21 移除
# ========================================
#
# 移除原因：功能已由更強大的端點替代
#
# 已移除的項目：
# - class ChatRequest
# - class ChatResponse
# - POST /chat 端點函數
```

---

### ✅ 現在活躍的端點

#### 1. **主要端點**：`POST /api/v1/message`

**檔案**：`rag-orchestrator/routers/chat.py`

**Request 模型**：`VendorChatRequest`
```python
class VendorChatRequest(BaseModel):
    message: str                    # 使用者訊息
    vendor_id: int                  # 業者 ID
    target_user: Optional[str]      # 目標用戶角色
    mode: Optional[str]             # b2c / b2b
    session_id: Optional[str]       # 會話 ID ← 表單會用到這個
    user_id: Optional[str]          # 使用者 ID
    top_k: int = 5
    include_sources: bool = True
    include_debug_info: bool = False
```

**Response 模型**：`VendorChatResponse`
```python
class VendorChatResponse(BaseModel):
    answer: str
    intent_name: Optional[str]
    confidence: Optional[float]
    sources: Optional[List[KnowledgeSource]]
    vendor_id: int
    mode: str
    session_id: Optional[str]       # ← 會返回 session_id
    timestamp: str
    # ... 其他欄位
```

**功能特點**：
- ✅ 支持多業者（vendor_id）
- ✅ 支持 SOP 整合
- ✅ 支持業者參數配置
- ✅ 支持多 Intent 檢索
- ✅ 有 session_id 欄位（表單需要）
- ✅ 有緩存機制

**處理流程**：
```
1. 驗證業者
2. 檢查緩存
3. 意圖分類
4. SOP 檢索（優先）
5. unclear 意圖處理
6. 知識庫檢索
7. LLM 優化
8. 返回答案
```

---

#### 2. **流式端點**：`POST /api/v1/chat/stream` ❌ **已移除**

**檔案**：`rag-orchestrator/routers/chat_stream.py`（已刪除）

**移除狀態**：已完全移除（原暫時停用於 2026-01-09）

**廢棄原因**：
- 系統統一使用 `/message` 端點處理對話
- 減少雙端點維護複雜度
- 前端主要使用 `/message` 端點
- 流式輸出功能暫時不是優先需求

**Request 模型**：`ChatStreamRequest`
```python
class ChatStreamRequest(BaseModel):
    question: str                   # 問題
    vendor_id: int                  # 業者 ID
    target_user: Optional[str]
    mode: Optional[str]
    user_id: Optional[str]
    context: Optional[Dict]         # 上下文（但沒有 session_id）
```

**Response 格式**：Server-Sent Events (SSE)
```
event: start
data: {"message": "開始處理問題..."}

event: intent
data: {"intent_type": "租屋申請", "confidence": 0.95}

event: search
data: {"doc_count": 5}

event: answer_chunk
data: {"chunk": "好的"}

event: answer_chunk
data: {"chunk": "，我來協助您"}

event: done
data: {"processing_time": 1250}
```

**功能特點**：
- ✅ 提供即時反饋（逐字輸出）
- ✅ 更好的用戶體驗
- ⚠️ **沒有 session_id 欄位**（無法追蹤表單會話）
- ❌ **暫時廢棄**（代碼保留，前端不再調用）

---

## 🎯 表單功能應該整合到哪裡？

### 推薦：整合到 `POST /api/v1/message`

**理由**：

1. ✅ **有 session_id 欄位**
   - Request 和 Response 都支持 session_id
   - 可以追蹤表單會話狀態

2. ✅ **是主要端點**
   - 代碼最完整、最穩定
   - 有完整的緩存、SOP、知識庫處理流程

3. ✅ **前端已在使用**
   - 不需要前端改動太多

4. ✅ **符合設計理念**
   - 表單填寫需要多輪對話
   - 需要狀態追蹤（session_id）
   - 需要檢查緩存（已有機制）

---

### 不推薦：整合到 `POST /api/v1/chat/stream` ⚠️ **已暫時廢棄**

**理由**：

1. ❌ **端點已暫時廢棄**
   - 端點於 2026-01-09 標記為暫時停用
   - 系統統一使用 `/message` 端點處理對話

2. ❌ **沒有 session_id 欄位**
   - 無法追蹤表單會話
   - 需要修改 Request 模型（影響現有前端）

3. ❌ **流式輸出的複雜度**
   - 表單填寫需要返回結構化資料（progress, current_field 等）
   - 流式輸出不適合複雜的狀態管理

4. ❌ **增加維護成本**
   - 需要同時維護兩個端點的表單邏輯

5. ⚠️ **未來可選擇性支持**
   - Phase 1-4 先整合到 `/message`
   - 如果端點重新啟用，Phase 5+ 可考慮擴展到 `/stream`

---

## 📊 整合方案總結

### 方案：單端點整合（推薦）

**目標端點**：`POST /api/v1/message`

**修改範圍**：
- `routers/chat.py` 的 `vendor_chat_message()` 函數
- 增加表單會話檢查（雙點整合）
- 擴展 `VendorChatResponse` 模型（+7 個欄位）

**優點**：
- ✅ 修改最小（~60 行代碼）
- ✅ 風險最低（只改一個端點）
- ✅ 前端適配簡單（已在用此端點）
- ✅ 維護成本低（單一流程）

**缺點**：
- ⚠️ 流式端點已暫時廢棄（不影響表單功能）

---

### 未來擴展：雙端點支持（可選，需先重新啟用 /stream）

**如果未來重新啟用流式端點並需要流式表單**：

**前提條件**：
1. 確認流式輸出（即時逐字顯示）是業務優先需求
2. 前端有資源處理 SSE 事件
3. 評估雙端點維護成本是否可接受

**Phase 5+**：擴展 `POST /api/v1/chat/stream`
1. 重新啟用 `/stream` 端點
2. 增加 `session_id` 欄位到 `ChatStreamRequest`
3. 在流式輸出中支持表單狀態事件
4. 前端需要處理新的 SSE 事件

**流式表單的 SSE 事件設計**：
```
event: form_triggered
data: {"form_id": "rental_application", "progress": "0/4"}

event: form_field
data: {"field_name": "full_name", "prompt": "請問您的全名是？"}

event: form_completed
data: {"submission_id": 123}
```

**預估工作量**：
- 重新啟用端點：0.5 天
- 表單功能整合：2-3 天
- 前端適配：1-2 天
- 總計：3.5-5.5 天（在完成 Phase 1-4 後）

---

## ✅ 結論與確認

### 關鍵決策

**Q：表單功能應該整合到哪個端點？**
**A：`POST /api/v1/message`**

**Q：廢棄的端點是哪個？**
**A：`POST /api/v1/chat`（已於 2025-10-21 移除，不要碰）**

**Q：是否需要同時整合到兩個端點？**
**A：不需要。`/stream` 已暫時廢棄，只整合到 `/message`**

**Q：`/stream` 端點是否完全移除？**
**A：否。暫時停用但代碼保留，觀察期 6 個月（至 2026-07-09）**

---

## 📝 更新文檔路線圖

由於發現有兩套端點，需要確認前面的文檔：

### 已確認無需修改
- ✅ `FORM_FILLING_DIALOG_DESIGN.md` - 架構設計（通用）
- ✅ `FORM_FILLING_INTEGRATION_PLAN.md` - 整合方案（通用）
- ✅ `FORM_FILLING_CONFLICT_ANALYSIS.md` - 衝突分析（已針對 /message）
- ✅ `FORM_FILLING_CODE_CHANGES.md` - 代碼修改（已針對 /message）
- ✅ `FORM_FILLING_IMPLEMENTATION_ROADMAP.md` - 實施路線圖（已針對 /message）

**所有文檔都正確**，因為我從一開始就分析的是 `vendor_chat_message()` 函數（即 `/message` 端點）。

---

## 🎯 下一步確認

### 請確認

1. ✅ 表單整合到 `POST /api/v1/message` 端點（正確）
2. ✅ 不碰 `POST /api/v1/chat` 端點（已移除 2025-10-21）
3. ✅ 不整合到 `POST /api/v1/chat/stream`（已暫時廢棄 2026-01-09）
4. ⚠️ 如果 `/stream` 重新啟用，Phase 5+ 可選擇性擴展（需先評估需求）

### 現有文檔狀態

所有文檔 ✅ **已正確針對 `/message` 端點**，無需修改。

---

## 📚 相關端點完整列表（供參考）

### chat.py（對話相關）
- ✅ `POST /api/v1/message` - 主要對話端點（**表單整合到這**）
- ✅ `GET /api/v1/conversations` - 查詢對話歷史
- ✅ `GET /api/v1/conversations/{id}` - 查詢特定對話
- ✅ `POST /api/v1/conversations/{id}/feedback` - 提交反饋
- ✅ `GET /api/v1/vendors/{vendor_id}/test` - 測試業者配置
- ✅ `POST /api/v1/reload` - 重新載入服務

### chat_stream.py（流式對話）
- ⚠️ `POST /api/v1/chat/stream` - 流式對話端點（**暫時廢棄 2026-01-09**）
- ⚠️ `GET /api/v1/chat/stream/test` - 流式對話測試（**暫時廢棄 2026-01-09**）

### 端點狀態說明
| 端點 | 狀態 | 說明 |
|------|------|------|
| `POST /api/v1/chat` | ❌ 已移除 | 2025-10-21 移除，不要使用 |
| `POST /api/v1/message` | ✅ 活躍中 | 主要對話端點，表單整合到這 |
| `POST /api/v1/chat/stream` | ⚠️ 暫時廢棄 | 代碼保留，觀察期至 2026-07-09 |

---

**一切清楚了嗎？** 🎉
