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
