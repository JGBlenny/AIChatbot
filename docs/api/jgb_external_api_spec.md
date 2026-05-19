# JGB External API 需求規格書

> 版本：v1.1
> 日期：2026-05-19
> 目的：提供 AI Chatbot 系統查詢 JGB 帳務、合約、修繕、租客等資料的 API 端點規格
>
> **v1.1 變更**：新增 5 支診斷用端點（2.8~2.12）+ 2 項現有端點欄位擴充（2.13~2.14），支援 99-conditional-diagnosis.json 的 24 條診斷情境

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

### 2.3 GET `/api/external/v1/contracts/status-overview`

**說明**：查詢指定租客的合約狀態總覽

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

### 2.8 GET `/api/external/v1/bills/{bill_id}`

**說明**：查詢單一帳單詳情，包含付款資訊（虛擬帳號）與帳單明細項目

> 此端點用於診斷：帳單發不出（DIAG-B01）、虛擬帳號過期（DIAG-P04）、手動到帳失敗（DIAG-B04）

#### 路徑參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `bill_id` | integer | 是 | 帳單 ID |

#### Query 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `role_id` | integer | 是 | 出租方身份 ID |

#### 回應欄位

```json
{
  "success": true,
  "mapping": {
    "status": { "1": "待發送", "2": "待繳費", "8": "待對帳", "16": "已繳費", "32": "排定發送", "64": "已失效" },
    "invoice_status": { "0": "未開發票", "1": "已開發票", "2": "發票異常" },
    "type": { "1": "一般租金", "2": "點退", "3": "新增帳單", "4": "罰款", "5": "儲值", "6": "押金設算息" },
    "unit_type": { "": "無單位", "1": "度", "2": "日", "3": "月" }
  },
  "data": {
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
    "online_payment_action": "atm",
    "payment_id": 9876,
    "invoice_status": 0,
    "invoice_number": null,
    "ready_at": "2026-04-01T00:00:00+08:00",
    "pay_at": null,
    "complete_at": null,
    "created_at": "2026-03-25T10:30:00+08:00",
    "updated_at": "2026-04-01T00:00:00+08:00",

    "pay_info": {
      "type": "online",
      "manufacturer": "newebpay",
      "action": "atm",
      "expire_ymd": "2026/04/10",
      "atm_info": {
        "bank_code": "004",
        "bank_name": "台灣銀行",
        "atm": "9103522178643201",
        "expire": "2026-04-10"
      }
    },

    "details": [
      {
        "id": 101,
        "label": "租金",
        "unit_price": 25000.00,
        "unit_type": null,
        "unit_count": 1.00,
        "measurement_before": null,
        "measurement_after": null,
        "total_price": 25000.00,
        "active": 1
      },
      {
        "id": 102,
        "label": "電費",
        "unit_price": 5.50,
        "unit_type": 1,
        "unit_count": 120.00,
        "measurement_before": 1000.00,
        "measurement_after": 1120.00,
        "total_price": 660.00,
        "active": 1
      }
    ]
  }
}
```

#### pay_info 欄位說明

| 欄位 | 類型 | 說明 |
|------|------|------|
| `type` | string | 付款類型：`online`（線上）/ `offline`（線下） |
| `manufacturer` | string | 金流廠商（newebpay、cathaybk、sinopac、ctbc、icashpay） |
| `action` | string | 繳費方式（credit_card、atm、cvs 等） |
| `expire_ymd` | string | 付款到期日期 |
| `atm_info` | object/null | ATM 虛擬帳號資訊（僅 ATM 付款時存在） |
| `atm_info.bank_code` | string | 銀行代碼 |
| `atm_info.bank_name` | string | 銀行名稱 |
| `atm_info.atm` | string | 虛擬帳號 |
| `atm_info.expire` | string | 虛擬帳號到期日期 |

#### details 欄位說明

