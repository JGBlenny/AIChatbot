# 防止重複建立測試情境說明

## 問題描述

### 原始問題

使用者提問：
> "所以我先輸入「可不可以寵物」、「我想養寵物」會出現測試情境，我如果拒絕的話，之後再出現「我要養寵物」，那這樣在測試問題就不會出現嗎?"

### 問題情境

```
步驟 1: 輸入「可不可以養寵物」
   ↓
unclear_questions (ID: 23, frequency: 1)

步驟 2: 輸入「我想養寵物」(語義相似)
   ↓
unclear_questions (ID: 23, frequency: 2) ← 累加到同一筆
   ↓
手動轉換 → test_scenarios (ID: A, source_question_id: 23)

步驟 3: 審核拒絕
   ↓
test_scenarios (ID: A, status: rejected)

步驟 4: 再輸入「我要養寵物」(語義相似)
   ↓
unclear_questions (ID: 23, frequency: 3) ← 繼續累加

問題：如果再次手動轉換，會再次建立 test_scenario 嗎？
```

### 舊版本行為（已修復）

❌ **會重複建立**：
- 沒有檢查 `source_question_id` 是否已存在
- 可以針對同一個 `unclear_question` 建立多個 `test_scenario`
- 導致已拒絕的測試情境可能重複出現在審核中心

## 解決方案

### 新增防重複機制

修改 `create_test_scenario_from_unclear_question()` 函數，加入以下檢查：

```sql
-- 檢查是否已存在相同 source_question_id 的 test_scenario
SELECT id, status
FROM test_scenarios
WHERE source_question_id = p_unclear_question_id
ORDER BY created_at DESC
LIMIT 1;
```

### 處理邏輯

| 現有狀態 | 行為 | 結果 |
|---------|------|------|
| **無記錄** | 正常建立 | ✅ 建立新的 `pending_review` 記錄 |
| **pending_review** | 直接返回現有 ID | ℹ️ 避免重複建立，返回現有記錄 |
| **approved** | 拋出異常 | ⛔ 已審核通過，無需重複建立 |
| **rejected** | 拋出異常 | ⛔ 已被拒絕，需手動處理 |

### 錯誤訊息

#### 1. 待審核中（pending_review）

```
NOTICE: 測試情境已存在且待審核中: test_scenario #15, 直接返回
返回: 15 (現有 test_scenario ID)
```

**處理方式：**
- 不建立新記錄
- 直接返回現有 ID
- 該記錄仍在審核中心顯示

#### 2. 已審核通過（approved）

```
ERROR: 測試情境已審核通過: test_scenario #20, 無需重複建立
```

**處理方式：**
- 不允許重複建立
- 該測試情境已在測試題庫中
- 如需修改，請在「測試題庫管理」頁面編輯

#### 3. 已被拒絕（rejected）

```
ERROR: 測試情境已被拒絕: test_scenario #18.
如需重新審核，請先將該記錄狀態改為 draft 或直接刪除舊記錄。
```

**處理方式：**

**選項 A：重新開啟審核（推薦）**
```sql
-- 使用新的輔助函數
SELECT reopen_rejected_test_scenario(18, 'admin_name');

-- 結果：test_scenario #18 狀態改回 pending_review
-- 會再次出現在審核中心
```

**選項 B：刪除舊記錄，重新建立**
```sql
-- 刪除舊的拒絕記錄
DELETE FROM test_scenarios WHERE id = 18;

-- 重新建立
SELECT create_test_scenario_from_unclear_question(23, '寵物相關', 'medium', 'admin');
```

## 使用指南

### 正常流程

```sql
-- 1. 檢查是否有符合條件的 unclear_questions
SELECT * FROM v_unclear_question_candidates ORDER BY frequency DESC LIMIT 10;

-- 2. 建立測試情境（會自動檢查重複）
SELECT create_test_scenario_from_unclear_question(
    23,              -- unclear_question_id
    '寵物相關',       -- expected_category
    'medium',        -- difficulty
    'admin'          -- created_by
);

-- 3. 如果成功，返回新建立的 test_scenario ID
-- 如果已存在 pending_review，返回現有 ID
-- 如果已 approved/rejected，拋出異常
```

