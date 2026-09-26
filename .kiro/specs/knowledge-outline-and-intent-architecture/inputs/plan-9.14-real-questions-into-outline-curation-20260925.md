# Plan 9.14：真實客服問句接進 outline-curation（步 4 → 5 → 5b）— 2026-09-25 第 4 稿

> 第 2 稿＝第 1 稿＋security-reviewer（2026-09-25）P1×3／P2×2／P3×2 全數 FIX（§7）。
> 第 3 稿＝plan-verifier 第 1 輪：
> - 大綱 REVISE 3 條 P2：P1 計數與判定先定、184 格四桶去向、成本量尺改 `subagent_tokens`＋試跑
> - S0＋S1 REVISE P1×1／P2×1：守門改標記檔圍欄以適用無 `.git` 的容器、單一實作 `tools/text_containment.py`
> - 全數 FIX（§8）。
> 第 4 稿＝plan-verifier 第 2 輪：大綱 READY；S0＋S1 第 2 次 REVISE（P2×3），主 session 逐條裁決全 FIX（§9）：定位不依賴 cwd、單一旗標鍵、圍欄不得落在 rag root 下。

> 業主 2026-09-25：「不能整合 outline-curation 讓也能判出缺口？」→「補進 skill？」→「寫計畫」。
> 起因：Plan 9.13 另外臨時做了一套可答性判定——三批各 1 位判者，Plan 9.13 §11 自己記了「判者間口徑不一」，事後只抽 45＋40 題複核，缺口歸類 `gaps_categorized.json` 也在修正前產出、已經過期。而 skill 步 4 本來就是同一件事，而且比較嚴：2 位判者互不可見、不一致才加第 3 位、Reconcile 門檻 0.80、rubric v0.2.0 已經業主 2026-09-06 核可。步 5b 還有業主 2026-09-07 的裁定：「⛔ 未核對不得交業主」。
> ⛔ 本 Plan 不動 runtime、selector、正本內容；不 commit、不部署。題目文字 ⛔ 不進 git（沿用 Plan 9.13 P0 決定一 (a)；repo 公開）。
> 上游：`plan-9.13-real-cs-questions-20260924.md` §11（凍結後 no_canon 184 題）。

## 0. 受測物與命題

- **受測物**：Plan 9.13 凍結的 no_canon 184 題（repo 外 `~/jgb-archive/ruler-9.13/no_canon.json`：`property_manager` 179、`prospect` 5），對照正本 `rag-orchestrator/canon/jgb`（`canon_sha256` 開頭 `9b67e763e9c5`，515 細目，`sources` 為空的 0 條）。
  - 9.13 的「歸類者疑判錯 4 題」是 `gaps_categorized.json` 裡 `maybe_answered` 旗標的題，本來就在這 184 題內。「審題者多抓的 4 題」也已在凍結時併入 184。⇒ **範圍就是這 184 題，不另外加題**。
- **P1（驗 9.13）**：用步 4 重判後，184 題中還有幾題是缺口？（9.13 判的是 184/184，也就是缺口率 48.3% 的分子）
  - **計數定義（先定、看結果不改；plan-verifier 第 1 輪 #1）**：`answerability_agents.py::reconcile` 會把三位判者都對不上的格也終判成 `no_source` 並標 `unresolved`。所以五類分開數，五類加總必須＝184：
    - **N_ns**：已決的 `no_source`（沒有 `unresolved` 旗標）
    - **N_un**：`unresolved`
    - **N_pa**：`partial`
    - **N_an**：`answerable`
    - **N_dn**：`deliberate_no`（本案所有格 `policy` 為空，依 rubric 應為 0；>0 ⇒ 視為判者錯誤、併入 N_un）
  - **對 9.13 的對應**：9.13 是全有全無的二分法。
    - 「仍是缺口」＝ N_ns ＋ N_pa：`partial` 是正本只答一部分，其餘部分仍缺
    - 「9.13 判錯」＝ N_an
  - **判定（先定）**：
    - N_un ＞ 18（＞10%）⇒ P1 記 **INCONCLUSIVE**，只報數字，⛔ 不修改 9.13 的結論
    - 否則 N_an ≤ 18 ⇒ 9.13 的 48.3% **成立**，並以 (N_ns＋N_pa)／381 報修正值
    - 否則 N_an ＞ 18 ⇒ 9.13 的缺口判定**不可靠**，改報新值 (N_ns＋N_pa)／381，並記進 Plan 9.13 §11
    - 分母 381 裡的 197 題 gold 未重判（見「證不了」）。
- **P2（缺口去向）**：`no_source` 的題經 5b 對源後，分成三種：
  - `verified_fact`：產品有做，但正本沒寫 ⇒ 補知識
  - `verified_absent`：產品沒有這個功能 ⇒ 列進 I 架「目前不支援」
  - `owner_needed`：盤查完仍定不了 ⇒ 只有這種交業主
- **證不了**：
  - 155 題未複核 gold 裡藏著的缺口：9.13 抽樣 45 題中 4 題其實是缺口，約 9%，推估約 14 題。ruler-9.13 已凍結、永不修改，這部分本 Plan 不重判。
  - 檢索層：A0／A3 已另外量過。
  - 回答品質。
  - 租客。

## 1. 已查證的前提（決定設計用；每條可重跑）

| # | 事實 | 查證 |
|---|---|---|
| F1 | 步 4 的格只取 `id`／`questions[0]`／`policy`／`policy_ref`；其他已知欄位靜默丟棄，未知欄位 raise ⇒ 真實問句一題＝一格 `{id, questions:[q], policy:""}` 可直接吃 | `.claude/skills/outline-curation/scripts/answerability_args.py::project_cell`、`_CELL_ALLOWED`、`KNOWN_SYSTEM_FIELDS` |
| F2 | `--canon` 模式把**全部細目**當候選，不篩受眾、不排序 | `answerability_args.py::candidates_from_canon` |
| F3 | 候選區塊大小（容器內真 tokenizer `services.agent.outline._count_tokens`）：全部 515 條 136,051 token；`property_manager` 可見 509 條 134,558 token；`prospect` 可見 112 條 29,836 token | 容器內 `canon_items.parse_canon_auto('/app/canon/jgb')` 後依 `target_user` 分組計數（本 Plan 附錄 A 指令） |
| F4 | 分組 prompt 的順序是 rubric → 本組各格 → 候選 → 輸出說明；每組 2 個 slot 的內容逐位元相同 | `answerability_agents.py::build_group_prompt`、`cmd_prepare` |
| F5 | 判者原文輸出落在 `--out-dir`（`prompts/*.prompt.md` 含問句）；第 3 判者 prompt 也在同一目錄 | `answerability_agents.py::cmd_prepare`、`cmd_collect` |
| F6 | 步 5 的 `coverage-map.json` 會把問句原文寫進 `min_verification.phrasings`；5b 的 worklist 也會把它寫進 `items[].question` ⇒ **這兩份也含客戶文字** | `rag-orchestrator/tools/gapmap/coverage_map.py::reweigh`、`source_audit.py::build_worklist` |
| F7 | `finalize_answerability.py`／`reweigh.py`／`source_audit.py check` 都寫同一份狀態檔 `.claude/hooks/state/outline-gate/session.json`（已在 .gitignore）；該檔**目前存著主線大綱的 `answerability`／`reweigh`／`source_audit` 鍵** ⇒ 直接跑會蓋掉主線的閘門狀態 | `_envelope.py::state_file_path`、`update_state`；`python3 -c "import json;print(sorted(json.load(open('.claude/hooks/state/outline-gate/session.json'))))"` |
| F8 | `g0.authority` 為 `none` ⇒ `no_source` 一律落 `not_available` ⇒ 全部進 5b worklist（5b 本來就是判「權威來源裡有沒有」的那一步） | `coverage_map.py::_decide`、`has_authority`、`AUTHORITY_NO_PREFIXES` |
| F9 | 量測層 stub：`cause_state="NOT_MEASURED"` ⇒ `coverage_map` 不判任何 gap class；檢索缺口由 ruler-9.13 A0／A3 另外量 | `surface_to_cells.py` 檔頭「量測層 map」、`coverage_map.py::is_retrieval_gap` |
| F10 | 識別碼掃描 hook 只在 Edit／Write 命中 `rag-orchestrator/canon/**.md` 或 `.claude/skills/outline-curation/runs/` 時觸發；**事實帳本 `docs/knowledge/jgb-product-facts.md` 不在掃描範圍**，而 5b 會把事實寫進它（公開 repo） | `.claude/hooks/outline_gate.py::CANON_RE`、`RUNS_RE`、`check_identifiers` 的呼叫點 |
| F11 | 5b 預設權威來源是 jgb2 `master`；但本線正本與 drafts 都釘在 `b2ee2ac382ce`，而 master 已經領先 85 個提交 ⇒ 兩者衝突，已記成 **DSP-071（unresolved）** | `source_audit.py::DEFAULT_AUTHORITY`；`HANDOFF-20260923.md` §7；`steps/00c-topic-first-drafting.md`「來源」 |
| F12 | 步 4 預算：SKILL.md front matter `answerability.agents: 180`；步驟文件寫「≤180 代理／$3」——這條是在候選只有 ~7k token 時訂的（`answerability_agents.py` 檔頭「rubric＋候選 ≈7k token」） | `.claude/skills/outline-curation/SKILL.md`、`steps/04-answerability.md` 出口條件 |
| F13 | 並行上限：主 session 每次最多 4 個子代理（8 GB 機器 ≥10 並行會整機重開） | `steps/04-answerability.md` 形態段 |

## 2. 切片

### S0 — .gitignore 補洞（S1 的前置條件；security-reviewer P1-2／P3-7）

- `.gitignore` 加三行：
  - `.agents/skills/outline-curation/raw/`
  - `.agents/skills/outline-curation/journal/`
  - `.codex/hooks/state/`
- 理由：`.agents/skills/outline-curation/raw/` 目前**沒被忽略**，裡面約 150 個檔，含 `phrasing-20260906/candidates-raw.json`、`trial-20260906/judge-openai-55.jsonl`、`answerability-20260907/prompts/*`（`.gitignore` 對 `.claude/` 同名目錄的註解是「講法原始候選（去識別前）」）。S1 第 5 步要同步 `.agents/` 鏡像，之後任何一次 `git add .agents/skills/outline-curation` 都會把它帶上公開 repo。
- 驗收：
  - 三條路徑 `git check-ignore -v <路徑>/x` 各自命中新規則
  - 正對照：`.claude/skills/outline-curation/raw/x` 仍命中原規則
  - `git status --porcelain` 不再列出這三個目錄
- ⛔ 不刪、不移動目錄內任何檔（內容去留另由業主定）。

### S1 — skill 補「真實問句進場」入口（程式面，⛔ 不跑任何判者）

改動只限：
- `.claude/skills/outline-curation/`（加 `.agents/` 鏡像）
- `rag-orchestrator/tools/gapmap/coverage_map.py`
- 新檔 `rag-orchestrator/tools/text_containment.py`
- 新測試

