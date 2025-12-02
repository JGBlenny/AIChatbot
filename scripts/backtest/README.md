# 回測框架 V2 - 並發版本

## 概述

高性能異步並發回測框架，支持實時進度追蹤和資料庫整合。

## 核心文件

```
backtest_v2/
├── backtest_framework_async.py          # 核心並發回測框架
├── run_backtest_with_db_progress.py     # 主執行腳本（帶資料庫進度）
├── requirements.txt                      # Python 依賴
└── README.md                            # 本文件
```

## 主要特性

- ✅ **異步並發執行** - 使用 aiohttp + asyncio，5-10x 速度提升
- ✅ **實時進度追蹤** - 每 5 秒更新進度到資料庫
- ✅ **資料庫整合** - 自動保存測試結果到 PostgreSQL
- ✅ **智能重試機制** - 自動處理失敗請求
- ✅ **批量 LLM 評估** - 減少 API 調用次數
- ✅ **前端 UI 支持** - 通過管理後台執行

## 使用方式

### 1. 通過前端 UI（推薦）

訪問管理後台的「回測」頁面（開發環境範例：http://localhost:8087/backtest），點擊「執行回測」按鈕。

**注意**：生產環境請將 `localhost:8087` 替換為實際域名。

### 2. 手動執行（Docker 容器內）

```bash
# 在 rag-orchestrator 容器內執行
docker exec -it aichatbot-rag-orchestrator bash

# 設置環境變數
export BACKTEST_CONCURRENCY=5
export BACKTEST_QUALITY_MODE=detailed

# 執行回測
python3 /app/scripts/backtest/run_backtest_with_db_progress.py
```

## 配置參數

| 環境變數 | 說明 | 默認值 |
|---------|------|--------|
| `BACKTEST_CONCURRENCY` | 並發數 | 5 |
| `BACKTEST_QUALITY_MODE` | 品質評估模式 (detailed/hybrid) | detailed |
| `BACKTEST_SELECTION_STRATEGY` | 測試策略 (full/incremental/failed_only) | full |
| `RAG_API_URL` | RAG API 端點 | http://localhost:8100 |
| `VENDOR_ID` | 廠商 ID | 1 |

## 性能指標

| 配置 | 速度 | 適用場景 |
|------|------|---------|
| 並發數 5 | ~6-13 測試/分鐘 | 推薦配置 |
| 並發數 10 | ~12-20 測試/分鐘 | 高負載可能降速 |

## 資料庫結構

### backtest_runs 表
存儲每次回測的執行記錄，包含：
- 狀態追蹤（running/completed/cancelled）
- 統計摘要（通過率、平均分數等）
- 品質指標（相關性、完整性、準確性等）

### backtest_results 表
存儲每個測試的詳細結果，包含：
- 測試問題和系統答案
- 評估結果和品質指標
- 知識來源和優化建議

## 前端功能

- 📊 **實時進度顯示** - 進度條、已運行時間、預估剩餘時間
- 🛑 **中斷回測** - 可隨時中斷，保留已完成結果
- 📈 **統計圖表** - 通過率、品質指標等視覺化展示
- 📝 **詳細結果** - 每個測試的完整評估和優化建議
- 🔍 **結果篩選** - 按狀態、品質分數等條件過濾

## 故障排除

### 問題：回測速度很慢
- 檢查 RAG API 響應時間
- 降低並發數（過高的並發可能適得其反）
- 考慮使用 hybrid 模式（不做詳細 LLM 評估）

### 問題：前端看不到進度
- 檢查資料庫連接是否正常
- 確認回測進程正在運行
- 刷新頁面或點擊「重新載入」按鈕

### 問題：中斷後看不到結果
- 檢查 `backtest_results` 表是否有數據
- 在前端選擇對應的 Run ID
- 確認狀態為 `cancelled` 的記錄

## 依賴安裝

```bash
pip install -r requirements.txt
```

主要依賴：
- aiohttp - 異步 HTTP 客戶端
- aiodns - 異步 DNS 解析
- tenacity - 智能重試機制
- psycopg2-binary - PostgreSQL 連接
- pandas + openpyxl - Excel 報告生成

## 開發者

如需修改或擴展功能，請參考：
- `backtest_framework_async.py` - 核心框架邏輯
- `run_backtest_with_db_progress.py` - 執行流程和進度追蹤
- `/knowledge-admin/backend/app.py` - 後端 API 端點
- `/knowledge-admin/frontend/src/views/BacktestView.vue` - 前端 UI

---

**版本**: 2.0
**最後更新**: 2025-12-02
