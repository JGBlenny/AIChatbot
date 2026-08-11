# 智能客服「回報」案例修正 SOP

把線上使用者按「回報」的案例，流程化地變成：已分類的缺口 → 已驗證的修正 → 防回歸的測試案例。本 SOP 由批次 20260731（R-31～R-37）實戰驗證定型；登錄簿見 `assistant-report-regression.md`。

```
① 同步登錄 → ② 分類 → ③ 查證事實 → ④ 修正 → ⑤ 本機驗證 → ⑥ 部署驗收 → ⑦ 標「已入回測」
```

---

## ① 同步與登錄

**回報來源（S3）**：

- **Bucket**：`s3://jgb2-production-upload/assistant-reports/`（region `ap-northeast-1`；CloudFront `d1h2hzes3rmzug.cloudfront.net` 可直接下載）
- **路徑規則**：`assistant-reports/{年}/{月}/{Ymd_His}_role{角色ID}_{40碼亂數}.md`
- **內容**：每筆一份 Markdown 逐字稿——回報時間、user_id、團隊/角色、頁面、session_id、使用者填的問題描述、完整對話
- **寫入端**：使用者在 JGB 平台對 AI 對話按「回報」→ jgb2 `HelpAssistantController@report`（`POST /api2/assistant/report`），disk/前綴設定在 jgb2 `config/services.php` 的 `assistant_report`
- 注意：「回報」＝使用者對 AI 對話的回饋，**不是報修**（報修走 `/api/external/v1/repairs`）

```bash
# 列出全部回報
aws s3 ls s3://jgb2-production-upload/assistant-reports/ --recursive
# 下載上次批次之後的新檔（比對登錄簿「處理批次」表的涵蓋範圍）
aws s3 cp s3://jgb2-production-upload/assistant-reports/<年>/<月>/<檔名> ./
```

每筆新回報在登錄簿依 R-編號續列，記：來源檔名、團隊/role、頁面、session_id、**問句原文**、實際行為、**正確期望**（回報人怎麼說就怎麼記，這是之後的通過標準）。批次表補一列。

## ② 分類（決定修法）

| 分類 | 特徵 | 修法（見④） |
|---|---|---|
| 路由缺口 | 帶具體 ID/編號問實際資料，卻被通用知識直答或 fallback | 補面向分類／錨點 |
| 知識錯誤 | AI 講的規則與系統實際行為不符（常由回報人指正） | 勘誤（含解碼器同掃） |
| 知識缺漏 | 功能存在但無知識可答，走 fallback | 新增知識 |
| 能力缺口 | 期望的查詢方式上游 API 不支援 | 誠實引導＋J 清單轉交 |
| 程式 bug | 佔位符外洩、卡住、500 等 | 修碼（先紅後綠） |

同型案例（多筆同根因）併成橫向問題（T-x/B-x），修一次收多案。

## ③ 查證事實（鐵則：不憑印象、不信 AI 原答案）

- **系統行為**一律對 jgb2 原始碼：`/Users/lenny/jgb/project/jgb_1/jgb2`（preview 分支）。狀態機看 model 常數與 `canXxx()` 方法；功能存在與否看 `routes/*.php` 是否為通用路由（客製後綴如 `-ziyu` 不寫入通用知識）。
- **API 能力**看 `app/Http/Controllers/External/`（AI 只接 `/api/external/v1/` 系列）。
- 回報人的「正確期望」也要查證——他們對，就是通過標準；他們記錯，記入登錄簿說明。

## ④ 修正

**載體**：資料改動集中一支冪等 migration（放 `rag-orchestrator/database/migrations/`，`YYYYMMDD_` 前綴；UPDATE 用內容特徵定位、INSERT 用 question_summary 判重；新知識列 embedding 留 NULL 並在檔頭註記需補嵌）。程式改動照常提交。

各分類要點：

- **路由缺口**：查資料型知識**必須掛面向診斷分類**（如 `條件診斷：帳單`、`續約`），否則它當檢索 top-1 時會直答不進面向——這是 T-1 的根因，日後匯入知識時就要掛好。短句（如「716317 帳單收據金額」）相似度不足時，照口語錨點範式補**空答案錨點**：一種講法一筆、掛面向分類，勿多講法塞同筆（會稀釋向量）。
- **知識錯誤**：改知識條目＋**同步掃三處有無同一錯誤斷言**：①相關系統脈絡（`系統脈絡：…` 條目）②決定性解碼器（`services/jgb/*.py` 的 diagnose/formatter 函式）③其他知識條目（grep 關鍵句）。R-33 的教訓：只修知識，面向底稿仍會吐解碼器裡的錯話。
- **知識缺漏**：question_summary 用短主題關鍵字；answer 先述情境再帶條件；business_types/target_user 照同類條目慣例（多為 `{system_provider}`/`{property_manager}`）。
- **能力缺口**：寫誠實引導知識（明說 AI 不支援＋教後台路徑），並在登錄簿「轉交 jgb2（J 清單）」立案。
- **程式 bug**：先加會失敗的回歸測試（紅）→ 修碼 → 全綠。解碼器類修正必須鏡射 jgb2 真碼，不自創規則。

