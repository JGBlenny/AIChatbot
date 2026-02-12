# 2025年10月舊測試歸檔

## 歸檔時間
2026-02-12 15:50

## 歸檔原因
這些測試文件最後更新於 2025年10月（4個月前），長期未維護和更新。
為保持測試目錄整潔，移至歸檔保存。

---

## 歸檔文件清單

### integration/ (6 個文件)
1. `test_knowledge_import.py` - 知識匯入測試數據生成
2. `run_import_test.py` - 知識匯入流程測試
3. `test_scoring_quality.py` - 評分質量測試
4. `test_multi_intent_rag.py` - 多意圖 RAG 系統測試
5. `test_multi_intent.py` - 多意圖分類測試
6. `test_business_logic_matrix.py` - 業務邏輯矩陣測試

**歸檔原因**: 最後更新 2025-10-18，4個月未更新

### shell_scripts/ (2 個文件)
1. `run_advanced_tests.sh` - 進階測試執行腳本
2. `run_business_logic_tests.sh` - 業務邏輯測試執行腳本

**歸檔原因**: 最後更新 2025-10-18，4個月未使用

### manual/ (2 個文件)
1. `test_business_types_filtering.py` - 業務類型過濾測試
2. `test_tone_final.py` - 語氣調整測試

**歸檔原因**: 最後更新 2025-10-25，功能已穩定

---

## 保留的核心測試

### integration/ (保留 2 個)
- `test_parameter_injection.py` - 參數動態注入測試（核心功能）
- `test_fallback_mechanism.py` - Fallback 機制測試（核心功能）

### manual/ (保留 1 個)
- `test_comprehensive_chat_flow.sh` - 完整聊天流程測試（2026-01-24 更新）

---

## 恢復使用方法

如需重新使用這些測試：

1. 從歸檔移回工作目錄：
```bash
cp tests/archive/old_tests_202510/integration/<file> tests/integration/
```

2. 更新測試代碼以適配當前系統

3. 更新測試文檔

---

## 未來處理建議

- **3個月後（2026-05-12）**: 評估是否需要永久刪除
- **如需保留**: 更新測試適配新系統
- **如不需要**: 可安全刪除整個目錄

---

**歸檔者**: Development Team
**版本**: v1.0
