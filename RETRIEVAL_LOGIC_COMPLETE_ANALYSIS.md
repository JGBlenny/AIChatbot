# 🔍 完整檢索邏輯分析

## 日期
2026-01-13

---

## 📋 目錄

1. [檢索流程總覽](#檢索流程總覽)
2. [各階段詳細分析](#各階段詳細分析)
3. [關鍵參數與閾值](#關鍵參數與閾值)
4. [意圖加成機制](#意圖加成機制)
5. [過濾與排序邏輯](#過濾與排序邏輯)
6. [邏輯問題分析](#邏輯問題分析)
7. [優化建議](#優化建議)

---

## 檢索流程總覽

```
用戶查詢: "你好，我要續約，新的合約甚麼時候會提供?"
    ↓
[階段 0] 預處理
    ├─ 意圖識別 → intent_id = 10 (租期／到期)
    ├─ 生成查詢 embedding → query_embedding
    ├─ 決定業態過濾策略 (B2B/B2C)
    └─ 決定用戶角色過濾策略
    ↓
[階段 1] SQL 候選檢索
    ├─ 計算 sql_threshold = 0.55 / 1.3 = 0.423
    ├─ WHERE base_similarity >= 0.423
    ├─ WHERE scope 過濾 (vendor/global)
    ├─ WHERE business_types 過濾
    ├─ WHERE target_user 過濾
    ├─ ORDER BY scope_weight, sql_boosted_similarity, priority
    ├─ LIMIT top_k * 3 (獲取候選集)
    └─ LEFT JOIN knowledge_intent_mapping
    ↓
    返回候選集 (可能包含多意圖重複)
    ↓
[階段 2] Python 語義加成與過濾
    ├─ For each candidate:
    │   ├─ 計算語義 boost (1.0 - 1.3x)
    │   ├─ boosted_similarity = base_similarity × boost
    │   └─ IF boosted_similarity < 0.55: 丟棄 ❌
    │
    └─ 保留所有通過閾值的候選
    ↓
[階段 3] 重新排序與去重
    ├─ 排序: scope_weight > boosted_similarity > priority
    ├─ 去重: 每個知識只保留最高分版本
    └─ 取前 top_k 個
    ↓
返回最終結果
```

---

## 各階段詳細分析

### 階段 0: 預處理

**代碼位置**: `vendor_knowledge_retriever.py:190-224`

#### 業態類型過濾策略

| 用戶角色 | 業態類型 | SQL 過濾邏輯 |
|---------|---------|-------------|
| property_manager, system_admin (B2B) | `['system_provider']` | `kb.business_types && ARRAY['system_provider']` (嚴格) |
| tenant, landlord (B2C) | 業者的 business_types | `kb.business_types IS NULL OR kb.business_types && vendor_types` (寬鬆) |

**設計意圖**：
- B2B：只顯示系統商專用知識
- B2C：顯示通用知識或業者業態匹配的知識

#### 目標用戶過濾策略

```python
target_user_filter_sql = "(kb.target_user IS NULL OR kb.target_user && ARRAY[target_user])"
```

**邏輯**：
- 知識沒有指定 target_user → 通用知識，顯示給所有人
- 知識有指定 target_user → 只顯示給對應角色

---

### 階段 1: SQL 候選檢索

**代碼位置**: `vendor_knowledge_retriever.py:253-355`

#### 1.1 SQL 閾值計算

```python
sql_threshold = similarity_threshold / 1.3 if use_semantic_boost else similarity_threshold
# 默認: 0.55 / 1.3 = 0.423
```

**設計邏輯**：
- `similarity_threshold` = 0.55 (Python 階段的最終閾值)
- 除以 1.3 (最大 boost) 得到 SQL 閾值
- **目的**：讓 SQL 返回更多候選，包括那些需要意圖加成才能達到閾值的知識

**案例**：
```
知識 A: base_similarity = 0.45
- SQL 階段: 0.45 >= 0.423 ✓ 通過
- 如果意圖匹配 (boost 1.3): 0.45 × 1.3 = 0.585 >= 0.55 ✓
- 如果意圖不匹配 (boost 1.0): 0.45 × 1.0 = 0.45 < 0.55 ✗
```

#### 1.2 SQL 查詢結構

```sql
SELECT
    kb.*,
    kim.intent_id,
    kim.intent_type,
    1 - (kb.embedding <=> query_vector) as base_similarity,

    -- SQL 臨時計算的 boost (會被 Python 覆蓋)
    CASE
        WHEN kim.intent_id = primary_intent THEN 1.3
        WHEN kim.intent_id = ANY(all_intents) THEN 1.1
        ELSE 1.0
    END as sql_intent_boost,

    -- Scope 權重
    CASE
        WHEN scope = 'customized' AND vendor_id = ? THEN 1000
        WHEN scope = 'vendor' AND vendor_id = ? THEN 500
        WHEN scope = 'global' AND vendor_id IS NULL THEN 100
        ELSE 0
    END as scope_weight

FROM knowledge_base kb
LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
WHERE
    (kb.vendor_id = ? OR kb.vendor_id IS NULL)  -- Scope 過濾
    AND kb.embedding IS NOT NULL                 -- 必須有 embedding
    AND base_similarity >= sql_threshold         -- 0.423
    AND business_type_filter                     -- 業態過濾
    AND target_user_filter                       -- 角色過濾
ORDER BY
    scope_weight DESC,
    sql_boosted_similarity DESC,
    kb.priority DESC
LIMIT top_k * 3  -- 獲取更多候選
```

#### 1.3 LEFT JOIN 的影響

**重要**：如果一個知識有多個意圖映射，LEFT JOIN 會產生多行！

**案例**：
```
知識 ID 100:
- 主要意圖: intent_id = 10 (租期／到期)
- 次要意圖: intent_id = 13 (續約流程)

SQL 返回 2 行：
Row 1: id=100, intent_id=10, intent_type='primary'
Row 2: id=100, intent_id=13, intent_type='secondary'
```

**影響**：
- 同一知識會被計算多次 boost
- 去重邏輯會保留最高分版本

---

### 階段 2: Python 語義加成與過濾

**代碼位置**: `vendor_knowledge_retriever.py:365-413`

#### 2.1 語義 Boost 計算

**使用語義匹配器** (`intent_semantic_matcher.py:104-171`):

```python
if use_semantic_boost and knowledge_intent_id:
    boost, reason, similarity = intent_matcher.calculate_semantic_boost(
        query_intent_id,
        knowledge_intent_id,
        knowledge_intent_type
    )
```

**計算邏輯**：

| 情況 | Boost | 說明 |
|------|-------|------|
| **精確匹配** | | |
| query_intent == knowledge_intent (primary) | 1.3 | 主要意圖精確匹配 |
| query_intent == knowledge_intent (secondary) | 1.15 | 次要意圖精確匹配 |
| **語義匹配** (需要 intent embedding) | | |
| 意圖 embedding 相似度 >= 0.85 | 1.3 | 高度語義相關 |
| 意圖 embedding 相似度 >= 0.70 | 1.2 | 強語義相關 |
| 意圖 embedding 相似度 >= 0.55 | 1.1 | 中度語義相關 |
| 意圖 embedding 相似度 >= 0.40 | 1.05 | 弱語義相關 |
| 意圖 embedding 相似度 < 0.40 | 1.0 | 語義不相關 |
| **沒有 embedding** | 1.0 | 無法計算語義，默認無加成 |

#### 2.2 過濾邏輯（❗問題所在）

```python
base_similarity = knowledge['base_similarity']
boosted_similarity = base_similarity * boost

# ❗關鍵過濾點
if boosted_similarity < similarity_threshold:  # 0.55
    filtered_count += 1
    continue  # 被過濾掉
```

**這就是問題的根源**：使用 `boosted_similarity` 而非 `base_similarity` 進行過濾！

---

### 階段 3: 重新排序與去重

**代碼位置**: `vendor_knowledge_retriever.py:415-440`

#### 3.1 排序邏輯

```python
candidates.sort(
    key=lambda x: (
        -x['scope_weight'],           # 1st: 1000 > 500 > 100
        -x['boosted_similarity'],     # 2nd: 高到低
        -x.get('priority', 0)         # 3rd: 高到低
    )
)
```

**排序優先級**：
1. **Scope 權重** (最高優先級)
   - customized: 1000
   - vendor: 500
   - global: 100

2. **加成後相似度** (第二優先級)
   - 向量相似度 × 意圖加成

3. **人工優先級** (第三優先級)
   - 由管理員設定的 priority 欄位

#### 3.2 去重邏輯

```python
seen_ids = set()
unique_candidates = []

for candidate in candidates:
    knowledge_id = candidate['id']
    if knowledge_id not in seen_ids:
        seen_ids.add(knowledge_id)
        unique_candidates.append(candidate)
    else:
        duplicates_removed += 1
```

**邏輯**：
- 因為 LEFT JOIN，同一知識可能有多個意圖映射
- 去重邏輯保留**第一個出現**的版本（排序後的最高分版本）

**案例**：
```
候選集（排序後）：
1. ID 100, intent_id=10, boosted_similarity=0.78  ← 保留
2. ID 100, intent_id=13, boosted_similarity=0.69  ← 丟棄（重複）
3. ID 200, intent_id=10, boosted_similarity=0.65  ← 保留
```

---

## 關鍵參數與閾值

### 默認配置

| 參數 | 默認值 | 來源 | 說明 |
|------|--------|------|------|
| `similarity_threshold` | 0.55 | `chat.py:944` | Python 階段最終閾值 |
| `sql_threshold` | 0.423 | 計算得出 | SQL 階段初始閾值 (0.55/1.3) |
| `top_k` | 3 | 請求參數 | 返回知識數量 |
| `candidate_limit` | 9 | 計算得出 | SQL 候選數量 (top_k×3) |
| `use_semantic_boost` | True | 默認 | 是否使用語義匹配器 |

### 意圖加成範圍

| 加成類型 | Boost 範圍 | 條件 |
|---------|-----------|------|
| 精確匹配 (primary) | 1.3 | query_intent == knowledge_intent |
| 精確匹配 (secondary) | 1.15 | query_intent == knowledge_intent |
| 高度語義相關 | 1.3 | intent embedding 相似度 >= 0.85 |
| 強語義相關 | 1.2 | intent embedding 相似度 >= 0.70 |
| 中度語義相關 | 1.1 | intent embedding 相似度 >= 0.55 |
| 弱語義相關 | 1.05 | intent embedding 相似度 >= 0.40 |
| 無相關 | 1.0 | 其他情況 |

### Scope 權重

| Scope | 權重 | 說明 |
|-------|------|------|
| customized | 1000 | 業者客製化知識（最高優先級） |
| vendor | 500 | 業者通用知識 |
| global | 100 | 全域通用知識 |

---

## 意圖加成機制

### 設計目標

**引用代碼註釋** (`vendor_knowledge_retriever.py:243-251`):

```python
# ✅ 方案5：意圖作為軟過濾器
# - 移除硬性意圖過濾，所有知識都參與檢索
# - intent_boost 先用簡單邏輯（精確匹配 1.3，其他 1.0）
# - 後續在 Python 中使用語義匹配器重新計算 boost（方案2）

# ✅ 方案2：語義化意圖匹配（在 Python 中實現）
# - SQL 查詢使用較低閾值（考慮最大 boost 1.3x）
# - Python 中使用語義相似度重新計算 boost
# - 加成後過濾 >= similarity_threshold
# - 重新排序後取 top_k
```

### 實際效果

雖然註釋說「意圖作為軟過濾器」，但實際上：

**SQL 階段** (✓ 軟過濾):
```sql
-- ✅ 移除了硬性意圖過濾
-- 之前：AND (kim.intent_id = ANY(intent_ids) OR kim.intent_id IS NULL)
-- 現在：所有知識都參與
```

**Python 階段** (❌ 仍然硬過濾):
```python
# ❌ 仍然使用 boosted_similarity 過濾
if boosted_similarity < similarity_threshold:
    continue  # 意圖影響過濾決策
```

---

## 過濾與排序邏輯

### 過濾階段

| 階段 | 過濾條件 | 閾值 | 意圖影響? |
|------|---------|------|----------|
| **SQL** | base_similarity >= sql_threshold | 0.423 | ❌ 無 |
| **SQL** | scope 過濾 | - | ❌ 無 |
| **SQL** | business_types 過濾 | - | ❌ 無 |
| **SQL** | target_user 過濾 | - | ❌ 無 |
| **Python** | boosted_similarity >= threshold | 0.55 | ✅ **有** |

### 排序階段

| 階段 | 排序依據 | 意圖影響? |
|------|---------|----------|
| **SQL** | scope_weight > sql_boosted_similarity > priority | ✅ 有 (臨時) |
| **Python** | scope_weight > boosted_similarity > priority | ✅ 有 (最終) |

---

## 邏輯問題分析

### 問題 1: 「意圖依賴區間」的存在

#### 問題描述

**雙閾值設計創造了「意圖依賴區間」**：

```
[0.423, 0.55) = 意圖依賴區間
```

在這個區間內的知識：
- **必須**有意圖匹配 (boost >= 1.18) 才能通過 Python 過濾
- 沒有意圖匹配 (boost = 1.0) 則被過濾

#### 數學證明

```
已知：
- sql_threshold = 0.423
- python_threshold = 0.55
- boosted_similarity = base_similarity × boost

要通過 Python 過濾：
boosted_similarity >= 0.55
base_similarity × boost >= 0.55
boost >= 0.55 / base_similarity

當 base_similarity = 0.45 時：
boost >= 0.55 / 0.45 = 1.22

結論：base_similarity 在 [0.423, 0.55) 的知識，
需要 boost >= 1.22 才能通過（只有精確匹配或高度語義相關才能達到）
```

#### 實際案例

| base_similarity | boost | boosted_similarity | SQL 階段 | Python 階段 |
|-----------------|-------|-------------------|---------|------------|
| 0.45 | 1.3 (匹配) | 0.585 | ✅ 通過 | ✅ 通過 |
| 0.45 | 1.0 (無匹配) | 0.450 | ✅ 通過 | ❌ **被過濾** |
| 0.50 | 1.1 (中度相關) | 0.550 | ✅ 通過 | ✅ 通過 |
| 0.50 | 1.0 (無匹配) | 0.500 | ✅ 通過 | ❌ **被過濾** |
| 0.60 | 1.0 (無匹配) | 0.600 | ✅ 通過 | ✅ 通過 |

**結論**：意圖在 [0.423, 0.55) 區間內變成了「必要條件」，不是「加分項」！

---

### 問題 2: 完美匹配仍可能被過濾

#### 理論 vs. 實際

**理論上**：
```python
base_similarity = 1.0  # 完美匹配
boost = 1.0            # 無意圖匹配
boosted_similarity = 1.0 × 1.0 = 1.0
1.0 >= 0.55 → ✅ 應該通過
```

**但用戶報告**：知識 1262 修正前找不到

**可能原因**：
1. ✅ **已確認**：知識被錯誤分類到 intent 105，修正後可以找到
2. ❓ 查詢意圖識別錯誤（可能被識別為 intent 105）
3. ❓ 其他過濾條件阻擋 (business_types, target_user)
4. ❓ 去重邏輯選擇了錯誤版本

#### 需要驗證

```bash
# 檢查線上日誌，看知識 1262 修正前：
# 1. SQL 階段是否返回？
# 2. Python 階段 base_similarity 是多少？
# 3. 計算的 boost 是多少？
# 4. 是否被其他過濾條件阻擋？
```

---

### 問題 3: 設計哲學不一致

#### 代碼註釋 vs. 實際行為

| 方面 | 代碼註釋說明 | 實際行為 |
|------|------------|---------|
| 意圖角色 | 「軟過濾器」「加成」 | ❌ 影響過濾決策 |
| SQL 意圖過濾 | ✅ 「移除硬性過濾」 | ✅ 確實移除 |
| Python 意圖過濾 | 「加成後過濾」 | ❌ 實際上是硬過濾 |
| 設計目標 | 「所有知識都參與」 | ❌ 部分知識因意圖被過濾 |

#### 用戶觀察

> "意圖應該是加分而不是主要吧？"

**用戶是對的**！當前設計違背了「向量為主，意圖為輔」的設計哲學。

---

## 優化建議

### 方案 A: 純向量過濾，意圖只影響排序（推薦）

#### 修改內容

**文件**: `vendor_knowledge_retriever.py`
**位置**: 第 401 行

```python
# 修改前
if boosted_similarity < similarity_threshold:
    filtered_count += 1
    continue

# 修改後
if base_similarity < similarity_threshold:  # ✅ 只用向量過濾
    filtered_count += 1
    continue
```

#### 效果

| 場景 | 修改前 | 修改後 |
|------|--------|--------|
| base=0.50, 無意圖匹配 | ❌ 被過濾 (0.50 < 0.55) | ✅ 保留，排序靠後 |
| base=0.50, 意圖匹配 | ✅ 保留 (0.65 >= 0.55) | ✅ 保留，排序靠前 |
| base=0.45, 意圖匹配 | ❌ 被過濾 (0.45 < 0.55) | ❌ 被過濾 (0.45 < 0.55) |

**優點**：
- ✅ 意圖變成純排序因子
- ✅ 消除「意圖依賴區間」
- ✅ 符合「向量為主，意圖為輔」設計哲學
- ✅ 最小改動（一行代碼）

**缺點**：
- ⚠️ 可能返回意圖不太相關但文本相似的知識（但會排序較後）

---

### 方案 B: 調整閾值，縮小意圖依賴區間

#### 修改內容

```python
# 方案 B1: 提高 SQL 閾值
sql_threshold = similarity_threshold / 1.15  # 0.55 / 1.15 = 0.478
# 意圖依賴區間縮小為 [0.478, 0.55)

# 方案 B2: 降低 Python 閾值
similarity_threshold = 0.50
sql_threshold = 0.50 / 1.3 = 0.385
# 意圖依賴區間為 [0.385, 0.50)，但閾值更寬鬆
```

**優點**：
- ✅ 保留意圖過濾邏輯
- ✅ 縮小問題區間

**缺點**：
- ❌ 沒有根本解決問題
- ❌ 意圖依賴區間仍然存在
- ⚠️ 需要調整閾值（影響所有查詢）

---

### 方案 C: 分層過濾策略

#### 修改內容

```python
HIGH_SIMILARITY_THRESHOLD = 0.85  # 高相似度閾值
MEDIUM_SIMILARITY_THRESHOLD = 0.55  # 中等相似度閾值

base_similarity = knowledge['base_similarity']
boosted_similarity = base_similarity * boost

# ✅ 分層過濾
if base_similarity >= HIGH_SIMILARITY_THRESHOLD:
    # 高相似度：直接通過，意圖無關緊要
    pass
elif base_similarity >= MEDIUM_SIMILARITY_THRESHOLD:
    # 中等相似度：使用加成後閾值
    if boosted_similarity < MEDIUM_SIMILARITY_THRESHOLD:
        filtered_count += 1
        continue
else:
    # 低相似度：嚴格依賴意圖匹配
    if boost < 1.2:  # 至少需要中度以上相關
        filtered_count += 1
        continue
```

**優點**：
- ✅ 保護高相似度匹配
- ✅ 低相似度依賴意圖（合理）
- ✅ 邏輯更精細

**缺點**：
- ❌ 複雜度增加
- ⚠️ 需要更多測試

---

### 方案 D: 統一閾值，移除雙閾值設計

#### 修改內容

```python
# 不要用不同閾值
sql_threshold = similarity_threshold  # 都用 0.55

# 過濾只看原始相似度
if base_similarity < similarity_threshold:
    filtered_count += 1
    continue

# boost 只用於排序
boosted_similarity = base_similarity * boost
```

**優點**：
- ✅ 邏輯最簡單清晰
- ✅ 意圖純粹是排序因子
- ✅ 沒有「意圖依賴區間」

**缺點**：
- ❌ SQL 返回候選減少（性能影響）
- ⚠️ candidate_limit 可能需要調整

---

## 推薦方案

### 立即實施：方案 A

**原因**：
1. ✅ 最小改動（一行代碼）
2. ✅ 根本解決問題
3. ✅ 符合設計哲學
4. ✅ 向後兼容（不影響高相似度匹配）

**修改**：
```python
# vendor_knowledge_retriever.py:401
if base_similarity < similarity_threshold:  # 改這一行
    filtered_count += 1
    continue
```

### 長期優化：方案 C

**原因**：
1. ✅ 更精細的邏輯
2. ✅ 保護高相似度
3. ✅ 合理利用意圖信息

**時機**：
- 方案 A 實施並驗證後
- 收集更多數據後
- 下個季度規劃中

---

## 測試計劃

### 測試案例 1: 完美匹配 + 意圖不匹配

```python
知識: "租金每個月幾號要繳？"
  - intent_id: 13 (租金繳納)
  - base_similarity: 1.0

查詢: "租金每個月幾號要繳？"
  - intent_id: 10 (租期／到期)  # 錯誤意圖
  - boost: 1.0 (無匹配)

修改前: 1.0 × 1.0 = 1.0 >= 0.55 ✅ 通過
修改後: 1.0 >= 0.55 ✅ 通過

預期: 兩者都應該找到
```

### 測試案例 2: 中等相似度 + 意圖不匹配（關鍵差異）

```python
知識: "租金什麼時候繳納？"
  - intent_id: 13 (租金繳納)
  - base_similarity: 0.50

查詢: "如何續約？"
  - intent_id: 10 (租期／到期)
  - boost: 1.0 (無匹配)

修改前: 0.50 × 1.0 = 0.50 < 0.55 ❌ 被過濾
修改後: 0.50 >= 0.55 → False ❌ 被過濾

預期: 兩者都應該被過濾（相似度不夠）
```

### 測試案例 3: 意圖依賴區間（關鍵差異）

```python
知識: "提前解約要賠償嗎？"
  - intent_id: 10 (租期／到期)
  - base_similarity: 0.48

查詢: "如何續約？"
  - intent_id: 10 (租期／到期)
  - boost_情況A: 1.3 (精確匹配)
  - boost_情況B: 1.0 (假設意圖錯誤分類)

修改前:
  - 情況A: 0.48 × 1.3 = 0.624 >= 0.55 ✅ 通過
  - 情況B: 0.48 × 1.0 = 0.480 < 0.55 ❌ 被過濾

修改後:
  - 情況A: 0.48 < 0.55 ❌ 被過濾
  - 情況B: 0.48 < 0.55 ❌ 被過濾

預期: 修改後相似度不夠應該被過濾（合理）
```

### 測試案例 4: 高相似度 + 意圖匹配

```python
知識: "如何辦理續約？"
  - intent_id: 10 (租期／到期)
  - base_similarity: 0.85

查詢: "如何續約？"
  - intent_id: 10 (租期／到期)
  - boost: 1.3

修改前: 0.85 × 1.3 = 1.105 >= 0.55 ✅ 通過 (排序第1)
修改後: 0.85 >= 0.55 ✅ 通過 (排序第1)

預期: 兩者都通過且排序相同
```

---

## 總結

### 當前邏輯的本質

**表面上**：意圖是「軟過濾器」和「加成因子」

**實際上**：意圖在 [0.423, 0.55) 區間內變成「必要條件」

### 核心問題

```python
# ❌ 問題代碼
if boosted_similarity < similarity_threshold:
    continue
```

這一行代碼讓意圖影響了過濾決策，違背了設計哲學。

### 解決方案

```python
# ✅ 修正代碼
if base_similarity < similarity_threshold:
    continue
```

**效果**：
- 意圖變成純排序因子 ✅
- 過濾只依據向量相似度 ✅
- 符合「向量為主，意圖為輔」✅

---

**分析完成日期**: 2026-01-13
**分析人員**: Claude
**建議優先級**: 🔴 高
**建議實施時間**: 立即

