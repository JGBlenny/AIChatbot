# 語義相似度與測試情境管理 - 綜合測試計劃

## 測試目標

驗證以下核心功能：
1. ✅ 語義相似度自動判斷與頻率累加
2. ✅ 語義不同問題的獨立處理
3. ✅ 防止重複建立測試情境
4. ✅ 測試情境審核流程
5. ✅ 邊界情況與錯誤處理

## 測試環境

- RAG Orchestrator: Docker container
- PostgreSQL + pgvector: v16
- Embedding API: OpenAI text-embedding-ada-002
- 語義相似度閾值: 0.85

## 測試案例總覽

| 測試組 | 測試案例數 | 目的 |
|-------|----------|------|
| A. 語義相似度測試 | 8 | 驗證相同意思不同說法的合併 |
| B. 語義差異測試 | 6 | 驗證不同意思問題的獨立處理 |
| C. 防重複建立測試 | 7 | 驗證各狀態下的防重複機制 |
| D. 審核流程測試 | 5 | 驗證完整審核工作流程 |
| E. 邊界情況測試 | 4 | 驗證極端情況和錯誤處理 |
| **總計** | **30** | - |

---

## A. 語義相似度測試（相同意思不同說法）

### 測試目標
驗證語義相似的問題會累加到同一個 `unclear_question` 記錄。

### 測試案例

#### A1: 寵物飼養 - 基本變體
| # | 輸入問題 | 預期 unclear_question_id | 預期頻率 | 預期匹配類型 |
|---|---------|------------------------|---------|-------------|
| 1 | 可以養寵物嗎 | 新建（ID: X） | 1 | 新問題 |
| 2 | 我可以養寵物嗎 | X | 2 | 語義相似 |
| 3 | 我想養寵物 | X | 3 | 語義相似 |
| 4 | 能養寵物嗎 | X | 4 | 語義相似 |
| 5 | 我要養寵物 | X | 5 | 語義相似 |

**預期相似度範圍：** 0.85 - 0.95

#### A2: 繳費時間 - 語序變化
| # | 輸入問題 | 預期 unclear_question_id | 預期頻率 | 預期匹配類型 |
|---|---------|------------------------|---------|-------------|
| 1 | 什麼時候要繳房租 | 新建（ID: Y） | 1 | 新問題 |
| 2 | 房租什麼時候繳 | Y | 2 | 語義相似 |
| 3 | 繳房租的時間是什麼時候 | Y | 3 | 語義相似 |
| 4 | 租金何時繳納 | Y | 4 | 語義相似 |

**預期相似度範圍：** 0.85 - 0.92

---

## B. 語義差異測試（相關主題但意思不同）

### 測試目標
驗證語義不同的問題會建立獨立的 `unclear_question` 記錄。

### 測試案例

#### B1: 寵物主題 - 不同面向的問題
| # | 輸入問題 | 預期結果 | 相似度（與「可以養寵物嗎」） |
|---|---------|---------|---------------------------|
| 1 | 可以養寵物嗎 | 新建 unclear_question #A | - |
| 2 | 養寵物要繳押金嗎 | 新建 unclear_question #B | < 0.75 |
| 3 | 寵物可以進電梯嗎 | 新建 unclear_question #C | < 0.70 |
| 4 | 寵物可以帶去公設嗎 | 新建 unclear_question #D | < 0.70 |
| 5 | 養寵物有什麼規定 | 新建 unclear_question #E | < 0.75 |

#### B2: 繳費主題 - 不同面向的問題
| # | 輸入問題 | 預期結果 | 相似度（與「什麼時候繳房租」） |
|---|---------|---------|------------------------------|
| 1 | 什麼時候要繳房租 | 新建 unclear_question #F | - |
| 2 | 房租多少錢 | 新建 unclear_question #G | < 0.70 |
| 3 | 如何繳房租 | 新建 unclear_question #H | < 0.75 |
| 4 | 房租可以延期嗎 | 新建 unclear_question #I | < 0.70 |
| 5 | 逾期繳房租會怎樣 | 新建 unclear_question #J | < 0.70 |

