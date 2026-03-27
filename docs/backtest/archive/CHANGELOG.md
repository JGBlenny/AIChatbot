# 回測系統更新日誌

---

## [2026-03-18] - 表單 Session 隔離修復

### 🔴 修復 (Critical)
- **表單 Session 隔離問題** ([#BACKTEST-001](./FORM_SESSION_ISOLATION_FIX.md))
  - 修復連續 30+ 題被困在同一表單狀態的問題
  - 為每個測試案例生成獨立的 `session_id`
  - 格式: `backtest_session_{scenario_id}`
  - 完全消除 session 污染

### ✨ 新增
- **前端表單標記**
  - 列表中顯示 `📝 表單` 小標籤
  - 詳情頁顯示 `📝 表單類型` 大標籤
  - 紫色漸層視覺標識

- **表單類型檢測邏輯**
  - 檢查 `action_type in ['form_fill', 'form_then_api']`
  - 自動標記 `is_form: True`
  - 特殊優化建議提示

### 🔧 修改
- **backtest_framework_async.py**
  - `_query_rag_async()`: 添加 `scenario_id` 參數
  - 生成獨立 session_id 和 user_id
  - 優化表單檢測邏輯

- **run_backtest_db.py**
  - Scenarios 字典添加 `'id'` 欄位
  - 保留 `'scenario_id'` 向後兼容

- **BacktestView.vue**
  - 添加表單標記組件
  - 新增 `.form-badge` 和 `.form-badge-large` CSS 樣式

### 📊 驗證
- Run 77: 10 題測試，0 題污染 ✅
- 通過率: 20% (2/10)
- 平均耗時: 2.97 秒/題

---

## [2026-03-16] - Similarity Extraction 修復

### 🐛 修復
- **Similarity 提取問題**
  - 修復 `max_similarity` 始終為 0.0 的問題
  - 從 `debug_info.knowledge_candidates` 提取 similarity
  - 注入到 `sources` 供評估使用

### 🔧 修改
- **backtest_framework_async.py**
  - 請求 `include_debug_info: True`
  - 添加 similarity 提取與注入邏輯 (Lines 157-173)
  - 優先使用 `boosted_similarity`，次選 `base_similarity`

### 📊 驗證
- Run 66: 100 題測試
- 修復前: 全部失敗 (max_similarity=0.0)
- 修復後: similarity 正常提取 ✅

---

## [2026-03-14] - V2 評估邏輯實作

### ✨ 新增
- **V2 評估系統**
  - `calculate_confidence_score()`: 對齊生產環境計算邏輯
  - `evaluate_answer_v2()`: 簡化評估流程
  - 移除 LLM 評估依賴

### 🔧 修改
- **Confidence Score 公式**
  ```
  confidence_score = max_similarity × 0.7
                   + min(result_count/5, 1.0) × 0.2
                   + keyword_match_rate × 0.1
  ```

- **通過條件**
  - ✅ >= 0.85: 高信心度
  - ✅ >= 0.70: 中等信心度
  - ✅ >= 0.60: 較低信心度
  - ❌ < 0.60: 失敗

### 🗑️ 移除
- 移除 LLM 評估相關方法（共約 283 行）
- 移除 `semantic_overlap` 檢查
- 簡化評估流程

---

## [2026-03-12] - 連續分批測試功能

### ✨ 新增
- **智能分批回測**
  - API: `POST /api/backtest/run/smart-batch`
  - 支援批次大小: 50/100/200/500
  - 自動分批執行

- **連續批次執行**
  - API: `POST /api/backtest/run/continuous-batch`
  - 背景執行，不會 timeout
  - 前端輪詢進度

### 📊 資料庫
- 新增 `backtest_runs` 表
- 新增 `backtest_results` 表
- 實時進度追蹤

---

## 版本歷史

| 日期 | 版本 | 主要更新 |
|------|------|----------|
| 2026-03-18 | v2.3 | 表單 Session 隔離修復 |
| 2026-03-16 | v2.2 | Similarity Extraction 修復 |
| 2026-03-14 | v2.1 | V2 評估邏輯實作 |
| 2026-03-12 | v2.0 | 連續分批測試功能 |

---

**維護者**: Claude
**最後更新**: 2026-03-18
