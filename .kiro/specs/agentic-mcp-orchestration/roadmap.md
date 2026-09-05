# agentic-mcp 路線圖（母 spec 與子 spec）

> 建立：2026-09-04。Kiro 無巢狀 spec；本檔是母 spec 的依賴波次表，子 spec 到波次才 `spec-init`，各自走 requirements→design→tasks。
> 母 spec 收案線＝不捏造、敏感五類零漏（requirements D2）。子 spec 各有自己的尺，⛔ 不共用收案線。

## 波次

| 波 | spec | 範圍 | 依賴 | 尺 | 狀態 |
|---|---|---|---|---|---|
| 0 | `agentic-mcp-orchestration`（母） | M0 單一謂詞＋不變量 18–21、M1 Runtime＋Verifier＋影子、M2 影子評估、M3 prospect 切換 | DSP-011；D1–D3 | 不捏造／敏感零漏／邊界題不硬答／p95 | design 1.1 收案審查中 |
| 1 | `help-center-source` | `help_center_pages` 匯入、`source_url`＋`content_sha256`、`citable` 人工核可、jgb2 觸發式同步（source-index §8） | D3 裁定 | 匯入完整性；引用來源可追 | 待 D3 |
| 2 | `agent-write-tools` | `jgb2.action.*`、`agent_confirmation_tokens` 表、修繕面向（tenant）；M4 | 母 M3 收案；D4 | 重放／TOCTOU／跨 session 零通過；獨立 security review | 未開 |
| 2 | `agent-pm-diagnosis` | 五張 builder 表全接 `jgb2.query.<domain>`、`face` enum、pm 身分切換；M5 | 母 M3 收案 | 五域 face 各一 e2e；pm 影子收案線另定 | 未開 |
| 3 | `agent-user-memory` | 跨 session 個人偏好與互動指標（`memory.get/set`，封閉 key、provenance 可引用、保存期限、使用者可清、跨業者隔離）；⛔ 不存 jgb2 事實、不做行為側寫 | 母 M3 收案；業者／租客 user_id | 回合數下降、留存；個資責任需求另列 | 業主 2026-09-04 提出，待裁 D6 |
| 2 | `agent-tenant-audience`（M4） | tenant 身分的 agent 對話（LINE 租客、語音來電者）：`AGENT_AUDIENCES` 加 tenant、tenant 目錄、`role_id=null` 組合的 e2e；含 LINE bot 承接 `handoff{channel,message}` | 母 M3 收案；D4 部分 | tenant 影子收案線另定 | r5 目標驗證後立案 2026-09-04 |
| 3 | `voice-turn-budget` | 語音回合：逐句驗證後放行（sentence-level gate）、首字 ≤1.5 s、工具 ≤2、可取消／打斷、handoff 語音話術；STT／TTS 在 JGB 端；走 REST SSE | 母 M3 收案；`agent-tenant-audience` | 首字延遲、打斷成功率 | r5 目標驗證後立案 2026-09-04 |
| 後 | `jgb2-contract-drift` | L2 契約漂移偵測進 CI、`bills.STATUS_LABELS` 除役改讀 `mapping`（source-index §10.2、缺口 7） | M3 有流量 | 漂移偵測誤報率 | 不開 |
| 後 | `retrieval-metadata-retire` | `instance_applicability`／`retrieval_representation` 除役；**reranker／`semantic-model` 容器除役**（業主 2026-09-05 問：prospect agent 路徑不用檢索；`kb.search` 於 M5 改目錄＋`kb.get` 後無消費者；若上 NLI 接地檢查則以同級容器換位） | agent 路徑證明不依賴；三身分皆切 agent 且回切窗口過 | 不變量 10／12／17 重定；部署少一服務 | 不開 |


## 外部驗收情境來源（業主 2026-09-05 提供，line-bot-platform）

四份文件（皆在 `/Users/lenny/jgb/line-bot-platform/docs/`，⛔ 本 repo 不複製、不修改）：`chatai-requests.md`（總表）、`chatai-repair-capture-spec.md`（線③拍照開修繕單，§6 12 案例）、`chatai-digest-followup-spec.md`（線⑤追問＋線④催繳草稿，§6 9 案例）、`chatai-wire-examples.md`（逐輪 body）。

| 事實 | 對本路線圖的意義 |
| --- | --- |
| 呼叫方走 `POST /rag-api/v1/message`＋`trigger_facet_key`，⛔ 不走 `/mcp` | 與母 design 1.4 一致（jgb2／LINE 走 REST，MCP 是 server-to-server 給其他 agent）；線③④⑤的接入需求（`facet_context`／`attachment_urls`／`form_completed`＋`repair{id,no}`／`session_expired`／`scope_exit`／`dunning_draft`）是**現有面向鏈**的改動，不在母 spec 範圍，需另立 spec（本 repo 目前查無：grep `facet_context|session_expired|scope_exit|dunning` 於 `.kiro/specs`、`routers/chat.py` 皆無命中；正對照 `trigger_facet_key` 有 8 處） |
| 使用者是代管業務（landlord／property_manager），不是 prospect | 這 21 個案例**不能**當 M2（prospect 影子）的樣本；它們是 `agent-write-tools`（線③：確認閘門、冪等、候選降級、不編描述、過期訊號）與 `agent-pm-diagnosis`（線⑤：bill／contract／meter 追問、範圍鎖定、查無資料誠實、id 不存在不猜）的**消費方定義驗收**，優先於我們自寫的劇本 |
| 線④催繳草稿：回模板＋`tone_level`，`late_count_1y` 決定等級、模板不得含數字、佔位符 ⊆ 8 鍵 | 封閉集合（三級語氣×有無滯納金條款＝6 個模板）⇒ 決定性程式選模板即可，⛔ 不該讓模型寫；建議獨立同步端點（呼叫方偏好選項二）。不進 agent 路線圖 |
| 呼叫方需要**機器可讀的回合狀態**（`form_completed`／`form_cancelled`／`session_expired`／`scope_exit`），不靠 `answer` 文字比對 | `agent.turn` 目前只回 `{answer, kind, handoff, quick_replies, trace_id}`；`agent-tenant-audience`／`agent-pm-diagnosis` 的 requirements 必須把「回合終態訊號」列為契約（母 design 升版項） |
| 30 分鐘會話過期後同 `session_id` 進來要可辨識（tombstone） | 母 spec 的 `form_sessions` 狀態同樣會撞到；列入 `agent-tenant-audience` 需求 |
| 延遲：呼叫方逾時 30 秒、追問 p95 待我方給數字 | 與 D2 的 p95 ≤12 s 一致方向；M2 報表的 p95 要能對外引用 |

## 規則
- 子 spec 的 requirements 必須引用母 design 的元件契約（`ToolRegistry`／`OutputVerifier`／`Identity`），⛔ 不得重定義。
- 任一子 spec 改到母 spec 契約 ⇒ 母 design 升版並重審。
- 每波開工前重看 `.claude/DECISIONS.md` 與 `jgb2-source-index.md` §9 同步狀態。
- jgb2 API 不足一律走 `jgb2-api-requests.md` 總帳：先登列、只在 `JGBSystemAPI` 邊界 mock、資料錄不編、報表標 `jgb_mock`、解除條件成立即拆（業主 2026-09-05）。
