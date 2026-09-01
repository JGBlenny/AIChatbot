# 檢索覆蓋率主線計畫（v2）

> 建立 2026-09-01｜v2 依獨立審查全面改寫｜狀態：**PROPOSED，等待業主批准**
> 業主目標序列：驗證架構 → 治「單一知識點覆蓋率不足」→ 擴測試情境 → 大量回測驗證 → 補知識庫 → 上版
> v1 已作廢：其 P0-1 建立在錯誤前提上，且漏掉真正的阻塞（量測 harness 不存在）

---

## 0. 事實基準（2026-09-01 經二輪獨立稽核；⛔ 無出處者不得寫入本檔）

```text
知識庫
  active 知識                     922
  有 retrieval_representation       9   ← **1%**；913 筆每次檢索仍用 legacy question_summary
  有 embedding                    871   ← 51 筆 active 無向量
    ⚠️ 這 51 筆**兩條路都進不去**：vector 路徑要求 embedding IS NOT NULL
       （vendor_knowledge_retriever_v2.py:142）；keyword 路徑要求 keywords 非空（:285-286）
       實查 51 筆中 keywords 非空者 = **0** ⇒ 絕對檢索不到
  空 answer（面向進場錨點）         98
  （正對照：generation_metadata 本身 477/922 有資料 ⇒ 上述 9 非查詢假象）

測試資料
  test_scenarios                4,875   全 active
    有 expected_category        3,533   72%
    有 related_knowledge_ids       24  0.5%
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
```

### P0 建尺（⛔ 不動任何產品行為）

```text
P0-0  裁決缺口盤點與呈核                                        我做＋業主裁
  待裁 ① expected_answer 全 0 ⇒ 答案正確性只有 heuristic 尺
          （evaluate_answer_v2 門檻硬編在被驗方 repo——freeze_measurement docstring
           自己就把「及格線在被驗方手上」列為系統性缺陷）
          ⇒ 明文接受此尺，或排補 expected_answer 的工作
       ② 療效訊號門檻 —— **業主裁定：屆時再評估，取決於測試資料品質**
          ⚠️ 參考下限：同 HEAD 重跑變異 13%（14/107）
  出口  兩項各有明文裁決並落檔

P0-1  量測 harness 擴充（**取代 v1 的 collection 接線，為真前置**）    我做
  目的  現有工具產不出計畫承諾的任何數字
  步驟  ① 選題端補讀 expected_category、related_knowledge_ids
        ② 判定端新增兩個獨立指標：路由分類正確率、檢索命中正確率
           ⛔ 不改既有 evaluate_answer_v2／_gold_checks 的行為（避免動到既有判定）
        ③ 修掉或明確繞開 backtest_framework_async.py:1304 的斷裂入口
        ④ pass 判定規則凍結於單一檔案，⛔ 不散落
  出口  以 20 題小樣本跑出「路由正確率」「命中率」兩個數字，且獨立重算一致
  ⚠️ 這是**開發任務**，不是「跑既有工具」

P0-2  檢索命中 ground truth 標註（100 筆）                      我做＋業主核判準
  前置  P0-0①
  步驟  ① 判準先寫死並經業主核可（什麼叫「該命中這筆」）
        ② 從 user_question 來源 982 筆真實問題挑 100 筆
        ③ 逐筆標「應命中知識 id」＋「是否該進面向」
           ⚠️ 可用 test_scenarios.question_embedding 做候選推薦，⛔ 但不得取代人工判定
        ④ 正負對照：含已知會過與已知會敗各數筆
  出口  100 筆標註凍結（sha256），且尺在 3 樣本下看得見已知病灶
  ⛔ 標註不得由實作方單獨完成

P0-3  知識庫覆蓋率盤查                                          我做，唯讀
  步驟  ① 913 筆缺 declaration 的清單與分型
        ② **扣除不變量 16 管的 alias／錨點**與「answer 缺的不可補造」列 ⇒ 得**適格母體**
        ③ 51 筆無 embedding 的成因｜④ 98 筆空 answer 錨點分型
  出口  適格母體數字（⚠️ 913 是毛數字，⛔ 不得當分母）

P0-4  51 筆無 embedding 處理（**從 v1 的 P3-2 提前**）           我做
  理由  獨立、便宜、立刻消滅「絕對檢索不到」族群（兩條檢索路都進不去）
  ⚠️ 走 Level-A 批准路徑；⛔ 禁用 regenerate_all_embeddings

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
  前置  P0-1、P0-2、P1-1
  步驟  ① 先驗容器與 HEAD 一致（舊 image 會讓整輪翻盤）
        ② 確認 ENABLE_RERANKER 實際值（程式預設 false／compose true）
        ③ 分批跑 3,533 題（有 expected_category）＋ 100 筆命中標註集
  預算  ⚠️ 歷史 60 題／210–500 秒 ⇒ 3,533 題估 **3.5–8 小時**；
        多輪模擬器與生產 chat 全程呼叫 OpenAI ⇒ 費用需先估並呈報
  ⚠️ **與 SEC-01 換 key 時點協調**——回測中途換 key 會整輪作廢
  出口  路由正確率、命中率各有數字與分母

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
```

---

## 6. 每輪固定回報

```text
主線進度    階段（P0–P4）／任務編號／出口條件達成與否
遇到問題    具體卡點 ＋ 誰能解（我／業主裁決／外部條件）
優化了什麼  對照哪個指標、數字動了多少；⛔ 動不了就寫「無」
```
