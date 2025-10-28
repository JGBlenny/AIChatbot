# Audience 欄位價值評估報告

## 🤔 問題：這個欄位真的需要嗎？

## 一、當前設計分析

### 1.1 設計意圖
- **目標**: B2B/B2C 隔離 + 角色權限控制
- **實現**: 透過 audience 欄位 + user_role 參數 + 映射邏輯

### 1.2 實際使用情況
```
數據統計 (480 筆知識):
- 租客:    332 筆 (69%)  ← B2C
- 管理師:  105 筆 (22%)  ← B2B
- 房東:     25 筆 (5%)   ← B2C
- 其他:     18 筆 (4%)
```

### 1.3 複雜度成本
```
維護成本:
- audience 欄位本身
- audience_config 表（10筆配置）
- FALLBACK_AUDIENCE_MAPPING 硬編碼
- get_allowed_audiences_for_scope() 函數
- 前端下拉選單 + 提示文字
- SQL 查詢額外的 AND 條件
```

## 二、功能重疊分析

### 2.1 與 user_role 的重疊

**user_role 已經區分了 B2C/B2B**:
```python
user_role = "customer"  →  B2C 終端用戶
user_role = "staff"     →  B2B 內部員工
```

**audience 的細分**:
```python
audience = "租客"    → B2C 的子類別
audience = "房東"    → B2C 的子類別
audience = "管理師"  → B2B 的子類別
```

**問題**: user_role 已經能做 B2C/B2B 隔離，audience 真的需要更細的分類嗎？

### 2.2 與 category/intent 的重疊

**category 已有分類**:
- "租金與費用" (租客相關)
- "房東指南" (房東相關)
- "系統操作" (管理師相關)

**intent 已有意圖分類**:
- 每個知識都有 intent_id
- 可以用 intent 區分不同對象的問題

**問題**: 為什麼不直接用 category + intent 來區分知識類型？

## 三、實際業務場景驗證

### 場景 1: 租客使用 AI 客服
```
用戶: 租客 A
問題: "租金怎麼繳？"

當前機制:
  user_role = "customer"
  → allowed_audiences = ['租客', '房東', ...]
  → 可以看到 332 筆租客知識 + 25 筆房東知識

問題:
  ❓ 租客為什麼能看到房東知識？
  ❓ 如果租客不該看到房東知識，為什麼 allowed_audiences 包含 '房東'？
  ❓ 如果可以看到，那隔離的意義是什麼？
```

### 場景 2: 管理師使用內部系統
```
用戶: 管理師 B
問題: "如何新增租客？"

當前機制:
  user_role = "staff"
  → allowed_audiences = ['管理師', '系統管理員', ...]
  → 可以看到 105 筆管理師知識

替代方案:
  user_role = "staff"
  → 直接查詢所有知識（或過濾 category = "內部管理"）

問題:
  ❓ 用 user_role + category 組合不是更簡單嗎？
```

### 場景 3: 租客和房東的隔離
```
實際問題:
  ❓ 租客和房東是在同一個入口嗎？
  ❓ 還是有兩個不同的 URL/系統？

如果是分開的入口:
  → 用 vendor_id 或 URL 就能隔離
  → audience 沒有必要

如果是同一個入口:
  → 租客和房東的知識真的不能互看嗎？
  → 「房東如何收租」對租客真的是敏感資訊嗎？
```

## 四、問題點總結

### 4.1 配置混亂
```sql
-- audience_config 表的問題
SELECT business_scope, COUNT(*) FROM audience_config GROUP BY business_scope;

business_scope | count
---------------+-------
both           | 10    ← 所有對象都在 'both'，沒有區分 external/internal
```

**結論**: 配置表形同虛設，實際使用硬編碼

### 4.2 邏輯重複
```python
# 當前: 雙層判斷
if user_role == "customer":
    allowed_audiences = ['租客', '房東', ...]
    # SQL: WHERE audience IN (allowed_audiences)

# 簡化: 單層判斷
if user_role == "customer":
    # SQL: WHERE category NOT IN ('內部管理', ...)
```

### 4.3 混合對象的困境
```
當前有這些混合值:
- '租客|管理師'
- '房東|租客'
- '房東|租客|管理師'

問題:
  ❓ 如果知識需要多對象共享，是否說明分類本身不合理？
  ❓ 這種複雜組合是否說明需要標籤系統，而不是單一欄位？
```