---

## C. 防重複建立測試

### 測試目標
驗證同一個 `unclear_question` 在不同狀態下的防重複機制。

### 測試案例

#### C1: pending_review 狀態
```sql
-- 前置：unclear_question #X 頻率 >= 2
-- 操作 1：首次建立
SELECT create_test_scenario_from_unclear_question(X, '寵物相關', 'medium', 'admin');

-- 預期：成功建立 test_scenario #T1 (status: pending_review)
-- 返回：T1

-- 操作 2：立即重複建立
SELECT create_test_scenario_from_unclear_question(X, '寵物相關', 'easy', 'admin2');

-- 預期：返回現有 ID，不建立新記錄
-- 返回：T1
-- NOTICE：測試情境已存在且待審核中: test_scenario #T1, 直接返回
```

#### C2: approved 狀態
```sql
-- 前置：test_scenario #T1 已審核通過
UPDATE test_scenarios SET status = 'approved' WHERE id = T1;

-- 操作：嘗試重複建立
SELECT create_test_scenario_from_unclear_question(X, '寵物相關', 'hard', 'admin3');

-- 預期：拋出異常，不允許重複建立
-- ERROR：測試情境已審核通過: test_scenario #T1, 無需重複建立
```

#### C3: rejected 狀態（未重新開啟）
```sql
-- 前置：test_scenario #T1 已被拒絕
UPDATE test_scenarios SET status = 'rejected' WHERE id = T1;

-- 操作：嘗試重複建立
SELECT create_test_scenario_from_unclear_question(X, '寵物相關', 'medium', 'admin4');

-- 預期：拋出異常，提示需要重新開啟
-- ERROR：測試情境已被拒絕: test_scenario #T1.
--        如需重新審核，請先將該記錄狀態改為 draft 或直接刪除舊記錄。
```

#### C4: rejected 狀態（重新開啟後）
```sql
-- 前置：test_scenario #T1 已被拒絕
UPDATE test_scenarios SET status = 'rejected' WHERE id = T1;

-- 操作 1：重新開啟審核
SELECT reopen_rejected_test_scenario(T1, 'manager');

-- 預期：成功重新開啟
-- 返回：TRUE
-- 狀態：test_scenario #T1 (status: pending_review)

-- 操作 2：嘗試再次建立
SELECT create_test_scenario_from_unclear_question(X, '寵物相關', 'medium', 'admin5');

-- 預期：返回現有 ID（因為已重新開啟，狀態為 pending_review）
-- 返回：T1
-- NOTICE：測試情境已存在且待審核中: test_scenario #T1, 直接返回
```

#### C5: 多個 unclear_question，各自獨立
```sql
-- 前置：
-- unclear_question #A: "可以養寵物嗎" (freq: 3)
-- unclear_question #B: "養寵物要繳押金嗎" (freq: 2)

-- 操作 1：建立 A 的測試情境
SELECT create_test_scenario_from_unclear_question(A, '寵物相關', 'medium', 'admin');
-- 預期：test_scenario #T1 (source_question_id: A)

-- 操作 2：建立 B 的測試情境
SELECT create_test_scenario_from_unclear_question(B, '寵物相關', 'medium', 'admin');
-- 預期：test_scenario #T2 (source_question_id: B)

-- 操作 3：驗證兩者獨立
SELECT id, source_question_id, status FROM test_scenarios WHERE id IN (T1, T2);
-- 預期：兩筆獨立記錄，互不影響
```

#### C6: 檢視重複記錄
```sql
-- 操作：查詢是否有重複的 source_question_id
SELECT * FROM v_duplicate_test_scenarios;

-- 預期（正常情況）：無記錄（或只有測試期間故意建立的重複）
-- 預期（異常情況）：顯示有重複的記錄，需要手動處理
```

