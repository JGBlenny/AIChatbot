# Intents vs Category：功能重疊分析

## 🎯 用戶洞察

> **「intents 意圖不就是你指的 category 的作用？」**

**完全正確！** 這是關鍵觀察。

## 📊 兩者對比

### Intents（意圖）- 細粒度分類
```
✅ 用於檢索過濾（WHERE intent_id = ANY(...)）

ID | 名稱                | Type        | 知識數
---|---------------------|-------------|-------
1  | 退租流程            | knowledge   | 13
2  | 合約規定            | knowledge   | 103
3  | 設備使用            | knowledge   | 17
4  | 服務說明            | knowledge   | 1
5  | 租約查詢            | data_query  | 10
6  | 帳務查詢            | data_query  | 105
8  | 設備報修            | action      | 3
11 | 寵物飼養            | knowledge   | 1
14 | 帳號問題            | knowledge   | 27
16 | 設施使用            | knowledge   | 3
17 | 系統操作            | knowledge   | ?
```

### Category（分類）- 粗粒度分類
```
❌ 不用於檢索過濾

分類      | 知識數 | 對應的 Intents
---------|--------|--------------------------------------------------
合約問題  | 167   | 合約規定(103), 退租流程(13), 帳號問題(10), 租約查詢(10)...
帳務問題  | 153   | 帳務查詢(105), 合約規定(20), 帳號問題(6)...
服務問題  | 144   | 帳號問題(27), 設備報修(23), 設備使用(16)...
設備報修  | 4     | 設備報修(3), 帳務查詢(1)
```

## 🔍 關係分析

### 層級關係
```
Category (粗)
  └─ Intent (細)
      └─ Knowledge (知識)

例子:
合約問題 (category)
  ├─ 合約規定 (intent) → 103 筆知識
  ├─ 退租流程 (intent) → 13 筆知識
  └─ 租約查詢 (intent) → 10 筆知識
```

### 功能重疊

| 功能 | Category | Intent | 重疊程度 |
|------|----------|--------|---------|
| 分類知識 | ✅ 粗分類 | ✅ 細分類 | 🔴 100% 重疊 |
| 檢索過濾 | ❌ 不使用 | ✅ 使用 | N/A |
| 前端顯示 | ✅ 顯示 | ✅ 顯示 | 🔴 重疊 |
| 統計報表 | ✅ 可用 | ✅ 可用 | 🔴 重疊 |

## 💡 關鍵發現

### 1. Category 是冗餘的

```python
# 當前設計（冗餘）
知識 {
    category: "合約問題",      # ← 粗分類（不用於檢索）
    intent_id: 2,             # ← 細分類（用於檢索）
    intent_name: "合約規定"   # ← 已經說明是合約相關
}
```

**Intent 已經提供了比 Category 更好的分類！**

### 2. Category 的唯一價值

僅用於前端顯示的「大分類」：
- 知識管理頁面的粗略分組
- 統計報表的高層級概覽

但這可以通過 Intent 聚合實現：
```python
# 不需要 category，可以從 intents 聚合
"合約相關" = SUM(intents WHERE name IN ['合約規定', '退租流程', '租約查詢'])
"帳務相關" = SUM(intents WHERE name IN ['帳務查詢'])
```

### 3. Intents 已經可以做權限控制！

看看這個 Intent：
```
ID: 17
名稱: "系統操作"
Type: knowledge
```

**這本身就是「內部管理」的意圖！**

## 🎯 新方案：基於 Intent 的權限控制

### 方案 D：在 Intents 層面做權限隔離

```sql
-- 在 intents 表添加 access_level
ALTER TABLE intents ADD COLUMN access_level VARCHAR(20) DEFAULT 'customer';

-- 更新現有 intents
UPDATE intents
SET access_level = 'staff'
WHERE name IN ('系統操作', '後台管理', '業者設定');

UPDATE intents
SET access_level = 'customer'
WHERE name NOT IN ('系統操作', '後台管理', '業者設定');
```

