# 業務邏輯測試 - 快速開始指南

## 🚀 5 分鐘快速開始

### 步驟 1：確保服務運行中

```bash
# 在專案根目錄
docker-compose up -d

# 等待服務啟動（約 30 秒）
sleep 30

# 檢查服務狀態
curl http://localhost:8100/health
```

### 步驟 2：安裝測試依賴

```bash
pip3 install pytest requests
```

### 步驟 3：執行快速測試（1 分鐘）

```bash
# 方法 1：使用腳本（推薦）
./scripts/run_business_logic_tests.sh
# 選擇選項 1（快速測試）

# 方法 2：直接使用 pytest
cd tests/integration
pytest test_business_logic_matrix.py -v -s -k "rent_payment"
```

### 步驟 4：查看測試結果

成功的輸出應該類似：

```
test_business_logic_matrix.py::TestScenario1_FullService::test_full_service_questions[rent_payment] PASSED

✅ 測試通過：租金怎麼繳？
   語氣：主動服務型 (匹配 3 個關鍵詞)
   內容：金流過公司 (匹配 4 個關鍵詞)
```

## 📋 完整測試（6 分鐘）

```bash
# 測試所有 4 種情境 × 6 個問題 = 24 個測試
./scripts/run_business_logic_tests.sh
# 選擇選項 2（完整測試）
```

## 🎯 測試單一情境

```bash
# 只測試包租型
pytest tests/integration/test_business_logic_matrix.py::TestScenario1_FullService -v -s

# 只測試純代管型-混合型
pytest tests/integration/test_business_logic_matrix.py::TestScenario4_PropertyManagement_Hybrid -v -s
```

## 🔍 交叉驗證測試

```bash
# 驗證不同情境之間的差異
pytest tests/integration/test_business_logic_matrix.py::TestCrossValidation -v -s
```

## ❓ 常見問題

### Q: pytest 找不到模組

```bash
pip3 install pytest requests
```

### Q: API 連接失敗

```bash
# 檢查服務狀態
docker-compose ps

# 重啟 RAG 服務
docker-compose restart rag-orchestrator

# 查看日誌
docker-compose logs -f rag-orchestrator
```

### Q: 測試失敗但不知道原因

```bash
# 使用 -vv 獲取更詳細的輸出
pytest tests/integration/test_business_logic_matrix.py -vv -s

# 使用 --tb=long 查看完整錯誤追蹤
pytest tests/integration/test_business_logic_matrix.py --tb=long
```

## 📚 更多資訊

詳細說明請參考：[README_BUSINESS_LOGIC_TESTS.md](./README_BUSINESS_LOGIC_TESTS.md)
