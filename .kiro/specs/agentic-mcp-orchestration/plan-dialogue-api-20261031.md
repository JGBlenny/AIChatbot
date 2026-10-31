# 對話入口對齊片計畫：專用對話 API（DSP-131）

**日期**：2026-10-31　**狀態**：**業主 2026-10-31 核可**（AskUserQuestion 選項原文「核可，§9 照建議 (Recommended)」）；§2 規則與 §7 清單（含比對口徑 N、「## 廣度」）自此凍結，之後收窄要重新核可。收尾審查 r3 的修正未再審，收案 verifier 一併驗。
**業主裁定合併量測**（2026-10-31，AskUserQuestion 選項原文「合併成一輪 (Recommended)」）：本片在填欄結構化片的 X4 之前併回；X4 用兩片都含的映像、經新入口跑，同一輪當兩片的收案重量（取代原排的獨立 X-E1）。改前＝填欄片 X1r（off、經 `/mcp`、不含本片程式）。代價：改前改後之差含兩片，退步時先跑 X-E2、仍分不清就撤回本片再量（§5.4、§8）。
**工作線**：站內幫手（`assistant-agent-demo`）。**本檔＝規則與凍結驗收清單的正本**（§2 規則在前、§7 清單在後，核可時一起凍結）。

## 0. 目標正本定位

- 架構正本：`docs/architecture/TARGET_ARCHITECTURE.md`。本片碰：§0 第 1 點（`/mcp` 不是最終對話入口）、§4 目標架構圖「呼叫端 → 對話 API（HTTP；取上傳票也走這裡）→ 對話入口」、§5 第 1 點（呼叫端只走對話 API，不碰 MCP）與「身分由程式每次注入；新入口要處理 `Identity.entry` 與命名空間身分」、§8 差距表「對話入口」「上傳票」「測試底座」「MCP 門面」四列、§9「對話入口」條。
  - 「測試底座」列（目標：改前改後走同一入口）：本片把模擬客人與回測的驅動加上新入口選項，收案重量改走新入口（§5.2 第 8 項）；「工具搬走要有 MCP 替身」不在本片（隨 JGB 工具移交片）。
  - 「MCP 門面」列（目標：對話入口搬出去）：本片做到協定、路由、計量三層分開（新入口不經 MCP 協定、不 import `mcp.*`、計量分得出）；入口核心 `_make_invoke` 仍在 `mcp_facade.py`，模組搬家不在本片（DA-R2 讀法、§9 第 3 題）。
- 分工表（§2）與原則 P0～P8：**不碰**。換入口不改分工（§0 第 3 點）；`_agent_turn` 內部一行不改。
- 工作線目標正本：`.kiro/specs/agentic-mcp-orchestration/architecture-target-20261018.md` §4「對話入口對齊」列（系統定位，非 M0 缺陷）。
- 已知偏離（目標正本 §3.1、§3.2）：**不碰任何一條**。本片不是過渡修正，也不是哪條偏離的接手片。
- 決策：DSP-130（目標架構）、DSP-131（現在做、加法、`/mcp` 留到呼叫端改完）。
- **風險觸發**：有。資安與信任（金鑰、身分、命名空間、限流與額度）、跨元件驗收（JGB `AgentTurnClient`、line-bot 客戶端將改接）。⇒ 先 `security-reviewer`，再 fresh `plan-verifier`，業主核可後由 `security-executor` 實作，收案前 fresh `verifier`。
- 審查紀錄：/Users/chenqinghuang/jgb-archive/arch-step3-20261018/entry-align/plan-verifier-r3.md（收尾審查 r3，REVISE，修了、未再審，§6.2）；同目錄另有 security-review-r1.md（處置 §6.1）、plan-verifier-r1.md、plan-verifier-r2.md（REVISE，處置 §6.2）。
- 省略審查：業主原話「核可，§9 照建議 (Recommended)」（2026-10-31 AskUserQuestion；該選項說明「最後 3 條修正沒再審，要等收案驗證時才一起驗」，業主沒選「再審一輪才核可」）。省略的只有收尾審查 r3 那 3 條修正的再審；資安審查、plan-verifier r1～r3 都已跑，收案 verifier 照排。

## 1. 先答三題、終點指標、斷路器

- **廣度**：本片新增的驗收項全部是機制項（DA1～DA11，DSP-131 取捨：「上線當天客人看到的行為不變」）。⛔ 拿本片宣稱使用者成效。使用者層只有終點表的防退步重量（既有題組照舊，見「## 廣度」）。
- **輸入誰寫**：機制項由實作者寫測試；收案 verifier 另寫 ≥10 個新請求（含錯誤形狀）在兩個入口實打。終點重量用既有題組（出題代理撰寫、模擬客人自由講），不新寫。
- **跟改前比**：`/mcp` 的行為改前改後要相同（DA8）；新入口與 `/mcp` 同輸入決定性比對（DA2）；終點表改前＝填欄結構化片 X1r（off、經 `/mcp`、不含本片程式的映像），改後＝兩片都含的映像經新入口重量（填欄片 X4＝本片 §8 X-E1，業主 2026-10-31 裁定合併）。入口不同的處理見 §9 第 2 題。

**終點指標**：
- **目標文件**：目標正本 §1「每片怎樣算完成」的全部量法，加 DSP-115 第 3 點的收案門檻「錯筆卡、錯筆寫入」。量法清單照最近一份點名同一目標文件的計畫（`plan-fill-structured-20261030.md` §1 終點表），去掉該片自己凍結清單的列（定題 P、FS 新輸入：是該片 A5、A7 的量法，不是目標文件的量法），補上一片收案報告有的 T4、道謝後轉真人兩列。
- **受測物與現值**：本片的改前受測物＝填欄結構化片 X1r 的映像（實作後、開關 off、不含本片程式，經 `/mcp`）。X1r 2026-10-31 量測中，量完填入下表，填入時寫明 commit／md5 與檔案路徑。本片程式在 X1r 全部跑完後、X4 之前才併進主工作樹（§5.4），所以現值一定在本片任何程式進受測物之前量完。核可時未量的處理見 §9 第 1 題。
- 下表「參考值」是填欄結構化片 X1（舊正本、`fad1f936`）的值，全域「終點指標」第 2 條不算現值。

