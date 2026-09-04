# 檢索覆蓋率主線計畫（v2）

> 建立 2026-09-01｜v2 依獨立審查全面改寫｜**v2.1 2026-09-01：併入 P0-3 結果與答案驗證軌**
> 狀態：**PROPOSED，等待業主批准**
> 業主目標序列：驗證架構 → 治「單一知識點覆蓋率不足」→ 擴測試情境 → 大量回測驗證 → 補知識庫 → 上版
> v1 已作廢：其 P0-1 建立在錯誤前提上，且漏掉真正的阻塞（量測 harness 不存在）

---

## 0. 事實基準（2026-09-01 經二輪獨立稽核；⛔ 無出處者不得寫入本檔）

```text
知識庫（⚠️ 分母已由 P0-3 修正，見 p0-3-knowledge-coverage-census.md）
  active 知識                     922
  − 設定列（系統脈絡27＋對話規則23＋4253）51  ⛔ 不是知識，retriever 兩條路都寫死排除
  − 錨點列（answer 空，⛔ 不可補造）       98  （與設定列交集 0，非重複扣除）
  = **適格母體                     773**
    其中已宣告 representation         6   ⇒ **覆蓋率 6/773 = 0.78%**
  ⛔ **913 不得當分母**（把設定列與錨點列都算進去了）
  有 retrieval_representation       9   ← 9 = Level-A V2 全體；其中 3 筆落在上面的 98 內
  有 embedding                    871   ← 51 筆 active 無向量
    ⚠️ 這 51 筆**兩條路都進不去**：vector 路徑要求 embedding IS NOT NULL
       （vendor_knowledge_retriever_v2.py:142）；keyword 路徑要求 keywords 非空（:285-286）
       實查 51 筆中 keywords 非空者 = **0** ⇒ 絕對檢索不到
  空 answer（面向進場錨點）         98
  （正對照：generation_metadata 本身 477/922 有資料 ⇒ 上述 9 非查詢假象）

測試資料
  test_scenarios                4,875   全 active
    有 expected_category        3,533   72%  ⚠️ **全部來自 imported 2,608／auto_generated 690／
                                          manual 235；user_question 佔 0** ⇒ 路由正確率若只跑這
                                          3,533 題，母體裡**沒有任何一句真實使用者問句**
    有 related_knowledge_ids       24  0.5%  ⛔ **實際可用 = 0**，24 筆全為懸空引用（見 D-3）
    有 expected_answer              0    0%   ⚠️ 見 §2 P0-0 的裁決缺口
    collection_id 非空              0    ⚠️ **與能否批次無關**，見下
    來源  imported 2608／auto_generated 1035／user_question 982／manual 250
  凍結語料 corpus-20260810      37 案／107 輪，26 輪有期望答案
    ⚠️ **同 HEAD 重跑 14/107（13%）路由類別不同**（corpus README:28）
       ⇒ 任何「療效」若小於此變異即為雜訊
  holdout 2026Q3                已凍結

歷史基準（⚠️ 母體 test_scenarios 548 題，**非 production holdout**，⛔ 不得宣稱線上品質）
  60.2% 污染舊尺 → **69.7%** 乾淨重批（scripts/audit/reports/regrade291-triage.md:3）
  → 75.2% 雙票（僅記憶檔記載）
  ⛔ 62.8% 不存在，全 repo/DB 查無來源（記憶檔已修正並加警語）
  最後回測 2026-07-06，距今 57 天

檢索管線
  分數合成  base_retriever.py:522 `_finalize_scores`；rerank 分支 `0.1×vector + 0.9×rerank`
  ⚠️ **只套在實際進 rerank 的候選**（RERANKER_INPUT_LIMIT=20、MIN_VECTOR_SIMILARITY=0.3）
     未進 rerank 者走 keyword/vector 分支 `min(1.0, max(vector,keyword)×boost)`
  ⚠️ **ENABLE_RERANKER 程式碼預設 false**（base_retriever.py:47）；
     `docker-compose.prod.yml:243` 才是 `${ENABLE_RERANKER:-true}`
     ⇒ 不經 compose 跑（單測／直起 uvicorn）reranker 是關的，分數管線完全不同
  keyword_boost  base_retriever.py:373，倍率 1.0–1.3
  客服回報型別   21/25 = 84% 知識題（docs/retrieval-recall-audit-20260822.md:55-59）
                 ⚠️ 母體僅 25 筆

版本狀態
  分支 fix/retrieval-routing-stability｜**463** 筆未 push｜repo 為 **PUBLIC**
  主線 spec tasks 57/64｜稽核不變量 25 條
```

