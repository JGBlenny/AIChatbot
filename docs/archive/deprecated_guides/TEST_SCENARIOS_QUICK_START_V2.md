# 測試題庫系統快速開始指南 🚀

**版本：** v2.0 (Collection-Free)
**狀態：** ✅ 100% 完成
**更新日期：** 2025-10-11

---

## ⚡ 重大更新（v2.0）

**🎉 移除集合功能，採用智能評分優先策略**

- ❌ 移除測試集合（smoke, full, regression, edge_cases）
- ✅ 自動優先測試低分/失敗案例
- ✅ 簡化 API 和前端介面
- ✅ 基於歷史數據智能決定測試優先級

詳見：[COLLECTION_REMOVAL_SUMMARY.md](./COLLECTION_REMOVAL_SUMMARY.md)

---

## 📌 系統概覽

測試題庫系統已從 Excel 完整遷移到 PostgreSQL 資料庫，提供：

✅ **13 個 REST API 端點** - 完整的 CRUD 操作（v2.0 精簡）
✅ **2 個前端管理頁面** - 測試題庫管理 + 待審核
✅ **用戶問題審核流程** - 4 狀態生命週期
✅ **智能優先測試** - 基於評分和失敗率自動排序
✅ **自動統計追蹤** - 執行次數、通過率、信心度

---

## 🎯 快速存取

### 前端頁面

| 頁面 | 網址 | 功能 |
|------|------|------|
| **測試題庫管理** | http://localhost:8080/#/test-scenarios | 查看、新增、編輯、刪除測試情境 |
| **待審核頁面** | http://localhost:8080/#/test-scenarios/pending | 審核待批准的測試情境 |
| **回測結果** | http://localhost:8080/#/backtest | 查看回測執行結果 |

### API 端點

**Base URL:** http://localhost:8000

```bash
# 測試情境 (5 個端點)
GET    /api/test/scenarios                # 列出測試情境（支援篩選）
GET    /api/test/scenarios/:id            # 獲取情境詳情
POST   /api/test/scenarios                # 創建新測試情境
PUT    /api/test/scenarios/:id            # 更新測試情境
DELETE /api/test/scenarios/:id            # 刪除測試情境

# 審核與統計 (5 個端點)
GET    /api/test/scenarios/pending        # 待審核列表
POST   /api/test/scenarios/:id/review     # 審核測試情境（批准/拒絕）
GET    /api/test/unclear-questions/candidates  # 候選用戶問題列表
POST   /api/test/unclear-questions/:id/convert # 轉為測試情境
GET    /api/test/stats                    # 測試題庫統計

# 回測記錄 (3 個端點)
GET    /api/test/backtest/runs            # 回測執行歷史
GET    /api/test/backtest/runs/:id        # 回測執行詳情
GET    /api/test/backtest/runs/:id/results # 回測結果詳情
```

---

## ⚡ 常用操作

### 1️⃣ 執行回測（智能優先策略）

```bash
# 進入專案目錄
cd /Users/lenny/jgb/AIChatbot

# 快速測試（5 個測試，優先低分案例）⭐ 推薦
BACKTEST_QUALITY_MODE=basic \
BACKTEST_SAMPLE_SIZE=5 \
BACKTEST_PRIORITIZE_FAILED=true \
PROJECT_ROOT=/Users/lenny/jgb/AIChatbot \
python3 scripts/knowledge_extraction/backtest_framework.py

# 完整測試（所有已批准測試）
BACKTEST_QUALITY_MODE=basic \
BACKTEST_PRIORITIZE_FAILED=true \
PROJECT_ROOT=/Users/lenny/jgb/AIChatbot \
python3 scripts/knowledge_extraction/backtest_framework.py

# 難度篩選（只測中等難度）
BACKTEST_DIFFICULTY=medium \
BACKTEST_PRIORITIZE_FAILED=true \
PROJECT_ROOT=/Users/lenny/jgb/AIChatbot \
python3 scripts/knowledge_extraction/backtest_framework.py

# 使用 Excel 模式（向後相容）
BACKTEST_USE_DATABASE=false \
python3 scripts/knowledge_extraction/backtest_framework.py
```

