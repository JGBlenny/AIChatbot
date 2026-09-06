# Plan 切片 KOIA-3.7：`FineIndex` 內文鍵——`content_units` 每句一鍵進線上匹配（2026-09-07）

> 狀態：**收案（2026-09-07）**：業主核（§8 四項照預設）→ executor → fresh verifier **CONFIRMED**（獨立重算：真正本 358 鍵＝38＋189＋131、序與 index_eval 內文臂一致；第二份材料 47/49 vs 44/49＝報告 article 臂 .9592／.898；sha 不符 SKIP 非 FAIL；丟一個內文向量 ⇒ not_ready、select 回 None；`ct:`／`ph:` 與文字不出現於回傳／health／log；K／MAX_BATCH／逾時／無 MIN_SCORE 不變）；unit 1014／integration 210／`make audit` PASS。P4（不改）：`_best_entry` 對未知 kind 一律 -2（KeyKind 現只三值）。取捨：executor 為讓 audit 不變量 3 過而重建本機 `aichatbot-rag-orchestrator` 容器（本機堆疊、非線上）。**收案取捨表**：內文句增益可能含「記住來源」成分（3.4 內文鍵 article=None 不受 LOO 剔除），4.4a 假設表須以非 helpcenter／koyu 改寫的問句量三臂。前史：第 1 輪 REVISE 3 條 P2 皆 FIX（3.3b tie 案正對照位移；對照臂改 article；sha 閘門），第 2 輪 READY。

## 0. 結論先講

把每細目的 `content_units` 每句加成一把 `content` 鍵（內部 id `ct:<sha8>`），與標題鍵、approved 講法鍵一起進 `FineIndex`；選取分數改為三者取最大，`winning_key_kind` 值域加 `content`，同分序 `title > phrasing > content`。快取鍵、批次 ≤8、三態、失敗不服務、可見性切法、K=5、不設門檻、不接 reranker——**一律不動**。驗收三把尺：(1) 合成正本的鍵集合／順序／隱私／health；(2) `FineIndex` 送去 embed 的鍵文字集合＝`index_eval` 內文臂（`title+phrasing+content`）的鍵文字集合，合成正本與真正本各驗一次；(3) 突變控制——用 3.4 凍結的 embedding 快取重放第二份材料 49 格，有內文鍵 r@5 必須高於拿掉內文鍵（預期 47/49 對 44/49，與 3.4 報告 .9592／.898 對齊）。

## 1. 結果（outcome）

### 1.1 `services/agent/canon/fine_index.py`
1. `KeyKind = Literal["title", "phrasing", "content"]`；新增 `CONTENT_KEY_PREFIX = "ct:"`，內部 id 由 `_content_key_id(text)` 產生（NFKC → sha256 前 8 碼，與 `_phrasing_key_id` 同法；可共用一個 `_hashed_key_id(prefix, text)`）。⛔ `ct:*` 與 `ph:*` 同待遇：不出現在任何回傳值／trace／health／log。
2. `_key_plan(doc)` 每細目的決定性順序：`title` → approved 講法（正本序）→ `content_units` 每句一鍵（正本序）。內文句不去重（真正本有 2 句跨細目重複，各細目保留自己那把；同細目內若重複亦保留——鍵 id 相同無妨，索引以位置存）。⛔ 不過濾任何內文句（parser 已保證每句非空；F8 保證屬性區塊不落入 `content_units`）。
3. 快取鍵維持 `(canon_sha256, phrasing_set_sha256)`：`canon_sha256` 涵蓋整份 `.md`，改任一內文句必變 sha ⇒ 必重建（以測試釘住，§4.1-7）。
4. `entry_count` 含內文鍵；新增唯讀 `content_key_count` 屬性（ready 才非零；`not_ready`／`absent` 為 0）。
5. `index_registry_states()`／`_observe` 的每受眾觀測值加 `"content_keys"`；`_ABSENT_STATE` 加 `"content_keys": 0`。⛔ 不致紅語義不變。
6. 模組 docstring 的「標題向量＋approved 講法向量」與隱私硬規則改為含內文句；`MAX_BATCH`／`PREPARE_EMBED_TIMEOUT_S`／`EmbeddingUtilsBackend` ⛔ 不動。