| 欄位 | 類型 | 說明 |
|------|------|------|
| `id` | integer | 明細 ID |
| `label` | string | 項目名稱 |
| `unit_price` | float | 單位價格 |
| `unit_type` | integer/null | 單位類型（null=無單位、1=度、2=日、3=月） |
| `unit_count` | float | 數量 |
| `measurement_before` | float/null | 量測前讀數（如電表度數） |
| `measurement_after` | float/null | 量測後讀數 |
| `total_price` | float | 項目總金額 |

#### 錯誤回應範例

**帳單不存在或無權存取（404）**：

```json
{
  "success": false,
  "error": {
    "code": 404,
    "message": "帳單不存在或無權存取"
  }
}
```

---

### 2.9 GET `/api/external/v1/payment-logs`

**說明**：查詢付款交易的金流 API 日誌（錯誤碼、回應資料）

> 此端點用於診斷：付了款沒到帳（DIAG-P01）、信用卡失敗（DIAG-P02）、自動扣款失敗（DIAG-P03）

#### 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `role_id` | integer | 是 | 出租方身份 ID |
| `payment_id` | integer | 否 | 付款紀錄 ID |
| `bill_id` | integer | 否 | 帳單 ID（篩選該帳單相關的付款日誌） |
| `transaction_id` | string | 否 | 交易編號 |
| `page` | integer | 否 | 頁碼 |
| `per_page` | integer | 否 | 每頁筆數 |

#### 回應欄位