1. **新腳本 `scripts/real_questions_to_cells.py`**
   - 輸入：遮蔽後題目 JSON `[{id, q, audience}]`（本案＝9.13 `no_canon.json`）。
   - 輸出：依受眾各出一份
     - `cells-<audience>.json`：`{_meta:{text_policy:"external", source_sha256, audience, n}, cells:[{id, questions:[q], policy:"", module:"", topic:"", g0:{authority:"none"}}]}`
     - `map-<audience>.json`：`{cells:[{id, cause_state:"NOT_MEASURED", entry_state:"", coverage:""}]}`
   - `--out-dir` 的 realpath 任一祖先有 `.git` ⇒ 非 0 退出並印原因；否則在該目錄建立標記檔 `.text-external`（見 3.）。
   - 在主機執行（只讀寫 JSON）。
   - stdout 只印筆數與 sha。
   - `topic` 留空：⛔ 不寫任何題目衍生字。
2. **`answerability_args.py` 加 `--target-user <aud>`**（選填；預設行為不變）
   - 把 `candidates_from_canon` 的結果篩成 `target_user` 含該受眾的細目；篩選條件記進 `inputsSha.candidateFilter`。
   - 理由：Plan 9.13 §3 定過「只能從該受眾看得到的細目裡選」。
   - 同時把 cells 的 `_meta.text_policy` 原樣寫進 args 的頂層 `_meta`（鍵名不變）。
3. **客戶文字不落 repo 的守門（fail-closed；security-reviewer P1-1／P2-4；plan-verifier 第 1 輪 S1 #1／#2 改寫）**
   - **設計：正向圍欄（標記檔），不靠偵測 `.git`**。理由：測試容器沒有掛 `.git`，而且 `find_repo_root()` 在容器內會停在 `/`（因為 `/.claude/settings.json` 有掛載），所以任何「以 git 工作樹判斷」的規則在主機與容器會得出不同結果，也會讓既有測試轉紅。
   - **標記檔**：`.text-external`（空檔）
     - 只由轉換器 `real_questions_to_cells.py` 在它的 `--out-dir` 建立
     - 轉換器在**主機**上執行（只讀 JSON、不需要容器）
     - 建立前檢查：`--out-dir` 的 realpath 任何祖先有 `.git`（目錄或檔）⇒ 非 0 退出
   - **觸發條件**：該 CLI 的**任一個輸入檔參數**符合下列任一條即觸發
     - 內含 `_meta.text_policy == "external"`
     - 該檔的 realpath 任一祖先目錄有 `.text-external`
   - 第二條讓 `_meta` 在某環節掉了時仍然觸發（security-reviewer P2-4）。
   - **觸發後的規則**：輸出路徑（檔的父目錄，或 `--out-dir` 本身）的 realpath 必須有一個祖先含 `.text-external`，否則 raise 並非 0 退出。
     - 這是「必須落在圍欄內」的正向條件：找不到圍欄一律拒絕，與 repo 根找不找得到無關。
     - symlink 以 realpath 處理。
   - **未觸發**（沒有任何輸入帶標記或 `_meta`，即既有流程）⇒ 完全不檢查，行為逐位元不變。
     - 既有測試 `test_outline_curation_answerability_agents_req.py`、`test_outline_curation_answerability_args_req.py` 的輸入都沒有標記 ⇒ 不受影響
     - S1 驗收會在容器內實跑確認
   - **單一實作**：`rag-orchestrator/tools/text_containment.py`（只用標準庫），提供 `is_external(input_paths) -> bool` 與 `require_contained(out_path)`。
     - `coverage_map.py` 從同層 `tools/` 直接 import。
     - skill 端 `_envelope.py` 的定位方式照 `canon_items.py`／`apply_proposal.py`：以 `__file__` 為基準的 `_RAG = _HERE/../../../../rag-orchestrator`，不存在就退 `/app`，並確認 `tools/text_containment.py` 存在；⛔ 不用 `reweigh.py::_rag_root`，因為它依賴 cwd。
       - 主機：`<repo>/rag-orchestrator`
       - `.agents` 鏡像：`<repo>/rag-orchestrator`
       - 容器：`/app`
     - 七個呼叫點**每次執行都 import**，不論是否觸發（`is_external` 本身就在這個模組裡）；找不到或 import 失敗 ⇒ raise。
     - ⛔ 不在兩處各寫一份。
   - **單一旗標鍵**：外部文字一律用 `_meta.text_policy == "external"` 表示。會帶這個鍵的檔：
     - cells、map（轉換器寫）
     - args（`answerability_args.py` 寫進頂層 `_meta`）
     - `manifest.json`（prepare 寫）
     - `coverage-map.json`（`coverage_map.py` 寫）
     - worklist（`source_audit.py` 寫）

     ⛔ 不另設 `textPolicy` 之類的第二個鍵。
   - **圍欄不得落在 repo 內（不靠 `.git` 的第二道排除，只寫在 `text_containment.py` 一處）**：標記檔所在目錄與輸出路徑的 realpath，只要符合任一條就 raise：
     - 位於 `_RAG`（模組自身定位出的 rag root：主機 `<repo>/rag-orchestrator`、容器 `/app`）底下
     - 任一祖先含 `.git`
     - 理由：容器內 `/app` 是可寫的 repo 目錄且沒有 `.git`；其餘 repo 掛載（`/.claude`、`/.kiro`、`/scripts`、`/docs`）都是 `:ro`，寫不進去。
     - 轉換器建立標記檔與 `require_contained` 用同一個函式。
   - 呼叫點共**七處**（含文字的寫出點全列；每處的「輸入檔參數」＝該 CLI 所有 JSON 輸入）：
     - `answerability_args.py` 的 `--out`
     - `answerability_agents.py prepare` 的 `--out-dir`
     - `answerability_agents.py collect` 的 `--out-dir`（`third.prompt.md`、`third-cells.json`）
     - `reweigh.py` 的 `--coverage-out`
     - `reweigh.py` 的 `--out`（`payload.cells` 含 `min_verification.phrasings`）
     - `coverage_map.py` 直接 CLI 的 `--out`
     - `source_audit.py worklist` 的 `--out`
   - `coverage_map.py` 把 demand 的 `_meta.text_policy` 原樣帶進 `coverage-map.json` 的 `_meta`。
   - 已查證**不含文字**、不加守門的寫出點：
     - `collect --out`（`validate_verdict` 白名單）
     - `finalize` 的 `--out` 與 journal（`build_journal_entry` 只記計數）
     - 狀態檔（`update_state` 只存 relpath）
   - `save_verdict.py` 存的判者原始陣列，一律落在 `prepare --out-dir/verdicts/`，由該目錄的守門涵蓋。
4. **`--state-file`**：`finalize_answerability.py`、`reweigh.py`、`source_audit.py check` 三支加這個選項。預設＝現行 `session.json`，行為不變；本案指向 repo 外 run 目錄（F7）。
5. **文件**：`steps/04-answerability.md` 與 `steps/05b-source-audit.md` 各加一節「真實問句進場」（CLI、客戶文字落點、`--state-file`、`--target-user`、權威來源顯式傳 `--authority`）。同步 `.agents/skills/outline-curation/`，並用 `cmp` 核對兩份一致。
6. **測試**（`rag-orchestrator/tests/unit/skills/outline_curation/`，每條做變異檢查：把功能還原後必須轉紅）
   - ⛔ fixture **只准用合成字串**，⛔ 不得取自 `~/jgb-archive/` 任何檔（security-reviewer P2-5）；S3 的外洩掃描也涵蓋 `tests/`。
   - 轉換器形狀＋落 repo 內即拒
   - `--target-user`：
     - fixture 正本內預先放入僅限某受眾的細目，篩選後的集合必須逐一吻合
     - 負對照：不給 ⇒ 全部
     - 篩選時候選區塊的標頭改寫成「依受眾篩選（target_user=<aud>）、原序列舉、未排序」；不篩選時標頭逐字不變（既有 prompt sha 不變）
     - 真正本的計數（pm 509／prospect 112／全部 515）只作 S1 驗收時的一次性實跑，⛔ 不寫成單元測試（正本一改就會紅）
   - 守門（全部用 `tmp_path` 建兩個目錄：`fence/` 放 `.text-external`、`plain/` 不放；容器內外同一套語義，不需要假 `.git`）：
     - 七個呼叫點各一條：輸入在 `fence/`、輸出在 `plain/` ⇒ 非 0；輸出在 `fence/` ⇒ 0
     - 輸入 `_meta` 缺席但位於 `fence/` ⇒ 仍觸發
     - `plain/` 內有 symlink 指向 `fence/` 以外 ⇒ 依 realpath 判斷
     - 輸入全在 `plain/` 且無 `_meta` ⇒ 不檢查（舊流程）
     - 轉換器 `--out-dir` 的祖先有 `.git`（測試裡建一個假 `.git` 目錄）⇒ 拒；沒有 ⇒ 建立標記
     - `coverage_map.py` 直接 CLI：輸出不在圍欄 ⇒ 非 0；把守門呼叫移除 ⇒ 此測試轉紅
     - **舊流程在任意 cwd 不變**：`answerability_agents.py prepare` 對 `plain/` 輸入、`cwd=tmp_path`、env 移除 `CLAUDE_PROJECT_DIR` ⇒ exit 0，且 `manifest.json` 與改動前逐位元相同
     - **模組缺席即失敗**：定位器指向一個沒有 `text_containment.py` 的目錄（測試用 env 覆寫點，僅供測試）⇒ 任一呼叫點非 0
     - **args 帶旗標但不在圍欄**：`plain/` 裡的 args.json 帶 `_meta.text_policy=external`，`prepare --out-dir plain/…` ⇒ 非 0；把 `is_external` 改成忽略 `_meta` 時必須轉紅
     - **圍欄在 rag root 下即拒**：在 fixture rag root（env 覆寫點）底下建 `.text-external`，轉換器與任一呼叫點都非 0；移除該規則時必須轉紅
   - **端到端不含文字**：合成問句跑 converter → args → prepare → collect（以假判者檔）→ finalize → reweigh，掃描 repo 內每一個被寫出或改動的檔，⛔ 不得出現任何一句合成問句
   - `--state-file`：給了時預設狀態檔的位元組不變；不給時照舊寫預設檔

**S1 驗收**
- 新測試全綠且通過變異檢查。
- `scripts/run-tests.sh unit` 紅燈＝HANDOFF §4 那 9 條、逐名相同，⛔ 不得出現名單外的紅。
- 既有 skill 測試一條不改，且在容器內全數維持原結果；特別是 `test_outline_curation_answerability_agents_req.py`、`test_outline_curation_answerability_args_req.py` 全綠。
- 兩份 skill 相同：`diff -rq .claude/skills/outline-curation .agents/skills/outline-curation -x runs -x raw -x journal` 無輸出。
- `rag-orchestrator/tools/text_containment.py` 是唯一實作：`grep -rn "def require_contained" .claude rag-orchestrator` 只命中它。
- `make audit` 只剩不變量 34（§5-5 既有）。
- fresh `verifier` CONFIRMED。

### S2 — 步 4 重判 184 題（花 token；需業主核可預算）

