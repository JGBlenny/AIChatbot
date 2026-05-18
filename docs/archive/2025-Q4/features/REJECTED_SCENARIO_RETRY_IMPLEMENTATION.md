# 測試情境拒絕後重試機制實現報告

**實現日期**: 2025-10-12
**功能**: 智能高頻重試機制 + 前端視覺提示

---

## 📋 需求背景

### 用戶提出的兩個問題

#### ❓ 問題 1：測試情境被拒絕後，用戶再次詢問應該再出現嗎？

**場景**：
```
頻率 2 → 創建測試情境 → 審核員拒絕（認為表述不清）
用戶持續詢問 → 頻率達到 5次、10次、20次...
問題：系統應該永遠沉默嗎？
```

**問題點**：
- 一次拒絕不代表永遠拒絕
- 高頻問題可能是真實需求
- 審核員可能需要重新評估

#### ❓ 問題 2：審核過程中刪除測試情境應該再出現嗎？

**當前行為**：刪除後會重新創建 ✅（合理）

---

## 🎯 解決方案：智能重試機制

### 核心設計：雙閾值系統

```
第一次閾值（頻率 ≥ 2）  → 創建測試情境
       ↓
審核員拒絕
       ↓
靜默期（頻率 3-4）      → 不做任何動作
       ↓
重試閾值（頻率 ≥ 5）   → 重新創建測試情境
```

### 設計優勢

1. **漸進式重試**：不是一拒絕就死，給高頻問題第二次機會
2. **閾值保護**：只有真正高頻才重試，避免垃圾數據
3. **清晰追溯**：每個情境的 notes 記錄完整歷史
4. **自動化 + 可見性**：自動處理但完整記錄

---

## 🔧 技術實現

### 1️⃣ 數據庫層

#### Migration 14: 修改創建函數

**文件**: `database/migrations/14-add-rejected-scenario-retry-logic.sql`

**核心修改**：
```sql
CREATE OR REPLACE FUNCTION create_test_scenario_from_unclear_question(
    p_unclear_question_id INTEGER,
    p_expected_category VARCHAR(100) DEFAULT NULL,
    p_difficulty VARCHAR(20) DEFAULT 'medium',
    p_created_by VARCHAR(100) DEFAULT 'system',
    p_allow_retry BOOLEAN DEFAULT false  -- ⭐ 新增參數
) RETURNS INTEGER AS $$
BEGIN
    -- rejected 情境處理邏輯
    IF v_existing_status = 'rejected' THEN
        IF p_allow_retry THEN
            -- 允許重試：繼續創建新情境
            RAISE NOTICE '允許重試：舊情境 #% 已被拒絕，創建新情境';
        ELSE
            -- 不允許重試：拋出異常
            RAISE EXCEPTION '測試情境已被拒絕: test_scenario #%...';
        END IF;
    END IF;

    -- 創建新情境時記錄歷史
    notes := FORMAT('從用戶問題 #%s 創建，問題被問 %s 次%s',
        p_unclear_question_id,
        frequency,
        CASE WHEN v_existing_scenario_id IS NOT NULL
            THEN FORMAT(' (原情境 #%s 已被拒絕)', v_existing_scenario_id)
            ELSE ''
        END);
END;
$$;
```

#### Migration 14: 更新觸發器

**高頻重試邏輯**：
```sql
CREATE OR REPLACE FUNCTION auto_create_test_scenario_from_unclear()
RETURNS TRIGGER AS $$
DECLARE
    v_high_freq_threshold INTEGER := 5;  -- 重試閾值
BEGIN
    -- 檢查現有情境
    SELECT id, status INTO v_existing_scenario, v_scenario_status
    FROM test_scenarios
    WHERE source_question_id = NEW.id
    ORDER BY created_at DESC
    LIMIT 1;

    IF v_existing_scenario IS NOT NULL THEN
        -- rejected + 達到高頻閾值 = 允許重新創建
        IF v_scenario_status = 'rejected' AND NEW.frequency >= v_high_freq_threshold THEN
            RAISE NOTICE '🔄 頻率已達 %次（閾值：%），允許重新創建',
                NEW.frequency, v_high_freq_threshold;
        ELSE
            -- 未達閾值或其他狀態，跳過
            RETURN NEW;
        END IF;
    END IF;

    -- 調用創建函數，傳入 allow_retry 參數
    SELECT create_test_scenario_from_unclear_question(
        p_unclear_question_id := NEW.id,
        p_allow_retry := (v_existing_scenario IS NOT NULL AND v_scenario_status = 'rejected')
    ) INTO v_scenario_id;
END;
$$;
```

