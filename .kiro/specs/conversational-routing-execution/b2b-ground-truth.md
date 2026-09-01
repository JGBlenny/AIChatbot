# b2b 檢索：查證用的 ground truth（實查，非引用文件）

> 2026-09-01｜⚠️ 本檔是**判斷文件對錯的尺**，所有數字皆為當日實查
> ⛔ 本檔不引用任何文件的說法——文件的說法要拿本檔來驗，不是反過來

## 程式實際怎麼過濾（`services/vendor_knowledge_retriever_v2.py`，符號 `_vector_search`／`_keyword_search`）

```text
is_b2b_mode = (target_user in ['property_manager','system_admin']) or (mode == 'b2b')

b2b   business_types && {system_provider}                  ← 嚴格，**無 IS NULL 放行**
      target_user IS NULL OR target_user && {該角色}
b2c   business_types IS NULL OR business_types && 該業者業態
      target_user IS NULL OR target_user && {該角色, 'all_users'}

兩條路（vector／keyword）都額外寫死：
      category IS DISTINCT FROM '系統脈絡'
      category IS DISTINCT FROM '對話規則'
向量路徑另要求 embedding IS NOT NULL；詞面路徑另要求 keywords 非空
```

⚠️ **陷阱**（`base_retriever.py`，符號 `retrieve`）：
`similarity_threshold = similarity_threshold or self.default_similarity_threshold`
⇒ 傳 `0.0` 會被當 falsy **靜默換成 0.6**。要真的關掉門檻不能傳 0。

## ⚠️ 三個不同的「0.6 系」門檻——**⛔ 不是同一顆，⛔ 不可互相取代**

這是文件錯得最集中的一點（`COMPLETE_CONVERSATION_ARCHITECTURE.md:383` 兩處皆錯）。

```text
① KB_SIMILARITY_THRESHOLD          檢索過濾／Brain kb_search 同源
   程式 fallback  0.55（decision_layer.py，符號 kb_threshold）
   容器實際值     **0.65**
② knowledge_min = **0.6**          六 case 答題仲裁，**硬編碼、無 env、不可調**
   （decision_layer.py 符號 knowledge_min → KNOWLEDGE_MIN_THRESHOLD，
    刻意不開 env：開了會讓等價驗證失去對照意義）
③ default_similarity_threshold = **0.6**
   base_retriever 的 retrieve() 預設，呼叫端沒傳時用
```

⇒ ⛔ 「0.6 已過時、正確值是 0.65」**是錯的**：0.6 仍活在②③兩處，
   而 0.65 是①的部署值，是**另一顆常數**，不是 0.6 的後繼。

## 容器實際環境值（實查 `printenv`，非 compose 預設、非 .env 檔）

```text
KB_SIMILARITY_THRESHOLD      = 0.65    （程式 fallback 是 0.55）
FORM_TRIGGER_THRESHOLD       = 0.75    （面向進場＋表單觸發**同一顆**，未拆）
ENABLE_RERANKER              = true    ⚠️ 程式 fallback 是 false，compose 才是 true
RERANKER_INPUT_LIMIT         = 20
RERANKER_MIN_VECTOR_SIMILARITY = 0.3   （先砍候選，再取 top-20 進 rerank）
ENABLE_QUERY_REWRITE         = true
ENABLE_QUERY_REWRITE_B2B     = **false**  ⚠️ **b2b 不做查詢改寫**（2026-08-22 A/B 定案）
SEARCH_KB_ENABLED            = （未設，走程式預設 true）
USE_MOCK_JGB_API             = false   ⚠️ 與記憶檔「本機定為 true」不符
不變量 3（容器 image 與 HEAD 一致）= PASS
```

## 分數怎麼合成（`base_retriever.py`，符號 `_finalize_scores`）

```text
有 rerank_score       final = 0.1 × vector + 0.9 × rerank
沒有 rerank_score     final = min(1.0, max(vector, keyword) × keyword_boost)
⇒ keyword_boost **只在沒進 rerank 時生效**；KB 路徑幾乎都有 rerank
⚠️ 只有實際進 rerank 的候選（RERANKER_MIN_VECTOR_SIMILARITY=0.3 之上、取前 20）
   才走第一條公式

## b2b 的真實工作母體（DB 實查）

```text
適格母體（active，扣設定列 51、扣空 answer 錨點 98）        773
b2b 業者（property_manager）可見                          **285**   ← b2b 的分母
  來源      source=manual **285／285**（100%，⛔ 沒有一筆 loop 生成）
  vendor_ids 非空（業者專屬）                                 0
  categories 空                                            33   ← 面向進場對它們靜默失效
  keywords 空                                              21
  有 retrieval_representation                               6
b2b prospect 可見                                          18   （presales-kb）
b2b 看不到的                                              488
  其中 source=loop／target_user=tenant                     445
  ＝租客生活知識（社會住宅、租屋保險、包租代管差異、分租糾紛…）
  ⇒ 對「業者問 JGB 系統操作」本來就不該可見，⛔ 不計為 b2b 缺口
```

## 實際流量（`usage_events`，非內部事件）

```text
b2b / property_manager   1,321     ← 現役主力
b2b / (null)               258
b2c / tenant                21
b2b / prospect               6
```

## 契約（`docs/jgb2-chat-integration.md` §1，**已與程式對照一致**）

```text
業者 b2b   mode=b2b + target_user=property_manager   只走 JGB 系統知識（**不走 SOP**）
租客 b2c   mode=b2c + target_user=tenant             該業者 SOP ＋ 租客知識，比分擇優
售前       mode=b2b + target_user=prospect           售前顧問知識
```

⚠️ SOP 現況：vendor 2 有 250 筆、vendor 3 有 4 筆、**vendor 1 與 4 各 0 筆**。
b2b 不走 SOP ⇒ 知識庫是 b2b 唯一答案來源，⛔ 沒有「我沒量 SOP」的量測缺口。

## 已被裁決過、⛔ 不要重新發明的事

```text
docs/retrieval-recall-audit-20260822.md:82
  b2b 的 `business_types && {system_provider}` 嚴格過濾是**刻意的隔離機制，勿改**
同檔 :114
  「補 categories」的有效對象只有 b2b 可見那群（該檔記 34 筆，本日實查 **33 筆**）
  business_types 空的 75 筆補了也沒用——b2b 看不到
同檔
  keywords 空的 107 筆**業主定案不補**（keyword_boost 幾乎不生效，且是排序漂移根因）
同檔
  ⚠️ 補 categories 是**行為變更**：等於把知識移進一條繞過適用性把關的面向進場路徑
```

## CANON 已判定為「快照」的文件（⛔ 過時是預期，不是缺陷）

```text
docs/features/*_FEATURE.md（含 RERANKER_FEATURE.md）
docs/features/KNOWLEDGE_FORM_TRIGGER_IMPLEMENTATION.md
docs/research/account-conversational-facets-research.md
docs/backtest/assistant-report-regression.md／assistant-report-workflow.md
（2026-08-22 /canon-triage 兩輪逐份判定，帳本在 ~/.claude/canon/judgments/）
```
