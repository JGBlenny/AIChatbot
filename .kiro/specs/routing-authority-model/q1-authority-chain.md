# Q1：Routing Hint 現在實際擁有多少 authority？（production chain 實查）

> 2026-08-24｜語言 zh-TW｜discovery Q1｜**唯讀盤查，未改任何程式**
> 讀值來源：`routers/chat.py`、`services/decision_layer.py`、`services/conversational_config.py`

## 結論（先講）

> **Face Routing Hint 的 authority **高於** 同一筆知識的答題 authority。**
> 同一筆 top-1 知識，若走**答題**路徑要先過 LLM 適用性把關（b2b **fail-closed**）；
> 若走 **Face 進場**路徑則**完全不經該把關**——進場成功即 `return`，
> 適用性把關與錨點防呆**都在下方、永不執行**。

## 實查的 authority chain

```text
① 檢索          retrieve_knowledge_hybrid(top_k=5, similarity_threshold=kb_threshold)
                 決定者：vector + reranker｜依據：answer similarity｜可否否決：—

② 仲裁          decide_arbitration(sop_score, knowledge_score, …)   decision_layer.py:67
                 決定者：決定性比分規則｜依據：分數與門檻（sop_min／knowledge_min／score_gap）
                 → decision['type'] ∈ {sop, knowledge, …}

③ 面向進場      _diagnosis_config_for_knowledge(top1)              chat.py:1195
                 ├ facet_entry_eligible：similarity ≥ form_trigger_threshold
                 ├ _knowledge_category(top1)：categories 多值優先，否則 category
                 ├ config_for_category：by_category 索引（topic_scope.mode=='category' 且 enabled）
                 ├ instance gate（v1 candidate）：**REFUTED，manifest=failed → 恆不生效**
                 └ _preentry_routable：env `PREENTRY_ROUTABILITY_GATE` **預設 false** → 恆放行
                 決定者：**KB 的 categories**｜依據：**answer similarity ＋ 分類字串命中**
                 可否否決：**目前無任何生效中的否決者**

    ⬇ 進場成功 → `return _diag_resp`  ←★ 以下節點永不執行 ★

④ 錨點防呆      _drop_empty_answer_rows                            chat.py:1233
⑤ 適用性把關    _top1_relevance_gate(question, list, b2b)          chat.py:1244
                 決定者：**LLM**｜依據：問題 vs 知識標題＋內容節錄
                 b2b **fail-closed**（LLM 失敗＝不適用，續判次筆）；b2c fail-open
                 註記逐字：「reranker 高分錯位直答比查無更糟」
```

## 這條 chain 的三個 authority 事實

**F1｜同一筆知識，兩條路徑的把關強度不對稱。**
答題路徑有 LLM 適用性把關可否決；**Face 進場路徑沒有任何生效中的否決者**。
系統已經承認「reranker 高分 ≠ 這筆知識適用」（把關存在的理由），
但該承認**只作用於答題，不作用於 routing**。

**F2｜Hint 的 authority 實質等於「answer similarity ＋ 分類字串命中」。**
`facet_entry_eligible` 讀的是 similarity；`config_for_category` 讀的是 categories 字串。
兩者都源自**同一列 answer-evidence KB**——
與 v1 前提 **P7（另一個 similarity-based representation 不構成新 authority）** 直接相關。

**F3｜兩個既有 gate 目前都不在線。**
`instance gate`（v1）已 REFUTED、`manifest.holdout=failed` → 恆不生效；
`_preentry_routable` 旗標**預設 false** → 恆放行。
故**今日 Face 進場實際上是無否決者的**。

## 對三組探針的解釋力（初步，非結論）

```text
T-1 signal 正確、authority 不足   → 與 F3 一致：即使判對，也沒有生效中的否決通道
T-2 authority 足夠、signal 不足   → 顯示「否決通道存在」不等於「有依據可否決」
T-3 signal 本身錯誤              → 與 F2 一致：字面規則與 similarity 皆非 applicability 的語義來源
```

## 對 H1／H2／H3 的初步指向（**尚不足以選 winner**）

- **H1**：F2 支持「authority 來自 answer-evidence row」的描述**成立**，
  但**不證明**把 Hint 搬離該 row 就會產生新 authority（P7 仍在）。
- **H2**：F1 顯示系統已有一個**以 query 為輸入**的適用性判斷（LLM 把關），
  但它是**非決定性**且只服務答題——這是 H2 的**部分證據**，非證成。
- **H3**：F3 顯示 Face 側目前沒有可執行的 applicability 契約，
  與 H3 描述一致；但**同樣無法排除** H1／H2。

## Q1 尚未完成的部分

```text
□ SOP 路徑（decision['type']=='sop'）是否也有 Face 進場？其把關為何？
□ 表單／API 觸發路徑（form_fill／api_call）與 Face 進場的優先序
□ brain／session 既有 scope 判斷（conversational_step 的 scope=stay|switch）
   ——它是**面向內**的否決者，可否上提為進場前 authority？（與 Q2 直接相關）
□ `_top1_relevance_gate` 的實測攔截率與 b2b fail-closed 的實際觸發頻率
```

⚠️ 以上四項**未查**，不得先當成已知。
