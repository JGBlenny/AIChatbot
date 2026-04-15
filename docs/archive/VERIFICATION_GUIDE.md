# 知識完善迴圈 - 驗證測試執行指南

**目標**：驗證知識完善迴圈的核心功能穩定性，確認以下關鍵項目：
1. ✅ 測試集固定性（scenario_ids 儲存與一致性）
2. ✅ 立即同步機制（批准後自動同步到正式庫）
3. ✅ 改善幅度可追蹤（固定測試集下的通過率變化）

---

## 🚀 快速開始

### 選擇測試規模

```bash
# 快速驗證（推薦先執行）
./run_50_verification.sh      # 50 題，10-15 分鐘

# 標準測試
./run_500_verification.sh     # 500 題，60-90 分鐘

# 全面評估（選擇性）
./run_3000_verification.sh    # 3000 題，90-120 分鐘
```

---

## 第一階段：執行第一次迭代

### 1. 設定 OpenAI API Key

```bash
export OPENAI_API_KEY='your-openai-api-key-here'
```

### 2. 選擇測試規模並執行

```bash
# 建議：從 50 題開始
./run_50_verification.sh
```

✅ **說明**：每個腳本都會建立新的 loop，可以重複執行測試不同規模

**預期輸出**：
- 回測 50 題測試情境
- 分析失敗案例並分類
- 生成知識（SOP 或一般知識）
- 儲存到 `loop_generated_knowledge` 表（status = 'pending_review'）

**預計耗時**：10-15 分鐘

### 3. 查詢 Loop ID

```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -t -c \
  "SELECT id FROM knowledge_completion_loops ORDER BY id DESC LIMIT 1;"
```

記錄輸出的 Loop ID，例如：`12`

### 4. 執行快速驗證

```bash
./quick_verification.sh 12  # 替換為實際的 Loop ID
```

**預期檢查項目**：
- ✅ scenario_ids 已儲存（50 題）
- ✅ 回測結果已記錄
- ✅ 知識缺口已分類
- ✅ 知識已生成（待審核）

---

## 第二階段：人工審核

### 選項 A：使用前端審核（推薦）

1. 開啟前端：`http://localhost:5178`
2. 進入「知識審核中心」
3. 選擇「迴圈生成知識」分頁
4. 測試批量審核功能：
   - 使用「全選」功能
   - 點擊「批量批准」
   - 確認操作

**驗證重點**：
- 全選功能是否正常
- 批量批准是否成功
- 是否有錯誤提示

### 選項 B：使用資料庫直接批准（測試用）

```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
UPDATE loop_generated_knowledge
SET status = 'approved', reviewed_at = NOW()
WHERE loop_id = 12 AND status = 'pending_review';
"
```

### 5. 驗證立即同步

執行快速驗證腳本，檢查同步狀態：

```bash
./quick_verification.sh 12
```

**預期結果**：
```
6. ✅ 立即同步檢查
----------------------------------------
knowledge_base 新增: 8
vendor_sop_items 新增: 5
總同步數: 13
已批准數: 13
✅ PASS: 同步數量匹配
```

**驗證 SQL**：
```sql
-- 檢查同步到 knowledge_base
SELECT COUNT(*) FROM knowledge_base
WHERE source = 'loop' AND source_loop_id = 12;

-- 檢查同步到 vendor_sop_items
SELECT COUNT(*) FROM vendor_sop_items
WHERE source = 'loop' AND source_loop_id = 12;
```

---

## 第三階段：執行第二次迭代

### 6. 執行第二次迭代（使用便利腳本）

```bash
./run_next_iteration.sh 12  # 替換為實際的 Loop ID
```

腳本會自動：
- 檢查 Loop 狀態
- 警告是否有待審核知識
- 執行下一次迭代
- 顯示回測結果與成本統計

### 7. 驗證測試集一致性與改善幅度

```bash
./quick_verification.sh 12
```

**預期結果**：
```
8. ✅ 改善幅度分析
----------------------------------------
迭代間通過率變化：
迭代 1: 60.00% (失敗 20 題)
迭代 2: 70.00% (失敗 15 題) [改善 10.00%]
✅ PASS: 可追蹤改善幅度（測試集固定）
```

**關鍵驗證**：
- 兩次迭代的 scenario_ids 必須完全相同
- 通過率變化可清楚追蹤
- 改善幅度 = 新通過率 - 舊通過率

---

## 驗證總結

執行完成後，使用快速驗證腳本產生最終報告：

```bash
./quick_verification.sh 12
```

**通過標準**：
- ✅ 測試集固定性：scenario_ids 儲存正確，兩次迭代使用相同測試集
- ✅ 立即同步：同步數量匹配批准數量
- ✅ 改善幅度可追蹤：通過率變化可量化

**如果所有檢查通過**：
```
🎉 所有檢查通過！可以進入設計階段。
```

執行設計階段：
```bash
/kiro:spec-design backtest-knowledge-refinement -y
```

**如果發現問題**：
```
⚠️  發現 X 個問題，請檢查後再進入設計階段。
```

記錄問題到 `test_verification_log.md`，修復後重新測試。

---

## 故障排除

### 問題 1：OpenAI API Key 未設定
**錯誤**：`❌ 錯誤：未設定 OPENAI_API_KEY 環境變數`

**解決方式**：
```bash
export OPENAI_API_KEY='your-api-key-here'
```

### 問題 2：Docker 容器未運行
**錯誤**：`Cannot connect to the Docker daemon`

**解決方式**：
```bash
docker-compose up -d
```

### 問題 3：資料庫連接失敗
**錯誤**：`psycopg2.OperationalError: could not connect to server`

**檢查方式**：
```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "SELECT 1;"
```

### 問題 4：回測服務無回應
**錯誤**：`Connection refused to http://rag-orchestrator:8100`

**檢查方式**：
```bash
docker logs aichatbot-rag-orchestrator --tail 50
```

---

## 測試記錄

請在測試過程中填寫 `test_verification_log.md`，記錄：
- 基本資訊（Loop ID、開始/結束時間）
- 測試情境選取（scenario_ids 前 10 個）
- 回測結果（通過率、失敗數）
- 知識生成統計
- 審核方式與耗時
- 驗證結果（PASS/FAIL）
- 發現的問題

完整測試記錄將有助於後續分析與改進。
