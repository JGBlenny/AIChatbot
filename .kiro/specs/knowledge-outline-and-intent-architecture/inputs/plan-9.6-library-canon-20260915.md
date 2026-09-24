# 9.6 圖書館正本（DSP-058）計畫 v4 — 2026-09-15

> 狀態：**已落地（2026-09-15）**。業主「開工」放行 v4；S1／S2／S3／S4 各由 fresh verifier CONFIRMED（交件與驗證紀錄見 `brief-9.6-S{1,2,3,4}-20260915.md` 與 tasks.md 9.6）。⛔ 未 commit、⛔ 未部署。
> 前史：收尾審查（第 3 輪）REVISE 三條（P1×1、P2×2）全部 FIX 折入（§9）後依規矩 PAUSED 交業主。

## 0. 定案（DSP-058，業主 2026-09-15）

一份目錄＋九架大綱，受眾＝細目屬性；取代 DSP-052「受眾各自正本」。

```
rag-orchestrator/canon/jgb/A.md … I.md   正本：每粗目一檔（一架）；H 為空架（兩舊檔 H 皆 0 條）
rag-orchestrator/canon/jgb/CATALOG.md    衍生目錄：每細目一行 id｜標題｜target_user｜approved 講法；⛔ 不含內容、不手改
rag-orchestrator/canon/jgb.json          衍生導出（沿用 export_json 逐位元比對）
docs/archive/2026-09/canon-pre-library/  舊 prospect／property_manager .md+.json（⛔ 不是現況；表頭註明已掉出 hook CANON_RE 掃描）
```

檢索順序不變：查目錄選細目（K=5）→ 只取那幾條內容。受眾／社宅／客製在選細目時以屬性過濾。**受眾視圖仍存在**：同一份 canon 依靜態身分產 prospect／pm 兩份 `OutlineDoc`，登記鍵與 `OutlineDoc.audience` 都是受眾字面。

## 1. 目標與非目標

**目標**：程式、正本、skill、測試、文件描述同一形態；prospect 與 pm 身分各自看到的細目集合**與今天逐條相同——含「未審細目在本受眾視圖以標題現身、內容空、不可引用」這個刻意設計**（`build_outline` 的過濾只走受眾／業態軸，⛔ 不把未審細目連標題一起拿掉；內容仍只給已審）。**中途每個切片落地時工作樹都是綠的**（S1／S2 舊路徑原封；S3 含所有簽名呼叫點同步）。

**非目標**（⛔ 不做）：補內容、pm 題集、H 存廢、租客線、aggregate face、部署、資料庫 UPDATE、`canon_visible` b2c 分支任何改動（§5-3 REJECT）。

## 2. 現況縫（全部對碼，符號可 grep）

