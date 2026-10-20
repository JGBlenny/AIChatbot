# 分工防偏離片（DG）計畫：兩道自動檢查（2026-10-20，業主核可）

> 服務原則：P0（混合式分工，目標正本 `architecture-target-20261018.md` 檔首分工表）；目標正本 §5「防歪機制」（AR3）。
> 規則與凍結驗收清單：`acceptance-division-guard-20261020.md`（規則在前）。決策：DSP-091（分工）。本片排在 A+ 之後、B 之前，依據是業主 2026-10-20 的原話「先補兩道 驗證 在記錄 重開 執行 b計畫」；新增「文件回合」片則依業主 2026-10-20「三題都選建議」（Q2）。現行順序決策 DSP-096 沒有這兩項，核可時另記 DSP-098（完整新順序：A → 期別 → A+ → DG → B → W2 → E → D → C → G → A-2 → 文件回合 → F；`supersedes` DSP-096），DSP-096 列首標「已由 DSP-098 取代。原決定：」。
> **終點指標**：E2b 寫入＋更正題組的 Intercom 解決數，現值 30/32（A+ 收案，`~/jgb-archive/arch-step3-20261018/aplus/report-aplus.md` §5 V7 E2b）。本片預期變化：**0**。依據：本片只加檢查與來源標記、不改受測系統行為（DG-R6）；業主同意先做本片再做 B（原話 2「先補兩道…執行 b計畫」）。效果在機制層：之後各片若讓已接手的環節退回模型，會被測試或 `make audit` 擋下。
> 業界原文以 web-drive 渲染存於 `~/jgb-archive/arch-guard-20261020/sources/`（每檔首兩行內有網址與擷取時間）。

## 1. 目標

業主原話（2026-10-20）：
- 「要怎麼確保沒有偏離架構 ?」
- 「先補兩道 驗證 在記錄 重開 執行 b計畫 ?」——回應主視窗的提議「建議補的兩道自動檢查：1. 架構契約測試，放進單元測試全量…2. 線上分工指標，接進 `make audit`…3. 另外建一份「仍由模型主導」清單，放在目標正本 §3」。

**成功的樣子**：之後任何一片（B、E、D、C、G、A-2、F 或其他修改）讓 DSP-091 分工表「程式」列的環節退回由模型決定時，不必等審查員或業主發現——單元測試或 `make audit` 會失敗並說出是哪一列；尚未接手的環節是一份看得到、只會變短的清單，每一筆有接手片。

## 2. 目標形態（業界做法）

| 做法 | 原文（逐字） | 來源 |
|---|---|---|
| 架構特性用自動化檢查持續驗證，可包含單元測試、指標、監控 | 「An architectural fitness function … provides an objective integrity assessment of some architectural characteristics, which may encompass existing verification criteria, such as unit testing, metrics, monitors, and so on.」「We believe architects can communicate, validate and preserve architectural characteristics in an automated, continual manner」 | Thoughtworks Technology Radar https://www.thoughtworks.com/radar/techniques/architectural-fitness-function（`thoughtworks-fitness-function.txt`） |
| 架構規則寫成一般單元測試 | 「ArchUnit’s main focus is to automatically test architecture and coding rules, using any plain Java unit testing framework.」 | ArchUnit User Guide https://www.archunit.org/userguide/html/000_Index.html（`archunit-userguide.txt`） |
| 既有違規先登記凍結，只報新違規；修掉的自動從登記移除，不准退回 | 「FreezingArchRule can help in these scenarios by recording all existing violations to a ViolationStore. Consecutive runs will then only report new violations and ignore known violations. If violations are fixed, FreezingArchRule will automatically reduce the known stored violations to prevent any regression.」 | 同上 |
| 對話層用端到端斷言防回歸：斷言「某個動作被觸發」這類事件 | 「E2E tests … are an important guardrail to prevent regressions—especially as you iterate on your flows, patterns, or LLM prompts.」「Assertions: Validate that certain events happen in the conversation as expected (e.g., a slot is set, a flow is started, a specific action is triggered, a response is grounded).」 | Rasa https://rasa.com/docs/pro/testing/evaluating-assistant/（`rasa-e2e-assertions.txt`） |
| 預期失敗的測試若意外通過，讓整套測試失敗 | 「This will make XPASS (“unexpectedly passing”) results from this test to fail the test suite.」（`@pytest.mark.xfail(strict=True)`） | pytest https://docs.pytest.org/en/stable/how-to/skipping.html（`pytest-xfail-strict.txt`） |

