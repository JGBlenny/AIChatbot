# 實作任務：knowledge-outline-and-intent-architecture（大綱正本、口語多意圖架構、小量先於放量）

> 建立時間：2026-09-06
> 需求：requirements.md v2（R1–R8，64 子項；業主 2026-09-06 核可，R1.5 定向 hook＋Workflow；v2.1 改 API 判者＋子代理提議）｜設計：design.md **1.3**（12 元件、10 決策、不變量 32–34；security-reviewer 20 條→附錄 E、plan-verifier r1 11 條→附錄 F、r2 6 條→附錄 G、closing **READY**，餘 N1–N3 三條 P3 由 1.2 吸收）｜研究：research.md｜缺口：validation_gap.md
> 標記：`(P)` = 可與同層其他 `(P)` 平行；`- [ ]*` = 可延後的補充測試
> ⚠️ 規則／模板缺席：`.kiro/settings/rules/tasks-*.md` 與 `templates/specs/tasks.md` 不存在，格式沿用 `agentic-mcp-orchestration/tasks.md`。
> 鐵律：**正本＝system prompt 寫入權（R2.9／DSP-012）——正本只在 git、走 code review，DB 為衍生物**；**正本目錄＝`rag-orchestrator/canon/`（design 路徑約定）**；**隔離謂詞單一來源 `build_visibility_predicate`，b2b ⛔ 不加 `IS NULL`；「內容已審」為第二單一來源 `review_state.content_reviewed_predicate`（正向白名單 `reviewed:`）**；**引用單位＝正本細目的行（DSP-029a unit），Verifier 尺 ⛔ 不動（DSP-034 重提條件）**；**⛔ LLM 查詢改寫（裁定 8）**；**判「已覆蓋」⛔ 用被驗系統排序（裁定 10）**；**凍結題 ⛔ 入講法（裁定 11）**；**trace ⛔ 落原文、⛔ 落講法 id**；**DB 寫入／migration 執行由業主授權（D1）**；⛔ 不 push；⛔ 不動線上；`*.sql` `git add -f`；一次性腳本不 commit；材料 sha 跑前凍結、比較性結論 ≥30 題；TDD 先紅後綠、容器內跑（`make test`）；破壞性操作給指令＋預期輸出由業主跑。
> **執行註記**：每個子任務下方一行 `執行：<角色>／effort <低|中|高>——理由`。角色＝Claude Code 派工角色，**model 由各角色定義路由、⛔ 派工時不覆寫**（`mech-executor`＝全規格機械工；`executor`＝有限判斷；`security-executor`＝授權後的安全敏感實作；`verifier`／`plan-verifier`／`security-reviewer`＝唯讀；`main`＝主 session 親做）。**風險觸發（可見性／審核謂詞／匯入寫入／個資）的任務完成後必派 fresh `verifier`**；宣稱療效／數字／尺一律派獨立代理（G4）。
> **待裁對應**（不擋任務生成，擋對應里程碑）：D1 DB 寫入授權 → 7.3；D2 部分回答＋轉人 → 5.4（步 2／3 探針後才裁）；D3 個資政策 → 2.2 已以預設落地（`raw/` gitignored＋90 天刪＋識別碼掃描），改裁只動 2.2。
> **驗證標記（業主 2026-09-06 要求）**：每個子任務末行 `驗收：目標＝…｜成果＝…｜做法＝…｜驗證＝…`。驗證四種：`[自驗]`＝unit／integration 綠即可、無獨立驗證；`[代理驗證]`＝完成後派 fresh `verifier`（唯讀實跑，給確切 claim）；`[業主審核]`＝業主看產出（文件／草稿／rubric／門檻）決定通過，⛔ 未審不得進下一步；`[業主親跑]`＝業主自己執行指令或下裁決（DB 寫入、migration、D1–D3、預算）。一個任務可疊多種。
> **定義清楚度自檢（同日）**：原稿 6 處定義不足已補在任務本文（1.4 可答性 rubric、2.2 幫助中心標題來源、2.3 結構提議 schema、4.2 身分反問句型表、4.4 探針選題規則、5.5 六套劇本內容）；其餘任務的目標／成果／做法皆可由 design 對應元件唯一推出。
> **路徑基準**：`inputs/`＝本 spec 目錄 `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/`；跨 spec 材料一律寫完整 repo 相對路徑（問法正本＝`.kiro/specs/presales-grounding-gate/coverage-map/sources/koyu-v2-phrasings.json`；凍結題 manifest＝`.kiro/specs/agentic-mcp-orchestration/eval/samples-manifest.json`）。
> **plan-verifier r1（tasks）處置（2026-09-06）**：4 P2 全 FIX（3.4 gold 改決定性映射、不變量 32／33 D1 前 SKIP、`reweigh.py` 補進 2.6、7.4 樣本 C 前置與 stop）；3 筆派工改 `security-executor`（3.2／3.3／4.2）；2.1／1.5 加 `[代理驗證]`；P3：rubric `partial` 定義、1.1 先建占位檔、4.3 落點寫死、2.2 計數改實查、四個大任務標 a／b 兩段派工。
> **plan-verifier r2（tasks，closing）READY**：3 P2 已落（2.4b 明寫 `helpcenter:<slug>` 併入細目 `sources`＝3.4 gold 生產者；32／33 的 SKIP 改程式自動判定＋正對照；1.2 匹配收窄為受眾正本白名單、README 不命中）；P3 #5 落 3.4（slug 由 article 鍵生成）、#4 落 3.6。
> **依賴序**：1 → 2 → 3 → 4 → 5 → 6 → 7；同一大項內 `(P)` 可平行，未標者依序。M-a 首件（1.1）⛔ 不得跳過——它是所有 hook 閘門「接得上線」的唯一實證。

## 0. 你會拿到什麼（業主視角；每階段第一個交付物都是給你審的東西，不是程式碼）

| 階段 | 這階段要證明的一件事 | 你會拿到 | 你拿它做什麼 |
|---|---|---|---|
| **M-a 機制**（§1） | 流程紀律靠 hook／隔離判者跑得起來，不靠叮嚀（Workflow 試作後改 API 判者） | ① `inputs/hook-probe-20260906.md`：hook 真的接上線的實跑證據 ② 可答性 rubric（四值判準）③ `inputs/m-a-trial-20260906.md`：55 格試作的成本／一致率／續跑命中率 ④ 預算初值（每步／整案） | 核 rubric；看試作報告核預算上限；此時**沒有任何正本、沒動產品程式** |
| **M-b 售前正本**（§2） | 21 列＋18 草稿能變成一份你看得懂、能逐條審的大綱 | ① `rag-orchestrator/canon/prospect.md` 草稿（A–G 粗目；每細目標題／講法／內容句／來源／審核者欄）② `diff-report.json`：舊 kb 列→細目的取代對應表 ③ `coverage-map.json`：55 格每格去向（進哪個細目／現有不足／刻意不補／待你裁） | 逐粗目審草稿、改講法、裁 `owner_decision` 格；**你審過並簽 reviewer 的那份才是正本** |
| **M-c 組裝與索引**（§3） | 程式能決定性組裝正本、口語能對到細目 | ① health 三個 sha（正本／講法集／索引）② 步 1 三臂數字：標題／標題＋講法／＋內文 各自 recall@1/3/5，依粗目×問法型 ③ 決策 5 定案文 | 看數字點頭「線上用哪個匹配鍵」；這是**第一個免費就能回答的命題**（口語→細目的上限在哪） |
| **M-d 回合接線**（§4） | 候選細目＋入口身分能讓「查無」變成「回答」而不猜 | ① `inputs/object-under-test.md`＋假設表（跑前給你核）② 凍結的 ≥30 題探針集 ③ 步 2 探針報告：翻轉率、對照組是否仍轉人、引用細目＝正解比率、盲標無據率（兩判者） | 跑前核受測物與推翻條件；跑後看三個數字決定是否進 M-e；推翻條件命中就停 |
| **M-e 對話邏輯**（§5） | 售前對話規則（kb 3645）搬進 agent 後流程正確 | ① `agent_rules.py` 定義文（它就是 prompt，給你審）② 身分反問句型表 ③ 六套劇本＋契約測試報告（A/B 判對率、一次一題、身分不重問、CTA 只在收斂、零捏造） | 審定義文與劇本；此時才裁 D2（部分回答＋轉人） |
| **M-f 閉環與 LINE**（§6） | 缺口按受眾有去向；LINE 業務受眾有自己的知識正本 | ① coverage_map 完整版（判者一致率、跨受眾改寫草稿）② `property_manager-line.md` 草稿（含「什麼時候說不」清單、待驗三項）③ LINE 可見性契約測試結果 | 審 LINE 草稿與待驗清單 |
| **M-g 入庫與上版**（§7） | 正本安全進 DB、放量前門檻先凍結 | ① D1 執行包：七步指令＋每步預期輸出＋rollback 路徑（你自己跑）② 放量門檻文件（跑前核）③ 步 4 放量報告（依受眾×問法型答到率／無據率／敏感 0 漏）④ 平台票五張、agentic-mcp 收尾註記 | 跑 D1；核門檻；看放量數字決定上版 |

一句話：**M-a 給「流程可信」的證據、M-b 給「可審的正本草稿」、M-c 給「口語能不能對到細目」的數字、M-d 給「候選有沒有用」的數字、M-e 給「對話對不對」的契約、M-f 給 LINE 草稿、M-g 給上版包。** 你要出手的 14 個點見各任務 `驗收：` 行的 `[業主審核]`／`[業主親跑]` 標記。

## 1. M-a 機制：hook 閘門、判者最小試作（Workflow→API）、skill 骨架（1.1 先做；1.2／1.3 平行；1.4 後 1.5 後 1.6）——**全部完成**