## 五、替代方案

### 方案 A: 完全移除 audience，只用 user_role

```python
# 簡化後的查詢邏輯
if user_role == "customer":
    # B2C: 查詢所有非內部管理的知識
    WHERE category NOT IN ('內部管理', '系統操作')
elif user_role == "staff":
    # B2B: 查詢所有知識
    # 不需要任何過濾
```

**優點**:
- ✅ 簡化代碼和配置
- ✅ 減少維護成本
- ✅ 邏輯更清晰

**缺點**:
- ❌ 無法區分租客和房東（如果真的需要區分）

---

### 方案 B: 用 category 替代 audience

```python
# 設定 category
- "租客指南"
- "房東指南"
- "通用客服"
- "內部管理"

# 查詢邏輯
if user_role == "customer":
    WHERE category IN ('租客指南', '房東指南', '通用客服')
elif user_role == "staff":
    WHERE category IN ('內部管理', '通用客服')
```

**優點**:
- ✅ 利用現有欄位
- ✅ 語義更明確
- ✅ 與知識分類對齊

**缺點**:
- ❌ 需要重新分類現有知識

---

### 方案 C: 簡化 audience 為布林值

```python
# 簡化為單一布林值
is_internal BOOLEAN  -- TRUE = 內部管理知識, FALSE/NULL = 客戶可見

# 查詢邏輯
if user_role == "customer":
    WHERE (is_internal = FALSE OR is_internal IS NULL)
elif user_role == "staff":
    # 查詢所有知識
```

**優點**:
- ✅ 極簡設計
- ✅ 足夠滿足 B2C/B2B 隔離需求
- ✅ 沒有配置維護成本

**缺點**:
- ❌ 無法區分租客/房東/管理師

---

### 方案 D: 改用標籤系統

```python
# 利用現有 keywords 欄位
keywords = ['租客', '租金', '繳費']

# 查詢邏輯
if user_role == "customer":
    WHERE NOT ('內部' = ANY(keywords))
elif user_role == "staff":
    # 查詢所有知識
```

**優點**:
- ✅ 靈活性最高
- ✅ 支援多標籤
- ✅ 利用現有欄位

**缺點**:
- ❌ keywords 主要用於檢索，混用可能造成混淆

## 六、成本效益分析

### 當前方案 (保留 audience)
```
成本: ████████░░ (8/10)
- 資料庫欄位
- 配置表維護
- 映射邏輯
- 前端表單
- 文檔培訓

效益: ███░░░░░░░ (3/10)
- 租客/房東隔離（價值存疑）
- B2C/B2B 隔離（user_role 已能做到）
```

### 方案 A (移除 audience)
```
成本: ██░░░░░░░░ (2/10)
- 修改代碼移除相關邏輯
- 更新文檔

效益: ████████░░ (8/10)
- 簡化系統
- 減少維護成本
- 邏輯更清晰
```

### 方案 C (簡化為布林值)
```
成本: ████░░░░░░ (4/10)
- 修改欄位結構
- 遷移現有數據
- 更新代碼

效益: ███████░░░ (7/10)
- 保留 B2C/B2B 隔離
- 大幅簡化邏輯
- 減少配置複雜度
```

## 七、數據驅動的洞察

### 7.1 實際隔離效果
```bash
# 測試 B2C 用戶能看到的知識
External (B2C) 允許的受眾:
  ✓ 租客         (332筆)
  ✓ 房東         (25筆)
  ✓ tenant       (11筆)
  ✓ 租客|管理師  (2筆)
  ✓ 房東|租客    (1筆)
  ✓ 房東|租客|管理師 (1筆)

總計: 372筆 (77%)
```

**結論**: B2C 用戶能看到 77% 的知識，B2C/B2B 隔離有在運作

### 7.2 租客和房東是否隔離？
```
當前設計: 租客能看到房東知識，房東能看到租客知識
allowed_audiences (external) = ['租客', '房東', ...]

實際情況:
- 租客 332筆 + 房東 25筆 = 兩者都能互看

問題: 既然互看，為什麼要分開標記？
```

## 八、關鍵問題清單

在決定是否保留 audience 之前，需要回答：