#### 環境變數說明

| 變數名 | 說明 | 預設值 |
|--------|------|--------|
| `BACKTEST_QUALITY_MODE` | 品質模式（basic/full） | basic |
| `BACKTEST_SAMPLE_SIZE` | 抽樣數量（不設定=全部） | None |
| `BACKTEST_DIFFICULTY` | 難度篩選（easy/medium/hard） | None |
| `BACKTEST_PRIORITIZE_FAILED` | 優先低分/失敗案例 | true |
| `BACKTEST_USE_DATABASE` | 使用資料庫模式 | true |
| `BACKTEST_NON_INTERACTIVE` | 非交互模式 | false |

**回測結果位置：**
- 詳細結果：`output/backtest/backtest_results_detail.json`
- 摘要報告：`output/backtest/backtest_results_summary.txt`
- 執行日誌：`output/backtest/backtest_log.txt`

---

### 2️⃣ 使用前端管理測試情境

#### 新增測試情境

1. 訪問 http://localhost:8080/#/test-scenarios
2. 點擊「➕ 新增測試情境」按鈕
3. 填寫表單：
   - **測試問題**：實際的問題文字
   - **預期分類**：選擇意圖（如「帳務問題」）
   - **難度**：Easy / Medium / Hard
   - **優先級**：1-100（數字越大越優先）
4. 點擊「建立」

#### 審核測試情境

1. 訪問 http://localhost:8080/#/test-scenarios/pending
2. 查看待審核的測試情境卡片
3. 選擇操作：
   - **✏️ 編輯**：修改內容後再審核
   - **✅ 批准**：批准測試情境
   - **❌ 拒絕**：拒絕並填寫原因

---

### 3️⃣ 使用 API 管理測試情境

#### 查詢測試情境（篩選已批准）

```bash
curl "http://localhost:8000/api/test/scenarios?status=approved&limit=10" | python3 -m json.tool
```

#### 查詢測試情境（篩選難度）

```bash
curl "http://localhost:8000/api/test/scenarios?difficulty=medium" | python3 -m json.tool
```

#### 新增測試情境

```bash
curl -X POST http://localhost:8000/api/test/scenarios \
  -H "Content-Type: application/json" \
  -d '{
    "test_question": "租金可以分期繳嗎？",
    "expected_category": "帳務問題",
    "difficulty": "medium",
    "priority": 70,
    "notes": "常見問題"
  }' | python3 -m json.tool
```

#### 批准測試情境

```bash
curl -X POST http://localhost:8000/api/test/scenarios/15/review \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve",
    "notes": "問題清晰，適合測試"
  }' | python3 -m json.tool
```

#### 查詢統計資訊

```bash
# 測試題庫總體統計
curl http://localhost:8000/api/test/stats | python3 -m json.tool
```

---

### 4️⃣ 用戶問題審核流程（SQL）

```sql
-- 1. 查看候選用戶問題（頻率 >= 2）
SELECT * FROM v_unclear_question_candidates LIMIT 10;

-- 2. 從用戶問題創建測試情境
SELECT create_test_scenario_from_unclear_question(
    p_unclear_question_id := 5,
    p_expected_category := '帳務問題',
    p_difficulty := 'medium',
    p_created_by := 'admin'
);

-- 3. 查看待審核列表
SELECT * FROM v_pending_test_scenarios
ORDER BY question_frequency DESC NULLS LAST;

-- 4. 批准測試情境
UPDATE test_scenarios
SET status = 'approved',
    reviewed_by = 'admin',
    reviewed_at = NOW(),
    review_notes = '問題頻率高，適合加入測試'
WHERE id = 15;
```

