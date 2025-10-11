# 語義相似度 vs 類別分組說明

## 問題說明

使用者提問：
> "你這裡「寵物相關」，假設是「寵物相關但不同於可不可以養寵物的問題」呢，會進去測試問題嗎？"

## 核心概念

### 1. 語義相似度（Semantic Similarity）- 自動

**定義**：基於 Embedding 向量計算，判斷兩個問題的**意思是否相同**

**閾值**：0.85（預設）

**範例**：

| 問題 A | 問題 B | 相似度 | 結果 |
|--------|--------|--------|------|
| 我可以養寵物嗎 | 我想養寵物 | 0.8549 | ✅ 語義相似，累加到同一筆 |
| 我可以養寵物嗎 | 能養寵物嗎 | 0.8973 | ✅ 語義相似，累加到同一筆 |
| 寵物可以進電梯嗎 | 寵物可以搭電梯嗎 | 0.9110 | ✅ 語義相似，累加到同一筆 |
| 我可以養寵物嗎 | 養寵物要繳押金嗎 | ~0.70 | ❌ 語義不同，分開記錄 |
| 我可以養寵物嗎 | 寵物可以進電梯嗎 | ~0.65 | ❌ 語義不同，分開記錄 |

### 2. 類別分組（Category Grouping）- 人工

**定義**：基於人工判斷，將相關但語義不同的問題歸類到同一**主題類別**

**時機**：轉換為 test_scenario 時手動指定

**範例**：

```
類別：「寵物相關」
├─ unclear_question #23: "我可以養寵物嗎" (頻率: 4)
├─ unclear_question #24: "養寵物要繳押金嗎" (頻率: 1)
└─ unclear_question #25: "寵物可以進電梯嗎" (頻率: 2)
```

這三個問題語義不同，但都屬於「寵物相關」主題。

## 實際案例

### 案例：寵物相關問題

#### 輸入序列

```
1. 用戶 A: "可不可以養寵物"
2. 用戶 B: "我想養寵物"
3. 用戶 C: "我要養寵物"
4. 用戶 D: "養寵物要繳押金嗎"
5. 用戶 E: "養寵物需要押金嗎"
6. 用戶 F: "寵物可以進電梯嗎"
7. 用戶 G: "寵物可以搭電梯嗎"
```

#### 處理結果

```
unclear_questions 表:

ID  | 問題              | 頻率 | 說明
----|------------------|------|------------------
23  | 我可以養寵物嗎     | 3    | 累加 1+2+3
24  | 養寵物要繳押金嗎   | 2    | 累加 4+5
25  | 寵物可以進電梯嗎   | 2    | 累加 6+7
```

#### 轉換為測試情境

**步驟 1：檢查候選問題**
```sql
SELECT * FROM v_unclear_question_candidates;

-- 結果：
-- ID  | 問題              | 頻率
-- 23  | 我可以養寵物嗎     | 3  ✅ >= 2
-- 24  | 養寵物要繳押金嗎   | 2  ✅ >= 2
-- 25  | 寵物可以進電梯嗎   | 2  ✅ >= 2
```

**步驟 2：分別轉換（每個都會產生獨立的 test_scenario）**

```sql
-- 轉換問題 #23
SELECT create_test_scenario_from_unclear_question(23, '寵物相關', 'medium', 'admin');
-- 結果：test_scenario #A (status: pending_review)

-- 轉換問題 #24
SELECT create_test_scenario_from_unclear_question(24, '寵物相關', 'medium', 'admin');
-- 結果：test_scenario #B (status: pending_review)

-- 轉換問題 #25
SELECT create_test_scenario_from_unclear_question(25, '寵物相關', 'medium', 'admin');
-- 結果：test_scenario #C (status: pending_review)
```

**步驟 3：審核中心顯示**

```
測試情境審核 Tab:

ID | 測試問題          | 預期分類  | 頻率 | 狀態
---|------------------|----------|------|-------------
A  | 我可以養寵物嗎    | 寵物相關  | 3    | pending_review
B  | 養寵物要繳押金嗎  | 寵物相關  | 2    | pending_review
C  | 寵物可以進電梯嗎  | 寵物相關  | 2    | pending_review
```

**結論：✅ 會！每個語義不同的問題都會分別進入測試問題審核。**

## 關鍵區別

