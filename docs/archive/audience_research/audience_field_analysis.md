# Audience 欄位完整盤查報告

## 1. 資料庫層面

### 1.1 表結構
```sql
-- knowledge_base 表
audience VARCHAR(50)  -- 可為 NULL
```

### 1.2 資料儲存
- **NULL**: 通用知識，所有業務範圍都可見
- **租客**: 只有租客可見
- **房東**: 只有房東可見
- **管理師**: 只有管理師可見
- **租客|管理師**: 租客和管理師都可見
- **房東|租客**: 房東和租客都可見
- **房東|租客|管理師**: 所有人都可見
- **系統管理員**: 系統管理員專用
- **房東/管理師**: 房東相關的內部管理

## 2. 業務邏輯層面

### 2.1 業務範圍映射 (business_scope_utils.py)

**External (B2C) - 終端用戶**:
```python
allowed_audiences = [
    '租客', '房東', 'tenant', 'general',
    '租客|管理師', '房東|租客', '房東|租客|管理師',
]
```

**Internal (B2B) - 內部管理**:
```python
allowed_audiences = [
    '管理師', '系統管理員', 'general',
    '租客|管理師', '房東|租客|管理師', '房東/管理師',
]
```

### 2.2 業務範圍與用戶角色關係

| user_role | business_scope | 可見 audience |
|-----------|----------------|--------------|
| customer  | external       | 租客, 房東, 租客\|管理師, 房東\|租客, 房東\|租客\|管理師, NULL |
| staff     | internal       | 管理師, 系統管理員, 租客\|管理師, 房東\|租客\|管理師, 房東/管理師, NULL |

## 3. 檢索過濾邏輯

### 3.1 RAG Engine (rag_engine.py)

```sql
WHERE
    -- 其他條件...
    AND (
        %s::text[] IS NULL                    -- 未提供 allowed_audiences，不過濾
        OR kb.audience IS NULL                -- NULL audience 視為通用
        OR kb.audience = ANY(%s::text[])      -- audience 在允許列表中
    )
```

### 3.2 Vendor Knowledge Retriever (vendor_knowledge_retriever.py)

```sql
-- ✅ Audience 過濾：B2B/B2C 隔離
AND (
    %s::text[] IS NULL           -- 未提供 allowed_audiences，不過濾
    OR kb.audience IS NULL       -- NULL audience 視為通用
    OR kb.audience = ANY(%s::text[])  -- audience 在允許列表中
)
```

## 4. API 調用流程

### 4.1 聊天 API (chat.py)

```python
from services.business_scope_utils import get_allowed_audiences_for_scope

# 根據用戶角色決定業務範圍
business_scope = "external" if request.user_role == "customer" else "internal"

# 獲取允許的受眾列表
allowed_audiences = get_allowed_audiences_for_scope(business_scope)

# 傳遞給 RAG 引擎
rag_results = await rag_engine.search(
    query=request.message,
    allowed_audiences=allowed_audiences,  # 這裡過濾
    vendor_id=request.vendor_id
)
```

### 4.2 流式聊天 API (chat_stream.py)

```python
from services.business_scope_utils import get_allowed_audiences_for_scope

business_scope = "external" if request.user_role == "customer" else "internal"
allowed_audiences = get_allowed_audiences_for_scope(business_scope)

# 傳遞給檢索器
results = await retriever.retrieve_knowledge_hybrid(
    question_embedding=embedding,
    vendor_id=request.vendor_id,
    allowed_audiences=allowed_audiences,
    user_role=request.user_role
)
```

## 5. 完整數據流

```
用戶請求
    ↓
[user_role: "customer" 或 "staff"]
    ↓
business_scope = "external" 或 "internal"
    ↓
get_allowed_audiences_for_scope(business_scope)
    ↓
allowed_audiences = ['租客', '房東', ...] 或 ['管理師', '系統管理員', ...]
    ↓
SQL 查詢過濾
    ↓
WHERE audience IS NULL OR audience = ANY(allowed_audiences)
    ↓
返回符合條件的知識
```

## 6. 典型場景

### 場景 1: B2C 租客查詢
```
user_role = "customer"
business_scope = "external"
allowed_audiences = ['租客', '房東', 'tenant', 'general', ...]

可檢索到的知識:
✅ audience = NULL (通用知識)
✅ audience = '租客'
✅ audience = '房東'
✅ audience = '租客|管理師'
✅ audience = '房東|租客'
✅ audience = '房東|租客|管理師'
❌ audience = '管理師' (B2B 專用)
❌ audience = '系統管理員' (B2B 專用)
```

