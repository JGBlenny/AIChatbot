# 🔍 檢索邏輯評估報告

## 日期
2026-01-13

## 🎯 用戶提出的核心問題

> "但是就算意圖是不完美，但知識完美匹配，搜尋不到，有點不合邏輯吧"

**用戶的觀察是完全正確的！** 這是一個重要的邏輯缺陷。

---

## 📊 案例分析：知識 ID 1262

### 基本資訊
- **知識內容**: "你好，我要續約，新的合約甚麼時候會提供?"
- **知識 metadata**:
  - vendor_id: NULL (全局知識)
  - business_types: `{property_management, full_service}`
  - target_user: `{tenant}`
  - scope: `global`
  - embedding: ✓ 存在

### 修正前狀態
- **意圖分類**: Intent 105 (一般知識) ❌ 錯誤分類
- **結果**: 線上找不到

### 修正後狀態
- **意圖分類**: Intent 10 (租期／到期) ✅ 正確分類
- **結果**: 可以找到 ✓

---

## 🔬 當前檢索邏輯分析

### 檢索管道 (Pipeline)

```
用戶查詢
    ↓
[1] 意圖識別 → intent_id = 10 (租期／到期)
    ↓
[2] SQL 階段過濾
    ├─ 相似度閾值: base_similarity >= 0.423 (sql_threshold)
    ├─ Scope 過濾: vendor/global 匹配
    ├─ business_types 過濾: 業態重疊檢查
    └─ target_user 過濾: 角色匹配
    ↓
    返回候選知識 (每個知識可能有多個意圖映射)
    ↓
[3] Python 階段加成與過濾
    ├─ 計算 intent_boost:
    │   ├─ 主要意圖匹配: 1.3x
    │   ├─ 次要意圖匹配: 1.15x (語義相似)
    │   └─ 無匹配: 1.0x
    ├─ boosted_similarity = base_similarity × boost
    └─ 過濾: if boosted_similarity < 0.55: 丟棄
    ↓
[4] 重新排序與去重
    ├─ 排序: scope_weight > boosted_similarity > priority
    └─ 去重: 每個知識只保留最高分版本
    ↓
返回 top_k 結果
```

### 關鍵代碼位置

**SQL 閾值計算** (`vendor_knowledge_retriever.py:256`):
```python
sql_threshold = similarity_threshold / 1.3  # 0.55 / 1.3 = 0.423
```

**SQL 意圖過濾已移除** (`vendor_knowledge_retriever.py:318-320`):
```python
# ✅ 方案5：移除硬性意圖過濾！
# 之前：AND (kim.intent_id = ANY(intent_ids) OR kim.intent_id IS NULL)
# 現在：所有知識都參與，無論意圖是否匹配
```

**Python 階段過濾** (`vendor_knowledge_retriever.py:401-403`):
```python
if boosted_similarity < similarity_threshold:  # 0.55
    filtered_count += 1
    continue  # 被過濾掉！
```

---

## 🤔 理論 vs. 實際

### 理論計算（修正前）

**場景**: 知識 1262 意圖為 105，查詢意圖為 10

| 階段 | 參數 | 值 | 結果 |
|------|------|-----|------|
| SQL | base_similarity | 1.0 (完美匹配) | ✓ 通過 (1.0 >= 0.423) |
| SQL | business_types | 重疊 | ✓ 通過 |
| SQL | target_user | {tenant} | ✓ 通過 |
| Python | knowledge_intent_id | 105 | - |
| Python | query_intent_id | 10 | - |
| Python | intent_match? | NO | boost = 1.0 |
| Python | boosted_similarity | 1.0 × 1.0 = 1.0 | ✓ 應該通過 (1.0 >= 0.55) |

**結論**: 按照代碼邏輯，**應該能找到**！

### 實際情況

**用戶報告**: 修正前找不到，修正後可以找到

**這表示存在以下可能性之一**:

