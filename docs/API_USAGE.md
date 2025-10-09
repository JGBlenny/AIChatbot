# API 使用說明

## 基礎 URL

```
http://localhost:8000
```

---

## 1. 對話管理 API

### 1.1 匯入 LINE 對話（文字檔案）

**端點**: `POST /api/conversations/import/line/text`

**請求**:
```bash
curl -X POST "http://localhost:8000/api/conversations/import/line/text" \
  -F "file=@conversation.txt" \
  -F "default_date=2024/01/15"
```

**檔案格式範例** (`conversation.txt`):
```
2024/01/15 14:30 客戶: 你好，請問這個功能怎麼用？
2024/01/15 14:31 客服: 您好！使用方式如下：
2024/01/15 14:31 客服: 1. 打開設定
2024/01/15 14:32 客戶: 明白了，謝謝！
```

**回應**:
```json
{
  "id": "uuid",
  "raw_content": {...},
  "source": "line",
  "status": "pending",
  "created_at": "2024-01-15T14:30:00"
}
```

---

### 1.2 匯入 LINE 對話（JSON 格式）

**端點**: `POST /api/conversations/import/line`

**請求**:
```bash
curl -X POST "http://localhost:8000/api/conversations/import/line" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "timestamp": "2024/01/15 14:30",
        "sender": "客戶",
        "message": "你好，請問如何使用？"
      },
      {
        "timestamp": "2024/01/15 14:31",
        "sender": "客服",
        "message": "您好！使用方式如下..."
      }
    ],
    "conversation_id": "line-12345"
  }'
```

---

### 1.3 查詢對話列表

**端點**: `GET /api/conversations/`

**參數**:
- `page`: 頁碼 (預設: 1)
- `page_size`: 每頁數量 (預設: 20)
- `status`: 狀態篩選 (pending/processing/reviewed/approved/rejected)
- `category`: 分類篩選
- `source`: 來源篩選 (line/manual)
- `min_quality`: 最低品質分數 (1-10)
- `search`: 搜尋關鍵字

**範例**:
```bash
# 查詢所有對話
curl "http://localhost:8000/api/conversations/"

# 篩選已批准的對話
curl "http://localhost:8000/api/conversations/?status=approved"

# 搜尋包含「功能」的對話
curl "http://localhost:8000/api/conversations/?search=功能"

# 分頁查詢
curl "http://localhost:8000/api/conversations/?page=2&page_size=10"
```

**回應**:
```json
{
  "total": 100,
  "page": 1,
  "page_size": 20,
  "items": [...]
}
```

---

### 1.4 查詢單一對話

**端點**: `GET /api/conversations/{conversation_id}`

```bash
curl "http://localhost:8000/api/conversations/abc-123-def"
```

---

### 1.5 更新對話

**端點**: `PUT /api/conversations/{conversation_id}`

```bash
curl -X PUT "http://localhost:8000/api/conversations/abc-123-def" \
  -H "Content-Type: application/json" \
  -d '{
    "primary_category": "技術支援",
    "tags": ["常見問題", "設定"],
    "review_notes": "已確認內容正確"
  }'
```

---

### 1.6 刪除對話

**端點**: `DELETE /api/conversations/{conversation_id}`

```bash
curl -X DELETE "http://localhost:8000/api/conversations/abc-123-def"
```

---

### 1.7 對話統計

**端點**: `GET /api/conversations/stats/summary`

```bash
curl "http://localhost:8000/api/conversations/stats/summary"
```

**回應**:
```json
{
  "total": 150,
  "by_status": {
    "pending": 50,
    "approved": 80,
    "rejected": 20
  },
  "by_category": {
    "技術支援": 60,
    "產品功能": 40,
    "使用教學": 30
  },
  "avg_quality_score": 7.5,
  "recent_imports": 25
}
```

---

## 2. AI 處理 API

### 2.1 完整處理對話

**端點**: `POST /api/processing/{conversation_id}/process-all`

**功能**: 一次完成品質評估、分類、清理、實體提取

```bash
curl -X POST "http://localhost:8000/api/processing/abc-123-def/process-all"
```

**回應**:
```json
{
  "id": "abc-123-def",
  "quality_score": 8,
  "primary_category": "技術支援",
  "secondary_categories": ["功能詢問"],
  "tags": ["設定", "教學", "常見問題"],
  "sentiment": "positive",
  "confidence_score": 0.92,
  "processed_content": {
    "quality": {
      "score": 8,
      "reasoning": "對話完整且內容相關...",
      "suggestions": [...]
    },
    "category": {...},
    "cleaned": {
      "question": "如何使用這個功能？",
      "answer": "使用方式如下：1. 打開設定...",
      "context": "對話時間：2024-01-15 14:30",
      "tags": ["設定", "教學"],
      "confidence": 0.95
    },
    "entities": {...}
  },
  "status": "reviewed"
}
```