### 1.2 `services/agent/canon/candidate_selector.py`
7. `_best_entry` 的同分比較鍵改為三階：`title` 0 > `phrasing` -1 > `content` -2（明示比較鍵，⛔ 不依賴 `entries_for` 順序）。理由：同分時取「意圖形狀最強、最受治理的鍵」——標題是細目命名、講法是人核過的問法、內文句是答案本文；讓內文句在同分時墊底，避免答案句「碰巧」同分就把 trace 記成 `content`（design 決策 5 只寫「同分取 title」，講法 vs 內文的同分序是本片補明，§8.1）。
8. `Selection.winning_key_kind: dict[str, KeyKind]` 值域自然擴為三值；模組 docstring 硬規則 3 改為 `∈ {"title","phrasing","content"}`，並加「⛔ 不記 `ct:*`」。`K`、`QUERY_EMBED_TIMEOUT_S`、無 `MIN_SCORE`、可見性先切、失敗只回 `None`——⛔ 一字不改。

### 1.3 `services/agent/health.py`
9. `_index_state` docstring 補 `content_keys`；邏輯零改（它只透傳 `index_registry_states()`）。

### 1.4 文件回寫（主 session，verifier CONFIRMED 後）
10. design 元件 6 的 `winning_key_kind: dict[str, Literal["title", "phrasing"]]` 改為三值＋同分序註記；變更歷史加 1.15 一列；tasks 3.7 打勾＋收案摘要；快照更新。

## 2. 現況事實（主 session 2026-09-07 實查；查證指令附於各條）

