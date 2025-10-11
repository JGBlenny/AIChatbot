# 測試情境狀態管理說明

## 狀態定義

### Test Scenarios 狀態

| 狀態 | 說明 | 在審核中心顯示 | 備註 |
|-----|------|--------------|------|
| `pending_review` | 待審核 | ✅ 是 | 從 unclear_questions 轉換而來，等待人工審核 |
| `approved` | 已批准 | ❌ 否 | 審核通過，加入測試題庫 |
| `rejected` | 已拒絕 | ❌ 否 | 審核拒絕，不加入測試題庫 |
| `draft` | 草稿 | ❌ 否 | 手動建立但尚未完成的測試情境 |

## 狀態流轉

### 流程圖

```
┌─────────────────────┐
│ unclear_questions   │
│ (frequency >= 2)    │
└──────────┬──────────┘
           │
           │ 手動轉換（create_test_scenario_from_unclear_question）
           ↓
┌─────────────────────┐
│  test_scenarios     │
│ status: pending_review │ ← 出現在「測試情境審核」Tab
└──────────┬──────────┘
           │
           │ 人工審核
           │
     ┌─────┴─────┐
     │           │
     ↓           ↓
┌─────────┐ ┌──────────┐
│approved │ │ rejected │ ← 不再出現在審核中心
└─────────┘ └──────────┘
     │
     │ 執行回測
     ↓
   測試結果
```

### 狀態轉換規則

#### 1. unclear_questions → test_scenarios (pending_review)

**觸發條件：**
- `unclear_questions.frequency >= 2`（在 `v_unclear_question_candidates` 中）
- 手動呼叫 SQL 函數

**SQL 函數：**
```sql
SELECT create_test_scenario_from_unclear_question(
    unclear_question_id,
    expected_category,
    difficulty,
    created_by
);
```

**結果：**
- 建立新的 `test_scenarios` 記錄
- 初始狀態：`status = 'pending_review'`
- 出現在審核中心的「測試情境審核」Tab

#### 2. pending_review → approved

**觸發位置：**
- 審核中心 → 測試情境審核 Tab → 點擊「✅ 批准」按鈕

**API 端點：**
```http
POST /api/test/scenarios/{scenario_id}/approve
```

**資料庫更新：**
```sql
UPDATE test_scenarios
SET status = 'approved',
    reviewed_by = '{reviewer_name}',
    reviewed_at = NOW(),
    review_notes = '{notes}'
WHERE id = {scenario_id};
```

**結果：**
- ❌ 從審核中心移除
- ✅ 可在「測試題庫管理」中查看（篩選 status = 'approved'）
- ✅ 可用於回測

#### 3. pending_review → rejected

**觸發位置：**
- 審核中心 → 測試情境審核 Tab → 點擊「❌ 拒絕」按鈕

**API 端點：**
```http
POST /api/test/scenarios/{scenario_id}/reject
```

**資料庫更新：**
```sql
UPDATE test_scenarios
SET status = 'rejected',
    reviewed_by = '{reviewer_name}',
    reviewed_at = NOW(),
    review_notes = '{rejection_reason}'
WHERE id = {scenario_id};
```

**結果：**
- ❌ 從審核中心移除
- ❌ 不會出現在回測中
- ✅ 可在「測試題庫管理」中查看（篩選 status = 'rejected'）
- ℹ️ 保留記錄以供日後參考

## 審核中心篩選邏輯

### 後端 API

**端點：** `GET /api/test/scenarios/pending`

**查詢視圖：** `v_pending_test_scenarios`

**視圖定義：**
```sql
CREATE OR REPLACE VIEW v_pending_test_scenarios AS
SELECT
    ts.id,
    ts.test_question,
    ts.expected_category,
    ts.difficulty,
    ts.status,
    ts.source,
    ts.source_question_id,
    -- 如果來自 unclear_questions，顯示原始問題的頻率
    CASE
        WHEN ts.source_question_id IS NOT NULL
        THEN (SELECT frequency FROM unclear_questions WHERE id = ts.source_question_id)
        ELSE NULL
    END AS question_frequency,
    CASE
        WHEN ts.source_question_id IS NOT NULL
        THEN (SELECT first_asked_at FROM unclear_questions WHERE id = ts.source_question_id)
        ELSE NULL
    END AS first_asked_at,
    ts.notes,
    ts.created_at,
    ts.created_by
FROM test_scenarios ts
WHERE ts.status = 'pending_review'  -- ⭐ 關鍵篩選條件
ORDER BY ts.created_at DESC;
```

### 前端元件

**檔案：** `knowledge-admin/frontend/src/components/review/TestScenarioReviewTab.vue`

**載入邏輯：**
```javascript
async loadPendingScenarios() {
    const response = await fetch('http://localhost:8000/api/test/scenarios/pending');
    const data = await response.json();
    this.scenarios = data.scenarios; // 只包含 pending_review 狀態
}
```

## 常見問題 (FAQ)

### Q1: 審核過的測試情境會再出現在審核中心嗎？

**A:** ❌ **不會**。一旦狀態從 `pending_review` 改為 `approved` 或 `rejected`，該記錄就不會再出現在審核中心的「測試情境審核」Tab。