| 量法 | 門檻 | 參考值（不是現值） | 現值 | 本片預期 | 前兩片實際變化 |
|---|---|---|---|---|---|
| OV Intercom 解決 | 改後 ≥ 改前 | 86/96（`fill3/x1/x1_summary.md`） | 未量（填欄結構化 X4） | 0 | 填欄只填答覆：未量 OV；填欄擴及：未逐片量（`plan-fill-structured-20261030.md` §1） |
| OV 嚴格 | 改後 ≥ 改前 | 86/96（`fill3/x1/blind_ov/res/`） | 未量 | 0 | 同上 |
| OV 錯筆卡（雙胞胎算／不算） | 本片 0 新增 | 5／1（`fill3/x1/x1_summary.md`） | 未量 | 0 | 同上 |
| OV 錯筆寫入（雙胞胎算／不算） | 0 新增 | 4／0（`ov1030b_precheck.jsonl`） | 未量 | 0 | 同上 |
| M0 harness 現在 W／K／A／全部 | 每列改後 ≥ 改前 | 20/20、20/20、12/12、52/52（`fill3/x1/m0b_score.json`） | 未量 | 每列 0 | 填欄只填答覆：全部 46→49、W 14→18、K 20→19（`fill/report-fill-close.md` 終點節）；填欄擴及：全部 49→51、K 19→20、W 18→19（`plan-fill-wide-20261028.md` §11「X7 M0 結果」） |
| M0 T4 現在 W／K／A／全部 | 每列改後 ≥ 改前 | 未量（X1 未分列） | 未量（由同一 M0 紀錄以 `overall/p5_score.py` 算，不另跑） | 每列 0 | 填欄只填答覆：全部 48→50；填欄擴及：同節表未分列 T4 |
| M0 盲判嚴格 A／K／W／W-D／全部 | 每列改後 ≥ 改前 | A 12/12、K 12/20、W 20/20、全部 44/52（`fill3/x1/blind_m0/res/tally.json`） | 未量 | 每列 0 | 填欄只填答覆：全部 45→46、W-D 9→10；填欄擴及：全部 46→46、K 14→15、W-D 10→9 |
| 道謝後轉真人（M0 場數） | 0 | 未分列 | 未量（同一 M0 紀錄） | 0 | 填欄只填答覆：0→0；填欄擴及：同節表未分列 |
| M0 錯筆卡 | 0 新增 | 2 張／1 場（`fill3/x1/m0b_judgement.md`） | 未量 | 0 | 兩片都未分列 M0 錯筆卡（前片量的是 X9 同批 17 場，見下一列） |
| X9 同批 17 場錯筆卡（單欄追問回合） | 0 | 0/17（填欄擴及 §11 F4） | 未量（填欄結構化 X5 on） | 0 | 填欄只填答覆：11/17→0/17，−11（`fill/report-fill-close.md` 終點節）；填欄擴及：0（§11 F4「X9 0/17 沒退步」） |
| 既有回歸 E2a、E 片、F12 | 每組 ≥ 改前 | 見 `plan-fill-structured-20261030.md` §1「既有回歸」列（`fill3/x5-off/`） | 未量（填欄結構化 X5 on） | 0 | 填欄只填答覆：E2a 0；E 片 E1 47→48（+1）、E2 63→64（+1）、E3 原卡 4→5（+1）、E4 0→0、E14 15→15；F12 F3″ 34→35（+1）、F8 錯筆卡 1→0（`plan-fill-wide-20261028.md` §0 終點表 E 片、F12 兩列，引 `fill/report-fill-close.md` FA4、FA4b 列）。填欄擴及：E2a 0（r1 T 組 0/2，修復輪後回 2/2）；F3″ 37→36（−1，§11「X8 前查證 FW6 F3″」）；E 片、F8 未重跑（§11「不跑：E 片全量、F8」） |
| 單元測試 | 測試全過（字面） | 9 failed、7459 passed（`fill3/x1r/x6_unit.txt`，2026-10-31，HEAD `74e2a356` 加未提交改動） | 同參考值（現行程式）；填欄片交件後以其 `unit-after-impl.txt` 為準 | 9 筆既有失敗不變、新測試全過；仍**未達字面** | 0、0 |
| `make audit` | PASS | 紅燈只在不變量 36、`.claude/worktrees/` 舊代理副本（`fill3/x1r/x6_audit.txt`） | 同左；填欄片交件後以其 `invariants-after-impl.txt` 為準 | PASS 或與改前相同的紅燈集合 | PASS、PASS |

- **預期全部 0 的依據**：本片只換入口、`_agent_turn` 內部一行不改（§0），業主說「換入口的好處目前沒有數據 不換也沒有好處啊」（DSP-131），本片不宣稱成效；這些列只防退步。出處：DSP-131 取捨「換入口對使用者的效果沒有數據，上線當天客人看到的行為不變」；目標正本 §4「對話入口對齊」列鎖定缺陷欄「—（架構對齊，非 M0 缺陷）」。
- **前兩片**＝點名目標正本為目標文件、有改後量測的最近兩片：填欄只填答覆（DSP-118，已收案）、填欄擴及（DSP-119，**未收案**：未完成的部分由填欄結構化片取代，`plan-fill-structured-20261030.md` 檔首；變化取自其 §11 修復輪量測）。填欄結構化片收案後是本片的前一片，其實際變化在本片收案報告補進。
- **斷路器**：前兩片 M0 harness 全部 +3、+2，不全為 0，**不觸發**。本片收案時預期 0，會計入下一片的斷路器計數（本片是業主定方向的前提片，照計 0）。
- 不設 token 上限（2026-10-18）；收案報告列實際子代理用量。

## 2. 業主原話與規則（判定一律依規則）

業主原話（逐字）：
- DSP-130：「哪站內幫手就不該從 /mcp 入口進入 因為他使用的是對話服務」「對話服務 跟 mcp 調用 應該分兩個區塊吧 ?」
- DSP-131：「換入口的好處目前沒有數據 不換也沒有好處啊」「越放只會成本越高」「就是目前本就是要對其正確架構」「我不要有誤導資訊讓你不去對其」
- 2026-10-31：「1，架構也一起做」「你統一更新文件 我請 JGB 調整 且你不需要在意對方上 master 時程 你處理好你的部分」

| ID | 可檢查的條件 | 來源 | 讀法註記 |
|---|---|---|---|
| DA-R1 | 呼叫端可以不經 MCP 協定完成一回合對話：一個 HTTP POST 帶訊息，回一份結構化結果；不需要 `initialize`、`Mcp-Session-Id`、JSON-RPC。 | 「就不該從 /mcp 入口進入 因為他使用的是對話服務」 | — |
| DA-R2 | 取上傳票也走對話 API，不經 MCP；對話入口與 MCP 門面在協定、路由、計量三層分開。 | 「對話服務 跟 mcp 調用 應該分兩個區塊」；TARGET §4、§5、§8「MCP 門面」列 | 主會話讀法：「分兩個區塊」本片做到協定（不經 MCP）、路由（新路由檔不 import `mcp.*`）、計量（`channel` 分得出）三層；入口核心 `_make_invoke` 留在 `mcp_facade.py`，程式模組搬家不在本片。這是擇一讀法，交業主 §9 第 3 題。 |
| DA-R3 | 新入口的金鑰、身分、vendor 範圍、Origin、命名空間、每小時上限、額度，與 `/mcp` 同等或更嚴；⛔ 任何一道比 `/mcp` 鬆。 | DSP-131 取捨「碰身分、金鑰與計量，屬資安範圍」 | 主會話讀法：「同等」＝同一組函式（`resolve_call`、`_agent_turn_preflight`、`quota_check`），不另寫一套。 |
| DA-R4 | 兩個入口的流量在 `usage_events` 分得出來；新入口每呼叫恰一列（同不變量 31）。 | DSP-131 依據「入口計畫要讓新入口也有量測」 | — |
| DA-R5 | 加法：`/mcp` 對現有呼叫端的行為不變（回應、錯誤、計量值）；本片不關 `/mcp`；終點表各列預期 0、只防退步。 | DSP-131 決定第 3 點（主會話提議，等級 C，業主採入決定）；「換入口的好處目前沒有數據 不換也沒有好處啊」（本片不宣稱成效的依據） | 「關 `/mcp`」是另一件事，等 JGB、line-bot 都改完才做（非目標）。 |
| DA-R6 | 現行文件寫出新入口；⛔ 留「站內幫手只能／應該走 `/mcp`」的現行陳述。 | 「我不要有誤導資訊讓你不去對其」 | 範圍：DA9 的 grep（§7）在 `docs/`、`.claude/MAP.md`、`.kiro/specs/agentic-mcp-orchestration/` 現行文件命中的全部檔；已知含接口 A、`docs/api/conversational-api.md`（「外部串接只能走 `/mcp` 門面」）、`docs/api/mcp-facade.md`、`.claude/MAP.md`、現況架構文件、JGB 規格草稿 L1／L2。紀錄（報告、凍結清單、決策）不改寫。 |
| DA-R7 | 本片在第 4 步切換正式機之前完成，與填欄結構化片同時進行。 | 「就是目前本就是要對其正確架構」「越放只會成本越高」；DSP-131 決定第 2 點（主會話讀法）；2026-10-31「1，架構也一起做」（與填欄片同時開工，排法見 §5.4） | JGB 何時上 master 不是本片的條件（業主 2026-10-31，見 DA-R8）。 |
| DA-R9 | 收案的終點重量走新入口：模擬客人與回測驅動可選新入口，本片收案量測用它。 | 目標正本 §1「現況是 `/mcp`，對話入口對齊後改打專用對話 API」（上位驗收方式，業主核可的目標正本）；DSP-131 風險「量測全來自 `/mcp`，產品卻走新路由；入口計畫要讓新入口也有量測」 | 不是業主在本片的原話，是上位驗收方式的照做項（全域「驗收廣度」第 6 條）。改前改後入口不同的處理交 §9 第 2 題。 |
| DA-R8 | 本系統這邊做完：新入口、測試、文件（含給 JGB 的接口文件）一次統一更新；呼叫端改接由業主請 JGB 調整，本片不等、不追 JGB 時程。 | 2026-10-31「你統一更新文件 我請 JGB 調整 且你不需要在意對方上 master 時程 你處理好你的部分」 | 給 JGB 的接口文件在計畫核可（契約凍結）後才寫，避免 JGB 照會變的草稿改。 |

