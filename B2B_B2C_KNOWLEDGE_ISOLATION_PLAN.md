# B2B/B2C 知識隔離方案

**日期**: 2025-10-12
**優先級**: 🔴 高（資料安全與業務範圍隔離）

---

## 1. 問題陳述

### 1.1 用戶需求
> "像是『設定用戶權限』在 B2C 就不該回答"

### 1.2 當前架構問題

**核心問題**：所有 global 知識對所有業者可見，缺乏業務範圍隔離。

#### 現狀分析

1. **知識庫結構**
   - 467 筆 global 知識
   - 0 筆 vendor-specific 知識
   - 知識通過 `audience` 欄位標記受眾（租客、管理師、系統管理員等）

2. **Audience 分布**
   | Audience | 數量 | 業務範圍 |
   |----------|------|---------|
   | 租客 | 329 | B2C (external) |
   | 房東 | 25 | B2C (external) |
   | **管理師** | **105** | **B2B (internal)** |
   | **系統管理員** | **1** | **B2B (internal)** |

3. **管理師 audience 知識範例**（B2B 內部管理）
   - 「加盟主進入系統後的頁面不正常，無法建物件」
   - 「系統列印收據時發現缺少X6個月，該如何處理？」
   - 「如何處理租客的押金退還狀態？」
   - 「合約建立流程中出現重複帳單，該如何處理？」

4. **租客 audience 知識範例**（B2C 租客服務）
   - 「如何辦理退租？退租流程是什麼？」
   - 「如何報修？維修流程是什麼？」
   - 「如何繳費？有哪些繳費方式？」

#### 當前檢索邏輯的過濾機制

**VendorKnowledgeRetriever.retrieve_knowledge_hybrid()**:
```sql
WHERE
    -- ✅ Scope 過濾
    (
        (kb.vendor_id = %s AND kb.scope IN ('customized', 'vendor'))
        OR
        (kb.vendor_id IS NULL AND kb.scope = 'global')
    )
    -- ✅ 向量存在
    AND kb.embedding IS NOT NULL
    -- ✅ 相似度閾值
    AND (1 - (kb.embedding <=> %s::vector)) >= %s
    -- ✅ Intent 過濾
    AND (kim.intent_id = ANY(%s::int[]) OR kim.intent_id IS NULL)
    -- ❌ 沒有 audience 過濾
    -- ❌ 沒有 business_scope 過濾
```

**RAG Engine.search()**:
```sql
WHERE kb.embedding IS NOT NULL
    AND (1 - (kb.embedding <=> $1::vector)) >= $2
    AND (kim.intent_id = ANY($5::int[]) OR kim.intent_id IS NULL)
    -- ❌ 沒有 audience 過濾
    -- ❌ 沒有 business_scope 過濾
```

### 1.3 風險與影響

| 風險 | 嚴重性 | 影響 |
|------|-------|------|
| **資料外洩** | 🔴 高 | B2C 租客可能看到 B2B 內部系統管理知識 |
| **用戶體驗差** | 🟡 中 | 租客問「設定用戶權限」會得到不相關的系統管理答案 |
| **業務範圍混淆** | 🟡 中 | Vendor 1 (B2C) 可以檢索到 B2B 管理師知識 |

#### 實際案例

**測試場景**: Vendor 1 (external/B2C) 用戶問「設定用戶權限」

**預期行為**:
- ❌ 不應該檢索到任何 B2B 內部管理知識
- ✅ 應該返回兜底回應或提示不相關

**實際行為** (如果有相關知識):
- ⚠️ 可能檢索到「管理師」audience 的知識
- ⚠️ 可能檢索到「系統管理員」audience 的知識

---

## 2. 解決方案設計

### 方案 A: 使用現有 `audience` 欄位進行過濾（推薦 - 短期快速方案）

#### 2.1 方案概述

利用現有的 `audience` 欄位，根據 Vendor 的 `business_scope_name` 映射到允許的 audience 列表。

#### 2.2 Audience 與 Business Scope 映射

```python
BUSINESS_SCOPE_AUDIENCE_MAPPING = {
    'external': {  # B2C 包租代管
        'allowed_audiences': ['租客', '房東', '租客|管理師', '房東|租客', '房東|租客|管理師', 'tenant', 'general'],
        'blocked_audiences': ['管理師', '系統管理員', '房東/管理師']  # 明確排除 B2B
    },
    'internal': {  # B2B 系統商
        'allowed_audiences': ['管理師', '系統管理員', '租客|管理師', '房東|租客|管理師', '房東/管理師', 'general'],
        'blocked_audiences': ['租客', '房東', 'tenant']  # 明確排除 B2C
    }
}
```