---

## 1. 相關文件與資料在哪

```text
【規格】
主線        .kiro/specs/conversational-routing-execution/{requirements,design,tasks}.md
已封存      .kiro/specs/archive/retrieval-decision-layer/HALTED.md
架構母圖    docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md（⚠️ §3 有 5 處錯，見 §4）
檢索盤查    docs/retrieval-recall-audit-20260822.md｜參數台帳 docs/retrieval-parameters.md

【程式碼】
分數合成    services/base_retriever.py:522 `_finalize_scores`／:373 `_apply_keyword_boost`
知識檢索    services/vendor_knowledge_retriever_v2.py（:142 vector 條件／:285 keyword 條件）
表示法      services/retrieval_representation.py:122 `scoring_surface`
決策層      services/decision_layer.py（DecisionConfig／facet_entry_eligible）

【回測工具｜⚠️ 現況見 §2 P0-1】
可用 runner  scripts/backtest/run_backtest_with_db_progress.py
             選題＝env filter（BACKTEST_FILTER_*）＋BACKTEST_SAMPLE_SEED md5 排序＋LIMIT/OFFSET
             SELECT :113-115 **不含 expected_category／related_knowledge_ids**
判定         backtest_framework_async.py:851 `evaluate_answer_v2`（confidence＋semantic overlap）
             :706 `_gold_checks`（只驗 action_type/form_id/path/facts_tokens）
⚠️ 壞的入口  backtest_framework_async.py:1304 呼叫不存在的 `load_test_scenarios` ⇒ __main__ 一跑就炸
⚠️ 錯配工具  scripts/backtest/freeze_measurement.py 綁 corpus-20260810 母體，凍不了 test_scenarios

【表示法既有流程｜⚠️ 射程鎖死】
9 筆來源     database/migrations/{r9_level_a_retrieval_representation,p1e_level_a_reviewed_declarations}.sql
embedding    scripts/regenerate_level_a_embeddings.py —— **射程鎖死 LEVEL_A_ROWS**、
             只處理 approved declaration、任一非 reviewed 整批中止、
             與 semantic-model 重建是同一個 migration step
⛔ 禁用      scripts/regenerate_all_embeddings.py —— 全庫 legacy surface 重生，事後無法回推
完整性稽核    scripts/audit/checks/level_a_representation_completeness.py
alias 約束    scripts/audit/checks/entry_alias_contract.py（**不變量 16**，見 §2 P2-1）

【測試資料】
凍結語料    docs/backtest/corpus-20260810/（run2-head／run3-head 已在本機；S3 正本 sha256 b9c690cf…）
holdout     .kiro/specs/routing-disambiguation/evidence/holdout-2026Q3-*
歷史重批    scripts/audit/reports/regrade291-triage.md
DB          aichatbot_admin：knowledge_base／test_scenarios／backtest_runs／usage_events

【稽核】
scripts/audit/check_invariants.sh（25 條）｜scripts/audit/baseline_oracle.py
```

---

## 2. 階段任務

> ⚠️ **v1 的兩個錯誤已修**：
> ① collection 連結**不是**批次的前置——現行 runner 完全不讀它，49 筆歷史 run 皆如此 ⇒ 降級為選配
> ② 真正的前置是**量測 harness 擴充**——現有工具產不出「路由正確率」「命中率」任何一個數字

### 已完成（業主目標第 1 步：驗證架構）

```text
✅ 架構驗證 —— 二輪獨立稽核（2026-09-01），證據落在本檔 §0／§4 與兩份代理報告
   分數合成公式與其適用條件、15 項機制實作狀態、spec 範圍歸屬、文件與程式碼 5 處不符
   ⛔ 本項不再重做

✅ P0-3 知識庫覆蓋率盤查（2026-09-01，唯讀）
   出口達成：適格母體 **773**（不是 913）、覆蓋率 6/773
   落檔 `p0-3-knowledge-coverage-census.md`
   ⚠️ 順帶推翻 P0-4 前提（見下）＋抓到未記錄缺陷 D-1（見 §4）
```

