# 驗證測試腳本使用說明

## 📊 腳本總覽

| 腳本 | 測試題數 | 用途 | 使用次數 | 說明 |
|------|---------|------|---------|------|
| `run_50_verification.sh` | 50 | 快速驗證 | ✅ **可重複** | 建立新 loop（50 題），可多次執行測試不同批次 |
| `run_500_verification.sh` | 500 | 標準測試 | ✅ **可重複** | 建立新 loop（500 題），正式測試流程 |
| `run_3000_verification.sh` | 3000 | 全面評估 | ✅ **可重複** | 建立新 loop（3000 題），大規模測試 |
| `run_next_iteration.sh <loop_id>` | 同 loop | 繼續迭代 | ✅ **可重複** | 繼續現有 loop 的第 2、3、4... 次迭代 |
| `quick_verification.sh <loop_id>` | - | 驗證工具 | ✅ **可重複** | 隨時檢查 loop 狀態，可執行任意次 |

---

## 🔄 完整執行流程

### 第一次迭代（新建 Loop）

```bash
# 1. 設定 API Key（僅需執行一次）
export OPENAI_API_KEY='your-key-here'

# 2. 選擇測試規模並執行第一次迭代
./run_50_verification.sh      # 快速驗證（50 題）
# 或
./run_500_verification.sh     # 標準測試（500 題）
# 或
./run_3000_verification.sh    # 全面評估（3000 題）

# ✅ 輸出：Loop #12 已建立

# 3. 查詢 Loop ID
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -t -c \
  "SELECT id FROM knowledge_completion_loops ORDER BY id DESC LIMIT 1;"
# ✅ 輸出：12

# 4. 驗證執行狀態
./quick_verification.sh 12
```

### 人工審核

```bash
# 方式 A：使用前端審核（推薦）
# 開啟 http://localhost:5178
# 進入「知識審核中心」→「迴圈生成知識」

# 方式 B：資料庫直接批准（測試用）
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
UPDATE loop_generated_knowledge
SET status = 'approved', reviewed_at = NOW()
WHERE loop_id = 12 AND status = 'pending_review';
"

# 驗證同步
./quick_verification.sh 12
```

### 第二次迭代（繼續現有 Loop）

```bash
# 執行第二次迭代（使用同一個 Loop ID）
./run_next_iteration.sh 12

# 驗證改善幅度
./quick_verification.sh 12
```

### 第三次迭代（如需要）

```bash
# 審核第二次迭代的知識...

# 執行第三次迭代
./run_next_iteration.sh 12

# 驗證
./quick_verification.sh 12
```

---

## ⚠️ 常見誤解

### 誤解 1：不能重複執行 run_XXX_verification.sh？

**❌ 錯誤理解**：「執行一次後就不能再用了」

**✅ 正確理解**：可以重複執行，每次都會建立新的獨立 loop

```bash
./run_50_verification.sh  # Loop #12（50 題）
./run_50_verification.sh  # Loop #13（另一組 50 題）✅ 可以！
./run_500_verification.sh # Loop #14（500 題）✅ 可以！
```

**使用場景**：
- 測試不同規模（50 → 500 → 3000）
- 驗證穩定性（重複測試多次）
- 測試不同配置（修改目標通過率）

### 誤解 2：loop 完成後要修改代碼才能測新規模？

**❌ 錯誤做法**：修改 Python 代碼的 batch_size

**✅ 正確做法**：直接執行不同的腳本

```bash
# Loop #12（50 題）已達標
./quick_verification.sh 12
# 輸出：status = "COMPLETED"，通過率 86%

# 想測試 500 題？直接執行！
./run_500_verification.sh  # 建立 Loop #13（500 題）
```

### 正確的迭代流程

**單一 Loop 的多次迭代**：
```bash
./run_50_verification.sh      # Loop #12（第 1 次迭代）
# 審核...
./run_next_iteration.sh 12    # Loop #12（第 2 次迭代）
# 審核...
./run_next_iteration.sh 12    # Loop #12（第 3 次迭代）
```

**多個 Loop 的測試計劃**：
```bash
./run_50_verification.sh      # Loop #12（50 題驗證）
# Loop #12 完成後...

./run_500_verification.sh     # Loop #13（500 題測試）
# Loop #13 完成後...

./run_3000_verification.sh    # Loop #14（3000 題評估）
```