> **階段目標**：證明「流程紀律靠機制」在本 repo 跑得起來——hook 接得上線、判者可回放、成本可量（Workflow 版量出不可行 ⇒ 1.6 改 API 判者）。**成果**：可用的閘門＋一次試作報告＋預算初值。**⛔ 不產正本、不動產品程式。**

- [x] 1.1 hook 接線實跑（⛔ 首件，不憑文件）：建 repo 層 `.claude/settings.json`（`PreToolUse`／`PostToolUse` matcher `Edit|Write`、`Stop`；command 形狀 `sh -c '[ -f "$CLAUDE_PROJECT_DIR/.claude/hooks/outline_gate.py" ] && exec python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/outline_gate.py" || exit 0'`）與 `outline_gate.py` 探測骨架（只印 `CLAUDE_PROJECT_DIR`、事件名、事件原始 `file_path` 的形狀（絕對／相對）到 `.claude/hooks/state/outline-gate/probe.log`，⛔ 不擋任何事）；先 Write 建 `rag-orchestrator/canon/README.md`（占位檔，內容＝路徑約定一句）再對它做一次 Edit 觸發並讀 log；結果落 `inputs/hook-probe-20260906.md`。`.gitignore` 補 `.claude/hooks/state/`、`.claude/skills/outline-curation/raw/`、Workflow journal 路徑。
  - 需求：1.4
  - 執行：main／effort 低——這是「前提形狀是否對齊線上」的實測，⛔ 不派工；結果決定 1.2 的相對化寫法
  - 驗收：目標＝證明 hook 拿得到 `CLAUDE_PROJECT_DIR` 與事件 `file_path` 形狀｜成果＝`inputs/hook-probe-20260906.md`（含 log 原文）＋`.gitignore` 三條｜做法＝探測骨架只印不擋，Edit 占位檔一次｜驗證＝[自驗]（log 有三個值即過）
- [x] 1.2 (P) `outline_gate.py` 五道判定＋自證（TDD）：PreToolUse（目標完整相對路徑匹配**受眾正本白名單** `rag-orchestrator/canon/<audience>.md`（`prospect.md`／`property_manager-line.md`…），⛔ 不含 `README.md` ⇒ 本 session 須有 `diff-report.json` 且 `inputs_sha.canon`＝目標現 sha，否則 exit 2）；PostToolUse（同路徑 ⇒ parser 可解析、schema 過、細目 id 唯一、講法 ∩ `.kiro/specs/agentic-mcp-orchestration/eval/samples-manifest.json` 各 set 題句（NFKC）＝∅；**另對 `.claude/skills/outline-curation/runs/` 跑識別碼掃描**（N3））；Stop（跑過 `agent_eval`／`index_eval` ⇒ `inputs/object-under-test.md` 存在且核可欄非空、材料 sha 已凍結、`cost.json` 兩層未超支；`answerability.json.needs_rubric_revision=true` ⇒ 擋）；腳本先把 `file_path` 依 1.1 實測形狀相對化再比對（N2）。測試 `tests/unit/_meta/test_outline_gate_req.py`：五種違反各紅、五種合規各綠（N1）；負對照「repo 根 `canon/prospect.md` ⇒ 不命中」、「`rag-orchestrator/canon/README.md` ⇒ 不命中」；絕對路徑假事件必命中；接線 meta 測試（解析 `.claude/settings.json` 每條 command，`$CLAUDE_PROJECT_DIR` 代入後檔案存在，故意改壞必紅）。腳本零第三方依賴、⛔ 不讀網路、⛔ 不讀 `.env`。
  - 需求：1.4, 5.5, 6.1
  - 執行：executor／effort 中——判定規格齊，但相對化與事件形狀需依 1.1 實測決定
  - 驗收：目標＝四道紀律變成機制｜成果＝`outline_gate.py`＋10 案自證＋接線 meta 測試綠｜做法＝TDD，依 1.1 形狀相對化｜驗證＝[自驗]＋[代理驗證]（claim：五種違反在真 hook 路徑各被擋一次、非目標路徑零誤擋）
- [x] 1.3 (P) skill 骨架與決定性腳本（TDD）：`.claude/skills/outline-curation/{SKILL.md,steps/01–07,schemas/*.json,scripts/}`；`intake.py`（讀 kb 列／草稿／缺口地圖／既有正本 → `intake.json`，含各輸入 sha 與「受測物定義清單」骨架）、`diff_report.py`（結構差異＋id 對應表＋取代對應表 `replacements[]`）、`cost_ledger.py`（彙總 Workflow journal＋provider usage → `cost.json`；每步／整案兩層上限自 `SKILL.md` front matter 讀：步 2 ≤6／$0.5、步 4 ≤180／$3、整案 ≤240／$6；任一層超支 exit 2）。所有腳本輸出走 `StepEnvelope`（`inputs_sha`、`deterministic`、`raw_outputs_path`、`cost`）。測試：同輸入兩次逐位元相等；`cost_ledger` 以 110 代理假 journal 不擋、181 必擋（正對照）；schema 校驗每步輸出。
  - 需求：1.1, 1.2, 1.3, 1.6, 1.7
  - 執行：mech-executor／effort 中——schema 與腳本契約已在 design 元件 1；預算值為初值
  - 驗收：目標＝七步有 schema、可回放、記成本｜成果＝skill 目錄＋三支腳本＋schema 校驗綠｜做法＝決定性腳本、`StepEnvelope`｜驗證＝[自驗]
- [x] 1.4 Workflow `.claude/workflows/outline-curation.js` 可答性一步（1.2／1.3 後）：`meta` 純字面（phases Structure／Answerability／Reconcile）；`args={step:'answerability', cells, items, frozenAt}`；候選＝程式列舉的**臨時細目集合**（F2 的 21 列 prospect＋18 筆草稿，id `tmp:kb:<id>`／`tmp:draft:<n>`；⛔ 不經 FineIndex／任何排序）；`pipeline(cells, 判者1, (v1,c)⇒判者2, r⇒不一致才判者3)`，判者 `effort:'low'`、schema `AnswerabilityVerdict{cell_id,label,fine_id(enum＝臨時集合),evidence_unit,confidence,provisional:true}`；Reconcile 純程式算一致率、`<0.90` ⇒ `needs_rubric_revision=true`；⛔ `Date.now()`（時間戳由 args）。判者 prompt 組裝函式 unit：輸入不含分數／排序／系統判定欄位（塞 `score` 必紅）。先以 2 格乾跑確認 `resumeFromRunId` 續跑 100% 快取命中（API 名稱以本 session 工具 schema 為準，乾跑再證）。 **rubric（定義不足已補）**：`schemas/answerability-rubric.md`——`answerable`＝候選細目內容有 ≥1 句可直接回答該格代表問句且不需使用者實值；`partial`＝只答得了部分子問題（子問題＝代表問句可拆出的獨立問點，判者於 `evidence_unit` 註記答到的那一點）；`no_source`＝候選中無任何句可答；`deliberate_no`＝格的 `policy=deliberate_no` 且有 `policy_ref`。判者只看問句＋候選內容＋此 rubric；rubric 跑前凍結（sha 入 `inputs_sha`）並經業主核可，改 rubric＝新 readiness epoch。
  - 需求：1.5, 3.4, 6.5
  - 執行：executor／effort 高——本 repo Workflow 首例；判者隔離與 schema 是這一步的全部價值
  - 驗收：目標＝判者隔離＋schema 強制的 Workflow 首例可續跑｜成果＝`outline-curation.js`＋rubric＋2 格乾跑報告｜做法＝pipeline 三階段、臨時細目集合｜驗證＝[業主審核] rubric；[自驗] 乾跑續跑 100%
- [x] 1.5 M-a 試作實跑與報告（1.4 後；2026-09-06 跑 44／55 格、一致率 0.841；業主同日裁 0.841 可接受 ⇒ 門檻改 0.80、done ③ 過；usd $15.84 超支待裁，見 inputs/m-a-trial-20260906.md §7）：55 格 × 2 判者（不一致加第 3）跑一次；`cost_ledger` 出 `cost.json`；報告 `inputs/m-a-trial-20260906.md`：總 token／usd、wall、一致率、續跑命中率、每格 verdict 分佈；對照 design 附錄 C M-a done ①–⑦ 逐條打勾（一致率 <0.90 ⇒ 出口＝回修 rubric，⛔ 不算通過；重跑前回主 session 重核預算）。預算初值（步／整案）交業主核定。
  - 需求：1.5, 1.7
  - 執行：main／effort 中——收案判斷與預算呈核屬主 session；⚠️ 這裡的 verdict 全為 `provisional`，⛔ 不進正本、不進地圖
  - 驗收：目標＝量出試作成本／一致率，定預算初值｜成果＝`inputs/m-a-trial-20260906.md`＋done ①–⑦ 打勾表｜做法＝跑一次 55 格｜驗證＝[代理驗證]（claim：一致率與成本數字可由 journal 重算一致）；[業主親跑] 核定預算；[業主審核] 報告