#### C7: 頻率增加後的行為
```sql
-- 前置：
-- unclear_question #X (freq: 2) → test_scenario #T1 (status: rejected)

-- 操作 1：頻率持續增加（用戶繼續問類似問題）
-- 輸入語義相似問題，頻率從 2 → 5 → 10

-- 操作 2：檢視是否需要重新評估
SELECT
    ts.id AS scenario_id,
    ts.status,
    ts.reviewed_at,
    uq.frequency AS current_frequency,
    uq.frequency - 2 AS frequency_increase
FROM test_scenarios ts
JOIN unclear_questions uq ON ts.source_question_id = uq.id
WHERE ts.source_question_id = X;

-- 預期：顯示頻率大幅增加（如從 2 增加到 10）

-- 操作 3：重新開啟審核
SELECT reopen_rejected_test_scenario(T1, 'manager');

-- 預期：成功重新開啟，再次出現在審核中心
```

---

## D. 審核流程測試

### 測試目標
驗證完整的測試情境審核工作流程。

### 測試案例

#### D1: 完整審核流程 - 批准路徑
```
步驟 1: 用戶輸入問題
   輸入: "可以養寵物嗎" × 3 次（語義相似）
   結果: unclear_question #X (freq: 3)

步驟 2: 轉換為測試情境
   SQL: SELECT create_test_scenario_from_unclear_question(X, '寵物相關', 'medium', 'admin');
   結果: test_scenario #T1 (status: pending_review)

步驟 3: 審核中心顯示
   API: GET /api/test/scenarios/pending
   預期: 回傳包含 T1 的列表

步驟 4: 審核批准
   API: POST /api/test/scenarios/T1/approve
   Body: {"reviewed_by": "manager", "notes": "測試情境清晰明確"}
   預期: 成功更新狀態

步驟 5: 驗證狀態
   SQL: SELECT id, status, reviewed_by, reviewed_at FROM test_scenarios WHERE id = T1;
   預期: status='approved', reviewed_by='manager', reviewed_at 不為 NULL

步驟 6: 驗證不再出現在審核中心
   API: GET /api/test/scenarios/pending
   預期: 列表中不包含 T1
```

#### D2: 完整審核流程 - 拒絕路徑
```
步驟 1-2: 同 D1

步驟 3: 審核拒絕
   API: POST /api/test/scenarios/T1/reject
   Body: {"reviewed_by": "manager", "notes": "問題不夠明確"}
   預期: 成功更新狀態

步驟 4: 驗證狀態
   SQL: SELECT id, status, review_notes FROM test_scenarios WHERE id = T1;
   預期: status='rejected', review_notes='問題不夠明確'

步驟 5: 驗證不再出現在審核中心
   API: GET /api/test/scenarios/pending
   預期: 列表中不包含 T1

步驟 6: 驗證在測試題庫中可見（使用狀態篩選）
   API: GET /api/test/scenarios?status=rejected
   預期: 列表中包含 T1
```

#### D3: 重新開啟審核流程
```
步驟 1: 前置條件
   test_scenario #T1 (status: rejected, freq: 2)

步驟 2: 頻率增加
   用戶繼續詢問類似問題
   unclear_question #X: freq 2 → 10

步驟 3: 重新開啟審核
   SQL: SELECT reopen_rejected_test_scenario(T1, 'manager');
   預期: 返回 TRUE

步驟 4: 驗證狀態變更
   SQL: SELECT id, status, reviewed_by, reviewed_at FROM test_scenarios WHERE id = T1;
   預期:
   - status='pending_review'
   - reviewed_by=NULL
   - reviewed_at=NULL

步驟 5: 驗證再次出現在審核中心
   API: GET /api/test/scenarios/pending
   預期: 列表中包含 T1

步驟 6: 驗證 review_notes 記錄重新開啟歷史
   SQL: SELECT review_notes FROM test_scenarios WHERE id = T1;
   預期: 包含 "[YYYY-MM-DD HH:MM:SS] 由 manager 重新開啟審核"
```