- `fine_index.py`：`KeyKind = Literal["title", "phrasing"]`；`_key_plan` 只出標題＋approved 講法；`_phrasing_key_id` NFKC+sha8；快取鍵 `(canon_sha256, phrasing_set_sha256)`；`index_registry_states` 每受眾 `{state, prepared_sha, entries, dim}`；`_ABSENT_STATE` 四欄。`grep -n "KeyKind\|_key_plan\|_ABSENT_STATE" rag-orchestrator/services/agent/canon/fine_index.py`
- `candidate_selector.py`：`_best_entry` 比較鍵 `(score, 0 if kind == "title" else -1)`；`Selection.winning_key_kind: dict[str, KeyKind]`（型別直接引用 `KeyKind`，擴值域不需改 TypedDict）。`grep -n "_best_entry\|winning_key_kind" rag-orchestrator/services/agent/canon/candidate_selector.py`
- `health.py::_index_state` 只呼叫 `index_registry_states()`；`_canon_state` 把它掛在 `"index"`。`grep -n "_index_state\|index_registry_states" rag-orchestrator/services/agent/health.py`
- `canon_parser.FineItem.content_units: tuple[str, ...]`（frozen dataclass；`CanonDoc`／`CoarseItem` 亦 frozen）。真正本 `rag-orchestrator/canon/prospect.md`：38 細目、**131** 內文句、189 approved 講法；跨細目重複句 2、內文句與標題／講法相等 0。`cd rag-orchestrator && python3 -c "from services.agent.canon.canon_parser import parse_canon; d=parse_canon('canon/prospect.md'); fs=d.fines(); print(len(fs), sum(len(f.content_units) for f in fs), sum(1 for f in fs for p in f.phrasings if p.status=='approved'))"`
- `tools/canon/index_eval.py`：`build_fine_keys(fines)` 內文臂＝`[("content", u, None) for u in f.content_units]`（每句一鍵，與 tasks 3.7 定義一致）；`all_index_texts(fine_keys)` 取三臂聯集（＝內文臂集合）；`score_fine_for_query` 為過濾後鍵集合上的 max cos、`rank_fines` 排 `(-score, fine_id)`（與 selector 同序）；`load_second_material(map_v2, canon_v3)` 回 `[{cell_id, question, gold}]`；`_cache_key(text) = sha256(NFKC(text))`。`grep -n "def build_fine_keys\|def all_index_texts\|def load_second_material\|def _cache_key" rag-orchestrator/tools/canon/index_eval.py`
- 3.4 報告 `inputs/index-eval-20260907.json` → `results.second_material`：**article 模式對第二份材料等於無 LOO**（`build_report` 對第二份材料呼叫 `rank_fines(..., query_article=None, loo_mode)`，而 `score_fine_for_query` 的 article 分支要 `query_article is not None` 才剔鍵）；exact 模式**有剔鍵**（title 臂 r@5 exact .8367 ≠ article .8571、r@1 .5714 ≠ .5918）。故 `FineIndex`（無 LOO）的對照對象是 **`second_material.article.arms`**：title .8571／title+phrasing **.898**／title+phrasing+content **.9592**；mappable 49、`excluded_deliberate` 6 ⇒ 預期 44/49 與 47/49。`python3 -c "import json; r=json.load(open('.kiro/specs/knowledge-outline-and-intent-architecture/inputs/index-eval-20260907.json'))['results']['second_material']; print({m:{a:(v['recall_at_1'],v['recall_at_5']) for a,v in x['arms'].items()} for m,x in r.items()})"`
- 3.4 embedding 快取：`.claude/skills/outline-curation/raw/index-eval-20260907/embeddings.json`（**gitignored、只在本機**；`{"dim":1536,"vectors":{sha256(NFKC(text)): [1536 floats]}}`，773 筆＝鍵文字＋422 句＋第二份材料問句去重後）。測試容器把 `./.claude` 掛成 `/.claude:ro`（`docker-compose.dev.yml`），唯讀足夠。`ls -la .claude/skills/outline-curation/raw/index-eval-20260907/; grep -n "\.claude" docker-compose.dev.yml`
- 第二份材料兩個輸入皆已進版控：`.kiro/specs/presales-grounding-gate/coverage-map/map-v2.json`、`.claude/skills/outline-curation/runs/2026-09-06T00-00-00Z/answerability-canon-v3.json`。`git ls-files <兩路徑>`
- 既有測試：`tests/unit/agent/test_fine_index_req.py` 的合成夾具 `_fine_block` **每細目已帶一句內文**（`內容句{slug}`）⇒ 本片落地後鍵數斷言會位移：`test_keys_are_titles_plus_approved_phrasings_only` 6→9、`test_backend_is_called_in_batches_of_at_most_eight` 12→15（`sum(backend.calls)` 同步）、`test_flipping_one_phrasing_status_changes_sha_and_rebuilds` 7→10、`test_failed_prepare_is_not_cached_so_a_retry_can_recover` 6→9、health 案 `entries` 6→9。`grep -n "== 6\|== 12\|== 7" rag-orchestrator/tests/unit/agent/test_fine_index_req.py`
- `tests/unit/agent/test_candidate_selector_req.py`：`_fine_block` 每細目亦寫一行內文（`內容句{slug}`）；未列在 `vectors` 的文字一律 `_ORTHOGONAL`（0.0 分）⇒ 內文句在既有情境永遠不勝出、排序／候選斷言不受影響。**唯一會位移的一條**：`test_winning_key_kind_prefers_phrasing_when_it_scores_higher_and_title_on_a_tie` 的正對照 `assert [k for k, _v in index.entries_for(fid("tie-kind"))] == ["title", "phrasing"]` 落地後必為 `["title", "phrasing", "content"]`（§4.2-12 明列）；同案 `<= {"title","phrasing"}` 仍成立。`grep -n 'entries_for(fid("tie-kind"))' rag-orchestrator/tests/unit/agent/test_candidate_selector_req.py`身分夾具 `B2B_PROSPECT = Identity(vendor_id=1, target_user="prospect", mode="b2b")`；3.3b 已驗真正本對 b2b prospect 可見＝全 38。
- `tests/unit/agent/test_index_eval_req.py` 以 `sys.path.insert(0, _RAG)` 後 `from tools.canon import index_eval as ie` 匯入（unit 層可離線 import，本片沿用）。
- CANON：`.claude/prerequisites.json` 未涵蓋 `services/agent/canon/*`／`health.py`／`tests/unit/agent`（M1 閘門不觸發）；`.claude/MAP.md` 沒有本 spec 的功能鍵（只在 `{#kiro-specs-tree}` 目錄宣告），`/canon-audit` 無可指定之鍵——本片以 §2 逐條查證指令代替。

