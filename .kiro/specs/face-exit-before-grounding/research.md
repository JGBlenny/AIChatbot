# face-exit-before-grounding — Research（evidence baseline ＋ 初步 control-flow tracing）

> 2026-08-25｜語言 zh-TW｜**未呼叫任何 OpenAI API**（本檔全部為讀碼與 DB 讀取）
> 本檔是 R1–R4 的工作底稿；**不含 R5 裁決**。下列 F-x 為**初步發現**，不是結論。

## 1. Evidence baseline（自 C4b 移轉，provenance-only）

```text
案例       c4b-diag-01：「幫我查點退帳單金額」→「900003」（fixture 900003，total 7500）
觀測       🎯 trigger_facet_key 'bill_diagnosis' 命中 → 直達面向
           🔀 brain 判定離題(scope=switch) → 關會話、重路由當前訊息
           （落回檢索 → 分類路由再進一次面向）
           🔀 brain 判定離題(scope=switch) → 引擎降級
           → 通用兜底文案（intent_type=None、action_type=direct_answer）
正式分類   face_exit_before_grounding（`conversational-routing-execution` 6.3 diagnostic taxonomy）
原始證據   ../conversational-routing-execution/evidence/c4b-diag01-diagnostic-replay-stdout.log
           ../conversational-routing-execution/evidence/c4b-diag01-diagnostic-replay.json
```

```text
SUPPORTED       brain 的 scope／stay-switch 行為是直接 mechanism
SUPPORTED       trigger_facet_key 不是充分原因——分類路由進場同樣被退出
NOT ESTABLISHED 為什麼 brain 會判 switch     ← 本 spec 的工作面
```

## 2. R2 初步 tracing：producer → inputs → consumer

### 2.1 producer：`scope` 由 **LLM 產生**，不是程式判定

```text
services/llm_answer_optimizer.py  conversational_step()
  system_prompt = f"{system_context_md}\n\n{rules_text}{faces_note}{schema_note}{tool_note}"
  user_prompt   = 【已知欄位】/【asked_count】/【已給過推薦】/
                  【已鎖定資料】(grounding_note)/【最近對話】/【使用者最新訊息】
  model=PRESALES_SYNTH_MODEL(gpt-4o)  temperature=ADVISOR_TEMP(0.4)  max_tokens=400
  response_format=json_object
  → 正規化：data['scope'] = 'switch' if data.get('scope') == 'switch' else 'stay'
```

⇒ **`scope` 的語義完全由 `rules_text`（persona 規則）指示**；程式只做越界正規化。

### 2.2 inputs：`rules_text` 來自 DB 的「對話規則」列

```text
services/conversational_engine.py  prepare()
  rules_text = await self._load_rules(db_pool, config.persona_role)   # 取不到 → return None 降級
  system_md  = await self._get_system_context(db_pool, state.face or _domain_key(config))
  faces      = _domain_faces(db_pool, config)
```

### 2.3 consumer：引擎**直接關會話**

```text
services/conversational_engine.py
  if step.get("scope") == "switch":
      print("🔀 [conversational] brain 判定離題(scope=switch) → 關會話、重路由當前訊息")
      await self._close(session_id)
      return None
```

⇒ consumer 對 `switch` **沒有任何條件**：不看是否為進場輪、不看 entry 是誰決定的、
不看是否已有 grounding。回 `None` 後由 `chat.py` 落回一般流程重路由。

---

## F-1（初步）：producer 的 inputs 裡**沒有** entry 這件事

`conversational_step()` 的 system／user prompt 皆**不含**任何「本會話是被明確指定進入
某 Face」的敘述——沒有 entry 來源、沒有 entry authority、沒有「這是進場第一輪」。
brain 在 `asked_count=0`、`collected={}`、無 dialog、無 grounding_note 的空狀態下，
**只憑 query 對 persona 規則**做 stay/switch 判定。

⚠️ 這是 R3 contract map 的關鍵一格：**entry 的存在本身不在 scope 判定的輸入集合裡**。

## F-2（初步）：兩個 Face 的規則**都**把本 query 判給對方

實查測試庫 `knowledge_base`（`category='對話規則'`）：

```text
pm_bill_diagnosis（id 4252）
  【本輪範疇 scope】是帳單操作可否/原因相關、或在回答你剛問的問題 → scope="stay"。
  **帳單金額組成**/看不到帳單（帳單異常）、繳費入帳（繳費金流排障）、
  其他領域完整新問題 → scope="switch"。不確定 → stay 並澄清。

pm_billing_anomaly（id 3916）
  【本輪範疇 scope】是帳單內容/顯示相關、或在回答你剛問的 → stay。
  **封存/點退帳單處理**、其他領域完整新問題 → scope="switch"。不確定 → stay 並澄清。
```