- run 目錄：`~/jgb-archive/ruler-9.13/skill-run-20260925/`（700），所有中間檔都在這裡。
- 分組：
  - `property_manager` 179 格，`--cells-per-agent 30` ⇒ 6 組 × 2 slot＝12 代理
  - `prospect` 5 格 ⇒ 1 組 × 2＝2 代理
  - 第 3 判者各受眾最多 1 代理
  - ⇒ 最多 16 代理（上限 180 ✓）
- **成本量尺（plan-verifier 第 1 輪 #3）**：
  - 量什麼：每個判者子代理完成時，任務通知回報的 `<usage><subagent_tokens>`。這是 harness 計的實際值；`answerability_agents.py::cmd_collect` 自己註明「token 由 harness 計，此處不估」。
  - 在哪記：主 session 每收一個判者，就把 `subagent_tokens` 累計寫進 run 目錄的 `cost.json`，§4 的停止條件讀這一份。
  - 為什麼不能用 137k × 代理數：判者要分段讀一份約 37 萬位元組的 prompt 檔，每一段讀取都會把先前的上下文再送一次 ⇒ 每位判者的實際用量是 137k 的數倍，倍數取決於分幾段，而分幾段無法事前確定。
  - 本 session 的參考點：唯讀代理整檔讀完約 1.4 MB 的目錄，回報 `subagent_tokens` 801,927。
- **先做一組試跑**：先只派 pm 的 G01 兩個 slot（2 判者），量得每判者平均用量 u。
  - 外推值 ＝ u ×（pm 12＋prospect 2 × 31/137＋第 3 判者 2）。prospect 那一組依候選大小比例折算。
  - 外推值 ≤ 業主核定的上限 ⇒ 繼續扇出；超過 ⇒ 停、帶 u 與外推值回業主。
  - 試跑的兩份判決保留，⛔ 不重跑。
- 預估區間（僅供 D2 參考、⛔ 不當判準）：每判者 30–60 萬 ⇒ 全案約 5–10M `subagent_tokens`。
- **判者**：臨時子代理，model 顯式指定 `sonnet`（⛔ 不繼承主 session 模型），每次 ≤4 並行（F13）。Brief 的 Hard rules：
  - 只讀指定的那一份 prompt 檔（檔案約 37 萬位元組，分段讀完）
  - 只依檔內資料作答，⛔ 不讀其他檔
  - 最後一則只輸出 JSON 陣列
  - ⛔ 不寫任何檔
  - ⛔ 不在回覆中轉述題目文字
- 收件：`save_verdict.py` 從 transcript 取最後一則 → `collect` → `finalize_answerability.py --state-file <run>/state.json --journal-dir <run>/journal`。
- **S2 執行步驟（逐條可照打；`R=~/jgb-archive/ruler-9.13/skill-run-20260925`）**：
  1. **主機**：`python3 .claude/skills/outline-curation/scripts/real_questions_to_cells.py --in ~/jgb-archive/ruler-9.13/no_canon.json --out-dir $R`
     - 預期輸出：`cells-property_manager.json`（179）、`cells-prospect.json`（5）、兩份 map、`.text-external`
     - 然後 `chmod 700 $R`
  2. **容器**（兩受眾各一次；`FROZEN=2026-09-25T00:00:00+08:00`）：
     ```
     docker compose -f docker-compose.dev.yml run --rm -T -v $R:/run_ext rag-orchestrator \
       python3 /.claude/skills/outline-curation/scripts/answerability_args.py \
       --cells /run_ext/cells-<aud>.json --canon /app/canon/jgb --target-user <aud> \
       --rubric /.claude/skills/outline-curation/schemas/answerability-rubric.md \
       --frozen-at $FROZEN --slim --out /run_ext/args-<aud>.json
     ```
  3. **主機**：`python3 .claude/skills/outline-curation/scripts/answerability_agents.py prepare --args $R/args-<aud>.json --out-dir $R/ans-<aud> --cells-per-agent 30`
     - pm 應得 6 組、prospect 應得 1 組，各組 2 份逐位元相同的 prompt。
     - 以 `manifest.json` 的 `chars` 確認組大小；主 session ⛔ 不讀 prompt 內容。
  4. **試跑**：只派 pm 的 G01 兩個 slot，每 slot 一個臨時子代理（`model: sonnet`，並行 2）。
     - 容量前提（plan-verifier S2 第 1 輪 #1(a)）：`claude-sonnet-5` 的 context window＝**1M token**（claude-api skill 模型表，快取日 2026-06-24）；pm prompt 約 13.7 萬 token（F3）＋ rubric、30 題、Read 行號前綴、子代理系統提示，估計 ≤ 17 萬，約占 17%。
       - Claude Code 子代理實際拿到的視窗沒有文件可查 ⇒ 不靠推估，改由下面的逐判者完整性檢查實證。
     - Brief：
       - 「讀 `<R>/ans-property_manager/prompts/G01-s<slot>.prompt.md` 全檔（分段讀到檔尾）；該檔是你的全部輸入，檔內『⛔ 不讀取任何檔案或工具』指的是**除此檔以外**」
       - 「讀完後、輸出答案前，先單獨送出一則訊息，內容只有一行：`COVERAGE n=<候選區塊標頭寫的筆數> first=<第 1 筆候選 id> mid=<第 ⌊n/2⌋+1 筆候選 id> last=<最後一筆候選 id>`」（pm：n=509 ⇒ 第 255 筆；prospect：n=112 ⇒ 第 57 筆）
       - 「然後，依檔內 rubric 與輸出定義，最後一則訊息只輸出 JSON 陣列」
       - 「⛔ 寫檔、⛔ 在任何訊息中轉述或引用題目文字、⛔ 讀其他檔、⛔ 網路」
  5. **收件**：每個判者完成後：
     - 把任務通知的 `subagent_tokens` 追加寫入 `$R/cost.json`。
     - **完整性檢查（plan-verifier S2 第 1 輪 #1(b)(c)）**：以 repo 外一次性腳本 `$R/../scripts/coverage_check.py` 讀該判者的 transcript JSONL。
       - 只印：`COVERAGE` 那一行的四個值，以及它們與 `args-<aud>.json` 的 `fineIdEnum` 比對的真假。應為：`n == len(fineIdEnum)`（pm 509）；`first`／`mid`／`last` 分別等於 `fineIdEnum[0]`／`fineIdEnum[len//2]`／`fineIdEnum[-1]`。
       - 另外只印一個數字：transcript 內 `compact`（不分大小寫）出現的次數，應為 0。這一項沒有已知壓縮的 transcript 可當正對照，只作輔助訊號；主判準是上面的四值比對。
       - 腳本 ⛔ 不印任何其他內容。
     - 通過後才執行 `python3 .claude/skills/outline-curation/scripts/save_verdict.py G01-s<slot> <該判者 transcript.jsonl> --out-dir $R/ans-property_manager`。
       - save_verdict 只印 `cell_id`／`label`。
     - **不通過** ⇒ 該判決作廢、⛔ 不存；S2 依 §4 停下、交業主。
     - ⛔ 主 session 不 Read 任何 transcript。
  6. **外推**：u＝兩判者 `subagent_tokens` 的平均；全案外推＝u ×（pm 12＋prospect 2 × 29,836／134,558＋第 3 判者 2）≈ u × 14.44。
     - ≤ 10M ⇒ 記錄
     - ASK 模式：不論外推值多少，都先停下交業主，再決定是否扇出。交付內容：u、外推值、G01 兩 slot 的一致格數，以及兩 slot 的完整性檢查結果（四值比對、`compact` 次數）
  7. 扇出（業主點頭後）：
     - pm G02–G06 與 prospect G01，每次 ≤4 並行，步驟同 4–5；每位判者（含第 3 判者）都過完整性檢查
     - `python3 .claude/skills/outline-curation/scripts/answerability_agents.py collect --args $R/args-<aud>.json --out-dir $R/ans-<aud> --out $R/result-<aud>.json`
       - exit 4 ⇒ 依印出的 `third.prompt.md` 派第 3 判者，存成 `$R/ans-<aud>/verdicts/third.json`，再跑 collect
     - `python3 .claude/skills/outline-curation/scripts/finalize_answerability.py --run-result $R/result-<aud>.json --out $R/answerability-<aud>.json --state-file $R/state.json --journal-dir $R/journal --run-id answerability-<aud>-20260925`（兩受眾 run-id 分開，避免 journal 互蓋）
     - 算 §0 五類計數。
- 每一步做完都跑：`git status --porcelain` 比對步驟前的快照，不得出現新增或改動的 repo 檔（第 1–3 步屬本 Plan 範圍、預期零變動）。
- **S2 驗收**：
  - **每一位判者（含第 3 判者）都通過完整性檢查**
  - 兩受眾 `agreementRate` 都 ≥ 0.80：未達 ⇒ `needs_rubric_revision`，依 E6 停下、交業主，⛔ 不自行改 rubric
  - `droppedCells == 0`
  - 184 格每格都有終判
- **S2 交業主的數字**：
  - §0 P1 的五類 N_ns／N_un／N_pa／N_an／N_dn（加總＝184），以及依先定判準得出的 P1 判定
  - 被推翻的題（N_an）附對到的細目 id（⛔ 不附題目原文）
  - 兩受眾各自的一致率
  - 試跑的 u、實際累計 `subagent_tokens`
- **執行環境**：`answerability_args.py --canon` 需要容器（`canon_parser` 會 import `psycopg2`，主機沒有）。
  - 以 `-v <run 目錄>:/run_ext` 讀寫掛載，輸出寫 `/run_ext`；標記檔跟著目錄進容器，圍欄照常生效。
  - ⛔ 不 `docker cp`。

### S3 — 步 5 去向＋步 5b 對源（花 token；交業主前的最後一道）

1. `reweigh.py --canon rag-orchestrator/canon/jgb --demand <run>/cells-<aud>.json --map <run>/map-<aud>.json --answerability <run>/answerability-<aud>.json --coverage-out <run>/coverage-map-<aud>.json --out <run>/coverage-reweigh-<aud>.json --state-file <run>/state.json`
2. `source_audit.py worklist --coverage <run>/coverage-map-<aud>.json --out <run>/worklist-<aud>.json`，**顯式** `--authority`：
   - `code:/Users/chenqinghuang/dev/work/jgb2/dev2（git show b2ee2ac382ce:<path>，釘住 commit）`
   - `help:<幫助中心 HTML 目錄>`
   - `ledger:docs/knowledge/jgb-product-facts.md`

   本 Plan 依本線紀律取釘住 commit；DSP-071 由業主另裁，⛔ 本 Plan 不改 `DEFAULT_AUTHORITY`。
