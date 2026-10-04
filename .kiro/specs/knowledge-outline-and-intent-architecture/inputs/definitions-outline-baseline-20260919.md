# 大綱補齊：目標與必須先定的定義（盤查清單）— 2026-09-19

> 為什麼有這份：2026-09-16～19 我在沒有定義基準的情況下換了四種分母（路由／權限＋幫助中心／真實問句／主題），每種都能跑、都過審查，但沒有一種是從產品全貌出發，「齊了沒」無法回答（業主：「現況就是一個注定不會達到效果的任務」「先基於目標把該定義盤查的整理好」）。本檔只列定義與查證方式，⛔ 不含計畫、不含執行。每條定義後面是「查證」：代理要用什麼證據證明它與現況相符。

## 0. 目標（業主 2026-09-19 對齊）

AI 客服對 JGB 產品每一件可被問的事，都有一條**經業主審過、有來源**的細目可答。

- agent 回合的機制：拿客戶問句比對細目（標題／講法／內文），取最像的 5 條給模型；⛔ 不預測客戶會問什麼。所以大綱該有哪些細目，由「產品有哪些可被問的事」決定。
- 終點的判準：基準（D1）的每件事，對每個開放的身分（D3），各有一條 `reviewed` 的細目，且每句可對回來源（D6）。
- 查證：`rag-orchestrator/services/agent/runtime.py::_select_outline`／`canon/candidate_selector.py::select`（比對而非預測）；`canon_assembler.canon_visible`（未審 ⇒ 不可見）。

### 任務與驗收（業主 2026-09-19「對」）

**任務**：對基準 D1 的每件事（粒度待裁），售前與業者兩身分各有一條有來源、經審核的細目。

**驗收**（每條可被外部證偽；⛔ 不以條數／格數／測試綠當驗收）：
1. **覆蓋**：D1 每格 × 每個開放身分有一條細目直接答（覆蓋表由代理判、腳本驗格集合與值域、業主抽查 20 格）；產品沒有的題在 I 架「不支援」一條逐項附 jgb2 查證與正對照。⚠️ 已由 2026-10-04 業主裁決取代，見 `../goal-acceptance-spec-20261004.md` §0。
2. **內容**：每條細目每一句對回 jgb2 程式或幫助中心；查無來源的句子標出、⛔ 不寫；業主抽查 30 句回源全中。
3. **審核**：進模型的細目 100% 經業主（或指定人）審過；未審不算完成。
4. **效果**：以真實問句（`test_scenarios` 業者 227、售前 113）跑實際回合，命中細目率與答到率相對今日基線（業者可用 9 條；⚠️ 2026-09-23 換正本後工作樹已是 0 條，該基準線只存在於封存的舊 210 條，見 D7）有可量提升；需真後端，支出業主定。⚠️ 已由 2026-10-04 業主裁決取代，見 `../goal-acceptance-spec-20261004.md` §0。
5. **不做**：租客、業態分流、商務中心、部署。

上一輪（9.7／9.9）的驗收是「條數落地、測試綠」，可全綠而目標零進展；本驗收以目標為準。

## D1. 基準（分母）＝產品面向使用者的頁面樹