### P0 建尺（⛔ 不動任何產品行為）

```text
P0-0  裁決缺口盤點與呈核                                        ✅ 兩項均已裁
  ① 答案正確性的尺 —— **業主定案 2026-09-01：⛔ 不補 expected_answer**
     改為「先自己建情境與接受範圍的回答，再派代理驗證」
     ⇒ 代理當**對帳員**（拿人工指定的來源對帳），⛔ 不當裁判（憑自身常識判對錯）
     ⇒ 及格線因此離開被驗方 repo，`evaluate_answer_v2` 的系統性缺陷被繞開
     ⇒ 執行協議固化為 skill `answer-acceptance-verify`；情境建置＝新的 P0-2
     ⚠️ claim ceiling：三型的率**分開報**，⛔ 不得合成單一「答案正確率」
  ② 療效訊號門檻 —— **業主裁定：屆時再評估，取決於測試資料品質**
     ⚠️ 參考下限：同 HEAD 重跑變異 13%（14/107）
  出口  ✅ 兩項均已明文裁決並落檔（本節即落檔處）

P0-1  量測 harness 擴充（**取代 v1 的 collection 接線，為真前置**）    我做
  ⚠️ **2026-09-01 改寫**：原本只寫「加路由正確率、命中率兩個數字」——**不夠**。
     實測發現：沒有背景資訊，「轉客服 +2」這種數字**無法判斷是缺陷還是正確行為**
     （b2b 是 precision-first，「該轉客服、也轉了」是正確的）。
     ⇒ 真正要做的是**輸出契約**：正本 `.claude/skills/retrieval-improvement-loop/steps/03-回測輸出契約.md`

  ### P0-1 的實際內容＝實作那份契約
```text
  跑前凍結（人裁兩格）
    expected_owner   knowledge_direct｜facet:<鍵>｜api｜**escalate**｜out_of_scope
    expected_kb_id   正解 id 或 NO_COVERAGE
  每輪自動落盤（機械，⛔ 不事後撈 log）
    ① 走了哪條路   usage_events：processing_path／facet_key／decision_case／分數
    ② 候選與分數   生產 debug 開關（⛔ 不自寫 SQL）
    ③ **可見性**   對 expected_kb_id 機械算三軸過濾 ⇒ 直接標「正解存在但這角色看不到」
    ④ 面向職責     該面向的 topic_scope／grounding_scope／responsibility
    ⑤ 環境指紋     printenv 實查 ＋ reranker 實際狀態 ＋ **USE_MOCK_JGB_API**
  ⇒ 有了 A＋B，每題自動歸類：門檻／排序／**可見性錯配**／知識缺口／進場錯／**正確轉客服**
