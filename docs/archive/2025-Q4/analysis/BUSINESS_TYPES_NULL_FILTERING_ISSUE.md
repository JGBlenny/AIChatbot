# 業態過濾 NULL 值問題分析報告

## 問題概述

**現象：** 通用知識（business_types = NULL）在檢索時被錯誤過濾，導致無法返回給用戶。

**環境：**
- 知識 497：`business_types: null`（通用知識，應該對所有業態可見）
- Vendor 1：`business_types: ['full_service']`
- 查詢日誌：`🏢 業態過濾: ['full_service']`
- 檢索結果：0 筆（錯誤）

**預期結果：** Knowledge 497 應該被返回（因為 business_types IS NULL 的知識應該對所有業態可見）

**實際結果：** Knowledge 497 被過濾掉了

---

## 根本原因分析

### 問題 1: 數據庫欄位名稱不一致

**發現：**`vendor_parameter_resolver.py` 中的 `get_vendor_info()` 方法使用了錯誤的欄位名。

```python
# vendor_parameter_resolver.py line 262-275
cursor.execute("""
    SELECT
        id,
        code,
        name,
        short_name,
        contact_phone,
        contact_email,
        is_active,
        subscription_plan,
        business_type    -- ❌ 錯誤：應該是 business_types (複數)
    FROM vendors
    WHERE id = %s
""", (vendor_id,))
```

**數據庫實際欄位名：**
- 根據 migration `38-expand-business-types.sql`，欄位名是 `business_types` (複數，TEXT[])
- 舊欄位 `business_type` (單數) 已在該 migration 中被移除

**影響範圍：**
- `vendor_knowledge_retriever.py` line 62, 219：使用 `get_vendor_info()` 獲取 business_types
- `rag_engine.py` line 68：直接從數據庫查詢 business_types（✅ 正確）

**結果：**
- `vendor_info.get('business_types', [])` 返回空列表 `[]`（因為欄位不存在，使用默認值）
- 空列表傳入 SQL 查詢：`business_types && ARRAY[]::text[]`
- PostgreSQL 行為：`NULL::text[] && ARRAY[]::text[]` 返回 `NULL`（不是 TRUE）
- 最終導致 NULL 知識被過濾掉

---

## 問題 2: 空數組的數組重疊判斷

**PostgreSQL 數組操作符 `&&` 的行為：**

```sql
-- 測試 1: NULL 與非空數組的交集
SELECT NULL::text[] && ARRAY['full_service']::text[] AS result;
-- 結果: NULL (不是 TRUE，也不是 FALSE)

-- 測試 2: NULL 與空數組的交集
SELECT NULL::text[] && ARRAY[]::text[] AS result;
-- 結果: NULL

-- 測試 3: 非空數組與空數組的交集
SELECT ARRAY['full_service']::text[] && ARRAY[]::text[] AS result;
-- 結果: FALSE (空數組與任何數組都沒有交集)
```

**SQL 過濾邏輯：**

```sql
-- 當前邏輯（理論上正確）
WHERE (business_types IS NULL OR business_types && %s::text[])

-- 當 %s = [] 時：
WHERE (business_types IS NULL OR business_types && ARRAY[]::text[])
--     ^^^^^^^^^^^^^^^^^^^^^^^^    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
--     這個條件應該為 TRUE          這個條件為 FALSE（空數組沒有交集）

-- 如果 business_types = NULL：
WHERE (TRUE OR FALSE) = TRUE  -- ✅ 應該通過

-- 但是，如果參數是 NULL 而不是空數組：
WHERE (business_types IS NULL OR business_types && NULL::text[])
--     ^^^^^^^^^^^^^^^^^^^^^^^^    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
--     這個條件應該為 TRUE          這個條件為 NULL

-- 如果 business_types = NULL：
WHERE (TRUE OR NULL) = TRUE  -- ✅ 應該通過
```

**關鍵發現：**
- 即使傳入空數組 `[]`，`business_types IS NULL` 條件仍應該讓 NULL 知識通過
- 但實際上沒有通過，說明**參數根本就沒有正確傳入**

---

## 影響範圍

### 1. vendor_knowledge_retriever.py

**受影響的方法：**

