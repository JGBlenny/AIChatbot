# 📡 知識匯入 API 參考文件

## 概述

知識匯入 API 提供了完整的知識批量匯入功能，包括檔案上傳、作業追蹤、審核管理等端點。

**Base URL**: `http://localhost:8100/api/v1`

---

## 📤 檔案上傳

### POST /knowledge-import/upload

上傳檔案並啟動知識匯入作業。

#### Request

**Content-Type**: `multipart/form-data`

**參數**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| file | File | ✅ | 上傳的檔案（.xlsx, .json, .txt） |
| vendor_id | Integer | ❌ | 業者 ID（不填為通用知識） |
| import_mode | String | ❌ | 匯入模式：append/replace/merge（預設：append） |
| enable_deduplication | Boolean | ❌ | 是否啟用去重（預設：true） |

**cURL 範例**:
```bash
curl -X POST http://localhost:8100/api/v1/knowledge-import/upload \
  -F "file=@test_knowledge_data.xlsx" \
  -F "vendor_id=1" \
  -F "import_mode=append" \
  -F "enable_deduplication=true"
```

**Python 範例**:
```python
import requests

url = "http://localhost:8100/api/v1/knowledge-import/upload"

files = {
    'file': open('test_knowledge_data.xlsx', 'rb')
}
data = {
    'vendor_id': 1,
    'import_mode': 'append',
    'enable_deduplication': True
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

**JavaScript 範例**:
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('vendor_id', '1');
formData.append('import_mode', 'append');
formData.append('enable_deduplication', 'true');

const response = await fetch('http://localhost:8100/api/v1/knowledge-import/upload', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log(result);
```

#### Response

**Status**: `200 OK`

```json
{
  "job_id": "f87958b1-a660-477f-8725-17b074da76f0",
  "status": "processing",
  "message": "檔案上傳成功，開始處理中。所有知識將進入審核佇列，需經人工審核後才會正式加入知識庫。"
}
```

#### Error Responses

**400 Bad Request** - 檔案格式不支援
```json
{
  "detail": "不支援的檔案類型: .pdf"
}
```

**400 Bad Request** - 缺少必填欄位
```json
{
  "detail": "找不到答案欄位。支援的欄位名稱: answer, 答案, 回覆, response"
}
```

**500 Internal Server Error** - 處理失敗
```json
{
  "detail": "向量生成失敗: Connection timeout"
}
```

---

## 📊 作業狀態查詢

### GET /knowledge-import/jobs/{job_id}

查詢匯入作業的處理狀態。

#### Request

**Path Parameters**:

| 參數 | 類型 | 說明 |
|------|------|------|
| job_id | UUID | 作業 ID（由上傳端點返回） |

**cURL 範例**:
```bash
curl http://localhost:8100/api/v1/knowledge-import/jobs/f87958b1-a660-477f-8725-17b074da76f0
```

#### Response

**處理中** (`status: "processing"`):
```json
{
  "job_id": "f87958b1-a660-477f-8725-17b074da76f0",
  "status": "processing",
  "progress": {
    "current": 55,
    "total": 100,
    "stage": "生成向量嵌入"
  },
  "file_name": "test_knowledge_data.xlsx",
  "vendor_id": 1,
  "import_mode": "append",
  "enable_deduplication": true,
  "created_at": "2025-10-12T10:48:20Z",
  "updated_at": "2025-10-12T10:48:25Z"
}
```

**處理完成** (`status: "completed"`):
```json
{
  "job_id": "f87958b1-a660-477f-8725-17b074da76f0",
  "status": "completed",
  "progress": {
    "current": 100,
    "total": 100
  },
  "result": {
    "imported": 10,
    "skipped": 0,
    "errors": 0,
    "total": 10,
    "test_scenarios_created": 8,
    "mode": "review_queue"
  },
  "file_name": "test_knowledge_data.xlsx",
  "vendor_id": 1,
  "created_at": "2025-10-12T10:48:20Z",
  "completed_at": "2025-10-12T10:48:30Z"
}
```

**處理失敗** (`status: "failed"`):
```json
{
  "job_id": "f87958b1-a660-477f-8725-17b074da76f0",
  "status": "failed",
  "error_message": "向量生成失敗: OpenAI API timeout",
  "progress": {
    "current": 55,
    "total": 100,
    "stage": "生成向量嵌入"
  },
  "created_at": "2025-10-12T10:48:20Z",
  "updated_at": "2025-10-12T10:48:25Z"
}
```

#### 狀態說明

| 狀態 | 說明 |
|------|------|
| `processing` | 處理中 |
| `completed` | 處理完成 |
| `failed` | 處理失敗 |

#### 處理階段

