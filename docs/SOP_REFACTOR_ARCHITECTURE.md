# SOP 架構重構設計文檔

> **重構日期**: 2025-10-18
> **設計模式**: Platform Template + Vendor Override
> **目標**: 範本化 SOP 管理，減少重複，支援業者客製化

---

## 📐 新架構設計

### 核心概念

```
Platform Level (平台層)
    ↓ 定義範本
平台管理員建立 SOP 範本（一次性定義）
    ↓
Vendor Level (業者層)
    ↓ 選擇 + 覆寫
業者選擇範本並客製化（只定義差異）
    ↓
Runtime (運行時)
    ↓ 動態合併
系統合併範本 + 覆寫 = 最終 SOP
```

---

## 🗄️ 資料庫架構

### 1. Platform SOP Categories（平台 SOP 分類）

```sql
CREATE TABLE platform_sop_categories (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'admin'
);

COMMENT ON TABLE platform_sop_categories IS '平台 SOP 分類範本（由平台管理員維護）';
```

**範例資料**:
```sql
INSERT INTO platform_sop_categories (category_name, description, display_order) VALUES
('租賃流程相關', '租賃申請流程、資格審核、合約簽訂等', 1),
('租金繳費相關', '租金繳納方式、收據發票、遲繳處理等', 2),
('維修報修相關', '報修流程、緊急聯絡、設備保養等', 3),
('合約條款相關', '提前退租、續約流程、違約處理等', 4),
('寵物飼養規定', '寵物飼養許可、限制、費用、押金、責任等', 5);
```

---

### 2. Platform SOP Templates（平台 SOP 範本）

```sql
CREATE TABLE platform_sop_templates (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES platform_sop_categories(id) ON DELETE CASCADE,

    -- 項目基本資訊
    item_number INTEGER NOT NULL,
    item_name VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,  -- 基礎範本內容

    -- 金流模式相關
    requires_cashflow_check BOOLEAN DEFAULT FALSE,
    cashflow_through_company TEXT,  -- 範本：金流過我家
    cashflow_direct_to_landlord TEXT,  -- 範本：金流不過我家
    cashflow_mixed TEXT,  -- 範本：混合型

    -- 業種類型相關
    requires_business_type_check BOOLEAN DEFAULT FALSE,
    business_type_full_service TEXT,  -- 範本：包租型
    business_type_management TEXT,  -- 範本：代管型

    -- 關聯與優先級
    related_intent_id INTEGER REFERENCES intents(id) ON DELETE SET NULL,
    priority INTEGER DEFAULT 50,

    -- 範本說明（給業者看的）
    template_notes TEXT,  -- 例如：「此項目建議根據業者實際政策調整金額」
    customization_hint TEXT,  -- 例如：「常見客製化：押金金額、允許寵物種類」

    -- 狀態與時間
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'admin'
);

CREATE INDEX idx_platform_sop_category ON platform_sop_templates(category_id);
CREATE INDEX idx_platform_sop_intent ON platform_sop_templates(related_intent_id);

COMMENT ON TABLE platform_sop_templates IS '平台 SOP 範本（由平台管理員維護，業者可選擇性覆寫）';
```

---

### 3. Vendor SOP Overrides（業者 SOP 覆寫）

```sql
CREATE TABLE vendor_sop_overrides (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE,
    template_id INTEGER REFERENCES platform_sop_templates(id) ON DELETE CASCADE,

    -- 覆寫模式
    override_type VARCHAR(20) NOT NULL DEFAULT 'use_template',
    -- 可選值：
    -- 'use_template': 完全使用範本（預設，此時不需要 override 記錄）
    -- 'partial_override': 部分覆寫（只改某些欄位）
    -- 'full_override': 完全覆寫（整個項目替換）
    -- 'disabled': 停用（此項目不適用本業者）

    -- 覆寫內容（NULL = 使用範本）
    item_name VARCHAR(200),
    content TEXT,
    cashflow_through_company TEXT,
    cashflow_direct_to_landlord TEXT,
    cashflow_mixed TEXT,
    business_type_full_service TEXT,
    business_type_management TEXT,
    related_intent_id INTEGER REFERENCES intents(id) ON DELETE SET NULL,
    priority INTEGER,

    -- 覆寫原因（記錄為什麼要客製化）
    override_reason TEXT,

    -- 狀態與時間
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'admin',

    UNIQUE(vendor_id, template_id)
);

CREATE INDEX idx_vendor_override_vendor ON vendor_sop_overrides(vendor_id);
CREATE INDEX idx_vendor_override_template ON vendor_sop_overrides(template_id);
CREATE INDEX idx_vendor_override_type ON vendor_sop_overrides(override_type);

COMMENT ON TABLE vendor_sop_overrides IS '業者 SOP 客製化覆寫（只記錄與範本的差異）';
```