### 檢索邏輯修改

```python
# vendor_knowledge_retriever.py

# 原本：根據 allowed_audiences 過濾
WHERE (
    kb.audience IS NULL
    OR kb.audience = ANY(['租客', '房東', ...])
)

# 改為：根據 intent.access_level 過濾
WHERE (
    i.access_level = 'customer'  -- B2C
    OR (i.access_level = 'staff' AND %s = 'staff')  -- B2B
)
```

## 📊 方案對比更新

### 當前方案（複雜）
```
audience (欄位) → allowed_audiences (映射) → SQL 過濾
成本: 8/10 | 效益: 3/10
```

### 方案 A：user_role + category
```
category (重新定義) → SQL 過濾
成本: 5/10 | 效益: 5/10
問題: category 語義混淆，與 intent 功能重疊
```

### 方案 C：布林值 is_internal
```
is_internal (新欄位) → SQL 過濾
成本: 4/10 | 效益: 7/10
優點: 簡單清晰
```

### 方案 D：Intent 層級權限（新推薦）⭐
```
intent.access_level → SQL 過濾（JOIN intents）
成本: 3/10 | 效益: 9/10
優點:
  ✅ 利用現有 intent 分類
  ✅ 不需要在 knowledge_base 添加欄位
  ✅ 集中管理（所有知識的權限取決於其 intent）
  ✅ 細粒度控制（可以針對不同 intent 設定不同權限）
  ✅ 語義清晰（"系統操作" intent 本來就該是內部專用）
```

## 🚀 方案 D 實施細節

### 步驟 1: 修改 intents 表

```sql
-- 添加 access_level 欄位
ALTER TABLE intents
ADD COLUMN access_level VARCHAR(20) DEFAULT 'customer',
ADD COLUMN access_description TEXT;

-- 設定現有 intents 的權限
UPDATE intents SET access_level = 'staff', access_description = '僅業者內部人員可見'
WHERE name IN ('系統操作');

UPDATE intents SET access_level = 'customer', access_description = '終端客戶可見'
WHERE name NOT IN ('系統操作');

-- 添加約束
ALTER TABLE intents
ADD CONSTRAINT check_access_level
CHECK (access_level IN ('customer', 'staff', 'both'));
```

### 步驟 2: 修改檢索邏輯

```python
# vendor_knowledge_retriever.py: retrieve_knowledge_hybrid()

sql_query = f"""
    SELECT
        kb.id,
        kb.question_summary,
        kb.answer,
        -- ... 其他欄位
    FROM knowledge_base kb
    LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
    LEFT JOIN intents i ON kim.intent_id = i.id  -- ✅ JOIN intents 表
    WHERE
        -- 其他過濾條件...

        -- ✅ Intent 權限過濾（取代 audience 過濾）
        AND (
            i.access_level = 'customer'  -- B2C 客戶可見
            OR i.access_level = 'both'   -- 所有人可見
            OR (i.access_level = 'staff' AND %s = 'staff')  -- B2B 員工可見
        )

    ORDER BY boosted_similarity DESC
    LIMIT %s
"""
```

### 步驟 3: 移除冗餘欄位

```sql
-- 移除 knowledge_base 的 audience 欄位
ALTER TABLE knowledge_base DROP COLUMN audience;

-- 考慮移除 category 欄位（可選）
-- 如果前端仍需要顯示大分類，可以從 intents 聚合
ALTER TABLE knowledge_base DROP COLUMN category;

-- 刪除配置表
DROP TABLE IF EXISTS audience_config;
```

### 步驟 4: 前端調整