## 3. 非目標

- ⛔ 不調 `K`、⛔ 不接 reranker、⛔ 不加分數門檻／`MIN_SCORE`、⛔ 不動可見性（`visible_subset`／`canon_visible`／`build_visibility_predicate`）、⛔ 不動 `embedding_utils.py`。
- 不接 runtime（4.1）；不改 `index_eval.py`（3.4 已收案；本片只讀它當對照尺）；不改正本內容（2 個 0 講法細目補講法待業主核，與本片無關）；不做 5.x 講法治理；不動 DB／匯入。
- 不為「拿掉內文鍵」加任何產線旗標／建構參數——突變控制只在測試用「剝掉 `content_units` 的正本副本」構造（§4.4），⛔ 產線沒有關掉內文鍵的開關。

## 4. 驗收（容器內；指令見 §4.6）

### 4.1 `test_fine_index_req.py`（既有檔延伸；合成正本、假後端）
1. 鍵集合＝標題＋approved 講法＋**每句內文**（`_doc_three_statuses` ⇒ 9；proposed／retired 仍不進）。
2. 每細目順序＝`title` → 講法（正本序）→ 內文句（正本序）：以 `backend.texts`（送去 embed 的文字序）與 `entries_for` 的 kind 序同時斷言；**另立**一個每細目 3 句內文的夾具（`_doc_multi_content`）以能辨序——既有夾具維持每細目 1 句，§2 所列 9／15／10 的位移數字以既有夾具為準。
3. 決定性（兩次 prepare `_snapshot` 相等）與分批 ≤8 不變（`_doc_twelve_keys` 15 鍵、`max(calls) ≤ 8`）。
4. `entries_for` 回傳只有 `(kind, vector)`，kind ∈ 三值；序列化整個索引與 health 結果後 **不含 `ct:`、不含 `ph:`**（延伸既有 `test_entries_for_never_exposes_internal_key_ids`）。
5. 三態不變：任一**內文句**向量 `None`／NaN ⇒ `not_ready` 且 `entry_count == 0`、`content_key_count == 0`（新增一案針對內文鍵）。
6. 快取：同 doc 二次 prepare 不再呼叫後端（既有）；**改一句內文** ⇒ `canon_sha256` 變 ⇒ 重建（新增，對照 `test_flipping_one_phrasing_status_changes_sha_and_rebuilds`）；`phrasing_set_sha256` 不變也要重建（證明快取鍵靠的是 `canon_sha256`）。
7. health：ready 案 `{state, prepared_sha, entries: 9, dim, content_keys: 3}`；`not_ready` 與 `absent` 的 `content_keys == 0`；三受眾恆列；`status`／`red_flags` 差分不變（既有差分斷言）。
8. 隱私：`_secret_texts` 加入全部 `content_units`（夾具內文句改帶 `ZZCONTENT*` 標記），四條路徑後 `caplog`＋`capsys` 皆無任何標題／講法／內文文字；正對照（先證兩個擷取器活著）**⛔ 不得刪**。

### 4.2 `test_candidate_selector_req.py`（既有檔延伸；合成正本、明示向量）
9. 新情境：細目 `ct-wins` 標題與講法 `_ORTHOGONAL`、內文句 `_HIGH` ⇒ 進候選且 `winning_key_kind == "content"`、分數 1.0。
10. 同分序：三鍵同向量 ⇒ `title`；標題較低、講法＝內文同分 ⇒ `phrasing`（證 `content` 墊底）。
11. `Selection` JSON 序列化不含 `ph:` 亦不含 `ct:`；`winning_key_kind` 值域 ⊆ 三值。
12. 既有 3.3b 案例只改一處：`test_winning_key_kind_prefers_phrasing_when_it_scores_higher_and_title_on_a_tie` 的正對照斷言改為 `== ["title", "phrasing", "content"]`（仍證「標題與講法都在索引裡」，多證內文句也在）；其餘斷言一字不改、仍綠（內文句在既有向量表為 0.0 分）。

