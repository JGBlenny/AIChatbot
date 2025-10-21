# SOP 新增快速參考卡

> 快速上手指南 - 5分鐘掌握 SOP 新增操作

---

## 🚀 快速開始

### 最簡單的方式：使用現成腳本

```bash
# 1. 新增寵物飼養規定（解決回測缺口）
psql -h localhost -U aichatbot -d aichatbot_admin \
  -f scripts/add_pet_policy_sop.sql

# 2. 驗證結果
psql -h localhost -U aichatbot -d aichatbot_admin \
  -c "SELECT category_name, COUNT(*) FROM vendor_sop_items si
      JOIN vendor_sop_categories sc ON si.category_id = sc.id
      WHERE vendor_id = 1 GROUP BY category_name;"
```

---

## 📝 三種新增方法比較

| 方法 | 適用場景 | 時間 | 難度 |
|------|---------|------|------|
| **SQL 腳本** | 新增 1-5 個 SOP | 5-15 分鐘 | ⭐⭐ |
| **Excel 匯入** | 批次新增 >10 個 SOP | 30-60 分鐘 | ⭐⭐⭐ |
| **API 調用** | 程式化整合 | 依需求 | ⭐⭐⭐⭐ |

---

## 🎯 核心概念（必讀）

### 1. 資料結構

```
vendor (業者)
 └─ vendor_sop_categories (分類)
     └─ vendor_sop_items (項目)
         ├─ content (基礎內容)
         ├─ cashflow_through_company (金流過我家版本) ⬅️ 動態選擇
         └─ cashflow_direct_to_landlord (金流不過我家版本) ⬅️ 動態選擇
```

### 2. 金流模式判斷（關鍵邏輯）

**什麼時候需要設置 `requires_cashflow_check = TRUE`？**

- ✅ **需要**：租金繳納、押金、收據、發票、遲付處理
- ❌ **不需要**：物業規定、設備說明、緊急聯絡、一般流程

**範例**：

```sql
-- ✅ 正確：租金繳納（金流敏感）
requires_cashflow_check = TRUE
cashflow_through_company = '登入 JGB 系統繳納...'
cashflow_direct_to_landlord = '向房東繳納...'

-- ✅ 正確：物業規定（非金流敏感）
requires_cashflow_check = FALSE
content = '社區規定：禁止在陽台晾曬衣物...'
```

### 3. 意圖關聯（提升檢索精準度）

```sql
-- 步驟 1: 查詢可用意圖
SELECT id, name FROM intents WHERE is_active = TRUE;

-- 步驟 2: 新增 SOP 時關聯意圖
related_intent_id = 15  -- 例如：寵物飼養意圖
```

---

## ⚡ 最常用的 3 個操作

### 操作 1: 新增簡單 SOP（不需金流判斷）

```sql
-- 範例：新增「垃圾分類規定」
INSERT INTO vendor_sop_items (
    category_id,     -- 先用 SELECT id FROM vendor_sop_categories WHERE category_name = '物業規定'
    vendor_id,       -- 1 (業者ID)
    item_number,     -- 10 (項次)
    item_name,       -- '垃圾分類規定'
    content,         -- '本社區實施垃圾分類...'
    requires_cashflow_check,  -- FALSE
    related_intent_id,  -- NULL 或相關意圖ID
    priority         -- 80
) VALUES (
    456, 1, 10, '垃圾分類規定',
    '本社區實施垃圾分類，請將一般垃圾、資源回收、廚餘分開投放...',
    FALSE, NULL, 80
);
```

### 操作 2: 新增金流敏感 SOP

```sql
-- 範例：新增「停車費繳納方式」
INSERT INTO vendor_sop_items (
    category_id, vendor_id, item_number, item_name, content,
    requires_cashflow_check,
    cashflow_through_company,
    cashflow_direct_to_landlord,
    related_intent_id, priority
) VALUES (
    456, 1, 11, '停車費繳納方式',
    '停車費為每月NT$2,000元',
    TRUE,
    '登入 JGB 系統查看停車費帳單並繳納，可使用銀行轉帳或信用卡。',
    '請向房東確認停車費繳納方式，JGB 系統僅提供繳費提醒。',
    6, 85
);
```

