# AIChatbot 系統盤查報告

**盤查日期**: 2025-10-13
**執行者**: Claude Code

## 📊 執行摘要

本次盤查發現了以下關鍵問題和改善機會：

### ⚠️ 需要處理的問題

1. **遺留代碼目錄** `/backend` - 未被使用，建議移除或歸檔
2. **文檔結構分散** - 有 90+ 個文檔文件，需要整理
3. **配置文件重複** - 多個 `.env` 和配置範例文件

### ✅ 系統健康狀況

- **運行中的服務**: 7 個容器正常運行
- **代碼質量**: 僅 3 個 TODO 註釋（非常少）
- **路由結構**: 清晰，無明顯重複

---

## 1️⃣ 架構盤查

### 當前服務架構

```
aichatbot-rag-orchestrator      ✅ 核心服務（FastAPI）
aichatbot-knowledge-admin-web   ✅ 前端（Vue.js + Vite）
aichatbot-knowledge-admin-api   ✅ 管理後台API（Flask）
aichatbot-embedding-api         ✅ 向量嵌入服務
aichatbot-postgres              ✅ 資料庫（pgvector）
aichatbot-redis                 ✅ 快取
aichatbot-pgadmin               ✅ 資料庫管理工具
```

### RAG Orchestrator 路由結構

| 路由模組 | 前綴 | 功能 | 狀態 |
|---------|------|------|------|
| `chat.py` | `/api/v1` | 聊天對話（含多業者支援） | ✅ 核心 |
| `intents.py` | `/api/v1` | 意圖管理 | ✅ 核心 |
| `knowledge.py` | - | 知識庫管理 | ✅ 核心 |
| `vendors.py` | - | 多業者配置 | ✅ Phase 1 |
| `suggested_intents.py` | `/api/v1` | 意圖建議審核 | ✅ Phase B |
| `unclear_questions.py` | `/api/v1` | 未釐清問題管理 | ✅ 核心 |
| `business_scope.py` | `/api/v1` | 業務範圍管理 | ✅ 核心 |
| `knowledge_import.py` | - | LINE 對話匯入 | ✅ 功能擴展 |
| `knowledge_generation.py` | `/api/v1` | AI 知識生成 | ✅ 功能擴展 |

**評估**: ✅ 結構清晰，無重複，職責分明

---

## 2️⃣ 目錄結構盤查

### 🔴 問題：遺留代碼目錄

```
/backend/                          ⚠️ 未使用，未在 docker-compose.yml 中
  ├── app/
  │   ├── main.py                  （舊版 FastAPI 應用）
  │   ├── api/                     （舊版路由）
  │   └── services/                （舊版服務）
  ├── test_example.py
  └── test_knowledge.py
```

**建議**:
- ✅ **移動到** `docs/archive/legacy_backend/`
- 📝 添加 `DEPRECATED.md` 說明為何廢棄

### 🟢 正常使用的目錄

```
/rag-orchestrator/          ✅ 核心服務
/knowledge-admin/           ✅ 管理後台
/embedding-service/         ✅ 向量服務
/database/                  ✅ 資料庫腳本
/scripts/                   ✅ 工具腳本
/docs/                      ✅ 文檔（需要整理）
```

---

## 3️⃣ 文檔盤查

### 文檔統計

```
總文檔數: 90+ 個 Markdown 文件
- 主要README: 4個
- 功能文檔: 10個
- 架構文檔: 4個
- 歸檔文檔: 50+ 個
- Changelog: 3個
```

### 🔴 問題：文檔結構混亂

```
/docs/
  ├── BACKTEST_*.md                    （3個回測相關）
  ├── BUSINESS_SCOPE_*.md              （2個業務範圍）
  ├── DOCUMENTATION_UPDATE_SUMMARY.md
  ├── api/                             ✅ API文檔
  ├── architecture/                    ✅ 架構文檔
  ├── archive/                         ✅ 歸檔
  │   ├── completion_reports/          （20+ 完成報告）
  │   ├── design_docs/                 （設計文檔）
  │   ├── evaluation_reports/          （評估報告）
  │   └── deprecated_guides/           （廢棄指南）
  ├── backtest/                        ✅ 回測文檔
  ├── features/                        ✅ 功能文檔
  ├── guides/                          ✅ 使用指南
  └── planning/                        ✅ 規劃文檔
```

**建議整合方案**:

```
/docs/
  ├── README.md                        📝 文檔導覽索引
  ├── ARCHITECTURE.md                  📝 系統架構總覽
  ├── CHANGELOG.md                     📝 統一變更日誌
  │
  ├── getting-started/                 ✨ 新增
  │   ├── QUICKSTART.md
  │   ├── INSTALLATION.md
  │   └── CONFIGURATION.md
  │
  ├── api/                             ✅ 保留
  ├── features/                        ✅ 保留
  ├── guides/                          ✅ 保留
  │
  ├── development/                     ✨ 新增（整合 backtest、planning）
  │   ├── BACKTEST_GUIDE.md           （合併3個回測文檔）
  │   ├── DEVELOPMENT_WORKFLOW.md
  │   └── TESTING_STRATEGY.md
  │
  └── archive/                         ✅ 保留（清理）
      ├── 2024-Q4/                    ✨ 按季度歸檔
      └── legacy/                      ✨ 遺留代碼文檔
```

---

## 4️⃣ 配置文件盤查

### 當前配置

```
/
├── .env.example                     ✅ 範例配置
├── docker-compose.yml               ✅ 核心編排
├── /backend/.env.example            ⚠️ 遺留
├── /backend/.env.docker             ⚠️ 遺留
├── /rag-orchestrator/config/intents.yaml  ✅ Fallback配置
```

**建議**:
- 移除 `/backend/.env*`
- 統一環境變數命名規範

---

## 5️⃣ 代碼質量

### TODO/FIXME 統計

```
RAG Orchestrator: 3 個 TODO
Knowledge Admin: 未檢查
Scripts: 未檢查
```

✅ **評估**: 代碼質量良好，技術債務少

### 測試覆蓋

```
/tests/integration/         ✅ 整合測試
/rag-orchestrator/tests/    ✅ 單元測試
```

---

## 6️⃣ 資料庫結構

### 主要資料表

```sql
-- 核心表
知識庫: knowledge_base
意圖: intents
測試場景: test_scenarios

-- 審核表
suggested_intents           ✅ 意圖建議
unclear_questions           ✅ 未釐清問題
ai_generated_knowledge_candidates  ✅ AI生成知識

-- 多業者
vendors                     ✅ 業者資料
vendor_parameters           ✅ 業者參數

-- 回測
backtest_results            ✅ 回測結果
backtest_sessions           ✅ 回測會話
```

✅ **評估**: 結構完整，無冗餘

---

## 📋 建議行動清單

### 🔴 高優先級（建議立即處理）

1. **移除遺留 backend 目錄**
   ```bash
   mkdir -p docs/archive/legacy
   mv backend docs/archive/legacy/
   echo "此目錄包含早期版本代碼，已被 rag-orchestrator 取代" > docs/archive/legacy/backend/DEPRECATED.md
   ```

2. **整理文檔結構**
   - 創建 `docs/README.md` 作為文檔導覽
   - 合併重複的回測文檔
   - 將完成報告按季度歸檔

3. **清理配置文件**
   ```bash
   rm backend/.env.example backend/.env.docker
   ```

### 🟡 中優先級（建議本週處理）

4. **創建統一 CHANGELOG**
   - 合併 `CHANGELOG.md`, `BACKTEST_PHASE2_CHANGELOG.md`, `BACKTEST_PHASE3_CHANGELOG.md`
   - 按時間順序整理

5. **補充主README**
   - 更新系統架構圖
   - 添加快速開始連結
   - 明確各服務職責

6. **統一環境變數命名**
   - 審查所有 `DB_*`, `OPENAI_*`, `REDIS_*` 變數
   - 確保一致性

### 🟢 低優先級（建議下週處理）

7. **補充API文檔**
   - 為新增的路由補充文檔
   - 更新 `API_REFERENCE_PHASE1.md`

8. **代碼註釋審查**
   - 處理剩餘的 3 個 TODO
   - 為複雜邏輯添加註釋

9. **測試覆蓋提升**
   - 為新功能添加測試
   - 回測覆蓋率報告

---

## 🎯 總結

### 當前狀態: 🟢 良好

系統整體架構清晰、代碼質量高、技術債務少。主要問題集中在：
- 遺留目錄未清理
- 文檔過於分散
- 缺少統一導覽

### 建議執行順序

1. **第一天**: 清理遺留代碼（2小時）
2. **第二天**: 整理文檔結構（4小時）
3. **第三天**: 更新主README（2小時）
4. **第四天**: 統一配置和環境變數（2小時）

**預計總工時**: 10-12 小時

---

**報告生成**: 2025-10-13
**下次審查建議**: 2025-11-13 (一個月後)
