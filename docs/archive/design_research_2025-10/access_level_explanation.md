# access_level 欄位作用說明

## 🎯 核心作用

**`access_level` 決定哪些用戶角色可以看到屬於該 Intent 的知識**

## 📊 具體例子

### 當前系統的 Intents

```sql
-- 查看現有 intents
SELECT id, name, type FROM intents;

ID | 名稱                | Type
---|---------------------|----------
1  | 退租流程            | knowledge
2  | 合約規定            | knowledge
6  | 帳務查詢            | data_query
8  | 設備報修            | action
17 | 系統操作            | knowledge    ← 這應該只給員工看！
```

### 添加 access_level 後

```sql
-- 方案 D: 添加 access_level 欄位
ALTER TABLE intents ADD COLUMN access_level VARCHAR(20);

-- 設定權限
UPDATE intents SET access_level = 'customer' WHERE id IN (1, 2, 6, 8);
UPDATE intents SET access_level = 'staff' WHERE id = 17;

-- 結果：
ID | 名稱       | access_level | 說明
---|-----------|--------------|---------------------
1  | 退租流程   | customer     | 租客可以看到
2  | 合約規定   | customer     | 租客可以看到
6  | 帳務查詢   | customer     | 租客可以看到
8  | 設備報修   | customer     | 租客可以看到
17 | 系統操作   | staff        | 只有員工可以看到
```

## 🔄 實際運作流程

### 場景 1: 租客查詢「如何退租？」

```python
# 1. 用戶請求
user_role = "customer"
question = "如何退租？"

# 2. AI 分類意圖
intent_id = 1  # 退租流程

# 3. 檢索知識（使用 access_level 過濾）
SELECT kb.*
FROM knowledge_base kb
JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
JOIN intents i ON kim.intent_id = i.id
WHERE
    i.id = 1  -- 退租流程
    AND (
        i.access_level = 'customer'  -- ✅ 通過！
        OR i.access_level = 'both'
    )

# 結果：✅ 找到 13 筆「退租流程」知識
```

### 場景 2: 租客查詢「如何操作後台？」

```python
# 1. 用戶請求
user_role = "customer"
question = "如何操作後台？"

# 2. AI 分類意圖
intent_id = 17  # 系統操作

# 3. 檢索知識（使用 access_level 過濾）
SELECT kb.*
FROM knowledge_base kb
JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
JOIN intents i ON kim.intent_id = i.id
WHERE
    i.id = 17  -- 系統操作
    AND (
        i.access_level = 'customer'  -- ❌ 不符合（是 'staff'）
        OR i.access_level = 'both'
    )

# 結果：❌ 找不到任何知識
# AI 回應：「抱歉，我無法回答此問題」
```

### 場景 3: 管理師查詢「如何操作後台？」

```python
# 1. 用戶請求
user_role = "staff"
question = "如何操作後台？"

# 2. AI 分類意圖
intent_id = 17  # 系統操作

# 3. 檢索知識（使用 access_level 過濾）
SELECT kb.*
FROM knowledge_base kb
JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
JOIN intents i ON kim.intent_id = i.id
WHERE
    i.id = 17  -- 系統操作
    AND (
        i.access_level = 'customer'
        OR i.access_level = 'both'
        OR (i.access_level = 'staff' AND 'staff' = 'staff')  -- ✅ 通過！
    )

# 結果：✅ 找到「系統操作」相關知識
```

## 📋 三種 access_level 值

| 值 | 意義 | 適用 Intent 範例 |
|---|------|-----------------|
| **customer** | 只有 B2C 客戶可見 | 退租流程、租金繳納、設備報修 |
| **staff** | 只有 B2B 員工可見 | 系統操作、後台管理、業者設定 |
| **both** | 所有人都可見 | 服務說明、FAQ |

## 🔄 取代當前的 audience 欄位

### 當前（複雜）

每個知識都要設定 audience：

