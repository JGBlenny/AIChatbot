# T1 batch-01 檢索 run1 結果（19 題真實使用者問句）

> 2026-09-01｜**DIAGNOSTIC**｜對照的是 `t1-batch01-hits.pre-run-draft.json`
> （sha256 `c2c315e9…`，**跑檢索之前**凍結的實作方初判）
> ⛔ **業主尚未確認命中真相** ⇒ 下列比率**不是收案證據**，只是診斷。

## 執行參數（凍結）

```text
容器      aichatbot-rag-orchestrator｜不變量 3 = PASS（image 與 HEAD 一致）
ENABLE_RERANKER = true｜RERANKER_INPUT_LIMIT = 20
入口      VendorKnowledgeRetrieverV2.retrieve_knowledge_hybrid（similarity_threshold=0.0）
情境      tenant → vendor_id=1 / mode=b2c        （依 test_scenarios 記錄的 request_mode）
          property_manager・prospect → vendor_id=0 / mode=b2b（chat.py:4808 的 JGB System）
          未標 target_user 者 → b2c 與 b2b **各跑一次**，取較佳
三輪      ① 濾後 top-10 ② 未濾 top-10 ③ 未濾 top-20（判斷是否在候選池內）
⚠️ USE_MOCK_JGB_API 容器實際值 = **false**，與記憶檔記載的「本機定為 true」不符（T1 不受影響，但要知道）
```

## 結果

```text
19 題
  有提案命中的         12
    濾後 top-1 命中      5    9537 9538 9974 10320 10323
    濾後 top-3 命中      6    ＋10243（名次 2）
    濾後完全沒回         6    9620 9645 9758 9994 10068 10089
  初判「疑似無覆蓋」的  7
    檢索回 0 筆          3    9596 9631 9900
    回了東西但非正解     4    7617 8149 10236 10314
零結果題數（濾後回 0 筆）＝ 6／19
```

## ⛔ 最重要的發現：6 個沒中裡有 4 個**不是檢索問題，是池的問題**

```text
9620 超商繳費代碼怎麼拿      應中 3411
9645 轉帳金額和帳單不一樣    應中 3416
9758 收到簽約邀請 email      應中 3442
9994 儲值金回充帳戶          應中 3417
```

這 4 筆在 b2c 的 **20 筆候選池裡完全不存在**。改走 b2b 池後——

```text
對照組（同一題、同一句、只換池）
  ts9620 → kb:3411 名次 **1**
  ts9645 → kb:3416 名次 **1**
  ts9758 → kb:3442 名次 **1**
  ts9994 → kb:3417 名次 **1**
反向對照（證明不是「b2b 什麼都找得到」）
  ts9537 → kb:3335 在 b2b **回 0 筆**（3335 業態＝full_service/property_management）
正對照   ts9537／ts9974／ts10320 在各自情境名次皆為 1 ⇒ 量測路徑是通的
```

**成因（已讀碼確認，非推測）**：`vendor_knowledge_retriever_v2.py:66-81`
b2c 的業態過濾是 `(business_types IS NULL OR business_types && 業者業態)`；
3411／3416／3442／3417 的 `business_types = {system_provider}`，非 NULL 也不相交
⇒ 任何 b2c 情境都**結構上**看不到它們。

⚠️ **資料自相矛盾**：3411／3416／3417 的 `target_user` 明寫 `{property_manager, tenant}`，
3442 更是 **只寫 `{tenant}`** ——宣告給租客看的知識，卻放在租客觸不到的池裡。

⛔ 這**不是**「b2b 池隔離是正常行為」那條的反例：那條講的是 b2b 只看 system_provider。
   這裡是反方向——b2c 看不到 system_provider，而有一批**宣告給租客**的知識被放在那裡。

## 這改變了什麼

```text
原以為  覆蓋率不足 ⇒ 要補 representation／補知識
實測    至少 4/19 是**知識已存在、排名第 1、但這個角色的會話拿不到**
⇒ P1-3 的錯誤分型要加第五類：**可見性錯配（pool/業態錯置）**
⇒ 這一類的修法是改 business_types（資料），不是改檢索或補知識
⚠️ 修之前要先確認產品意圖——這 4 筆是否**刻意**只給 b2b。⛔ 這是業主的產品裁決，不是我的。
```

## 仍待業主確認

```text
① 19 題的命中真相（confirmed_kb_id / NO_COVERAGE）——本檔比率全部依實作方初判
② 上述 4 筆的 business_types 是否為誤置
③ 7 題「疑似無覆蓋」是否確為知識缺口
```