#### Migration 15: 更新視圖

**文件**: `database/migrations/15-update-candidates-view-for-rejected-scenarios.sql`

**新增欄位**：
```sql
CREATE VIEW v_unclear_question_candidates AS
SELECT
    uq.id as unclear_question_id,
    uq.question,
    uq.frequency,

    -- 判斷是否可以創建/重新創建
    CASE
        WHEN ts.id IS NULL THEN true                          -- 沒有情境
        WHEN ts.status = 'rejected' AND uq.frequency >= 5 THEN true  -- 高頻重試
        ELSE false
    END as can_create_scenario,

    -- ⭐ 標識高頻重試場景
    CASE
        WHEN ts.status = 'rejected' AND uq.frequency >= 5 THEN true
        ELSE false
    END as is_high_freq_retry,

    ts.id as existing_scenario_id,
    ts.status as scenario_status
FROM unclear_questions uq
LEFT JOIN (
    SELECT DISTINCT ON (source_question_id)
        id, source_question_id, status, created_at
    FROM test_scenarios
    WHERE source_question_id IS NOT NULL
    ORDER BY source_question_id, created_at DESC  -- 取最新情境
) ts ON ts.source_question_id = uq.id
WHERE uq.status IN ('pending', 'in_progress')
  AND uq.frequency >= 2
ORDER BY
    CASE WHEN ts.status = 'rejected' AND uq.frequency >= 5 THEN 0 ELSE 1 END,  -- 高頻重試優先
    uq.frequency DESC;
```

### 2️⃣ 後端 API

**端點**: `GET /api/test/unclear-questions/candidates`

**返回數據結構**（已包含新欄位）：
```json
{
  "candidates": [
    {
      "unclear_question_id": 36,
      "question": "社區泳池水質檢測報告哪裡看",
      "frequency": 6,
      "can_create_scenario": true,
      "is_high_freq_retry": true,        // ⭐ 新增
      "existing_scenario_id": 35,
      "scenario_status": "rejected"
    }
  ]
}
```

### 3️⃣ 前端組件

**文件**: `knowledge-admin/frontend/src/components/review/UnclearQuestionReviewTab.vue`

#### 修改 1：高頻重試徽章

```vue
<div class="card-header">
  <span class="question-id">#{{ candidate.unclear_question_id }}</span>
  <span class="frequency-badge">📊 被問 {{ candidate.frequency }} 次</span>

  <!-- ⭐ 高頻重試特殊標識 -->
  <span v-if="candidate.is_high_freq_retry" class="retry-badge">
    🔄 高頻重試
  </span>
</div>
```

**CSS 動畫效果**：
```css
.retry-badge {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
  animation: pulse 2s infinite;  /* 脈衝動畫 */
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
```

#### 修改 2：情境狀態詳細顯示

```vue
<div v-if="candidate.existing_scenario_id"
     class="existing-info"
     :class="getScenarioStatusClass(candidate.scenario_status)">
  <div class="info-header">
    <span v-if="candidate.scenario_status === 'rejected'" class="status-icon">⚠️</span>
    <strong>{{ getScenarioStatusText(candidate.scenario_status) }}</strong>
  </div>

  <p class="info-detail">
    測試情境 #{{ candidate.existing_scenario_id }}
    <span v-if="candidate.scenario_status === 'rejected' && candidate.is_high_freq_retry">
      曾被拒絕，但問題頻率持續上升，建議重新審核
    </span>
    <span v-else-if="candidate.scenario_status === 'rejected'">
      已被拒絕（頻率達 5 次時可自動重新創建）
    </span>
  </p>
</div>
```

**條件樣式**：
```css
.existing-info.status-rejected {
  background: #fef0f0;
  border-left: 4px solid #f56c6c;  /* 紅色左邊框 */
}

.existing-info.status-approved {
  background: #f0f9ff;
  border-left: 4px solid #67c23a;  /* 綠色左邊框 */
}

.existing-info.status-pending {
  background: #e7f3ff;
  border-left: 4px solid #409eff;  /* 藍色左邊框 */
}
```