query「幫我查**點退**帳單**金額**」同時命中兩條 switch 條款：

```text
對 bill_diagnosis   → 「金額組成」→ switch（規則要它交給帳單異常）
對 billing_anomaly  → 「點退帳單處理」→ switch（規則要它交出去）
```

⇒ **brain 沒有違反規則；它嚴格照著 authoritative rules 走。**
⇒ 目前證據指向的不是「brain 判錯」，而是**責任歸屬在規則層面存在缺口**：
   兩個 Face 的規則各自把這句話推給對方。

## F-3（初步）：core question 的前提需要重新查證

Core question 假定該 query「產品上屬於 `bill_diagnosis`」。目前唯一把它綁到
`bill_diagnosis` 的 artifact 是 C4a case set 的 `execution_face` 標籤，
而該檔**自己明文**：

> `execution_face` 是 **test execution context**，不是 routing ownership label；
> **C4a case inclusion SHALL NOT be cited as evidence of query→Face routing ownership.**

⇒ 前提「產品上屬於該 Face」**尚未由任何 production artifact 支持**。
⇒ 這不推翻 F-2 的觀測，但會改變 R5 分流的形狀（見下）。

---

## 3. 對 R5 分流的影響（**業主 2026-08-25 已裁：新增第五類**）

R5 目前只允許四種結論。若 F-2／F-3 在後續查證後成立，實際形狀可能是：

```text
兩套 contract **並非**各自主張 ownership 然後衝突，
而是**兩者都主動棄權**——responsibility gap，不是 authority conflict。
```

此形狀與四種既有結論的對應並不乾淨：

```text
IMPLEMENTATION_DEFECT_CONFIRMED   ✗ 規則載對、brain 照做、consumer 照契約關會話
CONTRACT_DEFECT_CONFIRMED         ？ 端看「兩份規則互推」算不算 contract 之間不一致；
                                     但**不得**用它偷渡「應該改成哪一套產品規則」（R5 窄定義）
AUTHORITY_CONFLICT_CONFIRMED      ？ 字面是「相反決定」；此處是「兩邊都說不是我」
INSUFFICIENT_EVIDENCE             ✓ 目前尚未完成 R1／R3／R4，仍為誠實的當前狀態
```

**裁示結果（2026-08-25）**：新增第五類 **`RESPONSIBILITY_GAP_CONFIRMED`**（定義與三條護欄見
`requirements.md` R5），理由是硬塞既有四類會污染語義——
`AUTHORITY_CONFLICT` 是「兩邊相反」，此處是「兩邊都說不是我」；
`CONTRACT_DEFECT` 已定窄為傳遞／一致性問題，把「規則內容彼此留洞」也算進去，
會把 **contract implementation defect** 與 **responsibility allocation defect** 混成一類。

⚠️ **但不得提前套用**：`outcome` 維持 `INSUFFICIENT_EVIDENCE`，直到 R1／R3／R4 完成。

---

## 5. R3 contract map（**只記錄、不裁決**）

### 5.1 兩次 entry 分開記

| | **A. `trigger_facet_key` 直達** | **B. reroute 後的 classification entry** |
|---|---|---|
| entry producer | 呼叫端（`POST /api/v1/message` 的 `trigger_facet_key` 欄，`chat.py:3867`）；Step 0.4 派發 `chat.py:4158-4165` | `_diagnosis_config_for_knowledge()`（`chat.py:832`） |
| entry evidence | **呼叫端給的字串本身**——無任何 query 側證據 | 檢索 top-1 知識的 `similarity` ＋ 其 `category` |
| entry authority | registry 存在且 `enabled`（`config_for_key` → `_cache["by_key"]`） | `facet_entry_eligible()`：`similarity ≥ form_trigger_threshold`（0.75，`decision_layer.py:191-199`）＋ `config_for_category` 的 category→Face 索引 |
| 額外抑制器 | **無** | `_instance_gate_decision`／`_instance_hint_suppressed`；`_preentry_routable`（**預設關閉**，見 F-5） |
| commit 點 | `_seed_repair_facet` → `_conversational_respond(start_if_absent=True)` → 引擎開會話 | 同左 |

⚠️ **兩者都沒有查過任何 responsibility contract**：
A 只看「這個 key 存在嗎」，B 只看「檢索夠像嗎、分類對得上嗎」。

### 5.2 scope 側