---

### 4. 查詢檢視（方便查詢）

```sql
CREATE OR REPLACE VIEW v_vendor_sop_merged AS
SELECT
    v.id AS vendor_id,
    v.name AS vendor_name,
    v.business_type,
    v.cashflow_model,

    pc.id AS category_id,
    pc.category_name,
    pc.description AS category_description,

    pt.id AS template_id,
    pt.item_number,

    -- 動態選擇：override 優先，否則 template
    COALESCE(vo.item_name, pt.item_name) AS item_name,
    COALESCE(vo.content, pt.content) AS content,
    COALESCE(vo.cashflow_through_company, pt.cashflow_through_company) AS cashflow_through_company,
    COALESCE(vo.cashflow_direct_to_landlord, pt.cashflow_direct_to_landlord) AS cashflow_direct_to_landlord,
    COALESCE(vo.related_intent_id, pt.related_intent_id) AS related_intent_id,
    COALESCE(vo.priority, pt.priority) AS priority,

    pt.requires_cashflow_check,
    pt.template_notes,
    pt.customization_hint,

    vo.override_type,
    vo.override_reason,

    CASE
        WHEN vo.override_type IS NULL THEN 'template'
        ELSE vo.override_type
    END AS source

FROM vendors v
CROSS JOIN platform_sop_templates pt
LEFT JOIN platform_sop_categories pc ON pt.category_id = pc.id
LEFT JOIN vendor_sop_overrides vo ON v.id = vo.vendor_id AND pt.id = vo.template_id
WHERE pt.is_active = TRUE
  AND pc.is_active = TRUE
  AND (vo.override_type IS NULL OR vo.override_type != 'disabled')
ORDER BY v.id, pc.display_order, pt.item_number;

COMMENT ON VIEW v_vendor_sop_merged IS '業者 SOP 合併檢視（範本 + 覆寫動態合併）';
```

---

## 🔄 覆寫模式詳解

### 1. `use_template` - 使用範本（預設）

**行為**: 完全使用平台範本，不做任何修改

**資料庫**: 不需要建立 override 記錄（節省空間）

**前端顯示**:
```
┌────────────────────────────────────┐
│ 🔄 租金繳納方式                     │
│ 來源: 📋 使用範本                   │
│ [👁️ 預覽範本] [✏️ 客製化]          │
└────────────────────────────────────┘
```

---

### 2. `partial_override` - 部分覆寫

**行為**: 只修改某些欄位，其他欄位使用範本

**範例**:
```sql
-- 範本定義
template.item_name = '寵物押金繳納方式'
template.content = '寵物押金為 NT$5,000'
template.cashflow_through_company = '登入系統繳納...'

-- 業者只覆寫金額
override.content = '寵物押金為 NT$10,000'  -- 只改這個
override.cashflow_through_company = NULL  -- 其他使用範本

-- 最終結果
final.item_name = '寵物押金繳納方式'  -- 來自範本
final.content = '寵物押金為 NT$10,000'  -- 來自覆寫
final.cashflow_through_company = '登入系統繳納...'  -- 來自範本
```

**前端顯示**:
```
┌────────────────────────────────────┐
│ 🔄 寵物押金繳納方式                 │
│ 來源: ✏️ 部分客製化                 │
│ 已覆寫: 內容                        │
│ 使用範本: 項目名稱、金流版本        │
│ [編輯客製內容] [🔄 還原為範本]      │
└────────────────────────────────────┘
```

---

### 3. `full_override` - 完全覆寫

**行為**: 整個項目完全由業者自訂，不使用範本任何內容

**範例**:
```sql
-- 範本定義
template.item_name = '寵物押金繳納方式'
template.content = '...'

-- 業者完全覆寫
override.override_type = 'full_override'
override.item_name = '特殊寵物保證金說明'  -- 全新名稱
override.content = '本公司特殊政策...'  -- 全新內容

-- 最終結果：完全使用 override
```

**前端顯示**:
```
┌────────────────────────────────────┐
│ 🔄 特殊寵物保證金說明               │
│ 來源: 📝 完全客製化                 │
│ 備註: 此項目完全由業者自訂          │
│ [編輯客製內容] [👁️ 查看範本]       │
└────────────────────────────────────┘
```

---

### 4. `disabled` - 停用

**行為**: 此 SOP 項目不適用本業者，不顯示

**範例**:
```sql
-- 業者不允許寵物，停用所有寵物相關 SOP
override.override_type = 'disabled'
override.override_reason = '本物業完全不允許飼養寵物'
```

**前端顯示**:
```
┌────────────────────────────────────┐
│ 🚫 寵物押金繳納方式（已停用）       │
│ 原因: 本物業完全不允許飼養寵物      │
│ [啟用此項目]                        │
└────────────────────────────────────┘
```

---

