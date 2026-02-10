# 📦 部署文件目錄

此目錄存放所有部署相關文件，包括通用部署指南和特定版本的部署文件。

## 🚀 快速開始

### 從 fa4d9a6 更新到最新版本（⭐ 推薦）
```bash
cat docs/deployment/DEPLOY_FROM_FA4D9A6_TO_LATEST.md
```
**適用情境**：從生產環境版本（fa4d9a6）升級到最新版本（e3a6ff9）

### 日常小更新（沒有資料庫遷移）
```bash
cat docs/deployment/DEPLOY_GUIDE.md
```

### 首次部署 2026-01-10 版本（有遷移）
```bash
cat docs/deployment/2026-01-10/QUICK_DEPLOY_2026-01-10.md
# 或
bash docs/deployment/2026-01-10/deploy_2026-01-10.sh
```

### 搭配檢查清單使用
```bash
cat docs/deployment/DEPLOY_CHECKLIST.md
```

## 📂 目錄結構

```
deployment/
├── README.md                    ← 本文件（部署索引）
├── DEPLOY_GUIDE.md              ← 通用部署指南
├── DEPLOY_CHECKLIST.md          ← 通用檢查清單
└── 2026-01-10/                  ← 2026-01-10 版本部署
    ├── DEPLOY_README_2026-01-10.md
    ├── QUICK_DEPLOY_2026-01-10.md
    ├── PRODUCTION_DEPLOY_2026-01-10.md
    └── deploy_2026-01-10.sh
```

## 🎯 使用說明

### 📋 通用部署文件

**DEPLOY_GUIDE.md** - 通用部署指南
- 適用於日常小更新
- 沒有資料庫遷移
- 沒有特殊配置需求
- 包含標準部署流程（拉取代碼 → 判斷變更 → 選擇方案 → 驗證）

**DEPLOY_CHECKLIST.md** - 標準檢查清單
- 每次部署都可參考
- 確保不遺漏步驟
- 適合搭配其他部署文件使用

### 🚀 特定版本部署文件

**使用情境：**
- ✅ 首次部署某個特定版本
- ✅ 該版本包含資料庫遷移
- ✅ 該版本有特殊的部署步驟
- ✅ 需要追溯歷史部署記錄

**文件位置：**
- 按日期（版本號）組織在子目錄下
- 例如：`2026-01-10/`

## 📋 版本列表

### 2026-01-10
**主要更新：**
- 動態表單收集系統
- 表單審核與編輯
- 表單狀態管理與備註
- 知識庫缺失欄位補充（form_id, video_url, trigger_form_condition 等）
- 修復前端 sidebarCollapsed 錯誤

**部署文件：**
- [DEPLOY_README_2026-01-10.md](2026-01-10/DEPLOY_README_2026-01-10.md) - 部署索引
- [QUICK_DEPLOY_2026-01-10.md](2026-01-10/QUICK_DEPLOY_2026-01-10.md) - 快速部署
- [PRODUCTION_DEPLOY_2026-01-10.md](2026-01-10/PRODUCTION_DEPLOY_2026-01-10.md) - 完整部署
- [deploy_2026-01-10.sh](2026-01-10/deploy_2026-01-10.sh) - 自動化腳本

**資料庫遷移：**
- `database/migrations/add_knowledge_base_missing_columns.sql`
- `database/migrations/create_form_tables.sql`
- `database/migrations/add_form_schema_description_fields.sql`
- `database/migrations/add_form_sessions_trigger_fields.sql`
- `rag-orchestrator/database/migrations/create_digression_config.sql`
- `database/migrations/add_form_submission_status.sql`

---

### 2026-01-21
**主要更新：**
- **Critical P0**：Knowledge Admin API 整合修復（action_type 和 api_config 欄位支援）
- API Endpoints 動態管理功能
- 表單系統增強
- 文檔結構重組優化

**部署文件：**
- [DEPLOY_2026-01-21.md](archive/2026-01-21/DEPLOY_2026-01-21.md) - 完整部署指南

**資料庫遷移：**
- `database/migrations/add_action_type_and_api_config.sql` - 新增知識庫動作類型和 API 配置
- `database/migrations/create_api_endpoints_table.sql` - 創建 API 端點管理表
- `database/migrations/upgrade_api_endpoints_dynamic.sql` - 升級為動態 API 管理
- `database/migrations/configure_billing_inquiry_examples.sql` - 配置帳單查詢範例
- `database/migrations/remove_handler_function_column.sql` - 移除已棄用欄位