```text
scope producer   LLM（gpt-4o@0.4/400，json_object）於 conversational_step()
scope inputs     system_context_md ＋ rules_text ＋ faces 清單 ＋ 狀態六欄
                 （進場輪：collected={}／asked_count=0／recommended=False／
                   grounding_note=""／dialog=[]）→ **實際只餵原始問句**
scope contract   該 persona「對話規則」列的【本輪範疇 scope】條款（DB，見 F-2）
scope consumer   engine：`if step.get("scope")=="switch": await self._close(session_id); return None`
                 **無條件**——不看是否進場輪、不看 entry 由誰決定、不看有無 grounding
irreversible     會話關閉、該輪重路由；grounding 從未取得；brain 的那次付費呼叫已花掉
```

### 5.3 這張表直接顯示的不對稱

```text
entry 的證據語言   = 「呼叫端指定」或「檢索相似度＋分類」
scope 的證據語言   = 「責任範疇 wording」
兩者在現行系統中**沒有任何交集**：
  entry 從不查 responsibility wording；
  scope 從不知道 entry 發生過（F-1）。
```

⇒ 支持前提修正：**「成功進場」是 mechanism-level commitment，
不是 responsibility contract 對該 query 的認領。**

## F-5（初步）：早退這個形狀是**已知且被刻意停用**的設計狀態

`chat.py:737-762` 的 `_preentry_routable()` 是 entry-scoped gate，其 docstring 自述：

> 現況：「KB 很像 + KB 掛 category + score ≥ 0.75 → 直接進 workflow」——
> 沒有先問「使用者這題真的適合這個 workflow 嗎」。而 brain **已經會判**…
> 只是判得太晚：**先進場、判錯再退出**。

它把同一個 scope 判斷挪到 commit 之前，但 `PREENTRY_ROUTABILITY_GATE` 現行為 **false**：
`.env:164` 明設 `false`，兩份 compose 亦皆宣告 `${PREENTRY_ROUTABILITY_GATE:-false}`
（prod:224／dev:81）——三處一致，故現行不生效。

⚠️ **關鍵推論（待 R4 證偽）**：即使打開它，本案也只是**更早退出**——
`bill_diagnosis` 仍不接這句 query，`billing_anomaly` 的規則也把它推走。
**責任覆蓋的洞不會因為退出時機提前而被補上。**

⇒ 「先進場再退出」比較像**時機問題**，F-2 的互推比較像**責任分配問題**——
兩者不同層，R5 分流時不得混為一談。

## 6. 更新後的缺口（對齊業主 2026-08-25 裁示）

```text
R5 分類  已新增第五類 RESPONSIBILITY_GAP_CONFIRMED（業主 2026-08-25）；
         **目前 outcome 仍為 INSUFFICIENT_EVIDENCE，不得提前套用**
R3       ✅ 本次完成（§5.1／5.2／5.3）；但「不存在 responsibility 層的 entry authority」
         這個結論本身仍待 R4 交叉驗證
R2       主幹完成；尚未列全 system_context 與 faces 清單的實際內容
R1       ❌ 最小 reproduction 尚未建立（目前僅有 C4b 的 e2e 重現）
R4       載錯 rules ✗ 已證偽（F-2）／responsibility context 未傳入 ✅ 有證據（F-1）
         **尚未證偽**：context 截斷 ／ Face identity·state 不一致 ／
         reroute 殘留 ／ producer-consumer contract mismatch
```

⚠️ 依 R7，「讓 `diag-01` 不再退出」不是本 spec 的 acceptance criterion；
上列缺口補齊、證據足以歸因，才是。

---

## 7. R4-static：三項候選的證偽（**零 OpenAI 成本**）

### 7.0 方法：capture-then-raise（不送網路）

把 `provider.chat_completion` 換成「記錄參數後**拋例外**」的替身，走**真 HTTP 路徑**
（`POST /api/v1/message` 帶 `trigger_facet_key=bill_diagnosis`）進場一次。
brain 呼叫因此**從未送出**，但送進 producer 的 `messages` 已被逐字捕捉；
brain 失敗 → 引擎關會話 → 落回檢索 → 分類路由再進場 → 第二次捕捉。

⚠️ 這**不是** R1 的 reproduction：它不重現 `scope=switch` 的判定（沒有 LLM），
只捕捉**輸入**與 **session lineage**。判定的重現仍屬 R1。

一次請求捕到 5 次 provider 呼叫：

```text
#1 gpt-4o      0.4 / 400 / json_object   ← entry A（trigger 直達）的 brain
#2 gpt-4o      0.4 / 400 / json_object   ← entry B（分類路由）的 brain
#3 gpt-4o-mini 0    / 32                 ← 適用性把關（非 brain）
#4 gpt-4o-mini 0    / 32                 ← 適用性把關（非 brain）
#5 gpt-3.5-turbo 0.2 / 800               ← 兜底答案合成（非 brain）
```