```
  ⚠️ 實證：kb:3336 是 ts9885 的正解，但業態不含 system_provider ⇒ b2b 看不到
     **改一個欄位就好，補再多知識都沒用** —— 沒有第③格就會誤判成知識缺口
  ⚠️ API 型（T2）判準完全不同：**逐欄比對 API 回傳**，⛔ 不用知識庫、⛔ 不交 LLM 判語義
     LLM 只判一件事：有沒有超出 facts 亂講。詳見契約 §D

  步驟  ① 選題端補讀 expected_category、related_knowledge_ids
           ⚠️ related_knowledge_ids 現有 24 筆**全懸空**（D-3）⇒ 補讀本身沒錯，
              但 ⛔ 不得預期它產出任何命中真相；命中母體必須由 P0-2 新標
        ② 判定端新增兩個獨立指標：路由分類正確率、檢索命中正確率
           ⛔ 不改既有 evaluate_answer_v2／_gold_checks 的行為（避免動到既有判定）
        ③ 修掉或明確繞開 backtest_framework_async.py:1304 的斷裂入口
        ④ pass 判定規則凍結於單一檔案，⛔ 不散落
  出口  20 題小樣本跑完後，**每題可直接歸類**（含可見性判定），
        且「路由正確率」「命中率」兩個數字獨立重算一致
        ⛔ 只有數字、無法歸類 ⇒ 不算完成
  ⚠️ 這是**開發任務**，不是「跑既有工具」

  ### ⛔ 出口補強（2026-09-02 獨立設計審查 REVISE 後）
```text
  ⚠️ 上面那條「每題可直接歸類」**單獨恆真且無資訊量**——舊契約矩陣有 catch-all
     「以上皆非 ⇒ T or R」，任何案例都能被吸收，形式上 100% 可歸類而歸類可能是錯的。
     實證：2026-09-02 的 35 題裡，11 題轉客服中有 5 題落不進七類
     （4 題被 `_top1_relevance_gate` 清空、1 題被 `_drop_empty_answer_rows` 清空），
     而它們會被 catch-all 判成 T／R —— 門檻已過、正解已在前列，那兩種修法
     **在物理上不可能有效**。
  ⚠️ 不對稱：P0-2 出口②要求「尺自證：已裁定病灶餵進判官必須全紅」，
     **答案側有突變控制、檢索側沒有**。本節補齊。

  ① UNCLASSIFIED 第三格：出現 ≥1 筆即停止並交裁決
     ⛔ 不得併入任何一類（比照 §5 的 UNJUDGEABLE 紀律：單獨報）
  ② 每題歸類須附**可覆核證據欄位清單**（指名 §B 哪一格哪個值）
     ⛔ 指不出來者一律 UNCLASSIFIED；⛔ 指到 log／oracle／旁路均不算
  ③ 分類器突變控制：ts9945／ts7620／ts9833 必須為 G 或 UNCLASSIFIED，
     ts8143（top1 0.167、全未過門檻）**必須為 T**（正對照，證明新類不是萬用桶）
  ④ 契約 §B 新增第⑥格「否決軌跡」；生產側未儀器化前一律 NOT_OBSERVABLE
     ⇒ 該題歸 UNCLASSIFIED，⛔ 不得撈 log 補值
  ⚠️ **出口條件本身是否足以當收案依據 ＝ 業主裁**，⛔ 不得由實作方自行宣告達成。
```

  ### ❓ 本節產生的待裁清單（⛔ 未裁前 P0-1 到不了出口）
```text
  ① max_checks=2「未受審候選一律丟棄」算不算正確行為      決定失敗率怎麼算
  ② b2b fail-closed 清空整批算不算正確行為                同上，且須與①分開計
  ③ G 類的修法允不允許動 gate（max_checks／prompt／策略）  決定 P2 的方向
  ④ 要不要在 P1 基準之前把否決軌跡儀器化（動 chat.py）    §5 明訂基準前不動門檻與規則
  ⑤ escalate／out_of_scope 要不要逐題核可                 這兩格直接決定分母
  ⚠️ ①②的背景：2026-08-22 的裁示射程只到「gate 判準從『相關』改為『適用』」，
     ⛔ 不涵蓋 max_checks 與 fail-closed。援引它把兩者判為正確行為會
     **結構性壓低失敗率**，並把 gate 這個真正的槓桿排除在改善清單之外。