## 3. 目標形態（業界與第一原理，不看自家現況）

原文存 `~/jgb-archive/arch-step3-20261018/arch-review-20261030/sources/`（2026-10-30 擷取，檔頭有 URL、FETCHED）。只限所查幾家，不代表全業界。

1. **一回合＝一次 HTTP POST，對話以 session 識別續接**：
   - Dialogflow CX `df-detectintent.txt`：「POST https://{endpoint}/v3/{session=projects/*/locations/*/agents/*/sessions/*}:detectIntent」
   - Amazon Lex V2 `lex-recognizetext.txt`：「POST /bots/botId/botAliases/botAliasId/botLocales/localeId/sessions/sessionId/text HTTP/1.1」
   - Amazon Bedrock Agents `bedrock-invokeagent.txt`：「POST /agents/agentId/agentAliases/agentAliasId/sessions/sessionId/text HTTP/1.1」、「To continue the same conversation with an agent, use the same sessionId value in the request.」
2. **錯誤用 HTTP 狀態碼分類**：Lex `lex-recognizetext.txt`「Errors」節：「AccessDeniedException HTTP Status Code: 403」「ConflictException HTTP Status Code: 409」「DependencyFailedException HTTP Status Code: 424」「InternalServerException HTTP Status Code: 500」「ResourceNotFoundException HTTP Status Code: 404」「ThrottlingException HTTP Status Code: 429」「ValidationException HTTP Status Code: 400」。Bedrock `InvokeAgent` 的 Errors 節同型（403、502、409、424、500、404、429、400）。
3. **串流是另一支或另一個選項**：Dialogflow CX 另有 `serverStreamingDetectIntent`（`df-detectintent.txt`）；Bedrock 在 `InvokeAgent` 帶 `streamingConfigurations`。本系統逐字串流要先做逐句 Verifier（TARGET §5），不在本片。
4. **第一原理**（查無業界對應，推導）：同一個對話核心有兩個入口時，入口只做「驗證 → 轉呼叫 → 對應錯誤」，其餘共用同一段程式，否則兩邊防護會漂移；兩入口要能用量測分開，否則無法知道呼叫端搬完沒有。

## 4. 差距（現況，2026-10-31 對碼；可重跑）

| 項目 | 現況 | 查證 |
|---|---|---|
| 對話入口 | 只有 `/mcp`（MCP streamable HTTP），`agent.turn` 以 `tools/call` 呼叫；JGB 每回合 `initialize`→`notifications/initialized`→`tools/call`→同步 `DELETE` | `grep -n 'Mount("/mcp"' rag-orchestrator/app.py`；`attack-entry-early.md` §0 |
| 入口核心 | `_make_invoke(registry, deps)` 回 `_invoke(name, ctx, args)`，對 ctx 只用 `.headers`；三道檢查＋計量＋額度＋preflight＋命名空間都在裡面 | `grep -n "def _make_invoke\|getattr(ctx, \"headers\"" rag-orchestrator/services/agent/mcp_facade.py` |
| 錯誤 | `_invoke` 失敗 raise MCP SDK 的 `ToolError`（訊息＝業務代碼字串），沒有 HTTP 狀態碼；請求層 `McpRequestError` 已帶 401／403／400 | `grep -n "class McpRequestError\|def _tool_error_cls" rag-orchestrator/services/agent/mcp_facade.py` |
| 計量 | `_metering_fields` 寫死 `"channel": "mcp"`；`_stamp_metering_context` 寫死 `processing_path = f"mcp:{name}"` | `grep -n '"channel": "mcp"\|processing_path = f"mcp:' rag-orchestrator/services/agent/mcp_facade.py` |
| `Identity.entry` | `parse_identity` 寫死 `entry="mcp"`（註解：只被 `/mcp` 請求層呼叫）；確認兌現與寫入工具可見性看 `entry == "mcp"`：`runtime.py` 3 處、`tools/registry.py` `specs_for` | `git grep -nE 'entry *(!=\|==) *"mcp"' -- rag-orchestrator/services` |
| 服務閘 | `GATED_PREFIXES = ("/mcp", "/api/v1/agent")`，`/api/v1/agent/*` 已過閘 | `grep -n "GATED_PREFIXES =" rag-orchestrator/services/agent/mcp_facade.py` |
| 稽核 | 不變量 28（金鑰無條件）、31（每呼叫一列 `usage_events`）只認 `/mcp` | `grep -n "def check_28\|def check_31" scripts/audit/checks/agent_boundary.py` |
| 呼叫端 | JGB `AgentTurnClient`（只在 staging `86d8feb086`，master `442ad608b8` 沒有）；line-bot `main` 的 `packages/server/src/mcp/agent-client.ts`（TS SDK `^1.30.0`，每位使用者一條長連線） | `~/jgb-archive/arch-step3-20261018/entry-align/prereq-20261031.md` |
| SDK | `mcp==2.1.1` 同時支援握手式（2024-11-05～2025-11-25）與 2026-07-28 無 session 版；沒有「升 SDK 逼換入口」的時間壓力 | 同上 §3 |

## 5. 路徑

### 5.1 介面（給 JGB、line-bot 的新契約）

網址分兩層（資安審查 F1：nginx `location /rag-api/` 會 `rewrite ^/rag-api/(.*)$ /api/$1`，`AICHATBOT_BASE`＝`…/rag-api`）：

| | 對外（給 JGB、line-bot，經 nginx） | 後端（容器內路由） |
|---|---|---|
| 對話一回合 | `POST {AICHATBOT_BASE}/v1/agent/turn` | `POST /api/v1/agent/turn` |
| 取上傳票 | `POST {AICHATBOT_BASE}/v1/agent/upload-ticket` | `POST /api/v1/agent/upload-ticket` |

