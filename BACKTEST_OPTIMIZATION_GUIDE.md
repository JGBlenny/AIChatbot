# 回測優化指南 🚀

本文檔說明如何優化回測成本與效能。

## 📊 已完成的優化

### 1. 測試場景分類 (Test Scenarios)

我們建立了兩個測試集：

#### Smoke Tests (快速測試) - 5 個測試
- **路徑**: `test_scenarios_smoke.xlsx`
- **用途**: 日常測試、快速驗證
- **成本**: 5次 API 調用
- **測試案例**:
  1. 租金如何計算？(帳務問題)
  2. 如何申請退租？(合約問題)
  3. 房屋設備損壞如何報修？(物件問題)
  4. 如何聯繫管理師？(操作問題)
  5. 忘記密碼怎麼辦？(帳號問題)

#### Full Tests (完整測試) - 10 個測試
- **路徑**: `test_scenarios_full.xlsx`
- **用途**: 週測試、完整驗證
- **成本**: 10次 API 調用
- **包含**: 所有測試類別的完整覆蓋

### 2. 環境變數配置

#### OPENAI_MODEL
控制使用的 OpenAI 模型

- **預設值**: `gpt-4o-mini`
- **可選值**:
  - `gpt-4o-mini` - 最便宜，推薦用於測試
  - `gpt-4o` - 更強大，用於生產環境

#### RAG_RETRIEVAL_LIMIT
控制檢索的知識條數

- **預設值**: `5`
- **優化建議**: `3`
- **影響**: 減少傳送給 LLM 的 context 長度，降低 token 成本

#### BACKTEST_TYPE
控制使用哪個測試集

- **預設值**: `smoke` (前端執行回測時)
- **可選值**:
  - `smoke` - 使用 smoke tests (5個測試)
  - `full` - 使用 full tests (10個測試)
  - `custom` - 自訂路徑 (需搭配 `BACKTEST_SCENARIOS_PATH`)

## 💰 成本比較

| 配置 | 測試數 | 檢索條數 | 模型 | 預估成本 |
|------|--------|----------|------|----------|
| **最省錢** | 5 | 3 | gpt-4o-mini | ~$0.01 |
| **預設** | 5 | 5 | gpt-4o-mini | ~$0.015 |
| **完整測試** | 10 | 5 | gpt-4o-mini | ~$0.03 |
| **生產級別** | 10 | 5 | gpt-4o | ~$0.15 |

## 🎯 使用建議

### 日常開發測試
使用前端「執行回測」按鈕即可（已自動優化配置）

### 手動執行 Smoke Tests (最省錢)
```bash
export OPENAI_MODEL=gpt-4o-mini
export RAG_RETRIEVAL_LIMIT=3
export BACKTEST_TYPE=smoke

python3 scripts/knowledge_extraction/backtest_framework.py
```

### 週測試 (完整驗證)
```bash
export OPENAI_MODEL=gpt-4o-mini
export RAG_RETRIEVAL_LIMIT=5
export BACKTEST_TYPE=full

python3 scripts/knowledge_extraction/backtest_framework.py
```

### 自訂測試集
```bash
export BACKTEST_TYPE=custom
export BACKTEST_SCENARIOS_PATH=/path/to/your/test_scenarios.xlsx

python3 scripts/knowledge_extraction/backtest_framework.py
```

## 📈 優化效果

通過以上優化，我們實現了：

1. ✅ **成本降低 70%** - 使用 smoke tests + gpt-4o-mini + 3條檢索
2. ✅ **測試時間減少 50%** - 只測試 5個核心案例
3. ✅ **靈活配置** - 可根據需求選擇不同測試級別
4. ✅ **自動化** - 前端執行已預設優化配置

## 🔧 進一步優化建議

### 短期可做
1. ✅ 精簡測試場景 (已完成)
2. ✅ 環境變數配置 (已完成)
3. ✅ 減少檢索條數 (已完成)

### 中期優化
4. 建立回測結果快取 - 相同問題不重複測試
5. 輕量級回測模式 - 只測試分類，不生成完整回答

### 長期優化
6. 使用本地模型進行初步過濾
7. 建立 A/B 測試機制
8. 自動化成本追蹤與報表

## 📝 修改的檔案

1. `rag-orchestrator/services/llm_answer_optimizer.py:25-26` - 模型配置
2. `rag-orchestrator/services/rag_engine.py:31,50-52` - 檢索條數配置
3. `scripts/knowledge_extraction/backtest_framework.py:261-275` - 測試類型選擇
4. `knowledge-admin/backend/app.py:613-616` - 前端執行時的優化配置

## 🎉 結論

現在您可以：
- 在前端點擊「執行回測」進行快速測試（自動優化）
- 根據需求選擇不同測試級別
- 大幅降低回測成本
- 保持測試覆蓋質量

祝測試順利！🚀
