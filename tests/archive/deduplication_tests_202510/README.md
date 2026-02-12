# 去重測試歸檔 - 2025年10月

## 歸檔時間
2026-02-12 15:50

## 歸檔原因
去重功能已穩定，測試文件最後更新於 2025年10月（4個月前）。
功能正常運作中，但測試不需要頻繁執行。

---

## 歸檔文件清單（7 個）

1. `verify_duplicate_detection.py` - 端到端驗證（與 test_duplicate_detection_direct.py 重複）
2. `test_duplicate_detection_direct.py` - 直接重複檢測測試
3. `test_enhanced_detection.py` - 增強檢測測試
4. `test_error_severity.py` - 錯誤嚴重度測試
5. `test_typo_similarity.py` - 拼寫相似度測試
6. `test_parser_only.py` - 解析器測試
7. `test_sop_retriever.py` - SOP 檢索器測試（2026-02-12 新增）

**最後更新**: 2025-10-13 ~ 2025-10-18

**2026-02-12 更新**: 新增 test_sop_retriever.py，與其他去重測試保持一致歸檔邏輯

---

## 功能狀態

| 功能 | 狀態 | 說明 |
|------|------|------|
| 重複問題檢測 | ✅ 穩定 | 已在生產環境運行 4個月 |
| 增強檢測 | ✅ 穩定 | 功能正常 |
| 拼寫相似度 | ✅ 穩定 | 功能正常 |
| 錯誤嚴重度 | ✅ 穩定 | 功能正常 |

---

## 恢復使用方法

如需重新測試去重功能：

1. 從歸檔移回：
```bash
cp tests/archive/deduplication_tests_202510/<file> tests/deduplication/
```

2. 在 Docker 容器內執行：
```bash
docker exec -it aichatbot-rag-orchestrator python3 tests/deduplication/<file>
```

---

## 未來處理建議

- **如去重功能需要重大更新**: 恢復測試並更新
- **如功能持續穩定**: 可於 6個月後（2026-08-12）永久刪除
- **建議**: 保留至少 1年以供參考

---

**歸檔者**: Development Team
**版本**: v1.0