## ⑤ 本機驗證（先定標準再跑）

**前置閘門（0 步，不可跳）：`make audit` 必須先過，重點是不變量 3「服務容器內關鍵檔案與本地一致」。**
容器跑舊 image 時，整輪回測結論不具效力——20260810 批實錘：撤案還原後未重建容器，第一輪 107 輪
重播判出「10 筆宣稱已修的知識 MISS」等一長串劣化，重建 image 重跑後 10 筆全部命中，結論全數作廢。
不變量 3 未過 → 先 `docker compose -f docker-compose.prod.yml up -d --build --no-deps rag-orchestrator`
（碼包在 image，restart 無效），再開跑。**凡重播結果與登錄簿既有結論衝突，先驗容器一致性，
再談知識或引擎缺陷。**

同理，**判定「系統不穩定」前要先分離變異來源**：同一 image、同一輸入至少跑兩輪對照，
再加單輪受控探測（同句 ×N 個新 session）。20260810 批據此才分清「多輪路由非決定性 13%（真）」
與「單輪檢索抖動（假，12/12 一致）」。

環境注意：**本機 rag-orchestrator 接的是 preview 真 API**（非 mock）——prod 的資料編號在 preview 查無是正常的；要驗「答出實值」需用 preview 實際存在的編號（可先 `curl preview API` 找一筆）。

1. **套用**：psql 跑 migration＋手動記帳（`schema_migrations`）；`docker cp` `tools/embed_missing.py` 進容器補嵌；程式改動要 `docker compose -f docker-compose.prod.yml up -d --build --no-deps rag-orchestrator`（碼包在 image，restart 無效）。
2. **逐案通過標準**寫成可判定敘述（進哪個面向／必含或禁含哪些字串），對照登錄簿「正確期望」。
3. **必跑三類**：
   - 案例原句 → 應命中修正後行為（log `分類命中 <facet>` 佐證）
   - **回歸句**：無 ID 泛問（「…怎麼計算」「…怎麼下載」）仍須直答知識，不得被拐進面向要編號
   - **真對話 e2e**：用 preview 真編號跑完整多輪（追問→給編號→答實值），對 API 原始回應核對數字——這一步在 20260731 批抓到解碼器漏網之魚，不可省
4. `scripts/run-tests.sh unit` 全綠。
5. **兩層獨立驗證，缺一不可，過完才 commit**（20260803 批實證：單句斷言 18/18 全過，情境回測仍抓出 P1）：
   - **第一層｜斷言 verifier**：乾淨脈絡 agent 逐項驗可判定條件（進哪面向/必含禁含字串/DB 值）——管回歸，快而可重複。
   - **第二層｜情境回測 agent（收案關卡）**：agent 扮演回報人，**同 session 多輪**把情境走到解決或卡死，語義判 PASS/FAIL。要求：口語開場、依 AI 回覆自然追問、直指矛盾時觀察是否回頭；測試用的編號/資料必須與所用 role 權限圈配對（拿別的 role 的帳單編號查無是正確行為，不是 bug）。單句命中不算過——多輪後路由換面向、引用到矛盾舊知識、查無死結，都只有這層抓得到。
   - 情境回測發現逐項處置（FIX/DEFER/REJECT），P1 修完須**重跑同情境**確認收斂。
6. **知識矛盾同掃**：新增/修正知識時，grep 同主題既有條目（含面向專用分類如「建約引導」下的條目）——新舊知識並存且互斥時，多輪對話會在不同輪引用不同筆，把使用者帶向錯誤指引（F1 教訓：矛盾要雙向調和，不是只加新的）。

## ⑥ 部署與驗收

在 `docs/deployment-runbook.md` 加一節（照 §18 範式）：git pull → runner dry-run/--apply → 補嵌 → 重建容器 → 資料側補值 → 驗收 curl（含案例原句與健康檢查）。prod 由使用者執行；「進面向後答實值」的最終驗收只能在 prod 做。

## ⑦ 收案

- 登錄簿狀態：`待處理` → `已修正（本機驗證 日期）` → prod 驗過 → `已入回測`（把問句納入對應面向回測集）。
- 轉交項（J 清單）、待觀察項（未立案的鄰近缺口）分節記錄，不混入案例。
- commit 訊息引用批次與案例編號；一次性驗證腳本不 commit。

---

## 檔案地圖

| 檔案 | 角色 |
|---|---|
| `docs/backtest/assistant-report-regression.md` | 案例登錄簿（來源、批次、狀態、J 清單） |
| `docs/backtest/assistant-report-workflow.md` | 本 SOP |
| `rag-orchestrator/database/migrations/YYYYMMDD_assistant_report_*.sql` | 每批修正的資料載體 |
| `docs/deployment-runbook.md` §18 起 | 每批的 prod 部署節 |
| `/Users/lenny/jgb/JGB回報_完整對話逐字稿_*.md` | 逐字稿彙整（repo 外，給人看） |
