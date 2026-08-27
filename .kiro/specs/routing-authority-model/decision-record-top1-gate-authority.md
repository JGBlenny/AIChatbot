# 決策稿：`_top1_relevance_gate` 的 authority 射程

> 2026-08-27｜語言 zh-TW｜**本檔不含任何實作、未執行任何付費測試**
> 觸發事件：P2.5 canary 在 production 等價語料上被該 gate 攔截。
> 待裁決者：產品決策方。工程端**不代填**。

## 一、先固定狀態（避免被讀成 delegation regression）

```text
P2.5  **NOT_VALIDATED**：production 等價語料在 `_top1_relevance_gate` 被攔截，
      **尚未進入** responsibility-routing vertical slice。
P3    證明「**一旦進入**該 slice，mini ＋ strict schema ＋ responsibility delegation 可以成立」（3/3）。
P2.5  證明「目前 production entry path **不保證**能讓它進去」。
⇒ 這**不是** delegation regression；兩者證的是不同命題。
```

實測日誌（2026-08-27，本機 stack ＋ 真 production JGB API ＋ 真 brain）：

```text
🛡️ [適用性把關] top1「點退帳單金額計算 押金結算」判不適用
   （sim=0.740｜NO; 知識內容未提供查詢帳單金額的具體方法或步驟。）→ 次筆晉位
   ❌ 知識庫沒有找到相關知識（閾值: 0.55）
```

該筆 top1 的 `categories` 含 **`條件診斷：帳單`**——正是 vertical slice 的進場面向。
gate 否決「直接回答」的同時，**連帶消滅了它攜帶的 Face nomination**。

## 二、核心問題（這才是要裁的，不是「怎麼繞過 gate」）

> **`_top1_relevance_gate` 的 authority，原本是否就應該同時支配
> direct answer 與 Face nomination？**

```text
現在：
  retrieval top1 → _top1_relevance_gate → 否決 → knowledge 消失 → **Face nomination 也一起消失**

方案 A：
  retrieval top1
  ├─ Direct-answer applicability → 決定「這篇知識能不能直接回答」
  └─ Face nomination evidence    → category 只能 **nominate candidate**
                                   → 再過 pre-entry responsibility applicability
                                   → **stay 才 commit**
```

一句話：

> **「這篇知識不足以直接回答問題」不等於「它提供的 Face routing hint 也沒有資格被考慮」。**

這對應本專案已建立的三層分離：`Entry nomination ≠ Face responsibility ≠ Execution／direct answer`。

## 三、三案比較

| 方案 | 做法 | 主要風險 | 最少需要的證據 |
|---|---|---|---|
| **A. 分離兩種 authority** | gate 否決 direct answer 時，不同步消滅帶 Face category 的 nomination；Face 另走 responsibility applicability | 可能增加誤進 Face；**必須先定義** direct-answer applicability 與 Face applicability 的權限順序 | 已知誤殺案例 ＋ 既有 pre-entry responsibility evidence；再做 deterministic routing regression |
| **B. 先量 gate** | 不改 production 行為，建立真語料標註集，量 false-kill／false-pass | 延後 rollout；**且 ≥30 judgeable 才有 aggregate rate** | ≥30 judgeable production-like cases，人工標「direct answer 可答否／Face 是否應候選」 |
| **C. Stage-1 暫停** | 不處理 gate，維持 CLOSED | 最安全，但已完成的 routing implementation 無法 rollout | 不需新證據；接受功能停在 pre-production |

## 四、A 的正確形狀（**寫死，防止被實作成寬版**）

```text
✅ 正確：
   top1 被 direct-answer gate 否決
   → 不准直接回答                         ✅ 維持
   → category 保留為 **candidate evidence**
   → candidate **仍須**通過 pre-entry responsibility applicability
   → **stay 才 commit**

❌ 錯誤（太寬，不得實作）：
   有 Face category → 無條件進 Face
```

兩者風險差距很大：後者等於把 gate 的否決整個作廢，並讓 category 直接取得 commit 權
——那正是 `routing-authority-model` 三次 REFUTED 的同一個錯（similarity／category 重編碼冒充 authority）。

## 五、既有數字與其證據身分（**不得只引百分比**）

來源：`q2-gate-discrimination.md`（2026-08-24，offline replay）
因果鏈：**pairs freeze（`9f4929b586d29cbc`）→ blind labels freeze（`95fae69d07f090ca`）→ 首次 gate 執行**，順序未顛倒。

```text
分母 31（33 判定 − 2 UNDECIDABLE）
TP 9 ｜ TN 15 ｜ **FP 0（放行錯位一筆都沒有）** ｜ **FN 7（誤殺）**
agreement 24/31 = 77%｜precision 9/9 = 100%｜recall 9/16 = 56%
```

⚠️ **證據身分**：所謂「44% 誤殺」＝ **7/16**，分母是「人判適用」的子集，**n=16 < 30**。

> 在既有已標註樣本中觀察到顯著 false-kill，**足以證明 gate 可誤殺**；
> **不足以估計真實母體誤殺率**。任何以「44%」當 production rate 的推論皆不成立。

另一項不可略過的對照（同檔）：要用單一 similarity 門檻達到同樣的零放行錯位，
門檻須 > 0.945，屆時適用知識只剩 **1/16** 通過——
**gate 有資訊價值，問題在它的 authority 射程，不在它該不該存在。**

## 六、今天這輪的自我否證（必須寫進 regression harness）

```text
我用「直接呼叫 retrieve_knowledge_hybrid → _diagnosis_config_for_knowledge」的探針
得到 sim=0.947、三跳、commit contract_closeout，並據此一度判定「路由正常」。
**那是複本，不是 production routing path**——它繞過 `_top1_relevance_gate`。
```

⇒ 該探針只能證明「**候選資料與 responsibility chain 存在**」，
**不能**證明「production 可達」。

**永久規約**：任何宣稱 production 路由行為的測試，其驅動點必須包含
`_top1_relevance_gate`；繞過它的探針一律標記為 `NOT_PRODUCTION_PATH`，
其綠燈不得作為可達性證據。（此條應納入 routing regression harness，防止複本假綠再現。）

## 七、待裁決事項

```text
① `_top1_relevance_gate` 的 authority 是否應同時支配 direct answer 與 Face nomination？
② 若否（＝採 A）：兩種 applicability 的**權限順序**如何定義？
   （direct-answer 否決是否構成 Face nomination 的否決前提？）
③ 若選 B：誰負責標註、標註準則為何、判準凍結在誰手上？
④ 若選 C：Stage-1 停在 pre-production 的期限與再評估條件？
```

⚠️ 工程端不得代填 ①②——那正是本 spec `BLOCKED_BY_EXTERNAL_DECISION` 的原因。