（#3–#5 再次印證：共用 provider 的呼叫計數**不等於** brain 呼叫數。）

### 7.1 `context truncation` → **FALSIFIED**

```text
value flow   DB knowledge_base.answer（id 4252，888 字）
             → conversational_rules.load_rules()：**原樣回傳**，無切片（僅進程快取）
             → system_context.get_system_context()：base ＋ appends 以 "\n\n" 串接；
               超過 MAX_CHARS_WARN 只 **print 警告**，**不裁切**
             → conversational_step()：system_prompt = system_context_md + rules_text
               + faces_note + schema_note + tool_note（純串接，無切片）
runtime 佐證 捕捉到的 system message：len=1737，且**逐字包含**授權原文：
             「【本輪範疇 scope】…帳單金額組成/看不到帳單（帳單異常）、繳費入帳（繳費金流排障）、
               其他領域完整新問題 → scope="switch"。不確定 → stay 並澄清。」
             亦包含【本領域可用面向】與 JSON schema 段。
```

⇒ 關鍵 scope 條款**確實存在於實際送進 producer 的 prompt**，未被裁切或替換。

### 7.2 `Face identity / state mismatch` → **FALSIFIED**

```text
session lineage（同一 sid，實查 form_sessions）
  row 759  state=COMPLETED  config_key=bill_diagnosis  collected={}  asked=0   ← entry A 開、退出時關
  row 760  state=COMPLETED  config_key=bill_diagnosis  collected={}  asked=0   ← entry B 另開、再關
prompt 同一性
  #1 與 #2 的 system message **byte-identical**（同 sha1），user message 亦然
```

⇒ 兩次進場都是 `bill_diagnosis`、都是全新空狀態、consumer 關掉的正是自己開的那一列。
**沒有 identity 漂移，沒有跨列狀態污染。**

⚠️ 附帶（正式判定屬 R1）：`reroute 殘留` 已取得強證據——第二次不但沒有殘留，
連 prompt 都與第一次逐字相同。

### 7.3 `producer / consumer contract mismatch` → **FALSIFIED**

```text
producer 正規化   data['scope'] = 'switch' if data.get('scope') == 'switch' else 'stay'
                  → **只有字面 'switch' 會活下來**；缺省／越界／大小寫不同一律 'stay'
consumer 判斷     if step.get("scope") == "switch": await self._close(session_id); return None
                  → 精確等值比對，無 fallback／default 會把別的值轉成 switch
其他寫入點        全庫僅此一處寫 data['scope']；引擎不另行改寫 step['scope']
可區分的鄰近失效  action 越界 → 整包 JSON 丟棄回 None（**不是** switch），
                  引擎走「brain 失敗」分支，log 行不同
```

⇒ 對位完整；且實際 log 印的是 `🔀 brain 判定離題(scope=switch)`，
可與「brain 失敗」分支明確區分——本案確為 producer 真的輸出了 `switch`。

### 7.4 三項結論與**尚未成立**的部分

```text
context truncation                FALSIFIED
Face identity / state mismatch    FALSIFIED
producer / consumer mismatch      FALSIFIED
reroute 殘留                       強證據支持排除，正式判定留 R1
```

⚠️ **mutual delegation 目前仍是規則文字推論，不是 runtime 觀測**：
本次兩次進場**都是 `bill_diagnosis`**（entry B 的檢索分類同樣落回 `條件診斷：帳單`），
`billing_anomaly` 從未實際被進場過。F-2 對 `billing_anomaly` 的「也會 switch」是讀規則得出的，
**必須由 R1 以 diagnostic invocation 實測**，否則 `RESPONSIBILITY_GAP_CONFIRMED`
的關鍵支柱只有一半。

---

## 8. R1 first execution（**diagnostic reproduction**，2026-08-25）

> 協議：`r1-protocol-frozen.md`（**先於本次執行 commit**，`535a2e1`）
> evidence：`evidence/r1-first-execution.json` ＋ `evidence/r1-first-execution-stdout.log`
> 預算：`target_scope_calls = 9`（上限 12）／`all_provider_calls = 18`（上限 30）／`retries = 0`
> query sha1（前 16）：`c0d220cc3f1d47cb`

### 8.1 Goal A：bill_diagnosis 的 reroute residue → **FALSIFIED**

3 次 repetition，每次都捕到兩次 brain 呼叫（entry #1 直達／entry #2 分類路由）：

| rep | session rows | call#1 | call#2 |
|---|---|---|---|
| 1 | 761／762 皆 `bill_diagnosis`・`asked=0`・COMPLETED | sys `2285acc5…` user `f045d139…` → **switch** | 同 digest → **switch** |
| 2 | 763／764 同上 | 同 digest → **switch** | 同 digest → **switch** |
| 3 | 765／766 同上 | 同 digest → **switch** | 同 digest → **switch** |

