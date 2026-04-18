# JGB External API 需求規格書

> 版本：v1.0
> 日期：2026-04-18
> 目的：提供 AI Chatbot 系統查詢 JGB 帳務、合約、修繕、租客等資料的 API 端點規格

---

## 1. 總覽

### 1.1 基本資訊

| 項目 | 說明 |
|------|------|
| Base URL | `https://www.jgbsmart.com` |
| API 版本 | v1 |
| 路徑前綴 | `/api/external/v1` |
| 協定 | HTTPS（僅限） |
| 回應格式 | JSON |

### 1.2 認證方式

透過 `X-API-Key` Header 傳送 API Key：

```
X-API-Key: your-api-key-here
```

或透過 Query String（不建議，僅供除錯）：

```
GET /api/external/v1/bills?api_key=your-api-key-here
```

API Key 驗證流程：
1. 驗證 API Key 是否存在且有效（SHA-256 hash 比對）
2. 檢查 API Key 是否已停用或過期
3. 檢查該 Key 對應的操作權限（resource + action）
4. API Key 資訊注入 Request 供 Controller 使用

### 1.3 頻率限制

| 項目 | 預設值 |
|------|--------|
| 請求上限 | 60 次/分鐘（依 API Key 設定） |
| 限流計數 | 每個 API Key 獨立計算 |
| 超限回應 | HTTP 429，附帶 `Retry-After` Header |

### 1.4 共用回應格式

#### 成功回應

```json
{
  "success": true,
  "data": [ ... ],
  "pagination": {
    "current_page": 1,
    "per_page": 50,
    "total": 120,
    "total_pages": 3,
    "has_more": true
  }
}
```

#### 錯誤回應

```json
{
  "success": false,
  "error": {
    "code": 404,
    "message": "資料不存在"
  }
}
```

### 1.5 共用分頁參數

| 參數 | 類型 | 預設值 | 說明 |
|------|------|--------|------|
| `page` | integer | 1 | 頁碼（最小值 1） |
| `per_page` | integer | 50 | 每頁筆數（最小 1，最大 200） |

### 1.6 共用必填參數

所有端點均需提供以下參數以識別查詢範圍：

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `role_id` | integer | 是 | 出租方身份 ID（房東 role 主鍵） |
| `user_id` | integer | 是 | 承租方使用者 ID（租客 user 主鍵） |

---

## 2. 端點規格

---

### 2.1 GET `/api/external/v1/bills`

**說明**：查詢指定租客的帳單列表

#### 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `role_id` | integer | 是 | 出租方身份 ID |
| `user_id` | integer | 是 | 承租方使用者 ID |
| `month` | string | 否 | 帳單月份，格式 `YYYY-MM`（篩選 `date_start` ~ `date_end` 區間） |
| `status` | string | 否 | 帳單狀態篩選（見下方狀態對照表） |
| `type` | integer | 否 | 帳單類型（1=一般租金, 2=點退, 3=新增帳單, 4=罰款, 5=儲值, 6=押金設算息） |
| `page` | integer | 否 | 頁碼 |
| `per_page` | integer | 否 | 每頁筆數 |

#### 帳單狀態對照表（`bills.bit_status`）

| bit_status 值 | 狀態名稱 | 常數名稱 | 說明 |
|---------------|----------|----------|------|
| 1 | 待發送 | `BILL_PREPARE` | 帳單已建立，尚未發送給租客 |
| 2 | 待繳費 | `BILL_READY` | 帳單已發送，等待租客繳費 |
| 8 | 待對帳 | `BILL_PAYED` | 租客已付款，等待房東確認查收 |
| 16 | 已繳費 | `BILL_COMPLETE` | 房東已確認收到款項 |
| 32 | 排定發送 | `BILL_PREPARE_TO_READY` | 帳單排定自動發送 |
| 64 | 已失效 | `BILL_EXPIRED` | 帳單已失效 |

#### 帳單類型對照表（`bills.type`）