- [x] 1.6 可答性判者改腳本直打 API（**同日業主再裁撤回：API 只在真實對話；步 4 改 `answerability_agents.py` 分組子代理，API 判者已刪，本項只留試作紀錄**）（1.5 後；2026-09-06 實跑 gpt-4o-mini 55 格：自身一致率 0.964、≈$0.10、跨模型同 sonnet 33／44，見報告 §8；業主 2026-09-06 裁：硬體撐不住 Workflow、Workflow 留參考）：`scripts/answerability_judge.py`——system＝`promptHead+candidatesBlock` 掛 `cache_control`（rubric＋39 候選共用前綴）、user＝`cellBlock+cellTail`，system+user 逐位元等於 `build_judge_prompt`；每判者獨立請求（互不可見）；`output_config.format=json_schema`（VERDICT 同 JS）；judge1／judge2、不一致才 judge3；Reconcile 與 JS 逐條等價（門檻 0.80）；journal jsonl 以 prompt sha＋slot 為 key 續跑；usage 逐請求累加、usd 依牌價表；憑證由 SDK 零參數解析，⛔ 不讀 .env、不進 argv／transcript。**測試**（假 client、不需 SDK）：請求形狀＋prompt 等價、隔離與第 3 判者、三不同落 no_source、refusal 丟格、續跑零呼叫、成本算術、門檻同值。**實跑（業主 2026-09-06 裁：1.5 的 44 格結果不作廢）**：只補批 5（C45–C55）——用 `--layout workflow`（system+user 逐位元＝Workflow 判者 prompt、無共用快取，11 格約 30 請求估 <$0.5）跑完後 `merge_answerability_batches.py` 併成 55 格；`--layout cached`（共用快取前綴，段落順序不同＝另一版 prompt）留給日後整輪重跑，⛔ 不與 workflow 版面混算。業主在自己 shell 設 Anthropic 憑證後跑；`cost_ledger` 步 4 回到 $3 內（只計本次 API 花費）。
  - 需求：1.5, 1.7
  - 執行：main／effort 中——與 1.4 同一套 schema 與 Reconcile，換執行形態；實跑要業主憑證
  - 驗收：目標＝同一把尺在 MB 級記憶體下補完 55 格、日後整輪 <$2｜成果＝`answerability_judge.py`＋unit＋55 格合併 envelope｜做法＝直打 API；批 5 用 workflow 版面、日後用 cached 版面｜驗證＝[自驗] unit；[業主親跑] 憑證與實跑；[代理驗證]（claim：system+user 與 Workflow 判者 prompt 逐位元相同、usd 可由 journal usage 重算）

## 2. M-b 售前正本：parser、講法、結構提議、首跑草稿（2.1 先做；2.2／2.3／2.5 平行；2.4 後 2.6）

> **階段目標**：把 21 列 prospect＋18 筆草稿變成第一份人審正本草稿（A–G），且每個缺口格有去向。**成果**：`rag-orchestrator/canon/prospect.md` 草稿＋diff-report＋取代對應表＋coverage-map（步 0 出口全綠）。**驗證**：業主審草稿（[業主審核]）。

- [x] 2.1 `services/agent/canon/canon_parser.py`（TDD；2026-09-06 主 session 親做，34 unit 容器綠，verifier 派中）：Markdown 正本 → `CanonDoc`（front matter 七鍵 `audience, version, reviewers, language, budget_tokens, target_user, business_types`；粗目 `## … {#X}`；細目 `### … {#<audience>/<X>/<slug>}`，id 正則 `^[a-z_]+/[A-Z]/[a-z0-9-]+$`；屬性清單 `phrasings/sources/reviewed/see_also/policy/policy_ref/target_user/business_types/categories/instance_applicability`；內容一行一句＝`content_units`）；`content_sha256`、`canon_sha256`（Markdown 位元組）、`phrasing_set_sha256`；`export_json`（JSON 帶同一 sha）；**屬性區塊內任何無法解析的行 ⇒ `CanonFormatError`（列號＋原因），⛔ 不落 `content_units`**；`source: traffic:*` 的講法 ≤20 字且不含 ≥4 位數字串。測試：固定樣本往返決定性；`content_units` 對 `provenance_units` 恆等；`OutlineDoc.text ∩ 講法集合＝∅`（塞一句講法必紅）；每種格式錯各一案。
  - 需求：2.1, 2.3, 2.5, 2.8, 7.3
  - 執行：executor／effort 中——格式已定，錯誤分類需局部決定
  - 驗收：目標＝正本可被決定性解析且格式錯即紅｜成果＝parser＋往返測試＋每種格式錯一案｜做法＝TDD｜驗證＝[自驗]＋[代理驗證]（claim：屬性區塊任何壞行皆 raise、講法零字元進 `OutlineDoc.text`——注入面）
- [x] 2.2 (P) 講法與相似細目工具（2026-09-06 security-executor＋fresh verifier：REFUTED P2「全形／空白變體漏網」已修＋回歸鎖；hook 三條正則誤判另修；首跑 230 講法／984 待審）：`phrasing_map.py`（question_summary 關鍵字／幫助中心標題／問法正本 → 講法提案 `status=proposed`，**去識別在任何 agent 呼叫之前**：人名／地址／合約號／電話／email／LINE id／統編／房號戶名／社區與物件名／車牌／金額＋日期，原句只落 `raw/`（gitignored）、`raw_purge.py` 依檔名日期刪 90 天前）；`similar_items.py`（細目標題含講法向量兩兩相似 → 待審清單，⛔ 不合併；每細目講法上限 12、NFKC 去空白去重）。測試：去識別各類正反例；`tests/unit/_meta/test_pii_scan_req.py` 對 `rag-orchestrator/canon/`、`.claude/skills/outline-curation/runs/` 全掃，塞 email／電話必紅。 **來源解析（定義不足已補）**：幫助中心標題＝`/Users/lenny/jgb/幫助中心/JGB幫助中心_HTML_交付_20260818/*_zh-Hant.html`（扁平檔名，⛔ 無子目錄；數量以 `ls … | grep -c '_zh-Hant.html$'` 實查為準並寫進報告，2026-09-06 實查＝92）的 `<title>`／`<h1>`，來源標 `helpcenter:<slug>`（slug＝檔名去 `_zh-Hant.html`）；問法正本＝`.kiro/specs/presales-grounding-gate/coverage-map/sources/koyu-v2-phrasings.json`（排除凍結 54 句與「操作」型）；question_summary＝F2 的 21 列。
  - 需求：1.8, 2.5, 5.5
  - 執行：executor／effort 中——D3 預設已定，識別碼類別封閉；⚠️ 個資觸發 ⇒ 完成後派 fresh verifier
  - 驗收：目標＝講法有出處、已去識別、相似細目只出待審｜成果＝兩支工具＋PII 掃描測試｜做法＝去識別先於任何 agent 呼叫｜驗證＝[代理驗證]（claim：塞入各類識別碼皆被擋、`raw/` 未進版控）
- [x] 2.3 (P) 結構提議（**形態＝Claude Code 子代理、⛔ 不打 API**，業主 2026-09-06 裁；`structure_propose.py prepare／validate／synth-prompt／package` 決定性外殼，2026-09-06 主 session 親做、7 unit 綠）＋`apply_proposal.py`：3 角度（使用者提問路徑／內容邊界／受眾層級）＝3 個子代理各出 `structure-proposal` schema → 第 4 個子代理合成（三份原提案留 raw/）；`apply_proposal.py` 把提議決定性套成正本 Markdown 草稿＋id 對應表（拆／併／移／新增各有前後對照；未附對應表 ⇒ exit 2）。測試：合成輸出 schema 校驗；`apply_proposal` 同輸入兩次逐位元相等；缺對應表必擋。 **schema（定義不足已補）**：`structure-proposal.json`＝`{coarses:[{id,title}], fines:[{id, coarse_id, title, slug, merge_of:[kb id|draft n], split_from:[…], moved_from:[…], reason}], id_map:[{old, new, op∈{keep,split,merge,move,new}}], angle}`；合成 agent 輸出同 schema 外加 `rejected_alternatives[]`（每條一句理由）。
  - 需求：1.1, 1.3, 1.5
  - 執行：executor／effort 高——結構提議是唯一「LLM 決定結構」的步，非決定性標記與 journal 保留要做對
  - 驗收：目標＝結構由三角度提議、人審合成、id 對應表強制｜成果＝Structure phase＋`apply_proposal.py`｜做法＝judge panel＋決定性套用｜驗證＝[自驗]
- [x] 2.4 售前首跑（2.1–2.3 後；**2026-09-07 收案**：2.4a 審查版→2.4b 步 4 子代理 55 格 0.945→2.6 reweigh→步 5b 權威來源核對（jgb2 對碼 8 格）→步 6 草稿 v3→v3 重判 55/55→**業主照准**，落 `rag-orchestrator/canon/prospect.md`＋`prospect.json`（38 細目全 `reviewed: owner 2026-09-07`）；報告 `inputs/m-b-answerability-20260907.md`、`inputs/m-b-reweigh-20260907.md`；⛔ 未入庫，入庫＝7.x／D1）：輸入＝F2 的 21 列 prospect（8 列 `IS NULL` 業者列 ⛔ 排除）＋18 筆草稿（`scripts/knowledge-batches/presales-gapmap-batch2-20260904.json`）＋缺口地圖 v2.1；**分兩段派工**：2.4a 步 1–3（intake、Structure 提議＋合成、講法掛載）→ 產結構草稿＋講法提案，主 session 檢視後才起 2.4b；2.4b 步 4–6（可答性判者＝`answerability_agents.py`：分組 5 格、每組 2 個子代理、≤4 並行（H7）、重量、diff）→ `rag-orchestrator/canon/prospect.md` 草稿（**細目內容取自某幫助中心文章者，其 `sources` 必併入 `helpcenter:<slug>`——這是 3.4 gold 的唯一生產者**）（A–G；G「現有不足」每格一句對外說法＋出口、E 只用既有來源、缺者標不足）、`diff-report.json`（含 `replacements[]` old kb id → fine id）、`cost.json`；交業主審草稿（⛔ 不 commit 正本、⛔ 不入庫）。
  - 需求：1.9, 2.2, 2.10, 3.6, 3.7
  - 執行：main／effort 高——首跑的每一步輸出都是業主要審的東西，主 session 親跑並逐步檢視
  - 驗收：目標＝第一份售前正本草稿｜成果＝`prospect.md` 草稿＋diff-report＋replacements＋cost｜做法＝主 session 親跑步 1–6｜驗證＝[業主審核] 草稿逐粗目（⛔ 未審不 commit）