```text
七欄比對   face identity   兩次皆 bill_diagnosis（session row 的 config_key 與 rules digest 一致）
           rules digest    b2dfdc465e1182a5（888 字）— 六次呼叫全同
           sys ctx digest  d1f88c90a2e0c9d2（key=條件診斷：帳單）— 六次呼叫全同
           state           collected={}／asked_count=0／recommended=False — 全同
           query           逐字相同
           history         六次皆**無**【最近對話】區塊
           scope result    **6/6 switch**（取自回應 JSON 的原始值，正規化前）
```

⇒ 第二次進場的輸入除 session row id／生命週期外**逐位元等價**，判定亦相同。
**reroute residue → FALSIFIED**（協議 §5 判準）。

⇒ 併帶：`bill_diagnosis` 對本 query 的拒絕為 **6/6 → stable observed rejection**。

### 8.2 Goal B：billing_anomaly 的 runtime 判定 → **2/3 switch**

以 production `_preentry_routable` 判定 seam，同一句 query：

```text
rep1  switch   {"action":"ask","scope":"switch", next_question:"…需要帳單編號或合約編號/物件名稱…"}
rep2  **stay** {"action":"ask","scope":"stay",  next_question:"…是帳單金額不對嗎？還是有其他異常？"}
rep3  switch   {"action":"ask","scope":"switch", next_question:"…這筆帳單的編號或相關合約編號是什麼？"}
```

依協議 §3：**2/3 switch ＝ rejection reproduced, stability not established**。

⚠️ **F-2 對 billing_anomaly 的「一定 switch」推論，被 runtime 反證為「不一定」。**

### 8.3 事前揭露的 confounder **已成真**，且是 B 的首要保留

協議 §1 事前寫下兩個 seam 的 system-context key 分歧。實測 digest：

```text
bill_diagnosis    in-session key=條件診斷：帳單 → d1f88c90a2e0c9d2
                  pre-entry  key=bill_diagnosis → d1f88c90a2e0c9d2   （相同：都落回 base）
billing_anomaly   in-session key=帳單異常       → **2158ebdc2d8fe7e6**
                  pre-entry  key=billing_anomaly → d1f88c90a2e0c9d2   （**不同**：落回 base）
```

⇒ **Goal B 實測時，billing_anomaly 拿到的是 base system context，
不是 in-session 會拿到的「帳單異常」領域脈絡。**
故 B 的 2/3 **不能**直接當成「in-session 的 billing_anomaly 也會這樣判」。

### 8.4 對裁決表的對位（**不自行解釋，提請裁示**）

協議 §5 的四列裡：

```text
列1  需要「billing_anomaly switch」——實測為 2/3，**非**一致 switch
列2  需要「billing_anomaly stay」——實測**也不是**一致 stay
列3  reroute 輸入實質不同——**已排除**（8.1 逐位元等價）
列4  「LLM 結果不穩定」→ INSUFFICIENT_EVIDENCE——§3 對 2/3 的定義是
     「reproduced, stability not established」，與「unstable（1/3）」**不是同一格**
```

⇒ 觀測結果落在列 1 與列 4 之間，凍結的表**沒有涵蓋這一格**。
**本檔不自行補格**（那正是「臨場發明分類」）。目前 outcome 維持 **`INSUFFICIENT_EVIDENCE`**。

提請裁示的兩個選項（互斥）：

```text
(a) 直接裁定 2/3 在本表如何對位（例如視為未達列 1 的門檻 → 維持 INSUFFICIENT_EVIDENCE）
(b) 先移除 8.3 的 confounder 再判：以 **in-session 的 system-context key**（帳單異常）
    重跑 B 三次（+3 次 target 呼叫）。⚠️ 這會是**變體 seam**，須先凍結為 B′ 再跑，
    且其結果**不得**回填 B 的原始紀錄。
```

### 8.5 本次可以確定的三件事

```text
✅ reroute residue                      FALSIFIED
✅ bill_diagnosis 對本 query 的拒絕      stable（6/6）
❌ 「兩個 Face 都拒絕」                  **尚未成立**——billing_anomaly 2/3，且帶 confounder
⇒ RESPONSIBILITY_GAP_CONFIRMED **不得**套用
```

---

## 9. F-5 降級（獨立 discovery，2026-08-25）

§8.3 實測證明：`_preentry_routable` 對 `billing_anomaly` 取到的 system context
（`get_system_context(db, cfg.key)` → base，digest `d1f88c90…`）
**與該面向真正的 in-session context**（`_domain_key(config)`＝「帳單異常」，digest `2158ebdc…`）
**不同**。