| type 值 | 類型名稱 | 說明 |
|---------|----------|------|
| 1 | 一般租金 | 週期性租金帳單 |
| 2 | 點退 | 退租點退帳單 |
| 3 | 新增帳單 | 手動建立的額外帳單 |
| 4 | 罰款 | 罰款帳單 |
| 5 | 儲值 | 儲值帳單 |
| 6 | 押金設算息 | 押金利息帳單 |

#### 帳單報表類別（`bills.category`）

| category 值 | 類別名稱 |
|-------------|----------|
| 1 | 備用金（物業營運） |
| 2 | 屋主資金 |
| 3 | 團隊營運 |
| 4 | 屋主提領 |
| 5 | 屋主直收 |
| 6 | 押金 |

#### 回應欄位（基於 `bills` 資料表實際欄位）

```json
{
  "success": true,
  "data": [
    {
      "id": 12345,
      "contract_id": 678,
      "estate_id": 456,
      "type": 1,
      "category": 3,
      "bit_status": 2,
      "title": "2026年4月租金",
      "sub_title": "2026/04/01 ~ 2026/04/30",
      "currency": "TWD",
      "total": 25000.00,
      "final_total": 25000.00,
      "rate": 1.00,
      "date_start": 20260401,
      "date_end": 20260430,
      "date_expire": 20260405,
      "date_expire_note": ["繳費期限：2026/04/05"],
      "cycle": 1,
      "days": 30,
      "is_auto_pay": false,
      "is_paid_on_time": null,
      "online_payment_method": "newebpay",
      "online_payment_action": "credit_card",
      "payment_id": 9876,
      "invoice_status": 0,
      "invoice_number": null,
      "ready_at": "2026-04-01T00:00:00+08:00",
      "pay_at": null,
      "complete_at": null,
      "created_at": "2026-03-25T10:30:00+08:00",
      "updated_at": "2026-04-01T00:00:00+08:00"
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 50,
    "total": 12,
    "total_pages": 1,
    "has_more": false
  }
}
```

#### 錯誤回應範例

**未授權（401）**：

```json
{
  "success": false,
  "error": {
    "code": 401,
    "message": "API Key 無效"
  }
}
```

**無權限（403）**：

```json
{
  "success": false,
  "error": {
    "code": 403,
    "message": "無權存取此出租方資料"
  }
}
```

**找不到資料（404）**：

```json
{
  "success": false,
  "error": {
    "code": 404,
    "message": "查無此租客帳單資料"
  }
}
```

---

### 2.2 GET `/api/external/v1/invoices`

**說明**：查詢指定租客的發票列表

#### 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `role_id` | integer | 是 | 出租方身份 ID |
| `user_id` | integer | 是 | 承租方使用者 ID |
| `bill_id` | integer | 否 | 指定帳單 ID（篩選該帳單的發票） |
| `status` | integer | 否 | 發票狀態篩選 |
| `page` | integer | 否 | 頁碼 |
| `per_page` | integer | 否 | 每頁筆數 |

#### 發票狀態對照表（`invoices.status`）

| status 值 | 狀態名稱 | 常數名稱 | 說明 |
|-----------|----------|----------|------|
| 0 | 未開立 | `NOT_ISSUED` | 尚未開立發票 |
| 1 | 已開立 | `ADD` | 發票已開立 |
| 2 | 作廢 | `INVALID` | 發票已作廢 |
| 3 | 折讓 | `ALLOWANCE` | 發票已折讓 |
| 4 | 作廢折讓 | `ALLOWANCE_INVALID` | 折讓已作廢 |

#### 發票種類（`invoices.category`）

| category 值 | 說明 |
|-------------|------|
| `B2B` | 企業對企業發票 |
| `B2C` | 企業對消費者發票 |

#### 課稅別（`invoices.tax_type`）

| tax_type 值 | 說明 |
|-------------|------|
| 1 | 應稅 |
| 2 | 零稅率 |
| 3 | 免稅 |
| 9 | 混合應稅與免稅或零稅率 |

#### 載具類別（`invoices.carrier_type`）

| carrier_type 值 | 說明 |
|-----------------|------|
| 0 | 手機條碼載具 |
| 1 | 自然人憑證條碼載具 |
| 2 | ezPay 電子發票載具 |

#### 回應欄位（基於 `invoices` 資料表實際欄位）