```

P0-2  三型測試情境與接受範圍建置                              我草擬＋業主核
  前置  P0-0①（已裁）｜協議 `.claude/skills/answer-acceptance-verify/SKILL.md`
  ⚠️ **業主定案 2026-09-01：對話流程／API 查詢／單筆知識，三型各別建集、各別報率。**
     正解的**來源**不同，尺就必須不同；⛔ 不得混批，⛔ 不得合成單一正確率。

  P0-2-T1  單筆知識題                                        第一批，先做
    正解來源  人工標「該命中哪筆」⇒ 該 knowledge_base row 的 answer 欄位即答案本體
              ⇒ **標了命中就免費得到答案尺**，不必另寫標準答案
    尺        rubric 三欄：必含事實／禁止內容／允許差異（逐條可打勾）
    母體      適格母體 773 中的 direct_answer 739
    起手      25 案現成（`corpus-20260810/expected_answers.json`，逐字取自客服逐字稿
              的「標準答案」欄）＋業主指定痛點若干
    ⚠️ 逐字標準答案 ⛔ 不得直接當 must_have——換講法就誤殺，率會被壓成雜訊

  P0-2-T2  API 查詢題                                        次做
    正解來源  API 回傳本身；formatter 的決定性輸出（facts）
    尺        **決定性逐欄比對**；LLM 只判一條：有沒有超出 facts 亂講／自己算數字
    母體      api_call 錨點 27 筆 ＋ grounding_scope.select='api' 的面向
    ⛔ 機械可解碼的事實不交 LLM 判（本專案已裁：formatter 算 facts、LLM 只組話）
    ⚠️ 跑之前先確認 USE_MOCK_JGB_API 實際值——mock 與真 API 的正解不同

  P0-2-T3  對話流程題                                        末做，門檻最高
    正解來源  逐輪期望的**動作**（該追問什麼／進哪個面向／該收斂／該退出），⛔ 非字句
    母體      corpus-20260810：37 案／107 輪
    判定單位  **以案為單位**，⛔ 不以輪報率（同 HEAD 重跑變異 13%）
    ⚠️ 已知引擎級缺口（追問不帶上下文 E-2、面向誤搶接與黏著 E-3）會集中在這一型
       ⇒ 這一型的 FAIL ⛔ 不得直接歸因為知識覆蓋率不足

  出口  ① 每型各自的 rubric 凍結（sha256）＋業主核可紀錄
        ② **尺自證通過**：三個已裁定病灶（收據 NT$0／iot 搶接反向否定／3863 矛盾知識）
           餵給判官必須全紅；任一漏抓 ⇒ 尺是瞎的，⛔ 該輪停止
        ③ 判官散度（同輸出重跑 ≥3 次）小於系統側 13%
  ⛔ rubric 不得由實作方單獨定案；我草擬並機械抽候選，業主核可才生效
  ⛔ 沒有真相來源的情境不進批次——不得用代理生一個答案來湊
  ✅ **業主定案 2026-09-01：T1 第一批 30 題**

  ### T1 batch-01 組成（草稿已產出 2026-09-01）
```text
  已有        21 案  出自 corpus-20260810 的 25 案，扣掉分型為 T2 的 4 案
                     （31|1 收據金額、35|1 點退金額、36|1 租客合約 ID、37|1 續約歷程）
                     ⇒ must_have 57 條、must_not 8 條，逐字取自客服標準答案，⛔ 未改寫
  待補         9 案  ⛔ 選題規則須先凍結、且**在跑系統之前**定案
  草稿檔      rubric-batch-01-T1.draft.json（DRAFT_PENDING_OWNER_APPROVAL）
  T2 種子檔   rubric-batch-T2.seed.json（4 案，本輪不判）
  待業主逐條裁 09|13（含元註記）、18|2（同一條混了正／負命題，已提兩條拆分提案）
```
  ⚠️ **claim ceiling（本批專屬）**：這 21 案的語料**已驅動過修正**（P1-a 等）
     ⇒ 對它們而言是**回歸尺**（不得再壞），⛔ **不是**留出集，
     ⛔ 通過率不得當作泛化能力或線上答案品質的證據。
  ⚠️ 型別判定規則已在**看過任何系統輸出之前**寫死：
     T2 ＝ 問句要求某一筆實體記錄的**現值**；T1 ＝ 其餘（機制／規則／操作方法），
     句中出現編號但正解不依實值者仍為 T1（例 18|2）

P0-3  知識庫覆蓋率盤查                                    ✅ **已完成 2026-09-01**
  步驟  ① 913 筆缺 declaration 的清單與分型
        ② **扣除不變量 16 管的 alias／錨點**與「answer 缺的不可補造」列 ⇒ 得**適格母體**
        ③ 51 筆無 embedding 的成因｜④ 98 筆空 answer 錨點分型
  出口  ✅ 適格母體 **773**｜落檔 `p0-3-knowledge-coverage-census.md`
        ⚠️ 913 是毛數字，⛔ 不得當分母

P0-4  51 筆無 embedding 處理                    ⛔ **業主定案 2026-09-01：不做**（前提已被推翻）
  ⚠️ 原文的理由「兩條檢索路都進不去 ⇒ 絕對檢索不到，優先消滅」**是錯的**。
     P0-3 實查：51 筆 = 系統脈絡 27 ＋ 對話規則 23 ＋ id 4253，
     全是**設定列**（system_context.py／load_rules 依 category 載入後注入 prompt），
     且 retriever 的向量路徑與 keyword 路徑**都寫死** `category IS DISTINCT FROM` 排除。
     ⇒ 沒有 embedding 是**正確狀態**；補了等於把系統提示詞丟進檢索候選池、直接污染排序。
  ⇒ ✅ 已從 P0 移除，記入 §5「明確不做」
  ⚠️ `tools/embed_missing.py` 已有前綴防護，今天跑它會選出 **0 筆**（已實測；
     正對照：`embedding IS NULL` 確實有 51 筆，查詢路徑是通的）
     ⛔ 但不得改用「補完所有 NULL embedding」的其他寫法

P0-5  collection 連結（**降級為選配**）                          我做，低優先
  ⚠️ 非批次前置（runner 不讀它）；四個 collection 已存在（init-legacy seed），⛔ 不需建立
  ⚠️ 兩套 schema 並存未裁：單欄 collection_id vs 多對多 test_scenario_collections
  ⇒ 僅在有管理需求時做；⛔ 不阻塞任何後續任務
```

