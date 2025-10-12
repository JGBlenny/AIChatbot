# 回測框架快速開始指南

## 5 分鐘上手

### 1. 基本執行（預設配置）

```bash
cd /Users/lenny/jgb/AIChatbot

# 最簡單的執行方式（使用預設配置）
BACKTEST_SELECTION_STRATEGY=incremental \
BACKTEST_QUALITY_MODE=basic \
BACKTEST_NON_INTERACTIVE=true \
BACKTEST_USE_DATABASE=true \
PROJECT_ROOT=$(pwd) \
python3 scripts/knowledge_extraction/backtest_framework.py
```

**預期輸出：**
```
============================================================
知識庫回測框架
============================================================
✅ 品質評估模式: basic（快速模式）
✅ 測試題庫來源: 資料庫 (aichatbot_admin)

🎯 測試選擇策略: incremental
📖 從資料庫載入測試情境（策略: incremental）...
   策略: 增量測試（新測試 + 失敗測試 + 長期未測試）
   限制: 100 個
   ✅ 載入 45 個測試情境
   📊 組成：新測試 20 | 失敗測試 15 | 長期未測試 10

🧪 開始回測...
[1/45] 測試問題: ...
   ✅ PASS (分數: 0.60)
...
```

### 2. 三種策略選擇

#### A. Incremental（日常使用）⭐ 推薦

```bash
BACKTEST_SELECTION_STRATEGY=incremental \
python3 scripts/knowledge_extraction/backtest_framework.py
```

**何時使用：**
- ✅ 每日早上自動執行
- ✅ Pull Request 驗證
- ✅ 快速回歸測試

**特點：** 只測試最重要的測試（新測試、失敗測試、長期未測試）

#### B. Full（週度使用）

```bash
BACKTEST_SELECTION_STRATEGY=full \
python3 scripts/knowledge_extraction/backtest_framework.py
```

**何時使用：**
- ✅ 每週五完整測試
- ✅ 版本發布前驗證
- ✅ 季度品質審查

**特點：** 測試所有已批准的測試

#### C. Failed Only（修復驗證）

```bash
BACKTEST_SELECTION_STRATEGY=failed_only \
python3 scripts/knowledge_extraction/backtest_framework.py
```

**何時使用：**
- ✅ 修復 Bug 後驗證
- ✅ 知識庫優化後測試
- ✅ 意圖調整後驗證

**特點：** 只測試之前失敗的測試

### 3. 查看結果

```bash
# 查看摘要
cat output/backtest/backtest_results_summary.txt

# 查看詳細結果（Excel）
open output/backtest/backtest_results.xlsx
```

## 進階用法

### 自訂測試數量

```bash
# 限制 incremental 為 30 個測試（快速驗證）
BACKTEST_SELECTION_STRATEGY=incremental \
BACKTEST_INCREMENTAL_LIMIT=30 \
python3 scripts/knowledge_extraction/backtest_framework.py

# 抽樣測試（從選中的測試中再抽樣）
BACKTEST_SELECTION_STRATEGY=incremental \
BACKTEST_SAMPLE_SIZE=10 \
python3 scripts/knowledge_extraction/backtest_framework.py
```

### 環境變數文件

創建 `backtest.env`：

```bash
# backtest.env
BACKTEST_USE_DATABASE=true
BACKTEST_SELECTION_STRATEGY=incremental
BACKTEST_QUALITY_MODE=basic
BACKTEST_NON_INTERACTIVE=true
PROJECT_ROOT=/Users/lenny/jgb/AIChatbot

# 資料庫配置（如有需要）
DB_HOST=localhost
DB_PORT=5432
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password
DB_NAME=aichatbot_admin
```

使用方式：

```bash
# 載入環境變數並執行
source backtest.env
python3 scripts/knowledge_extraction/backtest_framework.py

# 或一行命令
env $(cat backtest.env | xargs) python3 scripts/knowledge_extraction/backtest_framework.py
```

### 創建快捷腳本

```bash
# 創建 run_backtest.sh
cat > run_backtest.sh << 'EOF'
#!/bin/bash
cd /Users/lenny/jgb/AIChatbot

BACKTEST_SELECTION_STRATEGY=${1:-incremental} \
BACKTEST_QUALITY_MODE=basic \
BACKTEST_NON_INTERACTIVE=true \
BACKTEST_USE_DATABASE=true \
PROJECT_ROOT=$(pwd) \
python3 scripts/knowledge_extraction/backtest_framework.py
EOF

chmod +x run_backtest.sh

# 使用方式
./run_backtest.sh                # 預設 incremental
./run_backtest.sh full          # 完整測試
./run_backtest.sh failed_only   # 僅失敗測試
```

## 常見場景

### 場景 1：每日自動化測試

```bash
# 加入 crontab
crontab -e

# 每天早上 9:00 執行
0 9 * * * cd /Users/lenny/jgb/AIChatbot && BACKTEST_SELECTION_STRATEGY=incremental BACKTEST_NON_INTERACTIVE=true BACKTEST_USE_DATABASE=true python3 scripts/knowledge_extraction/backtest_framework.py >> logs/backtest.log 2>&1
```

### 場景 2：修復後快速驗證

```bash
# 1. 修改知識庫或意圖
vim knowledge_admin/...

# 2. 只測試失敗案例
BACKTEST_SELECTION_STRATEGY=failed_only \
BACKTEST_FAILED_LIMIT=20 \
python3 scripts/knowledge_extraction/backtest_framework.py

# 3. 檢查是否全部通過
grep "通過率" output/backtest/backtest_results_summary.txt
```

### 場景 3：週五完整測試

