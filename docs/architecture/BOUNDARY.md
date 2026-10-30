# 系統邊界正本——什麼算「本系統」，什麼不算

> 建立：2026-09-12　對象：`docs/architecture/**`、`docs/api/**` 的每一句敘述
> 讀者：要寫或要改架構文的人（含 AI 代理）。
> **本檔是邊界規則的唯一正本。** 其他架構文 ⛔ 不再各自重寫一份宣告，只指回這裡。

## 0. 為什麼要有這一檔

三份架構文各自寫了一段「外部串接不屬於本系統」，措辭都不同、涵蓋範圍也不同，結果是
**每遇到一個詞就要重新想一次它算哪邊**——`quick_replies` 算不算？`relay.jgbsmart.com`
算不算？於是同一份文件裡有的清掉、有的留著，看起來像「混在一起」。

真正缺的不是宣告，是**判準**與**歸屬表**。本檔提供這兩樣，並由不變量 40 機械檢查。

---

## 1. 判準：三個桶，不是兩個

以前只分「本系統／外部」，所以判不動。實際有**三**類，第三類才是混淆的來源：

| 桶 | 定義 | 進不進架構敘述 |
|---|---|---|
| **① 本系統** | `AgentRuntime` 與它的門面**自己定義、自己算、自己回出去**的東西 | ✅ 進，而且要寫完整 |
| **② 呼叫端（inbound）** | 誰呼叫對話入口、使用者在什麼畫面上打字、回出去的東西被畫成什麼 | ⛔ **不進**——換一個呼叫端，本系統一行都不用改 |
| **③ 外部相依（outbound）** | **本系統自己的程式**決定要去打的外部位址 | ✅ 進，但寫成**能力與限制**，⛔ 不寫成某個合作方的故事 |

### 一句話測試

> **把呼叫端整個換掉，這句話還成立嗎？**
> 成立 ⇒ 桶 ①／③，可以寫。
> 不成立 ⇒ 桶 ②，⛔ 不寫。

例：「回合結束時回出 `outcome.expects="image"`」——換呼叫端仍成立 ⇒ 寫。
「使用者會看到一個傳檔鍵」——換呼叫端就不一定 ⇒ ⛔ 不寫。

### 名字有外部血統 ≠ 屬於外部

**判歸屬看的是「誰定義它」，不是「名字像誰」。** `quick_replies` 這個名字來自某個通路
平台，但它是 `TurnResult` 的欄位、由本系統填、由本系統的契約保證存在
（`services/agent/turn_context.py::TurnResult`）——**它是桶 ①**。
把它當外部名詞清掉，會把本系統的對外契約清掉。⛔ 這是最容易犯的錯。

---

## 2. 歸屬表——易混詞逐個判定