1. ❓ **LEFT JOIN 產生的多行問題**
   - 如果知識 1262 同時有多個意圖映射
   - 去重邏輯可能選擇了錯誤的版本

2. ❓ **查詢意圖識別錯誤**
   - 查詢"你好，我要續約，新的合約甚麼時候會提供?"可能被識別為 intent 105
   - 如果 query_intent = 105, knowledge_intent = 105, boost = 1.3
   - 但修正後 knowledge_intent = 10, 如果 query_intent = 10, boost 也是 1.3
   - 都應該能找到，除非查詢意圖識別在修正前後不同

3. ❓ **其他隱藏過濾條件**
   - 可能存在未記錄的過濾邏輯

---

## 💡 核心邏輯缺陷

### 問題：完美匹配被意圖過濾

**當前邏輯**:
```python
boosted_similarity = base_similarity × boost
if boosted_similarity < 0.55:
    continue
```

**問題場景**:
- base_similarity = 0.6 (高相似度)
- intent 不匹配 → boost = 1.0
- boosted_similarity = 0.6 × 1.0 = 0.6
- ✓ 通過 (0.6 >= 0.55)

但是:
- base_similarity = 0.5 (中等相似度)
- intent 不匹配 → boost = 1.0
- boosted_similarity = 0.5 × 1.0 = 0.5
- ✗ 被過濾 (0.5 < 0.55)

**如果文本相似度很高 (例如 0.9 或 1.0)，意圖不匹配真的應該成為障礙嗎？**

---

## 🎯 理想檢索邏輯

### 提議：分層過濾策略

```python
# 方案 A: 高相似度繞過意圖過濾
HIGH_SIMILARITY_THRESHOLD = 0.9  # 近乎完美匹配
MEDIUM_SIMILARITY_THRESHOLD = 0.7  # 高相似度
BASE_THRESHOLD = 0.55  # 基礎閾值

if base_similarity >= HIGH_SIMILARITY_THRESHOLD:
    # 完美匹配：直接通過，無論意圖如何
    return True
elif base_similarity >= MEDIUM_SIMILARITY_THRESHOLD:
    # 高相似度：意圖作為加成，但不強制要求
    boosted_similarity = base_similarity * boost
    return boosted_similarity >= BASE_THRESHOLD
else:
    # 中低相似度：嚴格依賴意圖匹配
    if boost == 1.0:  # 無意圖匹配
        return False  # 直接過濾
    boosted_similarity = base_similarity * boost
    return boosted_similarity >= BASE_THRESHOLD
```

### 邏輯說明

| base_similarity | intent 匹配 | 處理策略 | 理由 |
|-----------------|-------------|----------|------|
| >= 0.9 | 任何 | 直接通過 | 文本幾乎完美，意圖無關緊要 |
| 0.7 - 0.9 | 匹配 | boost 1.3x | 高相似度 + 意圖匹配 = 優質結果 |
| 0.7 - 0.9 | 不匹配 | boost 1.0x，但仍可能通過 | 高相似度彌補意圖不匹配 |
| < 0.7 | 匹配 | boost 1.3x | 依賴意圖加成達到閾值 |
| < 0.7 | 不匹配 | 直接過濾 | 低相似度 + 無意圖匹配 = 低質量 |

---

## 📋 具體建議

### 選項 1: 保守修正（推薦）

**只修改完美匹配情況**:

```python
# vendor_knowledge_retriever.py:401 附近
HIGH_SIMILARITY_BYPASS = 0.9  # 配置參數

if base_similarity >= HIGH_SIMILARITY_BYPASS:
    # 完美匹配：直接通過
    boost = max(boost, 1.0)  # 確保至少 1.0
    boosted_similarity = base_similarity
    knowledge['intent_boost'] = boost
    knowledge['boosted_similarity'] = boosted_similarity
    knowledge['boost_reason'] = f"完美匹配 (繞過意圖過濾)"
    candidates.append(knowledge)
    continue

# 原有邏輯
boosted_similarity = base_similarity * boost
if boosted_similarity < similarity_threshold:
    filtered_count += 1
    continue
```