### Q2: 如何查看已審核或已拒絕的測試情境？

**A:** 有兩種方式：

1. **前端介面**：
   - 進入「測試題庫管理」頁面（`/test-scenarios`）
   - 使用狀態篩選器選擇「已批准」或「已拒絕」

2. **資料庫查詢**：
```sql
-- 查看所有已批准的測試情境
SELECT * FROM test_scenarios WHERE status = 'approved';

-- 查看所有已拒絕的測試情境
SELECT * FROM test_scenarios WHERE status = 'rejected';

-- 查看特定測試情境的審核歷史
SELECT
    id,
    test_question,
    status,
    reviewed_by,
    reviewed_at,
    review_notes
FROM test_scenarios
WHERE id = {scenario_id};
```

### Q3: 可以重新審核已批准/拒絕的測試情境嗎？

**A:** 目前系統沒有「重新審核」功能，但有以下選項：

**方式 1：修改狀態（資料庫）**
```sql
-- 將已批准的測試情境改回待審核
UPDATE test_scenarios
SET status = 'pending_review',
    reviewed_by = NULL,
    reviewed_at = NULL,
    review_notes = NULL
WHERE id = {scenario_id};
```

**方式 2：編輯測試情境（前端）**
- 在「測試題庫管理」頁面找到該測試情境
- 點擊「✏️ 編輯」按鈕
- 修改內容後儲存
- 注意：這不會改變狀態，只會更新內容

### Q4: 拒絕的測試情境會被刪除嗎？

**A:** ❌ **不會刪除**。拒絕的測試情境會保留在資料庫中，僅改變狀態為 `rejected`。

**保留原因：**
- 追蹤審核歷史
- 避免重複建立相同的測試情境
- 日後可能需要重新評估

**如需刪除：**
- 在「測試題庫管理」頁面手動刪除
- 或使用 SQL：`DELETE FROM test_scenarios WHERE id = {scenario_id};`

### Q5: 同一個 unclear_question 可以建立多個 test_scenario 嗎？

**A:** ✅ **可以**，但需要注意：

```sql
-- 檢查某個 unclear_question 已建立的測試情境
SELECT
    id,
    test_question,
    status,
    created_at
FROM test_scenarios
WHERE source_question_id = {unclear_question_id};
```

**建議：**
- 避免重複建立
- 如果需要不同變體，應該：
  1. 修改現有測試情境，或
  2. 建立新的 unclear_question 記錄

## 統計資料

### 審核中心統計

```sql
-- 待審核數量
SELECT COUNT(*) FROM test_scenarios WHERE status = 'pending_review';

-- 已審核數量
SELECT COUNT(*) FROM test_scenarios WHERE status = 'approved';

-- 拒絕數量
SELECT COUNT(*) FROM test_scenarios WHERE status = 'rejected';
```

### 審核效率統計

```sql
-- 平均審核時間
SELECT
    AVG(EXTRACT(EPOCH FROM (reviewed_at - created_at))/3600) as avg_hours
FROM test_scenarios
WHERE reviewed_at IS NOT NULL;

-- 審核者統計
SELECT
    reviewed_by,
    COUNT(*) as total_reviewed,
    SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved_count,
    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_count
FROM test_scenarios
WHERE reviewed_by IS NOT NULL
GROUP BY reviewed_by;
```

## 相關檔案

### 資料庫
- 表：`test_scenarios`
- 視圖：`v_pending_test_scenarios`
- 函數：`create_test_scenario_from_unclear_question()`

### 後端 API
- 檔案：`knowledge-admin/backend/routes_test_scenarios.py`
- 端點：
  - `GET /api/test/scenarios/pending` - 取得待審核列表
  - `POST /api/test/scenarios/{id}/approve` - 批准
  - `POST /api/test/scenarios/{id}/reject` - 拒絕
  - `PUT /api/test/scenarios/{id}` - 更新

### 前端
- 檔案：`knowledge-admin/frontend/src/components/review/TestScenarioReviewTab.vue`
- 頁面：`knowledge-admin/frontend/src/views/TestScenariosView.vue`

## 最佳實踐

### 審核流程建議

1. **定期檢查待審核列表**
   - 建議每週至少檢查一次
   - 優先處理高頻率的問題（`question_frequency` 高）

2. **審核標準**
   - ✅ 批准：問題明確、有代表性、測試價值高
   - ❌ 拒絕：重複問題、無意義問題、超出業務範圍

3. **填寫審核備註**
   - 拒絕時務必填寫原因
   - 批准時可註明測試重點

4. **定期檢視拒絕的情境**
   - 每季度檢視一次 `rejected` 狀態的記錄
   - 評估是否有誤判需要重新審核

### 資料維護

```sql
-- 清理 6 個月前被拒絕的測試情境（選擇性）
DELETE FROM test_scenarios
WHERE status = 'rejected'
  AND reviewed_at < NOW() - INTERVAL '6 months';

-- 定期備份審核歷史
SELECT * FROM test_scenarios
WHERE reviewed_at IS NOT NULL
ORDER BY reviewed_at DESC;
```

---

**文件版本：** v1.0.0
**最後更新：** 2025-10-11
**維護者：** Claude
