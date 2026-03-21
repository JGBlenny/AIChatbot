# 批次測試驗證標準

## 通過標準

每個批次必須滿足以下條件才算通過：

### 1. 必要條件（Must Have）

| 指標 | 標準 | 驗證方式 |
|------|------|---------|
| **實際執行** | 每題都調用 RAG API | 檢查 HTTP 狀態碼 = 200 |
| **有召回** | ≥ 50% 測試召回至少 1 個知識點 | `source_count > 0` |
| **有回答** | ≥ 50% 測試有實際回答 | `answer` 不為空 |
| **無錯誤** | < 10% 測試發生異常 | HTTP 錯誤 / Exception |

### 2. 品質標準（Should Have）

| 指標 | 目標 | 優秀 |
|------|------|------|
| 通過率 | ≥ 50% | ≥ 80% |
| 平均召回數 | ≥ 1.5 | ≥ 3.0 |
| 相關性分數 | ≥ 0.6 | ≥ 0.8 |

### 3. 失敗處理

如果批次失敗：

#### 步驟 1：分析失敗原因

```bash
# 查看詳細結果
cat /Users/lenny/jgb/AIChatbot/logs/batch_tests/batch_N_result.json | jq '.results[] | select(.passed == false)'
```

#### 步驟 2：分類問題

- **知識庫問題**：知識點 `answer` 為空 → 補充內容
- **問題表述問題**：測試問題與知識點語義不符 → 調整問題或知識
- **系統問題**：API 錯誤、timeout → 檢查系統狀態

#### 步驟 3：修復後重試

```bash
# 重新執行失敗的批次
./batch_test_runner.sh N
```

### 4. 審計證據

每個批次必須生成：

1. **匯入證據**：`/tmp/batch_N_info.json`
   - 記錄匯入的測試 ID 範圍
   - 記錄實際匯入數量

2. **測試結果**：`/Users/lenny/jgb/AIChatbot/logs/batch_tests/batch_N_result.json`
   - 每題的實際執行結果
   - 召回的知識點
   - 通過/失敗狀態

3. **SQL 驗證**：
   ```sql
   -- 驗證批次 N 的測試狀態
   SELECT 
     expected_category,
     COUNT(*) as 總數,
     COUNT(*) FILTER (WHERE status = 'approved') as 已通過,
     COUNT(*) FILTER (WHERE status = 'pending_review') as 待審核
   FROM test_scenarios
   WHERE notes LIKE 'Batch N:%'
   GROUP BY expected_category;
   ```

### 5. 防偷懶機制

❌ **以下行為視為無效**：

- 未實際調用 RAG API（沒有 HTTP 請求記錄）
- 直接設為 `approved` 而沒有測試結果
- 通過率計算錯誤（與實際結果不符）
- 偽造測試結果（JSON 檔案與資料庫不一致）

✅ **驗證方法**：

```bash
# 1. 檢查是否真的調用了 API（查看 API 日誌）
docker logs aichatbot-rag-orchestrator | grep "batch_test_"

# 2. 比對 JSON 結果與資料庫
psql -c "SELECT COUNT(*) FROM test_scenarios WHERE notes LIKE 'Batch N:%' AND status='approved'"
# 應該等於 JSON 中的 passed 數量

# 3. 隨機抽查 5 題，手動執行驗證
```

## 使用範例

### 執行單一批次
```bash
./batch_test_runner.sh 1
```

### 執行所有批次（1-60）
```bash
./run_all_batches.sh
```

### 執行部分批次（10-20）
```bash
./run_all_batches.sh 10 20
```

### 查看批次結果
```bash
cat /Users/lenny/jgb/AIChatbot/logs/batch_tests/batch_1_result.json | jq '.passed, .failed, .errors'
```