**定義**：JGB 使用者可到達的每一個頁面＝一件可被問的事的上界。來源兩段、缺一不可：(a) SPA 路由 jgb2 `src/routes/*.js`（Vue Router：`name`／`path`／`meta`／頁面元件）；(b) 仍由後端直接渲染的非內部頁——`routes/web.php` 中 controller 非 `IndexController@vueIndex`、非 `Admin\*`／`Internal\*` 且對應 `resources/views/**` 存在者（實例：`notifications.index`、`users.account`、`contracts.sign`、`customers.demand`）。側欄選單為動態資料（`AsideMenu.vue` 只有一條靜態項，其餘來自 `state.aside_list`），⛔ 不當來源。權限 action（`config/character.php`）與幫助中心段只用來**補粒度與對照**，⛔ 不當基準；後端 API 路由是實作，⛔ 不當基準。
**觀察（2026-09-19，jgb2 `master`；代理查證）**：SPA 路由檔 15 支（balanceInvoices、bigLandlords、bills、communities、contracts、controlPanel、entrustedContracts、estates、index、iots、listings、repairs、resultScreen、tools、users），具名路由 200 條（路由物件的 `name:`，含單行寫法；`beforeEnter next({ name })`／`redirect: { name }` 不算）；頁面元件 385 個（users 94、contracts 66、estates 58、listings 33、communities 30、bigLandlords 29、repair 17、balanceInvoices 15、bills 12、control-panel 9、help-center 6、iots 4、nthurc＋nthurc-parking 6、entrustedContracts 2、vite／marketing／tools／root 各 1）；`web.php` 去註解後 GET／match 536 條：`vueIndex` 55、內部 172、api 路徑 56、無 view 217、controller 缺 8 ⇒ blade 頁 28（含 `contracts.sign` 一層轉呼叫渲染）。第一次基準（`inputs/page-surface-20260919.md`）：格 228＝基準 183＋住都 10＋不計 35（無頁面元件 6＋非功能 19：結果頁、匯入、匯出、404、官網行銷頁 14 條含 `listings.home*`／about／features／advantages／TA／sitemap、`vite`、LIFF 測試頁、通用殼層路由＋DSP-067 排除 10：統上簽核、出售 5 頁、找房 2 頁、IoT 商品頁、舊活動付款頁）；粗目層見 `inputs/outline-skeleton-20260920.md`（57 個，DSP-067）；租客 0（此路由樹無 `/tenant` 入口）；同名 blade／SPA 頁各一格（`contracts.show` 兩頁）。**已裁（業主 2026-09-19，DSP-065a）**：具名路由無頁面元件（父路由轉址／catch-all）者剔除，內容由子格承接。
**不在基準內**：`Admin\*`／`Internal\*`（JGB 內部後台）、租客側頁面（D3 未開，另列）、商務中心等 DSP-060 排除客群的專屬功能。
**查證**：`git -C /Users/chenqinghuang/dev/work/jgb2/dev2 ls-tree -r --name-only master src/routes src/pages`；抽 3 支路由檔確認 `name`／`path`／`component` 可正則抓取；`git grep -n "vueIndex" master -- routes/web.php` 對照非 vueIndex 的 view 路由清單且對應 blade 檔存在（正對照：`bills.stat` 已走 vueIndex）。**已裁（業主 2026-09-19，DSP-065）**：一條具名路由一格（200 條為上界；同一頁的分頁如出租／出售各一格）。樣本：`estates.dashboard`（`/estates/dashboard/:id`）底下 `estates.dashboard.rent`／`estates.dashboard.sell` 是同一頁的兩個分頁；`contracts.js` 44 條具名路由、`users.js` 36 條。

## D2. 三層＝架 → 粗目（產品功能）→ 細目（一件可問的事）→ 講法（DSP-067，2026-09-20 取代本條原「格×身分」定義）

- 粗目＝JGB 一個功能（使用者在產品裡看得到的一個頁面或功能區），名稱用產品介面自己的標籤（`meta.label`／`t()`／blade 頁標題）；骨架 57 個粗目定案 `inputs/outline-skeleton-20260920.md`。
- 細目＝該功能上使用者會問的一件事，3–10 句、每句對回 jgb2 釘住 commit 或幫助中心（D6）；講法＝使用者問法，掛在細目下。
- 身分（`target_user`）是細目的**屬性**，⛔ 不是缺口的維度（業主 2026-09-20：「售前是身份⋯缺口地圖不是應該是大綱主題？」）；同一件事售前與業者說法不同時才分兩條，否則一條標兩個 `target_user`（DSP-058）。
- 頁面樹（D1）只當「每個功能都盤到了沒」的分母；細目數由該功能上可問的事決定，⛔ 不是一頁一條。
- 查證：`inputs/outline-skeleton-20260920.md` 數字節；`runs/outline-20260920/drafts-<架>.json` 的 `coarses[].fines[]` 形狀；`.claude/DECISIONS.md` DSP-067。

## D3. 身分（開放中的）＝售前 `prospect`、業者 `property_manager`；租客未開

- 業者＝JGB 房東側（個人／法人／社宅房東與其團隊；jgb2 `Role.php` 無管理者角色，入口送 `property_manager`）；`system_admin` 可見性折成業者（DSP-053a）；`landlord` 已移除（DSP-061）。
- 租客側頁面列出但標「未開」（DSP-054），不計缺口。
- 查證：`docs/knowledge/jgb-product-facts.md#landlord-is-the-manager`；`identity.py::audience_of`；`KNOWN_TARGET_USERS` 四值。

