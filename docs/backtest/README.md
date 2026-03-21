# 回測系統文檔索引

**最後更新**: 2026-03-18 (表單 Session 隔離修復完成)

---

## 📌 核心文檔（5個）

### 1. [ACTUAL_TESTING_STATUS.md](./ACTUAL_TESTING_STATUS.md) ⭐⭐
**最新實際狀態**
- V2 評估邏輯實作完成
- Similarity Extraction 修復完成 (解決 max_similarity=0.0 問題)
- 表單 Session 隔離修復完成 (解決連續污染問題)
- Docker 基礎設施修復完成
- Run 77 測試驗證

### 2. [FORM_SESSION_ISOLATION_FIX.md](./FORM_SESSION_ISOLATION_FIX.md) 🆕 ⭐
**表單 Session 隔離修復**
- 問題描述：連續 30+ 題被困在同一表單
- 修復方案：獨立 session_id 生成機制
- 驗證結果：完全消除 session 污染
- 部署步驟與後續建議

### 3. [QUICK_START_V2.md](./QUICK_START_V2.md) ⭐
**快速入門指南**
- V2 系統使用說明
- confidence_score 計算邏輯
- 評估指標說明（confidence_score, confidence_level, semantic_overlap）
- 常見問題 FAQ

### 4. [CONTINUOUS_BATCH_TESTING_GUIDE.md](./CONTINUOUS_BATCH_TESTING_GUIDE.md)
**連續分批測試功能**
- 智能分批執行
- 資料庫架構
- API 端點說明
- 前端 UI 功能

### 5. [README.md](./README.md)
**本文檔**
- 文檔索引
- 快速導航

---

## 🎯 快速開始

1. **了解當前狀態**: 閱讀 [ACTUAL_TESTING_STATUS.md](./ACTUAL_TESTING_STATUS.md)
2. **查看最新修復**: 閱讀 [FORM_SESSION_ISOLATION_FIX.md](./FORM_SESSION_ISOLATION_FIX.md) 🆕
3. **學習使用**: 閱讀 [QUICK_START_V2.md](./QUICK_START_V2.md)
4. **批量測試**: 閱讀 [CONTINUOUS_BATCH_TESTING_GUIDE.md](./CONTINUOUS_BATCH_TESTING_GUIDE.md)
5. **查看更新記錄**: 閱讀 [CHANGELOG.md](./CHANGELOG.md)

---

## 📝 其他文檔

- [CHANGELOG.md](./CHANGELOG.md) - 系統更新日誌

---

**維護者**: Claude
**最後更新**: 2026-03-18
