# 方案 A：user_role + category 實際運作說明

## 核心概念

**移除 audience 欄位，改用 `user_role` + `category` 組合來過濾知識**

## 當前狀況 vs 簡化後

### 當前（複雜）
```python
# 1. 根據 user_role 決定 business_scope
business_scope = "external" if user_role == "customer" else "internal"

# 2. 查詢允許的 audience 列表
allowed_audiences = get_allowed_audiences_for_scope(business_scope)
# 返回: ['租客', '房東', 'tenant', 'general', '租客|管理師', ...]

# 3. SQL 過濾
WHERE (
    kb.audience IS NULL
    OR kb.audience = ANY(['租客', '房東', 'tenant', ...])
)
```

### 簡化後（方案 A）
```python
# 1. 直接用 user_role 過濾 category
if user_role == "customer":
    # B2C: 排除內部管理的 category
    WHERE category NOT IN ('內部管理', '系統操作', '後台設定')
elif user_role == "staff":
    # B2B: 查詢所有知識（不過濾）
    # 或者只看內部管理的
    WHERE category IN ('內部管理', '系統操作', '後台設定')
```

## 實際實現

### 修改 1: vendor_knowledge_retriever.py

```python
# 原代碼（使用 allowed_audiences）
async def retrieve_knowledge_hybrid(
    self,
    question_embedding: List[float],
    vendor_id: int,
    allowed_audiences: Optional[List[str]] = None,  # ← 移除這個參數
    user_role: str = 'customer'
):
    # ... SQL 查詢
    AND (
        %s::text[] IS NULL
        OR kb.audience IS NULL
        OR kb.audience = ANY(%s::text[])  # ← 移除這部分
    )
```

**改為**:

```python
async def retrieve_knowledge_hybrid(
    self,
    question_embedding: List[float],
    vendor_id: int,
    user_role: str = 'customer'  # ← 只保留 user_role
):
    # 定義內部管理的 category
    internal_categories = ['內部管理', '系統操作', '後台設定']

    # 根據 user_role 決定過濾條件
    if user_role == 'customer':
        # B2C: 排除內部管理知識
        sql_filter = "AND kb.category NOT IN %s"
        filter_params = (tuple(internal_categories),)
    elif user_role == 'staff':
        # B2B: 不過濾（或只看內部知識）
        sql_filter = ""  # 不過濾，查詢所有
        filter_params = ()

    # SQL 查詢（移除 audience 過濾）
    query = f"""
        SELECT
            kb.id,
            kb.question_summary,
            kb.answer,
            kb.category,  -- category 仍保留
            -- ... 其他欄位
        FROM knowledge_base kb
        WHERE kb.vendor_id = %s
          {sql_filter}  -- 用 category 過濾取代 audience
        ORDER BY similarity DESC
        LIMIT %s
    """
```

### 修改 2: chat_stream.py

```python
# 原代碼
business_scope = "external" if request.user_role == "customer" else "internal"
allowed_audiences = get_allowed_audiences_for_scope(business_scope)  # ← 移除

results = await retriever.retrieve_knowledge_hybrid(
    question_embedding=embedding,
    vendor_id=request.vendor_id,
    allowed_audiences=allowed_audiences,  # ← 移除
    user_role=request.user_role
)
```

**改為**:

```python
# 簡化：直接傳 user_role
results = await retriever.retrieve_knowledge_hybrid(
    question_embedding=embedding,
    vendor_id=request.vendor_id,
    user_role=request.user_role  # ← 只需要這個
)
```

### 修改 3: 移除 business_scope_utils.py

```python
# 這個整個檔案可以刪除
# - FALLBACK_AUDIENCE_MAPPING
# - get_allowed_audiences_for_scope()
# - audience_config 表也可以刪除
```

## 優勢與劣勢對比

### ✅ 優勢

1. **代碼簡化**：
   - 移除 `business_scope_utils.py`（~200 行）
   - 移除 `audience_config` 表
   - 移除 `FALLBACK_AUDIENCE_MAPPING` 硬編碼
   - SQL 查詢減少一個 AND 條件

2. **邏輯清晰**：
   ```python
   # 簡單易懂
   if user_role == "customer":
       # 客戶看不到內部管理知識
   elif user_role == "staff":
       # 員工看所有知識
   ```

3. **維護成本低**：
   - 只需維護 internal_categories 列表
   - 新增知識時不需要選擇 audience

4. **語義更明確**：
   - category = "內部管理" 比 audience = "管理師" 更清楚

### ❌ 劣勢