---

## 🗄️ 資料庫結構

### 核心資料表

| 表名 | 說明 | 記錄數 |
|------|------|--------|
| `test_scenarios` | 測試情境 | 14 個（10 遷移 + 1 測試 + 3 用戶問題）|
| `backtest_runs` | 回測執行記錄 | 待執行後填充 |
| `backtest_results` | 回測結果詳細 | 待執行後填充 |
| ~~`test_collections`~~ | ~~測試集合~~（已廢棄） | 保留歷史數據 |
| ~~`test_scenario_collections`~~ | ~~多對多關聯~~（已廢棄） | 保留歷史數據 |

### 輔助視圖

| 視圖名 | 說明 |
|--------|------|
| `v_test_scenario_details` | 測試情境詳情 |
| `v_pending_test_scenarios` | 待審核列表 |
| `v_unclear_question_candidates` | 用戶問題候選 |
| `v_test_run_history` | 執行歷史 |
| ~~`v_test_collection_summary`~~ | ~~集合摘要統計~~（已廢棄） |

### SQL 函數

| 函數名 | 說明 |
|--------|------|
| `create_test_scenario_from_unclear_question()` | 從用戶問題創建測試情境 |

---

## 🎯 智能優先測試策略（v2.0 新功能）

### 優先排序邏輯

測試情境按以下順序排列（當 `BACKTEST_PRIORITIZE_FAILED=true` 時）：

1. **失敗率（fail_rate）** - 降序
   - 計算公式：`1.0 - (pass_count / total_runs)`
   - 未執行過的測試預設 0.5

2. **平均分數（avg_score）** - 升序
   - 優先測試低分案例

3. **優先級（priority）** - 降序
   - 手動設定的重要性（1-100）

4. **ID** - 升序
   - 較舊的測試優先

### 範例

| 測試ID | 失敗率 | 平均分數 | 優先級 | 排序 |
|--------|--------|---------|--------|------|
| 5 | 0.80 | 0.45 | 50 | 1 |
| 12 | 0.60 | 0.52 | 50 | 2 |
| 8 | 0.50 | 0.30 | 50 | 3 |
| 3 | 0.50 | 0.30 | 80 | 4 |

**解釋：**
- 測試 5：失敗率最高（80%）→ 優先測試
- 測試 12：失敗率次高（60%）→ 第二優先
- 測試 8 vs 3：失敗率相同，但測試 8 分數較低 → 測試 8 優先

---

## 🔧 開發模式配置

### Docker Compose 動態掛載

```yaml
# docker-compose.yml
knowledge-admin-api:
  volumes:
    # 開發模式：動態掛載後端程式碼
    - ./knowledge-admin/backend/app.py:/app/app.py
    - ./knowledge-admin/backend/routes_test_scenarios.py:/app/routes_test_scenarios.py
```

**優點：**
- ✅ 程式碼變更即時生效
- ✅ 無需重建 Docker image
- ✅ 加速開發迭代

**使用方式：**
```bash
# 修改程式碼後重啟服務
docker-compose restart knowledge-admin-api

# 無需重新建置
```

---

## 🎯 測試情境狀態

| 狀態 | 說明 | 下一步 |
|------|------|--------|
| **draft** | 草稿 | 編輯後設為 pending_review |
| **pending_review** | 待審核 | 管理者批准或拒絕 |
| **approved** | 已批准 | 可用於回測 |
| **rejected** | 已拒絕 | 不再使用 |

---

## 🚨 常見問題

### Q1: 回測報錯「找不到測試情境」？

**A:** 確認資料庫中有已批准的測試情境：

```sql
SELECT COUNT(*) FROM test_scenarios WHERE status = 'approved';
```

如果數量為 0，請執行遷移腳本或使用前端新增測試情境。

### Q2: 如何切換回 Excel 模式？

**A:** 設定環境變數：