```
headers：X-API-Key（同 /mcp 那把）、X-JGB-Identity（同 /mcp 的 JSON，含 session_id）、Content-Type: application/json
turn body：JSON object，原樣交 agent.turn（現行 schema：message、upload_ids、attachment_purpose、context；image_urls、file_urls 帶了回 INVALID_INPUT）
upload-ticket body：JSON object，原樣交 agent.upload_ticket（attachment_purpose）
200：工具結果 dict 原樣（agent.turn 為 AgentTurnOutput）
非 200：{"code": "<業務代碼>", "detail"?: "<現行 _input_detail 白名單內的字>"}；500 回固定 body，⛔ 帶例外文字
```

- 對話鍵（`state_store.py` `NAMESPACE = "mcp"`）與入口無關：同一組金鑰＋vendor＋`session_id` 在兩個入口間可續用同一段對話與確認卡，`_session_owner_matches` 照常比對 `(user_id, role_id)`。這是刻意的：同一主體換入口不斷線（資安審查確認不是越權）。

- **偏離業界（session 放 header 不放路徑）**：理由——`session_id` 依接口 A §5 是綁 `(user_id, role_id)` 的 128 bit 亂數，放進網址會進 nginx access log 與代理紀錄；現行契約已放 `X-JGB-Identity`，JGB 不必重組身分。代價：不像 Lex／Bedrock 能從網址看出 session。
- **錯誤碼對 HTTP 狀態碼**（草案，實作時逐碼列出 `_invoke` 對這兩支工具實際會 raise 的全部代碼，表外代碼一律 500）：

| 代碼 | HTTP | 依據（§3 第 2 點同型） |
|---|---|---|
| `IDENTITY_MALFORMED`、`IDENTITY_MISSING_VENDOR_ID`、`IDENTITY_MISSING_SESSION_ID`、`IDENTITY_MISSING_USER_ID` | 400 | 現行 `McpRequestError` |
| `API_KEY_REQUIRED` | 401 | 同上 |
| `ORIGIN_NOT_ALLOWED`、`VENDOR_UNKNOWN`、`VENDOR_NOT_IN_KEY_SCOPE` | 403 | 同上 |
| `INVALID_INPUT` | 400 | ValidationException |
| `NO_MATCH` | 404 | ResourceNotFoundException |
| `RATE_LIMITED`、`QUOTA_EXCEEDED` | 429 | ThrottlingException |
| `AGENT_UNAVAILABLE`、`METERING_UNAVAILABLE` | 503 | 查無業界對應（所存 Lex、Bedrock 原文只有 400、403、404、409、424、429、500、502）。第一原理推導：本系統暫時不能服務（模型或計量庫不可用），請求本身沒錯，稍後可再試；與 500「程式出錯」分開，呼叫端才能決定要不要稍後重試（確認回合除外，見下） |
| `TOOL_TIMEOUT` | 504 | 查無業界對應（同上）。第一原理推導：本系統等下游逾時，回合結果**未知**（確認回合可能已寫入）；與 503「確定沒處理」分開，呼叫端才不會把「可能已寫入」當成「沒處理」而重送 |
| `CONFIRMATION_REQUIRED` | 409 | ConflictException |
| 其他／未預期例外 | 500 | InternalServerException |

  確認回合逾時的語意不變：504 ＝結果未知，呼叫端 ⛔ 自動重送（接口 A F2-6）。

### 5.2 程式（範圍項目 → 服務的規則）

| # | 改動 | 服務 |
|---|---|---|
| 1 | 新檔 `rag-orchestrator/routers/agent_dialogue.py`：兩個 handler，`include_in_schema=False`；收原始 JSON（不是 object ⇒ 400 `INVALID_INPUT`；⛔ pydantic body 模型——會走 FastAPI 422、回顯 `input`、不經 `_invoke`、不寫 `usage_events`，F5），其餘原樣交 `_invoke`（由 `registry.call` 剝身分鍵、驗 `additionalProperties`）；用 shim ctx（只有 `.headers`）。⛔ import `mcp.*`。`app.py` 加一行 `include_router`，`_invoke` 由 `_mcp_registry`、`_mcp_deps` 建——**必須同一份 registry**（每分鐘上限掛在 registry 實例上；⛔ 照抄 `routers/agent.py` 自建 registry 的寫法）。 | DA-R1、DA-R2、DA-R3 |
| 2 | 門面錯誤結構化（F5）：`_invoke` 改 raise 門面自己的錯誤（帶 `code`、`status`、`detail`），`/mcp` 的包裝層把它轉成現行 `ToolError` 字串（`f"{message}: {detail}"`，逐字不變）；新路由直接讀 `code`／`detail` 對照 §5.1。請求層 `McpRequestError` 的 status 一路帶到新路由。 | DA-R1、DA-R5 |
| 3 | 計量參數化：`_make_invoke(registry, deps, *, entry)`（必填），決定 `channel`、`processing_path` 前綴、`answer_source`，含 `_invoke` 內兩處 `um.set_path(f"mcp:…")`（F2）。`/mcp` 明寫 `entry="mcp"`，值不變；新入口 `channel="dialogue_api"`、`processing_path="api:<tool>"`（`usage_events.channel` 為 `VARCHAR(20)`、無 CHECK，`add_usage_events.sql`）。`McpServiceGate` 對新兩條路徑的被擋嘗試也呼叫 `note_mcp_traffic`（F3）。 | DA-R4、DA-R5 |
| 4 | `Identity.entry`（F4）：`identity.py` 的 `EntryChannel` 加 `"dialogue"`，新增 `BACKEND_ENTRIES = frozenset({"mcp", "dialogue"})` 與 `is_backend_entry()`；`DEFAULT_ENTRY_CHANNEL` 維持 `"rest"`。`parse_identity`、`resolve_call` 的 `entry` 改**必填關鍵字**、不在 `BACKEND_ENTRIES` 就 raise；既有呼叫點（`/mcp`、`routers/agent.py` `_require_identity`、`agent_openapi`、`_ToolListFilter`、`McpServiceGate.__call__` 的 `resolve_call(headers, self._get_pool(), self._allowed_origins)`）明寫 `"mcp"`，行為不變；實作時以 `git grep -n "parse_identity(\|resolve_call(" -- rag-orchestrator` 列全部呼叫點，清單外的一律補上並寫進收案報告。`runtime.py` 3 處與 `tools/registry.py` `specs_for` 的 `entry == "mcp"`／`!= "mcp"` 改呼叫 `is_backend_entry()`；其他建構點照舊落 `"rest"`。`parse_identity` 註解「只被 `/mcp` 呼叫」改正。 | DA-R3 |
| 5 | 稽核（F9）：不變量 28 的 `facade_paths` 加新路由檔，並查新路由路徑都在 `GATED_PREFIXES` 內、不在豁免；不變量 31 由新測試釘「新入口每呼叫恰一列」；新增兩條：新路由不 import `mcp.`；`identity.py` 以外（範圍 `rag-orchestrator/services/`、`routers/`、`app.py`，不含 tests——`test_mcp_only_write_tools_req.py` 有合法的 `.entry == "mcp"` 斷言）不得有 `entry ==／!= "mcp"` 字面比較，也不得有 `!= "rest"` 這類對未知值放行的寫法。 | DA-R1、DA-R3、DA-R4 |
| 6 | 測試：新路由 HTTP 層（§5.1 每個代碼、各安全閘、非 object body、未預期例外 500 固定 body）；兩入口等價（同輸入、同 fake runtime；預期差異只有 channel／processing_path／answer_source，與額度用盡時 `/mcp` 由 `usage_metering_middleware` 先擋不寫列、新入口由 `quota_check` 寫一列 blocked——F6）；`/mcp` 既有 3 個斷言 `channel == "mcp"` 的測試與 `ToolError` 訊息字串不改。 | DA-R3、DA-R4、DA-R5 |
| 7 | 文件（主會話，核可後契約凍結即寫、實作收案時一次對齊）：`TARGET_ARCHITECTURE.md` §8「對話入口」「上傳票」兩列的現況欄；接口 A `docs/api/jgb2-web-assistant-integration.md` 加新入口章節（對外網址用 §5.1 對外欄）並把 §3 改成「建議走對話 API；`/mcp` 過渡」；`jgb-spec-structured-card-draft-20261019.md` L1、L2 填端點與欄位；`docs/api/conversational-api.md` 檔首「專用對話 API 上線前，外部串接只能走 `/mcp` 門面」「目前沒有給外部專案的公開 REST 端點」兩句改成現況；`docs/api/mcp-facade.md` 計量辨識欄位、`docs/deployment-runbook.md` 監控查詢（F8；後者屬別窗檔，只交裁決、不自改）；`.claude/MAP.md`；`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`（現況）入口段；新 DSP 記 `entry`、狀態碼對照、session 放 header、跨入口續用對話的取捨。 | DA-R6、DA-R8 |
| 8 | 量測底座加新入口（repo 外，`~/jgb-archive`）：`assistant-demo-20261014/mcp_client.py`、`run_s5.py` 的 `turn`、`eval-harness/harness/runner.py`、`chat.py` 中打 `/mcp` 的地方，加一個入口選項（環境變數 `HARNESS_ENTRY`，預設 `mcp`＝現行逐字不變；`dialogue` ⇒ 單次 `POST /api/v1/agent/turn`，把 200 body 轉成底座現在讀的同一形狀，錯誤 body 照記）；收案用的派工單、`pickchat.py` 經同一選項。⛔ 在填欄片量測期間改動這些檔（§5.4）。 | DA-R9 |