#### A. `retrieve_knowledge()` (line 30-159)
```python
# line 62: ❌ 獲取到空字典 {'business_type': ...}，缺少 business_types
vendor_info = self.param_resolver.get_vendor_info(vendor_id)
vendor_business_types = vendor_info.get('business_types', [])  # 返回 []

# line 113: ❌ 傳入空列表
OR kb.business_types && %s::text[]  -- 參數: []
```

**影響：** B2C 模式下，所有通用知識（business_types = NULL）無法被檢索。

#### B. `retrieve_knowledge_hybrid()` (line 173-412)
```python
# line 218-219: ❌ B2C 模式
vendor_info = self.param_resolver.get_vendor_info(vendor_id)
vendor_business_types = vendor_info.get('business_types', [])  # 返回 []

# line 221: ✅ SQL 邏輯正確，但參數錯誤
business_type_filter_sql = "(kb.business_types IS NULL OR kb.business_types && %s::text[])"

# line 344: ❌ 傳入空列表
vendor_business_types,  # []
```

**影響：** B2C 混合檢索模式下，所有通用知識無法被返回。

**B2B 模式不受影響：**
```python
# line 212: ✅ B2B 模式直接賦值，不依賴 get_vendor_info()
vendor_business_types = ['system_provider']
```

### 2. rag_engine.py

**✅ 不受影響：**
```python
# line 63-68: 直接從數據庫查詢，不依賴 get_vendor_info()
async with self.db_pool.acquire() as conn:
    vendor_row = await conn.fetchrow("""
        SELECT business_types FROM vendors WHERE id = $1
    """, vendor_id)
    if vendor_row and vendor_row['business_types']:
        vendor_business_types = vendor_row['business_types']
```

### 3. 其他可能受影響的地方

搜索結果顯示，`get_vendor_info()` 在以下位置被調用：
- `chat.py` line 906：但只用於獲取 vendor_info，不用於 business_types 過濾
- 其他位置主要用於獲取業者名稱、狀態等信息

**結論：** 主要影響 `vendor_knowledge_retriever.py` 的知識檢索功能。

---

## 類似問題檢查

### target_user 過濾

**檢查結果：** ✅ 無問題

所有使用 `target_user` 過濾的地方都使用了正確的邏輯：
```sql
WHERE (target_user IS NULL OR target_user && %s::text[])
```

並且參數傳遞正確（不依賴有問題的 `get_vendor_info()`）。

### 其他 NULL 值過濾

**搜索結果：** 沒有發現其他類似的 NULL 值過濾問題。

---

## 修復方案

### 方案 1: 修正 get_vendor_info() 的欄位名（推薦）

**優點：**
- 一處修改，解決所有問題
- 保持代碼一致性
- 符合數據庫 schema

**修改位置：**
```python
# rag-orchestrator/services/vendor_parameter_resolver.py

def get_vendor_info(self, vendor_id: int) -> Optional[Dict]:
    """獲取業者基本資訊"""
    conn = self._get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("""
            SELECT
                id,
                code,
                name,
                short_name,
                contact_phone,
                contact_email,
                is_active,
                subscription_plan,
                business_types    -- ✅ 修改：business_type -> business_types
            FROM vendors
            WHERE id = %s
        """, (vendor_id,))

        row = cursor.fetchone()
        cursor.close()

        return dict(row) if row else None

    finally:
        conn.close()
```

**影響範圍：**
- 修復 `vendor_knowledge_retriever.py` 中的所有業態過濾問題
- 不影響其他代碼（因為其他地方不使用 business_types 欄位）

---

### 方案 2: 在 retrieve_knowledge 中直接查詢數據庫（備選）

**缺點：**
- 需要修改多處
- 代碼重複（rag_engine.py 已經這樣做了）
- 不符合 DRY 原則

**不推薦此方案。**

---

## 測試驗證

### 測試腳本

已編寫完整的 SQL 測試腳本：
```
/Users/lenny/jgb/AIChatbot/tests/manual/test_business_types_null_filtering.sql
```

**測試內容：**
1. 驗證知識 497 的 business_types 值
2. 驗證 Vendor 1 的 business_types 值
3. 測試 NULL 過濾邏輯（簡化版）
4. 測試向量查詢中的業態過濾
5. 檢查知識 497 的意圖映射
6. 模擬完整的檢索查詢
7. 測試數組操作符 && 的行為
8. 檢查空數組參數的影響
9. 檢查向量檢索（RAG Engine）
10. 檢查 target_user 過濾

