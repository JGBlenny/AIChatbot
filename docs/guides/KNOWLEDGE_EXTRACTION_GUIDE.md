# LINE 聊天記錄知識提取與回測完整指南

## 📋 概述

本指南說明如何從 LINE 聊天記錄中提取知識庫、累積測試情境並進行回測驗證。

### 已建立的資源

1. ✅ 知識提取腳本
2. ✅ 回測框架
3. ✅ 知識庫匯入頁面（含智能去重）
4. ✅ 現有客服 QA 資料

---

## 🎯 工作流程

```
LINE 聊天記錄 (.txt)
    ↓
【步驟 1】提取知識庫 + 測試情境
    ↓
知識庫 Excel  +  測試情境 Excel
    ↓
【步驟 2】導入知識庫到資料庫
    ↓
【步驟 3】執行回測
    ↓
回測報告（通過率、準確度等）
```

---

## 📂 文件位置

### 輸入文件（已存在）

```
/Users/lenny/jgb/AIChatbot/data/
├── [LINE] 一方生活x JGB的聊天.txt                    # 356 KB
├── [LINE] 富喬 X JGB排除疑難雜症區的聊天.txt          # 218 KB
├── [LINE] 興中資產管理&易聚的聊天.txt                 # 202 KB
├── 5.3.4_客服_ QA, FB, 來電.xlsx                     # 72 KB（已整理）
└── 客服QA整理_測試結果.xlsx                          # 7.1 KB
```

### 處理腳本

```
/Users/lenny/jgb/AIChatbot/scripts/knowledge_extraction/
├── extract_knowledge_and_tests.py        # 知識提取腳本
└── backtest_framework.py                 # 回測框架
```

### 輸出目錄

```
/Users/lenny/jgb/AIChatbot/output/
├── knowledge_base_extracted.xlsx         # 提取的知識庫
├── test_scenarios.xlsx                   # 測試情境
└── backtest/
    ├── backtest_results.xlsx             # 回測詳細結果
    └── backtest_results_summary.txt      # 回測摘要報告
```

### 前端頁面

```
/Users/lenny/jgb/AIChatbot/knowledge-admin/frontend/src/views/
└── KnowledgeImportView.vue               # 知識庫匯入頁面
```

---

## 🚀 使用方法

### 方法一：使用前端頁面（推薦）

**優點：**
- ✅ 視覺化操作界面
- ✅ 智能去重，避免浪費 token
- ✅ 預覽功能（不消耗 token）
- ✅ 實時進度顯示
- ✅ 匯入歷史記錄

**步驟：**

1. **啟動服務**
   ```bash
   cd /Users/lenny/jgb/AIChatbot
   docker-compose up -d
   ```

2. **訪問知識庫匯入頁面**
   ```
   http://localhost:8200/knowledge-import
   ```

   或者點擊頂部導航欄的「知識匯入」連結

3. **上傳文件**
   - 點擊或拖曳 txt 文件
   - 選擇匯入模式：
     - **新增知識**：提取新問答對並添加
     - **優化現有**：分析並優化現有知識（較少 token）
   - 啟用智能去重（推薦）

4. **預覽確認（不消耗 token）**
   - 查看文件統計
   - 預覽前 20 行內容
   - 估算問答對數量

5. **確認匯入**
   - 點擊「確認匯入」開始處理
   - 觀察實時進度
   - 查看去重統計

6. **查看結果**
   - 提取的問答對數量
   - 去重跳過的數量
   - 處理時間

---

### 方法二：使用 Python 腳本（批量處理）

**優點：**
- ✅ 適合批量處理多個文件
- ✅ 可自動化和排程
- ✅ 同時產生測試情境

#### 步驟 1：提取知識庫和測試情境

```bash
cd /Users/lenny/jgb/AIChatbot

# 設定 OpenAI API Key
export OPENAI_API_KEY="sk-..."

# 執行提取腳本
python scripts/knowledge_extraction/extract_knowledge_and_tests.py
```