### 5.3 不在本片（非目標）

- 關閉 `/mcp`：等 JGB、line-bot 都改完（DA-R5）；改名 `note_mcp_traffic`／`premise_stats` 計數（P3，記後補）。
- 呼叫端改接：JGB `AgentTurnClient`（JGB 的事，只寫進給 JGB 的規格）；line-bot `agent-client.ts`（業主另一個 repo，另排）。
- 逐字串流（要先做逐句 Verifier，TARGET §5）。
- 測試底座的「工具搬走要有 MCP 替身」（TARGET §8 測試底座列後半）：隨 JGB 工具移交片。
- 入口核心搬出 `mcp_facade.py`（TARGET §8「MCP 門面」列的模組層）：本片不做，業主裁定見 §9 第 3 題。

### 5.4 執行順序、獨佔與映像邊界

- **寫手隔離**：本片 security-executor 用 `isolation: "worktree"`，從派工當下的 HEAD 開分支寫 5.2 第 1～6 項（`runtime.py` 除外；第 7 項文件由主會話寫，第 8 項併回後才做）；主工作樹由填欄結構化片的 security-executor 獨佔，本片寫手不碰主工作樹。
- **併回時點**（業主 2026-10-31 裁定合併量測）：填欄結構化片 X1r（off）全部跑完之後、X4 之前，把 worktree 併回主工作樹，同一次補上 `runtime.py` 3 處判斷式（5.2 第 4 項）與 `app.py` 的 `include_router`，再跑單元全套與 `make audit`；以 on 重建常駐容器後跑 DA1～DA10 實打。任一項不過 ⇒ 撤回本片（§5.5），填欄片照原排經 `/mcp` 跑 X4，本片改回獨立 X-E1。
- **映像邊界**：填欄片的 off 量測（X1r）映像**不含**本片任何程式；X4 映像**兩片都含**，`AGENT_FILL_STRUCTURED=on`，經新入口量，同時是本片收案重量（§8 X-E1）。各映像的 commit／md5 寫進收案報告。
- **量測底座（5.2 第 8 項）**：X1r 跑完、併回之後才改（X1r 期間⛔ 改）；改完以預設 `mcp` 跑 DA2 的 2 輪，照比對口徑 N（§7 表下）與改前紀錄 0 差異，證明預設路徑沒變（DA11），通過才以 `HARNESS_ENTRY=dialogue` 跑 X4。
- worktree 會碰的 repo 檔（`mcp_facade.py`、`identity.py`、`tools/registry.py`、`app.py`、`routers/`、`scripts/audit/checks/agent_boundary.py`、新測試）在 2026-10-31 git status 都沒有未提交改動，從 HEAD 開分支不會漏掉主工作樹的改動；派工前再查一次，有變就停。
- **不留半套（F7）**：`include_router` 與 `runtime.py` 3 處判斷式同一次落地。否則 `entry="dialogue"` 看得到寫入工具、確認鈕卻靜默失效。
- 本片一位寫手；文件（5.2 第 7 項）由主會話在主工作樹寫，碰的檔與填欄片不重疊（`deployment-runbook.md` 是別窗檔，只交裁決）。`jgb-spec-structured-card-draft-20261019.md` 目前的未提交改動是本 session 主會話寫的 L4 段，本片改 L1、L2，同一位寫手。

### 5.5 併回與回復

業主規定 commit 由業主下令，所以 worktree 的成果不以 commit 併回，改用 patch 檔：
- **保存**：寫手交件時在 worktree 跑 `git add -N <新檔>` 後 `git diff --binary HEAD > ~/jgb-archive/arch-step3-20261018/entry-align/impl/entry-worktree.patch`；`runtime.py` 3 處判斷式與 `include_router` 另存 `entry-runtime.patch`（併回時才寫，見 §5.4）。兩檔各記 sha256。
- **併回**：主工作樹先記本片會碰的每個檔的 md5（存 `impl/pre-apply-md5.txt`；`runtime.py` 此時含填欄片的改動，照記），`git apply --check` 通過才 `git apply`；不過 ⇒ 停，不手動合。
- **撤回**（收案驗收任一項失敗且業主決定撤，或填欄片需要回到不含本片的狀態）：`git apply -R entry-runtime.patch`，再 `git apply -R entry-worktree.patch`；新檔隨反向套用移除。只想先關新入口、保留其餘：只反向套用 `entry-runtime.patch` 中 `app.py` 的 `include_router` 那一段不夠——`/mcp` 共用路徑（錯誤結構化、計量參數化、`entry` 必填）仍是新的，所以撤回一律兩檔全撤。
- **回到原狀的檢查**：撤回後本片碰過的每個檔 md5 與 `pre-apply-md5.txt` 相同；單元全套失敗集合＝9 筆基準；重建常駐後 `/mcp` 實打 2 輪，回應形狀與錯誤碼與改前相同（DA8 同法）。
- **worktree 副本**：併回後 `.claude/worktrees/` 下的本片副本會讓 `make audit` 不變量 36 多出紅燈（現有紅燈同源，`fill3/x1r/x6_audit.txt`）。DA7 判定時，不變量 36 只排除 `.claude/worktrees/` 下的命中並照實列出；刪 worktree 屬刪除，由業主下令。

## 6. 推翻項檢查

