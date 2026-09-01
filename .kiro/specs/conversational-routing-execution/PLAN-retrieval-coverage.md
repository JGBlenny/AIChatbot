# 檢索覆蓋率主線計畫

> 建立 2026-09-01｜狀態：**PROPOSED，等待業主批准**
> 目標序列由業主定：驗證架構 → 治單一知識點覆蓋率 → 擴測試情境 → 大量回測驗證 → 補知識庫 → 上版
> 本檔取代先前的 `PLAN-mainline-r10.md`（該檔以 R10 對話品質為主軸，非業主目標）

---

## 0. 事實基準（全部經 2026-09-01 查證，附出處；⛔ 未附出處者不得寫入本檔）

```text
知識庫
  active 知識                     922
  有 retrieval_representation       9   ← **1%**，其餘 913 筆每次檢索仍用 legacy question_summary
  有 embedding                    871   ← 51 筆 active 但無向量，檢索不到
  空 answer（面向進場錨點）         98
  （正對照：generation_metadata 本身 477/922 有資料 ⇒ 上述 9 非查詢假象）

測試資料
  test_scenarios                4,875   全 active
    有 expected_category        3,533   72%   可驗路由分類
    有 related_knowledge_ids       24  0.5%   ⛔ 幾乎無法驗檢索命中
    有 expected_answer              0    0%   ⛔ 無法驗答案正確性
    collection_id 非空              0    0%   ⛔ 連結全斷，跑不了批次
    來源  imported 2608／auto_generated 1035／user_question 982／manual 250
  凍結語料 corpus-20260810      37 案／107 重播輪，26 輪有期望答案（24%）
  holdout 2026Q3                已凍結（routing-disambiguation 產出）

歷史基準（⚠️ 母體為 test_scenarios 548 題，**非 production holdout**，⛔ 不得宣稱線上品質）
  60.2%  舊寬鬆尺，污染（run 288 舊 image）
  69.7%  548 題乾淨重批  ← scripts/audit/reports/regrade291-triage.md:3（2026-07-05）
  75.2%  雙票＋ASK_BAD 根因修後（僅記憶檔記載）
  ⛔ 62.8% 是錯的，全 repo/DB 查無來源（2026-09-01 獨立稽核；記憶檔已修正）
  最後一次回測 2026-07-06，距今 57 天

檢索管線（經獨立稽核 CONFIRMED）
  分數合成  base_retriever.py:585  `0.1×vector + 0.9×rerank`
  ⚠️ 條件：**只套在實際進 rerank 的候選**（RERANKER_INPUT_LIMIT=20、
     RERANKER_MIN_VECTOR_SIMILARITY=0.3、ENABLE_RERANKER 預設 true）
     未進 rerank 的列走 keyword／vector 分支，⛔ 不是 90/10
  keyword_boost  base_retriever.py:373，1.0–1.3 倍率
  客服回報型別   21/25 = 84% 知識題（docs/retrieval-recall-audit-20260822.md:59）
                 ⚠️ 母體僅 25 筆，且 S3 回報自 2026-07-29 零新增
```

---

## 1. 相關文件與資料在哪