```json
{
  "success": true,
  "data": [
    {
      "id": 5001,
      "bill_id": 12345,
      "payment_id": 9876,
      "payment_no": "P202604010001",
      "manufacturer": "ezpay",
      "year": 2026,
      "month": 4,
      "number": "AZ00000123",
      "random_num": "1234",
      "status": 1,
      "upload_status": 1,
      "category": "B2C",
      "buyer_name": "王小明",
      "buyer_ubn": null,
      "buyer_address": null,
      "buyer_email": "tenant@example.com",
      "carrier_type": 0,
      "carrier_number": "/ABC+123",
      "love_code": null,
      "print_flag": 0,
      "tax_type": 1,
      "tax_rate": 0.05,
      "tax_amt": 1190,
      "amt": 23810,
      "total_amt": 25000,
      "item_data": [
        {
          "item_name": "2026年4月租金",
          "item_count": 1,
          "item_unit": "月",
          "item_price": 25000,
          "item_amount": 25000
        }
      ],
      "bar_code": "10604AZ000001231234",
      "url": "https://inv.ezpay.com.tw/...",
      "added_at": "2026-04-01T10:00:00+08:00",
      "invalid_at": null,
      "allowanced_at": null
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 50,
    "total": 5,
    "total_pages": 1,
    "has_more": false
  }
}
```

#### 錯誤回應範例

**找不到帳單（404）**：

```json
{
  "success": false,
  "error": {
    "code": 404,
    "message": "查無此帳單 ID 的發票資料"
  }
}
```

---

### 2.3 GET `/api/external/v1/contracts`

**說明**：查詢指定租客的合約列表

#### 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `role_id` | integer | 是 | 出租方身份 ID |
| `user_id` | integer | 是 | 承租方使用者 ID |
| `status` | string | 否 | 合約狀態篩選（見下方狀態對照表） |
| `page` | integer | 否 | 頁碼 |
| `per_page` | integer | 否 | 每頁筆數 |

#### 合約狀態對照表（`contracts.bit_status`）

| bit_status 值 | 狀態名稱 | 常數名稱 | 說明 |
|---------------|----------|----------|------|
| 1 | 待發送合約 | `CONTRACT_READY` | 合約剛建立 |
| 2 | 待租客簽回 | `CONTRACT_INVITING` | 已送出邀請給租客 |
| 4 | 待房東簽名 | `CONTRACT_INVITING_NEXT` | 租客已簽，等待房東簽名 |
| 8 | 執行中合約 | `CONTRACT_SIGNED` | 雙方簽名完成 |
| 16 | 點交送出 | `CONTRACT_MOVE_IN` | 送出點交清單，等租客確認 |
| 32 | 點交完成 | `CONTRACT_MOVE_IN_DONE` | 租客已同意點交 |
| 64 | 點退送出 | `CONTRACT_MOVE_OUT` | 送出點退清單，等租客確認 |
| 128 | 點退完成 | `CONTRACT_MOVE_OUT_DONE` | 租客已同意點退 |
| 256 | 提前解約 | `CONTRACT_EARLY_TERMINATION` | 提前解約申請中 |
| 512 | 提前解約已確認 | `CONTRACT_EARLY_TERMINATION_DONE` | 提前解約已確認 |
| 1024 | 歷史合約 | `CONTRACT_HISTORY` | 合約已結束 |
| 2048 | 合約結束（生命週期結束） | `CONTRACT_HISTORY_DONE` | 合約完全歸檔 |

#### 合約分組簡化說明

| 群組 | 涵蓋 bit_status | 說明 |
|------|-----------------|------|
| 待簽約 | 1, 2, 4 | 合約尚未正式成立 |
| 執行中 | 8, 16, 32, 64, 128, 256, 512 | 合約已成立，執行中 |
| 歷史 | 1024, 2048 | 合約已結束 |

#### 回應欄位（基於 `contracts` 資料表實際欄位）

