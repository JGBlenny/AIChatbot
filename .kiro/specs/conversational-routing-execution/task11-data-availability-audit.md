# 任務 11：observability-blocked report
# （production telemetry inventory ／ 原定的 dialogue-quality baseline 已證明不可量測）

> 2026-08-25｜語言 zh-TW｜**唯讀，只有 SELECT；未驅動任何 production 請求、未寫入任何一列**
> 授權範圍：業主 2026-08-25「只到 11.1 四條安全條件內的 production read-only measurement」

## 0. 裁定與結論（業主 2026-08-25）

> **Task 11 原定的 production dialogue-quality baseline，
> 已被證明在現有 telemetry contract 下不可量測。**
> 可以完成的是 **production telemetry baseline**；**不得**把它偽裝成 dialogue-quality baseline。

```text
Task 11 outcome = **BLOCKED_BY_OBSERVABILITY**
```

⚠️ 這**不是** `INSUFFICIENT_EVIDENCE`（那表示資料存在、只是量不夠），
也**不是** `FAILED`（沒有跑出「品質很差」或「樣本不足」）。
本輪證明的是 **measurement contract 與 production instrumentation 不相容**：
至少兩類指標的**觀測欄位根本不存在**。

### 逐項狀態

```text
11.1 production read-only safety preconditions   **SATISFIED**
11.2 quality ruler freeze                        **NOT PERFORMED / NOT APPLICABLE**
     reason: required observables unavailable；在確立可量測性之前凍結量尺沒有意義
11.3 turn-distribution metrics                   **NOT MEASURABLE AS SPECIFIED**
     turn_number：diagnostic 側無任何資料｜decision_snapshot.user_turns：亦無資料
     僅有 facet-row-count-per-session 作為 proxy，**SHALL NOT** 改標為 conversation turns
11.4 dialogue-quality judgments                  **NOT MEASURABLE**
     無 transcript／user message／final answer 材料 → **judgeable N = 0**
11.5 required_slots 設計合理性                    **NOT STARTED**（不需 production 資料，未在本輪範圍）
11.6 ≥30 judgeable production cases              **PRECONDITION UNSATISFIED**
```

## 1. 四條安全條件的現況（11.1）

```text
① session_id 內部前綴   本輪**未驅動任何請求** → 不需要 r10_ 前綴即無污染風險
                        （若日後要驅動 production 流量，仍須先補 _SMOKE_PREFIXES）
② usage_events 不清     ✅ 未做任何刪除
③ form_sessions 依 prefix 清除  本輪未建立任何 session → 無需清除
④ 業務資料零寫入        ✅ **零寫入**：全程僅 SELECT，未觸及任何 execute_endpoint 面向
```

⚠️ 因此本輪的 production 存取風險面**低於** 11.1 原本設想的情境（原情境假設要驅動請求）。

## 2. 可用資料（`aichatbot_admin.usage_events`）

```text
列數      5,948（2026-07-07 ～ 2026-08-22）｜internal 4,414／external 1,534
facet_key 20 個面向有列；近 30 天非 internal 且有 facet 的 session＝**317**
facet_event   enter 1368／stay 1159／exit_degraded 84／exit_user_cancel 1
routing_verdict（decision_snapshot）
          enter_facet 1094／direct_answer 715／stay_facet_answer 641／
          stay_facet_ask 415／fallback 206／degrade_knowledge 77／
          stay_facet 25／exit_facet 2／degrade_honest 1／(null) 502
processing_path（近 30 天非 internal）
          conversational 507／param_answer 352／(null) 262／
          no_knowledge_found 131／knowledge_form 20／knowledge 6
```

## 3. **不可用**：三個硬缺口

### 3.1 `turn_number` 全表 **0 列非空** → 11.3 的 `turns_p50/p90` 不可算

```text
埋點現況  set_facet(turn_number=…) **只在交易面向**（_tx，宣告 execute_endpoint）呼叫；
          chat.py 的分類進場只帶 facet_key，不帶 turn_number
資料現況  usage_events.turn_number 非空列數 = **0**
替代欄位  decision_snapshot->>'user_turns' 非空列數 = **0**（同一個原因）
```

⚠️ 任務 11.3 寫「無須新增埋點」——**該前提不成立**。

### 3.2 **沒有任何對話逐字稿** → 11.4 的三項判定指標無材料

```text
chat_history          0 列
conversation_logs     0 列
unclear_questions     0 列
usage_events          只有 message_len，**無** message／answer 欄位
```

⇒ `on_target_ask_rate`（反問是否對題）、`premise_honored_rate`、
`grounding_utilization_rate` 三者**都需要看見問句與回答文字**，現況一句都取不到。

### 3.3 `scope=switch` 的退出**不產生 facet_event** → 該現象在 production 不可見

```text
現有 exit 事件只有 exit_degraded（84）與 exit_user_cancel（1）
引擎在 scope=switch 時走 `_close(session_id)` 後 return None，**未埋 exit 事件**
```

⇒ `face-exit-before-grounding` 那條線查到的現象，**無法**從 production 統計其發生率。
（本檔只記錄觀測盲點，**不**提修法——補埋點是 production 變更。）

## 4. 在現有資料下**可以**產出的 baseline（若採窄化路線）

