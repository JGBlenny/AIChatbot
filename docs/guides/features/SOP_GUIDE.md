# 📋 SOP 系統完整指南

**最後更新**: 2025-10-23
**版本**: v2.0（整合版）
**適用對象**: 開發者、系統管理員、業者管理員

---

## 📚 目錄

1. [系統概述](#系統概述)
2. [架構設計](#架構設計)
3. [資料庫結構](#資料庫結構)
4. [使用指南](#使用指南)
   - [介面操作（CRUD）](#介面操作crud)
   - [SQL 直接操作](#sql-直接操作)
   - [Excel 批次匯入](#excel-批次匯入)
5. [意圖關聯](#意圖關聯)
6. [變數替換功能](#變數替換功能)
7. [最佳實踐](#最佳實踐)
8. [故障排除](#故障排除)

---

## 系統概述

### 什麼是 SOP 系統？

SOP（Standard Operating Procedure）系統是包租代管業者的**標準作業流程管理系統**，用於儲存和管理各種業務規範、流程說明、常見問題解答等結構化知識。

### 核心特性

✅ **多業者支援**: 每個業者有獨立的 SOP 配置
✅ **平台範本**: 平台級 SOP 範本，業者可複製編輯
✅ **意圖關聯**: SOP 項目可關聯特定意圖，智能檢索
✅ **變數替換**: 支援動態變數（如 `{{payment_day}}`）
✅ **業種適配**: 根據業種類型（包租/代管）顯示不同內容
✅ **完整 CRUD**: 前端介面支援新增、編輯、刪除

### 系統演進

| 版本 | Migration | 說明 |
|------|-----------|------|
| v1.0 | Migration 33 | 初版架構，支援金流模式調整 |
| v1.5 | Migration 35 | 添加平台範本系統 |
| v2.0 | Migration 36 | 簡化為複製-編輯模式 ⭐ 當前版本 |

---

## 架構設計

### 設計模式：複製-編輯模式（Copy-Edit Pattern）

```
平台級 SOP 範本
    ↓ 複製
業者級 SOP 項目
    ↓ 編輯
業者自定義內容
```

**優勢**:
- 業者完全自主編輯，無需擔心覆蓋
- 平台範本更新不影響已建立的業者 SOP
- 簡化架構，易於理解和維護

### 三層架構

#### 1. 平台層（Platform Layer）
- **platform_sop_categories**: 平台 SOP 分類
- **platform_sop_templates**: 平台 SOP 範本
- 由平台管理員維護

#### 2. 業者層（Vendor Layer）
- **vendor_sop_categories**: 業者 SOP 分類（複製自平台）
- **vendor_sop_items**: 業者 SOP 項目（可自由編輯）
- 由業者管理員維護

#### 3. 意圖層（Intent Layer）
- **intent_sop_mapping**: 意圖與 SOP 的關聯
- 用於智能檢索和答案生成

---

## 資料庫結構

### 核心資料表

#### platform_sop_categories（平台 SOP 分類）

```sql
CREATE TABLE platform_sop_categories (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(200) UNIQUE NOT NULL,
    description TEXT,
    display_order INTEGER DEFAULT 0,
    template_notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### platform_sop_templates（平台 SOP 範本）

```sql
CREATE TABLE platform_sop_templates (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES platform_sop_categories(id),
    business_type VARCHAR(50),          -- 'full_service', 'property_management', 'both'
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    display_order INTEGER DEFAULT 0,
    template_notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### vendor_sop_categories（業者 SOP 分類）

```sql
CREATE TABLE vendor_sop_categories (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER REFERENCES vendors(id),
    category_name VARCHAR(200) NOT NULL,
    description TEXT,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(vendor_id, category_name)
);
```

#### vendor_sop_items（業者 SOP 項目）

```sql
CREATE TABLE vendor_sop_items (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER REFERENCES vendors(id),
    category_id INTEGER REFERENCES vendor_sop_categories(id),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    display_order INTEGER DEFAULT 0,
    source VARCHAR(50) DEFAULT 'manual',  -- 'template', 'manual'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### intent_sop_mapping（意圖 SOP 關聯）

```sql
CREATE TABLE intent_sop_mapping (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER REFERENCES vendors(id),
    intent_id INTEGER REFERENCES intents(id),
    sop_item_id INTEGER REFERENCES vendor_sop_items(id),
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(intent_id, sop_item_id)
);
```

### 索引

```sql
-- 提升查詢效能
CREATE INDEX idx_vendor_sop_items_vendor ON vendor_sop_items(vendor_id);
CREATE INDEX idx_vendor_sop_items_category ON vendor_sop_items(category_id);
CREATE INDEX idx_intent_sop_mapping_intent ON intent_sop_mapping(intent_id);
CREATE INDEX idx_intent_sop_mapping_sop ON intent_sop_mapping(sop_item_id);
```

---

## 使用指南

### 介面操作（CRUD）

#### 訪問路徑

1. 訪問管理介面：`http://localhost:8080`
2. 左側選單「業者管理」
3. 選擇業者，點擊「配置」
4. 頂部標籤「📋 SOP 管理」

**完整路徑**: `http://localhost:8080/#/vendors/1/configs` → 「SOP 管理」標籤

#### 新增 SOP 分類

1. 點擊「➕ 新增分類」按鈕
2. 填寫表單：
   - **分類名稱**（必填）: 例如「寵物飼養規定」
   - **分類說明**: 例如「寵物飼養許可、限制、費用等」
   - **顯示順序**: 數字越小越靠前
3. 點擊「✅ 建立分類」

#### 新增 SOP 項目

1. 在分類卡片中，點擊「➕ 新增項目」按鈕
2. 填寫表單：
   - **項目標題**（必填）
   - **項目內容**（必填，支援 Markdown）
   - **顯示順序**
3. 點擊「✅ 建立項目」

**支援變數**:
- `{{payment_day}}` - 繳費日期
- `{{late_fee}}` - 滯納金
- `{{deposit_months}}` - 押金月數

#### 編輯 SOP 項目

1. 在項目卡片中，點擊「✏️ 編輯」按鈕
2. 修改內容
3. 點擊「💾 儲存」

#### 刪除 SOP 項目

1. 點擊「🗑️ 刪除」按鈕
2. 確認刪除（軟刪除，設定 `is_active = false`）

---

### SQL 直接操作

#### 新增 SOP 分類

```sql
INSERT INTO vendor_sop_categories (vendor_id, category_name, description, display_order)
VALUES (1, '繳費規定', '租金繳納、滯納金、繳費方式等', 1);
```

#### 新增 SOP 項目

```sql
INSERT INTO vendor_sop_items (vendor_id, category_id, title, content, display_order)
VALUES (
    1,                          -- vendor_id
    1,                          -- category_id
    '租金繳納時間',              -- title
    '每月{{payment_day}}號前繳納，逾期收取滯納金{{late_fee}}元。', -- content
    1                           -- display_order
);
```

#### 關聯意圖與 SOP

```sql
INSERT INTO intent_sop_mapping (vendor_id, intent_id, sop_item_id, priority)
VALUES (1, 5, 10, 1);  -- 將意圖 5 關聯到 SOP 項目 10
```

---

### Excel 批次匯入

#### 準備 Excel 檔案

**格式要求**:

| 分類名稱 | 項目標題 | 項目內容 | 顯示順序 |
|---------|---------|---------|---------|
| 繳費規定 | 租金繳納時間 | 每月{{payment_day}}號前繳納 | 1 |
| 繳費規定 | 滯納金規定 | 逾期收取{{late_fee}}元 | 2 |
| 報修流程 | 報修方式 | 撥打服務專線或使用APP報修 | 1 |

#### 匯入步驟

1. 準備 Excel 檔案（.xlsx）
2. 在 SOP 管理介面，點擊「📥 批次匯入」按鈕
3. 選擇檔案
4. 系統自動建立分類和項目
5. 檢查匯入結果

---

## 意圖關聯

### 為什麼需要意圖關聯？

當使用者提問時，系統會：
1. 識別問題的意圖（如「租金繳納」）
2. 根據意圖查詢關聯的 SOP 項目
3. 將 SOP 內容整合到回答中

### 設定意圖關聯

#### 方法 1: 透過介面

1. 在 SOP 項目卡片中，點擊「🔗 關聯意圖」
2. 選擇要關聯的意圖
3. 設定優先級（數字越小優先級越高）
4. 點擊「✅ 建立關聯」

#### 方法 2: 透過 SQL

```sql
-- 將「租金繳納時間」SOP 關聯到「租金查詢」意圖
INSERT INTO intent_sop_mapping (vendor_id, intent_id, sop_item_id, priority)
VALUES (1, 5, 10, 1);

-- 一個意圖可關聯多個 SOP 項目
INSERT INTO intent_sop_mapping (vendor_id, intent_id, sop_item_id, priority)
VALUES
    (1, 5, 10, 1),  -- 租金繳納時間（優先級 1）
    (1, 5, 11, 2),  -- 滯納金規定（優先級 2）
    (1, 5, 12, 3);  -- 繳費方式（優先級 3）
```

### 查詢意圖關聯的 SOP

```sql
SELECT
    i.name AS intent_name,
    vsi.title AS sop_title,
    vsi.content AS sop_content,
    ism.priority
FROM intent_sop_mapping ism
JOIN intents i ON ism.intent_id = i.id
JOIN vendor_sop_items vsi ON ism.sop_item_id = vsi.id
WHERE ism.vendor_id = 1
  AND i.id = 5  -- 租金查詢意圖
ORDER BY ism.priority ASC;
```

---

## 變數替換功能

### 支援的變數

| 變數名稱 | 說明 | 範例值 |
|---------|------|--------|
| `{{payment_day}}` | 繳費日期 | 每月 5 號 |
| `{{late_fee}}` | 滯納金 | 200 元 |
| `{{deposit_months}}` | 押金月數 | 2 個月 |
| `{{contract_duration}}` | 合約期限 | 1 年 |
| `{{notice_period}}` | 通知期限 | 30 天 |

### 設定變數值

變數值儲存在 `vendor_configs` 表中：

```sql
-- 設定繳費日期
INSERT INTO vendor_configs (vendor_id, category, param_key, param_value)
VALUES (1, 'payment', 'payment_day', '每月 5 號');

-- 設定滯納金
INSERT INTO vendor_configs (vendor_id, category, param_key, param_value)
VALUES (1, 'payment', 'late_fee', '200 元');
```

### 使用範例

**SOP 內容（含變數）**:
```
租金應於{{payment_day}}前繳納，逾期將收取滯納金{{late_fee}}。
押金為{{deposit_months}}租金，合約期限為{{contract_duration}}。
```

**替換後（顯示給使用者）**:
```
租金應於每月 5 號前繳納，逾期將收取滯納金 200 元。
押金為 2 個月租金，合約期限為 1 年。
```

---

## 最佳實踐

### 內容撰寫

✅ **DO**:
- 使用清晰簡潔的語言
- 結構化內容（使用列表、表格）
- 善用變數替換，避免硬編碼數值
- 提供具體範例

❌ **DON'T**:
- 避免過長的段落
- 避免使用專業術語（或提供解釋）
- 避免重複內容

### 分類組織

建議的分類結構：

```
繳費規定/
├── 租金繳納時間
├── 滯納金規定
└── 繳費方式

報修流程/
├── 報修方式
├── 報修受理時間
└── 緊急報修處理

退租流程/
├── 退租通知期限
├── 退租檢查項目
└── 押金退還時間

寵物飼養/
├── 寵物飼養許可
├── 寵物押金
└── 寵物違規處理
```

### 意圖關聯策略

1. **一對多關聯**: 一個意圖可關聯多個 SOP 項目
2. **優先級設定**: 重要資訊優先級設定較低數字
3. **定期檢查**: 定期檢查關聯是否仍然有效

### 維護建議

1. **定期更新**: 每季度檢查 SOP 內容是否需要更新
2. **版本控制**: 重大修改前備份舊版本
3. **測試驗證**: 修改後測試意圖檢索是否正確

---

## 故障排除

### 常見問題

#### Q1: SOP 內容沒有顯示變數替換結果

**原因**: 變數值未設定或變數名稱錯誤

**解決**:
```sql
-- 檢查變數值
SELECT * FROM vendor_configs WHERE vendor_id = 1 AND category = 'payment';

-- 如果沒有，新增變數值
INSERT INTO vendor_configs (vendor_id, category, param_key, param_value)
VALUES (1, 'payment', 'payment_day', '每月 5 號');
```

#### Q2: 意圖檢索不到關聯的 SOP

**原因**: 未建立意圖關聯或關聯被刪除

**解決**:
```sql
-- 檢查意圖關聯
SELECT * FROM intent_sop_mapping WHERE vendor_id = 1 AND intent_id = 5;

-- 如果沒有，新增關聯
INSERT INTO intent_sop_mapping (vendor_id, intent_id, sop_item_id, priority)
VALUES (1, 5, 10, 1);
```

#### Q3: 批次匯入失敗

**原因**: Excel 格式不正確或缺少必填欄位

**解決**:
1. 檢查 Excel 欄位名稱是否正確
2. 確認「分類名稱」和「項目標題」不為空
3. 確認檔案格式為 .xlsx

#### Q4: 無法刪除 SOP 分類

**原因**: 分類下還有 SOP 項目

**解決**:
```sql
-- 先軟刪除所有項目
UPDATE vendor_sop_items SET is_active = false
WHERE category_id = 1;

-- 再刪除分類
UPDATE vendor_sop_categories SET is_active = false
WHERE id = 1;
```

---

## 📚 延伸閱讀

- [SOP 快速參考](./SOP_QUICK_REFERENCE.md) - 常用操作速查表
- [Database Schema + ERD](./DATABASE_SCHEMA_ERD.md) - 完整資料庫架構
- [API Reference](./api/API_REFERENCE_PHASE1.md) - SOP 相關 API

---

## 📝 變更歷史

| 日期 | 版本 | 說明 |
|------|------|------|
| 2026-02-03 | v2.3 | 實現知識庫表單觸發模式，支援 manual/immediate/auto，統一知識庫與 SOP 觸發機制 ([詳細文檔](../features/KNOWLEDGE_FORM_TRIGGER_IMPLEMENTATION.md)) |
| 2026-02-03 | v2.2 | 前端 UI 優化:移除 trigger_mode='none',優化欄位順序,新增詳細提示 ([詳細文檔](../features/SOP_TRIGGER_MODE_UI_UPDATE_2026-02-03.md)) |
| 2026-02-03 | v2.1 | 移除 trigger_mode='none' 選項,簡化為排查型/行動型兩種模式 |
| 2025-10-23 | v2.0 | 整合 6 個 SOP 指南為單一完整文檔 |
| 2025-10-18 | v1.5 | 新增完整 CRUD 功能 |
| 2025-10-17 | v1.0 | 初版 SOP 系統上線 |

---

**文檔維護**: AIChatbot Development Team
**最後審查**: 2026-02-03