## 🔍 查詢邏輯

### Python 查詢範例

```python
def get_vendor_sop(vendor_id: int):
    """獲取業者的 SOP（範本 + 覆寫動態合併）"""

    query = """
        SELECT
            pt.id AS template_id,
            pc.category_name,
            pt.item_number,

            -- 使用 COALESCE 動態選擇
            COALESCE(vo.item_name, pt.item_name) AS item_name,
            COALESCE(vo.content, pt.content) AS content,
            COALESCE(vo.cashflow_through_company, pt.cashflow_through_company) AS cashflow_through_company,
            COALESCE(vo.cashflow_direct_to_landlord, pt.cashflow_direct_to_landlord) AS cashflow_direct_to_landlord,

            pt.requires_cashflow_check,
            pt.template_notes,

            COALESCE(vo.override_type, 'use_template') AS override_type,
            vo.override_reason

        FROM platform_sop_templates pt
        INNER JOIN platform_sop_categories pc ON pt.category_id = pc.id
        LEFT JOIN vendor_sop_overrides vo
            ON vo.vendor_id = %s AND vo.template_id = pt.id
        WHERE pt.is_active = TRUE
          AND pc.is_active = TRUE
          AND (vo.override_type IS NULL OR vo.override_type != 'disabled')
        ORDER BY pc.display_order, pt.item_number
    """

    return execute_query(query, [vendor_id])
```

---

## 🎨 前端介面設計

### 1. Platform Admin - SOP 範本管理

**路由**: `/platform/sop-templates`

**功能**:
- ✅ 建立 SOP 範本分類
- ✅ 建立 SOP 範本項目
- ✅ 編輯範本
- ✅ 刪除範本
- ✅ 查看哪些業者覆寫了此範本
- ✅ 範本使用統計

**介面預覽**:
```
┌─────────────────────────────────────────┐
│ 📋 Platform SOP 範本管理                │
│                                         │
│ [➕ 新增分類] [➕ 新增範本]             │
│                                         │
│ 📁 租賃流程相關 (5 個範本)              │
│   #1 如何申請租賃                       │
│      使用業者: 8/10                     │
│      覆寫業者: 2/10                     │
│      [✏️ 編輯] [📊 使用統計]            │
│                                         │
│   #2 資格審核標準                       │
│      使用業者: 10/10                    │
│      覆寫業者: 0/10                     │
│      [✏️ 編輯] [📊 使用統計]            │
└─────────────────────────────────────────┘
```

---

### 2. Vendor Config - SOP 客製化

**路由**: `/vendors/{id}/configs` → SOP 管理標籤

**功能**:
- ✅ 查看所有範本 SOP
- ✅ 選擇性覆寫
- ✅ 部分覆寫特定欄位
- ✅ 完全自訂項目
- ✅ 停用不適用項目
- ✅ 還原為範本

**介面預覽**:
```
┌─────────────────────────────────────────┐
│ 📋 SOP 管理 - 甲山林包租代管            │
│                                         │
│ 📁 寵物飼養規定                         │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ #1 是否允許飼養寵物                 │ │
│ │ 📋 使用範本                         │ │
│ │ [👁️ 預覽範本] [✏️ 客製化]          │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ #2 寵物押金繳納方式                 │ │
│ │ ✏️ 部分客製化                       │ │
│ │ 已覆寫: 內容（押金金額改為1萬）     │ │
│ │ 使用範本: 金流版本                  │ │
│ │ [編輯] [🔄 還原]                    │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ #3 寵物飼養規範                     │ │
│ │ 🚫 已停用                           │ │
│ │ 原因: 本物業不允許寵物              │ │
│ │ [啟用]                              │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

---

## 📊 遷移策略

### 階段 1: 建立新結構（不影響現有）

1. ✅ 建立新的 Platform SOP 表
2. ✅ 保留舊的 Vendor SOP 表
3. ✅ 兩套系統並存

### 階段 2: 資料遷移

1. ✅ 分析現有 SOP，抽取共同部分作為範本
2. ✅ 將差異部分轉為 override
3. ✅ 提供遷移工具

### 階段 3: 逐步切換

1. ✅ 新業者使用新架構
2. ✅ 舊業者可選擇性遷移
3. ✅ 提供一鍵遷移按鈕

---

## ✅ 優勢總結

| 項目 | 舊架構 | 新架構 |
|------|--------|--------|
| **範本定義** | 每個業者重複定義 | 平台定義一次 |
| **維護成本** | 修改要改 N 次 | 修改一次，全部生效 |
| **客製化** | 全部重建 | 只定義差異 |
| **資料量** | 大量重複資料 | 最小化儲存 |
| **一致性** | 難以保證 | 範本確保一致 |

---

**下一步**: 建立 database migration script

**檔案**: `database/migrations/40-create-platform-sop-tables.sql`
