# Plan 切片 KOIA-3.4：`tools/canon/index_eval.py`——步 1 離線量測（三臂 recall@1/3/5，$0）（2026-09-07）

> 狀態：**業主核准 (a)（2026-09-07）；§7.1 三個髒鍵皆視為同一篇（別名表 `TOFILL-beike→beike`、`TOFILL-repair→repair`、`property（原→property`）；§7.2 接受三項全等作凍結證據；§7.3 若 limited 改以 55 格代表問句為主材料；§7.4 `object-under-test.md` 待簽 → executor 實作（先到 dry-run）→ 業主簽核可欄 → 全跑 → fresh verifier**。前史：三輪 plan-verifier 皆 REVISE、皆已 FIX。量測工具（非安全敏感）：`executor` 實作；**數字宣稱必派 fresh `verifier`**（tasks 3.4 驗證欄）。核准前 ⛔ 不寫碼。對應 tasks 3.4、design 元件 10 步 1、R5.2／5.11／6.2／6.4／6.7。前置：3.3 已收案（`d9f6565c`）；正本 24／38 細目已掛 `helpcenter:<slug>`（`46ed093b`，version 2026-09-07.5）。

## 0. 結論先講

用 422 句真問法（85 篇×5 型各 1 句，規則凍結、sha 對得上）對 38 細目量三臂（只標題／標題＋講法／標題＋講法＋內文）的 recall@1/3/5，gold 由「文章→細目」決定性對映（細目 `sources` 含 `helpcenter:<slug>`），⛔ 不派判者、$0（本機 embedding）。留一輪替：查詢句若本身已被掛成該細目講法，評分時剔除那條鍵。報表依粗目×問法型；任一型可對映句 <30 ⇒ 標「該型結論受限」。55 格代表問句（gold＝v3 判者 `fine_id`）另做第二份材料分開報。**只出數字，3.6 決策 5（線上匹配鍵、reranker）由主 session 依數字定案。**

## 1. 結果（outcome）

