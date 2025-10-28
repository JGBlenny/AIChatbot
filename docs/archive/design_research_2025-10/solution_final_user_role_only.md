# 最終方案：只用 user_role（移除 audience）

## 🎯 用戶決策

> **「user_role 就行了，此系統的知識沒要分這麼細」**

## ✅ 最終方案

### 完全移除 audience 相關邏輯

```sql
-- 1. 移除 audience 欄位
ALTER TABLE knowledge_base DROP COLUMN audience;

-- 2. 刪除配置表
DROP TABLE IF EXISTS audience_config;
```

### 檢索邏輯簡化

```python
# vendor_knowledge_retriever.py

# 原本（複雜）
from services.business_scope_utils import get_allowed_audiences_for_scope
business_scope = "external" if user_role == "customer" else "internal"
allowed_audiences = get_allowed_audiences_for_scope(business_scope)

WHERE (
    kb.audience IS NULL
    OR kb.audience = ANY(allowed_audiences)
)

# 改為（簡單）
# 不做任何 audience 過濾
# 所有用戶看所有知識
```

### 完整 SQL（移除 audience）

```python
sql_query = f"""
    SELECT
        kb.id,
        kb.question_summary,
        kb.answer,
        kb.category,
        kb.scope,
        kb.priority,
        kb.is_template,
        kb.template_vars,
        kb.vendor_id,
        kb.business_types,  -- 保留（業態類型過濾）
        kb.created_at,
        kb.video_url,
        kb.video_file_size,
        kb.video_duration,
        kb.video_format,
        kim.intent_id,
        1 - (kb.embedding <=> %s::vector) as base_similarity,
        -- Intent 匹配加成
        CASE
            WHEN kim.intent_id = %s THEN 1.5
            WHEN kim.intent_id = ANY(%s::int[]) THEN 1.2
            ELSE 1.0
        END as intent_boost,
        (1 - (kb.embedding <=> %s::vector)) *
        CASE
            WHEN kim.intent_id = %s THEN 1.5
            WHEN kim.intent_id = ANY(%s::int[]) THEN 1.2
            ELSE 1.0
        END as boosted_similarity,
        CASE
            WHEN kb.scope = 'customized' AND kb.vendor_id = %s THEN 1000
            WHEN kb.scope = 'vendor' AND kb.vendor_id = %s THEN 500
            WHEN kb.scope = 'global' AND kb.vendor_id IS NULL THEN 100
            ELSE 0
        END as scope_weight
    FROM knowledge_base kb
    LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
    WHERE
        -- Scope 過濾
        (
            (kb.vendor_id = %s AND kb.scope IN ('customized', 'vendor'))
            OR
            (kb.vendor_id IS NULL AND kb.scope = 'global')
        )
        -- 向量存在
        AND kb.embedding IS NOT NULL
        -- 相似度閾值
        AND (1 - (kb.embedding <=> %s::vector)) >= %s
        -- Intent 過濾
        AND (kim.intent_id = ANY(%s::int[]) OR kim.intent_id IS NULL)
        -- ✅ 業態類型過濾（保留）
        AND {business_type_filter_sql}

        -- ❌ 移除 audience 過濾
        -- AND (
        --     %s::text[] IS NULL
        --     OR kb.audience IS NULL
        --     OR kb.audience = ANY(%s::text[])
        -- )

    ORDER BY
        scope_weight DESC,
        boosted_similarity DESC,
        kb.priority DESC
    LIMIT %s
"""
```

## 🗑️ 移除的文件和代碼

### 1. 刪除 business_scope_utils.py
```bash
rm /Users/lenny/jgb/AIChatbot/rag-orchestrator/services/business_scope_utils.py
```

### 2. 移除 chat.py 中的引用
```python
# chat.py

# 移除
from services.business_scope_utils import get_allowed_audiences_for_scope
business_scope = "external" if request.user_role == "customer" else "internal"
allowed_audiences = get_allowed_audiences_for_scope(business_scope)

# RAG 檢索時移除 allowed_audiences 參數
rag_results = await rag_engine.search(
    query=request.message,
    # allowed_audiences=allowed_audiences,  # ← 移除
    vendor_id=request.vendor_id
)
```

### 3. 移除 chat_stream.py 中的引用
```python
# chat_stream.py

# 移除
from services.business_scope_utils import get_allowed_audiences_for_scope
business_scope = "external" if request.user_role == "customer" else "internal"
allowed_audiences = get_allowed_audiences_for_scope(business_scope)

# 檢索時移除參數
results = await retriever.retrieve_knowledge_hybrid(
    question_embedding=embedding,
    vendor_id=request.vendor_id,
    # allowed_audiences=allowed_audiences,  # ← 移除
    user_role=request.user_role
)
```

### 4. 移除 vendor_knowledge_retriever.py 的參數
```python
# vendor_knowledge_retriever.py

async def retrieve_knowledge_hybrid(
    self,
    question_embedding: List[float],
    vendor_id: int,
    # allowed_audiences: Optional[List[str]] = None,  # ← 移除參數
    user_role: str = 'customer'
):
    """
    混合模式檢索：Intent 過濾 + 向量相似度排序

    參數:
        # allowed_audiences: 允許的受眾列表（用於 B2B/B2C 隔離），None 表示不過濾  # ← 移除註釋
    """

    # SQL 中移除 audience 過濾（見上面的 SQL）
```