### 場景 2: B2B 管理師查詢
```
user_role = "staff"
business_scope = "internal"
allowed_audiences = ['管理師', '系統管理員', 'general', ...]

可檢索到的知識:
✅ audience = NULL (通用知識)
✅ audience = '管理師'
✅ audience = '系統管理員'
✅ audience = '租客|管理師'
✅ audience = '房東|租客|管理師'
✅ audience = '房東/管理師'
❌ audience = '租客' (B2C 專用)
❌ audience = '房東' (B2C 專用)
```

### 場景 3: 回測/測試
```
allowed_audiences = None  # 不提供過濾

可檢索到的知識:
✅ 所有知識（不受 audience 限制）
```

## 7. 特殊值處理

### 7.1 NULL vs 空字符串
- `audience = NULL`: 通用知識，所有業務範圍可見
- `audience = ''`: 在前端視為 NULL，提交後存為 NULL

### 7.2 'general' 值
- **舊設計**: 使用 `'general'` 字符串
- **現設計**: 使用 `NULL`
- **相容性**: 資料庫映射中仍保留 `'general'` 在兩個業務範圍中

## 8. 配置來源

### 8.1 硬編碼 Fallback (business_scope_utils.py)
```python
FALLBACK_AUDIENCE_MAPPING = {
    'external': {...},
    'internal': {...}
}
```

### 8.2 數據庫動態配置 (audience_config 表)
```sql
SELECT business_scope, audience_value, display_name
FROM audience_config
WHERE is_enabled = TRUE
```

### 8.3 緩存機制
- 使用內存緩存 `_AUDIENCE_MAPPING_CACHE`
- 5 分鐘過期時間
- 如果資料庫讀取失敗，使用硬編碼 fallback

## 9. 前端使用

### 9.1 表單選擇
```vue
<select v-model="formData.audience">
  <option value="">通用（所有業務範圍）</option>
  <option value="租客">租客</option>
  <option value="房東">房東</option>
  ...
</select>
```

### 9.2 顯示
```vue
<td>{{ item.audience || '通用' }}</td>
```

### 9.3 API 配置端點
```
GET /rag-api/v1/audience-config/grouped
```
返回：
```json
{
  "external": [
    {"audience_value": "租客", "display_name": "租客", ...}
  ],
  "internal": [
    {"audience_value": "管理師", "display_name": "管理師", ...}
  ],
  "both": [
    {"audience_value": "general", "display_name": "所有人（通用）", ...}
  ]
}
```

## 10. 安全性與隔離

### 10.1 B2B/B2C 隔離
- **目的**: 防止終端客戶看到內部管理知識
- **實現**: 透過 `user_role` → `business_scope` → `allowed_audiences` 過濾
- **例子**: 租客無法看到「管理師」專用知識

### 10.2 跨業務範圍知識
- **混合對象**: `'租客|管理師'` 同時對 B2C 和 B2B 可見
- **用途**: 需要雙方都了解的知識（如流程說明）

## 11. 與其他欄位的關係

### 11.1 與 business_types 的差異
- **business_types**: 業態過濾（包租代管 vs 系統商）
- **audience**: 對象過濾（租客 vs 房東 vs 管理師）
- **組合使用**: 兩個維度獨立過濾

### 11.2 與 scope 的差異
- **scope**: 全域 (global) vs 業者專屬 (vendor)
- **audience**: 用戶角色過濾
- **關係**: scope 決定是否共享，audience 決定誰能看

### 11.3 與 vendor_id 的關係
- **vendor_id**: 業者隔離
- **audience**: 同一業者內的角色隔離
- **組合**: 先過濾業者，再過濾對象

## 12. 潛在問題與建議

### 12.1 已發現的問題
1. ✅ 'general' vs NULL 的混用（已統一為 NULL）
2. ✅ 前端對象下拉選單必填改為非必填（已修復）

### 12.2 優化建議
1. **考慮重構**: 將 audience 映射完全移到資料庫配置
2. **文檔更新**: 更新所有文檔說明 NULL = 通用
3. **測試覆蓋**: 確保所有 B2C/B2B 場景都有測試

### 12.3 未來擴展
- 如果需要更細粒度的權限控制，考慮引入 RBAC (Role-Based Access Control)
- 考慮將 audience 改為多對多關係（使用關聯表）

## 13. 核心結論

**audience 欄位的作用**:
1. **B2B/B2C 業務隔離**: 防止終端客戶看到內部管理知識
2. **角色權限控制**: 不同用戶角色看到不同的知識
3. **靈活的可見性**: 支援單一對象、多對象、通用三種模式
4. **業務範圍映射**: 透過配置表動態管理對象與業務範圍的關係

**簡單來說**:
- audience 決定「誰可以看到這個知識」
- 透過 user_role 和 business_scope 自動過濾
- NULL 值代表所有人都能看到（通用知識）
