# 系統盤查與整理報告

**生成日期**: 2025-10-12
**工作目錄**: `/Users/lenny/jgb/AIChatbot`
**資料庫**: `aichatbot-postgres` / `aichatbot_admin`

---

## 📊 執行摘要

### 系統當前狀態

- **資料庫表**: 16 張表，運作正常
- **知識庫條目**: 467 條
- **意圖數量**: 13 個
- **測試場景**: 17 個（5 個重複）
- **模糊問題**: 31 個
- **文檔數量**: 45+ 個（含根目錄和 docs/）
- **未追蹤文件**: 60+ 個

### 主要發現

🔴 **嚴重問題**:
1. **測試場景有重複數據**：5 組重複的測試問題
2. **文檔散落各處**：根目錄有 18 個 .md 文件，docs/ 有 37 個
3. **大量未追蹤文件**：包括臨時測試文件、備份文件、完成報告等

🟡 **中度問題**:
1. **文檔重複**：多個相似主題的文檔（如 QUICKSTART vs QUICK_START）
2. **備份文件未清理**：3 個 .backup/.bak 文件
3. **Migration 文件混亂**：15 個 migration 文件未版本控制

🟢 **良好狀態**:
1. 資料庫結構完整，觸發器和約束正常運作
2. 核心功能代碼組織良好
3. 前端組件結構清晰

---

## 第一階段：完整盤查

### 1. 資料庫狀態檢查

#### 1.1 資料庫表結構
```
✅ 16 張表已建立：
- ai_generated_knowledge_candidates
- backtest_results
- backtest_runs
- business_scope_config
- chat_history
- conversation_logs
- intents
- knowledge_base
- knowledge_intent_mapping
- suggested_intents
- test_collections (已棄用但保留)
- test_scenario_collections (已棄用但保留)
- test_scenarios
- unclear_questions
- vendor_configs
- vendors
```

#### 1.2 測試數據情況

**unclear_questions 表** (總計 31 條):
```
狀態分佈：
- pending (待處理): 20 條 (64.5%)
- in_progress (處理中): 8 條 (25.8%)
- resolved (已解決): 3 條 (9.7%)

✅ 無重複數據
```

**test_scenarios 表** (總計 17 條):
```
狀態分佈：
- pending_review (待審核): 7 條 (41.2%)
- approved (已批准): 5 條 (29.4%)
- rejected (已拒絕): 5 條 (29.4%)

❌ 發現 5 組重複數據：
1. "社區停車位如何申請" - 2 條
2. "社區游泳池開放時間？" - 2 條
3. "垃圾回收時間是星期幾" - 2 條
4. "社區泳池水質檢測報告哪裡看" - 2 條
5. "電梯可以載多重的物品" - 2 條
```

**其他測試數據**:
```
- ai_generated_knowledge_candidates: 5 條
- backtest_results: 0 條
```

#### 1.3 Migration 文件狀態

