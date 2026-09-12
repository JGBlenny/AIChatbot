# 對話系統演化原則（2026-07-10 定案）

**最後對碼：2026-09-12**

## 演化原則（2026-07-10 定案，⛔ 仍然有效）

> 這是本檔僅存的內容。2026-09-12 刪掉 §3 觸發語彙盤點、§4 關係規則、§5 應然 vs 實然、
> §6 的「方向正確的證據」——它們的受測物（`chat.py`／`sop_orchestrator.py`／
> `sop_trigger_handler.py`／`digression_detector.py`／`form_manager.py`）已於 2026-09-11
> 刪除，表格卻把它們標成「🟢 活」。⛔ 不加退役標記，直接刪。
>
> §3 的觸發語彙診斷另有完整正本：`.kiro/specs/trigger-vocabulary-debt/`（5 份）。
> 「骨架重心」評估見 `docs/conversation-first-architecture-assessment.md`。
> 現況架構見 [`architecture/SYSTEM_ARCHITECTURE.md`](architecture/SYSTEM_ARCHITECTURE.md)
> 與 [`architecture/AGENTIC_MCP_ARCHITECTURE.md`](architecture/AGENTIC_MCP_ARCHITECTURE.md) §2b。

**演化原則**（定案）：
1. 語義層保持薄：錨點只做認出與路由，不承載流程與資料
2. 流程機器承重：多步驟進表單/chaining/決策樹/面向；判準＝有沒有「下一步」
3. 通用 vs 客製就近落位：平台語義→通用知識；業者差異按強度→configs/業者知識/SOP/表單變體
4. 決定性優先：明確場景 template/formatter，模糊場景才 LLM
5. 入口越明確越早攔截：按鈕→入口層；明確句式→語義錨點；模糊→檢索兜底＋澄清
6. 觸發語彙收斂：**⛔ 不再新增第四套觸發機制**
   🔴 2026-09-12 更正：原文寫「以 SOP 側（活的那套）為基準」——**SOP 側已不活**
   （編排器與觸發器 2026-09-11 刪除，對話路徑對 `vendor_sop_items` 零讀取）。
   現行只有一套：`services/agent/tools/registry.py` 的工具註冊表，由模型選工具。
   這條原則存活的部分是「不要再開新機制」，不是「向 SOP 對齊」。