### P1 量基準

```text
P1-1  建立 test_scenarios 母體的量測凍結物                       我做
  ⚠️ ⛔ 不用 freeze_measurement.py（它綁 corpus-20260810 母體）
  內容  判準／分母／尺版本／**重跑變異基線**（同 HEAD 連跑取變異）
  出口  凍結物落檔含 sha256

P1-2  跑第一次大量回測                                          我做
  前置  P0-1、P0-2（至少 T1 已凍結且尺自證通過）、P1-1
  步驟  ① 先驗容器與 HEAD 一致（舊 image 會讓整輪翻盤）
        ② 確認 ENABLE_RERANKER 實際值（程式預設 false／compose true）
        ③ 分批跑 3,533 題（有 expected_category）＋ 100 筆命中標註集
  預算  ⚠️ **時間才是限制，⛔ 不是錢**（2026-09-02 實測更正）
        時間  歷史 60 題／210–500 秒 ⇒ 3,533 題估 **3.5–8 小時**
              ⚠️ ⛔ 不得並行縮短——semantic-model 是 CPU 推論（>90s、600%+），
                併發會讓 reranker 逾時而靜默落到詞面分支，整輪數字作廢
        費用  實測 `usage_events.est_cost_usd`：114 事件 $0.0185 ⇒ 約 **$0.00016／題**
              ⇒ 3,533 題估 **≈ $0.6**。⛔ 別為了省錢縮母體或減輪數。
  ⚠️ **與 SEC-01 換 key 時點協調**——回測中途換 key 會整輪作廢
  出口  路由正確率、命中率各有數字與分母
  ⚠️ **claim ceiling**：3,533 題母體裡 user_question 佔 0 ⇒ ⛔ 不得宣稱「真實使用者問句的
     路由正確率」，只能宣稱「imported／auto_generated／manual 題庫上的路由正確率」

P1-3  錯誤分型                                                  我做
  分成  召回不到／召回到但排序輸／路由錯／答案錯
  出口  各類數量與代表案例 ⇒ P2 的工作清單
```

### P2 治單一知識點覆蓋率

```text
P2-1  表示法覆蓋 pilot（**業主裁定：50 筆**）                    我做＋業主核
  ⚠️ 現況：**無批次工具**。9 筆是 SQL migration 匯入；
     regenerate_level_a_embeddings 射程鎖死 LEVEL_A_ROWS ⇒ 需自建或解鎖射程
  ⚠️ Level-A 單筆先例成本：declaration → blocker → 實作＋6 guard＋3 mutation → 業主 APPROVED
     ⇒ pilot 的目的就是量出**單筆真實成本**與**療效**
  步驟  ① 從 P0-3 的適格母體、依 P1-3 錯誤清單排序，取 50 筆
        ② 逐筆產 reviewed declaration（⚠️ 必須理解實際對話流程，
           ⛔ 不得把資料直接丟 LLM 批量生成——那正是 conversation-retrieval-resilience
             整案還原的形狀）
        ③ **每批綁 embedding regen ＋ semantic-model 重建**
           ⛔ 不重建即量到舊 surface，數字無效
        ④ 重跑 P1-2 子集，對照 P1-1 的重跑變異基線
  出口  單筆成本（人時／LLM 費用／審核輪次）＋ 療效數字
  ⚠️ **pilot 未過門檻前 ⛔ 不擴大到 913**

P2-2  依 pilot 結果決定是否擴大                                 業主裁
P2-3  一知識一問法（變體表 knowledge_variants）                 ⚠️ 業主裁 owner
  現況  未實作；設計在已封存 spec 的 P2 3.4
  ⛔ P2-1 未證明成效前不啟動
```