1. **業務模式問題**:
   - [ ] 租客和房東是在同一個入口嗎？
   - [ ] 租客真的不該看到房東知識嗎？
   - [ ] 有哪些知識是「租客專屬但房東不能看」的？

2. **隔離需求問題**:
   - [ ] B2C/B2B 隔離用 user_role 是否足夠？
   - [ ] 是否有更細粒度的權限需求？
   - [ ] 未來是否會有更多角色（如仲介、清潔人員）？

3. **維護成本問題**:
   - [ ] 團隊是否有精力維護複雜的映射邏輯？
   - [ ] 新增知識時，如何決定 audience 值？
   - [ ] 是否經常發生「知識該給誰看」的困惑？

## 九、建議

### 短期建議（立即可做）
```sql
-- 1. 統一 'general' 為 NULL
UPDATE knowledge_base SET audience = NULL WHERE audience = 'general';

-- 2. 驗證實際需求
SELECT
    audience,
    COUNT(*) as count,
    STRING_AGG(DISTINCT category, ', ') as categories
FROM knowledge_base
GROUP BY audience
ORDER BY count DESC;

-- 看看每個 audience 的知識是否真的有明確區分
```

### 中期建議（需驗證需求）

**如果確認需要細粒度隔離**:
- 保留 audience，但簡化配置（移除 audience_config 表，只用硬編碼）
- 清理混合對象（如 '租客|管理師'），改用更明確的分類

**如果只需要 B2C/B2B 隔離**:
- 方案 C: 改為 is_internal 布林值
- 移除所有映射邏輯

**如果連 B2C/B2B 隔離都不需要**:
- 方案 A: 完全移除 audience

### 長期建議（架構優化）

考慮引入 RBAC (Role-Based Access Control):
```python
roles:
  - tenant (租客)
  - landlord (房東)
  - property_manager (管理師)
  - admin (系統管理員)

permissions:
  - view_tenant_knowledge
  - view_landlord_knowledge
  - view_internal_knowledge

role_permissions:
  tenant: [view_tenant_knowledge]
  landlord: [view_landlord_knowledge]
  property_manager: [view_internal_knowledge]
  admin: [view_tenant_knowledge, view_landlord_knowledge, view_internal_knowledge]
```

## 十、評估結論

### ❌ 當前設計的問題
1. **過度設計**: audience 提供了細粒度隔離，但實際需求不明確
2. **配置混亂**: audience_config 表沒有正確配置，實際使用硬編碼
3. **邏輯重疊**: user_role 已經能做 B2C/B2B 隔離
4. **維護成本高**: 複雜的映射邏輯、前端表單、文檔維護

### ✅ 可能的價值
1. **如果租客和房東需要嚴格隔離**: audience 有其價值
2. **如果未來有更多角色**: audience 提供了擴展性
3. **如果需要審計追蹤**: 明確記錄每個知識的對象

### 🎯 最終建議

**我傾向於方案 C (簡化為布林值)**:

```sql
-- 遷移腳本
ALTER TABLE knowledge_base ADD COLUMN is_internal BOOLEAN DEFAULT FALSE;

UPDATE knowledge_base
SET is_internal = TRUE
WHERE audience IN ('管理師', '系統管理員', '房東/管理師');

UPDATE knowledge_base
SET is_internal = FALSE
WHERE audience IN ('租客', '房東', 'tenant', '房東|租客');

-- 混合對象保持 FALSE（客戶可見）
UPDATE knowledge_base
SET is_internal = FALSE
WHERE audience LIKE '%|%' AND audience NOT LIKE '%管理師%';

-- 然後移除 audience 欄位
ALTER TABLE knowledge_base DROP COLUMN audience;
```

**理由**:
- ✅ 保留 B2C/B2B 隔離（這是實際需求）
- ✅ 大幅簡化代碼和配置
- ✅ 足夠滿足當前業務需求
- ✅ 如果未來需要更細粒度，再擴展也不遲

**投資回報比**: ⭐⭐⭐⭐⭐ (5/5)
- 開發成本: 低（1-2小時）
- 維護成本: 低（幾乎為零）
- 業務價值: 高（保留核心隔離）
- 代碼簡潔度: 高（移除大量邏輯）

---

## 最後的問題

**你的系統真的需要區分「租客」和「房東」嗎？**

如果答案是「不需要」或「不確定」，那 audience 確實「用途不大」。