| 縫 | 現況 | 改後 |
|---|---|---|
| `canon_parser.AUDIENCES`／`FRONT_MATTER_KEYS`／`CanonDoc.audience` | 一檔＝一受眾；front matter 七鍵；細目 id 首段須等於 `audience` | **新路徑**：架檔 front matter 六鍵 `coarse, title, scope, version, reviewers, language`（⛔ 無 `budget_tokens`、無 `target_user`／`business_types` 檔級預設）；`CanonDoc` 加欄位 `name`（單檔路徑填 `audience` 值，目錄路徑填 `"jgb"`）；**`CanonDoc.audience` 保留**（目錄路徑填 `"jgb"`，切換後 `build_outline` 不再拿它當視圖受眾）；細目 id 首段須等於 `CanonDoc.name`（常數 `CANON_NAME="jgb"`；parser 與 hook 同值）。**舊 `parse_canon(path)` 單檔語義原封**（封存檔測試與 S2 遷移腳本的輸入都靠它） |
| 細目 `target_user`／`business_types` | 缺省繼承檔級預設（現行兩檔 53 細目 **0 條**自帶） | **只在 `parse_canon_dir` 路徑**兩者皆必填非空（`_build_fine(..., require_fine_attrs=True)` raise）；`target_user` 值域 `KNOWN_TARGET_USERS`、⛔ `all_users`；`business_types` 須含 `system_provider` |
| `parse_canon(path)` | 單檔 | 原封；新增 `parse_canon_dir(dir)`：**固定白名單** `A.md…I.md`（⛔ 不 glob）；白名單外 `.md`（除 `CATALOG.md`／`README.md`）⇒ `CanonFormatError`；每檔 `resolve()` 後 parent＝base、拒符號連結；每檔恰一個 `## X {#X}` 且 X＝檔名（零細目允許）；合成一份 `CanonDoc(name="jgb", audience="jgb")`；`canon_sha256`＝各檔 sha 依序串接再 sha；`see_also` 跨架 |
| `export_json` | 單檔 | 同；新增 `export_catalog(doc, path)`（決定性） |
| skill 新腳本 `canon_to_library.py`（**S1 出貨**） | 不存在（`remap_ids.py` 只做驗收材料 id 純文字改寫；`apply_proposal.render_remap` 是提案驅動的重切渲染，兩者都不切架、不落明列屬性） | 輸入兩份舊正本（`parse_canon`）＋ **`--scopes scopes.json`（九條 `scope` 文字，來源＝本計畫附錄 A，由 `docs/knowledge/jgb-domain-map.md` §2 脊椎表與 §3 邊界規則整理；業主在 S2 交件時過目，⛔ 不是補知識內容，是索引的歸位判準）** → 每細目 id 前綴改 `jgb/`、`target_user`／`business_types` 由檔級預設落成明列、`see_also` 同步 → 依粗目寫 `A.md…I.md`（H 空架）→ 呼叫 `export_catalog`／`export_json`；決定性（同輸入逐位元同輸出）；輸出 `id_map.json`（全 keep 形狀，供 `remap_ids.py` 改驗收材料） |
| `canon_assembler.load_canon_or_die(dir, audience)` | 按受眾讀檔＋`.json` 比對 | S3 切換：`load_canon_or_die(dir)`：`jgb/`＋`jgb.json`＋`jgb/CATALOG.md` 三者逐位元同源。**CATALOG 的安全控制點是這裡，⛔ 不是 hook** |
| `_CANON_REGISTRY`／`get_canon(audience)`／`canon_registry_shas` | 受眾鍵；tenant 靠 `get_canon("tenant") is None` 天然擋 | 單一 `register_canon(doc)`／`get_canon()`；**`make_outline_resolver` 與 `runtime._select_outline` 取 doc 前先過「受眾有登記視圖」閘**（只有 `_STATIC_TOC_IDENTITY` 內的受眾拿得到），tenant／未登記受眾維持 `NO_MATCH`；health 回 `{"jgb": sha}` |
| `canon_assembler.build_outline(doc)` | **所有**細目進 `OutlineDoc`（未審＝標題＋`text=""`），`OutlineDoc.audience=canon.audience` | `build_outline(doc, audience, identity, vendor_business_types)`：**先過受眾／業態軸再組**——`canon_visible` 拆成 `_axes_visible(effective_target_user, mode, fine, vbt)`（受眾＋業態，不看 reviewed）與 `canon_visible`＝`reviewed_by is not None` **且自身先呼叫 `VendorKnowledgeRetrieverV2._effective_target_user(identity.target_user)` 再傳給 `_axes_visible`**（⛔ 正規化呼叫必須留在 `canon_visible` 本體——不變量 29b 規則②以 `_references_name(canon_visible, TARGET_USER_NORMALIZER)` 檢查它；對外行為不變，`test_visible_subset_sql_equiv_req` 仍釘 SQL 同式）；`build_outline` 同樣先 `_effective_target_user` 再呼叫 `_axes_visible`／`canon_visible`；`build_outline` 對 `_axes_visible` 為假的細目連 id／標題都不進，為真者：`canon_visible` 真 ⇒ 含內容、假（未審）⇒ 標題＋空內容（今日語義）；**`OutlineDoc.audience`＝視圖受眾字面，⛔ 不得是 `jgb`**；`build_outline` 加進 `scripts/audit/checks/agent_boundary.py::CANON_VISIBLE_CALLERS`，**同步改 `_self_test_29b` 的 `clean_src` 與 `tests/unit/audit/test_agent_boundary_req.py::_CANON_CLEAN_SRC` 加第三個 caller** |
| `runtime.py::_select_outline` | `get_canon(audience)`；`canon is None or audience != identity.resolved_audience()` ⇒ 原樣回整份 | 改取 doc；**保留 audience 不符的閘且 fail-closed**（不符 ⇒ ⛔ 不回未過濾整份；回空候選＋`miss_kind`，語義同 `none_visible`） |
| `outline._STATIC_TOC_IDENTITY`／`build_audience_outline(audience)` | 受眾→靜態身分→讀該受眾檔 | 保留表；同一份 canon 依靜態身分產受眾視圖；`check_budget` 對**過濾後**視圖 |
| 預算 `check_budget(doc, min(default_token_limit(aud), canon.budget_tokens))`；`default_token_limit` 讀 env `int()` 無鉗制 | 正本 `budget_tokens` 是硬天花板 | `default_token_limit` 改為 `min(env, OUTLINE_TOKEN_LIMIT_DEFAULTS[aud])`（常數表是天花板、env 只能往小調）；`app.py` 事後那次 `check_budget` 自然同受鉗 |
| `app.py::_init_agent_runtime` | 每受眾各自 load＋prepare | load 一次；`FineIndex.prepare(canon)` 一次；`selectors[aud]` 共用同一 index；`register_index(aud, index)` 兩鍵同物；**單一正本失敗＝兩受眾都不可用（fail-closed，語義由「基準受眾失敗才紅」改為「正本失敗即紅」）**；health `index_registry_states` 的 `entries`／`content_keys`／`prepared_sha` 改為整份的量、兩受眾相同，⛔ 不得當受眾覆蓋率指標（附註） |
| `mcp_facade._outline_for_audience`／`stage` | 受眾鍵查 `agent_outlines` | 不變 |
| `resolve_canon_dir`／`AGENT_CANON_DIR` | 只在 `DB_ENV=test` 生效 | 不變；覆寫的是 `canon/`（含 `jgb/` 與 `jgb.json`），指到半套 ⇒ `load_canon_or_die` 紅 |
| **其他現存呼叫點（兩輪 verifier 補齊）** | `tools/gapmap/coverage_map.py`（`parse_canon(canon_path)`＋兩處 `canon.audience`）；`tools/agent_outline_dump.py`（`build_prospect_outline`）；`tools/agent_eval.py`；`scripts/audit/checks/canon_visibility_reconcile.py`（`load_canon_or_die(resolve_canon_dir(), CANON_AUDIENCE)`，由 `tests/unit/audit/test_canon_invariants_req.py` 載入）；測試 `tests/unit/agent/test_agent_turn_pm_outline_req.py`（`load_canon_or_die(..., "property_manager")`）、`test_outline_unit_req.py`／`test_candidate_outline_req.py`／`test_agent_policy_kb_outline_req.py`（`register_canon("prospect", doc)` 三處）、`test_candidate_selector_req.py`、`tests/integration/agent/test_outline_req.py`、`test_review_state_visibility_req.py`、`tests/unit/audit/test_agent_boundary_req.py` | **全部併入 S3 同一次落地**（簽名一改就同步）：`coverage_map.py` 改 `parse_canon_dir`＋`canon.name`（`audience` 欄由呼叫端指定）；`agent_outline_dump.py`／`agent_eval.py` 改 `build_audience_outline`／新簽名；`canon_visibility_reconcile.py` 改讀 jgb；測試檔改 fixture／id／簽名 |
| `.claude/hooks/outline_gate.py` | `CANON_RE=^rag-orchestrator/canon/[a-z_]+(-[a-z_]+)*\.md$`；七鍵；id 首段任意 | **`CANON_RE` 改寬 `^rag-orchestrator/canon/.+\.md$` 扣 `README.md`**（不變量：hook 覆蓋 ⊇ loader 讀取）；結構檢查依檔名分流：`jgb/[A-I]\.md` 走六鍵＋一檔一粗目＋X＝檔名＋id 首段 `jgb`＋細目必填兩屬性；其他 `canon/*.md` 走舊七鍵規則（S3 封存前舊檔仍受管）；識別碼／講法唯一／撞凍結題對所有命中檔照跑；`.codex/` 複本手動同步 |
| skill（`apply_proposal.render`／`render_remap`、`--audience`、`structure_propose.output_spec_block`／`coarses_block`、`canon_items.py`、`structure_review_sheet.py`、`diff_report.py`） | 受眾檔 | 讀／寫 `jgb/`（渲染依粗目切檔、每細目寫明兩屬性）；`coarses-jgb.json` 一份；proposal schema 的 fine 加必填 `target_user`；id 規則 `jgb/<粗目碼>/<slug>`；`.agents/` 複本手動同步（S4） |
| `scripts/audit/checks/canon_visibility_reconcile.py` `CANON_AUDIENCE="prospect"` | 讀 prospect 檔 | 讀 jgb；b2b pm／b2b prospect 各命中 ≥1 |
| 測試（`tests/{unit,integration}/agent/test_canon_*`、`test_outline_*`、`test_candidate_outline_req`、`test_agent_turn_pm_outline_req`、`test_fine_index_content_parity_req`、`test_index_eval_req`、`test_probe_three_arm_req`、`test_vendor_business_types_resolution_req`、`tests/unit/_meta/test_outline_gate_req`、`test_pii_scan_req`、`tests/unit/skills/outline_curation/*`＋上列三檔）＋工具 `tools/canon/{index_eval,outline_probe_select,probe_three_arm}.py`、`tools/agent_eval.py` | 受眾檔／id 前綴 | 改 fixture 與 id；`test_build_prospect_outline_registers_same_doc_and_leaves_sha_unchanged` 依 DSP-058 作廢，改釘「prospect 視圖細目 id 集合＝舊 prospect 可見集合經 remap」 |
| 文件 | `canon/README.md`、`.claude/MAP.md`、`SYSTEM_ARCHITECTURE.md` A-9、`AGENTIC_MCP_ARCHITECTURE.md`、`outline-architecture-proposal.md` §6／§11 第 6 列、記憶 `project_outline_catalog_not_chunks.md` | | 圖書館形態；proposal §6 標「DSP-058 取代」 |

