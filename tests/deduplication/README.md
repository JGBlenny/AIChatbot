# 去重檢測測試

此目錄包含未釐清問題去重檢測功能的測試文件。

## 測試文件

### 功能測試
- `test_duplicate_detection_direct.py` - 直接調用去重檢測功能的測試
- `test_enhanced_detection.py` - 增強去重檢測（語義 + 編輯距離 + 拼音）測試
- `test_enhanced_detection_api.py` - 去重檢測 API 端點測試
- `test_error_severity.py` - 錯誤嚴重程度檢測測試
- `test_typo_similarity.py` - 拼音相似度檢測測試

### 驗證工具
- `verify_duplicate_detection.py` - 去重檢測功能驗證腳本

## 執行測試

```bash
# 執行所有去重檢測測試
pytest tests/deduplication/

# 執行特定測試
pytest tests/deduplication/test_enhanced_detection.py

# 驗證去重功能
python tests/deduplication/verify_duplicate_detection.py
```

## 相關文檔

- [去重檢測架構文檔](../../docs/features/)
- [API 文檔](../../docs/api/)