由此得到的目標形態：
1. **分工表每一列都有自動檢查**：已由程式接手的列是必過的契約測試。業界依據：ArchUnit「架構規則寫成單元測試」、Rasa「斷言某個動作被觸發」。斷言「由程式而非模型觸發」是本計畫依 DSP-091 的延伸（第一原理：分工表規定的是誰決定下一步，所以斷言對象是來源），Rasa 原文沒有講來源。
2. **尚未接手的列登記為已知偏離**：業界依據是 FreezingArchRule「記錄既有違規、只報新違規、修掉的自動從登記縮減」。本計畫的做法不同：偏離被修掉時檢查**失敗**，要人手動移出登記、改成必過。「意外通過即讓整套測試失敗」的效果取自 pytest `xfail(strict=True)`；以「現況探針」實作（探針斷言偏離仍在，偏離消失即失敗），屬本計畫設計。不用 xfail 斷言目標行為，因為那等於現在就替 B、E、D、G 決定介面（偏離與理由見 §4.3）。
3. **線上也量**（fitness function 的 metrics／monitors）：實際對話裡，確認卡與缺欄追問由誰發出，按來源計數；已接手的情境出現模型來源即失敗。

## 3. 差距（現況；查證指令在 repo 根目錄執行）

| 項目 | 現況 | 查證 |
|---|---|---|
| 分工契約測試 | 無以 DSP-091 列為單位的測試檔；A+ 的測試覆蓋「出卡」一列，但散在 A+ 驗收題號下，無列對照 | `ls rag-orchestrator/tests/unit/agent/ \| grep -i "dsp091\|division"`（正對照：同指令 `grep -i contract` 命中 `test_identity_slots_contract_req.py`） |
| 既有測試釘住舊行為 | golden 測試固定 `AGENT_WRITE_DRAFT` off（模型主導寫入）；`test_finalize_caches_handoff_and_counts_fixed_streak` 固定模型決定的轉人；`test_v13n_*` 刻意釘住點選範圍、文件暫存回合維持模型參數出卡 | `grep -n "AGENT_WRITE_DRAFT" rag-orchestrator/tests/unit/agent/test_pipeline_golden_req.py`；`grep -n "def test_finalize_caches_handoff" rag-orchestrator/tests/unit/agent/test_pipeline_order_req.py`；`grep -n "def test_v13n" rag-orchestrator/tests/unit/agent/test_aplus_card_program_only_req.py` |
| 出卡來源 | `_begin_pending_confirm` 是唯一出卡點（一處呼叫）；**模型自呼出卡沒有正面標記**，只能用排除法（`pending_id` 非空且無程式／提議標記），共現時會誤判 | `grep -n "_begin_pending_confirm(" rag-orchestrator/services/agent/runtime.py`（定義＋一處呼叫） |
| 線上資料 | 標記在 `usage_events.decision_snapshot->'agent'->'violations'`（jsonb 陣列，時間欄 `ts`），表上沒有 `violations` 欄；影子回合寫在 `agent_shadow` 另一鍵；`ask_target`、`outcome` 不進快照；表上分不出常駐、診斷、測試來源 | `grep -n '"violations": trace.violations' rag-orchestrator/services/agent/turn_context.py`；`grep -ln "decision_snapshot" rag-orchestrator/database/migrations/*usage_events*.sql` |
| `make audit` | `scripts/audit/check_invariants.sh`，現有不變量 1～44；FAIL 擋部署、WARN 不擋；維護準則 1「修掉一類 bug ＝ 加一條不變量」、準則 3「WARN 清單只准變短，變長要有新掛帳的立案紀錄」；已有多條查 `usage_events` 近 24h 的 FAIL（如不變量 6） | `grep -n "維護準則" -A6 scripts/audit/check_invariants.sh`；`grep -n "═══ 不變量 44" scripts/audit/check_invariants.sh` |
| 「過渡修正」註解 | 全 `rag-orchestrator` 只有 4 處，全在 `runtime.py` `_run_model_loop`；其中開關 off 那一處（`elif` 呼叫 `_write_draft_merge_model_confirm`）**沒有指向接手片**，與目標正本 §5 第 7 條「並指向將接手的那一片」不合 | `grep -rn "過渡修正" rag-orchestrator/`（正對照：同指令命中 4 處） |
| 目標正本 §3 | 差距表按原則寫，沒有「仍由模型主導」的逐筆清單 | `grep -n "仍由模型主導" .kiro/specs/agentic-mcp-orchestration/architecture-target-20261018.md`（正對照：同檔 `grep -n "## 3. 差距"` 命中） |
| 現況文件錯句 | `docs/architecture/AGENTIC_MCP_ARCHITECTURE.md` 仍寫「寫入面出卡與否綁模型…出卡率隨模型換動、非固定契約」，與同檔 A+ 段及 DSP-091 相反（A+ V11 漏掃） | `grep -n "出卡率隨模型換動" docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`（改前命中；DG-6 修正後預期 0 命中） |