1. `rag-orchestrator/tools/canon/index_eval.py`（新；`tools/canon/__init__.py`）：
   - **材料凍結**：讀 `canon/prospect.md`（parse，記 `canon_sha256`）、`.kiro/specs/presales-grounding-gate/coverage-map/sources/koyu-v2-phrasings.json`（記 sha）、`inputs/phrasing-selection-rule-20260906.json`（規則參數）、frozen 54 句來源（`coverage-map/topics-v2.json` 全部 `q`）、**幫助中心目錄 `--helpcenter-dir`（預設 `/Users/lenny/jgb/幫助中心/JGB幫助中心_HTML_交付_20260818`，repo 外材料）以 `phrasing_map.dir_digest(dir, "_zh-Hant.html")` 記進輸出 `inputs_sha.helpcenter_dir`（可與 `runs/…/phrasing-map.json` 的值比對）；目錄缺 ⇒ exit 2，⛔ 不得把全部鍵當 unresolved**。
   - **422 句重生**：依規則「每篇每型（直接／口語／情境／俗稱／邊界）各 1 句：排除『操作』型與凍結 54 句（`topics-v2.json` 全部 `q`：46＋8 邊界）後，以 `md5('presales-s1-2026-09-06:'+q)` 升冪取第一」；凍結比對的正規化用 `phrasing_map.norm`（NFKC＋去空白＋去句尾標點，與步 3 同一支，⛔ 不另寫）。凍結證據＝**三項全等**：`n=422`、`by_type` 逐型相等、`excluded_frozen_recomputed=48`（＝被凍結排除的 koyu 句數；規則檔的 54 是凍結題數、48 是被排除句數，兩者不矛盾）；另嘗試重算規則檔 `sha256`（先查 `raw/phrasing-20260906/` 與 commit `eabb2c2b` 找原計法），找到就必須相等、找不到記「sha 原計法未留」；三項任一不等 ⇒ exit 2。
   - **gold 映射**：產 `inputs/koyu-article-map.json`：article 鍵（即 slug）→ `<slug>_zh-Hant.html` 存在？→ 細目 id 集合（正本細目 `sources` 含 `helpcenter:<slug>`；一篇對多細目全列）；對不到檔案的鍵列 `unresolved[]`（現況 **3 鍵**：`TOFILL-beike`、`TOFILL-repair`（目錄內是 `beike`／`repair` 頁，鍵名帶前綴）、`property（原`（Word 匯出截斷，目錄是 `property`）；**業主審一次是否各視為同一篇**。影響分鍵：`beike` 合併無影響（`helpcenter:beike` 不在任何 `sources`）；**`repair` 合併 ⇒ `articles_with_gold` 30→31、每型可對映上限 +1**（`helpcenter:repair` 在 `repair-system` 的 `sources`）；`property` 合併 ⇒ 視 `helpcenter:property` 是否在 `sources`（實查：`community-batch-create` 等有 `property` slug ⇒ 亦 +1）——這兩個裁決會動到 dry-run 的 `<30` 閘門）；文章對不到任何細目的句子**排除並計數**（claim ceiling）。⛔ gold 只從細目 `sources`，不從講法 `source`（會與 `title+phrasing` 臂同源）；⛔ 不重用 1.4（item 是格不是句）。
   - **三臂**：鍵集合 `title`＝標題；`title+phrasing`＝標題＋approved 講法；`title+phrasing+content`＝再加每句 `content_units`。向量用 3.3 的 `EmbeddingUtilsBackend`（分批 ≤8、timeout；本機服務 `embedding-api` 1536 維，$0）；embedding 結果快取到 `raw/index-eval-<日期>/embeddings.json`（gitignored）供重跑；**任何 `None`／維度≠1536 的向量 ⇒ 計數、印失敗批次、非 0 退出（大聲失敗），⛔ 不寫入快取、⛔ 不記 0 分**（`EmbeddingUtilsBackend` 逾時／例外回 None 不 raise，量測工具必須自己擋）；載入快取時校驗維度＝1536 且筆數＝鍵數，不符 ⇒ 重算；細目分數＝該臂鍵集合上的 max cos；排序 `(-score, id)`；recall@k＝gold 集合與 top-k 交集非空。
   - **留一輪替（`--loo {exact,article}`，主報表兩組數都出）**：`exact`＝查詢句 NFKC＋去空白後等於某細目已掛講法文字 ⇒ 該查詢評分時剔除那條 `ph:` 鍵；`article`＝查詢句所屬文章 slug 等於某講法 `source` 的 slug（`koyu:<slug>#n`／`helpcenter:<slug>`）⇒ 該查詢評分時剔除該細目所有來自同文章的鍵（**同源污染**：gold 靠 `sources` 的 helpcenter，而同細目常掛同一篇文章的標題與兄弟句作講法，例 `rental-storefront-vr` 的 `helpcenter:slug90`＋`koyu:slug90#2/#8`，逐字 LOO 抓不到）。三臂一致處理；報表每組記「被剔除鍵數」與「受影響句數」；⛔ 不得只報 exact。
   - **報表**：`loo_mode ∈ {exact, article}` 各一組 recall@1/3/5 依 粗目（A–G）× 問法型（5 型）；每型「可對映句數／總句數」；任一型可對映 <30 ⇒ 該型標 `limited`；`articles_with_gold`（＝正本 helpcenter slug ∩ koyu article 鍵；實查 34 個 slug 中 30 個在 koyu，`Landlordonboarding09Socialhousing`／`einvoice`／`paymentapply`／`repair` 不在）；臂間差（點）；`--report misrouted`：勝出鍵為講法且其所屬細目 ∉ gold 的句子清單（`misrouted_phrasing[]`，附講法所屬細目與 gold）。**第二份材料**：55 格代表問句，gold＝`runs/…/answerability-canon-v3.json` 該格 `fine_id`（deliberate_no／no_source 格排除並計數），同三臂、分開報。
   - **輸出**：`inputs/index-eval-20260907.json`（含所有輸入 sha、規則、arms、每句結果、彙總）＋`inputs/m-c-index-eval-20260907.md`（報表）。
   - **`--dry-run`＝硬閘門（不打 embedding）**：印 `n=422`、`by_type`、`frozen_set_size`（預期 54）、`excluded_frozen_recomputed`（預期 48）、`articles_with_gold`（預期 30）、每型可對映句數；**≥3 型可對映 <30 ⇒ exit 3、停下回主 session**（全 limited 時本片不足以支撐 3.6，改以第二份材料或擴 gold，由業主裁）；全跑前必先 dry-run 綠。
   - **受測物定義清單（R6.1／元件 10）**：全跑前主 session 產 `inputs/object-under-test.md`（知識正本 sha、koyu sha、規則、gold 映射 sha、材料能證什麼／證不了什麼、假設表：命題／最小材料／尺／推翻條件／費用 $0），**業主核可欄非空後才全跑**；`index_eval` 全跑時寫 session 狀態 `evals_ran += ["index_eval"]`、`materials_frozen=true`、`object_under_test_path`（`_envelope.update_state`），Stop hook 據此把關；未核可 ⇒ 工具 exit 2 不啟動。
   - **⛔ 不 log 查詢句以外的任何個資**；句子本身是業主正本材料（非流量），可寫入 inputs。
