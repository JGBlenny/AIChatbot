# 📦 知識完善迴圈系統部署指南

> **部署日期**: 2026-03-27
> **版本**: backtest-knowledge-refinement v1.0
> **風險等級**: 🟡 中風險（新增資料庫欄位、新增 API 路由）
> **預計停機時間**: < 2 分鐘

---

## 📋 概述

### 主要更新

本次部署新增**知識完善迴圈系統**的完整功能，包含：

1. **迴圈管理 API**：啟動、執行迭代、暫停、恢復、取消、完成批次
2. **知識審核 API**：待審核列表、單一審核、批量審核、重複檢測
3. **非同步執行架構**：長時間迭代任務的背景執行機制
4. **固定測試集保證**：確保同一迴圈的所有迭代使用相同測試情境
5. **批次間避免重複**：自動排除已使用的測試情境
6. **成本追蹤與控制**：OpenAI API 成本監控與預算限制

### 涵蓋範圍

- ✅ **後端 API**：`/api/v1/loops/*` 和 `/api/v1/loop-knowledge/*`
- ✅ **資料庫架構**：補充缺失欄位、新增索引、建立 `knowledge_gap_analysis` 表
- ✅ **服務層**：`AsyncExecutionManager`、`ScenarioSelector`、`LoopCoordinator` 擴展
- ⚠️  **前端介面**：需後續開發（已提供 API 文檔與需求規格）

---

## 🚀 快速部署

### 前置條件

- Docker 與 Docker Compose 已安裝
- PostgreSQL 14+ with pgvector
- Python 3.9+
- OpenAI API Key（已配置在環境變數）
- Embedding API 已啟動（`http://localhost:5001`）

### 快速執行腳本

```bash
# 1. 備份資料庫（必須！）
docker exec aichatbot-postgres pg_dump -U aichatbot -d aichatbot > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. 執行資料庫 Migration
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot < database/migrations/add_loop_features.sql

# 3. 重啟服務（載入新路由）
docker-compose restart rag-orchestrator

# 4. 驗證部署
curl http://localhost:8100/health
```

---

## 📦 詳細部署步驟

### Step 1: 備份資料庫 ⚠️ 必須

```bash
# 方法 1: Docker 內部備份
docker exec aichatbot-postgres pg_dump -U aichatbot -d aichatbot > backup_$(date +%Y%m%d_%H%M%S).sql

# 方法 2: 使用 Migration 自動備份
./database/run_migrations.sh docker-compose.yml
```

**驗證備份**：
```bash
ls -lh backup_*.sql
# 確保檔案大小 > 1MB
```

---

### Step 2: 執行資料庫 Migration

#### 使用自動化腳本（推薦）

```bash
# 預覽變更（Dry-run）
./database/run_migrations.sh docker-compose.yml --dry-run

# 執行 Migration（自動備份）
./database/run_migrations.sh docker-compose.yml

# 交互式執行（需要確認）
./database/run_migrations.sh docker-compose.yml --interactive
```

#### 手動執行

```bash
# 進入 PostgreSQL 容器
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot < database/migrations/add_loop_features.sql
```

#### Migration 內容說明

**1. knowledge_completion_loops 表補充欄位**：
- `scenario_ids` (INTEGER[]): 固定測試集 ID 列表
- `selection_strategy` (VARCHAR): 選取策略（stratified_random/sequential/full_random）
- `difficulty_distribution` (JSONB): 難度分布統計
- `parent_loop_id` (INTEGER): 父迴圈 ID（批次關聯）
- `max_iterations` (INTEGER): 最大迭代次數

**2. loop_generated_knowledge 表補充欄位**：
- `similar_knowledge` (JSONB): 重複檢測結果
- `duplication_warning` (VARCHAR): 重複警告文字
- `knowledge_type` (VARCHAR): 知識類型（sop/null）
- `sop_config` (JSONB): SOP 配置

**3. 建立 knowledge_gap_analysis 表**（如果不存在）：
- 記錄失敗測試案例的分類與聚類結果
- 支援智能分類（OpenAI）與知識生成

**4. 建立索引**：
- GIN 索引：`scenario_ids`（加速測試集查詢）
- B-tree 索引：`parent_loop_id`（批次關聯查詢）
- 複合索引：`(loop_id, iteration)`（知識缺口分析）