**主視窗先前說錯的前提（更正）**：我 2026-10-20 回覆業主時說「子代理的 Stop 閘門會跑 `make audit`…容器沒開就會讓所有視窗、所有子代理都卡住」。實查不成立：完成閘門跑的是 `.claude/canon-accept.sh`，只對改動的 `.py` 做語法編譯，檔頭寫明「完整的系統不變量稽核仍是 `make audit`（需 DB/容器、數分鐘），部署前後手動跑」（`grep -n "make audit" .claude/canon-accept.sh`）。因此線上檢查照現有不變量的慣例放進 `make audit`、已接手的列 FAIL 即可，不必另開 make 目標。

**現存偏離逐筆**（runtime 盤查員唯讀盤查、主視窗抽查 `elif` 條件；DSP-091 程式列仍可能由模型決定的點）：

| ID | 偏離 | DSP-091 列 | 接手片 | 依據 |
|---|---|---|---|---|
| KD-1 | 點選範圍（`SELECT_SCOPE_KEY`）、唯讀檢視（`readonly_view`）回合：模型自呼 `confirm.request` 的參數照舊執行出卡；`elif` 同時把模型參數經值閘併進草稿 | 寫入全程、已選定的那筆紀錄 | A-2 | A+ 提議分支條件含 `agent_state.get(SELECT_SCOPE_KEY) is None and not self.readonly_view`，`elif` 條件不含；`test_v13n_carry_and_select_scope_turns_keep_current_behaviour` 斷言開關 on／off 相同 |
| KD-2 | 文件回合、文件暫存有效回合：模型參數出卡；文件程式發卡的非終結結果交回模型 | 寫入全程 | 文件回合（新片，業主 2026-10-20 裁 Q2；現註解寫「改動另審」，DSP-076） | A+ 提議分支條件 `document is None and _document_carry_of(agent_state) is None` |
| KD-3 | 提議未轉成程式呼叫（`write_proposal_not_issued`）、提議或草稿觸發的非終結結果（`write_draft_program_confirm_nonterminal`）：之後由模型寫寫入中的回話 | 寫入全程、帶狀態的句子 | B | 註解「寫入進行中回話由 B 片接手」 |
| KD-4 | 模型自寫「請確認」類句子（`prose_confirm_suspect`）只統計不改寫；寫入欄位的追問可由模型自寫（`kind=ask`） | 帶狀態的句子 | B | `grep -n '"prose_confirm_suspect"' rag-orchestrator/services/agent/runtime.py` |
| KD-5 | 轉人由模型 `kind=handoff` 決定；出口閘只在模型選了轉人後介入；敏感類、點選範圍零查詢、工具非 ok 等情形整段不動；無收尾規則 | 轉人規則（含收尾） | E | `exit_gates.py` `_apply_handoff_data_exits` 首行 `if result.kind != "handoff": return result` |
| KD-6 | 知識完全查無沒有程式先發的出口（`candidate_none_visible` 退回只給目錄） | 知識完全查無的出口 | D | `grep -n "candidate_none_visible" rag-orchestrator/services/agent/runtime.py` |
| KD-7 | 唯讀查詢的參數由模型自呼工具決定；程式只有範圍閘、前置查詢與查無出口（前置查詢是否完整接手：待查） | 唯讀查詢的查詢與篩選 | G | `grep -n "def _pre_lookup_trigger\|def _enforce_tool_scope" rag-orchestrator/services/agent/runtime.py` |
| KD-8 | 打字挑選候選無程式路徑（只有 `select:` 按鈕 fullmatch） | 已選定的那筆紀錄 | A-2 | `grep -n "_SELECT_VALUE_RE = re.compile" rag-orchestrator/services/agent/runtime.py` |