| 階段 | current | 說明 |
|------|---------|------|
| 解析檔案 | 10 | 讀取並解析上傳的檔案 |
| 文字去重 | 20 | 精確匹配去重 |
| 生成問題摘要 | 35 | LLM 生成問題（若缺少） |
| 生成向量嵌入 | 55 | OpenAI embedding |
| 語意去重 | 70 | 向量相似度去重 |
| 推薦意圖 | 76 | LLM 推薦意圖 |
| 建立測試情境 | 78 | B2C 知識建立測試情境 |
| 匯入審核佇列 | 85 | 寫入資料庫 |
| 處理中 | 100 | 完成 |

---

## 📋 審核佇列管理

### GET /knowledge/candidates

查詢審核佇列中的知識候選。

#### Request

**Query Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| status | String | ❌ | 狀態過濾：pending_review/approved/rejected |
| ai_model | String | ❌ | 來源過濾：knowledge_import/ai_generated |
| limit | Integer | ❌ | 每頁數量（預設：50） |
| offset | Integer | ❌ | 偏移量（預設：0） |

**cURL 範例**:
```bash
# 查詢所有待審核的匯入知識
curl "http://localhost:8100/api/v1/knowledge/candidates?status=pending_review&ai_model=knowledge_import"

# 查詢已審核的知識
curl "http://localhost:8100/api/v1/knowledge/candidates?status=approved"

# 分頁查詢
curl "http://localhost:8100/api/v1/knowledge/candidates?limit=20&offset=40"
```

#### Response

```json
{
  "candidates": [
    {
      "id": 45,
      "test_scenario_id": 20,
      "question": "如何繳納租金？",
      "generated_answer": "租金應於每月 1 號前繳清。可透過以下方式繳費：\n1. ATM 轉帳\n2. 線上刷卡\n3. 超商繳費\n\n逾期 5 天後將加收 200 元手續費。",
      "confidence_score": 0.95,
      "ai_model": "knowledge_import",
      "generation_reasoning": "分類: 帳務查詢, 對象: 租客, 關鍵字: 繳費, 租金, ATM, 信用卡\n\n【推薦意圖】\n意圖 ID: 6\n意圖名稱: 帳務查詢\n信心度: 0.95\n推薦理由: 問題涉及繳納租金的方式和期限，屬於帳務查詢的範疇。",
      "suggested_sources": ["test_knowledge_data.xlsx"],
      "warnings": [],
      "status": "pending_review",
      "created_at": "2025-10-12T10:48:30Z",
      "updated_at": "2025-10-12T10:48:30Z"
    }
  ],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

---

### POST /knowledge/candidates/{candidate_id}/review

審核知識候選。

#### Request

**Path Parameters**:

| 參數 | 類型 | 說明 |
|------|------|------|
| candidate_id | Integer | 候選 ID |

**Body Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| status | String | ✅ | 審核結果：approved/rejected |
| reviewed_by | String | ✅ | 審核者 |
| review_notes | String | ❌ | 審核備註 |
| edited_question | String | ❌ | 編輯後的問題 |
| edited_answer | String | ❌ | 編輯後的答案 |
| edit_summary | String | ❌ | 編輯摘要 |

**cURL 範例**:
```bash
# 審核通過
curl -X POST http://localhost:8100/api/v1/knowledge/candidates/45/review \
  -H "Content-Type: application/json" \
  -d '{
    "status": "approved",
    "reviewed_by": "admin",
    "review_notes": "知識內容正確，通過審核"
  }'

# 審核拒絕
curl -X POST http://localhost:8100/api/v1/knowledge/candidates/46/review \
  -H "Content-Type: application/json" \
  -d '{
    "status": "rejected",
    "reviewed_by": "admin",
    "review_notes": "答案不夠詳細"
  }'

# 編輯後通過
curl -X POST http://localhost:8100/api/v1/knowledge/candidates/47/review \
  -H "Content-Type: application/json" \
  -d '{
    "status": "approved",
    "reviewed_by": "admin",
    "edited_question": "租金繳費方式有哪些？",
    "edited_answer": "租金可透過以下方式繳納：\n1. ATM 轉帳\n2. 線上刷卡\n3. 超商繳費\n\n請於每月 1 號前完成繳費。",
    "edit_summary": "優化問題表述，補充繳費期限"
  }'