- [x] 2.5 (P) 正本同源與治理測試（2026-09-06 主 session；同源測試在尚無正本時 skip 標示、竄改正對照綠；README 審核流程＋PR 模板高風險 diff）：CI unit 硬把關 `export_json(parse_canon("rag-orchestrator/canon/<a>.md"))` 與版控 `.json` 逐位元相等（竄改一位元必紅）；`canon/README.md` 寫審核流程（PR review＝寫入權、reviewer 名進 front matter）；review checklist 標 `.claude/settings.json`／`.claude/hooks/` 為高風險 diff。
  - 需求：2.9
  - 執行：mech-executor／effort 低——規格齊全
  - 驗收：目標＝JSON 永遠是 Markdown 的衍生物｜成果＝CI unit 硬把關＋README 審核流程｜做法＝逐位元比對測試｜驗證＝[自驗]
- [x] 2.6 `tools/gapmap/coverage_map.py` 初版與步 0 出口（2.4 後；**2026-09-07 主 session 親做**：Plan `inputs/plan-2.6-coverage-map-20260907.md` 三輪 plan-verifier P2 全 FIX→業主核 (a)；fresh verifier CONFIRMED；容器 272 綠；真材料 55／55 有去向，報告 `inputs/m-b-reweigh-20260907.md`；偏離 design 四點見 Plan §8）：讀正本＋`demand-v2.json`＋`answerability.json` → `CellRecord`（去向 ∈ {fine, not_available, deliberate_no, owner_decision}、`fix_type`、`min_verification`）；跨受眾缺口列 `cross_audience_rewrite`＋草稿路徑（⛔ 不直接開放 Y 的列）；「回答未含必含」與「有知識但撈不到」分開報；輸出 `coverage-map.json`＋摘要進 `scripts/status.py`；**skill 步 5 腳本 `reweigh.py`**（design 元件 1；E6）：呼叫本工具重量，讀到 `answerability.json.needs_rubric_revision=true` ⇒ exit 2（正對照 unit：旗標 true 必擋、false 必過）。出口：無去向格＝0、無來源細目＝0（Stop hook 亦查）。
  - 需求：2.4, 3.1, 3.2, 3.3, 3.5, 3.7
  - 執行：executor／effort 中——狀態機沿 demand-v2 `_meta.states`，去向欄與「一格對一細目」對應為新增
  - 驗收：目標＝每格有去向｜成果＝`coverage-map.json`＋status 摘要＋無去向格＝0｜做法＝讀正本＋demand＋answerability｜驗證＝[業主審核] 去向表（`owner_decision` 格由業主裁）

## 3. M-c 組裝與索引：審核謂詞、正本組裝、細目索引、步 1 上限（3.1 先做；3.2 後 3.3／3.4／3.5 平行）

> **階段目標**：正本能被程式決定性組裝與索引，可見性與審核狀態各有唯一謂詞；量出口語→細目的檢索上限。**成果**：啟動契約（sha 重算）、FineIndex／selector、不變量 32–34、步 1 三臂數字、決策 5 定案。**驗證**：3.1／3.2／3.3 [代理驗證]。

- [x] 3.1 `services/agent/canon/review_state.py`（TDD；security-sensitive；**2026-09-07 收案**：Plan `inputs/plan-3.1-review-state-20260907.md` 三輪 plan-verifier P2 全 FIX→業主核 (a)＋值域收嚴 (a)；security-executor 實作；verifier CONFIRMED；unit 926／integration 150；`make audit` PASS、32 SKIP(pending-D1)；migration ⛔ 未執行、D1 由業主；P3 債：unicode NBSP 在 PG 與 Python 鏡像分歧）：`REVIEWED_PREFIX="reviewed:"`、`POOL_MARK_PREFIX="pool-marked-"`、`content_reviewed_predicate() -> (" AND kb.outline_approved_by ~ %s", [REVIEWED_REGEX])`（正向白名單；⚠️ **regex 不用 `LIKE`**——`LIKE` 的 `_` 會吃空白，`reviewed: alice` 會被放行，plan-verifier 2026-09-07）；`tools/kb.py::fetch_visible_row` 拼此謂詞（票 D）；migration `20260907_outline_approved_by_domain.sql`（`CHECK (outline_approved_by IS NULL OR outline_approved_by ~ '^(reviewed:[^[:space:]]+|pool-marked-[0-9]{8})$') NOT VALID`，業主 2026-09-07 裁值域收嚴；⚠️ `database/migrations/*.sql` 已在 `.gitignore` 白名單，**不需 `git add -f`**；執行與 `VALIDATE CONSTRAINT` 由業主，D1）；不變量 32 進 `agent_boundary.py`（新增 `_review_state_paths()` 只供 32；掃 `services/agent/**`＋`tools/**` 的 `outline_approved_by` 字面；命中 <1 ⇒ FAIL；DB 側值域外列數＝0——**D1 前現況 29 列為 `owner-20260905` 必為值域外，此子檢查在 D1 執行前印 `SKIP(pending-D1)`、⛔ 不計 FAIL；7.3 ⑤ 之後轉硬失敗**。SKIP 為**程式自動判定、⛔ 不寫死旗標**：僅當「`generation_metadata->>'canon_ref'` 衍生列數＝0 ∧ 值域外列全為 `owner-20260905`」才 SKIP，否則實跑；自測正對照：模擬 D1 後狀態（有一列衍生列／出現一個新值域外值）必紅）。測試：現況 29 列 `owner-20260905` 在新謂詞下**全部不可見**（預期，D1 前整池視為未審）；大小寫／前導空白變體不放行；`kb.get` 整數 id 對未審列 `NO_MATCH`。
  - 需求：2.7, 5.4, 8.4
  - 執行：security-executor／effort 高——動 agent 路徑可見性；完成後派 fresh verifier 跑正反例與不變量 32 空跑不綠
  - 驗收：目標＝「內容已審」有唯一正向謂詞，未審列 agent 路徑不可見｜成果＝`review_state.py`＋kb.get 拼謂詞＋migration＋不變量 32｜做法＝白名單、TDD｜驗證＝[代理驗證]（claim：29 列現值全不可見、變體不放行、32 空跑不綠）；migration [業主親跑]（D1 時）
- [x] 3.2 `canon_assembler.py`＋啟動契約（3.1 後；**2026-09-07 收案**：Plan `inputs/plan-3.2-canon-assembler-20260907.md` 三輪 plan-verifier P2 全 FIX→業主核 (a)＋§8 照准；security-executor 實作；verifier CONFIRMED（17 組身分×細目對 SQL 謂詞零分歧）；unit 959／integration 154；`make audit` PASS＋29b；design 1.11 回寫；**P3 債：`build_outline` 未套 `canon_visible`，4.1 每回合子集必須套**）：`load_canon_or_die(canon_dir, audience)`（同讀 `.md`＋`.json`、`.md` 重算 sha 比對；缺檔／不符／格式錯 raise；`AGENT_CANON_DIR` 預設 `<rag root>/canon`，覆寫只在 `DB_ENV=test` 生效，health 印 resolved path）；`build_outline(doc)`（每細目一節、id＝fine id、標題行 `【fine_id】`、`citable=(reviewed_by is not None)`、未審只出標題）；`build_toc(doc, visible)`（`outline:toc`、`citable=False`、只列 visible 且已審）；`make_outline_resolver` 回傳前套 `visible_subset`（不可見／未審 ⇒ `NO_MATCH`）；`build_prospect_outline(db_pool)` 首行改呼叫 `load_canon_or_die` → `build_outline` → `check_budget`；退役 `SIX_MODULES`／`_classify_row`／`_CTA_TEXT`／`DSP009_DELIBERATE_GAPS`／`_extract_boundary_sentences`（G／F 粗目承接）；映像已含 `.md`＋`.json`（`COPY . .`）。測試：unit 每細目一節／未審 citable=False／sha 涵蓋 version；integration：`_agent_configured()` 為真時刪 `.md` ⇒ 啟動紅、竄改 `.json` 一位元 ⇒ 啟動紅、未竄改必綠。
  - 需求：2.6, 5.4, 5.9
  - 執行：security-executor／effort 高——resolver／toc 套可見性＝附錄 E F7 可見性繞過的修補，屬 validation／hardening；完成後派 fresh verifier
  - 驗收：目標＝啟動由 .md 重算 sha、目錄與 resolver 套可見性｜成果＝assembler＋`load_canon_or_die`＋退役舊分類表＋兩條啟動紅測試｜做法＝改 `build_prospect_outline` 首行｜驗證＝[代理驗證]（claim：刪 .md／竄改 .json 各啟動紅、未竄改綠）