```text
【規格】
主線 spec        .kiro/specs/conversational-routing-execution/
                   requirements.md（R1–R10）／design.md／tasks.md（57/64）
已封存           .kiro/specs/archive/retrieval-decision-layer/
                   HALTED.md 載明:已交付仍在跑的部分 ＋ 未開工的 P1/P2/P3
架構母圖         docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md
                   §0 三層責任分層（⚠️ §3 檢索引擎有 5 處與程式碼不符，見本檔 §4）
檢索盤查         docs/retrieval-recall-audit-20260822.md（84% 知識題的出處）
參數台帳         docs/retrieval-parameters.md

【程式碼】
分數合成         rag-orchestrator/services/base_retriever.py:522 `_finalize_scores`
知識檢索         rag-orchestrator/services/vendor_knowledge_retriever_v2.py
表示法契約       rag-orchestrator/services/retrieval_representation.py:122 `scoring_surface`
決策層           rag-orchestrator/services/decision_layer.py（DecisionConfig／facet_entry_eligible）
適用性把關       rag-orchestrator/routers/chat.py:1485 `_top1_relevance_gate`

【測試資料】
凍結語料         docs/backtest/corpus-20260810/（run2-head／run3-head 已在本機）
                 expected_answers.json（26 輪期望答案）
                 S3 正本 sha256 b9c690cf…（README 載取回方式）
holdout          .kiro/specs/routing-disambiguation/evidence/holdout-2026Q3-*
回測工具         rag-orchestrator/scripts/backtest/{freeze_measurement,decision_replay}.py
                 docs/backtest/corpus-20260810/replay_harness.py
歷史重批清單     scripts/audit/reports/regrade291-triage.md
DB               aichatbot_admin：knowledge_base／test_scenarios／test_collections
                 ／backtest_runs／usage_events

【稽核】
不變量           scripts/audit/check_invariants.sh（25 條）
baseline oracle  scripts/audit/baseline_oracle.py（集合式判準）
```

---

## 2. 階段任務

> ⚠️ **順序修正（重要）**：業主原排「先治病 → 再測試回測」。
> 本計畫把「量基準」插到治病之前——否則改完證明不了有沒有效（本分支已重演多次）。

### P0 建尺（前置，⛔ 不動任何產品行為）

```text
P0-1  修 collection 連結                                          我做
  目的  4,875 筆現成情境目前掛不到任何 collection ⇒ 跑不了批次
  步驟  ① 唯讀診斷:test_scenarios.collection_id 全 NULL 是資料被清、schema 改、還是從未接
        ② 依診斷結果提修法（若需 migration 則 additive）
        ③ 建立四個 collection 的歸屬規則（smoke／regression／full／edge_cases）
  出口  能以 collection 驅動一次批次跑，且 backtest_runs 產得出 pass_rate
  證據  診斷報告 ＋ 一次成功的批次 run id

P0-2  檢索命中 ground truth 標註（最小可用集 100 筆）            我做＋業主核判準
  目的  4,875 筆只有 24 筆有 related_knowledge_ids ⇒ 改了也不知道好壞
  步驟  ① 判準先寫死（什麼叫「該命中這筆」）並由業主核可
        ② 從 user_question 來源 982 筆真實問題挑 100 筆
        ③ 逐筆標「應命中知識 id」＋「是否該進面向」
        ④ 正負對照:必須含已知會過與已知會敗各數筆
  出口  100 筆標註凍結（含 sha256），且尺在 3 樣本下看得見已知病灶
  ⛔ 標註不得由實作方單獨完成

P0-3  知識庫覆蓋率盤查                                          我做，唯讀
  目的  量出「單一知識點覆蓋率不足」的實際分佈
  步驟  ① 913 筆缺 retrieval_representation 的清單與分型
        ② 51 筆 active 無 embedding 的成因
        ③ 98 筆空 answer 錨點分型（面向進場 vs 遺漏）
        ④ 每筆知識現有幾種可命中的問法（＝覆蓋率現況）
  出口  分型清單落檔，⛔ 不改任何知識內容
```

### P1 量基準

```text
P1-1  跑第一次大量回測                                          我做
  前置  P0-1、P0-2
  步驟  ① 先驗容器與 HEAD 一致（舊 image 會讓整輪翻盤）
        ② freeze_measurement 凍結判準／分母／雜訊標記／尺版本
        ③ 跑 regression（3,533 有 expected_category）＋ 100 筆命中標註集
  出口  今天的命中率與路由正確率各有數字與分母
  ⚠️ ⛔ 不與 69.7% 直接比較（母體與判準不同），只當參考

P1-2  錯誤分型                                                  我做
  步驟  把 P1-1 的失敗分成:召回不到／召回到但排序輸／路由錯／答案錯
  出口  各類數量與代表案例，成為 P2 的工作清單
```

### P2 治單一知識點覆蓋率