### 5. 移除前端 audience 選擇
```vue
<!-- KnowledgeView.vue -->

<!-- 移除整個 audience 表單組 -->
<!-- <div class="form-group">
  <label>對象</label>
  <select v-model="formData.audience">
    <option value="">通用（所有業務範圍）</option>
    <option value="租客">租客</option>
    ...
  </select>
</div> -->

<!-- formData 初始化時移除 audience -->
formData: {
  question_summary: '',
  category: '',
  // audience: '',  // ← 移除
  content: '',
  keywords: [],
  // ...
}
```

### 6. 移除後端 audience 欄位
```python
# knowledge-admin/backend/app.py

class KnowledgeUpdate(BaseModel):
    question_summary: str
    category: str
    # audience: Optional[str] = None  # ← 移除
    content: str
    keywords: List[str] = []
    # ...
```

## 📋 保留的過濾邏輯

雖然移除 audience，但保留其他過濾：

```python
✅ 保留:
  - vendor_id (業者隔離)
  - scope (global/vendor/customized)
  - business_types (業態類型: 包租/代管/系統商)
  - intent_id (意圖匹配)
  - embedding similarity (向量相似度)

❌ 移除:
  - audience (對象過濾)
  - audience_config (配置表)
  - business_scope_utils.py (映射邏輯)
```

## 🎯 結果

### 所有用戶看到的知識
```
user_role = "customer" (租客/房東)
  → 看到所有知識（479 筆）
  → 包含之前標記為「管理師」的 105 筆知識

user_role = "staff" (管理師)
  → 看到所有知識（479 筆）
```

### 如果需要極少數隔離

如果未來發現某些知識真的不該給客戶看：

**選項 1: 不放入知識庫**
```
內部敏感資訊 → 不要放入 knowledge_base
改放在內部文檔系統
```

**選項 2: 用 scope 隔離**
```
內部知識 → scope = 'customized'，vendor_id = 特定業者
客戶知識 → scope = 'global'
```

**選項 3: 未來再加回簡單的布林值**
```sql
-- 極簡版本
ALTER TABLE knowledge_base ADD COLUMN is_internal BOOLEAN DEFAULT FALSE;

-- 只標記極少數內部知識
UPDATE knowledge_base SET is_internal = TRUE WHERE id IN (1, 2, 3);

-- 檢索時簡單過濾
WHERE (user_role = 'staff' OR kb.is_internal = FALSE)
```

## 🚀 遷移腳本

```sql
-- migration: 36-remove-audience.sql

BEGIN;

-- 1. 移除 knowledge_base 的 audience 欄位
ALTER TABLE knowledge_base DROP COLUMN IF EXISTS audience;

-- 2. 刪除 audience_config 表
DROP TABLE IF EXISTS audience_config;

-- 3. 記錄變更
INSERT INTO migration_log (migration_name, applied_at)
VALUES ('36-remove-audience', NOW());

COMMIT;
```

## 📊 代碼簡化對比

### 移除前
```python
# 1. 導入模組
from services.business_scope_utils import get_allowed_audiences_for_scope

# 2. 計算業務範圍
business_scope = "external" if request.user_role == "customer" else "internal"

# 3. 查詢允許的受眾
allowed_audiences = get_allowed_audiences_for_scope(business_scope)
# 返回: ['租客', '房東', 'tenant', 'general', '租客|管理師', '房東|租客', '房東|租客|管理師']

# 4. 傳遞給檢索
results = await retriever.retrieve_knowledge_hybrid(
    question_embedding=embedding,
    vendor_id=request.vendor_id,
    allowed_audiences=allowed_audiences,  # ← 複雜
    user_role=request.user_role
)

# 5. SQL 過濾
WHERE (
    %s::text[] IS NULL
    OR kb.audience IS NULL
    OR kb.audience = ANY(%s::text[])
)

總行數: ~200 行 (business_scope_utils.py + 呼叫代碼)
```

### 移除後
```python
# 1. 直接檢索
results = await retriever.retrieve_knowledge_hybrid(
    question_embedding=embedding,
    vendor_id=request.vendor_id,
    user_role=request.user_role  # ← 保留但不用於過濾
)

# 2. SQL 不做 audience 過濾
# (移除該段代碼)

總行數: 0 行新增，~200 行刪除
```

## ✅ 優勢

1. **極簡設計**
   - 移除 ~200 行代碼
   - 移除 2 個資料庫表/欄位
   - 移除 1 個服務模組

2. **維護成本降低**
   - 不需要維護 audience 映射
   - 新增知識時不需要選擇對象
   - 不需要更新 audience_config

3. **效能提升**
   - SQL 查詢減少一個 AND 條件
   - 減少 JOIN 或陣列比對

4. **靈活性**
   - 所有用戶看到所有知識
   - 未來如需隔離，可用更簡單的方式

## ⚠️ 注意事項

### 當前有 105 筆「管理師」知識

移除 audience 後，這些知識會對所有用戶可見：

```sql
SELECT COUNT(*) FROM knowledge_base WHERE audience = '管理師';
-- 結果: 105 筆

-- 例如:
-- "如何新增房東"
-- "後台操作手冊"
-- "業者設定說明"
```

**確認**: 這些知識讓租客看到沒問題嗎？

如果有問題，可以：
1. 手動刪除真正敏感的知識
2. 或保留極簡版本的 is_internal 布林值

## 🎯 總結

遵循用戶決策：
- ✅ 只用 user_role（保留參數但不用於過濾）
- ✅ 移除所有 audience 相關邏輯
- ✅ 極大簡化代碼和維護成本
- ✅ 所有用戶看到所有知識

**最簡單的設計！**