開關 off 路徑（三開關任一 off 時模型參數出卡，`model_confirm_ok`）**不列為偏離**（同一個 `elif` 在開關 on 時也服務 KD-1 的點選範圍、唯讀檢視回合，那部分屬 KD-1）：開關 off 是回復用的組態（A+ AP-R7「開關 off 時行為與改前相同」），目標組態是三開關皆 on（`docker-compose.prod.yml` 預設空＝on）。⇒ 該處註解依 DG-5 改寫（業主 2026-10-20 裁 Q3）。

## 4. 路徑（單片）

### 4.1 改動

| # | 改動 | 服務 |
|---|---|---|
| DG-1 | **出卡來源標記**：每次 `confirm.request` 經 registry 執行（不論出卡或回缺欄），本回合 `violations` 加且只加一筆 `confirm_source:<來源>`。來源：`program_draft`（草稿觸發，`wd_program`）、`program_proposal`（提議轉程式）、`program_document`（文件程式發卡）、`model:<理由>`。`<理由>` 由一支**獨立的純函式**依狀態判定（三開關、`document`、文件暫存、`SELECT_SCOPE_KEY`、`readonly_view`），⛔ 重用 A+ 分支的布林式；理由值域 `flag_off`、`document`、`document_carry`、`select_scope`、`readonly_view`，都不成立時為 `unregistered`。只加字串，⛔ 改任何分支、出卡或執行行為。 | 目標形態 3；取代排除法計數 |
| DG-2 | **已知偏離登記** `rag-orchestrator/tests/unit/agent/dsp091_known_deviations.py`：資料檔，KD-1～KD-8 各一筆（ID、DSP-091 列、說明、接手片、程式錨點符號、是否有「過渡修正」註解）；另列 DSP-091 程式列 R1～R6 與每列的必過測試名或 KD ID。 | 目標形態 2 |
| DG-3 | **分工契約測試** `rag-orchestrator/tests/unit/agent/test_dsp091_division_contract_req.py`（重用 `test_aplus_card_program_only_req.py` 的 `_World`、`_turn_p`、`_proposal`、`_with_select_scope`、`_with_carry`、`_runtime_functions` 等 helper）：<br>(a) **必過契約**（已接手列，見驗收 V2）；<br>(b) **現況探針**：KD 每筆一支，斷言偏離仍在；探針失敗訊息寫明「KD-n 已不成立：移出登記、改寫成必過契約、更新目標正本 §3 清單與程式註解」；<br>(c) **登記完整**：R1～R6 每列至少一支必過測試或一筆 KD；登記中的測試名都存在；<br>(d) **靜態**：`_begin_pending_confirm` 只有一處呼叫；`confirm_source` 理由函式在一般寫入回合判為「須由程式」時，A+ 提議分支條件為真（兩者一致）；「過渡修正」註解每一處都寫出一個登記中的接手片，登記中標「有註解」的 KD 至少一處註解。 | 目標形態 1、2 |
| DG-4 | **不變量 45** `scripts/audit/checks/division_guard.py`（附 `--self-test`）接進 `check_invariants.sh`：<br>(a) **靜態**（不需 DB）：目標正本 §3 新增的「仍由模型主導」清單 ID 集合＝`dsp091_known_deviations.py` 的 KD 集合，接手片相同；不一致 FAIL（`CODE_REGRESSIONS`）。<br>(b) **線上**：近 7 天 `decision_snapshot->'agent'->'violations'` 含 `confirm_source:` 的列。正對照：`confirm_source:program_%` 計數 > 0，否則印「⚠️ 未判：近 7 天無程式出卡樣本」（WARN，立案紀錄＝本計畫）；有樣本時 `confirm_source:model:unregistered` > 0 ⇒ FAIL（`CODE_REGRESSIONS`）並列出 `trace_id`。<br>(c) **尚未接手的列只印數字**（ℹ️，不 WARN、不 FAIL、不設門檻，DSP-087）：各 `confirm_source` 來源計數、`prose_confirm_suspect` 次數。 | 目標形態 3 |
| DG-5 | **程式註解**：`elif` 呼叫 `_write_draft_merge_model_confirm` 那一處的註解改寫為同時涵蓋兩種情形：(i) 開關 off——回復開關（AP-R7），非目標組態；(ii) 三開關 on 時的點選範圍、唯讀檢視回合——KD-1 過渡修正、不新增 AI 決定權，由 A-2 接手（現註解「這裡只剩開關 off 的現行行為」與程式不符，一併改正）；KD-1、KD-3 既有註解保留並確認寫出接手片；KD-2 依 Q2 裁示寫入接手片。 | 目標正本 §5 第 7 條 |
| DG-6 | **文件**：目標正本 §3 末加「仍由模型主導（已知偏離）」清單（KD-1～KD-8、接手片、登記檔路徑）；§5 加第 8 條「自動檢查」（契約測試檔、登記檔、不變量 45；每片收尾把接手的 KD 改成必過）；§4 加 DG 列；`AGENTIC_MCP_ARCHITECTURE.md` 錯句改成現況（A+ 開關 on 時一般寫入回合出卡只由程式依草稿觸發，例外情境見目標正本 §3 清單）；同檔其餘轉人來源段與 `docs/architecture/agent-path-retired-symbols.md` 若有與 DSP-091 相反的現行陳述，一併改正文；`.claude/MAP.md` 登記本計畫與驗收檔；`.claude/DECISIONS.md` 記 DSP-098（新順序，取代 DSP-096），目標正本 §4 順序句與 HANDOFF 只寫新順序並引 DSP-098；HANDOFF 改各片狀態與下一步（B）；快照重寫。 | AR8、AR9；業主「在記錄」 |