#### D4: 批量審核（多個測試情境）
```
步驟 1: 建立多個測試情境
   unclear_question #A, #B, #C → test_scenarios #T1, #T2, #T3

步驟 2: 批准 T1
   API: POST /api/test/scenarios/T1/approve

步驟 3: 拒絕 T2
   API: POST /api/test/scenarios/T2/reject

步驟 4: 保持 T3 為 pending_review

步驟 5: 驗證審核中心只剩 T3
   API: GET /api/test/scenarios/pending
   預期: 只包含 T3

步驟 6: 驗證統計正確
   API: GET /api/test/stats
   預期:
   - pending_review_count: 1
   - approved: >=1 (包含 T1)
   - rejected: >=1 (包含 T2)
```

#### D5: 審核權限與審核者追蹤
```
步驟 1: 不同審核者審核不同測試情境
   T1: reviewed_by='admin_a'
   T2: reviewed_by='manager_b'
   T3: reviewed_by='admin_a'

步驟 2: 查詢各審核者的審核統計
   SQL:
   SELECT
       reviewed_by,
       COUNT(*) as total,
       SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) as approved,
       SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) as rejected
   FROM test_scenarios
   WHERE reviewed_by IS NOT NULL
   GROUP BY reviewed_by;

   預期: 顯示各審核者的審核數據
```

---

## E. 邊界情況與錯誤處理測試

### 測試目標
驗證系統在極端情況和錯誤條件下的穩定性。

### 測試案例

#### E1: 頻率未達閾值
```sql
-- 前置：unclear_question #X (freq: 1) ← 未達閾值 2

-- 操作：嘗試建立測試情境
SELECT create_test_scenario_from_unclear_question(X, '分類', 'medium', 'admin');

-- 預期：可以建立（沒有頻率檢查）
-- 注意：頻率檢查在 v_unclear_question_candidates 視圖中，不在函數內

-- 建議：前端應該只允許從 v_unclear_question_candidates 中選擇
```

#### E2: 不存在的 unclear_question_id
```sql
-- 操作：使用不存在的 ID
SELECT create_test_scenario_from_unclear_question(99999, '分類', 'medium', 'admin');

-- 預期：拋出異常
-- ERROR: Unclear question not found: 99999
```

#### E3: 重新開啟非 rejected 狀態的測試情境
```sql
-- 前置：test_scenario #T1 (status: approved)

-- 操作：嘗試重新開啟
SELECT reopen_rejected_test_scenario(T1, 'manager');

-- 預期：拋出異常
-- ERROR: 只能重新開啟狀態為 rejected 的測試情境，當前狀態: approved
```

#### E4: Embedding API 失敗時的 fallback
```
步驟 1: 模擬 Embedding API 失敗（停止服務）
   docker stop aichatbot-embedding-api

步驟 2: 輸入問題
   API: POST /api/v1/chat
   Body: {"question": "測試問題", "user_id": "test"}

步驟 3: 驗證 fallback 機制
   預期:
   - 顯示警告: "⚠️ 無法生成問題向量，回退到精確匹配模式"
   - 仍然建立 unclear_question（只使用精確匹配，不使用語義相似度）
   - 系統不中斷

步驟 4: 恢復服務
   docker start aichatbot-embedding-api

步驟 5: 驗證恢復正常
   再次輸入問題，應該正常生成 embedding
```

---

## 測試執行順序

### Phase 1: 基礎功能驗證
1. 執行 A1: 語義相似度基本測試
2. 執行 B1: 語義差異基本測試
3. 驗證 unclear_questions 表的正確性

### Phase 2: 防重複機制驗證
4. 執行 C1-C4: 各狀態下的防重複測試
5. 執行 C5: 多問題獨立性測試
6. 執行 C6: 重複記錄檢查