3. **盤查**：唯讀 `scout`，依架分批（每批 ≤25 格、每次 ≤4 並行）。
   - 題目交付方式：主 session 用 `jq` 從 worklist 切出該批，寫成 run 目錄下的 `worklist-<aud>-<批>.json`；scout 只收到**檔案路徑**，⛔ 題目不放進 Agent prompt 參數。
   - scout Hard rules：
     - 回報一律以 `cell_id` 指稱，⛔ 不轉述或引用題目文字
     - ⛔ 不寫檔
     - jgb2 只走 `git show b2ee2ac382ce:<path>`
   - 每格要 `path:symbol` 證據；否定結論必附正對照。
   - 主 session 維持 Plan 9.13 §2 的輸出紀律（⛔ 不 Read／cat 含題目文字的檔）。對碼只看 scout 回報的 `cell_id`、證據與正對照：親自重跑**每一條** `verified_absent` 的正對照 grep，並抽 10% 的 `verified_fact` 對碼。
   - `source-audit-<aud>.json` 由主 session 依 scout 回報組裝，只含 `cell_id`／`status`／`evidence`／`positive_control`／`ledger_anchor`／`why_unresolvable`，放在 run 目錄。
4. **事實帳本回填**：`docs/knowledge/jgb-product-facts.md`。只寫受眾中立的產品事實、附引用與錨點，⛔ 不寫客戶措辭。
5. `source_audit.py check --coverage … --audit <run>/source-audit-<aud>.json --state-file <run>/state.json` ⇒ `unaudited == 0` 才算出口。

**S3 執行步驟（逐條可照打；`R=~/jgb-archive/ruler-9.13/skill-run-20260925`，`J=<scratchpad>/jgb2-b2ee2ac`）**
1. **釘住 commit 的唯讀匯出**：唯讀 `scout` 角色只有 Read／Glob／Grep，跑不了 `git show` ⇒ 先匯出一份給它讀。
   - 指令：`git -C /Users/chenqinghuang/dev/work/jgb2/dev2 archive b2ee2ac382ce | tar -x -C $J`（5,882 檔、約 211 MB）
   - 放在 session scratchpad，⛔ 不進 repo，⛔ 不改動 jgb2 repo
   - 驗收：`ls $J | wc -l` > 0；`git -C …/dev2 ls-tree -r --name-only b2ee2ac382ce | wc -l` ＝ `find $J -type f | wc -l`
2. **步 5（容器，兩受眾各一次）**：
   ```
   docker compose -f docker-compose.dev.yml run --rm -T -v $R:/run_ext rag-orchestrator \
     python3 /.claude/skills/outline-curation/scripts/reweigh.py --canon /app/canon/jgb \
     --demand /run_ext/cells-<aud>.json --map /run_ext/map-<aud>.json \
     --answerability /run_ext/answerability-<aud>.json \
     --coverage-out /run_ext/coverage-map-<aud>.json --out /run_ext/coverage-reweigh-<aud>.json \
     --state-file /run_ext/state.json
   ```
   - 預期：`not_available` ＝ N_ns＋N_un（pm 142、prospect 3，合計 145）；`fine` ＝ N_pa＋N_an（pm 37、prospect 2）；無去向 0
3. **worklist（主機）**：
   ```
   python3 .claude/skills/outline-curation/scripts/source_audit.py worklist \
     --coverage $R/coverage-map-<aud>.json --out $R/worklist-<aud>.json \
     --authority "code:jgb2 b2ee2ac382ce（唯讀匯出 $J，路徑為 jgb2 repo 相對）" \
     --authority "help:/Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/*_zh-Hant.html" \
     --authority "ledger:docs/knowledge/jgb-product-facts.md"
   ```
4. **分批（主機，repo 外一次性腳本 `$R/../scripts/batch_worklist.py`）**：
   - 依 `gaps_categorized.json` 的 `coarse_id` 取架字母（⛔ 只用來分批路由，不當結論）；查無者歸「未分類」批
   - 每批 ≤25 格，寫成 `$R/audit/batch-<nn>.json`（含題目文字，落在圍欄內）
   - 只印每批格數與架字母
5. **盤查**：每批一個唯讀 `scout`（每次 ≤4 並行，總數 ≤12）。Brief：
   - 讀 `$R/audit/batch-<nn>.json`；jgb2 一律讀 `$J`（它是 `b2ee2ac382ce` 的內容）；幫助中心讀上述目錄；帳本讀 `docs/knowledge/jgb-product-facts.md`
   - 最後一則只輸出 JSON 陣列，每格一筆（plan-verifier S3 第 1 輪 #2／#3 修正後的形狀）：
     `{cell_id, status∈{verified_fact, verified_absent, owner_needed}, evidence:[ "<jgb2 repo 相對路徑>:<逐字子字串>" | "help:<檔名>#<逐字子字串>" ], fact(verified_fact 時：一句受眾中立的產品事實，⛔ 不用客戶措辭), negative_grep(verified_absent 時：{pattern, path, mode∈{regex,fixed}, case∈{sensitive,insensitive}}，預期 0 命中), positive_control(verified_absent 時：同一個 path、同一個 mode 與 case，已知必然命中), topic(owner_needed 時：一般化主題 ≤20 字，⛔ 不用客戶措辭), why_unresolvable(owner_needed 時：查了哪些來源、為何仍定不了)}`
   - **「逐字子字串」**：從該檔**某一行逐字複製**的一段（≥4 字元、不跨行），⛔ 不寫 `Class::method`、`method()` 這類自己組出來的限定名，⛔ 不改寫
     - 程式子字串**不得以空白開頭**：去掉縮排
     - `help:` 子字串**不得含任何空白**：取一段不含空白的連續字；兩條都是為了符合 `source_audit.py::EVIDENCE_RE`
   - `negative_grep`／`positive_control` 必須就是你實際用 Grep 工具（ripgrep）跑過的 pattern 與旗標
     - `mode` 一律填 `regex`（Grep 工具沒有固定字串模式；要查字面就自己跳脫中介字元）
     - `path` 一律是 **jgb2 repo 相對路徑**（`.` 代表整個 repo），⛔ 絕對路徑、⛔ `..`
   - Hard rules：⛔ 寫檔、⛔ 在任何訊息轉述或引用題目文字（以 `cell_id` 指稱）、⛔ 讀 `$J`／幫助中心／帳本／該批檔以外的檔、⛔ 網路
   - **試跑與派發規則（plan-verifier S3 第 1 輪 #4）**：
     - 先只派第 1 批（試跑），把它的 `subagent_tokens` 記入 `cost.json` 當作 u_s3
     - 之後每派一個新 scout 前檢查：`累計 ＋ 進行中 scout 數 × u_s3 ＋ u_s3 ≤ 10M`，不成立就不派、停下
     - ASK 模式：試跑完就停，把 u_s3 與外推值（累計 ＋ 剩餘批數 × u_s3）交業主
6. **收件（主機，repo 外一次性腳本 `$R/../scripts/ingest_audit.py`）**：
   - 以 `handback_to_jsonl.py` 抽出交件內容
   - 驗形狀：每格恰一筆、`status` 在值域內、欄位齊全、`evidence` 符合 `source_audit.py::EVIDENCE_RE`
   - **機械複驗（依證據種類分開）**：
     - 程式證據 `<path>:<子字串>`：`$J/<path>` 必須存在，且該檔以固定字串比對子字串 ≥1 次
     - 幫助中心證據 `help:<檔名>#<子字串>`：幫助中心目錄下的 `<檔名>` 必須存在，且以固定字串比對子字串 ≥1 次
     - 每條 `verified_absent`：用 **ripgrep 14.1.1**（主機上的 `rg` 是呼叫 Claude 執行檔、argv0＝`rg`；腳本以同一個執行檔、同樣的 argv0 呼叫，與 scout 的 Grep 工具是同一引擎）重跑 `negative_grep` 與 `positive_control`
       - 只接受 `mode=regex`，⛔ 不傳 `-F`；`case=insensitive` ⇒ `-i`；對 `$J/<path>` 遞迴、`-c` 加總
       - `path` 若為絕對路徑、含 `..` 或越出 `$J` ⇒ 複驗失敗
       - 判準：negative 必須＝0、positive 必須 ≥1；兩者的 path／mode／case 必須相同
       - 這就是 §2 S3-3「主 session 親自重跑每一條正對照」的落實
   - **程式證據路徑在 `$J` 不存在（唯一規則，plan-verifier S3 第 2 輪 #4）**：
     - 算複驗失敗，退回同一 scout 重查一次；仍失敗 ⇒ 改判 `owner_needed`（寫明「證據無法在釘住 commit 找到」）
     - ⛔ 不停止整片
     - §4 的停止條件只管「組好的 `source-audit-<aud>.json` 裡仍有不在 `$J` 的程式證據」（收件已擋掉，理論上不會發生）
   - 程式證據的路徑同樣要是 jgb2 repo 相對路徑：⛔ 絕對路徑、⛔ `..`，且正規化後必須在 `$J` 之內。`help:` 的檔名必須是幫助中心目錄內的純檔名（收尾審查 #1）
   - **腳本先用合成紀錄自測**，16 案全數得到預期結果才處理真紀錄（2026-09-25 已實跑 16/16 ✓；⑭ 程式證據絕對路徑、⑮ 含 `..`、⑯ `help:../` 皆失敗）：
     - ① 合法程式證據 ⇒ 通過
     - ② 合法 `help:` 證據 ⇒ 通過，且⛔ 不觸發 §4 停止
     - ③ `Class::method` 限定名 ⇒ 失敗並寫明原因
     - ④ regex `negative_grep` 實際在 `$J` 命中 ⇒ 報複驗失敗（⛔ 不當成 0）
     - ⑤ positive 與 negative 的 mode 不同 ⇒ 失敗
     - ⑥ 合法 absent ⇒ 通過
     - ⑦ help 子字串含空白 ⇒ 失敗
     - ⑧ 程式子字串以空白開頭 ⇒ 失敗
     - ⑨ `mode=fixed` ⇒ 失敗
     - ⑩ 含 `|` 的 regex negative 在 `$J` 命中 ⇒ 失敗
     - ⑪ 絕對路徑 ⇒ 失敗
     - ⑫ 相對路徑 ⇒ 重跑成功
     - ⑬ 程式證據路徑不存在 ⇒ 失敗（走上面那條唯一規則）
     - 另抽 10% 的 `verified_fact`，由主 session 讀 `evidence` 指到的程式段對碼：只讀 `$J` 的程式，⛔ 不讀題目
   - 只印格數、各狀態計數、複驗失敗的 `cell_id`
   - 複驗失敗的格 ⇒ 退回同一 scout 重查一次，仍失敗改判 `owner_needed`
7. **帳本回填（repo 內 Edit）**：`verified_fact` 的 `fact` 依產品主題合併成條目，追加到 `docs/knowledge/jgb-product-facts.md` 新節「Plan 9.14 對源事實（2026-09-25，jgb2 `b2ee2ac382ce`）」。
   - 每條附錨點 `{#p914-<slug>}`（slug 限 `[a-z0-9-]+`，才會被 `source_audit.py::_ledger_anchors` 的 `\{#([A-Za-z0-9_-]+)\}` 抓到）與引用
   - 同一事實可供多格共用一個錨點
   - 回填後把錨點寫回 `source-audit-<aud>.json`
