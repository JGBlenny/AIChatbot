# 清理任務：過時的回測架構與文檔

> **建立時間**：2026-03-27T17:00:00Z
> **功能**：backtest-knowledge-refinement
> **目的**：在實作新架構前，清理過時的回測架構、資料表、腳本與文檔，避免混淆

---

## 清理範圍概述

根據調查，系統中存在以下需要清理或重構的內容：

### 🔴 需要清理的元件

1. **過時的資料表名稱**（需求文件提到但實際不存在）
2. **重複的回測框架檔案**（多個位置存在相同檔案）
3. **無法使用的 Shell 腳本**（依賴未實作功能）
4. **過時的文檔**（描述已變更的流程）

---

## 詳細清理任務

### 階段 0：清理前置作業（在任務 1 之前執行）

#### 0.1 資料表名稱對齊

**問題**：
- 需求文件 (requirements.md Section 3.1) 提到 `backtest_scenarios` 表
- 實際資料庫使用 `test_scenarios` 表
- 這會造成開發時的混淆

**清理動作**：
- ✅ **保留** `test_scenarios` 表（實際存在且正在使用）
- ✅ **更新** requirements.md，將所有 `backtest_scenarios` 改為 `test_scenarios`
- ✅ **檢查** 所有程式碼，確保沒有引用 `backtest_scenarios`

**驗收標準**：
- requirements.md 中無 `backtest_scenarios` 字樣
- 所有文檔與程式碼統一使用 `test_scenarios`

---

#### 0.2 清理重複的回測框架檔案

**問題**：
- `backtest_framework_async.py` 存在於三個位置：
  1. `/scripts/backtest/backtest_framework_async.py` (39KB, 最新)
  2. `/rag-orchestrator/backtest_framework_async.py` (過時副本)
- `run_backtest_with_db_progress.py` 也存在重複

**清理動作**：
- ✅ **保留** `/scripts/backtest/backtest_framework_async.py`（正式版本）
- ✅ **刪除** `/rag-orchestrator/backtest_framework_async.py`（過時副本）
- ✅ **保留** `/scripts/backtest/run_backtest_with_db_progress.py`
- ✅ **刪除** `/rag-orchestrator/run_backtest_db.py`（如果是重複）
- ✅ **更新** 所有 import 路徑指向 `/scripts/backtest/`

**驗收標準**：
- 只有 `/scripts/backtest/` 保留回測框架檔案
- 所有程式碼的 import 路徑正確
- 執行 `run_first_loop.py` 仍可正常運作

---

#### 0.3 處理無法使用的 Shell 腳本

**問題**（參考 implementation.md）：
- `run_next_iteration.sh` - 依賴未實作的跨 session 續接功能
- `quick_verification.sh` - 同上
- 這些腳本目前無法按原設計使用

**清理動作選項**：

**選項 A（推薦）：標記為待修復**
- ✅ **移動** 到 `/scripts/deprecated/` 目錄
- ✅ **添加** 警告註釋說明目前無法使用
- ✅ **創建** `scripts/deprecated/README.md` 說明原因
- ✅ **保留** 以便任務 4.1 完成後啟用

**選項 B：暫時刪除**
- ❌ **不建議**：這些腳本在 load_loop() 實作後仍有價值

**驗收標準**：
- 腳本移至 `/scripts/deprecated/` 並附帶說明
- 根目錄保留可用的腳本（`run_50_verification.sh` 等）
- README 清楚說明哪些腳本可用、哪些待修復

---

#### 0.4 清理與合併過時文檔

**問題**：
- `/docs/backtest/` 有 17 個文檔，部分內容重疊或過時
- 多個 `CHANGELOG.md`, `README.md`, `QUICK_START_V2.md` 等
- 部分文檔描述的流程已變更

**清理動作**：

**第一步：識別文檔狀態**
- ✅ **保留並更新**：
  - `KNOWLEDGE_COMPLETION_LOOP_GUIDE.md`（核心指南）
  - `QUICK_REFERENCE.md`（快速參考）
  - `IMPLEMENTATION_GAPS.md`（目前已知缺陷）