### Phase 3: 審核流程驗證
7. 執行 D1-D2: 基本審核流程
8. 執行 D3: 重新開啟流程
9. 執行 D4-D5: 批量與追蹤

### Phase 4: 邊界與錯誤處理
10. 執行 E1-E4: 所有邊界情況

### Phase 5: 壓力測試（可選）
11. 大量並發輸入相似問題
12. 快速連續建立測試情境
13. 長時間運行穩定性測試

---

## 測試數據準備

### 預設測試問題集

#### 主題 1: 寵物飼養
```
語義相似組 A:
- 可以養寵物嗎
- 我可以養寵物嗎
- 我想養寵物
- 能養寵物嗎
- 我要養寵物
- 可不可以養寵物
- 允許養寵物嗎

語義不同組:
- 養寵物要繳押金嗎
- 寵物可以進電梯嗎
- 寵物可以帶去公設嗎
- 養寵物有什麼規定
```

#### 主題 2: 租金繳納
```
語義相似組 B:
- 什麼時候要繳房租
- 房租什麼時候繳
- 繳房租的時間是什麼時候
- 租金何時繳納
- 繳租日期是哪天

語義不同組:
- 房租多少錢
- 如何繳房租
- 房租可以延期嗎
- 逾期繳房租會怎樣
- 房租包含什麼費用
```

#### 主題 3: 設施使用
```
語義相似組 C:
- 健身房在哪裡
- 健身房位置
- 請問健身房怎麼去
- 健身房的地點

語義不同組:
- 健身房開放時間
- 健身房需要預約嗎
- 健身房有什麼器材
- 健身房使用規定
```

---

## 測試腳本結構

### 自動化測試腳本

```bash
#!/bin/bash
# test_comprehensive.sh

# 測試配置
export RAG_API="http://localhost:8100"
export ADMIN_API="http://localhost:8000"
export TEST_USER="test_user_$(date +%s)"

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 測試計數器
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 測試函數
run_test() {
    local test_name=$1
    local test_command=$2
    local expected_result=$3

    echo -e "\n${YELLOW}執行測試: ${test_name}${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    # 執行測試
    result=$(eval $test_command)

    # 驗證結果
    if [[ "$result" == *"$expected_result"* ]]; then
        echo -e "${GREEN}✅ 通過${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}❌ 失敗${NC}"
        echo "預期: $expected_result"
        echo "實際: $result"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# Phase 1: 語義相似度測試
echo "=== Phase 1: 語義相似度測試 ==="

# A1-1: 首次輸入
run_test "A1-1: 首次輸入問題" \
    "curl -s -X POST $RAG_API/api/v1/chat -H 'Content-Type: application/json' -d '{\"question\": \"可以養寵物嗎\", \"user_id\": \"$TEST_USER\"}' | jq -r '.unclear_question_id'" \
    "[0-9]+"

# ... 更多測試案例

# 輸出測試總結
echo -e "\n========================================="
echo -e "測試總結"
echo -e "========================================="
echo -e "總測試數: $TOTAL_TESTS"
echo -e "${GREEN}通過: $PASSED_TESTS${NC}"
echo -e "${RED}失敗: $FAILED_TESTS${NC}"
echo -e "通過率: $((PASSED_TESTS * 100 / TOTAL_TESTS))%"
```

---

## 測試報告模板

### 測試執行記錄