### 操作 3: 批次新增完整分類

```sql
-- 使用範本：複製 scripts/sop_templates.sql 中的「範本 3」
-- 修改分類名稱、項目內容後執行
```

---

## 🔍 實用查詢（Debug 必備）

### 查詢 1: 我的 SOP 有哪些？

```sql
SELECT
    sc.category_name AS 分類,
    COUNT(si.id) AS 項目數
FROM vendor_sop_categories sc
LEFT JOIN vendor_sop_items si ON sc.id = si.category_id
WHERE sc.vendor_id = 1
GROUP BY sc.category_name
ORDER BY sc.display_order;
```

### 查詢 2: 檢查金流版本是否完整

```sql
SELECT
    item_name,
    CASE
        WHEN cashflow_through_company IS NULL THEN '❌ 缺少'
        ELSE '✅ 完整'
    END AS 金流過我家,
    CASE
        WHEN cashflow_direct_to_landlord IS NULL THEN '❌ 缺少'
        ELSE '✅ 完整'
    END AS 金流不過我家
FROM vendor_sop_items
WHERE vendor_id = 1
  AND requires_cashflow_check = TRUE;
```

### 查詢 3: 找出未關聯意圖的 SOP

```sql
SELECT item_name, LEFT(content, 80) AS 內容
FROM vendor_sop_items
WHERE vendor_id = 1
  AND related_intent_id IS NULL
  AND is_active = TRUE;
```

---

## ⚠️ 常見錯誤 & 快速解決

### 錯誤 1: 外鍵約束失敗

```
ERROR: insert or update violates foreign key constraint
```

**解決**：
```sql
-- 檢查分類是否存在
SELECT id FROM vendor_sop_categories WHERE id = 你的category_id;

-- 檢查意圖是否存在
SELECT id FROM intents WHERE id = 你的intent_id;
```

### 錯誤 2: 金流版本缺失警告

```
WARNING: requires_cashflow_check = TRUE but versions are NULL
```

**解決**：
```sql
UPDATE vendor_sop_items
SET
    cashflow_through_company = '金流過我家版本...',
    cashflow_direct_to_landlord = '金流不過我家版本...'
WHERE id = 你的item_id;
```

### 錯誤 3: 意圖不存在

**解決**：
```sql
-- 建立新意圖
INSERT INTO intents (name, description, keywords, is_active)
VALUES ('意圖名稱', '說明', '["關鍵字1", "關鍵字2"]', TRUE)
RETURNING id;
```

---

## 📚 延伸閱讀

- **完整指南**: `docs/SOP_ADDITION_GUIDE.md` (詳細說明、最佳實踐)
- **SQL 範本**: `scripts/sop_templates.sql` (8 種常用範本)
- **實際範例**: `scripts/add_pet_policy_sop.sql` (寵物規定完整示範)

---

## ✅ 新增後必做檢查清單

- [ ] 資料庫層面：執行驗證查詢，確認 SOP 已正確插入
- [ ] 金流版本：如果 `requires_cashflow_check = TRUE`，確認兩個版本都已填寫
- [ ] 意圖關聯：確認關聯了正確的意圖 ID
- [ ] 優先級設定：核心問題 priority >= 90，一般問題 60-80
- [ ] 回測驗證：執行 `python3 scripts/knowledge_extraction/backtest_framework.py`
- [ ] 實際測試：使用 RAG API 測試相關問題是否返回正確答案

---

## 🎓 學習路徑

1. **初學者** (5 分鐘)
   - 閱讀本文「快速開始」章節
   - 執行 `add_pet_policy_sop.sql` 腳本
   - 查詢驗證結果

2. **進階使用** (30 分鐘)
   - 閱讀 `SOP_ADDITION_GUIDE.md`
   - 使用 `sop_templates.sql` 範本
   - 新增自己的 SOP 分類

3. **專家級別** (1 小時+)
   - 深入理解金流模式設計
   - 開發 API 自動化腳本
   - 建立 Excel 批次匯入流程

---

**最後更新**: 2025-10-18
**維護**: AI Chatbot Team
