# Q1（封口）：entry source × applicability veto × early-return × authority source

> 2026-08-24｜語言 zh-TW｜discovery Q1 第二輪｜**唯讀盤查，未改任何程式**
> 讀值來源：`routers/chat.py` dispatcher（4132–4185）與各 handler

## Q1 主結論（業主 2026-08-24 修正措辭，取代第一輪的「authority 高低」）

> **同一個 top-1 Knowledge evidence，在成為 direct-answer evidence 前仍須通過
> applicability veto；但它攜帶的 Face Routing Hint 可以在該 veto 之前生效，
> 並提前結束 Knowledge 路徑。**
>
> 即：**Routing Hint 的生效條件比 answer evidence 更弱、更少受 applicability 約束。**

## 完整 entry topology（dispatcher 實際順序）

```text
Step 0    handle_form_session          表單會話 REVIEWING/EDITING
Step 0    handle_conversational_session 對話會話續跑          ← Face 進場①
Step 0    handle_collecting             表單收集中
Step 0.4  handle_trigger_facet          trigger_facet_key 直達 ← Face 進場②
Step 0.5  handle_image                  損傷圖改道             ← Face 進場③
Step 1.5  handle_conversational_entry   prospect 自由問答      ← Face 進場④
Step 2    handle_cache
Step 4    handle_retrieval ─ sop      → SOP 回應（**不產生 Face 進場**）
                          └ knowledge → 分類路由              ← Face 進場⑤
```

## 矩陣

| # | Entry source | Authority source（誰讓它生效） | Applicability veto | Early-return |
|---|---|---|---|---|
| ① | 對話會話續跑 | **既有 session state 存在** | **無**（僅引擎降級才退出）| 是 |
| ② | `trigger_facet_key` 直達 | **呼叫端傳入的參數** ＋ config 存在且 enabled | **無**——只檢查「key 找不找得到」，**不判這句話適不適用** | 是 |
| ③ | 損傷圖改道 | **Vision 模型對圖片**的 `is_damage` ＋ `confidence ≥ 0.6` | 僅信心門檻；**判的是圖片不是問句**；且**直接跳過 SOP 檢索** | 是 |
| ④ | prospect 自由問答 | **`target_user == 'prospect'`**（`topic_scope.mode='all'`）| **無** | 是 |
| ⑤ | 分類路由（knowledge）| **KB 的 categories** ＋ `similarity ≥ form_trigger_threshold` | **無生效中者**（v1 gate 已 REFUTED；`_preentry_routable` 旗標預設 false）| 是 |
| — | direct answer（同一筆 KB）| 同上檢索 | **`_top1_relevance_gate`：LLM 判適用性，b2b fail-closed** | — |

## 這張表回答了業主提的分岔

問題是：現在發現的是 `Knowledge-only asymmetry`，還是整個 routing architecture
**對不同 entry source 使用不同 authority standards**？

> **答案是後者。** 五個 Face 進場來源，各自的 authority source 完全不同
> （session 狀態／呼叫端參數／圖片辨識／角色欄位／KB 分類字串），
> 且**沒有任何一個共用的 applicability 契約**；
> 五者全部 early-return，其中**四個完全沒有 applicability veto**。

⚠️ 對照之下，**唯一存在的 applicability veto（`_top1_relevance_gate`）只掛在 answer path**。

## 制度性發現（保留）

```text
Applicability evidence available ≠ applicability evidence authorized for routing.
```

與前案的 `answer evidence available ≠ answer evidence used` 同型：
系統已有元件會說「這東西可能不適用」，但它們**在不同時間點、管不同 output、
沒有共同 authority contract**，而 Routing Hint 可以在其中一些 veto 之前
造成**不可逆的 Face entry**（early-return）。

## 對三個假說的影響（**仍不選 winner**）

- **H3**（Face applicability contract 不完整）：矩陣顯示**不只 Face 契約缺**，
  而是**五個 entry source 沒有共同契約**——H3 若只補 Face 側，
  無法解釋②③④的 authority 來源根本不在 Face。
- **H1**（KB Hint overloading）：只解釋⑤，**解釋不了①②③④**。
- **H2**（缺 first-class query semantics）：②③的 authority 甚至**不看 query**
  （參數／圖片），故 H2 也非全域答案。

⚠️ **三者皆無法單獨解釋整張矩陣**——這是本輪最重要的負面結果。

## 尚未查（Q2 第二組，不得先當已知）

```text
□ brain `scope=stay|switch` 的契約語義／輸入／消費者／時機
   ⚠️ 必須先確認它是「此 query 不適用於本 Face」還是「已在 Face 內、現在該切話題」
   ——兩者相近但 architecture implication 不同；若依賴進場後才存在的 state，
     就不能直接上提為 pre-entry authority
□ `_top1_relevance_gate` 的實際產品作用：適用 mode／fail 行為／prompt 輸入／
   回 false 的效果／歷史攔截率／誤殺率／production 觸發頻率
   ⚠️ 若觸發率極低或大量錯殺，不得因「位置看起來對」就升格為 authority 候選
```
