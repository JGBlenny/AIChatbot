# 路徑修復總結報告 📝

## 問題背景

您正確地指出了代碼中使用硬編碼絕對路徑的問題：
> "像是這種 /Users/lenny/jgb/AIChatbot/ 不能這樣用吧 我要不屬實這都會出問題"

這些硬編碼的絕對路徑會導致以下問題：
- 代碼無法在其他機器上運行
- 無法在不同的用戶環境下使用
- 不適合團隊協作和部署

## 解決方案

所有硬編碼的絕對路徑都已修改為使用相對路徑解析：

```python
# 從環境變數讀取專案根目錄，或使用相對路徑計算
project_root = os.getenv("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# 使用 os.path.join 拼接路徑
file_path = os.path.join(project_root, "relative/path/to/file")
```

## 修改的文件清單

### 1. knowledge-admin/backend/app.py
**修改位置**：
- Line 588-589: 測試場景文件路徑檢查
- Line 613-620: 回測執行環境變數設置
- Line 632: 回測日誌路徑
- Line 494: 回測結果文件路徑
- Line 565: 回測摘要文件路徑
- Line 674-675: 下載文件路徑

**修改內容**：
```python
# 計算專案根目錄
project_root = os.getenv("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# 使用相對路徑
test_scenarios_path = os.path.join(project_root, "test_scenarios_smoke.xlsx")
backtest_path = os.path.join(project_root, "output/backtest/backtest_results.xlsx")
summary_path = os.path.join(project_root, "output/backtest/backtest_results_summary.txt")
log_path = os.path.join(project_root, "output/backtest/backtest_log.txt")
```

### 2. scripts/knowledge_extraction/backtest_framework.py
**修改位置**：
- Line 266-278: 測試場景文件路徑選擇

**修改內容**：
```python
# 取得專案根目錄
project_root = os.getenv("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# 根據測試類型選擇不同的測試文件
test_type = os.getenv("BACKTEST_TYPE", "smoke")
if test_type == "smoke":
    test_scenarios_path = os.path.join(project_root, "test_scenarios_smoke.xlsx")
elif test_type == "full":
    test_scenarios_path = os.path.join(project_root, "test_scenarios_full.xlsx")
else:
    test_scenarios_path = os.getenv("BACKTEST_SCENARIOS_PATH", os.path.join(project_root, "test_scenarios.xlsx"))

output_path = os.path.join(project_root, "output/backtest/backtest_results.xlsx")
```

### 3. scripts/knowledge_extraction/create_test_scenarios.py
**修改位置**：
- Line 150-151: 輸出文件路徑

**修改內容**：
```python
# 保存到 Excel
project_root = os.getenv("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
output_path = os.path.join(project_root, 'test_scenarios.xlsx')
df.to_excel(output_path, index=False, engine='openpyxl')
```

## 環境變數支持

現在代碼支持通過環境變數 `PROJECT_ROOT` 指定專案根目錄：

```bash
# 方式 1: 使用環境變數
export PROJECT_ROOT=/path/to/your/project
python3 scripts/knowledge_extraction/backtest_framework.py

# 方式 2: 自動計算（預設）
# 代碼會自動從當前文件位置向上查找專案根目錄
python3 scripts/knowledge_extraction/backtest_framework.py
```

## 其他相關修改

### 1. 添加依賴套件
已將 `pandas` 和 `openpyxl` 添加到 `knowledge-admin/backend/requirements.txt`：
```
pandas==2.3.3
openpyxl==3.1.5
```

### 2. 後端服務已啟動
後端服務已成功啟動並運行在 `http://0.0.0.0:8000`

## 測試建議

### 1. 測試相對路徑解析
```bash
cd /Users/lenny/jgb/AIChatbot/knowledge-admin/backend
python3 -c "import os; print(os.path.abspath(os.path.join(os.path.dirname('app.py'), '../..')))"
```

### 2. 測試回測功能
在前端界面點擊「執行回測」按鈕，驗證：
- ✅ 文件路徑正確解析
- ✅ 回測成功執行
- ✅ 結果文件正確生成

### 3. 測試環境變數
```bash
export PROJECT_ROOT=/Users/lenny/jgb/AIChatbot
export BACKTEST_TYPE=smoke
python3 scripts/knowledge_extraction/backtest_framework.py
```

## 優點總結

✅ **可移植性**: 代碼可在任何機器上運行
✅ **環境獨立**: 不依賴特定用戶路徑
✅ **團隊協作**: 適合多人開發
✅ **部署友好**: 可用於 Docker 等容器環境
✅ **靈活配置**: 支持環境變數自定義

## 下一步

1. ✅ 後端服務已啟動
2. 建議測試前端「執行回測」功能
3. 確認所有路徑解析正確
4. 如有問題，可通過環境變數 `PROJECT_ROOT` 手動指定專案根目錄

---

**修復完成時間**: 2025-10-10
**修改文件數**: 3 個核心文件
**修改位置數**: 12 處