本片改的是 DSP-130 原「上線前入口不動」，已由業主以 DSP-131 取代，推翻卡與反向攻擊（`attack-entry-early.md`）已附在 DSP-131。本片沒有新的推翻項。

## 6.1 資安審查 r1 處置

報告 `~/jgb-archive/arch-step3-20261018/entry-align/security-review-r1.md`。沒有找到能繞過 `/mcp` 現有防護的路徑。

| 發現 | 處置 | 落在 |
|---|---|---|
| F1 P2 對外網址經 nginx 會 404 | FIX | §5.1 網址兩層、DA10 改必驗 |
| F2 P3 計量漏兩處 `mcp:` 與 `answer_source` | FIX | §5.2 第 3 項 |
| F3 P3 新入口錯金鑰不進前提偵測 | FIX | §5.2 第 3 項 |
| F4 P3 `entry` 預設與 fail-closed 相反 | FIX | §5.2 第 4、5 項 |
| F5 P3 對照表做不出、pydantic 會繞過 `_invoke` | FIX | §5.1、§5.2 第 1、2 項 |
| F6 P3 等價比對的兩處預期差異 | FIX | §5.2 第 6 項、DA2 |
| F7 P3 分兩次落地的半套狀態 | FIX | §5.4 |
| F8 P4 監控文件漏列 | FIX（`deployment-runbook.md` 是別窗檔，只交裁決） | §5.2 第 7 項、DA9 |
| F9 P4 稽核與 schema | FIX | §5.2 第 1、5 項 |

待查（實作時查，查到再定，不擋核可）：
1. `mcp==2.1.1` 對請求 body 有沒有自己的上限；有 ⇒ 新路由套同一上限（DA-R3「不比 `/mcp` 鬆」），查證寫進收案報告。
2. 503／504 時 JGB 會不會自動重送確認回合：接口 A 新章節寫明「503、504 與逾時一樣，確認回合 ⛔ 自動重送」（沿 F2-6）；JGB 端實際設定由業主請 JGB 對。
3. 確認回合中途斷線的計量與狀態：兩入口同一套 middleware，DA2 實打時各做一次斷線，結果寫進收案報告。
4. 後台 JWT 持有者由 nginx 注入 `RAG_ADMIN_API_KEY`：`/rag-api/mcp` 既有、非本片引入，記後補。
5. 正式機 `usage_events.channel` 型別：部署前由業主查（本系統正式機不在唯讀工具範圍）。

## 6.2 plan-verifier r1 處置

報告 `~/jgb-archive/arch-step3-20261018/entry-align/plan-verifier-r1.md`（REVISE，7 條）。主會話先對碼：前片終點表（`fill/report-fill-close.md` 終點節、`plan-fill-wide-20261028.md` §11、`plan-fill-structured-20261030.md` §1）、`McpServiceGate.__call__` 呼叫 `resolve_call`、目標正本 §1 第 61 行、DSP-131 第 31 行風險句，都屬實；引句「對話入口對齊不動解決率與錯筆卡」在 DSP-131 與目標正本都查無（`grep -c`＝0），屬實。

| 條 | 內容 | 處置 | 落在 |
|---|---|---|---|
| 1 | 終點指標只寫「全部 0」、現值未量未交裁、沒排收案重量、引句出處錯 | FIX | §1 逐列表、§7 DA12、§8 X-E1／X-E2、§9 第 1 題；引句改引 DSP-131 取捨原句與目標正本 §4 列 |
| 2 | 量測底座沒搬、偏離目標正本 §1 未交裁；缺廣度表與上位驗收方式 | FIX：底座搬進範圍 | DA-R9、§5.2 第 8 項、DA11、DA12、「## 廣度」、§0、§9 第 2 題 |
| 3 | 同一工作樹兩位寫手、填欄片量測映像可能被汙染；呼叫點漏 `McpServiceGate` | FIX：worktree、填欄片收案後才併回 | §5.4、§5.2 第 4 項 |
| 4 | DA-R2 讀法未標、§0 漏「MCP 門面」列（可後補） | FIX（順手，改動小） | DA-R2、§0、§5.3、§9 第 3 題 |
| 5 | 兩句業主原話沒對到規則（wording-only） | FIX | DA-R5、DA-R7 |
| 6 | §8 缺列、缺單位成本來源（wording-only） | FIX | §8 |
| 7 | 503／504 沒有依據（wording-only） | FIX | §5.1 |

plan-verifier r2（`~/jgb-archive/arch-step3-20261018/entry-align/plan-verifier-r2.md`，REVISE 2 條，皆標可後補；第二次 REVISE，處置後送一次收尾審查）：

| 條 | 內容 | 處置 | 落在 |
|---|---|---|---|
| 1 | 缺併回方法與撤回步驟（substantive，可後補） | FIX | §5.5 |
| 2 | 「前兩片實際變化」既有回歸列不全、M0 錯筆卡列引 X9、填欄擴及未收案卻寫已收案（wording-only，可後補） | FIX；對碼 `plan-fill-wide-20261028.md` §0 E 片、F12 兩列與 §11 屬實 | §1 終點表 |
| 待查 1 | DA2「無模型呼叫」與 DA11 不一致 | FIX：按鈕前要先 1 個模型回合出卡（`run_s5.py` `turn` 每回合送一句） | DA2、§8 |
| 待查 2 | 規格草稿未提交改動是誰的 | 本 session 主會話的 L4 段 | §5.4 |
| 待查 3 | worktree 副本會加不變量 36 紅燈 | FIX：判定與刪除方式寫明 | §5.5 |
| 待查 4 | 本機多半起不了 nginx | 計畫已有退路（DA10 pending-verify），不改 | — |

收尾審查 r3（`~/jgb-archive/arch-step3-20261018/entry-align/plan-verifier-r3.md`，REVISE 3 條：2 條 substantive、1 條 wording-only，皆標可後補）。依全域規則收尾審查不再開新一輪；三條都是凍結前改最省事，主會話對碼屬實後修掉，**修了、未再審**，交業主（DSP-115 第 2、4 點）：

| 條 | 內容 | 處置 | 落在 |
|---|---|---|---|
| 1 | DA2、DA11、§5.4「逐字相同」照字面做不到（模型輸出、`pending_id` 隨機） | FIX：統一比對口徑 N＋正對照 | §7 表下、DA2、DA11、§5.4 |
| 2 | DA-R6 範圍未標收窄，漏 `docs/api/conversational-api.md`（「外部串接只能走 `/mcp` 門面」） | FIX：範圍改成 DA9 grep 命中的全部現行文件，並點名該檔 | DA-R6、§5.2 第 7 項 |
| 3 | 文件擁有者前後矛盾（wording-only） | FIX：寫手只寫第 1～6 項 | §5.4 |
| 待查 2 | 不變量掃描範圍會命中 tests 的合法斷言 | FIX：範圍限 `services/`、`routers/`、`app.py` | §5.2 第 5 項 |
| 待查 3 | §3 Bedrock 錯誤碼漏 429 | FIX | §3 第 2 點 |
| 待查 1 | 本片 worktree 副本會不會讓填欄片 X6 audit 多紅燈 | 填欄片跑 audit 時對照，紅燈只在 `.claude/worktrees/` 照實列 | — |

## 7. 凍結驗收清單（核可時與 §2 一起凍結）