### 4.3 鍵集合對照 `index_eval` 內文臂（新檔 `tests/unit/agent/test_fine_index_content_parity_req.py`，`req("knowledge-outline-and-intent-architecture:3.7")`）
13. 合成正本（3 細目、含 proposed／retired 講法、每細目 2–3 句內文、其中一句跨細目重複）：`FineIndex.prepare` 後 `backend.texts` 的**多重集合**＝`ie.build_fine_keys(doc.fines())` 各細目 `title+phrasing+content` 臂的 `(kind, text)` 依細目序串接；且 `set(backend.texts) == set(ie.all_index_texts(fine_keys))`。
14. 真正本 `rag-orchestrator/canon/prospect.md`（`parse_canon`，路徑由 `_RAG` 推）：同一等式，**斷言只印數量**（`n_diff = len(a ^ b); assert n_diff == 0, f"{n_diff} 把鍵不一致"`；逐細目比對以布林＋細目 id 回報，⛔ 任何 assert 訊息不得帶出鍵文字——講法是去識別後的真流量）；另斷 `index.content_key_count == sum(len(f.content_units) for f in fines)`、`entry_count == 38 標題數 + approved 數 + 內文句數`（三個數從 parser 現算，⛔ 不寫死 131／189，正本會隨業主補講法而變）。
    ⚠️ 本條刻意用真正本（3.3 測試的「不拿真正本當材料」原則是為了不把講法印進失敗訊息／log；這裡以「只印數量」約束達到同一目的，§8.2 交裁）。

### 4.4 突變控制：第二份材料 r@5（同上新檔；**以 3.4 凍結快取重放，⛔ 不打 embedding API**）
15. 前置閘門（兩道，依序）：(i) 快取檔不存在 ⇒ `pytest.skip("3.4 embedding 快取不在本機（gitignored）")`；(ii) `doc.canon_sha256 != report["inputs_sha"]["canon_sha256"]` ⇒ **整案** `pytest.skip("正本已變（sha 不符 3.4 報告）、需重跑 3.4 全跑更新快取與報告")`——3.4 快取只含該次全跑的 `all_texts`，正本一改（例如業主補講法）新鍵必缺向量，不設這道閘門會把已排程的正本編輯變成 unit 層假紅。兩道都過之後，任一鍵文字／問句查不到向量 ⇒ 後端回 `None` ⇒ `FineIndex` 落 `not_ready` ⇒ 測試**失敗**（不是 skip；這就是快取覆蓋的正對照）。**驗收要求在當前正本 sha 下 `-rA` 顯示本案 PASSED，SKIPPED 不算過**（否定結論要有正對照）；verifier 另以暫存副本改一句內文重跑，須見 SKIPPED＋上述理由而非 FAILED。
16. 材料：`doc = parse_canon(真正本)`；`cells, excluded = ie.load_second_material(map_v2, canon_v3)`（兩檔已進版控）；只取 `gold` 非空的格（預期 49，`excluded` 預期 6——兩數從報告 JSON 讀、不寫死）；身分 `B2B_PROSPECT`（可見＝全 38，與 `index_eval` 對全部細目排序等價）。
17. 有內文鍵：`FineIndex(cache_backend).prepare(doc)`、`CandidateSelector(index).select(doc, B2B_PROSPECT, question)` 逐格，`hit5 = Σ[gold ∩ candidate_ids ≠ ∅]`。拿掉內文鍵：`doc_stripped = dataclasses.replace(...)` 把每個 `FineItem.content_units` 換成 `()`（`canon_sha256` 原樣複製，故 selector 首行 sha 比對仍過），對它建第二份索引、同法算 `hit5_without`。
18. 斷言（依序；sha 閘門已在 §4.4-15 過）：(a) **`hit5_with > hit5_without`**（tasks 3.7 的「必降」，主斷言）；(b) `round(hit5_with / mappable, 4)` 與 `round(hit5_without / mappable, 4)` 各等於報告 **`results.second_material.article.arms["title+phrasing+content"].recall_at_5`／`["title+phrasing"].recall_at_5`**（article＝無 LOO，見 §2；預期 .9592／.898；`mappable` 亦與報告該臂 `mappable` 相等＝49）；(c) 全程 `caplog` 無任何問句／鍵文字（沿 §4.1-8 正對照）。
19. 若 (b) 不等：**停下交裁**，⛔ 不調分數算法遷就報告、⛔ 不改 `index_eval`——兩者差異即是「線上索引與離線量尺不同尺」的證據，要先找原因。

