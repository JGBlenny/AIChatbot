# SOP Excel 匯入功能說明

## 📋 功能概述

提供完整的 Web UI Excel 匯入功能，支援從 Excel 文件批量導入 SOP 到業者系統。

---

## 🏗️ 架構設計

### 代碼重用原則

所有 SOP 相關的共用邏輯統一在 **`services/sop_utils.py`** 中：

```
services/sop_utils.py
├── parse_sop_excel()                    # Excel 解析（三層結構）
├── identify_cashflow_sensitive_items()  # 金流判斷共用函數
└── (未來可擴展其他 SOP 工具函數)

使用位置：
├── routers/vendors.py                   # 業者 SOP Excel 匯入 API
└── routers/platform_sop.py              # 平台 SOP Excel 匯入 API
```

**優點：**
- ✅ 避免代碼重複
- ✅ 邏輯統一管理
- ✅ 三層結構（Categories → Groups → Items）
- ✅ 易於維護和測試

---

## 🔧 金流欄位處理

### 資料庫結構

`vendor_sop_items` 表包含以下金流相關欄位：

| 欄位 | 類型 | 說明 |
|-----|------|------|
| `requires_cashflow_check` | BOOLEAN | 是否需要金流判斷 |
| `cashflow_through_company` | TEXT | 金流過公司的內容版本 |
| `cashflow_direct_to_landlord` | TEXT | 金流直接給房東的內容版本 |

### 運作邏輯

1. **導入時自動識別**：
   ```python
   from services.sop_utils import identify_cashflow_sensitive_items

   cashflow_info = identify_cashflow_sensitive_items(item_name, content)
   # 返回：
   # {
   #   'requires_cashflow': bool,
   #   'through_company': str or None,
   #   'direct_to_landlord': str or None
   # }
   ```

2. **查詢時動態選擇**：
   - 系統根據業者的 `vendors.cashflow_model` 欄位選擇對應版本
   - `through_company` → 使用 `cashflow_through_company` 內容
   - `direct_to_landlord` → 使用 `cashflow_direct_to_landlord` 內容

### 識別關鍵字

系統自動識別以下關鍵字作為金流敏感項目：
```python
['租金支付', '繳費', '收據', '發票', '遲付', '押金', '帳戶', '匯款']
```

### 預設內容模板

| 項目類型 | 過公司版本 | 直接房東版本 |
|---------|-----------|-------------|
| 押金 | 押金由公司收取並專戶保管... | 押金由房東收取，請與房東確認... |
| 租金支付方式 | 登入JGB系統查看公司收款帳號... | 請向房東索取收款帳號... |
| 租金提醒通知 | JGB系統會提前發送提醒，並在收款後通知... | JGB系統會提前發送提醒，請自行與房東確認... |
| 收據或發票 | JGB系統會自動生成收據或電子發票... | 請向房東索取收據... |

---

## 📤 Excel 匯入 API

### 端點

```
POST /api/v1/vendors/{vendor_id}/sop/import-excel
```

### 參數

| 參數 | 類型 | 必填 | 說明 |
|-----|------|------|------|
| `file` | File | ✅ | Excel 文件（.xlsx 或 .xls） |
| `overwrite` | Query | ❌ | 是否覆蓋現有 SOP（預設 false） |

### Excel 格式要求

| 欄位位置 | 欄位名稱 | 說明 | 範例 |
|---------|---------|------|------|
| 第一欄 | 分類名稱 | 新分類的名稱 | 租賃流程相關資訊 |
| 第二欄 | 分類說明 | 分類的描述 | 租賃申請流程：介紹如何申請租賃... |
| 第三欄 | 項目序號 | 項目編號（整數） | 1, 2, 3... |
| 第四欄 | 項目名稱 | SOP 項目標題 | 申請步驟： |
| 第五欄 | 項目內容 | SOP 項目的詳細內容 | 租客首先需要在線提交租賃申請表... |

### 回應範例

**成功：**
```json
{
  "message": "成功從 Excel 匯入 4 個分類、56 個 SOP 項目，已觸發背景 embedding 生成",
  "vendor_id": 2,
  "vendor_name": "信義包租代管股份有限公司",
  "file_name": "租管業 SOP.xlsx",
  "created_categories": 4,
  "created_items": 56,
  "embedding_generation_triggered": 56
}
```

**錯誤（已有 SOP）：**
```json
{
  "detail": "業者已有 30 個 SOP 項目，如需覆蓋請設定 overwrite=true"
}
```

---

## 🖥️ Web UI 使用

### 操作步驟

1. 訪問：`http://localhost:8087/vendors/{vendor_id}/configs`
2. 切換到「📝 我的 SOP」標籤
3. 點擊「📤 匯入 Excel」按鈕
4. 選擇 Excel 文件（系統會顯示格式說明）
5. 確認匯入

### 功能特性

- ✅ 檔案格式驗證（只接受 .xlsx 和 .xls）
- ✅ 檔案大小限制（最大 10MB）
- ✅ 覆蓋警告提示（當已有 SOP 時）
- ✅ Excel 格式說明顯示
- ✅ 上傳進度提示

---

## 🧪 測試驗證

### 功能測試

```bash
# 測試 API 匯入
curl -X POST "http://localhost:8100/api/v1/vendors/2/sop/import-excel?overwrite=true" \
  -F "file=@你的文件.xlsx"

# 驗證金流欄位
psql -d aichatbot_admin -c "
SELECT
  COUNT(*) FILTER (WHERE requires_cashflow_check = TRUE) as cashflow_items,
  COUNT(*) as total_items
FROM vendor_sop_items vsi
JOIN vendor_sop_categories vsc ON vsi.category_id = vsc.id
WHERE vsc.vendor_id = 2;
"
```

### 預期結果

使用範例文件 `20250305 租管業 SOP_2 管理模式 基礎-改.xlsx`：

```
✅ 總項目數：56 個
✅ 金流敏感項目：11 個（19.6%）
✅ 分類數：4 個
✅ Embeddings：56 個（100% 生成）
```

---

## 📝 維護指南

### 添加新的金流模板

編輯 `services/sop_utils.py` 中的 `identify_cashflow_sensitive_items()` 函數：

```python
elif '新的金流項目' in item_name:
    versions['through_company'] = "過公司的處理方式..."
    versions['direct_to_landlord'] = "直接房東的處理方式..."
```

### 修改金流關鍵字

修改 `cashflow_keywords` 列表：

```python
cashflow_keywords = ['租金支付', '繳費', '收據', '發票', '遲付', '押金', '帳戶', '匯款', '新關鍵字']
```

---

## ⚠️ 注意事項

1. **覆蓋模式**：設定 `overwrite=true` 會刪除所有現有 SOP
2. **空內容項目**：Excel 中允許項目內容為空（用於詞彙定義等）
3. **換行符處理**：系統自動清理分類名稱中的換行符
4. **Embedding 生成**：背景批量生成，不阻塞匯入流程
5. **金流判斷**：自動識別並生成兩個版本，查詢時根據業者金流模式動態選擇

---

## 🎯 相關文件

- 業者 SOP API：`rag-orchestrator/routers/vendors.py` (Line 2017: `import_sop_from_excel`)
- 平台 SOP API：`rag-orchestrator/routers/platform_sop.py` (Line 1053: `import_sop_from_excel`)
- 前端 UI：`knowledge-admin/frontend/src/components/VendorSOPManager.vue`
- 共用工具：`rag-orchestrator/services/sop_utils.py`
- 測試文件：`data/20250305 租管業 SOP_2 管理模式 基礎-改.xlsx`