---

### 2.2 僅評估品質

**端點**: `POST /api/processing/{conversation_id}/evaluate`

```bash
curl -X POST "http://localhost:8000/api/processing/abc-123-def/evaluate"
```

---

### 2.3 僅分類

**端點**: `POST /api/processing/{conversation_id}/categorize`

```bash
curl -X POST "http://localhost:8000/api/processing/abc-123-def/categorize"
```

---

### 2.4 僅清理改寫

**端點**: `POST /api/processing/{conversation_id}/clean`

```bash
curl -X POST "http://localhost:8000/api/processing/abc-123-def/clean"
```

---

### 2.5 僅提取實體

**端點**: `POST /api/processing/{conversation_id}/extract`

```bash
curl -X POST "http://localhost:8000/api/processing/abc-123-def/extract"
```

---

### 2.6 批次處理

**端點**: `POST /api/processing/batch/process`

**說明**: 背景執行，適合大量對話

```bash
curl -X POST "http://localhost:8000/api/processing/batch/process" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_ids": [
      "abc-123",
      "def-456",
      "ghi-789"
    ],
    "action": "process"
  }'
```

**回應**:
```json
{
  "total": 3,
  "success": 0,
  "failed": 0,
  "results": [
    {"conversation_id": "abc-123", "status": "queued"},
    {"conversation_id": "def-456", "status": "queued"},
    {"conversation_id": "ghi-789", "status": "queued"}
  ]
}
```

---

### 2.7 批准對話

**端點**: `POST /api/processing/{conversation_id}/approve`

```bash
curl -X POST "http://localhost:8000/api/processing/abc-123-def/approve?reviewed_by=admin&review_notes=已確認"
```

---

### 2.8 拒絕對話

**端點**: `POST /api/processing/{conversation_id}/reject`

```bash
curl -X POST "http://localhost:8000/api/processing/abc-123-def/reject?reviewed_by=admin&review_notes=內容不相關"
```

---

## 3. 完整工作流程範例

### 步驟 1: 匯入對話

```bash
CONV_ID=$(curl -X POST "http://localhost:8000/api/conversations/import/line/text" \
  -F "file=@conversation.txt" \
  | jq -r '.id')

echo "對話 ID: $CONV_ID"
```

### 步驟 2: AI 處理

```bash
curl -X POST "http://localhost:8000/api/processing/$CONV_ID/process-all"
```

### 步驟 3: 查看結果

```bash
curl "http://localhost:8000/api/conversations/$CONV_ID" | jq
```

### 步驟 4: 審核（批准或拒絕）

```bash
# 批准
curl -X POST "http://localhost:8000/api/processing/$CONV_ID/approve?reviewed_by=admin"

# 或拒絕
curl -X POST "http://localhost:8000/api/processing/$CONV_ID/reject?reviewed_by=admin&review_notes=內容重複"
```

### 步驟 5: 查看統計

```bash
curl "http://localhost:8000/api/conversations/stats/summary" | jq
```

---

## 4. Python 範例

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. 匯入對話
with open("conversation.txt", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/api/conversations/import/line/text",
        files={"file": f}
    )
    conversation = response.json()
    conv_id = conversation["id"]
    print(f"匯入成功，ID: {conv_id}")

# 2. AI 處理
response = requests.post(
    f"{BASE_URL}/api/processing/{conv_id}/process-all"
)
result = response.json()
print(f"品質分數: {result['quality_score']}")
print(f"分類: {result['primary_category']}")
print(f"標籤: {', '.join(result['tags'])}")

# 3. 批准
requests.post(
    f"{BASE_URL}/api/processing/{conv_id}/approve",
    params={"reviewed_by": "admin"}
)
print("已批准")

# 4. 查詢列表
response = requests.get(
    f"{BASE_URL}/api/conversations/",
    params={"status": "approved", "page_size": 10}
)
conversations = response.json()
print(f"已批准對話數: {conversations['total']}")
```

---

## 5. 錯誤處理

### 常見錯誤碼

| 狀態碼 | 說明 |
|--------|------|
| 400 | 請求格式錯誤 |
| 404 | 資源不存在 |
| 500 | 伺服器錯誤（通常是 AI API 失敗）|

### 錯誤回應格式

```json
{
  "detail": "錯誤訊息"
}
```

### 處理範例

```python
try:
    response = requests.post(url, json=data)
    response.raise_for_status()
    result = response.json()
except requests.HTTPError as e:
    print(f"錯誤: {e.response.json()['detail']}")
```
