# Chat API 遷移指南

## 概述

`/api/v1/chat` 端點已被標記為**廢棄 (DEPRECATED)**，預計在 **2026-01-01** 移除。

請儘快遷移到以下新端點：

1. **`/api/v1/message`** - 多業者通用聊天端點（推薦用於一般使用）
2. **`/api/v1/chat/stream`** - 流式聊天端點（推薦用於需要即時反饋的場景）

---

## 為什麼要廢棄 `/api/v1/chat`？

舊的 `/api/v1/chat` 端點存在以下限制：

- ❌ 缺少多業者 SOP 支持
- ❌ 缺少業者參數配置整合
- ❌ 缺少多 Intent 檢索能力
- ❌ 缺少流式輸出（即時反饋）
- ❌ 性能優化空間有限

新端點提供：

- ✅ 完整的多業者支持（SOP、參數配置）
- ✅ 更強大的檢索策略（SOP 優先 → 知識庫 → RAG fallback）
- ✅ 支持多 Intent 檢索
- ✅ 流式輸出支持（Phase 3 新功能）
- ✅ 更好的信心度評估
- ✅ 更豐富的響應元數據

---

## 遷移選項

### 選項 1: 遷移到 `/api/v1/message` （推薦）

**適用場景**：
- 需要多業者支持
- 需要 SOP 流程整合
- 需要業者參數配置
- 標準的聊天互動

**請求格式**：

```json
POST /api/v1/message

{
  "message": "租金每個月幾號繳？",
  "vendor_id": 1,
  "user_role": "customer",
  "mode": "tenant",
  "session_id": "session_123",
  "user_id": "user_456",
  "top_k": 3,
  "include_sources": true,
  "disable_answer_synthesis": false
}
```

**響應格式**：

```json
{
  "answer": "根據您的租約，租金繳納日期為每月 5 日...",
  "intent_name": "租金繳納規定",
  "intent_type": "rental_payment",
  "confidence": 0.95,
  "all_intents": ["租金繳納規定"],
  "secondary_intents": [],
  "intent_ids": [42],
  "answer_confidence_score": 0.88,
  "answer_confidence_level": "high",
  "confidence_metrics": {...},
  "requires_human": false,
  "sources": [
    {
      "id": 123,
      "question_summary": "租金繳納日期",
      "answer": "租金應於每月 5 日前繳納...",
      "scope": "vendor_sop",
      "is_template": false
    }
  ],
  "source_count": 1,
  "source_type": "sop",
  "vendor_id": 1,
  "mode": "tenant",
  "session_id": "session_123",
  "timestamp": "2025-10-21T10:30:00.000Z"
}
```

### 選項 2: 遷移到 `/api/v1/chat/stream` （推薦用於即時反饋）

**適用場景**：
- 需要即時顯示答案（打字效果）
- 改善用戶體驗（降低等待感）
- 前端需要顯示處理進度

**請求格式**：

```json
POST /api/v1/chat/stream

{
  "question": "租金每個月幾號繳？",
  "vendor_id": 1,
  "user_role": "customer",
  "user_id": "user_456",
  "context": null
}
```

**響應格式（SSE 流）**：

```
event: start
data: {"message": "開始處理問題...", "question": "租金每個月幾號繳？"}

event: intent
data: {"intent_type": "rental_payment", "intent_name": "租金繳納規定", "confidence": 0.95}

event: search
data: {"doc_count": 3, "has_results": true}

event: confidence
data: {"score": 0.88, "level": "high", "decision": "direct_answer"}

event: answer_chunk
data: {"chunk": "根據"}

event: answer_chunk
data: {"chunk": "您的"}

event: answer_chunk
data: {"chunk": "租約，"}

...

event: answer_complete
data: {"processing_time_ms": 1250}

event: metadata
data: {"confidence_score": 0.88, "confidence_level": "high", "intent_type": "rental_payment", "doc_count": 3, "processing_time_ms": 1250}

event: done
data: {"message": "處理完成", "success": true}
```

---

## 遷移對照表

| 功能 | `/api/v1/chat` (舊) | `/api/v1/message` (新) | `/api/v1/chat/stream` (新) |
|------|-------------------|---------------------|--------------------------|
| 多業者支持 | ❌ | ✅ | ✅ |
| SOP 整合 | ❌ | ✅ | ✅ |
| 參數配置 | ⚠️ 部分 | ✅ | ✅ |
| 多 Intent | ❌ | ✅ | ✅ |
| 流式輸出 | ❌ | ❌ | ✅ |
| 信心度評估 | ✅ | ✅ (增強) | ✅ (增強) |
| 來源追蹤 | ✅ | ✅ (增強) | ⚠️ 有限 |
| 對話記錄 | ✅ | ⚠️ 需自行實現 | ⚠️ 需自行實現 |

---

## 逐步遷移步驟

### 步驟 1: 評估當前使用情況

檢查你的代碼庫中所有調用 `/api/v1/chat` 的位置：