**database/migrations/** 目錄 (15 個文件):
```
❌ 未納入版本控制（未追蹤）

文件列表：
09-deprecate-collection-tables.sql
09-knowledge-multi-intent.sql
10-create-suggested-knowledge.sql
11-add-semantic-similarity-to-unclear-questions.sql
11-add-source-tracking-to-knowledge-candidates.sql
11b-fix-semantic-function.sql
12-fix-duplicate-test-scenario-creation.sql
12-remove-suggested-knowledge.sql
13-add-auto-scenario-creation-trigger.sql
13-ai-knowledge-generation.sql
13b-fix-knowledge-check-function.sql
14-add-rejected-scenario-retry-logic.sql
15-update-candidates-view-for-rejected-scenarios.sql
16-fix-candidates-view-filter.sql
17-fix-candidates-view-check-all-scenarios.sql

⚠️ 問題：
1. 編號重複（09, 11, 12, 13）
2. 用途不清（哪些已執行？哪些未執行？）
3. 缺乏執行記錄機制
```

**database/init/** 目錄 (7 個文件):
```
✅ 部分在版本控制中

01-enable-pgvector.sql ✅
02-create-knowledge-base.sql ✅
03-create-rag-tables.sql ✅
06-vendors-and-configs.sql ❌ 未追蹤
07-extend-knowledge-base.sql ❌ 未追蹤
08-remove-templates-use-generic-values.sql ❌ 未追蹤
09-create-test-scenarios.sql ❌ 未追蹤
```

---

### 2. 文檔檔案檢查

#### 2.1 根目錄文檔 (18 個 .md 文件)

**快速開始類** (重複):
```
❌ QUICKSTART.md (7.8KB) - 在 docs/README.md 中引用
❌ QUICK_START.md (3.9KB) - 內容相似但更簡短
❌ QUICK_REFERENCE.md (8.4KB) - 快速參考手冊

建議：保留 QUICKSTART.md，刪除其他兩個
```

**測試場景類** (版本混亂):
```
✅ TEST_SCENARIOS_DATABASE_COMPLETE.md (22KB) - 完整文檔
✅ TEST_SCENARIOS_MIGRATION_GUIDE.md (12KB) - 遷移指南
✅ TEST_SCENARIOS_QUICK_START.md (11KB) - 快速開始
❌ TEST_SCENARIOS_QUICK_START_V2.md (12KB) - 版本 2，似乎是測試版本

建議：檢查 V2 是否有新內容，若無則刪除
```

**回測與優化類** (重複):
```
根目錄：
- BACKTEST_OPTIMIZATION_GUIDE.md (3.7KB)
- BACKTEST_ANSWER_SYNTHESIS_IMPLEMENTATION_COMPLETE.md (9.7KB)
- ANSWER_SYNTHESIS_BACKTEST_SOLUTION.md (5.3KB)

docs/ 目錄：
- BACKTEST_KNOWLEDGE_OPTIMIZATION_GUIDE.md (8.3KB)
- BACKTEST_QUALITY_IMPLEMENTATION_COMPLETE.md (10KB)
- BACKTEST_QUALITY_INTEGRATION.md (16KB)
- BACKTEST_TESTING_REPORT.md (8.3KB)
- ANSWER_SYNTHESIS_BACKTEST_GUIDE.md (6.3KB)
- ANSWER_SYNTHESIS_IMPLEMENTATION.md (9.9KB)
- ANSWER_SYNTHESIS_SUMMARY.md (4.6KB)
- ANSWER_SYNTHESIS_TESTING_GUIDE.md (9.1KB)

❌ 嚴重重複，需要整合

建議：
1. 保留 docs/ 中的系統性文檔
2. 將根目錄的完成報告歸檔到 docs/archive/completion_reports/
```

**功能完成報告類**:
```
根目錄：
- COLLECTION_REMOVAL_SUMMARY.md (13KB)
- SEMANTIC_SIMILARITY_TEST_REPORT.md (7.6KB)
- UNIFIED_REVIEW_CENTER_COMPLETE.md (11KB)

建議：移至 docs/archive/completion_reports/
```

**系統配置類** (保留):
```
✅ README.md (19KB) - 主文檔
✅ README_DEPLOYMENT.md (6.4KB) - 部署指南
✅ CHANGELOG.md (7.9KB) - 變更記錄
✅ DOCKER_COMPOSE_GUIDE.md (6.9KB) - Docker 指南
✅ PGVECTOR_SETUP.md (5.5KB) - 資料庫設置
✅ Makefile (3.6KB) - 構建腳本
```

#### 2.2 docs/ 目錄文檔 (37 個文件)

**核心文檔** (保留):
```
✅ docs/README.md - 文檔索引
✅ docs/architecture/SYSTEM_ARCHITECTURE.md - 系統架構
✅ docs/MULTI_INTENT_CLASSIFICATION.md - 多意圖分類
✅ docs/INTENT_MANAGEMENT_README.md - 意圖管理
✅ docs/KNOWLEDGE_CLASSIFICATION_COMPLETE.md - 知識分類
✅ docs/KNOWLEDGE_EXTRACTION_GUIDE.md - 知識提取
✅ docs/frontend_usage_guide.md - 前端使用
✅ docs/API_REFERENCE_PHASE1.md - API 參考
✅ docs/MARKDOWN_GUIDE.md - Markdown 指南
✅ docs/DEVELOPMENT_WORKFLOW.md - 開發流程
✅ docs/PHASE2_PLANNING.md - Phase 2 規劃
✅ docs/QUICKSTART.md - 快速開始（與根目錄重複？）
✅ docs/API_USAGE.md - API 使用
```

**功能完成記錄** (可歸檔):
```
⚠️ docs/KNOWLEDGE_EXTRACTION_COMPLETION.md
⚠️ docs/intent_management_phase_b_complete.md
⚠️ docs/DOCUMENTATION_COMPLETE.md
⚠️ docs/FRONTEND_STAGE3_COMPLETE.md
```

**測試與評估報告** (可歸檔):
```
⚠️ docs/AI_KNOWLEDGE_GENERATION_EVALUATION.md
⚠️ docs/KNOWLEDGE_MULTI_INTENT_EVALUATION.md
⚠️ docs/SCORING_QUALITY_ANALYSIS.md
⚠️ docs/SEMANTIC_VS_CATEGORY_GROUPING.md
```

**修復記錄** (可歸檔):
```
⚠️ docs/DUPLICATE_TEST_SCENARIO_PREVENTION.md
⚠️ docs/UNCLEAR_QUESTION_CANDIDATES_FIX.md
⚠️ docs/TEST_SCENARIO_STATUS_MANAGEMENT.md
⚠️ docs/REJECTED_SCENARIO_RETRY_IMPLEMENTATION.md
```

**設計文檔** (可歸檔):
```
⚠️ docs/UNIFIED_REVIEW_CENTER_DESIGN.md
⚠️ docs/AI_KNOWLEDGE_GENERATION_FEATURE.md
```

**驗證文檔** (測試性質):
```
❌ docs/FRONTEND_VERIFY.md - 可刪除或歸檔
```

**archive/ 目錄** (4 個文件 + 4 個 SQL):
```
✅ 已正確歸檔：
- INTENT_MANAGEMENT_COMPLETE.md
- KNOWLEDGE_SUGGESTIONS_TEST_REPORT.md
- KNOWLEDGE_SUGGESTION_DESIGN.md
- PATH_FIXES_SUMMARY.md
- database_migrations/ (4 個舊 SQL 文件)
```

---

### 3. 代碼檔案檢查

#### 3.1 前端組件

**knowledge-admin/frontend/src/components/**:
```
✅ review/ 目錄 - 4 個組件（統一審核中心）
  - IntentReviewTab.vue
  - KnowledgeReviewTab.vue
  - ScenarioReviewTab.vue
  - UnclearQuestionReviewTab.vue

狀態：正在使用中
```

**knowledge-admin/frontend/src/views/**:
```
✅ 14 個 Vue 組件：
  - AIKnowledgeReviewView.vue ⚠️ 已重定向至 ReviewCenterView
  - BacktestView.vue ✅
  - BusinessScopeView.vue ✅
  - ChatTestView.vue ✅
  - IntentsView.vue ✅
  - KnowledgeImportView.vue ✅
  - KnowledgeReclassifyView.vue ✅
  - KnowledgeView.vue ✅
  - PendingReviewView.vue ✅
  - ReviewCenterView.vue ✅ (新的統一審核中心)
  - SuggestedIntentsView.vue ✅
  - TestScenariosView.vue ✅
  - VendorConfigView.vue ✅
  - VendorManagementView.vue ✅

⚠️ AIKnowledgeReviewView.vue 可能可以刪除（已重定向）
```

#### 3.2 後端代碼

**備份文件**:
```
❌ knowledge-admin/backend/routes_knowledge_suggestions.py.bak
❌ rag-orchestrator/services/llm_answer_optimizer.py.backup

建議：刪除備份文件
```

**測試文件**:
```
❌ knowledge-admin/backend/routes_test_scenarios.py - 未追蹤
✅ rag-orchestrator/routers/knowledge_generation.py - 未追蹤但可能在使用
✅ rag-orchestrator/services/knowledge_generator.py - 未追蹤但可能在使用
```

---

### 4. 臨時文件檢查

#### 4.1 測試腳本 (根目錄)

```
❌ test_classifier_direct.py
❌ test_debug.py
❌ test_multi_intent.py
❌ test_multi_intent_rag.py
❌ test_scoring_quality.py

建議：
- 移至 tests/ 目錄
- 或刪除（如果是一次性測試）
```

#### 4.2 Excel 測試文件

```
❌ test_scenarios_smoke.xlsx
❌ test_scenarios_full.xlsx

建議：
- 移至 tests/fixtures/ 或 docs/examples/
- 已遷移至資料庫，可歸檔
```

#### 4.3 輸出目錄

**output/** (156KB):
```
✅ backtest/ - 回測結果（保留）
  - backtest_log.txt
  - backtest_results.xlsx
  - backtest_results_summary.txt

❌ 臨時測試輸出（可刪除）：
  - multi_intent_test_20251011_*.json (5 個文件)
  - scoring_quality_test_20251011_151131.json

⚠️ 已提取的數據（可歸檔）：
  - knowledge_base_extracted.xlsx
  - test_scenarios.xlsx
```

#### 4.4 Docker 配置備份

```
❌ docker-compose.yml.backup (3.3KB)

建議：刪除（已有 git 版本控制）
```

#### 4.5 未使用的配置文件

```
✅ docker-compose.dev.yml - 開發環境配置（保留）
✅ docker-compose.prod.yml - 生產環境配置（保留）
```

---

## 第二階段：整理建議

### 1. 清理測試數據

#### 1.1 刪除重複的測試場景

**SQL 清理腳本**:

```sql
-- 檢視重複的測試場景
SELECT test_question, COUNT(*) as count,
       STRING_AGG(id::text || ':' || status, ', ') as scenarios
FROM test_scenarios
GROUP BY test_question
HAVING COUNT(*) > 1;

-- 方案 A: 保留最早的記錄（推薦）
WITH duplicates AS (
  SELECT id,
         ROW_NUMBER() OVER (PARTITION BY test_question ORDER BY created_at ASC) as rn
  FROM test_scenarios
)
DELETE FROM test_scenarios
WHERE id IN (
  SELECT id FROM duplicates WHERE rn > 1
);

-- 方案 B: 保留已批准的，其次是待審核的
WITH duplicates AS (
  SELECT id,
         test_question,
         status,
         ROW_NUMBER() OVER (
           PARTITION BY test_question
           ORDER BY
             CASE status
               WHEN 'approved' THEN 1
               WHEN 'pending_review' THEN 2
               WHEN 'rejected' THEN 3
               ELSE 4
             END,
             created_at ASC
         ) as rn
  FROM test_scenarios
)
DELETE FROM test_scenarios
WHERE id IN (
  SELECT id FROM duplicates WHERE rn > 1
);

-- 驗證結果
SELECT COUNT(*) as duplicate_count
FROM (
  SELECT test_question, COUNT(*)
  FROM test_scenarios
  GROUP BY test_question
  HAVING COUNT(*) > 1
) as duplicates;
```

**預期結果**: 從 17 條減少到 12 條

#### 1.2 保留必要的種子數據

```sql
-- 不需要刪除 unclear_questions（真實用戶數據）
-- 不需要刪除 knowledge_base（467 條知識庫）
-- 不需要刪除 intents（13 個核心意圖）

-- 可選：清理測試 AI 生成候選（如果不需要）
-- DELETE FROM ai_generated_knowledge_candidates;
```

---

### 2. 整合文檔

#### 2.1 快速開始文檔整合

**保留**:
- `QUICKSTART.md` (根目錄) - 作為主要快速開始指南

**刪除**:
- `QUICK_START.md` - 內容已包含在 QUICKSTART.md 中
- `QUICK_REFERENCE.md` - 建議整合到 README.md 或 docs/

**命令**:
```bash
# 備份並刪除
git rm QUICK_START.md
git rm QUICK_REFERENCE.md

# 或移至 archive（保留記錄）
mkdir -p docs/archive/deprecated_guides
git mv QUICK_START.md docs/archive/deprecated_guides/
git mv QUICK_REFERENCE.md docs/archive/deprecated_guides/
```

#### 2.2 測試場景文檔整合

**保留**:
- `TEST_SCENARIOS_QUICK_START.md` - 快速開始
- `TEST_SCENARIOS_DATABASE_COMPLETE.md` - 完整文檔
- `TEST_SCENARIOS_MIGRATION_GUIDE.md` - 遷移指南

**檢查並可能刪除**:
- `TEST_SCENARIOS_QUICK_START_V2.md` - 需確認是否有新內容

**命令**:
```bash
# 比較 V1 和 V2 的差異
diff TEST_SCENARIOS_QUICK_START.md TEST_SCENARIOS_QUICK_START_V2.md

# 如果 V2 沒有新內容，刪除
git rm TEST_SCENARIOS_QUICK_START_V2.md
```

#### 2.3 回測文檔整合

**整合方案**:

創建新的統一文檔結構：
```
docs/backtest/
├── README.md (索引)
├── OPTIMIZATION_GUIDE.md (優化指南)
├── ANSWER_SYNTHESIS_GUIDE.md (答案合成指南)
└── archive/
    ├── completion_reports/
    │   ├── QUALITY_IMPLEMENTATION_COMPLETE.md
    │   ├── QUALITY_INTEGRATION.md
    │   └── TESTING_REPORT.md
    └── evaluation_reports/
        ├── ANSWER_SYNTHESIS_EVALUATION.md
        └── KNOWLEDGE_OPTIMIZATION_EVALUATION.md
```

**合併內容**:
```bash
# 創建新目錄結構
mkdir -p docs/backtest/archive/{completion_reports,evaluation_reports}

# 移動並重命名文檔（保留重要的）
git mv docs/BACKTEST_KNOWLEDGE_OPTIMIZATION_GUIDE.md docs/backtest/OPTIMIZATION_GUIDE.md
git mv docs/ANSWER_SYNTHESIS_SUMMARY.md docs/backtest/ANSWER_SYNTHESIS_GUIDE.md

# 歸檔完成報告
git mv docs/BACKTEST_QUALITY_IMPLEMENTATION_COMPLETE.md docs/backtest/archive/completion_reports/
git mv docs/BACKTEST_QUALITY_INTEGRATION.md docs/backtest/archive/completion_reports/
git mv docs/BACKTEST_TESTING_REPORT.md docs/backtest/archive/completion_reports/

# 歸檔根目錄的完成報告
git mv BACKTEST_ANSWER_SYNTHESIS_IMPLEMENTATION_COMPLETE.md docs/backtest/archive/completion_reports/
git mv ANSWER_SYNTHESIS_BACKTEST_SOLUTION.md docs/backtest/archive/completion_reports/
git mv BACKTEST_OPTIMIZATION_GUIDE.md docs/backtest/archive/completion_reports/

# 保留或合併其他文檔
git mv docs/ANSWER_SYNTHESIS_IMPLEMENTATION.md docs/backtest/archive/evaluation_reports/
git mv docs/ANSWER_SYNTHESIS_BACKTEST_GUIDE.md docs/backtest/archive/evaluation_reports/
git mv docs/ANSWER_SYNTHESIS_TESTING_GUIDE.md docs/backtest/archive/evaluation_reports/

# 創建索引文檔
cat > docs/backtest/README.md << 'EOF'
# 回測系統文檔

## 📖 使用指南

- [優化指南](./OPTIMIZATION_GUIDE.md) - 回測成本與效能優化
- [答案合成指南](./ANSWER_SYNTHESIS_GUIDE.md) - LLM 答案合成系統

## 📁 歷史記錄

- [完成報告](./archive/completion_reports/) - 功能實施完成記錄
- [評估報告](./archive/evaluation_reports/) - 測試與評估結果
EOF
```

#### 2.4 功能完成報告歸檔

**創建統一的完成報告目錄**:

```bash
# 創建目錄
mkdir -p docs/archive/completion_reports

# 移動根目錄的完成報告
git mv COLLECTION_REMOVAL_SUMMARY.md docs/archive/completion_reports/
git mv SEMANTIC_SIMILARITY_TEST_REPORT.md docs/archive/completion_reports/
git mv UNIFIED_REVIEW_CENTER_COMPLETE.md docs/archive/completion_reports/

# 移動 docs/ 中的完成報告
git mv docs/KNOWLEDGE_EXTRACTION_COMPLETION.md docs/archive/completion_reports/
git mv docs/intent_management_phase_b_complete.md docs/archive/completion_reports/
git mv docs/DOCUMENTATION_COMPLETE.md docs/archive/completion_reports/
git mv docs/FRONTEND_STAGE3_COMPLETE.md docs/archive/completion_reports/

# 移動評估報告
mkdir -p docs/archive/evaluation_reports
git mv docs/AI_KNOWLEDGE_GENERATION_EVALUATION.md docs/archive/evaluation_reports/
git mv docs/KNOWLEDGE_MULTI_INTENT_EVALUATION.md docs/archive/evaluation_reports/
git mv docs/SCORING_QUALITY_ANALYSIS.md docs/archive/evaluation_reports/
git mv docs/SEMANTIC_VS_CATEGORY_GROUPING.md docs/archive/evaluation_reports/

# 移動修復記錄
mkdir -p docs/archive/fix_reports
git mv docs/DUPLICATE_TEST_SCENARIO_PREVENTION.md docs/archive/fix_reports/
git mv docs/UNCLEAR_QUESTION_CANDIDATES_FIX.md docs/archive/fix_reports/
git mv docs/TEST_SCENARIO_STATUS_MANAGEMENT.md docs/archive/fix_reports/
git mv docs/REJECTED_SCENARIO_RETRY_IMPLEMENTATION.md docs/archive/fix_reports/

# 移動設計文檔
mkdir -p docs/archive/design_docs
git mv docs/UNIFIED_REVIEW_CENTER_DESIGN.md docs/archive/design_docs/
git mv docs/AI_KNOWLEDGE_GENERATION_FEATURE.md docs/archive/design_docs/

# 刪除或歸檔驗證文檔
git mv docs/FRONTEND_VERIFY.md docs/archive/deprecated_guides/

# 更新 archive README
cat >> docs/archive/README.md << 'EOF'

## 完成報告

記錄各階段功能開發的完成狀況：

- Collection 系統移除總結
- 語義相似度測試報告
- 統一審核中心完成報告
- 知識提取完成記錄
- Intent 管理 Phase B 完成
- 文檔整理完成
- 前端 Stage 3 完成

## 評估報告

系統測試與評估結果：

- AI 知識生成評估
- 多 Intent 分類評估
- 評分品質分析
- 語義 vs 分類分組比較

## 修復記錄

問題修復的實施記錄：

- 重複測試場景防護
- 模糊問題候選修復
- 測試場景狀態管理
- 拒絕場景重試邏輯

## 設計文檔

功能設計草案：

- 統一審核中心設計
- AI 知識生成功能設計
EOF
```

---

### 3. 移除文件

#### 3.1 刪除備份文件

```bash
# 從 Git 中移除並刪除
git rm docker-compose.yml.backup
git rm knowledge-admin/backend/routes_knowledge_suggestions.py.bak
git rm rag-orchestrator/services/llm_answer_optimizer.py.backup
```

#### 3.2 清理臨時測試文件

```bash
# 創建測試目錄（如果不存在）
mkdir -p tests/integration

# 移動測試腳本到適當位置
git mv test_classifier_direct.py tests/integration/
git mv test_debug.py tests/integration/
git mv test_multi_intent.py tests/integration/
git mv test_multi_intent_rag.py tests/integration/
git mv test_scoring_quality.py tests/integration/

# 或者，如果這些是一次性測試，直接刪除
# git rm test_*.py
```

#### 3.3 清理 output/ 目錄

```bash
# 刪除臨時測試輸出
rm output/multi_intent_test_*.json
rm output/scoring_quality_test_*.json

# 可選：歸檔已提取的 Excel 文件
mkdir -p docs/examples/extracted_data
mv output/knowledge_base_extracted.xlsx docs/examples/extracted_data/
mv output/test_scenarios.xlsx docs/examples/extracted_data/

# 保留 backtest/ 目錄（持續使用）
```

#### 3.4 清理 Excel 測試文件

```bash
# 移至示例目錄
mkdir -p docs/examples/test_data
git mv test_scenarios_smoke.xlsx docs/examples/test_data/
git mv test_scenarios_full.xlsx docs/examples/test_data/

# 或歸檔（已遷移至資料庫）
# git mv test_scenarios_*.xlsx docs/archive/legacy_data/
```

#### 3.5 清理前端未使用組件

```bash
# AIKnowledgeReviewView 已重定向，可以刪除
git rm knowledge-admin/frontend/src/views/AIKnowledgeReviewView.vue

# 更新 router.js，移除重定向（已處理）
```

---

### 4. 歸檔文件

#### 4.1 Migration 文件歸檔

**建議創建 Migration 管理系統**:

```bash
# 創建 executed_migrations 記錄表
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin << 'EOF'
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    migration_file VARCHAR(255) UNIQUE NOT NULL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- 記錄已執行的 migrations
INSERT INTO schema_migrations (migration_file, description, executed_at) VALUES
('09-deprecate-collection-tables.sql', 'Deprecate collection tables', '2025-10-11'),
('09-knowledge-multi-intent.sql', 'Add multi-intent support', '2025-10-11'),
-- ... 根據實際執行情況添加
EOF

# 重命名 migration 文件以避免編號衝突
cd database/migrations
git mv 09-knowledge-multi-intent.sql 09a-knowledge-multi-intent.sql
git mv 11-add-source-tracking-to-knowledge-candidates.sql 11a-add-source-tracking-to-knowledge-candidates.sql
git mv 12-remove-suggested-knowledge.sql 12a-remove-suggested-knowledge.sql
git mv 13-ai-knowledge-generation.sql 13a-ai-knowledge-generation.sql

# 將 migrations 加入版本控制
cd /Users/lenny/jgb/AIChatbot
git add database/migrations/*.sql
git commit -m "docs: 將 database migrations 納入版本控制"
```

#### 4.2 Init 文件歸檔

```bash
# 將未追蹤的 init 文件加入版本控制
git add database/init/06-vendors-and-configs.sql
git add database/init/07-extend-knowledge-base.sql
git add database/init/08-remove-templates-use-generic-values.sql
git add database/init/09-create-test-scenarios.sql

git commit -m "docs: 將 database init 文件納入版本控制"
```

---

## 建議的文件結構

### 整理後的目錄結構

```
/Users/lenny/jgb/AIChatbot/
├── README.md ✅
├── QUICKSTART.md ✅
├── README_DEPLOYMENT.md ✅
├── CHANGELOG.md ✅
├── DOCKER_COMPOSE_GUIDE.md ✅
├── PGVECTOR_SETUP.md ✅
├── Makefile ✅
│
├── docs/
│   ├── README.md ✅ (文檔索引)
│   │
│   ├── architecture/
│   │   └── SYSTEM_ARCHITECTURE.md ✅
│   │
│   ├── guides/
│   │   ├── INTENT_MANAGEMENT_README.md ✅
│   │   ├── KNOWLEDGE_CLASSIFICATION_COMPLETE.md ✅
│   │   ├── KNOWLEDGE_EXTRACTION_GUIDE.md ✅
│   │   ├── frontend_usage_guide.md ✅
│   │   └── DEVELOPMENT_WORKFLOW.md ✅
│   │
│   ├── features/
│   │   ├── MULTI_INTENT_CLASSIFICATION.md ✅
│   │   ├── TEST_SCENARIOS_QUICK_START.md ✅
│   │   ├── TEST_SCENARIOS_DATABASE_COMPLETE.md ✅
│   │   └── TEST_SCENARIOS_MIGRATION_GUIDE.md ✅
│   │
│   ├── backtest/ ⭐ NEW
│   │   ├── README.md
│   │   ├── OPTIMIZATION_GUIDE.md
│   │   ├── ANSWER_SYNTHESIS_GUIDE.md
│   │   └── archive/
│   │       ├── completion_reports/
│   │       └── evaluation_reports/
│   │
│   ├── api/
│   │   ├── API_REFERENCE_PHASE1.md ✅
│   │   └── API_USAGE.md ✅
│   │
│   ├── planning/
│   │   └── PHASE2_PLANNING.md ✅
│   │
│   ├── examples/ ⭐ NEW
│   │   ├── test_data/
│   │   │   ├── test_scenarios_smoke.xlsx
│   │   │   └── test_scenarios_full.xlsx
│   │   └── extracted_data/
│   │       ├── knowledge_base_extracted.xlsx
│   │       └── test_scenarios.xlsx
│   │
│   └── archive/
│       ├── README.md ✅
│       ├── completion_reports/ ⭐ EXPANDED
│       │   ├── COLLECTION_REMOVAL_SUMMARY.md
│       │   ├── SEMANTIC_SIMILARITY_TEST_REPORT.md
│       │   ├── UNIFIED_REVIEW_CENTER_COMPLETE.md
│       │   ├── KNOWLEDGE_EXTRACTION_COMPLETION.md
│       │   ├── intent_management_phase_b_complete.md
│       │   ├── DOCUMENTATION_COMPLETE.md
│       │   └── FRONTEND_STAGE3_COMPLETE.md
│       │
│       ├── evaluation_reports/ ⭐ NEW
│       │   ├── AI_KNOWLEDGE_GENERATION_EVALUATION.md
│       │   ├── KNOWLEDGE_MULTI_INTENT_EVALUATION.md
│       │   ├── SCORING_QUALITY_ANALYSIS.md
│       │   └── SEMANTIC_VS_CATEGORY_GROUPING.md
│       │
│       ├── fix_reports/ ⭐ NEW
│       │   ├── DUPLICATE_TEST_SCENARIO_PREVENTION.md
│       │   ├── UNCLEAR_QUESTION_CANDIDATES_FIX.md
│       │   ├── TEST_SCENARIO_STATUS_MANAGEMENT.md
│       │   └── REJECTED_SCENARIO_RETRY_IMPLEMENTATION.md
│       │
│       ├── design_docs/ ⭐ NEW
│       │   ├── UNIFIED_REVIEW_CENTER_DESIGN.md
│       │   └── AI_KNOWLEDGE_GENERATION_FEATURE.md
│       │
│       ├── deprecated_guides/ ⭐ NEW
│       │   ├── QUICK_START.md
│       │   ├── QUICK_REFERENCE.md
│       │   └── FRONTEND_VERIFY.md
│       │
│       └── database_migrations/ ✅
│           ├── README.md
│           └── ... (舊版 SQL)
│
├── database/
│   ├── init/ ✅ (全部納入版本控制)
│   └── migrations/ ✅ (全部納入版本控制，修復編號)
│
├── knowledge-admin/
│   ├── backend/
│   │   ├── app.py ✅
│   │   └── routes_test_scenarios.py ⚠️ (需確認用途)
│   └── frontend/
│       └── src/
│           ├── components/
│           │   └── review/ ✅
│           └── views/ ✅ (移除 AIKnowledgeReviewView.vue)
│
├── rag-orchestrator/
│   ├── routers/ ✅
│   └── services/ ✅
│
├── scripts/
│   └── knowledge_extraction/ ✅
│
├── tests/ ⭐ ORGANIZED
│   ├── integration/
│   │   ├── test_classifier_direct.py
│   │   ├── test_debug.py
│   │   ├── test_multi_intent.py
│   │   ├── test_multi_intent_rag.py
│   │   └── test_scoring_quality.py
│   └── unit/
│
└── output/
    └── backtest/ ✅ (保留，清理臨時文件)
```

---

## 執行計劃

### Phase 1: 資料庫清理（立即執行）

```bash
# 1. 備份資料庫
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > backup_before_cleanup_$(date +%Y%m%d).sql

# 2. 清理重複測試場景（使用方案 B）
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin << 'EOF'
WITH duplicates AS (
  SELECT id,
         test_question,
         status,
         ROW_NUMBER() OVER (
           PARTITION BY test_question
           ORDER BY
             CASE status
               WHEN 'approved' THEN 1
               WHEN 'pending_review' THEN 2
               WHEN 'rejected' THEN 3
               ELSE 4
             END,
             created_at ASC
         ) as rn
  FROM test_scenarios
)
DELETE FROM test_scenarios
WHERE id IN (
  SELECT id FROM duplicates WHERE rn > 1
);
EOF

# 3. 創建 migration 追蹤表
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin << 'EOF'
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    migration_file VARCHAR(255) UNIQUE NOT NULL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);
EOF
```

### Phase 2: 文件歸檔（30 分鐘）

```bash
#!/bin/bash
# cleanup_phase2_archive.sh

set -e
cd /Users/lenny/jgb/AIChatbot

echo "=== Phase 2: 文件歸檔 ==="

# 創建目錄結構
mkdir -p docs/{backtest/archive/{completion_reports,evaluation_reports},archive/{completion_reports,evaluation_reports,fix_reports,design_docs,deprecated_guides},examples/{test_data,extracted_data},guides,features,api,planning}
mkdir -p tests/integration

# 2.1 快速開始文檔
echo "📝 整理快速開始文檔..."
git mv QUICK_START.md docs/archive/deprecated_guides/
git mv QUICK_REFERENCE.md docs/archive/deprecated_guides/

# 2.2 測試場景文檔
echo "📝 整理測試場景文檔..."
if diff -q TEST_SCENARIOS_QUICK_START.md TEST_SCENARIOS_QUICK_START_V2.md > /dev/null 2>&1; then
    git rm TEST_SCENARIOS_QUICK_START_V2.md
else
    echo "⚠️ V2 有差異，請手動檢查"
fi
git mv TEST_SCENARIOS_*.md docs/features/

# 2.3 回測文檔整合
echo "📝 整理回測文檔..."
git mv docs/BACKTEST_KNOWLEDGE_OPTIMIZATION_GUIDE.md docs/backtest/OPTIMIZATION_GUIDE.md 2>/dev/null || true
git mv docs/ANSWER_SYNTHESIS_SUMMARY.md docs/backtest/ANSWER_SYNTHESIS_GUIDE.md 2>/dev/null || true

# 歸檔完成報告
for file in BACKTEST_QUALITY_IMPLEMENTATION_COMPLETE BACKTEST_QUALITY_INTEGRATION BACKTEST_TESTING_REPORT; do
    git mv "docs/${file}.md" docs/backtest/archive/completion_reports/ 2>/dev/null || true
done

# 根目錄回測文檔
for file in BACKTEST_ANSWER_SYNTHESIS_IMPLEMENTATION_COMPLETE ANSWER_SYNTHESIS_BACKTEST_SOLUTION BACKTEST_OPTIMIZATION_GUIDE; do
    git mv "${file}.md" docs/backtest/archive/completion_reports/ 2>/dev/null || true
done

# 評估報告
for file in ANSWER_SYNTHESIS_IMPLEMENTATION ANSWER_SYNTHESIS_BACKTEST_GUIDE ANSWER_SYNTHESIS_TESTING_GUIDE; do
    git mv "docs/${file}.md" docs/backtest/archive/evaluation_reports/ 2>/dev/null || true
done

# 2.4 功能完成報告歸檔
echo "📝 歸檔完成報告..."
for file in COLLECTION_REMOVAL_SUMMARY SEMANTIC_SIMILARITY_TEST_REPORT UNIFIED_REVIEW_CENTER_COMPLETE; do
    git mv "${file}.md" docs/archive/completion_reports/ 2>/dev/null || true
done

for file in KNOWLEDGE_EXTRACTION_COMPLETION intent_management_phase_b_complete DOCUMENTATION_COMPLETE FRONTEND_STAGE3_COMPLETE; do
    git mv "docs/${file}.md" docs/archive/completion_reports/ 2>/dev/null || true
done

# 評估報告
for file in AI_KNOWLEDGE_GENERATION_EVALUATION KNOWLEDGE_MULTI_INTENT_EVALUATION SCORING_QUALITY_ANALYSIS SEMANTIC_VS_CATEGORY_GROUPING; do
    git mv "docs/${file}.md" docs/archive/evaluation_reports/ 2>/dev/null || true
done

# 修復記錄
for file in DUPLICATE_TEST_SCENARIO_PREVENTION UNCLEAR_QUESTION_CANDIDATES_FIX TEST_SCENARIO_STATUS_MANAGEMENT REJECTED_SCENARIO_RETRY_IMPLEMENTATION; do
    git mv "docs/${file}.md" docs/archive/fix_reports/ 2>/dev/null || true
done

# 設計文檔
for file in UNIFIED_REVIEW_CENTER_DESIGN AI_KNOWLEDGE_GENERATION_FEATURE; do
    git mv "docs/${file}.md" docs/archive/design_docs/ 2>/dev/null || true
done

git mv docs/FRONTEND_VERIFY.md docs/archive/deprecated_guides/ 2>/dev/null || true

# 2.5 組織核心文檔
echo "📝 組織核心文檔..."
for file in INTENT_MANAGEMENT_README KNOWLEDGE_CLASSIFICATION_COMPLETE KNOWLEDGE_EXTRACTION_GUIDE frontend_usage_guide DEVELOPMENT_WORKFLOW; do
    [ -f "docs/${file}.md" ] && git mv "docs/${file}.md" docs/guides/ 2>/dev/null || true
done

for file in MULTI_INTENT_CLASSIFICATION; do
    [ -f "docs/${file}.md" ] && git mv "docs/${file}.md" docs/features/ 2>/dev/null || true
done

for file in API_REFERENCE_PHASE1 API_USAGE; do
    [ -f "docs/${file}.md" ] && git mv "docs/${file}.md" docs/api/ 2>/dev/null || true
done

[ -f "docs/PHASE2_PLANNING.md" ] && git mv docs/PHASE2_PLANNING.md docs/planning/ 2>/dev/null || true

echo "✅ Phase 2 完成"
```

### Phase 3: 刪除臨時文件（10 分鐘）

```bash
#!/bin/bash
# cleanup_phase3_remove.sh

set -e
cd /Users/lenny/jgb/AIChatbot

echo "=== Phase 3: 刪除臨時文件 ==="

# 3.1 備份文件
echo "🗑️ 刪除備份文件..."
git rm docker-compose.yml.backup
git rm knowledge-admin/backend/routes_knowledge_suggestions.py.bak
git rm rag-orchestrator/services/llm_answer_optimizer.py.backup

# 3.2 測試腳本
echo "📦 移動測試腳本..."
mkdir -p tests/integration
for file in test_classifier_direct test_debug test_multi_intent test_multi_intent_rag test_scoring_quality; do
    [ -f "${file}.py" ] && git mv "${file}.py" tests/integration/
done

# 3.3 清理 output 目錄
echo "🗑️ 清理 output 目錄..."
rm -f output/multi_intent_test_*.json
rm -f output/scoring_quality_test_*.json

# 歸檔已提取數據
mkdir -p docs/examples/extracted_data
[ -f output/knowledge_base_extracted.xlsx ] && mv output/knowledge_base_extracted.xlsx docs/examples/extracted_data/
[ -f output/test_scenarios.xlsx ] && mv output/test_scenarios.xlsx docs/examples/extracted_data/

# 3.4 Excel 測試文件
echo "📦 移動 Excel 測試文件..."
mkdir -p docs/examples/test_data
[ -f test_scenarios_smoke.xlsx ] && git mv test_scenarios_smoke.xlsx docs/examples/test_data/
[ -f test_scenarios_full.xlsx ] && git mv test_scenarios_full.xlsx docs/examples/test_data/

# 3.5 前端未使用組件
echo "🗑️ 清理前端組件..."
[ -f knowledge-admin/frontend/src/views/AIKnowledgeReviewView.vue ] && git rm knowledge-admin/frontend/src/views/AIKnowledgeReviewView.vue

echo "✅ Phase 3 完成"
```

### Phase 4: Migration 管理（15 分鐘）

```bash
#!/bin/bash
# cleanup_phase4_migrations.sh

set -e
cd /Users/lenny/jgb/AIChatbot

echo "=== Phase 4: Migration 管理 ==="

# 4.1 重命名有編號衝突的 migrations
echo "🔢 修復 migration 編號..."
cd database/migrations
git mv 09-knowledge-multi-intent.sql 09a-knowledge-multi-intent.sql 2>/dev/null || true
git mv 11-add-source-tracking-to-knowledge-candidates.sql 11a-add-source-tracking-to-knowledge-candidates.sql 2>/dev/null || true
git mv 12-remove-suggested-knowledge.sql 12a-remove-suggested-knowledge.sql 2>/dev/null || true
git mv 13-ai-knowledge-generation.sql 13a-ai-knowledge-generation.sql 2>/dev/null || true
cd ../..

# 4.2 納入版本控制
echo "✅ 將 migrations 納入版本控制..."
git add database/migrations/*.sql
git add database/init/*.sql

echo "✅ Phase 4 完成"
```

### Phase 5: 提交更改（5 分鐘）

```bash
#!/bin/bash
# cleanup_phase5_commit.sh

set -e
cd /Users/lenny/jgb/AIChatbot

echo "=== Phase 5: 提交更改 ==="

# 創建索引文檔
cat > docs/backtest/README.md << 'EOF'
# 回測系統文檔

## 📖 使用指南

- [優化指南](./OPTIMIZATION_GUIDE.md) - 回測成本與效能優化
- [答案合成指南](./ANSWER_SYNTHESIS_GUIDE.md) - LLM 答案合成系統

## 📁 歷史記錄

- [完成報告](./archive/completion_reports/) - 功能實施完成記錄
- [評估報告](./archive/evaluation_reports/) - 測試與評估結果
EOF

# 更新 docs/README.md
# (手動編輯，更新文檔路徑)

# 更新 .gitignore
cat >> .gitignore << 'EOF'

# Backups
*.backup
*.bak
*.old

# Temporary test outputs
output/multi_intent_test_*.json
output/scoring_quality_test_*.json
output/*_test_*.json
EOF

# 提交更改
git add .
git status

echo "📝 請檢查 git status，確認無誤後執行："
echo "git commit -m 'docs: 系統文件整理與歸檔"
echo ""
echo "- 清理重複的測試場景數據"
echo "- 整合並歸檔文檔（回測、完成報告、評估報告等）"
echo "- 刪除備份和臨時文件"
echo "- 重組文檔結構（guides, features, api, archive）"
echo "- 將 database migrations 納入版本控制"
echo "- 移動測試腳本至 tests/ 目錄"
echo "'"

echo "✅ Phase 5 準備完成"
```

---

## 檢查清單

### 執行前檢查

- [ ] 已備份資料庫
- [ ] 已備份整個專案目錄
- [ ] 已確認 git status 乾淨（或已記錄當前變更）
- [ ] 已檢查是否有正在進行的工作

### 執行後驗證

#### 資料庫
- [ ] test_scenarios 表無重複數據（應為 12 條）
- [ ] 所有表正常運作
- [ ] 觸發器和約束正常

#### 文件結構
- [ ] docs/ 目錄結構清晰（guides, features, api, archive）
- [ ] 根目錄僅保留關鍵文檔（README, QUICKSTART 等）
- [ ] 無備份文件（.backup, .bak）
- [ ] 測試腳本已移至 tests/

#### 版本控制
- [ ] database/migrations/ 已納入版本控制
- [ ] database/init/ 已納入版本控制
- [ ] 所有重要文檔已追蹤
- [ ] .gitignore 已更新

#### 功能測試
- [ ] 前端所有頁面可正常訪問
- [ ] 統一審核中心正常運作
- [ ] 回測功能正常
- [ ] 資料庫 CRUD 操作正常

---

## 預期成果

### 文件數量變化

**根目錄 .md 文件**: 18 個 → 7 個
- 保留：README.md, QUICKSTART.md, README_DEPLOYMENT.md, CHANGELOG.md, DOCKER_COMPOSE_GUIDE.md, PGVECTOR_SETUP.md
- 刪除/移動：11 個

**docs/ 文件**: 37 個 → 20 個核心文檔 + 歸檔
- 核心文檔：guides (5), features (4), api (2), planning (1), architecture (1)
- 歸檔文檔：completion_reports (11), evaluation_reports (4), fix_reports (4), design_docs (2), deprecated_guides (3)

**備份文件**: 3 個 → 0 個

**測試腳本**: 5 個散落 → 移至 tests/integration/

### 磁碟空間節省

- 刪除臨時 JSON: ~10KB
- 移動 Excel 到 examples: ~110KB
- 整體組織改善，無顯著空間節省（主要是結構優化）

### 維護性改善

✅ 文檔結構清晰，易於查找
✅ 歷史記錄歸檔，不影響主線閱讀
✅ Migration 有版本控制和追蹤
✅ 測試代碼組織良好
✅ 減少根目錄混亂

---

## 附錄

### A. 快速執行腳本

將上述 5 個 Phase 的腳本保存為單獨的 .sh 文件，然後：

```bash
# 賦予執行權限
chmod +x cleanup_phase*.sh

# 執行（按順序）
./cleanup_phase2_archive.sh
./cleanup_phase3_remove.sh
./cleanup_phase4_migrations.sh
./cleanup_phase5_commit.sh

# Phase 1 需要手動執行（資料庫操作）
```

### B. 回滾計劃

如果需要回滾：

```bash
# Git 回滾
git reset --hard HEAD~1

# 資料庫回滾
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin < backup_before_cleanup_YYYYMMDD.sql
```

### C. 聯絡人

如有疑問，請聯繫：
- 開發團隊
- 專案負責人

---

**報告生成時間**: 2025-10-12 02:30
**報告版本**: 1.0
**狀態**: ✅ 完成，待執行