- [x] 3.3 (P) `fine_index.py`＋`candidate_selector.py`（TDD；**2026-09-07 收案**：Plan `inputs/plan-3.3-fine-index-selector-20260907.md` 第 2 輪 READY→業主核 (a)＋§8 照准；3.3a／3.3b 皆 security-executor＋fresh verifier CONFIRMED；15 格×3 身分＋4 額外身分記憶體＝SQL 零分歧、突變控制紅；unit 985／integration 210；design 1.13；已知：匯入端空清單預設 system_provider 待 7.1／3.5 對齊）：`FineIndex.prepare(doc)`（標題向量＋approved 講法向量，每批 ≤8；任一 None ⇒ `not_ready`；快取鍵＝`canon_sha256`＋`phrasing_set_sha256`）、`state ∈ {absent, not_ready, ready}`、`visible_subset(identity, doc, *, vendor_business_types)`（b2b：`∩{system_provider}` 非空且 target_user 命中或空；b2c：空或 ∩ 非空且含 `all_users`；target_user 先過 `_effective_target_user`；⛔ 內部不查 DB）；`CandidateSelector.select(doc, identity, query)`（首行 sha 比對；查詢＝當前＋上一則 user；分數＝max(標題, 講法)；只在 visible 內排序；K=5、同分 id 序；`miss_kind`；三態回 None；⛔ 不 log 查詢）；`Selection.winning_key_kind`（⛔ 不記講法 id）；health `canon` 節。測試：決定性、同分序、`doc.sha` 不符 None、caplog 無查詢字串、`visible_subset` 對 b2b pm／b2b prospect 與 `build_visibility_predicate` 集合相等（衍生列以 `canon_ref` 查）。
  - 需求：5.1, 5.2, 5.3, 5.6, 5.10
  - 執行：security-executor／effort 高——`visible_subset` 是記憶體側授權謂詞（與 SQL 集合相等為 acceptance）；**分兩段派工**：3.3a `FineIndex`（prepare／快取鍵／三態／health）、3.3b `visible_subset`＋`CandidateSelector`＋等價測試；完成後派 fresh verifier
  - 驗收：目標＝細目索引決定性、記憶體可見性＝SQL 可見性｜成果＝FineIndex＋selector＋health｜做法＝標題＋講法取最大、三態｜驗證＝[代理驗證]（claim：兩組身分集合相等、caplog 無查詢字串）
- [x] 3.4 (P) `tools/canon/index_eval.py`（步 1，$0；**2026-09-07 收案**：Plan `inputs/plan-3.4-index-eval-20260907.md` 業主核（三髒鍵合併、三項全等凍結、limited 備案 55 格）；受測物 `inputs/object-under-test.md` 核可；422 句重生三項全等、gold＝細目 `sources` 決定性映射（`koyu-article-map.json`，alias 後 unresolved 0）、153/422 句可對映、五型皆 ≥30；主結果 loo=article 三臂 r@5 title .582／+phrasing .621／+content .673，第二份材料 49 格 .857／.898／.959；misrouted 81 屬 5.6 治理；fresh verifier CONFIRMED（獨立重算 0 差異）；P3 狀態路徑＋P4 article-map 已修；報告 `inputs/m-c-index-eval-20260907.md`＋`index-eval-20260907.json`；決策 5 數字交 3.6）：輸入正本 JSON＋422 句（依 `inputs/phrasing-selection-rule-20260906.json` 規則自問法正本重生，sha 對得上）＋**gold 細目（決定性、$0，⛔ 不派判者）**：新建 `inputs/koyu-article-map.json`——程式由 koyu json 的 article **鍵**（本身即 slug，如 `slug13`／`qa27`，實查對應 `<slug>_zh-Hant.html` 存在）生成 slug、對不到檔案者列人工待審 → 細目 id（正本細目 `sources` 含該 `helpcenter:<slug>` 者；一篇對多細目時全列為 gold 集合）；文章對不到任何細目的句子**排除並計數**（claim ceiling：報「可對映句數／型」，任一型 <30 句即標「該型結論受限」）；55 格代表問句（gold＝2.4b 判者標的 `fine_id`）作第二份材料分開報。gold 以細目 `sources` 為準、⛔ 不改用講法 `source` 迴避（會與 `title+phrasing` 臂同源）；⛔ 不重用 1.4（其 item 是格不是句）；三臂 `title`／`title+phrasing`／`title+phrasing+content` 留一輪替；輸出 recall@1/3/5 依粗目×問法型；`--report misrouted`（勝出講法所屬細目 ≠ gold）。結論：臂間差 <10 點 ⇒ 該臂不值得；reranker 是否納入依 top-5 增益 ≥5 點且 p95 不退步（此處只出數字，決策 5 定案由主 session）。
  - 需求：5.2, 5.11, 6.2, 6.4, 6.7
  - 執行：executor／effort 中——量測工具；材料 sha 跑前凍結；gold 映射表只審「對不到檔案」的待審列 [業主審核]（一次）；結果只證檢索層承載力（R6.7）；費用 $0（無 LLM）
  - 驗收：目標＝量出三臂 recall 上限｜成果＝`index_eval.py`＋報表（依粗目×問法型）｜做法＝留一輪替、材料 sha 凍結｜驗證＝[代理驗證]（數字宣稱必派）
- [x] 3.5 (P) 不變量 33／34 checkers（**2026-09-07 收案**：mech-executor；33 走 docker exec 進 rag 容器呼叫真 `visible_subset`／`build_visibility_predicate`（host 無 pydantic），衍生列 0 ⇒ SKIP(pending-D1)、psql 不可達 FAIL、self-test 6 案注入假查詢；34 首跑抓到真違規「水電費怎麼分算」＝agentic-mcp 劇本 S1 題句，講法改「水電費分算方式」（正本 .6）；unit audit 42 綠、`make audit` PASS）（**加對帳（業主 2026-09-07）：衍生列 `business_types`／`target_user` 為 NULL ⇔ 正本細目該欄為空清單；出現 `'{}'` 或被預設成 `system_provider` 而正本為空 ⇒ FAIL**）：33（必查組 b2b pm vendor 0、b2b prospect；tenant 標 M4 納入列 notes；每組命中 <1 ⇒ FAIL——**衍生列（`generation_metadata.canon_ref`）在 D1 入庫前恆為 0，此檢查 D1 前印 `SKIP(pending-D1)`、⛔ 不計 FAIL，7.3 ⑤ 後轉硬失敗；SKIP 同 3.1 為程式自動（衍生列數＝0 才 SKIP），自測：塞一列衍生列必實跑且必紅**；突變控制改錯一列 `business_types` 必紅）；34（`rag-orchestrator/canon/*.json` 講法 ∩ 跨 spec manifest 題句＝∅；塞一句必紅）；接 `check_invariants.sh`（編號接續 27–31）。
  - 需求：2.7
  - 執行：mech-executor／effort 中——照 `agent_boundary.py` 既有 checker 慣例＋正對照
  - 驗收：目標＝33／34 進 audit 且空跑不綠｜成果＝兩支 checker＋正對照｜做法＝照 agent_boundary 慣例｜驗證＝[自驗]
- [x] 3.6 決策 5 定案（3.4 後；**2026-09-07 業主裁 (a)**：線上匹配鍵改標題＋講法＋內文句取最大（內文臂 loo=article r@5 +9.1 點、講法臂 +3.9 點）；reranker 不接；講法密度目標每細目 approved ≥3（0 講法細目 2 個待業主補講法：`prospect/C/role-permission-granularity`、`prospect/D/subscription-change-renewal`）；design 決策 5 修訂＋變更歷史 1.14）：依三臂數字定線上匹配鍵（預設標題＋講法取最大）與講法密度目標；寫回 design 1.4 變更歷史；⛔ 不調 K。
- [x] 3.7 `FineIndex` 內文鍵（3.6 後、4.1 前；決策 5 修訂落地；**2026-09-07 收案**：Plan `inputs/plan-3.7-fine-index-content-keys-20260907.md` 第 1 輪 REVISE 3 P2 FIX→第 2 輪 READY→業主核（§8 照預設）；executor＋fresh verifier CONFIRMED（獨立重算 358 鍵、47/49 vs 44/49 對報告 article 臂 .9592／.898、sha 不符 SKIP、隱私與常數不變）；unit 1014／integration 210／`make audit` PASS；design 1.15；P4：`_best_entry` 未知 kind 落 -2、未驗「內文句只記住來源」命題交 4.4a）：`KeyKind` 加 `content`；`prepare` 對每細目 `content_units` 每句一鍵（key id＝`ct:<sha8>`，⛔ 不記句文於 trace）；快取鍵 `canon_sha256` 已涵蓋內文、不加鍵；批次 ≤8 與三態不變；`Selection.winning_key_kind` 值域加 `content`；health `canon` 節加 `content_keys` 計數。測試：`index_eval` 內文臂與 `FineIndex` 同鍵集（鍵文字集合相等）；`visible_subset` 等價測試不變；突變控制（拿掉內文鍵 ⇒ 第二份材料 r@5 必降）。⛔ 不調 K、⛔ 不接 reranker。
  - 需求：5.2, 5.6
  - 執行：executor／effort 中；完成後派 fresh verifier
  - 需求：5.2
  - 執行：main／effort 低——判斷屬主 session
  - 驗收：目標＝匹配鍵定案｜成果＝design 1.4 變更歷史一行（同時記：步 1 gold 由「判者標」改為「文章→slug→細目 `sources` 決定性映射」，55 格判者材料降為第二份）｜做法＝讀 3.4 數字｜驗證＝[業主審核]（決策 5 由業主點頭）

## 4. M-d 回合接線：候選注入、身分槽位、評估工具、步 2 探針（4.1／4.2／4.3 平行；4.4 後）

> **階段目標**：回合真的用候選細目與入口身分作答，且探針證明「查無→回答」翻轉而不猜。**成果**：runtime 接線、身分槽位、評估工具擴充、步 2 探針報告（翻轉率／對照組／無據率）。**驗證**：4.1／4.2 [代理驗證]；4.4 材料與假設表 [業主審核]、盲標 [代理驗證]×2。

