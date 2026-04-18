# 研究記錄：sop-coverage-completion

> 分析時間：2026-04-17
> 類型：Light Discovery（Extension）

---

## Discovery 範圍

盤查現有 SOP 生成與管理 pipeline 的擴展點，確認批量 SOP 生成的可行性。

## 關鍵發現

### 1. 現有 SOP 生成能力

- `SOPGenerator.generate_sop_items()` 已支援批量生成（`batch_size=5`，可調整）
- 輸入為 `gaps: List[Dict]`，每個 gap 需包含 `test_question`、`gap_type`、`failure_reason`、`priority`
- 內建品質驗證（2-pass AI QA）、重複偵測（pgvector 0.75 threshold）、分類/群組自動選擇（LLM）
- 生成結果寫入 `loop_generated_knowledge`（status=pending），經審核後同步到 `vendor_sop_items`

### 2. 需解決的 gap

- **無流程清單**：目前生成邏輯依賴「從回測失敗案例反向發現缺口」，沒有主動盤點機制
- **無批量停用**：沒有現成的 SOP 批量停用功能
- **SOPGenerator 輸入格式**：需要 `gaps` 格式的輸入，但我們要從流程清單生成，需要轉換層
- **LLM 答案判定**：`evaluate_answer_v2()` 沒有 LLM 評審步驟

### 3. 設計決策

| 決策 | 選擇 | 理由 |
|------|------|------|
| 流程清單格式 | JSON 靜態檔案 | 可版控、可人工編輯、無需 DB |
| 批量生成策略 | 複用 SOPGenerator + 轉換層 | 保留現有品質驗證與重複偵測 |
| 停用機制 | 直接 SQL UPDATE | 簡單操作，不需新 API |
| LLM 判定位置 | 新增獨立函數，回測後執行 | 不影響現有 confidence 公式 |
| 分類建立 | 先批量建分類，再生成 SOP | 避免每筆 SOP 獨立呼叫 LLM 選分類 |

### 4. Synthesis 結論

- **Generalization**：Req 1-4（清單→清除→生成→分類）是同一 pipeline 的四個 phase，設計為 orchestrator
- **Build vs Adopt**：SOPGenerator、審核流程、回測框架全部複用；新建 orchestrator + 清單 + LLM evaluator
- **Simplification**：不需獨立 API/服務，用 Python script 執行即可（與 `run_first_loop.py` 同層級）