### 重新審核被拒絕的情境

```sql
-- 情境：某個測試情境被拒絕，但頻率持續增加，需要重新評估

-- 1. 查看被拒絕的測試情境
SELECT
    ts.id,
    ts.test_question,
    ts.status,
    ts.reviewed_at,
    ts.review_notes,
    uq.frequency AS current_frequency
FROM test_scenarios ts
LEFT JOIN unclear_questions uq ON ts.source_question_id = uq.id
WHERE ts.status = 'rejected'
ORDER BY uq.frequency DESC;

-- 2. 重新開啟審核（如果頻率顯著增加）
SELECT reopen_rejected_test_scenario(18, 'admin_name');

-- 3. 該記錄會再次出現在審核中心，狀態改回 pending_review
```

### 檢查重複記錄

```sql
-- 使用視圖查看是否有重複的 test_scenario
SELECT * FROM v_duplicate_test_scenarios;

-- 範例輸出：
-- source_question_id | unclear_question | current_frequency | scenario_count | scenarios
-- 23                 | 我可以養寵物嗎    | 5                 | 2              | ID:25 (status:pending_review, created:2025-10-11), ID:18 (status:rejected, created:2025-10-10)
```

## 實際案例示範

### 案例 1：首次建立

```sql
-- 情境：頻率達到 2，首次建立測試情境
SELECT create_test_scenario_from_unclear_question(23, '寵物相關', 'medium', 'admin');

-- 結果：成功建立
-- 返回: 15 (新的 test_scenario ID)
-- test_scenarios: ID=15, status=pending_review, source_question_id=23
```

### 案例 2：重複建立（待審核中）

```sql
-- 情境：ID=15 還在待審核，有人再次嘗試建立
SELECT create_test_scenario_from_unclear_question(23, '寵物相關', 'easy', 'admin2');

-- 結果：返回現有 ID
-- NOTICE: 測試情境已存在且待審核中: test_scenario #15, 直接返回
-- 返回: 15 (現有的 test_scenario ID)
```

### 案例 3：審核通過後嘗試重建

```sql
-- 情境：ID=15 已審核通過，有人嘗試重新建立
-- (審核動作)
UPDATE test_scenarios SET status = 'approved', reviewed_by = 'admin', reviewed_at = NOW()
WHERE id = 15;

-- (嘗試重建)
SELECT create_test_scenario_from_unclear_question(23, '寵物相關', 'hard', 'admin3');

-- 結果：拋出異常
-- ERROR: 測試情境已審核通過: test_scenario #15, 無需重複建立
```

### 案例 4：拒絕後重新評估

```sql
-- 情境：ID=15 被拒絕，但頻率從 2 增加到 10，需要重新評估

-- 步驟 1: 審核拒絕
UPDATE test_scenarios
SET status = 'rejected',
    reviewed_by = 'admin',
    reviewed_at = NOW(),
    review_notes = '問題不明確'
WHERE id = 15;

-- 步驟 2: 用戶持續詢問類似問題
-- unclear_questions.frequency: 2 → 5 → 8 → 10

-- 步驟 3: 嘗試重新建立
SELECT create_test_scenario_from_unclear_question(23, '寵物相關', 'medium', 'admin');

-- 結果：拋出異常
-- ERROR: 測試情境已被拒絕: test_scenario #15.
--        如需重新審核，請先將該記錄狀態改為 draft 或直接刪除舊記錄。

-- 步驟 4: 重新開啟審核
SELECT reopen_rejected_test_scenario(15, 'admin');

-- 結果：成功重新開啟
-- 返回: TRUE
-- test_scenarios: ID=15, status=pending_review (重新出現在審核中心)
-- review_notes 自動追加: "[2025-10-11 10:30:00] 由 admin 重新開啟審核"
```

## API 使用

### 前端實作建議