- [x] 4.1 (P) `CandidateOutlineDoc`＋runtime 注入（**2026-09-07 收案**：Plan `inputs/plan-m-d-runtime-wiring-20260907.md` §2（封套＋S1 經 plan-verifier 兩輪 REVISE＋收尾審查、主 session 逐條 FIX、業主核 §5 六項）；executor＋fresh verifier CONFIRMED（15 探針：K=5 只選細目進 prompt／provenance、降級只給可見細目、pm-only 內容兩路徑皆不外洩、同物件 `is`、白名單 16、形狀守門、主／影子共用 selector、prepare 逾時留 absent、health 紅規則、b2c prospect `none_visible`＋`candidate_none_visible`、kb_get 前綴矩陣、無文字外洩）；unit 1049／integration 210／audit PASS；design 1.16；3.2 P3 債還清；P4 三條留紀錄；TDD；**前置債（3.2 verifier P3）**：`build_outline` 不套 `canon_visible`，整份正本內容進 system prompt——本任務的每回合子集必須以 `canon_visible`／`visible_subset` 切，並加測試「不可見細目內容不得出現在 `OutlineDoc.text`」）：`from_selection(full, sel)`（audience／version／sha 複製自母 doc；sections＝K 細目＋toc）；`run_turn` 在 `outline = agent_state.get("outline")` 後呼叫 selector，同一物件餵 `_seed_outline_provenance` 與 `build_messages`（unit 以 `is` 斷言）；selector None ⇒ 整份正本＋`violations.append("candidate_fallback_full_outline")`；`except Exception` ⇒ 整份＋`candidate_selector_error`；`app.py` 主／影子共用同一個已 prepare 的 selector；trace／`decision_snapshot.agent` 加 `candidate_ids`／`winning_key_kind`／`miss_kind`（票 C；同步 `_ALLOWED_AGENT_DECISION_KEYS`，形狀斷言 `re.fullmatch(r"[a-z_]+/[A-Z]/[a-z0-9-]+")`、長度 ≤K，違規值必紅）；`trace_view`／`shadow` 鏡射。測試：候選路徑與降級路徑各一回合（假 embedding client）；`tool_results_by_id["outline"]` 只含 K 細目＋toc；toc 引用得 `SOURCE_NOT_CITABLE`。
  - 需求：5.1, 5.9, 8.3
  - 執行：executor／effort 高——動 runtime 熱路徑；完成後派 fresh verifier
  - 驗收：目標＝回合只看被選的細目，降級走整份｜成果＝`CandidateOutlineDoc`＋runtime 注入＋trace 三鍵｜做法＝沿 Plan v3 路徑 (a)｜驗證＝[代理驗證]（claim：候選／降級各一回合形狀正確、白名單多一鍵即紅）
- [x] 4.2 (P) 身分槽位（**2026-09-07 全數收案**：S2b＝句型表 30 句（業主核、五欄×6、`presales_gate.IDENTITY_REASK_PATTERNS` 唯讀映射＋`reask_hits` NFKC 雙側子字串）＋`test_identity_no_reask_req.py` 21 案（非空守門、anonymous 正例／清空必紅、**entry 否定斷言收窄到 identity 欄＋已知槽位欄**（業主以「你好我有需求」案例定案：未知欄位補問合法）、不進 prompt AST＋文字掃描、NFKC 雙側）；verifier CONFIRMED（獨立解析草稿逐列相等、兩種突變各紅 9、誤殺類「有興趣的功能」「有什麼困擾」如預期命中＝(b) 先留著量）；unit 1201／integration 210／audit PASS；主張範圍＝agent 路徑內不重問（F-10 舊鏈重問留債）。S2a 程式面 2026-09-07 收案：Plan `inputs/plan-m-d-runtime-wiring-20260907.md` §4（security-reviewer 13 條＋plan-verifier 兩輪＋收尾審查逐條 FIX、業主核 §4.4）；security-executor＋fresh verifier CONFIRMED 22 探針；unit 1180／integration 210／audit PASS；design 1.17。**S2b 待業主核句型表** `inputs/identity-reask-patterns-draft-20260907.md` → `IDENTITY_REASK_PATTERNS`＋`test_identity_no_reask_req.py`；TDD）：`run_turn` 在 `_slots_for_prompt(state)` 後**強制覆寫** `slots["identity"]=identity.resolved_audience()`、`identity_source ∈ {entry, anonymous}`；`SlotKey` 加 `identity_detail`／`team`／`pain`／`interested`（票 B；`identity` ⛔ 不入 enum）；`tests/unit/agent/test_identity_no_reask_req.py`（entry 回合不得含身分反問句型；**正對照**：anonymous＋分叉正例句型表須匹配得到，清空句型表必紅）；AST 測試禁止 `slots["identity"]`／`identity_detail` 流向 `jgb2.*`／`kb.*` 參數；契約測試：模型經 `slots_set` 寫任何值後 prompt 的 `identity` 仍為 entry 值。 **句型表（定義不足已補）**：封閉「身分反問句型」由 executor 依 kb 3645 五欄位（identity／scale／team／pain／interested）草擬（每欄位 ≤6 句型、NFKC、定義不寫例子進 prompt、句型只用於測試與掃描），落 `services/presales_gate.py` 同層常數，**業主核可後**才寫測試。
  - 需求：4.1, 4.2, 4.3, 8.2
  - 執行：security-executor／effort 中——身分強制覆寫＝附錄 E F9／F10（identity／trust boundary，DSP-011）；完成後派 fresh verifier
  - 驗收：目標＝身分由入口派生、模型寫不到｜成果＝強制覆寫＋SlotKey 四值＋契約測試＋句型表｜做法＝TDD｜驗證＝[業主審核] 句型表；[代理驗證]（claim：模型寫入後 prompt 仍為 entry 值）
- [x] 4.3 (P) `tools/agent_eval.py` 擴充（**2026-09-07 收案**：Plan `inputs/plan-m-d-runtime-wiring-20260907.md` §3（plan-verifier 兩輪 REVISE＋收尾審查共 6 P2 逐條 FIX、業主核 §3.5）；mech-executor＋兩次補刀（真 provider on 臂 selector 真接線；`_require_openai_key()` 先於索引）＋fresh verifier CONFIRMED（22 探針：兩臂形狀、fallback／selector_error 由 `candidate_violations` 分辨、key 檢查→索引→就緒閘門 exit 5→`build_real_runtime(candidate_selector=)`、outline-probe exit 4／3、28 鍵、無 env 讀）；unit 1064；P4 三條留紀錄：`--chain old` 仍印 candidates 節、`--chain both` fallback 分母含 old 列、真／假臂 kwarg 不對稱）：`--candidates {on,off}`（評估專用 DI，off ⇒ `build_runtime(candidate_selector=None)`；⛔ 不讀 env）、`--set outline-probe`（新 loader＋manifest 登記）、JSONL 加 `candidate_ids`／`miss_kind`／`candidates_mode`（同步點＝`rag-orchestrator/tests/unit/agent/test_agent_eval_req.py::_EXPECTED_JSONL_KEYS`，實查在測試檔非工具本體）、report 加 `candidate_fallback` 回合數／`avg_candidates`。測試：`test_agent_eval_req.py` 同步鍵集合；manifest 未登記 set exit 3 不變。
  - 需求：6.2, 6.3, 6.4
  - 執行：mech-executor／effort 中——擴充點在既有 argparse／loader（`--set` choices 現為 topics/scenarios/sensitive/traffic）
  - 驗收：目標＝評估工具能跑兩臂與新樣本集｜成果＝三個旗標＋JSONL 鍵同步｜做法＝擴 argparse／loader｜驗證＝[自驗]
- [ ] 4.4 步 2 探針（**2026-09-07 已跑一輪、推翻條件命中、⛔ 不打勾**：4.4a 定義 `inputs/plan-4.4a-outline-probe-definition-20260907.md`（業主核）＋題集凍結 `eval/outline-probe-20260907.json`（36 題／49 turn，sha 22aa2c10…）＋受測物 `inputs/object-under-test-outline-probe-20260907.md`；4.4b 報告 `inputs/probe-report-20260907.md`：H1 翻轉 1/10、H4 無據 on 4/34 > off 1/23 ⇒ 命中；候選層通過（gold 在前五 0.906、violation 0）、回答層未通過（直接 no_grounding、三段式畸形 ref、敏感過度分類）；H7 內文臂 +4.3 未命中；成本 $0.63。**處置＝業主 2026-09-07 起 5.1；5.1 收案後以同一凍結題集重跑，翻轉 ≥50% 才打勾**。**5.1 重跑（同日，`inputs/probe-report-51-20260907.md`）**：翻轉 3/10、答到 21→46、直接 no_grounding 64→39、畸形 ref 48→6、C 層 on 0.93 vs off 0.47、H4 無據 5.6%（↓）、對照組 0、敏感 0 漏；未過三門：翻轉 <5、budget_exhausted 22（拒因改為 QUOTE_NOT_COVERING）、邊界硬答 6/15（其中 5 回合盲標有據＝標籤過時）。仍不打勾。**換模型 gpt-5-mini（同日，`inputs/probe-report-52-20260907.md`，只跑 on 臂 $0.83）**：答到 46.9%、直接放棄 3、A 層 7/10 答到／4/10 引 gold、無據 0/117、敏感 0 漏；未過：翻轉差 1、budget_exhausted 35（極性 21／覆蓋 21 拒因）、邊界 9/15（盲標全有據）、**p95 延遲 38 s**（gpt-5 預設推理、runtime 無 `reasoning_effort`）。下一刀待裁：runtime 加 `reasoning_effort` 重量／極性尺離線量測／下次凍結重標邊界＋「答到」限 `kind=answer`。H5 邊界整數線 vs 同批對照、H3 兩臂皆低於 round9 兩項待裁；4.1–4.3 後；<$0.5→業主上修 $0.7）：**分兩段派工**——4.4a 定義與凍結（跑前，[業主審核] 後才起 4.4b）、4.4b 實跑與盲標。先寫 `inputs/object-under-test.md`（知識正本 sha、`agent_rules.py` 版本、覆蓋來源、材料能證／不能證、事實 vs 待裁）＋假設表（命題／最小材料／尺／推翻條件／費用）交業主核；新選 ≥30 題（可答卻沒答／gold 不在候選對照／已能答／敏感／邊界／多輪／跨粗目）跑前凍結入 manifest（round9 13 題只作對照）；`--chain agent --candidates on/off --repeat 3`；盲標 2 判者走 `answer-acceptance-verify`（同批同判者、封包不標 arm）；報翻轉率／對照組維持轉人／引用細目＝gold／無據率；推翻條件：翻轉 <50%、對照組被答到 ≥2、已能答變差 ⇒ 停下回主 session，⛔ 不調參。 **選題規則（定義不足已補，跑前凍結）**：母體＝422 句問法（`inputs/phrasing-selection-rule-20260906.json`）＋缺口地圖 55 格代表問句；分層：可答卻沒答（依 round9 answerability 標籤）≥10、gold 不在候選對照 ≥5、已能答 ≥5、敏感 5、邊界 5、多輪 3、跨粗目 3；每層以 `md5('outline-probe-20260906:'+q)` 升冪取前 N；規則與 sha 落 `inputs/outline-probe-selection-rule.json` 並登記 manifest；⛔ 抽完不得改。
  - 需求：6.1, 6.2, 6.3, 6.4, 6.5, 6.6
  - 執行：main／effort 高——受測物定義與假設表屬主 session；盲標派獨立代理 ×2（G4）
  - 驗收：目標＝證明候選＋身分讓「查無」轉回答且不猜｜成果＝受測物定義清單、假設表、凍結題集、探針報告｜做法＝兩臂 ×3 rep、盲標同批同判者｜驗證＝[業主審核] 定義清單＋假設表（跑前）；[代理驗證]×2 盲標；推翻條件命中 ⇒ 回主 session