因此 F-5 原本引述 `_preentry_routable` docstring 的那句「**只是把同一判定提前**」
**必須降級**。目前證據只支持：

```text
✅ 它重用同一個 scope evaluator（同一支 conversational_step、同一組 model/config）
❌ 它**不一定**重建相同的 evaluation context
```

⚠️ **先不要叫它 implementation defect**：gate 現為 disabled，且此 context 差異是否為
設計允許尚未查證。但下列表述自本日起**不得再使用**：

```text
❌ 「pre-entry 使用的是同一個 scope 判斷」（作為 production-equivalent 的完整命題）
❌ 以 R1 Goal B 的結果替 pre-entry gate 背書
```

⇒ 本項**不阻擋 B′**，也不需先修；記錄於此，避免日後被誤引。

---

## 10. B′ execution（production-equivalent variant，2026-08-25）

> 協議：`r1b-prime-protocol-frozen.md`（**先於執行 commit**，`322029e`）
> evidence：`evidence/r1b-prime-execution.json` ＋ `…-stdout.log`
> 預算：`target_scope_calls = 6`（上限 8）／`all_provider_calls = 15`（上限 20）／retry 0

### 10.1 confounder 已消掉（協議 §3 成立條件通過）

```text
in-session ctx key      帳單異常
ctx 出現在 prompt        三次皆 True（system sha 9dbd5c13a31b95c9，len 2177）
rules digest            aefa054899cdd7e6（＝billing_anomaly，與協議一致）
session rows            每次兩列：#1 billing_anomaly、#2 bill_diagnosis（switch 後落回分類路由）
                        後者以 rules digest 判定為 **uncounted**（協議 §2）
```

### 10.2 結果：**3/3 switch** → 依凍結表列 1 ＝ **stable in-session rejection**

```text
rep1 switch  「點退帳單屬合約退租收尾範疇，涉及封存處理時轉由合約領域接手，不在此重複解答。」
rep2 switch  （extracted_fields={"symptom":"金額"}，仍 scope=switch）
rep3 switch  「點退帳單處理屬於合約退租收尾範疇…建議您向合約管理專員詢問。」
```

三次的 uncounted 呼叫（落回後的 `bill_diagnosis`）亦皆 `switch`，與 §8.1 一致。

### 10.3 五項前提現況

```text
bill_diagnosis 拒絕          stable  6/6 switch（§8.1）
billing_anomaly 拒絕（in-session） stable  3/3 switch（本節）
reroute residue              FALSIFIED（§8.1）
context truncation           FALSIFIED（§7.1）
identity／state mismatch      FALSIFIED（§7.2）
producer／consumer mismatch   FALSIFIED（§7.3）
```

⇒ 凍結表列 1 的條件**全部滿足**。

### 10.4 ⚠️ 一個 B′ 意外帶出、且會影響 R5 標籤範圍的事實

`billing_anomaly` 的 runtime 輸出**指名了第三個接手方**：

```text
「點退帳單屬**合約退租收尾**範疇…轉由**合約領域**接手」
```

對照 §F-2 的規則文字，delegation 其實是**鏈**而非雙向迴圈：

```text
bill_diagnosis  ──「金額組成」──▶  billing_anomaly
billing_anomaly ──「封存/點退處理」──▶  合約退租收尾（contract_closeout）
contract_closeout ──?──▶  **未測**
```

⚠️ R5 對 `RESPONSIBILITY_GAP_CONFIRMED` 的定義是「未被**任何候選 Face** 接受為自身責任」。
本線實測的候選只有**兩個**；被指名的第三個（`contract_closeout`）**尚未測**。

⇒ 目前可安全成立的敘述是：

```text
✅ 在本 query 上，**已測的兩個候選 Face** 於各自 authoritative in-session context 下
   皆 stable 拒絕，且四項 execution 解釋皆已排除。
❓ 「不存在任何 owner」尚未成立——候選集是否應含 contract_closeout，屬**範圍裁定**。
```

**本檔不自行裁定候選集邊界**，亦不自行套用 R5 標籤。提請裁示（互斥）：

```text
(a) 候選集＝本線既定的兩個 Face → 條件已滿足 → 套 RESPONSIBILITY_GAP_CONFIRMED → STOP → 升級
(b) 候選集須含被指名的 contract_closeout → 先凍結 B″ 再測（+3 次 target 呼叫），
    結果不得回填 B′
```

---

## 11. B″ execution（runtime-delegated candidate expansion，2026-08-25）

