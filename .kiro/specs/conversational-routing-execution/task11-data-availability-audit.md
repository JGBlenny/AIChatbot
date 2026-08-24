# 任務 11 前置：production 量測資料可用性稽核

> 2026-08-25｜語言 zh-TW｜**唯讀，只有 SELECT；未驅動任何 production 請求、未寫入任何一列**
> 授權範圍：業主 2026-08-25「只到 11.1 四條安全條件內的 production read-only measurement」

## 0. 結論（先講）

> **「先量現況」的第一個現況是：現行 production 量不到對話品質。**
> 11.3 的 `turns_p50/p90` 與 11.4 的三項判定指標，**在現有資料下皆不可計算**——
> 不是授權問題，是資料不存在。

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
⚠️ 近 30 天的實況：facet session 中 rows=1 者 294、rows=3 者 21、rows=2 者 3、rows=5 者 1
   ——樣本以單輪為主，任何「多輪品質」的 aggregate claim 都缺可判樣本
```

## 5. 提請裁示（互斥三選一，本檔不自行選）

```text
(a) 窄化 Task 11 → **telemetry baseline**（第 4 節可算項）＋ 明文記錄不可算項與盲點，然後收。
    優點：零 production 變更、立即可得、且「量不到」本身就是有價值的 baseline 事實。
    代價：11.3／11.4 的原指標維持未達成，11.6 的比較性結論（≥30 可判案例）無法成立。

(b) 先補埋點（turn_number 於診斷面向、scope=switch 的 exit 事件、可選的逐字留存）
    → 屬 **production 變更**，需另外授權；且 gate CLOSED 期間不上線 → **短期內產不出資料**。

(c) 以 branch e2e 自造樣本量測 → 那不是 production 現況，**會失去 baseline 的意義**。
```

⚠️ 依 Requirement 10.5 與業主的 claim ceiling，本輪**未**調整任何規則、routing、metadata，
也**未**因量測缺口順手補埋點。

## 6. 本檔**未**做

```text
❌ 未凍結量尺（11.2）——在確定要量什麼之前凍結沒有意義
❌ 未產出任何 baseline 數字作為結論（第 2 節為可用性佐證，非 baseline）
❌ 未新增 r10_ 前綴（本輪不驅動請求即不需要；要驅動時再補）
❌ 未做 11.4／11.5／11.6
```