---

### Step 3: 驗證 Migration 結果

```bash
# 檢查新欄位
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot -c "
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'knowledge_completion_loops'
  AND column_name IN ('scenario_ids', 'selection_strategy', 'difficulty_distribution', 'parent_loop_id', 'max_iterations');
"

# 檢查索引
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot -c "
SELECT indexname
FROM pg_indexes
WHERE tablename = 'knowledge_completion_loops'
  AND indexname IN ('idx_loops_scenario_ids', 'idx_loops_parent');
"

# 檢查 knowledge_gap_analysis 表
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot -c "
SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'knowledge_gap_analysis';
"
```

**預期輸出**：
- 5 個新欄位存在
- 2 個新索引存在
- `knowledge_gap_analysis` 表存在

---

### Step 4: 重啟服務

```bash
# 僅重啟 rag-orchestrator（無需重建）
docker-compose restart rag-orchestrator

# 查看啟動日誌
docker-compose logs -f rag-orchestrator | head -50
```

**預期日誌**：
```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

### Step 5: 驗證 API 端點

```bash
# 健康檢查
curl http://localhost:8100/health

# 測試迴圈管理 API（列出迴圈）
curl -X GET http://localhost:8100/api/v1/loops \
  -H "Content-Type: application/json"

# 測試知識審核 API（查詢待審核知識）
curl -X GET "http://localhost:8100/api/v1/loop-knowledge/pending?vendor_id=2&limit=10" \
  -H "Content-Type: application/json"
```

**預期回應**：
- `/health`: `{"status": "healthy"}`
- `/api/v1/loops`: 迴圈列表（可能為空陣列）
- `/api/v1/loop-knowledge/pending`: 待審核知識列表

---

## 🧪 功能測試

### 測試 1: 啟動迴圈

```bash
curl -X POST http://localhost:8100/api/v1/loops/start \
  -H "Content-Type: application/json" \
  -d '{
    "loop_name": "測試迴圈 2026-03-27",
    "vendor_id": 2,
    "batch_size": 50,
    "max_iterations": 10,
    "target_pass_rate": 0.85
  }'
```

**預期回應**（200 OK）：
```json
{
  "loop_id": 1,
  "loop_name": "測試迴圈 2026-03-27",
  "vendor_id": 2,
  "status": "pending",
  "scenario_ids": [1, 2, 3, ..., 50],
  "scenario_selection_strategy": "stratified_random",
  "difficulty_distribution": {"easy": 10, "medium": 25, "hard": 15},
  "initial_statistics": {...},
  "created_at": "2026-03-27T00:00:00Z"
}
```

---

### 測試 2: 執行迭代（非同步模式）

```bash
curl -X POST http://localhost:8100/api/v1/loops/1/execute-iteration \
  -H "Content-Type: application/json" \
  -d '{
    "async_mode": true
  }'
```

**預期回應**（202 Accepted）：
```json
{
  "loop_id": 1,
  "current_iteration": 1,
  "status": "running",
  "message": "迭代已在背景執行",
  "execution_task_id": "task_1_1711497600.0"
}
```

---

### 測試 3: 查詢迴圈狀態

```bash
# 前端輪詢使用（每 5 秒）
curl -X GET http://localhost:8100/api/v1/loops/1 \
  -H "Content-Type: application/json"
```

**預期回應**（200 OK）：
```json
{
  "loop_id": 1,
  "loop_name": "測試迴圈 2026-03-27",
  "vendor_id": 2,
  "status": "backtesting",  // 或 analyzing, generating, reviewing
  "current_iteration": 1,
  "max_iterations": 10,
  "current_pass_rate": null,
  "target_pass_rate": 0.85,
  "scenario_ids": [1, 2, ..., 50],
  "total_scenarios": 50,
  "progress": {
    "phase": "backtest",
    "percentage": 45.0,
    "message": "正在測試第 23 個情境..."
  },
  "created_at": "2026-03-27T00:00:00Z",
  "updated_at": "2026-03-27T00:05:00Z",
  "completed_at": null
}
```

---

### 測試 4: 批量審核知識

```bash
curl -X POST http://localhost:8100/api/v1/loop-knowledge/batch-review \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_ids": [1, 2, 3, 4, 5],
    "action": "approve"
  }'