### 4.2 不做

- 不修任何 KD 偏離本身（各由接手片做）；不改出卡、追問、轉人、查詢的行為。
- 不翻轉 golden 與 `test_pipeline_order_req.py` 釘住舊行為的測試（golden 測的是開關 off 的回復組態；轉人那支屬 KD-5，E 片翻轉）。
- 不設線上指標門檻（DSP-087、DSP-093：先跑出數字再定）。
- 不新增模型呼叫、不碰 JGB、不碰正式機與 preview。

### 4.3 偏離目標形態的取捨

| 偏離 | 理由 |
|---|---|
| 已知偏離用「現況探針」而非 pytest `xfail(strict=True)` 斷言目標行為 | 用 xfail 要先寫出 B、E、D、G 的目標行為斷言，等於本片替後續片決定介面；探針只斷言「偏離仍在」，消失即失敗，同樣只准變短（FreezingArchRule 的效果），不預設後續片怎麼做。 |
| 偏離被修掉時檢查失敗、要人手動移出登記（FreezingArchRule 是自動縮減） | 本系統的登記同時是目標正本 §3 清單、程式註解與接手片的對照；自動縮減會讓三處不同步。手動移出時一併改 §3 與註解，不變量 45 靜態段核對兩者一致。 |
| 線上檢查只對「確認卡與缺欄追問的來源」設 FAIL，其他列只印數字 | 只有寫入面已接手且有可靠的來源標記；轉人、查無、查詢尚未接手，設 FAIL 會常紅（準則 5「避免稽核疲勞」）。 |
| 線上表分不出常駐、診斷、測試來源 | `usage_events` 無來源欄（盤查實查）；本片不加欄位（動 migration 屬另一風險類），所以線上 FAIL 列出 `trace_id` 讓人追。 |
| 無樣本時 WARN 而非 FAIL | 正式機部署前 runbook 也跑 `make audit`；本片程式上線前正式機一定沒有 `confirm_source` 標記，FAIL 會擋住所有部署。檢查器本身以非 0 退出碼回報「未判」，`check_invariants.sh` 印出原因，不靜默當 PASS（全域「否定結論」第 2 條）。我先這樣做了，要改請說。 |