```text
P2-1  表示法覆蓋補齊（L1，**優先**）                            我做＋業主核
  理由  機制已接好（retrieval_representation.py:122 ＋ 三個消費端），
        只缺內容:9/922 ⇒ 913 筆待補。**不需新機制、不需新 spec**
  步驟  ① 依 P1-2 的錯誤清單排序，先補會錯的
        ② 逐筆產 reviewed declaration
        ③ 每批補完重跑 P1-1 的子集，報出命中率變化
  出口  覆蓋率由 1% 提升；每批都有「動了多少」的數字
  ⚠️ 知識生成必須理解實際對話流程，⛔ 不得把資料直接丟 LLM 生成

P2-2  一知識一問法（L2，變體表）                                ⚠️ 需業主裁
  現況  knowledge_variants 表**未實作**，其設計在已封存的 spec P2 3.4
  待裁  owner 歸屬（納入主線 spec／另立／沿用封存設計）
  ⛔ 在 P2-1 未證明成效前不啟動
```

### P3 補知識庫

```text
P3-1  依 P2 殘餘錯誤補知識內容                                  我做＋業主核
P3-2  51 筆無 embedding 處理
P3-3  98 筆空 answer 錨點依 P0-3 分型處置
```

### P4 上版

```text
P4-1  解 SEC-01（現行 OpenAI key 撤銷換新）                     業主執行
P4-2  解 SEC-02（AWS Access Key ID 在 public repo 歷史）        業主裁定
P4-3  PUB-01 揭露決策（462 筆未 push 含全部 specs 與稽核紀錄）   業主裁定
P4-4  部署（含 semantic-model 重建）                            業主執行
```

---

## 3. 硬 blocker（與 P0–P3 平行，不阻塞前面）

```text
SEC-01  現行 OpenAI key 曾明文進 transcript，**尚未撤銷**
SEC-02  現行 AWS Access Key ID 在 **public repo** 歷史（origin/main 祖先）
PUB-01  repo 是 PUBLIC；SECRET-SAFE ≠ PUBLICATION-SAFE
        ⇒ 462 筆未 push 內容是否該公開，需業主決定
```

---

## 4. 已知文件錯誤（照文件改碼會出事，⛔ 先修文件再引用）

```text
COMPLETE_CONVERSATION_ARCHITECTURE.md §3 有 5 處與程式碼不符：
  :433  業者隔離漏掉「vendor_ids 為空＝全業者共用」放行；運算子是 && 非 @>
  :434  角色隔離漏掉 NULL 放行與 all_users 通用放行
  :435  ⚠️ **業態過濾漏掉 b2b 嚴格分支**——b2b 是 `&& ['system_provider']` 且**無 IS NULL 放行**
        ⛔ 照文件給 b2b 補 IS NULL 會打穿刻意設計的隔離（記憶「勿改回」正是這條）
  :383  把仍在仲裁使用的 0.6 標成「已過時」（0.65 是檢索過濾門檻，兩個不同命題）
  :440  行號漂移；且主排序鍵是向量相似度，priority 只是次鍵

程式碼幽靈引用：
  chat.py:2624 註解引用「既有 append_turn 統一出口」——**全 repo 無此函式**
```

---

## 5. 明確不做

```text
⛔ 責任架構橫向擴張         R-29 已走通一條即停，⛔ 不接其餘 29 條
⛔ 在 P1 基準之前調任何門檻或對話規則
⛔ 動已封存的 retrieval-decision-layer（其 DecisionConfig 仍在生產運行，⛔ 勿刪）
⛔ 引用 62.8%
⛔ 拿 69.7%／75.2% 宣稱線上品質（母體非 production holdout）
⛔ 照 §4 的錯誤文件改程式碼
```

---

## 6. 每輪固定回報

```text
主線進度    階段（P0–P4）／任務編號／出口條件達成與否
遇到問題    具體卡點 ＋ 誰能解（我／業主裁決／外部條件）
優化了什麼  對照哪個指標、數字動了多少；⛔ 動不了就寫「無」
```