```
測試日期: YYYY-MM-DD HH:MM:SS
測試環境: Docker Desktop / MacOS / PostgreSQL 16
執行者: [Your Name]

=== Phase 1: 語義相似度測試 ===
A1-1: 首次輸入問題                    ✅ 通過 (unclear_question_id: 26)
A1-2: 語義相似問題 #1                 ✅ 通過 (相似度: 0.8632, 累加頻率: 2)
A1-3: 語義相似問題 #2                 ✅ 通過 (相似度: 0.8791, 累加頻率: 3)
A1-4: 語義相似問題 #3                 ✅ 通過 (相似度: 0.8912, 累加頻率: 4)
...

總結: 8/8 通過

=== Phase 2: 語義差異測試 ===
B1-1: 不同面向問題 #1                 ✅ 通過 (新建 unclear_question_id: 27)
B1-2: 不同面向問題 #2                 ✅ 通過 (新建 unclear_question_id: 28)
...

總結: 6/6 通過

=== 最終統計 ===
總測試案例: 30
通過: 28
失敗: 2
通過率: 93.3%

失敗案例分析:
- C3: rejected 狀態重複建立 - 錯誤訊息格式不符預期（已修正）
- E4: Embedding API fallback - 未正確顯示警告訊息（待修正）
```

---

## 驗證檢查清單

### 資料庫完整性檢查

```sql
-- ✅ 檢查 1: 沒有重複的 source_question_id (pending_review 或 approved)
SELECT * FROM v_duplicate_test_scenarios;
-- 預期: 0 筆記錄

-- ✅ 檢查 2: 所有 test_scenario 的 source_question_id 都存在
SELECT ts.id, ts.source_question_id
FROM test_scenarios ts
LEFT JOIN unclear_questions uq ON ts.source_question_id = uq.id
WHERE ts.source_question_id IS NOT NULL
  AND uq.id IS NULL;
-- 預期: 0 筆記錄

-- ✅ 檢查 3: 所有 pending_review 的記錄都在視圖中
SELECT COUNT(*) FROM test_scenarios WHERE status = 'pending_review';
SELECT COUNT(*) FROM v_pending_test_scenarios;
-- 預期: 兩個數字相同

-- ✅ 檢查 4: 已審核記錄的必填欄位完整
SELECT id, status
FROM test_scenarios
WHERE status IN ('approved', 'rejected')
  AND (reviewed_by IS NULL OR reviewed_at IS NULL);
-- 預期: 0 筆記錄

-- ✅ 檢查 5: 語義相似度記錄完整（有 embedding）
SELECT COUNT(*) FROM unclear_questions WHERE frequency >= 2 AND question_embedding IS NULL;
-- 預期: 0 或極少數（僅限 embedding API 失敗的情況）
```

---

## 測試工具

### SQL 輔助查詢

```sql
-- 查看測試期間建立的所有記錄
SELECT
    'unclear_questions' AS table_name,
    id,
    question AS description,
    frequency,
    created_at
FROM unclear_questions
WHERE created_at >= NOW() - INTERVAL '1 hour'
UNION ALL
SELECT
    'test_scenarios' AS table_name,
    id,
    test_question AS description,
    NULL AS frequency,
    created_at
FROM test_scenarios
WHERE created_at >= NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;

-- 清理測試資料
DELETE FROM test_scenarios WHERE created_at >= NOW() - INTERVAL '1 hour' AND created_by LIKE 'test_%';
DELETE FROM unclear_questions WHERE created_at >= NOW() - INTERVAL '1 hour' AND user_id LIKE 'test_%';
```

---

## 附錄

### 相關文件
- `SEMANTIC_SIMILARITY_TEST_REPORT.md` - 語義相似度實作報告
- `DUPLICATE_TEST_SCENARIO_PREVENTION.md` - 防重複機制說明
- `SEMANTIC_VS_CATEGORY_GROUPING.md` - 語義相似度 vs 類別分組
- `TEST_SCENARIO_STATUS_MANAGEMENT.md` - 狀態管理說明

### 測試資料位置
- 測試腳本: `tests/test_comprehensive.sh`
- 測試結果: `tests/results/test_report_[timestamp].md`
- 測試資料備份: `tests/data/test_data_[timestamp].sql`

---

**文件版本：** v1.0.0
**建立日期：** 2025-10-11
**最後更新：** 2025-10-11
**維護者：** Claude