```

#### Response

**Status**: `200 OK`

```json
{
  "message": "審核完成",
  "candidate_id": 45,
  "status": "approved",
  "knowledge_id": 123,
  "reviewed_at": "2025-10-12T11:00:00Z"
}
```

---

## 🧪 測試情境管理

### GET /test-scenarios

查詢測試情境列表。

#### Request

**Query Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| status | String | ❌ | 狀態過濾：pending_review/approved/rejected |
| source | String | ❌ | 來源過濾：imported/manual/user_question |
| limit | Integer | ❌ | 每頁數量（預設：50） |
| offset | Integer | ❌ | 偏移量（預設：0） |

**cURL 範例**:
```bash
# 查詢所有匯入的測試情境
curl "http://localhost:8000/api/test-scenarios?source=imported&status=pending_review"
```

#### Response

```json
{
  "scenarios": [
    {
      "id": 20,
      "test_question": "如何繳納租金？",
      "expected_category": "帳務查詢",
      "difficulty": "medium",
      "status": "pending_review",
      "source": "imported",
      "has_knowledge": true,
      "created_at": "2025-10-12T10:48:30Z"
    }
  ],
  "total": 8
}
```

---

### POST /test-scenarios/{scenario_id}/review

審核測試情境。

#### Request

**Path Parameters**:

| 參數 | 類型 | 說明 |
|------|------|------|
| scenario_id | Integer | 測試情境 ID |

**Body Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| status | String | ✅ | 審核結果：approved/rejected |
| reviewed_by | String | ✅ | 審核者 |
| review_notes | String | ❌ | 審核備註 |

**cURL 範例**:
```bash
curl -X POST http://localhost:8000/api/test-scenarios/20/review \
  -H "Content-Type: application/json" \
  -d '{
    "status": "approved",
    "reviewed_by": "admin",
    "review_notes": "測試情境合理"
  }'
```

#### Response

```json
{
  "message": "審核完成",
  "scenario_id": 20,
  "status": "approved",
  "reviewed_at": "2025-10-12T11:00:00Z"
}
```

---

## 📊 統計資訊

### GET /knowledge-import/stats

查詢知識匯入統計資訊。

#### Request

**Query Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| start_date | Date | ❌ | 開始日期（ISO 8601） |
| end_date | Date | ❌ | 結束日期（ISO 8601） |
| vendor_id | Integer | ❌ | 業者 ID 過濾 |

**cURL 範例**:
```bash
curl "http://localhost:8100/api/v1/knowledge-import/stats?start_date=2025-10-01&end_date=2025-10-31"
```

#### Response

```json
{
  "total_jobs": 25,
  "completed_jobs": 20,
  "failed_jobs": 2,
  "processing_jobs": 3,
  "total_knowledge_imported": 250,
  "total_knowledge_pending": 50,
  "total_knowledge_approved": 200,
  "total_test_scenarios_created": 180,
  "deduplication_stats": {
    "text_duplicates_skipped": 45,
    "semantic_duplicates_skipped": 12,
    "total_duplicates_skipped": 57
  },
  "period": {
    "start_date": "2025-10-01",
    "end_date": "2025-10-31"
  }
}
```

---

## 🔧 開發測試

### 完整測試流程範例

```python
import requests
import time

BASE_URL = "http://localhost:8100/api/v1"

# 1. 上傳檔案
print("📤 上傳檔案...")
files = {'file': open('test_knowledge_data.xlsx', 'rb')}
data = {
    'vendor_id': 1,
    'import_mode': 'append',
    'enable_deduplication': True
}
response = requests.post(f"{BASE_URL}/knowledge-import/upload", files=files, data=data)
result = response.json()
job_id = result['job_id']
print(f"✅ Job ID: {job_id}")

# 2. 輪詢作業狀態
print("\n⏳ 等待處理完成...")
while True:
    response = requests.get(f"{BASE_URL}/knowledge-import/jobs/{job_id}")
    status = response.json()

    if status['status'] == 'completed':
        print("✅ 處理完成")
        print(f"   匯入: {status['result']['imported']} 條")
        print(f"   測試情境: {status['result']['test_scenarios_created']} 個")
        break
    elif status['status'] == 'failed':
        print(f"❌ 處理失敗: {status['error_message']}")
        break
    else:
        progress = status['progress']
        print(f"   [{progress['current']}/{progress['total']}] {progress.get('stage', 'processing')}")
        time.sleep(2)

# 3. 查詢審核佇列
print("\n📋 查詢審核佇列...")
response = requests.get(
    f"{BASE_URL}/knowledge/candidates",
    params={'status': 'pending_review', 'ai_model': 'knowledge_import'}
)
candidates = response.json()
print(f"   待審核知識: {candidates['total']} 條")

# 4. 審核第一條知識
if candidates['total'] > 0:
    candidate_id = candidates['candidates'][0]['id']
    print(f"\n✅ 審核知識 #{candidate_id}...")
    response = requests.post(
        f"{BASE_URL}/knowledge/candidates/{candidate_id}/review",
        json={
            'status': 'approved',
            'reviewed_by': 'admin',
            'review_notes': '自動測試審核通過'
        }
    )
    print("   審核完成")
```

---

## 📚 相關文件

- [知識匯入功能文檔](../features/KNOWLEDGE_IMPORT_FEATURE.md)
- [測試情境管理](../features/TEST_SCENARIO_STATUS_MANAGEMENT.md)
- [審核中心使用指南](../guides/REVIEW_CENTER_GUIDE.md)

---

**建立日期**: 2025-10-12
**最後更新**: 2025-10-12
**版本**: 1.0
**維護者**: Claude Code
