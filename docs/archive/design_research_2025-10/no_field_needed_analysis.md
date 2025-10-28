# 「不需要 is_staff_only」分析

## 🤔 可能的含義

### 理解 1: 不需要任何權限控制？
```python
# 所有用戶看所有知識
if user_role == 'customer':
    # 查詢所有知識（不過濾）

if user_role == 'staff':
    # 查詢所有知識（不過濾）
```

**問題**: 租客會看到「系統操作」、「後台管理」等內部知識

---

### 理解 2: 用 Intent 的現有欄位判斷？

#### 可能性 A: 用 Intent.type
```sql
-- intents 表已有 type 欄位
SELECT id, name, type FROM intents;

id | name       | type
---|-----------|----------
1  | 退租流程   | knowledge
6  | 帳務查詢   | data_query
8  | 設備報修   | action
17 | 系統操作   | knowledge  ← 和其他 knowledge 沒區別
```

**問題**: type = "knowledge" 無法區分客戶知識 vs 內部知識

#### 可能性 B: 用 Intent.name 關鍵字
```python
# 根據名稱判斷
internal_keywords = ['系統', '後台', '管理', '業者']

if user_role == 'customer':
    WHERE i.name NOT LIKE '%系統%'
      AND i.name NOT LIKE '%後台%'
      AND i.name NOT LIKE '%管理%'
```

**問題**:
- 不可靠（如果 intent 改名？）
- 維護困難（需要維護關鍵字列表）
- 可能誤判（「設備管理」是內部的嗎？）

---

### 理解 3: user_role 本身就足夠？

```python
# API 層面控制
if user_role == 'customer':
    # 調用 customer 專用的 API
    endpoint = '/api/customer/chat'

if user_role == 'staff':
    # 調用 staff 專用的 API
    endpoint = '/api/staff/chat'
```

**問題**:
- 兩個 API 端點要各自維護
- 無法靈活控制單個 intent 的權限

---

### 理解 4: 完全移除 audience，不做任何替代？

```python
# 當前
WHERE kb.audience = ANY(['租客', '房東', ...])  # 複雜

# 改為
# （不加任何過濾）  # 簡單
```

**結果**:
- ✅ 代碼最簡化
- ❌ 所有用戶看到所有知識
- ❌ 租客會看到內部管理知識

---

## 🎯 你的想法是？

請告訴我你的意思：

### A. 完全不需要隔離
```
所有用戶（租客、管理師）看到相同的知識
→ 移除所有 audience 相關邏輯，不做替代
```

### B. 用 Intent 名稱判斷
```
根據 intent.name 包含的關鍵字判斷是否內部知識
→ 不需要新增欄位
```

### C. 用 Intent.type 判斷
```
根據 intent.type 判斷權限
→ 可能需要新增 type 值（如 "internal"）
```

### D. 用 API 層級隔離
```
customer 和 staff 調用不同的 API endpoint
→ 資料庫層不做過濾
```

### E. 其他想法？
```
你有其他的設計思路？
```

---

## 📊 當前 audience 的實際作用

讓我先確認當前 audience 在做什麼：

```sql
-- 當前統計
SELECT audience, COUNT(*) FROM knowledge_base GROUP BY audience;

audience        | count
----------------|-------
租客            | 332 (69%)
管理師          | 105 (22%)  ← B2B 內部知識
房東            | 25 (5%)
tenant          | 11
租客|管理師     | 2
房東|租客       | 1
```

**如果移除 audience 過濾**：
- 租客會看到 105 筆「管理師」專用知識
- 例如：「如何新增房東」、「後台操作手冊」

**這是你想要的嗎？**

---

## 🤔 我的猜測

你可能的想法：

1. **Intent 的語義本身就足夠**
   - "系統操作" 這個名字就說明是內部的
   - 不需要額外的布林值標記

2. **過度設計**
   - 當前 audience 太複雜
   - 實際上可能不需要這麼細的權限控制

3. **實務上用不到**
   - 租客和管理師可能用不同的入口（不同 URL/系統）
   - 已經在前端隔離了，後端不需要再過濾

請告訴我你的想法！