## 3. 切片（**依序 S1 → S2 → S3 → S4**；每片落地時樹必綠；下一片等上一片 verifier CONFIRMED）

### S1 契約：新 parser 路徑＋衍生物＋遷移腳本＋hook（**舊路徑原封、現行正本照常解析**）
- 出貨：`parse_canon_dir`（白名單、parent／symlink、id 首段 `CANON_NAME`、細目兩屬性必填）、`CanonDoc.name`、`export_catalog`、`canon_to_library.py`、hook `CANON_RE` 改寬＋依檔名分流。⛔ 不動 `load_canon_or_die`／registry／`build_outline`／runtime／app。
- 驗收（否定帶正對照）：
  ① 合成 fixture 目錄（3 架＋1 空架、6 細目、跨架 see_also、共用 `[prospect, property_manager]`）`parse_canon_dir`＝預期 JSON；
  ② 缺 `target_user`／空／含 `all_users`／缺 `business_types`／不含 `system_provider` 各 ⇒ raise（正對照：同檔合法細目通過）；
  ③ 檔名≠粗目碼 ⇒ raise；④ 一檔兩粗目 ⇒ raise；⑤ 多一個 `Z.md` ⇒ raise（正對照：多 `README.md` 不 raise）；⑥ 符號連結 ⇒ raise；⑦ id 首段 `prospect/` ⇒ raise；
  ⑧ `export_catalog` 兩次逐位元相同；
  ⑧b `scope` 缺鍵或空值 ⇒ raise（正對照：同 fixture 有 scope 通過）；
  ⑨ **相容性**：`parse_canon("rag-orchestrator/canon/prospect.md")`／`property_manager.md` 仍成功且 `canon_sha256` 與改前相同；`scripts/run-tests.sh unit tests/unit/agent` 綠、`integration` agent 子集綠（材料＝版控現行正本）；
  ⑩ `canon_to_library.py` 對兩份現行正本跑兩次，輸出目錄逐位元相同，且 `parse_canon_dir(輸出)` 成功（⛔ 此驗收只寫到暫存目錄，不落版控）；
  ⑪ hook 自測全綠；`canon/jgb/A.md`、`canon/jgb/CATALOG.md`、`canon/foo.md`、`canon/prospect.md` 都命中 `CANON_RE`、`canon/README.md` 不命中；`canon/prospect.md` 仍走七鍵規則通過。