> 協議：`r1b2-protocol-frozen.md`（**先於執行 commit**，`b14c09c`）
> evidence：`evidence/r1b2-execution.json` ＋ `…-stdout.log`
> 預算：`target_scope_calls = 3`（上限 8）／`all_provider_calls = 3`（上限 20）／retry 0

### 11.1 結果：**3/3 stay** → 凍結表列 1 ＝ **responsibility owner exists**

```text
成立條件  三次的 system message 皆含 in-session（退租收尾）脈絡：ctx_in_prompt=True
          sys sha e1d2ccc0a3c10a31（2748）／rules digest 363ed0d0da3ca23c（協議一致）
rep1 stay {"action":"ask","next_question":"請問是哪一份合約或物件名稱呢？","scope":"stay","face":"退租收尾"}
rep2 stay {"action":"ask","next_question":"請問是哪份合約或物件名稱呢？…","scope":"stay","face":"退租收尾"}
rep3 stay {"action":"ask","next_question":"請提供合約編號或物件名稱，…","scope":"stay","face":"退租收尾"}
session   773／774／775 皆 **COLLECTING**（留在面向內，未被關閉）
uncounted 0（沒有落回分類路由——因為它根本沒退出）
```

⇒ **`contract_closeout` 接受這句 query，且穩定（3/3）。**

### 11.2 `RESPONSIBILITY_GAP_CONFIRMED` → **假說被反證（refuted）**

依 R9 的 closure 規則，delegation closure 於**終止條件 A（stable stay）**收斂：

```text
bill_diagnosis ──「金額組成」──▶ billing_anomaly ──「封存/點退處理」──▶ contract_closeout ──▶ **STAY**
```

⇒ 候選集已追至終點，且終點**接受**責任。第五類的操作化定義（§R5 第二版）
要求「所有實際被提出的候選 owner 皆不接受」——**不成立**。

### 11.3 觀測到的實際形狀（依協議 §5，**不得硬塞既有分類**）

```text
responsibility owner exists      contract_closeout accepts（3/3 stay，in-session context）
observed routing path            retrieval／classification → **bill_diagnosis**
                                 → scope rejects → reroute → **bill_diagnosis** again
                                 （§8.1 六次、§10.1 三次 uncounted 呼叫，皆為 bill_diagnosis）
從未發生                          任何一次 entry-routing 提出 contract_closeout
```

⇒ 形狀是：

> **responsibility owner exists but is unreachable /
> not proposed by current entry-routing authority.**

⚠️ 依協議 §5：**不是** responsibility gap，**不得**硬塞 `IMPLEMENTATION_DEFECT`。

### 11.4 R5 五類**沒有**對應這個形狀（提請裁示）

```text
IMPLEMENTATION_DEFECT_CONFIRMED   ✗ 協議 §5 明文不得硬塞；且 rules 載對、evaluator 照契約走
CONTRACT_DEFECT_CONFIRMED         ✗ 窄定義是傳遞／一致性問題；此處 contract 傳遞正確
AUTHORITY_CONFLICT_CONFIRMED      ✗ 不是「兩邊相反」——三個 Face 的判定彼此**一致且互補**
RESPONSIBILITY_GAP_CONFIRMED      ✗ **已被 B″ 反證**
INSUFFICIENT_EVIDENCE             ？ 就 descriptive discovery 而言，證據其實已相當充分
```

⇒ **本檔不自行新增第六類**。目前 `outcome` 維持 `INSUFFICIENT_EVIDENCE`，
並記錄：五類皆不對應，需業主裁定分類（例如
`OWNER_EXISTS_BUT_UNREACHABLE` 之類的名稱與定義）。

### 11.5 這一輪把治理問題換掉了

```text
原本要交給 governance 的  「責任配置沒有 owner，誰該接？」
實測後應交給 governance 的 「owner 已存在且會接，為什麼 entry-routing authority
                            從來不提出它？該由誰決定 entry 提名的依據？」
```

⚠️ 兩者是**完全不同**的治理問題。若當初在 B′ 之後就收 gap，交出去的會是錯的那一個。

### 11.6 仍未回答（不得順手做）

```text
❌ 為什麼 retrieval／classification 從不提出 contract_closeout（entry 提名機制的問題）
❌ 是否該讓它被提出（**normative**，屬 routing-authority-model）
❌ 任何修法——root cause 於 entry 側尚未 adjudicated
```

---

## 12. entry nomination chain tracing（**零 OpenAI**，2026-08-25）

> 授權範圍：仍是 descriptive——「**現行系統為什麼實際上沒有提出已存在的 owner**」，
> 不是「未來應該由誰決定 owner」。

### 12.1 提名鏈的實際依據