## 5. 安全

本片不碰授權、憑證、身分、個資：DG-1 只在 `violations` 加來源字串（值域固定、不含使用者文字或 id），DG-4 唯讀查本機 DB 計數與 `trace_id`。不觸發 security-reviewer。

## 6. 執行與驗收

- **改前基線**：工作樹裡 `runtime.py`、目標正本、HANDOFF、MAP、DECISIONS 等已有其他片未 commit 的改動（HEAD `4bb48114`），AUTO 不得 commit。故動工前先把本片會改的每一個既有檔複製到 `~/jgb-archive/arch-guard-20261020/baseline/`（保留 repo 相對路徑），並記下各檔 `shasum -a 256`；V3 的 diff 與 §8 回復一律以這份副本為準（`diff -u baseline/<路徑> <路徑>`），⛔ 用 `git diff` 或 `git checkout` 判斷或回復。單元測試全量的改前失敗集合也在動工前於同一容器跑一次存到同目錄，V7 以它為準。
- 執行：核可後由主視窗派一位 `executor`（判斷型；DG-1～DG-5），文件 DG-6 由主視窗寫。動 `runtime.py` 前依 canon 先讀前置文件。
- 驗收清單：`acceptance-division-guard-20261020.md`（凍結後依它判）。實作完成後：單元測試全量、`make audit`、本機常駐容器重建後實打數回合寫入（mock 檢查先印 True），再派 fresh `verifier`。
- 新增不變量前再查一次最大編號（DSP-013），他窗若已用 45 就順延。

## 7. 業主裁示與待裁

Q1～Q3 已裁（2026-10-20：「照建議，三題都選建議」）；Q4、Q5 為 r2 新增，業主同日皆選建議（驗收檔原話 4）。

Q1～Q3 皆採建議，記為驗收檔原話 3：Q1 含清單；Q2 KD-2 由新增「文件回合」片接手（DG-6 在目標正本 §4 加列、排在 A-2 之後 F 之前，並另立一條 DECISION 記順序變更，DSP-096 只標被取代）；Q3 開關 off 路徑不列偏離、註解改寫為「回復開關」。按鈕歸屬已記為待裁 DSP-097（`dispute.py`，不擋本片）。下列為原提問：

