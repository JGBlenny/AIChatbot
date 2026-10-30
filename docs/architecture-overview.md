# AIChatbot 系統架構總覽（指路檔）

> 🎯 **本檔寫現況，不是設計依據。目標：本系統是對話服務，不是 MCP 系統；呼叫端走專用對話 API，`/mcp` 不是最終入口；JGB 工具要搬出本系統，由 JGB 維護。** 分工與完整架構見 `docs/architecture/TARGET_ARCHITECTURE.md`。

> **最後對碼：2026-09-12**
>
> 🔴 **本檔已於 2026-09-12 整份改寫成指路檔。** 前一版（更新於 2026-07-11）把舊 REST
> 對話鏈寫成現況——`POST /api/v1/message` 單一入口、21＋售前對話面向、SOP 檢索、
> 表單狀態機——**那些機制已於 2026-09-11 隨 31 個模組刪除**（DSP-046）。
>
> **為什麼不只是加警語就好**：前一版檔頭已經寫了「本檔全篇已過時、⛔ 勿以本檔為
> 現況入口」，但 2026-09-12 的對照實驗證明**沒有用**——一位只讀文件的工程師仍然
> 從本檔讀走「21＋售前面向」，因而**完全答不出現行有幾個 face**（程式清楚是 16 個）。
> 讀者不會為了一句警語放棄一張看起來很完整的表。⇒ 依 D-001，**以 runtime 為準逐節改寫**。

---

## 目標與現況看哪裡

| 想知道 | 去哪裡 |
|---|---|
| **應該長什麼樣**（目標架構、分工、原則、差距；設計以這份為準） | [`docs/architecture/TARGET_ARCHITECTURE.md`](architecture/TARGET_ARCHITECTURE.md) |
| **系統全景**（核心／門面／知識兩條路／後台維護面／已知缺陷） | [`docs/architecture/SYSTEM_ARCHITECTURE.md`](architecture/SYSTEM_ARCHITECTURE.md) |
| **對話線內部**（元件責任、一回合的完整流程、每個分岔與終止點） | [`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`](architecture/AGENTIC_MCP_ARCHITECTURE.md)（§2b 是逐步流程） |
| **`/mcp` 串接契約**（header、工具、錯誤碼、額度） | [`docs/api/mcp-facade.md`](api/mcp-facade.md) |
| **檢索分數欄位** | [`docs/architecture/retriever-pipeline.md`](architecture/retriever-pipeline.md) |
| **資料表 schema** | [`docs/architecture/DATABASE_SCHEMA.md`](architecture/DATABASE_SCHEMA.md) |
| **部署** | [`docs/deployment-runbook.md`](deployment-runbook.md) |
| **任務導向索引** | [`docs/INDEX.md`](INDEX.md) |

**三句話現況**（逐項可對碼，詳見上表第二列）：

1. **核心是 `AgentRuntime`**（`services/agent/runtime.py`），它的建構依賴裡**沒有任何協定或門面**。
2. **`/mcp` 是門面之一**，且是目前唯一掛著的（目標是對話改走專用對話 API）；另有 `agent_entry`（遷移橋，上游已滅）、
   `agent_eval`（回測）、`shadow`（影子）。⚠️ 「門面之一」⛔ 不等於「門面很薄」。
3. **受眾只有兩種**：`prospect` 與 `property_manager` 有 canon 正本；
   **`tenant` 在新線完全不存在**（無 `canon/tenant.md`、`AGENT_TURN_SPEC` 無該鍵）。

---

## 仍然成立的一節：資料體系分工（2026-07-06 定案）

⚠️ 這張表的**分工原則**仍是現行的；但「消費端」欄已隨舊鏈變動，已就地更正。

| 體系 | 內容 | 粒度 | 維護動線 | 消費端（2026-09-12 對碼） |
|---|---|---|---|---|
| `knowledge_base` | 系統知識＋錨點（＋已無消費者的面向規則／系統脈絡列） | 全域/受眾 | 人工閘門＋import 工具 | **只剩 `kb.search`／`kb.get` 兩支工具**；⚠️ 大綱**不讀它**（正本在 git `canon/*.md`） |
| `vendor_sop_items` | 各業者客服標準回覆 | per-vendor | 後台 | 🔴 **對話路徑零讀取**——檢索程式已刪。後台仍可維護、存檔時仍真的算 embedding，但沒有任何程式會查 |
| `vendor_configs` | 通用單值參數（電話/LINE/營業時間/繳費日） | per-vendor | 後台 | `{{param}}` 模板注入；⚠️ 注入實作隨 `llm_answer_optimizer` 刪除，消費端待對碼 |
| `lookup_tables` | 案場級/清單級（各棟管理費/包裹/水電/廠商） | per-vendor per-key | Excel 統一匯入 | 同上，待對碼 |
| jgb 外部 API | 個人現況資料（帳單/合約/電表） | per-user | jgb2 | ✅ **仍是主力**：`jgb2.query.*` 六域 → `JGBSystemAPI` → `services/jgb/transport.py`（替身 15 端點）或真 `external/v1` |

**仍然成立的鐵則**：機械判定用程式不用 LLM（狀態解碼由 `services/jgb/*.py` 的
`*_FACE_BUILDERS` 決定性算 facts，LLM 只照 facts 組話）；個資紅線（完整地址／經緯度不出口）；
金額只引存值禁重算。

---

## 已刪除的章節（前一版有、本版移除）

| 原章節 | 為什麼移除 |
|---|---|
| 一、系統做什麼（三類使用者、一個端點 `/api/v1/message`） | 端點已刪；且 `tenant` 在新線不存在，該表會讓人低估接回租客的成本 |
| 二、請求的一生（①–⑧ 路由順位） | 整條鏈已刪（意圖分類、SOP 檢索、表單觸發、錨點防呆、相關性把關全數不存在） |
| 三、對話面向 21＋售前（含領域對照表） | 🔴 **本版移除的主因**。現行是 16 個 face 的封閉枚舉（bills 5、contracts 5、accounts 2、repairs 2、iot 1、estates 1；查證：`grep -n "FACE_BUILDERS: dict" rag-orchestrator/services/jgb/contracts.py rag-orchestrator/services/jgb/bills.py rag-orchestrator/services/jgb/accounts.py rag-orchestrator/services/jgb/repairs.py rag-orchestrator/services/jgb/iot.py rag-orchestrator/services/jgb/estates.py` 逐表數鍵），由六張 `*_FACE_BUILDERS` 現算，名單見 `SYSTEM_ARCHITECTURE.md` §3。舊表的「狀態判斷」等 face **已不在任何註冊表**，且有測試釘死「永不註冊」 |
| 六、品質三層（unit 709／回測／稽核） | unit 現為 **3,629**；系統回測的執行器已刪（後台頁面與資料表仍在，零執行器） |
| 七、已知債總表 | 多數項目與舊鏈綁定；仍成立的部分（業者資料就緒、vendor 4 缺 `service_hotline`）請以 `.claude/DECISIONS.md` 與各 spec 為準 |

前一版全文見 `git show ee7aa933^:docs/architecture-overview.md`。

---

## ⛔ 不屬於本系統

> 📐 **邊界規則見 `docs/architecture/BOUNDARY.md`（唯一正本）。** 三個桶：本系統／呼叫端／外部相依；
> 一句話測試＝「把呼叫端整個換掉，這句話還成立嗎」。⛔ 不要在本檔另寫一份宣告。

部署事實（誰持 key、哪些停用、實際流量）查 `api_keys` 與 `usage_events`，⛔ 不寫進架構文。