---

## 🧪 測試驗證

### 測試場景 1：完整生命週期

```sql
-- 步驟 1：創建問題（頻率 2）
INSERT INTO unclear_questions (question, frequency, status)
VALUES ('社區游泳池開放時間？', 2, 'pending');

-- 結果：✅ 自動創建測試情境 #26

-- 步驟 2：審核員拒絕
UPDATE test_scenarios SET status = 'rejected' WHERE id = 26;

-- 步驟 3：用戶繼續詢問（頻率 3-4）
UPDATE unclear_questions SET frequency = 3 WHERE id = 32;
-- 結果：⚠️ 跳過創建（未達閾值）

UPDATE unclear_questions SET frequency = 4 WHERE id = 32;
-- 結果：⚠️ 跳過創建（未達閾值）

-- 步驟 4：達到高頻閾值（頻率 5）
UPDATE unclear_questions SET frequency = 5 WHERE id = 32;
-- 結果：✅ 重新創建測試情境 #27
-- 通知：🔄 用戶問題 #32 的情境 #26 曾被拒絕，但頻率已達 5次，允許重新創建
```

### 數據庫狀態

```sql
-- test_scenarios 表
| id | test_question        | status         | notes                           |
|----|---------------------|----------------|---------------------------------|
| 26 | 社區游泳池開放時間？   | rejected       | 從用戶問題 #32 創建，被問 2 次    |
| 27 | 社區游泳池開放時間？   | pending_review | 從用戶問題 #32 創建，被問 5 次 (原情境 #26 已被拒絕) |

-- v_unclear_question_candidates 視圖
| unclear_question_id | question          | frequency | can_create_scenario | is_high_freq_retry | existing_scenario_id | scenario_status |
|---------------------|-------------------|-----------|---------------------|--------------------|--------------------|-----------------|
| 32                  | 社區游泳池開放時間？ | 5         | false               | false              | 27                  | pending_review  |
```

### 測試場景 2：高頻重試顯示

```sql
-- 創建演示數據（手動繞過觸發器）
INSERT INTO unclear_questions (question, frequency, status)
VALUES ('社區泳池水質檢測報告哪裡看', 6, 'pending');

INSERT INTO test_scenarios (
    test_question, status, source, source_question_id, created_by
) VALUES (
    '社區泳池水質檢測報告哪裡看', 'rejected', 'user_question', 36, 'auto_trigger'
);

-- 查詢結果
SELECT * FROM v_unclear_question_candidates WHERE question = '社區泳池水質檢測報告哪裡看';

-- 結果：
| is_high_freq_retry | can_create_scenario | scenario_status |
|--------------------|---------------------|-----------------|
| true ✅            | true ✅             | rejected        |
```

### API 驗證

```bash
curl http://localhost:8000/api/test/unclear-questions/candidates | jq '.candidates[] | select(.is_high_freq_retry)'

# 輸出：
{
  "unclear_question_id": 36,
  "question": "社區泳池水質檢測報告哪裡看",
  "frequency": 6,
  "can_create_scenario": true,
  "is_high_freq_retry": true,  # ✅
  "existing_scenario_id": 35,
  "scenario_status": "rejected"
}
```

---

## 🎨 前端效果

### 視覺呈現

#### 1. 普通問題（無特殊標識）
```
┌─────────────────────────────────────────────────┐
│ #26  📊 被問 3 次  待處理                        │
├─────────────────────────────────────────────────┤
│ 可以養寵物嗎                                     │
│ ...                                              │
└─────────────────────────────────────────────────┘
```

#### 2. 高頻重試問題（閃爍徽章）
```
┌─────────────────────────────────────────────────┐
│ #36  📊 被問 6 次  🔄 高頻重試  處理中          │
├─────────────────────────────────────────────────┤
│ 社區泳池水質檢測報告哪裡看                        │
│                                                  │
│ ⚠️ 測試情境已拒絕                               │
│ 測試情境 #35                                     │
│ 曾被拒絕，但問題頻率持續上升，建議重新審核        │
│                                                  │
│ [🔄 轉為測試情境]  [🚫 忽略]                    │
└─────────────────────────────────────────────────┘
```