**相關文檔：**
- [API 整合完整修復報告](../fixes/2026-01-21-api-integration-fix.md)
- [API 整合深度分析](../fixes/2026-01-21-api-integration-analysis.md)
- [API 整合測試指南](../testing/api-integration-testing-guide.md)
- [文檔重組報告](../DOCS_REORGANIZATION_REPORT_2026-01-21.md)

---

### 2026-01-13
**主要更新：**
- 統一檢索路徑（commit cbf4c4f）- 使意圖成為純排序因子
- 前端表單編輯器增加 prompt 欄位必填驗證（commit ba503d3）
- 移除 form_intro 欄位，統一使用表單 default_intro（commit 781a7c0）

**部署文件：**
- [DEPLOY_2026-01-13.md](archive/2026-01-13/DEPLOY_2026-01-13.md) - 整合部署指南（包含所有更新）

**資料庫遷移：**
- `database/migrations/remove_form_intro_2026-01-13.sql` - 刪除 knowledge_base.form_intro 欄位

**相關文檔：**
- [統一檢索路徑實施報告](../implementation/FINAL_2026-01-13.md)
- [表單引導語改善報告](../features/FORM_GUIDANCE_IMPROVEMENT_2026-01-13.md)

---

### 2026-01-22
**主要更新：**
- **Migration 追蹤系統**：建立 `schema_migrations` 表，解決推版漏掉欄位問題
- **自動執行腳本**：`database/run_migrations.sh` 支援 dry-run、自動備份、交互式確認
- **安全機制**：冪等性、錯誤停止、執行記錄、回滾指南
- **文檔完善**：完整的 Migration 使用說明和 FAQ

**部署文件：**
- [DEPLOY_2026-01-22.md](archive/2026-01-22/DEPLOY_2026-01-22.md) - Migration 系統部署指南

**資料庫遷移：**
- `database/migrations/000_create_schema_migrations.sql` - 創建 Migration 追蹤表
- 所有歷史 migration (17 個) - 自動追蹤和執行

**核心工具：**
- `database/run_migrations.sh` - Migration 自動執行腳本（安全加強版）
- `database/migrations/README.md` - Migration 完整文檔

**重要特性：**
- ✅ 自動追蹤已執行的 migration
- ✅ Dry-run 模式預覽變更
- ✅ 自動備份資料庫
- ✅ 失敗自動停止並提供回滾命令
- ✅ 防止重複執行

**使用方法：**
```bash
# 預覽即將執行的 migration
./database/run_migrations.sh docker-compose.prod.yml --dry-run

# 執行 migration（自動備份）
./database/run_migrations.sh docker-compose.prod.yml

# 交互式執行（需要確認）
./database/run_migrations.sh docker-compose.prod.yml --interactive
```

---

### 2026-01-28 ⭐⭐⭐ 最新

**主要更新：**
- **🔄 Reranker 二階段檢索** ⭐⭐⭐⭐⭐：Knowledge 準確率提升 3 倍（25%→75%）
- **🎯 智能檢索系統** ⭐⭐⭐⭐⭐：SOP 與知識庫並行檢索 + 分數比較決策
- **⚡ 意圖加成優化** ⭐⭐⭐：效能提升 5-10%，代碼簡化 -46 行
- **🎨 前端改進**：新增 Rerank 分數顯示，移除混亂欄位（11 欄 → 8 欄）
- **🔧 觸發模式改進**：immediate 模式確認提示詞改為可選（系統預設）

**部署文件：**
- [DEPLOYMENT_2026-01-28.md](DEPLOYMENT_2026-01-28.md) - 完整部署指南（含回滾計畫）

**技術文檔：**
- [SMART_RETRIEVAL_IMPLEMENTATION.md](../SMART_RETRIEVAL_IMPLEMENTATION.md) - 智能檢索完整實施報告
- [SMART_RETRIEVAL_QUICK_REF.md](../SMART_RETRIEVAL_QUICK_REF.md) - 快速參考指南
- [RERANKER_FEATURE.md](../features/RERANKER_FEATURE.md) - Reranker 功能文檔
- [CHANGELOG_2026-01-28.md](../CHANGELOG_2026-01-28.md) - 詳細更新日誌
- [INTENT_BOOST_OPTIMIZATION_2026-01-28.md](../fixes/INTENT_BOOST_OPTIMIZATION_2026-01-28.md) - 意圖加成優化

**主要代碼變更：**
- `rag-orchestrator/requirements.txt` - 新增 Reranker 依賴
  - `sentence-transformers==5.2.2`
  - `torch==2.5.0`
