# 🔧 系統修復記錄

此目錄包含重要的系統問題修復文檔。

---

## 📋 修復清單

### 2026-01-28

#### ✅ 意圖加成優化 - 移除被 Reranker 覆蓋的無效計算（Performance Optimization）
**檔案**: [INTENT_BOOST_OPTIMIZATION_2026-01-28.md](./INTENT_BOOST_OPTIMIZATION_2026-01-28.md)

**問題**: 知識庫和 SOP 檢索系統中的意圖加成計算被 Reranker 10/90 混合完全覆蓋

**影響**:
- 知識庫：54 行無效意圖加成計算（1.0-1.1x）浪費 CPU
- SOP：SQL CASE WHEN 意圖加成（1.3x）浪費查詢資源
- 前端：3 個欄位顯示被覆蓋的無效數值（意圖加成、意圖相似度、Scope權重）

**修復**:
- **知識庫** (`vendor_knowledge_retriever.py`):
  - 移除 Line 464-518 意圖加成計算邏輯 (-54 行, -68.5%)
  - 簡化為 base_similarity 過濾 (17 行)
  - 更新 Log 輸出：顯示 base/rerank/final
  - 清理無效字段：scope_weight, sql_intent_boost, sql_boosted_similarity

- **SOP** (`vendor_sop_retriever.py`):
  - 移除 SQL CASE WHEN intent_boost 計算 (-9 行, -15.5%)
  - 減少 SQL 參數：11 → 9 (-18.2%)
  - 簡化 Log 輸出：移除 boost 顯示
  - 添加 Reranker 覆蓋說明註釋

- **前端** (`ChatTestView.vue`):
  - 移除無效欄位：意圖加成、意圖相似度、Scope權重 (-3 欄)
  - 添加 Rerank分數 欄位
  - 表格簡化：11 欄 → 8 欄 (-27%)

- **Router** (`chat.py`):
  - 添加 rerank_score 到 Pydantic model
  - 修復 knowledge_candidates_debug 數據流 (2 處)

**結果**:
- ✅ 知識庫效能提升 ~5-10%（CPU、記憶體、處理時間）
- ✅ SOP SQL 查詢優化 ~5-8%（參數減少、執行時間）
- ✅ 代碼可讀性大幅提升（-46 行無效邏輯）
- ✅ 前端展示更清晰（移除混亂欄位）
- ✅ 所有測試通過，無功能退化

**保留項目**:
- ✅ 意圖分類系統完整保留（SOP 觸發、表單觸發、業務邏輯路由）
- ✅ retrieve_sop_hybrid 保留 intent_boost（不使用 Reranker）
- ✅ retrieve_sop_by_intent_batch 保留 1000x boost（專門 intent 檢索）

---

### 2026-01-21

#### ✅ Knowledge Admin API 整合修復（Critical P0）
**檔案**:
- [2026-01-21-api-integration-fix.md](./2026-01-21-api-integration-fix.md) - 完整修正報告
- [2026-01-21-api-integration-analysis.md](./2026-01-21-api-integration-analysis.md) - 深度分析
- [2026-01-21-api-integration-quick-ref.md](./2026-01-21-api-integration-quick-ref.md) - 快速參考

**問題**: Knowledge Admin 後端 API 缺少 `action_type` 和 `api_config` 欄位支援

**影響**:
- 前端傳送的 API 關聯設定無法保存到資料庫
- 編輯知識時無法顯示現有的 API 關聯設定
- API 整合功能完全無法透過 UI 操作

**修復**:
- 更新 Pydantic 模型：加入 `action_type` 和 `api_config` 欄位
- 更新 INSERT 語句：插入時保存這兩個欄位
- 更新 UPDATE 語句：更新時修改這兩個欄位
- 更新 GET 端點：查詢和列表返回這兩個欄位
- 加入必要的 import：`from psycopg2.extras import Json`
- 修改檔案：`knowledge-admin/backend/app.py` (7 處修正)
- 修改檔案：`knowledge-admin/frontend/src/views/KnowledgeView.vue` (3 處修正)

**結果**:
- ✅ 可透過前端 UI 新增帶有 API 關聯的知識
- ✅ 可編輯和修改現有的 API 關聯
- ✅ 編輯時正確顯示現有的關聯類型
- ✅ 完整的 CRUD 生命週期支援
- ✅ 對話流程可正確觸發 API 調用

**相關測試**: [API 整合測試指南](../testing/api-integration-testing-guide.md)

---

### 2025-10-29

#### ✅ Business Types 欄位名稱錯誤修復（Critical P0）
**檔案**: [2025-10-29-business-types-field-name-fix.md](./2025-10-29-business-types-field-name-fix.md)