```json
{
  "success": true,
  "data": [
    {
      "id": 678,
      "father_id": null,
      "is_newest": 1,
      "property_purpose_key": 1,
      "contract_type": "general",
      "contract_is_existing": false,
      "bit_status": 8,
      "estate_id": 456,
      "title": "信義區套房A",
      "country": "TW",
      "city": "台北市",
      "district": "信義區",
      "address": "信義路五段7號",
      "room_number": "A01",
      "currency": "TWD",
      "rent": 25000.00,
      "deposit_type": 0,
      "deposit": 2.0,
      "deposit_amount": 50000.00,
      "cycle": 1,
      "cycle_type": 2,
      "cycle_date": 1,
      "date_start": 20260101,
      "date_end": 20261231,
      "is_auto_pay": false,
      "online_payment_method": "newebpay",
      "online_payment_action": "credit_card",
      "fees": {
        "電費": 0,
        "水費": 0,
        "瓦斯費": 0,
        "網路費": 0,
        "管理費": 1500
      },
      "allow_early_termination": true,
      "early_termination_days": 30,
      "enable_late_fee": 0,
      "sales_tax_type": 0,
      "is_auto_generate_invoice": 0,
      "contract_inviting_at": "2025-12-15T10:00:00+08:00",
      "contract_finish_sign_at": "2025-12-20T14:30:00+08:00",
      "created_at": "2025-12-10T09:00:00+08:00",
      "updated_at": "2026-01-01T00:00:00+08:00"
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

#### 錯誤回應範例

**找不到資料（404）**：

```json
{
  "success": false,
  "error": {
    "code": 404,
    "message": "查無此租客的合約資料"
  }
}
```

---

### 2.4 GET `/api/external/v1/contracts/{id}/checkin-eligibility`

**說明**：查詢指定合約是否符合入住（點交）條件

#### 路徑參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `id` | integer | 是 | 合約 ID |

#### Query 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `role_id` | integer | 是 | 出租方身份 ID |
| `user_id` | integer | 是 | 承租方使用者 ID |

#### 判定邏輯

入住資格基於合約狀態與相關帳單繳費狀況判定：

1. **合約狀態檢查**：合約 `bit_status` 必須為 `CONTRACT_SIGNED`（8）或更後的執行中狀態
2. **首期帳單檢查**：對應合約的首期帳單（`type=1`）是否已繳費完成（`bit_status=16`，即 `BILL_COMPLETE`）
3. **押金檢查**：押金是否已收齊

#### 回應欄位

```json
{
  "success": true,
  "data": {
    "contract_id": 678,
    "eligible": true,
    "contract_status": {
      "bit_status": 8,
      "label": "執行中合約",
      "is_signed": true
    },
    "first_bill_status": {
      "bill_id": 12340,
      "bit_status": 16,
      "label": "已繳費",
      "is_paid": true
    },
    "deposit_status": {
      "required_amount": 50000.00,
      "paid_amount": 50000.00,
      "is_fulfilled": true
    },
    "checkin_blockers": []
  }
}
```

**不符合入住條件的範例**：

```json
{
  "success": true,
  "data": {
    "contract_id": 679,
    "eligible": false,
    "contract_status": {
      "bit_status": 8,
      "label": "執行中合約",
      "is_signed": true
    },
    "first_bill_status": {
      "bill_id": 12350,
      "bit_status": 2,
      "label": "待繳費",
      "is_paid": false
    },
    "deposit_status": {
      "required_amount": 50000.00,
      "paid_amount": 0.00,
      "is_fulfilled": false
    },
    "checkin_blockers": [
      "首期租金尚未繳費",
      "押金尚未收齊"
    ]
  }
}
```

#### 錯誤回應範例

**合約不存在（404）**：

```json
{
  "success": false,
  "error": {
    "code": 404,
    "message": "查無此合約"
  }
}
```

**無權存取（403）**：

```json
{
  "success": false,
  "error": {
    "code": 403,
    "message": "無權存取此合約"
  }
}
```

---

### 2.5 GET `/api/external/v1/payments`

**說明**：查詢指定租客的付款記錄列表

#### 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `role_id` | integer | 是 | 出租方身份 ID |
| `user_id` | integer | 是 | 承租方使用者 ID |
| `month` | string | 否 | 付款月份，格式 `YYYY-MM` |
| `status` | integer | 否 | 付款狀態篩選 |
| `page` | integer | 否 | 頁碼 |
| `per_page` | integer | 否 | 每頁筆數 |

#### 付款狀態對照表（`payments.status`）

| status 值 | 狀態名稱 | 說明 |
|-----------|----------|------|
| -3 | 第3次付款 | 第三次重試付款 |
| -2 | 第2次付款 | 第二次重試付款 |
| -1 | 第1次付款 | 第一次重試付款 |
| 0 | 付款失敗 | 付款未成功 |
| 1 | 付款中 | 正在處理付款 |
| 2 | 付款成功 | 付款已完成 |
| 99 | 取消付款 | 付款已取消 |

#### 付款管道對照表

**線上/線下**：

| 值 | 常數 | 說明 |
|----|------|------|
| 1 | `PAYMENT_VENDOR` | 線上金流 |
| 2 | `PAYMENT_CASH` | 線下付款 |

**金流廠商**：

| 常數名稱 | 值 | 說明 |
|----------|-----|------|
| `PAYMENT_NEWEBPAY` | 4 | 藍新金流 |
| `PAYMENT_CATHAYBK` | 8 | 國泰世華 |
| `PAYMENT_SINOPAC` | 16 | 永豐銀行 |
| `PAYMENT_CTBC` | 32 | 中國信託 |
| `PAYMENT_ICASHPAY` | 64 | 愛金卡 |
| `PAYMENT_NTUPAY` | 128 | 台大金流 |

**付款方式**：

| 常數名稱 | key | 說明 |
|----------|-----|------|
| `PAYMENT_CREDIT_CARD` | `credit_card` | 信用卡 |
| `PAYMENT_ATM` | `atm` | ATM 轉帳 |
| `PAYMENT_GOOGLE_PAY` | `google_pay` | Google Pay |
| `PAYMENT_SAMSUNG_PAY` | `samsung_pay` | Samsung Pay |
| `PAYMENT_CVS` | `cvs` | 超商代碼 |
| `PAYMENT_CVS_BARCODE` | `cvs_barcode` | 超商條碼 |
| `PAYMENT_PAY` | `pay` | 中信 PAY |
| `ICASHPAY_APP` | `icashpay` | 愛金卡 APP |

#### 回應欄位（基於 `payments` 資料表實際欄位）

```json
{
  "success": true,
  "data": [
    {
      "id": 9876,
      "no": "P202604010001",
      "transaction_id": "TXN20260401123456",
      "user_id": 100,
      "role_id": 200,
      "creditor_user_id": 50,
      "creditor_role_id": 300,
      "type": "bill",
      "status": 2,
      "manufacturer": "newebpay",
      "payment": "credit_card",
      "currency": "TWD",
      "orig_currency": "TWD",
      "orig_price": 25000.00,
      "price": 25000.00,
      "final_currency": "TWD",
      "final_price": 25000.00,
      "discount_cash": 0.00,
      "discount_price": 0.00,
      "payment_times": 1,
      "data": "末四碼 1234",
      "note": "2026年4月租金",
      "items": [
        {
          "name": "租金",
          "amount": 25000
        }
      ],
      "invoice_status": 1,
      "invoice_number": "AZ00000123",
      "ymd": 20260401,
      "payment_completed_ymd": 20260401,
      "payment_completed_at": "2026-04-01T15:30:00+08:00",
      "created_at": "2026-04-01T14:00:00+08:00",
      "updated_at": "2026-04-01T15:30:00+08:00"
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 50,
    "total": 8,
    "total_pages": 1,
    "has_more": false
  }
}
```

#### 錯誤回應範例

**找不到資料（404）**：

```json
{
  "success": false,
  "error": {
    "code": 404,
    "message": "查無此租客的付款紀錄"
  }
}
```

---

### 2.6 GET `/api/external/v1/repairs`

**說明**：查詢指定租客的修繕單列表

#### 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `role_id` | integer | 是 | 出租方身份 ID |
| `user_id` | integer | 是 | 承租方使用者 ID |
| `status` | integer | 否 | 修繕狀態篩選（見下方狀態對照表） |
| `page` | integer | 否 | 頁碼 |
| `per_page` | integer | 否 | 每頁筆數 |

#### 修繕狀態對照表（`repairs.status`）

| status 值 | 狀態名稱 | 常數名稱 | 說明 |
|-----------|----------|----------|------|
| 1 | 申請中 | `APPLY` | 租客或房東已提交修繕申請 |
| 2 | 安排修繕 | `ASSIGN` | 已分配廠商，安排修繕時間 |
| 4 | 進行中 | `PROCESS` | 修繕作業進行中 |
| 16 | 完成修繕 | `COMPLETE` | 廠商已完成修繕 |
| 32 | 結單 | `FINISH` | 修繕單已結單 |
| 64 | 封存 | `ARCHIVE` | 修繕單已封存 |

#### 緊急狀態（`repairs.emergency_status`）

| emergency_status 值 | 說明 |
|---------------------|------|
| 1 | 非緊急 |
| 2 | 緊急 |

#### 回應欄位（基於 `repairs` 資料表實際欄位）

```json
{
  "success": true,
  "data": [
    {
      "id": 3001,
      "estate_id": 456,
      "contract_id": 678,
      "role_id": 200,
      "user_id": 50,
      "to_user_id": 100,
      "to_role_id": 201,
      "status": 16,
      "emergency_status": 1,
      "estate_title": "信義區套房A",
      "estate_full_address": "台北市信義區信義路五段7號",
      "estate_room_number": "A01",
      "category_id": 1,
      "category_name": "水電類",
      "item_id": 3,
      "item_name": "水管漏水",
      "broken_reason": "管線老化",
      "broken_note": "浴室水管持續滴水",
      "broken_photos": ["photo1.jpg", "photo2.jpg"],
      "manufacturer_id": 10,
      "manufacturer_name": "信義水電行",
      "manufacturer_phone": "02-12345678",
      "currency": "TWD",
      "total": 3500.00,
      "apply_role_key": 3,
      "apply_role_id": 201,
      "pre_assign_data": [
        {
          "date": "2026-04-10",
          "time_slot": "上午"
        }
      ],
      "assign_data": [
        {
          "date": "2026-04-12",
          "time": "10:00",
          "manufacturer_id": 10,
          "manufacturer_name": "信義水電行"
        }
      ],
      "user_note": "已完成修繕，更換新水管",
      "to_user_note": "謝謝，已確認修繕完成",
      "apply_at": "2026-04-05T09:00:00+08:00",
      "assign_at": "2026-04-06T11:00:00+08:00",
      "complete_at": "2026-04-12T14:00:00+08:00",
      "finish_at": "2026-04-13T10:00:00+08:00",
      "archive_at": null,
      "created_at": "2026-04-05T09:00:00+08:00",
      "updated_at": "2026-04-13T10:00:00+08:00"
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 50,
    "total": 3,
    "total_pages": 1,
    "has_more": false
  }
}
```

#### 錯誤回應範例

**找不到資料（404）**：

```json
{
  "success": false,
  "error": {
    "code": 404,
    "message": "查無此租客的修繕紀錄"
  }
}
```

---

### 2.7 GET `/api/external/v1/tenants/{user_id}/summary`

**說明**：查詢指定租客的綜合摘要（合約數、帳單數、修繕數等統計）

#### 路徑參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `user_id` | integer | 是 | 承租方使用者 ID |

#### Query 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `role_id` | integer | 是 | 出租方身份 ID |

#### 回應欄位（基於 `existed_lessee` 資料表實際欄位）

此端點回傳的統計資料直接來自 `existed_lessee` 資料表中快取的聚合欄位：

```json
{
  "success": true,
  "data": {
    "tenant_info": {
      "id": 5001,
      "lessee_user_id": 100,
      "lessee_role_id": 201,
      "lessor_role_id": 200,
      "lessee_name": "王小明",
      "lessee_email": "tenant@example.com",
      "lessee_registered_phone": "0912345678",
      "lessee_registered_phone_country": "TW",
      "is_lessee_user_registered": 1,
      "lessee_nationality": "TW",
      "lessee_birthday": "1990-01-15",
      "lessee_primary_contact": "phone",
      "lessee_emergency_contact_name": "王大明",
      "lessee_emergency_contact_phone": "0923456789",
      "lessee_emergency_contact_relationship": "父親",
      "active": 1
    },
    "contract_summary": {
      "registered_contract_count": 3,
      "registered_contract_inviting_count": 0,
      "registered_contract_inviting_next_count": 0,
      "registered_contract_signed_count": 1,
      "registered_contract_history_count": 2,
      "exempt_register_contract_count": 0,
      "exempt_register_contract_signed_count": 0,
      "exempt_register_contract_history_count": 0
    },
    "bill_summary": {
      "income_bill_count": 24,
      "income_bill_ready_count": 1,
      "income_bill_ready_overdue_count": 0,
      "income_bill_paid_count": 0,
      "income_bill_complete_count": 23,
      "income_bill_complete_on_time_count": 20,
      "income_bill_complete_late_count": 3,
      "income_bill_paid_on_time_ratio": 87,
      "payment_bill_count": 0,
      "payment_bill_ready_count": 0,
      "payment_bill_paid_count": 0,
      "payment_bill_complete_count": 0
    },
    "repair_summary": {
      "repair_count": 5,
      "repair_apply_count": 0,
      "repair_assign_count": 0,
      "repair_complete_count": 1,
      "repair_finish_count": 4
    }
  }
}
```

#### 錯誤回應範例

**租客不存在（404）**：

```json
{
  "success": false,
  "error": {
    "code": 404,
    "message": "查無此租客資料"
  }
}
```

**無權存取（403）**：

```json
{
  "success": false,
  "error": {
    "code": 403,
    "message": "無權存取此租客資料"
  }
}
```

---

## 3. 共用錯誤代碼

| HTTP 狀態碼 | 錯誤類型 | 說明 |
|-------------|----------|------|
| 400 | Bad Request | 請求參數格式錯誤（缺少必填參數、類型錯誤等） |
| 401 | Unauthorized | API Key 未提供、無效、已停用或已過期 |
| 403 | Forbidden | API Key 無權存取此資源或操作 |
| 404 | Not Found | 請求的資源不存在 |
| 429 | Too Many Requests | 超過頻率限制，請參考 `Retry-After` Header |
| 500 | Internal Server Error | 伺服器內部錯誤 |

### 400 Bad Request 範例

```json
{
  "success": false,
  "error": {
    "code": 400,
    "message": "缺少必填參數: role_id"
  }
}
```

### 429 Too Many Requests 範例

```json
{
  "success": false,
  "error": {
    "code": 429,
    "message": "請求過於頻繁，請稍後再試"
  }
}
```

回應 Header：
```
Retry-After: 60
```

---

## 4. 備註

### 4.1 日期格式

- 資料庫中部分日期欄位以整數格式存放（`YYYYMMDD`），例如 `date_start: 20260401`
- 時間戳記欄位回傳 ISO 8601 格式（`YYYY-MM-DDTHH:mm:ss+08:00`）
- 查詢參數 `month` 使用 `YYYY-MM` 格式

### 4.2 金額格式

- 所有金額欄位精度為小數點後 5 位（`decimal(20,5)`），回傳時保留實際精度
- 幣別以 ISO 4217 三碼表示（如 `TWD`、`USD`）

### 4.3 狀態欄位說明

- `bit_status`：使用二進位旗標表示狀態，每個狀態為 2 的冪次方
- `status`：部分資料表同時存有 `status` 與 `bit_status`，API 統一以 `bit_status` 為準

### 4.4 存取權限控制

- 每個 API Key 綁定特定的 `role_id` 存取範圍
- 查詢時傳入的 `role_id` 必須在 API Key 的授權範圍內
- `user_id` 篩選範圍限於該 `role_id` 下的合約關聯租客

### 4.5 與現有 Estate API 的關係

此 API 沿用 JGB 現有的 External API 架構（`ExternalApiAuth` Middleware + `ExternalApiKey` Model），與物件 API（`/api/external/v1/estates`）共用相同的認證與限流機制。新端點只需註冊路由並套用相同 Middleware 即可。