1. **無法細分租客和房東**：
   ```python
   # 當前可以區分
   audience = "租客"    # 332 筆
   audience = "房東"    # 25 筆

   # 簡化後無法區分（除非用 category）
   category = "租客指南"
   category = "房東指南"
   ```

2. **需要重新分類現有知識**：
   ```sql
   -- 需要將 audience 映射到 category
   UPDATE knowledge_base
   SET category = '租客指南'
   WHERE audience = '租客';

   UPDATE knowledge_base
   SET category = '內部管理'
   WHERE audience = '管理師';
   ```

3. **如果未來有更多角色**：
   - 例如：清潔人員、仲介、會計
   - 用 category 可能不夠靈活

## 實際範例

### 場景 1: 租客查詢

```python
# API 請求
{
    "question": "租金怎麼繳？",
    "vendor_id": 1,
    "user_role": "customer"  # B2C
}

# 系統過濾
WHERE category NOT IN ('內部管理', '系統操作', '後台設定')

# 可檢索到的知識
✅ category = "租約管理"  (包含租金相關)
✅ category = "租金問題"
✅ category = "維修報修"
❌ category = "內部管理"  (被排除)
```

### 場景 2: 管理師查詢

```python
# API 請求
{
    "question": "如何新增租客？",
    "vendor_id": 1,
    "user_role": "staff"  # B2B
}

# 系統過濾
# 不過濾 category（或只看內部）

# 可檢索到的知識
✅ category = "內部管理"  (管理師操作)
✅ category = "系統操作"
✅ category = "租約管理"  (如果需要了解流程)
```

## 遷移步驟

### 步驟 1: 分析當前 category 分佈

```sql
SELECT category, COUNT(*) as count
FROM knowledge_base
GROUP BY category
ORDER BY count DESC;
```

### 步驟 2: 定義內部管理的 category

```python
# 在配置中定義
INTERNAL_CATEGORIES = [
    '內部管理',
    '系統操作',
    '後台設定',
    # 根據實際情況添加
]
```

### 步驟 3: 確認所有知識都有正確的 category

```sql
-- 檢查是否有 NULL category
SELECT COUNT(*) FROM knowledge_base WHERE category IS NULL;

-- 如果有，需要補上適當的 category
UPDATE knowledge_base
SET category = CASE
    WHEN audience = '管理師' THEN '內部管理'
    WHEN audience = '租客' THEN '租約管理'
    -- ... 其他映射
END
WHERE category IS NULL;
```

### 步驟 4: 修改代碼（如上述範例）

### 步驟 5: 移除 audience 相關代碼和表

```sql
-- 移除 audience 欄位
ALTER TABLE knowledge_base DROP COLUMN audience;

-- 刪除配置表
DROP TABLE IF EXISTS audience_config;
```

## 決策關鍵問題

**你需要回答這個問題**：

### ❓ 租客和房東需要嚴格區分嗎？

**情況 1: 不需要區分**
```
→ 方案 A 完全足夠
→ 用 category 區分「內部」vs「客戶」即可
→ 租客和房東都是 B2C，看到相同的知識
```

**情況 2: 需要區分**
```
→ 方案 A 需要調整
→ 用 category 細分：
   - "租客指南" (只給租客)
   - "房東指南" (只給房東)
   - "通用客服" (兩者都看)

→ SQL 過濾變為：
   if user_role == "customer" and user_type == "tenant":
       WHERE category IN ('租客指南', '通用客服')
   elif user_role == "customer" and user_type == "landlord":
       WHERE category IN ('房東指南', '通用客服')
```

**但這樣又變複雜了** → 不如直接用方案 C (布林值)

## 結論

### 推薦使用方案 A 的情況

✅ **如果你的系統**：
1. 不需要區分租客和房東
2. 只需要 B2C/B2B 隔離
3. category 已經有明確的分類
4. 追求極簡設計

### 不推薦使用方案 A 的情況

❌ **如果你的系統**：
1. 租客和房東需要看到不同的知識
2. 未來可能有更多角色（清潔、仲介等）
3. category 主要用於知識分類，不想混用為權限控制

## 我的建議

基於你的系統（480 筆知識，77% B2C，23% B2B），我認為：

**方案 C（布林值）> 方案 A（user_role + category）**

理由：
- 方案 C 保留了未來擴展的可能性
- 方案 A 將 category 用於權限控制，可能與知識分類的語義衝突
- 方案 C 的開發成本只比方案 A 多一點點

但如果你確定：
- 永遠不需要區分租客/房東
- category 本來就是按對象分類的
- 追求最簡設計

那麼 **方案 A 也是可行的**。