## D4. 九架＝格的歸位規則

- 架不變（A 帳號與身分／B 團隊、人員與大房東／C 社區與物件／D 租約／E 帳務／F 修繕／G 裝置／H 幫助中心／I 方案與導入，DSP-047）。
- 歸位規則：路由檔／頁面目錄 → 架的對應表，進版控，一路由一架；跨架者由「內容邊界」角度裁。對應表（15 支路由檔＋非路由頁面目錄全部列入）：users→A／B（帳號 vs 團隊由內容邊界裁）、bigLandlords→B、communities＋estates＋listings→C、contracts＋entrustedContracts→D、bills＋balanceInvoices→E、repairs→F、iots→G、`src/pages/help-center`（路由在 listings.js 的 `listings.helpCenter*`，以 `route:` 覆寫）→H、`listings.pricing*`／`listings.demoForm`（方案與預約 demo）→I、`listings.js` 其餘官網行銷頁（home／about／features／advantages／TA／sitemap）→不計、controlPanel＋tools→I、`index.js`（首頁／登入／儀表板入口）→I、`resultScreen.js`（結果頁，非功能）→不計、`src/pages/vite`／`marketing`／`404.vue`（建置入口、行銷頁、錯誤頁，非功能）→不計、`nthurc`＋`nthurc-parking`（住都＝特定業者專屬知識，業主 2026-09-19 裁）→⛔ 不入通用基準、blade 非內部頁逐條對架。
- 查證：對應表覆蓋 15 支路由檔＋`src/pages` 全部頂層目錄無遺漏（腳本核）；`schemas/coarses-jgb.json` 九架與 `A–I.md` front matter 一致。

## D5. 覆蓋判定＝每個粗目底下「可問的事」有沒有細目、每句有沒有來源（DSP-067 後）

- 判定對象是粗目（產品功能），不是頁×身分格：每個粗目由起草代理從釘住 commit 的頁面程式與幫助中心列出可問的事並成句，verifier 逐句對源；任何一句矛盾 ⇒ 整架 REFUTED 重修。規約 `.claude/skills/outline-curation/steps/00c-topic-first-drafting.md`。
- 「有細目 ≠ 答對」：0b 的頁×身分工具（`feature_coverage_check.py`／`page_coverage_report.py`／`outline_gap_map.py`）只證明「有細目未對源」，保留作粒度對照，⛔ 不再當覆蓋判定。
- 文件與程式衝突、程式缺陷、查無來源 ⇒ 進該細目 `open_questions`，⛔ 不選邊；總表 `inputs/outline-summary-20260920.md`（81 題）交業主裁。
- 「產品沒有但客戶會問」不是粗目；由 I 架一條「目前不支援的功能」承接，逐項要 jgb2 查證＋正對照（未變）。
- 查證：`scripts/outline_summary.py` 產表；每架 drafts 的 `evidence[]`／`not_supported_greps[]` 非空；verifier 最終 CONFIRMED 記錄在各架 run 目錄。

## D6. 來源＝細目每句可對回的權威

- 順序：jgb2 `master` 程式（`git show master:<path>`，本機 `/Users/chenqinghuang/dev/work/jgb2/dev2`）→ 幫助中心頁#段 → 事實帳本 `docs/knowledge/jgb-product-facts.md`。真實問句／客群痛點只當講法與優先序，⛔ 不當內容來源。
- 否定句（「目前沒有」）須附 jgb2 查證與一個正對照命中。
- 現況：`canon_parser` **已強制** `sources` 非空——目錄路徑 `_build_fine(require_fine_attrs=True)` 對 `target_user`／`business_types`／`sources` 三者一律要求非空（2026-09-19 起）。⛔ 不要再加一道檢查；待處理的是它造成的既有紅燈（見 `../HANDOFF-20260923.md` §5-4）。查證：`source_audit.py::DEFAULT_AUTHORITY` 四路徑本機存在（已核）。

## D7. 審核＝細目進模型的唯一門

