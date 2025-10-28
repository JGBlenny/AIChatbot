# 測試數據

此目錄包含用於測試和驗證的數據文件。

## 📋 數據文件清單

### 回測情境數據

#### 1. test_scenarios_smoke.xlsx
- **用途**: 煙霧測試情境數據（快速驗證）
- **類型**: Excel 格式
- **日期**: 2025-10-25
- **包含**: 基本測試情境，用於快速驗證系統功能

#### 2. test_scenarios_full.xlsx
- **用途**: 完整測試情境數據（全面測試）
- **類型**: Excel 格式
- **日期**: 2025-10-25
- **包含**: 完整的測試情境集合，覆蓋各種場景

## 📊 數據格式

### 回測情境 Excel 格式
```
欄位：
- question: 測試問題
- expected_answer: 預期答案
- difficulty: 難度（easy/medium/hard）
- business_type: 業態類型
- category: 分類
- notes: 備註
```

## 🚀 使用方式

### 1. 回測執行
```bash
# 使用煙霧測試數據（快速）
docker exec -it aichatbot-knowledge-admin-api \
  python scripts/knowledge_extraction/backtest_framework.py \
  --input tests/data/test_scenarios_smoke.xlsx

# 使用完整測試數據
docker exec -it aichatbot-knowledge-admin-api \
  python scripts/knowledge_extraction/backtest_framework.py \
  --input tests/data/test_scenarios_full.xlsx
```

### 2. 透過 API 上傳
```bash
curl -X POST http://localhost:8000/api/backtest/run \
  -F "file=@tests/data/test_scenarios_smoke.xlsx" \
  -F "quality_mode=basic"
```

## 📝 數據維護

### 添加新測試情境
1. 打開 Excel 文件
2. 按照格式添加新行
3. 確保所有必填欄位完整
4. 儲存並測試

### 數據更新記錄
| 日期 | 文件 | 變更 |
|------|------|------|
| 2025-10-28 | * | 遷移到 tests/data/ 目錄 |

## 🔄 遷移記錄

**遷移日期**: 2025-10-28
**原位置**: 根目錄
**新位置**: `tests/data/`
**原因**: 整理項目結構，統一測試數據管理

## 🎯 相關文檔

- [回測優化指南](../../docs/guides/BACKTEST_OPTIMIZATION_GUIDE.md)
- [測試情境管理](../../docs/features/TEST_SCENARIO_STATUS_MANAGEMENT.md)
- [回測品質整合](../../docs/backtest/BACKTEST_QUALITY_INTEGRATION.md)

---

**維護**: 測試團隊
**狀態**: 活躍使用中