- ✅ **歸檔**（移至 `/docs/backtest/archive/`）：
  - `WORK_COMPLETED_2026-03-21.md`（歷史記錄）
  - `FILES_CHANGED_2026-03-18.md`（歷史記錄）
  - `FORM_SESSION_ISOLATION_FIX.md`（已完成的修復）
  - `SOP_GENERATOR_FIX_PLAN.md`（已完成的修復）
  - `GAP_CLASSIFIER_FINAL_SUMMARY.md`（歷史總結）
  - `GAP_CLASSIFIER_INTEGRATION.md`（已完成的整合）
  - `CLASSIFIER_INTEGRATION_STATUS.md`（歷史狀態）

- ✅ **合併並刪除**：
  - `README.md` + `QUICK_START_V2.md` → 合併為新的 `GETTING_STARTED.md`
  - `CHANGELOG.md` → 合併到 Git commit history
  - `ACTUAL_TESTING_STATUS.md` → 整合到 `IMPLEMENTATION_GAPS.md`

**第二步：創建新的文檔結構**
```
/docs/backtest/
├── GETTING_STARTED.md          (新建：快速開始指南)
├── KNOWLEDGE_COMPLETION_LOOP_GUIDE.md  (保留：核心指南)
├── QUICK_REFERENCE.md          (保留：快速參考)
├── IMPLEMENTATION_GAPS.md      (保留：已知缺陷)
├── API_REFERENCE.md            (新建：API 參考)
└── archive/                    (歷史文檔)
    ├── 2026-03-21/
    │   ├── WORK_COMPLETED.md
    │   ├── GAP_CLASSIFIER_*.md
    │   └── ...
    └── 2026-03-18/
        └── FILES_CHANGED.md
```

**驗收標準**：
- `/docs/backtest/` 只保留 5 個核心文檔
- 歷史文檔移至 `/archive/` 按日期整理
- 新的 `GETTING_STARTED.md` 包含最新的執行流程

---

#### 0.5 更新 requirements.md 與 design.md

**問題**：
- requirements.md 可能包含過時的資料表名稱
- design.md 可能引用不存在的檔案路徑

**清理動作**：
- ✅ **檢查** requirements.md 所有資料表名稱
- ✅ **檢查** design.md 所有檔案路徑
- ✅ **更新** 過時的參考
- ✅ **驗證** 所有 SQL 範例可執行

**驗收標準**：
- requirements.md 的資料表名稱與實際資料庫一致
- design.md 的檔案路徑全部正確
- 沒有引用已刪除的檔案

---

## 清理順序建議

**執行順序**（必須按順序）：

1. **0.5 更新文檔** ← 先確保文檔正確
2. **0.1 資料表名稱對齊** ← 避免後續混淆
3. **0.2 清理重複檔案** ← 確保程式碼整潔
4. **0.3 處理無法使用的腳本** ← 標記或移除
5. **0.4 清理文檔** ← 最後整理文檔

---

## 清理檢查清單

清理完成後，請驗證：

- [ ] 執行 `run_first_loop.py` 仍可正常運作
- [ ] 所有 import 路徑正確無誤
- [ ] 資料庫表名稱統一使用 `test_scenarios`
- [ ] 重複檔案已刪除
- [ ] 無法使用的腳本已標記或移至 deprecated
- [ ] 文檔結構清晰，無過時內容
- [ ] requirements.md 與實際系統一致

---

## 風險評估

| 風險 | 機率 | 影響 | 緩解措施 |
|------|------|------|---------|
| 刪除檔案導致系統無法運作 | 低 | 高 | 先備份，逐步清理並測試 |
| 修改文檔導致資訊遺失 | 低 | 中 | 移至 archive/ 而非直接刪除 |
| import 路徑錯誤 | 中 | 高 | 使用 grep 全局搜尋，確保更新完整 |

---

## 預估工時

- 0.1 資料表名稱對齊：30 分鐘
- 0.2 清理重複檔案：1 小時
- 0.3 處理腳本：30 分鐘
- 0.4 清理文檔：1.5 小時
- 0.5 更新 requirements/design：1 小時

**總計**：約 4-5 小時

---

*此清理任務應在任務 1.2 之前完成，確保後續實作基於清晰的架構。*
