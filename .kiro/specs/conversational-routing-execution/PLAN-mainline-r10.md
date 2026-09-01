# 主線任務計畫：R10 面向對話品質可量測

> 狀態：**PROPOSED —— 等待業主批准**
> 主線 spec：`conversational-routing-execution`｜分支 `fix/retrieval-routing-stability`
> 依據：requirements.md R10、tasks.md §11、R9.3（五次翻盤教訓）

---

## 0. 為什麼卡住（一句話）

R10 要量四個對話品質指標，但**埋點裡沒有可判定的東西**：
`turn_number` 與 `decision_snapshot.user_turns` 無資料、無 transcript／user message／final answer
⇒ `judgeable N = 0` ⇒ 11.2／11.3／11.4／11.6 全部 NOT MEASURABLE。

⚠️ R10.5：**先量現況、建立基準，再談優化。⛔ 無基準不得調對話規則文字。**

---

## A. 可觀測性補齊（解除 NOT MEASURABLE）

```text
A1  盤點四個指標各自需要哪些欄位，逐項對照現有埋點缺什麼
    反問對題率      需 user message ＋ 面向反問文字
    前提衝突處理率  需 user message ＋ 首輪回應
    輪數分佈        需 turn_number／session 內輪序
    重複詢問率      需 每輪索取的 slot 名稱
A2  決定落點：usage_events／decision_snapshot／新表——⚠️ 先提案，⛔ 不自行決定
A3  additive migration ＋ writer 接線（僅新增，⛔ 不改既有列）
A4  覆蓋率驗收：面向對話輪次的埋點覆蓋率須達門檻（現況 decision_snapshot 54.8%、面向續輪 0%）
    ⛔ 覆蓋率不足時任何量測結論不成立
A5  隱私邊界：逐字稿含使用者輸入 ⇒ 存放位置與保留期限須業主裁定
```

**出口條件**：對任一面向對話 session，四個指標所需欄位皆可查得；抽 3 個真實 session 人工核對無缺漏。

---

## B. 評測資料建立（判準先於量測）

```text
B1  盤點既有可用資產（⛔ 不重造）
      凍結語料 corpus-20260810：37 份真實客服對話／107 輪×3，已在本機
      routing-disambiguation holdout 2026Q3：已凍結標註與量測
      test_scenarios 4,875 筆 ⚠️ 但 4 個 collection 全掛 0 筆 —— 連結疑似斷，B2 先查
B2  修復或重建 scenario→collection 連結（先判是資料問題還是 schema 問題）
B3  R10 專用評測集：從凍結語料挑出**面向對話輪次**，逐輪標註
      該輪使用者的實際訴求／面向反問是否對題／是否有已陳述前提被忽略／索取的 slot
    ⚠️ 判準先寫死再標註（先定標準再執行）；⛔ 標註不得由實作方單獨完成
B4  正負對照：評測集必須含「已知會過」與「已知會敗」各數筆
    ⛔ 尺看不見已知病灶即作廢（requirements.md 已載兩個實測病灶：續約帳單問成帳號狀態、
      「已經簽約了」被當成還能改）
```

**出口條件**：評測集凍結（含 sha256），且在 3 筆樣本上證明尺看得見那兩個已知病灶。

---

## C. 知識庫盤整（供 B3 標註與 D 歸因用）

```text
現況（2026-09-01 實查）
  knowledge_base 1,043 筆｜active 922｜有 embedding 871｜空答案錨點 98
  business_types：system_provider 373／NULL 308／full_service+property_management 241

C1  空答案錨點 98 筆分型：哪些是面向進場錨點、哪些是遺漏
C2  active 但無 embedding 的 51 筆（922−871）盤查：是否影響檢索母體
C3  面向 categories 與 required_slots 對照：供 11.5「required_slots 設計合理性」評估
⛔ 本階段只盤查與分型，⛔ 不改任何知識內容
```

---

## D. 量測基準（原 tasks 11.2／11.3／11.4／11.6）

```text
D1  freeze_measurement.py 凍結判準／分母／雜訊標記／尺版本（原 11.2）
D2  輪數分佈 turns_p50／turns_p90（原 11.3）
D3  三項需判定指標：反問對題率／前提衝突處理率／重複詢問率（原 11.4）
    ⚠️ 判定程序須可重複執行；⛔ 不得僅以「有回應」視為通過（R10.3）
D4  baseline 落檔並標註結論分級（原 11.6）
D5  11.5 required_slots 設計合理性評估
```

**出口條件**：四個指標各有數字與分母，且獨立重算一致。

---

## E. 優化（**基準之後才開始**）

```text
E1  依 D 的結果排序病灶，逐個立案
E2  每一刀都要能回答「這讓哪個指標動了多少」——動不了就不做
⛔ 在 D 完成前，⛔ 不得調整任何對話規則文字（R10.5）
```

---

## 明確不做（範圍外，⛔ 不得擴張）

```text
⛔ 責任架構橫向擴張：R-29 已走通一條即停，⛔ 不接 R-28／R-31／其餘 27 條
⛔ SOP vs Knowledge arbitration、Form Engine、API Engine、交易面向引擎（R8 已聲明）
⛔ 澄清分岔（brain 對 Route-R3 全判 stay，列研究項）
⛔ task 3.4：修法已 REFUTED，需業主另裁後才動
⛔ task 10.4：業主 2026-08-25 裁定 intentionally deferred
⛔ retrieval-decision-layer：**已封存**至 `.kiro/specs/archive/`（2026-09-01）。
   ⚠️ 它已交付且仍在跑的 `DecisionConfig`（R7.4 門檻唯一讀值點）與決策快照埋點（R8.3）
   **主線仍在使用**，⛔ 不得因封存而移除；其 P1/P2/P3（逃生門／變體表／省略補全／
   複合拆解／詞面通道）全部未開工，⛔ 不在本計畫內。
```

---

## 固定回報格式（每輪）

```text
主線進度    階段（A–E）／任務編號／出口條件達成與否
遇到問題    具體卡點 ＋ 誰能解（我／業主裁決／外部條件）
優化了什麼  對照哪個指標、數字動了多少；⛔ 動不了就寫「無」
```