2. **測試**（unit，假 backend）：假 backend 回一批 None ⇒ 工具非 0 退出、印失敗批次數、快取檔未寫入（正對照：全有向量正常產表）；規則重生在小語料上決定性且 md5 排序正確；凍結句與操作型被排除；gold 映射（一篇對多細目、對不到檔案進 unresolved、對不到細目的句子計數）；LOO 剔除生效（同句作講法時分數不得來自該鍵；正對照：不開 `--loo` 時分數來自該鍵）；recall@k 計算；misrouted 判定；claim ceiling（<30 ⇒ limited）；sha 不符 ⇒ exit 2。

## 2. 現況事實（2026-09-07 實查）

- koyu 檔：`articles` 85 篇、1,546 句、六型；規則檔 `n=422`、`by_type` 各 83–85、`excluded_frozen=48`；凍結題＝`topics-v2.json` 54 句 `q`（46＋8 邊界），48＝被排除的 koyu 句數（plan-verifier 第 1 輪核）；規則檔 `sha256` 計法未在 repo 內找到腳本。
- 正本：38 細目、189 approved 講法（koyu 59、question_summary 99、gapmap 17、helpcenter 14）；24 細目 `sources` 含 34 個 helpcenter slug，其中 **30 個是 koyu article 鍵** ⇒ 85 篇中 30 篇有 gold，55 篇的句子屬「文章對不到細目」排除計數 ⇒ 每型可對映上限約 30×1＝30 句，**claim ceiling 很可能整片 `limited`**——因此 dry-run 是硬閘門，且第二份材料（55 格）與「擴 gold」是備案（§7.3）。
- embedding：`aichatbot-embedding-api` 在線、`POST localhost:5001/api/v1/embeddings` 1536 維；3.3 `EmbeddingUtilsBackend` 可直接用（測試映像無 tiktoken 與此無關）。
- 3.3 `FineIndex` 只吃 approved 講法且不含內文 ⇒ 第三臂與「只標題」臂要在 `index_eval` 內自建鍵集合（不改 `FineIndex`）。
- 實作提醒（plan-verifier 註記）：422 重生 ⛔ 不可用 `phrasing_map.load_koyu`（`KOYU_INCLUDE_TYPES` 不含「邊界」）；核可欄判定直接 import `.claude/hooks/outline_gate.py::APPROVAL_RE`（與 Stop hook 同一把尺）；第二份材料檔實際路徑 `.claude/skills/outline-curation/runs/2026-09-06T00-00-00Z/answerability-canon-v3.json`。

## 3. 非目標