- `rag-orchestrator/routers/chat.py` - 智能檢索系統核心邏輯
  - Lines 515-850: `_smart_retrieval_with_comparison` 函數
  - Lines 621: SCORE_GAP_THRESHOLD = 0.15
  - Lines 852-964: comparison_metadata 傳遞修復
  - Lines 1622-1647: SOP 候選結構修復
- `rag-orchestrator/services/vendor_knowledge_retriever.py` - Reranker 整合
  - 移除無效意圖加成計算（-54 行）
  - 10% base + 90% rerank 混合策略
- `rag-orchestrator/services/vendor_sop_retriever.py` - SOP Reranker
  - 移除 SQL 意圖加成計算（-9 行）
- `knowledge-admin/frontend/src/views/ChatTestView.vue` - 前端改進
  - Lines 160: 新增 Rerank 分數欄位
  - Lines 210: 移除無效欄位（意圖加成、意圖相似度、Scope權重）
  - Lines 707, 726: 處理路徑和 LLM 策略映射
- `docker-compose.yml` - 環境變數配置
  - Lines 226-227: ENABLE_RERANKER, ENABLE_KNOWLEDGE_RERANKER

**資料庫遷移：**
- `database/migrations/add_trigger_mode_to_knowledge_base.sql` - 新增觸發模式欄位
  - 新增 `trigger_mode` VARCHAR(20) DEFAULT NULL
  - 新增 `immediate_prompt` TEXT

**部署步驟（重要）：**
1. ⚠️ **備份資料庫**（必須！）
2. 執行 Migration：`./database/run_migrations.sh docker-compose.yml`
3. 停止服務：`docker-compose down`
4. **重新構建**：`docker-compose build --no-cache rag-orchestrator knowledge-admin-api`（5-8 分鐘）
5. 啟動服務：`docker-compose up -d`
6. 首次啟動會下載 Reranker 模型（~500MB，需 2-3 分鐘）
7. 重建前端（如需要）：`cd knowledge-admin/frontend && npm run build`
8. 執行測試：`/tmp/test_smart_retrieval.sh`

**部署效果：**
- ✅ Knowledge 準確率：25% → **75%** (+200%) 🚀
- ✅ 檢索效能：提升 **5-10%**
- ✅ 代碼簡化：**-46 行** 無效邏輯
- ✅ 前端優化：11 欄 → **8 欄**
- ✅ 響應時間：+50-100ms（Rerank 開銷，可接受）

**停機時間：** ~2 分鐘（完整重建 + 依賴安裝）

**風險評估：** 🟡 中風險（需重新構建，但已大量測試）

**特別注意：**
- ⚠️ 首次啟動需下載模型（~500MB），請確保網路暢通
- ⚠️ 需要磁碟空間 ≥ 5GB（依賴 + 模型）
- ⚠️ 建議深夜或週末部署（2 分鐘停機）

**監控重點（1 週）：**
- Knowledge 準確率 ≥ 75%
- SOP 準確率 ≥ 90%
- 平均響應時間 < 500ms
- 服務可用性 ≥ 99.9%

---

### 2026-01-26

#### 更新 1: Primary Embedding 修復
**主要更新：**
- **Primary Embedding 修復** ⭐⭐⭐：解決向量稀釋問題
- **涵蓋率大幅提升**：66.7% → 92.6% (+25.9%)
- **關鍵問題修復**：「垃圾要怎麼丟」等問題正確匹配
- **零誤配風險**：False Positive 保持 0%
- **Embeddings 重新生成**：56 個 SOP 全部更新

**部署文件：**
- [DEPLOYMENT_2026-01-26_PRIMARY_EMBEDDING_FIX.md](DEPLOYMENT_2026-01-26_PRIMARY_EMBEDDING_FIX.md) - 完整部署記錄

**技術文檔：**
- [PRIMARY_EMBEDDING_FIX.md](../features/PRIMARY_EMBEDDING_FIX.md) - 技術詳細說明
- [DUAL_EMBEDDING_RETRIEVAL.md](../features/DUAL_EMBEDDING_RETRIEVAL.md) - 雙 Embedding 檢索
- [threshold_evaluation_report.md](../../threshold_evaluation_report.md) - 閾值評估報告

**代碼變更：**
- `rag-orchestrator/services/sop_embedding_generator.py` - Primary Embedding 修復

**部署步驟：**
1. 修改 `sop_embedding_generator.py`（Line 51-56）
2. 重啟 `rag-orchestrator` 服務
3. 重新生成 56 個 SOP embeddings（100% 成功）
4. 驗證測試通過（涵蓋率 92.6%）

