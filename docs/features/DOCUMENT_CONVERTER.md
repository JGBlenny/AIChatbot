# 📄 文件轉換器功能文件

**最後更新**: 2026-01-14
**功能狀態**: ✅ Phase 1 完成
**Base URL**: `http://localhost:8100/api/v1/document-converter`

---

## 📋 目錄

- [概述](#概述)
- [功能特色](#功能特色)
- [支援格式](#支援格式)
- [API 端點](#api-端點)
- [前端頁面](#前端頁面)
- [使用流程](#使用流程)
- [成本估算](#成本估算)
- [範例](#範例)

---

## 概述

文件轉換器是一個強大的工具，可以將 Word、PDF 等文件自動轉換為 Q&A 格式的知識內容。系統使用 OpenAI GPT 模型分析文件內容，智能提取問答對，大幅減少手動建立知識的時間。

### 典型使用場景

- 📚 **SOP 文件轉知識**: 將標準作業程序轉換為問答
- 📄 **FAQ 文件處理**: 批量匯入常見問題
- 📋 **規章制度轉換**: 將公司規定轉為查詢式內容
- 🏢 **業者文件導入**: 快速建立新業者知識庫

---

## 功能特色

### 1. 智能文件解析

- **多格式支援**: Word (.docx), PDF, 純文字 (.txt)
- **結構識別**: 自動識別標題、段落、列表
- **圖表處理**: (PDF) 提取文字內容

### 2. AI 問答生成

使用 OpenAI GPT 模型：
- 自動生成相關問題
- 提取對應答案
- 優化問答品質
- 支援中文語境

### 3. 互動式編輯

- **預覽與編輯**: 轉換後可編輯問答對
- **批次操作**: 勾選匯入特定問答
- **品質檢查**: 標記低品質內容
- **成本估算**: 預估 API 使用成本

### 4. 批量匯出

- **CSV 匯出**: 標準格式方便備份
- **直接匯入**: 一鍵匯入知識庫
- **審核流程**: 匯入後進入審核佇列

---

## 支援格式

| 格式 | 副檔名 | 支援程度 | 備註 |
|------|--------|---------|------|
| **Word** | .docx | ✅ 完整支援 | 建議使用，結構保留最佳 |
| **PDF** | .pdf | ✅ 支援 | 純文字 PDF 效果最佳 |
| **純文字** | .txt | ✅ 支援 | 需手動標記結構 |
| **Markdown** | .md | ⚠️ 部分支援 | 需轉為 .txt |

---

## API 端點

### 1. POST /api/v1/document-converter/upload

上傳文件

**Content-Type**: `multipart/form-data`

**Form Data**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `file` | file | ✅ | 文件檔案 |
| `vendor_id` | integer | ❌ | 業者 ID |
| `business_type` | string | ❌ | 業態類型 |

**範例**:

```bash
curl -X POST http://localhost:8100/api/v1/document-converter/upload \
  -F "file=@SOP_document.docx" \
  -F "vendor_id=1" \
  -F "business_type=rent"
```

**回應 (201 Created)**:

```json
{
  "job_id": "conv-123e4567-e89b-12d3-a456-426614174000",
  "filename": "SOP_document.docx",
  "file_size_bytes": 45678,
  "status": "uploaded",
  "message": "檔案上傳成功，準備解析",
  "created_at": "2026-01-14T10:00:00"
}
```

---

### 2. POST /api/v1/document-converter/{job_id}/parse

解析文件

**Path Parameters**:
- `job_id` (string): 任務 ID

**範例**:

```bash
curl -X POST http://localhost:8100/api/v1/document-converter/conv-123e4567/parse
```

**回應 (200 OK)**:

```json
{
  "job_id": "conv-123e4567",
  "status": "parsing",
  "message": "文件解析中...",
  "progress": {
    "current": 0,
    "total": 100
  },
  "estimated_time_seconds": 30
}
```

---

### 3. POST /api/v1/document-converter/{job_id}/convert

轉換為 Q&A

**Path Parameters**:
- `job_id` (string): 任務 ID

**Body Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `model` | string | ❌ | GPT 模型 (預設: gpt-4o-mini) |
| `max_qa_pairs` | integer | ❌ | 最大問答對數（預設: 50） |
| `language` | string | ❌ | 語言（預設: zh-TW） |

**範例**:

```bash
curl -X POST http://localhost:8100/api/v1/document-converter/conv-123e4567/convert \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "max_qa_pairs": 30,
    "language": "zh-TW"
  }'
```

**回應 (202 Accepted)**:

```json
{
  "job_id": "conv-123e4567",
  "status": "converting",
  "message": "AI 轉換中...",
  "progress": {
    "current": 5,
    "total": 30
  },
  "estimated_time_seconds": 120
}
```

---

### 4. GET /api/v1/document-converter/{job_id}

取得任務狀態

**Path Parameters**:
- `job_id` (string): 任務 ID

**範例**:

```bash
curl http://localhost:8100/api/v1/document-converter/conv-123e4567
```

**回應 (200 OK)**:

**狀態：已完成**
```json
{
  "job_id": "conv-123e4567",
  "filename": "SOP_document.docx",
  "status": "completed",
  "qa_list": [
    {
      "id": 1,
      "question": "退租要提前多久通知？",
      "answer": "退租需要提前 30 天以書面方式通知房東。",
      "confidence": 0.92,
      "selected": true
    },
    {
      "id": 2,
      "question": "押金什麼時候退還？",
      "answer": "房屋狀況確認無誤後，房東應在 7 個工作天內退還押金。",
      "confidence": 0.88,
      "selected": true
    }
  ],
  "total_qa_pairs": 25,
  "selected_count": 25,
  "statistics": {
    "avg_confidence": 0.87,
    "high_confidence_count": 20,
    "medium_confidence_count": 5,
    "low_confidence_count": 0
  },
  "cost_estimation": {
    "total_tokens": 12500,
    "estimated_cost_usd": 0.125
  },
  "created_at": "2026-01-14T10:00:00",
  "completed_at": "2026-01-14T10:02:30"
}
```

**狀態代碼**:
- `uploaded`: 已上傳
- `parsing`: 解析中
- `parsed`: 解析完成
- `converting`: 轉換中
- `completed`: 完成
- `failed`: 失敗

---

### 5. PUT /api/v1/document-converter/{job_id}/qa-list

更新 Q&A 列表

**說明**: 編輯問答對或勾選要匯入的項目

**Path Parameters**:
- `job_id` (string): 任務 ID

**Body Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `qa_list` | array | ✅ | 更新後的問答列表 |

**範例**:

```bash
curl -X PUT http://localhost:8100/api/v1/document-converter/conv-123e4567/qa-list \
  -H "Content-Type: application/json" \
  -d '{
    "qa_list": [
      {
        "id": 1,
        "question": "退租要提前多久通知？（已編輯）",
        "answer": "退租需要提前 30 天以書面方式通知房東。",
        "selected": true
      },
      {
        "id": 2,
        "question": "押金什麼時候退還？",
        "answer": "房屋狀況確認無誤後，房東應在 7 個工作天內退還押金。",
        "selected": false
      }
    ]
  }'
```

**回應 (200 OK)**:

```json
{
  "message": "Q&A 列表已更新",
  "job_id": "conv-123e4567",
  "total_qa_pairs": 25,
  "selected_count": 24,
  "updated_at": "2026-01-14T10:05:00"
}
```

---

### 6. POST /api/v1/document-converter/{job_id}/estimate-cost

估算轉換成本

**Path Parameters**:
- `job_id` (string): 任務 ID

**Body Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `model` | string | ❌ | GPT 模型 |
| `max_qa_pairs` | integer | ❌ | 預計問答對數 |

**範例**:

```bash
curl -X POST http://localhost:8100/api/v1/document-converter/conv-123e4567/estimate-cost \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "max_qa_pairs": 30
  }'
```

**回應 (200 OK)**:

```json
{
  "estimated_tokens": 15000,
  "estimated_cost_usd": 0.15,
  "estimated_cost_ntd": 4.65,
  "model": "gpt-4o-mini",
  "pricing": {
    "input_tokens": 10000,
    "output_tokens": 5000,
    "input_cost_per_1k": 0.00015,
    "output_cost_per_1k": 0.0006
  },
  "estimated_time_seconds": 120
}
```

---

### 7. POST /api/v1/document-converter/{job_id}/export-csv

匯出為 CSV

**Path Parameters**:
- `job_id` (string): 任務 ID

**範例**:

```bash
curl -X POST http://localhost:8100/api/v1/document-converter/conv-123e4567/export-csv \
  -o qa_export.csv
```

**回應**: CSV 檔案下載

**CSV 格式**:
```csv
Question,Answer,Confidence,Selected
"退租要提前多久通知？","退租需要提前 30 天以書面方式通知房東。",0.92,true
"押金什麼時候退還？","房屋狀況確認無誤後，房東應在 7 個工作天內退還押金。",0.88,true
```

---

### 8. DELETE /api/v1/document-converter/{job_id}

刪除任務

**Path Parameters**:
- `job_id` (string): 任務 ID

**範例**:

```bash
curl -X DELETE http://localhost:8100/api/v1/document-converter/conv-123e4567
```

**回應 (200 OK)**:

```json
{
  "message": "任務已刪除",
  "job_id": "conv-123e4567"
}
```

---

## 前端頁面

### 文件轉換器頁面

**路由**: `/document-converter`
**組件**: `DocumentConverterView.vue`

**功能**:
1. **上傳區域**: 拖放或點擊上傳文件
2. **任務列表**: 顯示所有轉換任務及狀態
3. **進度追蹤**: 即時顯示解析/轉換進度
4. **Q&A 編輯器**: 轉換完成後編輯問答對
5. **批次操作**: 全選/取消、批次匯入
6. **成本預估**: 預估 API 使用成本
7. **匯出功能**: 匯出為 CSV

---

## 使用流程

### 完整流程

```
1. 上傳文件
   ↓
2. 文件解析（提取文字）
   ↓
3. 成本估算（可選）
   ↓
4. AI 轉換（生成 Q&A）
   ↓
5. 預覽與編輯
   ↓
6. 選擇要匯入的問答對
   ↓
7. 匯出 CSV 或直接匯入知識庫
   ↓
8. 進入審核佇列
```

### 步驟詳解

#### 步驟 1：上傳文件

1. 進入文件轉換器頁面: `http://localhost:8087/document-converter`
2. 點擊上傳區域或拖放文件
3. 支援格式: .docx, .pdf, .txt
4. 選填業者 ID、業態類型
5. 點擊「上傳」

---

#### 步驟 2：文件解析

- 系統自動解析文件結構
- 提取文字內容
- 識別標題、段落
- 預處理特殊格式

**等待時間**: 約 10-30 秒（依文件大小）

---

#### 步驟 3：成本估算（建議）

點擊「估算成本」查看：
- 預估 Token 數
- 預估費用（USD / NTD）
- 預估處理時間

**範例估算**:
```
文件大小: 50KB
預估 Tokens: 15,000
預估費用: $0.15 USD (約 NT$4.65)
預估時間: 2 分鐘
```

---

#### 步驟 4：AI 轉換

1. 點擊「開始轉換」
2. 系統使用 GPT 模型分析
3. 自動生成問答對
4. 顯示即時進度

**GPT Prompt 範例**:
```
請分析以下文件內容，提取關鍵資訊並生成問答對。

要求：
1. 每個問答對應該清晰、獨立
2. 問題應該是使用者可能會問的自然語言
3. 答案應該完整、準確
4. 優先提取重要資訊
5. 生成 20-30 個問答對

文件內容：
[解析後的文字]
```

---

#### 步驟 5：預覽與編輯

轉換完成後：
- 查看所有生成的問答對
- 編輯問題或答案
- 查看信心度分數
- 標記低品質內容

**信心度說明**:
- 🟢 **高 (>0.85)**: 品質良好，可直接使用
- 🟡 **中 (0.70-0.85)**: 建議檢查
- 🔴 **低 (<0.70)**: 需要編輯或刪除

---

#### 步驟 6：選擇匯入項目

- 勾選要匯入的問答對
- 取消勾選低品質項目
- 查看已選數量

---

#### 步驟 7：匯出或匯入

**選項 A: 匯出 CSV**
- 點擊「匯出 CSV」
- 下載問答對檔案
- 可用於備份或後續處理

**選項 B: 直接匯入**
- 點擊「匯入知識庫」
- 所有已選問答對進入審核佇列
- 需管理員審核後才會生效

---

## 成本估算

### OpenAI API 定價（GPT-4o-mini）

| 項目 | 單價 | 說明 |
|------|------|------|
| Input Tokens | $0.00015 / 1K | 輸入文字 |
| Output Tokens | $0.0006 / 1K | 生成文字 |

### 成本計算範例

**範例 1: 小型文件 (20KB)**
```
Input: ~8,000 tokens
Output: ~3,000 tokens
總成本: (8 × 0.00015) + (3 × 0.0006) = $0.003 ≈ NT$0.09
```

**範例 2: 中型文件 (50KB)**
```
Input: ~20,000 tokens
Output: ~8,000 tokens
總成本: (20 × 0.00015) + (8 × 0.0006) = $0.0078 ≈ NT$0.24
```

**範例 3: 大型文件 (100KB)**
```
Input: ~40,000 tokens
Output: ~15,000 tokens
總成本: (40 × 0.00015) + (15 × 0.0006) = $0.015 ≈ NT$0.47
```

### 成本優化建議

1. **選擇合適模型**: gpt-4o-mini 最經濟
2. **限制問答對數**: 設定 `max_qa_pairs` 參數
3. **批次處理**: 一次處理多個相關文件
4. **預先清理**: 移除無關內容（頁首、頁尾）

---

## 範例

### 完整使用範例

**場景**: 將「退租 SOP.docx」轉換為知識庫

**步驟**:

1. **上傳文件**:
```bash
curl -X POST http://localhost:8100/api/v1/document-converter/upload \
  -F "file=@退租SOP.docx" \
  -F "vendor_id=1"
```

回應:
```json
{
  "job_id": "conv-abc123",
  "status": "uploaded"
}
```

---

2. **解析文件**:
```bash
curl -X POST http://localhost:8100/api/v1/document-converter/conv-abc123/parse
```

---

3. **估算成本**:
```bash
curl -X POST http://localhost:8100/api/v1/document-converter/conv-abc123/estimate-cost \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o-mini", "max_qa_pairs": 30}'
```

回應:
```json
{
  "estimated_cost_usd": 0.08,
  "estimated_cost_ntd": 2.48
}
```

---

4. **開始轉換**:
```bash
curl -X POST http://localhost:8100/api/v1/document-converter/conv-abc123/convert \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o-mini", "max_qa_pairs": 30}'
```

---

5. **查看結果**:
```bash
curl http://localhost:8100/api/v1/document-converter/conv-abc123
```

回應:
```json
{
  "status": "completed",
  "qa_list": [
    {
      "id": 1,
      "question": "退租要提前多久通知？",
      "answer": "退租需要提前 30 天以書面方式通知房東。",
      "confidence": 0.92,
      "selected": true
    }
    // ... 更多問答對
  ],
  "total_qa_pairs": 28,
  "selected_count": 28
}
```

---

6. **匯出 CSV**:
```bash
curl -X POST http://localhost:8100/api/v1/document-converter/conv-abc123/export-csv \
  -o 退租QA.csv
```

---

## 限制與注意事項

### 檔案大小限制

- 單一檔案上限: **10MB**
- 建議大小: **< 5MB** (效果最佳)
- 超過限制請分割檔案

### 格式限制

- ❌ **不支援**: 掃描 PDF（純圖片）
- ❌ **不支援**: 加密文件
- ⚠️ **部分支援**: 複雜排版（表格、多欄）

### API 限制

- 單次最大問答對: **100 對**
- 建議數量: **20-50 對** (品質較佳)
- Rate Limit: 依 OpenAI API 限制

---

## 故障排除

### 問題 1: 轉換失敗

**可能原因**:
- OpenAI API 錯誤
- Token 超過限制
- 文件格式不支援

**解決方案**:
1. 檢查 API Key 是否有效
2. 減少 `max_qa_pairs` 參數
3. 確認文件格式正確

---

### 問題 2: 品質不佳

**症狀**: 生成的問答對不相關或重複

**解決方案**:
1. 清理文件內容（移除無關文字）
2. 調整 `max_qa_pairs` 參數
3. 手動編輯問答對
4. 考慮使用更強大的模型（gpt-4）

---

### 問題 3: 成本過高

**解決方案**:
1. 使用 gpt-4o-mini 而非 gpt-4
2. 減少 `max_qa_pairs`
3. 預先清理文件內容
4. 批次處理相似文件

---

## 相關文件

- [Knowledge Admin API 參考](../api/API_REFERENCE_KNOWLEDGE_ADMIN.md)
- [RAG Orchestrator API 參考](../api/API_REFERENCE_PHASE1.md)
- [知識匯入功能](./KNOWLEDGE_IMPORT_FEATURE.md)
- [資料庫架構文件](../database/DATABASE_SCHEMA.md)

---

**維護者**: Claude Code
**最後更新**: 2026-01-14
**版本**: 1.0