```bash
# 執行完整測試
BACKTEST_SELECTION_STRATEGY=full \
python3 scripts/knowledge_extraction/backtest_framework.py

# 如果通過率 < 80%，發送警報
pass_rate=$(grep "通過率" output/backtest/backtest_results_summary.txt | awk '{print $2}' | cut -d'%' -f1)

if (( $(echo "$pass_rate < 80" | bc -l) )); then
    echo "⚠️ 通過率過低: $pass_rate%"
    # 發送通知...
fi
```

### 場景 4：本地開發測試

```bash
# 快速測試（限制 10 個）
BACKTEST_SELECTION_STRATEGY=incremental \
BACKTEST_SAMPLE_SIZE=10 \
python3 scripts/knowledge_extraction/backtest_framework.py
```

## 結果解讀

### 摘要報告

```
============================================================
回測摘要
============================================================
通過率：85.00% (85/100)          ← 整體通過率
平均分數（基礎）：0.67            ← 平均評分
平均信心度：0.82                 ← RAG 系統信心度
============================================================
```

**評估標準：**
- **通過率 >= 90%**：✅ 優秀
- **通過率 >= 80%**：⚠️ 良好（需關注）
- **通過率 < 80%**：❌ 需改善

### 失敗案例

```
問題：請問停車位的租金怎麼算？
預期分類：帳務問題
實際意圖：合約規定               ← 意圖分類錯誤
分數：0.30
知識來源：無來源                 ← 沒有找到相關知識
優化建議：
意圖分類不匹配: 預期「帳務問題」但識別為「合約規定」
💡 建議: 在意圖管理中編輯「合約規定」意圖，添加更多相關關鍵字
```

**優化步驟：**
1. 前往知識管理界面
2. 搜尋相關知識（如有來源 ID，可直接點擊鏈接）
3. 補充或優化知識內容
4. 調整意圖設定
5. 重新執行 `failed_only` 測試驗證

### 知識來源鏈接

```
來源IDs：2,5,6
🔗 直接鏈接:
   1. http://localhost:8080/#/knowledge?search=2
   2. http://localhost:8080/#/knowledge?search=5
   3. http://localhost:8080/#/knowledge?search=6
📦 批量查詢: http://localhost:8080/#/knowledge?ids=2,5,6
```

點擊鏈接可直接跳轉到知識庫管理界面。

## 故障排除

### 問題 1：找不到測試

```
❌ 從資料庫載入測試情境失敗
```

**檢查：**
```bash
# 連接資料庫檢查測試數量
psql -h localhost -U aichatbot -d aichatbot_admin -c "SELECT COUNT(*) FROM test_scenarios WHERE status='approved' AND is_active=true;"
```

**解決：**
- 確認資料庫中有已批准的測試
- 檢查 `BACKTEST_USE_DATABASE=true` 是否設定

### 問題 2：載入 0 個測試（incremental/failed_only）

```
✅ 載入 0 個測試情境
```

**原因：** 所有測試都不符合策略條件

**解決：**
```bash
# 先執行一次 full 測試建立基線
BACKTEST_SELECTION_STRATEGY=full python3 scripts/knowledge_extraction/backtest_framework.py

# 然後再執行 incremental
BACKTEST_SELECTION_STRATEGY=incremental python3 scripts/knowledge_extraction/backtest_framework.py
```

### 問題 3：環境變數未生效

```bash
# 檢查環境變數
echo $BACKTEST_SELECTION_STRATEGY

# 確認傳遞到 Python
python3 -c "import os; print(os.getenv('BACKTEST_SELECTION_STRATEGY'))"

# 使用 env 確保傳遞
env BACKTEST_SELECTION_STRATEGY=incremental python3 backtest_framework.py
```

### 問題 4：資料庫連線失敗

```
❌ 從資料庫載入測試情境失敗: connection refused
```

**檢查：**
```bash
# 確認 PostgreSQL 運行
docker ps | grep postgres
# 或
pg_isready -h localhost -p 5432

# 測試連線
psql -h localhost -U aichatbot -d aichatbot_admin -c "SELECT 1;"
```

**解決：**
- 確認資料庫服務運行
- 檢查連線參數（DB_HOST, DB_PORT, DB_USER, DB_PASSWORD）
- 檢查防火牆設定

## 下一步

1. **閱讀詳細文檔**
   - [回測策略指南](./backtest_strategies.md)
   - [環境變數參考](./backtest_env_vars.md)
   - [Phase 2 更新日誌](./BACKTEST_PHASE2_CHANGELOG.md)

2. **CI/CD 整合**
   - 設定自動化測試流程
   - 配置通過率警報
   - 整合到 GitHub Actions / GitLab CI

3. **優化測試**
   - 分析失敗案例
   - 優化知識庫內容
   - 調整意圖設定

4. **探索進階功能**
   - LLM 深度評估（hybrid/detailed 模式）
   - 自訂測試策略
   - 趨勢分析（Phase 3）

## 快速參考

```bash
# 最常用的三個命令
BACKTEST_SELECTION_STRATEGY=incremental python3 scripts/...  # 日常
BACKTEST_SELECTION_STRATEGY=failed_only python3 scripts/...  # 驗證修復
BACKTEST_SELECTION_STRATEGY=full python3 scripts/...         # 完整測試

# 查看結果
cat output/backtest/backtest_results_summary.txt

# 檢查通過率
grep "通過率" output/backtest/backtest_results_summary.txt
```

---

**問題回報：** 如有問題請查閱 [故障排除文檔](./backtest_strategies.md#故障排除)

**最後更新：** 2025-10-12
