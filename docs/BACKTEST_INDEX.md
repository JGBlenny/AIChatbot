# 回測框架文檔索引

## 📚 文檔總覽

本索引整理了回測框架的所有相關文檔，幫助您快速找到所需資訊。

## 🚀 快速開始

**新手推薦路徑：**

1. **[快速開始指南](./BACKTEST_QUICKSTART.md)** ⭐
   - 5 分鐘上手
   - 三種策略使用
   - 常見場景範例
   - 故障排除

**適合：** 第一次使用回測框架的開發者

## 📖 核心文檔

### 策略與配置

| 文檔 | 說明 | 適合對象 |
|-----|------|---------|
| **[回測策略指南](./backtest_strategies.md)** | 詳細說明三種智能測試策略 | 所有用戶 |
| **[環境變數參考](./backtest_env_vars.md)** | 完整環境變數列表與範例 | 配置管理員 |
| **[Phase 2 更新日誌](./BACKTEST_PHASE2_CHANGELOG.md)** | 最新功能與技術細節 | 開發者 |

### 架構與設計

| 文檔 | 說明 | 適合對象 |
|-----|------|---------|
| **[架構評估報告](./BACKTEST_ARCHITECTURE_EVALUATION.md)** | 系統架構分析與改進建議 | 架構師、Tech Lead |

## 📋 功能分類

### Phase 1: 資料庫整合

**狀態：** ✅ 已完成

**功能：**
- 測試結果資料庫儲存
- 回測歷史 API
- 前端歷史查詢界面

**相關文檔：**
- Phase 1.1 更新日誌（待建立）
- Phase 1.2 更新日誌（待建立）

### Phase 2: 智能測試策略

**狀態：** ✅ 已完成

**功能：**
- Incremental（增量測試）
- Full（完整測試）
- Failed Only（僅失敗測試）
- 優先級評分系統
- 統計資訊展示

**相關文檔：**
- [回測策略指南](./backtest_strategies.md)
- [環境變數參考](./backtest_env_vars.md)
- [Phase 2 更新日誌](./BACKTEST_PHASE2_CHANGELOG.md)
- [快速開始指南](./BACKTEST_QUICKSTART.md)

### Phase 3: 趨勢分析與視覺化 ⭐ 最新

**狀態：** ✅ 已完成

**功能：**
- 趨勢分析 API（4個端點）
- 前端圖表視覺化（Chart.js）
- 自動警報系統
- 期間對比分析

**相關文檔：**
- [Phase 3 更新日誌](./BACKTEST_PHASE3_CHANGELOG.md)

## 🎯 按角色分類

### 開發者

**推薦閱讀順序：**
1. [快速開始指南](./BACKTEST_QUICKSTART.md)
2. [回測策略指南](./backtest_strategies.md)
3. [環境變數參考](./backtest_env_vars.md)

**關注重點：**
- 如何執行回測
- 如何解讀結果
- 如何優化失敗案例

### DevOps / SRE

**推薦閱讀順序：**
1. [環境變數參考](./backtest_env_vars.md)
2. [回測策略指南](./backtest_strategies.md) - CI/CD 整合章節
3. [Phase 2 更新日誌](./BACKTEST_PHASE2_CHANGELOG.md) - 效能提升章節

**關注重點：**
- CI/CD 整合
- 環境變數配置
- Docker / K8s 部署
- 監控與警報

### 產品經理 / QA

**推薦閱讀順序：**
1. [快速開始指南](./BACKTEST_QUICKSTART.md)
2. [回測策略指南](./backtest_strategies.md)
3. [Phase 2 更新日誌](./BACKTEST_PHASE2_CHANGELOG.md) - 使用範例章節

**關注重點：**
- 測試策略選擇
- 結果解讀
- 品質指標
- 優化建議

### 架構師 / Tech Lead

**推薦閱讀順序：**
1. [架構評估報告](./BACKTEST_ARCHITECTURE_EVALUATION.md)
2. [Phase 2 更新日誌](./BACKTEST_PHASE2_CHANGELOG.md) - 技術改進章節
3. [回測策略指南](./backtest_strategies.md) - 進階用法章節

**關注重點：**
- 系統架構
- 技術債務
- 擴展性
- 未來規劃

## 🔍 按主題查找

### 安裝與配置

