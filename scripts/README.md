# Scripts 目錄

此目錄包含項目的生產環境腳本和工具。

## 📁 目錄結構

### `/scripts/` (根目錄)
生產環境使用的核心腳本：

- **`generate_sop_embeddings.py`** - 生成 SOP 雙 Embedding（Primary + Fallback）
  - 支援批次處理和進度恢復
  - 自動向量化策略選擇
  - Primary: group_name + item_name
  - Fallback: content only

- **`import_sop_from_excel.py`** - 從 Excel 批量導入 SOP 到資料庫
  - 支援業者 SOP 和平台 SOP
  - 自動處理意圖關聯
  - 自動觸發 embedding 生成

- **`process_line_chats.py`** - 處理 LINE 聊天記錄並提取知識
  - 自動分類知識類型
  - 整理為結構化格式

---

### 部署腳本

#### 生產環境部署（根目錄）

- **`deploy_local_build.sh`** - 【方案 A】在本地構建前端並打包
  - 適用於小規格伺服器（≤ 2GB RAM）
  - 執行位置：開發機器
  - 輸出：`dist_YYYYMMDD_HHMMSS.tar.gz`

- **`deploy_server_prebuilt.sh`** - 【方案 A】部署預構建的前端到伺服器
  - 適用於小規格伺服器
  - 執行位置：生產伺服器
  - 自動備份、遷移、驗證

詳細使用指南：[方案 A 部署指南](../docs/DEPLOYMENT_PLAN_A.md)

#### 開發和維護（`/scripts/deployment/`）

詳見 [`deployment/README.md`](./deployment/README.md)

- `setup.sh` - 環境初始化
- `start_rag_services.sh` - RAG 服務啟動
- `deploy-frontend.sh` - 前端部署（開發模式）

---

### `/scripts/knowledge_extraction/`
知識提取和測試場景生成：

- **`extract_knowledge_and_tests.py`** - 從文檔提取知識和測試場景
- **`import_excel_to_kb.py`** - Excel 知識庫導入
- **`reclassify_knowledge_intents.py`** - 重新分類知識意圖
- **`monitor_and_autorun.sh`** - 監控和自動執行腳本

### `/scripts/backtest/`
回測框架和測試執行：

- **`backtest_framework_async.py`** - 異步回測框架（並發執行測試場景）
- **`run_backtest_with_db_progress.py`** - 資料庫整合的回測執行腳本
- **`README.md`** - 回測框架使用說明

推薦使用管理後台的「回測」頁面執行（開發環境：http://localhost:8087/backtest）

---

## 🚀 使用說明

### 部署腳本

#### 方案 A：本地構建 + 預構建部署（推薦用於小規格伺服器）

```bash
# 步驟 1: 在開發機器上構建
cd /path/to/AIChatbot
bash scripts/deploy_local_build.sh
# 輸出: dist_20251103_120000.tar.gz

# 步驟 2: 上傳到伺服器
scp dist_20251103_120000.tar.gz user@server:/path/to/AIChatbot/
scp docker-compose.prod-prebuilt.yml user@server:/path/to/AIChatbot/
scp scripts/deploy_server_prebuilt.sh user@server:/path/to/AIChatbot/scripts/

# 步驟 3: 在伺服器上部署
ssh user@server
cd /path/to/AIChatbot
bash scripts/deploy_server_prebuilt.sh dist_20251103_120000.tar.gz
```

詳細說明請參考：[方案 A 部署指南](../docs/DEPLOYMENT_PLAN_A.md)

### 生產工具腳本

```bash
# 生成 SOP Embeddings（批次處理）
python scripts/generate_sop_embeddings.py --batch-size 10

# Dry-run 模式（測試不寫入）
python scripts/generate_sop_embeddings.py --dry-run

# 從特定 ID 開始處理
python scripts/generate_sop_embeddings.py --start-id 100

# 從 Excel 導入 SOP
python scripts/import_sop_from_excel.py --file data/sop.xlsx

# 處理 LINE 聊天記錄
python scripts/process_line_chats.py
```

---

## 🧪 測試

本項目使用正式的測試框架，測試文件位於：

- **`/tests/integration/`** - 整合測試（10+ 個測試）
  - `test_multi_intent_rag.py` - 多意圖 RAG 檢索測試
  - `test_business_logic_matrix.py` - 業務邏輯矩陣測試
  - `test_scoring_quality.py` - 評分質量測試
  - 等等...

- **`/rag-orchestrator/tests/`** - 單元測試（4 個測試）
  - `test_answer_synthesis.py` - 答案合成測試
  - `test_intent_manager.py` - 意圖管理測試
  - 等等...

運行測試：
```bash
# 運行整合測試
cd tests && bash run_business_logic_tests.sh

# 運行單元測試
cd rag-orchestrator/tests && python test_answer_synthesis.py
```

---

## 📋 相關目錄

- **`/database/seeds/`** - SQL 種子數據文件
- **`/tests/`** - 整合測試和單元測試
- **`/rag-orchestrator/services/`** - RAG 核心服務

---

## 📝 腳本開發指南

### 添加新腳本

1. **確定類別**：根據功能選擇正確的子目錄
   - 生產工具 → 根目錄
   - 部署相關 → `deployment/`
   - 知識提取 → `knowledge_extraction/`
   - **測試腳本** → `/tests/integration/` (正式測試)

2. **腳本規範**：
   ```python
   #!/usr/bin/env python3
   """
   腳本簡短說明

   詳細功能描述
   使用方式
   """
   ```

3. **更新文檔**：在本 README 中添加腳本說明

### 最佳實踐

- ✅ 使用命令行參數（`argparse`）
- ✅ 提供 `--dry-run` 模式（對於修改資料的腳本）
- ✅ 添加進度顯示（對於長時間運行的腳本）
- ✅ 錯誤處理和日誌記錄
- ✅ 在腳本頭部添加詳細註釋

---

## 🗑️ 已移除的腳本

以下腳本已完成任務並移除（2025-10-29）：

### 分析工具（已完成）
- `analysis/analyze_sop_vectorization.py` - 向量化策略分析（策略已確定）
- `analysis/compare_intent_boost_weights.py` - Intent Boost 權重測試（權重已確定為 1.3x/1.1x）

### 遷移腳本（已執行）
- `migrations/migrate_sop_to_templates.py` - SOP 架構遷移（28 templates 已建立）
- `migrations/migration_add_sop_embeddings.sql` - 添加 Embedding 欄位（138 SOPs 完成）

### 臨時驗證腳本（已完成驗證）
- `tests/test_embedding_retrieval.py` - Embedding 檢索驗證（功能已穩定，正式測試已覆蓋）
- `tests/test_hybrid_sop_retrieval.py` - 混合檢索驗證（功能已穩定，正式測試已覆蓋）
- `tests/test_sop_async_embedding.py` - 異步生成驗證（功能已穩定）

**注意**: 正式測試請使用 `/tests/integration/` 中的測試套件。

如需查閱這些腳本，請參考 Git 歷史記錄。

---

**最後更新：** 2025-11-03
**版本：** v4.1 - 新增方案 A 部署腳本（適用於小規格伺服器）