8. **`source-audit-<aud>.json`（主機組裝，放 `$R`）**：形狀照 `schemas/source-audit.json`（`additionalProperties:false`）：
   ```
   {step:"source_audit", coverage_map_sha, authority_sources:<從 worklist-<aud>.json 原樣複製>,
    records:[{cell_id, status, evidence?, positive_control?（字串 "<pattern> [<mode>,<case>] @ <path> hits=<n>"）, ledger_anchor?, why_unresolvable?}]}
   ```
   - 真正組裝前，先用合成資料自測 `source_audit.py check`：
     - 合成 coverage map（3 格 `not_available`）與 `--state-file` 都放 scratchpad
     - 三種 status 各一筆，錨點用帳本現有的錨點 ⇒ exit 0；拿掉 `step` ⇒ 失敗；錨點改成非 ASCII ⇒ 失敗
     - 前後比對 `.claude/hooks/state/outline-gate/session.json` 的 sha，不得改變
     - 2026-09-25 已實跑：good 0／nostep 1／nonascii 2；session.json sha 前後同為 `3105cbe7d0c5f948…` ✓
   - 然後跑 `source_audit.py check --coverage $R/coverage-map-<aud>.json --audit $R/source-audit-<aud>.json --state-file $R/state.json` ⇒ `unaudited == 0`
9. **81 題清單追加（repo 內 Edit）**：`owner_needed` 追加到 `runs/outline-20260920/open-questions-20260923.md`，82 號起，格式 `` `<粗目 id>` ``：〔9.14 真實問句〕<topic>——<why_unresolvable 摘要>。
   - Edit 會觸發 `outline_gate` 的識別碼掃描，算額外的一道防護
10. **外洩掃描**：指令固定為 `cd <repo> && python3 ~/jgb-archive/ruler-9.13/scripts/leak_scan.py`。
    - 規則二一律執行、無旗標，沒執行即非 0
    - 必須同時印出 substring 摘要行與「寬掃描行數…新增命中」行，且兩個正對照都過
    - 有命中就交業主
11. **fresh verifier**（見下方「S3 驗收」）。

**S3 驗收**
- 兩受眾 `check` 皆 exit 0。
- **外洩檢查 0 未裁決命中**（補 F10 的缺口；security-reviewer P1-3：整句雜湊只抓得到逐字相同，`outline_gate.py::IDENTIFIER_CATEGORIES` 只有 7 類，沒有人名／地址／社區名／房號／身分證）：
  - **掃描對象**：
    - `git diff` 的所有新增行（已追蹤檔被改動的部分：帳本 `docs/knowledge/jgb-product-facts.md`、`runs/outline-20260920/open-questions-20260923.md`、`tests/`、skill 檔）
    - 加上 `git ls-files --others --exclude-standard` 列出的每一個未追蹤檔
  - **規則一**：逐行做 NFKC 並去空白後，與 184 題各自的正規化文字比對最長共同子字串，**≥8 字即命中**。
  - **規則二**：套用 Plan 9.13 獨立寬掃描器的規則與替換字典（≥4 碼數字、`@`、網址、稱謂、路街巷弄號樓、身分證樣式、替換字典殘留）。
    - 規則逐字抄進 `leak_scan.py`，⛔ 不執行 `scan.py`（見 §10 事故）
    - **掃描範圍只限** S3 會寫入自由文字的檔的新增行：`docs/knowledge/jgb-product-facts.md`、`runs/outline-20260920/open-questions-20260923.md`，外加 `rag-orchestrator/tests/`
    - 理由：這些規則套在一般程式碼上幾乎每行都會命中（數字、`@`、網址），全 repo 套用只會是雜訊
    - 全範圍的外洩由規則一（≥8 字共同子字串）負責
    - 以 S3 寫入前存的基準（86 行，全在 `tests/`，逐條判定為產品通用詞或測試佔位）扣除後，只看新增命中
  - **正對照**：把一段 ≥8 字的題目片段嵌進合成句中間、再塞一個 `王小姐`，兩者都必須命中；否則非 0 退出。
  - 掃描程式放 repo 外 run 目錄；stdout 只印檔名、行號、類別，⛔ 不印內容。
  - 命中逐筆交業主裁（遮蔽或放行）。
  - **commit 前業主看過帳本與 open-questions 的 diff**。
- fresh `verifier` 驗「交業主清單的每一格都有三態之一與證據、數字與 run 檔一致、repo 無客戶文字」⇒ CONFIRMED。

**S3 交業主**
- `owner_needed` 清單：只給一般化主題＋架／粗目＋`why_unresolvable`，⛔ 不貼原文。
  - 併入 81 題時沿用它現有的形狀：`runs/outline-20260920/open-questions-20260923.md` 是扁平編號清單，每則 `` `fine_id` ``：自由文字，沒有分類欄位。新項接在 82 號之後，沒有細目的就用粗目 id（`coarse-ids-20260921.md`），並在文字開頭標「〔9.14 真實問句〕」以便區分來源。
- **184 格全數有去向**（plan-verifier 第 1 輪 #2：`coverage_map.py::_decide` 把 `partial`／`answerable` 送到 `fine`，⛔ 不進 5b）。四個桶加總＝184：
  | 桶 | 來自 | 去向 | 交付欄位 |
  |---|---|---|---|
  | ① 已對源的缺口 | N_ns＋N_un（兩者都終判 `no_source` ⇒ `not_available` ⇒ 進 5b） | `verified_fact`（產品有、正本沒寫 ⇒ 起草新細目的材料）／`verified_absent`（I 架「不支援」清單）／`owner_needed`（交業主） | 三態計數＋`owner_needed` 清單；`unresolved` 另外標註 |
  | ② 部分缺口 | N_pa | `fine`＋`add_knowledge`：在既有細目補一段；補的內容在起草時照 00c 逐句對源 | `fine_id`＋計數 |
  | ③ 9.13 判錯 | N_an | `fine`：正本已有答案，屬說法或檢索問題（檢索另由 ruler-9.13 量） | `fine_id`＋計數 |
  | ④ 判者錯誤 | N_dn | 併入 ① 處理 | 計數 |
- ①～④ 合起來**取代** `gaps_categorized.json` 的全部 184 題；舊檔保留在 repo 外、標為已被取代，⛔ 不刪（結案時依 Plan 9.13 §2 一併處理）。

## 3. 不做（另案）

- 依 `verified_fact` 起草新細目、重跑生成正本（HANDOFF §6-3 的下游）。
- 155 題未複核 gold 重判。
- 調整 prompt 順序讓候選區塊成為共用前綴、以節省快取寫入：未驗證、會動到步 4 的 prompt 結構，另案評估。
- `.agents/skills/outline-curation/raw/` 裡既有 ~150 個檔的內容去留（S0 只讓它不被追蹤，⛔ 不刪）。
- commit、部署。

## 4. 停止條件

- S1：紅燈 >9 或出現名單外的紅；鏡像 `cmp` 不同。
- S2：
  - 試跑外推值 > 業主核定上限，或 run 目錄 `cost.json` 的累計 `subagent_tokens` 超過上限
  - 任一受眾一致率 <0.80
  - 判者寫檔或回覆轉述題目文字（改派、記事故）
  - `droppedCells >0`
  - 五類加總 ≠184
  - 任一判者完整性檢查不通過（四值不符，或 `compact` 次數 >0）
- S3：
  - 組好的 `source-audit-<aud>.json` 裡仍有**程式證據**不在 `$J` 內（收件階段的缺路徑走「重查一次 → `owner_needed`」，不在此列；`help:` 證據改查幫助中心目錄）
  - 帳本外洩檢查命中
  - `git status` 掃描命中
  - `cost.json` 累計 `subagent_tokens`（S2＋S3）超過 10M
  - 四桶加總 ≠184
  - `source_audit.py check` 非 0
- 任一步 repo 正本 sha 變動 ⇒ 停。

## 5. 回滾

- S1：改動前把受影響檔案備份到 session scratchpad `p914-backup/`；新腳本與新測試直接刪除；鏡像同步回退。
- S0：刪掉 `.gitignore` 新增的三行。
- S2／S3：
  - 刪 repo 外 run 目錄（刪前刪後各列一次目錄）
  - 判者與 scout 的 task-output JSONL 在 `/private/tmp/claude-501/…/tasks/`（含遮蔽後題目），Plan 結案時一併列出並刪除，刪前刪後各列一次
  - 帳本與 open-questions 的新增段落未 commit，用備份 diff 還原
- 題目文字從未進 git ⇒ 沒有公開撤回的問題。

## 6. ⏳ 待業主裁

- **D1 範圍**：只重判 184 題（建議）／全部 381 題 knowledge 題（多約 1 倍 token，但 ruler-9.13 已凍結，gold 側結果只能報告、不能回寫）。
- **D2 S2 預算（兩段式）**：
  - 現在核可試跑 2 判者
  - 並給一個扇出上限（以 `subagent_tokens` 計；建議 10M，對應預估區間的上緣）
  - 試跑外推超過上限就停下回報，⛔ 不自行放寬
  - 這已遠超步 4 原訂「$3」的前提（F12）
  - S3 scout 預估 ≤12 個唯讀 scout，用量同樣記進 `cost.json`。**上限解讀（plan-verifier S3 第 1 輪 #4；取較嚴的一種）**：S2＋S3 **合計** ≤ 10M；S3 試跑完停下時，由業主確認或改訂
- **D3 分組**：成本幾乎跟判者人數成正比，因為每位判者都要讀完整份候選。
  - 每代理 30 格（建議；16 判者）
  - 每代理 60 格（約 8 判者、成本約一半，每位判者負擔加倍）
  - 每代理 15 格（約 28 判者、成本約 1.8 倍）
- **D4**：已依 security-reviewer 改列 **S0**（S1 的前置條件，⛔ 不再當另案），要業主核可才動。
- **DSP-071**：5b 權威來源取 master 還是釘住 commit（本 Plan 先用釘住 commit）。
- **執行模式**：S2／S3 屬長時間自動作業，請選 `AUTO` 或 `ASK`。

## 7. security-reviewer（2026-09-25）處置

| # | 審查 | 處置 |
|---|---|---|
| P1-1 | `reweigh.py --out` 與 `coverage_map.py --out` 含問句卻不在守門內（主 session 對碼：`reweigh.py::main` 的 `payload={"cells": cm["cells"]}`） | FIX：守門點由 5 處擴成 7 處；新增端到端「repo 內不含合成問句」測試（§2 S1-3／S1-6） |
| P1-2 | `.agents/skills/outline-curation/raw/`、`journal/` 未 ignore，且 S1 要同步 `.agents/` 鏡像 ⇒ 有耦合 | FIX：新增 S0，列為 S1 前置 |
| P1-3 | 帳本外洩檢查只比整句雜湊＋7 類識別碼；open-questions 與已追蹤檔的改動不在掃描內 | FIX：改掃 `git diff` 新增行＋未追蹤檔；≥8 字最長共同子字串＋9.13 寬掃描器；附正對照；命中交業主；commit 前業主看 diff（§2 S3 驗收） |
| P2-4 | 守門 fail-open（`_meta` 缺席即關閉、無 realpath、找不到 repo 根即跳過） | FIX：輸入在 repo 外即視為 external；逐層找 `.git`＋realpath／samefile；找不到根不放行 |
| P2-5 | 測試 fixture 可能用到真實題目 | FIX：只准合成字串；`tests/` 納入外洩掃描 |
| P3-6 | `save_verdict` 原樣存陣列；task-output JSONL 在 `/private/tmp`；scout 的交付方式與不轉述規則未寫；主 session 讀 scout 報告與 9.13 §2 衝突 | FIX（成本小）：verdicts 落在受守門的 out-dir；JSONL 納入結案刪除清單；scout 只收檔案路徑、以 `cell_id` 回報、不轉述；主 session 維持 9.13 §2 不讀含文字檔 |
| P3-7 | `.codex/hooks/state/` 未 ignore（現只有 relpath） | FIX：併入 S0 |

