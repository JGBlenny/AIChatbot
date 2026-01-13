# 🎯 檢索哲學分析：意圖應該是加分，不是主要條件

## 💡 核心觀點

**用戶觀點**：「意圖應該是加分而不是主要吧？」

**結論**：✅ **完全正確！**

---

## 🔍 當前邏輯的根本問題

### 設計意圖 vs. 實際效果

**設計意圖**（從代碼註釋看）：
```python
# ✅ 方案5：意圖作為軟過濾器
# - 移除硬性意圖過濾，所有知識都參與檢索
# - intent_boost 先用簡單邏輯（精確匹配 1.3，其他 1.0）
```

**實際效果**：
意圖仍然是**硬性過濾條件**，不是加分項！

### 為什麼？數學證明

```python
sql_threshold = similarity_threshold / 1.3  # 0.55 / 1.3 = 0.423
```

**案例分析**：

| base_similarity | intent 匹配? | boost | boosted_similarity | 結果 |
|-----------------|--------------|-------|-------------------|------|
| 0.50 | ✓ 是 | 1.3 | 0.50 × 1.3 = **0.65** | ✅ 通過 (>= 0.55) |
| 0.50 | ✗ 否 | 1.0 | 0.50 × 1.0 = **0.50** | ❌ 被過濾 (< 0.55) |
| 0.60 | ✓ 是 | 1.3 | 0.60 × 1.3 = **0.78** | ✅ 通過 |
| 0.60 | ✗ 否 | 1.0 | 0.60 × 1.0 = **0.60** | ✅ 通過 |

**問題**：
- 相似度 0.50 的知識，**必須**有意圖匹配才能通過
- 意圖匹配變成了「必要條件」，不是「加分項」
- 這違背了「向量檢索為主，意圖為輔」的設計理念

---

## 🎯 正確的設計哲學

### 層次結構

```
主要檢索依據：向量相似度（語義匹配）
    ↓
輔助排序依據：意圖匹配（錦上添花）
    ↓
業務規則：Scope > Priority
```

### 意圖的正確角色

**意圖不應該**：
- ❌ 決定是否過濾掉知識
- ❌ 成為必要條件
- ❌ 影響知識是否被返回

**意圖應該**：
- ✅ 影響排序順序
- ✅ 提高匹配知識的排名
- ✅ 作為「相關性加成」而非「准入門檻」

---

## 🔧 修正方案：意圖純粹作為排序因子

### 方案 A：基於向量閾值過濾，意圖只影響排序

```python
# ========================================
# 修正邏輯
# ========================================

# 第一步：基於原始相似度過濾
BASE_SIMILARITY_THRESHOLD = 0.55  # 或 0.5，根據業務調整

candidates = []
filtered_count = 0

for row in rows:
    knowledge = dict(row)
    base_similarity = knowledge['base_similarity']

    # ✅ 第一關：基於向量相似度過濾（主要依據）
    if base_similarity < BASE_SIMILARITY_THRESHOLD:
        filtered_count += 1
        continue  # 向量相似度不夠，直接過濾

    # ✅ 第二步：計算意圖加成（只用於排序）
    knowledge_intent_id = knowledge.get('intent_id')
    knowledge_intent_type = knowledge.get('intent_type')

    if use_semantic_boost and knowledge_intent_id:
        boost, reason, intent_semantic_similarity = self.intent_matcher.calculate_semantic_boost(
            intent_id,
            knowledge_intent_id,
            knowledge_intent_type
        )
    else:
        if knowledge_intent_id == intent_id:
            boost = 1.3
            reason = "精確匹配"
        elif knowledge_intent_id in all_intent_ids:
            boost = 1.15
            reason = "次要意圖匹配"
        else:
            boost = 1.0
            reason = "無意圖匹配"

    # ✅ 計算排序分數（不再用於過濾！）
    boosted_similarity = base_similarity * boost

    # 保存所有信息
    knowledge['intent_boost'] = boost
    knowledge['boosted_similarity'] = boosted_similarity  # 只用於排序
    knowledge['boost_reason'] = reason

    candidates.append(knowledge)

print(f"   Based on vector similarity: {len(candidates)} candidates (filtered: {filtered_count})")

# ✅ 第三步：排序（意圖在這裡發揮作用）
candidates.sort(
    key=lambda x: (
        -x['scope_weight'],           # 1st: Scope 優先級
        -x['boosted_similarity'],     # 2nd: 向量相似度 + 意圖加成
        -x.get('priority', 0)         # 3rd: 人工優先級
    )
)
```

### 邏輯對比

**修正前**：
```
if boosted_similarity < 0.55:
    continue  # 意圖影響過濾決策 ❌
```

**修正後**：
```
if base_similarity < 0.55:
    continue  # 只依據向量相似度過濾 ✅

# 意圖只影響排序
boosted_similarity = base_similarity * boost  # 用於排序
```

---

## 📊 效果對比

### 案例 1：中等相似度 + 無意圖匹配

**知識**：「租金什麼時候繳納？」(intent: 租金繳納)
**查詢**：「如何續約？」(intent: 租期／到期)
**相似度**：0.50（語義有些相關，但不強）

| 邏輯 | base | boost | boosted | 過濾? | 排序位置 |
|------|------|-------|---------|------|---------|
| 修正前 | 0.50 | 1.0 | 0.50 | ❌ **被過濾** | - |
| 修正後 | 0.50 | 1.0 | 0.50 | ✅ 保留 | 較後 |

**結果**：
- 修正前：直接看不到
- 修正後：保留但排序靠後（符合預期）

