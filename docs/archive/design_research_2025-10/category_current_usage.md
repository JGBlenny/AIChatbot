# Category 欄位當前使用情況分析

## 📊 資料庫現況

### 當前分佈（479 筆知識）
```
category      | count
--------------+-------
合約問題      | 167 筆 (35%)
帳務問題      | 153 筆 (32%)
服務問題      | 144 筆 (30%)
設備報修      |   4 筆 (1%)
設施使用      |   3 筆
設施問題      |   2 筆
其他          |   1 筆
預約看房      |   1 筆
寵物相關      |   1 筆
帳務查詢      |   1 筆
設施維修      |   1 筆
unclear       |   1 筆
```

## 🔍 檢索邏輯中的使用

### ❌ 檢索時**沒有**使用 category 過濾

查看 `vendor_knowledge_retriever.py:247-315` 的 SQL 查詢：

```sql
SELECT
    kb.id,
    kb.question_summary,
    kb.answer,
    kb.category,  -- ✅ 只是返回欄位
    kb.audience,
    kb.business_types,
    -- ... 其他欄位
FROM knowledge_base kb
WHERE
    -- Scope 過濾
    (kb.vendor_id = %s AND kb.scope IN ('customized', 'vendor'))
    OR (kb.vendor_id IS NULL AND kb.scope = 'global')

    -- 向量相似度閾值
    AND (1 - (kb.embedding <=> %s::vector)) >= %s

    -- Intent 過濾
    AND (kim.intent_id = ANY(%s::int[]) OR kim.intent_id IS NULL)

    -- ✅ 業態類型過濾
    AND (kb.business_types IS NULL OR kb.business_types && %s::text[])

    -- ✅ Audience 過濾
    AND (
        %s::text[] IS NULL
        OR kb.audience IS NULL
        OR kb.audience = ANY(%s::text[])
    )

    -- ❌ 沒有 category 過濾！
```

### 實際過濾條件

當前檢索只使用以下過濾：
1. **vendor_id + scope**: 業者隔離 + 全域/專屬
2. **intent_id**: 意圖匹配
3. **business_types**: 業態類型（包租/代管/系統商）
4. **audience**: B2C/B2B 隔離（租客/房東/管理師）
5. **embedding similarity**: 向量相似度

**category 完全沒參與過濾！**

## 🖥️ 前端使用

### 表單中必填
```vue
<label>分類 *</label>
<select v-model="formData.category" required>
  <option value="">請選擇</option>
  <!-- 動態載入 categories -->
</select>
```

### API 端點
```javascript
// knowledge-admin/frontend/src/views/KnowledgeView.vue:513
const response = await axios.get(`${API_BASE}/category-config`);
this.categories = response.data.categories || [];
```

### 顯示用途
```vue
<!-- 知識列表中顯示 category -->
<td>{{ item.category }}</td>
```

## 📋 配置表

存在 `category_config` 表：
```sql
-- database/migrations/40-create-category-config.sql
CREATE TABLE IF NOT EXISTS category_config (
    id SERIAL PRIMARY KEY,
    category_value VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    display_order INT DEFAULT 999,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## 🎯 結論

### category 當前的作用

✅ **有的功能**:
1. 前端表單必填欄位
2. 資料庫儲存
3. 列表顯示
4. 配置管理（category_config 表）

❌ **沒有的功能**:
1. **檢索過濾** - SQL 查詢不使用
2. **權限控制** - 不影響 B2C/B2B 隔離
3. **相似度加成** - 不影響排序

### 實際意義

**category 目前只是「純粹的標籤/分類」，用於人工管理和顯示，不影響 AI 檢索邏輯。**

等同於：
```python
# 當前 category 的作用
category = "帳務問題"  # ← 只是個標籤，不影響檢索

# 實際檢索靠的是
- 向量相似度 (embedding)
- Intent 匹配 (intent_id)
- Audience 過濾 (audience)
- 業態過濾 (business_types)
```

## 💡 這意味著什麼？

### 對「方案 A：user_role + category」的影響

**✅ 可以直接重新利用 category 欄位！**

因為 category 目前沒有被用於權限控制，我們可以：

1. **改變 category 的語義**：
   ```
   原本: 純粹分類（合約、帳務、服務）
   改為: 權限控制（內部管理、客戶知識）
   ```

2. **或者新增權限相關的 category**：
   ```
   category = "內部管理"  → 只有 staff 可見
   category = "合約問題"  → customer 和 staff 都可見
   ```

3. **在檢索邏輯中加入 category 過濾**：
   ```python
   # vendor_knowledge_retriever.py 新增
   if user_role == "customer":
       sql_filter = "AND kb.category NOT IN ('內部管理', '系統操作')"
   ```

### 風險評估

⚠️ **潛在問題**：

1. **語義混淆**：
   - category 原本用於「業務分類」
   - 改為「權限控制」可能讓維護人員困惑

2. **需要重新分類**：
   - 現有 479 筆知識都已有 category
   - 需要決定哪些是「內部管理」

3. **配置衝突**：
   - category_config 表可能需要調整
   - 前端下拉選單需要更新提示文字

## 📊 對比：Category vs Audience

| 欄位 | 當前作用 | 是否用於檢索 | 配置來源 |
|------|---------|-------------|----------|
| **category** | 業務分類（合約/帳務/服務） | ❌ 不使用 | category_config 表 |
| **audience** | 權限控制（租客/房東/管理師） | ✅ 使用 | audience_config 表 + 硬編碼 |
| **business_types** | 業態類型（包租/代管/系統商） | ✅ 使用 | business_types_config 表 |
| **intent_id** | 意圖分類 | ✅ 使用 | intents 表 |

## 🤔 決策建議

### 選項 1: 保持 category 純粹

**不使用 category 做權限控制**，維持現狀：
- category = 業務分類（合約、帳務等）
- audience = 權限控制（租客、管理師等）
- 推薦：方案 C（簡化 audience 為布林值）

### 選項 2: 重新定義 category

**讓 category 承擔權限控制**，實施方案 A：
- 移除 audience 欄位
- category 改為權限導向（「內部管理」vs「客戶知識」）
- 風險：語義混淆 + 需要大規模重新分類

### 選項 3: 同時保留

**category 和 audience 各司其職**：
- category = 業務分類（不影響檢索）
- audience = 權限控制（簡化為布林值）
- 推薦：這是最清晰的方案

## 🎯 我的建議

基於以上分析，我推薦 **選項 3**：

**保留 category 作為業務分類，簡化 audience 為布林值**

理由：
1. ✅ 語義清晰：category = 分類，is_internal = 權限
2. ✅ 低風險：不需要重新分類 479 筆知識
3. ✅ 向後兼容：現有 category 資料完全不受影響
4. ✅ 最小變更：只需簡化 audience

具體實施：
```sql
-- 新增 is_internal 欄位
ALTER TABLE knowledge_base ADD COLUMN is_internal BOOLEAN DEFAULT FALSE;

-- 遷移 audience → is_internal
UPDATE knowledge_base
SET is_internal = TRUE
WHERE audience IN ('管理師', '系統管理員', '房東/管理師');

-- 移除 audience
ALTER TABLE knowledge_base DROP COLUMN audience;

-- category 保持不變，繼續作為業務分類
-- 不影響檢索邏輯
```

這樣：
- **category 繼續做分類** → "合約問題"、"帳務問題"...
- **is_internal 做權限** → TRUE/FALSE
- **檢索邏輯簡化** → 只需檢查 is_internal