**邏輯說明**:
- `allowed_audiences`: 白名單，該業務範圍允許的受眾
- `blocked_audiences`: 黑名單，明確排除的受眾（用於雙重檢查）
- 複合受眾（如「租客|管理師」）可以被多個業務範圍使用

#### 2.3 實施步驟

##### Step 1: 修改 VendorKnowledgeRetriever

**檔案**: `rag-orchestrator/services/vendor_knowledge_retriever.py`

**修改位置**: `retrieve_knowledge_hybrid()` 方法

**新增邏輯**:
```python
def retrieve_knowledge_hybrid(
    self,
    query: str,
    intent_id: int,
    vendor_id: int,
    top_k: int = 3,
    similarity_threshold: float = 0.6,
    resolve_templates: bool = True,
    all_intent_ids: Optional[List[int]] = None
) -> List[Dict]:
    # 1. 獲取 vendor 的 business_scope_name
    vendor_info = self.param_resolver.get_vendor_info(vendor_id)
    business_scope_name = vendor_info.get('business_scope_name', 'external')

    # 2. 映射到允許的 audience 列表
    BUSINESS_SCOPE_AUDIENCE_MAPPING = {
        'external': ['租客', '房東', '租客|管理師', '房東|租客', '房東|租客|管理師', 'tenant', 'general'],
        'internal': ['管理師', '系統管理員', '租客|管理師', '房東|租客|管理師', '房東/管理師', 'general']
    }

    allowed_audiences = BUSINESS_SCOPE_AUDIENCE_MAPPING.get(business_scope_name, ['general'])

    # 3. 在 SQL WHERE 子句中添加 audience 過濾
    cursor.execute("""
        SELECT ...
        FROM knowledge_base kb
        LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
        WHERE
            -- 現有過濾條件
            (...)
            -- ✅ 新增：Audience 過濾（基於業務範圍）
            AND (
                kb.audience IS NULL  -- 允許沒有標記受眾的知識
                OR kb.audience = ANY(%s::text[])  -- 允許的受眾列表
            )
        ORDER BY ...
    """, (..., allowed_audiences, ...))
```

**優點**:
- ✅ 快速實施（利用現有欄位）
- ✅ 不需要修改資料庫結構
- ✅ 邏輯清晰，易於理解

**缺點**:
- ⚠️ audience 值不統一（中英文混用、分隔符不一致）
- ⚠️ 需要維護映射表

##### Step 2: 修改 RAG Engine

**檔案**: `rag-orchestrator/services/rag_engine.py`

**挑戰**: RAG Engine 目前不接收 `vendor_id` 參數

**解決方案**: 新增 `allowed_audiences` 可選參數

```python
async def search(
    self,
    query: str,
    limit: int = None,
    similarity_threshold: float = 0.6,
    intent_ids: Optional[List[int]] = None,
    primary_intent_id: Optional[int] = None,
    allowed_audiences: Optional[List[str]] = None  # ✅ 新增參數
) -> List[Dict]:
    """
    搜尋相關知識（支援多意圖過濾與加成）

    Args:
        ...
        allowed_audiences: 允許的受眾列表（用於業務範圍過濾）
    """
    async with self.db_pool.acquire() as conn:
        # 構建 WHERE 子句
        where_clauses = [
            "kb.embedding IS NOT NULL",
            "(1 - (kb.embedding <=> $1::vector)) >= $2"
        ]

        params = [vector_str, similarity_threshold, limit * 2, primary_intent_id, intent_ids]
        param_idx = 6  # 下一個參數索引

        # ✅ 新增：Audience 過濾
        if allowed_audiences:
            where_clauses.append(
                f"(kb.audience IS NULL OR kb.audience = ANY(${param_idx}::text[]))"
            )
            params.insert(param_idx - 1, allowed_audiences)

        where_sql = " AND ".join(where_clauses)

        results = await conn.fetch(f"""
            SELECT DISTINCT ON (kb.id) ...
            FROM knowledge_base kb
            LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
            WHERE {where_sql}
            ORDER BY ...
        """, *params)
```

**呼叫端修改**:

**檔案**: `rag-orchestrator/routers/chat.py`

```python
# /message 端點 (Line 461)
if intent_result['intent_name'] == 'unclear':
    # 獲取 vendor 業務範圍
    vendor_info = resolver.get_vendor_info(request.vendor_id)
    business_scope_name = vendor_info.get('business_scope_name', 'external')

    # 映射到允許的受眾
    allowed_audiences = get_allowed_audiences_for_scope(business_scope_name)

    # RAG 檢索時傳入 allowed_audiences
    rag_results = await rag_engine.search(
        query=request.message,
        limit=5,
        similarity_threshold=0.55,
        allowed_audiences=allowed_audiences  # ✅ 新增參數
    )
```

