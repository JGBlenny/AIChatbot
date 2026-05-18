# Dialogue Steering

> **完整文件**：[docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md](../../docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md)
>
> **相關文件**：
> - Retriever Pipeline：[docs/architecture/retriever-pipeline.md](../../docs/architecture/retriever-pipeline.md)
> - 知識資料結構：[knowledge.md](./knowledge.md)

本文件為 AI 引導用摘要，詳細邏輯與圖表請查閱完整文件。

---

## 對話處理核心流程

```
用戶問題
    ↓
表單會話檢查（進行中表單優先）
    ↓
業者驗證 + 緩存檢查
    ↓
意圖分類（LLM Function Calling，主意圖 1.3x + 次意圖 1.1x 加成）
    ↓
智能檢索（SOP + 知識庫並行）
    ↓
特殊情況處理（0A 取消 / 0B 已觸發 / 0C 等待關鍵詞）
    ↓
分數比較決策（Case 1~6：SOP 0.55 / KB 0.6 / 差距 0.15）
    ↓
處理路徑選擇：
    ├─ SOP 路徑：觸發模式處理（none/manual/immediate/auto）+ 後續動作
    └─ 知識庫路徑：信心度評估 → 答案優化（完美匹配/合成/快速路徑/模板/LLM）
    ↓
業者參數注入 → 緩存存儲 → 返回回應（JSON/SSE）
```

## 關鍵決策閾值

| 閾值 | 值 | 比對欄位 |
|------|-----|---------|
| SOP 最低 | 0.55 | similarity |
| KB 最低 | 0.6 | similarity |
| 顯著差距 | 0.15 | — |
| 完美匹配 | 0.90 | vector_similarity |
| 合成閾值 | 0.80 | similarity |
| 快速路徑 | 0.75 | similarity |
| 高信心 | >= 0.85 | confidence_score |
| 中信心 | 0.70-0.85 | confidence_score |

## SOP 觸發模式速查

| 模式 | 行為 | 使用場景 |
|------|------|---------|
| `none`/null | 純資訊展示 | 政策說明 |
| `manual` | 等待 trigger_keywords | 用戶主動確認 |
| `immediate` | 詢問確認（短訊息判定） | 即時確認操作 |
| `auto` | 立即執行後續動作（不等待） | 自動觸發表單/API |

## 表單狀態機速查

```
COLLECTING → DIGRESSION（離題） / REVIEWING（完成）/ CONFIRMING（SOP 確認）/ PAUSED（暫停）
CONFIRMING → COLLECTING（確認） / CANCELLED（取消）
DIGRESSION → COLLECTING / CANCELLED
REVIEWING → EDITING / COMPLETED / PAUSED（API 前暫停） / CANCELLED
EDITING → REVIEWING
PAUSED → COLLECTING / CANCELLED（超時 30 分鐘）
```

## 答案優化策略速查

1. **完美匹配** (>= 0.90)：直出，不經 LLM
2. **合成** (>= 2 結果 + 複雜問題)：LLM 整合多來源
3. **快速路徑** (>= 0.75 + 單一結果)：模板格式化
4. **模板** (0.55-0.75)：套用模板
5. **完整 LLM** (< 0.55)：LLM 優化

## 系統角色對應

| 組件 | 檔案 |
|------|------|
| 主入口 | `routers/chat.py` |
| SOP 編排 | `services/sop_orchestrator.py` |
| 知識檢索 | `services/vendor_knowledge_retriever_v2.py` |
| 表單管理 | `services/form_manager.py` |
| 意圖分類 | `services/intent_classifier.py` |
| 答案優化 | `services/llm_answer_optimizer.py` |
| 統一檢索 | `services/base_retriever.py` |
| 信心度評估 | `services/confidence_evaluator.py` |
| 緩存 | `services/cache_service.py` |
