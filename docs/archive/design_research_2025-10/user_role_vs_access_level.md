# user_role vs access_level：功能重複分析

## 🎯 用戶洞察

> **「但是 user_role 不是就在做這件事」**

**完全正確！** 這是第二個關鍵觀察。

## 📊 功能對比

### user_role（請求參數）
```python
user_role = "customer"  # B2C 客戶
user_role = "staff"     # B2B 員工
```

### access_level（我提議的）
```python
access_level = "customer"  # 客戶可見
access_level = "staff"     # 員工可見
access_level = "both"      # 所有人可見
```

## 🔍 邏輯分析

### 我原本的檢索邏輯
```sql
WHERE (
    i.access_level = 'customer'
    OR i.access_level = 'both'
    OR (i.access_level = 'staff' AND user_role = 'staff')
)
```

### 問題在哪？

```
user_role = "customer" + access_level = "customer" → ✅ 允許
user_role = "customer" + access_level = "staff"    → ❌ 拒絕
user_role = "staff"    + access_level = "customer" → ✅ 允許
user_role = "staff"    + access_level = "staff"    → ✅ 允許
```

**發現了嗎？access_level 只是在重複 user_role 的判斷！**

## 💡 實際需求

### 真正的邏輯

```python
if user_role == "staff":
    # 員工可以看所有知識
    return all_knowledge

if user_role == "customer":
    # 客戶只能看「非內部專用」的知識
    return knowledge WHERE NOT internal_only
```

### 本質上只需要一個布林值

```sql
-- 不需要三個值（customer, staff, both）
access_level IN ('customer', 'staff', 'both')  ❌ 過度設計

-- 只需要一個布林值
is_staff_only BOOLEAN  ✅ 足夠
```

## 🎯 正確的設計

### 方案 D-修正版：使用布林值

```sql
-- intents 表
ALTER TABLE intents ADD COLUMN is_staff_only BOOLEAN DEFAULT FALSE;

-- 設定
UPDATE intents SET is_staff_only = TRUE WHERE name IN ('系統操作', '後台管理');
UPDATE intents SET is_staff_only = FALSE WHERE name NOT IN ('系統操作', '後台管理');
```

### 檢索邏輯

```python
# vendor_knowledge_retriever.py

if user_role == 'staff':
    # 員工看所有知識（不過濾）
    sql_filter = ""
elif user_role == 'customer':
    # 客戶只看非內部專用的
    sql_filter = "AND i.is_staff_only = FALSE"
```

完整 SQL：
```sql
SELECT kb.*
FROM knowledge_base kb
JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
JOIN intents i ON kim.intent_id = i.id
WHERE
    kb.vendor_id = %s
    AND (1 - (kb.embedding <=> %s::vector)) >= %s
    -- ✅ 只需這一個條件
    AND (
        %s = 'staff'  -- 員工看所有
        OR i.is_staff_only = FALSE  -- 客戶只看非內部的
    )
```

## 📋 三個值的真相

### "both" 和 "customer" 其實一樣

```python
access_level = "customer"  # 客戶可以看
access_level = "both"      # 客戶也可以看
# 對於檢索邏輯，這兩個沒有區別！

# 真正的區別只有：
is_staff_only = FALSE  # 客戶可以看（相當於 "customer" 或 "both"）
is_staff_only = TRUE   # 只有員工可以看（相當於 "staff"）
```

### 為什麼 "both" 是多餘的？

```python
# 錯誤的思考
access_level = "customer"  # 只給客戶？
access_level = "staff"     # 只給員工？
access_level = "both"      # 兩者都給？

# 正確的思考
is_staff_only = FALSE  # 不是「員工專用」→ 客戶也能看
is_staff_only = TRUE   # 是「員工專用」→ 只有員工能看

# 員工本來就能看所有知識！
# 所以不存在「只給客戶不給員工」的情況
# 因此不需要三個值
```

## 🔄 方案對比更新

### 方案 C：knowledge_base 層級的布林值
```sql
ALTER TABLE knowledge_base ADD COLUMN is_internal BOOLEAN;

-- 每個知識都要設定（479 次）
UPDATE knowledge_base SET is_internal = TRUE WHERE ...;
```

### 方案 D-修正：intents 層級的布林值 ⭐
```sql
ALTER TABLE intents ADD COLUMN is_staff_only BOOLEAN;

-- 只需設定 15 個 intents（15 次）
UPDATE intents SET is_staff_only = TRUE WHERE name IN ('系統操作');
```

## 💡 為什麼 Intent 層級更好？

### 1. 設定次數
```
方案 C: 479 個知識 × 設定 is_internal = 479 次
方案 D: 15 個 intents × 設定 is_staff_only = 15 次

減少工作量 96%
```

### 2. 語義清晰
```
Intent: "系統操作"
is_staff_only: TRUE

→ 完美！「系統操作」本來就該只給員工
```

### 3. 自動繼承
```
設定: intents(id=17).is_staff_only = TRUE

自動套用到:
  - 知識 1（如何新增房東）
  - 知識 2（後台操作手冊）
  - 知識 3（業者設定說明）
  ...

不需要每個知識都設定
```

