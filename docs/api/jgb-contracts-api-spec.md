# JGB 合約查詢 API 規格需求

AI 客服需要查詢合約資料，判斷用戶能否執行特定操作（點交/點退/提前解約/續約）並回答原因。

---

## API 端點

```
GET /api/external/v1/contracts
```

**認證**：`X-API-Key` header（同現有 estates API）

**限流**：60 次/分鐘

---

## Request 參數

| 參數 | 類型 | 必填 | 說明 |
|---|---|---|---|
| role_id | integer | 是 | 管理者角色 ID |
| user_id | integer | 否 | 租客用戶 ID（篩選特定租客） |
| contract_id | integer | 否 | 指定合約 ID |
| keyword | string | 否 | 物件名稱/合約標題模糊搜尋 |
| page | integer | 否 | 頁碼（預設 1） |
| per_page | integer | 否 | 每頁筆數（預設 50，最大 200） |

---

## Response 格式

遵循現有 estates API 的回應格式：

```json
{
  "success": true,
  "mapping": {
    "bit_status_flags": {
      "1": "已建立",
      "2": "已發送簽約邀請",
      "4": "租客已簽名",
      "8": "雙方簽名完成",
      "16": "已發送點交",
      "32": "租客同意點交",
      "64": "已發送點退",
      "128": "租客同意點退",
      "256": "提前解約中",
      "512": "提前解約已確認",
      "1024": "歷史合約",
      "2048": "歷史完成"
    }
  },
  "data": [
    {
      // 見下方欄位表
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 50,
    "total": 2,
    "total_pages": 1,
    "has_more": false
  }
}
```

---

## 必要回傳欄位

### 核心識別

| 欄位 | 類型 | 說明 |
|---|---|---|
| id | integer | 合約 ID |
| title | string | 物件名稱 |
| active | integer | 合約是否啟用（1=啟用） |

### 狀態欄位（判斷引擎核心依據）

| 欄位 | 類型 | 說明 | 判斷用途 |
|---|---|---|---|
| status | integer | 當前階段（會被覆寫為最新階段） | canMoveIn/Out/EarlyTermination 等所有判斷都用到 |
| bit_status | integer | 狀態 bitmask（累加，不會被覆寫） | 核心：所有判斷邏輯的主要依據 |
| is_history | integer | 是否已標記歷史 | applyHistory / status 還原邏輯 |
| is_history_done | integer | 是否歷史完成 | applyHistory / status 還原邏輯 |

### 合約資訊

| 欄位 | 類型 | 說明 | 判斷用途 |
|---|---|---|---|
| date_start | integer | 合約起始日（YYYYMMDD） | canMoveOut：已到開始日 |
| date_end | integer | 合約結束日（YYYYMMDD） | canMoveOut：到期前30天 / canRenew：未到期 |
| rent | number | 月租金 | 顯示 |
| allow_early_termination | boolean | 是否允許提前終止 | canEarlyTermination |
| early_termination_days | integer | 提前終止需提前天數 | 顯示 |
| property_purpose_key | integer | 用途（1=住宅, 2=社會住宅） | invite 分流邏輯 |

### 租客相關

| 欄位 | 類型 | 說明 | 判斷用途 |
|---|---|---|---|
| to_user_connect | boolean | 租客是否已綁定 JGB | canMoveIn/Out/Renew |
| is_tenant_registered | boolean | 是否為註冊租客（非免註冊） | confirm 條件 / moveIn 通知邏輯 |
| to_user_phone | string | 租客電話 | invite：至少有 phone 或 email |
| to_user_email | string | 租客 Email | 同上 |

### 續約/解約相關

| 欄位 | 類型 | 說明 | 判斷用途 |
|---|---|---|---|
| father_id | integer | 續約來源合約 ID（null=非續約） | isRenewing() 判斷 |
| early_termination_wish_date_end | string | 提前解約期望結束日 | applyEarlyTermination 條件 |

---

## 回應範例

### 執行中的合約（已點交）

```json
{
  "id": 678,
  "title": "信義區套房A",
  "active": 1,
  "status": 5,
  "bit_status": 47,
  "is_history": 0,
  "is_history_done": 0,
  "date_start": 20260101,
  "date_end": 20261231,
  "rent": 25000.00,
  "allow_early_termination": true,
  "early_termination_days": 30,
  "property_purpose_key": 1,
  "to_user_connect": true,
  "is_tenant_registered": true,
  "to_user_phone": "0912345678",
  "to_user_email": "tenant@example.com",
  "father_id": null,
  "early_termination_wish_date_end": null,
  "created_at": "2025-12-10 09:00:00",
  "updated_at": "2026-01-01 00:00:00"
}
```

bit_status = 47 = 1+2+4+8+32 = READY + INVITING + INVITING_NEXT + SIGNED + MOVE_IN_DONE

### 歷史合約

```json
{
  "id": 600,
  "title": "中山區雅房B",
  "active": 1,
  "status": 10,
  "bit_status": 3087,
  "is_history": 1,
  "is_history_done": 1,
  "date_start": 20250101,
  "date_end": 20251231,
  "rent": 18000.00,
  "allow_early_termination": false,
  "early_termination_days": 0,
  "property_purpose_key": 1,
  "to_user_connect": true,
  "is_tenant_registered": true,
  "to_user_phone": "0923456789",
  "to_user_email": "tenant2@example.com",
  "father_id": null,
  "early_termination_wish_date_end": null,
  "created_at": "2024-12-05 09:00:00",
  "updated_at": "2025-12-31 23:59:59"
}
```

---

## 錯誤回應

```json
{
  "success": false,
  "error": {
    "code": 401,
    "message": "API Key 無效或未提供"
  }
}
```

| HTTP 狀態碼 | 說明 |
|---|---|
| 401 | API Key 無效或未提供 |
| 403 | 無權存取此資料 |
| 404 | 合約不存在 |
| 429 | 請求過於頻繁 |

---

## AI 客服使用場景

| 用戶問題 | AI 查什麼 | 判斷什麼 |
|---|---|---|
| 合約為什麼不能點交 | bit_status, status, to_user_connect | canMoveIn 條件 |
| 合約為什麼不能點退 | bit_status, status, date_start, date_end | canMoveOut 條件 |
| 可以提前解約嗎 | bit_status, status, allow_early_termination, father_id | canEarlyTermination 條件 |
| 合約可以續約嗎 | bit_status, date_end, to_user_connect | canRenew 條件 |
| 合約目前什麼狀態 | bit_status, status, is_history | 顯示當前階段 + 可用操作 |

---

*文件建立日期：2026-04-20*
*對應 AI 客服判斷引擎：rag-orchestrator/services/jgb/contracts.py*