- 執行者：`security-executor`。verifier 針對 ②⑤⑥⑦⑨⑩。

### S2 正本遷移（資料；**舊檔仍在、舊 loader 仍讀舊檔，新目錄與之並存**）
- 步驟：`canon_to_library.py` 產 `canon/jgb/A.md…I.md`（H 空架）＋`CATALOG.md`＋`jgb.json`＋`id_map.json`；`remap_ids.py --id-map id_map.json` 改 `runs/`／驗收材料裡的 id（⛔ 不動 tests 與舊正本，那是 S4）。⛔ 不封存舊檔（S3 切換時同 commit 封存）。
- **停點 1 已盤（2026-09-15，正對照 `prospect/A/account-registration` 存在）**：同架同 slug 碰撞 0、內容 sha 相同 0 ⇒ 純機械。分布 pm D1／E3／F10／G1；prospect A1／B4／C4／D6／E9／F1／G1／I12。
- 驗收：
  ① **全部 53 條**逐條對照（母體＝53，<53 即失敗）：`新 id → (target_user, business_types, reviewed_by, reviewed_at, content_sha256, phrasings 集合, policy, instance_applicability, categories)` ＝ 舊檔同細目（舊檔級預設落成明列後應逐條相等；`see_also` 經 remap 後相等）；⛔ 不只比可見子集（15 條未審在視圖不可見，只比可見會漏掉受眾標錯）；
  ② 未審 15 條的 `target_user`＝其原檔受眾（逐條列出）；
  ③ `parse_canon_dir("canon/jgb")` 成功，`jgb.json`／`CATALOG.md` 與重導出逐位元相同；CATALOG 行數＝53；
  ④ hook 對每架綠（含識別碼掃描）；
  ⑤ 現行啟動與測試不受影響：`scripts/run-tests.sh unit tests/unit/agent` 綠（舊 loader 只讀 `<audience>.md`，正對照：`test_canon_export_sync_req` 仍綠）。