⚠️ P2-4 的第 2 稿修法（「輸入在 git 工作樹外即 external＋逐層找 `.git`」）在無 `.git` 的測試容器裡會把所有輸入判成 external、讓既有測試轉紅。第 3 稿改成標記檔圍欄（§8 S1-#1），仍然滿足「`_meta` 掉了照樣擋、找不到根不放行」。

## 8. plan-verifier 第 1 輪（2026-09-25）處置

| 單位 | # | 審查 | 處置 |
|---|---|---|---|
| 大綱 | 1 P2 | P1 不可證偽：`reconcile` 把 unresolved 併進 `no_source`；`partial`／`deliberate_no` 對 9.13 的對應未定 | FIX：§0 五類計數、對應規則與先定判準（門檻 18＝10%） |
| 大綱 | 2 P2 | `partial`／`answerable` 不進 5b，「取代 gaps_categorized」涵蓋不到 | FIX：§2 S3 四桶去向、加總＝184 |
| 大綱 | 3 P2 | 137k × 代理數低估了分段讀取；量尺未命名 | FIX：量尺＝任務通知的 `subagent_tokens`、記 `cost.json`；G01 試跑後外推；D2 改兩段式 |
| S0＋S1 | 1 P1 | 容器無 `.git`、`find_repo_root` 停在 `/` ⇒ 守門讓既有測試轉紅 | FIX：標記檔 `.text-external` 正向圍欄；測試用 `tmp_path` 的 `fence/`／`plain/`；驗收點名兩檔全綠 |
| S0＋S1 | 2 P2 | `coverage_map.py` 取不到 skill 的 `_envelope` | FIX：單一實作 `rag-orchestrator/tools/text_containment.py`，skill 依 `_rag_root` import，失敗即 raise |
| S0＋S1 | P3 | 候選標頭「未篩選」在 `--target-user` 下不實；真正本計數寫進單元測試會漂；`cmp` 範圍未定 | FIX：篩選時改標頭；計數改一次性實跑；改 `diff -rq … -x runs -x raw -x journal` |

## 9. plan-verifier 第 2 輪（2026-09-25）

- 大綱：**READY**。
- S0＋S1：**REVISE**（該單位第 2 次）。依規則停止自動重送，由主 session 逐條裁決：

| # | 審查 | 主 session 查證 | 處置 |
|---|---|---|---|
| 1 P2 | 「只在需要時 import」與 `is_external` 同在模組內互相矛盾；`reweigh.py::_rag_root` 依賴 cwd，主機上 cwd 在 repo 外時會 raise，會弄壞原本不依賴 repo 根的 `answerability_agents.py` | 屬實：`_rag_root` 的候選是 `find_repo_root()+"/rag-orchestrator"` 再退 `/app`；`canon_items.py` 的 `_RAG` 以 `__file__` 為基準 | **FIX**：七個呼叫點每次都 import；定位改用 `__file__` 為基準的 `_RAG` → `/app`；補「任意 cwd 舊流程不變」與「模組缺席即失敗」兩條測試 |
| 2 P2 | args 的鍵名 `textPolicy` 與觸發條件 `_meta.text_policy` 不一致 ⇒ prepare／collect 的旗標觸發永遠不生效 | 屬實（第 3 稿 S1-2 與 S1-3 用了兩個鍵） | **FIX**：只用 `_meta.text_policy` 一個鍵，列出會帶它的所有檔；補變異敏感測試 |
| 3 P2 | 只靠 `.git` 排除圍欄；容器內 `/app` 可寫又沒 `.git`，可能在 repo 內建出圍欄 | 屬實：`docker-compose.dev.yml` 的 `./rag-orchestrator:/app` 可寫，其餘 repo 掛載為 `:ro` | **FIX**：`text_containment.py` 一處加「realpath 位於 rag root 下即拒」；補測試 |

- 以上為實質修改 ⇒ 開新的就緒週期，只送**一次**收尾審查；再 REVISE 就暫停、交業主。
- **收尾審查（fresh plan-verifier）：S0＋S1 READY。**

## 10. 執行紀錄

- **業主 2026-09-25「核可，照建議」**，也就是以下全部照建議：
  - D1：只重判 184 題
  - D2：先試跑 2 判者，扇出上限 10M `subagent_tokens`
  - D3：每代理 30 格
  - 執行模式：ASK
  - DSP-071：用釘住 commit，已寫進 `.claude/DECISIONS.md` DSP-071，來源＝業主，範圍限本線
- **S0＋S1 完成（security-executor 實作；fresh verifier CONFIRMED）**：
  - 新測試 `test_outline_curation_real_questions_req.py`：38 條綠；26 個變異各自轉紅（實作者），另有 verifier 自做 5 個變異，也都轉紅。
  - 全套單元 3923 passed／9 failed（與 HANDOFF §4 那 9 條逐名相同）／3 skipped。
  - 舊流程 15 項輸出與改動前逐位元相同（實作者）；verifier 另比對 `answerability_args` 的完整版與 `--slim`、prepare 的 prompts 與 manifest，也都相同。
  - 守門對抗測試（相對路徑、`..`、symlink、rag root 下、大小寫變體、模組缺席）在主機與容器都擋下。
  - 其他驗收：
    - 鏡像 `diff -rq` 無輸出
    - `def require_contained` 只有 `rag-orchestrator/tools/text_containment.py` 一處
    - S0 三條規則命中 `.gitignore:155–157`
    - 真正本計數 515／509／112
    - `make audit` 只剩不變量 34（既有的「合約範本有哪幾種」）
  - 改動前備份在 session scratchpad `p914-backup/`（18 檔）。
- 執行中另外修的一處：不變量 34 checker 對 `ruler-9.13` 誤把 material 也拿來比對，已改回 §4 的「只比留出集」（見 Plan 9.13 §11 更正）。
- **留給業主**：
  - ①`.agents/skills/outline-curation/journal/` 有 7 個檔**早已被 git 追蹤**，`.gitignore` 管不到它們；要不要 untrack？
  - ②測試用環境變數 `OUTLINE_CURATION_TEST_RAG_ROOT` 能改變守門模組的載入位置（verifier 判 P4：要蓄意設定才會發生，屬操作失誤層級）；要不要收緊？
- **下一步**：S2 細部的就緒審查（plan-verifier）→ 業主點頭 → G01 兩判者試跑。
- **業主 2026-09-25「開始 S2，照建議」**：同意取消追蹤 `.agents/skills/outline-curation/journal/` 那 7 個檔（`git rm --cached`，只改索引、未 commit、檔案留在本機）；測試環境變數的收緊列為後續事項。
- **S2 就緒審查**：
  - 第 1 輪 REVISE P2：缺逐判者完整性檢查 ⇒ 補上容量前提、`COVERAGE` 四值比對、`compact` 結構標記計數
  - 第 2 輪 **READY**
- **S2 步驟 1–3 完成**（repo `git status` 前後相同）：
  - 轉換器 `source_sha256=759eca49…`，pm 179／prospect 5，run 目錄 700 且有標記檔
  - args：pm 179 格 × 509 候選、prospect 5 × 112；`canon` `9b67e763e9c5`；兩份都帶 `_meta.text_policy=external`
  - prepare：pm 6 組（30×5＋29，每組約 12.4 萬字元）、prospect 1 組（5 題）
- **試跑（pm G01，2 判者，`sonnet`）**：
  | slot | 完整性檢查 | `subagent_tokens` | 判決 |
  |---|---|---|---|
  | s1 | PASS（n 509；first／mid／last 相符；compact 0） | 224,577 | no_source 29／partial 1 |
  | s2 | PASS（同上） | 236,465 | no_source 25／partial 5 |
  - u＝230,521 ⇒ 全案外推 ≈ **3.33M**（上限 10M）。試跑累計 461,042。
  - 兩判者 label 一致 **26/30（0.867）**：
    - 兩人都判 no_source：25 格
    - 兩人都判 partial：1 格（`b771d7c44194`），但對到的細目不同
    - 不一致 4 格：皆為 s1 判 no_source、s2 判 partial（s2 信心 low／medium），扇出後由第 3 判者裁
  - ⚠️ 收件相容問題：判者以 `SubagentHandback` 工具交件，`save_verdict.py` 取的是「最後一則 assistant 文字」（交件後的收尾短句）⇒ 解析失敗。
    - ⛔ 未改 skill 程式（不在核可範圍）
    - 改在 repo 外加 `~/jgb-archive/ruler-9.13/scripts/handback_to_jsonl.py`：抽出交件內容，只寫進圍欄內，並附負對照；之後照常交給 `save_verdict.py` 驗證
    - skill 端要不要支援 handback，列為後續事項
  - ASK 模式 ⇒ 停下交業主，等業主決定是否扇出。
- **業主「展開」後的扇出結果**：
  - 14 位判者全數通過完整性檢查（pm 12：n 509；prospect 2：n 112；compact 皆 0）。
  - prospect：一致 5/5（no_source 3／partial 2），已 finalize。
  - pm：一致 144/179＝**0.804**（剛過 0.80），不一致 35 格進第 3 判者。
  - 累計 `subagent_tokens` 3,201,105（含下述作廢的第 3 判者 224,543）。
- ⛔ **停止條件觸發：第 3 判者完整性檢查 FAIL**。它回報 `n=35`，first／mid／last 都是**格 id**：它把「本組待判格（35 格）」誤當成候選標頭，而不是 `## 候選（509 筆…）`。
  - 依 §4，判決作廢、未存。
  - 它引用的細目遍及 A–E 架，看起來有讀到候選，但檢查無法證明。
  - 12 位一般判者用同一套措辭都判讀正確 ⇒ 研判為 brief 措辭歧義，而不是讀取被截斷。
- **目前的上下界（只用兩判者已一致的 149 格）**：
  - no_source 125／partial 23／answerable 1；爭議 35 格
  - ⇒ N_an ∈ [1, 36]；「仍是缺口」（N_ns＋N_pa，未決也算缺口）∈ [148, 183]
  - P1 的門檻 18 落在區間內 ⇒ **第 3 判者的結果決定 P1**。
- 待業主裁：是否以明確化的 brief 重跑第 3 判者一次。明確化＝「候選標頭指以 `## 候選（` 開頭的那一行，⛔ 不是待判格標頭」。約 22.5 萬 token，累計約 3.43M。
- **業主「照建議」⇒ 第 3 判者以明確化的 brief 重跑（僅此一次）**：完整性檢查 PASS（n 509、first／mid／last 相符、compact 0），245,998 token。
- **S2 完成**：
  - collect：pm total 179、agree 144（0.804）、`needs_rubric_revision=False`；prospect 5/5。
  - finalize：兩受眾皆 exit 0（run-id 分開）。
  - **累計 `subagent_tokens` 3,447,103**，含作廢的第 3 判者 224,543（上限 10M）。
  - repo `git status` 前後相同。