### 4.5 不變性
20. `tests/integration/agent/`（`visible_subset` 與 SQL 等價、突變控制）不改一字、仍綠。
21. `make audit` 不變量全 PASS（27–34 不動）。

### 4.6 指令（repo 根；host 無 `timeout`）
- `scripts/run-tests.sh unit tests/unit/agent/ tests/unit/_meta/ -rA`（必看 `test_fine_index_content_parity_req.py` 兩案為 PASSED）
- `scripts/run-tests.sh integration tests/integration/agent/`
- `make audit`

### 4.7 fresh verifier 主張（exact claim）
「`FineIndex` 對每細目建標題＋approved 講法＋`content_units` 每句一鍵，鍵文字多重集合＝`index_eval` 內文臂（合成＋真正本）；三態／≤8／快取鍵／失敗不服務／可見性先切／`None` 不變寬全部不變；`ct:`／`ph:` 與任何文字不出現在回傳、health、log、stdout；`winning_key_kind` 可為 `content`，同分 `title > phrasing > content`；第二份材料以 3.4 快取重放（正本 sha 與報告相符時）：有內文鍵 r@5 47/49、拿掉 44/49（與報告 `second_material.article` 臂 .9592／.898 對齊；sha 不符則整案 SKIPPED 而非 FAILED）；health 每受眾多 `content_keys`、不致紅。」

## 5. 回滾／預算／停損

- 回滾：還原 `fine_index.py`、`candidate_selector.py`、`health.py` 與三個測試檔。$0（假後端＋本機快取，全程零 embedding 呼叫；⚠️ `EmbeddingUtilsBackend` 在產線啟動會多 131 句 ≈17 批，屬既有成本模型）。
- 停損：§4.4-19 對照不等 ⇒ 停；§4.4-18(a) 不成立（有內文鍵反而不高）⇒ 停（與 3.4 報告矛盾＝尺出問題，⛔ 不「調到會過」）；verifier REFUTED 兩次 ⇒ 停。
- 執行紀律（進 brief）：⛔ 禁 `git stash`／`checkout --`／`reset`／`clean`；⛔ 不讀 `.env`、不印金鑰；⛔ 不動別窗檔（`docs/INDEX.md`、`.kiro/specs/testing-traceability/`、`docs/presales-assistant-quality-audit-20260902.md`、`scripts/review_coverage.py`、`.claude/DECISIONS.md.lock`）；⛔ 不 commit（主 session 收案後併一筆）；⛔ 不跑 `raw_purge.py --apply`；log／assert 訊息不得帶出正本文字。

## 6. 對 design 的偏離（待回寫 1.15）

- 同分序補明為 `title > phrasing > content`（design 只寫「同分取 title」）。
- 突變控制以「剝掉 `content_units` 的正本副本」構造，不加產線開關。
- 鍵集合對照與突變控制用真正本＋本機快取：unit 層有條件跳過（快取不在）但驗收要求實跑 PASSED。

## 7. 執行角色

預設 **`executor`**（快照所記）：本片不開新 IO／log 面，隱私由既有硬規則＋延伸標記測試守；改動是型別值域＋鍵計畫＋比較鍵，屬有界判斷。替代：`security-executor`（3.3 先例，理由是文字外洩控制在此檔）。§8.3 交裁；不論何者，完工後 fresh `verifier` 對 §4.7 主張。

## 8. 待業主核

1. 同分序 `title > phrasing > content`（§1.2-7）。替代：`title` 優先、講法與內文同分時取先出現者（＝講法，因鍵序）——效果相同但隱含、不明示；不建議。
2. §4.3-14／§4.4 在 unit 測試讀真正本與本機快取（只印數量、快取不在則 skip 但驗收要求 PASSED）。替代：這兩條只由 verifier 在容器內以一次性腳本跑、不進測試檔——可重跑性差，之後補講法後無人再驗尺。
3. 執行角色 `executor` vs `security-executor`（§7）。
4. 同意本片不含「2 個 0 講法細目補講法」（那是正本內容改動，另案業主核）。