**優點**:
- ✅ 最小化改動
- ✅ 只影響高相似度情況
- ✅ 向後兼容

**風險**:
- ⚠️ 可能返回意圖完全不相關但文本相似的知識

### 選項 2: 完整分層邏輯

實現上述「理想檢索邏輯」的完整版本。

**優點**:
- ✅ 邏輯更合理
- ✅ 處理所有相似度範圍

**風險**:
- ⚠️ 需要更多測試
- ⚠️ 可能影響現有檢索結果

### 選項 3: 可配置策略

添加配置參數讓不同業者選擇策略:

```python
RETRIEVAL_STRATEGY = {
    "high_similarity_bypass": True,  # 是否啟用高相似度繞過
    "high_similarity_threshold": 0.9,  # 繞過閾值
    "strict_intent_matching": False,  # 是否嚴格意圖匹配
}
```

---

## 🧪 建議測試案例

### 測試 1: 完美匹配 + 意圖不匹配
- **知識**: "租金每個月幾號要繳？" (intent: 租金繳納)
- **查詢**: "租金每個月幾號要繳？" (intent: 租金繳納)
- **預期**: 找到 ✓

### 測試 2: 完美匹配 + 意圖錯誤分類
- **知識**: "租金每個月幾號要繳？" (intent: 一般知識) ❌ 錯誤
- **查詢**: "租金每個月幾號要繳？" (intent: 租金繳納)
- **預期**: 應該找到 (文本完美匹配)

### 測試 3: 高相似度 + 意圖不匹配
- **知識**: "租金什麼時候繳納？" (intent: 租金繳納)
- **查詢**: "租金幾號要繳？" (intent: 租金繳納)
- **預期**: 找到 ✓

### 測試 4: 低相似度 + 意圖匹配
- **知識**: "提前解約要賠償嗎？" (intent: 租期／到期)
- **查詢**: "續約流程是什麼？" (intent: 租期／到期)
- **預期**: boost 後如果 >= 閾值就通過

### 測試 5: 低相似度 + 意圖不匹配
- **知識**: "如何報修？" (intent: 房屋維修)
- **查詢**: "租金怎麼繳？" (intent: 租金繳納)
- **預期**: 不應找到 ✗

---

## ✅ 結論

### 用戶的觀察是正確的

**現有邏輯的問題**:
1. ❌ 過度依賴意圖匹配，即使文本完美匹配
2. ❌ 沒有區分不同相似度等級的處理策略
3. ❌ 意圖錯誤分類會直接導致高質量知識被過濾

### 建議立即採取的行動

1. **短期 (本週)**:
   - ✅ 實施「選項 1: 保守修正」
   - ✅ 添加 `HIGH_SIMILARITY_BYPASS = 0.9` 配置
   - ✅ 測試 5 個測試案例

2. **中期 (本月)**:
   - 📊 監控高相似度繞過的使用情況
   - 📊 收集繞過後的查詢質量數據
   - 🔍 批量檢查意圖錯誤分類的知識

3. **長期 (下季度)**:
   - 🎯 考慮實施完整分層邏輯 (選項 2)
   - 🤖 改進意圖自動分類演算法
   - 📈 建立檢索質量監控儀表板

---

## 📝 修正記錄

| 日期 | 問題 | 解決方案 | 狀態 |
|------|------|----------|------|
| 2026-01-13 | 知識 1262 意圖錯誤分類 | 修正 intent 105 → 10 | ✅ 完成 |
| 2026-01-13 | 完美匹配被意圖過濾 | 待實施分層邏輯 | ⏳ 規劃中 |

---

**分析人員**: Claude
**審核狀態**: 待用戶確認
**優先級**: 🔴 高 (影響檢索準確性)