### 4. 集中管理
```
要改變「系統操作」的權限？
- 方案 C: 需要更新所有相關知識（可能漏掉）
- 方案 D: 只需更新 1 個 intent（不會漏）
```

## 🎯 最終方案對比

| 方案 | 欄位位置 | 欄位類型 | 設定次數 | 推薦度 |
|------|---------|---------|---------|--------|
| 當前 | knowledge_base.audience | VARCHAR | 479 次 | ⭐ |
| C | knowledge_base.is_internal | BOOLEAN | 479 次 | ⭐⭐⭐ |
| D-錯誤 | intents.access_level | VARCHAR(customer/staff/both) | 15 次 | ⭐⭐⭐ (過度設計) |
| **D-修正** | **intents.is_staff_only** | **BOOLEAN** | **15 次** | **⭐⭐⭐⭐⭐** |

## 📝 實施方案（最終版）

### 步驟 1: 修改 intents 表

```sql
-- migration: 36-add-intent-staff-only.sql

BEGIN;

-- 添加布林值欄位
ALTER TABLE intents ADD COLUMN is_staff_only BOOLEAN DEFAULT FALSE;
COMMENT ON COLUMN intents.is_staff_only IS '是否僅限員工可見（TRUE=內部專用，FALSE=客戶可見）';

-- 設定現有 intents
UPDATE intents SET is_staff_only = TRUE
WHERE name IN ('系統操作', '後台管理', '業者設定');

UPDATE intents SET is_staff_only = FALSE
WHERE is_staff_only IS NULL;

-- 設為非空
ALTER TABLE intents ALTER COLUMN is_staff_only SET NOT NULL;

COMMIT;
```

### 步驟 2: 修改檢索邏輯

```python
# vendor_knowledge_retriever.py

sql_query = f"""
    SELECT
        kb.id,
        kb.question_summary,
        kb.answer,
        -- ... 其他欄位
    FROM knowledge_base kb
    LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
    LEFT JOIN intents i ON kim.intent_id = i.id
    WHERE
        -- 其他過濾條件...

        -- ✅ 權限過濾（簡單布林值）
        AND (
            %s = 'staff'              -- 員工看所有
            OR i.is_staff_only = FALSE  -- 客戶只看非內部的
        )

    ORDER BY boosted_similarity DESC
    LIMIT %s
"""

cursor.execute(sql_query, (
    # ... 其他參數
    user_role,  # ✅ 只需要傳入 user_role
    top_k
))
```

### 步驟 3: 移除冗餘欄位

```sql
-- 移除 knowledge_base 的 audience 欄位
ALTER TABLE knowledge_base DROP COLUMN IF EXISTS audience;

-- 刪除配置表
DROP TABLE IF EXISTS audience_config;

-- category 保留（用於業務分類，不影響權限）
-- ALTER TABLE knowledge_base DROP COLUMN category;  -- 可選
```

### 步驟 4: 前端調整

```vue
<!-- KnowledgeView.vue -->

<!-- 移除 audience 選擇 -->
<!-- <select v-model="formData.audience">...</select> -->

<!-- Intent 選擇時顯示權限提示 -->
<div class="form-group">
  <label>意圖 *</label>
  <select v-model="formData.intent_id" required>
    <option v-for="intent in intents" :key="intent.id" :value="intent.id">
      {{ intent.name }}
      <span v-if="intent.is_staff_only" class="badge">🔒 員工專用</span>
    </option>
  </select>
  <p class="hint" v-if="selectedIntent && selectedIntent.is_staff_only">
    ⚠️ 此意圖標記為「員工專用」，客戶無法看到相關知識
  </p>
</div>
```

## 🎯 總結

### 用戶的兩個關鍵洞察

1. **Intent 已經在做 Category 的工作** ✅
   - Category 是冗餘的
   - Intent 提供更細的分類

2. **user_role 已經在做權限判斷** ✅
   - 不需要 access_level 三個值
   - 只需要標記「哪些 Intent 是員工專用」

### 最終方案

**在 Intent 層級添加布林值 `is_staff_only`**

```
intents 表:
  - is_staff_only = TRUE  → 只有 staff 可見
  - is_staff_only = FALSE → customer 和 staff 都可見

檢索邏輯:
  if user_role == "staff":
      不過濾（看所有）
  elif user_role == "customer":
      只看 is_staff_only = FALSE 的
```

**這才是最簡單、最正確的設計！**

### 優勢

1. ✅ 只需要布林值（不是三個值）
2. ✅ 利用現有 user_role（不重複判斷）
3. ✅ 在 Intent 層級管理（15 次設定 vs 479 次）
4. ✅ 權限自動繼承（不需要每個知識都設定）
5. ✅ 語義完美（"系統操作" 就該是 is_staff_only = TRUE）

### 完全移除

- ❌ audience 欄位
- ❌ audience_config 表
- ❌ FALLBACK_AUDIENCE_MAPPING 硬編碼
- ❌ business_scope_utils.py
- ❌ access_level 三個值的過度設計

### 保留

- ✅ user_role 參數（已經存在）
- ✅ intents 表（已經存在）
- ✅ category 欄位（可選，用於業務分類顯示）