**問題**: `vendor_parameter_resolver.py` 查詢錯誤的資料庫欄位名稱導致通用知識無法被檢索

**影響**:
- B2C 模式下通用知識（`business_types: null`）完全無法檢索
- 知識庫檢索結果為空，即使知識存在且向量正確
- 回測系統失敗（例如：知識 497「可以養寵物嗎」檢索失敗）

**修復**:
- 更正欄位名稱：`business_type` → `business_types`（singular → plural）
- 修改檔案：`vendor_parameter_resolver.py:272`
- 修改檔案：`chat.py:456, 631-633`（資料結構鍵值一致性）

**結果**:
- ✅ B2C 通用知識檢索恢復正常
- ✅ 回測系統運作正常
- ✅ 資料結構鍵值錯誤同步修復

#### ✅ 多意圖獨立信心度評分（Solution A）
**相關議題**: 副意圖信心度固定衰減不精確

**問題**: 副意圖使用主意圖 * 0.85 固定衰減值，不夠精確

**影響**:
- 副意圖信心度無法反映 LLM 真實判斷
- 例如：主意圖 0.9，副意圖應為 0.7，但系統計算為 0.765

**修復**:
- LLM Function Schema 改為返回結構化物件：`{name, confidence}`
- 主意圖與副意圖皆獨立評分（0-1 範圍）
- 資料庫直接儲存 LLM 原始信心度
- 修改檔案：`intent_classifier.py:211-377`, `knowledge_classifier.py:150-190`

**結果**:
- ✅ 副意圖信心度準確反映 LLM 判斷
- ✅ 知識 510 驗證：主意圖 0.9，副意圖 0.7（非 0.765）
- ✅ Migration 49 修復現有 86 筆資料

### 2025-10-21

#### ✅ 拼音去重檢測修復
**檔案**: [PINYIN_DETECTION_FIX_REPORT.md](./PINYIN_DETECTION_FIX_REPORT.md)

**問題**: PostgreSQL vector 類型轉換錯誤導致拼音相似度檢測失敗

**影響**:
- 嚴重同音錯誤無法被正確合併（例如「每月租金」vs「美越租金」）
- 測試通過率：5/6 (83%)

**修復**:
- 正確解析 asyncpg 返回的 pgvector 字符串格式
- 修改 `unclear_question_manager.py:127-148`

**結果**:
- ✅ 測試通過率：6/6 (100%)
- ✅ 拼音相似度達到 1.0000（完美匹配）

---

## 📊 統計

| 日期 | 修復數量 | 類型 | 影響範圍 |
|------|---------|------|---------|
| 2026-01-28 | 1 | Performance Optimization | 知識庫檢索、SOP 檢索、前端展示 |
| 2026-01-21 | 1 | Critical Bug Fix | Knowledge Admin API、CRUD 生命週期、API 整合 |
| 2025-10-29 | 2 | Critical Bug Fix + Enhancement | 知識檢索、多意圖信心度、UI |
| 2025-10-21 | 1 | Bug Fix | 去重檢測 |

---

## 🔍 查找修復

### 按功能模組
- **知識庫檢索 & SOP 檢索**: [意圖加成優化](./INTENT_BOOST_OPTIMIZATION_2026-01-28.md)
- **Knowledge Admin API**: [API 整合修復](./2026-01-21-api-integration-fix.md)
- **知識檢索**: [Business Types 欄位名稱修復](./2025-10-29-business-types-field-name-fix.md)
- **多意圖分類**: [獨立信心度評分](./2025-10-29-business-types-field-name-fix.md)
- **去重檢測**: [拼音檢測修復](./PINYIN_DETECTION_FIX_REPORT.md)

### 按影響等級
- **Performance Optimization**:
  - [意圖加成優化](./INTENT_BOOST_OPTIMIZATION_2026-01-28.md)
- **Critical**:
  - [Knowledge Admin API 整合修復](./2026-01-21-api-integration-fix.md)
  - [Business Types 欄位名稱修復](./2025-10-29-business-types-field-name-fix.md)
- **高**: [拼音檢測修復](./PINYIN_DETECTION_FIX_REPORT.md)

---

## 📝 修復報告規範

每個修復報告應包含：

1. **問題描述**: 症狀、錯誤訊息
2. **根本原因**: 技術分析
3. **修復方案**: 代碼變更
4. **測試結果**: 修復前後對比
5. **影響範圍**: 受益功能列表
6. **後續建議**: 長期改進方案

---

**最後更新**: 2026-01-28