```json
{
  "success": true,
  "mapping": {
    "action": {
      "credit_card": "信用卡",
      "atm": "ATM 轉帳",
      "cvs": "超商代碼",
      "cvs_barcode": "超商條碼",
      "icashpay": "愛金卡",
      "google_pay": "Google Pay",
      "samsung_pay": "Samsung Pay"
    },
    "type": {
      "bill": "帳單付款",
      "subscription": "訂閱付款",
      "topup": "儲值"
    }
  },
  "data": [
    {
      "id": 50001,
      "role_id": 200,
      "payment_id": 9876,
      "transaction_id": "TXN20260401123456",
      "manufacturer": "newebpay",
      "action": "credit_card",
      "type": "bill",
      "amount": "25000",
      "note": "信用卡授權失敗",
      "response": {
        "Status": "LIB10002",
        "Message": "信用卡授權失敗，請確認卡片資訊"
      },
      "created_at": "2026-04-01T14:00:00+08:00"
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

#### 安全過濾說明

`response` 欄位經過安全過濾處理，僅保留錯誤碼與錯誤訊息相關的 key（如 `Status`、`Message`、`Result`、`RtnCode`、`RtnMsg`），信用卡號、token 等敏感資訊已移除。

---

### 2.10 GET `/api/external/v1/invoice-logs`

**說明**：查詢發票開立/作廢的 API 日誌（錯誤碼、回應資料）

> 此端點用於診斷：發票沒開出來（DIAG-I01）、發票作廢不了（DIAG-I02）

#### 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `role_id` | integer | 是 | 出租方身份 ID |
| `invoice_id` | integer | 否 | 發票 ID |
| `bill_id` | integer | 否 | 帳單 ID |
| `action` | string | 否 | 操作類型篩選（issue=開立、invalid=作廢、allowance=折讓） |
| `page` | integer | 否 | 頁碼 |
| `per_page` | integer | 否 | 每頁筆數 |

#### 回應欄位

```json
{
  "success": true,
  "mapping": {
    "action": {
      "issue": "開立",
      "invalid": "作廢",
      "allowance": "折讓",
      "allowance_invalid": "作廢折讓",
      "search": "查詢"
    }
  },
  "data": [
    {
      "id": 60001,
      "invoice_id": 5001,
      "bill_id": 12345,
      "manufacturer": "ezpay",
      "action": "issue",
      "type": "bill",
      "http_code": 200,
      "response_data": {
        "RtnCode": 1,
        "RtnMsg": "開立發票成功",
        "InvoiceNumber": "AZ00000123"
      },
      "note": null,
      "created_at": "2026-04-01T10:00:00+08:00"
    },
    {
      "id": 60002,
      "invoice_id": null,
      "bill_id": 12346,
      "manufacturer": "ezpay",
      "action": "issue",
      "type": "bill",
      "http_code": 200,
      "response_data": {
        "RtnCode": -1,
        "RtnMsg": "該期別已有發票，不可重複開立"
      },
      "note": "開立失敗",
      "created_at": "2026-04-02T09:30:00+08:00"
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

#### 安全過濾說明

`response_data` 欄位經過安全過濾處理，僅保留錯誤碼與處理狀態相關的 key（如 `RtnCode`、`RtnMsg`、`InvoiceNumber`），買方個資已移除。

---

### 2.11 GET `/api/external/v1/roles/{role_id}/subscription`

**說明**：查詢團隊的訂閱方案資訊與物件額度使用狀況

> 此端點用於診斷：不能新增物件（DIAG-E01）、物件突然全下架（DIAG-E02）、訂閱扣款失敗（DIAG-S01）

#### 路徑參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `role_id` | integer | 是 | 團隊（出租方）身份 ID |

#### 回應欄位

```json
{
  "success": true,
  "mapping": {
    "plan_type": {
      "trial": "試用",
      "basic": "基本",
      "advance": "進階"
    }
  },
  "data": {
    "role_id": 200,
    "is_subscribed": 1,
    "plan_id": 3,
    "plan_type": "advance",
    "plan_name": "進階方案",
    "plan_start_ymd": 20260101,
    "plan_end_ymd": 20261231,
    "plan_estate_limit": 50,
    "plan_contract_limit": 100,
    "plan_price": 2990.00,
    "plan_currency": "TWD",
    "plan_cycle": "monthly",
    "estate_usage": {
      "current_count": 35,
      "limit": 55,
      "remain": 20
    }
  }
}
```

#### 欄位說明

| 欄位 | 類型 | 說明 |
|------|------|------|
| `is_subscribed` | integer | 訂閱狀態（0=無訂閱、1=有訂閱） |
| `plan_type` | string | 方案類型（trial=試用、basic=基本、advance=進階） |
| `plan_start_ymd` | integer | 訂閱開始日期（YYYYMMDD） |
| `plan_end_ymd` | integer | 訂閱到期日期（YYYYMMDD） |
| `plan_estate_limit` | integer | 基本物件上限（0=無限制） |
| `estate_usage.current_count` | integer | 目前物件數量 |
| `estate_usage.limit` | integer | 總物件上限（基本額度 + 優惠碼贈送 + 額外加購） |
| `estate_usage.remain` | integer | 剩餘可新增物件數 |

#### 錯誤回應範例

**團隊不存在（404）**：

```json
{
  "success": false,
  "error": {
    "code": 404,
    "message": "團隊不存在"
  }
}
```

---

### 2.12 GET `/api/external/v1/iot-manufacturers`

**說明**：查詢團隊的 IoT 廠商綁定狀態

> 此端點用於診斷：IoT 綁定失敗（DIAG-IOT02）

#### 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `role_id` | integer | 是 | 出租方身份 ID |
| `page` | integer | 否 | 頁碼 |
| `per_page` | integer | 否 | 每頁筆數 |

#### 回應欄位

```json
{
  "success": true,
  "mapping": {
    "manufacturer": {
      "SkyWatch": "SkyWatch",
      "Miezo": "Miezo",
      "DAE": "DAE"
    }
  },
  "data": [
    {
      "id": 1,
      "role_id": 200,
      "manufacturer": "SkyWatch",
      "manufacturer_user_id": "user_abc123",
      "is_active": 1
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 50,
    "total": 1,
    "total_pages": 1,
    "has_more": false
  }
}
```

#### 欄位說明

| 欄位 | 類型 | 說明 |
|------|------|------|
| `manufacturer` | string | IoT 廠商名稱 |
| `manufacturer_user_id` | string | 廠商端帳號 ID |
| `is_active` | integer | 綁定啟用狀態（0=停用、1=啟用） |

> **安全性**：此端點不回傳 `manufacturer_password` 欄位。

---

### 2.13 合約查詢 API 擴充欄位（v1.1）

**說明**：`GET /api/external/v1/contracts/status-overview` 新增以下診斷用欄位

> 此擴充用於診斷：被收逾期費（DIAG-B03）、不能提前解約（DIAG-C04）

#### 新增回傳欄位

在現有合約回應的每筆合約物件中，新增以下欄位：

| 欄位 | 類型 | 說明 |
|------|------|------|
| `enable_late_fee` | integer | 是否啟用滯納金（0=否、1=是） |
| `calc_late_fee_buffer_days` | integer | 計算滯納金的緩衝天數 |
| `late_fee_percent` | float | 滯納金百分比 |
| `early_termination_penalty_type` | integer | 違約金類型（0=月份數、1=固定金額、2=參照補充條款） |
| `early_termination_penalty` | float | 違約金月數（當 type=0 時） |
| `early_termination_penalty_amount` | float | 違約金固定金額（當 type=1 時） |
| `early_termination_notice_date` | integer | 提前解約預告日期 |

#### 回應範例（新增欄位部分）

```json
{
  "enable_late_fee": 1,
  "calc_late_fee_buffer_days": 5,
  "late_fee_percent": 0.05,
  "early_termination_penalty_type": 0,
  "early_termination_penalty": 2.0,
  "early_termination_penalty_amount": 0.00,
  "early_termination_notice_date": 30
}
```

---

### 2.14 物件詳情 API 擴充欄位（v1.1）

**說明**：`GET /api/external/v1/estates/{id}` 新增簽約必填欄位檢查

> 此擴充用於診斷：簽約邀請發不出（DIAG-C01）、物件不能建合約（DIAG-E03）

#### 新增回傳欄位

在單一物件詳情回應中，新增 `contract_required_fields` 物件：

```json
{
  "contract_required_fields": {
    "all_filled": false,
    "fields": [
      { "field": "use_for", "label": "用途", "is_filled": true },
      { "field": "space_type", "label": "格局", "is_filled": true },
      { "field": "building", "label": "建築類型", "is_filled": false },
      { "field": "floor", "label": "所在樓層", "is_filled": true },
      { "field": "floor_all", "label": "總樓層", "is_filled": true },
      { "field": "title", "label": "物件標題", "is_filled": true },
      { "field": "size", "label": "面積", "is_filled": true },
      { "field": "rent", "label": "租金", "is_filled": true },
      { "field": "country_id", "label": "國家", "is_filled": true },
      { "field": "city_id", "label": "城市", "is_filled": true },
      { "field": "district_id", "label": "區域", "is_filled": true },
      { "field": "address", "label": "地址", "is_filled": true },
      { "field": "display_country_id", "label": "顯示國家", "is_filled": true },
      { "field": "display_city_id", "label": "顯示城市", "is_filled": true },
      { "field": "display_district_id", "label": "顯示區域", "is_filled": true },
      { "field": "display_address", "label": "顯示地址", "is_filled": true }
    ]
  }
}
```

#### 欄位說明

| 欄位 | 類型 | 說明 |
|------|------|------|
| `all_filled` | boolean | 所有必填欄位是否皆已填寫 |
| `fields[].field` | string | 欄位名稱 |
| `fields[].label` | string | 欄位顯示名稱 |
| `fields[].is_filled` | boolean | 該欄位是否已填寫 |

> **注意**：地址相關的必填欄位數量依國家而異。無子區域的國家僅需 `country_id` + `address`，有子區域的國家需 `country_id` + `city_id` + `district_id` + `address`。

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
