# 文件狀態分類報告 — 2026-04-22

**任務**: Task 3 — 活躍文件狀態判定與處理建議
**掃描基準**: `scan_results_2026-04-22.md` 過時關鍵字命中清單
**判定規則**: 關鍵字在標題/核心主題 → 過時；在次要描述 → 待更新；form flow 中的 intent_classifier → 有效

---

## 分類結果

| # | File Path | Status | Action | Reason |
|---|-----------|--------|--------|--------|
| 1 | `docs/implementation/FINAL_2026-01-13.md` | 過時 (outdated) | Archive → `docs/archive/2026-04/` | 主題為「統一檢索路徑」實施報告，核心內容討論 intent_boost 過濾邏輯，該機制已移除 |
| 2 | `docs/implementation/DEDUPLICATION_SUMMARY.md` | 過時 (outdated) | Archive → `docs/archive/2026-04/` | 主題為多意圖知識去重，核心範例展示 intent_boost 計算 (1.15x)，依賴已移除的 intent_boost 機制 |
| 3 | `docs/analysis/retrieval_logic_complete.md` | 過時 (outdated) | Archive → `docs/archive/2026-04/` | 主題為「完整檢索邏輯分析」，目錄含「意圖加成機制」專章，核心引用 intent_boost 與 knowledge_intent_mapping |
| 4 | `docs/analysis/CHAT_FLOW_ANALYSIS_2026-01-24.md` | 待更新 (needs update) | Edit：移除 intent_boost / intent_classifier 過時段落 | 主題為對話流程分析（仍有效），intent_boost 與 intent_classifier 出現在子步驟描述中 |
| 5 | `docs/analysis/retrieval_philosophy.md` | 過時 (outdated) | Archive → `docs/archive/2026-04/` | 主題即為「意圖應該是加分」哲學討論，核心程式碼引用 intent_boost / sql_threshold，該機制已移除 |
| 6 | `docs/features/sop/implementation/VENDOR_SOP_RETRIEVAL_IMPROVEMENT.md` | 過時 (outdated) | Archive → `docs/archive/2026-04/` | 主題為 SOP 檢索改進，核心改動為 intent_boost SQL，該機制已移除 |
| 7 | `docs/fixes/README.md` | 待更新 (needs update) | Edit：更新修復清單，標記 intent_boost 相關條目為已過時 | 主題為修復記錄索引（仍有效），intent_boost 出現在子條目描述中 |
| 8 | `docs/fixes/INTENT_BOOST_OPTIMIZATION_2026-01-28.md` | 過時 (outdated) | Archive → `docs/archive/2026-04/` | 標題即為「意圖加成優化」，整份文件圍繞 intent_boost 移除 |
| 9 | `docs/verification/report_2026-01-13.md` | 過時 (outdated) | Archive → `docs/archive/2026-04/` | 驗證報告針對 intent_boost 過濾邏輯修改，該機制已移除 |
| 10 | `docs/features/MULTI_INTENT_SCORING.md` | 過時 (outdated) | Archive → `docs/archive/2026-04/` | 標題為「多意圖知識評分機制」，核心內容為 knowledge_intent_mapping 表與 intent_boost 評分，均已移除 |
| 11 | `docs/analysis/retrieval_logic_complete.md` | (同 #3) | (同 #3) | knowledge_intent_mapping 命中，與 #3 為同一檔案 |
| 12 | `docs/architecture/DATABASE_SCHEMA.md` | 待更新 (needs update) | Edit：移除 knowledge_intent_mapping 表定義、intents 表定義、gpt-3.5-turbo 範例 | 主題為資料庫 Schema 總覽（仍有效），knowledge_intent_mapping 與 gpt-3.5-turbo 出現在表定義中 |
| 13 | `docs/fixes/2026-01-21-api-integration-fix.md` | 待更新 (needs update) | Edit：移除或標注 IntentMapping model 相關段落 | 主題為 Knowledge Admin API 整合修正（仍有效），IntentMapping 出現在修正細節中 |
| 14 | `docs/fixes/2026-01-21-api-integration-analysis.md` | 待更新 (needs update) | Edit：移除或標注 IntentMapping model 相關段落 | 主題為 API 整合全面盤查（仍有效），IntentMapping 出現在分層檢查細節中 |
| 15 | `docs/API_ENDPOINTS_COMPLETE_INVENTORY.md` | 待更新 (needs update) | Edit：移除 /api/v1/intents 端點區塊 | 主題為 API 端點完整清單（仍有效），/intents 端點僅佔清單中一個區塊 |
| 16 | `docs/api/API_REFERENCE_KNOWLEDGE_ADMIN.md` | 待更新 (needs update) | Edit：移除「意圖管理 API」章節 | 主題為 Knowledge Admin API 參考（仍有效），目錄含「意圖管理 API」章節 |
| 17 | `docs/implementation/AUTH_IMPLEMENTATION_SUMMARY.md` | 待更新 (needs update) | Edit：移除 intent API 端點保護相關描述 | 主題為登入認證實作（仍有效），/intents 出現在受保護端點列表中 |
| 18 | `docs/architecture/SYSTEM_ARCHITECTURE.md` | 待更新 (needs update) | Edit：移除 /intents 路由、suggested_intents 表、intent_classifier.py 描述 | 主題為系統架構總覽（仍有效），過時引用分散在多個子章節中 |
| 19 | `docs/features/AUTH_SYSTEM_README.md` | 待更新 (needs update) | Edit：移除 /intents 路徑引用 | 主題為認證系統說明（仍有效），/intents 出現在受保護路徑列表中 |
| 20 | `docs/design/PERMISSION_SYSTEM_DESIGN.md` | 待更新 (needs update) | Edit：移除 intent 相關權限定義 | 主題為 RBAC 權限系統設計（仍有效），/intents 出現在資源權限列表中 |
| 21 | `docs/guides/api/api-path-conventions.md` | 待更新 (needs update) | Edit：移除 /intents 路徑規範 | 主題為 API 路徑使用規範（仍有效），/intents 出現在端點列表中 |
| 22 | `docs/guides/development/FRONTEND_VERIFY.md` | 過時 (outdated) | Archive → `docs/archive/2026-04/` | 主要內容為驗證前端導航，核心步驟包含「意圖管理」頁面驗證，導航列已無此頁面 |
| 23 | `docs/guides/development/FRONTEND_USAGE_GUIDE.md` | 待更新 (needs update) | Edit：移除「意圖管理頁面」章節 | 主題為前端頁面使用說明（仍有效），意圖管理為其中一個頁面章節 |
| 24 | `docs/guides/deployment/ENVIRONMENT_VARIABLES.md` | 待更新 (needs update) | Edit：移除 INTENT_CLASSIFIER_MODEL 環境變數 | 主題為環境變數參考（仍有效），INTENT_CLASSIFIER_MODEL 為其中一個變數條目 |
| 25 | `docs/guides/getting-started/USER_MANUAL_NON_TECHNICAL.md` | 待更新 (needs update) | Edit：移除 INTENT_CLASSIFIER_MODEL 與 intent_classifier 描述 | 主題為非技術用戶使用手冊（仍有效），過時引用出現在系統說明子章節中 |
| 26 | `docs/architecture/DATABASE_SCHEMA.md` | (同 #12) | (同 #12) | gpt-3.5-turbo 命中，與 #12 為同一檔案 |
| 27 | `docs/architecture/SYSTEM_ARCHITECTURE.md` | (同 #18) | (同 #18) | intent_classifier.py 命中，與 #18 為同一檔案 |
| 28 | `docs/implementation/FINAL_2026-01-13.md` | (同 #1) | (同 #1) | intent_classifier 命中，與 #1 為同一檔案 |
| 29 | `docs/analysis/CHAT_FLOW_ANALYSIS_2026-01-24.md` | (同 #4) | (同 #4) | intent_classifier 命中，與 #4 為同一檔案 |
| 30 | `docs/analysis/CONVERSATION_LOGIC_COMPREHENSIVE_ANALYSIS_2026-02-04.md` | 待更新 (needs update) | Edit：更新架構描述中 intent_classifier 相關段落 | 主題為對話邏輯架構探索報告（仍有效），intent_classifier 出現在架構描述中 |
| 31 | `docs/fixes/README.md` | (同 #7) | (同 #7) | intent_classifier 命中，與 #7 為同一檔案 |
| 32 | `docs/rag-system/RAG_IMPLEMENTATION_PLAN.md` | 待更新 (needs update) | Edit：更新意圖識別模組描述 | 主題為 RAG 系統實作計畫（仍有效），intent_classifier 出現在模組架構描述中 |
| 33 | `docs/guides/getting-started/USER_MANUAL_NON_TECHNICAL.md` | (同 #25) | (同 #25) | intent_classifier 命中，與 #25 為同一檔案 |

---

## 去重統計摘要

| 狀態 | 獨立檔案數 | 檔案列表 |
|------|-----------|---------|
| **過時 (outdated)** → Archive | 9 | FINAL_2026-01-13.md, DEDUPLICATION_SUMMARY.md, retrieval_logic_complete.md, retrieval_philosophy.md, VENDOR_SOP_RETRIEVAL_IMPROVEMENT.md, INTENT_BOOST_OPTIMIZATION_2026-01-28.md, report_2026-01-13.md, MULTI_INTENT_SCORING.md, FRONTEND_VERIFY.md |
| **待更新 (needs update)** → Edit | 14 | CHAT_FLOW_ANALYSIS_2026-01-24.md, fixes/README.md, DATABASE_SCHEMA.md, 2026-01-21-api-integration-fix.md, 2026-01-21-api-integration-analysis.md, API_ENDPOINTS_COMPLETE_INVENTORY.md, API_REFERENCE_KNOWLEDGE_ADMIN.md, AUTH_IMPLEMENTATION_SUMMARY.md, SYSTEM_ARCHITECTURE.md, AUTH_SYSTEM_README.md, PERMISSION_SYSTEM_DESIGN.md, api-path-conventions.md, FRONTEND_USAGE_GUIDE.md, ENVIRONMENT_VARIABLES.md, USER_MANUAL_NON_TECHNICAL.md, CONVERSATION_LOGIC_COMPREHENSIVE_ANALYSIS_2026-02-04.md, RAG_IMPLEMENTATION_PLAN.md |
| **有效 (valid)** — 不處理 | N/A | FORM_FILLING_*.md, LLM_PROVIDER_MIXED_CONFIG_GUIDE.md (form flow intent_classifier 為有效引用) |

> **注意**: 待更新列表中部分檔案有多個過時關鍵字命中（如 DATABASE_SCHEMA.md 同時有 knowledge_intent_mapping 和 gpt-3.5-turbo），編輯時需一併處理。

---

## Archive 目錄現況 (Task 3.3)

```
docs/archive/
├── 2025-Q4/                  ← 季度歸檔
├── 2026-01-13/               ← 日期歸檔
├── 2026-02-12/               ← 日期歸檔
├── 2026-04/                  ← ⚠️ 尚未建立，需建立此目錄供本次歸檔使用
├── api/
├── architecture/
├── auth_testing/
├── backups/
├── cleanup_reports/
├── completion_reports/
├── database_migrations/
├── design_docs/
├── design_research_2025-10/
├── evaluation_reports/
├── fix_reports/
├── hotfixes/
├── llm_reference/
├── migrations_history/
├── planning/
├── sop_guides/
├── sop_implementation/
├── sop_reports/
└── (多個獨立 .md 檔案)
```

**建議**: 建立 `docs/archive/2026-04/` 目錄，將 9 個過時檔案移入。