| 比較項目 | 語義相似度 | 類別分組 |
|---------|-----------|---------|
| **目的** | 避免重複記錄相同意思的問題 | 組織相關主題的問題 |
| **判斷方式** | 自動（AI Embedding） | 人工（審核時指定） |
| **閾值** | 0.85（可調整） | 無（主觀判斷） |
| **影響範圍** | `unclear_questions` 的頻率累加 | `test_scenarios` 的分類標籤 |
| **時機** | 即時（輸入問題時） | 延後（轉換為測試情境時） |

## 完整流程圖

```
用戶輸入問題
    ↓
    ├─ "我可以養寵物嗎"
    ├─ "我想養寵物"          → unclear_question #23 (頻率: 3)
    ├─ "我要養寵物"          ↗  語義相似，累加
    │
    ├─ "養寵物要繳押金嗎"
    ├─ "養寵物需要押金嗎"    → unclear_question #24 (頻率: 2)
    │                         ↗  語義相似，累加
    │
    ├─ "寵物可以進電梯嗎"
    └─ "寵物可以搭電梯嗎"    → unclear_question #25 (頻率: 2)
                              ↗  語義相似，累加

    ↓ 頻率 >= 2，成為候選問題

v_unclear_question_candidates
    ↓ 手動轉換

test_scenarios (3 筆獨立記錄)
    ├─ #A: "我可以養寵物嗎"   (category: 寵物相關)
    ├─ #B: "養寵物要繳押金嗎" (category: 寵物相關)
    └─ #C: "寵物可以進電梯嗎" (category: 寵物相關)

    ↓ 出現在審核中心

測試情境審核 Tab (顯示 3 筆)
    ↓ 各自審核

    ├─ 批准 #A → test_scenarios (status: approved)
    ├─ 批准 #B → test_scenarios (status: approved)
    └─ 拒絕 #C → test_scenarios (status: rejected)
```

## 實際測試驗證

### 測試資料

```sql
-- 查看目前的 unclear_questions
SELECT id, question, frequency FROM unclear_questions WHERE id >= 23;

-- 結果：
--  id |     question     | frequency
-- ----+------------------+-----------
--  23 | 我可以養寵物嗎   |         4
--  24 | 養寵物要繳押金嗎 |         1
--  25 | 寵物可以進電梯嗎 |         2
```

### 語義相似度測試

| 輸入問題 | 匹配結果 | unclear_question_id | 相似度 | 說明 |
|---------|---------|-------------------|--------|------|
| 我可以養寵物嗎 | 新建 | 23 | - | 首次輸入 |
| 我想養寵物 | 語義匹配 | 23 | 0.8549 | 累加到 ID 23 |
| 能養寵物嗎 | 語義匹配 | 23 | 0.8973 | 累加到 ID 23 |
| 養寵物要繳押金嗎 | 新建 | 24 | - | 語義不同，新建 |
| 寵物可以進電梯嗎 | 新建 | 25 | - | 語義不同，新建 |
| 寵物可以搭電梯嗎 | 語義匹配 | 25 | 0.9110 | 累加到 ID 25 |

### 轉換為測試情境

```sql
-- 因為 #24 頻率只有 1，不符合候選條件（< 2）
-- 只有 #23 和 #25 可以轉換

-- 轉換 #23
SELECT create_test_scenario_from_unclear_question(23, '寵物相關', 'medium', 'admin');
-- → test_scenario #19 (status: pending_review)

-- 轉換 #25
SELECT create_test_scenario_from_unclear_question(25, '寵物相關', 'medium', 'admin');
-- → test_scenario #26 (status: pending_review)

-- 嘗試轉換 #24（頻率不足）
-- 需要等到有第二個用戶問類似問題
```

## 常見問題 (FAQ)

### Q1: 如果我拒絕了「我可以養寵物嗎」，之後輸入「養寵物要繳押金嗎」還會出現嗎？

**A:** ✅ **會**！因為這兩個是語義不同的問題，會產生不同的 `unclear_question` 記錄。

```
unclear_question #23: "我可以養寵物嗎" → test_scenario #A (rejected)
unclear_question #24: "養寵物要繳押金嗎" → test_scenario #B (pending_review) ✅
```

### Q2: 如果我批准了「我可以養寵物嗎」，之後輸入「我想養寵物」還會再建立測試情境嗎？

