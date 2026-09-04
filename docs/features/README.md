# 🎯 Features - 功能文檔索引

**最後更新**: 2026-09-04（依實況重建）
**文件總數**: 19 份（本目錄 12 ＋ `sop/` 子樹 7）

> 🔴 **2026-09-04 重建說明**：此前本索引自稱「24 個功能文件」，實際提到 30 個檔名、
> 其中 **19 個已不存在**（存活率 36%），同時漏列 8 份確實存在的檔案。
> 已移除的死引用包括 `INTENT_MANAGEMENT_README.md`、`MULTI_INTENT_CLASSIFICATION.md`、
> `MULTI_INTENT_SCORING.md`、`PRIORITY_SYSTEM.md`、`B2B_API_INTEGRATION.md`、
> `PRIMARY_EMBEDDING_FIX.md`、`VENDOR_SOP_RETRIEVAL_IMPROVEMENT.md`、
> `LINE_CHAT_IMPORT_FINAL_SUMMARY.md` 等 19 份——它們的歷史在 git log。
> ⛔ 新增或搬移檔案後務必回來更新本表，否則它會再次變成騙人的索引。

---

## 📋 本目錄的文件

### 🤖 檢索與知識

| 文件 | 說明 |
|------|------|
| [DUAL_EMBEDDING_RETRIEVAL.md](./DUAL_EMBEDDING_RETRIEVAL.md) | 雙 Embedding 檢索：`GREATEST(primary, fallback)` |
| [RERANKER_FEATURE.md](./RERANKER_FEATURE.md) | Reranker 重排序機制 |
| [KNOWLEDGE_SCOPE_SIMPLIFICATION.md](./KNOWLEDGE_SCOPE_SIMPLIFICATION.md) | 知識範圍從 `scope` 欄位簡化為 `vendor_id` 判定 |
| [DOCUMENT_CONVERTER.md](./DOCUMENT_CONVERTER.md) | 文件轉換（Word/PDF → Q&A），含 API 端點與成本估算 |

### 📋 表單

| 文件 | 說明 |
|------|------|
| [FORM_MANAGEMENT_SYSTEM.md](./FORM_MANAGEMENT_SYSTEM.md) | 動態表單收集系統：Schema、API、前端整合 |
| [KNOWLEDGE_FORM_TRIGGER_IMPLEMENTATION.md](./KNOWLEDGE_FORM_TRIGGER_IMPLEMENTATION.md) | 知識觸發表單的實作 |
| [knowledge-form-auto-option.md](./knowledge-form-auto-option.md) | 表單自動選擇功能的改進**設計方案**（2026-02-05） |
| [knowledge-form-auto-quick-ref.md](./knowledge-form-auto-quick-ref.md) | 表單 Auto 選項**速查**（2026-07-22） |

> ⚠️ 上兩份是同主題的設計版與速查版。**兩份都沒有任何一句宣告取代關係**，
> 誰是正本待裁 —— ⛔ 不要自行認定其中一份已作廢。

### 🔐 系統管理

| 文件 | 說明 |
|------|------|
| [AUTH_SYSTEM_README.md](./AUTH_SYSTEM_README.md) | 管理後台 JWT 認證系統與安全配置 |
| [PERMISSION_SYSTEM_README.md](./PERMISSION_SYSTEM_README.md) | 帳號權限系統（RBAC）架構總覽 |

### 💬 對話

| 文件 | 說明 |
|------|------|
| [conversational-presales.md](./conversational-presales.md) | 對話式回答模式：單次直答 → 多輪自適應收斂 |

---

## 📁 `sop/` 子樹

| 文件 | 說明 |
|------|------|
| [sop/README.md](./sop/README.md) | SOP 系統文檔索引 |
| [sop/SOP_TRIGGER_MODE_UPDATE_INDEX.md](./sop/SOP_TRIGGER_MODE_UPDATE_INDEX.md) | SOP 觸發模式 UI 更新（2026-02-03）的文檔導引 |
| [sop/implementation/VENDOR_SOP_FLOW_CONFIGURATION.md](./sop/implementation/VENDOR_SOP_FLOW_CONFIGURATION.md) | Vendor SOP 流程配置：4 種觸發模式 × 4 種後續動作 |
| [sop/implementation/SOP_NEXT_ACTION_IMPLEMENTATION.md](./sop/implementation/SOP_NEXT_ACTION_IMPLEMENTATION.md) | SOP 後續動作的實作說明與進度 |
| [sop/implementation/SOP_FLOW_STRICT_VALIDATION_2026-01-26.md](./sop/implementation/SOP_FLOW_STRICT_VALIDATION_2026-01-26.md) | 觸發模式與後續動作的有效組合嚴格限制 |
| [sop/optimization/SOP_KEYWORDS_COMPARISON.md](./sop/optimization/SOP_KEYWORDS_COMPARISON.md) | `keywords` 與 `trigger_keywords` 的欄位差異 |
| [sop/testing/SOP_TRIGGER_MODE_TEST_EXECUTION_GUIDE.md](./sop/testing/SOP_TRIGGER_MODE_TEST_EXECUTION_GUIDE.md) | ⚠️ **2026-02-03 的測試執行紀錄**（含測試資料、發現問題、簽核）——已判為快照，⛔ 不是現行指南 |

⚠️ SOP 相關文件另散在 `docs/guides/features/`（`SOP_GUIDE.md`、`SOP_EXCEL_IMPORT_GUIDE.md`）
與 `docs/guides/reference/SOP_QUICK_REFERENCE.md`，那三份已列於 `.claude/MAP.md`〈SOP 受眾隔離〉。

---

## 🌟 從哪份開始讀

**管理員**：`FORM_MANAGEMENT_SYSTEM.md` → `DOCUMENT_CONVERTER.md` → `PERMISSION_SYSTEM_README.md`
**開發者**：`AUTH_SYSTEM_README.md` → `DUAL_EMBEDDING_RETRIEVAL.md` → `RERANKER_FEATURE.md`
**知識維護者**：`sop/implementation/VENDOR_SOP_FLOW_CONFIGURATION.md` → `KNOWLEDGE_SCOPE_SIMPLIFICATION.md`

---

## 🔗 相關資源

- [主項目 README](../../README.md)
- [API 文檔索引](../api/README.md)
- [系統架構](../architecture/SYSTEM_ARCHITECTURE.md)
- [快速開始指南](../guides/getting-started/QUICKSTART.md)
- `.claude/MAP.md` — 產品功能地圖（哪個功能對應哪份規格／產線／判準）

---

## 📝 新增功能文件指南

### 文件命名規範

- 使用全大寫 + 底線：`FEATURE_NAME.md`
- 包含功能關鍵字：`FORM_`、`INTENT_`、`AUTH_` 等
- 完整文件加 `_SYSTEM` 或 `_FEATURE` 後綴

### 必須包含的章節

1. **概述** — 功能簡介、使用情境
2. **功能特色** — 核心功能列表
3. **系統架構** — 前後端互動、資料流
4. **API 端點** — 完整 API 文件
5. **使用指南** — 操作步驟、範例
6. **資料庫設計** — 相關資料表
7. **故障排除** — 常見問題

⛔ **不要寫行號**——行號隨每次 commit 漂移，一律以可 grep 的符號名引用。

### 更新索引

新增、搬移或刪除功能文件後，**必須**回來更新本 README 的表格。
可用 `find docs/features -name '*.md' | sort` 對帳。