```sql
-- knowledge_base 表
id | question_summary        | audience  | intent_id
---|------------------------|-----------|----------
1  | 如何退租？              | 租客      | 1
2  | 退租流程說明            | 租客      | 1
3  | 退租注意事項            | 租客      | 1
4  | 如何新增房東？          | 管理師    | 17
5  | 後台操作手冊            | 管理師    | 17
```

檢索邏輯：
```python
WHERE kb.audience = ANY(['租客', '房東', ...])  # 需要維護映射表
```

### 方案 D（簡化）

只需在 Intent 設定一次：

```sql
-- intents 表
id | name       | access_level
---|-----------|-------------
1  | 退租流程   | customer     ← 所有 intent_id=1 的知識自動繼承
17 | 系統操作   | staff        ← 所有 intent_id=17 的知識自動繼承

-- knowledge_base 表（不需要 audience 欄位）
id | question_summary        | intent_id
---|------------------------|----------
1  | 如何退租？              | 1          ← 自動繼承 customer
2  | 退租流程說明            | 1          ← 自動繼承 customer
3  | 退租注意事項            | 1          ← 自動繼承 customer
4  | 如何新增房東？          | 17         ← 自動繼承 staff
5  | 後台操作手冊            | 17         ← 自動繼承 staff
```

檢索邏輯：
```python
JOIN intents i ON kim.intent_id = i.id
WHERE i.access_level = 'customer'  # 簡單直接
```

## 💡 核心優勢

### 1. 權限繼承
```
設定 1 次（Intent 層級）→ 影響多個知識

intents.access_level = 'staff'
  ↓ 自動繼承
知識 1（系統操作）
知識 2（後台管理）
知識 3（業者設定）
...
```

### 2. 集中管理
```
當前: 479 筆知識 × 每筆設定 audience = 479 次設定
方案D: 15 個 intents × 每個設定 access_level = 15 次設定

工作量減少 96%！
```

### 3. 語義清晰
```
Intent: "系統操作"
access_level: "staff"

→ 完美的語義！「系統操作」本來就該只給員工看
```

### 4. 自動化
```
新增知識時:
- 只需選擇 intent_id = 17
- access_level 自動從 intents 表繼承
- 不需要再手動選擇 audience
```

## 📊 SQL 查詢對比

### 當前（使用 audience）

```sql
SELECT kb.*, i.name as intent_name
FROM knowledge_base kb
LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
LEFT JOIN intents i ON kim.intent_id = i.id
WHERE
    kb.vendor_id = 1
    AND (
        kb.audience IS NULL
        OR kb.audience = ANY(ARRAY['租客', '房東', 'tenant', 'general',
                                   '租客|管理師', '房東|租客', '房東|租客|管理師'])
    )
    -- 需要維護複雜的映射表和硬編碼列表
```

### 方案 D（使用 access_level）

```sql
SELECT kb.*, i.name as intent_name, i.access_level
FROM knowledge_base kb
LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
LEFT JOIN intents i ON kim.intent_id = i.id
WHERE
    kb.vendor_id = 1
    AND (
        i.access_level = 'customer'  -- 簡單！
        OR i.access_level = 'both'
    )
    -- 不需要映射表，不需要硬編碼
```

## 🎯 總結

### access_level 的作用

1. **權限控制**: 決定哪些用戶角色可以看到該 Intent 的知識
2. **自動繼承**: 所有關聯該 Intent 的知識自動繼承權限
3. **集中管理**: 只需在 15 個 Intents 設定，不用在 479 個知識設定
4. **簡化邏輯**: 移除複雜的 audience 映射和硬編碼

### 實際效果

```
user_role = "customer" + intent.access_level = "customer"
  → ✅ 可以看到知識

user_role = "customer" + intent.access_level = "staff"
  → ❌ 看不到知識（隱藏內部管理知識）

user_role = "staff" + intent.access_level = "staff"
  → ✅ 可以看到知識

user_role = "staff" + intent.access_level = "customer"
  → ✅ 可以看到知識（員工可以看所有知識）
```

**就像是給每個 Intent 打上「客戶可見」或「員工專用」的標籤！**