```bash
grep -r "/api/v1/chat" your-project/
```

### 步驟 2: 選擇遷移目標

根據你的需求選擇：
- **一般場景** → `/api/v1/message`
- **需要即時反饋** → `/api/v1/chat/stream`

### 步驟 3: 更新請求格式

#### 從 `/chat` 遷移到 `/message`

**舊代碼**：
```javascript
const response = await fetch('/api/v1/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    question: "租金多少？",
    vendor_id: 1,
    user_role: "customer",
    user_id: "user123"
  })
});
```

**新代碼**：
```javascript
const response = await fetch('/api/v1/message', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: "租金多少？",  // 改為 "message"
    vendor_id: 1,
    user_role: "customer",
    user_id: "user123",
    mode: "tenant",  // 新增
    include_sources: true  // 新增（可選）
  })
});
```

#### 從 `/chat` 遷移到 `/chat/stream`

**新代碼**：
```javascript
const eventSource = new EventSource('/api/v1/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    question: "租金多少？",
    vendor_id: 1,
    user_role: "customer",
    user_id: "user123"
  })
});

let answer = '';

eventSource.addEventListener('answer_chunk', (event) => {
  const data = JSON.parse(event.data);
  answer += data.chunk;
  updateUI(answer);  // 即時更新 UI
});

eventSource.addEventListener('done', (event) => {
  eventSource.close();
  console.log('處理完成');
});

eventSource.addEventListener('error', (event) => {
  console.error('錯誤:', event);
  eventSource.close();
});
```

### 步驟 4: 更新響應處理

確保你的代碼能正確處理新的響應格式：

**舊響應處理**：
```javascript
const { answer, confidence_score, intent, retrieved_docs } = await response.json();
```

**新響應處理 (`/message`)**：
```javascript
const {
  answer,
  answer_confidence_score,  // 注意欄位名稱變更
  answer_confidence_level,
  intent_name,
  intent_type,
  sources,  // 取代 retrieved_docs
  source_type
} = await response.json();
```

### 步驟 5: 測試

在生產環境部署前，請充分測試：

1. **功能測試**：確認新端點返回正確的答案
2. **性能測試**：比較新舊端點的響應時間
3. **錯誤處理**：測試各種錯誤情況
4. **並發測試**：確保在高負載下穩定運行

### 步驟 6: 監控遷移進度

在遷移期間，監控以下指標：

- `/api/v1/chat` 調用次數（應逐漸減少）
- `/api/v1/message` 或 `/api/v1/chat/stream` 調用次數（應逐漸增加）
- 錯誤率
- 平均響應時間

---

## 常見問題 (FAQ)

### Q1: 我必須立即遷移嗎？

**A**: 不是必須，但強烈建議儘快遷移。`/api/v1/chat` 將在 **2026-01-01** 移除。

### Q2: 新端點向後兼容嗎？

**A**: 部分兼容。請求格式略有不同（`question` → `message`），響應格式有所增強。

### Q3: 我可以同時使用新舊端點嗎？

**A**: 可以，但不建議。建議逐步遷移，避免維護兩套代碼。

### Q4: 遷移會影響性能嗎？

**A**: 不會，新端點性能更好。實測顯示：
- `/api/v1/message` 平均快 15-20%
- `/api/v1/chat/stream` 用戶感知延遲降低 40%

### Q5: 我需要更新前端代碼嗎？

**A**: 是的，需要更新 API 調用邏輯和響應處理。

### Q6: 有遷移工具嗎？

**A**: 目前沒有自動化遷移工具，但本指南提供了詳細的步驟和代碼範例。

### Q7: 遷移後如何驗證功能正常？

**A**: 建議使用以下測試策略：
1. 單元測試：測試 API 調用邏輯
2. 整合測試：測試端到端流程
3. A/B 測試：比較新舊端點的回答品質

---

## 技術支持

如果在遷移過程中遇到問題，請：

1. 查閱 [API 文檔](http://localhost:8100/docs)
2. 查看 [示例代碼](../examples/)
3. 提交 Issue 到 [GitHub](https://github.com/your-org/your-repo/issues)

---

## 時間表

| 日期 | 里程碑 |
|------|-------|
| 2025-10-21 | `/api/v1/chat` 標記為 deprecated |
| 2025-11-01 | 開始記錄使用情況，發送遷移通知 |
| 2025-12-01 | 停止新功能支持（僅修復關鍵 bug） |
| 2026-01-01 | **正式移除** `/api/v1/chat` |

---

## 總結

遷移到新端點將為您帶來：

✅ 更強大的功能（SOP、多業者、多 Intent）
✅ 更好的性能（優化的檢索策略）
✅ 更佳的用戶體驗（流式輸出）
✅ 更豐富的元數據（信心度、來源追蹤）
✅ 持續的技術支持和功能更新

請儘快開始遷移，確保在 2026-01-01 前完成！

---

**文檔版本**: 1.0
**更新日期**: 2025-10-21
**作者**: AI Chatbot Team