- **§0 五類計數（加總 184 ✓）**：
  | | N_ns | N_un | N_pa | N_an | N_dn |
  |---|---|---|---|---|---|
  | pm（179） | 136 | 6 | 35 | 2 | 0 |
  | prospect（5） | 3 | 0 | 2 | 0 | 0 |
  | **合計** | **139** | **6** | **37** | **2** | **0** |
- **P1 判定（依先定判準）**：N_un＝6 ≤ 18，且 N_an＝2 ≤ 18 ⇒ **9.13 的 48.3% 成立**。
  - 修正值：(N_ns＋N_pa)／381 ＝ 176／381 ＝ **46.2%**；未決的 6 題若也算缺口 ＝ 182／381 ＝ 47.8%。
  - 分母 381 裡的 197 題 gold 未重判（見 §0「證不了」）。
- **S2 驗收**：
  - 每位判者（含第 3 判者）都通過完整性檢查：作廢的第 1 次第 3 判者判決未採用 ✓
  - 兩受眾一致率 ≥ 0.80 ✓
  - dropped 0 ✓
  - 加總 184 ✓
- **S3 的輸入**：
  - N_ns＋N_un＝145 題會落到 `not_available`，進 5b 對源
  - N_pa 37 題 ⇒ 桶②（`fine`＋`add_knowledge`）
  - N_an 2 題 ⇒ 桶③
- ASK 模式 ⇒ 停下交業主。S3 的細部執行前，要先做就緒審查。
- **業主「開始 S3，照建議」**：
  - S3 就緒審查第 1 輪 REVISE P2×4：audit 形狀、證據種類、重跑引擎、試跑與上限 ⇒ 全 FIX
  - 第 2 輪 REVISE P2×5：EVIDENCE_RE 的空白、`mode=fixed` scout 做不到、`path` 基準、缺路徑時是停止還是重查、`check` 自測會碰真狀態檔
  - 第 2 輪已是該單位第 2 次 ⇒ 依規則停止自動重送，由主 session 逐條裁決：**全 FIX**（見 §2 S3 步驟 5／6／8、§4），並實跑腳本自測（ingest 13/13；`check` 三案＋狀態檔 sha 不變）⇒ 開新就緒週期，只送**一次**收尾審查
- **S3 步驟 1 已做**：釘住 commit 匯出 5,882 檔＝樹 5,882；jgb2 repo `status` 0 變動。
- **外洩掃描基準**：寬掃描在 S3 寫入前已命中 86 行，全在 `tests/`。其中 `dict_residual` 命中的全是 3 字元、正本裡也出現的產品通用詞，其餘是 `at`／`digits4` 的測試佔位。已存成基準（檔名＋行雜湊，無內容），S3 驗收只看**新增命中**。
- ⚠️ **事故（主 session 自己造成，已還原）**：
  - 經過：2026-09-25 22:15，`leak_scan.py` 為了沿用規則，執行了 `scan.py` 的模組；`scan.py` 在模組層級就跑 `main()`，覆寫了 archive 的 `scan_hits.json`（2 → 17,980 位元組）與 `owner_random30.json`（4,702 → 5,590）。
  - 還原：`SCAN_FILE=masked_clean.json` 重跑（固定種子），兩檔大小回到 2／4,702，結果「898 題 0 命中」與 Plan 9.13 §11 相符。原檔當初沒記雜湊 ⇒ 無法證明逐位元相同，只能以輸入、種子、大小三者一致推定。
  - 未外流：檔案一直在 archive（600），stdout 只印計數。
  - 已改：`leak_scan.py` 改為逐字抄規則，⛔ 不再 import 或執行 `scan.py`；事後確認兩檔的 mtime 與大小未再變動。
- **S3 收尾審查（fresh plan-verifier）＝REVISE P2×2**：
  - ① 程式／help 證據路徑沒有限定在 `$J`、幫助中心目錄內
  - ② 步驟 10 沒帶旗標，跑不到規則二；規則二的範圍與驗收寫的不一致
  - 主 session 兩條都 **FIX**（腳本自測 16/16；`leak_scan` 規則二改為一律執行，並把驗收範圍寫清楚、附理由）
  - ⚠️ 依規則：**收尾審查不能再開下一輪**，停下交業主，由業主決定可否以本修正直接開始 S3（試跑 1 批），或指示再審一輪。
- **業主（2026-09-25／26）「開始 S3 試跑，照建議」**：
  - 步 5 reweigh：pm `not_available` 142／`fine` 37（`add_knowledge` 35＋無補法 2）；prospect 3／2 ⇒ 合計 145／39，與預測相符
  - worklist：142＋3
  - 分批：改成同架平均分、未分類與 NEW 併為一批 ⇒ 12 批（A 6、B 3、C 11、D 17×3、E 22＋21、G 11、H 3、I 4、X 13）
  - repo 相對 S2 結束無變動
- **S3 試跑（batch-04，D 架 17 題；唯讀 `scout` 角色，定義檔 `model: haiku`）**：
  - `subagent_tokens` 102,681 ⇒ u_s3；累計 3,549,784；外推全案 ≈ 3.55M ＋ 11 × 0.103M ≈ **4.68M**（上限 10M）
  - 機械複驗 15/17 過。失敗 2 筆：`48d6f1f589a7` 的證據寫成自由文字、正對照路徑與 negative 不同；`e89dfd4febaf` 用了自組名 `handle()`
  - **品質不及格**：
    - owner_needed **12/17（71%）**，理由多為「沒找到明確的 X」。這類應判 `verified_absent` 並附正對照，⛔ 不該交業主，違反業主 2026-09-07「問業主是盤查窮盡後的剩餘」
    - `topic` 用英文 snake_case，不是 ≤20 字的中文一般化主題
    - 抽看 verified_fact：`ebdf63d65846` 的 `fact` 說「確認期限 30 天」，但所附幫助中心句講的是「點退時機：租約 30 天內到期」⇒ 事實與證據不相符
  - 研判：此工作需要判斷力，`haiku` 的 scout 不勝任。
- 待業主裁：scout 的模型與 brief 要不要換（見交業主訊息）。
- **業主「照建議」⇒ 第 2 次試跑（同 batch-04；`scout` 角色、`model: sonnet` 覆寫〔業主核可的計畫變更〕、brief 收緊 owner_needed 三條件）**：
  - `subagent_tokens` 67,073（比 haiku 少），累計 3,616,857
  - 收件腳本補一條容錯：scout 把 PHP 的 `$` 寫成 `\$`，不是合法 JSON 跳脫 ⇒ 只修這一種；自測仍 16/16
  - 機械複驗 16/17：`48d6f1f589a7` 的正對照 path 與 negative 不同
  - 狀態：owner_needed **12**／verified_fact 4／verified_absent 1 ⇒ **換模型沒有改善 owner_needed 比例**（haiku 也是 12）
  - scout 自己註明「批次太大、追不到那麼深」；12 題中有 6 題的理由是「(c) 超出本次搜尋深度／未逐一追蹤」＝沒查完，不是真的定不了
  - ⚠️ **抽查抓到 2 條錯誤事實**：`90170e3f51de`、`32e60ab5d92d` 判「系統支援同一合約新增第二位承租人」，但證據 `app/Modules/CustomerService/ContractService/…::addTenantToContract` 掛在 `Admin\CustomerServiceController`（路由 `admin.customer_service.*`），是 **JGB 內部後台**，不是業者可用的產品功能
    - 定義 D1 本來就排除 `Admin\*`／`Internal\*`，但 scout brief 漏寫這條範圍
    - 機械複驗抓不到（證據確實存在於 `$J`）
- 研判：根因是**每題的盤查深度不夠（一個 scout 17 題）＋ brief 沒寫產品範圍**，不在模型。
- 待業主裁：縮小批次並補範圍規則後，第 3 次試跑（見交業主訊息）。
- **業主「照建議」⇒ 第 3 次試跑**（batch-04 拆 04a／04b／04c＝6／6／5 題；`scout`＋`sonnet`；brief 加兩條：產品範圍排除內部後台、⛔「超出搜尋深度」當理由）：
  - 收件腳本加「證據全在內部後台 ⇒ 退回」（`INTERNAL_PREFIXES`＝`app/Http/Controllers/{Admin,Internal,Vendors}/`、`app/Modules/CustomerService/`、`resources/views/admin/`）
    - 查證：CustomerService 模組的路由是 `prefix 'admin/customer-service/contracts'`＋`admin_allow_ip`
    - 另外移除 `::` 啟發式：PHP 的 `Class::CONST` 是合法的逐字程式碼，而逐字檢查本身就擋得住自組名
    - 自測 18/18
  - `subagent_tokens` 67,641＋93,471＋94,492＝255,604（每題約 1.5 萬）；累計 3,872,461
  - 機械複驗 17/17 過
  - **狀態：verified_fact 8／verified_absent 2／owner_needed 7**（前兩次都是 4／1／12）
  - **修正了前兩次的錯判**：
    - `48d6f1f589a7` 由「沒有」改為「有」：`resources/structures/contract/edit/form.php` 有「第四台」費用項
    - `32e60ab5d92d` 由「後台證據」改為業者頁面證據：`src/pages/contracts/edit/tenantInfo/Index.jsx::addAdditionalTenant`，上限 10 筆
  - 主 session 抽查 3／8 條 verified_fact 對碼成立：`32e60` 的 `addAdditionalTenant` 與 `>= 10`、`48d6` 的 `form.php` 「第四台」、`ebdf` 的 `cancelMoveOut` 走非後台 API 路由 `api.contract.cancel.move.out`
  - **仍有瑕疵**：
    - ① 跨格不一致：`90170e3f51de`（owner_needed，雙具名承租人）與 `32e60ab5d92d`（verified_fact，其他租客最多 10 筆）是相近主題，結論卻相反
    - ② `10e43c55dc28` 的理由仍屬「需更完整追蹤」，違反 brief
    - ③ `7b5c41b4e638` 以「範本改名歷程靜態不可知」判 owner_needed；但「現行名稱是什麼」本身答得出來，應可改判 verified_fact
  - 研判：小批次＋範圍規則有效；剩下的是跨格一致性，以及少數理由不合規。
- 待業主裁：扇出剩餘 128 題（≤6 題／批），並加「收尾一致性複查」（見交業主訊息）。 ⇒ 大綱與第一個可執行片皆 READY，交業主核可（`next_gate: user_approval`）。S2／S3 的細部在執行前各自再過一次就緒審查。
- **業主「照建議」⇒ S3 全面執行（2026-09-25～26）**：
  - 扇出：剩餘 128 題拆 25 批（`batch-r01`～`r25`，每批 ≤6 題），`scout`＋`sonnet`，brief 沿用第 3 次試跑（產品範圍、⛔「超出搜尋深度」當理由）
  - 收件：每批過 `ingest_audit.py` 機械複驗；複查佇列 28 格（機械複驗失敗 17＋理由不合規／跨格不一致），拆 14 批（`batch-k01`～`k14`，每批 2 格）退回重查一次
  - `finalize_s3.py` 合併初跑與複查 ⇒ `audit/final.json`
  - ⚠️ 看完結果後改過一次分類正規式：`UNCLEAR_RE` 漏了「遮罩」「上下文」兩個同義詞，補上後 unclear 12 → 14（`5b6fad016640`、`f7970b89bd25`）。只影響「交業主清單」與「題意不明清單」之間的分流，⛔ 不影響三態與 P1。備份 `scripts/finalize_s3.py.bak-v1`