## 5. M-e 對話邏輯：定義搬遷、CTA／handoff、敏感程式側、步 3 劇本（5.1 先做；5.2／5.3 平行；5.4 待 D2；5.5 後）

> **階段目標**：售前對話邏輯以定義搬進 agent，CTA／轉人由程式與設定供給。**成果**：`agent_rules.py` 定義版、CTA／handoff 接線、步 3 劇本契約全綠。**驗證**：劇本 [代理驗證]；5.4 待 D2 [業主親跑]。

- [ ] 5.1 `agent_rules.py` 定義搬遷（TDD）：`_POLICY_TEXT` 改三段定義（判準：A 事實題直答／B 推薦題補問，補問欄位封閉集合、一次一題、已知不重問、基本資訊門檻 identity＋(scale 或 pain)；已推薦後三態；fact_class 七值＋「句形不是判準」）；「入口已帶身分者不得反問身分」定義句；`persona_provider(identity)` 依 `resolved_audience()` 三分支；⛔ 不寫例子（裁定 13）。測試：prompt 快照測試（三分支）；R1.3 回歸鎖（`kb_search=None` 路徑逐字不變）不適用 agent 路徑但 `test_prompt_assembler_req` 白名單測試須綠。
  - 需求：4.4, 4.7
  - 執行：executor／effort 中——來源＝kb 3645 原文（`inputs/kb3645-…md`），改寫為定義需判斷
  - 驗收：目標＝對話邏輯以定義搬入、persona 分支｜成果＝`agent_rules.py` 定義版＋快照測試｜做法＝從 kb 3645 改寫為定義句｜驗證＝[業主審核] 定義文（它就是 prompt）
- [ ] 5.2 (P) CTA 程式端與 handoff 設定接線（TDD）：`_finalize` 前，`out.kind=="recommend"` 或 `explicit_action(user_message)`（封閉詞表：預約／試用／留資／方案）⇒ 附加由 `conversational_config.cta_rules` 提取的固定 CTA 段（連結由程式給，模型不寫）；`_build_fixed`／handoff 分支改 `effective_handoff_message(cfg)`／`effective_handoff_channel(cfg)`，`cfg` 由 `config_for_target_user(db_pool, identity.target_user)` 啟動時快取、隨 `conversational_config` 快取失效。測試：CTA 只在兩種情況出現（一般追問不附）；DB 覆寫 handoff 文案時 agent 回合用 DB 值（正對照：無覆寫用 code 保底）。
  - 需求：4.5, 4.6
  - 執行：executor／effort 中——接線點明確（`runtime.py` 兩處 `effective_handoff_message(None)`）
  - 驗收：目標＝CTA／轉人由程式與設定供給｜成果＝兩處接線＋測試｜做法＝`config_for_target_user` 啟動快取｜驗證＝[自驗]
- [ ] 5.3 (P) 敏感判定程式側為準（tasks 4.8 移交）：`sensitive_patterns` 命中 ⇒ 敏感出口，模型 `fact_class` 敏感值只作建議；量尺＝敏感 0 漏不變＋誤標敏感回合數（topics 現 12/324）。測試：第一人稱情境句（fixture 既有）不再因模型誤標而轉人；敏感 fixture 全紅。
  - 需求：5.7
  - 執行：executor／effort 低——規則已在 `presales_gate.SENSITIVE`／verifier 步①，只調優先序
  - 驗收：目標＝敏感以程式規則為準｜成果＝優先序調整＋fixture｜做法＝既有 `SENSITIVE`｜驗證＝[自驗]（敏感 0 漏由 5.5 劇本再驗）
- [ ] 5.4 票 A：部分回答＋帶理由轉人（**待 D2**；步 2／3 探針證明需要才起）：`AgentOutput` 允許 `kind=answer` 且 `handoff_reason` 非空；Verifier 步② 對 `kind=routing` 的轉人句免引用、`fact` 句照驗；fixtures 雙向釘（放行一例＋拒一例）。
  - 需求：5.8, 8.1
  - 執行：security-executor／effort 中——動輸出契約與 Verifier 分支（平台層）；前置：業主裁 D2＋security-reviewer 前置審
  - 驗收：目標＝一回合部分回答＋轉人並存｜成果＝契約＋Verifier 分支＋fixtures｜做法＝待 D2｜驗證＝[業主親跑] 裁 D2；security-reviewer 前置；[代理驗證]
- [ ] 5.5 步 3 劇本探針（5.1–5.3 後；~$0.3）：六套劇本（事實直答／推薦補問／已推薦三態／中途岔題／身分不重問／敏感）＋LINE 口語材料（6.2 產出者可先用文件輸入句）；契約測試：A/B 判對率、一次一題、身分不重問、CTA 只在收斂、零捏造；任一契約紅 ⇒ 停下。 **六套劇本（定義不足已補）**：每套 3–5 輪、逐輪寫「期望動作」（⛔ 非字句）：①事實直答（問功能→`answer` 且引用細目）；②推薦補問（模糊需求→`ask` 一題→補 identity→補 scale→`recommend`＋CTA）；③已推薦三態（接受→簡短收尾無 CTA；追問→`answer` 無 CTA；換題→照一般規則）；④中途岔題（推薦中插價格→`handoff sensitive`／插功能→`answer` 再接回）；⑤身分不重問（pm 入口問功能→不得出現身分反問）；⑥敏感（五類各一句→`handoff sensitive_no_grounding`）。劇本檔 `inputs/scripts-step3-20260906.json` 跑前凍結、業主核可。
  - 需求：6.3
  - 執行：main／effort 中——收案判斷屬主 session；劇本跑派 verifier 實跑
  - 驗收：目標＝流程正確性契約化｜成果＝六套劇本檔＋契約測試報告｜做法＝逐輪期望動作｜驗證＝[業主審核] 劇本；[代理驗證] 實跑

## 6. M-f 閉環與 LINE：地圖重量、LINE 正本、可見性契約、skill 整合（6.1／6.4 平行；**6.2 待售前驗證有效後才開**（業主 2026-09-06 裁）；6.3 依 6.2）

> **階段目標**：覆蓋閉環工具化、LINE 受眾正本草稿、可見性契約。**成果**：coverage_map 完整版、`property_manager-line.md` 草稿、LINE 可見性測試。**驗證**：6.2 [業主審核]；6.3 [代理驗證]。

- [ ] 6.1 (P) `coverage_map.py` 完整版：判者一致率欄（`judge_agreement`）；`answered`／`answered_handoff` 由 `agent_eval` 實跑回填 entry_state；批次放行後重組上下文文件並重量，報告格狀態變化；每格 `min_verification`（哪幾句問法、預期細目）。測試：假 answerability 與 demand 的重量決定性；無去向格 ≠0 ⇒ exit 2。
  - 需求：3.4, 3.6
  - 執行：executor／effort 中——2.6 的延伸
  - 驗收：目標＝閉環可重量、判者一致率可見｜成果＝完整版工具｜做法＝2.6 延伸｜驗證＝[自驗]
