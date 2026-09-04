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
| 2 | `agent-tenant-audience` | tenant 身分的 agent 對話（LINE 租客、語音來電者）：`AGENT_AUDIENCES` 加 tenant、tenant 目錄、`role_id=null` 組合的 e2e；含 LINE bot 承接 `handoff{channel,message}` | 母 M3 收案；D4 部分 | tenant 影子收案線另定 | r5 目標驗證後立案 2026-09-04 |
| 3 | `voice-turn-budget` | 語音回合：逐句驗證後放行（sentence-level gate）、首字 ≤1.5 s、工具 ≤2、可取消／打斷、handoff 語音話術；STT／TTS 在 JGB 端；走 REST SSE | 母 M3 收案；`agent-tenant-audience` | 首字延遲、打斷成功率 | r5 目標驗證後立案 2026-09-04 |
| 後 | `jgb2-contract-drift` | L2 契約漂移偵測進 CI、`bills.STATUS_LABELS` 除役改讀 `mapping`（source-index §10.2、缺口 7） | M3 有流量 | 漂移偵測誤報率 | 不開 |
| 後 | `retrieval-metadata-retire` | `instance_applicability`／`retrieval_representation` 除役 | agent 路徑證明不依賴 | 不變量 10／12／17 重定 | 不開 |

## 規則
- 子 spec 的 requirements 必須引用母 design 的元件契約（`ToolRegistry`／`OutputVerifier`／`Identity`），⛔ 不得重定義。
- 任一子 spec 改到母 spec 契約 ⇒ 母 design 升版並重審。
- 每波開工前重看 `.claude/DECISIONS.md` 與 `jgb2-source-index.md` §9 同步狀態。