### P2.5 缺口地圖（**PROPOSED 2026-09-04**，業主尚未裁；由 presales-grounding-gate 收案後的 skill 盤查提出）

```text
問題  retrieval-improvement-loop 是「一輪修一題型一成因」的迴圈：樣本凍結→燒毀，每輪結束沒有東西說「主題空間還剩哪幾格是空的」。
      覆蓋率要有分母，現在只有供給側盤點（status.py 面向覆蓋＝知識筆數，⛔ 不是答案覆蓋），沒有需求側全集。
產物  一張地圖：需求側分母 × 供給側狀態，⛔ 是盤點不是測試集 ⇒ 不受 steps/07 燒毀規則約束、跨輪累積。
分母  ① 幫助中心 zh-Hant 頁面（~/jgb/幫助中心/JGB幫助中心_HTML_交付_20260818）× 角色（pm／landlord／tenant／prospect）
      ② test_scenarios user_question 依主題分群（expected_category 全空 ⇒ 分群要自己做並凍結）
      ③ 產品功能索引（3622 基礎 md／3798 售前脈絡）逐條
每格四態  已覆蓋（G0 四查有正解且 e2e 答得到）／表示法缺（庫裡有、口語講法撈不到＝成因 S）／缺口（成因 N，過 G0）／
          **刻意不補**（業主裁走轉人：客戶案例、規模數字、SLA…）——第四態要登錄，否則每輪重抽重判重上呈
與迴圈的關係  迴圈每輪的 NO_COVERAGE／S／N 判定回寫地圖對應格；地圖的空格是下一輪選題的候選來源（⛔ 仍走 steps/01 凍結紀律抽樣，不直接拿地圖當樣本）
工具  scripts/status.py 加一節印地圖摘要（每角色：四態各幾格）；逐格清單落 .kiro/specs/.../coverage-map.json（含 G0 證據路徑）
先決  P0 建尺（尺沒驗過，地圖的「已覆蓋」不可信）；匯入工具已強制 instance_applicability（2026-09-04 完成，見 knowledge-batches/README）
成本  分母 ① 需人工對頁面分角色一次；② 分群一次；之後每輪增量回寫
⛔ 不做  用被驗系統自己的檢索排序來判「已覆蓋」（尺與系統同構）；用地圖格數當療效數字（療效只在 /api/v1/message 那層量）
```

### P3 補知識庫

```text
P3-1  依 P2 殘餘錯誤補知識內容                                  我做＋業主核
P3-2  98 筆空 answer 錨點依 P0-3 分型處置
```

### P4 上版

```text
P4-1  SEC-01 現行 OpenAI key 撤銷換新                           業主執行
P4-2  SEC-02 AWS Access Key ID 在 public repo 歷史              業主裁定
P4-3  PUB-01 揭露決策（463 筆未 push 含全部 specs 與稽核紀錄）    業主裁定
P4-4  部署（含 semantic-model 重建）                            業主執行
```

---

## 3. 硬 blocker（與 P0–P3 平行，不阻塞前面）

```text
SEC-01  現行 OpenAI key 曾明文進 transcript，尚未撤銷
        ⚠️ 換 key 時點必須與 P1-2／P2-1 的回測協調
SEC-02  現行 AWS Access Key ID 在 **public repo** 歷史（origin/main 祖先）
PUB-01  repo 為 PUBLIC；SECRET-SAFE ≠ PUBLICATION-SAFE
```

---

## 4. 已知文件錯誤（⛔ 照文件改碼會出事）

```text
COMPLETE_CONVERSATION_ARCHITECTURE.md §3（實際行號 432-434）
  業者隔離漏掉「vendor_ids 為空＝全業者共用」放行；運算子是 && 非 @>
  角色隔離漏掉 NULL 放行與 all_users 通用放行
  ⚠️ **業態過濾漏掉 b2b 嚴格分支**——b2b 是 `&& ['system_provider']` 且**無 IS NULL 放行**
     ⛔ 照文件給 b2b 補 IS NULL 會打穿刻意設計的隔離
  :383  把仍在仲裁使用的 0.6 標成「已過時」（0.65 是檢索過濾門檻，兩個不同命題）
  :440  行號漂移；主排序鍵是向量相似度，priority 只是次鍵
chat.py:2624  註解引用「既有 append_turn 統一出口」——**全 repo 無此函式**
```

