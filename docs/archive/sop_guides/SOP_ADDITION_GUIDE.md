# SOP 新增操作指南

## 📋 目錄

1. [SOP 架構說明](#sop-架構說明)
2. [新增方法概覽](#新增方法概覽)
3. [方法 1: 使用 SQL 直接新增](#方法-1-使用-sql-直接新增)
4. [方法 2: 使用 Excel 批次匯入](#方法-2-使用-excel-批次匯入)
5. [方法 3: 透過 API 新增](#方法-3-透過-api-新增)
6. [多版本內容設計](#多版本內容設計)
7. [關聯意圖設定](#關聯意圖設定)
8. [測試與驗證](#測試與驗證)
9. [最佳實踐與注意事項](#最佳實踐與注意事項)

---

## SOP 架構說明

### 資料庫結構

系統使用兩個核心資料表來儲存 SOP：

#### 1. `vendor_sop_categories` - SOP 分類表

```sql
CREATE TABLE vendor_sop_categories (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER REFERENCES vendors(id),
    category_name VARCHAR(200) NOT NULL,       -- 分類名稱
    description TEXT,                          -- 分類說明
    display_order INTEGER DEFAULT 0,           -- 顯示順序
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**分類範例**：
- 租賃流程相關資訊
- 租金繳費相關
- 維護修繕相關
- 合約條款相關

#### 2. `vendor_sop_items` - SOP 項目表

```sql
CREATE TABLE vendor_sop_items (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES vendor_sop_categories(id),
    vendor_id INTEGER REFERENCES vendors(id),

    -- 項目基本資訊
    item_number INTEGER,                          -- 項次（如：1, 2, 3）
    item_name VARCHAR(200),                       -- 項目名稱
    content TEXT NOT NULL,                        -- 基礎內容（通用版本）

    -- 金流模式相關（支援動態調整）
    requires_cashflow_check BOOLEAN DEFAULT FALSE,
    cashflow_through_company TEXT,                -- 金流過我家版本
    cashflow_direct_to_landlord TEXT,             -- 金流不過我家版本
    cashflow_mixed TEXT,                          -- 混合型版本

    -- 業種類型相關
    requires_business_type_check BOOLEAN DEFAULT FALSE,
    business_type_full_service TEXT,              -- 包租型語氣
    business_type_management TEXT,                -- 代管型語氣

    -- 關聯與優先級
    related_intent_id INTEGER REFERENCES intents(id),
    priority INTEGER DEFAULT 0,

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 業者屬性設定

每個業者有兩個關鍵屬性影響 SOP 內容選擇：

```sql
ALTER TABLE vendors
ADD COLUMN business_type VARCHAR(50) DEFAULT 'property_management',
ADD COLUMN cashflow_model VARCHAR(50) DEFAULT 'direct_to_landlord';
```

**業種類型 (business_type)**：
- `full_service` - 包租型
- `property_management` - 代管型

**金流模式 (cashflow_model)**：
- `through_company` - 金流過我家
- `direct_to_landlord` - 金流不過我家
- `mixed` - 混合型

---

## 新增方法概覽

| 方法 | 適用場景 | 優點 | 缺點 |
|------|---------|------|------|
| **SQL 直接新增** | 新增少量 SOP、快速測試 | 靈活、即時生效 | 需要 DB 權限、不適合批次 |
| **Excel 批次匯入** | 初次建立、大量新增 | 一次匯入完整結構、可視化編輯 | 需要準備 Excel、格式固定 |
| **API 新增** | 程式化整合、介面開發 | 可整合至管理介面、自動化 | 目前僅支援更新，需擴充 |

---

## 方法 1: 使用 SQL 直接新增

### 步驟 1: 建立分類

```sql
-- 為業者 1 建立新的 SOP 分類
INSERT INTO vendor_sop_categories (vendor_id, category_name, description, display_order)
VALUES
    (1, '寵物飼養規定', '寵物飼養許可、限制、費用與責任', 10)
RETURNING id;  -- 記下返回的 category_id
```

### 步驟 2: 新增 SOP 項目

#### 範例 1: 不需要金流判斷的項目

```sql
-- 通用型 SOP（不分金流模式）
INSERT INTO vendor_sop_items (
    category_id,
    vendor_id,
    item_number,
    item_name,
    content,
    requires_cashflow_check,
    related_intent_id,
    priority
) VALUES (
    123,  -- 使用上一步返回的 category_id
    1,    -- vendor_id
    1,
    '是否允許飼養寵物',
    '本物業允許房客飼養寵物，但需遵守以下規定：1) 事前書面申請並獲得同意 2) 僅限小型犬貓，體重不超過10公斤 3) 需繳交寵物押金NT$5,000元',
    FALSE,  -- 不需要金流判斷
    15,     -- 關聯到「寵物飼養」意圖 ID
    100
);
```

#### 範例 2: 需要金流判斷的項目

```sql
-- 金流敏感型 SOP（會根據業者金流模式動態調整內容）
INSERT INTO vendor_sop_items (
    category_id,
    vendor_id,
    item_number,
    item_name,
    content,
    requires_cashflow_check,
    cashflow_through_company,
    cashflow_direct_to_landlord,
    related_intent_id,
    priority
) VALUES (
    123,
    1,
    2,
    '寵物押金如何繳交',
    '寵物押金可透過多種方式繳納',  -- 基礎內容
    TRUE,  -- 需要金流判斷
    '登入 JGB 系統查看公司收款帳號，寵物押金為NT$5,000元，可通過銀行轉帳或信用卡支付。系統會在收款後主動通知您。',  -- 金流過我家版本
    '請向房東索取收款帳號，寵物押金為NT$5,000元，建議使用銀行轉帳並留存交易記錄。JGB 系統僅提供繳款提醒服務。',  -- 金流不過我家版本
    15,
    90
);
```

### 步驟 3: 批次新增多個項目

```sql
-- 使用 DO 區塊批次新增
DO $$
DECLARE
    cat_id INTEGER;
    intent_id_pet INTEGER := 15;  -- 寵物飼養意圖 ID
BEGIN
    -- 建立分類
    INSERT INTO vendor_sop_categories (vendor_id, category_name, description, display_order)
    VALUES (1, '寵物飼養規定', '寵物相關政策與規定', 10)
    RETURNING id INTO cat_id;

    -- 項目 1: 寵物飼養許可
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check, related_intent_id, priority
    ) VALUES (
        cat_id, 1, 1, '是否允許飼養寵物',
        '本物業允許飼養小型寵物（貓、狗），體重不超過10公斤，需事前申請並獲得同意。',
        FALSE, intent_id_pet, 100
    );

    -- 項目 2: 寵物押金（金流敏感）
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check,
        cashflow_through_company,
        cashflow_direct_to_landlord,
        related_intent_id, priority
    ) VALUES (
        cat_id, 1, 2, '寵物押金繳納方式',
        '寵物押金為NT$5,000元',
        TRUE,
        '登入 JGB 系統查看公司收款帳號繳納寵物押金NT$5,000元，可使用銀行轉帳或信用卡。',
        '請向房東索取收款帳號繳納寵物押金NT$5,000元，建議使用銀行轉帳並保留收據。',
        intent_id_pet, 90
    );

    -- 項目 3: 寵物規範
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check, related_intent_id, priority
    ) VALUES (
        cat_id, 1, 3, '寵物飼養規範',
        '房客需確保寵物不影響鄰居，包括：1) 控制噪音 2) 定期清潔 3) 不得在公共區域排泄 4) 外出需使用牽繩。違規者將收到警告，嚴重者可能終止租約。',
        FALSE, intent_id_pet, 80
    );

    -- 項目 4: 寵物押金退還（金流敏感）
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check,
        cashflow_through_company,
        cashflow_direct_to_landlord,
        related_intent_id, priority
    ) VALUES (
        cat_id, 1, 4, '寵物押金退還',
        '租約結束後，寵物押金將依據房屋狀況退還',
        TRUE,
        '寵物押金由公司專戶保管，租約結束後會進行房屋檢查，若無損壞將於7個工作天內退還至您指定帳戶。',
        '寵物押金由房東保管，租約結束後請與房東確認退還時間與方式。',
        1, 70  -- 關聯到退租流程
    );

END $$;
```

### 步驟 4: 驗證新增結果

```sql
-- 查詢剛才新增的 SOP
SELECT
    v.name AS vendor_name,
    sc.category_name,
    si.item_number,
    si.item_name,
    si.requires_cashflow_check,
    i.name AS intent_name
FROM vendor_sop_items si
INNER JOIN vendor_sop_categories sc ON si.category_id = sc.id
INNER JOIN vendors v ON si.vendor_id = v.id
LEFT JOIN intents i ON si.related_intent_id = i.id
WHERE sc.category_name = '寵物飼養規定'
ORDER BY si.item_number;
```

---

## 方法 2: 使用 Excel 批次匯入

### 步驟 1: 準備 Excel 文件

**檔案位置**: `data/20250305 real_estate_rental_knowledge_base SOP.xlsx`

**Excel 結構**（Sheet1）：

| 分類 | 說明 | 序號 | 項目 | 內容 | JGB範本 | 愛租屋管理制度 | 備註 |
|------|------|------|------|------|---------|---------------|------|
| 寵物飼養規定 | 寵物飼養許可、限制、費用與責任 | 1 | 是否允許飼養寵物 | 本物業允許飼養小型寵物... | | | |
| | | 2 | 寵物押金繳納方式 | 寵物押金為NT$5,000元... | | | |
| | | 3 | 寵物飼養規範 | 房客需確保寵物不影響鄰居... | | | |

**欄位說明**：
- **分類**: 只在該分類的第一行填寫，其他留空
- **說明**: 分類的詳細說明
- **序號**: SOP 項目的順序編號（1, 2, 3...）
- **項目**: SOP 項目名稱
- **內容**: SOP 項目的基礎內容

### 步驟 2: 執行匯入腳本

```bash
# 進入專案目錄
cd /Users/lenny/jgb/AIChatbot

# 執行匯入腳本
python3 scripts/import_sop_from_excel.py
```

### 步驟 3: 匯入腳本說明

匯入腳本會自動：

1. **解析 Excel 結構**
2. **識別金流敏感項目**（根據關鍵字）
3. **生成不同版本內容**（金流過我家 vs. 不過我家）
4. **批次插入資料庫**

**自動識別的金流敏感關鍵字**：
- 租金支付、繳費、收據、發票
- 遲付、押金、帳戶、匯款

### 步驟 4: 客製化金流敏感邏輯

如果需要自訂金流版本內容，請編輯 `scripts/import_sop_from_excel.py`:

```python
def identify_cashflow_sensitive_items(item_name: str, content: str) -> dict:
    """識別是否需要金流模式判斷"""

    # 新增寵物相關的金流判斷
    if '寵物押金' in item_name:
        versions = {
            'through_company': "登入 JGB 系統繳納寵物押金...",
            'direct_to_landlord': "請向房東繳納寵物押金..."
        }
        return {
            'requires_cashflow': True,
            'through_company': versions['through_company'],
            'direct_to_landlord': versions['direct_to_landlord']
        }

    # 其他邏輯...
```

---

## 方法 3: 透過 API 新增

### 目前可用的 API 端點

#### 1. 讀取 SOP 分類

```bash
GET http://localhost:8100/api/v1/vendors/{vendor_id}/sop/categories
```

**回應範例**：
```json
[
    {
        "id": 1,
        "category_name": "租賃流程相關資訊",
        "description": "租賃申請流程、合約簽訂等",
        "display_order": 1
    }
]
```

#### 2. 讀取 SOP 項目

```bash
GET http://localhost:8100/api/v1/vendors/{vendor_id}/sop/items?category_id={category_id}
```

**回應範例**：
```json
[
    {
        "id": 1,
        "category_id": 1,
        "vendor_id": 1,
        "item_number": 1,
        "item_name": "申請步驟",
        "content": "租客首先需要...",
        "requires_cashflow_check": false,
        "cashflow_through_company": null,
        "cashflow_direct_to_landlord": null,
        "related_intent_id": 5,
        "related_intent_name": "租賃申請流程",
        "created_at": "2025-10-18T10:00:00",
        "updated_at": "2025-10-18T10:00:00"
    }
]
```

#### 3. 更新 SOP 項目

```bash
PUT http://localhost:8100/api/v1/vendors/{vendor_id}/sop/items/{item_id}
Content-Type: application/json

{
    "item_name": "寵物押金繳納方式",
    "content": "寵物押金為NT$5,000元",
    "requires_cashflow_check": true,
    "cashflow_through_company": "登入 JGB 系統繳納寵物押金...",
    "cashflow_direct_to_landlord": "請向房東繳納寵物押金...",
    "related_intent_id": 15
}
```

### 未來擴充建議

目前 API **缺少新增功能**，建議擴充以下端點：

```python
# 待實作：新增 SOP 分類
@router.post("/{vendor_id}/sop/categories")
async def create_sop_category(vendor_id: int, category: SOPCategoryCreate):
    """建立新的 SOP 分類"""
    pass

# 待實作：新增 SOP 項目
@router.post("/{vendor_id}/sop/items")
async def create_sop_item(vendor_id: int, item: SOPItemCreate):
    """建立新的 SOP 項目"""
    pass
```

---

## 多版本內容設計

### 金流模式版本設計

當 `requires_cashflow_check = TRUE` 時，系統會根據業者的 `cashflow_model` 自動選擇對應版本：

| 業者金流模式 | 使用欄位 |
|-------------|---------|
| `through_company` | `cashflow_through_company` |
| `direct_to_landlord` | `cashflow_direct_to_landlord` |
| `mixed` | `cashflow_mixed` |

**設計原則**：

1. **金流過我家** (through_company)
   - 強調「公司收款」「系統自動處理」「主動通知」
   - 範例：「登入 JGB 系統查看公司收款帳號...」

2. **金流不過我家** (direct_to_landlord)
   - 強調「房東收款」「自行確認」「系統僅提醒」
   - 範例：「請向房東索取收款帳號...JGB 僅提供提醒服務」

3. **混合型** (mixed)
   - 提供兩種選項，讓房客選擇
   - 範例：「您可選擇向公司或房東繳納，請先確認您的租約類型」

### 業種類型版本設計

當 `requires_business_type_check = TRUE` 時，系統會根據 `business_type` 調整語氣：

| 業種類型 | 語氣特色 | 使用欄位 |
|---------|---------|---------|
| `full_service` (包租型) | 更正式、公司化、主動服務 | `business_type_full_service` |
| `property_management` (代管型) | 較彈性、協助性質 | `business_type_management` |

**範例**：

```sql
-- 包租型語氣
business_type_full_service = '我們公司將全權處理您的租金帳務，包含收款、開立發票與提供收據。'

-- 代管型語氣
business_type_management = '我們會協助您與房東完成租金繳納流程，並提供必要的文件與提醒服務。'
```

### 完整範例：多版本 SOP

```sql
INSERT INTO vendor_sop_items (
    category_id, vendor_id, item_number, item_name,
    content,  -- 基礎版本
    requires_cashflow_check,
    cashflow_through_company,  -- 金流過我家版本
    cashflow_direct_to_landlord,  -- 金流不過我家版本
    requires_business_type_check,
    business_type_full_service,  -- 包租型語氣
    business_type_management,  -- 代管型語氣
    related_intent_id, priority
) VALUES (
    123, 1, 5, '租金帳務處理',
    '租金帳務由系統管理',
    TRUE,
    '公司將統一處理您的租金收款與發票開立，所有資訊可在 JGB 系統中查詢。',
    '房東將負責租金收款，JGB 系統僅提供繳款提醒與記錄查詢功能。',
    TRUE,
    '我們公司全權負責租金帳務管理，確保流程順暢。',
    '我們協助您與房東完成租金帳務，提供必要的支援服務。',
    6, 100
);
```

---

## 關聯意圖設定

### 為什麼需要關聯意圖？

SOP 項目可以關聯到意圖 (Intent)，以便：
1. **精準檢索**：當 AI 識別到某個意圖時，優先返回相關 SOP
2. **優先級排序**：關聯意圖的 SOP 會有更高的檢索權重
3. **語意增強**：幫助 RAG 系統更準確理解 SOP 適用場景

### 步驟 1: 查詢可用意圖

```sql
-- 查詢所有可用意圖
SELECT id, name, description
FROM intents
WHERE is_active = TRUE
ORDER BY name;
```

**常見意圖範例**：
```
ID  | 意圖名稱          | 說明
----|-----------------|---------------------------
1   | 退租流程         | 退租申請、押金退還等
5   | 租賃申請流程      | 租賃申請、資格審核等
6   | 帳務查詢         | 租金、水電費查詢等
7   | 維修報修         | 設備故障、維護請求等
15  | 寵物飼養         | 寵物相關規定與政策
```

### 步驟 2: 建立意圖（如果不存在）

```sql
-- 新增「寵物飼養」意圖
INSERT INTO intents (name, description, keywords, is_active)
VALUES (
    '寵物飼養',
    '寵物飼養許可、規範、費用相關問題',
    '["寵物", "養貓", "養狗", "寵物押金", "飼養規定", "可以養寵物嗎"]',
    TRUE
)
RETURNING id;
```

### 步驟 3: 關聯 SOP 到意圖

```sql
-- 將寵物相關 SOP 關聯到「寵物飼養」意圖 (ID = 15)
UPDATE vendor_sop_items
SET related_intent_id = 15
WHERE item_name LIKE '%寵物%';
```

### 步驟 4: 驗證關聯

```sql
-- 查詢某意圖下的所有 SOP
SELECT
    si.item_name,
    si.content,
    i.name AS intent_name
FROM vendor_sop_items si
LEFT JOIN intents i ON si.related_intent_id = i.id
WHERE si.related_intent_id = 15
ORDER BY si.priority DESC;
```

---

## 測試與驗證

### 1. 資料庫層面驗證

```sql
-- 驗證分類與項目數量
SELECT
    v.id AS vendor_id,
    v.name AS vendor_name,
    sc.id AS category_id,
    sc.category_name,
    COUNT(si.id) AS item_count
FROM vendors v
LEFT JOIN vendor_sop_categories sc ON v.id = sc.vendor_id
LEFT JOIN vendor_sop_items si ON sc.id = si.category_id
WHERE v.id = 1  -- 指定業者
GROUP BY v.id, v.name, sc.id, sc.category_name
ORDER BY sc.display_order;
```

```sql
-- 驗證金流敏感項目
SELECT
    item_name,
    requires_cashflow_check,
    CASE
        WHEN cashflow_through_company IS NOT NULL THEN '✓'
        ELSE '✗'
    END AS has_company_version,
    CASE
        WHEN cashflow_direct_to_landlord IS NOT NULL THEN '✓'
        ELSE '✗'
    END AS has_landlord_version
FROM vendor_sop_items
WHERE vendor_id = 1 AND requires_cashflow_check = TRUE;
```

### 2. API 層面驗證

```bash
# 測試讀取分類
curl -X GET "http://localhost:8100/api/v1/vendors/1/sop/categories"

# 測試讀取項目
curl -X GET "http://localhost:8100/api/v1/vendors/1/sop/items?category_id=123"
```

### 3. 功能測試：使用 Backtest

在測試案例中加入新的 SOP 問題：

**檔案**: `scripts/knowledge_extraction/backtest_cases.py` 或資料庫 `backtest_cases` 表

```python
# 新增測試案例
test_cases.append({
    'question': '我可以養寵物嗎？',
    'expected_intent': '寵物飼養',
    'expected_keywords': ['允許', '小型', '申請', '押金'],
    'vendor_id': 1,
    'difficulty': 'EASY'
})
```

執行回測：

```bash
BACKTEST_QUALITY_MODE=hybrid \
python3 scripts/knowledge_extraction/backtest_framework.py
```

### 4. 實際查詢測試

使用 RAG API 進行真實查詢：

```bash
curl -X POST "http://localhost:8100/api/query" \
-H "Content-Type: application/json" \
-d '{
    "user_message": "我可以養寵物嗎？",
    "vendor_id": 1,
    "session_id": "test-session-001"
}'
```

**預期結果**：
- 應返回「寵物飼養規定」分類下的 SOP
- 根據業者金流模式顯示正確版本
- 信心度應 >= 0.8

---

## 最佳實踐與注意事項

### 1. 內容撰寫原則

#### 清晰簡潔
- 每個 SOP 項目聚焦單一主題
- 使用條列式說明（1, 2, 3...）
- 避免過長的段落（建議 3-5 句）

#### 語氣一致
- **包租型**：「公司將...」「我們提供...」（主動、負責）
- **代管型**：「我們協助...」「建議您...」（協助、建議）

#### 參數化
- 數字參數（金額、天數）建議使用 `vendor_configs` 管理
- 避免硬編碼在 SOP 內容中
- 範例：`${deposit_amount}` 可替換為實際金額

### 2. 金流版本設計建議

| 項目類型 | 是否需要金流判斷 | 原因 |
|---------|----------------|------|
| 租金繳納方式 | ✓ YES | 收款對象不同 |
| 押金退還 | ✓ YES | 保管與退還流程不同 |
| 收據發票 | ✓ YES | 開立主體不同 |
| 繳費提醒 | ✓ YES | 通知方式與內容不同 |
| 物業規定 | ✗ NO | 與金流無關 |
| 緊急聯絡 | ✗ NO | 與金流無關 |
| 設備說明 | ✗ NO | 與金流無關 |

### 3. 優先級設定策略

```
priority 值建議：
- 100: 高優先級（核心流程、常見問題）
- 80-90: 中高優先級（重要但非核心）
- 50-70: 中等優先級（補充說明）
- 30-40: 低優先級（細節、特殊情況）
```

**範例**：
```sql
-- 寵物飼養許可（核心問題）
priority = 100

-- 寵物押金（重要但次要）
priority = 90

-- 寵物規範（補充說明）
priority = 70

-- 寵物違規處理（特殊情況）
priority = 50
```

### 4. 常見錯誤與解決

#### 錯誤 1: 外鍵約束失敗

```
ERROR: insert or update on table "vendor_sop_items" violates foreign key constraint
```

**原因**: `category_id` 或 `vendor_id` 或 `related_intent_id` 不存在

**解決**:
```sql
-- 檢查分類是否存在
SELECT id FROM vendor_sop_categories WHERE id = 123;

-- 檢查業者是否存在
SELECT id FROM vendors WHERE id = 1;

-- 檢查意圖是否存在
SELECT id FROM intents WHERE id = 15;
```

#### 錯誤 2: 金流版本缺失

```
WARNING: requires_cashflow_check = TRUE but cashflow_through_company is NULL
```

**解決**: 確保金流敏感項目填寫所有金流版本
```sql
UPDATE vendor_sop_items
SET
    cashflow_through_company = '金流過我家版本內容...',
    cashflow_direct_to_landlord = '金流不過我家版本內容...'
WHERE id = 456 AND requires_cashflow_check = TRUE;
```

#### 錯誤 3: 意圖關鍵字未更新

如果新增 SOP 後查詢效果不佳，可能需要更新意圖關鍵字：

```sql
-- 擴充「寵物飼養」意圖的關鍵字
UPDATE intents
SET keywords = '["寵物", "養貓", "養狗", "寵物押金", "飼養規定", "可以養寵物嗎", "能養動物嗎", "寵物費用"]'
WHERE id = 15;
```

### 5. 維護建議

#### 定期檢查
```sql
-- 檢查是否有未關聯意圖的 SOP（可能需要關聯）
SELECT item_name, content
FROM vendor_sop_items
WHERE related_intent_id IS NULL
AND is_active = TRUE;

-- 檢查金流敏感項目是否完整
SELECT item_name
FROM vendor_sop_items
WHERE requires_cashflow_check = TRUE
AND (cashflow_through_company IS NULL OR cashflow_direct_to_landlord IS NULL);
```

#### 版本控制
- 建議將 SOP Excel 納入版本控制 (Git)
- 記錄每次 SOP 變更的原因與時間
- 使用 `updated_at` 欄位追蹤修改時間

#### 回測驗證
- 每次新增或修改 SOP 後，執行回測驗證
- 確保通過率維持在 80% 以上
- 特別關注新增 SOP 相關問題的品質分數

---

## 快速參考：完整範例

### 新增「寵物飼養規定」SOP（完整流程）

```sql
-- ========================================
-- Step 1: 確認或建立意圖
-- ========================================
INSERT INTO intents (name, description, keywords, is_active)
VALUES (
    '寵物飼養',
    '寵物飼養許可、規範、費用相關問題',
    '["寵物", "養貓", "養狗", "寵物押金", "飼養規定", "可以養寵物嗎", "能養動物嗎"]',
    TRUE
)
ON CONFLICT (name) DO UPDATE
SET keywords = EXCLUDED.keywords
RETURNING id;  -- 假設返回 ID = 15

-- ========================================
-- Step 2: 建立 SOP 分類與項目
-- ========================================
DO $$
DECLARE
    cat_id INTEGER;
    intent_id_pet INTEGER := 15;
    vendor_id_test INTEGER := 1;
BEGIN
    -- 建立分類
    INSERT INTO vendor_sop_categories (vendor_id, category_name, description, display_order)
    VALUES (vendor_id_test, '寵物飼養規定', '寵物飼養許可、限制、費用與責任', 10)
    RETURNING id INTO cat_id;

    -- 項目 1: 寵物飼養許可（通用型）
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check, related_intent_id, priority
    ) VALUES (
        cat_id, vendor_id_test, 1, '是否允許飼養寵物',
        '本物業允許房客飼養寵物，但需遵守以下規定：
1) 事前提出書面申請並獲得同意
2) 僅限小型犬貓，體重不超過10公斤
3) 需繳交寵物押金NT$5,000元
4) 遵守社區寵物管理規範',
        FALSE, intent_id_pet, 100
    );

    -- 項目 2: 寵物押金繳納（金流敏感）
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check,
        cashflow_through_company,
        cashflow_direct_to_landlord,
        related_intent_id, priority
    ) VALUES (
        cat_id, vendor_id_test, 2, '寵物押金如何繳納',
        '寵物押金為NT$5,000元，可透過多種方式繳納',
        TRUE,
        '登入 JGB 系統查看公司收款帳號，寵物押金NT$5,000元可通過銀行轉帳、信用卡支付。系統會在收款後主動通知您。',
        '請向房東索取收款帳號，寵物押金NT$5,000元建議使用銀行轉帳並留存收據。JGB 系統僅提供繳款提醒。',
        intent_id_pet, 90
    );

    -- 項目 3: 寵物飼養規範（通用型）
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check, related_intent_id, priority
    ) VALUES (
        cat_id, vendor_id_test, 3, '寵物飼養規範',
        '為維護社區環境品質，房客需遵守以下規範：
1) 控制寵物噪音，避免影響鄰居安寧
2) 定期清潔居住環境，保持衛生
3) 不得讓寵物在公共區域排泄
4) 外出時須使用牽繩或寵物籠
5) 違規者將收到警告，嚴重或屢次違規可能導致終止租約',
        FALSE, intent_id_pet, 80
    );

    -- 項目 4: 寵物押金退還（金流敏感）
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check,
        cashflow_through_company,
        cashflow_direct_to_landlord,
        related_intent_id, priority
    ) VALUES (
        cat_id, vendor_id_test, 4, '寵物押金退還方式',
        '租約結束後，寵物押金將依據房屋狀況退還',
        TRUE,
        '寵物押金由公司專戶保管，租約結束後我們會進行房屋檢查，確認無寵物造成的損壞後將於7個工作天內退還至您指定帳戶。',
        '寵物押金由房東收取並保管，租約結束後請與房東確認房屋狀況與退還時間。JGB 可提供標準的退租檢核表供參考。',
        1, 70  -- 關聯到退租流程意圖
    );

    RAISE NOTICE '✅ 寵物飼養規定 SOP 建立完成（分類ID: %）', cat_id;
END $$;

-- ========================================
-- Step 3: 驗證結果
-- ========================================
SELECT
    sc.category_name,
    si.item_number,
    si.item_name,
    si.requires_cashflow_check,
    CASE
        WHEN si.cashflow_through_company IS NOT NULL THEN '✓'
        ELSE '✗'
    END AS has_company_version,
    i.name AS intent_name,
    si.priority
FROM vendor_sop_items si
INNER JOIN vendor_sop_categories sc ON si.category_id = sc.id
LEFT JOIN intents i ON si.related_intent_id = i.id
WHERE sc.category_name = '寵物飼養規定' AND si.vendor_id = 1
ORDER BY si.item_number;
```

---

## 總結

本指南提供了三種 SOP 新增方法：

1. **SQL 直接新增** - 適合快速新增少量 SOP，靈活度高
2. **Excel 批次匯入** - 適合初次建立或大量新增，可視化編輯
3. **API 新增** - 適合程式化整合（目前需擴充）

### 推薦工作流程

1. **規劃階段**：使用 Excel 整理 SOP 結構與內容
2. **匯入階段**：使用批次匯入腳本或 SQL 批次新增
3. **調整階段**：使用 SQL 或 API 進行微調
4. **驗證階段**：執行回測確保品質
5. **維護階段**：定期檢查與更新

### 下一步建議

1. ✅ 立即新增「寵物飼養規定」SOP（解決回測失敗案例）
2. ⚠️ 擴充 API 以支援 SOP 建立功能
3. 📊 建立 SOP 覆蓋率檢查機制
4. 🔄 定期執行回測驗證 SOP 品質

---

**文檔版本**: 1.0
**建立日期**: 2025-10-18
**維護者**: AI Chatbot Team