```text
query
→ 檢索 top-1（本 query 實測：id 3519「點退帳單金額計算 押金結算」sim=0.947）
→ _knowledge_category(best)：**categories 多值優先**，無則退 category 單值（chat.py:722-734）
→ config_for_category(cat)：只索引 topic_scope.mode=='category' 且 enabled 的面向
→ facet_entry_eligible：similarity ≥ form_trigger_threshold（0.75）
→ 抑制器：_instance_hint_suppressed ／ _preentry_routable（後者預設 false）
→ entry proposal
```

### 12.2 六個問題的實查答案

```text
Q1 contract_closeout 在可被提名的 Face index 內嗎？
   **在。** topic_scope={mode:category, category:退租收尾}，enabled=True
   → 落在 by_category['退租收尾']；且該分類實際有 **11 筆** active 知識。

Q2 什麼證據才能提名它？
   檢索 top-1 的 categories（或 category）**含「退租收尾」** 且 similarity ≥ 0.75。

Q3 為何 diag-01 的 query 只導向 bill_diagnosis？
   top-1 id 3519 categories = ['合約管理', '條件診斷：帳單'] → 命中 bill_diagnosis；
   top-2 id 3518 categories = ['合約管理'] → 不對應任何面向。
   另有 id 4657「合約的點退帳單金額 查點退金額」categories = ['條件診斷：帳單']
   ——**與本 query 幾乎同義的知識，也只掛 bill_diagnosis 的分類**。
   實查「點退」相關 22 筆中，掛 '退租收尾' 的只有 id 3526（提前解約生效後…）與
   id 4216（退房後換新租客…），**沒有一筆是在講「查點退帳單金額」**。

Q4 entry layer 看得到 billing_anomaly→contract_closeout 這條 delegation 嗎？
   **看不到。** 該 delegation 只存在於 persona 規則列的 answer 文字（【本輪範疇 scope】），
   而 entry 只讀「檢索知識的 categories ＋ 門檻」（§5.1）。兩者無交集。

Q5 有 deterministic suppression 把它排掉嗎？
   **沒有。** 抑制器只能作用在**已被 category 命中的**面向；
   contract_closeout 從未被提名，因此不存在「被抑制」這回事。

Q6 固定現行 routing inputs，contract_closeout 在 candidate set 內嗎？
   **對本 query：不在**（沒有任何檢索到的知識掛 '退租收尾'）。
   ⚠️ 但對其他 query **可以在**（該索引鍵有 11 筆知識）——
   故**不得**說它「架構上 unreachable」。這正是第六類刻意不叫 unreachable 的理由。
```

### 12.3 三種形狀的判定

```text
A. mapping／metadata 明確缺漏          ⚠️ **部分觀測到，但不得逕稱 defect**
   事實：與本 query 同義的知識（3519／4657）只掛 '條件診斷：帳單'。
   要說「應該也掛 退租收尾」就是在**判定誰該擁有**——那是 normative，不屬本線。

B. entry contract 只看 retrieval category，responsibility contract 不參與 nomination
   ✅ **CONFIRMED**——程式面（§5.1）＋ Q4 實查雙重支持。這是結構性答案。

C. contract_closeout 本可被提名，但 ranking 永遠把別人推上來
   ✗ **REFUTED**——不是排序問題：能提名它的證據（掛 '退租收尾' 的知識）
   在本 query 的候選集中**根本不存在**，換排序也提不出來。
```

### 12.4 缺的那座橋（本輪 discovery correction 的一句話）

```text
responsibility layer   contract_closeout → STAY 3/3（§11）
entry layer            observed proposals → bill_diagnosis only（9/9）
missing bridge         **entry nomination 完全不讀 responsibility contract**；
                       兩層之間唯一的耦合是「知識列的 categories」這個人工標註
```

> **問題已從「責任沒有 owner」修正為
> 「owner 存在，但 responsibility ownership 與 entry nomination 之間
> 沒有被證實存在可達的橋」。**

### 12.5 升級用的問題（**descriptive 半段已完成；normative 半段尚未送出**）

```text
本線已回答（descriptive）
  現行 entry nomination 依賴：檢索 top-1 的 categories ＋ 相似度門檻。
  contract_closeout 未被提出，因為本 query 的候選知識沒有一筆掛 '退租收尾'，
  且 entry 從不讀 responsibility contract。

待升級（normative，屬 Responsibility Governance Decision Record）
  當 responsibility owner 已存在且會接受 query，但現行 entry-routing authority
  未將其納入／選為候選時，entry nomination 應如何取得 responsibility evidence，
  以及**哪個 authority 有權決定候選集合**？
```

⚠️ **尚未送出**：依業主裁示，等 descriptive 段落定稿後再作為 governance input 升級；
本檔**不**產生 normative 建議、**不**提修法。