```vue
<!-- KnowledgeView.vue -->
<!-- 移除 audience 選擇 -->
<!-- 移除 category 選擇（可選） -->

<!-- 只需選擇 intent -->
<div class="form-group">
  <label>意圖 *</label>
  <select v-model="formData.intent_id" required>
    <option v-for="intent in intents" :key="intent.id" :value="intent.id">
      {{ intent.name }}
      <span v-if="intent.access_level === 'staff'">🔒 內部</span>
    </option>
  </select>
  <p class="hint">{{ selectedIntent.access_description }}</p>
</div>
```

## 🎯 為什麼方案 D 最好？

### 1. 語義正確
```
Intent: "系統操作" → 本來就該是內部專用
Intent: "租金繳納" → 本來就該是客戶可見
```

### 2. 集中管理
```
不需要每個知識都設定權限
只需要在 intents 表設定一次
所有關聯該 intent 的知識自動繼承權限
```

### 3. 細粒度控制
```
可以設定：
- "系統操作" → staff only
- "租金繳納" → customer only
- "服務說明" → both（客戶和員工都能看）
```

### 4. 零冗餘
```
移除了：
✅ audience 欄位
✅ audience_config 表
✅ FALLBACK_AUDIENCE_MAPPING 硬編碼
✅ business_scope_utils.py
✅ category 欄位（可選）
```

### 5. 效能更好
```
原本: knowledge_base WHERE audience = ANY([...])
現在: knowledge_base JOIN intents WHERE access_level = 'customer'

JOIN 是必須的（本來就要用 intent 檢索）
不增加額外查詢成本
```

## 📋 決策矩陣

| 方案 | 成本 | 效益 | 語義 | 維護性 | 推薦度 |
|------|------|------|------|--------|--------|
| 當前（audience） | 8/10 | 3/10 | ⚠️ 混亂 | ❌ 差 | ⭐ |
| A (user_role+category) | 5/10 | 5/10 | ⚠️ 重疊 | ⚠️ 中 | ⭐⭐ |
| C (is_internal) | 4/10 | 7/10 | ✅ 清晰 | ✅ 好 | ⭐⭐⭐⭐ |
| **D (intent.access_level)** | **3/10** | **9/10** | **✅ 完美** | **✅ 優秀** | **⭐⭐⭐⭐⭐** |

## 🎯 最終建議

**實施方案 D：在 Intent 層級控制權限**

理由：
1. ✅ Intent 已經在做分類（比 category 更細）
2. ✅ 檢索本來就需要 JOIN intents 表（零額外成本）
3. ✅ 語義完美（"系統操作" 本來就該是內部專用）
4. ✅ 集中管理（不需要每個知識都設定）
5. ✅ 可以完全移除 audience 和 category（最大簡化）

### 遷移腳本

```sql
-- migration: 36-simplify-to-intent-access-level.sql

BEGIN;

-- 1. 添加 access_level 到 intents
ALTER TABLE intents ADD COLUMN IF NOT EXISTS access_level VARCHAR(20) DEFAULT 'customer';
ALTER TABLE intents ADD COLUMN IF NOT EXISTS access_description TEXT;

-- 2. 設定現有 intents 的權限
UPDATE intents SET access_level = 'staff' WHERE name IN ('系統操作', '後台管理');
UPDATE intents SET access_level = 'customer' WHERE access_level IS NULL OR access_level = 'customer';

-- 3. 移除冗餘欄位
ALTER TABLE knowledge_base DROP COLUMN IF EXISTS audience;
-- ALTER TABLE knowledge_base DROP COLUMN IF EXISTS category;  -- 可選

-- 4. 刪除配置表
DROP TABLE IF EXISTS audience_config;

-- 5. 添加約束
ALTER TABLE intents ADD CONSTRAINT check_access_level
CHECK (access_level IN ('customer', 'staff', 'both'));

COMMIT;
```

## 結論

你的觀察完全正確：
- ✅ Intent 已經在做 Category 的工作（而且做得更好）
- ✅ Category 是冗餘的
- ✅ 應該在 Intent 層級控制權限，而不是在每個知識上

**這是最優雅、最簡潔的解決方案。**