| 條目 | 規則 | 觀察點（層） | 證據 | 通過條件 |
|---|---|---|---|---|
| DA1 | R1、R2 | 常駐容器實打 `POST /api/v1/agent/turn`、`/upload-ticket`（真指令，用量測底座既有的金鑰取得方式，⛔ 讀憑證檔） | 請求與回應存檔 | 兩輪對話 200、7 鍵齊；上傳票 200；全程無 `initialize`、無 `Mcp-Session-Id` |
| DA2 | R5、R4 | 測試：兩入口同輸入、同 fake runtime；實打：2 輪，每輪先 1 個模型回合出卡、再按鈕回合（機器值，決定性），兩入口各跑一次 | 測試名；實打輸出 | 照比對口徑 N 兩入口 0 差異；`usage_events` 除 channel／processing_path／answer_source 外相同；額度用盡的差異照 §5.2 第 6 項預期 |
| DA3 | R3 | 測試＋實打：缺金鑰、身分壞、vendor 越界、帶外部 Origin、超每小時上限、額度用盡 | 測試名；實打狀態碼 | 每項與 `/mcp` 同樣被擋，HTTP 狀態依 §5.1 |
| DA4 | R1 | 測試：`_invoke` 對兩支工具實際會 raise 的每個代碼 | 代碼→狀態表＋測試名 | 全表有對應；表外代碼 500 |
| DA5 | R4 | 測試＋實打後查 `usage_events` | 查詢輸出 | 新入口每呼叫恰一列，`channel="dialogue_api"`；`/mcp` 的列仍是 `"mcp"` |
| DA6 | R3 | 測試：新入口 `entry="dialogue"` 下確認鈕兌現、寫入工具可見性與 `/mcp` 同；`"rest"` 仍 fail-closed | 測試名 | 全過 |
| DA7 | R1、R3、R4 | `make audit` | 輸出 | 不變量 28、31 涵蓋新路徑且綠；「新路由不 import `mcp.`」「`identity.py` 外無 `entry` 字面比較」綠 |
| DA8 | R5 | `scripts/run-tests.sh unit`；`/mcp` 實打 2 輪 | 輸出 | 失敗集合＝改前基準；`/mcp` 回應形狀與錯誤碼不變 |
| DA9 | R6、R8 | grep 現行文件：`git grep -nE "(外部串接\|呼叫端\|站內幫手\|JGB).{0,20}(只能\|應該)?(走\|經由\|透過\|打) ?\`?(POST )?/mcp" -- docs .claude/MAP.md .kiro/specs/agentic-mcp-orchestration`，命中逐條判現行或紀錄（2026-10-31 已知命中 `docs/api/conversational-api.md`、`TARGET_ARCHITECTURE.md` §8） | 指令與輸出（附正對照：同指令命中新入口段落） | 現行文件沒有「只能／應該走 `/mcp`」的陳述；接口 A 有新入口章節且對外網址是 `{AICHATBOT_BASE}/v1/agent/…`；L1、L2 不再寫「待定案」；`mcp-facade.md` 的計量辨識欄位含新入口；`deployment-runbook.md` 的改法已交裁決 |
| DA10 | R1 | **必驗**：經 nginx 的對外網址 `/rag-api/v1/agent/turn` 實打（本機 compose 有 `knowledge-admin-web` 就經它打） | 輸出 | 200；本機起不了 nginx ⇒ 標「上線前待驗」寫進 pending-verify，⛔ 寫成已驗 |
| DA11 | R9、R5 | 量測底座：`HARNESS_ENTRY` 預設與 `dialogue` 各跑 DA2 的決定性 2 輪 | 兩份紀錄＋與改前紀錄的 diff | 照比對口徑 N：預設 `mcp` 與改前 0 差異、`dialogue` 與 `mcp` 0 差異；`usage_events` 為 `dialogue_api` |
| DA12 | R9、R5 | 終點重量：本片收案映像經新入口跑 OV 96、M0 56（含盲判）、X5 回歸（§8 X-E1） | 判分檔、盲判結果、映像 commit／md5 | §1 終點表每列 ≥ 現值（填欄結構化片收案值）；錯筆卡、錯筆寫入不新增；任一列低於現值 ⇒ 停，跑 §8 X-E2 歸因後交業主 |

**比對口徑 N**（DA2、DA11、§5.4 共用）：模型輸出與確認值每次不同（確認鈕值＝動詞＋`pending_id`，`pending_id = pending_id_for(token)`、`token = secrets.token_urlsafe(...)`，`tools/confirm.py`），所以 ⛔ 比整份 dict。
- 出卡回合只比形狀：`kind`、頂層鍵集合、有沒有確認鈕、`quick_replies` 各顆 `value` 的動詞前綴（`:` 前一段）。
- 按鈕回合：先把 `pending_id`、確認 token、`trace_id`、時間戳、寫入產生的新紀錄 id、卡上欄位值換成佔位字，再比 `kind`、頂層鍵集合、狀態句（請確認／已完成／已取消／已轉人）、`quick_replies` 動詞前綴。
- 兩入口完整 dict 逐字相同只在單元測試（同 fake runtime、固定 token）比。
- 正對照：同一入口跑兩次，照 N 比必須 0 差異；不是 0 ⇒ 口徑漏了隨機欄位，先修口徑再判。

## 廣度

| 項目 | 類型 | 資料組（用／可用） | 不同輸入數 | 重複次數 | 輸入撰寫者 | 改前對照 |
|---|---|---|---|---|---|---|
| DA1～DA11 | 機制項 | — | — | — | — | — |
| 終點重量 OV（防退步） | 使用者層 | 1／1 mock 資料（OV 48 題涵蓋 6 類動作） | 48 | 2 | 既有出題代理，模擬客人自由講 | 填欄結構化片收案值（同 48 題） |
| 終點重量 M0（防退步） | 使用者層 | 1／1 | 29 題組（56 場） | 1～2 | 同上 | 同上 |
| 終點重量 X5 回歸（E2a、E 片、F12） | 使用者層 | 照各題組既有設定 | 照各題組 | 照各題組 | 既有題組 | 同上 |

上位驗收方式：目標正本 `architecture-target-20261018.md` §1「每片怎樣算完成」——通過條件在使用者入口層（「現況是 `/mcp`，對話入口對齊後改打專用對話 API」）；其他類別不退步：既有回歸題組不低於前一基線、測試全過、`make audit` PASS。本片照做：收案重量改走新入口（§5.2 第 8 項、§8 X-E1）。

## 8. 測試選擇（每次執行回答的決定與成本）

單位成本來源：單元全套 550.88 秒（`fill3/x1r/x6_unit.txt`，2026-10-31）；一次模型回合約 US$0.005、1 分鐘內（`plan-fill-structured-20261030.md` §10 第 3 點 (10)「`/mcp` 實打 2 輪：成本不到 1 分鐘、約 US$0.01」）；OV、M0、X5 的時間與 token 見同檔 §8 X1、X1r 列（OV 約 1 小時 49 分、M0 約 18 分、模擬客人約 60 萬＋34 萬 token、OV 盲判約 25 萬、M0 盲判約 14 萬；X5 約 21 分）。