```

**預期回應**（200 OK）：
```json
{
  "total": 5,
  "successful": 5,
  "failed": 0,
  "failed_items": [],
  "duration_ms": 3500
}
```

---

## 🔧 環境變數配置

### 必要環境變數

確保以下環境變數已正確設定：

```bash
# OpenAI API（知識分類、生成）
OPENAI_API_KEY=sk-...

# Embedding API（重複檢測）
EMBEDDING_API_URL=http://localhost:5001/api/v1/embeddings

# 資料庫連接
DB_HOST=aichatbot-postgres
DB_PORT=5432
DB_NAME=aichatbot
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password

# RAG API（回測使用）
RAG_API_URL=http://localhost:8100/api/v1/message
```

### 新增環境變數（可選）

```bash
# 迴圈預設配置
DEFAULT_BATCH_SIZE=50
DEFAULT_MAX_ITERATIONS=10
DEFAULT_TARGET_PASS_RATE=0.85

# 成本控制
BUDGET_LIMIT_USD=100.0  # 單次迴圈預算上限

# 非同步執行配置
POLLING_INTERVAL_SECONDS=5  # 前端輪詢頻率
```

---

## 📊 監控與告警

### 關鍵指標

部署後監控以下指標（1 週）：

| 指標 | 目標值 | 監控方式 |
|------|--------|---------|
| API 回應時間（啟動迴圈） | < 1 秒 | Prometheus |
| 迭代執行時間（50 題） | 10-15 分鐘 | `loop_execution_logs` 表 |
| 批量審核 10 項 | < 5 秒 | API 日誌 |
| OpenAI API 成本 | < 預算限制 | `openai_cost_tracking` 表 |
| 服務可用性 | ≥ 99.9% | 健康檢查 |

### 資料庫監控

```sql
-- 監控迴圈執行狀態
SELECT status, COUNT(*)
FROM knowledge_completion_loops
GROUP BY status;

-- 監控待審核知識數量
SELECT COUNT(*)
FROM loop_generated_knowledge
WHERE status = 'pending';

-- 監控成本使用情況
SELECT
  loop_id,
  loop_name,
  total_openai_cost_usd,
  budget_limit_usd,
  (total_openai_cost_usd / NULLIF(budget_limit_usd, 0)) * 100 AS budget_usage_pct
FROM knowledge_completion_loops
WHERE budget_limit_usd IS NOT NULL
ORDER BY budget_usage_pct DESC;
```

### 告警規則

- ⚠️  迴圈執行時間 > 20 分鐘（50 題預期 10-15 分鐘）
- ⚠️  OpenAI API 錯誤率 > 10%
- ⚠️  預算使用率 > 90%
- ⚠️  待審核知識數量 > 100（需人工處理積壓）
- 🚨 資料庫連接池使用率 > 80%

---

## 🔄 回滾計畫

### 何時需要回滾？

- 🚨 API 錯誤率 > 50%
- 🚨 資料庫 Migration 失敗
- 🚨 服務無法啟動
- 🚨 關鍵功能無法使用

### 回滾步驟

```bash
# 1. 停止服務
docker-compose stop rag-orchestrator

# 2. 回滾資料庫
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot < database/migrations/rollback_add_loop_features.sql

# 3. 還原備份（如果 Migration 回滾失敗）
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot < backup_YYYYMMDD_HHMMSS.sql

# 4. 重啟服務
docker-compose start rag-orchestrator

# 5. 驗證回滾成功
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot -c "
SELECT column_name FROM information_schema.columns
WHERE table_name = 'knowledge_completion_loops' AND column_name = 'scenario_ids';
"
# 應該返回 0 rows（欄位已移除）
```

### 回滾風險

- ⚠️  已啟動的迴圈資料會遺失（`scenario_ids` 欄位刪除）
- ⚠️  已生成的知識重複檢測資料會遺失
- ✅  知識庫正式資料不受影響（`knowledge_base` 表未修改）

---

## ✅ 部署檢查清單

### 部署前

- [ ] 資料庫已備份（`backup_*.sql` 檔案存在且大小 > 1MB）
- [ ] Migration 腳本已測試（dry-run 通過）
- [ ] OpenAI API Key 已配置
- [ ] Embedding API 已啟動（`http://localhost:5001` 可訪問）
- [ ] 確認部署時間窗口（建議深夜或週末）

