# Audience 欄位盤查總結

## 核心作用

**audience 欄位用於 B2B/B2C 業務隔離和角色權限控制**

## 實際數據分佈

```
當前資料庫統計（480 筆知識）:
- 租客: 332 筆 (69%)
- 管理師: 105 筆 (22%)
- 房東: 25 筆 (5%)
- tenant: 11 筆
- general: 2 筆（舊設計，應改為 NULL）
- NULL: 0 筆（未來通用知識應使用 NULL）
- 混合對象: 4 筆（如 租客|管理師）
```

## 過濾規則

### B2C (user_role = "customer")
**可見的 audience 值**:
- ✅ `NULL` (通用)
- ✅ `租客`
- ✅ `房東`
- ✅ `tenant`
- ✅ `general`
- ✅ `租客|管理師` (混合)
- ✅ `房東|租客` (混合)
- ✅ `房東|租客|管理師` (混合)
- ❌ `管理師` (B2B 專用)
- ❌ `系統管理員` (B2B 專用)

### B2B (user_role = "staff")
**可見的 audience 值**:
- ✅ `NULL` (通用)
- ✅ `管理師`
- ✅ `系統管理員`
- ✅ `general`
- ✅ `租客|管理師` (混合)
- ✅ `房東|租客|管理師` (混合)
- ✅ `房東/管理師` (混合)
- ❌ `租客` (B2C 專用)
- ❌ `房東` (B2C 專用)
- ❌ `tenant` (B2C 專用)

## SQL 過濾邏輯

```sql
WHERE
    -- 其他條件...
    AND (
        allowed_audiences IS NULL          -- 不過濾（測試/回測模式）
        OR kb.audience IS NULL             -- 通用知識（所有人可見）
        OR kb.audience = ANY(allowed_audiences)  -- 在允許列表中
    )
```

## 實例說明

### 場景 1: 租客問「租金怎麼繳？」
```
請求參數:
  user_role = "customer"

系統處理:
  business_scope = "external"
  allowed_audiences = ['租客', '房東', 'tenant', 'general', ...]

可檢索知識:
  ✅ audience = NULL (通用)
  ✅ audience = '租客' (332筆)
  ✅ audience = '房東' (25筆)
  ❌ audience = '管理師' (105筆，B2B專用)
```

### 場景 2: 管理師查詢內部流程
```
請求參數:
  user_role = "staff"

系統處理:
  business_scope = "internal"
  allowed_audiences = ['管理師', '系統管理員', 'general', ...]

可檢索知識:
  ✅ audience = NULL (通用)
  ✅ audience = '管理師' (105筆)
  ✅ audience = '系統管理員'
  ❌ audience = '租客' (332筆，B2C專用)
  ❌ audience = '房東' (25筆，B2C專用)
```

## 關鍵發現

### 1. 數據庫配置 vs 硬編碼
- **audience_config 表**: 所有值都在 'both' 範圍（實際沒起作用）
- **硬編碼 fallback**: 正確區分 external/internal（實際在用）
- **結論**: 目前系統使用硬編碼邏輯

### 2. 'general' vs NULL
- **設計意圖**: NULL = 通用知識
- **實際狀況**: 有 2 筆使用 'general'，0 筆使用 NULL
- **已修正**: 新代碼統一使用 NULL

### 3. 隔離效果
```
僅 B2C 可見: 租客, 房東, tenant, 房東|租客
僅 B2B 可見: 管理師, 系統管理員, 房東/管理師
雙方可見: general, 租客|管理師, 房東|租客|管理師, NULL
```

## 配置來源優先級

```
1. 嘗試從數據庫讀取 (audience_config 表)
2. 如果失敗，使用硬編碼 FALLBACK_AUDIENCE_MAPPING
3. 緩存 5 分鐘
```

## 與其他欄位的關係

| 欄位 | 作用 | 關係 |
|------|------|------|
| **audience** | 角色過濾（租客/房東/管理師） | 用戶角色 |
| **business_types** | 業態過濾（包租代管/系統商） | 業者類型 |
| **scope** | 範圍（全域/業者專屬） | 知識共享 |
| **vendor_id** | 業者隔離 | 多租戶 |

**組合邏輯**:
```
vendor_id (業者隔離)
  → scope (全域/專屬)
    → business_types (業態過濾)
      → audience (角色過濾)
```

## 安全性意義

**audience 欄位確保了業務隔離**:
1. 終端客戶（租客/房東）看不到內部管理知識
2. 管理師看不到純粹的客戶服務知識
3. 混合對象支援跨業務範圍的共享知識

**防止資訊洩漏**:
- 租客無法查詢到「管理師操作手冊」
- 管理師的內部流程不會暴露給客戶
- 價格策略等敏感資訊可限制在內部

## 未來優化建議

1. **統一 'general' 為 NULL**:
   ```sql
   UPDATE knowledge_base SET audience = NULL WHERE audience = 'general';
   ```

2. **修正 audience_config 配置**:
   - 將不同 audience 正確分配到 external/internal/both
   - 或刪除該表，完全使用硬編碼

3. **添加監控指標**:
   - B2C/B2B 知識分佈比例
   - audience = NULL 的知識數量
   - 異常 audience 值檢測

4. **文檔更新**:
   - 所有文檔明確說明 NULL = 通用
   - 新增知識時的對象選擇指南

## 結論

**audience 是系統安全的關鍵欄位**，它實現了：
- ✅ B2B/B2C 業務隔離
- ✅ 角色權限控制
- ✅ 靈活的可見性配置
- ✅ 防止敏感資訊洩漏

**現況**：運作正常，使用硬編碼配置，未來可考慮完全數據庫化配置。