##### Step 3: 創建輔助函數

**檔案**: 新建 `rag-orchestrator/services/business_scope_utils.py`

```python
"""
業務範圍工具函數
提供業務範圍與受眾的映射邏輯
"""
from typing import List

# 業務範圍與受眾映射表
BUSINESS_SCOPE_AUDIENCE_MAPPING = {
    'external': {
        'allowed_audiences': [
            '租客', '房東', '租客|管理師', '房東|租客',
            '房東|租客|管理師', 'tenant', 'general'
        ],
        'description': 'B2C 包租代管服務（租客、房東）'
    },
    'internal': {
        'allowed_audiences': [
            '管理師', '系統管理員', '租客|管理師',
            '房東|租客|管理師', '房東/管理師', 'general'
        ],
        'description': 'B2B 系統商內部管理'
    }
}

def get_allowed_audiences_for_scope(business_scope_name: str) -> List[str]:
    """
    根據業務範圍名稱獲取允許的受眾列表

    Args:
        business_scope_name: 業務範圍名稱 (external/internal)

    Returns:
        允許的受眾列表
    """
    mapping = BUSINESS_SCOPE_AUDIENCE_MAPPING.get(
        business_scope_name,
        BUSINESS_SCOPE_AUDIENCE_MAPPING['external']  # 預設 B2C
    )
    return mapping['allowed_audiences']

def is_audience_allowed_for_scope(
    audience: str,
    business_scope_name: str
) -> bool:
    """
    判斷受眾是否屬於業務範圍

    Args:
        audience: 受眾名稱
        business_scope_name: 業務範圍名稱

    Returns:
        是否允許
    """
    if not audience:
        return True  # NULL audience 視為通用

    allowed = get_allowed_audiences_for_scope(business_scope_name)
    return audience in allowed
```

#### 2.4 測試計劃

##### 測試案例 1: B2C 不應該看到 B2B 知識

```bash
# Vendor 1 (external/B2C) 問 B2B 管理問題
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "如何設定用戶權限？",
    "vendor_id": 1,
    "mode": "tenant"
  }'
```

**預期結果**:
- ❌ 不檢索到任何「管理師」或「系統管理員」audience 的知識
- ✅ 返回兜底回應或觸發意圖建議引擎

##### 測試案例 2: B2B 不應該看到 B2C 租客知識

```bash
# Vendor 2 (internal/B2B) 問 B2C 租客問題
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "如何報修冷氣？",
    "vendor_id": 2,
    "mode": "customer_service"
  }'
```

**預期結果**:
- ❌ 不檢索到「租客」或「房東」audience 的知識
- ✅ 返回兜底回應

##### 測試案例 3: 驗證 general audience 對所有範圍開放

```bash
# 檢查 general audience 的知識
# 應該對所有 vendor 開放
```

#### 2.5 實施時間估計

| 任務 | 預估時間 | 優先級 |
|------|---------|--------|
| 創建 business_scope_utils.py | 30 分鐘 | P0 |
| 修改 VendorKnowledgeRetriever | 1 小時 | P0 |
| 修改 RAG Engine | 1 小時 | P0 |
| 修改 chat.py 呼叫端 | 30 分鐘 | P0 |
| 測試與驗證 | 1 小時 | P0 |
| **總計** | **4 小時** | |

---

### 方案 B: 新增 `business_scope_name` 欄位到 knowledge_base（長期方案）

#### 2.1 方案概述

在 `knowledge_base` 表新增 `business_scope_name` 欄位，直接標記知識屬於哪個業務範圍。

#### 2.2 資料庫 Schema 修改

```sql
-- 新增欄位
ALTER TABLE knowledge_base
ADD COLUMN business_scope_name VARCHAR(100) REFERENCES business_scope_config(scope_name);

-- 建立索引
CREATE INDEX idx_knowledge_business_scope ON knowledge_base(business_scope_name);

-- 設定預設值（現有資料）
UPDATE knowledge_base
SET business_scope_name = CASE
    WHEN audience IN ('租客', '房東', '租客|管理師', 'tenant', 'general') THEN 'external'
    WHEN audience IN ('管理師', '系統管理員', '房東/管理師') THEN 'internal'
    ELSE 'external'  -- 預設為 external
END;
```

#### 2.3 檢索邏輯修改