**輸出：**
```
/Users/lenny/jgb/AIChatbot/output/
├── knowledge_base_extracted.xlsx    # 提取的知識庫
└── test_scenarios.xlsx              # 測試情境
```

**預期處理時間：**
- 每個文件約 5-10 分鐘（取決於內容量）
- 三個文件總共約 15-30 分鐘

#### 步驟 2：導入知識庫到資料庫

**選項 A：使用前端管理後台**

1. 訪問知識庫管理頁面：`http://localhost:8200/knowledge`
2. 點擊「批次匯入」
3. 上傳 `knowledge_base_extracted.xlsx`
4. 確認導入

**選項 B：使用 API**

```bash
# TODO: 創建批次導入腳本
python scripts/import_knowledge_batch.py \
  --file output/knowledge_base_extracted.xlsx \
  --vendor_id 1
```

#### 步驟 3：執行回測

```bash
# 執行回測框架
python scripts/knowledge_extraction/backtest_framework.py
```

**互動選項：**
```
是否要執行完整回測？
總共 N 個測試情境
輸入要測試的數量（直接按 Enter 測試全部）: [輸入數字或按 Enter]
```

**輸出：**
```
/Users/lenny/jgb/AIChatbot/output/backtest/
├── backtest_results.xlsx            # 詳細結果
└── backtest_results_summary.txt     # 摘要報告
```

**報告內容：**
- 整體通過率
- 平均分數和信心度
- 按難度分組統計
- 失敗案例列表

---

## 💡 智能去重機制

### 為什麼需要去重？

重複匯入相同內容會：
- ❌ 浪費 OpenAI API token（成本增加）
- ❌ 產生重複知識（降低查詢品質）
- ❌ 增加資料庫負擔

### 去重策略

| 策略 | 說明 | 效果 |
|------|------|------|
| **內容雜湊** | 計算文件內容 MD5，避免完全相同的文件重複處理 | 🔥 高 |
| **問題摘要比對** | 檢查知識庫中是否已存在相同問題 | 🔥 高 |
| **語義相似度** | 使用向量相似度檢測近似重複（待實作） | 🟡 中 |
| **批次模式** | 一次處理多條訊息，減少 API 呼叫 | 🟡 中 |

### 使用建議

1. **首次匯入**：關閉去重，完整提取
2. **增量匯入**：啟用去重，只處理新內容
3. **定期優化**：使用「優化模式」重新整理知識

---

## 📊 評估指標

### 回測指標

| 指標 | 說明 | 目標 |
|------|------|------|
| **通過率** | 測試通過的百分比 | ≥ 80% |
| **平均分數** | 答案品質評分（0-1） | ≥ 0.7 |
| **平均信心度** | 意圖分類信心度 | ≥ 0.75 |
| **分類準確度** | 意圖分類正確率 | ≥ 85% |
| **關鍵字覆蓋率** | 答案包含預期關鍵字的比例 | ≥ 70% |

### 評分規則

```python
分數計算：
- 分類匹配：+0.3
- 關鍵字覆蓋：+0.4（比例）
- 信心度 ≥ 0.7：+0.3

總分 ≥ 0.6 → 通過 ✅
總分 < 0.6 → 失敗 ❌
```

---

## 🔧 故障排除

### 問題 1：提取腳本無法運行

**錯誤訊息：** `ModuleNotFoundError: No module named 'openai'`

**解決方案：**
```bash
pip install openai pandas openpyxl
```

### 問題 2：API 請求失敗

**錯誤訊息：** `OpenAI API Error: Rate limit exceeded`

**解決方案：**
1. 減少 `batch_size`（預設 50 → 改為 20）
2. 增加延遲時間（`time.sleep(1)` → `time.sleep(2)`）
3. 使用付費 OpenAI 帳號提高速率限制