- 執行者：`mech-executor`（腳本已由 S1 出貨，brief 逐步列工具檔＋符號＋輸入輸出）。verifier 針對 ①②③。

### S3 切換：assembler＋outline＋runtime＋app＋facade＋index＋預算＋封存＋**所有簽名呼叫點與測試同步**（**單一不可分割落地**）
- 出貨：§2「其他現存呼叫點」列全部；`canon_visible` 拆 `_axes_visible`；`index_eval.py` 的 `--canon` 支援目錄輸入（`_load_fines` 走 `parse_canon_dir`；`freeze_materials` 對目錄改記 `parse_canon_dir` 合成的 `canon_sha256`，⛔ 不再 `sha256_file` 單檔）＋加 `--target-user <值>` 過濾（只留 `fine.target_user` 含該值的細目，⛔ 不走 `canon_visible`——量尺母體要與舊 prospect.md 的 38 條逐一相同）；`tests/integration/agent/test_visible_subset_sql_equiv_req.py`（`parse_canon(str(CANON_DIR / "prospect.md"))`）改讀 `canon/jgb`；`canon/README.md` 重導出指令改 `parse_canon_dir`＋`export_json`／`export_catalog`；`load_canon_or_die(dir)` 三者同源、單一 registry＋受眾登記閘、`build_outline(doc, audience, identity, …)` 先過濾且 `OutlineDoc.audience`＝受眾、`runtime._select_outline` 改取 doc＋fail-closed、`build_audience_outline` 走視圖、`default_token_limit` 取 `min`、`_init_agent_runtime` 單次 load／prepare、health sha 形狀＋語義附註、`CANON_VISIBLE_CALLERS`＋兩處假樹加 `build_outline`、`test_canon_startup_req.py` fixture 改複製 `canon/jgb/`＋`jgb.json`＋`CATALOG.md`、舊 `canon/{prospect,property_manager}.{md,json}` 移 `docs/archive/2026-09/canon-pre-library/`（表頭「⛔ 不是現況；已掉出 hook 掃描」）、`canon/README.md`／`MAP.md` 正本行改寫。
- 驗收（外洩面是主驗收；材料：①～⑥⑨ 用**合成 fixture**（pm-only／prospect-only／共用各 1＋未審 1），⑦⑧⑩ 用 S2 產出的真實 `canon/jgb/`）：
  ① **視圖零外洩**：兩靜態身分建視圖：pm-only 的 id **與標題**不在 prospect 視圖 `text`；正對照：共用細目兩視圖都在、prospect-only 在 prospect 視圖；母體：兩視圖 section 數皆 > 0。
  ② `resolve_canon_section(outline:<pm-only id>)` 對 prospect 身分＝`NO_MATCH`；正對照 pm 身分回內容。
  ③ `CandidateSelector.select` 對 prospect 身分不回 pm-only id（`_FakeBackend` 先例：`test_agent_turn_pm_outline_req.py`／`test_fine_index_req.py`；向量刻意讓 pm-only 最相似）；正對照 pm 身分回它。
  ④ `Identity(mode="b2b", target_user="tenant")` 可見集合＝∅；正對照 `property_manager` 非空。tenant 受眾經 `make_outline_resolver`／`_select_outline` 取不到 doc ⇒ `NO_MATCH`／空候選。
  ⑤ `OutlineDoc.audience` 與身分不符時 `_select_outline` fail-closed：回傳 outline 不含任何細目節（正對照：相符時含候選）。
  ⑥ 候選集合 ⊆ 該受眾視圖 section id 集合；故意塞視圖外 id ⇒ 走 fallback 而非崩。
  ⑦ 真實正本：未審 15 條在**本受眾**視圖以標題現身、`text==""`、`citable==False`，在**另一受眾**視圖連標題都不在；`resolve_canon_section` 對它們兩身分皆 `NO_MATCH`（正對照：已審 `jgb/A/account-registration` 在 prospect 視圖含內容且 `kb.get` 回內容）。
  ⑧ 啟動：`test_canon_startup_req.py` 綠；`canon_registry_shas()=={"jgb": …}`；`_init_agent_runtime` 對真實正本組出兩視圖。
  ⑨ 預算：`AGENT_OUTLINE_TOKEN_LIMIT_PROSPECT=999999` 時上限仍＝`OUTLINE_TOKEN_LIMIT_DEFAULTS["prospect"]`（正對照：設 1 ⇒ raise）；真實兩視圖 `token_count` ≤ 各自常數。
  ⑩ 不變量 29b：**未改任何檢查器的前提下**該 checker 自測綠（含「29b 正對照：現樹的 `canon_visible` 通過」＝規則② `_effective_target_user` 仍在本體）；且暫時拿掉 `build_outline` 內軸過濾呼叫時規則③紅（驗一次放回）。
  ⑪ 全 repo `*.py`＋`.claude/skills/**/*.py`＋`scripts/**/*.py` grep `canon\.audience|build_prospect_outline|get_canon\(|register_canon\(|load_canon_or_die\(|build_outline\(|budget_tokens|parse_canon\(|canon/prospect\.md|canon/property_manager\.md` 命中集合 ⊆ §2 列出的檔案（正對照：`app.py`／`outline.py` 必中）；未列者＝S3 未完成。
  ⑫ **樹綠**：`scripts/run-tests.sh unit` 0 failed、`integration` agent 子集 0 failed、`tests/unit/audit/` 綠（正對照：暫時還原 `build_outline` 的 `_axes_visible` 呼叫時 29b 紅）。
  ⑬ `index_eval --canon rag-orchestrator/canon/jgb --target-user prospect`：先 `--dry-run` 成功並印 `n=422`／`articles_with_gold`（正對照：指到不存在目錄 ⇒ 大聲失敗），再全跑；受測母體 38 條、id 經 remap 後與 `index-eval-recut-20260915.json` 的母體一一對應；per-type r@5 與該檔逐項相同（同細目同講法同向量快取；有差 ⇒ 停點 4，須說明來源）。
