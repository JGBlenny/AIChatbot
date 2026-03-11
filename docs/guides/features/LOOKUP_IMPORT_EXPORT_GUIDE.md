# Lookup 批量匯入/匯出系統使用指南

**功能版本**: v1.0.0
**最後更新**: 2026-03-11
**適用對象**: 系統管理員、業者管理人員

---

## 目錄

1. [功能概述](#功能概述)
2. [使用場景](#使用場景)
3. [前端介面操作](#前端介面操作)
4. [Excel 匯入格式](#excel-匯入格式)
5. [API 端點使用](#api-端點使用)
6. [複合鍵查詢](#複合鍵查詢)
7. [常見問題](#常見問題)

---

## 功能概述

Lookup 系統提供業者專屬資料的批量管理功能，支援：

- ✅ **Excel 批量匯入** - 從業務格式 Excel 檔案匯入多分頁資料
- ✅ **Excel 匯出** - 匯出現有資料為標準格式 Excel
- ✅ **前端視覺化管理** - 統計查看、批量刪除
- ✅ **CRUD 操作** - 完整的建立、讀取、更新、刪除功能
- ✅ **複合鍵查詢** - 支援多層級查詢（如地址+停車位編號）
- ✅ **查詢全部功能** - 快速查詢某個 key 的所有子項目

---

## 使用場景

### 場景 1：新業者資料匯入
當新業者加入時，可批量匯入包含水費、電費、停車位、公共設施等各類資料：

```
1. 準備業務格式 Excel（14 個分頁）
2. 前端上傳匯入
3. 系統自動轉換為 Lookup 格式
4. 聊天機器人即可查詢使用
```

### 場景 2：資料更新
業者資訊變更時（如電費繳費日、停車位分配），可快速更新：

```
1. 匯出現有資料
2. 在 Excel 中修改
3. 重新匯入（系統會自動覆蓋）
```

### 場景 3：聊天機器人查詢
租客透過聊天機器人查詢時，表單填寫後自動調用 Lookup API：

```
租客: "我的電費幾號繳？"
系統: [觸發表單填寫地址]
租客: "台北市大安區信義路三段123號4樓之2"
系統: [調用 /api/lookup?category=billing_interval&key=地址]
回應: "單月"
```

---

## 前端介面操作

### 1. 進入 Lookup 管理介面

路徑: `業者配置 > 選擇業者 > Lookup 數據` 標籤

![Lookup 標籤位置](../../images/lookup-tab.png)

### 2. 查看統計資訊

介面顯示：
- 各分類的記錄數量
- 總記錄數
- 更新時間

```
🌍 地區代碼: 2 筆
🔢 電號列表: 5 筆
💡 電費資訊: 5 筆
...
總計: 86 筆記錄
```

### 3. 匯入資料

**步驟：**

1. 點擊「📤 匯入 Lookup」按鈕
2. 選擇業務格式 Excel 檔案
3. 系統自動上傳並轉換
4. 顯示匯入結果（成功/失敗數量）

**Excel 格式要求：**
- 必須包含 14 個指定分頁
- 每個分頁的欄位名稱需符合規範
- 參考範本：`rag-orchestrator/templates/Lookup匯入範本.xlsx`

### 4. 匯出資料

**步驟：**

1. 點擊「📥 匯出 Lookup」按鈕
2. 系統生成標準格式 Excel
3. 自動下載檔案
4. 檔名格式：`Lookup_資料_vendor{vendor_id}_{timestamp}.xlsx`

### 5. 批量刪除

**步驟：**

1. 點擊「🗑️ 清除 Lookup」按鈕
2. 確認對話框顯示記錄數量：`真的要刪除所有 86 筆 Lookup 記錄嗎？`
3. 確認後刪除該業者的所有 Lookup 資料

⚠️ **警告**：刪除操作無法復原，建議先匯出備份！

---

## Excel 匯入格式

### 業務格式 Excel 結構

匯入的 Excel 需包含 **14 個分頁**：

| 分頁名稱 | 說明 | 產生的 category |
|---------|------|----------------|
| 地區代碼 | 行政區對應代碼 | `region_code` |
| 電號列表 | 物件地址與電號對應 | `electric_number` |
| 電費資訊 | 電費繳費資訊 | `billing_interval`, `billing_method`, `meter_reading_day` |
| 水號列表 | 物件地址與水號對應 | `water_number` |
| 水費資訊 | 水費繳費資訊 | `water_billing_interval`, `water_billing_method`, `water_meter_reading_day` |
| 停車位資訊 | 停車位分配與收費 | `parking_fee`, `parking_type` |
| 公共設施 | 公共設施使用規則 | `facility_hours`, `facility_booking`, `facility_fee` |
| 管理費 | 管理費繳費方式 | `management_fee`, `management_fee_method` |
| 門禁卡 | 門禁卡申請流程 | `access_card_process`, `access_card_fee` |
| 垃圾清運 | 垃圾清運時間 | `trash_collection_time`, `trash_collection_location` |
| 租約條款 | 租約特殊條款 | `lease_terms` |
| 寵物政策 | 寵物飼養規定 | `pet_policy`, `pet_deposit` |
| 裝修規範 | 裝修申請流程 | `renovation_rules`, `renovation_approval` |
| 緊急聯絡 | 緊急聯絡資訊 | `emergency_contact`, `emergency_phone` |

### Excel 欄位範例

**電費資訊分頁：**

| 物件地址（必填） | 繳費週期 | 繳費方式 | 抄表日 |
|----------------|---------|---------|--------|
| 台北市大安區信義路三段123號4樓之2 | 單月 | 轉帳 | 5 |
| 台北市大安區信義路三段123號5樓之1 | 雙月 | 現金 | 10 |

**停車位資訊分頁：**

| 物件地址（必填） | 停車位編號 | 月租費用 | 停車位類型 |
|----------------|-----------|---------|-----------|
| 台北市大安區信義路三段123號 | B1-001 | 3000 | 平面 |
| 台北市大安區信義路三段123號 | B1-002 | 3500 | 機械 |

### 轉換邏輯

系統會自動將業務格式轉換為 Lookup Table 格式：

**轉換前（電費資訊）：**
```
物件地址: 台北市大安區信義路三段123號4樓之2
繳費週期: 單月
繳費方式: 轉帳
抄表日: 5
```

**轉換後（3 筆 Lookup 記錄）：**
```json
[
  {
    "category": "billing_interval",
    "lookup_key": "台北市大安區信義路三段123號4樓之2",
    "lookup_value": "單月",
    "metadata": {"electric_number": "01190293109"}
  },
  {
    "category": "billing_method",
    "lookup_key": "台北市大安區信義路三段123號4樓之2",
    "lookup_value": "轉帳"
  },
  {
    "category": "meter_reading_day",
    "lookup_key": "台北市大安區信義路三段123號4樓之2",
    "lookup_value": "5"
  }
]
```

---

## API 端點使用

### 基本查詢

**端點**: `GET /api/lookup`

**參數**:
- `category` (必填): 查詢類別
- `key` (必填): 查詢鍵值
- `key2` (選填): 第二層鍵值（複合鍵）
- `vendor_id` (必填): 業者 ID

**範例 1：查詢電費繳費週期**

```bash
curl -X GET "http://localhost:8100/api/lookup?category=billing_interval&key=台北市大安區信義路三段123號4樓之2&vendor_id=2"
```

**回應**:
```json
{
  "success": true,
  "match_type": "exact",
  "category": "billing_interval",
  "key": "台北市大安區信義路三段123號4樓之2",
  "value": "單月",
  "note": "您的電費帳單將於每【單月】寄送。",
  "metadata": {
    "electric_number": "01190293109"
  }
}
```

### 複合鍵查詢

**範例 2：查詢特定停車位費用**

```bash
curl -X GET "http://localhost:8100/api/lookup?category=parking_fee&key=台北市大安區信義路三段123號&key2=B1-001&vendor_id=2"
```

**回應**:
```json
{
  "success": true,
  "match_type": "exact",
  "category": "parking_fee",
  "key": "台北市大安區信義路三段123號_B1-001",
  "value": "3000",
  "note": "停車位 B1-001 的月租費用為 3000 元。"
}
```

### 查詢全部子項目

**範例 3：查詢某地址的所有停車位**

```bash
curl -X GET "http://localhost:8100/api/lookup?category=parking_fee&key=台北市大安區信義路三段123號&key2=全部&vendor_id=2"
```

**回應**:
```json
{
  "success": true,
  "match_type": "multiple",
  "category": "parking_fee",
  "key": "台北市大安區信義路三段123號",
  "results": [
    {
      "key2": "B1-001",
      "value": "3000",
      "note": "停車位 B1-001 的月租費用為 3000 元。"
    },
    {
      "key2": "B1-002",
      "value": "3500",
      "note": "停車位 B1-002 的月租費用為 3500 元。"
    }
  ],
  "count": 2
}
```

### 批量匯入

**端點**: `POST /api/lookup/import`

```bash
curl -X POST "http://localhost:8100/api/lookup/import?vendor_id=2" \
  -F "file=@Vendor2_知識資料.xlsx"
```

**回應**:
```json
{
  "success": true,
  "message": "成功匯入 86 筆記錄",
  "total_records": 86,
  "categories": {
    "billing_interval": 5,
    "billing_method": 5,
    "meter_reading_day": 5,
    "parking_fee": 12,
    ...
  }
}
```

### 匯出資料

**端點**: `GET /api/lookup/export`

```bash
curl -X GET "http://localhost:8100/api/lookup/export?vendor_id=2" \
  -o "lookup_export.xlsx"
```

### CRUD 操作

**建立記錄**: `POST /api/lookup`
```bash
curl -X POST "http://localhost:8100/api/lookup" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "billing_interval",
    "lookup_key": "台北市大安區信義路三段125號",
    "lookup_value": "單月",
    "vendor_id": 2
  }'
```

**更新記錄**: `PUT /api/lookup/{id}`
```bash
curl -X PUT "http://localhost:8100/api/lookup/123" \
  -H "Content-Type: application/json" \
  -d '{
    "lookup_value": "雙月"
  }'
```

**刪除記錄**: `DELETE /api/lookup/{id}`
```bash
curl -X DELETE "http://localhost:8100/api/lookup/123"
```

**批量刪除**: `DELETE /api/lookup/batch`
```bash
curl -X DELETE "http://localhost:8100/api/lookup/batch?vendor_id=2"
```

---

## 複合鍵查詢

### 什麼是複合鍵？

某些業務場景需要兩層查詢，例如：
- **停車位**: 地址 + 停車位編號
- **公共設施**: 地址 + 設施名稱

系統將複合鍵存儲為 `key1_key2` 格式。

### 使用方式

**1. 查詢特定項目**

查詢「台北市大安區信義路三段123號」的「B1-001」停車位：

```bash
GET /api/lookup?category=parking_fee&key=台北市大安區信義路三段123號&key2=B1-001
```

**2. 查詢所有項目**

查詢「台北市大安區信義路三段123號」的所有停車位（使用 `key2=全部`）：

```bash
GET /api/lookup?category=parking_fee&key=台北市大安區信義路三段123號&key2=全部
```

### 在表單中配置

在 `api_endpoints` 表的 `static_params` 配置：

```json
{
  "category": "parking_fee",
  "key2": "全部"
}
```

在 `params_from_form` 配置表單欄位映射：

```json
{
  "key": "address"
}
```

這樣當用戶填寫「地址」欄位後，系統會自動查詢該地址的所有停車位。

---

## 常見問題

### Q1: 匯入失敗，提示「重複的 (category, lookup_key) 組合」

**原因**: Excel 中存在相同分類和鍵值的重複記錄。

**解決方案**:
1. 匯出現有資料檢查是否已存在
2. 先執行「清除 Lookup」刪除舊資料
3. 修正 Excel 中的重複記錄後重新匯入

### Q2: 查詢沒有結果

**檢查項目**:
- ✅ `vendor_id` 是否正確
- ✅ `category` 是否拼寫正確
- ✅ `key` 是否完全一致（包括空格、標點符號）
- ✅ 資料庫中是否已匯入該筆記錄

### Q3: 複合鍵查詢失敗

**常見錯誤**:
```bash
# 錯誤：未提供 key2
GET /api/lookup?category=parking_fee&key=地址

# 正確：提供 key2
GET /api/lookup?category=parking_fee&key=地址&key2=B1-001
# 或查詢全部
GET /api/lookup?category=parking_fee&key=地址&key2=全部
```

### Q4: 批量刪除顯示 0 筆

**原因**: 前端計算邏輯錯誤或無資料。

**檢查方式**:
```bash
# 查詢統計
GET /api/lookup/stats?vendor_id=2
```

如果返回資料但前端顯示 0，請檢查前端 `VendorLookupManager.vue` 是否正確計算 `totalRecords`。

### Q5: Excel 匯出後中文亂碼

**解決方案**:
- 使用 Excel 2016+ 或 WPS 開啟
- 或用記事本開啟 CSV，選擇 UTF-8 編碼後另存

### Q6: 如何重新匯入（更新資料）？

**步驟**:
1. 不需要先刪除，直接匯入
2. 系統會檢測相同的 `(category, lookup_key)` 並更新
3. 如果要完全替換，建議先「清除 Lookup」再匯入

---

## 技術細節

### 資料庫 Schema

```sql
CREATE TABLE lookup_tables (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    category VARCHAR(100) NOT NULL,
    lookup_key VARCHAR(500) NOT NULL,
    lookup_value TEXT,
    metadata JSONB,
    note TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(vendor_id, category, lookup_key)
);

CREATE INDEX idx_lookup_tables_vendor_category
ON lookup_tables(vendor_id, category);
```

### 轉換函數

位置: `rag-orchestrator/routers/lookup.py`

函數: `_convert_business_to_lookup_format(excel_file, vendor_id)`

支援的分頁轉換：
- 簡單映射（1 行 → 1 記錄）
- 複雜映射（1 行 → 多記錄，如電費資訊）
- 複合鍵映射（如停車位、公共設施）

---

## 相關資源

- **API 完整清單**: [docs/API_ENDPOINTS_COMPLETE_INVENTORY.md](../../API_ENDPOINTS_COMPLETE_INVENTORY.md)
- **範本檔案**: `rag-orchestrator/templates/Lookup匯入範本.xlsx`
- **前端元件**: `knowledge-admin/frontend/src/components/VendorLookupManager.vue`
- **後端路由**: `rag-orchestrator/routers/lookup.py`
- **表單整合**: `rag-orchestrator/services/form_manager.py`

---

**更新日誌**:
- 2026-03-11: 初版發布，支援批量匯入/匯出、CRUD、複合鍵查詢