- 不定案 3.6（匹配鍵、講法密度）；不接 reranker；不動 `FineIndex`／`CandidateSelector`／正本；不派判者；不用流量樣本（D3）；不改規則檔。

## 4. 驗收（executor 做、fresh verifier 反證數字）

1. `--dry-run`：三項全等（n／by_type／excluded_frozen=48）、`frozen_set_size=54`；`koyu-article-map.json` 產出、`unresolved` 排序後逐字＝`[TOFILL-beike, TOFILL-repair, property（原]`（len 3）；`articles_with_gold` 依業主 §7.1 裁決分支＝30（不合併）／31（合併 repair）／32（再合併 property）；輸出含 `inputs_sha.helpcenter_dir`；指到不存在目錄 ⇒ exit 2；`articles_with_gold=30`（與 slug∩koyu 手算一致）；每型可對映句數印出；**≥3 型 <30 ⇒ exit 3 且未呼叫 embedding**（正對照：故意把正規化改成保留句尾標點 ⇒ `excluded_frozen_recomputed` 改變並 exit 2）。
2. 全跑（前置：`inputs/object-under-test.md` 核可欄非空，否則 exit 2）：`exact`／`article` 兩組三臂 recall@1/3/5 表（粗目×型）、每型 mappable 數與 `limited` 標記、被剔除鍵數／受影響句數、臂間差、misrouted 清單、第二份材料表；session.json `evals_ran` 含 `index_eval`、`materials_frozen=true`、`object_under_test_path`；輸出 json 含所有輸入 sha；重跑（快取 embedding）數字逐位元相同；正對照：清空核可欄 ⇒ Stop hook 必擋。
3. verifier：抽 ≥20 句手算 gold 與 top-5 對照工具輸出；LOO 兩模式生效（抽 slug90 一句：`article` 模式下 `rental-storefront-vr` 分數不來自任何 slug90 來源鍵；`exact` 模式下同句作講法時不來自該鍵）；claim ceiling 標記與計數一致；sha 凍結欄位與檔案實算相符。
4. 結論格式（給 3.6）：每臂總 recall@5、臂間差是否 ≥10 點、是否有型 `limited`；⛔ 本片不下「採用哪臂」的結論。

## 5. 回滾／預算／停損

- 回滾：刪 `tools/canon/index_eval.py`、測試、`inputs/index-eval-*`、`koyu-article-map.json`。預算 $0（本機 embedding）；embedding 約 422＋38＋189＋~130 內文句 ≈ 800 次呼叫。
- 停損：dry-run ≥3 型 <30 ⇒ exit 3 停下交裁（§7.3）；凍結三項任一不等 ⇒ exit 2 停下；⛔ 不擴材料、不改規則。

## 6. 對 design 的偏離（待回寫）

- 元件 10 步 1 寫 `--arms … --loo`：本 Plan 增 `--dry-run`、`--report misrouted`、embedding 快取；gold 來源明訂為細目 `sources` 的 `helpcenter:`（tasks 3.4 已寫，design 表格未寫）。

## 7. 待業主核

1. `koyu-article-map.json` 的 `unresolved` 3 鍵各自是否視為同一篇：`TOFILL-beike`→`beike`（無影響）、`TOFILL-repair`→`repair`（**會讓 gold 文章 30→31**）、`property（原`→`property`（**再 +1**）。建議三個都合併（它們就是同一篇，只是鍵名髒），dry-run 以合併後的值為準。
2. 若規則檔 `sha256` 原計法找不到：接受「三項全等（n／by_type／excluded_frozen=48）」作凍結證據（plan-verifier 第 1 輪建議）。
3. dry-run 若 ≥3 型 `limited`（可對映 <30）：(a) 只用第二份材料（55 格代表問句）出 3.6 的數字；(b) 擴 gold——把更多幫助中心文章對到細目（要你判 24 條以外的細目對哪些文章）；(c) 接受 limited 照跑只當參考。
4. `inputs/object-under-test.md`（跑前產）要你核可欄簽字。