- 執行者：`security-executor`。verifier 針對 ①②③④⑤⑦⑩。

### S4 skill／文件／鏡像收攏（不含任何程式簽名改動——那些都在 S3）
- 出貨：skill 腳本（`apply_proposal`／`structure_propose`／`canon_items`／`structure_review_sheet`／`diff_report`、`coarses-jgb.json`、proposal schema 加 `target_user`）＋skill 測試＋文件（§2 文件列）＋`.agents/`／`.codex/` 手動同步＋記憶更新。
- 驗收：`scripts/run-tests.sh unit` 全綠（含 skill 測試 161 或新增後數字）；`make audit` 不變量 29b／33／34／40／41 不比改前差（3／41 既有紅另案）；**全 repo 無 `prospect/`／`property_manager/` 細目 id 前綴殘留**（`canon/`、`runs/`、tests、tools、skill；正對照：封存檔會命中）；`.agents/`／`.codex/` 複本與正本 diff 為空。
- 執行者：`mech-executor`＋主 session 收尾。

## 4. 回滾
逐切片 commit；回滾＝revert 該切片。S1／S2 落地後舊路徑仍是現況，revert 零風險；S3 是唯一行為切換點，revert 即回到 S2 狀態（舊檔從封存目錄一併回來）。DB 不動。