### 部署中

- [ ] Migration 執行成功（無錯誤訊息）
- [ ] 新欄位已建立（5 個欄位存在）
- [ ] 索引已建立（2 個索引存在）
- [ ] `knowledge_gap_analysis` 表已建立
- [ ] 服務重啟成功（無錯誤日誌）

### 部署後

- [ ] 健康檢查通過（`/health` 返回 200 OK）
- [ ] 迴圈管理 API 可訪問（`/api/v1/loops` 返回 200）
- [ ] 知識審核 API 可訪問（`/api/v1/loop-knowledge/pending` 返回 200）
- [ ] 啟動迴圈測試通過（返回 `loop_id`）
- [ ] 執行迭代測試通過（返回 `task_id`）
- [ ] 查詢狀態測試通過（返回進度資訊）
- [ ] 批量審核測試通過（5 個項目全部成功）
- [ ] 監控指標正常（API 回應時間 < 1 秒）

### 1 週後

- [ ] 迴圈執行時間符合預期（50 題 10-15 分鐘）
- [ ] OpenAI API 成本在預算內
- [ ] 服務可用性 ≥ 99.9%
- [ ] 無關鍵錯誤或告警

---

## 📚 相關文檔

- [API 文檔 - 迴圈管理](../../api/loops_api.md)
- [API 文檔 - 知識審核](../../api/loop_knowledge_api.md)
- [前端需求 - 批量審核](../../frontend/batch_review_requirements.md)
- [前端需求 - 迴圈管理界面](../../frontend/loop_management_requirements.md)
- [技術設計文檔](.kiro/specs/backtest-knowledge-refinement/design.md)
- [開發者指南](../../developer_guide/architecture.md)

---

## 🆘 疑難排解

### 問題 1: Migration 執行失敗

**錯誤訊息**：
```
ERROR:  column "scenario_ids" already exists
```

**解決方法**：
```bash
# 欄位已存在，跳過此步驟（Migration 是冪等的）
# 或者先執行回滾再重新執行
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot < database/migrations/rollback_add_loop_features.sql
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot < database/migrations/add_loop_features.sql
```

---

### 問題 2: API 返回 404 Not Found

**錯誤訊息**：
```
{"detail": "Not Found"}
```

**可能原因**：
1. 路由未註冊（服務未重啟）
2. API 路徑錯誤

**解決方法**：
```bash
# 1. 重啟服務
docker-compose restart rag-orchestrator

# 2. 檢查路由是否註冊
docker-compose logs rag-orchestrator | grep "loops"

# 3. 確認 API 路徑正確
curl http://localhost:8100/api/v1/loops  # 正確
curl http://localhost:8100/loops          # 錯誤（缺少 /api/v1/ 前綴）
```

---

### 問題 3: 並發執行錯誤

**錯誤訊息**：
```json
{"error_code": "CONCURRENT_EXECUTION", "message": "Loop 1 已在執行中"}
```

**原因**：同一迴圈不允許並發執行

**解決方法**：
```bash
# 等待當前迭代完成（查詢狀態）
curl -X GET http://localhost:8100/api/v1/loops/1

# 或者取消當前迭代
curl -X POST http://localhost:8100/api/v1/loops/1/cancel
```

---

### 問題 4: 預算超出錯誤

**錯誤訊息**：
```json
{"error_code": "BUDGET_EXCEEDED", "message": "預算超出限制"}
```

**原因**：OpenAI API 成本超過預算限制

**解決方法**：
```bash
# 查詢成本使用情況
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot -c "
SELECT loop_id, total_openai_cost_usd, budget_limit_usd
FROM knowledge_completion_loops
WHERE loop_id = 1;
"

# 調整預算限制（如需要）
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot -c "
UPDATE knowledge_completion_loops
SET budget_limit_usd = 200.0
WHERE loop_id = 1;
"
```

---

## 📞 支援

如有問題，請聯繫：
- **技術文檔**: `.kiro/specs/backtest-knowledge-refinement/`
- **API 文檔**: `docs/api/`
- **開發者指南**: `docs/developer_guide/`

---

**最後更新**：2026-03-27
**維護者**：AI Development Team