**A:** ❌ **不會**！因為這兩個是語義相似的問題，會累加到同一個 `unclear_question #23`。

```
"我可以養寵物嗎" → unclear_question #23 (freq: 1)
"我想養寵物"     → unclear_question #23 (freq: 2) ← 語義相似，累加

轉換 #23 → test_scenario #A (approved)

之後再有用戶問「我要養寵物」：
unclear_question #23 (freq: 3) ← 語義相似，繼續累加

嘗試再次轉換 #23：
ERROR: 測試情境已審核通過: test_scenario #A, 無需重複建立 ❌
```

### Q3: 如何判斷兩個問題是否「語義相似」？

**A:** 使用 OpenAI Embeddings 計算向量相似度（Cosine Similarity）

**相似度範圍：**
- `0.90+`：幾乎相同意思
- `0.85-0.90`：相似（預設閾值 0.85）
- `0.80-0.85`：有些相關但意思不完全相同
- `0.80-`：意思不同

**範例：**
```
相似度 0.9110: "寵物可以進電梯嗎" vs "寵物可以搭電梯嗎" ✅
相似度 0.8973: "我可以養寵物嗎" vs "能養寵物嗎" ✅
相似度 0.8549: "我可以養寵物嗎" vs "我想養寵物" ✅
相似度 0.70：  "我可以養寵物嗎" vs "養寵物要繳押金嗎" ❌
相似度 0.65：  "我可以養寵物嗎" vs "寵物可以進電梯嗎" ❌
```

### Q4: 可以調整語義相似度閾值嗎？

**A:** ✅ 可以！在 `record_unclear_question()` 時指定：

```python
await unclear_manager.record_unclear_question(
    question="我可以養寵物嗎",
    semantic_similarity_threshold=0.90  # 提高閾值，更嚴格
)
```

**建議值：**
- 寬鬆（0.80）：更多問題會被合併，減少重複
- 平衡（0.85）：預設值，適合大多數情況
- 嚴格（0.90）：只合併幾乎相同的問題

### Q5: 如何查看哪些問題被歸為同一個 unclear_question？

**A:** 目前系統只記錄最原始的問題文字。如需追蹤所有變體，可以：

**選項 A：查看審核日誌（未實作）**
```sql
-- 未來可以建立 unclear_question_variants 表
CREATE TABLE unclear_question_variants (
    id SERIAL PRIMARY KEY,
    unclear_question_id INTEGER REFERENCES unclear_questions(id),
    variant_text TEXT,
    similarity_score DECIMAL(5,4),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**選項 B：查看對話記錄**
```sql
-- 查看特定 unclear_question 相關的所有對話
SELECT DISTINCT question
FROM conversation_logs
WHERE /* 需要 JOIN unclear_questions */;
```

## 總結

### 簡單記憶法

**語義相似度 = 「意思是否相同」（自動判斷）**
- 範圍：同一個問題的不同說法
- 影響：頻率累加
- 範例：「我可以養寵物嗎」≈「我想養寵物」

**類別分組 = 「主題是否相關」（人工標註）**
- 範圍：相關但意思不同的問題
- 影響：組織測試情境
- 範例：「我可以養寵物嗎」和「養寵物要繳押金嗎」都是「寵物相關」

### 回答原始問題

> "你這裡「寵物相關」，假設是「寵物相關但不同於可不可以養寵物的問題」呢，會進去測試問題嗎？"

**✅ 會！**

語義不同的「寵物相關」問題會：
1. 產生不同的 `unclear_question` 記錄
2. 各自累加頻率
3. 達到閾值（頻率 >= 2）後
4. 可以分別轉換為 `test_scenario`
5. 分別出現在測試情境審核中心

**實例：**
- ✅ "我可以養寵物嗎" → test_scenario #A
- ✅ "養寵物要繳押金嗎" → test_scenario #B
- ✅ "寵物可以進電梯嗎" → test_scenario #C

這三個都會獨立出現在審核中心，可以各自批准或拒絕。

---

**文件版本：** v1.0.0
**最後更新：** 2025-10-11
**相關文件：**
- `SEMANTIC_SIMILARITY_TEST_REPORT.md` - 語義相似度實作說明
- `TEST_SCENARIO_STATUS_MANAGEMENT.md` - 測試情境狀態管理
- `DUPLICATE_TEST_SCENARIO_PREVENTION.md` - 防止重複建立測試情境