---

## 📝 腳本詳細說明

### 1. run_50_verification.sh

**功能**：建立新的知識完善迴圈並執行第一次迭代

**何時使用**：
- ✅ 開始新的 50 題驗證測試
- ✅ 開始新的 500 題測試（需修改 config.batch_size）
- ❌ 不要用於繼續現有測試

**執行內容**：
1. 檢查 OpenAI API Key
2. 進入 rag-orchestrator 容器
3. 執行 `run_first_loop.py`
4. 建立新的 `knowledge_completion_loops` 記錄
5. 執行回測、分析、生成知識

**參數**：無

### 2. run_next_iteration.sh

**功能**：執行指定 loop 的下一次迭代

**何時使用**：
- ✅ 執行第 2、3、4... 次迭代
- ✅ 繼續現有 loop 的測試
- ❌ 不要用於第一次迭代（會出錯）

**執行內容**：
1. 檢查 OpenAI API Key
2. 查詢 Loop 目前狀態
3. 檢查待審核知識數量（若有則警告）
4. 執行下一次迭代
5. 使用相同的 scenario_ids（從第一次迭代儲存的）

**參數**：
- `<loop_id>`：必填，要繼續的 Loop ID

**範例**：
```bash
./run_next_iteration.sh 12
./run_next_iteration.sh 15
```

### 3. quick_verification.sh

**功能**：快速驗證 loop 執行狀態與資料完整性

**何時使用**：
- ✅ 第一次迭代後
- ✅ 審核完成後
- ✅ 每次迭代後
- ✅ 隨時想檢查狀態時

**執行內容**：
1. 顯示 Loop 基本資訊
2. ✅ 檢查測試集固定性（scenario_ids）
3. 顯示回測結果統計
4. 顯示知識缺口分類
5. 顯示知識生成統計
6. ✅ 檢查立即同步（同步數量匹配）
7. 顯示執行日誌
8. ✅ 分析改善幅度（多次迭代時）
9. 輸出驗證總結（PASS/FAIL）

**參數**：
- `<loop_id>`：必填，要驗證的 Loop ID

**範例**：
```bash
./quick_verification.sh 12
./quick_verification.sh 15
```

**輸出範例**：
```
========================================
驗證總結
========================================

✅ 測試集固定性：PASS
✅ 立即同步：PASS
✅ 改善幅度可追蹤：PASS

🎉 所有檢查通過！可以進入設計階段。
```

---

## 💡 使用建議

### 場景 1：第一次測試（完整流程）

```bash
# 執行第一次迭代
./run_50_verification.sh

# 獲取 Loop ID
LOOP_ID=$(docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -t -c \
  "SELECT id FROM knowledge_completion_loops ORDER BY id DESC LIMIT 1;" | xargs)

echo "Loop ID: $LOOP_ID"

# 驗證
./quick_verification.sh $LOOP_ID

# 人工審核...

# 執行第二次迭代
./run_next_iteration.sh $LOOP_ID

# 再次驗證
./quick_verification.sh $LOOP_ID
```

### 場景 2：調試時檢查狀態

```bash
# 隨時查看狀態
./quick_verification.sh 12

# 檢查待審核知識
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "SELECT COUNT(*) FROM loop_generated_knowledge WHERE loop_id = 12 AND status = 'pending_review';"

# 再次驗證
./quick_verification.sh 12
```

### 場景 3：多次迭代測試

```bash
# 第一次
./run_50_verification.sh
LOOP_ID=12

# 第二次
./run_next_iteration.sh $LOOP_ID
./quick_verification.sh $LOOP_ID

# 第三次
./run_next_iteration.sh $LOOP_ID
./quick_verification.sh $LOOP_ID

# 第四次
./run_next_iteration.sh $LOOP_ID
./quick_verification.sh $LOOP_ID
```

---

## 🎯 記憶重點

1. **`run_50_verification.sh`** = 建立新 loop（只用一次）
2. **`run_next_iteration.sh`** = 繼續現有 loop（可重複）
3. **`quick_verification.sh`** = 檢查狀態（隨時可用）

**簡化記憶**：
- 第一次：`run_50_verification.sh`
- 第 N 次：`run_next_iteration.sh <loop_id>`
- 檢查：`quick_verification.sh <loop_id>`