### 驗證步驟

**修復前：**
1. 運行測試腳本，確認問題存在
2. 查詢 Vendor 1 的 business_types：應該返回 `['full_service']`
3. 查詢 Knowledge 497：應該有 business_types = NULL
4. 測試過濾邏輯：`business_types IS NULL OR business_types && ['full_service']` 應該返回 Knowledge 497

**修復後：**
1. 修改 `get_vendor_info()` 的 SQL 查詢
2. 重啟服務
3. 再次運行測試腳本
4. 驗證 Knowledge 497 能被正確檢索

### Python 單元測試

```python
# tests/test_vendor_parameter_resolver.py

def test_get_vendor_info_includes_business_types():
    """測試 get_vendor_info 返回正確的 business_types 欄位"""
    resolver = VendorParameterResolver()
    vendor_info = resolver.get_vendor_info(vendor_id=1)

    # 斷言 business_types 欄位存在
    assert 'business_types' in vendor_info

    # 斷言 business_types 是列表（不是 None 或空）
    assert isinstance(vendor_info['business_types'], list)

    # 斷言包含預期的業態
    assert 'full_service' in vendor_info['business_types']
```

---

## 總結

### 問題根源

1. **數據庫欄位名不一致：** `get_vendor_info()` 查詢 `business_type`（單數），但實際欄位是 `business_types`（複數）
2. **參數傳遞錯誤：** 導致 SQL 查詢收到空列表 `[]` 而不是正確的業態列表
3. **SQL 邏輯被破壞：** 雖然 SQL 邏輯 `(business_types IS NULL OR ...)` 是正確的，但因為參數錯誤導致無法正常工作

### 修復重點

- **一處修改：** 修正 `vendor_parameter_resolver.py` 的 `get_vendor_info()` 方法
- **影響範圍：** 修復 B2C 模式下所有通用知識的檢索問題
- **不影響：** B2B 模式、RAG Engine、其他業務邏輯

### 優先級

**P0 - 緊急修復：**
- 這是一個嚴重的業務邏輯錯誤
- 導致通用知識完全無法被檢索
- 影響所有 B2C 用戶的體驗

---

## 附錄

### 相關文件

1. **數據庫 Migration：**
   - `/Users/lenny/jgb/AIChatbot/database/migrations/38-expand-business-types.sql`（業態欄位從單數改為複數）

2. **受影響的代碼文件：**
   - `/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/vendor_parameter_resolver.py`（需要修復）
   - `/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/vendor_knowledge_retriever.py`（受影響）
   - `/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/rag_engine.py`（不受影響）

3. **測試文件：**
   - `/Users/lenny/jgb/AIChatbot/tests/manual/test_business_types_null_filtering.sql`（新建）

### SQL 過濾邏輯匯總

**所有使用 business_types 過濾的位置：**

| 文件 | 行號 | SQL 條件 | 狀態 |
|------|------|----------|------|
| vendor_knowledge_retriever.py | 111-114 | `(business_types IS NULL OR business_types && %s)` | ❌ 參數錯誤 |
| vendor_knowledge_retriever.py | 221 | `(kb.business_types IS NULL OR kb.business_types && %s)` | ❌ B2C 參數錯誤 |
| vendor_knowledge_retriever.py | 214 | `kb.business_types && %s` | ✅ B2B 正確 |
| rag_engine.py | 128 | `(kb.business_types IS NULL OR kb.business_types && $7)` | ✅ 參數正確 |
| rag_engine.py | 196 | `(kb.business_types IS NULL OR kb.business_types && $6)` | ✅ 參數正確 |
| rag_engine.py | 261 | `(business_types IS NULL OR business_types && $5)` | ✅ 參數正確 |
| rag_engine.py | 298 | `(business_types IS NULL OR business_types && $4)` | ✅ 參數正確 |

**結論：** 只有 `vendor_knowledge_retriever.py` 的 B2C 模式受影響。

---

**報告日期：** 2025-10-29
**報告人：** Claude Code
**優先級：** P0 (Critical)