```text
✅ 面向進場量與分布（per facet，非 internal，近 30 天）
✅ routing_verdict 分布（enter／stay／exit／fallback／degrade 各佔比）
✅ facet_event 分布，並標註 3.3 的盲點
✅ 每 session 的 facet 列數分布——**turns 的 proxy**（一請求一列；
   須標為 proxy，且不得改稱 turns_p50/p90）
✅ processing_path 分布
⚠️ **指標名稱：`facet_event_rows_per_session`**（近 30 天）rows=1:294／rows=3:21／rows=2:3／rows=5:1
   ⚠️ **只能說**「facet telemetry 以每 session 單列為主」；
   **不得**推論「production conversation 以單輪為主」——目前沒有可靠的 turn observable 支持後者。
```

## 4.4 正式缺口登記：OBS-1／OBS-2／OBS-3（**Task 11 的產物**）

```text
OBS-1  diagnostic conversational turns lack a reliable turn counter
       缺在哪：set_facet(turn_number=…) 只在交易面向呼叫；分類進場只帶 facet_key
       證據：usage_events.turn_number 非空 0 列；decision_snapshot->>'user_turns' 非空 0 列
       → **blocks 11.3**

OBS-2  scope=switch exits lack an observable facet lifecycle event
       缺在哪：engine 於 scope=switch 走 `_close(session_id)` 後 return None，未發 facet_event
       證據：現有 exit 事件只有 exit_degraded(84)／exit_user_cancel(1)
       → **blocks scope-exit baseline**

OBS-3  semantic quality metrics lack judgeable user/assistant evidence
       缺在哪：usage_events 僅有 message_len；chat_history／conversation_logs／
               unclear_questions 皆 0 列
       → **blocks 11.4 / 11.6**
```

### ⚠️ 責任邊界：**Task 11 指出要補哪裡，不負責把資料補出來**

```text
✅ 留在 Task 11    缺口定義（OBS-1/2/3）、缺在哪個 execution point、各自阻塞哪個 requirement
❌ 不屬 Task 11    新增 facet_turn event／新增 exit_scope_switch event／
                   決定是否保存 transcript／retention・privacy 處置
                   ——那些是**新的 production observability design**
```

⚠️ 這與剛處理完的 `skip_refine` 是同一種病：把 measurement 與 instrumentation design
塞進同一格。**不重蹈。** Task 11 到 `BLOCKED_BY_OBSERVABILITY` 為止即 STOP。

```text
Conversational Observability（**另開的線，尚未開**）
        │  provides required observables
        ▼
Task 11 resumes → freeze ruler → collect judgeable production sample → establish baseline
```

## 4.5 三個發現各自的 claim ceiling（**分開，不得互相加碼**）

```text
F1 turn observables 缺席
   ✅ 可說：11.3 指定的 turns_p50/p90 **無法從 production 現有資料計算**
   ❌ 不可說：由 facet rows/session 回推 turns；不可把 proxy 改名為 turns

F2 無逐字內容
   ✅ 可說：反問對題率／前提衝突處理率／grounding utilization **structurally unjudgeable**，
           **judgeable N = 0**（不是「<30」——資料契約上根本無法形成判讀單位）
   ❌ 不可說：品質好或差

F3 scope=switch 無 exit telemetry
   ✅ 可說：**若**發生此路徑，現有 `facet_event` taxonomy 無法直接統計它
   ❌ 不可說：production 其實常常發生 face-exit，只是我們看不到
```

## 5. 決策紀錄（業主已裁：採 (a)）

```text
(a) **採用**：窄化為 telemetry inventory／observability baseline ＋ 明文記錄不可算項與盲點。
(b) 排除：補埋點在 gate CLOSED 下無法上 production → 只會產生「未部署 instrumentation 存貨」，
    不會完成 Task 11；且「逐字留存」牽涉比一般 telemetry 更大的資料治理問題，
    **不得**當成 Task 11 的小修補順手決定。
(c) 排除：branch 自造樣本可測 evaluator／harness，但回答不了「production 現況如何」；
    拿 synthetic cases 補滿 30 只會製造**假 baseline**。
```

### 若未來要開 observability 工作線，題目應為（本輪**不偷做**，且**不掛在 Task 11 底下**）

> **為了讓 production conversational-quality baseline 可重複量測，
> 最小必要 telemetry contract 是什麼？**

該線才負責判：turn lifecycle 記在哪／`scope=switch` exit 記在哪／grounding utilization
可用哪些結構化欄位／哪些指標真的需要 user・assistant content／retention・privacy 怎麼處理／
哪些 instrumentation 能先做、哪些涉及 production release。

⚠️ 這樣即使未來決定「不保存逐字稿，只量結構化 grounding 指標」，
也**不會**是在 Task 11 裡偷偷改掉原本的 measurement contract。

⚠️ 依 Requirement 10.5 與業主的 claim ceiling，本輪**未**調整任何規則、routing、metadata，
也**未**因量測缺口順手補埋點。

## 5.5 本輪最根本的結果

> **目前 production 不具備驗證「多輪對話品質是否改善」所需的觀測面。**

這解釋了為什麼 C4b 與 face-exit 都只能自建專用 evidence harness——
但**反過來不成立**：那些 harness **不得**用來宣稱 production aggregate quality。

## 6. 本檔**未**做

```text
❌ 未凍結量尺（11.2）——在確定要量什麼之前凍結沒有意義
❌ 未產出任何 baseline 數字作為結論（第 2 節為可用性佐證，非 baseline）
❌ 未新增 r10_ 前綴（本輪不驅動請求即不需要；要驅動時再補）
❌ 未做 11.4／11.5／11.6
❌ **未設計、未實作任何埋點**——OBS-1/2/3 只登記缺口，補法屬另一條 observability 線
```