```sql
-- VendorKnowledgeRetriever
WHERE
    -- Scope 過濾
    (...)
    -- ✅ Business Scope 過濾
    AND (
        kb.business_scope_name IS NULL  -- 通用知識
        OR kb.business_scope_name = (
            SELECT business_scope_name
            FROM vendors
            WHERE id = %s
        )
    )
```

#### 2.4 優缺點

**優點**:
- ✅ 明確的業務範圍標記
- ✅ 與 vendors 表的 business_scope_name 一致
- ✅ 支援未來擴展更多業務範圍
- ✅ 查詢效能更好（直接 JOIN）

**缺點**:
- ❌ 需要修改資料庫結構
- ❌ 需要數據遷移腳本
- ❌ 需要更新知識新增/編輯 UI
- ⏰ 實施時間較長（約 8-12 小時）

---

## 3. 推薦方案

### 3.1 短期（本周）: **方案 A - Audience 過濾**

**理由**:
1. ✅ 快速實施（4 小時）
2. ✅ 不需要修改資料庫結構
3. ✅ 可立即解決安全風險
4. ✅ 現有 audience 數據品質足夠

**實施順序**:
1. Day 1: 實施 VendorKnowledgeRetriever 過濾
2. Day 1: 實施 RAG Engine 過濾
3. Day 2: 測試與驗證
4. Day 2: 部署到生產環境

### 3.2 長期（下階段）: **方案 B - Business Scope 欄位**

**理由**:
1. ✅ 架構更清晰
2. ✅ 未來擴展性更好
3. ✅ 與整體 Multi-Vendor 架構一致

**實施時機**: Phase 2 或 Phase 3 後期

---

## 4. 風險與緩解措施

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| **Audience 值不統一** | 🟡 中 | 在映射表中窮舉所有變體 |
| **過濾過於嚴格** | 🟡 中 | 測試階段仔細驗證，允許 NULL audience |
| **效能影響** | 🟢 低 | audience 欄位已有索引 |
| **向後兼容性** | 🟢 低 | 參數為可選，預設不過濾 |

---

## 5. 後續優化建議

### 5.1 Audience 欄位標準化

**問題**: 當前 audience 值不統一
- 中英文混用：`租客` vs `tenant`
- 分隔符不一致：`租客|管理師` vs `房東/管理師`

**建議**: 標準化為英文 + 分隔符統一

```sql
-- Migration script
UPDATE knowledge_base
SET audience = CASE
    WHEN audience = '租客' THEN 'tenant'
    WHEN audience = '房東' THEN 'landlord'
    WHEN audience = '管理師' THEN 'property_manager'
    WHEN audience = '系統管理員' THEN 'system_admin'
    WHEN audience = '租客|管理師' THEN 'tenant,property_manager'
    WHEN audience = '房東|租客' THEN 'landlord,tenant'
    WHEN audience = '房東|租客|管理師' THEN 'landlord,tenant,property_manager'
    WHEN audience = '房東/管理師' THEN 'landlord,property_manager'
    ELSE audience
END;
```

### 5.2 Knowledge 新增時自動標記 Business Scope

在知識新增/編輯介面自動根據 audience 推斷並設定 business_scope_name。

### 5.3 監控與告警

新增監控指標：
- 跨業務範圍知識檢索嘗試次數
- Audience 為 NULL 的知識數量
- 不在映射表中的 audience 值

---

## 6. 附錄：當前 Audience 分布詳情

```sql
SELECT
    audience,
    COUNT(*) as count,
    CASE
        WHEN audience IN ('租客', '房東', 'tenant', 'general') THEN 'B2C'
        WHEN audience IN ('管理師', '系統管理員') THEN 'B2B'
        WHEN audience LIKE '%管理師%' THEN 'B2B (mixed)'
        ELSE 'Unknown'
    END as suggested_scope
FROM knowledge_base
GROUP BY audience
ORDER BY count DESC;
```

| Audience | 數量 | 建議 Scope |
|----------|------|-----------|
| 租客 | 329 | B2C (external) |
| 管理師 | 105 | B2B (internal) |
| 房東 | 25 | B2C (external) |
| 租客\|管理師 | 2 | Mixed (allow both) |
| 房東\|租客\|管理師 | 1 | Mixed (allow both) |
| general | 1 | Universal (allow all) |
| tenant | 1 | B2C (external) |
| 房東\|租客 | 1 | B2C (external) |
| 房東/管理師 | 1 | Mixed (allow both) |
| 系統管理員 | 1 | B2B (internal) |

---

**產生時間**: 2025-10-12T04:55:00Z
**作者**: Claude Code
**版本**: v1.0