## 5. 安全面處置（security-reviewer 2026-09-15）
1. 標題是外洩面；唯一未套 `canon_visible` 的攜帶路徑是 `build_outline`，可達點是 `_select_outline` 提早返回 ⇒ **FIX**（§2 兩列＋S3 ①⑤⑩）。其餘六條路徑已套或不含標題。
2. tenant＋b2b 鑰匙：今天與改後皆 0 條；`get_canon("tenant") is None` 的天然保護消失 ⇒ **FIX**（受眾登記閘＋S3 ④）。
3. b2c 「空＝不設限」與 `all_users` 在正本側永遠不可達 ⇒ **REJECT 收緊 `canon_visible` b2c**（會與 `build_visibility_predicate` 分裂，`tests/integration/agent/test_visible_subset_sql_equiv_req.py`＋29b 釘兩側同式）；改 parser 釘（S1 ②）＋ b2c 分支加註「對正本恆假、為與 SQL 同式保留、⛔ 不得刪」。
4. CATALOG 無新增暴露；控制點＝啟動期三者同源、⛔ 不是 hook；loader 白名單防 CATALOG 被當正本讀 ⇒ **FIX**。
5. 單一索引乾淨；health 總量語義變更 ⇒ **FIX（附註）**。
6. env 單方決定上限 ⇒ **FIX**：`default_token_limit` 取 `min`（S3 ⑨）。
7. F1 `business_types` ⇒ **FIX**；F2 hook ⊇ loader ⇒ **FIX**；F3 `runtime.py` ⇒ **FIX**；F4 id 首段 ⇒ **FIX**；F5 候選 ⊆ 視圖 ⇒ **FIX**（S3 ⑥）；F6 `AGENT_CANON_DIR` ⇒ 附註。

## 6. 停點
1. ~~S2 碰撞／相同內容~~ 已盤：無。
2. 任一切片 verifier REFUTED ⇒ 停該切片與後續。
3. 預算超過 ⇒ 停，交業主（⛔ 不自行放大常數）。
4. S3 ⑬ `index_eval` 任一 type 與 `index-eval-recut-20260915.json` 有差 ⇒ 停，須先說明差的來源（母體、講法集、向量快取三者逐一對）才續；⛔ 基線不是 `index-eval-20260907.json`（那是舊 38 細目切法前的材料）。
5. S3 ⑪ 發現 §2 未列的呼叫點 ⇒ 不阻斷 S3，但列入 S4 出貨並在 S3 報告點名。

## 7. 成本
無付費 run；`index_eval` 用既有向量快取（無快取則 53 細目 embedding，< USD 0.05）。代理：security-reviewer 1（已用）、plan-verifier 2、security-executor 2、mech-executor 2、verifier 3。

## 8. 前置
- 9.1a／9.1b 已落地。
- 15 條未審細目維持未審（補審是業主步驟）。
- 主 session 已覆核決定性事實：`runtime.py` `if canon is None or audience != identity.resolved_audience():`；`agent_boundary.py` `CANON_VISIBLE_CALLERS = ("build_canon_toc", "resolve_canon_section")`；`outline.py` `min(default_token_limit(audience), canon.budget_tokens)`、env `int()` 無鉗制；`KNOWN_TARGET_USERS = {'tenant','landlord','property_manager','system_admin','prospect'}`；兩舊檔細目自帶 `business_types` 0 條；`apply_proposal.render_remap` 是提案驅動渲染（非切架工具）；`coverage_map.py` 兩處 `canon.audience`、`agent_outline_dump.py` 用 `build_prospect_outline`。