### 顏色編碼

- **高頻重試徽章**: 粉紅-紅色漸層 + 脈衝動畫
- **rejected 狀態框**: 紅色左邊框 (#f56c6c) + 淡紅背景
- **approved 狀態框**: 綠色左邊框 (#67c23a) + 淡綠背景
- **pending 狀態框**: 藍色左邊框 (#409eff) + 淡藍背景

---

## 📊 業務影響

### 改進前 vs 改進後

| 場景 | 改進前 | 改進後 |
|------|--------|--------|
| 測試情境被拒絕 | 永遠不會再出現 ❌ | 頻率達 5 次時自動重新創建 ✅ |
| 高頻問題識別 | 需要手動查詢資料庫 | 前端自動標記「🔄 高頻重試」✅ |
| 審核員可見性 | 看不到歷史拒絕記錄 | 清楚顯示「曾被拒絕」+ 原因 ✅ |
| 誤判保護 | 一次拒絕 = 永久沉默 | 給真實需求第二次機會 ✅ |

### 預期效果

1. **減少遺漏**: 高頻需求不會因一次拒絕而永久消失
2. **提升效率**: 審核員快速識別需要重新審核的問題
3. **改善體驗**: 用戶持續反饋的問題最終會被處理
4. **可追溯性**: 完整記錄每個決策歷史

---

## 🚀 部署清單

### 數據庫 Migration

- [x] `14-add-rejected-scenario-retry-logic.sql` - 核心重試邏輯
- [x] `15-update-candidates-view-for-rejected-scenarios.sql` - 視圖更新

### 前端更新

- [x] 修改 `UnclearQuestionReviewTab.vue` - 視覺提示
- [x] 重新編譯前端 (`npm run build`)
- [x] 重啟前端容器

### 驗證步驟

```bash
# 1. 檢查資料庫函數
psql -c "\df+ create_test_scenario_from_unclear_question"

# 2. 檢查觸發器
psql -c "\d+ unclear_questions" | grep TRIGGER

# 3. 檢查視圖
psql -c "\d+ v_unclear_question_candidates"

# 4. 測試 API
curl http://localhost:8000/api/test/unclear-questions/candidates | jq '.candidates[0].is_high_freq_retry'

# 5. 訪問前端
open http://localhost:8080/review-center
# 切換到「用戶問題」標籤，確認高頻重試徽章顯示
```

---

## 📝 維護建議

### 閾值調整

如需調整重試閾值，修改觸發器函數中的常量：

```sql
DECLARE
    v_high_freq_threshold INTEGER := 5;  -- 改為 10、15 等
```

### 監控指標

建議追蹤以下指標：

1. **重試情境數量**: 每月有多少 rejected 情境被重新創建
2. **重試情境批准率**: 重新創建的情境有多少最終被批准
3. **平均重試頻率**: 通常在什麼頻率觸發重試

### 查詢範例

```sql
-- 查看所有重試情境
SELECT
    id,
    test_question,
    status,
    notes,
    created_at
FROM test_scenarios
WHERE notes LIKE '%原情境%已被拒絕%'
ORDER BY created_at DESC;

-- 統計重試情境批准率
SELECT
    status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM test_scenarios
WHERE notes LIKE '%原情境%已被拒絕%'
GROUP BY status;
```

---

## 👥 相關人員

- **需求提出**: 用戶
- **方案設計**: Claude (AI Assistant)
- **實現開發**: Claude (AI Assistant)
- **測試驗證**: Claude (AI Assistant)

---

## 📅 版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| 1.0.0 | 2025-10-12 | 初始實現：雙閾值重試機制 + 前端視覺提示 |

---

## 🔗 相關文檔

- [Migration 13: Auto-scenario creation trigger](../../migrations_history/13-add-auto-scenario-creation-trigger.sql)
- [Migration 14: Rejected scenario retry logic](../../migrations_history/14-add-rejected-scenario-retry-logic.sql)
- [Migration 15: Update candidates view](../../migrations_history/15-update-candidates-view-for-rejected-scenarios.sql)
- UnclearQuestionReviewTab Component