- 只有 `reviewed` 的細目對模型可見、可引用（⚠️ 2026-09-23 換正本後：新正本 515 條**全未審**、兩身分可用 0 條；「業者可用 9 條」那條**效果驗收的基準線**只存在於封存的舊 210 條 `docs/archive/2026-09/canon-pre-dsp067/`（2026-09-23 已移出工作樹，內容在 git `c06575a9`），要比對須從封存重建）。補齊的終點包含審核完成。
- **已裁（業主 2026-09-19，DSP-066）**：代理先審（逐句對源＋可答性）、業主終審；補完基準缺口後一次交審；審核單形式沿 9.7 四張。
- 查證：`canon_visible` 第一行 `reviewed_by is not None`；`canon/README.md` 審核規則。

## D8. 現有產物的定位（DSP-067 後）

| 產物 | 是什麼 | 定位 |
|---|---|---|
| 舊正本 210 條（20 已審） | 9.6 合併 53＋9.7 擴充 157（材料＝舊 kb 列＋幫助中心） | ⛔ 不當基準、⛔ 不當材料；**2026-09-23 已被 S3 生成的新正本取代**，封存於 `docs/archive/2026-09/canon-pre-dsp067/`（2026-09-23 已移出工作樹，內容在 git `c06575a9`） |
| 九架 drafts（`runs/outline-20260920/drafts-A…I.json`；人讀版 `inputs/outline-<架>-draft-20260920.md`） | 57 粗目／515 細目／1,327 句，全數對 jgb2 `b2ee2ac382ce` 或幫助中心，每架 verifier CONFIRMED | **新正本的唯一材料**；✅ 已由腳本生成 `canon/jgb/*`（2026-09-23，⛔ 不手改）；81 題裁完後重跑生成即可 |
| `inputs/outline-skeleton-20260920.md` | 九架→57 粗目→頁 的對應（含 10 頁排除、11 處換架） | 分母（每個功能都盤到了沒） |
| `inputs/page-surface-20260919.{json,md}` | 頁面樹 183 頁基準（D1） | 骨架的來源；只證明頁面全列 |
| 0b 頁×身分判定（`runs/page-0b-20260919/`、`schemas/feature-coverage.json`） | 每頁×兩身分「有無細目」 | 粒度對照，⛔ 不是覆蓋判定（有細目≠答對） |
| `demand-v2.json` 55 格、真實問句 | 售前講法證據 | 講法與優先序，⛔ 不是內容來源 |
| skill outline-curation 步 1–7 | 舊七步（intake→import） | 步 7 import 與 diff 仍用；步 2–5 的格制流程待 DSP-067 程式改動後重對 |

## D9. 不做（本輪）

租客線、業態分流（代管／包租細目分流）、商務中心客群、S4 答到率回測、部署、DB 寫入。

## D10. 順序（2026-09-20 現況）

0. ~~採 D1 即與 DSP-064 互斥~~ 已裁：DSP-065 取代 DSP-064；DSP-065a 剔除無頁路由；DSP-067 定三層。
1. ✅ 代理對 D1～D8 逐條查證（2026-09-19）；✅ 業主裁 D1 粒度、住都排除、審核節奏（DSP-065／066）。
2. ✅ 步 0 改吃頁面樹（`page_surface.py`，183 頁）；✅ 骨架 57 粗目（三輪 verifier）業主「同意」（DSP-067）。
3. ✅ 九架起草（executor 起草＋verifier 逐句對源，每架 3–4 輪至 CONFIRMED）；總表與 81 待裁題 `inputs/outline-summary-20260920.md`。
4. ⏳ 業主審總表與九份人讀版、裁 81 題 → 依裁決修 drafts（腳本）。
5. ✅／⏳ 程式面（Plan 9.10）：`canon_parser` 放行架下粗目（S1 ✅）、`build_canon_toc` 改列粗目（S2 ✅）；**預算重量已取消**——真值量過後兩張常數表都不改；D6 的 `sources` 非空檢查**已在 parser 目錄路徑生效**（`_build_fine(require_fine_attrs=True)`），待處理的是它造成的既有紅燈；skill 分母改粗目仍待辦。
6. ✅ 已用腳本把 drafts 生成新正本 `canon/jgb/*`（2026-09-23，S3）；舊 210 條封存 `docs/archive/2026-09/canon-pre-dsp067/`（2026-09-23 已移出工作樹，內容在 git `c06575a9`）。全未審 ⇒ 模型看不到；審核照 DSP-066；部署由業主。