- [快速開始 - 基本執行](./BACKTEST_QUICKSTART.md#1-基本執行預設配置)
- [環境變數 - 完整列表](./backtest_env_vars.md#完整變數列表)
- [環境變數 - 常用組合](./backtest_env_vars.md#常用組合)

### 策略使用

- [策略指南 - Incremental](./backtest_strategies.md#1-incremental增量測試)
- [策略指南 - Full](./backtest_strategies.md#2-full完整測試)
- [策略指南 - Failed Only](./backtest_strategies.md#3-failed-only僅失敗測試)
- [快速開始 - 三種策略](./BACKTEST_QUICKSTART.md#2-三種策略選擇)

### CI/CD 整合

- [策略指南 - CI/CD 整合](./backtest_strategies.md#cicd-整合)
- [環境變數 - CI/CD 自動化](./backtest_env_vars.md#2-cicd-自動化)
- [環境變數 - Docker 環境](./backtest_env_vars.md#docker-環境)

### 故障排除

- [快速開始 - 故障排除](./BACKTEST_QUICKSTART.md#故障排除)
- [策略指南 - 故障排除](./backtest_strategies.md#故障排除)
- [環境變數 - 驗證配置](./backtest_env_vars.md#驗證配置)

### 優化與最佳實踐

- [策略指南 - 最佳實踐](./backtest_strategies.md#最佳實踐)
- [策略指南 - 使用建議](./backtest_strategies.md#使用建議)
- [快速開始 - 常見場景](./BACKTEST_QUICKSTART.md#常見場景)

### 技術細節

- [Phase 2 更新日誌 - 技術改進](./BACKTEST_PHASE2_CHANGELOG.md#技術改進)
- [Phase 2 更新日誌 - 架構變更](./BACKTEST_PHASE2_CHANGELOG.md#架構變更)
- [架構評估 - 系統架構](./BACKTEST_ARCHITECTURE_EVALUATION.md)

## 📊 文檔統計

| 類別 | 文檔數 | 總字數（約） |
|-----|--------|------------|
| 快速指南 | 1 | 3,000 |
| 策略說明 | 1 | 5,000 |
| 配置參考 | 1 | 6,000 |
| 更新日誌 | 2 | 12,000 |
| 架構設計 | 1 | 6,000 |
| **總計** | **6** | **32,000** |

## 🔄 更新記錄

| 日期 | 文檔 | 變更 |
|------|------|------|
| 2025-10-12 | BACKTEST_PHASE3_CHANGELOG.md | 新增 Phase 3 更新日誌（趨勢分析） |
| 2025-10-12 | BACKTEST_INDEX.md | 更新索引，Phase 3 標記為已完成 |
| 2025-10-12 | BACKTEST_QUICKSTART.md | 新增快速開始指南 |
| 2025-10-12 | BACKTEST_PHASE2_CHANGELOG.md | 新增 Phase 2 更新日誌 |
| 2025-10-12 | backtest_env_vars.md | 新增環境變數參考 |
| 2025-10-12 | backtest_strategies.md | 新增策略指南 |

## 🚧 待建立文檔

- [ ] Phase 1.1 更新日誌
- [ ] Phase 1.2 更新日誌
- [ ] 資料庫 Schema 說明
- [ ] API 端點文檔
- [ ] 前端使用指南（含趨勢分析）
- [ ] 貢獻指南
- [ ] FAQ 常見問題

## 💡 使用建議

### 第一次使用

```
1. 閱讀「快速開始指南」（5 分鐘）
   ↓
2. 執行第一個回測（incremental 策略）
   ↓
3. 查看「回測策略指南」了解更多細節
```

### 配置 CI/CD

```
1. 閱讀「環境變數參考」的 CI/CD 章節
   ↓
2. 參考「回測策略指南」的 CI/CD 整合範例
   ↓
3. 根據專案需求調整配置
```

### 優化測試效能

```
1. 查看「Phase 2 更新日誌」的效能提升章節
   ↓
2. 閱讀「回測策略指南」的最佳實踐
   ↓
3. 根據場景選擇合適策略
```

### 深入理解架構

```
1. 閱讀「架構評估報告」
   ↓
2. 查看「Phase 2 更新日誌」的架構變更
   ↓
3. 參考程式碼實作（backtest_framework.py）
```

## 🔗 相關資源

### 內部資源

- 主 README：`/README.md`
- 回測框架：`/scripts/knowledge_extraction/backtest_framework.py`
- 資料庫遷移：`/knowledge-admin/backend/migrations/`
- 前端界面：`/knowledge-admin/frontend/src/views/BacktestView.vue`

### 外部資源

- PostgreSQL 文檔：https://www.postgresql.org/docs/
- psycopg2 文檔：https://www.psycopg.org/docs/
- GitHub Actions：https://docs.github.com/en/actions

## 📞 支援與回饋

### 問題回報

1. **查閱文檔**
   - 先查看「故障排除」章節
   - 確認環境變數配置正確

2. **提交 Issue**
   - 提供完整錯誤訊息
   - 說明復現步驟
   - 附上環境資訊

3. **尋求協助**
   - 聯繫團隊成員
   - 在內部聊天群組提問

### 文檔改進

如果您發現：
- 文檔錯誤或過時
- 說明不清楚
- 缺少重要資訊

歡迎：
- 提交 Pull Request
- 提出改進建議
- 貢獻使用範例

## 📜 版本歷史

- **v3.0** (2025-10-12) - Phase 3 完成，趨勢分析與視覺化
- **v2.0** (2025-10-12) - Phase 2 完成，新增智能測試策略
- **v1.2** (2025-10-10) - Phase 1.2 完成，前端歷史查詢
- **v1.1** (2025-10-08) - Phase 1.1 完成，資料庫儲存
- **v1.0** (2025-10-01) - 初始版本，基礎回測功能

---

**最後更新：** 2025-10-12
**維護者：** Claude Code & Lenny
**當前版本：** Phase 3.0