- Q1 範圍讀法：「先補兩道」——是否含提議第 3 項「仍由模型主導」清單（本計畫讀法：含，因為它就是第 1 道的登記內容，DG-4(a) 讓兩者一致）。
- Q2 KD-2（文件回合模型參數出卡）的接手片：現註解只寫「改動另審」，與目標正本 §5 第 7 條要指向接手片不合。建議：在目標正本 §4 新增「文件回合」片，排在 A-2 之後、F 之前（改路徑須業主核可）。
- Q3 開關 off 路徑：建議視為回復組態、不列偏離，註解改寫為「回復開關」。
- Q4（r2 新增）採主視窗修正 (a)：尚未接手的列登記為已知偏離＋現況探針、測試現在全綠；線上只對 `unregistered` 判 FAIL，已登記情境只印數字。另一種讀法是照提議字面「每一列都寫成必過測試、模型路徑次數必須為 0」，則測試與 `make audit` 會一直紅到 B、E、D、G 做完。建議採 (a)。影響 DG-R1、DG-R2、DG-R4。
- Q5（r2 新增）提議 3「處數必須和清單一致」改讀成「每處註解對得到登記、登記中標有註解者至少一處」：KD-5～KD-8 是缺少的程式路徑，沒有分支可掛註解，字面一對一做不到。建議採改讀。影響 DG-R5。
- 另記（不擋本片）：DSP-091 決策檔的程式列沒有「按鈕」，專案 CLAUDE.md 與目標正本有；本片把按鈕歸在「帶狀態的句子與確認卡」那一列測（按鈕本來就只由程式組，`AgentOutput` 沒有按鈕欄位），以 `dispute.py` 記為待裁。

## 8. 回復、停點、用量

- 回復：新增的檔（契約測試、登記檔、檢查器、本計畫與驗收檔）直接移除（屬未追蹤新檔，移除前問業主）；既有檔以 §6 基線副本對照，只撤回本片加的區塊（`diff -u` 列出的部分），⛔ 整檔蓋回或 `git checkout`——那會抹掉他片未 commit 的成果。
- 停點：(1) 必過契約任何一支在現行程式上失敗 ⇒ 停，回報為新發現的偏離（不在本片修）；(2) 探針任何一支失敗（偏離其實不存在）⇒ 停，更正登記與 §3 後再續；(3) 不變量 45 在本機有樣本時判 FAIL ⇒ 停，查 `trace_id`。
- 用量：收尾回報子代理 token 加總（含本計畫三位盤查員）與 API 費用。

## 9. 計畫審查紀錄

| 輪 | 結論 | 處置 |
|---|---|---|
| r1 | REVISE（5 項） | 全 FIX：補終點指標行；順序出處改依業主原話、核可時記 DSP-098；主視窗修正 (a) 與 DG-R5 改讀交業主（Q4、Q5，原話 4）；V8 正對照改 `_write_proposal_handle`、同義詞改 `出卡.{0,4}綁模型`；§2 過度歸因改標本計畫設計並加 §4.3 偏離列 |
| r2 | REVISE（4 項） | 第二次 REVISE，停止自動重送，逐項處置後開一次收尾審查：(1) brief 未附業主逐字原話——FIX（收尾審查 brief 直接貼原話 1～4）；(2) `elif` 註解只寫開關 off、漏 KD-1——FIX（DG-5、V5）；(3) DG-R4 漏寫 `kind=ask` 寫入追問不量——FIX（DG-R4 讀法欄、非目標）；(4) `git diff` 無改前基線——FIX（§6 基線副本、V3、V7、§8 回復）。另修：報告節名 §5 V7、存檔首兩行說明 |
| r3（收尾審查，brief 附業主逐字原話 1～4） | READY | — |