**部署效果：**
- ✅ 涵蓋率：66.7% → **92.6%** (+25.9%)
- ✅ 誤配率：保持 **0%**
- ✅ 關鍵問題：「垃圾要怎麼丟」正確匹配「垃圾收取規範」
- ✅ 響應時間：無影響（~200ms）
- ✅ 服務可用性：100%

**停機時間：** ~30 秒（服務重啟）

**風險評估：** 🟢 低風險（事前大量測試，100% 成功率）

---

#### 更新 2: SOP 流程配置嚴格限制 ⭐⭐⭐
**主要更新：**
- **嚴格組合驗證** ⭐⭐⭐：實施 7 種有效組合規則
- **動態選項限制**：根據觸發模式自動過濾選項
- **自動調整機制**：切換模式時自動調整為有效組合
- **前後端雙重驗證**：確保配置可靠性
- **必填欄位驗證**：防止遺漏關鍵配置
- **動態關鍵詞組合**：觸發關鍵詞不再硬編碼
- **API 端點修正**：統一使用 /v1/ 前綴

**功能文檔：**
- [SOP_FLOW_STRICT_VALIDATION_2026-01-26.md](../features/SOP_FLOW_STRICT_VALIDATION_2026-01-26.md) - 完整實施文檔

**代碼變更：**
- `knowledge-admin/frontend/src/components/VendorSOPManager.vue` - 前端驗證邏輯
  - Lines 354-378: 動態下拉選單
  - Lines 510-516: VALID_COMBINATIONS 定義
  - Lines 888-893: 保存前驗證
  - Lines 1124-1142: API 端點修正
  - Lines 1157-1180: 自動調整邏輯
- `rag-orchestrator/routers/vendors.py` - 後端驗證邏輯
  - Lines 589-603: Pydantic 模型更新
  - Lines 733-761: 組合與必填欄位驗證
  - Lines 801-824: SQL 更新
- `rag-orchestrator/services/sop_trigger_handler.py` - 動態關鍵詞組合
  - Lines 222-241: 動態組合邏輯

**測試結果：**
- ✅ 後端測試：**8/8 全部通過 (100%)**
  - 3 個有效組合測試 (200 OK)
  - 2 個無效組合測試 (400 Bad Request)
  - 3 個必填欄位測試 (400 Bad Request)
- ✅ 前端測試指南：10 個檢查點

**部署步驟：**
1. 修改前端 `VendorSOPManager.vue`（動態驗證邏輯）
2. 修改後端 `vendors.py`（組合與必填驗證）
3. 修改 `sop_trigger_handler.py`（動態關鍵詞）
4. 重啟 `knowledge-admin` 和 `rag-orchestrator` 服務
5. 重新生成 66 個 SOP embeddings（100% 成功）
6. 執行測試驗證（8/8 通過）

**部署效果：**
- ✅ 用戶體驗：動態選項限制，減少選擇困惑
- ✅ 配置可靠性：嚴格驗證防止無意義組合
- ✅ 數據一致性：前後端雙重驗證
- ✅ 維護成本：清晰的規則，易於理解和維護
- ✅ API 修正：表單和 API 端點正確載入
- ✅ Embeddings 更新：移除硬編碼關鍵詞

**符合率：** 89.4% (59/66 SOP 符合嚴格限制規則)

**停機時間：** ~30 秒（服務重啟）

**風險評估：** 🟢 低風險（100% 測試通過，前後端雙重驗證）

---

## 🆕 新增版本

當有新版本需要特殊部署步驟時，請按以下方式組織：

1. 創建新目錄：`docs/deployment/YYYY-MM-DD/`
2. 複製模板文件並修改內容
3. 更新本 README，添加版本記錄
4. 在 `docs/DEPLOYMENT_CLEANUP_YYYY-MM-DD.md` 記錄整理過程

---

---

## 🔥 重點推薦

### 生產環境升級指南
如果您的生產環境目前是 **fa4d9a6 版本**，請使用：
- **[DEPLOY_FROM_FA4D9A6_TO_LATEST.md](DEPLOY_FROM_FA4D9A6_TO_LATEST.md)** - 完整的從 fa4d9a6 到 e3a6ff9 的升級指南

這份文檔包含：
- ✅ 5 個 commit 的完整變更說明
- ✅ 4 個資料庫 migration 的詳細步驟
- ✅ 新依賴安裝指南（sentence-transformers, torch）
- ✅ Reranker 模型下載說明
- ✅ 完整的回滾計畫
- ✅ 1 週監控策略
- ✅ 詳細的檢查清單

---

**最後更新**：2026-01-28
