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
交易面向直達分支：
    ├─ trigger_facet_key 參數 → 直接進對話面向（跳過分類/檢索）
    └─ Step 0.5 損傷圖改道 → 偵測到報修損傷圖，不打 SOP 直接進修繕面向
    ↓
意圖分類（LLM Function Calling，主意圖 1.3x + 次意圖 1.1x 加成；意圖錨點命中「修繕報修」≥0.75 → 進修繕面向）
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

## 交易面向速查

面向體系分兩型：**診斷面向（唯讀，照 facts 組話）** 與 **交易面向（寫入，走確認 gate）**。交易面向判定＝面向配置 `grounding_scope.execute_endpoint` 存在，全配置驅動；下一個交易面向＝加配置與 seeds、引擎零改動（目標）。修繕為第一個交易面向。

- **confirm gate 一句話**：收齊欄位 ≠ 送出——brain 收齊後回 `confirm` action，引擎渲染確認卡，用戶按鈕同意才 execute 建單。
- **三鈕機器值**：`confirm_submit`（送出）／`confirm_edit`（修改）／`confirm_cancel`（取消）；同意判定在引擎層決定性比對機器值，非交給 brain 自由判讀。
- **冪等**：execute 成功後標 `executed`，防重複建單；失敗誠實告知可重試、不設旗標；取消不留殘單；brain 失敗絕不建單。
- **進場三路**：①分類路由（意圖錨點「修繕報修」≥0.75）②Step 0.5 損傷圖改道（不打 SOP 直接進面向）③`trigger_facet_key` 參數直達；三路共用 `repair_enabled` gate（vendor_configs，預設開，關→降級文案＋service_hotline）。
- **配置鍵鐵則**：面向配置 `target_user` 必須＝persona_role（修繕＝`tenant_repair`），寫錯 load_rules 查不到 → 全程降級。
- **輪數可觀測**：usage_events 埋 `facet_key`／`turn_number`（M3）；P50/P90 以 per-session MAX 聚合，上線目標 P50≤4／P90≤6（含岔題），未達標觸發設計覆核。
- **詳節**：面向配置結構、grounding_scope、確認 gate 完整流程見 [docs/architecture/facet-architecture.md](../../docs/architecture/facet-architecture.md)。

## 候選分流速查（診斷面向）

API grounding 回 N 筆時：`N ≤ candidate_cap` → 直接列候選供選序號；`N > cap` → 預設先請使用者「補更明確的識別」，補不動才截斷列前 cap 筆。

- **`result_mapping.skip_refine`（預設關）**：同母體多期資料（如同一合約的 26 期帳單）用關鍵字縮不了，補識別是**問使用者答不出來的問題** → 設 true 直接列候選，少一輪。
- ⚠️ **跳過的是「補識別輪」，不是「重查」**：使用者選定候選後仍會填回 `required_slots[0]` 並**重查 API**，實證收斂單筆（任務 7 定案）。誤讀成跳過重查 → 有人會拿候選列欄位當 grounding，底稿就失去 API 權威來源。
- 旗標住在 `result_mapping`，管的卻是對話政策；它同時承載「此實體集合無法以關鍵字縮小」這個資料形狀事實。**不改鍵名**（改名＝改既有 DB 配置列），靠本條與程式註解防誤讀。

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
| 對話面向引擎／交易語義 | `services/conversational_engine.py` |
| 修繕槽位預填 | `services/jgb/repair_prefill.py` |
| SOP 編排 | `services/sop_orchestrator.py` |
| 知識檢索 | `services/vendor_knowledge_retriever_v2.py` |
| 表單管理 | `services/form_manager.py` |
| 意圖分類 | `services/intent_classifier.py` |
| 答案優化 | `services/llm_answer_optimizer.py` |
| 統一檢索 | `services/base_retriever.py` |
| 信心度評估 | `services/confidence_evaluator.py` |
| 緩存 | `services/cache_service.py` |