```javascript
// 在審核中心或其他需要建立測試情境的地方

async function createTestScenario(unclearQuestionId, category, difficulty) {
    try {
        const response = await fetch('/api/test/scenarios/from-unclear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                unclear_question_id: unclearQuestionId,
                expected_category: category,
                difficulty: difficulty,
                created_by: currentUser.name
            })
        });

        if (!response.ok) {
            const error = await response.json();

            // 處理不同的錯誤情況
            if (error.detail.includes('已審核通過')) {
                alert('此問題已有審核通過的測試情境，無需重複建立');
            } else if (error.detail.includes('已被拒絕')) {
                // 提供重新開啟選項
                if (confirm('此問題的測試情境曾被拒絕。是否要重新開啟審核？')) {
                    await reopenRejectedScenario(extractScenarioId(error.detail));
                }
            } else {
                alert('建立失敗: ' + error.detail);
            }
            return null;
        }

        const data = await response.json();
        alert(`測試情境已建立/返回: ID ${data.scenario_id}`);
        return data.scenario_id;

    } catch (error) {
        console.error('建立測試情境失敗:', error);
        alert('系統錯誤');
        return null;
    }
}

async function reopenRejectedScenario(scenarioId) {
    try {
        const response = await fetch(`/api/test/scenarios/${scenarioId}/reopen`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                reopened_by: currentUser.name
            })
        });

        if (response.ok) {
            alert('已重新開啟審核，測試情境將再次出現在審核中心');
            refreshReviewCenter();
        }
    } catch (error) {
        console.error('重新開啟失敗:', error);
    }
}
```

### 後端 API 端點（建議新增）

```python
# knowledge-admin/backend/routes_test_scenarios.py

@router.post("/scenarios/{scenario_id}/reopen")
async def reopen_test_scenario(scenario_id: int, data: ReopenRequest):
    """重新開啟已拒絕的測試情境審核"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT reopen_rejected_test_scenario(%s, %s)",
            (scenario_id, data.reopened_by)
        )
        result = cur.fetchone()[0]
        conn.commit()

        return {"success": True, "scenario_id": scenario_id}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    finally:
        cur.close()
        conn.close()
```

## 總結

### 修復前後對比

| 情境 | 修復前 | 修復後 |
|-----|--------|--------|
| 首次建立 | ✅ 正常建立 | ✅ 正常建立 |
| 重複建立（pending_review） | ❌ 建立重複記錄 | ✅ 返回現有 ID |
| 重複建立（approved） | ❌ 建立重複記錄 | ⛔ 拋出異常 |
| 重複建立（rejected） | ❌ 建立重複記錄 | ⛔ 拋出異常，提示使用 reopen |
| 重新評估拒絕的情境 | ❌ 只能刪除舊記錄 | ✅ 使用 reopen 函數 |

### 回答原始問題

> "所以我先輸入「可不可以寵物」、「我想養寵物」會出現測試情境，我如果拒絕的話，之後再出現「我要養寵物」，那這樣在測試問題就不會出現嗎?"

**答案（修復後）：**

✅ **不會自動再出現！**

1. 「可不可以養寵物」+ 「我想養寵物」→ `unclear_question` (頻率: 2)
2. 手動轉換 → `test_scenario` (status: pending_review)
3. 審核拒絕 → `test_scenario` (status: rejected)
4. 「我要養寵物」→ `unclear_question` (頻率: 3，語義累加)
5. ⭐ **嘗試再次轉換 → 拋出異常：「測試情境已被拒絕: test_scenario #X」**

**如需重新審核：**
```sql
SELECT reopen_rejected_test_scenario({scenario_id}, 'admin_name');
```

---

**文件版本：** v1.0.0
**最後更新：** 2025-10-11
**相關檔案：**
- `database/migrations/12-fix-duplicate-test-scenario-creation.sql`
- 函數：`create_test_scenario_from_unclear_question()`
- 函數：`reopen_rejected_test_scenario()`
- 視圖：`v_duplicate_test_scenarios`