| 執行 | 回答的決定 | 會改變下一步的結果 | 規模與成本（估） |
|---|---|---|---|
| 單元全套（worktree 交件時一次、併回主工作樹後一次） | 改動有沒有打壞現有行為（DA8）；便宜、決定性，每次改動照跑 | 失敗集合 ≠ 9 筆基準 ⇒ 不收案、修 | 每次約 9 分 |
| `make audit`（併回後） | 新不變量與 28、31 是否綠（DA7） | 新增紅燈 ⇒ 不收案、修 | 約 1 分（未單獨計時，估） |
| 新入口實打 2 輪＋上傳票 1 次（DA1） | 新入口在真容器能不能用 | 任一非 200 ⇒ 不收案 | 3 次請求、模型呼叫 2 次，約 2 分、約 US$0.01 |
| 兩入口按鈕型回合各 2 輪（DA2 實打）＋各一次中途斷線（§6.1 待查 3） | 薄殼有沒有改變回應；斷線時計量與狀態兩邊是否一致 | 按鈕回合回應不同或斷線結果不同 ⇒ 不收案、查 | 每輪先 1 個模型回合出卡（只比形狀，模型輸出不決定性），再按鈕回合逐字比對；約 10 次請求、模型呼叫 4 次，約 3 分、約 US$0.02 |
| DA3 實打 6 種拒絕（缺金鑰、身分壞、vendor 越界、外部 Origin、超每小時上限、額度用盡），兩入口各一次 | 新入口的每道閘是否與 `/mcp` 同樣擋 | 任一道新入口放行 ⇒ 不收案（資安） | 12 次請求、無模型呼叫；每小時上限與額度用盡要先把測試金鑰的上限調到可觸發，約 5 分、US$0（只動本機測試金鑰的上限，跑完還原） |
| DA5 查 `usage_events`（DA1～DA3 跑完後） | 每呼叫恰一列、`channel` 分得出 | 列數 ≠ 呼叫數或 `channel` 錯 ⇒ 不收案 | 1 條 SQL，<1 分 |
| `/mcp` 實打 2 輪（DA8） | 加法有沒有動到現有入口 | 回應形狀或錯誤碼與改前不同 ⇒ 不收案、查 | 2 次請求、模型呼叫 2 次，約 1 分、約 US$0.01 |
| DA10 經 nginx 實打 1 次 | 對外網址是否通 | 非 200 ⇒ 不收案；本機無 nginx ⇒ 寫 pending-verify | 1 次請求，<1 分 |
| DA11 底座 2 輪 × 2 入口 | 底座預設路徑沒變、新入口選項能跑 | 預設路徑按鈕回合紀錄不同 ⇒ 停、修底座（不跑 X-E1） | 同 DA2 的出卡＋按鈕形狀（`run_s5.py` `turn` 每回合送一句 `message`，按鈕值也是一句），模型呼叫 4 次，約 3 分、約 US$0.02 |
| **X-E1 終點重量＝填欄片 X4**（業主 2026-10-31 裁定合併）：兩片都含的映像、新入口跑 OV 96＋M0 56（含盲判）＋X5 回歸 | §1 終點表每列有沒有退步（DA12）；同時是「改後走新入口」的第一份量測 | 任一列 < 現值（X1r）⇒ 停、跑 X-E2；錯筆卡或錯筆寫入新增 ⇒ 停、交業主（DSP-115 第 3 點） | 不另跑：成本計在填欄片 X4。省下獨立一輪約 2 小時 30 分、模擬客人約 94 萬＋盲判約 39 萬 token |
| X-E2 歸因（條件執行） | X-E1 退步是入口造成、填欄片造成，還是隨機差 | 同映像經 `/mcp` 跑退步的那一批：只有新入口退 ⇒ 查入口；`/mcp` 也退 ⇒ 撤回本片（§5.5）重建、經 `/mcp` 再跑該批，仍退 ⇒ 填欄片或隨機差，照填欄片停點交業主 | 只跑退步的批（OV 或 M0 或 X5 的那一組），每步上限同 X4 該批 |
| 收案 verifier（另寫 ≥10 個新請求、兩入口實打） | 宣稱是否成立 | REFUTED ⇒ 依發現處置 | 約 20 次請求；verifier 用量以前片 X8b 101,928 token 估（`plan-fill-wide-20261028.md` §7 X8 列） |
| OV、M0、FS **在 worktree 階段** | **不排**：worktree 階段程式沒進任何映像；終點只在收案映像量一次（X-E1） | — | 0 |

## 9. 待業主裁

1. **核可時現值未量**（全域「終點指標」第 3 條）：§1 終點表的現值＝填欄結構化片收案值，該片程式還在寫，核可時量不到。建議：接受核可時未量，由該片 X4、X5 on 量完填入；本片程式在該片收案後才併進受測物（§5.4），現值一定先量完。另一做法：等填欄片收案再核可本片——worktree 寫程式的時間就跟著延後，與「1，架構也一起做」相反。
2. **改前改後入口不同**（TARGET §8「測試底座」列目標「改前改後走同一入口」）：本片改前值經 `/mcp` 量（填欄片收案值），改後經新入口量（X-E1）。入口本身就是本片的改動，所以兩邊入口必然不同。建議：接受，以 DA2、DA11 的決定性逐字比對證明兩入口回應相同，X-E1 退步時同映像補跑 `/mcp`（X-E2）歸因；本片之後的各片改前改後都走新入口。另一做法：收案映像兩入口各跑全量，多約 2 小時 30 分、約 133 萬 token。
3. **「分兩個區塊」要不要含程式模組搬家**（DA-R2 讀法）：本片做到協定、路由、計量三層分開，入口核心 `_make_invoke` 仍在 `mcp_facade.py`。建議：模組搬家記後補，等 `/mcp` 關閉時一起做（那時 MCP 門面只剩工具入口或整個拿掉，搬一次就好）；不改變本片的下一步（plan-verifier r1 判可後補）。另一做法：本片一起把入口核心搬到新模組，多一次大檔重構，`/mcp` 回歸風險變大。
4. 新入口的 `Identity.entry` 用新值 `"dialogue"`（本計畫），或沿用 `"mcp"`（改動最少，但 `/mcp` 關掉後名稱誤導，與 DA-R6 衝突）。主會話建議新值。

（JGB 上 master 時程：業主 2026-10-31 裁定不必在意，見 DA-R8；relay.jgbsmart.com 現況只影響日後何時關 `/mcp`，不在本片。）

**業主裁定（2026-10-31）**：選「核可，§9 照建議 (Recommended)」⇒ 第 1 題接受核可時現值未量，由填欄結構化片收案值填入；第 2 題接受改前 `/mcp`、改後新入口，以比對口徑 N 與 X-E2 歸因；第 3 題模組搬家記後補，`/mcp` 關閉時一起做；第 4 題 `Identity.entry` 用 `"dialogue"`。四題都出自主會話建議（等級 C），業主採入。

**業主裁定（2026-10-31，X-E1 停點）**：開關 off、經新入口跑 ov1031e、m0e31，四列都 ≥ X1r：OV 嚴格 69→75/96、OV 解決（扣錯筆）77→80/96、M0 harness 47→48/52、M0 盲判 44→45/52，所以不跑 X-E2。錯筆寫入 2→3，新增 1 場 OV contract-2 s9f983c06（同名物件只差編號，系統回覆與 X1r 逐字相同，模擬客人按第一顆，選成 40303），觸發「錯筆卡或錯筆寫入新增 ⇒ 停、交業主」。業主選「記為既有缺陷，續收案 (Recommended)」⇒ 記為既有雙胞胎物件缺陷（與 X1r interject-2 同），照 DSP-115 順序在上線後的雙胞胎片處理；續跑 X5 off、收案 verifier、收案報告。量測筆記：`~/jgb-archive/arch-step3-20261018/fill3/x1r/entry_close_notes.md`。

## 10. 用量

收案報告列子代理 token（任務通知加總）與模型呼叫次數。
