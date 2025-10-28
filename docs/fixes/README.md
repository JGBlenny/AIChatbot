# 🔧 系統修復記錄

此目錄包含重要的系統問題修復文檔。

---

## 📋 修復清單

### 2025-10-29

#### ✅ Business Types 欄位名稱錯誤修復（Critical P0）
**檔案**: [2025-10-29-business-types-field-name-fix.md](./2025-10-29-business-types-field-name-fix.md)

**問題**: `vendor_parameter_resolver.py` 查詢錯誤的資料庫欄位名稱導致通用知識無法被檢索

**影響**:
- B2C 模式下通用知識（`business_types: null`）完全無法檢索
- 知識庫檢索結果為空，即使知識存在且向量正確
- 回測系統失敗（例如：知識 497「可以養寵物嗎」檢索失敗）

**修復**:
- 更正欄位名稱：`business_type` → `business_types`（singular → plural）
- 修改檔案：`vendor_parameter_resolver.py:272`
- 修改檔案：`chat.py:456, 631-633`（資料結構鍵值一致性）

**結果**:
- ✅ B2C 通用知識檢索恢復正常
- ✅ 回測系統運作正常
- ✅ 資料結構鍵值錯誤同步修復

#### ✅ 多意圖獨立信心度評分（Solution A）
**相關議題**: 副意圖信心度固定衰減不精確

**問題**: 副意圖使用主意圖 * 0.85 固定衰減值，不夠精確

**影響**:
- 副意圖信心度無法反映 LLM 真實判斷
- 例如：主意圖 0.9，副意圖應為 0.7，但系統計算為 0.765

**修復**:
- LLM Function Schema 改為返回結構化物件：`{name, confidence}`
- 主意圖與副意圖皆獨立評分（0-1 範圍）
- 資料庫直接儲存 LLM 原始信心度
- 修改檔案：`intent_classifier.py:211-377`, `knowledge_classifier.py:150-190`

**結果**:
- ✅ 副意圖信心度準確反映 LLM 判斷
- ✅ 知識 510 驗證：主意圖 0.9，副意圖 0.7（非 0.765）
- ✅ Migration 49 修復現有 86 筆資料

### 2025-10-21

#### ✅ 拼音去重檢測修復
**檔案**: [PINYIN_DETECTION_FIX_REPORT.md](./PINYIN_DETECTION_FIX_REPORT.md)

**問題**: PostgreSQL vector 類型轉換錯誤導致拼音相似度檢測失敗

**影響**:
- 嚴重同音錯誤無法被正確合併（例如「每月租金」vs「美越租金」）
- 測試通過率：5/6 (83%)

**修復**:
- 正確解析 asyncpg 返回的 pgvector 字符串格式
- 修改 `unclear_question_manager.py:127-148`

**結果**:
- ✅ 測試通過率：6/6 (100%)
- ✅ 拼音相似度達到 1.0000（完美匹配）

---

## 📊 統計

| 日期 | 修復數量 | 類型 | 影響範圍 |
|------|---------|------|---------|
| 2025-10-29 | 2 | Critical Bug Fix + Enhancement | 知識檢索、多意圖信心度、UI |
| 2025-10-21 | 1 | Bug Fix | 去重檢測 |

---

## 🔍 查找修復

### 按功能模組
- **知識檢索**: [Business Types 欄位名稱修復](./2025-10-29-business-types-field-name-fix.md)
- **多意圖分類**: [獨立信心度評分](./2025-10-29-business-types-field-name-fix.md)
- **去重檢測**: [拼音檢測修復](./PINYIN_DETECTION_FIX_REPORT.md)

### 按影響等級
- **Critical**: [Business Types 欄位名稱修復](./2025-10-29-business-types-field-name-fix.md)
- **高**: [拼音檢測修復](./PINYIN_DETECTION_FIX_REPORT.md)

---

## 📝 修復報告規範

每個修復報告應包含：

1. **問題描述**: 症狀、錯誤訊息
2. **根本原因**: 技術分析
3. **修復方案**: 代碼變更
4. **測試結果**: 修復前後對比
5. **影響範圍**: 受益功能列表
6. **後續建議**: 長期改進方案

---

**最後更新**: 2025-10-29