### 案例 2：高相似度 + 意圖匹配

**知識**：「如何辦理續約？」(intent: 租期／到期)
**查詢**：「如何續約？」(intent: 租期／到期)
**相似度**：0.85

| 邏輯 | base | boost | boosted | 過濾? | 排序位置 |
|------|------|-------|---------|------|---------|
| 修正前 | 0.85 | 1.3 | 1.105 | ✅ 保留 | 第 1 |
| 修正後 | 0.85 | 1.3 | 1.105 | ✅ 保留 | 第 1 |

**結果**：兩者相同（符合預期）

### 案例 3：高相似度 + 無意圖匹配

**知識**：「如何辦理續約？」(intent: 一般知識) ❌ 錯誤分類
**查詢**：「如何續約？」(intent: 租期／到期)
**相似度**：0.85

| 邏輯 | base | boost | boosted | 過濾? | 排序位置 |
|------|------|-------|---------|------|---------|
| 修正前 | 0.85 | 1.0 | 0.85 | ✅ 保留 | 第 3-5 |
| 修正後 | 0.85 | 1.0 | 0.85 | ✅ 保留 | 第 3-5 |

**結果**：兩者相同，但修正後邏輯更清晰

### 案例 4：中等相似度 + 意圖匹配（關鍵差異）

**知識**：「提前解約要賠償嗎？」(intent: 租期／到期)
**查詢**：「如何續約？」(intent: 租期／到期)
**相似度**：0.50（同類別但不同子問題）

| 邏輯 | base | boost | boosted | 過濾? | 排序位置 |
|------|------|-------|---------|------|---------|
| 修正前 | 0.50 | 1.3 | 0.65 | ✅ 保留 | 第 2-3 |
| 修正後 | 0.50 | 1.3 | 0.65 | ✅ 保留 | 第 2-3 |

**結果**：兩者相同

---

## 🎯 關鍵洞察

### 當前邏輯的真實問題

**並不是「意圖成為主要條件」**，而是：

```python
sql_threshold = similarity_threshold / 1.3  # 0.423
python_threshold = similarity_threshold      # 0.55
```

這個設計創造了一個**「意圖依賴區間」**：

```
[0.423, 0.55) → 「必須有意圖匹配才能通過」的區間
```

在這個區間內：
- base = 0.50, boost = 1.0 → 0.50 < 0.55 → ❌ 被過濾
- base = 0.50, boost = 1.3 → 0.65 >= 0.55 → ✅ 通過

**這就是意圖變成「必要條件」的根源！**

---

## ✅ 最終建議

### 選項 1：統一閾值（最簡單）

```python
# 不要用不同閾值！
sql_threshold = similarity_threshold  # 都用 0.55

# 過濾只看原始相似度
if base_similarity < similarity_threshold:
    continue

# boost 只用於排序
boosted_similarity = base_similarity * boost
```

**優點**：
- ✅ 邏輯最清晰
- ✅ 意圖純粹是加分
- ✅ 沒有「意圖依賴區間」

**缺點**：
- ⚠️ SQL 返回的候選數可能較少
- ⚠️ 需要調整 sql_threshold 以平衡性能

### 選項 2：保留雙閾值但改過濾邏輯（推薦）

```python
# SQL 用較低閾值獲取更多候選
sql_threshold = 0.423  # 保持不變

# Python 只用原始相似度過濾
if base_similarity < similarity_threshold:  # 用 base，不是 boosted
    continue

# boost 只用於排序
boosted_similarity = base_similarity * boost
```

**優點**：
- ✅ 保持性能（SQL 返回更多候選）
- ✅ 意圖純粹是加分
- ✅ 最小改動

**缺點**：
- ⚠️ 需要解釋為什麼有兩個不同閾值

---

## 📋 修正步驟

### 一行修改即可！

**文件**：`vendor_knowledge_retriever.py`
**位置**：約第 401 行

**修正前**：
```python
if boosted_similarity < similarity_threshold:  # ❌ 意圖影響過濾
    filtered_count += 1
    continue
```

**修正後**：
```python
if base_similarity < similarity_threshold:  # ✅ 只用向量過濾
    filtered_count += 1
    continue
```

**就這麼簡單！**

---

## 🧪 驗證測試

修正後重新測試案例 4：

```bash
# 知識：「提前解約要賠償嗎？」(base=0.50, intent: 租期／到期)
# 查詢：「如何續約？」(intent: 租金繳納) ← 意圖不匹配

curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "如何續約？",
    "vendor_id": 2,
    "target_user": "tenant"
  }'
```

**預期結果**：
- 修正前：如果 base=0.50, boost=1.0 → 被過濾
- 修正後：base=0.50 >= 0.5 → 保留（排序較後）

---

## 📊 總結

| 設計哲學 | 當前 | 修正後 |
|----------|------|--------|
| 主要依據 | 向量 + 意圖 | ✅ 純向量 |
| 意圖角色 | ❌ 過濾條件 | ✅ 排序加成 |
| 邏輯清晰度 | ⚠️ 混淆 | ✅ 清晰 |
| 是否有「意圖依賴區間」 | ❌ 有 [0.423, 0.55) | ✅ 沒有 |

**用戶的觀點是對的**：意圖應該是加分，不是主要條件！

**修正方法**：一行代碼即可
`if base_similarity < threshold` 代替 `if boosted_similarity < threshold`

---

**分析日期**：2026-01-13
**核心洞察**：意圖依賴區間 [0.423, 0.55) 是問題根源
**修正難度**：⭐ 極低（一行代碼）
**優先級**：🔴 高（影響設計哲學）