- **主 session 對碼（§2 S3-3）**：
  - 抽 7／62 條 `verified_fact`（固定種子，排除試跑已抽的 3 條）：6 條成立；`6b5e55ab0fed`「系統無自助改手機入口」超出證據（`/users/verify/phone` 路由未限定只給未綁定者）⇒ 帳本收窄
  - 回填帳本時逐條讀完 62 條，另抓到：
    - `77cba6a26bca` **錯**：scout 以 `utf8mb4_unicode_ci` 判「Email 比對不分大小寫」；但 `User::setEmailAttribute` 以 XXTEA 加密後存、比對用密文相等，寫入與比對前都不轉小寫 ⇒ 更正後以主 session 自己的證據記為事實
    - `c18cbfb4fdc7`／`e093019fff73` 看似互斥、其實互補：排程最多提前產生到下個月的帳單 ⇒ 合併成一條
  - 15 條 `verified_absent` 的正對照皆由收件腳本實跑；逐條看否定查詢範圍，`c79cb91a25c7` 的否定查詢只涵蓋合約編輯頁，而 `app/Estate.php`、`app/Jobs/ContractsAllExportJob.php` 含同一組關鍵字 ⇒ 否定結論不成立，改判 `owner_needed`（併入 unresolved）
- **S3 結果（145 格，加總 145 ✓）**：
  | | verified_fact | verified_absent | owner_needed | unclear_question | unresolved |
  |---|---|---|---|---|---|
  | pm（142） | 60 | 13 | 51 | 14 | 4 |
  | prospect（3） | 2 | 1 | 0 | 0 | 0 |
  - unclear／unresolved 在 `source-audit-*.json` 裡的 `status` 都是 `owner_needed`（schema 只有四態），以 `note` 區分
  - unresolved 4：`31b33da327f0`、`53207e659ced`、`b360fbefe4b2`（兩次機械複驗未過）、`c79cb91a25c7`（主 session 推翻）
- **四桶（加總 184 ✓）**：① 145（上表）／② 37（`fine`＋`add_knowledge`）／③ 2／④ 0
- **步 7 帳本**：`docs/knowledge/jgb-product-facts.md` 新節 `{#p914}`，46 條、錨點 47 個（含節錨點），62 格全數對上、無多無漏；抽 13 條新寫的引用字串在 `$J` 逐字存在
- **步 8 `check`**：兩受眾皆 exit 0、`unaudited=0`（pm 60／13／69；prospect 2／1／0）；`session.json` sha 前後同為 `3105cbe7d0c5f948`
- **步 9 open-questions**：82～132 共 51 則業主題；133～136 共 4 則「對源未過」（⛔ 不是業主題）。unclear 14 則不併入，另列交業主
  - `outline_gate` 每次 Edit 都報「`line_id` 第 44 行」：與 HEAD 逐位元相同（md5 `5d449846…`），是既有內容、非本次引入 ⇒ 交業主裁
- **步 10 外洩掃描**：
  - 規則一（≥8 字共同子字串）初跑 4 行；1 行是 scout 主題沿用了客戶措辭 ⇒ 改寫；剩 3 行（帳本）都是程式逐字的產品用語，客戶問句也照抄了畫面文字：
    - 兩個合約狀態名（帳本 `p914-contract-exempt-register-signed`）
    - 齒輪選單順序（`p914-contract-gear-menu`）
    - 一個通知名（`p914-atm-amount-mismatch`）
  - 規則二新增 69：`digits4` 全是 `cell_id` 或標題日期（去掉後 0 剩餘）、`url` 全是 `app/Http/…` 路徑、`at` 是 Blade 的 `@if`、`dict_residual` 命中「業者」「內部」「IG」（SIGNED）等通用詞、`phone_like` 是日期
  - ⛔ 依 §4「帳本外洩檢查命中」停止條件 ⇒ **停下交業主裁**，步 11 fresh verifier 等裁決後再跑（若遮蔽會改到帳本，先驗等於白驗）
- **事故／偏差**：
  - scout 在部分 `why_unresolvable` 引用了題目片段，違反 brief；只存在 repo 外圍欄內，進 repo 的一律由主 session 改寫成一般化主題
  - `48ea4e9e16e8` 的理由自承兩個子問未追完，仍以 owner_needed 收件（收件規則沒擋住這種措辭）
- **成本**：`subagent_tokens` 累計 **6,435,923**／10M（S2 3,447,103；S3 試跑 425,358、扇出 1,794,006、複查 769,456）
- **業主裁（2026-09-26）**：外洩規則一剩的 3 行（程式逐字產品用語）**放行**，接著跑步 11 fresh verifier；open-questions 第 44 行 `line_id`（既有內容）**先不動、另案**。
- **步 11 fresh verifier 第 1 次＝REFUTED**（138,605 token）：C1～C4、C7 CONFIRMED；C6 實質成立
  - **F1（P2，已重現、FIX）**：`30961bcd1289` 的押金差額規則只在新北住都延長續約成立——`app/Contract.php` 守衛 `canSeeNthurcSocialHousing() && isRenewContract() && empty($prevBill)`（註解「新北住都續約第一筆帳單繳押金計算方式」）；`previous_deposit_amount` 只由 `ContractService::nthurcExtension` 寫入；一般續約第一張帳單不列押金（`empty($prevBill) && !$this->isRenewContract()`，另一條續約分支只接續父合約的租金序列）。本格情境也不是續約
    - 處置：帳本 `p914-renewal-deposit-diff` 收窄為新北住都延長續約、不再掛格；該格改判 owner_needed＋unresolved，open-questions 137
  - A1（P3、FIX）：本檔 §10 逐字列了那 3 個產品用語 ⇒ 改成指向帳本錨點
  - A2（P3、FIX）：帳本「email 相關 `strtolower` 只在報表」不對，內部後台與外部 API 也有 ⇒ 改寫，並補「`users.email` 明文與密文並存」的註解事實
  - A3（P3、DEFER）：`50586cf08df3` 事實正確，但題目沒說是哪種虛擬帳號，是否答到題目未證 ⇒ 交業主，不改判
  - A4（P4、FIX）：open-questions 節標題範圍
  - 修正後三態：fact 61／absent 14／owner_needed 51／unclear 14／unresolved 5（加總 145）；兩受眾 `check` 皆 exit 0、`unaudited=0`
- **步 11 收尾 fresh verifier＝CONFIRMED**（K1 F1 修正、K2 A2 修正、K3 計數與 `check` 出口、K4 open-questions 82～137、K5 外洩只剩業主放行的 3 行、規則二無人名／地址／電話／社區名）⇒ **S3 驗收通過**
  - 未修、交業主（P3／P4 依規則不動已 CONFIRMED 的候選，DEFER）：
    - A-1（P3）：新北住都押金區塊的守衛只看「是新北住都團隊＋續約」，沒限定來自 `nthurcExtension`；新北住都團隊若走一般續約，第一張帳單會列全額押金 ⇒ 帳本「一般續約不列押金」應限定為非新北住都團隊（要先查前端是否對新北住都隱藏一般續約）
    - A-2（P4）：車位押金差額為負時列的是負數「車位押金」，不是「退押金」
    - A3（P3，第 1 輪）：`50586cf08df3` 是否答到題目未證
- **S3 完成（ASK ⇒ 停下交業主）**。
- **業主「照建議」（2026-09-26）⇒ 主 session 重新對源 5 格 unresolved＋處理收尾 verifier 的 A-1／A-2**（只讀 `$J`，⛔ 不讀題目；依 scout 的一般化主題與已查過的程式定命題）：
  - `31b33da327f0` ⇒ fact `p914-duplicate-remittance`：單筆國泰 ATM 已付款後再入金只記「該訂單已被處理」、不沖帳；固定虛擬帳號一律進儲值餘額、同一通知指紋去重。「業者端有沒有退還操作」未證，寫在條目裡
  - `53207e659ced` ⇒ absent：`催繳通知書|催繳函|催告書|存證信函` 在 `$J` 0、幫助中心 0；正對照「催繳租金」`$J` 8、「催繳」幫助中心 2
  - `b360fbefe4b2` ⇒ fact `p914-receipt-email`：`bill_paid` 寄款項確認信附收據 PDF；`src` 無重寄（`重寄|重新寄送|再次寄送|resend` 0／正對照「寄送」72）
  - `c79cb91a25c7` ⇒ fact `p914-estate-pet-cooking`：`pet_limit`／`fires_limit` 是物件出租條件（搜尋＋合約匯出），合約相關 5 個路徑 0／正對照 `deposit` 350；合約上只能寫補充條款
  - `30961bcd1289` ⇒ absent `p914-no-deposit-carryover`：押金移轉 8 種寫法 0／正對照「點退押金」65
  - A-1／A-2 已對碼補進 `p914-renewal-deposit-diff`：車位押金差額為負列負數「車位押金」；守衛只看新北住都團隊＋續約，新北住都非社宅合約能否走到一般續約寫明「未追證」
  - open-questions 133～137 移除（非業主題、已解決），節標題改回 82～132
  - 三態：**fact 64／absent 16／owner_needed 51／unclear 14／unresolved 0**（加總 145）；兩受眾 `check` exit 0、`unaudited=0`；`session.json` sha 不變；外洩規則一仍只有業主放行的 3 行，規則二新增 74 全屬日期／路徑／通用詞／Blade
  - 腳本備份 `scripts/assemble_audit.py.bak-v1`
  - **fresh verifier＝CONFIRMED**（R1 5 格證據／敘述／答題／否定查詢重跑、R2 押金條目、R3 計數與 `check`、R4 open-questions 82～132、R5 外洩）
  - DEFER（P4，依規則不動已 CONFIRMED 的候選）：`p914-duplicate-remittance`「同一通知指紋去重、不會重複儲值」有例外——銀行電文欄位不完整時（`$txUniqueId === ''`）跳過指紋檢查、只發 Slack 警示（`錢包入金但電文欄位不完整`），程式註解稱極少見

## 附錄 A：F3 重跑指令

```bash
docker compose -f docker-compose.dev.yml run --rm -T rag-orchestrator python3 -c "
import sys; sys.path.insert(0, '/.claude/skills/outline-curation/scripts')
import canon_items as ci
from services.agent.outline import _count_tokens
doc = ci.parse_canon_auto('/app/canon/jgb'); fs = doc.fines()
t = lambda xs: _count_tokens('\n'.join(f.id+' '+f.title+'\n'+'\n'.join(f.content_units) for f in xs))
print(len(fs), t(fs)); [print(a, len(s), t(s)) for a in ('property_manager','prospect') for s in [[f for f in fs if a in (f.target_user or ())]]]"
```