- [ ] 6.2 LINE 正本草稿（**前置：業主 2026-09-06 裁「先用售前大綱驗證，合理有效果才補其他大綱、開始切」——需 4.4 步 2 探針（翻轉率／無據率）與 7.4 放量門檻證明售前大綱有效，並由業主點頭；⛔ 不與 M-b～M-e 並行**）`rag-orchestrator/canon/property_manager-line.md`：粗目依 chatai 四文件（③損壞分類與判定／④語氣模板與禁止項／⑤帳單狀態語義與資料邊界／⑥什麼時候說不／⑦待裁與待驗）；API 實值以 `policy: not_available`＋`sources: [jgb2:<endpoint>]`，內容只寫邊界句；矛盾三項（emergency_status 值域、image_recognition 回傳、`status-overview` 過濾）列「待裁決／待驗」；21 案例知識類 5 案＋文件實際使用者輸入句 → `inputs/line-phrasings-20260906.json`（照抄、標情境與多輪、去識別）。走同一 skill 流程（步 1–6）產草稿交業主審。**分兩段派工**：6.2a 粗目與待驗清單、6.2b 口語材料檔。
  - 需求：7.1, 7.2, 7.3, 7.5, 7.6
  - 執行：executor／effort 中——材料在 `/Users/lenny/jgb/line-bot-platform/docs/chatai-*.md`；⛔ 不套售前切法（裁定 2）
  - 驗收：目標＝LINE 業務受眾知識層正本草稿｜成果＝`property_manager-line.md` 草稿＋口語材料檔｜做法＝同一 skill 流程｜驗證＝[業主審核] 草稿與待驗清單
- [ ] 6.3 LINE 可見性契約測試（6.2 後）：先一次 SQL 對照 `Identity(vendor_id=0, target_user="property_manager", mode="b2b")` 的可見集合（正對照：pm 可見 285）；`tests/unit/agent/test_line_visibility_req.py`：`FineIndex.visible_subset` 與 `build_visibility_predicate` 對衍生列的集合相等；缺 `vendor_id` 入口填 0 的行為明文。
  - 需求：7.4
  - 執行：executor／effort 中——可見性觸發 ⇒ 完成後派 fresh verifier
  - 驗收：目標＝LINE 入口（vendor_id 缺→0）可見集合明文且與 SQL 相等｜成果＝SQL 對照＋契約測試｜做法＝正對照 pm 285｜驗證＝[代理驗證]
- [ ] 6.4 (P) `retrieval-improvement-loop` 整合（agentic-mcp 5.5 移交）：本 skill steps/05／06 以連結引用該 skill 的 `rules/`（G0＝`rules/正解判定.md`、G2＝`rules/量測管線自證.md`、G4＝`rules/代理分工.md`，⛔ 不複製）；量測步改「以細目為單位重跑 `agent_eval`，輸入正本 sha、輸出每粗目／細目的可答率與無據率」；該 skill 只追加 agent 分支段落、⛔ 不刪既有。
  - 需求：1.10
  - 執行：mech-executor／effort 低——文件性整合，內容已定
  - 驗收：目標＝兩支 skill 共用閘門不複製｜成果＝連結式整合文字｜做法＝只追加｜驗證＝[自驗]

## 7. M-g 入庫與上版：導出、匯入 fail-closed、D1 執行包、放量、收尾（7.1 先做；7.2 後 7.3；7.5／7.6 平行）

> **階段目標**：正本入庫（D1）、放量門檻凍結、平台票與收尾。**成果**：匯入 fail-closed、D1 執行包、步 4 報告、agentic-mcp 收尾。**驗證**：7.2 [代理驗證]；7.3／7.4 [業主親跑]＋[業主審核]。

- [ ] 7.1 `tools/canon/export_batch.py`（TDD；**業主 2026-09-07 裁（3.3 §8.2）：正本 `business_types`／`target_user` 空清單 ⇒ 批次寫 `null`、7.2 匯入 ⛔ 不預設 `system_provider`，與記憶體 `canon_visible` 的「空＝不設限／b2b 空⇒不可見」對齊 SQL `IS NULL`**）：`CanonDoc`＋`replacements` → 匯入批次 JSON（`knowledge[]`：`question=title`、`answer=content_units 逐行`、三軸自細目、`instance_applicability`、`approved_by="reviewed:<reviewer>"`、`canon_ref`、`replaces[]`；**首批 ⛔ 不寫 `keywords`**；`updates[]`：舊列 `replaced_by`＋`outline_approved_by="pool-marked-<date>"`＋`expect_current`（export 當下 DB 快照）；頂層 `canon_sha256`；rollback SQL 由逐列 pre-image SELECT 快照生成）。測試：同正本兩次逐位元相等；rollback 逆轉每欄原值。
  - 需求：1.9, 2.7, 2.9
  - 執行：executor／effort 中——批次格式沿既有工具契約
  - 驗收：目標＝正本→批次決定性、rollback 有 pre-image｜成果＝`export_batch.py`＋測試｜做法＝沿匯入契約｜驗證＝[自驗]
- [ ] 7.2 `import_facet_knowledge.py` 擴充（7.1 後；security-sensitive）：批次 `canon_sha256` 必等於工具當下由 `rag-orchestrator/canon/<audience>.md` 重算值；每筆 `answer` 與 `canon_ref` 細目 `content_units` 逐字相符、`approved_by` 等於細目 `reviewed_by`；`updates[]` 先讀 DB 現值比 `expect_current`；任一不符整批不寫、exit 2；冪等鍵改 `generation_metadata->>'canon_ref'`（`run()` 兩處 `question_summary=$1`）；`--dry-run` 印逐筆比對與影響列數；⛔ 不動 `seeds.manifest`。測試：改一字必紅；dry-run 對 `aichatbot_test` 影響列數＝已審細目數；rollback 逆轉。
  - 需求：2.7
  - 執行：security-executor／effort 高——這是「內容已審」標記的唯一寫入口；完成後派 fresh verifier
  - 驗收：目標＝「內容已審」唯一寫入口 fail-closed｜成果＝匯入擴充＋dry-run 比對｜做法＝sha＋逐筆＋現值比對｜驗證＝[代理驗證]（claim：改一字必紅、dry-run 列數＝已審細目數、rollback 逆轉）
- [ ] 7.3 D1 執行包（業主跑；7.2 後、正本已 commit）：逐條指令＋預期輸出：① `make audit`（前）；② `python3 rag-orchestrator/tools/import_facet_knowledge.py scripts/knowledge-batches/canon-prospect-<date>.json --dry-run`（預期 `canon_sha256 ✅ 相符`、逐筆 `✅ content match`、`knowledge N／updates M`）；③ 不帶 `--dry-run` 重跑（無 `--apply` 旗標）；④ migration `20260906_outline_approved_by_domain.sql` 經 `database/migrate.sh`（dry-run → apply）；⑤ `make audit`（後；預期：不變量 10 對本批列有反應（runbook 標明）；不變量 32／33 由 `SKIP(pending-D1)` 轉為實跑且 PASS）；⑥ `GET /api/v1/agent/health` 核 `canon.canon_sha256`＝版控、`index_state=ready`；⑦ semantic-model 重建（舊鏈仍讀衍生列）。rollback 檔路徑同列。
  - 需求：2.7
  - 執行：main／effort 中——prod 破壞性操作不代跑、不打包腳本（記憶 `feedback_prod_ops_self_run`／`feedback_no_deploy_scripts`）
  - 驗收：目標＝D1 安全落地｜成果＝七步指令＋預期輸出＋rollback 路徑｜做法＝逐條、不打包｜驗證＝[業主親跑] 全部；[業主審核] health 三值
- [ ] 7.4 步 4 放量（需 D3 材料＋7.3 後）：**前置**——樣本 C（真流量）現況缺席（F13）：由 `usage_events`／對話紀錄匯出 prospect 問句 → 2.2 去識別流程 → 登記 `samples-manifest.json`（sha 凍結）→ 業主授權；**stop：樣本 C 未備妥 ⇒ 7.4 不起跑、回主 session，⛔ 不以幫助中心問法代替（R6.7）**。探針結果後、放量前凍結門檻（依受眾×問法型答到率／無據率／不硬答／敏感 0 漏）交業主核；`--set traffic`（樣本 C）；報表標每 arm 的 production 組態；比較性結論 ≥30 題。
  - 需求：6.6
  - 執行：main／effort 高——門檻凍結與收案判斷屬主 session；療效數字派獨立 verifier
  - 驗收：目標＝放量門檻先凍結再跑｜成果＝門檻文件＋步 4 報告｜做法＝`--set traffic`（需 D3 材料）｜驗證＝[業主審核] 門檻（跑前）；[代理驗證] 數字
- [ ] 7.5 (P) agentic-mcp 收尾（文件）：DECISIONS 新列一條 DSP 收窄該 spec 為平台層、DSP-035 撤回留檔；該 spec tasks 4.6 標撤回、4.7／4.8／5.5 標移交本 spec（對應 3.3／5.3／6.4）；requirements R5「不用向量檢索」等四處以本 spec 註記（⛔ 不刪原文）。
  - 需求：8.5, 8.6
  - 執行：mech-executor／effort 低——內容已在 design 決策表
  - 驗收：目標＝agentic-mcp 邊界收窄留檔｜成果＝DSP 一列＋四處註記｜做法＝只註記不刪｜驗證＝[自驗]
- [ ] 7.6 (P) 平台需求票登記：在 `agentic-mcp-orchestration/tasks.md` 追加 A（D2 後）／B／C／D／E 五票，各附本 spec 依賴任務（4.2／4.1／3.1／5.4）與收窄後實作量；⛔ 不在本 spec 偷改平台層。
  - 需求：8.1, 8.2, 8.3, 8.4, 8.5
  - 執行：main／effort 低——跨 spec 協調屬主 session
  - 驗收：目標＝平台票有落點與依賴｜成果＝五票登記｜做法＝跨 spec 追加｜驗證＝[業主審核]（排程屬業主）

- [ ]* 8.1 補充測試（可延後）：`index_eval` 三臂結果的凍結物 sha 測試；`coverage_map` 跨受眾改寫草稿的格式測試；LINE 口語材料去識別回歸。
  - 需求：6.4, 3.6, 7.6
  - 執行：mech-executor／effort 低
  - 驗收：目標＝補充回歸｜成果＝三組測試｜做法＝可延後｜驗證＝[自驗]