### 問題 3：回測連不到 RAG 系統

**錯誤訊息：** `Connection refused`

**解決方案：**
```bash
# 檢查服務是否運行
docker-compose ps

# 重啟服務
docker-compose restart rag-orchestrator

# 檢查日誌
docker-compose logs rag-orchestrator
```

### 問題 4：前端頁面顯示 404

**解決方案：**
```bash
# 重新建置前端
cd knowledge-admin/frontend
npm run build

# 重啟容器
docker-compose restart knowledge-admin
```

---

## 📈 效能優化建議

### 1. 批次大小調整

```python
# 小文件（< 100 行）
batch_size = 30

# 中等文件（100-500 行）
batch_size = 50  # 預設

# 大文件（> 500 行）
batch_size = 100
```

### 2. 並行處理（進階）

```python
# TODO: 實作多線程處理
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(extract_from_file, file)
        for file in file_list
    ]
```

### 3. 快取策略

```python
# 快取已處理的對話片段（避免重複呼叫 LLM）
cache_dir = "/tmp/knowledge_cache"
```

---

## 📝 範例結果

### 提取知識庫範例

| title | category | question_summary | answer | audience | keywords |
|-------|----------|-----------------|--------|----------|----------|
| 租金繳費日期 | 帳務問題 | 每月繳費日期是什麼時候？ | 租金繳費日為每月 5 號... | 租客 | ["繳費", "日期"] |
| 逾期處理 | 帳務問題 | 逾期繳費會怎樣？ | 如果逾期超過 3 天... | 租客 | ["逾期", "罰款"] |

### 測試情境範例

| test_question | expected_category | expected_keywords | difficulty |
|---------------|-------------------|-------------------|------------|
| 請問租金什麼時候要繳？ | 帳務問題 | ["繳費", "日期"] | easy |
| 如果我這個月繳不出來會怎樣？ | 帳務問題 | ["逾期", "罰款", "後果"] | medium |

### 回測報告範例

```
==============================================================
知識庫回測報告
==============================================================

測試時間：2025-10-10 15:30:00
RAG 系統：http://localhost:8100
業者 ID：1

==============================================================
整體統計
==============================================================
總測試數：50
通過數：42
失敗數：8
通過率：84.00%
平均分數：0.76
平均信心度：0.82

==============================================================
按難度統計
==============================================================
EASY      : 18/20 (90.0%)
MEDIUM    : 20/24 (83.3%)
HARD      : 4/6 (66.7%)

==============================================================
失敗案例
==============================================================

問題：合約期限內可以提前解約嗎？
預期分類：合約問題
實際意圖：服務問題
分數：0.45
------------------------------------------------------------
```

---

## 🎯 下一步

完成知識提取與回測後：

1. **分析失敗案例**
   - 檢查意圖分類錯誤
   - 補充缺失的知識
   - 調整關鍵字設定

2. **優化知識庫**
   - 合併相似問答
   - 補充詳細答案
   - 更新過時資訊

3. **持續回測**
   - 定期執行回測（每週）
   - 追蹤通過率變化
   - 累積更多測試情境

4. **實際部署**
   - 整合到生產環境
   - 監控查詢品質
   - 收集使用者反饋

---

## 📚 相關文檔

- [Phase 1 實作文件](./PHASE1_MULTI_VENDOR_IMPLEMENTATION.md)
- [Phase 2 規劃文件](./PHASE2_PLANNING.md)
- [系統架構文檔](./architecture/SYSTEM_ARCHITECTURE.md)
- [API 參考文檔](./API_REFERENCE_PHASE1.md)

---

## 🤝 支援

如有問題或需要協助：

1. 檢查本指南的「故障排除」章節
2. 查看系統日誌：`docker-compose logs`
3. 參考相關文檔

---

**維護者：** Claude Code
**最後更新：** 2025-10-10
**版本：** 1.0