## 9. 版本變更
- v0→v1：security-reviewer 十二條全數 FIX 折入。
- v3→v4（收尾審查三條，全 FIX）：(P1) `canon_visible` 拆法明寫正規化呼叫留在本體、29b 規則②不動，⑩ 改為「不改檢查器自測綠」；(P2) `index_eval` 加目錄輸入（`_load_fines`→`parse_canon_dir`、sha 改合成值），⑬ 加 `--dry-run` 前置；(P2) ⑪ 樣式補 `parse_canon\(|canon/prospect\.md|canon/property_manager\.md`，`test_visible_subset_sql_equiv_req.py` 與 `canon/README.md` 重導出指令補進 S3。
- v2→v3（plan-verifier 第 2 輪五條，主 session 逐條處置）：(P1 FIX) 所有簽名呼叫點與測試同步併入 S3 單一落地，S3 加 ⑫ 樹綠驗收，S4 只剩 skill／文件／鏡像；(P2 FIX) `test_agent_policy_kb_outline_req.py`＋`agent_eval.py`＋`canon_visibility_reconcile.py` 補進 §2，⑪ 樣式補 `register_canon\(|load_canon_or_die\(|build_outline\(|budget_tokens`；(P2 FIX) `scope` 來源定為附錄 A（由 domain-map §2／§3 整理、業主 S2 交件時過目），S1 加 ⑧b；(P2 FIX) `index_eval` 加 `--target-user` 過濾，基線改 `index-eval-recut-20260915.json`，停點 4 改「有差須說明來源」；(P2 FIX) 未審細目語義保留今日設計——`canon_visible` 拆 `_axes_visible`，`build_outline` 只過受眾／業態軸，§1 目標與 S3 ⑦ 改寫一致。
- v1→v2（plan-verifier 第 1 輪五條全 FIX）：(P1) S1 改為**只加新路徑、舊 `parse_canon` 與現行正本原封**，加相容性驗收 ⑨；(P1) 切片重排 **S1 契約 → S2 遷移（並存）→ S3 切換 → S4 收攏**，S3 的真實正本驗收 ⑦⑧ 有材料可跑、合成 fixture 與真實材料逐條標明；(P2) 遷移工具改為 S1 出貨的 `canon_to_library.py`（`remap_ids.py` 只改驗收材料），brief 逐步列符號；(P2) S2 驗收 ① 改比對**全部 53 條**含 `target_user`，加 ② 未審 15 條受眾逐條；(P2) 補 `coverage_map.py`／`agent_outline_dump.py`／`_self_test_29b` 與 `_CANON_CLEAN_SRC`／三個測試檔進 §2 與 S3⑪／S4。

## 附錄 A：九條 `scope`（索引歸位判準；來源 `docs/knowledge/jgb-domain-map.md` §2 脊椎表＋§3 邊界規則；業主 S2 交件時過目）

| 架 | scope |
|---|---|
| A 帳號與身分 | 註冊、登入、找回帳號、身分（房東／租客／法人／社宅）與個人資料、聯絡方式變更；⛔ 團隊成員權限歸 B |
| B 團隊、人員與大房東 | 團隊建立與成員邀請、角色權限、人員管理、大房東記錄與代管關係；⛔ 帳號本身歸 A |
| C 社區與物件 | 社區建檔、物件新增與批次匯入、刊登與銷售、物件狀態與欄位；⛔ 物件上的租約歸 D、抄表歸 E |
| D 租約（含委託約子題） | 合約建立、簽署、狀態與階段、續約、退租、違約金、租客邀請簽約；委託約（僅法人房東）；⛔ 帳單與押金金流歸 E |
| E 帳務（含發票、收款金流、抄表） | 帳單產生與週期、催繳、滯納金、收款方式與金流商、發票、抄表與水電費；⛔ 修繕流程歸 F |
| F 修繕 | 報修、派工、進度與狀態、修繕通知；⛔ 費用入帳歸 E |
| G 裝置 | IoT 門鎖、密碼、裝置廠商與狀態；⛔ 抄表歸 E |
| H 幫助中心 | 幫助中心入口與使用方式、教學文件位置；⛔ 各功能怎麼用歸該功能所在架（目前空架，存廢另裁） |
| I 方案與導入 | 方案比較與試用、功能矩陣、導入與資料遷移、批次匯入流程、競品（`deliberate_no`）；⛔ 找真人走 `handoff` |