```bash
BACKTEST_USE_DATABASE=false python3 scripts/knowledge_extraction/backtest_framework.py
```

### Q3: 前端修改後沒有生效？

**A:** 確認使用生產模式時需要重新建置：

```bash
cd knowledge-admin/frontend
npm run build
docker-compose restart knowledge-admin-web
```

**建議使用開發模式：** `npm run dev`（自動熱重載）

### Q4: 如何查看回測日誌？

**A:**

```bash
# 查看最新日誌
cat output/backtest/backtest_log.txt

# 查看 Docker 容器日誌
docker-compose logs -f knowledge-admin-api
```

### Q5: 如何備份測試題庫？

**A:**

```bash
# 匯出測試情境
pg_dump -U aichatbot -d aichatbot_admin \
  -t test_scenarios \
  -t backtest_runs \
  -t backtest_results \
  > test_scenarios_backup_$(date +%Y%m%d).sql

# 恢復備份
psql -U aichatbot -d aichatbot_admin < test_scenarios_backup_20251011.sql
```

### Q6: v2.0 與 v1.0 的主要差異？

**A:** 見下表：

| 功能 | v1.0 | v2.0 |
|------|------|------|
| 測試集合 | ✅ 4 個集合 | ❌ 已移除 |
| 優先策略 | 手動分配集合 | ✅ 智能評分排序 |
| API 端點數 | 16 個 | 13 個 |
| 環境變數 | `BACKTEST_TYPE` | `BACKTEST_PRIORITIZE_FAILED` |
| 前端介面 | 集合篩選器 | 難度篩選器 |

詳見：[COLLECTION_REMOVAL_SUMMARY.md](./COLLECTION_REMOVAL_SUMMARY.md)

---

## 📚 相關文檔

| 文檔 | 說明 | 位置 |
|------|------|------|
| **集合移除報告** ⭐ NEW | 完整的集合功能移除說明 | [COLLECTION_REMOVAL_SUMMARY.md](./COLLECTION_REMOVAL_SUMMARY.md) |
| **完整實施報告** | 詳細的系統架構與實作說明 | [TEST_SCENARIOS_DATABASE_COMPLETE.md](./TEST_SCENARIOS_DATABASE_COMPLETE.md) |
| **遷移指南** | 資料遷移與使用說明 | [TEST_SCENARIOS_MIGRATION_GUIDE.md](./TEST_SCENARIOS_MIGRATION_GUIDE.md) |
| **回測優化指南** | 回測策略與優化建議 | [BACKTEST_OPTIMIZATION_GUIDE.md](./BACKTEST_OPTIMIZATION_GUIDE.md) |

---

## ✅ 系統狀態檢查

```bash
# 1. 檢查 Docker 服務狀態
docker-compose ps

# 2. 檢查資料庫連線
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "SELECT COUNT(*) FROM test_scenarios WHERE status='approved';"

# 3. 檢查 API 端點
curl http://localhost:8000/api/test/scenarios
curl http://localhost:8000/api/test/stats

# 4. 檢查前端訪問
curl http://localhost:8080

# 5. 檢查回測結果
ls -lh output/backtest/
```

---

## 🎉 完成度

| 模組 | 狀態 | 完成度 |
|------|------|--------|
| 資料庫 Schema | ✅ | 100% |
| 資料遷移 | ✅ | 100% |
| 後端 API | ✅ | 100% (13/13 端點) |
| 前端頁面 | ✅ | 100% (2/2 頁面) |
| 智能優先測試 | ✅ | 100% |
| 回測整合 | ✅ | 100% |
| 端到端測試 | ✅ | 100% |
| 文檔 | ✅ | 100% |

**🏆 專案狀態：100% 完成，v2.0 已投入生產使用**

---

**最後更新：** 2025-10-11 13:45
**維護者：** 開發團隊
**版本：** v2.0 (Collection-Free)