| 詞／符號 | 桶 | 為什麼 | 查證 |
|---|---|---|---|
| `quick_replies` | ① | `TurnResult` 欄位，本系統填、本系統的七鍵契約之一 | `grep -n "quick_replies: list" rag-orchestrator/services/agent/turn_context.py` |
| `confirm_submit`／`confirm_edit`／`confirm_cancel` | ① | 本系統定義的穩定機器值，寫進 DB 也送給呼叫端 | `grep -n "QR_SUBMIT" rag-orchestrator/services/form_contract.py` |
| `select:<type>:<id>` | ① | 本系統產生、本系統在模型前解析 | `grep -n "select:(%s)" rag-orchestrator/services/agent/runtime.py` |
| `outcome.state` 封閉八值 | ① | DSP-043，**與畫面無關、任何呼叫端共用** | `grep -n "OUTCOME_STATES" rag-orchestrator/services/agent/turn_context.py` |
| `outcome.expects` 封閉六值 | ① | 同上；`image`／`file` 兩值是本系統告知「等的是檔案不是文字」 | `grep -n "OUTCOME_EXPECTS" rag-orchestrator/services/agent/turn_context.py` |
| `confirm_qr_labels` | ① | 面向配置鍵，落在本系統的 seed；只覆寫顯示文字、機器值不變 | `grep -n "confirm_qr_labels" rag-orchestrator/database/migrations/seed_repair_facet_config.sql` |
| `line_official` | ① | `PRESALES_HANDOFF_CHANNEL_DEFAULT` 的**值**，本系統寫進 `handoff.channel` | `grep -n "PRESALES_HANDOFF_CHANNEL_DEFAULT" rag-orchestrator/services/conversational_config.py` |
| `IMAGE_URL_ALLOWLIST`／`relay.jgbsmart.com` | ③ | 回滾模式 `AGENT_ATTACHMENT_INPUT=urls` 時**本系統自己下載照片**，白名單是本系統的安全邊界；預設模式收直傳，不抓網址 | `grep -n "DEFAULT_IMAGE_URL_ALLOWLIST" rag-orchestrator/services/agent/image_fetch.py` |
| `jgb2.query.*`／`jgb2.action.*` | ① | **工具名**，登記在本系統的 registry；名字指向資料來源，工具本身是本系統的 | `grep -rn "jgb2.query" rag-orchestrator/services/agent/tools/` |
| jgb2 Web、LINE OA demo、LIFF 畫面、回測工具、內部操作者的 Claude Code | ② | 都是**部署時接上來的消費者** | — |
| 誰持 key、哪些停用、實際流量 | ② | **部署事實**，查 `api_keys` 與 `usage_events`，⛔ 不寫進架構文（寫進來就會過期） | — |

### 桶 ② 的唯一例外：當它是「某個欄位為什麼存在」的證據

呼叫端的**實測現象**可以當欄位的立案理由寫在**程式註解**裡，因為那是不可從程式推導、
查證成本高的外部觀察。但**欄位定義本身 ⛔ 不得依賴任一呼叫端**。

現成例子：`turn_context.py` 的 `OUTCOME_EXPECTS` 註解記著「使用者被要求傳照片卻只看得到
打字列」這個實測，那是 `image`／`file` 兩值的立案理由；而 `OUTCOME_EXPECTS` 的定義本身
（封閉六值、`_ASK_TARGET_EXPECTS` 對映）一個呼叫端名字都沒有。**照這個形狀寫就對了。**

---

## 3. 外部情境的文件住在哪

桶 ② 的材料**不是要刪掉，是要住對地方**。它們有用，只是不在架構正本裡：

| 內容 | 正本位置 |
|---|---|
| jgb2 呼叫時的三種身分形狀（`mode`＋`target_user`＋`role_id`） | `docs/jgb2-chat-integration.md`（MAP：`#jgb2-chat-integration`） |
| 通路 bot 串接資訊單（端點、header、機器值、照片、限制、自測） | `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/line-bot-integration-sheet-20260908.md` |
| demo 帳本、劇本、情境缺口地圖 | 同上 `inputs/` 目錄 |
| 部署值、誰持 key、流量 | `docs/deployment-runbook.md`＋DB（`api_keys`／`usage_events`） |

`docs/api/mcp-facade.md` 是**串接契約**不是架構文：它的「讀者」段落點名哪些工程要接，
屬於桶 ② 但**寫在讀者聲明裡是對的**——讀者聲明不是架構敘述。

---

## 4. 這條規則怎麼被強制

`make audit` 不變量 40：`docs/architecture/**`＋`docs/api/**` 的敘述段落裡，
桶 ② 的字樣只允許出現在三種位置——**讀者／對象聲明**、**明確標為邊界宣告的段落**、
**引用外部文件路徑的連結**。其餘一律 FAIL 並指出行號。

自帶正對照組：檢查器有一份「已知必然會中」的樣本，它若沒中就是尺壞了，非 0 退出。

---

## 5. 三份架構文現在只留一行

`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`、`docs/architecture/SYSTEM_ARCHITECTURE.md`、
`docs/architecture-overview.md` 原本各自寫了一段措辭不同的宣告，已全部換成指回本檔的一行。
⛔ 不要再在別的架構文裡新寫一份宣告——兩份宣告只會各自演化，那正是這次要修的病。