### D-1（P0-3 新發現，⚠️ 此前全 repo 未記錄）⏸ **業主定案 2026-09-01：先不動**，排在 P1 基準之後

```text
id 4253  question_summary =「系統脈絡：帳務領域-帳單診斷(子面向)」
         實際 category = '條件診斷：帳單'（其他 26 筆同型列都是 '系統脈絡'）
後果     system_context 的三條查詢都要求 category='系統脈絡' ⇒ 三條全不命中；
         又因無 embedding、無 keywords 而檢索不到 ⇒ **這一列在系統裡是死的**
         ⇒ **帳單診斷面向只拿到通用 base，領域脈絡層從未載入**
實證     pm_bill_diagnosis 的 topic_scope.category='條件診斷：帳單'，
         父鏈 ['條件診斷','條件診斷：帳單'] 兩層命中的系統脈絡列皆 0
正對照   '帳單異常' = 1 ✅｜'條件診斷：訂閱' = 1 ✅（⇒ 查詢路徑是通的）
⚠️ 這正是 HANDOFF-20260901 §2 收線實測走的那個面向
⚠️ 修法是一筆 UPDATE category ＋容器重啟（system_context 有進程級快取），
   但 ⛔ 在 P1 基準之前動它，會讓第一次回測失去乾淨基準（見 §5）

D-2  tenant_repair（修繕報修）同樣 own_layer = 0，且**從來沒寫過**系統脈絡列
     22 個 category 模式面向逐一盤查，只有 D-1／D-2 兩個缺；其餘 20 個都有
     ⚠️ 是否刻意設計**尚未查證**

D-3  ⛔ **`related_knowledge_ids` 的 24 筆標註全部懸空——可用的檢索命中 ground truth ＝ 0**
     實查   被引用的 distinct knowledge id 共 25 個，**存在於 knowledge_base 者 0 個**
            （引用值為 48–59 等小號；knowledge_base 的 min(id) = 1345）
     正對照 id 3402 查得到 ⇒ 查詢路徑是通的，不是查詢寫錯
     後果   ① §0「有 related_knowledge_ids 24」不得再當成「有 24 筆命中真相」
            ② P0-1 步驟①「選題端補讀 related_knowledge_ids」讀到的每一筆都是死引用
            ③ P0-2-T1 的 9 個缺額**不能**靠既有標註補——必須新標
     ⚠️ 分布：user_question 9 筆／manual 15 筆；imported 與 auto_generated 皆 0
```

---

## 5. 明確不做

```text
⛔ 責任架構橫向擴張（R-29 走通一條即停）
⛔ 在 P1 基準之前調任何門檻或對話規則
⛔ 動已封存的 retrieval-decision-layer（其 DecisionConfig 仍在生產運行）
⛔ 引用 62.8%；⛔ 拿 69.7%／75.2% 宣稱線上品質
⛔ 跑 regenerate_all_embeddings.py（全庫 legacy surface 重生，證據失去 provenance）
⛔ 以 913 為覆蓋率分母（毛數字，須扣不變量 16 的 alias／錨點）
⛔ 照 §4 的錯誤文件改程式碼
⛔ 把 collection 連結當成批次前置
⛔ 為 `embedding IS NULL` 的設定列補向量（P0-4 改判，理由見上）
⛔ 讓判官代理憑自身常識判 JGB 專有語義——它會替「聽起來合理但與庫相反」的錯蓋章
⛔ 把三型（單筆知識／API 查詢／對話流程）混批或合成單一「答案正確率」
⛔ 把 UNJUDGEABLE 併入 PASS 或 FAIL——它是第三格，單獨報
```

---

## 6. 每輪固定回報

```text
主線進度    階段（P0–P4）／任務編號／出口條件達成與否
遇到問題    具體卡點 ＋ 誰能解（我／業主裁決／外部條件）
優化了什麼  對照哪個指標、數字動了多少；⛔ 動不了就寫「無」
```
